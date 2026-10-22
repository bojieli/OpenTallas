# MU.S81.L20.RTL bench evidence (S81-RTLGAP/RG-L20, 10-21)
Existing rank-tree compose bench (tools/s81_dv/layer_prog/bk/run_idx_tree.sh, compiler stimulus lower_bk tree-rd,
checker tree-rd-check) with DIEM=1: each of the 6 dies = the 72-frame die master dsdv_bk_sel_vmtx (vmux + bk_sel +
dsdv_idx_tx_n32), TXS=1 (SRAM macros), Verilator 5.050, ot-epyc5. Stimulus dirs = the S81-L20SUB 10-19 cases (unchanged).
| case | TX_MUT | verdict |
|---|---|---|
| k3 | 0 | PASS (tx_span die1 17963-19406 1431, die2 19564-20987 1424) |
| k6 | 0 | PASS (5 transmitting dies) |
| k6_mut_corrupt (stimulus mutant) | 0 | FAIL as expected (16 vo mismatches at the root) |
| k3_tx1 neighbour score field | 1 | FAIL as expected (tx-seq) |
| k3_tx2 last BEAT without last | 2 | FAIL as expected (tx-seq) |
| k3_tx3 grid one pitch late | 3 | FAIL as expected (tx-window) |
| k3_tx4 capture without lane-valid mask | 4 | PASS = NOT caught (k3 stimulus has no partial lane-valid BEAT whose masked fields matter; never exercised by the 10-19 bench either) |
Every TX and VO line of k3 and k6 is identical (edge and value) to the 10-19 dsdv_idx_tx runs (diff 0 lines):
+0 schedule edges, lower_bk job_rank_tree_rd prices unchanged.
Logs: tree/<case>/run_*_d1.log.gz, client logs m0..m4.log.
