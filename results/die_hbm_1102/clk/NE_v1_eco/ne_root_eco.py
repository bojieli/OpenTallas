#!/usr/bin/env python3
"""DIE-HBM-58/CLK one-block DRC fix for the full-hub NE_v1 DRT (NDR w0.04): the 2 M9 Min Step markers are the
80-nm root pin pad (x 3764.880-3764.960, y 630.680-630.760) meeting the 40-nm n_root wire (x 3764.896-3764.936):
shoulders 16/24 nm < MINSTEP 0.04.  Patch = one M9 RECT on n_root covering pad + wire + VIA89 M9 pad
(x 3764.880-3764.960, y 630.096-630.760): the union of all n_root M9 shapes becomes one 80 x 664 nm rectangle (no edge
< 40 nm); nearest foreign M9 = PG stripe 1.8 um away (NDR spacing 0.32 kept, patch widens <= 24 nm).
usage: ne_root_eco.py IN_drt.def OUT_drt_eco.def"""
import sys
s = open(sys.argv[1]).read()
old = "      NEW M9 ( 3764916 630116 ) ( * 630716 0 )\n"
assert s.count(old) == 1
open(sys.argv[2], "w").write(s.replace(old, old + "      NEW M9 ( 3764920 630096 ) RECT ( -40 0 40 664 )\n"))
print("patched")
