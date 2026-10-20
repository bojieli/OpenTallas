# MU-DIE-S81/PO2 (10-19): po2 landing views bound, strict landing reset check active

- Branch claude/mu-die-s81-po2-1019 = parent claude/mu-die-s81-1019 (a218435f6) + merge claude/po-submit-1019 (c3c9de24c, clean).
- dv_bind strict check (tools/s81_dv/dv_bind.py landing_reset_check): per bound dsfd_dvland* master, RL of the bound view =
  reset_landing.stages of the kit spec.json at the view's closure-job source commit (abstract.json orfs_dir -> job -> verdict
  source_commit); table landing_reset_stages (absent = 0) must equal it, else DIE_PORT_BIND FAIL (+ landing_reset_mismatch /
  landing_reset_unresolved counters, LANDING_RESET lines, SystemExit).  Unit test tools/test_s81_land_reset_check.py (9 cases).
- Bind tables (mk_table_p4l3_mu.py) pin land_views per master (record commit + kit + job); dv_rvcase binds those views (overrides
  first-ref-wins).  po2 (RL 2, key set): 276, 276l, 70.  No key: 562 l1, 512 g3a (po2 still routing), 682 l1, pvrd p3.
- Strict bind (p4l_mu_lkcol, bind_table_p4l3_mu, land plan p4l3): DIE_PORT_BIND PASS 41 masters / 9,005 inst, every counter 0
  incl. landing_reset_mismatch 0 / unresolved 0; frame_contract PASS.  +57 inst vs mu1 = gate-calendar stations 714 -> 771
  (hop-0 gate opens 2 edges later on the 239 po2-landed lanes; K = E, data latency unchanged).
- Note: the worktree kit dirs physical/ref_tile/s81dv_land_{276,276l,70} now hold the po2 spec.json but still the OLD views;
  without land_views the check FAILS (as designed) -- always bind landing views through the table.
