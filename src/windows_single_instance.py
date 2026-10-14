# Created: 2026-10-14 JST
"""Single-instance Windows UX with safe, cooperative replacement of prior versions.

A second launch must never create simultaneous Saxo token-refresh processes.
The existing instance handles a named stop event and exits before replacement.
Older ChartRecorder versions lack the stop event and are NOT force-killed.
"""
import ctypes
import time

MUTEX_NAME = r"Local\ChartRecorderSaxoTray"
STOP_EVENT_NAME = r"Local\ChartRecorderSaxoTrayStopV1"
ERROR_ALREADY_EXISTS = 183
EVENT_MODIFY_STATE = 0x0002
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
MB_YESNO = 0x0004
MB_OK = 0x0000
MB_ICONQUESTION = 0x0020
MB_ICONINFORMATION = 0x0040
MB_TOPMOST = 0x00040000
MB_SETFOREGROUND = 0x00010000
IDYES = 6


class WindowsSingleInstance:
    """Own the legacy mutex; coordinate shutdown with a separate named event."""

    def __init__(self, kernel32=None, user32=None, get_last_error=None, sleep=None):
        if kernel32 is None:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
            kernel32.CreateMutexW.restype = ctypes.c_void_p
            kernel32.CreateEventW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_bool, ctypes.c_wchar_p]
            kernel32.CreateEventW.restype = ctypes.c_void_p
            kernel32.OpenEventW.argtypes = [ctypes.c_uint, ctypes.c_bool, ctypes.c_wchar_p]
            kernel32.OpenEventW.restype = ctypes.c_void_p
            kernel32.SetEvent.argtypes = [ctypes.c_void_p]
            kernel32.SetEvent.restype = ctypes.c_bool
            kernel32.ResetEvent.argtypes = [ctypes.c_void_p]
            kernel32.ResetEvent.restype = ctypes.c_bool
            kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            kernel32.WaitForSingleObject.restype = ctypes.c_uint
            kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel32.CloseHandle.restype = ctypes.c_bool
        if user32 is None:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.MessageBoxW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
            user32.MessageBoxW.restype = ctypes.c_int
        self.kernel32 = kernel32
        self.user32 = user32
        self.last_error = get_last_error or ctypes.get_last_error
        self.sleep = sleep or time.sleep
        self.mutex = None
        self.stop_event = None

    def _message(self, message, style=MB_OK | MB_ICONINFORMATION):
        return self.user32.MessageBoxW(
            None, message, "ChartRecorder", style | MB_TOPMOST | MB_SETFOREGROUND
        )

    def _try_mutex(self):
        mutex = self.kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if not mutex:
            raise OSError(self.last_error(), "Failed to create ChartRecorder Windows mutex")
        if self.last_error() == ERROR_ALREADY_EXISTS:
            # Close our handle; keeping it would prevent the named object from
            # disappearing after the existing owner exits.
            self.kernel32.CloseHandle(mutex)
            return False
        self.mutex = mutex
        return True

    def _start_listener(self):
        self.stop_event = self.kernel32.CreateEventW(
            None, True, False, STOP_EVENT_NAME
        )
        if not self.stop_event:
            raise OSError(self.last_error(), "Failed to create ChartRecorder restart event")
        # Previous owner is gone: ensure the new event is not already signaled.
        if not self.kernel32.ResetEvent(self.stop_event):
            raise OSError(self.last_error(), "Failed to reset ChartRecorder restart event")

    def acquire(self):
        """Return False without traceback if user declines or restart is unsafe."""
        if self._try_mutex():
            try:
                self._start_listener()
            except Exception:
                self.close()
                raise
            return True

        choice = self._message(
            "ChartRecorderは既に起動しています。\n\n"
            "既存のChartRecorderを終了して、新しく起動しますか？\n"
            "「はい」: 既存のアプリを終了して新版を起動\n"
            "「いいえ」: そのまま既存のアプリを使用",
            MB_YESNO | MB_ICONQUESTION,
        )
        if choice != IDYES:
            return False

        event = self.kernel32.OpenEventW(EVENT_MODIFY_STATE, False, STOP_EVENT_NAME)
        if not event:
            self._message(
                "起動中のChartRecorderが旧バージョンのため、\n"
                "自動再起動には対応していません。\n\n"
                "既存のChartRecorder（Python版を含む）を終了してから、\n"
                "新しいEXEを起動してください。"
            )
            return False

        try:
            signaled = self.kernel32.SetEvent(event)
        finally:
            self.kernel32.CloseHandle(event)
        if not signaled:
            self._message("既存アプリへ終了要求を送れませんでした。手動で終了してください。")
            return False

        # The old process owns its mutex *handle* without locking the mutex.
        # Never WaitForSingleObject(mutex): it can succeed while old process runs.
        for _ in range(80):
            self.sleep(0.25)
            if self._try_mutex():
                try:
                    self._start_listener()
                except Exception:
                    self.close()
                    raise
                return True

        self._message(
            "既存のChartRecorderが20秒以内に終了しませんでした。\n"
            "安全のため新しいインスタンスは起動していません。\n"
            "既存のアプリを確認してください。"
        )
        return False

    def watch_for_stop(self, request_stop, shutdown):
        """Listen on a worker thread; never block pystray's UI thread."""
        while not shutdown.is_set():
            status = self.kernel32.WaitForSingleObject(self.stop_event, 250)
            if status == WAIT_OBJECT_0:
                if not shutdown.is_set():
                    request_stop()
                return
            if status != WAIT_TIMEOUT:
                return

    def close(self):
        if self.stop_event:
            self.kernel32.CloseHandle(self.stop_event)
            self.stop_event = None
        if self.mutex:
            self.kernel32.CloseHandle(self.mutex)
            self.mutex = None
