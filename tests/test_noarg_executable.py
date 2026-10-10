# Created: 2026-10-10 JST
"""Test argument-free ChartRecorder default setting resolution."""
from pathlib import Path

from src import tray_app


def test_frozen_exe_in_dist_uses_repo_settings_even_if_stale_copy_exists(tmp_path, monkeypatch):
    repo = tmp_path / "product_chat_record"
    dist = repo / "dist"
    dist.mkdir(parents=True)
    (repo / "setting.yaml").write_text("saxo: {enabled: true}\n", encoding="utf-8")
    (dist / "setting.yaml").write_text("saxo: {enabled: false}\n", encoding="utf-8")
    monkeypatch.setattr(tray_app.sys, "frozen", True, raising=False)
    monkeypatch.setattr(tray_app.sys, "executable", str(dist / "ChartRecorder.exe"))
    assert tray_app.default_config() == repo / "setting.yaml"


def test_packaged_standalone_exe_can_use_adjacent_config(tmp_path, monkeypatch):
    folder = tmp_path / "portable"
    folder.mkdir()
    monkeypatch.setattr(tray_app.sys, "frozen", True, raising=False)
    monkeypatch.setattr(tray_app.sys, "executable", str(folder / "ChartRecorder.exe"))
    assert tray_app.default_config() == folder / "setting.yaml"


def test_python_module_uses_repository_config_regardless_of_cwd(tmp_path, monkeypatch):
    monkeypatch.setattr(tray_app.sys, "frozen", False, raising=False)
    monkeypatch.chdir(tmp_path)
    assert tray_app.default_config() == Path(tray_app.__file__).resolve().parents[1] / "setting.yaml"
