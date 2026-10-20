# SHLK s10c terminal route evidence

Exact job dsdv_sh_lk_s10c-dsdv_sh_lk_s10c-1b3fedddc final physical artifacts completed 2026-10-20T08:20:26 UTC. Collected 01:37 PT from ot-epyc9 closure-loop/<job>/routes/dsdv_sh_lk_s10c_dsdv_sh_lk_s10c_1b3fedddc. No bind/cancel/resubmit.

Signoff corner_sta.json TT setup +17.92 ps, FF hold +5.99 ps. Final route DRC2: two M4 SHORT records share signal net37083 at x304.117..305.376, y148.080..148.104 um against VSS and SRAM u_ot_pr_core.u_h.host.u_hi.g_hx_sram.u_hx.g_rsz2.u_mem1. Sibling s10d has the same physical failure class at another Y coordinate. This is a macro-boundary signal/ground short; structural pin-access/placement correction and a new-source gate are needed. No flow-only reroute is justified by these records alone.

Independent full mapped census ../shlk_s10c_mapped_native.json.gz finds 264 nonclock roots over32, maximum597, including reset-labelled roots. Clean signoff timing alone does not qualify the source. Neither original s10c nor s10d is a qualified child for parent binding; neither should be resubmitted unchanged.
