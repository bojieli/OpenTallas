# HBM plan event d44q (HBM-CORES-KITS-40, 2026-11-01)

Metadata-only event on d44p (die_plan d8d63587cf3e -> 3171b0fc3732; core_macros d44o 3bca79b4624e, core_conns d44m
e689ac2475d8 unchanged): hfd_ep_static block arrival contract (OWNER 12.25; DIE-HBM-57 13:3x ruling, form (a)).
The 6 clock taps with budget_owner hfd_ep_static (NW_io u_ep_N0 + u_host_ep.clk, NE_io u_ep_N2, q_spb0 u_ep_S0,
q_spb0__physical_v1 u_ep_S0, vsN0 u_ep_S1) change insertion_ps 386.4 -> 435.0 and insertion_ff_ps 315.9 -> 352.0
(+48.6 / +36.1 ps; the die early tap = core insertion, DIE-HBM-6), tol 40.  No other field changes.

Basis: hfd_ep_static@ce811c3f8f1c on single-root taps B (e5b857a7e34) measured pin-register mean TT 411.95 / FF 333.43
(postcts_gate.tcl on 4_cts.odb, placement RC) plus about 25 ps GRT RC -> 435 / 352.  Form (b), a lower
OT_DTAP_TARGET, was rejected by measurement: dt400 gives 30 taps at 452 ps and dt200 gives 53 taps at 463 ps (more taps
mean a longer root-to-tap tree).  Kit: gen_core_kit_hbm.py --io-tt-ps 435 --io-ff-ps 352 (SDC vclk, OT_VCLK_TT/FF,
OT_TAP_TARGET_PS and sdc_lint all 435/352).

die_plan.json sha256 = 3171b0fc3732 (full in SHA256SUMS).  No geometry, pin, core or connection change.

G0 / G0C (tools/die_plan/check.py at origin/main d600e840831, --completeness for G0C; plan dir = DIE-HBM-54 d44p
sidecars) d44p vs d44q on the same tools: identical message sets (G0 6 ERROR / 964 WARN, G0C 14 ERROR / 1181 WARN,
0 new, 0 gone), reports in g0/.  The 4 ERRORs above the committed d44p reports (q_su11 / q_su11__physical_v1 slots
L30x1/L31x1 station sites over u_cxdl_Q1_s/_q macros) come from the newer check.py and appear on d44p too.
Consumers: the die STA / gen_phys tap insertion of the 6 ep taps and the hfd_ep_static core kit contract.
