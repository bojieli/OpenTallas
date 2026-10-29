TOK-HBM-3 (2026-10-28), results only + one opt-in RTL file + one opt-in tool.
1. idx provider: rtl/hbm_next/idxn/ot_hnx_idxn_kb_ctl.sv (wires, reuse of the IDXQ quad-client decode), bind table
   idx_kb_ctl_bind.json (28 ports / 112 b from the d4g qctl outputs), bench run_kb_ctl.sh (positive.log, mutant.log, lint.log).
2. S-role fold: tools/hbm_b2/fold_s_roles.py -> s_role_fold.json/.svh. FAIL_CLOSED: mirror copies of the 47 N-role
   templates need 79 further S-role upstream instances that do not exist (incl. sm_SW4..7, vmks_SW*, xc_SW*, sucore_S*,
   hb_coll_S*); a mechanical copy would rebuild the S hubs (and 4 more SMs, against the 8-SM release). The fold map
   (which N-hub q0 instance serves each S net) must come from the plan (DIE-HBM-10).
3. rgap_vs_kx_estimate.json: KX=8 lane x store +0.10 mm2 + lane re-plan vs rgap ~0.36% of an MTP verify step, 0 on SU AR.
