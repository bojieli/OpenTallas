# Near-HBM (shoreline) attention for the Qwen3-8B ROM die (TP4): pricing from the model only

There is no RTL and no P&R behind this. `price_near_hbm_attention.py` generated the numbers in this note and wrote them to `near_hbm_attention_pricing.json`. The checkout was at origin/main `dcba5c0ab` and was only read, never modified. Every source used is pinned by sha256 in the JSON.

## 1. Can it match the golden exactly? Yes, with two passes. Online softmax cannot.

The golden is `tools/hdc_golden.py`, functions `decode_token_tp`, `attend`, `matvec_il` and `reduce_chunked`. The model-r3 baseline runs the program at G = 6144 groups. At that size, `hdc_program` emits scores with `me_split=7` (128) and `me_rmax`, and P.V with `me_split=9` (512). This agrees with `attn_splits(128, 6144) = (128, 512)`.

| step | golden order |
|---|---|
| score | s_t = pairwise 7-level tree over the 128 products bf16(q)[d]·K[t,d], then ×0.25 |
| max | M is the max over **all** positions. It is order-free, but it must be known before any exp. |
| exp | e_t = exp(s_t − M), computed as Cody-Waite plus degree-6 Horner. This is **not** correctly rounded. `ot_hdc_exp` in `rtl/hdc/ot_hdc_sfu.sv` mirrors it. |
| Z | Contiguous chunks of 8 positions, each summed sequentially from +0. Then a pairwise tree over ceil(T/8) chunks, padded with +0. Z uses FP32 e. |
| P.V | Chunk c holds the positions t ≡ c (mod 512), summed in increasing t from +0. Then a 9-level pairwise tree. P.V uses bf16(e). |
| out | P.V × reciprocal(Z), using the bit seed and 3 Newton steps. The golden normalises after the sum. |

**Verdict.** Online softmax (running max with exp(m_old − m_new) rescale) is **not bit-exact**. It uses different exp arguments and adds extra roundings.

The exact scheme has two phases per layer:
1. Stream all K and store the FP32 scores.
2. Exchange the per-head max across stacks.
3. Stream V, generating e from the stored scores.

Stripe the KV by residue so that stack = (t mod 512) div 128. With that layout:
- Every P.V chunk is local to one stack. Tree levels 1–7 run locally and levels 8–9 run at the hub.
- Every 8-position Z chunk is local to one stack. Z tree levels 1–4 run locally (each run of 16 consecutive chunks stays in one stack) and levels 5–10 run at the hub.
- Padding with +0 is exact because e > 0.

The score buffer is 2,048 positions × 8 heads × FP32 = **512 Kbit per stack** (2 Mbit per die). That is four `ot_sram_1r1w_1024x256` macros per stack; four rather than two because the macros' bandwidth is the binding need. Recomputing the scores instead of storing them would cost +50% HBM traffic.

The max round trip is 162 cycles, including 2 × 45 wire stages. The design hides it by streaming K of KV-head A, then K of KV-head B (350 cycles), then V of A, then V of B.

**Fragility.** The golden's P.V split depends on G. If G changes, the order the unit must mirror changes with it.

## 2. Rates per stack (0.9 TB/s FP8 at 1.2 GHz)

The stack delivers 750 B per edge, which is 5.86 KV rows per edge. Each row is 4 MAC/B × 128 B = 512 MACs (4 q heads × 128 d).

| item | count | how it is arranged |
|---|---|---|
| MACs needed per edge | 3,000 | 6 row-engines × 512 = **3,072 lanes per stack** (12,288 per die) |
| tree / accumulator use | – | Scores use a 128-wide tree. P.V uses sequential accumulators that interleave at least 7 chunks, matching the SS 1,208 MHz LAT-7 adder (FP32_ADD_SS). |
| exp pipes | 24 | 23.4 scores per edge |
| phase length | 700 cycles | per phase (K or V), per layer |

## 3. Boundaries and routing

| quantity | value |
|---|---|
| into each stack, per layer | q is 16,384 b; the new k and v are 4,096 b |
| out of each stack, per layer | P.V partials 32,768 b + Z partials 4,096 b + max 256 b = 37,120 b |
| average across the die | about 60 b/cycle |
| link width | 512 b each way |
| tracks per stack link | 1,056 (4,224 per die) |
| tracks removed | the 7,973 fill-control tracks |

Each link carries 1,056 tracks, which is within one corridor's 1,360 only if each stack gets its own corridor. If all four links must share one corridor, the bus narrows to 128 b. That uses 1,152 tracks, which fits, and costs +10.1 µs per token.

The new wiring is 9.4e7 µm against 4.0e9 µm removed, a 97.6% reduction. Destinations drop from 1,536 to 4 point links. The output re-enters the existing x-broadcast network.

## 4. Latency

The 1,624-cycle on-core attention stage is replaced by a 1,700-cycle near-HBM attention per layer. The cycle counts below are at 1.2 GHz.

| term | cycles |
|---|---|
| q in (45 wire + 40 serialise) | 85 |
| K phase + V phase | 700 + 700 |
| drain + local P.V tree | 76 |
| return + hub (levels 8–9, Z top + reciprocal + multiply) | 139 |
| **total per layer** | **1,700** |

The parts of the token outside attention stay at 69,980 cycles. The figure is model-r3's 128,444 minus 36 × 1,624.

| case | token | tok/s | vs 358.6 µs |
|---|---|---|---|
| **primary** | **109.3 µs** | 9,148 | +228% rate |
| HBM 0.7 TB/s sustained | 121.4 µs | 8,239 | +195% |
| 128-b links | 119.4 µs | 8,373 | +200% |
| full K+V prefetch + 2× lanes (+15.5 mm²) | 88.3 µs | 11,323 | +306% |

The 280.6 µs fill floor goes away, so the HBM floor becomes 41.9 µs per token. With the primary design the binder becomes the **HBM PHY sustained rate**. The rate the stack must sustain rises from 113 to 900 GB/s per stack (7.96×), and model-r3 records `actual_sustained_PHY_Bps = null`. For comparison, the KV-on-core baseline with no fill is 107.0 µs.

## 5. Area per die (ASAP7, routed-unit constants)

| item | mm² |
|---|---|
| lanes, at MAC_UM2 1,071.8 (or LANE_COPY 528.08 + tree FP32 adders 385.5) | 13.17 (11.30) |
| exp pipes 96 × 10,109.8 µm² | 0.97 |
| P.V tree stack flip-flops | 0.39 |
| score SRAM, 16 macros | 0.20 |
| q stationary storage, link flip-flops, adders, hub | about 0.3 |
| control, at an assumed +5% | – |
| **added** | **13.85–15.81** |

What it frees:
- **Assembly pools:** at least 1.58 mm². The 4,760 words × 787 b are known.
- **KV source service:** up to 19.22 mm² (model-r3 `total_known_service_mm2`). The per-PC controller share that must be kept is not priced.
- **Tile KV macros:** 23.91 mm² of macro area, or 31.32 mm² packed, at one 128×256 macro per group × 6,144 groups. This holds only if nothing else uses those macros.

| scenario | net change per die |
|---|---|
| without the tile-macro credit | −5.4 to +14.2 mm² |
| with the tile-macro credit | −36.7 to −9.7 mm² |

The +15.8 mm² added also fits within the 19.67 mm² slot headroom on its own.

**Shoreline fit.** Each stack needs about 3.4–3.9 mm². That is a strip about 0.29–0.33 mm deep behind each 12 mm × 0.83 mm PHY, displacing roughly a quarter of a tile row per stack. The floorplan owner has to approve it.

## 6. What it removes from the credit and ownership problem

These go away:
- the global 7-lane fill to 1,536 destinations, and the 6,613-track deficit
- the 136/17 cohort credits, the 56 × 85 assembly pools and owned DATA_GRANT
- reverse grants and validation to the tiles, and the per-tile write ports and KV landing
- the Ampere legal-channel blocker for the fill corridor

These remain:
- per-PC request/return RAM, refresh and command scheduling, now with **one in-order local consumer** per stack (credit is a local FIFO)
- the new-token write, which has a single owner stack
- 3 small handshakes: q-ready, the max exchange and the partial return

## 7. Assumptions that are not qualified

1. **HBM sustained rate.** 0.9 TB/s per stack is modelled, not measured. This rate is now the binder.
2. **Controller accept rate.** With LEN1 reads at accept II = 5 edges, the controller caps at 204.8 GB/s per stack. Reaching 0.9 TB/s needs reads of LEN ≥ 5 sectors per accept, or a controller redesign.
3. **KV layout change.** The residue-512 stack striping and chunk-major order replace the source-hash PC allocator.
4. **Unit closure.** Several units do not close at SS 1.2 GHz:
   - exp, rebalanced: 1,196 MHz, not closed
   - recip: not closed
   - fp32_mul: 1,274 MHz, not closed
   - BF16 MAC pipe: closed only at 1,040 MHz
   - the LANE_COPY "1.2 GHz" figure does not state its corner
   - the SRAM's SS clk→q is 692 ps against an 833 ps period
5. **Geometry.** The hub-to-stack distance of 22.3 mm (45 stages at 504 µm per stage) assumes the hub sits at the array centre.
6. **Not priced:** control share (assumed 5%), repeaters, CTS, power-grid and the power density at the shoreline.
7. **Tile KV macro credit.** It is conditional on those macros having no other user.
8. **Adoption gates still to pass.** Per AGENTS.md, adoption needs an exact RTL gate, a measured gain, and SS/FF closure in context.

---

## r2: compute recalibrated to the measured TP4 layer (coordinator correction, 2026-10-03)

r1 above is kept as it was. r1 used the unified model's 128,444-cycle token, which under-predicts the measured layer. Source for the measurements: `/tmp/claude-review-20261003/l0cal/l0_reconciliation.md` and `.json`.

### Measured inputs (retained RTL terminal, TP4, position 0)

| term | cycles |
|---|---|
| L0 | 4,669 |
| L1–L35, each | 4,668 |
| head | 2,998 |
| start/terminal cycles not attributed to any span | 43 |
| **total** | **171,090** |
| all-reduces per layer, 2 × 991 (two serialized ~490-cycle segments each, exposed) | 1,982 |

### Per-layer composition

The share of attention at position 0 is taken from the trace span (87 cycles). Using the model's ctx-1 figure (522 cycles) instead is a sensitivity case below. The near-HBM attention stays at 1,700 cycles: it runs on its own unit with its own wire stages, so the tile `me_lat_extra` (now 167) does not enter it.

| per layer | cycles |
|---|---|
| non-collective, non-attention body (4,668 − 87 − 1,982) | 2,599 |
| all-reduces, measured two-segment | 1,982 |
| near-HBM attention (of which 1,400 is the HBM stream) | 1,700 |
| **total** | **6,281** |

### Corrected token

**229,158 cycles = 191.0 µs = 5,237 tok/s.** That is +88% rate against r1's 358.6 µs baseline.

The 358.6 µs baseline came from the same under-predicting model. The calibrated fill-bound current design is at least 358.6 µs and was not recomputed here, so +88% is a lower bound. If the position-0 attention share is the model's 522 cycles, the token is 177.9 µs.

### What binds now

The **compute chain** binds, not HBM:
- non-collective body: 40.8% of the token;
- exposed all-reduces: 31.1%;
- HBM KV stream: 22.0% (42 µs);
- attention fixed latency: 4.7%;
- head: 1.3%.

The HBM sustained rate (0.9 TB/s per stack, unqualified) still sets the attention term. The largest single lever is now the all-reduce.

### All-reduce sensitivity (primary design)

| AR per all-reduce | per layer | token | tok/s |
|---|---|---|---|
| 991 (measured, two-segment) | 6,281 | 191.0 µs | 5,237 |
| ~620 (one-segment, l0cal estimate, unmeasured) | 5,539 | 168.7 µs | 5,928 |
| ~490 (one-segment) | 5,279 | 160.9 µs | 6,215 |

### The three sensitivities

| case | AR 991 | AR 490 |
|---|---|---|
| primary | 191.0 µs / 5,237 | 160.9 µs / 6,215 |
| HBM 0.7 TB/s sustained | 203.0 µs / 4,926 | 173.0 µs / 5,782 |
| 128-b links | 201.1 µs / 4,973 | 171.0 µs / 5,847 |
| full K+V prefetch + 2× lanes (+15.5 mm²) | 170.0 µs / 5,884 | 139.9 µs / 7,148 |

The prefetch refill (1,400 cycles of HBM streaming per layer) fits inside the 4,581-cycle non-attention window.

### Unchanged from r1

Area, routing and the exactness verdict.

### New caveats

- **Long context in the body is not measured.** The measured body is at position 0. Only attention grows with context, and the near-HBM unit carries that, so the body is taken as position-independent.
- **Embedding handoff is not included.** It is host-preloaded in the measurement and unmeasured.
- **Physical timing.** The RTL cycle counts include no SS/FF physical timing.
