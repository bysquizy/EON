# Sürüm yayınlama

Her yeni sürümde kod, README, CHANGELOG ve sürüm notları birlikte güncellenir. GitHub'a yalnız genel teknik bilgi eklenir.

1. Özellikleri yaz ve negatif senaryoları test et.
2. `python -m unittest discover -s tests -v` ve `python scripts/check_repo_privacy.py` çalıştır.
3. `VERSION` dosyasını yükselt; `docs/releases/vX.Y.Z.md` dosyasını oluştur.
4. README, değişiklik geçmişi, kurulum ve güvenlik belgelerini güncelle.
5. Kimlik, adres, cihaz ayrıntısı, özel dosya yolu veya kişisel veri kalmadığını **elle** incele.
6. `main` dalına commit gönder; GitHub Actions Windows/Linux testleri başarılı olursa yeni GitHub Release açar.
7. Yayını ve kaynak arşivini doğrula. Eski tag'ler kendiliğinden değişmez.

`0.x` sürümleri önizlemedir. Yayınlanan tag yeniden yazılmaz; düzeltme gerekiyorsa yeni sürüm çıkarılır.
