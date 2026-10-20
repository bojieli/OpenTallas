# TOKSIM-S81C/FSEQ 10-19: ffn.router and attn.idx.q as full phase SEQUENCES on the release frame RTL (GEN mu4c 19bf4121e)
Vehicle = TOKSIM-S81B/FSMALL's (slice 0's die frames on their release die.v masters + lk, build_seq.sh; real rank-0 rows;
xs_place field of record) rebuilt on tb_toksim_fgu_seq.sv = FGU 4cd48a7ab (+RETIRE: rows written back after each phase's
last calendar word, so >4-phase sequences retire) + +PHASE_VM (router: per-phase x segment reload at go). Every RET word
assigned by calendar and xs_place-checked per phase (golden bit-exact, coverage, cycle-exact, fixture tie where it exists).
DUT sources identical to FSMALL's 83/83-SAME-vs-19bf4121e set; Verilator 5.050, ot-epyc9; 82 ot-run jobs, all exit 0.
- ffn.router (5 BF phases, 6 router frames): PASS down to go period 231 (230 FAILS on all 6: returned values correct, but
  each BF return word carries the NEXT phase's segment index -> RTL schedule constraint, BF gos >= 231 apart).
  span 4 x 231 + 345 = 1269 (max), + DAG wire tail 150 = 1419 (old 977.2).
- attn.idx.q field projection (6 phases, 8 frames): PASS down to P 126 (125 FAULT status 11): 925 standalone; merged
  with wq_b (17 phases, same x, same frames) 2311; wq_b alone 1554 -> idx.q adds 757 behind wq_b. Golden-only tie
  (fixture holds q after RoPE/FP4). The DAG's sparse-layer wq_b (1559.6, 12288 = 8192 + 4096 indexer rows) already
  prices this projection: fold as wq_b by_old 1559.6 -> 2311 + 317, or wq_b 1554 + 317 and a 757 node (not both).
Files: run_fseq.sh, build_seq.sh, FSEQ.json (record), evidence/sweep_all.txt (568 runs), evidence/L*/... res json + logs.
