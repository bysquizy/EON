"""EON Local v0.0.1 — ilk yazılı ve tamamen yerel prototip."""
import argparse
from eon.config import ALLOWED_MODELS, LocalSettings
from eon.provider import LocalModelError, LocalOllama
from eon.session import VolatileSession
from eon.tools import ToolError, calculate

def main():
    parser = argparse.ArgumentParser(description="EON Local (bulut bağlantısı yok)")
    parser.add_argument(
        "--model", choices=sorted(ALLOWED_MODELS),
        default="qwen3:4b-instruct",
    )
    args = parser.parse_args()
    settings = LocalSettings(model=args.model)
    ollama = LocalOllama(settings)
    session = VolatileSession()
    print("\nEON Local v0.0.1 — tamamen yerel sohbet")
    print(f"Model: {settings.model} | Hafıza: sadece RAM | Bulut modeli: kapalı")
    print("Komutlar: /yardim, /durum, /hesap 2*(3+5), /temizle, /cikis")
    print("Uyarı: Bu prototip dosya veya terminal kontrolü yapmaz.\n")

    try:
        models = ollama.installed_models()
    except LocalModelError as exc:
        print(f"Bağlantı sorunu: {exc}")
        print("Önce resmi Ollama'yı kurup arka planda çalıştır.")
        return 1

    if settings.model not in models:
        print(f"Model yerelde yüklü değil: {settings.model}")
        print(f"Yalnızca ilk kurulumda, onaylayarak indir: ollama pull {settings.model}")
        return 1

    while True:
        try:
            user_text = input("Sen > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nEON > Görüşürüz.")
            return 0
        if not user_text:
            continue
        if user_text in ("/cikis", "/çıkış"):
            print("EON > Görüşürüz.")
            return 0
        if user_text == "/yardim":
            print("EON > /durum /hesap <ifade> /temizle /cikis")
            continue
        if user_text == "/durum":
            print(f"EON > Model {settings.model}; internet servisi: yok; kayıt: yok.")
            continue
        if user_text == "/temizle":
            session.clear()
            print("EON > Bu oturumun konuşma belleği temizlendi.")
            continue
        if user_text.startswith("/hesap "):
            try:
                print("EON >", calculate(user_text[7:].strip()))
            except ToolError as exc:
                print("EON >", exc)
            continue
        if user_text.startswith("/"):
            print("EON > Tanınmayan komut. /yardim yaz.")
            continue
        try:
            messages = session.messages_for(user_text)
            answer = ollama.chat(messages)
            print("EON >", answer, "\n")
            session.remember_turn(user_text, answer)
        except (LocalModelError, ValueError) as exc:
            print("EON >", exc, "\n")

if __name__ == "__main__":
    raise SystemExit(main())
