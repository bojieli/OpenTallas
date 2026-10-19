# G2 regression on the 2c+r rstop (Verilator 5.050, ot-epyc5, 10-18 12:30-13:10)
| bench | expect | result |
|---|---|---|
| slice_eng VS_MUT 0 (seed 3; SID 3 = col 1 tier N) | PASS | PASS (sums 4, gates 4, half_rows 80, mismatches 0, fault 0) |
| slice_lep none lepe | PASS | BENCH_PASS (200+200 beats bit-exact, faults 0) |
| slice_lep none lepe_nh | PASS | BENCH_PASS (200+200, faults 0) |
| slice_lep swap lepe (negative control) | FAIL | NEGATIVE_CONTROL_FAILED_AS_EXPECTED (69/200, 75/200, mismatches 144) |
| xdie_s81 min (gm golden) | PASS | BENCH_PASS (1380 beats on deadline, late 0, faults 0) |
Scripts run.sh / run2.sh; client logs *.client.log; bench logs eng/, slep/.
