# S81-SAFE-FIX/LEP bench receipt (10-19)
Source d77e88ef6 (claude/s81-safe-fix-lep-1019 = S81-FIX3 40686fe1c RTL, ot_s81sl_lep_core TXRP 1). Verilator 5.050, ot-epyc7 via ot-run.
| leg | expect | got |
|---|---|---|
| lep_exact s1 / lep_exact_s7 s7 | PASS | BENCH_PASS (1000+1000 beats bit-exact) |
| leph_exact s3 (lep_host) | PASS | BENCH_PASS |
| lep_mut_swap / nopair / noovf | FAIL | FAIL (963 / 2000 mismatches; overflow_fault 0) |
| leph_mut_ksoff / hdrop | FAIL | FAIL lep_host |
Witnesses re-recorded at TXRP 1: results/rtl/s81_lepv_1018/witness_{swap,nopair,noovf,ksoff,hdrop}.log (each matches its spec fail_regex).
Added cycles (handed to lanes/MU-DIE-S81.md INBOX): TXRP +1 edge on lo0/lo1 (lo_v/lo_d, both lanes); reset release +2 (reset_landing).
