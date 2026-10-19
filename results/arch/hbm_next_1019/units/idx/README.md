# HBM-NEXT-UNITS-IDX — N-row IDX records (HGI-1R), 2026-10-19

Scope item 4 of lanes/HBM-NEXT-UNITS.md: IDX.INDEX N queries, IDX.TOPK heap row reset, IDX.UNION verify expert-union record.
All benches: Verilator 5.050 on the fleet (ot-epyc4 / ot-epyc5), logs committed beside this file.

## Verdicts

| Record | RTL (rtl/hbm_next/idx/) | N = 1 vs d4g | N rows | Mutants (FAIL witnesses) | Measured row II | Price (isa_rows.md) |
|---|---|---|---|---|---|---|
| IDX.INDEX | `ot_hnx_idx_scheduled_static`, `_calendar_rows`, `_parent_static`, `_vm_query_static` (d4g query / scorer / selector / link unchanged) | **IDENTICAL**: every score and TX flit at the same edge (700 lines), both with the d4g programme and with the row frame | N = 1..4 PASS bit-exact (10,928 scores + 512 top records a row) | m11 query-seen clear, m12 link clear stripped, m13 selector row clear, mstride (row strides 0), mpitch940 (collision fault) | **953** (done 1,399 / 2,352 / 3,305 / 4,258) | 152 a row (of the 658.9 frame) |
| IDX.TOPK | `ot_hnx_idx_topk_rows_static` (fork of the H-MTP2 rows engine) | same golden VM image as d4g `ot_hbm_idx_topk_static`, both PASS (d4g m6 852 cyc, m1 153) | P = 2,3,4,6 PASS (m1 113, m2 163, m3 212, m4 260, m6 359) | t_m1 heap not reset per row, t_m2 row stride dropped, t_m3 lane insert rate | **49.2** | 47.0 |
| IDX.UNION | `ot_hnx_idx_union_static` (new, op 5) | new record (golden `tools/hbm_next/isa_rows.idx_union`); N = 1 = 6 ids, 48 cyc | N = 1,2,3,4,6 + 8 random + 3 fault records PASS | u_m1 descending pop (E2 order), u_m2 kappa dropped, u_m3 row stride dropped, u_m4 U = N k | ~18.6 (48 / 67 / 90 / 100-101 / 140-142) | N x 6/8 + 24 (0.75 a row) |

## IDX.INDEX: the price miss (6.3x a row)

- The row frame is the d4g single-row microprogram, re-launched every `pitch` edges (2 issue streams, field-class
  collision = fault). The calendar's binding span is the **selector** (top-512 over each row's 10,928 scores: edges
  309..1,261 = 953). Next spans: link 307, scorer array 306, query unit 225, operand reader 145.
- Pitch sweep at N = 2 (`pitch_sweep_n2.txt`, `tools/hbm_next/hnx_idx_pitch_sweep.sh`): 950/951/952 PASS, 940 and below
  FAIL (collision fault + score errors). The true minimum is in 941..950; the compiled 953 is within 1.3%.
- **The key stream is NOT shared**: each row re-issues its key slots (N key passes at pitch 953). The D2 plan's "one key
  stream, query ingest 152 a row" needs the scorer array to score N queries per key line AND N selectors (one per
  row; small replicated slices). With N selectors the II would fall to the link/array span (~307); 152 also needs the
  array to take the N queries in one key pass.
- Also pre-existing: the d4g RTL record is 1,397 cycles (GAP 100, registered pins) vs the priced 658.9 frame.
- N = 4 record: measured 4,258 vs priced 658.9 + 3 x 152 = 1,115. **CMTP must re-time IDX.INDEX at frame 1,397 + 953 (N-1)**
  (DS indexer only) and report the MTP delta; if significant, the next RTL step is the N-selector / N-query scorer above.

## IDX.TOPK / IDX.UNION

- TOPK: 49.2 per added row vs 47.0 priced (+4.7%), and the hnx engine is faster than the die-bound d4g at every N
  (m6 359 vs 852).
- UNION: bound by the idx packet client (4 sequence numbers, 4 writes / 10 edges): ~18.6 a row vs 0.75 priced, but the
  whole record is <= 142 cycles at N = 6 -- negligible next to INDEX; no redesign proposed.

## Evidence

- `index/`: verdict_index.txt (bundle 71e301580, ot-epyc4), run_*.log, run_mpitch940.log (fail witness),
  run_mpitch952_pass.log (old mutant pitch II-1 PASSES: bench now uses II-13), pitch_sweep_n2.txt, calendar_frame.json.
- `topk/`: verdict_topk.txt (bundle 4803b9c42, ot-epyc5), run_t_*.log.
- `union/`: verdict_union.txt (bundle b623d2b7e, ot-epyc5), run_u_*.log.
- Bench: `tools/hbm_next/hnx_idx_bench.sh OUT {lint|index|topk|union}`; INDEX builds are --hierarchical, ~29 GB RSS,
  30 min each (declare --mem 64).

## Next (not done)

1. CMTP re-time with the measured INDEX II (953) and TOPK II (49.2), UNION cycles.
2. If INDEX matters for MTP: one-key-pass INDEX (N query lanes per scorer, N replicated selectors / link row slots).
3. Re-gate of the touched tiles (idx_query with N x 4,096-word store, idx_selector, topk) under hnx_ names.
