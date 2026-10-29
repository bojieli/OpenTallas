#!/usr/bin/env python3
"""DIE-HBM-19 SPB V3_stagger3: rewrite the 512 phy_rx M7 pin rects of the V1/A probe macros.lef into 3 rows
(y 634.848 / 565.728 / 496.608, rel x 3.984 + 0.192*floor(i/3), 0.032 x 0.192). usage: stagger3.py IN.lef OUT.lef"""
import re, sys
t = open(sys.argv[1]).read(); Y = [634.848, 565.728, 496.608]
def f(m):
    i = int(m.group(1)); x = 3.984 + (i // 3) * 0.192; y = Y[i % 3]
    return "PIN rx[%d]%sRECT %.6f %.6f %.6f %.6f ;" % (i, m.group(2), x, y, x + 0.032, y + 0.192)
t2, n = re.subn(r"PIN rx\[(\d+)\](\s+DIRECTION OUTPUT ;\s+USE SIGNAL ;\s+PORT\s+LAYER M7 ;\s+)RECT [\d.]+ [\d.]+ [\d.]+ [\d.]+ ;", f, t)
assert n == 512; open(sys.argv[2], "w").write(t2)
