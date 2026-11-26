#!/usr/bin/env python3
"""adv_rst_spread.py -- PRECHECK advisory RSTSPREAD (CLASS-OWNERS-R2, class C-RST-RELAY-REACH round 3; report only, never a gate).

RSTREACH (derived_drop.py) checks that START / local-reset RAW POINTERS name a live tap within reach.  It cannot see a reset
NET whose sinks are spread: 11-25/26 placed reviews found reset nets that are in reach at the tree but not at the sinks
(S81 lepw_mus_C XG ring 123 loads over 2116 um, COL P2 xrl nets 1403 / 1298 um, HEAD lep0N local_r[918] spread 1325 um with
2 seats in SRAM, lep0N_w built 606 um vs 56 um, KV IO_COR rst_n_t38 six terminals HPWL 1131 um, recovery -712 ps).

Model (plan only, no netlist).  Every FIRM-seated flop of the plan (ft_slots bit_sites_um / regs_um, internal_stations
regs_um / bit_sites_um / face_bit_sites_um, relay_sites seats, clock.sink_sites_um, sink bins where the plan has them) takes the
reset net of its NEAREST consumer tap -- the same nearest-tap rule reset_taps.tcl applies after FIRM placement.  Per tap net:
    fanout   sum of the seat weights (stage bits; sink counts)
    hpwl     half perimeter of the seat bounding box (um)
    far      the farthest seat from the tap relay (L1, um)
    regions  k_cover clusters of the seats within one reach box (default 405 um, CBC budget)
A net is WIDE when far > 405 um (the CBC reach), hpwl > 900 um, or fanout > 3000 loads (a registered tap that drives thousands of
flops gets a repair buffer chain, the measured recovery path: S81 col_h9 r1 -298 ps through fanout-60/64 buffers).  Thresholds are the calibrated defaults below (tools/die_plan/rst_spread_calib.py, report in the lane post).

    python3 adv_rst_spread.py PLAN [--tree TREE] [--types a,b] [--json OUT]       (exit 0; findings(...) for plan_advisory)
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

CHECK = "ADV-RSTSPREAD"
REACH_UM = 405.0
FAR_UM = float(os.environ.get("OT_RSTSPREAD_FAR_UM", "405"))
HPWL_UM = float(os.environ.get("OT_RSTSPREAD_HPWL_UM", "900"))
FANOUT = int(os.environ.get("OT_RSTSPREAD_FANOUT", "3000"))
SPLIT = int(os.environ.get("OT_RSTSPREAD_SPLIT", "1500"))       # construct: loads per region after the split
MAX_LINES = 25


def _pts(v):
    """flatten nested [[x, y], ...] / [[[x, y], ...], ...] into [(x, y)]"""
    out = []
    if isinstance(v, (list, tuple)):
        if len(v) >= 2 and all(isinstance(a, (int, float)) for a in v[:2]):
            out.append((float(v[0]), float(v[1])))
        else:
            for x in v:
                out += _pts(x)
    return out


def _bus_w(t):
    return {b["name"]: int(b.get("width") or 1) for b in t.get("buses") or [] if isinstance(b, dict) and "name" in b}


def seats(t, bins=None):
    """[(x, y, w, kind)] of every plan seat that carries a reset load"""
    out = []
    bw = _bus_w(t)
    for s in t.get("ft_slots") or []:
        if not isinstance(s, dict):
            continue
        bs = _pts(s.get("bit_sites_um"))
        if bs:
            out += [(x, y, 1, "ft_bit") for x, y in bs]
        else:
            w = int(s.get("width") or 1)
            out += [(x, y, w, "ft_reg") for x, y in _pts(s.get("regs_um"))]
    for e in t.get("internal_stations") or []:
        if not isinstance(e, dict):
            continue
        conn = str(e.get("conn") or "")
        bits = int(e.get("bits") or (bw.get(conn[4:], 1) if conn.startswith("bus:") else 1))
        ex = _pts(e.get("bit_sites_um")) + _pts(e.get("face_bit_sites_um"))
        if ex:
            out += [(x, y, 1, "st_bit") for x, y in ex]
        else:
            out += [(x, y, bits, "st_reg") for x, y in _pts(e.get("regs_um"))]
    for _k, v in (t.get("relay_sites") or {}).items():
        p = _pts(v)
        if p:
            out.append((p[0][0], p[0][1], 1, "relay_site"))
    for r in (t.get("clock") or {}).get("sink_sites_um") or []:
        if isinstance(r, (list, tuple)) and len(r) >= 2:
            out.append((float(r[0]), float(r[1]), int(r[2]) if len(r) > 2 else 1, "sink_site"))
    for b in bins or []:
        out.append((b[0], b[1], b[2], "bin"))
    return out


def l1(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def k_cover(items, reach):
    """items [(key, (x, y))] -> clusters within `reach` L1 of their own centre (strips in u = x + y, v = x - y; as reset_leg_plan)"""
    side = 2 * reach
    uv = sorted(((xy[0] + xy[1], xy[0] - xy[1], k, xy) for k, xy in items))
    out, i = [], 0
    while i < len(uv):
        j = i
        while j < len(uv) and uv[j][0] <= uv[i][0] + side + 1e-9:
            j += 1
        strip = sorted(uv[i:j], key=lambda r: (r[1], r[2]))
        m = 0
        while m < len(strip):
            n = m
            while n < len(strip) and strip[n][1] <= strip[m][1] + side + 1e-9:
                n += 1
            out.append([(r[2], r[3]) for r in strip[m:n]])
            m = n
        i = j
    return out


def net_metrics(taps, sts, reach=REACH_UM):
    """taps [(name, x, y)], seats [(x, y, w, kind)] -> {tap name: {fanout, hpwl, far, regions, n}} (nearest-tap rule)"""
    by = {}
    for i, (x, y, w, k) in enumerate(sts):
        j = min(range(len(taps)), key=lambda q: (l1(taps[q][1:], (x, y)), q))
        by.setdefault(j, []).append((i, x, y, w))
    out = {}
    for j, rows in by.items():
        xs = [r[1] for r in rows]
        ys = [r[2] for r in rows]
        tx, ty = taps[j][1], taps[j][2]
        out[taps[j][0]] = dict(
            fanout=sum(r[3] for r in rows), n=len(rows), hpwl=round((max(xs) - min(xs)) + (max(ys) - min(ys)), 1),
            far=round(max(l1((tx, ty), (r[1], r[2])) for r in rows), 1),
            regions=len(k_cover([(r[0], (r[1], r[2])) for r in rows], reach)), tap=[tx, ty])
    return out


def wide(m, far=None, hpwl=None, fanout=None):
    far = FAR_UM if far is None else far
    hpwl = HPWL_UM if hpwl is None else hpwl
    fanout = FANOUT if fanout is None else fanout
    return m["far"] > far or m["hpwl"] > hpwl or m["fanout"] > fanout


def read_bins(ck, plan_path, tree):
    f = ck.get("sink_bins_file")
    if not f:
        return None
    pd = Path(plan_path).resolve().parent if plan_path else Path(".")
    cands = [Path(f)] if os.path.isabs(f) else []
    for root in (tree, str(pd)):
        if root:
            cands.append(Path(root) / f)
    cands.append(pd / "sink_bins" / Path(f).name)
    for c in cands:
        if c.is_file():
            try:
                return [(float(r[0]), float(r[1]), float(r[2]) if len(r) > 2 else 1.0) for r in json.loads(c.read_text())["bins"]]
            except (OSError, ValueError, KeyError, TypeError):
                return None
    return None


def type_features(raw, plan_path, tree, tn, S=None, P=None):
    """{tap: metrics} for one type, or None when the type has no taps / seats"""
    import reset_tree as RT
    t = raw["partition_types"][tn]
    if S is None:
        import derived_drop as D
        S = D.Solver(raw, plan_path, tree)
    try:
        taps = RT.consumer_taps(P or S._plan(), tn)
    except Exception:  # noqa: BLE001 density taps that need inputs the plan dir lacks: the plan's own tap table (as adv_insertion_band)
        ck = t.get("clock") or {}
        taps = [(p.get("name"), float(p["xy"][0]), float(p["xy"][1])) for p in list(ck.get("taps") or []) + list(ck.get("added_taps") or [])
                if isinstance(p, dict) and p.get("xy") and not p.get("kind")]
        taps += [(f"reset_local_{j}", float(x), float(y)) for j, (x, y) in enumerate((t.get("reset") or {}).get("local_taps_um") or [])]
    sts = seats(t, read_bins(t.get("clock") or {}, plan_path, tree))
    if not taps or not sts:
        return None
    return net_metrics(taps, sts)


def features(raw, plan_path, tree=None, types=None, **_kw):
    import derived_drop as D
    S = D.Solver(raw, plan_path, tree)
    P = S._plan()
    out, err = {}, {}
    for tn in sorted(raw["partition_types"]):
        if types and tn not in types:
            continue
        if not isinstance(raw["partition_types"][tn], dict):
            continue
        try:
            f = type_features(raw, plan_path, tree, tn, S, P)
        except Exception as e:  # noqa: BLE001 a type without an evaluable tree is reported, not raised
            err[tn] = f"{type(e).__name__}: {str(e)[:160]}"
            continue
        if f:
            out[tn] = f
    return out, err


def summarize_type(f):
    """worst net of a type by (far, hpwl): its metrics + the number of wide nets"""
    worst = max(f.items(), key=lambda kv: (kv[1]["far"], kv[1]["hpwl"]))
    return dict(worst_tap=worst[0], **worst[1], wide_nets=sum(wide(m) for m in f.values()),
                max_fanout=max(m["fanout"] for m in f.values()), max_hpwl=max(m["hpwl"] for m in f.values()))


def findings(raw, plan_path=None, tree=None, types=None, **kw):
    feats, err = features(raw, plan_path, tree, set(types) if types else None)
    rows = []
    for tn, f in feats.items():
        w = {k: m for k, m in f.items() if wide(m)}
        if w:
            k, m = max(w.items(), key=lambda kv: (kv[1]["far"], kv[1]["hpwl"]))
            rows.append((m["far"], f"WARN {CHECK} {tn}: {len(w)} reset net(s) with spread sinks; worst {k}: {m['fanout']} loads over "
                         f"hpwl {m['hpwl']:g} um, farthest seat {m['far']:g} um from its tap, {m['regions']} {REACH_UM:g}-um region(s); "
                         f"fix: one relay stage per region (rst_reach_construct.py spread), report only"))
    rows.sort(key=lambda r: -r[0])
    out = [r[1] for r in rows][:MAX_LINES]
    out.append(f"WARN {CHECK} summary: {len(feats)} types judged, {len(rows)} wide, {len(err)} not evaluable; report only")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--tree")
    ap.add_argument("--types")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    only = set(filter(None, (a.types or "").split(",")))
    feats, err = features(raw, a.plan, a.tree, only)
    if a.json:
        Path(a.json).write_text(json.dumps(dict(types={tn: summarize_type(f) for tn, f in feats.items()},
                                                nets=feats, errors=err), indent=1) + "\n")
    for ln in findings(raw, a.plan, a.tree, only):
        print(ln)
    return 0


if __name__ == "__main__":
    sys.exit(main())
