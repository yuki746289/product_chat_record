# Created: 2026-10-09 22:09 JST
"""CLI: generate PNG charts, with explicit --demo for synthetic test data."""
import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from .chart import render_pair
from .config import load_settings, EXPECTED_TIMEFRAMES
from .providers import DemoProvider, TradingViewMcpProvider, resample_8h


def generate(settings, timestamp=None, demo=False, output_override=None):
    cfg = load_settings(settings)
    folder_time = timestamp or datetime.now(ZoneInfo(cfg['output']['timezone'])).strftime(cfg['output']['folder_format'])
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
        for tf in EXPECTED_TIMEFRAMES:
            if tf == '8H':
                bars[tf] = resample_8h(bars['4H'])
            else:
                bars[tf] = provider.get(item['tradingview'], tf, cfg['chart']['history_bars'] * (2 if tf == '4H' else 1))
            if len(bars[tf]) < cfg['chart']['bars']:
                raise RuntimeError(f'{item["pair"]} {tf}: insufficient candles ({len(bars[tf])})')
        dst = render_pair(bars, item['pair'], out / f'{item["pair"]}.png', cfg, folder_time, demo=demo)
        print(f'Generated: {dst}', flush=True)
        outputs.append(dst)
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
