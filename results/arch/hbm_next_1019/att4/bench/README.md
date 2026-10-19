# HBM-NEXT-ATT4 slice bench (2026-10-19)

DUT: `rtl/hbm_next/att/ot_hnx_att4_slice.sv`. One SM's KV-line-stationary 4-query attention: one `kv_line`, the ATT4 issue, and 4 lanes x 4 `tcpv_col` + the 4-leaf combine. Bench: `tools/hbm_next/att4_bench.py`, run under Verilator 5.050 on the fleet (ot-epyc4).

- **Golden.** Each lane ALONE, i.e. 4 single-query runs: `att_qk` scores, plus the csum8 run nodes of the lane's own list. Each lane's nodes merged across SMs equal `att_pv(p_l, K_l)` (`pv_cross_sm_merge_equals_att_pv_every_lane`).
- **Operands.** DS production shape:
  - head dim 512;
  - window 128 KV8 rows and top-512 KV4 rows a lane, out of 2,048 compressed rows;
  - real SM-KV8 / SM-KV4 line formats, golden qdq values.
- **SM jobs.** E1 "aligned": job s = every lane's run s, i.e. 32 ordinals.

| run | overlap (sigma) | union lines | ops | verdict |
|---|---|---:|---:|---|
| s00 | full (0.0) | 643 | 200 (incl. 160 single-lane P=1 ops) | PASS |
| s03 | ~0.78 (0.3) | 865 | 200 | PASS |
| s10 | ~0.49 (1.0) | 1,212 | 40 | PASS |
| sdj | disjoint (multi-user) | 2,179 | 200 | PASS |

Mutants (q4/p4/q10/p10 at sigma 0.3) all FAIL. The witnesses are `imut*.log` / `pvmut*.log` (bench verdict line), `*.json`, and `witness/<mut>_{q4,p4}.log` (simulator output).

| mutant | what it does | result |
|---|---|---|
| imut1 | lane ordinals count every union row (zero insertion) | FAIL (fault + 2,048-word node mismatch) |
| imut2 | PV lanes ignore the mask | FAIL (PV mismatch) |
| imut3 | PV x read at the union row | FAIL |
| imut4 | lane reads lane^1's mask | FAIL (QK + PV) |
| pvmut1 / pvmut2 | inherited merge mutants | FAIL |

**Throughput** (`throughput.json`).
- Op span = fixed + ~7.8 cycles a union row, from a linear fit over 80 QK and 80 PV ops:
  - QK: 126.5 + 7.76 U;
  - PV: 113 + 7.93 U.
- This is the model's `fixed + comp x U(N)/U(1)` form. A P=1 32-row op measures 363 / 377 cycles, which is the same line.
- 4 lanes at full overlap: one job is 401 PV cycles against 1,508 for the 4 lanes run back to back (3.76x). Disjoint lanes: 1,129 against 1,508.
- Record time = the maximum job. The SM assignment must be balanced over 32 SMs (E1.md §4).
