#!/usr/bin/env python3
"""Oturan Tepesu'nun hızlı önizlemesi (OpenGL gerektirmez).

    python3 oturan_onizleme.py     ->  preview/tepesu_oturan.png
"""
import os
import sys

import matplotlib
import numpy as np
import trimesh

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from preview_render import BG, view                              # noqa: E402

import oturan as O                                               # noqa: E402
import tepecan_model as T                                        # noqa: E402

VIEWS = [(0, 10, "ön"), (40, 14, "çeyrek"), (90, 6, "yan"), (200, 12, "arka")]


def main():
    T.configure(T.DEFAULT_HEIGHT)
    figure = trimesh.util.concatenate([T.cut_below(O.figure(), O.BASE),
                                       O.right_arm()])

    out = os.path.join(HERE, "preview")
    os.makedirs(out, exist_ok=True)
    fig, axes = plt.subplots(1, len(VIEWS), figsize=(4.2 * len(VIEWS), 6.2),
                             facecolor=BG)
    for ax, (az, el, title) in zip(axes, VIEWS):
        ax.set_facecolor(BG)
        view(ax, figure, az, el, color=(0.88, 0.42, 0.62), title=title)
    fig.suptitle("Tepesu - oturan duruş  (%.0f x %.0f x %.0f birim)"
                 % tuple(np.round(figure.extents)), color="#dfe6ef", fontsize=11)
    plt.tight_layout()
    path = os.path.join(out, "tepesu_oturan.png")
    plt.savefig(path, dpi=120, facecolor=BG)
    print("yazıldı:", path)


if __name__ == "__main__":
    main()
