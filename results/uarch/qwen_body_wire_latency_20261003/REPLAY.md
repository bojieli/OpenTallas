# Qwen3-8B ROM TP4: body wire latency and golden-order levers (model only)

Status: MODEL ONLY, nothing adopted. No RTL, no P&R, no simulation was launched. The record is `study.json`, written by `tools/qwen_body_wire_latency.py`. Every input is copied under `inputs/` and sha256-pinned in the record.

## Inputs
- **Programs:** the TP4 SW64 L1 die-0 programs.
  - Pinned split image: `50934438`.
  - One-stream image: `23e52eb4`, which measured 3,930 cycles a layer (`claude/qwen-allreduce-oneseg-20261003` @ `7d736e8e6`).
- **Trace:** the RT_ITRACE die-0 L0 trace `a17a3c79` (split build, 4,669 cycles). Its body is the same as the one-stream build's, because only the all-reduce descriptors differ.
- **All-reduce timing:** the one-stream Verilator gate (624 cycles an all-reduce) and `measured.json`.
- **Floorplans:**
  - W12 estimate `c6e6b845`, where the runtime's BD 41 / NWS 5 / TWS 38 / ORD 7 come from;
  - B2-EW r2 `ced04cd96`, the selected frame: 64 x 24 tiles of 313.6 x 1,291.7 um, with the hub at the die centre.
- **Calendar:** the selected near-HBM calendar (`results/uarch/qwen_rom_calibrated_calendar_20261003/near-hbm-selected-r1.json`).

## Method
1. **Simulator.** A re-implementation of `hdc_timing.simulate` that also records which event bound each issue. The tool asserts it equals `hdc_timing.simulate` on every segment of both programs. Parameters: G 6,144, SW 64, position 0, me_lat 16 + 112, and a tree of 4 x 13 levels.
2. **Calibration against the trace.** In steady state, a fetch of word f follows the issue of word f − 5, because the core holds NFQ 4 + NEXT. Model against trace:
   - every instruction issue is within 17 cycles;
   - the body segments are 2,654 in the model against 2,688 in the trace (0.987).
3. **Critical-path walk.** Each segment is walked from END back to its start, and every cycle is attributed. Wire exposure is also measured by sensitivity: setting each ME op's 112 to 0 and seeing what the layer saves.
4. **Candidates.** Each is priced as a cycle delta per layer, on three bases:
   - **A:** the measured one-stream token at position 0, 144,522 cycles;
   - **B:** the selected near-HBM calendar with the one-stream all-reduce: 2,599 + 2 x 624 + 1,700 per layer, plus 3,042, for 202,734 cycles;
   - **C:** basis B with the body corrected for attention (see the findings below), 186,930 cycles.

## 1. Decomposition of the measured one-stream layer (3,930)
- **Layer composition:**
  - non-collective: 2,682 measured, 2,654 in the model;
  - 2 x 624 all-reduce;
  - 28 calibrated boundary cycles.
- **Critical path by category:**

  | category | cycles |
  |---|---|
  | ME compute | 522 |
  | ME fill | 102 |
  | ME tree adders | 312 |
  | **ME wire stages** | **672** |
  | row max | 21 |
  | SU stream | 437 |
  | SU pipe | 434 |
  | SU reducer tails | 108 |
  | handoffs, issue and start | 46 |

- **The serial chain has six ME ops, each 1 + n_el + 16 + 52 + 112 cycles:**

  | op | n_el |
  |---|---|
  | QKV | 64 |
  | scores | 8 |
  | P.V | 8 |
  | O | 48 |
  | GU | 256 |
  | down | 144 |

- **Wire stages on the critical path:**
  - By the walk: 6 x 112 = 672. Of these, 448 are on the four body ops: BD 164, NWS 100, TWS 152, ORD 28, MEM_EXTRA 1 x 4.
  - By sensitivity: 584 in total. QKV exposes only 49, because the input-norm SU chain takes over below that. P.V exposes 87.
  - Body ops by sensitivity: **385 cycles**, which is 17.8% of the non-attention body and 9.8% of the layer.
- **Finding: the calendar's body undercounts attention.** The calendar's "body 2,599" subtracts 87 cycles of attention. The on-core attention on the critical path (scores issue to O issue) is **522**: scores ME, softmax, P.V ME, 1/Z and scale. The non-attention body the near-HBM design keeps is therefore about **2,160**.
- **Finding: the stage runtime adds 58 cycles per layer.** The runtime runs each layer as a stage, which costs a drain, a restart and a recomputed input-norm sum of squares. A continuous token program, where QKV chases the residual op's sum, avoids this. The calendar inherits these cycles.

## 2. Candidates

| id | lever | saving per layer | B | C | verdict |
|---|---|---|---|---|---|
| W1 | per-level NWS (2,3,4,5,3 instead of 5x5), W12 frame | 32 | 0.57% | 0.62% | <3% |
| W2 | monotone, spine-directed in-block H-tree + result ports beside the VM, W12 frame, best case (worst-case rounding: 80) | 112 | 2.03% | 2.20% | <3% (A 4.4%, but not the built design) |
| W3 | selected B2-EW frame: trees at the 2 x farthest-tile floor | 40 | 0.72% | 0.78% | <3% |
| W4 | regional broadcast trees | 0 | 0 | – | triangle inequality |
| W5 | place ops' tiles nearer the hub | ~0 | 0 | – | not exact; G changes the golden tree |
| W6 | level 4: interleave independent chains | 0 | 0 | – | nothing independent at batch 1 |
| W7 | x produced in k-step order, so the ME chases the first SU vector (upper bound) | 125 | 2.27% | 2.47% | <3% |
| L5a | next-norm sum of squares carried with the collective | 0 | 0 | 0 | off the critical path (norm folded after the matvec) |
| L5b1 | post-TP scale + residual in one SU op; the core keeps running across the collective | 136 | 2.47% | 2.69% | – |
| L5c | cut-through send: words leave as tree results are written (O 3 rounds 16 cycles apart, down 48) | 150 | 2.74% | 2.97% | – |
| **L5pkg** | **asynchronous collective = L5b1 + L5c, no new arithmetic** | **286** | **5.35%** | **5.83%** | **> 3%** (A 7.7%) |
| L5b2 / L5max | epilogue applied to the arriving words (new fp32 mul/add); with L5c | 286 / 436 | 5.35% / 8.39% | – | needs SS closure of new arithmetic |

Level-5 terms are priced against the **continuous** token program, not the stage runtime, so no stage artifact counts as a gain. Their timing comes from the Verilator gate: 256 words + LAT 339 + fold 17 + a handoff of 12.

**Geometry.**
- **W12 frame.** The return path is 29.8 mm against a 20.5 mm broadcast: the in-block levels detour, and the uniform NWS pads 17 stages to 25.
- **B2-EW frame.** The hub sits at the die centre, which is the minimax point. The farthest tile is 25.4 mm away in Manhattan distance, which is 51 stages at 504 um.
  - The floor is 106, or 102 if the pins are at the tile's near corner, against the 112 measured.
  - A W12-style tree would *exceed* 112 on B2-EW, because the broadcast alone needs about 53 stages against the runtime's 41. A monotone tree is therefore needed just to hold the measured figure.

## 3. Verdict
**Wire stages: KEEP the current design.**
- On the selected B2-EW frame, the 112-cycle round trip is within 6–10 cycles of the 2 x farthest-tile floor.
- Every wire-side lever prices below 3% per user on the selected design:
  - W2 is 2.0%, and exists only on the W12 frame;
  - W7 is 2.3%, and that is an upper bound.
- Level 4 has no independent ME chain to interleave at batch 1.

**Recommended single candidate: L5pkg, the asynchronous collective.** It saves 286 cycles per layer:
- per-user rate +5.35% on basis B (token 168.9 to 160.4 us) and +5.83% on basis C;
- the AGENTS 1% gate and the 3% bar are cleared on every basis;
- it needs no new arithmetic.

**Exactness:**
- The fold per word, ((p0+p1)+p2)+p3, and the word tags are unchanged; only the send time moves.
- The epilogue is the golden's two element-wise roundings, fl(fl(p x s) + x), done in the SU's multiply stage then its add stage, with no FMA.
- The sum of squares stays in the reducer, in its order.

## RTL plan (opt-in `ASYNC_COLL`, default 0; pinned images byte-identical)
1. **Exactness gate first, in seconds.** In the existing vstream Verilator bench, compare the fused op against the two-op sequence on adversarial vectors: subnormal, −0, overflow and NaN. The fused op is MA_AB with b = the constant-ROM scale, then AD_C with c = X, then the sum of squares. The two-op sequence is MC_C scale, then AD_C. Adopt only if the outputs are bit-identical.
2. **Sequencer:**
   - The core issues the collective to `ot_qwen_tp_seq_w12` and keeps running. A `wait_coll` flag gates the epilogue op.
   - The TP sequencer's VM reads chase the spine's result-slot progress (cut-through) instead of waiting for END.
   - Word tags are unchanged.
3. **Generator:** `QWEN_O4_ASYNC_COLL=1` emits this order: O/down ME, then COLL, then the fused epilogue (`wait_coll`), then the next ME op (chase).
4. **Measure.**
   - Extend the collective gate to cover cut-through and async: bit-exact, with faults identical.
   - Run the TP4 runtime L0+L1 A/B on one binary, requiring X = 7631b189 / bd905163.
   - The model expects a saving of at least 286 cycles per layer, below 3,930 (more in the stage runtime).
5. **Adopt** only on a measured gain and SS/FF closure of the changed sequencers in context. Note that the TP sequencer already misses 1.2 GHz pre-layout.
6. **L5b2** (the receive-path epilogue, a further 150 cycles per layer) follows only if fp32 mul/add close at SS.

## Replay
```bash
(cd tools && python3 qwen_body_wire_latency.py)            # writes study.json
(cd tools && python3 qwen_body_wire_latency.py --verify)   # regenerates in a temp dir; byte-identical
```
It runs in seconds and needs no simulator.
