# Windows'ta EON'u çalıştırmak

EON v0.0.1 henüz bir EXE uygulaması değil. Şimdilik Python ve Ollama ile çalışan bir sohbet prototipi.

## 1. Gerekenleri kur

- [Python](https://www.python.org/downloads/windows/) (3.10 veya üzeri; 3.13 önerilir)
- [Ollama for Windows](https://ollama.com/download/windows)

PowerShell'de `py -3 --version` ve `ollama --version` komutlarıyla kurulumları kontrol edebilirsin. Python zaten yüklüyse tekrar kurmana gerek yok.

## 2. Ollama'yı yerel çalışacak şekilde ayarla

Windows kullanıcı ortam değişkenlerine şu iki değeri ekle:

| Değişken | Değer |
| --- | --- |
| `OLLAMA_NO_CLOUD` | `1` |
| `OLLAMA_HOST` | `127.0.0.1:11434` |

İstersen PowerShell'de kullanıcı düzeyinde ayarlayabilirsin:

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_NO_CLOUD", "1", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "127.0.0.1:11434", "User")
```

Sonrasında Ollama'yı tamamen kapatıp yeniden aç.

## 3. Modeli indir

```powershell
ollama pull qwen3:4b-instruct
```

Daha hafif seçenek: `ollama pull qwen3:1.7b`. İlk indirme internet gerektirir.

## 4. EON'u başlat

Depoyu **Code → Download ZIP** üzerinden indirip aç. Klasördeki `baslat.bat` dosyasını çalıştır veya PowerShell'de:

```powershell
py -3 eon.py
```

Hafif model için:

```powershell
py -3 eon.py --model qwen3:1.7b
```

`/yardim` komutuyla seçenekleri görebilirsin.

## Bir sorun olursa

Ollama'nın çalıştığını, indirdiğin modelin doğru olduğunu ve Python/Ollama komutlarının bulunduğunu kontrol et. Yanıtlar yavaşsa daha küçük modeli dene.

Testleri çalıştırmak için: `py -3 -m unittest discover -s tests -v`.

> Bu sürüm henüz gerçek Windows + Ollama sohbetiyle uçtan uca doğrulanmadı. Hassas verilerle kullanılması önerilmez.
