# Speculative decoding on the area-constrained roofline: released_dspark

> DeepSeek-V4's own speculative module, as shipped. Every figure below is derived from the roofline artifacts
> this repository has already published, by re-assembling each point's own five
> critical-path terms for a speculative cycle. Nothing here re-runs the machine
> model, and nothing here invents an acceptance rate.

## What this layer says

1. **Every term the speculative arithmetic needs is already in the published artifact, exactly.** 31,809 feasible points across 16 studies were rebuilt from their own five critical-path terms and every one reproduced its published step time to 1e-9 relative. Nothing here re-ran the machine model, and the layer is additive by construction rather than by promise.
2. **The headline is a break-even, not a speedup.** `tau* = T_cycle / step_time_s`, and `tau <= gamma+1` always. Of 43,432 (point, draft-placement) pairs where this profile's drafter applies, 9,263 (21.3%) cannot be sped up by speculation at ANY acceptance rate, at any block size on the ladder, even charging the drafter no KV traffic at all.
3. **The ROM-versus-GPU ratio under speculation carries no acceptance rate.** It is `T_cycle(GPU) / T_cycle(ROM)`: `tau` is a property of the model and its drafter, not of the machine, so it is identical on both sides and cancels. Every movement this report shows is a machine effect and nothing else, which is why it can be published without inventing an acceptance rate.
4. **The ratio moves, and it mostly compresses.** Across 256 model-context-batch-class rows, 201 move the ROM-versus-GPU per-user ratio DOWN under speculation and 55 move it UP, spanning 0.204x to 3.670x. The ROM advantage compresses on most operating points.
5. **At batch 1 the two extremes are opposite in sign, and they are the result.** DeepSeek-V4-Flash-0731 on `array` silicon goes from 1.93x to 0.50x -- a 0.257x movement -- while DeepSeek-V4-Pro-0813 on `array` silicon goes from 1.37x to 1.29x, a 0.937x movement. A layer that multiplied both sides by `tau` would have reported neither.
6. **A moving ratio is not a win for either side, and the report says so on every table.** At the most favourable sourced acceptance (5.00) speculation is worth having on 124 of 256 ROM class rows and 195 of 256 GPU rows; everywhere else the design runs SLOWER with a drafter than without one. Where both sides lose, a rising ratio means only that the comparator lost more.
7. **Compute is never a gain and always a loss.** A verification pass over `n` positions charges `n` times the arithmetic exactly, so per accepted token compute costs `(n/tau) >= 1` times what it did. A compute-bound design cannot be sped up by speculation at any acceptance rate; it can only be slowed. That is where the recommended ROM designs live, because the sizing rule gives them just enough compute for one token per sweep.
8. **On a mask-ROM machine the draft pass costs a full array sweep, and that is the load-bearing assumption of the whole ROM verdict.** `stored/peak` is a technology constant in `src/opentallas/roofline.py`, so a pass reading only the drafter's region takes as long as sweeping the entire array. The alternative -- holding the drafter in the KV store -- is priced beside it on every ROM row and has NOT been costed in silicon area.
9. **The mask-ROM designs are already storing this drafter, and already sweeping it on every ordinary token.** `_rom_stored_bytes` stores the whole released checkpoint, and the checkpoint ships the draft module for DeepSeek-V4-Flash-0731, DeepSeek-V4-Pro-0813. So the storage inflation is 1.000x, the extra array requirement is zero, and the autoregressive ROM baseline in the published study is ALREADY paying for a drafter it does not use. The HBM comparators are not: their engaged bytes exclude the draft categories entirely.
10. **This profile does not apply to Qwen3-8B.** Its released checkpoint carries no draft weights at all, and transplanting a drafter that was never trained for it would be inventing a model. It is reported as not applicable rather than modelled.
11. **This drafter's SEQUENTIAL step is what it costs on a mask-ROM machine, and it costs more than the drafter's own size.** The bias is applied once per draft token with no transformer re-run, so on a bandwidth machine it moves a table and is nearly free -- but under the locality rule every pass that touches the array takes the full-array sweep time whatever it reads, so `gamma` sequential applications cost `gamma` full sweeps. The draft pass is 5% to 85% of the whole speculative cycle on the ROM designs this report quotes (median 47%), almost all of it those sweeps. A block-diffusion drafter has no such term at all, which is the single largest structural difference between the two profiles on this silicon.
12. **Every number here is conditional on inputs nobody has measured.** The drafter's own KV traffic is unsourced for both drafters and is published as a band on every row; the compute efficiency derate that decides which designs are compute-bound is graded `assumed` at 0.55; and no speculative decoder has ever been executed in this repository.

## What this layer is, and what it is not

It **is** an arithmetic layer over `results/roofline/**/analytical.json`. Every term it uses -- weight read, KV read, compute, link latency, the per-layer serial floor, the thermal throttle -- is recovered exactly from the published artifact, and the reconstruction is gated on every feasible point before any speculative arithmetic runs.

It is **not** a measurement of a speculative system. No token in this repository has been produced by a speculative decoder. The only quantities taken from outside are the drafter's shape and the acceptance lengths, both published by their authors and both measured on hardware that is not in this study.

The headline is therefore **not a speedup**. It is the break-even acceptance `tau* = T_cycle / step_time_s`: speculation pays if and only if `tau >= tau*`, and `tau <= gamma+1` always. A design whose `tau*` exceeds `gamma+1` at every block size **cannot be sped up by speculation at any acceptance rate** -- a verdict that needs no acceptance rate to state, and the only kind of verdict this study can honestly publish for a model whose acceptance nobody has measured.

## The arithmetic

Write `n = gamma + 1` for the positions one verification pass carries, the extra one
being the target's own bonus token. DFlash equation (1) is `L = (T_draft + T_verify)/tau`
with `tau` in `[1, gamma+1]` counting accepted tokens INCLUDING that bonus token.

**`gamma` is the block size, taken from each source's own definition and never derived as `block_size - 1`.** DFlash states that the block size IS the speculation budget, so a block of 16 proposes 16 draft tokens and caps `tau` at 17. DSpark treats the anchor itself as the first prediction position, so a block of `gamma` (anchor plus `gamma-1` masks) yields `gamma` draft logits and caps `tau` at `gamma+1`. A ladder rung above the block size a source actually configures is an extension this study states rather than a configuration anyone has served.

**Every headline figure in this report is at gamma = 7, so a verification pass carries 8 positions and `tau` is capped at 8.** The break-even ladder runs over gamma = 1, 2, 3, 4, 5, 7, 8, 15, 16. Of those, 5, 7 are block sizes a source names for this drafter; 1, 2, 3, 4, 8, 15, 16 are rungs no source configures, carried so the parameter-free verdict below is tested over a wider range than anyone serves, and never quoted as a served figure.

| term | verification pass over `n` positions | why |
| --- | --- | --- |
| weight, ROM `batched` | `W` | one array sweep serves the block exactly as it serves a batch, and it is immune to the expert-union widening that taxes a bandwidth machine |
| weight, ROM `per_stream` | `W * n` | compute-in-ROM: the multiply IS the sweep, so each position is its own pass through the fabric |
| weight, ROM `per_region` | `W * R(mb*n)/R(mb)` | the busiest expert region carries more of a wider block |
| weight, HBM | `W * t(mb*n)/t(mb)` | **not invariant**: `n` positions are `n` independent expert draws, so the union of routed experts widens and the engaged bytes grow |
| weight, drafter held off-array (`in_kv_store`) | `(dense + routed * coverage(mb*n)) / kv_read_bytes_s` | a bandwidth read over the KV store's own path, charged ONCE for the block. The compute-in-ROM sweep multiplier belongs to the fabric and this transfer never enters the fabric. |
| KV | `K * (read + n*write)/(read + write)` | the block shares one prefix, so the context is read ONCE per cycle and only the writes multiply |
| compute | `C * n` | exact under the model's own convention: `_scaled_operations` is linear in positions |
| link | `lat + xfer * n` | only the payload half of a link event scales with positions; the latency half is fixed per cycle |
| per-layer floor | `F` | one traversal of the layers however many positions ride it |

The draft pass runs on the same machine under the same rules with the drafter's own numbers. On a mask-ROM machine it is where the locality rule bites: `t = stored/peak` is a technology constant in `src/opentallas/roofline.py`, so a pass that touches only the drafter's region takes exactly as long as sweeping the whole array.

## The profile, and every parameter's grade

| parameter | value | grade | source |
| --- | --- | --- | --- |
| `acceptance_length` | (a block of values; see the tables in this report) | `published` | LMSYS Org, 'DSpark in SGLang: Speculative Decoding with Confidence-Driven, Variable-Length Verification', https://www.lmsys.org... |
| `external_draft_traffic_decomposition` | (a block of values; see the tables in this report) | `published` | DSpark draft weight-traffic decomposition for DeepSeek-V4-Pro-0813, arXiv:2607.05147 / github.com/deepseek-ai/DeepSpec (2026) |
| `parameters.block_size` | 5 | `published` | arXiv:2607.05147 (2026), dspark_block_size = 5: 'We configure the maximum block size to gamma=5' |
| `parameters.draft_block_passes` | 1 | `published` | arXiv:2607.05147 (2026): the masked block is embedded once, takes one pass through the 3 stages, and one lm_head pass covers al... |
| `parameters.draft_compute_ops_ratio_rule` | engaged draft weight bytes / engaged target weight bytes at the same block, at equal da... | `assumed` | explicit modelling convention; operations = 2 x active parameters (configs/hardware/technology.json counting convention) makes ... |
| `parameters.draft_sequential_passes_per_draft_token` | 1 | `published` | arXiv:2607.05147 (2026): a rank-256 Markov bias is applied sequentially per position after the block pass, with no transformer ... |
| `parameters.draft_stages` | 3 | `published` | DSpark: Confidence-Scheduled Speculative Decoding with Semi-Autoregressive Generation, arXiv:2607.05147 (2026); shipped inferen... |
| `parameters.draft_weight_bytes_source` | configs/models/<model>.json draft_dense_weight_bytes + draft_routed_weight_bytes, read ... | `derived` | checkpoint tensor inventory already committed in configs/models/deepseek-v4-pro-0813.json and configs/models/deepseek-v4-flash-... |
| `parameters.drafter_kv_traffic` | BAND [0.0, target KV time x draft_stages / num_layers] | `assumed` | no primary source: arXiv:2607.05147 (2026) states no KV byte count for the MTP stages |
| `parameters.markov_bias_rank` | 256 | `published` | arXiv:2607.05147 (2026): 'The low-rank factorization (r=256 by default) keeps both storage and per-step compute small', with W1... |
| `parameters.served_speculative_tokens` | 7 | `published` | DeepSeek's own vLLM integration flag num_speculative_tokens = 7, github.com/deepseek-ai/DeepSpec (2026), corroborated by https:... |

**The acceptance length is an input, never an output, and it is task-dependent.** The range carried here is 5.00 to 5.00, graded `published`, from LMSYS Org, 'DSpark in SGLang: Speculative Decoding with Confidence-Driven, Variable-Length Verification', https://www.lmsys.org/blog/2026-07-06-dspark-sglang/ (6 July 2026), which states verbatim: 'Together they reach 383.7 tok/s at accept length ~5 at batch size 1 on DeepSeek-V4-Pro, TP=8, B300.'. Every speculative rate below is published across that range.

| workload | tau | source's own reported speedup |
| --- | ---: | ---: |
| SGLang integration measurement, workload mix not stated | 5.00 | -- |

_WHOSE NUMBER THIS IS: the SGLang integration's own measurement, published by LMSYS Org, not a statement by DeepSeek. DeepSeek's own pages carry no accepted-length figure -- the vLLM integration blog (https://vllm.ai/blog/2026-08-14-dspark-adaptive-verification) and the DeepSeek-V4-Pro-DSpark model card were both checked and state the serving flag, the hardware and the per-position survival rates but no average accepted length. The source writes 'accept length ~5'; it is approximate and it is used here as an exact point, which is a property of the source and not a claim of precision. It is one figure and not a range; that too is a property of the source, not a claim that acceptance is workload-independent. At the paper's configured block of 5 the cap is gamma+1 = 6 and at the served block of 7 the cap is 8, so 5.00 is inside the interval at both and is never clamped._

## The reconstruction gate

Before any speculative arithmetic runs, every feasible point in every study is rebuilt from its own published terms and must reproduce its published step time to 1e-9 relative.

| study | feasible points checked | failures |
| --- | ---: | ---: |
| `n5_vs_b200-flash-1m` | 1,810 | 0 |
| `n5_vs_b200-flash-32k` | 1,880 | 0 |
| `n5_vs_b200-flash-8k` | 1,894 | 0 |
| `n5_vs_b200-pro-200k` | 1,428 | 0 |
| `n5_vs_b200-pro-32k` | 1,444 | 0 |
| `n5_vs_b200-pro-8k` | 1,408 | 0 |
| `n6_vs_a100-flash-1m` | 1,846 | 0 |
| `n6_vs_a100-flash-32k` | 1,996 | 0 |
| `n6_vs_a100-flash-8k` | 2,008 | 0 |
| `n6_vs_a100-pro-200k` | 1,242 | 0 |
| `n6_vs_a100-pro-32k` | 1,260 | 0 |
| `n6_vs_a100-pro-8k` | 1,398 | 0 |
| `n5_vs_b200` | 4,638 | 0 |
| `n6_vs_a100` | 4,668 | 0 |
| `n5_vs_b200-quantised_variant` | 1,385 | 0 |
| `n6_vs_a100-quantised_variant` | 1,504 | 0 |

The identity checked is: `(max(memory, compute)/stage_balance + link_latency + layer_fixed_latency) x thermal_scale == step_time_s, with memory assembled by designs[].shared_memory_path and the compute-in-ROM fusion rule, and the weight and link terms independently rebuilt from the model profile and the technology file`.

## Headline: where speculation cannot pay at any acceptance rate

Counted at the LOW end of the unsourced drafter-KV band, which is the most favourable assumption available to speculation. `tau*` is the break-even acceptance at this profile's served block size.

| study | model | family | draft placement | binds on (autoregressive) | points | cannot pay at any gamma | tau* min | tau* median | tau* max |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 174 | 0 | 1.66 | 3.41 | 7.87 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 354 | 0 | 1.27 | 2.45 | 3.19 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 85 | 40 | 5.37 | 7.95 | 8.53 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 95 | 7 | 1.10 | 3.23 | 8.36 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 580 | 26 | 1.08 | 2.36 | 8.34 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `thermal` | 8 | 0 | 2.73 | 5.49 | 7.87 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 514 | 28 | 1.05 | 2.35 | 8.57 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 85 | 61 | 7.81 | 8.39 | 14.33 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 95 | 19 | 1.26 | 7.40 | 19.57 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 580 | 45 | 1.13 | 4.08 | 11.94 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `thermal` | 8 | 4 | 5.60 | 8.78 | 14.64 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 514 | 390 | 5.28 | 10.03 | 22.94 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 184 | 0 | 1.66 | 3.48 | 7.97 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 4 | 0 | 1.24 | 1.95 | 2.91 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 380 | 0 | 1.40 | 2.58 | 4.24 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 59 | 32 | 5.85 | 8.32 | 10.11 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 3 | 1 | 4.37 | 6.40 | 36.61 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 620 | 27 | 1.12 | 2.48 | 9.65 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 630 | 37 | 1.11 | 2.34 | 27.94 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 59 | 39 | 5.93 | 8.43 | 14.60 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 3 | 0 | 5.07 | 6.39 | 7.98 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 620 | 47 | 1.13 | 4.04 | 11.94 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 630 | 482 | 5.22 | 8.92 | 22.80 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 184 | 0 | 1.66 | 3.49 | 7.97 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 3 | 0 | 1.24 | 1.35 | 1.96 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 381 | 0 | 1.41 | 2.59 | 4.26 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 56 | 28 | 5.71 | 8.31 | 8.89 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 2 | 2 | 82.02 | 82.24 | 82.24 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 624 | 35 | 1.12 | 2.69 | 32.77 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 644 | 101 | 1.17 | 2.42 | 76.33 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 56 | 35 | 5.83 | 8.42 | 14.30 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 2 | 0 | 5.28 | 7.40 | 7.40 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 624 | 47 | 1.13 | 4.04 | 11.94 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 644 | 493 | 5.22 | 8.92 | 22.80 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 151 | 0 | 1.95 | 4.04 | 7.77 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 329 | 0 | 1.32 | 2.40 | 4.15 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 56 | 24 | 6.36 | 7.77 | 8.57 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 6 | 0 | 4.40 | 5.84 | 6.61 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 404 | 20 | 1.14 | 2.93 | 8.25 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 482 | 35 | 1.12 | 2.08 | 8.98 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 56 | 50 | 6.39 | 10.68 | 13.99 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 6 | 0 | 5.51 | 6.10 | 6.63 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 404 | 38 | 1.18 | 4.03 | 11.15 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 482 | 373 | 5.15 | 8.98 | 22.95 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 151 | 0 | 1.95 | 4.05 | 7.78 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 321 | 0 | 1.46 | 2.38 | 4.12 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 55 | 26 | 6.54 | 7.72 | 11.45 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 417 | 20 | 1.14 | 2.99 | 8.25 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 500 | 42 | 1.18 | 2.20 | 15.21 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 55 | 48 | 6.78 | 10.70 | 13.88 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 417 | 40 | 1.18 | 4.03 | 11.15 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 500 | 375 | 5.15 | 8.98 | 22.95 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 135 | 0 | 1.95 | 4.05 | 7.78 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 289 | 0 | 1.41 | 2.41 | 4.20 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 55 | 26 | 6.66 | 7.77 | 21.96 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 421 | 25 | 1.14 | 3.03 | 19.66 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 508 | 83 | 1.28 | 2.18 | 54.01 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 55 | 48 | 6.75 | 10.52 | 13.76 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 421 | 40 | 1.18 | 4.05 | 11.15 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 508 | 377 | 5.15 | 8.98 | 22.95 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 204 | 0 | 1.67 | 3.70 | 7.83 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 420 | 0 | 1.67 | 2.37 | 3.74 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 80 | 50 | 5.36 | 8.27 | 8.67 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 144 | 0 | 1.09 | 2.55 | 7.54 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 606 | 25 | 1.08 | 2.47 | 8.38 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 392 | 34 | 1.09 | 2.56 | 9.43 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 80 | 50 | 6.77 | 9.46 | 14.84 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 144 | 10 | 1.07 | 4.25 | 12.91 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 606 | 53 | 1.13 | 4.75 | 11.60 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 392 | 324 | 5.28 | 9.95 | 22.94 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 215 | 0 | 1.67 | 3.81 | 7.87 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 449 | 0 | 1.37 | 2.43 | 4.29 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 46 | 28 | 5.76 | 8.37 | 9.62 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 11 | 0 | 3.67 | 5.49 | 6.40 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 726 | 30 | 1.13 | 2.67 | 8.37 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 549 | 56 | 1.14 | 2.57 | 30.23 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 46 | 28 | 6.69 | 8.95 | 13.96 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 11 | 0 | 3.93 | 5.00 | 6.25 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 726 | 59 | 1.14 | 4.25 | 11.60 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 549 | 457 | 4.97 | 8.94 | 22.91 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 215 | 0 | 1.67 | 3.82 | 7.87 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 449 | 0 | 1.41 | 2.43 | 4.25 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 50 | 28 | 5.65 | 8.27 | 15.88 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 2 | 1 | 6.80 | 82.24 | 82.24 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 738 | 36 | 1.13 | 2.85 | 20.99 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 554 | 88 | 1.27 | 2.56 | 73.63 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 50 | 28 | 5.50 | 8.27 | 14.41 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 2 | 0 | 6.47 | 6.93 | 6.93 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 738 | 60 | 1.14 | 4.29 | 11.49 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 554 | 461 | 4.97 | 8.94 | 22.91 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 134 | 0 | 1.89 | 4.52 | 7.59 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 370 | 0 | 1.43 | 2.13 | 4.25 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 78 | 36 | 5.55 | 8.11 | 8.86 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 10 | 0 | 4.25 | 4.82 | 5.91 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 313 | 14 | 1.14 | 3.01 | 8.28 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 337 | 26 | 1.25 | 2.44 | 9.72 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 78 | 72 | 6.86 | 9.89 | 15.52 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 10 | 0 | 4.18 | 5.32 | 5.75 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 313 | 28 | 1.19 | 4.46 | 11.79 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 337 | 233 | 5.15 | 8.98 | 22.96 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 133 | 0 | 1.89 | 4.50 | 7.60 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 371 | 0 | 1.49 | 2.13 | 4.65 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 79 | 36 | 5.55 | 8.31 | 11.06 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 325 | 14 | 1.14 | 3.15 | 9.15 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 352 | 31 | 1.25 | 2.67 | 13.42 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 79 | 72 | 7.13 | 9.90 | 15.57 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 325 | 30 | 1.19 | 4.46 | 11.79 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 352 | 240 | 5.15 | 8.98 | 22.96 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 141 | 0 | 1.89 | 4.50 | 7.60 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 387 | 0 | 1.46 | 2.13 | 4.57 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 55 | 24 | 5.84 | 8.31 | 20.44 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 363 | 22 | 1.14 | 3.34 | 17.44 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 452 | 98 | 1.37 | 2.91 | 39.26 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 55 | 48 | 7.11 | 9.45 | 14.35 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 363 | 39 | 1.19 | 4.48 | 11.79 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 452 | 321 | 5.15 | 8.99 | 22.96 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 176 | 0 | 1.66 | 3.51 | 7.95 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 368 | 0 | 1.33 | 2.56 | 3.87 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 61 | 30 | 5.52 | 8.02 | 8.56 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 25 | 0 | 1.22 | 2.53 | 7.59 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 597 | 27 | 1.12 | 2.28 | 8.30 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 617 | 25 | 1.05 | 1.86 | 9.74 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 61 | 41 | 7.40 | 8.42 | 15.00 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 25 | 2 | 2.11 | 2.88 | 9.89 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 597 | 45 | 1.13 | 3.89 | 11.94 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 617 | 475 | 5.19 | 8.92 | 22.80 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 155 | 0 | 1.95 | 4.04 | 7.72 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 325 | 0 | 1.42 | 2.38 | 4.00 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 82 | 42 | 6.23 | 8.10 | 8.36 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 32 | 0 | 1.45 | 3.02 | 7.02 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 386 | 20 | 1.11 | 2.83 | 8.25 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 436 | 37 | 1.12 | 2.08 | 8.89 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 82 | 82 | 8.27 | 11.37 | 15.60 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 32 | 0 | 2.40 | 3.87 | 7.02 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 386 | 38 | 1.18 | 4.03 | 11.15 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 436 | 346 | 5.15 | 9.18 | 22.95 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 216 | 0 | 1.67 | 3.77 | 7.85 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 448 | 0 | 1.48 | 2.42 | 4.63 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 50 | 28 | 5.35 | 8.21 | 8.98 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 41 | 0 | 1.27 | 2.43 | 7.54 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 697 | 30 | 1.12 | 2.40 | 8.37 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 526 | 43 | 1.11 | 2.18 | 11.40 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 50 | 28 | 6.69 | 8.29 | 14.54 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 41 | 1 | 1.38 | 2.20 | 8.64 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 697 | 60 | 1.14 | 4.34 | 11.60 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 526 | 444 | 5.16 | 8.97 | 22.91 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 137 | 0 | 1.89 | 4.47 | 7.55 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 367 | 0 | 1.73 | 2.13 | 4.14 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 76 | 36 | 5.65 | 7.94 | 8.33 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 37 | 0 | 1.52 | 2.56 | 3.07 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 292 | 14 | 1.11 | 2.62 | 8.28 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 315 | 23 | 1.12 | 2.91 | 9.72 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 76 | 76 | 8.21 | 10.13 | 15.58 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 37 | 0 | 1.61 | 2.95 | 5.69 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 292 | 27 | 1.19 | 4.43 | 11.79 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 315 | 237 | 5.15 | 8.99 | 22.96 |

## Per model, per context, per batch and per design class

Each row is that class's **fastest** feasible design at that batch, read against the iso-area GPU comparator the published study already chose for it. The `densest` pick of every class is in `analytical.json` beside it.

**The ROM-versus-GPU ratio under speculation is `T_cycle(GPU) / T_cycle(ROM)` and carries no `tau` at all.** The acceptance length is a property of the model and its drafter, not of the machine, so it is the same on both sides and cancels out of the ratio. Every movement in the last column is therefore a machine effect and nothing else.

### `n5_vs_b200-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,374.7 | 1,701.0-1,701.0 | 6.98 | **no** | `b200_sxm-x19-tensor` | 1,232.8 | 3,429.5-3,429.5 | 1.80 | yes | 1.926x | 0.496x | 0.257x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 4,824.6 | 10,128.5-10,128.5 | 2.38 | yes | `b200_sxm-x29-tensor` | 1,290.0 | 3,659.4-3,659.4 | 1.76 | yes | 3.740x | 2.768x | 0.740x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,374.7 | 1,701.0-1,701.0 | 6.98 | **no** | `b200_sxm-x19-hybrid` | 1,157.2 | 2,458.7-2,458.7 | 2.35 | yes | 2.052x | 0.692x | 0.337x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 4,315.7 | 9,490.3-9,490.3 | 2.27 | yes | `b200_sxm-x87-tensor` | 1,244.9 | 2,950.3-2,950.3 | 2.11 | yes | 3.467x | 3.217x | 0.928x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,374.7 | 1,701.0-1,701.0 | 6.98 | **no** | `b200_sxm-x19-hybrid` | 1,050.1 | 2,121.8-2,121.8 | 2.47 | yes | 2.262x | 0.802x | 0.355x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,223.6 | 9,386.7-9,386.7 | 2.25 | yes | `b200_sxm-x116-tensor` | 1,077.7 | 2,006.5-2,006.5 | 2.69 | yes | 3.919x | 4.678x | 1.194x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,175.9 | 1,374.3-1,374.3 | 7.92 | **no** | `b200_sxm-x19-hybrid` | 802.6 | 1,471.2-1,471.2 | 2.73 | yes | 2.711x | 0.934x | 0.345x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,891.3 | 8,993.9-8,993.9 | 2.16 | yes | `b200_sxm-x231-tensor` | 894.5 | 1,259.5-1,259.5 | 3.55 | yes | 4.350x | 7.141x | 1.642x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 2,069.1 | 1,212.9-1,212.9 | 8.53 | **no** | `b200_sxm-x22-hybrid` | 620.6 | 1,147.1-1,147.1 | 2.71 | yes | 3.334x | 1.057x | 0.317x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,425.1 | 8,258.6-8,258.6 | 2.07 | yes | `b200_sxm-x347-tensor` | 668.3 | 719.2-719.2 | 4.65 | yes | 5.125x | 11.483x | 2.241x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x87-romfill` | 2,038.5 | 1,277.7-1,277.7 | 7.98 | **no** | `b200_sxm-x44-hybrid` | 463.0 | 904.5-904.5 | 2.56 | yes | 4.402x | 1.413x | 0.321x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,849.2 | 7,038.6-7,038.6 | 2.02 | yes | `b200_sxm-x347-tensor` | 442.3 | 387.3-387.3 | 5.71 | **no** | 6.442x | 18.174x | 2.821x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 1,909.1 | 1,229.7-1,229.7 | 7.76 | **no** | `b200_sxm-x87-hybrid` | 333.8 | 700.3-700.3 | 2.38 | yes | 5.720x | 1.756x | 0.307x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,132.2 | 5,433.4-5,433.4 | 1.96 | yes | `b200_sxm-x347-tensor` | 268.7 | 201.5-201.5 | 6.67 | **no** | 7.936x | 26.958x | 3.397x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 1,287.2 | 824.6-824.6 | 7.81 | **no** | `b200_sxm-x173-hybrid` | 163.8 | 405.9-405.9 | 2.02 | yes | 7.858x | 2.032x | 0.259x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 849.5 | 1,006.7-1,006.7 | 4.22 | yes | `b200_sxm-x347-hybrid` | 129.4 | 319.8-319.8 | 2.02 | yes | 6.563x | 3.148x | 0.480x |

**Does the ratio compress?** Of 16 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 5 move it UP. The movement spans 0.257x to 3.397x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 8 of 16 ROM rows and 14 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hybrid-x29` | 2,627.4 | 2,211.7-2,211.7 | 5.94 | **no** | `b200_sxm-x15-hybrid` | 1,476.2 | 3,152.0-3,152.0 | 2.34 | yes | 1.780x | 0.702x | 0.394x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 4,855.8 | 11,304.2-11,304.2 | 2.15 | yes | `b200_sxm-x29-tensor` | 1,303.0 | 3,680.2-3,680.2 | 1.77 | yes | 3.727x | 3.072x | 0.824x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 2,627.4 | 2,130.4-2,130.4 | 6.17 | **no** | `b200_sxm-x16-hybrid` | 1,510.3 | 3,255.0-3,255.0 | 2.32 | yes | 1.740x | 0.654x | 0.376x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,849.3 | 11,105.6-11,105.6 | 2.18 | yes | `b200_sxm-x29-tensor` | 1,165.2 | 2,699.8-2,699.8 | 2.16 | yes | 4.162x | 4.114x | 0.988x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 2,627.4 | 2,130.4-2,130.4 | 6.17 | **no** | `b200_sxm-x16-hybrid` | 1,230.1 | 2,290.2-2,290.2 | 2.69 | yes | 2.136x | 0.930x | 0.436x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,849.3 | 10,332.4-10,332.4 | 2.35 | yes | `b200_sxm-x29-hybrid` | 1,123.0 | 2,368.7-2,368.7 | 2.37 | yes | 4.318x | 4.362x | 1.010x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,365.6 | 2,196.4-2,196.4 | 5.39 | **no** | `b200_sxm-x19-hybrid` | 868.5 | 1,513.3-1,513.3 | 2.87 | yes | 2.724x | 1.451x | 0.533x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,849.3 | 9,069.4-9,069.4 | 2.67 | yes | `b200_sxm-x29-hybrid` | 892.1 | 1,694.5-1,694.5 | 2.63 | yes | 5.436x | 5.352x | 0.985x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,341.6 | 1,799.6-1,799.6 | 6.51 | **no** | `b200_sxm-x19-hybrid` | 646.9 | 1,087.3-1,087.3 | 2.98 | yes | 3.620x | 1.655x | 0.457x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,725.1 | 7,287.8-7,287.8 | 3.24 | yes | `b200_sxm-x29-hybrid` | 686.8 | 1,218.4-1,218.4 | 2.82 | yes | 6.880x | 5.982x | 0.869x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 2,109.5 | 1,553.5-1,553.5 | 6.79 | **no** | `b200_sxm-x22-hybrid` | 496.2 | 939.4-939.4 | 2.64 | yes | 4.251x | 1.654x | 0.389x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 4,534.7 | 7,553.0-7,553.0 | 3.00 | yes | `b200_sxm-x87-hybrid` | 454.8 | 930.3-930.3 | 2.44 | yes | 9.971x | 8.119x | 0.814x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x87-romfill` | 1,994.8 | 1,562.5-1,562.5 | 6.38 | **no** | `b200_sxm-x44-hybrid` | 367.7 | 749.0-749.0 | 2.45 | yes | 5.424x | 2.086x | 0.385x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,291.8 | 6,413.3-6,413.3 | 3.35 | yes | `b200_sxm-x116-hybrid` | 319.5 | 673.9-673.9 | 2.37 | yes | 13.431x | 9.516x | 0.709x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 1,761.1 | 1,124.1-1,124.1 | 7.83 | **no** | `b200_sxm-x87-hybrid` | 198.0 | 536.3-536.3 | 1.85 | yes | 8.892x | 2.096x | 0.236x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,382.1 | 4,952.9-4,952.9 | 3.41 | yes | `b200_sxm-x347-hybrid` | 132.3 | 323.2-323.2 | 2.05 | yes | 25.570x | 15.324x | 0.599x |

**Does the ratio compress?** Of 16 class rows in this study, 15 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.236x to 1.010x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 8 of 16 ROM rows and 16 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hybrid-x28` | 2,627.4 | 1,853.9-1,853.9 | 7.09 | **no** | `b200_sxm-x14-hybrid` | 1,441.3 | 3,044.6-3,044.6 | 2.37 | yes | 1.823x | 0.609x | 0.334x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 4,856.6 | 11,311.6-11,311.6 | 2.15 | yes | `b200_sxm-x29-tensor` | 1,303.3 | 3,680.8-3,680.8 | 1.77 | yes | 3.726x | 3.073x | 0.825x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 2,627.4 | 2,190.1-2,190.1 | 6.00 | **no** | `b200_sxm-x16-hybrid` | 1,511.9 | 3,256.6-3,256.6 | 2.32 | yes | 1.738x | 0.673x | 0.387x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,849.3 | 11,167.8-11,167.8 | 2.17 | yes | `b200_sxm-x29-tensor` | 1,165.8 | 2,700.3-2,700.3 | 2.16 | yes | 4.160x | 4.136x | 0.994x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 2,627.4 | 2,190.1-2,190.1 | 6.00 | **no** | `b200_sxm-x16-hybrid` | 1,232.3 | 2,291.7-2,291.7 | 2.69 | yes | 2.132x | 0.956x | 0.448x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,849.3 | 10,440.6-10,440.6 | 2.32 | yes | `b200_sxm-x29-hybrid` | 1,124.0 | 2,369.6-2,369.6 | 2.37 | yes | 4.314x | 4.406x | 1.021x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,365.6 | 2,230.3-2,230.3 | 5.30 | **no** | `b200_sxm-x19-hybrid` | 870.3 | 1,514.4-1,514.4 | 2.87 | yes | 2.718x | 1.473x | 0.542x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,849.3 | 9,237.6-9,237.6 | 2.62 | yes | `b200_sxm-x29-hybrid` | 893.4 | 1,695.4-1,695.4 | 2.63 | yes | 5.428x | 5.448x | 1.004x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,341.6 | 1,845.6-1,845.6 | 6.34 | **no** | `b200_sxm-x19-hybrid` | 648.9 | 1,088.4-1,088.4 | 2.98 | yes | 3.608x | 1.696x | 0.470x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,781.8 | 7,507.4-7,507.4 | 3.18 | yes | `b200_sxm-x29-hybrid` | 688.2 | 1,219.3-1,219.3 | 2.82 | yes | 6.948x | 6.157x | 0.886x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,177.0 | 1,372.2-1,372.2 | 7.93 | **no** | `b200_sxm-x19-hybrid` | 462.3 | 855.2-855.2 | 2.70 | yes | 4.709x | 1.605x | 0.341x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,577.4 | 6,833.6-6,833.6 | 3.35 | yes | `b200_sxm-x58-hybrid` | 480.3 | 918.9-918.9 | 2.61 | yes | 9.531x | 7.437x | 0.780x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 2,032.5 | 1,189.2-1,189.2 | 8.55 | **no** | `b200_sxm-x22-hybrid` | 351.2 | 829.6-829.6 | 2.12 | yes | 5.788x | 1.433x | 0.248x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,343.8 | 6,602.1-6,602.1 | 3.29 | yes | `b200_sxm-x116-hybrid` | 319.9 | 674.2-674.2 | 2.37 | yes | 13.580x | 9.792x | 0.721x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 1,784.6 | 1,186.3-1,186.3 | 7.52 | **no** | `b200_sxm-x87-hybrid` | 198.7 | 537.3-537.3 | 1.85 | yes | 8.981x | 2.208x | 0.246x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,428.5 | 5,123.0-5,123.0 | 3.35 | yes | `b200_sxm-x347-hybrid` | 132.3 | 323.3-323.3 | 2.05 | yes | 25.906x | 15.846x | 0.612x |

**Does the ratio compress?** Of 16 class rows in this study, 14 move the ROM-versus-GPU ratio DOWN under speculation and 2 move it UP. The movement spans 0.246x to 1.021x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 8 of 16 ROM rows and 16 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 1,062.6 | 2,501.9-2,501.9 | 2.12 | yes | `b200_sxm-x173-tensor` | 773.9 | 1,945.1-1,945.1 | 1.99 | yes | 1.373x | 1.286x | 0.937x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 2,648.8 | 3,547.7-3,547.7 | 3.73 | yes | `b200_sxm-x87-tensor` | 748.5 | 1,819.6-1,819.6 | 2.06 | yes | 3.539x | 1.950x | 0.551x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 951.6 | 1,711.6-1,711.6 | 2.78 | yes | `b200_sxm-x173-tensor` | 678.4 | 1,337.1-1,337.1 | 2.54 | yes | 1.403x | 1.280x | 0.913x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.8 | 3,523.6-3,523.6 | 3.76 | yes | `b200_sxm-x87-tensor` | 640.8 | 1,251.8-1,251.8 | 2.56 | yes | 4.133x | 2.815x | 0.681x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x161` | 857.6 | 383.0-383.0 | 11.20 | **no** | `b200_sxm-x82-tensor` | 506.4 | 793.8-793.8 | 3.19 | yes | 1.693x | 0.482x | 0.285x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.3 | 3,347.0-3,347.0 | 3.96 | yes | `b200_sxm-x87-tensor` | 509.8 | 801.3-801.3 | 3.18 | yes | 5.194x | 4.177x | 0.804x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x161` | 857.6 | 383.0-383.0 | 11.20 | **no** | `b200_sxm-x82-tensor` | 377.7 | 481.8-481.8 | 3.92 | yes | 2.271x | 0.795x | 0.350x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,646.5 | 2,788.1-2,788.1 | 4.75 | yes | `b200_sxm-x87-tensor` | 381.0 | 485.9-485.9 | 3.92 | yes | 6.946x | 5.738x | 0.826x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x161` | 857.6 | 383.0-383.0 | 11.20 | **no** | `b200_sxm-x82-tensor` | 259.4 | 281.6-281.6 | 4.61 | yes | 3.306x | 1.360x | 0.411x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,426.5 | 2,090.1-2,090.1 | 5.80 | **no** | `b200_sxm-x87-tensor` | 261.9 | 283.4-283.4 | 4.62 | yes | 9.265x | 7.375x | 0.796x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 825.3 | 439.5-439.5 | 9.39 | **no** | `b200_sxm-x87-tensor` | 167.5 | 159.0-159.0 | 5.27 | **no** | 4.927x | 2.764x | 0.561x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 2,364.4 | 2,197.9-2,197.9 | 5.38 | **no** | `b200_sxm-x116-tensor` | 172.3 | 158.3-158.3 | 5.44 | **no** | 13.724x | 13.882x | 1.012x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x193` | 742.3 | 427.7-427.7 | 8.68 | **no** | `b200_sxm-x98-tensor` | 102.2 | 84.7-84.7 | 6.03 | **no** | 7.265x | 5.051x | 0.695x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 2,219.3 | 1,965.1-1,965.1 | 5.65 | **no** | `b200_sxm-x173-tensor` | 106.4 | 83.5-83.5 | 6.37 | **no** | 20.859x | 23.547x | 1.129x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227` | 627.5 | 285.6-285.6 | 10.98 | **no** | `b200_sxm-x116-hybrid` | 50.6 | 112.6-112.6 | 2.25 | yes | 12.393x | 2.537x | 0.205x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,613.7 | 1,393.7-1,393.7 | 5.79 | **no** | `b200_sxm-x347-hybrid` | 36.3 | 84.9-84.9 | 2.14 | yes | 44.422x | 16.416x | 0.370x |

**Does the ratio compress?** Of 16 class rows in this study, 14 move the ROM-versus-GPU ratio DOWN under speculation and 2 move it UP. The movement spans 0.205x to 1.129x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 6 of 16 ROM rows and 12 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 1,062.6 | 2,502.5-2,502.5 | 2.12 | yes | `b200_sxm-x173-tensor` | 774.1 | 1,945.4-1,945.4 | 1.99 | yes | 1.373x | 1.286x | 0.937x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 2,648.8 | 3,671.4-3,671.4 | 3.61 | yes | `b200_sxm-x87-tensor` | 748.9 | 1,820.0-1,820.0 | 2.06 | yes | 3.537x | 2.017x | 0.570x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 952.4 | 1,716.6-1,716.6 | 2.77 | yes | `b200_sxm-x173-tensor` | 678.7 | 1,337.3-1,337.3 | 2.54 | yes | 1.403x | 1.284x | 0.915x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.8 | 3,640.4-3,640.4 | 3.64 | yes | `b200_sxm-x87-tensor` | 641.3 | 1,252.2-1,252.2 | 2.56 | yes | 4.130x | 2.907x | 0.704x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x160` | 888.6 | 415.9-415.9 | 10.68 | **no** | `b200_sxm-x82-tensor` | 507.1 | 794.1-794.1 | 3.19 | yes | 1.752x | 0.524x | 0.299x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.3 | 3,488.9-3,488.9 | 3.80 | yes | `b200_sxm-x87-tensor` | 510.5 | 801.6-801.6 | 3.18 | yes | 5.188x | 4.352x | 0.839x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x160` | 888.6 | 415.9-415.9 | 10.68 | **no** | `b200_sxm-x82-tensor` | 378.5 | 482.1-482.1 | 3.93 | yes | 2.348x | 0.863x | 0.367x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,646.5 | 2,990.8-2,990.8 | 4.42 | yes | `b200_sxm-x87-tensor` | 381.8 | 486.2-486.2 | 3.93 | yes | 6.932x | 6.152x | 0.887x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x160` | 888.6 | 415.9-415.9 | 10.68 | **no** | `b200_sxm-x82-tensor` | 260.1 | 281.7-281.7 | 4.62 | yes | 3.416x | 1.476x | 0.432x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,619.5 | 2,326.5-2,326.5 | 5.63 | **no** | `b200_sxm-x87-tensor` | 262.6 | 283.6-283.6 | 4.63 | yes | 9.975x | 8.205x | 0.822x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 825.3 | 474.8-474.8 | 8.69 | **no** | `b200_sxm-x87-tensor` | 168.1 | 159.1-159.1 | 5.28 | **no** | 4.910x | 2.983x | 0.608x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 2,364.4 | 2,356.6-2,356.6 | 5.02 | **no** | `b200_sxm-x116-tensor` | 172.7 | 158.4-158.4 | 5.45 | **no** | 13.687x | 14.877x | 1.087x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 814.4 | 358.3-358.3 | 11.36 | **no** | `b200_sxm-x87-tensor` | 101.9 | 85.5-85.5 | 5.96 | **no** | 7.992x | 4.190x | 0.524x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 2,351.7 | 1,826.6-1,826.6 | 6.44 | **no** | `b200_sxm-x116-tensor` | 104.0 | 84.3-84.3 | 6.16 | **no** | 22.622x | 21.656x | 0.957x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227` | 627.5 | 312.1-312.1 | 10.05 | **no** | `b200_sxm-x116-hybrid` | 50.9 | 112.9-112.9 | 2.26 | yes | 12.316x | 2.765x | 0.224x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,991.3 | 1,546.3-1,546.3 | 6.44 | **no** | `b200_sxm-x347-hybrid` | 36.4 | 85.0-85.0 | 2.14 | yes | 54.735x | 18.200x | 0.333x |

**Does the ratio compress?** Of 16 class rows in this study, 15 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.224x to 1.087x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 6 of 16 ROM rows and 12 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 1,062.6 | 2,502.6-2,502.6 | 2.12 | yes | `b200_sxm-x173-tensor` | 774.1 | 1,945.4-1,945.4 | 1.99 | yes | 1.373x | 1.286x | 0.937x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 2,648.8 | 3,689.8-3,689.8 | 3.59 | yes | `b200_sxm-x87-tensor` | 748.9 | 1,820.1-1,820.1 | 2.06 | yes | 3.537x | 2.027x | 0.573x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 952.8 | 1,718.9-1,718.9 | 2.77 | yes | `b200_sxm-x173-tensor` | 678.8 | 1,337.4-1,337.4 | 2.54 | yes | 1.404x | 1.285x | 0.916x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.8 | 3,658.3-3,658.3 | 3.62 | yes | `b200_sxm-x87-tensor` | 641.4 | 1,252.3-1,252.3 | 2.56 | yes | 4.130x | 2.921x | 0.707x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x157` | 888.6 | 408.3-408.3 | 10.88 | **no** | `b200_sxm-x80-tensor` | 506.8 | 795.0-795.0 | 3.19 | yes | 1.753x | 0.514x | 0.293x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.3 | 3,510.7-3,510.7 | 3.77 | yes | `b200_sxm-x87-tensor` | 510.6 | 801.7-801.7 | 3.18 | yes | 5.187x | 4.379x | 0.844x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x157` | 888.6 | 408.3-408.3 | 10.88 | **no** | `b200_sxm-x80-tensor` | 378.3 | 483.3-483.3 | 3.91 | yes | 2.349x | 0.845x | 0.360x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,646.5 | 3,023.1-3,023.1 | 4.38 | yes | `b200_sxm-x87-tensor` | 381.9 | 486.2-486.2 | 3.93 | yes | 6.930x | 6.218x | 0.897x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x157` | 888.6 | 408.3-408.3 | 10.88 | **no** | `b200_sxm-x80-tensor` | 260.2 | 283.0-283.0 | 4.60 | yes | 3.414x | 1.443x | 0.422x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,643.0 | 2,365.8-2,365.8 | 5.59 | **no** | `b200_sxm-x87-tensor` | 262.7 | 283.6-283.6 | 4.63 | yes | 10.061x | 8.342x | 0.829x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 825.3 | 520.8-520.8 | 7.92 | **no** | `b200_sxm-x87-tensor` | 168.2 | 159.2-159.2 | 5.28 | **no** | 4.908x | 3.272x | 0.667x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 2,364.4 | 2,381.9-2,381.9 | 4.96 | yes | `b200_sxm-x116-tensor` | 172.8 | 158.4-158.4 | 5.45 | **no** | 13.682x | 15.035x | 1.099x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 814.4 | 413.5-413.5 | 9.85 | **no** | `b200_sxm-x87-tensor` | 102.0 | 85.5-85.5 | 5.96 | **no** | 7.987x | 4.834x | 0.605x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 2,351.7 | 1,857.1-1,857.1 | 6.33 | **no** | `b200_sxm-x116-tensor` | 104.0 | 84.4-84.4 | 6.16 | **no** | 22.611x | 22.016x | 0.974x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227` | 627.5 | 326.9-326.9 | 9.60 | **no** | `b200_sxm-x116-hybrid` | 51.0 | 112.9-112.9 | 2.26 | yes | 12.304x | 2.895x | 0.235x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,008.8 | 1,572.7-1,572.7 | 6.39 | **no** | `b200_sxm-x347-hybrid` | 36.4 | 85.0-85.0 | 2.14 | yes | 55.203x | 18.508x | 0.335x |

**Does the ratio compress?** Of 16 class rows in this study, 15 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.235x to 1.099x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 7 of 16 ROM rows and 12 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x48` | 1,449.0 | 1,273.6-1,273.6 | 5.69 | **no** | `a100_sxm_80gb-x47-tensor` | 699.8 | 1,686.8-1,686.8 | 2.07 | yes | 2.071x | 0.755x | 0.365x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 4,707.9 | 8,457.5-8,457.5 | 2.78 | yes | `a100_sxm_80gb-x56-tensor` | 715.0 | 1,739.2-1,739.2 | 2.06 | yes | 6.585x | 4.863x | 0.739x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 1,449.0 | 1,217.3-1,217.3 | 5.95 | **no** | `a100_sxm_80gb-x46-tensor` | 584.2 | 1,178.4-1,178.4 | 2.48 | yes | 2.480x | 1.033x | 0.416x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 3,388.5 | 7,603.9-7,603.9 | 2.23 | yes | `a100_sxm_80gb-x168-tensor` | 684.0 | 1,414.9-1,414.9 | 2.42 | yes | 4.954x | 5.374x | 1.085x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 1,449.0 | 1,217.3-1,217.3 | 5.95 | **no** | `a100_sxm_80gb-x46-tensor` | 463.5 | 784.6-784.6 | 2.95 | yes | 3.126x | 1.552x | 0.496x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 3,331.4 | 7,537.2-7,537.2 | 2.21 | yes | `a100_sxm_80gb-x224-tensor` | 565.2 | 954.8-954.8 | 2.96 | yes | 5.895x | 7.894x | 1.339x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 1,366.3 | 1,276.7-1,276.7 | 5.35 | **no** | `a100_sxm_80gb-x55-tensor` | 355.3 | 518.4-518.4 | 3.43 | yes | 3.846x | 2.463x | 0.640x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,121.2 | 7,281.8-7,281.8 | 2.14 | yes | `a100_sxm_80gb-x448-tensor` | 391.8 | 579.1-579.1 | 3.38 | yes | 7.966x | 12.574x | 1.578x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 1,290.9 | 961.2-961.2 | 6.72 | **no** | `a100_sxm_80gb-x55-tensor` | 245.8 | 319.9-319.9 | 3.84 | yes | 5.252x | 3.005x | 0.572x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,656.1 | 6,690.6-6,690.6 | 1.98 | yes | `a100_sxm_80gb-x672-tensor` | 298.2 | 338.7-338.7 | 4.40 | yes | 8.908x | 19.756x | 2.218x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x111-romfill` | 1,211.2 | 970.6-970.6 | 6.24 | **no** | `a100_sxm_80gb-x110-tensor` | 182.6 | 185.6-185.6 | 4.92 | yes | 6.635x | 5.229x | 0.788x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,922.9 | 5,574.4-5,574.4 | 1.72 | yes | `a100_sxm_80gb-x672-tensor` | 201.6 | 184.6-184.6 | 5.46 | **no** | 9.540x | 30.203x | 3.166x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x170-romfill` | 1,149.9 | 846.8-846.8 | 6.79 | **no** | `a100_sxm_80gb-x168-tensor` | 118.5 | 97.7-97.7 | 6.07 | **no** | 9.707x | 8.671x | 0.893x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,238.9 | 1,105.2-1,105.2 | 5.60 | **no** | `a100_sxm_80gb-x672-tensor` | 124.3 | 96.7-96.7 | 6.43 | **no** | 9.966x | 11.428x | 1.147x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x340-romfill` | 746.5 | 561.4-561.4 | 6.65 | **no** | `a100_sxm_80gb-x335-tensor` | 38.4 | 24.8-24.8 | 7.73 | **no** | 19.450x | 22.604x | 1.162x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 395.3 | 791.2-791.2 | 2.50 | yes | `a100_sxm_80gb-x672-tensor` | 39.0 | 24.9-24.9 | 7.83 | **no** | 10.133x | 31.744x | 3.133x |

**Does the ratio compress?** Of 16 class rows in this study, 8 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.365x to 3.166x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 7 of 16 ROM rows and 11 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x37` | 1,539.7 | 1,493.8-1,493.8 | 5.15 | **no** | `a100_sxm_80gb-x37-tensor` | 687.1 | 1,619.5-1,619.5 | 2.12 | yes | 2.241x | 0.922x | 0.412x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 4,707.9 | 9,989.1-9,989.1 | 2.36 | yes | `a100_sxm_80gb-x56-tensor` | 723.1 | 1,748.8-1,748.8 | 2.07 | yes | 6.511x | 5.712x | 0.877x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 1,539.7 | 1,519.1-1,519.1 | 5.07 | **no** | `a100_sxm_80gb-x39-tensor` | 583.2 | 1,152.9-1,152.9 | 2.53 | yes | 2.640x | 1.318x | 0.499x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 4,707.9 | 9,585.0-9,585.0 | 2.46 | yes | `a100_sxm_80gb-x56-tensor` | 614.5 | 1,233.9-1,233.9 | 2.49 | yes | 7.662x | 7.768x | 1.014x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 1,539.7 | 1,519.1-1,519.1 | 5.07 | **no** | `a100_sxm_80gb-x39-tensor` | 467.8 | 772.0-772.0 | 3.03 | yes | 3.292x | 1.968x | 0.598x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 4,707.9 | 8,662.2-8,662.2 | 2.72 | yes | `a100_sxm_80gb-x56-tensor` | 495.2 | 822.5-822.5 | 3.01 | yes | 9.508x | 10.532x | 1.108x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 1,443.6 | 1,669.9-1,669.9 | 4.32 | yes | `a100_sxm_80gb-x46-tensor` | 360.8 | 513.3-513.3 | 3.51 | yes | 4.001x | 3.253x | 0.813x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 4,707.9 | 7,263.7-7,263.7 | 3.24 | yes | `a100_sxm_80gb-x56-tensor` | 373.5 | 527.3-527.3 | 3.54 | yes | 12.604x | 13.776x | 1.093x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 1,422.2 | 1,363.8-1,363.8 | 5.21 | **no** | `a100_sxm_80gb-x46-tensor` | 253.7 | 322.0-322.0 | 3.94 | yes | 5.606x | 4.235x | 0.755x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,406.4 | 6,617.5-6,617.5 | 3.33 | yes | `a100_sxm_80gb-x112-tensor` | 290.7 | 333.7-333.7 | 4.36 | yes | 15.155x | 19.830x | 1.308x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 1,316.1 | 1,197.2-1,197.2 | 5.50 | **no** | `a100_sxm_80gb-x55-tensor` | 174.7 | 190.3-190.3 | 4.59 | yes | 7.535x | 6.291x | 0.835x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 4,205.0 | 6,462.1-6,462.1 | 3.25 | yes | `a100_sxm_80gb-x224-tensor` | 204.7 | 186.9-186.9 | 5.48 | **no** | 20.543x | 34.580x | 1.683x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x57` | 1,203.9 | 854.6-854.6 | 7.04 | **no** | `a100_sxm_80gb-x56-tensor` | 112.3 | 104.6-104.6 | 5.37 | **no** | 10.720x | 8.169x | 0.762x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill` | 3,915.3 | 5,764.5-5,764.5 | 3.40 | yes | `a100_sxm_80gb-x336-tensor` | 122.6 | 97.2-97.2 | 6.30 | **no** | 31.935x | 59.279x | 1.856x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 1,028.9 | 811.0-811.0 | 6.34 | **no** | `a100_sxm_80gb-x224-hybrid` | 42.4 | 100.8-100.8 | 2.10 | yes | 24.290x | 8.048x | 0.331x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,899.7 | 3,964.9-3,964.9 | 3.66 | yes | `a100_sxm_80gb-x672-tensor` | 39.5 | 25.1-25.1 | 7.87 | **no** | 73.359x | 157.817x | 2.151x |

**Does the ratio compress?** Of 16 class rows in this study, 9 move the ROM-versus-GPU ratio DOWN under speculation and 7 move it UP. The movement spans 0.331x to 2.151x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 9 of 16 ROM rows and 12 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x37` | 1,539.7 | 1,554.4-1,554.4 | 4.95 | yes | `a100_sxm_80gb-x37-tensor` | 687.3 | 1,619.8-1,619.8 | 2.12 | yes | 2.240x | 0.960x | 0.428x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 4,707.9 | 9,989.1-9,989.1 | 2.36 | yes | `a100_sxm_80gb-x56-tensor` | 723.3 | 1,749.0-1,749.0 | 2.07 | yes | 6.509x | 5.711x | 0.877x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 1,539.7 | 1,562.0-1,562.0 | 4.93 | yes | `a100_sxm_80gb-x39-tensor` | 583.6 | 1,153.2-1,153.2 | 2.53 | yes | 2.639x | 1.354x | 0.513x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 4,707.9 | 9,661.6-9,661.6 | 2.44 | yes | `a100_sxm_80gb-x56-tensor` | 614.8 | 1,234.2-1,234.2 | 2.49 | yes | 7.658x | 7.828x | 1.022x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 1,539.7 | 1,562.0-1,562.0 | 4.93 | yes | `a100_sxm_80gb-x39-tensor` | 468.3 | 772.3-772.3 | 3.03 | yes | 3.288x | 2.023x | 0.615x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 4,707.9 | 8,788.2-8,788.2 | 2.68 | yes | `a100_sxm_80gb-x56-tensor` | 495.6 | 822.7-822.7 | 3.01 | yes | 9.500x | 10.682x | 1.124x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 1,455.3 | 1,277.7-1,277.7 | 5.70 | **no** | `a100_sxm_80gb-x39-tensor` | 350.7 | 503.6-503.6 | 3.48 | yes | 4.149x | 2.537x | 0.611x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 4,707.9 | 7,442.6-7,442.6 | 3.16 | yes | `a100_sxm_80gb-x56-tensor` | 374.0 | 527.4-527.4 | 3.55 | yes | 12.589x | 14.111x | 1.121x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 1,422.2 | 1,396.9-1,396.9 | 5.09 | **no** | `a100_sxm_80gb-x46-tensor` | 254.2 | 322.2-322.2 | 3.94 | yes | 5.595x | 4.336x | 0.775x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,406.4 | 6,755.7-6,755.7 | 3.26 | yes | `a100_sxm_80gb-x112-tensor` | 291.0 | 333.8-333.8 | 4.36 | yes | 15.141x | 20.240x | 1.337x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 1,316.1 | 1,224.0-1,224.0 | 5.38 | **no** | `a100_sxm_80gb-x55-tensor` | 175.1 | 190.4-190.4 | 4.60 | yes | 7.518x | 6.428x | 0.855x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,312.9 | 5,341.6-5,341.6 | 4.04 | yes | `a100_sxm_80gb-x112-tensor` | 192.3 | 187.6-187.6 | 5.12 | **no** | 22.434x | 28.470x | 1.269x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 1,230.1 | 902.7-902.7 | 6.81 | **no** | `a100_sxm_80gb-x55-tensor` | 112.2 | 104.6-104.6 | 5.37 | **no** | 10.961x | 8.631x | 0.787x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 4,104.9 | 5,199.2-5,199.2 | 3.95 | yes | `a100_sxm_80gb-x224-tensor` | 125.6 | 98.5-98.5 | 6.37 | **no** | 32.692x | 52.794x | 1.615x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 1,040.2 | 847.9-847.9 | 6.13 | **no** | `a100_sxm_80gb-x224-hybrid` | 42.4 | 100.8-100.8 | 2.10 | yes | 24.530x | 8.410x | 0.343x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,227.7 | 4,098.8-4,098.8 | 3.94 | yes | `a100_sxm_80gb-x672-tensor` | 39.5 | 25.1-25.1 | 7.87 | **no** | 81.627x | 163.143x | 1.999x |

**Does the ratio compress?** Of 16 class rows in this study, 9 move the ROM-versus-GPU ratio DOWN under speculation and 7 move it UP. The movement spans 0.343x to 1.999x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 11 of 16 ROM rows and 12 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x194` | 725.7 | 1,389.1-1,389.1 | 2.61 | yes | `a100_sxm_80gb-x191-tensor` | 355.1 | 805.0-805.0 | 2.21 | yes | 2.044x | 1.726x | 0.844x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 2,375.7 | 2,805.8-2,805.8 | 4.23 | yes | `a100_sxm_80gb-x224-tensor` | 358.3 | 819.8-819.8 | 2.19 | yes | 6.630x | 3.423x | 0.516x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x227` | 626.1 | 932.7-932.7 | 3.36 | yes | `a100_sxm_80gb-x224-tensor` | 307.4 | 562.6-562.6 | 2.73 | yes | 2.037x | 1.658x | 0.814x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,375.7 | 2,789.3-2,789.3 | 4.26 | yes | `a100_sxm_80gb-x224-tensor` | 307.4 | 562.6-562.6 | 2.73 | yes | 7.729x | 4.958x | 0.641x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x208` | 578.9 | 292.7-292.7 | 9.89 | **no** | `a100_sxm_80gb-x205-tensor` | 230.8 | 358.6-358.6 | 3.22 | yes | 2.508x | 0.816x | 0.325x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,375.7 | 2,789.3-2,789.3 | 4.26 | yes | `a100_sxm_80gb-x224-tensor` | 233.7 | 363.0-363.0 | 3.22 | yes | 10.167x | 7.685x | 0.756x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x208` | 578.9 | 292.7-292.7 | 9.89 | **no** | `a100_sxm_80gb-x205-tensor` | 170.1 | 219.7-219.7 | 3.87 | yes | 3.405x | 1.332x | 0.391x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,374.1 | 2,404.9-2,404.9 | 4.94 | yes | `a100_sxm_80gb-x224-tensor` | 171.8 | 221.9-221.9 | 3.87 | yes | 13.822x | 10.837x | 0.784x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x208` | 578.9 | 292.7-292.7 | 9.89 | **no** | `a100_sxm_80gb-x205-tensor` | 116.3 | 129.4-129.4 | 4.50 | yes | 4.977x | 2.263x | 0.455x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,370.9 | 1,885.3-1,885.3 | 6.29 | **no** | `a100_sxm_80gb-x224-tensor` | 117.8 | 130.2-130.2 | 4.52 | yes | 20.124x | 14.478x | 0.719x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 546.6 | 373.9-373.9 | 7.31 | **no** | `a100_sxm_80gb-x224-tensor` | 76.0 | 73.3-73.3 | 5.18 | **no** | 7.196x | 5.102x | 0.709x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,961.6 | 1,810.8-1,810.8 | 5.42 | **no** | `a100_sxm_80gb-x336-tensor` | 76.5 | 73.5-73.5 | 5.20 | **no** | 25.635x | 24.631x | 0.961x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 536.4 | 291.7-291.7 | 9.20 | **no** | `a100_sxm_80gb-x224-tensor` | 46.4 | 39.4-39.4 | 5.89 | **no** | 11.558x | 7.399x | 0.640x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,831.2 | 1,764.1-1,764.1 | 5.19 | **no** | `a100_sxm_80gb-x672-tensor` | 49.5 | 39.4-39.4 | 6.28 | **no** | 37.010x | 44.768x | 1.210x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x297` | 416.0 | 221.1-221.1 | 9.41 | **no** | `a100_sxm_80gb-x293-tensor` | 15.4 | 10.4-10.4 | 7.42 | **no** | 26.950x | 21.259x | 0.789x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 961.1 | 874.7-874.7 | 5.49 | **no** | `a100_sxm_80gb-x672-tensor` | 15.6 | 10.3-10.3 | 7.59 | **no** | 61.480x | 84.991x | 1.382x |

**Does the ratio compress?** Of 16 class rows in this study, 14 move the ROM-versus-GPU ratio DOWN under speculation and 2 move it UP. The movement spans 0.325x to 1.382x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 6 of 16 ROM rows and 10 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x191` | 725.9 | 1,387.9-1,387.9 | 2.61 | yes | `a100_sxm_80gb-x188-tensor` | 354.9 | 803.5-803.5 | 2.21 | yes | 2.045x | 1.727x | 0.845x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 2,375.7 | 2,903.6-2,903.6 | 4.09 | yes | `a100_sxm_80gb-x224-tensor` | 358.4 | 819.9-819.9 | 2.19 | yes | 6.628x | 3.541x | 0.534x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x227` | 626.1 | 940.5-940.5 | 3.33 | yes | `a100_sxm_80gb-x224-tensor` | 307.6 | 562.7-562.7 | 2.73 | yes | 2.036x | 1.671x | 0.821x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,375.7 | 2,882.6-2,882.6 | 4.12 | yes | `a100_sxm_80gb-x224-tensor` | 307.6 | 562.7-562.7 | 2.73 | yes | 7.724x | 5.123x | 0.663x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 581.5 | 293.8-293.8 | 9.90 | **no** | `a100_sxm_80gb-x203-tensor` | 230.7 | 358.2-358.2 | 3.22 | yes | 2.520x | 0.820x | 0.325x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,375.7 | 2,882.6-2,882.6 | 4.12 | yes | `a100_sxm_80gb-x224-tensor` | 233.9 | 363.1-363.1 | 3.22 | yes | 10.158x | 7.940x | 0.782x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 581.5 | 293.8-293.8 | 9.90 | **no** | `a100_sxm_80gb-x203-tensor` | 170.1 | 219.5-219.5 | 3.87 | yes | 3.419x | 1.338x | 0.391x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,374.1 | 2,547.1-2,547.1 | 4.66 | yes | `a100_sxm_80gb-x224-tensor` | 172.0 | 222.0-222.0 | 3.87 | yes | 13.803x | 11.474x | 0.831x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 581.5 | 293.8-293.8 | 9.90 | **no** | `a100_sxm_80gb-x203-tensor` | 116.4 | 129.3-129.3 | 4.50 | yes | 4.997x | 2.272x | 0.455x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,370.9 | 2,066.2-2,066.2 | 5.74 | **no** | `a100_sxm_80gb-x224-tensor` | 118.0 | 130.3-130.3 | 4.53 | yes | 20.087x | 15.860x | 0.790x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 546.6 | 394.9-394.9 | 6.92 | **no** | `a100_sxm_80gb-x224-tensor` | 76.1 | 73.3-73.3 | 5.19 | **no** | 7.179x | 5.386x | 0.750x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,016.9 | 1,499.8-1,499.8 | 6.72 | **no** | `a100_sxm_80gb-x224-tensor` | 76.1 | 73.3-73.3 | 5.19 | **no** | 26.490x | 20.457x | 0.772x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 536.4 | 318.1-318.1 | 8.43 | **no** | `a100_sxm_80gb-x224-tensor` | 46.5 | 39.4-39.4 | 5.90 | **no** | 11.524x | 8.064x | 0.700x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,951.9 | 1,590.5-1,590.5 | 6.14 | **no** | `a100_sxm_80gb-x336-tensor` | 47.2 | 39.3-39.3 | 6.00 | **no** | 41.366x | 40.464x | 0.978x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x297` | 416.0 | 238.7-238.7 | 8.71 | **no** | `a100_sxm_80gb-x293-tensor` | 15.5 | 10.4-10.4 | 7.44 | **no** | 26.870x | 22.944x | 0.854x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,758.1 | 1,166.5-1,166.5 | 7.54 | **no** | `a100_sxm_80gb-x672-tensor` | 15.7 | 10.3-10.3 | 7.60 | **no** | 112.323x | 113.327x | 1.009x |

**Does the ratio compress?** Of 16 class rows in this study, 15 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.325x to 1.009x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 6 of 16 ROM rows and 10 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x191` | 725.9 | 1,394.1-1,394.1 | 2.60 | yes | `a100_sxm_80gb-x188-tensor` | 354.9 | 803.5-803.5 | 2.21 | yes | 2.045x | 1.735x | 0.848x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 2,375.7 | 2,918.2-2,918.2 | 4.07 | yes | `a100_sxm_80gb-x224-tensor` | 358.4 | 819.9-819.9 | 2.19 | yes | 6.628x | 3.559x | 0.537x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x227` | 626.1 | 941.7-941.7 | 3.32 | yes | `a100_sxm_80gb-x224-tensor` | 307.6 | 562.8-562.8 | 2.73 | yes | 2.035x | 1.673x | 0.822x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,375.7 | 2,896.9-2,896.9 | 4.10 | yes | `a100_sxm_80gb-x224-tensor` | 307.6 | 562.8-562.8 | 2.73 | yes | 7.723x | 5.148x | 0.667x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 587.0 | 299.2-299.2 | 9.81 | **no** | `a100_sxm_80gb-x203-tensor` | 230.8 | 358.2-358.2 | 3.22 | yes | 2.544x | 0.835x | 0.328x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,375.7 | 2,896.9-2,896.9 | 4.10 | yes | `a100_sxm_80gb-x224-tensor` | 233.9 | 363.1-363.1 | 3.22 | yes | 10.157x | 7.979x | 0.786x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 587.0 | 299.2-299.2 | 9.81 | **no** | `a100_sxm_80gb-x203-tensor` | 170.1 | 219.6-219.6 | 3.87 | yes | 3.450x | 1.363x | 0.395x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,374.1 | 2,569.5-2,569.5 | 4.62 | yes | `a100_sxm_80gb-x224-tensor` | 172.0 | 222.0-222.0 | 3.87 | yes | 13.800x | 11.574x | 0.839x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 587.0 | 299.2-299.2 | 9.81 | **no** | `a100_sxm_80gb-x203-tensor` | 116.4 | 129.3-129.3 | 4.50 | yes | 5.042x | 2.314x | 0.459x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,370.9 | 2,095.7-2,095.7 | 5.66 | **no** | `a100_sxm_80gb-x224-tensor` | 118.1 | 130.3-130.3 | 4.53 | yes | 20.081x | 16.086x | 0.801x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 546.6 | 398.2-398.2 | 6.86 | **no** | `a100_sxm_80gb-x224-tensor` | 76.2 | 73.3-73.3 | 5.19 | **no** | 7.176x | 5.431x | 0.757x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,052.2 | 1,531.1-1,531.1 | 6.70 | **no** | `a100_sxm_80gb-x224-tensor` | 76.2 | 73.3-73.3 | 5.19 | **no** | 26.945x | 20.883x | 0.775x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 536.4 | 322.3-322.3 | 8.32 | **no** | `a100_sxm_80gb-x224-tensor` | 46.6 | 39.4-39.4 | 5.90 | **no** | 11.519x | 8.172x | 0.709x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,951.9 | 1,609.3-1,609.3 | 6.06 | **no** | `a100_sxm_80gb-x336-tensor` | 47.2 | 39.3-39.3 | 6.00 | **no** | 41.354x | 40.939x | 0.990x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x297` | 416.0 | 245.0-245.0 | 8.49 | **no** | `a100_sxm_80gb-x293-tensor` | 15.5 | 10.4-10.4 | 7.44 | **no** | 26.858x | 23.543x | 0.877x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,776.5 | 1,186.5-1,186.5 | 7.49 | **no** | `a100_sxm_80gb-x672-tensor` | 15.7 | 10.3-10.3 | 7.60 | **no** | 113.474x | 115.264x | 1.016x |

**Does the ratio compress?** Of 16 class rows in this study, 15 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.328x to 1.016x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 6 of 16 ROM rows and 10 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-pipeline-x8-romfill` | 5,027.2 | not applicable | -- | -- | `b200_sxm-x4-tensor` | 1,232.0 | not applicable | -- | -- | 4.080x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | not applicable | -- | -- | `b200_sxm-x29-hybrid` | 1,866.3 | not applicable | -- | -- | 3.464x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x16-romfill` | 4,528.6 | not applicable | -- | -- | `b200_sxm-x8-tensor` | 1,917.0 | not applicable | -- | -- | 2.362x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,400.8 | not applicable | -- | -- | `b200_sxm-x58-hybrid` | 1,836.2 | not applicable | -- | -- | 2.941x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x57-romfill` | 4,191.8 | not applicable | -- | -- | `b200_sxm-x29-hybrid` | 1,866.3 | not applicable | -- | -- | 2.246x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 5,121.2 | not applicable | -- | -- | `b200_sxm-x116-hybrid` | 1,858.0 | not applicable | -- | -- | 2.756x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x57-romfill` | 4,191.8 | not applicable | -- | -- | `b200_sxm-x29-hybrid` | 1,773.8 | not applicable | -- | -- | 2.363x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,640.7 | not applicable | -- | -- | `b200_sxm-x231-hybrid` | 1,787.5 | not applicable | -- | -- | 2.596x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x113-romfill` | 3,928.4 | not applicable | -- | -- | `b200_sxm-x58-hybrid` | 1,744.6 | not applicable | -- | -- | 2.252x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,040.9 | not applicable | -- | -- | `b200_sxm-x347-hybrid` | 1,730.2 | not applicable | -- | -- | 2.336x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227-romfill` | 3,503.0 | not applicable | -- | -- | `b200_sxm-x116-hybrid` | 1,754.1 | not applicable | -- | -- | 1.997x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,395.4 | not applicable | -- | -- | `b200_sxm-x347-hybrid` | 1,730.2 | not applicable | -- | -- | 1.962x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 3,145.5 | not applicable | -- | -- | `b200_sxm-x173-hybrid` | 1,657.6 | not applicable | -- | -- | 1.898x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,573.2 | not applicable | -- | -- | `b200_sxm-x347-hybrid` | 1,688.9 | not applicable | -- | -- | 1.524x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-pipeline-x340-romfill` | 2,343.2 | not applicable | -- | -- | `b200_sxm-x173-hybrid` | 1,169.3 | not applicable | -- | -- | 2.004x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,049.1 | not applicable | -- | -- | `b200_sxm-x347-hybrid` | 1,374.0 | not applicable | -- | -- | 0.764x | -- | -- |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hybrid-x30` | 2,627.4 | 2,062.0-2,062.0 | 6.37 | **no** | `b200_sxm-x15-hybrid` | 1,465.1 | 3,141.8-3,141.8 | 2.33 | yes | 1.793x | 0.656x | 0.366x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 4,850.6 | 11,253.4-11,253.4 | 2.16 | yes | `b200_sxm-x29-tensor` | 1,300.7 | 3,676.6-3,676.6 | 1.77 | yes | 3.729x | 3.061x | 0.821x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x32` | 2,627.4 | 2,100.1-2,100.1 | 6.26 | **no** | `b200_sxm-x16-hybrid` | 1,499.3 | 3,244.8-3,244.8 | 2.31 | yes | 1.752x | 0.647x | 0.369x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,849.3 | 10,700.0-10,700.0 | 2.27 | yes | `b200_sxm-x29-tensor` | 1,161.6 | 2,695.9-2,695.9 | 2.15 | yes | 4.175x | 3.969x | 0.951x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x32` | 2,627.4 | 2,100.1-2,100.1 | 6.26 | **no** | `b200_sxm-x16-hybrid` | 1,215.6 | 2,280.1-2,280.1 | 2.67 | yes | 2.161x | 0.921x | 0.426x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,744.7 | 9,651.6-9,651.6 | 2.46 | yes | `b200_sxm-x29-hybrid` | 1,116.3 | 2,362.7-2,362.7 | 2.36 | yes | 4.250x | 4.085x | 0.961x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,365.6 | 1,990.5-1,990.5 | 5.94 | **no** | `b200_sxm-x19-hybrid` | 856.3 | 1,505.9-1,505.9 | 2.84 | yes | 2.762x | 1.322x | 0.479x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,553.2 | 8,901.9-8,901.9 | 2.56 | yes | `b200_sxm-x58-tensor` | 832.4 | 1,219.9-1,219.9 | 3.41 | yes | 5.470x | 7.297x | 1.334x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,341.6 | 1,538.8-1,538.8 | 7.61 | **no** | `b200_sxm-x19-hybrid` | 633.5 | 1,079.6-1,079.6 | 2.93 | yes | 3.696x | 1.425x | 0.386x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,346.7 | 8,678.8-8,678.8 | 2.50 | yes | `b200_sxm-x116-tensor` | 639.9 | 721.2-721.2 | 4.44 | yes | 6.792x | 12.035x | 1.772x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 2,109.5 | 1,341.4-1,341.4 | 7.86 | **no** | `b200_sxm-x22-hybrid` | 482.7 | 929.5-929.5 | 2.60 | yes | 4.371x | 1.443x | 0.330x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,985.1 | 8,264.6-8,264.6 | 2.41 | yes | `b200_sxm-x231-tensor` | 440.6 | 389.7-389.7 | 5.65 | **no** | 9.045x | 21.206x | 2.344x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x87-romfill` | 1,994.8 | 1,380.2-1,380.2 | 7.23 | **no** | `b200_sxm-x44-hybrid` | 360.3 | 742.7-742.7 | 2.43 | yes | 5.537x | 1.858x | 0.336x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,511.7 | 7,371.2-7,371.2 | 2.38 | yes | `b200_sxm-x347-tensor` | 271.2 | 201.8-201.8 | 6.72 | **no** | 12.950x | 36.523x | 2.820x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227-romfill` | 1,731.6 | 1,070.7-1,070.7 | 8.09 | **no** | `b200_sxm-x116-hybrid` | 184.7 | 472.1-472.1 | 1.96 | yes | 9.376x | 2.268x | 0.242x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,271.5 | 4,126.2-4,126.2 | 2.75 | yes | `b200_sxm-x347-hybrid` | 131.8 | 322.6-322.6 | 2.04 | yes | 17.239x | 12.789x | 0.742x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 1,062.3 | 2,499.1-2,499.1 | 2.13 | yes | `b200_sxm-x173-tensor` | 773.0 | 1,943.9-1,943.9 | 1.99 | yes | 1.374x | 1.286x | 0.935x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 2,648.8 | 2,991.0-2,991.0 | 4.43 | yes | `b200_sxm-x87-tensor` | 746.8 | 1,817.6-1,817.6 | 2.05 | yes | 3.547x | 1.646x | 0.464x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 951.6 | 1,695.8-1,695.8 | 2.81 | yes | `b200_sxm-x173-tensor` | 677.0 | 1,336.0-1,336.0 | 2.53 | yes | 1.406x | 1.269x | 0.903x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.8 | 3,054.4-3,054.4 | 4.34 | yes | `b200_sxm-x87-tensor` | 638.3 | 1,249.9-1,249.9 | 2.55 | yes | 4.150x | 2.444x | 0.589x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x167` | 843.5 | 370.9-370.9 | 11.37 | **no** | `b200_sxm-x85-tensor` | 505.3 | 796.8-796.8 | 3.17 | yes | 1.669x | 0.465x | 0.279x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.3 | 2,801.9-2,801.9 | 4.73 | yes | `b200_sxm-x87-tensor` | 506.7 | 799.7-799.7 | 3.17 | yes | 5.227x | 3.504x | 0.670x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x167` | 843.5 | 370.9-370.9 | 11.37 | **no** | `b200_sxm-x85-tensor` | 376.1 | 483.1-483.1 | 3.89 | yes | 2.243x | 0.768x | 0.342x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 2,374.1 | 2,657.5-2,657.5 | 4.47 | yes | `b200_sxm-x116-tensor` | 390.3 | 494.7-494.7 | 3.95 | yes | 6.082x | 5.372x | 0.883x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x167` | 843.5 | 370.9-370.9 | 11.37 | **no** | `b200_sxm-x85-tensor` | 257.5 | 281.9-281.9 | 4.57 | yes | 3.275x | 1.316x | 0.402x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 2,233.4 | 2,410.4-2,410.4 | 4.63 | yes | `b200_sxm-x173-tensor` | 278.2 | 288.9-288.9 | 4.81 | yes | 8.028x | 8.342x | 1.039x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x193` | 750.8 | 433.9-433.9 | 8.65 | **no** | `b200_sxm-x98-tensor` | 166.8 | 157.8-157.8 | 5.28 | **no** | 4.502x | 2.749x | 0.611x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,086.5 | 2,360.0-2,360.0 | 4.42 | yes | `b200_sxm-x347-tensor` | 185.6 | 158.3-158.3 | 5.86 | **no** | 11.239x | 14.910x | 1.327x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x193` | 742.3 | 333.1-333.1 | 11.14 | **no** | `b200_sxm-x98-tensor` | 100.4 | 84.4-84.4 | 5.94 | **no** | 7.394x | 3.945x | 0.534x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,535.9 | 1,945.2-1,945.2 | 3.95 | yes | `b200_sxm-x347-tensor` | 109.5 | 82.6-82.6 | 6.63 | **no** | 14.032x | 23.557x | 1.679x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x308-romfill` | 561.1 | 253.9-253.9 | 11.05 | **no** | `b200_sxm-x157-hybrid` | 47.1 | 104.4-104.4 | 2.26 | yes | 11.914x | 2.432x | 0.204x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 594.5 | 830.9-830.9 | 3.58 | yes | `b200_sxm-x347-hybrid` | 36.1 | 84.6-84.6 | 2.13 | yes | 16.483x | 9.819x | 0.596x |

**Does the ratio compress?** Of 32 class rows in this study, 25 move the ROM-versus-GPU ratio DOWN under speculation and 7 move it UP. The movement spans 0.204x to 2.820x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 18 of 32 ROM rows and 26 of 32 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-pipeline-x8-romfill` | 3,524.3 | not applicable | -- | -- | `a100_sxm_80gb-x8-tensor` | 621.5 | not applicable | -- | -- | 5.671x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 1,109.0 | not applicable | -- | -- | 5.829x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x15` | 2,119.2 | not applicable | -- | -- | `a100_sxm_80gb-x15-tensor` | 690.2 | not applicable | -- | -- | 3.070x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4,245.8 | not applicable | -- | -- | `a100_sxm_80gb-x112-tensor` | 1,116.3 | not applicable | -- | -- | 3.803x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x57-romfill` | 2,036.0 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 878.5 | not applicable | -- | -- | 2.318x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 4,071.0 | not applicable | -- | -- | `a100_sxm_80gb-x224-tensor` | 993.3 | not applicable | -- | -- | 4.099x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x57-romfill` | 2,036.0 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 687.8 | not applicable | -- | -- | 2.960x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,761.4 | not applicable | -- | -- | `a100_sxm_80gb-x448-tensor` | 632.0 | not applicable | -- | -- | 5.952x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x113-romfill` | 1,963.8 | not applicable | -- | -- | `a100_sxm_80gb-x111-hybrid` | 600.5 | not applicable | -- | -- | 3.270x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,178.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 591.2 | not applicable | -- | -- | 5.376x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 1,843.0 | not applicable | -- | -- | `a100_sxm_80gb-x224-hybrid` | 592.5 | not applicable | -- | -- | 3.111x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,331.9 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 591.2 | not applicable | -- | -- | 3.945x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x340-romfill` | 1,665.8 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 570.8 | not applicable | -- | -- | 2.918x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,521.5 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 591.2 | not applicable | -- | -- | 2.574x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-pipeline-x340-romfill` | 1,210.5 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 445.0 | not applicable | -- | -- | 2.720x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 493.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 522.8 | not applicable | -- | -- | 0.943x | -- | -- |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x39` | 1,539.7 | 1,505.3-1,505.3 | 5.11 | **no** | `a100_sxm_80gb-x38-tensor` | 687.9 | 1,628.0-1,628.0 | 2.11 | yes | 2.238x | 0.925x | 0.413x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 4,707.9 | 9,842.1-9,842.1 | 2.39 | yes | `a100_sxm_80gb-x56-tensor` | 721.7 | 1,747.1-1,747.1 | 2.07 | yes | 6.523x | 5.633x | 0.864x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 1,456.6 | 1,280.1-1,280.1 | 5.69 | **no** | `a100_sxm_80gb-x39-tensor` | 580.5 | 1,150.8-1,150.8 | 2.52 | yes | 2.509x | 1.112x | 0.443x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 4,583.4 | 9,094.3-9,094.3 | 2.52 | yes | `a100_sxm_80gb-x56-tensor` | 612.4 | 1,232.3-1,232.3 | 2.48 | yes | 7.484x | 7.380x | 0.986x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 1,456.6 | 1,280.1-1,280.1 | 5.69 | **no** | `a100_sxm_80gb-x39-tensor` | 464.4 | 770.1-770.1 | 3.01 | yes | 3.137x | 1.662x | 0.530x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,390.6 | 8,021.5-8,021.5 | 2.74 | yes | `a100_sxm_80gb-x112-tensor` | 533.8 | 898.3-898.3 | 2.97 | yes | 8.225x | 8.930x | 1.086x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 1,443.6 | 1,520.0-1,520.0 | 4.75 | yes | `a100_sxm_80gb-x46-tensor` | 357.4 | 511.9-511.9 | 3.49 | yes | 4.039x | 2.969x | 0.735x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 4,202.1 | 7,862.9-7,862.9 | 2.67 | yes | `a100_sxm_80gb-x224-tensor` | 437.5 | 586.7-586.7 | 3.73 | yes | 9.605x | 13.401x | 1.395x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 1,422.2 | 1,174.6-1,174.6 | 6.05 | **no** | `a100_sxm_80gb-x46-tensor` | 250.3 | 320.9-320.9 | 3.90 | yes | 5.682x | 3.660x | 0.644x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,869.7 | 7,564.0-7,564.0 | 2.56 | yes | `a100_sxm_80gb-x448-tensor` | 294.6 | 336.6-336.6 | 4.38 | yes | 13.136x | 22.469x | 1.711x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 1,316.1 | 1,042.1-1,042.1 | 6.31 | **no** | `a100_sxm_80gb-x55-tensor` | 172.0 | 189.7-189.7 | 4.53 | yes | 7.652x | 5.494x | 0.718x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,399.6 | 6,986.6-6,986.6 | 2.43 | yes | `a100_sxm_80gb-x672-tensor` | 203.0 | 184.8-184.8 | 5.49 | **no** | 16.748x | 37.806x | 2.257x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x111-romfill` | 1,177.3 | 1,012.2-1,012.2 | 5.82 | **no** | `a100_sxm_80gb-x110-tensor` | 118.4 | 100.1-100.1 | 5.91 | **no** | 9.946x | 10.116x | 1.017x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,814.0 | 5,997.8-5,997.8 | 2.35 | yes | `a100_sxm_80gb-x672-tensor` | 125.4 | 96.8-96.8 | 6.47 | **no** | 22.442x | 61.935x | 2.760x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 1,028.9 | 707.8-707.8 | 7.27 | **no** | `a100_sxm_80gb-x224-hybrid` | 42.0 | 100.4-100.4 | 2.09 | yes | 24.469x | 7.049x | 0.288x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,383.8 | 1,108.0-1,108.0 | 6.24 | **no** | `a100_sxm_80gb-x672-tensor` | 39.4 | 25.1-25.1 | 7.85 | **no** | 35.089x | 44.116x | 1.257x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x207` | 725.5 | 1,384.5-1,384.5 | 2.62 | yes | `a100_sxm_80gb-x204-tensor` | 355.8 | 810.5-810.5 | 2.19 | yes | 2.039x | 1.708x | 0.838x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 2,375.7 | 2,376.4-2,376.4 | 5.00 | yes | `a100_sxm_80gb-x224-tensor` | 357.7 | 819.1-819.1 | 2.18 | yes | 6.642x | 2.901x | 0.437x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x248` | 625.8 | 925.8-925.8 | 3.38 | yes | `a100_sxm_80gb-x245-tensor` | 309.3 | 569.0-569.0 | 2.72 | yes | 2.023x | 1.627x | 0.804x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 2,153.7 | 2,360.4-2,360.4 | 4.56 | yes | `a100_sxm_80gb-x280-tensor` | 313.3 | 579.5-579.5 | 2.70 | yes | 6.873x | 4.073x | 0.593x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x218` | 554.6 | 273.7-273.7 | 10.13 | **no** | `a100_sxm_80gb-x215-tensor` | 231.3 | 360.5-360.5 | 3.21 | yes | 2.398x | 0.759x | 0.317x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 2,153.7 | 2,360.4-2,360.4 | 4.56 | yes | `a100_sxm_80gb-x280-tensor` | 239.9 | 372.4-372.4 | 3.22 | yes | 8.978x | 6.339x | 0.706x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x218` | 554.6 | 273.7-273.7 | 10.13 | **no** | `a100_sxm_80gb-x215-tensor` | 169.9 | 220.6-220.6 | 3.85 | yes | 3.265x | 1.241x | 0.380x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,969.0 | 2,052.2-2,052.2 | 4.80 | yes | `a100_sxm_80gb-x336-tensor` | 163.4 | 224.7-224.7 | 3.64 | yes | 12.051x | 9.134x | 0.758x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x218` | 554.6 | 273.7-273.7 | 10.13 | **no** | `a100_sxm_80gb-x215-tensor` | 116.1 | 129.6-129.6 | 4.48 | yes | 4.778x | 2.112x | 0.442x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,845.4 | 2,003.6-2,003.6 | 4.61 | yes | `a100_sxm_80gb-x672-tensor` | 124.0 | 135.8-135.8 | 4.56 | yes | 14.887x | 14.751x | 0.991x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 546.6 | 298.1-298.1 | 9.17 | **no** | `a100_sxm_80gb-x224-tensor` | 75.1 | 73.1-73.1 | 5.14 | **no** | 7.278x | 4.077x | 0.560x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,379.9 | 1,783.1-1,783.1 | 3.87 | yes | `a100_sxm_80gb-x672-tensor` | 80.9 | 74.6-74.6 | 5.43 | **no** | 17.051x | 23.918x | 1.403x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x248` | 514.7 | 266.3-266.3 | 9.66 | **no** | `a100_sxm_80gb-x245-tensor` | 46.2 | 39.3-39.3 | 5.88 | **no** | 11.132x | 6.772x | 0.608x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 875.7 | 1,025.6-1,025.6 | 4.27 | yes | `a100_sxm_80gb-x672-tensor` | 49.2 | 39.4-39.4 | 6.25 | **no** | 17.786x | 26.048x | 1.465x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x340` | 385.5 | 184.1-184.1 | 10.47 | **no** | `a100_sxm_80gb-x335-tensor` | 15.2 | 10.3-10.3 | 7.40 | **no** | 25.376x | 17.938x | 0.707x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 274.3 | 666.4-666.4 | 2.06 | yes | `a100_sxm_80gb-x672-tensor` | 15.5 | 10.3-10.3 | 7.55 | **no** | 17.658x | 64.813x | 3.670x |

**Does the ratio compress?** Of 32 class rows in this study, 22 move the ROM-versus-GPU ratio DOWN under speculation and 10 move it UP. The movement spans 0.288x to 3.670x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 18 of 32 ROM rows and 22 of 32 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-pipeline-x5-romfill` | 13,519.8 | not applicable | -- | -- | `b200_sxm-x3-tensor` | 2,222.7 | not applicable | -- | -- | 6.083x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | not applicable | -- | -- | `b200_sxm-x29-hybrid` | 3,342.0 | not applicable | -- | -- | 1.934x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x16-romfill` | 4,528.6 | not applicable | -- | -- | `b200_sxm-x8-tensor` | 3,254.9 | not applicable | -- | -- | 1.391x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x2-romfill` | 5,400.8 | not applicable | -- | -- | `b200_sxm-x58-hybrid` | 3,246.8 | not applicable | -- | -- | 1.663x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x57-romfill` | 4,191.8 | not applicable | -- | -- | `b200_sxm-x29-hybrid` | 3,342.0 | not applicable | -- | -- | 1.254x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x4-romfill` | 5,121.2 | not applicable | -- | -- | `b200_sxm-x116-hybrid` | 3,160.6 | not applicable | -- | -- | 1.620x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x57-romfill` | 4,191.8 | not applicable | -- | -- | `b200_sxm-x29-hybrid` | 3,056.7 | not applicable | -- | -- | 1.371x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 4,640.7 | not applicable | -- | -- | `b200_sxm-x231-hybrid` | 2,906.4 | not applicable | -- | -- | 1.597x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x113-romfill` | 3,928.4 | not applicable | -- | -- | `b200_sxm-x58-hybrid` | 2,971.1 | not applicable | -- | -- | 1.322x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 4,040.9 | not applicable | -- | -- | `b200_sxm-x347-hybrid` | 2,774.4 | not applicable | -- | -- | 1.457x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x227-romfill` | 3,503.0 | not applicable | -- | -- | `b200_sxm-x116-hybrid` | 2,871.4 | not applicable | -- | -- | 1.220x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,395.4 | not applicable | -- | -- | `b200_sxm-x347-hybrid` | 2,774.4 | not applicable | -- | -- | 1.224x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x340-romfill` | 3,145.5 | not applicable | -- | -- | `b200_sxm-x173-hybrid` | 2,596.5 | not applicable | -- | -- | 1.211x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 2,573.2 | not applicable | -- | -- | `b200_sxm-x347-hybrid` | 2,669.7 | not applicable | -- | -- | 0.964x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-pipeline-x340-romfill` | 2,486.0 | not applicable | -- | -- | `b200_sxm-x173-hybrid` | 1,569.6 | not applicable | -- | -- | 1.584x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 1,049.1 | not applicable | -- | -- | `b200_sxm-x347-hybrid` | 1,959.8 | not applicable | -- | -- | 0.535x | -- | -- |

### `n6_vs_a100-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-pipeline-x5-romfill` | 9,438.0 | not applicable | -- | -- | `a100_sxm_80gb-x5-tensor` | 995.3 | not applicable | -- | -- | 9.483x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 1,279.6 | not applicable | -- | -- | 5.052x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x15` | 2,119.2 | not applicable | -- | -- | `a100_sxm_80gb-x15-hybrid` | 1,255.6 | not applicable | -- | -- | 1.688x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x2` | 4,245.8 | not applicable | -- | -- | `a100_sxm_80gb-x112-hybrid` | 1,252.6 | not applicable | -- | -- | 3.390x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x57-romfill` | 2,036.0 | not applicable | -- | -- | `a100_sxm_80gb-x56-hybrid` | 1,279.0 | not applicable | -- | -- | 1.592x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x4-romfill` | 4,071.0 | not applicable | -- | -- | `a100_sxm_80gb-x224-hybrid` | 1,202.8 | not applicable | -- | -- | 3.385x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x57-romfill` | 2,036.0 | not applicable | -- | -- | `a100_sxm_80gb-x56-hybrid` | 1,256.4 | not applicable | -- | -- | 1.621x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 3,761.4 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 1,176.1 | not applicable | -- | -- | 3.198x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x113-romfill` | 1,963.8 | not applicable | -- | -- | `a100_sxm_80gb-x111-hybrid` | 1,224.8 | not applicable | -- | -- | 1.603x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,178.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 1,176.1 | not applicable | -- | -- | 2.702x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x227-romfill` | 1,843.0 | not applicable | -- | -- | `a100_sxm_80gb-x224-hybrid` | 1,181.4 | not applicable | -- | -- | 1.560x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 2,331.9 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 1,176.1 | not applicable | -- | -- | 1.983x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x340-romfill` | 1,665.8 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 1,101.1 | not applicable | -- | -- | 1.513x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,521.5 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 1,176.1 | not applicable | -- | -- | 1.294x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-q4p25-HBMKV-array-pipeline-x340-romfill` | 1,210.5 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 712.5 | not applicable | -- | -- | 1.699x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12` | 493.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 933.3 | not applicable | -- | -- | 0.528x | -- | -- |

## Where the drafter lives on a ROM machine

The locality rule -- `stored/peak` is a technology constant -- is the load-bearing assumption of the whole ROM verdict. A pass that reads only the drafter's region uses only that region's read ports and takes exactly as long as sweeping the entire array. Two placements are therefore priced side by side, and the second is an architectural proposal this study **has not costed in silicon area**.

The same rule is what makes a SEQUENTIAL draft step expensive here. A per-position operation that moves only a small table is nearly free on a global-bandwidth store and costs a full array sweep on this one, so a drafter with `gamma` sequential applications pays `gamma` sweeps for them. That term is charged in full below; on a bandwidth store the bytes it moves are not separately charged at all, because this repository's model configs carry no size for the table -- an omission whose size, on DeepSeek-V4-Pro-0813, is the externally published 132,382,720 B per draft token, 0.33% of the 39,666,603,980 B target pass.

| study | model | ctx | batch | class | design | tau* draft in ROM | tau* draft in KV store | KV placement feasible | why not |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 6.98 | 3.54 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 2.38 | 1.27 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 6.98 | 3.54 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 2.27 | 1.48 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 6.98 | 3.54 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 2.25 | 1.48 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 7.92 | 4.87 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2.16 | 1.45 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 8.53 | 5.05 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.07 | 1.50 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x87-romfill` | 7.98 | 4.37 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.02 | 1.69 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 7.76 | 4.30 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.96 | 1.86 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 7.81 | 5.63 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 4.22 | 1.36 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hybrid-x29` | 5.94 | 3.83 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 2.15 | 1.52 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 6.17 | 3.15 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 2.18 | 1.57 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 6.17 | 3.15 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 2.35 | 2.01 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 5.39 | 2.02 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 2.67 | 2.66 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 6.51 | 3.33 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 3.24 | 3.44 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 6.79 | 3.42 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 3.00 | 3.10 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x87-romfill` | 6.38 | 3.01 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 3.35 | 3.55 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 7.83 | 5.10 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.41 | 3.60 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hybrid-x28` | 7.09 | 8.01 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 2.15 | 2.78 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 6.00 | 2.98 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 2.17 | 1.56 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 6.00 | 2.98 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 2.32 | 1.98 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 5.30 | 1.94 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 2.62 | 2.61 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 6.34 | 3.17 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 3.18 | 3.38 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 7.93 | 5.17 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3.35 | 3.56 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 8.55 | 5.46 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 3.29 | 3.49 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 7.52 | 5.55 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.35 | 4.75 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 2.12 | 1.92 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 3.73 | 1.56 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 2.78 | 2.56 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3.76 | 1.81 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x161` | 11.20 | 5.95 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3.96 | 2.12 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x161` | 11.20 | 5.95 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4.75 | 3.31 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x161` | 11.20 | 5.95 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.80 | 5.06 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 9.39 | 4.05 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 5.38 | 4.33 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x193` | 8.68 | 3.29 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 5.65 | 4.67 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227` | 10.98 | 5.98 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.79 | 5.44 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 2.12 | 2.10 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 3.61 | 2.74 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 2.77 | 2.57 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3.64 | 1.69 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x160` | 10.68 | 5.48 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3.80 | 1.95 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x160` | 10.68 | 5.48 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4.42 | 2.99 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x160` | 10.68 | 5.48 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.63 | 4.83 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 8.69 | 3.35 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 5.02 | 3.97 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 11.36 | 6.24 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 6.44 | 6.03 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227` | 10.05 | 5.05 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.44 | 6.00 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 2.12 | 2.67 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 3.59 | 7.01 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 2.77 | 2.57 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3.62 | 1.67 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x157` | 10.88 | 5.69 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3.77 | 1.93 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x157` | 10.88 | 5.69 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4.38 | 2.94 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x157` | 10.88 | 5.69 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.59 | 4.78 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 7.92 | 2.73 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 4.96 | 3.91 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 9.85 | 4.96 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 6.33 | 5.92 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227` | 9.60 | 4.97 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.39 | 6.12 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x48` | 5.69 | 3.18 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 2.78 | 1.53 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 5.95 | 3.55 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 2.23 | 1.61 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 5.95 | 3.55 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 2.21 | 1.60 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 5.35 | 2.69 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2.14 | 1.58 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 6.72 | 4.36 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.98 | 1.60 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x111-romfill` | 6.24 | 3.40 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.72 | 1.69 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x170-romfill` | 6.79 | 4.09 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 5.60 | 1.67 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x340-romfill` | 6.65 | 5.09 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2.50 | 1.34 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x37` | 5.15 | 3.61 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 2.36 | 1.51 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 5.07 | 2.99 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 2.46 | 2.30 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 5.07 | 2.99 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 2.72 | 3.23 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 4.32 | 1.99 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 3.24 | 4.51 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 5.21 | 3.11 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3.33 | 4.47 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 5.50 | 3.33 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 3.25 | 4.34 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x57` | 7.04 | 4.97 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill` | 3.40 | 4.65 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 6.34 | 4.28 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.66 | 4.83 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x37` | 4.95 | 5.63 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 2.36 | 2.73 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 4.93 | 2.85 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 2.44 | 2.28 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 4.93 | 2.85 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 2.68 | 3.19 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 5.70 | 3.83 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 3.16 | 4.43 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 5.09 | 2.99 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3.26 | 4.40 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 5.38 | 3.21 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4.04 | 5.68 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 6.81 | 5.02 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 3.95 | 5.51 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 6.13 | 4.61 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.94 | 5.24 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x194` | 2.61 | 2.41 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 4.23 | 1.64 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x227` | 3.36 | 3.18 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.26 | 2.41 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x208` | 9.89 | 5.55 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.26 | 2.41 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x208` | 9.89 | 5.55 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.94 | 3.79 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x208` | 9.89 | 5.55 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 6.29 | 6.31 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 7.31 | 2.74 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 5.42 | 4.76 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 9.20 | 4.90 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.19 | 4.53 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x297` | 9.41 | 5.36 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 5.49 | 4.61 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x191` | 2.61 | 2.54 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 4.09 | 3.06 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x227` | 3.33 | 3.15 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.12 | 2.27 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 9.90 | 5.55 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.12 | 2.27 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 9.90 | 5.55 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.66 | 3.52 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 9.90 | 5.55 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5.74 | 5.76 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 6.92 | 2.35 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 6.72 | 8.12 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 8.43 | 4.14 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 6.14 | 6.87 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x297` | 8.71 | 4.67 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.54 | 9.11 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x191` | 2.60 | 2.92 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 4.07 | 8.16 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x227` | 3.32 | 3.15 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.10 | 2.25 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 9.81 | 5.42 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.10 | 2.25 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 9.81 | 5.42 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.62 | 3.47 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 9.81 | 5.42 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5.66 | 5.68 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 6.86 | 2.29 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 6.70 | 8.12 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 8.32 | 4.03 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 6.06 | 6.80 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x297` | 8.49 | 4.64 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.49 | 9.08 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hybrid-x30` | 6.37 | 3.34 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 2.16 | 1.14 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x32` | 6.26 | 3.23 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 2.27 | 1.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x32` | 6.26 | 3.23 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 2.46 | 2.13 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 5.94 | 2.58 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 2.56 | 2.20 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 7.61 | 4.43 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 2.50 | 2.17 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 7.86 | 4.49 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2.41 | 2.10 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x87-romfill` | 7.23 | 3.85 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.38 | 2.22 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227-romfill` | 8.09 | 5.21 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.75 | 2.88 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 2.13 | 1.89 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 4.43 | 2.06 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 2.81 | 2.59 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4.34 | 2.38 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x167` | 11.37 | 6.23 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4.73 | 2.89 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x167` | 11.37 | 6.23 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 4.47 | 2.28 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x167` | 11.37 | 6.23 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 4.63 | 2.47 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x193` | 8.65 | 3.08 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.42 | 2.40 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x193` | 11.14 | 5.76 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.95 | 2.82 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x308-romfill` | 11.05 | 5.69 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 3.58 | 2.06 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x39` | 5.11 | 2.89 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 2.39 | 1.17 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 5.69 | 3.72 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 2.52 | 2.37 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 5.69 | 3.72 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 2.74 | 2.39 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 4.75 | 2.42 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 2.67 | 2.34 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 6.05 | 3.95 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2.56 | 2.25 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 6.31 | 4.14 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.43 | 2.37 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x111-romfill` | 5.82 | 3.27 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.35 | 2.78 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 7.27 | 5.20 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 6.24 | 2.20 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x207` | 2.62 | 2.41 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 5.00 | 2.16 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x248` | 3.38 | 3.20 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 4.56 | 2.22 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x218` | 10.13 | 5.65 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 4.56 | 2.22 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x218` | 10.13 | 5.65 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.80 | 2.26 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x218` | 10.13 | 5.65 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4.61 | 2.18 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 9.17 | 4.60 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.87 | 2.57 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x248` | 9.66 | 5.20 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4.27 | 2.36 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x340` | 10.47 | 6.07 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2.06 | 1.81 | yes | -- |

## The capacity requirement, stated as a requirement

Every evaluated ROM design carries `weight_capacity_bytes == stored_weight_bytes` (the `romfill` variants reach 1.0039x), so no evaluated design has spare array for a drafter it does not already store. Re-solving the area split is `balanced_area_split`'s job and that file is not touched here, so what follows is a requirement -- this much extra array, or this much extra sweep on every pass -- and not a new design. **The speculative-optimal ROM design has not been computed, only bounded by the rungs that already exist.**

| study | model | design | drafter already in the checkpoint | extra stored bytes | extra array mm2 | as a fraction of the design | sweep inflation if area is held fixed |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hybrid-x37` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hybrid-x29` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hybrid-x28` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hybrid-x48` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hybrid-x37` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hybrid-x37` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-tensor-x194` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-tensor-x191` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-tensor-x191` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hybrid-x30` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hybrid-x39` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-tensor-x207` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |

## Which design the published rule chooses once a block is verified

A re-ranking of designs the study already evaluated, under the study's own selection rule (non-dominated on per-user tokens/s and tokens/s per 1,000 mm2, then a marginal-return walk from the smallest feasible machine). `tau` is a common factor on both axes, so the choice is independent of the acceptance rate. The rule's reproduction of the published autoregressive recommendation is reported first, because a re-ranking whose baseline does not reproduce is not evidence of anything.

| study | model | published recommendation | rule reproduces it | under speculation, draft in ROM | draft in KV store | moves |
| --- | --- | --- | --- | --- | --- | --- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-array-tensor-x37` | no |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hybrid-x29` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | yes |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hybrid-x28` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | yes |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | no |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-tensor-x1` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | no |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-tensor-x1` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | no |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-pipeline-x5-romfill` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hybrid-x30` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | yes |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | no |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-pipeline-x6` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-tensor-x1` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | no |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | no |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-array-pipeline-x2` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-array-pipeline-x3-romfill` | yes | `--` | `--` | the drafter does not apply to this model |

**The rule reproduces the published autoregressive recommendation on 20 of 20 model-and-study rows.** Of the 16 rows where it reproduces and the drafter applies, verifying a block moves the chosen rung on 9. Where it moves, it moves toward machines with compute headroom for a block, which is exactly what the arithmetic predicts: a verification pass raises arithmetic intensity by the block size, and a machine sized with just enough compute for one token per sweep has no room for it. **This is a re-ranking of rungs that already exist. The speculative-optimal design has not been computed: that would need the area split re-solved, which is `balanced_area_split`'s job and not this layer's.**

## The draft-traffic decomposition does not reproduce, and both readings are printed

_The draft weight traffic this study models comes from the repository's own checkpoint inventory. An externally published decomposition for DeepSeek-V4-Pro-0813 gives a different answer, and the two are printed side by side rather than reconciled by choosing one._

External source, graded `published`: DSpark draft weight-traffic decomposition for DeepSeek-V4-Pro-0813, arXiv:2607.05147 / github.com/deepseek-ai/DeepSpec (2026)

| model | draft tokens | repository config bytes | as a fraction of the target pass | externally published bytes | as a fraction | repo / published |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1 | 835,830,300 | 7.5% | -- | -- | --x |
| DeepSeek-V4-Flash-0731 | 2 | 1,070,838,300 | 9.5% | -- | -- | --x |
| DeepSeek-V4-Flash-0731 | 3 | 1,300,338,300 | 11.6% | -- | -- | --x |
| DeepSeek-V4-Flash-0731 | 4 | 1,524,459,394 | 13.6% | -- | -- | --x |
| DeepSeek-V4-Flash-0731 | 5 | 1,743,327,649 | 15.5% | -- | -- | --x |
| DeepSeek-V4-Flash-0731 | 6 | 1,957,066,180 | 17.4% | -- | -- | --x |
| DeepSeek-V4-Flash-0731 | 7 | 2,165,795,214 | 19.3% | -- | -- | --x |
| DeepSeek-V4-Flash-0731 | 8 | 2,369,632,162 | 21.1% | -- | -- | --x |
| DeepSeek-V4-Pro-0813 | 1 | 2,182,181,148 | 5.5% | 3,903,156,508 | 9.8% | 0.559x |
| DeepSeek-V4-Pro-0813 | 2 | 2,804,012,316 | 7.1% | 4,035,539,228 | 10.2% | 0.695x |
| DeepSeek-V4-Pro-0813 | 3 | 3,416,127,372 | 8.6% | 4,167,921,948 | 10.5% | 0.820x |
| DeepSeek-V4-Pro-0813 | 4 | 4,018,678,130 | 10.1% | 4,300,304,668 | 10.8% | 0.935x |
| DeepSeek-V4-Pro-0813 | 5 | 4,611,814,033 | 11.6% | 4,432,687,388 | 11.2% | 1.040x |
| DeepSeek-V4-Pro-0813 | 6 | 5,195,682,187 | 13.1% | 4,565,070,108 | 11.5% | 1.138x |
| DeepSeek-V4-Pro-0813 | 7 | 5,770,427,401 | 14.5% | 4,697,452,828 | 11.8% | 1.228x |
| DeepSeek-V4-Pro-0813 | 8 | 6,336,192,222 | 16.0% | 4,829,835,548 | 12.2% | 1.312x |

_CARRIED AS A CROSS-CHECK, NOT AS THE MODELLED INPUT. At the shipped block size 5 it gives 4,432,687,388 B, 11.17% of the 39,666,603,980 B target pass; at the served gamma = 7 it gives 4,697,452,828 B, 11.84%. The slope is exactly TWO rank-256 BF16 tables over a 129,280-token vocabulary, 66,191,360 B each (2 x 129280 x 256 x 2 = 132,382,720), which is the shape this repository's own committed tensor inventory records; one rank-512 table gives the identical byte total, so the slope alone cannot tell the two apart. The repository's own configs/models/deepseek-v4-pro-0813.json gives a different decomposition; the tool reports both and the divergence._

## Evidence ledger

| grade | entries |
| --- | ---: |
| `assumed` | 2 |
| `derived` | 1 |
| `published` | 8 |

**`assumed`**: `parameters.draft_compute_ops_ratio_rule`; `parameters.drafter_kv_traffic`

**`derived`**: `parameters.draft_weight_bytes_source`

**`published`**: `acceptance_length`; `external_draft_traffic_decomposition`; `parameters.block_size`; `parameters.draft_block_passes`; `parameters.draft_sequential_passes_per_draft_token`; `parameters.draft_stages`; `parameters.markov_bias_rank`; `parameters.served_speculative_tokens`

## What would change the answer

- The drafter's own KV traffic is not sourced for either drafter and is published as a band. DFlash injects target hidden features from five uniformly selected layers as Key/Value into every draft layer and gives no byte count; DSpark's three MTP stages carry their own cache and the paper gives no byte count. At 200K-1M context this term could dominate the draft pass.
- The ROM draft sweep is the largest single modelled penalty and it rests entirely on the locality rule in src/opentallas/roofline.py. If a designer replicates the drafter across the array, gives it dedicated wide ports, or holds it off-array, the draft weight term collapses and the ROM verdict can change sign. The alternative placement is priced beside it and has not been costed in silicon area.
- The compute headroom that decides whether a verification block flips a design from memory-bound to compute-bound is downstream of the compute efficiency derate, which is graded `assumed` at 0.55 and has never been measured. The block size at which the flip happens is reported on every point so the exposure is visible.
- The DeepSeek-V4-Pro-0813 draft-traffic decomposition published externally (3,770,773,788 B constant plus 132,382,720 B per draft token) does not reproduce from this repository's own configs/models/deepseek-v4-pro-0813.json inventory. Both are reported; neither is silently preferred.
- No speculative decoder has been executed anywhere in this repository. Every rate here is modelled, and the acceptance lengths that turn a break-even into a speedup were measured by other people on other hardware.

