#!/usr/bin/env python3
"""Tepecan pin seviyesinde kablolama şeması -> PNG + SVG.

devre.py blok şemasını çiziyor: hangi modül hangisine bağlı. Bu dosya ise
her teli tek tek gösteriyor -- hangi bacak hangi pine, artı nereye, eksi
nereye. Pin numaraları yazilim/esp32/main/tepecan.h ile birebir aynı.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle

INK, MUT = "#16202c", "#5b6875"
GUC, TOPRAK, SINYAL = "#c62828", "#263238", "#1565c0"
BG, CARD, KENAR = "#ffffff", "#f5f7fa", "#8fa3b8"

fig, ax = plt.subplots(figsize=(13.2, 9.6), facecolor=BG)
ax.set_xlim(0, 132); ax.set_ylim(0, 96); ax.axis("off")


def kutu(x, y, w, h, baslik, alt=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1.0",
                                fc=CARD, ec=KENAR, lw=1.5, zorder=2))
    ax.text(x + w / 2, y + h - 2.6, baslik, ha="center", va="top",
            fontsize=10.5, fontweight="bold", color=INK, zorder=3)
    if alt:
        ax.text(x + w / 2, y + h - 6.4, alt, ha="center", va="top",
                fontsize=7.8, color=MUT, zorder=3)


def pin(x, y, ad, sag=True, renk=SINYAL):
    ax.add_patch(Circle((x, y), 0.7, fc=renk, ec="none", zorder=4))
    ax.text(x + (1.8 if sag else -1.8), y, ad, ha="left" if sag else "right",
            va="center", fontsize=8.4, color=INK, zorder=4)


def tel(p0, p1, renk, etiket=None, ara=None):
    """Düz ya da tek kırılımlı tel. `ara` verilirse oradan dirsek yapar."""
    noktalar = [p0] + ([ (ara, p0[1]), (ara, p1[1]) ] if ara is not None else []) + [p1]
    for a, b in zip(noktalar, noktalar[1:]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=renk, lw=2.0, zorder=1,
                solid_capstyle="round")
    if etiket:
        mx = (p0[0] + p1[0]) / 2 if ara is None else ara
        ax.text(mx, max(p0[1], p1[1]) + 1.2, etiket, ha="center", va="bottom",
                fontsize=7.6, color=renk, zorder=5,
                bbox=dict(fc=BG, ec="none", pad=0.8))


ax.text(3, 92.5, "Tepecan — kablolama", fontsize=16, fontweight="bold", color=INK)
ax.text(3, 88.6, "Pin numaraları yazilim/esp32/main/tepecan.h ile aynı.  "
                 "Kırmızı = besleme, siyah = toprak, mavi = sinyal.",
        fontsize=8.6, color=MUT)

# ------------------------------------------------------------------ kart
KX, KW = 44, 26
kutu(KX, 18, KW, 62, "ESP32-S3-DevKitC-1", "N16R8 · 64 × 28 mm")
ax.text(KX + KW / 2, 74.5, "USB-C ile beslenir ve programlanır",
        ha="center", fontsize=7.4, color=MUT, zorder=3)

kart_pin = {"3V3": (70.0, "GUC"), "GND1": (67.0, "TOPRAK"), "4": (64.0, "SINYAL"),
            "5": (61.0, "SINYAL"), "6": (58.0, "SINYAL"),
            "5V": (46.0, "GUC"), "GND2": (43.0, "TOPRAK"), "15": (40.0, "SINYAL"),
            "16": (37.0, "SINYAL"), "17": (34.0, "SINYAL"),
            "18": (25.0, "SINYAL"), "GND3": (22.0, "TOPRAK")}
renkler = {"GUC": GUC, "TOPRAK": TOPRAK, "SINYAL": SINYAL}
for ad, (y, tip) in kart_pin.items():
    pin(KX + KW, y, ad.rstrip("123") if ad.startswith("GND") else ad,
        sag=False, renk=renkler[tip])

# --------------------------------------------------------------- INMP441
MX = 92
kutu(MX, 52, 36, 26, "INMP441", "I2S mikrofon · göğüs ızgarasının arkasında")
mic = [("VDD", 70, GUC), ("GND", 67, TOPRAK), ("SCK", 64, SINYAL),
       ("WS", 61, SINYAL), ("SD", 58, SINYAL), ("L/R", 55, TOPRAK)]
for ad, y, r in mic:
    pin(MX, y, ad, sag=True, renk=r)

tel((KX + KW, 70), (MX, 70), GUC, "3V3")
tel((KX + KW, 67), (MX, 67), TOPRAK)
tel((KX + KW, 64), (MX, 64), SINYAL, "GPIO4 → SCK")
tel((KX + KW, 61), (MX, 61), SINYAL, "GPIO5 → WS")
tel((KX + KW, 58), (MX, 58), SINYAL, "GPIO6 ← SD")
tel((MX, 55), (MX - 5, 55), TOPRAK)
tel((MX - 5, 55), (MX - 5, 67), TOPRAK)
ax.text(MX - 6.2, 53.6, "L/R → GND\n(sol kanal)", ha="right", va="bottom",
        fontsize=7.4, color=TOPRAK)

# ------------------------------------------------------------ MAX98357A
kutu(MX, 28, 36, 22, "MAX98357A", "I2S amfi + DAC")
amp = [("VIN", 46, GUC), ("GND", 43, TOPRAK), ("BCLK", 40, SINYAL),
       ("LRC", 37, SINYAL), ("DIN", 34, SINYAL)]
for ad, y, r in amp:
    pin(MX, y, ad, sag=True, renk=r)
tel((KX + KW, 46), (MX, 46), GUC, "5V  (3V3 değil)")
tel((KX + KW, 43), (MX, 43), TOPRAK)
tel((KX + KW, 40), (MX, 40), SINYAL, "GPIO15 → BCLK")
tel((KX + KW, 37), (MX, 37), SINYAL, "GPIO16 → LRC")
tel((KX + KW, 34), (MX, 34), SINYAL, "GPIO17 → DIN")
ax.text(MX + 36, 31.5, "SD ve GAIN: kartta geldiği gibi bırak", ha="right",
        va="center", fontsize=7.4, color=MUT)

# --------------------------------------------------------------- hoparlör
kutu(MX, 4, 36, 17, "Hoparlör", "Ø30 mm · 4-8 Ω · vidalı klemens")
pin(MX + 8, 9.5, "", renk=INK)
ax.text(MX + 8, 6.4, "+", ha="center", fontsize=12, fontweight="bold", color=INK)
pin(MX + 20, 9.5, "", renk=INK)
ax.text(MX + 20, 6.4, "−", ha="center", fontsize=12, fontweight="bold", color=INK)
tel((MX + 8, 28), (MX + 8, 9.5), INK)
tel((MX + 20, 28), (MX + 20, 9.5), INK)
ax.text(MX + 6.5, 24, "OUT+", ha="right", fontsize=7.8, color=INK)
ax.text(MX + 21.5, 24, "OUT−", ha="left", fontsize=7.8, color=INK)
ax.text(MX - 3, 24, "iki ucun ikisi de sürülür:\nhiçbirini GND'ye bağlama",
        ha="right", va="center", fontsize=7.6, color=GUC, linespacing=1.5)

# ------------------------------------------------------------------ buton
BX = 6
kutu(BX, 16, 30, 16, "Buton", "6 × 6 mm · kapağın cebinde")
pin(BX + 30, 25, "", sag=False, renk=SINYAL)
pin(BX + 30, 22, "", sag=False, renk=TOPRAK)
tel((BX + 30, 25), (KX, 25), SINYAL, "GPIO18")
tel((BX + 30, 22), (KX, 22), TOPRAK, "GND")
ax.text(BX + 15, 14.5, "kutbu yok, iki bacağı da olur", ha="center",
        fontsize=7.4, color=MUT)

# ------------------------------------------------------------------- güç
kutu(BX, 54, 30, 24, "Güç")
ax.text(BX + 2.0, 71.0, "A) USB-C kablosu\n     powerbank ya da adaptör,\n"
                        "     karta doğrudan takılır",
        fontsize=7.9, color=INK, va="top", linespacing=1.5)
ax.text(BX + 2.0, 62.0, "B) 18650 + TP4056 + boost\n     boost 5.00 V'a ayarlı,\n"
                        "     kartın 5V ve GND pinine",
        fontsize=7.9, color=INK, va="top", linespacing=1.5)
tel((BX + 30, 57), (KX, 57), GUC)
ax.text((BX + 30 + KX) / 2, 58.2, "B: 5V + GND", ha="center", fontsize=7.4, color=GUC)

plt.tight_layout()
here = os.path.dirname(os.path.abspath(__file__))
for ext in ("png", "svg"):
    fig.savefig(os.path.join(here, "kablolama." + ext),
                **({"dpi": 170} if ext == "png" else {}), facecolor=BG)
print("yazıldı: " + os.path.join(here, "kablolama.png"))
