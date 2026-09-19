"""Plakalari kur ve her nesneyi DILIMLENECEGI KONUMDA denetle.

Parca kendi basina temiz cikip plakadaki konumunda bozuk cikabiliyor: tasima
ondalik aritmetigi degistirip sinirdaki bir kusuru aciga cikariyor. O yuzden
temizlik ve denetim yerlestirmeden sonra, yani dilimleyicinin gorecegi hal
uzerinde yapiliyor.
"""
import os, sys
import numpy as np, trimesh

sys.path.insert(0, "/home/user/tepecan_maskot/govde")
import agtemiz

G = "/home/user/tepecan_maskot/govde"
OUT = os.path.join(G, "3mf")
BED = 256.0


def place(path, x, y, name, spin=0.0):
    m = trimesh.load(path, process=False)
    if spin:
        m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(spin), [0, 0, 1]))
    lo, hi = m.bounds
    mid = (lo + hi) / 2.0
    m.apply_translation([x - mid[0], y - mid[1], -lo[2]])

    bad = agtemiz.gap_layers(m, 0.1)
    if bad:
        print("   %-14s yerinde %d kopukluk, temizleniyor" % (name, len(bad)))
        for tol in (1e-2, 3e-2, 1e-1, 2e-1, 3e-1):
            c = agtemiz.snap(agtemiz.simplify(agtemiz.snap(m), tol))
            c.vertices = c.vertices.astype(np.float32).astype(np.float64)
            c = agtemiz.snap(c)
            if not (c.is_watertight and c.volume > 0):
                continue
            if not agtemiz.gap_layers(c, 0.1):
                trimesh.repair.fix_normals(c)
                print("   %-14s tol %.0e ile temizlendi (hacim %.3f -> %.3f)"
                      % (name, tol, m.volume / 1000, c.volume / 1000))
                m = c
                break
        else:
            raise SystemExit("%s: yerinde temizlenemedi" % name)
    return name, m


def write(path, parts, gap=10.0):
    boxes = [(n, m.bounds[0][0], m.bounds[1][0], m.bounds[0][1], m.bounds[1][1]) for n, m in parts]
    for i, (n1, x0, x1, y0, y1) in enumerate(boxes):
        assert 0 < x0 and x1 < BED and 0 < y0 and y1 < BED, n1
        for n2, a0, a1, b0, b1 in boxes[i + 1:]:
            assert max(max(a0 - x1, x0 - a1), max(b0 - y1, y0 - b1)) > gap, "%s/%s" % (n1, n2)

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
        print("   %-14s hacim %6.1f cm3  wt  kopukluk %d" % (name, got.volume / 1000, n))
    print("%s -> %d nesne, kopukluk %d\n" % (os.path.basename(path), len(parts), total))
    return total


bad = 0
print("plaka 1")
bad += write(os.path.join(OUT, "parca_plaka1_govde_bacaklar.3mf"),
             [place(G + "/stl_parca/tepecan_govde.stl", 75, 128, "govde"),
              place(G + "/stl_parca/tepecan_bacaklar.stl", 180, 128, "bacaklar")])
print("plaka 2")
bad += write(os.path.join(OUT, "parca_plaka2_kafa.3mf"),
             [place(G + "/stl_parca/tepecan_kafa.stl", 128, 128, "kafa")])
print("plaka 3")
bad += write(os.path.join(OUT, "parca_plaka3_kapak_kollar.3mf"),
             [place(G + "/stl/tepecan_lid.stl", 128, 60, "arka_kapak"),
              place(G + "/stl_parca/tepecan_kol_sol_on.stl", 40, 180, "kol_sol_on"),
              place(G + "/stl_parca/tepecan_kol_sol_arka.stl", 95, 180, "kol_sol_arka"),
              place(G + "/stl_parca/tepecan_kol_sag_on.stl", 150, 180, "kol_sag_on"),
              place(G + "/stl_parca/tepecan_kol_sag_arka.stl", 205, 180, "kol_sag_arka")])
print("TUM PLAKALAR - toplam dikilemeyecek kopukluk:", bad)
