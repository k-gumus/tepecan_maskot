#!/usr/bin/env python3
"""Oturan Tepesu için baskı plakaları. Yerleşim ve denetim plakalar.py'den.

    python3 oturan.py && python3 plakalar_oturan.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plakalar as PL                                            # noqa: E402

SRC = os.path.join(HERE, "stl_oturan")


def S(name):
    return os.path.join(SRC, "tepesu_%s.stl" % name)


def main():
    os.makedirs(PL.OUT, exist_ok=True)
    bad = 0
    print("plaka 1 - gövde ve kafa")
    bad += PL.yaz(os.path.join(PL.OUT, "oturan_plaka1_govde_kafa.3mf"),
                  [("govde", S("govde")), ("kafa", S("kafa"))])
    print("plaka 2 - sağ kol")
    bad += PL.yaz(os.path.join(PL.OUT, "oturan_plaka2_sag_kol.3mf"),
                  [("kol_sag_on", S("kol_sag_on")), ("kol_sag_arka", S("kol_sag_arka"))])
    print("TÜM PLAKALAR - dikilemeyecek toplam kopukluk:", bad)


if __name__ == "__main__":
    main()
