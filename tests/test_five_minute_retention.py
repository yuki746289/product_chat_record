# Created: 2026-10-14 JST
"""Tests for the 5-minute Saxo schedule, 10-folder limit, and aligned YAML."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import re

import pandas as pd
import pytest
import yaml

from src import saxo_local
from src.config import load_settings
from src.local_monitor import clean_local_images, get_monitor_options
from src.providers import DemoProvider

ROOT = Path(__file__).resolve().parents[1]


def test_five_minute_and_ten_folder_defaults():
    cfg = load_settings(ROOT / "setting.yaml")
    assert cfg["local_monitor"] == {
        "mode": "saxo_local",
        "poll_seconds": 60,
        "chart_interval_minutes": 5,
        "max_folders": 10,
    }
    assert get_monitor_options(cfg) == (60, 10)
    assert saxo_local.get_saxo_config(cfg)[1] == 5
    assert "retention_hours" not in cfg["output"]


def test_legacy_time_retention_and_bad_limits_are_rejected():
    cfg = load_settings(ROOT / "setting.yaml")
    for extra in ({"min_folders": 16}, {"retention_hours": 8}):
        bad = {**cfg, "local_monitor": {**cfg["local_monitor"], **extra}}
        with pytest.raises(ValueError, match="Deprecated"):
            get_monitor_options(bad)
    for limit in (0, -1, True, 5.0, "10", 1001):
        bad = {**cfg, "local_monitor": {**cfg["local_monitor"], "max_folders": limit}}
        with pytest.raises(ValueError, match="max_folders"):
            get_monitor_options(bad)
    for period in (3, True, 5.0, "5"):
        bad = {**cfg, "local_monitor": {**cfg["local_monitor"], "chart_interval_minutes": period}}
        with pytest.raises(ValueError, match="chart_interval_minutes"):
            saxo_local.get_saxo_config(bad)
    cfg["local_monitor"]["chart_interval_minutes"] = 30
    assert saxo_local.get_saxo_config(cfg)[1] == 30


def test_yaml_colons_aligned_and_each_scalar_has_description():
    lines = (ROOT / "setting.yaml").read_text(encoding="utf-8").splitlines()
    section = None
    positions = {}
    for line in lines:
        if re.fullmatch(r"[a-z_]+:", line):
            section = line[:-1]
            continue
        if line.startswith("  - ") or not line.startswith("  ") or line.strip().startswith("#"):
            continue
        if section not in {"provider", "market", "chart", "output", "saxo", "local_monitor"}:
            continue
        match = re.match(r"  ([a-z_]+)(\s*):", line)
        if not match:
            continue
        positions.setdefault(section, set()).add(line.index(":"))
        assert "#" in line, (section, line)
    for section in ("provider", "market", "chart", "output", "saxo", "local_monitor"):
        assert len(positions.get(section, ())) == 1, section


def _source(now, stale=False):
    class Source:
        session = SimpleNamespace(access_token=lambda: "FAKE")
        calls = 0

        def get(self, pair, tf, count):
            self.calls += 1
            df = DemoProvider().get("FX:" + pair, tf, count)
            if tf == "1M":
                end = now - timedelta(minutes=100 if stale else 2)
                df.index = pd.date_range(end=end, periods=len(df), freq="min", tz="UTC")
            return df
    return Source()


def test_five_minute_capture_and_dedupe_with_categories(tmp_path, monkeypatch):
    cfg = load_settings(ROOT / "setting.yaml")
    cfg["output"]["local_dir"] = str(tmp_path / "charts")
    cfg["symbols"] = [cfg["symbols"][0], cfg["symbols"][7]]
    cp = tmp_path / "setting.yaml"
    cp.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    def fake_render(data, pair, dest, settings, timestamp, **kwargs):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"\x89PNG\r\n\x1a\nFAKE")
        return dest
    monkeypatch.setattr(saxo_local, "render_pair", fake_render)
    now = datetime(2026, 10, 14, 0, 2, tzinfo=timezone.utc)
    provider = _source(now)
    first = saxo_local.tick_once(cp, now=now, provider=provider)
    assert len(first) == 2
    assert provider.calls == 18
    assert (tmp_path / "charts" / "20261014_0900" / "cross_non_jpy" / "GBPAUD.png").exists()
    assert (tmp_path / "charts" / "20261014_0900" / "cross_jpy" / "AUDJPY.png").exists()

    assert saxo_local.tick_once(cp, now + timedelta(minutes=1), provider=provider) == []
    assert provider.calls == 18
    next_now = now + timedelta(minutes=3)
    second = saxo_local.tick_once(cp, next_now, provider=_source(next_now))
    assert len(second) == 2
    assert all(path.parent.parent.name == "20261014_0905" for path in second)


def test_folder_cleanup_at_exact_boundary_preserves_10(tmp_path):
    now = datetime(2026, 10, 14, 2, tzinfo=timezone.utc)
    snaps = []
    for i in range(11):
        folder = tmp_path / (now - timedelta(minutes=5 * (10 - i))).strftime("%Y%m%d_%H%M")
        subdir = folder / ("cross_jpy" if i % 2 else "cross_non_jpy")
        subdir.mkdir(parents=True)
        (subdir / "USDJPY.png").write_bytes(b"PNG")
        snaps.append(folder)
    other = tmp_path / "notes"
    other.mkdir()
    (other / "keep.txt").write_text("important", encoding="utf-8")
    ignored = tmp_path / "20200101_0000"
    ignored.mkdir()
    assert clean_local_images(tmp_path, now, 10, "UTC") == [snaps[0]]
    assert sum(f.exists() for f in snaps) == 10
    assert other.exists() and ignored.exists()
    assert clean_local_images(tmp_path, now, 10, "UTC") == []


def test_closed_market_does_not_discard_latest_ten(tmp_path):
    now = datetime(2026, 10, 14, 0, tzinfo=timezone.utc)
    snaps = []
    for i in range(10):
        folder = tmp_path / (now - timedelta(days=i + 1)).strftime("%Y%m%d_%H%M")
        folder.mkdir()
        (folder / "USDJPY.png").write_bytes(b"PNG")
        snaps.append(folder)
    assert clean_local_images(tmp_path, now, 10, "UTC") == []
    assert all(p.exists() for p in snaps)
