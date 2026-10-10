# Created: 2026-10-09 22:09 JST
"""CLI: generate PNG charts, with explicit --demo for synthetic test data."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from zoneinfo import ZoneInfo
from .chart import render_pair
from .config import load_settings, EXPECTED_TIMEFRAMES
from .providers import DemoProvider, TradingViewMcpProvider, resample_8h


def is_fresh_minute_candle(one_minute_bars, now_utc, max_age_minutes):
    """Return True only when the last 1-minute candle timestamp is recent.

    Data freshness is a proxy, not an exchange holiday calendar.
    Verify timestamp semantics and delays on the live provider.
    """
    if one_minute_bars.empty:
        return False
    last = one_minute_bars.index.max()
    if last.tzinfo is None or now_utc.tzinfo is None:
        raise ValueError('Candle and comparison timestamps must be timezone-aware')
    age = (pd.Timestamp(now_utc).tz_convert('UTC') - last.tz_convert('UTC')).total_seconds()
    return -60 <= age <= max_age_minutes * 60


def generate(settings, timestamp=None, demo=False, output_override=None, now_utc=None):
    cfg = load_settings(settings)
    now_utc = now_utc or datetime.now(timezone.utc)
    folder_time = timestamp or now_utc.astimezone(ZoneInfo(cfg['output']['timezone'])).strftime(cfg['output']['folder_format'])
    out = Path(output_override or cfg['output']['staging_dir']) / folder_time
    if demo:
        provider = DemoProvider()
    else:
        if not cfg['provider']['enabled']:
            raise RuntimeError('Live provider disabled in setting.yaml; authorization and terms review required')
        provider = TradingViewMcpProvider(cfg['provider']['url'])
    outputs = []
    for item in cfg['symbols']:
        bars = {}
        if not demo and cfg['market']['skip_stale']:
            # Fetch 1-minute candles first. Closed/stale pairs skip expensive frames.
            bars['1M'] = provider.get(item['tradingview'], '1M', cfg['chart']['history_bars'])
            if not is_fresh_minute_candle(bars['1M'], now_utc, cfg['market']['max_1m_age_minutes']):
                latest = bars['1M'].index.max() if len(bars['1M']) else 'none'
                print(f'SKIPPED: {item["pair"]} -- no recent 1M data (latest {latest})', flush=True)
                continue
        for tf in EXPECTED_TIMEFRAMES:
            if tf == '8H':
                bars[tf] = resample_8h(bars['4H'])
            elif tf not in bars:
                bars[tf] = provider.get(item['tradingview'], tf, cfg['chart']['history_bars'] * (2 if tf == '4H' else 1))
            if len(bars[tf]) < cfg['chart']['bars']:
                raise RuntimeError(f'{item["pair"]} {tf}: insufficient candles ({len(bars[tf])})')
        dst = render_pair(bars, item['pair'], out / f'{item["pair"]}.png', cfg, folder_time, demo=demo)
        print(f'Generated: {dst}', flush=True)
        outputs.append(dst)
    if not outputs:
        print('SKIPPED: no current market images; no artifact should be uploaded', flush=True)
    return outputs


def cli():
    p = argparse.ArgumentParser()
    p.add_argument('--config', default='setting.yaml')
    p.add_argument('--demo', action='store_true', help='Synthetic candles for smoke tests only')
    p.add_argument('--timestamp', help='Override YYYYMMDD_HHMM for repeatable tests')
    p.add_argument('--output', help='Override staging output root')
    args = p.parse_args()
    generate(args.config, args.timestamp, args.demo, args.output)

if __name__ == '__main__':
    cli()
