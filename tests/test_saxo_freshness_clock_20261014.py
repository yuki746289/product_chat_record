# Created: 2026-10-14 JST
"""Reproduce late-pair freshness drift without network calls or Saxo credentials."""
from datetime import datetime, timedelta, timezone
import logging
from types import SimpleNamespace

import pandas as pd
import yaml

from src import saxo_local
from src.config import load_settings
from src.providers import DemoProvider


def make_config(tmp_path):
    cfg = load_settings("setting.yaml")
    cfg["symbols"] = [
        next(x for x in cfg["symbols"] if x["pair"] == "GBPAUD"),
        next(x for x in cfg["symbols"] if x["pair"] == "USDJPY"),
    ]
    cfg["output"]["local_dir"] = str(tmp_path / "output")
    path = tmp_path / "setting.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return path


class FakeSaxo:
    session = SimpleNamespace(access_token=lambda: "FAKE")
    def __init__(self, times):
        self.times = times
        self.calls = []

    def get(self, pair, timeframe, count):
        self.calls.append((pair, timeframe))
        bars = DemoProvider().get("FX:" + pair, timeframe, count)
        if timeframe == "1M":
            bars.index = pd.date_range(
                end=self.times[pair], periods=len(bars), freq="min", tz="UTC"
            )
        return bars


def render_png(frames, pair, path, cfg, stamp, **kwargs):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\\x89PNG\\r\\n\\x1a\\nFAKE")
    return path


def test_late_usdjpy_is_not_discarded_as_future_data(tmp_path, monkeypatch):
    config = make_config(tmp_path)
    monkeypatch.setattr(saxo_local, "render_pair", render_png)
    base = datetime(2026, 10, 14, 6, 15, 30, tzinfo=timezone.utc)
    late = base + timedelta(seconds=90)
    clock_values = iter([base, base + timedelta(seconds=5), late])
    src = FakeSaxo({
        "GBPAUD": base + timedelta(seconds=2),
        "USDJPY": late - timedelta(seconds=2),
    })

    images = saxo_local.tick_once(
        config, provider=src, clock=lambda: next(clock_values)
    )
    assert len(images) == 2
    assert {p.name for p in images} == {"GBPAUD.png", "USDJPY.png"}
    assert all(p.parent.parent.name == "20261014_1515" for p in images)
    assert len(src.calls) == 18


def test_genuinely_stale_usdjpy_is_skipped_with_safe_diagnostics(
    tmp_path, monkeypatch, caplog
):
    config = make_config(tmp_path)
    monkeypatch.setattr(saxo_local, "render_pair", render_png)
    base = datetime(2026, 10, 14, 6, 15, 30, tzinfo=timezone.utc)
    late = base + timedelta(seconds=90)
    clock_values = iter([base, base + timedelta(seconds=5), late])
    src = FakeSaxo({
        "GBPAUD": base,
        "USDJPY": base - timedelta(minutes=15),
    })
    with caplog.at_level(logging.WARNING, logger="chart_recorder"):
        images = saxo_local.tick_once(
            config, provider=src, clock=lambda: next(clock_values)
        )
    assert len(images) == 1
    assert images[0].name == "GBPAUD.png"
    assert "USDJPY" in caplog.text
    assert "latest_1m=" in caplog.text
    assert "checked_at=" in caplog.text
    assert "slot=20261014_1515" in caplog.text
