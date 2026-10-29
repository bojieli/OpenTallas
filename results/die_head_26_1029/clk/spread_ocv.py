"""DIE-HEAD-26: in-region spread incl. OCV + droop (12.15c "in-region spread <=150 ps incl. OCV+droop").
Per region (spine_regions part_region), every ordered tap pair (a late, b early):
  skew = f*(arr_a - arr_b) on OpenSTA late arrivals, f = spice factor (inverter tree: SPICE_CLOCK_CAL_INV 0.9324/0.9380
         = die_sta_related spice for inv; also reported with the x1.0485/1.0552 BUF factor as the pessimistic bound)
  ocv  = clk_aocv.branch_pessimism (approved table clk_aocv_table_g021, class Ainv, one stage per CKINVDCx16) on the two
         branches below their last common clock CELL (cell-level LCA from tree.json parent_of), core latency NOT included
         (die tap spread), distance = bbox diagonal of the 2 taps + LCA cell.  droop: shared rule (same region -> 0) and,
         as a bound, stated (+one_sided_late_frac on the late branch always).
usage: spread_ocv.py TAG REGIONS_JSON TOOLS_DIE_PLAN_DIR"""
import json, sys, collections, itertools
tag, regf, tdir = sys.argv[1:4]
sys.path.insert(0, tdir)
import clk_aocv as CA
T = CA.load(tdir + "/clk_aocv_table_g021.json")
SP = {"TT": 0.9324, "FF": 0.9380}; SPB = {"TT": 1.0485, "FF": 1.0552}
t = json.load(open(f"kit_{tag}/kit/clock/tree.json"))
par = t["parent_of"]; nb = t["node_buf"]; site = t["sites"]
reg = json.load(open(regf))["part_region"]
def chain(c):
    out = [c]
    while c in par: c = par[c]; out.append(c)
    return out
out = {}
for C in ("TT", "FF"):
    arr = {}
    for l in open(f"out_{tag}_{C}/arr_{C}.txt"):
        f = l.split()
        if len(f) >= 3 and f[0] in ("T", "N"): arr[f[1]] = float(f[2])
    fc = T["classes"]["Ainv"][C]["cell_share"]
    R = collections.defaultdict(list)
    for x in t["taps"]:
        R[reg[x["part"]]].append(x)
    rows = []
    for r, taps in R.items():
        ch = {x["port"]: chain(nb[str(x["node"])]) for x in taps}
        best = None
        for a, b in itertools.permutations(taps, 2):
            ca, cb = ch[a["port"]], ch[b["port"]]
            sb = set(cb); lca = next(c for c in ca if c in sb)
            na, nbb = ca.index(lca) + 1, cb.index(lca) + 1          # stages below the LCA incl. the tap driver
            ua = max(0.0, arr[a["port"]] - arr[lca]) * SP[C]; ub = max(0.0, arr[b["port"]] - arr[lca]) * SP[C]
            pts = [a["xy"], b["xy"], site[lca]]
            d = ((max(p[0] for p in pts) - min(p[0] for p in pts)) ** 2 + (max(p[1] for p in pts) - min(p[1] for p in pts)) ** 2) ** .5
            br = lambda u, n: dict(cell_ps=fc * u, net_ps=(1 - fc) * u, stages={"Ainv": n})
            o_sh = CA.branch_pessimism(T, C, br(ua, na), br(ub, nbb), d, True, "setup")
            o_st = CA.branch_pessimism(T, C, br(ua, na), br(ub, nbb), d, False, "setup")
            raw = arr[a["port"]] - arr[b["port"]]
            v = (raw * SP[C] + o_sh, raw * SP[C] + o_st, raw * SPB[C] + o_st, raw, a["port"], b["port"], round(o_sh, 1), round(o_st, 1), na, nbb)
            if best is None or v[0] > best[0]: best = v
        if best: rows.append((r,) + best)
    rows.sort(key=lambda x: -x[1])
    out[C] = dict(regions=len(rows), worst_shared_droop=round(rows[0][1], 2), worst_stated_droop=round(max(x[2] for x in rows), 2),
                  worst_bufx105_stated=round(max(x[3] for x in rows), 2),
                  n_over_150_shared=sum(x[1] > 150 for x in rows), n_over_150_stated=sum(x[2] > 150 for x in rows),
                  worst5=[dict(region=x[0], spread_ocv=round(x[1], 1), stated=round(x[2], 1), raw=round(x[4], 1), a=x[5], b=x[6],
                               ocv_shared=x[7], ocv_stated=x[8], stages=[x[9], x[10]]) for x in rows[:5]])
    print(tag, C, json.dumps({k: v for k, v in out[C].items() if k != "worst5"}), out[C]["worst5"][0])
json.dump(dict(rule="12.15c in-region spread <=150 ps incl. OCV+droop", method=__doc__, corners=out), open(f"spread_ocv_{tag}.json", "w"), indent=1)
