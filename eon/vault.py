"""Per-user Windows DPAPI vault. Only encrypted bytes reach disk."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import tempfile
import time


class Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.c_void_p)]


def protect(data, *, decrypt=False):
    if os.name != "nt":
        raise OSError("Windows anahtar koruması kullanılamıyor.")
    source = ctypes.create_string_buffer(data)
    incoming = Blob(len(data), ctypes.cast(source, ctypes.c_void_p))
    outgoing = Blob()
    dll = ctypes.windll.crypt32
    operation = dll.CryptUnprotectData if decrypt else dll.CryptProtectData
    if not operation(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise OSError("Windows anahtar koruması işlemi başarısız.")
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        ctypes.windll.kernel32.LocalFree(ctypes.c_void_p(outgoing.data))


class Vault:
    def __init__(self, path):
        self.path = Path(path)
        self.guard = None

    def open(self):
        import msvcrt
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.guard = self.path.with_suffix(".lock").open("a+b")
        self.guard.seek(0)
        msvcrt.locking(self.guard.fileno(), msvcrt.LK_NBLCK, 1)
        if not self.path.exists():
            protect(b"")
            return None
        if self.path.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("Kayıt boyutu geçersiz.")
        return json.loads(protect(self.path.read_bytes(), decrypt=True))

    def close(self):
        if self.guard:
            self.guard.close()
            self.guard = None

    def backup_legacy(self, suffix=".pre-v030.dpapi"):
        # Publish a complete encrypted rollback copy before the first schema upgrade.
        if not self.path.exists():
            return
        target = self.path.with_suffix(suffix)
        if target.exists():
            return
        fd, temp = tempfile.mkstemp(dir=self.path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(self.path.read_bytes())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, target)
        finally:
            Path(temp).unlink(missing_ok=True)

    def rotate_backups(self, keep: int = 3, min_interval: float = 0) -> None:
        if not self.path.exists() or keep < 1:
            return
        newest = self.path.with_suffix(".bak1.dpapi")
        try:
            if min_interval and newest.exists() and time.time() - newest.stat().st_mtime < min_interval:
                return
        except OSError:
            pass
        try:
            raw = self.path.read_bytes()
            for idx in range(keep, 1, -1):
                src = self.path.with_suffix(f".bak{idx - 1}.dpapi")
                dst = self.path.with_suffix(f".bak{idx}.dpapi")
                if src.exists():
                    os.replace(src, dst)
            fd, temp = tempfile.mkstemp(dir=self.path.parent)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(raw)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp, self.path.with_suffix(".bak1.dpapi"))
            finally:
                Path(temp).unlink(missing_ok=True)
        except OSError:
            pass

    def save(self, data):
        encrypted = protect(json.dumps(data, ensure_ascii=False).encode())
        if len(encrypted) > 32 * 1024 * 1024:
            raise ValueError("Kayıt sınırına ulaşıldı.")
        fd, temp = tempfile.mkstemp(dir=self.path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(encrypted)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.path)
        finally:
            Path(temp).unlink(missing_ok=True)
