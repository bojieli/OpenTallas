"""Pipelined die reset tree (OWNER DECISION 2026-10-24 #2, RESET RULE, all dies; = KV-G3 option (b)).

Rule: exactly ONE root 2-flop reset synchroniser per die region (its async input is the only false path, a CDC by
design). From it the synchronised reset travels as a SYNCHRONOUS signal through relay flops every <= 405 um (the data
reach rule), with EQUAL depth to every partition reset tap, so every block releases on the same known cycle. Local
flops use the delivered reset with normal timed recovery / removal (or as a sync reset). No recovery waivers.

Plan form (top-level `reset`):

    "reset": {..., "mode": "pipelined",
              "tree": {"relay_max_um": 405, "depth": D,
                       "roots": [{"region": "core", "xy": [x, y], "part": P}],      # the one synchroniser per region
                       "chains": {"<partition>": {"region": "core", "relays": [[x, y] x D]}}}}

  relays[k] are die-frame relay flop sites; relays[-1] is the partition's reset tap (the delivered-reset flop);
  hop k = Manhattan(relays[k-1], relays[k]) with relays[-1 before 0] = the region root.  A partition type under the
  pipelined rule has reset {"tap_um", "mode": "delivered"} and NO own synchroniser (no sync_stages).

    python3 tools/die_plan/reset_tree.py plan PLAN.json [--root X,Y] [--region core] [--hop-target 364]
            [--out PLAN_OUT.json]        # writes the tree + per-type reset mode into the plan
    check(P, R) from check.py: rule 'reset_tree' (ERROR under --completeness when mode is pipelined; one WARN when a
            plan has not adopted the rule).

Relay sites avoid hard cores, hard-IP partitions and die.io windows (slid along the route; the hop budget is
re-checked after sliding).  The hop target (default 364 = 0.9 x 405) leaves the kit room to move a relay off a soft
macro.  Boot cost = 2 (synchroniser) + depth cycles, the same for every partition.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402

RELAY_MAX_UM = 405.0
EPS = 1e-6


def keepouts(P):
    """die-frame rects relays may not sit in: hard cores, hard-IP partition types, die.io windows."""
    ko = []
    for pn, p in P.parts.items():
        t = P.ptype(pn)
        if t.get("hard"):
            ko.append(P.rect(pn))
            continue
        for c in t.get("hard_cores", []) or []:
            (ox, oy), (w, h) = c["origin_um"], c["outline_um"]
            a, b = P.to_die(pn, (ox, oy)), P.to_die(pn, (ox + w, oy + h))
            ko.append((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])))
    for w in P.die.get("io", []) or []:
        ko.append(tuple(w["rect_um"]))
    return ko


def inside(ko, x, y, m=0.5):
    return any(r[0] - m < x < r[2] + m and r[1] - m < y < r[3] + m for r in ko)


def part_at(P, x, y):
    for pn in P.parts:
        r = P.rect(pn)
        if r[0] - EPS <= x <= r[2] + EPS and r[1] - EPS <= y <= r[3] + EPS:
            return pn
    return None


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def lpath(a, b, xfirst):
    c = (b[0], a[1]) if xfirst else (a[0], b[1])
    return [a, c, b]


def at(path, s):
    for p, q in zip(path, path[1:]):
        L = man(p, q)
        if s <= L + EPS:
            f = s / L if L else 0.0
            return (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f)
        s -= L
    return path[-1]


def chain(P, ko, root, tap, D, hop_max, step=4.32):
    """D relay sites root -> tap (last = tap), equal spacing along the better L route, slid off keep-outs."""
    best = None
    for xf in (True, False):
        path = lpath(root, tap, xf)
        L = sum(man(p, q) for p, q in zip(path, path[1:]))
        pts, slid = [], 0
        for k in range(1, D + 1):
            s0 = L * k / D
            if k == D:
                pts.append(tuple(tap))
                continue
            pt = at(path, s0)
            if inside(ko, *pt):
                found = None
                for j in range(1, int(hop_max / step)):
                    for sg in (-1, 1):
                        s = s0 + sg * j * step
                        if 0 < s < L:
                            q = at(path, s)
                            if not inside(ko, *q):
                                found = q
                                break
                    if found:
                        break
                if found is None:
                    pts = None
                    break
                pt, slid = found, slid + 1
            pts.append(pt)
        if pts is None:
            continue
        hops = [man(root, pts[0])] + [man(p, q) for p, q in zip(pts, pts[1:])]
        cand = (max(hops) > hop_max + EPS, slid, max(hops), pts)
        if best is None or cand[:3] < best[:3]:
            best = cand
    return None if best is None or best[0] else [[round(x, 3), round(y, 3)] for x, y in best[3]]


def reset_tap_die(P, pn):
    t = P.ptype(pn)
    rs = (t.get("reset") or {}).get("tap_um")
    if rs is None:
        ck = (t.get("clock") or {}).get("tap_um")
        if ck is None:
            return None
        rs = ck
    return P.to_die(pn, tuple(rs))


def plan(raw, root=None, region="core", hop_target=0.9 * RELAY_MAX_UM, relay_max=RELAY_MAX_UM):
    P = S.Plan(raw)
    ko = keepouts(P)
    if root is None:
        root = tuple(raw.get("clock", {}).get("spine", {}).get("root_um") or (P.W / 2.0, P.H / 2.0))
    root = tuple(root)
    if inside(ko, *root):       # slide the synchroniser off a core along +x / -x / +y / -y
        for j in range(1, 2000):
            c = [(root[0] + s * j * 4.32, root[1]) for s in (1, -1)] + [(root[0], root[1] + s * j * 4.32) for s in (1, -1)]
            c = [q for q in c if not inside(ko, *q) and part_at(P, *q)]
            if c:
                root = c[0]
                break
    taps = {pn: reset_tap_die(P, pn) for pn in P.parts if not P.ptype(pn).get("hard")}
    taps = {k: v for k, v in taps.items() if v is not None}
    Lmax = max(man(root, t) for t in taps.values())
    D = max(1, math.ceil(Lmax / hop_target))
    while True:
        chains, bad = {}, []
        for pn, tp in sorted(taps.items()):
            c = chain(P, ko, root, tp, D, relay_max)
            if c is None:
                bad.append(pn)
            chains[pn] = dict(region=region, relays=c)
        if not bad:
            break
        D += 1
        if D > 4 * math.ceil(Lmax / relay_max) + 8:
            raise SystemExit(f"reset_tree: no legal chain for {bad[:5]} up to depth {D}")
    tree = dict(relay_max_um=relay_max, depth=D, hop_target_um=round(hop_target, 3),
                roots=[dict(region=region, xy=[round(root[0], 3), round(root[1], 3)], part=part_at(P, *root))],
                chains=chains,
                boot_cycles=2 + D,
                note="OWNER 10-24 reset rule: one 2-flop synchroniser at roots[]; synchronous relay flops every "
                     f"<= {relay_max:g} um, depth {D} to every partition reset tap (release on cycle 2 + {D}); "
                     "relays[-1] = the partition's delivered-reset flop at its reset tap; reset_tree.py plan")
    out = json.loads(json.dumps(raw))
    out["reset"] = dict(raw.get("reset", {}), mode="pipelined", tree=tree)
    for tn, t in out["partition_types"].items():
        if t.get("hard") or "reset" not in t:
            continue
        r = {k: v for k, v in t["reset"].items() if k != "sync_stages"}
        r["mode"] = "delivered"
        t["reset"] = r
    hosts = {}
    for pn, c in chains.items():
        for x, y in c["relays"][:-1]:
            h = part_at(P, x, y)
            hosts[h] = hosts.get(h, 0) + 1
    return out, dict(depth=D, root=root, max_path_um=round(Lmax, 1), relays=sum(len(c["relays"]) for c in chains.values()),
                     foreign_relays_per_part=dict(sorted(hosts.items(), key=lambda x: -x[1])[:12]))


def check(P, R, raw=None):
    rs = P.reset if hasattr(P, "reset") else (raw or {}).get("reset", {})
    if rs.get("mode") != "pipelined":
        R.warn("reset_tree", "reset rule (OWNER 10-24 #2) not applied: no reset.mode 'pipelined' tree (one root "
               "synchroniser per region, synchronous relays <= 405 um, equal depth)")
        return dict(applied=False)
    tr = rs.get("tree") or {}
    hop_max = float(tr.get("relay_max_um", RELAY_MAX_UM))
    if hop_max > RELAY_MAX_UM + EPS:
        R.err("reset_tree", f"relay_max_um {hop_max:g} > {RELAY_MAX_UM:g} (data reach rule)")
    D = tr.get("depth")
    roots = {}
    for r in tr.get("roots", []):
        if r["region"] in roots:
            R.err("reset_tree", f"region {r['region']}: more than one root synchroniser")
        roots[r["region"]] = tuple(r["xy"])
    ko = keepouts(P)
    chains = tr.get("chains", {})
    worst = 0.0
    for pn in P.parts:
        t = P.ptype(pn)
        if t.get("hard") or "reset" not in t:
            continue
        if "sync_stages" in t["reset"] or t["reset"].get("mode") != "delivered":
            R.err("reset_tree", f"type {P.parts[pn]['type']}: own reset synchroniser under the pipelined rule "
                  "(reset.mode must be 'delivered', no sync_stages)", type=P.parts[pn]["type"], part=pn)
        c = chains.get(pn)
        if not c or not c.get("relays"):
            R.err("reset_tree", f"{pn}: no reset chain", part=pn)
            continue
        if c.get("region") not in roots:
            R.err("reset_tree", f"{pn}: chain region {c.get('region')} has no root", part=pn)
            continue
        rl = [tuple(x) for x in c["relays"]]
        if D is not None and len(rl) != D:
            R.err("reset_tree", f"{pn}: chain depth {len(rl)} != tree depth {D} (equal release cycle)", part=pn)
        tap = reset_tap_die(P, pn)
        if tap and man(tap, rl[-1]) > 1.0:
            R.err("reset_tree", f"{pn}: last relay {rl[-1]} is not the reset tap {tuple(round(v, 2) for v in tap)}",
                  part=pn)
        hops = [man(roots[c["region"]], rl[0])] + [man(a, b) for a, b in zip(rl, rl[1:])]
        worst = max(worst, max(hops))
        if max(hops) > hop_max + EPS:
            k = max(range(len(hops)), key=hops.__getitem__)
            R.err("reset_tree", f"{pn}: reset hop {k} = {hops[k]:.1f} um > {hop_max:g}", part=pn)
        kin = [x for x in rl[:-1] if inside(ko, *x, m=0.0)]
        if kin:
            R.err("reset_tree", f"{pn}: {len(kin)} relay sites inside a hard core / hard IP / io window (e.g. {kin[0]})",
                  part=pn)
    return dict(applied=True, depth=D, roots=len(roots), chains=len(chains), worst_hop_um=round(worst, 1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["plan"])
    ap.add_argument("plan_json")
    ap.add_argument("--root")
    ap.add_argument("--region", default="core")
    ap.add_argument("--hop-target", type=float, default=0.9 * RELAY_MAX_UM)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan_json).read_text())
    root = tuple(float(v) for v in a.root.split(",")) if a.root else None
    out, summ = plan(raw, root=root, region=a.region, hop_target=a.hop_target)
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=0) + "\n")
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
