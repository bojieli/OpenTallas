"""DIE-HBM-10: PHY_N one-region feed variants (the PHY is ONE hard macro, single clk pin at window 16 -> no 3-way split).
usage: mk_var.py RETREE_DIR OUTDIR.  V1: PHY_N (T060) whole, fed from the centre column T057 at its S-face centre tap
(clock enters at the macro clk pin side); T059/T061 keep parents T055/T056.  V2: V1 + NW_mcb (T059) and NE_mcb (T061)
fed FROM PHY_N's W/E leaves (clock follows the L8/L21/L22 data)."""
import csv, sys, os
rd, od = sys.argv[1:3]; os.makedirs(od, exist_ok=True)
F = list(csv.DictReader(open(f"{rd}/hbm_feed_split.tsv"), delimiter="\t"))
X = list(csv.DictReader(open(f"{rd}/hbm_xings_split.tsv"), delimiter="\t"))
hdrF = list(F[0].keys()); hdrX = list(X[0].keys())
base = [r for r in F if not r["child_region"].startswith("T060")]
t060 = dict(child_region="T060", parent_region="T057", feed_tap_xy_um="[14199.8, 16467.8]", w_mm="8.8", h_mm="2.07", ins_ps="1990.1")
def xr():
    out = []
    for r in X:
        r = dict(r)
        for k in ("src_region", "dst_region", "tree_node_region"):
            if r[k].startswith("T060"): r[k] = "T060"
        if r["class"] == "tree-edge" and "T060" in (r["src_region"], r["dst_region"]): r["class"] = "remapped"
        out.append(r)
    return out
for name, mod in (("V1", {}), ("V2", {"T059": ("T060", "[9797.8, 17504.6]"), "T061": ("T060", "[18601.9, 17504.6]")})):
    rows = [dict(r) for r in base] + [dict(t060)]
    for r in rows:
        if r["child_region"] in mod: r["parent_region"], r["feed_tap_xy_um"] = mod[r["child_region"]]
    with open(f"{od}/feed_{name}.tsv", "w") as f:
        w = csv.DictWriter(f, hdrF, delimiter="\t"); w.writeheader(); w.writerows(rows)
    with open(f"{od}/xings_{name}.tsv", "w") as f:
        w = csv.DictWriter(f, hdrX, delimiter="\t"); w.writeheader(); w.writerows(xr())
