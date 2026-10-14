# Created: 2026-10-14 JST
"""Regression tests: a custom pystray setup must explicitly show the icon."""
import sys
import threading
from types import SimpleNamespace
from unittest.mock import Mock

from src import tray_app
from src.saxo_auth import SaxoLoginRequired


class FakeIcon:
    def __init__(self, name="ChartRecorder", image=None, title="", fail_to_show=False):
        self.name = name
        self.title = title
        self.fail_to_show = fail_to_show
        self._visible = False
        self.menu = None
        self.stop_calls = 0
        self.setup_called = False
        self.notifications = []

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, enabled):
        if self.fail_to_show:
            raise OSError("test: failed to register system tray icon")
        self._visible = bool(enabled)

    def update_menu(self):
        pass

    def notify(self, message, title):
        self.notifications.append((message, title))

    def stop(self):
        self.stop_calls += 1

    def run(self, setup):
        self.setup_called = True
        setup(self)


def make_controller():
    app = tray_app.TrayController.__new__(tray_app.TrayController)
    app.config_path = "unused-in-test.yaml"
    app.mode = "saxo_local"
    app.stopping = threading.Event()
    app.wake = threading.Event()
    app.worker = None
    app.icon = None
    app.single_instance_handle = None
    app.kernel32 = None
    app.logger = Mock()
    app.status = "起動中"
    app.paused = False
    app.login_required = False
    app.login_in_progress = False
    app.auth_notice_sent = False
    app.interval = 60
    return app


def test_custom_setup_explicitly_makes_tray_icon_visible():
    app = make_controller()
    icon = FakeIcon()
    seen = []

    def poll():
        seen.append(icon.visible)
        app.stopping.set()
    app.poll_loop = poll

    app._on_tray_ready(icon)
    assert app.worker is not None
    app.worker.join(timeout=3)
    assert seen == [True]
    assert icon.visible is True
    app.logger.info.assert_called_once()


def test_icon_registration_failure_stops_instead_of_leaving_hidden_daemon():
    app = make_controller()
    icon = FakeIcon(fail_to_show=True)
    app.poll_loop = Mock()
    app._on_tray_ready(icon)

    assert app.stopping.is_set()
    assert icon.stop_calls == 1
    assert app.worker is None
    app.poll_loop.assert_not_called()
    app.logger.exception.assert_called_once()


def test_run_wires_custom_setup_to_visible_icon(monkeypatch):
    app = make_controller()
    icons = []

    def fake_icon(*args, **kwargs):
        value = FakeIcon(*args, **kwargs)
        icons.append(value)
        return value

    fake_pystray = SimpleNamespace(
        Icon=fake_icon,
        Menu=lambda *args: args,
        MenuItem=lambda *args, **kwargs: (args, kwargs),
    )
    monkeypatch.setitem(sys.modules, "pystray", fake_pystray)
    # Run the Windows-independent path to avoid touching a real session mutex.
    monkeypatch.setattr(tray_app, "os", SimpleNamespace(name="posix"))
    def poll():
        app.stopping.set()
    app.poll_loop = poll

    app.run()

    assert len(icons) == 1
    assert icons[0].setup_called
    assert icons[0].visible
    assert app.worker is not None and not app.worker.is_alive()


def test_expired_saxo_token_does_not_hide_tray_icon(monkeypatch):
    app = make_controller()
    icon = FakeIcon()
    app.icon = icon

    def expired(_):
        raise SaxoLoginRequired("expired test token")

    monkeypatch.setattr(tray_app, "tick_once", expired)
    class OnePoll:
        def wait(self, seconds):
            app.stopping.set()
        def clear(self):
            pass
        def set(self):
            pass
    app.wake = OnePoll()

    app._on_tray_ready(icon)
    app.worker.join(timeout=3)

    assert icon.visible is True
    assert app.login_required is True
    assert len(icon.notifications) == 1
    assert "再ログイン" in app.status
