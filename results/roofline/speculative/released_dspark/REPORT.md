# Speculative decoding on the area-constrained roofline: released_dspark

> DeepSeek-V4's own speculative module, as shipped. Every figure below is derived from the roofline artifacts
> this repository has already published, by re-assembling each point's own five
> critical-path terms for a speculative cycle. Nothing here re-runs the machine
> model, and nothing here invents an acceptance rate.

## What this layer says

1. **Every term the speculative arithmetic needs is already in the published artifact, exactly.** 180,578 feasible points across 52 studies were rebuilt from their own five critical-path terms and every one reproduced its published step time to 1e-9 relative. Nothing here re-ran the machine model, and the layer is additive by construction rather than by promise.
2. **The headline is a break-even, not a speedup.** `tau* = T_cycle / step_time_s`, and `tau <= gamma+1` always. Of 240,804 (point, draft-placement) pairs where this profile's drafter applies, 85,351 (35.4%) cannot be sped up by speculation at ANY acceptance rate, at any block size on the ladder, even charging the drafter no KV traffic at all.
3. **The ROM-versus-GPU ratio under speculation carries no acceptance rate.** It is `T_cycle(GPU) / T_cycle(ROM)`: `tau` is a property of the model and its drafter, not of the machine, so it is identical on both sides and cancels. Every movement this report shows is a machine effect and nothing else, which is why it can be published without inventing an acceptance rate.
4. **The ratio moves, and it mostly compresses.** Across 775 model-context-batch-class rows, 769 move the ROM-versus-GPU per-user ratio DOWN under speculation and 6 move it UP, spanning 0.010x to 1.086x. The ROM advantage compresses on most operating points.
5. **At batch 1 the two extremes are opposite in sign, and they are the result.** DeepSeek-V4.1-Flash on `array` silicon goes from 3.98x to 0.04x -- a 0.010x movement -- while MiMo-V2.6-Flash on `wafer` silicon goes from 12.94x to 6.33x, a 0.489x movement. A layer that multiplied both sides by `tau` would have reported neither.
6. **A moving ratio is not a win for either side, and the report says so on every table.** At the most favourable sourced acceptance (5.00) speculation is worth having on 15 of 777 ROM class rows and 754 of 777 GPU rows; everywhere else the design runs SLOWER with a drafter than without one. Where both sides lose, a rising ratio means only that the comparator lost more.
7. **Compute is never a gain and always a loss.** A verification pass over `n` positions charges `n` times the arithmetic exactly, so per accepted token compute costs `(n/tau) >= 1` times what it did. A compute-bound design cannot be sped up by speculation at any acceptance rate; it can only be slowed. That is where the recommended ROM designs live, because the sizing rule gives them just enough compute for one token per sweep.
8. **On a mask-ROM machine the draft pass costs a full array sweep, and that is the load-bearing assumption of the whole ROM verdict.** `stored/peak` is a technology constant in `src/opentallas/roofline.py`, so a pass reading only the drafter's region takes as long as sweeping the entire array. The alternative -- holding the drafter in the KV store -- is priced beside it on every ROM row and has NOT been costed in silicon area.
9. **The mask-ROM designs are already storing this drafter, and already sweeping it on every ordinary token.** `_rom_stored_bytes` stores the whole released checkpoint, and the checkpoint ships the draft module for DeepSeek-V4-Flash-0731, DeepSeek-V4-Pro-0813, DeepSeek-V4.1-Flash, DeepSeek-V4.1-Flash-engram-hbm, DeepSeek-V4.1-Flash-engram-host, MiMo-V2.6-Flash, MiMo-V2.6-Pro. So the storage inflation is 1.000x, the extra array requirement is zero, and the autoregressive ROM baseline in the published study is ALREADY paying for a drafter it does not use. The HBM comparators are not: their engaged bytes exclude the draft categories entirely.
10. **This profile does not apply to Kimi-K3, Qwen3-8B.** Their released checkpoints carry no draft weights at all, and transplanting a drafter that was never trained for them would be inventing a model. They are reported as not applicable rather than modelled.
11. **This drafter's SEQUENTIAL step is what it costs on a mask-ROM machine, and it costs more than the drafter's own size.** The bias is applied once per draft token with no transformer re-run, so on a bandwidth machine it moves a table and is nearly free -- but under the locality rule every pass that touches the array takes the full-array sweep time whatever it reads, so `gamma` sequential applications cost `gamma` full sweeps. The draft pass is 7% to 99% of the whole speculative cycle on the ROM designs this report quotes (median 90%), almost all of it those sweeps. A block-diffusion drafter has no such term at all, which is the single largest structural difference between the two profiles on this silicon.
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
| `n5_vs_b200-deepseek-v41-flash` | 4,726 | 0 |
| `n6_vs_a100-deepseek-v41-flash` | 3,744 | 0 |
| `n5_vs_b200-deepseek-v41-flash-1m` | 4,684 | 0 |
| `n6_vs_a100-deepseek-v41-flash-1m` | 3,667 | 0 |
| `n5_vs_b200-deepseek-v41-flash-8k` | 4,630 | 0 |
| `n6_vs_a100-deepseek-v41-flash-8k` | 3,770 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | 5,829 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | 4,638 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | 5,545 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | 4,134 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | 5,766 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | 4,688 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | 5,208 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | 4,468 | 0 |
| `n5_vs_b200-kimi-k3` | 3,322 | 0 |
| `n6_vs_a100-kimi-k3` | 2,094 | 0 |
| `n5_vs_b200-kimi-k3-1m` | 1,543 | 0 |
| `n6_vs_a100-kimi-k3-1m` | 1,140 | 0 |
| `n5_vs_b200-kimi-k3-8k` | 3,087 | 0 |
| `n6_vs_a100-kimi-k3-8k` | 2,046 | 0 |
| `n5_vs_b200-mimo-v26-flash` | 2,817 | 0 |
| `n6_vs_a100-mimo-v26-flash` | 2,055 | 0 |
| `n5_vs_b200-mimo-v26-flash-1m` | 1,628 | 0 |
| `n6_vs_a100-mimo-v26-flash-1m` | 1,386 | 0 |
| `n5_vs_b200-mimo-v26-flash-8k` | 4,174 | 0 |
| `n6_vs_a100-mimo-v26-flash-8k` | 4,436 | 0 |
| `n5_vs_b200-mimo-v26-pro` | 1,523 | 0 |
| `n6_vs_a100-mimo-v26-pro` | 1,209 | 0 |
| `n5_vs_b200-mimo-v26-pro-1m` | 1,790 | 0 |
| `n6_vs_a100-mimo-v26-pro-1m` | 1,239 | 0 |
| `n5_vs_b200-mimo-v26-pro-8k` | 4,776 | 0 |
| `n6_vs_a100-mimo-v26-pro-8k` | 3,783 | 0 |
| `n5_vs_b200-qwen3-8b-1m` | 774 | 0 |
| `n6_vs_a100-qwen3-8b-1m` | 597 | 0 |
| `n5_vs_b200-qwen3-8b-200k` | 1,104 | 0 |
| `n6_vs_a100-qwen3-8b-200k` | 931 | 0 |
| `n5_vs_b200-flash-1m` | 2,485 | 0 |
| `n5_vs_b200-flash-32k` | 4,402 | 0 |
| `n5_vs_b200-flash-8k` | 4,408 | 0 |
| `n5_vs_b200-pro-200k` | 4,353 | 0 |
| `n5_vs_b200-pro-32k` | 4,458 | 0 |
| `n5_vs_b200-pro-8k` | 4,386 | 0 |
| `n6_vs_a100-flash-1m` | 1,797 | 0 |
| `n6_vs_a100-flash-32k` | 4,364 | 0 |
| `n6_vs_a100-flash-8k` | 4,338 | 0 |
| `n6_vs_a100-pro-200k` | 3,455 | 0 |
| `n6_vs_a100-pro-32k` | 3,285 | 0 |
| `n6_vs_a100-pro-8k` | 3,494 | 0 |
| `n5_vs_b200` | 9,049 | 0 |
| `n6_vs_a100` | 7,668 | 0 |
| `n5_vs_b200-quantised_variant` | 2,990 | 0 |
| `n6_vs_a100-quantised_variant` | 2,695 | 0 |

The identity checked is: `max(max(memory, compute)/stage_balance, serial path) x thermal_scale == step_time_s, with memory assembled by designs[].shared_memory_path and the compute-in-ROM fusion rule, and the serial path -- link_latency + layer_fixed_latency + the sweep on the path -- independently rebuilt from the model profile, the technology file and the token's operator graph (opentallas.critical_path)`.

## Headline: where speculation cannot pay at any acceptance rate

Counted at the LOW end of the unsourced drafter-KV band, which is the most favourable assumption available to speculation. `tau*` is the break-even acceptance at this profile's served block size.

| study | model | family | draft placement | binds on (autoregressive) | points | cannot pay at any gamma | tau* min | tau* median | tau* max |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,601 | 438 | 1.19 | 3.88 | 65.78 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 89 | 0 | 1.17 | 3.40 | 4.83 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 440 | 2 | 2.00 | 3.17 | 23.98 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 755 | 216 | 5.00 | 7.46 | 20.72 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 48 | 48 | 17.26 | 18.57 | 20.68 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 485 | 57 | 1.54 | 4.01 | 11.26 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 963 | 109 | 1.36 | 3.10 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 345 | 77 | 2.01 | 5.58 | 11.95 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 755 | 755 | 8.18 | 60.61 | 178.50 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 48 | 48 | 13.99 | 54.63 | 64.29 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 485 | 345 | 2.54 | 18.73 | 126.80 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 963 | 319 | 1.48 | 6.47 | 67.37 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 345 | 315 | 6.75 | 20.58 | 277.26 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 1 | 1 | 8.21 | 8.21 | 8.21 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 779 | 247 | 1.37 | 4.91 | 65.77 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 540 | 1 | 1.35 | 2.84 | 23.39 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 739 | 320 | 5.01 | 8.24 | 22.14 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 46 | 42 | 4.49 | 18.81 | 20.22 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 425 | 51 | 1.55 | 4.72 | 11.44 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 919 | 119 | 1.38 | 3.21 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 295 | 107 | 2.08 | 7.38 | 18.13 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 739 | 739 | 8.18 | 52.49 | 205.35 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 46 | 43 | 5.70 | 55.39 | 125.25 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 425 | 282 | 2.45 | 19.69 | 115.11 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 919 | 258 | 1.52 | 6.20 | 40.73 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 295 | 270 | 6.27 | 16.22 | 275.79 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,571 | 400 | 1.19 | 3.62 | 65.78 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 82 | 0 | 1.19 | 3.51 | 4.72 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 399 | 0 | 2.08 | 3.14 | 7.93 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 751 | 149 | 4.66 | 7.37 | 9.90 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 126 | 36 | 3.20 | 7.74 | 9.58 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 438 | 50 | 1.56 | 3.75 | 8.28 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 1,008 | 118 | 1.36 | 3.02 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 309 | 55 | 1.68 | 5.63 | 9.16 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 751 | 749 | 7.79 | 44.50 | 182.41 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 126 | 123 | 4.37 | 69.18 | 188.58 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 438 | 312 | 2.57 | 16.10 | 146.66 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 1,008 | 327 | 1.48 | 6.40 | 65.86 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 309 | 272 | 5.99 | 16.24 | 263.83 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 2 | 0 | 6.76 | 6.77 | 6.77 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 780 | 243 | 1.37 | 4.69 | 65.72 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 529 | 0 | 1.64 | 2.81 | 13.17 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 684 | 212 | 4.86 | 8.14 | 10.52 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 125 | 8 | 2.57 | 7.47 | 10.24 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 345 | 31 | 1.57 | 4.03 | 8.28 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 958 | 125 | 1.38 | 3.09 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 244 | 71 | 2.14 | 7.60 | 10.66 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 684 | 684 | 8.18 | 43.54 | 202.25 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 125 | 111 | 2.70 | 55.13 | 183.67 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 345 | 246 | 2.77 | 19.28 | 96.45 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 958 | 258 | 1.52 | 6.31 | 39.19 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 244 | 221 | 6.62 | 16.07 | 219.23 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,485 | 411 | 1.19 | 3.94 | 65.79 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 86 | 0 | 1.17 | 3.48 | 4.86 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 419 | 4 | 1.74 | 3.17 | 27.28 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 736 | 197 | 4.82 | 7.27 | 84.59 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 64 | 64 | 36.68 | 88.23 | 92.55 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 470 | 76 | 1.54 | 4.23 | 36.79 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 989 | 161 | 1.36 | 3.38 | 43.00 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 381 | 112 | 2.01 | 5.90 | 62.70 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 736 | 736 | 8.18 | 65.24 | 190.62 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 64 | 51 | 4.59 | 17.55 | 21.97 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 470 | 327 | 2.54 | 18.69 | 140.24 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 989 | 298 | 1.47 | 6.27 | 67.79 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 381 | 347 | 6.75 | 17.56 | 281.52 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 2 | 2 | 8.20 | 8.32 | 8.32 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 719 | 227 | 1.37 | 4.82 | 65.74 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 509 | 1 | 1.36 | 2.84 | 22.00 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 780 | 351 | 4.85 | 8.27 | 90.25 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 46 | 46 | 36.79 | 89.84 | 93.39 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 420 | 70 | 1.55 | 4.67 | 36.79 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 982 | 169 | 1.38 | 3.69 | 37.08 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 312 | 117 | 2.08 | 7.40 | 53.75 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 780 | 780 | 8.19 | 56.24 | 207.01 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 46 | 42 | 5.97 | 17.85 | 22.91 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 420 | 277 | 2.76 | 19.17 | 100.13 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 982 | 265 | 1.51 | 6.15 | 40.85 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 312 | 287 | 7.12 | 16.22 | 281.43 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,963 | 529 | 1.19 | 3.83 | 65.79 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 105 | 0 | 1.17 | 3.40 | 4.83 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 542 | 5 | 2.00 | 3.17 | 23.98 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 828 | 214 | 4.87 | 7.47 | 15.62 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 5 | 2 | 5.87 | 7.78 | 11.96 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 631 | 78 | 1.48 | 4.21 | 10.25 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 1,127 | 131 | 1.36 | 2.82 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 628 | 116 | 1.11 | 5.54 | 14.24 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 828 | 828 | 8.16 | 30.81 | 128.37 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 5 | 3 | 7.33 | 8.80 | 26.58 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 631 | 432 | 2.16 | 10.67 | 94.55 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 1,127 | 290 | 1.42 | 5.77 | 40.91 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 628 | 579 | 5.61 | 19.12 | 180.65 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 3 | 3 | 8.21 | 8.24 | 8.24 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 996 | 312 | 1.37 | 4.81 | 65.77 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 681 | 3 | 1.38 | 2.84 | 23.39 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 717 | 211 | 5.23 | 8.16 | 9.63 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 107 | 98 | 4.00 | 21.28 | 22.17 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 547 | 72 | 1.48 | 5.00 | 16.02 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 1,077 | 128 | 1.36 | 2.87 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 510 | 138 | 1.11 | 6.56 | 19.52 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 717 | 715 | 7.34 | 40.29 | 151.40 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 107 | 104 | 4.04 | 93.80 | 109.10 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 547 | 365 | 2.24 | 14.61 | 95.22 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 1,077 | 235 | 1.43 | 5.54 | 37.17 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 510 | 458 | 5.65 | 19.09 | 180.65 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 2,124 | 552 | 1.19 | 3.82 | 65.78 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 104 | 0 | 1.19 | 3.56 | 4.72 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 536 | 0 | 2.04 | 3.14 | 8.26 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 738 | 149 | 4.66 | 7.40 | 8.32 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 70 | 0 | 3.00 | 7.69 | 8.37 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 551 | 61 | 1.49 | 4.00 | 8.28 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 1,011 | 116 | 1.36 | 2.86 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 411 | 60 | 1.28 | 4.76 | 9.60 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 738 | 738 | 8.15 | 22.31 | 126.77 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 70 | 62 | 3.32 | 49.84 | 84.03 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 551 | 387 | 2.92 | 12.51 | 102.07 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 1,011 | 256 | 1.42 | 5.94 | 39.75 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 411 | 375 | 5.67 | 20.70 | 176.19 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 1 | 0 | 6.76 | 6.76 | 6.76 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,013 | 307 | 1.37 | 4.54 | 65.71 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 657 | 0 | 1.54 | 2.81 | 13.29 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 671 | 192 | 4.45 | 8.15 | 9.16 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 86 | 0 | 2.76 | 6.85 | 7.88 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 390 | 43 | 1.49 | 3.68 | 8.28 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 982 | 113 | 1.36 | 2.86 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 334 | 72 | 1.61 | 6.49 | 11.98 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 671 | 663 | 7.22 | 37.91 | 142.02 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 86 | 66 | 2.29 | 33.72 | 127.03 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 390 | 267 | 2.68 | 15.26 | 90.57 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 982 | 217 | 1.43 | 5.57 | 36.75 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 334 | 310 | 6.01 | 20.12 | 176.52 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,865 | 508 | 1.19 | 3.90 | 65.79 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 99 | 0 | 1.17 | 3.48 | 4.86 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 526 | 7 | 1.74 | 3.17 | 27.28 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 838 | 234 | 4.70 | 7.48 | 15.89 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 643 | 82 | 1.48 | 4.63 | 10.49 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 1,135 | 132 | 1.36 | 2.80 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 660 | 123 | 1.06 | 5.17 | 16.41 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 838 | 838 | 8.16 | 34.38 | 135.06 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 643 | 439 | 2.22 | 10.47 | 95.84 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 1,135 | 296 | 1.42 | 5.78 | 41.23 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 660 | 605 | 5.67 | 18.87 | 181.83 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 4 | 4 | 8.20 | 8.24 | 8.32 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,008 | 316 | 1.37 | 4.77 | 65.75 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 698 | 3 | 1.38 | 2.84 | 22.00 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 800 | 298 | 5.09 | 8.22 | 25.48 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 530 | 84 | 1.48 | 4.81 | 18.27 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 1,095 | 128 | 1.36 | 2.89 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 553 | 150 | 1.06 | 6.43 | 22.80 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 800 | 798 | 7.33 | 44.58 | 146.75 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 530 | 369 | 2.37 | 23.84 | 96.66 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 1,095 | 247 | 1.43 | 5.62 | 37.29 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 553 | 499 | 5.67 | 18.74 | 181.83 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 1,455 | 401 | 1.19 | 3.72 | 65.79 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `thermal` | 95 | 0 | 1.17 | 3.02 | 4.83 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 450 | 6 | 1.94 | 3.17 | 24.65 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 828 | 256 | 4.87 | 7.57 | 18.25 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 51 | 50 | 5.14 | 17.51 | 19.58 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `layer_fixed_latency` | 654 | 80 | 1.54 | 4.74 | 10.25 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 1,109 | 131 | 1.36 | 2.98 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 566 | 98 | 1.98 | 5.71 | 14.24 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 828 | 828 | 8.16 | 29.47 | 102.80 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 51 | 50 | 6.67 | 45.73 | 64.61 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `layer_fixed_latency` | 654 | 438 | 2.22 | 10.28 | 94.55 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 1,109 | 269 | 1.43 | 5.75 | 40.91 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 566 | 527 | 5.61 | 20.23 | 179.66 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `compute` | 6 | 6 | 8.22 | 8.24 | 8.24 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 830 | 290 | 1.37 | 5.59 | 65.77 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 684 | 5 | 1.38 | 2.80 | 17.93 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 692 | 229 | 5.23 | 8.19 | 20.11 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 151 | 142 | 4.00 | 18.60 | 22.17 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `layer_fixed_latency` | 548 | 72 | 1.54 | 5.93 | 16.02 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 1,058 | 128 | 1.36 | 2.90 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 499 | 128 | 2.00 | 6.39 | 19.52 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 692 | 690 | 7.34 | 37.61 | 119.50 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 151 | 148 | 4.05 | 56.11 | 109.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `layer_fixed_latency` | 548 | 365 | 2.24 | 14.54 | 95.22 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 1,058 | 220 | 1.46 | 5.25 | 37.17 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 499 | 443 | 5.79 | 17.59 | 178.60 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 125 | 0 | 1.26 | 1.54 | 17.43 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 950 | 179 | 1.14 | 2.21 | 65.38 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 63 | 0 | 1.28 | 1.78 | 3.12 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 259 | 0 | 1.55 | 2.73 | 8.47 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 8 | 0 | 6.92 | 7.31 | 7.33 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 224 | 0 | 1.05 | 2.10 | 6.93 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 169 | 0 | 1.56 | 6.03 | 17.37 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 589 | 31 | 1.33 | 2.17 | 10.10 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `thermal` | 301 | 0 | 1.52 | 1.91 | 3.64 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 129 | 12 | 1.75 | 5.73 | 8.08 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 8 | 8 | 22.37 | 23.77 | 24.57 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 224 | 113 | 1.16 | 8.53 | 51.06 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 169 | 49 | 2.19 | 7.39 | 31.02 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 589 | 120 | 1.39 | 4.72 | 25.01 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `thermal` | 301 | 221 | 2.36 | 13.66 | 67.21 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 129 | 110 | 6.07 | 11.68 | 22.96 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 36 | 0 | 1.26 | 1.41 | 4.41 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 422 | 92 | 1.25 | 4.20 | 65.22 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 373 | 0 | 1.36 | 1.94 | 9.99 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 22 | 0 | 6.83 | 7.48 | 7.83 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 434 | 0 | 1.06 | 1.65 | 5.93 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 125 | 0 | 1.56 | 5.37 | 15.30 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 515 | 25 | 1.32 | 1.88 | 9.43 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 128 | 14 | 1.85 | 5.30 | 8.08 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 22 | 22 | 14.23 | 21.66 | 27.35 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 434 | 233 | 1.10 | 8.84 | 41.56 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 125 | 32 | 2.33 | 6.70 | 26.70 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 515 | 80 | 1.35 | 3.64 | 13.01 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 128 | 108 | 6.53 | 12.87 | 22.97 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 336 | 5 | 1.24 | 1.53 | 20.98 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 598 | 85 | 1.10 | 2.04 | 64.90 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 222 | 0 | 1.32 | 2.10 | 2.11 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 3 | 0 | 7.82 | 7.82 | 7.82 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 89 | 0 | 1.04 | 1.06 | 7.18 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 150 | 0 | 1.54 | 6.10 | 17.11 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 181 | 0 | 1.25 | 1.99 | 4.35 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 49 | 10 | 2.11 | 6.63 | 8.01 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 3 | 3 | 16.69 | 16.75 | 16.78 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 89 | 37 | 1.11 | 1.46 | 51.30 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 150 | 72 | 2.32 | 7.72 | 30.40 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 181 | 15 | 1.28 | 2.38 | 20.68 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 49 | 48 | 8.10 | 14.66 | 22.99 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 400 | 1 | 1.13 | 1.47 | 19.46 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 475 | 52 | 1.11 | 1.99 | 62.05 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 39 | 0 | 1.87 | 3.37 | 7.06 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 41 | 2 | 7.50 | 7.96 | 8.08 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 107 | 0 | 1.03 | 1.15 | 7.77 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 80 | 0 | 1.62 | 5.26 | 15.10 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 195 | 0 | 1.25 | 2.17 | 5.04 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 49 | 10 | 2.17 | 6.96 | 8.01 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 41 | 41 | 10.07 | 13.82 | 27.55 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 107 | 42 | 1.05 | 1.33 | 33.74 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 80 | 32 | 2.52 | 5.94 | 26.24 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 195 | 7 | 1.25 | 2.77 | 12.25 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 49 | 48 | 8.26 | 14.62 | 22.99 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 19 | 0 | 2.86 | 3.83 | 4.94 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 969 | 268 | 1.15 | 3.28 | 65.49 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 61 | 0 | 1.13 | 1.36 | 3.33 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 421 | 0 | 1.44 | 3.09 | 14.25 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 478 | 44 | 4.78 | 7.46 | 10.31 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 182 | 1 | 1.33 | 6.18 | 11.25 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 562 | 56 | 1.54 | 4.15 | 19.84 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 899 | 64 | 1.29 | 2.54 | 11.77 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 583 | 24 | 1.30 | 5.23 | 10.08 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 478 | 478 | 8.04 | 16.44 | 64.08 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 182 | 144 | 2.27 | 25.56 | 80.66 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 562 | 317 | 2.16 | 8.18 | 49.07 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 899 | 176 | 1.36 | 4.84 | 21.14 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 583 | 559 | 5.27 | 45.81 | 105.32 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `compute` | 18 | 4 | 5.67 | 6.57 | 8.04 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 604 | 241 | 1.39 | 6.62 | 65.48 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 738 | 3 | 1.12 | 2.26 | 19.58 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 614 | 64 | 5.13 | 7.90 | 11.17 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 275 | 7 | 1.21 | 6.06 | 11.11 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 558 | 60 | 1.54 | 4.32 | 17.50 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 1,067 | 107 | 1.31 | 2.55 | 10.02 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 562 | 21 | 1.65 | 5.58 | 11.22 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 614 | 614 | 8.02 | 18.67 | 73.74 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 275 | 200 | 1.64 | 17.29 | 74.54 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 558 | 303 | 2.29 | 8.11 | 55.87 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 1,067 | 172 | 1.37 | 4.39 | 13.85 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 562 | 526 | 5.43 | 21.98 | 105.32 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 65 | 0 | 1.39 | 1.78 | 2.75 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 674 | 128 | 1.14 | 3.38 | 64.87 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 41 | 0 | 1.28 | 2.80 | 3.07 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 323 | 0 | 1.37 | 2.52 | 14.32 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 10 | 0 | 7.69 | 7.85 | 7.99 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 104 | 0 | 1.09 | 1.25 | 6.75 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 68 | 0 | 1.53 | 5.46 | 7.84 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 189 | 0 | 1.30 | 1.78 | 5.02 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 49 | 10 | 1.76 | 5.01 | 8.03 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 10 | 10 | 12.42 | 17.27 | 21.61 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 104 | 56 | 1.39 | 14.50 | 51.45 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 68 | 31 | 2.70 | 7.15 | 20.16 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 189 | 27 | 1.32 | 2.25 | 16.62 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 49 | 41 | 6.47 | 13.40 | 22.97 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 16 | 0 | 1.31 | 1.42 | 1.49 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 363 | 73 | 1.59 | 3.91 | 64.64 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 392 | 0 | 1.22 | 1.96 | 17.36 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 18 | 0 | 7.51 | 7.89 | 8.05 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 94 | 0 | 1.11 | 1.24 | 7.69 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 45 | 0 | 1.50 | 4.01 | 6.17 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 200 | 0 | 1.28 | 1.88 | 4.60 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 81 | 12 | 1.84 | 5.47 | 8.06 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 18 | 18 | 12.02 | 18.76 | 30.98 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 94 | 47 | 1.27 | 10.82 | 32.17 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 45 | 5 | 3.02 | 5.73 | 11.47 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 200 | 15 | 1.29 | 2.29 | 11.64 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 81 | 73 | 7.09 | 13.96 | 22.98 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 254 | 0 | 1.30 | 1.45 | 16.12 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 832 | 109 | 1.07 | 2.42 | 63.05 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 221 | 0 | 1.32 | 1.99 | 2.08 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 6 | 0 | 3.20 | 3.81 | 6.65 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 12 | 2 | 5.11 | 7.91 | 8.16 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 90 | 0 | 1.04 | 1.06 | 6.04 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 157 | 6 | 1.55 | 6.71 | 8.12 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 167 | 0 | 1.21 | 1.91 | 4.67 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 51 | 10 | 2.02 | 7.00 | 8.01 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 12 | 8 | 5.40 | 20.05 | 31.29 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 90 | 29 | 1.17 | 1.54 | 51.31 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 157 | 96 | 2.92 | 8.84 | 18.68 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 167 | 2 | 1.22 | 2.21 | 13.10 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 51 | 49 | 7.88 | 13.78 | 22.99 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 276 | 0 | 1.24 | 1.48 | 17.40 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 381 | 44 | 1.50 | 2.35 | 58.89 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 150 | 0 | 1.08 | 2.20 | 13.07 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 39 | 6 | 4.63 | 8.00 | 8.10 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 85 | 0 | 1.03 | 1.05 | 5.59 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 91 | 2 | 1.55 | 5.83 | 8.08 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 167 | 0 | 1.20 | 2.03 | 4.47 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 50 | 10 | 2.06 | 7.26 | 8.01 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 39 | 35 | 6.49 | 15.94 | 34.54 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 85 | 23 | 1.07 | 1.29 | 33.91 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 91 | 41 | 3.18 | 7.30 | 22.91 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 167 | 6 | 1.20 | 2.28 | 9.99 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 50 | 50 | 9.26 | 14.13 | 22.99 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 2 | 0 | 4.06 | 4.54 | 4.54 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 1,125 | 339 | 1.18 | 4.70 | 65.02 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 68 | 0 | 1.14 | 2.59 | 4.04 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 625 | 6 | 1.52 | 2.68 | 23.37 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 604 | 32 | 4.82 | 7.62 | 11.57 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 170 | 4 | 1.38 | 6.27 | 11.40 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 469 | 58 | 1.59 | 3.80 | 8.14 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 1,136 | 78 | 1.30 | 3.07 | 8.28 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 577 | 30 | 2.07 | 5.74 | 9.61 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 604 | 604 | 8.09 | 21.58 | 85.40 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 170 | 151 | 2.48 | 29.60 | 81.30 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 469 | 324 | 2.62 | 14.08 | 48.52 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 1,136 | 288 | 1.40 | 6.17 | 28.44 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 577 | 531 | 6.63 | 20.64 | 108.28 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `compute` | 2 | 0 | 5.95 | 7.05 | 7.05 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 571 | 199 | 1.59 | 5.99 | 65.00 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 666 | 4 | 1.20 | 2.16 | 20.06 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 566 | 32 | 5.06 | 7.93 | 11.57 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 201 | 4 | 1.23 | 6.21 | 11.72 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 373 | 38 | 1.49 | 3.97 | 8.13 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 1,003 | 102 | 1.31 | 3.09 | 8.30 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 401 | 36 | 2.13 | 6.73 | 11.65 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 566 | 566 | 8.07 | 26.60 | 92.57 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 201 | 158 | 1.82 | 29.32 | 107.25 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 373 | 235 | 2.96 | 9.58 | 52.71 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 1,003 | 195 | 1.44 | 5.91 | 25.81 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 401 | 369 | 5.52 | 20.39 | 101.40 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,068 | 351 | 1.81 | 6.51 | 60.93 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 25 | 0 | 1.97 | 2.77 | 3.54 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 294 | 0 | 2.47 | 2.93 | 5.69 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 133 | 18 | 6.16 | 7.11 | 8.36 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 57 | 0 | 2.13 | 3.26 | 6.68 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 123 | 0 | 1.53 | 3.81 | 5.28 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 505 | 112 | 1.72 | 5.09 | 10.63 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `thermal` | 14 | 0 | 5.10 | 5.61 | 6.05 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 266 | 38 | 1.84 | 3.73 | 8.15 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 133 | 133 | 8.29 | 23.60 | 71.84 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 57 | 11 | 1.79 | 4.81 | 51.60 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 123 | 71 | 1.78 | 9.53 | 59.63 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 505 | 174 | 1.74 | 6.23 | 38.65 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `thermal` | 14 | 14 | 10.55 | 20.19 | 44.49 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 266 | 238 | 5.96 | 16.66 | 116.78 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,221 | 376 | 1.27 | 4.73 | 65.62 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 67 | 0 | 1.23 | 1.81 | 3.93 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 302 | 0 | 2.67 | 2.87 | 12.34 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 461 | 210 | 5.37 | 8.18 | 20.20 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 44 | 38 | 5.70 | 26.54 | 34.76 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 795 | 110 | 1.45 | 5.54 | 21.19 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,093 | 207 | 1.45 | 3.77 | 11.38 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 419 | 64 | 1.65 | 5.11 | 15.01 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 461 | 457 | 8.03 | 12.68 | 43.72 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 44 | 40 | 5.60 | 31.19 | 98.85 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 795 | 634 | 1.75 | 31.19 | 58.48 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,093 | 305 | 1.49 | 5.84 | 30.52 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 419 | 397 | 6.24 | 18.53 | 113.07 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,184 | 365 | 1.25 | 4.65 | 65.63 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 69 | 0 | 1.23 | 1.82 | 4.62 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 327 | 2 | 2.20 | 2.94 | 15.79 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 465 | 217 | 5.29 | 8.23 | 37.24 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 52 | 51 | 9.72 | 63.65 | 79.79 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 813 | 140 | 1.45 | 5.48 | 44.49 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,081 | 196 | 1.44 | 3.96 | 17.20 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 417 | 56 | 1.63 | 5.18 | 38.91 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 465 | 461 | 8.08 | 13.08 | 38.03 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 52 | 50 | 5.13 | 35.19 | 62.29 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 813 | 644 | 1.75 | 31.05 | 58.81 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,081 | 286 | 1.47 | 5.67 | 30.68 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 417 | 396 | 7.12 | 18.56 | 113.29 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,548 | 537 | 1.50 | 6.54 | 64.82 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 82 | 0 | 1.55 | 4.17 | 4.76 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 455 | 0 | 2.61 | 3.21 | 4.18 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 647 | 216 | 5.14 | 7.69 | 13.76 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 48 | 42 | 6.77 | 13.19 | 14.40 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 273 | 6 | 1.35 | 3.91 | 8.97 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 998 | 248 | 1.59 | 5.02 | 8.39 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 302 | 59 | 1.95 | 6.89 | 10.91 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 647 | 631 | 7.13 | 24.51 | 106.57 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 48 | 45 | 5.23 | 74.43 | 106.70 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 273 | 207 | 1.82 | 15.76 | 71.89 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 998 | 359 | 1.64 | 7.46 | 33.34 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 302 | 269 | 5.78 | 15.99 | 144.40 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,518 | 490 | 1.38 | 5.97 | 65.13 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 87 | 0 | 1.22 | 4.18 | 4.83 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 435 | 0 | 1.97 | 3.22 | 9.18 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 687 | 308 | 5.37 | 7.92 | 42.33 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 24 | 24 | 41.24 | 45.48 | 52.45 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 398 | 35 | 1.35 | 3.77 | 15.81 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 949 | 192 | 1.53 | 4.85 | 8.39 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 360 | 86 | 1.96 | 7.57 | 23.12 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 687 | 683 | 7.06 | 34.68 | 106.39 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 24 | 24 | 30.09 | 65.85 | 80.42 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 398 | 263 | 1.79 | 12.53 | 75.40 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 949 | 288 | 1.70 | 7.14 | 34.43 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 360 | 317 | 6.07 | 16.10 | 146.73 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,385 | 450 | 1.37 | 5.87 | 65.09 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 82 | 0 | 1.25 | 4.19 | 4.83 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 423 | 2 | 1.97 | 3.23 | 19.58 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 696 | 299 | 5.39 | 7.88 | 87.51 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 34 | 34 | 85.84 | 93.34 | 105.30 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 405 | 48 | 1.35 | 4.05 | 40.34 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 983 | 215 | 1.52 | 4.90 | 21.37 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 378 | 88 | 1.95 | 7.54 | 34.89 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 696 | 694 | 7.68 | 35.91 | 109.21 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 34 | 34 | 16.66 | 40.21 | 44.41 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 405 | 268 | 1.78 | 12.91 | 75.70 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 983 | 301 | 1.69 | 7.17 | 34.58 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 378 | 331 | 5.96 | 16.12 | 147.17 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 668 | 256 | 2.18 | 7.06 | 51.19 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 295 | 0 | 2.63 | 3.04 | 11.63 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 56 | 4 | 6.39 | 7.34 | 8.44 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 128 | 0 | 2.16 | 3.75 | 7.69 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 63 | 0 | 1.53 | 1.88 | 5.85 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 421 | 72 | 1.74 | 4.61 | 10.57 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 166 | 37 | 1.90 | 4.40 | 8.10 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 56 | 56 | 9.01 | 24.78 | 74.14 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 128 | 63 | 1.47 | 8.20 | 83.67 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 63 | 24 | 1.72 | 4.68 | 60.95 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 421 | 126 | 1.76 | 6.33 | 30.18 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 166 | 149 | 6.72 | 17.26 | 117.86 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 2 | 1 | 7.69 | 8.24 | 8.24 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 904 | 306 | 1.45 | 6.27 | 65.56 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 454 | 0 | 1.45 | 3.17 | 7.21 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 573 | 323 | 4.67 | 8.48 | 20.54 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 137 | 122 | 4.19 | 25.94 | 34.76 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 644 | 61 | 1.45 | 6.64 | 22.29 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,202 | 237 | 1.46 | 4.24 | 11.69 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 448 | 131 | 2.07 | 6.92 | 23.54 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 573 | 533 | 5.74 | 13.52 | 60.87 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 137 | 125 | 3.04 | 47.29 | 98.85 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 644 | 475 | 1.82 | 25.13 | 67.04 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,202 | 307 | 1.50 | 5.59 | 27.69 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 448 | 416 | 6.31 | 18.34 | 112.83 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 1 | 1 | 8.56 | 8.56 | 8.56 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 846 | 287 | 1.42 | 6.24 | 65.57 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 463 | 0 | 1.40 | 3.15 | 12.51 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 558 | 363 | 5.76 | 8.52 | 50.97 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 62 | 61 | 7.85 | 59.87 | 79.79 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 741 | 122 | 1.45 | 7.12 | 34.21 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,202 | 220 | 1.44 | 4.16 | 11.51 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 465 | 136 | 2.07 | 7.18 | 33.81 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 558 | 534 | 7.41 | 13.57 | 60.93 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 62 | 59 | 5.33 | 34.91 | 62.29 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 741 | 555 | 1.82 | 29.45 | 67.42 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,202 | 283 | 1.48 | 5.36 | 27.82 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 465 | 434 | 6.53 | 18.43 | 113.17 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 585 | 321 | 2.71 | 8.28 | 63.65 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 794 | 0 | 1.71 | 3.21 | 6.19 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 622 | 394 | 4.84 | 8.54 | 15.20 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 44 | 37 | 7.28 | 13.59 | 15.66 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 207 | 6 | 1.35 | 3.86 | 8.21 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 964 | 248 | 1.59 | 5.23 | 8.39 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 239 | 79 | 2.02 | 7.69 | 13.94 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 622 | 602 | 6.59 | 37.11 | 112.11 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 44 | 40 | 3.46 | 77.98 | 112.90 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 207 | 157 | 1.91 | 16.32 | 47.10 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 964 | 316 | 1.67 | 7.23 | 23.55 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 239 | 205 | 6.60 | 14.67 | 23.00 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 491 | 276 | 3.35 | 8.28 | 64.87 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 748 | 1 | 1.44 | 3.20 | 15.51 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 609 | 422 | 4.97 | 8.66 | 47.30 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 23 | 21 | 7.70 | 48.54 | 53.03 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 312 | 35 | 1.35 | 4.92 | 23.93 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 854 | 176 | 1.59 | 4.87 | 8.39 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 248 | 100 | 1.99 | 8.18 | 34.48 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 609 | 605 | 7.00 | 43.53 | 120.76 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 23 | 21 | 6.22 | 69.08 | 80.73 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 312 | 202 | 1.88 | 16.20 | 81.87 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 854 | 231 | 1.72 | 6.84 | 24.77 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 248 | 217 | 6.56 | 16.22 | 147.15 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 1 | 1 | 8.39 | 8.39 | 8.39 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 483 | 286 | 3.00 | 8.35 | 65.08 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 796 | 1 | 1.45 | 3.18 | 19.71 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 677 | 466 | 4.99 | 8.74 | 94.17 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 29 | 28 | 9.50 | 96.20 | 105.30 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 359 | 45 | 1.35 | 5.02 | 40.63 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 890 | 206 | 1.59 | 5.17 | 22.16 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 259 | 112 | 1.99 | 8.18 | 40.25 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 677 | 673 | 7.06 | 42.33 | 122.96 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 29 | 29 | 8.74 | 42.40 | 45.11 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 359 | 228 | 1.87 | 15.02 | 83.68 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 890 | 248 | 1.71 | 6.87 | 24.98 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 259 | 228 | 6.09 | 16.18 | 147.71 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,056 | 323 | 1.38 | 5.30 | 65.31 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 42 | 0 | 1.23 | 2.23 | 3.90 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 275 | 0 | 2.38 | 2.81 | 4.09 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 229 | 103 | 6.20 | 8.18 | 8.79 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 68 | 0 | 3.17 | 8.06 | 8.69 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 589 | 5 | 1.46 | 5.23 | 13.57 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,015 | 234 | 1.49 | 4.65 | 10.44 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 411 | 39 | 1.74 | 4.10 | 12.11 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 229 | 229 | 8.23 | 12.37 | 44.70 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 68 | 54 | 2.45 | 23.22 | 41.44 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 589 | 504 | 1.75 | 36.25 | 67.10 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,015 | 347 | 1.53 | 6.37 | 41.22 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 411 | 377 | 6.25 | 21.77 | 111.76 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,131 | 400 | 1.81 | 6.92 | 59.79 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 40 | 0 | 3.35 | 4.14 | 5.84 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 315 | 0 | 2.84 | 3.14 | 6.36 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 106 | 15 | 6.30 | 7.70 | 8.60 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 44 | 10 | 3.20 | 5.16 | 8.56 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 88 | 0 | 1.41 | 2.31 | 6.60 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 366 | 72 | 1.74 | 4.60 | 8.39 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 194 | 21 | 1.79 | 4.78 | 8.16 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 106 | 104 | 7.51 | 49.88 | 97.16 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 44 | 30 | 3.62 | 16.68 | 139.08 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 88 | 40 | 2.02 | 6.44 | 67.87 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 366 | 121 | 1.93 | 6.74 | 33.01 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 194 | 164 | 5.34 | 14.35 | 168.35 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 880 | 304 | 1.63 | 6.29 | 64.65 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 418 | 0 | 1.81 | 3.16 | 5.83 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 399 | 133 | 6.71 | 8.60 | 10.05 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 99 | 16 | 3.31 | 8.16 | 10.62 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 274 | 0 | 1.46 | 4.24 | 7.32 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,008 | 226 | 1.50 | 4.62 | 13.54 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 370 | 41 | 2.11 | 5.98 | 8.81 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 399 | 399 | 8.23 | 40.41 | 66.17 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 99 | 74 | 1.80 | 15.30 | 72.28 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 274 | 205 | 1.82 | 18.64 | 62.92 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,008 | 320 | 1.52 | 6.41 | 26.91 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 370 | 345 | 5.21 | 50.30 | 111.15 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 574 | 249 | 2.03 | 7.80 | 50.89 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 393 | 10 | 2.71 | 3.45 | 12.75 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 53 | 11 | 7.22 | 7.93 | 9.23 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 54 | 1 | 2.85 | 3.86 | 8.66 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 55 | 0 | 1.42 | 2.09 | 5.04 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 193 | 15 | 1.81 | 4.35 | 8.32 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 68 | 13 | 1.86 | 4.57 | 8.18 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 53 | 51 | 7.54 | 40.42 | 91.76 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 54 | 36 | 2.84 | 9.26 | 126.66 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 55 | 15 | 2.11 | 3.96 | 31.31 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 193 | 28 | 1.98 | 6.38 | 20.39 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 68 | 58 | 6.22 | 11.90 | 23.00 |

## Per model, per context, per batch and per design class

Each row is that class's **fastest** feasible design at that batch, read against the iso-area GPU comparator the published study already chose for it. The `densest` pick of every class is in `analytical.json` beside it.

**The ROM-versus-GPU ratio under speculation is `T_cycle(GPU) / T_cycle(ROM)` and carries no `tau` at all.** The acceptance length is a property of the model and its drafter, not of the machine, so it is the same on both sides and cancels out of the ratio. Every movement in the last column is therefore a machine effect and nothing else.

### `n5_vs_b200-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 4,107.2 | 337.7-337.7 | 60.80 | **no** | `b200_sxm-x93-nvl72-hybrid` | 1,056.7 | 4,330.1-4,330.1 | 1.22 | yes | 3.887x | 0.078x | 0.020x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,326.1 | 699.1-699.1 | 38.09 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,053.8 | 4,301.3-4,301.3 | 1.22 | yes | 5.054x | 0.163x | 0.032x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 4,107.2 | 337.7-337.7 | 60.80 | **no** | `b200_sxm-x93-nvl72-hybrid` | 1,056.7 | 4,330.1-4,330.1 | 1.22 | yes | 3.887x | 0.078x | 0.020x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,326.1 | 699.1-699.1 | 38.09 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,053.8 | 4,301.3-4,301.3 | 1.22 | yes | 5.054x | 0.163x | 0.032x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 4,107.2 | 337.7-337.7 | 60.80 | **no** | `b200_sxm-x93-nvl72-hybrid` | 1,032.2 | 3,903.0-3,903.0 | 1.32 | yes | 3.979x | 0.087x | 0.022x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,326.1 | 699.1-699.1 | 38.09 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,028.4 | 3,870.4-3,870.4 | 1.33 | yes | 5.179x | 0.181x | 0.035x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 4,107.2 | 337.7-337.7 | 60.80 | **no** | `b200_sxm-x93-nvl72-hybrid` | 988.2 | 3,512.1-3,512.1 | 1.41 | yes | 4.156x | 0.096x | 0.023x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,326.1 | 699.1-699.1 | 38.09 | **no** | `b200_sxm-x87-nvl72-hybrid` | 982.2 | 3,465.5-3,465.5 | 1.42 | yes | 5.423x | 0.202x | 0.037x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 4,107.2 | 337.7-337.7 | 60.80 | **no** | `b200_sxm-x93-nvl72-hybrid` | 925.7 | 2,920.4-2,920.4 | 1.58 | yes | 4.437x | 0.116x | 0.026x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,326.1 | 699.1-699.1 | 38.09 | **no** | `b200_sxm-x87-nvl72-hybrid` | 922.5 | 2,881.7-2,881.7 | 1.60 | yes | 5.774x | 0.243x | 0.042x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 4,107.2 | 337.7-337.7 | 60.80 | **no** | `b200_sxm-x93-nvl72-hybrid` | 837.4 | 2,368.8-2,368.8 | 1.77 | yes | 4.905x | 0.143x | 0.029x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,186.8 | 844.9-844.9 | 30.69 | **no** | `b200_sxm-x231-nvl72-hybrid` | 932.5 | 2,950.8-2,950.8 | 1.58 | yes | 5.562x | 0.286x | 0.051x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x185` | 4,035.9 | 169.4-169.4 | 119.14 | **no** | `b200_sxm-x94-nvl72-hybrid` | 709.0 | 1,558.1-1,558.1 | 2.28 | yes | 5.692x | 0.109x | 0.019x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,183.6 | 840.3-840.3 | 30.85 | **no** | `b200_sxm-x347-nvl72-hybrid` | 886.5 | 2,645.1-2,645.1 | 1.68 | yes | 5.847x | 0.318x | 0.054x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 3,044.5 | 200.1-200.1 | 76.05 | **no** | `b200_sxm-x179-nvl72-hybrid` | 526.9 | 1,022.9-1,022.9 | 2.58 | yes | 5.778x | 0.196x | 0.034x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,173.4 | 422.8-422.8 | 49.35 | **no** | `b200_sxm-x347-nvl72-hybrid` | 664.4 | 1,482.1-1,482.1 | 2.24 | yes | 6.281x | 0.285x | 0.045x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 1,567.7 | 86.5-86.5 | 90.59 | **no** | `b200_sxm-x179-nvl72-hybrid` | 265.4 | 470.7-470.7 | 2.82 | yes | 5.907x | 0.184x | 0.031x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,147.3 | 107.6-107.6 | 99.83 | **no** | `b200_sxm-x347-nvl72-hybrid` | 355.2 | 735.8-735.8 | 2.41 | yes | 6.045x | 0.146x | 0.024x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 551.2 | 41.1-41.1 | 67.00 | **no** | `b200_sxm-x179-nvl72-hybrid` | 142.2 | 156.5-156.5 | 4.54 | yes | 3.875x | 0.263x | 0.068x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 685.6 | 85.1-85.1 | 40.29 | **no** | `b200_sxm-x347-nvl72-hybrid` | 172.6 | 206.8-206.8 | 4.17 | yes | 3.971x | 0.411x | 0.104x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.019x to 0.104x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,830.0 | 237.3-237.3 | 80.71 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 1,056.6-1,056.6 | 2.06 | yes | 8.809x | 0.225x | 0.025x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,041.0 | 533.2-533.2 | 47.27 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 1,104.2-1,104.2 | 2.00 | yes | 11.395x | 0.483x | 0.042x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,830.0 | 237.3-237.3 | 80.71 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 1,056.6-1,056.6 | 2.06 | yes | 8.809x | 0.225x | 0.025x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,041.0 | 533.2-533.2 | 47.27 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 1,104.2-1,104.2 | 2.00 | yes | 11.395x | 0.483x | 0.042x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,830.0 | 237.3-237.3 | 80.71 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 1,056.6-1,056.6 | 2.06 | yes | 8.809x | 0.225x | 0.025x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,041.0 | 533.2-533.2 | 47.27 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 1,104.2-1,104.2 | 2.00 | yes | 11.395x | 0.483x | 0.042x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,830.0 | 237.3-237.3 | 80.71 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 1,056.6-1,056.6 | 2.06 | yes | 8.809x | 0.225x | 0.025x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,041.0 | 533.2-533.2 | 47.27 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 1,104.2-1,104.2 | 2.00 | yes | 11.395x | 0.483x | 0.042x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,830.0 | 237.3-237.3 | 80.71 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 1,056.6-1,056.6 | 2.06 | yes | 8.809x | 0.225x | 0.025x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,041.0 | 533.2-533.2 | 47.27 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 1,104.2-1,104.2 | 2.00 | yes | 11.395x | 0.483x | 0.042x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,830.0 | 237.3-237.3 | 80.71 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 1,056.6-1,056.6 | 2.06 | yes | 8.809x | 0.225x | 0.025x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4,915.6 | 615.8-615.8 | 39.91 | **no** | `a100_sxm_80gb-x448-hybrid` | 433.5 | 974.5-974.5 | 2.22 | yes | 11.341x | 0.632x | 0.056x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,830.0 | 237.3-237.3 | 80.71 | **no** | `a100_sxm_80gb-x258-hybrid` | 375.9 | 778.6-778.6 | 2.41 | yes | 10.188x | 0.305x | 0.030x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,911.3 | 612.3-612.3 | 40.10 | **no** | `a100_sxm_80gb-x672-hybrid` | 433.5 | 909.2-909.2 | 2.38 | yes | 11.331x | 0.673x | 0.059x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 2,891.3 | 93.0-93.0 | 155.49 | **no** | `a100_sxm_80gb-x335-hybrid` | 234.9 | 390.3-390.3 | 3.01 | yes | 12.307x | 0.238x | 0.019x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,669.5 | 306.3-306.3 | 59.90 | **no** | `a100_sxm_80gb-x672-hybrid` | 322.5 | 544.3-544.3 | 2.96 | yes | 11.378x | 0.563x | 0.049x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,181.8 | 45.2-45.2 | 130.87 | **no** | `a100_sxm_80gb-x337-hybrid` | 98.0 | 179.9-179.9 | 2.72 | yes | 12.058x | 0.251x | 0.021x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,679.0 | 91.2-91.2 | 92.02 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.6 | 233.7-233.7 | 3.33 | yes | 10.791x | 0.390x | 0.036x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 328.7 | 39.0-39.0 | 42.18 | **no** | `a100_sxm_80gb-x337-hybrid` | 37.3 | 49.3-49.3 | 3.79 | yes | 8.804x | 0.791x | 0.090x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 606.8 | 44.2-44.2 | 68.70 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.3 | 116.6-116.6 | 2.54 | yes | 10.232x | 0.379x | 0.037x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.019x to 0.090x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 3,851.3 | 273.1-273.1 | 70.50 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,064.7 | 4,411.9-4,411.9 | 1.21 | yes | 3.617x | 0.062x | 0.017x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,803.1 | 843.9-843.9 | 28.46 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,071.3 | 4,468.0-4,468.0 | 1.20 | yes | 4.484x | 0.189x | 0.042x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 3,851.3 | 273.1-273.1 | 70.50 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,064.7 | 4,411.9-4,411.9 | 1.21 | yes | 3.617x | 0.062x | 0.017x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,803.1 | 843.9-843.9 | 28.46 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,071.3 | 4,468.0-4,468.0 | 1.20 | yes | 4.484x | 0.189x | 0.042x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 3,851.3 | 273.1-273.1 | 70.50 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,042.0 | 3,994.2-3,994.2 | 1.30 | yes | 3.696x | 0.068x | 0.019x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,803.1 | 843.9-843.9 | 28.46 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,050.4 | 4,053.0-4,053.0 | 1.30 | yes | 4.573x | 0.208x | 0.046x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 3,851.3 | 273.1-273.1 | 70.50 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,000.0 | 3,382.7-3,382.7 | 1.48 | yes | 3.851x | 0.081x | 0.021x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,803.1 | 843.9-843.9 | 28.46 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,012.0 | 3,622.1-3,622.1 | 1.40 | yes | 4.746x | 0.233x | 0.049x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 3,851.3 | 273.1-273.1 | 70.50 | **no** | `b200_sxm-x116-nvl72-hybrid` | 941.9 | 3,083.0-3,083.0 | 1.53 | yes | 4.089x | 0.089x | 0.022x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,803.1 | 843.9-843.9 | 28.46 | **no** | `b200_sxm-x144-nvl72-hybrid` | 958.0 | 3,235.6-3,235.6 | 1.48 | yes | 5.014x | 0.261x | 0.052x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 3,851.3 | 273.1-273.1 | 70.50 | **no** | `b200_sxm-x116-nvl72-hybrid` | 860.9 | 2,527.9-2,527.9 | 1.70 | yes | 4.474x | 0.108x | 0.024x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,641.4 | 1,546.6-1,546.6 | 15.00 | **no** | `b200_sxm-x347-nvl72-hybrid` | 957.9 | 3,145.8-3,145.8 | 1.52 | yes | 4.846x | 0.492x | 0.101x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 3,773.0 | 237.8-237.8 | 79.33 | **no** | `b200_sxm-x134-nvl72-hybrid` | 769.2 | 1,983.9-1,983.9 | 1.94 | yes | 4.905x | 0.120x | 0.024x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,491.2 | 818.8-818.8 | 27.43 | **no** | `b200_sxm-x347-nvl72-hybrid` | 882.2 | 2,636.5-2,636.5 | 1.67 | yes | 5.091x | 0.311x | 0.061x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 2,731.9 | 93.1-93.1 | 146.66 | **no** | `b200_sxm-x173-nvl72-hybrid` | 508.1 | 1,002.9-1,002.9 | 2.53 | yes | 5.377x | 0.093x | 0.017x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,068.8 | 409.1-409.1 | 37.51 | **no** | `b200_sxm-x347-nvl72-hybrid` | 654.9 | 1,470.6-1,470.6 | 2.23 | yes | 4.686x | 0.278x | 0.059x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 1,255.7 | 44.1-44.1 | 142.23 | **no** | `b200_sxm-x179-nvl72-hybrid` | 254.0 | 463.1-463.1 | 2.74 | yes | 4.944x | 0.095x | 0.019x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,259.1 | 46.8-46.8 | 134.59 | **no** | `b200_sxm-x347-nvl72-hybrid` | 344.5 | 726.0-726.0 | 2.37 | yes | 3.654x | 0.064x | 0.018x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 360.6 | 38.7-38.7 | 46.61 | **no** | `b200_sxm-x179-nvl72-hybrid` | 129.7 | 153.3-153.3 | 4.23 | yes | 2.780x | 0.252x | 0.091x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 359.4 | 23.0-23.0 | 78.26 | **no** | `b200_sxm-x347-nvl72-hybrid` | 162.8 | 203.9-203.9 | 3.99 | yes | 2.208x | 0.113x | 0.051x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.017x to 0.101x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,552.7 | 359.2-359.2 | 49.46 | **no** | `a100_sxm_80gb-x337-hybrid` | 427.3 | 998.1-998.1 | 2.14 | yes | 8.313x | 0.360x | 0.043x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 4,448.8 | 1,269.6-1,269.6 | 17.52 | **no** | `a100_sxm_80gb-x168-hybrid` | 444.9 | 1,149.4-1,149.4 | 1.94 | yes | 10.000x | 1.105x | 0.110x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,552.7 | 359.2-359.2 | 49.46 | **no** | `a100_sxm_80gb-x337-hybrid` | 427.3 | 998.1-998.1 | 2.14 | yes | 8.313x | 0.360x | 0.043x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,212.6 | 699.1-699.1 | 30.13 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 9.780x | 0.771x | 0.079x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,552.7 | 359.2-359.2 | 49.46 | **no** | `a100_sxm_80gb-x337-hybrid` | 427.3 | 998.1-998.1 | 2.14 | yes | 8.313x | 0.360x | 0.043x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,212.6 | 699.1-699.1 | 30.13 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 9.780x | 0.771x | 0.079x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,552.7 | 359.2-359.2 | 49.46 | **no** | `a100_sxm_80gb-x337-hybrid` | 427.3 | 998.1-998.1 | 2.14 | yes | 8.313x | 0.360x | 0.043x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,212.6 | 699.1-699.1 | 30.13 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 9.780x | 0.771x | 0.079x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,552.7 | 359.2-359.2 | 49.46 | **no** | `a100_sxm_80gb-x337-hybrid` | 427.3 | 998.1-998.1 | 2.14 | yes | 8.313x | 0.360x | 0.043x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,212.6 | 699.1-699.1 | 30.13 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 9.780x | 0.771x | 0.079x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,552.7 | 359.2-359.2 | 49.46 | **no** | `a100_sxm_80gb-x337-hybrid` | 427.3 | 998.1-998.1 | 2.14 | yes | 8.313x | 0.360x | 0.043x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,116.3 | 367.5-367.5 | 56.01 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 9.556x | 0.405x | 0.042x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 3,535.8 | 184.8-184.8 | 95.65 | **no** | `a100_sxm_80gb-x335-hybrid` | 394.2 | 842.1-842.1 | 2.34 | yes | 8.969x | 0.219x | 0.024x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,540.0 | 364.0-364.0 | 48.63 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 8.218x | 0.401x | 0.049x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 2,395.1 | 91.3-91.3 | 131.23 | **no** | `a100_sxm_80gb-x337-hybrid` | 230.7 | 389.7-389.7 | 2.96 | yes | 10.380x | 0.234x | 0.023x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,874.5 | 93.6-93.6 | 100.12 | **no** | `a100_sxm_80gb-x672-hybrid` | 318.0 | 541.4-541.4 | 2.94 | yes | 5.895x | 0.173x | 0.029x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 827.5 | 44.0-44.0 | 94.03 | **no** | `a100_sxm_80gb-x337-hybrid` | 94.7 | 177.5-177.5 | 2.67 | yes | 8.735x | 0.248x | 0.028x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 597.6 | 23.6-23.6 | 126.73 | **no** | `a100_sxm_80gb-x672-hybrid` | 151.4 | 231.7-231.7 | 3.27 | yes | 3.947x | 0.102x | 0.026x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 222.0 | 35.7-35.7 | 31.09 | **no** | `a100_sxm_80gb-x337-hybrid` | 35.5 | 45.0-45.0 | 3.94 | yes | 6.259x | 0.794x | 0.127x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 156.6 | 22.5-22.5 | 34.78 | **no** | `a100_sxm_80gb-x672-hybrid` | 56.9 | 114.6-114.6 | 2.48 | yes | 2.752x | 0.196x | 0.071x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.023x to 0.127x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,200.2 | 179.1-179.1 | 117.24 | **no** | `b200_sxm-x90-nvl72-hybrid` | 1,055.5 | 4,316.9-4,316.9 | 1.22 | yes | 3.979x | 0.041x | 0.010x |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,465.8 | 703.6-703.6 | 38.84 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,054.0 | 4,302.0-4,302.0 | 1.23 | yes | 5.186x | 0.164x | 0.032x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,200.2 | 179.1-179.1 | 117.24 | **no** | `b200_sxm-x90-nvl72-hybrid` | 1,055.5 | 4,316.9-4,316.9 | 1.22 | yes | 3.979x | 0.041x | 0.010x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,465.8 | 703.6-703.6 | 38.84 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,054.0 | 4,302.0-4,302.0 | 1.23 | yes | 5.186x | 0.164x | 0.032x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,200.2 | 179.1-179.1 | 117.24 | **no** | `b200_sxm-x90-nvl72-hybrid` | 1,030.7 | 3,888.4-3,888.4 | 1.33 | yes | 4.075x | 0.046x | 0.011x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,465.8 | 703.6-703.6 | 38.84 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,028.8 | 3,871.7-3,871.7 | 1.33 | yes | 5.313x | 0.182x | 0.034x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,200.2 | 179.1-179.1 | 117.24 | **no** | `b200_sxm-x90-nvl72-hybrid` | 985.9 | 3,491.5-3,491.5 | 1.41 | yes | 4.260x | 0.051x | 0.012x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,465.8 | 703.6-703.6 | 38.84 | **no** | `b200_sxm-x87-nvl72-hybrid` | 982.9 | 3,467.5-3,467.5 | 1.42 | yes | 5.561x | 0.203x | 0.036x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,200.2 | 179.1-179.1 | 117.24 | **no** | `b200_sxm-x90-nvl72-hybrid` | 919.6 | 2,880.1-2,880.1 | 1.60 | yes | 4.567x | 0.062x | 0.014x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,465.8 | 703.6-703.6 | 38.84 | **no** | `b200_sxm-x87-nvl72-hybrid` | 923.7 | 2,884.4-2,884.4 | 1.60 | yes | 5.918x | 0.244x | 0.041x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,200.2 | 179.1-179.1 | 117.24 | **no** | `b200_sxm-x90-nvl72-hybrid` | 830.9 | 2,331.2-2,331.2 | 1.78 | yes | 5.055x | 0.077x | 0.015x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,330.9 | 851.8-851.8 | 31.29 | **no** | `b200_sxm-x231-nvl72-hybrid` | 933.4 | 2,952.9-2,952.9 | 1.58 | yes | 5.711x | 0.288x | 0.051x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,200.2 | 179.1-179.1 | 117.24 | **no** | `b200_sxm-x90-nvl72-hybrid` | 699.3 | 1,494.7-1,494.7 | 2.34 | yes | 6.006x | 0.120x | 0.020x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,327.8 | 847.0-847.0 | 31.45 | **no** | `b200_sxm-x347-nvl72-hybrid` | 887.6 | 2,647.3-2,647.3 | 1.68 | yes | 6.002x | 0.320x | 0.053x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 3,271.8 | 201.6-201.6 | 81.13 | **no** | `b200_sxm-x179-nvl72-hybrid` | 529.9 | 1,025.7-1,025.7 | 2.58 | yes | 6.174x | 0.197x | 0.032x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,450.9 | 427.1-427.1 | 52.11 | **no** | `b200_sxm-x347-nvl72-hybrid` | 666.9 | 1,485.1-1,485.1 | 2.25 | yes | 6.674x | 0.288x | 0.043x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 1,632.6 | 87.3-87.3 | 93.55 | **no** | `b200_sxm-x179-nvl72-hybrid` | 268.5 | 472.7-472.7 | 2.84 | yes | 6.081x | 0.185x | 0.030x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,433.4 | 108.5-108.5 | 112.14 | **no** | `b200_sxm-x347-nvl72-hybrid` | 358.1 | 738.3-738.3 | 2.43 | yes | 6.795x | 0.147x | 0.022x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 610.9 | 42.9-42.9 | 71.14 | **no** | `b200_sxm-x173-nvl72-hybrid` | 142.9 | 146.5-146.5 | 4.88 | yes | 4.275x | 0.293x | 0.069x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 769.7 | 93.5-93.5 | 41.16 | **no** | `b200_sxm-x347-nvl72-hybrid` | 175.3 | 207.6-207.6 | 4.22 | yes | 4.389x | 0.450x | 0.103x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.010x to 0.103x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 3,927.6 | 252.6-252.6 | 77.74 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 1,075.1-1,075.1 | 2.04 | yes | 8.965x | 0.235x | 0.026x |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,218.1 | 536.5-536.5 | 48.63 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 1,105.3-1,105.3 | 2.00 | yes | 11.776x | 0.485x | 0.041x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 3,927.6 | 252.6-252.6 | 77.74 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 1,075.1-1,075.1 | 2.04 | yes | 8.965x | 0.235x | 0.026x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,218.1 | 536.5-536.5 | 48.63 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 1,105.3-1,105.3 | 2.00 | yes | 11.776x | 0.485x | 0.041x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 3,927.6 | 252.6-252.6 | 77.74 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 1,075.1-1,075.1 | 2.04 | yes | 8.965x | 0.235x | 0.026x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,218.1 | 536.5-536.5 | 48.63 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 1,105.3-1,105.3 | 2.00 | yes | 11.776x | 0.485x | 0.041x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 3,927.6 | 252.6-252.6 | 77.74 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 1,075.1-1,075.1 | 2.04 | yes | 8.965x | 0.235x | 0.026x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,218.1 | 536.5-536.5 | 48.63 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 1,105.3-1,105.3 | 2.00 | yes | 11.776x | 0.485x | 0.041x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 3,927.6 | 252.6-252.6 | 77.74 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 1,075.1-1,075.1 | 2.04 | yes | 8.965x | 0.235x | 0.026x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,218.1 | 536.5-536.5 | 48.63 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 1,105.3-1,105.3 | 2.00 | yes | 11.776x | 0.485x | 0.041x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 3,927.6 | 252.6-252.6 | 77.74 | **no** | `a100_sxm_80gb-x244-hybrid` | 435.8 | 1,062.0-1,062.0 | 2.05 | yes | 9.012x | 0.238x | 0.026x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,099.5 | 620.5-620.5 | 41.09 | **no** | `a100_sxm_80gb-x448-hybrid` | 434.2 | 975.3-975.3 | 2.23 | yes | 11.746x | 0.636x | 0.054x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 3,817.9 | 252.3-252.3 | 75.66 | **no** | `a100_sxm_80gb-x244-hybrid` | 373.1 | 768.0-768.0 | 2.43 | yes | 10.233x | 0.329x | 0.032x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,094.9 | 617.0-617.0 | 41.29 | **no** | `a100_sxm_80gb-x672-hybrid` | 434.2 | 909.9-909.9 | 2.39 | yes | 11.735x | 0.678x | 0.058x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 2,963.7 | 93.3-93.3 | 158.83 | **no** | `a100_sxm_80gb-x335-hybrid` | 236.2 | 391.0-391.0 | 3.02 | yes | 12.547x | 0.239x | 0.019x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,968.0 | 309.4-309.4 | 64.13 | **no** | `a100_sxm_80gb-x672-hybrid` | 323.7 | 545.1-545.1 | 2.97 | yes | 12.259x | 0.568x | 0.046x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,328.4 | 45.5-45.5 | 146.11 | **no** | `a100_sxm_80gb-x337-hybrid` | 98.9 | 180.5-180.5 | 2.74 | yes | 13.435x | 0.252x | 0.019x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,899.7 | 78.2-78.2 | 121.39 | **no** | `a100_sxm_80gb-x672-hybrid` | 156.7 | 234.3-234.3 | 3.34 | yes | 12.123x | 0.334x | 0.028x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 375.9 | 39.9-39.9 | 47.09 | **no** | `a100_sxm_80gb-x337-hybrid` | 37.8 | 50.5-50.5 | 3.75 | yes | 9.931x | 0.790x | 0.080x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 721.4 | 83.1-83.1 | 43.38 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.9 | 117.1-117.1 | 2.56 | yes | 12.033x | 0.710x | 0.059x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.019x to 0.080x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 626.2-626.2 | 34.59 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,065.2 | 4,405.7-4,405.7 | 1.21 | yes | 4.067x | 0.142x | 0.035x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 5,400.3 | 1,222.6-1,222.6 | 22.09 | **no** | `b200_sxm-x347-nvl72-hybrid` | 1,060.6 | 4,308.0-4,308.0 | 1.23 | yes | 5.092x | 0.284x | 0.056x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 626.2-626.2 | 34.59 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,042.5 | 4,008.3-4,008.3 | 1.30 | yes | 4.155x | 0.156x | 0.038x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,360.5 | 1,288.9-1,288.9 | 20.80 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,050.0 | 4,069.0-4,069.0 | 1.29 | yes | 5.105x | 0.317x | 0.062x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 626.2-626.2 | 34.59 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,000.6 | 3,408.9-3,408.9 | 1.47 | yes | 4.330x | 0.184x | 0.042x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,360.5 | 1,288.9-1,288.9 | 20.80 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,010.6 | 3,475.6-3,475.6 | 1.45 | yes | 5.304x | 0.371x | 0.070x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 626.2-626.2 | 34.59 | **no** | `b200_sxm-x49-nvl72-tensor` | 927.9 | 2,669.7-2,669.7 | 1.74 | yes | 4.669x | 0.235x | 0.050x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,360.5 | 1,288.9-1,288.9 | 20.80 | **no** | `b200_sxm-x58-nvl72-tensor` | 941.7 | 2,727.3-2,727.3 | 1.73 | yes | 5.692x | 0.473x | 0.083x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 626.2-626.2 | 34.59 | **no** | `b200_sxm-x49-hybrid` | 830.0 | 2,245.2-2,245.2 | 1.85 | yes | 5.219x | 0.279x | 0.053x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5,350.7 | 1,315.4-1,315.4 | 20.34 | **no** | `b200_sxm-x87-nvl72-hybrid` | 922.5 | 2,881.7-2,881.7 | 1.60 | yes | 5.800x | 0.456x | 0.079x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,259.9 | 320.1-320.1 | 66.55 | **no** | `b200_sxm-x49-hybrid` | 701.7 | 1,545.7-1,545.7 | 2.27 | yes | 6.071x | 0.207x | 0.034x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,318.2 | 1,349.8-1,349.8 | 19.70 | **no** | `b200_sxm-x231-nvl72-hybrid` | 932.5 | 2,950.8-2,950.8 | 1.58 | yes | 5.703x | 0.457x | 0.080x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,186.0 | 650.0-650.0 | 32.20 | **no** | `b200_sxm-x173-nvl72-hybrid` | 815.7 | 2,259.0-2,259.0 | 1.81 | yes | 5.132x | 0.288x | 0.056x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,316.1 | 1,342.6-1,342.6 | 19.80 | **no** | `b200_sxm-x347-nvl72-hybrid` | 886.5 | 2,645.1-2,645.1 | 1.68 | yes | 5.997x | 0.508x | 0.085x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,426.8 | 324.5-324.5 | 52.79 | **no** | `b200_sxm-x173-nvl72-hybrid` | 519.7 | 1,013.7-1,013.7 | 2.56 | yes | 6.594x | 0.320x | 0.049x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,530.1 | 684.3-684.3 | 33.10 | **no** | `b200_sxm-x347-nvl72-hybrid` | 664.4 | 1,482.1-1,482.1 | 2.24 | yes | 6.818x | 0.462x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,455.9 | 152.6-152.6 | 47.69 | **no** | `b200_sxm-x173-nvl72-hybrid` | 262.6 | 450.0-450.0 | 2.92 | yes | 5.544x | 0.339x | 0.061x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,637.2 | 175.8-175.8 | 74.99 | **no** | `b200_sxm-x347-nvl72-hybrid` | 355.2 | 735.8-735.8 | 2.41 | yes | 7.424x | 0.239x | 0.032x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 416.4 | 107.5-107.5 | 19.37 | **no** | `b200_sxm-x173-nvl72-hybrid` | 139.3 | 145.7-145.7 | 4.78 | yes | 2.989x | 0.738x | 0.247x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 872.6 | 144.5-144.5 | 30.20 | **no** | `b200_sxm-x347-nvl72-hybrid` | 172.6 | 206.8-206.8 | 4.17 | yes | 5.054x | 0.699x | 0.138x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.032x to 0.247x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 435.5-435.5 | 46.21 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 1,177.7-1,177.7 | 1.91 | yes | 8.927x | 0.370x | 0.041x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 5,167.1 | 863.5-863.5 | 29.92 | **no** | `a100_sxm_80gb-x672-hybrid` | 433.5 | 909.2-909.2 | 2.38 | yes | 11.921x | 0.950x | 0.080x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 435.5-435.5 | 46.21 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 1,177.7-1,177.7 | 1.91 | yes | 8.927x | 0.370x | 0.041x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.6 | 965.8-965.8 | 26.32 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.355x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 435.5-435.5 | 46.21 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 1,177.7-1,177.7 | 1.91 | yes | 8.927x | 0.370x | 0.041x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.6 | 965.8-965.8 | 26.32 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.355x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 435.5-435.5 | 46.21 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 1,177.7-1,177.7 | 1.91 | yes | 8.927x | 0.370x | 0.041x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.6 | 965.8-965.8 | 26.32 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.355x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 435.5-435.5 | 46.21 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 1,177.7-1,177.7 | 1.91 | yes | 8.927x | 0.370x | 0.041x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.6 | 965.8-965.8 | 26.32 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.355x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 435.5-435.5 | 46.21 | **no** | `a100_sxm_80gb-x136-hybrid` | 396.2 | 895.7-895.7 | 2.21 | yes | 10.159x | 0.486x | 0.048x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,062.2 | 991.9-991.9 | 25.52 | **no** | `a100_sxm_80gb-x448-hybrid` | 433.5 | 974.5-974.5 | 2.22 | yes | 11.679x | 1.018x | 0.087x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 3,937.8 | 475.0-475.0 | 41.45 | **no** | `a100_sxm_80gb-x272-hybrid` | 382.0 | 795.7-795.7 | 2.40 | yes | 10.307x | 0.597x | 0.058x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,059.0 | 986.5-986.5 | 25.64 | **no** | `a100_sxm_80gb-x672-hybrid` | 433.5 | 909.2-909.2 | 2.38 | yes | 11.671x | 1.085x | 0.093x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,960.5 | 235.6-235.6 | 62.83 | **no** | `a100_sxm_80gb-x335-hybrid` | 234.9 | 390.3-390.3 | 3.01 | yes | 12.601x | 0.604x | 0.048x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,982.4 | 497.6-497.6 | 40.02 | **no** | `a100_sxm_80gb-x672-hybrid` | 322.5 | 544.3-544.3 | 2.96 | yes | 12.349x | 0.914x | 0.074x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,129.9 | 110.6-110.6 | 51.07 | **no** | `a100_sxm_80gb-x335-hybrid` | 97.7 | 179.3-179.3 | 2.72 | yes | 11.570x | 0.617x | 0.053x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,977.6 | 127.0-127.0 | 77.84 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.6 | 233.7-233.7 | 3.33 | yes | 12.710x | 0.543x | 0.043x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 401.3 | 73.3-73.3 | 27.37 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.2 | 48.4-48.4 | 3.85 | yes | 10.774x | 1.515x | 0.141x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 602.7 | 104.5-104.5 | 28.84 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.3 | 116.6-116.6 | 2.54 | yes | 10.162x | 0.896x | 0.088x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.041x to 0.141x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4,034.1 | 535.2-535.2 | 37.69 | **no** | `b200_sxm-x57-nvl72-tensor` | 1,070.0 | 4,453.1-4,453.1 | 1.20 | yes | 3.770x | 0.120x | 0.032x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 5,108.5 | 1,195.6-1,195.6 | 21.36 | **no** | `b200_sxm-x347-nvl72-hybrid` | 1,060.1 | 4,306.3-4,306.3 | 1.23 | yes | 4.819x | 0.278x | 0.058x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4,034.1 | 535.2-535.2 | 37.69 | **no** | `b200_sxm-x57-nvl72-tensor` | 1,048.2 | 4,059.4-4,059.4 | 1.29 | yes | 3.849x | 0.132x | 0.034x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,815.0 | 848.1-848.1 | 28.39 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,071.3 | 4,468.0-4,468.0 | 1.20 | yes | 4.495x | 0.190x | 0.042x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4,034.1 | 535.2-535.2 | 37.69 | **no** | `b200_sxm-x57-nvl72-tensor` | 1,007.6 | 3,463.6-3,463.6 | 1.45 | yes | 4.004x | 0.155x | 0.039x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,815.0 | 848.1-848.1 | 28.39 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,050.4 | 4,053.0-4,053.0 | 1.30 | yes | 4.584x | 0.209x | 0.046x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4,034.1 | 535.2-535.2 | 37.69 | **no** | `b200_sxm-x57-nvl72-tensor` | 936.7 | 2,714.9-2,714.9 | 1.73 | yes | 4.306x | 0.197x | 0.046x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,815.0 | 848.1-848.1 | 28.39 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,012.0 | 3,622.1-3,622.1 | 1.40 | yes | 4.758x | 0.234x | 0.049x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4,034.1 | 535.2-535.2 | 37.69 | **no** | `b200_sxm-x57-hybrid` | 845.3 | 2,364.7-2,364.7 | 1.79 | yes | 4.772x | 0.226x | 0.047x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,815.0 | 848.1-848.1 | 28.39 | **no** | `b200_sxm-x144-nvl72-hybrid` | 958.0 | 3,235.6-3,235.6 | 1.48 | yes | 5.026x | 0.262x | 0.052x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x113` | 3,831.6 | 514.8-514.8 | 37.22 | **no** | `b200_sxm-x58-hybrid` | 727.4 | 1,746.6-1,746.6 | 2.08 | yes | 5.267x | 0.295x | 0.056x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,641.4 | 2,375.6-2,375.6 | 9.77 | **no** | `b200_sxm-x347-nvl72-hybrid` | 957.9 | 3,145.8-3,145.8 | 1.52 | yes | 4.846x | 0.755x | 0.156x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,809.2 | 634.3-634.3 | 30.02 | **no** | `b200_sxm-x173-nvl72-hybrid` | 808.5 | 2,246.3-2,246.3 | 1.80 | yes | 4.712x | 0.282x | 0.060x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,491.2 | 1,298.6-1,298.6 | 17.29 | **no** | `b200_sxm-x347-nvl72-hybrid` | 882.2 | 2,636.5-2,636.5 | 1.67 | yes | 5.091x | 0.493x | 0.097x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,746.3 | 312.8-312.8 | 43.91 | **no** | `b200_sxm-x173-nvl72-hybrid` | 508.1 | 1,002.9-1,002.9 | 2.53 | yes | 5.405x | 0.312x | 0.058x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,068.7 | 654.1-654.1 | 23.46 | **no** | `b200_sxm-x347-nvl72-hybrid` | 654.9 | 1,470.6-1,470.6 | 2.23 | yes | 4.686x | 0.445x | 0.095x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,021.5 | 142.5-142.5 | 35.86 | **no** | `b200_sxm-x173-nvl72-hybrid` | 251.0 | 442.9-442.9 | 2.83 | yes | 4.069x | 0.322x | 0.079x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,249.0 | 169.0-169.0 | 36.96 | **no** | `b200_sxm-x347-nvl72-hybrid` | 344.5 | 726.0-726.0 | 2.37 | yes | 3.625x | 0.233x | 0.064x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 348.1 | 72.0-72.0 | 24.16 | **no** | `b200_sxm-x173-nvl72-hybrid` | 126.9 | 142.8-142.8 | 4.44 | yes | 2.743x | 0.505x | 0.184x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 359.6 | 44.8-44.8 | 40.12 | **no** | `b200_sxm-x347-nvl72-hybrid` | 162.8 | 203.9-203.9 | 3.99 | yes | 2.209x | 0.220x | 0.100x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.032x to 0.184x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 3,724.2 | 734.3-734.3 | 25.36 | **no** | `a100_sxm_80gb-x155-hybrid` | 440.0 | 1,135.5-1,135.5 | 1.94 | yes | 8.464x | 0.647x | 0.076x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | 4,953.7 | 1,613.1-1,613.1 | 15.35 | **no** | `a100_sxm_80gb-x616-hybrid` | 430.7 | 921.5-921.5 | 2.34 | yes | 11.500x | 1.750x | 0.152x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 3,724.2 | 734.3-734.3 | 25.36 | **no** | `a100_sxm_80gb-x155-hybrid` | 440.0 | 1,135.5-1,135.5 | 1.94 | yes | 8.464x | 0.647x | 0.076x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 4,243.6 | 1,001.5-1,001.5 | 21.19 | **no** | `a100_sxm_80gb-x448-hybrid` | 430.7 | 971.5-971.5 | 2.22 | yes | 9.852x | 1.031x | 0.105x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 3,724.2 | 734.3-734.3 | 25.36 | **no** | `a100_sxm_80gb-x155-hybrid` | 440.0 | 1,135.5-1,135.5 | 1.94 | yes | 8.464x | 0.647x | 0.076x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 4,243.6 | 1,001.5-1,001.5 | 21.19 | **no** | `a100_sxm_80gb-x448-hybrid` | 430.7 | 971.5-971.5 | 2.22 | yes | 9.852x | 1.031x | 0.105x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 3,724.2 | 734.3-734.3 | 25.36 | **no** | `a100_sxm_80gb-x155-hybrid` | 440.0 | 1,135.5-1,135.5 | 1.94 | yes | 8.464x | 0.647x | 0.076x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 4,243.6 | 1,001.5-1,001.5 | 21.19 | **no** | `a100_sxm_80gb-x448-hybrid` | 430.7 | 971.5-971.5 | 2.22 | yes | 9.852x | 1.031x | 0.105x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 3,724.2 | 734.3-734.3 | 25.36 | **no** | `a100_sxm_80gb-x155-hybrid` | 440.0 | 1,135.5-1,135.5 | 1.94 | yes | 8.464x | 0.647x | 0.076x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,223.1 | 700.9-700.9 | 30.13 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 9.804x | 0.773x | 0.079x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156` | 3,695.0 | 388.2-388.2 | 47.59 | **no** | `a100_sxm_80gb-x154-hybrid` | 398.9 | 917.5-917.5 | 2.17 | yes | 9.262x | 0.423x | 0.046x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,053.8 | 368.4-368.4 | 55.02 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 9.411x | 0.406x | 0.043x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 3,508.8 | 464.0-464.0 | 37.81 | **no** | `a100_sxm_80gb-x272-hybrid` | 378.1 | 791.8-791.8 | 2.39 | yes | 9.280x | 0.586x | 0.063x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,595.6 | 365.4-365.4 | 49.20 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 906.6-906.6 | 2.38 | yes | 8.347x | 0.403x | 0.048x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,310.6 | 227.6-227.6 | 50.76 | **no** | `a100_sxm_80gb-x335-hybrid` | 230.1 | 387.4-387.4 | 2.97 | yes | 10.041x | 0.588x | 0.059x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,900.4 | 94.0-94.0 | 101.06 | **no** | `a100_sxm_80gb-x672-hybrid` | 318.0 | 541.4-541.4 | 2.94 | yes | 5.977x | 0.174x | 0.029x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 983.0 | 85.9-85.9 | 57.23 | **no** | `a100_sxm_80gb-x335-hybrid` | 94.4 | 177.0-177.0 | 2.67 | yes | 10.415x | 0.485x | 0.047x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 601.7 | 23.7-23.7 | 127.03 | **no** | `a100_sxm_80gb-x672-hybrid` | 151.4 | 231.7-231.7 | 3.27 | yes | 3.974x | 0.102x | 0.026x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340` | 325.4 | 39.4-39.4 | 41.32 | **no** | `a100_sxm_80gb-x335-hybrid` | 35.4 | 44.2-44.2 | 4.00 | yes | 9.200x | 0.891x | 0.097x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 157.6 | 22.9-22.9 | 34.39 | **no** | `a100_sxm_80gb-x672-hybrid` | 56.9 | 114.6-114.6 | 2.48 | yes | 2.768x | 0.200x | 0.072x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.026x to 0.152x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,404.8 | 334.5-334.5 | 65.84 | **no** | `b200_sxm-x47-nvl72-tensor` | 1,063.7 | 4,391.1-4,391.1 | 1.21 | yes | 4.141x | 0.076x | 0.018x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,513.7 | 1,305.1-1,305.1 | 21.12 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,071.4 | 4,461.2-4,461.2 | 1.20 | yes | 5.147x | 0.293x | 0.057x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,404.8 | 334.5-334.5 | 65.84 | **no** | `b200_sxm-x47-nvl72-tensor` | 1,040.8 | 3,992.3-3,992.3 | 1.30 | yes | 4.232x | 0.084x | 0.020x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,513.7 | 1,305.1-1,305.1 | 21.12 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,050.3 | 4,070.0-4,070.0 | 1.29 | yes | 5.250x | 0.321x | 0.061x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,404.8 | 334.5-334.5 | 65.84 | **no** | `b200_sxm-x47-nvl72-tensor` | 998.4 | 3,391.7-3,391.7 | 1.47 | yes | 4.412x | 0.099x | 0.022x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,513.7 | 1,305.1-1,305.1 | 21.12 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,011.2 | 3,477.2-3,477.2 | 1.45 | yes | 5.453x | 0.375x | 0.069x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,404.8 | 334.5-334.5 | 65.84 | **no** | `b200_sxm-x47-hybrid` | 929.0 | 2,858.9-2,858.9 | 1.62 | yes | 4.742x | 0.117x | 0.025x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,513.7 | 1,305.1-1,305.1 | 21.12 | **no** | `b200_sxm-x58-nvl72-tensor` | 942.6 | 2,729.2-2,729.2 | 1.73 | yes | 5.849x | 0.478x | 0.082x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,404.8 | 334.5-334.5 | 65.84 | **no** | `b200_sxm-x47-hybrid` | 838.8 | 2,251.9-2,251.9 | 1.86 | yes | 5.251x | 0.149x | 0.028x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5,501.7 | 1,332.2-1,332.2 | 20.65 | **no** | `b200_sxm-x87-nvl72-hybrid` | 923.7 | 2,884.4-2,884.4 | 1.60 | yes | 5.956x | 0.462x | 0.078x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,404.8 | 334.5-334.5 | 65.84 | **no** | `b200_sxm-x47-hybrid` | 705.2 | 1,561.2-1,561.2 | 2.26 | yes | 6.246x | 0.214x | 0.034x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,464.9 | 1,367.2-1,367.2 | 19.99 | **no** | `b200_sxm-x231-nvl72-hybrid` | 933.4 | 2,952.9-2,952.9 | 1.58 | yes | 5.855x | 0.463x | 0.079x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 4,397.6 | 335.7-335.7 | 65.49 | **no** | `b200_sxm-x83-nvl72-hybrid` | 682.6 | 1,420.9-1,420.9 | 2.40 | yes | 6.443x | 0.236x | 0.037x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,463.3 | 1,359.9-1,359.9 | 20.09 | **no** | `b200_sxm-x347-nvl72-hybrid` | 887.6 | 2,647.3-2,647.3 | 1.68 | yes | 6.155x | 0.514x | 0.083x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,658.7 | 327.7-327.7 | 55.82 | **no** | `b200_sxm-x173-nvl72-hybrid` | 522.7 | 1,016.5-1,016.5 | 2.57 | yes | 6.999x | 0.322x | 0.046x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,837.3 | 693.3-693.3 | 34.89 | **no** | `b200_sxm-x347-nvl72-hybrid` | 666.9 | 1,485.1-1,485.1 | 2.25 | yes | 7.253x | 0.467x | 0.064x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,634.9 | 155.5-155.5 | 52.56 | **no** | `b200_sxm-x173-nvl72-hybrid` | 265.7 | 451.9-451.9 | 2.94 | yes | 6.152x | 0.344x | 0.056x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,988.1 | 177.8-177.8 | 84.02 | **no** | `b200_sxm-x347-nvl72-hybrid` | 358.1 | 738.3-738.3 | 2.43 | yes | 8.344x | 0.241x | 0.029x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 477.4 | 113.5-113.5 | 21.03 | **no** | `b200_sxm-x173-nvl72-hybrid` | 142.9 | 146.5-146.5 | 4.88 | yes | 3.341x | 0.775x | 0.232x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,022.9 | 149.5-149.5 | 34.22 | **no** | `b200_sxm-x347-nvl72-hybrid` | 175.3 | 207.6-207.6 | 4.22 | yes | 5.834x | 0.720x | 0.123x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.018x to 0.232x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,114.4 | 475.3-475.3 | 43.28 | **no** | `a100_sxm_80gb-x126-hybrid` | 449.6 | 1,173.4-1,173.4 | 1.92 | yes | 9.151x | 0.405x | 0.044x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,340.1 | 978.0-978.0 | 27.30 | **no** | `a100_sxm_80gb-x168-hybrid` | 448.5 | 1,154.9-1,154.9 | 1.94 | yes | 11.906x | 0.847x | 0.071x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,114.4 | 475.3-475.3 | 43.28 | **no** | `a100_sxm_80gb-x126-hybrid` | 449.6 | 1,173.4-1,173.4 | 1.92 | yes | 9.151x | 0.405x | 0.044x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,340.1 | 978.0-978.0 | 27.30 | **no** | `a100_sxm_80gb-x168-hybrid` | 448.5 | 1,154.9-1,154.9 | 1.94 | yes | 11.906x | 0.847x | 0.071x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,114.4 | 475.3-475.3 | 43.28 | **no** | `a100_sxm_80gb-x126-hybrid` | 449.6 | 1,173.4-1,173.4 | 1.92 | yes | 9.151x | 0.405x | 0.044x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,340.1 | 978.0-978.0 | 27.30 | **no** | `a100_sxm_80gb-x168-hybrid` | 448.5 | 1,154.9-1,154.9 | 1.94 | yes | 11.906x | 0.847x | 0.071x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,114.4 | 475.3-475.3 | 43.28 | **no** | `a100_sxm_80gb-x126-hybrid` | 449.6 | 1,173.4-1,173.4 | 1.92 | yes | 9.151x | 0.405x | 0.044x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,340.1 | 978.0-978.0 | 27.30 | **no** | `a100_sxm_80gb-x168-hybrid` | 448.5 | 1,154.9-1,154.9 | 1.94 | yes | 11.906x | 0.847x | 0.071x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,114.4 | 475.3-475.3 | 43.28 | **no** | `a100_sxm_80gb-x126-hybrid` | 449.6 | 1,173.4-1,173.4 | 1.92 | yes | 9.151x | 0.405x | 0.044x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,340.1 | 978.0-978.0 | 27.30 | **no** | `a100_sxm_80gb-x168-hybrid` | 448.5 | 1,154.9-1,154.9 | 1.94 | yes | 11.906x | 0.847x | 0.071x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,114.4 | 475.3-475.3 | 43.28 | **no** | `a100_sxm_80gb-x126-hybrid` | 389.1 | 871.6-871.6 | 2.23 | yes | 10.574x | 0.545x | 0.052x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,313.8 | 1,004.7-1,004.7 | 26.44 | **no** | `a100_sxm_80gb-x448-hybrid` | 434.2 | 975.3-975.3 | 2.23 | yes | 12.239x | 1.030x | 0.084x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,059.2 | 477.9-477.9 | 42.47 | **no** | `a100_sxm_80gb-x272-hybrid` | 383.1 | 796.7-796.7 | 2.40 | yes | 10.596x | 0.600x | 0.057x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,310.5 | 999.2-999.2 | 26.57 | **no** | `a100_sxm_80gb-x672-hybrid` | 434.2 | 909.9-909.9 | 2.39 | yes | 12.232x | 1.098x | 0.090x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,197.7 | 237.8-237.8 | 67.25 | **no** | `a100_sxm_80gb-x335-hybrid` | 236.2 | 391.0-391.0 | 3.02 | yes | 13.538x | 0.608x | 0.045x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,417.5 | 503.9-503.9 | 43.83 | **no** | `a100_sxm_80gb-x672-hybrid` | 323.7 | 545.1-545.1 | 2.97 | yes | 13.647x | 0.924x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,271.0 | 112.6-112.6 | 56.44 | **no** | `a100_sxm_80gb-x335-hybrid` | 98.5 | 180.0-180.0 | 2.74 | yes | 12.899x | 0.626x | 0.049x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,403.2 | 128.4-128.4 | 93.61 | **no** | `a100_sxm_80gb-x672-hybrid` | 156.7 | 234.3-234.3 | 3.34 | yes | 15.336x | 0.548x | 0.036x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 424.2 | 82.8-82.8 | 25.61 | **no** | `a100_sxm_80gb-x272-hybrid` | 35.1 | 44.8-44.8 | 3.92 | yes | 12.080x | 1.850x | 0.153x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 759.1 | 107.8-107.8 | 35.21 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.9 | 117.1-117.1 | 2.56 | yes | 12.662x | 0.921x | 0.073x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.036x to 0.153x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 626.2-626.2 | 34.59 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,065.2 | 4,405.7-4,405.7 | 1.21 | yes | 4.067x | 0.142x | 0.035x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,360.5 | 1,288.9-1,288.9 | 20.80 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,071.2 | 4,460.6-4,460.6 | 1.20 | yes | 5.004x | 0.289x | 0.058x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 626.2-626.2 | 34.59 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,042.5 | 4,008.3-4,008.3 | 1.30 | yes | 4.155x | 0.156x | 0.038x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,360.5 | 1,288.9-1,288.9 | 20.80 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,050.0 | 4,069.0-4,069.0 | 1.29 | yes | 5.105x | 0.317x | 0.062x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 626.2-626.2 | 34.59 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,000.6 | 3,408.9-3,408.9 | 1.47 | yes | 4.330x | 0.184x | 0.042x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,360.5 | 1,288.9-1,288.9 | 20.80 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,010.6 | 3,475.6-3,475.6 | 1.45 | yes | 5.304x | 0.371x | 0.070x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 626.2-626.2 | 34.59 | **no** | `b200_sxm-x49-nvl72-tensor` | 927.9 | 2,669.7-2,669.7 | 1.74 | yes | 4.669x | 0.235x | 0.050x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,360.5 | 1,288.9-1,288.9 | 20.80 | **no** | `b200_sxm-x58-nvl72-tensor` | 941.7 | 2,727.3-2,727.3 | 1.73 | yes | 5.692x | 0.473x | 0.083x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 626.2-626.2 | 34.59 | **no** | `b200_sxm-x49-hybrid` | 830.0 | 2,245.2-2,245.2 | 1.85 | yes | 5.219x | 0.279x | 0.053x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5,350.8 | 1,315.5-1,315.5 | 20.34 | **no** | `b200_sxm-x87-nvl72-hybrid` | 922.5 | 2,881.7-2,881.7 | 1.60 | yes | 5.801x | 0.456x | 0.079x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,259.9 | 320.1-320.1 | 66.55 | **no** | `b200_sxm-x49-hybrid` | 701.7 | 1,545.7-1,545.7 | 2.27 | yes | 6.071x | 0.207x | 0.034x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,318.2 | 1,349.8-1,349.8 | 19.70 | **no** | `b200_sxm-x231-nvl72-hybrid` | 932.5 | 2,950.8-2,950.8 | 1.58 | yes | 5.703x | 0.457x | 0.080x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,186.0 | 650.0-650.0 | 32.20 | **no** | `b200_sxm-x173-nvl72-hybrid` | 815.7 | 2,259.1-2,259.1 | 1.81 | yes | 5.132x | 0.288x | 0.056x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,316.2 | 1,342.6-1,342.6 | 19.80 | **no** | `b200_sxm-x347-nvl72-hybrid` | 886.5 | 2,645.1-2,645.1 | 1.68 | yes | 5.997x | 0.508x | 0.085x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,426.8 | 324.5-324.5 | 52.79 | **no** | `b200_sxm-x173-nvl72-hybrid` | 519.7 | 1,013.7-1,013.7 | 2.56 | yes | 6.594x | 0.320x | 0.049x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,530.2 | 684.3-684.3 | 33.10 | **no** | `b200_sxm-x347-nvl72-hybrid` | 664.4 | 1,482.1-1,482.1 | 2.24 | yes | 6.818x | 0.462x | 0.068x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,455.9 | 152.6-152.6 | 47.69 | **no** | `b200_sxm-x173-nvl72-hybrid` | 262.6 | 450.0-450.0 | 2.92 | yes | 5.544x | 0.339x | 0.061x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,637.2 | 175.8-175.8 | 74.99 | **no** | `b200_sxm-x347-nvl72-hybrid` | 355.2 | 735.8-735.8 | 2.41 | yes | 7.424x | 0.239x | 0.032x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 416.4 | 107.5-107.5 | 19.37 | **no** | `b200_sxm-x173-nvl72-hybrid` | 139.3 | 145.7-145.7 | 4.78 | yes | 2.989x | 0.738x | 0.247x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 872.6 | 144.5-144.5 | 30.20 | **no** | `b200_sxm-x347-nvl72-hybrid` | 172.6 | 206.8-206.8 | 4.17 | yes | 5.054x | 0.699x | 0.138x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.032x to 0.247x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 435.5-435.5 | 46.21 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 1,177.7-1,177.7 | 1.91 | yes | 8.927x | 0.370x | 0.041x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.7 | 965.9-965.9 | 26.32 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.356x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 435.5-435.5 | 46.21 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 1,177.7-1,177.7 | 1.91 | yes | 8.927x | 0.370x | 0.041x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.7 | 965.9-965.9 | 26.32 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.356x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 435.5-435.5 | 46.21 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 1,177.7-1,177.7 | 1.91 | yes | 8.927x | 0.370x | 0.041x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.7 | 965.9-965.9 | 26.32 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.356x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 435.5-435.5 | 46.21 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 1,177.7-1,177.7 | 1.91 | yes | 8.927x | 0.370x | 0.041x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.7 | 965.9-965.9 | 26.32 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.356x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 435.5-435.5 | 46.21 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 1,177.7-1,177.7 | 1.91 | yes | 8.927x | 0.370x | 0.041x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.7 | 965.9-965.9 | 26.32 | **no** | `a100_sxm_80gb-x168-hybrid` | 447.8 | 1,153.8-1,153.8 | 1.94 | yes | 11.356x | 0.837x | 0.074x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 435.5-435.5 | 46.21 | **no** | `a100_sxm_80gb-x136-hybrid` | 396.2 | 895.7-895.7 | 2.21 | yes | 10.159x | 0.486x | 0.048x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,062.4 | 991.9-991.9 | 25.52 | **no** | `a100_sxm_80gb-x448-hybrid` | 433.5 | 974.5-974.5 | 2.22 | yes | 11.679x | 1.018x | 0.087x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 3,937.8 | 475.0-475.0 | 41.45 | **no** | `a100_sxm_80gb-x272-hybrid` | 382.0 | 795.7-795.7 | 2.40 | yes | 10.307x | 0.597x | 0.058x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,059.2 | 986.5-986.5 | 25.64 | **no** | `a100_sxm_80gb-x672-hybrid` | 433.5 | 909.2-909.2 | 2.38 | yes | 11.672x | 1.085x | 0.093x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,960.5 | 235.6-235.6 | 62.83 | **no** | `a100_sxm_80gb-x335-hybrid` | 234.9 | 390.3-390.3 | 3.01 | yes | 12.601x | 0.604x | 0.048x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,982.8 | 497.6-497.6 | 40.02 | **no** | `a100_sxm_80gb-x672-hybrid` | 322.5 | 544.3-544.3 | 2.96 | yes | 12.350x | 0.914x | 0.074x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,129.9 | 110.6-110.6 | 51.07 | **no** | `a100_sxm_80gb-x335-hybrid` | 97.7 | 179.3-179.3 | 2.72 | yes | 11.570x | 0.617x | 0.053x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,978.0 | 127.0-127.0 | 77.86 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.6 | 233.7-233.7 | 3.33 | yes | 12.712x | 0.543x | 0.043x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 401.3 | 73.3-73.3 | 27.37 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.2 | 48.4-48.4 | 3.85 | yes | 10.774x | 1.515x | 0.141x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 602.8 | 104.5-104.5 | 28.84 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.3 | 116.6-116.6 | 2.54 | yes | 10.165x | 0.896x | 0.088x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.041x to 0.141x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-kimi-k3`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | 927.8 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 486.8 | not applicable | -- | -- | 1.906x | -- | -- |
| Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 1,776.9 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 487.2 | not applicable | -- | -- | 3.647x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 862.2 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 487.2 | not applicable | -- | -- | 1.770x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,755.0 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 480.3 | not applicable | -- | -- | 3.654x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 862.2 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 480.4 | not applicable | -- | -- | 1.795x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,755.0 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 480.3 | not applicable | -- | -- | 3.654x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 862.2 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 455.1 | not applicable | -- | -- | 1.895x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,755.0 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 476.9 | not applicable | -- | -- | 3.680x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 823.8 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 412.7 | not applicable | -- | -- | 1.996x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,755.0 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 451.6 | not applicable | -- | -- | 3.886x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 717.4 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 350.3 | not applicable | -- | -- | 2.048x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,529.9 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 408.8 | not applicable | -- | -- | 3.742x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 530.9 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 274.2 | not applicable | -- | -- | 1.936x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,261.2 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 345.5 | not applicable | -- | -- | 3.651x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 174.4 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 140.2 | not applicable | -- | -- | 1.244x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 508.9 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 193.9 | not applicable | -- | -- | 2.625x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 45.8 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 63.2 | not applicable | -- | -- | 0.724x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 144.4 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 88.0 | not applicable | -- | -- | 1.641x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 11.5 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 25.1 | not applicable | -- | -- | 0.457x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 36.9 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 38.7 | not applicable | -- | -- | 0.954x | -- | -- |

### `n6_vs_a100-kimi-k3`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x398` | 687.6 | not applicable | -- | -- | `a100_sxm_80gb-x393-hybrid` | 127.8 | not applicable | -- | -- | 5.380x | -- | -- |
| Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x10` | 1,698.4 | not applicable | -- | -- | `a100_sxm_80gb-x560-hybrid` | 129.9 | not applicable | -- | -- | 13.078x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 564.8 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 127.9 | not applicable | -- | -- | 4.417x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,397.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 127.9 | not applicable | -- | -- | 10.924x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 564.8 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 127.9 | not applicable | -- | -- | 4.417x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,397.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 127.9 | not applicable | -- | -- | 10.924x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 549.7 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 125.8 | not applicable | -- | -- | 4.371x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,397.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 127.9 | not applicable | -- | -- | 10.924x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 484.6 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 111.1 | not applicable | -- | -- | 4.361x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,397.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 127.9 | not applicable | -- | -- | 10.924x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 335.1 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 93.2 | not applicable | -- | -- | 3.596x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,158.2 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 118.9 | not applicable | -- | -- | 9.745x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 199.1 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 74.0 | not applicable | -- | -- | 2.691x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 847.6 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 100.1 | not applicable | -- | -- | 8.468x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 55.1 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 41.7 | not applicable | -- | -- | 1.322x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 301.7 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 63.3 | not applicable | -- | -- | 4.765x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 14.0 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 17.2 | not applicable | -- | -- | 0.812x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 81.8 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 33.8 | not applicable | -- | -- | 2.420x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 3.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 6.7 | not applicable | -- | -- | 0.523x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x22` | 20.8 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 13.0 | not applicable | -- | -- | 1.595x | -- | -- |

### `n5_vs_b200-kimi-k3-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x383` | 589.0 | not applicable | -- | -- | `b200_sxm-x195-nvl72-hybrid` | 478.5 | not applicable | -- | -- | 1.231x | -- | -- |
| Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | 1,528.2 | not applicable | -- | -- | `b200_sxm-x520-nvl72-hybrid` | 472.0 | not applicable | -- | -- | 3.238x | -- | -- |
| Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,160.8 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | not applicable | -- | -- | 2.563x | -- | -- |
| Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,160.8 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | not applicable | -- | -- | 2.563x | -- | -- |
| Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,160.8 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | not applicable | -- | -- | 2.563x | -- | -- |
| Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,160.8 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | not applicable | -- | -- | 2.563x | -- | -- |
| Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,142.7 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 447.0 | not applicable | -- | -- | 2.557x | -- | -- |
| Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,133.2 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 405.2 | not applicable | -- | -- | 2.797x | -- | -- |
| Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 517.3 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 272.8 | not applicable | -- | -- | 1.896x | -- | -- |
| Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 151.8 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 145.3 | not applicable | -- | -- | 1.045x | -- | -- |
| Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x68` | 39.3 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 49.4 | not applicable | -- | -- | 0.795x | -- | -- |

### `n6_vs_a100-kimi-k3-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x399` | 379.3 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 126.0 | not applicable | -- | -- | 3.012x | -- | -- |
| Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x23` | 1,329.0 | not applicable | -- | -- | `a100_sxm_80gb-x1287-hybrid` | 125.9 | not applicable | -- | -- | 10.557x | -- | -- |
| Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 989.3 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 117.7 | not applicable | -- | -- | 8.404x | -- | -- |
| Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 989.3 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 117.7 | not applicable | -- | -- | 8.404x | -- | -- |
| Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 989.3 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 117.7 | not applicable | -- | -- | 8.404x | -- | -- |
| Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 989.3 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 117.7 | not applicable | -- | -- | 8.404x | -- | -- |
| Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 881.4 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 117.7 | not applicable | -- | -- | 7.488x | -- | -- |
| Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 723.6 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 117.7 | not applicable | -- | -- | 6.148x | -- | -- |
| Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 312.0 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 91.5 | not applicable | -- | -- | 3.408x | -- | -- |
| Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 87.5 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 59.8 | not applicable | -- | -- | 1.464x | -- | -- |
| Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 22.4 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 29.9 | not applicable | -- | -- | 0.748x | -- | -- |

### `n5_vs_b200-kimi-k3-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,365.7 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 488.3 | not applicable | -- | -- | 2.797x | -- | -- |
| Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,158.1 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 488.6 | not applicable | -- | -- | 4.417x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,365.7 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 488.3 | not applicable | -- | -- | 2.797x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,158.1 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 488.6 | not applicable | -- | -- | 4.417x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,365.7 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 481.9 | not applicable | -- | -- | 2.834x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,158.1 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 482.2 | not applicable | -- | -- | 4.475x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,365.7 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 458.1 | not applicable | -- | -- | 2.981x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,158.1 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 458.5 | not applicable | -- | -- | 4.707x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,365.7 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 417.8 | not applicable | -- | -- | 3.269x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,158.1 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 418.3 | not applicable | -- | -- | 5.159x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,365.7 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 357.9 | not applicable | -- | -- | 3.816x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,144.4 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 399.0 | not applicable | -- | -- | 5.374x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,207.4 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 283.7 | not applicable | -- | -- | 4.255x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,868.6 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 331.7 | not applicable | -- | -- | 5.633x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 688.8 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 150.9 | not applicable | -- | -- | 4.565x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,089.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 182.1 | not applicable | -- | -- | 5.978x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 217.0 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 72.7 | not applicable | -- | -- | 2.985x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 369.4 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 87.1 | not applicable | -- | -- | 4.241x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 57.1 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 35.1 | not applicable | -- | -- | 1.629x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 99.2 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 41.9 | not applicable | -- | -- | 2.366x | -- | -- |

### `n6_vs_a100-kimi-k3-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 920.8 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 128.3 | not applicable | -- | -- | 7.174x | -- | -- |
| Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,855.5 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 129.6 | not applicable | -- | -- | 14.319x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 920.8 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 128.3 | not applicable | -- | -- | 7.174x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,855.5 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 129.6 | not applicable | -- | -- | 14.319x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 920.8 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 128.3 | not applicable | -- | -- | 7.174x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,855.5 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 129.6 | not applicable | -- | -- | 14.319x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 920.8 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 126.3 | not applicable | -- | -- | 7.292x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,855.5 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 129.6 | not applicable | -- | -- | 14.319x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 920.8 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 111.9 | not applicable | -- | -- | 8.227x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,847.0 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 123.1 | not applicable | -- | -- | 15.009x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 812.1 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 94.3 | not applicable | -- | -- | 8.611x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,644.1 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 106.1 | not applicable | -- | -- | 15.501x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 663.4 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 75.4 | not applicable | -- | -- | 8.797x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,324.8 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 88.9 | not applicable | -- | -- | 14.895x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 245.9 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 43.6 | not applicable | -- | -- | 5.639x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554.6 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 53.0 | not applicable | -- | -- | 10.456x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 66.4 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 18.5 | not applicable | -- | -- | 3.584x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 159.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 24.6 | not applicable | -- | -- | 6.489x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 16.7 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 7.5 | not applicable | -- | -- | 2.224x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 40.9 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 9.3 | not applicable | -- | -- | 4.415x | -- | -- |

### `n5_vs_b200-mimo-v26-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | 3,851.6 | 1,772.5-1,772.5 | 10.86 | **no** | `b200_sxm-x23-nvl72-tensor` | 1,267.3 | 4,910.1-4,910.1 | 1.29 | yes | 3.039x | 0.361x | 0.119x |
| MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 5,503.2 | 8,245.3-8,245.3 | 3.34 | yes | `b200_sxm-x29-nvl72-tensor` | 1,307.1 | 5,228.7-5,228.7 | 1.25 | yes | 4.210x | 1.577x | 0.375x |
| MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 3,177.8 | 1,172.1-1,172.1 | 13.56 | **no** | `b200_sxm-x96-nvl72-hybrid` | 1,364.4 | 5,792.1-5,792.1 | 1.18 | yes | 2.329x | 0.202x | 0.087x |
| MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,337.9 | 700.8-700.8 | 23.81 | **no** | `b200_sxm-x636-nvl72-hybrid` | 1,369.1 | 5,977.4-5,977.4 | 1.15 | yes | 2.438x | 0.117x | 0.048x |
| MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 3,177.8 | 1,172.1-1,172.1 | 13.56 | **no** | `b200_sxm-x96-nvl72-hybrid` | 1,303.6 | 5,280.3-5,280.3 | 1.23 | yes | 2.438x | 0.222x | 0.091x |
| MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,337.9 | 700.8-700.8 | 23.81 | **no** | `b200_sxm-x636-nvl72-hybrid` | 1,369.1 | 5,977.4-5,977.4 | 1.15 | yes | 2.438x | 0.117x | 0.048x |
| MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 3,177.8 | 1,172.1-1,172.1 | 13.56 | **no** | `b200_sxm-x96-nvl72-hybrid` | 1,198.9 | 4,515.8-4,515.8 | 1.33 | yes | 2.651x | 0.260x | 0.098x |
| MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,337.9 | 700.8-700.8 | 23.81 | **no** | `b200_sxm-x636-nvl72-hybrid` | 1,369.1 | 5,977.4-5,977.4 | 1.15 | yes | 2.438x | 0.117x | 0.048x |
| MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x282` | 3,164.1 | 819.4-819.4 | 19.31 | **no** | `b200_sxm-x144-nvl72-hybrid` | 1,141.4 | 4,050.3-4,050.3 | 1.41 | yes | 2.772x | 0.202x | 0.073x |
| MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,337.9 | 700.8-700.8 | 23.81 | **no** | `b200_sxm-x636-nvl72-hybrid` | 1,332.7 | 5,585.4-5,585.4 | 1.19 | yes | 2.505x | 0.125x | 0.050x |
| MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 2,999.7 | 332.7-332.7 | 45.08 | **no** | `b200_sxm-x192-nvl72-hybrid` | 1,035.8 | 3,523.4-3,523.4 | 1.47 | yes | 2.896x | 0.094x | 0.033x |
| MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 2,752.9 | 690.0-690.0 | 19.95 | **no** | `b200_sxm-x636-nvl72-hybrid` | 1,257.7 | 4,907.0-4,907.0 | 1.28 | yes | 2.189x | 0.141x | 0.064x |
| MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 2,528.9 | 329.2-329.2 | 38.41 | **no** | `b200_sxm-x192-nvl72-hybrid` | 830.0 | 2,558.3-2,558.3 | 1.62 | yes | 3.047x | 0.129x | 0.042x |
| MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 1,845.1 | 396.2-396.2 | 23.28 | **no** | `b200_sxm-x636-nvl72-hybrid` | 1,134.2 | 4,024.6-4,024.6 | 1.41 | yes | 1.627x | 0.098x | 0.061x |
| MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 951.4 | 432.5-432.5 | 11.00 | **no** | `b200_sxm-x192-nvl72-hybrid` | 428.1 | 1,032.2-1,032.2 | 2.07 | yes | 2.222x | 0.419x | 0.189x |
| MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 600.0 | 101.0-101.0 | 29.71 | **no** | `b200_sxm-x636-nvl72-hybrid` | 747.3 | 2,030.0-2,030.0 | 1.84 | yes | 0.803x | 0.050x | 0.062x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 238.5 | 223.8-223.8 | 5.33 | **no** | `b200_sxm-x192-nvl72-hybrid` | 168.1 | 459.8-459.8 | 1.83 | yes | 1.419x | 0.487x | 0.343x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 159.0 | 25.3-25.3 | 31.40 | **no** | `b200_sxm-x636-nvl72-hybrid` | 364.5 | 755.8-755.8 | 2.41 | yes | 0.436x | 0.033x | 0.077x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 59.7 | 76.0-76.0 | 3.93 | yes | `b200_sxm-x192-nvl72-hybrid` | 53.1 | 175.1-175.1 | 1.52 | yes | 1.125x | 0.434x | 0.386x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x22` | 40.2 | 12.3-12.3 | 16.38 | **no** | `b200_sxm-x636-nvl72-hybrid` | 139.9 | 335.4-335.4 | 2.09 | yes | 0.287x | 0.037x | 0.127x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.033x to 0.386x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 2 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x61` | 3,551.3 | 1,386.5-1,386.5 | 12.81 | **no** | `a100_sxm_80gb-x60-tensor` | 414.3 | 1,340.5-1,340.5 | 1.55 | yes | 8.571x | 1.034x | 0.121x |
| MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 5,440.2 | 7,708.8-7,708.8 | 3.53 | yes | `a100_sxm_80gb-x56-hybrid` | 420.3 | 1,217.9-1,217.9 | 1.73 | yes | 12.943x | 6.330x | 0.489x |
| MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 2,500.3 | 1,248.7-1,248.7 | 10.01 | **no** | `a100_sxm_80gb-x335-hybrid` | 409.8 | 1,346.2-1,346.2 | 1.52 | yes | 6.102x | 0.928x | 0.152x |
| MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2,846.5 | 1,702.4-1,702.4 | 8.36 | **no** | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 1,338.4-1,338.4 | 1.51 | yes | 7.041x | 1.272x | 0.181x |
| MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 2,500.3 | 1,248.7-1,248.7 | 10.01 | **no** | `a100_sxm_80gb-x335-hybrid` | 409.8 | 1,346.2-1,346.2 | 1.52 | yes | 6.102x | 0.928x | 0.152x |
| MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2,846.5 | 1,702.4-1,702.4 | 8.36 | **no** | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 1,338.4-1,338.4 | 1.51 | yes | 7.041x | 1.272x | 0.181x |
| MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 2,500.3 | 1,248.7-1,248.7 | 10.01 | **no** | `a100_sxm_80gb-x335-hybrid` | 405.6 | 1,326.4-1,326.4 | 1.53 | yes | 6.165x | 0.941x | 0.153x |
| MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2,846.5 | 1,702.4-1,702.4 | 8.36 | **no** | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 1,338.4-1,338.4 | 1.51 | yes | 7.041x | 1.272x | 0.181x |
| MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 2,372.9 | 602.5-602.5 | 19.69 | **no** | `a100_sxm_80gb-x391-hybrid` | 403.4 | 1,327.0-1,327.0 | 1.52 | yes | 5.883x | 0.454x | 0.077x |
| MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2,466.1 | 922.5-922.5 | 13.37 | **no** | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 1,338.4-1,338.4 | 1.51 | yes | 6.100x | 0.689x | 0.113x |
| MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 2,087.2 | 593.2-593.2 | 17.59 | **no** | `a100_sxm_80gb-x391-hybrid` | 403.4 | 1,327.0-1,327.0 | 1.52 | yes | 5.175x | 0.447x | 0.086x |
| MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,970.3 | 495.7-495.7 | 19.87 | **no** | `a100_sxm_80gb-x1735-hybrid` | 403.8 | 1,479.2-1,479.2 | 1.36 | yes | 4.880x | 0.335x | 0.069x |
| MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,533.9 | 308.1-308.1 | 24.89 | **no** | `a100_sxm_80gb-x391-hybrid` | 369.2 | 1,183.1-1,183.1 | 1.56 | yes | 4.155x | 0.260x | 0.063x |
| MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,206.2 | 281.9-281.9 | 21.40 | **no** | `a100_sxm_80gb-x1735-hybrid` | 403.8 | 1,479.2-1,479.2 | 1.36 | yes | 2.987x | 0.191x | 0.064x |
| MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 501.8 | 79.1-79.1 | 31.72 | **no** | `a100_sxm_80gb-x391-hybrid` | 180.1 | 573.2-573.2 | 1.57 | yes | 2.787x | 0.138x | 0.050x |
| MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 356.0 | 71.2-71.2 | 25.01 | **no** | `a100_sxm_80gb-x1735-hybrid` | 383.0 | 1,356.5-1,356.5 | 1.41 | yes | 0.930x | 0.052x | 0.056x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 131.0 | 38.2-38.2 | 17.16 | **no** | `a100_sxm_80gb-x391-hybrid` | 64.5 | 227.2-227.2 | 1.42 | yes | 2.031x | 0.168x | 0.083x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 92.0 | 17.8-17.8 | 25.80 | **no** | `a100_sxm_80gb-x1735-hybrid` | 192.8 | 633.2-633.2 | 1.52 | yes | 0.477x | 0.028x | 0.059x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 33.0 | 31.3-31.3 | 5.29 | **no** | `a100_sxm_80gb-x391-hybrid` | 22.5 | 66.2-66.2 | 1.70 | yes | 1.471x | 0.472x | 0.321x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x31` | 23.1 | 8.6-8.6 | 13.48 | **no** | `a100_sxm_80gb-x1735-hybrid` | 69.9 | 256.0-256.0 | 1.37 | yes | 0.331x | 0.034x | 0.101x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.050x to 0.489x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 1 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 2,931.9 | 1,503.7-1,503.7 | 9.75 | **no** | `b200_sxm-x53-nvl72-tensor` | 1,286.9 | 5,517.3-5,517.3 | 1.17 | yes | 2.278x | 0.273x | 0.120x |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 5,241.1 | 2,915.8-2,915.8 | 8.99 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,301.9 | 5,610.6-5,610.6 | 1.16 | yes | 4.026x | 0.520x | 0.129x |
| MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,266.6 | 548.1-548.1 | 20.68 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 5,070.2-5,070.2 | 1.17 | yes | 1.919x | 0.108x | 0.056x |
| MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,266.6 | 548.1-548.1 | 20.68 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 5,070.2-5,070.2 | 1.17 | yes | 1.919x | 0.108x | 0.056x |
| MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,266.6 | 548.1-548.1 | 20.68 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 5,070.2-5,070.2 | 1.17 | yes | 1.919x | 0.108x | 0.056x |
| MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,266.6 | 548.1-548.1 | 20.68 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 5,070.2-5,070.2 | 1.17 | yes | 1.919x | 0.108x | 0.056x |
| MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,133.3 | 545.0-545.0 | 19.57 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 5,070.2-5,070.2 | 1.17 | yes | 1.806x | 0.107x | 0.060x |
| MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,573.0 | 284.6-284.6 | 27.63 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 1,138.1 | 4,704.5-4,704.5 | 1.21 | yes | 1.382x | 0.061x | 0.044x |
| MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 585.1 | 81.7-81.7 | 35.80 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 866.4 | 3,492.4-3,492.4 | 1.24 | yes | 0.675x | 0.023x | 0.035x |
| MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 157.7 | 20.6-20.6 | 38.36 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 447.8 | 1,669.9-1,669.9 | 1.34 | yes | 0.352x | 0.012x | 0.035x |
| MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 40.0 | 5.1-5.1 | 38.91 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 158.9 | 574.1-574.1 | 1.38 | yes | 0.252x | 0.009x | 0.036x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.035x to 0.129x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | 2,769.4 | 1,215.2-1,215.2 | 11.39 | **no** | `a100_sxm_80gb-x139-tensor` | 416.1 | 1,368.2-1,368.2 | 1.52 | yes | 6.656x | 0.888x | 0.133x |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 5,043.9 | 4,557.9-4,557.9 | 5.53 | **no** | `a100_sxm_80gb-x112-tensor` | 410.0 | 1,352.0-1,352.0 | 1.52 | yes | 12.302x | 3.371x | 0.274x |
| MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,455.6 | 393.3-393.3 | 18.51 | **no** | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 1,265.1-1,265.1 | 1.47 | yes | 3.916x | 0.311x | 0.079x |
| MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,455.6 | 393.3-393.3 | 18.51 | **no** | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 1,265.1-1,265.1 | 1.47 | yes | 3.916x | 0.311x | 0.079x |
| MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,455.6 | 393.3-393.3 | 18.51 | **no** | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 1,265.1-1,265.1 | 1.47 | yes | 3.916x | 0.311x | 0.079x |
| MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,455.6 | 393.3-393.3 | 18.51 | **no** | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 1,265.1-1,265.1 | 1.47 | yes | 3.916x | 0.311x | 0.079x |
| MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,455.6 | 393.3-393.3 | 18.51 | **no** | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 1,265.1-1,265.1 | 1.47 | yes | 3.916x | 0.311x | 0.079x |
| MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,045.2 | 383.2-383.2 | 13.64 | **no** | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 1,265.1-1,265.1 | 1.47 | yes | 2.812x | 0.303x | 0.108x |
| MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 346.2 | 100.4-100.4 | 17.25 | **no** | `a100_sxm_80gb-x8562-hybrid` | 331.9 | 1,194.2-1,194.2 | 1.39 | yes | 1.043x | 0.084x | 0.081x |
| MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 90.9 | 28.2-28.2 | 16.13 | **no** | `a100_sxm_80gb-x8562-hybrid` | 258.2 | 1,141.2-1,141.2 | 1.13 | yes | 0.352x | 0.025x | 0.070x |
| MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 22.9 | 7.1-7.1 | 16.26 | **no** | `a100_sxm_80gb-x8562-hybrid` | 101.1 | 411.6-411.6 | 1.23 | yes | 0.227x | 0.017x | 0.076x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.070x to 0.274x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 5,716.5 | 1,129.2-1,129.2 | 25.31 | **no** | `b200_sxm-x31-nvl72-tensor` | 1,356.6 | 5,439.7-5,439.7 | 1.25 | yes | 4.214x | 0.208x | 0.049x |
| MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,512.3 | 1,833.0-1,833.0 | 17.76 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,413.8 | 6,021.4-6,021.4 | 1.17 | yes | 4.606x | 0.304x | 0.066x |
| MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 5,716.5 | 1,129.2-1,129.2 | 25.31 | **no** | `b200_sxm-x31-nvl72-tensor` | 1,305.7 | 4,861.4-4,861.4 | 1.34 | yes | 4.378x | 0.232x | 0.053x |
| MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,512.3 | 1,833.0-1,833.0 | 17.76 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,380.6 | 5,583.9-5,583.9 | 1.24 | yes | 4.717x | 0.328x | 0.070x |
| MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 5,716.5 | 1,129.2-1,129.2 | 25.31 | **no** | `b200_sxm-x31-nvl72-tensor` | 1,217.9 | 4,105.7-4,105.7 | 1.48 | yes | 4.694x | 0.275x | 0.059x |
| MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,512.3 | 1,833.0-1,833.0 | 17.76 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,320.7 | 4,907.9-4,907.9 | 1.35 | yes | 4.931x | 0.373x | 0.076x |
| MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 5,716.5 | 1,129.2-1,129.2 | 25.31 | **no** | `b200_sxm-x31-nvl72-tensor` | 1,083.1 | 3,335.4-3,335.4 | 1.62 | yes | 5.278x | 0.339x | 0.064x |
| MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,512.3 | 1,833.0-1,833.0 | 17.76 | **no** | `b200_sxm-x58-nvl72-tensor` | 1,222.0 | 4,097.8-4,097.8 | 1.49 | yes | 5.329x | 0.447x | 0.084x |
| MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill` | 5,630.3 | 1,105.0-1,105.0 | 25.48 | **no** | `b200_sxm-x46-nvl72-tensor` | 1,023.3 | 3,054.8-3,054.8 | 1.67 | yes | 5.502x | 0.362x | 0.066x |
| MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 6,352.9 | 3,969.8-3,969.8 | 8.00 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,271.3 | 4,628.5-4,628.5 | 1.37 | yes | 4.997x | 0.858x | 0.172x |
| MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 5,495.4 | 1,113.6-1,113.6 | 24.67 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,001.3 | 3,004.7-3,004.7 | 1.67 | yes | 5.488x | 0.371x | 0.068x |
| MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6,240.7 | 4,030.5-4,030.5 | 7.74 | **no** | `b200_sxm-x347-nvl72-hybrid` | 1,262.4 | 4,525.0-4,525.0 | 1.39 | yes | 4.943x | 0.891x | 0.180x |
| MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,472.4 | 1,125.4-1,125.4 | 24.31 | **no** | `b200_sxm-x173-nvl72-hybrid` | 998.3 | 2,834.3-2,834.3 | 1.76 | yes | 5.481x | 0.397x | 0.072x |
| MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6,047.0 | 2,269.5-2,269.5 | 13.32 | **no** | `b200_sxm-x347-nvl72-hybrid` | 1,142.3 | 3,560.1-3,560.1 | 1.60 | yes | 5.294x | 0.637x | 0.120x |
| MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,472.1 | 558.7-558.7 | 40.02 | **no** | `b200_sxm-x173-nvl72-hybrid` | 678.9 | 1,256.0-1,256.0 | 2.70 | yes | 6.587x | 0.445x | 0.068x |
| MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,122.1 | 1,163.9-1,163.9 | 17.71 | **no** | `b200_sxm-x347-nvl72-hybrid` | 818.9 | 1,726.0-1,726.0 | 2.37 | yes | 5.034x | 0.674x | 0.134x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,830.9 | 256.3-256.3 | 35.71 | **no** | `b200_sxm-x173-nvl72-hybrid` | 413.1 | 682.3-682.3 | 3.03 | yes | 4.432x | 0.376x | 0.085x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,614.2 | 304.5-304.5 | 26.51 | **no** | `b200_sxm-x347-nvl72-hybrid` | 509.4 | 663.9-663.9 | 3.84 | yes | 3.169x | 0.459x | 0.145x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 525.0 | 164.5-164.5 | 15.95 | **no** | `b200_sxm-x173-nvl72-hybrid` | 221.7 | 329.6-329.6 | 3.36 | yes | 2.368x | 0.499x | 0.211x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 452.3 | 237.3-237.3 | 9.53 | **no** | `b200_sxm-x347-nvl72-hybrid` | 285.3 | 319.1-319.1 | 4.47 | yes | 1.585x | 0.744x | 0.469x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.049x to 0.469x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 5,316.5 | 860.0-860.0 | 30.91 | **no** | `a100_sxm_80gb-x67-hybrid` | 471.2 | 1,275.8-1,275.8 | 1.85 | yes | 11.283x | 0.674x | 0.060x |
| MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,652.5 | 1,821.4-1,821.4 | 15.52 | **no** | `a100_sxm_80gb-x224-hybrid` | 477.5 | 1,445.7-1,445.7 | 1.65 | yes | 11.838x | 1.260x | 0.106x |
| MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 5,316.5 | 860.0-860.0 | 30.91 | **no** | `a100_sxm_80gb-x67-hybrid` | 471.2 | 1,275.8-1,275.8 | 1.85 | yes | 11.283x | 0.674x | 0.060x |
| MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,652.5 | 1,821.4-1,821.4 | 15.52 | **no** | `a100_sxm_80gb-x224-hybrid` | 477.5 | 1,445.7-1,445.7 | 1.65 | yes | 11.838x | 1.260x | 0.106x |
| MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 5,316.5 | 860.0-860.0 | 30.91 | **no** | `a100_sxm_80gb-x67-hybrid` | 471.2 | 1,275.8-1,275.8 | 1.85 | yes | 11.283x | 0.674x | 0.060x |
| MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,652.5 | 1,821.4-1,821.4 | 15.52 | **no** | `a100_sxm_80gb-x224-hybrid` | 477.5 | 1,445.7-1,445.7 | 1.65 | yes | 11.838x | 1.260x | 0.106x |
| MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 5,316.5 | 860.0-860.0 | 30.91 | **no** | `a100_sxm_80gb-x67-hybrid` | 471.2 | 1,275.8-1,275.8 | 1.85 | yes | 11.283x | 0.674x | 0.060x |
| MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,652.5 | 1,821.4-1,821.4 | 15.52 | **no** | `a100_sxm_80gb-x224-hybrid` | 477.5 | 1,445.7-1,445.7 | 1.65 | yes | 11.838x | 1.260x | 0.106x |
| MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 5,316.5 | 860.0-860.0 | 30.91 | **no** | `a100_sxm_80gb-x67-hybrid` | 407.5 | 1,037.9-1,037.9 | 1.96 | yes | 13.048x | 0.829x | 0.064x |
| MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,474.8 | 5,108.8-5,108.8 | 5.36 | **no** | `a100_sxm_80gb-x672-hybrid` | 467.0 | 1,505.4-1,505.4 | 1.55 | yes | 11.724x | 3.394x | 0.289x |
| MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 5,152.8 | 824.5-824.5 | 31.25 | **no** | `a100_sxm_80gb-x154-hybrid` | 423.0 | 1,155.8-1,155.8 | 1.83 | yes | 12.181x | 0.713x | 0.059x |
| MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,323.7 | 3,074.6-3,074.6 | 8.66 | **no** | `a100_sxm_80gb-x672-hybrid` | 467.0 | 1,505.4-1,505.4 | 1.55 | yes | 11.400x | 2.042x | 0.179x |
| MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,096.9 | 823.9-823.9 | 30.93 | **no** | `a100_sxm_80gb-x335-hybrid` | 426.3 | 1,235.5-1,235.5 | 1.73 | yes | 11.956x | 0.667x | 0.056x |
| MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,450.6 | 1,681.0-1,681.0 | 13.24 | **no** | `a100_sxm_80gb-x672-hybrid` | 467.0 | 1,505.4-1,505.4 | 1.55 | yes | 9.531x | 1.117x | 0.117x |
| MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,830.4 | 406.1-406.1 | 47.16 | **no** | `a100_sxm_80gb-x335-hybrid` | 244.1 | 657.9-657.9 | 1.86 | yes | 15.689x | 0.617x | 0.039x |
| MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,330.3 | 849.5-849.5 | 13.72 | **no** | `a100_sxm_80gb-x672-hybrid` | 337.0 | 942.5-942.5 | 1.79 | yes | 6.915x | 0.901x | 0.130x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,424.3 | 186.2-186.2 | 38.25 | **no** | `a100_sxm_80gb-x335-hybrid` | 108.2 | 313.7-313.7 | 1.72 | yes | 13.163x | 0.593x | 0.045x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 723.5 | 220.1-220.1 | 16.44 | **no** | `a100_sxm_80gb-x672-hybrid` | 163.2 | 457.9-457.9 | 1.78 | yes | 4.433x | 0.481x | 0.108x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 395.4 | 120.5-120.5 | 16.40 | **no** | `a100_sxm_80gb-x335-hybrid` | 58.2 | 121.2-121.2 | 2.40 | yes | 6.791x | 0.994x | 0.146x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 190.0 | 171.5-171.5 | 5.54 | **no** | `a100_sxm_80gb-x672-hybrid` | 75.2 | 213.0-213.0 | 1.76 | yes | 2.528x | 0.805x | 0.318x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.039x to 0.318x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | 2,097.3 | 1,181.6-1,181.6 | 8.88 | **no** | `b200_sxm-x71-nvl72-tensor` | 916.0 | 3,798.1-3,798.1 | 1.21 | yes | 2.290x | 0.311x | 0.136x |
| MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 3,539.9 | 2,047.4-2,047.4 | 8.64 | **no** | `b200_sxm-x87-nvl72-hybrid` | 858.9 | 3,412.5-3,412.5 | 1.26 | yes | 4.121x | 0.600x | 0.146x |
| MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,111.3 | 1,074.6-1,074.6 | 9.82 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 3,746.8-3,746.8 | 1.17 | yes | 2.401x | 0.287x | 0.119x |
| MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,111.3 | 1,074.6-1,074.6 | 9.82 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 3,746.8-3,746.8 | 1.17 | yes | 2.401x | 0.287x | 0.119x |
| MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,111.3 | 1,074.6-1,074.6 | 9.82 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 3,746.8-3,746.8 | 1.17 | yes | 2.401x | 0.287x | 0.119x |
| MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,995.9 | 600.5-600.5 | 16.62 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 3,746.8-3,746.8 | 1.17 | yes | 2.270x | 0.160x | 0.071x |
| MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,836.2 | 319.2-319.2 | 28.76 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 852.9 | 3,437.5-3,437.5 | 1.24 | yes | 2.153x | 0.093x | 0.043x |
| MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,563.1 | 316.2-316.2 | 24.71 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 790.5 | 2,895.5-2,895.5 | 1.36 | yes | 1.977x | 0.109x | 0.055x |
| MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 574.7 | 90.7-90.7 | 31.68 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 556.6 | 1,569.0-1,569.0 | 1.77 | yes | 1.033x | 0.058x | 0.056x |
| MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 158.1 | 22.8-22.8 | 34.68 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 276.2 | 592.0-592.0 | 2.33 | yes | 0.573x | 0.039x | 0.067x |
| MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x49` | 40.3 | 5.7-5.7 | 35.33 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 108.7 | 274.1-274.1 | 1.98 | yes | 0.371x | 0.021x | 0.056x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.043x to 0.146x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | 1,970.2 | 910.8-910.8 | 10.82 | **no** | `a100_sxm_80gb-x178-tensor` | 281.6 | 818.3-818.3 | 1.72 | yes | 6.997x | 1.113x | 0.159x |
| MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 3,479.3 | 3,148.1-3,148.1 | 5.53 | **no** | `a100_sxm_80gb-x168-tensor` | 280.9 | 816.6-816.6 | 1.72 | yes | 12.387x | 3.855x | 0.311x |
| MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,737.8 | 837.5-837.5 | 10.37 | **no** | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 759.4-759.4 | 1.65 | yes | 6.924x | 1.103x | 0.159x |
| MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,737.8 | 837.5-837.5 | 10.37 | **no** | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 759.4-759.4 | 1.65 | yes | 6.924x | 1.103x | 0.159x |
| MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,737.8 | 837.5-837.5 | 10.37 | **no** | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 759.4-759.4 | 1.65 | yes | 6.924x | 1.103x | 0.159x |
| MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,737.8 | 837.5-837.5 | 10.37 | **no** | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 759.4-759.4 | 1.65 | yes | 6.924x | 1.103x | 0.159x |
| MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,401.1 | 443.6-443.6 | 15.79 | **no** | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 759.4-759.4 | 1.65 | yes | 5.583x | 0.584x | 0.105x |
| MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,024.4 | 228.5-228.5 | 22.42 | **no** | `a100_sxm_80gb-x3805-hybrid` | 248.8 | 736.6-736.6 | 1.69 | yes | 4.117x | 0.310x | 0.075x |
| MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 342.6 | 64.8-64.8 | 26.42 | **no** | `a100_sxm_80gb-x3805-hybrid` | 191.3 | 469.1-469.1 | 2.04 | yes | 1.791x | 0.138x | 0.077x |
| MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 90.5 | 16.3-16.3 | 27.76 | **no** | `a100_sxm_80gb-x3805-hybrid` | 135.5 | 433.3-433.3 | 1.56 | yes | 0.668x | 0.038x | 0.056x |
| MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x68` | 22.9 | 4.1-4.1 | 28.02 | **no** | `a100_sxm_80gb-x3805-hybrid` | 56.7 | 172.3-172.3 | 1.64 | yes | 0.403x | 0.024x | 0.059x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.056x to 0.311x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | 1,631.6 | 997.2-997.2 | 8.18 | **no** | `b200_sxm-x170-nvl72-hybrid` | 808.3 | 3,392.2-3,392.2 | 1.19 | yes | 2.019x | 0.294x | 0.146x |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 3,354.6 | 2,528.8-2,528.8 | 6.63 | **no** | `b200_sxm-x116-nvl72-hybrid` | 813.5 | 3,394.5-3,394.5 | 1.20 | yes | 4.124x | 0.745x | 0.181x |
| MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,291.2 | 255.3-255.3 | 25.29 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 3,142.3-3,142.3 | 1.19 | yes | 1.729x | 0.081x | 0.047x |
| MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,291.2 | 255.3-255.3 | 25.29 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 3,142.3-3,142.3 | 1.19 | yes | 1.729x | 0.081x | 0.047x |
| MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,291.2 | 255.3-255.3 | 25.29 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 3,142.3-3,142.3 | 1.19 | yes | 1.729x | 0.081x | 0.047x |
| MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,291.2 | 255.3-255.3 | 25.29 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 3,142.3-3,142.3 | 1.19 | yes | 1.729x | 0.081x | 0.047x |
| MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,291.2 | 255.3-255.3 | 25.29 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 3,142.3-3,142.3 | 1.19 | yes | 1.729x | 0.081x | 0.047x |
| MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,254.3 | 254.8-254.8 | 24.61 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 3,142.3-3,142.3 | 1.19 | yes | 1.679x | 0.081x | 0.048x |
| MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 552.1 | 66.0-66.0 | 41.79 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 627.0 | 2,267.9-2,267.9 | 1.38 | yes | 0.880x | 0.029x | 0.033x |
| MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 155.8 | 18.6-18.6 | 41.95 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 370.2 | 1,376.5-1,376.5 | 1.34 | yes | 0.421x | 0.013x | 0.032x |
| MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 39.9 | 4.6-4.6 | 42.96 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 142.9 | 521.5-521.5 | 1.37 | yes | 0.279x | 0.009x | 0.032x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.032x to 0.181x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x340` | 1,478.5 | 859.2-859.2 | 8.60 | **no** | `a100_sxm_80gb-x335-hybrid` | 229.5 | 708.4-708.4 | 1.62 | yes | 6.442x | 1.213x | 0.188x |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 3,198.6 | 1,849.6-1,849.6 | 8.65 | **no** | `a100_sxm_80gb-x336-hybrid` | 229.7 | 708.9-708.9 | 1.62 | yes | 13.926x | 2.609x | 0.187x |
| MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 763.8 | 182.1-182.1 | 20.97 | **no** | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 721.5-721.5 | 1.58 | yes | 3.356x | 0.252x | 0.075x |
| MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 763.8 | 182.1-182.1 | 20.97 | **no** | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 721.5-721.5 | 1.58 | yes | 3.356x | 0.252x | 0.075x |
| MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 763.8 | 182.1-182.1 | 20.97 | **no** | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 721.5-721.5 | 1.58 | yes | 3.356x | 0.252x | 0.075x |
| MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 763.8 | 182.1-182.1 | 20.97 | **no** | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 721.5-721.5 | 1.58 | yes | 3.356x | 0.252x | 0.075x |
| MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 763.8 | 182.1-182.1 | 20.97 | **no** | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 721.5-721.5 | 1.58 | yes | 3.356x | 0.252x | 0.075x |
| MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 763.8 | 182.1-182.1 | 20.97 | **no** | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 721.5-721.5 | 1.58 | yes | 3.356x | 0.252x | 0.075x |
| MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 323.9 | 91.0-91.0 | 17.81 | **no** | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 721.5-721.5 | 1.58 | yes | 1.423x | 0.126x | 0.089x |
| MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 89.9 | 25.6-25.6 | 17.56 | **no** | `a100_sxm_80gb-x18971-hybrid` | 159.3 | 487.8-487.8 | 1.63 | yes | 0.564x | 0.052x | 0.093x |
| MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 22.9 | 6.4-6.4 | 17.83 | **no** | `a100_sxm_80gb-x18971-hybrid` | 83.1 | 335.4-335.4 | 1.24 | yes | 0.275x | 0.019x | 0.069x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.069x to 0.188x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 3,210.4 | 748.1-748.1 | 21.46 | **no** | `b200_sxm-x77-nvl72-hybrid` | 871.3 | 3,381.4-3,381.4 | 1.29 | yes | 3.685x | 0.221x | 0.060x |
| MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,195.0 | 1,300.4-1,300.4 | 16.13 | **no** | `b200_sxm-x87-nvl72-hybrid` | 885.4 | 3,495.6-3,495.6 | 1.27 | yes | 4.738x | 0.372x | 0.079x |
| MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 3,210.4 | 748.1-748.1 | 21.46 | **no** | `b200_sxm-x77-nvl72-hybrid` | 871.3 | 3,381.4-3,381.4 | 1.29 | yes | 3.685x | 0.221x | 0.060x |
| MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,195.0 | 1,300.4-1,300.4 | 16.13 | **no** | `b200_sxm-x87-nvl72-hybrid` | 885.4 | 3,495.6-3,495.6 | 1.27 | yes | 4.738x | 0.372x | 0.079x |
| MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 3,210.4 | 748.1-748.1 | 21.46 | **no** | `b200_sxm-x77-nvl72-hybrid` | 832.7 | 2,996.8-2,996.8 | 1.39 | yes | 3.855x | 0.250x | 0.065x |
| MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,195.0 | 1,300.4-1,300.4 | 16.13 | **no** | `b200_sxm-x87-nvl72-hybrid` | 849.4 | 3,119.5-3,119.5 | 1.36 | yes | 4.939x | 0.417x | 0.084x |
| MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 3,210.4 | 748.1-748.1 | 21.46 | **no** | `b200_sxm-x77-nvl72-hybrid` | 766.5 | 2,447.5-2,447.5 | 1.57 | yes | 4.188x | 0.306x | 0.073x |
| MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,195.0 | 1,300.4-1,300.4 | 16.13 | **no** | `b200_sxm-x87-nvl72-hybrid` | 786.8 | 2,573.6-2,573.6 | 1.53 | yes | 5.332x | 0.505x | 0.095x |
| MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 3,210.4 | 748.1-748.1 | 21.46 | **no** | `b200_sxm-x77-nvl72-hybrid` | 666.0 | 1,876.2-1,876.2 | 1.77 | yes | 4.821x | 0.399x | 0.083x |
| MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 4,157.2 | 1,383.0-1,383.0 | 15.03 | **no** | `b200_sxm-x173-nvl72-hybrid` | 794.3 | 2,614.6-2,614.6 | 1.52 | yes | 5.234x | 0.529x | 0.101x |
| MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 3,152.0 | 684.5-684.5 | 23.02 | **no** | `b200_sxm-x150-nvl72-hybrid` | 666.1 | 1,885.2-1,885.2 | 1.77 | yes | 4.732x | 0.363x | 0.077x |
| MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,116.5 | 1,410.1-1,410.1 | 14.60 | **no** | `b200_sxm-x347-nvl72-hybrid` | 793.6 | 2,598.0-2,598.0 | 1.53 | yes | 5.187x | 0.543x | 0.105x |
| MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,000.5 | 356.4-356.4 | 42.09 | **no** | `b200_sxm-x173-nvl72-hybrid` | 564.3 | 1,421.7-1,421.7 | 1.98 | yes | 5.318x | 0.251x | 0.047x |
| MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,682.8 | 745.8-745.8 | 24.69 | **no** | `b200_sxm-x347-nvl72-hybrid` | 688.7 | 1,923.3-1,923.3 | 1.79 | yes | 5.348x | 0.388x | 0.073x |
| MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 2,326.9 | 177.6-177.6 | 65.51 | **no** | `b200_sxm-x200-nvl72-hybrid` | 349.7 | 614.9-614.9 | 2.84 | yes | 6.654x | 0.289x | 0.043x |
| MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,256.5 | 372.8-372.8 | 30.27 | **no** | `b200_sxm-x347-nvl72-hybrid` | 430.4 | 860.1-860.1 | 2.50 | yes | 5.243x | 0.433x | 0.083x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x392-romfill` | 844.7 | 83.1-83.1 | 50.85 | **no** | `b200_sxm-x200-nvl72-hybrid` | 191.9 | 237.9-237.9 | 4.03 | yes | 4.403x | 0.349x | 0.079x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 791.9 | 94.9-94.9 | 41.74 | **no** | `b200_sxm-x347-nvl72-hybrid` | 240.0 | 325.6-325.6 | 3.69 | yes | 3.299x | 0.291x | 0.088x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 318.3 | 93.8-93.8 | 16.96 | **no** | `b200_sxm-x200-nvl72-hybrid` | 96.9 | 104.3-104.3 | 4.65 | yes | 3.284x | 0.900x | 0.274x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 215.4 | 23.0-23.0 | 46.75 | **no** | `b200_sxm-x347-nvl72-hybrid` | 127.4 | 155.7-155.7 | 4.09 | yes | 1.691x | 0.148x | 0.087x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.043x to 0.274x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 3,007.4 | 538.2-538.2 | 27.94 | **no** | `a100_sxm_80gb-x208-tensor` | 285.7 | 827.9-827.9 | 1.73 | yes | 10.526x | 0.650x | 0.062x |
| MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,636.1 | 1,548.6-1,548.6 | 11.74 | **no** | `a100_sxm_80gb-x280-tensor` | 287.9 | 834.7-834.7 | 1.72 | yes | 12.628x | 1.855x | 0.147x |
| MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 3,007.4 | 538.2-538.2 | 27.94 | **no** | `a100_sxm_80gb-x208-hybrid` | 260.9 | 755.7-755.7 | 1.73 | yes | 11.527x | 0.712x | 0.062x |
| MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,636.1 | 1,548.6-1,548.6 | 11.74 | **no** | `a100_sxm_80gb-x280-hybrid` | 263.0 | 767.4-767.4 | 1.71 | yes | 13.825x | 2.018x | 0.146x |
| MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 3,007.4 | 538.2-538.2 | 27.94 | **no** | `a100_sxm_80gb-x208-hybrid` | 260.9 | 755.7-755.7 | 1.73 | yes | 11.527x | 0.712x | 0.062x |
| MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,636.1 | 1,548.6-1,548.6 | 11.74 | **no** | `a100_sxm_80gb-x280-hybrid` | 263.0 | 767.4-767.4 | 1.71 | yes | 13.825x | 2.018x | 0.146x |
| MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 3,007.4 | 538.2-538.2 | 27.94 | **no** | `a100_sxm_80gb-x208-hybrid` | 236.8 | 665.0-665.0 | 1.78 | yes | 12.699x | 0.809x | 0.064x |
| MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,636.1 | 1,548.6-1,548.6 | 11.74 | **no** | `a100_sxm_80gb-x280-hybrid` | 247.0 | 611.7-611.7 | 2.02 | yes | 14.719x | 2.532x | 0.172x |
| MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 3,007.4 | 538.2-538.2 | 27.94 | **no** | `a100_sxm_80gb-x208-hybrid` | 216.5 | 589.0-589.0 | 1.84 | yes | 13.894x | 0.914x | 0.066x |
| MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,611.2 | 696.1-696.1 | 25.94 | **no** | `a100_sxm_80gb-x672-hybrid` | 252.2 | 654.2-654.2 | 1.93 | yes | 14.317x | 1.064x | 0.074x |
| MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 2,958.5 | 497.9-497.9 | 29.71 | **no** | `a100_sxm_80gb-x249-hybrid` | 211.9 | 584.6-584.6 | 1.81 | yes | 13.963x | 0.852x | 0.061x |
| MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,256.7 | 367.1-367.1 | 44.36 | **no** | `a100_sxm_80gb-x672-hybrid` | 228.4 | 602.5-602.5 | 1.90 | yes | 14.261x | 0.609x | 0.043x |
| MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 2,762.3 | 486.1-486.1 | 28.41 | **no** | `a100_sxm_80gb-x373-hybrid` | 198.9 | 540.0-540.0 | 1.84 | yes | 13.884x | 0.900x | 0.065x |
| MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,723.8 | 363.4-363.4 | 37.48 | **no** | `a100_sxm_80gb-x672-hybrid` | 211.4 | 624.4-624.4 | 1.69 | yes | 12.886x | 0.582x | 0.045x |
| MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 1,884.0 | 128.2-128.2 | 73.46 | **no** | `a100_sxm_80gb-x373-hybrid` | 116.4 | 271.9-271.9 | 2.14 | yes | 16.187x | 0.472x | 0.029x |
| MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,182.9 | 93.6-93.6 | 63.18 | **no** | `a100_sxm_80gb-x672-hybrid` | 152.1 | 389.6-389.6 | 1.95 | yes | 7.777x | 0.240x | 0.031x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 731.2 | 74.9-74.9 | 48.82 | **no** | `a100_sxm_80gb-x373-hybrid` | 49.0 | 134.0-134.0 | 1.83 | yes | 14.907x | 0.559x | 0.037x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 345.9 | 23.6-23.6 | 73.34 | **no** | `a100_sxm_80gb-x672-hybrid` | 71.5 | 183.7-183.7 | 1.95 | yes | 4.840x | 0.128x | 0.027x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 230.6 | 33.4-33.4 | 34.49 | **no** | `a100_sxm_80gb-x373-hybrid` | 22.4 | 58.7-58.7 | 1.91 | yes | 10.293x | 0.569x | 0.055x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 89.5 | 22.5-22.5 | 19.86 | **no** | `a100_sxm_80gb-x672-hybrid` | 29.5 | 83.6-83.6 | 1.76 | yes | 3.040x | 0.269x | 0.089x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.027x to 0.172x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-qwen3-8b-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340-romfill` | 2,695.1 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,262.0 | not applicable | -- | -- | 2.135x | -- | -- |
| Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 8,234.2 | not applicable | -- | -- | `b200_sxm-x58-nvl72-tensor` | 1,276.4 | not applicable | -- | -- | 6.451x | -- | -- |

### `n6_vs_a100-qwen3-8b-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x308-romfill` | 2,733.5 | not applicable | -- | -- | `a100_sxm_80gb-x304-tensor` | 615.8 | not applicable | -- | -- | 4.439x | -- | -- |
| Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 8,190.8 | not applicable | -- | -- | `a100_sxm_80gb-x112-tensor` | 459.8 | not applicable | -- | -- | 17.813x | -- | -- |

### `n5_vs_b200-qwen3-8b-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x60-romfill` | 4,696.5 | not applicable | -- | -- | `b200_sxm-x31-nvl72-tensor` | 1,745.3 | not applicable | -- | -- | 2.691x | -- | -- |
| Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 9,134.8 | not applicable | -- | -- | `b200_sxm-x29-nvl72-tensor` | 1,699.9 | not applicable | -- | -- | 5.374x | -- | -- |
| Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,597.2 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | not applicable | -- | -- | 1.365x | -- | -- |
| Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,597.2 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | not applicable | -- | -- | 1.365x | -- | -- |
| Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,597.2 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | not applicable | -- | -- | 1.365x | -- | -- |
| Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,597.2 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | not applicable | -- | -- | 1.365x | -- | -- |
| Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,597.2 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | not applicable | -- | -- | 1.365x | -- | -- |
| Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1,746.9 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,865.9 | not applicable | -- | -- | 0.936x | -- | -- |
| Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 600.7 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,280.5 | not applicable | -- | -- | 0.469x | -- | -- |
| Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 158.3 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 593.6 | not applicable | -- | -- | 0.267x | -- | -- |
| Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 40.0 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 190.4 | not applicable | -- | -- | 0.210x | -- | -- |

### `n6_vs_a100-qwen3-8b-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 4,687.2 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 564.5 | not applicable | -- | -- | 8.304x | -- | -- |
| Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 9,194.4 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 564.5 | not applicable | -- | -- | 16.289x | -- | -- |
| Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196-romfill` | 1,731.8 | not applicable | -- | -- | `a100_sxm_80gb-x10969-tensor` | 584.4 | not applicable | -- | -- | 2.963x | -- | -- |
| Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 1,626.8 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 555.9 | not applicable | -- | -- | 2.927x | -- | -- |
| Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,447.5 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 555.9 | not applicable | -- | -- | 2.604x | -- | -- |
| Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,447.5 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 555.9 | not applicable | -- | -- | 2.604x | -- | -- |
| Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,447.5 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 555.9 | not applicable | -- | -- | 2.604x | -- | -- |
| Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,163.7 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 555.9 | not applicable | -- | -- | 2.093x | -- | -- |
| Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 353.7 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 502.9 | not applicable | -- | -- | 0.703x | -- | -- |
| Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 91.4 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 285.1 | not applicable | -- | -- | 0.321x | -- | -- |
| Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 23.0 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 117.9 | not applicable | -- | -- | 0.195x | -- | -- |

### `n5_vs_b200-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 2,488.0 | 258.0-258.0 | 48.22 | **no** | `b200_sxm-x58-nvl72-tensor` | 767.6 | 1,687.6-1,687.6 | 2.27 | yes | 3.241x | 0.153x | 0.047x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3,785.9 | 1,671.6-1,671.6 | 11.32 | **no** | `b200_sxm-x58-nvl72-tensor` | 767.6 | 1,687.6-1,687.6 | 2.27 | yes | 4.932x | 0.990x | 0.201x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,959.9 | 797.0-797.0 | 12.29 | **no** | `b200_sxm-x173-nvl72-hybrid` | 762.6 | 1,665.4-1,665.4 | 2.29 | yes | 2.570x | 0.479x | 0.186x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,758.2 | 5,995.7-5,995.7 | 2.30 | yes | `b200_sxm-x953-nvl72-hybrid` | 747.6 | 1,573.8-1,573.8 | 2.38 | yes | 3.689x | 3.810x | 1.033x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,959.9 | 797.0-797.0 | 12.29 | **no** | `b200_sxm-x173-nvl72-hybrid` | 747.5 | 1,636.6-1,636.6 | 2.28 | yes | 2.622x | 0.487x | 0.186x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,758.2 | 5,995.7-5,995.7 | 2.30 | yes | `b200_sxm-x953-nvl72-hybrid` | 747.6 | 1,573.8-1,573.8 | 2.38 | yes | 3.689x | 3.810x | 1.033x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,959.9 | 797.0-797.0 | 12.29 | **no** | `b200_sxm-x173-nvl72-hybrid` | 722.3 | 1,580.0-1,580.0 | 2.29 | yes | 2.713x | 0.504x | 0.186x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,758.2 | 5,995.7-5,995.7 | 2.30 | yes | `b200_sxm-x953-nvl72-hybrid` | 747.6 | 1,573.8-1,573.8 | 2.38 | yes | 3.689x | 3.810x | 1.033x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,959.9 | 797.0-797.0 | 12.29 | **no** | `b200_sxm-x173-nvl72-hybrid` | 720.6 | 1,500.6-1,500.6 | 2.40 | yes | 2.720x | 0.531x | 0.195x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,758.2 | 5,995.7-5,995.7 | 2.30 | yes | `b200_sxm-x953-nvl72-hybrid` | 737.6 | 1,508.2-1,508.2 | 2.45 | yes | 3.739x | 3.975x | 1.063x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,959.9 | 797.0-797.0 | 12.29 | **no** | `b200_sxm-x173-nvl72-hybrid` | 663.3 | 1,198.0-1,198.0 | 2.77 | yes | 2.955x | 0.665x | 0.225x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,758.2 | 5,995.7-5,995.7 | 2.30 | yes | `b200_sxm-x953-nvl72-hybrid` | 717.0 | 1,435.7-1,435.7 | 2.50 | yes | 3.847x | 4.176x | 1.086x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,959.9 | 797.0-797.0 | 12.29 | **no** | `b200_sxm-x173-nvl72-hybrid` | 570.4 | 1,041.4-1,041.4 | 2.74 | yes | 3.436x | 0.765x | 0.223x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,553.8 | 4,543.3-4,543.3 | 2.81 | yes | `b200_sxm-x953-nvl72-hybrid` | 707.0 | 1,195.0-1,195.0 | 2.96 | yes | 3.612x | 3.802x | 1.052x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349-romfill` | 1,403.7 | 416.1-416.1 | 16.87 | **no** | `b200_sxm-x178-pipeline` | 375.3 | 618.6-618.6 | 3.03 | yes | 3.741x | 0.673x | 0.180x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,694.8 | 1,759.2-1,759.2 | 4.82 | yes | `b200_sxm-x953-nvl72-hybrid` | 616.5 | 877.7-877.7 | 3.51 | yes | 2.749x | 2.004x | 0.729x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 576.3 | 79.3-79.3 | 36.35 | **no** | `b200_sxm-x178-pipeline` | 173.4 | 248.4-248.4 | 3.49 | yes | 3.323x | 0.319x | 0.096x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 634.8 | 67.7-67.7 | 46.87 | **no** | `b200_sxm-x953-pipeline` | 417.8 | 366.8-366.8 | 5.69 | **no** | 1.520x | 0.185x | 0.121x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 144.5 | 54.8-54.8 | 13.18 | **no** | `b200_sxm-x178-pipeline` | 58.3 | 147.4-147.4 | 1.98 | yes | 2.477x | 0.372x | 0.150x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 175.7 | 17.0-17.0 | 51.60 | **no** | `b200_sxm-x953-pipeline` | 210.8 | 226.8-226.8 | 4.65 | yes | 0.834x | 0.075x | 0.090x |

**Does the ratio compress?** Of 20 class rows in this study, 14 move the ROM-versus-GPU ratio DOWN under speculation and 6 move it UP. The movement spans 0.047x to 1.086x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 7 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 3,778.7 | 568.0-568.0 | 33.26 | **no** | `b200_sxm-x26-nvl72-tensor` | 864.3 | 3,172.9-3,172.9 | 1.36 | yes | 4.372x | 0.179x | 0.041x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,234.4 | 1,201.3-1,201.3 | 17.62 | **no** | `b200_sxm-x58-nvl72-tensor` | 885.0 | 3,307.0-3,307.0 | 1.34 | yes | 4.785x | 0.363x | 0.076x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 3,778.7 | 568.0-568.0 | 33.26 | **no** | `b200_sxm-x26-nvl72-tensor` | 831.0 | 2,629.9-2,629.9 | 1.58 | yes | 4.547x | 0.216x | 0.048x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,234.4 | 1,201.3-1,201.3 | 17.62 | **no** | `b200_sxm-x58-nvl72-tensor` | 854.2 | 2,739.6-2,739.6 | 1.56 | yes | 4.957x | 0.438x | 0.088x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 3,778.7 | 568.0-568.0 | 33.26 | **no** | `b200_sxm-x26-hybrid` | 814.8 | 2,504.3-2,504.3 | 1.63 | yes | 4.638x | 0.227x | 0.049x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,234.4 | 1,201.3-1,201.3 | 17.62 | **no** | `b200_sxm-x58-hybrid` | 823.4 | 2,533.7-2,533.7 | 1.62 | yes | 5.143x | 0.474x | 0.092x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 3,778.7 | 568.0-568.0 | 33.26 | **no** | `b200_sxm-x26-hybrid` | 755.4 | 1,978.0-1,978.0 | 1.91 | yes | 5.002x | 0.287x | 0.057x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,234.4 | 1,201.3-1,201.3 | 17.62 | **no** | `b200_sxm-x58-hybrid` | 823.4 | 2,533.7-2,533.7 | 1.62 | yes | 5.143x | 0.474x | 0.092x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 3,778.7 | 568.0-568.0 | 33.26 | **no** | `b200_sxm-x26-hybrid` | 661.5 | 1,434.0-1,434.0 | 2.31 | yes | 5.712x | 0.396x | 0.069x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,234.4 | 1,201.3-1,201.3 | 17.62 | **no** | `b200_sxm-x58-hybrid` | 765.5 | 2,020.3-2,020.3 | 1.89 | yes | 5.532x | 0.595x | 0.107x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x116-romfill` | 3,689.8 | 589.6-589.6 | 31.29 | **no** | `b200_sxm-x59-hybrid` | 676.1 | 1,487.0-1,487.0 | 2.27 | yes | 5.458x | 0.397x | 0.073x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,222.5 | 1,220.1-1,220.1 | 17.30 | **no** | `b200_sxm-x116-nvl72-hybrid` | 770.8 | 2,013.9-2,013.9 | 1.91 | yes | 5.478x | 0.606x | 0.111x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 3,689.8 | 589.6-589.6 | 31.29 | **no** | `b200_sxm-x87-nvl72-hybrid` | 632.7 | 1,306.4-1,306.4 | 2.42 | yes | 5.832x | 0.451x | 0.077x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,222.5 | 1,220.1-1,220.1 | 17.30 | **no** | `b200_sxm-x231-nvl72-hybrid` | 758.6 | 1,854.7-1,854.7 | 2.05 | yes | 5.566x | 0.658x | 0.118x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,169.5 | 566.9-566.9 | 27.96 | **no** | `b200_sxm-x173-nvl72-hybrid` | 489.5 | 851.7-851.7 | 2.87 | yes | 6.474x | 0.666x | 0.103x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,889.5 | 633.6-633.6 | 30.69 | **no** | `b200_sxm-x347-nvl72-hybrid` | 609.6 | 1,150.3-1,150.3 | 2.65 | yes | 6.380x | 0.551x | 0.086x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,612.8 | 261.8-261.8 | 30.80 | **no** | `b200_sxm-x173-nvl72-hybrid` | 251.0 | 448.5-448.5 | 2.80 | yes | 6.424x | 0.584x | 0.091x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,697.5 | 311.7-311.7 | 43.27 | **no** | `b200_sxm-x347-nvl72-hybrid` | 360.7 | 603.3-603.3 | 2.99 | yes | 7.478x | 0.517x | 0.069x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 498.2 | 165.5-165.5 | 15.05 | **no** | `b200_sxm-x173-nvl72-hybrid` | 121.3 | 185.7-185.7 | 3.27 | yes | 4.106x | 0.891x | 0.217x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,013.1 | 238.6-238.6 | 21.23 | **no** | `b200_sxm-x347-nvl72-hybrid` | 171.1 | 286.7-286.7 | 2.98 | yes | 5.922x | 0.832x | 0.141x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.041x to 0.217x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 3,818.2 | 594.4-594.4 | 32.12 | **no** | `b200_sxm-x30-nvl72-tensor` | 872.8 | 3,288.0-3,288.0 | 1.33 | yes | 4.374x | 0.181x | 0.041x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,262.0 | 1,211.3-1,211.3 | 17.59 | **no** | `b200_sxm-x58-nvl72-tensor` | 888.4 | 3,389.7-3,389.7 | 1.31 | yes | 4.797x | 0.357x | 0.074x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 3,818.2 | 594.4-594.4 | 32.12 | **no** | `b200_sxm-x30-nvl72-tensor` | 843.3 | 2,774.3-2,774.3 | 1.52 | yes | 4.528x | 0.214x | 0.047x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,262.0 | 1,211.3-1,211.3 | 17.59 | **no** | `b200_sxm-x58-nvl72-tensor` | 860.7 | 2,854.9-2,854.9 | 1.51 | yes | 4.952x | 0.424x | 0.086x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 3,818.2 | 594.4-594.4 | 32.12 | **no** | `b200_sxm-x30-hybrid` | 838.6 | 2,676.9-2,676.9 | 1.57 | yes | 4.553x | 0.222x | 0.049x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,262.0 | 1,211.3-1,211.3 | 17.59 | **no** | `b200_sxm-x58-hybrid` | 826.5 | 2,577.7-2,577.7 | 1.60 | yes | 5.157x | 0.470x | 0.091x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 3,818.2 | 594.4-594.4 | 32.12 | **no** | `b200_sxm-x30-hybrid` | 784.4 | 2,156.2-2,156.2 | 1.82 | yes | 4.868x | 0.276x | 0.057x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,262.0 | 1,211.3-1,211.3 | 17.59 | **no** | `b200_sxm-x58-hybrid` | 826.5 | 2,577.7-2,577.7 | 1.60 | yes | 5.157x | 0.470x | 0.091x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 3,818.2 | 594.4-594.4 | 32.12 | **no** | `b200_sxm-x30-hybrid` | 696.5 | 1,593.8-1,593.8 | 2.18 | yes | 5.482x | 0.373x | 0.068x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,262.0 | 1,211.3-1,211.3 | 17.59 | **no** | `b200_sxm-x58-hybrid` | 770.9 | 2,076.8-2,076.8 | 1.86 | yes | 5.528x | 0.583x | 0.106x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x116-romfill` | 3,754.2 | 593.3-593.3 | 31.64 | **no** | `b200_sxm-x59-hybrid` | 684.6 | 1,549.1-1,549.1 | 2.21 | yes | 5.484x | 0.383x | 0.070x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,249.6 | 1,230.7-1,230.7 | 17.26 | **no** | `b200_sxm-x116-nvl72-hybrid` | 776.6 | 2,073.8-2,073.8 | 1.87 | yes | 5.472x | 0.593x | 0.108x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 3,754.2 | 593.3-593.3 | 31.64 | **no** | `b200_sxm-x87-nvl72-hybrid` | 643.4 | 1,376.7-1,376.7 | 2.34 | yes | 5.835x | 0.431x | 0.074x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,249.6 | 1,230.7-1,230.7 | 17.26 | **no** | `b200_sxm-x231-nvl72-hybrid` | 764.4 | 1,907.1-1,907.1 | 2.00 | yes | 5.559x | 0.645x | 0.116x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 3,279.3 | 302.6-302.6 | 54.18 | **no** | `b200_sxm-x173-nvl72-hybrid` | 502.6 | 912.4-912.4 | 2.75 | yes | 6.525x | 0.332x | 0.051x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,015.0 | 638.3-638.3 | 31.45 | **no** | `b200_sxm-x347-nvl72-hybrid` | 619.6 | 1,204.4-1,204.4 | 2.57 | yes | 6.480x | 0.530x | 0.082x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,724.0 | 266.3-266.3 | 32.38 | **no** | `b200_sxm-x173-nvl72-hybrid` | 258.8 | 377.0-377.0 | 3.43 | yes | 6.661x | 0.706x | 0.106x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,867.5 | 314.7-314.7 | 45.56 | **no** | `b200_sxm-x347-nvl72-hybrid` | 362.9 | 635.9-635.9 | 2.85 | yes | 7.901x | 0.495x | 0.063x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 541.4 | 172.8-172.8 | 15.67 | **no** | `b200_sxm-x173-nvl72-hybrid` | 127.9 | 205.4-205.4 | 3.11 | yes | 4.235x | 0.841x | 0.199x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,113.7 | 246.3-246.3 | 22.61 | **no** | `b200_sxm-x347-nvl72-hybrid` | 175.1 | 309.8-309.8 | 2.83 | yes | 6.359x | 0.795x | 0.125x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.041x to 0.199x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,566.6 | 194.6-194.6 | 40.25 | **no** | `b200_sxm-x157-nvl72-hybrid` | 570.7 | 1,674.0-1,674.0 | 1.70 | yes | 2.745x | 0.116x | 0.042x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 2,130.2 | 913.4-913.4 | 11.66 | **no** | `b200_sxm-x116-nvl72-hybrid` | 574.9 | 1,705.4-1,705.4 | 1.69 | yes | 3.705x | 0.536x | 0.145x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,566.6 | 194.6-194.6 | 40.25 | **no** | `b200_sxm-x157-nvl72-hybrid` | 570.7 | 1,674.0-1,674.0 | 1.70 | yes | 2.745x | 0.116x | 0.042x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,074.9 | 875.5-875.5 | 11.85 | **no** | `b200_sxm-x289-nvl72-hybrid` | 571.7 | 1,650.3-1,650.3 | 1.73 | yes | 3.629x | 0.531x | 0.146x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,566.6 | 194.6-194.6 | 40.25 | **no** | `b200_sxm-x157-nvl72-hybrid` | 554.1 | 1,474.6-1,474.6 | 1.88 | yes | 2.827x | 0.132x | 0.047x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,074.9 | 875.5-875.5 | 11.85 | **no** | `b200_sxm-x289-nvl72-hybrid` | 571.7 | 1,650.3-1,650.3 | 1.73 | yes | 3.629x | 0.531x | 0.146x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,566.6 | 194.6-194.6 | 40.25 | **no** | `b200_sxm-x157-nvl72-hybrid` | 547.6 | 1,441.6-1,441.6 | 1.90 | yes | 2.861x | 0.135x | 0.047x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,074.9 | 875.5-875.5 | 11.85 | **no** | `b200_sxm-x289-nvl72-hybrid` | 545.3 | 1,514.5-1,514.5 | 1.80 | yes | 3.805x | 0.578x | 0.152x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,566.6 | 194.6-194.6 | 40.25 | **no** | `b200_sxm-x157-nvl72-hybrid` | 511.2 | 1,158.2-1,158.2 | 2.21 | yes | 3.065x | 0.168x | 0.055x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,074.9 | 875.5-875.5 | 11.85 | **no** | `b200_sxm-x289-nvl72-hybrid` | 539.9 | 1,340.0-1,340.0 | 2.01 | yes | 3.843x | 0.653x | 0.170x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,566.6 | 194.6-194.6 | 40.25 | **no** | `b200_sxm-x157-nvl72-hybrid` | 434.7 | 791.8-791.8 | 2.75 | yes | 3.603x | 0.246x | 0.068x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,074.9 | 875.5-875.5 | 11.85 | **no** | `b200_sxm-x289-nvl72-hybrid` | 498.8 | 1,062.0-1,062.0 | 2.35 | yes | 4.159x | 0.824x | 0.198x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,566.6 | 194.6-194.6 | 40.25 | **no** | `b200_sxm-x157-nvl72-hybrid` | 350.1 | 618.4-618.4 | 2.83 | yes | 4.475x | 0.315x | 0.070x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,994.5 | 471.0-471.0 | 21.17 | **no** | `b200_sxm-x289-nvl72-hybrid` | 420.7 | 721.2-721.2 | 2.92 | yes | 4.740x | 0.653x | 0.138x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,286.4 | 89.5-89.5 | 71.89 | **no** | `b200_sxm-x173-nvl72-hybrid` | 188.3 | 251.5-251.5 | 3.74 | yes | 6.833x | 0.356x | 0.052x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,478.0 | 233.7-233.7 | 31.62 | **no** | `b200_sxm-x347-nvl72-hybrid` | 269.8 | 397.2-397.2 | 3.40 | yes | 5.477x | 0.588x | 0.107x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 524.8 | 42.6-42.6 | 61.58 | **no** | `b200_sxm-x173-nvl72-hybrid` | 74.5 | 120.3-120.3 | 3.10 | yes | 7.046x | 0.354x | 0.050x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 671.4 | 59.7-59.7 | 56.25 | **no** | `b200_sxm-x347-nvl72-hybrid` | 121.6 | 173.9-173.9 | 3.49 | yes | 5.523x | 0.343x | 0.062x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 148.6 | 32.1-32.1 | 23.18 | **no** | `b200_sxm-x173-nvl72-hybrid` | 29.4 | 48.9-48.9 | 3.01 | yes | 5.056x | 0.656x | 0.130x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 198.8 | 22.2-22.2 | 44.67 | **no** | `b200_sxm-x347-nvl72-hybrid` | 45.4 | 75.5-75.5 | 3.00 | yes | 4.380x | 0.295x | 0.067x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.042x to 0.198x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,673.3 | 224.1-224.1 | 37.33 | **no** | `b200_sxm-x137-nvl72-hybrid` | 594.5 | 1,976.3-1,976.3 | 1.50 | yes | 2.814x | 0.113x | 0.040x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,250.0 | 898.1-898.1 | 12.53 | **no** | `b200_sxm-x144-nvl72-hybrid` | 595.8 | 1,984.4-1,984.4 | 1.50 | yes | 3.776x | 0.453x | 0.120x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,673.3 | 224.1-224.1 | 37.33 | **no** | `b200_sxm-x137-nvl72-hybrid` | 594.5 | 1,976.3-1,976.3 | 1.50 | yes | 2.814x | 0.113x | 0.040x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,250.0 | 898.1-898.1 | 12.53 | **no** | `b200_sxm-x144-nvl72-hybrid` | 595.8 | 1,984.4-1,984.4 | 1.50 | yes | 3.776x | 0.453x | 0.120x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,673.3 | 224.1-224.1 | 37.33 | **no** | `b200_sxm-x137-nvl72-hybrid` | 568.7 | 1,706.2-1,706.2 | 1.67 | yes | 2.943x | 0.131x | 0.045x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,250.0 | 898.1-898.1 | 12.53 | **no** | `b200_sxm-x144-nvl72-hybrid` | 570.6 | 1,717.3-1,717.3 | 1.66 | yes | 3.943x | 0.523x | 0.133x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,673.3 | 224.1-224.1 | 37.33 | **no** | `b200_sxm-x137-nvl72-hybrid` | 559.1 | 1,606.4-1,606.4 | 1.74 | yes | 2.993x | 0.140x | 0.047x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,250.0 | 898.1-898.1 | 12.53 | **no** | `b200_sxm-x144-nvl72-hybrid` | 564.3 | 1,631.3-1,631.3 | 1.73 | yes | 3.987x | 0.551x | 0.138x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,673.3 | 224.1-224.1 | 37.33 | **no** | `b200_sxm-x137-nvl72-hybrid` | 520.0 | 1,277.1-1,277.1 | 2.04 | yes | 3.218x | 0.175x | 0.055x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,250.0 | 898.1-898.1 | 12.53 | **no** | `b200_sxm-x144-nvl72-hybrid` | 525.6 | 1,297.9-1,297.9 | 2.02 | yes | 4.281x | 0.692x | 0.162x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,673.3 | 224.1-224.1 | 37.33 | **no** | `b200_sxm-x137-nvl72-hybrid` | 449.0 | 913.5-913.5 | 2.46 | yes | 3.727x | 0.245x | 0.066x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,229.0 | 900.6-900.6 | 12.37 | **no** | `b200_sxm-x347-nvl72-hybrid` | 532.6 | 1,282.3-1,282.3 | 2.08 | yes | 4.186x | 0.702x | 0.168x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,673.3 | 224.1-224.1 | 37.33 | **no** | `b200_sxm-x137-nvl72-hybrid` | 354.7 | 590.2-590.2 | 3.00 | yes | 4.718x | 0.380x | 0.080x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,185.5 | 474.1-474.1 | 23.05 | **no** | `b200_sxm-x347-nvl72-hybrid` | 469.9 | 932.1-932.1 | 2.52 | yes | 4.651x | 0.509x | 0.109x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,367.7 | 90.7-90.7 | 75.40 | **no** | `b200_sxm-x173-nvl72-hybrid` | 203.7 | 321.0-321.0 | 3.17 | yes | 6.714x | 0.283x | 0.042x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,824.8 | 238.9-238.9 | 38.19 | **no** | `b200_sxm-x347-nvl72-hybrid` | 287.6 | 471.0-471.0 | 3.05 | yes | 6.344x | 0.507x | 0.080x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 654.8 | 43.7-43.7 | 74.84 | **no** | `b200_sxm-x173-nvl72-hybrid` | 82.5 | 129.5-129.5 | 3.19 | yes | 7.934x | 0.338x | 0.043x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,015.2 | 60.9-60.9 | 83.33 | **no** | `b200_sxm-x347-nvl72-hybrid` | 129.4 | 195.9-195.9 | 3.30 | yes | 7.847x | 0.311x | 0.040x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 192.0 | 34.8-34.8 | 27.61 | **no** | `b200_sxm-x173-nvl72-hybrid` | 37.5 | 45.2-45.2 | 4.15 | yes | 5.114x | 0.770x | 0.150x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 396.7 | 76.4-76.4 | 25.98 | **no** | `b200_sxm-x347-nvl72-hybrid` | 53.4 | 74.5-74.5 | 3.58 | yes | 7.431x | 1.025x | 0.138x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.040x to 0.168x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,737.2 | 226.2-226.2 | 38.39 | **no** | `b200_sxm-x157-nvl72-hybrid` | 588.6 | 1,961.7-1,961.7 | 1.50 | yes | 2.951x | 0.115x | 0.039x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,305.6 | 903.4-903.4 | 12.76 | **no** | `b200_sxm-x144-nvl72-hybrid` | 598.2 | 2,029.7-2,029.7 | 1.47 | yes | 3.854x | 0.445x | 0.115x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,737.2 | 226.2-226.2 | 38.39 | **no** | `b200_sxm-x157-nvl72-hybrid` | 588.6 | 1,961.7-1,961.7 | 1.50 | yes | 2.951x | 0.115x | 0.039x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,305.6 | 903.4-903.4 | 12.76 | **no** | `b200_sxm-x144-nvl72-hybrid` | 598.2 | 2,029.7-2,029.7 | 1.47 | yes | 3.854x | 0.445x | 0.115x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,737.2 | 226.2-226.2 | 38.39 | **no** | `b200_sxm-x157-nvl72-hybrid` | 576.8 | 1,781.5-1,781.5 | 1.62 | yes | 3.012x | 0.127x | 0.042x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,305.6 | 903.4-903.4 | 12.76 | **no** | `b200_sxm-x144-nvl72-hybrid` | 573.6 | 1,762.6-1,762.6 | 1.63 | yes | 4.020x | 0.513x | 0.128x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,737.2 | 226.2-226.2 | 38.39 | **no** | `b200_sxm-x157-nvl72-hybrid` | 564.2 | 1,640.6-1,640.6 | 1.72 | yes | 3.079x | 0.138x | 0.045x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,305.6 | 903.4-903.4 | 12.76 | **no** | `b200_sxm-x144-nvl72-hybrid` | 566.5 | 1,660.5-1,660.5 | 1.71 | yes | 4.070x | 0.544x | 0.134x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,737.2 | 226.2-226.2 | 38.39 | **no** | `b200_sxm-x157-nvl72-hybrid` | 534.6 | 1,372.2-1,372.2 | 1.95 | yes | 3.249x | 0.165x | 0.051x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,305.6 | 903.4-903.4 | 12.76 | **no** | `b200_sxm-x144-nvl72-hybrid` | 529.0 | 1,331.1-1,331.1 | 1.99 | yes | 4.358x | 0.679x | 0.156x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,737.2 | 226.2-226.2 | 38.39 | **no** | `b200_sxm-x157-nvl72-hybrid` | 469.8 | 1,006.3-1,006.3 | 2.33 | yes | 3.698x | 0.225x | 0.061x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,303.4 | 474.3-474.3 | 24.28 | **no** | `b200_sxm-x144-nvl72-hybrid` | 460.2 | 963.6-963.6 | 2.39 | yes | 5.005x | 0.492x | 0.098x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,737.2 | 226.2-226.2 | 38.39 | **no** | `b200_sxm-x157-nvl72-hybrid` | 379.7 | 666.5-666.5 | 2.85 | yes | 4.576x | 0.339x | 0.074x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,292.9 | 476.3-476.3 | 24.07 | **no** | `b200_sxm-x347-nvl72-hybrid` | 474.4 | 960.1-960.1 | 2.47 | yes | 4.834x | 0.496x | 0.103x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,376.2 | 98.8-98.8 | 69.63 | **no** | `b200_sxm-x157-nvl72-hybrid` | 193.1 | 316.9-316.9 | 3.05 | yes | 7.128x | 0.312x | 0.044x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,912.2 | 240.0-240.0 | 39.84 | **no** | `b200_sxm-x347-nvl72-hybrid` | 288.1 | 487.2-487.2 | 2.96 | yes | 6.636x | 0.493x | 0.074x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 679.7 | 43.9-43.9 | 77.38 | **no** | `b200_sxm-x173-nvl72-hybrid` | 82.9 | 139.2-139.2 | 2.98 | yes | 8.202x | 0.316x | 0.038x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,049.8 | 61.1-61.1 | 85.90 | **no** | `b200_sxm-x347-nvl72-hybrid` | 129.8 | 206.8-206.8 | 3.14 | yes | 8.089x | 0.295x | 0.037x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 200.7 | 35.2-35.2 | 28.49 | **no** | `b200_sxm-x173-nvl72-hybrid` | 39.2 | 49.2-49.2 | 3.99 | yes | 5.115x | 0.716x | 0.140x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 415.1 | 120.6-120.6 | 17.21 | **no** | `b200_sxm-x347-nvl72-hybrid` | 53.9 | 79.9-79.9 | 3.37 | yes | 7.699x | 1.510x | 0.196x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.037x to 0.196x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x170` | 2,142.2 | 175.7-175.7 | 60.95 | **no** | `a100_sxm_80gb-x168-hybrid` | 332.9 | 535.8-535.8 | 3.11 | yes | 6.435x | 0.328x | 0.051x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 3,716.7 | 1,268.3-1,268.3 | 14.65 | **no** | `a100_sxm_80gb-x168-hybrid` | 332.9 | 535.8-535.8 | 3.11 | yes | 11.165x | 2.367x | 0.212x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,771.6 | 293.5-293.5 | 30.18 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 469.0-469.0 | 3.45 | yes | 5.471x | 0.626x | 0.114x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,405.2 | 340.9-340.9 | 35.28 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 276.3-276.3 | 5.88 | **no** | 7.404x | 1.234x | 0.167x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,771.6 | 293.5-293.5 | 30.18 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 469.0-469.0 | 3.45 | yes | 5.471x | 0.626x | 0.114x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,405.2 | 340.9-340.9 | 35.28 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 276.3-276.3 | 5.88 | **no** | 7.404x | 1.234x | 0.167x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,771.6 | 293.5-293.5 | 30.18 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 469.0-469.0 | 3.45 | yes | 5.471x | 0.626x | 0.114x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,405.2 | 340.9-340.9 | 35.28 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 276.3-276.3 | 5.88 | **no** | 7.404x | 1.234x | 0.167x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,771.6 | 293.5-293.5 | 30.18 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 469.0-469.0 | 3.45 | yes | 5.471x | 0.626x | 0.114x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,405.2 | 340.9-340.9 | 35.28 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 276.3-276.3 | 5.88 | **no** | 7.404x | 1.234x | 0.167x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,771.6 | 293.5-293.5 | 30.18 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 469.0-469.0 | 3.45 | yes | 5.471x | 0.626x | 0.114x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,405.2 | 340.9-340.9 | 35.28 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 276.3-276.3 | 5.88 | **no** | 7.404x | 1.234x | 0.167x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 1,664.8 | 611.0-611.0 | 13.62 | **no** | `a100_sxm_80gb-x387-hybrid` | 296.8 | 396.7-396.7 | 3.74 | yes | 5.610x | 1.540x | 0.275x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,210.8 | 338.3-338.3 | 32.68 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 276.3-276.3 | 5.88 | **no** | 6.805x | 1.224x | 0.180x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,177.0 | 79.4-79.4 | 74.15 | **no** | `a100_sxm_80gb-x387-hybrid` | 175.3 | 206.7-206.7 | 4.24 | yes | 6.714x | 0.384x | 0.057x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,229.9 | 97.6-97.6 | 63.00 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 276.3-276.3 | 5.88 | **no** | 3.786x | 0.353x | 0.093x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 358.8 | 38.3-38.3 | 46.81 | **no** | `a100_sxm_80gb-x387-hybrid` | 80.5 | 102.5-102.5 | 3.93 | yes | 4.456x | 0.374x | 0.084x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 390.0 | 24.6-24.6 | 79.11 | **no** | `a100_sxm_80gb-x2574-hybrid` | 222.0 | 138.7-138.7 | 8.00 | **no** | 1.756x | 0.178x | 0.101x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 93.4 | 31.0-31.0 | 15.06 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 103.3 | 6.2-6.2 | 83.67 | **no** | `a100_sxm_80gb-x2574-hybrid` | 111.7 | 60.7-60.7 | 9.19 | **no** | 0.925x | 0.102x | 0.110x |

**Does the ratio compress?** Of 19 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.051x to 0.275x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 10 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,425.7 | 404.9-404.9 | 42.30 | **no** | `a100_sxm_80gb-x73-hybrid` | 404.0 | 978.5-978.5 | 2.06 | yes | 8.480x | 0.414x | 0.049x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,946.2 | 991.6-991.6 | 19.90 | **no** | `a100_sxm_80gb-x112-hybrid` | 413.4 | 991.1-991.1 | 2.09 | yes | 9.547x | 1.000x | 0.105x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,425.7 | 404.9-404.9 | 42.30 | **no** | `a100_sxm_80gb-x73-hybrid` | 404.0 | 978.5-978.5 | 2.06 | yes | 8.480x | 0.414x | 0.049x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,946.2 | 991.6-991.6 | 19.90 | **no** | `a100_sxm_80gb-x112-hybrid` | 413.4 | 991.1-991.1 | 2.09 | yes | 9.547x | 1.000x | 0.105x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,425.7 | 404.9-404.9 | 42.30 | **no** | `a100_sxm_80gb-x73-hybrid` | 404.0 | 978.5-978.5 | 2.06 | yes | 8.480x | 0.414x | 0.049x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,946.2 | 991.6-991.6 | 19.90 | **no** | `a100_sxm_80gb-x112-hybrid` | 413.4 | 991.1-991.1 | 2.09 | yes | 9.547x | 1.000x | 0.105x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,425.7 | 404.9-404.9 | 42.30 | **no** | `a100_sxm_80gb-x73-hybrid` | 404.0 | 978.5-978.5 | 2.06 | yes | 8.480x | 0.414x | 0.049x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,946.2 | 991.6-991.6 | 19.90 | **no** | `a100_sxm_80gb-x112-hybrid` | 413.4 | 991.1-991.1 | 2.09 | yes | 9.547x | 1.000x | 0.105x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,425.7 | 404.9-404.9 | 42.30 | **no** | `a100_sxm_80gb-x73-hybrid` | 374.0 | 808.0-808.0 | 2.31 | yes | 9.159x | 0.501x | 0.055x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 3,941.8 | 1,634.2-1,634.2 | 12.06 | **no** | `a100_sxm_80gb-x168-hybrid` | 409.4 | 935.7-935.7 | 2.19 | yes | 9.628x | 1.747x | 0.181x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,425.7 | 404.9-404.9 | 42.30 | **no** | `a100_sxm_80gb-x73-hybrid` | 313.2 | 578.0-578.0 | 2.71 | yes | 10.937x | 0.701x | 0.064x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,924.3 | 1,674.3-1,674.3 | 11.72 | **no** | `a100_sxm_80gb-x448-hybrid` | 397.4 | 725.6-725.6 | 2.74 | yes | 9.874x | 2.308x | 0.234x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 3,369.8 | 429.6-429.6 | 39.22 | **no** | `a100_sxm_80gb-x146-hybrid` | 309.0 | 535.9-535.9 | 2.88 | yes | 10.906x | 0.802x | 0.074x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,922.2 | 1,665.8-1,665.8 | 11.77 | **no** | `a100_sxm_80gb-x672-hybrid` | 397.4 | 641.1-641.1 | 3.10 | yes | 9.869x | 2.598x | 0.263x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,828.2 | 413.6-413.6 | 34.19 | **no** | `a100_sxm_80gb-x335-hybrid` | 235.3 | 321.1-321.1 | 3.66 | yes | 12.022x | 1.288x | 0.107x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,256.7 | 860.8-860.8 | 18.92 | **no** | `a100_sxm_80gb-x672-hybrid` | 309.6 | 404.3-404.3 | 3.83 | yes | 10.519x | 2.129x | 0.202x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,277.8 | 190.2-190.2 | 33.59 | **no** | `a100_sxm_80gb-x335-hybrid` | 112.0 | 163.1-163.1 | 3.43 | yes | 11.410x | 1.166x | 0.102x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,776.8 | 225.5-225.5 | 39.40 | **no** | `a100_sxm_80gb-x672-hybrid` | 168.7 | 197.1-197.1 | 4.28 | yes | 10.535x | 1.144x | 0.109x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 375.6 | 120.9-120.9 | 15.53 | **no** | `a100_sxm_80gb-x335-hybrid` | 46.8 | 72.9-72.9 | 3.21 | yes | 8.022x | 1.658x | 0.207x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 567.0 | 172.6-172.6 | 16.42 | **no** | `a100_sxm_80gb-x672-hybrid` | 71.5 | 101.9-101.9 | 3.51 | yes | 7.925x | 1.693x | 0.214x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.049x to 0.263x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 3,498.1 | 432.5-432.5 | 40.44 | **no** | `a100_sxm_80gb-x73-hybrid` | 406.3 | 998.4-998.4 | 2.03 | yes | 8.609x | 0.433x | 0.050x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,176.9 | 1,628.4-1,628.4 | 12.83 | **no** | `a100_sxm_80gb-x112-hybrid` | 415.8 | 1,011.5-1,011.5 | 2.06 | yes | 10.045x | 1.610x | 0.160x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 3,498.1 | 432.5-432.5 | 40.44 | **no** | `a100_sxm_80gb-x73-hybrid` | 406.3 | 998.4-998.4 | 2.03 | yes | 8.609x | 0.433x | 0.050x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,176.9 | 1,628.4-1,628.4 | 12.83 | **no** | `a100_sxm_80gb-x112-hybrid` | 415.8 | 1,011.5-1,011.5 | 2.06 | yes | 10.045x | 1.610x | 0.160x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 3,498.1 | 432.5-432.5 | 40.44 | **no** | `a100_sxm_80gb-x73-hybrid` | 406.3 | 998.4-998.4 | 2.03 | yes | 8.609x | 0.433x | 0.050x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,176.9 | 1,628.4-1,628.4 | 12.83 | **no** | `a100_sxm_80gb-x112-hybrid` | 415.8 | 1,011.5-1,011.5 | 2.06 | yes | 10.045x | 1.610x | 0.160x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 3,498.1 | 432.5-432.5 | 40.44 | **no** | `a100_sxm_80gb-x73-hybrid` | 406.3 | 998.4-998.4 | 2.03 | yes | 8.609x | 0.433x | 0.050x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,176.9 | 1,628.4-1,628.4 | 12.83 | **no** | `a100_sxm_80gb-x112-hybrid` | 415.8 | 1,011.5-1,011.5 | 2.06 | yes | 10.045x | 1.610x | 0.160x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 3,498.1 | 432.5-432.5 | 40.44 | **no** | `a100_sxm_80gb-x73-hybrid` | 377.3 | 829.9-829.9 | 2.27 | yes | 9.272x | 0.521x | 0.056x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 4,169.8 | 1,660.5-1,660.5 | 12.56 | **no** | `a100_sxm_80gb-x168-hybrid` | 411.8 | 953.8-953.8 | 2.16 | yes | 10.126x | 1.741x | 0.172x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 3,498.1 | 432.5-432.5 | 40.44 | **no** | `a100_sxm_80gb-x73-hybrid` | 317.9 | 600.6-600.6 | 2.65 | yes | 11.005x | 0.720x | 0.065x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4,142.7 | 1,701.6-1,701.6 | 12.17 | **no** | `a100_sxm_80gb-x448-hybrid` | 399.7 | 736.4-736.4 | 2.71 | yes | 10.365x | 2.311x | 0.223x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 3,474.8 | 432.2-432.2 | 40.20 | **no** | `a100_sxm_80gb-x146-hybrid` | 313.7 | 556.3-556.3 | 2.82 | yes | 11.077x | 0.777x | 0.070x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,141.9 | 1,692.9-1,692.9 | 12.23 | **no** | `a100_sxm_80gb-x672-hybrid` | 399.7 | 649.5-649.5 | 3.08 | yes | 10.362x | 2.606x | 0.252x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,943.0 | 417.2-417.2 | 35.27 | **no** | `a100_sxm_80gb-x335-hybrid` | 240.2 | 334.3-334.3 | 3.59 | yes | 12.254x | 1.248x | 0.102x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,700.8 | 873.3-873.3 | 21.19 | **no** | `a100_sxm_80gb-x672-hybrid` | 313.8 | 414.7-414.7 | 3.78 | yes | 11.793x | 2.106x | 0.179x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,370.5 | 193.3-193.3 | 35.45 | **no** | `a100_sxm_80gb-x335-hybrid` | 112.9 | 170.4-170.4 | 3.31 | yes | 12.145x | 1.134x | 0.093x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,386.5 | 227.5-227.5 | 52.44 | **no** | `a100_sxm_80gb-x672-hybrid` | 169.6 | 202.6-202.6 | 4.19 | yes | 14.068x | 1.123x | 0.080x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 408.5 | 126.2-126.2 | 16.19 | **no** | `a100_sxm_80gb-x335-hybrid` | 47.4 | 79.6-79.6 | 2.98 | yes | 8.612x | 1.584x | 0.184x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 845.0 | 177.9-177.9 | 23.75 | **no** | `a100_sxm_80gb-x672-hybrid` | 72.3 | 107.6-107.6 | 3.36 | yes | 11.695x | 1.653x | 0.141x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.050x to 0.252x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,430.0 | 151.8-151.8 | 47.10 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 294.2-294.2 | 3.21 | yes | 7.580x | 0.516x | 0.068x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 2,087.8 | 651.9-651.9 | 16.01 | **no** | `a100_sxm_80gb-x336-hybrid` | 190.0 | 309.0-309.0 | 3.07 | yes | 10.990x | 2.110x | 0.192x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,430.0 | 151.8-151.8 | 47.10 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 294.2-294.2 | 3.21 | yes | 7.580x | 0.516x | 0.068x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,881.4 | 591.4-591.4 | 15.91 | **no** | `a100_sxm_80gb-x783-hybrid` | 186.9 | 234.5-234.5 | 3.99 | yes | 10.065x | 2.522x | 0.251x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,430.0 | 151.8-151.8 | 47.10 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 294.2-294.2 | 3.21 | yes | 7.580x | 0.516x | 0.068x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,881.4 | 591.4-591.4 | 15.91 | **no** | `a100_sxm_80gb-x783-hybrid` | 186.9 | 234.5-234.5 | 3.99 | yes | 10.065x | 2.522x | 0.251x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,430.0 | 151.8-151.8 | 47.10 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 294.2-294.2 | 3.21 | yes | 7.580x | 0.516x | 0.068x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,881.4 | 591.4-591.4 | 15.91 | **no** | `a100_sxm_80gb-x783-hybrid` | 186.9 | 234.5-234.5 | 3.99 | yes | 10.065x | 2.522x | 0.251x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,430.0 | 151.8-151.8 | 47.10 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 294.2-294.2 | 3.21 | yes | 7.580x | 0.516x | 0.068x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,881.4 | 591.4-591.4 | 15.91 | **no** | `a100_sxm_80gb-x783-hybrid` | 186.9 | 234.5-234.5 | 3.99 | yes | 10.065x | 2.522x | 0.251x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,430.0 | 151.8-151.8 | 47.10 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 294.2-294.2 | 3.21 | yes | 7.580x | 0.516x | 0.068x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,841.2 | 309.7-309.7 | 29.73 | **no** | `a100_sxm_80gb-x783-hybrid` | 186.9 | 234.5-234.5 | 3.99 | yes | 9.849x | 1.321x | 0.134x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,430.0 | 151.8-151.8 | 47.10 | **no** | `a100_sxm_80gb-x391-hybrid` | 176.0 | 259.8-259.8 | 3.39 | yes | 8.125x | 0.584x | 0.072x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,709.4 | 307.1-307.1 | 27.84 | **no** | `a100_sxm_80gb-x783-hybrid` | 186.9 | 234.5-234.5 | 3.99 | yes | 9.144x | 1.309x | 0.143x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,093.9 | 76.2-76.2 | 71.74 | **no** | `a100_sxm_80gb-x391-hybrid` | 95.6 | 115.5-115.5 | 4.14 | yes | 11.436x | 0.660x | 0.058x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,024.3 | 79.7-79.7 | 64.22 | **no** | `a100_sxm_80gb-x783-hybrid` | 135.4 | 147.6-147.6 | 4.59 | yes | 7.564x | 0.540x | 0.071x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 401.6 | 35.9-35.9 | 55.89 | **no** | `a100_sxm_80gb-x391-hybrid` | 37.1 | 50.9-50.9 | 3.64 | yes | 10.828x | 0.705x | 0.065x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 364.5 | 20.1-20.1 | 90.77 | **no** | `a100_sxm_80gb-x783-hybrid` | 59.6 | 65.0-65.0 | 4.59 | yes | 6.114x | 0.309x | 0.051x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 110.1 | 26.1-26.1 | 21.14 | **no** | `a100_sxm_80gb-x391-hybrid` | 13.2 | 21.8-21.8 | 3.03 | yes | 8.323x | 1.193x | 0.143x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 99.0 | 18.9-18.9 | 26.19 | **no** | `a100_sxm_80gb-x783-hybrid` | 22.1 | 30.5-30.5 | 3.62 | yes | 4.474x | 0.619x | 0.138x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.051x to 0.251x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,567.1 | 154.3-154.3 | 50.77 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 312.7-312.7 | 3.05 | yes | 8.212x | 0.494x | 0.060x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,216.0 | 661.7-661.7 | 16.75 | **no** | `a100_sxm_80gb-x336-hybrid` | 192.2 | 329.3-329.3 | 2.92 | yes | 11.529x | 2.009x | 0.174x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,567.1 | 154.3-154.3 | 50.77 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 312.7-312.7 | 3.05 | yes | 8.212x | 0.494x | 0.060x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,216.0 | 661.7-661.7 | 16.75 | **no** | `a100_sxm_80gb-x336-hybrid` | 192.2 | 329.3-329.3 | 2.92 | yes | 11.529x | 2.009x | 0.174x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,567.1 | 154.3-154.3 | 50.77 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 312.7-312.7 | 3.05 | yes | 8.212x | 0.494x | 0.060x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,216.0 | 661.7-661.7 | 16.75 | **no** | `a100_sxm_80gb-x336-hybrid` | 192.2 | 329.3-329.3 | 2.92 | yes | 11.529x | 2.009x | 0.174x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,567.1 | 154.3-154.3 | 50.77 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 312.7-312.7 | 3.05 | yes | 8.212x | 0.494x | 0.060x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,216.0 | 661.7-661.7 | 16.75 | **no** | `a100_sxm_80gb-x336-hybrid` | 192.2 | 329.3-329.3 | 2.92 | yes | 11.529x | 2.009x | 0.174x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,567.1 | 154.3-154.3 | 50.77 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 312.7-312.7 | 3.05 | yes | 8.212x | 0.494x | 0.060x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,216.0 | 661.7-661.7 | 16.75 | **no** | `a100_sxm_80gb-x336-hybrid` | 192.2 | 329.3-329.3 | 2.92 | yes | 11.529x | 2.009x | 0.174x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,567.1 | 154.3-154.3 | 50.77 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 312.7-312.7 | 3.05 | yes | 8.212x | 0.494x | 0.060x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,205.0 | 667.3-667.3 | 16.52 | **no** | `a100_sxm_80gb-x672-hybrid` | 189.2 | 260.8-260.8 | 3.63 | yes | 11.653x | 2.559x | 0.220x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,567.1 | 154.3-154.3 | 50.77 | **no** | `a100_sxm_80gb-x391-hybrid` | 178.9 | 279.4-279.4 | 3.20 | yes | 8.759x | 0.553x | 0.063x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,088.7 | 346.1-346.1 | 30.17 | **no** | `a100_sxm_80gb-x672-hybrid` | 189.2 | 260.8-260.8 | 3.63 | yes | 11.039x | 1.327x | 0.120x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,267.4 | 77.4-77.4 | 81.87 | **no** | `a100_sxm_80gb-x391-hybrid` | 100.6 | 132.5-132.5 | 3.80 | yes | 12.600x | 0.584x | 0.046x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,630.5 | 173.2-173.2 | 47.06 | **no** | `a100_sxm_80gb-x672-hybrid` | 130.8 | 155.5-155.5 | 4.21 | yes | 12.465x | 1.114x | 0.089x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 501.9 | 37.0-37.0 | 67.84 | **no** | `a100_sxm_80gb-x391-hybrid` | 38.4 | 52.0-52.0 | 3.69 | yes | 13.086x | 0.711x | 0.054x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 892.8 | 86.5-86.5 | 51.60 | **no** | `a100_sxm_80gb-x672-hybrid` | 56.1 | 68.8-68.8 | 4.08 | yes | 15.902x | 1.258x | 0.079x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 141.3 | 28.4-28.4 | 24.86 | **no** | `a100_sxm_80gb-x391-hybrid` | 14.5 | 18.6-18.6 | 3.89 | yes | 9.764x | 1.529x | 0.157x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 333.3 | 40.2-40.2 | 41.45 | **no** | `a100_sxm_80gb-x672-hybrid` | 20.3 | 33.0-33.0 | 3.07 | yes | 16.454x | 1.217x | 0.074x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.046x to 0.220x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,630.8 | 164.8-164.8 | 49.47 | **no** | `a100_sxm_80gb-x391-hybrid` | 191.0 | 312.8-312.8 | 3.05 | yes | 8.539x | 0.527x | 0.062x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,262.2 | 665.0-665.0 | 17.01 | **no** | `a100_sxm_80gb-x336-hybrid` | 192.4 | 329.4-329.4 | 2.92 | yes | 11.761x | 2.019x | 0.172x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,630.8 | 164.8-164.8 | 49.47 | **no** | `a100_sxm_80gb-x391-hybrid` | 191.0 | 312.8-312.8 | 3.05 | yes | 8.539x | 0.527x | 0.062x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,262.2 | 665.0-665.0 | 17.01 | **no** | `a100_sxm_80gb-x336-hybrid` | 192.4 | 329.4-329.4 | 2.92 | yes | 11.761x | 2.019x | 0.172x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,630.8 | 164.8-164.8 | 49.47 | **no** | `a100_sxm_80gb-x391-hybrid` | 191.0 | 312.8-312.8 | 3.05 | yes | 8.539x | 0.527x | 0.062x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,262.2 | 665.0-665.0 | 17.01 | **no** | `a100_sxm_80gb-x336-hybrid` | 192.4 | 329.4-329.4 | 2.92 | yes | 11.761x | 2.019x | 0.172x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,630.8 | 164.8-164.8 | 49.47 | **no** | `a100_sxm_80gb-x391-hybrid` | 191.0 | 312.8-312.8 | 3.05 | yes | 8.539x | 0.527x | 0.062x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,262.2 | 665.0-665.0 | 17.01 | **no** | `a100_sxm_80gb-x336-hybrid` | 192.4 | 329.4-329.4 | 2.92 | yes | 11.761x | 2.019x | 0.172x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,630.8 | 164.8-164.8 | 49.47 | **no** | `a100_sxm_80gb-x391-hybrid` | 191.0 | 312.8-312.8 | 3.05 | yes | 8.539x | 0.527x | 0.062x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,262.2 | 665.0-665.0 | 17.01 | **no** | `a100_sxm_80gb-x336-hybrid` | 192.4 | 329.4-329.4 | 2.92 | yes | 11.761x | 2.019x | 0.172x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,630.8 | 164.8-164.8 | 49.47 | **no** | `a100_sxm_80gb-x391-hybrid` | 191.0 | 312.8-312.8 | 3.05 | yes | 8.539x | 0.527x | 0.062x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,249.4 | 670.7-670.7 | 16.77 | **no** | `a100_sxm_80gb-x672-hybrid` | 189.4 | 260.9-260.9 | 3.63 | yes | 11.879x | 2.571x | 0.216x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,630.8 | 164.8-164.8 | 49.47 | **no** | `a100_sxm_80gb-x391-hybrid` | 179.1 | 279.4-279.4 | 3.20 | yes | 9.106x | 0.590x | 0.065x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,215.6 | 347.6-347.6 | 31.87 | **no** | `a100_sxm_80gb-x672-hybrid` | 189.4 | 260.9-260.9 | 3.63 | yes | 11.700x | 1.332x | 0.114x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,298.4 | 77.6-77.6 | 83.68 | **no** | `a100_sxm_80gb-x391-hybrid` | 100.8 | 134.2-134.2 | 3.76 | yes | 12.881x | 0.578x | 0.045x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,712.5 | 173.9-173.9 | 49.22 | **no** | `a100_sxm_80gb-x672-hybrid` | 131.0 | 156.3-156.3 | 4.19 | yes | 13.071x | 1.113x | 0.085x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 521.2 | 37.2-37.2 | 70.15 | **no** | `a100_sxm_80gb-x391-hybrid` | 38.5 | 54.1-54.1 | 3.56 | yes | 13.546x | 0.687x | 0.051x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 949.3 | 156.2-156.2 | 30.39 | **no** | `a100_sxm_80gb-x672-hybrid` | 56.3 | 70.5-70.5 | 3.99 | yes | 16.863x | 2.216x | 0.131x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 147.6 | 28.8-28.8 | 25.60 | **no** | `a100_sxm_80gb-x391-hybrid` | 14.5 | 19.8-19.8 | 3.67 | yes | 10.145x | 1.455x | 0.143x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 365.4 | 69.6-69.6 | 26.24 | **no** | `a100_sxm_80gb-x672-hybrid` | 20.3 | 33.2-33.2 | 3.07 | yes | 17.965x | 2.100x | 0.117x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.045x to 0.216x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x8-romfill` | 8,382.2 | not applicable | -- | -- | `b200_sxm-x4-tensor` | 1,019.6 | not applicable | -- | -- | 8.221x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 9,245.0 | not applicable | -- | -- | `b200_sxm-x29-nvl72-tensor` | 2,284.3 | not applicable | -- | -- | 4.047x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 7,221.4 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 2,283.2 | not applicable | -- | -- | 3.163x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 7,446.9 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,493.8 | not applicable | -- | -- | 2.986x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 7,221.4 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 2,199.2 | not applicable | -- | -- | 3.284x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 7,446.9 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,481.1 | not applicable | -- | -- | 3.001x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 7,221.4 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 2,048.4 | not applicable | -- | -- | 3.525x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 7,423.2 | not applicable | -- | -- | `b200_sxm-x231-nvl72-hybrid` | 2,442.5 | not applicable | -- | -- | 3.039x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x147-romfill` | 7,085.2 | not applicable | -- | -- | `b200_sxm-x75-nvl72-hybrid` | 2,099.4 | not applicable | -- | -- | 3.375x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6,431.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 2,432.9 | not applicable | -- | -- | 2.643x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,925.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,172.2 | not applicable | -- | -- | 3.188x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,170.8 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 2,325.6 | not applicable | -- | -- | 2.223x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,086.3 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,901.6 | not applicable | -- | -- | 3.201x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,660.4 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 2,137.1 | not applicable | -- | -- | 1.713x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,148.4 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,192.8 | not applicable | -- | -- | 2.639x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,238.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,521.5 | not applicable | -- | -- | 0.814x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 801.0 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 531.3 | not applicable | -- | -- | 1.507x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 331.2 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 808.3 | not applicable | -- | -- | 0.410x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 201.1 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 178.3 | not applicable | -- | -- | 1.128x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 84.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 314.7 | not applicable | -- | -- | 0.267x | -- | -- |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 3,459.7 | 520.5-520.5 | 33.23 | **no** | `b200_sxm-x29-nvl72-tensor` | 846.3 | 2,764.8-2,764.8 | 1.53 | yes | 4.088x | 0.188x | 0.046x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3,938.3 | 990.6-990.6 | 19.88 | **no** | `b200_sxm-x58-nvl72-tensor` | 862.2 | 2,836.5-2,836.5 | 1.52 | yes | 4.568x | 0.349x | 0.076x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 3,398.5 | 488.1-488.1 | 34.81 | **no** | `b200_sxm-x31-hybrid` | 818.6 | 2,369.4-2,369.4 | 1.73 | yes | 4.152x | 0.206x | 0.050x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,588.4 | 3,591.7-3,591.7 | 5.00 | yes | `b200_sxm-x202-nvl72-hybrid` | 858.2 | 2,781.5-2,781.5 | 1.54 | yes | 4.181x | 1.291x | 0.309x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 3,398.5 | 488.1-488.1 | 34.81 | **no** | `b200_sxm-x31-hybrid` | 818.6 | 2,369.4-2,369.4 | 1.73 | yes | 4.152x | 0.206x | 0.050x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,588.4 | 3,591.7-3,591.7 | 5.00 | yes | `b200_sxm-x202-nvl72-hybrid` | 851.5 | 2,736.6-2,736.6 | 1.56 | yes | 4.214x | 1.312x | 0.311x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 3,398.5 | 488.1-488.1 | 34.81 | **no** | `b200_sxm-x31-hybrid` | 747.5 | 1,776.5-1,776.5 | 2.10 | yes | 4.547x | 0.275x | 0.060x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,588.4 | 3,591.7-3,591.7 | 5.00 | yes | `b200_sxm-x202-nvl72-hybrid` | 828.3 | 2,536.7-2,536.7 | 1.63 | yes | 4.332x | 1.416x | 0.327x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 3,398.5 | 488.1-488.1 | 34.81 | **no** | `b200_sxm-x31-hybrid` | 638.5 | 1,206.9-1,206.9 | 2.65 | yes | 5.323x | 0.404x | 0.076x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,588.4 | 3,591.7-3,591.7 | 5.00 | yes | `b200_sxm-x202-nvl72-hybrid` | 802.0 | 2,185.3-2,185.3 | 1.83 | yes | 4.474x | 1.644x | 0.367x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x70` | 3,349.4 | 427.1-427.1 | 39.21 | **no** | `b200_sxm-x36-hybrid` | 545.6 | 1,046.1-1,046.1 | 2.61 | yes | 6.139x | 0.408x | 0.067x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,550.7 | 3,572.2-3,572.2 | 4.97 | yes | `b200_sxm-x347-nvl72-hybrid` | 788.7 | 2,007.4-2,007.4 | 1.96 | yes | 4.502x | 1.780x | 0.395x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 3,151.8 | 566.0-566.0 | 27.84 | **no** | `b200_sxm-x86-nvl72-hybrid` | 571.5 | 1,161.0-1,161.0 | 2.46 | yes | 5.515x | 0.488x | 0.088x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,448.8 | 2,111.9-2,111.9 | 8.17 | **no** | `b200_sxm-x347-nvl72-hybrid` | 756.8 | 1,762.9-1,762.9 | 2.15 | yes | 4.557x | 1.198x | 0.263x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,595.2 | 533.9-533.9 | 24.30 | **no** | `b200_sxm-x173-nvl72-hybrid` | 443.8 | 757.5-757.5 | 2.93 | yes | 5.848x | 0.705x | 0.121x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,436.5 | 1,089.4-1,089.4 | 11.18 | **no** | `b200_sxm-x347-nvl72-hybrid` | 564.1 | 982.2-982.2 | 2.87 | yes | 4.320x | 1.109x | 0.257x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,123.1 | 235.4-235.4 | 23.85 | **no** | `b200_sxm-x173-nvl72-hybrid` | 217.7 | 381.9-381.9 | 2.85 | yes | 5.158x | 0.616x | 0.119x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,035.3 | 293.0-293.0 | 17.67 | **no** | `b200_sxm-x347-nvl72-hybrid` | 320.0 | 497.5-497.5 | 3.22 | yes | 3.235x | 0.589x | 0.182x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 324.5 | 128.8-128.8 | 12.60 | **no** | `b200_sxm-x173-nvl72-hybrid` | 91.1 | 186.0-186.0 | 2.45 | yes | 3.564x | 0.693x | 0.194x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 297.9 | 84.2-84.2 | 17.70 | **no** | `b200_sxm-x347-nvl72-hybrid` | 140.2 | 255.5-255.5 | 2.74 | yes | 2.125x | 0.329x | 0.155x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340` | 1,165.4 | 166.8-166.8 | 34.93 | **no** | `b200_sxm-x173-nvl72-hybrid` | 509.0 | 1,044.2-1,044.2 | 2.44 | yes | 2.290x | 0.160x | 0.070x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 2,048.4 | 644.5-644.5 | 15.89 | **no** | `b200_sxm-x173-nvl72-hybrid` | 509.0 | 1,044.2-1,044.2 | 2.44 | yes | 4.025x | 0.617x | 0.153x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,163.0 | 144.7-144.7 | 40.20 | **no** | `b200_sxm-x203-nvl72-hybrid` | 511.9 | 1,047.1-1,047.1 | 2.44 | yes | 2.272x | 0.138x | 0.061x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,663.8 | 327.6-327.6 | 25.39 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 947.8-947.8 | 2.64 | yes | 3.328x | 0.346x | 0.104x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,163.0 | 144.7-144.7 | 40.20 | **no** | `b200_sxm-x203-nvl72-hybrid` | 504.9 | 1,029.9-1,029.9 | 2.45 | yes | 2.303x | 0.140x | 0.061x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,663.8 | 327.6-327.6 | 25.39 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 947.8-947.8 | 2.64 | yes | 3.328x | 0.346x | 0.104x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,163.0 | 144.7-144.7 | 40.20 | **no** | `b200_sxm-x203-nvl72-hybrid` | 486.0 | 942.8-942.8 | 2.58 | yes | 2.393x | 0.153x | 0.064x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,663.8 | 327.6-327.6 | 25.39 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 947.8-947.8 | 2.64 | yes | 3.328x | 0.346x | 0.104x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,163.0 | 144.7-144.7 | 40.20 | **no** | `b200_sxm-x203-nvl72-hybrid` | 463.0 | 828.2-828.2 | 2.80 | yes | 2.512x | 0.175x | 0.070x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,663.8 | 327.6-327.6 | 25.39 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 947.8-947.8 | 2.64 | yes | 3.328x | 0.346x | 0.104x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,163.0 | 144.7-144.7 | 40.20 | **no** | `b200_sxm-x203-nvl72-hybrid` | 395.7 | 700.5-700.5 | 2.82 | yes | 2.939x | 0.207x | 0.070x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,663.8 | 327.6-327.6 | 25.39 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 472.8 | 840.6-840.6 | 2.81 | yes | 3.519x | 0.390x | 0.111x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,163.0 | 144.7-144.7 | 40.20 | **no** | `b200_sxm-x203-nvl72-hybrid` | 312.7 | 442.9-442.9 | 3.53 | yes | 3.719x | 0.327x | 0.088x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,636.3 | 1,444.5-1,444.5 | 5.66 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 468.8 | 720.4-720.4 | 3.25 | yes | 3.491x | 2.005x | 0.574x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 943.2 | 74.3-74.3 | 63.50 | **no** | `b200_sxm-x203-nvl72-hybrid` | 165.5 | 218.5-218.5 | 3.79 | yes | 5.697x | 0.340x | 0.060x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,297.3 | 95.6-95.6 | 67.87 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 368.5 | 426.5-426.5 | 4.32 | yes | 3.521x | 0.224x | 0.064x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 338.0 | 34.8-34.8 | 48.62 | **no** | `b200_sxm-x203-nvl72-hybrid` | 67.5 | 90.2-90.2 | 3.74 | yes | 5.011x | 0.385x | 0.077x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 568.3 | 24.2-24.2 | 117.44 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 218.5 | 206.9-206.9 | 5.28 | **no** | 2.601x | 0.117x | 0.045x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 91.7 | 24.1-24.1 | 19.03 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 168.7 | 6.1-6.1 | 139.08 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 97.4 | 96.4-96.4 | 5.05 | **no** | 1.731x | 0.063x | 0.036x |

**Does the ratio compress?** Of 39 class rows in this study, 39 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.036x to 0.574x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 5 of 40 ROM rows and 37 of 40 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x16-romfill` | 7,885.6 | not applicable | -- | -- | `a100_sxm_80gb-x16-hybrid` | 559.8 | not applicable | -- | -- | 14.087x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 9,289.5 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 682.2 | not applicable | -- | -- | 13.617x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill` | 5,514.8 | not applicable | -- | -- | `a100_sxm_80gb-x204-tensor` | 687.0 | not applicable | -- | -- | 8.027x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,433.8 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 684.2 | not applicable | -- | -- | 7.942x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill` | 5,514.8 | not applicable | -- | -- | `a100_sxm_80gb-x204-hybrid` | 669.4 | not applicable | -- | -- | 8.239x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,433.8 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 684.2 | not applicable | -- | -- | 7.942x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill` | 5,514.8 | not applicable | -- | -- | `a100_sxm_80gb-x204-hybrid` | 622.8 | not applicable | -- | -- | 8.854x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,433.8 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 676.9 | not applicable | -- | -- | 8.027x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,429.1 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 583.5 | not applicable | -- | -- | 9.305x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,497.8 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 654.0 | not applicable | -- | -- | 6.878x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,053.4 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 542.6 | not applicable | -- | -- | 9.314x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,069.3 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 591.2 | not applicable | -- | -- | 5.191x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,991.7 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 518.7 | not applicable | -- | -- | 7.696x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,851.7 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 535.7 | not applicable | -- | -- | 3.456x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,578.5 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 411.4 | not applicable | -- | -- | 3.837x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 531.6 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 478.2 | not applicable | -- | -- | 1.112x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 430.3 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 225.0 | not applicable | -- | -- | 1.912x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 136.7 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 323.1 | not applicable | -- | -- | 0.423x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 110.7 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 80.4 | not applicable | -- | -- | 1.378x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 34.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 140.6 | not applicable | -- | -- | 0.244x | -- | -- |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | 3,111.9 | 369.7-369.7 | 42.08 | **no** | `a100_sxm_80gb-x79-hybrid` | 398.0 | 890.4-890.4 | 2.24 | yes | 7.818x | 0.415x | 0.053x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 3,938.3 | 982.6-982.6 | 20.04 | **no** | `a100_sxm_80gb-x112-hybrid` | 397.4 | 871.9-871.9 | 2.28 | yes | 9.910x | 1.127x | 0.114x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,019.3 | 344.8-344.8 | 43.79 | **no** | `a100_sxm_80gb-x85-hybrid` | 394.9 | 876.9-876.9 | 2.25 | yes | 7.647x | 0.393x | 0.051x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,217.9 | 836.3-836.3 | 19.24 | **no** | `a100_sxm_80gb-x560-hybrid` | 382.7 | 621.4-621.4 | 3.08 | yes | 8.409x | 1.346x | 0.160x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,019.3 | 344.8-344.8 | 43.79 | **no** | `a100_sxm_80gb-x85-hybrid` | 394.9 | 876.9-876.9 | 2.25 | yes | 7.647x | 0.393x | 0.051x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,217.9 | 836.3-836.3 | 19.24 | **no** | `a100_sxm_80gb-x560-hybrid` | 382.7 | 621.4-621.4 | 3.08 | yes | 8.409x | 1.346x | 0.160x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,019.3 | 344.8-344.8 | 43.79 | **no** | `a100_sxm_80gb-x85-hybrid` | 394.9 | 876.9-876.9 | 2.25 | yes | 7.647x | 0.393x | 0.051x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,217.9 | 836.3-836.3 | 19.24 | **no** | `a100_sxm_80gb-x560-hybrid` | 382.7 | 621.4-621.4 | 3.08 | yes | 8.409x | 1.346x | 0.160x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,019.3 | 344.8-344.8 | 43.79 | **no** | `a100_sxm_80gb-x85-hybrid` | 367.4 | 730.5-730.5 | 2.51 | yes | 8.218x | 0.472x | 0.057x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,217.9 | 836.3-836.3 | 19.24 | **no** | `a100_sxm_80gb-x560-hybrid` | 382.7 | 621.4-621.4 | 3.08 | yes | 8.409x | 1.346x | 0.160x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,019.3 | 344.8-344.8 | 43.79 | **no** | `a100_sxm_80gb-x85-hybrid` | 301.2 | 497.1-497.1 | 3.03 | yes | 10.024x | 0.693x | 0.069x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,094.0 | 435.2-435.2 | 35.54 | **no** | `a100_sxm_80gb-x560-hybrid` | 382.7 | 621.4-621.4 | 3.08 | yes | 8.085x | 0.700x | 0.087x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 2,805.9 | 772.2-772.2 | 18.17 | **no** | `a100_sxm_80gb-x312-hybrid` | 346.7 | 571.7-571.7 | 3.03 | yes | 8.094x | 1.351x | 0.167x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,761.8 | 364.0-364.0 | 37.93 | **no** | `a100_sxm_80gb-x672-hybrid` | 382.7 | 589.1-589.1 | 3.25 | yes | 7.217x | 0.618x | 0.086x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,237.6 | 390.5-390.5 | 28.65 | **no** | `a100_sxm_80gb-x335-hybrid` | 215.7 | 291.1-291.1 | 3.70 | yes | 10.375x | 1.341x | 0.129x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,462.6 | 182.7-182.7 | 40.04 | **no** | `a100_sxm_80gb-x672-hybrid` | 283.6 | 345.6-345.6 | 4.10 | yes | 5.157x | 0.528x | 0.102x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 877.4 | 171.7-171.7 | 25.55 | **no** | `a100_sxm_80gb-x335-hybrid` | 99.1 | 131.6-131.6 | 3.76 | yes | 8.853x | 1.304x | 0.147x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 480.3 | 46.8-46.8 | 51.29 | **no** | `a100_sxm_80gb-x672-hybrid` | 153.9 | 172.4-172.4 | 4.46 | yes | 3.121x | 0.272x | 0.087x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 296.6 | 72.5-72.5 | 20.47 | **no** | `a100_sxm_80gb-x312-hybrid` | 36.4 | 68.0-68.0 | 2.68 | yes | 8.142x | 1.066x | 0.131x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 128.2 | 23.0-23.0 | 27.84 | **no** | `a100_sxm_80gb-x672-hybrid` | 61.8 | 83.4-83.4 | 3.70 | yes | 2.075x | 0.276x | 0.133x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 1,066.2 | 261.4-261.4 | 20.39 | **no** | `a100_sxm_80gb-x384-hybrid` | 166.7 | 228.6-228.6 | 3.64 | yes | 6.397x | 1.143x | 0.179x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 1,973.7 | 456.8-456.8 | 21.60 | **no** | `a100_sxm_80gb-x504-hybrid` | 165.1 | 213.0-213.0 | 3.88 | yes | 11.953x | 2.145x | 0.179x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,480.8 | 236.4-236.4 | 31.31 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 98.4-98.4 | 8.39 | **no** | 8.970x | 2.402x | 0.268x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,480.8 | 236.4-236.4 | 31.31 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 98.4-98.4 | 8.39 | **no** | 8.970x | 2.402x | 0.268x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,480.8 | 236.4-236.4 | 31.31 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 98.4-98.4 | 8.39 | **no** | 8.970x | 2.402x | 0.268x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,480.8 | 236.4-236.4 | 31.31 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 98.4-98.4 | 8.39 | **no** | 8.970x | 2.402x | 0.268x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,480.8 | 236.4-236.4 | 31.31 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 98.4-98.4 | 8.39 | **no** | 8.970x | 2.402x | 0.268x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,480.8 | 236.4-236.4 | 31.31 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 98.4-98.4 | 8.39 | **no** | 8.970x | 2.402x | 0.268x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 986.7 | 68.6-68.6 | 71.92 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 98.4-98.4 | 8.39 | **no** | 5.977x | 0.697x | 0.117x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 361.1 | 17.3-17.3 | 104.64 | **no** | `a100_sxm_80gb-x3694-hybrid` | 118.2 | 64.6-64.6 | 9.14 | **no** | 3.055x | 0.267x | 0.087x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 100.3 | 4.3-4.3 | 116.15 | **no** | `a100_sxm_80gb-x3694-hybrid` | 54.9 | 28.7-28.7 | 9.55 | **no** | 1.828x | 0.150x | 0.082x |

**Does the ratio compress?** Of 31 class rows in this study, 31 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.051x to 0.268x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 31 ROM rows and 22 of 31 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 9,973.4 | not applicable | -- | -- | `b200_sxm-x2-tensor` | 1,328.0 | not applicable | -- | -- | 7.510x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 9,137.9 | not applicable | -- | -- | `b200_sxm-x29-nvl72-tensor` | 2,641.2 | not applicable | -- | -- | 3.460x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 7,078.7 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 2,601.6 | not applicable | -- | -- | 2.721x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 7,351.8 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,693.6 | not applicable | -- | -- | 2.729x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 7,078.7 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 2,493.1 | not applicable | -- | -- | 2.839x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 7,351.8 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,678.9 | not applicable | -- | -- | 2.744x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 7,078.7 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 2,301.1 | not applicable | -- | -- | 3.076x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 7,328.7 | not applicable | -- | -- | `b200_sxm-x231-nvl72-hybrid` | 2,633.5 | not applicable | -- | -- | 2.783x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x147-romfill` | 6,947.7 | not applicable | -- | -- | `b200_sxm-x75-nvl72-hybrid` | 2,322.4 | not applicable | -- | -- | 2.992x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 6,327.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 2,588.6 | not applicable | -- | -- | 2.444x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 6,794.8 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,328.9 | not applicable | -- | -- | 2.918x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 5,084.2 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 2,467.4 | not applicable | -- | -- | 2.061x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 5,997.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 2,086.3 | not applicable | -- | -- | 2.875x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,578.6 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 2,271.2 | not applicable | -- | -- | 1.576x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3,204.0 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,340.8 | not applicable | -- | -- | 2.390x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,226.9 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,676.9 | not applicable | -- | -- | 0.732x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 832.2 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 591.8 | not applicable | -- | -- | 1.406x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 331.1 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 913.1 | not applicable | -- | -- | 0.363x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 208.3 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 192.6 | not applicable | -- | -- | 1.081x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 84.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 349.1 | not applicable | -- | -- | 0.241x | -- | -- |

### `n6_vs_a100-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-hw-hybrid-x8-romfill` | 9,483.0 | not applicable | -- | -- | `a100_sxm_80gb-x8-tensor` | 1,063.1 | not applicable | -- | -- | 8.920x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 9,155.9 | not applicable | -- | -- | `a100_sxm_80gb-x56-hybrid` | 1,045.1 | not applicable | -- | -- | 8.761x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x207-romfill` | 5,414.9 | not applicable | -- | -- | `a100_sxm_80gb-x204-hybrid` | 990.7 | not applicable | -- | -- | 5.466x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,409.8 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 975.4 | not applicable | -- | -- | 5.546x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x207-romfill` | 5,414.9 | not applicable | -- | -- | `a100_sxm_80gb-x204-hybrid` | 990.7 | not applicable | -- | -- | 5.466x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,360.6 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 975.4 | not applicable | -- | -- | 5.496x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x207-romfill` | 5,414.9 | not applicable | -- | -- | `a100_sxm_80gb-x204-hybrid` | 990.7 | not applicable | -- | -- | 5.466x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,360.6 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 975.4 | not applicable | -- | -- | 5.496x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 5,333.5 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 979.9 | not applicable | -- | -- | 5.443x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 4,446.1 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 975.4 | not applicable | -- | -- | 4.558x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4,977.3 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 974.3 | not applicable | -- | -- | 5.109x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,025.7 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 975.4 | not applicable | -- | -- | 3.102x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3,884.8 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 922.5 | not applicable | -- | -- | 4.211x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,827.8 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 975.4 | not applicable | -- | -- | 1.874x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 1,571.3 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 630.0 | not applicable | -- | -- | 2.494x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 529.7 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 800.0 | not applicable | -- | -- | 0.662x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 429.3 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 277.8 | not applicable | -- | -- | 1.545x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 136.7 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 443.7 | not applicable | -- | -- | 0.308x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340` | 110.7 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 93.0 | not applicable | -- | -- | 1.191x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12` | 34.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 167.3 | not applicable | -- | -- | 0.205x | -- | -- |

## Where the drafter lives on a ROM machine

The locality rule -- `stored/peak` is a technology constant -- is the load-bearing assumption of the whole ROM verdict. A pass that reads only the drafter's region uses only that region's read ports and takes exactly as long as sweeping the entire array. Two placements are therefore priced side by side, and the second is an architectural proposal this study **has not costed in silicon area**.

The same rule is what makes a SEQUENTIAL draft step expensive here. A per-position operation that moves only a small table is nearly free on a global-bandwidth store and costs a full array sweep on this one, so a drafter with `gamma` sequential applications pays `gamma` sweeps for them. That term is charged in full below; on a bandwidth store the bytes it moves are not separately charged at all, because this repository's model configs carry no size for the table -- an omission whose size, on DeepSeek-V4-Pro-0813, is the externally published 132,382,720 B per draft token, 0.33% of the 39,666,603,980 B target pass.

| study | model | ctx | batch | class | design | tau* draft in ROM | tau* draft in KV store | KV placement feasible | why not |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 60.80 | 3.32 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.09 | 3.95 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 60.80 | 3.32 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.09 | 3.95 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 60.80 | 3.32 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.09 | 3.95 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 60.80 | 3.32 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.09 | 3.95 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 60.80 | 3.32 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.09 | 3.95 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 60.80 | 3.32 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 30.69 | 3.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x185` | 119.14 | 4.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 30.85 | 3.97 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 76.05 | 5.88 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 49.35 | 6.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 90.59 | 6.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 99.83 | 13.04 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 67.00 | 8.42 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 40.29 | 6.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 80.71 | 4.19 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 47.27 | 6.52 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 80.71 | 4.19 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 47.27 | 6.52 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 80.71 | 4.19 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 47.27 | 6.52 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 80.71 | 4.19 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 47.27 | 6.52 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 80.71 | 4.19 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 47.27 | 6.52 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 80.71 | 4.19 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 39.91 | 6.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 80.71 | 4.19 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 40.10 | 6.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 155.49 | 6.63 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 59.90 | 11.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 130.87 | 9.18 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 92.02 | 11.70 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 42.18 | 9.01 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 68.70 | 13.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 70.50 | 3.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.46 | 2.75 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 70.50 | 3.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.46 | 2.75 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 70.50 | 3.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.46 | 2.75 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 70.50 | 3.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.46 | 2.75 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 70.50 | 3.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.46 | 2.75 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 70.50 | 3.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 15.00 | 2.97 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 79.33 | 3.41 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 27.43 | 4.14 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 146.66 | 5.04 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 37.51 | 6.36 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 142.23 | 7.72 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 134.59 | 6.12 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 46.61 | 8.28 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 78.26 | 5.94 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 49.46 | 3.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 17.52 | 3.41 | NO | the KV store has no room for it |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 49.46 | 3.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 30.13 | 2.59 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 49.46 | 3.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 30.13 | 2.59 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 49.46 | 3.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 30.13 | 2.59 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 49.46 | 3.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 30.13 | 2.59 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 49.46 | 3.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 56.01 | 3.41 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 95.65 | 4.42 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 48.63 | 3.74 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 131.23 | 7.18 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 100.12 | 5.60 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 94.03 | 8.83 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 126.73 | 6.72 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 31.09 | 8.69 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 34.78 | 4.95 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 117.24 | 4.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.84 | 3.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 117.24 | 4.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.84 | 3.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 117.24 | 4.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.84 | 3.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 117.24 | 4.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.84 | 3.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 117.24 | 4.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 38.84 | 3.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 117.24 | 4.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 31.29 | 3.82 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 117.24 | 4.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 31.45 | 3.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 81.13 | 5.72 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 52.11 | 6.93 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 93.55 | 6.42 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 112.14 | 13.79 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 71.14 | 8.47 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 41.16 | 13.30 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 77.74 | 4.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 48.63 | 6.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 77.74 | 4.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 48.63 | 6.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 77.74 | 4.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 48.63 | 6.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 77.74 | 4.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 48.63 | 6.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 77.74 | 4.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 48.63 | 6.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 77.74 | 4.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 41.09 | 6.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 75.66 | 4.06 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 41.29 | 6.41 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 158.83 | 6.24 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 64.13 | 11.66 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 146.11 | 9.32 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 121.39 | 21.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 47.09 | 9.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 43.38 | 11.08 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 34.59 | 3.16 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 22.09 | 2.09 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 34.59 | 3.16 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 20.80 | 3.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 34.59 | 3.16 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 20.80 | 3.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 34.59 | 3.16 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 20.80 | 3.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 34.59 | 3.16 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 20.34 | 3.93 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 66.55 | 4.73 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 19.70 | 3.86 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 32.20 | 3.23 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 19.80 | 3.87 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 52.79 | 5.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 33.10 | 6.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 47.69 | 7.90 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 74.99 | 14.10 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 19.37 | 8.33 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 30.20 | 13.73 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 46.21 | 4.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 29.92 | 2.37 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 46.21 | 4.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.32 | 6.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 46.21 | 4.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.32 | 6.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 46.21 | 4.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.32 | 6.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 46.21 | 4.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.32 | 6.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 46.21 | 4.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 25.52 | 6.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 41.45 | 4.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 25.64 | 6.36 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 62.83 | 6.97 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 40.02 | 11.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 51.07 | 9.14 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 77.84 | 21.25 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 27.37 | 7.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 28.84 | 17.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 37.69 | 3.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 21.36 | 2.46 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 37.69 | 3.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.39 | 2.61 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 37.69 | 3.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.39 | 2.61 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 37.69 | 3.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.39 | 2.61 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 37.69 | 3.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 28.39 | 2.61 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x113` | 37.22 | 3.58 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.77 | 2.82 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 30.02 | 3.66 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 17.29 | 3.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 43.91 | 6.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 23.46 | 5.66 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 35.86 | 7.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 36.96 | 8.12 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 24.16 | 6.35 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 40.12 | 4.41 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 25.36 | 2.99 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | 15.35 | 2.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 25.36 | 2.99 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 21.19 | 2.56 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 25.36 | 2.99 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 21.19 | 2.56 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 25.36 | 2.99 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 21.19 | 2.56 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 25.36 | 2.99 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 30.13 | 2.52 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156` | 47.59 | 4.32 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 55.02 | 3.22 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 37.81 | 4.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 49.20 | 3.60 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 50.76 | 7.17 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 101.06 | 5.23 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 57.23 | 7.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 127.03 | 6.20 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340` | 41.32 | 8.67 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 34.39 | 4.38 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 65.84 | 4.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 21.12 | 3.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 65.84 | 4.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 21.12 | 3.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 65.84 | 4.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 21.12 | 3.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 65.84 | 4.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 21.12 | 3.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 65.84 | 4.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 20.65 | 3.78 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 65.84 | 4.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 19.99 | 3.71 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 65.49 | 4.63 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 20.09 | 3.72 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 55.82 | 5.36 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 34.89 | 6.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 52.56 | 7.88 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 84.02 | 15.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 21.03 | 8.37 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 34.22 | 14.92 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 43.28 | 3.92 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 27.30 | 6.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 43.28 | 3.92 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 27.30 | 6.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 43.28 | 3.92 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 27.30 | 6.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 43.28 | 3.92 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 27.30 | 6.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 43.28 | 3.92 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 27.30 | 6.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 43.28 | 3.92 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 26.44 | 6.31 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 42.47 | 3.93 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 26.57 | 6.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 67.25 | 6.92 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 43.83 | 12.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 56.44 | 9.27 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 93.61 | 24.84 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 25.61 | 8.67 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 35.21 | 21.34 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 34.59 | 3.16 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 20.80 | 3.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 34.59 | 3.16 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 20.80 | 3.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 34.59 | 3.16 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 20.80 | 3.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 34.59 | 3.16 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 20.80 | 3.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 34.59 | 3.16 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 20.34 | 3.93 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 66.55 | 4.73 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 19.70 | 3.86 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 32.20 | 3.23 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 19.80 | 3.87 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 52.79 | 5.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 33.10 | 6.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 47.69 | 7.90 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 74.99 | 14.10 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 19.37 | 8.33 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 30.20 | 13.73 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 46.21 | 4.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.32 | 6.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 46.21 | 4.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.32 | 6.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 46.21 | 4.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.32 | 6.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 46.21 | 4.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.32 | 6.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 46.21 | 4.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 26.32 | 6.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 46.21 | 4.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 25.52 | 6.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 41.45 | 4.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 25.64 | 6.36 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 62.83 | 6.97 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 40.02 | 11.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 51.07 | 9.14 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 77.86 | 21.26 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 27.37 | 7.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 28.84 | 17.83 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | 10.86 | 3.85 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 3.34 | 1.83 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 13.56 | 1.93 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 23.81 | 1.43 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 13.56 | 1.93 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 23.81 | 1.43 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 13.56 | 1.93 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 23.81 | 1.43 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x282` | 19.31 | 1.92 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 23.81 | 1.43 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 45.08 | 2.00 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 19.95 | 1.49 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 38.41 | 2.09 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 23.28 | 1.35 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 11.00 | 3.63 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 29.71 | 1.18 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 5.33 | 3.48 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 31.40 | 1.16 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 3.93 | 3.47 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x22` | 16.38 | 1.08 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x61` | 12.81 | 4.18 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 3.53 | 2.04 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 10.01 | 1.64 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 8.36 | 1.45 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 10.01 | 1.64 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 8.36 | 1.45 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 10.01 | 1.64 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 8.36 | 1.45 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 19.69 | 1.63 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 13.37 | 1.38 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 17.59 | 1.70 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 19.87 | 1.33 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 24.89 | 1.53 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 21.40 | 1.25 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 31.72 | 1.46 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 25.01 | 1.22 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 17.16 | 1.37 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 25.80 | 1.22 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 5.29 | 1.30 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x31` | 13.48 | 1.11 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 9.75 | 3.50 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 8.99 | 2.60 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 20.68 | 1.25 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 20.68 | 1.25 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 20.68 | 1.25 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 20.68 | 1.25 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 19.57 | 1.29 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 27.63 | 1.15 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 35.80 | 1.06 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 38.36 | 1.04 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 38.91 | 1.04 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | 11.39 | 3.81 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 5.53 | 2.47 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 18.51 | 1.15 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 18.51 | 1.15 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 18.51 | 1.15 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 18.51 | 1.15 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 18.51 | 1.15 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 13.64 | 1.17 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 17.25 | 1.05 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 16.13 | 1.03 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 16.26 | 1.03 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 25.31 | 3.18 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 17.76 | 2.69 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 25.31 | 3.18 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 17.76 | 2.69 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 25.31 | 3.18 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 17.76 | 2.69 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 25.31 | 3.18 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 17.76 | 2.69 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill` | 25.48 | 3.19 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 8.00 | 2.73 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 24.67 | 3.14 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 7.74 | 2.68 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 24.31 | 3.12 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 13.32 | 3.52 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 40.02 | 5.39 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 17.71 | 4.42 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 35.71 | 7.35 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 26.51 | 5.78 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 15.95 | 7.82 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 9.53 | 3.72 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 30.91 | 4.18 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 15.52 | 2.61 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 30.91 | 4.18 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 15.52 | 2.61 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 30.91 | 4.18 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 15.52 | 2.61 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 30.91 | 4.18 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 15.52 | 2.61 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 30.91 | 4.18 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.36 | 2.57 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 31.25 | 3.98 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 8.66 | 3.37 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 30.93 | 3.96 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 13.24 | 4.39 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 47.16 | 6.62 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 13.72 | 4.51 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 38.25 | 8.10 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 16.44 | 5.05 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.40 | 8.03 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 5.54 | 2.55 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | 8.88 | 3.14 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 8.64 | 2.19 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 9.82 | 1.45 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 9.82 | 1.45 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 9.82 | 1.45 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 16.62 | 1.40 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 28.76 | 1.33 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 24.71 | 1.36 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 31.68 | 1.19 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 34.68 | 1.17 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x49` | 35.33 | 1.16 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | 10.82 | 3.63 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 5.53 | 2.35 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 10.37 | 1.40 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 10.37 | 1.40 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 10.37 | 1.40 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 10.37 | 1.40 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 15.79 | 1.32 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 22.42 | 1.26 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 26.42 | 1.23 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 27.76 | 1.23 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x68` | 28.02 | 1.23 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | 8.18 | 2.70 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 6.63 | 2.55 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 25.29 | 1.18 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 25.29 | 1.18 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 25.29 | 1.18 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 25.29 | 1.18 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 25.29 | 1.18 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 24.61 | 1.19 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 41.79 | 1.07 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 41.95 | 1.05 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 42.96 | 1.04 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x340` | 8.60 | 3.65 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 8.65 | 2.80 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 20.97 | 1.11 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 20.97 | 1.11 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 20.97 | 1.11 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 20.97 | 1.11 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 20.97 | 1.11 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 20.97 | 1.11 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 17.81 | 1.06 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 17.56 | 1.04 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 17.83 | 1.03 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 21.46 | 3.01 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 16.13 | 3.08 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 21.46 | 3.01 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 16.13 | 3.08 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 21.46 | 3.01 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 16.13 | 3.08 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 21.46 | 3.01 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 16.13 | 3.08 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 21.46 | 3.01 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 15.03 | 3.12 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 23.02 | 2.77 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 14.60 | 3.07 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 42.09 | 3.80 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 24.69 | 4.06 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 65.51 | 6.11 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 30.27 | 5.13 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x392-romfill` | 50.85 | 7.72 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 41.74 | 6.62 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 16.96 | 7.45 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 46.75 | 2.68 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 27.94 | 3.64 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 11.74 | 2.85 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 27.94 | 3.64 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 11.74 | 2.85 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 27.94 | 3.64 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 11.74 | 2.85 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 27.94 | 3.64 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 11.74 | 2.85 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 27.94 | 3.64 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 25.94 | 2.75 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 29.71 | 3.36 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 44.36 | 3.49 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 28.41 | 3.81 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 37.48 | 3.29 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 73.46 | 7.38 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 63.18 | 4.14 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 48.82 | 7.03 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 73.34 | 4.58 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 34.49 | 8.13 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 19.86 | 2.07 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 48.22 | 5.28 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 11.32 | 2.15 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 12.29 | 5.12 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.30 | 1.79 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 12.29 | 5.12 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.30 | 1.79 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 12.29 | 5.12 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.30 | 1.79 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 12.29 | 5.12 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.30 | 1.79 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 12.29 | 5.12 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.30 | 1.79 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 12.29 | 5.12 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.81 | 1.99 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349-romfill` | 16.87 | 6.68 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 4.82 | 2.67 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 36.35 | 5.99 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 46.87 | 2.19 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 13.18 | 5.67 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 51.60 | 2.13 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 33.26 | 4.29 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.62 | 6.37 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 33.26 | 4.29 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.62 | 6.37 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 33.26 | 4.29 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.62 | 6.37 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 33.26 | 4.29 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.62 | 6.37 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 33.26 | 4.29 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.62 | 6.37 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x116-romfill` | 31.29 | 4.27 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 17.30 | 6.28 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 31.29 | 4.27 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 17.30 | 6.28 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 27.96 | 5.05 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 30.69 | 10.44 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 30.80 | 8.25 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 43.27 | 18.62 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 15.05 | 8.67 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 21.23 | 19.30 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 32.12 | 4.16 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.59 | 6.27 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 32.12 | 4.16 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.59 | 6.27 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 32.12 | 4.16 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.59 | 6.27 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 32.12 | 4.16 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.59 | 6.27 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 32.12 | 4.16 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 17.59 | 6.27 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x116-romfill` | 31.64 | 4.15 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 17.26 | 6.17 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 31.64 | 4.15 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 17.26 | 6.17 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 54.18 | 6.15 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 31.45 | 10.54 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 32.38 | 8.27 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 45.56 | 19.36 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 15.67 | 8.73 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 22.61 | 20.49 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 40.25 | 3.90 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 11.66 | 2.93 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 40.25 | 3.90 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 11.85 | 3.17 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 40.25 | 3.90 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 11.85 | 3.17 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 40.25 | 3.90 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 11.85 | 3.17 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 40.25 | 3.90 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 11.85 | 3.17 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 40.25 | 3.90 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 11.85 | 3.17 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 40.25 | 3.90 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 21.17 | 4.71 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 71.89 | 6.25 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 31.62 | 8.45 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 61.58 | 8.76 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 56.25 | 14.35 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 23.18 | 8.91 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 44.67 | 10.66 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 37.33 | 3.64 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.53 | 3.11 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 37.33 | 3.64 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.53 | 3.11 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 37.33 | 3.64 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.53 | 3.11 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 37.33 | 3.64 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.53 | 3.11 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 37.33 | 3.64 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.53 | 3.11 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 37.33 | 3.64 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 12.37 | 3.09 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 37.33 | 3.64 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 23.05 | 4.84 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 75.40 | 5.61 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 38.19 | 9.58 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 74.84 | 8.95 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 83.33 | 19.98 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 27.61 | 9.18 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 25.98 | 11.69 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 38.39 | 3.69 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.76 | 3.11 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 38.39 | 3.69 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.76 | 3.11 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 38.39 | 3.69 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.76 | 3.11 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 38.39 | 3.69 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.76 | 3.11 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 38.39 | 3.69 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 12.76 | 3.11 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 38.39 | 3.69 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 24.28 | 5.00 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 38.39 | 3.69 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 24.07 | 4.97 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 69.63 | 6.26 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 39.84 | 9.86 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 77.38 | 8.99 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 85.90 | 20.39 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 28.49 | 9.23 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 17.21 | 9.85 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x170` | 60.95 | 5.81 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 14.65 | 2.27 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 30.18 | 3.91 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 35.28 | 1.78 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 30.18 | 3.91 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 35.28 | 1.78 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 30.18 | 3.91 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 35.28 | 1.78 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 30.18 | 3.91 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 35.28 | 1.78 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 30.18 | 3.91 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 35.28 | 1.78 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 13.62 | 5.43 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 32.68 | 1.99 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 74.15 | 4.49 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 63.00 | 2.20 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 46.81 | 4.72 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 79.11 | 2.36 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 15.06 | 4.37 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 83.67 | 2.43 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 42.30 | 5.93 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 19.90 | 6.70 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 42.30 | 5.93 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 19.90 | 6.70 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 42.30 | 5.93 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 19.90 | 6.70 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 42.30 | 5.93 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 19.90 | 6.70 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 42.30 | 5.93 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 12.06 | 6.81 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 42.30 | 5.93 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 11.72 | 6.64 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 39.22 | 6.05 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 11.77 | 6.67 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 34.19 | 7.02 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 18.92 | 12.98 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 33.59 | 10.52 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 39.40 | 26.58 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 15.53 | 9.83 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 16.42 | 22.39 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 40.44 | 6.01 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 12.83 | 7.13 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 40.44 | 6.01 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 12.83 | 7.13 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 40.44 | 6.01 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 12.83 | 7.13 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 40.44 | 6.01 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 12.83 | 7.13 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 40.44 | 6.01 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 12.56 | 7.00 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 40.44 | 6.01 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 12.17 | 6.81 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 40.20 | 5.99 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 12.23 | 6.84 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 35.27 | 6.99 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 21.19 | 14.45 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 35.45 | 10.71 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 52.44 | 35.22 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.19 | 9.99 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 23.75 | 32.64 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 47.10 | 5.10 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 16.01 | 3.46 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 47.10 | 5.10 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 15.91 | 3.00 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 47.10 | 5.10 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 15.91 | 3.00 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 47.10 | 5.10 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 15.91 | 3.00 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 47.10 | 5.10 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 15.91 | 3.00 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 47.10 | 5.10 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 29.73 | 4.46 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 47.10 | 5.10 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 27.84 | 4.91 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 71.74 | 7.91 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 64.22 | 9.56 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 55.89 | 10.27 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 90.77 | 13.08 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 21.14 | 9.84 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 26.19 | 10.34 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 50.77 | 4.74 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 16.75 | 5.43 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 50.77 | 4.74 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 16.75 | 5.43 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 50.77 | 4.74 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 16.75 | 5.43 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 50.77 | 4.74 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 16.75 | 5.43 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 50.77 | 4.74 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 16.75 | 5.43 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 50.77 | 4.74 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 16.52 | 5.32 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 50.77 | 4.74 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 30.17 | 8.95 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 81.87 | 7.91 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 47.06 | 17.65 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 67.84 | 10.84 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 51.60 | 25.40 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 24.86 | 10.36 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 41.45 | 28.69 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 49.47 | 4.97 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 17.01 | 5.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 49.47 | 4.97 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 17.01 | 5.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 49.47 | 4.97 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 17.01 | 5.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 49.47 | 4.97 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 17.01 | 5.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 49.47 | 4.97 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 17.01 | 5.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 49.47 | 4.97 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 16.77 | 5.34 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 49.47 | 4.97 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 31.87 | 9.36 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 83.68 | 7.92 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 49.22 | 18.34 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 70.15 | 10.95 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 30.39 | 21.17 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 25.60 | 10.47 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 26.24 | 21.77 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 33.23 | 5.27 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 19.88 | 2.82 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 34.81 | 4.57 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 5.00 | 2.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 34.81 | 4.57 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 5.00 | 2.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 34.81 | 4.57 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 5.00 | 2.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 34.81 | 4.57 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 5.00 | 2.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x70` | 39.21 | 4.28 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.97 | 2.64 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 27.84 | 4.76 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 8.17 | 3.64 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 24.30 | 5.55 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 11.18 | 5.58 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 23.85 | 8.15 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 17.67 | 8.21 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 12.60 | 8.44 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 17.70 | 3.40 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340` | 34.93 | 5.24 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 15.89 | 2.38 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 40.20 | 5.03 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 25.39 | 1.74 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 40.20 | 5.03 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 25.39 | 1.74 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 40.20 | 5.03 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 25.39 | 1.74 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 40.20 | 5.03 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 25.39 | 1.74 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 40.20 | 5.03 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 25.39 | 1.74 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 40.20 | 5.03 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 5.66 | 2.26 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 63.50 | 6.60 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 67.87 | 2.64 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 48.62 | 8.37 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 117.44 | 3.32 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 19.03 | 8.52 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 139.08 | 3.71 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | 42.08 | 6.15 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 20.04 | 2.99 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 43.79 | 6.18 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 19.24 | 2.46 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 43.79 | 6.18 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 19.24 | 2.46 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 43.79 | 6.18 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 19.24 | 2.46 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 43.79 | 6.18 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 19.24 | 2.46 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 43.79 | 6.18 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 35.54 | 3.28 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 18.17 | 4.36 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 37.93 | 3.72 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 28.65 | 7.15 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 40.04 | 5.21 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 25.55 | 9.71 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 51.29 | 5.98 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 20.47 | 7.08 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 27.84 | 4.98 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 20.39 | 4.73 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 21.60 | 2.67 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 31.31 | 2.03 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 31.31 | 2.03 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 31.31 | 2.03 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 31.31 | 2.03 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 31.31 | 2.03 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 31.31 | 2.03 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 71.92 | 2.85 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 104.64 | 3.53 | yes | -- |
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
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
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
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x61` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-hybrid-x340` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x170` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
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
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-array-hw-hybrid-x141-romfill` | yes |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-array-hw-tensor-x125` | yes |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-wafer-tensor-x2` | yes |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-wafer-tensor-x2` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x68` | yes | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | `ROM-N5-native-HBMKV-wafer-tensor-x2` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-wafer-tensor-x2` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x68` | yes | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x87` | yes | `ROM-N6-native-HBMKV-array-hw-tensor-x72` | `ROM-N6-native-HBMKV-array-hw-tensor-x87` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | no |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-wafer-tensor-x2` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | no |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-wafer-tensor-x2` | yes |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `ROM-N6-native-SRAMKV-wafer-hybrid-x7` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `ROM-N6-native-SRAMKV-wafer-hybrid-x8` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | yes |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | no |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | no |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | no |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-array-hw-hybrid-x38` | yes |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-tensor-x44` | yes |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | yes |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | yes |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | yes |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | yes |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-wafer-tensor-x3` | yes |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x21` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | yes |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-array-hw-tensor-x32` | yes |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-array-hw-hybrid-x208` | yes |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-tensor-x3` | yes |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-tensor-x3` | yes |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | no |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x44` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-tensor-x45` | yes |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x44` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | yes |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | yes |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-tensor-x4` | yes |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-tensor-x4` | yes |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x35` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-array-hw-hybrid-x56` | yes |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399-romfill` | yes |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-hybrid-x79-romfill` | no |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | yes |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | yes | `--` | `--` | the drafter does not apply to this model |

**The rule reproduces the published autoregressive recommendation on 56 of 56 model-and-study rows.** Of the 42 rows where it reproduces and the drafter applies, verifying a block moves the chosen rung on 35. Where it moves, it moves toward machines with compute headroom for a block, which is exactly what the arithmetic predicts: a verification pass raises arithmetic intensity by the block size, and a machine sized with just enough compute for one token per sweep has no room for it. **This is a re-ranking of rungs that already exist. The speculative-optimal design has not been computed: that would need the area split re-solved, which is `balanced_area_split`'s job and not this layer's.**

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

