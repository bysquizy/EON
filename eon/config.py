"""Dış servis kullanılmasını önleyen sabitler."""
from dataclasses import dataclass

OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434

# Yalnızca önceden seçilmiş yerel modeller. :cloud modelleri kabul edilmez.
ALLOWED_MODELS = frozenset({"qwen3:4b-instruct", "qwen3:1.7b"})

SYSTEM_PROMPT = (
    "Sen EON adlı kişisel, tamamen yerel çalışan bir AI asistansın. "
    "Türkçe yanıt ver; kullanıcı İngilizce isterse İngilizce kullan. "
    "Sakin, zeki, profesyonel ve samimi ol. Kısa soruya kısa cevap ver. "
    "Dış internete erişimin, dosyaları okuma ve Windows komutu çalıştırma "
    "yetkin yok. Bu işleri yaptığını asla iddia etme. "
    "Bilmediğin şeyleri uydurma. Özel verileri paylaşma."
)

@dataclass(frozen=True)
class LocalSettings:
    model: str = "qwen3:4b-instruct"
    context_tokens: int = 4096
    output_tokens: int = 256
    timeout_seconds: int = 180

    def __post_init__(self) -> None:
        if self.model not in ALLOWED_MODELS:
            raise ValueError("EON yalnızca izin verilen yerel modelleri kullanabilir.")
        if not 512 <= self.context_tokens <= 8192:
            raise ValueError("Geçersiz bağlam büyüklüğü.")
        if not 1 <= self.output_tokens <= 1024:
            raise ValueError("Geçersiz yanıt sınırı.")
