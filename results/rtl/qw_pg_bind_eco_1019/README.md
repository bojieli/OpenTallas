# Qwen closed-view PG-bind-only ECO (ROOT4-PGFLOW 10-19)

Method = results/rtl/s81_pg_bind_eco_1019 (claude/s81-native-pg-1019): same launch.sh + pg_bind_eco.tcl (bind unbound native PG ITerms from the block's own global-connect rules, restore dont_touch; signal netlist/placement/dont_touch fingerprint identical; post all-terminal audit; PSM VDD/VSS). Inputs: the 17 final ODBs of audit 0ea3ca6ba (codex/qw-pg-audit-1019, results/arch/qwen_cluster_1017/pg_audit_1019). The 3 ot-epyc4 ODBs (host not admitting) were copied to ot-epyc5 /srv/opentallas-scratch/claude/root4-qw-eco-1019 (sha256 equal to the audit's odb_sha256). Output: <route root>/pg_bind_eco_native/6_final_pgbound.odb (sha in each run.log). The 4 CB16 halves of that audit (326 terminals) are NOT covered here.

| view | host | bound terminals | post audit | grid VDD/VSS | signal |
|---|---|---:|---|---|---|
| qfd_embedding_word_provider-rr1-ebd3f200b | ot-agidock128 | 1240 | PASS | 2/2 PASS | identical |
| qfwd_landh0_1_en_65x30-e1-6b2db6290 | ot-agidock128 | 26 | PASS | 2/2 PASS | identical |
| qfd_rstseq-r1-feceba3b2 | ot-agidock128 | 16 | PASS | 2/2 PASS | identical |
| qfd_rstsync-r1-feceba3b2 | ot-agidock128 | 10 | PASS | 2/2 PASS | identical |
| qfd_sys_face-rs3-5aa256c9f | ot-agidock128 | 3188 | PASS | 2/2 PASS | identical |
| qfwd_landh0_1_ew_65x30-e1-5a20260cc | ot-agidock128 | 26 | PASS | 2/2 PASS | identical |
| qfwd_landh0_1_ne_65x30-e1-965cc6dcd | ot-agidock128 | 26 | PASS | 2/2 PASS | identical |
| qfwd_landh0_1_ns_65x30-e1-965cc6dcd | ot-agidock128 | 26 | PASS | 2/2 PASS | identical |
| qfwd_rlyh0_1_en_65x30-f1-fc2236d82 | ot-agidock128 | 22 | PASS | 2/2 PASS | identical |
| qfwd_rlyh0_1_ew_65x30-f1-fc2236d82 | ot-agidock128 | 22 | PASS | 2/2 PASS | identical |
| qfwd_rlyh0_1_ns_65x30-f1-fc2236d82 | ot-agidock128 | 20 | PASS | 2/2 PASS | identical |
| qfwd_rlyh0_1_sw_65x30-f1-fc2236d82 | ot-agidock128 | 22 | PASS | 2/2 PASS | identical |
| qfd_rst_rep-a1-cddafbdcc | ot-agidock128 | 6 | PASS | 2/2 PASS | identical |
| qfd_rst_rep_p8-a1-cddafbdcc | ot-pve1 | 6 | PASS | 2/2 PASS | identical |
| qfwd_landh_1_en_65x30-c1-779e8477e | ot-epyc5 | 12 | PASS | 2/2 PASS | identical |
| qfwd_landh_1_ne_65x30-c1-07cc6c281 | ot-epyc5 | 12 | PASS | 2/2 PASS | identical |
| qfwd_landh_1_ns_65x30-c1-996b12250 | ot-epyc5 | 12 | PASS | 2/2 PASS | identical |

## CB16 halves (ROOT4-STAPG 10-19 22:2x)

Same launch.sh + pg_bind_eco.tcl on the 4 selected CLOSED CB16 halves of audit 0ea3ca6ba (source 5bdb2ae92; 326 unbound BUFx24 terminals). ot-epyc6 (ControlMaster socket hung; ot-run probe timed out) and ot-epyc8 (not an ot-run host) ODBs were copied with scp (ControlPath=none) to ot-epyc5 /srv/opentallas-scratch/claude/root4-stapg-eco-1019/<view>/base; sha256 equal to the audit's odb_sha256. Outputs: ot-epyc5 .../root4-stapg-eco-1019/<view>/pg_bind_eco_native/6_final_pgbound.odb; W257 on ot-agidock128 <route root>/pg_bind_eco_native/. List cb16_eco_list.txt.

| view | ran on | bound terminals | post audit | grid VDD/VSS | signal |
|---|---|---:|---|---|---|
| qfd_c_land_r257_narrow-safe1-5bdb2ae92 | ot-epyc5 | 44 | PASS (62094) | 2/2 PASS | identical |
| qfd_c_land_w258_narrow-safe1-5bdb2ae92 | ot-epyc5 | 116 | PASS (75742) | 2/2 PASS | identical |
| qfd_c_land_r258_narrow-safe1-5bdb2ae92 | ot-epyc5 | 44 | PASS (62246) | 2/2 PASS | identical |
| qfd_c_land_w257_narrow-safe1-5bdb2ae92 | ot-agidock128 | 122 | PASS (75610) | 2/2 PASS | identical |
