# S81 HC NORM tree: production layer re-measure at 319830486 (2026-10-14 ~21:50 PDT, ot-epyc4)
g2c.sh (tb_s81_die_layer NG 256 HCH 1 FP dpi --coef-split --h-stream, PIPE 1 HST 1 HTX 2 PGAP 600), same source, same binary options.
Source 319830486 = branch claude/s81-norm-tree-1014 with the die-layer bench file list fixed (dsfd_coll_xc + mtp_link_pair, broken since 8bd3bfdea).
The later reset change ee6ac6d7d (sync local-epoch reset) does not change cycles (reset lockstep exact).

| layer | base (NTREE 0) | NTREE 1 NT_K 67 | delta | per NORM (2 NORMs/layer) |
|---|---|---|---|---|
| L0 | 8,674 PASS | 8,244 PASS | -430 | -215 |
| L2 | 17,586 PASS | 17,165 PASS | -421 | -210.5 |
mut_hc FAIL (expected).  Layer-local NORM 713 -> 503 (conservative: smaller L2 saving, rounded down), 1.525x of 329.9.
Matches r2_127e27974 (-432 / -421) within 2 cycles.
