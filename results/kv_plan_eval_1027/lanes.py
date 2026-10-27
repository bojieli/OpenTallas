#!/usr/bin/env python3
"""KV-PLAN-EVAL (c): lane-level 405-um feasibility of FT station counts (greedy furthest placement, Manhattan paths).
Lane = src face reg -> [ft slot crossings] -> dst face reg; stations of slot k must lie inside crossing k."""
import json, math, sys, collections
from pathlib import Path
sys.path[:0] = [sys.argv[1] + "/tools/die_plan", sys.argv[1] + "/tools"]
import schema as S, gen_phys
qp, ep, out = sys.argv[2], sys.argv[3], sys.argv[4]
REACH = float(sys.argv[5]) if len(sys.argv) > 5 else 405.0
def load(p): return S.Plan(S.load(p), Path(p)), json.load(open(p))
Q, qr = load(qp); E, er = load(ep)
def slotlen(P):
    L = {}
    for tn, t in P.types.items():
        pins = collections.defaultdict(list)
        for bus, bit, ln, x, y, f in gen_phys.type_pins(P, tn):
            pins[bus].append((bit, x, y))
        for s in t.get("ft_slots", []) or []:
            a, b = sorted(pins[s["name"] + "_i"]), sorted(pins[s["name"] + "_o"])
            L[(tn, s["name"])] = (max(abs(p[1] - r[1]) + abs(p[2] - r[2]) for p, r in zip(a, b)), s["stations"])
    return L
LQ, LE = slotlen(Q), slotlen(E)
ptype = {p["name"]: p["type"] for p in qr["partitions"]}
ports = {p["id"]: p for p in qr["ports"]}
lq, le = qr["latency"]["lanes"], er["latency"]["lanes"]
changed = [k for k in lq if le[k]["stations"] != lq[k]["stations"]]
def feasible(chain):
    """chain = [(length, n_stations)], returns (ok, worst_needed_hop)."""
    p = 0.0; s0 = 0.0; worst = 0
    for Lk, n in chain:
        e0 = s0 + Lk
        for _ in range(n):
            pos = min(p + REACH, e0)
            if pos < s0: return False, None
            worst = max(worst, pos - p); p = pos
        s0 = e0
    worst = max(worst, s0 - p)
    return s0 - p <= REACH + 1e-6, worst
def min_extra(chain):
    """smallest number of added stations (anywhere in the chain) for feasibility: greedy add to the slot that fails."""
    ch = [list(c) for c in chain]; add = 0
    while not feasible([tuple(c) for c in ch])[0] and add < 20:
        # add one station to the longest-per-station crossing
        k = max(range(len(ch)), key=lambda i: ch[i][0] / (ch[i][1] + 1))
        ch[k][1] += 1; add += 1
    return add
def uniform(chain, mode):
    """per-crossing fixed placement. mode j1: stations at j/(n+1) (legs L/(n+1)); mode half: legs L/(2n), hops L/n."""
    hops = []; carry = 0.0
    for Lk, n in chain:
        if n == 0: carry += Lk; continue
        if mode == "j1": a = Lk / (n + 1); mid = Lk / (n + 1)
        else: a = Lk / (2 * n); mid = Lk / n
        hops.append(carry + a); hops += [mid] * (n - 1); carry = a
    hops.append(carry)
    return max(hops)
def min_extra_uniform(chain, mode):
    ch = [list(c) for c in chain]; add = 0
    while uniform([tuple(c) for c in ch], mode) > REACH + 1e-6 and add < 40:
        hops = []
        k = max(range(len(ch)), key=lambda i: ch[i][0] / (ch[i][1] + 1))
        ch[k][1] += 1; add += 1
    return add
rows = []
for lid in changed:
    lane = next(l for l in qr["lanes"] if l["id"] == lid)
    cq, ce = [], []
    for pid in lane["ports"]:
        d = ports[pid]["dst"]
        if d["bus"].startswith("ft") and d["bus"].endswith("_i"):
            key = (ptype[d["part"]], d["bus"][:-2])
            cq.append(LQ[key]); ce.append(LE[key])
    okq, wq = feasible(cq); oke, we = feasible(ce)
    rows.append(dict(lane=lid, crossings=len(cq), length=round(sum(c[0] for c in cq), 1),
                     st_q2=sum(c[1] for c in cq), st_ev=sum(c[1] for c in ce), lat_st_q2=lq[lid]["stations"],
                     lat_st_ev=le[lid]["stations"], dcyc=le[lid]["cycles"] - lq[lid]["cycles"],
                     q2_feasible=okq, ev_feasible=oke, min_extra=min_extra(cq) if not okq else 0,
                     j1_q2=round(uniform(cq,"j1"),1), j1_ev=round(uniform(ce,"j1"),1), half_q2=round(uniform(cq,"half"),1),
                     add_j1=min_extra_uniform(cq,"j1"), add_half=min_extra_uniform(cq,"half"),
                     lower_bound_extra=max(0, math.ceil(sum(c[0] for c in cq) / REACH) - 1 - sum(c[1] for c in cq))))
c = collections.Counter((r["q2_feasible"], r["ev_feasible"]) for r in rows)
summ = dict(reach_um=REACH, lanes=len(rows), event_added_cycles=sum(r["dcyc"] for r in rows),
            q2_counts_feasible=sum(r["q2_feasible"] for r in rows), event_feasible=sum(r["ev_feasible"] for r in rows),
            minimal_added_stations=sum(r["min_extra"] for r in rows),
            lanes_needing_add=sum(1 for r in rows if r["min_extra"]),
            lower_bound_added=sum(r["lower_bound_extra"] for r in rows),
            j1_q2_fail=sum(1 for r in rows if r["j1_q2"] > REACH), j1_ev_fail=sum(1 for r in rows if r["j1_ev"] > REACH),
            add_j1_total=sum(r["add_j1"] for r in rows), add_half_total=sum(r["add_half"] for r in rows),
            half_q2_fail=sum(1 for r in rows if r["half_q2"] > REACH),
            no_ft_crossing=sum(1 for r in rows if r["crossings"] == 0))
json.dump(dict(summary=summ, rows=rows), open(out, "w"), indent=1)
print(json.dumps(summ, indent=1))
