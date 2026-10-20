# S81-CAL (MU.S81.CAL, 10-20): 10-20 structural cycles priced, both pinned stage counts

Base: S81-CAL1 fold (claude/s81-cal1-1019 152d70002, carried onto this branch: dv_mu_calendar --edge-deltas,
results/token_pass/cal1_s81_1019, RATEFIX cycles). Tool: `fold_cal2.py` (ledger in its docstring) -> `fold.json`,
`edge_deltas_s140.json`, `edge_deltas_s201.json`; calendars `results/arch/mu_s81_1018/calendar_{ar,mtp}_cal2_s{140,201}.json`
(`dv_mu_calendar.py --edge-deltas ... --tag cal2_s<N>`, fleet ot-epyc5 units 2868197/2868369, `--check` SAME on 2868542;
legacy / l20split / cal1 records unchanged; test_dv_mu_calendar PASS).

| ledger (edges a critical occurrence) | grade | AR token | MTP step |
|---|---|---|---|
| XG5 x path +2 / ring +1 a field op (290 / 312) | bench RTL | +870 | +936 |
| COLL s7 +1 tx +3 rx a coll phase (257 / 281) | bench RTL | +1,028 | +1,100 |
| idx3 non-inline reader +36 worst pair RT +21 W->E chain, 8 idx.score (140 only) | MODEL | +456 | +456 |
| stage hops (N-120) x (1006 + 2): 140 -> +20, 201 -> +81 | MODEL | +20,160 / +81,648 | same |
| COLL ACK +2 a phase (off the data path) | sensitivity | (+514) | (+562) |

Per layer (structural only): 140 max +116 / mean +58.8 edges; 201 max +59 / mean +47.4; plus 1,008 edges a stage hop.

| stages | composer | AR tok/s CAL1 -> CAL2 | MTP tok/s CAL1 -> CAL2 | MU AR / MTP agg (legacy 59-group calendar) |
|---|---|---|---|---|
| 140 (122 frames, PRIMARY) | RATEFIX | 1,087.7 -> 1,066.0 (-2.0%) | 3,335.9 -> 3,286.1 (-1.5%) | 46 u 49,034 / 10+1 u 32,861 |
| 140 | TOKSIM-S81B | 945.3 -> 928.8 (-1.7%) | 3,001.9 -> 2,961.5 (-1.3%) | 42,724 / 29,615 |
| 201 (116 frames, FALLBACK) | RATEFIX | 1,087.7 -> 1,011.1 (-7.0%) | 3,335.9 -> 3,159.2 (-5.3%) | 50 u 50,557 / 10+4 u 31,592 |
| 201 | TOKSIM-S81B | 945.3 -> 886.9 (-6.2%) | 3,001.9 -> 2,858.0 (-4.8%) | 44,345 / 28,580 |

Calendar periods: 140 AR 1,011,772 / MTP 1,335,560; 201 AR 1,072,804 / MTP 1,396,592 (lemma PASS, 0 collisions).
MU is bound by the per-user token (T > period) in every row.

Caveats (owed): the MU rows still use the 59 legacy Sxxx windows (+ the per-stage bound), NOT the 140 / 201 physical
stage windows (DECISIONS_FOR_CLAUDE 13:04 / 13:08): the physical-stage occupancy calendar, and the re-split of a
layer's routed-expert field ops / collectives when one layer spans 2-3 stages, are not priced here. idx3 numbers are
MODEL until lane S81-IDX3R's rg3 bench lands. Capacity campaigns f122_140 / req201 (ep9) not re-run.
dv_mu_calendar change: `--tag` output suffix; MTP user search steps down when an odd count has no A/B colouring
(201 MTP: floor gave 11 -> FAULT, now 10 + 4 fillers PASS).
