#!/usr/bin/env python3
"""HEAD-CORE-R20: the COORD 11:15 (HEAD-CORE-R19 ruling 3) approved plan delta, applied to the s81_head plan in place.
(a) the 26-slot declared-slot island delta of the R19 tree (results/s81_head_r20_plan/slot_delta_r19.json, copied from
    claude/head-r19-tree-1027@6acfb0b663 results/s81_head_r19/tree/slot_delta.json): appended to
    partition_types.<t>.clock.die_islands_um, per type (identical on every instance, 12.2a1).
(b) the spine-trunk M9 riser: the y-trunk nodes sit at die x 8760.96 = a VDD M9 stripe centre; the trunk legs run on the
    free M9 lane at 8769.6 (8.64 um riser at each trunk node), recorded as clock.spine.trunk.
Fail-closed: every slot rect is 8.64 x 8.64, centred on its site, inside the type outline, off every hard core of the type,
and not already declared; the trunk lane clears every die PG stripe of its layer (all widths/pitches in die.pg.grid AND
the --also-pg-width alternatives, e.g. the HEAD-5 12.96 M9) by >= --min-space; riser = |lane - node|.
  head_r19_island_riser_delta.py PLAN SLOT_DELTA --report OUT.json [--undo-check]"""
import argparse, copy, hashlib, json, sys
from pathlib import Path

SIDE = 8.64
NODE_X, LANE_X, LAYER = 8760.96, 8769.6, "M9"
CLK_W = 0.32


def overlaps(a, b):
    return a[0] < b[2] - 1e-9 and b[0] < a[2] - 1e-9 and a[1] < b[3] - 1e-9 and b[1] < a[3] - 1e-9


def stripes(g, lo, hi):
    """(net, x0, x1) of every stripe of grid entry g between lo and hi (nets alternate along the pitch)."""
    w, p, o, nets = g["width_um"], g["pitch_um"], g["offset_um"], g["nets"]
    step = p / len(nets)
    k0 = int((lo - o) // step) - 2
    out = []
    for k in range(k0, k0 + int((hi - lo) / step) + 6):
        c = o + k * step
        out.append((nets[k % len(nets)], round(c - w / 2, 4), round(c + w / 2, 4), round(c, 4)))
    return out


def lane_check(P, extra_widths, min_space):
    rows = []
    for g in P["die"]["pg"]["grid"]:
        if g["layer"] != LAYER:
            continue
        for w in [g["width_um"]] + list(extra_widths):
            gg = dict(g, width_um=w)
            near = stripes(gg, LANE_X - 40, LANE_X + 40)
            lane = (LANE_X - CLK_W / 2, LANE_X + CLK_W / 2)
            sp = min(max(s[1] - lane[1], lane[0] - s[2]) for s in near)
            node_on = [s for s in near if s[1] <= NODE_X <= s[2]]
            rows.append(dict(width_um=w, pitch_um=g["pitch_um"], offset_um=g["offset_um"], lane_min_space_um=round(sp, 4),
                             node_x_on_stripe=[s[0] + "@" + str(s[3]) for s in node_on],
                             verdict="PASS" if sp >= min_space else "FAIL"))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("slot_delta")
    ap.add_argument("--report", required=True)
    ap.add_argument("--also-pg-width", type=float, action="append", default=[12.96])
    ap.add_argument("--min-space", type=float, default=0.5)
    a = ap.parse_args()
    pp = Path(a.plan)
    P0 = json.loads(pp.read_text()); P = copy.deepcopy(P0)
    D = json.loads(Path(a.slot_delta).read_text())
    errs, added = [], {}
    for tn, v in sorted(D["types"].items()):
        slots = v.get("slots", [])
        if not slots:
            continue
        T = P["partition_types"][tn]
        W, H = T["outline_um"]
        cores = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
                  c["origin_um"][1] + c["outline_um"][1]) for c in T.get("hard_cores", []) or []]
        isl = T.setdefault("clock", {}).setdefault("die_islands_um", [])
        have = {tuple(round(x, 3) for x in r) for r in isl}
        for s in slots:
            r = [round(x, 3) for x in s["rect_um"]]; cx, cy = s["centre_um"]
            if abs(r[2] - r[0] - SIDE) > 1e-6 or abs(r[3] - r[1] - SIDE) > 1e-6:
                errs.append(f"{tn} {r}: not {SIDE} square")
            if abs((r[0] + r[2]) / 2 - cx) > 1e-6 or abs((r[1] + r[3]) / 2 - cy) > 1e-6:
                errs.append(f"{tn} {r}: not centred on {s['centre_um']}")
            if r[0] < -1e-9 or r[1] < -1e-9 or r[2] > W + 1e-9 or r[3] > H + 1e-9:
                errs.append(f"{tn} {r}: outside outline {W}x{H}")
            for k in cores:
                if overlaps(r, k):
                    errs.append(f"{tn} {r}: overlaps hard core {k}")
            if tuple(r) in have:
                errs.append(f"{tn} {r}: already declared")
            isl.append(r); have.add(tuple(r))
        added[tn] = len(slots)
    lane = lane_check(P, a.also_pg_width, a.min_space)
    if any(x["verdict"] != "PASS" for x in lane):
        errs.append(f"trunk lane {LANE_X} fails PG clearance: {lane}")
    sp = P["clock"]["spine"]
    sp["trunk"] = dict(layer=LAYER, node_x_um=NODE_X, lane_x_um=LANE_X, riser_um=round(abs(LANE_X - NODE_X), 3))
    # undo check: only die_islands_um of the 3 types and clock.spine.trunk differ
    U = copy.deepcopy(P)
    del U["clock"]["spine"]["trunk"]
    for tn, n in added.items():
        del U["partition_types"][tn]["clock"]["die_islands_um"][-n:]
    if U != P0:
        errs.append("undo check: plan differs beyond the delta")
    rep = dict(plan_in=hashlib.sha256(pp.read_bytes()).hexdigest(), slot_delta=a.slot_delta,
               slot_delta_sha256=hashlib.sha256(Path(a.slot_delta).read_bytes()).hexdigest(),
               added=added, total=sum(added.values()), trunk=sp["trunk"], lane_pg=lane, errors=errs)
    if not errs:
        pp.write_text(json.dumps(P, indent=2) + "\n")
        rep["plan_out"] = hashlib.sha256(pp.read_bytes()).hexdigest()
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep, indent=1))
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
