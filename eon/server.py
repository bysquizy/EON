"""Same-origin loopback web UI with CSRF token and explicit action endpoints."""
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import re
import threading
from urllib.parse import urlsplit

from .service import EonService
from .launcher import LaunchError, choose_executable
from .provider import LocalModelError

ASSET_DIR = Path(__file__).parent / "ui"
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/workspace.js": ("workspace.js", "application/javascript; charset=utf-8"),
    "/chat.js": ("chat.js", "application/javascript; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/studio.js": ("studio.js", "application/javascript; charset=utf-8"),
    "/hybrid.js": ("hybrid.js", "application/javascript; charset=utf-8"),
    "/theme.css": ("theme.css", "text/css; charset=utf-8"),
    "/extras.js": ("extras.js", "application/javascript; charset=utf-8"),
}


class EonServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, service: EonService, port: int = 0):
        super().__init__(("127.0.0.1", port), EonHandler)
        self.service = service
        self.token = secrets.token_urlsafe(32)
        self.access = secrets.token_urlsafe(32)

    @property
    def origin(self):
        return f"http://127.0.0.1:{self.server_port}"


class EonHandler(BaseHTTPRequestHandler):
    server_version = "EON"
    sys_version = ""

    def log_message(self, fmt, *args):
        # Never log message content, application paths, or sensitive query data.
        pass

    def _headers(self, status: int, type_: str, size: int | None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", type_)
        if size is not None:
            self.send_header("Content-Length", str(size))
        else:
            self.send_header("Connection", "close")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Permissions-Policy", "geolocation=(), camera=(), microphone=(), clipboard-read=(self), clipboard-write=(self)")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        self.end_headers()

    def _json(self, status: int, value: dict) -> None:
        output = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(output))
        self.wfile.write(output)

    def _host_ok(self) -> bool:
        return self.headers.get("Host", "") == f"127.0.0.1:{self.server.server_port}"

    def _authorized(self):
        return (self.headers.get("Sec-Fetch-Site", "same-origin") in ("same-origin", "none")
                and self.headers.get("Origin", self.server.origin) == self.server.origin
                and hmac.compare_digest(self.headers.get("X-EON-Access", "").encode(), self.server.access.encode()))

    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"error": "Geçersiz adres."})
        path = urlsplit(self.path).path
        if path in ASSETS:
            file_name, media = ASSETS[path]
            content = (ASSET_DIR / file_name).read_bytes()
            self._headers(200, media, len(content))
            self.wfile.write(content)
            return
        if path.startswith("/api/") and path != "/api/health" and not self._authorized():
            return self._json(403, {"error":"EON başlatıcısındaki bağlantıyı kullan."})
        if path == "/api/bootstrap":
            return self._json(200, {"token": self.server.token, "state": self.server.service.snapshot(),
                                    "models": self.server.service.models(),
                                    "apps": self.server.service.apps()})
        if path == "/api/health":
            return self._json(200, {"status": "ok", "version": "0.4.0"})
        if path == "/api/state":
            return self._json(200, self.server.service.snapshot())
        if path == "/api/models":
            return self._json(200, self.server.service.models(refresh=True))
        if path == "/api/apps":
            return self._json(200, {"apps": self.server.service.apps(include_native=True)})
        return self._json(404, {"error": "Sayfa bulunamadı."})

    def _deny_post(self, message):
        # Consume a small pending body before closing to avoid a TCP reset on Windows.
        try:
            size = int(self.headers.get("Content-Length","0"))
            if 0 < size <= 16000 and not self.headers.get("Transfer-Encoding"):
                self.connection.settimeout(1)
                self.rfile.read(size)
        except (ValueError,OSError):
            pass
        return self._json(403, {"error":message})

    def do_POST(self):
        if not self._host_ok():
            return self._deny_post("Geçersiz adres.")
        origin = self.headers.get("Origin", "")
        token = self.headers.get("X-EON-Token", "")
        if (not self._authorized() or origin != self.server.origin or not token
                or not hmac.compare_digest(token.encode(), self.server.token.encode())
                or self.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none")):
            return self._deny_post("İstek doğrulanamadı.")
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            return self._json(415, {"error": "JSON istek gerekli."})
        try:
            content_length = int(self.headers.get("Content-Length", "-1"))
            limit = 24*1024*1024 if self.path == "/api/backup/restore" else 16000
            if not 0 <= content_length <= limit:
                return self._json(413, {"error": "İstek çok büyük."})
            if self.headers.get("Transfer-Encoding"):
                return self._json(400, {"error":"Aktarım biçimi desteklenmiyor."})
            self.connection.settimeout(12)
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            self.connection.settimeout(None)
            if not isinstance(payload, dict):
                return self._json(400, {"error": "Geçersiz veri."})
        except (OSError, TypeError, ValueError, UnicodeError):
            return self._json(400, {"error": "Geçersiz JSON."})
        service = self.server.service
        route = urlsplit(self.path).path
        try:
            if route == "/api/stream":
                key = payload.get("key")
                if not isinstance(key, str) or not re.fullmatch(r"[a-zA-Z0-9-]{16,64}", key) or not isinstance(payload.get("id"), str):
                    raise ValueError("Geçersiz sohbet isteği.")
                self._headers(200, "application/x-ndjson; charset=utf-8", None)
                def event(value):
                    self.wfile.write(json.dumps(value, ensure_ascii=False).encode() + b"\n")
                    self.wfile.flush()
                try:
                    result = service.generate(text=payload.get("text"), chat_id=payload["id"],
                                              key=key, edit_index=payload.get("index"), destination=payload.get("destination", "ollama"),
                                              emit=lambda part: event({"delta": part}),
                                              ready=lambda: event({"ready": True}))
                    event({"state": result["state"]})
                except (ValueError, LocalModelError) as exc:
                    event({"error": str(exc)})
                except OSError:
                    pass
                return
            elif route == "/api/stop":
                result = service.cancel(payload.get("key"))
            elif route == "/api/search":
                result = service.search(payload.get("query", ""), payload.get("favorites", False), payload.get("project"))
            elif route in {"/api/library/" + kind for kind in ("project", "mode", "look", "configure", "pin", "star")}:
                result = service.library_action(route.rsplit("/", 1)[1], payload)
            elif route == "/api/credentials":
                result = service.credentials_action(payload.get("action"), payload.get("model"), payload.get("consent"))
            elif route == "/api/cloud/new":
                result = service.cloud_chat(payload.get("model"), payload.get("id"), payload.get("consent"),
                                            payload.get("memory"), payload.get("instructions"))
            elif route == "/api/compare":
                result = service.compare(payload.get("model"),payload.get("consent"))
            elif route == "/api/apps/windows-icon":
                from .icons import windows_pixels
                ident = payload.get("id")
                app = next((x for x in service.launcher.list_apps() if x["id"] == ident and x["ready"]), None)
                if not app:
                    raise ValueError("Uygulama bulunamadı.")
                result = service.save_icon(ident, windows_pixels(service.launcher.target(ident)))
            elif route == "/api/apps/icon":
                result = service.save_icon(payload.get("id"), payload.get("pixels"))
            elif route == "/api/extras":
                result = service.extra_action(payload)
            elif route == "/api/backup/export":
                from copy import deepcopy
                with service._lock:
                    result = deepcopy(service.backup_data())
            elif route == "/api/backup/restore":
                result = service.restore_data(payload)
            elif route == "/api/runtime":
                result = service.runtime_action(payload.get("action"), payload.get("value"))
            elif route == "/api/weather/preferences":
                result = service.weather_settings(payload)
            elif route == "/api/weather":
                result = service.weather_report(payload.get("consent"))
            elif route == "/api/preferences":
                result = service.preferences(payload.get("instructions"), payload.get("context"), payload.get("output"))
            elif route == "/api/memory":
                result = service.memory_edit(payload.get("id", ""), payload.get("value"))
            elif route == "/api/chats/rename":
                result = service.rename(payload.get("id"), payload.get("title"))
            elif route == "/api/message":
                if service.cloud_chats.get(service.chats.active_id):
                    raise ValueError("Gemini için sohbetin akışlı Gönder düğmesini kullan.")
                result = service.send(payload.get("text", ""))
            elif route == "/api/regenerate":
                result = service.generate(destination="ollama")
            elif route == "/api/chats/new":
                result = service.new_chat()
            elif route == "/api/chats/open":
                result = service.open_chat(payload.get("id", ""))
            elif route == "/api/chats/delete":
                result = service.delete_chat(payload.get("id", ""))
            elif route == "/api/summary":
                result = service.summary(payload.get("id"), payload.get("destination","ollama"))
            elif route == "/api/model":
                result = service.select_model(payload.get("model", ""))
            elif route == "/api/length":
                result = service.select_length(payload.get("style", ""))
            elif route == "/api/clear":
                result = service.clear()
            elif route == "/api/apps/refresh":
                service.launcher.refresh()
                result = {"apps": service.apps(include_native=True)}
            elif route == "/api/apps/restore":
                service.launcher.restore_presets()
                result = {"apps": service.apps()}
            elif route == "/api/apps/save":
                result = service.launcher.save(payload.get("id", ""), payload.get("name", ""), payload.get("path", ""))
            elif route == "/api/apps/remove":
                service.launcher.remove(payload.get("id", ""))
                result = {"apps": service.apps()}
            elif route == "/api/apps/target":
                result = {"target":service.launcher.target(payload.get("id"))}
            elif route == "/api/apps/launch":
                if not isinstance(payload.get("id"), str):
                    raise LaunchError("Geçersiz uygulama.")
                if not isinstance(payload.get("target"), str):
                    raise LaunchError("Önce uygulama hedefini onayla.")
                service.launcher.launch(payload["id"], payload["target"])
                result = {"started": True}
            elif route == "/api/apps/pick":
                result = {"path": choose_executable()}
            else:
                return self._json(404, {"error": "İşlem bulunamadı."})
            return self._json(200, result)
        except (ValueError, LaunchError) as exc:
            return self._json(400, {"error": str(exc)})
        except LocalModelError as exc:
            return self._json(502, {"error": str(exc)})
        except Exception:
            # Avoid disclosing environment paths, tokens or machine identifiers.
            return self._json(500, {"error": "İşlem tamamlanamadı. Ayrıntılar için uygulamayı kontrol et."})


def start_server(*, service=None, port=0) -> EonServer:
    return EonServer(service or EonService(), port=port)
