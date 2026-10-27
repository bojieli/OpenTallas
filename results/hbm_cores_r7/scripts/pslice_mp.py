#!/usr/bin/env python3
"""HBM-CORES-R7: plan-computed explicit macro placement for ot_hbm_su_programme_pslice_c5 (939.6 x 760.32).
MPL-0003 (RTL-MP: no valid tiling at 3.7 % std-cell util, 55 % macro area) -> fixed placement:
100 x ot_sram_1r1w_128x256_m1_r2c2 (94.824 x 41.064, pins M4 on the W and E edges only, OBS M1-M4 full).
8 vertical stacks on the 4.32 lattice (x0 = 12.96 + s*116.64 -> 21.816-um pin channels between stacks, both
macro pin edges face a channel), macros abutted in y on the row grid (pitch 41.31 = 153 rows, gap 0.246 < 1 row,
no std-cell slivers), stack origin y 12.96.  Stack order = boustrophedon over g_c[0..9] so each programme column's
SRAMs stay contiguous.  N band y 549.8..756 = std-cell band under the 2470 N-face command pins; W/E edge channels for
the 302 W cfg pins / 16 E pins.  Clock entry island (466.56..475.2, 375.84..384.48) lies in the channel between
stacks 3 and 4 (457.70 .. 479.52) clear of the 4.32 halo.
usage: pslice_mp.py NETLIST OUT.json [render.png]"""
import json, re, sys
net, out = sys.argv[1], sys.argv[2]
MW, MH = 94.824, 41.064
X0, XP, Y0, YP, NS, NR = 12.96, 116.64, 12.96, 41.31, 8, 13
names = sorted(set(re.findall(r"ot_sram_1r1w_128x256_m1_r2c2 \\(\S+)", open(net).read())))
def key(n):
    m = re.search(r"g_c\[(\d+)\].*g_m4\.(dt|ix)\[(\d+)\]\.mem\.g\[(\d+)\]", n)
    return (int(m.group(1)), m.group(2) != "dt", int(m.group(3)), int(m.group(4)))
names.sort(key=key)
assert len(names) == 100, len(names)
names = [n[len("u_fcore."):] if n.startswith("u_fcore.") else n for n in names]
slots = []
for s in range(NS):
    rows = range(NR) if s % 2 == 0 else range(NR - 1, -1, -1)
    for r in rows:
        slots.append((round(X0 + s * XP, 4), round(Y0 + r * YP, 4)))
mp = []
for i, n in enumerate(names):
    x, y = slots[i]
    assert abs((x - 4.32) / 0.054 - round((x - 4.32) / 0.054)) < 1e-6 and abs((y - 4.32) / 0.27 - round((y - 4.32) / 0.27)) < 1e-6
    mp.append(dict(k=n, macro="ot_sram_1r1w_128x256_m1_r2c2", origin_um=[x, y], orient="R0", stack=i // NR if True else 0))
# checks: inside core, no overlap, clock island clear of halo
core = (4.32, 4.32, 935.28, 756.0)
for m in mp:
    x, y = m["origin_um"]; assert core[0] <= x and x + MW <= core[2] and core[1] <= y and y + MH <= core[3], m
rects = [(m["origin_um"][0], m["origin_um"][1], m["origin_um"][0] + MW, m["origin_um"][1] + MH) for m in mp]
for i in range(len(rects)):
    for j in range(i + 1, len(rects)):
        a, b = rects[i], rects[j]
        assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], (i, j)
isl = (466.56, 375.84, 475.2, 384.48)
for r in rects:
    h = (r[0] - 4.32, r[1] - 4.32, r[2] + 4.32, r[3] + 4.32)
    assert h[2] <= isl[0] or isl[2] <= h[0] or h[3] <= isl[1] or isl[3] <= h[1], ("island under halo", r)
json.dump(dict(schema="opentallas.macro_placement.v1", design="ot_hbm_su_programme_pslice_c5", outline_um=[939.6, 760.32],
               rule=__doc__.split("usage")[0].strip(), macro_placement=mp,
               stacks=NS, rows=NR, channel_um=round(XP - MW, 3), n_band_um=[round(Y0 + (NR - 1) * YP + MH, 3), 756.0]),
          open(out, "w"), indent=1)
print("macros", len(mp), "channel", round(XP - MW, 3), "stack top", round(Y0 + (NR - 1) * YP + MH, 3))
if len(sys.argv) > 3:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt; from matplotlib.patches import Rectangle
    pins = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else []
    f, ax = plt.subplots(figsize=(10, 8.2)); ax.add_patch(Rectangle((0, 0), 939.6, 760.32, fill=False))
    ax.add_patch(Rectangle(core[:2], core[2] - core[0], core[3] - core[1], fill=False, ls=":"))
    cols = plt.cm.tab10.colors
    for m, r in zip(mp, rects):
        c = int(re.search(r"g_c\[(\d+)\]", m["k"]).group(1))
        ax.add_patch(Rectangle(r[:2], MW, MH, fc=cols[c % 10], ec="k", lw=0.3, alpha=0.7))
    ax.add_patch(Rectangle(isl[:2], 8.64, 8.64, fc="red"))
    for p in pins:
        ax.plot(p["x"], p["y"], ",", color="b")
    ax.set_aspect("equal"); ax.set_title("pslice_c5 plan macro placement (colour = g_c column; red = clock island; dots = pins)")
    f.savefig(sys.argv[3], dpi=110, bbox_inches="tight")
