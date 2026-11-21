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

## State 10:35 PST
- Lane clone commit 52898d0aef (bind r8_keep + R8-CORE-SEAT + budget key + tests): ot-push-main running on epyc7 (log tmp/push1.log, waiter in the session).
- Next: rt snapshot of the pushed sha -> epyc7 `bash tmp/bind_strap.sh <rt sha12> /srv/opentallas-scratch2/claude/FABLE-FIX-QC-STRAP/b1` via ot-run --priority plan (private strict bind + LATCHECK on V1 tree)
  -> intel2 kit_wave.py private-spec qwen_compute slw_st_a_v2__cl9f076a5c --plan <b1/tree plan> --tree <b1/tree> --bind-out <b1/bind> --src-manifest off --lane FABLE-FIX-QC-STRAP -> run-item.
- No job running. Nothing cancelled or deleted.
