"""EON v0.8.0 — local desktop-style interface, or optional terminal mode."""
from __future__ import annotations

import argparse
import sys
import webbrowser


def run_cli(service: EonService) -> int:
    print("EON v0.8.0 — Yerel CLI · /yardim ile komutları gör")
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


def open_app_window(url: str, *, prefer_app_window: bool = True) -> bool:
    if prefer_app_window and sys.platform == "win32":
        import os
        import subprocess
        candidates = []
        for env_key in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
            base = os.environ.get(env_key)
            if base:
                candidates.append(os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"))
                candidates.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))
        try:
            import winreg
            for sub in (r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
                        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"):
                for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                    try:
                        with winreg.OpenKey(root, sub) as k:
                            val, _ = winreg.QueryValueEx(k, "")
                            if isinstance(val, str) and val.strip():
                                candidates.append(val.strip().strip('"'))
                    except OSError:
                        pass
        except ImportError:
            pass
        profile_dir = os.path.join(
            os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
            "EON",
            "AppWindow",
        )
        try:
            os.makedirs(profile_dir, exist_ok=True)
        except OSError:
            profile_dir = ""
        for exe in candidates:
            if os.path.isfile(exe):
                cmd = [
                    exe,
                    f"--app={url}",
                    "--new-window",
                    "--window-size=1340,860",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-features=Translate,EdgeSidebar",
                ]
                if profile_dir:
                    cmd.append(f"--user-data-dir={profile_dir}")
                try:
                    subprocess.Popen(cmd, shell=False, close_fds=True)
                    return True
                except OSError:
                    pass
    return bool(webbrowser.open(url))


def start_tray_controller(url: str, service: EonService, server) -> object | None:
    if sys.platform != "win32":
        return None
    import os
    import subprocess
    exe = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
    if not os.path.isfile(exe):
        return None
    script = (
        "Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
        "$n=New-Object System.Windows.Forms.NotifyIcon;"
        "$n.Icon=[System.Drawing.SystemIcons]::Application;"
        "$n.Text='EON v0.8.0 — Kisisel AI Calisma Ortami';"
        "$n.Visible=$true;"
        "$m=New-Object System.Windows.Forms.ContextMenuStrip;"
        "$open=$m.Items.Add('EON Calisma Ortamini Ac');"
        "$open.Add_Click({[Console]::Out.WriteLine('OPEN');[Console]::Out.Flush()});"
        "$unload=$m.Items.Add('Ollama Modelini Bellekten Bosalt');"
        "$unload.Add_Click({[Console]::Out.WriteLine('UNLOAD');[Console]::Out.Flush()});"
        "$m.Items.Add('-')|Out-Null;"
        "$exit=$m.Items.Add('EON Sunucusunu Kapat');"
        "$exit.Add_Click({$n.Visible=$false;[Console]::Out.WriteLine('EXIT');[Console]::Out.Flush();[System.Windows.Forms.Application]::Exit()});"
        "$n.ContextMenuStrip=$m;"
        "$n.Add_DoubleClick({[Console]::Out.WriteLine('OPEN');[Console]::Out.Flush()});"
        "[System.Windows.Forms.Application]::Run()"
    )
    try:
        import threading
        proc = subprocess.Popen(
            [exe, "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        def _listen():
            if not proc.stdout:
                return
            for line in proc.stdout:
                cmd = line.strip()
                if cmd == "OPEN":
                    open_app_window(url, prefer_app_window=True)
                elif cmd == "UNLOAD":
                    try:
                        service.runtime_action("unload")
                    except Exception:
                        pass
                elif cmd == "EXIT":
                    try:
                        server.shutdown()
                    except Exception:
                        pass
                    break
        threading.Thread(target=_listen, daemon=True).start()
        return proc
    except OSError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="EON — Ollama ve isteğe bağlı Gemini asistanı")
    parser.add_argument("--cli", action="store_true", help="Tarayıcı arayüzü yerine terminal")
    parser.add_argument("--no-browser", action="store_true", help="Tarayıcıyı açma")
    parser.add_argument("--tab", action="store_true", help="Uygulama penceresi yerine normal tarayıcı sekmesinde aç")
    parser.add_argument("--tray", action="store_true", help="Windows sistem tepsisi (System Tray) ikonuyla çalıştır")
    parser.add_argument("--silent", action="store_true", help="Konsol kullanmadan aç; başlangıç hataları bildirilir")
    parser.add_argument("--model", default="qwen3:4b-instruct", help="Kurulu yerel model adı")
    args = parser.parse_args()
    if args.tray:
        args.silent = True
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
    tray_proc = None
    try:
        from eon.launcher import storage_path
        service = EonService(model=args.model, vault_path=storage_path().with_name("library.dpapi"))
        if args.cli:
            return run_cli(service)
        from eon.server import start_server
        server = start_server(service=service)
        url = server.origin + "#boot=" + server.boot_code
        if args.tray:
            tray_proc = start_tray_controller(url, service, server)
        if not args.silent:
            print("EON v0.8.0 hazır. Yerel adres:", server.origin)
            print("Oturum anahtarı bağlantı parçasında saklanır ve konsola yazdırılmaz.")
            print("Kapatmak için Ctrl+C. Ollama yalnız yerel model seçilince kullanılır.")
        if not args.no_browser and not open_app_window(url, prefer_app_window=not args.tab) and args.silent:
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
        if tray_proc is not None:
            try:
                tray_proc.terminate()
            except Exception:
                pass
        if server is not None:
            server.server_close()
        release_instance()


if __name__ == "__main__":
    raise SystemExit(main())
