# LATCHECK-1 handoff (tool lane, COORD-assigned 11-12)
State 2026-11-12 17:0x: READY posted, branch claude/latcheck-1-1112@a6e337d5a685 (off main 91a4101f1877), awaiting ROOT-MERGE-60.
- Tool: tools/die_plan/lane_asbuilt_latency.py (+ test_lane_asbuilt_latency.py, 12 tests); hook in bind.py cmd_bind
  (LANE_ASBUILT errors, bind_lane_asbuilt.json; hard, no opt-out).
- Worktree: epyc9 /srv/opentallas-scratch2/claude/latcheck-1/wt (own clone, --reference to epyc9 main checkout).
  Lone CLI copies: epyc9 + epyc8 /srv/opentallas-scratch2/claude/latcheck-1/bin; audit outputs .../latcheck-1/out
  (qc_d2d_g1*, qc_c8t*, hbm_pEv4*, kv_cb_vN*, s81_r12bA_m2*; .tsv per lane, .log errors).
- Audit (see the READY in COORD-REVIEW-QUEUE): QC d2d_g1 63 STALE_TABLE; KV cleanbind 0; HBM pEv4 118 UNPRICED;
  S81 r12bA_m2 84 (58 DOUBLE_PAD) -> 41 predicted ON. KV bind_vN2f stopped at EMIT (no top) -> not checkable.
- Open: HBM/S81 confirm their schedule reads latency.lanes (then the UNPRICED lanes are functional); default-ON flip
  of kit_source_station_pricing after this check lands (recommended).
- Cleanup after merge: delete epyc9/epyc8 /srv/opentallas-scratch2/claude/latcheck-1.
