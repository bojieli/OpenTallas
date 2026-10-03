# DS-V4.1 ROM edge index scorer: replay (handover state, 2026-10-03)

Branch `claude/dsrom-edge-scorer-20261003`. Pricing basis: `claude/dsrom-nearhbm-20261003` @ 723243a4a, variant (i).
This is a handover snapshot. The build continues with Codex (`/tmp/claude-review-20261003/HANDOVER_TO_CODEX_2.md`).

## RTL (default-off, new files only)

- `rtl/dsrom_sys/ot_dsrom_edge_lsel.sv`: the per-stack streamed exact top-512.
  - Threshold prefilter (drop key <= T, the K-th of S).
  - Dense 16 -> 64 lane compaction into a line FIFO.
  - Folds S ++ FIFO lines through the unchanged `ot_hdc_tselect` (W=64). The FIFO is the selector's virtual line memory, read with predicted addresses and asserted in simulation.
  - `ot_dsrom_edge_ram` is the memory: behavioural, or `MACRO=1` with v2 aligned `ot_sram_1r1w_128x256` tiles.
- `rtl/dsrom_sys/ot_dsrom_edge_merge.sv`: the merge.
  - A merge-path 2-way merge at 16 elements/cycle; the loop is rotate -> comparators -> popcount -> pointer.
  - The bitonic sort runs in a registered pipeline off the loop.
  - A 4-way tree.
- `rtl/dsrom_sys/ot_dsrom_edge_hub.sv`: the position-order merge of the 4 stack lists, then the global `ot_hdc_tselect`.
- `rtl/dsrom_sys/ot_dsrom_idx_edge.sv`: the per-stack element `ot_dsrom_edge_stack` and the die composition.
  - Each stack element is `ot_hdc_v41x_idx_array_l` (NS 4 x NK 4, FPL 7 / FML 5 / QL 5) + lsel.
  - Global position = 64*(j>>4)+16*s+(j&15).

## Exactness (class A): `select.json`, PASS

```
python3 tools/dsrom_edge_scorer_campaign.py select --real-cache <pickle of rtl_hdc_v41_select_campaign.real_sets(48)>
```

- **Golden.** `sorted(topk_lowest_index(s, min(512, n)))` (tools/hdc_golden_v41.py) on BF16 scores.
- **Functional set: 84 queries, 0 errors** in each of three modes: at the HBM rate (11 keys/cycle/stack), with 30% bubbles, and at the MAC rate.
  - Edge sizes: n = 0, 1, 15/16/17, 63/64/65, 511/512/513, 2047-2049, 4097.
  - Tie-heavy alphabets: +-0, +-inf, subnormals.
  - Data patterns: random, all-equal, signed zeros, ascending, descending, all -inf, ties at the threshold.
  - Real reduced-vehicle index scores, scaled.
- **Shipped set: 7 queries, 0 errors.**
  - L20 full scan at 200K (50,000 keys) and 1M (262,144 keys) positions, ratio 4, on real-scaled, tie-heavy and candidate-masked (-inf) scores.
  - The 1M ascending worst case.
- **Measured.** At the HBM rate the scan runs at 44.0 keys/cycle per die with 0 stalls in every case, including ascending, where every score survives.

  | Context | Last key -> stack lists (cycles) | Last key -> die selection out (cycles) |
  |---|---:|---:|
  | 1M | 314 | 490 (0.41 us) |
  | 200K | 400 | 570 |
  | 1M ascending (worst case) | 588 | 745 |

  These exposed tails go to the model. The model's merge level (161 cycles) assumed concatenation and so did not price the cross-stack position merge.

## Not done at handover

- **Score bench** (`tools/dsrom_edge_scorer_campaign.py score`, `tb_dsrom_edge_stack.sv`; full score slices + lsel per stack, every key's score checked).
  - It is written and was never run: the remote launch on ot-epyc1tb did not start.
  - Run `score` (mixed classes), then `score --contexts 200000 1048576`.
- **Synth + SS/FF screen and ORFS P&R.** Not launched. The plan is below. Each job goes through `tools/run_abi3_physical_aligned.py --macro-track-gate`, with `--macro-view ot_sram_1r1w_128x256_m1_r2c2=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2`, `--step-tcl POST_MACRO_PLACE=physical/dsrom_edge_macro_snap.tcl`, `--orfs-corner WC --hold-corners WC,BC`, 0.833 ns, and 0.06 / 0.025 uncertainty. Use distinct nickname tags.
  - (a) `ot_dsrom_edge_lsel` with MACRO=1.
  - (b) `ot_dsrom_edge_hub` with MACRO=1.
  - (c) `ot_hdc_v41x_idx_score_slice_l` with NK=1: the hardened per-stack scorer slice, which replaces the 5.42 mm2 ESTIMATE.
- **Timing risks to screen.**
  - The merge2 loop at W=16. Fallback: W=8.
  - The lsel placement mux: 64 lanes x 16:1 by fill.
  - The macro clk->q is 455 ps SS. It is absorbed by the predicted-read register.

## Area ledger (statement, pending P&R)

- **S58 margin.**
  - Before: -2.42 mm2 (FAIL).
  - After: **+18.4 mm2**, from the pricing record, which charges the full 21.7 mm2 scorer at the shoreline (5.52 mm2 per stack).
- **Added by this RTL, per stack.**
  - The selector: 10 x 128x256 macros = 0.039 mm2, plus logic not yet measured. The tselect logic was priced at 0.072 mm2.
  - The hub: one tselect + 10 macros + merge, which replaces the removed pooled indexer (7.48 mm2).
- **Net.** The margin stays at about +18.2 mm2 pending the measured selector and hub areas. No figure here is P&R evidence yet.

## Codex execution milestone

- Baseline score pin `722c2d26c`: `score_roundrobin_722c2d26c.json`, all four stacks PASS; 15,082 keys checked, zero score/candidate errors. This completes the original score-array/local-selection functional path. Existing select history above remains unchanged.
- Opt-in `CONTIGUOUS=1` implementation pin `67d69cb75`: the same 84 functional queries in all three modes plus seven shipped queries PASS (`select_contiguous_67d69cb75.json`). Real-scaled 200K/1M tails are 412/366 cycles, versus 570/490; ascending 1M is 735 versus 745. HBM scan rate and zero stalls are unchanged.
- `ot_dsrom_edge_layout` preserves eight-key candidate blocks and maps both scanner positions and the new writer adapter. `ot_dsrom_edge_kwr` reuses the unchanged native encoder and packs code/scales into the native sector layout. Its descriptor stays held through backpressure. Faulted records are suppressed; `writer_map.json` checks held coordinates/payload, collisions, encoding faults and recovery.
- Layout extent is **frozen and installed**, not an automatically changing query length. `layout_installed` must come from the actual image owner after any required relocation. The system peer must enroll this descriptor/ACK and map compressed-KV coordinates coherently; this branch does not implement a migration engine or modify peer full-system sources. Include `rtl/dsrom_sys/ot_dsrom_edge_layout.sv` with the scorer source list.
- `tools/dsrom_edge_scorer_contribution.py` substitutes only matched AR L20 sizes into the unchanged S58 near-HBM graph. The graph already prices 324/350 cycles of composed selection depth at 200K/1M; 161 is only its added hub term. Measured contiguous versus measured round-robin L20 gives +0.037245%/+0.026773% AR. Other layers and simultaneous full-system timing remain unmeasured.
- Runtime dynamic dense repartition is **rejected**, default remains zero: boundary-changing appends relocate old dense local addresses. Index-only movement near 1M costs about 2.5–7.4 us at ideal aggregate HBM bandwidth; if compressed KV shares the new map, total payload movement alone costs 13–39 us, before quiescence/ACK/sector overhead. This outweighs the 0.103 us measured L20 select saving. See the migration lower-bound record and one-line verdict. No rescue or physical launch.
- Frozen-image contiguous mixed/context score campaign remains on PVE1: `/home/ubuntu/otjobs/dsrom-edge-score-67d69cb75`, clean snapshot `3af9f3d` of source `67d69cb75`, supervisor `2377338`; mixed then contexts200000/1048576 reuse one binary. No claim of its PASS before terminal collection. Original EPYC build and completed objects are preserved.

Replay the matched contribution and migration pricing:

```
python3 tools/dsrom_edge_scorer_contribution.py --old-select results/rtl/dsrom_edge_scorer_20261003/select.json --select results/rtl/dsrom_edge_scorer_20261003/select_contiguous_67d69cb75.json --out /tmp/edge-contribution.json --migration-out /tmp/edge-migration.json
```
