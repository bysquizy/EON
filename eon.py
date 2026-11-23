"""EON v0.5.0 — local desktop-style interface, or optional terminal mode."""
from __future__ import annotations

import argparse
import sys
import webbrowser


def run_cli(service: EonService) -> int:
    print("EON v0.5.0 — Yerel CLI · /yardim ile komutları gör")
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
    parser = argparse.ArgumentParser(description="EON — Ollama ve isteğe bağlı Gemini asistanı")
    parser.add_argument("--cli", action="store_true", help="Tarayıcı arayüzü yerine terminal")
    parser.add_argument("--no-browser", action="store_true", help="Tarayıcıyı açma")
    parser.add_argument("--silent", action="store_true", help="Konsol kullanmadan aç; başlangıç hataları bildirilir")
    parser.add_argument("--model", default="qwen3:4b-instruct", help="Kurulu yerel model adı")
    args = parser.parse_args()
    if args.silent and args.cli:
        message = "Sessiz başlatma yalnızca tarayıcı arayüzüyle kullanılabilir."
        if sys.platform == "win32":
            import ctypes
            ctypes.WinDLL("user32").MessageBoxW(None, message, "EON başlatılamadı", 0x10)
        else:
            print(message)
        return 2
    if sys.version_info < (3, 10):
        message = "EON için Python 3.10 veya üzeri gerekli."
        if args.silent and sys.platform == "win32":
            import ctypes
            ctypes.WinDLL("user32").MessageBoxW(None, message, "EON başlatılamadı", 0x10)
        else:
            print(message)
        return 2
    from eon.instance import acquire_instance, focus_existing_window, release_instance
    from eon.service import EonService
    try:
        if not acquire_instance():
            focus_existing_window()
            return 0
    except (OSError, AttributeError) as exc:
        message = "EON tek örnek korumasını başlatamadı: " + str(exc)
        if args.silent and sys.platform == "win32":
            import ctypes
            ctypes.WinDLL("user32").MessageBoxW(None, message, "EON başlatılamadı", 0x10)
        else:
            print(message)
        return 1
    server = None
    try:
        from eon.launcher import storage_path
        service = EonService(model=args.model, vault_path=storage_path().with_name("library.dpapi"))
        if args.cli:
            return run_cli(service)
        from eon.server import start_server
        server = start_server(service=service)
        url = server.origin + "#access=" + server.access
        if not args.silent:
            print("EON v0.5.0 hazır. Yerel adres:", server.origin)
            print("Oturum anahtarı bağlantı parçasında saklanır ve konsola yazdırılmaz.")
            print("Kapatmak için Ctrl+C. Ollama yalnız yerel model seçilince kullanılır.")
        if not args.no_browser and not webbrowser.open(url) and args.silent:
            raise RuntimeError("Varsayılan tarayıcı açılamadı.")
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass
        return 0
    except Exception as exc:
        message = "EON başlatılamadı: " + str(exc)
        if args.silent and sys.platform == "win32":
            import ctypes
            ctypes.WinDLL("user32").MessageBoxW(None, message, "EON başlatılamadı", 0x10)
        else:
            print(message)
        return 1
    finally:
        if server is not None:
            server.server_close()
        release_instance()


if __name__ == "__main__":
    raise SystemExit(main())
