# "Hey Tepecan" — uyandırma kelimesi

Butona basmadan konuşabilmek için. Sistem **openWakeWord** kullanıyor: küçük
bir sinir ağı sürekli mikrofonu dinliyor, sadece kelimeyi duyunca kaydı
başlatıyor. Tamamen yerel, ücretsiz, internet gerektirmiyor.

Pi Zero 2 W'de rahat çalışıyor çünkü metin→ses işini sunucuya taşıdık; o RAM
boşta.

---

## 1. Önce zinciri hazır bir modelle dene

Kendi modelini eğitmeden önce sistemin çalıştığını gör. openWakeWord birkaç
hazır model ile geliyor ("alexa", "hey jarvis" gibi):

```bash
pip install openwakeword onnxruntime
python3 -c "import openwakeword; openwakeword.utils.download_models()"
```

İndirilen modellerden birinin yolunu vererek çalıştır:

```bash
TEPECAN_WAKE_MODEL=~/.local/share/openwakeword/hey_jarvis_v0.1.onnx python3 tepecan.py
```

"Hey Jarvis" deyince uyanıyorsa boru hattı sağlam; sıra kendi kelimende.

## 2. Kendi modelini eğit

openWakeWord'ün kendi deposunda, **otomatik eğitim not defteri** var. Elle ses
kaydetmene gerek yok: istediğin ifadeyi metin olarak veriyorsun, defter TTS ile
binlerce sentetik örnek üretip modeli eğitiyor. Colab'ın ücretsiz GPU'sunda
yaklaşık bir saat sürüyor ve sonunda bir `.onnx` dosyası veriyor.

Yaparken dikkat:

- İfadeyi **"hey tepecan"** gibi iki heceli-artı bir kalıpta tut. Tek heceli
  kelimeler ("Tepecan" tek başına) günlük konuşmada çok yanlış tetiklenir.
- Sentetik seslerin telaffuzu Türkçe değilse "tepejan / tepekan" gibi
  varyasyonları da eğitim ifadelerine ekle — model sesi öğreniyor, yazımı değil.
- Çıkan `.onnx` dosyasını Pi'de `~/tepecan/hey_tepecan.onnx` konumuna koy;
  varsayılan yol bu.

## 3. Ayarlar

| Değişken | Varsayılan | Ne işe yarar |
|---|---|---|
| `TEPECAN_WAKE_MODEL` | `~/tepecan/hey_tepecan.onnx` | Model yolu. Dosya yoksa program çalışır, sadece buton tetikler. |
| `TEPECAN_WAKE_THRESHOLD` | `0.5` | 0-1 arası güven eşiği. Yükselt = daha az yanlış tetikleme, daha çok kaçırma. |
| `TEPECAN_WAKE_HITS` | `2` | Kaç ardışık 80 ms bloğun eşiği aşması gerektiği. Gürültülü ortamda 3 yap. |

## 4. Gürültülü stantta ayar

Yanlış tetikleme kalabalıkta gerçek bir sorun. Sırayla dene:

1. `TEPECAN_WAKE_THRESHOLD=0.6`, sonra `0.7`
2. `TEPECAN_WAKE_HITS=3`
3. Hâlâ sorunluysa uyandırmayı kapat (`TEPECAN_WAKE_MODEL=` boş bırak) ve
   omuzdaki butonu kullan — buton her zaman çalışmaya devam ediyor.

Ters yönde, hiç uyanmıyorsa: eşiği `0.4`'e indir, mikrofon giriş seviyesini
`alsamixer` ile yükselt, ve modeli eğitirken kullandığın telaffuzla konuş.

## 5. Bilmen gerekenler

- **Kendi sesini duymaz.** Tepecan konuşurken mikrofon tamamen durduruluyor,
  konuşma bitince tampon boşaltılıyor. Kendi cevabıyla tekrar uyanmaz.
- **Buton hep açık.** Uyandırma kelimesi çalışsa da buton yedek olarak duruyor;
  ikisinden biri yeterli.
- **Sürekli dinliyor ama hiçbir şey kaydetmiyor.** Uyandırma kelimesi
  duyulmadan hiçbir ses diske yazılmıyor, ağa gönderilmiyor. Kelime duyulunca
  başlayan kayıt, sen susunca bitiyor ve sadece o parça sunucuya gidiyor.
