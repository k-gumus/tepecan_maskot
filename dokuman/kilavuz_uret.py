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
    "3D baskı gövde · Raspberry Pi Zero 2 W · yerel yapay zekâ · Türkçe sesli sohbet",
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
  "çalışır. Maskotun içindeki Pi'nin tek görevi mikrofonu okumak ve hoparlöre "
  "yazmak — bu sayede 512 MB RAM'li küçük bir kart yeter ve token maliyeti oluşmaz.")

code("""
   MASKOT (Pi Zero 2 W)                    BEYİN SUNUCUSU (bir PC)
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
      "Pi Zero 2 W'de 512 MB RAM var; en küçük dil modeli bile sığmaz, sığsa "
      "saniyede 1-3 token üretir. Bir cümle yarım dakika sürerdi."],
     ["Pi 4 alınmıyor",
      "85 × 56 mm kart maskotun içine pratikte girmiyor (kapak açıklığı 59 × 62 mm) "
      "ve kapalı PLA kasada ısınıyor. Çözdüğü tek darboğaz zaten sunucuya taşındı."],
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
    [["1", "Raspberry Pi Zero 2 W (header lehimli)",
      "Maskotun beyni değil, kulağı ve ağzı. 65 × 30 mm, kasaya sığan tek makul kart.", "$20"],
     ["2", "ReSpeaker 2-Mics Pi HAT (Seeed)",
      "Tek kartta 2 mikrofon + ses kodeki + 3 W amfi + buton + 3 RGB LED. "
      "Pi Zero ile birebir aynı ölçü. Modül sayısını dörtten bire indirir.", "$15"],
     ["3", "40 × 20 mm oval 4 Ω 3 W hoparlör",
      "Gövdedeki yuva bu ölçüye göre: ızgara 40 × 20 mm, oturma omzu 42 × 22 mm, "
      "en fazla 8 mm gövde derinliği. Yuvarlak 40 mm de sığar ama göğüs yazısını "
      "sıkıştırır.", "$3"],
     ["4", "microSD 32 GB, A1 sınıfı",
      "İşletim sistemi. A1 sınıfı olmayan kartlar Pi'yi belirgin yavaşlatır.", "$6"],
     ["5", "5 V 3 A adaptör + micro-USB kablo",
      "Pi + amfi tepe akımı ~800 mA. Zayıf adaptör ses bozulmasına yol açar.", "$8"],
     ["6", "14 × 14 mm alüminyum soğutucu",
      "Kapalı PLA kasada işlemci sıcaklığını düşürür.", "$1"],
     ["7", "M2.5 × 8 mm kendinden kılavuzlu vida (4 adet)",
      "Kartı basılı montaj kulelerine sabitlemek için. Kulelerde Ø2.1 mm "
      "kılavuz delik hazır, ara pula gerek yok.", "$3"],
     ["8", "6 × 6 × 4.3 mm tactile switch + ince kablo",
      "Sırt kapağındaki bas-konuş butonu. Uyandırma kelimesi çalışırken de "
      "yedek kalıyor. Basılan kapağı (tepecan_buton.stl) sen basıyorsun.", "$1"],
     ["9", "M3 × 8 kendinden kılavuzlu vida (2 adet)",
      "Sırt kapağını tutturmak için. Kasada yuvaları hazır.", "$1"],
     ["10", "PLA filament, mavi (~400 g)",
      "Gövde. Güneşte/araçta kalacaksa PETG tercih et.", "$12"],
     ["—", "Beyin sunucusu: kulüpte zaten olan bir PC",
      "16 GB RAM yeterli. 8-12 GB VRAM'li bir ekran kartı varsa cevaplar "
      "üç kat hızlanır.", "—"]],
    [8 * mm, 42 * mm, 92 * mm, 14 * mm])

note("HAT bulunamazsa yedek: INMP441 (I2S mikrofon) + MAX98357A (I2S amfi), ikisi ~$6. "
     "Daha ucuz ama iki I2S cihazını aynı hatta çalıştırmak device-tree ayarı ister ve "
     "butonu, LED'leri ayrıca eklemen gerekir. HAT'in kendi zorluğu da var: seeed-voicecard "
     "sürücüsü güncel Raspberry Pi OS'ta sorun çıkarabiliyor, bakımlı bir fork gerekebilir. "
     "Hangisini seçersen seç, bunu bilerek seç.")

# ==========================================================================
story.append(PageBreak())
h1("3. Gövde: 3D baskı")
h2("Basılacak dosyalar")
table(
    ["Dosya", "Ne", "Adet"],
    [["tepecan_body.stl", "İçi boş gövde. Sırtta açıklık ve kapak oturma kenarı, "
      "iki vida boss'u, hoparlör adası, dört kart kulesi, kablo yuvası.", "1"],
     ["tepecan_lid.stl", "Sırt kapağı. Havalandırma yarıkları ve havşalı vida "
      "delikleriyle, baskı pozisyonunda.", "1"],
     ["tepecan_buton.stl", "Kapaktaki butonun kapağı: Ø10 mm başlık, 5 mm sap. "
      "Yatık basılır, destek istemez.", "1"],
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
    "<b>Göğüs ızgarası</b> — 40 × 20 mm oval alan içinde 4 yatay yarık, 2.7 mm "
    "yükseklik. IEEE / YEDİTEPE yazısı üstte kalıyor.",
    "<b>Hoparlör yuvası</b> — ızgaranın arkasında düz omuzlu bir ada: göğüs duvarı "
    "küresel olduğu için düz yüzlü bir hoparlör ona yaslanamıyor, ada 6.4 mm'lik "
    "sarkmayı dolduruyor. Cep 42 × 22 mm, omuz 2.4 mm, yanal tutuş 4 mm.",
    "<b>Kart montaj kuleleri</b> — Ø6 mm, dört adet, Pi Zero 2 W delik düzenine göre "
    "58 × 23 mm. Üst yüzeyleri tabandan 61 mm'de, tepelerinde M2.5 için Ø2.1 mm "
    "kılavuz delik, 8 mm derin.",
    "<b>Kapak açıklığı</b> — dıştan 70 × 62 mm, oturma kenarından geçiş 61 × 53 mm. "
    "Kart 65 mm; köşegen 80 mm olduğu için hafif çapraz tutarak giriyor.",
    "<b>Vida boss'ları</b> — Ø18.7 mm, kavite yüzeyinden 12 mm içeri; M3 vidaya "
    "kapak eti ile birlikte 15 mm diş kalıyor.",
    "<b>Buton yuvası</b> — sırt kapağının iç yüzünde: 6.6 mm kare cep, 4.6 mm derin, "
    "önünde 2 mm sap kılavuzu, dışa Ø4.2 mm delik.",
    "<b>Kablo yuvası</b> — alt sırtta 15.6 × 7.8 mm, tabandan 38 mm'de; micro-USB "
    "fişi kıvrılmadan geçiyor.",
])

note("Işıklı gözler denenmedi: HAT'teki RGB LED'leri boyundan geçen bir ışık "
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
   │   ○        ○     mikrofon portları (HAT üzerinde)     │  z ≈ 100-115 mm
   │  ╔════════════╗                                      │
   │  ║  HOPARLÖR  ║  40 x 20 mm oval, öne bakar,          │  z = 57-77 mm
   │  ║  + adası   ║  göğüs ızgarasından konuşur           │
   │  ╚════════════╝            ┌───────────────────────┐  │
   │                            │  Pi Zero 2 W + HAT    │  │  z = 61-83 mm
   │        4 kule ─────────────│  yatay, kule üstünde  │  │
   │        z = 34-61 mm        └───────────────────────┘  │
   │                                  vida bossu ● z=59 mm │
   │   kablo yuvası ─────────────────────────────────▶     │  z = 38 mm
   └──────────────────────────────────────────────────────┘

   Kart y ekseninde hoparlör adasının 5 mm arkasında, alt vida bossunun
   9 mm önünde duruyor. Her yönde en az 1 mm boşluk ölçüldü.
""")

picture("govde/preview/tepecan_ic.png", 150 * mm,
        "Solda gövdenin dikey kesiti: kart kuleleri ve hoparlör adası. "
        "Sağda kapak açıkken bölmenin içi.")

h2("Montaj sırası")
bullets([
    "Gövdeyi ve kapağı bas, destekleri temizle. Kapağın açıklığa boşlukla "
    "oturduğunu kuru kuruya dene.",
    "Hoparlörü göğüs ızgarasının arkasındaki adaya, düz omza yüzü öne bakacak "
    "şekilde otur ve kenarından yapıştır. <b>Arkasını olabildiğince kapalı tut</b> "
    "— omzun çevresini silikonla sızdırmaz yapmak ses kalitesini gözle görülür "
    "artırır, bedava kazançtır.",
    "HAT'i Pi'nin üstüne otur, ikisini birlikte dört kuleye M2.5 vidalarla sabitle. "
    "Kart yatay durur, delikleri kulelerin Ø2.1 mm kılavuz deliklerine denk gelir. "
    "Micro-USB portları kablo yuvasına baksın, böylece güç kablosu kıvrılmadan çıkar.",
    "İşlemcinin üstüne soğutucuyu yapıştır (HAT'i takmadan önce yap, sonra elin girmez).",
    "Hoparlör kablosunu HAT'in JST hoparlör çıkışına tak.",
    "Buton kapağını (tepecan_buton.stl) sırt kapağının <b>dışından</b> deliğe geçir. "
    "Switch'i kapağın iç yüzündeki cebe, pistonu kapağa bakacak şekilde bastır; sap "
    "tam pistona dayanır. İki telini HAT'in GPIO17 ve GND pinlerine bağla. "
    "Telleri kapağı kapatırken sıkışmayacak kadar uzun bırak.",
    "Güç kablosunu alt sırttaki yuvadan geçir, Pi'ye tak.",
    "Kapağı iki M3 vidayla kapat. Vidalar havşalı deliklere oturur, başları yüzeyle "
    "aynı hizada kalır.",
])

h2("Kablolama")
table(
    ["Nereden", "Nereye", "Not"],
    [["Hoparlör (+/−)", "HAT üzerindeki JST hoparlör çıkışı", "Kutup önemli değil, "
      "tek hoparlör var"],
     ["Buton bacak 1", "GPIO17", "Kapaktaki switch; kodda TEPECAN_BUTTON_PIN"],
     ["Buton bacak 2", "GND", ""],
     ["5 V adaptör", "Pi'nin PWR IN micro-USB portu", "Veri portuna değil"],
     ["HAT", "Pi 40 pin header", "Doğrudan oturur, ara kablo yok"]],
    [34 * mm, 62 * mm, 60 * mm])

picture("dokuman/devre_semasi.png", 150 * mm, "Bağlantı şeması.")

note("Isı: kapalı PLA kasada Zero 2 W boşta 50-55 °C civarında kalır. Kapaktaki "
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

h2("Ses kartı sürücüsü")
code("""
sudo apt update && sudo apt install -y git python3-pip libportaudio2

# ReSpeaker 2-Mics Pi HAT sürücüsü (bakımlı fork):
git clone https://github.com/HinTak/seeed-voicecard
cd seeed-voicecard && sudo ./install.sh && sudo reboot

# Dönüşte kartın göründüğünü doğrula:
arecord -l          # seeed-2mic-voicecard listede olmalı
arecord -d 3 -f cd deneme.wav && aplay deneme.wav
""")

h2("Tepecan")
code("""
mkdir -p ~/tepecan && cd ~/tepecan
# tepecan.py, persona.txt, bilgiler.txt, requirements-pi.txt dosyalarını buraya koy

pip install --break-system-packages -r requirements-pi.txt
python3 tepecan.py
""")

p("\"Hey Tepecan\" de ya da sırt kapağındaki butona bas; kayıt sen susunca kendiliğinden "
  "biter. Terminalde durumu ve konuşulan metni görürsün. Uyandırma kelimesi "
  "modelini edinmek için <font face='Mono'>yazilim/maskot/UYANDIRMA.md</font> "
  "dosyasına bak — model dosyası yoksa program yine çalışır, sadece buton tetikler.")

h2("Açılışta otomatik başlasın")
p("<font face='Mono'>/etc/systemd/system/tepecan.service</font> dosyasını oluştur:")
code("""
[Unit]
Description=Tepecan sesli asistan
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/tepecan
Environment=TEPECAN_BRAIN=http://tepecan-beyin.local
ExecStart=/usr/bin/python3 /home/pi/tepecan/tepecan.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
""")
code("""
sudo systemctl enable --now tepecan
sudo journalctl -u tepecan -f        # canlı günlük
""")

# ==========================================================================
story.append(PageBreak())
h1("7. Ayarlar")
table(
    ["Değişken", "Varsayılan", "Ne işe yarar"],
    [["TEPECAN_BRAIN", "http://tepecan-beyin.local", "Beyin sunucusunun adresi"],
     ["TEPECAN_MODEL", "qwen3:4b", "Ollama'da kullanılacak model"],
     ["TEPECAN_LLM_BACKEND", "ollama", "ollama veya claude"],
     ["TEPECAN_BUTTON_PIN", "17", "Butonun bağlı olduğu GPIO"],
     ["TEPECAN_WAKE_MODEL", "~/tepecan/hey_tepecan.onnx", "Uyandırma modeli; yoksa sadece buton"],
     ["TEPECAN_WAKE_THRESHOLD", "0.5", "Uyandırma güven eşiği (yükselt = az yanlış tetikleme)"],
     ["TEPECAN_WAKE_HITS", "2", "Ardışık kaç blok eşiği aşmalı (gürültüde 3 yap)"],
     ["STT_MODEL", "small", "Sunucuda: whisper boyutu (small / medium)"],
     ["STT_DEVICE", "cpu", "Sunucuda: cpu veya cuda"],
     ["PIPER_MODEL", "~/piper/tr_TR-dfki-medium.onnx", "Sunucuda: Türkçe ses modeli"]],
    [42 * mm, 46 * mm, 68 * mm], mono_cols=(0, 1))

p("Stant gününde daha kaliteli cevap istersen tek satır:")
code("TEPECAN_LLM_BACKEND=claude ANTHROPIC_API_KEY=... python3 tepecan.py")
note("Claude arka ucu <font face='Mono'>claude-opus-5</font> kullanır, kişilik promptunu "
     "önbelleğe alır ve sohbet için düşük efor ayarıyla çalışır. Soru başına maliyet "
     "kabaca 0,25 TL. Bu yolu asıl arka uç yapacaksan sunucu taraflı yedek model "
     "(fallbacks) ayarını da eklemek gerekir; şu hâliyle eklenmedi.")

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
      "Ses kartı sürücüsü kurulmamış",
      "arecord -l çıktısında seeed-2mic-voicecard var mı bak"],
     ["Kayıt hemen bitiyor",
      "VAD gürültüyü konuşma sanıyor ya da mikrofon sessiz",
      "alsamixer ile giriş seviyesini yükselt; kodda Vad(2) yerine Vad(1) dene"],
     ["Kayıt hiç bitmiyor",
      "Ortam gürültülü, sessizlik algılanmıyor",
      "Vad(3) yap; SILENCE_MS değerini 600'e düşür"],
     ["STT hatası / bağlanamıyor",
      "Sunucu adresi yanlış veya güvenlik duvarı",
      "Pi'den curl http://tepecan-beyin.local:8000/health dene"],
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
h2("yazilim/maskot/tepecan.py — maskotun içindeki program")
source("yazilim/maskot/tepecan.py")

story.append(PageBreak())
h2("yazilim/maskot/persona.txt — kişilik")
source("yazilim/maskot/persona.txt")

h2("yazilim/maskot/UYANDIRMA.md — uyandırma kelimesi kurulumu")
source("yazilim/maskot/UYANDIRMA.md")

h2("yazilim/maskot/bilgiler.txt — doldurulacak bilgi dosyası")
source("yazilim/maskot/bilgiler.txt")

h2("yazilim/maskot/requirements.txt")
source("yazilim/maskot/requirements.txt")

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
