#!/usr/bin/env python3
"""DIE-QC-58 11-01: early core taps for the eight QC SU lane hard cores (S81 delta_etap_1031.py form, 12.3 v5.0).

DIE-QC-58S CTS-only probe on the l1 pilot 3_place (kit qfd_qc_su_lane_w_l1_w0e61bf, TritonCTS full tree, placement RC):
the lane's own boundary pin-register clock insertion is TT 392.45 / FF 320.95 ps (1012 IO pin registers; all 39,444
registers TT 348.8-401.0 mean 378.6, FF 274.7-328.9 mean 307.6), against the 250 / 202.5 frame the kit IO clock and
the plan tap assumed.  The kit failed CTS on OT_HOLD_STRUCTURAL FF hold -150.00 ps / 2056 endpoints (765 I2R c_i ->
lrly pin registers captured ~118 ps late at FF).  With the IO frame at the measured insertion the same tree gives FF hold
-31.55 ps / 2288 endpoints (I2R 754, R2O 243, R2R 1291: planned-input split passes) -- probe
epyc2:/srv/opentallas-scratch2/claude/die-qc-58s/probe_cts.out.

Plan change (only the partition types carrying qfd_qc_su_lane_w_l<k>):
  * clock.core_taps = 'early'  (12.3 v5.0 macro insertion-delay balancing: the die tree taps the lane earlier by
    insertion - 250 TT / insertion_ff - 202.5 FF);
  * the existing core tap '<inst>.ck' (no such pin; budget 250) becomes '<inst>.clk' at the lane's planned clk pin
    (plan pin table + origin + track_offset), insertion_ps / insertion_ff_ps = the measured l1 view 392.5 / 321.0.
  * l0 and l2-l7 carry l1's value as the planned ESTIMATE (12.28b), marked 're-measure from own kit view'.
The kit IO frame follows the tap (qc_core_wave.py su_lane recipe insertion_ps / insertion_ff_ps from this tap).
usage: delta_etap_1101.py PLAN_IN PLAN_OUT [REPORT.json]"""
import copy
import json
import re
import sys
from pathlib import Path

MEASURED = "qfd_qc_su_lane_w_l1"
TT, FF = 392.5, 321.0
SRC = ("DIE-QC-58S CTS-only probe, l1 pilot kit qfd_qc_su_lane_w_l1_w0e61bf 3_place, boundary pin-register mean "
       "TT 392.45 / FF 320.95 ps (epyc2:/srv/opentallas-scratch2/claude/die-qc-58s/probe_cts.out)")
CLK = "clk"


def pin_xy(plan_dir, hc, pin):
    pins = json.loads((plan_dir / hc["pins_file"]).read_text())["pins"]
    p = next(x for x in pins if x["name"] == pin)
    (ox, oy), (w, h), o = hc["origin_um"], hc["outline_um"], hc.get("orient", "R0")
    tx, ty = hc.get("track_offset_um", [0.0, 0.0])
    x = {"R0": p["x"], "MX": p["x"], "MY": w - p["x"], "R180": w - p["x"]}[o]
    y = {"R0": p["y"], "MY": p["y"], "MX": h - p["y"], "R180": h - p["y"]}[o]
    return [round(ox + x + tx, 3), round(oy + y + ty, 3)]


def main():
    pin, pout = sys.argv[1:3]
    rep_p = sys.argv[3] if len(sys.argv) > 3 else None
    text = open(pin).read()
    raw = json.loads(text)
    assert json.dumps(raw) + "\n" == text, "plan text style is not one-line json.dumps"
    orig = copy.deepcopy(raw)
    plan_dir = Path(pout).resolve().parent   # pin tables beside the plan of record
    rep, touched = [], set()
    for tn, t in raw["partition_types"].items():
        lanes = [hc for hc in t.get("hard_cores", []) if re.fullmatch(r"qfd_qc_su_lane_w_l\d", hc.get("module", ""))]
        if not lanes:
            continue
        ck = t["clock"]
        assert ck.get("core_taps") in (None, "early"), (tn, ck.get("core_taps"))
        ck["core_taps"] = "early"
        taps = ck.setdefault("taps", [])
        for hc in lanes:
            inst, mod = hc["inst"], hc["module"]
            xy = pin_xy(plan_dir, hc, CLK)
            olds = [x for x in taps if x.get("kind") == "core" and x["name"] in (inst, f"{inst}.ck", f"{inst}.{CLK}")]
            assert len(olds) <= 1, (tn, inst, olds)
            was = None
            if olds:
                tap = olds[0]
                was = dict(name=tap["name"], xy=tap["xy"], insertion_ps=tap.get("insertion_ps"),
                           insertion_ff_ps=tap.get("insertion_ff_ps"))
                for k in ("insertion_tol_ps", "orient"):
                    tap.pop(k, None)
            else:
                tap = dict(kind="core")
                taps.append(tap)
            tap["name"], tap["xy"] = f"{inst}.{CLK}", xy
            tap["insertion_ps"], tap["insertion_ff_ps"] = TT, FF
            if mod == MEASURED:
                tap["budget_owner"] = f"parent_budget early tap {round(TT - 250.0, 1)} ps TT: MEASURED {SRC}"
                tap["note"] = "CORELAT-SQ-1: early core tap (12.3 v5.0) at the lane clk pin; ETAP-1101 measured kit frame"
            else:
                tap["budget_owner"] = (f"parent_budget early tap {round(TT - 250.0, 1)} ps TT: ESTIMATE = {MEASURED} "
                                       f"measured view ({SRC}); re-measure from own kit view (12.28b)")
                tap["note"] = ("CORELAT-SQ-1: early core tap (12.3 v5.0) at the lane clk pin; ETAP-1101 ESTIMATE from "
                               "l1, re-measure from own kit view")
            rep.append(dict(type=tn, inst=inst, module=mod, tap=tap["name"], xy=xy, was=was, now=[TT, FF],
                            basis="measured" if mod == MEASURED else "estimate (l1)"))
            touched.add(tn)
    for tn in raw["partition_types"]:
        if tn not in touched:
            assert raw["partition_types"][tn] == orig["partition_types"][tn]
    assert {k: v for k, v in raw.items() if k != "partition_types"} == \
        {k: v for k, v in orig.items() if k != "partition_types"}
    open(pout, "w").write(json.dumps(raw) + "\n")
    if rep_p:
        open(rep_p, "w").write(json.dumps(rep, indent=1) + "\n")
    for r in rep:
        print(r)
    print(len(rep), "taps in", len(touched), "types")


if __name__ == "__main__":
    main()
