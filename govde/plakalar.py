#!/usr/bin/env python3
"""Baskı plakalarını kur ve her nesneyi DİLİMLENECEĞİ KONUMDA denetle.

Parça kendi başına temiz çıkıp plakadaki konumunda bozuk çıkabiliyor: taşıma
ondalık aritmetiği değiştirip sınırdaki bir kusuru açığa çıkarıyor. O yüzden
temizlik ve denetim yerleştirmeden sonra, yani dilimleyicinin göreceği hâl
üzerinde yapılıyor.

Yerleşim elle değil, raf paketlemesiyle: parçaların ayak izi tasarım
değiştikçe değişiyor, sabit koordinatlar her seferinde çakışıyordu.

    python3 parcala.py && python3 plakalar.py
"""
import os
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import agtemiz                                                   # noqa: E402

OUT = os.path.join(HERE, "3mf")
BED = 256.0
GAP = 10.0
EDGE = 6.0


def temizle_yerinde(name, m):
    """Parçayı bulunduğu konumda denetle, gerekirse orada temizle."""
    bad = agtemiz.gap_layers(m, 0.1)
    if not bad:
        return m
    print("   %-14s yerinde %d kopukluk, temizleniyor" % (name, len(bad)))
    for tol in (1e-2, 3e-2, 1e-1, 2e-1, 3e-1):
        c = agtemiz.snap(agtemiz.simplify(agtemiz.snap(m), tol))
        c.vertices = c.vertices.astype(np.float32).astype(np.float64)
        c = agtemiz.snap(c)
        if not (c.is_watertight and c.volume > 0):
            continue
        if not agtemiz.gap_layers(c, 0.1):
            trimesh.repair.fix_normals(c)
            print("   %-14s tol %.0e ile temizlendi" % (name, tol))
            return c
    raise SystemExit("%s: yerinde temizlenemedi" % name)


def paketle(items):
    """(ad, yol) listesini tablaya raf raf yerleştir. (ad, ağ) listesi döner.

    Parçalar yüksekliğine (y ayak izi) göre azalan sıralanıp soldan sağa
    diziliyor; satır dolunca bir alt rafa geçiliyor. Sığmazsa hata veriyor,
    sessizce üst üste bindirmiyor.
    """
    loaded = []
    for name, path in items:
        m = trimesh.load(path, process=False)
        m.apply_translation(-m.bounds[0])                 # köşeyi orijine al
        loaded.append([name, m, m.extents[0], m.extents[1]])
    loaded.sort(key=lambda r: -r[3])

    placed, x, y, shelf = [], EDGE, EDGE, 0.0
    for name, m, w, d in loaded:
        if x + w > BED - EDGE:
            x, y, shelf = EDGE, y + shelf + GAP, 0.0
        if y + d > BED - EDGE:
            raise SystemExit("%s tablaya sığmıyor (%.0f x %.0f mm)" % (name, w, d))
        m.apply_translation((x, y, 0.0))
        placed.append((name, m))
        x += w + GAP
        shelf = max(shelf, d)
    return placed


def yaz(path, items):
    parts = [(n, temizle_yerinde(n, m)) for n, m in paketle(items)]

    boxes = [(n, m.bounds[0][0], m.bounds[1][0], m.bounds[0][1], m.bounds[1][1])
             for n, m in parts]
    for i, (n1, x0, x1, y0, y1) in enumerate(boxes):
        assert 0 < x0 and x1 < BED and 0 < y0 and y1 < BED, "%s tablanın dışında" % n1
        for n2, a0, a1, b0, b1 in boxes[i + 1:]:
            d = max(max(a0 - x1, x0 - a1), max(b0 - y1, y0 - b1))
            assert d > GAP - 0.5, "%s ile %s arası yalnız %.1f mm" % (n1, n2, d)

    scene = trimesh.Scene()
    for name, mesh in parts:
        scene.add_geometry(mesh, geom_name=name, node_name=name)
    scene.export(path)

    back = trimesh.load(path)
    total = 0
    for name, src in parts:
        got = [g for k, g in back.geometry.items() if name in k][0]
        assert abs(got.volume - src.volume) < 1.0 and got.is_watertight, name
        n = len(agtemiz.gap_layers(got, 0.1))
        total += n
        print("   %-14s %6.1f cm3  %3.0f x %3.0f x %3.0f mm  su sızdırmaz  kopukluk %d"
              % (name, got.volume / 1000.0, *np.round(got.extents), n))
    print("%s -> %d nesne, kopukluk %d\n" % (os.path.basename(path), len(parts), total))
    return total


def P(name):
    return os.path.join(HERE, "stl_parca", "tepecan_%s.stl" % name)


def main():
    os.makedirs(OUT, exist_ok=True)
    bad = 0
    print("plaka 1 - gövde ve bacaklar")
    bad += yaz(os.path.join(OUT, "parca_plaka1_govde_bacaklar.3mf"),
               [("govde", P("govde")), ("bacaklar", P("bacaklar"))])
    print("plaka 2 - kafa")
    bad += yaz(os.path.join(OUT, "parca_plaka2_kafa.3mf"), [("kafa", P("kafa"))])
    print("plaka 3 - kapak ve kollar")
    bad += yaz(os.path.join(OUT, "parca_plaka3_kapak_kollar.3mf"),
               [("arka_kapak", os.path.join(HERE, "stl", "tepecan_lid.stl")),
                ("kol_sol_on", P("kol_sol_on")), ("kol_sol_arka", P("kol_sol_arka")),
                ("kol_sag_on", P("kol_sag_on")), ("kol_sag_arka", P("kol_sag_arka"))])
    print("TÜM PLAKALAR - dikilemeyecek toplam kopukluk:", bad)


if __name__ == "__main__":
    main()
