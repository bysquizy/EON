# EON — Depo içeriği ve gizlilik politikası

EON'un kaynak kodu, README'si, teknik belgeleri, örnekleri, testleri ve GitHub Release açıklamaları **herkes için geçerli, genel proje bilgileri** içermelidir.

## Depoya eklenmemesi gerekenler

- Gerçek kişilerin adları, e-posta adresleri, telefonları, öğrenci veya müşteri numaraları
- Özel adresler, konumlar, eğitim/iş geçmişi veya kişiye özel günlük yaşam ayrıntıları
- Proje sahibi ya da herhangi bir kullanıcıya ait bilgisayarın tam marka/model/donanım profili
- Özel sohbetler, kişisel tasarım dosyalarının isimleri, tarihleri ve içerikleri
- Gerçek kullanıcı klasör yolları, oturum isimleri, parolalar, API anahtarları, erişim token'ları
- Kişiye ait veriler içeren ekran görüntüleri, test kayıtları veya örnek veritabanları

## Kabul edilen içerik

- Genel proje amacı, mimari, teknik gereksinimler ve ürün hedefleri
- **Örnek** sistem gereksinimleri ve farklı donanım sınıfları için genel performans notları
- Gerçek kullanıcıya bağlanamayan sentetik test verileri
- Güvenlik, gizlilik, kurulum, değişiklik geçmişi ve sürüm notları
- Kaynağı belirtilmiş genel teknik kararlar; özel konuşmalara veya kişisel belgelere atıf olmadan

## Yayın öncesi kontrol

1. Yeni veya değiştirilen dosyaları kişisel veri açısından elle incele.
2. `python scripts/check_repo_privacy.py` çalıştır; otomatik taramanın sınırlı olduğunu unutma.
3. Release notlarını ve kaynak kodu arşivini yayın öncesinde incele.
4. Bir Release oluşturulduktan sonra tag/arşiv geçmişinin otomatik güncellenmediğini dikkate al.
5. Gizlilik sorunu fark edilirse yeni içerik eklemeyi durdur; geçmiş sürümler ve commit'ler için ayrı temizlik planı uygula.

**Önemli:** GitHub kullanıcı adı, commit yazarı ve e-posta metadata'sı Git tarafından yönetilebilir. Bu politika yalnız içerik incelemesi sağlar; geçmişi veya platform metadata'sını anonimleştirme garantisi vermez.
