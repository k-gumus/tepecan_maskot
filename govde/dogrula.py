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
plate = load("tepecan_plaka")


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
                   ("tepecan_lid", lid), ("tepecan_buton", cap),
                   ("tepecan_plaka", plate)):
    parts = len(mesh.split(only_watertight=False))
    if mesh.is_watertight and mesh.is_winding_consistent and parts == 1 and mesh.volume > 0:
        ok("%-14s su geçirmez, tek parça, %6.1f cm3" % (name, mesh.volume / 1000.0))
    else:
        bad("%s: watertight=%s winding=%s parça=%d"
            % (name, mesh.is_watertight, mesh.is_winding_consistent, parts))

print("\n--- iç hacim ---")
# Kart artık doğrudan gövdeye değil, adaptör plakasının üstüne oturuyor.
plate_z0 = Z(T.BOARD_Z)                             # kulelerin tepesi
board_z0 = plate_z0 + M(T.PLATE_T + T.PLATE_STAND)  # kartın alt yüzeyi

# 1. Referans kart zarfı: Pi Zero ayak izi, konnektörlerle 18 mm yükseklik.
#    HAT yok (Pi bulunamıyor, USB ses yolu kullanılıyor), ama USB dongle ve
#    kablo için HAT'inkine yakın bir yükseklik bırakıyoruz.
fits("kart (65x30x18 mm, +%.0f mm boşluk)" % CLEAR, body,
     box((65 + 2 * CLEAR, 30 + 2 * CLEAR, 18 + CLEAR),
         (0, M(T.BOARD_Y), board_z0 + 9 + CLEAR / 2)))

# 2. Hangi kartın alınacağı belli değil: kavitenin kabul ettiği zarfı ölçüp
#    yazdırıyoruz, ki muadil seçerken tahmine değil sayıya bakılsın.
def envelope(depth, height, lo=20.0, hi=95.0):
    """Verilen derinlik/yükseklikte sığan en geniş kart; sığmıyorsa None."""
    for _ in range(8):
        mid = (lo + hi) / 2.0
        env = box((mid + 2 * CLEAR, depth + 2 * CLEAR, height + CLEAR),
                  (0, M(T.BOARD_Y), board_z0 + height / 2.0 + CLEAR / 2.0))
        lo, hi = (mid, hi) if clash(body, env)[0] <= 1.0 else (lo, mid)
    return None if lo <= 20.5 else lo

for d in (30.0, 35.0, 40.0):
    w = envelope(d, 18.0)
    print("     %4.0f mm derin kart -> %s"
          % (d, "en fazla %.1f mm genişlik" % w if w else "SIĞMIYOR"))

h = 20.0
while h < 60.0 and envelope(30.0, h + 5.0):
    h += 5.0
print("     30 mm derin kart -> plakanın üstünde en az %.0f mm yükseklik" % h)

# 3. Hoparlör: 30 mm yuvarlak, 8 mm derin gövde, düz omuza oturmuş
spk_y = M(T.speaker_seat_y())
fits("hoparlör (Ø%.0f mm yuvarlak, 8 mm derin)" % T.SPK_BODY_W, body,
     oval_prism(T.SPK_BODY_W / 2 + CLEAR - 0.05, T.SPK_BODY_H / 2 + CLEAR - 0.05,
                spk_y - 8.0, spk_y - 0.2, (0, Z(T.SPK_Z))))

# 4. Hoparlör adası kartın önüne girmemeli. Sınırlayan yüzey oturma omzu
#    değil, adanın arkaya bakan yüzü: omuz eksi bilezik derinliği.
spk_back = spk_y - M(T.SPK_LIP)
board_front = M(T.BOARD_Y) + 15.0
if spk_back - board_front >= CLEAR:
    ok("hoparlör adasının arkası kartın %.1f mm önünde (y=%.1f mm)"
       % (spk_back - board_front, spk_back))
else:
    bad("hoparlör adası karta giriyor: ada arkası y=%.1f, kart ön kenarı y=%.1f mm"
        % (spk_back, board_front))

# 5. Göğüs yazısına pay: ızgaranın üst kenarı YEDİTEPE'nin altına girmemeli
spk_top = Z(T.SPK_Z) + T.SPK_BODY_H / 2.0
text_bottom = Z(57.0 - 3.6 / 2)
if text_bottom - spk_top >= 2.0:
    ok("ızgara üst kenarı YEDİTEPE'ye %.1f mm uzak" % (text_bottom - spk_top))
else:
    bad("ızgara göğüs yazısına giriyor: ızgara üstü z=%.1f, yazı altı z=%.1f"
        % (spk_top, text_bottom))

# 6. Alt vida bossu kartın arka kenarının gerisinde kalmalı
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

# Plaka açıklıktan geçmeli: düz geçmezse yan yatırılarak, köşegenden.
pw, pd, pt = plate.extents
plate_diag = float(np.hypot(pw, pd))
if pw <= w_open and pd <= h_open:
    ok("adaptör plakası (%.1f x %.1f mm) açıklıktan düz geçiyor" % (pw, pd))
elif plate_diag + 2.0 <= diag:
    ok("adaptör plakası (%.1f x %.1f mm) yan yatırılarak geçiyor "
       "(köşegen %.1f < %.1f mm)" % (pw, pd, plate_diag, diag))
else:
    bad("adaptör plakası açıklıktan geçmiyor: köşegen %.1f > %.1f mm"
        % (plate_diag, diag))

# Tornavida erişimi: hem gövde kulelerinin hem plaka standoff'larının vidaları
# açıklıktan dik girilerek sıkılabilmeli. Açıklık yuvarlatılmış dikdörtgen,
# o yüzden delik yüksekliğindeki yarı-genişliği hesaplıyoruz.
corner_r = M(4.0)
hatch_zc = Z(T.HATCH_Z)


def half_width_at(z):
    d = abs(z - hatch_zc)
    straight = h_open / 2 - corner_r
    if d <= straight:
        return w_open / 2
    return w_open / 2 - corner_r + float(
        np.sqrt(max(0.0, corner_r ** 2 - (d - straight) ** 2)))


for label, z, hx in (("gövde kulesi", plate_z0, M(T.PLATE_HOLE_X)),
                     ("plaka standoff'u", board_z0, M(T.BOARD_HOLE_X))):
    margin = half_width_at(z) - hx
    if margin >= 3.0:
        ok("%s vidalarına erişim: açıklık kenarına %.1f mm (tornavida girer)"
           % (label, margin))
    else:
        bad("%s vidaları açıklığın kenarına çok yakın: %.1f mm" % (label, margin))

print("\n--- montaj ölçüleri ---")
print("     gövde kule aralığı  %.1f x %.1f mm (karttan bağımsız)"
      % (M(2 * T.PLATE_HOLE_X), M(2 * T.PLATE_HOLE_Y)))
print("     kule üst yüzeyi     z = %.1f mm (tabandan)" % plate_z0)
print("     plaka               %.1f x %.1f x %.1f mm, %.1f cm3"
      % (pw, pd, pt, plate.volume / 1000.0))
print("     plakadaki kart deseni %.1f x %.1f mm (Pi Zero ailesi: 58.0 x 23.0)"
      % (M(2 * T.BOARD_HOLE_X), M(2 * T.BOARD_HOLE_Y)))
print("     kart alt yüzeyi     z = %.1f mm, üstü (18 mm) z = %.1f mm"
      % (board_z0, board_z0 + 18.0))
print("     kart için y penceresi %.1f .. %.1f mm = %.1f mm derinlik"
      " (kart merkezi y=%.1f)"
      % (boss_front + CLEAR, spk_back - CLEAR,
         (spk_back - boss_front) - 2 * CLEAR, M(T.BOARD_Y)))
print("     kule / kılavuz çapı %.1f / %.1f mm" % (M(2 * T.POST_R), M(2 * T.POST_PILOT)))
print("     vida bossu          Ø%.1f mm, %.1f mm derin" % (M(2 * T.BOSS_R), M(T.BOSS_DEPTH)))
print("     hoparlör            Ø%.1f mm @ z=%.1f mm, %d yarık"
      % (M(T.SPK_W), Z(T.SPK_Z), T.SPK_SLOTS))
print("     kablo yuvası        %.1f x %.1f mm @ z=%.1f mm"
      % (M(T.CABLE_W), M(T.CABLE_H), Z(T.CABLE_Z)))
print("     et kalınlığı        %.1f mm" % M(T.WALL))

print("\nSONUÇ: %s" % ("BAŞARISIZ (%d)" % len(failures) if failures else "GEÇTİ"))
sys.exit(1 if failures else 0)
