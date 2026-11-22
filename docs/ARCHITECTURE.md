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
