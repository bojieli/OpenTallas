# DIE-QC-43 (QC die owner) 2026-10-30 00:07-01:1x PDT

## 1. QC plan event qc43 = plan_straps + ring-START copies + native macro sites  [CHECKED]
- Composite `plan_qc43.json` sha256 e630ffb8da5e1270003768c8a1c59e5dd9c2bf2e81b036fe241da5251cd50a42
  = DIE-QC-40 `plan_straps.json` (6d5b996f1411bfaa) + `landing_relay_start_copy: true` on the 35 types in
  `plan/ring_start_copy_types.json` (Codex 447404f/ef874 option; equals plan_ring_codex.json 0bf41499 exactly) + Codex
  physical-only macro delta c5547024f (30 types / 418 existing native SRAM/ROM hard_cores, core_pg_connect).
  Rebuild: `python3 plan/compose_qc43.py plan_straps.json plan/ring_start_copy_types.json macro_plan_delta.json OUT`
  (byte-identical sha re-checked), then copy `results/qc_codex_kits_2249/macro_pins/` next to the plan (pins_file is relative).
  Copy on disk: intel2:/srv/opentallas-scratch2/claude/die-qc-43/plan/ (plan_qc43.json + macro_pins/ + cores/ + census/).
- Delta verification: add_macro_sites.py re-run on main tools reproduces macro_plan_delta.json and all 9 macro_pins
  files byte-identically, from plan_straps AND from the ring plan; the composite built from the ring plan equals my fold.
- Full G0C (main check.py, completeness): plan_straps 155, ring 155, plan_qc43 155; new 0 / gone 0 vs base
  (plan/fold_g0c.json). The 155 baseline errors are pre-existing and NOT closed by this event.
- Strict bind (main 3fc2fcf0d, ot-run intel2): 377 parts / 119 types / 1921 crossings / 790,393 bits / 11,568 straps,
  0 errors / unbound / tied / undriven / multiply bound (plan/bind_report_summary.json).
- Bound-RTL attribution (ring plan bound on the same main tools vs plan_qc43): the macro sites change 11 bound files:
  9 comment-only (generated reset relay coordinates), 2 logic: coll_core gate taps t2<->t3 and t4<->t5 renumbered,
  coll_n core rst_n from tap t0 to t2. Same reset-tree depth (5 resp. 4), so the release cycle is unchanged; physical
  re-assignment only. Against Codex's 447404f ring bind, coll_ftm also differs: that is the main reset-grid fix 0f308.
- 10 types carry both macros and ring copies (fold_g0c.json types_both): the first kit of each must show the relay
  copy FFs in the landing band with the macros placed (G0C does not check that pair).

## 2. QC infrastructure GRT TRIAL0 (Codex epyc2 codex-qc-2249/grt_trial): fixed clock PRESERVED  [CHECKED]
Codex's helper said FAIL_CLOCK_CHANGED (44,591 -> 51,123 CLOCK nets). By source net name
(grt_trial/clock_preserve_named.py): all 44,591 fixed clock nets byte-identical (physical_snapshot), 0 missing,
0 retyped. The 6,532 extra CLOCK nets were SIGNAL nets with NO wires in the source: 3,266 CKINVDCx16/Y + 3,266
CKINVDCx5p33/Y start_provider leaf nets (census.json counts match) that GRT retyped and routed for the first time.
The trial used set_routing_layers -clock M8-M9, so these leaf nets got clock-layer guides; the real die GRT0 must
route local leaf nets by the leaf rule (ot_clk), not M8-M9. TRIAL0 is NOT full-die GRT0 (no native data plane,
PG IR not run) and NOT freeze evidence.

## 3. BTAB MIF1 H13 clock tree plan model: PASS (plan model; latency numbers UNCHECKED)
core_family_slice (main) on Codex's H13 placement (4532 FF + 4 SRAM). Sinks: S strip 1545, C column x125-147 1415,
E column x268-289 1157, M band 400, N 15. Codex's sink-centroid entry (164.2, 52.1) sits INSIDE SRAM g_btb[1], and
its branches land in the 12.96 um E/W pin channels (converter: no legal site near (6.48, 25.92)).
Winning structure D10 (btab/D10_kit_ko_m.json): centre entry (12.8a), lv0 x-band split at x=150 (C column = one
subtree; E column + right S strip = the other), leaf_target 24 (2,2,8,8, 9 stages, 473 cells, 199 leaves),
keepout_um = the kit's real per-side blockage (E/W 13.5, N/S 6.84 um around each SRAM) instead of the symmetric
planner halo, ndr2w. TT 259.58 w14.04 / FF 199.93 w12.20, leaf spread max 25.6 um, driver displacement max 0.675 um,
pg_clearance PASS, every gate PASS. D9 (exact 12.96/6.3) PASS TT 260.21 w15.82 / FF 199.81 w11.01.
Sweep table btab/summary.tsv (15 variants; Codex's N32 reproduced exactly as C). Renders viewed: D, D10.
No CTS was run. Next: the build (kit CTS with the D10 slice) in the kit lane.

## 4. VMR C1full (Codex epyc2 codex-qc-kits-2249/vmrC1full): DRT DRC 0, 1 M6 data stub left  [CHECKED readback]
Full-signal DRT finished DRC 0. Readback (vmr/readback.json, vmr/clock_netdiff.txt): clock geometry unchanged
(106 nets; the one hash change, ot_ms_Q7B1L0_clk, has the identical 419 shapes = wire-encoding order only), BUT one
data shape above M5 remains: net _02546_ M6 [119612,13120,119740,13152] DBU (the obstructed wb_d[1][106] stub moved
to a neighbour net). The Codex chain died at finish (die-qc-42-vmrC/finish_c.sh line 7 syntax error); fixed copy
vmr/finish_c43.sh; finish -> signoff TT/FF -> post-route LEC relaunched for numbers only. NOT SIGNED (layer rule).
