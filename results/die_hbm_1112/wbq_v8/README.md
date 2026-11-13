# WBQ root v8 (g0 + g1), HBM-CORES-C 2026-11-12, accepted by DIE-HBM-101

One design for both lane groups: ot_wbq_root_s7 (G=0 / G=1) with the RR ingress FIFO (RPIPE), registered one-hot read select (RSEL=1),
8 kept srst copies (RSTCP=8, ot_reset_sync TREE form) and a registered ordinal+8 (O8=1).

## Parent cycle change (for the HBM plan open list)
- g0 now takes RPIPE like g1: +1 fifo_clk edge between `we` and the entry becoming readable (ingress record register `stage_data`/`stage_valid`), ring 4 -> 5 words per lane.
  Nothing is added on the hbm_clk read side; RSEL, srst copies and ordinal8 are cycle-exact.
- After parent s_stop the root works at most 1 more fifo_clk (old 0); seam valids after h_stop at most 1 (old 0); K writes after h_stop up to 32 in both forms (QUAL measurement, wbq_qual/RESULTS.md).
- Source only; parent adoption review still required (CBREG/SSTOPREG kit pin cycle on copy_bank / s_stop as before).

## Files
- rtl/hbm_accel/counted_1109/ot_wbq_root_g0/{ot_wbq_root_s7.sv,ot_wbq_root_s7_rr_fifo.sv} and the same under ot_wbq_root_g1/.
  The module `ot_wbq_root_gX` is the recipe top (the face shell renames it to `ot_wbq_root_gX__fcore`); CBREG/SSTOPREG default 1 because the shell instantiates it without parameters.
  The files the kits were proven on define `ot_wbq_root_gX__fcore` directly with CBREG default 0 and the shell instantiated with `#(.CBREG(1),.SSTOPREG(1))`: the elaboration is identical.
  Recipe path checked: gen_core_kit_hbm.py from these committed files reproduces both proven kits byte for byte (pins.json, io.tcl, constraint.sdc, macro_placement.tcl, rr_fifo, reset_sync, cdc_fifo)
  except the one-line module header / CBREG default above and flow config lines (see mkv8kit.sh).
- physical/die_plan/hbm_arch_cores/recipes_b2.json: ot_wbq_root_g0 / ot_wbq_root_g1 now point at these files, define OT_WBQ_ROOT_S7_RPIPE, read_at_commit false.
- tables/: clk52 pin tables (g0 d44v_p51 sha 73843b0228dc, g1 vC5 sha a7cdad8bffc0) + the clock-entry delta (32 entries); both interior clock pins at x 51.864 / 52.056, y 64.8.
- mkv8kit.sh: exact kit generation command (private plan dir with the clk52 tables, views json, macro placement) and flow options.
- proof_eq/: yosys equivalence at W=288, G=0, CBREG=SSTOPREG=1; gold = RSEL=0, RSTCP=1, O8=0 vs gate = RSEL=1, RSTCP=8, O8=1 (RPIPE FIFO in both, same SRAM stub).
  eq.ys with the keep wire `inv_chk` (gold {1'b0,ordinal}+13'd8, gate ordinal8) as compare point: 22460 compare points, 22460 proven, 0 unproven (eq_pass.log.gz).
  Mutant (gate ordinal8 += 16): 22413 proven, 47 unproven (eq_mutant_ordinal8_plus16.log.gz). eq_without_invchk.ys is the first run: 61 unproven in the ordinal8 cone only.
- proof_inv/: standalone inductive proof of ordinal8 == ordinal+8 on the fill logic excerpt (SUCCESS) and its mutant (FAIL); redundant with proof_eq now.
- qual/: HBM-WBQ-QUAL-1 lock-step bench (Verilator) on the v8 RTL, build rr_rsel: 27 jobs 0 not OK (results_v8.tsv); mutant ordinal8 += 16: all rows FAIL REGRESSION (results_v8_mutant.tsv).
  run_qual_v8.py takes the S7 file through V8_S7 and renames modules for the bench; run it on the proven kit text (module ot_wbq_root_gX__fcore).
- receipts/g0, receipts/g1: signoff_v8_base.json (routed v8, NOT SIGNED: hold port-launched only + g0 drv), signoff_v8_eco.json (after the near-miss ECO: LOCAL_PASS_NEEDS_PARENT),
  eco_loop.json, lec_routed_eco.json (routed LEC of the ECO netlist: EQUIVALENT, 9569 compare points both), kit_config.mk.

## Results (both kits routed, DRT 0 violations)
|  | setup TT | drv | drc | hold FF | NEEDS_PARENT |
|---|---|---|---|---|---|
| g0 v8 base | +72.1 | 29 TT / 25 FF slew | 0 | -126.84, 1088 | 1085 port-launched |
| g0 v8 after ECO | +68.5 | 0 | 0 | -126.74 (ports only) | 1085 |
| g1 v8 base | +87.5 | 0 | 0 | -142.9, 1089 | 1085 |
| g1 v8 after ECO | +87.5 | 0 | 0 | -142.85 (ports only) | 1085 |
The 3 (g0) / 4 (g1) register-launched FF hold endpoints (-8.64 / -6.43 ps) and the g0 slew net _14004_ were cleared by one eco_loop iteration; no override.
Not formally proven: RPIPE (QUAL only). Kit DBs are not in this branch (epyc9 kit_g0_v8, kit_g1_v8 under /srv/opentallas-scratch2/claude/hbm-cores-c, .keep).
