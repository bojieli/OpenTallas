
## OPEN-RELAYS from FABLE-FIX-QC-STRAP (stand-down 2026-11-21 10:26 PST)
Unanswered failure classes; post RESULT or ACK naming the class id (fail_route accepts the whole owner chain).
- FAIL-CLASS a2e8efcde6 qwen_compute/pipeline/FLOW tool / Tcl error @pipeline: Traceback (most recent call last: open 8 min, 1 item(s): slw_fw_v1__clf51c11d8__cl592e3d37; owner chain FABLE-FIX-QC-STRAP

# FABLE-FIX-QC-STRAP-R2 handoff (Fable, started 2026-11-21 10:3x PST). Owns: QC R8 pad first-hop seats (lever 7 lead: st_a, sle_ctl, stm, cb) + proof on slw_st_a_v2__cl9f076a5c.
Read lanes/handoff/FABLE-FIX-QC-STRAP.md first (findings + design). Work dirs: epyc8 /srv/opentallas-scratch3/claude/FABLE-FIX-QC-STRAP-R2/{clone,tmp}, epyc8 + intel2 /srv/opentallas-scratch2/claude/FABLE-FIX-QC-STRAP-R2/{b1,tmp}.

## State 12:30 PST
- On main: 289287760f (r8_keep + R8-CORE-SEAT + budgets.r_r8_core_seat), 3fba1b4bc0 (schema file); 8df26be75d + 257642da66 (FAIL-CLASS a2e8efcde6: flow refresh over the ssh argument limit, test_flow2045 base failures).
- b1 private strict bind (V1 tree + two opt-ins, rt 3fba1b4bc021): 0 errors, LATCHECK 1921/1921. r8_keep acts on slw_st_a_v2__cl9f076a5c only (+60 flops). epyc8 /srv/opentallas-scratch2/claude/FABLE-FIX-QC-STRAP-R2/b1.
- Proof kit p1 (private-spec, env=wave, config.mk differs from wave a3 by OT_R8_CORE_SEAT = 1 only): spec intel2 ~/coord/autopilot/private_specs/FABLE-FIX-QC-STRAP-R2/qwen_compute_slw_st_a_v2__cl9f076a5c_1121115227,
  kit epyc8 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V2/private/FABLE-FIX-QC-STRAP-R2/slw_st_a_v2__cl9f076a5c_1121115227/gen/slw_st_a_v2__cl9f076a5c,
  run-item client intel2 pid 1088086 (log /srv/opentallas-scratch2/claude/FABLE-FIX-QC-STRAP-R2/tmp/run_item_p1.log). Place started 12:26 PST.
- Read next: place log R8-CORE-SEAT lines (seated / need_stage), CTS post-hook setup, final 5_1_grt.odb endpoints on rs_n_c_p / rs_n_hi_p (R1 scripts: rtx-pro scratchpad qcstrap/ep.sh + ep_tail.tcl, copies epyc2 /srv/opentallas-scratch3/claude/FABLE-FIX-QC-STRAP/tmp).
- Known remaining blocker for st_a sign-off: btab g_read -> u_u_r3/bt_q_p -124.3 (22 endpoints). Owner QC-PLAN-R11 (ACKed 11:5x), V3 plan item. The proof kit is expected to stop short of sign-off on that path; the proof target is the R8 endpoints.
- Rows (PROVISIONAL at QC-PLAN-R11, R8S-1): asbuilt land_pad_tail_split.r8_keep true; budgets.r_r8_core_seat ["slw_st_a", "sle_st_a"]. Enter V3 only after the proof kit CTS post-hook post.
- Lever 7: asked QC-SLE-R5 + FAM-QC-CB-R2 for failing first-hop endpoint lists; sort each into covered / floorplan row / station before adding a type.

## State 21:50 PST (after the limit; Codex 14:23-18:1x)
- V3 package = intake row 2a (lanes/handoff/FABLE-FIX-QC-STRAP-R2-V3-sta-seat.json), owner QC-PLAN-R12. Unchanged values.
- p1 GRT done (epyc8, GOAL grt, unit oth-ubuntu-187101-1795317712; no route). Final 5_1_grt.odb, GRT RC, propagated clocks, frame of tt_setup_repair.tcl:
  wns -195.32, tns -1144.0, 29 violating endpoints (table epyc8 /srv/opentallas-scratch2/claude/FABLE-FIX-QC-STRAP-R2/tmp/ep_p1_grt.tsv + .rpt):
  R8 pad endpoints (rs_n_c_p, rs_n_hi_p): 0 violating (a3: -333.6 x4, -7, -33.7). Seat proven at GRT RC.
  btab g_read -> u_u_r3/bt_q_p: 22 endpoints, worst -195.3 (a3 -124.3); +1 on u_u_r2 -6.8. Row 2b/2c (FAM-QC-HCST-R2).
  NEW vs a3: u_bin_b_tw_data_i/q -> u_pd1_b_tw_data_i_<n>_u_r3_1.q (first pad stage of the b_tw_data chain to r3): 5 endpoints -43.6, -43.0, -34.5, -10.9, -2.3
  (placed scan: 925-931 um bin -> pd1). Not judged yet whether the seat pass moved pd1 away from the bin or the kept chain changed it; next read.
  cland fstart -11.7 (inside gate).
- Kit's own post-GRT repair stalled at setup -45.57 (150 it); hold ws +40.09 after hold repair, 0 viol.
- Next: (1) cause of the b_tw_data bin -> pd1 hop (compare pd1 positions a3 vs p1; if the seat pass pulled stage 1 toward the pin, cap the first hop from the port register in core_input_chain.tcl); (2) after 2b lands in a bind, rebuild st_a proof to route; (3) lever 7 endpoint sort for sle_ctl / stm / cb.
