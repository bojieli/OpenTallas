"""DIE-QC-13 probe: why the 60 slice-head start edges cannot retime in width mode (trial10 proof, main tools).
For each failing edge print the (unshared_a, unshared_b, width, clean) of lau -> vtap(n) for every tree node n on the
capture path below the fork, and of vtap(n) -> capture."""
import json, sys
sys.path.insert(0, sys.argv[1])
import count_align_plan as C
import die_sta_related as DSR
proof, plan, pw = sys.argv[2], sys.argv[3], sys.argv[4]
ctx = C.clock_contexts(proof, plan, ["TT", "FF"], "spice", "table", "shared", proof + "/droop_regions.json", 202.5)
cs = list(ctx); c0 = ctx[cs[0]]
leg = {c: DSR.tap_leg(k["meta"], k["taps"]) for c, k in ctx.items()}
T, ap = 833.0, 833.0 / 8


def vt(p):
    for c in cs:
        DSR.virtual_tap(ctx[c]["meta"], ctx[c]["taps"], p, leg[c])
    return f"__st__{p}"


def iv(a, b):
    old, DSR.CPPR_LCA = DSR.CPPR_LCA, True
    lo = hi = None
    for c in cs:
        x = DSR.count_align_d_intervals([(a, b, "s")], ctx[c]["taps"], ctx[c]["rng"], ocv=ctx[c]["ocv"])["s"]
        lo = x[0] if lo is None else min(lo, x[0]); hi = x[1] if hi is None else max(hi, x[1])
    DSR.CPPR_LCA = old
    A, B = c0["taps"][a], c0["taps"][b]
    nl = c0["meta"]["node_late_ps"]
    f = C._lcp(A["tree_path"], B["tree_path"]) or "h"
    q = dict(lo=lo, hi=hi)
    n, e, off, dist = C.sync_choice(q, T, ap)
    ok = n == 1 and hi - lo <= T / 2 - 2 * ap
    return dict(ua=round(A["late_ps"] - nl[f]), ub=round(B["late_ps"] - nl[f]), w=round(hi - lo), lo=round(lo), hi=round(hi),
                n=n, ok=ok)


d = json.load(open(pw))
F = [e for e in d["start_edges"] if not e["clean_ok"]]
sel = sys.argv[5].split(",") if len(sys.argv) > 5 else None
for e in F:
    if sel and not any(s in e["port"] for s in sel):
        continue
    lau, cap = e["launch"], e["capture"]
    cp = c0["taps"][cap]["tree_path"]; lp = c0["taps"][lau]["tree_path"]
    f = C._lcp(lp, cp)
    print(e["port"], "fork", f, "direct", iv(lau, cap))
    nl = c0["meta"]["node_late_ps"]; xy = c0["meta"]["node_xy_um"]
    for n in range(len(f) + 1, len(cp)):
        p = cp[:n]
        if p not in nl:
            continue
        v = vt(p)
        print("   node", p, round(nl[p]), xy.get(p), "lau->n", iv(lau, v), "n->cap", iv(v, cap))
