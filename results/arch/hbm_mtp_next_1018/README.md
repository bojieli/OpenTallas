# HBM-MTP deliverable 1: tok/s against P lanes against added die area (2026-10-18)

This is a design study. It sits outside the release closure: the d4g GEN2 die and its kits are untouched. It composes three branches: claude/hbm-mtp-stats-1018@c26488f3c, claude/hbm-mtp-model-1018@c3a96760b, claude/hbm-mtp-area-1018@edc5b8dfa.

The added area is measured. It covers the SM leaf block-dot lanes, the BF16-column lanes and a replicated x store, synthesised on the fleet in `sm_area/`, plus the model's estimates for the units outside the SM. The tok/s figures come from the compiler timing model in `model/`, timed with the measured expert-union statistics from `stats/`. The current die is 641.83 mm².

| P | +mm² | die mm² | +mm² (bdc-only variant) | DS AR | **DS MTP** | DS MTP kv-lower / union-p90 | DS users agg | Qwen AR | Qwen DFlash b16 pub / meas | Qwen users agg | DS MTP tok/s per die mm² |
|---:|---:|---:|---:|---:|---:|---|---:|---:|---|---:|---:|
| 1 | 0.0 | 641.8 | 0.0 | 1905.4 | **1694.3** |  /  | 1905.4 | 946.2 | 459.5 / 209.7 | 946.2 | 2.64 |
| 2 | 34.56 | 676.4 | 16.58 | 1905.4 | **3142.8** | 3288.8 / 3063.1 | 3060.3 | 946.2 | 874.3 / 399.1 | 1734.2 | 4.646 |
| 4 | 101.11 | 742.9 | 47.2 | 1905.4 | **3363.5** | 3597.8 / 3272.3 | 4365.3 | 946.2 | 1465.9 / 669.1 | 2971.4 | 4.527 |
| 6 | 167.64 | 809.5 | 77.79 | 1905.4 | **3519.3** | 3841.7 / 3419.6 | 5153.7 | 946.2 | 1758.1 / 802.5 | 3898.6 | 4.348 |
| 8 | 234.51 | 876.3 | 108.72 | 1905.4 | **3519.3** | 3841.7 / 3419.6 | 5710.4 | 946.2 | 2442.8 / 1115.0 | 4619.2 | 4.016 |

## Where the knee is

- **DeepSeek single-user MTP: the knee is at P=2.** Throughput goes from 1694 to 3143 tok/s (+86%) for +34.6 mm² (+5.4% of the die). P=4 adds only +7% more and P=6 +12% more, for +101 mm² and +168 mm². P=8 is the same as P=6 for DS, because there is no gamma-7 drafter.
- **Qwen DFlash and multi-user aggregate keep rising up to P=8.** DFlash b16 (published tau 8.01) is 0.92/1.55/1.86/2.58 x AR at P=2/4/6/8; with our measured tau 3.656 it reaches AR only at P=8 (1,115 tok/s, 1.18x). These rows were corrected on 10-18 (see below). Throughput per die mm² peaks at P=2 (4.65 against 2.64 at P=1).
- **Cheaper variant: give P lanes to the FP8/FP4 block-dot only.** At P=6 that costs about 78 mm² instead of 168. It gives up the multi-query attention lanes in the BF16 column (the ATT feature saves 189k verify cycles at P=6). This variant was not re-timed.

## Qwen DFlash check (10-18, lane HBM-MTP-QCHK)

The first table had DFlash +2% from P=4 to P=6, then +41% at P=8. That was a modelling error, now fixed in `tools/hgi_sim/hbm_plane_model.py`:

1. **Weight passes.** The DFlash programme was always emitted in the as-built records: 8 slots per SM record and 4 slots per LM-head pass. The P-lane rule then charged ceil(8/P) line passes per record. So P=4 and P=6 both paid 4 weight passes for the 16 positions (P=6 should pay 3), and every head paid 4 passes at any P. Now the compiler picks the record size R from {P, 2P, 8, 16} (the SM slot field is widened to 4 bits, per the change list). It also picks the head pass PH from {16, 8, 6, 4}: the largest that fits the P-lane VM. Chosen (R, PH): P=2 (8,4), P=4 (8,6), P=6 (12,8), P=8 (16,8).
2. **Attention merging.** The attention group index was read from the tag `.g<s0>`, which holds the first *slot* (0/4/8/12). So no passes merged at P=2/4, and the wrong groups merged at P=6/8. The index is now slot / 4.

Checks that hold:

- **Draft cost.** The drafter is charged per pass (its weights are re-read for each pass), not per position. At P=8 it costs about 0.28M cycles.
- **Verify passes.** At P=8 the verify reads the weights in 1.745M cycles, exactly 2 x AR's 0.898M.
- **Prices.** AR and DFlash go through the same d4g cost chain. P=1 reproduces the earlier step.
- **MoE union.** None: Qwen is dense.

**Why DFlash is not far above AR.** At P=8 one 16-position step takes 3.93M cycles, which is 3.10 AR steps. The parts:

| cost | cycles |
|---|---:|
| target weights, 2 passes | 1.75M |
| drafter | 0.28M |
| LM heads (15 draft + 16 verify slots, 4 passes) | 0.31M |

The rest is per-position work that P lanes do not amortise:

| per-position cost | DFlash | AR |
|---|---:|---:|
| tensor-parallel all-reduce, 16 x H payload | 0.46M | 0.10M |
| softmax over 8K scores x 16 slots | 0.36M | 0.04M |
| attention | 0.23M | 0.09M |
| norms | 0.17M | 0.01M |

The all-reduce price (64 B/cycle serialisation) is an estimate, and the largest per-position term. Step / AR at P=1/2/4/6/8 is 16.5/8.67/5.17/4.31/3.10. So DFlash beats AR from P=4 with the published tau, but needs P=8 with our measured tau 3.656.

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
