# Created: 2026-10-10 JST
"""Contract tests for the observed TradingView MCP response envelope.

All bar values are synthetic. No licensed price history or secrets are committed.
"""
import json
from types import SimpleNamespace
import pandas as pd
import pytest
from src.providers import choose_ohlcv_tool, parse_mcp_response, resample_8h, DemoProvider

MOCK_BARS = [
    {'t': 1791561600, 'o': 150.0, 'h': 151.5, 'l': 149.2, 'c': 150.5, 'v': 6000},
    {'t': 1791565200, 'o': 150.5, 'h': 151.8, 'l': 149.7, 'c': 151.0, 'v': 6001},
]


def test_mcp_rows_from_structured_content():
    payload = {'success':True,'format':'rows','interval':'1h','symbol':'FX:USDJPY',
               'has_more':True,'count':2,'bars':MOCK_BARS}
    got = parse_mcp_response(SimpleNamespace(structuredContent=payload,content=[]))
    assert len(got)==2
    assert got.index[0] == pd.Timestamp(1791561600, unit='s', tz='UTC')
    assert list(got.columns)==['Open','High','Low','Close','Volume']
    assert got.iloc[0].to_dict()=={'Open':150,'High':151.5,'Low':149.2,'Close':150.5,'Volume':6000}


def test_mcp_rows_from_json_text():
    payload={'success':True,'format':'rows','bars':MOCK_BARS,'count':2}
    response=SimpleNamespace(structuredContent=None,content=[SimpleNamespace(text=json.dumps(payload))])
    assert len(parse_mcp_response(response))==2


def test_mcp_nested_result():
    response=SimpleNamespace(structuredContent={'result':{'success':True,'bars':MOCK_BARS}},content=[])
    assert len(parse_mcp_response(response))==2


def test_mcp_success_false_is_error():
    response=SimpleNamespace(structuredContent={'success':False,'message':'unauthorized','bars':MOCK_BARS},content=[])
    with pytest.raises(RuntimeError,match='unauthorized'):
        parse_mcp_response(response)


def test_mcp_error_flag():
    response=SimpleNamespace(isError=True,structuredContent={'bars':MOCK_BARS})
    with pytest.raises(RuntimeError,match='tool error'):
        parse_mcp_response(response)


def test_mcp_missing_bars_or_timestamp():
    with pytest.raises(ValueError,match='non-empty'):
        parse_mcp_response(SimpleNamespace(structuredContent={'success':True,'bars':[]},content=[]))
    with pytest.raises(ValueError,match='Unix time'):
        parse_mcp_response(SimpleNamespace(structuredContent={'success':True,'bars':[{'o':1,'h':2,'l':.5,'c':1}]},content=[]))


def test_mcp_tool_alias_discovery():
    tool=lambda name:SimpleNamespace(name=name)
    assert choose_ohlcv_tool([tool('mcp_tv_get_ohlcv')])=='mcp_tv_get_ohlcv'
    assert choose_ohlcv_tool([tool('get_ohlcv')])=='get_ohlcv'
    assert choose_ohlcv_tool([tool('get_ohlcv'),tool('mcp_tv_get_ohlcv')])=='mcp_tv_get_ohlcv'
    with pytest.raises(RuntimeError,match='unavailable'):
        choose_ohlcv_tool([tool('get_news')])


def test_8h_offline_sample_with_incomplete_bucket():
    df=DemoProvider().get('FX:USDJPY','4H',440)
    got=resample_8h(df)
    assert len(got)==219  # An incomplete 8H bucket is intentionally dropped.
    assert got.index.tz is not None
