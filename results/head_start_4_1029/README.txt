HEAD-START-4 results (collected by DIE-HEAD-28 sub-agent, 2026-10-29 09:37 PDT). Diagnostic/results only; no tool change, no waiver.

1. V1 (01f3eb4612e + BUFx8 row 027a94c5af1) -- NOTE: already on main via Codex merge 67fcee035 (08:26, 'CODEX: include measured
   START data delay and calibrated BUF8 model'), not via a COORD ROOT-MERGE approval.
   Tests (docker python:3.12, pytest, run_tests.sh, 14 START/CA/STA test files): V1 tree 027a94c 162 pass/1 skip; Codex 2fda405c2
   166 pass/1 skip; main f483150e0 163 pass/1 skip. CHECKED.
   Byte-identity with the data-delay input ABSENT (old = a4453d4004 pre-V1 tools):
   - HEAD (replay_head.sh, HEAD-START-3 plan5 spice_edge on proof_r1): head_old.json == head_new.json == head_cx.json (cmp), logs identical.
   - QC  (replay_qc.sh + replay_qc_sta.sh, DIE-QC-25 g25 plan + die_sta_related): plan json/log and sta_gate dir + log identical old == new == cx (cmp/diff -r). CHECKED.
   - KV  (replay_kv.sh on intel1, DIE-KV-28 sta_E_edge inputs: proofE, plan_e26a, native6 bind, 4 signed views, spice_edge, HB4):
     sta_old == sta_new == sta_cx == sta_main (diff -r, logs identical) and == DIE-KV-28 original die_sta_related.json. CHECKED.

2. Codex review (68271bfe7 per-corner data delay, 723c2267c per-corner candidate envelopes, 42d07e1f7/2fda405c2 source packet):
   same functions as V1 (load_start_data_delay, clock_start_edges.ival, die_sta_related sdd). Per-corner form subtracts each corner's
   data delay from the same corner's clock interval and unions: lo=min_c(iv_lo-dd_hi_c), hi=max_c(iv_hi-dd_lo_c). This is a strict
   tightening of V1's [dd_min_FF, dd_max_TT] hull shift (V1 = the same formula with the cross-corner hull); no double count (dd
   still REPLACES clk->Q in die_sta_related; planner unchanged). Legacy 'ports' docs and absent input take the old code path
   (byte-identical, above). Missing corner rows fail closed; model rows never reach die_sta_related. Corner keys are TT/FF in both tools.

3. START data-path (V1 plans on routed proof_r1, dd_head_v1.json = 1355 measured ports [dd_min_FF, dd_max_TT] + hop envelope model):
   plan          edges  unclean(all MODEL ports)  data-crossing fail  worst lo/hi
   v1p  (edge)    1643   283                       0                   113.0/135.7
   v1pc (cell)    1442   613                       21                  113.0/154.4
   v1w  (width)   1066   874 (872 model + 2 meas)  69                  113.0/133.3
   Gate start-port row (gate_pred.py, die_sta_related.count_align_start_ports on proof_r1) for v1p: 1190 measured ports 0 FAIL;
   min sync dist TT spice_cell 83.2 (125 <100) / spice_edge 104.3; FF 100.0/111.6; 453 new ports UNMEASURED -> fail closed
   (they need a rebuilt vehicle + measurement).
   Root cause of the unclean candidates: the hop envelope model (lo -62.4+0.760 h, hi 235.6+1.030 h) has a 298 ps intercept spread,
   width ~310 ps at the median 46 um hop vs measured per-port width median 89.7 (max 180.6) -> too wide to be clean.
   CLASS-B HYPOTHESIS CONFIRMED (probe_corelat.py, diagnosis only): clock_ocv_fn.branch adds B.cell_share*core_lat (+nB class-B
   stages) to EVERY tap, core_lat = plan common latency 450 TT / 380 FF, also to virtual START taps (part None) outside hard cores.
   1292/1643 v1p ports are virtual->virtual, 351 virtual->part leaf. Zeroing core_lat on virtual-virtual pairs only:
   OCV setup+hold median TT 110.6 -> 22.3 ps, FF 85.9 -> 16.8; spice_cell TT min sync 83.2 -> 129.8 (below 100: 125 -> 0),
   FF 100.0 -> 135.5; spice_edge TT 104.3 -> 150.5. The same callable widens the planner's START intervals.
   Verdicts: 68271bfe7 MERGEABLE; 723c2267c MERGEABLE (planner-only candidate envelopes, never qualify the gate; the per-corner
   envelope does not fix the wide-intercept problem above); 42d07e1f7 MERGEABLE (docstring only); 2fda405c2 MERGEABLE results-only
   (1.6 MB source packet + helper scripts). git merge-tree origin/main f483150e0 + 2fda405c2: clean. Order: V1 already on main ->
   68271bfe7 -> 723c2267c -> 42d07e1f7 -> 2fda405c2 (= merge the branch as is), after COORD approval.

Next: (a) ROOT-MERGE ASK: virtual START taps (part None) must not inherit the hard-core class-B latency in clock_ocv_fn.branch
(model fix inside the existing gate, not a new check; real partition/core taps keep it); (b) replace the bounding hop envelope by
measured rows on a rebuilt vehicle (453 new ports) or a per-port residual model; (c) rerun v1pc (spice_cell) after (a), rebuild +
measure, die_sta_related spice_cell+AOCV. START offsets stay PLANNED.
