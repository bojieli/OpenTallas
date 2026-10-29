"""DIE-HBM-10 C23b ESTIMATE: PHY_N 2-way split W = PC 0-15 (NW hub) / E = PC 16-31 (NE hub) after the C23 3-way plan hit
the vsN6 face capacity (L22 + L22m via the centre column need +732 um of window; vsN6 has 664 um free of 1684.8).
All NW-hub PHY traffic (L8, L9, L21, L22, L63, L114) takes the W path hub -> spu0 -> spt0..2 -> mcb -> PHY_NW (the L8 /
L21 chain); mirror for NE.  The vsN4..6 column then carries no PHY bus.  Region tree: T060W child of T059 (W face tap),
T060E child of T061; T060C removed.  Region insertion scaled from the C23 W third by the half-width change at V = 0.3659.
usage: mk_var_c23b.py RETREE_DIR C23_FEED OUTDIR"""
import csv, sys, os
rd, c23feed, od = sys.argv[1:4]; os.makedirs(od, exist_ok=True)
F = list(csv.DictReader(open(c23feed), delimiter="\t"))
X = list(csv.DictReader(open(f"{rd}/hbm_xings_split.tsv"), delimiter="\t"))
V = 0.3659; wW3 = 152.1 + 8 * 265.6; wH = 8804.16 / 2
feed = []
for r in F:
    r = dict(r)
    if r["child_region"] == "T060C": continue
    if r["child_region"] in ("T060W", "T060E"):
        r["ins_ps"] = f"{float(r['ins_ps']) + (wH - wW3) / 2 * V:.1f}"; r["w_mm"] = f"{wH / 1000:.2f}"
    feed.append(r)
moved = ("L9", "L63", "L114")
def base(p): return p.rsplit("_", 1)[0]
keep = [dict(r) for r in X if base(r["port"]) not in moved + tuple(m + "m" for m in moved)]
tmpl = {k: [r for r in X if base(r["port"]) == k] for k in ("L8", "L8m", "L21", "L21m")}
add = []
for bus, t, bits in (("L9", "L8", 2456), ("L9m", "L8m", 2456), ("L63", "L8", 336), ("L63m", "L8m", 336),
                     ("L114", "L21", 16), ("L114m", "L21m", 16)):
    for r in tmpl[t]:
        r = dict(r); r["port"] = bus + "_" + r["port"].rsplit("_", 1)[1]; r["bits"] = str(bits); add.append(r)
with open(f"{od}/feed_c23b.tsv", "w") as f:
    w = csv.DictWriter(f, list(F[0].keys()), delimiter="\t"); w.writeheader(); w.writerows(feed)
with open(f"{od}/xings_c23b.tsv", "w") as f:
    w = csv.DictWriter(f, list(X[0].keys()), delimiter="\t"); w.writeheader(); w.writerows(keep + add)
print([(r["child_region"], r["ins_ps"]) for r in feed if r["child_region"].startswith("T060")], len(keep), len(add))
