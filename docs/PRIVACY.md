# EON gizliliği

**v0.0.3'te** sohbetler, ayrı oturumlar ve başlıkları yalnız çalışan Python işleminin belleğinde bulunur. Program kapanınca kaybolur. EON, şifrelenmemiş bir sohbet veritabanı oluşturmaz.

Uygulama başlatıcı, seçilen uygulamaların yerel yollarını `%LOCALAPPDATA%\EON\applications.json` dosyasına kaydeder. Bu dosya GitHub'a gönderilmez. Masaüstü kısayollarının keşfi yalnız bilgisayarda yapılır.

Model istekleri yalnız yerel Ollama'ya gider. Model indirme internet gerektirir. Windows, Ollama ve tarayıcının kendi sistem kayıtları EON'un kapsamı dışındadır.

Kalıcı ve kullanıcı tarafından düzenlenebilir **şifreli** geçmiş sonraki aşamanın hedefidir.
