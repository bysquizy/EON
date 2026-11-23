# Güvenlik

EON v0.4.1 geliştirme önizlemesidir. Henüz tam güvenlik incelemesinden geçmiş bir ürün değildir.

**Şu anda:**
- Ollama yerel loopback adresiyle sınırlıdır. Açık onaylı Gemini sohbetleri sabit bir HTTPS sunucusuna gider. Anahtar tarayıcıya verilmez ve yönlendirmeler izlenmez.
- HTTP arayüzü yalnız `127.0.0.1` üzerine rastgele portla bağlanır; POST istekleri aynı-origin kontrolü ve rastgele oturum token'ı ister.
- Arayüzde dış font, CDN, analitik veya üçüncü taraf script bulunmaz. Sohbet mesajları HTML olarak yorumlanmaz.
- Sohbet ve hafıza Windows DPAPI ile şifrelenir. Şifreleme kullanılamıyorsa kayıt kapanır. Hava durumu, yalnız kullanıcı koordinatlarını girip izin verdikten ve güncelleme düğmesine bastıktan sonra Open-Meteo’ya bağlanır.
- Uygulama açma yalnız kullanıcı tarafından açılan **Uygulamalar** ekranındaki **Aç** düğmesiyle olur. Model metni veya keyfî bir terminal komutu uygulama açamaz.
- Windows'ta yalnız yerel tam yola sahip `.exe` ve `.lnk` dosyaları seçilebilir; bilinmeyen yollar çalıştırılmaz. Komut satırı argümanı veya `shell=True` kullanılmaz.

**Kısıtlar ve açık riskler:**
- Kullanıcının elle seçtiği `.exe` zararlı olabilir; `.lnk` kısayolları farklı hedefler başlatabilir. EON kısayolun argümansız yerel EXE hedefini çözer ve açılacak yolu gösterir. Dosya imzası doğrulanmaz.
- Yerel web portuna erişimi olan aynı makinedeki zararlı yazılımlar, tarayıcı eklentileri veya çalınan token risktir.
- Oturum mesajları işletim sistemi swap veya çökme kayıtlarında kalabilir; Ollama'nın kendi günlüklerinden EON sorumlu değildir.
- Bütün masaüstü eylemleri için tek kullanımlık onaylar ve imzalı yükleyici henüz yoktur.

**Geliştirme kuralı:** Her yeni riskli yetenek önce dar yetkiyle uygulanır; varsayılan kapalıdır ve reddetme testleri gerekir. Sırlar, kişisel yollar ve gerçek kullanıcı verileri GitHub'a eklenmez. [Depo politikası](docs/CONTENT_POLICY.md).

Başlatıcı sekmeye rastgele bir erişim sırrını URL parçasında iletir. Tarayıcı bu parçayı adres çubuğundan kaldırır ve sekme oturumunda tutar. Özel GET ve POST uçları erişim başlığını ister. POST istekleri ayrıca oturum CSRF değeri ve aynı origin gerektirir. Sağlık uç noktası yalnız sürüm ve sunucu durumunu verir. Başlatma bağlantısını paylaşma. Aynı Windows kullanıcısının tarayıcısını veya işlemlerini okuyabilen yazılım bu güven sınırının içindedir.

## Parola korumalı yedek

Tarayıcı Web Crypto üzerinden PBKDF2 SHA-256 (600.000 tur) ve AES-256-GCM kullanır. Her yedeğin tuzu ve nonce değeri ayrıdır. Parola yerel HTTP servisine iletilmez. Doğrulanan içerik, oturum başlığı ve CSRF denetimi ardından yerel sunucuda yeniden doğrulanır ve DPAPI kasasına atomik yazılır. Aynı Windows hesabının süreçleri veya tarayıcı eklentileri yerel güven sınırı içindedir. Yedek parolası unutulursa kurtarma anahtarı bulunmaz.
