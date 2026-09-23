# Speculative decoding on the area-constrained roofline: released_dspark

> DeepSeek-V4's own speculative module, as shipped. Every figure below is derived from the roofline artifacts
> this repository has already published, by re-assembling each point's own five
> critical-path terms for a speculative cycle. Nothing here re-runs the machine
> model, and nothing here invents an acceptance rate.

## What this layer says

1. **Every term the speculative arithmetic needs is already in the published artifact, exactly.** 98,262 feasible points across 22 studies were rebuilt from their own five critical-path terms and every one reproduced its published step time to 1e-9 relative. Nothing here re-ran the machine model, and the layer is additive by construction rather than by promise.
2. **The headline is a break-even, not a speedup.** `tau* = T_cycle / step_time_s`, and `tau <= gamma+1` always. Of 137,883 (point, draft-placement) pairs where this profile's drafter applies, 55,764 (40.4%) cannot be sped up by speculation at ANY acceptance rate, at any block size on the ladder, even charging the drafter no KV traffic at all.
3. **The ROM-versus-GPU ratio under speculation carries no acceptance rate.** It is `T_cycle(GPU) / T_cycle(ROM)`: `tau` is a property of the model and its drafter, not of the machine, so it is identical on both sides and cancels. Every movement this report shows is a machine effect and nothing else, which is why it can be published without inventing an acceptance rate.
4. **The ratio moves, and it mostly compresses.** Across 429 model-context-batch-class rows, 407 move the ROM-versus-GPU per-user ratio DOWN under speculation and 22 move it UP, spanning 0.006x to 3.598x. The ROM advantage compresses on most operating points.
5. **At batch 1 the two extremes are opposite in sign, and they are the result.** DeepSeek-V4.1-Flash on `array` silicon goes from 3.87x to 0.02x -- a 0.006x movement -- while DeepSeek-V4-Pro-0813 on `array` silicon goes from 6.40x to 4.99x, a 0.780x movement. A layer that multiplied both sides by `tau` would have reported neither.
6. **A moving ratio is not a win for either side, and the report says so on every table.** At the most favourable sourced acceptance (5.00) speculation is worth having on 61 of 431 ROM class rows and 382 of 431 GPU rows; everywhere else the design runs SLOWER with a drafter than without one. Where both sides lose, a rising ratio means only that the comparator lost more.
7. **Compute is never a gain and always a loss.** A verification pass over `n` positions charges `n` times the arithmetic exactly, so per accepted token compute costs `(n/tau) >= 1` times what it did. A compute-bound design cannot be sped up by speculation at any acceptance rate; it can only be slowed. That is where the recommended ROM designs live, because the sizing rule gives them just enough compute for one token per sweep.
8. **On a mask-ROM machine the draft pass costs a full array sweep, and that is the load-bearing assumption of the whole ROM verdict.** `stored/peak` is a technology constant in `src/opentallas/roofline.py`, so a pass reading only the drafter's region takes as long as sweeping the entire array. The alternative -- holding the drafter in the KV store -- is priced beside it on every ROM row and has NOT been costed in silicon area.
9. **The mask-ROM designs are already storing this drafter, and already sweeping it on every ordinary token.** `_rom_stored_bytes` stores the whole released checkpoint, and the checkpoint ships the draft module for DeepSeek-V4-Flash-0731, DeepSeek-V4-Pro-0813, DeepSeek-V4.1-Flash, DeepSeek-V4.1-Flash-engram-hbm, DeepSeek-V4.1-Flash-engram-host. So the storage inflation is 1.000x, the extra array requirement is zero, and the autoregressive ROM baseline in the published study is ALREADY paying for a drafter it does not use. The HBM comparators are not: their engaged bytes exclude the draft categories entirely.
10. **This profile does not apply to Qwen3-8B.** Its released checkpoint carries no draft weights at all, and transplanting a drafter that was never trained for it would be inventing a model. It is reported as not applicable rather than modelled.
11. **This drafter's SEQUENTIAL step is what it costs on a mask-ROM machine, and it costs more than the drafter's own size.** The bias is applied once per draft token with no transformer re-run, so on a bandwidth machine it moves a table and is nearly free -- but under the locality rule every pass that touches the array takes the full-array sweep time whatever it reads, so `gamma` sequential applications cost `gamma` full sweeps. The draft pass is 11% to 99% of the whole speculative cycle on the ROM designs this report quotes (median 83%), almost all of it those sweeps. A block-diffusion drafter has no such term at all, which is the single largest structural difference between the two profiles on this silicon.
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
| `n5_vs_b200-deepseek-v41-flash` | 5,220 | 0 |
| `n6_vs_a100-deepseek-v41-flash` | 4,110 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | 5,761 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | 4,443 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | 5,112 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | 4,196 | 0 |
| `n5_vs_b200-flash-1m` | 2,695 | 0 |
| `n5_vs_b200-flash-32k` | 4,246 | 0 |
| `n5_vs_b200-flash-8k` | 4,372 | 0 |
| `n5_vs_b200-pro-200k` | 4,339 | 0 |
| `n5_vs_b200-pro-32k` | 4,912 | 0 |
| `n5_vs_b200-pro-8k` | 4,838 | 0 |
| `n6_vs_a100-flash-1m` | 1,875 | 0 |
| `n6_vs_a100-flash-32k` | 4,288 | 0 |
| `n6_vs_a100-flash-8k` | 4,162 | 0 |
| `n6_vs_a100-pro-200k` | 3,397 | 0 |
| `n6_vs_a100-pro-32k` | 3,531 | 0 |
| `n6_vs_a100-pro-8k` | 3,492 | 0 |
| `n5_vs_b200` | 9,413 | 0 |
| `n6_vs_a100` | 7,820 | 0 |
| `n5_vs_b200-quantised_variant` | 3,150 | 0 |
| `n6_vs_a100-quantised_variant` | 2,890 | 0 |

The identity checked is: `(max(memory, compute)/stage_balance + link_latency + layer_fixed_latency) x thermal_scale == step_time_s, with memory assembled by designs[].shared_memory_path and the compute-in-ROM fusion rule, and the weight and link terms independently rebuilt from the model profile and the technology file`.

## Headline: where speculation cannot pay at any acceptance rate

Counted at the LOW end of the unsourced drafter-KV band, which is the most favourable assumption available to speculation. `tau*` is the break-even acceptance at this profile's served block size.

| study | model | family | draft placement | binds on (autoregressive) | points | cannot pay at any gamma | tau* min | tau* median | tau* max |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,110 | 134 | 1.33 | 3.24 | 8.58 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 340 | 0 | 1.17 | 3.39 | 4.83 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 730 | 0 | 1.36 | 2.29 | 5.05 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 1,030 | 562 | 5.29 | 8.19 | 25.88 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 78 | 72 | 2.25 | 19.90 | 26.22 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 1,232 | 143 | 1.11 | 3.01 | 9.03 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 700 | 159 | 1.72 | 5.96 | 16.59 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 1,030 | 969 | 6.29 | 66.15 | 290.53 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 78 | 72 | 4.44 | 62.65 | 71.22 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 1,232 | 447 | 1.37 | 6.15 | 41.86 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 700 | 605 | 4.85 | 15.74 | 307.62 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 1 | 1 | 8.23 | 8.23 | 8.23 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 360 | 110 | 1.77 | 6.46 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 959 | 0 | 1.27 | 2.47 | 6.69 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 993 | 709 | 5.41 | 8.66 | 29.34 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 78 | 49 | 1.30 | 19.47 | 23.25 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 1,174 | 123 | 1.13 | 3.00 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 545 | 185 | 2.07 | 7.62 | 22.92 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 993 | 922 | 6.08 | 61.61 | 294.07 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 78 | 52 | 2.48 | 53.00 | 142.81 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 1,174 | 429 | 1.48 | 6.43 | 25.49 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 545 | 493 | 5.06 | 15.65 | 308.37 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,299 | 155 | 1.33 | 3.12 | 8.58 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 380 | 0 | 1.17 | 3.39 | 4.83 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 791 | 0 | 1.36 | 2.30 | 5.90 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 1,026 | 551 | 4.94 | 8.18 | 21.66 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 23 | 1 | 1.47 | 5.57 | 12.66 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 1,359 | 154 | 1.07 | 2.63 | 8.58 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 883 | 165 | 1.05 | 5.56 | 17.87 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 1,026 | 968 | 6.07 | 43.68 | 185.80 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 23 | 4 | 2.81 | 7.09 | 28.84 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 1,359 | 479 | 1.17 | 6.01 | 41.13 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 883 | 787 | 5.06 | 16.67 | 188.95 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 3 | 3 | 8.21 | 8.21 | 8.23 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 427 | 130 | 1.77 | 6.53 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 1,130 | 0 | 1.27 | 2.50 | 6.69 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 855 | 592 | 5.52 | 8.62 | 11.64 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 152 | 74 | 1.07 | 10.44 | 30.99 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 1,249 | 132 | 1.07 | 2.80 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 627 | 159 | 1.05 | 6.91 | 26.22 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 855 | 823 | 6.99 | 58.15 | 187.06 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 152 | 77 | 1.76 | 11.58 | 144.41 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 1,249 | 430 | 1.19 | 6.33 | 24.22 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 627 | 575 | 5.06 | 19.85 | 189.65 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 864 | 106 | 1.33 | 3.75 | 8.58 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `thermal` | 300 | 0 | 1.17 | 3.39 | 4.83 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 716 | 0 | 1.36 | 2.40 | 5.91 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 1,028 | 600 | 4.94 | 8.21 | 25.22 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 85 | 67 | 1.38 | 19.30 | 25.88 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 1,322 | 154 | 1.10 | 3.02 | 8.98 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 797 | 175 | 1.90 | 5.56 | 17.87 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 1,028 | 964 | 6.07 | 38.25 | 177.59 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 85 | 69 | 2.69 | 50.23 | 70.27 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 1,322 | 485 | 1.26 | 6.29 | 37.78 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 797 | 712 | 4.85 | 16.75 | 187.23 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `compute` | 5 | 5 | 8.21 | 8.21 | 8.25 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 362 | 111 | 1.77 | 6.33 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 953 | 0 | 1.27 | 2.52 | 6.69 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 823 | 601 | 5.52 | 8.81 | 25.98 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 212 | 134 | 1.07 | 19.20 | 30.99 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 1,248 | 132 | 1.13 | 3.06 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 593 | 178 | 2.00 | 6.94 | 26.22 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 823 | 791 | 6.99 | 55.83 | 180.26 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 212 | 137 | 1.76 | 41.33 | 144.45 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 1,248 | 427 | 1.32 | 6.35 | 24.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 593 | 546 | 4.85 | 19.85 | 187.26 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `kv_read` | 100 | 0 | 1.47 | 2.49 | 4.12 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 833 | 26 | 1.17 | 2.08 | 8.49 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 253 | 0 | 1.29 | 2.94 | 6.25 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 393 | 0 | 1.28 | 2.09 | 3.40 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 188 | 95 | 5.59 | 8.19 | 9.33 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 58 | 0 | 1.07 | 2.93 | 178.69 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 492 | 33 | 1.09 | 2.00 | 108.75 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `thermal` | 35 | 0 | 1.25 | 3.87 | 4.94 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 343 | 47 | 1.80 | 3.50 | 8.83 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 188 | 182 | 7.79 | 31.61 | 120.46 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 58 | 8 | 1.08 | 4.35 | 355.68 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 492 | 101 | 1.09 | 4.15 | 212.97 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `thermal` | 35 | 21 | 1.37 | 13.49 | 65.51 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 343 | 334 | 7.36 | 20.50 | 121.08 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 804 | 94 | 1.29 | 2.59 | 8.53 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 250 | 0 | 1.23 | 3.17 | 4.34 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 476 | 0 | 1.29 | 2.31 | 5.83 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 904 | 692 | 5.43 | 8.58 | 39.11 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 86 | 63 | 1.14 | 32.66 | 39.22 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,127 | 111 | 1.10 | 2.76 | 129.60 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `thermal` | 2 | 0 | 5.88 | 6.20 | 6.20 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 597 | 146 | 1.63 | 5.50 | 221.88 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 904 | 841 | 5.40 | 31.01 | 110.92 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 86 | 63 | 2.09 | 45.75 | 104.23 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,127 | 318 | 1.17 | 5.85 | 254.72 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `thermal` | 2 | 2 | 11.15 | 11.79 | 11.79 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 597 | 550 | 5.20 | 22.49 | 442.63 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 4 | 4 | 8.49 | 8.50 | 8.50 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 803 | 124 | 1.29 | 2.60 | 8.53 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 264 | 0 | 1.23 | 3.17 | 4.63 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 509 | 0 | 1.29 | 2.34 | 6.55 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 968 | 736 | 5.32 | 8.61 | 81.70 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 72 | 68 | 2.56 | 79.09 | 84.99 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,153 | 136 | 1.10 | 2.91 | 129.60 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 599 | 160 | 1.63 | 5.45 | 252.87 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 968 | 900 | 5.29 | 32.72 | 113.67 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 72 | 66 | 3.79 | 53.39 | 169.76 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,153 | 322 | 1.17 | 5.97 | 254.72 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 599 | 549 | 5.27 | 22.22 | 505.63 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 788 | 93 | 1.46 | 4.63 | 8.37 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 284 | 0 | 1.55 | 3.27 | 4.76 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 825 | 0 | 1.37 | 2.46 | 4.30 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 796 | 723 | 5.25 | 8.94 | 20.42 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 71 | 41 | 1.22 | 14.64 | 19.31 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 937 | 124 | 1.12 | 3.49 | 8.38 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `thermal` | 5 | 0 | 4.32 | 4.33 | 4.43 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 633 | 248 | 1.90 | 7.37 | 13.07 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 796 | 778 | 6.15 | 39.04 | 174.24 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 71 | 46 | 1.70 | 59.81 | 126.21 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 937 | 322 | 1.21 | 6.18 | 29.24 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `thermal` | 5 | 0 | 8.45 | 8.48 | 8.67 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 633 | 543 | 6.29 | 14.27 | 181.14 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 889 | 121 | 1.46 | 4.96 | 8.38 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 321 | 0 | 1.22 | 3.29 | 4.83 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 930 | 0 | 1.38 | 2.50 | 6.21 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 913 | 810 | 5.18 | 9.17 | 62.59 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 45 | 32 | 2.47 | 55.63 | 61.80 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 1,100 | 149 | 1.12 | 3.49 | 16.95 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 714 | 261 | 1.91 | 7.51 | 26.56 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 913 | 866 | 5.95 | 43.21 | 174.74 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 45 | 32 | 4.60 | 82.93 | 92.59 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 1,100 | 327 | 1.40 | 5.97 | 29.04 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 714 | 620 | 4.77 | 14.61 | 179.58 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 2 | 2 | 8.35 | 8.35 | 8.35 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 851 | 116 | 1.46 | 4.98 | 8.38 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 310 | 0 | 1.25 | 3.29 | 4.83 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 897 | 0 | 1.38 | 2.50 | 4.36 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 893 | 789 | 5.15 | 9.18 | 116.48 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 44 | 40 | 4.61 | 107.85 | 116.04 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 1,098 | 155 | 1.11 | 3.64 | 46.72 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 743 | 291 | 1.91 | 7.52 | 52.35 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 893 | 846 | 5.90 | 42.41 | 175.23 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 44 | 43 | 7.87 | 45.76 | 52.84 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 1,098 | 325 | 1.39 | 5.97 | 29.01 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 743 | 643 | 4.77 | 14.27 | 179.35 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `kv_read` | 22 | 0 | 4.09 | 4.78 | 6.69 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 256 | 30 | 1.64 | 4.85 | 8.53 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 745 | 0 | 1.12 | 2.72 | 11.77 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 78 | 41 | 7.36 | 8.09 | 8.98 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 179 | 2 | 1.08 | 3.89 | 112.78 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 363 | 17 | 1.09 | 1.85 | 11.66 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 232 | 47 | 2.03 | 4.51 | 8.91 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 78 | 78 | 16.41 | 32.46 | 110.32 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 179 | 86 | 1.05 | 8.50 | 224.48 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 363 | 52 | 1.09 | 3.25 | 47.92 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 232 | 223 | 7.94 | 18.11 | 122.94 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 21 | 17 | 7.54 | 8.41 | 8.51 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 381 | 117 | 1.65 | 5.96 | 8.54 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 918 | 0 | 1.19 | 2.74 | 7.03 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 843 | 785 | 5.62 | 10.03 | 39.83 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 208 | 124 | 1.09 | 30.96 | 120.94 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,248 | 128 | 1.14 | 3.10 | 71.25 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 669 | 243 | 2.13 | 7.26 | 33.80 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 843 | 787 | 6.88 | 36.33 | 117.14 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 208 | 136 | 1.56 | 37.90 | 241.21 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,248 | 249 | 1.20 | 5.83 | 137.77 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 669 | 619 | 5.20 | 19.14 | 118.83 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 19 | 19 | 8.39 | 8.44 | 8.56 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 348 | 106 | 1.65 | 5.96 | 8.54 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 863 | 0 | 1.19 | 2.75 | 7.63 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 899 | 821 | 5.52 | 10.13 | 82.89 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 101 | 79 | 1.64 | 73.89 | 146.60 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,246 | 146 | 1.14 | 3.48 | 126.55 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 686 | 268 | 2.13 | 7.57 | 44.59 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 899 | 823 | 5.50 | 37.65 | 115.56 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 101 | 78 | 2.56 | 48.59 | 293.04 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,246 | 252 | 1.20 | 5.80 | 248.50 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 686 | 636 | 5.27 | 19.48 | 118.83 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 23 | 12 | 7.00 | 8.10 | 8.22 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 305 | 80 | 1.99 | 6.16 | 8.38 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 891 | 0 | 1.21 | 3.05 | 6.51 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 754 | 684 | 5.23 | 9.86 | 20.44 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 71 | 38 | 1.30 | 14.39 | 20.54 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 890 | 114 | 1.17 | 3.68 | 8.39 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 463 | 193 | 2.04 | 7.80 | 14.84 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 754 | 734 | 6.40 | 41.70 | 157.60 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 71 | 38 | 1.41 | 46.36 | 129.10 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 890 | 316 | 1.20 | 6.43 | 19.81 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 463 | 412 | 6.03 | 14.50 | 22.98 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 22 | 20 | 7.78 | 8.13 | 8.35 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 310 | 85 | 2.00 | 6.23 | 8.38 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 907 | 0 | 1.23 | 3.06 | 7.61 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 880 | 784 | 5.22 | 10.40 | 62.82 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 40 | 26 | 1.54 | 56.21 | 63.30 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 990 | 121 | 1.18 | 3.70 | 11.77 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 382 | 182 | 2.04 | 8.02 | 37.43 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 880 | 835 | 5.69 | 50.59 | 176.24 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 40 | 27 | 2.55 | 81.75 | 94.27 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 990 | 331 | 1.53 | 6.28 | 19.96 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 382 | 351 | 4.77 | 15.30 | 182.18 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 24 | 23 | 7.82 | 8.17 | 8.37 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 294 | 80 | 2.00 | 6.22 | 8.38 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 882 | 0 | 1.23 | 3.05 | 7.79 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 833 | 739 | 5.16 | 10.35 | 116.52 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 53 | 38 | 2.68 | 107.59 | 116.76 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 984 | 136 | 1.18 | 3.88 | 33.36 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 422 | 206 | 2.04 | 8.19 | 49.56 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 833 | 790 | 5.86 | 40.12 | 175.88 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 53 | 38 | 4.68 | 46.00 | 53.01 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 984 | 319 | 1.52 | 6.16 | 19.94 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 422 | 385 | 4.77 | 15.30 | 181.91 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `kv_read` | 13 | 0 | 2.45 | 3.40 | 4.44 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 806 | 48 | 1.29 | 2.33 | 8.51 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 227 | 0 | 1.23 | 3.12 | 4.21 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 387 | 0 | 1.29 | 2.25 | 3.32 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 629 | 438 | 6.30 | 8.55 | 14.53 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 95 | 38 | 1.07 | 8.58 | 186.49 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 964 | 106 | 1.10 | 2.28 | 109.89 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `thermal` | 22 | 4 | 1.66 | 7.65 | 9.80 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 566 | 91 | 1.63 | 4.71 | 14.82 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 629 | 616 | 7.08 | 58.98 | 115.01 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 95 | 52 | 1.26 | 15.10 | 371.42 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 964 | 308 | 1.14 | 5.82 | 215.41 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `thermal` | 22 | 14 | 3.13 | 14.39 | 38.57 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 566 | 531 | 5.43 | 22.97 | 118.83 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `kv_read` | 7 | 0 | 3.18 | 3.32 | 3.70 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 633 | 37 | 1.27 | 3.56 | 8.36 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 250 | 0 | 1.48 | 3.19 | 6.41 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 722 | 0 | 1.20 | 2.38 | 5.21 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 144 | 137 | 5.17 | 8.87 | 10.52 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 53 | 10 | 1.22 | 5.10 | 9.13 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 357 | 22 | 1.07 | 2.04 | 8.38 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `thermal` | 4 | 0 | 1.74 | 3.35 | 3.39 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 276 | 86 | 1.72 | 5.01 | 8.46 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 144 | 144 | 8.55 | 68.89 | 150.95 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 53 | 30 | 1.26 | 11.02 | 148.33 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 357 | 79 | 1.09 | 3.78 | 43.75 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `thermal` | 4 | 0 | 3.45 | 7.51 | 7.55 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 276 | 259 | 6.16 | 13.83 | 180.06 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 48 | 14 | 5.83 | 7.19 | 8.40 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 336 | 76 | 1.65 | 5.17 | 8.54 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 950 | 0 | 1.19 | 2.76 | 5.91 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 541 | 504 | 6.41 | 9.99 | 14.57 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 146 | 29 | 1.09 | 7.96 | 118.46 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 924 | 93 | 1.14 | 2.44 | 11.91 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 497 | 117 | 2.09 | 6.35 | 11.94 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 541 | 520 | 7.29 | 57.10 | 116.70 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 146 | 82 | 1.15 | 10.09 | 235.86 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 924 | 211 | 1.13 | 5.89 | 21.37 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 497 | 475 | 5.98 | 59.05 | 119.47 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 4 | 0 | 5.32 | 5.39 | 6.47 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 242 | 45 | 1.98 | 5.88 | 8.38 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 721 | 10 | 1.08 | 3.00 | 12.69 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 71 | 69 | 5.36 | 8.62 | 10.71 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 64 | 1 | 1.31 | 3.86 | 10.44 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 208 | 0 | 1.08 | 1.95 | 4.39 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 92 | 25 | 2.04 | 7.52 | 8.36 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 71 | 71 | 10.17 | 57.16 | 118.19 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 64 | 34 | 1.16 | 9.49 | 137.62 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 208 | 35 | 1.08 | 2.67 | 49.87 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 92 | 90 | 8.15 | 15.20 | 23.00 |

## Per model, per context, per batch and per design class

Each row is that class's **fastest** feasible design at that batch, read against the iso-area GPU comparator the published study already chose for it. The `densest` pick of every class is in `analytical.json` beside it.

**The ROM-versus-GPU ratio under speculation is `T_cycle(GPU) / T_cycle(ROM)` and carries no `tau` at all.** The acceptance length is a property of the model and its drafter, not of the machine, so it is the same on both sides and cancels out of the ratio. Every movement in the last column is therefore a machine effect and nothing else.

### `n5_vs_b200-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 15,555.9 | 337.7-337.7 | 230.32 | **no** | `b200_sxm-x96-nvl72-hybrid` | 4,014.6 | 13,864.4-13,864.4 | 1.45 | yes | 3.875x | 0.024x | 0.006x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,969.3 | 4,457.0-4,457.0 | 6.70 | **no** | `b200_sxm-x87-nvl72-hybrid` | 3,945.6 | 13,394.4-13,394.4 | 1.47 | yes | 1.513x | 0.333x | 0.220x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 15,555.9 | 337.7-337.7 | 230.32 | **no** | `b200_sxm-x96-nvl72-hybrid` | 4,014.6 | 13,864.4-13,864.4 | 1.45 | yes | 3.875x | 0.024x | 0.006x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,969.3 | 4,457.0-4,457.0 | 6.70 | **no** | `b200_sxm-x87-nvl72-hybrid` | 3,945.6 | 13,394.4-13,394.4 | 1.47 | yes | 1.513x | 0.333x | 0.220x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 15,555.9 | 337.7-337.7 | 230.32 | **no** | `b200_sxm-x96-nvl72-hybrid` | 3,752.8 | 11,488.2-11,488.2 | 1.63 | yes | 4.145x | 0.029x | 0.007x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 5,942.8 | 3,512.9-3,512.9 | 8.46 | **no** | `b200_sxm-x116-nvl72-hybrid` | 3,895.4 | 12,300.8-12,300.8 | 1.58 | yes | 1.526x | 0.286x | 0.187x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 15,555.9 | 337.7-337.7 | 230.32 | **no** | `b200_sxm-x96-nvl72-hybrid` | 3,327.1 | 8,838.6-8,838.6 | 1.88 | yes | 4.675x | 0.038x | 0.008x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,925.3 | 5,114.1-5,114.1 | 5.79 | **no** | `b200_sxm-x231-nvl72-hybrid` | 3,819.8 | 11,824.6-11,824.6 | 1.62 | yes | 1.551x | 0.432x | 0.279x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 15,555.9 | 337.7-337.7 | 230.32 | **no** | `b200_sxm-x96-nvl72-hybrid` | 2,730.9 | 6,178.5-6,178.5 | 2.21 | yes | 5.696x | 0.055x | 0.010x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,864.5 | 5,056.0-5,056.0 | 5.80 | **no** | `b200_sxm-x347-nvl72-hybrid` | 3,671.5 | 10,420.9-10,420.9 | 1.76 | yes | 1.597x | 0.485x | 0.304x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 15,555.9 | 337.7-337.7 | 230.32 | **no** | `b200_sxm-x96-nvl72-hybrid` | 2,049.8 | 4,180.7-4,180.7 | 2.45 | yes | 7.589x | 0.081x | 0.011x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,685.6 | 4,845.7-4,845.7 | 5.87 | **no** | `b200_sxm-x347-nvl72-hybrid` | 3,184.1 | 7,805.5-7,805.5 | 2.04 | yes | 1.786x | 0.621x | 0.348x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 13,436.0 | 279.9-279.9 | 240.00 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,589.9 | 3,053.4-3,053.4 | 2.60 | yes | 8.451x | 0.092x | 0.011x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,358.7 | 4,473.4-4,473.4 | 5.99 | **no** | `b200_sxm-x347-nvl72-hybrid` | 2,544.0 | 5,262.6-5,262.6 | 2.42 | yes | 2.106x | 0.850x | 0.404x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 6,357.0 | 185.8-185.8 | 171.04 | **no** | `b200_sxm-x173-nvl72-hybrid` | 926.6 | 1,522.1-1,522.1 | 3.04 | yes | 6.860x | 0.122x | 0.018x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 4,186.1 | 1,582.8-1,582.8 | 13.22 | **no** | `b200_sxm-x231-nvl72-hybrid` | 1,060.1 | 1,794.9-1,794.9 | 2.95 | yes | 3.949x | 0.882x | 0.223x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 2,380.6 | 165.5-165.5 | 71.93 | **no** | `b200_sxm-x179-expert` | 483.8 | 691.1-691.1 | 3.50 | yes | 4.921x | 0.239x | 0.049x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,803.6 | 107.9-107.9 | 129.97 | **no** | `b200_sxm-x347-expert` | 664.0 | 1,194.5-1,194.5 | 2.78 | yes | 4.222x | 0.090x | 0.021x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 625.4 | 41.5-41.5 | 75.39 | **no** | `b200_sxm-x179-expert` | 235.1 | 186.2-186.2 | 6.31 | **no** | 2.660x | 0.223x | 0.084x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,209.7 | 546.5-546.5 | 11.07 | **no** | `b200_sxm-x347-expert` | 379.9 | 356.5-356.5 | 5.33 | **no** | 3.185x | 1.533x | 0.481x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.006x to 0.481x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 11,839.5 | 240.5-240.5 | 246.12 | **no** | `a100_sxm_80gb-x260-tensor` | 1,152.3 | 2,843.4-2,843.4 | 2.03 | yes | 10.275x | 0.085x | 0.008x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,910.8 | 3,470.4-3,470.4 | 8.52 | **no** | `a100_sxm_80gb-x224-tensor` | 1,146.5 | 2,831.2-2,831.2 | 2.02 | yes | 5.156x | 1.226x | 0.238x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 11,839.5 | 240.5-240.5 | 246.12 | **no** | `a100_sxm_80gb-x260-tensor` | 1,019.5 | 1,867.3-1,867.3 | 2.73 | yes | 11.612x | 0.129x | 0.011x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,910.8 | 3,470.4-3,470.4 | 8.52 | **no** | `a100_sxm_80gb-x224-tensor` | 1,013.8 | 1,860.6-1,860.6 | 2.72 | yes | 5.830x | 1.865x | 0.320x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 11,839.5 | 240.5-240.5 | 246.12 | **no** | `a100_sxm_80gb-x260-tensor` | 829.0 | 1,113.1-1,113.1 | 3.72 | yes | 14.282x | 0.216x | 0.015x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,910.8 | 3,470.4-3,470.4 | 8.52 | **no** | `a100_sxm_80gb-x224-tensor` | 823.7 | 1,111.1-1,111.1 | 3.71 | yes | 7.176x | 3.123x | 0.435x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 11,839.5 | 240.5-240.5 | 246.12 | **no** | `a100_sxm_80gb-x260-hybrid` | 665.9 | 1,405.1-1,405.1 | 2.37 | yes | 17.781x | 0.171x | 0.010x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,871.4 | 3,884.3-3,884.3 | 7.56 | **no** | `a100_sxm_80gb-x448-hybrid` | 665.0 | 1,292.6-1,292.6 | 2.57 | yes | 8.829x | 3.005x | 0.340x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 11,839.5 | 240.5-240.5 | 246.12 | **no** | `a100_sxm_80gb-x260-hybrid` | 665.9 | 1,405.1-1,405.1 | 2.37 | yes | 17.781x | 0.171x | 0.010x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,794.4 | 3,838.5-3,838.5 | 7.55 | **no** | `a100_sxm_80gb-x672-hybrid` | 665.0 | 1,183.8-1,183.8 | 2.81 | yes | 8.713x | 3.242x | 0.372x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 11,839.5 | 240.5-240.5 | 246.12 | **no** | `a100_sxm_80gb-x260-hybrid` | 665.9 | 1,405.1-1,405.1 | 2.37 | yes | 17.781x | 0.171x | 0.010x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,555.2 | 3,671.0-3,671.0 | 7.57 | **no** | `a100_sxm_80gb-x672-hybrid` | 665.0 | 1,183.8-1,183.8 | 2.81 | yes | 8.353x | 3.101x | 0.371x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 11,839.5 | 240.5-240.5 | 246.12 | **no** | `a100_sxm_80gb-x260-hybrid` | 541.7 | 1,020.8-1,020.8 | 2.65 | yes | 21.858x | 0.236x | 0.011x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 5,157.9 | 1,254.8-1,254.8 | 20.55 | **no** | `a100_sxm_80gb-x672-hybrid` | 665.0 | 1,183.8-1,183.8 | 2.81 | yes | 7.756x | 1.060x | 0.137x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 5,207.3 | 180.0-180.0 | 144.64 | **no** | `a100_sxm_80gb-x337-hybrid` | 302.0 | 550.9-550.9 | 2.74 | yes | 17.241x | 0.327x | 0.019x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,852.0 | 1,142.2-1,142.2 | 16.86 | **no** | `a100_sxm_80gb-x672-hybrid` | 445.7 | 718.7-718.7 | 3.10 | yes | 8.642x | 1.589x | 0.184x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,409.5 | 45.3-45.3 | 155.58 | **no** | `a100_sxm_80gb-x337-expert` | 222.3 | 359.0-359.0 | 3.10 | yes | 6.340x | 0.126x | 0.020x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,045.7 | 77.8-77.8 | 131.50 | **no** | `a100_sxm_80gb-x672-expert` | 285.0 | 685.9-685.9 | 2.08 | yes | 7.179x | 0.113x | 0.016x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 356.6 | 39.3-39.3 | 45.34 | **no** | `a100_sxm_80gb-x337-expert` | 139.7 | 92.8-92.8 | 7.52 | **no** | 2.554x | 0.424x | 0.166x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 596.5 | 408.8-408.8 | 7.30 | **no** | `a100_sxm_80gb-x672-expert` | 206.5 | 183.1-183.1 | 5.64 | **no** | 2.889x | 2.233x | 0.773x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.008x to 0.773x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 649.0-649.0 | 137.78 | **no** | `b200_sxm-x49-nvl72-tensor` | 4,065.4 | 13,962.0-13,962.0 | 1.46 | yes | 4.399x | 0.046x | 0.011x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,986.1 | 7,543.8-7,543.8 | 3.97 | yes | `b200_sxm-x58-nvl72-tensor` | 4,173.9 | 14,748.5-14,748.5 | 1.42 | yes | 1.434x | 0.511x | 0.357x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 649.0-649.0 | 137.78 | **no** | `b200_sxm-x49-nvl72-tensor` | 3,804.6 | 11,596.9-11,596.9 | 1.64 | yes | 4.701x | 0.056x | 0.012x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,986.1 | 7,543.8-7,543.8 | 3.97 | yes | `b200_sxm-x58-nvl72-tensor` | 3,933.1 | 12,391.1-12,391.1 | 1.59 | yes | 1.522x | 0.609x | 0.400x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 649.0-649.0 | 137.78 | **no** | `b200_sxm-x49-nvl72-tensor` | 3,379.4 | 8,754.6-8,754.6 | 1.93 | yes | 5.292x | 0.074x | 0.014x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 5,978.8 | 7,541.0-7,541.0 | 3.96 | yes | `b200_sxm-x116-nvl72-hybrid` | 3,895.4 | 12,300.8-12,300.8 | 1.58 | yes | 1.535x | 0.613x | 0.399x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 649.0-649.0 | 137.78 | **no** | `b200_sxm-x49-nvl72-tensor` | 2,781.4 | 6,136.3-6,136.3 | 2.27 | yes | 6.430x | 0.106x | 0.016x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,964.3 | 7,535.5-7,535.5 | 3.96 | yes | `b200_sxm-x231-nvl72-hybrid` | 3,819.8 | 11,824.6-11,824.6 | 1.62 | yes | 1.561x | 0.637x | 0.408x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 649.0-649.0 | 137.78 | **no** | `b200_sxm-x49-nvl72-tensor` | 2,094.6 | 4,192.1-4,192.1 | 2.50 | yes | 8.539x | 0.155x | 0.018x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,915.6 | 7,442.6-7,442.6 | 3.97 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,671.5 | 10,420.9-10,420.9 | 1.76 | yes | 1.611x | 0.714x | 0.443x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 16,612.5 | 676.5-676.5 | 122.79 | **no** | `b200_sxm-x110-nvl72-hybrid` | 2,185.1 | 4,478.3-4,478.3 | 2.44 | yes | 7.603x | 0.151x | 0.020x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,782.4 | 7,112.6-7,112.6 | 4.06 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,184.1 | 7,805.4-7,805.4 | 2.04 | yes | 1.816x | 0.911x | 0.502x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 16,612.5 | 676.5-676.5 | 122.79 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,926.0 | 3,797.1-3,797.1 | 2.54 | yes | 8.625x | 0.178x | 0.021x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 5,568.7 | 181.1-181.1 | 153.78 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,589.9 | 3,053.4-3,053.4 | 2.60 | yes | 3.503x | 0.059x | 0.017x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,666.3 | 616.5-616.5 | 54.07 | **no** | `b200_sxm-x173-nvl72-hybrid` | 926.6 | 1,522.1-1,522.1 | 3.04 | yes | 7.194x | 0.405x | 0.056x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 5,568.7 | 181.1-181.1 | 153.78 | **no** | `b200_sxm-x231-nvl72-hybrid` | 1,060.1 | 1,794.9-1,794.9 | 2.95 | yes | 5.253x | 0.101x | 0.019x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,847.6 | 154.7-154.7 | 59.72 | **no** | `b200_sxm-x173-expert` | 474.9 | 670.0-670.0 | 3.54 | yes | 3.890x | 0.231x | 0.059x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 3,809.5 | 176.8-176.8 | 107.72 | **no** | `b200_sxm-x347-expert` | 664.0 | 1,194.5-1,194.5 | 2.78 | yes | 5.737x | 0.148x | 0.026x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 566.8 | 143.7-143.7 | 19.72 | **no** | `b200_sxm-x173-expert` | 228.7 | 179.7-179.7 | 6.36 | **no** | 2.478x | 0.799x | 0.323x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,273.2 | 665.9-665.9 | 9.56 | **no** | `b200_sxm-x347-expert` | 379.9 | 356.5-356.5 | 5.33 | **no** | 3.352x | 1.868x | 0.557x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.011x to 0.557x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 6 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 446.5-446.5 | 154.41 | **no** | `a100_sxm_80gb-x136-tensor` | 1,120.0 | 2,767.5-2,767.5 | 2.02 | yes | 12.312x | 0.161x | 0.013x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5,932.5 | 6,073.3-6,073.3 | 4.88 | yes | `a100_sxm_80gb-x112-tensor` | 1,106.1 | 2,730.8-2,730.8 | 2.03 | yes | 5.364x | 2.224x | 0.415x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 446.5-446.5 | 154.41 | **no** | `a100_sxm_80gb-x136-tensor` | 987.6 | 1,828.1-1,828.1 | 2.70 | yes | 13.963x | 0.244x | 0.017x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5,932.5 | 6,073.3-6,073.3 | 4.88 | yes | `a100_sxm_80gb-x112-tensor` | 973.8 | 1,810.2-1,810.2 | 2.69 | yes | 6.092x | 3.355x | 0.551x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 446.5-446.5 | 154.41 | **no** | `a100_sxm_80gb-x136-tensor` | 799.3 | 1,098.3-1,098.3 | 3.64 | yes | 17.253x | 0.407x | 0.024x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 5,925.3 | 5,874.8-5,874.8 | 5.04 | **no** | `a100_sxm_80gb-x224-tensor` | 823.7 | 1,111.1-1,111.1 | 3.71 | yes | 7.194x | 5.287x | 0.735x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 446.5-446.5 | 154.41 | **no** | `a100_sxm_80gb-x136-hybrid` | 690.8 | 1,513.8-1,513.8 | 2.28 | yes | 19.961x | 0.295x | 0.015x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,911.1 | 5,871.4-5,871.4 | 5.03 | **no** | `a100_sxm_80gb-x448-hybrid` | 665.0 | 1,292.6-1,292.6 | 2.57 | yes | 8.888x | 4.542x | 0.511x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 446.5-446.5 | 154.41 | **no** | `a100_sxm_80gb-x136-hybrid` | 690.8 | 1,513.8-1,513.8 | 2.28 | yes | 19.961x | 0.295x | 0.015x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,846.0 | 5,794.7-5,794.7 | 5.04 | **no** | `a100_sxm_80gb-x672-hybrid` | 665.0 | 1,183.8-1,183.8 | 2.81 | yes | 8.790x | 4.895x | 0.557x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 446.5-446.5 | 154.41 | **no** | `a100_sxm_80gb-x136-hybrid` | 567.9 | 1,110.7-1,110.7 | 2.56 | yes | 24.280x | 0.402x | 0.017x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,650.9 | 5,518.9-5,518.9 | 5.12 | **no** | `a100_sxm_80gb-x672-hybrid` | 665.0 | 1,183.8-1,183.8 | 2.81 | yes | 8.497x | 4.662x | 0.549x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 12,954.3 | 488.2-488.2 | 132.66 | **no** | `a100_sxm_80gb-x335-hybrid` | 588.8 | 1,130.5-1,130.5 | 2.60 | yes | 22.003x | 0.432x | 0.020x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,297.4 | 5,039.1-5,039.1 | 5.26 | **no** | `a100_sxm_80gb-x672-hybrid` | 665.0 | 1,183.8-1,183.8 | 2.81 | yes | 7.965x | 4.257x | 0.534x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,970.1 | 445.1-445.1 | 55.83 | **no** | `a100_sxm_80gb-x335-hybrid` | 301.9 | 551.1-551.1 | 2.74 | yes | 16.464x | 0.808x | 0.049x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,851.6 | 3,311.7-3,311.7 | 5.82 | **no** | `a100_sxm_80gb-x672-hybrid` | 445.7 | 718.7-718.7 | 3.10 | yes | 8.641x | 4.608x | 0.533x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 1,623.3 | 194.6-194.6 | 41.71 | **no** | `a100_sxm_80gb-x272-expert` | 202.4 | 292.3-292.3 | 3.46 | yes | 8.018x | 0.666x | 0.083x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,556.0 | 127.5-127.5 | 100.21 | **no** | `a100_sxm_80gb-x672-expert` | 285.0 | 685.9-685.9 | 2.08 | yes | 8.970x | 0.186x | 0.021x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 566.8 | 125.1-125.1 | 22.65 | **no** | `a100_sxm_80gb-x335-expert` | 139.1 | 92.1-92.1 | 7.55 | **no** | 4.075x | 1.359x | 0.333x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 657.8 | 105.4-105.4 | 31.21 | **no** | `a100_sxm_80gb-x672-expert` | 206.5 | 183.1-183.1 | 5.64 | **no** | 3.186x | 0.576x | 0.181x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.013x to 0.735x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 2 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 649.0-649.0 | 137.78 | **no** | `b200_sxm-x49-nvl72-tensor` | 4,065.4 | 13,962.0-13,962.0 | 1.46 | yes | 4.399x | 0.046x | 0.011x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,986.1 | 7,543.8-7,543.8 | 3.97 | yes | `b200_sxm-x58-nvl72-tensor` | 4,173.9 | 14,748.5-14,748.5 | 1.42 | yes | 1.434x | 0.511x | 0.357x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 649.0-649.0 | 137.78 | **no** | `b200_sxm-x49-nvl72-tensor` | 3,804.6 | 11,596.9-11,596.9 | 1.64 | yes | 4.701x | 0.056x | 0.012x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,986.1 | 7,543.8-7,543.8 | 3.97 | yes | `b200_sxm-x58-nvl72-tensor` | 3,933.1 | 12,391.1-12,391.1 | 1.59 | yes | 1.522x | 0.609x | 0.400x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 649.0-649.0 | 137.78 | **no** | `b200_sxm-x49-nvl72-tensor` | 3,379.4 | 8,754.6-8,754.6 | 1.93 | yes | 5.292x | 0.074x | 0.014x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 5,978.8 | 7,541.0-7,541.0 | 3.96 | yes | `b200_sxm-x116-nvl72-hybrid` | 3,895.4 | 12,300.8-12,300.8 | 1.58 | yes | 1.535x | 0.613x | 0.399x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 649.0-649.0 | 137.78 | **no** | `b200_sxm-x49-nvl72-tensor` | 2,781.4 | 6,136.3-6,136.3 | 2.27 | yes | 6.430x | 0.106x | 0.016x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,964.3 | 7,535.5-7,535.5 | 3.96 | yes | `b200_sxm-x231-nvl72-hybrid` | 3,819.8 | 11,824.6-11,824.6 | 1.62 | yes | 1.561x | 0.637x | 0.408x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 649.0-649.0 | 137.78 | **no** | `b200_sxm-x49-nvl72-tensor` | 2,094.6 | 4,192.1-4,192.1 | 2.50 | yes | 8.539x | 0.155x | 0.018x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,915.6 | 7,442.6-7,442.6 | 3.97 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,671.5 | 10,420.9-10,420.9 | 1.76 | yes | 1.611x | 0.714x | 0.443x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 16,612.5 | 676.5-676.5 | 122.79 | **no** | `b200_sxm-x110-nvl72-hybrid` | 2,185.1 | 4,478.3-4,478.3 | 2.44 | yes | 7.603x | 0.151x | 0.020x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,782.4 | 7,112.6-7,112.6 | 4.06 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,184.1 | 7,805.5-7,805.5 | 2.04 | yes | 1.816x | 0.911x | 0.502x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 16,612.5 | 676.5-676.5 | 122.79 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,926.1 | 3,797.1-3,797.1 | 2.54 | yes | 8.625x | 0.178x | 0.021x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 5,568.7 | 181.1-181.1 | 153.78 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,589.9 | 3,053.4-3,053.4 | 2.60 | yes | 3.503x | 0.059x | 0.017x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,666.3 | 616.5-616.5 | 54.07 | **no** | `b200_sxm-x173-nvl72-hybrid` | 926.6 | 1,522.1-1,522.1 | 3.04 | yes | 7.194x | 0.405x | 0.056x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 5,568.7 | 181.1-181.1 | 153.78 | **no** | `b200_sxm-x231-nvl72-hybrid` | 1,060.1 | 1,794.9-1,794.9 | 2.95 | yes | 5.253x | 0.101x | 0.019x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,847.6 | 154.7-154.7 | 59.72 | **no** | `b200_sxm-x173-expert` | 474.9 | 670.0-670.0 | 3.54 | yes | 3.890x | 0.231x | 0.059x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 3,809.5 | 176.8-176.8 | 107.72 | **no** | `b200_sxm-x347-expert` | 664.0 | 1,194.5-1,194.5 | 2.78 | yes | 5.737x | 0.148x | 0.026x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 566.8 | 143.7-143.7 | 19.72 | **no** | `b200_sxm-x173-expert` | 228.7 | 179.7-179.7 | 6.36 | **no** | 2.478x | 0.799x | 0.323x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,273.5 | 665.9-665.9 | 9.56 | **no** | `b200_sxm-x347-expert` | 379.9 | 356.5-356.5 | 5.33 | **no** | 3.352x | 1.868x | 0.557x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.011x to 0.557x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 6 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 446.5-446.5 | 154.41 | **no** | `a100_sxm_80gb-x136-tensor` | 1,120.0 | 2,767.5-2,767.5 | 2.02 | yes | 12.312x | 0.161x | 0.013x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5,932.5 | 6,073.3-6,073.3 | 4.88 | yes | `a100_sxm_80gb-x112-tensor` | 1,106.1 | 2,730.8-2,730.8 | 2.03 | yes | 5.364x | 2.224x | 0.415x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 446.5-446.5 | 154.41 | **no** | `a100_sxm_80gb-x136-tensor` | 987.6 | 1,828.1-1,828.1 | 2.70 | yes | 13.963x | 0.244x | 0.017x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5,932.5 | 6,073.3-6,073.3 | 4.88 | yes | `a100_sxm_80gb-x112-tensor` | 973.8 | 1,810.2-1,810.2 | 2.69 | yes | 6.092x | 3.355x | 0.551x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 446.5-446.5 | 154.41 | **no** | `a100_sxm_80gb-x136-tensor` | 799.3 | 1,098.3-1,098.3 | 3.64 | yes | 17.253x | 0.407x | 0.024x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 5,925.4 | 5,874.8-5,874.8 | 5.04 | **no** | `a100_sxm_80gb-x224-tensor` | 823.7 | 1,111.1-1,111.1 | 3.71 | yes | 7.194x | 5.287x | 0.735x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 446.5-446.5 | 154.41 | **no** | `a100_sxm_80gb-x136-hybrid` | 690.8 | 1,513.8-1,513.8 | 2.28 | yes | 19.961x | 0.295x | 0.015x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,911.1 | 5,871.4-5,871.4 | 5.03 | **no** | `a100_sxm_80gb-x448-hybrid` | 665.0 | 1,292.6-1,292.6 | 2.57 | yes | 8.888x | 4.542x | 0.511x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 446.5-446.5 | 154.41 | **no** | `a100_sxm_80gb-x136-hybrid` | 690.8 | 1,513.8-1,513.8 | 2.28 | yes | 19.961x | 0.295x | 0.015x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,846.1 | 5,794.7-5,794.7 | 5.04 | **no** | `a100_sxm_80gb-x672-hybrid` | 665.0 | 1,183.8-1,183.8 | 2.81 | yes | 8.790x | 4.895x | 0.557x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 446.5-446.5 | 154.41 | **no** | `a100_sxm_80gb-x136-hybrid` | 567.9 | 1,110.7-1,110.7 | 2.56 | yes | 24.280x | 0.402x | 0.017x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,651.0 | 5,518.9-5,518.9 | 5.12 | **no** | `a100_sxm_80gb-x672-hybrid` | 665.0 | 1,183.8-1,183.8 | 2.81 | yes | 8.497x | 4.662x | 0.549x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 12,954.3 | 488.2-488.2 | 132.66 | **no** | `a100_sxm_80gb-x335-hybrid` | 588.8 | 1,130.5-1,130.5 | 2.60 | yes | 22.003x | 0.432x | 0.020x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,297.6 | 5,039.1-5,039.1 | 5.26 | **no** | `a100_sxm_80gb-x672-hybrid` | 665.0 | 1,183.8-1,183.8 | 2.81 | yes | 7.966x | 4.257x | 0.534x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,970.1 | 445.1-445.1 | 55.83 | **no** | `a100_sxm_80gb-x335-hybrid` | 301.9 | 551.1-551.1 | 2.74 | yes | 16.464x | 0.808x | 0.049x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,852.0 | 3,311.7-3,311.7 | 5.82 | **no** | `a100_sxm_80gb-x672-hybrid` | 445.7 | 718.7-718.7 | 3.10 | yes | 8.642x | 4.608x | 0.533x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 1,623.3 | 194.6-194.6 | 41.71 | **no** | `a100_sxm_80gb-x272-expert` | 202.4 | 292.3-292.3 | 3.46 | yes | 8.018x | 0.666x | 0.083x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,556.6 | 127.5-127.5 | 100.24 | **no** | `a100_sxm_80gb-x672-expert` | 285.0 | 685.9-685.9 | 2.08 | yes | 8.972x | 0.186x | 0.021x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 566.8 | 125.1-125.1 | 22.65 | **no** | `a100_sxm_80gb-x335-expert` | 139.1 | 92.1-92.1 | 7.55 | **no** | 4.075x | 1.359x | 0.333x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 658.0 | 105.4-105.4 | 31.22 | **no** | `a100_sxm_80gb-x672-expert` | 206.5 | 183.1-183.1 | 5.64 | **no** | 3.187x | 0.576x | 0.181x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.013x to 0.735x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 2 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x63` | 12,688.5 | 11,197.7-11,197.7 | 5.67 | **no** | `b200_sxm-x32-nvl72-tensor` | 3,539.8 | 11,637.8-11,637.8 | 1.52 | yes | 3.584x | 0.962x | 0.268x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 5,458.3 | 5,920.7-5,920.7 | 4.61 | yes | `b200_sxm-x58-nvl72-tensor` | 3,921.7 | 14,182.3-14,182.3 | 1.38 | yes | 1.392x | 0.417x | 0.300x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,320.2 | 1,010.7-1,010.7 | 31.27 | **no** | `b200_sxm-x173-nvl72-hybrid` | 3,852.3 | 13,429.7-13,429.7 | 1.43 | yes | 1.641x | 0.075x | 0.046x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 4,447.5 | 9,633.6-9,633.6 | 2.31 | yes | `b200_sxm-x953-nvl72-hybrid` | 3,590.6 | 10,248.4-10,248.4 | 1.75 | yes | 1.239x | 0.940x | 0.759x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,320.2 | 1,010.7-1,010.7 | 31.27 | **no** | `b200_sxm-x173-nvl72-hybrid` | 3,775.7 | 12,613.6-12,613.6 | 1.50 | yes | 1.674x | 0.080x | 0.048x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 4,447.5 | 9,633.6-9,633.6 | 2.31 | yes | `b200_sxm-x953-nvl72-hybrid` | 3,590.6 | 10,248.4-10,248.4 | 1.75 | yes | 1.239x | 0.940x | 0.759x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,320.2 | 1,010.7-1,010.7 | 31.27 | **no** | `b200_sxm-x173-nvl72-hybrid` | 3,500.4 | 10,499.0-10,499.0 | 1.67 | yes | 1.806x | 0.096x | 0.053x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 4,447.5 | 9,633.6-9,633.6 | 2.31 | yes | `b200_sxm-x953-nvl72-hybrid` | 3,590.6 | 10,248.4-10,248.4 | 1.75 | yes | 1.239x | 0.940x | 0.759x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,320.2 | 1,010.7-1,010.7 | 31.27 | **no** | `b200_sxm-x173-nvl72-hybrid` | 3,065.2 | 8,235.2-8,235.2 | 1.86 | yes | 2.062x | 0.123x | 0.060x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 4,447.5 | 9,633.6-9,633.6 | 2.31 | yes | `b200_sxm-x953-nvl72-hybrid` | 3,562.1 | 9,884.3-9,884.3 | 1.80 | yes | 1.249x | 0.975x | 0.781x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,320.2 | 1,010.7-1,010.7 | 31.27 | **no** | `b200_sxm-x173-nvl72-hybrid` | 2,479.7 | 5,992.4-5,992.4 | 2.07 | yes | 2.549x | 0.169x | 0.066x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 4,447.5 | 9,633.6-9,633.6 | 2.31 | yes | `b200_sxm-x953-nvl72-hybrid` | 3,350.8 | 8,224.1-8,224.1 | 2.04 | yes | 1.327x | 1.171x | 0.883x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,320.2 | 1,010.7-1,010.7 | 31.27 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,840.8 | 4,179.1-4,179.1 | 2.20 | yes | 3.433x | 0.242x | 0.070x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 3,760.8 | 8,496.6-8,496.6 | 2.21 | yes | `b200_sxm-x953-nvl72-hybrid` | 3,001.6 | 6,572.6-6,572.6 | 2.28 | yes | 1.253x | 1.293x | 1.032x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349-romfill` | 2,332.0 | 699.8-699.8 | 16.66 | **no** | `b200_sxm-x178-nvl72-hybrid` | 878.5 | 1,671.1-1,671.1 | 2.63 | yes | 2.655x | 0.419x | 0.158x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 1,922.4 | 469.7-469.7 | 20.46 | **no** | `b200_sxm-x953-nvl72-hybrid` | 1,906.5 | 3,375.6-3,375.6 | 2.82 | yes | 1.008x | 0.139x | 0.138x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x349-romfill` | 606.4 | 176.5-176.5 | 17.18 | **no** | `b200_sxm-x178-nvl72-hybrid` | 347.5 | 494.9-494.9 | 3.51 | yes | 1.745x | 0.357x | 0.204x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 650.5 | 428.4-428.4 | 7.59 | **no** | `b200_sxm-x953-nvl72-hybrid` | 896.9 | 1,288.0-1,288.0 | 3.48 | yes | 0.725x | 0.333x | 0.459x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x349-romfill` | 152.5 | 74.0-74.0 | 10.31 | **no** | `b200_sxm-x178-expert` | 114.1 | 172.9-172.9 | 3.30 | yes | 1.337x | 0.428x | 0.320x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill` | 183.9 | 213.6-213.6 | 4.30 | yes | `b200_sxm-x953-expert` | 442.7 | 871.5-871.5 | 2.54 | yes | 0.415x | 0.245x | 0.590x |

**Does the ratio compress?** Of 20 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.046x to 1.032x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 8 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 20,313.6 | 1,170.9-1,170.9 | 86.75 | **no** | `b200_sxm-x26-nvl72-tensor` | 3,471.9 | 10,841.5-10,841.5 | 1.60 | yes | 5.851x | 0.108x | 0.018x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 6,648.0 | 325.9-325.9 | 102.00 | **no** | `b200_sxm-x116-nvl72-hybrid` | 3,947.5 | 13,993.7-13,993.7 | 1.41 | yes | 1.684x | 0.023x | 0.014x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 20,313.6 | 1,170.9-1,170.9 | 86.75 | **no** | `b200_sxm-x26-nvl72-tensor` | 3,218.9 | 8,826.6-8,826.6 | 1.82 | yes | 6.311x | 0.133x | 0.021x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 6,648.0 | 325.9-325.9 | 102.00 | **no** | `b200_sxm-x116-nvl72-hybrid` | 3,947.5 | 13,993.7-13,993.7 | 1.41 | yes | 1.684x | 0.023x | 0.014x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 20,313.6 | 1,170.9-1,170.9 | 86.75 | **no** | `b200_sxm-x26-nvl72-tensor` | 2,820.4 | 6,683.7-6,683.7 | 2.11 | yes | 7.202x | 0.175x | 0.024x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 6,648.0 | 325.9-325.9 | 102.00 | **no** | `b200_sxm-x116-nvl72-hybrid` | 3,774.4 | 12,010.6-12,010.6 | 1.57 | yes | 1.761x | 0.027x | 0.015x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 20,313.6 | 1,170.9-1,170.9 | 86.75 | **no** | `b200_sxm-x26-nvl72-tensor` | 2,288.0 | 4,918.5-4,918.5 | 2.33 | yes | 8.878x | 0.238x | 0.027x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 6,648.0 | 325.9-325.9 | 102.00 | **no** | `b200_sxm-x116-nvl72-hybrid` | 3,477.6 | 9,807.0-9,807.0 | 1.77 | yes | 1.912x | 0.033x | 0.017x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 19,024.5 | 1,201.9-1,201.9 | 79.14 | **no** | `b200_sxm-x44-nvl72-tensor` | 2,224.9 | 4,929.9-4,929.9 | 2.26 | yes | 8.551x | 0.244x | 0.029x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 6,648.0 | 325.9-325.9 | 102.00 | **no** | `b200_sxm-x116-nvl72-hybrid` | 3,026.6 | 7,412.6-7,412.6 | 2.04 | yes | 2.197x | 0.044x | 0.020x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18,398.7 | 1,214.8-1,214.8 | 75.73 | **no** | `b200_sxm-x173-nvl72-hybrid` | 2,764.3 | 6,306.3-6,306.3 | 2.19 | yes | 6.656x | 0.193x | 0.029x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 6,648.0 | 325.9-325.9 | 102.00 | **no** | `b200_sxm-x116-nvl72-hybrid` | 2,453.2 | 5,397.9-5,397.9 | 2.27 | yes | 2.710x | 0.060x | 0.022x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18,398.7 | 1,214.8-1,214.8 | 75.73 | **no** | `b200_sxm-x173-nvl72-hybrid` | 2,173.0 | 4,490.9-4,490.9 | 2.42 | yes | 8.467x | 0.270x | 0.032x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 6,648.0 | 325.9-325.9 | 102.00 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,870.2 | 3,745.7-3,745.7 | 2.50 | yes | 3.555x | 0.087x | 0.024x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7,883.1 | 1,064.6-1,064.6 | 37.02 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,210.5 | 1,864.2-1,864.2 | 3.25 | yes | 6.512x | 0.571x | 0.088x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 6,648.0 | 325.9-325.9 | 102.00 | **no** | `b200_sxm-x231-nvl72-hybrid` | 1,344.7 | 2,187.2-2,187.2 | 3.07 | yes | 4.944x | 0.149x | 0.030x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 2,266.9 | 267.9-267.9 | 42.31 | **no** | `b200_sxm-x173-nvl72-hybrid` | 625.0 | 570.2-570.2 | 5.48 | **no** | 3.627x | 0.470x | 0.130x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 4,602.0 | 314.9-314.9 | 73.07 | **no** | `b200_sxm-x347-nvl72-hybrid` | 828.2 | 839.5-839.5 | 4.93 | yes | 5.557x | 0.375x | 0.068x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 580.2 | 172.9-172.9 | 16.78 | **no** | `b200_sxm-x173-expert` | 271.7 | 208.4-208.4 | 6.52 | **no** | 2.136x | 0.829x | 0.388x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,225.1 | 241.9-241.9 | 25.32 | **no** | `b200_sxm-x347-expert` | 448.2 | 412.0-412.0 | 5.44 | **no** | 2.734x | 0.587x | 0.215x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.014x to 0.388x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 17 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 20,317.2 | 1,198.9-1,198.9 | 84.73 | **no** | `b200_sxm-x26-nvl72-tensor` | 3,474.6 | 10,846.7-10,846.7 | 1.60 | yes | 5.847x | 0.111x | 0.019x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 7,768.0 | 362.3-362.3 | 107.19 | **no** | `b200_sxm-x29-nvl72-tensor` | 3,559.9 | 11,371.7-11,371.7 | 1.57 | yes | 2.182x | 0.032x | 0.015x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 20,317.2 | 1,198.9-1,198.9 | 84.73 | **no** | `b200_sxm-x26-nvl72-tensor` | 3,223.4 | 8,833.5-8,833.5 | 1.82 | yes | 6.303x | 0.136x | 0.022x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 7,768.0 | 362.3-362.3 | 107.19 | **no** | `b200_sxm-x29-nvl72-tensor` | 3,319.5 | 9,356.4-9,356.4 | 1.77 | yes | 2.340x | 0.039x | 0.017x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 20,317.2 | 1,198.9-1,198.9 | 84.73 | **no** | `b200_sxm-x26-nvl72-tensor` | 2,827.4 | 6,691.5-6,691.5 | 2.11 | yes | 7.186x | 0.179x | 0.025x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 7,768.0 | 362.3-362.3 | 107.19 | **no** | `b200_sxm-x29-nvl72-tensor` | 2,935.2 | 7,149.5-7,149.5 | 2.05 | yes | 2.647x | 0.051x | 0.019x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 20,317.2 | 1,198.9-1,198.9 | 84.73 | **no** | `b200_sxm-x26-nvl72-tensor` | 2,297.2 | 4,927.0-4,927.0 | 2.33 | yes | 8.844x | 0.243x | 0.028x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 7,768.0 | 362.3-362.3 | 107.19 | **no** | `b200_sxm-x29-nvl72-tensor` | 2,410.5 | 5,286.3-5,286.3 | 2.28 | yes | 3.223x | 0.069x | 0.021x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 20,042.4 | 1,208.1-1,208.1 | 82.95 | **no** | `b200_sxm-x44-nvl72-tensor` | 2,235.2 | 4,940.0-4,940.0 | 2.26 | yes | 8.967x | 0.245x | 0.027x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 7,768.0 | 362.3-362.3 | 107.19 | **no** | `b200_sxm-x29-nvl72-tensor` | 1,830.9 | 3,959.5-3,959.5 | 2.31 | yes | 4.243x | 0.092x | 0.022x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 19,337.7 | 1,221.0-1,221.0 | 79.19 | **no** | `b200_sxm-x173-nvl72-hybrid` | 2,772.4 | 6,314.7-6,314.7 | 2.20 | yes | 6.975x | 0.193x | 0.028x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 7,768.0 | 362.3-362.3 | 107.19 | **no** | `b200_sxm-x29-nvl72-tensor` | 1,326.0 | 2,977.9-2,977.9 | 2.23 | yes | 5.858x | 0.122x | 0.021x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 19,337.7 | 1,221.0-1,221.0 | 79.19 | **no** | `b200_sxm-x173-nvl72-hybrid` | 2,183.1 | 4,499.4-4,499.4 | 2.43 | yes | 8.858x | 0.271x | 0.031x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 7,115.6 | 327.6-327.6 | 108.61 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,881.2 | 3,754.6-3,754.6 | 2.51 | yes | 3.782x | 0.087x | 0.023x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8,410.1 | 1,079.2-1,079.2 | 38.96 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,223.0 | 1,870.1-1,870.1 | 3.27 | yes | 6.876x | 0.577x | 0.084x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 7,115.6 | 327.6-327.6 | 108.61 | **no** | `b200_sxm-x231-nvl72-hybrid` | 1,356.2 | 2,193.3-2,193.3 | 3.09 | yes | 5.247x | 0.149x | 0.028x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 2,443.0 | 271.6-271.6 | 44.98 | **no** | `b200_sxm-x173-nvl72-hybrid` | 638.5 | 572.4-572.4 | 5.58 | **no** | 3.826x | 0.474x | 0.124x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 4,939.9 | 317.3-317.3 | 77.85 | **no** | `b200_sxm-x347-nvl72-hybrid` | 839.9 | 841.9-841.9 | 4.99 | yes | 5.881x | 0.377x | 0.064x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 626.5 | 179.2-179.2 | 17.48 | **no** | `b200_sxm-x173-expert` | 282.0 | 209.7-209.7 | 6.72 | **no** | 2.221x | 0.854x | 0.385x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,637.4 | 768.6-768.6 | 10.65 | **no** | `b200_sxm-x347-expert` | 462.1 | 414.5-414.5 | 5.57 | **no** | 3.543x | 1.854x | 0.523x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.015x to 0.523x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 17 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 6,308.0 | 202.7-202.7 | 155.59 | **no** | `b200_sxm-x157-nvl72-hybrid` | 2,277.1 | 6,609.7-6,609.7 | 1.72 | yes | 2.770x | 0.031x | 0.011x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 3,784.7 | 3,159.9-3,159.9 | 5.99 | **no** | `b200_sxm-x116-nvl72-hybrid` | 2,351.4 | 7,078.4-7,078.4 | 1.66 | yes | 1.610x | 0.446x | 0.277x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 6,308.0 | 202.7-202.7 | 155.59 | **no** | `b200_sxm-x157-nvl72-hybrid` | 2,277.1 | 6,609.7-6,609.7 | 1.72 | yes | 2.770x | 0.031x | 0.011x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 3,745.8 | 2,955.8-2,955.8 | 6.34 | **no** | `b200_sxm-x289-nvl72-hybrid` | 2,311.6 | 6,428.3-6,428.3 | 1.80 | yes | 1.620x | 0.460x | 0.284x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 6,308.0 | 202.7-202.7 | 155.59 | **no** | `b200_sxm-x157-nvl72-hybrid` | 2,201.6 | 5,991.0-5,991.0 | 1.84 | yes | 2.865x | 0.034x | 0.012x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 3,745.8 | 2,955.8-2,955.8 | 6.34 | **no** | `b200_sxm-x289-nvl72-hybrid` | 2,311.6 | 6,428.3-6,428.3 | 1.80 | yes | 1.620x | 0.460x | 0.284x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 6,308.0 | 202.7-202.7 | 155.59 | **no** | `b200_sxm-x157-nvl72-hybrid` | 1,946.2 | 4,628.8-4,628.8 | 2.10 | yes | 3.241x | 0.044x | 0.014x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 3,745.8 | 2,955.8-2,955.8 | 6.34 | **no** | `b200_sxm-x289-nvl72-hybrid` | 2,184.3 | 5,547.1-5,547.1 | 1.97 | yes | 1.715x | 0.533x | 0.311x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 6,308.0 | 202.7-202.7 | 155.59 | **no** | `b200_sxm-x157-nvl72-hybrid` | 1,587.3 | 3,333.2-3,333.2 | 2.38 | yes | 3.974x | 0.061x | 0.015x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,680.5 | 2,908.8-2,908.8 | 6.33 | **no** | `b200_sxm-x347-nvl72-hybrid` | 2,026.6 | 4,534.6-4,534.6 | 2.23 | yes | 1.816x | 0.641x | 0.353x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 6,308.0 | 202.7-202.7 | 155.59 | **no** | `b200_sxm-x157-nvl72-hybrid` | 1,175.5 | 2,236.4-2,236.4 | 2.63 | yes | 5.366x | 0.091x | 0.017x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 3,450.0 | 1,231.9-1,231.9 | 14.00 | **no** | `b200_sxm-x347-nvl72-hybrid` | 1,654.8 | 3,326.6-3,326.6 | 2.49 | yes | 2.085x | 0.370x | 0.178x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 6,308.0 | 202.7-202.7 | 155.59 | **no** | `b200_sxm-x157-nvl72-hybrid` | 800.1 | 1,504.9-1,504.9 | 2.66 | yes | 7.884x | 0.135x | 0.017x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 3,066.1 | 1,197.6-1,197.6 | 12.80 | **no** | `b200_sxm-x347-nvl72-hybrid` | 1,229.1 | 2,233.3-2,233.3 | 2.75 | yes | 2.495x | 0.536x | 0.215x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 2,584.2 | 172.7-172.7 | 74.83 | **no** | `b200_sxm-x173-nvl72-hybrid` | 376.0 | 681.0-681.0 | 2.76 | yes | 6.874x | 0.254x | 0.037x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,838.5 | 1,026.1-1,026.1 | 8.96 | **no** | `b200_sxm-x347-nvl72-hybrid` | 556.5 | 958.7-958.7 | 2.90 | yes | 3.304x | 1.070x | 0.324x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 691.3 | 43.3-43.3 | 79.92 | **no** | `b200_sxm-x173-nvl72-hybrid` | 193.6 | 230.8-230.8 | 4.19 | yes | 3.572x | 0.187x | 0.052x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 844.4 | 60.1-60.1 | 70.29 | **no** | `b200_sxm-x347-expert` | 267.1 | 535.7-535.7 | 2.49 | yes | 3.161x | 0.112x | 0.035x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 174.6 | 33.4-33.4 | 26.16 | **no** | `b200_sxm-x173-expert` | 90.1 | 79.7-79.7 | 5.65 | **no** | 1.939x | 0.418x | 0.216x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 214.5 | 22.4-22.4 | 47.93 | **no** | `b200_sxm-x347-expert` | 151.2 | 158.9-158.9 | 4.76 | yes | 1.418x | 0.141x | 0.099x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.011x to 0.353x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 6,790.3 | 229.0-229.0 | 148.23 | **no** | `b200_sxm-x138-nvl72-hybrid` | 2,454.4 | 7,611.6-7,611.6 | 1.61 | yes | 2.767x | 0.030x | 0.011x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3,832.3 | 2,986.2-2,986.2 | 6.42 | **no** | `b200_sxm-x144-nvl72-hybrid` | 2,476.9 | 7,734.8-7,734.8 | 1.60 | yes | 1.547x | 0.386x | 0.250x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 6,790.3 | 229.0-229.0 | 148.23 | **no** | `b200_sxm-x138-nvl72-hybrid` | 2,454.4 | 7,611.6-7,611.6 | 1.61 | yes | 2.767x | 0.030x | 0.011x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3,832.3 | 2,986.2-2,986.2 | 6.42 | **no** | `b200_sxm-x144-nvl72-hybrid` | 2,476.9 | 7,734.8-7,734.8 | 1.60 | yes | 1.547x | 0.386x | 0.250x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 6,790.3 | 229.0-229.0 | 148.23 | **no** | `b200_sxm-x138-nvl72-hybrid` | 2,262.5 | 6,061.3-6,061.3 | 1.87 | yes | 3.001x | 0.038x | 0.013x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3,832.3 | 2,986.2-2,986.2 | 6.42 | **no** | `b200_sxm-x144-nvl72-hybrid` | 2,287.8 | 6,169.8-6,169.8 | 1.85 | yes | 1.675x | 0.484x | 0.289x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 6,790.3 | 229.0-229.0 | 148.23 | **no** | `b200_sxm-x138-nvl72-hybrid` | 1,961.5 | 4,581.6-4,581.6 | 2.14 | yes | 3.462x | 0.050x | 0.014x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,827.8 | 2,985.6-2,985.6 | 6.41 | **no** | `b200_sxm-x231-nvl72-hybrid` | 2,127.2 | 5,243.6-5,243.6 | 2.03 | yes | 1.799x | 0.569x | 0.316x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 6,790.3 | 229.0-229.0 | 148.23 | **no** | `b200_sxm-x138-nvl72-hybrid` | 1,561.7 | 3,139.4-3,139.4 | 2.49 | yes | 4.348x | 0.073x | 0.017x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,782.7 | 2,946.7-2,946.7 | 6.42 | **no** | `b200_sxm-x347-nvl72-hybrid` | 2,037.2 | 4,545.2-4,545.2 | 2.24 | yes | 1.857x | 0.648x | 0.349x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 6,790.3 | 229.0-229.0 | 148.23 | **no** | `b200_sxm-x138-nvl72-hybrid` | 1,133.2 | 2,108.3-2,108.3 | 2.69 | yes | 5.992x | 0.109x | 0.018x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,634.2 | 2,803.8-2,803.8 | 6.48 | **no** | `b200_sxm-x347-nvl72-hybrid` | 1,669.1 | 3,338.1-3,338.1 | 2.50 | yes | 2.177x | 0.840x | 0.386x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 6,790.3 | 229.0-229.0 | 148.23 | **no** | `b200_sxm-x138-nvl72-hybrid` | 768.5 | 1,408.5-1,408.5 | 2.73 | yes | 8.836x | 0.163x | 0.018x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 3,379.6 | 1,646.6-1,646.6 | 10.26 | **no** | `b200_sxm-x231-nvl72-hybrid` | 1,012.2 | 1,852.5-1,852.5 | 2.73 | yes | 3.339x | 0.889x | 0.266x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 3,183.6 | 176.2-176.2 | 90.33 | **no** | `b200_sxm-x173-nvl72-hybrid` | 388.0 | 688.7-688.7 | 2.82 | yes | 8.204x | 0.256x | 0.031x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 2,572.8 | 1,067.6-1,067.6 | 12.05 | **no** | `b200_sxm-x347-nvl72-hybrid` | 569.6 | 966.4-966.4 | 2.95 | yes | 4.517x | 1.105x | 0.245x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 865.8 | 44.1-44.1 | 98.06 | **no** | `b200_sxm-x173-nvl72-hybrid` | 206.8 | 235.9-235.9 | 4.38 | yes | 4.186x | 0.187x | 0.045x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,602.5 | 723.9-723.9 | 11.07 | **no** | `b200_sxm-x347-expert` | 279.4 | 545.3-545.3 | 2.56 | yes | 5.735x | 1.327x | 0.231x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 219.2 | 35.6-35.6 | 30.81 | **no** | `b200_sxm-x173-expert` | 102.3 | 82.3-82.3 | 6.21 | **no** | 2.144x | 0.432x | 0.202x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 576.2 | 316.4-316.4 | 9.10 | **no** | `b200_sxm-x347-expert` | 168.0 | 164.0-164.0 | 5.12 | **no** | 3.430x | 1.929x | 0.562x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.011x to 0.562x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 6,893.2 | 232.5-232.5 | 148.25 | **no** | `b200_sxm-x136-nvl72-hybrid` | 2,447.2 | 7,570.2-7,570.2 | 1.62 | yes | 2.817x | 0.031x | 0.011x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3,836.7 | 2,990.6-2,990.6 | 6.41 | **no** | `b200_sxm-x144-nvl72-hybrid` | 2,477.6 | 7,736.2-7,736.2 | 1.60 | yes | 1.549x | 0.387x | 0.250x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 6,893.2 | 232.5-232.5 | 148.25 | **no** | `b200_sxm-x136-nvl72-hybrid` | 2,447.2 | 7,570.2-7,570.2 | 1.62 | yes | 2.817x | 0.031x | 0.011x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3,836.7 | 2,990.6-2,990.6 | 6.41 | **no** | `b200_sxm-x144-nvl72-hybrid` | 2,477.6 | 7,736.2-7,736.2 | 1.60 | yes | 1.549x | 0.387x | 0.250x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 6,893.2 | 232.5-232.5 | 148.25 | **no** | `b200_sxm-x136-nvl72-hybrid` | 2,254.9 | 6,025.6-6,025.6 | 1.87 | yes | 3.057x | 0.039x | 0.013x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3,836.7 | 2,990.6-2,990.6 | 6.41 | **no** | `b200_sxm-x144-nvl72-hybrid` | 2,289.0 | 6,171.5-6,171.5 | 1.85 | yes | 1.676x | 0.485x | 0.289x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 6,893.2 | 232.5-232.5 | 148.25 | **no** | `b200_sxm-x136-nvl72-hybrid` | 1,953.6 | 4,550.8-4,550.8 | 2.15 | yes | 3.528x | 0.051x | 0.014x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,832.2 | 2,989.9-2,989.9 | 6.41 | **no** | `b200_sxm-x231-nvl72-hybrid` | 2,128.5 | 5,245.2-5,245.2 | 2.03 | yes | 1.800x | 0.570x | 0.317x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 6,893.2 | 232.5-232.5 | 148.25 | **no** | `b200_sxm-x136-nvl72-hybrid` | 1,554.1 | 3,116.5-3,116.5 | 2.49 | yes | 4.436x | 0.075x | 0.017x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,788.5 | 2,952.3-2,952.3 | 6.42 | **no** | `b200_sxm-x347-nvl72-hybrid` | 2,038.8 | 4,546.8-4,546.8 | 2.24 | yes | 1.858x | 0.649x | 0.349x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 6,893.2 | 232.5-232.5 | 148.25 | **no** | `b200_sxm-x136-nvl72-hybrid` | 1,126.8 | 2,093.5-2,093.5 | 2.69 | yes | 6.118x | 0.111x | 0.018x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,645.0 | 2,814.1-2,814.1 | 6.48 | **no** | `b200_sxm-x347-nvl72-hybrid` | 1,671.2 | 3,339.7-3,339.7 | 2.50 | yes | 2.181x | 0.843x | 0.386x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 6,893.2 | 232.5-232.5 | 148.25 | **no** | `b200_sxm-x136-nvl72-hybrid` | 763.9 | 1,400.7-1,400.7 | 2.73 | yes | 9.024x | 0.166x | 0.018x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,388.2 | 2,573.2-2,573.2 | 6.58 | **no** | `b200_sxm-x347-nvl72-hybrid` | 1,247.2 | 2,245.2-2,245.2 | 2.78 | yes | 2.717x | 1.146x | 0.422x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 3,295.9 | 176.8-176.8 | 93.24 | **no** | `b200_sxm-x173-nvl72-hybrid` | 389.9 | 689.9-689.9 | 2.83 | yes | 8.454x | 0.256x | 0.030x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 2,572.8 | 1,074.0-1,074.0 | 11.98 | **no** | `b200_sxm-x347-nvl72-hybrid` | 571.6 | 967.5-967.5 | 2.95 | yes | 4.501x | 1.110x | 0.247x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 899.1 | 44.3-44.3 | 101.53 | **no** | `b200_sxm-x173-nvl72-hybrid` | 208.9 | 236.7-236.7 | 4.41 | yes | 4.303x | 0.187x | 0.043x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,639.0 | 735.8-735.8 | 11.14 | **no** | `b200_sxm-x347-expert` | 281.3 | 546.8-546.8 | 2.57 | yes | 5.826x | 1.346x | 0.231x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 227.8 | 35.9-35.9 | 31.70 | **no** | `b200_sxm-x173-expert` | 104.3 | 82.7-82.7 | 6.31 | **no** | 2.183x | 0.434x | 0.199x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 595.3 | 325.6-325.6 | 9.14 | **no** | `b200_sxm-x347-expert` | 170.8 | 164.8-164.8 | 5.18 | **no** | 3.486x | 1.976x | 0.567x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.011x to 0.567x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x63-romfill` | 11,704.1 | 10,009.0-10,009.0 | 5.85 | **no** | `a100_sxm_80gb-x62-tensor` | 1,003.9 | 2,636.8-2,636.8 | 1.90 | yes | 11.658x | 3.796x | 0.326x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 5,380.2 | 4,274.7-4,274.7 | 6.29 | **no** | `a100_sxm_80gb-x168-tensor` | 1,082.1 | 2,877.6-2,877.6 | 1.88 | yes | 4.972x | 1.485x | 0.299x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 5,202.7 | 9,150.3-9,150.3 | 2.84 | yes | `a100_sxm_80gb-x387-tensor` | 742.8 | 1,751.6-1,751.6 | 2.12 | yes | 7.004x | 5.224x | 0.746x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 3,457.0 | 7,681.6-7,681.6 | 2.25 | yes | `a100_sxm_80gb-x2574-tensor` | 754.3 | 1,775.1-1,775.1 | 2.12 | yes | 4.583x | 4.327x | 0.944x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 4,999.4 | 8,485.4-8,485.4 | 2.95 | yes | `a100_sxm_80gb-x387-hybrid` | 656.1 | 1,025.3-1,025.3 | 3.20 | yes | 7.620x | 8.276x | 1.086x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 3,457.0 | 7,681.6-7,681.6 | 2.25 | yes | `a100_sxm_80gb-x2574-tensor` | 662.7 | 1,142.4-1,142.4 | 2.90 | yes | 5.216x | 6.724x | 1.289x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 4,637.1 | 7,408.8-7,408.8 | 3.13 | yes | `a100_sxm_80gb-x387-hybrid` | 656.1 | 1,025.3-1,025.3 | 3.20 | yes | 7.068x | 7.226x | 1.022x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 3,457.0 | 7,681.6-7,681.6 | 2.25 | yes | `a100_sxm_80gb-x2574-hybrid` | 661.2 | 408.4-408.4 | 8.10 | **no** | 5.229x | 18.810x | 3.598x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 4,050.1 | 5,909.3-5,909.3 | 3.43 | yes | `a100_sxm_80gb-x387-hybrid` | 656.1 | 1,025.3-1,025.3 | 3.20 | yes | 6.173x | 5.763x | 0.934x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 3,457.0 | 7,681.6-7,681.6 | 2.25 | yes | `a100_sxm_80gb-x2574-hybrid` | 661.2 | 408.4-408.4 | 8.10 | **no** | 5.229x | 18.810x | 3.598x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 4,014.6 | 729.9-729.9 | 27.50 | **no** | `a100_sxm_80gb-x387-hybrid` | 656.1 | 1,025.3-1,025.3 | 3.20 | yes | 6.119x | 0.712x | 0.116x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 3,457.0 | 7,681.6-7,681.6 | 2.25 | yes | `a100_sxm_80gb-x2574-hybrid` | 661.2 | 408.4-408.4 | 8.10 | **no** | 5.229x | 18.810x | 3.598x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 4,014.6 | 729.9-729.9 | 27.50 | **no** | `a100_sxm_80gb-x387-hybrid` | 607.7 | 929.5-929.5 | 3.27 | yes | 6.607x | 0.785x | 0.119x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 3,019.5 | 346.3-346.3 | 43.59 | **no** | `a100_sxm_80gb-x2574-hybrid` | 661.2 | 408.4-408.4 | 8.10 | **no** | 4.567x | 0.848x | 0.186x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,609.9 | 155.7-155.7 | 51.71 | **no** | `a100_sxm_80gb-x387-hybrid` | 317.3 | 496.5-496.5 | 3.20 | yes | 5.073x | 0.314x | 0.062x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,284.9 | 335.9-335.9 | 19.13 | **no** | `a100_sxm_80gb-x2574-hybrid` | 661.2 | 408.4-408.4 | 8.10 | **no** | 1.943x | 0.822x | 0.423x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 413.4 | 38.9-38.9 | 53.06 | **no** | `a100_sxm_80gb-x387-expert` | 177.6 | 195.4-195.4 | 4.54 | yes | 2.328x | 0.199x | 0.086x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 389.6 | 299.7-299.7 | 6.50 | **no** | `a100_sxm_80gb-x2574-hybrid` | 424.5 | 257.9-257.9 | 8.23 | **no** | 0.918x | 1.162x | 1.266x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 103.8 | 32.6-32.6 | 15.90 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 104.7 | 6.2-6.2 | 84.72 | **no** | `a100_sxm_80gb-x2574-expert` | 261.2 | 319.5-319.5 | 4.09 | yes | 0.401x | 0.019x | 0.048x |

**Does the ratio compress?** Of 19 class rows in this study, 12 move the ROM-versus-GPU ratio DOWN under speculation and 7 move it UP. The movement spans 0.048x to 3.598x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 9 of 20 ROM rows and 13 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 15,837.4 | 846.0-846.0 | 93.60 | **no** | `a100_sxm_80gb-x71-tensor` | 1,031.9 | 2,702.5-2,702.5 | 1.91 | yes | 15.348x | 0.313x | 0.020x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 5,514.7 | 10,137.7-10,137.7 | 2.72 | yes | `a100_sxm_80gb-x56-tensor` | 1,007.9 | 2,625.3-2,625.3 | 1.92 | yes | 5.472x | 3.862x | 0.706x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 15,837.4 | 846.0-846.0 | 93.60 | **no** | `a100_sxm_80gb-x71-tensor` | 926.2 | 1,880.4-1,880.4 | 2.46 | yes | 17.100x | 0.450x | 0.026x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 5,473.8 | 8,851.0-8,851.0 | 3.09 | yes | `a100_sxm_80gb-x112-tensor` | 961.1 | 1,942.3-1,942.3 | 2.47 | yes | 5.695x | 4.557x | 0.800x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 15,837.4 | 846.0-846.0 | 93.60 | **no** | `a100_sxm_80gb-x71-tensor` | 769.9 | 1,182.4-1,182.4 | 3.26 | yes | 20.571x | 0.715x | 0.035x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 5,467.7 | 8,847.2-8,847.2 | 3.09 | yes | `a100_sxm_80gb-x224-tensor` | 833.3 | 1,232.0-1,232.0 | 3.38 | yes | 6.561x | 7.181x | 1.095x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 15,837.4 | 846.0-846.0 | 93.60 | **no** | `a100_sxm_80gb-x71-hybrid` | 749.9 | 1,500.2-1,500.2 | 2.50 | yes | 21.118x | 0.564x | 0.027x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,455.6 | 8,839.8-8,839.8 | 3.09 | yes | `a100_sxm_80gb-x448-hybrid` | 713.5 | 1,005.0-1,005.0 | 3.55 | yes | 7.646x | 8.795x | 1.150x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 15,837.4 | 846.0-846.0 | 93.60 | **no** | `a100_sxm_80gb-x71-hybrid` | 646.9 | 1,186.6-1,186.6 | 2.73 | yes | 24.482x | 0.713x | 0.029x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,397.9 | 8,698.8-8,698.8 | 3.10 | yes | `a100_sxm_80gb-x672-hybrid` | 713.5 | 852.2-852.2 | 4.19 | yes | 7.566x | 10.208x | 1.349x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 14,829.5 | 877.6-877.6 | 84.49 | **no** | `a100_sxm_80gb-x146-hybrid` | 635.3 | 1,083.3-1,083.3 | 2.93 | yes | 23.344x | 0.810x | 0.035x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,222.7 | 8,202.5-8,202.5 | 3.18 | yes | `a100_sxm_80gb-x672-hybrid` | 713.5 | 852.2-852.2 | 4.19 | yes | 7.320x | 9.626x | 1.315x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 14,692.8 | 877.5-877.5 | 83.72 | **no** | `a100_sxm_80gb-x335-hybrid` | 645.4 | 958.3-958.3 | 3.37 | yes | 22.764x | 0.916x | 0.040x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,904.4 | 7,362.4-7,362.4 | 3.33 | yes | `a100_sxm_80gb-x672-hybrid` | 713.5 | 852.2-852.2 | 4.19 | yes | 6.874x | 8.640x | 1.257x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,947.4 | 769.3-769.3 | 38.65 | **no** | `a100_sxm_80gb-x335-hybrid` | 361.1 | 539.3-539.3 | 3.35 | yes | 16.468x | 1.426x | 0.087x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,591.1 | 4,560.0-4,560.0 | 3.94 | yes | `a100_sxm_80gb-x672-hybrid` | 508.1 | 575.3-575.3 | 4.42 | yes | 7.068x | 7.927x | 1.122x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,649.4 | 193.2-193.2 | 42.68 | **no** | `a100_sxm_80gb-x335-expert` | 287.5 | 415.9-415.9 | 3.46 | yes | 5.737x | 0.465x | 0.081x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,415.2 | 227.2-227.2 | 53.16 | **no** | `a100_sxm_80gb-x672-expert` | 360.7 | 792.4-792.4 | 2.28 | yes | 6.695x | 0.287x | 0.043x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 493.9 | 149.0-149.0 | 16.57 | **no** | `a100_sxm_80gb-x224-expert` | 117.1 | 73.0-73.0 | 8.02 | **no** | 4.217x | 2.040x | 0.484x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 623.7 | 174.5-174.5 | 17.87 | **no** | `a100_sxm_80gb-x672-expert` | 253.0 | 215.0-215.0 | 5.88 | **no** | 2.466x | 0.812x | 0.329x |

**Does the ratio compress?** Of 20 class rows in this study, 14 move the ROM-versus-GPU ratio DOWN under speculation and 6 move it UP. The movement spans 0.020x to 1.349x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 8 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 16,019.5 | 893.0-893.0 | 89.69 | **no** | `a100_sxm_80gb-x67-tensor` | 1,026.2 | 2,678.0-2,678.0 | 1.92 | yes | 15.611x | 0.333x | 0.021x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.4 | 8,881.3-8,881.3 | 3.11 | yes | `a100_sxm_80gb-x112-tensor` | 1,067.2 | 2,819.7-2,819.7 | 1.89 | yes | 5.176x | 3.150x | 0.609x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 16,019.5 | 893.0-893.0 | 89.69 | **no** | `a100_sxm_80gb-x67-tensor` | 920.4 | 1,864.2-1,864.2 | 2.47 | yes | 17.405x | 0.479x | 0.028x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.4 | 8,881.3-8,881.3 | 3.11 | yes | `a100_sxm_80gb-x112-tensor` | 961.5 | 1,942.6-1,942.6 | 2.47 | yes | 5.745x | 4.572x | 0.796x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 16,019.5 | 893.0-893.0 | 89.69 | **no** | `a100_sxm_80gb-x67-tensor` | 764.3 | 1,172.7-1,172.7 | 3.26 | yes | 20.960x | 0.761x | 0.036x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 5,517.2 | 8,877.6-8,877.6 | 3.11 | yes | `a100_sxm_80gb-x224-tensor` | 833.6 | 1,232.1-1,232.1 | 3.38 | yes | 6.619x | 7.205x | 1.089x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 16,019.5 | 893.0-893.0 | 89.69 | **no** | `a100_sxm_80gb-x67-hybrid` | 723.5 | 1,434.6-1,434.6 | 2.52 | yes | 22.141x | 0.622x | 0.028x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,504.9 | 8,870.1-8,870.1 | 3.10 | yes | `a100_sxm_80gb-x448-hybrid` | 714.9 | 1,005.6-1,005.6 | 3.55 | yes | 7.700x | 8.821x | 1.146x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 16,019.5 | 893.0-893.0 | 89.69 | **no** | `a100_sxm_80gb-x67-hybrid` | 623.3 | 1,134.0-1,134.0 | 2.75 | yes | 25.703x | 0.788x | 0.031x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,462.5 | 8,738.0-8,738.0 | 3.13 | yes | `a100_sxm_80gb-x672-hybrid` | 714.9 | 852.6-852.6 | 4.19 | yes | 7.641x | 10.249x | 1.341x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 15,680.6 | 882.2-882.2 | 88.88 | **no** | `a100_sxm_80gb-x146-hybrid` | 637.2 | 1,084.5-1,084.5 | 2.94 | yes | 24.607x | 0.813x | 0.033x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,345.0 | 8,272.4-8,272.4 | 3.23 | yes | `a100_sxm_80gb-x672-hybrid` | 714.9 | 852.6-852.6 | 4.19 | yes | 7.476x | 9.703x | 1.298x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 15,527.8 | 882.0-882.0 | 88.02 | **no** | `a100_sxm_80gb-x335-hybrid` | 647.2 | 959.1-959.1 | 3.37 | yes | 23.992x | 0.920x | 0.038x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 5,317.6 | 236.3-236.3 | 112.51 | **no** | `a100_sxm_80gb-x672-hybrid` | 714.9 | 852.6-852.6 | 4.19 | yes | 7.438x | 0.277x | 0.037x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,364.6 | 779.9-779.9 | 40.81 | **no** | `a100_sxm_80gb-x335-hybrid` | 363.4 | 540.3-540.3 | 3.36 | yes | 17.515x | 1.443x | 0.082x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 5,317.6 | 236.3-236.3 | 112.51 | **no** | `a100_sxm_80gb-x672-hybrid` | 510.3 | 575.8-575.8 | 4.43 | yes | 10.421x | 0.410x | 0.039x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,778.8 | 195.9-195.9 | 45.40 | **no** | `a100_sxm_80gb-x335-expert` | 293.3 | 431.8-431.8 | 3.40 | yes | 6.065x | 0.454x | 0.075x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 3,651.1 | 228.9-228.9 | 79.76 | **no** | `a100_sxm_80gb-x672-expert` | 365.2 | 821.1-821.1 | 2.22 | yes | 9.997x | 0.279x | 0.028x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 532.3 | 154.4-154.4 | 17.24 | **no** | `a100_sxm_80gb-x224-expert` | 121.5 | 76.0-76.0 | 8.00 | **no** | 4.380x | 2.032x | 0.464x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,134.4 | 631.7-631.7 | 8.98 | **no** | `a100_sxm_80gb-x672-expert` | 262.0 | 223.4-223.4 | 5.86 | **no** | 4.330x | 2.827x | 0.653x |

**Does the ratio compress?** Of 20 class rows in this study, 16 move the ROM-versus-GPU ratio DOWN under speculation and 4 move it UP. The movement spans 0.021x to 1.341x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 6 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x196` | 4,637.4 | 6,457.6-6,457.6 | 3.59 | yes | `a100_sxm_80gb-x193-tensor` | 682.3 | 1,467.0-1,467.0 | 2.33 | yes | 6.797x | 4.402x | 0.648x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 3,734.7 | 2,256.3-2,256.3 | 8.28 | **no** | `a100_sxm_80gb-x336-tensor` | 523.4 | 1,309.3-1,309.3 | 2.00 | yes | 7.136x | 1.723x | 0.241x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4,443.3 | 156.5-156.5 | 141.96 | **no** | `a100_sxm_80gb-x391-tensor` | 466.7 | 871.5-871.5 | 2.68 | yes | 9.520x | 0.180x | 0.019x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3,483.1 | 1,081.4-1,081.4 | 16.10 | **no** | `a100_sxm_80gb-x783-tensor` | 474.9 | 883.5-883.5 | 2.69 | yes | 7.334x | 1.224x | 0.167x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4,443.3 | 156.5-156.5 | 141.96 | **no** | `a100_sxm_80gb-x391-tensor` | 381.1 | 522.1-522.1 | 3.65 | yes | 11.659x | 0.300x | 0.026x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3,483.1 | 1,081.4-1,081.4 | 16.10 | **no** | `a100_sxm_80gb-x783-tensor` | 388.9 | 527.8-527.8 | 3.68 | yes | 8.957x | 2.049x | 0.229x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4,443.3 | 156.5-156.5 | 141.96 | **no** | `a100_sxm_80gb-x391-tensor` | 279.1 | 291.2-291.2 | 4.79 | yes | 15.923x | 0.537x | 0.034x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3,483.1 | 1,081.4-1,081.4 | 16.10 | **no** | `a100_sxm_80gb-x783-tensor` | 285.6 | 293.1-293.1 | 4.87 | yes | 12.196x | 3.689x | 0.302x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4,443.3 | 156.5-156.5 | 141.96 | **no** | `a100_sxm_80gb-x391-hybrid` | 262.2 | 377.8-377.8 | 3.47 | yes | 16.945x | 0.414x | 0.024x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3,426.3 | 1,079.1-1,079.1 | 15.88 | **no** | `a100_sxm_80gb-x783-hybrid` | 260.4 | 289.1-289.1 | 4.50 | yes | 13.160x | 3.732x | 0.284x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4,443.3 | 156.5-156.5 | 141.96 | **no** | `a100_sxm_80gb-x391-hybrid` | 262.2 | 377.8-377.8 | 3.47 | yes | 16.945x | 0.414x | 0.024x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3,030.6 | 1,061.3-1,061.3 | 14.28 | **no** | `a100_sxm_80gb-x783-hybrid` | 260.4 | 289.1-289.1 | 4.50 | yes | 11.640x | 3.670x | 0.315x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4,443.3 | 156.5-156.5 | 141.96 | **no** | `a100_sxm_80gb-x391-hybrid` | 242.0 | 339.9-339.9 | 3.56 | yes | 18.364x | 0.460x | 0.025x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 2,462.0 | 1,027.2-1,027.2 | 11.98 | **no** | `a100_sxm_80gb-x783-hybrid` | 260.4 | 289.1-289.1 | 4.50 | yes | 9.456x | 3.553x | 0.376x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,849.6 | 145.0-145.0 | 63.76 | **no** | `a100_sxm_80gb-x391-hybrid` | 123.5 | 179.0-179.0 | 3.45 | yes | 14.978x | 0.810x | 0.054x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,158.1 | 861.4-861.4 | 6.72 | **no** | `a100_sxm_80gb-x783-hybrid` | 181.3 | 197.8-197.8 | 4.58 | yes | 6.389x | 4.356x | 0.682x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 484.6 | 36.3-36.3 | 66.72 | **no** | `a100_sxm_80gb-x391-expert` | 87.3 | 147.5-147.5 | 2.96 | yes | 5.551x | 0.246x | 0.044x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 406.2 | 20.1-20.1 | 100.98 | **no** | `a100_sxm_80gb-x783-expert` | 111.7 | 287.8-287.8 | 1.94 | yes | 3.637x | 0.070x | 0.019x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 122.0 | 26.8-26.8 | 22.79 | **no** | `a100_sxm_80gb-x391-expert` | 55.6 | 37.6-37.6 | 7.39 | **no** | 2.194x | 0.711x | 0.324x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 102.3 | 19.0-19.0 | 26.97 | **no** | `a100_sxm_80gb-x783-expert` | 81.9 | 74.9-74.9 | 5.47 | **no** | 1.249x | 0.253x | 0.203x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.019x to 0.682x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 1 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 5,167.5 | 165.8-165.8 | 155.88 | **no** | `a100_sxm_80gb-x371-tensor` | 525.2 | 1,313.9-1,313.9 | 2.00 | yes | 9.838x | 0.126x | 0.013x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3,782.8 | 2,278.2-2,278.2 | 8.30 | **no** | `a100_sxm_80gb-x336-tensor` | 523.5 | 1,309.5-1,309.5 | 2.00 | yes | 7.226x | 1.740x | 0.241x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 5,167.5 | 165.8-165.8 | 155.88 | **no** | `a100_sxm_80gb-x371-tensor` | 466.1 | 870.2-870.2 | 2.68 | yes | 11.087x | 0.190x | 0.017x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3,782.8 | 2,278.2-2,278.2 | 8.30 | **no** | `a100_sxm_80gb-x336-tensor` | 464.4 | 867.5-867.5 | 2.68 | yes | 8.145x | 2.626x | 0.322x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 5,167.5 | 165.8-165.8 | 155.88 | **no** | `a100_sxm_80gb-x371-tensor` | 380.6 | 521.6-521.6 | 3.65 | yes | 13.578x | 0.318x | 0.023x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3,782.8 | 2,278.2-2,278.2 | 8.30 | **no** | `a100_sxm_80gb-x336-tensor` | 379.0 | 520.7-520.7 | 3.64 | yes | 9.981x | 4.375x | 0.438x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 5,167.5 | 165.8-165.8 | 155.88 | **no** | `a100_sxm_80gb-x371-tensor` | 278.7 | 291.0-291.0 | 4.79 | yes | 18.541x | 0.570x | 0.031x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,782.5 | 2,252.7-2,252.7 | 8.40 | **no** | `a100_sxm_80gb-x448-tensor` | 281.0 | 291.9-291.9 | 4.81 | yes | 13.461x | 7.719x | 0.573x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 5,167.5 | 165.8-165.8 | 155.88 | **no** | `a100_sxm_80gb-x371-hybrid` | 262.2 | 381.7-381.7 | 3.43 | yes | 19.708x | 0.434x | 0.022x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,724.1 | 2,222.2-2,222.2 | 8.38 | **no** | `a100_sxm_80gb-x672-hybrid` | 262.5 | 309.0-309.0 | 4.25 | yes | 14.187x | 7.191x | 0.507x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 5,167.5 | 165.8-165.8 | 155.88 | **no** | `a100_sxm_80gb-x371-hybrid` | 262.2 | 381.7-381.7 | 3.43 | yes | 19.708x | 0.434x | 0.022x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,527.5 | 2,109.9-2,109.9 | 8.36 | **no** | `a100_sxm_80gb-x672-hybrid` | 262.5 | 309.0-309.0 | 4.25 | yes | 13.438x | 6.828x | 0.508x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 5,167.5 | 165.8-165.8 | 155.88 | **no** | `a100_sxm_80gb-x371-hybrid` | 239.0 | 337.9-337.9 | 3.54 | yes | 21.623x | 0.491x | 0.023x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,315.7 | 1,177.1-1,177.1 | 14.08 | **no** | `a100_sxm_80gb-x672-hybrid` | 262.5 | 309.0-309.0 | 4.25 | yes | 12.632x | 3.809x | 0.302x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 2,292.1 | 148.6-148.6 | 77.11 | **no** | `a100_sxm_80gb-x391-hybrid` | 125.7 | 179.9-179.9 | 3.49 | yes | 18.232x | 0.826x | 0.045x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,379.9 | 968.3-968.3 | 12.29 | **no** | `a100_sxm_80gb-x672-hybrid` | 170.3 | 196.4-196.4 | 4.34 | yes | 13.975x | 4.931x | 0.353x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 607.5 | 37.2-37.2 | 81.62 | **no** | `a100_sxm_80gb-x391-expert` | 91.9 | 169.7-169.7 | 2.71 | yes | 6.610x | 0.219x | 0.033x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,086.9 | 566.4-566.4 | 9.59 | **no** | `a100_sxm_80gb-x672-expert` | 110.0 | 285.8-285.8 | 1.92 | yes | 9.881x | 1.982x | 0.201x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 153.2 | 28.8-28.8 | 26.57 | **no** | `a100_sxm_80gb-x391-expert` | 63.8 | 43.4-43.4 | 7.34 | **no** | 2.403x | 0.664x | 0.276x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 342.5 | 212.9-212.9 | 8.04 | **no** | `a100_sxm_80gb-x672-expert` | 84.2 | 74.4-74.4 | 5.66 | **no** | 4.068x | 2.863x | 0.704x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.013x to 0.704x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 5,241.4 | 169.0-169.0 | 155.11 | **no** | `a100_sxm_80gb-x391-tensor` | 526.1 | 1,316.3-1,316.3 | 2.00 | yes | 9.962x | 0.128x | 0.013x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3,789.0 | 2,281.8-2,281.8 | 8.30 | **no** | `a100_sxm_80gb-x336-tensor` | 523.6 | 1,309.5-1,309.5 | 2.00 | yes | 7.237x | 1.742x | 0.241x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 5,241.4 | 169.0-169.0 | 155.11 | **no** | `a100_sxm_80gb-x391-tensor` | 467.0 | 871.7-871.7 | 2.68 | yes | 11.223x | 0.194x | 0.017x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3,789.0 | 2,281.8-2,281.8 | 8.30 | **no** | `a100_sxm_80gb-x336-tensor` | 464.4 | 867.5-867.5 | 2.68 | yes | 8.158x | 2.630x | 0.322x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 5,241.4 | 169.0-169.0 | 155.11 | **no** | `a100_sxm_80gb-x391-tensor` | 381.5 | 522.3-522.3 | 3.65 | yes | 13.740x | 0.324x | 0.024x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3,789.0 | 2,281.8-2,281.8 | 8.30 | **no** | `a100_sxm_80gb-x336-tensor` | 379.1 | 520.7-520.7 | 3.64 | yes | 9.996x | 4.382x | 0.438x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 5,241.4 | 169.0-169.0 | 155.11 | **no** | `a100_sxm_80gb-x391-tensor` | 279.5 | 291.3-291.3 | 4.80 | yes | 18.756x | 0.580x | 0.031x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,788.6 | 2,256.2-2,256.2 | 8.40 | **no** | `a100_sxm_80gb-x448-tensor` | 281.0 | 291.9-291.9 | 4.81 | yes | 13.480x | 7.730x | 0.573x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 5,241.4 | 169.0-169.0 | 155.11 | **no** | `a100_sxm_80gb-x391-hybrid` | 264.4 | 378.7-378.7 | 3.49 | yes | 19.823x | 0.446x | 0.023x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,731.9 | 2,226.7-2,226.7 | 8.38 | **no** | `a100_sxm_80gb-x672-hybrid` | 262.8 | 309.1-309.1 | 4.25 | yes | 14.202x | 7.204x | 0.507x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 5,241.4 | 169.0-169.0 | 155.11 | **no** | `a100_sxm_80gb-x391-hybrid` | 264.4 | 378.7-378.7 | 3.49 | yes | 19.823x | 0.446x | 0.023x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,541.5 | 2,118.0-2,118.0 | 8.36 | **no** | `a100_sxm_80gb-x672-hybrid` | 262.8 | 309.1-309.1 | 4.25 | yes | 13.478x | 6.852x | 0.508x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 5,241.4 | 169.0-169.0 | 155.11 | **no** | `a100_sxm_80gb-x391-hybrid` | 244.4 | 340.9-340.9 | 3.59 | yes | 21.447x | 0.496x | 0.023x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,315.7 | 1,180.3-1,180.3 | 14.05 | **no** | `a100_sxm_80gb-x672-hybrid` | 262.8 | 309.1-309.1 | 4.25 | yes | 12.618x | 3.819x | 0.303x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 2,375.6 | 149.2-149.2 | 79.63 | **no** | `a100_sxm_80gb-x391-hybrid` | 126.0 | 180.0-180.0 | 3.50 | yes | 18.847x | 0.829x | 0.044x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,497.1 | 977.0-977.0 | 12.78 | **no** | `a100_sxm_80gb-x672-hybrid` | 170.7 | 196.4-196.4 | 4.34 | yes | 14.632x | 4.973x | 0.340x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 631.0 | 37.4-37.4 | 84.47 | **no** | `a100_sxm_80gb-x391-expert` | 92.6 | 173.6-173.6 | 2.67 | yes | 6.813x | 0.215x | 0.032x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,188.8 | 578.4-578.4 | 10.28 | **no** | `a100_sxm_80gb-x672-expert` | 110.6 | 292.1-292.1 | 1.89 | yes | 10.749x | 1.980x | 0.184x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 159.2 | 29.2-29.2 | 27.30 | **no** | `a100_sxm_80gb-x391-expert` | 65.2 | 44.5-44.5 | 7.33 | **no** | 2.444x | 0.656x | 0.269x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 384.0 | 219.8-219.8 | 8.74 | **no** | `a100_sxm_80gb-x672-expert` | 85.6 | 76.1-76.1 | 5.63 | **no** | 4.485x | 2.889x | 0.644x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.013x to 0.644x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 28,190.4 | not applicable | -- | -- | `b200_sxm-x8-tensor` | 2,013.6 | not applicable | -- | -- | 14.000x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | not applicable | -- | -- | `b200_sxm-x29-nvl72-tensor` | 3,724.5 | not applicable | -- | -- | 1.736x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-tensor-x62-romfill` | 14,725.8 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 3,730.3 | not applicable | -- | -- | 3.948x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 5,536.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 4,353.8 | not applicable | -- | -- | 1.272x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-tensor-x62-romfill` | 12,494.2 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 3,526.8 | not applicable | -- | -- | 3.543x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 5,536.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 4,319.3 | not applicable | -- | -- | 1.282x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-tensor-x62` | 9,588.1 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 3,180.0 | not applicable | -- | -- | 3.015x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,530.5 | not applicable | -- | -- | `b200_sxm-x231-nvl72-hybrid` | 4,211.0 | not applicable | -- | -- | 1.313x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9,373.0 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 3,944.5 | not applicable | -- | -- | 2.376x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,187.1 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 4,196.5 | not applicable | -- | -- | 1.236x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9,373.0 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 3,535.5 | not applicable | -- | -- | 2.651x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,183.1 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 3,918.6 | not applicable | -- | -- | 1.068x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9,373.0 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,928.2 | not applicable | -- | -- | 3.201x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,015.8 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 3,460.3 | not applicable | -- | -- | 0.872x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,185.2 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,442.0 | not applicable | -- | -- | 2.209x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,127.6 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 2,033.5 | not applicable | -- | -- | 0.555x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 803.3 | not applicable | -- | -- | `b200_sxm-x173-hybrid` | 536.8 | not applicable | -- | -- | 1.497x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 336.6 | not applicable | -- | -- | `b200_sxm-x347-hybrid` | 787.1 | not applicable | -- | -- | 0.428x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 201.3 | not applicable | -- | -- | `b200_sxm-x173-hybrid` | 169.7 | not applicable | -- | -- | 1.187x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 84.4 | not applicable | -- | -- | `b200_sxm-x347-hybrid` | 290.6 | not applicable | -- | -- | 0.290x | -- | -- |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x59` | 18,118.9 | 1,014.3-1,014.3 | 89.32 | **no** | `b200_sxm-x30-nvl72-tensor` | 3,566.3 | 11,493.3-11,493.3 | 1.55 | yes | 5.081x | 0.088x | 0.017x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | 6,168.1 | 296.0-296.0 | 104.19 | **no** | `b200_sxm-x29-nvl72-tensor` | 3,540.5 | 11,332.1-11,332.1 | 1.56 | yes | 1.742x | 0.026x | 0.015x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 17,197.9 | 950.8-950.8 | 90.44 | **no** | `b200_sxm-x32-nvl72-tensor` | 3,369.9 | 9,769.7-9,769.7 | 1.72 | yes | 5.103x | 0.097x | 0.019x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 5,328.6 | 10,625.4-10,625.4 | 2.51 | yes | `b200_sxm-x202-nvl72-hybrid` | 3,969.3 | 13,998.0-13,998.0 | 1.42 | yes | 1.342x | 0.759x | 0.565x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 17,197.9 | 950.8-950.8 | 90.44 | **no** | `b200_sxm-x32-nvl72-tensor` | 2,978.7 | 7,501.7-7,501.7 | 1.99 | yes | 5.774x | 0.127x | 0.022x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 5,328.6 | 10,625.4-10,625.4 | 2.51 | yes | `b200_sxm-x202-nvl72-hybrid` | 3,911.6 | 13,239.5-13,239.5 | 1.48 | yes | 1.362x | 0.803x | 0.589x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 17,197.9 | 950.8-950.8 | 90.44 | **no** | `b200_sxm-x32-nvl72-tensor` | 2,442.8 | 5,545.6-5,545.6 | 2.20 | yes | 7.040x | 0.171x | 0.024x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,325.7 | 10,622.7-10,622.7 | 2.51 | yes | `b200_sxm-x231-nvl72-hybrid` | 3,687.7 | 11,166.2-11,166.2 | 1.65 | yes | 1.444x | 0.951x | 0.659x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 17,197.9 | 950.8-950.8 | 90.44 | **no** | `b200_sxm-x32-nvl72-tensor` | 1,847.5 | 4,114.3-4,114.3 | 2.25 | yes | 9.309x | 0.231x | 0.025x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,229.6 | 10,403.5-10,403.5 | 2.51 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,573.1 | 9,886.0-9,886.0 | 1.81 | yes | 1.464x | 1.052x | 0.719x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 13,849.4 | 1,173.8-1,173.8 | 58.99 | **no** | `b200_sxm-x86-nvl72-hybrid` | 2,112.4 | 4,714.6-4,714.6 | 2.24 | yes | 6.556x | 0.249x | 0.038x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,916.6 | 9,645.4-9,645.4 | 2.55 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,186.7 | 7,804.9-7,804.9 | 2.04 | yes | 1.543x | 1.236x | 0.801x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 13,829.4 | 1,173.8-1,173.8 | 58.91 | **no** | `b200_sxm-x173-nvl72-hybrid` | 2,107.3 | 4,433.7-4,433.7 | 2.38 | yes | 6.563x | 0.265x | 0.040x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,390.9 | 8,418.6-8,418.6 | 2.61 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,653.0 | 5,662.5-5,662.5 | 2.34 | yes | 1.655x | 1.487x | 0.898x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,526.7 | 974.8-974.8 | 28.35 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,131.8 | 1,825.1-1,825.1 | 3.10 | yes | 4.883x | 0.534x | 0.109x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 2,675.0 | 1,209.4-1,209.4 | 11.06 | **no** | `b200_sxm-x347-nvl72-hybrid` | 1,509.3 | 2,491.5-2,491.5 | 3.03 | yes | 1.772x | 0.485x | 0.274x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,521.0 | 245.1-245.1 | 31.02 | **no** | `b200_sxm-x173-nvl72-hybrid` | 546.5 | 555.3-555.3 | 4.92 | yes | 2.783x | 0.441x | 0.159x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,257.0 | 299.6-299.6 | 20.98 | **no** | `b200_sxm-x347-nvl72-hybrid` | 756.4 | 823.6-823.6 | 4.59 | yes | 1.662x | 0.364x | 0.219x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 464.4 | 139.8-139.8 | 16.61 | **no** | `b200_sxm-x173-expert` | 217.4 | 200.0-200.0 | 5.43 | **no** | 2.136x | 0.699x | 0.327x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 319.6 | 209.2-209.2 | 7.64 | **no** | `b200_sxm-x347-expert` | 371.8 | 395.6-395.6 | 4.70 | yes | 0.859x | 0.529x | 0.615x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x184` | 5,063.9 | 7,949.6-7,949.6 | 3.19 | yes | `b200_sxm-x94-nvl72-hybrid` | 2,193.2 | 6,367.7-6,367.7 | 1.72 | yes | 2.309x | 1.248x | 0.541x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 3,736.6 | 2,251.3-2,251.3 | 8.30 | **no** | `b200_sxm-x173-nvl72-hybrid` | 2,310.3 | 6,837.5-6,837.5 | 1.69 | yes | 1.617x | 0.329x | 0.204x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 4,226.3 | 154.6-154.6 | 136.71 | **no** | `b200_sxm-x203-nvl72-hybrid` | 2,402.2 | 7,264.1-7,264.1 | 1.65 | yes | 1.759x | 0.021x | 0.012x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3,119.7 | 2,816.0-2,816.0 | 5.54 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 2,230.8 | 4,700.9-4,700.9 | 2.37 | yes | 1.398x | 0.599x | 0.428x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 4,226.3 | 154.6-154.6 | 136.71 | **no** | `b200_sxm-x203-nvl72-hybrid` | 2,327.0 | 6,648.2-6,648.2 | 1.75 | yes | 1.816x | 0.023x | 0.013x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3,119.7 | 2,816.0-2,816.0 | 5.54 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 2,230.8 | 4,700.9-4,700.9 | 2.37 | yes | 1.398x | 0.599x | 0.428x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 4,226.3 | 154.6-154.6 | 136.71 | **no** | `b200_sxm-x203-nvl72-hybrid` | 2,070.3 | 5,147.9-5,147.9 | 2.01 | yes | 2.041x | 0.030x | 0.015x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3,119.7 | 2,816.0-2,816.0 | 5.54 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 2,230.8 | 4,700.9-4,700.9 | 2.37 | yes | 1.398x | 0.599x | 0.428x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 4,226.3 | 154.6-154.6 | 136.71 | **no** | `b200_sxm-x203-nvl72-hybrid` | 1,702.9 | 3,762.4-3,762.4 | 2.26 | yes | 2.482x | 0.041x | 0.017x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3,119.7 | 2,816.0-2,816.0 | 5.54 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 2,230.8 | 4,700.9-4,700.9 | 2.37 | yes | 1.398x | 0.599x | 0.428x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 4,226.3 | 154.6-154.6 | 136.71 | **no** | `b200_sxm-x203-nvl72-hybrid` | 1,271.2 | 2,520.3-2,520.3 | 2.52 | yes | 3.325x | 0.061x | 0.018x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3,119.7 | 2,816.0-2,816.0 | 5.54 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 2,093.3 | 3,846.1-3,846.1 | 2.72 | yes | 1.490x | 0.732x | 0.491x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 4,226.3 | 154.6-154.6 | 136.71 | **no** | `b200_sxm-x203-nvl72-hybrid` | 867.4 | 1,674.4-1,674.4 | 2.59 | yes | 4.873x | 0.092x | 0.019x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2,911.1 | 2,726.3-2,726.3 | 5.34 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 1,820.3 | 3,027.1-3,027.1 | 3.01 | yes | 1.599x | 0.901x | 0.563x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,769.6 | 143.0-143.0 | 61.90 | **no** | `b200_sxm-x203-nvl72-hybrid` | 366.2 | 682.2-682.2 | 2.68 | yes | 4.832x | 0.210x | 0.043x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,658.7 | 331.9-331.9 | 24.99 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 1,046.7 | 1,543.0-1,543.0 | 3.39 | yes | 1.585x | 0.215x | 0.136x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 462.6 | 35.9-35.9 | 64.49 | **no** | `b200_sxm-x203-nvl72-hybrid` | 163.4 | 216.0-216.0 | 3.78 | yes | 2.831x | 0.166x | 0.059x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 609.6 | 307.8-307.8 | 9.90 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 441.5 | 632.9-632.9 | 3.49 | yes | 1.381x | 0.486x | 0.352x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 116.5 | 26.2-26.2 | 22.22 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 180.2 | 6.1-6.1 | 148.33 | **no** | `b200_sxm-x1358-expert` | 254.4 | 516.4-516.4 | 2.46 | yes | 0.708x | 0.012x | 0.017x |

**Does the ratio compress?** Of 39 class rows in this study, 39 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.012x to 0.898x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 7 of 40 ROM rows and 38 of 40 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 25,281.1 | not applicable | -- | -- | `a100_sxm_80gb-x16-tensor` | 758.6 | not applicable | -- | -- | 33.326x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 1,109.0 | not applicable | -- | -- | 5.829x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x87-romfill` | 10,992.1 | not applicable | -- | -- | `a100_sxm_80gb-x86-tensor` | 1,084.9 | not applicable | -- | -- | 10.132x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x8-romfill` | 5,028.2 | not applicable | -- | -- | `a100_sxm_80gb-x448-tensor` | 889.3 | not applicable | -- | -- | 5.654x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x87-romfill` | 9,063.7 | not applicable | -- | -- | `a100_sxm_80gb-x86-tensor` | 927.9 | not applicable | -- | -- | 9.768x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x8` | 4,531.9 | not applicable | -- | -- | `a100_sxm_80gb-x448-tensor` | 783.0 | not applicable | -- | -- | 5.788x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x138` | 7,134.8 | not applicable | -- | -- | `a100_sxm_80gb-x136-tensor` | 744.2 | not applicable | -- | -- | 9.588x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4,325.6 | not applicable | -- | -- | `a100_sxm_80gb-x448-tensor` | 632.0 | not applicable | -- | -- | 6.845x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x227` | 5,223.1 | not applicable | -- | -- | `a100_sxm_80gb-x224-hybrid` | 597.8 | not applicable | -- | -- | 8.737x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,846.9 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 591.2 | not applicable | -- | -- | 6.507x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,125.0 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 592.8 | not applicable | -- | -- | 8.645x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,678.3 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 591.2 | not applicable | -- | -- | 4.530x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,125.0 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 561.3 | not applicable | -- | -- | 9.131x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,666.0 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 591.2 | not applicable | -- | -- | 2.818x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,773.0 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 445.0 | not applicable | -- | -- | 3.984x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 509.8 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 522.8 | not applicable | -- | -- | 0.975x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 452.2 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 236.5 | not applicable | -- | -- | 1.912x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 137.6 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 344.7 | not applicable | -- | -- | 0.399x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 113.4 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 82.3 | not applicable | -- | -- | 1.378x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 34.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 145.9 | not applicable | -- | -- | 0.236x | -- | -- |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x83` | 13,876.3 | 724.8-724.8 | 95.73 | **no** | `a100_sxm_80gb-x82-tensor` | 1,041.9 | 2,735.5-2,735.5 | 1.90 | yes | 13.318x | 0.265x | 0.020x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 5,467.3 | 8,680.6-8,680.6 | 3.15 | yes | `a100_sxm_80gb-x112-tensor` | 1,065.4 | 2,817.2-2,817.2 | 1.89 | yes | 5.131x | 3.081x | 0.600x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 13,172.6 | 691.1-691.1 | 95.31 | **no** | `a100_sxm_80gb-x87-tensor` | 940.3 | 1,908.7-1,908.7 | 2.46 | yes | 14.009x | 0.362x | 0.026x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10-romfill` | 4,970.0 | 8,635.5-8,635.5 | 2.88 | yes | `a100_sxm_80gb-x560-tensor` | 748.4 | 1,761.4-1,761.4 | 2.12 | yes | 6.641x | 4.903x | 0.738x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 13,172.6 | 691.1-691.1 | 95.31 | **no** | `a100_sxm_80gb-x87-tensor` | 781.7 | 1,195.0-1,195.0 | 3.27 | yes | 16.851x | 0.578x | 0.034x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10-romfill` | 4,970.0 | 8,635.5-8,635.5 | 2.88 | yes | `a100_sxm_80gb-x560-hybrid` | 703.9 | 917.1-917.1 | 3.84 | yes | 7.060x | 9.416x | 1.334x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 13,172.6 | 691.1-691.1 | 95.31 | **no** | `a100_sxm_80gb-x87-hybrid` | 737.9 | 1,473.8-1,473.8 | 2.50 | yes | 17.851x | 0.469x | 0.026x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10-romfill` | 4,970.0 | 8,635.5-8,635.5 | 2.88 | yes | `a100_sxm_80gb-x560-hybrid` | 703.9 | 917.1-917.1 | 3.84 | yes | 7.060x | 9.416x | 1.334x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 13,172.6 | 691.1-691.1 | 95.31 | **no** | `a100_sxm_80gb-x87-hybrid` | 671.8 | 1,258.3-1,258.3 | 2.67 | yes | 19.607x | 0.549x | 0.028x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,787.7 | 8,441.4-8,441.4 | 2.84 | yes | `a100_sxm_80gb-x672-hybrid` | 703.9 | 849.4-849.4 | 4.14 | yes | 6.801x | 9.938x | 1.461x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x99` | 11,363.0 | 606.1-606.1 | 93.73 | **no** | `a100_sxm_80gb-x98-hybrid` | 540.9 | 957.6-957.6 | 2.82 | yes | 21.006x | 0.633x | 0.030x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,189.5 | 1,273.0-1,273.0 | 16.46 | **no** | `a100_sxm_80gb-x672-hybrid` | 703.9 | 849.4-849.4 | 4.14 | yes | 5.952x | 1.499x | 0.252x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 10,757.0 | 847.8-847.8 | 63.44 | **no** | `a100_sxm_80gb-x312-hybrid` | 624.0 | 950.2-950.2 | 3.28 | yes | 17.240x | 0.892x | 0.052x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,351.8 | 1,253.8-1,253.8 | 13.37 | **no** | `a100_sxm_80gb-x672-hybrid` | 703.9 | 849.4-849.4 | 4.14 | yes | 4.762x | 1.476x | 0.310x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,112.9 | 704.3-704.3 | 29.20 | **no** | `a100_sxm_80gb-x335-hybrid` | 346.6 | 532.7-532.7 | 3.25 | yes | 11.867x | 1.322x | 0.111x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,523.8 | 1,149.9-1,149.9 | 6.63 | **no** | `a100_sxm_80gb-x672-hybrid` | 493.5 | 571.4-571.4 | 4.32 | yes | 3.088x | 2.012x | 0.652x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x237` | 1,164.2 | 207.4-207.4 | 28.07 | **no** | `a100_sxm_80gb-x234-expert` | 212.1 | 235.6-235.6 | 4.50 | yes | 5.488x | 0.880x | 0.160x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 519.4 | 216.2-216.2 | 12.02 | **no** | `a100_sxm_80gb-x672-expert` | 332.9 | 639.8-639.8 | 2.60 | yes | 1.560x | 0.338x | 0.216x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 423.3 | 121.5-121.5 | 17.42 | **no** | `a100_sxm_80gb-x335-expert` | 129.6 | 85.9-85.9 | 7.54 | **no** | 3.267x | 1.414x | 0.433x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 130.8 | 23.1-23.1 | 28.28 | **no** | `a100_sxm_80gb-x672-expert` | 204.9 | 170.8-170.8 | 6.00 | **no** | 0.638x | 0.135x | 0.212x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x237` | 4,414.2 | 7,408.2-7,408.2 | 2.98 | yes | `a100_sxm_80gb-x234-tensor` | 689.9 | 1,485.0-1,485.0 | 2.32 | yes | 6.398x | 4.989x | 0.780x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 3,649.0 | 1,570.1-1,570.1 | 11.62 | **no** | `a100_sxm_80gb-x504-tensor` | 529.0 | 1,325.1-1,325.1 | 2.00 | yes | 6.898x | 1.185x | 0.172x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 2,415.3 | 242.2-242.2 | 49.87 | **no** | `a100_sxm_80gb-x3694-tensor` | 481.5 | 894.7-894.7 | 2.69 | yes | 5.017x | 0.271x | 0.054x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 2,415.3 | 242.2-242.2 | 49.87 | **no** | `a100_sxm_80gb-x3694-tensor` | 395.1 | 532.2-532.2 | 3.71 | yes | 6.114x | 0.455x | 0.074x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 2,415.3 | 242.2-242.2 | 49.87 | **no** | `a100_sxm_80gb-x3694-tensor` | 290.8 | 294.7-294.7 | 4.93 | yes | 8.307x | 0.822x | 0.099x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 2,415.3 | 242.2-242.2 | 49.87 | **no** | `a100_sxm_80gb-x3694-hybrid` | 251.9 | 120.0-120.0 | 10.50 | **no** | 9.589x | 2.019x | 0.211x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 2,415.3 | 242.2-242.2 | 49.87 | **no** | `a100_sxm_80gb-x3694-hybrid` | 251.9 | 120.0-120.0 | 10.50 | **no** | 9.589x | 2.019x | 0.211x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 2,415.3 | 242.2-242.2 | 49.87 | **no** | `a100_sxm_80gb-x3694-hybrid` | 251.9 | 120.0-120.0 | 10.50 | **no** | 9.589x | 2.019x | 0.211x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,160.3 | 237.0-237.0 | 24.48 | **no** | `a100_sxm_80gb-x3694-hybrid` | 251.9 | 120.0-120.0 | 10.50 | **no** | 4.606x | 1.976x | 0.429x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 374.2 | 218.1-218.1 | 8.58 | **no** | `a100_sxm_80gb-x3694-hybrid` | 185.3 | 84.8-84.8 | 10.93 | **no** | 2.020x | 2.573x | 1.274x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 103.4 | 4.3-4.3 | 119.61 | **no** | `a100_sxm_80gb-x3694-expert` | 121.8 | 209.6-209.6 | 2.91 | yes | 0.849x | 0.021x | 0.024x |

**Does the ratio compress?** Of 31 class rows in this study, 27 move the ROM-versus-GPU ratio DOWN under speculation and 4 move it UP. The movement spans 0.020x to 1.461x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 6 of 31 ROM rows and 24 of 31 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 40,683.1 | not applicable | -- | -- | `b200_sxm-x2-tensor` | 1,712.2 | not applicable | -- | -- | 23.761x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | not applicable | -- | -- | `b200_sxm-x29-nvl72-tensor` | 4,776.9 | not applicable | -- | -- | 1.353x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-tensor-x62-romfill` | 14,725.8 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 4,662.6 | not applicable | -- | -- | 3.158x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 5,536.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 5,001.5 | not applicable | -- | -- | 1.107x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-tensor-x62-romfill` | 12,494.2 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 4,349.1 | not applicable | -- | -- | 2.873x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 5,536.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 4,956.1 | not applicable | -- | -- | 1.117x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x196-romfill` | 9,944.2 | not applicable | -- | -- | `b200_sxm-x100-nvl72-hybrid` | 4,600.2 | not applicable | -- | -- | 2.162x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,530.5 | not applicable | -- | -- | `b200_sxm-x231-nvl72-hybrid` | 4,813.0 | not applicable | -- | -- | 1.149x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x196-romfill` | 9,944.2 | not applicable | -- | -- | `b200_sxm-x100-nvl72-hybrid` | 4,154.4 | not applicable | -- | -- | 2.394x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 5,187.1 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 4,682.1 | not applicable | -- | -- | 1.108x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x196-romfill` | 9,944.2 | not applicable | -- | -- | `b200_sxm-x100-nvl72-hybrid` | 3,480.0 | not applicable | -- | -- | 2.858x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 4,183.1 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 4,338.9 | not applicable | -- | -- | 0.964x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 9,944.2 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 3,207.6 | not applicable | -- | -- | 3.100x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,015.8 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 3,784.0 | not applicable | -- | -- | 0.797x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3,323.3 | not applicable | -- | -- | `b200_sxm-x173-hybrid` | 1,569.6 | not applicable | -- | -- | 2.117x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 1,127.6 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 2,141.1 | not applicable | -- | -- | 0.527x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 832.8 | not applicable | -- | -- | `b200_sxm-x173-hybrid` | 607.9 | not applicable | -- | -- | 1.370x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 336.6 | not applicable | -- | -- | `b200_sxm-x347-hybrid` | 949.7 | not applicable | -- | -- | 0.354x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x340-romfill` | 208.4 | not applicable | -- | -- | `b200_sxm-x173-pipeline` | 188.7 | not applicable | -- | -- | 1.104x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 84.4 | not applicable | -- | -- | `b200_sxm-x347-pipeline` | 336.8 | not applicable | -- | -- | 0.251x | -- | -- |

### `n6_vs_a100-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-hw-hybrid-x8-romfill` | 33,480.9 | not applicable | -- | -- | `a100_sxm_80gb-x8-tensor` | 1,302.6 | not applicable | -- | -- | 25.704x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 1,279.6 | not applicable | -- | -- | 5.052x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-tensor-x87-romfill` | 10,992.1 | not applicable | -- | -- | `a100_sxm_80gb-x86-hybrid` | 1,249.2 | not applicable | -- | -- | 8.799x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-tensor-x8-romfill` | 5,028.2 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 1,176.1 | not applicable | -- | -- | 4.275x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-tensor-x87-romfill` | 9,063.7 | not applicable | -- | -- | `a100_sxm_80gb-x86-hybrid` | 1,249.2 | not applicable | -- | -- | 7.255x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-tensor-x8` | 4,531.9 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 1,176.1 | not applicable | -- | -- | 3.853x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-tensor-x138` | 7,134.8 | not applicable | -- | -- | `a100_sxm_80gb-x136-hybrid` | 1,241.6 | not applicable | -- | -- | 5.747x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 4,325.6 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 1,176.1 | not applicable | -- | -- | 3.678x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-tensor-x227` | 5,223.1 | not applicable | -- | -- | `a100_sxm_80gb-x224-hybrid` | 1,202.8 | not applicable | -- | -- | 4.342x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,846.9 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 1,176.1 | not applicable | -- | -- | 3.271x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 5,125.0 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 1,182.7 | not applicable | -- | -- | 4.333x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 2,678.3 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 1,176.1 | not applicable | -- | -- | 2.277x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 5,125.0 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 1,063.5 | not applicable | -- | -- | 4.819x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12` | 1,666.0 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 1,176.1 | not applicable | -- | -- | 1.417x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 1,773.0 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 712.5 | not applicable | -- | -- | 2.488x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12` | 509.8 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 933.3 | not applicable | -- | -- | 0.546x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 452.2 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 295.5 | not applicable | -- | -- | 1.531x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 137.6 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 485.5 | not applicable | -- | -- | 0.283x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 113.4 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 88.4 | not applicable | -- | -- | 1.282x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12` | 34.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 166.3 | not applicable | -- | -- | 0.207x | -- | -- |

## Where the drafter lives on a ROM machine

The locality rule -- `stored/peak` is a technology constant -- is the load-bearing assumption of the whole ROM verdict. A pass that reads only the drafter's region uses only that region's read ports and takes exactly as long as sweeping the entire array. Two placements are therefore priced side by side, and the second is an architectural proposal this study **has not costed in silicon area**.

The same rule is what makes a SEQUENTIAL draft step expensive here. A per-position operation that moves only a small table is nearly free on a global-bandwidth store and costs a full array sweep on this one, so a drafter with `gamma` sequential applications pays `gamma` sweeps for them. That term is charged in full below; on a bandwidth store the bytes it moves are not separately charged at all, because this repository's model configs carry no size for the table -- an omission whose size, on DeepSeek-V4-Pro-0813, is the externally published 132,382,720 B per draft token, 0.33% of the 39,666,603,980 B target pass.

| study | model | ctx | batch | class | design | tau* draft in ROM | tau* draft in KV store | KV placement feasible | why not |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 230.32 | 7.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 6.70 | 1.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 230.32 | 7.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 6.70 | 1.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 230.32 | 7.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 8.46 | 1.44 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 230.32 | 7.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5.79 | 1.51 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 230.32 | 7.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.80 | 1.60 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 230.32 | 7.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.87 | 1.95 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 240.00 | 6.76 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.99 | 2.52 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 171.04 | 6.68 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 13.22 | 3.90 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 71.93 | 8.68 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 129.97 | 16.66 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 75.39 | 8.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 11.07 | 6.90 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 246.12 | 9.54 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 8.52 | 1.93 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 246.12 | 9.54 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 8.52 | 1.93 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 246.12 | 9.54 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 8.52 | 1.93 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 246.12 | 9.54 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 7.56 | 1.95 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 246.12 | 9.54 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.55 | 2.12 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 246.12 | 9.54 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.57 | 2.73 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 246.12 | 9.54 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 20.55 | 3.13 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 144.64 | 9.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 16.86 | 4.72 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 155.58 | 10.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 131.50 | 23.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 45.34 | 9.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.30 | 5.44 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 137.78 | 8.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3.97 | 1.46 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 137.78 | 8.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3.97 | 1.46 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 137.78 | 8.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 3.96 | 1.46 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 137.78 | 8.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3.96 | 1.46 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 137.78 | 8.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.97 | 1.55 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 122.79 | 7.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.06 | 1.85 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 122.79 | 7.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 153.78 | 21.65 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 54.07 | 8.52 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 153.78 | 21.65 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 59.72 | 9.22 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 107.72 | 19.77 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 19.72 | 5.24 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 9.56 | 5.17 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 154.41 | 9.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4.88 | 1.90 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 154.41 | 9.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4.88 | 1.90 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 154.41 | 9.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 5.04 | 1.89 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 154.41 | 9.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5.03 | 1.89 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 154.41 | 9.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.04 | 2.04 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 154.41 | 9.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.12 | 2.59 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 132.66 | 9.68 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.26 | 3.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 55.83 | 9.72 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.82 | 5.36 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 41.71 | 9.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 100.21 | 27.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 22.65 | 8.57 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 31.21 | 19.19 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 137.78 | 8.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3.97 | 1.46 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 137.78 | 8.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3.97 | 1.46 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 137.78 | 8.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 3.96 | 1.46 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 137.78 | 8.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3.96 | 1.46 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 137.78 | 8.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.97 | 1.55 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 122.79 | 7.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.06 | 1.85 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 122.79 | 7.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 153.78 | 21.65 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 54.07 | 8.52 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 153.78 | 21.65 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 59.72 | 9.22 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 107.72 | 19.77 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 19.72 | 5.24 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 9.56 | 5.17 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 154.41 | 9.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4.88 | 1.90 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 154.41 | 9.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4.88 | 1.90 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 154.41 | 9.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 5.04 | 1.89 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 154.41 | 9.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5.03 | 1.89 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 154.41 | 9.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.04 | 2.04 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 154.41 | 9.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.12 | 2.59 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 132.66 | 9.68 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.26 | 3.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 55.83 | 9.72 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.82 | 5.36 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 41.71 | 9.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 100.24 | 27.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 22.65 | 8.57 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 31.22 | 19.20 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x63` | 5.67 | 1.83 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 4.61 | 1.30 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 31.27 | 8.12 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.31 | 1.49 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 31.27 | 8.12 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.31 | 1.49 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 31.27 | 8.12 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.31 | 1.49 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 31.27 | 8.12 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.31 | 1.49 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 31.27 | 8.12 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.31 | 1.49 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 31.27 | 8.12 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.21 | 1.67 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349-romfill` | 16.66 | 8.43 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 20.46 | 1.50 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x349-romfill` | 17.18 | 8.69 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 7.59 | 1.22 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x349-romfill` | 10.31 | 8.55 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill` | 4.30 | 2.91 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 86.75 | 8.82 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 102.00 | 32.85 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 86.75 | 8.82 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 102.00 | 32.85 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 86.75 | 8.82 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 102.00 | 32.85 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 86.75 | 8.82 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 102.00 | 32.85 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 79.14 | 8.68 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 102.00 | 32.85 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 75.73 | 8.36 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 102.00 | 32.85 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 75.73 | 8.36 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 102.00 | 32.85 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 37.02 | 9.47 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 102.00 | 32.85 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 42.31 | 10.62 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 73.07 | 31.01 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.78 | 9.35 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 25.32 | 22.99 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 84.73 | 8.88 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 107.19 | 34.16 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 84.73 | 8.88 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 107.19 | 34.16 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 84.73 | 8.88 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 107.19 | 34.16 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 84.73 | 8.88 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 107.19 | 34.16 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 82.95 | 8.72 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 107.19 | 34.16 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 79.19 | 8.38 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 107.19 | 34.16 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 79.19 | 8.38 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 108.61 | 34.60 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 38.96 | 9.57 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 108.61 | 34.60 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 44.98 | 10.82 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 77.85 | 32.70 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.48 | 9.46 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 10.65 | 5.14 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 155.59 | 9.25 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 5.99 | 1.85 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 155.59 | 9.25 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 6.34 | 1.98 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 155.59 | 9.25 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 6.34 | 1.98 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 155.59 | 9.25 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 6.34 | 1.98 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 155.59 | 9.25 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.33 | 2.20 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 155.59 | 9.25 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 14.00 | 2.62 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 155.59 | 9.25 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 12.80 | 3.41 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 74.83 | 9.82 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 8.96 | 4.27 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 79.92 | 10.35 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 70.29 | 17.61 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 26.16 | 9.40 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 47.93 | 11.23 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 148.23 | 9.44 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 6.42 | 1.96 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 148.23 | 9.44 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 6.42 | 1.96 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 148.23 | 9.44 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 6.42 | 1.96 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 148.23 | 9.44 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 6.41 | 1.96 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 148.23 | 9.44 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.42 | 2.18 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 148.23 | 9.44 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.48 | 2.96 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 148.23 | 9.44 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 10.26 | 4.62 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 90.33 | 10.24 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 12.05 | 5.49 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 98.06 | 10.94 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 11.07 | 7.11 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 30.81 | 9.76 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 9.10 | 7.68 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 148.25 | 9.46 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 6.41 | 1.95 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 148.25 | 9.46 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 6.41 | 1.95 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 148.25 | 9.46 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 6.41 | 1.95 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 148.25 | 9.46 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 6.41 | 1.95 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 148.25 | 9.46 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.42 | 2.17 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 148.25 | 9.46 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.48 | 2.95 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 148.25 | 9.46 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.58 | 4.10 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 93.24 | 10.32 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 11.98 | 5.42 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 101.53 | 11.06 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 11.14 | 7.09 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 31.70 | 9.83 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 9.14 | 7.67 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x63-romfill` | 5.85 | 2.35 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 6.29 | 1.41 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 2.84 | 1.28 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 2.25 | 1.62 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 2.95 | 1.46 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 2.25 | 1.62 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 3.13 | 1.77 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 2.25 | 1.62 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 3.43 | 2.25 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 2.25 | 1.62 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 27.50 | 7.74 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 2.25 | 1.62 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 27.50 | 7.74 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 43.59 | 1.67 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 51.71 | 4.50 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 19.13 | 1.68 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 53.06 | 4.58 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.50 | 1.30 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 15.90 | 4.03 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 84.72 | 2.36 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 93.60 | 11.95 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 2.72 | 1.72 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 93.60 | 11.95 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3.09 | 2.10 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 93.60 | 11.95 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 3.09 | 2.10 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 93.60 | 11.95 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3.09 | 2.09 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 93.60 | 11.95 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.10 | 2.32 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 84.49 | 11.50 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.18 | 3.08 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 83.72 | 11.41 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.33 | 4.08 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 38.65 | 11.81 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.94 | 5.39 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 42.68 | 12.90 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 53.16 | 35.73 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 16.57 | 8.76 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 17.87 | 24.44 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 89.69 | 12.01 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3.11 | 2.11 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 89.69 | 12.01 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3.11 | 2.11 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 89.69 | 12.01 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 3.11 | 2.11 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 89.69 | 12.01 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3.10 | 2.10 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 89.69 | 12.01 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.13 | 2.33 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 88.88 | 11.70 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.23 | 3.13 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 88.02 | 11.60 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 112.51 | 57.70 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 40.81 | 12.08 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 112.51 | 57.70 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 45.40 | 13.29 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 79.76 | 53.41 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 17.24 | 8.82 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 8.98 | 5.68 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x196` | 3.59 | 2.32 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 8.28 | 2.15 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 141.96 | 11.46 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 16.10 | 2.72 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 141.96 | 11.46 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 16.10 | 2.72 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 141.96 | 11.46 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 16.10 | 2.72 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 141.96 | 11.46 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 15.88 | 2.86 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 141.96 | 11.46 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 14.28 | 3.77 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 141.96 | 11.46 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 11.98 | 4.76 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 63.76 | 11.25 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 6.72 | 4.85 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 66.72 | 11.69 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 100.98 | 14.39 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 22.79 | 10.27 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 26.97 | 10.57 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 155.88 | 12.02 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 8.30 | 3.04 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 155.88 | 12.02 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 8.30 | 3.04 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 155.88 | 12.02 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 8.30 | 3.04 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 155.88 | 12.02 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 8.40 | 3.03 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 155.88 | 12.02 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 8.38 | 3.48 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 155.88 | 12.02 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 8.36 | 5.03 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 155.88 | 12.02 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 14.08 | 6.87 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 77.11 | 12.03 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 12.29 | 10.11 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 81.62 | 12.62 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 9.59 | 8.81 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 26.57 | 10.86 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 8.04 | 7.80 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 155.11 | 12.08 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 8.30 | 3.03 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 155.11 | 12.08 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 8.30 | 3.03 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 155.11 | 12.08 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 8.30 | 3.03 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 155.11 | 12.08 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 8.40 | 3.02 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 155.11 | 12.08 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 8.38 | 3.47 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 155.11 | 12.08 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 8.36 | 5.02 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 155.11 | 12.08 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 14.05 | 6.84 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 79.63 | 12.17 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 12.78 | 10.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 84.47 | 12.80 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 10.28 | 9.42 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 27.30 | 10.97 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 8.74 | 8.46 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x59` | 89.32 | 10.86 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | 104.19 | 12.84 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 90.44 | 8.70 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 2.51 | 1.53 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 90.44 | 8.70 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 2.51 | 1.53 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 90.44 | 8.70 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2.51 | 1.53 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 90.44 | 8.70 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.51 | 1.63 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 58.99 | 8.28 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.55 | 1.97 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 58.91 | 8.27 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.61 | 2.40 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 28.35 | 9.03 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 11.06 | 2.05 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 31.02 | 9.76 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 20.98 | 9.49 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 16.61 | 4.83 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 7.64 | 7.03 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x184` | 3.19 | 1.67 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 8.30 | 1.58 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 136.71 | 8.89 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 5.54 | 1.91 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 136.71 | 8.89 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 5.54 | 1.91 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 136.71 | 8.89 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 5.54 | 1.91 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 136.71 | 8.89 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 5.54 | 1.91 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 136.71 | 8.89 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 5.54 | 1.91 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 136.71 | 8.89 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 5.34 | 2.09 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 61.90 | 9.07 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 24.99 | 2.13 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 64.49 | 9.39 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 9.90 | 1.82 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 22.22 | 8.87 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 148.33 | 3.67 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x83` | 95.73 | 11.60 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 3.15 | 1.45 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 95.31 | 11.25 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10-romfill` | 2.88 | 1.97 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 95.31 | 11.25 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10-romfill` | 2.88 | 1.97 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 95.31 | 11.25 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10-romfill` | 2.88 | 1.97 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 95.31 | 11.25 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.84 | 2.14 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x99` | 93.73 | 11.58 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 16.46 | 2.43 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 63.44 | 10.50 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 13.37 | 2.73 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 29.20 | 10.64 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 6.63 | 2.17 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x237` | 28.07 | 8.54 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 12.02 | 8.27 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 17.42 | 7.09 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 28.28 | 4.96 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x237` | 2.98 | 1.66 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 11.62 | 1.78 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 49.87 | 2.11 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 49.87 | 2.11 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 49.87 | 2.11 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 49.87 | 2.11 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 49.87 | 2.11 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 49.87 | 2.11 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 24.48 | 2.42 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 8.58 | 1.97 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 119.61 | 3.79 | yes | -- |

## The capacity requirement, stated as a requirement

Every evaluated ROM design carries `weight_capacity_bytes == stored_weight_bytes` (the `romfill` variants reach 1.0039x), so no evaluated design has spare array for a drafter it does not already store. Re-solving the area split is `balanced_area_split`'s job and that file is not touched here, so what follows is a requirement -- this much extra array, or this much extra sweep on every pass -- and not a new design. **The speculative-optimal ROM design has not been computed, only bounded by the rungs that already exist.**

| study | model | design | drafter already in the checkpoint | extra stored bytes | extra array mm2 | as a fraction of the design | sweep inflation if area is held fixed |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-tensor-x63` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-tensor-x63-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-tensor-x196` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x59` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-tensor-x184` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x83` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-tensor-x237` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |

## Which design the published rule chooses once a block is verified

A re-ranking of designs the study already evaluated, under the study's own selection rule (non-dominated on per-user tokens/s and tokens/s per 1,000 mm2, then a marginal-return walk from the smallest feasible machine). `tau` is a common factor on both axes, so the choice is independent of the acceptance rate. The rule's reproduction of the published autoregressive recommendation is reported first, because a re-ranking whose baseline does not reproduce is not evidence of anything.

| study | model | published recommendation | rule reproduces it | under speculation, draft in ROM | draft in KV store | moves |
| --- | --- | --- | --- | --- | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-SRAMKV-array-hw-tensor-x88` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x96` | `ROM-N5-native-HBMKV-array-hw-tensor-x113` | yes |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-array-hw-tensor-x113` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x126` | `ROM-N6-native-HBMKV-array-hw-tensor-x143` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-tensor-x63` | yes | `ROM-N5-native-HBMKV-array-hw-tensor-x63` | `ROM-N5-native-HBMKV-array-hw-tensor-x63` | no |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-tensor-x74` | yes | `ROM-N6-native-HBMKV-array-hw-tensor-x87` | `ROM-N6-native-HBMKV-array-hw-tensor-x90` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-SRAMKV-array-hw-tensor-x57` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x57` | `ROM-N5-native-HBMKV-array-hw-tensor-x63` | no |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-SRAMKV-array-hw-tensor-x68` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x80` | `ROM-N6-native-HBMKV-array-hw-tensor-x90` | yes |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-tensor-x36` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x40` | `ROM-N5-native-HBMKV-array-hw-tensor-x279` | yes |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-tensor-x34` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x34` | `ROM-N5-native-HBMKV-array-hw-tensor-x36` | no |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-tensor-x34` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x34` | `ROM-N5-native-HBMKV-array-hw-tensor-x36` | no |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-tensor-x154` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x170` | `ROM-N5-native-HBMKV-array-hw-tensor-x193` | yes |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-tensor-x151` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x169` | `ROM-N5-native-HBMKV-array-hw-tensor-x193` | yes |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-tensor-x160` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x160` | `ROM-N5-native-HBMKV-array-hw-tensor-x193` | no |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-tensor-x50` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x57` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | yes |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | `ROM-N6-native-HBMKV-array-hw-tensor-x54` | no |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | `ROM-N6-native-HBMKV-array-hw-tensor-x53` | no |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-tensor-x196` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x227` | `ROM-N6-native-HBMKV-array-hw-tensor-x248` | yes |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-tensor-x195` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x227` | `ROM-N6-native-HBMKV-array-hw-tensor-x248` | yes |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-tensor-x194` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x221` | `ROM-N6-native-HBMKV-array-hw-tensor-x248` | yes |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | `ROM-N5-native-HBMKV-array-hw-tensor-x56` | no |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-tensor-x166-romfill` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x182` | `ROM-N5-native-HBMKV-array-hw-tensor-x399` | yes |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x7-romfill` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | `ROM-N6-native-HBMKV-array-hw-tensor-x79` | no |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-tensor-x209` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x236` | `ROM-N6-native-HBMKV-wafer-tensor-x66` | yes |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | yes | `--` | `--` | the drafter does not apply to this model |

**The rule reproduces the published autoregressive recommendation on 26 of 26 model-and-study rows.** Of the 22 rows where it reproduces and the drafter applies, verifying a block moves the chosen rung on 13. Where it moves, it moves toward machines with compute headroom for a block, which is exactly what the arithmetic predicts: a verification pass raises arithmetic intensity by the block size, and a machine sized with just enough compute for one token per sweep has no room for it. **This is a re-ranking of rungs that already exist. The speculative-optimal design has not been computed: that would need the area split re-solved, which is `balanced_area_split`'s job and not this layer's.**

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
| DeepSeek-V4.1-Flash | 1 | 826,232,712 | 6.3% | -- | -- | --x |
| DeepSeek-V4.1-Flash | 2 | 937,273,992 | 7.2% | -- | -- | --x |
| DeepSeek-V4.1-Flash | 3 | 1,046,580,252 | 8.0% | -- | -- | --x |
| DeepSeek-V4.1-Flash | 4 | 1,154,178,602 | 8.9% | -- | -- | --x |
| DeepSeek-V4.1-Flash | 5 | 1,260,095,727 | 9.7% | -- | -- | --x |
| DeepSeek-V4.1-Flash | 6 | 1,364,357,898 | 10.5% | -- | -- | --x |
| DeepSeek-V4.1-Flash | 7 | 1,466,990,972 | 11.3% | -- | -- | --x |
| DeepSeek-V4.1-Flash | 8 | 1,568,020,404 | 12.0% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 826,232,712 | 6.3% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 937,273,992 | 7.2% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-hbm | 3 | 1,046,580,252 | 8.0% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 1,154,178,602 | 8.9% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-hbm | 5 | 1,260,095,727 | 9.7% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-hbm | 6 | 1,364,357,898 | 10.5% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-hbm | 7 | 1,466,990,972 | 11.3% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 1,568,020,404 | 12.0% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 826,232,712 | 6.3% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 937,273,992 | 7.2% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-host | 3 | 1,046,580,252 | 8.0% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 1,154,178,602 | 8.9% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-host | 5 | 1,260,095,727 | 9.7% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-host | 6 | 1,364,357,898 | 10.5% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-host | 7 | 1,466,990,972 | 11.3% | -- | -- | --x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 1,568,020,404 | 12.0% | -- | -- | --x |

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

