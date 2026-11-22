# EON'u Windows'ta çalıştırmak

EON v0.1.0, Python ile çalışan yerel bir tarayıcı uygulamasıdır. Henüz `.exe` kurulum dosyası yoktur.

### Kurulum

1. [Python 3.10+](https://www.python.org/downloads/windows/) ve [Ollama](https://ollama.com/download/windows) kur.
2. Windows kullanıcı ortam değişkenlerinden `OLLAMA_NO_CLOUD=1` ve `OLLAMA_HOST=127.0.0.1:11434` değerlerini ayarla. Ollama'yı tamamen kapatıp yeniden aç.
3. PowerShell'de `ollama pull qwen3:4b-instruct` komutunu çalıştır. Hafif model için `ollama pull qwen3:1.7b` kullanılabilir.
4. GitHub'da **Releases → v0.1.0 → Source code (zip)** arşivini indir ve klasöre çıkar.
5. `baslat.bat` dosyasına çift tıkla. Alternatif: klasörde `py -3 eon.py`.

Terminalde `EON v0.1.0 hazır. Yerel adres: http://127.0.0.1:...` yazdığında arayüz tarayıcıda açılır. Terminali açık tut. EON'u durdurmak için **Ctrl+C**.

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
