# Changelog

EON `MAJOR.MINOR.PATCH` sürümleme kullanır. `0.x` geliştirme aşamasıdır; uyumluluk garantisi yoktur.

## [0.0.1] — 2026-11-20

### Eklendi
- Python CLI ve yerel Ollama sohbeti.
- Qwen3 4B Instruct ve 1.7B model seçimi.
- Türkçe EON kişiliği, geçici RAM hafızası.
- AST/Decimal tabanlı güvenli hesaplama.
- Loopback ve izinli Ollama API yollarıyla sınırlandırılmış istemci.
- **13 otomatik birim ve olumsuz senaryo testi.**
- Ayrıntılı README, vizyon, mimari, Windows kurulumu, güvenlik ve gizlilik belgeleri.
- GitHub Actions CI ve sürüm bazlı otomatik Release iş akışı.

### Bilinen sınırlamalar
- Gerçek Ollama sohbeti hedef Windows bilgisayarında doğrulanmadı.
- Kalıcı şifreli hafıza, ses, arayüz, agent araçları ve Windows kontrolü yok.
- EXE veya Windows yükleyici paketi üretilmiyor.

[0.0.1]: https://github.com/bysquizy/EON/releases/tag/v0.0.1
