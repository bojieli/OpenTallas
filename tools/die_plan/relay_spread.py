#!/usr/bin/env python3
"""RELAY-SPREAD (CLASS-OWNERS-B, class C-RELAY-SEAT signature (b), 2026-11-26): relay stacks spread over legal bit sites.

PRE ADV-RELAY-SEAT (adv_fpconv.relay_seats) reports "(x, y) xN on one point": more than RELAY_STACK relays of a type with the SAME
relay_sites point.  The writers (type_relay_sites.py, kit_istations / bind_*_split rows, link_sites ...) give a point per bus or lane,
so every bit of the bus (and every stage of its delay pipe) carries the same coordinate: S81 bk_sel__t2 x277 per point, KV kv3_hg x68,
QC cbf_q01 x55.  The kit seats a plan site with face_flops.tcl ff_put_near (nearest free cell of the station grid, spiral), so the
placer already spreads the stack; the plan just does not say where.  This tool does it in the plan, deterministically, so the seats
are exact (bit order kept, stage order of one bit adjacent) and the planned site equals the seated site.

Opt-in, default OFF.  Plan top-level flag (schema: relay_spread):
    "relay_spread": {"enable": 1, "stack_min": 5, "max_um": 25, "halo_um": 6}
Flag absent (and no --enable): the tool is a no-op, --out-plan is a byte copy of the input, nothing is written.

What changes: only partition_types[t].relay_sites VALUES of keys that share a point with more than stack_min - 1 others (the point
group), nothing else in the plan.  Per group of n keys at point P:
  - lattice = the kit's station grid: column pitch COL_UM (2.16 = 40 sites), row pitch ROW_UM * row_mult (0.27 * 1, 2 or 3; the
    sparsest multiplier whose n nearest free cells all lie within max_um of P is used);
  - free cell = inside the outline (margin 1 um), outside every hard core grown by halo_um, not used by another group or by a
    site that is not part of a stack;
  - the n nearest free cells (L1 to P) are taken, sorted row by row (serpentine), and the keys (sorted by their last index = bit, then name) are
    assigned in that order, so one bit's stages (r[0][b] .. q[b]) are neighbours and the bits run in order;
  - a group that does not fit within max_um is KEPT as it was (reported).
Leg guard: a leg to a fixed endpoint grows by at most the displacement of the seat, so max_um is capped at the hop margin
(reach 405 - the type's longest planned hop: relay_depth rows path_um / (D + 1), else 380 = type_relay_sites --reach) and at
0.3 x clock.tap_radius_um (default 200); a type with no margin is kept whole.

  relay_spread.py --row IN OUT REPORT [--types T ...]     row_gate.py script row (always on; the output plan has no relay_spread key)
  relay_spread.py PLAN OUT_DIR [--types T ...] [--enable] [--stack-min 5] [--max-um 25] [--halo 6] [--out-plan PLAN_OUT]
OUT_DIR/<type>/relay_spread_sites.json   changed relay_sites keys (the row, merged like pipeseat_sites.json)
OUT_DIR/report.json                      per type: groups, keys moved, kept groups + reason, max displacement, stack count before / after
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_geom_static as G  # noqa: E402

FLAG = "relay_spread"
COL_UM = 2.16          # ff_cpitch = 40 sites x 0.054
ROW_UM = 0.27
REACH_UM = 405.0
PLANNED_HOP_UM = 380.0
DEFAULTS = {"stack_min": 5, "max_um": 25.0, "halo_um": 6.0, "margin_um": 1.0, "tap_frac": 0.3}
INT = re.compile(r"\d+")


def flag_cfg(plan, enable=False, **over):
    """-> merged config dict, or None when the flag is absent / off and not forced"""
    f = plan.get(FLAG)
    if isinstance(f, dict) and f.get("enable"):
        cfg = dict(DEFAULTS)
        cfg.update({k: v for k, v in f.items() if k in DEFAULTS})
    elif enable:
        cfg = dict(DEFAULTS)
    else:
        return None
    cfg.update({k: v for k, v in over.items() if v is not None})
    return cfg


def bit_key(name):
    ints = INT.findall(name)
    return (int(ints[-1]) if ints else -1, [int(s) if s.isdigit() else s for s in re.split(r"(\d+)", name)])


def hop_margin(t):
    """um a seat may move without a planned hop passing REACH_UM"""
    hop = PLANNED_HOP_UM
    for r in t.get("relay_depth") or []:
        if isinstance(r, dict) and isinstance(r.get("path_um"), (int, float)):
            hop = max(hop, float(r["path_um"]) / (int(r.get("D") or 0) + 1))
    return max(0.0, REACH_UM - hop)


def point_groups(sites):
    g = collections.defaultdict(list)
    for k, p in sites.items():
        try:
            g[(round(float(p[0]), 1), round(float(p[1]), 1))].append(k)
        except (TypeError, ValueError, IndexError):
            continue
    return g


def cell_of(x, y):
    return int(round(x / COL_UM)), int(round(y / ROW_UM))


def spread_type(t, cfg):
    """-> (changed {key: [x, y]}, report); t is not modified"""
    sites = t.get("relay_sites") or {}
    groups = {p: ks for p, ks in point_groups(sites).items() if len(ks) >= cfg["stack_min"]}
    rep = {"sites": len(sites), "stack_points_before": len(groups), "stacked_keys": sum(len(v) for v in groups.values()),
           "groups_spread": 0, "groups_kept": 0, "keys_moved": 0, "max_disp_um": 0.0, "kept": [], "kept_groups": []}
    if not groups:
        rep["stack_points_after"] = 0
        return {}, rep
    margin = hop_margin(t)
    tap = float((t.get("clock") or {}).get("tap_radius_um") or 200.0)
    dmax = min(float(cfg["max_um"]), margin, cfg["tap_frac"] * tap)
    rep["max_um_used"] = round(dmax, 2)
    if dmax < COL_UM:
        rep["groups_kept"] = len(groups)
        rep["kept"].append(["*", "no hop/tap margin %.1f um" % dmax])
        rep["kept_groups"] = [[p[0], p[1], len(ks)] for p, ks in sorted(groups.items())]
        rep["stack_points_after"] = len(groups)
        return {}, rep
    o = t.get("outline_um") or [1e9, 1e9]
    W, H = float(o[0]), float(o[1])
    m = float(cfg["margin_um"])
    boxes = [(x0 - cfg["halo_um"], y0 - cfg["halo_um"], x1 + cfg["halo_um"], y1 + cfg["halo_um"]) for x0, y0, x1, y1, _n in G.hard_rects(t)]

    def blocked(x, y):
        if x < m or y < m or x > W - m or y > H - m:
            return True
        return any(b[0] < x < b[2] and b[1] < y < b[3] for b in boxes)

    stacked = {k for ks in groups.values() for k in ks}
    used = set()
    for k, p in sites.items():
        if k not in stacked:
            try:
                used.add(cell_of(float(p[0]), float(p[1])))
            except (TypeError, ValueError, IndexError):
                pass
    changed = {}
    for (px, py), ks in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        n = len(ks)
        pick = None
        for mult in (3, 2, 1):
            cells = []
            c0, r0 = cell_of(px, py)
            nc = int(dmax / COL_UM) + 1
            nr = int(dmax / (ROW_UM * mult)) + 1
            for dc in range(-nc, nc + 1):
                for dr in range(-nr, nr + 1):
                    c, r = c0 + dc, r0 + dr * mult
                    if (c, r) in used:
                        continue
                    x, y = c * COL_UM, r * ROW_UM
                    d = abs(x - px) + abs(y - py)
                    if d > dmax or blocked(x, y):
                        continue
                    cells.append((d, c, r))
            if len(cells) >= n:
                cells.sort()
                pick = cells[:n]
                break
        if pick is None:
            rep["groups_kept"] += 1
            rep["kept"].append([[px, py], "%d keys: no %d free cells within %.1f um" % (n, n, dmax)])
            rep["kept_groups"].append([px, py, n])
            continue
        for _d, c, r in pick:
            used.add((c, r))
        pick.sort(key=lambda e: (e[2], e[1]))
        rows = collections.OrderedDict()
        for e in pick:
            rows.setdefault(e[2], []).append(e)
        pick = [e for i, r in enumerate(rows.values()) for e in (r if i % 2 == 0 else r[::-1])]   # serpentine: neighbours stay neighbours
        for k, (d, c, r) in zip(sorted(ks, key=bit_key), pick):
            xy = [round(c * COL_UM, 3), round(r * ROW_UM, 3)]
            if xy != [sites[k][0], sites[k][1]]:
                changed[k] = xy
            rep["max_disp_um"] = max(rep["max_disp_um"], round(abs(xy[0] - px) + abs(xy[1] - py), 2))
        rep["groups_spread"] += 1
    rep["keys_moved"] = len(changed)
    new_sites = dict(sites)
    new_sites.update(changed)
    rep["stack_points_after"] = sum(1 for ks in point_groups(new_sites).values() if len(ks) >= cfg["stack_min"])
    return changed, rep


def spread_plan(plan, cfg):
    """-> (new plan dict, {type: report}); the input is not modified.  Types without a stack are returned as the same objects."""
    reports, out = {}, dict(plan)
    pt = dict(plan["partition_types"])
    for tn, t in sorted(pt.items()):
        if not isinstance(t, dict) or not t.get("relay_sites"):
            continue
        changed, rep = spread_type(t, cfg)
        if rep["stack_points_before"]:
            reports[tn] = rep
        if changed:
            nt = dict(t)
            ns = dict(t["relay_sites"])
            ns.update(changed)
            nt["relay_sites"] = ns
            pt[tn] = nt
            rep["_changed"] = changed
    out["partition_types"] = pt
    return out, reports


def row_main(argv):
    """row_gate.py script row: relay_spread.py --row IN OUT REPORT [--types T ...] [--stack-min N] [--max-um U]: always on (the row IS the
    intent), writes the plan without a relay_spread key (a tool tree without the schema entry still binds it)."""
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("report")
    ap.add_argument("--types", nargs="*")
    ap.add_argument("--stack-min", type=int)
    ap.add_argument("--max-um", type=float)
    A = ap.parse_args(argv)
    plan = json.loads(Path(A.inp).read_text())
    cfg = flag_cfg(plan, True, stack_min=A.stack_min, max_um=A.max_um)
    plan.pop(FLAG, None)
    only = set(A.types) if A.types else None
    src = plan["partition_types"]
    new, reports = spread_plan({**plan, "partition_types": {k: v for k, v in src.items() if only is None or k in only}}, cfg)
    for tn, t in new["partition_types"].items():
        src[tn] = t
    for rep in reports.values():
        rep.pop("_changed", None)
    Path(A.out).write_text(json.dumps(plan, separators=(",", ":")) + "\n")
    Path(A.report).write_text(json.dumps({"config": cfg, "types": reports}, indent=1) + "\n")
    print(f"relay_spread row: {sum(r['keys_moved'] for r in reports.values())} keys moved in {sum(1 for r in reports.values() if r['keys_moved'])} types")
    return 0


def main(argv=None):
    if (argv if argv is not None else sys.argv[1:])[:1] == ["--row"]:
        return row_main((argv if argv is not None else sys.argv[1:])[1:])
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("out_dir")
    ap.add_argument("--types", nargs="*")
    ap.add_argument("--enable", action="store_true", help="run without the plan flag")
    ap.add_argument("--stack-min", type=int)
    ap.add_argument("--max-um", type=float)
    ap.add_argument("--halo", type=float, dest="halo_um")
    ap.add_argument("--out-plan")
    A = ap.parse_args(argv)
    src = Path(A.plan).read_bytes()
    plan = json.loads(src)
    cfg = flag_cfg(plan, A.enable, stack_min=A.stack_min, max_um=A.max_um, halo_um=A.halo_um)
    if cfg is None:
        print("relay_spread: plan flag absent / off (no --enable): nothing changed")
        if A.out_plan:
            Path(A.out_plan).write_bytes(src)
        return 0
    if A.types:
        plan = dict(plan)
        plan["partition_types"] = {k: v for k, v in plan["partition_types"].items() if k in A.types}
        full = json.loads(src)
    else:
        full = None
    new, reports = spread_plan(plan, cfg)
    out = Path(A.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = {"plan": A.plan, "config": cfg, "types": {}}
    for tn, rep in reports.items():
        ch = rep.pop("_changed", {})
        summary["types"][tn] = rep
        if ch:
            (out / tn).mkdir(parents=True, exist_ok=True)
            (out / tn / "relay_spread_sites.json").write_text(json.dumps(ch, indent=0, sort_keys=True) + "\n")
        print(f"{tn}: stack points {rep['stack_points_before']}->{rep['stack_points_after']} keys moved {rep['keys_moved']} "
              f"groups spread {rep['groups_spread']} kept {rep['groups_kept']} max disp {rep['max_disp_um']} um")
    (out / "report.json").write_text(json.dumps(summary, indent=1) + "\n")
    if A.out_plan:
        res = full if full is not None else new
        if full is not None:
            for tn, t in new["partition_types"].items():
                res["partition_types"][tn] = t
        Path(A.out_plan).write_text(json.dumps(res, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
