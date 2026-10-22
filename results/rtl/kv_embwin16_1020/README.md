# KV-EMBWIN16 10-20 bench witnesses (claude/kv-embwin16-1020 @ec3bf3acb, Verilator 5.050, ot-epyc7 job oth-ubuntu-2209651-1792562969)
- kvcal15_gate.log + kvcal15/: tb_kvcal15_emb_die at the die point (GEN9 i13a relays + HROOT_LAND + skew 1 + PIPE_JOIN) with the
  row header deadline of the ew595 window (row_tx slot 490 edges after the join start, last join word 489): PASS; m1-m4 (KV-CAL15) FAIL;
  m5 = window 594 (deadline 489) FAIL header; m6 = priced window 272 (deadline 167) FAIL header.
- ew595_run_dcal_bc4_production_m*.log: boot target 11 (ew595 image) -> qkd_d2d_cal_seq_bc4_ew595 -> real cal pair vs the MU pin tile
  on the ew595 image: m0 PASS; m1-m5 FAIL (as bc4); m7 target 11 from the base window image FAIL (table entry 4 differs).
- ew595_run_dcal_bc4_miter_m*.log: 600k-edge miter vs the frozen bc2 wrapper on the ew595 image: m0 PASS (53 bits, 80 resets,
  117 starts); m1-m3 FAIL; m7 reference on the base window image FAIL (mismatch edge 8134).
