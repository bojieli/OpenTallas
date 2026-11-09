#!/usr/bin/env python3
"""DIE-S81-85 11-09 ENG-CTAP-1109: early core taps for the eng__t1 hard cores (type-local plan event).

eng__t1 (block 382049d37428, wave KW-FIX-43 attempt_8) failed the post-CTS FF hold gate (WNS -712.58 ps, 17860
endpoints): its three hard cores sat on grid taps (clock.taps [], no core_taps) and 4_1_cts.log reported
  OT_TAP_CORE u_bound.u_u_e/ck  tap clk_t25 pin 110 + internal 849 = effective 959 ps (target 250, window 20) WARN
  OT_TAP_CORE u_bound.u_u_h0/ck tap clk_t6  pin 184 + internal 270 = effective 454 ps WARN
  OT_TAP_CORE u_bound.u_u_h1/ck tap clk_t6  pin 170 + internal 265 = effective 435 ps WARN
(tap mean insertion 222..998 ps).  dsdv_eng_rr_e has an inherent ~830-850 ps internal clock latency (vR1536N: 833),
so a new core view does not fix it.  pair.py --core-taps rule: every core clock pin whose internal latency
> common latency - CORE_TAP_MARGIN_PS (250 - 40 = 210) gets an EARLY dedicated core tap (clock.taps kind core,
clock.core_taps 'early'; gen_phys: port clk_c<k>, source latency -(insertion - 250) TT / -(insertion_ff - 202.5) FF).
All three pins qualify (849 / 270 / 263-265 > 210).

Form = the 143 early-tap types (CORELAT-SQ-1 parent_budget, insertion_ps + insertion_ff_ps), values chosen so the
kit's core_clock_contract selection (load -> plan_budget, or the view's insertion.json) matches the plan tap exactly:
  u_eng.u_e.ck   TT 848.98 / FF 671.43  selected view dsdv_eng_rr_e_{tt,ff}.lib max_clock_tree_path rise (no
                 measured mean in the view: plan parent_budget = the ETM number OT_TAP_CORE uses)
  u_eng.u_h0.ck  TT 270.23 / FF 226.63  holdeco_b10_1030 view lib max_clock_tree_path rise (no insertion record)
  u_eng.u_h1.ck  TT 263.18 / FF 211.69  ref_tile view insertion.json boundary-register mean (the contract reads it)
Tap site = the core clock pin (pins_file, origin + track offset; delta_etap_1031 form).
Only eng__t1 is rewritten in the plan text (its own text style); every other type is asserted unchanged.
usage: delta_eng_ctap_1109.py PLAN_IN PLAN_OUT [REPORT.json]"""
import copy
import json
import re
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent)]
from delta_romq_split_1106 import spans  # noqa: E402

EVENT = "ENG-CTAP-1109"
TARGET_PS, TARGET_FF_PS = 250.0, 202.5
# OT_TAP_CORE on an early core tap: effective = (-early + port-to-pin wire) + internal = target + wire.  Wire band of the
# same form at the pin, wave kits 11-09 (clk_c<k> lines: -238 vs -250, -53 vs -86): 12..34 ps.
WIRE_PS = (12.0, 34.0)
# type -> [(core inst, clock pin, TT, FF, basis)]
ENTRIES = {
    "eng__t1": [
        ("u_eng.u_e", "ck", 848.98, 671.43,
         "selected view dsdv_eng_rr_e_{tt,ff}.lib max_clock_tree_path rise (ETM; no measured mean in the view)"),
        ("u_eng.u_h0", "ck", 270.23, 226.63,
         "physical/die_plan/s81/cores/views/holdeco_b10_1030/dsdv_eng_rr_h0 {tt,ff}.lib max_clock_tree_path rise (ETM)"),
        ("u_eng.u_h1", "ck", 263.18, 211.69,
         "pin_register_mean physical/ref_tile/dsdv_eng_rr_h1/views/dsdv_eng_rr_h1/insertion.json (boundary mean)"),
    ],
}


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
    orig = copy.deepcopy(raw)
    plan_dir = Path(__file__).resolve().parent   # pins_file paths are relative to physical/die_plan/s81
    rep = []
    for tn, ents in ENTRIES.items():
        t = raw["partition_types"][tn]
        ck = t["clock"]
        taps = ck.setdefault("taps", [])
        had = ck.get("core_taps")
        assert had in (None, "early"), (tn, had)
        for inst, cpin, tt, ff, basis in ents:
            hc = next(c for c in t["hard_cores"] if c["inst"] == inst)
            name = f"{inst}.{cpin}"
            assert not any(x.get("name") in (name, inst) for x in taps), (tn, name, "already tapped")
            xy = pin_xy(plan_dir, hc, cpin)
            taps.append(dict(name=name, kind="core", xy=xy, insertion_ps=tt, insertion_ff_ps=ff,
                             budget_owner=f"parent_budget {basis}; {EVENT} DIE-S81-85",
                             note=f"CORELAT-SQ-1: early core tap (12.3 v5.0) at the core clock pin; {EVENT} "
                                  f"(pair.py --core-taps rule: internal {tt:g} > {TARGET_PS - 40:g} ps)"))
            rep.append(dict(type=tn, tap=name, module=hc["module"], xy=xy, insertion_ps=tt, insertion_ff_ps=ff,
                            early_tt_ps=round(max(0.0, tt - TARGET_PS), 2),
                            early_ff_ps=round(max(0.0, ff - TARGET_FF_PS), 2), basis=basis, core_taps_was=had,
                            predicted_effective_tt_ps=[round(tt - max(0.0, tt - TARGET_PS) + w, 2) for w in WIRE_PS]))
        ck["core_taps"] = "early"
    # text edits in the plan's own indent-1 style, last span first (only clock.core_taps / clock.taps of ENTRIES)
    sp = spans(text)
    edits = []
    for tn in ENTRIES:
        a, b = sp[("partition_types", tn, "clock", "taps")]
        line0 = text.rfind("\n", 0, a) + 1
        ind = re.match(r" *", text[line0:]).group(0)
        assert text[line0 + len(ind):a] == '"taps": ', (tn, text[line0:a])
        new = json.dumps(raw["partition_types"][tn]["clock"]["taps"], indent=1).replace("\n", "\n" + ind)
        if orig["partition_types"][tn]["clock"].get("core_taps") is None:
            new_key = ind + '"core_taps": "early",\n' + ind + '"taps": '
            edits.append((line0, b, new_key + new))
        else:
            edits.append((a, b, new))
    for a, b, new in sorted(edits, reverse=True):
        text = text[:a] + new + text[b:]
    assert json.loads(text) == raw
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn in raw["partition_types"]:
        if tn not in ENTRIES:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
    open(pout, "w").write(text)
    if rep_p:
        open(rep_p, "w").write(json.dumps(dict(event=EVENT, taps=rep), indent=1) + "\n")
    for r in rep:
        print(r)


if __name__ == "__main__":
    main()
