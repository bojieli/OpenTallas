# Qwen3.8-27B, model level: recommended design point and top risks (2026-10-03)

**Status: MODEL ONLY, not adopted.** There is no RTL, no place and route and no inference. The numbers are in [`model.json`](model.json), produced by `python3 tools/qwen38_27b_model.py`. The profile is `configs/models/candidates/qwen3.8-27b.json`, from `tools/profile_hf.py --model qwen3.8-27b` (config.json plus safetensors headers only).

**Model.** This is the released `Qwen/Qwen3.8-27B`, revision 1d4bf0f2. It is a dense hybrid of 64 layers at hidden 5120:
- 48 Gated DeltaNet layers: 16 key heads and 48 value heads at 128, an FP32 state, and a conv kernel of 4;
- 16 full gated-GQA layers: 24 Q heads and 4 KV heads at 256;
- FFN 17,408, an untied head with a 248,320 vocabulary, and 1 native MTP layer.

At 8 bits this is 26.9 GB of text weights, with the 0.46 GB vision tower excluded. A token streams 25.6 GB. The DeltaNet state is 3.21 MB per layer and **153.9 MB per user**, independent of context. KV is 268 MB at 8K and 1.07 GB at 32K, in FP8.

## Recommended design point: ROM accelerator, 12 dies, TP-4 × 3 stages, 2 stacks a die, KV striped over all dies, plus a new GDN unit

| per user, batch 1 | 8K | 32K |
|---|---|---|
| ROM AR / native MTP (g = 2, MT-Bench τ) | **3,570 / 4,687** tok/s | **3,150 / 4,251** |
| HBM accelerator at iso total silicon (36,012 mm²: 7 dies, 28 stacks, 2.8 GB SRAM), AR / DFlash2 | 1,160 / 4,389 | 1,121 / 4,252 |
| Ratio AR iso-silicon / best-spec iso-silicon / AR iso-power | **3.1× / 1.07× / 24×** | 2.8× / 1.0× / 11× |
| Energy, ROM / HBM iso-Si (AR) | 0.21 / 2.72 J (12.8×) | 0.32 / 2.81 J |
| B200 FP8 (tier-2 model) AR / DFlash2; H200 BF16 measured | 160 / 428; 68.9 / 184 | 158 / 421 |

**Choice of ROM point.** The ROM needs `ceil(26.9 / 3.14 GB) = 9` dies, which rounds to 12 for TP-4. That leaves ROM 71% full, with **92 mm² a die of slack**.

The 2-stack, striped point is within 2% (8K) and 8% (32K) of the fastest configuration swept, 4 stacks striped (3,651 / 3,418 tok/s), and uses 58% of that point's silicon. A 1-stack variant is the silicon-lean alternative: 22,944 mm², 3,418 / 2,724 tok/s, 5.0× AR at iso-silicon.

**The missing unit, Gated DeltaNet.** It is sized per die. Each die holds 12 value heads and 4 key heads, for 16 GDN layers a stage.
- **Golden order.** The unit keeps the golden order: decay, then the S^T k reduction, then the rank-1 update, then the S^T q reduction. It makes two FP32 passes over 196,608 state elements. The one-pass algebraic form changes rounding and is not used.
- **Lanes.** 4,096 FP32 MAC lanes, the widest count that still adds at least 1% (the step to 8,192 adds 0.9%). That gives **313 ns (376 cycles) a GDN layer**, against 1,718 cycles for a full-attention layer at 8K.
- **State in on-die SRAM.** 12.8 MB a user a die, double-buffered for speculative rollback, which is 24.5 MiB.
- **Area.** 13.3 mm² of logic plus 31.9 mm² of SRAM, **45 mm² in all, which fits in the ROM slack**.
- **State in the attached HBM instead** would cost 33 µs a token, cutting the rate from 3,560 to 3,186 tok/s (−10.5%).
- **Arithmetic.** The DeltaNet arithmetic is 0.5% of the weight operations, so it is a latency unit, not a throughput unit.

**Speculation.** Use the native MTP head at g = 2 (P = 3), which gives ×1.31. With 3.7 mm² of AR attention lanes, 22 mm² of verify attention lanes and the GDN unit, the die needs 71 of its 92 mm² of slack.

DFlash2 is worse on the ROM: ×1.25 at g = 3. It also does not fit (99 mm²) once its 1.92 GB drafter is stored in ROM. On the HBM accelerator, DFlash2 at g = 7 is the best drafter.

## Top 3 risks

1. **The GDN unit exists only in the model.**
   - The chain assumes LAT-3 for the FP32 mul and 12 cycles for exp, softplus, sigmoid and rsqrt. The reduction-tree order and the conv and L2-norm placement are unmeasured.
   - The 4,096-lane, 2-pass schedule needs about 24 KB a cycle from the state SRAM.
   - The unit sits where the 12-die build leaves ROM tiles unprogrammed. That makes it a second die variant of the hardened element, which needs its own floorplan and SS/FF closure.

2. **Speculation barely separates the designs.**
   - The ROM gains only ×1.31. Against the HBM accelerator with DFlash2 at iso silicon, the ROM's lead is 1.07× at 8K and 1.0× at 32K. If the HBM side's GDN chain is not hidden under its weight stream, the lead is 1.21× and 1.12×.
   - The τ values are published for BF16 on an H200 at T 1.0 with xhigh reasoning. Applying them to 8-bit weights is ASSUMED. τ at g < 7 is DERIVED from a geometric fit.
   - GDN verify is sequential per position and needs state rollback: a double buffer plus replay, which is assumed hidden behind drafting.
   - ROM's case for this model rests on the AR, iso-power and energy columns.

3. **Calibration transfer and exactness.**
   - About 40% of the token is the Qwen3-8B body: 2,083 fixed cycles measured at H = 4096. Only the weight issue and the all-reduce payload are scaled to H = 5120. Head dim 256, partial RoPE and the output gate are not re-measured.
   - Striping KV over three stages splits each head's softmax along the sequence. The golden must mirror that merge order, or the design falls back to the slower 4-stack local point.
   - The quality of 8-bit weights on this hybrid model, with its FP32 state, is unchecked.

**Assumed or derived, beyond the risks above:**
- FP8 KV (the Qwen contract).
- HBM stack area of 1,089 mm² and ROM die area of 823 mm².
- The B200 and H100 rows are modelled: the H200-calibrated η of 0.90, with speedups transferred from the H200's MT-Bench run. The B200 row with the repository's fit is 132 tok/s AR.
- ROM static power is the Qwen3-8B ungated clock-and-leakage figure, 38.8 W a die. It dominates ROM power, so with ICG the iso-power and energy ratios are conservative for the ROM.
