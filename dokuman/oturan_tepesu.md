# Oturan Tepesu — baskı kılavuzu

Ayakta duran Tepecan'ın ikizi, oturur duruşta: bacaklar öne uzanmış, botlar
dikine, sol el yerde, sağ el kaldırılmış ve avucunun önünde QR kartı yuvası
var. Elektronik yok — kavite, hoparlör ızgarası ve arka kapak bu sürümde
hiç açılmıyor, figür dolu basılıyor.

Varsayılan boy **170 mm** (oturur yükseklik, anten uçlarına kadar).
Değiştirmek için:

    cd govde
    python3 oturan.py --height 200
    python3 plakalar_oturan.py

## Parçalar

| Dosya | Ölçü | Hacim | İlk katman |
|---|---|---|---|
| `tepesu_govde.stl` | 104 × 102 × 81 mm | 304 cm³ | 4097 mm² |
| `tepesu_kafa.stl` | 99 × 79 × 99 mm | 246 cm³ | 388 mm² |
| `tepesu_kol_sag_on.stl` | 60 × 69 × 18 mm | 14.5 cm³ | 1048 mm² |
| `tepesu_kol_sag_arka.stl` | 44 × 52 × 21 mm | 10.3 cm³ | 1041 mm² |

Gövde; kalça, bacaklar, botlar ve **sol kolu** tek parça içeriyor. Sol kol
ayrılmıyor çünkü eli zaten tablada başlıyor. Sağ kol kalkık olduğu için
dirseği boşlukta kalıyor; o yüzden gövdeden ayrı ve kendi düzleminden ikiye
bölünmüş basılıyor — her yarım düz yüzüne yatıyor, desteğe gerek kalmıyor.

Plakalar:

* `3mf/oturan_plaka1_govde_kafa.3mf`
* `3mf/oturan_plaka2_sag_kol.3mf`

## Tüylü yüzey (Fuzzy Skin)

Tüy dilimleyicide veriliyor, modelde değil: Bambu duvarın her noktasını kendi
normali boyunca rastgele kaydırıyor. Modele tüy işlemek milyonlarca üçgen
demek olurdu ve hiçbir dilimleyici altından kalkamazdı.

Bambu Studio'da: sağdaki **Süreç (Process)** panelinde parametre kipini
**Gelişmiş (Advanced)** yap — basit kipte bu bölüm görünmüyor. Sonra
**Kalite (Quality)** sayfasının altındaki *Fuzzy Skin* grubunda:

| Ayar | Değer | Neden |
|---|---|---|
| Fuzzy Skin | **Contour** (dış kontur) | Görünen bütün yüzey tüylenir. *All walls* iç duvarları da tüylendirir: baskı uzar, dışarıdan hiçbir farkı görünmez. **Bunu *Contour and hole* yapma** — nedeni aşağıda. |
| Fuzzy skin thickness | **0.4 mm** | 0.3 varsayılanı 170 mm'lik bir figürde zar zor fark ediliyor. 0.4 pelüş dokusu veriyor. 0.5'in üstünde duvar bütünlüğü bozuluyor. |
| Fuzzy skin point distance | **0.6 mm** | Küçük değer = sık ve ince doku. 0.8 varsayılanı bu boyda iri taneli duruyor. |
| Fuzzy skin first layer | **kapalı** | İlk katman tüylenirse tabla tutuşu düşer. (Eski sürümlerde bu seçenek yok, sorun değil.) |

Bilinmesi gerekenler:

* Tüy yalnız **duvarlara** vuruluyor. Yataya yakın yüzeyler — kafanın
  tepesi, omuzların ve botların üstü — düz kalıyor. Bu Bambu'nun
  kısıtlaması, modelin değil.
* Göğsündeki **IEEE / YEDİTEPE** yazısı yüzeyden 3 mm kabarık; 0.4 mm'lik
  tüyün altında okunaklı kalıyor. Yüz hatları, kulaklık ve oluklar da öyle.
* **Geçme payı bu yüzden büyütüldü.** Gövdenin tepesindeki boyun mili bir
  dış kontur, yani tüy onu 0.4 mm'ye kadar şişiriyor. 0.25 mm'lik nominal
  pay bunu karşılamıyor, kafa boyna hiç girmiyor. Oturan sürümde pay
  yarıçapta **0.55 mm**, kolun omuz yüzeyinden kaçışı da 0.55 mm.
* Bu pay **yalnız milin şişmesine** göre hesaplandı. *Contour and hole*
  seçersen kafadaki yuva da tüylenip daralır, iki taraf birden yer ve pay
  yine yetmez. Modu **Contour** bırak.
* Bu STL'leri **tüysüz basarsan geçmeler biraz bol durur** — yapıştırıcı
  boşluğu dolduruyor, sorun değil, ama bilerek olsun.

## Baskı ayarları

| Ayar | Değer |
|---|---|
| Nozzle / katman | 0.4 mm / 0.20 mm |
| Duvar sayısı | 3 |
| Dolgu | %10 gyroid |
| İlk katman yüksekliği | 0.2 mm |
| Kenarlık (Brim) | **Kafa için açık, 5 mm.** Gövde ve kollar için gerekmiyor. |
| Destek | **Kafa ve `kol_sag_on`.** Ağaç (Otomatik) + *Yalnızca baskı plakasında*. Gövde ve `kol_sag_arka` desteksiz. |

Gövde desteksiz basılıyor: popo, iki baldırın altı ve iki bot tabanı aynı
düzlemde tablaya oturuyor (2101 mm² ilk katman) ve gövdenin kalçadan
taşan en dik yeri bile düşeyden 30°. Kol yarımları düz yüzlerine yatıyor.

Kafa boyun kesitiyle, yani Ø28 mm'lik bir bilezikle duruyor ve üstünde
99 mm yükseliyor: destek burada hem askıdaki kubbeyi taşıyor hem parçayı
ayakta tutuyor. Kenarlığı atlama.

`kol_sag_on` yarımında kart mandalı parçanın tepesinde havada başlıyor:
17.5 mm'lik parçanın üst 3.4 mm'sinde, toplam 184 mm²'lik iki ada. Ona ağaç
destek gerekiyor - parça 14.5 cm³, destek birkaç dakika sürüyor.
`kol_sag_arka` yarımında havada başlayan ada 0.0 mm², o desteksiz.

## Birleştirme

1. **Kafa ↔ gövde:** gövdenin tepesindeki mil kafanın altındaki yuvaya
   giriyor. Kuru dene, sonra milin yan yüzüne yapıştırıcı sür ve otur.
2. **Sağ kolun iki yarımı:** düz kesik yüzlerinden birbirine. Kesik yüzler
   tablaya bakan yüzler olduğu için tüylü değil, tam oturuyorlar.
3. **Sağ kol ↔ gövde:** kolun omuz tarafındaki eyer biçimli yüzey omza tek
   bir şekilde oturuyor, pime gerek yok. Kartı yuvaya kol takılıyken sok.

Yapıştırıcı: PLA için jel siyanoakrilat ya da iki bileşenli epoksi.
