#!/usr/bin/env python3
"""S81 plan event, leaf early core taps (S81-TYPES-7-CTAP 11-08, class CORE-TAP-LATE).

Measured on leaf t27 a7 (4_1_cts.log OT_TAP_CORE): 21 of 25 hard-core clock pins sit outside 250 +/- 20 ps.  (a) The
cores left on grid taps (16 vp LN cores at 246 ps internal, vs 289, ve_s 274, rxsf 259) add a 53-262 ps grid-tap leg
and CTS pads every register on that grid tap to the core (t14 447 ps, t4 490, t22 388), so the reset relay half-cycle
hops crossing taps fail by up to -402 ps (S81-TYPES-7-T27 05:00).  (b) The kits place the facing-form macro positions
(wave item_env OT_MACRO_MOVES, 63 of 65 leaf rows), but the plan core taps stay at the plan positions, so a moved
core's early tap drop is hundreds of um from its pin (t27: vn_b tap at 892,968, vn_b placed at 510,881; vsw/vq
"early core tap still late").

Per ot_s81sl_leaf__* type:
  1. --moves ITEM_ENV.json (kit_wave s81 item_env): the row's OT_MACRO_MOVES positions (origin_um, orient,
     track_offset_um per gen_phys._CORE_TRACK_OFFSET) are applied to a COPY of the type; the core taps of steps 2-3
     are sited on that copy (the geometry the kit places) and only clock goes back to the plan.  hard_cores stay as
     planned and the env entry stays the kit's move.  --bake also writes the moves into hard_cores: on main that
     exposed 2228 G0C errors (R3-INTERNAL bundles up to 1191 um, core_faces, ft stations under macros) and 9
     tap-budget bind stops (11-08 14:1x UTC), the facing form's own class, so it is not the default.  Rows in
     --skip-bake keep the plan positions (already composed by S81-TYPES-7-LEAFB) and get step 4.
  2. Existing core taps of a moved core are re-sited beside its moved clock pin (insertion/budget kept).
  3. early_core_taps.add(leg_ps=60, window_ps=20, merge=True): a clock pin gets its own early core tap (clk_c<k>,
     appended, existing port numbers kept) when TT lib max_clock_tree_path rise + 60 > 250 - 20; insertion_ps = that
     rise (the number tap_balance.tcl reads), insertion_ff_ps = the FF lib rise when an _ff.lib sits beside it.
  4. (--bake or composed rows) A grid+explicit added tap (clock.added_taps) that a baked or composed move left inside a macro halo, outside the
     outline or within tap spacing (taps.grid_explicit_sites, the G0 schema rule) is re-sited to the nearest legal
     point (schema.tap_clear, strict); legal added taps are not touched.  If that point fails the bind budget
     (taps.grid_explicit_taps: radius <= 1.10 x tap_radius_um, load <= cap, non-empty), or the baked moves made any
     added tap fail it, the legal points on 2.16-um rings around that tap are tried nearest first (budget_fix).
Asserted: nothing else in a type changes (hard_cores only origin/orient/track_offset of baked moves).
    python3 delta_leaf_core_taps_1108.py PLAN_IN PLAN_OUT REPORT.json [--moves item_env.json] [--skip-bake t1,t5 --ref PLAN0]
    (cwd = repo root)
"""
import argparse
import copy
import functools
import json
import re
import sys
from pathlib import Path

sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
import early_core_taps as E  # noqa: E402
import cores as C  # noqa: E402
import schema  # noqa: E402
from schema import tap_clear  # noqa: E402
from plan_event_1104 import plan_text  # noqa: E402

LEG_PS, WINDOW_PS, COMMON_PS = 60.0, 20.0, 250.0
LEAF = re.compile(r"^ot_s81sl_leaf__t\d+")
TRACK = {"R0": [0.108, 0.012], "MY": [0.132, 0.012], "MX": [0.108, 0.036], "R180": [0.132, 0.036]}

_res = functools.lru_cache(maxsize=None)(lambda p, root=None: C.resolve(p, root))
_lef = functools.lru_cache(maxsize=None)(lambda path, macro=None: C.lef_pins(path, macro))
_libck = functools.lru_cache(maxsize=None)(lambda path: C.lib_clocks(path))


def _clock_pins(core, root=None):
    if core.get("lib") and _res(core["lib"], root).is_file():
        ck = _libck(_res(core["lib"], root))
        if ck:
            return ck
    return C.clock_pins(core, root)


E.resolve, E.lef_pins, E.clock_pins = _res, _lef, _clock_pins


def ff_rise(c, pin):
    lib = c.get("lib") or ""
    if not lib.endswith("_tt.lib"):
        return None
    ff = _res(lib[:-len("_tt.lib")] + "_ff.lib")
    if not ff.is_file():
        return None
    v = _libck(ff).get(pin)
    return round(v["rise"], 5) if v else None


def pin_xy(t, c, pin):
    """the same transformed pin point early_core_taps.add uses"""
    x, y = c["origin_um"]; w, h = c["outline_um"]
    g = _lef(_res(c["lef"]), c.get("module"))
    pp = g.get(pin) or g.get(pin.split("[")[0])
    px, py = pp["xy"] if pp and pp.get("xy") else (w / 2, 0.)
    o = c.get("orient", "R0")
    if o in ("MY", "R180"):
        px = w - px
    if o in ("MX", "R180"):
        py = h - py
    dx, dy = c.get("track_offset_um", [0., 0.])
    return x + dx + px, y + dy + py


def bake(t, tn, moves):
    out = []
    cores = {c["inst"]: c for c in t.get("hard_cores", [])}
    for e in moves.split(","):
        f = e.split(":")
        c = cores[f[0]]
        o_old = c.get("orient", "R0")
        o_new = f[3] if len(f) == 4 else o_old
        frm = (list(c["origin_um"]), o_old)
        c["origin_um"] = [float(f[1]), float(f[2])]
        c["orient"] = o_new
        if c.get("track_offset_um") == TRACK.get(o_old) or "track_offset_um" not in c:
            c["track_offset_um"] = list(TRACK[o_new])
        out.append(dict(inst=f[0], frm=frm, to=(c["origin_um"], o_new)))
    return out


def _legal(t, x, y, taken, boxes):
    eps, clear = 1e-8, schema.TAP_CLEAR_UM
    w, h = t["outline_um"]
    return (clear - eps <= x <= w - clear + eps and clear - eps <= y <= h - clear + eps
            and not any(abs(x - a) < clear - eps and abs(y - b) < clear - eps for a, b in taken)
            and not any(a + eps < x < c - eps and b + eps < y < d - eps for a, b, c, d in boxes))


def _budget_err(PL, tn):
    """None when the bind budget passes, else the added tap name it stops on"""
    import taps as TP
    try:
        TP.grid_explicit_taps(PL, tn)
        return None
    except ValueError as e:
        m = re.search(r"grid\+explicit tap (\S+) load=", str(e))
        if not m:
            raise
        return m.group(1)


def budget_fix(PL, tn, t, ck, boxes, row, rounds=8, tries=300):
    """An added tap the bind budget stops on (taps.grid_explicit_taps: radius > 1.10 x tap_radius_um, load > cap or
    empty), because the baked moves changed the sink or macro geometry: try the legal points on 2.16-um rings around
    it, nearest first, and keep the first that clears that tap without making another one fail first."""
    for _ in range(rounds):
        bad = _budget_err(PL, tn)
        if bad is None:
            return
        p = next(q for q in ck["added_taps"] if q["name"] == bad)
        grid = [(gx, gy) for _, gx, gy in schema._grid_taps(PL, tn)]
        others = grid + [tuple(q["xy"]) for q in ck["added_taps"] if q is not p]
        x0, y0 = p["xy"]
        best, tried = None, 0
        for _, cx, cy in _ring_points(x0, y0):
            if tried >= tries:
                break
            if not _legal(t, cx, cy, others, boxes):
                continue
            tried += 1
            p["xy"] = [round(cx, 4), round(cy, 4)]
            e = _budget_err(PL, tn)
            if e != bad:
                best = p["xy"]
                break
        if best is None:
            p["xy"] = [x0, y0]
            raise AssertionError((tn, bad, "no legal site within budget"))
        row.setdefault("added_budget_resited", []).append(dict(name=bad, frm=[x0, y0], to=best, tried=tried))
    assert _budget_err(PL, tn) is None, (tn, "added tap budget")


def budget_fix_fast(PL, tn, t, ck, boxes, row, rounds=12, reach=129.6, step=8.64, top=12):
    """S81-TYPES-8 11-08: the bind budget (taps.grid_explicit_taps: added tap load <= cap, non-empty, L1 radius <=
    1.10 x tap_radius_um) by MOVING the failing added tap (no new tap, no deleted tap, so ports stay).  Sinks + reset
    relays are read once; candidate sites = legal points (TAP_CLEAR halo, outline, spacing) on an 8.64-um lattice within
    `reach` L1 of the tap; each is scored on the kit split (taps.assign, nearest + cap) by (violating added taps,
    summed overrun, worst radius ratio); the best wins; the real grid_explicit_taps confirms at the end."""
    import taps as TP, reset_tree as RT
    import numpy as np
    if _budget_err(PL, tn) is None:
        return
    cap = int(ck.get("tap_max_sinks", 1500)); R = float(ck.get("tap_radius_um", 200.)); lim = R * TP.ADDED_TAP_RADIUS_SLACK
    n_grid = len(schema._grid_taps(PL, tn))
    sinks = TP.sink_sites(PL, tn)
    if not t.get("hard"):
        sinks = sinks + [(float(r["xy"][0]), float(r["xy"][1]), 1.0) for r in RT.for_type(PL, tn).get("relays", [])]
    S = np.array([(s[0], s[1]) for s in sinks]); W = np.array([s[2] for s in sinks])
    def score(out, exact=False):
        if exact:
            load, far, _ = TP.assign(out, sinks, cap, R, max_distance_um=R)
        else:
            X = np.array([(o[1], o[2]) for o in out])
            D = np.abs(S[:, None, 0] - X[None, :, 0]) + np.abs(S[:, None, 1] - X[None, :, 1])
            a = D.argmin(1); load = np.bincount(a, weights=W, minlength=len(out))
            far = np.zeros(len(out)); np.maximum.at(far, a, D[np.arange(len(a)), a])
        bad = [i for i in range(n_grid, len(out)) if load[i] > cap or load[i] == 0 or far[i] > lim + 1e-6]
        over = sum(max(0.0, far[i] - lim) for i in bad) + sum(1000.0 for i in bad if load[i] == 0 or load[i] > cap)
        return (len(bad), round(over, 3), max(far[n_grid:], default=0) / R), bad, far
    added = ck["added_taps"]
    for _ in range(rounds):
        out = TP.grid_explicit_sites(PL, tn)
        names = [o[0] for o in out]
        s0, bad, far = score(out, exact=True)
        if not bad:
            break
        i = max(bad, key=lambda k: far[k])
        p = next(q for q in added if q["name"] == names[i])
        x0, y0 = map(float, p["xy"])
        others = [(o[1], o[2]) for k, o in enumerate(out) if k != i]
        n = int(reach / step); cands = []
        for a in range(-n, n + 1):
            for b in range(-n, n + 1):
                if 0 < (abs(a) + abs(b)) * step <= reach:
                    cx, cy = round(x0 + a * step, 4), round(y0 + b * step, 4)
                    if _legal(t, cx, cy, others, boxes):
                        o2 = list(out); o2[i] = (names[i], cx, cy)
                        cands.append((score(o2)[0], abs(a) + abs(b), cx, cy))
        cands.sort()
        best = None
        for sc, _, cx, cy in cands[:top]:
            o2 = list(out); o2[i] = (names[i], cx, cy)
            se = score(o2, exact=True)[0]
            if se < s0 and (best is None or se < best[0]):
                best = (se, cx, cy)
        assert best is not None, (tn, names[i], "no better legal site within reach")
        row.setdefault("added_budget_moved", []).append(dict(name=names[i], frm=[x0, y0], to=[best[1], best[2]], score=list(best[0])))
        p["xy"] = [best[1], best[2]]
    e = _budget_err(PL, tn)
    assert e is None, (tn, e, "added tap budget after moves")


def _ring_points(x0, y0, rmax=216.0, step=2.16):
    pts = []
    n = int(rmax / step)
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            d = (i * i + j * j) ** 0.5 * step
            if 0 < d <= rmax:
                pts.append((d, x0 + i * step, y0 + j * step))
    pts.sort()
    return pts


def fix_added(P, report):
    """step 4: the same legality walk as taps.grid_explicit_sites, re-siting only the illegal added taps"""
    from placement_obstacles import placement_boxes
    PL = schema.Plan(P)
    n, todo = 0, []
    for tn in sorted(report):
        t = P["partition_types"][tn]
        ck = t.get("clock", {})
        if ck.get("tap_mode") != "grid+explicit" or not ck.get("added_taps"):
            continue
        if PL.types[tn] is not t:
            # schema.Plan gives landing-pin types a separated copy: share the one added_taps list so the
            # budget check reads the sites edited here
            PL.types[tn].setdefault("clock", {})["added_taps"] = ck["added_taps"]
        boxes = list(placement_boxes(t, halo=schema.TAP_CLEAR_UM).values())
        taken = [(x, y) for _, x, y in schema._grid_taps(PL, tn)]
        for p in ck["added_taps"]:
            x, y = map(float, p["xy"])
            if not _legal(t, x, y, taken, boxes):
                nx, ny = tap_clear(t, x, y, taken, clear=schema.TAP_CLEAR_UM, strict=True)
                nx, ny = round(nx, 4), round(ny, 4)
                assert _legal(t, nx, ny, taken, boxes), (tn, p["name"], nx, ny)
                report[tn].setdefault("added_resited", []).append(dict(name=p["name"], frm=[x, y], to=[nx, ny]))
                p["xy"] = [nx, ny]
                x, y = nx, ny
                n += 1
            taken.append((x, y))
        todo.append((tn, t, ck, boxes))
    # second pass: the reset wavefront solve behind the budget reads every leaf type, so all sites are legal first
    for tn, t, ck, boxes in todo:
        budget_fix_fast(PL, tn, t, ck, boxes, report[tn])
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("rep")
    ap.add_argument("--moves"); ap.add_argument("--skip-bake", default="")
    ap.add_argument("--bake", action="store_true", help="also write the OT_MACRO_MOVES positions into hard_cores "
                    "(default: hard_cores unchanged, core taps sited for the moved kit positions only)")
    ap.add_argument("--ref", help="plan before an earlier composed move event (--skip-bake rows): cores whose origin/orient differ from it count as moved")
    a = ap.parse_args()
    P = json.loads(Path(a.src).read_text())
    env = json.loads(Path(a.moves).read_text()) if a.moves else {}
    ref = json.loads(Path(a.ref).read_text())["partition_types"] if a.ref else {}
    skip = {s if s.startswith("ot_s81sl_leaf__") else "ot_s81sl_leaf__" + s for s in a.skip_bake.split(",") if s}
    keep = {tn: {k: v for k, v in t.items() if k not in ("clock", "hard_cores")}
            for tn, t in P["partition_types"].items()}
    report, total, resited, baked = {}, 0, 0, 0
    for tn in sorted(P["partition_types"]):
        if not LEAF.match(tn):
            continue
        t0 = P["partition_types"][tn]
        t0.setdefault("clock", {})
        t = t0
        row = dict(resited=[], added=[])
        mv = (env.get(tn) or {}).get("OT_MACRO_MOVES")
        if mv and tn not in skip:
            if not a.bake:
                t = copy.deepcopy(t0)   # the kit geometry: sites are computed on it, only clock goes back
            row["baked" if a.bake else "sited_for_moves"] = bake(t, tn, mv)
            baked += 1
        moved = {b["inst"] for b in row.get("baked") or row.get("sited_for_moves") or []}
        if tn in skip and tn in ref:
            rc = {c["inst"]: (c["origin_um"], c.get("orient", "R0")) for c in ref[tn].get("hard_cores", [])}
            moved |= {c["inst"] for c in t.get("hard_cores", [])
                      if rc.get(c["inst"]) != (c["origin_um"], c.get("orient", "R0"))}
            row["composed_moved"] = sorted(moved)
        taps = t["clock"].get("taps", []) or []
        others = lambda me: [x["xy"] for x in taps if x is not me and x.get("xy")]
        for tp in taps:
            if tp.get("kind") != "core" or "core_group" in tp:
                continue
            inst, pin = tp["name"].rsplit(".", 1) if "." in tp["name"] else (tp["name"], None)
            c = next((c for c in t["hard_cores"] if c["inst"] == inst), None)
            if c is None:
                inst, pin = tp["name"], None
                c = next((c for c in t["hard_cores"] if tp["name"].startswith(c["inst"] + ".")), None)
                if c is None:
                    continue
                inst, pin = c["inst"], tp["name"][len(c["inst"]) + 1:]
            if inst not in moved:
                continue
            pin = pin or next(iter(_clock_pins(c)), "clk")
            x, y = pin_xy(t, c, pin)
            old = list(tp["xy"])
            tp["xy"] = list(tap_clear(t, x, y, others(tp), clear=4.32))
            tp["note"] = (tp.get("note", "") + " | CORE-TAP-LATE 11-08: re-sited beside the kit (OT_MACRO_MOVES) macro position").strip(" |")
            row["resited"].append(dict(name=tp["name"], frm=old, to=tp["xy"]))
            resited += 1
        new = E.add(t, common_ps=COMMON_PS, leg_ps=LEG_PS, window_ps=WINDOW_PS, merge=True)
        for tp in new:
            inst, pin = tp["name"].rsplit(".", 1)
            c = next(c for c in t["hard_cores"] if c["inst"] == inst)
            f = ff_rise(c, pin)
            if f is not None:
                tp["insertion_ff_ps"] = f
            tp["note"] = ("CORE-TAP-LATE 11-08 (S81-TYPES-7-CTAP): early core tap, TT lib max_clock_tree_path rise "
                          f"+ {LEG_PS:g} ps min grid leg > {COMMON_PS:g} - {WINDOW_PS:g}")
            row["added"].append(dict(name=tp["name"], module=c["module"], insertion_ps=tp["insertion_ps"],
                                     insertion_ff_ps=tp.get("insertion_ff_ps"), xy=tp["xy"]))
        if t is not t0:
            t0["clock"] = t["clock"]
        total += len(new)
        report[tn] = row
    added_fixed = fix_added(P, {tn: r for tn, r in report.items() if r.get("baked") or r.get("composed_moved")})
    for tn, t in P["partition_types"].items():
        assert {k: v for k, v in t.items() if k not in ("clock", "hard_cores")} == keep[tn], tn
    Path(a.out).write_text(plan_text(P))
    mods = {}
    for r in report.values():
        for x in r["added"]:
            mods[x["module"]] = mods.get(x["module"], 0) + 1
    summary = dict(leaf_types=len(report), types_with_new_taps=sum(1 for r in report.values() if r["added"]),
                   taps_added=total, types_baked=baked, core_taps_resited=resited,
                   added_taps_resited=added_fixed, types_added_resited=sum(1 for r in report.values() if r.get("added_resited")),
                   added_taps_budget_resited=sum(len(r.get("added_budget_resited", [])) for r in report.values()), added_taps_budget_moved=sum(len(r.get("added_budget_moved", [])) for r in report.values()), by_module=dict(sorted(mods.items())))
    Path(a.rep).write_text(json.dumps(dict(summary=summary, types=report), indent=1) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
