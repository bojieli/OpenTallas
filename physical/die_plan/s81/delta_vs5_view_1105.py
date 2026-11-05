#!/usr/bin/env python3
"""S81 plan event, vs5 view (DIE-S81-60 11-05, COORD 07:33 PST): the 79 ot_s81sl_vs rows take the signed vs5 form.

The signed vs was built on inputs/core_pins/ot_s81sl_vs_rf1.json (S81-RF1 RF-A a617811587b, 11-03: N/S M5 pins off the core M5
strap pairs); that table never reached the plan, which kept ot_s81sl_vs_tpl.json.  Same outline, same faces, same pin order,
every shift a multiple of the M5 pitch, clk and rst_n unmoved.  So this moves lef/lib/pins_file to the view; origin, orient,
track offset, clock taps and reset trees stay. 
obs_max stays M7: reset relay kinds depend on it, and both the old and signed LEF have OBS to M5 only.
    python3 delta_vs5_view_1105.py PLAN_IN PLAN_OUT REPORT.json        (cwd = repo root)
"""
import json, sys
from pathlib import Path
sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
import check as CK, schema as S, reset_tree as RT
from plan_event_1104 import plan_text

M = "ot_s81sl_vs"
VIEW = f"physical/die_plan/s81/cores/views/vs5_1105/{M}"
PF = "inputs/core_pins/ot_s81sl_vs_rf1.json"
OLD = "inputs/core_pins/ot_s81sl_vs_tpl.json"
R = lambda v: round(v, 3)


def table(pf):
    return {q["name"]: q for q in json.loads((Path("physical/die_plan/s81") / pf).read_text())["pins"]}


def main():
    src, out, rep = sys.argv[1:]
    P = json.loads(Path(src).read_text())
    Ps = S.Plan(S.load(src), src)
    new, old = table(PF), table(OLD)
    assert set(new) == set(old)
    for n in ("clk", "rst_n"):
        assert new[n] == old[n], n
    ins = json.loads(Path(f"{VIEW}/insertion.json").read_text())
    report = {}
    for tn, t in P["partition_types"].items():
        for c in t.get("hard_cores") or []:
            if c.get("module") != M:
                continue
            assert c["pins_file"] == OLD and c["outline_um"] == [172.8, 172.8], tn
            frames = [pi for pi, p in Ps.parts.items() if p["type"] == tn]
            o, (ox, oy), (dx, dy) = c["orient"], c["origin_um"], c["track_offset_um"]
            off = 0
            for q in new.values():
                L = Ps.layers.get(q["layer"])
                if L is None:
                    continue
                tx, ty = CK._orient_pt(o, 172.8, 172.8, q["x"], q["y"])
                pt = (ox + dx + tx, oy + dy + ty)
                a = 0 if L["dir"] == "V" else 1
                for f in [pt] + [Ps.to_die(pi, pt) for pi in frames if q["layer"] not in CK.MIRROR_SKIP or Ps.parts[pi].get("orient", "R0") == "R0"]:
                    off += not CK.on_track(f[a], L)
            assert not off, (tn, off)
            c.update(lef=f"{VIEW}/{M}.lef", lib=f"{VIEW}/{M}_tt.lib", pins_file=PF,
                     note=f"signed vs5 view (flow-20261105-s-s81); pins {PF} (S81-RF1 RF-A strap-clear)")
            tap = [x for x in t["clock"]["taps"] if x["name"] == c["inst"] + ".clk"]
            assert len(tap) <= 1, (tn, tap)
            old_tap = None
            if tap:  # no vs row carries a core tap on main today; a tap, if added, takes the measured budget
                old_tap = (tap[0].get("insertion_ps"), tap[0].get("insertion_ff_ps"))
                tap[0].update(insertion_ps=ins["tt"]["boundary"]["mean"], insertion_ff_ps=ins["ff"]["boundary"]["mean"],
                              budget_owner=f"parent_budget pin_register_mean {VIEW}/insertion.json")
            report[tn] = dict(inst=c["inst"], orient=o, off_track=off, old_tap_ps=old_tap)
    assert len(report) == 79, len(report)
    Path(out).write_text(plan_text(P))
    Pn = S.Plan(S.load(out), out)
    moved = []
    for tn in report:
        a, b = json.dumps(RT.for_type(Ps, tn), sort_keys=True, default=str), json.dumps(RT.for_type(Pn, tn), sort_keys=True, default=str)
        if a != b:
            moved.append(tn)
    Path(rep).write_text(json.dumps(dict(types=report, reset_tree_moved=moved), indent=1))
    print(json.dumps(dict(types=len(report), reset_tree_moved=len(moved), old_tap=sorted({str(v["old_tap_ps"]) for v in report.values()})[:6])))


if __name__ == "__main__":
    main()
