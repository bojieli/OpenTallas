Adopted Codex job intel2:/srv/opentallas-scratch2/claude/codex-qwen/xt1_capacity_both16_v2. Vehicle: the capacity
candidate bind (P6 plan from codex/qc-capacity-1024 @72ece79138, 430,195 pads), xt1 both clusters, lead 16.
VERDICT FAIL: nominal near 0/64, far 0/64. FAULT near_cluster fires at cycle 296 and FAULT far_cluster at 325. There is no heads
fault, so the lead is fine. The mutant FAILs as well. The schedule gate is FAIL because the nominal run is not exact.
Root cause: the CB16 n_a/n_b legs are out of step. cb16b.py on the bind gives t_0_0 skew -18, t_1_2 +12 and t_2_2 -2. This is
the same cause B as on bound_r8. The fix is under test with qc_cb16_pads_capacity.json (see the lane file).
