#!/usr/bin/env python3
"""S81 hierarchy contract v17 -> v18 (ONE revision for 2026-10-14; one-shot, idempotent).

Base: physical/s81_die_pins/v18/contract_trial.json (the 10-13 night geometry trial: SU slab grown S to 10,709.28 um,
VM bgq28 367.2 x 725.76 + FE 889.92 h, HC comb 840.24 h, sub_layouts) -- it kept version 17 and was never published.
v18 folds the die lead's 10-14 decisions on top of it and adds the master list the die really instantiates
(v18 native-envelope geometry, 59,546 instances / 225 masters) with the assigned pin file per unbound master.

Usage: contract_v18.py [--check]
"""
from __future__ import annotations
import argparse, glob, json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "results/arch/hier_contract_1011/s81.json"
TRIAL = ROOT / "physical/s81_die_pins/v18/contract_trial.json"
CENSUS = ROOT / "results/physical/die_iter_1014/s81/v18_native207_master_census.txt"
BIND = ROOT / "results/arch/s81_native_20261013/view_binding.json"
MACROS = ("ot_rom_", "ot_v41_rom_elem_q", "ot_pdie_", "ot_hbm3e_")


def master_list():
    cen = json.loads(CENSUS.read_text().split("\n", 1)[1])
    vb = json.loads(BIND.read_text())
    bound = set(vb["bound"]) if isinstance(vb["bound"], dict) else {x["master"] for x in vb["bound"]}
    hand = {Path(f).stem for f in glob.glob(str(ROOT / "physical/s81_die_pins/v18/*.json"))} - {"contract_trial"}
    gen = {Path(f).stem for f in glob.glob(str(ROOT / "physical/s81_die_pins/v18/generated/*.json"))}
    rows = []
    for m, n in sorted(cen.items(), key=lambda kv: (-kv[1], kv[0])):
        if m in bound:
            st, pf = "bound_closed_view", None
        elif m.startswith(MACROS):
            st, pf = "macro", None
        else:
            st = "unclosed"
            pf = (f"physical/s81_die_pins/v18/{m}.json" if m in hand else
                  f"physical/s81_die_pins/v18/generated/{m}.json" if m in gen else None)
        rows.append({"master": m, "instances": n, "state": st, "pin_file": pf})
    return rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    cur = json.loads(CON.read_text())
    if cur["version"] >= 18:
        print("already v%d" % cur["version"]); return 0
    c = json.loads(TRIAL.read_text())
    assert c["version"] == 17 and cur["version"] == 17
    c["version"] = 18
    c["updated"] = "2026-10-14 PT (s81_die_v18, Claude die lead)"
    c["changelog"] = c.get("changelog", []) + [
        "v18 (2026-10-14): base = v18 geometry trial (SU S growth 686.88 um, VM +609.12, HC comb 840.24); Q element per-mac "
        "re-partition; dsfd_rly_283_EW v3 kit; SU region decision; master list + assigned pin files; sign-off TT setup / FF hold / "
        "DRC 0 with SS as a sensitivity column (owner 10-07, restated 10-14 06:35)."]
    c["signoff"] = {"setup": "TT", "hold": "FF", "drc": 0, "ss": "reported sensitivity only, never a blocker (owner 10-07 option B)"}
    rows = master_list()
    c["master_list_v18"] = {
        "source": "v18 native-envelope geometry plan (ot-epyc4 .../v18_screen_native_envelopes207/plan.json.gz, die branch bc903eee7)",
        "instances": sum(r["instances"] for r in rows), "masters": len(rows),
        "pin_rule": "owner 10-13 18:22: unclosed masters consume the die-assigned file; hand-assigned v18 files (capture, gather, "
                    "VM, hcol/hsel, HC pads/CCF) take precedence over generated/; closed views are re-pinned only when the classified "
                    "die table or a cut window names them",
        "rows": rows,
        "unclosed_without_pin_file": [r["master"] for r in rows if r["state"] == "unclosed" and not r["pin_file"]]}
    c["v18_decisions"] = {
        "q_element": {"decision": "per-mac re-partition mac0 | ctl | mac1 inside the unchanged Q parent 512.64 x 216",
                      "evidence": "results/physical/die_iter_1014/s81/operand_endpoint_screen/q_seam_permac_partition.json (4720059cf)",
                      "seam": "2,274 wires per seam on 194.4 um: M2+M4 0.272, M4 alone 0.563 <= 0.60; no M6 grant",
                      "owed_by": "A (Q owner): map, seam pins M4, per-container CTS, PQ1 production proof"},
        "su_region": {"decision": "E (partial): sp_su_s grown S to 1890.0 x 10709.28 = 20.240 mm2 (686.88 of the 1,296 um column "
                                  "move; VM takes 609.12: bgq28 +414.72 / FE +194.4)",
                      "bill_mm2": 18.689, "fill": 0.923,
                      "closed_denser_masters": {"s81su_pinns_ref-v1-6494b8a37": "CLOSED TT +251.66 / FF +2.45 (453.6 x 64.8)",
                                                "s81su_sml_u65_ref-v1-6494b8a37": "CLOSED TT +88.90 / FF +20.36",
                                                "s81su_smd_u65_ref-v1-6494b8a37": "CLOSED TT +93.51 / FF +23.35",
                                                "s81su_sml_u69_ref-v1-6494b8a37": "FLOORPLAN_MARGIN 61.3 % (refused; u65 view is used)"},
                      "stands": "swe / qne / kve / kvq closed views stand (SRAM, spine, hold hooks)",
                      "owed_by": "SU owner (B): packing proof of the closed set in 1890 x 10709.28 incl. relay channels; if it does not "
                                 "pack at 0.923, the next lever is the remaining 609 um of the column (VM bgq28 then needs its own fix), "
                                 "not wings"},
        "rly_283_EW": {"kit": "v3 (b79442de6): hold owned once by the launcher's outhold; inhold removed (v2 GPL 845 %)",
                       "outline": [23.76, 30.24], "job": "s81_rly_283_ew-v3-b79442de6"},
        "wfc_vmx_p": {"diagnosis": "p2 EARLY_FAIL_HOLD -171 ps at CTS: two related clocks with unequal trees in one tile "
                                   "(core_clk ck L 447 ps, ser_clk ckv L 731 ps, 11 levels each): core->ser crossings see ~284 ps of "
                                   "inter-clock skew; plus ckv 6 macros on 0 leaf buffers (376 um avg clock wire)",
                      "structural_fix": "split into hardened leaves per clock (vmx_w / hep_t on ck, vmx_r ratio FIFO the only "
                                        "two-clock leaf, small) so the die delivers each clock pin at phi - R; macro inputs launched "
                                        "from a flop on the macro's leaf", "owed_by": "B"},
    }
    c["open_items"] = c.get("open_items", [])
    if a.check:
        print(json.dumps({k: c[k] for k in ("version", "signoff")}), len(rows)); return 0
    CON.write_text(json.dumps(c, indent=1) + "\n")
    print("wrote v18", CON, len(rows), "masters,", c["master_list_v18"]["instances"], "instances; unclosed without pin file:",
          c["master_list_v18"]["unclosed_without_pin_file"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
