# S81-RATEFIX token re-composition (10-19)
`python3 results/token_pass/ratefix_s81_1019/compose_ratefix.py` = tools/toksim_s81_compose.py on the committed
TOKSIM-S81 element records (measured_s81_1019, mu4c 19bf4121e) + per-scenario overrides (overrides/*.json, win per op).
Nothing re-priced; unmeasured ops keep their committed numbers.

| scenario | AR cyc | AR tok/s | MTP step | MTP tok/s | MU 46 AR / 10 MTP agg |
|---|---|---|---|---|---|
| baseline mu4c | 1,173,913 | 1,022.2 | 1,566,172 | 3,186.6 | 47,022 / 31,866 |
| wq_b pipeline P126 | 1,119,033 | 1,072.4 | 1,511,292 | 3,302.3 | 49,328 / 33,023 |
| top-k INDEXED13 + tail 276 | 1,150,242 | 1,043.3 | 1,542,501 | 3,235.5 | 47,990 / 32,355 |
| **both (P126, t276)** | **1,095,362** | **1,095.5** | **1,487,621** | **3,354.9** | **50,394 / 33,549** |
| both (P130 margin, t276) | 1,097,602 | 1,093.3 | 1,489,861 | 3,349.8 | 50,291 / 33,498 |

Note: `pct_measured` in cycles.json (37.2 -> 32.7 % AR) is the MEASURED-COVERAGE share of the critical path, not a
fraction of the target rate; it falls because the measured ops got shorter. wq_b is pure compiler on release-blob RTL;
the top-k row is newest-element RTL (successor quarter, not yet on the release die).
