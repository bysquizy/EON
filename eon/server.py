"""Same-origin loopback web UI with CSRF token and explicit action endpoints."""
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from urllib.parse import urlsplit

from .service import EonService
from .launcher import LaunchError, choose_executable
from .provider import LocalModelError

ASSET_DIR = Path(__file__).parent / "ui"
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}


class EonServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, service: EonService, port: int = 0):
        super().__init__(("127.0.0.1", port), EonHandler)
        self.service = service
        self.token = secrets.token_urlsafe(32)

    @property
    def origin(self):
        return f"http://127.0.0.1:{self.server_port}"


class EonHandler(BaseHTTPRequestHandler):
    server_version = "EON"
    sys_version = ""

    def log_message(self, fmt, *args):
        # Never log message content, application paths, or sensitive query data.
        pass

    def _headers(self, status: int, type_: str, size: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
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
        if path == "/api/bootstrap":
            return self._json(200, {"token": self.server.token, "state": self.server.service.snapshot(),
                                    "models": self.server.service.models(),
                                    "apps": self.server.service.launcher.list_apps()})
        if path == "/api/health":
            return self._json(200, {"status": "ok", "version": "0.0.3"})
        if path == "/api/state":
            return self._json(200, self.server.service.snapshot())
        if path == "/api/models":
            return self._json(200, self.server.service.models())
        if path == "/api/apps":
            return self._json(200, {"apps": self.server.service.launcher.list_apps()})
        return self._json(404, {"error": "Sayfa bulunamadı."})

    def do_POST(self):
        if not self._host_ok():
            return self._json(403, {"error": "Geçersiz adres."})
        origin = self.headers.get("Origin", "")
        token = self.headers.get("X-EON-Token", "")
        if (origin != self.server.origin or not token
                or not hmac.compare_digest(token, self.server.token)
                or self.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none")):
            return self._json(403, {"error": "İstek doğrulanamadı."})
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            return self._json(415, {"error": "JSON istek gerekli."})
        try:
            content_length = int(self.headers.get("Content-Length", "-1"))
            if not 0 <= content_length <= 16000:
                return self._json(413, {"error": "İstek çok büyük."})
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            if not isinstance(payload, dict):
                return self._json(400, {"error": "Geçersiz veri."})
        except (TypeError, ValueError, UnicodeError):
            return self._json(400, {"error": "Geçersiz JSON."})
        service = self.server.service
        route = urlsplit(self.path).path
        try:
            if route == "/api/message":
                result = service.send(payload.get("text", ""))
            elif route == "/api/regenerate":
                result = service.regenerate()
            elif route == "/api/chats/new":
                result = service.new_chat()
            elif route == "/api/chats/open":
                result = service.open_chat(payload.get("id", ""))
            elif route == "/api/chats/delete":
                result = service.delete_chat(payload.get("id", ""))
            elif route == "/api/summary":
                result = service.summary()
            elif route == "/api/model":
                result = service.select_model(payload.get("model", ""))
            elif route == "/api/length":
                result = service.select_length(payload.get("style", ""))
            elif route == "/api/clear":
                result = service.clear()
            elif route == "/api/apps/refresh":
                service.launcher.refresh()
                result = {"apps": service.launcher.list_apps()}
            elif route == "/api/apps/save":
                result = service.launcher.save(payload.get("id", ""), payload.get("name", ""), payload.get("path", ""))
            elif route == "/api/apps/remove":
                service.launcher.remove(payload.get("id", ""))
                result = {"apps": service.launcher.list_apps()}
            elif route == "/api/apps/launch":
                if not isinstance(payload.get("id"), str):
                    raise LaunchError("Geçersiz uygulama.")
                service.launcher.launch(payload["id"])
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
