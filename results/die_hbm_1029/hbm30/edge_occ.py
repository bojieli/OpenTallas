import sys, json
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-hbm-27/tools/die_plan")
import lane_add as LA, schema as S
raw = json.load(open(sys.argv[1] + "/die_plan.json"))
Bd = LA.Builder(raw)
P = Bd.P
for a, b in [(x, y) for x, y in (p.split("|") for p in sys.argv[2:])]:
    e = LA.shared_edge(P, a, b)
    if not e: print(a, b, "no shared edge"); continue
    df, lo, hi = e
    occ = LA.face_intervals(P, a, df) + LA.face_intervals(P, b, LA.OPP[df])
    used = sum(y - x for x, y in occ)
    gaps = LA.free_gaps(lo + 1, hi - 1, occ, 2.0)
    layers = LA.face_layers(P, a, df)
    pins, per = Bd.pins_need(0, layers)
    print(f"{a}|{b} face {df} edge {lo:.1f}-{hi:.1f} len {hi-lo:.1f} um, layers {layers}, per_um {per}, windows {len(occ)} used {used:.1f} um ({100*used/(hi-lo):.0f}%), largest free {max((g1-g0 for g0,g1 in gaps), default=0):.1f} um, free total {sum(g1-g0 for g0,g1 in gaps):.1f} um -> cap ~{sum(g1-g0 for g0,g1 in gaps)*per:.0f} b")
    # ports on that edge
    W = []
    for pid, pr in P.ports.items():
        if "window_um" not in pr: continue
        if {pr["src"]["part"], pr["dst"]["part"]} == {a, b}:
            W.append((pid, pr.get("width") or pr.get("bits"), [round(v,1) for v in pr["window_um"]]))
    print("   ports on edge:", W[:20])
