"""Ollama client. All HTTP calls are fixed to 127.0.0.1; redirects are never followed."""
import http.client
import json
from typing import Callable

from .config import LocalSettings, OLLAMA_HOST, OLLAMA_PORT, valid_model


class LocalModelError(RuntimeError):
    pass


class LocalOllama:
    MAX_RESPONSE_BYTES = 2 * 1024 * 1024

    def __init__(self, settings: LocalSettings,
                 connection_factory: Callable[..., http.client.HTTPConnection] = http.client.HTTPConnection):
        if not valid_model(settings.model):
            raise ValueError("İzin verilmeyen model.")
        self.settings = settings
        self._factory = connection_factory

    def _call(self, method: str, route: str, payload=None) -> dict:
        if (method, route) not in (("GET", "/api/tags"), ("POST", "/api/chat")):
            raise LocalModelError("Ollama için izin verilmeyen API yolu.")
        conn = self._factory(OLLAMA_HOST, OLLAMA_PORT, timeout=self.settings.timeout_seconds)
        try:
            body = None
            headers = {"Accept": "application/json"}
            if payload is not None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                if len(body) > 64 * 1024:
                    raise LocalModelError("Model isteği çok büyük.")
                headers["Content-Type"] = "application/json"
            conn.request(method, route, body=body, headers=headers)
            response = conn.getresponse()
            if response.status != 200:
                raise LocalModelError(f"Ollama HTTP {response.status} hatası verdi.")
            data_bytes = response.read(self.MAX_RESPONSE_BYTES + 1)
            if len(data_bytes) > self.MAX_RESPONSE_BYTES:
                raise LocalModelError("Ollama yanıtı çok büyük.")
            data = json.loads(data_bytes.decode("utf-8"))
            if not isinstance(data, dict):
                raise LocalModelError("Beklenmeyen Ollama yanıtı.")
            return data
        except (OSError, TimeoutError, UnicodeError, ValueError) as exc:
            if isinstance(exc, LocalModelError):
                raise
            raise LocalModelError("Yerel Ollama bağlantısı veya yanıtı okunamadı.") from None
        finally:
            conn.close()

    def installed_models(self) -> list[str]:
        data = self._call("GET", "/api/tags")
        results = []
        models = data.get("models", [])
        if not isinstance(models, list):
            raise LocalModelError("Model listesi okunamadı.")
        for entry in models:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if (valid_model(name)
                and not entry.get("remote_host")
                and not entry.get("remote_model")
                and name not in results):
                results.append(name)
        return sorted(results, key=str.casefold)

    def chat(self, messages: list[dict[str, str]]) -> str:
        data = self._call("POST", "/api/chat", {
            "model": self.settings.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "keep_alive": "3m",
            "options": {
                "num_ctx": self.settings.context_tokens,
                "num_predict": self.settings.output_tokens,
                "temperature": 0.55,
            },
        })
        message = data.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise LocalModelError("Ollama kullanılabilir bir yanıt vermedi.")
        return message["content"].strip() or "(Boş yanıt)"
