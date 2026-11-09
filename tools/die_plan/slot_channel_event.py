#!/usr/bin/env python3
"""TYPE-SAFE-2-AREA 11-08 (OWNER 11-08 (B) macro congestion budget; brief item 3): macro-edge CHANNEL REPACK plan event.

Channel model (TS1 a/ts_area.py, M4-M7 = 4 layers): for every hard-core edge facing another core (overlapping
projection, nothing between) or the outline, need = pins on the facing faces x 0.048 / (LAYERS x 0.7); deficit =
need - gap.  A die re-tile cannot grow S81 slots by the approved +349/+291 without breaking abutment (lattice
stretch needs >= +443/+357, see the queue post), so this event works INSIDE the current outline:

  per axis, the type's "free" lines are the x (y) intervals no hard core spans.  A deficit channel can only widen
  where its gap holds free lines; slack is moved there from free lines whose every containing channel has surplus
  (greedy transfer, never driving any channel below min(need, its old gap)).  The result is ONE monotone
  piecewise-linear map per axis: slope 1 over every core span (cores move rigidly by a grid-snapped shift), free
  intervals rescaled.  The map is applied to every type-local coordinate (hard_cores/contents origins, internal
  station sites, ft bit sites, clock taps / relays / bands, ...) EXCEPT points on the two faces parallel to the axis
  (face windows, ft in/out windows, chain face ends stay put: the slot's abutment and die ports are untouched).
  Outline, buses, pins_file, track_offset, RTL: unchanged.  Remaining deficits are reported per core face (re-pin /
  RE-FORM asks).

  python3 -I tools/die_plan/slot_channel_event.py BASE OUT EVENT --pins-root DIR [--skip-types a,b] [--only-types a,b]
                                                  [--layers 4] [--analyze]
"""
import argparse
import copy
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
EPS = 1e-6
OPP = dict(N="S", S="N", E="W", W="E")
_PC = {}


def pins_of(hc, root):
    pins = [(p["name"], *p["xy"]) for p in hc.get("pins", [])]
    pf = hc.get("pins_file")
    if pf:
        if pf not in _PC:
            f = Path(root) / pf
            js = json.loads(f.read_text()) if f.exists() else []
            js = js.get("pins", js) if isinstance(js, dict) else js
            _PC[pf] = [(q.get("name") or f"{q['bus']}[{q.get('bit', 0)}]", q["x"], q["y"]) for q in js]
        pins += _PC[pf]
    return pins


def face_counts(hc, root):
    cw, ch = hc["outline_um"]
    o = hc.get("orient", "R0")
    c = defaultdict(int)
    for nm, x, y in pins_of(hc, root):
        if "clk" in nm or nm.startswith("strap_"):
            continue
        f = min([(x, "W"), (cw - x, "E"), (y, "S"), (ch - y, "N")])[1]
        if o in ("MX", "R180") and f in "NS":
            f = OPP[f]
        if o in ("MY", "R180") and f in "EW":
            f = OPP[f]
        c[f] += 1
    return c


def boxes_of(t, root):
    out = []
    for hc in t.get("hard_cores", []):
        dx, dy = hc.get("track_offset_um", [0, 0])
        x0, y0 = hc["origin_um"][0] + dx, hc["origin_um"][1] + dy
        w, h = hc["outline_um"]
        out.append((x0, y0, x0 + w, y0 + h, face_counts(hc, root), hc["inst"]))
    return out


def channels(t, boxes, layers):
    """[(axis, lo, hi, need, core, face)] for every facing pair / core-outline edge with pins (TS1 model)"""
    W, H = t["outline_um"]
    out = []
    for i, a in enumerate(boxes):
        for f, ax in (("E", 0), ("N", 1), ("W", 0), ("S", 1)):
            best, nb = None, None
            for j, b in enumerate(boxes):
                if i == j:
                    continue
                if f == "E" and b[0] >= a[2] - EPS and min(a[3], b[3]) - max(a[1], b[1]) > 1:
                    g = b[0] - a[2]
                elif f == "N" and b[1] >= a[3] - EPS and min(a[2], b[2]) - max(a[0], b[0]) > 1:
                    g = b[1] - a[3]
                else:
                    continue
                if best is None or g < best:
                    best, nb = g, b
            if f in "WS":
                # only the outline edge for W/S (core<->core pairs are counted once from E/N)
                has = any((b[2] <= a[0] + EPS and min(a[3], b[3]) - max(a[1], b[1]) > 1) if f == "W" else
                          (b[3] <= a[1] + EPS and min(a[2], b[2]) - max(a[0], b[0]) > 1) for b in boxes if b is not a)
                if has:
                    continue
                lo, hi = (0.0, a[0]) if f == "W" else (0.0, a[1])
                pins = a[4][f]
            elif nb is None:
                lo, hi = (a[2], W) if f == "E" else (a[3], H)
                pins = a[4][f]
            else:
                lo, hi = (a[2], nb[0]) if f == "E" else (a[3], nb[1])
                pins = a[4][f] + nb[4][OPP[f]]
            if pins == 0 or hi - lo < -EPS:
                continue
            out.append((ax, lo, max(lo, hi), pins * 0.048 / (layers * 0.7), a[5], f))
    return out


def free_intervals(boxes, ax, L):
    sp = sorted((b[ax], b[ax + 2]) for b in boxes)
    out, cur = [], 0.0
    for a, b in sp:
        if a > cur + EPS:
            out.append([cur, a])
        cur = max(cur, b)
    if L > cur + EPS:
        out.append([cur, L])
    # zero-length cut lines: a core edge that no core spans strictly (abutted cores, gap 0) can still open
    have = {round(v, 4) for iv in out for v in iv}
    for e in sorted({round(v, 4) for a, b in sp for v in (a, b)}):
        if 0 < e < L and e not in have and not any(a < e - EPS and b > e + EPS for a, b in sp):
            out.append([e, e])
    return sorted(out)


def plan_axis(chs, fr, grid):
    """greedy slack transfer -> new free-interval lengths; returns (new_lengths, rows)"""
    L = [b - a for a, b in fr]
    n = list(L)
    mem = [[j for j, (a, b) in enumerate(fr) if a >= lo - EPS and b <= hi + EPS] for (_, lo, hi, _, _, _) in chs]
    gap = [hi - lo for (_, lo, hi, _, _, _) in chs]
    floor = [min(need, g) for (_, _, _, need, _, _), g in zip(chs, gap)]
    in_ch = defaultdict(list)
    for i, js in enumerate(mem):
        for j in js:
            in_ch[j].append(i)

    def cur(i):
        return gap[i] + sum(n[j] - L[j] for j in mem[i])
    order = sorted(range(len(chs)), key=lambda i: cur(i) - chs[i][3])
    for i in order:
        need = chs[i][3]
        if cur(i) >= need - EPS or not mem[i]:
            continue
        recv = max(mem[i], key=lambda j: L[j])
        for k in sorted(range(len(fr)), key=lambda k: -n[k]):
            d = need - cur(i)
            if d <= EPS:
                break
            if k in mem[i]:
                continue
            cap = n[k] - 0.0
            for i2 in in_ch[k]:
                if recv in mem[i2]:
                    continue          # a channel holding both donor and receiver keeps its width
                cap = min(cap, cur(i2) - floor[i2])
            # receiver may sit in channels too: they only gain
            cap = math.floor(max(0.0, min(cap, d)) / grid + EPS) * grid if grid else max(0.0, min(cap, d))
            if cap <= EPS:
                continue
            n[k] -= cap
            n[recv] += cap
    rows = []
    for i, (ax, lo, hi, need, core, face) in enumerate(chs):
        g1 = cur(i)
        if gap[i] < need - EPS or g1 < need - EPS:
            rows.append(dict(core=core, face=face, gap=round(gap[i], 2), need=round(need, 2), new_gap=round(g1, 2),
                             short=round(max(0.0, need - g1), 2)))
    return n, rows


def axis_map(fr, n):
    """monotone map x -> x' with slope 1 outside free intervals; free interval j scaled to n[j]"""
    knots = []
    acc = 0.0
    for (a, b), nj in zip(fr, n):
        knots.append((a, a + acc))
        acc += nj - (b - a)
        knots.append((b, b + acc))

    def m(x):
        prev = (0.0, 0.0)
        for (k, v) in knots:
            if x <= k + EPS:
                if (k - prev[0]) <= EPS:
                    return x + (v - k)
                return prev[1] + (x - prev[0]) * (v - prev[1]) / (k - prev[0])
            prev = (k, v)
        return x + (prev[1] - prev[0])
    return m


def transform_type(t, mx, my, W, H):
    """apply (mx, my) to every type-local coordinate; face points of the axis-parallel faces stay"""
    def pt(p):
        x, y = p[0], p[1]
        nx = x if (abs(y) < EPS or abs(y - H) < EPS) else mx(x)
        ny = y if (abs(x) < EPS or abs(x - W) < EPS) else my(y)
        return [round(nx, 4), round(ny, 4)] + list(p[2:])

    def rect(r):
        return pt(r[:2])[:2] + pt(r[2:4])[:2] + list(r[4:])
    SIZE = {"outline_um", "track_offset_um", "bit_site_cell_um", "window_um", "in_window_um", "out_window_um",
            "width_um", "pitch_um", "keepouts_um"}

    def walk(x, key=None):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in SIZE:
                    continue
                if k == "origin_um" and "outline_um" in x and x is not t:
                    continue                  # handled by the caller (rigid move)
                x[k] = walk(v, k)
            return x
        if isinstance(x, list):
            if x and all(isinstance(v, (int, float)) for v in x):
                if key and ("rect" in key) and len(x) == 4:
                    return rect(x)
                if len(x) >= 2 and key and (key.endswith("_um") or key in ("xy", "root", "outs")):
                    return pt(x)
                return x
            return [walk(v, key) for v in x]
        return x
    for hc in t.get("hard_cores", []):          # rigid: the core span (origin + track offset) moves by the map's shift
        dx, dy = hc.get("track_offset_um", [0, 0])
        o = hc["origin_um"]
        cx, cy = o[0] + dx + 0.5 * hc["outline_um"][0], o[1] + dy + 0.5 * hc["outline_um"][1]
        sx, sy = mx(cx) - cx, my(cy) - cy        # span midpoint: slope 1 there, no edge ambiguity
        hc["origin_um"] = [round(o[0] + sx, 4), round(o[1] + sy, 4)]
    for c in t.get("contents", []):
        for cc in [c] + list(c.get("physical_parts", [])):
            if "origin_um" in cc:
                o = cc["origin_um"]
                cc["origin_um"] = [round(mx(o[0]), 4), round(my(o[1]), 4)]
    walk(t)
    return t


def build(raw, root, skip, only, layers, grid, analyze):
    Q = copy.deepcopy(raw)
    edits, report = [], []
    for tn in sorted(Q["partition_types"]):
        t = Q["partition_types"][tn]
        if tn in skip or (only and tn not in only) or t.get("hard") or not t.get("hard_cores"):
            continue
        W, H = t["outline_um"]
        bx = boxes_of(t, root)
        chs = channels(t, bx, layers)
        if not any(hi - lo < need - EPS for (_, lo, hi, need, _, _) in chs):
            continue
        res = {}
        for ax, Lx in ((0, W), (1, H)):
            c = [ch for ch in chs if ch[0] == ax]
            fr = free_intervals(bx, ax, Lx)
            n, rows = plan_axis(c, fr, grid)
            res[ax] = (fr, n, rows)
        moved = any(abs(a - b) > EPS for ax in (0, 1) for a, b in zip(res[ax][1], [r[1] - r[0] for r in res[ax][0]]))
        d0 = sum(max(0.0, need - (hi - lo)) for (_, lo, hi, need, _, _) in chs)
        d1 = sum(r["short"] for ax in (0, 1) for r in res[ax][2])
        row = dict(type=tn, channels=len(chs), deficit_um=round(d0, 1), remaining_um=round(d1, 1),
                   resolved_um=round(d0 - d1, 1), moved=moved,
                   open=sorted([r for ax in (0, 1) for r in res[ax][2] if r["short"] > 0], key=lambda r: -r["short"])[:8])
        report.append(row)
        if moved and not analyze:
            mx = axis_map(res[0][0], res[0][1])
            my = axis_map(res[1][0], res[1][1])
            transform_type(t, mx, my, W, H)
            edits.append(row)
    return Q, edits, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("event")
    ap.add_argument("--pins-root", required=True)
    ap.add_argument("--skip-types", default="")
    ap.add_argument("--only-types", default="")
    ap.add_argument("--layers", type=float, default=4.0)
    ap.add_argument("--grid", type=float, default=0.864, help="snap of every slack transfer (um)")
    ap.add_argument("--analyze", action="store_true")
    a = ap.parse_args(argv)
    raw_b = Path(a.base).read_bytes()
    P0 = json.loads(raw_b)
    skip = {s for s in a.skip_types.split(",") if s}
    only = {s for s in a.only_types.split(",") if s} or None
    Q, edits, report = build(P0, a.pins_root, skip, only, a.layers, a.grid, a.analyze)
    touched = {e["type"] for e in edits}
    for k in P0:
        if k != "partition_types" and json.dumps(P0[k], sort_keys=True) != json.dumps(Q[k], sort_keys=True):
            raise AssertionError(f"top-level key {k} changed")
    for tn, v in P0["partition_types"].items():
        v1 = Q["partition_types"][tn]
        if tn not in touched and json.dumps(v, sort_keys=True) != json.dumps(v1, sort_keys=True):
            raise AssertionError(f"type {tn} changed but is not listed")
        for k in ("outline_um", "buses", "params", "module", "rtl"):
            if json.dumps(v.get(k), sort_keys=True) != json.dumps(v1.get(k), sort_keys=True):
                raise AssertionError(f"type {tn}: {k} changed")
    if not a.analyze:
        import schema as S
        base_errs = set(map(str, S.validate(copy.deepcopy(P0))))
        errs = [e for e in map(str, S.validate(copy.deepcopy(Q))) if e not in base_errs]
        if errs:
            raise SystemExit("slot_channel_event: output fails schema validation: " + "; ".join(errs[:5]))
        Path(a.out).write_text(json.dumps(Q, indent=1) + "\n")
    data = Path(a.out).read_bytes() if not a.analyze else b""
    rec = dict(schema="opentallas.slot_channel_event.v1", tool="tools/die_plan/slot_channel_event.py",
               owner="OWNER 2026-11-08 (B) macro congestion budget; lane TYPE-SAFE-2-AREA",
               base_plan=str(a.base), base_plan_sha256=hashlib.sha256(raw_b).hexdigest(),
               plan_output=None if a.analyze else str(a.out),
               plan_output_sha256=hashlib.sha256(data).hexdigest() if data else None,
               layers=a.layers, grid_um=a.grid, skipped_types=sorted(skip), edits=edits, report=report,
               totals=dict(types_with_deficit=len(report), types_moved=len(edits),
                           deficit_um=round(sum(r["deficit_um"] for r in report), 1),
                           resolved_um=round(sum(r["resolved_um"] for r in report), 1),
                           remaining_um=round(sum(r["remaining_um"] for r in report), 1),
                           fully_resolved=sum(1 for r in report if r["remaining_um"] <= EPS)))
    Path(a.event).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec["totals"]))


if __name__ == "__main__":
    main()
