# DIE-QC-46 (QC die owner), 2026-10-30

## (1) Pin abutment: origins rounded by die_trial
Root cause: `die_trial.py` grt_tcl and psm_tcl wrote `ot_place {ox:g} {oy:g}`. Python `:g` keeps 6 significant digits,
so a 16390.08 origin was placed at 16390.1. This explains all 221 shifted QC partitions (DIE-QC-45). FLOW-7 fixed it in
b462b6cd050, which is on main 28e3502c1dd. My duplicate fix (claude/die-qc-46-origin-1030) is withdrawn.

## (2) plan_qc45 (base plan_qc43 e630ffb8), `plan/compose_qc45.py`
- Plan file: intel2 /srv/opentallas-scratch2/claude/die-qc-46/plan/plan_qc45.json, sha256 2257b9fb1a47...
  macro_pins/, cores/ and census/ sit next to it.
- (a) Bands: main `clock_landing_plan.resize_undersized_bands` (DIE-KV-32 ring_ff reserve) re-sized 1158 bands in
  111 types (report: `plan/qc45_band_resize.json`, max pin-to-band hop 400.68 um).
  Three types have no macro-free band of the needed depth (51.84 um for rsn_i), so they keep their old bands:
  sle_su_l1__cl5ea486db, slw_su_l1__cla2a78701, slw_su_l1__clcc9d0155. These are open (band_ring=ff or a re-form).
- (b) R8 strap sites (M5) on all 15 types whose bind manifest declares r8pad_strap: 12 cb*, sle_fw_v1__clf58b4dfb,
  sle_sc_v1__cl115da35f and sle_sc_v2 (256 bits).
- (c) glue: 4 native d2d_sram_1r1w_64x137_m1_r2c2_p192, g_bank[0..3] (names CHECKED in the kit 1_2_yosys.v), placed
  at y 51.84 next to the S-face FDI flit windows.
- (d) coll_ucie widening was NOT applied (see the lane file / ASK). coll_core and coll_f2 have N/S face pins starting
  at x 4.5 um. Moving their W edge therefore moves the N/S abutments along the whole collective column.
- G0C (main check.py, completeness): plan_qc43 155 -> plan_qc45 155, 0 new, 0 gone [CHECKED g0c.log].
- Strict bind (main bind.py, asbuilt = bind_qc43 elab): 0 errors, 790,393 crossing bits, 11,568 straps [CHECKED].

## (3) Clock
- `clock/qc46.yaml` = trial25 form on plan_qc45, with stage model inv2_ndr_qc_trial1p.
- inv2_ndr_qc_trial1p = the DIE-QC-45 TRIAL1 placed-stage refit, registered in tools/clk/stage_registry.json.
- `ot_clk check` PASS.
