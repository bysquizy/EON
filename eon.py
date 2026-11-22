"""EON v0.0.2 — local desktop-style interface, or optional terminal mode."""
import argparse
import webbrowser

from eon.config import DEFAULT_MODEL
from eon.service import EonService
from eon.server import start_server


def run_cli(service: EonService) -> int:
    print("EON v0.0.2 — Yerel CLI · /yardim ile komutları gör")
    while True:
        try:
            text = input("Sen > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGörüşürüz.")
            return 0
        if not text:
            continue
        if text.lower() in ("/cikis", "/çıkış"):
            return 0
        try:
            print("EON >", service.send(text)["message"], "\n")
        except ValueError as exc:
            print("EON >", exc)
        except Exception:
            print("EON > Ollama'ya bağlanılamadı; yerel modeli kontrol et.")


def main() -> int:
    parser = argparse.ArgumentParser(description="EON — tamamen yerel AI asistanı")
    parser.add_argument("--cli", action="store_true", help="Tarayıcı arayüzü yerine terminal")
    parser.add_argument("--no-browser", action="store_true", help="Tarayıcıyı açma")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Kurulu yerel model adı")
    args = parser.parse_args()
    service = EonService(model=args.model)
    if args.cli:
        return run_cli(service)
    server = start_server(service=service)
    url = server.origin
    print("EON v0.0.2 hazır. Yerel adres:", url)
    print("Kapatmak için Ctrl+C. Dosyalar ve program yolları GitHub'a gönderilmez.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
