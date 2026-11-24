# EON v0.8.0

EON, Windows üzerinde çalışan hızlı, gizlilik odaklı kişisel yapay zekâ masaüstü uygulamasıdır. **Google Gemini API anahtarınla Ollama kurmadan hemen başlayabilir** veya bilgisayarının donanımına göre önerilen **yerel Ollama** modellerini isteğe bağlı olarak kurup kullanabilirsin.

## Başlangıç (Python Kurulumu Zorunlu Değildir)

1. Proje ZIP'ini bir klasöre çıkar ve `baslat.bat` dosyasına çift tıkla (sistemde Python varsa doğrudan `EON.pyw` üzerinden de pencere modunda açılır).
   - Bilgisayarında Python kurulu değilse `baslat.bat`, resmi **Python Software Foundation dijital imzalı** taşınabilir Python çalışma ortamını `.python\` klasörüne otomatik indirip imzasını doğrular.
   - **Windows Akıllı Uygulama Denetimi (Smart App Control) Notu:** İnternetten indirilen ZIP dosyaları Windows'ta "İnternetten geldi" (Mark-of-the-Web) etiketi taşır. ZIP'i ayıklamadan önce sağ tık → **Özellikler → Engellemeyi Kaldır** seçeneğini işaretlemek veya `baslat.bat` içindeki otomatik `Unblock-File` adımının çalışmasına izin vermek uyarıları önler.
2. **Hızlı Başlangıç (Önerilen):** Ayarlar ekranından Google AI Studio (Gemini) API anahtarını girip kaydet; anahtarın Windows DPAPI ile şifrelenir ve sohbetlerin doğrudan Gemini (`gemini-3.8-flash` / `gemini-4.0-helium`) + **Gemini Stüdyo HD Ses (`gemini-3.8-flash-tts`)** ile açılır.
3. **İsteğe Bağlı Yerel Model:** Yerel model kullanmak istersen Ollama kurup Ayarlar ekranında bilgisayarının RAM miktarına göre önerilen modeli (örn. `ollama pull qwen3:4b`) indirebilirsin.

[Windows kurulumu](docs/SETUP_WINDOWS.md) · [Mimari](docs/ARCHITECTURE.md) · [Gizlilik](docs/PRIVACY.md) · [Güvenlik](SECURITY.md) · [Sürüm notları](docs/releases/v0.8.0.md)
