# TOKSIM-S81B/FSMALL 10-19: router, a_proj, idx.q on the release frame RTL (GEN mu4c 19bf4121e)
Vehicle: slice 0's eight die frames, each on its release die.v master + lk (build_seq.sh), real rank-0 rows (L0 fixture: a_proj,
router; L2 fixture: indexer q), field of record (xs_place.compile_frame; a_proj phase 0 = lower_xs), checks of record
(xs_place / lower_xs check: golden bit-exact, row coverage, cycle-exact calendar, fixture tie). 83/83 RTL files blob-identical
to 19bf4121e (evidence/blob_vs_release_19bf4121e.txt). Verilator 5.050, ot-epyc9.
- attn.a_proj: 7/7 frames PASS (fixture 4/4 rows each), go -> last return 357..361 -> 361 + DAG wire tail 170 = 531 (old 628).
- ffn.router: 30/30 single BF phases PASS (5 phases x 6 frames); the 5-phase op is not sequenced -> pending.
- attn.idx.q: 48/48 single phases PASS; first 4 of 6 phases back to back PASS on all 8 frames down to go period 140
  (span 3 P + 296; floor not reached). Full 6-phase seq hangs: BENCH BUG, tb_toksim_fgu_seq ties spine r_v=0 so no op
  retires and the 5th go waits forever (also FGU experts_gu NO_END). DAG node idx.q (93) prices only the SU qbank -> mismatch.
