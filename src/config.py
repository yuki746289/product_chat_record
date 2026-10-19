# Created: 2026-10-09 22:09 JST
# Updated: 2026-10-14 JST (resolve relative image directory beside setting.yaml)
"""Load validated chart settings."""
from pathlib import Path, PureWindowsPath
from zoneinfo import ZoneInfo
import re
import yaml

EXPECTED_TIMEFRAMES = ('1M', '5M', '15M', '1H', '4H', '8H', '1D', '1W', '1Mn')

def load_settings(path):
    source = Path(path)
    cfg = yaml.safe_load(source.read_text(encoding='utf-8'))
    if not isinstance(cfg, dict):
        raise ValueError('setting.yaml must contain a mapping')
    # Portable desktop installations specify output.local_dir: chart_image.
    # Resolve relative to setting.yaml rather than the caller's working directory.
    output = cfg.get('output', {})
    if isinstance(output, dict):
        local_dir = output.get('local_dir')
        if isinstance(local_dir, str) and local_dir.strip():
            if not Path(local_dir).is_absolute() and not PureWindowsPath(local_dir).is_absolute():
                output['local_dir'] = str((source.resolve().parent / local_dir).resolve())
    symbols = cfg.get('symbols', [])
    if not isinstance(symbols, list) or not symbols:
        raise ValueError('symbols must be a non-empty list')
    seen = set()
    for item in symbols:
        if not isinstance(item, dict) or not re.fullmatch(r'[A-Z0-9_-]{3,32}', str(item.get('pair', ''))):
            raise ValueError(f'invalid currency pair entry: {item}')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+', str(item.get('tradingview', ''))):
            raise ValueError(f'invalid TradingView symbol for {item["pair"]}')
        category = item.get('category', 'uncategorized')
        if not isinstance(category, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,39}', category):
            raise ValueError(f'invalid category for {item["pair"]}')
        if item['pair'] in seen:
            raise ValueError(f'duplicate currency pair: {item["pair"]}')
        seen.add(item['pair'])
    chart = cfg.get('chart', {})
    if not isinstance(chart, dict):
        raise ValueError('chart must be a mapping')
    frames = chart.get('timeframes')
    if not isinstance(frames, list) or not frames or any(
            not isinstance(tf, str) or tf not in EXPECTED_TIMEFRAMES for tf in frames):
        raise ValueError(f'chart.timeframes must be a non-empty list of {EXPECTED_TIMEFRAMES}')
    if len(frames) != len(set(frames)):
        raise ValueError('chart.timeframes must not contain duplicates')
    columns = chart.get('columns')
    if isinstance(columns, bool) or not isinstance(columns, int) or not 1 <= columns <= 20:
        raise ValueError('chart.columns must be an integer from 1 to 20')
    for key, lower in (('ema', 1), ('rci', 2)):
        periods = chart.get(key)
        if not isinstance(periods, list) or not periods or any(
                isinstance(n, bool) or not isinstance(n, int) or n < lower for n in periods):
            raise ValueError(f'chart.{key} must be a non-empty list of integer periods >= {lower}')
        if len(periods) != len(set(periods)):
            raise ValueError(f'chart.{key} must not contain duplicates')
    bars = chart.get('bars')
    history = chart.get('history_bars')
    if (isinstance(bars, bool) or not isinstance(bars, int) or bars < 42
            or isinstance(history, bool) or not isinstance(history, int)
            or not max(100, bars, *chart['ema'], *chart['rci']) <= history <= 1200):
        raise ValueError('chart.bars must be >= 42 and chart.history_bars must be 100..1200 and >= all indicator periods and bars')
    dpi = chart.get('dpi')
    if isinstance(dpi, bool) or not isinstance(dpi, int) or not 40 <= dpi <= 600:
        raise ValueError('chart.dpi must be an integer from 40 to 600')
    size = chart.get('figsize')
    if (not isinstance(size, list) or len(size) != 2 or any(
            isinstance(n, bool) or not isinstance(n, (int, float)) or not 1 <= n <= 100 for n in size)):
        raise ValueError('chart.figsize must be [width, height], each between 1 and 100 inches')
    padding = chart.get('right_padding_bars', 12)
    if isinstance(padding, bool) or not isinstance(padding, int) or not 0 <= padding <= 1000:
        raise ValueError('chart.right_padding_bars must be an integer from 0 to 1000')
    if chart.get('theme', 'dark') not in ('dark', 'light'):
        raise ValueError('chart.theme must be dark or light')
    for section, name in ((chart, 'chart'), (cfg.get('output', {}), 'output')):
        try:
            ZoneInfo(section['timezone'])
        except (KeyError, TypeError, ValueError, OSError) as exc:
            raise ValueError(f'{name}.timezone must be a valid IANA timezone') from exc
    market = cfg.setdefault('market', {})
    market.setdefault('skip_stale', True)
    market.setdefault('max_1m_age_minutes', 10)
    if not isinstance(market['skip_stale'], bool):
        raise ValueError('market.skip_stale must be boolean')
    if (isinstance(market['max_1m_age_minutes'], bool)
            or not isinstance(market['max_1m_age_minutes'], int)
            or not 1 <= market['max_1m_age_minutes'] <= 30):
        raise ValueError('market.max_1m_age_minutes must be an integer from 1 to 30')
    if cfg.get('local_monitor', {}).get('mode', 'github') == 'github':
        if cfg.get('provider', {}).get('type') != 'tradingview_mcp':
            raise ValueError('provider.type must be tradingview_mcp in github mode')
    return cfg
