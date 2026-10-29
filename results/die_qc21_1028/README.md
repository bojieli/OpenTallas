# DIE-QC-21 (QC die owner, successor of DIE-QC-20) -- 2026-10-28 19:0x PDT

Runs: intel2:/srv/opentallas-scratch2/claude/die-qc21-1028 (trial14 kit + chain21/gate21 g14, a0k6m kit). Branch claude/die-qc21-1028.

## 1. trial13b gate (DIE-QC-20 chain20 g13b) collected
- declared FF hold intra -276.29 / seam -250.12 (g12m -312.5 / -238.8); TT setup intra 357.7 / seam 379.4. Plan proof width 754/754 clean,
  start-skew limit 104.6, min sync 131.1; phase 491/491. Gate mode (--core-insertion view): core_insertion FAIL (864 missing). UNCHECKED.
- worst intra hold: c_W4_tn_01 glue t15 -> A0 c1 (the c_* A0 lateness); worst seam: c_W5_bf_01 -> io_serdes_2.

## 2. Root cause of the c_* A0 lateness: the DME delay model, not the snake legs (CHECKED from routed trial13b arrivals)
- Per-leg routed/model (12626 DME legs, snake_meas.py/fit.py): plain 1.18 TT, snake 1.21 TT -> snakes are NOT under-delivering.
- By end-node fanout: fanout-1 legs 1.06 TT / 0.92 FF, fanout-2 (binary merge) 1.26 / 1.08. The BUFx24 1x-ladder STAGE_1X_TT has no
  fanout term and the wrong stage/wire split for inv2 (fit: d0 16.77 ps vs 20.83, k1 0.110 vs 0.014 ps/um, kf 10.95 ps per extra fanout).
- Branchy glue subtrees therefore arrive later than modelled while the A0 merge leg (fanout-1 chain) does not: realized
  early/model ratio c_* 1.288 TT / 1.121 FF vs the 1.48/1.28 used (su_c hang: 1.406/1.247) -> A0 ~50 ps late (decomp.py).
- Calibrated model (validate.py) predicts glue-minus-core median c_* 367.9 vs routed 367.5 TT, 319.9/319.8 FF; su_c 39.4/39.7.

## 3. Fix: opt-in die_trial --region-dme-stage-cal FILE (shared tool, default off)
- inv2_stage_cal_trial13b.json (TT fit) replaces STAGE_1X_TT in leg_ps/chain_ps/snake_leg/merge_point_delay, adds kf at every binary
  merge node, prices the tap leg with the fitted wire. Early ratios become measured/calibrated-model: --region-dme-early 1.0
  --region-dme-early-ff 0.87 (= FF/TT of the predicted c_* glue-minus-core). 3 new tests + 93 test_die_trial* PASS; flag off = globals unchanged.
- Estimate before build: predicted c_* A0 offset median ~0 (error -35..+21 per region); the GRT residual (~57 ps median glue spread,
  not explained by any plan feature, tap legs exact) stays.

## 4. trial14 (one rebuild; kit 23:12 with 24 workers) -- routed clock-only GRT, CHECKED from eval_trial14.json / val14_summary.json
- c_* A0-minus-glue TT min/med/max -28.7/-3.8/18.3 (trial13b 13.4/50.2/63.2), FF -9.7/14.1/35.1 (24.8/56.8/69.5).
- c_* in-region spread med/max TT 50.8/130.9 (126.2/190.6), FF 57.0/127.7. su_c 60.9/95.9 TT (74.7/94.2), A0-minus-glue 7.6/13.2/21.9.
- Model check on trial14: predicted glue-minus-core c_* 423.6 vs routed 419.6 TT (FF 361.6/359.9).
- Gate g14 (gate21.sh = gate20 on trial14; UNCHECKED): declared FF hold intra -225.0 (g13b -276.3), seam -138.3 (-250.1); TT setup
  421.6/507.2; width 754/754 clean, CA min sync 131.5; phase 491/491. Worst intra now glue-glue (c_W2_bn_01 t21->t8, damage 188.8):
  the residual glue spread + kit contract window 0 (partition taps on one ideal clock). Gate mode: core_insertion FAIL (864 missing).

## 5. a0k6 (ot_qwen_tile_node) FF input hold
- db14fa47fb37 routed data was deleted by the autopilot (16:12) -> no warm post-route hold ECO possible.
- Root cause of the near-miss: KIT_MODES FAIL in the original run (CTS hold repair timed FF hold against the TT vclk 250).
  Restaged copy kits/ot_qwen_tile_node_a0k6m with kit_modes.py stage (two-mode CTS: FF vclk 202.5) -> AP afe7e72b8696:
  STRUCTURAL at CTS: FF hold ws -48.26, 1544 planned input endpoints (> 1540 input-port bits) + 684 internal (ws -17.4).
  In the honest FF frame the input-port seam hold is ~-48 ps: the input face flops' clock (A0 node insertion) lands later than
  vclk_ff 202.5 + the -40 ps tol window. Not signed; no parent adoption / btab shrink. Shared seam_hold contract (sender 25 / seam 25)
  would need plan clock.seam_hold for all QC senders (not a per-core fit) -> ASK.

## 6. Early-tap views needed for gate mode (864 taps, early_views.py on ev_a0meas.json)
- 720 qfd_tile_nk_a0c (kit qfd_tile_nk_a0ck) + 48 qfd_tile_nl_a0c (kit qfd_tile_nl_a0ck): c_* partitions x clk_c0..3 (u_tXY.ck,
  declared 665.8/576.5, u_t30 692.6/601.9): NO signed views.
- su_c (96): qfd_dv_s8x_vmr 36 (signed f4kfinal 77013e5059), qfd_dv_s8_crh_rp1 12 (signed f4g 5ed4500430), qfd_dv_s8x_prog 12
  (signed s8b 6aa7f1fc4d), qfd_dv_s8x_crh 12 (qc/closed), qfd_dv_s5_su8_rst3 12 (intel1 qccores1-1027 rst3_k0), qfd_dv_s8x_btab 12
  (NOT signed; a1713 route CORES-EARLY-3). Signed ones need to be passed to die_sta_related --core-view with matching pins.
