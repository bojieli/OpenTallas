#!/usr/bin/env python3
"""DIE-KV-64 11-03 RF-KV1 step 2 (form B, zero-build): the 20 pv_join_t instances on the fR180 table (g0/g1 joins
of the 10 mixed kv3_pv* types) take the ONE signed R0 view at an x-preserving orient.

Why: pv_join_pins_fR180_r26q5c.json = R180 of the R0 table with every M3 pin snapped 18 nm (R0 M3 pins sit at a 9 nm
track residue, an x flip moves them to the other parity); M5 pins are exact under the flip, so no rigid placement of
the R0 view (any orient with an x flip + any shift) puts M3 (36 nm) and M5 (48 nm) on-grid together, and a second
master of the same name cannot sit in one type kit.  Form B keeps the slot origin/outline and only drops the x flip:
orient o (on fR180) -> R0 view at drop_x(o composed with R180), so the y side of every pin is unchanged and pins move
only within the 172.8 um core in x.  The die-frame pin displacement is reported (pvr0_rows.json).
Precedent: the plan-of-record kv3_pv_v1n..v6n types (same layout) already place all four joins x-preserving (MX) next
to x-flipped pv_pair columns; form B gives the 10 non-n types the same join geometry.
Binds lef/lib + SIGNED tap means as mk_pvview.py.  Fail-closed: nothing else changes.
Usage (repo root, after mk_pvview.py): python3 physical/die_plan/qwen_kvsys/pvview_1103/mk_pvr0.py
"""
import copy, json, os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "tools/die_plan")
import core_clock_contract as CC  # noqa: E402
import mk_pvview as V  # noqa: E402

JR180 = "pins/pv_join_pins_fR180_r26q5c.json"
COMP_R180 = {"R0": "R180", "R180": "R0", "MX": "MY", "MY": "MX"}
DROP_X = {"R0": "R0", "MX": "MX", "MY": "R0", "R180": "MX"}


def die_pins(h):
    to = h.get("track_offset_um", [0, 0])
    out = {}
    for p in json.load(open(os.path.join(V.POR, h["pins_file"])))["pins"]:
        dx, dy = V.tf(h["orient"], p["x"], p["y"], *h["outline_um"])
        out[p["name"]] = (h["origin_um"][0] + to[0] + dx, h["origin_um"][1] + to[1] + dy)
    return out


def main():
    path = os.path.join(V.POR, "plan_c.json")
    plan = json.loads(open(path).read())
    ref = copy.deepcopy(plan)
    d = os.path.join(V.VIEWS, V.JOIN)
    (cp, cv), = CC.load(dict(inst="x", module=V.JOIN, lib=f"{d}/{V.JOIN}_tt.lib", lef=f"{d}/{V.JOIN}.lef")).items()
    tt, ff = round(cv["corners"]["tt"]["mean_ps"], 2), round(cv["corners"]["ff"]["mean_ps"], 2)
    rows, touched = [], []
    for tn, t in sorted(plan["partition_types"].items()):
        hs = [h for h in t.get("hard_cores", []) if h["module"] == V.JOIN and h["pins_file"] == JR180]
        if not hs:
            continue
        touched.append(tn)
        taps = {tp["name"].split(".")[0]: tp for tp in t["clock"]["taps"] if tp.get("kind") == "core"}
        for h in hs:
            tp = taps[h["inst"]]
            assert tp["name"] == f"{h['inst']}.{cp}" and V.tap_xy(h, cp) == tp["xy"], (tn, tp["name"])
            assert not h.get("lef")
            old = die_pins(h)
            o0 = h["orient"]
            h["pins_file"], h["orient"] = V.JR0, DROP_X[COMP_R180[o0]]
            new = die_pins(h)
            dy = max(abs(new[k][1] - old[k][1]) for k in old)
            dxs = sorted(abs(new[k][0] - old[k][0]) for k in old)
            assert dy < 0.06, (tn, h["inst"], dy)     # y side kept (one M4 pitch snap at most)
            h["lef"], h["lib"] = f"{d}/{V.JOIN}.lef", f"{d}/{V.JOIN}_tt.lib"
            oxy = tp["xy"]
            tp["xy"] = V.tap_xy(h, cp)
            was = (tp.get("insertion_ps"), tp.get("insertion_ff_ps"), tp.get("budget_owner"))
            tp["insertion_ps"], tp["insertion_ff_ps"] = tt, ff
            tp["budget_owner"] = f"SIGNED:{d}/signoff.json"
            tp["note"] = (f"{V.TAG} form B: R0 view at {h['orient']} replaces fR180 table at {o0} (x flip dropped; "
                          f"tap {oxy} -> {tp['xy']}); SIGNED TT/FF {tt}/{ff} ps on {cp}; was {was[0]}/{was[1]} "
                          f"owner {was[2]} | " + tp.get("note", ""))
            rows.append(dict(type=tn, inst=h["inst"], orient_from=o0, orient_to=h["orient"],
                             pin_dx_mean_um=round(sum(dxs) / len(dxs), 2), pin_dx_max_um=round(dxs[-1], 2),
                             pin_dy_max_um=round(dy, 3), tap_from=oxy, tap_to=tp["xy"]))
    a, b = copy.deepcopy(ref), copy.deepcopy(plan)
    for x in (a, b):
        for tn in touched:
            for h in x["partition_types"][tn]["hard_cores"]:
                for k in ("lef", "lib", "pins_file", "orient"):
                    h.pop(k, None)
            for tp in x["partition_types"][tn]["clock"]["taps"]:
                for k in ("insertion_ps", "insertion_ff_ps", "budget_owner", "note", "xy"):
                    tp.pop(k, None)
    assert a == b
    open(path, "w").write(json.dumps(plan, indent=1) + "\n")
    here = os.path.dirname(os.path.abspath(__file__))
    json.dump(dict(rule="DIE-KV-64 RF-KV1 form B (mk_pvr0.py)", rows=rows), open(os.path.join(here, "pvr0_rows.json"), "w"), indent=1)
    print(len(rows), Counter((r["orient_from"], r["orient_to"], r["pin_dx_mean_um"], r["pin_dx_max_um"], r["pin_dy_max_um"]) for r in rows))


if __name__ == "__main__":
    main()
