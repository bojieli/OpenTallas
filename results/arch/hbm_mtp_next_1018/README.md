# HBM-MTP deliverable 1: tok/s against P lanes against added die area (2026-10-18)

This is a design study. It sits outside the release closure: the d4g GEN2 die and its kits are untouched. It composes three branches: claude/hbm-mtp-stats-1018@c26488f3c, claude/hbm-mtp-model-1018@c3a96760b, claude/hbm-mtp-area-1018@edc5b8dfa.

The added area is measured. It covers the SM leaf block-dot lanes, the BF16-column lanes and a replicated x store, synthesised on the fleet in `sm_area/`, plus the model's estimates for the units outside the SM. The tok/s figures come from the compiler timing model in `model/`, timed with the measured expert-union statistics from `stats/`. The current die is 641.83 mm².

| P | +mm² | die mm² | +mm² (bdc-only variant) | DS AR | **DS MTP** | DS MTP kv-lower / union-p90 | DS users agg | Qwen AR | Qwen DFlash b16 pub / meas | Qwen users agg | DS MTP tok/s per die mm² |
|---:|---:|---:|---:|---:|---:|---|---:|---:|---|---:|---:|
| 1 | 0.0 | 641.8 | 0.0 | 1905.4 | **1694.3** |  /  | 1905.4 | 946.2 | 459.5 / 209.7 | 946.2 | 2.64 |
| 2 | 34.56 | 676.4 | 16.58 | 1905.4 | **3142.8** | 3288.8 / 3063.1 | 3060.3 | 946.2 | 864.7 / 394.7 | 1734.2 | 4.646 |
| 4 | 101.11 | 742.9 | 47.2 | 1905.4 | **3363.5** | 3597.8 / 3272.3 | 4365.3 | 946.2 | 1460.0 / 666.4 | 2971.4 | 4.527 |
| 6 | 167.64 | 809.5 | 77.79 | 1905.4 | **3519.3** | 3841.7 / 3419.6 | 5153.7 | 946.2 | 1487.4 / 678.9 | 3898.6 | 4.348 |
| 8 | 234.51 | 876.3 | 108.72 | 1905.4 | **3519.3** | 3841.7 / 3419.6 | 5710.4 | 946.2 | 2101.9 / 959.4 | 4619.2 | 4.016 |

## Where the knee is

- **DeepSeek single-user MTP: the knee is at P=2.** Throughput goes from 1694 to 3143 tok/s (+86%) for +34.6 mm² (+5.4% of the die). P=4 adds only +7% more and P=6 +12% more, for +101 mm² and +168 mm². P=8 is the same as P=6 for DS, because there is no gamma-7 drafter.
- **Qwen DFlash and multi-user aggregate keep rising up to P=8.** Throughput per die mm² peaks at P=2 (4.65 against 2.64 at P=1).
- **Cheaper variant: give P lanes to the FP8/FP4 block-dot only.** At P=6 that costs about 78 mm² instead of 168. It gives up the multi-query attention lanes in the BF16 column (the ATT feature saves 189k verify cycles at P=6). This variant was not re-timed.

## Area at P=6 (mm²)

- block-dot lanes: 36.66
- BF16-column lanes (linear estimate): 89.85
- x store: 39.85
- units outside the SM (estimate): 1.278

Each added block-dot lane costs 6,404 µm² and 8,668 flops, which is 0.89 of a column; each added BF16-column lane costs 15,700 µm². Both are linear in P. Every lane matches the production column bit for bit on Verilator 5.050 at P=1 to 8 (see `sm_area/README.md`).

## RTL change list by unit (from `model/`; verify cycles saved per step at P=6)

| unit | owner | change | cycles saved |
|---|---|---|---:|
| SM | H-SM | P accumulator lanes per MAC column: each HBM weight word / BDC line broadcast to P lanes (P x MAC, same 99 B/cycle/SM HBM share, SMEM and VM ports); SM.MATVEC slot field (HGI-1 spec 6.7 param [4:2] = N - 1, widen to 4 b for N <= 16) + per-slot x base; P x-slot stores; per-lane result publish (slot-major) | 554112.8 |
| ATT | H-SM (SM attention) | KV-line-stationary multi-query attention: P query slots a SM engine, each KV line streamed once and applied to the lanes whose top-k mask selects it (per-line lane mask from the N IDX top-k lists + window rule), per-lane QK / PV accumulators, fixed spans (first access, dispatch, publish, cross-SM merge) once a record | 189092.8 |
| FUSED | H-SU (FUSED) | FUSED.HC_PRE_NORM / HC_POST row field N on the LL lanes: gain sectors kept across rows, two r slots (row p+1 phase A over row p's tail), per-row scalar set; MEASURED II 197 (P6 RTL) | 201983.3 |
| HC | H-SU (HC) | HC.HC_MIX N rows streamed against stationary mix weights (HCP x6 mode II 250) + Sinkhorn x 3 units (II 634 / 3) | 284081.6 |
| COLL | H-COLL | COLL ROW_GATHER / TOPK_MERGE / kv gather / ARGMAX_MERGE take N rows (one message train, endpoint / crossing / tail once); shared ALL_GATHER / GROUP_REDUCE_MCAST carry N x payload; ring AG flits x N (d4g adders unchanged per record) | 163834.0 |
| IDX | H-IDX | IDX.INDEX N queries over ONE key stream (N x 4,096-word query store), IDX.TOPK heap row reset, verify expert-UNION record (384-b union bitmap, per-expert lane lists for the grouped GEMM) | 63743.0 |
| SU_DMA | H-SU / H-DIE / H-IDX | row counters in SU.VOP (indexed + un-indexed), SFU chains, DMA.KVWB_DS (N rows, window ring 256 slots: +128 HBM rows a layer), position-addressed DMA.LOAD rows, FUSED.QDQ, ARGMAX.LOCAL | 38732.0 |
| VM | H-DIE | VM capacity: N resident verify / user columns (h + PRE): + (N - 1) x ~30k words (N = 6: ~+150k words, VM 2^18 -> ~2^18.9; 4 quadrant slices); else per-layer column swaps | 37139.7 |
| ISA | H-ISA | record header row count N (all units) + per-row descriptor stride; CTL.TOKX (k completion beats, SPEC_GAP Q-MTP-1) | None |
| DRAFT | H-MTP | DSpark draft on the same die: dsa / dsb / dhead as R = 5-row records (no new unit), SEED of the next step scheduled with the verify head (joint S2 schedule), Markov / demb serial | None |

## Still open

- tcc (BF16 column) P=6/8 syntheses still running (linear estimate used; P<=4 exactly linear)
- KV top-512 position overlap unmeasured (headline = upper bound; kv-lower bracket shown)
- HBM capacity for P users x 1M KV not checked
- non-SM unit area = model item estimates, not synthesised
- timing: synthesis-only; broadcast fan-out needs a registered per-lane-group tree (+1 cycle at P>=4)

**Owner decision:** choose P, and whether the BF16 column gets lanes, before the D2 RTL. Records: `summary.json`, `area_composed.json`, `model/`, `sm_area/`, `stats/`.
