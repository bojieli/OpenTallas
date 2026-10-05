# Qwen3-8B O4 RTL: performance requirements and gap audit (input to the RTL contract)

**Status: advisory.** This document feeds the two-reticle RTL contract; it is not that contract. Codex's Qwen agent owns the contract and the integration (TASKS.md section 1, the "two-reticle 8-bit RTL integration" item). The document states four things:

- what each block must sustain for the O4 rates, with and without DFlash;
- what the current RTL assumes;
- the numerics the 8-bit weight path must reproduce;
- the gap between the current RTL and the requirement.

It prescribes no interface. Where a requirement could be met several ways (the place of the scale multiply, the flow-control mechanism of the die-to-die link), it gives the budget and leaves the design to the contract.

Every figure here is written by `tools/qwen3_o4_rtl_gaps.py` into `results/arch/qwen3_o4_rtl_gaps.json`. The O4 rates come from the O4 record. That record is `results/arch/qwen3_8bit_design.json` at `claude/qwen-o4` 58d70929, configuration `O4_two_reticles_one_package`. It is not on main as of this writing, so the tool carries its figures and cross-checks them against the file when the file is present. `tests/test_qwen3_o4_rtl_gaps.py` checks that the gap table in section 7 is the JSON's table, row for row.

**The two items the contract freezes first:**

- **The INT8 arithmetic** is in section 3.1 (C0–C7). In short:
  - signed symmetric INT8 codes with one BF16 scale per output row;
  - exact INT8 x BF16 products, accumulated in FP32 in the golden's K-split order;
  - one binary32 round-to-nearest-even multiply of the finished FP32 sum by the scale;
  - the result stays FP32 and is never rounded to BF16 at the output.

  This is not bit-exact with the quality harness's quantised kernel, which scales inside every product (section 3.2).
- **The die split** is in section 1.1. The O4 rates need every layer split across both dies (TP-2). A contiguous cut, at its best P = 20, reaches 0.574 of the autoregressive rate and 0.753 of the DFlash rate.

**The 8-bit format passes the deployment-arithmetic quality test, but exact O4 TP-2 quality is open.** The full-model w8 study uses its published FP32 K-split order. A separate 6,144-group TP-2 numeric gate finds occasional BF16 differences from that order, so the quality pass is representative of the format rather than an exact two-die verdict. DFlash acceptance (2.8591 tokens a step at block 5) was measured in BF16 on a GPU, not at 8 bits.

## 1. The target and what binds it

O4 is the user's decision of 2026-09-28:

- two reticles in one CoWoS-L-class package;
- INT8 weight-only: signed, symmetric, one BF16 scale per output channel, never 4-bit;
- layers split across the two dies over UCIe, which the O4 record prices as every layer split (tensor-parallel 2, TP-2; section 1.1);
- 4 HBM3E stacks a die, 8 in the package;
- 6,144 lane groups a die, which is the most the die's ROM can feed at 8 bits;
- lane multiplier m = 5 for the DFlash verify at block 5.

The clock is 1.09864 GHz and the context is 8K with FP8 KV.

| Quantity | O4 figure | Source |
|---|---|---|
| lanes a die (6,144 groups x 16) | 98,304 | O4 ledger |
| copy lanes a die (m - 1 = 4 MAC-only copies) | **393,216** <!-- figure: 393216 src="results/arch/qwen3_o4_rtl_gaps.json#requirements.copy_lanes_per_die" name="O4 copy lanes a die" --> | derived |
| AR step at m = 1 (cycles a token) | **105,724** <!-- figure: 105724 src="results/arch/qwen3_o4_rtl_gaps.json#o4.ar_step_cycles" name="O4 AR step cycles" --> | RTL-calibrated chain 104,473 + UCIe exchanges 1,251 |
| AR rate | **10,391.6 tok/s** <!-- figure: 10391.6 src="results/arch/qwen3_o4_rtl_gaps.json#o4.ar_tokens_s" name="O4 AR tok/s" --> | O4 record |
| KV floor (8 stacks at 0.9) | **92,161** <!-- figure: 92161 src="results/arch/qwen3_o4_rtl_gaps.json#o4.kv_floor_cycles" name="O4 KV floor cycles" --> | O4 record |
| plain step on the specification chain (DFlash block 1) | 123,903 | spec chain 122,652 + 1,251 |
| DFlash step at block 5 (draft + verify + commit) | **189,758** <!-- figure: 189758 src="results/arch/qwen3_o4_rtl_gaps.json#o4.step_cycles" name="O4 DFlash step cycles" --> = 26,677 + 163,071 + 10 | O4 record |
| DFlash rate at 2.8591 tokens a step | **16,553.3 tok/s** <!-- figure: 16553.3 src="results/arch/qwen3_o4_rtl_gaps.json#o4.dflash_tokens_s" name="O4 DFlash tok/s" --> | O4 record (BF16 acceptance) |

The "~123K-cycle chain" in the directive is the plain step on the specification chain (123,903). The autoregressive rate is not priced on that chain. It is priced on the RTL-calibrated sequencer replay (105,724 cycles), as the single-reticle baseline was, and so the 10,392 tok/s figure rests on it.

**Current TP-2 rates (gap G15).** The adopted package replays one die's slice at 6,144 groups with 73 serial FP32 exchanges (1,407 cycles) and the embedding-row handoff (12 cycles). The INT8 post-tree multiplier adds 5 cycles on each of 145 weight and 72 exposed KV attention results. The current autoregressive rate is **10,873.6 tok/s** <!-- figure: 10873.6 src="results/arch/qwen3_budget.json#power.points.ar_batch1.at.design.tokens_s" name="O4 TP-2 AR tok/s" -->, and DFlash at block 5 is **18,719.9 tok/s** <!-- figure: 18719.9 src="results/speculative/dflash_step_timing.json#rom['8192/fp8/m5'].best.tokens_s" name="O4 TP-2 DFlash tok/s" -->. These are model rates; the full-size token and UCIe gates remain open.

**What binds.**

- **Autoregressive.** The dependency chain binds, 14.7% above the KV floor (105,724 against 92,161 cycles). The KV stream is therefore a near-binding secondary requirement, not a free one: a KV path that sustains less than about 87% of 3.6 TB/s a die makes the KV stream the binding resource.
- **ROM read.** It fixes the group count. Each die needs 98,304 B a cycle, and the ROM supplies 1.017 times that.
- **DFlash verify.** The chain binds (163,071 cycles). Its parts are:

  | Part | Cycles | Share |
  |---|---|---|
  | exposed pipeline latency | 57,132 | 35% |
  | five slots of stream-unit work | 48,960 | 30% |
  | the weight sweep (shared by the copies) | 38,880 | 24% |
  | attention | 16,128 | 10% |
  | control and exchanges | 1,971 | 1% |

### 1.1 The die split: which layers go where

`docs/QWEN_TWO_RETICLE_RTL_CONTRACT.md` proposes a contiguous layer cut at a layer P as the minimum-transfer topology, and leaves P, the embedding and lm_head owners and the stack allocation open. This section answers that question. Its figures are in `die_split` of the JSON.

**The O4 rates are TP-2 rates.** The O4 record prices "every layer split across both" dies: tensor-parallel 2, where each die holds half of every layer's heads and FFN rows and half of the embedding, lm_head and drafter. Both dies' 6,144 groups and both dies' 4 stacks then work on every token.

A contiguous cut cannot do that at batch 1. Token t+1 needs token t, so the two dies take turns. A token is then served by half the lanes and half the stacks, and with each die's KV on its own 4 stacks the KV floor doubles to 184,321 cycles and binds. Priced by the O4 tool's own model at one die's engine and stacks, plus the cut's handoffs:

| Split | AR step (cycles) | AR tok/s | DFlash step, block 5 (cycles) | DFlash tok/s | UCIe a token (AR) |
|---|---|---|---|---|---|
| **TP-2, every layer split** (the O4 rates) | 105,724 | **10,391.6** | 189,758 | **16,553.3** | 73 exchanges, 1,183,754 B a direction, 1,407 cycles |
| contiguous cut at P = 20 | 184,348 | **5,959.6** <!-- figure: 5959.6 src="results/arch/qwen3_o4_rtl_gaps.json#die_split.layer_cut.ar_tokens_s" name="O4 layer-cut AR tok/s" --> | 252,077 | **12,461.0** <!-- figure: 12461.0 src="results/arch/qwen3_o4_rtl_gaps.json#die_split.layer_cut.dflash_tokens_s" name="O4 layer-cut DFlash tok/s" --> | 2 handoffs, 16,384 B + 4 B, 27 cycles |

The contiguous cut reaches 0.574 of the O4 rate in the autoregressive step and 0.753 with DFlash. It moves 72 times fewer bytes, but bytes are not what the link limits: TP-2's 1.18 MB a token is 0.3% of the link. **Recommendation: TP-2.** This is decision D1 (section 8), and it is the user's to confirm, because TASKS.md's phrase "split layers across UCIe" reads either way. The contract's handoff machinery (header, credits, abort/replay) serves TP-2 unchanged; TP-2 simply has 73 transactions a token instead of 1.

**If a contiguous cut is kept, cut at P = 20.**

- **Die A** holds the embedding and layers 0–19.
- **Die B** holds layers 20–35, the final norm, the lm_head and the DFlash drafter. The drafter shares the lm_head, and its draft feeds die B's verify tail.
- **Capacity.** Die A needs 245.82 mm² of ROM and die B 261.01 mm², against the O4 ROM budget of 281.62 mm² a die (target and drafter ROM plus slack).
- **ROM read.** P = 20 is the only cut where both dies fit and both ROMs come within 0.3% of feeding their 6,144 groups at one INT8 a lane a cycle: die A reaches 1.037 of the need and die B 0.997. The swept ROM is the layers plus the lm_head, as in the O4 model. At P = 19 die A falls to 0.985; at P = 21 die B falls to 0.945.

Handoffs for the P = 20 cut, all serial on the chain:

| Direction | Autoregressive (m = 1), a token | DFlash (m = 5, block 5), a step |
|---|---|---|
| A → B, after layer 19 | 16,384 B: the FP32 residual, which is read by the residual add and by rstd, so it must stay FP32 | 204,800 B: 5 slots' FP32 residuals, plus the drafter's taps from layers 1, 9 and 17 in BF16 (bit-exact, because only a matvec reads them) |
| B → A, after the argmax | 4 B: the token id, for die A's embedding lookup | 24 B: 5 draft tokens and the accepted count |
| exposed cycles | 27 | 76 |

The sweep over P = 16..24 is in `die_split.layer_cut_sweep`.

**Under TP-2** (recommended), there is no layer cut:

- each die holds 16 query heads and 4 KV heads of every layer, and its KV on its own 4 stacks;
- QKV and gate/up are split by output rows, o and down by input columns with a rank-order all-reduce;
- the embedding, the lm_head and the drafter are split in half by vocabulary and rows;
- each die needs 253.41 mm² of ROM, equal to the O4 ledger, and its ROM feeds its groups 1.017 times over.

The exchange traffic and its position on the chain are in section 4.

## 2. Per-block requirements, per die

Every requirement below is per die of the TP-2 pair. The autoregressive gate is m = 1 with one slot (B = 1). The DFlash gate is the verify at m = 5 with B = 5, followed by the draft on the same engine.

| Block | Autoregressive (m = 1) | DFlash verify (m = 5, B = 5) | Basis |
|---|---|---|---|
| ROM read | **98,304 B/cycle** <!-- figure: 98304 src="results/arch/qwen3_o4_rtl_gaps.json#requirements.rom.read_bytes_per_cycle_per_die" name="O4 ROM read B/cycle/die" -->: 128 bits a group a cycle (256 today at BF16) | the same: the copies share the group's word | one INT8 code a lane a cycle |
| weight bytes a token | 3,784,048,640 (36 layers of 96,468,992, plus half the lm_head) | the same, once a step | TP-2 slices |
| matrix engine, a layer | qkv 128 + o 88 + gate/up 512 + down 264 = **992 cycles** <!-- figure: 992 src="results/arch/qwen3_o4_rtl_gaps.json#requirements.layer_mv_cycles" name="O4 layer matvec cycles a die" --> | the same 992, with 5 x 98,304 = 491,520 MACs a cycle | RTL tiling rule at 6,144 groups |
| lm_head (75,968 rows a die) | 3,168 cycles a token | 3,168 a step (5 slots' logits); the drafter's head over 4 slots in the draft | |
| scale multiply | at least **47 outputs/cycle** sustained, bursts up to 1,536 | **233 outputs/cycle** sustained | the densest matrix, o at K = 2,048 a die |
| attention, a layer at 8K | 16 query heads and 4 KV heads; 33,554,432 MACs; 512 cycles as built (scores 256 + P·V 256) | the same cycles; each KV word serves 5 slots' queries | |
| stream unit | width 1,024; 9,792 elementwise cycles a token | 48,960 cycles a step (5 slots) | spec chain |
| KV read | **3,276.8 B/cycle** <!-- figure: 3276.8 src="results/arch/qwen3_o4_rtl_gaps.json#requirements.kv.bytes_per_cycle_per_die" name="O4 KV B/cycle/die" --> (3.6 TB/s on 4 stacks); 8,388,608 B, i.e. 2,560 cycles, a layer | the same bytes once a step | FP8, 4 KV heads a die |
| KV ring | **9,648,608 B** <!-- figure: 9648608 src="results/arch/qwen3_o4_rtl_gaps.json#requirements.kv.ring_bytes_per_die" name="O4 KV ring bytes a die" --> (one layer of the die's KV plus refresh cover) | the same | `kv_prefetch_buffer_bytes` rule |
| KV write | 36,864 B a token | 5 rows a head a layer | |
| UCIe | 73 exchanges a token, 1,407 cycles (section 4) | 73 exchanges of 5 slots, 2,659 cycles a step | |
| cycles a layer | **2,814** <!-- figure: 2814 src="results/arch/qwen3_o4_rtl_gaps.json#requirements.ar.per_layer_cycles_budget" name="O4 AR per-layer budget" --> budget; as built 2,807 | 4,530 (163,071 / 36) | |

**Notes on the table.**

- **Budget sources.** The autoregressive per-layer budget is the step less the exchanges and the lm_head, spread over 36 layers. The engine-cycle rows use the RTL's tiling rule (`floor(G/S)` tiles a round, `rtl/hdc/ot_hdc_matvec.sv`, as in `tools/arch_budget_qwen3.split_rounds`) at 6,144 groups, one die's slice.
- **The TP pair as one engine.** The O4 record replays the pair as one 12,288-group engine. The per-die matrix cycles above equal that replay's (o: 88 = 88; gate/up: 512 = 512), so the per-die requirement and the O4 rate agree.
- **The as-built autoregressive layer.** The replay at the pair's 12,288 groups shows where the 2,807 cycles go:

  | Stage | Cycles | Engine busy | Exposed |
  |---|---|---|---|
  | QKV projection, then q/k norm, RoPE | 564 | 128 | 436 |
  | attention: scores, softmax, P·V, 1/Z | 873 | 512 | 361 |
  | O projection, residual, FFN norm | 183 | 88 | 95 |
  | gate/up projection, fused SiLU·up | 828 | 512 | 316 |
  | down projection, residual, next norm | 359 | 264 | 95 |

  The engine is busy for 1,504 of the 2,807 cycles. The other 1,303 are stream-unit and pipeline latency. Any latency the 8-bit path adds per matrix lands directly on this chain.
- **Scale multiply.** Its sustained rate is the densest matrix's rows over its cycles. For o, that is 4,096 rows in 88 cycles, i.e. 46.6 a cycle. The multiplies number 923,840 a token a die. The burst is set by the split tree: (G/S) x W results leave the tree together, and for gate/up (S = 64) that is 1,536. At an assumed 4-cycle multiply, exposing it after every matrix costs (4 x 36 + 1) x 4 = **580 cycles a token** <!-- figure: 580 src="results/arch/qwen3_o4_rtl_gaps.json#requirements.scale_multiply.chain_cost_cycles_per_token_if_exposed" name="O4 exposed scale cost cycles" -->, 0.55% of the autoregressive step.
- **Attention.** At 6,144 groups the golden's attention splits are 128 ways over the head dimension for scores and 512 ways over positions for P·V (`attn_splits`, which takes the power-of-two floor). That gives 256 P·V cycles a layer. The specification chain behind the DFlash figures prices P·V at 192 cycles (a 1,536-way split at the pair level). The verify therefore carries a known +64 cycles a layer (2,304 a step, 1.4%) of optimism.
- **Replicated work.** Norms, residual adds, the final norm and the embedding dequantisation run on both dies over the full hidden size. At a stream-unit width of 1,024 this is 4 vectors a norm, negligible, but it is not halved by TP-2.

## 3. Numerics: the 8-bit contract and the check against the harness

### 3.1 The contract

These are the terms the RTL and the golden must share. They are identical to Codex's corrected draft: fixed signed INT8 with one BF16 scale per output channel, applied after FP32 accumulation.

- **C0 quantiser.** Quantisation is offline and a model-side choice, pinned in the manifest; the RTL consumes codes and scales as data. Codes are clamped to [-128, 127] when they are quantised, so the datapath needs no saturation. The quality study that picks the production quantiser is still running. The reduced vehicle uses the harness's round-to-nearest rule with a per-row MSE clip (`_rtn_mse` at 8 bits):
  - s = bf16(amax x r / 127), with r chosen from linspace(0.5, 1, 21) by the row's squared error;
  - q = clamp(round-half-even(w / s), -128, 127).
- **C1 weights.** Weights are signed INT8 codes q in [-128, 127], symmetric, with no zero point. For q, k, v, gate and up, the codes quantise the norm-folded BF16 matrix W' = bf16(W diag(w)). For o, down and the lm_head they quantise W itself. There is one BF16 scale s_n per output row n; for the embedding and the lm_head that is one per vocabulary row.
- **C2 products.** Each product bf16(x_k) x q_nk is formed exactly in FP32; it has at most 15 significant bits. Accumulation follows the golden's K-split order: S contiguous chunks, each summed sequentially from +0 in FP32 round-to-nearest-even (RNE), and the chunk sums added by a pairwise tree.
- **C3 scale.** y_n = fl32(T_n x s_n): one binary32 round-to-nearest-even multiply of the FP32 sum by the BF16 scale. It has gradual underflow and canonical +0, the arithmetic of the qualified `ot_fp32_mul_rne_pipe`. **y_n stays FP32; it is not rounded to BF16.** BF16 rounding happens only where the golden already rounds (the next matvec's input, and q and the probabilities before attention), and FP8 at the KV write. The multiply sits after the whole K sum, including the split tree, and before every consumer: the argmax compare, the 1/rms multiply, the residual add and, under TP-2, the fold (C7).
- **C4 norm fold.** q, k, v, gate and up equal fl32(y_n x r) with r = rstd(x). The scale is applied first, then 1/rms.
- **C5 embedding.** x_h = q_th x s_t, which is exact in FP32 (no rounding).
- **C6 lm_head.** logits_n = fl32(T_n x s_n). The argmax compares scaled logits, with ties going to the lower index.
- **C7 TP-2 row split (o, down).** Either each die scales its partial (C3) and the partials are folded in rank order as fl32(y0 + y1), or the partials are folded first and scaled once. The two orders are not bit-identical, and the golden must pin one (decision D2). A contiguous cut has no row split, so C7 does not arise there.

C2 and C3 mean the existing exact BF16 x BF16 lane computes T unchanged: every INT8 code is exact in BF16. The 8-bit path is therefore a decode in front of the multiplier and one multiply behind the tree. It needs no change to the accumulation.

### 3.2 The check

`numerics()` in the tool compares the contract against the quality harness's quantised arithmetic (`tools/qwen3_deployment_quality.py`). The inputs are:

- **Rows.** 192 real Qwen3-8B rows per matrix from the HF snapshot: layer 0's q, o, gate and down, and the lm_head. The q and gate rows are norm-folded. The o and down rows are cut to one die's K slice.
- **Quantiser.** The harness's own `_rtn_mse` at 8 bits, with one group per row. Its codes span -128 to 127.
- **Split.** Each die's K-split at 6,144 groups.

The harness has no 8-bit mode. Its quantised kernel (`_chunk_tree_dot_ref`, the reference of its Triton kernel) forms w = code x scale and accumulates the scaled products. The scale is inside every product, as for its group-128 formats.

| Matrix (die slice) | K | S | Rows differing, harness order vs contract | Max ulp | Max relative |
|---|---|---|---|---|---|
| q (folded) | 4,096 | 256 | 145 / 192 | 780 | 5.0e-5 |
| o | 2,048 | 2,048 | 143 / 192 | 94 | 1.0e-5 |
| gate (folded) | 4,096 | 64 | 151 / 192 | 64 | 7.5e-6 |
| down | 6,144 | 2,048 | 149 / 192 | 110 | 1.1e-5 |
| lm_head | 4,096 | 1,024 | 132 / 192 | 188 | 1.1e-5 |

**Verdict: not bit-exact.** **720 of 960** <!-- figure: 720 src="results/arch/qwen3_o4_rtl_gaps.json#numerics.harness_order_rows_differing" name="O4 numerics rows differing" --> outputs differ from the contract. The reason is structural, not a quantiser detail: scaling inside the sum rounds every accumulation step at the scaled magnitude, and scaling after the sum does not.

Everything else the contract relies on held on every row:

- the harness kernel equals the golden with pre-scaled weights, bit for bit;
- every INT8 x BF16 product is exact in FP32;
- every code is exact in BF16;
- every scale is a BF16;
- the embedding dequantisation is exact.

The two C7 orders differ in 83 of 192 down rows, by at most 20 ulp.

**What this requires.** The contract stands as C1–C7. The harness needs a per-channel INT8 mode that scales after the chunk-tree sum (gap G14). Its quality verdict at 8 bits must be taken in that mode, so that the arithmetic the quality bar approves is the arithmetic the RTL computes. The differences are at most 5e-5 relative, so the harness's group-scale order is a fair quality proxy until then, but it is not a bit-exactness reference.

### 3.3 The K-split at 6,144 groups

6,144 is not a power of two, and the golden and the RTL pick the K-split by different packings:

- the golden's `split_for` packs ceil(tiles x S / G);
- the RTL issues floor(G / S) whole tiles a round.

At a power of two the two coincide. At 6,144 they agree on every target matrix slice: qkv S = 256, o 2,048, gate/up 64, down 2,048, lm_head 1,024. They **disagree on the drafter's fc slice** (2,048 x 20,480): the golden chooses S = 4,096 and the RTL rule S = 1,024. A different S is a different accumulation order, so the two must be reconciled before the drafter is gated (gap G6).

## 4. The UCIe boundary

**Link.** The package has one UCIe link between the two dies: 4.2 TB/s a direction and a 10 ns hop (range 3–30 ns), per `configs/hardware/technology.json` `links.rom_package_ucie`. At 1.09864 GHz the hop is 10.99 cycles.

**Traffic a token, each direction.**

| Exchange | Count | Bytes each | Where on the chain |
|---|---|---|---|
| all-reduce after o | 36 | 16,384 (H FP32 partials) | before the residual add and the FFN norm's sum of squares |
| all-reduce after down | 36 | 16,384 | before the residual add and the next layer's norm |
| argmax gather (lm_head vocabulary halves) | 1 | 8 (value and index) | before the token is known |
| embedding-row handoff | 1 | 4,098 (the INT8 row and its BF16 scale) | before layer 0 of the next token |
| **total** | 74 | **1,183,754 B** <!-- figure: 1183754 src="results/arch/qwen3_o4_rtl_gaps.json#requirements.ucie.bytes_per_token_per_direction" name="O4 UCIe bytes a token a direction" --> | |

At 10,391.6 tok/s that is 12.3 GB/s on average, about 0.3% of the link. **The link's bandwidth is not the requirement; its latency is.** Every exchange sits on the dependency chain at batch 1. The residual add needs the other die's partial, and the next norm's sum of squares needs the whole residual. No independent work hides it.

**Partials are FP32, not BF16.** The golden's all-reduce (`fold`) adds the dies' FP32 matrix outputs in rank order. A BF16 partial would be a different arithmetic: a golden change with its own quality question. The O4 record priced BF16 partials. With FP32 partials, each exchange costs hop 10.99 + transfer 4.29 + add 4 = 19.27 cycles. The token then pays 73 x 19.27 = **1,407 cycles** <!-- figure: 1407 src="results/arch/qwen3_o4_rtl_gaps.json#requirements.ucie.fp32_cycles_per_token" name="O4 UCIe cycles a token FP32" -->, against O4's 1,251. The autoregressive rate becomes 10,376.3 tok/s, a 0.15% change.

The embedding-row handoff is a 74th exchange that the O4 count leaves out. It adds about 12 cycles.

**Latency budget.** The O4 rate's budget for the exchanges is 1,251 cycles a token, about 17 cycles an exchange. Across the hop's range, with FP32 partials:

| Hop | Cycles a token | AR tok/s |
|---|---|---|
| 3 ns | 846 | 10,431.5 |
| 10 ns | 1,407 | 10,376.3 |
| 30 ns | 3,011 | 10,221.4 |

The requirement is at most about 19 cycles exposed an exchange at the 10 ns hop. That means:

- the transfer must start as soon as the partial's first rows exist;
- there must be no store-and-forward of a whole partial before the hop;
- the receive side's add must be pipelined into the residual pass.

Streaming a partial row-tile by row-tile as the tree produces it would leave only the hop, the last tile and the add exposed. That is one way to meet the budget, not a prescription.

**Verify at B = 5.** Each exchange carries 5 slots' partials, 81,920 B. The transfer grows to 21.43 cycles and the exchange to 36.42. The step pays **2,659 cycles** <!-- figure: 2659 src="results/arch/qwen3_o4_rtl_gaps.json#requirements.ucie.verify_b5_cycles_per_step" name="O4 UCIe cycles a verify step" -->, against the 1,251 the O4 verify carries. That is +1,408 cycles, 0.7% of the step. The verify also gathers 5 argmaxes and the draft 4.

**Flow control.** The requirement is that no credit round trip lands on the chain. The link's bandwidth-delay product over a 10 ns round trip each way is 84,000 B. The receiver must be able to accept one whole exchange without returning credit mid-exchange: 16,384 B an exchange at m = 1 and 81,920 B at B = 5, or the equivalent credit returned within the transfer. How this is done (buffer depth, credit granularity, the flit size of `ot_rom_ucie_link`) is the contract's choice.

The existing TP bench (`rtl/test/tb_hdc_package_tp.sv`) runs 16 flits of 64 B of credit (CDEPTH 16, FLIT 512 bits). That is 1 KiB, so at TP-2 the contract must show either that its collective never waits on credit, or what the wait costs.

**Energy.** At the advanced-package figure of 0.5 pJ/bit, both directions together cost about 9.5 µJ a token, against roughly 97 mJ a token for the package. It is not a design driver.

## 5. The DFlash verify organisation (m = 5)

**Shared weight word.** Each of the 5 lane copies of a group reads the same weight word as the base lane; the copies are MAC-only (`ot_hdc_lane_copy.sv`). The weight sweep of a verify step is therefore one sweep, 38,880 cycles, serving all 5 slots. The ROM read requirement does not change with m.

**What multiplies by 5.**

- activation operands: 5 a group a cycle, one per slot;
- accumulators and results: 5 a lane;
- the scale multiplies' sustained rate (233 a cycle);
- the stream unit's work;
- the exchanges' bytes.

**Attention.** The 5 slots' queries meet each KV word once:

- scores and P·V read the context's K and V once a step;
- the block's own 5 new K/V rows are causal within the block: slot j attends to the context and the draft slots up to and including j;
- the step writes 5 rows a KV head a layer.

**Draft.** The draft runs on the same engine and copies. Its work is the fc over the committed positions (4,096 x 20,480, split TP-2 like the target), the drafter's 5 layers over the block's slots, and the shared lm_head over the 4 draft slots with a per-slot argmax. Its budget is **26,677 cycles** <!-- figure: 26677 src="results/arch/qwen3_o4_rtl_gaps.json#o4.draft_cycles" name="O4 draft cycles" --> a step.

The drafter reads the target's hidden states at 5 layers (1, 9, 17, 25 and 33). TP-2 replicates the residual stream, so these taps are local on each die: 81,920 B a committed position. The drafter's weights are INT8 like the target's, 28.76 mm² of ROM a die.

**Commit.** The accept compares, the bonus token and the next step's dynamic state take 10 cycles. `ot_hdc_accept.sv` (greedy prefix accept, 8 slots) already exists and is instantiated only by the V4.1 cores.

**The autoregressive gate on the same RTL.** At m = 1 only the base lane works. The O4 power figures price the copies as idle in the autoregressive step (`lane_copies_on = min(m, B) - 1 = 0`), so the copies must be clock- or operand-gated there.

**Power.** This is not an RTL gate, but the O4 record puts a die at 419.9 W in the autoregressive step under the production-lane scenario, against a 374.6 W air-cooled limit. That scenario binds under air and not under liquid.

## 6. Where the current RTL assumes the old format or one die

**Weight format.** Every Qwen RTL path is BF16 today.

- The weight ROM word is `G x W x 16` bits (`ot_hdc_core.sv`, `ot_hdc_matvec.sv`).
- The matvec widens `{mq_wrom[16*l +: 16], 16'h0000}` into the exact BF16 multiplier (`ot_hdc_matvec.sv`).
- The stream unit reads the embedding the same way (`ot_hdc_stream.sv`, `ot_hdc_vstream_lane.sv`).
- The image writer stores BF16 top halves (`tools/hdc_program.py` `place_matrix`).
- 16 bits a lane is also hard-coded in `hbm_weight_image`, `pack_lanes(w, 16)` and `tools/hdc_timing.py` `price_hbm`.
- No ISA field carries a weight format or a scale base.

**Reduced vehicles.** Every RTL gate (`rtl_hdc_qwen_*.py`, `rtl_hdc_decode_campaign.py`) uses the same checkpoint: the BF16, Philox-random `build/models/qwen3-reduced-v1` with hidden size 128, 4 layers, 8/2 heads and a vocabulary of 4,096. No gate has ever run INT3/INT6 (3.5-bit) or INT8 weights. The 3.5-bit format existed only in the GPU quality study.

**Topology.**

- The Qwen core is one die. Its TP machinery lives in `rtl/rom`: `ot_rom_oneshot_allreduce` (N-parametric, a rank-order FP32 fold, per-pair credits), `ot_rom_tp_seq` and `ot_rom_ucie_link`.
- That machinery has run only at 4 dies with the *scalar* `ot_hdc_core` (`tools/rtl_hdc_package_tp_campaign.py`, TP = 4). It was bit-exact, with a 1.999x speedup on the reduced vehicle.
- No two-die run exists, and no run uses the vector core.
- `hdc_program.py` and the golden turn the norm fold off whenever tp > 1. `decode_token_tp` also keeps BF16 KV, not the vector core's FP8.

**KV path.**

- `ot_hdc_qwen_kv_system` has one 32-B HBM request port, and its physical arbiter keeps one request outstanding.
- The HBM model covers 2–4 pseudo-channels of one stack.
- O4 needs 4 stacks a die at 3.6 TB/s.

**DFlash.** No Qwen drafter, verify or accept RTL exists. `ot_hdc_lane_copy.sv` is an area probe that nothing instantiates; the only working lane multiplier is V4.1's.

**Generated wrapper.** `ot_hdc_core_vsu.sv` is stale against `tools/gen_hdc_core_top.py --check`.

## 7. Gap table

Size: **none** means no RTL change; **S** a parameter or a local edit; **M** a new or reworked block within one module family; **L** a new subsystem or a cross-module datapath change. Owner: Codex for every RTL, ISA, program-generator and gate item; Claude for the model- and golden-side items.

<!-- gap-table:begin -->
| ID | Block | Current RTL | Required | Size | Owner |
|---|---|---|---|---|---|
| G1 | ROM weight word and image | wrom_q is G x W x 16 bits: one BF16 a lane (ot_hdc_core.sv, ot_hdc_matvec.sv); hdc_program.place_matrix writes BF16 top halves; 16 bits a lane also in hbm_weight_image, pack_lanes(w,16) and hdc_timing.price_hbm | one signed INT8 code a lane a cycle: 128 bits a group a cycle, 98,304 B a cycle a die; image writer packs INT8 codes of the norm-folded matrices | M | Codex |
| G2 | Weight decode to the MAC operand | {wrom[16l+:16], 16'h0}: BF16 widened to binary32 (ot_hdc_matvec.sv) | INT8 code to an exact BF16/FP32 operand (every code -128..127 is exact in BF16), no rounding | S | Codex |
| G3 | MAC lane and accumulation | ot_hdc_bmul exact BF16 x BF16 -> FP32, ot_hdc_fadd RNE circulating, K-split chunks + pairwise ot_hdc_qadd tree | unchanged: INT8 x BF16 products are exact in FP32 (<= 15 significant bits), accumulation order is the golden's; a narrower INT8 x BF16 multiplier is a power lever, not a requirement | none | Codex |
| G4 | Per-output-channel scale multiply | none: the matvec result (lvl[LG] -> o_data) is the FP32 sum | one FP32 x BF16 RNE multiply per output row after the split tree and before argmax / writeback / the TP exchange; >= 47 outputs a cycle a die sustained (233 at m = 5), bursts up to (G/S) x W = 1,536; scale table 1.90 MB a die incl. lm_head, embedding and drafter | M | Codex |
| G5 | Lane copies (m = 5) and verify slots | ot_hdc_lane_copy.sv is an area probe, instantiated nowhere; one x operand a group; no Qwen verify slots | 4 MAC-only copies a lane (393,216 copy lanes a die) sharing the group's weight word; 5 x operands a group a cycle; 5 accumulators and results a lane; the KV word shared by 5 slots' scores and P.V with the block's causal mask | L | Codex |
| G6 | Matrix engine size and split rule at 6,144 groups | reduced vehicle G = 4 (8 in one campaign); spec 8,192 (a power of two); golden split_for packs ceil(tiles x S / G), the RTL floor(G / S) tiles a round | 6,144 groups a die (not a power of two): the golden and the RTL must choose the same K-split (they differ for the drafter fc slice: golden S = 4096, RTL rule S = 1024) | S | Codex |
| G7 | Stream unit | ot_hdc_vstream SW lanes (reduced gates SW = 16), R-ARITH reductions, embedding row read as BF16 | SW = 1,024 a die; norms and residuals replicated on both dies; 5 slots' elementwise work in the verify (48,960 cycles a step at SW = 1,024); embedding row as INT8 + scale (exact product) | M | Codex |
| G8 | KV path per die | ot_hdc_qwen_kv_system: one 32-B HBM request port, one outstanding request (phys arbiter); HBM model of 2-4 pseudo-channels of one stack; FP8 E4M3 KV | 4 HBM3E stacks a die at 3.6 TB/s sustained (3,277 B a cycle), its 4 KV heads; a ring of one layer of the die's KV (8.4 MB at 8K) + refresh cover (9.65 MB); 5 new rows a head a layer in the verify | L | Codex |
| G9 | UCIe TP-2 collectives | rtl/rom ot_rom_oneshot_allreduce (N-parametric, rank-order FP32 fold, credits), ot_rom_tp_seq, ot_rom_ucie_link; run only at D = 4 with the scalar ot_hdc_core (SU_VEC = 0) | TP-2 with the vector core: 2 all-reduces a layer of H FP32 partials (16 KiB a direction; 80 KiB at B = 5), argmax gather, embedding-row handoff; <= ~19 cycles exposed an exchange (1,251 cycles a token in the O4 rate); no credit round trip on the chain | M | Codex |
| G10 | Embedding and lm_head | embedding BF16 in wrom read by the stream unit; lm_head BF16 rows, matvec argmax over the unscaled result; argmax gather in ot_rom_tp_seq | INT8 rows + BF16 row scales; vocabulary split 75,968 rows a die; scale before the argmax compare; per-slot argmax for 5 verify slots and the drafter's 4 draft slots | M | Codex |
| G11 | DFlash drafter and accept | no Qwen drafter, verify or accept RTL (ot_hdc_accept.sv is instantiated only by the V4.1 cores) | drafter (fc 4096 x 20480 + 5 layers, INT8, TP-2) on the same engine and copies within 26,677 cycles a step; target hidden-state taps of 5 layers; accept/commit within 10 cycles | L | Codex |
| G12 | ISA and program generator | ME fields carry no weight format or scale base; place_matrix BF16; --tp emits per-die images but NORM_FOLD is off for tp > 1; no slot count or drafter program | 8-bit images and a scale table; TP-2 program with norm fold; verify-slot and drafter programs from the same source | M | Codex |
| G13 | Golden model (hdc_golden.py) | BF16 weights only, no quantiser; decode_token_tp unfolded norms and BF16 KV | INT8 codes + per-row BF16 scales with the post-accumulation contract; TP-2 with NORM_FOLD and FP8 KV; the scale's order around the fold pinned; B = 5 verify and drafter golden | M | Claude |
| G14 | Quality harness 8-bit mode | w8 mode (g_contract_w8, e_full_w8): codes x BF16 summed in the golden K-split order, one scale multiply after the sum; 0 of the 960 section 3.2 outputs differ from the contract (the group formats still scale every product); the 8-bit quality verdict is not yet run | a per-channel INT8 mode that scales after the chunk-tree sum, bit-exact with G13; the 8-bit quality verdict (<= 2% perplexity, <= 1 MMLU point) and DFlash acceptance at 8 bits | S | Claude |
| G15 | Timing and performance models | O4 priced per die (qwen3_8bit_design): calibrated replay of one die's TP-2 slice at 6,144 groups, 73 FP32-partial exchanges (1,407 cycles) + embedding handoff, 5-cycle scale stage, golden K-splits; the verify at m = 5 on the spec chain (a calibrated-core estimate beside it) | per-die TP-2 replay at 6,144 groups with the scale stage and FP32 partials; verify at m = 5 on the calibrated core | M | Claude |
| G16 | Reduced vehicle | every RTL gate uses the BF16 random reduced checkpoint (hidden 128, 4 layers) | an INT8-quantised reduced vehicle (codes + non-trivial row scales) the golden and the gates share | S | Claude |
| G17 | Reduced two-die gates | package TP bench at D = 4 with scalar cores; no two-die vector-core gate; no DFlash gate | two gates on one program: autoregressive (m = 1) and DFlash verify (m = 5, B = 5), TP-2, bit-exact tokens and KV against the golden | M | Codex |
<!-- gap-table:end -->

## 8. Golden and ISA changes, and the decisions they need

**For 8-bit weights.**

- **Golden (G13).** The golden gains INT8 codes and per-row BF16 scales, quantised from the norm-folded BF16 matrices for q, k, v, gate and up (C1). `matvec` of the codes is followed by one `mul` by the scale (C3), then the existing `mul` by r (C4). The embedding becomes an exact code x scale (C5). The lm_head's argmax runs over scaled logits (C6).
- **Quality harness (G14).** The same arithmetic becomes a harness mode, so that the quality bar and the RTL judge one arithmetic.
- **Reduced vehicle (G16).** The quantised reduced vehicle needs non-trivial scales. The current vehicle's RMSNorm gains are all ones, and a unit-scale vehicle would not exercise C3/C4.
- **ISA and program generator (G12).** The image writer packs INT8 lanes and places a scale table. How the engine locates a matrix's scales (an ISA field, an implicit base, a parallel ROM) is the contract's choice.

**For the two-die split.**

- `Model.decode_token_tp` and `hdc_program.Layout(tp, die)` already carry the TP-2 slicing:
  - QKV and gate/up by output rows (16 query heads and 4 KV heads a die, with no KV replication at TP-2);
  - o and down by input columns, with the rank-order fold;
  - the lm_head by vocabulary, with the argmax gather.
- They need three changes:
  - the norm fold at tp > 1 (the vector core's arithmetic);
  - FP8 KV in the TP path;
  - the INT8 terms above.
- The DFlash verify and the drafter need a golden at B = 5 with the block-causal attention. The O4 figures assume one.

**Decisions for the contract owner.**

| ID | Decision | Options and consequence |
|---|---|---|
| D1 | TP-2 or a contiguous layer cut | The O4 rates need TP-2. The best contiguous cut (P = 20) runs at 5,959.6 tok/s autoregressive (0.574x) and 12,461.0 tok/s with DFlash (0.753x) at batch 1 (section 1.1). |
| D2 | The scale's order around the TP fold (C7) | Scale each die's partial, then fold; or fold, then scale once. They differ in 83 of 192 down rows (at most 20 ulp). The golden pins one. |
| D3 | FP32 or BF16 partials over UCIe | FP32 is the golden today (1,407 cycles a token). BF16 halves the bytes, saves 156 cycles, and is a golden and quality change. |
| D4 | The K-split rule at 6,144 groups | The golden packs fractionally and the RTL tiles whole. They agree on every target matrix and differ on the drafter fc. One rule must serve both. |
| D5 | Embedding placement | Under TP-2, split by vocabulary with the O4 ledger: one handoff a token, about 12 cycles. Replicating it costs 34.1 mm² a die against 28.21 mm² of slack, so it does not fit. Under a cut, it goes on die A (section 1.1). |

## 9. Reproduce

```
python3 tools/qwen3_o4_rtl_gaps.py            # writes results/arch/qwen3_o4_rtl_gaps.json (~15 s; real rows if the HF snapshot is present)
python3 -m pytest tests/test_qwen3_o4_rtl_gaps.py
```
