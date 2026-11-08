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
  1. --moves ITEM_ENV.json (kit_wave s81 item_env): the row's OT_MACRO_MOVES is baked into hard_cores (origin_um,
     orient, track_offset_um per gen_phys._CORE_TRACK_OFFSET), so plan, die checks and kit agree; the env entry is then
     a no-op (same position).  Rows in --skip-bake keep the plan positions (already composed by S81-TYPES-7-LEAFB).
  2. Existing core taps of a moved core are re-sited beside its moved clock pin (insertion/budget kept).
  3. early_core_taps.add(leg_ps=60, window_ps=20, merge=True): a clock pin gets its own early core tap (clk_c<k>,
     appended, existing port numbers kept) when TT lib max_clock_tree_path rise + 60 > 250 - 20; insertion_ps = that
     rise (the number tap_balance.tcl reads), insertion_ff_ps = the FF lib rise when an _ff.lib sits beside it.
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("rep")
    ap.add_argument("--moves"); ap.add_argument("--skip-bake", default="")
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
        t = P["partition_types"][tn]
        t.setdefault("clock", {})
        row = dict(baked=[], resited=[], added=[])
        mv = (env.get(tn) or {}).get("OT_MACRO_MOVES")
        if mv and tn not in skip:
            row["baked"] = bake(t, tn, mv)
            baked += 1
        moved = {b["inst"] for b in row["baked"]}
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
            tp["note"] = (tp.get("note", "") + " | CORE-TAP-LATE 11-08: re-sited beside the baked macro move").strip(" |")
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
        total += len(new)
        report[tn] = row
    for tn, t in P["partition_types"].items():
        assert {k: v for k, v in t.items() if k not in ("clock", "hard_cores")} == keep[tn], tn
    Path(a.out).write_text(plan_text(P))
    mods = {}
    for r in report.values():
        for x in r["added"]:
            mods[x["module"]] = mods.get(x["module"], 0) + 1
    summary = dict(leaf_types=len(report), types_with_new_taps=sum(1 for r in report.values() if r["added"]),
                   taps_added=total, types_baked=baked, core_taps_resited=resited, by_module=dict(sorted(mods.items())))
    Path(a.rep).write_text(json.dumps(dict(summary=summary, types=report), indent=1) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
