"""DIE-HBM-10 C23 PHY_N split, ESTIMATE input: PC-aligned group geometry for the CA bound.
Groups (PHY window 265.6 um per pseudo-channel, PHY_N margin 152.1 um each side of the 8500-um macro):
  W = PC 0-7  (152.1 + 8 x 265.6 = 2276.9 um), C = PC 8-23 (16 x 265.6 = 4249.6 um), E = PC 24-31 (mirror of W).
The DIE-HBM-9 split feed (hbm9/retree/hbm_feed_split.tsv) assumed equal thirds (~2934.7 um). Region insertion
(centre -> farthest leaf) is scaled by the half-width change at the shared wire model V = 0.3659 ps/um; the feed taps
stay (W/E enter at the PHY_N outer edges, C at the centre bottom).
usage: mk_feed_c23.py SRC_FEED OUT_FEED"""
import csv, sys
src, out = sys.argv[1:3]
R = list(csv.DictReader(open(src), delimiter="\t")); V = 0.3659
third = 8804.16 / 3
wW = 152.1 + 8 * 265.6; wC = 16 * 265.6
d = {"T060C": (wC - third) / 2, "T060W": (wW - third) / 2, "T060E": (wW - third) / 2}
for r in R:
    if r["child_region"] in d:
        r["ins_ps"] = f"{float(r['ins_ps']) + d[r['child_region']] * V:.1f}"
        print(r["child_region"], r["ins_ps"], r["feed_tap_xy_um"])
w = csv.DictWriter(open(out, "w"), fieldnames=list(R[0].keys()), delimiter="\t"); w.writeheader(); w.writerows(R)
