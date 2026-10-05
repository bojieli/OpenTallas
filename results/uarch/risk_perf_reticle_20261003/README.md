# Disaster-class risk checks: measured performance vs specification, and the Qwen ROM reticle fallback (2026-10-03)

This is model-only composition. Nothing was simulated or routed, no pinned file changed, and nothing is adopted. The records are `part_a_ledger.json` and `part_b_reticle.json`; their generators sit beside them, and the replay steps are in `REPLAY.md`.

## Part A: specified targets

| Combination | Written target | Where |
|---|---|---|
| Qwen3-8B ROM (TP-4 option C, AR, 8K) | **3,000 tok/s** (current conditional target) | `results/uarch/qwen_rom_calibrated_calendar_20261003/baseline-r1.json:873` (`bounds.target_3k_s`); `results/uarch/qwen_rom_kv_successor_20261002/model-r7.json:66`; `docs/MICROARCH_MODEL.md:132`; `docs/HEADLINE_BUNDLE_SCOPE.md:77` |
| | 11,325 tok/s (historical TP-2 budget for a superseded design) | `docs/ARCH_SPEC_QWEN3.md:90,95`; superseded at line 3 |
| DeepSeek-V4.1 ROM (1M) | **more than 3,000 accepted tok/s after MTP**, with AR reported separately | `TASKS.md:245` (also lines 46 and 91); `docs/CURRENT_WORK_HANDOFF_2026_10_03.md:24`; `results/uarch/ds_mtp_headline_budget_20261002/model.json:39` |
| | Spec requirement of 4,599 AR at 1M (4,837 at 200K); budget of 9,500 with MTP | `docs/ARCH_SPEC_V41.md:21-23,44,575` |
| Qwen3-8B HBM | **Not written** | — |
| DeepSeek-V4.1 HBM | **Not written** (`ARCH_SPEC_V41.md:24` gives budget results of 926 / 1,221, not a target) | — |
| ROM/HBM ratio | **Not written** anywhere in the binding documents. The Atlas ratios (12.3×, 7,049) are historical results. | — |

## Part A: ledger

All rates are per user at batch 1, in tok/s. Brackets are written LOW–HIGH.

| Combination | AR central [LOW–HIGH] | After speculation, central [LOW–HIGH] | Target | Verdict |
|---|---|---|---|---|
| Qwen ROM (with near-HBM attention) | **5,797** [4,572–5,862] | not the target mode. DSpark-b4 sensitivity: 8,278 [5,710–10,532] at +46 mm²/die | 3,000 AR | **MEETS**: +93% central, +52% LOW. Conditional on the reticle fit and the near-HBM physical closure. |
| Qwen ROM without near-HBM attention | 2,793 (KV-fill bound; the best service floor is 3,245) | — | 3,000 | **MISSES** by 7% |
| Qwen HBM | 880.5 [822–937] | DFlash b16 2,671 | none | — |
| DS ROM (C1, measured collectives) | **2,369** [1,784–2,371] | **3,172** at τ 3.649 [2,059 at τ 2.91 – 4,078 at τ 4.69] | >3,000 MTP | **AT RISK**: +5.7% central, −31% LOW. Break-even τ is 3.45. Misses the spec's 4,599 AR (0.52×). |
| DS HBM (W19 fused) | 2,261.7 [1,954–2,323] | 4,847 at τ 3.649 [3,340–6,329] | none | — |

How each row is composed:

- **Qwen ROM.**
  - Measured: the one-stream layer (3,930 cycles, of which body plus all-reduce is 3,843) and the head (2,998).
  - Near-HBM attention is 1,824 cycles a layer from RTL at R=8, with modelled HBM.
  - The streaming controller holds the modelled 0.9 TB/s (measured 0.958 TB/s), but only with the 261-cycle notice and REFpb.
  - LOW adds:
    - R=6 attention (2,022 cycles), in case R=8 area does not fit;
    - first-data latency and async CDC;
    - +92 wire cycles a layer, because every routed corridor span misses SS setup by 11–58 ps;
    - a 1.0 GHz clock.
- **DS ROM.**
  - Basis: C1 at 2,356.8 AR (measured collectives).
  - Charged on top:
    - the real DSpark draft (0.117 × AR, not 0.075);
    - q-element pipelining at L=2 (−0.09% AR);
    - the measured CDC successor credit (+0.6%).
  - LOW adds:
    - the same-x phase-merge emitter gap (+73 µs on AR and on the MTP step);
    - one chunk-8 recurrence cycle (−0.65% AR / −1.66% MTP), because the zero-latency q-element fix failed by 316–437 ps;
    - 1.0 / 0.75 GHz clocks (+60 µs).
  - RTL-as-built floor: adding the three further model-assumed fusions the RTL lacks gives 1,526 AR and 2,420 MTP at τ 3.649.
- **DS HBM.** LOW is the unfused composition plus the clock and HBM derate on the non-collective part. HIGH is the H5 TMEM epilogue.

Comparator ratios under the same brackets:

| Ratio | Central [LOW–HIGH] |
|---|---|
| Qwen ROM AR / HBM AR | 6.6× [4.9–7.1] |
| Qwen ROM AR / HBM DFlash | 2.2× [1.6–2.4] |
| DS ROM AR / HBM AR | 1.05× [0.77–1.21] |
| DS ROM MTP / HBM MTP, same τ | **0.65× [0.52–0.76]** |

Two caveats on these ratios:

- The Qwen ROM row spans two packages and 16 stacks, while the HBM row is one 8-stack package. At equal package count the Qwen ratios roughly halve.
- On DeepSeek the HBM comparator beats the ROM after MTP. The ROM's MTP step (1,150 µs) is 2.7× its AR token, because the 6 verify positions issue ×6 on the stationary field. The HBM verify step is only 1.7× its AR token.

Levers if DS ROM misses:

1. Land the class-A phase-merge emitter option. It needs zero area and is already measured bit-exact. Follow it with a runtime layer A/B.
2. Cut the ROM verify step. A multi-column (m=2) field element, or verify-only lane doubling, is the only lever that changes the ROM/HBM MTP ratio.
3. Bind a qualified agentic τ. The pilot median of 4.69 gives 4,076.

## Part B: Qwen ROM reticle-fit fallback

**Area against corridor routable ratio.** This uses the gate tool's own `die_statement`, which is the r2 `build_frame` unchanged. All corridors are at the same density d; the "tile column only" thresholds are in `part_b_reticle.json`.

| d | 0.20 | 0.225 | 0.25 | 0.28 | 0.30 | 0.33 | 0.36 | 0.40 | ≥0.43 |
|---|---|---|---|---|---|---|---|---|---|
| Die (mm²) | 931.4 | 902.5 | 878.7 | 856.8 | 844.0 | 828.2 | 815.3 | 801.5 | 792.0 |
| Fits 26 × 33 mm | no | no | no | no (W 26.06) | yes | yes | yes | yes | yes |

- The 26 mm **width** binds first, at d ≥ 0.283. The 858 mm² area limit is reached at d = 0.277, and the 815 mm² HC1 budget at d = 0.362.
- At 0.225 the die fails on width (27.4 mm), not only on area.

**Gate status.** The records are uncommitted; `summary` has not been run.

- The tile column with a centred pin row (C) routes clean at r2 (0.43).
- The link span routes clean at 0.50.
- The one-sided pin row (B) overflows at 0.43 but is clean at 0.30.
- The C and B runs at 0.50/0.60 failed placement because the 8.64 µm station slab is too small. The D series is running.
- The 0.225 premise came from a GRT-only run on M4/M6/M8 and is superseded. The live risk is timing: every span misses SS setup by 11 to 58 ps.

**Fallbacks** that cut tile-column demand from 637 bits. The die figure is the area at gate density 0.225.

| ID | Change | Demand | Fits 815 at gate density ≥ | Fits 26 mm at ≥ | Die at 0.225 (mm²) | Latency | Re-qualification |
|---|---|---|---|---|---|---|---|
| F1 | One pipelined reset wire with per-tile synchronisers | 574 | 0.328 | 0.257 | 880.6 | 0 | Column reset/drain bench, column STA |
| F2 | 379-bit instruction sent as 2:1 beats into a 2-deep column FIFO (the schedule is static) | 448 | 0.263 | 0.203 | 838.8 | 0 to 296 cycles (≤ 0.14%) | Default-off param; exact gate with the stream identical; layer A/B; corridor gate re-run |
| F3 | Column pairs share one corridor, with instruction, clock and reset carried once per pair | 383.5 | 0.229 | 0.175 | 817.8 | 0 | Mirrored tile abstract and two-sided taps, which is where B overflowed |
| F4 | M5 added for latency-tolerant nets (upper bound) | 637 at ×1.74 tracks | 0.220 | 0.168 | 811.4 | 0 | Corridor gate with M5; only credible together with F2 |
| **F1+F2** | **Recommended** | **385** | **0.230** | **0.176** | 817.8 | ≤ 0.14% | Single-column, class A, no change to tile, slot or hub |
| F1+F2+F4 | Reserve | 385 at ×1.74 | 0.144 | 0.107 | 800.5 | ≤ 0.14% | As above |
| F7 | TP-8 over 4 packages | — | any | any | ~480 | +10.2 µs (~5,470 tok/s) | Everything: images, all-reduce, floorplan |

Narrow links (888 mm², +10.1 µs) and hub relocation or M8/M9 trees are rejected as area levers. The tile-column corridors hold about 105 mm²; the links and spine add only 8.5 mm² even at 0.225.

**Fallback to adopt immediately if the gate reports below about 0.36: F1+F2.**

- What it changes:
  - one pipelined reset wire;
  - the 379-bit instruction bus time-multiplexed 2:1 into a 2-deep per-column FIFO.
- Demand falls by 40%, from 637 to 385 bits. The die then fits 815 mm² down to a gate density of 0.23, and the 26 mm outline down to 0.176.
- Cost: at most 296 cycles a token, which is zero once the FIFO prefetches.
- It needs no change to the tile abstract, slot or hub. It is class A and default-off.
- Keep the centred pin row (C).
- If the gate lands below 0.23, add F4 (M5), then F3, and only then F7.
