# Parçalı baskı — 5 parça, yapıştırmalı

Tek parça baskı neden dağıldı: kafa küresi gövdeye **Ø33 mm'lik bir boyunla**
oturuyor, yani kürenin alt yarısı (30 cm²) havada başlıyor ve altında gövde var,
tabla değil. Kaldırılmış elin parmakları da öyle. O yüzeyler desteksiz kalınca
kafa ve eller havaya basılmış oluyor, sonuç birbirinden kopuk parçalar.

Bölünce sorun kendiliğinden bitiyor: **her askıda yüzey artık baskı plakasının
üstüne geliyor** ve arası çok kısa — kafada 10-20 mm, bacaklarda 26 mm. Yani
boyanmış destek gerekmiyor, sıradan otomatik destek yetiyor.

## Parçalar

| parça | ölçü (mm) | filament | tabla teması |
|---|---|---|---|
| `tepecan_kafa` | 114 × 90 × 114 | ~95 g | 540 mm² (boyun bileziği) |
| `tepecan_govde` | 92 × 77 × 98 | ~90 g | 2252 mm² (düz kalça kesiti) |
| `tepecan_bacaklar` | 84 × 58 × 40 | ~38 g | 3375 mm² (iki bot tabanı) |
| `tepecan_kol_sol` | 105 × 60 × 33 | ~18 g | destek taşıyor |
| `tepecan_kol_sag` | 81 × 59 × 42 | ~16 g | destek taşıyor |

Toplam ~257 g, desteklerle ~300 g. Tek makara fazlasıyla yeter.

## Birleşme yerleri

- **Boyun** — gövdenin üstünde Ø19.4 mm, 12 mm boyunda bir geçme mili var;
  kafanın altındaki yuvaya 0.25 mm boşlukla giriyor. Kendi kendine ortalıyor.
- **Bacaklar** — her bacağın üstünde Ø15 mm, 10 mm boyunda birer pim; gövdenin
  altındaki yuvalara giriyor. İki pim olduğu için dönmüyor da.
- **Kollar** — düzlemle değil, **gövde küresinin yüzeyiyle** kesildi. Kesit eyer
  biçiminde: omuza tek bir şekilde oturuyor, pime gerek yok. Aralarında 0.25 mm
  yapıştırıcı payı bırakıldı.

Yapıştırmadan önce hepsini kuru kuruya tak, oturuşu gör. Sonra jel kıvamında
siyanoakrilat (japon yapıştırıcısı) ya da iki bileşenli epoksi. İnce akıcı CA
bu boyuttaki yüzeylerde erken kuruyor.

Sıra: bacaklar → gövde, kollar → omuz, kafa en son.

## Plakalar

`govde/3mf/` altında:

| dosya | içinde | tahmini |
|---|---|---|
| `parca_plaka1_govde_bacak_kollar.3mf` | gövde, bacaklar, iki kol | ~162 g · 12-16 sa |
| `parca_plaka2_kafa.3mf` | kafa | ~95 g · 7-9 sa |

Riskli olan tek parça kafa, o yüzden kendi plakasında. Diğer dördü düşük riskli,
birlikte basılıyor; biri bozulursa yalnız onu tekrar basarsın.

## Ayarlar

`baski_ayarlari.md`'deki kalite/mukavemet/filament ayarları aynen geçerli.
Değişen tek şey destek — ve bu sefer **hiçbir şey boyamıyorsun**:

| ayar | değer |
|---|---|
| Desteği etkinleştir | ✓ |
| Tür | **ağaç(Otomatik)** — Manuel değil |
| **Yalnızca baskı plakasında** | **✓ işaretle** |
| Destek açısı | 30 |
| Üst Z mesafesi | 0.2 |
| Destek/nesne XY mesafesi | 0.35 |

"Yalnızca baskı plakasında" artık işaretleniyor, çünkü askıda kalan her yüzeyin
altında tabla var. Bu aynı zamanda gövdenin içindeki bölmeyi de koruyor: oraya
destek girmiyor, tavan zaten kendi kendini köprüleyerek kapanıyor.

Kenar (brim): **kafaya 8 mm**, kollara 8 mm, gövdeye 5 mm, bacaklara gerek yok.
Kafa Ø33'lük bir bilezikle duruyor, kollar zaten desteğin üstünde yüzüyor.

## Kafaya fuzzy

Bulanık kaplamayı **boyama modunda** kullan (`Bulanık kaplama → Yok (boyama)`
seçeneğinin yanındaki boyama aracı) ve yalnız kafanın arkasını ve tepesini boya.
Tüm yüzeye uygularsan gözler, kaş ve gülümseme de dokulanıp kayboluyor — yüzü
temiz bırak.

Nokta mesafesi 0.8, kalınlık **0.4** (varsayılan 0.3 biraz siliktir).

Yan etki olarak işine yarayacak: çenenin altındaki destek izlerini fuzzy doku
gizliyor.

## Yeniden üretmek

    cd govde && python3 parcala.py

Kesim yükseklikleri betiğin başında: `NECK_Z = 79.8`, `HIP_Z = 22.0`
(tasarım birimi). Dosyalar `govde/stl_parca/` altına yazılıyor ve her biri
yazılmadan önce watertight / tek parça / pozitif hacim diye denetleniyor.
