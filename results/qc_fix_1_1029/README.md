# QC-FIX-1: BTAB turntree successor F1 / F2 (2026-10-29)

Lane QC-FIX-1. Predecessor diagnosis: `results/qc_btab_hold_1029` (DIE-QC-28) on failed AP d2837604267e
(intel1 `codex-qc-btab-0251/kits_route_compat/qfd_dv_s8x_btab_turntree`: FF hold -27.50/1060, pair 84.4, slew 31, cap 3, DRC 6).
All runs live on intel1 `/srv/opentallas-scratch2/claude/qc-fix-1-1029` (kits/, f1/, f1b/, f2/, probe/).

## Extended root cause (CHECKED, `btcap_geo.tcl` on the turntree 3_place.odb)
* The turntree tree was planned (`core_family_slice.py`, Codex `census_turn.sh`) from the **turngap kit's** placement
  (btcap[588] at x 77.5). The turntree kit then re-placed the data (btcap[588] at x 111.0), so leaves sat 30-138 um from
  their sinks (16 leaves with a sink > 30 um; `leaf_geo.tcl`).
* Every btcap is a single-fanout rd_out capture (rd_out -> btcap D, fo 1). Unanchored GPL put 480 of the 512
  g_btb[0]/[2] btcap 150-166 um from their rd_out pin (median 155 / 151 um), toward the E face: the macro output drove
  the long wire (DIE-QC-28 rd_out slew 330-410, cap 49.9 > 46.1) and the clock sinks had no stable position.
* The 6 DRC shorts are M4 access wires *inside* the g_btb[3] E pin edge (x 253.3-254.6 < macro edge 254.664) at the
  column bottom; the existing pin-column strip [254.664, 261.738] and corner keep-off already cover the outside, so an
  extra keep-off cannot reach them. Structural cause = the E column at x 255-280 carried 256 g_btb[1]/[3] + ~480
  g_btb[0]/[2] btcap and the E face. F2 removes the 480 from that column.

## Forms (both M5, `kit_modes.py stage --measured-hold`, recipe `hold_ff_margin` 15, turntree outline/pins/macros/strips)
| form | change | placement check (3_place) | status |
|---|---|---|---|
| F1 | tree re-planned from turntree's own 3_place (TT 211.6 / w53.4, FF 166.5 / w56.1 PLAN MODEL, INFO) | data drifted again: 2 leaves with 39 sinks > 30 um, max 143 um; btcap still 150 um from rd_out | GEOM FAIL (own check), no route |
| F1b | F1 + shared FLOW-GEN-2 `post_place_rebind: exact_count` | rebind moved 1029 sinks, max 143.96 -> 51.35 um (counts kept) | diagnostic GRT only |
| F2a | turntree tree + recipe `macro_pin_flops` (anchor census) | 2048 macro-pin flops anchored (1024 rd captures + 1024 write landings); btcap->rd_out max 11.7 um | census only |
| **F2** | tree re-planned from the F2a anchored placement + `macro_pin_flops` | leaf->sink median 2.6 / p99 19.5 / max 33.3 um (turntree 3.2 / 44.1 / 137.7); btcap->rd_out max 16.4 um; GRT50 probe 0/0 overflow, usage 17.18 %, WL 362,001 um | AUTO-GEOM image VIEWED; GEOM REQ filed before route |

F2 plan model (core_family_slice, UNCHECKED until built): 410 cells, 9 stages, TT 270.49 / window 21.22, FF 212.19 /
window 21.19 (turntree plan 232.33 / 48.17), legs all <= 1.10 x Manhattan, leaf spread max 29.4 um.
F2 moves the core clock pin 167.916 -> 158.22 (M5, y 61.02 unchanged) with the legalized root; the QC parent tap moves
833.196 -> 823.5 (x) in the candidate plan copy only (current QC event untouched; die owner adopts or not).
F2 AUTO-GEOM flags: fill 0.0535 / empty 0.85 (macro-bound slot, INFO per COORD 13:55 as for turntree 0.049),
channel_h 2.329 estimate at (225, 90) with GRT50 0 overflow (same projection class GEOM-55 cleared on turntree),
channel_v 0.806 / col_v 0.772 WARN at the E column (260-275, 57.5).

## Generator change (claude/qc-fix-1-1029)
`physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py`: opt-in recipe key `macro_pin_flops` wires the shared
`physical/common_flow/macro_pin_flops.tcl` (+ release + anchor_row_packing) after `face_flops.tcl`; absent = kit bytes
unchanged (2 new unit tests; 19/19 PASS). Leaf siting stays in the plan generator (`core_family_slice.py` ->
`core_plan_to_infra.py` -> `core_infra_plan.legalize_slice`), driven by `finish_form.py` (= Codex convert_turn.sh +
legalize_turn.py + make_turntree.py, parametrized, main tools). No new clock script, no trims/pads.

## Files
`finish_form.py` plan->slice->kit inputs; `btcap_geo.tcl`, `leaf_geo.tcl`, `leafstat.py` probes; `f2_recipe.json`,
`f2_slice.json`, `f2_legalization.json`, `f2_plan_checks.json`, `f2_plan.png`, `f2_auto_geom.{png,json}`, `probe_summary.txt`.
