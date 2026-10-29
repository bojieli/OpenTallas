# DIE-QC-35 BTAB QC-014 V1d: GRT M4 macro-body block + full signal re-route from the V1c ROUTED DB + routed-RC DRV/hold ECO

Kit intel1 `/srv/opentallas-scratch2/claude/die-qc-35-kits/kits/qfd_dv_s8x_btab_f3bv1d` = V1c kit files (no run/) +
`results/.../4_cts.odb` = V1c `5_2_route.odb` (sha256 8302ccff..), V1c `4_cts.sdc`, `v1c_routed.spef` = V1c
6_final.spef (b0e80028..), main `tools/die_plan/clk_freeze.tcl` (791627f6..), files of this dir, `config_append.mk`.
Launch `ot-run --mem 48 --threads 16 --hosts intel1 --dir KIT -- bash KIT/run_v1d.sh KIT 16 48`.

## Form (no clock ECO, no PAD/trim, no skew target, no new check)
- PRE_GLOBAL_ROUTE `pre_v1d.tcl`: kit grt_pre/drv hooks (the 96 keep-off obstructions are carried by the routed DB, not
  re-created); main clk_freeze: 410 clock nets' V1c detailed wires re-encoded FIXED, 3854 clock-net instances LOCKED;
  detailed wire of every other signal net ripped (20,799 nets); `sram_body_m4_grt_adjust.tcl` = kit hook,
  `set_global_routing_region_adjustment` M4 1.0 over each of the 4 macro bodies incl. the pin-face strips.
- GRT `-congestion_iterations 50`, SKIP_INCREMENTAL_REPAIR 1. POST `eco_v1d.tcl` (FF-only frame as main mk_eco b /
  ffh10r: CORNERS bc, OT_HOLD_MM 0, OT_VCLK_CORNER=ff, kit_modes eco guard): read V1c routed SPEF, clk_freeze,
  `repair_design -slew_margin 20 -cap_margin 10` (wire-RC slew, TT/FF ratio 1.055 on V1c's worst nets: 412.44/390.95,
  353.37/335.31), `repair_timing -hold -hold_margin 10`, DPL, incremental GRT, clock freeze assert, vclk back to TT.
- try1 (unit oth-ubuntu-3991072-1793302604) used the copied two-mode session: FAILED by design at the ECO guard
  (`OT_VCLK_MEASURED_HOLD: FF pin-register mean 140.730 outside 202.5 +- 40`): ot_mm_sync re-estimates parasitics on
  GRT RC and the FIXED clock nets have no GRT route. => routed-RC ECO must be FF-only (as main 94d520e42). Logs
  `KIT/failed_try1/`.

## Results try2 (unit oth-ubuntu-4030117-1793302943, intel1, start 12:42 PDT; client intel2 ~/dqc35k2/btab_v1d_try2.otrun.log)
CHECKED from KIT/run_route.log unless marked:
- GRT: 0 overflow (all layers, Max H/V 0/0), 20,799 nets routed, WL 401,105 um; M4 derated resources 805,845 (V1c) ->
  799,200 (-6,645 = the M4 capacity the macro OBS had left in the face gcells).
- Guides (`guide_m4_over_body.py` on route.guide, macro-pin nets excluded via 6_final.v): non-macro nets with an M4
  guide over a macro body: V1c 12 nets / 24 rects (incl. _1154_, _1157_) -> V1d 6 nets / 10 rects, all in the S-corner
  gcells (y 17.10-19.95) of the face columns. i.e. the M4 rule works at GRT level.
- ECO on V1c routed RC (FF frame vclk 202.5): pre setup +418.9 / FF hold +2.05; RSZ 22 slew nets (margin 20): 2 buffers
  + resizes; 105 hold endpoints -> 105 hold buffers; clock freeze assert OK (410 nets, 18 restored after GRT
  updateDirtyNets). Post value on GRT RC (hold -47.5) is not meaningful (FIXED clock nets carry no GRT parasitics).
- **DRT (still running at 2026-10-29 13:12 PDT): 20 markers stuck from iteration ~30 to 46** (`5_route_drc.rpt-45.rpt`): 15 M4 Short +
  5 V4 Cut Short, 5 nets (_1147_, net4002, net5099, g_btb[0].m_wa[4], g_btb[0].m_wa[6]), every one = V4 at x 253.33-253.49
  + M4 east to 254.592 inside the **g_btb[1] / g_btb[3] E keep-off strip** (y 23-40 / 97), shorting obstruction + macro
  OBS + the macro M4 PG. Same class as V1c (2 nets / 6 markers), so the M4 GRT block did NOT remove it. UNCHECKED: final
  count after the remaining stubborn iterations.
- Reading (CHECKED on the try2 route.guide): the guides of these nets are OUTSIDE the macro (e.g. _1147_ M3 at x
  255.36-255.93 y 17.7-61.0, net4002 / net5099 M3 at x 254.79-255.36); DRT leaves the guide and dives into the macro
  over M5 because the vertical corridor between the g_btb[1]/[3] E face (254.664) and the E edge is full on M3. V1c's
  2 DRC nets and V1b's GRT overflow sit in the same corridor (E face / S corners). Root cause = vertical routing demand in
  the g_btb[1]/[3] E halo corridor, not M4 guides.

## Next ONE structural step (proposal)
Not another flow knob on this placement: the E corridor needs capacity. Either (A) re-place with the E-column pin
flops / tw-data starts pulled off the g_btb[1]/[3] E corridor (plan event: core_family_slice pin-column budget), or (B)
an M5 + V4 keep-off over the full E strip (DRT can no longer dive into the macro) together with a GRT region adjustment
that reserves M3 corridor capacity, accepted only if DRT then converges (risk: the 5 nets fail in the corridor instead).
V2 (halo widening) stays blocked on the tree re-plan (29 FIRM tree bufs off-row).

Collect when the unit ends: KIT/image.txt (end rc), KIT/run_route.log (DRT-0199 final), KIT/run/reports/.../5_route_drc.rpt,
KIT/signoff/signoff.json (TT setup, FF hold, insertion TT/FF, pair, slew TT/FF, DRC); the routed LEC is chained
(intel2 `~/dqc35k2/btab_lec_chain.sh`, pid 2552901, log `~/dqc35k2/btab_v1d_lec.otrun.log`): it stages main lec.py
(a62696e61) as KIT/lec.py (kit copy -> lec.py.kit) and runs it on 6_final.v -> KIT/lec_routed/lec.json.
