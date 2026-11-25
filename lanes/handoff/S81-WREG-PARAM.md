# S81-WREG-PARAM handoff (11-24 21:40 PST)
Job (COORD): VPW WREG per-instance parameter instead of the shared-file define OT_S81SL_VP_WREG (c9 ROW-DROP 46273028); row for c10.
CODE ON MAIN 0e07c1a066d3 (PLAN-LEAF-PARAMS): partition_types[T].leaf_params [{module, params}] -> bind.py plan_leaf_params() +
  regen_params merge (param_regen.json), schema.py leaf_params, test_bind_plan_leaf_params.py (36 pass). Gate trees need tools >= it
  (a c9seal-vintage tree schema.py gives PRE FAIL SCHEMA-UNKNOWN-KEY leaf_params).
Row: leaf_params [{ot_s81sl_vpw, WREG 1}] on t74 t13 t45 t31 t1 t14; RTL = s81_vpw_wreg_overlay.py on the tree; no WREG define.
LEC (epyc11 s81-wreg-param/lec.log): c9seal vpw == overlay WREG=0 PROVEN; overlay+define == WREG=1 param PROVEN; 0 vs 1 differ.
Gate 1 (row 544054dfd955 on w60p, ATTCUT kept): elab rc 0; bind 11 pre-emit errors incl TYPE_DEFINE_CONFLICT OT_SVC_ATTCUT (w60p
  still requests ATTCUT on 10 svc types) -> gate 2 = base/p_wreg_param2.json c134d7e316cc (= row + ATTCUT dropped on all 10 types,
  as the c9s drop), tree schema overlaid from main; gate2.otrun.log, out gate_wreg_param2.
Work: epyc11 /srv/opentallas-scratch2/claude/s81-wreg-param (tree = fork of c9seal_tree, base/w60p_p5_row.json 0420a62e2eb5).
Next: gate2 result (LF_CS_DEPTH 0, no define conflict, param_regen WREG 1 on 6 types) -> ROW-REBASED to S81-ALLFIX-INT + COORD.
