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
