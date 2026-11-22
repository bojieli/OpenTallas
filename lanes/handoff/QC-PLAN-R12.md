# QC-PLAN-R12 handoff (11-21 12:5x -> 20:3x PST; succeeds QC-PLAN-R11; successor QC-PLAN-R13). Read QC-PLAN-R11.md (gate recipe), QC-PLAN-R10.md (V2 pack/seal/apply recipe), lanes/handoff/QC-PLAN-R12-V3-INTAKE.md (ledger).
Row cut 11-22 06:00 PST; apply >= 11:16. All work on epyc7 /srv/opentallas-scratch2/claude/qc-plan-r12/ (Codex 14:23-18:1x built ctl_strap/ under this lane; adopted).
## Tools pin (COORD ruling 20:1x): V3 event tools = rt 6dbb162ffe89 (= main; has 3c2f3758f4 tap_split/tap_balance_to, 2c3fa5fd97 coll or_groups, 6dbb latch_except_by_type). Set gen_tools_pin / dies.qwen_compute.tools_sha to it at apply. KEEP rt 6dbb162ffe89 and 3c2f3758f4c1. rt 31c7ccbd1b93 / 55344f311cde no longer needed for V3.
## Candidate chain (v3p4/)
- V3p3 f5d51696a2eb (ctl_strap/v3p3_static): rows 1, 2a/2b/2c, 3 (289 sited FT), 6, 6c. Strict bind (rt 55344) = 3 errors, all row 6c (coll reset anchors coll_core/coll_ftc + coll_ftc start_10 depth 5 != 3). Bind took 2.6 h (v3t 27 min) on loaded epyc7.
- V3p4a = V3p3 + HC3 class records (ctl_strap/hc3_projection/v3p3_hc3_overlay.json) + sle_ctl rprog/hard-tap reset retaps + West SU C 43-tap cap (compose_v3p4.py).
- V3p4b = + SLWSLE su_c x_su_l1_ctl slots (33->32 sited) on slw_su_c cl92142dac/cl19bb38ef (add_suc_slot.py). sle_su_c row is a no-op vs V2.
- V3p5 = + clock.tap_balance_to slowest (10 st_a, glue, sle_ctl) + tap_split.py --over r300 (346 taps, 9 PARTIAL) (add_taps.py, stage_v3p5.sh).
- V3p5r b1281d55e514 (pre-lat; post-lat bb3d6871793f) = V3p5 with 6c reverted (revert_6c.py). THIS IS THE CURRENT CANDIDATE.
  chain_p5r2.sh (log chain_p5r2.log): waits static_p5r G0 (3c2f launch) -> asserts 0 errors -> strict bind on rt 6dbb (v3p5r_bound, bind_p5r.out) + LATCHECK -> post-bind G0 vs b20 + census. smoke_6dbb.sh: G0 of the same plan on a 6dbb launch (v3p6_launch) = COORD G0 smoke on the new pin.
  Waiter: until grep -q CHAIN_DONE v3p4/chain_p5r2.log ... ; STAGE intermediates a/b/p5 G0 were cancelled (not needed).
## Still to add for V3p6 (compose on V3p5r pre-lat plan_v3p5r.json, then latency -> G0 -> strict bind rt 6dbb + LATCHECK -> post-bind G0 -> census)
1. coll_core package from FABLE-FIX-QC-COLL-R2 (COORD: all 13 lane-latency changes OK; wall + rebind 508->477 + faultpipe 8->11 + 92-group stations with sites; due 04:00, based on V3p3). If it re-adds 6c it must carry re-recorded reset_tree_anchor + start_10 depth fix. Ask was posted: delta by type/row.
2. CB (COORD 20:1x): FAM-QC-CB-R3-V3-cts-fix.json rows A-D (A = clock.core_input_lockup latch_except by type, module qfd_tile_nk_rp2_romleaf_rr not qfd_tile_nk_a0c; B landing_ring_wreg dsrep 1->2 cbf_q01_s2; C u_rst_in early tap/HB4; D cbf_q00 cross-tap hold) + FAM-QC-CB-R3-V3-cbn-street.json + FAM-QC-CB-R2-V3-cb-candidates.json (paired_s2_v2_zero_egress for cbf_q00_s2/cbn_q01, cbn_dual_nohb4 typed NK strict-green) incl cbx_q10 cl89936551_h (place -659). All CANDIDATE, base V2 7f9f8260349f; apply per key, check no clash with V3p5 tap rows (cb t24/t25/t93/t100 untouched by tap_split).
3. Calendar K-C = -8 (OWNER): not a plan key; token lane to supply bound RTL overlay; verify in bind receipt.
4. Optional if native proofs read before cut: HC1 rs_return, FE START +2, FW five-bank sites (Codex, ctl_strap/hc1_rs_return, fefw_sc).
Stop list FABLE-PD-QC-1230 sec 3 applies. Then pack/seal/apply per QC-PLAN-R10 recipe after 11:16, post, report to COORD.
## Verdicts / other
- tt_ctlm owned by R12->R13 (UNOWNED in sweep): Codex RAE private TT -36.34/FF -121.93 (qc-plan-r12/ttctlm*), not in V3. Helper subagent died on limit.
- FEFW-V3-2 rejected (V2 already has 2 x_fe_p1_i stations; -84.28 was the 1-station N46C kit).
- COORD rulings recorded in ledger (faultpipe 8->11, rebind 508->477, calendar -8, coll 13 lanes, tools pin).
