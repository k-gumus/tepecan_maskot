#!/usr/bin/env python3
"""Basılmış STL'lerin elektronikle uyumunu ölçer.

Modeli yeniden kurmaz: stl/ altındaki dosyaları okur, gerçek parçaların
zarflarını milimetre cinsinden yerleştirir ve boolean kesişim hacmine bakar.
Sıfır olmayan her kesişim, o parçanın gövdeye girmediği anlamına gelir.

    python3 dogrula.py
"""

import os
import sys

import numpy as np
import trimesh
from trimesh import creation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tepecan_model as T

ENGINE = "manifold"
CLEAR = 1.0                     # her yöne istenen en az boşluk (mm)
STL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")

failures = []


def ok(msg):
    print("OK   " + msg)


def bad(msg):
    print("HATA " + msg)
    failures.append(msg)


# --------------------------------------------------------------------------
T.configure(240.0)
S = T.SCALE
BASE_TRIM = 2.0                 # build_all'ın tabandan kestiği tasarım birimi


def Z(zu):
    """Tasarım birimi z -> STL dosyasındaki mm z."""
    return (zu - BASE_TRIM) * S


def M(vu):
    """Tasarım birimi uzunluk -> mm."""
    return vu * S


def load(name):
    return trimesh.load(os.path.join(STL, name + ".stl"))


body = load("tepecan_body")
lid = load("tepecan_lid")
cap = load("tepecan_buton")
solid = load("tepecan_solid")


def clash(mesh, env):
    c = trimesh.boolean.intersection([env, mesh], engine=ENGINE)
    return (c.volume, c.bounds) if len(c.faces) else (0.0, None)


def box(size, center):
    return creation.box(
        extents=size,
        transform=trimesh.transformations.translation_matrix(center),
    )


def oval_prism(rx, rz, y0, y1, center_xz):
    """Y ekseni boyunca uzanan eliptik silindir."""
    m = creation.cylinder(radius=1.0, segment=[(0, 0, 0), (0, 0, 1)], sections=96)
    m.apply_scale((rx, rz, abs(y1 - y0)))
    m.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, (1, 0, 0)))
    m.apply_translation((center_xz[0], min(y0, y1), center_xz[1]))
    return m


def fits(name, mesh, env, limit=1.0):
    v, b = clash(mesh, env)
    if v <= limit:
        ok("%s: boşlukta" % name)
    else:
        bad("%s: çakışma %8.1f mm3  bbox=%s" % (name, v, np.round(b, 1).tolist()))


# --------------------------------------------------------------------------
print("--- baskıya hazırlık ---")
for name, mesh in (("tepecan_solid", solid), ("tepecan_body", body),
                   ("tepecan_lid", lid), ("tepecan_buton", cap)):
    parts = len(mesh.split(only_watertight=False))
    if mesh.is_watertight and mesh.is_winding_consistent and parts == 1 and mesh.volume > 0:
        ok("%-14s su geçirmez, tek parça, %6.1f cm3" % (name, mesh.volume / 1000.0))
    else:
        bad("%s: watertight=%s winding=%s parça=%d"
            % (name, mesh.is_watertight, mesh.is_winding_consistent, parts))

print("\n--- iç hacim ---")
# 1. Pi Zero 2 W + HAT: 65 x 30 mm kart, başlıklarla birlikte 22 mm yükseklik
board_z0 = Z(T.BOARD_Z)
fits("kart + HAT (65x30x22 mm, +%.0f mm boşluk)" % CLEAR, body,
     box((65 + 2 * CLEAR, 30 + 2 * CLEAR, 22 + CLEAR),
         (0, M(T.BOARD_Y), board_z0 + 11 + CLEAR / 2)))

# 2. Hoparlör: 40 x 20 mm oval, 8 mm derin gövde, düz omuza oturmuş
spk_y = M(T.speaker_seat_y())
fits("hoparlör (%.0fx%.0f oval, 8 mm derin)" % (T.SPK_BODY_W, T.SPK_BODY_H), body,
     oval_prism(T.SPK_BODY_W / 2 + CLEAR - 0.05, T.SPK_BODY_H / 2 + CLEAR - 0.05,
                spk_y - 8.0, spk_y - 0.2, (0, Z(T.SPK_Z))))

# 3. Alt vida bossu kartın arka kenarının gerisinde kalmalı
boss_front = M(T.cavity_back_y(min(T.BOSS_Z)) + T.BOSS_DEPTH)
board_back = M(T.BOARD_Y) - 15.0
if board_back - boss_front >= CLEAR:
    ok("alt vida bossu kartın %.1f mm gerisinde (ön yüz y=%.1f mm)"
       % (board_back - boss_front, boss_front))
else:
    bad("alt vida bossu karta giriyor: boss y=%.1f, kart arka kenarı y=%.1f mm"
        % (boss_front, board_back))

print("\n--- kapak ve buton ---")
# 4. Tactile switch 6 x 6 x 4.3 mm ve buton kapağı
pocket_w = M(2 * T.BTN_POCKET)
pocket_d = M(T.BTN_DEPTH)
guide = M(T.BTN_GUIDE)
stem_len = M(T.WALL + T.BTN_GUIDE)
print("     switch cebi %.1f mm kare / %.1f mm derin, kılavuz %.1f mm"
      % (pocket_w, pocket_d, guide))
if pocket_w >= 6.4 and pocket_d >= 3.5:
    ok("6 x 6 x 4.3 mm switch cebe giriyor (%.1f mm bolluk)" % (pocket_w - 6.0))
else:
    bad("switch cebi yetersiz: %.1f mm kare / %.1f mm derin" % (pocket_w, pocket_d))

# sap ucu tam pistona dayanmalı: kapak eti + kılavuz kadar
if abs(stem_len - (M(T.WALL) + guide)) < 0.05:
    ok("cap sapı %.1f mm = kapak eti %.1f + kılavuz %.1f, switch'i ezmiyor"
       % (stem_len, M(T.WALL), guide))
else:
    bad("cap sapı boyu tutmuyor: %.1f mm" % stem_len)

stem_r = M(T.BTN_HOLE - T.BTN_FIT)
hole_r = M(T.BTN_HOLE)
if hole_r - stem_r >= 0.2:
    ok("buton sapı Ø%.1f mm, delik Ø%.1f mm (%.2f mm boşluk)"
       % (2 * stem_r, 2 * hole_r, hole_r - stem_r))
else:
    bad("buton sapı sıkı: sap Ø%.1f, delik Ø%.1f" % (2 * stem_r, 2 * hole_r))

cap_h = cap.extents.min()
if abs(cap_h - (M(T.BTN_CAP_T) + stem_len)) < 0.3:
    ok("buton kapağı Ø%.1f mm, toplam %.1f mm" % (M(2 * T.BTN_CAP_R), cap_h))
else:
    bad("buton kapağı ölçüsü beklenenden farklı: %.1f mm" % cap_h)

print("\n--- açıklıklar ---")
w_open = M(T.HATCH_W - 2 * T.LEDGE_W)
h_open = M(T.HATCH_H - 2 * T.LEDGE_W)
diag = float(np.hypot(w_open, h_open))
print("     kapak açıklığı %.1f x %.1f mm, geçiş %.1f x %.1f mm, köşegen %.1f mm"
      % (M(T.HATCH_W), M(T.HATCH_H), w_open, h_open, diag))
board_diag = float(np.hypot(65.0, 22.0))
if diag >= board_diag + 2.0:
    ok("kart (köşegen %.1f mm) açıklıktan geçiyor" % board_diag)
else:
    bad("kart açıklıktan geçmiyor: %.1f > %.1f mm" % (board_diag, diag))

# Kule vidalarına tornavida erişimi: delikler açıklığın kenarına ne kadar yakın?
# Açıklık yuvarlatılmış dikdörtgen; delik yüksekliğindeki yarı-genişliği ölçüyoruz.
corner_r = M(4.0)
hatch_zc = Z(T.HATCH_Z)
d = abs(board_z0 - hatch_zc)
straight = h_open / 2 - corner_r
if d <= straight:
    half_at_holes = w_open / 2
else:
    half_at_holes = w_open / 2 - corner_r + float(
        np.sqrt(max(0.0, corner_r ** 2 - (d - straight) ** 2)))
margin = half_at_holes - M(T.BOARD_HOLE_X)
if margin >= 3.0:
    ok("kule vidalarına erişim: açıklık kenarına %.1f mm (tornavida girer)" % margin)
else:
    bad("kule vidaları açıklığın kenarına çok yakın: %.1f mm" % margin)

print("\n--- montaj ölçüleri ---")
print("     kule delik aralığı  %.1f x %.1f mm (Pi Zero 2 W: 58.0 x 23.0)"
      % (M(2 * T.BOARD_HOLE_X), M(2 * T.BOARD_HOLE_Y)))
print("     kule üst yüzeyi     z = %.1f mm (tabandan)" % board_z0)
print("     kule / kılavuz çapı %.1f / %.1f mm" % (M(2 * T.POST_R), M(2 * T.POST_PILOT)))
print("     vida bossu          Ø%.1f mm, %.1f mm derin" % (M(2 * T.BOSS_R), M(T.BOSS_DEPTH)))
print("     hoparlör yuvası     %.1f x %.1f mm, %d yarık" % (M(T.SPK_W), M(T.SPK_H), T.SPK_SLOTS))
print("     kablo yuvası        %.1f x %.1f mm @ z=%.1f mm"
      % (M(T.CABLE_W), M(T.CABLE_H), Z(T.CABLE_Z)))
print("     et kalınlığı        %.1f mm" % M(T.WALL))

print("\nSONUÇ: %s" % ("BAŞARISIZ (%d)" % len(failures) if failures else "GEÇTİ"))
sys.exit(1 if failures else 0)
