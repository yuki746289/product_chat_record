# Created: 2026-10-14 JST
"""Offline versioned updater and Windows cooperative shutdown tests."""
from pathlib import Path
import shutil

import pytest

from scripts import update_chartrecorder as updater
from scripts.cooperative_shutdown import CooperativeShutdown


class FakeGuard:
    def __init__(self, events, running=True):
        self.events = events
        self.running = running
        self.called = 0

    def stop(self, timeout_seconds=300):
        assert timeout_seconds >= 60
        self.called += 1
        self.events.append("stop")
        was = self.running
        self.running = False
        return was


def prepared(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    source = Path(__file__).resolve().parents[1]
    shutil.copy2(source / "setting.yaml", root / "setting.yaml")
    (root / "system.yaml").write_text(
        "install:\n  location: desktop\n  folder_name: ChartRecorder\n  image_folder: chart_image\n",
        encoding="utf-8",
    )
    (root / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "apps").mkdir()
    return root, (tmp_path / "apps")


def arrange(monkeypatch):
    monkeypatch.setattr(updater, "build_id", lambda root: "v0.1.0-12345678")
    monkeypatch.setattr(updater, "is_dirty", lambda root: False)


def test_first_update_builds_before_stop_and_restarts(tmp_path, monkeypatch):
    root, parent = prepared(tmp_path)
    arrange(monkeypatch)
    events = []
    guard = FakeGuard(events)
    def builder(repo, stage):
        events.append("build")
        stage.mkdir(parents=True, exist_ok=True)
        (stage / "ChartRecorder.exe").write_bytes(b"MZ-VERSIONED")
    def launcher(exe):
        events.append("launch")
        assert exe.read_bytes() == b"MZ-VERSIONED"
    dest = updater.update_install(root, location=str(parent), builder=builder, guard=guard, launcher=launcher)
    assert events == ["build", "stop", "launch"]
    assert (dest / "installed-version.txt").read_text(encoding="utf-8").strip() == "v0.1.0-12345678"
    assert (dest / "chart_image").is_dir()
    assert (dest / "setting.yaml").is_file()
    assert (dest / "system.yaml").is_file()


def test_same_version_skips_build_but_safely_restarts(tmp_path, monkeypatch):
    root, parent = prepared(tmp_path)
    arrange(monkeypatch)
    guard = FakeGuard([])
    def builder(repo, stage):
        (stage / "ChartRecorder.exe").write_bytes(b"MZ-VALID")
    updater.update_install(root, location=str(parent), builder=builder,
                           guard=guard, launcher=lambda exe: None)
    events = []
    def must_not_build(*args):
        raise AssertionError("Same release must not be rebuilt")
    dest = updater.update_install(
        root, location=str(parent), builder=must_not_build,
        guard=FakeGuard(events), launcher=lambda exe: events.append("launch"),
    )
    assert events == ["stop", "launch"]
    assert (dest / "installed-version.txt").is_file()


def test_compile_failure_never_stops_old_application(tmp_path, monkeypatch):
    root, parent = prepared(tmp_path)
    arrange(monkeypatch)
    events = []
    guard = FakeGuard(events)
    def failed(repo, stage):
        events.append("build")
        raise RuntimeError("build failed")
    with pytest.raises(RuntimeError, match="build failed"):
        updater.update_install(root, location=str(parent), builder=failed,
                               guard=guard, launcher=lambda exe: events.append("launch"))
    assert events == ["build"]
    assert guard.called == 0


def test_safe_stop_failure_does_not_install_or_relaunch(tmp_path, monkeypatch):
    root, parent = prepared(tmp_path)
    arrange(monkeypatch)
    def builder(repo, stage):
        (stage / "ChartRecorder.exe").write_bytes(b"MZ-STAGED")
    class BusyGuard:
        def stop(self, timeout_seconds=300):
            raise TimeoutError("Saxo worker still active")
    with pytest.raises(TimeoutError, match="Saxo worker"):
        updater.update_install(root, location=str(parent), builder=builder,
                               guard=BusyGuard(), launcher=lambda exe: pytest.fail("launched"))
    assert not (parent / "ChartRecorder" / "ChartRecorder.exe").exists()


def test_release_metadata_is_public_and_dirty_tree_forces_rebuild(tmp_path, monkeypatch):
    root, parent = prepared(tmp_path)
    arrange(monkeypatch)
    build_events = []
    def builder(repo, stage):
        build_events.append(str(stage))
        (stage / "ChartRecorder.exe").write_bytes(b"MZ")
    updater.update_install(root, location=str(parent), builder=builder, guard=FakeGuard([]), launcher=lambda exe: None)
    monkeypatch.setattr(updater, "is_dirty", lambda root: True)
    updater.update_install(root, location=str(parent), builder=builder, guard=FakeGuard([]), launcher=lambda exe: None)
    assert len(build_events) == 2
    assert build_events[0] != build_events[1]


class FakeKernel:
    def __init__(self, cooperative=True):
        self.running = True
        self.cooperative = cooperative
        self.signaled = False
        self.last_error = 0
        self.closed = []
    def OpenMutexW(self, access, inherit, name):
        assert name.endswith("ChartRecorderSaxoTray")
        self.last_error = 0 if self.running else 2
        return 11 if self.running else None
    def OpenEventW(self, access, inherit, name):
        assert name.endswith("ChartRecorderSaxoTrayStopV1")
        self.last_error = 0 if self.cooperative else 2
        return 22 if self.cooperative else None
    def SetEvent(self, handle):
        assert handle == 22
        self.signaled = True
        return True
    def CloseHandle(self, handle):
        self.closed.append(handle)
        return True


def test_safe_shutdown_waits_for_mutex_to_disappear():
    kernel = FakeKernel()
    def allow_exit(seconds):
        assert kernel.signaled
        kernel.running = False
    ctrl = CooperativeShutdown(
        kernel32=kernel,
        get_last_error=lambda: kernel.last_error,
        sleep=allow_exit,
    )
    assert ctrl.stop() is True
    assert kernel.signaled
    assert kernel.closed.count(22) == 1


def test_safe_shutdown_refuses_legacy_without_stop_event():
    kernel = FakeKernel(cooperative=False)
    ctrl = CooperativeShutdown(kernel32=kernel, get_last_error=lambda: kernel.last_error)
    with pytest.raises(RuntimeError, match="Exit it from its tray"):
        ctrl.stop()
    assert kernel.running
    assert not kernel.signaled


def test_safe_shutdown_when_not_running_is_no_op():
    kernel = FakeKernel()
    kernel.running = False
    ctrl = CooperativeShutdown(kernel32=kernel, get_last_error=lambda: kernel.last_error)
    assert ctrl.stop() is False
    assert not kernel.signaled
