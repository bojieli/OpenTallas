#!/usr/bin/env python3
"""QC-A0 10-24: A0 v8 core clock taps = the v7 taps (R4 grid 6 + v6 sink additions, gen_a0c7_taps.py) with the taps
that F1 empties MOVED to where F1 puts the sinks, plus ADDITIONS where the hub's sink density needs them (clock rule,
BRIEFING decision 5 (b): taps on a grid sized by sink density, ~1000-1500 sinks/tap, extra taps at dense clusters,
none over hard children).

F1 (gen_a0c8_regions.py): every head's ring writers + readers (rung-0 landed crossing) sit in the hub (the former
empty LSL slot, x 205.8-316.8, y 658.4-829.0) and the E LSL column is mirrored (pin faces into the 35-um channel).
Per-tap loads are estimated with taps_sim.py (tools/die_plan/clock_taps.tcl rule: nearest tap, cap 1500, re-assign
<= 120 um) on the v8 sink sites (budget.py: boxed groups uniform in their boxes, FREE cells at their v7 sites):
  v7 taps on v8 sinks: the hub sink taps carry 1.6-4.1k each (NK 12.9k / NL 14.0k), the E-margin taps ck_t33 / ck_t36 (NK;
  NL ck_t34 / ck_t36)
  carry 0 (their v7 loads were the E-face readers).
  v8: those two E-margin taps move into the hub and four taps are added there, so the hub carries 12 (NK) / 12 (NL)
  taps of <= 1500 sinks (estimate: no tap over the cap, reach <= ~155 um; EST.json = taps_sim.py on the v8 sites).
Names: v7 names are kept (a moved tap keeps its port; the die spine drop moves with it); additions continue the
numbering (NK ck_t38..ck_t41, NL ck_t37..ck_t40) and need RTL ports (OT_A0_CK_TAPS42 / OT_A0_CK_TAPS41, no loads) and the plan
declaration (physical/die_plan/qwen_compute/inputs/a0_core_taps.json).
Reset landing copies: each copy goes to the tap nearest the centroid of its loads on the v8 sites (budget.py
--dump-ends), the a0_reset_taps6.tcl rule ("nearest its placed site") applied to the v8 floorplan.

    gen_a0c8_taps.py nk|nl ENDS.json [EST.json]     writes tools/qwen_romleaf/a0core/{qfd_tile_<k>_a0c8_pins.tcl, a0c8_<k>_taps.json,
                                         a0c8_<k>_rst_taps.tsv}
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from gen_a0c6_taps import free_x  # noqa: E402
from gen_a0c7_taps import snap_y, clear_of  # noqa: E402

SEP_UM = 8.64
# moved taps (v7 name -> target before snapping) and additions, per variant
PLAN = {
    "nk": dict(move={"ck_t33": (245.0, 812.0), "ck_t36": (290.0, 812.0)},
               add=[(240.0, 718.0), (290.0, 718.0), (222.0, 790.0), (268.0, 790.0)]),
    "nl": dict(move={"ck_t34": (270.0, 690.0), "ck_t36": (275.0, 790.0)},
               add=[(250.0, 715.0), (290.0, 760.0), (245.0, 812.0), (220.0, 760.0)]),
}


def children(k):
    fp = json.loads((ROOT / f"physical/ref_tile/qfd_tile_{k}_a0cv7/floorplan.json").read_text())
    W, H = fp["die"][2], fp["die"][3]
    boxes = [dict(origin_um=[b["x"], b["y"]], outline_um=[b["w"], b["h"]]) for b in fp["blocks"] if b.get("kind") == "child"]
    return W, H, boxes


def snap(x, y, boxes, W, H, taken):
    sx, sy = free_x(x), snap_y(y)
    for dx in [0.0] + [d * 0.064 * s for d in range(1, 300) for s in (1, -1)]:
        cx = free_x(sx + dx) if dx else sx
        if cx is None:
            continue
        if clear_of(boxes, cx, sy, W, H) and all(abs(cx - a) + abs(sy - b) >= SEP_UM for a, b in taken):
            return cx, sy
    raise SystemExit(f"no clear tap site near {x} {y}")


def build(k, ends_path, est_path=None):
    W, H, boxes = children(k)
    v7 = json.loads((HERE / f"a0c7_{k}_taps.json").read_text())
    plan = PLAN[k]
    taps = []
    for t in v7["taps"]:
        t = dict(t)
        if t["name"] in plan["move"]:
            t["v7_xy"] = t["xy"]
            t["kind"] = "moved"
        taps.append(t)
    taken = [tuple(t["xy"]) for t in taps if t["name"] not in plan["move"]]
    for t in taps:
        if t["name"] in plan["move"]:
            t["xy"] = list(snap(*plan["move"][t["name"]], boxes, W, H, taken))
            taken.append(tuple(t["xy"]))
    n0 = len(taps)
    for i, (x, y) in enumerate(plan["add"]):
        xy = snap(x, y, boxes, W, H, taken)
        taken.append(xy)
        taps.append(dict(name=f"ck_t{n0 + i}", xy=list(xy), kind="added", sinks_v5=0, reach_um=0))
    if est_path and Path(est_path).is_file():
        est = json.loads(Path(est_path).read_text())
        for t in taps:
            e = est.get(t["name"])
            if e:
                t["sinks_v8_est"], t["reach_v8_est_um"] = e["sinks"], e["reach_um"]
    for t in taps:  # the v7 sink taps keep their v6 sites (5.2-6.4 um off some children, GEOM v7 note); new sites are clear
        if t["kind"] in ("moved", "added"):
            assert clear_of(boxes, t["xy"][0], t["xy"][1], W, H), t
    # reset landing copies -> nearest tap of their v8 load centroid
    ends = json.loads(Path(ends_path).read_text())
    v7rst = [l.split("\t") for l in (HERE / f"a0c7_{k}_rst_taps.tsv").read_text().splitlines() if l and not l.startswith("#")]
    rst = []
    for f in v7rst:
        inst = f[0]
        e = ends.get(inst) or ends.get(inst.replace("\\", ""))
        if e:
            cx, cy = e[0], e[1]
            best = min(taps, key=lambda t: abs(t["xy"][0] - cx) + abs(t["xy"][1] - cy))
            rst.append((inst, best["name"], best["xy"][0], best["xy"][1], f"loads {e[2]} at ({cx:.0f},{cy:.0f})"))
        else:
            site = next(t for t in taps if t["name"] == f[1])
            rst.append((inst, f[1], site["xy"][0], site["xy"][1], "v7 tap (no v8 load estimate)"))
    pins_in = (HERE / f"qfd_tile_{k}_a0c7_pins.tcl").read_text().splitlines(keepends=True)
    keep = [l for l in pins_in if not re.match(r"place_pin -pin_name \{ck(_t\d+)?\}", l) and not l.startswith("# QC-A0 10-24 A0 v7")]
    hdr = (f"# QC-A0 10-24 A0 v8 ({k.upper()}): {len(taps)} interior M7 clock taps = the v7 taps with "
           f"{', '.join(plan['move'])} moved into the hub (F1 empties the E margin) + {len(plan['add'])} hub additions "
           f"(gen_a0c8_taps.py); every tap a die-spine M8 -> M7 drop.\n")
    body = "".join(f"place_pin -pin_name {{{t['name']}}} -layer M7 -location {{{t['xy'][0]} {t['xy'][1]}}} "
                   f"-pin_size {{0.032 0.768}}   ;# {t['kind']}" + (f" (v7 site {t['v7_xy']})" if t.get("v7_xy") else "") + "\n"
                   for t in taps)
    (HERE / f"qfd_tile_{k}_a0c8_pins.tcl").write_text("".join(keep) + hdr + body)
    with open(HERE / f"a0c8_{k}_rst_taps.tsv", "w") as f:
        f.write("# inst\ttap\tx_um\ty_um\tnote (gen_a0c8_taps.py: v7 reset landing copy -> the v8 tap nearest its loads)\n")
        for r in rst:
            f.write("\t".join(str(v) for v in r) + "\n")
    rec = dict(tool="tools/qwen_romleaf/a0core/gen_a0c8_taps.py", rule="v7 taps (R4 grid 400 um + v6 sink additions) with "
               "F1-emptied taps moved to the hub + hub additions (BRIEFING decision 5 (b))", outline_um=[W, H],
               n_taps=len(taps), moved=sorted(plan["move"]), added=[t["name"] for t in taps[n0:]], taps=taps,
               reset_copies=len(rst))
    (HERE / f"a0c8_{k}_taps.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"{k}: {len(taps)} taps; moved {[(t['name'], t['xy']) for t in taps if t.get('v7_xy')]}; added "
          f"{[(t['name'], t['xy']) for t in taps[n0:]]}; reset copies {len(rst)}")
    return rec


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
