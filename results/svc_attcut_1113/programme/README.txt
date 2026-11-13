SVC service-cut programme proof collected by Codex 2026-11-13.
Source from epyc2 cut-bench-1/root; compiled executable out1/obj/Vtb_svc_att_cut_prog (Verilator 5.050).
Seeds 1,2,3: nominal mismatches 0, fault_cycles 0, 160 PV words, 20 SM row beats each. CUTMUT2 caught 164 cycles, CUTMUT3 caught 37 cycles each.
The wrapper registers qrq with +1 latency, other attention lanes +2. This closes the unexercised P.V/SM control gap in 52dc675ba9.
Source package only: dsdv_svc_att OT_SVC_ATTCUT integration remains on existing branch claude/hard-s81-svc-1-attcut-1113@52dc675ba9. No production plan or source selection changes here.
Band/tile-stage work in the same worktree remains uncommitted and is intentionally excluded.
