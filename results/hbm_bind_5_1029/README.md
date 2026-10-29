# HBM-BIND-5 (2026-10-29): strict HBM die bind, masked EMITs

Plan: hbm-bind-3-1029/plan0/die_plan.json (h3plan).  Baseline HBM-BIND-4 b1: 159 = 158 UNPLANNED (179,387 b) + 1 EMIT.
All counts CHECKED from out/bind_report.json (`bind.py bind --strict`), run dir intel1:/srv/opentallas-scratch2/claude/hbm-bind-5-1029.

| run | change | errors | UNPLANNED (bits) | EMIT | unmapped / tied / undriven / multi | open_outputs |
|---|---|---|---|---|---|---|
| b1 (BIND-4) | baseline | 159 | 158 (179,387) | q_b113/u_sfucore_Q_ctl.rst_n found 0 leaves (HBM-029) | 0/0/0/0 | 2852 |
| c1 | + SFU ctl parent cuts (both SFUs) | 159 | 158 (179,387) | q_hub_ne/u_hc_Q.u_cen.ot_hbm_hc_subtree32_0.rst_n found 0 | 0/0/0/0 | 2814 |
| c2 | + hub qhub body spliced + 8 HC subtree32 cuts | 159 | 158 (179,387) | q_hub_ne/u_mu_fused_0.rst_n found 0 (NEW, see below) | 0/0/0/0 | 2880 |

## c1: SFU ctl (HBM-029 cleared)
tools/hbm_b2/sfu_ctl_parent_cutmap.py: per sfucore_NE/NW slice, members = cells not in base cores, not primitive-split
parents, not the operand store u_core.u_engine.u_memory.* (split.json ctl = u_vm + u_core/u_engine local + u_arithmetic
ctl reg); rst_n = u_core.u_rst.rst_n_in; module ot_hgi_sfu_core_split3__ctl (one identical master), inst
<slice>.__cut_ctl mapped [<b113 part>, u_sfucore_Q_ctl].  57 members, 11,810 pins (plan ABI 11,819), 1,147 store cells
excluded.  Report: compose.sfu_ctl_report.json.

## c2: hub HC subtree32
hc_NE/hc_NW were opaque ot_hbm_hc_qhub_static leaves.  A re-elab with qhub/qcen dissolved (run_elab.sh, native W128
rtl/ preferred) renumbers Yosys primitives die-wide, so instead splice_qhub.py replaces only the blackbox type of the
two top cells in the b1 netlist by the elaborated W128 qhub body (connections bit-identical, parameters equal, 294 other
modules + 407 other top cells byte-identical; splice_receipt_c2.json).  tools/hbm_b2/hc_subtree32_parent_cutmap.py then
cuts u_cen.ot_hbm_hc_subtree32_k (k=0..3, both hubs): 31 adder leaves (levels 1..5) + 62 per-node ne glue, ABI clk,
rst_n, valid_in, data[1024], sum[32], valid_out, node_fault[31] (= hc128_qhub_compact.py); one master
ot_hbm_hc_subtree32_core.  Report: compose.subtree32_report.json.  Manifest: c2_asbuilt_manifest.json.

## Next masked EMIT (not a cut-map gap): MU fused lanes absent from the as-built top
Plan q_hub_ne and q_hub_nw each carry 16 hnx_fused_lane + 15 ot_hnx_fused_tnode (n1 x8, n2 x4, n3 x2, n4).  The as-built
top instantiates only u_mu_fused_n4_ne/nw (tnode), u_mu_fused_root (ot_hnx_fused_hub_n4ext, levels 4/5) and
u_mu_fused_programme; the n4 ua/ub inputs are top ports native_required__u_mu_fused_n4_*__ua/ub (25 such ports).
So 2 x (16 lanes + 14 lower tnodes) = 60 plan cores have no as-built cells at all.  Fix = top source (instantiate the MU
lane subtree in hbm_current_native_top, owner of the top_native generator) or a plan-side delta; no bind-side map can
create them.  Further EMITs may be masked behind it.

Tests: tools/hbm_b2/test_parent_cutmaps.py (4 passed).  Shared tools are opt-in (compose inputs only), READY ROOT-MERGE.
