#!/usr/bin/env python3
"""DS85 CLKDIE-S81 (DO_NOT_COUNT): summary of landing_phase_sign.py output + arrivals detail.

(a) the tool's classes as-is (raw signed d, no wrap);
(b) by view quality (both sides measured / one / none DECLARED);
(c) [inferred] wrapped view: d folded into (-P/2, P/2] with P = 833 ps (the die clock period of clock_grt_probe / the
    die STA), because a mesochronous ring sees only the phase mod P; rows whose [lo, hi] crosses +-P/2 are EDGE;
(d) worst 10 = smallest flip clearance s = max(-hi, lo) (min over corners; s < 0: the interval straddles zero).

  ds85_report.py LPS_JSON DETAIL_JSON OUT_JSON
"""
import json
import sys
from collections import Counter

P = 833.0
M = 100.0
lps = json.load(open(sys.argv[1]))
det = json.load(open(sys.argv[2]))["corners"]
D = {c: {r["port"]: r for r in det[c]["rows"]} for c in det}


def view(port):
    r = D["TT"][port]
    n = sum(v != "DECLARED" for v in (r["src_view"], r["dst_view"]))
    return {2: "both_measured", 1: "one_side_declared", 0: "both_declared"}[n]


def wrap(x):
    return x - P * round(x / P)


def wcls(c):
    d, up, dn = wrap(c["d_ps"]), c["hi_ps"] - c["d_ps"], c["d_ps"] - c["lo_ps"]
    hi, lo = d + up, d - dn
    if hi > P / 2 or lo < -P / 2:
        return "EDGE"
    return "LEAD" if hi <= -M else "LAG" if lo >= M else "NEAR"


out = dict(period_ps=P, margin_ps=M, raw=dict(all=dict(Counter(r["cls"] for r in lps["rows"]))), by_corner={},
           by_view={}, wrapped={}, abs_d_over_half_period={})
for c in ("TT", "FF"):
    out["by_corner"][c] = dict(Counter(r["corners"][c]["cls"] for r in lps["rows"]))
    out["abs_d_over_half_period"][c] = sum(abs(r["corners"][c]["d_ps"]) > P / 2 for r in lps["rows"])
for r in lps["rows"]:
    out["by_view"].setdefault(view(r["port"]), Counter())[r["cls"]] += 1
wr = []
for r in lps["rows"]:
    cs = {c: wcls(r["corners"][c]) for c in ("TT", "FF")}
    k = "EDGE" if "EDGE" in cs.values() else cs["TT"] if cs["TT"] == cs["FF"] else "NEAR"
    wr.append(k)
    out["wrapped"].setdefault(view(r["port"]), Counter())[k] += 1
out["wrapped"]["all"] = Counter(wr)
rows = []
for r in lps["rows"]:
    s = min(max(-r["corners"][c]["hi_ps"], r["corners"][c]["lo_ps"]) for c in ("TT", "FF"))
    t = D["TT"][r["port"]]
    rows.append(dict(port=r["port"], cls=r["cls"], clearance_ps=round(s, 1), view=view(r["port"]),
                     TT=r["corners"]["TT"], FF=r["corners"]["FF"], src=t["src"], dst=t["dst"],
                     src_type=t["src_type"], dst_type=t["dst_type"], src_view=t["src_view"], dst_view=t["dst_view"],
                     A_src=t["A_src"], A_dst=t["A_dst"], I_out=t["I_out"], I_write=t["I_write"], I_read=t["I_read"],
                     net_ps=t["net_ps"], hop_um=t["hop_um"], p_up=t["p_up_ps"], p_dn=t["p_dn_ps"]))
rows.sort(key=lambda x: x["clearance_ps"])
out["worst10"] = rows[:10]
out["worst10_both_measured"] = [x for x in rows if x["view"] == "both_measured"][:10]
json.dump(out, open(sys.argv[3], "w"), indent=1, default=dict)
print(json.dumps({k: v for k, v in out.items() if not k.startswith("worst")}, default=dict))
for k in ("worst10", "worst10_both_measured"):
    print(k)
    for x in out[k]:
        print(f"  {x['port']:38s} {x['cls']:4s} s={x['clearance_ps']:7.1f} TT d={x['TT']['d_ps']:8.1f} "
              f"[{x['TT']['lo_ps']:.0f},{x['TT']['hi_ps']:.0f}] FF d={x['FF']['d_ps']:8.1f} {x['view']} "
              f"{x['src']}->{x['dst']} A {x['A_src']:.0f}/{x['A_dst']:.0f} net {x['net_ps']:.1f} hop {x['hop_um']:.0f}")
