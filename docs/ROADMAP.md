# EON — 16 özellik ve sürüm yol haritası

**Ürün kararı:** Windows 11'de tamamen yerel model, harici AI API'siz çalışma, ek model aboneliği olmadan geliştirme.

Bu tablo EON v1.2.1 tasarımındaki 16 ürün kararını korur. Bulut model bağlantıları ve çevrimiçi araştırma servisleri sonraki yerel-only kararıyla kaldırılmıştır.

| # | Ürün alanı | Hedef | Bugünkü durum |
| --- | --- | --- | --- |
| 01 | Kişilik ve günlük bilgi | Sakin, zeki, samimi TR/EN asistan; yerel özetler | Kısmi: yazılı kişilik |
| 02 | Seçici hafıza | Önemli tercihleri sakla, gör, düzenle, sil | Plan |
| 03 | Görev yürütme | Adım adım izinli iş, ilerleme, durdurma, sonuç raporu | Plan |
| 04 | Windows ve ekran | Uygulama, pencere, medya, izinli ekran kontrolü | Plan |
| 05 | EON Studio | PDF/DOCX/XLSX/PPTX üret ve düzenle | Plan |
| 06 | Görev ve hatırlatma | Öncelik, hatırlatma, kullanıcı tarafından tamamlama | Plan |
| 07 | Prompt Köprüsü | Prompt hazırla/kopyala; otomatik dış gönderim yok | Plan |
| 08 | Ana arayüz | Minimal koyu cam, buz mavisi vurgu, sohbet merkezli UI | Plan |
| 09 | Sesli asistan | Kadın ses karakteri, TR/EN, Hey EON, söz kesme | Plan |
| 10 | Araştırma | Yerel belgelere dayalı, kaynaklı analiz; canlı web yok | Plan |
| 11 | Projeler/sohbetler | Ayrı projeler, sohbetler, dosyalar, özel talimatlar | Plan |
| 12 | Araçlar/izinler | Araçları aç/kapat; riskli her eyleme ayrı onay | Plan |
| 13 | Windows bildirimleri | Hatırlatma, yerel brief, tepsi ve kısayol | Plan |
| 14 | Gizlilik | Şifreli yerel hafıza, PUBLIC/PRIVATE/SECRET, denetim | Plan |
| 15 | Offline/performans | 16 GB RAM ve Intel iGPU'da ölçülebilir yerel çalışma | Kısmi: model adaptörü |
| 16 | Kişisel kurulum | Tek Windows cihazı, sade kurulum, ek AI aboneliği yok | Kısmi: Python kaynak kodu |

## Sürüm hedefleri

### v0.0.1 — İlk yerel çekirdek (mevcut)
- [x] Python CLI ve Ollama yerel istemcisi
- [x] Türkçe sistem talimatı, geçici RAM hafızası
- [x] Sınırlı matematik aracı ve otomatik testler
- [ ] Hedef Windows cihazında gerçek model testi

### v0.0.2 — Onay ve araç güvenliği (plan)
- [ ] Sunucu tarafı PENDING → GRANTED → CONSUMED onay durumu
- [ ] Süre aşımı, argüman değişikliği ve tekrar kullanım testleri
- [ ] Yalnız izinli klasöre not yazma aracı
- [ ] Her terminal komutu için ayrı açık onay

### v0.0.3 — Şifreli hafıza (plan)
- [ ] SQLCipher + Windows Credential Manager, Windows doğrulaması
- [ ] Şifreleme yoksa kalıcı kayıt yok (fail-closed)
- [ ] Görülebilir, düzenlenebilir, silinebilir hafıza
- [ ] Hassas veri sınıflandırması ve sızıntı testleri

### v0.1.0 — Arayüzlü ilk MVP (plan)
- [ ] React + TypeScript arayüzü
- [ ] FastAPI, loopback, oturum güvenliği
- [ ] Proje/sohbet ayrımı ve izinli araç akışı
- [ ] Windows'ta uçtan uca test edilmiş kullanım

### Daha sonraki sürümler
Yerel ses tanıma/sentezi, Hey EON, EON Studio, Windows bildirimleri, yerel kaynaklı araştırma ve izinli masaüstü otomasyonu. **Tarih veya teslim garantisi verilmez.**

## Değişmez ilkeler

Her terminal komutu ayrı onay alır. Özel dosya gizlice dışarı gönderilmez. Belirsiz ifade kesin görev kabul edilmez. Model çıktısı yürütme yetkisi değildir. Şifreleme/izin denetimi başarısızsa ilgili özellik kapanır. Araştırma raporu yalnız kullanıcı isterse dosyaya dönüştürülür.

Kaynak: EON Teknik Tasarım v1.2.1 (19.11.2026); yerel-only kararına uyarlanmıştır.
