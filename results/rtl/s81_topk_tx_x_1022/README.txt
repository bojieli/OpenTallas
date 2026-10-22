TOPK TX x (MAIN) lockstep, STW-S81c-TOK4 10-22. Bench tools/s81_dv/tx_export_1021/run_tx.sh (Verilator 5.050).
DUT dsdv_idx_tx_n32 RDL=1 WDL=1 WDC=1 SCS=1 RIL=1 RHP=1 vs reference dsdv_idx_tx LPX=2 (TX_G -GREF_LPX=2):
  x2_m0  PASS 55,734 checks, 48 beats, 2 epochs (cycle-exact, every status/valid/payload bit)
  x_m1/m2/m3 (existing mutants) FAIL caught; x_m5 RIL bank-select mutant FAIL caught; x2_m6 RHP prefetch-ignores-pop FAIL caught
  x_m4 (write-mask mutant) PASSES = pre-existing bench gap (the bench writes all-ones masks; v baseline also passes MUT 4)
Booked latency: RIL adds one read-issue edge; with RDL the lookup pipe is LP 4 = reference LP 2 + LPX 2.
  LPX 1 is invisible at the ports (v and RIL-only both PASS vs LPX 1); LPX 2 is visible: ril_lpx0 FAILS vs the
  unextended reference at cycle 338 (beat 4 of the job moves one 4-cycle beat slot; beats 4.. and done +4 cycles).
  => compiled slot grid (lower_bk job_rank_tree_rd) must book the TX lookup pipe as reference LPX=2.
v2_m0: v config (RIL=0 RHP=0) still PASS vs LPX 0 (no regression).
