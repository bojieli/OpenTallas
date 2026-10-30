#!/usr/bin/env python3
"""DIE-HBM-21: host_cp_rxs SRAM-edge probe kits (synth reused).  mk_rxs.py KITDIR VARIANT
Macros moved off the pin-heavy N face; rd_out (R0 W edge / MY E edge) faces the logic; core tree leaf islands moved
off the macros (probe only: the re-kit regenerates them from the plan)."""
import sys, re, glob, os
K, V = sys.argv[1], sys.argv[2]
LK, LD = "ot_sram_1r1w_64x512_m1_r2c2", "ot_sram_1r1w_256x256_m2_r2c2"
WK, WD, HK, HD = 171.288, 172.824, 77.784, 41.064
n = {"l0": r"u_fcore.u_link.g_bank\[0\].u_store.u_native.u_sram", "l1": r"u_fcore.u_link.g_bank\[1\].u_store.u_native.u_sram",
     "l2": r"u_fcore.u_link.g_bank\[2\].u_store.u_native.u_sram", "l3": r"u_fcore.u_link.g_bank\[3\].u_store.u_native.u_sram",
     "d0": r"u_fcore.u_land.g_bank\[0\].u_mem", "d1": r"u_fcore.u_land.g_bank\[1\].u_mem"}
m = lambda k: LK if k[0] == "l" else LD
h = lambda k: HK if k[0] == "l" else HD
def column(order, x, orient, right=None):
    y, out = 15.12, []
    for k in order:
        xx = x if right is None else round(right - (WK if k[0] == "l" else WD), 3)
        out.append((k, xx, round(y, 3), orient)); y += h(k) + 8.64
    return out
W = 434.808
if V == "RD":   # one W column, MY: rd_out faces E into a 232-um logic field under the N pins
    mac = column(["l3", "d0", "d1", "l2", "l1", "l0"], 15.12, "MY")
    isl = {1: (250.56, None), 2: (250.56, None), 3: (250.56, None), 4: (250.56, None), 5: (362.88, None), 6: (362.88, None), 7: (362.88, None), 8: (362.88, None)}
elif V == "RB": # 2 x 3 in the S half, rd_out faces a 58.9-um centre channel (GEOM-65 sketch)
    mac = column(["l3", "l2", "d0"], 15.12, "MY") + column(["l1", "l0", "d1"], None, "R0", right=W - 15.12)
    isl = {1: (198.72, 60.48), 5: (233.28, 60.48), 2: (198.72, 151.2), 6: (233.28, 151.2)}
else: raise SystemExit("variant")
with open(K + "/macro_placement.tcl", "w") as f:
    f.write("foreach {inst master x y orient} {\n")
    for k, x, y, o in mac: f.write("  {%s} %s %s %s %s\n" % (n[k], m(k), x, y, o))
    f.write("} {\n  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact\n}\n")
# move leaf islands: island i centre (108|324, 60.48|181.44|298.08|419.04)
old = {i: ((108.0 if i <= 4 else 324.0), [60.48, 181.44, 298.08, 419.04][(i - 1) % 4]) for i in range(1, 9)}
t = open(K + "/master_core_infra.tcl").read().split("\n"); o2 = []
for l in t:
    mm = re.search(r"mp_isl(\d)_", l)
    if mm and int(mm.group(1)) in isl:
        i = int(mm.group(1)); nx, ny = isl[i]; ox, oy = old[i]; dx = nx - ox; dy = 0 if ny is None else ny - oy
        nums = lambda s: re.sub(r"(-?\d+\.?\d*)", lambda q: "%g" % round(float(q.group(1)) + (dx if nums.ix % 2 == 0 else dy), 3) if not nums.__setattr__("ix", nums.ix + 1) else "", s)
        if l.startswith("ot_ci_port"):
            a = l.split(); a[3] = "%g" % round(float(a[3]) + dx, 3); a[4] = "%g" % round(float(a[4]) + dy, 3); l = " ".join(a)
        elif l.startswith("ot_ci_cell"):
            a, r = l.split("{", 2)[0:2], l
            p = l.split(); p[3] = "%g" % round(float(p[3]) + dx, 3); p[4] = "%g" % round(float(p[4]) + dy, 3)
            box = [float(v.strip("{}")) for v in p[5:9]]; box = [box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy]
            l = " ".join(p[:5]) + " {" + " ".join("%g" % round(v, 3) for v in box) + "}"
    o2.append(l)
open(K + "/master_core_infra.tcl", "w").write("\n".join(o2))
print(V, mac)
