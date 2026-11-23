# EON v0.5.0

EON, Windows üzerinde çalışan yerel öncelikli kişisel yapay zekâ çalışma ortamıdır. Varsayılan sağlayıcı bilgisayarındaki yerel Ollama servisidir (`127.0.0.1:11434`). İsteğe bağlı olarak Google AI Studio API anahtarınla ayrı ve onaylı Gemini bulut sohbetleri açabilirsin.

## v0.5.0 ile Gelen Başlıca Özellikler

- **EON Projects 2.0 & Yerel Bilgi Tabanı:** Her proje için ayrı yönergeler, çalışma notları, model/profil seçimi ve yerel belge indeksi (TXT, MD, PDF, DOCX, CSV, XLSX). SQLite FTS5 / BM25 ve isteğe bağlı Ollama vektör gömmeleriyle çevrimdışı kaynaklı arama.
- **EON Actions:** İzinli çalışma klasörlerinde dosya arama, okuma, özetleme, klasör oluşturma, metin belgesi üretme, güvenli yeniden adlandırma ve uygulama başlatma. Yazma/değiştirme işlemlerinde önizleme, açık kullanıcı onayı, önceki sürüme geri alma (rollback) ve yerel denetim kaydı (audit log).
- **EON Studio:** Sohbet yanıtlarını ve tablo verilerini önizleyerek DOCX, PDF, XLSX, CSV, Markdown ve TXT dosyalarına dönüştürme; sayısal tablolardan otomatik sütun grafiği önizlemesi.
- **EON Research:** Onaylı Gemini sohbetlerinde Google Search Grounding desteği ve gerçek kaynak/bağlantı etiketleri.
- **EON Memory 2.0:** Kategori, kaynak, proje kapsamı, oluşturulma/son kullanım tarihi ve çelişen bilgi tespitiyle kontrollü kişisel hafıza.
- **EON Model Router & Vision:** Hızlı, Dengeli ve Derin Düşünme profilleri; gerçek token/süre metrikleri; PNG/JPEG/WebP görsel analizi.
- **EON Focus & Tasks:** Pomodoro odak sayacı, onaylı görev listesi, günlük çalışma özeti ve çevrimdışı `.ics` takvim içe/dışa aktarımı.
- **EON Command Center:** Sistem RAM'i ile Ollama model belleğini ayrı gösteren sağlık paneli, model boşaltma ve hassas içerik barındırmayan istek metrik geçmişi.

## Başlangıç

1. Python 3.10+ kur. Yerel model kullanacaksan Ollama kurup `ollama pull qwen3:4b-instruct` çalıştır; Gemini için Ollama gerekmez.
2. Proje klasöründeki `baslat.bat` dosyasını aç. Terminali açık tut (veya konsolsuz açılış için `baslat.bat --silent` kullan).
3. Yeni sohbet başlat veya **Ctrl+K** ile tüm çalışma alanı komutları, projeler, belgeler, modeller ve uygulamalar arasında geçiş yap.

[Windows kurulumu](docs/SETUP_WINDOWS.md) · [Mimari](docs/ARCHITECTURE.md) · [Gizlilik](docs/PRIVACY.md) · [Güvenlik](SECURITY.md) · [Sürüm notları](docs/releases/v0.5.0.md)
