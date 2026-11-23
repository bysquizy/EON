# EON

EON, Windows’ta tarayıcıdan kullanılan bir sohbet asistanıdır. Varsayılan sağlayıcı bilgisayarındaki Ollama’dır. İstersen Google AI Studio anahtarınla ayrı bir Gemini sohbeti açabilirsin.

v0.4.1, Gemini bağlamını ve yarım yanıt davranışını iyileştirir; Windows başlatıcısına tek örnek ve sessiz başlatma desteği ekler.

## Başlangıç

1. Python 3.10+ kur. Yerel model kullanacaksan Ollama kurup `ollama pull qwen3:4b-instruct` çalıştır; Gemini için Ollama gerekmez.
2. Sürüm ZIP’ini çıkar ve `baslat.bat` dosyasını aç. Terminali açık tut.
3. Yeni sohbet başlat veya **Ctrl+K** ile sohbet, proje, model ve uygulama ara. Geniş ekranda **Ctrl+B** sohbet listesini daraltır.

Projeler, seçici hafıza, favoriler ve sohbet geçmişi Windows hesabına bağlı olarak şifrelenir. Yanıtları akış halinde okuyabilir ve durdurabilirsin. Ayarlar’dan yerel modelin bellekte kalma süresini seçebilir, yüklü modelleri görebilir ve boşta olan seçili modeli boşaltabilirsin.

Gemini için Ayarlar’da anahtarı Windows penceresine gir, Google bağlantısını test et, model seç ve gönderim kapsamını onayla. Hava durumu ayrı bir izindir.

[Windows kurulumu](docs/SETUP_WINDOWS.md) · [Gizlilik](docs/PRIVACY.md) · [Sürüm notları](docs/releases/v0.4.1.md)
