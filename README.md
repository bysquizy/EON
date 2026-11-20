# EON

**Kendi bilgisayarında çalışan, kontrolü kullanıcıya bırakan bir AI asistanı.**

EON, Windows için geliştirilen yerel bir yapay zekâ asistanı projesi. Amaç; doğal bir sohbet deneyimini zamanla hafıza, görevler ve bilgisayar üzerinde yapılabilecek işlemlerle bir araya getirmek. Bunu yaparken gizlilikten ve kullanıcı kontrolünden ödün vermemek.

Proje henüz yolun başında. Şimdilik küçük ama çalışır bir temel oluşturuluyor; yeni özellikler adım adım eklenecek.

## Şu anda neler yapabiliyor?

**v0.0.1**, EON'un ilk prototipi.

- Ollama ile bilgisayarda çalışan bir model üzerinden yazılı sohbet.
- Türkçe ve İngilizce yanıtlar.
- Son birkaç mesajı oturum boyunca hatırlama.
- Basit matematik işlemleri.

Henüz bir masaüstü arayüzü, sesli konuşma veya Windows'u kontrol etme özelliği yok. Bunlar sonraki sürümlerin hedefi.

> **Durum:** Erken geliştirme aşaması. Otomatik testler geçiyor ancak gerçek modelle Windows üzerindeki ilk kullanım testi henüz tamamlanmadı.

## Başlamak için

Windows'ta **Python 3.10+** ve [Ollama](https://ollama.com/download/windows) gerekiyor. Ollama'nın bulut özelliklerini kapatıp yalnızca yerel adreste çalışacak şekilde ayarlanması önerilir.

Önce modeli indir:

```powershell
ollama pull qwen3:4b-instruct
```

Ardından projeyi indirip klasöründe çalıştır:

```powershell
py -3 eon.py
```

Daha hafif bir model kullanmak da mümkün. Kurulumun tamamı ve gerekli yerel bağlantı ayarları **[Windows kurulum rehberinde](docs/SETUP_WINDOWS.md)** anlatılıyor.

## Sırada ne var?

EON'un sonraki adımlarında güvenli araç izinleri, düzenlenebilir yerel hafıza ve sade bir masaüstü arayüzü var. Daha ilerideyse çevrimdışı sesli konuşma, dosyalarla çalışma ve izinli Windows işlemleri hedefleniyor.

Tüm planı [yol haritasında](docs/ROADMAP.md) görebilirsin.

## Nasıl bir proje?

EON'da temel fikir basit: **Önce güven, sonra yetenek.**

AI modeli yerel çalışır; harici AI servislerine bağlanmaz. Riskli işlemler, kullanıcı açıkça izin vermeden yapılmamalıdır. Bu izin sistemi henüz geliştirilme aşamasındadır; mevcut prototip zaten dosya değiştiremez veya terminal komutu çalıştıramaz.

---

[**Sürümler**](https://github.com/bysquizy/EON/releases) · [**Kurulum**](docs/SETUP_WINDOWS.md) · [**Yol haritası**](docs/ROADMAP.md) · [**Güvenlik**](SECURITY.md) · [**Değişiklikler**](CHANGELOG.md)

<sub>EON geliştirme aşamasındadır. Açık kaynak lisansı henüz belirlenmemiştir.</sub>
