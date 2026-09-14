#!/usr/bin/env python3
"""Tepecan bağlantı şeması -> PNG + SVG.

Raspberry Pi Türkiye'de bulunamadığı için kurulum muadil bir aarch64 karta
ve USB ses yoluna taşındı: ReSpeaker HAT yalnız Raspberry Pi'de çalışıyor
(seeed-voicecard device-tree overlay'i), USB ses kartı ise her Linux kartında
sınıf-uyumlu olarak sürücüsüz çalışıyor.
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
box(2, 58, 26, 13, "5 V 3 A adaptör", ["priz -> USB-C / micro-USB"])
box(36, 56, 36, 17, "aarch64 SBC",
    ["Orange Pi Zero 2W vb.  ·  Wi-Fi", "64-bit Linux (Armbian / Debian)",
     "Raspberry Pi DEĞİL — bkz. not 1"])
ax.add_patch(FancyBboxPatch((80, 56), 30, 17, boxstyle="round,pad=0.6,rounding_size=1.2",
                            fc="#eef3fa", ec=MUT, lw=1.4, linestyle=(0, (4, 3)), zorder=2))
ax.text(95, 70, "Beyin sunucusu", ha="center", va="top", fontsize=10.5,
        fontweight="bold", color=MUT)
for i, ln in enumerate(["ağdaki bir PC", "faster-whisper + Ollama + Piper",
                        ":8000 ve :11434"]):
    ax.text(95, 66.2 - i * 3.4, ln, ha="center", va="top", fontsize=8.3, color=MUT)

# --- orta sıra: mikrofon -> ses kartı, sağda buton
box(2, 37, 26, 13, "Elektret mikrofon", ["3.5 mm fişli kapsül"])
box(36, 36, 36, 14, "USB ses kartı (CM108)",
    ["sınıf-uyumlu: sürücü yok", "mic in + line out"])
box(80, 37, 30, 13, "Buton", ["6 × 6 mm tactile,", "kapağın iç yüzündeki cepte"])

# --- alt sıra: amfi -> hoparlör
box(36, 17, 36, 14, "PAM8403 amfi", ["2 × 3 W D-sınıfı", "5 V'u karttan alır"])
box(80, 18, 30, 13, "Hoparlör", ["Ø30 mm · 4 Ω · 3 W"])

# --- bağlantılar
arrow((28, 64.5), (36, 64.5), "5 V", off=(0, 0.8))
arrow((72, 64.5), (80, 64.5), "Wi-Fi", off=(0, 0.8), color=MUT,
      ls=(0, (4, 3)), style="<|-|>")
arrow((54, 56), (54, 50), "")
ax.text(55.5, 53, "USB", fontsize=8.2, color=INK, va="center")
arrow((28, 43.5), (36, 43.5), "mic in", off=(0, 0.6))
arrow((54, 36), (54, 31), "")
ax.text(55.5, 33.5, "line out (3.5 mm)", fontsize=8.2, color=INK, va="center")
arrow((72, 24), (80, 24), "2 tel", off=(0, 0.6))

# buton -> kart: sağ koridordan yukarı, Wi-Fi okunun altından
for p0, p1 in (((80, 43.5), (76, 43.5)), ((76, 43.5), (76, 62)), ((76, 62), (72, 62))):
    arrow(p0, p1, style="-")
ax.text(77.4, 53, "GPIO + GND", fontsize=8.2, color=INK, va="center", rotation=90,
        ha="center", bbox=dict(fc=BG, ec="none", pad=1.2))

# --- notlar: en altta, iki sütun
ax.text(2, 12.5, "Notlar", fontsize=10, fontweight="bold", color=INK)
left = ["1. ReSpeaker HAT yalnız Raspberry Pi'de çalışır (seeed-voicecard",
        "   overlay'i); muadil kartta USB ses kartı kullanılıyor.",
        "2. Kart 64-bit olmalı: openWakeWord'ün istediği onnxruntime",
        "   yalnız aarch64 için derleniyor. ARMv6/ARMv7 kart alma."]
right = ["3. Adaptör 3 A olmalı; zayıf besleme seste cızırtı yapar.",
         "4. Butonun kutbu yok, iki bacağı GPIO ve GND'ye gider.",
         "5. Ses cihazını TEPECAN_MIC / TEPECAN_SPK ile seç;",
         "   `python3 -m sounddevice` cihazları listeler."]
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
