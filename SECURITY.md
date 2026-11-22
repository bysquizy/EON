# Güvenlik

EON v0.0.2 geliştirme önizlemesidir. Henüz tam güvenlik incelemesinden geçmiş bir ürün değildir.

**Şu anda:**
- Yapay zekâ modeli yalnız yerel Ollama API'siyle (`127.0.0.1:11434`) konuşur. Uzak model API'si kullanılmaz.
- HTTP arayüzü yalnız `127.0.0.1` üzerine rastgele portla bağlanır; POST istekleri aynı-origin kontrolü ve rastgele oturum token'ı ister.
- Arayüzde dış font, CDN, analitik veya üçüncü taraf script bulunmaz. Sohbet mesajları HTML olarak yorumlanmaz.
- Sohbet metinleri EON tarafından diske kaydedilmez; yalnızca o oturumun RAM geçmişidir.
- Uygulama açma yalnız kullanıcı tarafından açılan **Uygulamalar** ekranındaki **Aç** düğmesiyle olur. Model metni veya keyfî bir terminal komutu uygulama açamaz.
- Windows'ta yalnız yerel tam yola sahip `.exe` ve `.lnk` dosyaları seçilebilir; bilinmeyen yollar çalıştırılmaz. Komut satırı argümanı veya `shell=True` kullanılmaz.

**Kısıtlar ve açık riskler:**
- Kullanıcının elle seçtiği `.exe` zararlı olabilir; `.lnk` kısayolları farklı hedefler başlatabilir. Dosya imzası veya kısayol hedefi doğrulaması henüz yoktur.
- Yerel web portuna erişimi olan aynı makinedeki zararlı yazılımlar, tarayıcı eklentileri veya çalınan token risktir.
- Oturum mesajları işletim sistemi swap veya çökme kayıtlarında kalabilir; Ollama'nın kendi günlüklerinden EON sorumlu değildir.
- Şifreli kalıcı hafıza, bütün masaüstü eylemleri için tek kullanımlık onaylar ve imzalı yükleyici henüz yoktur.

**Geliştirme kuralı:** Her yeni riskli yetenek önce dar yetkiyle uygulanır; varsayılan kapalıdır ve reddetme testleri gerekir. Sırlar, kişisel yollar ve gerçek kullanıcı verileri GitHub'a eklenmez. [Depo politikası](docs/CONTENT_POLICY.md).
