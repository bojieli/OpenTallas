DIE-KV-40 (2026-10-29 21:05 PDT) KV die owner. q1/q2 widen-EAST 233.28 -> 243.648 die-local plan delta (DIE-KV-39 ruling
20:21 step 2, COORD 10-29 conditions). Runs intel1 /srv/opentallas-scratch2/claude/die-kv-40-1029; worktree wt/die-kv-40 (main ac0b29e7fa5).

event28w = event28b (sha 79b4379e) + mk_plan_w243.py: hard_cores ectl_q1/ectl_q2 outline 233.28 -> 243.648 in all 8 hg types
  (16 entries, origins fixed), pins_file -> qkd_ectlk_q{1,2}_pins_243.json (E face x 233.184 -> 243.552: q1 283 / q2 269 pins;
  W 773, S 910/911, interior ck[0]/rst_n[0] (+ q2 ft_ck_i/o_0) unchanged); fail-closed: nothing else differs. 243.648 = 564 x 0.432.
  q2 pins = KV-KITS-V q2_w243 kit pins.json (1957/1957, same layer/coords modulo the kit edge snap).
event28w_c (plan_c, sha 16980115) = event28w + mk_coll_w243.py: the wider cores re-route the partition reset relay chain of
  kv3_hg_v1p5 (83 -> 79 relays) and kv3_hg_v1p6 (102 -> 96) (reset_tree.for_type; taps, depth 6/8, max hop 380 unchanged; old
  relays (574.56,1499.04) / (894.24,1317.6) sat within the core halo of the new outline). Collector tree := current reset tree for
  exactly those 2 types (mk_sd36 rule), sidecar eW_sidecar.json (sha 42860817), plan landing_contract patched.
G0C (check.py --completeness): base event28b / event28w / event28w_c: identical 2103 findings (47 ERR pre-existing: 43 complete +
  4 hard_cores; 2056 WARN); only street area -0.095 mm2 and cut track counts change.
Strict bind (eB3b recipe, + eW_sidecar) on event28w_c: errors/unbound/undriven/multiply_bound 0, 160 parts / 2545 crossings /
  430554 bits, regen_constants PASS 40 OK/2 WARN (= bindB3bG); 92 bound .sv/.v: 88 byte-identical to bindB3bG, 4 differ =
  kv3_hg_v1p5/_v1p6 (rtl + native_internal_stations: reset relay chain + landing collector only). Without the sidecar regen
  (event28w): bind errors 1 'EMIT collector rst_rl_81: raw reset parent rst_rl_80 absent'.
Die clock check (ot_clk, one clock tool): check PASS; control replay kv_e26a IDENTICAL; on plan_e26a + the same delta
  (kv_e26a_w243.yaml): ctree.v IDENTICAL, tree.json sites differ on exactly 32 cells = tree-c leg repeaters r<N>_0 (one per hg
  instance) that sat 2.76 um east of q2 (inside the new outline + 2.16 halo); site_slide moves each 19.26 um along its own leg
  (0 cells/taps in the growth strips or new cores afterwards). Die GRT0 incl clock (DIE-KV-26 grt.sh recipe): TT + FF overflow
  0, usage 2.37 %; tap arrivals: 64 of 1920 taps change (hg clk_t14 + clk_t15 of all 32 hg), max |d| TT 8.20 / FF 6.78 ps
  rise, 7.96 / 6.56 fall; mean +0.34 / +0.62 ps.
