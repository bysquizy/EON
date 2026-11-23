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
    def __init__(self, key, model="", output=320, factory=http.client.HTTPSConnection):
        if not key:
            raise LocalModelError("Önce Gemini anahtarını ekle.")
        self.key, self.model, self.output, self.factory = key, model, output, factory

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
        payload = {"systemInstruction":{"parts":[{"text":messages[0]["content"]}]},
                   "contents":[{"role":"model" if m["role"]=="assistant" else "user",
                                "parts":[{"text":m["content"]}]} for m in messages[1:]],
                   "generationConfig":{"maxOutputTokens":self.output}}
        def read(reply):
            total = 0
            finished = False
            while True:
                job.check()
                line = reply.readline(131073)
                if not line:
                    break
                total += len(line)
                if len(line)>131072 or total>2*1024*1024:
                    raise LocalModelError("Gemini yanıt sınırını aştı.")
                if not line.startswith(b"data:"):
                    continue
                data = json.loads(line[5:])
                if "error" in data:
                    raise LocalModelError("Gemini üretimi kesildi.")
                for candidate in data.get("candidates", []):
                    for part in candidate.get("content", {}).get("parts", []):
                        if part.get("text") and not part.get("thought"):
                            emit(part["text"])
                    if candidate.get("finishReason") in ("STOP", "MAX_TOKENS"):
                        finished = True
            if not finished:
                raise LocalModelError("Gemini tamamlanmış bir yanıt vermedi.")
        self._request("POST", "/v1beta/"+self.model+":streamGenerateContent?alt=sse",
                      read, json.dumps(payload).encode(), job)
