TW3-S81-FRAMEGATE 10-19: re-bench of the landed frame LP RTL after the kit's region centres (frame_kit.py, soft-relay
floorplan) set the lp.py reset-hop runs (reach 405): col_h9 reset depth 7 (hops r1 3 / r2 6), col_h10 depth 8 (r1 4 / r2 7)
(was depth 2, 1 hop each).  Verilator 5.050 via ot-run (ot-epyc8 / ot-epyc5), source = claude/tw3-frame-1019 src2 staging
+ the re-emitted col_h{9,10}_l4_lp.sv / tb / record / spec (md5 checked).
  col_h9  MUT0 plan K2048/nseg4 PASS; each 12/12 PASS; unland / landread / reset plan FAIL (NEGATIVE_CONTROL_FAILED_AS_EXPECTED)
  col_h10 MUT0 plan PASS; each 12/12 PASS; unland / landread / reset FAIL as expected
The first MUT0 runs show "BENCH_SETUP_FAILED gen 0" for SET=each only because the launcher exported KK=2048 into the each
set (element round capacity 32 > 16 words); re-run without KK: *_0_each.client.log.
