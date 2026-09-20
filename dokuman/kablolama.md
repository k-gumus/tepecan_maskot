# Kablolama

Şema: `kablolama.png` (kaynağı `kablolama.py`).
Pin numaraları `yazilim/esp32/main/tepecan.h` ile birebir aynı — orayı
değiştirirsen bu dosyayı da değiştir.

## INMP441 — mikrofon

| mikrofon | ESP32-S3 |
|---|---|
| VDD | **3V3** |
| GND | GND |
| SCK | GPIO4 |
| WS | GPIO5 |
| SD | GPIO6 |
| **L/R** | **GND** |

L/R'yi GND'ye çekmek mikrofonu sol kanaldan konuşturuyor; `ses.c` de sol
yuvayı okuyor (`MIC_KANAL_SOL`). Boşta bırakırsan ses gelmez.

## MAX98357A — amfi

| amfi | ESP32-S3 |
|---|---|
| VIN | **5V** |
| GND | GND |
| BCLK | GPIO15 |
| LRC | GPIO16 |
| DIN | GPIO17 |
| SD, GAIN | bağlama, kartta geldiği gibi kalsın |

VIN'i 3V3'e bağlamak çalışır ama ses cılız çıkar. GAIN varsayılanda 9 dB;
sesi yetersiz bulursan GAIN'i GND'ye çekmeyi dene.

## Hoparlör

Amfinin klemensindeki **OUT+ → hoparlörün +**, **OUT− → hoparlörün −**.

Çıkış köprülü (BTL): iki ucu da sürülüyor. **Hoparlörün hiçbir ucunu GND'ye
bağlama**, amfiyi yakarsın. Tek hoparlörde +/− yönü sesi değiştirmez.

## Buton

Bir bacağı GPIO18, öteki bacağı GND. Kutbu yok, harici direnç de gerekmiyor:
`main.c` dahili pull-up açıyor ve basıldığında hattı GND'de görüyor.

## Güç

Kartta şarj devresi ve pil soketi yok.

**A) USB-C** — powerbank ya da adaptör doğrudan karta. Ek devre yok.

**B) 18650 + TP4056 + boost** — hücre → TP4056 `B+`/`B−`; TP4056 `OUT+`/`OUT−`
→ boost girişi; boost çıkışı → kartın **5V** ve **GND** pinlerine. Boost'u
bağlamadan önce trimpotla 5.00 V'a ayarla, en az 2 A verebilmeli (amfi ses
tepelerinde ~1 A çekiyor). **Pil bağlıyken USB'yi takma**, iki besleme çakışır.

### Pil gövdenin neresine giriyor

Ölçüldü (gövde, tepsi ve kart engel olarak alınarak; z tabanından itibaren):

| bölge | boşluk | ne sığar |
|---|---|---|
| tepsinin altı, z 33-61 | 28 mm yükseklik ama dört kule bölüyor | TP4056 (26×17×5) ve boost (36×17×5) |
| kartın üstü, z 79-116 (kubbe) | geniş | 18650 hücre (65×18), LiPo 50×34×10'a kadar |

Yani **pil kartın üstünde, kubbede; şarj ve boost modülleri tepsinin altında.**
Uzun bir hücre tepsinin altına girmiyor, dört kule araya giriyor.

Kubbedeki pili çift taraflı bant ya da kablo bağıyla sabitle — gevşek kalırsa
sallanır ve kartın üstüne düşer. İkisi de kapak açıklığından (73 × 60 mm)
rahat uzanıyor.

## Lehim sayısı

Kartta bir header şeridi, INMP441'de 6, MAX98357A'da 5 bacak. Hoparlör ve
güç vidalı klemens. Toplam ~22 nokta.
