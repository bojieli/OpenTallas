"""DIE-HBM-10 C23h ESTIMATE (hybrid 2-way): PHY_N W = PC 0-15 / E = PC 16-31 cut at die x 14197.68 (8.64 lattice), which
also cuts the vsN6 column face in two (842 um each side).  NW buses that already use the centre column (L9, L63, L114)
keep it and land on PHY_NW through vsN6's W part; the NE ones (L9m, L63m, L114m) on PHY_NE through its E part.  L8/L21/L22
(+m) keep the W/E mcb paths.  No new pin load anywhere (window reshuffle inside vsN4..6 only).  The far link is
T057 -> T060W (column into the E end of the W half, ~4.4 mm from the half's W-face tap): this estimate prices it.
usage: mk_var_c23h.py RETREE_DIR C23B_FEED OUTDIR"""
import csv, sys, os
rd, feedf, od = sys.argv[1:4]; os.makedirs(od, exist_ok=True)
X = list(csv.DictReader(open(f"{rd}/hbm_xings_split.tsv"), delimiter="\t"))
out = []
for r in X:
    r = dict(r)
    for k in ("src_region", "dst_region", "tree_node_region"):
        if r[k] == "T060C":
            r[k] = "T060E" if r["port"].split("_")[0].endswith("m") else "T060W"
    out.append(r)
with open(f"{od}/xings_c23h.tsv", "w") as f:
    w = csv.DictWriter(f, list(X[0].keys()), delimiter="\t"); w.writeheader(); w.writerows(out)
print(sum(1 for r in out if "T060W" in (r["src_region"], r["dst_region"])), sum(1 for r in out if "T060E" in (r["src_region"], r["dst_region"])))
