# Değişiklikler

## v0.5.0

- **EON Projects 2.0 ve Yerel Bilgi Tabanı:** Proje başına çalışma notları, model/profil tercihleri, hafıza kapsamı ve TXT, MD, PDF, DOCX, CSV, XLSX belge içe aktarma. SQLite FTS5 (BM25) ve isteğe bağlı Ollama `/api/embed` vektör araması ile yanıtlarda dosya ve sayfa/bölüm kaynağı gösterimi.
- **EON Actions:** İzinli yerel klasörlerde çalışan modüler beceri sistemi (`search_files`, `read_file`, `summarize_file`, `create_folder`, `write_text_file`, `rename_file`, `open_app`). Yazma/değiştirme işlemlerinde önizleme, açık onay, yedekli geri alma (rollback), sembolik link/junction ve tehlikeli uzantı engeli ile yerel denetim günlüğü.
- **EON Studio:** Sohbet yanıtlarından ve tablolardan harici kütüphane zorunluluğu olmadan standart DOCX, PDF, XLSX, CSV, Markdown ve TXT belge üretimi; önizleme ve basit grafik çizimi.
- **EON Research:** Onaylı Gemini bulut sohbetlerinde isteğe bağlı Google Search Grounding (`googleSearch`) desteği ve doğrulanmış `groundingMetadata` web kaynaklarının gösterimi.
- **EON Memory 2.0:** Hafıza kayıtlarına kategori, kaynak, proje kapsamı, tarihçe ve çelişen bilgi algılama/çözümleme akışı eklendi.
- **EON Model Router, Vision ve Voice:** Hızlı, Dengeli ve Derin Düşünme profilleri; model yetenek keşfi; gerçek token kullanımı (`usageMetadata` / `eval_count`) ve düşünme imzası (`thoughtSignature`) korunumu; PNG/JPEG/WebP görsel ekleme ve doğrulama; bas-konuş ses girişi ve Windows SAPI yerel seslendirme.
- **EON Focus & Tasks ve Command Center:** Pomodoro sayacı, görev listesi, `.ics` takvim içe/dışa aktarımı, Windows sistem RAM'i ile Ollama model belleğini ayrı gösteren sistem sağlık ekranı ve`.pre-v050.dpapi` otomatik kasa yedeği.

## v0.4.1

- Gemini sohbetlerinde EON'un kişiliği, aktif proje yönergeleri ve tercih edilen model kullanılır. Açıkça seçilen hafıza/yönergeler DPAPI kasasında saklanan izne bağlıdır; eski kasalar varsayılan olarak paylaşımı etkinleştirmez.
- Gemini `MAX_TOKENS` yanıtları tamamlanmış sayılmaz veya sohbet geçmişine kaydedilmez. Dengeli ve detaylı Gemini yanıtlarına daha geniş çıktı bütçesi ayrılır.
- Windows başlangıcı Python 3.10+ kontrolü, kullanıcı başına tek örnek kilidi, güvenli pencere odağı ve isteğe bağlı `baslat.bat --silent` ile iyileştirildi. Konsol çıktısında oturum sırrı gösterilmez; Ollama otomatik başlatılmaz.
- Google Search Grounding bu sürüme alınmadı: güncel API arayüzü ve proje bazlı ücret/kota koşulları otomatik aramayı güvenli bir varsayılan yapmıyor.

## v0.4.0

- Gemini anahtar doğrulaması, model keşfi ve ayrı örnek yanıt testi.
- Ollama bellek tercihleri, uygulama favorileri ve önbellekli Shell simgeleri.
- Proje ve sohbet ayarları, şablonlar, odak modu, arama ve geri alma.
- Parola korumalı yedek ve yerel veri doğrulaması.

## v0.3.0

- Yeni sohbet kenar çubuğu, kare bazlı akış güncellemesi ve hareket azaltma desteği.
- İsteğe bağlı Gemini sohbetleri, ayrı DPAPI anahtar kasası ve paylaşım onayları.
- Ollama model önbelleği, bekletme süresi, boşaltma ve sistem sağlığı.
- İlk hava durumu kurulumu, yerel şehirler, uygulama simgeleri ve doğrulanan başlatma hedefi.
- Özel GET erişimi ve eski şifreli kasa için geri dönüş kopyası.

## v0.2.0

- Projeler, projeye özel yönergeler, dört hazır mod ve özel modlar.
- Ctrl+K komut paleti, mesaj içeriği araması, sabitlenmiş sohbetler ve favori mesajlar.
- İzinli pano yardımcısı, yerel Markdown ve metin indirmeleri.
- Açık tema, vurgu renkleri, kompakt görünüm ve azaltılmış hareket.
- Sekme içi sohbet taslakları ve kod bloğunu tek tıkla kopyalama.
- v0.1.0 şifreli kasalarını okuyan geriye uyumlu yükleme.

## v0.1.0

- Sohbet yanıtları için akış, iptal, mesaj düzenleme ve temel Markdown görünümü.
- Windows DPAPI ile şifreli sohbet geçmişi, kullanıcı notları ve ayarlar.
- Başlık araması, yeniden adlandırma, çevrimdışı saat ve izinli hava durumu.
- Sınırlı model bağlamı, özel yönergeler ve yanıt sınırları.
- Gerçek Ollama için isteğe bağlı kısa Türkçe ve İngilizce doğrulama betiği.

## v0.0.3

- Mesaj gönderildiğinde giriş alanını hemen boşaltma ve bekleme durumu.
- Ayrı sohbetler, geçmişten açma ve silme.
- Masaüstü ve OneDrive Masaüstü kısayollarını bulma.
- Uzun model yanıtları sırasında ayarlara erişimin iyileştirilmesi.
- Bağlantı sorunu ve yeniden bağlanma ekranı.
- Güncel kurulum ve sorun giderme rehberi.

## v0.0.2

- Yerel web arayüzü, model ve yanıt modu seçimi.
- Sohbet özeti, yeniden üretme ve oturum istatistikleri.
- Windows uygulama başlatıcı ve elle uygulama yolu ekleme.

## v0.0.1

- Python CLI, yerel Ollama sohbeti ve basit hesaplama.
