# S81-WREG-PARAM handoff (11-25 00:20 PST) -- ROW-REBASED posted (hub f2d3a8ba)
Job (COORD): VPW WREG per-instance parameter instead of the shared-file define OT_S81SL_VP_WREG (c9 ROW-DROP 46273028); row for c10.
CODE ON MAIN 0e07c1a066d3 (PLAN-LEAF-PARAMS): partition_types[T].leaf_params [{module, params}] -> bind.py plan_leaf_params() +
  regen_params merge (param_regen.json), schema.py leaf_params, test_bind_plan_leaf_params.py. Gate trees need tools >= it.
ROW = epyc11 /srv/opentallas-scratch2/claude/s81-wreg-param/base/p_wreg_param2.json c134d7e316cc (ops p_wreg_param2.ops.json):
  w60p 0420a62e2eb5 + leaf_params {ot_s81sl_vpw WREG 1} on t74 t13 t45 t31 t1 t14 + OT_SVC_ATTCUT dropped on 10 svc types.
  RTL = s81_vpw_wreg_overlay.py on the tree.
Results: LEC default == c9seal, WREG1 param == define RTL (PROVEN). Gate2 scoped strict PASS 0 errors, LF_CS_DEPTH 0 in scope,
  no define conflict. PRE vs w60p 0 FAIL; vs plan_h2_2249 26 ANCHORDRY inherited from w60p (col_h9_r0_p5 pv types).
Gate1 (ATTCUT kept) only error = TYPE_DEFINE_CONFLICT OT_SVC_ATTCUT. Logs: gate2.otrun.log, gate_wreg_param2/, pre_vs_base.log.
Next: none unless INT names a different c10 base (re-apply mk_row.py + mk_row2.py ops, rerun gate_row.sh).
