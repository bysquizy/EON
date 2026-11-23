"""Only local inference; no remote model endpoints or cloud tags."""
from dataclasses import dataclass
import re

OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
DEFAULT_MODEL = "qwen3:4b-instruct"
MODEL_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._/-]{0,119}(?::[A-Za-z0-9._-]{1,80})?$")
OUTPUT_LIMITS = {"kisa": 128, "normal": 320, "detayli": 720}
PROFILES = {
    "fast": {"name": "Hızlı", "temperature": 0.35, "thinking": False},
    "balanced": {"name": "Dengeli", "temperature": 0.55, "thinking": False},
    "deep": {"name": "Derin Düşünme", "temperature": 0.65, "thinking": True},
}
STYLE_GUIDANCE = {
    "kisa": "Çok kısa yanıtla. Gereksiz açıklama yapma.",
    "normal": "Açık ve doğal biçimde, gerektiği kadar ayrıntı ver.",
    "detayli": "Gerekli ayrıntıları anlaşılır biçimde açıkla; düzenli örnekler kullan.",
}
SYSTEM_PROMPT = (
    "Sen EON, yerel bir asistansın. Kullanıcının dilinde yanıtla. "
    "Önce sonucu ver, tekrardan kaçın. Eksik bilgi için sor; belirsizliği belirt. "
    "Kaynak, ölçüm veya araç sonucu uydurma. Yalnız metin üretirsin. "
    "Bir dosyayı okuduğunu veya program çalıştırdığını iddia etme."
)
GEMINI_SYSTEM_PROMPT = (
    "Sen EON'sun: kullanıcının kişisel yapay zekâ asistanısın. Düşünmesine, öğrenmesine, araştırmasına, "
    "üretmesine ve planlamasına yardım et. Doğal, güvenilir ve gerektiğinde ayrıntılı yanıt ver; "
    "gereksiz konuşma, bilgi uydurma veya erişmediğin araçları kullanmış gibi davranma. Kullanıcı Türkçe "
    "konuşuyorsa doğal Türkçe, İngilizce istiyorsa İngilizce kullan. Basit soruları kısa, zor soruları "
    "açıklamalı yanıtla. Bilmediğin güncel bilgiyi tahmin etme. Kendini yalnızca EON olarak tanıt."
)


def valid_model(name: object) -> bool:
    """Accept installed local model names, excluding any obvious remote/cloud tag."""
    return (
        isinstance(name, str)
        and MODEL_NAME.fullmatch(name) is not None
        and "cloud" not in name.casefold().split(":")[-1]
        and not name.startswith("/")
        and ".." not in name.split("/")
    )


@dataclass(frozen=True)
class LocalSettings:
    model: str = DEFAULT_MODEL
    context_tokens: int = 4096
    output_tokens: int = 320
    timeout_seconds: int = 180
    keep_alive: str = "3m"

    def __post_init__(self) -> None:
        if self.keep_alive not in ("0", "1m", "3m", "5m", "15m"):
            raise ValueError("Geçersiz bekletme süresi.")
        if not valid_model(self.model):
            raise ValueError("Geçersiz veya bulut modeli.")
        if not 512 <= self.context_tokens <= 8192:
            raise ValueError("Geçersiz bağlam boyutu.")
        if not 1 <= self.output_tokens <= 1024:
            raise ValueError("Geçersiz yanıt boyutu.")
