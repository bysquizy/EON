# EON'u Windows'ta çalıştırmak

EON v0.5.0, Python ile çalışan yerel bir tarayıcı çalışma ortamıdır. Henüz `.exe` kurulum dosyası yoktur.

### Kurulum

1. [Python 3.10+](https://www.python.org/downloads/windows/) kur.
2. Yerel model kullanacaksan [Ollama](https://ollama.com/download/windows) kur, `OLLAMA_NO_CLOUD=1` ve `OLLAMA_HOST=127.0.0.1:11434` ayarlarını yapıp `ollama pull qwen3:4b-instruct` çalıştır. Gemini için Ollama gerekmez ve EON onu otomatik başlatmaz.
3. GitHub'da **Releases → v0.5.0 → Source code (zip)** arşivini indir ve klasöre çıkar.
4. `baslat.bat` dosyasına çift tıkla. Alternatif: klasörde `py -3 eon.py`. İsteğe bağlı `baslat.bat --silent` konsolsuz başlatır; başlangıç hataları Windows uyarısı olarak gösterilir.

Terminalde `EON v0.5.0 hazır. Yerel adres: http://127.0.0.1:...` yazdığında arayüz tarayıcıda açılır. Terminali açık tut. EON'u durdurmak için **Ctrl+C**.

### “Failed to fetch” / bağlantı kesildi

Bu ifade, tarayıcının EON'un Python sunucusuna ulaşamadığı durumlarda görülebilir. Ollama ile bağlantı hatası bundan **farklıdır**.

1. EON'u başlattığın **terminal penceresi hâlâ açık mı?** Kapandıysa `baslat.bat` dosyasını yeniden çalıştır.
2. Sunucuyu tekrar başlattığında **yeni açılan tarayıcı sekmesini kullan**. EON her çalışmada farklı yerel port seçebilir; eski sekmenin adresi artık çalışmayabilir.
3. Yeni sekmede “Yeniden bağlan” düğmesini dene. Terminalden yeni adresi görebilirsin.
4. Tarayıcıda terminalde yazan `http://127.0.0.1:PORT/api/health` adresini aç. `{"status":"ok"...}` dönüyorsa EON sunucusu ayaktadır.
5. EON sunucusu ayaktaysa ama model yanıt vermiyorsa `ollama list` komutuyla kurulu modeli, `ollama --version` ile Ollama'yı kontrol et. Bilgisayarda iki ayrı Ollama veya EON örneği açmamaya dikkat et.

Yanıt uzunluğu gibi ayarlar model yanıtını beklemeden değiştirilebilir; yavaş model çağrıları artık arayüz ayarlarını kilitlemez.

### Sohbetler

Soldaki **Geçmiş** simgesinden sohbetlerini listeleyebilir, seçip açabilir veya silebilirsin. **+** düğmesiyle yeni sohbet başlar. Windows, sohbetleri ve elle eklediğin hafıza notlarını hesabına bağlı DPAPI ile şifreler. Geçmiş ekranında kayıt durumunu kontrol edebilirsin. Başka bir EON örneği kasayı kullanıyorsa bu oturum bellekte çalışır. Ctrl+Alt+N yeni sohbet açar, Esc yanıt akışını durdurur.

### Programları bulma

**Uygulamalar → Yeniden ara** seçeneğiyle Başlat menüsü, kayıtlı uygulamalar ve masaüstü `.lnk` kısayollarını tarat. Ayrıca OneDrive Masaüstü veya elle seçilen `.exe`/`.lnk` dosyalarını kullanabilirsin. Yalnız güvendiğin uygulamaları aç.

### Test

`py -3 -m unittest discover -s tests -v`

Birim ve sahte model testlerinin geçmesi, gerçek Windows cihazında her uygulamanın açıldığını kesinleştirmez. İlk kullanımdaki sorunları sürüm notlarında bildirebiliriz.

### v0.1.0 kullanıcıları

Önce çalışan EON örneğini kapat. Aynı Windows hesabında yeni klasördeki başlatıcıyı aç.
EON mevcut kasayı okur. Eski sohbetler **Projesiz** altında **Genel Asistan** moduyla görünür.
İlk değişiklikte yeni alanlar aynı şifreli kasaya atomik olarak yazılır. Yeni alanları korumak için sonrasında v0.3.0 kullan.

Ctrl+K ile Komut Merkezi’ni aç. Ok tuşlarıyla gez, Enter ile seç ve Esc ile kapat.
Sohbetin üstündeki mod düğmesi proje ataması, pano ve dışa aktarma seçeneklerini açar.

### Gemini ve başlangıç bağlantısı

Terminaldeki tam başlatma bağlantısını kullan. Adres sonundaki oturum bilgisi özel API uçlarını açar. Gemini istiyorsan Ayarlar’dan Windows anahtar penceresini aç, model listesini test et ve bulut sohbetini onayla. Kota veya bağlantı hatasında **Yerel sohbet aç** ile devam edebilirsin.

### Düşük bellekli bilgisayarlar

Model belleğini Ayarlar’dan izle. Önce 3 dakikayı dene. Belleği başka uygulamaya bırakmak için boşalt düğmesini veya yanıttan hemen sonra boşaltmayı seç. Hemen boşaltma sonraki istekte model yükleme süresini artırabilir. EON sunucusunu kapatmak Ollama sürecini durdurmaz.

Ollama’yı kendin yapılandırıyorsan `OLLAMA_MAX_LOADED_MODELS=1` ve `OLLAMA_NUM_PARALLEL=1` ile eşzamanlı yükü sınırlayabilirsin. Desteklenen donanımda `OLLAMA_FLASH_ATTENTION=1` ve uygun modellerde `OLLAMA_KV_CACHE_TYPE=q8_0` bellek ihtiyacını azaltabilir. Daha güçlü nicemleme kaliteyi etkileyebilir. EON ortam değişkenlerini değiştirmez. [Ollama yapılandırma rehberi](https://docs.ollama.com/faq)

### Önceki sürüme dönüş

EON’u kapat. Windows hesabının EON veri klasöründeki güncel library.dpapi dosyasını ayrı bir adla koru. Aynı klasördeki library.pre-v030.dpapi dosyasının bir kopyasını library.dpapi adıyla yerleştir ve önceki EON sürümünü başlat. Yedek ilk yükseltme öncesindeki sohbetleri içerir. v0.3.0 ile sonradan yapılan değişiklikler güncel kasa kopyasında kalır.

### Parola korumalı yedek

Ayarlar → Şifreli yedek ekranından en az 12 karakterli bir parola seçip dosyayı indir. Geri yükleme için dosya ve parola gerekir. Şifreli Windows kasası açık olmalı. Geri yükleme mevcut sohbetleri ve EON tercihlerini değiştirir. Önce güncel kayıtların ayrı bir yedeğini al.
