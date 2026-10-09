# Created: 2026-10-09 22:09 JST
"""Demo generator and official TradingView MCP data adapter.

Production auth is intentionally disabled until terms and OAuth token renewal
for unattended GitHub Actions use have been verified and authorized.
"""
import json
import os
import numpy as np
import pandas as pd

INTERVALS = {
    '1M': '1m', '5M': '5m', '15M': '15m', '1H': '1h',
    '4H': '4h', '1D': '1D', '1W': '1W', '1Mn': 'M',
}
FREQUENCIES = {
    '1M': '1min', '5M': '5min', '15M': '15min', '1H': '1h',
    '4H': '4h', '8H': '8h', '1D': '1D', '1W': '7D', '1Mn': '30D',
}
REQUIRED_COLUMNS = ('Open', 'High', 'Low', 'Close', 'Volume')


def validate_bars(df):
    if not isinstance(df.index, pd.DatetimeIndex) or df.index.tz is None:
        raise ValueError('OHLCV must have timezone-aware DatetimeIndex')
    if any(col not in df.columns for col in REQUIRED_COLUMNS):
        raise ValueError('OHLCV columns missing')
    df = df.loc[:, list(REQUIRED_COLUMNS)].sort_index()
    if df.index.has_duplicates or df.empty or df.isna().any().any():
        raise ValueError('OHLCV contains duplicate timestamps, missing data or no data')
    if ((df['High'] < df[['Open','Close','Low']].max(axis=1)) | (df['Low'] > df[['Open','Close','High']].min(axis=1))).any():
        raise ValueError('OHLCV price relationships invalid')
    return df.astype(float)


def parse_mcp_response(result):
    """Read MCP tool result structuredContent or a JSON text block."""
    structured = getattr(result, 'structuredContent', None)
    if structured is not None:
        payload = structured
    else:
        parts = [getattr(x, 'text', None) for x in getattr(result, 'content', [])]
        parts = [p for p in parts if p]
        if not parts:
            raise ValueError('MCP response has no parseable content')
        payload = json.loads(parts[0])
    if isinstance(payload, dict) and 'result' in payload and isinstance(payload['result'], dict):
        payload = payload['result']
    bars = payload if isinstance(payload, list) else payload.get('bars', payload.get('data'))
    if not isinstance(bars, list) or not bars:
        raise ValueError('MCP response does not contain non-empty OHLCV bars; check live response schema')
    df = pd.DataFrame(bars)
    df = df.rename(columns={'o':'Open','h':'High','l':'Low','c':'Close','v':'Volume'})
    if 't' not in df.columns:
        raise ValueError('OHLCV bars lack UTC Unix time field t')
    df.index = pd.to_datetime(df.pop('t'), unit='s', utc=True)
    if 'Volume' not in df.columns:
        df['Volume'] = 0.0
    return validate_bars(df)


def resample_8h(bars_4h):
    """Construct full UTC-anchored 8h bars from pairs of 4h bars.

    TradingView 8H may use another session anchor; compare before production.
    """
    df = validate_bars(bars_4h).tz_convert('UTC')
    rs = df.resample('8h', origin='epoch', label='left', closed='left')
    agg = rs.agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'})
    sizes = rs.size()
    # Do not mix periods with missing constituent 4h bars.
    return validate_bars(agg.loc[sizes == 2])


class DemoProvider:
    """Deterministic SYNTHETIC bars for offline layout tests only."""
    def get(self, symbol, timeframe, count):
        import hashlib
        seed = int.from_bytes(hashlib.sha256(f'{symbol}:{timeframe}'.encode()).digest()[:4], 'little')
        rng = np.random.default_rng(seed)
        period = FREQUENCIES[timeframe]
        # End at fixed bar to make tests reproducible.
        end = pd.Timestamp('2026-10-09 00:00:00', tz='UTC')
        dates = pd.date_range(end=end, periods=count, freq=period, tz='UTC')
        scale = 0.25 if 'JPY' in symbol else 0.003
        mid = 140.0 if 'JPY' in symbol else 1.20
        prices = mid + np.cumsum(rng.normal(0, scale, size=count))
        open_ = np.r_[prices[0], prices[:-1]]
        high = np.maximum(open_, prices) + rng.uniform(0, scale / 1.5, count)
        low = np.minimum(open_, prices) - rng.uniform(0, scale / 1.5, count)
        return validate_bars(pd.DataFrame({'Open':open_,'High':high,'Low':low,'Close':prices,
            'Volume':rng.integers(100, 500, count)}, index=dates))


class TradingViewMcpProvider:
    """MCP client using preauthorized OAuth bearer access token.

    No hidden credential harvesting, scraping, or token-refresh workarounds.
    Actual live auth and result schema require provider-side verification.
    """
    def __init__(self, url):
        self.url = url
        self.token = os.getenv('TRADINGVIEW_MCP_ACCESS_TOKEN', '')
        if not self.token:
            raise RuntimeError('TRADINGVIEW_MCP_ACCESS_TOKEN is not configured; live mode is disabled')

    async def get_async(self, symbol, timeframe, count):
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client
        except ImportError as exc:
            raise RuntimeError('Install requirements.txt to use TradingView MCP') from exc
        headers = {'Authorization': f'Bearer {self.token}'}
        async with streamablehttp_client(self.url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool('get_ohlcv', arguments={
                    'symbol':symbol, 'interval':INTERVALS[timeframe], 'count':count, 'summary':False
                })
                if result.isError:
                    raise RuntimeError(f'TradingView MCP get_ohlcv failed: {symbol} {timeframe}')
                return parse_mcp_response(result)

    def get(self, symbol, timeframe, count):
        import asyncio
        return asyncio.run(self.get_async(symbol, timeframe, count))
