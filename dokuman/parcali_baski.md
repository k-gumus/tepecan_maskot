# Parçalı baskı — 5 parça, yapıştırmalı

Tek parça baskı neden dağıldı: kafa küresi gövdeye **Ø33 mm'lik bir boyunla**
oturuyor, yani kürenin alt yarısı (30 cm²) havada başlıyor ve altında gövde var,
tabla değil. Kaldırılmış elin parmakları da öyle. O yüzeyler desteksiz kalınca
kafa ve eller havaya basılmış oluyor, sonuç birbirinden kopuk parçalar.

Bölünce sorun kendiliğinden bitiyor: **her askıda yüzey artık baskı plakasının
üstüne geliyor** ve arası çok kısa — kafada 10-20 mm, bacaklarda 26 mm. Yani
boyanmış destek gerekmiyor, sıradan otomatik destek yetiyor.

## Parçalar

| parça | ölçü (mm) | filament | tabla teması | destek |
|---|---|---|---|---|
| `tepecan_kafa` | 114 × 90 × 114 | ~95 g | 540 mm² | gerekli |
| `tepecan_govde` | 92 × 77 × 98 | ~90 g | 2252 mm² | az |
| `tepecan_bacaklar` | 84 × 58 × 40 | ~38 g | 3375 mm² | az |
| `tepecan_kol_sag_arka` | 37 × 60 × 26 | ~9 g | 1091 mm² | **yok** |
| `tepecan_kol_sag_on` | 46 × 75 × 32 | ~10 g | 1100 mm² | **yok** |
| `tepecan_kol_sol_arka` | 34 × 86 × 23 | ~11 g | 1499 mm² | **yok** |
| `tepecan_kol_sol_on` | 39 × 100 × 28 | ~11 g | 1495 mm² | **yok** |
| `tepecan_lid` (arka kapak) | 72 × 59 × 30 | ~21 g | 89 mm² | yok, **8 mm kenar şart** |

### Kollar neden ikiye bölündü

Bütün hâlde bir kol tablaya **7 mm²** ile değiyordu. Yuvarlak bir uzuv nereye
yatırılırsa yatırılsın bir çizgi üstünde duruyor: parça tamamen desteğin
üstünde yüzüyor, alt yüzeyi de destek iziyle kaplanıyor.

Kol kendi düzleminden ikiye ayrılınca her yarım düz yüzüne yatıyor. Ölçülen
sonuç: tabla teması **1091-1499 mm²** (150-200 katı), askıda kalan yüzey
neredeyse sıfır. Malzemenin tamamı düz yüzden yukarı doğru büyüyor, parmaklar
dahil hiçbir şey havada başlamıyor — yani **bu dört parça desteksiz basılıyor.**

Kesim düzlemi elin açıldığı düzleme paralel geçiyor, yani parmakların arasından
değil etrafından dolaşıyor: parmaklar tek parça hâlinde ön yarımda kalıyor.

## Birleşme yerleri

- **Boyun** — gövdenin üstünde Ø19.4 mm, 12 mm boyunda bir geçme mili var;
  kafanın altındaki yuvaya 0.25 mm boşlukla giriyor. Kendi kendine ortalıyor.
- **Bacaklar** — her bacağın üstünde Ø15 mm, 10 mm boyunda birer pim; gövdenin
  altındaki yuvalara giriyor. İki pim olduğu için dönmüyor da.
- **Kollar** — düzlemle değil, **gövde küresinin yüzeyiyle** kesildi. Kesit eyer
  biçiminde: omuza tek bir şekilde oturuyor, pime gerek yok. Aralarında 0.25 mm
  yapıştırıcı payı bırakıldı.
- **Kol yarımları** — iki yarım birbirinin tam tamamlayıcısı, aralarında boşluk
  yok. Hizalama için pim koymadım: iki yarımın dış hattı birebir aynı, kenarları
  denkleştirince yerine oturuyor. Önce yarımları birleştir, kol kuruduktan sonra
  omuza yapıştır.

Yapıştırmadan önce hepsini kuru kuruya tak, oturuşu gör. Sonra jel kıvamında
siyanoakrilat (japon yapıştırıcısı) ya da iki bileşenli epoksi. İnce akıcı CA
bu boyuttaki yüzeylerde erken kuruyor.

Sıra: bacaklar → gövde, kollar → omuz, kafa en son.

## Plakalar

`govde/3mf/` altında:

| dosya | içinde | tahmini |
|---|---|---|
| `parca_plaka1_govde_bacaklar.3mf` | gövde + bacaklar | ~128 g · 9-12 sa |
| `parca_plaka2_kafa.3mf` | kafa | ~95 g · 7-9 sa |
| `parca_plaka3_kapak_kollar.3mf` | arka kapak + dört kol yarımı | ~62 g · 4-6 sa |

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

## Dilimleyicinin "boş katman" uyarısı

Kusurun kaynağı tek bir kalıp çıktı: **bir parçayı kavitenin tam yüzeyinde
bitirmek.** Kapak bileziği ve vida bossları böyle kuruluyordu, dolayısıyla dış
yüzleri gövdenin iç yüzüyle birebir çakışıyordu; boolean çakışan yüzeyde üst
üste binmiş kabuk bırakıyor, dilimleyici de kesiti kapatamıyordu. Ölçüldü:
bilezik eklenince bozuk katman 1'den 69'a fırlıyor, bosslar eklenince ağ
watertight olmaktan çıkıyordu. İkisi de artık duvarın 1.2 birim içine
gömülüyor -- `speaker_mount()` zaten bunu yapıyordu.

Denetimin eşiğini bulmak üç deneme aldı ve ilk ikisi yanlıştı. "Hiç kopuk
olmasın" ölçütü sorunsuz dilimlenen ağları da suçluyor: libslic3r serbest
uçları `slice_closing_radius` (0.049 mm) kadar mesafede dikiyor ve kapaktaki
kopuklar 1e-7 mm. Alan kaybı ölçütü ters yöne kaçıyor: 436 parçalık bir
konturdaki tek kıl kopuğu yüzünden tüm halkayı atıp katmanı %100 kayıp
sayıyor. Şimdiki ölçüt doğrudan boşluğun büyüklüğünü o 0.049 mm'ye karşı
ölçüyor ve küre, kutu, silindir, iç içe delikli halkada sıfır yanlış alarm
veriyor.

Tarama yarım katman adımıyla yapılıyor: parça plakaya yerleştirilince dilim
düzlemleri kayabiliyor ve tek fazda bir kusur örnekleme noktalarının arasına
düşmüştü. `plakalar.py` de her nesneyi dilimleneceği konumda denetliyor,
gerekirse orada temizliyor ve 3MF'i yazdıktan sonra dosyadan geri okuyup
doğruluyor.

### Önceki teşhis


İlk parça setinde Bambu şu uyarıyı veriyordu: *"X ile Y arasındaki boş katman
için nesne yazdırılamıyor"* — ve uyardığı nesneyi plakadan düşürüyordu, bir kol
hiç basılmadı.

Sebep ağdaydı. Parçaları gövdeyle **kesiştirerek** ayırmıştım; iki katının
yüzeyi omuzda birebir çakışınca boolean orada üst üste binmiş kabuklar
bırakıyor. Dilimleyici aynı yerde iki kontur görünce ikisi birbirini götürüyor
ve katman boşalıyor. Aynı şey boyun mili ile bacak pimlerinde de vardı: ikisi de
kesim düzlemine tam teğet başlıyordu.

Üç değişiklikle gitti:

- Gövde artık **baştan kolsuz** kuruluyor, kollar da kendi başına. İkisi
  arasında hiç boolean yok, omuz yüzeyi el değmemiş kalıyor.
- Mil ve pimler kesim düzlemine teğetlenmiyor, ana parçanın 4 birim **içine**
  gömülüyor.
- `parcala.py` her parçayı yazmadan önce baştan sona 0.2 mm'de dilimliyor ve
  her katmana tek bir duvarın sığdığını doğruluyor — dilimleyicinin yaptığı
  denetimin aynısı. Bir katman bile geçmezse dosya yazılmıyor.

Şu anki set 1634 katmanın hepsinden geçiyor.

## Yeniden üretmek

    cd govde && python3 parcala.py

Kesim yükseklikleri betiğin başında: `NECK_Z = 79.8`, `HIP_Z = 22.0`
(tasarım birimi). Dosyalar `govde/stl_parca/` altına yazılıyor ve her biri
yazılmadan önce watertight / tek parça / pozitif hacim diye denetleniyor.
