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
TOPK TX y (FB) = x + SPLIT=1 (score store as two bank groups dsdv_idx_txm_grp: column A banks 0-4 = hardened child with
its own clock root, column B banks 5-7 in the parent; parent registers pa|pb into rd; 0 cycles):
  y_m0 PASS vs reference LPX=2, 55,734 checks; y_m1/m3/m5/m6 caught; x3_m0 = x (SPLIT=0) regression PASS.
Bench gap closed (STEWARD 10-22): tb_tx_miter now rewrites lane 0 window 0 under partial mask 16'h5a5a before the
lookups (masked-out positions must keep the first write). wmask/: x, y and v MUT0 PASS (56,074 checks); MUT4 (write
mask) now CAUGHT on x, y and v; x and y MUT1/2/3/5/6 all caught on the new bench.
Census fix (STW-S81c-TOK4 10-22, x gate native census FAIL: 7 drivers > 32 loads): with RIL the beat select is a
registered one-hot sel_oh (lp_i[LP-1][3:0] 80..125 loads), fourth pop predicate u_popk (fields 0..2/3..5/6..8;
u_popb 52), okk[17] = nx_sm[5:0] clear copy (okk[14] 38), u_ctq = nx_tc_pred[7:0] clear copy (u_ctp 34); 0 cycles.
census/: x and y MUT0 PASS (56,074 checks), MUT1..6 all caught on x and y; v MUT0 PASS (RIL=0 path unchanged).
