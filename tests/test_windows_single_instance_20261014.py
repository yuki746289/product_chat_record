# Created: 2026-10-14 JST
"""Network-free Windows single-instance and cooperative restart regressions."""
from unittest.mock import Mock

from src.windows_single_instance import (
    WindowsSingleInstance, ERROR_ALREADY_EXISTS, IDYES, WAIT_OBJECT_0,
    WAIT_TIMEOUT, STOP_EVENT_NAME, MUTEX_NAME
)


class FakeKernel:
    def __init__(self, running=False, cooperative=True):
        self.running = running
        self.cooperative = cooperative
        self.last_error = 0
        self.handles = []
        self.closed = []
        self.sent = 0
        self.reset_count = 0
        self.wait_results = []

    def CreateMutexW(self, unused_security, initial_owner, name):
        assert name == MUTEX_NAME
        assert initial_owner is False
        handle = 10 + len(self.handles)
        self.handles.append(handle)
        self.last_error = ERROR_ALREADY_EXISTS if self.running else 0
        return handle

    def CreateEventW(self, unused_security, manual_reset, initial_state, name):
        assert name == STOP_EVENT_NAME
        assert manual_reset is True
        assert initial_state is False
        return 100

    def OpenEventW(self, access, inherit, name):
        assert name == STOP_EVENT_NAME
        return 200 if self.cooperative else None

    def SetEvent(self, handle):
        assert handle == 200
        self.sent += 1
        return True

    def ResetEvent(self, handle):
        assert handle == 100
        self.reset_count += 1
        return True

    def WaitForSingleObject(self, handle, milliseconds):
        assert handle == 100
        return self.wait_results.pop(0) if self.wait_results else WAIT_TIMEOUT

    def CloseHandle(self, handle):
        self.closed.append(handle)
        return True


def make_gate(kernel, choices=None, sleep=None):
    user = Mock()
    user.MessageBoxW.side_effect = choices or [IDYES]
    gate = WindowsSingleInstance(
        kernel32=kernel, user32=user,
        get_last_error=lambda: kernel.last_error,
        sleep=sleep or (lambda seconds: None),
    )
    return gate, user


def test_first_instance_starts_normally_without_dialog():
    k = FakeKernel()
    gate, user = make_gate(k)
    assert gate.acquire()
    assert gate.stop_event == 100
    assert gate.mutex in k.handles
    assert k.reset_count == 1
    user.MessageBoxW.assert_not_called()
    gate.close()
    assert gate.stop_event is None and gate.mutex is None
    assert 100 in k.closed


def test_second_launch_cancel_has_no_exception_or_restart():
    k = FakeKernel(running=True)
    gate, user = make_gate(k, choices=[7])
    assert gate.acquire() is False
    assert gate.mutex is None and gate.stop_event is None
    assert k.sent == 0
    assert k.closed == [10]
    assert user.MessageBoxW.call_count == 1


def test_second_launch_yes_signals_and_replaces_after_old_exits():
    k = FakeKernel(running=True)
    wait_calls = []
    def wait(seconds):
        wait_calls.append(seconds)
        k.running = False
    gate, user = make_gate(k, choices=[IDYES], sleep=wait)
    assert gate.acquire()
    assert k.sent == 1
    assert wait_calls
    assert k.reset_count == 1
    assert 10 in k.closed and 200 in k.closed
    assert gate.mutex is not None
    assert user.MessageBoxW.call_count == 1
    gate.close()


def test_legacy_old_version_reports_manual_stop_without_killing():
    k = FakeKernel(running=True, cooperative=False)
    gate, user = make_gate(k, choices=[IDYES, 1])
    assert gate.acquire() is False
    assert k.sent == 0
    assert gate.mutex is None
    assert user.MessageBoxW.call_count == 2


def test_old_instance_shutdown_timeout_does_not_allow_duplicate():
    k = FakeKernel(running=True)
    gate, user = make_gate(k, choices=[IDYES, 1])
    assert gate.acquire() is False
    assert k.sent == 1
    assert len(k.handles) == 81  # initial check + 80 retries
    assert len(k.closed) == 82  # all mutex attempts + OpenEvent handle
    assert user.MessageBoxW.call_count == 2
    assert gate.mutex is None


def test_cooperative_stop_listener_invokes_callback_once():
    k = FakeKernel()
    gate, _ = make_gate(k)
    assert gate.acquire()
    k.wait_results = [WAIT_TIMEOUT, WAIT_OBJECT_0]
    stopper = Mock()
    shutdown = Mock()
    shutdown.is_set.return_value = False
    gate.watch_for_stop(stopper, shutdown)
    stopper.assert_called_once()
    gate.close()


def test_listener_does_not_stop_if_app_is_already_exiting():
    k = FakeKernel()
    gate, _ = make_gate(k)
    assert gate.acquire()
    shutdown = Mock()
    shutdown.is_set.return_value = True
    stopper = Mock()
    gate.watch_for_stop(stopper, shutdown)
    stopper.assert_not_called()
    gate.close()
