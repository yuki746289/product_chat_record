# Created: 2026-10-10 10:39 JST
"""Windows system-tray watcher for Chart Recorder (no global background daemon)."""
import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import sys
import threading
import time

from .config import load_settings
from .local_monitor import get_monitor_options, poll_once

APP_NAME = "ChartRecorder"
REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def default_config():
    # A PyInstaller executable reads editable setting.yaml beside the EXE.
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    return base / "setting.yaml"


def _startup_command(config_path):
    if os.name != "nt" or not getattr(sys, "frozen", False):
        raise RuntimeError("Autostart registration requires a Windows-built executable")
    return f'"{Path(sys.executable).resolve()}" --config "{Path(config_path).resolve()}"'


def is_autostart_enabled():
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
            return bool(winreg.QueryValueEx(key, APP_NAME)[0])
    except FileNotFoundError:
        return False


def set_autostart(config_path, enabled):
    import winreg
    if enabled:
        command = _startup_command(config_path)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
    else:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass


def _icon_image():
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (64, 64), "#131722")
    draw = ImageDraw.Draw(img)
    draw.rectangle((7, 9, 57, 49), outline="#d1d4dc", width=3)
    draw.line([(14, 42), (25, 32), (34, 37), (46, 22), (54, 18)], fill="#089981", width=4)
    draw.rectangle((26, 51, 38, 55), fill="#d1d4dc")
    return img


class TrayController:
    def __init__(self, config_path):
        self.config_path = Path(config_path).resolve()
        config = load_settings(self.config_path)
        self.interval, _, _ = get_monitor_options(config)
        self.local_dir = Path(config["output"]["local_dir"])
        self.stopping = threading.Event()
        self.wake = threading.Event()
        self.paused = False
        self.status = "起動中"
        self.icon = None
        self.worker = None
        self.local_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("chart_recorder")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = RotatingFileHandler(self.local_dir / ".chart_recorder.log", maxBytes=1_000_000,
                                          backupCount=2, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(handler)

    def _status(self, value):
        self.status = value
        if self.icon:
            self.icon.update_menu()

    def poll_loop(self):
        while not self.stopping.is_set():
            if not self.paused:
                try:
                    self._status("GitHub確認中")
                    result = poll_once(self.config_path)
                    if result:
                        self._status(f"取得完了（{len(result)}回分）")
                        self.logger.info("Downloaded %s snapshots", len(result))
                    else:
                        self._status("最新データ取得済み")
                except Exception:
                    self.logger.exception("Polling error")
                    self._status("エラー（ログを確認）")
            self.wake.wait(self.interval)
            self.wake.clear()

    def run(self):
        if not shutil.which("gh"):
            raise RuntimeError("GitHub CLI (gh) is missing. Install it and run gh auth login.")
        import pystray
        self.icon = pystray.Icon(APP_NAME, _icon_image(), "Chart Recorder")
        self.icon.menu = pystray.Menu(
            pystray.MenuItem(lambda _: f"状態: {self.status}", None, enabled=False),
            pystray.MenuItem("今すぐ確認", lambda icon, item: self.wake.set()),
            pystray.MenuItem("監視を一時停止", self.toggle_pause, checked=lambda _: self.paused),
            pystray.MenuItem("保存先を開く", self.open_folder),
            pystray.MenuItem("Windowsログオン時に起動", self.toggle_autostart,
                             checked=lambda _: is_autostart_enabled(),
                             enabled=lambda _: os.name == "nt" and getattr(sys, "frozen", False)),
            pystray.MenuItem("終了", self.stop),
        )
        self.worker = threading.Thread(target=self.poll_loop, name="GitHubChartPolling", daemon=True)
        self.worker.start()
        try:
            self.icon.run()
        finally:
            self.stopping.set()
            self.wake.set()
            self.worker.join(timeout=5)

    def toggle_pause(self, icon, item):
        self.paused = not self.paused
        if self.paused:
            self._status("一時停止中")
        else:
            self.wake.set()

    def open_folder(self, icon, item):
        if os.name == "nt":
            os.startfile(str(self.local_dir))

    def toggle_autostart(self, icon, item):
        try:
            set_autostart(self.config_path, not is_autostart_enabled())
        except Exception:
            self.logger.exception("Autostart update failed")
            self._status("自動起動設定エラー")

    def stop(self, icon, item):
        self.stopping.set()
        self.wake.set()
        icon.stop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(default_config()))
    args = parser.parse_args()
    TrayController(args.config).run()


if __name__ == "__main__":
    main()
