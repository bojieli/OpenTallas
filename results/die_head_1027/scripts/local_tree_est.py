"""DIE-HEAD 12.14b estimate (UNCHECKED): an equal-depth local region tree of insertion I is hung below each region root
on the routed spine_fishbone feed (LAND-HEAD-3 sfbR arrivals). Nominal d is kept (equal I on both sides); each side's
unshared grows by I, so the shared-model derate p is scaled by (ua+ub+core+2I)/(ua+ub+core) (linear-in-unshared
approximation of clk_aocv + one-sided droop). Readings: current ring (416.5 budget) and count-aligned per the COORD
20:26 ruling (window 403.4 TT / 407.0 FF, one design-time count K for TT and FF, whole-cycle or half-cycle step).
usage: local_tree_est.py LANDED_OCV.json REGION_MAP.json|part I_ps[,I_ps...]"""
import json, sys
P = 833.0; W = {"TT": 403.4, "FF": 407.0}
L = json.load(open(sys.argv[1]))
rm = None if sys.argv[2] == "part" else json.load(open(sys.argv[2]))["part_region"]
rows = {}
for c in ("TT", "FF"):
    k = [k for k in L["corners"] if k.startswith(c + "_droop-regions_corelat") and L["corners"][k].get("all")][0]
    for r in L["corners"][k]["all"]:
        rows.setdefault(r["port"], {})[c] = r
def marg(r, C, res, s):
    return W[C] - max(abs(res + r["p_up_ps"] * s), abs(res - r["p_dn_ps"] * s))
for I in [float(x) for x in sys.argv[3].split(",")]:
    cur = {"TT": 9e9, "FF": 9e9}; cah = caw = 9e9; n = u100 = 0
    for p, v in rows.items():
        if rm is not None and rm[v["TT"]["src"]] == rm[v["TT"]["dst"]]:
            continue
        n += 1; sc = {}
        for C in ("TT", "FF"):
            r = v[C]; u = r["unshared_a_ps"] + r["unshared_b_ps"] + (500 if C == "TT" else 405)
            sc[C] = (u + 2 * I * (1 if C == "TT" else 0.86)) / u
            cur[C] = min(cur[C], 416.5 - max(abs(r["d_ps"] + r["p_up_ps"] * sc[C]), abs(r["d_ps"] - r["p_dn_ps"] * sc[C])))
        bw = max(min(marg(v[C], C, v[C]["d_ps"] - K * P, sc[C]) for C in ("TT", "FF")) for K in range(-20, 21))
        bh = max(min(marg(v[C], C, v[C]["d_ps"] - K * P / 2, sc[C]) for C in ("TT", "FF")) for K in range(-40, 41))
        caw = min(caw, bw); cah = min(cah, bh); u100 += bh < 100
    print(f"I={I:6.0f} n={n:3d} current TT {cur['TT']:7.1f} FF {cur['FF']:7.1f} | count-aligned whole {caw:7.1f} half {cah:7.1f} (half <100: {u100})")
