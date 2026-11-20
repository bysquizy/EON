# EON v0.0.1 — Windows 11 kurulumu

Bu rehber **yazılı sohbet prototipi** içindir; henüz EXE yükleyicisi, sesli asistan veya Windows kontrolü yoktur.

## 1. Python

PowerShell'de `py -3 --version` çalıştır. Python 3.13 önerilir; kod 3.10+ hedefler. Kurulu değilse [resmî Windows Python sayfasından](https://www.python.org/downloads/windows/) Python Install Manager'ı yükle. Zaten kuruluysa yeniden kurmana gerek yok.

## 2. Ollama

[Resmî Ollama for Windows](https://ollama.com/download/windows) sürümünü kur. `ollama --version` ile kontrol et.

## 3. Yerel çalışma

Windows **kullanıcı ortam değişkenlerine** şunları ekle:

| Değişken | Değer |
| --- | --- |
| `OLLAMA_NO_CLOUD` | `1` |
| `OLLAMA_HOST` | `127.0.0.1:11434` |

PowerShell alternatifi:

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_NO_CLOUD", "1", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "127.0.0.1:11434", "User")
```

**Ollama'yı sistem tepsisinden tamamen kapatıp yeniden aç.** Yeni PowerShell penceresi aç.

## 4. Modeli bir kez indir

```powershell
ollama pull qwen3:4b-instruct
```

Bu modelin indirme boyutu yaklaşık **2,5 GB**; çalışma sırasında daha fazla RAM gerekebilir. Hafif seçenek: `ollama pull qwen3:1.7b`. İlk indirme için internet gerekir.

## 5. EON'u çalıştır

GitHub deposunu ZIP olarak indirip aç. `baslat.bat` dosyasına çift tıkla veya PowerShell'de depo klasöründeyken:

```powershell
py -3 eon.py
```

Hafif model için: `py -3 eon.py --model qwen3:1.7b`.

İlk deneme: `Merhaba EON` yaz. Matematik için `/hesap 2*(3+5)` kullan.

## 6. Testler

```powershell
py -3 -m unittest discover -s tests -v
```

Birim testleri gerçek modeli indirmez. Testlerin geçmesi, gerçek Windows + Ollama sohbetinin doğrulandığı anlamına gelmez.

## Sorun giderme

| Sorun | Kontrol |
| --- | --- |
| `py` yok | Python Install Manager / PATH ve yeni terminal |
| `ollama` yok | Ollama kurulumunu ve PATH'i kontrol et |
| Ollama'ya bağlanılamıyor | Servis çalışıyor mu, `127.0.0.1:11434` dinliyor mu? |
| Model bulunamadı | Seçtiğin model etiketini `ollama pull` ile indir |
| Çok yavaş | `qwen3:1.7b` ile dene, RAM/CPU kullanımını ölç |
| Sesli cevap yok | Ses özelliği henüz yok |

İlk prototipe hassas kişisel belgeleri ve parolaları vermemeni öneriyoruz.
