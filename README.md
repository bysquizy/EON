# EON v0.6.1

EON, Windows üzerinde çalışan hızlı, gizlilik odaklı kişisel yapay zekâ çalışma ortamıdır. **Google Gemini API anahtarınla Ollama kurmadan hemen başlayabilir** veya bilgisayarının donanımına göre önerilen **yerel Ollama** modellerini isteğe bağlı olarak kurup kullanabilirsin.

## Başlangıç (Python Kurulumu Zorunlu Değildir)

1. Proje ZIP'ini bir klasöre çıkar ve `baslat.bat` dosyasına çift tıkla. (Bilgisayarında Python kurulu değilse `baslat.bat` resmi taşınabilir Python çalışma ortamını `.python\` klasörüne otomatik indirip hazırlar.)
2. **Hızlı Başlangıç (Önerilen):** Ayarlar ekranından Google AI Studio (Gemini) API anahtarını girip kaydet; anahtarın Windows DPAPI ile şifrelenir ve yeni sohbetlerin doğrudan Gemini ile açılır.
3. **İsteğe Bağlı Yerel Model:** Yerel model kullanmak istersen Ollama kurup Ayarlar ekranında bilgisayarının RAM miktarına göre önerilen modeli (örn. `ollama pull qwen3:4b`) indirebilirsin.

[Windows kurulumu](docs/SETUP_WINDOWS.md) · [Mimari](docs/ARCHITECTURE.md) · [Gizlilik](docs/PRIVACY.md) · [Güvenlik](SECURITY.md) · [Sürüm notları](docs/releases/v0.6.1.md)
