#!/usr/bin/env python3
"""Ağ hijyeni: dilimleyicinin konturu kapatabildiğinden emin olmak.

Boolean'lar yoğun ağlarda kılcal üçgenler bırakıyor. trimesh bunlara
"watertight" diyor, kenarlar eşleştiği sürece öyleler de; ama dilimleyici
kesiti üretirken her üçgenden bir parça çıkarıp bunları uç uca zincirliyor,
ve kılcal üçgenlerin yüzünden zincir bazı katmanlarda kapanmıyor. Kapanmayan
kontur atılıyor: katman boşalıyor, Bambu da "boş katman için nesne
yazdırılamıyor" deyip nesneyi plakadan düşürüyor.

Ölçüldü: dokunulmamış `tepecan_solid.stl` 1150 katmanın 153'ünde açık kontur
veriyordu. Yani kusur bölme işleminden değil, modelin kendi boolean'larından
geliyor ve ilk baskıdaki "her yeri boşluklu" sonucun sebebi bu.

`temizle()` iki şeyi birleştiriyor: manifold3d'nin `simplify`'ı kılcal
üçgenleri yutuyor, vertex yapıştırma da çakışık köşeleri tek noktaya
indiriyor. İkisi hacmi değiştirmiyor; tolerans mikron mertebesinde, yani
0.4 mm'lik nozul'un çok altında.
"""

import numpy as np
import trimesh

try:
    import manifold3d
except ImportError:                                  # pragma: no cover
    manifold3d = None

QUANT = 1e-6        # uç noktaları eşleştirme hassasiyeti (mm)
# Tolerans merdiveni: en büyüğü 0.2 mm, yani bir katman yüksekliği kadar ve
# 0.42 mm'lik ekstrüzyon genişliğinin altında. Kanal ve panel çizgileri
# 2.2 mm genişliğinde, dolayısıyla bu ölçekte hiçbiri kaybolmuyor.
TOLERANCES = (1e-3, 3e-3, 1e-2, 3e-2, 1e-1, 2e-1)


def _layer_segments(mesh, z):
    """Bir düzlemin kestiği her üçgenden bir parça."""
    v = mesh.vertices[mesh.faces]
    d = v[:, :, 2] - z
    above = d > 0
    n_above = above.sum(axis=1)
    segments = []
    for f in np.where((n_above == 1) | (n_above == 2))[0]:
        tri, dd, ab = v[f], d[f], above[f]
        lone = int(np.argmax(ab)) if n_above[f] == 1 else int(np.argmin(ab))
        ends = []
        for other in (i for i in range(3) if i != lone):
            t = dd[lone] / (dd[lone] - dd[other])
            ends.append(tri[lone] + (tri[other] - tri[lone]) * t)
        segments.append((ends[0][:2], ends[1][:2]))
    return segments


def _chain(segments):
    """Parçaları zincirle; kapalı döngüleri ve kopan parçaları ayır.

    Kapalı bir döngüde her uç tam iki parçaya ait olur. Derecesi ikiden farklı
    bir uç, zincirin orada koptuğu anlamına gelir; o uca bağlı bileşenin
    tamamını açık sayıyoruz, çünkü dilimleyici de kapatamadığı konturu atıyor.
    """
    live = [(a, b) for a, b in segments if np.hypot(*(a - b)) >= QUANT]
    key = lambda p: (round(float(p[0]) / QUANT), round(float(p[1]) / QUANT))

    incident = {}
    for i, (a, b) in enumerate(live):
        for p in (a, b):
            incident.setdefault(key(p), []).append(i)

    broken = {k for k, v in incident.items() if len(v) != 2}
    parent = list(range(len(live)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for members in incident.values():
        for j in members[1:]:
            parent[find(members[0])] = find(j)

    tainted = set()
    for k in broken:
        for i in incident[k]:
            tainted.add(find(i))

    groups = {}
    for i in range(len(live)):
        groups.setdefault(find(i), []).append(i)
    closed = [[live[i] for i in idx] for root, idx in groups.items()
              if root not in tainted]
    return closed, len(tainted)


def _order_ring(group):
    """Bir bileşendeki parçaları uç uca dizip kapalı halkayı çıkar."""
    key = lambda p: (round(float(p[0]) / QUANT), round(float(p[1]) / QUANT))
    ends = {}
    for a, b in group:
        ends.setdefault(key(a), []).append((a, b))
        ends.setdefault(key(b), []).append((b, a))

    start, _ = group[0]
    ring = [start]
    prev_key, cur = None, start
    for _ in range(len(group) + 1):
        options = [o for o in ends.get(key(cur), []) if key(o[1]) != prev_key]
        if not options:
            break
        prev_key, cur = key(cur), options[0][1]
        if key(cur) == key(start):
            return np.asarray(ring)
        ring.append(cur)
    return None


def _shoelace(ring):
    x, y = ring[:, 0], ring[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def _closed_area(segments):
    """Yalnız kapanan konturlardan elde edilen alan.

    Halkaların yönü ağın sarımına göre değişebildiği için işaretli alana
    güvenmiyoruz: her halkanın mutlak alanını alıp, iç içe geçme derinliğinin
    tekliğine/çiftliğine bakarak delikleri çıkarıyoruz.
    """
    from shapely.geometry import Polygon, Point

    closed, _ = _chain(segments)
    rings = []
    for group in closed:
        ring = _order_ring(group)
        if ring is not None and len(ring) >= 3:
            rings.append(ring)
    if not rings:
        return 0.0

    polys = [Polygon(r) for r in rings]
    polys = [p if p.is_valid else p.buffer(0) for p in polys]
    total = 0.0
    for i, ring in enumerate(rings):
        # İç içe geçmeyi halkanın ÜZERİNDEKİ bir noktayla ölçüyoruz: dolu
        # dairenin iç noktası deliğin ortasına düşüp halkayı kendi deliği
        # sandırabiliyor.
        probe = Point(ring[0])
        depth = sum(1 for j, q in enumerate(polys)
                    if j != i and not q.is_empty and q.contains(probe))
        total += _shoelace(ring) * (1 if depth % 2 == 0 else -1)
    return max(0.0, total)


CLOSING_RADIUS = 0.049   # libslic3r slice_closing_radius (mm)


def gap_layers(mesh, layer=0.2, closing=CLOSING_RADIUS):
    """Konturun dilimleyicinin dikemeyeceği kadar koptuğu katmanların z'leri.

    Kopukluğun kendisi kusur değil: libslic3r kesitteki serbest uçları
    `slice_closing_radius` kadar bir mesafeye kadar birbirine dikiyor.
    Ölçtüğümüz şey boşluğun büyüklüğü -- 1e-7 mm'lik bir kopuk sorunsuz
    kapanıyor, 0.049 mm'yi aşan ya da eşi hiç olmayan bir uç ise konturu
    gerçekten kaybettiriyor ve katman boşalıyor.
    """
    import collections

    key = lambda p: (round(float(p[0]) / QUANT), round(float(p[1]) / QUANT))
    z0, z1 = mesh.bounds[:, 2]
    z = z0 + layer / 2.0
    bad = []
    while z < z1 - layer / 2.0:
        live = [(a, b) for a, b in _layer_segments(mesh, z)
                if np.hypot(*(a - b)) >= QUANT]
        incident = collections.defaultdict(list)
        for a, b in live:
            incident[key(a)].append(a)
            incident[key(b)].append(b)
        loose = [v[0] for v in incident.values() if len(v) != 2]
        if loose:
            pts = np.asarray(loose)
            if len(pts) < 2:
                bad.append(z)                      # eşi olmayan serbest uç
            else:
                d = np.linalg.norm(pts[:, None, :] - pts[None, :, :], axis=-1)
                np.fill_diagonal(d, np.inf)
                if float(d.min(axis=1).max()) > closing:
                    bad.append(z)
        z += layer
    return bad


def open_contour_layers(mesh, layer=0.2):
    """Üretim betiklerinin geçidi: dikilemeyecek kopukluğu olan katmanlar.

    Yarım katman adımıyla tarıyoruz. Parça plakaya yerleştirilince dilim
    düzlemleri yarım katman kayabiliyor; tek fazda tarayınca kusur örnekleme
    noktalarının arasına düşüp gözden kaçabiliyordu (bir kol yarımında tam
    olarak bu oldu: kendi başına temiz, plakadaki konumunda bir katman bozuk).
    """
    return gap_layers(mesh, layer / 2.0)


def snap(mesh, digits=4):
    """Çakışık köşeleri birleştir, sıfır alanlı üçgenleri at.

    Yalnız üç köşesi aynı indekse düşen üçgenler atılıyor; bunların alanı
    zaten sıfır olduğu için atmak delik açmıyor.
    """
    m = mesh.copy()
    m.merge_vertices(digits_vertex=digits)
    f = m.faces
    m.update_faces((f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2]))
    m.remove_unreferenced_vertices()
    return m


def simplify(mesh, tolerance):
    """manifold3d'ye ağı yeniden ördür; kılcal üçgenler bu sırada yutuluyor."""
    if manifold3d is None:
        return mesh
    src = manifold3d.Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
                          tri_verts=np.asarray(mesh.faces, dtype=np.uint32))
    out = manifold3d.Manifold(src).simplify(tolerance)
    try:
        got = out.to_mesh64()
    except Exception:
        got = out.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(got.vert_properties)[:, :3].astype(np.float64),
                           faces=np.asarray(got.tri_verts), process=False)


def temizle(mesh, layer=0.2):
    """Açık kontur kalmayana kadar toleransı kademeli büyüterek temizle."""
    best, best_bad = mesh, open_contour_layers(mesh, layer)
    if not best_bad:
        return best
    for tol in TOLERANCES:
        candidate = snap(simplify(snap(mesh), tol))
        if not candidate.is_watertight or candidate.volume <= 0:
            continue
        bad = open_contour_layers(candidate, layer)
        if len(bad) < len(best_bad):
            best, best_bad = candidate, bad
        if not bad:
            break
    return best
