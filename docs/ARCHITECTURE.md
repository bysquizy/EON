# EON v0.0.2 mimarisi

```
Tarayıcı UI (HTML/CSS/JS)
     │ Aynı-origin, token + Origin kontrolleri
     ▼
Python ThreadingHTTPServer (127.0.0.1: rastgele port)
     │
     ├── EonService ── VolatileSession (RAM)
     │         │
     │         └── LocalOllama ── 127.0.0.1:11434 ── yerel model
     │
     └── ApplicationRegistry ── Windows App Paths + Start Menu kısayolları
                         └── LOCALAPPDATA/EON/applications.json
```

Python standart kütüphanesi kullanılır. Arayüzde harici font veya script yoktur.

**Altı sohbet özelliği:** Geçmiş RAM'den okunur; yenileme yalnız son yanıtın yerini alır; model listesi Ollama'daki kurulu yerel modellerden gelir; özet sohbet geçmişini değiştirmez; uzunluk system prompt + token sınırıyla belirlenir; istatistikler oturuma aittir.

**Windows başlatıcı:** yalnız belirli uygulama kayıtları üzerinden, tek bir kullanıcı tıklamasıyla `.exe`/`.lnk` açma. Sohbet metninden araç çağrısı çıkarılmaz; komut yorumlayıcı yoktur. Otomatik keşif eksik kalabilir ve kullanıcı yol ekleyebilir.

**Sınırlar:** Bu sürüm gerçek masaüstü uygulaması gibi görünen yerel bir web arayüzüdür; ayrı bir WebView/EXE değildir. Kalıcı şifreli hafıza, sesli kontrol ve arka plan görevleri planlama aşamasındadır.
