# Created: 2026-10-10 10:41 JST
"""Tests for GitHub polling, partial-market artifacts and local retention."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest
import yaml

from src import local_monitor as mon
from src.local_monitor import clean_local_images, get_monitor_options, poll_once
from src.config import load_settings

SOURCE_CONFIG = Path(__file__).resolve().parents[1] / "setting.yaml"


def make_snapshot(root, dt, png=True):
    folder = root / dt.strftime("%Y%m%d_%H%M")
    folder.mkdir(parents=True, exist_ok=True)
    if png:
        (folder / "USDJPY.png").write_bytes(mon.PNG_HEADER + b"test")
    return folder


def test_cleanup_keeps_minimum_16_even_when_market_closed(tmp_path):
    now = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    snapshots = [make_snapshot(tmp_path, now - timedelta(hours=20 - n)) for n in range(20)]
    removed = clean_local_images(tmp_path, now, retention_hours=8, min_folders=16, time_zone="UTC")
    assert len(removed) == 4
    assert all(not item.exists() for item in snapshots[:4])
    assert all(item.exists() for item in snapshots[4:])


def test_cleanup_protects_all_folders_newer_than_8h(tmp_path):
    now = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    times = [now - timedelta(hours=7, minutes=n) for n in range(20)]
    times += [now - timedelta(days=n + 2) for n in range(5)]
    folders = [make_snapshot(tmp_path, t) for t in times]
    removed = clean_local_images(tmp_path, now, retention_hours=8, min_folders=16, time_zone="UTC")
    assert len(removed) == 5
    assert all(f.exists() for f in folders[:20])
    assert all(not f.exists() for f in folders[20:])


def test_cleanup_never_deletes_other_folders_or_minimum(tmp_path):
    now = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    snapshots = [make_snapshot(tmp_path, now - timedelta(days=i + 4)) for i in range(12)]
    other = tmp_path / "my_documents"
    other.mkdir()
    (other / "document.txt").write_text("safe")
    empty = make_snapshot(tmp_path, now - timedelta(days=100), png=False)
    assert clean_local_images(tmp_path, now, 8, 16, "UTC") == []
    assert all(p.exists() for p in snapshots)
    assert other.exists() and empty.exists()


def test_monitor_settings_validation():
    cfg = load_settings(SOURCE_CONFIG)
    assert get_monitor_options(cfg) == (60, 8, 16)
    for key, invalid in [("poll_seconds", 0), ("retention_hours", "8"), ("min_folders", -1)]:
        modified = {**cfg, "local_monitor": {**cfg["local_monitor"], key: invalid}}
        with pytest.raises(ValueError):
            get_monitor_options(modified)


def setup_config(tmp_path):
    cfg = load_settings(SOURCE_CONFIG)
    cfg["output"]["local_dir"] = str(tmp_path / "downloaded")
    config = tmp_path / "setting.yaml"
    config.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return config


def test_poll_backfills_in_order_and_deduplicates_and_accepts_partial(tmp_path, monkeypatch):
    config = setup_config(tmp_path)
    t0 = datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc)
    items = [{"id": 101 + i, "name": "charts", "expired": False,
              "created_at": (t0 + timedelta(minutes=i * 30)).isoformat(),
              "workflow_run": {"id": 201 + i}} for i in range(2)]
    calls = []
    def fake_gh(*args):
        if args[0] == "api":
            return json.dumps({"artifacts": list(reversed(items))})
        assert args[:2] == ("run", "download")
        calls.append(args[2])
        dest = Path(args[args.index("-D") + 1])
        stamp = "20261010_0900" if args[2] == "201" else "20261010_0930"
        folder = dest / stamp
        folder.mkdir(parents=True)
        (folder / "USDJPY.png").write_bytes(mon.PNG_HEADER + b"valid")
        if args[2] == "201":
            (folder / "EURUSD.png").write_bytes(mon.PNG_HEADER + b"valid")
        return ""
    monkeypatch.setattr(mon, "_gh", fake_gh)
    now = t0 + timedelta(hours=1)
    result = poll_once(config, now)
    assert calls == ["201", "202"]
    assert [p.name for p in result] == ["20261010_0900", "20261010_0930"]
    assert (result[1] / "USDJPY.png").exists()
    assert not (result[1] / "EURUSD.png").exists()
    assert poll_once(config, now) == []
    assert calls == ["201", "202"]
    state = json.loads((tmp_path / "downloaded" / ".downloaded_artifacts.json").read_text())
    assert state == [101, 102]


def test_failed_download_retries_without_recording_success(tmp_path, monkeypatch):
    config = setup_config(tmp_path)
    now = datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc)
    entry = {"id": 9, "name": "charts", "expired": False,
             "created_at": now.isoformat(), "workflow_run": {"id": 100}}
    attempts = 0
    def fake_gh(*args):
        nonlocal attempts
        if args[0] == "api":
            return json.dumps({"artifacts": [entry]})
        attempts += 1
        if attempts == 1:
            raise RuntimeError("network error")
        folder = Path(args[args.index("-D") + 1]) / "20261010_0900"
        folder.mkdir()
        (folder / "USDJPY.png").write_bytes(mon.PNG_HEADER + b"valid")
        return ""
    monkeypatch.setattr(mon, "_gh", fake_gh)
    with pytest.raises(RuntimeError, match="network error"):
        poll_once(config, now)
    assert not (tmp_path / "downloaded" / ".downloaded_artifacts.json").exists()
    result = poll_once(config, now)
    assert len(result) == 1
    assert attempts == 2


def test_no_artifact_still_prunes_expired_folders(tmp_path, monkeypatch):
    config = setup_config(tmp_path)
    root = tmp_path / "downloaded"
    now = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    folders = [make_snapshot(root, now - timedelta(hours=40 - i)) for i in range(20)]
    monkeypatch.setattr(mon, "_gh", lambda *args: json.dumps({"artifacts": []}))
    assert poll_once(config, now) == []
    assert not folders[0].exists() and folders[-1].exists()
