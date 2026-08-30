#!/usr/bin/env python3
"""Tepecan bağlantı şeması -> PNG + SVG."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

INK, ACC, MUT = "#16202c", "#1f5fa9", "#5b6875"
BG, CARD = "#ffffff", "#f4f6f9"

fig, ax = plt.subplots(figsize=(11, 7.2), facecolor=BG)
ax.set_xlim(0, 110); ax.set_ylim(0, 72); ax.axis("off")


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
                color=INK, zorder=4,
                bbox=dict(fc=BG, ec="none", pad=1.2))


ax.text(2, 68.5, "Tepecan — bağlantı şeması", fontsize=15, fontweight="bold", color=ACC)
ax.text(2, 65.0, "Maskotun içindeki tüm kablolama. Beyin sunucusu ağ üzerinden bağlanır, "
                 "kablosu yoktur.", fontsize=8.8, color=MUT)

# --- güç
box(2, 46, 26, 12, "5 V 3 A adaptör", ["priz -> micro-USB"])
# --- Pi
box(40, 44, 34, 16, "Raspberry Pi Zero 2 W",
    ["65 x 30 mm  ·  Wi-Fi", "microSD: Raspberry Pi OS Lite 64-bit"])
# --- HAT
box(40, 24, 34, 16, "ReSpeaker 2-Mics Pi HAT",
    ["mikrofon L      mikrofon R", "WM8960 kodek + 3 W D-sınıfı amfi"])
# --- hoparlör
box(84, 24, 24, 12, "Hoparlör", ["40 mm · 4 Ω · 3 W"])
# --- buton
box(78, 5, 30, 12, "Buton (6 mm tactile)", ["sol omuzdaki 7 rozetinin", "altına gelir"])

# --- bağlantılar
arrow((28, 52), (40, 52), "micro-USB\n(PWR IN portu)", off=(0, 0.8))
arrow((57, 44), (57, 40), "", style="-")
ax.text(58.5, 42, "40 pin header — HAT doğrudan oturur, ara kablo yok",
        fontsize=8.2, color=INK, va="center")
arrow((74, 30), (84, 30), "JST PH2.0\nhoparlör çıkışı", off=(0, 0.6))
arrow((62, 24), (62, 19), "", style="-")
arrow((62, 19), (78, 19), "", style="-")
arrow((78, 19), (78, 17), "", style="-")
ax.text(63.5, 21.0, "GPIO17 + GND (iki tel)", fontsize=8.2, color=INK, va="center")

# --- ağ tarafı
ax.add_patch(FancyBboxPatch((84, 44), 24, 16, boxstyle="round,pad=0.6,rounding_size=1.2",
                            fc="#eef3fa", ec=MUT, lw=1.4, linestyle=(0, (4, 3)), zorder=2))
ax.text(96, 57, "Beyin sunucusu", ha="center", va="top", fontsize=10.5,
        fontweight="bold", color=MUT)
for i, ln in enumerate(["ağdaki bir PC", "faster-whisper + Ollama + Piper",
                        ":8000 ve :11434"]):
    ax.text(96, 53.2 - i * 3.4, ln, ha="center", va="top", fontsize=8.3, color=MUT)
arrow((74, 52), (84, 52), "Wi-Fi", off=(0, 0.6), color=MUT, ls=(0, (4, 3)), style="<|-|>")

ax.text(2, 16, "Notlar", fontsize=10, fontweight="bold", color=INK)
for i, n in enumerate([
        "• Mikrofonlar ve amfi HAT'in üzerinde; ayrıca kablolama gerektirmez.",
        "• Adaptör 3 A olmalı; zayıf besleme seste cızırtı ve kesilme yapar.",
        "• Butonun kutbu yok, iki bacağı GPIO17 ve GND'ye gider.",
        "• İşlemciye soğutucuyu HAT'i takmadan önce yapıştır."]):
    ax.text(2, 12.4 - i * 3.1, n, fontsize=8.3, color=MUT, va="top")

plt.tight_layout()
fig.savefig("devre_semasi.png", dpi=170, facecolor=BG)
fig.savefig("devre_semasi.svg", facecolor=BG)
print("yazıldı")
