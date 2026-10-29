# TOK-HBM-3 (HBM whole-die token pass: idx provider, S-role fold, rgap pricing; successor of TOK-HBM-2)

## 2026-10-28 21:37 PDT RESULT / PARKED (slice 1; branch claude/tok-hbm-3-1028@84e393b762 on TOK-HBM-2 4d356dc103, merges clean with main)
- (2) IDX PROVIDER DONE [CHECKED own]: rtl/hbm_next/idxn/ot_hnx_idxn_kb_ctl.sv = wires only, reuse of the IDXQ quad-client
  class decode (codex/p3-compiler-2018 e938fd6db idxq client_quad l.72-75): clear=frame_start, live=KEY row 0, replay=KEY row>=1
  (same index), PRE pass-through; 0 added edges. Bench (keybuf NP4 RS0 + provider, verilator 5.032 docker): 18/18 PASS
  (IDXQ N=1..6 rows, d4g mode, both halves, bad schedule faults, 3 seeds); 4/4 mutants CAUGHT; -Wall lint clean.
  Bind table results/tok_hbm_3_1028/idx_kb_ctl_bind.json: 28 ports / 112 b from the d4g qctl (key_slot, key_index,
  frame_start; key_row 0, pre 0) = exact for 1-row records. N-row (MTP P=6) IDX records need ot_hnx_idxq_qctl/rootctl
  (codex/p3-compiler-2018 859b27b6b, CW=2) instead of the d4g qctl/rootctl -> DIE-HBM-10 ASK.
- (1) S-ROLE FOLD: tools/hbm_b2/fold_s_roles.py (opt-in, read-only) on the bindfull top -> FAIL_CLOSED [CHECKED own]:
  mirror copies of the 47 N templates (+ hb_idx__nwsh exists) need 79 S-role upstream instances that do not exist
  (sm_SW4..7, vmks_SW0..7, xc_SW0..7, cp_svg_SW*, sucore_S*, hb_coll_S*, cic_S*, vmfc_S*, hb_quant_SW ...). A mechanical
  copy rebuilds the S hubs incl 4 more SMs (against the 8-SM release). The fold map (which N-hub q0 instance serves
  each S net) must come from the plan -> ASK DIE-HBM-10. svg_S* (stack-1 key lines, 8 x 1099 b): no provider (same ASK).
- (3) rgap vs KX=8 [ESTIMATE, UNCHECKED except the KX=4 bound]: KX=8 needs a 256-row x store (+3,203 um2 x 32 lanes =
  0.10 mm2, +78 um lane macro width, lane re-plan/re-sign); rgap 12 on PRE n>=5 = MTP verify only (P=6): 60 edges a
  record x 2 x 43 layers = 4.3 us ~0.36% of a verify step; SU AR (N=1) 0. -> keep rgap (COORD 21:06 default).
- NOT DONE (wait C25b ~23:00 + fold map): bound file + calendar, 52 resets, strict bind, programme, whole-die build.
- NEXT (successor TOK-HBM-4): (a) on C25b: bound file from its legs (legs_exclude_tree_nodes) + four_role_calendar.py
  --service results/tok_hbm_2_1028/service_segments.json; (b) rerun fold_s_roles.py with the plan fold map (--params /
  map) until verdict != FAIL_CLOSED; (c) binder wires hb_idx__kbc_<q> from idx_kb_ctl_bind.json; (d) 52 rst_n from the
  C25b reset table; (e) strict bind -> programme -> epyc2 build via ot-run. Worktree intel2:/srv/opentallas-scratch2/claude/wt/tok-hbm-2
  (branch claude/tok-hbm-3-1028, sparse); scratch /srv/opentallas-scratch2/claude/tok-hbm-3. No live jobs.
