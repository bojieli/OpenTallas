
## STAND-DOWN 2026-11-23 ~11:00 PST (COORD: K3 f75a71af72eb already holds the rows)
Frozen rows (epyc2 /srv/opentallas-scratch2/claude/fam-kv-hubc-sysc/c/frozen, SHA256SUMS ok): sys_c C 08be3955c5c7, D c296998f3e31, RTL overlay ot_qwen_d2d_cal_seq_rom64_core.sv 23d08aceeda5, hub_C E 1656764949d7 (relay_sites seats). Gate D2 clean on base_d28.
Evidence: sys_c probe (C+D+E, goal grt): TT wns -201 / tns -8241 (A2 -369/-71k, baseline -418/-243k); triage FAIL (< -150), hold_est -105. Kit epyc2 .../KV-D28/private/FAM-KV-HUBC-SYSC-R2/kv3_sys_c_1123041646/gen/kv3_sys_c (5_1_grt.odb, run_route.log). Residual setup classes NOT classified (VIS-KV asked).
Still running (launched 04:17, before 10:45, left alone): hub_C probe qwen_kvsys_kv3_hub_C_1123041726 (run-item pid 3305956 on intel2, place on epyc2); census of NEED-STATION groups (711/375, d51/d7 delay chains, cland rx_payload ring, in-core kvs_attn) pending. Row E covers only d51/d7.
Open: cland rx_payload->u_bin 548 b and in-core kvs_attn chains have no row; hg-KV-HOLD-SKEW / hg-KV-IO-BOUNDARY sys_c items no row; port_in hold REASONED (FABLE-UNC-KV).
