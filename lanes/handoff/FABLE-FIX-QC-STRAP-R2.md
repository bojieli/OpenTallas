
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
