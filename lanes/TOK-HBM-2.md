# TOK-HBM-2 (HBM whole-die token pass: FUSED service + calendar, unified 4-role top; successor of TOK-HBM-1)

## 2026-10-28 21:05 PDT RESULT / PARKED (slice 1; branch claude/tok-hbm-2-1028@4d356dc103 on TOK-HBM-1 c8255e05b5, merges clean with main)
- (1) ROOT-LOCAL SERVICE measured [CHECKED, results/tok_hbm_2_1028/root_service.json]: production root wrapper
  ot_hnx_fused_hub_n4ext DELIVERED_RESET=1 alone (scalars reflected at n4, sums/fins injected; Verilator 5.050, docker 8 GB
  intel2), 16 (op,n) x wsc 63/115 x rgap 0/4/12, all DONE: capture -> GO = wsc + nsc + 5 + min(n,2) nbt (slope 1 in wsc),
  rows >= 2 beats at GO + 119 + rgap + per (p-2); PRE last chunk sum -> r on the command bus 114; fin -> done 1.
  The existing native bench (tb_n4_extract) cannot give capture -> done: done waits on the leaves' fin.
- (2) LANE + TNODE SEGMENTS measured [CHECKED, lane_service.log / lane_rgap_sweep.log]: one native lane + one native tnode,
  command stream = the measured root schedule, fixed-return VM: PRE GO -> row p last chunk sum 188 + (80+rgap) p,
  r -> fin 36; POST GO -> fin 50 + 100 n + rgap (n-1); tnode up 4 (scalar/fin) / 9 (chunk sum), down 2; lane SCRD -> scalar 14.
- (3) FINDING PRE x-slot [lane level CHECKED at rgap 0/4/12 on both sides of the edge]: HC_PRE with n > 4 rows FAULTs in the
  lane (row 4 x slot still busy) unless the r round trip (lane chunk out -> r in) <= 174 + 4 rgap. Composed (UNCHECKED):
  rd = 5 x (2+9) + RT + 114 = 169 + RT, RT = station round trip -> rgap 0 needs RT <= 5. C24 hub tree RT 45/46 + n4->root
  lanes (MISSING) -> PRE n >= 5 needs rgap >= 11-12 (+11..12 edges per row, ~14-15% of the 80-edge row II on those records).
  HC_POST and PRE n <= 4 are unaffected. Old 10-19 fused_top passed n 6 at rgap 0 only because its tree was short.
- (4) TOOL: four_role_calendar.py opt-in SEGMENTS mode (service per record = composed_service(): measured constants + wsc +
  bound station round trip; bound must declare legs_exclude_tree_nodes; wsc adds the 30 node edges; PRE x-slot rule fails
  closed with the needed rgap). Table mode unchanged (old 8 tests pass); 12/12 tests [CHECKED own]. Composition UNCHECKED until
  the full-tree vehicle runs. Illustration RT 46 (UNCHECKED): root capture -> done PRE/1 617, PRE/4 861, POST/1 334, POST/4 648.
- (5) UNIFIED TOP: DIE-HBM-10 20:40 split ACCEPTED. S-role fold census [CHECKED, s_role_fold_census.json]: 88 open S-role nets /
  28,504 b; reader-port mirroring finds an N-role template for every family except svg_SW* (8 x 1099 b): su 8 pgslice_lg,
  vmdel 16, hcollks 8, smw 2 + vmm, hleaf 2, dbk 2, hcollrs 2, xl ctl 2. 28 idx stream ports: NO producer RTL for the IDXN
  live/pre/replay strobes exists on main (contract in rtl/hbm_next/idxn/ot_hnx_idxn_keybuf.sv) -> ASK in the queue.
- NOT DONE: unified top RTL, calendar numbers, programme compile, whole-die build, nominal/mutant, VMX delta (all wait on C25b
  ~23:00 + the bindfull fix + the idx provider).
- NEXT (successor TOK-HBM-3, start here): (a) when C25b lands, write the bound file from its legs (station/lane registers only,
  legs_exclude_tree_nodes true) and run four_role_calendar.py --service results/tok_hbm_2_1028/service_segments.json --plan;
  (b) new opt-in tools/hbm_b2/fold_s_roles.py: instantiate the q0-half S-role copies from the C25b q0 hub content with params
  from the plan legs (templates = s_role_fold_census.json), fail closed on svg until its provider is named; (c) 52 rst_n from
  the C25b reset table; (d) idx stream provider per the queue ASK; (e) strict bind -> item 4 on epyc2 via ot-run.
  Worktree intel2:/srv/opentallas-scratch2/claude/wt/tok-hbm-2 (sparse, 119 MB); bench scratch /srv/opentallas-scratch2/claude/tok-hbm-2.
