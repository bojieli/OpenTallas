# TYPE-KVHROOT handoff (11-14 ~10:20 PST)
Problem: qwen_kvsys kv3_hroot attempt_4 (job f0985db5e6fa) ended OT_HOLD_STRUCTURAL at GRT (ws -19.72, 580 viol after 3 h).
Cause (CHECKED attempt_4/gen/kv3_hroot/pregrt_ff_hold.log): OT_PREGRT_FF_HOLD DID run. Debt 10246 FF endpoints (port_in 8180 -226.5, cross_tap 1766 -129.7).
 The repair worked (9068+90+2579 hold bufs, wns +5.0, 0 endpoints) but the final detailed_placement (negotiation legalizer) stopped with 79 overlaps
 in dense FIRM landing rings (u_cland_*, u_ring.dch) -> DPL-0033 -> FALLBACK, 4_cts.odb unchanged, whole debt went to GRT repair, which stalled.
 So it is a tool legalize failure, not a type-internal short path and not a tap-offset (844 pair) case.
Forms (private, intel1 /srv/opentallas-scratch3/claude/type-kvhroot/fA, fB; reuse attempt_4 4_cts.odb via resume.json start=grt, goal route):
 A = negotiation legalizer, then retry detailed_placement -use_diamond_legalizer on failure (keeps FIRM sinks).
 B = diamond legalizer directly, FIRM clock sinks released for the legalize.
 Both write 4_cts.odb.prelegal first. Logs: scratchpad runA.log/runB.log on rtx-pro; kit pregrt_ff_hold.log.
Next: on pass -> patch tools/die_plan/pregrt_ff_hold.py TAIL (class fix), READY to ROOT-MERGE, ASK KIT-OPS-5 retry key kv3_hroot@4, AUTO-RESIGN row + RESULT, archive.

## Update 11-14 ~11:30 PST
- Class fix: branch claude/type-kvhroot-1114 @a56a3476235 (hub), pregrt_ff_hold.py PREGRT-LEGAL-1 + test (16 pass). READY posted to ROOT-MERGE-63. KIT-OPS-5 deployed it in every die's live wave src; kv3_hroot@4 is in the retry list -> the wave relaunch is form C (real wave).
- Forms A/B first runs failed exit 11 (LEC_ASYNC proof identity differs: kit paths moved). LEC state cleared in my private copies (lec_async.* + lec/), LEC reruns (~30 min, parallel).
- A = intel1 .../type-kvhroot/fA (log scratchpad runA2.log), waiting load cap. B = moved to epyc7 .../type-kvhroot/fB (runB7.log), waiting memory. (A stray B run on intel1 also exited 11; its dir was cleaned.)
- Fleet pregrt FALLBACK count: 5 distinct items, only kv3_hroot@4 is DPL-0033 (others: kv3_sys_SD@4 setup loss, sle_fe_v3@6 and slw_fe_v2__clf110fab2@7 no hold gain, ot-jobs sle_fw_v1/slw_fe_v1 setup loss).
- On a pass (A, B or the wave attempt): AUTO-RESIGN.tsv row + RESULT line + archive per SIGNED-RECOVER.md ARCHIVE HOW-TO.

## Update 11-14 ~11:30 PST
- Class fix: branch claude/type-kvhroot-1114 @a56a3476235 (hub), pregrt_ff_hold.py PREGRT-LEGAL-1 + test (16 pass). READY posted to ROOT-MERGE-63. KIT-OPS-5 deployed it in every die's live wave src; kv3_hroot@4 is in the retry list, so the wave relaunch is form C.
- Forms A/B first runs failed exit 11 (LEC_ASYNC proof identity differs: kit paths moved). LEC state cleared in my private copies (lec_async.* + lec/), LEC reruns (~30 min, parallel).
- A = intel1 .../type-kvhroot/fA (log scratchpad runA2.log), waiting load cap. B = moved to epyc7 .../type-kvhroot/fB (runB7.log), waiting memory.
- Fleet pregrt FALLBACK count: 5 distinct items, only kv3_hroot@4 is DPL-0033 (others: kv3_sys_SD@4 setup loss, sle_fe_v3@6 and slw_fe_v2__clf110fab2@7 no hold gain, ot-jobs sle_fw_v1/slw_fe_v1 setup loss).
- On a pass (A, B or the wave attempt): AUTO-RESIGN.tsv row + RESULT line + archive per SIGNED-RECOVER.md ARCHIVE HOW-TO.
