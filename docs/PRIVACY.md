# EON gizlilik bildirimi — v0.0.1

| Veri | Mevcut davranış |
| --- | --- |
| Sohbet | EON işlem belleğinde tutulur, EON tarafından kalıcı DB'ye yazılmaz |
| Model yanıtı | Yerel Ollama servisinden alınır |
| Matematik komutu | Yalnız Python işlemi içinde değerlendirilir |
| API anahtarı | Gerekmez |
| Kalıcı hafıza | Henüz mevcut değil |
| EON telemetrisi | Prototipte telemetri kodu yok |

**Sınır:** EON'un kendi veritabanına yazmaması, Windows swap/çökme dökümleri, terminal geçmişi veya Ollama günlüklerinde hiç iz kalmayacağını garanti etmez.

EON model istemcisi yalnız `127.0.0.1:11434` adresine bağlanır. Bulut AI API'si veya otomatik web araştırması yoktur. Model indirme ve yazılım kurulumu internet gerektirir. `OLLAMA_NO_CLOUD=1` Ollama bulut işlevlerini kapatmak için önerilir; tüm bilgisayarın ağdan yalıtıldığı iddia edilmez.

GitHub'a kişisel sohbetler, sırlar, token'lar veya gerçek hafıza veritabanları yüklenmemelidir. `.gitignore` tek başına kazara commit riskini ortadan kaldırmaz.

**Hedef:** SQLCipher ile yerel şifreleme, kullanıcı tarafından düzenlenebilir/silinebilir seçici hafıza, PUBLIC/PRIVATE/SECRET sınıflandırması ve denetlenebilir izinler. Bunlar henüz uygulanmadı.
