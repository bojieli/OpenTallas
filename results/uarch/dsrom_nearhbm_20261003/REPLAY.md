# DeepSeek-V4.1 ROM: does a near-HBM index scan or near-HBM attention help?

This is model-only pricing. No RTL or P&R was run, nothing is adopted, and `tools/uarch_model.py` and every pinned record are untouched.

- **Basis.** The S58 product of the unified model: `cons_v41_rom`, with the S58 selection's settings. It reproduces AR 390.06 µs / MTP 3,809.4 tok/s at 1M and 373.05 µs / 4,176.7 tok/s at 200K.
- **Unit.** Figures are per logical die of the TP-4 group, which has 4 HBM3E stacks at 0.9 TB/s sustained each, 3.6 TB/s in total (3,000 B/cycle at 1.2 GHz).
- **Method.** Each variant is a surgery on the priced graph made before `_cons_adjust`, applied to both the AR pass and the DSpark verify pass (6 positions, τ 3.649).
- **Data.** Everything is in `model.json`.

## Replay

```
python3 tools/dsrom_nearhbm.py            # ~1.5 min on 12 processes; asserts the S58 baseline first
python3 tools/dsrom_nearhbm.py --check    # recompute; refuse if model.json differs
python3 -m pytest -q tests/test_dsrom_nearhbm.py
```

## Q1. How data moves today, and what binds

**The path.**
- HBM service strips sit at the north and south edges: 4 bands, each 8,500 × 216 µm, all placeholders.
- They feed one central hub, which holds the indexer (16 NK=4 score slices, 64 keys/cycle) and the attention tiles.
- The W18 routed die carries three buses:
  - `idx_keys`: 4 × 4,096 b, which is **2,048 B/cycle (2.46 TB/s)**. It is sized to the behavioural reader's 60.04 sectors/cycle, not to the HBM. It crosses 27–45 stages (39 on the 669 mm² die).
  - `hbm_window`: 4 × 256 b = 128 B/cycle.
  - `selected_kv`: 32-bit ID requests only. The selected-row return path is not a routed bus.
- The model prices the scan at the 3.6 TB/s aggregate and charges none of these crossings.

**Bytes per die per token, and time.**

| | 1M | 200K |
|---|---:|---:|
| (a) index scan, L20 die | 17.83 MB | 3.40 MB |
| L20 at the HBM aggregate / at the routed key bus / at the measured reader | 4.95 / 7.25 / 7.73 µs | 0.94 / 1.38 / 1.48 µs |
| scan, summed over the 8 scanning layers' dies | 45.7 MB = 12.7 µs at HBM | 9.6 MB = 2.7 µs |
| (b) selected + window rows, per layer die (each MTP position reads its own) | 53,760 B: 0.015 µs at HBM; 0.35 µs on `hbm_window` | same |
| (c) KV writes, per token per group | 22.5 KB: 1.6 ns | same |

**Critical-path exposure (AR, µs).**

| | 1M | 200K |
|---|---:|---:|
| scan read | 13.76 | 3.74 |
| serial top-k (not chased) | 9.81 | 2.82 |
| scan + top-k as a share of the token | 6.0% | 1.8% |
| selected-KV HBM latency (8 × 250 ns) | 2.03 | 2.03 |
| **cross-die** row all-gather | 8.04 | 8.04 |
| attention compute | 41.1 | 41.1 |

**Verdict.**
- In the model, HBM binds the scan.
- As routed, the key bus is 68% of the HBM rate, so the on-die path binds. That exposes **+5.90 µs at 1M (−1.49% AR)** and +1.24 µs at 200K (−0.33%). MTP is unaffected (−0.05%), because the verify scan is MAC-bound (6 positions on 64 keys/cycle).
- KV rows and writes are not bandwidth-bound. Their cost is latency plus the cross-die all-gather, which is not an on-die path.
- **This is not Qwen's problem.**
  - Qwen streams all KV through a 537.6 GB/s fill network, 7× below its HBM.
  - V4.1 reads only 640 rows per layer. Its one context-linear stream, the scan, falls short of the HBM rate by just 1.5×, and it does so on 4 of 58 stages.

## Q2. The priced variants (% per-user rate against the S58 model; Δ against C5hc-style CP-8 in the lower block)

| variant | 1M AR | 1M MTP | 200K AR | 200K MTP |
|---|---:|---:|---:|---:|
| base, routed key bus (as floorplanned) | −1.49 | −0.05 | −0.33 | −0.01 |
| chase (stage-balance; no per-die merge charged) | +2.31 | +5.82 | +0.41 | +1.24 |
| central stack-major select + chase (4 local top-512 + per-die merge) | +2.02 | +5.74 | +0.22 | +1.17 |
| **(i) near-HBM scan, per-stack top-512** | **+2.02** | **+5.74** | **+0.22** | **+1.17** |
| (ii) near-HBM attention, exact form | −0.41 | −0.18 | −0.43 | −0.20 |
| (iii) both | +1.59 | +5.54 | −0.21 | +0.97 |
| CP-8 (4 scans, +200 ns merge) | +2.43 | +5.59 | +0.12 | +0.99 |
| CP-8 + chase | +3.66 | +8.80 | +0.35 | +1.68 |
| CP-8 + (i) | +3.37 | +8.72 | +0.12 | +1.60 |
| CP-8 + (iii) | +2.93 | +8.51 | −0.30 | +1.40 |

**(i) Near-HBM index scan.**
- **Latency.** It prices **identically to the same stack-major select placed centrally** (Δ 0.000%). Proximity buys no latency. The scan is HBM-bound either way, and the q fan-out of 39 stages replaces the key crossing of 39 stages.
- **Where its gain comes from.**
  - Against the as-floorplanned bus it gains **+3.56% AR / +5.79% MTP at 1M**: 1.5 points from reaching the HBM rate and the rest from chasing.
  - Against chase plus a bus widened to the HBM rate it gains **0** (−0.28% for the per-die merge level that chase alone omits).
- **Exactness: class A.**
  - Scores are key-local.
  - The per-stack top-512 lists are concatenated in position order and reduced by one final top-512 that keeps the lower index on ties. This is the stack-major proof in `results/rtl/v41_idx_stack_major_ingest.json`.
  - Candidate blocks of 8 stay inside one stack under the 16-key round-robin.

**(ii) Near-HBM attention is not exact beyond q·k.**
- The golden's P×V is one sequential sum over all 640 rows from +0. Its denominator is the 8-way interleaved `reduce_rows`, taken after a single max.
- Per-stack partials with an (m, l, acc) merge are therefore class C. The parallelism study rejected CP attention for the same reason.
- Because K = V (MLA rows), the exact form still moves every row to the hub, and it adds q-out and score-back crossings: −0.41%.
- The rows are 15 ns of HBM time per layer. What dominates the selected-KV path is the cross-die all-gather (8.0 µs), and near-HBM placement cannot remove it.

**Physical cost of (i).**
- **Area.**
  - The 21.7 mm² scorer (ESTIMATE; no hardened slice) and its four selectors move to the shoreline. That is 5.52 mm² per stack, a strip about 460 µm deep behind a 12 mm PHY, or 649 µm on the 8.5 mm W18 strip.
  - The hub loses the raw-key route bands (33.2 mm², including the +3.08 mm² native correction), the collector band (2.19 mm²) and the pooled indexer (7.48 mm²).
  - The S58 capacity margin goes from **−2.42 mm² (FAIL)** to **+18.4 mm²**, charging the full scorer at the shoreline.
  - Central at the model's full scorer width would be −16.6 mm².
- **Tracks.** It removes 42,752 native S58 band tracks (35,712 response + 7,040 request), or 16,384 routed W18 key wires. It adds 32 candidate wires per stack plus a q load (17,920 b per slice, once per scan).
- **Power.**
  - On-die key wire energy is 0.255 mJ per token on the L20 die (0.1 pJ/b/mm ASSUMED, mean 17.9 mm). That is 20.6 W at the 80.8k tok/s saturation, and the model does not charge it today.
  - The shoreline power density (upper bound, ungated clock) is:

    | region | W/mm² |
    |---|---:|
    | scorer band, AR | 0.46 |
    | scorer band, MTP | 0.58 |
    | PHY | 0.58 |
    | PHY + scorer | 0.58 |

  - All of these **PASS** both the 2.0 nominal and the 1.0 conservative HIR limits.

**Interaction with C5hc CP-8.**
- **They compose.** CP-8 halves the keys per die, and near-HBM terminates each die's keys at its own stacks. CP-8 + (i) is +3.37% / +8.72% at 1M.
- **They overlap on latency.**
  - CP-8's gain comes from bytes and from chase.
  - (i) adds nothing over CP-8 + chase (−0.29%).
  - Against CP-8 on the routed bus, (i) adds +1.72% AR / +2.99% MTP.

## Q3. Verdict

- **(ii) and (iii): do not adopt.** Exact near-HBM attention gains nothing (−0.4%), and the variant that would gain is not bit-exact.
- **(i): it does not improve latency beyond what central placement achieves.** Price it as a floorplan choice, not a rate lever.
  - For the ≥1% rate lever, adopt **chase + CP-8** (C5hc).
  - Build the key path at the full HBM rate. As floorplanned it leaves 1.5% AR at 1M.
- **(i) is the cheaper way to build that full-rate path.** It turns the S58 corridor FAIL (−2.42 mm²) into a +18 mm² margin. It also removes 35.7k response tracks and about 20 W of unpriced key-wire power on the L20 die.
- **Recommendation.** Hand (i) to the floorplan owner as the scan-path placement, using the stack-major RTL that already exists, and gate it on:
  - a hardened score slice;
  - per-stack ingest at 0.9 TB/s;
  - a closure check of the shoreline strip at SS/FF.
