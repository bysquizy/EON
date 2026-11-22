# Gizlilik

Sohbetler, başlıklar, elle kaydedilen notlar ve model tercihleri Windows'ta `%LOCALAPPDATA%\EON\library.dpapi` içinde kullanıcı hesabına bağlı olarak korunur. Geçici dosyaya da yalnız şifreli veri yazılır. Windows koruması veya kayıt başarısız olursa uygulama bellekte çalışır ve kayıt durumunu gösterir. Eski kasa korunur. Linux oturumları geçicidir.

Hafıza ekranına yalnız kullanıcının eklediği kayıtlar girer. Notlar model isteğine sığdıkları ölçüde dahil edilir. Modelle sohbet etmek, uygulama başlatma yetkisi vermez. Seçilen uygulama yolları aynı klasörde `applications.json` içinde saklanır.

Ollama çağrıları aynı bilgisayarda kalır. Hava durumu ayrı bir istektir. Ayarlar ekranında açık izin ve güncelleme eylemiyle girilen koordinatlar Open-Meteo’ya gönderilir. Servis bağlantının IP adresini de görür. Konum otomatik alınmaz. Hava durumu izni sekme yeniden açıldığında kapanır.

DPAPI aynı kullanıcı hesabıyla çalışan diğer yazılımlara karşı yalıtım sağlamaz. Tarayıcı, işletim sistemi, yedekler ve Ollama günlükleri kendi saklama kurallarına tabidir.

Projeler, modlar, favoriler ve görünüm tercihleri de aynı şifreli kasaya dahildir.
Sohbet taslakları yalnız açık sekmenin belleğindedir. Pano metni ancak **Panoyu oku ve taslağa al** düğmesiyle okunur.
Metni inceleyip Gönder’e bastığında yerel modele iletilir. Markdown ve metin dışa aktarımları onaydan sonra
tarayıcıda üretilir. İndirilen dosyalar düz metindir ve kullanıcı tarafından ayrıca korunmalıdır.
