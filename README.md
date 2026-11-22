# EON Local v0.0.1

İlk **tamamen yerel yazılı sohbet prototipi**. Bulut AI API'si, API anahtarı, abonelik,
MCP, dosya taraması veya shell komut yürütme kullanmaz.

> Bu bir üretim uygulaması değildir. Henüz şifreli kalıcı hafıza, proje
> izolasyonu, ses, onay sistemi veya Windows kontrolü yoktur.

## Gerekenler
- Windows 11.
- Python 3.10 veya üzeri (Windows üzerinde `py -3` çalışmalı).
- Resmî Ollama: https://ollama.com/download/windows
- En az birkaç GB boş alan. Resmî Ollama Windows belgeleri ikili
  kurulum için en az 4 GB ve modeller için ek depolama belirtiyor.

## 1. Ollama'yı yalnız yerel olacak şekilde yapılandır
Windows > "Hesabınız için ortam değişkenlerini düzenleyin" penceresinde
iki kullanıcı değişkeni oluştur:

`OLLAMA_NO_CLOUD` = `1`
`OLLAMA_HOST` = `127.0.0.1:11434`

Ollama görev çubuğu simgesinden **Quit** seç, sonra Başlat menüsünden
yeniden aç. Resmî yönerge: https://docs.ollama.com/faq

Önemli: Ollama'nın bulut özelliklerini kapatmak, uygulamanın yazılım
güncellemeleri için asla internete çıkmayacağını garanti etmez.
EON'un kendi kodundaki model isteği yalnızca 127.0.0.1'e yapılır.

## 2. Modeli bir kere indir
PowerShell veya CMD'de ayrı bir komut olarak:

`ollama pull qwen3:4b-instruct`

Daha hafif model istiyorsan bunun yerine:

`ollama pull qwen3:1.7b`

Bu indirme için internet gerekir. Sonrasında yerel model sohbeti
internetsiz yapılabilir.

## 3. EON'u başlat
ZIP'i klasöre aç. `baslat.bat` dosyasına çift tıkla ya da:

`py -3 eon.py`

Hafif model indirdiysen:

`py -3 eon.py --model qwen3:1.7b`

## Komutlar
- `/yardim` — komutlar
- `/durum` — yerel model bilgisi
- `/hesap 2*(3+5)` — kod çalıştırmadan güvenli hesaplama
- `/temizle` — RAM'deki sohbet geçmişini sil
- `/cikis` — çıkış

## Test
`py -3 -m unittest discover -s tests -v`

Testler gerçek modeli kullanmaz. Gerçek Ollama + model kontrolü Windows
üzerinde ayrıca yapılmalıdır.

## Güvenlik ve gizlilik sınırları
- EON herhangi bir dış sunucuya bağlanmaz; istemci bağlantısı kaynak
  kodda `127.0.0.1:11434` adresine sabittir.
- URL yönlendirmeleri, proxy ya da uzak model çağrıları kullanılmaz.
- Sadece `qwen3:4b-instruct` ve `qwen3:1.7b` seçilebilir.
- Sohbet yalnız işlem belleğinde tutulur; EON kendisi dosyaya yazmaz.
- Ollama'nın kendi logları, işletim sistemi swap/çökme kayıtları veya
  disk önbelleği için mutlak gizlilik garantisi verilmez.
- Henüz kalıcı hafıza yok; EON v1.2.1 tasarımına uygun şifreli
  hafızaya geçmeden özel projelerini yükleme.
- Yanıtlar küçük yerel model tarafından üretildiği için doğrulama
  gerektirir. Bu prototip kendi kendine bilgisayarda iş yapamaz.

## Sonraki sürüm
v0.0.2: sunucu tarafı onay durum makinesi ve yalnız önceden
izinli klasöre not yazma aracı.
v0.0.3: SQLCipher ve Windows Credential Manager ile şifreli
veri kaydı; doğru çalışmıyorsa kalıcı kaydı kapalı tut.
v0.1: React sohbet arayüzü, proje ayrımı ve test edilmiş güvenli MVP.

Tasarım kaynağı: kullanıcıya ait EON Teknik Tasarım v1.2.1
(19 Kasım 2026). Yerel model mimarisi güncellenmiştir.
