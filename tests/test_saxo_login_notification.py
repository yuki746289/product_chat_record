# Created: 2026-10-12 JST
# Updated: 2026-10-14 JST (retain existing browser login tests with first-run setup)
"""Saxo expired-token tray notification and manual login recovery tests."""
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src import tray_app, saxo_local
from src.saxo_auth import SaxoLoginRequired


class DummyIcon:
    def __init__(self, fail=False):
        self.fail = fail
        self.messages = []
        self.menu_updates = 0

    def update_menu(self):
        self.menu_updates += 1

    def notify(self, message, title):
        if self.fail:
            raise OSError("Windows notifications disabled")
        self.messages.append((title, message))


class DummyWake:
    def __init__(self, app, iterations=3):
        self.app = app
        self.iterations = iterations
        self.count = 0
        self.triggered = False

    def wait(self, interval):
        self.count += 1
        if self.count >= self.iterations:
            self.app.stopping.set()

    def clear(self):
        pass

    def set(self):
        self.triggered = True


def make_app(tmp_path):
    app = tray_app.TrayController.__new__(tray_app.TrayController)
    app.config_path = tmp_path / "setting.yaml"
    app.logger = Mock()
    app.icon = DummyIcon()
    app.status = "起動中"
    app.paused = False
    app.login_required = False
    app.login_in_progress = False
    app.auth_notice_sent = False
    app.stopping = threading.Event()
    app.interval = 60
    app.mode = "saxo_local"
    app.wake = DummyWake(app)
    return app


def test_expired_refresh_token_notifies_once_and_halts_retries(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    fetch = Mock(side_effect=SaxoLoginRequired("refresh token expired"))
    monkeypatch.setattr(tray_app, "tick_once", fetch)
    app.poll_loop()
    assert fetch.call_count == 1
    assert app.login_required is True
    assert "再ログインが必要" in app.status
    assert len(app.icon.messages) == 1
    assert "Saxo" in app.icon.messages[0][1]
    app.logger.warning.assert_called_once()


def test_notification_unavailable_still_shows_tray_status(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    app.icon = DummyIcon(fail=True)
    fetch = Mock(side_effect=SaxoLoginRequired("refresh token expired"))
    monkeypatch.setattr(tray_app, "tick_once", fetch)
    app.poll_loop()
    assert fetch.call_count == 1
    assert app.login_required is True
    assert "再ログインが必要" in app.status
    assert app.icon.menu_updates >= 1


def test_network_error_remains_generic(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    app.wake.iterations = 1
    fetch = Mock(side_effect=RuntimeError("Temporary network error"))
    monkeypatch.setattr(tray_app, "tick_once", fetch)
    app.poll_loop()
    assert fetch.call_count == 1
    assert not app.login_required
    assert "エラー" in app.status
    assert not app.icon.messages
    app.logger.exception.assert_called_once()


def test_browser_login_success_resumes_capture_immediately(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    app.login_required = True
    app.login_in_progress = True
    app.auth_notice_sent = True
    app.paused = True
    login = Mock(return_value=True)
    monkeypatch.setattr(tray_app, "SaxoSession", lambda _: SimpleNamespace(sign_in_interactively=login))
    monkeypatch.setattr(tray_app, "load_settings", lambda _: {"saxo": {"environment": "sim"}})
    monkeypatch.setattr(tray_app, "ensure_app_credentials", lambda environment: True)
    app._run_saxo_login()
    login.assert_called_once_with()
    assert not app.login_required
    assert not app.login_in_progress
    assert not app.auth_notice_sent
    assert not app.paused
    assert app.wake.triggered
    assert "画像取得を再開" in app.status


def test_browser_login_failure_preserves_relogin_state(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    app.login_required = True
    app.login_in_progress = True
    app.paused = True
    monkeypatch.setattr(tray_app, "load_settings", lambda _: {})
    monkeypatch.setattr(tray_app, "SaxoSession", Mock(side_effect=RuntimeError("Browser unavailable")))
    monkeypatch.setattr(tray_app, "ensure_app_credentials", lambda environment: True)
    app._run_saxo_login()
    assert app.login_required
    assert not app.login_in_progress
    assert not app.paused
    assert app.wake.triggered
    assert "再ログイン失敗" in app.status


def test_multiple_login_clicks_not_started_concurrently(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    app.login_in_progress = True
    fake_thread = Mock()
    monkeypatch.setattr(tray_app.threading, "Thread", fake_thread)
    app.start_saxo_login(None, None)
    fake_thread.assert_not_called()


def test_auth_required_during_pair_fetch_is_not_misreported_as_generic(tmp_path):
    from datetime import datetime, timezone
    from pathlib import Path
    import pandas as pd
    import yaml
    from src.config import load_settings
    from src.providers import DemoProvider

    cfg = load_settings(Path(__file__).resolve().parents[1] / "setting.yaml")
    cfg["output"]["local_dir"] = str(tmp_path / "charts")
    cfg["symbols"] = cfg["symbols"][:1]
    cp = tmp_path / "setting.yaml"
    cp.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    now = datetime(2026, 10, 12, 0, 2, tzinfo=timezone.utc)

    class ExpiredDuringPair:
        session = SimpleNamespace(access_token=lambda: "FAKE")
        def get(self, pair, tf, count):
            if tf != "1M":
                raise SaxoLoginRequired("refresh rejected mid-fetch")
            data = DemoProvider().get("FX:" + pair, tf, count)
            data.index = pd.date_range(end=now, periods=len(data), freq="min", tz="UTC")
            return data

    with pytest.raises(SaxoLoginRequired, match="mid-fetch"):
        saxo_local.tick_once(cp, now=now, provider=ExpiredDuringPair())
