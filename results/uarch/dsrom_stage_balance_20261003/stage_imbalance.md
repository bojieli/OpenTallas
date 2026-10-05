# DeepSeek-V4.1 ROM array: stage imbalance, root cause and fixes

Review date 2026-10-03. This is a model-only review: no RTL or P&R was run.

- **Basis.** `tools/uarch_model.py` (sha256 2da5b6d9…) at origin/main 103d3ec89, run read-only in `/home/ubuntu/dsrom-stage-balance-20261003`.
- **Settings.** The S58 selection's pricing settings, from `tools/dsrom_4096_partition_token_options.py`.
  - The model reproduces AR at 390.06 µs for 1M context and 373.05 µs for 200K.
- **Numbers.** Machine-readable figures are in `stage_imbalance.json`. The scripts are `probe.py` and `options.py`; per-variant output is in `opt_*.json`.
- **PAR2.** The model has no PAR2 term. Every figure here is per die of the TP-4 group.
- **Stage numbering.** "Stage 14" in older records is the S28 numbering. At S58, layer 20 sits on **stage 29** (0.667 of layer 20 plus 0.022 of layer 19).

## 1. What "the layer 20 scan" is

- **The layer itself.** Layer 20 is the only `csa2-1-full` layer (`configs/models/candidates/deepseek-v4.1-flash.json:433-441`). It has:
  - compression ratio 1;
  - KV-owner status;
  - an index scan with `index_scan_entries_cap = 0`, so it scores **every** context position;
  - the `candidate_source_layer_id` role (:757). It also produces the top-2048 block candidates that the reindex layers 24/28/32/36 use.
- **Comparison layers.**
  - Layers 2, 8 and 14 (`csa2-2-full`) also scan uncapped, but over ctx/2.
  - Reindex layers are capped at 16,384 entries (:474-594).
  - Every other layer reuses an index.
- **Operator chain.** The chain is `idx.score` → `idx.topk_local` (ot_hdc_tselect, top-512) → `topk_merge` (4×512 all-gather) → `topk_final`, plus `cand.topk_local` (`decode_critical_path.py:1103-1135`, `arch_budget_v41.py:241-245, 295`).
- **What dominates the time: HBM bandwidth.**
  - Each die reads 262,144 keys × 68 B = 17.8 MB per token.
  - At 4 stacks × 0.9 TB/s that takes **4.95 µs**. The compute floor is 3.41 µs (`uarch_model.py:352-361`, `arch_budget_v41.py:137-139`).
  - The top-k then adds a **serial** 3.41 µs ingest of 4,096 beats.
  - The node is built with `stream=False` (`decode_critical_path.py:276, 843-848`), although its own docstring (816-819) says the scorer chases it.
- **Why it depends on context.** Both terms are linear in context.
  - The four uncapped scans explain **17.02 µs of the 17.01 µs** AR difference between 1M and 200K: all of the token's context sensitivity.
  - The ratio of the layer-20 stage to the mean stage is 5.2× at 1M and 2.3× at 200K.
- **MoE does not cause it.** Expert issue is only 0.27 µs per die per layer, because only 6 of 384 experts are active.

## 2. Per-stage time (occupancy per die, µs)

| | 1M | 200K |
|---|---:|---:|
| Layer-stage mean / std | 2.23 / 2.04 | 1.93 / 1.22 |
| Max (stage 29, L20) | **11.57** (5.2× mean) | 4.46 (2.3×) |
| Next: stage 20 (L13–14), 11 (L7–8), 2 (L1–2) | 7.51, 7.01, 7.00 | 4.13, 3.62, 3.62 |
| Then stage 1, then the non-scan stages | 2.84, then ≤ 2.72 | 2.84, then ≤ 2.72 |
| **Head stage (lm_head, 4-way)** | **12.37, which binds saturation** | **12.37, which binds** |

The full 58-stage table is in the JSON under `stage_tables`. It has occupancy, critical-path window and resources for each stage.

## 3. Effect

**(a) Single-user latency: none from the imbalance itself.**
- The batch-1 token is the sum of the stage windows (390.07 against 390.06 µs). Layer 20's chain is serial wherever its stage boundaries fall.
- What costs latency is the scan itself. The four scans take **27.6 µs of the 1M token (7.1 %)**; layer 20 alone takes 9.17 µs (2.4 %). At 200K they take 10.6 µs.

**(b) Throughput.**
- Saturation is 80,833 tok/s. It is bound by the **head** stage (12.37 µs), not by stage 29 (11.57 µs).
- Rebalancing layer stages therefore gives 0 % at S58 until lm_head is split 8 ways.
- `n_head = 8` is already provisioned, but the vocabulary is split only 4 ways (`decode_critical_path.py:1048`).

**(c) Power.**
- The model's published "busiest" figure (189.0 W at 1M, 203.6 W at 200K) is the **head** stage. `_cons_cooling` (`uarch_model.py:3713-3722`) takes the maximum over all stages, including the head.
- The hottest *layer* die is stage 29:
  - **204.4 W at 1M**, against a mean (and balanced) 95.7 W;
  - 131.8 W at 200K, against 95.2 W.
- This is per die without PAR2. All of these are below the 474.6 W limit.

## 4. Fix options, priced (AR and MTP change against the current design)

| Option | Dies | Single-user? | AR 1M | MTP 1M | AR 200K | MTP 200K | Layer-stage max 1M | Hottest layer die 1M |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Cut by time / own stage for L20 | +0 / +4 (+8 PAR2) | No (+0.40 µs per added hop) | 0 | 0 | 0 | 0 | 11.39 floor | ≈ same |
| Replicate stage 29 | +4 (+8) | No | 0 | 0 | 0 | 0 | 7.51 (stage 20 next) | 166 W |
| More indexer MACs or tselect lanes | area | No (HBM-bound) | ≈ 0 | — | — | — | — | — |
| **Chase** (tselect on the scorer stream) | 0 | **Yes** | **+2.31 %** | **+5.82 %** | +0.41 % | +1.24 % | 11.57 | 204 W |
| CP-8, L20 only (PAR2 pair) | 0* | Yes | +1.06 % | +2.21 % | +0.19 % | +0.44 % | 7.51 | 166 W |
| CP-8, L2/8/14/20, +200 ns | 0* | Yes | +2.43 % | +5.59 % | +0.12 % | +0.99 % | 7.17 | 163 W |
| **Chase + CP-8 on all four scans, +200 ns** | **0*** | **Yes** | **+3.66 %** (376.28 µs) | **+8.80 %** | +0.35 % | +1.68 % | 7.17 | 163 W |
| CP-16 (adds the next stage's pair), +200 ns | 0 | Yes | +3.68 % | +8.62 % | +0.13 % | +1.49 % | 4.98 | 139 W |
| Chase + CP-16, +500 ns | 0 | Yes | +3.95 % | +10.18 % | −0.02 % | +1.73 % | 4.98 | 139 W |

\* This assumes each PAR2 die keeps its own indexer and 4 HBM stacks (the fixed services are replicated: model-r4.json:329), with the scan layer's index keys striped over all 8 dies.

**Exactness (class A).**
- Scores are computed per key.
- The local top-512 lists are concatenated in position order into one `tselect_final`, which is the two-level form already verified in RTL.
- The golden's tie order is kept.

**Why time-cutting cannot work.**
- Layer 20's non-expert block, 11.39 µs at 1M, is indivisible on its stage. No cut gets the stage below that floor; the gain is −1.6 %.
- Equal bytes is already roughly equal expert count. The imbalance comes from one operator, not from where the cut falls.

**Caveat on stage occupancy.**
- The model's stage occupancy sums issue over every unit on the die.
- If the indexer HBM reader, tselect and field serve different users concurrently, stage 29's interval would be 4.95 µs, not 11.57.

## Recommendation

- **First, chase:** zero hardware, +2.3 % AR and +5.8 % MTP at 1M.
- **Then context-parallel the four uncapped scans over the PAR2 pair:** +3.7 % AR and +8.8 % MTP combined at 1M, with 0 dies. This also brings the hottest layer die from 204 W to 163 W.
- **Hand-off to the parallelism study:**
  - Split lm_head 8 ways. Without it, no layer-stage fix raises saturation above 80.8k tok/s.
  - Price the PAR2 merge crossing.

**Gates before adoption:**
- the chase measured in RTL;
- key placement over the PAR2 HBM;
- the 8-way merge exact against the golden;
- the AGENTS.md ≥ 1 % lever rule. At 200K, the AR gain is only 0.35 %.
