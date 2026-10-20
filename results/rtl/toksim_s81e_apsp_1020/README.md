# TOKSIM-S81E: sparse a_proj field front on the remaining five sparse layers (2026-10-20)

Fills the last old-RTL a_proj nodes (L8, L14, L28, L32, L36; old 3,090.3 / 1,858.1 cycles) with the same vehicle as
results/rtl/codex_apsp_pickup_1020 (L2/L20/L24): unchanged scripts toksim_apsp_{fix,place,leg}.sh/.py (md5-identical to
that receipt), the same four FSEQ Verilator 5.050 executables (exe.sha256 identical to codex_apsp_pickup_1020/out/L2), and
real per-layer reduced fixtures (fix_logs/, sha256 of every fixture file; L2 regenerates byte-identically).

| layer | frames with BF rows | P231 | P230 | worst GO->root | +wire | cycles |
|---|---:|---|---|---:|---:|---:|
| L8  | 8 | all PASS | all FAIL | 1507 | 170 | 1677 |
| L14 | 8 | all PASS | all FAIL | 1507 | 170 | 1677 |
| L28 | 2 | all PASS | all FAIL | 1500 | 170 | 1670 |
| L32 | 2 | all PASS | all FAIL | 1500 | 170 | 1670 |
| L36 | 2 | all PASS | all FAIL | 1500 | 170 | 1670 |

Every single phase passes its xs_place check; every swap/shift mutant is rejected. Jobs: ot-epyc9 units
oth-ubuntu-{1750428(L8),1750426(L14),1749984(L28),1750126(L32),1749991(L36)}-1792488053, all exit 0.
Composition (tools/toksim_s81_compose.py, --check/--selftest/9 tests PASS): AR 834.0 -> 836.0 tok/s, measured 80.25 -> 81.02 %;
MTP 2,649.1 -> 2,653.9, 71.64 -> 72.21 %. Partial component composition; release token qualification remains open.
