#!/usr/bin/env python3
"""DIE-QC-63/SC 11-02 (OWNER 11-02: ADOPT the QC SC source event as an explicit plan event, gated on
equivalence/simulation PASS; reach problems fixed with added pipeline stages; tok/s loss accepted).

The nine QC SC partition types (12 replicas) are 459-677k std cells flat (kit synth incl. landing rings) with no
hard_cores[], so G0C CORE-KS fails all nine and their type kits cannot be built.  The SC leaf (bound wrapper instance
u_core) is ~337k cells of the type; it becomes a hard core.

Plan change (only these nine types; every other type is asserted byte-identical):
  * base family (7 types / 10 replicas, bound leaf qfd_dv_s5_sc2_leaf): hard_cores[] += u_core = qfd_dv_s5_sc2_leaf
    with params {HARD_PINREG: 1} (explicit, per hard core; the RTL default stays 0, so no silent default flip anywhere
    else).  HARD1 = codex/qc-sc-source-1755@98bbbbd8184 capture sharing: 103 plain + 4 reset input-capture classes
    become one pin register each (-391 +4 FFs; no added architectural cycle; proofs: Codex whole-vs-mapped EQ
    55664/55664 0eb23b82700, old-vs-HARD1 cone 41612e22eac; DIE-QC-63/SC lock-step co-simulation old d90 leaf vs HARD1,
    results/qc_die63_sc_1102/eq).  Outline 244.56 x 514.08, 572-bit plan pin table (Codex legal-track N-pin fix
    38a0c216181 / currentgen-1810, sha256 4a2a3eb4b830...), measured standalone HARD1 mapped count 336662 std / 42665 FF.
    The bind applies the parameter from this entry (physical/die_plan/qwen_compute/bind/sc_hard_params.py via the
    coll_regen.py param_regen hook); a hard core with params whose bound leaf is missing fails the bind.
  * chain-end family (slw_sc_v3 = qfd_dv_s5_sc2_leaf_up0, sle_sc_v3 = qfd_dv_s5_sc2_leaf_dn0; 1 replica each): the
    same hard core slot with params {HARD_PINREG: 1} (DIE-QC-71 11-04: tools/qwen_dv/sc2_hard_pinreg.py applied the same
    capture-sharing rule to k79_up0/dn0; 68 plain + 3 reset classes; without it the leaf stops at FACE_GUARD shared 71),
    pin table = the HARD1 table minus the absent up_i / dn_i port.
  * every SC type: clock.core_taps = 'early' with one core tap u_core.ck at the core ck pin (12.3 v5.0, S81/QC ETAP
    form), insertion TT 335.3 / FF 287.3 ps = the Codex HARD1 GRT readout pin-register means (sc_timing_readout,
    three-buffer replay, global RC; ESTIMATE, re-measure from the own kit view, 12.28b).  The kit IO frame follows the
    tap (qc_core_wave.py sc_leaf recipe), which is the frame half of the old FF hold -160 ps.
usage: delta_sc_hard1_1102.py PLAN_IN PLAN_OUT [REPORT.json]"""
import copy
import json
import sys
from pathlib import Path

BASE = ["slw_sc_v2", "sle_sc_v2", "slw_sc_v1__cl63e5a7a2", "slw_sc_v1__cl64543eaf__cl5e017c6f",
        "slw_sc_v1__cl64543eaf__cl4590432d", "sle_sc_v1__cl115da35f", "sle_sc_v1__cl7479a5ec"]
CE = {"slw_sc_v3": "qfd_dv_s5_sc2_leaf_up0", "sle_sc_v3": "qfd_dv_s5_sc2_leaf_dn0"}
OUTLINE = [244.56, 514.08]
ORIGIN = [345.6, 648.0]          # Codex HARD1 prototype slot (sle_sc_v2), identical in every SC type (same faces)
TRACK = [0.012, 0.012]        # DIE-QC-64/SC G0C: x 0.012 puts the 386 N/S M5 pins on the plan M5 track (offset 0.024, pitch 0.048); y 0.012 for E/W M4
TT, FF = 335.3, 287.3
SRC = ("Codex HARD1 standalone GRT readout epyc2:/srv/opentallas-scratch2/claude/codex-qc-sc-red-1101/sc_timing_readout "
       "+ sc_buffer_replay: 572 pin-register means TT 335.32 / FF 287.28 ps (global RC, no CTS repair)")
H1_COUNT = dict(std=336662, ff=42665, basis="Codex standalone HARD1 actual mapped netlist (model.json 7f37de21..., "
                "scope sc_place db9 kit); native count 338681 std/0 macro after seed cells")


def pin_xy(plan_dir, hc, pin):
    pins = json.loads((plan_dir / hc["pins_file"]).read_text())["pins"]
    p = next(x for x in pins if x["name"] == pin)
    assert hc.get("orient", "R0") == "R0"
    return [round(hc["origin_um"][0] + p["x"] + hc["track_offset_um"][0], 3),
            round(hc["origin_um"][1] + p["y"] + hc["track_offset_um"][1], 3)]


def core(module, params):
    pf = "cores/sc/%s_pins.json" % ("qfd_dv_s5_sc2_leaf_h1" if module == "qfd_dv_s5_sc2_leaf" else module)
    hc = dict(inst="u_core", module=module, origin_um=list(ORIGIN), outline_um=list(OUTLINE), orient="R0",
              track_offset_um=list(TRACK), pins_file=pf)
    hc["params"] = dict(params)
    if module == "qfd_dv_s5_sc2_leaf":
        hc["cells"] = H1_COUNT["std"]
        hc["cells_basis"] = H1_COUNT["basis"]
        hc["note"] = ("QC SC event (OWNER 11-02, DIE-QC-63/SC): SC leaf hardened as HARD1 (HARD_PINREG=1 capture sharing, "
                      "0 added cycles); bind applies params via bind/sc_hard_params.py")
    else:
        hc["note"] = ("QC SC event (OWNER 11-02, DIE-QC-71): chain-end SC leaf hardened with the HARD_PINREG=1 capture "
                      "sharing rule, 0 added cycles; pins = HARD1 table minus the absent port")
    return hc


def apply(raw, plan_dir):
    pt = raw["partition_types"]
    reps = {}
    for p in raw["partitions"]:
        reps[p["type"]] = reps.get(p["type"], 0) + 1
    assert sorted(t for t in pt if "_sc_" in t) == sorted(BASE + list(CE)), sorted(t for t in pt if "_sc_" in t)
    assert sum(reps[t] for t in BASE) == 10 and sum(reps[t] for t in CE) == 2, reps
    rep = []
    for tn in BASE + list(CE):
        t = pt[tn]
        assert not t.get("hard_cores"), tn
        x0, y0 = ORIGIN
        assert x0 + OUTLINE[0] <= t["outline_um"][0] and y0 + OUTLINE[1] <= t["outline_um"][1], tn
        hc = core("qfd_dv_s5_sc2_leaf", {"HARD_PINREG": 1}) if tn in BASE else core(CE[tn], {"HARD_PINREG": 1})
        t["hard_cores"] = [hc]
        ck = t["clock"]
        assert ck.get("core_taps") in (None, "early"), (tn, ck.get("core_taps"))
        assert not [x for x in ck.get("taps", []) if x.get("kind") == "core"], tn
        ck["core_taps"] = "early"
        xy = pin_xy(plan_dir, hc, "ck")
        ck.setdefault("taps", []).append(dict(
            kind="core", name="u_core.ck", xy=xy, insertion_ps=TT, insertion_ff_ps=FF,
            budget_owner=f"parent_budget early tap {round(TT - 250.0, 1)} ps TT: ESTIMATE = {SRC}; re-measure from own kit view (12.28b)",
            note="QC SC event: early core tap (12.3 v5.0) at the SC core ck pin"))
        rep.append(dict(type=tn, replicas=reps[tn], family="base_HARD1" if tn in BASE else "chain_end_as_is",
                        module=hc["module"], params=hc.get("params", {}), origin_um=hc["origin_um"],
                        pins_file=hc["pins_file"], tap=dict(name="u_core.ck", xy=xy, tt=TT, ff=FF)))
    return rep


def main():
    pin, pout = sys.argv[1:3]
    rep_p = sys.argv[3] if len(sys.argv) > 3 else None
    text = open(pin).read()
    raw = json.loads(text)
    assert json.dumps(raw) + "\n" == text, "plan text style is not one-line json.dumps"
    orig = copy.deepcopy(raw)
    rep = apply(raw, Path(pout).resolve().parent)
    touched = {r["type"] for r in rep}
    for tn in raw["partition_types"]:
        if tn not in touched:
            assert raw["partition_types"][tn] == orig["partition_types"][tn]
    assert {k: v for k, v in raw.items() if k != "partition_types"} == \
        {k: v for k, v in orig.items() if k != "partition_types"}
    open(pout, "w").write(json.dumps(raw) + "\n")
    if rep_p:
        open(rep_p, "w").write(json.dumps(dict(event="QC SC hard-core event (DIE-QC-63/SC 11-02)", types=rep,
                                               added_cycles=0, base_types=7, base_replicas=10, ce_types=2,
                                               ce_replicas=2), indent=1) + "\n")
    for r in rep:
        print(json.dumps(r))
    print(len(rep), "SC types hardened")


if __name__ == "__main__":
    main()
