# S81-WREG-PARAM handoff (11-24 PST)
Job (COORD): VPW WREG per-instance parameter instead of the shared-file define OT_S81SL_VP_WREG (c9 ROW-DROP 46273028); row for c10.
Form: bind PLAN-LEAF-PARAMS: partition_types[T].leaf_params [{module: ot_s81sl_vpw, params: {WREG: 1}}] on t74 t13 t45 t31 t1 t14;
  bind.py plan_leaf_params() + regen_params merge (recorded in param_regen.json), schema.py leaf_params, test_bind_plan_leaf_params.py.
  RTL = s81_vpw_wreg_overlay.py applied to the tree (vpw WREG param, default 0 = g_nwreg wires); no define requested anywhere.
Findings: LF_CS_DEPTH x10 was the S81-LEAF-REGRID pvs/vsp 1->2 station (not WREG), realised by the LFCS netlist (c9s 26efcbda541d);
  w60p already has pvs/vsp 2 on 5 of 6 types (t45 1). TIED_TOTAL 486192 = base svc class. ATTCUT = module select in dsdv_svc_rs, not
  this pattern, already dropped in c9s.
LEC (epyc11 s81-wreg-param/lec, lec.log): A vpw(c9seal RTL) == vpw(overlay, WREG=0) PROVEN; B vpw(overlay+define) == vpw(overlay,
  WREG=1 param) PROVEN; C WREG0 vs WREG1 not equivalent (sanity). vp module text before vpw byte-identical (603 lines).
Work: epyc11 /srv/opentallas-scratch2/claude/s81-wreg-param (tree = fork of c9seal_tree, base/w60p_p5_row.json 0420a62e2eb5,
  base/p_wreg_param.json 544054dfd955 = row, gate_row.sh, gate.otrun.log); tests on epyc10 same dir (pytest2.log); wt diff row.diff.
Next: gate result -> push via ot-push-main -> ROW-REBASED to S81-ALLFIX-INT + COORD.
