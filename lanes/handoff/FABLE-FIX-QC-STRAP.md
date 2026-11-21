# FABLE-FIX-QC-STRAP handoff (Fable, started 2026-11-21 09:30 PST). Owns: QC R8 strap / first-hop face-seat class + representative proof.
Representative: slw_st_a_v2__cl9f076a5c (wave event s29q103S4Q9N46R6V1, V1 plan). Inputs: QC-PLAN-R10-R8S census (epyc7 qc-plan-r9/v3rows/r8_straps_rows.{json,md}).
Work dirs: epyc7 /srv/opentallas-scratch3/claude/FABLE-FIX-QC-STRAP/{clone,tmp}; epyc2 + epyc8 /srv/opentallas-scratch3/claude/FABLE-FIX-QC-STRAP/tmp (read-only STA / geometry dumps);
rtx-pro scratchpad qcstrap/ (scripts: geo.tcl, ep_tail.tcl, dry.tcl, seat.tcl, bind_strap.sh).

## Findings (measured, epyc2 a3 kit 5_1_grt.odb after TT repair, propagated clocks; 29 violating endpoints, wns -333.62)
- Straps: nothing to tie. Every strap_r8pad_* port is already a parent-tied count strap with set_false_path; no failing path starts at a strap port.
  The failing starts are R8 DATA pad flops (ot_dp_dly u_r8b_<site>_f fixed pad, ot_dp_dly_cnt bank).
- rs_n_c_p: 4 endpoints -333.6 (u_r0) and 1 at -7 (u_r1): the four identical 4-bit chains are merged by yosys; one flop at y 1284 drives 4 cores (last hop 1,067 um).
- rs_n_hi_p u_r0: -33.7: unmerged 64-bit chain, last fixed stage 439 um from the pin (stages bunched: in 777 / 374 / 168 / 139 / 94 um).
- NOT a strap: btab read register g_read[*].q -> u_u_r3/bt_q_p: 22 endpoints -124.3 (668 ps of wire, about 800 um; r0 +377, r1 +417, r2 +148; r0 bt_word -> SRAM +309;
  SRAM clk -> rd_out 360 ps + read mux, SRAM -> g_read +58 to +225, so the register cannot move). One read (issued by u_r0) feeds all four cores in the same cycle
  (BT_LAT 1 is a core parameter). Needs the btab SRAM group about 200 to 330 um north (re-floorplan of the r1 / r2 corridor: ft cws0 station, reset tap, ist 4 / 5 sit there) or a
  re-phased r3. Plan item for QC-PLAN-R10 / FAM-QC-HCST-R2; blocks st_a sign-off on V1 after the strap fix.
- cland fstart -12.5 (inside the -42 gate).

## Design (0 cycles, no growth)
1. bind: asbuilt land_pad_tail_split.r8_keep = true (opt-in; absent = byte-identical). Fixed pads of R8 sites with equal width / depth / source become ot_dp_dly_keep: one chain per site.
2. flow: core_input_chain.tcl R8-CORE-SEAT, opt-in plan budgets.r_r8_core_seat = true | [type bases] -> kit config.mk OT_R8_CORE_SEAT = 1. For each hard-core input pin whose cone holds only
   R8 pad flops: cone flops + data gates at the pin face, earlier fixed stages spread on the macro-avoiding route. Base-independent (no coordinates in the plan).
   Dry run on the a3 placed DB (merged netlist): 528 pins, 404 seated, unshared tails 439 -> 15 um, chain hop max 251 um, 0 need_stage.
3. Rows for QC-PLAN-R10 (V3): asbuilt r8_keep true; budgets.r_r8_core_seat ["slw_st_a", "sle_st_a"] (extend to other families with u_r8b_* -> hard-core pins after the proof).
   R8S-2 (160 relay_sites) is then not needed.

## STAND-DOWN 10:45 PST (context limit) -> successor FABLE-FIX-QC-STRAP-R2
- RUNNING, handed to R2: ot-push-main on epyc7 (loved-redfish), pid 2015849 (wrapper 2015846), started 10:37 PST from the lane clone
  /srv/opentallas-scratch3/claude/FABLE-FIX-QC-STRAP/clone; log /srv/opentallas-scratch3/claude/FABLE-FIX-QC-STRAP/tmp/push1.log (ends with "PUSH_RC <n>"; 0 = on main).
  Commit: 52898d0aef before the rebase, 33d25422f0 after ot-push-main rebased it onto main (same change). Tests of touched files still running at stand-down; result NOT read.
  My session waiter (rtx-pro background poll on PUSH_RC) dies with this session: R2 must re-arm (until grep -q PUSH_RC push1.log). Exit 4 = failing test (nothing pushed), 3 = rebase conflict.
- No ot-run job running. Nothing cancelled. Nothing deleted except one own temp file (/tmp on intel2, noted by COORD; keep temp files in the lane tmp dir).
- Dry run numbers (epyc2 unit oth-ubuntu-110946-1795285050, a3 3_place.odb, merged netlist, in memory only), final pass:
  OT_R8_CORE_SEAT pins 528 seated_pins 404 roots 796 shared_roots 4 gates 1621 chains 469 stages_moved 1876 hop_bufs_moved 3979 noroute 0
  tail_um max before 1067.2 after 512.6 (the 512.6 is the 4 merged rs_n_c flops at the median of four cores; gone with r8_keep) chain_hop_um max 250.6 need_stage 0 kept_tails 124.
  Unshared tails 439 -> 15 um was read on the previous dry-run build (u_r0 rs_n_hi), not re-read on the final one.
- NOT done: private strict bind, private-spec proof kit, any timing result with the fix. The fix is unproven in timing.
- Next for R2: (1) read PUSH_RC; (2) wait for rt/<sha12> of the pushed main on epyc7 (ot-tools-sync); (3) epyc7 via ot-run --priority plan --mem 48:
  bash /srv/opentallas-scratch3/claude/FABLE-FIX-QC-STRAP/tmp/bind_strap.sh <rt sha12> /srv/opentallas-scratch2/claude/FABLE-FIX-QC-STRAP/b1 (script written, never run; expect R8_KEEP lines for st_a types,
  LATCHECK 1921/1921); (4) intel2 kit_wave.py private-spec qwen_compute slw_st_a_v2__cl9f076a5c --plan <b1/tree/.../zz_s29_qc103_s4q9n46r4_final_preview.json> --tree <b1/tree> --bind-out <b1/bind>
  --src-manifest off --lane <R2>, diff config.mk vs the wave kit (must differ only by OT_R8_CORE_SEAT = 1), run-item; (5) read 1_2_yosys.v for u_r8b_..._u_r1/r2/r3_rs_n_c_p_f cells,
  run_place.log OT_R8_CORE_SEAT line, 4_cts_post_hook.rpt, final 5_1_grt.odb (tmp/ep.sh / ep2.sh on epyc2 show the method).
- Open plan item (not owned by this lane, posted 10:36): btab g_read -> u_u_r3/bt_q_p 22 endpoints -124.3; st_a cannot sign on V1 until it is fixed. Corridor survey of the V1 plan (r1 / r2 gap y 568 to 752:
  ft cws0 station 376,669.6; reset tap 311,674; ist 4 / 5 regs 438..455,727; ist 0 506,622; 165 relay_sites) says a plain +345.6 um SRAM shift collides: needs a real corridor re-floorplan.
