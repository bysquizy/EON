"""Windows per-user single-instance guard and best-effort window activation."""
import ctypes
import hashlib
import os
import sys

_HANDLE = None
_API = None
ERROR_ALREADY_EXISTS = 183


def mutex_name(profile=None):
    """Use a stable, non-identifying per-profile mutex name."""
    profile = profile or os.environ.get("USERPROFILE") or os.path.expanduser("~")
    identity = os.path.normcase(os.path.abspath(profile)).encode("utf-8", "surrogatepass")
    return "Local\\EON-" + hashlib.sha256(identity).hexdigest()[:32]


class _WindowsMutexApi:
    def __init__(self):
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateMutexW.restype = ctypes.c_void_p
        self.kernel.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p)
        self.kernel.CloseHandle.argtypes = (ctypes.c_void_p,)

    def create(self, name):
        return self.kernel.CreateMutexW(None, False, name)

    @staticmethod
    def last_error():
        return ctypes.get_last_error()

    def close(self, handle):
        self.kernel.CloseHandle(handle)


def acquire_instance(api=None, profile=None):
    """Return False when another EON owns the current user's mutex."""
    global _HANDLE, _API
    if sys.platform != "win32" and api is None:
        return True
    api = api or _WindowsMutexApi()
    handle = api.create(mutex_name(profile))
    if not handle:
        raise OSError("Windows tek-örnek koruması başlatılamadı.")
    if api.last_error() == ERROR_ALREADY_EXISTS:
        api.close(handle)
        return False
    _HANDLE, _API = handle, api
    return True


def release_instance():
    global _HANDLE, _API
    if _HANDLE is not None:
        _API.close(_HANDLE)
        _HANDLE = _API = None


def focus_existing_window():
    """Bring an existing EON browser window forward without reading its URL or token."""
    if sys.platform != "win32":
        return False
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    found = []

    def inspect(hwnd, _):
        length = user32.GetWindowTextLengthW(hwnd)
        if not length or length > 512:
            return True
        title = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title, len(title))
        if "eon — yerel asistan" in title.value.casefold():
            found.append(hwnd)
            return False
        return True

    callback = callback_type(inspect)
    user32.EnumWindows(callback, None)
    if found:
        hwnd = found[0]
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        focused = bool(user32.SetForegroundWindow(hwnd))
        if not focused:
            user32.MessageBoxW(None,
                               "EON zaten çalışıyor. Açık EON tarayıcı oturumunu kullanın.",
                               "EON zaten açık", 0x40)
        return focused
    user32.MessageBoxW(None,
                       "EON zaten çalışıyor. Açık EON tarayıcı oturumunu kullanın.",
                       "EON zaten açık", 0x40)
    return False
