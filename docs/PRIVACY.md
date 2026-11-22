# Gizlilik

EON'un amacı yerel çalışmak ve kullanıcıya veri üzerinde kontrol vermektir.

| Veri | v0.0.2 davranışı |
| --- | --- |
| Sohbet ve yanıtlar | Yalnız çalışan Python işleminde RAM'de; EON kalıcı kaydetmez |
| Model işlemi | `127.0.0.1:11434` Ollama yerel API |
| Kurulu model listesi | Ollama'dan yerel olarak sorgulanır |
| Uygulama yolları | Kullanıcının yerel `%LOCALAPPDATA%\EON\applications.json` ayar dosyası |
| API anahtarı | Gerekmez |
| Harici AI / telemetri | Kodda yok |

Model indirme ve yazılım kurulumu internet gerektirir. Windows'un ve Ollama'nın sistem düzeyindeki günlükleri, önbellekleri ve ağ davranışı ayrıca değerlendirilmelidir. Tam bilgisayar izolasyonu garanti edilmez.

GitHub'a gerçek kişilerin verileri, cihaz bilgileri, kullanıcı yolları, API anahtarları veya sohbet örnekleri yüklenmemelidir. Otomatik kontrol elle incelemenin yerini tutmaz.
