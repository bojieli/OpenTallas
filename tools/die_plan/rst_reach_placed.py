#!/usr/bin/env python3
"""rst_reach_placed.py (C-LEG405-R3 for C-RST-RELAY-REACH, 11-26): why KV PRE RSTREACH cannot tell a PASS type from a FAIL type, and the
placed term that can.  REPORT ONLY; never edits a plan, never gates.

The kit places every reset relay at its plan seat (gen/<type>/reset_tree.tcl rtr_place lines, FIRM + ff_put_near legalisation) and then
judges relay -> relay Manhattan hops against the 300 um generator gate: 'OT_RESET_TREE ... placed max hop X um, N hops > 300 um: PASS|FAIL'.
The plan side reads max_hop_um 275.0 on EVERY type (reset_tree.build caps the hop at the slew-safe relay_um minus a 25 um margin), so
PRE RSTREACH / the plan hop cannot separate the 7 FAIL trees from the 22 PASS trees.

Measured on 29 retained KV trees (35 kits, intel2 R/KV-*/ ot_face_flops.txt + gen/reset_tree.tcl, 34,644 edges, 5,121 at planned hop >= 265):
  * placed hop = planned hop + seat drift of both ends.  Drift p50 2.4 um, p95 7.3, p99 11.3, p99.9 35.4, max 56.3 (relay slid along its row to
    the next free site).  A cap edge (planned 267.5 - 275) fails only when the drift exceeds the 25 - 32 um of slack: 17 of 5,121 edges (0.33 %).
  * every failing edge has a planned hop >= 260 (v5 260.7 -> 304.0); no edge below 260 failed.
  * no plan-side number separates the types: relay count AUC 0.81, flops 0.81, near-cap edge count 0.53, hard-core-adjacent seats 0.49,
    a per-edge drift-tail model (this module's expected_fails) 0.51.  The failure is a rare legaliser tail on a few cap edges.
  * so the separating terms are the PLACED ones below: placed max hop, the edges over the gate with both seat drifts, and the count of
    edges inside the tail margin (headroom).  A re-seat row for a failing tree is the failing relay's placed seat (or a cap of 250 um in
    reset_tree for the type: an edge then needs > 50 um drift, 0.08 % of cap edges in the table above).

    python3 -I rst_reach_placed.py GEN_DIR [GEN_DIR ...] [--json OUT] [--plan PLAN]       GEN_DIR = kit gen/<type> with run/results/.../ot_face_flops.txt
"""
import glob
import json
import os
import re
import sys

GATE_UM = 300.0
CAP_UM = 275.0
NEAR_UM = 265.0          # planned hops from here are within the p99.9 drift (35 um) of the gate
# P(placed - planned hop > x) over the 5,121 KV edges with planned hop >= 265 (29 trees)
TAIL = ((5, 0.0701), (10, 0.01386), (15, 0.00625), (20, 0.00391), (25, 0.00332), (30, 0.00234), (35, 0.00234), (40, 0.00234), (50, 0.00078))
_PLACE = re.compile(r"^rtr_place(?:_opt)? (\S+) \{\*?(.+?)\[\./\]\*\} ([-\d.]+) ([-\d.]+) (\S+)")
_EDGES = re.compile(r"foreach \{q d\} \{([^}]*)\} \{")


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def p_exceed(x):
    """P(drift excess > x um) for one near-cap edge, step form of TAIL (conservative between steps; half the last step beyond it)"""
    prev = 1.0
    for xv, p in TAIL:
        if x < xv:
            return prev
        prev = p
    return prev * 0.5


def expected_fails(planned_hops, gate=GATE_UM, near=None):
    """plan-time term: expected number of edges over the gate = sum of P(excess > gate - hop) over the edges with hop >= NEAR_UM"""
    return sum(p_exceed(gate - h) for h in planned_hops if h >= (NEAR_UM if near is None else near))


def parse_plan(tcl_text):
    """(plan seat {q: (x, y)}, instance pattern {q: name}, edges [(q, d)]) of one gen/<type>/reset_tree.tcl"""
    plan, names = {}, {}
    for ln in tcl_text.splitlines():
        m = _PLACE.match(ln)
        if m and not m.group(1).startswith(("exp:", "run_root")) and ":copy" not in m.group(1):
            plan[m.group(1)] = (float(m.group(3)), float(m.group(4)))
            names[m.group(1)] = m.group(2)
    m = _EDGES.search(tcl_text)
    t = m.group(1).split() if m else []
    return plan, names, list(zip(t[0::2], t[1::2]))


def parse_placed(ff_text):
    """{instance: (x, y)} of the relay rows (tag rrl:*) of ot_face_flops.txt"""
    out = {}
    for ln in ff_text.splitlines():
        p = ln.split("\t")
        if len(p) >= 4 and p[1].startswith("rrl:"):
            try:
                out[p[0]] = (float(p[2]), float(p[3]))
            except ValueError:
                pass
    return out


def tree_report(tcl_text, ff_text, gate=GATE_UM):
    plan, names, edges = parse_plan(tcl_text)
    pbn = parse_placed(ff_text)
    placed = {}
    for q, nm in names.items():
        rg = re.compile("^" + "[./]".join(re.escape(x) for x in nm.split("[./]")) + "[./]")
        hit = [xy for k, xy in pbn.items() if "__rs" not in k and rg.match(k.replace("\\", ""))]
        if hit:
            placed[q] = hit[0]
    drift = {q: man(plan[q], placed[q]) for q in plan if q in placed}
    rows = []
    for q, d in edges:
        if q in plan and d in plan:
            hp = man(plan[q], plan[d])
            hq = man(placed[q], placed[d]) if q in placed and d in placed else None
            rows.append((q, d, hp, hq))
    hq = [r[3] for r in rows if r[3] is not None]
    over = sorted((r for r in rows if r[3] is not None and r[3] > gate), key=lambda r: -r[3])
    dv = sorted(drift.values())
    return dict(gate_um=gate, relays=len(plan), seated=len(placed), edges=len(rows), plan_max=round(max((r[2] for r in rows), default=0.0), 1),
                placed_max=round(max(hq), 1) if hq else None, n_over=len(over), verdict=("FAIL" if over else "PASS") if hq else "UNMEASURED",
                near_cap_edges=sum(1 for r in rows if r[2] >= gate - _SHIFT), expected_fails=round(expected_fails([r[2] for r in rows], gate, near=gate - _SHIFT), 2),
                drift_p95=round(dv[int(0.95 * (len(dv) - 1))], 1) if dv else None, drift_max=round(dv[-1], 1) if dv else None,
                drift_gt25=sum(1 for v in dv if v > 25),
                failing=[dict(q=q, d=d, plan_hop=round(hp, 1), placed_hop=round(hq_, 1), drift_q=round(drift.get(q, 0.0), 1),
                              drift_d=round(drift.get(d, 0.0), 1), plan_seat_q=plan[q], placed_seat_q=placed.get(q)) for q, d, hp, hq_ in over[:8]])


_LIM = re.compile(r"set rtr_lim \[expr \{\s*([0-9.]+)\s*\*")
_SHIFT = GATE_UM - NEAR_UM    # near-cap window below the gate


def kit_gate_um(tcl_text, default=GATE_UM):
    """the type's OWN placed-hop gate: the 'set rtr_lim [expr {N * $ff_dbu}]' the kit reset_tree.tcl itself judges PASS/FAIL against
    (HEAD 405, hd_spn_wshim_tx 300, hd_spn_wshim_rx 260; KV/S81 300).  GATE_UM is only the fallback when the line is absent."""
    m = _LIM.search(tcl_text)
    return float(m.group(1)) if m else default


def plan_gate_um(plan, default=GATE_UM):
    """the per-die gate a plan records as reset.reach_cap_um (HEAD 405; KV/S81 record none);
    `default` (the historic 300) when the plan records none.  plan = path, raw dict or reset section (cbc_rules.plan_reset_hop_cap)."""
    try:
        import cbc_rules as C
        v = C.plan_reset_hop_cap(plan)
    except Exception:  # noqa: BLE001 - older tree without cbc_rules
        v = None
    return float(v) if v else default


def gen_report(gen_dir, plan_gate=None):
    ff = glob.glob(os.path.join(gen_dir, "run/results/*/*/base/ot_face_flops.txt"))
    tcl = os.path.join(gen_dir, "reset_tree.tcl")
    if not ff or not os.path.isfile(tcl):
        return dict(verdict="UNMEASURED", why="no ot_face_flops.txt / reset_tree.tcl under " + gen_dir)
    with open(tcl, errors="replace") as a, open(ff[0], errors="replace") as b:
        t = a.read()
        return tree_report(t, b.read(), kit_gate_um(t, plan_gate if plan_gate else GATE_UM))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    out = None
    if "--json" in argv:
        i = argv.index("--json")
        out = argv[i + 1]
        del argv[i:i + 2]
    plan_gate = None
    if "--plan" in argv:     # gate order: the kit's own rtr_lim, else the plan's reset.reach_cap_um, else GATE_UM (300)
        i = argv.index("--plan")
        plan_gate = plan_gate_um(argv[i + 1], 0.0) or None
        del argv[i:i + 2]
    res = {}
    for g in argv:
        r = gen_report(g, plan_gate)
        res[g] = r
        print(f"WARN RST-REACH-PLACED {os.path.basename(g.rstrip('/'))}: {r['verdict']} plan max {r.get('plan_max')} um, placed max {r.get('placed_max')} um, "
              f"{r.get('n_over')} edge(s) > {r.get('gate_um', GATE_UM):g} um, {r.get('near_cap_edges')} near-cap edges (expected {r.get('expected_fails')}), "
              f"drift p95 {r.get('drift_p95')} / max {r.get('drift_max')} um (report only)")
        for f in r.get("failing", [])[:3]:
            print(f"    {f['q']} -> {f['d']}: plan {f['plan_hop']} -> placed {f['placed_hop']} um, seat drift {f['drift_q']} / {f['drift_d']} um")
    if out:
        with open(out, "w") as f:
            json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
