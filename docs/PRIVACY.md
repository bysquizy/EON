# Gizlilik

Ollama sohbetleri loopback üzerinden yerel modele gönderilir. EON kendi başına Google’a bağlanmaz. Google bağlantı testi API anahtarıyla model listesini ister. Karşılaştırma düğmesi onaydan sonra iki sağlayıcıya sabit bir aritmetik soru gönderir.

Gemini’ye geçerken ayrı bir bulut sohbeti oluşturulur. Gönderilen veri, bu sohbetin yeni mesajı, bütçeye sığan yakın geçmişi ve kısa sistem yönergesidir. Genel notlar ve özel yönergeler ayrı kutularla açılır. Proje yönergeleri ve diğer sohbetler kapsam dışındadır. Yeniden başlatmada bulut gönderim onayı sona erer. Sağlayıcı hatasında otomatik geçiş yapılmaz.

Google’ın ücretsiz ve ücretli katmanlarında veri kullanımı ve kota koşulları farklı olabilir. Ücretsiz hizmetlerde girdiler ve çıktılar ürün geliştirmek için işlenebilir ve insan incelemesine konu olabilir. Bölgesel koşulları kendi hesabın için kontrol et. EON ödeme hesabı açmaz. [Google hizmet koşulları](https://ai.google.dev/gemini-api/terms) · [Fiyatlar](https://ai.google.dev/gemini-api/docs/pricing) · [Kota](https://ai.google.dev/gemini-api/docs/rate-limits)

Windows’ta sohbet ve tercih kasası `%LOCALAPPDATA%\EON\library.dpapi`, Google anahtarı ayrı `gemini.dpapi` dosyasındadır. API anahtarı maskeli yerel Windows penceresinden alınır ve Google’a HTTPS başlığında gönderilir. Şifreleme çalışmıyorsa düz metin kayıt yapılmaz. Linux’ta sohbetler oturum belleğindedir.

Uygulama yolları yerel başlatıcı ayarlarında bulunur. Özel simgeler piksele dönüştürülüp sohbet kasasına kaydedilir. Pano yalnız düğmeye basıldığında okunur. Markdown ve TXT indirmeleri şifresizdir.

Hava durumu kurulumunda şehir seçimi çevrimdışıdır. Kullanıcı izin verip güncel veriyi istediğinde seçtiği koordinatlar Open-Meteo’ya gönderilir. Tercih kasada saklanır. İzni kapatmak kayıtlı konumu kaldırır. EON arka planda konum aramaz.


## Gemini aktarım izni v0.4.1

Gemini sohbetleri için kalıcı bulut izni, model konuşma bağlamını kullanabilmeden önce açıkça istenir ve DPAPI sohbet kasasında saklanır. Genel hafıza ve özel yönergeler ayrı seçimlerdir. Projeye bağlı sohbetlerde yalnız o projenin yönergeleri ve seçilmiş notları kullanılabilir; başka projelerin içerikleri gönderilmez. İzin Ayarlar ekranından kapatılabilir. v0.4.0 kasaları paylaşımı etkinleştirmeden açılır.

## v0.5.0 Bilgi Tabanı, Araştırma ve Görsel Gizliliği

- **Yerel Bilgi Tabanı:** İçe aktarılan belgeler yerel olarak ayrıştırılır ve DPAPI kasasında şifrelenir. Gemini sohbetlerinde proje belgelerinden bulunan parçalar yalnızca hem genel yönerge paylaşımı hem de ilgili projenin **Bilgi Tabanı bulut paylaşımı** (`share_docs`) açıkça işaretlenmişse gönderilir.
- **Kaynaklı Araştırma (Grounding):** Google Search Grounding yalnız onaylı Gemini sohbetlerinde kullanıcı Araştırma düğmesini etkinleştirdiğinde çalışır. Yerel Ollama sohbetlerinde gizli web araması yapılmaz.
- **Görseller (Vision) ve İstek Günlüğü:** Sohbete eklenen görseller yerel modelde cihaz dışına çıkmaz; Gemini sohbetinde yalnız bulut izni açıkken gönderilir. Command Center istek geçmişi varsayılan olarak istem veya yanıt metinlerini kaydetmez; yalnızca zaman, süre, sağlayıcı, model ve token sayısını tutar.
