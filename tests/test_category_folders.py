# Created: 2026-10-10 JST
"""FX category layout and retention tests (synthetic data only)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import yaml

from src.config import load_settings
from src import saxo_local
from src.local_monitor import clean_local_images, _find_artifact_batch
from src.providers import DemoProvider

ROOT = Path(__file__).resolve().parents[1]


def test_categories_and_pair_order():
    cfg = load_settings(ROOT / "setting.yaml")
    assert [v["pair"] for v in cfg["symbols"]] == [
        "GBPAUD", "AUDUSD", "GBPUSD", "EURGBP", "USDCAD", "EURUSD", "GBPNZD",
        "AUDJPY", "GBPJPY", "USDJPY", "EURJPY", "CADJPY", "NZDJPY",
    ]
    assert [v["category"] for v in cfg["symbols"]] == ["cross_non_jpy"] * 7 + ["cross_jpy"] * 6


def test_unsafe_category_is_rejected(tmp_path):
    cfg = load_settings(ROOT / "setting.yaml")
    for value in ("../outside", "foo/bar", "", "a" * 41, None):
        cfg["symbols"][0]["category"] = value
        test_setting = tmp_path / "setting.yaml"
        test_setting.write_text(yaml.safe_dump(cfg), encoding="utf-8")
        with pytest.raises(ValueError, match="category"):
            load_settings(test_setting)


def _demo_source(now):
    class Source:
        session = SimpleNamespace(access_token=lambda: "FAKE")

        def get(self, pair, tf, count):
            data = DemoProvider().get("FX:" + pair, tf, count)
            if tf == "1M":
                data.index = pd.date_range(
                    end=now - timedelta(minutes=2), periods=len(data), freq="min", tz="UTC"
                )
            return data

    return Source()


def test_category_output_and_slot_dedupe(tmp_path, monkeypatch):
    cfg = load_settings(ROOT / "setting.yaml")
    cfg["symbols"] = [cfg["symbols"][0], cfg["symbols"][7]]
    cfg["output"]["local_dir"] = str(tmp_path / "charts")
    f = tmp_path / "setting.yaml"
    f.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    def render(bars, pair, path, cfg, timestamp, **kwargs):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x89PNG\r\n\x1a\nTEST")
        return path

    monkeypatch.setattr(saxo_local, "render_pair", render)
    now = datetime(2026, 10, 9, 6, 2, tzinfo=timezone.utc)
    images = saxo_local.tick_once(f, now=now, provider=_demo_source(now))
    assert len(images) == 2
    batch = tmp_path / "charts" / "20261009_1500"
    assert (batch / "cross_non_jpy" / "GBPAUD.png").is_file()
    assert (batch / "cross_jpy" / "AUDJPY.png").is_file()
    assert saxo_local.tick_once(f, now=now + timedelta(minutes=1), provider=_demo_source(now)) == []


def test_nested_retention_preserves_sixteen(tmp_path):
    now = datetime(2026, 10, 10, 10, tzinfo=timezone.utc)
    snapshots = []
    for i in range(20):
        folder = tmp_path / (now - timedelta(hours=20 - i)).strftime("%Y%m%d_%H%M")
        nested = folder / "cross_jpy"
        nested.mkdir(parents=True)
        (nested / "USDJPY.png").write_bytes(b"PNG")
        snapshots.append(folder)
    deleted = clean_local_images(tmp_path, now, 8, 16, "UTC")
    assert len(deleted) == 4
    assert all(not p.exists() for p in snapshots[:4])
    assert all(p.exists() for p in snapshots[4:])


def test_unrelated_folders_are_preserved(tmp_path):
    now = datetime(2026, 10, 10, 10, tzinfo=timezone.utc)
    folder = tmp_path / "20200101_0000"
    (folder / "notes").mkdir(parents=True)
    (folder / "notes" / "keep.txt").write_text("important")
    assert clean_local_images(tmp_path, now, 8, 16, "UTC") == []
    assert folder.exists()


def test_nested_artifact_image_discovery(tmp_path):
    batch = tmp_path / "20261009_1500"
    category = batch / "cross_jpy"
    category.mkdir(parents=True)
    img = category / "USDJPY.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\nTEST")
    found_batch, files = _find_artifact_batch(tmp_path, ["USDJPY", "GBPAUD"])
    assert found_batch == batch
    assert files == [img]
