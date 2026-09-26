# Speculative decoding on the area-constrained roofline: released_dspark

> DeepSeek-V4's own speculative module, as shipped. Every figure below is derived from the roofline artifacts
> this repository has already published, by re-assembling each point's own five
> critical-path terms for a speculative cycle. Nothing here re-runs the machine
> model, and nothing here invents an acceptance rate.

## What this layer says

1. **Every term the speculative arithmetic needs is already in the published artifact, exactly.** 183,227 feasible points across 52 studies were rebuilt from their own five critical-path terms and every one reproduced its published step time to 1e-9 relative. Nothing here re-ran the machine model, and the layer is additive by construction rather than by promise.
2. **The headline is a break-even, not a speedup.** `tau* = T_cycle / step_time_s`, and `tau <= gamma+1` always. Of 245,677 (point, draft-placement) pairs where this profile's drafter applies, 87,490 (35.6%) cannot be sped up by speculation at ANY acceptance rate, at any block size on the ladder, even charging the drafter no KV traffic at all.
3. **The ROM-versus-GPU ratio under speculation carries no acceptance rate.** It is `T_cycle(GPU) / T_cycle(ROM)`: `tau` is a property of the model and its drafter, not of the machine, so it is identical on both sides and cancels. Every movement this report shows is a machine effect and nothing else, which is why it can be published without inventing an acceptance rate.
4. **The ratio moves, and it mostly compresses.** Across 775 model-context-batch-class rows, 769 move the ROM-versus-GPU per-user ratio DOWN under speculation and 6 move it UP, spanning 0.018x to 1.080x. The ROM advantage compresses on most operating points.
5. **At batch 1 the two extremes are opposite in sign, and they are the result.** DeepSeek-V4.1-Flash on `array` silicon goes from 4.68x to 0.12x -- a 0.026x movement -- while MiMo-V2.6-Flash on `wafer` silicon goes from 12.94x to 6.33x, a 0.489x movement. A layer that multiplied both sides by `tau` would have reported neither.
6. **A moving ratio is not a win for either side, and the report says so on every table.** At the most favourable sourced acceptance (5.00) speculation is worth having on 14 of 777 ROM class rows and 754 of 777 GPU rows; everywhere else the design runs SLOWER with a drafter than without one. Where both sides lose, a rising ratio means only that the comparator lost more.
7. **Compute is never a gain and always a loss.** A verification pass over `n` positions charges `n` times the arithmetic exactly, so per accepted token compute costs `(n/tau) >= 1` times what it did. A compute-bound design cannot be sped up by speculation at any acceptance rate; it can only be slowed. That is where the recommended ROM designs live, because the sizing rule gives them just enough compute for one token per sweep.
8. **On a mask-ROM machine the draft pass costs a full array sweep, and that is the load-bearing assumption of the whole ROM verdict.** `stored/peak` is a technology constant in `src/opentallas/roofline.py`, so a pass reading only the drafter's region takes as long as sweeping the entire array. The alternative -- holding the drafter in the KV store -- is priced beside it on every ROM row and has NOT been costed in silicon area.
9. **The mask-ROM designs are already storing this drafter, and already sweeping it on every ordinary token.** `_rom_stored_bytes` stores the whole released checkpoint, and the checkpoint ships the draft module for DeepSeek-V4-Flash-0731, DeepSeek-V4-Pro-0813, DeepSeek-V4.1-Flash, DeepSeek-V4.1-Flash-engram-hbm, DeepSeek-V4.1-Flash-engram-host, MiMo-V2.6-Flash, MiMo-V2.6-Pro. So the storage inflation is 1.000x, the extra array requirement is zero, and the autoregressive ROM baseline in the published study is ALREADY paying for a drafter it does not use. The HBM comparators are not: their engaged bytes exclude the draft categories entirely.
10. **This profile does not apply to Kimi-K3, Qwen3-8B.** Their released checkpoints carry no draft weights at all, and transplanting a drafter that was never trained for them would be inventing a model. They are reported as not applicable rather than modelled.
11. **This drafter's SEQUENTIAL step is what it costs on a mask-ROM machine, and it costs more than the drafter's own size.** The bias is applied once per draft token with no transformer re-run, so on a bandwidth machine it moves a table and is nearly free -- but under the locality rule every pass that touches the array takes the full-array sweep time whatever it reads, so `gamma` sequential applications cost `gamma` full sweeps. The draft pass is 7% to 99% of the whole speculative cycle on the ROM designs this report quotes (median 89%), almost all of it those sweeps. A block-diffusion drafter has no such term at all, which is the single largest structural difference between the two profiles on this silicon.
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
| `n5_vs_b200-deepseek-v41-flash` | 4,944 | 0 |
| `n6_vs_a100-deepseek-v41-flash` | 3,732 | 0 |
| `n5_vs_b200-deepseek-v41-flash-1m` | 4,924 | 0 |
| `n6_vs_a100-deepseek-v41-flash-1m` | 3,743 | 0 |
| `n5_vs_b200-deepseek-v41-flash-8k` | 4,930 | 0 |
| `n6_vs_a100-deepseek-v41-flash-8k` | 3,770 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | 5,965 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | 4,718 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | 5,789 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | 4,460 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | 5,908 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | 4,648 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | 5,160 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | 4,364 | 0 |
| `n5_vs_b200-kimi-k3` | 3,331 | 0 |
| `n6_vs_a100-kimi-k3` | 1,744 | 0 |
| `n5_vs_b200-kimi-k3-1m` | 1,611 | 0 |
| `n6_vs_a100-kimi-k3-1m` | 1,091 | 0 |
| `n5_vs_b200-kimi-k3-8k` | 3,075 | 0 |
| `n6_vs_a100-kimi-k3-8k` | 2,298 | 0 |
| `n5_vs_b200-mimo-v26-flash` | 2,781 | 0 |
| `n6_vs_a100-mimo-v26-flash` | 2,451 | 0 |
| `n5_vs_b200-mimo-v26-flash-1m` | 1,634 | 0 |
| `n6_vs_a100-mimo-v26-flash-1m` | 1,309 | 0 |
| `n5_vs_b200-mimo-v26-flash-8k` | 4,354 | 0 |
| `n6_vs_a100-mimo-v26-flash-8k` | 4,556 | 0 |
| `n5_vs_b200-mimo-v26-pro` | 1,523 | 0 |
| `n6_vs_a100-mimo-v26-pro` | 1,209 | 0 |
| `n5_vs_b200-mimo-v26-pro-1m` | 1,789 | 0 |
| `n6_vs_a100-mimo-v26-pro-1m` | 1,319 | 0 |
| `n5_vs_b200-mimo-v26-pro-8k` | 4,908 | 0 |
| `n6_vs_a100-mimo-v26-pro-8k` | 3,783 | 0 |
| `n5_vs_b200-qwen3-8b-1m` | 762 | 0 |
| `n6_vs_a100-qwen3-8b-1m` | 597 | 0 |
| `n5_vs_b200-qwen3-8b-200k` | 1,110 | 0 |
| `n6_vs_a100-qwen3-8b-200k` | 937 | 0 |
| `n5_vs_b200-flash-1m` | 2,479 | 0 |
| `n5_vs_b200-flash-32k` | 4,582 | 0 |
| `n5_vs_b200-flash-8k` | 4,540 | 0 |
| `n5_vs_b200-pro-200k` | 4,423 | 0 |
| `n5_vs_b200-pro-32k` | 4,388 | 0 |
| `n5_vs_b200-pro-8k` | 4,328 | 0 |
| `n6_vs_a100-flash-1m` | 1,801 | 0 |
| `n6_vs_a100-flash-32k` | 4,468 | 0 |
| `n6_vs_a100-flash-8k` | 4,418 | 0 |
| `n6_vs_a100-pro-200k` | 3,339 | 0 |
| `n6_vs_a100-pro-32k` | 3,365 | 0 |
| `n6_vs_a100-pro-8k` | 3,614 | 0 |
| `n5_vs_b200` | 8,991 | 0 |
| `n6_vs_a100` | 7,618 | 0 |
| `n5_vs_b200-quantised_variant` | 2,942 | 0 |
| `n6_vs_a100-quantised_variant` | 2,704 | 0 |

The identity checked is: `max(max(memory, compute)/stage_balance, serial path) x thermal_scale == step_time_s, with memory assembled by designs[].shared_memory_path and the compute-in-ROM fusion rule, and the serial path -- link_latency + layer_fixed_latency + the sweep on the path -- independently rebuilt from the model profile, the technology file and the token's operator graph (opentallas.critical_path)`.

## Headline: where speculation cannot pay at any acceptance rate

Counted at the LOW end of the unsourced drafter-KV band, which is the most favourable assumption available to speculation. `tau*` is the break-even acceptance at this profile's served block size.

| study | model | family | draft placement | binds on (autoregressive) | points | cannot pay at any gamma | tau* min | tau* median | tau* max |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,599 | 434 | 1.19 | 3.85 | 65.78 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 89 | 0 | 1.17 | 3.40 | 4.83 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 432 | 2 | 2.00 | 3.17 | 23.98 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 807 | 229 | 5.00 | 7.52 | 20.85 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 48 | 48 | 17.26 | 18.60 | 20.81 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 723 | 81 | 1.54 | 4.56 | 11.27 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 837 | 105 | 1.55 | 2.96 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 409 | 99 | 2.01 | 5.99 | 11.95 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 807 | 807 | 8.18 | 55.68 | 181.19 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 48 | 48 | 13.99 | 54.63 | 64.29 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 723 | 401 | 2.54 | 8.19 | 132.00 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 837 | 315 | 1.70 | 7.19 | 67.37 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 409 | 373 | 6.88 | 16.40 | 277.26 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 1 | 1 | 8.21 | 8.21 | 8.21 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 772 | 247 | 1.37 | 4.97 | 65.77 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 547 | 1 | 1.35 | 2.82 | 23.39 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 737 | 338 | 5.12 | 8.28 | 22.25 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 46 | 42 | 4.49 | 18.85 | 20.31 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 618 | 77 | 1.55 | 4.94 | 11.46 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 714 | 95 | 1.57 | 3.13 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 297 | 107 | 2.08 | 7.27 | 18.13 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 737 | 737 | 8.16 | 52.49 | 207.88 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 46 | 43 | 5.70 | 55.39 | 125.25 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 618 | 314 | 2.12 | 8.08 | 119.51 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 714 | 206 | 1.76 | 6.46 | 40.73 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 297 | 274 | 6.27 | 16.22 | 275.79 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,660 | 421 | 1.19 | 3.69 | 65.78 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 88 | 0 | 1.19 | 3.37 | 4.72 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 424 | 0 | 2.08 | 3.14 | 7.93 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 745 | 147 | 5.08 | 7.47 | 9.91 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 126 | 36 | 3.20 | 7.74 | 9.58 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 658 | 71 | 1.56 | 4.09 | 8.29 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 857 | 105 | 1.48 | 2.73 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 366 | 67 | 1.88 | 6.08 | 9.16 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 745 | 745 | 8.18 | 44.81 | 184.69 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 126 | 123 | 4.37 | 69.18 | 188.58 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 658 | 363 | 2.57 | 8.19 | 111.18 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 857 | 313 | 1.70 | 6.99 | 65.86 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 366 | 327 | 6.20 | 16.09 | 263.83 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 2 | 0 | 6.76 | 6.77 | 6.77 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 816 | 257 | 1.37 | 4.81 | 65.72 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 569 | 0 | 1.64 | 2.78 | 13.17 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 683 | 214 | 4.86 | 8.15 | 10.56 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 125 | 8 | 2.57 | 7.47 | 10.28 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 531 | 57 | 1.57 | 4.08 | 8.27 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 771 | 100 | 1.53 | 2.88 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 246 | 71 | 2.14 | 7.60 | 10.66 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 683 | 683 | 8.18 | 40.94 | 204.26 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 125 | 111 | 2.70 | 55.13 | 183.67 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 531 | 280 | 2.77 | 8.18 | 115.20 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 771 | 203 | 1.72 | 6.52 | 39.19 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 246 | 226 | 6.84 | 16.10 | 221.43 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,535 | 422 | 1.19 | 3.90 | 65.79 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 88 | 0 | 1.17 | 3.46 | 4.86 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 427 | 4 | 1.74 | 3.17 | 27.28 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 792 | 216 | 4.82 | 7.46 | 84.81 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 60 | 60 | 48.37 | 89.22 | 92.55 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 722 | 124 | 1.54 | 4.81 | 30.75 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 861 | 135 | 1.55 | 3.26 | 43.00 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 445 | 134 | 2.01 | 6.11 | 62.70 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 792 | 792 | 8.18 | 62.29 | 190.62 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 60 | 51 | 4.59 | 17.61 | 22.02 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 722 | 382 | 2.54 | 8.17 | 135.33 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 861 | 295 | 1.68 | 6.87 | 67.79 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 445 | 406 | 6.87 | 16.39 | 281.52 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 2 | 2 | 8.20 | 8.32 | 8.32 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 713 | 227 | 1.37 | 4.86 | 65.74 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 515 | 1 | 1.36 | 2.84 | 22.00 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 776 | 355 | 5.27 | 8.26 | 90.44 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 48 | 48 | 85.55 | 89.84 | 93.39 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 631 | 116 | 1.55 | 5.80 | 30.75 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 771 | 127 | 1.57 | 3.40 | 37.08 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 314 | 117 | 2.08 | 7.59 | 53.12 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 776 | 776 | 8.16 | 56.24 | 209.73 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 48 | 46 | 5.97 | 17.87 | 22.91 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 631 | 307 | 2.76 | 8.01 | 120.78 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 771 | 217 | 1.74 | 6.49 | 40.85 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 314 | 294 | 6.78 | 16.11 | 281.43 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 2,078 | 555 | 1.19 | 3.83 | 65.79 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 109 | 0 | 1.17 | 3.46 | 4.83 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 553 | 4 | 2.00 | 3.17 | 23.98 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 830 | 216 | 4.87 | 7.45 | 15.62 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 5 | 2 | 5.88 | 7.78 | 11.96 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 841 | 91 | 1.48 | 3.99 | 10.26 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 924 | 120 | 1.47 | 2.60 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 625 | 123 | 1.11 | 5.58 | 14.24 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 830 | 830 | 8.16 | 31.38 | 129.85 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 5 | 3 | 7.33 | 8.80 | 26.58 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 841 | 431 | 1.83 | 8.17 | 75.48 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 924 | 276 | 1.58 | 6.07 | 40.91 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 625 | 581 | 5.56 | 19.02 | 180.65 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 3 | 2 | 7.68 | 8.21 | 8.24 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,042 | 329 | 1.37 | 4.85 | 65.77 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 715 | 2 | 1.38 | 2.83 | 23.39 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 713 | 210 | 5.23 | 8.16 | 9.66 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 107 | 98 | 4.00 | 21.28 | 22.17 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 755 | 88 | 1.48 | 4.87 | 16.03 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 894 | 114 | 1.47 | 2.68 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 489 | 138 | 1.11 | 6.72 | 19.52 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 713 | 711 | 7.34 | 40.29 | 151.40 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 107 | 104 | 4.04 | 93.80 | 109.10 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 755 | 403 | 1.91 | 8.18 | 88.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 894 | 217 | 1.60 | 5.63 | 37.17 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 489 | 453 | 5.66 | 19.79 | 180.65 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 2,219 | 574 | 1.19 | 3.80 | 65.78 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 110 | 0 | 1.19 | 3.63 | 4.72 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 559 | 0 | 2.04 | 3.14 | 8.26 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 738 | 152 | 4.66 | 7.40 | 8.32 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 71 | 0 | 3.00 | 7.58 | 8.37 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 766 | 75 | 1.49 | 4.62 | 8.29 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 876 | 111 | 1.47 | 2.65 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 450 | 66 | 1.28 | 5.26 | 9.60 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 738 | 738 | 8.15 | 22.31 | 128.08 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 71 | 63 | 3.32 | 49.84 | 84.06 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 766 | 421 | 2.68 | 8.20 | 103.44 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 876 | 248 | 1.58 | 6.11 | 39.75 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 450 | 418 | 5.67 | 19.53 | 176.19 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 1 | 0 | 6.76 | 6.76 | 6.76 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,060 | 322 | 1.37 | 4.55 | 65.71 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 690 | 0 | 1.52 | 2.81 | 13.29 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 727 | 211 | 5.17 | 8.12 | 9.18 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 92 | 0 | 2.76 | 6.47 | 7.88 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 617 | 63 | 1.49 | 4.29 | 8.28 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 888 | 111 | 1.47 | 2.68 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 385 | 84 | 1.61 | 6.66 | 11.98 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 727 | 725 | 7.27 | 33.73 | 143.24 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 92 | 66 | 2.29 | 33.72 | 127.03 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 617 | 303 | 2.68 | 8.02 | 73.59 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 888 | 207 | 1.59 | 5.55 | 36.75 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 385 | 361 | 5.46 | 17.96 | 176.52 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,980 | 534 | 1.19 | 3.90 | 65.79 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 103 | 0 | 1.17 | 3.49 | 4.86 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 537 | 6 | 1.74 | 3.17 | 27.28 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 842 | 235 | 4.70 | 7.49 | 15.89 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 846 | 100 | 1.48 | 4.15 | 10.50 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 936 | 120 | 1.47 | 2.63 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 664 | 129 | 1.06 | 5.38 | 16.41 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 842 | 842 | 8.16 | 35.25 | 135.06 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 846 | 438 | 2.22 | 8.17 | 75.38 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 936 | 282 | 1.58 | 6.05 | 41.23 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 664 | 611 | 5.53 | 18.90 | 181.83 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 3 | 3 | 8.20 | 8.24 | 8.32 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 983 | 310 | 1.37 | 4.82 | 65.75 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 684 | 2 | 1.34 | 2.85 | 22.00 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 796 | 299 | 5.09 | 8.22 | 25.48 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 740 | 98 | 1.48 | 4.85 | 18.28 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 909 | 114 | 1.47 | 2.67 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 533 | 153 | 1.06 | 6.62 | 22.80 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 796 | 794 | 7.33 | 44.58 | 146.75 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 740 | 410 | 2.37 | 8.19 | 84.88 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 909 | 228 | 1.60 | 5.62 | 37.29 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 533 | 494 | 5.68 | 19.92 | 181.83 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 1,420 | 389 | 1.19 | 3.71 | 65.79 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `thermal` | 91 | 0 | 1.17 | 3.02 | 4.83 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 429 | 5 | 1.94 | 3.17 | 24.65 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 832 | 262 | 4.87 | 7.61 | 18.41 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 51 | 50 | 5.14 | 17.55 | 19.58 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `layer_fixed_latency` | 870 | 93 | 1.54 | 4.53 | 10.26 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 901 | 120 | 1.53 | 2.87 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 566 | 102 | 1.98 | 5.84 | 14.24 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 832 | 832 | 8.16 | 30.41 | 104.46 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 51 | 50 | 6.67 | 45.73 | 64.61 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `layer_fixed_latency` | 870 | 419 | 2.22 | 8.09 | 75.48 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 901 | 257 | 1.63 | 6.04 | 40.91 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 566 | 531 | 5.56 | 20.21 | 179.66 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `compute` | 5 | 4 | 7.68 | 8.24 | 8.24 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 797 | 276 | 1.37 | 5.35 | 65.77 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 638 | 3 | 1.38 | 2.79 | 17.93 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 680 | 222 | 5.23 | 8.19 | 20.25 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 151 | 142 | 4.00 | 18.64 | 22.17 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `layer_fixed_latency` | 763 | 88 | 1.54 | 5.30 | 16.03 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 864 | 114 | 1.49 | 2.79 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 466 | 127 | 2.00 | 6.84 | 19.52 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 680 | 678 | 7.34 | 38.82 | 121.11 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 151 | 148 | 4.05 | 56.17 | 109.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `layer_fixed_latency` | 763 | 405 | 1.91 | 8.18 | 88.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 864 | 207 | 1.67 | 5.59 | 37.17 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 466 | 432 | 6.27 | 19.62 | 178.60 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 117 | 0 | 1.26 | 1.55 | 17.43 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 926 | 174 | 1.14 | 2.21 | 65.38 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 60 | 0 | 1.28 | 1.91 | 3.12 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 246 | 0 | 1.55 | 2.73 | 8.47 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 8 | 0 | 6.92 | 7.34 | 7.36 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 198 | 0 | 1.05 | 2.28 | 6.93 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 327 | 0 | 1.56 | 4.17 | 17.46 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 464 | 31 | 1.36 | 2.08 | 10.10 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `thermal` | 303 | 0 | 1.52 | 1.96 | 3.64 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 132 | 12 | 1.80 | 5.80 | 8.07 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 8 | 8 | 22.37 | 23.87 | 24.68 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 198 | 102 | 1.16 | 8.55 | 51.06 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 327 | 88 | 2.19 | 6.80 | 35.96 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 464 | 85 | 1.48 | 4.31 | 21.88 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `thermal` | 303 | 223 | 2.35 | 13.66 | 67.21 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 132 | 114 | 5.95 | 12.51 | 22.96 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 47 | 0 | 1.25 | 1.40 | 4.41 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 511 | 112 | 1.25 | 4.25 | 65.23 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 453 | 1 | 1.36 | 1.94 | 17.36 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 26 | 0 | 6.83 | 7.48 | 7.84 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 522 | 0 | 1.06 | 2.20 | 7.10 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 280 | 0 | 1.56 | 4.27 | 15.37 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 478 | 31 | 1.35 | 1.93 | 9.43 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 134 | 14 | 1.90 | 5.30 | 8.07 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 26 | 26 | 14.23 | 23.27 | 27.35 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 522 | 251 | 1.10 | 6.98 | 41.61 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 280 | 52 | 2.33 | 5.90 | 26.84 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 478 | 87 | 1.44 | 3.67 | 13.01 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 134 | 112 | 6.49 | 13.13 | 22.97 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 336 | 5 | 1.24 | 1.53 | 20.98 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 598 | 85 | 1.10 | 2.04 | 64.90 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 222 | 0 | 1.32 | 2.10 | 2.11 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 3 | 0 | 7.82 | 7.82 | 7.82 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 107 | 0 | 1.04 | 1.16 | 7.19 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 203 | 0 | 1.54 | 5.14 | 17.21 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 115 | 0 | 1.33 | 1.94 | 4.35 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 50 | 10 | 2.13 | 6.78 | 8.01 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 3 | 3 | 16.69 | 16.75 | 16.78 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 107 | 41 | 1.11 | 1.45 | 51.30 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 203 | 80 | 2.32 | 6.79 | 30.61 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 115 | 7 | 1.36 | 2.39 | 14.56 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 50 | 49 | 8.18 | 14.77 | 22.99 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 364 | 1 | 1.13 | 1.46 | 19.46 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 454 | 50 | 1.11 | 2.00 | 62.05 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 37 | 0 | 1.87 | 3.37 | 7.06 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 39 | 2 | 5.59 | 7.96 | 8.09 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 105 | 0 | 1.03 | 1.15 | 7.78 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 127 | 0 | 1.62 | 4.39 | 15.18 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 133 | 0 | 1.32 | 2.04 | 5.04 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 50 | 10 | 2.19 | 7.08 | 8.01 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 39 | 37 | 6.93 | 13.84 | 27.55 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 105 | 41 | 1.05 | 1.31 | 33.74 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 127 | 37 | 2.52 | 5.45 | 26.40 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 133 | 3 | 1.33 | 2.62 | 11.14 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 50 | 49 | 8.33 | 14.75 | 22.99 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 18 | 0 | 2.86 | 3.83 | 4.94 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 931 | 257 | 1.15 | 3.27 | 65.49 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 58 | 0 | 1.13 | 1.38 | 3.33 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 403 | 0 | 1.44 | 3.09 | 14.25 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 534 | 54 | 4.78 | 7.46 | 10.36 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 177 | 1 | 1.33 | 6.19 | 11.25 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 810 | 64 | 1.54 | 3.99 | 19.86 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 783 | 72 | 1.29 | 2.52 | 11.77 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 640 | 27 | 1.30 | 5.28 | 10.08 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 534 | 534 | 8.04 | 16.44 | 65.10 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 177 | 141 | 2.27 | 26.51 | 80.66 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 810 | 343 | 2.16 | 7.88 | 47.33 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 783 | 184 | 1.56 | 5.04 | 21.14 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 640 | 615 | 5.27 | 21.98 | 105.32 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `compute` | 19 | 4 | 5.67 | 6.56 | 8.04 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 605 | 241 | 1.39 | 6.62 | 65.48 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 736 | 2 | 1.12 | 2.26 | 19.58 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 606 | 58 | 5.21 | 7.90 | 11.23 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 280 | 7 | 1.21 | 6.06 | 11.11 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 808 | 66 | 1.54 | 4.17 | 17.51 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 893 | 112 | 1.35 | 2.38 | 10.02 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 609 | 24 | 1.70 | 6.06 | 11.22 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 606 | 606 | 8.02 | 20.05 | 74.72 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 280 | 198 | 1.64 | 17.29 | 74.54 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 808 | 315 | 2.22 | 7.60 | 56.17 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 893 | 174 | 1.53 | 4.47 | 13.85 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 609 | 572 | 5.43 | 20.15 | 105.32 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 64 | 0 | 1.39 | 1.75 | 2.75 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 668 | 129 | 1.14 | 3.45 | 64.87 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 45 | 0 | 1.28 | 2.70 | 3.07 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 326 | 0 | 1.37 | 2.52 | 14.32 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 6 | 0 | 7.69 | 7.78 | 7.86 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 102 | 0 | 1.09 | 1.25 | 6.76 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 114 | 0 | 1.52 | 3.78 | 7.85 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 148 | 0 | 1.39 | 1.77 | 4.07 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 50 | 10 | 1.80 | 5.23 | 8.03 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 6 | 6 | 17.27 | 17.69 | 21.61 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 102 | 55 | 1.39 | 14.52 | 51.45 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 114 | 34 | 1.97 | 6.78 | 19.56 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 148 | 17 | 1.42 | 2.32 | 16.00 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 50 | 42 | 6.67 | 14.09 | 22.97 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 15 | 0 | 1.31 | 1.36 | 1.49 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 364 | 73 | 1.59 | 3.92 | 64.64 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 392 | 0 | 1.22 | 1.96 | 17.36 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 18 | 0 | 7.51 | 7.87 | 8.05 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 94 | 0 | 1.11 | 1.24 | 7.70 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 86 | 0 | 1.50 | 2.87 | 6.17 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 159 | 0 | 1.37 | 1.87 | 4.90 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 81 | 12 | 1.87 | 5.68 | 8.06 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 18 | 18 | 12.02 | 18.76 | 30.98 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 94 | 47 | 1.27 | 10.82 | 32.17 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 86 | 13 | 3.02 | 5.83 | 11.50 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 159 | 8 | 1.38 | 2.37 | 11.22 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 81 | 73 | 7.30 | 14.08 | 22.98 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 251 | 0 | 1.30 | 1.44 | 16.12 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 834 | 108 | 1.07 | 2.42 | 63.05 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 221 | 0 | 1.32 | 1.99 | 2.08 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 6 | 0 | 3.20 | 3.81 | 6.65 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 12 | 2 | 5.23 | 7.91 | 8.16 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 90 | 0 | 1.04 | 1.06 | 6.04 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 193 | 6 | 1.55 | 5.86 | 8.12 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 130 | 0 | 1.28 | 2.01 | 4.67 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 52 | 10 | 2.03 | 7.12 | 8.01 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 12 | 8 | 5.53 | 20.05 | 31.30 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 90 | 29 | 1.17 | 1.57 | 51.31 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 193 | 95 | 2.92 | 7.97 | 18.70 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 130 | 2 | 1.29 | 2.33 | 13.10 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 52 | 50 | 7.93 | 13.99 | 22.99 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 294 | 0 | 1.24 | 1.48 | 17.40 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 407 | 46 | 1.50 | 2.21 | 58.89 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 162 | 0 | 1.08 | 2.22 | 13.07 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 43 | 8 | 4.63 | 8.01 | 8.10 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 85 | 0 | 1.03 | 1.05 | 5.59 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 140 | 2 | 1.55 | 4.78 | 8.08 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 138 | 0 | 1.27 | 2.10 | 5.20 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 50 | 10 | 2.07 | 7.35 | 8.01 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 43 | 39 | 6.49 | 15.13 | 34.54 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 85 | 23 | 1.07 | 1.29 | 33.92 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 140 | 45 | 3.19 | 6.49 | 22.92 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 138 | 6 | 1.27 | 2.42 | 9.99 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 50 | 50 | 9.36 | 14.21 | 22.99 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 2 | 0 | 4.06 | 4.54 | 4.54 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 1,188 | 361 | 1.18 | 4.70 | 65.02 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 74 | 0 | 1.14 | 2.59 | 4.04 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 676 | 6 | 1.52 | 2.69 | 23.37 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 600 | 32 | 4.82 | 7.54 | 11.38 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 172 | 4 | 1.38 | 6.32 | 11.44 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 683 | 68 | 1.59 | 4.28 | 8.14 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 932 | 76 | 1.43 | 2.83 | 8.28 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 581 | 30 | 2.07 | 5.74 | 9.61 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 600 | 600 | 8.09 | 27.18 | 86.28 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 172 | 153 | 2.48 | 29.65 | 81.32 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 683 | 369 | 2.62 | 8.08 | 52.04 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 932 | 273 | 1.68 | 6.35 | 28.44 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 581 | 545 | 6.34 | 20.61 | 108.29 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `compute` | 2 | 0 | 5.95 | 7.05 | 7.05 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 571 | 199 | 1.59 | 5.99 | 65.00 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 666 | 4 | 1.20 | 2.17 | 20.06 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 564 | 32 | 5.26 | 7.95 | 11.60 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 198 | 4 | 1.23 | 6.21 | 11.75 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 542 | 52 | 1.49 | 4.50 | 8.13 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 830 | 96 | 1.48 | 2.83 | 8.30 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 410 | 36 | 2.13 | 6.73 | 11.65 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 564 | 564 | 8.07 | 26.88 | 93.32 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 198 | 154 | 1.82 | 29.58 | 107.26 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 542 | 278 | 2.82 | 8.06 | 59.59 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 830 | 159 | 1.72 | 5.91 | 25.81 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 410 | 379 | 5.53 | 20.36 | 101.93 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,062 | 347 | 1.81 | 6.50 | 60.93 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 25 | 0 | 1.97 | 2.77 | 3.54 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 294 | 0 | 2.47 | 2.93 | 5.69 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 135 | 14 | 5.74 | 7.13 | 8.37 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 58 | 0 | 2.13 | 3.26 | 6.68 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 161 | 0 | 1.53 | 3.41 | 5.04 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 463 | 121 | 1.84 | 5.68 | 10.73 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `thermal` | 14 | 0 | 5.08 | 5.61 | 5.99 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 267 | 38 | 1.88 | 3.74 | 8.15 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 135 | 133 | 6.53 | 23.60 | 71.84 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 58 | 12 | 1.79 | 4.81 | 51.61 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 161 | 83 | 1.84 | 8.93 | 64.89 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 463 | 165 | 1.94 | 6.29 | 38.65 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `thermal` | 14 | 14 | 10.50 | 20.16 | 44.49 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 267 | 240 | 6.31 | 16.63 | 116.78 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,266 | 392 | 1.27 | 4.73 | 65.62 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 70 | 0 | 1.23 | 1.81 | 3.93 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 314 | 0 | 2.67 | 2.86 | 12.34 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 484 | 220 | 5.37 | 8.19 | 20.20 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 44 | 38 | 5.70 | 26.54 | 34.76 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 1,056 | 130 | 1.45 | 5.52 | 21.44 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 933 | 208 | 1.55 | 4.16 | 9.04 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 415 | 64 | 1.65 | 5.30 | 15.01 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 484 | 480 | 8.03 | 12.58 | 44.29 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 44 | 40 | 5.60 | 31.46 | 98.85 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 1,056 | 710 | 1.61 | 18.25 | 59.31 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 933 | 306 | 1.61 | 6.31 | 30.52 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 415 | 399 | 6.24 | 18.34 | 113.07 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,185 | 366 | 1.25 | 4.62 | 65.63 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 69 | 0 | 1.23 | 1.82 | 4.62 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 326 | 2 | 2.20 | 2.94 | 15.79 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 483 | 227 | 5.29 | 8.24 | 37.54 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 51 | 50 | 9.72 | 64.06 | 79.79 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 1,125 | 199 | 1.45 | 5.56 | 44.96 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 885 | 180 | 1.54 | 3.72 | 17.20 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 416 | 60 | 1.63 | 5.45 | 38.91 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 483 | 479 | 8.08 | 12.89 | 38.51 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 51 | 49 | 5.13 | 35.55 | 62.29 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 1,125 | 744 | 1.75 | 17.30 | 59.66 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 885 | 272 | 1.60 | 5.96 | 30.68 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 416 | 400 | 7.12 | 18.38 | 113.29 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,600 | 556 | 1.50 | 6.55 | 64.82 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 86 | 0 | 1.55 | 4.19 | 4.76 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 469 | 0 | 2.61 | 3.21 | 4.18 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 649 | 220 | 5.14 | 7.71 | 13.85 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 48 | 42 | 6.77 | 13.26 | 14.40 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 345 | 12 | 1.35 | 3.25 | 8.98 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 934 | 242 | 1.70 | 5.68 | 8.39 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 292 | 60 | 1.98 | 6.92 | 10.91 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 649 | 635 | 7.13 | 25.33 | 107.53 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 48 | 45 | 5.23 | 74.45 | 106.71 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 345 | 229 | 1.86 | 9.93 | 73.66 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 934 | 356 | 1.76 | 7.62 | 33.34 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 292 | 264 | 5.93 | 16.23 | 144.42 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,463 | 473 | 1.38 | 5.98 | 65.13 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 84 | 0 | 1.22 | 4.18 | 4.83 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 423 | 0 | 1.96 | 3.22 | 9.18 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 685 | 308 | 5.52 | 7.93 | 42.63 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 24 | 24 | 41.24 | 45.48 | 52.45 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 517 | 33 | 1.35 | 3.56 | 15.81 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 838 | 204 | 1.64 | 5.30 | 8.39 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 354 | 87 | 1.96 | 7.67 | 23.12 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 685 | 681 | 7.06 | 33.20 | 107.45 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 24 | 24 | 30.10 | 66.33 | 80.42 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 517 | 290 | 1.83 | 8.50 | 77.38 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 838 | 297 | 1.83 | 7.47 | 34.43 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 354 | 316 | 6.69 | 16.28 | 146.75 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,328 | 433 | 1.37 | 5.89 | 65.09 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 79 | 0 | 1.25 | 4.18 | 4.83 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 413 | 2 | 1.96 | 3.23 | 19.58 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 694 | 299 | 5.53 | 7.89 | 87.96 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 34 | 34 | 85.84 | 93.75 | 105.31 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 531 | 60 | 1.35 | 3.66 | 29.56 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 878 | 228 | 1.63 | 5.35 | 21.37 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 371 | 93 | 1.95 | 7.70 | 34.89 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 694 | 692 | 7.68 | 34.30 | 109.24 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 34 | 34 | 16.66 | 40.39 | 44.41 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 531 | 296 | 1.82 | 8.46 | 71.55 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 878 | 312 | 1.81 | 7.46 | 34.58 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 371 | 331 | 6.68 | 16.22 | 147.19 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 669 | 258 | 2.18 | 7.06 | 51.19 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 298 | 0 | 2.55 | 3.08 | 11.63 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 58 | 4 | 6.37 | 7.33 | 8.44 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 128 | 0 | 2.16 | 3.75 | 7.71 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 124 | 0 | 1.53 | 3.58 | 5.36 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 358 | 74 | 1.84 | 5.89 | 10.67 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 166 | 37 | 1.94 | 4.40 | 8.10 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 58 | 56 | 6.74 | 24.68 | 74.64 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 128 | 63 | 1.47 | 8.22 | 83.67 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 124 | 44 | 1.73 | 6.61 | 44.05 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 358 | 104 | 1.96 | 6.30 | 27.07 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 166 | 147 | 7.08 | 17.20 | 117.86 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 2 | 1 | 7.69 | 8.24 | 8.24 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 951 | 324 | 1.45 | 6.29 | 65.56 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 487 | 0 | 1.44 | 3.16 | 7.21 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 566 | 327 | 5.16 | 8.50 | 21.65 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 137 | 122 | 4.19 | 25.94 | 34.76 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 857 | 79 | 1.45 | 6.05 | 22.98 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,006 | 215 | 1.59 | 4.33 | 8.77 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 462 | 136 | 2.07 | 6.98 | 23.54 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 566 | 540 | 5.93 | 16.76 | 60.31 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 137 | 125 | 3.04 | 47.29 | 98.85 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 857 | 526 | 1.64 | 11.75 | 67.90 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,006 | 275 | 1.62 | 5.97 | 27.69 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 462 | 433 | 6.32 | 18.16 | 112.83 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 1 | 1 | 8.56 | 8.56 | 8.56 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 898 | 304 | 1.42 | 6.24 | 65.57 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 491 | 0 | 1.40 | 3.14 | 12.51 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 583 | 365 | 6.10 | 8.53 | 51.52 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 61 | 60 | 7.85 | 59.87 | 79.79 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 934 | 172 | 1.45 | 6.83 | 33.50 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 983 | 201 | 1.58 | 4.20 | 11.22 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 467 | 135 | 2.07 | 7.24 | 33.81 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 583 | 567 | 7.26 | 16.17 | 61.71 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 61 | 58 | 5.33 | 34.91 | 62.29 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 934 | 592 | 1.82 | 12.27 | 68.30 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 983 | 251 | 1.61 | 5.78 | 27.82 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 467 | 439 | 6.83 | 18.43 | 113.17 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 536 | 295 | 2.71 | 8.28 | 63.65 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 727 | 0 | 1.71 | 3.22 | 6.19 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 616 | 392 | 5.88 | 8.52 | 15.28 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 44 | 37 | 7.28 | 13.60 | 15.66 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 285 | 8 | 1.35 | 3.57 | 8.19 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 895 | 248 | 1.72 | 6.21 | 8.39 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 236 | 79 | 2.02 | 7.75 | 13.94 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 616 | 602 | 7.01 | 37.22 | 112.91 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 44 | 40 | 3.46 | 77.99 | 112.92 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 285 | 164 | 1.96 | 10.81 | 56.48 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 895 | 316 | 1.80 | 7.34 | 23.55 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 236 | 205 | 5.72 | 15.33 | 23.00 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 475 | 267 | 3.35 | 8.28 | 64.87 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 724 | 1 | 1.44 | 3.20 | 15.51 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 607 | 420 | 5.59 | 8.68 | 47.58 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 23 | 21 | 7.70 | 48.79 | 53.04 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 410 | 27 | 1.35 | 4.06 | 23.94 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 825 | 206 | 1.69 | 5.49 | 8.39 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 301 | 116 | 1.99 | 8.16 | 34.49 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 607 | 605 | 7.00 | 43.53 | 121.75 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 23 | 21 | 6.22 | 69.42 | 80.73 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 410 | 214 | 1.79 | 8.16 | 83.71 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 825 | 260 | 1.88 | 7.07 | 24.77 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 301 | 267 | 6.63 | 16.18 | 147.17 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 1 | 1 | 8.39 | 8.39 | 8.39 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 483 | 286 | 3.00 | 8.35 | 65.08 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 796 | 1 | 1.45 | 3.19 | 19.71 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 675 | 466 | 5.59 | 8.75 | 94.57 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 29 | 28 | 9.50 | 96.61 | 105.31 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 445 | 54 | 1.35 | 4.48 | 30.64 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 872 | 238 | 1.68 | 5.88 | 14.64 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 313 | 128 | 1.99 | 8.18 | 40.26 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 675 | 673 | 7.06 | 42.33 | 122.99 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 29 | 29 | 8.74 | 42.53 | 45.12 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 445 | 241 | 1.92 | 10.08 | 85.62 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 872 | 280 | 1.87 | 7.19 | 24.98 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 313 | 277 | 6.09 | 16.10 | 147.74 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,101 | 335 | 1.38 | 5.30 | 65.31 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 45 | 0 | 1.23 | 2.23 | 3.99 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 287 | 0 | 2.34 | 2.81 | 4.09 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 220 | 98 | 6.20 | 8.18 | 8.81 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 68 | 0 | 3.17 | 8.07 | 8.70 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 629 | 5 | 1.46 | 4.42 | 13.70 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 944 | 226 | 1.54 | 4.93 | 11.10 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 397 | 39 | 1.74 | 4.34 | 12.11 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 220 | 220 | 8.23 | 12.64 | 45.17 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 68 | 54 | 2.45 | 23.22 | 41.44 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 629 | 488 | 1.75 | 27.39 | 67.87 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 944 | 337 | 1.62 | 6.87 | 41.22 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 397 | 370 | 6.25 | 21.77 | 111.76 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,131 | 400 | 1.81 | 6.92 | 59.79 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 41 | 0 | 3.35 | 4.13 | 5.84 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 314 | 0 | 2.84 | 3.14 | 6.36 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 106 | 15 | 6.30 | 7.71 | 8.60 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 44 | 10 | 3.20 | 5.16 | 8.56 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 133 | 0 | 1.41 | 2.81 | 6.64 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 318 | 78 | 1.92 | 5.98 | 8.39 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 197 | 21 | 1.83 | 4.63 | 8.17 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 106 | 104 | 7.51 | 49.88 | 97.74 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 44 | 30 | 3.62 | 16.68 | 139.08 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 133 | 51 | 2.00 | 6.24 | 68.07 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 318 | 111 | 2.14 | 7.14 | 33.01 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 197 | 166 | 5.63 | 13.48 | 168.35 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 853 | 294 | 1.63 | 6.30 | 64.63 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 406 | 0 | 1.77 | 3.16 | 5.83 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 400 | 137 | 6.71 | 8.60 | 10.10 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 103 | 16 | 3.31 | 8.16 | 10.62 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 319 | 2 | 1.46 | 3.68 | 13.69 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 965 | 223 | 1.59 | 5.30 | 11.35 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 363 | 41 | 2.11 | 5.98 | 8.82 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 400 | 400 | 8.23 | 40.41 | 66.88 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 103 | 77 | 1.80 | 15.04 | 72.28 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 319 | 215 | 1.82 | 22.08 | 54.51 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 965 | 316 | 1.62 | 6.71 | 26.91 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 363 | 340 | 5.38 | 48.97 | 111.15 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 568 | 248 | 2.03 | 7.82 | 50.89 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 399 | 10 | 2.71 | 3.49 | 12.75 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 54 | 11 | 6.47 | 7.94 | 9.23 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 54 | 1 | 2.85 | 3.86 | 8.66 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 83 | 0 | 1.42 | 2.15 | 4.63 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 161 | 18 | 1.93 | 4.50 | 8.32 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 68 | 13 | 1.90 | 4.80 | 8.18 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 54 | 50 | 6.70 | 38.18 | 91.77 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 54 | 36 | 2.84 | 9.26 | 126.66 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 83 | 26 | 2.05 | 4.52 | 31.62 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 161 | 20 | 2.19 | 6.39 | 9.57 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 68 | 58 | 6.53 | 12.59 | 23.00 |

## Per model, per context, per batch and per design class

Each row is that class's **fastest** feasible design at that batch, read against the iso-area GPU comparator the published study already chose for it. The `densest` pick of every class is in `analytical.json` beside it.

**The ROM-versus-GPU ratio under speculation is `T_cycle(GPU) / T_cycle(ROM)` and carries no `tau` at all.** The acceptance length is a property of the model and its drafter, not of the machine, so it is the same on both sides and cancels out of the ratio. Every movement in the last column is therefore a machine effect and nothing else.

### `n5_vs_b200-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,228.3 | 665.8-665.8 | 39.26 | **no** | `b200_sxm-x93-nvl72-hybrid` | 1,056.7 | 4,330.1-4,330.1 | 1.22 | yes | 4.948x | 0.154x | 0.031x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,338.7 | 699.2-699.2 | 38.18 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,053.8 | 4,301.3-4,301.3 | 1.22 | yes | 5.066x | 0.163x | 0.032x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,228.3 | 665.8-665.8 | 39.26 | **no** | `b200_sxm-x93-nvl72-hybrid` | 1,056.7 | 4,330.1-4,330.1 | 1.22 | yes | 4.948x | 0.154x | 0.031x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,338.7 | 699.2-699.2 | 38.18 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,053.8 | 4,301.3-4,301.3 | 1.22 | yes | 5.066x | 0.163x | 0.032x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,228.3 | 665.8-665.8 | 39.26 | **no** | `b200_sxm-x93-nvl72-hybrid` | 1,032.2 | 3,903.0-3,903.0 | 1.32 | yes | 5.065x | 0.171x | 0.034x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,338.7 | 699.2-699.2 | 38.18 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,028.4 | 3,870.4-3,870.4 | 1.33 | yes | 5.191x | 0.181x | 0.035x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,228.3 | 665.8-665.8 | 39.26 | **no** | `b200_sxm-x93-nvl72-hybrid` | 988.2 | 3,512.1-3,512.1 | 1.41 | yes | 5.291x | 0.190x | 0.036x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,338.7 | 699.2-699.2 | 38.18 | **no** | `b200_sxm-x87-nvl72-hybrid` | 982.2 | 3,465.5-3,465.5 | 1.42 | yes | 5.436x | 0.202x | 0.037x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,228.3 | 665.8-665.8 | 39.26 | **no** | `b200_sxm-x93-nvl72-hybrid` | 925.7 | 2,920.4-2,920.4 | 1.58 | yes | 5.648x | 0.228x | 0.040x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,338.7 | 699.2-699.2 | 38.18 | **no** | `b200_sxm-x87-nvl72-hybrid` | 922.5 | 2,881.7-2,881.7 | 1.60 | yes | 5.787x | 0.243x | 0.042x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,087.5 | 339.7-339.7 | 74.88 | **no** | `b200_sxm-x93-nvl72-hybrid` | 837.4 | 2,368.8-2,368.8 | 1.77 | yes | 6.075x | 0.143x | 0.024x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,204.7 | 845.0-845.0 | 30.80 | **no** | `b200_sxm-x231-nvl72-hybrid` | 932.5 | 2,950.8-2,950.8 | 1.58 | yes | 5.581x | 0.286x | 0.051x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 4,850.1 | 405.0-405.0 | 59.88 | **no** | `b200_sxm-x134-nvl72-hybrid` | 777.7 | 1,997.4-1,997.4 | 1.95 | yes | 6.237x | 0.203x | 0.033x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,201.5 | 840.4-840.4 | 30.95 | **no** | `b200_sxm-x347-nvl72-hybrid` | 886.5 | 2,645.1-2,645.1 | 1.68 | yes | 5.867x | 0.318x | 0.054x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 3,322.9 | 177.7-177.7 | 93.48 | **no** | `b200_sxm-x179-nvl72-hybrid` | 526.9 | 1,022.9-1,022.9 | 2.58 | yes | 6.306x | 0.174x | 0.028x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,179.1 | 422.8-422.8 | 49.42 | **no** | `b200_sxm-x347-nvl72-hybrid` | 664.4 | 1,482.1-1,482.1 | 2.24 | yes | 6.290x | 0.285x | 0.045x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 1,640.8 | 86.8-86.8 | 94.49 | **no** | `b200_sxm-x179-nvl72-hybrid` | 265.4 | 470.7-470.7 | 2.82 | yes | 6.183x | 0.184x | 0.030x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,147.3 | 107.6-107.6 | 99.83 | **no** | `b200_sxm-x347-nvl72-hybrid` | 355.2 | 735.8-735.8 | 2.41 | yes | 6.045x | 0.146x | 0.024x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 558.9 | 41.2-41.2 | 67.83 | **no** | `b200_sxm-x179-nvl72-hybrid` | 142.2 | 156.5-156.5 | 4.54 | yes | 3.929x | 0.263x | 0.067x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 685.8 | 85.1-85.1 | 40.30 | **no** | `b200_sxm-x347-nvl72-hybrid` | 172.6 | 206.8-206.8 | 4.17 | yes | 3.972x | 0.411x | 0.104x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.024x to 0.104x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 469.3-469.3 | 52.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 1,056.6-1,056.6 | 2.06 | yes | 11.390x | 0.444x | 0.039x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,055.1 | 533.3-533.3 | 47.40 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 1,104.2-1,104.2 | 2.00 | yes | 11.427x | 0.483x | 0.042x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 469.3-469.3 | 52.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 1,056.6-1,056.6 | 2.06 | yes | 11.390x | 0.444x | 0.039x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,055.1 | 533.3-533.3 | 47.40 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 1,104.2-1,104.2 | 2.00 | yes | 11.427x | 0.483x | 0.042x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 469.3-469.3 | 52.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 1,056.6-1,056.6 | 2.06 | yes | 11.390x | 0.444x | 0.039x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,055.1 | 533.3-533.3 | 47.40 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 1,104.2-1,104.2 | 2.00 | yes | 11.427x | 0.483x | 0.042x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 469.3-469.3 | 52.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 1,056.6-1,056.6 | 2.06 | yes | 11.390x | 0.444x | 0.039x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,055.1 | 533.3-533.3 | 47.40 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 1,104.2-1,104.2 | 2.00 | yes | 11.427x | 0.483x | 0.042x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 469.3-469.3 | 52.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 1,056.6-1,056.6 | 2.06 | yes | 11.390x | 0.444x | 0.039x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,055.1 | 533.3-533.3 | 47.40 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 1,104.2-1,104.2 | 2.00 | yes | 11.427x | 0.483x | 0.042x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 469.3-469.3 | 52.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 1,056.6-1,056.6 | 2.06 | yes | 11.390x | 0.444x | 0.039x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4,931.7 | 615.8-615.8 | 40.04 | **no** | `a100_sxm_80gb-x448-hybrid` | 433.5 | 974.5-974.5 | 2.22 | yes | 11.378x | 0.632x | 0.056x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,669.0 | 238.2-238.2 | 98.00 | **no** | `a100_sxm_80gb-x258-hybrid` | 375.9 | 778.6-778.6 | 2.41 | yes | 12.420x | 0.306x | 0.025x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,927.4 | 612.4-612.4 | 40.23 | **no** | `a100_sxm_80gb-x672-hybrid` | 433.5 | 909.2-909.2 | 2.38 | yes | 11.368x | 0.674x | 0.059x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 2,994.5 | 93.1-93.1 | 160.87 | **no** | `a100_sxm_80gb-x335-hybrid` | 234.9 | 390.3-390.3 | 3.01 | yes | 12.746x | 0.238x | 0.019x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,673.9 | 306.3-306.3 | 59.97 | **no** | `a100_sxm_80gb-x672-hybrid` | 322.5 | 544.3-544.3 | 2.96 | yes | 11.392x | 0.563x | 0.049x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,194.1 | 45.2-45.2 | 132.17 | **no** | `a100_sxm_80gb-x337-hybrid` | 98.0 | 179.9-179.9 | 2.72 | yes | 12.184x | 0.251x | 0.021x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,680.0 | 91.2-91.2 | 92.07 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.6 | 233.7-233.7 | 3.33 | yes | 10.797x | 0.390x | 0.036x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 331.5 | 39.0-39.0 | 42.48 | **no** | `a100_sxm_80gb-x337-hybrid` | 37.3 | 49.3-49.3 | 3.79 | yes | 8.878x | 0.792x | 0.089x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 606.9 | 44.2-44.2 | 68.71 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.3 | 116.6-116.6 | 2.54 | yes | 10.233x | 0.379x | 0.037x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.019x to 0.089x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,977.8 | 530.7-530.7 | 46.90 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,064.7 | 4,411.9-4,411.9 | 1.21 | yes | 4.675x | 0.120x | 0.026x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,818.5 | 844.0-844.0 | 28.55 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,071.3 | 4,468.0-4,468.0 | 1.20 | yes | 4.498x | 0.189x | 0.042x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,977.8 | 530.7-530.7 | 46.90 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,064.7 | 4,411.9-4,411.9 | 1.21 | yes | 4.675x | 0.120x | 0.026x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,818.5 | 844.0-844.0 | 28.55 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,071.3 | 4,468.0-4,468.0 | 1.20 | yes | 4.498x | 0.189x | 0.042x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,977.8 | 530.7-530.7 | 46.90 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,042.0 | 3,994.2-3,994.2 | 1.30 | yes | 4.777x | 0.133x | 0.028x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,818.5 | 844.0-844.0 | 28.55 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,050.4 | 4,053.0-4,053.0 | 1.30 | yes | 4.587x | 0.208x | 0.045x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,977.8 | 530.7-530.7 | 46.90 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,000.0 | 3,382.7-3,382.7 | 1.48 | yes | 4.978x | 0.157x | 0.032x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,818.5 | 844.0-844.0 | 28.55 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,012.0 | 3,622.1-3,622.1 | 1.40 | yes | 4.761x | 0.233x | 0.049x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,977.8 | 530.7-530.7 | 46.90 | **no** | `b200_sxm-x116-nvl72-hybrid` | 941.9 | 3,083.0-3,083.0 | 1.53 | yes | 5.285x | 0.172x | 0.033x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,818.5 | 844.0-844.0 | 28.55 | **no** | `b200_sxm-x144-nvl72-hybrid` | 958.0 | 3,235.6-3,235.6 | 1.48 | yes | 5.030x | 0.261x | 0.052x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 4,903.9 | 470.3-470.3 | 52.14 | **no** | `b200_sxm-x134-nvl72-hybrid` | 880.3 | 2,637.6-2,637.6 | 1.67 | yes | 5.571x | 0.178x | 0.032x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,675.1 | 1,547.5-1,547.5 | 15.10 | **no** | `b200_sxm-x347-nvl72-hybrid` | 957.9 | 3,145.8-3,145.8 | 1.52 | yes | 4.881x | 0.492x | 0.101x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 4,584.6 | 238.8-238.8 | 96.01 | **no** | `b200_sxm-x134-nvl72-hybrid` | 769.2 | 1,983.9-1,983.9 | 1.94 | yes | 5.960x | 0.120x | 0.020x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,504.6 | 818.9-818.9 | 27.50 | **no** | `b200_sxm-x347-nvl72-hybrid` | 882.2 | 2,636.5-2,636.5 | 1.67 | yes | 5.106x | 0.311x | 0.061x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 3,058.6 | 174.8-174.8 | 87.47 | **no** | `b200_sxm-x179-nvl72-hybrid` | 515.4 | 1,012.3-1,012.3 | 2.55 | yes | 5.934x | 0.173x | 0.029x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,071.9 | 409.1-409.1 | 37.55 | **no** | `b200_sxm-x347-nvl72-hybrid` | 654.9 | 1,470.6-1,470.6 | 2.23 | yes | 4.691x | 0.278x | 0.059x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 1,269.4 | 44.2-44.2 | 143.71 | **no** | `b200_sxm-x179-nvl72-hybrid` | 254.0 | 463.1-463.1 | 2.74 | yes | 4.998x | 0.095x | 0.019x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,259.4 | 46.8-46.8 | 134.63 | **no** | `b200_sxm-x347-nvl72-hybrid` | 344.5 | 726.0-726.0 | 2.37 | yes | 3.655x | 0.064x | 0.018x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 363.9 | 38.7-38.7 | 46.97 | **no** | `b200_sxm-x179-nvl72-hybrid` | 129.7 | 153.3-153.3 | 4.23 | yes | 2.805x | 0.253x | 0.090x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 359.4 | 23.0-23.0 | 78.26 | **no** | `b200_sxm-x347-nvl72-hybrid` | 162.8 | 203.9-203.9 | 3.99 | yes | 2.208x | 0.113x | 0.051x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.018x to 0.101x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,695.2 | 753.2-753.2 | 31.17 | **no** | `a100_sxm_80gb-x312-hybrid` | 431.5 | 1,022.7-1,022.7 | 2.11 | yes | 10.882x | 0.736x | 0.068x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 4,457.6 | 1,269.8-1,269.8 | 17.55 | **no** | `a100_sxm_80gb-x168-hybrid` | 444.9 | 1,149.4-1,149.4 | 1.94 | yes | 10.020x | 1.105x | 0.110x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,695.2 | 753.2-753.2 | 31.17 | **no** | `a100_sxm_80gb-x312-hybrid` | 431.5 | 1,022.7-1,022.7 | 2.11 | yes | 10.882x | 0.736x | 0.068x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,256.3 | 699.4-699.4 | 30.43 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 9.881x | 0.771x | 0.078x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,695.2 | 753.2-753.2 | 31.17 | **no** | `a100_sxm_80gb-x312-hybrid` | 431.5 | 1,022.7-1,022.7 | 2.11 | yes | 10.882x | 0.736x | 0.068x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,256.3 | 699.4-699.4 | 30.43 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 9.881x | 0.771x | 0.078x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,695.2 | 753.2-753.2 | 31.17 | **no** | `a100_sxm_80gb-x312-hybrid` | 431.5 | 1,022.7-1,022.7 | 2.11 | yes | 10.882x | 0.736x | 0.068x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,256.3 | 699.4-699.4 | 30.43 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 9.881x | 0.771x | 0.078x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,695.2 | 753.2-753.2 | 31.17 | **no** | `a100_sxm_80gb-x312-hybrid` | 431.5 | 1,022.7-1,022.7 | 2.11 | yes | 10.882x | 0.736x | 0.068x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,256.3 | 699.4-699.4 | 30.43 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 9.881x | 0.771x | 0.078x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 4,658.6 | 362.2-362.2 | 64.31 | **no** | `a100_sxm_80gb-x337-hybrid` | 427.3 | 998.1-998.1 | 2.14 | yes | 10.901x | 0.363x | 0.033x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,142.7 | 367.5-367.5 | 56.36 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 9.618x | 0.405x | 0.042x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 4,239.1 | 185.4-185.4 | 114.31 | **no** | `a100_sxm_80gb-x335-hybrid` | 394.2 | 842.1-842.1 | 2.34 | yes | 10.753x | 0.220x | 0.020x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,559.7 | 364.0-364.0 | 48.89 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 8.264x | 0.402x | 0.049x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 2,465.2 | 91.3-91.3 | 134.94 | **no** | `a100_sxm_80gb-x337-hybrid` | 230.7 | 389.7-389.7 | 2.96 | yes | 10.684x | 0.234x | 0.022x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,875.7 | 93.6-93.6 | 100.18 | **no** | `a100_sxm_80gb-x672-hybrid` | 318.0 | 541.4-541.4 | 2.94 | yes | 5.899x | 0.173x | 0.029x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 833.5 | 44.0-44.0 | 94.67 | **no** | `a100_sxm_80gb-x337-hybrid` | 94.7 | 177.5-177.5 | 2.67 | yes | 8.799x | 0.248x | 0.028x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 597.6 | 23.6-23.6 | 126.73 | **no** | `a100_sxm_80gb-x672-hybrid` | 151.4 | 231.7-231.7 | 3.27 | yes | 3.947x | 0.102x | 0.026x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 223.3 | 35.7-35.7 | 31.23 | **no** | `a100_sxm_80gb-x337-hybrid` | 35.5 | 45.0-45.0 | 3.94 | yes | 6.295x | 0.795x | 0.126x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 156.6 | 22.5-22.5 | 34.78 | **no** | `a100_sxm_80gb-x672-hybrid` | 56.9 | 114.6-114.6 | 2.48 | yes | 2.752x | 0.196x | 0.071x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.020x to 0.126x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,280.8 | 696.2-696.2 | 37.93 | **no** | `b200_sxm-x90-nvl72-hybrid` | 1,055.5 | 4,316.9-4,316.9 | 1.22 | yes | 5.003x | 0.161x | 0.032x |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,479.0 | 703.6-703.6 | 38.93 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,054.0 | 4,302.0-4,302.0 | 1.23 | yes | 5.198x | 0.164x | 0.031x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,280.8 | 696.2-696.2 | 37.93 | **no** | `b200_sxm-x90-nvl72-hybrid` | 1,055.5 | 4,316.9-4,316.9 | 1.22 | yes | 5.003x | 0.161x | 0.032x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,479.0 | 703.6-703.6 | 38.93 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,054.0 | 4,302.0-4,302.0 | 1.23 | yes | 5.198x | 0.164x | 0.031x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,280.8 | 696.2-696.2 | 37.93 | **no** | `b200_sxm-x90-nvl72-hybrid` | 1,030.7 | 3,888.4-3,888.4 | 1.33 | yes | 5.124x | 0.179x | 0.035x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,479.0 | 703.6-703.6 | 38.93 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,028.8 | 3,871.7-3,871.7 | 1.33 | yes | 5.326x | 0.182x | 0.034x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,280.8 | 696.2-696.2 | 37.93 | **no** | `b200_sxm-x90-nvl72-hybrid` | 985.9 | 3,491.5-3,491.5 | 1.41 | yes | 5.356x | 0.199x | 0.037x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,479.0 | 703.6-703.6 | 38.93 | **no** | `b200_sxm-x87-nvl72-hybrid` | 982.9 | 3,467.5-3,467.5 | 1.42 | yes | 5.575x | 0.203x | 0.036x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,280.8 | 696.2-696.2 | 37.93 | **no** | `b200_sxm-x90-nvl72-hybrid` | 919.6 | 2,880.1-2,880.1 | 1.60 | yes | 5.743x | 0.242x | 0.042x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,479.0 | 703.6-703.6 | 38.93 | **no** | `b200_sxm-x87-nvl72-hybrid` | 923.7 | 2,884.4-2,884.4 | 1.60 | yes | 5.932x | 0.244x | 0.041x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,211.3 | 355.5-355.5 | 73.29 | **no** | `b200_sxm-x90-nvl72-hybrid` | 830.9 | 2,331.2-2,331.2 | 1.78 | yes | 6.272x | 0.153x | 0.024x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,349.8 | 851.9-851.9 | 31.40 | **no** | `b200_sxm-x231-nvl72-hybrid` | 933.4 | 2,952.9-2,952.9 | 1.58 | yes | 5.731x | 0.288x | 0.050x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 5,024.6 | 407.0-407.0 | 61.73 | **no** | `b200_sxm-x134-nvl72-hybrid` | 779.9 | 2,000.9-2,000.9 | 1.95 | yes | 6.443x | 0.203x | 0.032x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,346.7 | 847.1-847.1 | 31.56 | **no** | `b200_sxm-x347-nvl72-hybrid` | 887.6 | 2,647.3-2,647.3 | 1.68 | yes | 6.024x | 0.320x | 0.053x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 3,402.3 | 202.1-202.1 | 84.18 | **no** | `b200_sxm-x179-nvl72-hybrid` | 529.9 | 1,025.7-1,025.7 | 2.58 | yes | 6.420x | 0.197x | 0.031x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,457.5 | 427.1-427.1 | 52.19 | **no** | `b200_sxm-x347-nvl72-hybrid` | 666.9 | 1,485.1-1,485.1 | 2.25 | yes | 6.684x | 0.288x | 0.043x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,713.1 | 90.2-90.2 | 94.91 | **no** | `b200_sxm-x173-nvl72-hybrid` | 265.7 | 451.9-451.9 | 2.94 | yes | 6.447x | 0.200x | 0.031x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,433.4 | 108.5-108.5 | 112.14 | **no** | `b200_sxm-x347-nvl72-hybrid` | 358.1 | 738.3-738.3 | 2.43 | yes | 6.795x | 0.147x | 0.022x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 620.7 | 43.0-43.0 | 72.16 | **no** | `b200_sxm-x173-nvl72-hybrid` | 142.9 | 146.5-146.5 | 4.88 | yes | 4.344x | 0.294x | 0.068x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 769.7 | 93.5-93.5 | 41.16 | **no** | `b200_sxm-x347-nvl72-hybrid` | 175.3 | 207.6-207.6 | 4.22 | yes | 4.389x | 0.450x | 0.103x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.022x to 0.103x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 5,026.9 | 499.4-499.4 | 50.33 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 1,075.1-1,075.1 | 2.04 | yes | 11.474x | 0.465x | 0.040x |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,233.2 | 536.6-536.6 | 48.76 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 1,105.3-1,105.3 | 2.00 | yes | 11.810x | 0.485x | 0.041x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 5,026.9 | 499.4-499.4 | 50.33 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 1,075.1-1,075.1 | 2.04 | yes | 11.474x | 0.465x | 0.040x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,233.2 | 536.6-536.6 | 48.76 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 1,105.3-1,105.3 | 2.00 | yes | 11.810x | 0.485x | 0.041x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 5,026.9 | 499.4-499.4 | 50.33 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 1,075.1-1,075.1 | 2.04 | yes | 11.474x | 0.465x | 0.040x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,233.2 | 536.6-536.6 | 48.76 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 1,105.3-1,105.3 | 2.00 | yes | 11.810x | 0.485x | 0.041x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 5,026.9 | 499.4-499.4 | 50.33 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 1,075.1-1,075.1 | 2.04 | yes | 11.474x | 0.465x | 0.040x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,233.2 | 536.6-536.6 | 48.76 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 1,105.3-1,105.3 | 2.00 | yes | 11.810x | 0.485x | 0.041x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 5,026.9 | 499.4-499.4 | 50.33 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 1,075.1-1,075.1 | 2.04 | yes | 11.474x | 0.465x | 0.040x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,233.2 | 536.6-536.6 | 48.76 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 1,105.3-1,105.3 | 2.00 | yes | 11.810x | 0.485x | 0.041x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342-romfill` | 4,869.3 | 576.0-576.0 | 42.27 | **no** | `a100_sxm_80gb-x337-hybrid` | 430.8 | 1,002.3-1,002.3 | 2.15 | yes | 11.304x | 0.575x | 0.051x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,116.8 | 620.6-620.6 | 41.23 | **no** | `a100_sxm_80gb-x448-hybrid` | 434.2 | 975.3-975.3 | 2.23 | yes | 11.786x | 0.636x | 0.054x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 4,654.3 | 253.4-253.4 | 91.83 | **no** | `a100_sxm_80gb-x244-hybrid` | 373.1 | 768.0-768.0 | 2.43 | yes | 12.475x | 0.330x | 0.026x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,112.2 | 617.0-617.0 | 41.42 | **no** | `a100_sxm_80gb-x672-hybrid` | 434.2 | 909.9-909.9 | 2.39 | yes | 11.775x | 0.678x | 0.058x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,166.8 | 178.9-178.9 | 88.50 | **no** | `a100_sxm_80gb-x337-hybrid` | 236.8 | 393.4-393.4 | 3.01 | yes | 13.373x | 0.455x | 0.034x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,973.2 | 309.4-309.4 | 64.21 | **no** | `a100_sxm_80gb-x672-hybrid` | 323.7 | 545.1-545.1 | 2.97 | yes | 12.275x | 0.568x | 0.046x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,344.0 | 45.5-45.5 | 147.75 | **no** | `a100_sxm_80gb-x337-hybrid` | 98.9 | 180.5-180.5 | 2.74 | yes | 13.592x | 0.252x | 0.019x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,899.7 | 78.2-78.2 | 121.39 | **no** | `a100_sxm_80gb-x672-hybrid` | 156.7 | 234.3-234.3 | 3.34 | yes | 12.123x | 0.334x | 0.028x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 379.6 | 40.0-40.0 | 47.47 | **no** | `a100_sxm_80gb-x337-hybrid` | 37.8 | 50.5-50.5 | 3.75 | yes | 10.028x | 0.791x | 0.079x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 721.6 | 83.1-83.1 | 43.39 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.9 | 117.1-117.1 | 2.56 | yes | 12.037x | 0.710x | 0.059x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.019x to 0.079x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,065.2 | 4,405.7-4,405.7 | 1.21 | yes | 5.043x | 0.276x | 0.055x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 5,419.7 | 1,222.8-1,222.8 | 22.16 | **no** | `b200_sxm-x347-nvl72-hybrid` | 1,060.6 | 4,308.0-4,308.0 | 1.23 | yes | 5.110x | 0.284x | 0.056x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,042.5 | 4,008.3-4,008.3 | 1.30 | yes | 5.152x | 0.304x | 0.059x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 1,289.0-1,289.0 | 20.83 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,050.0 | 4,069.0-4,069.0 | 1.29 | yes | 5.114x | 0.317x | 0.062x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,000.6 | 3,408.9-3,408.9 | 1.47 | yes | 5.368x | 0.357x | 0.067x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 1,289.0-1,289.0 | 20.83 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,010.6 | 3,475.6-3,475.6 | 1.45 | yes | 5.314x | 0.371x | 0.070x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 927.9 | 2,669.7-2,669.7 | 1.74 | yes | 5.788x | 0.456x | 0.079x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 1,289.0-1,289.0 | 20.83 | **no** | `b200_sxm-x58-nvl72-tensor` | 941.7 | 2,727.3-2,727.3 | 1.73 | yes | 5.702x | 0.473x | 0.083x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,361.8 | 632.2-632.2 | 42.40 | **no** | `b200_sxm-x49-hybrid` | 830.0 | 2,245.2-2,245.2 | 1.85 | yes | 6.460x | 0.282x | 0.044x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5,363.4 | 1,315.6-1,315.6 | 20.38 | **no** | `b200_sxm-x87-nvl72-hybrid` | 922.5 | 2,881.7-2,881.7 | 1.60 | yes | 5.814x | 0.457x | 0.079x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 5,209.0 | 657.3-657.3 | 39.62 | **no** | `b200_sxm-x110-nvl72-hybrid` | 862.1 | 2,508.4-2,508.4 | 1.72 | yes | 6.042x | 0.262x | 0.043x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,337.0 | 1,350.1-1,350.1 | 19.77 | **no** | `b200_sxm-x231-nvl72-hybrid` | 932.5 | 2,950.8-2,950.8 | 1.58 | yes | 5.723x | 0.458x | 0.080x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,209.0 | 657.3-657.3 | 39.62 | **no** | `b200_sxm-x173-nvl72-hybrid` | 815.7 | 2,259.0-2,259.0 | 1.81 | yes | 6.386x | 0.291x | 0.046x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,334.9 | 1,342.9-1,342.9 | 19.86 | **no** | `b200_sxm-x347-nvl72-hybrid` | 886.5 | 2,645.1-2,645.1 | 1.68 | yes | 6.018x | 0.508x | 0.084x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,572.7 | 325.7-325.7 | 54.84 | **no** | `b200_sxm-x173-nvl72-hybrid` | 519.7 | 1,013.7-1,013.7 | 2.56 | yes | 6.875x | 0.321x | 0.047x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,536.9 | 684.4-684.4 | 33.15 | **no** | `b200_sxm-x347-nvl72-hybrid` | 664.4 | 1,482.1-1,482.1 | 2.24 | yes | 6.828x | 0.462x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,474.7 | 152.9-152.9 | 48.23 | **no** | `b200_sxm-x173-nvl72-hybrid` | 262.6 | 450.0-450.0 | 2.92 | yes | 5.616x | 0.340x | 0.060x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,637.2 | 175.8-175.8 | 74.99 | **no** | `b200_sxm-x347-nvl72-hybrid` | 355.2 | 735.8-735.8 | 2.41 | yes | 7.424x | 0.239x | 0.032x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 434.2 | 127.1-127.1 | 17.08 | **no** | `b200_sxm-x173-nvl72-hybrid` | 139.3 | 145.7-145.7 | 4.78 | yes | 3.117x | 0.873x | 0.280x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 872.6 | 144.5-144.5 | 30.20 | **no** | `b200_sxm-x347-nvl72-hybrid` | 172.6 | 206.8-206.8 | 4.17 | yes | 5.054x | 0.699x | 0.138x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.032x to 0.280x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 445.6 | 1,157.5-1,157.5 | 1.92 | yes | 11.569x | 0.758x | 0.066x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 5,184.8 | 863.6-863.6 | 30.02 | **no** | `a100_sxm_80gb-x672-hybrid` | 433.5 | 909.2-909.2 | 2.38 | yes | 11.962x | 0.950x | 0.079x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 445.6 | 1,157.5-1,157.5 | 1.92 | yes | 11.569x | 0.758x | 0.066x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.0 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.381x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 445.6 | 1,157.5-1,157.5 | 1.92 | yes | 11.569x | 0.758x | 0.066x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.0 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.381x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 445.6 | 1,157.5-1,157.5 | 1.92 | yes | 11.569x | 0.758x | 0.066x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.0 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.381x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 445.6 | 1,157.5-1,157.5 | 1.92 | yes | 11.569x | 0.758x | 0.066x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.0 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.381x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,021.1 | 916.5-916.5 | 27.39 | **no** | `a100_sxm_80gb-x272-hybrid` | 437.9 | 1,060.7-1,060.7 | 2.06 | yes | 11.467x | 0.864x | 0.075x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,079.3 | 992.0-992.0 | 25.60 | **no** | `a100_sxm_80gb-x448-hybrid` | 433.5 | 974.5-974.5 | 2.22 | yes | 11.718x | 1.018x | 0.087x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,830.1 | 478.9-478.9 | 50.43 | **no** | `a100_sxm_80gb-x335-hybrid` | 397.7 | 845.7-845.7 | 2.35 | yes | 12.145x | 0.566x | 0.047x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,076.0 | 986.6-986.6 | 25.72 | **no** | `a100_sxm_80gb-x672-hybrid` | 433.5 | 909.2-909.2 | 2.38 | yes | 11.711x | 1.085x | 0.093x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,068.8 | 236.2-236.2 | 64.96 | **no** | `a100_sxm_80gb-x335-hybrid` | 234.9 | 390.3-390.3 | 3.01 | yes | 13.062x | 0.605x | 0.046x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,987.7 | 497.6-497.6 | 40.07 | **no** | `a100_sxm_80gb-x672-hybrid` | 322.5 | 544.3-544.3 | 2.96 | yes | 12.365x | 0.914x | 0.074x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 1,176.6 | 163.6-163.6 | 35.96 | **no** | `a100_sxm_80gb-x335-hybrid` | 97.7 | 179.3-179.3 | 2.72 | yes | 12.048x | 0.912x | 0.076x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,977.6 | 127.0-127.0 | 77.84 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.6 | 233.7-233.7 | 3.33 | yes | 12.710x | 0.543x | 0.043x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 428.3 | 114.1-114.1 | 18.76 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.2 | 48.4-48.4 | 3.85 | yes | 11.499x | 2.358x | 0.205x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 602.7 | 104.5-104.5 | 28.84 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.3 | 116.6-116.6 | 2.54 | yes | 10.162x | 0.896x | 0.088x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.043x to 0.205x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 5,145.7 | 1,045.1-1,045.1 | 24.62 | **no** | `b200_sxm-x57-nvl72-tensor` | 1,070.0 | 4,453.1-4,453.1 | 1.20 | yes | 4.809x | 0.235x | 0.049x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 5,125.9 | 1,195.8-1,195.8 | 21.43 | **no** | `b200_sxm-x347-nvl72-hybrid` | 1,060.1 | 4,306.3-4,306.3 | 1.23 | yes | 4.835x | 0.278x | 0.057x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 5,145.7 | 1,045.1-1,045.1 | 24.62 | **no** | `b200_sxm-x57-nvl72-tensor` | 1,048.2 | 4,059.4-4,059.4 | 1.29 | yes | 4.909x | 0.257x | 0.052x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,830.4 | 848.3-848.3 | 28.47 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,071.3 | 4,468.0-4,468.0 | 1.20 | yes | 4.509x | 0.190x | 0.042x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 5,145.7 | 1,045.1-1,045.1 | 24.62 | **no** | `b200_sxm-x57-nvl72-tensor` | 1,007.6 | 3,463.6-3,463.6 | 1.45 | yes | 5.107x | 0.302x | 0.059x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,830.4 | 848.3-848.3 | 28.47 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,050.4 | 4,053.0-4,053.0 | 1.30 | yes | 4.599x | 0.209x | 0.046x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 5,145.7 | 1,045.1-1,045.1 | 24.62 | **no** | `b200_sxm-x57-nvl72-tensor` | 936.7 | 2,714.9-2,714.9 | 1.73 | yes | 5.493x | 0.385x | 0.070x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,830.4 | 848.3-848.3 | 28.47 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,012.0 | 3,622.1-3,622.1 | 1.40 | yes | 4.773x | 0.234x | 0.049x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 4,966.0 | 1,194.7-1,194.7 | 20.78 | **no** | `b200_sxm-x83-nvl72-hybrid` | 907.2 | 2,809.7-2,809.7 | 1.61 | yes | 5.474x | 0.425x | 0.078x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,830.4 | 848.3-848.3 | 28.47 | **no** | `b200_sxm-x144-nvl72-hybrid` | 958.0 | 3,235.6-3,235.6 | 1.48 | yes | 5.042x | 0.262x | 0.052x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,887.4 | 1,216.4-1,216.4 | 20.09 | **no** | `b200_sxm-x173-nvl72-hybrid` | 903.3 | 2,801.0-2,801.0 | 1.61 | yes | 5.411x | 0.434x | 0.080x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,675.0 | 2,377.7-2,377.7 | 9.83 | **no** | `b200_sxm-x347-nvl72-hybrid` | 957.9 | 3,145.8-3,145.8 | 1.52 | yes | 4.881x | 0.756x | 0.155x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,638.1 | 641.3-641.3 | 36.16 | **no** | `b200_sxm-x173-nvl72-hybrid` | 808.5 | 2,246.3-2,246.3 | 1.80 | yes | 5.737x | 0.286x | 0.050x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,504.6 | 1,298.8-1,298.8 | 17.34 | **no** | `b200_sxm-x347-nvl72-hybrid` | 882.2 | 2,636.5-2,636.5 | 1.67 | yes | 5.106x | 0.493x | 0.096x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,839.3 | 313.9-313.9 | 45.23 | **no** | `b200_sxm-x173-nvl72-hybrid` | 508.1 | 1,002.9-1,002.9 | 2.53 | yes | 5.588x | 0.313x | 0.056x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,071.8 | 654.1-654.1 | 23.48 | **no** | `b200_sxm-x347-nvl72-hybrid` | 654.9 | 1,470.6-1,470.6 | 2.23 | yes | 4.690x | 0.445x | 0.095x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,053.7 | 161.7-161.7 | 32.58 | **no** | `b200_sxm-x173-nvl72-hybrid` | 251.0 | 442.9-442.9 | 2.83 | yes | 4.197x | 0.365x | 0.087x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,249.0 | 169.0-169.0 | 36.96 | **no** | `b200_sxm-x347-nvl72-hybrid` | 344.5 | 726.0-726.0 | 2.37 | yes | 3.625x | 0.233x | 0.064x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 366.7 | 110.3-110.3 | 16.62 | **no** | `b200_sxm-x173-nvl72-hybrid` | 126.9 | 142.8-142.8 | 4.44 | yes | 2.890x | 0.773x | 0.267x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 359.7 | 44.8-44.8 | 40.12 | **no** | `b200_sxm-x347-nvl72-hybrid` | 162.8 | 203.9-203.9 | 3.99 | yes | 2.209x | 0.220x | 0.100x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.042x to 0.267x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,881.0 | 746.0-746.0 | 32.72 | **no** | `a100_sxm_80gb-x155-hybrid` | 440.0 | 1,135.5-1,135.5 | 1.94 | yes | 11.093x | 0.657x | 0.059x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | 4,989.2 | 1,614.0-1,614.0 | 15.46 | **no** | `a100_sxm_80gb-x616-hybrid` | 430.7 | 921.5-921.5 | 2.34 | yes | 11.583x | 1.751x | 0.151x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,881.0 | 746.0-746.0 | 32.72 | **no** | `a100_sxm_80gb-x155-hybrid` | 440.0 | 1,135.5-1,135.5 | 1.94 | yes | 11.093x | 0.657x | 0.059x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 4,273.7 | 1,001.9-1,001.9 | 21.33 | **no** | `a100_sxm_80gb-x448-hybrid` | 430.7 | 971.5-971.5 | 2.22 | yes | 9.922x | 1.031x | 0.104x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,881.0 | 746.0-746.0 | 32.72 | **no** | `a100_sxm_80gb-x155-hybrid` | 440.0 | 1,135.5-1,135.5 | 1.94 | yes | 11.093x | 0.657x | 0.059x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 4,273.7 | 1,001.9-1,001.9 | 21.33 | **no** | `a100_sxm_80gb-x448-hybrid` | 430.7 | 971.5-971.5 | 2.22 | yes | 9.922x | 1.031x | 0.104x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,881.0 | 746.0-746.0 | 32.72 | **no** | `a100_sxm_80gb-x155-hybrid` | 440.0 | 1,135.5-1,135.5 | 1.94 | yes | 11.093x | 0.657x | 0.059x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 4,273.7 | 1,001.9-1,001.9 | 21.33 | **no** | `a100_sxm_80gb-x448-hybrid` | 430.7 | 971.5-971.5 | 2.22 | yes | 9.922x | 1.031x | 0.104x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,881.0 | 746.0-746.0 | 32.72 | **no** | `a100_sxm_80gb-x155-hybrid` | 440.0 | 1,135.5-1,135.5 | 1.94 | yes | 11.093x | 0.657x | 0.059x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,267.0 | 701.2-701.2 | 30.43 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 9.906x | 0.773x | 0.078x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,654.1 | 895.8-895.8 | 25.98 | **no** | `a100_sxm_80gb-x272-hybrid` | 435.1 | 1,057.1-1,057.1 | 2.06 | yes | 10.696x | 0.847x | 0.079x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,079.4 | 368.5-368.5 | 55.36 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 9.471x | 0.406x | 0.043x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,200.2 | 467.7-467.7 | 44.90 | **no** | `a100_sxm_80gb-x272-hybrid` | 378.1 | 791.8-791.8 | 2.39 | yes | 11.109x | 0.591x | 0.053x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,615.9 | 365.5-365.5 | 49.47 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 8.395x | 0.403x | 0.048x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 2,413.0 | 214.2-214.2 | 56.32 | **no** | `a100_sxm_80gb-x272-hybrid` | 208.8 | 352.4-352.4 | 2.96 | yes | 11.556x | 0.608x | 0.053x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,901.6 | 94.0-94.0 | 101.13 | **no** | `a100_sxm_80gb-x672-hybrid` | 318.0 | 541.4-541.4 | 2.94 | yes | 5.981x | 0.174x | 0.029x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 1,032.0 | 153.3-153.3 | 33.66 | **no** | `a100_sxm_80gb-x335-hybrid` | 94.4 | 177.0-177.0 | 2.67 | yes | 10.934x | 0.866x | 0.079x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 601.7 | 23.7-23.7 | 127.03 | **no** | `a100_sxm_80gb-x672-hybrid` | 151.4 | 231.7-231.7 | 3.27 | yes | 3.974x | 0.102x | 0.026x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 329.6 | 66.2-66.2 | 24.91 | **no** | `a100_sxm_80gb-x335-hybrid` | 35.4 | 44.2-44.2 | 4.00 | yes | 9.320x | 1.497x | 0.161x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 157.6 | 22.9-22.9 | 34.39 | **no** | `a100_sxm_80gb-x672-hybrid` | 56.9 | 114.6-114.6 | 2.48 | yes | 2.768x | 0.200x | 0.072x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.026x to 0.161x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5,462.9 | 660.5-660.5 | 41.35 | **no** | `b200_sxm-x47-nvl72-tensor` | 1,063.7 | 4,391.1-4,391.1 | 1.21 | yes | 5.136x | 0.150x | 0.029x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.8 | 1,305.2-1,305.2 | 21.16 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,071.4 | 4,461.2-4,461.2 | 1.20 | yes | 5.156x | 0.293x | 0.057x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5,462.9 | 660.5-660.5 | 41.35 | **no** | `b200_sxm-x47-nvl72-tensor` | 1,040.8 | 3,992.3-3,992.3 | 1.30 | yes | 5.249x | 0.165x | 0.032x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.8 | 1,305.2-1,305.2 | 21.16 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,050.3 | 4,070.0-4,070.0 | 1.29 | yes | 5.259x | 0.321x | 0.061x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5,462.9 | 660.5-660.5 | 41.35 | **no** | `b200_sxm-x47-nvl72-tensor` | 998.4 | 3,391.7-3,391.7 | 1.47 | yes | 5.472x | 0.195x | 0.036x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.8 | 1,305.2-1,305.2 | 21.16 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,011.2 | 3,477.2-3,477.2 | 1.45 | yes | 5.463x | 0.375x | 0.069x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5,462.9 | 660.5-660.5 | 41.35 | **no** | `b200_sxm-x47-hybrid` | 929.0 | 2,858.9-2,858.9 | 1.62 | yes | 5.881x | 0.231x | 0.039x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.8 | 1,305.2-1,305.2 | 21.16 | **no** | `b200_sxm-x58-nvl72-tensor` | 942.6 | 2,729.2-2,729.2 | 1.73 | yes | 5.860x | 0.478x | 0.082x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5,462.9 | 660.5-660.5 | 41.35 | **no** | `b200_sxm-x47-hybrid` | 838.8 | 2,251.9-2,251.9 | 1.86 | yes | 6.513x | 0.293x | 0.045x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5,515.1 | 1,332.4-1,332.4 | 20.70 | **no** | `b200_sxm-x87-nvl72-hybrid` | 923.7 | 2,884.4-2,884.4 | 1.60 | yes | 5.971x | 0.462x | 0.077x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 5,356.6 | 661.5-661.5 | 40.49 | **no** | `b200_sxm-x110-nvl72-hybrid` | 863.8 | 2,511.6-2,511.6 | 1.72 | yes | 6.202x | 0.263x | 0.042x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,484.8 | 1,367.5-1,367.5 | 20.05 | **no** | `b200_sxm-x231-nvl72-hybrid` | 933.4 | 2,952.9-2,952.9 | 1.58 | yes | 5.876x | 0.463x | 0.079x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,356.6 | 661.5-661.5 | 40.49 | **no** | `b200_sxm-x173-nvl72-hybrid` | 817.6 | 2,262.3-2,262.3 | 1.81 | yes | 6.552x | 0.292x | 0.045x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,483.1 | 1,360.2-1,360.2 | 20.16 | **no** | `b200_sxm-x347-nvl72-hybrid` | 887.6 | 2,647.3-2,647.3 | 1.68 | yes | 6.177x | 0.514x | 0.083x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,825.6 | 328.9-328.9 | 58.15 | **no** | `b200_sxm-x173-nvl72-hybrid` | 522.7 | 1,016.5-1,016.5 | 2.57 | yes | 7.318x | 0.324x | 0.044x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,845.1 | 693.3-693.3 | 34.94 | **no** | `b200_sxm-x347-nvl72-hybrid` | 666.9 | 1,485.1-1,485.1 | 2.25 | yes | 7.265x | 0.467x | 0.064x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,658.6 | 155.8-155.8 | 53.24 | **no** | `b200_sxm-x173-nvl72-hybrid` | 265.7 | 451.9-451.9 | 2.94 | yes | 6.242x | 0.345x | 0.055x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,988.1 | 177.8-177.8 | 84.02 | **no** | `b200_sxm-x347-nvl72-hybrid` | 358.1 | 738.3-738.3 | 2.43 | yes | 8.344x | 0.241x | 0.029x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 483.4 | 114.0-114.0 | 21.19 | **no** | `b200_sxm-x173-nvl72-hybrid` | 142.9 | 146.5-146.5 | 4.88 | yes | 3.383x | 0.779x | 0.230x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,022.9 | 149.5-149.5 | 34.22 | **no** | `b200_sxm-x347-nvl72-hybrid` | 175.3 | 207.6-207.6 | 4.22 | yes | 5.834x | 0.720x | 0.123x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.029x to 0.230x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 5,219.2 | 931.8-931.8 | 28.01 | **no** | `a100_sxm_80gb-x126-hybrid` | 449.6 | 1,173.4-1,173.4 | 1.92 | yes | 11.608x | 0.794x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,352.7 | 978.1-978.1 | 27.36 | **no** | `a100_sxm_80gb-x168-hybrid` | 448.5 | 1,154.9-1,154.9 | 1.94 | yes | 11.934x | 0.847x | 0.071x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 5,219.2 | 931.8-931.8 | 28.01 | **no** | `a100_sxm_80gb-x126-hybrid` | 449.6 | 1,173.4-1,173.4 | 1.92 | yes | 11.608x | 0.794x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,352.7 | 978.1-978.1 | 27.36 | **no** | `a100_sxm_80gb-x168-hybrid` | 448.5 | 1,154.9-1,154.9 | 1.94 | yes | 11.934x | 0.847x | 0.071x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 5,219.2 | 931.8-931.8 | 28.01 | **no** | `a100_sxm_80gb-x126-hybrid` | 449.6 | 1,173.4-1,173.4 | 1.92 | yes | 11.608x | 0.794x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,352.7 | 978.1-978.1 | 27.36 | **no** | `a100_sxm_80gb-x168-hybrid` | 448.5 | 1,154.9-1,154.9 | 1.94 | yes | 11.934x | 0.847x | 0.071x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 5,219.2 | 931.8-931.8 | 28.01 | **no** | `a100_sxm_80gb-x126-hybrid` | 449.6 | 1,173.4-1,173.4 | 1.92 | yes | 11.608x | 0.794x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,352.7 | 978.1-978.1 | 27.36 | **no** | `a100_sxm_80gb-x168-hybrid` | 448.5 | 1,154.9-1,154.9 | 1.94 | yes | 11.934x | 0.847x | 0.071x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 5,219.2 | 931.8-931.8 | 28.01 | **no** | `a100_sxm_80gb-x126-hybrid` | 449.6 | 1,173.4-1,173.4 | 1.92 | yes | 11.608x | 0.794x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,352.7 | 978.1-978.1 | 27.36 | **no** | `a100_sxm_80gb-x168-hybrid` | 448.5 | 1,154.9-1,154.9 | 1.94 | yes | 11.934x | 0.847x | 0.071x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,102.9 | 922.0-922.0 | 27.67 | **no** | `a100_sxm_80gb-x272-hybrid` | 438.6 | 1,061.6-1,061.6 | 2.07 | yes | 11.635x | 0.868x | 0.075x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,332.6 | 1,004.9-1,004.9 | 26.53 | **no** | `a100_sxm_80gb-x448-hybrid` | 434.2 | 975.3-975.3 | 2.23 | yes | 12.283x | 1.030x | 0.084x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,014.1 | 481.9-481.9 | 52.03 | **no** | `a100_sxm_80gb-x272-hybrid` | 383.1 | 796.7-796.7 | 2.40 | yes | 13.089x | 0.605x | 0.046x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,329.3 | 999.3-999.3 | 26.66 | **no** | `a100_sxm_80gb-x672-hybrid` | 434.2 | 909.9-909.9 | 2.39 | yes | 12.275x | 1.098x | 0.089x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,324.4 | 238.4-238.4 | 69.73 | **no** | `a100_sxm_80gb-x335-hybrid` | 236.2 | 391.0-391.0 | 3.02 | yes | 14.075x | 0.610x | 0.043x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,424.0 | 503.9-503.9 | 43.90 | **no** | `a100_sxm_80gb-x672-hybrid` | 323.7 | 545.1-545.1 | 2.97 | yes | 13.668x | 0.924x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,285.4 | 112.7-112.7 | 57.01 | **no** | `a100_sxm_80gb-x335-hybrid` | 98.5 | 180.0-180.0 | 2.74 | yes | 13.044x | 0.626x | 0.048x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,403.2 | 128.4-128.4 | 93.61 | **no** | `a100_sxm_80gb-x672-hybrid` | 156.7 | 234.3-234.3 | 3.34 | yes | 15.336x | 0.548x | 0.036x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 455.1 | 120.2-120.2 | 18.93 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.8 | 49.6-49.6 | 3.81 | yes | 12.055x | 2.423x | 0.201x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 759.1 | 107.8-107.8 | 35.21 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.9 | 117.1-117.1 | 2.56 | yes | 12.662x | 0.921x | 0.073x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.036x to 0.201x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,065.2 | 4,405.7-4,405.7 | 1.21 | yes | 5.043x | 0.276x | 0.055x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 1,289.0-1,289.0 | 20.83 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,071.2 | 4,460.6-4,460.6 | 1.20 | yes | 5.013x | 0.289x | 0.058x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,042.5 | 4,008.3-4,008.3 | 1.30 | yes | 5.152x | 0.304x | 0.059x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 1,289.0-1,289.0 | 20.83 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,050.0 | 4,069.0-4,069.0 | 1.29 | yes | 5.114x | 0.317x | 0.062x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,000.6 | 3,408.9-3,408.9 | 1.47 | yes | 5.368x | 0.357x | 0.067x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 1,289.0-1,289.0 | 20.83 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,010.6 | 3,475.6-3,475.6 | 1.45 | yes | 5.314x | 0.371x | 0.070x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 927.9 | 2,669.7-2,669.7 | 1.74 | yes | 5.788x | 0.456x | 0.079x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 1,289.0-1,289.0 | 20.83 | **no** | `b200_sxm-x58-nvl72-tensor` | 941.7 | 2,727.3-2,727.3 | 1.73 | yes | 5.702x | 0.473x | 0.083x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,361.9 | 632.2-632.2 | 42.40 | **no** | `b200_sxm-x49-hybrid` | 830.0 | 2,245.2-2,245.2 | 1.85 | yes | 6.460x | 0.282x | 0.044x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5,363.4 | 1,315.6-1,315.6 | 20.38 | **no** | `b200_sxm-x87-nvl72-hybrid` | 922.5 | 2,881.7-2,881.7 | 1.60 | yes | 5.814x | 0.457x | 0.079x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 5,209.1 | 657.3-657.3 | 39.62 | **no** | `b200_sxm-x110-nvl72-hybrid` | 862.1 | 2,508.4-2,508.4 | 1.72 | yes | 6.042x | 0.262x | 0.043x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,337.0 | 1,350.1-1,350.1 | 19.77 | **no** | `b200_sxm-x231-nvl72-hybrid` | 932.5 | 2,950.8-2,950.8 | 1.58 | yes | 5.723x | 0.458x | 0.080x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,209.1 | 657.3-657.3 | 39.62 | **no** | `b200_sxm-x173-nvl72-hybrid` | 815.7 | 2,259.1-2,259.1 | 1.81 | yes | 6.386x | 0.291x | 0.046x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,335.0 | 1,342.9-1,342.9 | 19.86 | **no** | `b200_sxm-x347-nvl72-hybrid` | 886.5 | 2,645.1-2,645.1 | 1.68 | yes | 6.018x | 0.508x | 0.084x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,572.7 | 325.7-325.7 | 54.84 | **no** | `b200_sxm-x173-nvl72-hybrid` | 519.7 | 1,013.7-1,013.7 | 2.56 | yes | 6.875x | 0.321x | 0.047x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,537.0 | 684.4-684.4 | 33.15 | **no** | `b200_sxm-x347-nvl72-hybrid` | 664.4 | 1,482.1-1,482.1 | 2.24 | yes | 6.828x | 0.462x | 0.068x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,474.7 | 152.9-152.9 | 48.23 | **no** | `b200_sxm-x173-nvl72-hybrid` | 262.6 | 450.0-450.0 | 2.92 | yes | 5.616x | 0.340x | 0.060x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,637.2 | 175.8-175.8 | 74.99 | **no** | `b200_sxm-x347-nvl72-hybrid` | 355.2 | 735.8-735.8 | 2.41 | yes | 7.424x | 0.239x | 0.032x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 434.2 | 127.1-127.1 | 17.08 | **no** | `b200_sxm-x173-nvl72-hybrid` | 139.3 | 145.7-145.7 | 4.78 | yes | 3.117x | 0.873x | 0.280x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 872.6 | 144.5-144.5 | 30.20 | **no** | `b200_sxm-x347-nvl72-hybrid` | 172.6 | 206.8-206.8 | 4.17 | yes | 5.054x | 0.699x | 0.138x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.032x to 0.280x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 445.6 | 1,157.5-1,157.5 | 1.92 | yes | 11.569x | 0.758x | 0.066x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.2 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.381x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 445.6 | 1,157.5-1,157.5 | 1.92 | yes | 11.569x | 0.758x | 0.066x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.2 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.381x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 445.6 | 1,157.5-1,157.5 | 1.92 | yes | 11.569x | 0.758x | 0.066x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.2 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.381x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 445.6 | 1,157.5-1,157.5 | 1.92 | yes | 11.569x | 0.758x | 0.066x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.2 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.381x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 445.6 | 1,157.5-1,157.5 | 1.92 | yes | 11.569x | 0.758x | 0.066x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.2 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.381x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,021.1 | 916.5-916.5 | 27.39 | **no** | `a100_sxm_80gb-x272-hybrid` | 437.9 | 1,060.7-1,060.7 | 2.06 | yes | 11.467x | 0.864x | 0.075x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,079.5 | 992.0-992.0 | 25.60 | **no** | `a100_sxm_80gb-x448-hybrid` | 433.5 | 974.5-974.5 | 2.22 | yes | 11.719x | 1.018x | 0.087x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,830.1 | 478.9-478.9 | 50.43 | **no** | `a100_sxm_80gb-x272-hybrid` | 382.0 | 795.7-795.7 | 2.40 | yes | 12.643x | 0.602x | 0.048x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,076.2 | 986.6-986.6 | 25.73 | **no** | `a100_sxm_80gb-x672-hybrid` | 433.5 | 909.2-909.2 | 2.38 | yes | 11.711x | 1.085x | 0.093x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,068.8 | 236.2-236.2 | 64.96 | **no** | `a100_sxm_80gb-x335-hybrid` | 234.9 | 390.3-390.3 | 3.01 | yes | 13.062x | 0.605x | 0.046x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,988.1 | 497.6-497.6 | 40.07 | **no** | `a100_sxm_80gb-x672-hybrid` | 322.5 | 544.3-544.3 | 2.96 | yes | 12.366x | 0.914x | 0.074x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 1,176.6 | 163.6-163.6 | 35.96 | **no** | `a100_sxm_80gb-x335-hybrid` | 97.7 | 179.3-179.3 | 2.72 | yes | 12.048x | 0.912x | 0.076x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,978.0 | 127.0-127.0 | 77.86 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.6 | 233.7-233.7 | 3.33 | yes | 12.712x | 0.543x | 0.043x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 428.3 | 114.1-114.1 | 18.76 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.2 | 48.4-48.4 | 3.85 | yes | 11.499x | 2.358x | 0.205x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 602.8 | 104.5-104.5 | 28.84 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.3 | 116.6-116.6 | 2.54 | yes | 10.165x | 0.896x | 0.088x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.043x to 0.205x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-kimi-k3`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | 1,428.2 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 486.8 | not applicable | -- | -- | 2.934x | -- | -- |
| Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 1,779.5 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 487.2 | not applicable | -- | -- | 3.653x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,322.3 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 487.2 | not applicable | -- | -- | 2.714x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,760.7 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 480.3 | not applicable | -- | -- | 3.666x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,322.3 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 480.4 | not applicable | -- | -- | 2.753x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,760.7 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 480.3 | not applicable | -- | -- | 3.666x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,301.1 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 455.1 | not applicable | -- | -- | 2.859x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,760.7 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 476.9 | not applicable | -- | -- | 3.692x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,154.8 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 412.7 | not applicable | -- | -- | 2.798x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,760.7 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 451.6 | not applicable | -- | -- | 3.899x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 911.1 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 350.3 | not applicable | -- | -- | 2.601x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,537.9 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 408.8 | not applicable | -- | -- | 3.762x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 580.6 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 274.2 | not applicable | -- | -- | 2.118x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,264.7 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 345.5 | not applicable | -- | -- | 3.661x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 176.3 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 140.2 | not applicable | -- | -- | 1.257x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 509.1 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 193.9 | not applicable | -- | -- | 2.626x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 45.9 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 63.2 | not applicable | -- | -- | 0.726x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 144.4 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 88.0 | not applicable | -- | -- | 1.641x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 11.5 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 25.1 | not applicable | -- | -- | 0.458x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 36.9 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 38.7 | not applicable | -- | -- | 0.954x | -- | -- |

### `n6_vs_a100-kimi-k3`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x398` | 1,092.5 | not applicable | -- | -- | `a100_sxm_80gb-x393-hybrid` | 127.8 | not applicable | -- | -- | 8.548x | -- | -- |
| Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x10` | 1,701.7 | not applicable | -- | -- | `a100_sxm_80gb-x560-hybrid` | 129.9 | not applicable | -- | -- | 13.104x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 885.7 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 127.9 | not applicable | -- | -- | 6.927x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,402.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 127.9 | not applicable | -- | -- | 10.963x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 885.7 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 127.9 | not applicable | -- | -- | 6.927x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,402.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 127.9 | not applicable | -- | -- | 10.963x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 810.2 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 125.8 | not applicable | -- | -- | 6.442x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,402.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 127.9 | not applicable | -- | -- | 10.963x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 600.3 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 111.1 | not applicable | -- | -- | 5.403x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,402.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 127.9 | not applicable | -- | -- | 10.963x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 372.0 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 93.2 | not applicable | -- | -- | 3.993x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,164.3 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 118.9 | not applicable | -- | -- | 9.796x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 205.7 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 74.0 | not applicable | -- | -- | 2.781x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 851.0 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 100.1 | not applicable | -- | -- | 8.502x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 55.3 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 41.7 | not applicable | -- | -- | 1.326x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 301.9 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 63.3 | not applicable | -- | -- | 4.767x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 14.0 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 17.2 | not applicable | -- | -- | 0.812x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 81.8 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 33.8 | not applicable | -- | -- | 2.420x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 3.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 6.7 | not applicable | -- | -- | 0.523x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x22` | 20.8 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 13.0 | not applicable | -- | -- | 1.595x | -- | -- |

### `n5_vs_b200-kimi-k3-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x383` | 946.4 | not applicable | -- | -- | `b200_sxm-x195-nvl72-hybrid` | 478.5 | not applicable | -- | -- | 1.978x | -- | -- |
| Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | 1,533.1 | not applicable | -- | -- | `b200_sxm-x520-nvl72-hybrid` | 472.0 | not applicable | -- | -- | 3.248x | -- | -- |
| Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,293.4 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | not applicable | -- | -- | 2.856x | -- | -- |
| Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,293.4 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | not applicable | -- | -- | 2.856x | -- | -- |
| Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,293.4 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | not applicable | -- | -- | 2.856x | -- | -- |
| Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,293.4 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | not applicable | -- | -- | 2.856x | -- | -- |
| Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,207.7 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 447.0 | not applicable | -- | -- | 2.702x | -- | -- |
| Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,143.4 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 405.2 | not applicable | -- | -- | 2.822x | -- | -- |
| Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 518.2 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 272.8 | not applicable | -- | -- | 1.899x | -- | -- |
| Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 151.9 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 145.3 | not applicable | -- | -- | 1.045x | -- | -- |
| Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x68` | 39.3 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 49.4 | not applicable | -- | -- | 0.795x | -- | -- |

### `n6_vs_a100-kimi-k3-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 722.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 126.0 | not applicable | -- | -- | 5.736x | -- | -- |
| Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x23` | 1,333.7 | not applicable | -- | -- | `a100_sxm_80gb-x1287-hybrid` | 125.9 | not applicable | -- | -- | 10.594x | -- | -- |
| Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 1,084.9 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 117.7 | not applicable | -- | -- | 9.217x | -- | -- |
| Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 1,084.9 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 117.7 | not applicable | -- | -- | 9.217x | -- | -- |
| Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 1,084.9 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 117.7 | not applicable | -- | -- | 9.217x | -- | -- |
| Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 1,084.9 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 117.7 | not applicable | -- | -- | 9.217x | -- | -- |
| Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 956.7 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 117.7 | not applicable | -- | -- | 8.127x | -- | -- |
| Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 750.1 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 117.7 | not applicable | -- | -- | 6.373x | -- | -- |
| Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 313.0 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 91.5 | not applicable | -- | -- | 3.420x | -- | -- |
| Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 87.5 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 59.8 | not applicable | -- | -- | 1.465x | -- | -- |
| Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 22.4 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 29.9 | not applicable | -- | -- | 0.748x | -- | -- |

### `n5_vs_b200-kimi-k3-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,928.0 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 488.3 | not applicable | -- | -- | 3.949x | -- | -- |
| Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,162.9 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 488.6 | not applicable | -- | -- | 4.426x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,928.0 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 488.3 | not applicable | -- | -- | 3.949x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,162.9 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 488.6 | not applicable | -- | -- | 4.426x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,928.0 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 481.9 | not applicable | -- | -- | 4.001x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,162.9 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 482.2 | not applicable | -- | -- | 4.485x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,928.0 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 458.1 | not applicable | -- | -- | 4.209x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,162.9 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 458.5 | not applicable | -- | -- | 4.717x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,928.0 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 417.8 | not applicable | -- | -- | 4.614x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,162.9 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 418.3 | not applicable | -- | -- | 5.171x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,731.2 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 357.9 | not applicable | -- | -- | 4.837x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,152.4 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 399.0 | not applicable | -- | -- | 5.394x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,499.1 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 283.7 | not applicable | -- | -- | 5.283x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,873.9 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 331.7 | not applicable | -- | -- | 5.649x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 719.1 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 150.9 | not applicable | -- | -- | 4.766x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,089.9 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 182.1 | not applicable | -- | -- | 5.984x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 219.5 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 72.7 | not applicable | -- | -- | 3.020x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 369.4 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 87.1 | not applicable | -- | -- | 4.242x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 57.8 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 35.1 | not applicable | -- | -- | 1.647x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 99.2 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 41.9 | not applicable | -- | -- | 2.366x | -- | -- |

### `n6_vs_a100-kimi-k3-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,383.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 128.3 | not applicable | -- | -- | 10.780x | -- | -- |
| Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,860.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 129.6 | not applicable | -- | -- | 14.356x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,383.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 128.3 | not applicable | -- | -- | 10.780x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,860.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 129.6 | not applicable | -- | -- | 14.356x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,383.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 128.3 | not applicable | -- | -- | 10.780x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,860.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 129.6 | not applicable | -- | -- | 14.356x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,383.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 126.3 | not applicable | -- | -- | 10.956x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,860.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 129.6 | not applicable | -- | -- | 14.356x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,251.6 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 111.9 | not applicable | -- | -- | 11.183x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,855.7 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 123.1 | not applicable | -- | -- | 15.080x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,069.6 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 94.3 | not applicable | -- | -- | 11.340x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,648.8 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 106.1 | not applicable | -- | -- | 15.545x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 742.9 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 75.4 | not applicable | -- | -- | 9.850x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,327.9 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 88.9 | not applicable | -- | -- | 14.931x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 249.6 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 43.6 | not applicable | -- | -- | 5.724x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554.8 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 53.0 | not applicable | -- | -- | 10.460x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 66.6 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 18.5 | not applicable | -- | -- | 3.597x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 159.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 24.6 | not applicable | -- | -- | 6.490x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 16.8 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 7.5 | not applicable | -- | -- | 2.231x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 40.9 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 9.3 | not applicable | -- | -- | 4.415x | -- | -- |

### `n5_vs_b200-mimo-v26-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | 5,396.1 | 3,274.0-3,274.0 | 8.24 | **no** | `b200_sxm-x23-nvl72-tensor` | 1,267.3 | 4,910.1-4,910.1 | 1.29 | yes | 4.258x | 0.667x | 0.157x |
| MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 5,503.2 | 8,245.3-8,245.3 | 3.34 | yes | `b200_sxm-x29-nvl72-tensor` | 1,307.1 | 5,228.7-5,228.7 | 1.25 | yes | 4.210x | 1.577x | 0.375x |
| MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,797.9 | 1,220.5-1,220.5 | 19.66 | **no** | `b200_sxm-x192-nvl72-hybrid` | 1,386.6 | 6,020.3-6,020.3 | 1.15 | yes | 3.460x | 0.203x | 0.059x |
| MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,663.1 | 2,224.7-2,224.7 | 8.23 | **no** | `b200_sxm-x636-nvl72-hybrid` | 1,369.1 | 5,977.4-5,977.4 | 1.15 | yes | 2.676x | 0.372x | 0.139x |
| MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,797.9 | 1,220.5-1,220.5 | 19.66 | **no** | `b200_sxm-x192-nvl72-hybrid` | 1,369.6 | 5,836.5-5,836.5 | 1.17 | yes | 3.503x | 0.209x | 0.060x |
| MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,663.1 | 2,224.7-2,224.7 | 8.23 | **no** | `b200_sxm-x636-nvl72-hybrid` | 1,369.1 | 5,977.4-5,977.4 | 1.15 | yes | 2.676x | 0.372x | 0.139x |
| MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,797.9 | 1,220.5-1,220.5 | 19.66 | **no** | `b200_sxm-x192-nvl72-hybrid` | 1,306.3 | 5,289.5-5,289.5 | 1.23 | yes | 3.673x | 0.231x | 0.063x |
| MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,496.8 | 1,322.6-1,322.6 | 13.22 | **no** | `b200_sxm-x636-nvl72-hybrid` | 1,369.1 | 5,977.4-5,977.4 | 1.15 | yes | 2.554x | 0.221x | 0.087x |
| MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x282` | 4,634.9 | 841.0-841.0 | 27.55 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,141.4 | 4,050.3-4,050.3 | 1.41 | yes | 4.061x | 0.208x | 0.051x |
| MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,364.9 | 701.1-701.1 | 24.00 | **no** | `b200_sxm-x636-nvl72-hybrid` | 1,332.7 | 5,585.4-5,585.4 | 1.19 | yes | 2.525x | 0.126x | 0.050x |
| MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,038.8 | 634.0-634.0 | 31.85 | **no** | `b200_sxm-x192-nvl72-hybrid` | 1,035.8 | 3,523.4-3,523.4 | 1.47 | yes | 3.899x | 0.180x | 0.046x |
| MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 2,771.2 | 690.2-690.2 | 20.07 | **no** | `b200_sxm-x636-nvl72-hybrid` | 1,257.7 | 4,907.0-4,907.0 | 1.28 | yes | 2.203x | 0.141x | 0.064x |
| MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 2,943.2 | 331.2-331.2 | 44.43 | **no** | `b200_sxm-x192-nvl72-hybrid` | 830.0 | 2,558.3-2,558.3 | 1.62 | yes | 3.546x | 0.129x | 0.037x |
| MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 1,859.8 | 396.4-396.4 | 23.46 | **no** | `b200_sxm-x636-nvl72-hybrid` | 1,134.2 | 4,024.6-4,024.6 | 1.41 | yes | 1.640x | 0.098x | 0.060x |
| MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 951.4 | 433.2-433.2 | 10.98 | **no** | `b200_sxm-x192-nvl72-hybrid` | 428.1 | 1,032.2-1,032.2 | 2.07 | yes | 2.222x | 0.420x | 0.189x |
| MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 600.3 | 101.0-101.0 | 29.72 | **no** | `b200_sxm-x636-nvl72-hybrid` | 747.3 | 2,030.0-2,030.0 | 1.84 | yes | 0.803x | 0.050x | 0.062x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 238.5 | 224.3-224.3 | 5.32 | **no** | `b200_sxm-x192-nvl72-hybrid` | 168.1 | 459.8-459.8 | 1.83 | yes | 1.419x | 0.488x | 0.344x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 159.0 | 25.3-25.3 | 31.40 | **no** | `b200_sxm-x636-nvl72-hybrid` | 364.5 | 755.8-755.8 | 2.41 | yes | 0.436x | 0.033x | 0.077x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 59.7 | 76.2-76.2 | 3.92 | yes | `b200_sxm-x192-nvl72-hybrid` | 53.1 | 175.1-175.1 | 1.52 | yes | 1.125x | 0.435x | 0.387x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x22` | 40.2 | 12.3-12.3 | 16.38 | **no** | `b200_sxm-x636-nvl72-hybrid` | 139.9 | 335.4-335.4 | 2.09 | yes | 0.287x | 0.037x | 0.127x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.037x to 0.387x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 2 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x64` | 5,173.0 | 2,664.9-2,664.9 | 9.71 | **no** | `a100_sxm_80gb-x63-hybrid` | 416.3 | 1,212.5-1,212.5 | 1.72 | yes | 12.427x | 2.198x | 0.177x |
| MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 5,440.2 | 7,708.8-7,708.8 | 3.53 | yes | `a100_sxm_80gb-x56-hybrid` | 420.3 | 1,217.9-1,217.9 | 1.73 | yes | 12.943x | 6.330x | 0.489x |
| MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3,903.2 | 1,928.9-1,928.9 | 10.12 | **no** | `a100_sxm_80gb-x391-hybrid` | 409.4 | 1,346.1-1,346.1 | 1.52 | yes | 9.534x | 1.433x | 0.150x |
| MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3,134.8 | 1,722.7-1,722.7 | 9.10 | **no** | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 1,338.4-1,338.4 | 1.51 | yes | 7.754x | 1.287x | 0.166x |
| MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3,903.2 | 1,928.9-1,928.9 | 10.12 | **no** | `a100_sxm_80gb-x391-hybrid` | 409.4 | 1,346.1-1,346.1 | 1.52 | yes | 9.534x | 1.433x | 0.150x |
| MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3,134.8 | 1,722.7-1,722.7 | 9.10 | **no** | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 1,338.4-1,338.4 | 1.51 | yes | 7.754x | 1.287x | 0.166x |
| MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x287` | 3,860.3 | 1,558.9-1,558.9 | 12.38 | **no** | `a100_sxm_80gb-x283-hybrid` | 404.7 | 1,311.4-1,311.4 | 1.54 | yes | 9.538x | 1.189x | 0.125x |
| MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3,134.8 | 1,722.7-1,722.7 | 9.10 | **no** | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 1,338.4-1,338.4 | 1.51 | yes | 7.754x | 1.287x | 0.166x |
| MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3,415.0 | 1,110.4-1,110.4 | 15.38 | **no** | `a100_sxm_80gb-x391-hybrid` | 403.4 | 1,327.0-1,327.0 | 1.52 | yes | 8.466x | 0.837x | 0.099x |
| MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2,577.1 | 925.7-925.7 | 13.92 | **no** | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 1,338.4-1,338.4 | 1.51 | yes | 6.375x | 0.692x | 0.108x |
| MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 2,658.9 | 605.7-605.7 | 21.95 | **no** | `a100_sxm_80gb-x391-hybrid` | 403.4 | 1,327.0-1,327.0 | 1.52 | yes | 6.592x | 0.456x | 0.069x |
| MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,983.5 | 495.9-495.9 | 20.00 | **no** | `a100_sxm_80gb-x1735-hybrid` | 403.8 | 1,479.2-1,479.2 | 1.36 | yes | 4.912x | 0.335x | 0.068x |
| MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,676.6 | 309.9-309.9 | 27.05 | **no** | `a100_sxm_80gb-x391-hybrid` | 369.2 | 1,183.1-1,183.1 | 1.56 | yes | 4.541x | 0.262x | 0.058x |
| MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,213.9 | 282.0-282.0 | 21.53 | **no** | `a100_sxm_80gb-x1735-hybrid` | 403.8 | 1,479.2-1,479.2 | 1.36 | yes | 3.006x | 0.191x | 0.063x |
| MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 503.9 | 79.1-79.1 | 31.85 | **no** | `a100_sxm_80gb-x391-hybrid` | 180.1 | 573.2-573.2 | 1.57 | yes | 2.798x | 0.138x | 0.049x |
| MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 356.1 | 71.2-71.2 | 25.02 | **no** | `a100_sxm_80gb-x1735-hybrid` | 383.0 | 1,356.5-1,356.5 | 1.41 | yes | 0.930x | 0.052x | 0.056x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 131.0 | 38.2-38.2 | 17.17 | **no** | `a100_sxm_80gb-x391-hybrid` | 64.5 | 227.2-227.2 | 1.42 | yes | 2.032x | 0.168x | 0.083x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 92.0 | 17.8-17.8 | 25.80 | **no** | `a100_sxm_80gb-x1735-hybrid` | 192.8 | 633.2-633.2 | 1.52 | yes | 0.477x | 0.028x | 0.059x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 33.0 | 31.3-31.3 | 5.29 | **no** | `a100_sxm_80gb-x391-hybrid` | 22.5 | 66.2-66.2 | 1.70 | yes | 1.471x | 0.473x | 0.321x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x31` | 23.1 | 8.6-8.6 | 13.48 | **no** | `a100_sxm_80gb-x1735-hybrid` | 69.9 | 256.0-256.0 | 1.37 | yes | 0.331x | 0.034x | 0.101x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.049x to 0.489x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 1 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 4,359.9 | 2,564.7-2,564.7 | 8.50 | **no** | `b200_sxm-x53-nvl72-tensor` | 1,286.9 | 5,517.3-5,517.3 | 1.17 | yes | 3.388x | 0.465x | 0.137x |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 5,253.1 | 2,916.6-2,916.6 | 9.01 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,301.9 | 5,610.6-5,610.6 | 1.16 | yes | 4.035x | 0.520x | 0.129x |
| MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,458.8 | 550.3-550.3 | 22.34 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 5,070.2-5,070.2 | 1.17 | yes | 2.081x | 0.109x | 0.052x |
| MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,458.8 | 550.3-550.3 | 22.34 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 5,070.2-5,070.2 | 1.17 | yes | 2.081x | 0.109x | 0.052x |
| MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,458.8 | 550.3-550.3 | 22.34 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 5,070.2-5,070.2 | 1.17 | yes | 2.081x | 0.109x | 0.052x |
| MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,458.8 | 550.3-550.3 | 22.34 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 5,070.2-5,070.2 | 1.17 | yes | 2.081x | 0.109x | 0.052x |
| MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,302.8 | 547.2-547.2 | 21.04 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 5,070.2-5,070.2 | 1.17 | yes | 1.949x | 0.108x | 0.055x |
| MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,626.6 | 285.0-285.0 | 28.54 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 1,138.1 | 4,704.5-4,704.5 | 1.21 | yes | 1.429x | 0.061x | 0.042x |
| MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 586.9 | 81.7-81.7 | 35.91 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 866.4 | 3,492.4-3,492.4 | 1.24 | yes | 0.677x | 0.023x | 0.035x |
| MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 157.8 | 20.6-20.6 | 38.37 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 447.8 | 1,669.9-1,669.9 | 1.34 | yes | 0.352x | 0.012x | 0.035x |
| MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 40.0 | 5.1-5.1 | 38.91 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 158.9 | 574.1-574.1 | 1.38 | yes | 0.252x | 0.009x | 0.036x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.035x to 0.137x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | 4,193.4 | 2,125.7-2,125.7 | 9.86 | **no** | `a100_sxm_80gb-x139-tensor` | 416.1 | 1,368.2-1,368.2 | 1.52 | yes | 10.078x | 1.554x | 0.154x |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 5,049.5 | 4,558.8-4,558.8 | 5.54 | **no** | `a100_sxm_80gb-x112-tensor` | 410.0 | 1,352.0-1,352.0 | 1.52 | yes | 12.315x | 3.372x | 0.274x |
| MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 1,661.2 | 4,110.0-4,110.0 | 2.02 | yes | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 1,265.1-1,265.1 | 1.47 | yes | 4.469x | 3.249x | 0.727x |
| MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,535.4 | 394.5-394.5 | 19.46 | **no** | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 1,265.1-1,265.1 | 1.47 | yes | 4.131x | 0.312x | 0.075x |
| MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,535.4 | 394.5-394.5 | 19.46 | **no** | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 1,265.1-1,265.1 | 1.47 | yes | 4.131x | 0.312x | 0.075x |
| MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,535.4 | 394.5-394.5 | 19.46 | **no** | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 1,265.1-1,265.1 | 1.47 | yes | 4.131x | 0.312x | 0.075x |
| MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,535.4 | 394.5-394.5 | 19.46 | **no** | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 1,265.1-1,265.1 | 1.47 | yes | 4.131x | 0.312x | 0.075x |
| MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,085.8 | 384.3-384.3 | 14.13 | **no** | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 1,265.1-1,265.1 | 1.47 | yes | 2.921x | 0.304x | 0.104x |
| MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 346.8 | 100.4-100.4 | 17.28 | **no** | `a100_sxm_80gb-x8562-hybrid` | 331.9 | 1,194.2-1,194.2 | 1.39 | yes | 1.045x | 0.084x | 0.080x |
| MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 90.9 | 28.2-28.2 | 16.13 | **no** | `a100_sxm_80gb-x8562-hybrid` | 258.2 | 1,141.2-1,141.2 | 1.13 | yes | 0.352x | 0.025x | 0.070x |
| MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 22.9 | 7.1-7.1 | 16.26 | **no** | `a100_sxm_80gb-x8562-hybrid` | 101.1 | 411.6-411.6 | 1.23 | yes | 0.227x | 0.017x | 0.076x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.070x to 0.727x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 1 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,140.0 | 2,168.6-2,168.6 | 16.46 | **no** | `b200_sxm-x61-nvl72-tensor` | 1,417.2 | 6,056.6-6,056.6 | 1.17 | yes | 5.038x | 0.358x | 0.071x |
| MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,526.2 | 1,833.2-1,833.2 | 17.80 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,413.8 | 6,021.4-6,021.4 | 1.17 | yes | 4.616x | 0.304x | 0.066x |
| MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,140.0 | 2,168.6-2,168.6 | 16.46 | **no** | `b200_sxm-x61-nvl72-tensor` | 1,385.1 | 5,627.9-5,627.9 | 1.23 | yes | 5.155x | 0.385x | 0.075x |
| MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,526.2 | 1,833.2-1,833.2 | 17.80 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,380.6 | 5,583.9-5,583.9 | 1.24 | yes | 4.727x | 0.328x | 0.069x |
| MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,140.0 | 2,168.6-2,168.6 | 16.46 | **no** | `b200_sxm-x61-nvl72-tensor` | 1,327.0 | 4,959.3-4,959.3 | 1.34 | yes | 5.380x | 0.437x | 0.081x |
| MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,526.2 | 1,833.2-1,833.2 | 17.80 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,320.7 | 4,907.9-4,907.9 | 1.35 | yes | 4.941x | 0.374x | 0.076x |
| MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,140.0 | 2,168.6-2,168.6 | 16.46 | **no** | `b200_sxm-x61-nvl72-tensor` | 1,230.9 | 4,148.7-4,148.7 | 1.48 | yes | 5.801x | 0.523x | 0.090x |
| MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,526.2 | 1,833.2-1,833.2 | 17.80 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,222.0 | 4,097.8-4,097.8 | 1.49 | yes | 5.341x | 0.447x | 0.084x |
| MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 7,074.1 | 2,100.2-2,100.2 | 16.84 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,157.3 | 3,827.9-3,827.9 | 1.51 | yes | 6.113x | 0.549x | 0.090x |
| MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 6,388.4 | 3,972.7-3,972.7 | 8.04 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,271.3 | 4,628.5-4,628.5 | 1.37 | yes | 5.025x | 0.858x | 0.171x |
| MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,967.4 | 2,139.2-2,139.2 | 16.29 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,153.9 | 3,746.5-3,746.5 | 1.54 | yes | 6.038x | 0.571x | 0.095x |
| MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6,305.2 | 4,036.3-4,036.3 | 7.81 | **no** | `b200_sxm-x347-nvl72-hybrid` | 1,262.4 | 4,525.0-4,525.0 | 1.39 | yes | 4.994x | 0.892x | 0.179x |
| MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,929.3 | 1,140.0-1,140.0 | 30.39 | **no** | `b200_sxm-x173-nvl72-hybrid` | 998.3 | 2,834.3-2,834.3 | 1.76 | yes | 6.941x | 0.402x | 0.058x |
| MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6,075.1 | 2,270.4-2,270.4 | 13.38 | **no** | `b200_sxm-x347-nvl72-hybrid` | 1,142.3 | 3,560.1-3,560.1 | 1.60 | yes | 5.318x | 0.638x | 0.120x |
| MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,651.0 | 559.8-559.8 | 41.54 | **no** | `b200_sxm-x173-nvl72-hybrid` | 678.9 | 1,256.0-1,256.0 | 2.70 | yes | 6.851x | 0.446x | 0.065x |
| MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,129.5 | 1,164.0-1,164.0 | 17.74 | **no** | `b200_sxm-x347-nvl72-hybrid` | 818.9 | 1,726.0-1,726.0 | 2.37 | yes | 5.043x | 0.674x | 0.134x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,847.6 | 256.5-256.5 | 36.01 | **no** | `b200_sxm-x173-nvl72-hybrid` | 413.1 | 682.3-682.3 | 3.03 | yes | 4.472x | 0.376x | 0.084x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,614.2 | 304.5-304.5 | 26.51 | **no** | `b200_sxm-x347-nvl72-hybrid` | 509.4 | 663.9-663.9 | 3.84 | yes | 3.169x | 0.459x | 0.145x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 527.4 | 164.8-164.8 | 16.00 | **no** | `b200_sxm-x173-nvl72-hybrid` | 221.7 | 329.6-329.6 | 3.36 | yes | 2.379x | 0.500x | 0.210x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 452.3 | 237.3-237.3 | 9.53 | **no** | `b200_sxm-x347-nvl72-hybrid` | 285.3 | 319.1-319.1 | 4.47 | yes | 1.585x | 0.744x | 0.469x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.058x to 0.469x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,845.8 | 1,569.2-1,569.2 | 21.81 | **no** | `a100_sxm_80gb-x77-hybrid` | 478.5 | 1,316.8-1,316.8 | 1.82 | yes | 14.306x | 1.192x | 0.083x |
| MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,680.5 | 1,822.0-1,822.0 | 15.59 | **no** | `a100_sxm_80gb-x224-hybrid` | 477.5 | 1,445.7-1,445.7 | 1.65 | yes | 11.896x | 1.260x | 0.106x |
| MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,845.8 | 1,569.2-1,569.2 | 21.81 | **no** | `a100_sxm_80gb-x77-hybrid` | 478.5 | 1,316.8-1,316.8 | 1.82 | yes | 14.306x | 1.192x | 0.083x |
| MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,680.5 | 1,822.0-1,822.0 | 15.59 | **no** | `a100_sxm_80gb-x224-hybrid` | 477.5 | 1,445.7-1,445.7 | 1.65 | yes | 11.896x | 1.260x | 0.106x |
| MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,845.8 | 1,569.2-1,569.2 | 21.81 | **no** | `a100_sxm_80gb-x77-hybrid` | 478.5 | 1,316.8-1,316.8 | 1.82 | yes | 14.306x | 1.192x | 0.083x |
| MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,680.5 | 1,822.0-1,822.0 | 15.59 | **no** | `a100_sxm_80gb-x224-hybrid` | 477.5 | 1,445.7-1,445.7 | 1.65 | yes | 11.896x | 1.260x | 0.106x |
| MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,845.8 | 1,569.2-1,569.2 | 21.81 | **no** | `a100_sxm_80gb-x77-hybrid` | 478.5 | 1,316.8-1,316.8 | 1.82 | yes | 14.306x | 1.192x | 0.083x |
| MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,680.5 | 1,822.0-1,822.0 | 15.59 | **no** | `a100_sxm_80gb-x224-hybrid` | 477.5 | 1,445.7-1,445.7 | 1.65 | yes | 11.896x | 1.260x | 0.106x |
| MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 6,790.9 | 1,567.9-1,567.9 | 21.66 | **no** | `a100_sxm_80gb-x154-hybrid` | 473.2 | 1,377.8-1,377.8 | 1.72 | yes | 14.352x | 1.138x | 0.079x |
| MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,547.9 | 5,122.4-5,122.4 | 5.42 | **no** | `a100_sxm_80gb-x672-hybrid` | 467.0 | 1,505.4-1,505.4 | 1.55 | yes | 11.880x | 3.403x | 0.286x |
| MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,679.9 | 1,584.8-1,584.8 | 21.08 | **no** | `a100_sxm_80gb-x335-hybrid` | 469.5 | 1,455.9-1,455.9 | 1.61 | yes | 14.229x | 1.088x | 0.076x |
| MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,370.5 | 3,078.0-3,078.0 | 8.72 | **no** | `a100_sxm_80gb-x672-hybrid` | 467.0 | 1,505.4-1,505.4 | 1.55 | yes | 11.500x | 2.045x | 0.178x |
| MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,338.1 | 831.7-831.7 | 38.10 | **no** | `a100_sxm_80gb-x335-hybrid` | 426.3 | 1,235.5-1,235.5 | 1.73 | yes | 14.867x | 0.673x | 0.045x |
| MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,465.8 | 1,681.4-1,681.4 | 13.28 | **no** | `a100_sxm_80gb-x672-hybrid` | 467.0 | 1,505.4-1,505.4 | 1.55 | yes | 9.563x | 1.117x | 0.117x |
| MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,960.9 | 406.7-406.7 | 48.70 | **no** | `a100_sxm_80gb-x335-hybrid` | 244.1 | 657.9-657.9 | 1.86 | yes | 16.223x | 0.618x | 0.038x |
| MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,332.7 | 849.5-849.5 | 13.73 | **no** | `a100_sxm_80gb-x672-hybrid` | 337.0 | 942.5-942.5 | 1.79 | yes | 6.922x | 0.901x | 0.130x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,434.4 | 186.3-186.3 | 38.50 | **no** | `a100_sxm_80gb-x335-hybrid` | 108.2 | 313.7-313.7 | 1.72 | yes | 13.255x | 0.594x | 0.045x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 723.5 | 220.1-220.1 | 16.44 | **no** | `a100_sxm_80gb-x672-hybrid` | 163.2 | 457.9-457.9 | 1.78 | yes | 4.433x | 0.481x | 0.108x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 396.7 | 120.7-120.7 | 16.44 | **no** | `a100_sxm_80gb-x335-hybrid` | 58.2 | 121.2-121.2 | 2.40 | yes | 6.814x | 0.995x | 0.146x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 190.0 | 171.5-171.5 | 5.54 | **no** | `a100_sxm_80gb-x672-hybrid` | 75.2 | 213.0-213.0 | 1.76 | yes | 2.528x | 0.805x | 0.318x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.038x to 0.318x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | 3,064.9 | 2,001.7-2,001.7 | 7.66 | **no** | `b200_sxm-x71-nvl72-tensor` | 916.0 | 3,798.1-3,798.1 | 1.21 | yes | 3.346x | 0.527x | 0.158x |
| MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 3,548.1 | 2,048.0-2,048.0 | 8.66 | **no** | `b200_sxm-x87-nvl72-hybrid` | 858.9 | 3,412.5-3,412.5 | 1.26 | yes | 4.131x | 0.600x | 0.145x |
| MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,345.5 | 1,086.3-1,086.3 | 10.80 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 3,746.8-3,746.8 | 1.17 | yes | 2.668x | 0.290x | 0.109x |
| MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,345.5 | 1,086.3-1,086.3 | 10.80 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 3,746.8-3,746.8 | 1.17 | yes | 2.668x | 0.290x | 0.109x |
| MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,345.5 | 1,086.3-1,086.3 | 10.80 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 3,746.8-3,746.8 | 1.17 | yes | 2.668x | 0.290x | 0.109x |
| MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,179.3 | 1,070.8-1,070.8 | 10.18 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 3,746.8-3,746.8 | 1.17 | yes | 2.479x | 0.286x | 0.115x |
| MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,903.5 | 594.7-594.7 | 16.00 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 852.9 | 3,437.5-3,437.5 | 1.24 | yes | 2.232x | 0.173x | 0.078x |
| MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,576.3 | 316.4-316.4 | 24.91 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 790.5 | 2,895.5-2,895.5 | 1.36 | yes | 1.994x | 0.109x | 0.055x |
| MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 575.6 | 90.7-90.7 | 31.73 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 556.6 | 1,569.0-1,569.0 | 1.77 | yes | 1.034x | 0.058x | 0.056x |
| MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 158.2 | 22.8-22.8 | 34.68 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 276.2 | 592.0-592.0 | 2.33 | yes | 0.573x | 0.039x | 0.067x |
| MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x49` | 40.3 | 5.7-5.7 | 35.33 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 108.7 | 274.1-274.1 | 1.98 | yes | 0.371x | 0.021x | 0.056x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.055x to 0.158x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | 2,984.6 | 1,710.7-1,710.7 | 8.72 | **no** | `a100_sxm_80gb-x178-tensor` | 281.6 | 818.3-818.3 | 1.72 | yes | 10.600x | 2.090x | 0.197x |
| MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 3,483.3 | 3,148.7-3,148.7 | 5.53 | **no** | `a100_sxm_80gb-x168-tensor` | 280.9 | 816.6-816.6 | 1.72 | yes | 12.402x | 3.856x | 0.311x |
| MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,895.0 | 844.7-844.7 | 11.22 | **no** | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 759.4-759.4 | 1.65 | yes | 7.550x | 1.112x | 0.147x |
| MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,895.0 | 844.7-844.7 | 11.22 | **no** | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 759.4-759.4 | 1.65 | yes | 7.550x | 1.112x | 0.147x |
| MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,895.0 | 844.7-844.7 | 11.22 | **no** | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 759.4-759.4 | 1.65 | yes | 7.550x | 1.112x | 0.147x |
| MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,895.0 | 844.7-844.7 | 11.22 | **no** | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 759.4-759.4 | 1.65 | yes | 7.550x | 1.112x | 0.147x |
| MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,455.4 | 444.7-444.7 | 16.37 | **no** | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 759.4-759.4 | 1.65 | yes | 5.799x | 0.586x | 0.101x |
| MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,032.2 | 228.5-228.5 | 22.58 | **no** | `a100_sxm_80gb-x3805-hybrid` | 248.8 | 736.6-736.6 | 1.69 | yes | 4.148x | 0.310x | 0.075x |
| MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 342.9 | 64.8-64.8 | 26.44 | **no** | `a100_sxm_80gb-x3805-hybrid` | 191.3 | 469.1-469.1 | 2.04 | yes | 1.793x | 0.138x | 0.077x |
| MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 90.5 | 16.3-16.3 | 27.76 | **no** | `a100_sxm_80gb-x3805-hybrid` | 135.5 | 433.3-433.3 | 1.56 | yes | 0.668x | 0.038x | 0.056x |
| MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x68` | 22.9 | 4.1-4.1 | 28.02 | **no** | `a100_sxm_80gb-x3805-hybrid` | 56.7 | 172.3-172.3 | 1.64 | yes | 0.403x | 0.024x | 0.059x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.056x to 0.311x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | 2,556.9 | 1,743.7-1,743.7 | 7.33 | **no** | `b200_sxm-x170-nvl72-hybrid` | 808.3 | 3,392.2-3,392.2 | 1.19 | yes | 3.163x | 0.514x | 0.163x |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 3,359.6 | 2,529.4-2,529.4 | 6.64 | **no** | `b200_sxm-x116-nvl72-hybrid` | 813.5 | 3,394.5-3,394.5 | 1.20 | yes | 4.130x | 0.745x | 0.180x |
| MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,385.2 | 256.0-256.0 | 27.05 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 3,142.3-3,142.3 | 1.19 | yes | 1.855x | 0.081x | 0.044x |
| MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,385.2 | 256.0-256.0 | 27.05 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 3,142.3-3,142.3 | 1.19 | yes | 1.855x | 0.081x | 0.044x |
| MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,385.2 | 256.0-256.0 | 27.05 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 3,142.3-3,142.3 | 1.19 | yes | 1.855x | 0.081x | 0.044x |
| MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,385.2 | 256.0-256.0 | 27.05 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 3,142.3-3,142.3 | 1.19 | yes | 1.855x | 0.081x | 0.044x |
| MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,385.2 | 256.0-256.0 | 27.05 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 3,142.3-3,142.3 | 1.19 | yes | 1.855x | 0.081x | 0.044x |
| MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,342.8 | 255.5-255.5 | 26.27 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 3,142.3-3,142.3 | 1.19 | yes | 1.798x | 0.081x | 0.045x |
| MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 554.4 | 66.1-66.1 | 41.97 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 627.0 | 2,267.9-2,267.9 | 1.38 | yes | 0.884x | 0.029x | 0.033x |
| MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 155.8 | 18.6-18.6 | 41.97 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 370.2 | 1,376.5-1,376.5 | 1.34 | yes | 0.421x | 0.013x | 0.032x |
| MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 39.9 | 4.6-4.6 | 42.96 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 142.9 | 521.5-521.5 | 1.37 | yes | 0.279x | 0.009x | 0.032x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.032x to 0.180x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | 2,389.5 | 1,701.2-1,701.2 | 7.02 | **no** | `a100_sxm_80gb-x316-tensor` | 280.8 | 823.3-823.3 | 1.71 | yes | 8.510x | 2.066x | 0.243x |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 3,205.3 | 1,850.1-1,850.1 | 8.66 | **no** | `a100_sxm_80gb-x336-hybrid` | 229.7 | 708.9-708.9 | 1.62 | yes | 13.956x | 2.610x | 0.187x |
| MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 873.9 | 2,598.6-2,598.6 | 1.68 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 721.5-721.5 | 1.58 | yes | 3.840x | 3.602x | 0.938x |
| MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 805.6 | 2,090.1-2,090.1 | 1.93 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 721.5-721.5 | 1.58 | yes | 3.540x | 2.897x | 0.818x |
| MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 796.3 | 182.5-182.5 | 21.81 | **no** | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 721.5-721.5 | 1.58 | yes | 3.499x | 0.253x | 0.072x |
| MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 796.3 | 182.5-182.5 | 21.81 | **no** | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 721.5-721.5 | 1.58 | yes | 3.499x | 0.253x | 0.072x |
| MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 796.3 | 182.5-182.5 | 21.81 | **no** | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 721.5-721.5 | 1.58 | yes | 3.499x | 0.253x | 0.072x |
| MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 796.3 | 182.5-182.5 | 21.81 | **no** | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 721.5-721.5 | 1.58 | yes | 3.499x | 0.253x | 0.072x |
| MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 327.2 | 91.0-91.0 | 17.97 | **no** | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 721.5-721.5 | 1.58 | yes | 1.438x | 0.126x | 0.088x |
| MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 90.0 | 25.6-25.6 | 17.57 | **no** | `a100_sxm_80gb-x18971-hybrid` | 159.3 | 487.8-487.8 | 1.63 | yes | 0.565x | 0.052x | 0.093x |
| MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 22.9 | 6.4-6.4 | 17.83 | **no** | `a100_sxm_80gb-x18971-hybrid` | 83.1 | 335.4-335.4 | 1.24 | yes | 0.275x | 0.019x | 0.069x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.069x to 0.938x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 2 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,293.8 | 1,377.1-1,377.1 | 15.59 | **no** | `b200_sxm-x78-nvl72-hybrid` | 872.8 | 3,393.8-3,393.8 | 1.29 | yes | 4.919x | 0.406x | 0.082x |
| MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,202.7 | 1,300.6-1,300.6 | 16.16 | **no** | `b200_sxm-x87-nvl72-hybrid` | 885.4 | 3,495.6-3,495.6 | 1.27 | yes | 4.747x | 0.372x | 0.078x |
| MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,293.8 | 1,377.1-1,377.1 | 15.59 | **no** | `b200_sxm-x78-nvl72-hybrid` | 872.8 | 3,393.8-3,393.8 | 1.29 | yes | 4.919x | 0.406x | 0.082x |
| MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,202.7 | 1,300.6-1,300.6 | 16.16 | **no** | `b200_sxm-x87-nvl72-hybrid` | 885.4 | 3,495.6-3,495.6 | 1.27 | yes | 4.747x | 0.372x | 0.078x |
| MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,293.8 | 1,377.1-1,377.1 | 15.59 | **no** | `b200_sxm-x78-nvl72-hybrid` | 834.5 | 3,010.1-3,010.1 | 1.39 | yes | 5.145x | 0.458x | 0.089x |
| MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,202.7 | 1,300.6-1,300.6 | 16.16 | **no** | `b200_sxm-x87-nvl72-hybrid` | 849.4 | 3,119.5-3,119.5 | 1.36 | yes | 4.948x | 0.417x | 0.084x |
| MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,293.8 | 1,377.1-1,377.1 | 15.59 | **no** | `b200_sxm-x78-nvl72-hybrid` | 768.8 | 2,461.0-2,461.0 | 1.56 | yes | 5.585x | 0.560x | 0.100x |
| MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,202.7 | 1,300.6-1,300.6 | 16.16 | **no** | `b200_sxm-x87-nvl72-hybrid` | 786.8 | 2,573.6-2,573.6 | 1.53 | yes | 5.341x | 0.505x | 0.095x |
| MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 4,249.4 | 1,287.8-1,287.8 | 16.50 | **no** | `b200_sxm-x150-nvl72-hybrid` | 772.4 | 2,490.0-2,490.0 | 1.55 | yes | 5.502x | 0.517x | 0.094x |
| MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 4,172.4 | 1,383.3-1,383.3 | 15.08 | **no** | `b200_sxm-x173-nvl72-hybrid` | 794.3 | 2,614.6-2,614.6 | 1.52 | yes | 5.253x | 0.529x | 0.101x |
| MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 4,179.8 | 697.3-697.3 | 29.97 | **no** | `b200_sxm-x150-nvl72-hybrid` | 666.1 | 1,885.2-1,885.2 | 1.77 | yes | 6.275x | 0.370x | 0.059x |
| MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,144.5 | 1,410.8-1,410.8 | 14.69 | **no** | `b200_sxm-x347-nvl72-hybrid` | 793.6 | 2,598.0-2,598.0 | 1.53 | yes | 5.222x | 0.543x | 0.104x |
| MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 3,902.5 | 686.3-686.3 | 28.43 | **no** | `b200_sxm-x200-nvl72-hybrid` | 592.0 | 1,485.0-1,485.0 | 1.99 | yes | 6.593x | 0.462x | 0.070x |
| MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,697.7 | 746.0-746.0 | 24.78 | **no** | `b200_sxm-x347-nvl72-hybrid` | 688.7 | 1,923.3-1,923.3 | 1.79 | yes | 5.369x | 0.388x | 0.072x |
| MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 2,400.0 | 177.8-177.8 | 67.50 | **no** | `b200_sxm-x200-nvl72-hybrid` | 349.7 | 614.9-614.9 | 2.84 | yes | 6.863x | 0.289x | 0.042x |
| MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,259.3 | 372.8-372.8 | 30.30 | **no** | `b200_sxm-x347-nvl72-hybrid` | 430.4 | 860.1-860.1 | 2.50 | yes | 5.249x | 0.433x | 0.083x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 881.9 | 153.4-153.4 | 28.75 | **no** | `b200_sxm-x173-nvl72-hybrid` | 176.2 | 191.5-191.5 | 4.60 | yes | 5.005x | 0.801x | 0.160x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 792.0 | 94.9-94.9 | 41.75 | **no** | `b200_sxm-x347-nvl72-hybrid` | 240.0 | 325.6-325.6 | 3.69 | yes | 3.299x | 0.291x | 0.088x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 345.6 | 96.9-96.9 | 17.84 | **no** | `b200_sxm-x200-nvl72-hybrid` | 96.9 | 104.3-104.3 | 4.65 | yes | 3.566x | 0.929x | 0.260x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 215.4 | 23.0-23.0 | 46.76 | **no** | `b200_sxm-x347-nvl72-hybrid` | 127.4 | 155.7-155.7 | 4.09 | yes | 1.691x | 0.148x | 0.087x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.042x to 0.260x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,100.9 | 1,011.9-1,011.9 | 20.26 | **no** | `a100_sxm_80gb-x208-tensor` | 285.7 | 827.9-827.9 | 1.73 | yes | 14.353x | 1.222x | 0.085x |
| MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,649.2 | 1,549.1-1,549.1 | 11.78 | **no** | `a100_sxm_80gb-x280-tensor` | 287.9 | 834.7-834.7 | 1.72 | yes | 12.673x | 1.856x | 0.146x |
| MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,100.9 | 1,011.9-1,011.9 | 20.26 | **no** | `a100_sxm_80gb-x208-hybrid` | 260.9 | 755.7-755.7 | 1.73 | yes | 15.718x | 1.339x | 0.085x |
| MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,649.2 | 1,549.1-1,549.1 | 11.78 | **no** | `a100_sxm_80gb-x280-hybrid` | 263.0 | 767.4-767.4 | 1.71 | yes | 13.875x | 2.019x | 0.145x |
| MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,100.9 | 1,011.9-1,011.9 | 20.26 | **no** | `a100_sxm_80gb-x208-hybrid` | 260.9 | 755.7-755.7 | 1.73 | yes | 15.718x | 1.339x | 0.085x |
| MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,649.2 | 1,549.1-1,549.1 | 11.78 | **no** | `a100_sxm_80gb-x280-hybrid` | 263.0 | 767.4-767.4 | 1.71 | yes | 13.875x | 2.019x | 0.145x |
| MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,100.9 | 1,011.9-1,011.9 | 20.26 | **no** | `a100_sxm_80gb-x208-hybrid` | 236.8 | 665.0-665.0 | 1.78 | yes | 17.316x | 1.522x | 0.088x |
| MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,649.2 | 1,549.1-1,549.1 | 11.78 | **no** | `a100_sxm_80gb-x280-hybrid` | 247.0 | 611.7-611.7 | 2.02 | yes | 14.772x | 2.533x | 0.171x |
| MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 4,086.5 | 969.9-969.9 | 21.07 | **no** | `a100_sxm_80gb-x249-hybrid` | 217.8 | 515.2-515.2 | 2.11 | yes | 18.766x | 1.883x | 0.100x |
| MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,642.9 | 696.4-696.4 | 26.16 | **no** | `a100_sxm_80gb-x672-hybrid` | 252.2 | 654.2-654.2 | 1.93 | yes | 14.442x | 1.065x | 0.074x |
| MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 3,837.2 | 504.6-504.6 | 38.02 | **no** | `a100_sxm_80gb-x249-hybrid` | 211.9 | 584.6-584.6 | 1.81 | yes | 18.110x | 0.863x | 0.048x |
| MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,274.2 | 367.1-367.1 | 44.60 | **no** | `a100_sxm_80gb-x672-hybrid` | 228.4 | 602.5-602.5 | 1.90 | yes | 14.338x | 0.609x | 0.042x |
| MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 3,568.8 | 493.6-493.6 | 36.15 | **no** | `a100_sxm_80gb-x373-hybrid` | 198.9 | 540.0-540.0 | 1.84 | yes | 17.939x | 0.914x | 0.051x |
| MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,736.1 | 363.4-363.4 | 37.64 | **no** | `a100_sxm_80gb-x672-hybrid` | 211.4 | 624.4-624.4 | 1.69 | yes | 12.944x | 0.582x | 0.045x |
| MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 1,932.0 | 128.3-128.3 | 75.27 | **no** | `a100_sxm_80gb-x373-hybrid` | 116.4 | 271.9-271.9 | 2.14 | yes | 16.599x | 0.472x | 0.028x |
| MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,183.6 | 93.6-93.6 | 63.22 | **no** | `a100_sxm_80gb-x672-hybrid` | 152.1 | 389.6-389.6 | 1.95 | yes | 7.782x | 0.240x | 0.031x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 782.0 | 130.2-130.2 | 30.02 | **no** | `a100_sxm_80gb-x373-hybrid` | 49.0 | 134.0-134.0 | 1.83 | yes | 15.944x | 0.972x | 0.061x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 345.9 | 23.6-23.6 | 73.35 | **no** | `a100_sxm_80gb-x672-hybrid` | 71.5 | 183.7-183.7 | 1.95 | yes | 4.840x | 0.128x | 0.027x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 231.4 | 33.4-33.4 | 34.59 | **no** | `a100_sxm_80gb-x373-hybrid` | 22.4 | 58.7-58.7 | 1.91 | yes | 10.328x | 0.569x | 0.055x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 89.5 | 22.5-22.5 | 19.86 | **no** | `a100_sxm_80gb-x672-hybrid` | 29.5 | 83.6-83.6 | 1.76 | yes | 3.040x | 0.269x | 0.089x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.027x to 0.171x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-qwen3-8b-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x180` | 3,783.5 | not applicable | -- | -- | `b200_sxm-x92-nvl72-hybrid` | 1,110.5 | not applicable | -- | -- | 3.407x | -- | -- |
| Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 8,249.0 | not applicable | -- | -- | `b200_sxm-x58-nvl72-tensor` | 1,276.4 | not applicable | -- | -- | 6.463x | -- | -- |

### `n6_vs_a100-qwen3-8b-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x227` | 3,567.0 | not applicable | -- | -- | `a100_sxm_80gb-x224-tensor` | 575.1 | not applicable | -- | -- | 6.202x | -- | -- |
| Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 8,205.5 | not applicable | -- | -- | `a100_sxm_80gb-x112-tensor` | 459.8 | not applicable | -- | -- | 17.845x | -- | -- |

### `n5_vs_b200-qwen3-8b-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x60-romfill` | 7,120.3 | not applicable | -- | -- | `b200_sxm-x31-nvl72-tensor` | 1,745.3 | not applicable | -- | -- | 4.080x | -- | -- |
| Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 9,134.8 | not applicable | -- | -- | `b200_sxm-x29-nvl72-tensor` | 1,699.9 | not applicable | -- | -- | 5.374x | -- | -- |
| Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x139-romfill` | 3,018.8 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | not applicable | -- | -- | 1.587x | -- | -- |
| Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,737.9 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | not applicable | -- | -- | 1.439x | -- | -- |
| Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,737.9 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | not applicable | -- | -- | 1.439x | -- | -- |
| Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,737.9 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | not applicable | -- | -- | 1.439x | -- | -- |
| Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,737.9 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | not applicable | -- | -- | 1.439x | -- | -- |
| Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1,809.5 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,865.9 | not applicable | -- | -- | 0.970x | -- | -- |
| Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 602.2 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,280.5 | not applicable | -- | -- | 0.470x | -- | -- |
| Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 158.3 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 593.6 | not applicable | -- | -- | 0.267x | -- | -- |
| Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 40.0 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 190.4 | not applicable | -- | -- | 0.210x | -- | -- |

### `n6_vs_a100-qwen3-8b-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 7,114.3 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 564.5 | not applicable | -- | -- | 12.604x | -- | -- |
| Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 9,194.4 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 564.5 | not applicable | -- | -- | 16.289x | -- | -- |
| Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196-romfill` | 2,704.1 | not applicable | -- | -- | `a100_sxm_80gb-x10969-tensor` | 584.4 | not applicable | -- | -- | 4.627x | -- | -- |
| Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 2,461.8 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 555.9 | not applicable | -- | -- | 4.429x | -- | -- |
| Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 2,041.1 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 555.9 | not applicable | -- | -- | 3.672x | -- | -- |
| Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 1,518.6 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 555.9 | not applicable | -- | -- | 2.732x | -- | -- |
| Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,490.4 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 555.9 | not applicable | -- | -- | 2.681x | -- | -- |
| Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,191.2 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 555.9 | not applicable | -- | -- | 2.143x | -- | -- |
| Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 354.2 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 502.9 | not applicable | -- | -- | 0.704x | -- | -- |
| Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 91.5 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 285.1 | not applicable | -- | -- | 0.321x | -- | -- |
| Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 23.0 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 117.9 | not applicable | -- | -- | 0.195x | -- | -- |

### `n5_vs_b200-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 3,387.3 | 501.3-501.3 | 33.79 | **no** | `b200_sxm-x58-nvl72-tensor` | 767.6 | 1,687.6-1,687.6 | 2.27 | yes | 4.413x | 0.297x | 0.067x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3,790.6 | 1,671.8-1,671.8 | 11.34 | **no** | `b200_sxm-x58-nvl72-tensor` | 767.6 | 1,687.6-1,687.6 | 2.27 | yes | 4.939x | 0.991x | 0.201x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2,745.8 | 1,471.8-1,471.8 | 9.33 | **no** | `b200_sxm-x142-nvl72-hybrid` | 766.7 | 1,677.0-1,677.0 | 2.29 | yes | 3.581x | 0.878x | 0.245x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,786.1 | 6,026.0-6,026.0 | 2.31 | yes | `b200_sxm-x953-nvl72-hybrid` | 747.6 | 1,573.8-1,573.8 | 2.38 | yes | 3.727x | 3.829x | 1.027x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2,745.8 | 1,471.8-1,471.8 | 9.33 | **no** | `b200_sxm-x142-nvl72-hybrid` | 747.7 | 1,640.5-1,640.5 | 2.28 | yes | 3.672x | 0.897x | 0.244x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,786.1 | 6,026.0-6,026.0 | 2.31 | yes | `b200_sxm-x953-nvl72-hybrid` | 747.6 | 1,573.8-1,573.8 | 2.38 | yes | 3.727x | 3.829x | 1.027x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2,745.8 | 1,471.8-1,471.8 | 9.33 | **no** | `b200_sxm-x142-nvl72-hybrid` | 724.3 | 1,521.6-1,521.6 | 2.38 | yes | 3.791x | 0.967x | 0.255x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,786.1 | 6,026.0-6,026.0 | 2.31 | yes | `b200_sxm-x953-nvl72-hybrid` | 747.6 | 1,573.8-1,573.8 | 2.38 | yes | 3.727x | 3.829x | 1.027x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2,745.8 | 1,471.8-1,471.8 | 9.33 | **no** | `b200_sxm-x142-nvl72-hybrid` | 724.3 | 1,521.6-1,521.6 | 2.38 | yes | 3.791x | 0.967x | 0.255x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,786.1 | 6,026.0-6,026.0 | 2.31 | yes | `b200_sxm-x953-nvl72-hybrid` | 737.6 | 1,508.2-1,508.2 | 2.45 | yes | 3.777x | 3.996x | 1.058x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2,745.8 | 1,471.8-1,471.8 | 9.33 | **no** | `b200_sxm-x142-nvl72-hybrid` | 631.0 | 1,063.3-1,063.3 | 2.97 | yes | 4.351x | 1.384x | 0.318x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,786.1 | 6,026.0-6,026.0 | 2.31 | yes | `b200_sxm-x953-nvl72-hybrid` | 717.0 | 1,435.7-1,435.7 | 2.50 | yes | 3.886x | 4.197x | 1.080x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,713.1 | 914.2-914.2 | 14.84 | **no** | `b200_sxm-x173-nvl72-hybrid` | 570.4 | 1,041.4-1,041.4 | 2.74 | yes | 4.757x | 0.878x | 0.185x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,585.1 | 4,566.2-4,566.2 | 2.83 | yes | `b200_sxm-x953-nvl72-hybrid` | 707.0 | 1,195.0-1,195.0 | 2.96 | yes | 3.656x | 3.821x | 1.045x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 1,579.6 | 169.2-169.2 | 46.69 | **no** | `b200_sxm-x178-pipeline` | 375.3 | 618.6-618.6 | 3.03 | yes | 4.209x | 0.273x | 0.065x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,697.1 | 1,759.8-1,759.8 | 4.82 | yes | `b200_sxm-x953-nvl72-hybrid` | 616.5 | 877.7-877.7 | 3.51 | yes | 2.753x | 2.005x | 0.728x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 576.3 | 79.4-79.4 | 36.29 | **no** | `b200_sxm-x178-pipeline` | 173.4 | 248.4-248.4 | 3.49 | yes | 3.323x | 0.320x | 0.096x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 635.2 | 67.7-67.7 | 46.89 | **no** | `b200_sxm-x953-pipeline` | 417.8 | 366.8-366.8 | 5.69 | **no** | 1.520x | 0.185x | 0.121x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 144.5 | 55.1-55.1 | 13.12 | **no** | `b200_sxm-x178-pipeline` | 58.3 | 147.4-147.4 | 1.98 | yes | 2.477x | 0.374x | 0.151x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 175.7 | 17.0-17.0 | 51.61 | **no** | `b200_sxm-x953-pipeline` | 210.8 | 226.8-226.8 | 4.65 | yes | 0.834x | 0.075x | 0.090x |

**Does the ratio compress?** Of 20 class rows in this study, 14 move the ROM-versus-GPU ratio DOWN under speculation and 6 move it UP. The movement spans 0.065x to 1.080x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 7 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x44` | 4,377.2 | 1,268.2-1,268.2 | 17.26 | **no** | `b200_sxm-x22-nvl72-tensor` | 857.3 | 3,120.1-3,120.1 | 1.37 | yes | 5.106x | 0.406x | 0.080x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,240.3 | 1,201.4-1,201.4 | 17.65 | **no** | `b200_sxm-x58-nvl72-tensor` | 885.0 | 3,307.0-3,307.0 | 1.34 | yes | 4.791x | 0.363x | 0.076x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 4,351.3 | 1,103.8-1,103.8 | 19.71 | **no** | `b200_sxm-x26-nvl72-tensor` | 831.0 | 2,629.9-2,629.9 | 1.58 | yes | 5.236x | 0.420x | 0.080x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,240.3 | 1,201.4-1,201.4 | 17.65 | **no** | `b200_sxm-x58-nvl72-tensor` | 854.2 | 2,739.6-2,739.6 | 1.56 | yes | 4.964x | 0.439x | 0.088x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 4,351.3 | 1,103.8-1,103.8 | 19.71 | **no** | `b200_sxm-x26-hybrid` | 814.8 | 2,504.3-2,504.3 | 1.63 | yes | 5.341x | 0.441x | 0.083x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,240.3 | 1,201.4-1,201.4 | 17.65 | **no** | `b200_sxm-x58-hybrid` | 823.4 | 2,533.7-2,533.7 | 1.62 | yes | 5.150x | 0.474x | 0.092x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 4,351.3 | 1,103.8-1,103.8 | 19.71 | **no** | `b200_sxm-x26-hybrid` | 755.4 | 1,978.0-1,978.0 | 1.91 | yes | 5.760x | 0.558x | 0.097x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,240.3 | 1,201.4-1,201.4 | 17.65 | **no** | `b200_sxm-x58-hybrid` | 823.4 | 2,533.7-2,533.7 | 1.62 | yes | 5.150x | 0.474x | 0.092x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 4,311.3 | 1,133.3-1,133.3 | 19.02 | **no** | `b200_sxm-x44-hybrid` | 737.6 | 1,826.2-1,826.2 | 2.02 | yes | 5.845x | 0.621x | 0.106x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,240.3 | 1,201.4-1,201.4 | 17.65 | **no** | `b200_sxm-x58-hybrid` | 765.5 | 2,020.3-2,020.3 | 1.89 | yes | 5.539x | 0.595x | 0.107x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,249.7 | 1,141.4-1,141.4 | 18.62 | **no** | `b200_sxm-x173-nvl72-hybrid` | 801.8 | 2,219.6-2,219.6 | 1.81 | yes | 5.300x | 0.514x | 0.097x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,230.4 | 1,220.3-1,220.3 | 17.33 | **no** | `b200_sxm-x116-nvl72-hybrid` | 770.8 | 2,013.9-2,013.9 | 1.91 | yes | 5.488x | 0.606x | 0.110x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,249.7 | 1,141.4-1,141.4 | 18.62 | **no** | `b200_sxm-x173-nvl72-hybrid` | 730.7 | 1,732.2-1,732.2 | 2.11 | yes | 5.816x | 0.659x | 0.113x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,230.4 | 1,220.3-1,220.3 | 17.33 | **no** | `b200_sxm-x231-nvl72-hybrid` | 758.6 | 1,854.7-1,854.7 | 2.05 | yes | 5.576x | 0.658x | 0.118x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,282.0 | 569.7-569.7 | 28.81 | **no** | `b200_sxm-x173-nvl72-hybrid` | 489.5 | 851.7-851.7 | 2.87 | yes | 6.704x | 0.669x | 0.100x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,892.8 | 633.6-633.6 | 30.72 | **no** | `b200_sxm-x347-nvl72-hybrid` | 609.6 | 1,150.3-1,150.3 | 2.65 | yes | 6.386x | 0.551x | 0.086x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,633.5 | 262.4-262.4 | 31.13 | **no** | `b200_sxm-x173-nvl72-hybrid` | 251.0 | 448.5-448.5 | 2.80 | yes | 6.507x | 0.585x | 0.090x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,697.5 | 311.7-311.7 | 43.27 | **no** | `b200_sxm-x347-nvl72-hybrid` | 360.7 | 603.3-603.3 | 2.99 | yes | 7.478x | 0.517x | 0.069x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 503.6 | 166.3-166.3 | 15.14 | **no** | `b200_sxm-x173-nvl72-hybrid` | 121.3 | 185.7-185.7 | 3.27 | yes | 4.150x | 0.896x | 0.216x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,013.1 | 238.6-238.6 | 21.23 | **no** | `b200_sxm-x347-nvl72-hybrid` | 171.1 | 286.7-286.7 | 2.98 | yes | 5.922x | 0.832x | 0.141x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.069x to 0.216x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4,355.9 | 1,187.0-1,187.0 | 18.35 | **no** | `b200_sxm-x24-nvl72-tensor` | 864.4 | 3,222.4-3,222.4 | 1.34 | yes | 5.039x | 0.368x | 0.073x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,268.0 | 1,211.4-1,211.4 | 17.62 | **no** | `b200_sxm-x58-nvl72-tensor` | 888.4 | 3,389.7-3,389.7 | 1.31 | yes | 4.804x | 0.357x | 0.074x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4,355.9 | 1,187.0-1,187.0 | 18.35 | **no** | `b200_sxm-x24-hybrid` | 849.3 | 2,749.3-2,749.3 | 1.54 | yes | 5.129x | 0.432x | 0.084x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,268.0 | 1,211.4-1,211.4 | 17.62 | **no** | `b200_sxm-x58-nvl72-tensor` | 860.7 | 2,854.9-2,854.9 | 1.51 | yes | 4.959x | 0.424x | 0.086x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4,355.9 | 1,187.0-1,187.0 | 18.35 | **no** | `b200_sxm-x24-hybrid` | 830.8 | 2,539.1-2,539.1 | 1.64 | yes | 5.243x | 0.467x | 0.089x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,268.0 | 1,211.4-1,211.4 | 17.62 | **no** | `b200_sxm-x58-hybrid` | 826.5 | 2,577.7-2,577.7 | 1.60 | yes | 5.164x | 0.470x | 0.091x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4,355.9 | 1,187.0-1,187.0 | 18.35 | **no** | `b200_sxm-x24-hybrid` | 765.1 | 1,972.3-1,972.3 | 1.94 | yes | 5.693x | 0.602x | 0.106x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,268.0 | 1,211.4-1,211.4 | 17.62 | **no** | `b200_sxm-x58-hybrid` | 826.5 | 2,577.7-2,577.7 | 1.60 | yes | 5.164x | 0.470x | 0.091x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 4,340.6 | 1,140.1-1,140.1 | 19.04 | **no** | `b200_sxm-x44-hybrid` | 744.4 | 1,888.2-1,888.2 | 1.97 | yes | 5.831x | 0.604x | 0.104x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,268.0 | 1,211.4-1,211.4 | 17.62 | **no** | `b200_sxm-x58-hybrid` | 770.9 | 2,076.8-2,076.8 | 1.86 | yes | 5.536x | 0.583x | 0.105x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,278.1 | 1,148.2-1,148.2 | 18.63 | **no** | `b200_sxm-x173-nvl72-hybrid` | 806.1 | 2,268.7-2,268.7 | 1.78 | yes | 5.307x | 0.506x | 0.095x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,257.6 | 1,230.9-1,230.9 | 17.30 | **no** | `b200_sxm-x116-nvl72-hybrid` | 776.6 | 2,073.8-2,073.8 | 1.87 | yes | 5.482x | 0.594x | 0.108x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,278.1 | 1,148.2-1,148.2 | 18.63 | **no** | `b200_sxm-x173-nvl72-hybrid` | 737.8 | 1,792.9-1,792.9 | 2.06 | yes | 5.798x | 0.640x | 0.110x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,257.6 | 1,230.9-1,230.9 | 17.30 | **no** | `b200_sxm-x231-nvl72-hybrid` | 764.4 | 1,907.1-1,907.1 | 2.00 | yes | 5.570x | 0.645x | 0.116x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,393.8 | 574.8-574.8 | 29.52 | **no** | `b200_sxm-x173-nvl72-hybrid` | 502.6 | 912.4-912.4 | 2.75 | yes | 6.753x | 0.630x | 0.093x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,018.6 | 638.3-638.3 | 31.48 | **no** | `b200_sxm-x347-nvl72-hybrid` | 619.6 | 1,204.4-1,204.4 | 2.57 | yes | 6.486x | 0.530x | 0.082x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,747.7 | 266.8-266.8 | 32.75 | **no** | `b200_sxm-x173-nvl72-hybrid` | 258.8 | 377.0-377.0 | 3.43 | yes | 6.752x | 0.708x | 0.105x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,867.5 | 314.7-314.7 | 45.56 | **no** | `b200_sxm-x347-nvl72-hybrid` | 362.9 | 635.9-635.9 | 2.85 | yes | 7.901x | 0.495x | 0.063x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 547.7 | 173.7-173.7 | 15.76 | **no** | `b200_sxm-x173-nvl72-hybrid` | 127.9 | 205.4-205.4 | 3.11 | yes | 4.284x | 0.846x | 0.197x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,113.7 | 246.3-246.3 | 22.61 | **no** | `b200_sxm-x347-nvl72-hybrid` | 175.1 | 309.8-309.8 | 2.83 | yes | 6.359x | 0.795x | 0.125x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.063x to 0.197x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 375.6-375.6 | 26.18 | **no** | `b200_sxm-x157-nvl72-hybrid` | 570.7 | 1,674.0-1,674.0 | 1.70 | yes | 3.446x | 0.224x | 0.065x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 2,132.7 | 913.5-913.5 | 11.67 | **no** | `b200_sxm-x116-nvl72-hybrid` | 574.9 | 1,705.4-1,705.4 | 1.69 | yes | 3.710x | 0.536x | 0.144x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 375.6-375.6 | 26.18 | **no** | `b200_sxm-x157-nvl72-hybrid` | 570.7 | 1,674.0-1,674.0 | 1.70 | yes | 3.446x | 0.224x | 0.065x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,080.6 | 875.8-875.8 | 11.88 | **no** | `b200_sxm-x289-nvl72-hybrid` | 571.7 | 1,650.3-1,650.3 | 1.73 | yes | 3.639x | 0.531x | 0.146x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 375.6-375.6 | 26.18 | **no** | `b200_sxm-x157-nvl72-hybrid` | 554.1 | 1,474.6-1,474.6 | 1.88 | yes | 3.550x | 0.255x | 0.072x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,080.6 | 875.8-875.8 | 11.88 | **no** | `b200_sxm-x289-nvl72-hybrid` | 571.7 | 1,650.3-1,650.3 | 1.73 | yes | 3.639x | 0.531x | 0.146x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 375.6-375.6 | 26.18 | **no** | `b200_sxm-x157-nvl72-hybrid` | 547.6 | 1,441.6-1,441.6 | 1.90 | yes | 3.592x | 0.261x | 0.073x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,080.6 | 875.8-875.8 | 11.88 | **no** | `b200_sxm-x289-nvl72-hybrid` | 545.3 | 1,514.5-1,514.5 | 1.80 | yes | 3.816x | 0.578x | 0.152x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 375.6-375.6 | 26.18 | **no** | `b200_sxm-x157-nvl72-hybrid` | 511.2 | 1,158.2-1,158.2 | 2.21 | yes | 3.848x | 0.324x | 0.084x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,080.6 | 875.8-875.8 | 11.88 | **no** | `b200_sxm-x289-nvl72-hybrid` | 539.9 | 1,340.0-1,340.0 | 2.01 | yes | 3.853x | 0.654x | 0.170x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 375.6-375.6 | 26.18 | **no** | `b200_sxm-x157-nvl72-hybrid` | 434.7 | 791.8-791.8 | 2.75 | yes | 4.524x | 0.474x | 0.105x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,080.6 | 875.8-875.8 | 11.88 | **no** | `b200_sxm-x289-nvl72-hybrid` | 498.8 | 1,062.0-1,062.0 | 2.35 | yes | 4.171x | 0.825x | 0.198x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,953.8 | 198.2-198.2 | 49.30 | **no** | `b200_sxm-x157-nvl72-hybrid` | 350.1 | 618.4-618.4 | 2.83 | yes | 5.581x | 0.320x | 0.057x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,998.4 | 471.0-471.0 | 21.21 | **no** | `b200_sxm-x289-nvl72-hybrid` | 420.7 | 721.2-721.2 | 2.92 | yes | 4.750x | 0.653x | 0.137x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,320.2 | 89.6-89.6 | 73.66 | **no** | `b200_sxm-x173-nvl72-hybrid` | 188.3 | 251.5-251.5 | 3.74 | yes | 7.013x | 0.356x | 0.051x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,479.2 | 233.7-233.7 | 31.64 | **no** | `b200_sxm-x347-nvl72-hybrid` | 269.8 | 397.2-397.2 | 3.40 | yes | 5.482x | 0.588x | 0.107x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 529.2 | 42.7-42.7 | 62.03 | **no** | `b200_sxm-x173-nvl72-hybrid` | 74.5 | 120.3-120.3 | 3.10 | yes | 7.105x | 0.354x | 0.050x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 671.5 | 59.7-59.7 | 56.25 | **no** | `b200_sxm-x347-nvl72-hybrid` | 121.6 | 173.9-173.9 | 3.49 | yes | 5.524x | 0.343x | 0.062x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 149.7 | 32.1-32.1 | 23.29 | **no** | `b200_sxm-x173-nvl72-hybrid` | 29.4 | 48.9-48.9 | 3.01 | yes | 5.092x | 0.657x | 0.129x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 198.8 | 22.2-22.2 | 44.68 | **no** | `b200_sxm-x347-nvl72-hybrid` | 45.4 | 75.5-75.5 | 3.00 | yes | 4.380x | 0.295x | 0.067x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.050x to 0.198x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 431.6-431.6 | 23.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 594.5 | 1,976.3-1,976.3 | 1.50 | yes | 3.441x | 0.218x | 0.063x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,253.4 | 898.3-898.3 | 12.54 | **no** | `b200_sxm-x144-nvl72-hybrid` | 595.8 | 1,984.4-1,984.4 | 1.50 | yes | 3.782x | 0.453x | 0.120x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 431.6-431.6 | 23.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 594.5 | 1,976.3-1,976.3 | 1.50 | yes | 3.441x | 0.218x | 0.063x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,253.4 | 898.3-898.3 | 12.54 | **no** | `b200_sxm-x144-nvl72-hybrid` | 595.8 | 1,984.4-1,984.4 | 1.50 | yes | 3.782x | 0.453x | 0.120x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 431.6-431.6 | 23.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 568.7 | 1,706.2-1,706.2 | 1.67 | yes | 3.598x | 0.253x | 0.070x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,253.4 | 898.3-898.3 | 12.54 | **no** | `b200_sxm-x144-nvl72-hybrid` | 570.6 | 1,717.3-1,717.3 | 1.66 | yes | 3.949x | 0.523x | 0.132x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 431.6-431.6 | 23.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 559.1 | 1,606.4-1,606.4 | 1.74 | yes | 3.659x | 0.269x | 0.073x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,253.4 | 898.3-898.3 | 12.54 | **no** | `b200_sxm-x144-nvl72-hybrid` | 564.3 | 1,631.3-1,631.3 | 1.73 | yes | 3.993x | 0.551x | 0.138x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 431.6-431.6 | 23.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 520.0 | 1,277.1-1,277.1 | 2.04 | yes | 3.935x | 0.338x | 0.086x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,253.4 | 898.3-898.3 | 12.54 | **no** | `b200_sxm-x144-nvl72-hybrid` | 525.6 | 1,297.9-1,297.9 | 2.02 | yes | 4.287x | 0.692x | 0.161x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 431.6-431.6 | 23.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 449.0 | 913.5-913.5 | 2.46 | yes | 4.557x | 0.473x | 0.104x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,237.3 | 901.0-901.0 | 12.42 | **no** | `b200_sxm-x347-nvl72-hybrid` | 532.6 | 1,282.3-1,282.3 | 2.08 | yes | 4.201x | 0.703x | 0.167x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,024.2 | 226.9-226.9 | 44.60 | **no** | `b200_sxm-x137-nvl72-hybrid` | 354.7 | 590.2-590.2 | 3.00 | yes | 5.707x | 0.384x | 0.067x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,190.2 | 474.1-474.1 | 23.10 | **no** | `b200_sxm-x347-nvl72-hybrid` | 469.9 | 932.1-932.1 | 2.52 | yes | 4.661x | 0.509x | 0.109x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,406.1 | 90.9-90.9 | 77.38 | **no** | `b200_sxm-x173-nvl72-hybrid` | 203.7 | 321.0-321.0 | 3.17 | yes | 6.902x | 0.283x | 0.041x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,826.7 | 238.9-238.9 | 38.23 | **no** | `b200_sxm-x347-nvl72-hybrid` | 287.6 | 471.0-471.0 | 3.05 | yes | 6.351x | 0.507x | 0.080x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 661.6 | 43.8-43.8 | 75.55 | **no** | `b200_sxm-x173-nvl72-hybrid` | 82.5 | 129.5-129.5 | 3.19 | yes | 8.016x | 0.338x | 0.042x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,015.4 | 60.9-60.9 | 83.35 | **no** | `b200_sxm-x347-nvl72-hybrid` | 129.4 | 195.9-195.9 | 3.30 | yes | 7.849x | 0.311x | 0.040x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 193.8 | 34.9-34.9 | 27.80 | **no** | `b200_sxm-x173-nvl72-hybrid` | 37.5 | 45.2-45.2 | 4.15 | yes | 5.162x | 0.772x | 0.149x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 396.8 | 76.4-76.4 | 25.98 | **no** | `b200_sxm-x347-nvl72-hybrid` | 53.4 | 74.5-74.5 | 3.58 | yes | 7.433x | 1.025x | 0.138x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.040x to 0.167x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 445.2-445.2 | 24.26 | **no** | `b200_sxm-x134-nvl72-hybrid` | 596.4 | 2,017.2-2,017.2 | 1.48 | yes | 3.622x | 0.221x | 0.061x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,309.2 | 903.5-903.5 | 12.78 | **no** | `b200_sxm-x144-nvl72-hybrid` | 598.2 | 2,029.7-2,029.7 | 1.47 | yes | 3.860x | 0.445x | 0.115x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 445.2-445.2 | 24.26 | **no** | `b200_sxm-x134-nvl72-hybrid` | 596.4 | 2,017.2-2,017.2 | 1.48 | yes | 3.622x | 0.221x | 0.061x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,309.2 | 903.5-903.5 | 12.78 | **no** | `b200_sxm-x144-nvl72-hybrid` | 598.2 | 2,029.7-2,029.7 | 1.47 | yes | 3.860x | 0.445x | 0.115x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 445.2-445.2 | 24.26 | **no** | `b200_sxm-x134-nvl72-hybrid` | 570.7 | 1,745.7-1,745.7 | 1.63 | yes | 3.785x | 0.255x | 0.067x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,309.2 | 903.5-903.5 | 12.78 | **no** | `b200_sxm-x144-nvl72-hybrid` | 573.6 | 1,762.6-1,762.6 | 1.63 | yes | 4.026x | 0.513x | 0.127x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 445.2-445.2 | 24.26 | **no** | `b200_sxm-x134-nvl72-hybrid` | 558.9 | 1,623.0-1,623.0 | 1.72 | yes | 3.865x | 0.274x | 0.071x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,309.2 | 903.5-903.5 | 12.78 | **no** | `b200_sxm-x144-nvl72-hybrid` | 566.5 | 1,660.5-1,660.5 | 1.71 | yes | 4.076x | 0.544x | 0.133x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 445.2-445.2 | 24.26 | **no** | `b200_sxm-x134-nvl72-hybrid` | 520.7 | 1,299.4-1,299.4 | 2.00 | yes | 4.148x | 0.343x | 0.083x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,309.2 | 903.5-903.5 | 12.78 | **no** | `b200_sxm-x144-nvl72-hybrid` | 529.0 | 1,331.1-1,331.1 | 1.99 | yes | 4.365x | 0.679x | 0.156x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 445.2-445.2 | 24.26 | **no** | `b200_sxm-x134-nvl72-hybrid` | 451.2 | 939.0-939.0 | 2.40 | yes | 4.788x | 0.474x | 0.099x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,306.9 | 474.4-474.4 | 24.32 | **no** | `b200_sxm-x144-nvl72-hybrid` | 460.2 | 963.6-963.6 | 2.39 | yes | 5.013x | 0.492x | 0.098x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 2,103.9 | 229.1-229.1 | 45.92 | **no** | `b200_sxm-x157-nvl72-hybrid` | 379.7 | 666.5-666.5 | 2.85 | yes | 5.542x | 0.344x | 0.062x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,298.1 | 476.3-476.3 | 24.12 | **no** | `b200_sxm-x347-nvl72-hybrid` | 474.4 | 960.1-960.1 | 2.47 | yes | 4.845x | 0.496x | 0.102x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,465.3 | 171.6-171.6 | 42.69 | **no** | `b200_sxm-x173-nvl72-hybrid` | 204.2 | 335.8-335.8 | 3.04 | yes | 7.175x | 0.511x | 0.071x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,914.2 | 240.0-240.0 | 39.88 | **no** | `b200_sxm-x347-nvl72-hybrid` | 288.1 | 487.2-487.2 | 2.96 | yes | 6.643x | 0.493x | 0.074x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 687.0 | 44.0-44.0 | 78.14 | **no** | `b200_sxm-x173-nvl72-hybrid` | 82.9 | 139.2-139.2 | 2.98 | yes | 8.290x | 0.316x | 0.038x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,050.0 | 61.1-61.1 | 85.92 | **no** | `b200_sxm-x347-nvl72-hybrid` | 129.8 | 206.8-206.8 | 3.14 | yes | 8.091x | 0.295x | 0.037x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 202.6 | 35.3-35.3 | 28.70 | **no** | `b200_sxm-x173-nvl72-hybrid` | 39.2 | 49.2-49.2 | 3.99 | yes | 5.165x | 0.718x | 0.139x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 415.4 | 120.6-120.6 | 17.22 | **no** | `b200_sxm-x347-nvl72-hybrid` | 53.9 | 79.9-79.9 | 3.37 | yes | 7.705x | 1.510x | 0.196x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.037x to 0.196x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x152` | 3,050.2 | 385.0-385.0 | 39.61 | **no** | `a100_sxm_80gb-x150-hybrid` | 332.4 | 539.3-539.3 | 3.08 | yes | 9.177x | 0.714x | 0.078x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 3,722.8 | 1,268.4-1,268.4 | 14.67 | **no** | `a100_sxm_80gb-x168-hybrid` | 332.9 | 535.8-535.8 | 3.11 | yes | 11.184x | 2.367x | 0.212x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,523.9 | 556.4-556.4 | 22.68 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 469.0-469.0 | 3.45 | yes | 7.795x | 1.186x | 0.152x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,432.9 | 341.0-341.0 | 35.67 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 276.3-276.3 | 5.88 | **no** | 7.489x | 1.234x | 0.165x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,523.9 | 556.4-556.4 | 22.68 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 469.0-469.0 | 3.45 | yes | 7.795x | 1.186x | 0.152x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,432.9 | 341.0-341.0 | 35.67 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 276.3-276.3 | 5.88 | **no** | 7.489x | 1.234x | 0.165x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,523.9 | 556.4-556.4 | 22.68 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 469.0-469.0 | 3.45 | yes | 7.795x | 1.186x | 0.152x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,432.9 | 341.0-341.0 | 35.67 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 276.3-276.3 | 5.88 | **no** | 7.489x | 1.234x | 0.165x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,523.9 | 556.4-556.4 | 22.68 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 469.0-469.0 | 3.45 | yes | 7.795x | 1.186x | 0.152x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,432.9 | 341.0-341.0 | 35.67 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 276.3-276.3 | 5.88 | **no** | 7.489x | 1.234x | 0.165x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,444.6 | 306.8-306.8 | 39.84 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 469.0-469.0 | 3.45 | yes | 7.550x | 0.654x | 0.087x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,432.9 | 341.0-341.0 | 35.67 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 276.3-276.3 | 5.88 | **no** | 7.489x | 1.234x | 0.165x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 2,178.3 | 677.6-677.6 | 16.07 | **no** | `a100_sxm_80gb-x387-hybrid` | 296.8 | 396.7-396.7 | 3.74 | yes | 7.340x | 1.708x | 0.233x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,234.3 | 338.4-338.4 | 33.01 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 276.3-276.3 | 5.88 | **no** | 6.878x | 1.225x | 0.178x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,189.6 | 79.4-79.4 | 74.91 | **no** | `a100_sxm_80gb-x387-hybrid` | 175.3 | 206.7-206.7 | 4.24 | yes | 6.786x | 0.384x | 0.057x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,232.5 | 97.6-97.6 | 63.12 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 276.3-276.3 | 5.88 | **no** | 3.794x | 0.353x | 0.093x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 359.8 | 38.3-38.3 | 46.92 | **no** | `a100_sxm_80gb-x387-hybrid` | 80.5 | 102.5-102.5 | 3.93 | yes | 4.467x | 0.374x | 0.084x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 390.1 | 24.6-24.6 | 79.12 | **no** | `a100_sxm_80gb-x2574-hybrid` | 222.0 | 138.7-138.7 | 8.00 | **no** | 1.757x | 0.178x | 0.101x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 93.6 | 31.1-31.1 | 15.07 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 103.3 | 6.2-6.2 | 83.67 | **no** | `a100_sxm_80gb-x2574-hybrid` | 111.7 | 60.7-60.7 | 9.19 | **no** | 0.925x | 0.102x | 0.110x |

**Does the ratio compress?** Of 19 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.057x to 0.233x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 10 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 4,175.0 | 774.3-774.3 | 26.96 | **no** | `a100_sxm_80gb-x73-hybrid` | 404.0 | 978.5-978.5 | 2.06 | yes | 10.335x | 0.791x | 0.077x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,951.3 | 991.7-991.7 | 19.92 | **no** | `a100_sxm_80gb-x112-hybrid` | 413.4 | 991.1-991.1 | 2.09 | yes | 9.559x | 1.001x | 0.105x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 4,175.0 | 774.3-774.3 | 26.96 | **no** | `a100_sxm_80gb-x73-hybrid` | 404.0 | 978.5-978.5 | 2.06 | yes | 10.335x | 0.791x | 0.077x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,951.3 | 991.7-991.7 | 19.92 | **no** | `a100_sxm_80gb-x112-hybrid` | 413.4 | 991.1-991.1 | 2.09 | yes | 9.559x | 1.001x | 0.105x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 4,175.0 | 774.3-774.3 | 26.96 | **no** | `a100_sxm_80gb-x73-hybrid` | 404.0 | 978.5-978.5 | 2.06 | yes | 10.335x | 0.791x | 0.077x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,951.3 | 991.7-991.7 | 19.92 | **no** | `a100_sxm_80gb-x112-hybrid` | 413.4 | 991.1-991.1 | 2.09 | yes | 9.559x | 1.001x | 0.105x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 4,175.0 | 774.3-774.3 | 26.96 | **no** | `a100_sxm_80gb-x73-hybrid` | 404.0 | 978.5-978.5 | 2.06 | yes | 10.335x | 0.791x | 0.077x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,951.3 | 991.7-991.7 | 19.92 | **no** | `a100_sxm_80gb-x112-hybrid` | 413.4 | 991.1-991.1 | 2.09 | yes | 9.559x | 1.001x | 0.105x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 4,175.0 | 774.3-774.3 | 26.96 | **no** | `a100_sxm_80gb-x73-hybrid` | 374.0 | 808.0-808.0 | 2.31 | yes | 11.163x | 0.958x | 0.086x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 3,948.7 | 1,634.5-1,634.5 | 12.08 | **no** | `a100_sxm_80gb-x168-hybrid` | 409.4 | 935.7-935.7 | 2.19 | yes | 9.645x | 1.747x | 0.181x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 4,116.2 | 840.7-840.7 | 24.48 | **no** | `a100_sxm_80gb-x146-hybrid` | 371.6 | 746.3-746.3 | 2.49 | yes | 11.078x | 1.127x | 0.102x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,936.2 | 1,674.8-1,674.8 | 11.75 | **no** | `a100_sxm_80gb-x448-hybrid` | 397.4 | 725.6-725.6 | 2.74 | yes | 9.904x | 2.308x | 0.233x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,098.7 | 840.1-840.1 | 24.40 | **no** | `a100_sxm_80gb-x335-hybrid` | 370.5 | 662.5-662.5 | 2.80 | yes | 11.063x | 1.268x | 0.115x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,934.1 | 1,666.3-1,666.3 | 11.80 | **no** | `a100_sxm_80gb-x672-hybrid` | 397.4 | 641.1-641.1 | 3.10 | yes | 9.899x | 2.599x | 0.263x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,917.5 | 415.1-415.1 | 35.14 | **no** | `a100_sxm_80gb-x335-hybrid` | 235.3 | 321.1-321.1 | 3.66 | yes | 12.401x | 1.293x | 0.104x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,261.4 | 860.9-860.9 | 18.94 | **no** | `a100_sxm_80gb-x672-hybrid` | 309.6 | 404.3-404.3 | 3.83 | yes | 10.534x | 2.129x | 0.202x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,290.7 | 190.5-190.5 | 33.88 | **no** | `a100_sxm_80gb-x335-hybrid` | 112.0 | 163.1-163.1 | 3.43 | yes | 11.526x | 1.168x | 0.101x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,776.8 | 225.5-225.5 | 39.40 | **no** | `a100_sxm_80gb-x672-hybrid` | 168.7 | 197.1-197.1 | 4.28 | yes | 10.535x | 1.144x | 0.109x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 378.6 | 121.4-121.4 | 15.60 | **no** | `a100_sxm_80gb-x335-hybrid` | 46.8 | 72.9-72.9 | 3.21 | yes | 8.086x | 1.665x | 0.206x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 567.0 | 172.6-172.6 | 16.42 | **no** | `a100_sxm_80gb-x672-hybrid` | 71.5 | 101.9-101.9 | 3.51 | yes | 7.925x | 1.693x | 0.214x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.077x to 0.263x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 4,192.4 | 857.5-857.5 | 24.44 | **no** | `a100_sxm_80gb-x67-hybrid` | 409.5 | 1,015.4-1,015.4 | 2.02 | yes | 10.239x | 0.845x | 0.082x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,182.6 | 1,628.6-1,628.6 | 12.84 | **no** | `a100_sxm_80gb-x112-hybrid` | 415.8 | 1,011.5-1,011.5 | 2.06 | yes | 10.059x | 1.610x | 0.160x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 4,192.4 | 857.5-857.5 | 24.44 | **no** | `a100_sxm_80gb-x67-hybrid` | 409.5 | 1,015.4-1,015.4 | 2.02 | yes | 10.239x | 0.845x | 0.082x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,182.6 | 1,628.6-1,628.6 | 12.84 | **no** | `a100_sxm_80gb-x112-hybrid` | 415.8 | 1,011.5-1,011.5 | 2.06 | yes | 10.059x | 1.610x | 0.160x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 4,192.4 | 857.5-857.5 | 24.44 | **no** | `a100_sxm_80gb-x67-hybrid` | 409.5 | 1,015.4-1,015.4 | 2.02 | yes | 10.239x | 0.845x | 0.082x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,182.6 | 1,628.6-1,628.6 | 12.84 | **no** | `a100_sxm_80gb-x112-hybrid` | 415.8 | 1,011.5-1,011.5 | 2.06 | yes | 10.059x | 1.610x | 0.160x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 4,192.4 | 857.5-857.5 | 24.44 | **no** | `a100_sxm_80gb-x67-hybrid` | 409.5 | 1,015.4-1,015.4 | 2.02 | yes | 10.239x | 0.845x | 0.082x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,182.6 | 1,628.6-1,628.6 | 12.84 | **no** | `a100_sxm_80gb-x112-hybrid` | 415.8 | 1,011.5-1,011.5 | 2.06 | yes | 10.059x | 1.610x | 0.160x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 4,192.4 | 857.5-857.5 | 24.44 | **no** | `a100_sxm_80gb-x67-hybrid` | 372.7 | 808.5-808.5 | 2.31 | yes | 11.248x | 1.061x | 0.094x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 4,177.5 | 1,660.8-1,660.8 | 12.58 | **no** | `a100_sxm_80gb-x168-hybrid` | 411.8 | 953.8-953.8 | 2.16 | yes | 10.144x | 1.741x | 0.172x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 4,141.3 | 845.7-845.7 | 24.48 | **no** | `a100_sxm_80gb-x146-hybrid` | 374.9 | 765.8-765.8 | 2.45 | yes | 11.046x | 1.104x | 0.100x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4,156.0 | 1,702.1-1,702.1 | 12.21 | **no** | `a100_sxm_80gb-x448-hybrid` | 399.7 | 736.4-736.4 | 2.71 | yes | 10.398x | 2.311x | 0.222x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,123.6 | 845.1-845.1 | 24.40 | **no** | `a100_sxm_80gb-x335-hybrid` | 373.5 | 676.3-676.3 | 2.76 | yes | 11.041x | 1.249x | 0.113x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,155.1 | 1,693.4-1,693.4 | 12.27 | **no** | `a100_sxm_80gb-x672-hybrid` | 399.7 | 649.5-649.5 | 3.08 | yes | 10.396x | 2.607x | 0.251x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,039.8 | 418.8-418.8 | 36.30 | **no** | `a100_sxm_80gb-x335-hybrid` | 240.2 | 334.3-334.3 | 3.59 | yes | 12.657x | 1.252x | 0.099x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,706.8 | 873.4-873.4 | 21.22 | **no** | `a100_sxm_80gb-x672-hybrid` | 313.8 | 414.7-414.7 | 3.78 | yes | 11.812x | 2.106x | 0.178x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,385.4 | 193.6-193.6 | 35.78 | **no** | `a100_sxm_80gb-x335-hybrid` | 112.9 | 170.4-170.4 | 3.31 | yes | 12.277x | 1.136x | 0.093x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,386.5 | 227.5-227.5 | 52.44 | **no** | `a100_sxm_80gb-x672-hybrid` | 169.6 | 202.6-202.6 | 4.19 | yes | 14.068x | 1.123x | 0.080x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 412.1 | 126.7-126.7 | 16.27 | **no** | `a100_sxm_80gb-x335-hybrid` | 47.4 | 79.6-79.6 | 2.98 | yes | 8.687x | 1.590x | 0.183x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 845.0 | 177.9-177.9 | 23.75 | **no** | `a100_sxm_80gb-x672-hybrid` | 72.3 | 107.6-107.6 | 3.36 | yes | 11.695x | 1.653x | 0.141x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.080x to 0.251x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 295.2-295.2 | 31.31 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 294.2-294.2 | 3.21 | yes | 9.799x | 1.003x | 0.102x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 2,091.7 | 652.0-652.0 | 16.04 | **no** | `a100_sxm_80gb-x336-hybrid` | 190.0 | 309.0-309.0 | 3.07 | yes | 11.011x | 2.110x | 0.192x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 295.2-295.2 | 31.31 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 294.2-294.2 | 3.21 | yes | 9.799x | 1.003x | 0.102x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,891.3 | 591.6-591.6 | 15.98 | **no** | `a100_sxm_80gb-x783-hybrid` | 186.9 | 234.5-234.5 | 3.99 | yes | 10.117x | 2.523x | 0.249x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 295.2-295.2 | 31.31 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 294.2-294.2 | 3.21 | yes | 9.799x | 1.003x | 0.102x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,891.3 | 591.6-591.6 | 15.98 | **no** | `a100_sxm_80gb-x783-hybrid` | 186.9 | 234.5-234.5 | 3.99 | yes | 10.117x | 2.523x | 0.249x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 295.2-295.2 | 31.31 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 294.2-294.2 | 3.21 | yes | 9.799x | 1.003x | 0.102x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,891.3 | 591.6-591.6 | 15.98 | **no** | `a100_sxm_80gb-x783-hybrid` | 186.9 | 234.5-234.5 | 3.99 | yes | 10.117x | 2.523x | 0.249x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 295.2-295.2 | 31.31 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 294.2-294.2 | 3.21 | yes | 9.799x | 1.003x | 0.102x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,891.3 | 591.6-591.6 | 15.98 | **no** | `a100_sxm_80gb-x783-hybrid` | 186.9 | 234.5-234.5 | 3.99 | yes | 10.117x | 2.523x | 0.249x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 295.2-295.2 | 31.31 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 294.2-294.2 | 3.21 | yes | 9.799x | 1.003x | 0.102x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,847.6 | 309.7-309.7 | 29.83 | **no** | `a100_sxm_80gb-x783-hybrid` | 186.9 | 234.5-234.5 | 3.99 | yes | 9.884x | 1.321x | 0.134x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,737.9 | 153.8-153.8 | 56.48 | **no** | `a100_sxm_80gb-x391-hybrid` | 176.0 | 259.8-259.8 | 3.39 | yes | 9.874x | 0.592x | 0.060x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,715.0 | 307.1-307.1 | 27.92 | **no** | `a100_sxm_80gb-x783-hybrid` | 186.9 | 234.5-234.5 | 3.99 | yes | 9.174x | 1.310x | 0.143x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,116.4 | 76.3-76.3 | 73.12 | **no** | `a100_sxm_80gb-x391-hybrid` | 95.6 | 115.5-115.5 | 4.14 | yes | 11.672x | 0.661x | 0.057x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,024.8 | 79.7-79.7 | 64.25 | **no** | `a100_sxm_80gb-x783-hybrid` | 135.4 | 147.6-147.6 | 4.59 | yes | 7.568x | 0.540x | 0.071x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 403.9 | 36.0-36.0 | 56.17 | **no** | `a100_sxm_80gb-x391-hybrid` | 37.1 | 50.9-50.9 | 3.64 | yes | 10.890x | 0.706x | 0.065x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 364.5 | 20.1-20.1 | 90.78 | **no** | `a100_sxm_80gb-x783-hybrid` | 59.6 | 65.0-65.0 | 4.59 | yes | 6.114x | 0.309x | 0.051x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 110.7 | 26.1-26.1 | 21.20 | **no** | `a100_sxm_80gb-x391-hybrid` | 13.2 | 21.8-21.8 | 3.03 | yes | 8.361x | 1.195x | 0.143x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 99.0 | 18.9-18.9 | 26.19 | **no** | `a100_sxm_80gb-x783-hybrid` | 22.1 | 30.5-30.5 | 3.62 | yes | 4.474x | 0.619x | 0.138x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.051x to 0.249x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,987.3 | 569.1-569.1 | 17.46 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 312.7-312.7 | 3.05 | yes | 10.414x | 1.820x | 0.175x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,220.4 | 660.7-660.7 | 16.80 | **no** | `a100_sxm_80gb-x448-hybrid` | 190.0 | 298.7-298.7 | 3.18 | yes | 11.687x | 2.212x | 0.189x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,987.3 | 569.1-569.1 | 17.46 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 312.7-312.7 | 3.05 | yes | 10.414x | 1.820x | 0.175x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,220.4 | 660.7-660.7 | 16.80 | **no** | `a100_sxm_80gb-x448-hybrid` | 190.0 | 298.7-298.7 | 3.18 | yes | 11.687x | 2.212x | 0.189x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,987.3 | 569.1-569.1 | 17.46 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 312.7-312.7 | 3.05 | yes | 10.414x | 1.820x | 0.175x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,220.4 | 660.7-660.7 | 16.80 | **no** | `a100_sxm_80gb-x448-hybrid` | 190.0 | 298.7-298.7 | 3.18 | yes | 11.687x | 2.212x | 0.189x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,987.3 | 569.1-569.1 | 17.46 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 312.7-312.7 | 3.05 | yes | 10.414x | 1.820x | 0.175x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,220.4 | 660.7-660.7 | 16.80 | **no** | `a100_sxm_80gb-x448-hybrid` | 190.0 | 298.7-298.7 | 3.18 | yes | 11.687x | 2.212x | 0.189x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,987.3 | 569.1-569.1 | 17.46 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 312.7-312.7 | 3.05 | yes | 10.414x | 1.820x | 0.175x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,220.4 | 660.7-660.7 | 16.80 | **no** | `a100_sxm_80gb-x448-hybrid` | 190.0 | 298.7-298.7 | 3.18 | yes | 11.687x | 2.212x | 0.189x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 1,974.4 | 317.6-317.6 | 31.08 | **no** | `a100_sxm_80gb-x368-hybrid` | 191.6 | 319.8-319.8 | 2.99 | yes | 10.306x | 0.993x | 0.096x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,213.2 | 667.5-667.5 | 16.58 | **no** | `a100_sxm_80gb-x672-hybrid` | 189.2 | 260.8-260.8 | 3.63 | yes | 11.696x | 2.559x | 0.219x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,859.7 | 155.7-155.7 | 59.73 | **no** | `a100_sxm_80gb-x391-hybrid` | 178.9 | 279.4-279.4 | 3.20 | yes | 10.394x | 0.557x | 0.054x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,093.1 | 346.1-346.1 | 30.23 | **no** | `a100_sxm_80gb-x672-hybrid` | 189.2 | 260.8-260.8 | 3.63 | yes | 11.062x | 1.327x | 0.120x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,297.8 | 77.5-77.5 | 83.71 | **no** | `a100_sxm_80gb-x391-hybrid` | 100.6 | 132.5-132.5 | 3.80 | yes | 12.902x | 0.585x | 0.045x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,632.0 | 173.2-173.2 | 47.10 | **no** | `a100_sxm_80gb-x672-hybrid` | 130.8 | 155.5-155.5 | 4.21 | yes | 12.476x | 1.114x | 0.089x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 505.5 | 37.0-37.0 | 68.29 | **no** | `a100_sxm_80gb-x391-hybrid` | 38.4 | 52.0-52.0 | 3.69 | yes | 13.180x | 0.711x | 0.054x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 893.2 | 86.5-86.5 | 51.62 | **no** | `a100_sxm_80gb-x672-hybrid` | 56.1 | 68.8-68.8 | 4.08 | yes | 15.911x | 1.258x | 0.079x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 142.2 | 28.5-28.5 | 24.96 | **no** | `a100_sxm_80gb-x391-hybrid` | 14.5 | 18.6-18.6 | 3.89 | yes | 9.822x | 1.531x | 0.156x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 333.4 | 40.2-40.2 | 41.45 | **no** | `a100_sxm_80gb-x672-hybrid` | 20.3 | 33.0-33.0 | 3.07 | yes | 16.456x | 1.217x | 0.074x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.045x to 0.219x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 324.8-324.8 | 31.92 | **no** | `a100_sxm_80gb-x361-hybrid` | 189.8 | 317.1-317.1 | 2.99 | yes | 10.928x | 1.024x | 0.094x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,266.7 | 665.1-665.1 | 17.04 | **no** | `a100_sxm_80gb-x336-hybrid` | 192.4 | 329.4-329.4 | 2.92 | yes | 11.784x | 2.019x | 0.171x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 324.8-324.8 | 31.92 | **no** | `a100_sxm_80gb-x361-hybrid` | 189.8 | 317.1-317.1 | 2.99 | yes | 10.928x | 1.024x | 0.094x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,266.7 | 665.1-665.1 | 17.04 | **no** | `a100_sxm_80gb-x336-hybrid` | 192.4 | 329.4-329.4 | 2.92 | yes | 11.784x | 2.019x | 0.171x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 324.8-324.8 | 31.92 | **no** | `a100_sxm_80gb-x361-hybrid` | 189.8 | 317.1-317.1 | 2.99 | yes | 10.928x | 1.024x | 0.094x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,266.7 | 665.1-665.1 | 17.04 | **no** | `a100_sxm_80gb-x336-hybrid` | 192.4 | 329.4-329.4 | 2.92 | yes | 11.784x | 2.019x | 0.171x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 324.8-324.8 | 31.92 | **no** | `a100_sxm_80gb-x361-hybrid` | 189.8 | 317.1-317.1 | 2.99 | yes | 10.928x | 1.024x | 0.094x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,266.7 | 665.1-665.1 | 17.04 | **no** | `a100_sxm_80gb-x336-hybrid` | 192.4 | 329.4-329.4 | 2.92 | yes | 11.784x | 2.019x | 0.171x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 324.8-324.8 | 31.92 | **no** | `a100_sxm_80gb-x361-hybrid` | 189.8 | 317.1-317.1 | 2.99 | yes | 10.928x | 1.024x | 0.094x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,266.7 | 665.1-665.1 | 17.04 | **no** | `a100_sxm_80gb-x336-hybrid` | 192.4 | 329.4-329.4 | 2.92 | yes | 11.784x | 2.019x | 0.171x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 324.8-324.8 | 31.92 | **no** | `a100_sxm_80gb-x361-hybrid` | 189.8 | 317.1-317.1 | 2.99 | yes | 10.928x | 1.024x | 0.094x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,257.9 | 670.9-670.9 | 16.83 | **no** | `a100_sxm_80gb-x672-hybrid` | 189.4 | 260.9-260.9 | 3.63 | yes | 11.924x | 2.572x | 0.216x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,948.6 | 297.1-297.1 | 32.80 | **no** | `a100_sxm_80gb-x391-hybrid` | 179.1 | 279.4-279.4 | 3.20 | yes | 10.880x | 1.063x | 0.098x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,220.5 | 347.6-347.6 | 31.94 | **no** | `a100_sxm_80gb-x672-hybrid` | 189.4 | 260.9-260.9 | 3.63 | yes | 11.726x | 1.333x | 0.114x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,330.3 | 77.7-77.7 | 85.62 | **no** | `a100_sxm_80gb-x391-hybrid` | 100.8 | 134.2-134.2 | 3.76 | yes | 13.197x | 0.579x | 0.044x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,714.1 | 173.9-173.9 | 49.27 | **no** | `a100_sxm_80gb-x672-hybrid` | 131.0 | 156.3-156.3 | 4.19 | yes | 13.083x | 1.113x | 0.085x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 525.1 | 37.2-37.2 | 70.62 | **no** | `a100_sxm_80gb-x391-hybrid` | 38.5 | 54.1-54.1 | 3.56 | yes | 13.646x | 0.687x | 0.050x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 950.4 | 156.2-156.2 | 30.42 | **no** | `a100_sxm_80gb-x672-hybrid` | 56.3 | 70.5-70.5 | 3.99 | yes | 16.882x | 2.216x | 0.131x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 148.5 | 28.9-28.9 | 25.71 | **no** | `a100_sxm_80gb-x391-hybrid` | 14.5 | 19.8-19.8 | 3.67 | yes | 10.208x | 1.457x | 0.143x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 365.5 | 69.6-69.6 | 26.25 | **no** | `a100_sxm_80gb-x672-hybrid` | 20.3 | 33.2-33.2 | 3.07 | yes | 17.970x | 2.100x | 0.117x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.044x to 0.216x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 10,692.4 | not applicable | -- | -- | `b200_sxm-x8-tensor` | 1,501.9 | not applicable | -- | -- | 7.119x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 9,245.0 | not applicable | -- | -- | `b200_sxm-x29-nvl72-tensor` | 2,284.3 | not applicable | -- | -- | 4.047x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 9,796.1 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 2,283.2 | not applicable | -- | -- | 4.291x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 7,483.5 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,493.8 | not applicable | -- | -- | 3.001x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 9,796.1 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 2,199.2 | not applicable | -- | -- | 4.454x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 7,483.5 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,481.1 | not applicable | -- | -- | 3.016x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 9,712.9 | not applicable | -- | -- | `b200_sxm-x87-nvl72-hybrid` | 2,303.4 | not applicable | -- | -- | 4.217x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 7,471.7 | not applicable | -- | -- | `b200_sxm-x231-nvl72-hybrid` | 2,442.5 | not applicable | -- | -- | 3.059x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9,591.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,338.6 | not applicable | -- | -- | 4.101x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6,532.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 2,432.9 | not applicable | -- | -- | 2.685x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8,722.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,172.2 | not applicable | -- | -- | 4.016x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,236.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 2,325.6 | not applicable | -- | -- | 2.251x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7,119.0 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,901.6 | not applicable | -- | -- | 3.744x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,678.1 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 2,137.1 | not applicable | -- | -- | 1.721x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,148.4 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,192.8 | not applicable | -- | -- | 2.639x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,238.5 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,521.5 | not applicable | -- | -- | 0.814x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 801.0 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 531.3 | not applicable | -- | -- | 1.507x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 331.2 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 808.3 | not applicable | -- | -- | 0.410x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 201.1 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 178.3 | not applicable | -- | -- | 1.128x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 84.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 314.7 | not applicable | -- | -- | 0.267x | -- | -- |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 4,202.4 | 1,013.6-1,013.6 | 20.73 | **no** | `b200_sxm-x29-nvl72-tensor` | 846.3 | 2,764.8-2,764.8 | 1.53 | yes | 4.966x | 0.367x | 0.074x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3,943.5 | 990.6-990.6 | 19.90 | **no** | `b200_sxm-x58-nvl72-tensor` | 862.2 | 2,836.5-2,836.5 | 1.52 | yes | 4.574x | 0.349x | 0.076x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 4,142.4 | 952.1-952.1 | 21.75 | **no** | `b200_sxm-x31-hybrid` | 818.6 | 2,369.4-2,369.4 | 1.73 | yes | 5.061x | 0.402x | 0.079x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,601.2 | 3,594.6-3,594.6 | 5.01 | **no** | `b200_sxm-x202-nvl72-hybrid` | 858.2 | 2,781.5-2,781.5 | 1.54 | yes | 4.196x | 1.292x | 0.308x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 4,142.4 | 952.1-952.1 | 21.75 | **no** | `b200_sxm-x31-hybrid` | 818.6 | 2,369.4-2,369.4 | 1.73 | yes | 5.061x | 0.402x | 0.079x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,601.2 | 3,594.6-3,594.6 | 5.01 | **no** | `b200_sxm-x202-nvl72-hybrid` | 851.5 | 2,736.6-2,736.6 | 1.56 | yes | 4.229x | 1.314x | 0.311x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 4,142.4 | 952.1-952.1 | 21.75 | **no** | `b200_sxm-x31-hybrid` | 747.5 | 1,776.5-1,776.5 | 2.10 | yes | 5.542x | 0.536x | 0.097x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,601.2 | 3,594.6-3,594.6 | 5.01 | **no** | `b200_sxm-x202-nvl72-hybrid` | 828.3 | 2,536.7-2,536.7 | 1.63 | yes | 4.348x | 1.417x | 0.326x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x61` | 4,118.7 | 897.9-897.9 | 22.94 | **no** | `b200_sxm-x31-hybrid` | 638.5 | 1,206.9-1,206.9 | 2.65 | yes | 6.451x | 0.744x | 0.115x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,601.2 | 3,594.6-3,594.6 | 5.01 | **no** | `b200_sxm-x202-nvl72-hybrid` | 802.0 | 2,185.3-2,185.3 | 1.83 | yes | 4.490x | 1.645x | 0.366x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 3,916.7 | 1,097.0-1,097.0 | 17.85 | **no** | `b200_sxm-x86-nvl72-hybrid` | 692.8 | 1,468.8-1,468.8 | 2.36 | yes | 5.653x | 0.747x | 0.132x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,571.7 | 3,577.0-3,577.0 | 4.99 | yes | `b200_sxm-x347-nvl72-hybrid` | 788.7 | 2,007.4-2,007.4 | 1.96 | yes | 4.529x | 1.782x | 0.393x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,914.0 | 1,096.8-1,096.8 | 17.84 | **no** | `b200_sxm-x173-nvl72-hybrid` | 685.6 | 1,408.2-1,408.2 | 2.43 | yes | 5.709x | 0.779x | 0.136x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,458.0 | 2,112.7-2,112.7 | 8.18 | **no** | `b200_sxm-x347-nvl72-hybrid` | 756.8 | 1,762.9-1,762.9 | 2.15 | yes | 4.569x | 1.198x | 0.262x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,667.9 | 536.2-536.2 | 24.88 | **no** | `b200_sxm-x173-nvl72-hybrid` | 443.8 | 757.5-757.5 | 2.93 | yes | 6.012x | 0.708x | 0.118x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,439.2 | 1,089.5-1,089.5 | 11.19 | **no** | `b200_sxm-x347-nvl72-hybrid` | 564.1 | 982.2-982.2 | 2.87 | yes | 4.324x | 1.109x | 0.257x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,133.1 | 235.9-235.9 | 24.02 | **no** | `b200_sxm-x173-nvl72-hybrid` | 217.7 | 381.9-381.9 | 2.85 | yes | 5.204x | 0.618x | 0.119x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,035.3 | 293.0-293.0 | 17.67 | **no** | `b200_sxm-x347-nvl72-hybrid` | 320.0 | 497.5-497.5 | 3.22 | yes | 3.235x | 0.589x | 0.182x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 344.6 | 118.7-118.7 | 14.52 | **no** | `b200_sxm-x173-nvl72-hybrid` | 91.1 | 186.0-186.0 | 2.45 | yes | 3.784x | 0.638x | 0.169x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 298.0 | 84.2-84.2 | 17.70 | **no** | `b200_sxm-x347-nvl72-hybrid` | 140.2 | 255.5-255.5 | 2.74 | yes | 2.125x | 0.329x | 0.155x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340` | 1,581.9 | 321.0-321.0 | 24.64 | **no** | `b200_sxm-x173-nvl72-hybrid` | 509.0 | 1,044.2-1,044.2 | 2.44 | yes | 3.108x | 0.307x | 0.099x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 2,052.1 | 644.6-644.6 | 15.92 | **no** | `b200_sxm-x173-nvl72-hybrid` | 509.0 | 1,044.2-1,044.2 | 2.44 | yes | 4.032x | 0.617x | 0.153x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,575.6 | 282.2-282.2 | 27.92 | **no** | `b200_sxm-x203-nvl72-hybrid` | 511.9 | 1,047.1-1,047.1 | 2.44 | yes | 3.078x | 0.269x | 0.088x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,678.4 | 327.7-327.7 | 25.61 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 947.8-947.8 | 2.64 | yes | 3.357x | 0.346x | 0.103x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,575.6 | 282.2-282.2 | 27.92 | **no** | `b200_sxm-x203-nvl72-hybrid` | 504.9 | 1,029.9-1,029.9 | 2.45 | yes | 3.121x | 0.274x | 0.088x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,678.4 | 327.7-327.7 | 25.61 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 947.8-947.8 | 2.64 | yes | 3.357x | 0.346x | 0.103x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,575.6 | 282.2-282.2 | 27.92 | **no** | `b200_sxm-x203-nvl72-hybrid` | 486.0 | 942.8-942.8 | 2.58 | yes | 3.242x | 0.299x | 0.092x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,678.4 | 327.7-327.7 | 25.61 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 947.8-947.8 | 2.64 | yes | 3.357x | 0.346x | 0.103x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,575.6 | 282.2-282.2 | 27.92 | **no** | `b200_sxm-x203-nvl72-hybrid` | 463.0 | 828.2-828.2 | 2.80 | yes | 3.403x | 0.341x | 0.100x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,678.4 | 327.7-327.7 | 25.61 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 947.8-947.8 | 2.64 | yes | 3.357x | 0.346x | 0.103x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,575.6 | 282.2-282.2 | 27.92 | **no** | `b200_sxm-x203-nvl72-hybrid` | 395.7 | 700.5-700.5 | 2.82 | yes | 3.982x | 0.403x | 0.101x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,678.4 | 327.7-327.7 | 25.61 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 472.8 | 840.6-840.6 | 2.81 | yes | 3.550x | 0.390x | 0.110x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,568.9 | 150.2-150.2 | 52.21 | **no** | `b200_sxm-x203-nvl72-hybrid` | 312.7 | 442.9-442.9 | 3.53 | yes | 5.017x | 0.339x | 0.068x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,654.7 | 1,447.9-1,447.9 | 5.71 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 468.8 | 720.4-720.4 | 3.25 | yes | 3.530x | 2.010x | 0.569x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 958.0 | 74.3-74.3 | 64.44 | **no** | `b200_sxm-x203-nvl72-hybrid` | 165.5 | 218.5-218.5 | 3.79 | yes | 5.787x | 0.340x | 0.059x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,301.3 | 95.6-95.6 | 68.07 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 368.5 | 426.5-426.5 | 4.32 | yes | 3.531x | 0.224x | 0.063x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 339.6 | 34.8-34.8 | 48.83 | **no** | `b200_sxm-x203-nvl72-hybrid` | 67.5 | 90.2-90.2 | 3.74 | yes | 5.035x | 0.386x | 0.077x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 568.5 | 24.2-24.2 | 117.48 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 218.5 | 206.9-206.9 | 5.28 | **no** | 2.602x | 0.117x | 0.045x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 92.0 | 24.1-24.1 | 19.07 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 168.7 | 6.1-6.1 | 139.08 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 97.4 | 96.4-96.4 | 5.05 | **no** | 1.731x | 0.063x | 0.036x |

**Does the ratio compress?** Of 39 class rows in this study, 39 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.036x to 0.569x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 1 of 40 ROM rows and 37 of 40 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 10,396.4 | not applicable | -- | -- | `a100_sxm_80gb-x16-hybrid` | 559.8 | not applicable | -- | -- | 18.572x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 9,289.5 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 682.2 | not applicable | -- | -- | 13.617x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8,012.3 | not applicable | -- | -- | `a100_sxm_80gb-x272-tensor` | 692.4 | not applicable | -- | -- | 11.572x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,951.9 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 684.2 | not applicable | -- | -- | 8.699x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8,012.3 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 673.8 | not applicable | -- | -- | 11.892x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,537.5 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 684.2 | not applicable | -- | -- | 8.094x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8,012.3 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 644.8 | not applicable | -- | -- | 12.426x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,459.7 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 676.9 | not applicable | -- | -- | 8.065x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 7,650.1 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 583.5 | not applicable | -- | -- | 13.112x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,524.5 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 654.0 | not applicable | -- | -- | 6.918x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,230.8 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 542.6 | not applicable | -- | -- | 11.484x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,092.1 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 591.2 | not applicable | -- | -- | 5.230x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,555.8 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 518.7 | not applicable | -- | -- | 8.783x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,856.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 535.7 | not applicable | -- | -- | 3.465x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,594.7 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 411.4 | not applicable | -- | -- | 3.877x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 531.7 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 478.2 | not applicable | -- | -- | 1.112x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 431.0 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 225.0 | not applicable | -- | -- | 1.915x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 136.7 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 323.1 | not applicable | -- | -- | 0.423x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 111.0 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 80.4 | not applicable | -- | -- | 1.381x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 34.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 140.6 | not applicable | -- | -- | 0.244x | -- | -- |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | 3,949.8 | 725.8-725.8 | 27.21 | **no** | `a100_sxm_80gb-x79-hybrid` | 398.0 | 890.4-890.4 | 2.24 | yes | 9.923x | 0.815x | 0.082x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 3,943.5 | 982.7-982.7 | 20.06 | **no** | `a100_sxm_80gb-x112-hybrid` | 397.4 | 871.9-871.9 | 2.28 | yes | 9.923x | 1.127x | 0.114x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,844.6 | 663.0-663.0 | 28.99 | **no** | `a100_sxm_80gb-x85-hybrid` | 394.9 | 876.9-876.9 | 2.25 | yes | 9.737x | 0.756x | 0.078x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,238.6 | 836.6-836.6 | 19.36 | **no** | `a100_sxm_80gb-x560-hybrid` | 382.7 | 621.4-621.4 | 3.08 | yes | 8.463x | 1.346x | 0.159x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,844.6 | 663.0-663.0 | 28.99 | **no** | `a100_sxm_80gb-x85-hybrid` | 394.9 | 876.9-876.9 | 2.25 | yes | 9.737x | 0.756x | 0.078x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,238.6 | 836.6-836.6 | 19.36 | **no** | `a100_sxm_80gb-x560-hybrid` | 382.7 | 621.4-621.4 | 3.08 | yes | 8.463x | 1.346x | 0.159x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,844.6 | 663.0-663.0 | 28.99 | **no** | `a100_sxm_80gb-x85-hybrid` | 394.9 | 876.9-876.9 | 2.25 | yes | 9.737x | 0.756x | 0.078x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,238.6 | 836.6-836.6 | 19.36 | **no** | `a100_sxm_80gb-x560-hybrid` | 382.7 | 621.4-621.4 | 3.08 | yes | 8.463x | 1.346x | 0.159x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,844.6 | 663.0-663.0 | 28.99 | **no** | `a100_sxm_80gb-x85-hybrid` | 367.4 | 730.5-730.5 | 2.51 | yes | 10.464x | 0.908x | 0.087x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,238.6 | 836.6-836.6 | 19.36 | **no** | `a100_sxm_80gb-x560-hybrid` | 382.7 | 621.4-621.4 | 3.08 | yes | 8.463x | 1.346x | 0.159x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 3,628.0 | 807.5-807.5 | 22.47 | **no** | `a100_sxm_80gb-x312-hybrid` | 384.6 | 722.3-722.3 | 2.66 | yes | 9.432x | 1.118x | 0.119x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,106.7 | 435.3-435.3 | 35.69 | **no** | `a100_sxm_80gb-x560-hybrid` | 382.7 | 621.4-621.4 | 3.08 | yes | 8.118x | 0.700x | 0.086x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 3,628.0 | 807.5-807.5 | 22.47 | **no** | `a100_sxm_80gb-x312-hybrid` | 346.7 | 571.7-571.7 | 3.03 | yes | 10.465x | 1.412x | 0.135x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,774.5 | 364.1-364.1 | 38.10 | **no** | `a100_sxm_80gb-x672-hybrid` | 382.7 | 589.1-589.1 | 3.25 | yes | 7.250x | 0.618x | 0.085x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,291.5 | 391.8-391.8 | 29.24 | **no** | `a100_sxm_80gb-x335-hybrid` | 215.7 | 291.1-291.1 | 3.70 | yes | 10.625x | 1.346x | 0.127x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,464.3 | 182.7-182.7 | 40.08 | **no** | `a100_sxm_80gb-x672-hybrid` | 283.6 | 345.6-345.6 | 4.10 | yes | 5.163x | 0.528x | 0.102x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 883.5 | 171.9-171.9 | 25.69 | **no** | `a100_sxm_80gb-x335-hybrid` | 99.1 | 131.6-131.6 | 3.76 | yes | 8.915x | 1.306x | 0.147x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 480.3 | 46.8-46.8 | 51.30 | **no** | `a100_sxm_80gb-x672-hybrid` | 153.9 | 172.4-172.4 | 4.46 | yes | 3.121x | 0.272x | 0.087x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 313.9 | 106.0-106.0 | 14.81 | **no** | `a100_sxm_80gb-x335-hybrid` | 38.2 | 69.7-69.7 | 2.74 | yes | 8.211x | 1.521x | 0.185x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 128.2 | 23.0-23.0 | 27.84 | **no** | `a100_sxm_80gb-x672-hybrid` | 61.8 | 83.4-83.4 | 3.70 | yes | 2.075x | 0.276x | 0.133x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 1,467.1 | 488.0-488.0 | 15.03 | **no** | `a100_sxm_80gb-x384-hybrid` | 166.7 | 228.6-228.6 | 3.64 | yes | 8.802x | 2.135x | 0.243x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 1,978.5 | 456.9-456.9 | 21.65 | **no** | `a100_sxm_80gb-x504-hybrid` | 165.1 | 213.0-213.0 | 3.88 | yes | 11.982x | 2.145x | 0.179x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 236.5-236.5 | 31.62 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 98.4-98.4 | 8.39 | **no** | 9.061x | 2.403x | 0.265x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 236.5-236.5 | 31.62 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 98.4-98.4 | 8.39 | **no** | 9.061x | 2.403x | 0.265x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 236.5-236.5 | 31.62 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 98.4-98.4 | 8.39 | **no** | 9.061x | 2.403x | 0.265x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 236.5-236.5 | 31.62 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 98.4-98.4 | 8.39 | **no** | 9.061x | 2.403x | 0.265x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 236.5-236.5 | 31.62 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 98.4-98.4 | 8.39 | **no** | 9.061x | 2.403x | 0.265x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 236.5-236.5 | 31.62 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 98.4-98.4 | 8.39 | **no** | 9.061x | 2.403x | 0.265x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 989.0 | 68.6-68.6 | 72.08 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 98.4-98.4 | 8.39 | **no** | 5.991x | 0.697x | 0.116x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 361.2 | 17.3-17.3 | 104.66 | **no** | `a100_sxm_80gb-x3694-hybrid` | 118.2 | 64.6-64.6 | 9.14 | **no** | 3.055x | 0.267x | 0.087x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 100.3 | 4.3-4.3 | 116.15 | **no** | `a100_sxm_80gb-x3694-hybrid` | 54.9 | 28.7-28.7 | 9.55 | **no** | 1.828x | 0.150x | 0.082x |

**Does the ratio compress?** Of 31 class rows in this study, 31 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.078x to 0.265x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 31 ROM rows and 22 of 31 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 12,043.2 | not applicable | -- | -- | `b200_sxm-x2-tensor` | 1,328.0 | not applicable | -- | -- | 9.069x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 9,137.9 | not applicable | -- | -- | `b200_sxm-x29-nvl72-tensor` | 2,641.2 | not applicable | -- | -- | 3.460x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 9,519.0 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 2,601.6 | not applicable | -- | -- | 3.659x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 7,387.4 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,693.6 | not applicable | -- | -- | 2.743x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 9,519.0 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 2,493.1 | not applicable | -- | -- | 3.818x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 7,387.4 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,678.9 | not applicable | -- | -- | 2.758x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x170-romfill` | 9,440.2 | not applicable | -- | -- | `b200_sxm-x87-nvl72-hybrid` | 2,533.6 | not applicable | -- | -- | 3.726x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 7,375.9 | not applicable | -- | -- | `b200_sxm-x231-nvl72-hybrid` | 2,633.5 | not applicable | -- | -- | 2.801x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 9,325.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,513.5 | not applicable | -- | -- | 3.710x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 6,402.3 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 2,588.6 | not applicable | -- | -- | 2.473x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 8,516.1 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,328.9 | not applicable | -- | -- | 3.657x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 5,147.2 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 2,467.4 | not applicable | -- | -- | 2.086x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 6,884.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,086.3 | not applicable | -- | -- | 3.300x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,595.4 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 2,271.2 | not applicable | -- | -- | 1.583x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3,271.6 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,340.8 | not applicable | -- | -- | 2.440x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,227.3 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,676.9 | not applicable | -- | -- | 0.732x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 832.2 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 591.8 | not applicable | -- | -- | 1.406x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 331.1 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 913.1 | not applicable | -- | -- | 0.363x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 208.3 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 192.6 | not applicable | -- | -- | 1.081x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 84.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 349.1 | not applicable | -- | -- | 0.241x | -- | -- |

### `n6_vs_a100-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x8-romfill` | 11,594.0 | not applicable | -- | -- | `a100_sxm_80gb-x8-tensor` | 1,063.1 | not applicable | -- | -- | 10.906x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 9,155.9 | not applicable | -- | -- | `a100_sxm_80gb-x56-hybrid` | 1,045.1 | not applicable | -- | -- | 8.761x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,820.6 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 979.9 | not applicable | -- | -- | 7.981x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,928.2 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 975.4 | not applicable | -- | -- | 6.078x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,820.6 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 979.9 | not applicable | -- | -- | 7.981x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,498.6 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 975.4 | not applicable | -- | -- | 5.637x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,820.6 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 979.9 | not applicable | -- | -- | 7.981x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,385.8 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 975.4 | not applicable | -- | -- | 5.522x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,461.6 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 979.9 | not applicable | -- | -- | 7.615x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 4,472.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 975.4 | not applicable | -- | -- | 4.585x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 5,990.2 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 974.3 | not applicable | -- | -- | 6.148x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,047.9 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 975.4 | not applicable | -- | -- | 3.125x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4,417.1 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 922.5 | not applicable | -- | -- | 4.788x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,832.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 975.4 | not applicable | -- | -- | 1.878x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 1,587.4 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 630.0 | not applicable | -- | -- | 2.519x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 529.8 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 800.0 | not applicable | -- | -- | 0.662x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 430.0 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 277.8 | not applicable | -- | -- | 1.548x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 136.7 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 443.7 | not applicable | -- | -- | 0.308x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340` | 111.0 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 93.0 | not applicable | -- | -- | 1.194x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12` | 34.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 167.3 | not applicable | -- | -- | 0.205x | -- | -- |

## Where the drafter lives on a ROM machine

The locality rule -- `stored/peak` is a technology constant -- is the load-bearing assumption of the whole ROM verdict. A pass that reads only the drafter's region uses only that region's read ports and takes exactly as long as sweeping the entire array. Two placements are therefore priced side by side, and the second is an architectural proposal this study **has not costed in silicon area**.

The same rule is what makes a SEQUENTIAL draft step expensive here. A per-position operation that moves only a small table is nearly free on a global-bandwidth store and costs a full array sweep on this one, so a drafter with `gamma` sequential applications pays `gamma` sweeps for them. That term is charged in full below; on a bandwidth store the bytes it moves are not separately charged at all, because this repository's model configs carry no size for the table -- an omission whose size, on DeepSeek-V4-Pro-0813, is the externally published 132,382,720 B per draft token, 0.33% of the 39,666,603,980 B target pass.

| study | model | ctx | batch | class | design | tau* draft in ROM | tau* draft in KV store | KV placement feasible | why not |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 39.26 | 2.68 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.18 | 3.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 39.26 | 2.68 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.18 | 3.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 39.26 | 2.68 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.18 | 3.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 39.26 | 2.68 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.18 | 3.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 39.26 | 2.68 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.18 | 3.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 74.88 | 3.68 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 30.80 | 3.97 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 59.88 | 3.88 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 30.95 | 3.98 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 93.48 | 4.50 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 49.42 | 7.00 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 94.49 | 6.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 99.83 | 13.04 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 67.83 | 8.43 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 40.30 | 6.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 52.75 | 3.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 47.40 | 6.53 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 52.75 | 3.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 47.40 | 6.53 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 52.75 | 3.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 47.40 | 6.53 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 52.75 | 3.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 47.40 | 6.53 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 52.75 | 3.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 47.40 | 6.53 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 52.75 | 3.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 40.04 | 6.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 98.00 | 4.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 40.23 | 6.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 160.87 | 6.70 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 59.97 | 11.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 132.17 | 9.21 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 92.07 | 11.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 42.48 | 9.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 68.71 | 13.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 46.90 | 2.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.55 | 2.75 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 46.90 | 2.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.55 | 2.75 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 46.90 | 2.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.55 | 2.75 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 46.90 | 2.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.55 | 2.75 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 46.90 | 2.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.55 | 2.75 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 52.14 | 2.80 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 15.10 | 2.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 96.01 | 3.75 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 27.50 | 4.15 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 87.47 | 5.57 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 37.55 | 6.36 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 143.71 | 7.74 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 134.63 | 6.13 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 46.97 | 8.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 78.26 | 5.94 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 31.17 | 2.68 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 17.55 | 3.42 | NO | the KV store has no room for it |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 31.17 | 2.68 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 30.43 | 2.60 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 31.17 | 2.68 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 30.43 | 2.60 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 31.17 | 2.68 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 30.43 | 2.60 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 31.17 | 2.68 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 30.43 | 2.60 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 64.31 | 3.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 56.36 | 3.42 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 114.31 | 4.93 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 48.89 | 3.75 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 134.94 | 7.25 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 100.18 | 5.60 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 94.67 | 8.85 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 126.73 | 6.72 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 31.23 | 8.69 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 34.78 | 4.95 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 37.93 | 2.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.93 | 3.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 37.93 | 2.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.93 | 3.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 37.93 | 2.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.93 | 3.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 37.93 | 2.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.93 | 3.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 37.93 | 2.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.93 | 3.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 73.29 | 3.55 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 31.40 | 3.82 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 61.73 | 3.71 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 31.56 | 3.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 84.18 | 5.76 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 52.19 | 6.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 94.91 | 6.65 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 112.14 | 13.79 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 72.16 | 8.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 41.16 | 13.30 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 50.33 | 3.18 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 48.76 | 6.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 50.33 | 3.18 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 48.76 | 6.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 50.33 | 3.18 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 48.76 | 6.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 50.33 | 3.18 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 48.76 | 6.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 50.33 | 3.18 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 48.76 | 6.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342-romfill` | 42.27 | 3.31 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 41.23 | 6.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 91.83 | 4.56 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 41.42 | 6.43 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 88.50 | 6.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 64.21 | 11.67 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 147.75 | 9.36 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 121.39 | 21.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 47.47 | 9.16 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 43.39 | 11.08 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 22.05 | 2.57 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 22.16 | 2.10 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 22.05 | 2.57 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 20.83 | 3.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 22.05 | 2.57 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 20.83 | 3.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 22.05 | 2.57 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 20.83 | 3.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 42.40 | 3.50 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 20.38 | 3.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 39.62 | 3.58 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 19.77 | 3.87 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 39.62 | 3.58 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 19.86 | 3.88 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 54.84 | 5.57 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 33.15 | 6.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 48.23 | 7.93 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 74.99 | 14.10 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 17.08 | 5.98 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 30.20 | 13.73 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 29.37 | 3.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 30.02 | 2.37 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 29.37 | 3.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.38 | 6.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 29.37 | 3.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.38 | 6.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 29.37 | 3.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.38 | 6.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 29.37 | 3.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.38 | 6.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 27.39 | 3.21 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 25.60 | 6.35 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 50.43 | 4.58 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 25.72 | 6.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 64.96 | 7.06 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 40.07 | 11.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 35.96 | 6.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 77.84 | 21.25 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 18.76 | 8.12 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 28.84 | 17.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 24.62 | 2.80 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 21.43 | 2.46 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 24.62 | 2.80 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.47 | 2.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 24.62 | 2.80 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.47 | 2.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 24.62 | 2.80 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.47 | 2.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 20.78 | 2.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.47 | 2.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 20.09 | 2.98 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.83 | 2.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 36.16 | 4.06 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 17.34 | 3.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 45.23 | 6.07 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 23.48 | 5.67 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 32.58 | 5.56 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 36.96 | 8.12 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 16.62 | 7.25 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 40.12 | 4.41 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 32.72 | 3.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | 15.46 | 2.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 32.72 | 3.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 21.33 | 2.57 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 32.72 | 3.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 21.33 | 2.57 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 32.72 | 3.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 21.33 | 2.57 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 32.72 | 3.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 30.43 | 2.53 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 25.98 | 3.57 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 55.36 | 3.23 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 44.90 | 5.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 49.47 | 3.61 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 56.32 | 6.56 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 101.13 | 5.24 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 33.66 | 7.78 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 127.03 | 6.20 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 24.91 | 8.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 34.39 | 4.38 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 41.35 | 3.39 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 21.16 | 3.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 41.35 | 3.39 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 21.16 | 3.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 41.35 | 3.39 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 21.16 | 3.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 41.35 | 3.39 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 21.16 | 3.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 41.35 | 3.39 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 20.70 | 3.79 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 40.49 | 3.42 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 20.05 | 3.71 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 40.49 | 3.42 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 20.16 | 3.73 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 58.15 | 5.39 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 34.94 | 6.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 53.24 | 7.91 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 84.02 | 15.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 21.19 | 8.38 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 34.22 | 14.92 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 28.01 | 3.04 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 27.36 | 6.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 28.01 | 3.04 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 27.36 | 6.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 28.01 | 3.04 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 27.36 | 6.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 28.01 | 3.04 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 27.36 | 6.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 28.01 | 3.04 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 27.36 | 6.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 27.67 | 3.10 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 26.53 | 6.33 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 52.03 | 4.43 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 26.66 | 6.35 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 69.73 | 7.00 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 43.90 | 12.09 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 57.01 | 9.31 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 93.61 | 24.84 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 18.93 | 7.63 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 35.21 | 21.34 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 22.05 | 2.57 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 20.83 | 3.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 22.05 | 2.57 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 20.83 | 3.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 22.05 | 2.57 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 20.83 | 3.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 22.05 | 2.57 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 20.83 | 3.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 42.40 | 3.50 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 20.38 | 3.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 39.62 | 3.58 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 19.77 | 3.87 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 39.62 | 3.58 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 19.86 | 3.88 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 54.84 | 5.57 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 33.15 | 6.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 48.23 | 7.93 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 74.99 | 14.10 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 17.08 | 5.98 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 30.20 | 13.73 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 29.37 | 3.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.38 | 6.51 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 29.37 | 3.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.38 | 6.51 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 29.37 | 3.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.38 | 6.51 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 29.37 | 3.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.38 | 6.51 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 29.37 | 3.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.38 | 6.51 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 27.39 | 3.21 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 25.60 | 6.36 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 50.43 | 4.58 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 25.73 | 6.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 64.96 | 7.06 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 40.07 | 11.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 35.96 | 6.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 77.86 | 21.26 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 18.76 | 8.12 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 28.84 | 17.83 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | 8.24 | 3.32 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 3.34 | 1.83 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 19.66 | 2.06 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 8.23 | 1.53 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 19.66 | 2.06 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 8.23 | 1.53 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 19.66 | 2.06 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 13.22 | 1.50 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x282` | 27.55 | 2.08 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 24.00 | 1.43 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 31.85 | 2.23 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 20.07 | 1.49 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 44.43 | 2.16 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 23.46 | 1.35 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 10.98 | 3.61 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 29.72 | 1.18 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 5.32 | 3.47 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 31.40 | 1.16 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 3.92 | 3.46 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x22` | 16.38 | 1.08 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x64` | 9.71 | 3.42 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 3.53 | 2.04 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 10.12 | 1.80 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 9.10 | 1.48 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 10.12 | 1.80 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 9.10 | 1.48 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x287` | 12.38 | 1.82 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 9.10 | 1.48 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 15.38 | 1.86 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 13.92 | 1.40 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 21.95 | 1.70 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 20.00 | 1.33 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 27.05 | 1.52 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 21.53 | 1.25 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 31.85 | 1.46 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 25.02 | 1.23 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 17.17 | 1.37 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 25.80 | 1.22 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 5.29 | 1.30 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x31` | 13.48 | 1.11 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 8.50 | 3.19 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 9.01 | 2.61 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 22.34 | 1.27 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 22.34 | 1.27 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 22.34 | 1.27 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 22.34 | 1.27 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 21.04 | 1.31 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 28.54 | 1.16 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 35.91 | 1.06 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 38.37 | 1.04 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 38.91 | 1.04 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | 9.86 | 3.49 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 5.54 | 2.48 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 2.02 | 1.51 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 19.46 | 1.15 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 19.46 | 1.15 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 19.46 | 1.15 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 19.46 | 1.15 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 14.13 | 1.18 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 17.28 | 1.05 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 16.13 | 1.03 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 16.26 | 1.03 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 16.46 | 2.64 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 17.80 | 2.70 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 16.46 | 2.64 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 17.80 | 2.70 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 16.46 | 2.64 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 17.80 | 2.70 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 16.46 | 2.64 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 17.80 | 2.70 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 16.84 | 2.66 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 8.04 | 2.74 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 16.29 | 2.64 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 7.81 | 2.70 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 30.39 | 3.56 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 13.38 | 3.53 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 41.54 | 5.52 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 17.74 | 4.42 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 36.01 | 7.39 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 26.51 | 5.78 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.00 | 7.83 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 9.53 | 3.72 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 21.81 | 3.24 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 15.59 | 2.62 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 21.81 | 3.24 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 15.59 | 2.62 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 21.81 | 3.24 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 15.59 | 2.62 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 21.81 | 3.24 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 15.59 | 2.62 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 21.66 | 3.23 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.42 | 2.59 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 21.08 | 3.19 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 8.72 | 3.39 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 38.10 | 4.57 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 13.28 | 4.40 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 48.70 | 6.78 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 13.73 | 4.51 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 38.50 | 8.14 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 16.44 | 5.05 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.44 | 8.04 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 5.54 | 2.55 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | 7.66 | 3.00 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 8.66 | 2.19 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 10.80 | 1.50 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 10.80 | 1.50 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 10.80 | 1.50 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 10.18 | 1.54 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 16.00 | 1.49 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 24.91 | 1.36 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 31.73 | 1.19 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 34.68 | 1.17 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x49` | 35.33 | 1.16 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | 8.72 | 3.28 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 5.53 | 2.36 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 11.22 | 1.43 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 11.22 | 1.43 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 11.22 | 1.43 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 11.22 | 1.43 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 16.37 | 1.33 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 22.58 | 1.26 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 26.44 | 1.23 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 27.76 | 1.23 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x68` | 28.02 | 1.23 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | 7.33 | 2.65 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 6.64 | 2.55 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 27.05 | 1.19 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 27.05 | 1.19 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 27.05 | 1.19 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 27.05 | 1.19 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 27.05 | 1.19 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 26.27 | 1.20 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 41.97 | 1.07 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 41.97 | 1.05 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 42.96 | 1.04 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | 7.02 | 3.39 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 8.66 | 2.81 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 1.68 | 1.41 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 1.93 | 1.68 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 21.81 | 1.11 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 21.81 | 1.11 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 21.81 | 1.11 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 21.81 | 1.11 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 17.97 | 1.06 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 17.57 | 1.04 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 17.83 | 1.03 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 15.59 | 2.60 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 16.16 | 3.08 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 15.59 | 2.60 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 16.16 | 3.08 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 15.59 | 2.60 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 16.16 | 3.08 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 15.59 | 2.60 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 16.16 | 3.08 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 16.50 | 2.48 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 15.08 | 3.12 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 29.97 | 3.12 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 14.69 | 3.08 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 28.43 | 3.53 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 24.78 | 4.07 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 67.50 | 6.23 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 30.30 | 5.14 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 28.75 | 5.92 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 41.75 | 6.62 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 17.84 | 7.51 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 46.76 | 2.68 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 20.26 | 3.08 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 11.78 | 2.86 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 20.26 | 3.08 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 11.78 | 2.86 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 20.26 | 3.08 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 11.78 | 2.86 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 20.26 | 3.08 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 11.78 | 2.86 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 21.07 | 2.87 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 26.16 | 2.76 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 38.02 | 3.84 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 44.60 | 3.50 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 36.15 | 4.36 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 37.64 | 3.30 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 75.27 | 7.51 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 63.22 | 4.14 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 30.02 | 7.56 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 73.35 | 4.58 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 34.59 | 8.14 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 19.86 | 2.07 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 33.79 | 4.04 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 11.34 | 2.15 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 9.33 | 4.28 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.31 | 1.80 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 9.33 | 4.28 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.31 | 1.80 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 9.33 | 4.28 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.31 | 1.80 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 9.33 | 4.28 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.31 | 1.80 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 9.33 | 4.28 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.31 | 1.80 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 14.84 | 4.90 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.83 | 2.00 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 46.69 | 4.59 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 4.82 | 2.67 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 36.29 | 5.93 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 46.89 | 2.19 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 13.12 | 5.62 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 51.61 | 2.13 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x44` | 17.26 | 7.59 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.65 | 6.38 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 19.71 | 3.03 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.65 | 6.38 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 19.71 | 3.03 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.65 | 6.38 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 19.71 | 3.03 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.65 | 6.38 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 19.02 | 3.05 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.65 | 6.38 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.62 | 3.06 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 17.33 | 6.29 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.62 | 3.06 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 17.33 | 6.29 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 28.81 | 5.09 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 30.72 | 10.45 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 31.13 | 8.29 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 43.27 | 18.62 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 15.14 | 8.69 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 21.23 | 19.30 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 18.35 | 2.97 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.62 | 6.27 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 18.35 | 2.97 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.62 | 6.27 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 18.35 | 2.97 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.62 | 6.27 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 18.35 | 2.97 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.62 | 6.27 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 19.04 | 2.96 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.62 | 6.27 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.63 | 2.97 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 17.30 | 6.18 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.63 | 2.97 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 17.30 | 6.18 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 29.52 | 4.99 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 31.48 | 10.55 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 32.75 | 8.31 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 45.56 | 19.36 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 15.76 | 8.75 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 22.61 | 20.49 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 26.18 | 3.07 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 11.67 | 2.93 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 26.18 | 3.07 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 11.88 | 3.17 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 26.18 | 3.07 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 11.88 | 3.17 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 26.18 | 3.07 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 11.88 | 3.17 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 26.18 | 3.07 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 11.88 | 3.17 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 26.18 | 3.07 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 11.88 | 3.17 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 49.30 | 3.97 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 21.21 | 4.72 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 73.66 | 6.30 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 31.64 | 8.45 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 62.03 | 8.78 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 56.25 | 14.35 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 23.29 | 8.92 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 44.68 | 10.66 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 23.70 | 2.79 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.54 | 3.11 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 23.70 | 2.79 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.54 | 3.11 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 23.70 | 2.79 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.54 | 3.11 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 23.70 | 2.79 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.54 | 3.11 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 23.70 | 2.79 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.54 | 3.11 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 23.70 | 2.79 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 12.42 | 3.10 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 44.60 | 3.84 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 23.10 | 4.85 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 77.38 | 5.63 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 38.23 | 9.59 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 75.55 | 8.98 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 83.35 | 19.99 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 27.80 | 9.19 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 25.98 | 11.69 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 24.26 | 2.84 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.78 | 3.12 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 24.26 | 2.84 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.78 | 3.12 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 24.26 | 2.84 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.78 | 3.12 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 24.26 | 2.84 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.78 | 3.12 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 24.26 | 2.84 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.78 | 3.12 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 24.26 | 2.84 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 24.32 | 5.01 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 45.92 | 3.89 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 24.12 | 4.98 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 42.69 | 5.82 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 39.88 | 9.87 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 78.14 | 9.02 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 85.92 | 20.40 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 28.70 | 9.24 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 17.22 | 9.86 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x152` | 39.61 | 4.52 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 14.67 | 2.27 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 22.68 | 3.58 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 35.67 | 1.79 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 22.68 | 3.58 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 35.67 | 1.79 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 22.68 | 3.58 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 35.67 | 1.79 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 22.68 | 3.58 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 35.67 | 1.79 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 39.84 | 3.58 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 35.67 | 1.79 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 16.07 | 5.35 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 33.01 | 1.99 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 74.91 | 4.51 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 63.12 | 2.20 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 46.92 | 4.72 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 79.12 | 2.36 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 15.07 | 4.36 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 83.67 | 2.43 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 26.96 | 4.20 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 19.92 | 6.71 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 26.96 | 4.20 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 19.92 | 6.71 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 26.96 | 4.20 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 19.92 | 6.71 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 26.96 | 4.20 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 19.92 | 6.71 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 26.96 | 4.20 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 12.08 | 6.82 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 24.48 | 4.22 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 11.75 | 6.66 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 24.40 | 4.22 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 11.80 | 6.68 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 35.14 | 7.11 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 18.94 | 13.00 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 33.88 | 10.57 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 39.40 | 26.58 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 15.60 | 9.85 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 16.42 | 22.39 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 24.44 | 4.11 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 12.84 | 7.14 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 24.44 | 4.11 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 12.84 | 7.14 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 24.44 | 4.11 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 12.84 | 7.14 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 24.44 | 4.11 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 12.84 | 7.14 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 24.44 | 4.11 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 12.58 | 7.01 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 24.48 | 4.10 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 12.21 | 6.83 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 24.40 | 4.10 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 12.27 | 6.86 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 36.30 | 7.09 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 21.22 | 14.47 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 35.78 | 10.76 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 52.44 | 35.22 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.27 | 10.01 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 23.75 | 32.64 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 31.31 | 3.89 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 16.04 | 3.46 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 31.31 | 3.89 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 15.98 | 3.01 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 31.31 | 3.89 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 15.98 | 3.01 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 31.31 | 3.89 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 15.98 | 3.01 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 31.31 | 3.89 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 15.98 | 3.01 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 31.31 | 3.89 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 29.83 | 4.47 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 56.48 | 5.44 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 27.92 | 4.92 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 73.12 | 7.98 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 64.25 | 9.57 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 56.17 | 10.30 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 90.78 | 13.08 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 21.20 | 9.85 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 26.19 | 10.34 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 17.46 | 2.72 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 16.80 | 5.39 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 17.46 | 2.72 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 16.80 | 5.39 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 17.46 | 2.72 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 16.80 | 5.39 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 17.46 | 2.72 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 16.80 | 5.39 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 17.46 | 2.72 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 16.80 | 5.39 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 31.08 | 3.61 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 16.58 | 5.33 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 59.73 | 5.11 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 30.23 | 8.96 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 83.71 | 7.99 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 47.10 | 17.66 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 68.29 | 10.87 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 51.62 | 25.41 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 24.96 | 10.38 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 41.45 | 28.69 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 31.92 | 3.70 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 17.04 | 5.47 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 31.92 | 3.70 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 17.04 | 5.47 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 31.92 | 3.70 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 17.04 | 5.47 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 31.92 | 3.70 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 17.04 | 5.47 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 31.92 | 3.70 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 17.04 | 5.47 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 31.92 | 3.70 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 16.83 | 5.35 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 32.80 | 4.08 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 31.94 | 9.37 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 85.62 | 7.99 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 49.27 | 18.35 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 70.62 | 10.99 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 30.42 | 21.19 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 25.71 | 10.48 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 26.25 | 21.77 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 20.73 | 3.74 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 19.90 | 2.83 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 21.75 | 3.32 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 5.01 | 2.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 21.75 | 3.32 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 5.01 | 2.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 21.75 | 3.32 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 5.01 | 2.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x61` | 22.94 | 3.38 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 5.01 | 2.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 17.85 | 3.51 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.99 | 2.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 17.84 | 3.51 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 8.18 | 3.64 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 24.88 | 5.59 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 11.19 | 5.59 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 24.02 | 8.18 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 17.67 | 8.21 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 14.52 | 5.78 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 17.70 | 3.40 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340` | 24.64 | 4.25 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 15.92 | 2.39 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 27.92 | 4.09 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 25.61 | 1.74 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 27.92 | 4.09 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 25.61 | 1.74 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 27.92 | 4.09 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 25.61 | 1.74 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 27.92 | 4.09 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 25.61 | 1.74 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 27.92 | 4.09 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 25.61 | 1.74 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 52.21 | 4.76 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 5.71 | 2.28 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 64.44 | 6.64 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 68.07 | 2.64 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 48.83 | 8.38 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 117.48 | 3.32 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 19.07 | 8.52 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 139.08 | 3.71 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | 27.21 | 4.40 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 20.06 | 2.99 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 28.99 | 4.49 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 19.36 | 2.47 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 28.99 | 4.49 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 19.36 | 2.47 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 28.99 | 4.49 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 19.36 | 2.47 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 28.99 | 4.49 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 19.36 | 2.47 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 22.47 | 4.61 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 35.69 | 3.29 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 22.47 | 4.61 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 38.10 | 3.74 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 29.24 | 7.23 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 40.08 | 5.22 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 25.69 | 9.74 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 51.30 | 5.98 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 14.81 | 7.15 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 27.84 | 4.98 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 15.03 | 4.04 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 21.65 | 2.68 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 31.62 | 2.04 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 31.62 | 2.04 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 31.62 | 2.04 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 31.62 | 2.04 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 31.62 | 2.04 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 31.62 | 2.04 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 72.08 | 2.85 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 104.66 | 3.53 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 116.15 | 3.80 | yes | -- |

## The capacity requirement, stated as a requirement

Every evaluated ROM design carries `weight_capacity_bytes == stored_weight_bytes` (the `romfill` variants reach 1.0039x), so no evaluated design has spare array for a drafter it does not already store. Re-solving the area split is `balanced_area_split`'s job and that file is not touched here, so what follows is a requirement -- this much extra array, or this much extra sweep on every pass -- and not a new design. **The speculative-optimal ROM design has not been computed, only bounded by the rungs that already exist.**

| study | model | design | drafter already in the checkpoint | extra stored bytes | extra array mm2 | as a fraction of the design | sweep inflation if area is held fixed |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x64` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x44` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x152` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |

## Which design the published rule chooses once a block is verified

A re-ranking of designs the study already evaluated, under the study's own selection rule (non-dominated on per-user tokens/s and tokens/s per 1,000 mm2, then a marginal-return walk from the smallest feasible machine). `tau` is a common factor on both axes, so the choice is independent of the acceptance rate. The rule's reproduction of the published autoregressive recommendation is reported first, because a re-ranking whose baseline does not reproduce is not evidence of anything.

| study | model | published recommendation | rule reproduces it | under speculation, draft in ROM | draft in KV store | moves |
| --- | --- | --- | --- | --- | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-wafer-tensor-x2` | yes |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-wafer-tensor-x2` | yes |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-array-hw-tensor-x97` | yes |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-array-hw-tensor-x143` | yes |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-wafer-tensor-x2` | yes |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-wafer-tensor-x2` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | yes | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | yes | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x68` | yes | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x87` | yes | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | `ROM-N6-native-HBMKV-array-hw-tensor-x87` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | no |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x85` | yes | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-SRAMKV-array-hw-hybrid-x59` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-SRAMKV-array-hw-hybrid-x76` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x76` | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | yes |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `ROM-N6-native-SRAMKV-wafer-hybrid-x8` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-tensor-x6` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `ROM-N6-native-SRAMKV-wafer-tensor-x8` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-tensor-x36` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | yes |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | no |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | no |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | no |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x32` | `ROM-N5-native-HBMKV-array-hw-tensor-x34` | yes |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x43` | `ROM-N6-native-HBMKV-array-hw-tensor-x47` | yes |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | yes |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | yes |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | yes |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | no |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-array-hw-tensor-x112` | yes |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-hybrid-x139` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-array-hw-tensor-x138` | yes |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x21` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x27` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x38` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | yes |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x32` | `ROM-N5-native-HBMKV-array-hw-tensor-x32` | yes |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x32` | `ROM-N5-native-HBMKV-array-hw-tensor-x32` | yes |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-array-hw-hybrid-x208` | yes |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-tensor-x3` | yes |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-tensor-x3` | yes |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | no |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-tensor-x45` | yes |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x41` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-tensor-x45` | yes |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-array-hw-tensor-x217` | yes |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-tensor-x4` | yes |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-tensor-x4` | yes |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x31` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x31` | `ROM-N5-native-HBMKV-array-hw-hybrid-x56` | yes |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399-romfill` | yes |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x42` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-tensor-x79` | yes |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | yes |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | yes | `--` | `--` | the drafter does not apply to this model |

**The rule reproduces the published autoregressive recommendation on 56 of 56 model-and-study rows.** Of the 42 rows where it reproduces and the drafter applies, verifying a block moves the chosen rung on 36. Where it moves, it moves toward machines with compute headroom for a block, which is exactly what the arithmetic predicts: a verification pass raises arithmetic intensity by the block size, and a machine sized with just enough compute for one token per sweep has no room for it. **This is a re-ranking of rungs that already exist. The speculative-optimal design has not been computed: that would need the area split re-solved, which is `balanced_area_split`'s job and not this layer's.**

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
| MiMo-V2.6-Flash | 1 | 1,189,400,448 | 9.4% | -- | -- | --x |
| MiMo-V2.6-Flash | 2 | 1,189,400,448 | 9.4% | -- | -- | --x |
| MiMo-V2.6-Flash | 3 | 1,189,400,448 | 9.4% | -- | -- | --x |
| MiMo-V2.6-Flash | 4 | 1,189,400,448 | 9.4% | -- | -- | --x |
| MiMo-V2.6-Flash | 5 | 1,189,400,448 | 9.4% | -- | -- | --x |
| MiMo-V2.6-Flash | 6 | 1,189,400,448 | 9.4% | -- | -- | --x |
| MiMo-V2.6-Flash | 7 | 1,189,400,448 | 9.4% | -- | -- | --x |
| MiMo-V2.6-Flash | 8 | 1,189,400,448 | 9.4% | -- | -- | --x |
| MiMo-V2.6-Pro | 1 | 2,463,635,712 | 6.3% | -- | -- | --x |
| MiMo-V2.6-Pro | 2 | 2,463,635,712 | 6.3% | -- | -- | --x |
| MiMo-V2.6-Pro | 3 | 2,463,635,712 | 6.3% | -- | -- | --x |
| MiMo-V2.6-Pro | 4 | 2,463,635,712 | 6.3% | -- | -- | --x |
| MiMo-V2.6-Pro | 5 | 2,463,635,712 | 6.3% | -- | -- | --x |
| MiMo-V2.6-Pro | 6 | 2,463,635,712 | 6.3% | -- | -- | --x |
| MiMo-V2.6-Pro | 7 | 2,463,635,712 | 6.3% | -- | -- | --x |
| MiMo-V2.6-Pro | 8 | 2,463,635,712 | 6.3% | -- | -- | --x |

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

