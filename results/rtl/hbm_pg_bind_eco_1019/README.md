# HBM closed-view PG-bind-only ECO (ROOT4-STAPG 10-19)

Method = results/rtl/qw_pg_bind_eco_1019. Inputs: the 4 CLOSED views of the read-only native audit codex/hbm-closed-pg-scope-1019 dd3920111 (selected.json). ot-epyc6 ODBs copied to ot-epyc5 (ot-epyc6 ControlMaster socket hung), sha256 equal. fc_xr2 final ODB absent (NOT_AUDITED): reroute owed.

Output: <run root>/pg_bind_eco_native/6_final_pgbound.odb (sha in each run.log). Collector: collect.sh (rerun to fill RUNNING rows).

| view | ran on | bound terminals | post audit | grid VDD/VSS | signal |
|---|---|---:|---|---|---|
| hidx_op_n12_g2c_1019-g2c-c11f3bb33 | ot-epyc5 | 1494572 | PASS (1647394) | 2/2 PASS | identical |
| hbm_argmax_swvm_r2_g2c_1019-g2c-c11f3bb33 | ot-epyc5 | 780 | PASS (191464) | 2/2 PASS | identical |
| hidx_rootctl_am_1018-r4-49a5acb8f | ot-pve1 | RUNNING | | | |
| hbm_su_pretree_s_1018-p3-1dad69123 | ot-epyc7 | 1627080 | PASS (1997964) | 2/2 PASS | identical |
