# DIE-QC-20 (QC die owner, successor of DIE-QC-19) -- 2026-10-28 17:5x PDT

Runs: intel2:/srv/opentallas-scratch2/claude/die-qc20-1028 (trial13b kit + chain20, g12m gate, probes). Branch claude/die-qc20-1028.

## 1. trial13 (DIE-QC-19) never finished -> killed; trial13b on main + workers
- trial13 kit ran 85 min and was in region 3 of 192 (py-spy: dme_region_tree join() recursion, merge mode, ~290 ps A0 sink early).
  It was built on the pre-RM216 tool; it would also have failed later in reset_tree (plan dir die-qc18-1028/gate has no cores/ sidecar).
- Rebased: 20576a47c5 = merge of claude/die-qc19-1028@8c8f0b1e43 onto main 013a9a8543 (RM216 DIE-S81-16 join budget + RM217 CLK-INV-CAL-1);
  conflict only in the kwargs lists (cell_paths + merge_only both kept).
- With RM216 the c_* merge regions still take 99-171 s each (probe2.jsonl; py-spy: 99.8 % join_down->merge, 75 % snake_leg) = ~7 h serial.
  Lowering DME_JOIN_BUDGET trades spread (16: 20-33 ps, 128: 20-26, 512: 11, 4096: 11-12; probe runs) -> not used.
- Fix (8f8a4ce1c8): opt-in die_trial --region-dme-workers N: dme_region_tree is pure per region, so the trees are computed in a fork pool and
  attached in the serial order. Default 1 = serial (unchanged code path). 4 new tests (serial == pool, plain/snake/merge) + all 19 test_die_trial*
  files PASS; real-data identity on 6 trial13 regions (cap.pkl): serial 596 s vs 6 workers 235 s, hash IDENTICAL (ident.log). CHECKED.
- trial13b kit (24 workers, plan copy with sidecars) 24:32 wall (kit20_time.txt).

## trial13b result (eval_trial13b.json, routed clock-only GRT TT/FF) -- CHECKED from eval JSON
- c_* A0-minus-glue min/med/max TT 13.4/50.2/63.2 (trial12 hang: 42.2/124.5/157.9), FF 24.8/56.8/69.5 (52.7/124.8/158.1): A0 still LATE, ~50 ps common.
- c_* in-region spread med/max TT 126.2/190.6 (trial12 172/232); glue spread max 190.6 (trial12 105) -> the snaked glue spread grew.
- su_c (hang, same 1.48/1.28 ratio): A0-minus-glue TT -2.1/6.2/17.2, FF -7.6/1.9/12.7 -> the ratio is right for hang; the c_* miss is merge-mode
  specific (snake legs deliver less than modelled), so a global ratio change would break su_c. Not rebuilt (see ASK).
- Render viewed (trial13b_plan_E2arms.png): in each c_* cell the A0 taps (purple) sit at the region-tree merge with green snake legs on the glue side.

## 2. Wide start ports -- structural fix exists: retime at tree nodes with MEASURED node falls (CHECKED)
- trial12 readout redone with node M rows (mk_clkfirst13, c12m_TT/FF, 18992/18992 nodes with fall).
- g12m (gate20.sh, main tools): plan width mode on the fall proof: 754/754 start edges clean, 0 ambiguous, 265 retimes at existing tree
  nodes, max_path_ambiguous 0, CA worst lo/hi 104.3/104.3; phase mode 488/488. Gate CA (die_sta_related, independent): start-skew fail 0/754,
  TT/FF PASS. No plan change -> no ASK.

## 3. Gate mode (RM165 on main): g12m/sta_gate (--clock-cell inv2 --core-insertion view)
- core_insertion verdict FAIL (fail closed): 864/864 early core taps (= 216 c_* A0 instances x clk_c0..3) have no signed view; real-view
  coverage 0/960 core instances (the two given views qfd_dv_s8x_crh / qfd_dv_s8_crh_rp1 match no instance pins). A0 view needed = ot_qwen_tile_node (a0k6).
- declared (planning): FF hold intra -312.5 / seam -238.8 (QC-18 -306.4/-223.5); landed hop FAIL as before.

## 4. AP db14fa47fb37 (a0k6) -- NEAR-MISS (CHECKED from signoff.json)
- TT setup +25.65 (was -221.66), DRC 0, pin audit 2566/2566; FF hold -24.56 WNS / -9333.65 TNS / 896 endpoints: all input-port seam
  hold (set_input_delay -min -40 vs vclk 205.33 pin-flop mean; late capture leaves at 222.7). LEC on 1_2_yosys.v EQUIVALENT (15:12, synth
  level); post-route LEC not run. -> a0k6 not signed off; parent adoption / btab shrink not done.
