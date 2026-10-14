# Created: 2026-10-10 10:39 JST
# Updated: 2026-10-10 JST (argument-free EXE config discovery)
# Updated: 2026-10-12 JST (Saxo re-login notification and recovery)
# Updated: 2026-10-14 JST (make tray icon visible in custom pystray setup)
# Updated: 2026-10-14 JST (friendly single-instance dialog and cooperative restart)
# Updated: 2026-10-14 JST (hold Saxo mutex through polling and login shutdown)
# Updated: 2026-10-14 JST (first-run Saxo App Key/Secret UI without requiring Python)
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
from .saxo_local import tick_once
from .saxo_auth import SaxoSession, SaxoLoginRequired
from .saxo_first_run import ensure_app_credentials
from .windows_single_instance import WindowsSingleInstance

APP_NAME = "ChartRecorder"
REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def default_config():
    """Locate the editable configuration without requiring --config.

    A packaged EXE is built at <repo>/dist/ChartRecorder.exe. It must read
    <repo>/setting.yaml, not a potentially outdated dist/setting.yaml copy.
    A standalone executable outside a dist directory uses a neighboring file.
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if exe_dir.name.lower() == "dist":
            return exe_dir.parent / "setting.yaml"
        return exe_dir / "setting.yaml"
    return Path(__file__).resolve().parents[1] / "setting.yaml"


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
        self.interval, _ = get_monitor_options(config)
        self.mode = config.get("local_monitor", {}).get("mode", "github")
        if self.mode not in ("github", "saxo_local"):
            raise ValueError("local_monitor.mode must be github or saxo_local")
        self.local_dir = Path(config["output"]["local_dir"])
        self.stopping = threading.Event()
        self.wake = threading.Event()
        self.paused = False
        self.login_required = False
        self.login_in_progress = False
        self.auth_notice_sent = False
        self.status = "起動中"
        self.icon = None
        self.single_instance_handle = None
        self.kernel32 = None
        self.instance_guard = None
        self.instance_watcher = None
        self.worker = None
        self.login_worker = None
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

    def _signal_saxo_login_required(self):
        """Show the Windows notification once, keeping tray status visible."""
        if not self.login_required:
            # Tokens are never logged; no repeated tracebacks every minute.
            self.logger.warning("Saxo re-login required; use the tray menu to authenticate")
            self.login_required = True
        self._status("Saxo再ログインが必要（右クリック）")
        if not self.auth_notice_sent and self.icon is not None:
            try:
                self.icon.notify(
                    "Saxo認証が期限切れです。ChartRecorderを右クリックして「Saxoに再ログイン」を選んでください。",
                    "ChartRecorder：再ログインが必要",
                )
                self.auth_notice_sent = True
            except Exception:
                # Windows notifications can be disabled; tray menu still works.
                pass

    def poll_loop(self):
        while not self.stopping.is_set():
            if self.login_required:
                # Retry notice only if Windows was unable to show it earlier.
                if not self.login_in_progress:
                    self._signal_saxo_login_required()
            elif not self.paused:
                try:
                    if self.mode == "saxo_local":
                        self._status("Saxo確認中")
                        result = tick_once(self.config_path)
                        if result:
                            self._status(f"画像生成完了（{len(result)}通貨ペア）")
                            self.logger.info("Generated %s Saxo chart images", len(result))
                        else:
                            self._status("次の更新待機中／市場休場")
                    else:
                        self._status("GitHub確認中")
                        result = poll_once(self.config_path)
                        if result:
                            self._status(f"取得完了（{len(result)}回分）")
                            self.logger.info("Downloaded %s snapshots", len(result))
                        else:
                            self._status("最新データ取得済み")
                except SaxoLoginRequired:
                    self._signal_saxo_login_required()
                except Exception:
                    self.logger.exception("Polling error")
                    self._status("エラー（ログを確認）")
            self.wake.wait(self.interval)
            self.wake.clear()

    def run(self):
        if os.name == "nt":
            # Single-instance protection is mandatory: simultaneous Saxo
            # OAuth refresh-token rotation can invalidate both processes.
            guard = WindowsSingleInstance()
            if not guard.acquire():
                # User cancelled, or the old version cannot stop cooperatively.
                # No fatal PyInstaller traceback/dialog should be shown.
                return
            self.instance_guard = guard
        if self.mode == "github" and not shutil.which("gh"):
            raise RuntimeError("GitHub CLI (gh) is missing. Install it and run gh auth login.")
        import pystray
        self.icon = pystray.Icon(APP_NAME, _icon_image(), "Chart Recorder")
        self.icon.menu = pystray.Menu(
            pystray.MenuItem(lambda _: f"状態: {self.status}", None, enabled=False),
            pystray.MenuItem("今すぐ確認", lambda icon, item: self.wake.set()),
            pystray.MenuItem("監視を一時停止", self.toggle_pause, checked=lambda _: self.paused),
            pystray.MenuItem(
                lambda _: "Saxoに再ログイン【必要】" if self.login_required else "Saxoに再ログイン",
                self.start_saxo_login,
                enabled=lambda _: self.mode == "saxo_local" and not self.login_in_progress,
            ),
            pystray.MenuItem("保存先を開く", self.open_folder),
            pystray.MenuItem("Windowsログオン時に起動", self.toggle_autostart,
                             checked=lambda _: is_autostart_enabled(),
                             enabled=lambda _: os.name == "nt" and getattr(sys, "frozen", False)),
            pystray.MenuItem("終了", self.stop),
        )
        if getattr(self, "instance_guard", None) is not None:
            self.instance_watcher = threading.Thread(
                target=self.instance_guard.watch_for_stop,
                args=(self._request_restart_stop, self.stopping),
                name="ChartRestartListener", daemon=True,
            )
            self.instance_watcher.start()
        try:
            # A custom pystray setup callback MUST explicitly show the icon.
            # Without this, polling runs but Windows has no tray entry to access.
            self.icon.run(setup=self._on_tray_ready)
        finally:
            self.stopping.set()
            self.wake.set()
            # Never release the Saxo mutex while either worker can still access
            # the credential vault or API. A capture may take over five seconds;
            # the replacement launcher will time out safely if shutdown is slow.
            if self.worker is not None:
                self.worker.join()
            if getattr(self, "login_worker", None) is not None:
                self.login_worker.join()
            if getattr(self, "instance_watcher", None) is not None:
                self.instance_watcher.join(timeout=1)
            if getattr(self, "instance_guard", None) is not None:
                self.instance_guard.close()

    def _request_restart_stop(self):
        """Cooperatively exit after a new launcher requests replacement."""
        self.logger.info("Restart requested by a new ChartRecorder launcher")
        self.stopping.set()
        self.wake.set()
        if self.icon is not None:
            self.icon.stop()

    def _on_tray_ready(self, icon):
        """Show the Windows notification-area icon BEFORE starting polling.

        pystray's default setup sets visible=True, but supplying our own
        setup callback replaces that default. Never leave a hidden daemon if
        Windows rejects icon registration.
        """
        try:
            icon.visible = True
        except Exception:
            self.logger.exception("Tray icon could not be displayed; stopping ChartRecorder")
            self.stopping.set()
            icon.stop()
            return
        self.logger.info("Tray icon initialized and visible; mode=%s", self.mode)
        if not self.stopping.is_set():
            self.worker = threading.Thread(
                target=self.poll_loop, name="ChartLocalPolling", daemon=True
            )
            self.worker.start()

    def start_saxo_login(self, icon, item):
        if self.mode != "saxo_local" or self.login_in_progress:
            return
        self.login_in_progress = True
        self.paused = True
        self._status("Saxo再ログイン中（ブラウザで認証）")
        # Browser login must never block the tray UI thread.
        self.login_worker = threading.Thread(
            target=self._run_saxo_login, daemon=True, name="SaxoBrowserLogin"
        )
        self.login_worker.start()

    def _run_saxo_login(self):
        try:
            cfg = load_settings(self.config_path)
            # A new PC has no Saxo app credentials in its Windows vault.
            # Show a masked first-run dialog from this worker (never the tray
            # event loop), then keep the existing browser-based Saxo login.
            if not ensure_app_credentials(cfg["saxo"]["environment"]):
                self._status("Saxo初期設定をキャンセル（右クリックして再試行）")
                return
            session = SaxoSession(cfg)
            session.sign_in_interactively()
            self.login_required = False
            self.auth_notice_sent = False
            self._status("Saxo認証完了（画像取得を再開）")
            self.logger.info("Saxo OAuth login completed; chart polling resumes")
        except Exception:
            self.logger.exception("Saxo browser login failed")
            if self.login_required:
                self._status("Saxo再ログイン失敗（右クリックして再試行）")
            else:
                self._status("Saxo認証失敗（ログを確認）")
        finally:
            self.login_in_progress = False
            self.paused = False
            # Wake the polling loop now rather than wait for its next interval.
            self.wake.set()

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
