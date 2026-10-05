# Qwen3-8B ROM: speculative decoding re-checked against the measured design (2026-10-03)

This record is model-priced on measured per-layer terms. It was written as a proposal for the USER. **Afterwards the USER adopted DSpark at block 4 with 2x near-HBM attention lanes.** That configuration is being built on `claude/qwen-rom-dspark-20261003`. This record is the pricing behind the decision, not an RTL measurement of it.

- Pricing: `pricing.json`, from `tools/qwen_rom_speculation_recheck.py`. Test: `tests/test_qwen_rom_speculation_recheck.py`.
- RTL burst gate: `verify_burst_gate.json`, from `tools/qwen_rom_verify_burst_gate.py` on bench `rtl/test/tb_qwen_me_verify_burst_w12.sv`. No existing RTL file changed.

## 1. Why the old verdict no longer holds

The 2026-09-29 record (`results/speculative/dflash_step_timing.json`) said "m=1 never beats AR: the token is lane-bound; weight issue is ~36% of the step". The measured TP4 layer has changed that picture:

- The layer is now 3,930 cycles with the one-stream all-reduce (branch `claude/qwen-allreduce-oneseg-20261003` @ 7d736e8e6).
- Matrix-engine issue is only **512** of those cycles (13.0%). With the selected near-HBM attention at 8K it is 512 of 5,543 (9.2%).
- The issue counts come from the TP4 program's descriptors, tiles x k x IL: QKV 64, O 48, gate/up 256, down 144.
- The rest of the layer is fixed latency. Each ME op pays 16 fill + 112 wire stages + its tree; the all-reduce pays 368 of its 624; the SU chain also contributes.
- The measured ME clock windows (L0 itrace a17a3c79) are 252, 222, 273, 272, 528 and 480 cycles. Each is the op's issue plus 188-336 cycles of fixed latency.

## 2. How the RTL handles multi-position verify

- **No k-columns-per-weight-word mode exists in the ROM matrix engine.** In `ot_qwen_w12_matvec`, each issue cycle multiplies one weight word by one x element per group, and the IL = 8 slots are output rows.
- **The "16 columns = DFlash b16 verify block" note is not ROM.** It sits at `tools/uarch_model.py` `SM_ELEM['qwen']` and describes the GPU-organised HBM comparator.
- **`ot_hdc_qwen_m5_verify_array.sv` is standalone.** It implements the lane multiplier m = 5 (five position lane sets sharing one ROM word) and is not in the W12 runtime.
- **What does work today is back-to-back issue.** `ready = !active && !pend`, and the core issues independent ME ops at a 1-cycle gap. P positions of one projection can therefore be P descriptors: the fixed latency is paid once and the issue P times. The burst gate measures this (section 3).
- **Still missing for a verify layer:**
  - per-position DYN offsets (RoPE row, KV slot, context length);
  - causal in-block attention on the near-HBM unit;
  - an all-reduce of 256p words. Today the 8-bit count and the one-descriptor-at-a-time TP sequencer give +624 per position;
  - per-position LM-head argmax and accept/commit (`ot_hdc_accept.sv` exists).

## 3. Burst gate (Verilator 5.050, ot-pve1)

GATE_RESULTS

## 4. Increment per extra verify position, per layer (cycles)

| term | value | basis |
|---|---|---|
| ME issue | 512 (+4 issue gaps) | program descriptors; burst gate |
| SU | 473 | measured su_writes 30,236 / 64. "overlap" hides it under ME issue |
| all-reduce, existing RTL | 1,248 | 2 x 624, descriptors serialised |
| all-reduce, widened count | 512 | 2 x 256 words, one stream (RTL change) |
| near-HBM attention, lanes for 1 position (selected) | 1,512 | both phases become compute-bound: 1,400 + q 40 + return 72 |
| near-HBM attention, lanes x p | 112 | +14.7 mm2/die per extra lane set |
| LM head | 1,584 | issue per extra argmax position |

Layer increments at p = 2:

| configuration | increment | share of the AR layer (5,543) |
|---|---|---|
| existing RTL | 3,748 | 68% |
| widened all-reduce | 3,012 | |
| + 2x attention lanes | 1,612 | |
| + SU overlap | 1,140 | 21% |

## 5. Step and workloads

- **Step:** draft + verify(B) + commit.
  - **Draft (DFlash):** fc and drafter context K/V over the committed tokens, then 5 drafter layers at p = B, then the LM head over B-1 slots.
  - **Draft (DSpark):** the same, plus a Markov-head serial term of 1,000 cycles per slot. This term is ASSUMED.
- **AR baseline:** 202,590 cycles, 5,923 tok/s, at 8K with near-HBM attention and the measured one-stream all-reduce.
- **Workload classes:** eight, equal weight (USER, 2026-10-03).
  - **DFlash tau:** measured per block in `dflash_block_acceptance.json`, for 5 classes: chat, reasoning, coding, long agentic, assistant/structured.
  - **Missing classes:** long-doc/RAG, multilingual and creative. The "8-class pessimistic" column fills them with the worst measured class.
  - **DSpark tau:** DERIVED. Our DFlash (tau-1) is scaled by the per-benchmark ratio in arXiv 2607.05147 Table 1 (Qwen3-8B, gamma 7, T = 1). That ratio is 1.19-1.31.

**Best block per configuration.** Speedup is per-user tok/s against AR (5,923 tok/s):
- "5" is the equal-weight mean over the 5 measured classes;
- "8p" fills the 3 missing classes with the worst measured class;
- "env" is the per-class minimum and maximum.

"Fit" is judged against the r2 floorplan's 23.0 mm2 margin. Attention lane sets go in the 20.29 mm2 of free shoreline first. The drafter ROM is 30.36 mm2 by the model formula; with r2's 10-macro tile count it is 15.4 mm2.

| config | +mm2/die | fits r2 | DFlash B | DFlash x (5) | DFlash x (8p) | DFlash env | DSpark B | DSpark x (5) | DSpark x (8p) |
|---|---|---|---|---|---|---|---|---|---|
| `existing_rtl_m1` | 30.36 | only at r2 macro count | 1 | 1.000 | 1.000 | 1.00-1.00 | 1 | 1.000 | 1.000 |
| `m1_widenedAR` | 30.41 | only at r2 macro count | 1 | 1.000 | 1.000 | 1.00-1.00 | 3 | 1.082 | 1.046 |
| `m1_widenedAR_attn2` | 45.11 | only at r2 macro count | 2 | 1.171 | 1.155 | 1.13-1.26 | 2 | 1.276 | 1.253 |
| `m1_widenedAR_attn2_overlap` | 45.11 | only at r2 macro count | 4 | 1.254 | 1.207 | 1.13-1.59 | 4 | 1.428 | 1.361 |
| `m1_widenedAR_attn4` | 74.51 | no | 3 | 1.260 | 1.228 | 1.17-1.47 | 4 | 1.425 | 1.359 |
| `m1_widenedAR_attn4_overlap` | 74.51 | no | 4 | 1.442 | 1.388 | 1.30-1.83 | 4 | 1.640 | 1.563 |
| `m2_widenedAR_attn2` | 97.01 | no | 2 | 1.266 | 1.249 | 1.22-1.37 | 4 | 1.393 | 1.328 |
| `m2_widenedAR_attn2_overlap` | 97.01 | no | 4 | 1.283 | 1.236 | 1.16-1.63 | 4 | 1.461 | 1.392 |
| `m4_widenedAR_attn4_overlap` | 230.21 | no | 4 | 1.493 | 1.438 | 1.34-1.89 | 4 | 1.698 | 1.618 |
| `hbm_drafter_m1_widenedAR_attn2` | 14.75 | yes | 1 | 1.000 | 1.000 | 1.00-1.00 | 4 | 1.105 | 1.053 |
| `hbm_drafter_m1_widenedAR_attn2_overlap` | 14.75 | yes | 4 | 1.078 | 1.037 | 0.97-1.37 | 4 | 1.229 | 1.171 |

**Layer increment at p = 2 (cycles):**

| configuration | increment |
|---|---|
| existing RTL | 3749 |
| widened all-reduce | 3013 |
| + 2x attention lanes | 1613 |
| + SU overlap | 1140 |

## 6. Verdict (proposal for the USER, not adopted)

- **On the existing RTL, speculation still loses.** With the selected near-HBM attention (lanes for one position) and serial all-reduce descriptors, every block is slower than AR: DFlash 0.91x at B = 2, DSpark 0.99x. Widening the all-reduce count alone does not change that for DFlash.
- **The binding term moved.** It is no longer ME lanes, which are 512 issue cycles per position-layer. It is now the near-HBM attention, whose lanes are sized for one position, so every extra position pays +1,400 cycles. The second term is the all-reduce payload.
- **What wins:** widened all-reduce count, 2x near-HBM attention lanes (+14.7 mm2, which fit in the free shoreline), and the drafter in ROM.
  - **DFlash:** B = 4, **x1.25** on the 5 measured classes, x1.21 on the 8-class pessimistic fill. The class envelope is 1.13-1.59, and assistant/structured is best. That is about 7,400 tok/s against 5,923.
  - **DSpark (derived tau):** **x1.43**, or x1.36 pessimistic.
  - **These need the SU overlap schedule.** Without it the gains are x1.17 for DFlash and x1.28 for DSpark, both at B = 2.
  - **Area:** about 45 mm2/die, which exceeds the 23.0 mm2 margin unless r2's 10-macro tile accounting (drafter +15.4 mm2) holds.
- **The drafter in attached HBM** (+14.75 mm2, which fits) gives x1.08 for DFlash and x1.23 for DSpark. The 262 MB/die of drafter weights cost 73 us of stream time per step.
- **Lane multipliers m = 2 or 4** add 52 mm2/die per step of m, do not fit, and add little: the ME is no longer the binder.
- **Every win is above the 1% gate**, but nothing is measured end to end.
- **To measure in RTL first:**
  1. a 2- and 4-position verify layer on the TP4 runtime (back-to-back projections with per-position DYN offsets, 256p-word all-reduce, SU interleave), compared against 3,930 + the priced increments;
  2. a p-position near-HBM attention phase at 2x lanes;
  3. LM-head argmax per position plus accept/commit.
- **Quality and caveats:**
  - The drafter's acceptance under INT8 ROM weights is only piloted.
  - DFlash at small B is out of its training distribution (trained at 16).
  - The DSpark tau is derived from T = 1 published ratios at gamma 7, and the Markov-head serial cost is assumed.
- **Reversing the 2026-09-29 decision is a USER decision.**


## 7. Replay

```
python3 tools/qwen_rom_speculation_recheck.py            # writes pricing.json here
python3 -m pytest -q tests/test_qwen_rom_speculation_recheck.py
# burst gate (single Verilator build, ~35 min on a loaded host; ~1 GB RSS at GT=32; GT=128 needed ~20 GB)
python3 tools/qwen_rom_verify_burst_gate.py --workdir W --result results/speculative/qwen_rom_speculation_recheck_20261003/verify_burst_gate.json
```

The gate ran on ot-pve1 from a copy of this branch's `rtl/hdc`, `rtl/proto/ot_fp32_add_rne_pipe.sv`, the bench and the tool, at `/home/ubuntu/qspec-burst-20261003`. Its `source_sha256` pins every file.
