"""Windows application launcher with an explicit, local allowlist.

No shell, no command arguments, no LLM-controlled launch, no remote URLs.
Paths are saved outside the repository in the current user's LOCALAPPDATA.
"""
import json
import ntpath
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
from typing import Callable


PRESETS = {
    "chrome": {"name": "Chrome", "terms": ["google chrome", "chrome"], "executables": ["chrome.exe"]},
    "spotify": {"name": "Spotify", "terms": ["spotify"], "executables": ["spotify.exe"]},
    "notion": {"name": "Notion", "terms": ["notion"], "executables": ["notion.exe"]},
    "obs": {"name": "OBS Studio", "terms": ["obs studio", "obs"], "executables": ["obs64.exe", "obs32.exe"]},
    "solidworks": {"name": "SOLIDWORKS", "terms": ["solidworks"], "executables": ["sldworks.exe"]},
    "antigravity": {"name": "Antigravity", "terms": ["antigravity"], "executables": ["antigravity.exe"]},
}
BAD_SHORTCUT_WORDS = ("uninstall", "uninst", "setup", "install", "updater", "update", "crash", "repair", "readme", "help")
NAME_RE = re.compile(r"^[\w][\w .-]{0,47}$", flags=re.UNICODE)
KEY_RE = re.compile(r"^[a-z][a-z0-9_-]{0,47}$")


class LaunchError(ValueError):
    pass


def storage_path() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if root:
        return Path(root) / "EON" / "applications.json"
    return Path.home() / ".local" / "share" / "EON" / "applications.json"


def safe_launch_path(value: str, *, windows: bool = True) -> str:
    """Only allow existing local .exe/.lnk files. Never accept shell commands or UNC paths."""
    if not isinstance(value, str) or not 1 <= len(value) <= 1024 or "\x00" in value:
        raise LaunchError("Uygulama yolu geçersiz.")
    path = value.strip().strip('"')
    if windows:
        if (not ntpath.isabs(path) or path.startswith(("\\\\", "//"))
                or not re.match(r"^[A-Za-z]:[\\/]", path)):
            raise LaunchError("Yalnız yerel diskteki tam dosya yollarına izin verilir.")
    elif not os.path.isabs(path):
        raise LaunchError("Tam dosya yolu gerekli.")
    if ntpath.splitext(path)[1].lower() not in (".exe", ".lnk"):
        raise LaunchError("Yalnız EXE ve Windows kısayolu (LNK) seçilebilir.")
    if not Path(path).is_file():
        raise LaunchError("Bu konumda uygulama dosyası bulunamadı.")
    resolved = str(Path(path).resolve(strict=True))
    if windows and (not re.match(r"^[A-Za-z]:[\\/]", resolved) or ntpath.splitext(resolved)[1].lower() not in (".exe",".lnk")):
        raise LaunchError("Hedef yerel bir EXE veya kısayol olmalı.")
    return resolved


def shortcut_search_directories(environ=None) -> list[Path]:
    """Windows Start Menu and Desktop shortcut locations (local only)."""
    env = environ if environ is not None else os.environ
    directories = []
    if env.get("APPDATA"):
        directories.append(Path(env["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    if env.get("PROGRAMDATA"):
        directories.append(Path(env["PROGRAMDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
        directories.append(Path(env["PROGRAMDATA"]).parent / "Public" / "Desktop")
    if env.get("USERPROFILE"):
        directories.append(Path(env["USERPROFILE"]) / "Desktop")
    if env.get("PUBLIC"):
        directories.append(Path(env["PUBLIC"]) / "Desktop")
    for key in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        if env.get(key):
            directories.append(Path(env[key]) / "Desktop")
    # Windows allows Desktop to be moved. Read the configured path, if present.
    if sys.platform == "win32" and environ is None:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
                value, _ = winreg.QueryValueEx(k, "Desktop")
                if isinstance(value, str):
                    directories.append(Path(os.path.expandvars(value)))
        except (OSError, ImportError):
            pass
    unique = []
    for directory in directories:
        if directory not in unique:
            unique.append(directory)
    return unique


class ApplicationRegistry:
    def __init__(self, config_path: Path | None = None, *, platform: str | None = None,
                 start_process: Callable[..., object] | None = None):
        self.config_path = config_path or storage_path()
        self.platform = platform or sys.platform
        self._start_process = start_process or subprocess.Popen
        self._lock = threading.RLock()
        self._hidden = set()
        self._custom = self._load()
        self._discovered: dict[str, str] = {}
        self._native_icons = {}
        if self.platform == "win32":
            self.refresh()

    def _load(self) -> dict[str, dict[str, str]]:
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {}
            hidden = data.get("hidden", [])
            if isinstance(hidden, list):
                self._hidden = {key for key in hidden if isinstance(key, str) and key in PRESETS}
            items = data.get("applications", {})
            if not isinstance(items, dict):
                return {}
            return {
                key: {"name": val["name"], "path": val["path"]}
                for key, val in items.items()
                if (KEY_RE.fullmatch(key) and isinstance(val, dict)
                    and isinstance(val.get("name"), str) and isinstance(val.get("path"), str))
            }
        except (FileNotFoundError, OSError, ValueError, TypeError, KeyError):
            return {}

    def _persist(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix="eon-", suffix=".tmp", dir=self.config_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"version": 1, "applications": self._custom, "hidden": sorted(self._hidden)}, handle,
                          ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, self.config_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def refresh(self) -> None:
        """Look for registered application executables and Start Menu shortcuts."""
        discovered: dict[str, str] = {}
        if self.platform != "win32":
            self._discovered = discovered
            return
        # Registered App Paths are controlled by the local Windows installation.
        try:
            import winreg
            for key, preset in PRESETS.items():
                for executable in preset["executables"]:
                    for hive, view in ((winreg.HKEY_CURRENT_USER, 0),
                                       (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY),
                                       (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY)):
                        try:
                            with winreg.OpenKey(hive, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{executable}", 0, winreg.KEY_READ | view) as h:
                                target = winreg.QueryValue(h, None)
                            discovered[key] = safe_launch_path(target)
                            break
                        except (FileNotFoundError, OSError, LaunchError):
                            pass
                    if key in discovered:
                        break
        except ImportError:
            pass
        dirs = shortcut_search_directories()
        seen = 0
        for directory in dirs:
            try:
                if not directory.is_dir():
                    continue
            except OSError:
                continue
            for root, subdirs, filenames in os.walk(directory, followlinks=False, onerror=lambda _: None):
                kept = []
                for name in subdirs:
                    try:
                        if not Path(root, name).is_symlink():
                            kept.append(name)
                    except OSError:
                        pass
                subdirs[:] = kept
                for filename in sorted(filenames):
                    seen += 1
                    if seen > 6000:
                        break
                    if not filename.lower().endswith(".lnk"):
                        continue
                    stem = Path(filename).stem.casefold().strip()
                    if any(word in stem for word in BAD_SHORTCUT_WORDS):
                        continue
                    for key, preset in PRESETS.items():
                        if key in discovered:
                            continue
                        if any(stem == term or stem.startswith(term + " ")
                               for term in preset["terms"]):
                            try:
                                discovered[key] = safe_launch_path(str(Path(root) / filename))
                            except LaunchError:
                                pass
                if seen > 6000:
                    break
            if seen > 6000:
                break
        with self._lock:
            self._discovered = discovered
            self._native_icons.clear()

    def native_icon(self, entry):
        if self.platform != "win32" or not entry["ready"]:
            return None
        path = entry["path"]
        try:
            stamp = Path(path).stat().st_mtime_ns
        except OSError:
            return None
        key = (path, stamp)
        with self._lock:
            if key in self._native_icons:
                return self._native_icons[key]
        from .icons import windows_pixels
        try:
            image = windows_pixels(self.target(entry["id"]))
        except (OSError, ValueError):
            image = None
        with self._lock:
            if len(self._native_icons) >= 64:
                self._native_icons.clear()
            self._native_icons[key] = image
        return image

    def restore_presets(self):
        with self._lock:
            self._hidden.clear()
            self._persist()

    def list_apps(self) -> list[dict]:
        with self._lock:
            items = []
            for key, spec in PRESETS.items():
                if key in self._hidden:
                    continue
                override = self._custom.get(key)
                found = self._discovered.get(key)
                path = override["path"] if override else found
                items.append({"id": key, "name": spec["name"], "ready": bool(path and Path(path).is_file()),
                              "source": "saved" if override else "found" if found else "missing",
                              "path": path or ""})
            for key, custom in sorted(self._custom.items()):
                if key not in PRESETS:
                    items.append({"id": key, "name": custom["name"],
                                  "ready": Path(custom["path"]).is_file(),
                                  "source": "saved", "path": custom["path"]})
            return items

    def save(self, app_id: str, name: str, path: str) -> dict:
        if self.platform != "win32":
            raise LaunchError("Uygulama başlatma yalnız Windows'ta kullanılabilir.")
        if not isinstance(app_id, str) or not KEY_RE.fullmatch(app_id):
            raise LaunchError("Uygulama kimliği geçersiz.")
        if not isinstance(name, str) or not NAME_RE.fullmatch(name.strip()):
            raise LaunchError("Uygulama adı geçersiz.")
        checked = safe_launch_path(path)
        with self._lock:
            if app_id not in self._custom and len(self._custom) >= 24:
                raise LaunchError("En fazla 24 uygulama eklenebilir.")
            self._custom[app_id] = {"name": PRESETS[app_id]["name"] if app_id in PRESETS else name.strip(),
                                    "path": checked}
            self._persist()
        return {"id": app_id, "name": name.strip(), "path": checked}

    def remove(self, app_id: str) -> None:
        with self._lock:
            if not isinstance(app_id, str) or (app_id not in self._custom and app_id not in PRESETS):
                raise LaunchError("Kayıtlı uygulama bulunamadı.")
            if app_id in PRESETS:
                self._hidden.add(app_id)
            self._custom.pop(app_id, None)
            self._persist()

    def target(self, app_id: str) -> str:
        """Launch only an explicitly selected entry; never a freeform chat instruction."""
        if self.platform != "win32":
            raise LaunchError("Uygulama başlatma yalnız Windows'ta kullanılabilir.")
        with self._lock:
            if app_id in self._custom:
                path = self._custom[app_id]["path"]
            elif app_id in PRESETS and app_id not in self._hidden and app_id in self._discovered:
                path = self._discovered[app_id]
            else:
                raise LaunchError("Uygulama bulunamadı. Uygulamalar bölümünden yol ekle.")
        path = safe_launch_path(path)
        if path.lower().endswith(".lnk"):
            path = shortcut_executable(path)
        return path

    def launch(self, app_id: str, expected=None) -> None:
        path = self.target(app_id)
        if expected is not None and expected != path:
            raise LaunchError("Uygulama hedefi değişti. Yeniden kontrol et.")
        try:
            self._start_process([path], shell=False, cwd=str(Path(path).parent), close_fds=True)
        except OSError as exc:
            raise LaunchError("Windows uygulamayı başlatamadı.") from None


def shortcut_executable(path):
    # Read shortcut metadata only. The shortcut itself is never executed.
    exe = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    script = ("[Console]::InputEncoding=[Text.UTF8Encoding]::new($false);"
              "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"
              "$p=[Console]::In.ReadToEnd();"
              "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($p);"
              "@{target=$s.TargetPath;args=$s.Arguments}|ConvertTo-Json -Compress")
    try:
        result = subprocess.run([str(exe), "-NoProfile", "-NonInteractive", "-Command", script],
                                input=path, text=True, encoding="utf-8", capture_output=True,
                                timeout=5, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        info = json.loads(result.stdout)
        if info.get("args") or not isinstance(info.get("target"), str) or not info["target"].lower().endswith(".exe"):
            raise LaunchError("Argümansız yerel EXE hedefi gerekli. Programı doğrudan seç.")
        return safe_launch_path(info["target"])
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        raise LaunchError("Kısayol hedefi okunamadı. EXE dosyasını seç.") from None


def choose_executable() -> str:
    """Show local Windows-native file picker on a direct user request."""
    if sys.platform != "win32":
        raise LaunchError("Dosya seçici yalnız Windows'ta kullanılabilir.")
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            path = filedialog.askopenfilename(
                parent=root,
                title="Açılacak uygulamayı seç",
                filetypes=[("Uygulamalar", "*.exe *.lnk"), ("Tüm dosyalar", "*.*")],
            )
        finally:
            root.destroy()
        return safe_launch_path(path) if path else ""
    except (OSError, ImportError) as exc:
        raise LaunchError("Windows dosya seçicisi açılamadı.") from None
