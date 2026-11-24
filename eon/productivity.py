"""EON Focus & Tasks, Vision image validator, Windows SAPI TTS helper, and System Health inspector."""
from __future__ import annotations

import base64
import ctypes
from datetime import datetime, timezone
import os
import re
import secrets
import struct
import subprocess
import sys
import threading
import time


ALLOWED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp"}
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_IMAGE_DIMENSION = 4096


def validate_vision_image(mime: str, data_b64: str) -> dict:
    if not isinstance(mime, str) or mime.lower() not in ALLOWED_IMAGE_MIMES:
        raise ValueError("Desteklenmeyen görsel türü. Yalnız PNG, JPEG ve WebP kabul edilir.")
    if not isinstance(data_b64, str) or not data_b64:
        raise ValueError("Görsel verisi boş.")
    try:
        raw = base64.b64decode(data_b64, validate=True)
    except Exception:
        raise ValueError("Görsel Base64 verisi geçersiz.") from None
    if len(raw) < 24 or len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("Görsel boyutu 24 bayt ile 4 MiB arasında olmalı.")

    mime = mime.lower()
    width = height = 0
    if mime == "image/png":
        if raw[:8] != b"\x89PNG\r\n\x1a\n" or raw[12:16] != b"IHDR":
            raise ValueError("PNG başlığı doğrulanamadı.")
        width, height = struct.unpack(">II", raw[16:24])
    elif mime == "image/jpeg":
        if raw[:2] != b"\xff\xd8":
            raise ValueError("JPEG başlığı doğrulanamadı.")
        p = 2
        while p + 9 < len(raw) and raw[p] == 0xFF:
            marker = raw[p + 1]
            size = struct.unpack(">H", raw[p + 2:p + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2):
                height, width = struct.unpack(">HH", raw[p + 5:p + 9])
                break
            if size < 2 or marker == 0xDA:
                break
            p += size + 2
    elif mime == "image/webp":
        if len(raw) >= 30 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            tag = raw[12:16]
            if tag == b"VP8 " and raw[23:26] == b"\x9d\x01\x2a":
                w, h = struct.unpack("<HH", raw[26:30])
                width, height = w & 0x3FFF, h & 0x3FFF
            elif tag == b"VP8L" and raw[20] == 0x2F:
                dims = struct.unpack("<I", raw[21:25])[0]
                width, height = 1 + (dims & 0x3FFF), 1 + ((dims >> 14) & 0x3FFF)
            elif tag == b"VP8X" and len(raw) >= 30:
                width = 1 + int.from_bytes(raw[24:27], "little")
                height = 1 + int.from_bytes(raw[27:30], "little")

    if width <= 0 or height <= 0 or width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise ValueError(f"Görsel boyutları geçersiz veya {MAX_IMAGE_DIMENSION}px sınırını aşıyor.")
    return {
        "mime": mime,
        "data": base64.b64encode(raw).decode("ascii"),
        "width": width,
        "height": height,
        "size": len(raw),
    }


def system_memory_info() -> dict:
    """Measure Windows system RAM separately from Ollama model RAM/VRAM."""
    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            total = int(stat.ullTotalPhys)
            avail = int(stat.ullAvailPhys)
            return {
                "total_bytes": total,
                "used_bytes": max(0, total - avail),
                "available_bytes": avail,
                "percent": int(stat.dwMemoryLoad),
                "source": "Windows GlobalMemoryStatusEx (fiziksel sistem RAM'i)",
            }
    return {
        "total_bytes": None,
        "used_bytes": None,
        "available_bytes": None,
        "percent": None,
        "source": "İşletim sistemi bellek API'si bu platformda etkin değil",
    }


NATURAL_VOICES = {
    "Kore": {"name": "Kore — Stüdyo HD Kadın", "lang": "tr-TR", "gender": "Female", "studio": True},
    "Aoede": {"name": "Aoede — Stüdyo HD Sıcak Kadın", "lang": "tr-TR", "gender": "Female", "studio": True},
    "Charon": {"name": "Charon — Stüdyo HD Doğal Erkek", "lang": "tr-TR", "gender": "Male", "studio": True},
    "Puck": {"name": "Puck — Stüdyo HD Enerjik Erkek", "lang": "tr-TR", "gender": "Male", "studio": True},
    "Zephyr": {"name": "Zephyr — Stüdyo HD Akıcı Asistan", "lang": "tr-TR", "gender": "Female", "studio": True},
    "tr-TR-AhmetNeural": {"name": "Ahmet — Çevrimdışı Erkek", "lang": "tr-TR", "gender": "Male"},
    "tr-TR-EmelNeural": {"name": "Emel — Çevrimdışı Kadın", "lang": "tr-TR", "gender": "Female"},
    "en-US-AndrewMultilingualNeural": {"name": "Andrew — Çevrimdışı Çok Dilli Erkek", "lang": "en-US", "gender": "Male"},
    "en-US-AvaMultilingualNeural": {"name": "Ava — Çevrimdışı Çok Dilli Kadın", "lang": "en-US", "gender": "Female"},
}
DEFAULT_NEURAL_VOICE = "Kore"

STUDIO_VOICE_MAP = {
    "Kore": "Kore",
    "Aoede": "Aoede",
    "Charon": "Charon",
    "Puck": "Puck",
    "Zephyr": "Zephyr",
    "tr-TR-AhmetNeural": "Charon",
    "tr-TR-EmelNeural": "Kore",
    "en-US-AndrewMultilingualNeural": "Puck",
    "en-US-AvaMultilingualNeural": "Aoede",
}


def clean_speech_text(text: str) -> str:
    """Strip Markdown syntax so the voice reads natural sentences."""
    if not isinstance(text, str):
        return ""
    s = re.sub(r"```[\s\S]*?```", " Kod bloğu. ", text)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"\*([^*]+)\*", r"\1", s)
    s = re.sub(r"^[#>*\-+]+\s*", "", s, flags=re.MULTILINE)
    s = re.sub(r"\|", ", ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:1800]


class VoiceEngine:
    """Speech output that never sends text to a third party.

    Preferred path: the app window's own speechSynthesis voices (Edge ships free "Natural" voices locally).
    Fallback path: Windows System.Speech (SAPI) started on demand, stoppable with one click.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self.voice = DEFAULT_NEURAL_VOICE
        self.rate = "+2%"
        self.pitch = "+0Hz"
        self.auto_speak = False

    def voices(self) -> dict:
        return {
            "voices": [{"id": k, **v} for k, v in NATURAL_VOICES.items()],
            "selected": self.voice,
            "rate": self.rate,
            "pitch": self.pitch,
            "auto_speak": self.auto_speak,
        }

    def configure(self, *, voice=None, rate=None, pitch=None, auto_speak=None) -> dict:
        with self._lock:
            if voice is not None:
                if voice not in NATURAL_VOICES:
                    raise ValueError("Desteklenmeyen ses profili.")
                self.voice = voice
            if rate is not None and re.fullmatch(r"[+-]?\d{1,2}%", str(rate)):
                self.rate = str(rate)
            if pitch is not None and re.fullmatch(r"[+-]?\d{1,2}Hz", str(pitch)):
                self.pitch = str(pitch)
            if type(auto_speak) is bool:
                self.auto_speak = auto_speak
            return self.voices()

    def speak(self, text: str, *, voice: str | None = None, engine: str = "browser") -> dict:
        cleaned = clean_speech_text(text)
        if not cleaned:
            raise ValueError("Seslendirilecek metin boş.")
        self.stop()
        chosen = voice if voice in NATURAL_VOICES else self.voice
        if engine != "sapi" or sys.platform != "win32":
            return {"supported": True, "speaking": True, "engine": "browser_natural", "voice": chosen, "cleaned_text": cleaned}
        exe = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        if not os.path.isfile(exe):
            return {"supported": False, "notice": "Yerel Windows ses motoru bulunamadı."}
        script = (
            "[Console]::InputEncoding=[Text.UTF8Encoding]::new($false);"
            "$t=[Console]::In.ReadToEnd();"
            "Add-Type -AssemblyName System.Speech;"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$s.Speak($t)"
        )
        with self._lock:
            try:
                proc = subprocess.Popen(
                    [exe, "-NoProfile", "-NonInteractive", "-Command", script],
                    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                assert proc.stdin is not None
                proc.stdin.write(cleaned.encode("utf-8"))
                proc.stdin.close()
                self._proc = proc
                return {"supported": True, "speaking": True, "engine": "windows_sapi", "voice": chosen}
            except OSError:
                return {"supported": False, "notice": "Yerel Windows ses motoru başlatılamadı."}

    def stop(self) -> dict:
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                try:
                    self._proc.terminate()
                except OSError:
                    pass
            self._proc = None
        return {"speaking": False}


class ProductivityCenter:
    """Daily Tasks, Pomodoro sessions, and ICS import/export."""

    def __init__(self):
        self._lock = threading.RLock()
        self.tasks: dict[str, dict] = {}
        self.focus_sessions: list[dict] = []

    def dump(self) -> dict:
        with self._lock:
            return {
                "tasks": dict(self.tasks),
                "focus_sessions": list(self.focus_sessions[-100:]),
            }

    def restore(self, data: dict) -> None:
        if not isinstance(data, dict):
            return
        with self._lock:
            raw_tasks = data.get("tasks", {})
            if isinstance(raw_tasks, dict):
                cleaned = {}
                for tid, t in list(raw_tasks.items())[:100]:
                    if isinstance(tid, str) and isinstance(t, dict) and isinstance(t.get("title"), str):
                        cleaned[tid] = {
                            "id": tid,
                            "title": t["title"].strip()[:200],
                            "done": bool(t.get("done", False)),
                            "project": str(t.get("project", ""))[:64],
                            "due": str(t.get("due", ""))[:32],
                            "source": str(t.get("source", "user"))[:32],
                            "created_at": int(t.get("created_at", int(time.time()))),
                        }
                self.tasks = cleaned
            raw_focus = data.get("focus_sessions", [])
            if isinstance(raw_focus, list):
                self.focus_sessions = [
                    {
                        "minutes": int(s.get("minutes", 25)),
                        "label": str(s.get("label", "Odak"))[:80],
                        "completed_at": int(s.get("completed_at", 0)),
                    }
                    for s in raw_focus[-100:]
                    if isinstance(s, dict)
                ]

    def add_task(self, title: str, *, project: str = "", due: str = "", source: str = "user") -> dict:
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
            raise ValueError("Görev başlığı 1–200 karakter olmalı.")
        with self._lock:
            if len(self.tasks) >= 100:
                raise ValueError("En fazla 100 görev saklanabilir.")
            tid = secrets.token_hex(6)
            record = {
                "id": tid,
                "title": title.strip(),
                "done": False,
                "project": str(project or "")[:64],
                "due": str(due or "").strip()[:32],
                "source": str(source or "user")[:32],
                "created_at": int(time.time()),
            }
            self.tasks[tid] = record
            return record

    def update_task(self, task_id: str, *, done: bool | None = None, title: str | None = None, due: str | None = None) -> dict:
        with self._lock:
            if task_id not in self.tasks:
                raise ValueError("Görev bulunamadı.")
            t = self.tasks[task_id]
            if done is not None:
                t["done"] = bool(done)
            if title is not None:
                if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
                    raise ValueError("Görev başlığı geçersiz.")
                t["title"] = title.strip()
            if due is not None:
                t["due"] = str(due).strip()[:32]
            return dict(t)

    def delete_task(self, task_id: str) -> None:
        with self._lock:
            if task_id not in self.tasks:
                raise ValueError("Görev bulunamadı.")
            del self.tasks[task_id]

    def log_focus(self, minutes: int, label: str = "Odak Oturumu") -> dict:
        if type(minutes) is not int or not 1 <= minutes <= 240:
            raise ValueError("Odak süresi 1–240 dakika arasında olmalı.")
        entry = {
            "minutes": minutes,
            "label": str(label or "Odak Oturumu").strip()[:80],
            "completed_at": int(time.time()),
        }
        with self._lock:
            self.focus_sessions.append(entry)
            if len(self.focus_sessions) > 100:
                self.focus_sessions = self.focus_sessions[-100:]
        return entry

    def summary(self) -> dict:
        with self._lock:
            all_tasks = sorted(self.tasks.values(), key=lambda x: (x["done"], -x["created_at"]))
            total = len(all_tasks)
            done = sum(1 for t in all_tasks if t["done"])
            today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
            today_focus_mins = sum(s["minutes"] for s in self.focus_sessions if s["completed_at"] >= today_start)
            total_focus_mins = sum(s["minutes"] for s in self.focus_sessions)
            return {
                "tasks": all_tasks,
                "total_tasks": total,
                "completed_tasks": done,
                "pending_tasks": total - done,
                "today_focus_minutes": today_focus_mins,
                "total_focus_minutes": total_focus_mins,
                "recent_focus": list(reversed(self.focus_sessions[-10:])),
            }

    def export_ics(self) -> str:
        with self._lock:
            now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            lines = [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:-//EON//Personal AI Workspace v0.5.0//TR",
            ]
            for t in self.tasks.values():
                uid = f"eon-task-{t['id']}@local"
                due_clean = re.sub(r"[^0-9]", "", t.get("due", ""))[:8]
                dt_str = due_clean if len(due_clean) == 8 else datetime.fromtimestamp(t["created_at"], timezone.utc).strftime("%Y%m%d")
                status = "COMPLETED" if t["done"] else "NEEDS-ACTION"
                clean_title = t["title"].replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", " ")
                lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{now_str}",
                    f"DTSTART;VALUE=DATE:{dt_str}",
                    f"SUMMARY:{clean_title}",
                    f"STATUS:{status}",
                    "END:VEVENT",
                ])
            lines.append("END:VCALENDAR")
            return "\r\n".join(lines) + "\r\n"

    def import_ics(self, raw_ics: str, project: str = "") -> int:
        if not isinstance(raw_ics, str) or "BEGIN:VCALENDAR" not in raw_ics:
            raise ValueError("Geçerli bir ICS takvim verisi bulunamadı.")
        count = 0
        for block in re.findall(r"BEGIN:(?:VEVENT|VTODO)(.*?)END:(?:VEVENT|VTODO)", raw_ics, re.DOTALL):
            m_sum = re.search(r"^SUMMARY(?:;[^:]*)?:(.+)$", block, re.MULTILINE)
            if not m_sum:
                continue
            title = m_sum.group(1).strip().replace("\\,", ",").replace("\\;", ";")[:200]
            m_dt = re.search(r"^(?:DTSTART|DUE)(?:;[^:]*)?:(\d{8})", block, re.MULTILINE)
            due = f"{m_dt.group(1)[:4]}-{m_dt.group(1)[4:6]}-{m_dt.group(1)[6:8]}" if m_dt else ""
            if title:
                self.add_task(title, project=project, due=due, source="ics")
                count += 1
                if count >= 40:
                    break
        if count == 0:
            raise ValueError("ICS dosyasında içe aktarılacak etkinlik veya görev bulunamadı.")
        return count
