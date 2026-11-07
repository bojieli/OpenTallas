# gqi_issue ex_we without fire + SE corner relief (DIE-HBM-83-COLL 11-06)

Post-CTS, kit vC missed TT by -105 ps on 96 endpoints, all ex_we (vA has the same worst endpoint at -63). Worst path: cur -> rf[cur] -> tl compare -> fire -> g_f_n -> 11-bit compare -> ex_we.

Fix: ex_we uses g_* instead of the next-state g_*_n. 0 cycles. The two differ only when a fire and ev_v[S_P-2] land on the same edge. The bench measured that only together with busy, which is the sticky busy fault.
This is not exact after an illegal fire: from that fire until the next legal fire, the payload may differ from the original.

Proof: runbench.sh, Verilator lock-step against 82d223825a (the original, before any retime), with a directed legal driver. The bench resets both designs after a fire while busy. It does not compare ld_p_d, rb_lp_data or ra_lp_data until the next legal fire, since ex has no reset.
Mutants 3 (drop fv) and 5 (drop g_qbg) survive. By reading the code they look unobservable: without qbg, ex is never read, and is_code implies fv on legal rows. This is reasoning, not a formal proof.

corner_relief.tcl is the kit-local placement hook that spreads face flops in the SE corner. Copy it into a kit and source it from face_flops.tcl after reset_taps.tcl.
