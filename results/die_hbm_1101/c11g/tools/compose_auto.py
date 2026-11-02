#!/usr/bin/env python3
"""DIE-HBM-57 class-sweep composer (one batch plan event, OWNER 11-01): BASE plan + every newly per-bit sited slot from
SWEEP_DIR/t/<type>.json (ledger entries), station points by min-max DP over the legal bit sites of each station against
the G0 die hop (check.lane_geometry + lane_pin_hops through mandatory slot pins), then auto-revert: any swept slot on a
lane whose die hop becomes > 405 (G0) or > 364.5 (G0C reach margin) while the base lane was within it goes back to BASE.
compose_auto.py BASE SWEEP_DIR OUT [--skip-types a,b]"""
import json, sys, glob, os
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-hbm-56/tools/die_plan")
import numpy as np
import schema as S, check as C
base_p, sd, out = sys.argv[1:4]
skip = set(sys.argv[5].split(",")) if len(sys.argv) > 5 and sys.argv[4] == "--skip-types" else set()
base = json.load(open(base_p)); raw = json.loads(json.dumps(base))
todo = []
for f in sorted(glob.glob(f"{sd}/t/*.ledger.json")):
    t = os.path.basename(f)[:-12]
    if t in skip or t.startswith("q_hub_"): continue
    L = json.load(open(f))
    if not L: continue
    tt = json.load(open(f"{sd}/t/{t}.json"))["partition_types"][t]
    for e in L:
        if e.get("alpha") is None: continue
        new = next(s for s in tt["ft_slots"] if s["name"] == e["slot"])
        i = next(i for i, s in enumerate(raw["partition_types"][t]["ft_slots"]) if s["name"] == e["slot"])
        raw["partition_types"][t]["ft_slots"][i] = new; todo.append((t, e["slot"]))
print("swept slots", len(todo), flush=True)
def hops(r):
    P = S.Plan(r, None); h = {}
    for lid in P.lanes:
        _, regs, _ = C.lane_geometry(P, lid); h[lid] = C.lane_pin_hops(P, lid, regs)
    return P, h
Pb, hb = hops(base); bmax = {l: max(v) if v else 0 for l, v in hb.items()}
def dp(P, t, sl):
    s = next(x for x in raw["partition_types"][t]["ft_slots"] if x["name"] == sl)
    bs = next(x for x in base["partition_types"][t]["ft_slots"] if x["name"] == sl)
    part = next(p for p, v in P.parts.items() if v["type"] == t)
    L = [(lid, i) for lid in P.lanes for i, x in enumerate(P.lane_crossings(lid)) if x[0] == part and x[1] == sl]
    if not L: return []
    lid, ci = L[0]; xs = P.lane_crossings(lid); _, regs, _ = C.lane_geometry(P, lid)
    k = int(s["stations"]); idx0 = 1 + sum(int((P.slot(p2, s2) or {}).get("stations", 1)) for p2, s2, _, _ in xs[:ci])
    _, _, a, b = xs[ci]; pa, pb = np.array(P.port_point(a)), np.array(P.port_point(b))
    q = np.array(regs[idx0 - 1]); pre = 0.0
    if ci > 0: pp = np.array(P.port_point(xs[ci - 1][3])); pre += np.abs(q - pp).sum(); q = pp
    pre += np.abs(q - pa).sum()
    nxt = np.array(regs[idx0 + k]); suf = 0.0; q = pb
    if ci + 1 < len(xs): pn = np.array(P.port_point(xs[ci + 1][2])); suf += np.abs(q - pn).sum(); q = pn
    suf += np.abs(q - nxt).sum()
    half = np.array(s["bit_site_cell_um"], dtype=float) / 2
    cands = [[tuple(bs["regs_um"][0]), tuple(s["regs_um"][0])]]
    for st in s["bit_sites_um"]:
        p = np.array(st, dtype=float) + half
        sel = p[np.linspace(0, len(p) - 1, min(len(p), 400)).astype(int)]
        cands.append([tuple(x) for x in sel] + [tuple(p[np.abs(p - p.mean(axis=0)).sum(axis=1).argmin()])])
    D = [np.array([P.to_die(part, c) for c in cs]) for cs in cands]
    cost = pre + np.abs(D[0] - pa).sum(axis=1); back = []
    for j in range(1, k):
        m = np.abs(D[j][:, None, :] - D[j - 1][None, :, :]).sum(axis=2)
        tot = np.maximum(m, cost[None, :]) + 1e-4 * m; bi = tot.argmin(axis=1); back.append(bi); cost = tot[np.arange(len(bi)), bi]
    fin = np.maximum(cost, np.abs(D[k - 1] - pb).sum(axis=1) + suf)
    c = int(fin.argmin()); ch = [c]
    for bi in reversed(back): c = int(bi[c]); ch.append(c)
    ch = ch[::-1]; s["regs_um"] = [list(np.round(cands[j][ch[j]], 4)) for j in range(k)]
    return [l for l, _ in L]
reverted = []
for rnd in range(8):
    lanes_of = {}
    P, _ = hops(raw)
    for _ in range(2):
        for t, sl in todo:
            for l in dp(P, t, sl): lanes_of.setdefault(l, set()).add((t, sl))
        P, h = hops(raw)
    bad = {l for l, v in h.items() if v and max(v) > 364.5 + 1e-6 and max(v) > bmax[l] + .5}
    print("round", rnd, "bad lanes", sorted((l, round(max(h[l]), 1), round(bmax[l], 1)) for l in bad), flush=True)
    if not bad: break
    rv = set().union(*(lanes_of.get(l, set()) for l in bad))
    if not rv: print("bad lanes not owned by swept slots", bad); break
    for t, sl in rv:
        i = next(i for i, s in enumerate(raw["partition_types"][t]["ft_slots"]) if s["name"] == sl)
        raw["partition_types"][t]["ft_slots"][i] = next(s for s in base["partition_types"][t]["ft_slots"] if s["name"] == sl)
    todo = [x for x in todo if x not in rv]; reverted += sorted(rv)
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
json.dump(raw, open(out, "w"), indent=0)
json.dump(dict(kept=todo, reverted=reverted), open(out + ".compose.json", "w"), indent=1)
print("KEPT", len(todo), todo); print("REVERTED", len(reverted), reverted)
