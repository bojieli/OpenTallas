# n4 conservative form N4-C (HBM-COLLECT-1, 2026-11-09)

Kit: hand kit = the vRF1b gen kit (epyc4 /srv/opentallas-scratch3/claude/die-hbm-89/n4rf/kits/n4_vRF1b/ot_hnx_fused_hub_n4ext_c756b86982b8, a DIE-HBM-89-N4RF candidate that was not adopted on main) with ONE file replaced: rtl/ot_hnx_fused_tree.sv (base sha256 8e1c556dc3d3..., new 87fa5babc07d...). The other 24 kit RTL files are unchanged (eq/base_kit_rtl.sha256).
This directory is an n4-local reference copy. It replaces no shared main file (main rtl/hbm_next/fused/ot_hnx_fused_tree.sv has neither N4RF nor this change).

Measured cause (n4 vRF1b ECO hm5, intel1 hbm-collect-1/n4_vRF1b_ecohm): after the ECO the only remaining failure is TT slew on 5 pins (max 326 ps against 320), all on one net net13728. That net is a BUFx2 repair-tree leg (fanout13729 @95.5,148.8) to 8 sinks about 87 um away (y 61-65). The tree root is u_t5.u_add...valid_out, which yosys merged with cvl[LA]; that one flop is cout, the select of the 256-bit od mux in ot_hnx_fused_tnode.

Change (ot_hnx_fused_tnode, parameter COUT_REP, default 8 in this copy): 8 KEPT copies of cvl[LA], each loaded from cvl[LA-1] with the same async reset rl[1]. Each copy selects a 32-bit slice of od. Cycle-exact, no latency change, so TOK-VERIFY has a cycle delta of 0. COUT_REP=1 restores the original.

Proof (eq/run.out; yosys equiv_simple -seq 8 + equiv_induct -seq 3, tnode with DELIVERED_RESET=1 as n4 uses it):
- DN_DEAD_MSB=0: 10904/10904 proven.
- DN_DEAD_MSB=1 (u_t5): 10902/10902 proven.
- Mutant (copies loaded from cvl[LA], one stage late): 512 unproven, CAUGHT.
