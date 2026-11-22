# Windows'ta EON v0.0.2

EON şimdilik Python ile açılan yerel bir web arayüzüdür. Henüz `.exe` yükleyicisi yoktur.

### 1. Python ve Ollama

[Python 3.10+](https://www.python.org/downloads/windows/) ve [Ollama for Windows](https://ollama.com/download/windows) kurulu olmalı. PowerShell'de sürümleri kontrol et:

```powershell
py -3 --version
ollama --version
```

Python zaten yüklüyse yeniden kurma. EON'un kendisi üçüncü taraf Python paketi gerektirmez.

### 2. Ollama'yı yerel moda ayarla

Windows **kullanıcı ortam değişkenleri** üzerinden şunları tanımla:

| Değişken | Değer |
| --- | --- |
| `OLLAMA_NO_CLOUD` | `1` |
| `OLLAMA_HOST` | `127.0.0.1:11434` |

PowerShell ile de ayarlanabilir:

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_NO_CLOUD", "1", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "127.0.0.1:11434", "User")
```

**Ollama'yı tamamen kapatıp yeniden başlat.** EON, modelle yalnız `127.0.0.1:11434` adresinde iletişim kurar.

### 3. Modeli indir

```powershell
ollama pull qwen3:4b-instruct
```

Daha hafif bir seçenek için `ollama pull qwen3:1.7b` kullanılabilir. İlk indirme internet gerektirir. Daha sonra EON, yalnızca Ollama'nın kurulu yerel modellerini listeler; bulut modeli seçmez.

### 4. EON'u başlat

GitHub'da **Code → Download ZIP** seçeneğini kullanıp arşivi aç. İçindeki `baslat.bat` dosyasını çalıştır veya proje klasöründe:

```powershell
py -3 eon.py
```

Tarayıcıda rastgele bir yerel port üzerinden EON açılır. Kapatmak için terminalde **Ctrl+C** yap. Varsayılan tarayıcıyı otomatik açmak istemiyorsan `py -3 eon.py --no-browser`. Terminal modu için `py -3 eon.py --cli`.

### 5. Uygulama başlatıcı

Soldaki **Uygulamalar** sekmesini aç. EON Windows kayıtlı uygulamalarını ve Başlat menüsündeki kısayolları arar. Bulunamayan uygulamayı seçerek **Yol → Gözat** ile `.exe` veya `.lnk` dosyasını göster; ardından kaydet ve **Aç** tuşuna bas.

Uygulama yolları sistemin kullanıcıya özel `%LOCALAPPDATA%\EON\applications.json` dosyasında saklanır. Bu dosya GitHub'a gönderilmez. Yalnız güvenilir programların dosyalarını seç; bir EXE'yi başlatmak Windows'ta kod çalıştırmak anlamına gelir.

### Komutlar

`/gecmis`, `/yeniden`, `/model`, `/model MODEL_ADI`, `/ozet`, `/uzunluk kisa`, `/uzunluk normal`, `/uzunluk detayli`, `/istatistik`, `/temizle`, `/hesap 2*(3+5)`.

### Sorun olursa

- **Model bulunamadı:** Ollama'nın çalıştığından ve `ollama list` komutunda bir yerel modelin göründüğünden emin ol.
- **Ollama'ya bağlanılamıyor:** Yerel `127.0.0.1:11434` ayarını ve Ollama'nın çalıştığını kontrol et.
- **Uygulama bulunamadı:** Yol ekle; bazı Store uygulamaları normal `.exe` veya Başlat menüsü kısayolu sunmayabilir.
- **Dosya seçici açılmıyor:** Tam `.exe` veya `.lnk` yolunu elle girebilirsin.
- **Yanıt yavaş:** Daha küçük yerel model dene. Modelin boyutu ve bilgisayarın kaynakları önemlidir.

Geliştirici testi: `py -3 -m unittest discover -s tests -v`.

**Not:** Bu sürümde kalıcı şifreli sohbet hafızası ve sesli konuşma bulunmaz. Windows üzerinde uçtan uca gerçek model ve uygulama açma testi henüz tamamlanmamıştır.
