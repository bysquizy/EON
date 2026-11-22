# EON

**Bilgisayarında çalışan, kontrolü sana bırakan yerel AI asistanı.**

EON, sade bir sohbet deneyimini küçük ama faydalı masaüstü araçlarıyla birleştirmek için geliştiriliyor. Modeller kendi bilgisayarında çalışıyor. Harici AI API'si veya ek model aboneliği gerekmiyor.

> **v0.0.3 · Ön sürüm.** Gerçek kullanım testleri devam ediyor. Henüz tam özellikli bir Windows uygulaması değil; Python ile çalışan yerel bir tarayıcı arayüzü.

## Şu anda neler var?

- **Sohbet:** Ollama'da kurulu yerel modellerle Türkçe veya İngilizce konuşma.
- **Ayrı sohbetler:** Yeni sohbet oluşturma, geçmiş listesinden açma ve silme.
- **Sohbet araçları:** Yanıtı yenileme, özetleme, model seçme, kısa/normal/detaylı yanıt, istatistik ve basit hesaplama.
- **Uygulamalar:** Windows Başlat menüsü, kayıtlı uygulamalar, Masaüstü ve OneDrive Masaüstü kısayollarından program bulmayı deneme; seçtiğin uygulamayı tek tıklamayla açma.
- **Bağlantı kontrolü:** EON'un yerel sunucusu kapanırsa anlaşılır hata ve yeniden bağlanma seçeneği.

Sohbetlerin **şimdilik yalnızca uygulama açıkken** tutulur. EON kapandığında geçmiş silinir; kalıcı şifreli kayıt henüz hazır değil. Uygulama başlatıcı yolları ise yalnız yerel ayar dosyasında saklanır.

## Kurulum

Windows'ta [Python 3.10+](https://www.python.org/downloads/windows/) ve [Ollama](https://ollama.com/download/windows) kurulu olmalı.

1. Ollama'yı bulut özellikleri kapalı ve yalnız `127.0.0.1:11434` adresini dinleyecek biçimde ayarla.
2. Modeli bir kez indir:

   ```powershell
   ollama pull qwen3:4b-instruct
   ```

3. **[Releases](https://github.com/bysquizy/EON/releases)** bölümünden son sürümün ZIP arşivini indir, çıkar ve `baslat.bat` dosyasını aç.
4. EON tarayıcıda açılır. **Terminal penceresini açık tut.** Kapatmak için `Ctrl+C` kullan.

Kurulum ve **“Failed to fetch”** sorun giderme adımları: [Windows rehberi](docs/SETUP_WINDOWS.md).

## Sırada ne var?

Kalıcı şifreli sohbet geçmişi, daha gelişmiş izinler, çevrimdışı sesli iletişim ve gerçek masaüstü uygulaması deneyimi. Yeni özellikler yalnızca test edildikçe yayınlanacak.

**Önce güvenlik, sonra yetenek.** Model, kendiliğinden komut çalıştırmaz. Uygulamalar yalnızca arayüzdeki **Aç** düğmesine basılınca başlatılır.

---

[**Sürümler**](https://github.com/bysquizy/EON/releases) · [**Yol haritası**](docs/ROADMAP.md) · [**Güvenlik**](SECURITY.md) · [**Gizlilik**](docs/PRIVACY.md) · [**Değişiklikler**](CHANGELOG.md)

<sub>Erken geliştirme sürümü. Açık kaynak lisansı henüz belirlenmedi.</sub>
