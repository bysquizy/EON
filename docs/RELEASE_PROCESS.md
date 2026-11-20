# EON — GitHub Release süreci

**Kural:** Her yeni EON sürümü, test edilmiş, açıklamalı ve ayrı bir **GitHub Release** olarak yayımlanır. Commit ile Release aynı şey değildir.

## Yeni sürüm kontrol listesi

1. Kod değişikliğini ve olumsuz durum testlerini tamamla.
2. `python -m unittest discover -s tests -v` çalıştır.
3. `VERSION` dosyasını yeni `X.Y.Z` değerine yükselt.
4. `CHANGELOG.md` ve README'yi güncelle.
5. `docs/releases/vX.Y.Z.md` dosyasına değişiklikleri, testleri, bilinen eksikleri ve kurulum notlarını yaz.
6. Değişiklikleri `main` dalına gönder.
7. GitHub Actions **CI & Releases** Windows ve Linux testlerini çalıştırır; başarılıysa bu sürüm için Release yoksa oluşturmayı dener.
8. [Releases](https://github.com/bysquizy/EON/releases) sayfasından tag, açıklama ve Source code (zip) bağlantısını doğrula.

## Yayın kuralları

- `VERSION`: yalnız `X.Y.Z`.
- Release etiketi: `vX.Y.Z`.
- `0.x` sürümleri **pre-release**.
- Aynı sürüm Release'i varsa yeniden oluşturulmaz.
- GitHub kaynak kodu ZIP/TAR arşivini otomatik sunar; EXE üretilmez.
- İş akışı: `.github/workflows/ci-release.yml`.
- Test başarısızsa yayın yapılmaz.
- GitHub Actions açık ve `GITHUB_TOKEN` için `contents: write` izni kullanılabilir olmalıdır; depo politikaları veya kota engel olabilir.
- Daha önce yayınlanan tag zorla taşınmaz; düzeltmeler yeni sürümde yapılır.

**Sürüm stratejisi:** `0.0.x` ilk prototipler, `0.x.y` gelişen ürün, `1.0.0` yalnız doğrulanmış ve kabul edilmiş temel ürün. Her dokümantasyon commit'i yeni sürüm değildir; **her yeni sürüm** ayrı Release gerektirir.

Otomasyon başarısız olursa Actions sekmesindeki iş akışı ve izin hatası incelenir; yayın gerçekleşmeden “Release hazır” denmez.
