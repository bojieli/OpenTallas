"""DIE-HEAD: crossing margins of a landed_phase_ocv.json restricted to the ports that cross a region map, in the two
COORD readings (20:26 NUMBER-CHECK ruling, coord 749118554):
  CURRENT ring : 416.5 - max(|d + p_up|, |d - p_dn|)          (landed_phase_ocv margin, unchanged)
  COUNT-ALIGNED: window W = P - placement-flop setup+hold = +-403.4 TT / +-407.0 FF; ONE design-time count K for TT and FF
                 (step = P whole-cycle, or P/2 with half-cycle placement); residual r = d - K*step counts:
                 margin_C = W_C - max(|r_C + p_up|, |r_C - p_dn|); K chosen to maximise min(margin_TT, margin_FF).
usage: ca_reading.py LANDED_OCV.json REGION_MAP.json|part [--out JSON]"""
import json, sys, gzip
P = 833.0
W = {"TT": 403.4, "FF": 407.0}
L = json.load(open(sys.argv[1]))
rm = None if sys.argv[2] == "part" else json.load(open(sys.argv[2]))["part_region"]
rows = {}
for c in ("TT", "FF"):
    k = [k for k in L["corners"] if k.startswith(c + "_droop-regions_corelat") and L["corners"][k].get("all")][0]
    for r in L["corners"][k]["all"]:
        rows.setdefault(r["port"], {})[c] = r
def ca(rt, rf, step):
    best = None
    for K in range(-40, 41):
        m = []
        for C, r in (("TT", rt), ("FF", rf)):
            res = r["d_ps"] - K * step
            m.append(W[C] - max(abs(res + r["p_up_ps"]), abs(res - r["p_dn_ps"])))
        if best is None or min(m) > min(best[1]):
            best = (K, m)
    return best
out = []
for p, v in rows.items():
    rt, rf = v["TT"], v["FF"]
    if rm is not None and rm.get(rt["src"]) == rm.get(rt["dst"]):
        continue
    kw, mw = ca(rt, rf, P); kh, mh = ca(rt, rf, P / 2)
    out.append(dict(port=p, src=rt["src"], dst=rt["dst"], d_tt=rt["d_ps"], d_ff=rf["d_ps"], u_tt=max(rt["unshared_a_ps"], rt["unshared_b_ps"]),
                    cur_tt=rt["margin_ps"], cur_ff=rf["margin_ps"], caw_k=kw, caw_tt=round(mw[0], 1), caw_ff=round(mw[1], 1),
                    cah_k=kh, cah_tt=round(mh[0], 1), cah_ff=round(mh[1], 1)))
def s(key):
    v = [o[key] for o in out]
    return dict(worst=round(min(v), 1), under_100=sum(x < 100 for x in v), under_0=sum(x < 0 for x in v))
summ = dict(crossings=len(out), max_unshared_tt=max(o["u_tt"] for o in out), max_abs_d_tt=max(abs(o["d_tt"]) for o in out),
            current={c: s("cur_" + c.lower()) for c in ("TT", "FF")},
            count_aligned_whole={c: s("caw_" + c.lower()) for c in ("TT", "FF")},
            count_aligned_half={c: s("cah_" + c.lower()) for c in ("TT", "FF")})
print(json.dumps(summ))
if len(sys.argv) > 4:
    out.sort(key=lambda o: min(o["cah_tt"], o["cah_ff"]))
    json.dump(dict(summary=summ, doc=__doc__, rows=out), open(sys.argv[4], "w"), indent=1)
