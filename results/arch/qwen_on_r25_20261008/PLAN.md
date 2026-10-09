# Qwen3-8B on the unified HBM die r25: the minimal-change plan (stream qwen-hbm-unify, 2026-10-08)

This is a design study. No routes were run and no RTL was edited. Every cycle figure is an **estimate** unless it is marked measured. The machine-readable form is `plan.json`.

Inputs:
- the coverage record `results/arch/coverage_20261008/T4.{md,json}` (cc14fb202, branch claude/coverage-20261008);
- the r25 die (`tools/hbm_accel_die_fp.py` `ADOPTED = R25`; `check` gives **753.19 mm²**, 30,590 x 24,622 µm, which leaves 105 mm² to the 858 mm² reticle);
- the element table (`/api/elements`, 2026-10-08 ~21:50 PT);
- the Qwen quality search (`results/quality/qwen3_8b_weight_format_search.json`);
- the vehicle-A records (`results/rtl/qwen_hbmacc_p8191_20261004`, `hbm_accel_qwen_chains_20261004`);
- the DS collective record (`results/rtl/dshbm_1m_allmeasured_20261004/collectives.json`).

## 0. Headline

**Qwen3-8B can run bit-exactly on r25 without reopening a single closed block.**
- Two **open** blocks change, and both are already in re-route:
  - `ot_hbm_accel_smh_front_c` gains an INT8→BF16 unpack;
  - `hfd_cmdproc_n/s` gets token width 18.
- Everything else is a program, a data layout or a new golden.

The cost is in rate, not in reopened blocks:
- r25 has no weight SRAM, so the LM head streams and nothing hides the per-layer serial chain.
- The central estimate is **~1,240–1,340 tok/s at TP4, P8191, AR**.
- That compares with 2,154 measured on vehicle A, which had 421 MiB of SRAM and a 22 MB prefetch window.
- MTP recovers most of the gap: DSpark at p = 4 gives an estimated **~2,700–3,450 tok/s**.

One item could break the plan:
- In the r25 die view, the attention tiles' KV port is fed from **one fixed pseudo-channel per stack** (`ot_hbm_svc_core` `KV_PC`, closed svc segments).
- A Qwen dense 8K sweep cannot meet the ≥ 90 % bandwidth rule through that port.
- DS's functional model streams KV per PC at full rate, so this is probably a die-view gap shared with T3, but it must be confirmed first.

## 1. What is closed and what is open (the cost basis)

| State on 2026-10-08 | r25 elements Qwen uses |
|---|---|
| **Closed** (reopening costs a route) | svc segments (15 of 17 TT-era; SE_s6 and SW_s4 revoked); `smh_front_n`, `smh_front_s`; `hfd_quant`; `ot_attn_tile_m6h1q` quad; collective credit/idle/FIFO pieces; `ot_dshbm_dspark_ctl` (TT +28.49); `ot_hdc_accept` (TT +113.91); `hfd_su_result_ingress`; all stations |
| **Open** (a change rides the next variant) | `smh_front_c`, `smh_tile_e/w` (failing); `hfd_su`, `hfd_sfu`, `hfd_hc`, norm engine and groups, SU reducers (failing); `hfd_attn_tile` and its halves; `hfd_cmdproc_n/s` (revoked); `hfd_router` (revoked); `hfd_coll`, `hfd_loader` (failing); `ot_dshbm_argmax_m`, `hfd_mtp` (first trial) |

## 2. Gap by gap: (a) program-only, (b) numerics sign-off, (c) hardware mode

"Reopen" means a closed block goes back to open. The area and cycle figures are estimates. The exactness column names the reference golden.

### G1. SM weight dtype: no INT8 decode
The SM decodes BF16 (fmt 0, on the tc16 BF16 lanes), FP8 block-dot (fmt 1) and FP4 (fmt 2) in `front_c` stage A. Qwen's verified contract is signed per-row INT8 × BF16 activations, with the BF16 row scale applied after the FP32 sum.

| | (a) BF16-widened image | (b) FP8 W8A8 on block-dot | (c) fmt 3 = INT8→BF16 unpack |
|---|---|---|---|
| What | Each INT8 code is stored as its exact BF16 value. The BF16 lanes run it, and an SU multiply applies the scale. | Re-quantise to E4M3 (per-row or k32). Activations get FP8 k32 quantisation on the existing path. | `front_c` stage A gains sign-magnitude, a 7-bit LZC and a shift. Each 128-code line is consumed in 2 BF16 beats (half-select), so HBM carries 1 B per weight. |
| Reopen | none | none | none: `front_c` is **open** (failed, re-running) |
| Area | 0 | 0 | ~0.1 mm² for the die (~10k cells × 32 fronts), inside the strip if utilisation allows |
| Cycles | weight bytes ×2: stream 645k → **1,243k** a TP4 token (−48 %) | ≈ c, +~3 % (exponent bytes) | stream 645k; **+1** latency cycle per dependent SM op (DS sees it too unless bypass-matched) |
| Schedule risk | none | Quality harness has no activation-quant mode: ~0.5 day to add, plus ~2.2 GPU-h a contract run (the e8 mode took 7,998 s). | Rides a DS-critical block that is failing now. Put the converter in its own registered stage (≤ 700 ps). |
| Exactness | Exact to the INT8 contract values. Same operands and same lane order as (c), so the **same qwen_r25 golden** applies. | **New contract** (W8A8-FP8), not run. FP8 per-row with BF16 activations passed (+0.51 / +0.70 % PPL, −0.3 MMLU), but that variant needs the same unpack as (c). | Exact, and bit-identical to (a) |

**Recommendation:**
- Use **(a) now for bring-up.** It needs zero hardware and its benches are valid for (c).
- Add **(c) to `front_c`'s next variant.**
- Keep (b) only as the fallback if `front_c` cannot absorb the change.

### G2. Token and index width: 17 bits everywhere, Qwen needs 18
The 17-bit sites are argmax `IW`, dspark_ctl `TW`, accept `NW` and cmdproc20 `TW`.

| | (a) program | (b) | (c) TW / IW = 18 universal |
|---|---|---|---|
| What | **Shard the head:** a per-die argmax over ≤ 37,984 rows (TP4) fits in 17 bits. The cross-die merge is an all-gather plus an SU max that carries `die_base + idx` as an exact FP32 integer, with numpy's lowest-index tie rule. MTP accept is an SU prefix-compare on FP32-encoded ids instead of dspark_ctl. | n/a | 18 bits on all four sites. DS's vocabulary (129,280) is unaffected. |
| Reopen | none | — | `ot_dshbm_dspark_ctl`, `ot_hdc_accept` (two tiny closed blocks, ~1–2 h routes). cmdproc, argmax_m and hfd_mtp are open. |
| Cycles | merge ~0.5 µs (measured `ga_ha2hub` 488 ns) + ~100 SU cycles; SU accept ~300 cycles a verify step (< 0.05 %) | — | 0 |
| Exactness | Exact (ids < 2²⁴ are exact in FP32) | — | Exact |

**Recommendation:**
- **Set cmdproc TW to 18 now.** It is open, and the host token and embedding row id need it.
- Use the program path for the head and accept, so dspark_ctl and accept stay closed.
- If the token-to-address step for the embedding fetch turns out to sit in a closed block, there is a fallback: split the table at 2¹⁷ and let the SU select the base.

### G3. RoPE: adjacent-pair 64-dim tail vs rotate_half over 128 dims (θ = 1e6)
- **(a) Generic SU program.**
  - c12 lane offsets are an affine sum over the lane-index bits (`ld_c`), so lane l can read l XOR 64.
  - The rotation is y = x·cos + x_r·sin', with the sign folded into the sin table (negation is exact).
  - The tables are data.
  - Cost: ~60–120 SU cycles a layer.
  - Exact to a mul, mul, add (RNE) golden.
  - Risk: the XOR-64 offset program has not been benched.
- **(c)** A split-half mode in the fused chain: open SU quarters, no closed reopen, saves ~50 cycles a layer. Not worth adding to failing blocks.
- **Recommend (a).**

### G4. GQA: the tile broadcasts one KV row to 16 head lanes
- **(a) Program mapping.**
  - 32 tiles per KV head, with the 4 q heads in lanes 0–3 and rows split across tiles. That is 25 % lanes.
  - The lanes are not binding. Tile compute is 36.9k cycles a token at 25 %, against a KV stream of 1,325 cycles a layer (47.7k a token), so attention stays KV-bandwidth-bound.
  - MTP verify at p = 4 fills all 16 lanes (4 heads × 4 positions).
  - Exact: chunk8 + pairwise per 64-slice, two slices per head.
- **(c)** Per-lane KV select would reopen `ot_attn_tile_m6h1q` (closed) for no rate gain while attention is KV-bound. Rejected.
- **Recommend (a).**

### G5. QK-norm (per head, 128, with gain)
- **(a)** Generic SU segmented reduction (slots of 128 via `ls`/`lvw`), rsqrt on the side pipe, then a gain multiply.
  - Cost: ~200–300 cycles a layer.
  - Exact in SU tree order.
  - Risk: a segmented reduction has not been benched for Qwen.
- **(c)** not needed.
- **Recommend (a).**

### G6. Norm engine fixed at D5120, hc_pre mix, FP8 output
- **(a)** RMSNorm runs on the generic SU (twice a layer, plus the final norm). Cost ~300–400 cycles a norm; exact in SU order. The fused engine stays DS-only and is untouched.
- **(c)** A D4096/HC0/QUANT0 second master would be another 3.75–4.5M-cell engine. Rejected.
- **Recommend (a).**

### G7. Softmax: sink term, and NVMAX 40 (T ≤ 640)
- The fused `ot_dsrom_su_softmax` cannot hold 8,192 rows, whatever is done about the sink.
  - A sink of −2¹⁰⁰ would be an exact identity there: exp underflows to +0 and es + 0 = es.
- **(a)** A 3-pass generic SU softmax over 8 heads × 8,192 = 64 vectors of 1,024 (max; exp + sum; normalise the PV output). No sink appears on this path.
  - Cost: ~300–600 cycles a layer.
  - Exact: exp is correctly rounded and the divide is IEEE.
- **(c)** NVMAX 512 plus a sink-off bit, on open SU, saving ~300 cycles a layer. Not now.
- **Recommend (a).**

### G8. SwiGLU fused chain quantises to FP8
- **(a)** Generic SFU lanes compute silu(g)·u in FP32 with BF16 output, without the clamp, route weight or quant.
  - Cost: ~100–200 cycles a layer (3,072 elements a die).
  - Exact to the r25 SFU. It does not inherit the W12 reciprocal-seed NaN defect.
  - The fused chain is unusable here because `PUBLISH_QUANT` forces FP8.
- **Recommend (a).**

### G9. Arithmetic order
The r25 orders are: SM tc16 ring + column tree + stack pairing; attention chunk8 + pairwise; SU vred; TU owner-order all-reduce. None matches the W12 golden.
- **(a)** Write the **`qwen_r25` golden**: the Qwen graph in r25 arithmetic, built from `tools/hdc_golden_v41.py` R-ARITH plus the SM, SU and collective orders. ~3–5 days, with vehicle A's flow as the template.
- **(b) Owner sign-off:**
  - Qwen's bit-exact reference becomes `qwen_r25`. This is FP32 re-association only.
  - Confirm it with one contract quality run in r25 order: ~1–2 days for the harness plus ~2.2 GPU-h.
- **(c)** W12-order modes would reopen closed attention quads. Rejected.
- **Recommend (a) + (b).**

### G10. No weight SRAM: the head streams and no window hides the serial chain
- **(a)** Stream the head: 155.6 MB a die = **+49.1k cycles** a token. The serial chain is exposed (estimate 248k–320k cycles a token). MTP and batching amortise both.
- **(c)** SRAM for the head alone would be ~300 mm², more than the 105 mm² margin. Rejected.
- **Recommend (a).** The gap to vehicle A is structural; see §4.

### G11. Collective built for TP-96
- **(a)** A TP4 group of 4 endpoints on the same TU tier. Group membership is configuration.
  - The payload is 4,096 FP32 = 256 words, which is exactly the measured DS `ar_matched_p1` case: **928 ns** in endpoint RTL against the TU budget stub.
  - Full FEC adds ~0.2 µs, giving ~1.13 µs ≈ 1,350 cycles an all-reduce. Two a layer is ~97k cycles a token if exposed.
  - Exact to the owner's fixed-order reduction.
- **(c)** A direct TP4 ring (no switch) would save ~50k cycles a token but reopens closed collective pieces and changes the protocol. Not now.
- **Recommend (a).**

### G12. Qwen program, KV layout, host path, KV read path
**(a) program and layout.** Everything here except the KV read path is exact and needs no hardware:
- **Program.** The cmdproc launch list (36 layer kernels + head) fits NCMD 256 at one launch per layer. It also needs SM/SU kernels.
- **KV layout.** Per die: `[layer][kvhead][K|V][pos][128]` FP8, contiguous.
- **Append.** 144 posted 128 B writes a token. The posted write-back exists.
- **Cache-length mask.** The tile's `pad` bit.
- **Rollback.** The dead-row invariant plus a cache-length register. The DS audit argues it; nothing benches it, so bench it with a mutant.
- **Host.** The cmdproc doorbell `{token, pos}` and completion token (at TW 18) are the token-in/out path. EOS and max length stay host-side; this needs owner confirmation.
- **Embedding.** Replicated in each die's HBM (owner 10-08 decision), dequantised on the SU: ~0.5k cycles a token.
- **KV ingest.** Through `hfd_loader` (open, T3).

**HIGH risk: the KV read path.**
- In the r25 svc die view, kind-1 KV row reads go to one fixed `KV_PC` per stack.
- A dense 4.19 MB/die/layer sweep cannot reach ≥ 90 % of die bandwidth through that.
- If T3 confirms the gap is real for DS too, **(c)** multi-PC KV striping would reopen closed svc segments, and that would be a T3 fix.
- **Recommend (a), and send the `KV_PC` question to the T3 svc owner before any Qwen attention bench.**

## 3. Qwen TP topology on r25
**TP4 = 4 r25 dies per Qwen instance.** Each die holds:
- 8 q heads and 2 KV heads;
- an FFN slice of 3,072 (gate/up column-split, down row-split);
- two all-reduces a layer, after o_proj and after down;
- an LM-head shard of 37,984 rows;
- a full replicated embedding table.

**Iso-area rule** (memory `qwen3-comparisons-are-iso-area`, owner correction 10-03):
- The headline matches the Qwen ROM's die count, TP4 on 4 dies.
- r25 logic is 4 × 753.19 = **3,012.8 mm²**, against 4 Qwen ROM dies of ≤ 858 mm² each. r25 is the smaller side, so the comparison is conservative for r25.
- Iso-total-silicon must also be reported: logic plus every HBM stack, at ~1,000–1,300 mm² a stack. r25 TP4 carries 16 stacks. Iso-power goes alongside.
- TP8 appears only as a labelled scale-out sensitivity. TP2 is half the silicon.

## 4. Token-cycle estimate (TP4, P8191, AR, batch 1, 1.2 GHz)
Basis:
- Bytes a die a token: 36 layers × 48.2 MB INT8 = 1,736.4 MB; head 155.6 MB; KV 151.0 MB. Total **2,043 MB**.
- Sustained bandwidth 3.80 TB/s a die (vehicle A measured 95 % of 4.0 TB/s).
- Stream time: **645,164 cycles**.

Exposed serial chain a layer (estimate, ~6,900–8,900 cycles):

| Term | Cycles a layer |
|---|---:|
| 2 all-reduces | 2,700 |
| SU programs | 2,000–3,500 |
| first access of 4 matvecs + attention tail | 1,700 |
| die wire stages | 500–1,000 |

| Scenario | Cycles a token | tok/s | Grade |
|---|---:|---:|---|
| INT8 (G1c), latency fully hidden (needs a window r25 lacks) | 650,500 | 1,845 | upper bound |
| **INT8 (G1c), serial chain exposed** | **898,500–970,500** | **1,236–1,336** | **central estimate** |
| BF16-widened (G1a, bring-up), exposed | 1,496,000–1,568,000 | 765–802 | estimate |
| INT8 if every 1,088-bit line costs 5 × 32 B sectors (80 % payload) | ~1,048,000–1,120,000 | ~1,071–1,145 | risk to measure |

References:
- vehicle A TP4: measured 2,154.2;
- vehicle A with DSpark: 5,055 (drafter unvalidated);
- published model `qwen.hdc_hbm_rate`: 880.7;
- Qwen ROM published: 5,537.3.

None of the r25 numbers may be published until the stages are measured (owner rule: measured composition only).

## 5. MTP for Qwen on r25 (exact drafts only)
**Status.**
- There is no owner decision for r25.
- Vehicle A adopted DSpark verify at p = 4 (2.28×). Its τ of 3.0375 comes from the ROM record, not the 6-class blend, and its drafter is unvalidated.
- The 2026-09-26/29 decisions named DFlash for Qwen on HBM.
- r25's `hfd_mtp` and `dspark_ctl` are DS-parameterised (B 5, PMAX 8, TW 17, NSLOT 8).

**Why it pays on r25:**
- The weight stream and the exposed serial chain are both shared across verified positions. This is the "dominant cost is shared" condition.
- At p = 4 the GQA lanes go from 25 % to 100 %.

| Option | p | τ | Draft (est.) | Verify / AR step | Speed-up (est.) | Hardware |
|---|---|---|---|---|---|---|
| **DSpark** (the Qwen ROM record's DSpark drafter, block 4) | 4 | 3.0375 (re-measure on the 6-class blend) | 30–60k cycles | 1.1–1.35× | **2.2–2.7× (~2,700–3,450 tok/s)** | none, with SU accept |
| DFlash b16 drafter, block capped at 8 | ≤ 8 | ~3.2 (interpolated between 2.265 at b3 and 3.656 at b16; must be measured) | ~200k (a 2.1 GB BF16 drafter streamed over 4 dies) | 1.35–1.6× | 1.7–2.2× | none at b ≤ 8; b16 reopens dspark_ctl and accept |

Exactness: the released drafter is computed unchanged (memory `draft-must-stay-exact`), and greedy verify must emit exactly the AR tokens. The accept/commit/rollback bench needs a negative mutant.

## 6. Recommended package: "P-min", zero closed blocks reopened
1. **Open-block RTL** (rides the re-routes already in flight):
   - `front_c`: fmt 3 INT8→BF16 unpack plus half-line issue, +1 cycle a dependent SM op;
   - `cmdproc20`: TW 18 (NCMD 256 is enough).
2. **Golden:** `qwen_r25`. One quality run in r25 order for the owner's sign-off.
3. **Programs and layout:**
   - the r25 Qwen image (INT8 lines; BF16-widened for bring-up);
   - the cmdproc launch list;
   - SU programs: RMSNorm, QK-norm, RoPE, 3-pass softmax, SwiGLU, scale, residual, embedding dequant, argmax merge, MTP accept;
   - KV layout, append, mask and rollback;
   - the TP4 TU group;
   - the host doorbell/completion protocol, with EOS on the host.
4. **Benches** (owner rule: one exact stage per layer type plus the head at P8191, each with a negative mutant):
   - start with BF16-widened weights, valid for the INT8 build too;
   - a KV-sweep bandwidth bench, blocked on the `KV_PC` question.
5. **MTP:** DSpark at p = 4 with SU accept, after a 6-class τ measurement for Qwen.
6. **Not in the package:**
   - norm engine D4096;
   - tile GQA mode;
   - weight SRAM;
   - direct TP ring;
   - dspark_ctl/accept TW 18 (only if the owner prefers the DS control path or DFlash b16).

Owner decisions: `/home/ubuntu/claude-takeover-20261007/review_queue/qwen-hbm-unify.md`.
