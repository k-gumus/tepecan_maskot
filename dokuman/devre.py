#!/usr/bin/env python3
"""Tepecan bağlantı şeması -> PNG + SVG.

Raspberry Pi ve muadil aarch64 kartlar Türkiye'de bulunamadığı için kurulum
ESP32-S3'e taşındı. Ses tamamen I2S üzerinden: S3'ün dahili DAC'ı olmadığı
için analog çıkış seçenek değil.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

INK, ACC, MUT = "#16202c", "#1f5fa9", "#5b6875"
BG, CARD = "#ffffff", "#f4f6f9"

fig, ax = plt.subplots(figsize=(11.5, 8.4), facecolor=BG)
ax.set_xlim(0, 112); ax.set_ylim(0, 84); ax.axis("off")


def box(x, y, w, h, title, lines=(), fc=CARD, ec=ACC, lw=1.6, tc=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.2",
                                fc=fc, ec=ec, lw=lw, zorder=2))
    ax.text(x + w / 2, y + h - 3.0, title, ha="center", va="top", fontsize=10.5,
            fontweight="bold", color=tc, zorder=3)
    for i, ln in enumerate(lines):
        ax.text(x + w / 2, y + h - 7.4 - i * 3.4, ln, ha="center", va="top",
                fontsize=8.3, color=MUT, zorder=3)


def arrow(p0, p1, label="", off=(0, 1.6), style="-|>", color=ACC, ls="-"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=14,
                                 lw=1.7, color=color, linestyle=ls,
                                 shrinkA=2, shrinkB=2, zorder=1))
    if label:
        mx, my = (p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1]
        ax.text(mx, my, label, ha="center", va="bottom", fontsize=8.2,
                color=INK, zorder=4, bbox=dict(fc=BG, ec="none", pad=1.2))


ax.text(2, 81, "Tepecan — bağlantı şeması", fontsize=15, fontweight="bold", color=ACC)
ax.text(2, 77.5, "Maskotun içindeki tüm kablolama. Beyin sunucusu ağ üzerinden bağlanır, "
                 "kablosu yoktur.", fontsize=8.8, color=MUT)

# --- üst sıra: güç -> kart -> ağ
box(2, 58, 26, 13, "5 V adaptör", ["USB-C, 2 A yeter"])
box(36, 56, 36, 17, "ESP32-S3-DevKitC-1",
    ["N16R8: 16 MB flash, 8 MB PSRAM", "Wi-Fi  ·  64 x 28 mm",
     "kartta vida deliği yok — kelepçe"])
ax.add_patch(FancyBboxPatch((80, 56), 30, 17, boxstyle="round,pad=0.6,rounding_size=1.2",
                            fc="#eef3fa", ec=MUT, lw=1.4, linestyle=(0, (4, 3)), zorder=2))
ax.text(95, 70, "Beyin sunucusu", ha="center", va="top", fontsize=10.5,
        fontweight="bold", color=MUT)
for i, ln in enumerate(["ağdaki bir PC", "faster-whisper + Ollama + Piper",
                        ":8000 ve :11434"]):
    ax.text(95, 66.2 - i * 3.4, ln, ha="center", va="top", fontsize=8.3, color=MUT)

# --- orta sıra: mikrofon, sağda buton
box(2, 37, 26, 13, "INMP441", ["I2S mikrofon", "L/R bacağı GND'ye"])
box(80, 37, 30, 13, "Buton", ["6 × 6 mm tactile,", "kapağın iç yüzündeki cepte"])

# --- alt sıra: amfi -> hoparlör
box(36, 17, 36, 14, "MAX98357A", ["I2S amfi + DAC", "VIN 5 V (3V3 değil)"])
box(80, 18, 30, 13, "Hoparlör", ["Ø30 mm · 4-8 Ω", "vidalı klemens"])

# --- bağlantılar
arrow((28, 64.5), (36, 64.5), "5 V", off=(0, 0.8))
arrow((72, 64.5), (80, 64.5), "Wi-Fi", off=(0, 0.8), color=MUT,
      ls=(0, (4, 3)), style="<|-|>")
for p0, p1 in (((28, 43.5), (32, 43.5)), ((32, 43.5), (32, 59)), ((32, 59), (36, 59))):
    arrow(p0, p1, style="-" if p1 != (36, 59) else "-|>")
ax.text(30.6, 51, "I2S giriş — GPIO 4/5/6", fontsize=8.2, color=INK, va="center",
        rotation=90, ha="center", bbox=dict(fc=BG, ec="none", pad=1.2))
arrow((54, 56), (54, 31), "")
ax.text(55.5, 43, "I2S çıkış — GPIO 15/16/17", fontsize=8.2, color=INK, va="center",
        bbox=dict(fc=BG, ec="none", pad=1.2))
arrow((72, 24), (80, 24), "2 tel", off=(0, 0.6))

# buton -> kart: sağ koridordan yukarı, Wi-Fi okunun altından
for p0, p1 in (((80, 43.5), (76, 43.5)), ((76, 43.5), (76, 62)), ((76, 62), (72, 62))):
    arrow(p0, p1, style="-")
ax.text(77.4, 53, "GPIO18 + GND", fontsize=8.2, color=INK, va="center", rotation=90,
        ha="center", bbox=dict(fc=BG, ec="none", pad=1.2))

# --- notlar: en altta, iki sütun
ax.text(2, 12.5, "Notlar", fontsize=10, fontweight="bold", color=INK)
left = ["1. ESP32-S3'ün dahili DAC'ı yok (klasik ESP32'de vardı), o yüzden",
        "   ses tamamen I2S: MAX98357A hem DAC hem amfi.",
        "2. Bütün pinler kartın tek kenarında: 5Vin, GND, 18, 17, 16, 15,",
        "   6, 5, 4, 3V3. Tek header şeridi lehimlemek yetiyor."]
right = ["3. INMP441 3V3'ten beslenir, MAX98357A 5V'tan.",
         "4. Butonun kutbu yok, iki bacağı GPIO18 ve GND'ye gider.",
         "5. Uyandırma kelimesi varsayılan kapalı; buton tetikler.",
         "   Açmak için bkz. yazilim/esp32/README.md."]
for i, n in enumerate(left):
    ax.text(2, 9.0 - i * 2.9, n, fontsize=8.0, color=MUT, va="top")
for i, n in enumerate(right):
    ax.text(58, 9.0 - i * 2.9, n, fontsize=8.0, color=MUT, va="top")

plt.tight_layout()
# Çalışma dizinine değil, scriptin yanına yaz: kılavuz dosyayı buradan alıyor.
here = os.path.dirname(os.path.abspath(__file__))
for ext in ("png", "svg"):
    fig.savefig(os.path.join(here, "devre_semasi." + ext),
                **({"dpi": 170} if ext == "png" else {}), facecolor=BG)
print("yazıldı: " + os.path.join(here, "devre_semasi.png"))
