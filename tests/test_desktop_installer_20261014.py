# Created: 2026-10-14 JST
"""Installer safety and portable output regression tests (no real Windows writes)."""
from pathlib import Path
from types import SimpleNamespace
import re

import pytest
import yaml

from scripts import setup_chartrecorder as setup
from src.config import load_settings


def make_payload(tmp_path):
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "ChartRecorder.exe").write_bytes(b"MZ-test-executable")
    (payload / "setting.yaml").write_text(
        (Path(__file__).resolve().parents[1] / "setting.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    system = tmp_path / "system.yaml"
    system.write_text(
        "install:\n  location: desktop\n  folder_name: ChartRecorder\n  image_folder: chart_image\n",
        encoding="utf-8",
    )
    return payload, system


def test_install_to_desktop_copies_runtime_and_resolves_portable_image_path(tmp_path):
    payload, system = make_payload(tmp_path)
    desktop = tmp_path / "OneDrive" / "Desktop"
    desktop.mkdir(parents=True)
    dest = setup.perform_install(payload, system, desktop=desktop)
    assert dest == (desktop / "ChartRecorder").resolve()
    assert (dest / "ChartRecorder.exe").read_bytes() == b"MZ-test-executable"
    assert (dest / "chart_image").is_dir()
    assert (dest / "system.yaml").is_file()
    cfg = load_settings(dest / "setting.yaml")
    assert cfg["output"]["local_dir"] == str(dest / "chart_image")
    assert len(cfg["symbols"]) == 13
    assert cfg["chart"]["ema"] == [20, 30, 40]
    assert cfg["chart"]["rci"] == [9, 14, 26]
    assert cfg["local_monitor"]["chart_interval_minutes"] == 5
    assert cfg["local_monitor"]["max_folders"] == 10


def test_upgrade_keeps_custom_settings_images_and_existing_history(tmp_path):
    payload, system = make_payload(tmp_path)
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    dest = setup.perform_install(payload, system, desktop=desktop)
    path = dest / "setting.yaml"
    current = path.read_text(encoding="utf-8")
    current = current.replace("  poll_seconds           : 60", "  poll_seconds           : 90")
    current = current.replace("'chart_image'  # relative", "'C:/TradingViewCharts'  # relative")
    path.write_text(current, encoding="utf-8")
    snapshot = dest / "chart_image" / "20261014_1600" / "cross_jpy"
    snapshot.mkdir(parents=True)
    (snapshot / "USDJPY.png").write_bytes(b"PNG HISTORY")
    (payload / "ChartRecorder.exe").write_bytes(b"MZ-new-version")
    again = setup.perform_install(payload, system, desktop=desktop)
    assert again == dest
    assert (dest / "ChartRecorder.exe").read_bytes() == b"MZ-new-version"
    assert (snapshot / "USDJPY.png").read_bytes() == b"PNG HISTORY"
    text = path.read_text(encoding="utf-8")
    assert "poll_seconds           : 90" in text
    assert yaml.safe_load(text)["output"]["local_dir"] == "chart_image"
    assert list(dest.glob("setting.yaml.before-setup-*.bak"))


def test_invalid_install_paths_rejected(tmp_path):
    desktop = tmp_path / "Desktop"
    for name in ("..", "../other", "Bad\\name", "bad:name", ""):
        with pytest.raises(ValueError):
            setup.resolve_install({"location": "desktop", "folder_name": name}, desktop=desktop)
    with pytest.raises(ValueError):
        setup.resolve_install({"location": "relative/path"}, desktop=desktop)
    with pytest.raises(ValueError):
        setup.resolve_install({"location": "desktop", "image_folder": "../outside"}, desktop=desktop)


def test_current_repo_absolute_output_remains_unchanged():
    cfg = load_settings(Path(__file__).resolve().parents[1] / "setting.yaml")
    assert cfg["output"]["local_dir"] == "C:/TradingViewCharts"


def test_installer_does_not_write_credentials_and_never_copies_old_history(tmp_path):
    payload, system = make_payload(tmp_path)
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    dest = setup.perform_install(payload, system, desktop=desktop)
    for filename in ("system.yaml", "setting.yaml"):
        text = (dest / filename).read_text(encoding="utf-8")
        assert "access_token:" not in text
        assert "refresh_token:" not in text
        assert "app_secret:" not in text
    assert list((dest / "chart_image").iterdir()) == []


def test_running_exe_cannot_be_overwritten_without_leaving_temp(tmp_path, monkeypatch):
    payload, system = make_payload(tmp_path)
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    dest = setup.perform_install(payload, system, desktop=desktop)
    previous = (dest / "ChartRecorder.exe").read_bytes()
    original = setup.os.replace

    def locked(src, dst):
        if str(dst).endswith("ChartRecorder.exe"):
            raise PermissionError("in use")
        return original(src, dst)

    monkeypatch.setattr(setup.os, "replace", locked)
    with pytest.raises(RuntimeError, match="Exit it from the tray"):
        setup.perform_install(payload, system, desktop=desktop)
    assert (dest / "ChartRecorder.exe").read_bytes() == previous
    assert not (dest / "ChartRecorder.exe.install-tmp").exists()
