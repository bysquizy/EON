# EON

**Windows için gizlilik odaklı, yerel öncelikli yapay zekâ çalışma alanı.**

EON’u Google Gemini ile hızlıca kullanabilir veya Ollama üzerinden yerel modellerle çalıştırabilirsin. Gemini için Ollama kurulumu gerekmez.

[![CI](https://github.com/bysquizy/EON/actions/workflows/ci-release.yml/badge.svg?branch=main)](https://github.com/bysquizy/EON/actions/workflows/ci-release.yml)
![Sürüm](https://img.shields.io/badge/sürüm-v0.6.2-7967e8)

## Öne çıkanlar

- **Gemini ve Ollama:** Bulut veya yerel sağlayıcı seçimi.
- **Canlı sesli konuşma:** Altyazı, ses karakteri seçimi ve konuşmayı kesip araya girme.
- **Sohbet ve çalışma alanı:** Şifreli yerel saklama, projeler ve dosyalarla çalışma.
- **Windows araçları:** Masaüstü penceresi, ses kontrolleri ve donanıma göre model önerileri.

## Hızlı başlangıç

1. [EON v0.6.2 ZIP’ini indir](https://github.com/bysquizy/EON/releases/tag/v0.6.2) ve bir klasöre çıkar.
2. `baslat.bat` dosyasını çalıştır. Python yüklü değilse başlatıcı resmi taşınabilir Python dağıtımını hazırlar.
3. Ayarlardan Gemini API anahtarını ekle veya Ollama’yı kurup yerel modelini seç.

## Gizlilik

EON yerel HTTP sunucusu kullanır; sohbet kasası ve API anahtarı Windows DPAPI ile şifrelenir. Gemini’yi seçtiğinde isteklerin yanıt üretmek için Google’a gönderilir. Ollama ile yerel model seçildiğinde inference bilgisayarında çalışır. Dışa aktarılan dosyalar şifrelenmiş olmayabilir.

## Belgeler

[Windows kurulumu](docs/SETUP_WINDOWS.md) · [Mimari](docs/ARCHITECTURE.md) · [Gizlilik](docs/PRIVACY.md) · [Güvenlik](SECURITY.md) · [v0.6.2 sürüm notları](docs/releases/v0.6.2.md)

## Destek

Bir sorun bildirmeden önce [mevcut Issues’ları](https://github.com/bysquizy/EON/issues) kontrol et. Güvenlik açıklarını herkese açık issue yerine [güvenlik yönergelerine](SECURITY.md) göre bildir.

