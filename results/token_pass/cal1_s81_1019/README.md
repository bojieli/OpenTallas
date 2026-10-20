# S81-CAL1 (MU.S81.CAL.1, 10-19): closed edge deltas folded into the S81 MU calendar and the token pricer

Compiler/pricer only, static schedule. `fold_cal1.py` counts each delta on the critical nodes of the token DAGs
(`token_path_20261009/ds_rom{,_mtp}.json`) and adds it to the two token compositions. It writes `edge_deltas.json`.
`tools/s81_dv/dv_mu_calendar.py --edge-deltas edge_deltas.json` then re-compiles the MU calendar into
`results/arch/mu_s81_1018/calendar_{ar,mtp}[_l20split]_cal1.json`. Every number here is priced: compiled or bench edge
counts times the occurrence counts. No new token measurement was made.

| delta | edges | per | source |
|---|---|---|---|
| CAPC2 PINPIPE | +2 | field op instance (+1 in, +1 out; the reset +2 is boot only) | capc2 1e559612c, gate 1f4c80cf6 |
| CAP ED/LD | +24 (bound: the last return word is on E; W lane 3 is +16) | field op not measured on the L16/E24 cap | tok2-capld 636f4c670 |
| XDIE guard 2 / win 3 | +1 | crossing phase (AR = RS + AG = 2) | xdie-s81-mu eb0d31c63 |
| LEPCAP IN_PIPE | +1 | crossing phase, plus 2 a token (t_host, t_kd) | lepcap bb66563eb / RTL eec2dca41 (not in mu3/mu4c) |
| lower_vpx P6 + send frame -2 | +13 | attn.a_allgather (last of 14 RD sends) | 73879e4d2 + tok4 6ea6ea0a9 |
| HOP +2 (07ff2cc83) | 0 | frame artefact (TOK4) | - |

RATEFIX wq_b (fullsix P126) was measured on the L16/E24 cap exe with `--shifts`, so CAP ED/LD is not charged
again there. TOKSIM-S81B composes wq_b from the old number, so it is charged there.

| composer | AR tok/s before -> after | MTP tok/s before -> after | MU 46 AR / 10 MTP agg |
|---|---|---|---|
| RATEFIX (s81-ratefix ff8fa3745, both_p126_t276) | 1,095.5 -> **1,087.7** (+7,872 cyc, -0.7 %) | 3,354.9 -> **3,335.9** (+8,475) | 50,394 / 33,549 -> **50,035 / 33,359** |
| TOKSIM-S81B (953d8d510, strict bit_exact) | 951.9 -> **945.3** (+8,832) | 3,019.1 -> **3,001.9** (+9,507) | 43,787 / 30,191 -> **43,482 / 30,019** |

**MU calendar.** Per-stage bound is +265 edges, the largest per-layer delta (MTP step x6). Token deltas are +8,832 AR
and +9,507 MTP.
- AR: 46 users, slot 21,313.7 -> 21,505.7, period 980,428 -> 989,260. Lemma PASS: 5,474 windows, 0 collisions.
  The latency user passes.
- MTP: 10 users + 1 filler, slot 124,524 -> 126,112, period 1,303,400 -> 1,312,908. Lemma PASS: 1,309 windows,
  0 collisions.
- l20split variants: PASS. The helper S030 has 0 collisions.
- The fleet run (ot-epyc5, unit oth-ubuntu-548701-1792476636, `fleet_calendar_run.log`) is byte-identical to the
  local one.
- MU stays bound by the per-user token: T > period in both modes.

**Sensitivity (not folded).** lower_vpx issues one RD beat every P = 6 edges. The xdie gate issues one beat a cycle,
so it is lane-bound at 1.335. If every gather and AR phase on the critical path were issued at P6 (only a_allgather is
lowered today), it would add ~36.8k AR / 39.1k MTP cycles: RATEFIX would be 1,052.6 / 3,250.8 and S81B 918.6 /
2,932.8. That is a pricing risk for rows_allgather (132 beats) and the AR RS/AG (40 beats each), which the compiler
does not lower yet.

**Not folded** (not yet measured or not closed): SVC4 attw landing (+6 a result) and production engine (+12 a score
beat), still pending in S81-SVC5; SMWIRE SOT (+3 q words). The XDIE guard-2 rerun (out_g2 on ot-epyc5) is live;
it confirms or refutes +1 a phase.
