# Mimari

EON standart Python kütüphanesi ve tarayıcıdaki yerel HTML, CSS ve JavaScript ile çalışır. HTTP sunucusu rastgele bir loopback portu seçer. Durumu değiştiren istekler Host, Origin, CSRF ve içerik türü denetimlerinden geçer.

Ollama istemcisi yalnız sabit loopback adresine bağlanır ve kurulu yerel modelleri kullanır. Sohbet yanıtı satır bazlı JSON olarak işlenir. Her üretim kaynak sohbeti ve ayarlarını yakalar. İptal soket okumayı keser. Başarıyla biten yanıt tek işlemde geçmişe eklenir. Düzenleme, sonraki mesajları ancak yeni yanıt tamamlandığında değiştirir.

Servis bağlam için en son tamamlanmış mesaj çiftlerini ve ayrılan alan elverdiğinde eski kullanıcı mesajlarından kısa alıntıları seçer. Bayt bütçesi token sayısının yaklaşık değeridir. Kullanıcının isteyebildiği yerel model özeti ayrıca üretilir.

Windows kasası DPAPI ile korunan tek bir dosyadır. Kullanıcı bağlamında şifreleme, tek yazıcı kilidi ve atomik dosya değişimi uygulanır. Bu boyuttaki koleksiyonlar için SQLCipher ve ek anahtar dağıtımı gerekmez. Kasa her değişiklikte yeniden şifrelenir. Uygulama kayıtları ayrı bir yerel dosyada tutulur.

## Proje ve sohbet kapsamı

Kasa şeması 2, v0.1.0 sohbet dizilerini olduğu gibi saklar. Proje, mod, favori ve görünüm bilgileri ek alanlardadır.
Sürümsüz v0.1.0 kayıtları açılışta diske dokunmadan varsayılanlarla yüklenir. Bilinmeyen şemada yazma kapanır.
Model isteği yalnız kaynak sohbetin geçmişini, o sohbete atanmış mod ve proje yönergelerini kullanır.
Kullanıcının genel hafızası ve genel yönergeleri sohbetler arasında ortaktır. Etkin üretim sırasında kaynak sohbetin kapsamı değiştirilemez.
Arama açık bir kullanıcı sorgusuyla, RAM’de, en fazla 100 sonuç döndürür.

## v0.3.0 sağlayıcıları ve depolama

Ollama NDJSON ve Gemini SSE istemcileri aynı parça ve iptal arayüzünü kullanır. Gemini ayrı bir sohbete atanır ve kimlik bilgisi oluşturma anında ayrı DPAPI deposundan alınır. Yeniden başlatma bulut aktarım onaylarını sıfırlar. Çevrimdışı şehir listesi ve isteğe bağlı sistem sağlığı için arka plan taraması yapılmaz.

Kasa şeması 3, şema 1 ve 2’yi okuyabilir. Eski şifreli içerik ilk yazımdan önce .pre-v030.dpapi kopyasına atomik olarak alınır. Yedek oluşturma başarısızsa kalıcı yazma kapanır. Gizli anahtar sohbet kasasına veya yedeğine girmez. Özel simge için yalnız 48 × 48 RGBA piksel kabul edilir. Model listesi başarılı yanıtlarda on saniye önbelleğe alınır.

Gemini model kimlikleri sabitlenmez. Google model listesinde generateContent destekleyen Gemini adları seçilebilir. İstemci streamGenerateContent üzerinden metin parçalarını işler ve sağlayıcı hata gövdelerini kullanıcıya geri vermez. [Model listesi](https://ai.google.dev/api/models) · [Üretim API’si](https://ai.google.dev/api/generate-content)

Yüklü model ve VRAM miktarları sorgu anında Ollama API’sinden gelir. Model çıktısındaki eval_count ve eval_duration üretim hızına çevrilir. EON’un ilk parça ve toplam süre ölçümleri ayrı tutulur. [Ollama çalışan modeller](https://docs.ollama.com/api/ps) · [Ollama yapılandırması](https://docs.ollama.com/faq)

## v0.4.0 yedek ve görünüm

Şema 3 ek sohbet ve proje ayarlarını isteğe bağlı bir alanda taşır. Eski şifreli kasalar varsayılan değerlerle açılır. Parola korumalı yedek tarayıcıda AES-GCM ile hazırlanır. Geri yükleme aktif üretime izin vermez ve önce yeni kasayı doğrular. Dosya yazımı tamamlanınca açık oturumun verileri değiştirilir. Uygulama simgeleri Windows’tan uygulama ekranı açıldığında alınır ve işlem belleğinde önbelleğe alınır.


## v0.4.1 Gemini ve Windows başlatma

Gemini bulut izni ve paylaşım kapsamı xtras.gemini alanında, şifreli kasa zarfıyla birlikte saklanır. Şema numarası değişmez; eski şema 3 kayıtlarında alan bulunmaz ve paylaşım kapalı kalır. Gemini model seçimi ilk erişilebilir Flash adını tercih eder. SSE MAX_TOKENS akışı hata verir ve sohbet mutasyonu gerçekleşmeden durur. Windows mutex adı kullanıcı profil yolunun SHA-256 özetiyle oluşturulur; erişim URL'si ikinci örneğe aktarılmaz. --silent, pyw/pythonw kullanan başlatıcılar içindir.


## v0.5.0 Çalışma Ortamı Modülleri

- **Bilgi Tabanı (`eon/knowledge.py`):** TXT, MD, CSV, DOCX, XLSX ve PDF belgelerini yerel olarak ayrıştırır, bölümlere ayırır ve bellek içi SQLite FTS5 (`bm25`) tablosunda indeksler. İlk yükseltmede mevcut şema 3 kasası `.pre-v050.dpapi` olarak yedeklenir ve yeni veriler kasa zarfındaki `v050` alanı altında şifrelenir.
- **Güvenli Eylemler (`eon/actions.py`):** İzinli klasör doğrulaması, sembolik link/junction (`FILE_ATTRIBUTE_REPARSE_POINT`) engeli, tehlikeli uzantı filtresi, önizleme jetonu, onay sonrası atomik dosya yazımı, önceki sürüme geri alma (`rollback_stack`) ve maskelenmiş denetim günlüğü (`audit_log`) sağlar.
- **Belge Üretimi (`eon/studio_gen.py`):** Standart kütüphane `zipfile`/`xml` ve PDF 1.4 nesne yapısıyla geçerli DOCX, XLSX, PDF, CSV, MD ve TXT çıktıları üretir.
- **Üretkenlik, Görsel ve Sistem Sağlığı (`eon/productivity.py`):** PNG/JPEG/WebP ikili başlık ve boyut doğrulaması, Pomodoro ve görev yönetimi, `.ics` takvim dönüşümü, Windows SAPI TTS süreç kontrolü ve `GlobalMemoryStatusEx` sistem RAM ölçümünü içerir.
