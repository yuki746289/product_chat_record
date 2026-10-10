# Created: 2026-10-10 JST
"""Local Saxo chart captures: 30-minute snapshots, token refresh, conservative retention."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import load_settings, EXPECTED_TIMEFRAMES
from .chart import render_pair
from .local_monitor import clean_local_images, get_monitor_options
from .main import is_fresh_minute_candle
from .saxo_provider import SaxoProvider


def get_saxo_config(cfg):
    sax=cfg.get('saxo',{})
    if sax.get('environment') not in ('sim','live'):
        raise ValueError('saxo.environment must be sim or live')
    if sax.get('price_side') not in ('bid','ask'):
        raise ValueError('saxo.price_side must be bid or ask')
    period=cfg.get('local_monitor',{}).get('chart_interval_minutes',30)
    if isinstance(period,bool) or period not in (15,30,60):
        raise ValueError('chart_interval_minutes must be 15, 30, or 60')
    return sax,period


def _state_path(root):
    return Path(root)/'.saxo_capture_state.json'


def _read_last_success(root):
    path=_state_path(root)
    if not path.is_file():
        return None
    try:
        state=json.loads(path.read_text(encoding='utf-8'))
        return state.get('last_completed_slot')
    except (ValueError,TypeError):
        return None


def _save_last_success(root,slot):
    path=_state_path(root)
    temp=path.with_suffix('.json.tmp')
    temp.write_text(json.dumps({'last_completed_slot':slot})+'\n',encoding='utf-8')
    temp.replace(path)


def tick_once(config_path, now=None, provider=None):
    """Called every minute by tray; refresh token every tick and generate at most once/slot.

    Only the listed configured pairs are written, and stale pairs are skipped.
    If data is unavailable, the slot stays eligible for retry on the next poll.
    """
    cfg=load_settings(config_path)
    sax,period=get_saxo_config(cfg)
    if not sax.get('enabled',False):
        raise RuntimeError('Saxo local provider disabled. Complete OAuth setup, then set saxo.enabled: true')
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('now must be timezone-aware')
    now=now.astimezone(timezone.utc)
    root=Path(cfg['output']['local_dir'])
    root.mkdir(parents=True,exist_ok=True)
    _,hours,minimum=get_monitor_options(cfg)
    source=provider or SaxoProvider(cfg)
    try:
        # Refresh access/refresh tokens even if no 30-minute snapshot is due.
        source.session.access_token()
        slot=str(int(now.timestamp())//(period*60))
        if _read_last_success(root)==slot:
            return []
        # Use the scheduled slot time to avoid duplicate folders after a retry.
        stamp=datetime.fromtimestamp(int(slot)*period*60,timezone.utc).astimezone(ZoneInfo(cfg['output']['timezone'])).strftime(cfg['output']['folder_format'])
        folder=root/stamp
        generated=[]
        errors=[]
        for item in cfg['symbols']:
            pair=item['pair']
            try:
                frames={}
                one=source.get(pair,'1M',cfg['chart']['history_bars'])
                if not is_fresh_minute_candle(one,now,cfg['market']['max_1m_age_minutes']):
                    continue
                frames['1M']=one
                for tf in EXPECTED_TIMEFRAMES:
                    if tf!='1M':
                        frames[tf]=source.get(pair,tf,cfg['chart']['history_bars'])
                    if len(frames[tf])<cfg['chart']['bars']:
                        raise ValueError(f'{pair} {tf}: insufficient candles')
                path=folder/(pair+'.png')
                render_pair(frames,pair,path,cfg,stamp,
                            source_label=f"Saxo {sax['environment'].upper()} {sax['price_side'].upper()}",
                            eight_hour_label='Saxo native 8H')
                generated.append(path)
            except Exception as exc:
                errors.append(f'{pair}: {type(exc).__name__}: {exc}')
        if errors:
            # Partial output is kept; retry other pairs next tick in this slot.
            # Avoid marking completed until all pairs either succeeded or are closed.
            raise RuntimeError('Some Saxo pairs failed: '+'; '.join(errors))
        if generated:
            _save_last_success(root,slot)
        return generated
    finally:
        clean_local_images(root,now,hours,minimum,cfg['output']['timezone'])


def main():
    parser=argparse.ArgumentParser(description='Create local Saxo chart PNGs once')
    parser.add_argument('--config',default='setting.yaml')
    args=parser.parse_args()
    images=tick_once(args.config)
    print(f'Images generated: {len(images)}')
    for item in images: print(item)


if __name__=='__main__':
    main()
