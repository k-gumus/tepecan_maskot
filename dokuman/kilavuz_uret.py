#!/usr/bin/env python3
"""Tepecan yapım kılavuzunu PDF olarak üretir."""

import os
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether,
                                ListFlowable, ListItem, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Preformatted, Spacer, Table,
                                TableStyle)
from PIL import Image as PILImage

FONTS = "/usr/local/lib/python3.11/dist-packages/matplotlib/mpl-data/fonts/ttf"
SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # depo kökü
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Tepecan_Yapim_Kilavuzu.pdf")

for name, fn in [("DejaVu", "DejaVuSans.ttf"), ("DejaVu-Bold", "DejaVuSans-Bold.ttf"),
                 ("DejaVu-It", "DejaVuSans-Oblique.ttf"),
                 ("Mono", "DejaVuSansMono.ttf"), ("Mono-Bold", "DejaVuSansMono-Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name, os.path.join(FONTS, fn)))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold",
                              italic="DejaVu-It", boldItalic="DejaVu-Bold")

INK = colors.HexColor("#16202c")
ACCENT = colors.HexColor("#1f5fa9")
MUTED = colors.HexColor("#5b6875")
RULE = colors.HexColor("#d3dae2")
CODEBG = colors.HexColor("#f4f6f9")

ss = getSampleStyleSheet()
S = {
    "h1": ParagraphStyle("h1", fontName="DejaVu-Bold", fontSize=17, leading=21,
                         textColor=ACCENT, spaceBefore=2, spaceAfter=9),
    "h2": ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=11.5, leading=15,
                         textColor=INK, spaceBefore=13, spaceAfter=5),
    "p": ParagraphStyle("p", fontName="DejaVu", fontSize=9.3, leading=13.6,
                        textColor=INK, spaceAfter=6, alignment=TA_LEFT),
    "note": ParagraphStyle("note", fontName="DejaVu", fontSize=8.6, leading=12.4,
                           textColor=MUTED, spaceAfter=6, leftIndent=8,
                           borderPadding=(0, 0, 0, 6)),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=7.1, leading=9.4,
                           textColor=INK, backColor=CODEBG, borderPadding=6,
                           spaceBefore=3, spaceAfter=8, leftIndent=1),
    "cell": ParagraphStyle("cell", fontName="DejaVu", fontSize=8.2, leading=11.4,
                           textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="DejaVu-Bold", fontSize=8.2, leading=11.4,
                            textColor=colors.white),
    "cellm": ParagraphStyle("cellm", fontName="Mono", fontSize=7.6, leading=11,
                            textColor=INK),
}

story = []


def h1(t):
    story.append(Paragraph(t, S["h1"]))


def h2(t):
    story.append(Paragraph(t, S["h2"]))


def p(t):
    story.append(Paragraph(t, S["p"]))


def note(t):
    story.append(Paragraph(t, S["note"]))


def code(t):
    story.append(Preformatted(t.strip("\n"), S["code"]))


def bullets(items):
    story.append(ListFlowable(
        [ListItem(Paragraph(i, S["p"]), leftIndent=12, value="circle") for i in items],
        bulletType="bullet", start="•", leftIndent=12, bulletFontName="DejaVu",
        bulletFontSize=8, spaceAfter=4))


def table(head, rows, widths, mono_cols=()):
    data = [[Paragraph(h, S["cellb"]) for h in head]]
    for r in rows:
        data.append([Paragraph(c, S["cellm"] if i in mono_cols else S["cell"])
                     for i, c in enumerate(r)])
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fb")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))


def picture(path, width=150 * mm, caption=None):
    """Depodaki bir görseli en-boy oranını koruyarak yerleştirir."""
    full = os.path.join(SRC, path)
    if not os.path.exists(full):
        return
    w, h = PILImage.open(full).size
    story.append(Image(full, width=width, height=width * h / float(w)))
    if caption:
        story.append(Paragraph(caption, ParagraphStyle(
            "cap", parent=S["note"], spaceBefore=3, leftIndent=0)))
    story.append(Spacer(1, 8))


def source(path):
    with open(os.path.join(SRC, path), encoding="utf-8") as f:
        code(f.read())


# ==========================================================================
# Kapak
# ==========================================================================
story.append(Spacer(1, 58 * mm))
story.append(Paragraph("TEPECAN", ParagraphStyle(
    "cover", fontName="DejaVu-Bold", fontSize=40, leading=46, textColor=ACCENT)))
story.append(Paragraph("Konuşan maskot — yapım kılavuzu", ParagraphStyle(
    "cover2", fontName="DejaVu", fontSize=15, leading=20, textColor=INK,
    spaceBefore=4)))
story.append(Spacer(1, 8))
story.append(Paragraph(
    "3D baskı gövde · ESP32-S3 · yerel yapay zekâ · Türkçe sesli sohbet",
    ParagraphStyle("cover3", fontName="DejaVu", fontSize=10, leading=15,
                   textColor=MUTED)))
story.append(Spacer(1, 20))
story.append(Table([[""]], colWidths=[150 * mm], rowHeights=[2],
                   style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACCENT)])))
story.append(Spacer(1, 10))
picture("govde/preview/tepecan_views.png", 150 * mm)
story.append(PageBreak())

# ==========================================================================
h1("1. Ne yapıyoruz")
p("Maskot dinler, sorulanı yapay zekâya iletir, cevabı içindeki hoparlörden "
  "Türkçe olarak söyler. Ağır iş maskotun içinde değil, ağdaki bir bilgisayarda "
  "çalışır. Maskotun içindeki kartın tek görevi mikrofonu okumak ve hoparlöre "
  "yazmak — bu sayede 512 MB RAM'li küçük bir kart yeter ve token maliyeti oluşmaz.")

code("""
   MASKOT (ESP32-S3)                       BEYİN SUNUCUSU (bir PC)
   ─────────────────────                   ────────────────────────
   butona basılır
   mikrofon kaydeder      ──── Wi-Fi ───▶  /stt    faster-whisper   (ses → metin)
                                           :11434  Ollama, qwen3:4b (cevabı üretir)
   hoparlör çalar         ◀─── Wi-Fi ────  /tts    Piper            (metin → ses)
""")

p("Cevap tamamlanmadan konuşmaya başlar: model ilk cümleyi bitirir bitirmez o "
  "cümle seslendirilir, kalanı arka planda üretilir. Algılanan gecikmeyi yarıya "
  "indiren tek değişiklik budur.")

h2("Verilen kararlar ve gerekçeleri")
table(
    ["Karar", "Neden"],
    [["Beyin ayrı bir PC'de",
      "Bu sınıf kartlarda 512 MB - 2 GB RAM var; en küçük dil modeli bile zor "
      "sığar, sığsa saniyede 1-3 token üretir. Bir cümle yarım dakika sürerdi."],
     ["Büyük kart alınmıyor",
      "85 × 56 mm bir kart maskotun içine girmiyor: kapak açıklığının köşegeni "
      "85.1 mm, o kartın köşegeni 85.8 mm. Kapalı PLA kasada da ısınıyor. "
      "Çözdüğü tek darboğaz zaten sunucuya taşındı."],
     ["Linux kartı yerine ESP32-S3",
      "Raspberry Pi de, muadil aarch64 kartlar da Türkiye'de bulunamadı; "
      "ESP32-S3 her yerde var ve üçte bir fiyatta. Kart zaten ince istemci "
      "olduğu için işletim sistemine ihtiyaç yok: SD kart, açılış süresi ve "
      "sürücü avı tamamen kalkıyor."],
     ["Ses I2S üzerinden",
      "ESP32-S3'ün dahili DAC'ı yok (klasik ESP32'de vardı, S3'te kaldırıldı), "
      "yani analog çıkış seçenek değil. MAX98357A hem DAC hem amfi olduğu için "
      "tek modülle çözülüyor."],
     ["Metin → ses de sunucuda",
      "Piper'ın Türkçe medium sesi Zero 2 W'de gerçek zamandan yavaş kalabiliyor. "
      "Sunucuda çalıştırınca bu risk tamamen kalkar, Pi'ye hazır ses gelir."],
     ["Model: Qwen3 4B",
      "Küçük modeller arasında çok dilli tarafı güçlü olanlardan; Türkçesi "
      "kullanılabilir. Gemma 3 4B ikinci aday, karşılaştırmaya değer."],
     ["Uyandırma kelimesi + buton",
      "\"Hey Tepecan\" ile butonsuz tetikleme (openWakeWord, yerel). Metin→ses "
      "sunucuya taşındığı için Pi'de yer açıldı. Buton yedek olarak duruyor: "
      "gürültülü stantta uyandırmayı kapatıp butona dönebilirsin."],
     ["Ollama + faster-whisper + Piper",
      "Üçü de ücretsiz ve yerel. Zincirin tamamı internetsiz çalışır, "
      "kullanım başına maliyet yoktur."]],
    [38 * mm, 118 * mm])

# ==========================================================================
story.append(PageBreak())
h1("2. Malzeme listesi")
p("Fiyatlar kabaca, sadece büyüklük fikri versin diye.")
table(
    ["#", "Parça", "Neden bu", "≈"],
    [["1", "ESP32-S3-DevKitC-1, N16R8",
      "Maskotun beyni değil, kulağı ve ağzı: mikrofonu dinler, beyin "
      "sunucusuna gönderir, gelen cevabı çalar. N16R8 varyantı şart — 8 MB "
      "PSRAM'de kayıt tamponu ve Piper'dan dönen WAV duruyor. 64 × 28 mm, "
      "montaj deliği yok (tepsiye kelepçeyle bağlanıyor).", "$8"],
     ["2", "INMP441 I2S mikrofon modülü",
      "Dijital çıkışlı, doğrudan karta bağlanıyor. L/R bacağı GND'ye gider, "
      "kod sol kanalı okuyor.", "$3"],
     ["3", "MAX98357A I2S amfi modülü",
      "Hem DAC hem 3 W sınıf-D amfi. ESP32-S3'ün dahili DAC'ı olmadığı için "
      "sesin analoğa çevrilmesi burada oluyor. VIN 5 V ister, 3V3 değil. "
      "Hoparlör çıkışı vidalı klemens — lehim gerekmiyor.", "$4"],
     ["4", "Ø30 mm 4-8 Ω hoparlör",
      "Gövdedeki yuva bu ölçüye göre: ızgara Ø30 mm, oturma omzu Ø32 mm, "
      "en fazla 8 mm gövde derinliği. Ø36 sığmıyor — göğüs küresel olduğu "
      "için o ayak izinde oturma omzu kartın önüne giriyor. 8 Ω olur, "
      "biraz daha kısık çalar.", "$3"],
     ["5", "5 V 2 A adaptör + USB-C kablo",
      "Telefon şarjı iş görür. Namlu uçlu adaptör ALMA — kart USB-C ile "
      "besleniyor.", "$5"],
     ["6", "6 × 6 × 4.3 mm tactile switch + ince kablo",
      "Sırt kapağındaki bas-konuş butonu. Uyandırma kelimesi varsayılan "
      "kapalı olduğu için şimdilik tek tetikleyici bu. Basılan kapağı "
      "(tepecan_buton.stl) sen basıyorsun.", "$1"],
     ["7", "M2.5 × 8 mm kendinden kılavuzlu vida (4 adet)",
      "Tepsiyi gövde kulelerine sabitlemek için. Kılavuz delikleri Ø2.1 mm "
      "hazır.", "$2"],
     ["8", "M3 × 8 kendinden kılavuzlu vida (2 adet)",
      "Sırt kapağını tutturmak için. Kasada yuvaları hazır.", "$1"],
     ["9", "Plastik kelepçe (2.5 mm, birkaç adet)",
      "Kartı, amfiyi ve mikrofonu tepsiye bağlamak için. Tepside 3.6 mm'lik "
      "yuvalar hazır — kartta vida deliği olmadığı için montaj böyle.", "$1"],
     ["10", "Havya + lehim teli",
      "Modüller lehimsiz geliyor. Toplam ~22 nokta: kartta tek header "
      "şeridi (bütün kullanılan pinler aynı kenarda), mikrofonda 6, "
      "amfide 5. Yarım saatlik iş.", "—"],
     ["11", "PLA filament, mavi (~400 g)",
      "Gövde. Güneşte/araçta kalacaksa PETG tercih et.", "$12"],
     ["—", "Beyin sunucusu: kulüpte zaten olan bir PC",
      "16 GB RAM yeterli. 8-12 GB VRAM'li bir ekran kartı varsa cevaplar "
      "üç kat hızlanır. Kurulum: yazilim/sunucu/kur.sh", "—"]],
    [8 * mm, 42 * mm, 92 * mm, 14 * mm])

note("Kart alırken N16R8 yazısına dikkat: PSRAM'siz ESP32-S3 varyantları da "
     "satılıyor ve onlarda ses tamponları sığmıyor. Klasik ESP32 (S3 değil) da "
     "çalışır ama uyandırma kelimesi için S3'ün yapay zekâ komutları lazım. "
     "Kartta iki USB-C portu var; yükleme birinde olmazsa diğerini dene.")

# ==========================================================================
story.append(PageBreak())
h1("3. Gövde: 3D baskı")
h2("Basılacak dosyalar")
table(
    ["Dosya", "Ne", "Adet"],
    [["tepecan_body.stl", "İçi boş gövde. Sırtta açıklık ve kapak oturma kenarı, "
      "iki vida boss'u, hoparlör adası, dört genel amaçlı kart kulesi, "
      "kablo yuvası.", "1"],
     ["tepecan_lid.stl", "Sırt kapağı. Havalandırma yarıkları ve havşalı vida "
      "delikleriyle, baskı pozisyonunda.", "1"],
     ["tepecan_buton.stl", "Kapaktaki butonun kapağı: Ø10 mm başlık, 5 mm sap. "
      "Yatık basılır, destek istemez.", "1"],
     ["tepecan_plaka.stl", "Kart tepsisi: altı gövde kulelerine oturur, "
      "kart üstüne kelepçeyle bağlanır. 72 × 36 × 3 mm, "
      "~20 dakika. Kart değişirse yalnız bu yeniden basılır.", "1"],
     ["tepecan_solid.stl", "İçi dolu vitrin figürü. Elektronik koymayacaksan "
      "bunu bas, diğerlerini atla.", "0-1"]],
    [34 * mm, 106 * mm, 16 * mm], mono_cols=(0,))

h2("Baskı ayarları")
table(
    ["Ayar", "Değer", "Not"],
    [["Malzeme", "PLA / PLA+", "PETG daha ısıya dayanıklı"],
     ["Katman", "0.20 mm", "Yüz için 0.16 daha temiz"],
     ["Duvar", "3 perimetre", ""],
     ["Dolgu", "%10-15 gövde, %20 kapak", ""],
     ["Destek", "Evet, ağaç/tree, her yerden", "Çene altı, kollar, eller, kulaklık "
      "diskleri, mikrofon kolu, antenler"],
     ["Brim", "5 mm", "Antenler için"],
     ["Yönlendirme", "Figür ayakta", "Taban zaten düzleştirilmiş"]],
    [26 * mm, 42 * mm, 88 * mm])

p("Ölçüler: 240 mm boy (anten uçları dahil), 138 mm en, 94 mm derinlik. "
  "<b>Z ekseni en az 250 mm olan bir yazıcı gerekiyor</b> — Ender 3, P1S, X1C uygun; "
  "A1, A1 mini, MK4 gibi 180-210 mm'lik yazıcılara sığmaz. Kabaca 300-400 g "
  "filament ve 30-45 saat. Daha kısa baskı için modeli <font face='Mono'>--height 180</font> "
  "ile yeniden üretebilirsin; cidar 3 mm ve vidalar M3 olarak kalır.")

h2("Gövdedeki elektronik detayları")
p("Bunların hepsi modelde hazır; ölçüler <font face='Mono'>govde/dogrula.py</font> "
  "ile her baskı öncesi ölçülüyor.")
bullets([
    "<b>Göğüs ızgarası</b> — Ø30 mm dairesel alan içinde 5 yatay yarık, 2.7 mm "
    "yükseklik, merkezi tabandan 65 mm'de. YEDİTEPE yazısına 3.2 mm pay var.",
    "<b>Hoparlör yuvası</b> — ızgaranın arkasında düz omuzlu bir ada: göğüs duvarı "
    "küresel olduğu için düz yüzlü bir hoparlör ona yaslanamıyor, ada sarkmayı "
    "dolduruyor. Cep Ø32 mm, omuz 2.4 mm. Ø40 mm hoparlör bu yüzden sığmıyor: "
    "o ayak izinde omuz y = 11.9 mm'ye kadar geriliyor ve kartın önüne giriyor.",
    "<b>Kart montaj kuleleri</b> — Ø6 mm, dört adet, <b>karttan bağımsız</b> "
    "44 × 28 mm aralıkta. Üst yüzeyleri tabandan 63.8 mm'de, tepelerinde M2.5 için "
    "Ø2.1 mm kılavuz delik, 8 mm derin. Kartın kendi delik deseni bu kulelerde "
    "değil, üstlerine vidalanan tepside.",
    "<b>Adaptör plakası</b> — 66 × 36 × 6 mm ayrı parça. Gövdeyi kart seçiminden "
    "kurtarıyor: kart değişirse 30-45 saatlik gövde değil, 20 dakikalık plaka "
    "yeniden basılıyor. ESP32-S3-DevKitC-1'de montaj deliği olmadığı için kart "
    "vidalanmıyor, kelepçeyle bağlanıyor; köşe yuvalarına da amfi ve mikrofon "
    "bağlanıyor.",
    "<b>Kapak açıklığı</b> — dıştan 73 × 62 mm, oturma kenarından geçiş 65 × 54 mm, "
    "köşegen 85 mm. Genişliği kart değil, kartı vidalayan tornavida belirledi: "
    "plakadaki vidalar x = ±29 mm'de ve açıklığın alt köşesine yakın; bu ölçüde "
    "kenara 3.7 mm kalıyor, tornavida rahat giriyor. Plaka açıklıktan yan "
    "yatırılarak geçiyor (köşegen 75 < 85 mm).",
    "<b>Vida boss'ları</b> — Ø18.7 mm, kavite yüzeyinden 12 mm içeri; M3 vidaya "
    "kapak eti ile birlikte 15 mm diş kalıyor.",
    "<b>Buton yuvası</b> — sırt kapağının iç yüzünde: 6.6 mm kare cep, 4.6 mm derin, "
    "önünde 2 mm sap kılavuzu, dışa Ø4.2 mm delik.",
    "<b>Kablo yuvası</b> — alt sırtta 15.6 × 7.8 mm, tabandan 38 mm'de; micro-USB "
    "fişi kıvrılmadan geçiyor.",
])

note("Işıklı gözler denenmedi: RGB LED'leri boyundan geçen bir ışık "
     "kanalıyla gözlere taşımak, gözleri şeffaf filamentten ayrı basmayı ve kafayı "
     "iki parça yapmayı gerektiriyor. Maskotu en canlı gösterecek şey bu, ama "
     "yapımı belirgin zorlaştırdığı için modele girmedi.")

picture("govde/preview/tepecan_hatch.png", 150 * mm,
        "Soldan: sırt açıklığı ve kapak oturma kenarı; bölmenin dıştan görünüşü; "
        "kapak, baskı pozisyonunda (dış yüz yukarı, destek gerekmez).")

# ==========================================================================
story.append(PageBreak())
h1("4. İç yerleşim ve montaj")
p("İç boşluk elipsoid olduğu için kutu ölçüsünden cömert: en geniş yerinde "
  "90 × 75 mm, toplam yükseklik 87 mm. Boşluk tabandan 34 mm'de başlıyor, "
  "121 mm'de bitiyor. Aşağıdaki yükseklikler tabandan ölçülü.")

code("""
        ÖN (yüz)                              ARKA (kapak)
   ┌──────────────────────────────────────────────────────┐
   │  ╔══════════╗                                        │
   │  ║ HOPARLÖR ║  Ø30 mm, öne bakar,                    │  z = 50-80 mm
   │  ║ + adası  ║  göğüs ızgarasından konuşur            │
   │  ╚══════════╝   ┌────────────────────────────────┐   │
   │                 │  ESP32-S3 (64 x 28 mm)         │   │  z = 67-85 mm
   │                 ├────────────────────────────────┤   │
   │                 │  ADAPTÖR PLAKASI               │   │  z = 64-70 mm
   │      4 kule ────┴────────────────────────────────┘   │
   │      z = 34-64 mm                                    │
   │                 MAX98357A ve INMP441: tepsinin       │
   │                 köşelerine kelepçeyle bağlanır       │
   │                                  vida bossu * z=59 mm│
   │   kablo yuvasi ------------------------------->      │  z = 38 mm
   └──────────────────────────────────────────────────────┘

   Kart, alt vida bossunun (z = 49.8-68.5 mm) tepesinin üstünde duruyor;
   bu yüzden arka sınırı boss değil kavite duvarı belirliyor. Sığan en
   büyük kart: 30 mm derinse 74.5 mm, 40 mm derinse 64.8 mm, 50-55 mm
   derinse 63.4 mm genişlik (derin kartlar plakada 7-10 mm geriye
   kaydırılıyor). Plakanın üstünde 40 mm yükseklik var. dogrula.py bu
   sayıları her baskı öncesi ölçüyor.
""")

picture("govde/preview/tepecan_ic.png", 150 * mm,
        "Solda gövdenin dikey kesiti: kart kuleleri ve hoparlör adası. "
        "Sağda kapak açıkken bölmenin içi.")

h2("Montaj sırası")
p("Gövde baskısı karta bağlı değil: plakayı kart gelmeden de basabilirsin, ama "
  "delik desenini kartın kendisinden kumpasla ölçüp üretmek en güvenlisi.")
bullets([
    "Gövdeyi ve kapağı bas, destekleri temizle. Kapağın açıklığa boşlukla "
    "oturduğunu kuru kuruya dene.",
    "Kart elindeyken montaj deliklerinin aralığını kumpasla ölç. "
    "<font face='Mono'>tepecan_model.py</font> içinde BOARD_HOLE_X / BOARD_HOLE_Y "
    "değerlerini gir (yarı ölçü: 58 × 23 mm delik için 58/2 ve 23/2), yeniden üret, "
    "<font face='Mono'>tepecan_plaka.stl</font>'i bas. Kart 35 mm'den derinse "
    "BOARD_OFFSET_Y ile geriye kaydır: 50 mm için -7, 55 mm için -10 mm.",
    "Hoparlörü göğüs ızgarasının arkasındaki adaya, düz omza yüzü öne bakacak "
    "şekilde otur ve kenarından yapıştır. <b>Arkasını olabildiğince kapalı tut</b> "
    "— omzun çevresini silikonla sızdırmaz yapmak ses kalitesini gözle görülür "
    "artırır, bedava kazançtır.",
    "İşlemcinin üstüne soğutucuyu yapıştır (kartı plakaya vidalamadan önce yap, "
    "sonra elin girmez).",
    "Kartı tepsiye kelepçeyle bağla (kartta vida deliği yok; tepside kartın "
    "altından geçen iki sıra yuva var). MAX98357A ve INMP441'i köşe yuvalarına "
    "bağla, kabloları kısa kes. Bu işi gövdenin dışında yap — tepsi avucunda "
    "dururken çok rahat.",
    "Hazır plakayı açıklıktan <b>yan yatırarak</b> içeri sok (düz geçmez, köşegen "
    "75 mm) ve dört M2.5 vidayla gövde kulelerine sabitle. Kartın güç girişi "
    "kablo yuvasına baksın.",
    "Hoparlörün iki telini MAX98357A'nın vidalı klemensine sıkıştır.",
    "Buton kapağını (tepecan_buton.stl) sırt kapağının <b>dışından</b> deliğe geçir. "
    "Switch'i kapağın iç yüzündeki cebe, pistonu kapağa bakacak şekilde bastır; sap "
    "tam pistona dayanır. İki telini kartın bir GPIO hattına ve GND'ye bağla. "
    "Telleri kapağı kapatırken sıkışmayacak kadar uzun bırak.",
    "Güç kablosunu alt sırttaki yuvadan geçir, karta tak.",
    "Kapağı iki M3 vidayla kapat. Vidalar havşalı deliklere oturur, başları yüzeyle "
    "aynı hizada kalır.",
])

h2("Kablolama")
table(
    ["Nereden", "Nereye", "Not"],
    [["INMP441 VDD / GND", "Kartın 3V3 ve GND pini", "L/R bacağı da GND'ye"],
     ["INMP441 SCK / WS / SD", "GPIO 4 / 5 / 6", "I2S giriş"],
     ["MAX98357A VIN / GND", "Kartın 5Vin ve GND pini", "5 V ister, 3V3 değil"],
     ["MAX98357A BCLK / LRC / DIN", "GPIO 15 / 16 / 17", "I2S çıkış"],
     ["MAX98357A çıkışı", "Hoparlör (+/−)", "Vidalı klemens, kutup önemsiz"],
     ["Buton bacak 1", "Bir GPIO hattı", "Kodda TEPECAN_BUTTON_PIN / "
      "TEPECAN_BUTTON_CHIP"],
     ["Buton bacak 2", "GND", ""],
     ["5 V adaptör", "Kartın güç girişi", "Varsa veri portuna değil, güç portuna"]],
    [34 * mm, 62 * mm, 60 * mm])

note("Kullanılan pinlerin hepsi kartın tek kenarında: 5Vin, GND, 18, 17, 16, "
     "15, 6, 5, 4, 3V3. Yani tek bir header şeridi lehimlemek yetiyor, diğer "
     "kenara hiç dokunma.")

picture("dokuman/devre_semasi.png", 150 * mm, "Bağlantı şeması.")

note("Isı: kapalı PLA kasada bu sınıf bir kart boşta 50-55 °C civarında kalır. Kapaktaki "
     "üç yarık ve kablo yuvası hafif hava akışı sağlıyor, soğutucuyla birlikte "
     "sorun çıkarmaz. PLA 60 °C dolayında yumuşamaya başlar; maskot güneşte veya "
     "araçta kalacaksa gövdeyi PETG bas.")

# ==========================================================================
story.append(PageBreak())
h1("5. Beyin sunucusu kurulumu")
p("Kulüpteki herhangi bir PC. Linux varsayılıyor; Windows'ta WSL2 içinde de çalışır.")

h2("Ollama ve model")
code("""
curl -fsSL https://ollama.com/install.sh | sh

ollama pull qwen3:4b          # ana aday
ollama pull gemma3:4b         # ikinci aday, karşılaştırmak için

# Ağdan erişilebilir olsun diye:
OLLAMA_HOST=0.0.0.0 ollama serve
""")

h2("Piper (Türkçe ses)")
code("""
mkdir -p ~/piper && cd ~/piper
# piper çalıştırılabilir dosyasını ve şu ikisini buraya indir:
#   tr_TR-dfki-medium.onnx
#   tr_TR-dfki-medium.onnx.json

echo "Merhaba, ben Tepecan." | ./piper --model tr_TR-dfki-medium.onnx --output_file test.wav
aplay test.wav                # sesi duyuyorsan Piper hazır
""")

h2("Ses servisi")
code("""
pip install -r requirements-sunucu.txt
uvicorn beyin:app --host 0.0.0.0 --port 8000

# GPU varsa belirgin daha doğru:
STT_DEVICE=cuda STT_MODEL=medium uvicorn beyin:app --host 0.0.0.0 --port 8000
""")

p("Sunucunun ağdaki adını <font face='Mono'>tepecan-beyin</font> yaparsan Pi tarafında "
  "hiçbir ayar değiştirmen gerekmez. Yapamıyorsan Pi'de "
  "<font face='Mono'>TEPECAN_BRAIN=http://192.168.1.42</font> gibi ver.")

note("Kontrol: başka bir makineden <font face='Mono'>curl http://tepecan-beyin.local:8000/health</font> "
     "komutu <font face='Mono'>{\"ok\": true, ...}</font> döndürmeli.")

# ==========================================================================
story.append(PageBreak())
h1("6. Maskot (Pi) kurulumu")
p("Raspberry Pi OS Lite, 64 bit. Kurulum sırasında Wi-Fi ve SSH'ı aç.")

h2("Firmware'i yükle")
p("ESP-IDF v5.1 veya üstü gerekiyor. En kolay yol VS Code + Espressif'in "
  "ESP-IDF eklentisi; eklenti toolchain'i kendisi kuruyor.")
code("""
cd yazilim/esp32
idf.py set-target esp32s3
idf.py build
idf.py -p COM3 flash monitor        # Linux'ta /dev/ttyACM0 gibi
""")

p("Seri monitörde <font face='Mono'>Tepecan başlıyor</font> ve ardından "
  "<font face='Mono'>kayıtlı ağ yok - kurulum noktası açılıyor</font> görmelisin.")

h2("Ağa bağla — bilgisayara gerek yok")
p("Wi-Fi bilgisi koda gömülü değil, NVS'e yazılıyor. Kart kayıtlı ağ bulamazsa "
  "kendi erişim noktasını açıyor:")
bullets([
    "Telefondan <b>Tepecan-Kurulum</b> ağına bağlan (şifresiz).",
    "Tarayıcıda <font face='Mono'>http://192.168.4.1</font> aç.",
    "Wi-Fi adı, şifresi ve beyin sunucusunun adresini gir "
    "(<font face='Mono'>http://sunucunun-IP-adresi:8000</font>).",
    "Kaydet — kart yeniden başlayıp o ağa bağlanıyor.",
])
p("Kulüpten etkinliğe geçerken ağ değiştirmek için de aynı portal yeter; USB "
  "yalnız ilk yüklemede lazım. Sonrasında prize takılı durduğu sürece çalışır.")

note("Uyandırma kelimesi varsayılan KAPALI geliyor: çalışması için ifadeye özel "
     "eğitilmiş bir microWakeWord modeli gerekiyor ve o model depoda yok. "
     "Şimdilik sırt kapağındaki buton tetikliyor. Açma yolu ve model eğitimi "
     "<font face='Mono'>yazilim/esp32/README.md</font> içinde.")

# ==========================================================================
story.append(PageBreak())
h1("7. Ayarlar")
p("Maskot tarafındakiler <font face='Mono'>yazilim/esp32/main/tepecan.h</font> "
  "içinde derleme sabitleri, sunucu tarafındakiler ortam değişkeni.")
table(
    ["Ayar", "Varsayılan", "Ne işe yarar"],
    [["PIN_MIC_SCK / WS / SD", "4 / 5 / 6", "Mikrofonun I2S pinleri"],
     ["PIN_SPK_BCLK / LRC / DIN", "15 / 16 / 17", "Amfinin I2S pinleri"],
     ["PIN_BUTON", "18", "Butonun bağlı olduğu GPIO"],
     ["SESSIZLIK_MS", "800", "Bu kadar sessizlikten sonra kayıt biter"],
     ["EN_UZUN_KAYIT_SN", "10", "Kayıt tavanı"],
     ["UYANDIRMA_ETKIN", "0", "1 yapınca uyandırma kelimesi derlenir"],
     ["WAKE_ESIK", "0.85", "Uyandırma güven eşiği (yükselt = az yanlış tetik)"],
     ["BEYIN_VARSAYILAN", "tepecan-beyin.local:8000", "Kurulum sayfasından değişir"],
     ["TEPECAN_MODEL", "qwen3:4b", "Sunucuda: Ollama modeli"],
     ["STT_MODEL", "small", "Sunucuda: whisper boyutu (small / medium)"],
     ["STT_DEVICE", "cpu", "Sunucuda: cpu veya cuda"],
     ["PIPER_MODEL", "~/piper/tr_TR-dfki-medium.onnx", "Sunucuda: Türkçe ses"]],
    [46 * mm, 42 * mm, 68 * mm], mono_cols=(0, 1))

note("Mikrofon sesi kısık ya da bozuk gelirse "
     "<font face='Mono'>yazilim/esp32/main/ses.c</font> içindeki kazanç "
     "kaydırmasına (<font face='Mono'>&gt;&gt; 11</font>) ve "
     "<font face='Mono'>MIC_KANAL_SOL</font> ayarına bak; donanımda "
     "denenmemiş iki nokta bunlar.")

h1("8. Küçük modelden iyi cevap almanın yolu")
p("Model 4 milyar parametreli. Ondan bilgiyi <i>bilmesini</i> değil, verdiğimiz "
  "metni <i>okumasını</i> istiyoruz. Kaliteyi belirleyen şey model değil, aşağıdakiler:")
bullets([
    "<b>bilgiler.txt dosyasını doldur.</b> Kulübe dair her gerçek buraya. Her "
    "soruda modele veriliyor. Doğru cevabı sağlayan asıl mekanizma bu — en yüksek "
    "getirili iş, modeli değiştirmek değil bu dosyayı yazmaktır.",
    "<b>2-3 cümle sınırını gevşetme.</b> persona.txt bunu dayatıyor. Küçük modeller "
    "uzadıkça dağılır, üstelik hoparlörden uzun cevap dinlemek sıkıcıdır.",
    "<b>Hafızayı artırma.</b> Altı mesaj tutuluyor, üç dakika sessizlikte sıfırlanıyor. "
    "Uzun geçmiş küçük modelde kaliteyi düşürür.",
    "<b>repeat_penalty 1.15</b> kendini tekrarlama döngüsünü kesiyor, "
    "<b>num_predict 160</b> cevabı kısa tutuyor.",
    "Qwen3 düşünme modunda &lt;think&gt; etiketi üretebiliyor; hem kapatılıyor hem de "
    "metinden temizleniyor. Yoksa hoparlör modelin iç monologunu okur.",
    "<b>Model seçimini ölçerek yap:</b> aynı on soruyu qwen3:4b ve gemma3:4b'ye sor, "
    "kulüpten birkaç kişiyle kör karşılaştır. Bir akşamlık iş, kararı bitirir.",
])

# ==========================================================================
story.append(PageBreak())
h1("9. Test ve sorun giderme")
table(
    ["Belirti", "Muhtemel sebep", "Ne yapmalı"],
    [["Hiç ses kaydedilmiyor",
      "Yanlış ses cihazı seçili",
      "arecord -l ve python3 -m sounddevice ile USB kartını bul, "
      "TEPECAN_MIC'e yaz"],
     ["Buton çalışmıyor",
      "gpiozero yalnız Raspberry Pi'de çalışır",
      "python-periphery kurulu mu bak; TEPECAN_BUTTON_CHIP ve "
      "TEPECAN_BUTTON_PIN'i kartının pin haritasına göre ayarla"],
     ["Kayıt hemen bitiyor",
      "VAD gürültüyü konuşma sanıyor ya da mikrofon sessiz",
      "alsamixer ile giriş seviyesini yükselt; kodda Vad(2) yerine Vad(1) dene"],
     ["Kayıt hiç bitmiyor",
      "Ortam gürültülü, sessizlik algılanmıyor",
      "Vad(3) yap; SILENCE_MS değerini 600'e düşür"],
     ["STT hatası / bağlanamıyor",
      "Sunucu adresi yanlış veya güvenlik duvarı",
      "karttan curl http://tepecan-beyin.local:8000/health dene"],
     ["Cevap geliyor ama ses yok",
      "Piper modeli sunucuda bulunamıyor",
      "Sunucu günlüğüne bak; PIPER_MODEL yolunu tam ver"],
     ["Ses cızırtılı, kesik",
      "Adaptör zayıf",
      "5 V 3 A adaptör kullan; powerbank'ten besleme"],
     ["Model saçmalıyor, konuyu kaçırıyor",
      "bilgiler.txt boş ya da çok uzun",
      "Doldur ama 1500 karakteri geçme"],
     ["Cevaplar çok yavaş",
      "Sunucuda GPU yok",
      "Daha küçük model (qwen3:1.7b) veya STT_MODEL=base dene"],
     ["Hoparlörden model düşüncesi okunuyor",
      "&lt;think&gt; etiketi sızmış",
      "Ollama sürümünü güncelle; think:false destekli olmalı"],
     ["Durmadan kendi kendine uyanıyor",
      "Uyandırma eşiği düşük, ortam gürültülü",
      "TEPECAN_WAKE_THRESHOLD=0.6, sonra TEPECAN_WAKE_HITS=3"],
     ["Uyandırma kelimesine hiç tepki vermiyor",
      "Eşik yüksek, mikrofon kısık ya da model yolu yanlış",
      "Açılıştaki \"Uyandırma kelimesi hazır\" satırını gör; eşiği 0.4 yap"]],
    [36 * mm, 46 * mm, 74 * mm])

h2("Beklenen gecikme")
table(
    ["Sunucu", "Soru sonundan ilk sese"],
    [["Ekran kartlı PC (8-12 GB VRAM)", "yaklaşık 2-3 saniye"],
     ["Ekran kartsız PC, qwen3:4b", "yaklaşık 5-7 saniye"],
     ["Ekran kartsız PC, qwen3:1.7b", "yaklaşık 3-4 saniye"]],
    [70 * mm, 60 * mm])

# ==========================================================================
story.append(PageBreak())
h1("10. Kodlar")
h2("yazilim/sunucu/beyin.py — beyin sunucusu (ses↔metin)")
source("yazilim/sunucu/beyin.py")

story.append(PageBreak())
h2("yazilim/esp32/main/tepecan.h — ayarlar ve pinler")
source("yazilim/esp32/main/tepecan.h")

story.append(PageBreak())
h2("yazilim/esp32/main/main.c — akış")
source("yazilim/esp32/main/main.c")

story.append(PageBreak())
h2("yazilim/esp32/main/ses.c — I2S mikrofon ve hoparlör")
source("yazilim/esp32/main/ses.c")

story.append(PageBreak())
h2("yazilim/esp32/main/ag.c — Wi-Fi ve beyin sunucusu istemcisi")
source("yazilim/esp32/main/ag.c")

story.append(PageBreak())
h2("yazilim/esp32/main/portal.c — ilk kurulum sayfası")
source("yazilim/esp32/main/portal.c")

story.append(PageBreak())
h2("yazilim/sunucu/persona.txt — kişilik")
source("yazilim/sunucu/persona.txt")

h2("yazilim/sunucu/bilgiler.txt — doldurulacak bilgi dosyası")
source("yazilim/sunucu/bilgiler.txt")

h2("yazilim/sunucu/requirements.txt")
source("yazilim/sunucu/requirements.txt")


# ==========================================================================
def decorate(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont("DejaVu", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(20 * mm, 12 * mm, "Tepecan — konuşan maskot yapım kılavuzu")
        canvas.drawRightString(190 * mm, 12 * mm, str(doc.page))
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        canvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canvas.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, title="Tepecan — Yapım Kılavuzu",
                      author="Tepecan", leftMargin=20 * mm, rightMargin=20 * mm,
                      topMargin=18 * mm, bottomMargin=20 * mm)
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=decorate)])
doc.build(story)
print("yazıldı:", OUT)
