# IDX.INDEX production-shape throughput (tput-hbm-1011/idx, 2026-10-11)

- Op: IDX.INDEX (DS-V4.1 AR 1M, 8 records / token, price 7,513.6 cyc / token).
- Source: claude/hbmdie-idxn-1011 4959a3820 (ot_hgi_seq IKS_I fix; ot_hgi_idx_unit / _native identical to origin/main).
- Bench: die e2e tb_hgi_e2e --real idxn (unit NGLOB 1 / IKS 1 + native selector + 4 scorers + 4 svc IKS stripes + DRAM model), FLAT 40 KLAT 40 VLAT 6, vectors `export ds --iks` of rank 0 L2 / L20 / L24.

| record type (records/token) | price | RTL dispatch->retire | ratio | exact |
|---|---|---|---|---|
| L24 / 28 / 32 / 36: C 2048x2, n 1,048,576 (4) | 1,080.0 | 9,291 | 8.60x | PASS (1,024 words, 0 mismatch) |
| L20: D 1366x2, n 1,048,576 (1) | 1,212.0 | 3,823 | 3.15x | FAIL (2,717 / 3,756 words mismatch) |
| L2 / 8 / 14: n 524,288 (3) | 658.9 | never retires | - | HANG (watchdog at 404,198 cyc) |

- Ratio of record: 8.60x (the only exact record type). Whole token >= 5.72x even charging L2 at its price.
- Mutant IDX_MUT=2 on L24: 136 of 1,024 IDX words mismatch, HGI_E2E FAIL (mut2_L24_head.log) -> FAILS as required.
- Status: UNQUALIFIED (> 1.10) plus two correctness gaps (L20 mismatch, L2 hang); reported to el1011-hbm-idx.
