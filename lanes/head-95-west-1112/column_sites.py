#!/usr/bin/env python3
"""column_sites.py PLAN OUT --types T1,T2 --spans SWEEPDIR [--inset 10] [--rounds 2]   (HEAD-95 rp18, COORD fallback)

Reset entry derived from the PARENT exit, not by hand: for each listed soft type, take the wavefront solve's parent of
its instances (all instances must share the parent type + parent out site, else error), map that parent rst_o site
into the child frame (inverse of Plan.to_die, so mirrored/rotated instances work), clamp it into the child's logic span
(SWEEPDIR/<type>.json "span", the sink-bin 1-99 % box + macros, shrunk by --inset) and write it as
reset.in_sites[type].  The solver then re-picks every parent out (face sites near the new entries); repeated --rounds
times so a chain (eshim_rx -> eshim_tx, turn_a -> turn_b) settles.  Prints per type: old/new entry, parent, die hop."""
import argparse, json, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("out")
ap.add_argument("--types", required=True); ap.add_argument("--spans", required=True)
ap.add_argument("--inset", type=float, default=10.0); ap.add_argument("--rounds", type=int, default=2)
ap.add_argument("--tools", default=".")
a = ap.parse_args()
sys.path.insert(0, a.tools)
import schema, reset_tree as RT  # noqa: E402

raw = json.load(open(a.plan))
types = a.types.split(",")
span = {t: json.load(open(Path(a.spans) / f"{t}.json"))["span"] for t in types}


def inv(P, p, X, Y):
    o = P.to_die(p, (0.0, 0.0)); ex = P.to_die(p, (1.0, 0.0)); ey = P.to_die(p, (0.0, 1.0))
    a11, a21 = ex[0] - o[0], ex[1] - o[1]; a12, a22 = ey[0] - o[0], ey[1] - o[1]
    det = a11 * a22 - a12 * a21
    dx, dy = X - o[0], Y - o[1]
    return ((a22 * dx - a12 * dy) / det, (-a21 * dx + a11 * dy) / det)


for rnd in range(a.rounds):
    P = schema.Plan(raw, a.plan)
    r = RT.wf_solve(P)
    for t in types:
        inst = [p for p in P.parts if P.parts[p]["type"] == t and r["parent"].get(p)]
        keys = {(P.parts[r["parent"][p][0]]["type"], r["parent"][p][1]) for p in inst}
        if len(keys) != 1:
            # several parent forms: use the most common one, report the rest
            from collections import Counter
            c = Counter((P.parts[r["parent"][p][0]]["type"], r["parent"][p][1]) for p in inst)
            key = c.most_common(1)[0][0]
            print(f"  {t}: {len(keys)} parent forms {dict(c)}, using {key}")
        else:
            key = next(iter(keys))
        p0 = next(p for p in inst if (P.parts[r["parent"][p][0]]["type"], r["parent"][p][1]) == key)
        q, j, d = r["parent"][p0]
        X, Y = P.to_die(q, RT.face_sites(P, P.parts[q]["type"])[j]["xy"])
        x, y = inv(P, p0, X, Y)
        b = span[t]
        x = min(max(x, b[0] + a.inset), b[2] - a.inset); y = min(max(y, b[1] + a.inset), b[3] - a.inset)
        old = r["choice"][t]
        raw.setdefault("reset", {}).setdefault("in_sites", {})[t] = [round(x, 3), round(y, 3)]
        print(f"round {rnd} {t}: entry {old} -> {raw['reset']['in_sites'][t]} (parent {P.parts[q]['type']} site {j}, hop was {d})")

P = schema.Plan(raw, a.plan)
r = RT.wf_solve(P)
print("FINAL")
for t in types:
    hops = sorted({r["parent"][p][2] for p in P.parts if P.parts[p]["type"] == t and r["parent"].get(p)})
    print(f"  {t}: entry {r['choice'][t]} outs {r['outs'].get(t)} hops {hops}  unreachable "
          f"{sorted(p for p in r['unreachable'] if P.parts[p]['type'] == t)}")
json.dump(raw, open(a.out, "w"), indent=1)
