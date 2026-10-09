# Created: 2026-10-09 22:09 JST
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import json
import pandas as pd
import numpy as np
import pytest
from src.config import load_settings, EXPECTED_TIMEFRAMES
from src.indicators import add_indicators
from src.providers import DemoProvider, parse_mcp_response, resample_8h
from src.main import generate
from src.local_download import find_batch_folder
from scripts.cleanup_artifacts import is_expired

SETTINGS = Path(__file__).parent.parent / 'setting.yaml'

def test_config():
    cfg = load_settings(SETTINGS)
    assert len(EXPECTED_TIMEFRAMES) == 9
    assert cfg['chart']['ema'] == [20,30,40]
    assert cfg['chart']['rci'] == [9,14,26]
    assert cfg['output']['retention_hours'] == 8

def test_rci_and_ema():
    df = DemoProvider().get('FX:USDJPY', '1H', 120)
    out = add_indicators(df)
    assert all(c in out for c in ['EMA20','EMA30','EMA40','RCI9','RCI14','RCI26'])
    assert out['RCI26'].dropna().between(-100.00001,100.00001).all()
    increasing = df.copy(); increasing['Close'] = range(120)
    assert add_indicators(increasing)['RCI9'].iloc[-1] == pytest.approx(100)

def test_8h_pair_aggregation_and_drop_incomplete():
    idx = pd.date_range('2026-10-01', periods=5, freq='4h', tz='UTC')
    df = pd.DataFrame({'Open':[1,2,3,4,5], 'High':[2,3,4,5,6], 'Low':[0,1,2,3,4],
                       'Close':[1.5,2.5,3.5,4.5,5.5], 'Volume':[10]*5}, index=idx)
    out = resample_8h(df)
    assert len(out) == 2
    assert out.iloc[0]['Open'] == 1 and out.iloc[0]['Close'] == 2.5
    assert out.iloc[0]['High'] == 3 and out.iloc[0]['Low'] == 0
    assert out.iloc[0]['Volume'] == 20

def test_mcp_parser():
    bars = [{'t': 1791504000, 'o':1, 'h':2, 'l':.5, 'c':1.5, 'v':50}]
    result = SimpleNamespace(structuredContent=None, content=[SimpleNamespace(text=json.dumps({'bars':bars}))])
    got = parse_mcp_response(result)
    assert len(got) == 1 and got.index.tz is not None

def test_artifact_folder_discovery(tmp_path):
    d = tmp_path / '20261009_2200'; d.mkdir()
    (d/'USDJPY.png').write_bytes(b'PNG')
    assert find_batch_folder(tmp_path, ['USDJPY']) == d
    with pytest.raises(ValueError): find_batch_folder(tmp_path, ['EURUSD'])

def test_cleanup_age():
    now = datetime(2026,10,9,12,0,tzinfo=timezone.utc)
    assert is_expired('2026-10-09T04:00:00Z', now)
    assert not is_expired('2026-10-09T05:00:00Z', now)

def test_live_is_disabled():
    with pytest.raises(RuntimeError, match='disabled'):
        generate(SETTINGS, timestamp='20261009_2200')

def test_render_offline(tmp_path):
    # One-pair temporary config avoids unnecessary images in a unit test.
    import yaml
    cfg = load_settings(SETTINGS)
    cfg['symbols'] = cfg['symbols'][:1]
    cfg['chart']['dpi'] = 45
    cfg['chart']['figsize'] = [12, 16]
    tmpcfg = tmp_path/'setting.yaml'; tmpcfg.write_text(yaml.safe_dump(cfg), encoding='utf-8')
    out = generate(tmpcfg, timestamp='20261009_2200', demo=True, output_override=tmp_path/'output')
    assert len(out) == 1 and out[0].name == 'USDJPY.png'
    from PIL import Image
    with Image.open(out[0]) as im:
        assert im.format == 'PNG'
        assert im.width > 400 and im.height > 400
