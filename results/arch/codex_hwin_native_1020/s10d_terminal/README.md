# SHLK s10d terminal route evidence

Exact job dsdv_sh_lk_s10d-dsdv_sh_lk_s10d-87bd096d8 finished NEEDS_RTL. Root collection at 01:25 PT 2026-10-20, remote ot-epyc6 closure-loop/<job>/routes/dsdv_sh_lk_s10d_dsdv_sh_lk_s10d_87bd096d8. No resubmit or bind.

Actual signoff corner_sta.json TT setup +13.03 ps, FF hold +12.44 ps; zero respective violating paths. physical.json also reports the separate 0.77 ns implementation-target diagnostics, which are not the 833.333 ps signoff result. Final route DRC is not zero: 5_route_drc.rpt contains TWO M4 SHORT records at y137.328..137.352 um, signal net35836 against VSS (x304.117..305.148) and SRAM u_ot_pr_core.u_h.host.u_hi.g_hx_sram.u_hx.g_rsz2.u_mem1 (x304.117..305.376). This is a macro-boundary signal/ground short, requiring structural pin-access/placement correction and a new-source gate; no flow-only reroute is justified by these records alone.

Independent current-source full mapped census in ../shlk_s10d_mapped_native.json.gz reports 323 nonclock roots over 32, maximum 526, including reset-labelled roots. Therefore clean timing or repairing only the two shorts would not qualify this source. Sibling s10c remains independent and is also blocked by its mapped fanout census. No first-qualified child exists for parent binding.
