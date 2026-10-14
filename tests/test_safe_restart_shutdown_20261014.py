# Created: 2026-10-14 JST
"""Regression: the single-instance mutex outlives Saxo polling and login threads."""
import sys
import threading
from types import SimpleNamespace
from unittest.mock import Mock

from src import tray_app


class FakeGuard:
    def __init__(self, events):
        self.events = events
        self.closed = False

    def acquire(self):
        return True

    def watch_for_stop(self, callback, shutdown):
        self.events.append("listener")

    def close(self):
        self.events.append("guard-close")
        self.closed = True


class FakeIcon:
    def __init__(self, *args):
        self.menu = None

    def run(self, setup=None):
        # Simulate an icon shutdown while background Saxo work is still active.
        return


def test_mutex_stays_held_until_both_saxo_workers_have_exited(monkeypatch):
    calls = []
    polling_done = threading.Event()
    login_done = threading.Event()
    poll_join_entered = threading.Event()
    login_join_entered = threading.Event()

    class PendingWorker:
        def __init__(self, label, release, entered):
            self.label = label
            self.release = release
            self.entered = entered

        def join(self, timeout=None):
            assert timeout is None, "Saxo worker must fully stop before mutex release"
            calls.append(self.label + "-join")
            self.entered.set()
            assert self.release.wait(5), self.label + " worker was not allowed to finish"

    guard = FakeGuard(calls)
    monkeypatch.setattr(tray_app, "WindowsSingleInstance", lambda: guard)
    # Patch only the target module's OS reference, never the global os module.
    monkeypatch.setattr(tray_app, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(tray_app, "_icon_image", lambda: object())
    monkeypatch.setitem(sys.modules, "pystray", SimpleNamespace(
        Icon=FakeIcon,
        Menu=lambda *args: args,
        MenuItem=lambda *args, **kwargs: (args, kwargs),
    ))

    app = tray_app.TrayController.__new__(tray_app.TrayController)
    app.mode = "saxo_local"
    app.status = "起動中"
    app.stopping = threading.Event()
    app.wake = threading.Event()
    app.worker = PendingWorker("poll", polling_done, poll_join_entered)
    app.login_worker = PendingWorker("login", login_done, login_join_entered)
    app.instance_guard = None
    app.instance_watcher = None
    app.paused = False
    app.login_required = False
    app.login_in_progress = True
    app.icon = None
    app.logger = Mock()

    background = threading.Thread(target=app.run, daemon=True)
    background.start()
    try:
        assert poll_join_entered.wait(3), "polling cleanup did not start"
        assert not guard.closed
        assert not login_join_entered.is_set()
        polling_done.set()
        assert login_join_entered.wait(3), "login cleanup did not start"
        assert not guard.closed
        login_done.set()
        background.join(3)
        assert not background.is_alive()
        assert calls.index("poll-join") < calls.index("login-join") < calls.index("guard-close")
        assert guard.closed
    finally:
        polling_done.set()
        login_done.set()
        background.join(3)
