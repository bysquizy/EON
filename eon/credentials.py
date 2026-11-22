"""Windows-only secret entry. The browser never receives the Gemini key."""
from pathlib import Path
import re
import sys
from .vault import Vault


def secret(path, value=None):
    if path is None:
        raise ValueError("Anahtar saklamak için Windows DPAPI gerekli.")
    vault = Vault(path)
    try:
        record = vault.open() or {}
        if value is None:
            return record.get("key", "")
        if value and not re.fullmatch(r"[A-Za-z0-9_-]{16,256}", value):
            raise ValueError("Anahtar biçimi geçersiz.")
        vault.save({"key": value})
    except (ImportError, OSError):
        raise ValueError("Windows anahtar kasası açılamadı.") from None
    finally:
        vault.close()


def enter(path):
    from tkinter import Tk, simpledialog
    window = Tk()
    window.withdraw()
    try:
        value = simpledialog.askstring("EON · Google AI Studio", "Gemini API anahtarı", show="*", parent=window)
        if value:
            secret(Path(path), value.strip())
    finally:
        window.destroy()


if __name__ == "__main__":
    enter(sys.argv[1])
