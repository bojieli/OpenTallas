"""PATH-S81-PD12 (D) plan prediction on PD9 me1: legs whose repeated hop > 405 um, the repeaters a 405-um cap adds, and
whether each added repeater finds a free (non-hard-core) site on its own leg inside the slack that keeps every hop <= 405.
usage: dpred.py TOOLS BUILD PLAN"""
import collections, json, math, sys
sys.path.insert(0, sys.argv[1])
import die_clock as DC, die_clock_mesh as DM, schema as S
B, plan = sys.argv[2], sys.argv[3]
P = S.Plan(S.load(plan), plan)
K = DC.KeepIndex(DC.keepouts(P), die=(P.W, P.H))
rects = DC.keepouts(P)
M = json.load(open(f"{B}/mesh.json"))
def at(a, b, s):   # point at arclength s on the x-first L from a to b
    dx = b[0] - a[0]
    if s <= abs(dx):
        return (a[0] + math.copysign(s, dx), a[1])
    return (b[0], a[1] + math.copysign(s - abs(dx), b[1] - a[1]))
lv = collections.defaultdict(lambda: dict(legs=0, over=0, add=0, free=0, push=0, maxhop=0.0))
cores = collections.Counter()
for h in M["htree"]:
    L = h["len_um"]; n0 = len(h["reps"]); hop = L / (n0 + 1)
    r = lv[h["level"]]; r["legs"] += 1; r["maxhop"] = max(r["maxhop"], hop)
    if hop <= 405.0 + 1e-6:
        continue
    r["over"] += 1
    n = math.ceil(L / 405.0 - 1e-9) - 1          # repeaters for equal hops <= 405
    r["add"] += n - n0
    slack = (405.0 * (n + 1) - L) / 2          # each repeater may slide this far along the leg and keep hops <= 405
    for k in range(1, n + 1):
        s0 = L * k / (n + 1); ok = False
        for ds in [0.0] + [sgn * j * 2.16 for j in range(1, int(max(slack, 0) / 2.16) + 1) for sgn in (1, -1)]:
            p = at(h["a"], h["b"], min(max(s0 + ds, 0.0), L))
            if not DM.hitf(K, p):
                ok = True; break
        if ok:
            r["free"] += 1
        else:
            r["push"] += 1
            cores[DM.core_at(rects, at(h["a"], h["b"], s0)) or "?"] += 1
tot = {k: sum(v[k] for v in lv.values()) for k in ("legs", "over", "add", "free", "push")}
print(json.dumps(dict(levels={k: dict(v, maxhop=round(v["maxhop"], 1)) for k, v in sorted(lv.items())}, total=tot,
                      push_cores=dict(cores.most_common(12)), note="x-first L only; band trees not included; UNCHECKED"), indent=0))
