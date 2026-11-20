# EON — Güvenlik politikası

**v0.0.1 bir prototiptir; güvenli masaüstü otomasyonu ürünü değildir.**

## Şu anda uygulanan kontroller

- Model seçimi iki yerel Qwen3 etiketiyle sınırlıdır.
- HTTP istemcisi yalnız `127.0.0.1:11434` adresine bağlanır.
- Yalnız `GET /api/tags` ve `POST /api/chat` izinlidir; otomatik model indirme yoktur.
- HTTP yönlendirmeleri takip edilmez; istek ve yanıt boyutları sınırlanır.
- Matematik işlemleri `eval`/`exec` kullanmaz.
- Dosya yazma, terminal çalıştırma ve Windows otomasyonu bulunmaz.
- EON sohbeti kalıcı veritabanına yazmaz.

## Henüz uygulanmayanlar

Şifreli hafıza, oturum kimlik doğrulaması, tek kullanımlık araç onayları, dosya yolu güvenliği, imzalı Windows paketi ve gerçek cihazda uçtan uca güvenlik testi.

## Güvenlik sözleşmesi

1. **Fail-closed:** Politika, şifreleme veya kimlik doğrulama başarısızsa riskli işlem yapılmaz.
2. **Her eyleme ayrı onay:** Özellikle her terminal komutu için kullanıcıdan ayrı, kapsamı belli izin.
3. **En az yetki:** Dosya/uygulama erişimi varsayılan kapalıdır.
4. **Model çıktısı güvenilmez:** Prompt injection veya içe aktarılan belge talimatı komut yürütme izni vermez.
5. **Negatif test zorunluluğu:** Reddetme, süre aşımı, tekrar kullanım ve argüman değiştirme testleri.
6. **Gizlilik:** PRIVATE/SECRET içerik açık izin olmadan dışarı aktarılmaz.
7. **Sırlar repoya girmez:** Anahtarlar, kişisel veritabanları ve özel günlükler commit edilmez.

Yerel model kullanmak **tam sistem güvenliği** veya tüm uygulamalar için sıfır ağ trafiği garantisi değildir. Windows, Ollama ve işletim sistemi logları ayrı risk yüzeyleridir.

**Güvenlik bildirimi:** Depo Private. Açıkları herkese açık issue'da paylaşma; depo sahibiyle özel kanaldan iletişim kur. [Gizlilik ayrıntıları](docs/PRIVACY.md).
