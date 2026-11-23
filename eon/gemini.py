"""Fixed-host Gemini REST client. Never forwards provider error bodies."""
import http.client
import json
import re
import socket
import ssl
from urllib.parse import urlencode
from .provider import LocalModelError

MODEL = re.compile(r"models/gemini-[a-zA-Z0-9._-]{1,100}")
ERRORS = {400:"İstek veya anahtar geçersiz.",401:"API anahtarını kontrol et.",
          403:"Anahtar izinlerini, proje kısıtlarını ve bölge erişimini kontrol et.",
          404:"Model artık erişilebilir olmayabilir. Model listesini yenile.",429:"Kota veya hız sınırına ulaşıldı."}


class Gemini:
    def __init__(self, key, model="", output=320, factory=http.client.HTTPSConnection,
                 profile="balanced", search=False):
        if not key:
            raise LocalModelError("Önce Gemini anahtarını ekle.")
        self.key, self.model, self.output, self.factory = key, model, output, factory
        self.profile = profile if profile in ("fast", "balanced", "deep") else "balanced"
        self.search = bool(search)
        self.usage = None
        self.sources = []
        self.tokens_per_second = None
        self.raw_parts = []

    @staticmethod
    def capabilities(model_name=""):
        low = (model_name or "").casefold()
        is_thinking = any(k in low for k in ("2.5", "3.", "3-", "4", "thinking", "pro", "flash"))
        return {
            "provider": "gemini",
            "streaming": True,
            "vision": True,
            "thinking": is_thinking,
            "embeddings": False,
            "web_search": True,
            "context_window": 1048576,
        }

    def _request(self, method, path, consume, body=None, job=None):
        conn = self.factory("generativelanguage.googleapis.com", timeout=45)
        try:
            conn.connect()
            sock = conn.sock
            if job:
                def cancel():
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                job.attach(cancel)
            conn.request(method, path, body, {"x-goog-api-key": self.key, "Content-Type":"application/json"})
            with conn.getresponse() as reply:
                if reply.status != 200:
                    raise LocalModelError("Gemini: " + ERRORS.get(reply.status, "Google servis hatası." if reply.status >= 500 else "Servis isteği tamamlanamadı."))
                return consume(reply)
        except socket.gaierror:
            raise LocalModelError("Gemini DNS adresi çözülemedi.") from None
        except ssl.SSLError:
            raise LocalModelError("Gemini TLS bağlantısı doğrulanamadı.") from None
        except TimeoutError:
            if job:
                job.check()
            raise LocalModelError("Gemini bağlantısı zaman aşımına uğradı.") from None
        except (OSError, ValueError, TypeError, KeyError, AttributeError, http.client.HTTPException):
            if job:
                job.check()
            raise LocalModelError("Gemini bağlantısı kesildi veya yanıt okunamadı.") from None
        finally:
            if job:
                job.detach()
            conn.close()

    def models(self):
        results, token = [], ""
        for _ in range(10):
            query = {"pageSize":100}
            if token:
                query["pageToken"] = token
            page = self._request("GET", "/v1beta/models?" + urlencode(query),
                                 lambda reply: json.loads(reply.read(1024*1024)))
            if not isinstance(page, dict) or not isinstance(page.get("models", []), list):
                raise LocalModelError("Gemini model listesi okunamadı.")
            for model in page.get("models", []):
                if not isinstance(model, dict):
                    continue
                name = model.get("name", "")
                if isinstance(name, str) and MODEL.fullmatch(name) and "generateContent" in model.get("supportedGenerationMethods", []):
                    results.append(name)
            token = page.get("nextPageToken")
            if not token:
                break
        if not results:
            raise LocalModelError("Bu anahtar için metin üreten Gemini modeli bulunamadı.")
        return sorted(set(results))

    def stream(self, messages, emit, job):
        if not MODEL.fullmatch(self.model):
            raise LocalModelError("Gemini modeli geçersiz.")
        contents = []
        for m in messages[1:]:
            role = "model" if m["role"] == "assistant" else "user"
            if isinstance(m.get("gemini_parts"), list) and m["gemini_parts"]:
                parts = list(m["gemini_parts"])
            else:
                parts = [{"text": m["content"]}]
                for img in m.get("inline_images", []) or ():
                    if isinstance(img, dict) and img.get("mime") and img.get("data"):
                        parts.append({"inlineData": {"mimeType": img["mime"], "data": img["data"]}})
            contents.append({"role": role, "parts": parts})
        gen_cfg = {"maxOutputTokens": self.output}
        low_model = self.model.casefold()
        if self.profile == "fast":
            gen_cfg["temperature"] = 0.35
            if "2.5-flash" in low_model:
                gen_cfg["thinkingConfig"] = {"thinkingBudget": 0}
        elif self.profile == "deep":
            gen_cfg["temperature"] = 0.65
            if "2.5" in low_model:
                gen_cfg["thinkingConfig"] = {"thinkingBudget": min(2048, max(512, self.output // 2))}
        payload = {"systemInstruction": {"parts": [{"text": messages[0]["content"]}]},
                   "contents": contents,
                   "generationConfig": gen_cfg}
        if self.search:
            payload["tools"] = [{"googleSearch": {}}]
        self.sources = []
        self.usage = None
        self.raw_parts = []
        seen_urls = set()

        def read(reply):
            total = 0
            finished = False
            while True:
                job.check()
                line = reply.readline(131073)
                if not line:
                    break
                total += len(line)
                if len(line) > 131072 or total > 4 * 1024 * 1024:
                    raise LocalModelError("Gemini yanıt sınırını aştı.")
                if not line.startswith(b"data:"):
                    continue
                data = json.loads(line[5:])
                if "error" in data:
                    raise LocalModelError("Gemini üretimi kesildi.")
                usage_meta = data.get("usageMetadata")
                if isinstance(usage_meta, dict):
                    prompt_tok = usage_meta.get("promptTokenCount")
                    cand_tok = usage_meta.get("candidatesTokenCount")
                    thought_tok = usage_meta.get("thoughtsTokenCount")
                    total_tok = usage_meta.get("totalTokenCount")
                    self.usage = {
                        "input_tokens": prompt_tok if type(prompt_tok) is int else None,
                        "output_tokens": cand_tok if type(cand_tok) is int else None,
                        "thought_tokens": thought_tok if type(thought_tok) is int else None,
                        "total_tokens": total_tok if type(total_tok) is int else None,
                        "measured": True,
                    }
                for candidate in data.get("candidates", []):
                    for part in candidate.get("content", {}).get("parts", []):
                        if isinstance(part, dict):
                            if part.get("thoughtSignature") or part.get("thought") or part.get("text"):
                                clean_part = {}
                                if isinstance(part.get("text"), str):
                                    clean_part["text"] = part["text"]
                                if part.get("thought") is True:
                                    clean_part["thought"] = True
                                if isinstance(part.get("thoughtSignature"), str):
                                    clean_part["thoughtSignature"] = part["thoughtSignature"]
                                if clean_part:
                                    self.raw_parts.append(clean_part)
                            if part.get("text") and not part.get("thought"):
                                emit(part["text"])
                    gm = candidate.get("groundingMetadata")
                    if isinstance(gm, dict):
                        queries = [q for q in gm.get("webSearchQueries", []) if isinstance(q, str)]
                        for chunk in gm.get("groundingChunks", []) or ():
                            if not isinstance(chunk, dict):
                                continue
                            web = chunk.get("web")
                            if isinstance(web, dict):
                                uri = web.get("uri", "")
                                title = web.get("title", "") or uri
                                if isinstance(uri, str) and uri.startswith(("https://", "http://")) and uri not in seen_urls:
                                    seen_urls.add(uri)
                                    self.sources.append({
                                        "kind": "web",
                                        "title": str(title)[:200],
                                        "uri": uri[:1024],
                                        "queries": queries[:5],
                                    })
                    reason = candidate.get("finishReason")
                    if reason == "MAX_TOKENS":
                        raise LocalModelError("Gemini yanıt sınırına ulaştı; yanıt tamamlanmadı. Daha kısa bir istem veya kısa yanıt modu dene.")
                    if reason in ("SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"):
                        raise LocalModelError("Gemini güvenlik veya içerik politikası nedeniyle yanıtı durdurdu.")
                    if reason == "STOP":
                        finished = True
            if not finished:
                raise LocalModelError("Gemini tamamlanmış bir yanıt vermedi.")
        self._request("POST", "/v1beta/"+self.model+":streamGenerateContent?alt=sse",
                      read, json.dumps(payload).encode(), job)
