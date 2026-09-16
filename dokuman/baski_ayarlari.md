# Bambu Lab P1S — baskı ayarları

Ölçüler `govde/stl/` içindeki dosyalardan okundu, tasarım birimi değil **basılacak mm**.
Destek haritası: `dokuman/baski_destek_haritasi.png`
(kırmızı = destek şart, sarı = sınırda, mavi = kendini taşır).

## Hazır plakalar

`govde/3mf/` altında her plaka için tek bir 3MF var. Bambu Studio'ya sürükle-bırak
yeterli; parçalar 256 × 256'nın içine yerleştirilmiş, tablaya oturtulmuş ve gövde
yüzü kapıya bakacak şekilde döndürülmüş durumda (seam'i `Rear` yapınca dikiş sırta,
kapağın yanına düşüyor). Yerleşim kaymışsa "Auto arrange" bas.

| dosya | içindekiler |
|---|---|
| `plaka1_tepecan_govde.3mf` | gövde |
| `plaka2_kapak_plaka_buton.3mf` | kapak + kart plakası + buton |
| `plaka3_tepesu.3mf` | tepesu (pembe) |

Bunlar **yalnız geometri** taşıyor — içlerinde gömülü baskı profili ya da boyanmış
destek yok. Aşağıdaki ayarları elle gir; bir kere girip profili kaydedersen üç plakada
da kullanırsın.

## Plakalar

| plaka | parça | ayak izi | yükseklik | tahmini |
|---|---|---|---|---|
| 1 | `tepecan_body` | 133 × 90 mm | 230 mm | ~200-220 g · 18-24 sa |
| 2 | `tepecan_lid` + `tepecan_plaka` + `tepecan_buton` | en büyüğü 72 × 59 | 30 mm | ~35 g · 2-3 sa |
| 3 | `tepesu` (pembe) | 133 × 91 mm | 230 mm | ~200-230 g · 18-24 sa |

Gövdeyi tek başına bas. Küçük parçaları aynı plakaya koymak 1-2 saat kazandırır ama
kapağın brim'i kalkıp nozzle'a takılırsa 20 saatlik baskıyı da götürür. Acele yok, ayır.

256³ plakada üçü de rahat sığıyor; 230 mm boy Z limitinin 26 mm altında.

## Filament ve sıcaklık

PLA Basic. Nozzle 220 / 220, tabla 55 °C, textured PEI.

**P1S kapalı kabin — üst camı çıkar, ön kapağı aç.** 20 saatlik PLA baskısında kabin
45 °C'yi geçince extruder'ın üstünde filament yumuşuyor (heat creep) ve 14. saatte
tıkanma olarak karşına çıkıyor. P1S'te PLA hep açık kabinle basılır.

## Genel dilimleme

| ayar | değer | not |
|---|---|---|
| Nozzle / layer | 0.4 / 0.2 mm | 0.16 daha temiz yüz verir, +%25 süre |
| İlk katman | 0.2 mm | |
| Duvar sayısı | 3 | gövde eti zaten 3 mm, vida boss'ları için yeterli |
| Üst / alt katman | 4 / 4 | |
| Dolgu | %10 gyroid | maskot, yük taşımıyor |
| Seam position | Aligned | |
| Elephant foot comp. | 0.2 (varsayılan) | bot tabanları şişmesin |
| XY contour comp. | 0 | delik ölçüleri kaysın istemiyoruz |

Modeli Z'de 180° döndür, yüzü kapıya baksın: hem kameradan güzel görünür hem de
seam'i `Rear` yaparsan dikiş sırta, kapağın yanına düşer.

## İlk katman ve yapışma

| parça | ilk katman teması | brim |
|---|---|---|
| `tepecan_body` / `tepesu` | 3375 mm² (iki bot tabanı) | 5 mm, outer only, gap 0.1 |
| `tepecan_lid` | **89 mm²** | **8 mm — şart** |
| `tepecan_buton` | 78 mm² | 5 mm |
| `tepecan_plaka` | 2323 mm², düz | gerekmez |

Kapak 72 mm genişliğinde bir kubbe ama tablaya sadece ince bir bilezikle basıyor.
Brim'siz 10. katmanda kalkar.

Gövdenin tabanı geniş, yapışma derdi yok; brim yine de koy — 230 mm boyunda bir parça
kolundan darbe alırsa brim tutar.

Tablayı bulaşık deterjanı + sıcak suyla yıka, kurula. Sadece IPA parmak yağını almıyor.

## Destek — asıl mesele

### Destek gereken yerler

1. **Kafanın altı** — çene/boyun çevresindeki halkanın tamamı, ~19 cm². En büyük alan.
2. **Göbeğin altı** — bacakların üstündeki kuşak, z 22-34 mm, ~9 cm².
3. **Yan diskler** — kulaklık kabı ve lens yığınının altı (x ≈ ±47-49, z ≈ 146;
   lens kademeleri x ≈ -38, z ≈ 168-173).
4. **Omuz/kol** — açık kolun dirsek altı (x ≈ +57, z ≈ 71) ve yandaki elin parmakları
   (x ≈ -48, z ≈ 32).
5. **Mikrofon kolu** — yüzün önünde yatayda 31 mm uzanıp 10 mm alçalan Ø5 çubuk,
   yataya 18°. Desteksiz sarkar.

### Destek GİRMEMESİ gereken yerler

- **Gövdenin içindeki bölme.** Tavan z=110'da 46 × 33 mm, z=117'de kapanıyor — kubbe
  kendi kendini köprüleyerek kapanıyor, desteğe ihtiyacı yok. Oraya destek girerse
  hoparlör bileziğine ve kart kulelerine yapışır; 73 × 60 mm'lik kapak deliğinden
  pense ile sökmek eziyet, bilezik de kırılabilir.
- **Bölmedeki vida boss'u** (Ø18, duvardan 12 mm çıkıyor) — yatay silindir, biraz
  sarkar, vida tutmasına engel değil.
- **Göğüs ızgarası** — 5 kısa yarık, köprüyle geçer.
- **Kapağın içi** — aynı kubbe mantığı, desteksiz kapanır.
- **Anten topları** — Ø12.5 top Ø7.2 çubuğun üstünde, yanlardan 2.6 mm taşıyor.
  Desteksiz hafif sarkar, gözle fark edilmez.

### Nasıl

**Support type: `tree(manual)`** → destek yalnız boyadığın yere çıkar.
Support painting → Enforcer, fırça 5 mm, smart fill ile yukarıdaki 5 bölgeyi boya.

| destek ayarı | değer |
|---|---|
| Threshold angle | 30 (varsayılan) |
| Top Z distance | 0.2 mm |
| Support/object XY distance | 0.35 mm |

Boyamakla uğraşmak istemezsen `tree(auto)` + **everywhere**: bölmenin içine de destek
girer, kapaktan temizlemek 15-20 dakika sürer, hoparlör bileziğini kırmamaya dikkat et.
**"On build plate only" işaretleme** — o seçenek kafanın altındaki en büyük desteği de
iptal ediyor, çünkü orada zemin tabla değil gövde.

### Tepesu farkı

Tepesu içi dolu, bölme yok. Orada `tree(auto)` + everywhere'i gönül rahatlığıyla kullan.
Sağ elin önündeki kart klipsi 2.4 mm'lik dikey bir yarık, desteksiz basılıyor.

## Baskıdan sonra

- Kapak deliği Ø3.5 (M3 geçme), gövde boss'u Ø2.7 (M3 kendinden kılavuzlu).
  PLA'da delikler 0.1-0.3 mm dar çıkar; vida zorlarsa 3.5 mm matkapla bir geç.
- Kapak/gövde boşluğu tasarımda 0.3 mm. Kapak oturmazsa bileziği zımparala, ya da
  dilimleyicide yalnız kapağı %99.7 ölçekle.
- Buton sapı Ø4.2 deliğe 0.25 mm boşlukla giriyor; sıkıysa sapı hafif zımparala.
- Plakadaki kelepçe yuvası 10 × 3.6 mm — 2.5 mm kablo bağı geçer.
