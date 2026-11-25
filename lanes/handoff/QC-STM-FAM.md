# QC-STM-FAM handoff (parent QC-ALLFIX; scope FABLE-RC-QC rows 25/26 = stm family)
Updated 2026-11-25 07:5x PST.
- Census posted 07:33 (lanes/posts/QC-STM-FAM.md). Tables: epyc10 /srv/opentallas-scratch2/claude/QC-STM-FAM/census/cen_*.txt
- Causes: (A) slw_stm_v1__cle34a73c3 RESETN recovery -59.82 / 27 ep: one group-0 STM-DQ landing copy u_stream.g_rn.rs2_g[0] feeds ~470 flops (16-buf tree + 2 HB4 on root). (B) sle_stm_v2 cl55be2264 flt_o -78.42 and (C) sle_stm_v3 so_w -50.94: R6V4 kits had no flt_o stations; v13 has 2 flt_o stations on all 9 stm types -> COVERED.
- Row STM-RC: row json epyc10 QC-STM-FAM/row/STM-RC.json sha 2272284f3785; plan 58d5630bb451 = v13 aa3a14fb7484 + slw_stm_v1__cle34a73c3 verilog_defines += OT_QC_STMRC; sidecar a142fe516f24 unchanged.
- RTL: lane clone epyc10 /srv/opentallas-scratch2/claude/QC-STM-FAM/wt branch qc-stm-fam/stmrc-1125 (rtl/qwen_dv/qfd_dv_stream_tile.sv); equiv proven (eq/). Not pushed yet.
- Running: guard+PRE epyc10 (ot-run client pid 3399659, out QC-STM-FAM/pre.out); Fable review.
- Next: after BIND-PASS (QC-C1O-COMPOSE), private copy of launch_c1o_bind with v13+row and patched RTL, scoped bind slw_stm_v1__cle34a73c3, place probe, ROW-READY.
