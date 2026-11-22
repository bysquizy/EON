# EON mimarisi

**v0.0.3:** Python `http.server` üzerinde yalnızca `127.0.0.1` adresine bağlanan yerel web uygulaması. Tarayıcı ile EON servisi aynı origin'i kullanır. Ollama modeli yine yalnız yerel `127.0.0.1:11434` adresinden çağrılır.

- `eon/server.py`: HTTP API, Origin ve CSRF kontrolü, sağlık kontrolü, statik arayüz.
- `eon/service.py`: Sohbet, model, özet, yanıt uzunluğu ve eşzamanlılık yönetimi.
- `eon/session.py`: RAM'deki ayrı sohbetler, başlıkları ve geçmiş.
- `eon/launcher.py`: Kullanıcının açık isteğiyle uygulama keşfi, EXE/LNK doğrulama ve başlatma.
- `eon/ui/`: Harici JS/CSS kaynağı gerektirmeyen yerel arayüz.

Sohbet içeriği diske yazılmaz. Uygulama yolları yerel bir ayar dosyasına kaydedilir. Rastgele yerel port, oturuma özgü CSRF token ve sabit origin denetimi uygulanır. EON terminal komutlarını ve modelin istediği otomatik bilgisayar eylemlerini çalıştırmaz.

**Gelecek:** Kalıcı sohbet için şifreli depolama; fail-closed izin/araç akışları ve çevrimdışı ses. Bu özellikler bugün uygulanmış değildir.
