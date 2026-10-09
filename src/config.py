# Created: 2026-10-09 22:09 JST
"""Load validated chart settings."""
from pathlib import Path
import re
import yaml

EXPECTED_TIMEFRAMES = ('1M', '5M', '15M', '1H', '4H', '8H', '1D', '1W', '1Mn')

def load_settings(path):
    source = Path(path)
    cfg = yaml.safe_load(source.read_text(encoding='utf-8'))
    if not isinstance(cfg, dict):
        raise ValueError('setting.yaml must contain a mapping')
    symbols = cfg.get('symbols', [])
    if not isinstance(symbols, list) or not symbols:
        raise ValueError('symbols must be a non-empty list')
    seen = set()
    for item in symbols:
        if not isinstance(item, dict) or not re.fullmatch(r'[A-Z0-9_-]{3,32}', str(item.get('pair', ''))):
            raise ValueError(f'invalid currency pair entry: {item}')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+', str(item.get('tradingview', ''))):
            raise ValueError(f'invalid TradingView symbol for {item["pair"]}')
        if item['pair'] in seen:
            raise ValueError(f'duplicate currency pair: {item["pair"]}')
        seen.add(item['pair'])
    chart = cfg.get('chart', {})
    if tuple(chart.get('timeframes', [])) != EXPECTED_TIMEFRAMES:
        raise ValueError('chart.timeframes must be the nine ordered specified timeframes')
    if chart.get('columns') != 2:
        raise ValueError('chart.columns must be 2')
    for key, vals in (('ema', [20, 30, 40]), ('rci', [9, 14, 26])):
        if chart.get(key) != vals:
            raise ValueError(f'chart.{key} must be {vals}')
    if int(chart.get('bars', 0)) < 42 or int(chart.get('history_bars', 0)) < 100:
        raise ValueError('insufficient chart/history bars')
    if cfg.get('provider', {}).get('type') != 'tradingview_mcp':
        raise ValueError('provider.type must be tradingview_mcp; demo uses --demo')
    if cfg.get('output', {}).get('retention_hours') != 8:
        raise ValueError('retention_hours must be 8')
    return cfg
