# Gating DeepSeek sparse attention

## The hole this closes

DeepSeek-V4-Flash's attention is sparse, and the ROM-versus-HBM ratios this
program publishes are quoted at 200,000 and 1,000,000 context tokens, where
which KV rows sparse selection picks decides essentially every byte moved.

Until this work, **no correctness gate had ever crossed a sparsity threshold.**
The two DeepSeek gates that existed were `TA-DS-CHAT-1` at 104 prompt tokens
and its 32-token prefix, and the model's sparsity has three thresholds that
both sit under.

Stated exactly, because the loose version is wrong in a way that matters: at 32
tokens the selection operator *does* execute. The `compress_ratio=4` layers
hold eight compressed groups, `ROUTE.INDEX_TOPK` ranks them, and it keeps all
eight. What never happened is a selection that *selected* — that clipped a
window, that read a `compress_ratio=128` compressed group, or that discarded a
candidate. The operator ran; sparsity did not.

| threshold | value | first crossed at |
|---|---|---|
| sliding window | `window_tokens` = 128 | 129 prompt tokens <!-- figure: 128 src="configs/models/deepseek-v4-flash-0731.json#metadata.operator_config.window_tokens" name="window tokens" --> |
| first `compress_ratio=128` group | ratio 128 | 129 prompt tokens |
| selection discards a candidate | `top_k` = 512 at ratio 4 | 2,052 prompt tokens <!-- figure: 512 src="configs/models/deepseek-v4-flash-0731.json#attention_groups[compression_ratio=4].top_k" name="csa top_k" --> |

At 32 and at 104 tokens the window covers the whole context, the 20
`compress_ratio=128` layers hold zero compressed groups, and the ranking in the
21 `compress_ratio=4` layers keeps every candidate it ranks, so its order never
reaches an operand. The committed
`TA-DS-CTX-*` ladder starts at 1,000 tokens — already about 31x longer than the
only prompt a backend has ever completed — so the ladder could state the
problem and not gate it.

## The rungs, and why these lengths

`tools/build_deepseek_v4_context_threshold_workloads.py` builds the rungs
*between*. Every length is computed from the pinned profile by
`threshold_rungs()`; none is typed in. Each rung is built by the same
`compiler.workloads.deepseek_v4.build_context_workload` and the same digest rule
as the 1,000-to-200,000 ladder, from the same public-domain corpus, so these are
lower rungs of that ladder rather than a different question. The derived
prompts are committed in
`results/abi3/deepseek_v4_context_threshold_workload_pins.json`, because
`build/` is not in the repository.

| rung | tokens | what it crosses that 104 tokens does not |
|---|---|---|
| `TA-DS-CTX-129-1` | 129 | the window excludes a position for the first time; the ratio-128 layers hold their first compressed group <!-- figure: 129 src="results/abi3/deepseek_v4_context_threshold_workload_pins.json#rungs.window_and_coarse_first_group.tokens" name="rung 129" --> |
| `TA-DS-CTX-160-1` | 160 | the window excludes a position for 32 queries; the prefill circular-window commit splits at a non-zero cutoff <!-- figure: 160 src="results/abi3/deepseek_v4_context_threshold_workload_pins.json#rungs.window_clipping_with_split_write.tokens" name="rung 160" --> |
| `TA-DS-CTX-256-1` | 256 | the prefill commit lands on a zero cutoff, the boundary case of that split; two ratio-128 groups <!-- figure: 256 src="results/abi3/deepseek_v4_context_threshold_workload_pins.json#rungs.window_wrap_zero_cutoff.tokens" name="rung 256" --> |
| `TA-DS-CTX-2052-1` | 2052 | selection **discards** for the first time: 513 candidates, 512 kept <!-- figure: 2052 src="results/abi3/deepseek_v4_context_threshold_workload_pins.json#rungs.index_topk_prunes_ratio_4.tokens" name="rung 2052" --> |

The token streams of the rungs do **not** nest, and the pin records how far
each pair agrees rather than requiring it: nesting the prose does not nest the
tokens, because the tokenizer re-merges across a truncation boundary. The
129-token rung shares 127 leading token IDs with `TA-DS-CTX-1K-1`. <!-- figure: 127 src="results/abi3/deepseek_v4_context_threshold_workload_pins.json#token_prefix_agreement_with_parent_rung.agreed['TA-DS-CTX-129-1']" name="129 token prefix agreement" -->

Requiring token nesting would be requiring something the committed ladder never
had, so it is measured and reported instead of asserted. Each rung's gold is
produced for that rung's own token IDs, which is what makes the comparison
sound.

## A correction found while deriving the rungs

The first version of the rung rule read `operator_config.index_topk` — one
model-wide 512 — and derived a fifth rung at 65,664 tokens, "where `index_topk`
starts to prune the `compress_ratio=128` layers". **There is no such length.**
The released `Attention.__init__` builds an `Indexer` only when
`compress_ratio == 4`; the ratio-128 layers fall through to
`get_compress_topk_idxs`, which enumerates every completed compressed group
with no ranking and no `top_k`, at any context.

The pinned profile already said so, in a field the rule was not reading: the
`compression_ratio=4` group carries `top_k: 512` and `kind: compressed_sparse`,
and the `compression_ratio=128` group carries `top_k: 0` and
`kind: compressed_dense`.

<!-- figure: 0 src="configs/models/deepseek-v4-flash-0731.json#attention_groups[compression_ratio=128].top_k" name="hca top_k is zero" --> The ratio-128 group's `top_k` is 0.

This is the project's recurring defect class in miniature: a legal value, no
trap, nothing refused, and a threshold invented for a mechanism the model does
not have. `threshold_rungs()` now derives every pruning rung from the per-group
`top_k`, contributes no rung for a group that ranks nothing, and records why in
`no_pruning_rung_for_compression_ratios`. What should have refused it now does:
`_profile()` cross-checks the `attention_groups` layer census against
`operator_config.compress_ratios` and fails the build when the two pinned
statements about this model disagree.

## Oracle gold

`results/abi3/deepseek_v4_reference_oracle_threshold.json`, produced by
`tools/run_deepseek_v4_reference_oracle.py --workloads
build/workloads/deepseek-v4-flash-0731-threshold --engine-per-workload
--measure-kv` on the pinned snapshot. Eight generated tokens per rung, greedy
lowest-id argmax, the official fp8 expert path. It is an **external
comparator**: per ADR-003 §18 it supplies no activation to the accelerator and
produces no accelerator token.

| rung | first gold token |
|---|---|
| `TA-DS-CTX-129-1` | 6729 <!-- figure: 6729 src="results/abi3/deepseek_v4_context_threshold_workload_pins.json#gold.workloads['TA-DS-CTX-129-1'].first_generated_token_id" name="gold 129" --> |
| `TA-DS-CTX-160-1` | 201 <!-- figure: 201 src="results/abi3/deepseek_v4_context_threshold_workload_pins.json#gold.workloads['TA-DS-CTX-160-1'].first_generated_token_id" name="gold 160" --> |
| `TA-DS-CTX-256-1` | 61729 <!-- figure: 61729 src="results/abi3/deepseek_v4_context_threshold_workload_pins.json#gold.workloads['TA-DS-CTX-256-1'].first_generated_token_id" name="gold 256" --> |
| `TA-DS-CTX-2052-1` | 414 <!-- figure: 414 src="results/abi3/deepseek_v4_context_threshold_workload_pins.json#gold.workloads['TA-DS-CTX-2052-1'].first_generated_token_id" name="gold 2052" --> |

## What a backend run costs, stated plainly

The one completed DeepSeek backend run is 32 prompt tokens in 4,353 s. Taking
that rate as linear in prompt tokens — a floor, because attention is
superlinear — the ladder costs about 4.9 h at 129 tokens, 6.0 h at 160, 9.7 h
at 256, 78 h at 2,052, and 315 days at 200,001.

<!-- figure: 17549.6 src="results/abi3/deepseek_v4_context_threshold_workload_pins.json#rungs.window_and_coarse_first_group.linear_backend_estimate_seconds" name="129 backend floor seconds" --> The 129-token floor is 17,549.6 s.

So the two window thresholds are gateable in a session and the pruning
threshold is not. That is stated here rather than worked around.

## A gate on the KV traffic, not only on the token

A DeepSeek backend run had always been judged on one thing: did the token match
the oracle. The counters that say how much KV the run actually touched were
recorded and read by nothing.

`tools/check_deepseek_v4_context_gate.py` closes that. It states the sparse
traffic the pinned profile implies, exactly — for a query at 0-based position
`p` in a layer with window `W`, ratio `r` and per-group `top_k`, the gathered
rows are `min(p + 1, W) + min(top_k or all, (p + 1) // r)` — and requires the
executed counters to *equal* it. Not a tolerance: the quantities are integers
and the model is closed-form, so a disagreement is a defect.

The model was not fitted to anything, and it is checked on both arms against
two independent things.

<!-- figure: 25224 src="results/abi3/accelerator_tokens/deepseek_v4_flash_rom_p32_raw.json#counters['attention.context_positions']" name="p32 gathered positions" -->
The 32-token prefill gathered 25,224 positions, which is what the model says.

<!-- figure: 25829376 src="results/abi3/accelerator_tokens/deepseek_v4_flash_rom_p32_raw.json#counters['attention.kv_bytes_read']" name="p32 kv bytes" -->
It read 25829376 KV bytes, which is that count times the 1,024-byte BF16
latent row, and is what the model says.

Its **decode** arm has no accelerator run to be checked against, because there
are none. It is checked against the released implementation instead: the
reference oracle's `--measure-kv` records, per layer, how many
(layer, position) pairs its attention actually visited at each decode step, and
the checker compares the model to that number layer by layer rather than in
aggregate, where a compensating pair of errors could hide.

<!-- figure: 1204 src="results/abi3/deepseek_v4_context_gate.json#decode_arm_cross_check.total_layer_comparisons" name="decode cross-check comparisons" -->
<!-- figure: 28 src="results/abi3/deepseek_v4_context_gate.json#decode_arm_cross_check.decode_steps_compared" name="decode cross-check steps" -->
That is 1204 per-layer comparisons over 28 decode steps, at contexts from 130
to 2,059 — including 2,053 and above, where the ratio-4 selection is
discarding.

<!-- figure: 0 src="results/abi3/deepseek_v4_context_gate.json#decode_arm_cross_check.total_layer_mismatches" name="decode cross-check mismatches" -->
The mismatch count is 0.

<!-- figure: "True" src="results/abi3/deepseek_v4_context_gate.json#decode_arm_cross_check.all_agree" name="decode cross-check verdict" -->
`decode_arm_cross_check.all_agree` is True.

This says the analytical traffic model is right about what the *released
implementation* reads per decode step, at the pruning threshold. It says
nothing about what a backend reads there, because no backend has read anything
there.

### How much the gate can actually see

An equality check is a gate only where the quantity moves when the thing under
test breaks, so the checker states the margin instead of asserting the power.
For each pinned prompt length it computes what the gathered-position counter
would be under the two ways the sparse path can fail while still producing a
plausible run — a sliding window that never clips, and compressed segments that
are never attended.

| prompt tokens | correct | if the window never clipped | margin |
|---|---|---|---|
| 32 | 25,224 | 25,224 | **0** |
| 129 | 403,560 | 403,603 | 43 |
| 160 | 598,156 | 620,860 | 22,704 |
| 256 | 1,232,808 | 1,587,816 | 355,008 |
| 2,052 | 22,295,808 | 101,925,358 | 79,629,550 |

<!-- figure: 0 src="results/abi3/deepseek_v4_context_gate.json#discrimination_ladder.by_workload['TA-DS-CHAT-1-P32'].if_the_window_did_not_clip_margin" name="32-token window discrimination" -->
**At 32 prompt tokens the margin is 0.** A DeepSeek deployment whose sliding
window never clipped at all would produce a bit-identical counter at the length
of the only gate this program had. That is not an argument that the old gate
was careless; it is arithmetic. A prompt shorter than the window cannot
distinguish a window from no window, and every DeepSeek gate that existed was
shorter than the window.

<!-- figure: 22704 src="results/abi3/deepseek_v4_context_gate.json#discrimination_ladder.by_workload['TA-DS-CTX-160-1'].if_the_window_did_not_clip_margin" name="160-token window discrimination" -->
At 160 tokens the same failure moves the counter by 22,704 positions, and the
checker requires equality.

## What the gate found: DeepSeek decode does not run at all

The first thing run through the new gate was the cheapest possible decode: the
8-token prefix `TA-DS-CHAT-1-P8`, two new tokens. Its prefill succeeded and
emitted token 14, which is the oracle's. **Its first decode step trapped.**

<!-- figure: "decode step 1 failed: GROUPED_CONCAT output view 1417 dims (129, 512) differ from the axis-0 concatenation (131, 512)" src="results/abi3/deepseek_v4_rom_ta-ds-chat-1-p8_decode_execution.json#record.failure" name="DeepSeek decode trap" -->
The recorded failure is `decode step 1 failed: GROUPED_CONCAT output view 1417
dims (129, 512) differ from the axis-0 concatenation (131, 512)`, trap class
`DESCRIPTOR_OR_ADDRESS`.

Read the two numbers. The KV row space a decode step assembles is the request's
own row, then the 128-row window, then the committed compressed prefix:
`1 + 128 + 9 // 4 = 131` rows at a context of nine. The output view it is
written into presents `129`. 129 is `1 + 128`: the compressed segment is sized
from the request's span, and a decode step's span is one. In prefill the span
*is* the context and the two agree, which is why every DeepSeek run this
repository has ever recorded — all of them prefill-only — got past it.

The counters localise it exactly. The aborted step left `attention.heads` 128
above the model and `attention.context_positions` 18 above it: two layers of 64
heads, and `2 x min(9, 128) = 18` gathered positions. Those are layers 0 and 1,
the only two layers that do not compress. The trap is in layer 2, the first
`compress_ratio=4` layer — the first layer whose KV row space has a compressed
segment at all.

### This was declared, not undiscovered

Both backends already say it, in the same place and in the same words. The
neutral IR declares a dedicated symbol `attention_rows_ratio4` whose maximum is
`context + 128 + context // 4`, and both backends bind it to the *span*:

- `compiler/backends/rom/common/program.py`, `SYMBOL_BY_NAME`:
  `"attention_rows_ratio4": RequestAxis(Symbol.SPAN_TOKENS, 4, 5, 128)`, above
  the comment *"Decode binds the two symbols apart and A18 is exact for an
  affine function of one, so a decode of a compressed layer needs a phase split
  that prefill does not; it is not solved here because it is not needed here."*
- `compiler/backends/hbm_sram/plan.py`, `REQUEST_EXTENT`:
  `"attention_rows_ratio4": RequestExtent(numerator=5, unit=4, bias=128)`,
  above *"``context_*`` names resolve against the span deliberately. In prefill
  the two coincide; in decode a compressed layer's join is a sum over two
  different symbols, which wire format section 12.8 places outside the
  amendment."*

So this document does not claim to have found an unknown defect. It claims
three things the comments do not:

1. **It is reached.** A declared gap and an executed trap are different
   evidence, and until now nothing had run a DeepSeek decode step to find out
   which this was. The record above is the first.
2. **"It is not needed here" is wrong.** Every number this program publishes
   about DeepSeek KV traffic at 200,000 and 1,000,000 tokens is a *per decode
   step* number. The decode step is the claim. A gap that only bites in decode
   bites exactly where the argument lives.
3. **It is an ABI limitation, not a typo.** The row space is
   `span + window + context // ratio`, an affine function of *two* request
   symbols, and amendment A18's extent is an affine function of *one*. No
   binding of the existing grammar is correct; the fix is a phase split or an
   amendment, which is why neither backend approximated it.

Both backends carry it identically, so it does not bias the ROM-versus-HBM
comparison — it disables both sides of it equally.

On point 3 there is one thing worth recording, and it is a *suggestion, not a
result*: nothing here implements it and nothing here validates it. A decode
step's span is always one, so in decode the row space
`span + window + context // ratio` is `context // ratio + (window + 1)` — an
affine function of `context_length` alone, which A18 admits as it stands. The
gap may therefore be a per-phase binding of `attention_rows_ratioN` rather than
an amendment. It would have to be made identically in both backends, and
re-validated by a run, before anyone should believe it.

Stated plainly: **no DeepSeek decode step has ever executed on either backend**,
and none can at any context of four tokens or more, which is every context a
decode step is ever reached at. It **fails closed** — the ABI's own shape check
refuses the view rather than reading wrong rows, so the recurring silent-defect
class did not strike here. The general condition is `span < context`, not
"decode" as such, so a chunked prefill has the same shape; that is *derived
from the failure, not executed*, and is recorded as unvalidated below.

## The regime no end-to-end run reaches, and what does cover it

`tools/audit_deepseek_v4_index_selection.py` gates the *selection operators* in
the regime the published ratios live in. It executes `ROUTE.INDEX_TOPK` and
`ROUTE.WINDOW_INDEX` through a real ABI 3.0 deployment on the functional
device — not by calling an engine with hand-made Python state — at the model's
own `top_k`, window and compression ratios, and compares the choice against the
released implementation transcribed from the pinned `inference/model.py`
(`Indexer.forward`, `get_compress_topk_idxs`, `get_window_topk_idxs`, and the
`torch.cat` in `Attention.forward`).

**The two sides do not number KV rows the same way, and the audit checks the
map rather than assuming it.** The released `Attention.forward` attends over
`cat([kv, kv_compress])` in prefill, so compressed group `g` is row
`seqlen + g`; in decode it attends over the circular cache, so `g` is row
`window + g`. The accelerator's `ATTENTION.SPARSE` operand is the request's own
rows, then the window, then the compressed rows in both phases, so `g` is row
`span + window + g`. Both are internally consistent. The audit compares which
window positions and which compressed groups each side selects, and requires
the counts to match, so a defect that moved the compressed segment would break
the check rather than slip through it. The first version of the audit compared
raw row numbers and reported all eighteen cases disagreeing, including a case
with no ranking at all; that was the address map, not the selection, and
diagnosing it before believing it is the point.

<!-- figure: 24 src="results/abi3/deepseek_v4_index_selection_audit.json#case_count" name="index selection audit cases" -->
Result: 24 cases.

<!-- figure: "True" src="results/abi3/deepseek_v4_index_selection_audit.json#all_agree" name="index selection audit verdict" -->
`all_agree` in the artifact is True.

This establishes: for the same index scores, the accelerator's selection
operators name the same KV rows the released implementation names, at the
model's real parameters, in the pruning regime, at contexts up to 1,000,001.
The audit was run twice in separate processes and the artifact reproduces
byte-identically, so it is a comparator and not one observation.

It does **not** establish that the accelerator computes the same *scores*
(`INDEX_SCORE` is a different operator), nor end-to-end token agreement at any
context it did not run.

## A property of the model the audit measured on the way

<!-- figure: 32639 src="results/abi3/deepseek_v4_index_selection_audit.json#score_value_space.bf16_positive_finite_values" name="bf16 positive finite values" -->
The released index score is BF16, which has 32,639 positive finite values.

<!-- figure: 130556 src="results/abi3/deepseek_v4_index_selection_audit.json#score_value_space.context_above_which_ratio_4_candidates_cannot_all_differ" name="context above which ties are forced" -->
Above a context of 130,556 the `compress_ratio=4` layers hold more candidates
than that, so by pigeonhole some candidates necessarily carry equal scores, and
the released model does not say which of two equally-scored groups the top-512
keeps. Both contexts this program quotes are above that line.

What stays determined is *how many* rows are read — 512 per query per csa layer
— which is what the byte-traffic model uses, so the roofline is unaffected.
What is not determined is *which* rows, and therefore neither is the generated
token at those contexts, on any implementation including the released one. A
future 200,000-token token-identity claim would be claiming something the model
does not define; a byte-traffic claim would not.

## Neither arm of this gate can see a wrong index score

The gate has two arms: the token must equal oracle gold, and the executed
KV-traffic counters must equal the closed-form model. Neither arm is sensitive
to the *index scores* at any prompt length a backend has completed, and that is
not visible from either arm on its own. It is executed in
`tools/check_deepseek_v4_ctx_score_visibility.py`, which runs
`ROUTE.INDEX_TOPK` on the functional device **twice per case** with two
different BF16 score blocks and compares the KV-row array it emits, byte for
byte.

**The counter arm is blind at every context, without exception.** The rows a
query gathers are `min(p + 1, W) + min(top_k, (p + 1) // r)`. Every term is
position arithmetic; no score appears. So a deployment that computed index
scores by any rule at all — a constant included — gathers the same number of
rows and records the same counters.

<!-- figure: "True" src="results/abi3/deepseek_v4_ctx_score_visibility.json#kv_counter_is_blind_to_index_scores_at_every_case" name="counter arm blind to scores" -->
`kv_counter_is_blind_to_index_scores_at_every_case` is True: in every case the
two runs' counters — `route.topk_candidates`, SRAM bytes read and written,
instructions retired — are identical, at 200,000 and at 1,048,576 tokens as
much as at 129. The counter arm gates *how many* rows are read, which is what
the byte-traffic model needs and is the quantity the published ratios rest on.
It cannot gate *which* rows, anywhere. That is a property of the quantity, not
a weakness of the checker, and no stronger counter would fix it.

**The token arm is blind below the pruning threshold.** A ranking layer
discards a candidate only once it has more than `top_k` of them, so from
`r * (top_k + 1)` prompt tokens.

<!-- figure: 2052 src="results/abi3/deepseek_v4_ctx_score_visibility.json#thresholds['4'].first_prompt_length_that_prunes" name="flash score visibility threshold" -->
For Flash at ratio 4 and `top_k` 512 that is 2,052 tokens.
<!-- figure: 4100 src="results/abi3/deepseek_v4_ctx_score_visibility_pro.json#thresholds['4'].first_prompt_length_that_prunes" name="pro score visibility threshold" -->
For Pro, whose `top_k` is 1024, it is 4,100.

Below it the ranking keeps every candidate it ranks, and `ROUTE.INDEX_TOPK`
emits the selection *compacted and sorted ascending* — so neither the
membership of the set nor its order carries any score information, and the
token cannot move. Executed, at every rung a backend can reach:

| rung | prompt tokens | `index_score_can_move_the_token` |
|---|---:|---|
| `TA-DS-CTX-129-1` | 129 | False <!-- figure: "False" src="results/abi3/deepseek_v4_ctx_score_visibility.json#by_prompt_length['TA-DS-CTX-129-1'].index_score_can_move_the_token" name="129 score visibility" --> |
| `TA-DS-CTX-160-1` | 160 | False <!-- figure: "False" src="results/abi3/deepseek_v4_ctx_score_visibility.json#by_prompt_length['TA-DS-CTX-160-1'].index_score_can_move_the_token" name="160 score visibility" --> |
| `TA-DS-CTX-256-1` | 256 | False <!-- figure: "False" src="results/abi3/deepseek_v4_ctx_score_visibility.json#by_prompt_length['TA-DS-CTX-256-1'].index_score_can_move_the_token" name="256 score visibility" --> |
| `TA-DS-CTX-2052-1` | 2052 | True <!-- figure: "True" src="results/abi3/deepseek_v4_ctx_score_visibility.json#by_prompt_length['TA-DS-CTX-2052-1'].index_score_can_move_the_token" name="2052 score visibility" --> |

At 129, 160 and 256 the emitted KV-row array is byte-identical under two
different score blocks. **So the three rungs this ladder makes reachable close
the window and compressed-segment holes and leave the score hole exactly where
it was.** They are still worth running — the window discrimination margin above
is 43, 22,704 and 355,008 positions, and it was 0 at every gate that existed
before — but they must not be read as gating sparse selection *end to end*.

The half of this with teeth is the other direction. At 2,052 and above the two
score blocks produce *different* rows, so the check would fail if
`ROUTE.INDEX_TOPK` ignored its score input — the only check in this repository
that would. It passes.

<!-- figure: 11 src="results/abi3/deepseek_v4_ctx_score_visibility.json#case_count" name="score visibility case count" -->
<!-- figure: "True" src="results/abi3/deepseek_v4_ctx_score_visibility.json#all_cases_agree_with_the_position_arithmetic" name="score visibility verdict" -->
11 cases for Flash, spanning 129 to 1,048,576 tokens, and
`all_cases_agree_with_the_position_arithmetic` is True.
<!-- figure: 3 src="results/abi3/deepseek_v4_ctx_score_visibility_pro.json#case_count" name="pro score visibility case count" -->
<!-- figure: "True" src="results/abi3/deepseek_v4_ctx_score_visibility_pro.json#all_cases_agree_with_the_position_arithmetic" name="pro score visibility verdict" -->
3 cases for Pro, at 4,100, 200,000 and 1,048,576, likewise True.

### Why nothing expressed this before

The discrimination ladder asks what the counter would be under two faults — a
window that never clips, and compressed segments never attended — and both move
it. A wrong score moves nothing, so a ladder built out of counter margins had
no way to ask the question. The selection audit *does* vary scores, but it
feeds the same synthetic block to both sides and says so in its `not_a_claim`.
Each artifact was correct about its own scope; the gap was between them.

## What is still not established

Stated exhaustively, because the value of a gate is bounded by what it does not
cover.

- **No accelerator run above 256 prompt tokens.** The 2,052-token rung — the
  first context at which selection discards — has gold and no accelerator run.
  At the one measured backend rate it is about 78 hours. The 200,000-token
  contract is about 315 days at that rate and is not reachable by this route at
  all; it needs a faster functional path, not a longer session.
- **No accelerator decode step, at any context.** See above; it traps.
- **No chunked prefill.** The claim that `span < context` is the general
  condition is read off the failure, not executed.
- **The index *scores* are not gated, and no reachable run can gate them.**
  The audit fixes the scores and compares the selection. `INDEX_SCORE` — the
  64-head query-key product, the ReLU, the head-weighted sum, and the BF16
  roundings in all of it — is a separate operator and nothing here tests it
  against the released one. Worse than untested: the section above executes
  the demonstration that the KV-counter arm cannot see a score defect at *any*
  context, and the token arm cannot see one below 2,052 prompt tokens, which
  is every rung a backend has completed. Closing this needs a differential on
  `INDEX_SCORE` itself, or a 2,052-token backend run; adding rungs below 2,052
  cannot do it.
- **`ATTENTION.SPARSE`'s arithmetic at long context is not gated here.** The
  audit gates which rows are selected, not the online softmax over them.
- **Neither lane has produced a DeepSeek token at a length that crosses a
  sparsity threshold.** Both lanes now produce one below every threshold: ROM
  and HBM each emit 13806 for the 32-token prefix, which is oracle gold
  (commit `6f5f5fd`). That is the whole of the DeepSeek end-to-end evidence,
  and 32 tokens is under the window, under `top_k`, and under one compressed
  group. The `TA-DS-CTX-129/160/256` runs on both lanes are what change this
  and are recorded below when they land.
- **RTL is untouched.** This is the functional-simulator path.
- **The token at 200,000 and 1,000,000 tokens is not defined by the model**, as
  the BF16 tie argument above shows, so no future run can validate one. Byte
  traffic can be; token identity cannot.
