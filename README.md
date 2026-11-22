# EON

EON, Windows’ta Ollama ile çalışan yerel bir sohbet asistanıdır. Yanıtları yazılırken okuyabilir, durdurabilir, düzenlediğin mesajdan yeniden başlatabilir veya ayrı sohbetlerde sürdürebilirsin.

**v0.2.0** ile sohbetleri projelere ayırabilir, proje yönergeleri ve çalışma modları seçebilirsin.
**Ctrl+K** sohbet, model ve uygulama bulur. Geçmiş ekranı mesaj içeriklerini ve favorileri de arar.
Sohbet seçeneklerinden pano metnini taslağa alabilir veya sohbeti Markdown ve düz metin olarak indirebilirsin.

## Başlangıç

1. Python 3.10+ ve Ollama kur. Ollama’yı `127.0.0.1:11434` adresine bağla ve `OLLAMA_NO_CLOUD=1` ile yeniden başlat.
2. Bir kez `ollama pull qwen3:4b-instruct` çalıştır.
3. Sürüm ZIP’ini çıkar ve `baslat.bat` dosyasını aç. Tarayıcı açıkken terminali çalışır durumda tut.

Windows sohbet geçmişini, model tercihlerini ve elle eklenen hafıza notlarını kullanıcı hesabına bağlı DPAPI ile şifreler. Geçmiş ekranı kayıt durumunu gösterir. **Ctrl+Alt+N** yeni sohbet açar. **Esc** yanıt akışını durdurur. Uygulama başlatıcı yalnız seçtiğin programı açar.

Saat çevrimdışı çalışır. Hava durumunu kullanmak için Ayarlar’da koordinat gir, Open-Meteo erişimine izin ver ve güncelleme düğmesine bas.

[Windows kurulumu](docs/SETUP_WINDOWS.md) · [Gizlilik](docs/PRIVACY.md) · [Değişiklikler](CHANGELOG.md)
