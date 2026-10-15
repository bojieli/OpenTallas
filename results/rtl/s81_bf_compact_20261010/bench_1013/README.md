# BF pair exact bench at main 602d3ab9b (s81-bf, 2026-10-13)

`tools/s81/bf_txn_bench.py --variant recut --params QZE=1,TCG=1,BXST=2,FXST=2,PINLAT=1,HCOL=1 --mutant mutant_pinlat=PINLAT_MUTANT_B0
--mutant mutant_fxst=FXST_MUTANT_TAG` on ot-pve1 (Verilator 5.050), source = `git archive` of main 602d3ab9b
(`source_commit` in terminal.json is the snapshot's own git-init commit, not a repository commit).

| case | result |
|---|---|
| positive | PASS: 456 rows bit-exact (912 value / 448 config assertions), 124,422 element cycles, TXN MATCH 232/224 partials |
| mutant_dp, mutant_recut, mutant_pinlat, mutant_fxst | FAIL as required (DIFF TXN) |

`../bench_prep_1013/` is the prepared package of this bench (`run_bf_native_exact.py --prepare-only`, which needs the
repository history for its pinned reference sources): closure-loop benches run from a source snapshot without history
and pass it with `--prep`.
