# Qwen3-8B ROM TP4: the all-reduce as one stream (pricing, 2026-10-03)

The user decided on 2026-10-03 that the whole 4,096-element all-reduce vector goes as one stream. The data is in `pricing.json`. The measured inputs are the Verilator gate `vg1_verdict.json` and the L0 itrace a17a3c79.

## Why each all-reduce is two segments
- **The cause is program segmentation, nothing else.**
  - `split_collectives` in `tools/hdc_qwen_fullshape_program*.py` (AR_WORDS default 128) cuts each 256-word all-reduce into two TP descriptors.
  - The reason is that the 8-bit descriptor count cannot encode 256.
  - Segment B is a lone END word.
- **The sequencer serialises the two halves.** It runs one descriptor at a time: S_COLL leaves only after the last reduced word comes back. Each half therefore pays the full link fill and drain.
- **Ruled out:**
  - SU width;
  - FIFO DEPTH, which is 1,024 and so at least 256;
  - credits, with 0 link stalls measured;
  - a hub step.
- **The fix is already in source, default-off, and has never been measured on the runtime:**
  - `ot_qwen_tp_seq_w12` with `ENABLE_AR256` decodes count 0 as 256;
  - the generator emits it with `QWEN_O4_AR_WORDS=256`;
  - the token driver takes it with `--enable-ar256`.

## Latency terms of one segment
A segment costs words + LAT 339 + fold (2 + 3 × 5 = 17) + handoff.

| | model | measured (Verilator gate) |
|---|---|---|
| 2 × 128-word segments | 2 × (128 + 339 + 17) = 968, +~10 handoff each | **987** |
| one 256-word stream | 256 + 339 + 17 = 612, +12 handoff | **624** |
| saved per all-reduce | | **363** |

## Gain

| | now (measured) | one stream (priced) |
|---|---|---|
| per layer | 4,668 | 3,942 (−726) |
| per token (72 all-reduces) | 171,090 | 144,954 (−26,136, −15.3%) |
| per-user rate | | **+18.0%**, which passes the 1% gate |

## Depth by Little's law
- **Required depth.** The rate is 1 word per cycle and the round trip is 2 LAT + 2 + 17 = 697 cycles. A 256-word vector never has more than 256 words outstanding, so DEPTH = min(256, 697) = 256.
- **Measured one-stream cycles by DEPTH:**

  | DEPTH | cycles |
  |---|---|
  | 128 | 1,176 (552 credit stalls) |
  | 256 | 624 |
  | 512 | 624 |
  | 1,024 | 624 |

- **The chosen DEPTH is 256.**

## Area per die (FIFO record 546 b = 512 data + 2 + 32 tag)

| DEPTH | 3 remote FIFOs (bits) | SRAM macros (mm²) | flops, upper bound (mm²) |
|---|---|---|---|
| 16 (as built in the model) | 26,208 | – | 0.017 |
| 256 (chosen) | 419,328 | **0.064** (9 × ot_sram_1r1w_256x256) | 0.37 (4 FIFOs, as RTL) |
| 1,024 (the measured runtime) | 1,677,312 | 0.111 | 1.49 |

- Against the runtime's DEPTH of 1,024, the chosen depth saves 0.047 mm².
- Against the depth-16 flop engine, it costs +0.047 mm².
- Even as flops it is under 0.5 mm², so the small-area gate passes.
- **Caveat.** A macro FIFO needs a registered head, which the flop-array RTL lacks. The 256x256 macro has an SS clk-q of 511 ps against an 833 ps period. A macro FIFO is not implemented here.

## Link and routing
- The bytes are the same.
- Peak rate is 1 record per cycle per link either way; only the idle fill/drain gap goes away.
- No new wires are added.

## Exactness
- The fold is lane-wise, `((p0+p1)+p2)+p3` per binary32 lane. The split only partitioned words, so the golden `tools/hdc_golden.fold` and `decode_token_tp` do not change.
- **Verilator gate result:**
  - 3 uniform and 3 adversarial sets, with about 1,500 subnormal partials each, about 55 −0 partials, about 180 partials above 1e38, and about 60 subnormal sums;
  - bit-exact against the golden fold in both modes;
  - identical write logs between the two modes.
- **Fault behaviour is unchanged:**
  - an overflow sum faults code 001 on all four dies at the same word in both modes;
  - a corrupted `last` faults all four sequencers.

## Measured on the TP4 runtime (measured.json)

All runs used one build with `ENABLE_AR256=1`. Run A is the same-binary baseline on the pinned split images.

| run | images | DEPTH | L0 | L1 | X (die 0–3, L0 / L1) |
|---|---|---|---|---|---|
| A | pinned 2×128 | 1,024 | 4,669 | 4,668 | 7631b189 / bd905163, equal to the retained terminal |
| B | one stream | 1,024 | **3,931** | **3,930** | identical |
| C | one stream | **256** | **3,931** | **3,930** | identical |

- The one stream saves 738 cycles per layer, or 369 per all-reduce.
- **Token projection:** 36 × 738 saved gives 144,522 cycles against 171,090, which is −15.5% and **+18.4% per-user rate**. This is projected because the full token was not run.
