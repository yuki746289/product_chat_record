# Created: 2026-10-14 JST
"""Ask an existing Windows tray instance to exit safely; never kill a Saxo worker.

The named event and mutex are shared with the existing ChartRecorder code.
Do not use WaitForSingleObject on a mutex created with initial_owner=False:
that would report success while the old instance was still running.
"""
import ctypes
import time

from src.windows_single_instance import MUTEX_NAME, STOP_EVENT_NAME, EVENT_MODIFY_STATE

SYNCHRONIZE = 0x00100000
ERROR_FILE_NOT_FOUND = 2


class CooperativeShutdown:
    def __init__(self, kernel32=None, get_last_error=None, sleep=None, clock=None):
        if kernel32 is None:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenMutexW.argtypes = [ctypes.c_uint, ctypes.c_bool, ctypes.c_wchar_p]
            kernel32.OpenMutexW.restype = ctypes.c_void_p
            kernel32.OpenEventW.argtypes = [ctypes.c_uint, ctypes.c_bool, ctypes.c_wchar_p]
            kernel32.OpenEventW.restype = ctypes.c_void_p
            kernel32.SetEvent.argtypes = [ctypes.c_void_p]
            kernel32.SetEvent.restype = ctypes.c_bool
            kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel32.CloseHandle.restype = ctypes.c_bool
        self.kernel32 = kernel32
        self.last_error = get_last_error or ctypes.get_last_error
        self.sleep = sleep or time.sleep
        self.clock = clock or time.monotonic

    def is_running(self):
        handle = self.kernel32.OpenMutexW(SYNCHRONIZE, False, MUTEX_NAME)
        if handle:
            self.kernel32.CloseHandle(handle)
            return True
        error = self.last_error()
        if error == ERROR_FILE_NOT_FOUND:
            return False
        raise OSError(error, "Could not inspect ChartRecorder single-instance mutex")

    def stop(self, timeout_seconds=300):
        """Return True iff an instance was running. Refuse to force-stop old versions.

        The mutex remains alive until both the Saxo chart worker and OAuth
        browser-login worker exit. Leave the old instance intact on timeout.
        """
        if not self.is_running():
            return False
        event = self.kernel32.OpenEventW(EVENT_MODIFY_STATE, False, STOP_EVENT_NAME)
        if not event:
            raise RuntimeError(
                "The running ChartRecorder does not support cooperative shutdown. "
                "Exit it from its tray menu and retry. No process was terminated."
            )
        try:
            if not self.kernel32.SetEvent(event):
                raise RuntimeError("Could not send safe shutdown request; running app left intact.")
        finally:
            self.kernel32.CloseHandle(event)
        deadline = self.clock() + timeout_seconds
        while self.is_running():
            if self.clock() >= deadline:
                raise TimeoutError(
                    "ChartRecorder did not finish its Saxo capture/login within the safety timeout. "
                    "No forced termination or concurrent restart was attempted."
                )
            self.sleep(0.5)
        return True
