"""Windows-only secret entry. The browser never receives the Gemini key."""
from pathlib import Path
from hmac import compare_digest
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
        if value and not re.fullmatch(r"[A-Za-z0-9_.-]{16,1024}", value):
            raise ValueError("Anahtar biçimi geçersiz.")
        vault.save({"key": value})
    except (ImportError, OSError):
        raise ValueError("Windows anahtar kasası açılamadı.") from None
    finally:
        vault.close()
    if not compare_digest(secret(path), value):
        raise ValueError("Anahtar yazıldıktan sonra doğrulanamadı.")


def enter(path):
    from tkinter import Tk, simpledialog, messagebox
    window = Tk()
    window.withdraw()
    try:
        value = simpledialog.askstring("EON · Google AI Studio", "Gemini API anahtarı", show="*", parent=window)
        if value is None:
            raise SystemExit(2)
        try:
            if not value.strip():
                raise ValueError("Anahtar boş.")
            secret(Path(path), value.strip())
        except ValueError as exc:
            messagebox.showerror("Gemini", str(exc), parent=window)
            raise SystemExit(1) from None
    finally:
        window.destroy()


if __name__ == "__main__":
    enter(sys.argv[1])
