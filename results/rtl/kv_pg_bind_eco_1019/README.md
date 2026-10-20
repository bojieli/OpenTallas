# KV closed-view PG-bind-only ECO (ROOT4-STAPG 10-19)

Method = results/rtl/qw_pg_bind_eco_1019 (same launch.sh + pg_bind_eco.tcl: bind unbound native PG ITerms from the block's own global-connect rules, restore dont_touch; signal fingerprint identical; post all-terminal audit; PSM VDD/VSS). Inputs: the 17 views of frozen 5f2ce19bc-gen8v3mub (results/arch/kv_closed_pg_audit_1019/lane_views.tsv), final ODB from the closure-record run dir. ot-epyc4 ODBs copied to ot-epyc5 (ControlPath=none scp). These 17 had never been PG-audited; every one carried unbound terminals. cdc_pc/cdc_host are not ECO'd here: KV-HOST3 re-closes them (reroute_reason pg_binding).

Output: <run root>/pg_bind_eco_native/6_final_pgbound.odb (sha in each run.log). Collector: collect.sh (rerun to fill RUNNING rows).

| view | ran on | bound terminals | post audit | grid VDD/VSS | signal |
|---|---|---:|---|---|---|
| qkd_rlysh0_1-f1-72bdb806b | ot-pve1 | 6 | PASS (722) | 2/2 PASS | identical |
| qkd_rlysh0_36-f1-72bdb806b | ot-epyc5 | 10 | PASS (1226) | 2/2 PASS | identical |
| qkd_rlysh0_296-f1-72bdb806b | ot-epyc5 | 86 | PASS (10064) | 2/2 PASS | identical |
| qkd_rlysh0_528-f1-72bdb806b | ot-epyc5 | 166 | PASS (17888) | 2/2 PASS | identical |
| qkd_rlysh_1-f1-72bdb806b | ot-epyc5 | 6 | PASS (712) | 2/2 PASS | identical |
| qkd_rlysh_36-f1-72bdb806b | ot-epyc5 | 10 | PASS (1208) | 2/2 PASS | identical |
| qkd_rlysh_296-f1-72bdb806b | ot-epyc5 | 28 | PASS (9846) | 2/2 PASS | identical |
| qkd_rlysh_528-f1-72bdb806b | ot-epyc5 | 42 | PASS (17750) | 2/2 PASS | identical |
| qkd_landsh_1-f1-72bdb806b | ot-epyc5 | 12 | PASS (1288) | 2/2 PASS | identical |
| qkd_landsh_36-f1-20cef08c0 | ot-epyc5 | 44 | PASS (6428) | 2/2 PASS | identical |
| qkd_landsh_296-f1-20cef08c0 | ot-agidock128 | 174 | PASS (37802) | 2/2 PASS | identical |
| qkd_landsh_528-f1-20cef08c0 | ot-pve1 | 264 | PASS (68588) | 2/2 PASS | identical |
| qkd_landsh0_1-f1-72bdb806b | ot-epyc5 | 12 | PASS (1290) | 2/2 PASS | identical |
| qkd_landsh0_36-f1-20cef08c0 | ot-epyc5 | 56 | PASS (6380) | 2/2 PASS | identical |
| qkd_landsh0_296-f1-20cef08c0 | ot-epyc5 | 364 | PASS (39258) | 2/2 PASS | identical |
| qkd_landsh0_528-f1-20cef08c0 | ot-agidock128 | 708 | PASS (71004) | 2/2 PASS | identical |
| qkd_d2d_static_r7t-r7t-28642e9aa | ot-agidock128 | 11686 | PASS (722186) | 2/2 PASS | identical |
