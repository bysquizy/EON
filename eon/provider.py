"""Modelle yalnızca 127.0.0.1:11434 üzerinden konuşur.

Uzak URL, proxy, HTTP yönlendirmesi ve otomatik model indirme yok.
"""
import http.client
import json
from typing import Callable

from .config import ALLOWED_MODELS, OLLAMA_HOST, OLLAMA_PORT, LocalSettings

class LocalModelError(RuntimeError):
    pass

class LocalOllama:
    MAX_RESPONSE_BYTES = 2 * 1024 * 1024

    def __init__(
        self, settings: LocalSettings,
        connection_factory: Callable[..., http.client.HTTPConnection] = http.client.HTTPConnection
    ):
        if settings.model not in ALLOWED_MODELS:
            raise ValueError("İzin verilmeyen model.")
        self.settings = settings
        self._connection_factory = connection_factory

    def _call(self, method: str, route: str, payload=None) -> dict:
        if route not in ("/api/tags", "/api/chat"):
            raise LocalModelError("İzin verilmeyen yerel yol.")
        if (method, route) not in (("GET", "/api/tags"), ("POST", "/api/chat")):
            raise LocalModelError("İzin verilmeyen istek.")
        connection = self._connection_factory(
            OLLAMA_HOST, OLLAMA_PORT, timeout=self.settings.timeout_seconds
        )
        try:
            body = None
            headers = {"Accept": "application/json"}
            if payload is not None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                if len(body) > 64 * 1024:
                    raise LocalModelError("İstek çok büyük.")
                headers["Content-Type"] = "application/json"
            connection.request(method, route, body=body, headers=headers)
            response = connection.getresponse()
            # Yönlendirme izlenmez. Yanıtta URL varsa bile hiçbir yere bağlanılmaz.
            if response.status != 200:
                raise LocalModelError(f"Yerel Ollama yanıt vermedi (HTTP {response.status}).")
            raw = response.read(self.MAX_RESPONSE_BYTES + 1)
            if len(raw) > self.MAX_RESPONSE_BYTES:
                raise LocalModelError("Yerel modelin yanıtı çok büyük.")
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise LocalModelError("Beklenmedik Ollama yanıtı.")
            return data
        except (OSError, TimeoutError, json.JSONDecodeError, UnicodeError) as exc:
            raise LocalModelError(
                "Ollama'ya yerel bağlantı kurulamadı veya yanıt okunamadı."
            ) from None
        finally:
            connection.close()

    def installed_models(self) -> set[str]:
        data = self._call("GET", "/api/tags")
        return {
            obj["name"] for obj in data.get("models", [])
            if isinstance(obj, dict) and isinstance(obj.get("name"), str)
        }

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
                "temperature": 0.5,
            },
        })
        message = data.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise LocalModelError("Model okunabilir bir yanıt üretmedi.")
        return message["content"].strip() or "(Boş yanıt)"
