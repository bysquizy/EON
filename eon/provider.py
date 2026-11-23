"""Ollama client. All HTTP calls are fixed to 127.0.0.1; redirects are never followed."""
import http.client
import json
from typing import Callable, Protocol


class StreamingProvider(Protocol):
    def stream(self, messages, emit, job): ...

from .config import LocalSettings, OLLAMA_HOST, OLLAMA_PORT, valid_model


class LocalModelError(RuntimeError):
    pass


class LocalOllama:
    MAX_RESPONSE_BYTES = 2 * 1024 * 1024

    def __init__(self, settings: LocalSettings,
                 connection_factory: Callable[..., http.client.HTTPConnection] = http.client.HTTPConnection,
                 profile: str = "balanced"):
        if not valid_model(settings.model):
            raise ValueError("İzin verilmeyen model.")
        self.settings = settings
        self._factory = connection_factory
        self.profile = profile if profile in ("fast", "balanced", "deep") else "balanced"
        self.tokens_per_second = None
        self.usage = None
        self.sources = []
        self._capabilities_cache = {}

    def _call(self, method: str, route: str, payload=None, max_body: int = 64 * 1024) -> dict:
        if (method, route) not in (("GET", "/api/tags"), ("POST", "/api/chat"), ("GET", "/api/ps"),
                                   ("POST", "/api/generate"), ("POST", "/api/show"), ("POST", "/api/embed")):
            raise LocalModelError("Ollama için izin verilmeyen API yolu.")
        timeout = 4 if method == "GET" else self.settings.timeout_seconds
        conn = self._factory(OLLAMA_HOST, OLLAMA_PORT, timeout=timeout)
        try:
            body = None
            headers = {"Accept": "application/json"}
            if payload is not None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                if len(body) > max_body:
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
        except (OSError, http.client.HTTPException, UnicodeError, ValueError) as exc:
            if isinstance(exc, LocalModelError):
                raise
            raise LocalModelError("Yerel Ollama bağlantısı veya yanıtı okunamadı.") from None
        finally:
            conn.close()

    def capabilities(self, model_name: str | None = None) -> dict:
        name = model_name or self.settings.model
        low = name.casefold()
        caps = {
            "provider": "ollama",
            "streaming": True,
            "vision": any(k in low for k in ("vision", "vl", "llava", "minicpm-v", "moondream", "gemma3", "pixtral")),
            "thinking": any(k in low for k in ("qwen3", "r1", "deepseek-r1", "qwq", "think", "gpt-oss")),
            "embeddings": any(k in low for k in ("embed", "nomic-embed", "bge", "mxbai", "all-minilm")),
            "web_search": False,
            "context_window": self.settings.context_tokens,
        }
        try:
            info = self._call("POST", "/api/show", {"model": name})
            raw_caps = info.get("capabilities")
            if isinstance(raw_caps, list):
                caps["vision"] = "vision" in raw_caps or caps["vision"]
                caps["thinking"] = "thinking" in raw_caps or caps["thinking"]
                caps["embeddings"] = "embedding" in raw_caps or caps["embeddings"]
            model_info = info.get("model_info")
            if isinstance(model_info, dict):
                for k, v in model_info.items():
                    if k.endswith(".context_length") and isinstance(v, int) and v > 0:
                        caps["context_window"] = v
                    if "vision" in k.casefold():
                        caps["vision"] = True
        except LocalModelError:
            pass
        return caps

    def embed(self, text: str, model_name: str | None = None) -> list[float]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Gömme için metin gerekli.")
        data = self._call("POST", "/api/embed", {"model": model_name or self.settings.model, "input": text[:8000]})
        embeddings = data.get("embeddings")
        if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
            return [float(x) for x in embeddings[0][:2048] if isinstance(x, (int, float))]
        raise LocalModelError("Ollama embedding yanıtı okunamadı.")

    def loaded(self):
        return [{"model": m.get("name"), "bytes": m.get("size"), "vram": m.get("size_vram"), "expires": m.get("expires_at"), "context": m.get("context_length")}
                for m in self._call("GET", "/api/ps").get("models", []) if isinstance(m, dict)]

    def unload(self):
        self._call("POST", "/api/generate", {"model":self.settings.model, "keep_alive":0, "stream":False})

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
        has_images = any(isinstance(m.get("images"), list) and m["images"] for m in messages)
        data = self._call("POST", "/api/chat", self._payload(messages, False), max_body=6 * 1024 * 1024 if has_images else 64 * 1024)
        message = data.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise LocalModelError("Ollama kullanılabilir bir yanıt vermedi.")
        prompt_eval = data.get("prompt_eval_count")
        eval_count = data.get("eval_count")
        eval_duration = data.get("eval_duration")
        if type(eval_count) == int and type(eval_duration) == int and eval_duration > 0:
            self.tokens_per_second = round(eval_count * 1e9 / eval_duration, 1)
        if type(prompt_eval) == int or type(eval_count) == int:
            self.usage = {"input_tokens": prompt_eval if type(prompt_eval) == int else None,
                          "output_tokens": eval_count if type(eval_count) == int else None,
                          "measured": True}
        return message["content"].strip() or "(Boş yanıt)"

    def _payload(self, messages, stream):
        from .config import PROFILES
        prof = PROFILES.get(self.profile, PROFILES["balanced"])
        formatted = []
        for m in messages:
            entry = {"role": m["role"], "content": m["content"]}
            if isinstance(m.get("images"), list) and m["images"]:
                entry["images"] = m["images"]
            formatted.append(entry)
        return {
            "model": self.settings.model,
            "messages": formatted,
            "stream": stream,
            "think": bool(prof["thinking"]),
            "keep_alive": 0 if self.settings.keep_alive == "0" else self.settings.keep_alive,
            "options": {
                "num_ctx": self.settings.context_tokens,
                "num_predict": self.settings.output_tokens,
                "temperature": prof["temperature"],
            },
        }

    def stream(self, messages, emit, job):
        import socket
        has_images = any(isinstance(m.get("images"), list) and m["images"] for m in messages)
        body = json.dumps(self._payload(messages, True), ensure_ascii=False).encode()
        limit = 6 * 1024 * 1024 if has_images else 65536
        if len(body) > limit:
            raise LocalModelError("Model isteği çok büyük.")
        conn = self._factory(OLLAMA_HOST, OLLAMA_PORT, timeout=self.settings.timeout_seconds)
        def interrupt():
            if sock:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        try:
            conn.connect()
            sock = conn.sock
            job.attach(interrupt)
            conn.request("POST", "/api/chat", body, {"Content-Type": "application/json"})
            with conn.getresponse() as response:
                if response.status != 200:
                    raise LocalModelError(f"Ollama HTTP {response.status} hatası verdi.")
                size = 0
                while True:
                    job.check()
                    line = response.readline(65537)
                    size += len(line)
                    if not line or len(line) > 65536 or size > self.MAX_RESPONSE_BYTES:
                        raise LocalModelError("Model akışı kesildi veya sınırı aştı.")
                    event = json.loads(line)
                    if not isinstance(event, dict) or "error" in event:
                        raise LocalModelError("Model akışı tamamlanamadı.")
                    message = event.get("message")
                    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
                        raise LocalModelError("Model yanıtı okunamadı.")
                    if message["content"]:
                        emit(message["content"])
                    if event.get("done") is True:
                        count, duration = event.get("eval_count"), event.get("eval_duration")
                        prompt_eval = event.get("prompt_eval_count")
                        if type(count) == int and type(duration) == int and duration > 0:
                            self.tokens_per_second = round(count * 1e9 / duration, 1)
                        if type(prompt_eval) == int or type(count) == int:
                            self.usage = {"input_tokens": prompt_eval if type(prompt_eval) == int else None,
                                          "output_tokens": count if type(count) == int else None,
                                          "measured": True}
                        return
        except (OSError, ValueError, http.client.HTTPException):
            job.check()
            raise LocalModelError("Yerel model bağlantısı kesildi.") from None
        finally:
            job.detach()
            conn.close()
