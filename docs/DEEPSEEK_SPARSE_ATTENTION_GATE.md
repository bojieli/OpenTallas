# Gating DeepSeek sparse attention

## The hole this closes

DeepSeek-V4-Flash's attention is sparse, and the ROM-versus-HBM ratios this
program publishes are quoted at 200,000 and 1,000,000 context tokens, where
which KV rows sparse selection picks decides essentially every byte moved.

When this work began, **no correctness gate had ever crossed a sparsity
threshold.** The two DeepSeek gates were `TA-DS-CHAT-1` at 104 prompt tokens and
its 32-token prefix; both sat below all three of the model's sparsity thresholds.
Current accelerator captures now include short-context decode, but still
no successful current capture reaches the first threshold at 129.

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
longest prompt a current backend capture has completed — so the ladder could
state the problem and not gate it.

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

The ladder's cost projection was calibrated from the first raw DeepSeek backend
run: 32 prompt tokens in 4,353 s. It is a historical planning rate, not the
wall time of the current governed captures. Taking it as linear in prompt
tokens — a floor, because attention is superlinear — the ladder costs about
4.9 h at 129 tokens, 6.0 h at 160, 9.7 h at 256, 78 h at 2,052, and 315 days at
200,001.

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

The governed HBM capture now checks the model's **short-context decode** arm at
contexts 33 through 35. Its aggregate counters are cluster totals over 32
nodes, not a logical single-node count. The v2 gate therefore requires the
simulator's measured `node_counters`, checks the model against every node, and
separately checks the aggregate against 32 copies. It never divides a cluster
total or infers a node count from a target name or capability maximum.

<!-- figure: "True" src="results/abi3/deepseek_v4_context_gate.json#all_pass" name="current DeepSeek context gate verdict" -->
The retained v2 result is `all_pass: True` and binds **32** measured node sets. <!-- figure: 32 src="results/abi3/deepseek_v4_context_gate.json#results[0].node_count" name="context-gate measured node count" -->
For `attention.context_positions`, the per-node minimum and maximum are both
**30,114** <!-- figure: 30114 src="results/abi3/deepseek_v4_context_gate.json#results[0].per_node_counter_summary['attention.context_positions'].minimum_observed" name="context positions per-node minimum" --> <!-- figure: 30114 src="results/abi3/deepseek_v4_context_gate.json#results[0].per_node_counter_summary['attention.context_positions'].maximum_observed" name="context positions per-node maximum" -->,
the independently retained cluster total is **963,648** <!-- figure: 963648 src="results/abi3/deepseek_v4_context_gate.json#results[0].observed_aggregate_counters['attention.context_positions']" name="context positions cluster total" -->,
and **0** nodes mismatch the model. <!-- figure: 0 src="results/abi3/deepseek_v4_context_gate.json#results[0].per_node_counter_summary['attention.context_positions'].mismatched_node_count" name="context position mismatched nodes" -->
For `attention.kv_bytes_read`, every node likewise records **30,836,736** bytes <!-- figure: 30836736 src="results/abi3/deepseek_v4_context_gate.json#results[0].per_node_counter_summary['attention.kv_bytes_read'].minimum_observed" name="KV bytes per-node minimum" --> <!-- figure: 30836736 src="results/abi3/deepseek_v4_context_gate.json#results[0].per_node_counter_summary['attention.kv_bytes_read'].maximum_observed" name="KV bytes per-node maximum" -->,
the cluster records **986,775,552** bytes <!-- figure: 986775552 src="results/abi3/deepseek_v4_context_gate.json#results[0].observed_aggregate_counters['attention.kv_bytes_read']" name="KV bytes cluster total" -->,
and again **0** nodes mismatch. <!-- figure: 0 src="results/abi3/deepseek_v4_context_gate.json#results[0].per_node_counter_summary['attention.kv_bytes_read'].mismatched_node_count" name="KV byte mismatched nodes" -->

That pass reaches at most context **35** <!-- figure: 35 src="results/abi3/deepseek_v4_context_gate.json#claim_boundary.maximum_accelerator_context_tokens_checked" name="maximum accelerator context checked" -->.
`accelerator_window_clipping_executed` and
`accelerator_index_pruning_executed` are both `False`; <!-- figure: "False" src="results/abi3/deepseek_v4_context_gate.json#claim_boundary.accelerator_window_clipping_executed" name="accelerator window-clipping execution verdict" --> <!-- figure: "False" src="results/abi3/deepseek_v4_context_gate.json#claim_boundary.accelerator_index_pruning_executed" name="accelerator index-pruning execution verdict" -->
the clean counter result is evidence about short-context execution, not a
claim that an accelerator crossed either threshold.

The threshold-regime decode arm is checked against the released implementation
instead: the reference oracle's `--measure-kv` records, per layer, how many
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
of the shortest retained accelerator gate. That is arithmetic, not a judgment
about the gate: a prompt shorter than the window cannot distinguish a window
from no window, and every current accelerator record remains shorter than the
window.

<!-- figure: 22704 src="results/abi3/deepseek_v4_context_gate.json#discrimination_ladder.by_workload['TA-DS-CTX-160-1'].if_the_window_did_not_clip_margin" name="160-token window discrimination" -->
At 160 tokens the same failure moves the counter by 22,704 positions, and the
checker requires equality.

## What the gate found first, and why that result is now historical

The first thing run through this gate was the cheapest possible decode: the
8-token prefix `TA-DS-CHAT-1-P8`, two requested new tokens. Its prefill emitted
the oracle's token 14 and its first decode trapped:

<!-- figure: "decode step 1 failed: GROUPED_CONCAT output view 1417 dims (129, 512) differ from the axis-0 concatenation (131, 512)" src="results/abi3/deepseek_v4_rom_ta-ds-chat-1-p8_decode_execution.json#record.failure" name="historical DeepSeek decode trap" -->
The recorded failure was `decode step 1 failed: GROUPED_CONCAT output view 1417
dims (129, 512) differ from the axis-0 concatenation (131, 512)`.
`GROUPED_CONCAT` presented 129 rows where the request row, 128-row window and
compressed prefix required 131. That retained artifact is valid evidence about
the deployment it ran, and it localised the first failing compressed layer. It
is **not** the status of the current deployment.

Commit `77f847c` implemented the repair the failure pointed to, identically in
both backends. A compressed-attention join is emitted once per phase: prefill
declares `5 * span / 4 + 128` (or the ratio-128 equivalent), while decode
declares `context / 4 + 129`; the chosen extent is propagated to the
`ATTENTION.SPARSE` consumer, and the predicates are proved disjoint rather than
assumed. No ABI field was approximated and no two-symbol expression was forced
into A18.

The current governed HBM capture executes one prefill and three decode
transactions, all `SUCCESS`/`NONE`, and produces the oracle prefix
`[13806, 345, 7472, 55560]`. The ROM capture also executes all four
transactions; it diverges numerically at token index 1, which is a separate
open correctness defect rather than the old structural trap. Therefore the
former sentence "DeepSeek decode does not run" is retracted. What remains true
is narrower and important: these are contexts 32 through 35, still below the
first window-clipping threshold at 129.

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

The other direction is checked too, and passes: at 2,052 and above the two
score blocks produce *different* rows, so this would fail if
`ROUTE.INDEX_TOPK` ignored its score input. That is not a new guarantee — the
selection audit above already compares the operator's choice against the
released `topk` on the same scores, and would also fail — but it is a cheap
independent one, and it is what makes the *negative* half meaningful: the
operator demonstrably reads its scores, so "the rows did not move" below 2,052
is a fact about the arithmetic and not about a dead input.

### And the 2,052-token rung would barely be a score gate either

Crossing the threshold is not the same as testing what is past it. A prefill
query at 0-based `q` sees `(q + 1) // 4` candidates, so it prunes only from
`q + 1 >= 2052` — at a prompt of exactly 2,052 tokens that is the *last query
and no other*.

<!-- figure: 1 src="results/abi3/deepseek_v4_ctx_score_visibility.json#by_prompt_length['TA-DS-CTX-2052-1'].prefill_queries_that_prune" name="2052 pruning queries" -->
<!-- figure: 1 src="results/abi3/deepseek_v4_ctx_score_visibility.json#by_prompt_length['TA-DS-CTX-2052-1'].candidates_discarded_at_final_query" name="2052 candidates discarded" -->
1 query out of 2,052 prunes, and it discards 1 candidate out of 513. The
executed experiment shows exactly that: at `prefill_ratio4_2052` a different
score block moves one row of the emitted array and no other.

So a 2,052-token backend run — about 35 hours of the measured rate, on each
lane — would buy a token that depends on the index scores through a single
discarded candidate in a single query. That is a real crossing and it is worth
almost nothing as a test of the score arithmetic. **The conclusion is that
lengthening the ladder is the wrong instrument.** A differential on
`INDEX_SCORE` against the released `Indexer.forward` costs no backend time and
tests every candidate of every query; the ladder cannot reach that regime at
any length this program can afford.

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

## What the first threshold run found, and what A25 changed

The retained `TA-DS-CTX-129-1` ROM artifact predates amendment A25. It ran
9,076 seconds, gathered the exact sparse rows, and then failed closed while
committing 129 rows into a 128-slot window:

<!-- figure: "prefill failed: state 353: committing 129 rows at cursor 0 with 0 already staged exceeds capacity 128" src="results/abi3/deepseek_v4_rom_ta-ds-ctx-129_execution.json#record.failure" name="historical 129 commit trap" -->
Its recorded failure was `prefill failed: state 353: committing 129 rows at
cursor 0 with 0 already staged exceeds capacity 128`.

<!-- figure: 403560 src="results/abi3/deepseek_v4_rom_ta-ds-ctx-129_execution.json#record.counters['attention.context_positions']" name="historical 129 gathered positions" -->
Its 403,560 gathered positions are the closed-form value for the first clipped
window, and its 355,008 heads are exactly 129 x 64 x 43. <!-- figure: 355008 src="results/abi3/deepseek_v4_rom_ta-ds-ctx-129_execution.json#record.counters['attention.heads']" name="historical 129 attention heads" -->
The attention counter arm was right; the state policy had no way to say that a
ring publishes `min(span, capacity)` rows.

A25 adds that exact `SATURATING` policy and derives it from the finished
deployment's ring-indexed scatter rather than from a backend name. Both
DeepSeek lanes now declare their sliding-window resources saturating, and the
functional device and RTL state controller implement the same circular commit.
The old failure artifact is not rewritten: it remains evidence about the old
deployment, while the current deployments carry the repair.

The repair makes the 129-, 160-, and 256-token rungs reachable in the current
ABI, but none has been rerun on a current accelerator deployment. The
2,052-token rung is still structurally unreachable: its compressed KV cache
has a group row axis, while `REQUEST_SPAN` tries to commit token rows; the ROM
lane first exceeds that cache at span 2,049. The 200,000- and 1,048,576-token
regimes remain unreachable by this path for the same class of reason one
resource later. Thus A25 removes the historical window trap without turning an
old failed run into current threshold evidence.

## What is still not established

Stated exhaustively, because the value of a gate is bounded by what it does not
cover.

- **No current accelerator run reaches a sparsity threshold.** The successful
  governed HBM record reaches context 35. The 129- and 160-token artifacts are
  historical pre-A25 failures, not reruns of the repaired deployment; the
  256-token rung has no accelerator artifact. The 2,052-token rung — the first
  context at which selection discards — has gold but is blocked by the
  compressed-cache commit policy as well as its runtime cost.
- **Decode is executed only below the window.** Three HBM and three ROM decode
  transactions now complete at contexts 33 through 35. No accelerator decode
  has run at 129 or above.
- **No accelerator chunked prefill.** The phase-specific extent repair covers
  the shape, but no current accelerator record exercises that path.
- **The index *scores* are not gated, and no reachable run can gate them.**
  The audit fixes the scores and compares the selection. `INDEX_SCORE` — the
  64-head query-key product, the ReLU, the head-weighted sum, and the BF16
  roundings in all of it — is a separate operator and nothing here tests it
  against the released one. Worse than untested: the section above executes
  the demonstration that the KV-counter arm cannot see a score defect at *any*
  context, and the token arm cannot see one below 2,052 prompt tokens, which
  is every context a current backend record has completed. Closing this needs
  a differential on
  `INDEX_SCORE` itself, or a 2,052-token backend run; adding rungs below 2,052
  cannot do it.
- **`ATTENTION.SPARSE`'s arithmetic at long context is not gated here.** The
  audit gates which rows are selected, not the online softmax over them.
- **Neither current lane has produced a token at a length that crosses a
  sparsity threshold.** A25 makes the first three rungs reachable, but they
  have not been rerun; 2,052 and the quoted long contexts remain blocked by
  the compressed-cache row-count gap. Below the thresholds HBM is
  oracle-identical for four tokens and ROM diverges at its second.
- **No RTL vector crosses the window.** RTL implements A25 and the shipped
  DeepSeek co-simulation executes its policy below the ring, where saturating
  and request-span commits are byte-identical. The counter evidence here is
  still the functional simulator.
- **The token at 200,000 and 1,000,000 tokens is not defined by the model**, as
  the BF16 tie argument above shows, so no future run can validate one. Byte
  traffic can be; token identity cannot.
