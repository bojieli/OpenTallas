"""DIE-HBM-10 C23q ESTIMATE: PHY_N 3-way split re-balanced to whole channels W = PC 0-9 / C = PC 10-21 / E = PC 22-31,
after the C23 (8/16/8) face census: the centre column vsN4..6 would carry 16 PCs x 585 b = 9360 b (L22/L22m rdata must
leave PHY_NC via the column, no cut crossing) = 1674 um of 1684.8 um at the plan's achieved 5.59 b/um (L9 window 2456 b /
439.25 um): no margin.  10/12/10: column 12 x 585 = 7020 b, W/E paths 10 x 585 = 5850 b each (today 6552).
Part 1: face census (bits per face vs face_pins_per_um x length, and column window fill at 5.59 b/um) for C22b / C23 / C23q.
Part 2: CA feed for 10/12/10 (region insertion scaled by the half-width change at V = 0.3659, as mk_feed_c23.py).
usage: c23q.py PLAN SRC_FEED(hbm9 split) OUT_FEED"""
import json, sys, csv, collections
plan, srcf, outf = sys.argv[1:4]
P = json.load(open(plan)); T = P["partition_types"]; B = P["budgets"]
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}
R = {}
for p in P["partitions"]:
    o = T[p["type"]]["outline_um"]; x0, y0 = p["origin_um"]; R[p["name"]] = (x0, y0, x0 + o[0], y0 + o[1], p["type"])
def face(a, b):
    A, C = R[a], R[b]
    if abs(A[3] - C[1]) < 1: return "N"
    if abs(A[1] - C[3]) < 1: return "S"
    if abs(A[2] - C[0]) < 1: return "E"
    if abs(A[0] - C[2]) < 1: return "W"
use = collections.defaultdict(int); phy = collections.defaultdict(int)
def bus(pid): return pid.rsplit("_", 1)[0]
PHYB = {"L8", "L8m", "L9", "L9m", "L21", "L21m", "L22", "L22m", "L63", "L63m", "L114", "L114m"}
for p in P["ports"]:
    s, d = p["src"]["part"], p["dst"]["part"]; f = p.get("face") or face(s, d)
    for n, ff in ((s, f), (d, OPP[f])):
        if n not in R: continue
        if bus(p["id"]) in PHYB: phy[(n, ff)] += p["width"]
        else: use[(n, ff)] += p["width"]
PC = 585   # per-PC boundary bits: in 307 + 21, out 256 + 1 (mk_c23_map.py, CHECKED vs plan buses)
WPATH = ["NW_spu0", "NW_spt0", "NW_spt1", "NW_spt2"]; COL = ["vsN4", "vsN5", "vsN6"]
def census(name, w_pcs, c_pcs):
    rows = []
    for n in WPATH + COL:
        t = T[R[n][4]]; L = R[n][2] - R[n][0]; cap = B["face_pins_per_um"] * L
        for f in "NS":
            other = use.get((n, f), 0)
            new = other + (w_pcs * PC if n in WPATH else c_pcs * PC)
            if name == "C22b": new = other + phy.get((n, f), 0)
            rows.append(dict(part=n, face=f, len_um=round(L, 2), bits=new, fill_cap=round(new / cap, 3),
                             col_window_fill=round(new / 5.59 / L, 3) if n in COL else None))
    return rows
out = {"C22b": census("C22b", 0, 0), "C23_8_16_8": census("C23", 8, 16), "C23q_10_12_10": census("C23q", 10, 12)}
for k, v in out.items():
    print(k, "worst W-path fill", max(r["fill_cap"] for r in v if r["part"] in WPATH),
          "column fill", max(r["fill_cap"] for r in v if r["part"] in COL),
          "column window fill @5.59", max(r["col_window_fill"] or 0 for r in v))
json.dump(out, open(outf.replace(".tsv", "_census.json"), "w"), indent=1)
F = list(csv.DictReader(open(srcf), delimiter="\t")); V = 0.3659; third = 8804.16 / 3
wW = 146.88 + 308 * 8.64; wC = 369 * 8.64
d = {"T060C": (wC - third) / 2, "T060W": (wW - third) / 2, "T060E": (wW - third) / 2}
for r in F:
    if r["child_region"] in d: r["ins_ps"] = f"{float(r['ins_ps']) + d[r['child_region']] * V:.1f}"; print(r["child_region"], r["ins_ps"])
w = csv.DictWriter(open(outf, "w"), fieldnames=list(F[0].keys()), delimiter="\t"); w.writeheader(); w.writerows(F)
