#!/usr/bin/env python3
"""Tepecan'ı ayrı basılıp yapıştırılan parçalara böler.

Tek parça baskı kafanın altında ve ellerde havada başlıyordu: kafa küresi
gövdeye Ø33 mm'lik bir boyunla oturuyor, yani kürenin alt yarısı boşlukta
başlıyor; kaldırılmış elin parmakları da öyle. Bölününce o yüzeyler baskı
plakasının üstüne geliyor, boyalı destek yerine sıradan `ağaç(Otomatik)` +
`Yalnızca baskı plakasında` yetiyor.

Kollar düzlemle değil, gövde küresinin yüzeyiyle kesiliyor: kesit eyer
biçiminde çıkıyor ve omuza tek bir şekilde oturuyor, yani pime gerek
kalmadan kendi kendine hizalanıyor. Boyun ve bacaklar düz kesildiği için
oralarda geçme var.

    python3 parcala.py [--height 230] [--outdir stl_parca]
"""

import argparse
import os

import numpy as np
import trimesh

import agtemiz
import tepecan_model as T
from tepecan_model import union, diff, inter, rod, ell, half_space, rot

NECK_Z = 79.8       # kafa küresinin altı 82; burada kesit sadece boyun çubuğu
HIP_Z = 22.0        # kalça elipsoidinin altı 17, bacaklar 27'ye kadar
NECK_R = 11.0       # head_solid içindeki boyun çubuğuyla aynı
SPIGOT_R = 6.5      # boyun geçmesi, boyun çubuğundan ince olmalı ki
SPIGOT_H = 8.0      # kafanın altında oturacak düz bir bilezik kalsın
PEG_H = 7.0         # bacak pimlerinin boyu
PEG_BACK = 3.5      # pim yarıçapı = bacak yarıçapı - bu
SINK = 4.0          # mil ve pimlerin ana parçanın içine gömüldüğü boy
GAP_ARM = 0.25      # mm, kolun omuz yüzeyinden kaçışı (yapıştırıcı payı)
ARM_SPLIT = 0.54    # bölme düzleminin, avuç normali yönündeki aralıktaki yeri


def fit():
    """Geçme boşluğu: 0.25 mm, tasarım birimine çevrilmiş."""
    return 0.25 / T.SCALE


def cyl(r, z0, z1, center_xy=(0.0, 0.0), sections=96):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=sections)
    m.apply_translation((center_xy[0], center_xy[1], (z0 + z1) / 2.0))
    return m


def palm_normal(triple):
    """Avuç düzleminin normali: hand()'in kurduğu yerel çerçevenin Y ekseni."""
    _, elbow, wrist = (np.asarray(p, dtype=float) for p in triple)
    f = T.unit(wrist - elbow)
    up = np.array([0.0, 1.0, 0.0])
    return T.unit(up - f * np.dot(up, f))


def split_arm(arm, triple, frac=ARM_SPLIT):
    """Kolu AVUÇ DÜZLEMİNDEN ikiye böl, her yarımı kesik yüzüne yatır.

    Önceden bölme düzlemi y eksenine dikti. Elin ince ekseni ise avuç normali
    ve o, y'den 26 derece sapık: sonuçta parmaklar tablaya yatmıyor, avucun
    kubbesi üstünde ayrı ayrı dikilen kuleler oluyordu. Basarken her biri
    havada başlıyor, elde de 6.6 mm'lik çubuk olarak kalıp kopuyordu
    (kullanıcıda üç parmak çıktı, ikisi koptu).

    Avuç normalini +y'ye döndürüp oradan bölünce parmaklar yarım silindir
    olarak yatıyor. Ölçüldü (sol kol, 230 mm): havada başlayan ada 47.9 -> 0.3
    mm2, parça yüksekliği 27.5 -> 17.5 mm, tabla teması 800 -> 1228 mm2.

    0.54, dört oranın taranmasıyla seçildi; avuç kesiti tam ortada değil çünkü
    parmaklar ilerledikçe avuç düzleminden dışarı kıvrılıyor.
    """
    m = trimesh.geometry.align_vectors(palm_normal(triple), [0, 1, 0])
    a = arm.copy()
    a.apply_transform(m)
    y0, y1 = a.bounds[:, 1]
    cut = y0 + (y1 - y0) * frac
    return {"_on": rot(biggest(inter(a, half_space(1, +1, cut))), +90, (1, 0, 0)),
            "_arka": rot(biggest(inter(a, half_space(1, -1, cut))), -90, (1, 0, 0))}


def leg_axis(z):
    """legs_and_feet: (±14, 2, 10) -> (±15, 2, 27), yarıçap 8.5."""
    return 14.0 + (z - 10.0) / 17.0, 2.0, 8.5


def torso_hull(grow):
    """Gövde + kalça elipsoidleri, yüzeyden `grow` kadar şişirilmiş."""
    return union(ell(tuple(r + grow for r in T.TORSO_R), T.TORSO_C),
                 ell(tuple(r + grow for r in T.HIP_R), T.HIP_C))


def arm_envelope(triple, side, with_text):
    """Tek kol: üst kol, ön kol, el, omuz pedi, soldaysa rozet."""
    shoulder, elbow, wrist = (np.asarray(p, dtype=float) for p in triple)
    parts = [T.limb([shoulder, elbow, wrist], [11.0, 7.5, 6.8]),
             T.hand(wrist, T.unit(wrist - elbow), (0, 1, 0)),
             rod((side * 26, 0, 72), (side * 31, 0, 71), 9.0, caps=False)]
    if side < 0:
        parts.append(T.shoulder_badge(with_text))
    return union(*parts)


def first_layer_area(mesh):
    try:
        sec = mesh.section(plane_origin=[0, 0, mesh.bounds[0, 2] + 0.2],
                           plane_normal=[0, 0, 1])
        planar, _ = sec.to_2D()
        return sum(poly.area for poly in planar.polygons_full)
    except Exception:
        return 0.0


def lay_flat(mesh):
    """Kolu en yatık duruşuna yatır.

    Kolda düz yüzey yok, o yüzden tabla teması her durumda birkaç mm2: parçayı
    destek taşıyor. Önemli olan desteğin kısa olması, yani parçanın alçak
    durması. Adaylar dışbükey kabuğun yüzleri; en alçak duruşlar arasından
    tabla teması en geniş olan seçiliyor.
    """
    hull = mesh.convex_hull
    areas = {}
    for normal, area in zip(np.round(hull.face_normals, 2), hull.area_faces):
        areas[tuple(normal)] = areas.get(tuple(normal), 0.0) + area

    best = []
    for normal in sorted(areas, key=areas.get, reverse=True)[:12]:
        axis = np.asarray(normal, dtype=float)
        axis /= np.linalg.norm(axis)
        trial = mesh.copy()
        trial.apply_transform(trimesh.geometry.align_vectors(axis, [0, 0, -1]))
        trial.apply_translation([0, 0, -trial.bounds[0, 2]])
        best.append((trial.extents[2], first_layer_area(trial), trial))

    lowest = min(b[0] for b in best)
    return max((b for b in best if b[0] <= lowest * 1.15), key=lambda b: b[1])[2]


def heal(mesh):
    """Boolean çıktısını manifold3d'den bir kez daha geçir.

    Yüzey silmiyoruz: sıfır alanlı üçgenler zararsız, onları atmak deliyor.
    Dert olan, çakışan yüzeylerden kalan üst üste binmiş kabuklar; dilimleyici
    aynı yerde iki kontur görünce ikisi birbirini götürüyor ve katman boşalıyor.
    Tek nesneli birleşim manifold'a ağı yeniden ördürüyor.
    """
    try:
        return trimesh.boolean.union([mesh.copy()], engine="manifold")
    except ValueError:
        return mesh


def slice_check(name, m, layer=0.2, wall=0.21):
    """Bambu'nun "boş katman" denetiminin aynısı: her katman basılabiliyor mu.

    Dilimleyici bir katmanda hiçbir kontur bulamazsa ya da bulduğu kontura tek
    bir duvar bile sığmıyorsa nesneyi plakadan düşürüyor. Dosyayı yazmadan önce
    parçanın tüm yüksekliğini bu gözle tarıyoruz.
    """
    from shapely.ops import unary_union
    z0, z1 = m.bounds[:, 2]
    bad = []
    z = z0 + layer / 2.0
    # Tepedeki yarım katman dilimlenmiyor zaten; onu kusur saymıyoruz.
    while z < z1 - layer / 2.0:
        try:
            sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            area = 0.0
            if sec is not None:
                polys = unary_union(sec.to_2D()[0].polygons_full)
                area = 0.0 if polys.is_empty else polys.buffer(-wall).area
        except Exception:
            area = 0.0          # kontur geçerli bir çokgen kurmuyor
        if area < 0.01:
            bad.append(z)
        z += layer
    if bad:
        print("   %s: %d katman basılamıyor  %s"
              % (name, len(bad), " ".join("%.1f" % b for b in bad[:12])))
        return False
    return True


def biggest(mesh, share=0.02):
    """Boolean'ların teğet yüzeylerde bıraktığı kabukları at."""
    parts = mesh.split(only_watertight=False)
    if len(parts) <= 1:
        return mesh
    with np.errstate(invalid="ignore", divide="ignore"):
        vols = [abs(p.volume) for p in parts]
    top = max(vols)
    kept = [p for p, v in zip(parts, vols) if v > top * share]
    return kept[0] if len(kept) == 1 else trimesh.util.concatenate(kept)


def figure_without_arms(with_text):
    """build_outer'ın kolsuz hâli.

    Gövdeyi kollarla kurup sonra kesip çıkarmak, kesim yüzeyini gövdenin kendi
    yüzeyiyle birebir çakıştırıyor; boolean oradan üst üste binmiş kabuk
    bırakıyor ve dilimleyici kesiti paramparça görüyor. Kol hiç eklenmezse
    omuz yüzeyi el değmemiş kalıyor. Omuz rozeti de sol kola gidiyor.
    """
    figure = union(T.torso_solid(), T.legs_and_feet(), T.head_solid(), T.eyes(),
                   T.head_details(), T.head_panel(), T.chest_panel(with_text),
                   T.rivets())
    return diff(figure, T.smile_cut(), T.head_grooves(), T.joint_grooves(),
                T.torso_seams(), T.foot_detail())


def build_parts(with_text=True):
    figure = figure_without_arms(with_text)

    posts, post_holes = T.board_posts()
    body = diff(figure, T.cavity_solid(), T.hatch_prism())
    body = union(body, T.ledge(), T.bosses(), T.speaker_mount(), posts)
    body = diff(body, T.lid_seat(), T.screw_pilots(), T.cable_slot(),
                T.speaker_grille(), post_holes)
    body = T.cut_below(body, 2.0)

    f = fit()
    out = {}

    # --- kollar: gövdeye hiç dokunmadan, kendi başlarına ---
    #
    # Bütün hâlde kol tablaya 7 mm2 ile değiyordu: yuvarlak bir uzuv nereye
    # yatırılırsa yatırılsın bir çizgi üstünde duruyor ve tamamen desteğin
    # üstünde yüzüyor. Kendi düzleminden ikiye ayrılınca her yarım düz yüzüne
    # yatıyor; temas 1100-1500 mm2'ye çıkıyor ve askıda yüzey neredeyse sıfır.
    # Parmaklar da yarım silindir olarak tablada uzanıyor, havada değil.
    for name, triple, side in (("kol_sol", T.ARM_LEFT, -1), ("kol_sag", T.ARM_RIGHT, +1)):
        env = arm_envelope(triple, side, with_text)
        arm = biggest(diff(env, torso_hull(GAP_ARM / T.SCALE)))
        for suffix, half in split_arm(arm, triple).items():
            out[name + suffix] = half

    # --- kafa: boyundan düz kesim, gövdede geçme mili ---
    head = biggest(inter(body, half_space(2, +1, NECK_Z)))
    body = biggest(inter(body, half_space(2, -1, NECK_Z)))
    body = union(body, cyl(SPIGOT_R, NECK_Z - SINK, NECK_Z + SPIGOT_H))
    head = diff(head, cyl(SPIGOT_R + f, NECK_Z - 1.0, NECK_Z + SPIGOT_H + f))
    out["kafa"] = biggest(head)

    # --- bacaklar: düz kesim, bacaklarda pim ---
    legs = biggest(inter(body, half_space(2, -1, HIP_Z)))
    body = biggest(inter(body, half_space(2, +1, HIP_Z)))
    for s in (-1, 1):
        x, y, r = leg_axis(HIP_Z)
        legs = union(legs, cyl(r - PEG_BACK, HIP_Z - SINK, HIP_Z + PEG_H, (s * x, y)))
        body = diff(body, cyl(r - PEG_BACK + f, HIP_Z - 1.0, HIP_Z + PEG_H + f, (s * x, y)))
    out["bacaklar"] = biggest(legs)
    out["govde"] = biggest(body)

    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Tepecan'ı basılabilir parçalara böl.")
    ap.add_argument("--outdir", default=os.path.join(here, "stl_parca"))
    ap.add_argument("--height", type=float, default=T.DEFAULT_HEIGHT)
    ap.add_argument("--no-text", action="store_true")
    args = ap.parse_args()

    T.configure(args.height)
    os.makedirs(args.outdir, exist_ok=True)

    for name, mesh in build_parts(with_text=not args.no_text).items():
        mesh.apply_scale(T.SCALE)
        mesh.apply_translation((0, 0, -mesh.bounds[0][2]))
        # STL float32 saklıyor: yuvarlamayı burada yap ki yuvarlamanın
        # doğurduğu kılcal üçgenler dosyaya yazılmadan önce süpürülsün.
        mesh = agtemiz.temizle(biggest(heal(mesh)))
        mesh.vertices = mesh.vertices.astype(np.float32).astype(np.float64)
        mesh = agtemiz.snap(mesh)
        trimesh.repair.fix_normals(mesh)

        path = os.path.join(args.outdir, "tepecan_" + name + ".stl")
        mesh.export(path)

        check = trimesh.load(path)
        if not (check.is_watertight and check.is_winding_consistent
                and len(check.split(only_watertight=False)) == 1 and check.volume > 0):
            raise SystemExit("%s temiz bir katı değil" % path)
        bad = agtemiz.open_contour_layers(check)
        if bad:
            raise SystemExit("%s: %d katmanda kontur kapanmıyor, ilki z=%.2f"
                             % (path, len(bad), bad[0]))
        slice_check(path, check)
        T.report(name, check)


if __name__ == "__main__":
    main()
