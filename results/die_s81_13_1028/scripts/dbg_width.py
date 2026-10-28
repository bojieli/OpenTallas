"""DIE-S81-13 diagnostic: where does start-port width come from? interval width along the capture tree path for the
26 width-unclean ports of die-s81-12 ca_width (same ctx as count_align_plan --start-tree clock)."""
import json, sys
MT = sys.argv[1]; O = sys.argv[2]; PL = sys.argv[3]
sys.path.insert(0, MT)
import count_align_plan as CAP
import die_sta_related as DSR
ctx = CAP.clock_contexts(O + "/proof", PL, ["TT", "FF"], "spice", "table", "shared", O + "/proof/droop_regions.json", 202.5)
cs = list(ctx); c0 = ctx[cs[0]]
leg = {c: DSR.tap_leg(k["meta"], k["taps"]) for c, k in ctx.items()}
print("leg", leg)
def vt(p):
    for c in cs: k = DSR.virtual_tap(ctx[c]["meta"], ctx[c]["taps"], p, leg[c])
    return k
def iv(a, b):
    old, DSR.CPPR_LCA = DSR.CPPR_LCA, True
    lo = hi = None
    for c in cs:
        x = DSR.count_align_d_intervals([(a, b, "s")], ctx[c]["taps"], ctx[c]["rng"], ocv=ctx[c]["ocv"])["s"]
        lo = x[0] if lo is None else min(lo, x[0]); hi = x[1] if hi is None else max(hi, x[1])
    DSR.CPPR_LCA = old
    return hi - lo
p = json.load(open(sys.argv[5]))
nl = c0["meta"]["node_late_ps"]; nxy = c0["meta"]["node_xy_um"]
for e in [e for e in p["start_edges"] if not e.get("clean_ok", True)][:int(sys.argv[4])]:
    a, b = e["launch"], e["capture"]
    a = vt(a[6:]) if a.startswith("__st__") else a
    A, B = (c0["taps"][a] if not a.startswith("__st__") else None), c0["taps"][b]
    pa = A["tree_path"] if A else a[6:]
    f = CAP._lcp(pa, B["tree_path"])
    print("==", e["port"], "width", round(iv(a, b), 1), "fork len", len(f), "cap len", len(B["tree_path"]), "launch len", len(pa))
    # launch leaf -> fork node
    if A: print("   leaf->fork vtap width", round(iv(a, vt(f)), 1), "unsh", round(A["late_ps"] - nl[f]))
    cp = B["tree_path"]; prev = f
    for n in range(len(f) + 1, len(cp) + 1):
        q = cp[:n]
        if q not in nl: continue
        w1 = iv(vt(prev), vt(q)) if n < len(cp) else iv(vt(prev), b)
        print("   seg %s..%d late %.0f -> %.0f  xy %s width %.1f" % (len(prev), n, nl[prev], nl[q], [round(v) for v in nxy[q]], w1))
        prev = q
