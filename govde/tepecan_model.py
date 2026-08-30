#!/usr/bin/env python3
"""
Tepecan - parametric, 3D-printable model of the club mascot.

Builds three STL files:

  tepecan_solid.stl  - one-piece display figure (no cavity, no hatch)
  tepecan_body.stl   - hollow body with an opening on the back, a seating
                       ledge and two screw bosses for the hatch cover
  tepecan_lid.stl    - the hatch cover, already rotated flat for printing

Everything is CSG (constructive solid geometry) on watertight primitives, so
the exported meshes are manifold and slice without repair.

    python3 tepecan_model.py --height 240

The figure is modelled in design units and scaled to the requested printed
height on export. Dimensions that must stay absolute no matter how big the
figure is - wall thickness, screw holes, cover clearance - are divided by
that scale factor first, so an M3 screw stays an M3 screw at any size.
"""

import argparse
import os

import numpy as np
import trimesh
from trimesh import creation

ENGINE = "manifold"


# --------------------------------------------------------------------------
# CSG helpers
# --------------------------------------------------------------------------
def union(*meshes):
    ms = [m for m in meshes if m is not None]
    return ms[0] if len(ms) == 1 else trimesh.boolean.union(ms, engine=ENGINE)


def diff(a, *meshes):
    return trimesh.boolean.difference([a] + list(meshes), engine=ENGINE)


def inter(a, *meshes):
    return trimesh.boolean.intersection([a] + list(meshes), engine=ENGINE)


def ell(radii, center=(0, 0, 0), subd=5):
    """Ellipsoid."""
    m = creation.icosphere(subdivisions=subd, radius=1.0)
    m.apply_scale(np.asarray(radii, dtype=float))
    m.apply_translation(np.asarray(center, dtype=float))
    return m


def ball(r, center=(0, 0, 0), subd=4):
    return ell((r, r, r), center, subd)


def rod(p0, p1, r, caps=True, sections=48):
    """Capsule between two points."""
    p0 = np.asarray(p0, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    parts = [creation.cylinder(radius=r, segment=[p0, p1], sections=sections)]
    if caps:
        parts += [ball(r, p0), ball(r, p1)]
    return union(*parts)


def limb(points, radii, sections=48):
    """Chain of capsules through a polyline, with a single ball at each joint."""
    parts = [ball(r, p) for p, r in zip(points, radii)]
    for (p0, r0), (p1, r1) in zip(zip(points, radii), zip(points[1:], radii[1:])):
        parts.append(creation.cylinder(radius=min(r0, r1), segment=[p0, p1], sections=sections))
    return union(*parts)


def rbox(size, center=(0, 0, 0), radius=3.0, subd=3):
    """Rounded box, built as the convex hull of eight corner spheres."""
    size = np.asarray(size, dtype=float)
    half = size / 2.0 - radius
    if np.any(half < 0):
        raise ValueError("corner radius too large for box %s" % (size,))
    pts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                pts.append(ball(radius, (sx * half[0], sy * half[1], sz * half[2]), subd).vertices)
    hull = trimesh.Trimesh(vertices=np.vstack(pts)).convex_hull
    hull.apply_translation(np.asarray(center, dtype=float))
    return hull


def xz_prism(w, h, r, y0, y1, sections=48):
    """Prism along Y whose X/Z cross-section is a rounded rectangle (flat ends)."""
    length = abs(y1 - y0)
    parts = [
        creation.box(extents=(w - 2 * r, length, h)),
        creation.box(extents=(w, length, h - 2 * r)),
    ]
    for sx in (-1, 1):
        for sz in (-1, 1):
            parts.append(
                creation.cylinder(
                    radius=r,
                    segment=[(sx * (w / 2 - r), -length / 2, sz * (h / 2 - r)),
                             (sx * (w / 2 - r), length / 2, sz * (h / 2 - r))],
                    sections=sections,
                )
            )
    prism = union(*parts)
    prism.apply_translation((0, (y0 + y1) / 2.0, 0))
    return prism


def slab_z(z0, z1, radius=300.0):
    """Infinite-ish horizontal slab between two heights."""
    return creation.cylinder(radius=radius, segment=[(0, 0, z0), (0, 0, z1)], sections=96)


def half_space(axis, sign, value, size=600.0):
    """Everything on one side of a plane, as a big box."""
    box = creation.box(extents=(size, size, size))
    off = np.zeros(3)
    off[axis] = value + sign * size / 2.0
    box.apply_translation(off)
    return box


def surface_band(radii, center, outward, inward):
    """Thin layer straddling an ellipsoid surface: used to carve panel lines."""
    return diff(
        ell(tuple(r + outward for r in radii), center),
        ell(tuple(r + inward for r in radii), center),
    )


def ring_groove(center, direction, major, minor, sections=96):
    """Torus centred on `center`, its axis along `direction`."""
    t = creation.torus(major, minor, major_sections=sections, minor_sections=20)
    d = np.asarray(direction, dtype=float)
    d /= np.linalg.norm(d)
    t.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], d))
    t.apply_translation(np.asarray(center, dtype=float))
    return t


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def frame(origin, forward, up):
    """Right-handed transform whose local X/Y/Z are side/up/forward."""
    f = unit(forward)
    u = np.asarray(up, dtype=float)
    u = unit(u - f * np.dot(u, f))
    side = np.cross(u, f)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2] = side, u, f
    m[:3, 3] = np.asarray(origin, dtype=float)
    return m


def placed(mesh, transform):
    m = mesh.copy()
    m.apply_transform(transform)
    return m


def hand(wrist, forward, palm_normal, thumb_side=-1, span=5.4, finger_r=2.2):
    """Round mitten hand with fingers on it.

    The palm is the ball of the original design; four two-segment fingers with
    knuckle balls and a two-segment thumb grow out of it. Built in a local
    frame - X across the palm, Y out of the palm, Z along the fingers - then
    placed on the wrist.
    """
    parts = [ell((9.0, 8.5, 8.5), (0, 0, 5.5))]

    for xi in (-1.5, -0.5, 0.5, 1.5):
        long = abs(xi) < 1.0                      # middle fingers a little longer
        l1, l2 = (8.5, 7.5) if long else (7.5, 6.5)
        a1, a2 = np.radians(14.0), np.radians(32.0)
        yaw = np.radians(xi * 8.0)                # fan the fingers out slightly
        c, sn = np.cos(yaw), np.sin(yaw)

        def splay(v):
            return np.array([v[0] * c + v[2] * sn, v[1], -v[0] * sn + v[2] * c])

        p0 = np.array([xi * span, 0.6, 10.0 if long else 9.0])
        p1 = p0 + l1 * splay([0.0, np.sin(a1), np.cos(a1)])
        p2 = p1 + l2 * splay([0.0, np.sin(a2), np.cos(a2)])
        parts.append(limb([p0, p1, p2], [finger_r, finger_r * 0.93, finger_r * 0.84]))

    t0 = np.array([thumb_side * 6.0, 2.5, 4.0])
    td = unit([thumb_side * 0.72, 0.36, 0.59])
    t1 = t0 + 6.6 * td
    t2 = t1 + 5.6 * unit(td + np.array([0.0, 0.40, 0.22]))
    parts.append(limb([t0, t1, t2], [2.7, 2.5, 2.2]))

    return placed(union(*parts), frame(wrist, forward, palm_normal))


def rot(mesh, angle_deg, axis, point=(0, 0, 0)):
    m = mesh.copy()
    m.apply_transform(
        trimesh.transformations.rotation_matrix(np.radians(angle_deg), axis, point)
    )
    return m


# --------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------
_CAP_UNITS = None


def _cap_units(fp):
    """Height of a capital letter in font units, so accents don't shrink text."""
    global _CAP_UNITS
    if _CAP_UNITS is None:
        from matplotlib.textpath import TextPath

        ref = TextPath((0, 0), "H", size=100, prop=fp)
        _CAP_UNITS = max(p[:, 1].max() for p in ref.to_polygons())
    return _CAP_UNITS


def text_solid(txt, cap_height, depth, center, max_width=None, facing="+Y"):
    """Extruded text, readable from `facing`. Returns None if fonts are missing."""
    try:
        from matplotlib.font_manager import FontProperties
        from matplotlib.textpath import TextPath
        from shapely.geometry import Polygon
    except ImportError:
        return None

    fp = FontProperties(family="DejaVu Sans", weight="bold")
    path = TextPath((0, 0), txt, size=100, prop=fp)
    polys = [Polygon(p).buffer(0) for p in path.to_polygons() if len(p) >= 3]
    polys.sort(key=lambda p: -p.area)
    shape = None
    for p in polys:
        if shape is None:
            shape = p
        elif shape.contains(p.representative_point()):
            shape = shape.difference(p)     # counter of an 'A', 'e', ...
        else:
            shape = shape.union(p)
    if shape is None or shape.is_empty:
        return None

    f = cap_height / _cap_units(fp)
    x0, _, x1, _ = shape.bounds
    if max_width is not None and (x1 - x0) * f > max_width:
        f = max_width / (x1 - x0)           # keep long names inside the panel

    letters = []
    geoms = shape.geoms if shape.geom_type == "MultiPolygon" else [shape]
    for g in geoms:
        letters.append(creation.extrude_polygon(g, height=depth / f))
    solid = union(*letters)

    solid.apply_scale(f)
    solid.apply_translation(-solid.bounds.mean(axis=0))
    # extrusion axis +Z -> +Y, text up -> +Z, reading direction -> -X
    solid.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-90), (1, 0, 0)))
    solid.apply_transform(trimesh.transformations.rotation_matrix(np.radians(180), (0, 1, 0)))
    if facing == "-X":
        solid.apply_transform(trimesh.transformations.rotation_matrix(np.radians(90), (0, 0, 1)))
    elif facing == "+X":
        solid.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-90), (0, 0, 1)))
    elif facing != "+Y":
        raise ValueError("facing must be +Y, -X or +X")
    solid.apply_translation(np.asarray(center, dtype=float))
    return solid


# --------------------------------------------------------------------------
# Geometry parameters, in design units (see SCALE below)
# --------------------------------------------------------------------------
NATURAL_HEIGHT = 154.2          # height of the untransformed figure
DEFAULT_HEIGHT = 240.0          # printed height, antenna tips included

TORSO_C = (0.0, 0.0, 52.0)
TORSO_R = (31.0, 26.0, 30.0)
HIP_C = (0.0, 0.0, 32.0)
HIP_R = (27.0, 23.0, 15.0)

HEAD_C = (0.0, 0.0, 110.0)
HEAD_R = (31.0, 29.0, 28.0)
ARM_LEFT = ((-29.0, 0.0, 68.0), (-36.0, 0.0, 52.0), (-33.0, 6.0, 36.0))
ARM_RIGHT = ((29.0, 0.0, 68.0), (38.0, 2.0, 56.0), (31.0, 11.0, 78.0))

EYE_DIR = (0.44, 0.90, 0.06)    # direction from the head centre, mirrored in x
EYE_W, EYE_H = 9.5, 10.5        # lens half width / half height on the face
EYE_BULGE = 3.4                 # how far the lens stands off the head
EYE_SINK = 1.2                  # how far its equator sits under the surface

HATCH_W = 38.0                  # opening width  (x)
HATCH_H = 40.0                  # opening height (z)
HATCH_Z = 54.0
HATCH_R = 5.0                   # corner radius
LEDGE_W = 3.5                   # how far the ledge reaches into the opening
BOSS_R = 5.5
BOSS_Z = (67.0, 41.0)           # screw boss heights
CABLE_W, CABLE_H, CABLE_Z = 10.0, 5.0, 26.5
VENT_Z = (50.0, 54.0, 58.0)     # cooling slots in the cover

CHEST_TOP = "IEEE"
CHEST_BOTTOM = "YEDİTEPE"
SHOULDER_BADGE = "7"

# Absolute millimetre dimensions, converted to design units by configure()
SCALE = 1.0
WALL = 3.0
CAV_R = (28.0, 23.0, 27.0)
LID_GAP = 0.3
LEDGE_T = 2.5
SCREW_PILOT = 1.35              # radius, M3 self-tapping into plastic
SCREW_FREE = 1.75               # radius, clearance hole in the cover
SCREW_HEAD = 3.4                # radius, countersink
GROOVE = 0.9                    # panel-line half width


def configure(height_mm=DEFAULT_HEIGHT):
    """Set the design-unit values of everything that must stay absolute in mm."""
    global SCALE, WALL, CAV_R, LID_GAP, LEDGE_T
    global SCREW_PILOT, SCREW_FREE, SCREW_HEAD, GROOVE
    SCALE = height_mm / NATURAL_HEIGHT
    WALL = 3.0 / SCALE
    CAV_R = tuple(r - WALL for r in TORSO_R)
    LID_GAP = 0.3 / SCALE
    LEDGE_T = 2.5 / SCALE
    SCREW_PILOT = 1.35 / SCALE
    SCREW_FREE = 1.75 / SCALE
    SCREW_HEAD = 3.4 / SCALE
    GROOVE = 1.1 / SCALE


configure()


def torso_skin(offset):
    return ell(tuple(r + offset for r in TORSO_R), TORSO_C)


def head_skin(offset):
    return ell(tuple(r + offset for r in HEAD_R), HEAD_C)


def back_surface_y(z):
    """Y of the torso outer surface on the back centreline at height z."""
    t = (z - TORSO_C[2]) / TORSO_R[2]
    return -TORSO_R[1] * float(np.sqrt(max(0.0, 1.0 - t * t)))


# --------------------------------------------------------------------------
# Sub-assemblies
# --------------------------------------------------------------------------
def torso_solid():
    return union(ell(TORSO_R, TORSO_C), ell(HIP_R, HIP_C))


def cavity_solid():
    return ell(CAV_R, TORSO_C)


def legs_and_feet():
    parts = []
    for s in (-1, 1):
        parts.append(limb([(s * 14, 2, 10), (s * 15, 2, 27)], [8.5, 8.5]))
        parts.append(rbox((26, 34, 14), (s * 15, 5, 7), 5.0))
    return union(*parts)


def foot_detail():
    """Sole seam and toe cap line on each boot."""
    cuts = []
    for s in (-1, 1):
        band = diff(rbox((28, 36, 16), (s * 15, 5, 7), 6.0),
                    rbox((24, 32, 12), (s * 15, 5, 7), 4.0))
        cuts.append(inter(band, slab_z(4.2 - GROOVE, 4.2 + GROOVE)))
        toe = creation.box(extents=(40, 2 * GROOVE, 40))
        toe.apply_translation((s * 15, 16.0, 7))
        cuts.append(inter(band, toe))
    return union(*cuts)


def arms():
    parts = []
    for shoulder, elbow, wrist in (ARM_LEFT, ARM_RIGHT):
        shoulder = np.asarray(shoulder, dtype=float)
        elbow = np.asarray(elbow, dtype=float)
        wrist = np.asarray(wrist, dtype=float)
        d_upper, d_fore = unit(elbow - shoulder), unit(wrist - elbow)

        parts.append(limb([shoulder, elbow, wrist], [11.0, 7.5, 6.8]))
        parts.append(hand(wrist, d_fore, (0, 1, 0)))

    for s in (-1, 1):
        parts.append(rod((s * 26, 0, 72), (s * 31, 0, 71), 9.0, caps=False))
    return union(*parts)


def joint_grooves():
    """Panel lines around the legs; the arms are left plain."""
    cuts = [
        # knees and ankles
        ring_groove((-15, 2, 25), (0, 0, 1), 8.5, GROOVE),
        ring_groove((15, 2, 25), (0, 0, 1), 8.5, GROOVE),
        ring_groove((-15, 2, 16.5), (0, 0, 1), 8.5, GROOVE),
        ring_groove((15, 2, 16.5), (0, 0, 1), 8.5, GROOVE),
    ]
    return union(*cuts)


def torso_seams():
    """Panel lines on the front of the body, kept clear of the hatch."""
    band = surface_band(TORSO_R, TORSO_C, 1.2, -1.4)
    hip_band = surface_band(HIP_R, HIP_C, 1.2, -1.4)
    front = half_space(1, +1, -12.0)
    cuts = [
        inter(union(band, hip_band), slab_z(34 - GROOVE, 34 + GROOVE), front),
        inter(band, slab_z(72 - GROOVE, 72 + GROOVE), front),
    ]
    return union(*cuts)


def head_solid():
    return union(ell(HEAD_R, HEAD_C), rod((0, 0, 76), (0, 0, 90), 11.0))


def head_point(direction):
    """Where a ray from the head centre leaves the head, and the normal there."""
    d = unit(direction)
    r = np.asarray(HEAD_R, dtype=float)
    c = np.asarray(HEAD_C, dtype=float)
    p = c + d / np.sqrt(np.sum((d / r) ** 2))
    return p, unit((p - c) / r ** 2)


def eyes():
    """Lens, bezel and iris, all built on the head's surface normal.

    Sitting them on the local normal is what keeps the eye evenly proud all
    the way round - an axis-aligned lens digs into the head on its inner side
    and floats off it on the outer one, because the face curves away.
    """
    parts = []
    for s in (-1, 1):
        p, n = head_point((s * EYE_DIR[0], EYE_DIR[1], EYE_DIR[2]))
        m = frame(p, n, (0, 0, 1))          # local X across the face, Z outwards

        lens = ell((EYE_W, EYE_H, EYE_BULGE + EYE_SINK), (0, 0, -EYE_SINK))

        # bezel: an oval ring sitting on the lens, straddling the head surface
        h = 1.6                             # height up the lens where it sits
        k = np.sqrt(1.0 - (h / (EYE_BULGE + EYE_SINK)) ** 2)
        rim = creation.torus((EYE_W + EYE_H) / 2 * k, 1.4, major_sections=96,
                             minor_sections=20)
        rim.apply_scale((2 * EYE_W / (EYE_W + EYE_H), 2 * EYE_H / (EYE_W + EYE_H), 1.0))
        rim.apply_translation((0, 0, h - EYE_SINK))

        iris = ell((4.4, 4.8, 2.0), (0, 0, EYE_BULGE - 2.0 + 0.6))

        parts.append(placed(union(lens, rim, iris), m))
    return union(*parts)


def head_details():
    """Headset discs, mic boom, antennae and the brow ridge."""
    parts = []
    # left side: camera-style lens stack
    parts.append(rod((-24, 0, 110), (-35, 0, 110), 12.0, caps=False))
    parts.append(rod((-35, 0, 110), (-38, 0, 110), 8.0, caps=False))
    parts.append(rod((-38, 0, 110), (-40, 0, 110), 4.5, caps=False))
    # right side: headphone cup
    parts.append(rod((24, 0, 110), (34, 0, 110), 11.5, caps=False))
    parts.append(rod((34, 0, 110), (36.5, 0, 110), 6.0, caps=False))
    # microphone boom curving towards the mouth
    parts.append(limb([(-33, 2, 106), (-30, 14, 101), (-22, 20, 99)], [1.7, 1.7, 2.8]))
    # antennae, with a collar where each leaves the head
    parts.append(limb([(-9, -3, 132), (-20, -7, 148), (-20, -7, 152)], [2.4, 2.4, 4.2]))
    parts.append(rod((-9.6, -3.2, 133), (-11.5, -4.0, 136), 3.6, caps=False))
    parts.append(limb([(10, -3, 133), (20, -6, 146), (20, -6, 149)], [2.2, 2.2, 3.6]))
    parts.append(rod((10.6, -3.2, 134), (12.4, -3.8, 136.5), 3.4, caps=False))
    # brow ridge across the forehead
    brow = inter(surface_band(HEAD_R, HEAD_C, 1.3, -1.0),
                 slab_z(120.5, 123.5),
                 half_space(1, +1, 8.0))
    parts.append(brow)
    return union(*parts)


def head_grooves():
    """Helmet seam, forehead vents and the ring around each side disc."""
    band = surface_band(HEAD_R, HEAD_C, 1.5, -1.4)
    cuts = [inter(band, slab_z(125.6, 128.2))]
    for z in (117.5, 114.0):
        cuts.append(inter(band, slab_z(z - GROOVE, z + GROOVE), half_space(0, -1, -18.0)))
    cuts.append(ring_groove((-31, 0, 110), (1, 0, 0), 12.0, GROOVE))
    cuts.append(ring_groove((30, 0, 110), (1, 0, 0), 11.5, GROOVE))
    return union(*cuts)


def head_panel():
    """Small raised access panel on the forehead."""
    pad = rbox((13, 22, 9), (-14, 14, 126), 2.5)
    return inter(pad, head_skin(1.2))


def smile_cut():
    """Shallow grin: only the bottom 120 deg of a torus is kept."""
    t = ring_groove((0, 25.8, 104.5), (0, 1, 0), 7.5, 1.7)
    keep = creation.box(extents=(60, 40, 12))
    keep.apply_translation((0, 25.8, 95.0))
    return inter(t, keep)


def chest_panel(with_text=True):
    """Raised panel with a recessed field, IEEE and the university name."""
    plate = inter(rbox((40, 22, 32), (0, 17, 52), 6.0), torso_skin(1.6))
    recess = inter(rbox((34, 22, 26), (0, 17, 52), 4.0),
                   surface_band(TORSO_R, TORSO_C, 3.0, 0.8))
    panel = diff(plate, recess)

    studs = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            studs.append(
                creation.cylinder(radius=1.8,
                                  segment=[(sx * 17, 0, 52 + sz * 13), (sx * 17, 40, 52 + sz * 13)],
                                  sections=32)
            )
    panel = union(panel, inter(union(*studs), torso_skin(2.4)))

    if not with_text:
        return panel

    letters = []
    top = text_solid(CHEST_TOP, 9.0, 18.0, (0, 24, 57.5), max_width=30.0)
    bottom = text_solid(CHEST_BOTTOM, 5.0, 18.0, (0, 24, 45.0), max_width=30.0)
    for t in (top, bottom):
        if t is not None:
            letters.append(inter(t, torso_skin(2.6)))
    return union(panel, *letters) if letters else panel


def shoulder_badge(with_text=True):
    """Raised disc with the mascot's number on the left shoulder."""
    disc = rod((-37.5, 0, 68), (-40.5, 0, 68), 6.0, caps=False)
    ring = ring_groove((-40.5, 0, 68), (1, 0, 0), 4.8, GROOVE)
    badge = diff(disc, ring)
    if not with_text:
        return badge
    txt = text_solid(SHOULDER_BADGE, 6.0, 10.0, (-41.5, 0, 68), facing="-X")
    if txt is None:
        return badge
    keep = creation.box(extents=(2.5, 40, 40))
    keep.apply_translation((-41.25, 0, 68))
    return union(badge, inter(txt, keep))


def rivets():
    """Small studs, clipped to an offset of the torso so they stay attached."""
    studs = []
    for s in (-1, 1):
        for pos, r in (((s * 22, 0, 32), 2.4), ((s * 26, 0, 60), 2.2)):
            studs.append(creation.cylinder(radius=r,
                                           segment=[(pos[0], 0, pos[2]), (pos[0], 40, pos[2])],
                                           sections=32))
    return inter(union(*studs), torso_skin(1.2))


# --------------------------------------------------------------------------
# Hatch pieces
# --------------------------------------------------------------------------
def hatch_prism(shrink=0.0, y0=-60.0, y1=8.0):
    p = xz_prism(HATCH_W - shrink, HATCH_H - shrink, max(1.0, HATCH_R - shrink / 2.0), y0, y1)
    p.apply_translation((0, 0, HATCH_Z))
    return p


def ledge():
    """Rim inside the shell that the cover rests against."""
    band = diff(cavity_solid(),
                ell(tuple(r - LEDGE_T for r in CAV_R), TORSO_C))
    outer = xz_prism(HATCH_W + 14, HATCH_H + 15, 8.0, -60, -4)
    inner = xz_prism(HATCH_W - 2 * LEDGE_W, HATCH_H - 2 * LEDGE_W, 4.0, -70, 10)
    outer.apply_translation((0, 0, HATCH_Z))
    inner.apply_translation((0, 0, HATCH_Z))
    return inter(band, diff(outer, inner))


def bosses():
    parts = []
    for z in BOSS_Z:
        cyl = creation.cylinder(radius=BOSS_R, segment=[(0, -8, z), (0, -60, z)], sections=48)
        parts.append(inter(cyl, cavity_solid()))
    return union(*parts)


def screw_pilots():
    return union(
        *[creation.cylinder(radius=SCREW_PILOT, segment=[(0, 2, z), (0, -60, z)], sections=32)
          for z in BOSS_Z]
    )


def cable_slot():
    p = xz_prism(CABLE_W, CABLE_H, 1.6, -60, 10)
    p.apply_translation((0, 0, CABLE_Z))
    return p


def vent_slots():
    cuts = []
    for z in VENT_Z:
        p = xz_prism(18.0, 2.6, 1.2, -60, 10)
        p.apply_translation((0, 0, z))
        cuts.append(p)
    return union(*cuts)


def build_lid(vents=True):
    shell = diff(torso_solid(), cavity_solid())
    lid = inter(shell, hatch_prism(shrink=2 * LID_GAP, y0=-60.0, y1=-6.0))

    # raised border frame on the outer face
    frame_outer = hatch_prism(shrink=3.0, y0=-60.0, y1=-6.0)
    frame_inner = hatch_prism(shrink=9.0, y0=-60.0, y1=-6.0)
    frame = inter(diff(frame_outer, frame_inner), surface_band(TORSO_R, TORSO_C, 1.4, -0.2))
    lid = union(lid, frame)

    cuts = []
    for z in BOSS_Z:
        cuts.append(creation.cylinder(radius=SCREW_FREE, segment=[(0, 5, z), (0, -60, z)],
                                      sections=32))
        cone = creation.cone(radius=SCREW_HEAD, height=SCREW_HEAD, sections=48)
        cone = rot(cone, -90, (1, 0, 0))          # wide face outwards, tip inwards
        cone.apply_translation((0, back_surface_y(z) - 0.6, z))
        cuts.append(cone)
    if vents:
        cuts.append(vent_slots())
    return diff(lid, *cuts)


# --------------------------------------------------------------------------
# Whole figure
# --------------------------------------------------------------------------
def drop_slivers(mesh, keep_fraction=1e-4):
    """Remove zero-volume shells that booleans can leave at tangent surfaces."""
    parts = mesh.split(only_watertight=False)
    if len(parts) <= 1:
        return mesh
    total = abs(mesh.volume)
    with np.errstate(invalid="ignore", divide="ignore"):
        kept = [p for p in parts if abs(p.volume) > total * keep_fraction]
    return kept[0] if len(kept) == 1 else trimesh.util.concatenate(kept)


def cut_below(mesh, z):
    """Slice off everything under z, giving a flat printing base."""
    return diff(mesh, half_space(2, -1, z))


def build_outer(with_text=True):
    figure = union(
        torso_solid(),
        legs_and_feet(),
        arms(),
        head_solid(),
        eyes(),
        head_details(),
        head_panel(),
        chest_panel(with_text),
        shoulder_badge(with_text),
        rivets(),
    )
    return diff(figure, smile_cut(), head_grooves(), joint_grooves(),
                torso_seams(), foot_detail())


def build_all(with_text=True, vents=True, base_trim=2.0):
    outer = build_outer(with_text)

    solid = cut_below(outer, base_trim)

    body = diff(outer, cavity_solid(), hatch_prism())
    body = union(body, ledge(), bosses())
    body = diff(body, screw_pilots(), cable_slot())
    body = cut_below(body, base_trim)

    return drop_slivers(solid), drop_slivers(body), drop_slivers(build_lid(vents))


def report(name, mesh):
    print(
        "%-16s faces=%-7d watertight=%-5s parts=%d volume=%7.1f cm3  bbox=%s"
        % (name, len(mesh.faces), mesh.is_watertight, len(mesh.split(only_watertight=False)),
           mesh.volume / 1000.0, np.round(mesh.extents, 1))
    )


def main():
    ap = argparse.ArgumentParser(description="Generate Tepecan STL files.")
    ap.add_argument("--outdir", default=os.path.join(os.path.dirname(__file__), "stl"))
    ap.add_argument("--height", type=float, default=DEFAULT_HEIGHT,
                    help="printed height in mm, antenna tips included (default 240)")
    ap.add_argument("--no-text", action="store_true", help="skip the embossed lettering")
    ap.add_argument("--no-vents", action="store_true", help="solid cover, no cooling slots")
    args = ap.parse_args()

    configure(args.height)
    print("height %.0f mm -> scale %.3f, wall %.2f mm, %d faces per sphere"
          % (args.height, SCALE, WALL * SCALE, 20480))

    os.makedirs(args.outdir, exist_ok=True)
    solid, body, lid = build_all(with_text=not args.no_text, vents=not args.no_vents)

    outputs = {
        "tepecan_solid": solid,
        "tepecan_body": body,
        "tepecan_lid": rot(lid, -90, (1, 0, 0)),   # cover flat on the bed, outer face up
    }
    for name, mesh in outputs.items():
        mesh.apply_scale(SCALE)
        mesh.apply_translation((0, 0, -mesh.bounds[0][2]))

        # STL stores float32: round to it here, so the slivers that rounding
        # can create are cleaned up before the file is written, not after.
        mesh.vertices = mesh.vertices.astype(np.float32).astype(np.float64)
        mesh.merge_vertices()
        mesh = drop_slivers(mesh)
        trimesh.repair.fix_normals(mesh)

        path = os.path.join(args.outdir, name + ".stl")
        mesh.export(path)

        check = trimesh.load(path)
        if not (check.is_watertight and check.is_winding_consistent
                and len(check.split(only_watertight=False)) == 1 and check.volume > 0):
            raise SystemExit("%s is not a clean printable solid" % path)
        report(name, check)

    com = body.center_mass
    print("body centre of mass x/y = %.1f / %.1f mm (footprint check)" % (com[0], com[1]))
    print("wrote STL files to %s" % os.path.abspath(args.outdir))


if __name__ == "__main__":
    main()
