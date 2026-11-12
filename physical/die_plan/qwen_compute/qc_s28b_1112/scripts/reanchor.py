#!/usr/bin/env python3
"""QC-S28-B: re-anchor the reset relays of street-rule-moved types (brief B2: reset_tree anchors, tol 405).
The legalize pass re-selected raw relay refs on ITS re-solved tree, but the bind builds reset_tree.for_type on the final
plan (boundary geometry restored), and the anchors still named the stage-1 relays -> RESET_ANCHOR 'lacks referenced
relay(s)'.  Here every START / local-reset reference is re-picked on the bind's own tree: same depth as the stage-1
anchor (+0 cycles), nearest non-ported relay to the referencing stage's site (its xy_um in the final plan; the stage-1
anchor site when the holder has none), within the anchor's tol_um; then the anchor is re-recorded (reset_anchor.record).
   reanchor.py PLAN_OLD PLAN_IN PLAN_OUT REPORT T1,T2,...   (run from the bind tree root)"""
import json, sys
from pathlib import Path
sys.path.insert(0, "tools/die_plan")
import schema, reset_tree as RT, reset_anchor as RA
old_p, src, out, rep, types = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5].split(",")
O = json.load(open(old_p))["partition_types"]
raw = json.load(open(src))
P = schema.Plan(raw, Path(src).parent / "die_plan.json")
R = {}
for tn in types:
    t, t0 = raw["partition_types"][tn], O[tn]
    ck, ck0 = t.get("clock") or {}, t0.get("clock") or {}
    a0 = ck0.get(RA.KEY)
    if not a0:
        R[tn] = "no anchor"; continue
    tol = float(a0.get("tol_um", 405))
    tree = RT.for_type(P, tn); port = RA.ported(tree)
    cand = {}
    for r in tree["relays"]:
        if RA.NAME.match(r["q"]) and r["q"] not in port:
            cand.setdefault(int(r["depth"]), []).append(r)
    r1, r0 = RA.refs(t), RA.refs(t0)
    if len(r1) != len(r0):
        R[tn] = f"ERROR ref count {len(r0)} -> {len(r1)}"; print(tn, R[tn]); continue
    moves, err, far = 0, None, 0.0
    for (c1, k1), (c0, k0) in zip(r1, r0):
        n0 = c0[k0]; a = a0["relays"].get(n0)
        if a is None:
            err = f"stage-1 ref {n0} not anchored"; break
        site = c1.get("xy_um") if isinstance(c1, dict) and c1.get("xy_um") else a["xy"]
        cs = cand.get(int(a["depth"]), [])
        if not cs:
            err = f"no depth-{a['depth']} relay"; break
        b = min(cs, key=lambda r: (abs(r["xy"][0] - site[0]) + abs(r["xy"][1] - site[1]), r["q"]))
        d = abs(b["xy"][0] - site[0]) + abs(b["xy"][1] - site[1])
        if d > tol:
            err = f"{n0}: nearest depth-{a['depth']} relay {b['q']} {d:.1f} um > {tol}"; break
        far = max(far, d)
        if c1[k1] != b["q"]:
            moves += 1
        c1[k1] = b["q"]
    if err:
        R[tn] = f"ERROR {err}"; print(tn, R[tn]); continue
    try:
        ck[RA.KEY] = RA.record(t, tree, ".", tol)
    except RA.AnchorError as e:
        R[tn] = f"ERROR {e}"; print(tn, R[tn]); continue
    R[tn] = dict(refs=len(r1), renamed=moves, max_site_um=round(far, 1), relays=len(ck[RA.KEY]["relays"]))
    print(tn, R[tn])
open(out, "w").write(json.dumps(raw, indent=1) + "\n")
json.dump(R, open(rep, "w"), indent=1)
