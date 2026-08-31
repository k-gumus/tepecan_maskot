# Tepecan için hazır prompt'lar

## 1) AI 3B model araçları (Meshy / Tripo / Sloyd / Rodin) — görselden model

Bu araçlara `reference/tepecan_reference.jpg` görselini **image-to-3D** modunda
yükleyin, ardından açıklama alanına:

> Chibi mascot robot character, full body, standing, with the
> right arm raised in a fist. Big round helmet-like head, two large oval anime
> eyes with raised metallic rims, small curved smile, two thin antennae with
> spherical tips, round headphone/camera discs on both sides of the head.
> Rounded egg-shaped torso with a flat chest panel, short stubby arms with
> mitten fists, short legs with chunky flat-bottomed boots. Smooth hard-surface
> plastic robot toy, closed clean surfaces, no thin fins, no floating parts,
> no text. Single watertight solid, manifold, printable, flat base.
> Style: vinyl designer toy / collectible figurine.

Negatif prompt (destekliyorsa):

> thin fragile parts, floating geometry, holes in surface, open shell,
> hair strands, cloth, sharp spikes, text, logos

Sonrasında **Remesh → Watertight/Solid** ve **Export → STL (mm)** seçin,
yüksekliği 150 mm'ye ölçekleyin. Bu araçlar içi boş bölme ve vida kulağı
üretmez; onu Blender/Fusion/Tinkercad'de eklemek gerekir (bkz. 2. prompt).

## 2) Kod üreten bir asistana (Claude / ChatGPT) — parametrik ve kesin sonuç

> Write a Python script using trimesh + manifold3d that builds a 3D-printable
> chibi mascot robot and exports STL files. Build everything with CSG on
> watertight primitives (icospheres scaled into ellipsoids, capsules, rounded
> boxes made from convex hulls of corner spheres) so the result is manifold.
>
> Figure (design units, Z up, +Y = front): egg-shaped torso ellipsoid
> r=(31,26,30) at z=52 plus a hip ellipsoid r=(27,23,15) at z=32; head
> ellipsoid r=(31,29,28) at z=110; two eye ellipsoids r=(9,7.5,10.5) at
> (±13,21.5,112) with torus rims and raised iris discs; a shallow smile groove
> cut with a torus arc; headphone/camera discs on both sides of the head; a
> microphone boom; two antennae with ball tips and collars; stubby arms with
> ball fists, one raised; short legs with rounded-box boots; the base sliced
> flat at z=2. Natural height ~154 units; scale the exported meshes so the
> printed figure is 240 mm tall.
>
> Add surface detail by intersecting thin offset shells of a body with slabs
> and prisms: a helmet seam and vent lines on the head, a brow ridge, panel
> lines on the belly and chest, ring grooves at every elbow, wrist and knee,
> sole and toe seams on the boots, a raised chest panel with a recessed field
> carrying embossed "IEEE" and "YEDİTEPE", rivet studs, and a numbered badge
> disc on the left shoulder.
>
> Then make an electronics compartment: hollow the torso with an inner
> ellipsoid one wall thickness smaller (wall 3 mm at the printed size), cut a
> 38 x 40 unit rounded opening in the back, add a seating ledge that reaches
> into the opening, add two screw bosses with 2.7 mm pilot holes, and cut a
> cable slot below the opening. Build the cover as the intersection of the
> torso shell with the opening prism shrunk by 0.6 units (0.3 mm clearance per
> side), give it a raised border frame, three vent slots and countersunk
> 3.5 mm clearance holes.
>
> Keep wall thickness, screw holes and cover clearance absolute in mm: divide
> them by the export scale factor before building, so an M3 screw stays M3 at
> any figure height.
>
> Export tepecan_solid.stl (display figure), tepecan_body.stl and
> tepecan_lid.stl (cover rotated flat for printing). Round vertices to float32
> before writing (that is what STL stores), drop the zero-volume shells that
> booleans leave at tangent surfaces, then read each file back and assert it is
> watertight, winding-consistent, a single connected component and of positive
> volume.

Bu depodaki `tepecan_model.py` tam olarak bunun sonucudur; istersen doğrudan
onu çalıştırmak en hızlısı.
