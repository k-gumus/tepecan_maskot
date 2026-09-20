#!/usr/bin/env python3
"""Tepesu'nun oturan sürümü - bacaklar öne uzanmış, popo tablada.

Ayakta duran figürle tek farkı belden aşağısı: kalça elipsoidi, gövde, kollar
ve kafa aynen duruyor, `legs_and_feet` / `foot_detail` / `joint_grooves` ise
oturan hâline göre yeniden kuruluyor. Böylece göğüs paneli, yazılar, kulaklık,
antenler - hepsi ayaktaki figürle birebir aynı kalıyor.

Oturan duruş baskı için ayakta durandan çok daha iyi:

  * Popo, iki bacağın altı, iki bot tabanı ve sol el aynı düzlemde (BASE)
    kesiliyor. Tabla teması 3000 mm2'nin üstünde; ayakta duran figür iki bot
    tabanıyla duruyordu.
  * Figürün yüksekliği üçte bir azalıyor, yani devrilme momenti de öyle.
  * Sol el yere değiyor: üçüncü dayanak noktası, üstelik havada başlamıyor.

Bölme şeması ayaktakiyle aynı mantıkta ama daha az parça:

  kafa        - boyundan düz kesim, gövdede geçme mili
  govde       - gövde + kalça + bacaklar + botlar + SOL kol, tek parça
  kol_sag_*   - kalkık sağ kol, kendi düzleminden ikiye bölünmüş

Sol kol gövdede kalıyor çünkü eli zaten tablaya değiyor; sağ kol kalkık
olduğu için dirseği boşlukta başlıyor, o yüzden ayrı basılıyor.

    python3 oturan.py [--height 170] [--outdir stl_oturan]
"""

import argparse
import os

import numpy as np
import trimesh

import agtemiz
import parcala as P
import tepecan_model as T
from tepecan_model import (ball, diff, ell, half_space, inter, limb, rbox, rot,
                           ring_groove, slab_z, union)

# --------------------------------------------------------------------------
# Oturan bacak - tasarım birimi
# --------------------------------------------------------------------------
# Taban düzlemi (BASE) kalça elipsoidinin EN ALTINDA değil, 8 birim
# yukarısında. Küre tabanına teğet bir düzlemle kesersen ilk milimetrelerde
# yüzey neredeyse yataya yatıyor: 0.2 mm'lik katman başına 0.7 mm yanal
# kaçış çıkıyor, yani her katmanın duvarı bir öncekinin dışında havada
# başlıyor ve sarkıyor. 8 birim yukarıdan kesince o kaçış 0.19 mm'ye
# düşüyor - duvar genişliğinin yarısı - ve destek gerekmiyor. Yan etkisi
# de iyi: popo yayvanlaşıyor, figür masada devrilmiyor.
BASE = T.HIP_C[2] - T.HIP_R[2] + 8.0    # 25.0

LEG_R = 8.5
# Bacak ekseni tam BASE + LEG_R olsaydı silindir tabana teğet geçerdi:
# temas sıfır genişlikte başlar ve yine yatay bir kaçışla açılırdı. LEG_SINK
# kadar gömüp kesiyoruz, altında 11 birim genişliğinde düz bir pabuç kalıyor.
LEG_SINK = 2.0
LEG_Z = BASE + LEG_R - LEG_SINK
HIP_X, HIP_Y = 15.0, 2.0                # bacağın kalçadan çıktığı yer
ANKLE_X, ANKLE_Y = 17.0, 34.0           # hafif dışa açık
ANKLE_R = 7.6

BOOT = (23.0, 17.0, 23.0)               # genişlik, derinlik, yükseklik (dik)
# Botun tabanı da BASE'in altında: köşe yuvarlaması kesilip yerine keskin
# kenarlı, tam düz bir taban kalıyor.
BOOT_Z = BASE - LEG_SINK
BOOT_Y = 43.0
BOOT_TILT = 14.0                        # derece, burun ileri yatık
BOOT_R = 6.0                            # köşe yuvarlaması

# Oturan figürde sol kol yana uzanıyor, eli yerde. Bilek ayakta durandan
# 4 birim aşağıda ve 5 birim dışarıda: avuç taban düzleminin 4 birim altında
# kalıyor, yani kesildikten sonra tablaya geniş bir pabuçla oturuyor, ama
# parmaklar bacağı sıyırmıyor.
ARM_LEFT = ((-29.0, 0.0, 68.0), (-39.0, 1.0, 52.0), (-38.0, 9.0, 40.0))


def _boot_frame(side):
    """Botu yerinde kuran dönüşüm: önce yatır, sonra tabanı BOOT_Z'ye otur."""
    probe = rbox(BOOT, (0, 0, 0), BOOT_R)
    probe = rot(probe, -BOOT_TILT, (1, 0, 0))
    dz = BOOT_Z - probe.bounds[0][2]
    m = trimesh.transformations.rotation_matrix(np.radians(-BOOT_TILT), (1, 0, 0))
    m = trimesh.transformations.translation_matrix(
        (side * ANKLE_X, BOOT_Y, dz)) @ m
    return m


def _boot(side, size, radius):
    return T.placed(rbox(size, (0, 0, 0), radius), _boot_frame(side))


def legs_and_feet():
    """Öne uzanmış iki baldır ve dik duran botlar."""
    parts = []
    for s in (-1, 1):
        parts.append(limb([(s * HIP_X, HIP_Y, LEG_Z), (s * ANKLE_X, ANKLE_Y, LEG_Z)],
                          [LEG_R, ANKLE_R]))
        parts.append(_boot(s, BOOT, BOOT_R))
    return union(*parts)


def foot_detail():
    """Taban dikişi ve burun çizgisi - botun kendi çerçevesinde kesiliyor."""
    cuts = []
    for s in (-1, 1):
        band = diff(_boot(s, tuple(d + 2.0 for d in BOOT), BOOT_R + 1.0),
                    _boot(s, tuple(d - 2.0 for d in BOOT), BOOT_R - 1.0))
        # taban dikişi: botun ön yüzüne (tabana) paralel, ondan 4 birim içeride
        sole = T.placed(trimesh.creation.box(
            extents=(40.0, 2 * T.GROOVE, 40.0),
            transform=trimesh.transformations.translation_matrix(
                (0.0, BOOT[1] / 2.0 - 4.0, 0.0))), _boot_frame(s))
        cuts.append(inter(band, sole))
        # bilek çizgisi: botun tepesinden 5 birim aşağıda
        collar = T.placed(trimesh.creation.box(
            extents=(40.0, 40.0, 2 * T.GROOVE),
            transform=trimesh.transformations.translation_matrix(
                (0.0, 0.0, BOOT[2] / 2.0 - 5.0))), _boot_frame(s))
        cuts.append(inter(band, collar))
    return union(*cuts)


def joint_grooves():
    """Diz ve bilek halkaları - bacak yatay olduğu için ekseni Y."""
    cuts = []
    for s in (-1, 1):
        for y, r in ((14.0, LEG_R), (24.0, ANKLE_R + 0.4)):
            f = (y - HIP_Y) / (ANKLE_Y - HIP_Y)
            x = s * (HIP_X + (ANKLE_X - HIP_X) * f)
            cuts.append(ring_groove((x, y, LEG_Z), (0, 1, 0), r, T.GROOVE))
    return union(*cuts)


# --------------------------------------------------------------------------
# Kart klipsi
# --------------------------------------------------------------------------
# tepecan_model.card_clip avucun önüne 34 x 7.8 x 26 mm'lik dolu bir levha
# koyuyor: kartın tamamını saran bir cep, yani üç yanı kapalı. Kart 34 mm
# geniş olduğu için cep ondan da geniş olmak zorunda ve sonuç elin kendisi
# kadar büyük bir dikdörtgen - elden çok tabela duruyor.
#
# Buradaki klips cep değil, MANDAL: kartın yalnız alt kenarını tutuyor,
# yanları ve üstü açık. Kart mandaldan geniş olabildiği için mandal elin
# ölçüsüne inebiliyor. Kalınlık 5 mm, köşeler 2.5 mm yuvarlatılmış,
# yükseklik 14 mm - avuçla başparmağın arasına oturuyor, parmak uçlarının
# hizasını geçmiyor.
CLIP_W = 30.0                   # mm, mandalın genişliği (kart 34 mm, taşıyor)
CLIP_T = 5.0                    # mm, mandalın kalınlığı
CLIP_H = 14.0                   # mm, mandalın yüksekliği
CLIP_R = 2.5                    # mm, köşe yuvarlaması
CLIP_GRIP = 5.0                 # mm, yuvanın altında kalan dolu et
# Yuva kartın kendi kalınlığında olursa kart girmiyor: FDM ince yarıkları
# 0.2-0.4 mm dar basıyor. 0.4 mm pay bırakıyoruz.
CLIP_FIT = 0.4                  # mm
CLIP_POS = (8.5, 10.0)          # tasarım birimi, el çerçevesinde (y, z)
# Mandal öne yatık. Dik dursaydı kartın üst yarısı parmak uçlarının tam
# önünden geçerdi: uçlar bu çerçevede y = 8.5'e kadar geliyor, yuva da
# 8.5'te - kart parmaklara çarpıp içeri girmezdi. 15 derece yatınca kart
# uçların 5 mm önünden geçiyor ve elden dışa doğru bakıyor.
CLIP_TILT = 15.0                # derece


def card_clip():
    """Sağ elin kavradığı kart mandalı. (ekle, kes) döner."""
    shoulder, elbow, wrist = T.ARM_RIGHT
    wrist = np.asarray(wrist, dtype=float)
    fr = T.frame(wrist, T.unit(wrist - np.asarray(elbow, dtype=float)), (0, 1, 0))

    y, z = CLIP_POS
    w, t, h = CLIP_W / T.SCALE, CLIP_T / T.SCALE, CLIP_H / T.SCALE
    tilt = trimesh.transformations.rotation_matrix(
        np.radians(-CLIP_TILT), (1, 0, 0), (0.0, y, z))
    block = rbox((w, t, h), (0.0, y, z), CLIP_R / T.SCALE)

    # Yuva mandaldan geniş: kart iki yandan taşıyor, cep değil mandal oluyor.
    # Üstten de açık, kart yukarıdan sokuluyor. Yuvanın üstü mandalın tepesini
    # yalnız 2 mm aşıyor: daha yukarı uzatmak parmak uçlarını da yarıyordu
    # (uçlar bu çerçevede y = 8.8'e kadar geliyor, yuva ise y = 8.5'te).
    over = 2.0 / T.SCALE
    depth = h - CLIP_GRIP / T.SCALE + over
    # Yuva mandaldan yalnız 0.6 mm geniş. Daha genişi başparmağın ucunu da
    # kesip modelden kopardı (ölçüldü): kart zaten mandaldan taşıyor, yuvanın
    # kartı kadar geniş olması gerekmiyor.
    slot = trimesh.creation.box(extents=(w + 0.6 / T.SCALE,
                                        T.CARD_T + CLIP_FIT / T.SCALE, depth))
    slot.apply_translation((0.0, y, z - h / 2.0 + CLIP_GRIP / T.SCALE + depth / 2.0))
    return T.placed(block, fr @ tilt), T.placed(slot, fr @ tilt)


# --------------------------------------------------------------------------
# Tüylü yüzey (fuzzy skin) payı
# --------------------------------------------------------------------------
# Tüylü yüzey dilimleyicide duvarın her noktasını kendi normali boyunca
# rastgele +-FUZZ/2 kaydırıyor. Düz yüzeyde zararsız ama GEÇMELERDE değil:
# boyun mili bir duvar, kafadaki yuvası da bir duvar. Mil yarıçapı +FUZZ/2
# büyürken yuva -FUZZ/2 daralıyor, yani nominal boşluk FUZZ kadar yeniyor.
# 0.3 mm'lik tüyle 0.25 mm'lik geçme payı eksiye düşüyor ve kafa boyna
# hiç girmiyor. O yüzden oturan sürümde pay FUZZ kadar büyütülüyor.
#
# Yapıştırma yüzeylerinin hepsi duvar değil: kolun kesik yüzü ve kafanın
# boyun kesiti tabla/tavan yüzeyi, onlara tüy vurulmuyor. Büyütülmesi
# gereken yalnız mil-yuva çifti ile kolun omuza oturduğu eyer yüzeyi.
FUZZ = 0.3                      # mm, fuzzy_skin_thickness ile aynı değer
FIT = 0.25 + FUZZ               # mm, mil/yuva arası yarıçap payı
GAP_ARM = P.GAP_ARM + FUZZ      # mm, kolun omuz yüzeyinden kaçışı


def fit():
    return FIT / T.SCALE


# --------------------------------------------------------------------------
# Figür
# --------------------------------------------------------------------------
def figure(with_text=True, left_arm=True):
    """Tepesu: kavitesiz, ızgarasız; sağ elde kart klipsi."""
    parts = [T.torso_solid(), legs_and_feet(), T.head_solid(), T.eyes(),
             T.head_details(), T.head_panel(), T.chest_panel(with_text),
             T.rivets()]
    if left_arm:
        parts.append(P.arm_envelope(ARM_LEFT, -1, with_text))
    body = union(*parts)
    return diff(body, T.smile_cut(), T.head_grooves(), joint_grooves(),
                T.torso_seams(), foot_detail())


def right_arm(with_text=True):
    """Kalkık sağ kol + avucun önündeki kart klipsi, gövdeden ayrılmış."""
    add, cut = card_clip()
    env = union(P.arm_envelope(T.ARM_RIGHT, +1, with_text), add)
    arm = P.biggest(diff(env, P.torso_hull(GAP_ARM / T.SCALE)))
    return diff(arm, cut)


def build_parts(with_text=True):
    out = {}

    # Bölme parcala.split_arm ile aynı: avuç düzleminden, kesik yüz aşağı.
    for suffix, half in P.split_arm(right_arm(with_text), T.ARM_RIGHT).items():
        out["kol_sag" + suffix] = half

    body = T.cut_below(figure(with_text), BASE)

    f = fit()
    head = P.biggest(inter(body, half_space(2, +1, P.NECK_Z)))
    body = P.biggest(inter(body, half_space(2, -1, P.NECK_Z)))
    body = union(body, P.cyl(P.SPIGOT_R, P.NECK_Z - P.SINK, P.NECK_Z + P.SPIGOT_H))
    head = diff(head, P.cyl(P.SPIGOT_R + f, P.NECK_Z - 1.0,
                            P.NECK_Z + P.SPIGOT_H + f))
    out["kafa"] = P.biggest(head)
    out["govde"] = P.biggest(body)
    return out


def natural_height():
    """Oturan figürün ölçeklenmemiş yüksekliği - --height bunun karşılığı."""
    return T.head_details().bounds[1][2] - BASE


# --------------------------------------------------------------------------
# Dışa aktarma
# --------------------------------------------------------------------------
DEFAULT_SIT_HEIGHT = 170.0      # mm, oturan figürün anten ucuna kadar boyu


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Oturan Tepesu'yu basılabilir parçalara böl.")
    ap.add_argument("--outdir", default=os.path.join(here, "stl_oturan"))
    ap.add_argument("--height", type=float, default=DEFAULT_SIT_HEIGHT,
                    help="basılan oturan figürün mm cinsinden boyu")
    ap.add_argument("--no-text", action="store_true")
    args = ap.parse_args()

    # Ölçek iki adımda: configure() ayakta duran figürün doğal boyuna göre
    # ölçek kuruyor, oysa istenen boy oturan figürün. Önce herhangi bir
    # ölçekle kurup oturan doğal boyu ölçüyoruz, sonra ölçeği ona göre
    # tazeliyoruz - mm cinsinden sabit kalması gereken her şey (kart yuvası,
    # geçme boşluğu, oluk genişliği) böylece doğru kalıyor.
    T.configure(T.DEFAULT_HEIGHT)
    natural = natural_height()
    T.configure(T.NATURAL_HEIGHT * args.height / natural)
    print("oturan boy %.0f mm -> ölçek %.3f (doğal %.1f birim)"
          % (args.height, T.SCALE, natural))

    os.makedirs(args.outdir, exist_ok=True)
    for name, mesh in build_parts(with_text=not args.no_text).items():
        mesh.apply_scale(T.SCALE)
        mesh.apply_translation((0, 0, -mesh.bounds[0][2]))
        mesh = agtemiz.temizle(P.biggest(P.heal(mesh)))
        mesh.vertices = mesh.vertices.astype(np.float32).astype(np.float64)
        mesh = agtemiz.snap(mesh)
        trimesh.repair.fix_normals(mesh)

        path = os.path.join(args.outdir, "tepesu_" + name + ".stl")
        mesh.export(path)

        check = trimesh.load(path)
        if not (check.is_watertight and check.is_winding_consistent
                and len(check.split(only_watertight=False)) == 1 and check.volume > 0):
            raise SystemExit("%s temiz bir katı değil" % path)
        bad = agtemiz.open_contour_layers(check)
        if bad:
            raise SystemExit("%s: %d katmanda kontur kapanmıyor, ilki z=%.2f"
                             % (path, len(bad), bad[0]))
        P.slice_check(path, check)
        print("   ilk katman %.0f mm2" % P.first_layer_area(check))
        T.report(name, check)


if __name__ == "__main__":
    main()
