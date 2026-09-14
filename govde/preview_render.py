#!/usr/bin/env python3
"""
Quick offscreen previews of the generated STL files (no OpenGL needed).

    python3 preview_render.py

Writes preview/tepecan_views.png and preview/tepecan_hatch.png.
"""

import os
import sys

import numpy as np
import trimesh
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

HERE = os.path.dirname(os.path.abspath(__file__))
BG = "#12161c"


def view(ax, mesh, azim, elev=8, color=(0.20, 0.45, 0.80), title=""):
    """Painter's-algorithm render of a mesh from a given azimuth/elevation."""
    a, e = np.radians(azim), np.radians(elev)
    d = np.array([np.sin(a) * np.cos(e), -np.cos(a) * np.cos(e), np.sin(e)])
    up = np.array([0.0, 0.0, 1.0])
    right = np.cross(d, up)
    right /= np.linalg.norm(right)
    up = np.cross(right, d)

    v = mesh.vertices
    x, y, z = v @ right, v @ up, v @ d
    tri = mesh.faces
    n = mesh.face_normals
    keep = np.argsort(-z[tri].mean(axis=1))
    keep = keep[(n[keep] @ d) < 0]

    light = -d * 0.7 + np.array([0.3, 0.2, 0.75])
    light /= np.linalg.norm(light)
    shade = np.clip(n[keep] @ light, 0, 1) * 0.75 + 0.25

    ax.add_collection(
        PolyCollection(
            np.stack([x[tri[keep]], y[tri[keep]]], axis=-1),
            facecolors=np.clip(np.array(color)[None, :] * shade[:, None], 0, 1),
            edgecolors="none",
        )
    )
    ax.set_xlim(x.min() - 5, x.max() + 5)
    ax.set_ylim(y.min() - 5, y.max() + 5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=9, color="#dfe6ef")


def main():
    stl = os.path.join(HERE, "stl")
    out = os.path.join(HERE, "preview")
    os.makedirs(out, exist_ok=True)
    if not os.path.exists(os.path.join(stl, "tepecan_solid.stl")):
        sys.exit("run tepecan_model.py first")

    solid = trimesh.load(os.path.join(stl, "tepecan_solid.stl"))
    body = trimesh.load(os.path.join(stl, "tepecan_body.stl"))
    lid = trimesh.load(os.path.join(stl, "tepecan_lid.stl"))

    views = [(0, "front"), (35, "3/4"), (90, "side"), (180, "back")]
    fig, axes = plt.subplots(1, len(views), figsize=(3.1 * len(views), 6.4), facecolor=BG)
    for ax, (az, t) in zip(axes, views):
        ax.set_facecolor(BG)
        view(ax, solid, az, title=t)
    plt.tight_layout()
    fig.savefig(os.path.join(out, "tepecan_views.png"), dpi=110, facecolor=BG)

    fig, axes = plt.subplots(1, 3, figsize=(12, 6), facecolor=BG)
    for ax in axes:
        ax.set_facecolor(BG)
    view(axes[0], body, 180, elev=6, title="hatch opening")
    axes[0].set_xlim(-45, 45)
    axes[0].set_ylim(10, 110)
    view(axes[1], body, 205, elev=25, title="compartment")
    view(axes[2], lid, 200, elev=35, color=(0.85, 0.55, 0.15), title="cover, print orientation")
    plt.tight_layout()
    fig.savefig(os.path.join(out, "tepecan_hatch.png"), dpi=115, facecolor=BG)

    # iç yerleşim: gövdeyi kesip elektroniğin oturduğu yeri göster
    def cut_at(mesh, axis, keep_positive, at):
        e = [400.0, 400.0, 400.0]
        t = [0.0, 0.0, 0.0]
        t[axis] = at + (-200.0 if keep_positive else 200.0)
        box = trimesh.creation.box(
            extents=e, transform=trimesh.transformations.translation_matrix(t))
        return trimesh.boolean.difference([mesh, box], engine="manifold")

    fig, axes = plt.subplots(1, 2, figsize=(12, 6.6), facecolor=BG)
    for ax in axes:
        ax.set_facecolor(BG)
    view(axes[0], cut_at(body, 0, True, 0.0), 90, elev=3,
         title="dikey kesit — hoparlör adası, kart kuleleri, vida boss'ları")
    axes[0].set_xlim(-45, 45)
    axes[0].set_ylim(20, 130)
    view(axes[1], cut_at(body, 1, True, -14.0), 196, elev=20,
         title="bölme — kapak açıkken içeriden")
    axes[1].set_xlim(-46, 46)
    axes[1].set_ylim(18, 128)
    plt.tight_layout()
    fig.savefig(os.path.join(out, "tepecan_ic.png"), dpi=115, facecolor=BG)
    print("wrote previews to", out)


if __name__ == "__main__":
    main()
