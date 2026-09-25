# Speculative decoding on the area-constrained roofline: released_dspark

> DeepSeek-V4's own speculative module, as shipped. Every figure below is derived from the roofline artifacts
> this repository has already published, by re-assembling each point's own five
> critical-path terms for a speculative cycle. Nothing here re-runs the machine
> model, and nothing here invents an acceptance rate.

## What this layer says

1. **Every term the speculative arithmetic needs is already in the published artifact, exactly.** 183,227 feasible points across 52 studies were rebuilt from their own five critical-path terms and every one reproduced its published step time to 1e-9 relative. Nothing here re-ran the machine model, and the layer is additive by construction rather than by promise.
2. **The headline is a break-even, not a speedup.** `tau* = T_cycle / step_time_s`, and `tau <= gamma+1` always. Of 245,677 (point, draft-placement) pairs where this profile's drafter applies, 86,976 (35.4%) cannot be sped up by speculation at ANY acceptance rate, at any block size on the ladder, even charging the drafter no KV traffic at all.
3. **The ROM-versus-GPU ratio under speculation carries no acceptance rate.** It is `T_cycle(GPU) / T_cycle(ROM)`: `tau` is a property of the model and its drafter, not of the machine, so it is identical on both sides and cancels. Every movement this report shows is a machine effect and nothing else, which is why it can be published without inventing an acceptance rate.
4. **The ratio moves, and it mostly compresses.** Across 775 model-context-batch-class rows, 775 move the ROM-versus-GPU per-user ratio DOWN under speculation and 0 move it UP, spanning 0.016x to 0.920x. The ROM advantage compresses on most operating points.
5. **At batch 1 the two extremes are opposite in sign, and they are the result.** DeepSeek-V4.1-Flash on `array` silicon goes from 7.10x to 0.18x -- a 0.025x movement -- while MiMo-V2.6-Flash on `wafer` silicon goes from 16.28x to 7.33x, a 0.451x movement. A layer that multiplied both sides by `tau` would have reported neither.
6. **A moving ratio is not a win for either side, and the report says so on every table.** At the most favourable sourced acceptance (5.00) speculation is worth having on 14 of 777 ROM class rows and 757 of 777 GPU rows; everywhere else the design runs SLOWER with a drafter than without one. Where both sides lose, a rising ratio means only that the comparator lost more.
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
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 574 | 0 | 1.15 | 1.46 | 5.88 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,075 | 412 | 1.16 | 6.93 | 65.78 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 64 | 0 | 1.17 | 2.41 | 4.59 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 407 | 2 | 1.91 | 2.67 | 22.66 |
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
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 1 | 1 | 8.17 | 8.17 | 8.17 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 762 | 245 | 1.32 | 4.87 | 65.77 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 557 | 1 | 1.35 | 2.72 | 22.17 |
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
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 601 | 0 | 1.15 | 1.45 | 5.79 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,103 | 399 | 1.16 | 6.76 | 65.78 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 61 | 0 | 1.19 | 2.46 | 4.37 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 407 | 0 | 2.02 | 2.65 | 6.89 |
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
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 2 | 0 | 6.71 | 6.72 | 6.72 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 811 | 251 | 1.32 | 4.56 | 65.72 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 574 | 0 | 1.64 | 2.67 | 12.16 |
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
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 554 | 0 | 1.15 | 1.47 | 5.89 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,032 | 399 | 1.16 | 7.02 | 65.78 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 62 | 0 | 1.17 | 2.43 | 4.62 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 402 | 4 | 1.72 | 2.67 | 26.39 |
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
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 2 | 2 | 8.14 | 8.31 | 8.31 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 707 | 224 | 1.32 | 4.76 | 65.74 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 521 | 1 | 1.36 | 2.72 | 21.63 |
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
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `layer_fixed_latency` | 705 | 0 | 1.15 | 1.45 | 6.63 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,434 | 536 | 1.16 | 6.70 | 65.79 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 76 | 0 | 1.17 | 2.64 | 4.59 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 525 | 4 | 1.91 | 2.67 | 22.66 |
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
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 3 | 2 | 7.62 | 8.17 | 8.18 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,032 | 324 | 1.32 | 4.63 | 65.77 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 725 | 2 | 1.38 | 2.72 | 22.17 |
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
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `layer_fixed_latency` | 735 | 0 | 1.15 | 1.45 | 6.50 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,542 | 552 | 1.16 | 6.48 | 65.78 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 76 | 0 | 1.19 | 2.78 | 4.37 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 535 | 0 | 1.99 | 2.65 | 7.21 |
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
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 1 | 0 | 6.71 | 6.71 | 6.71 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,049 | 316 | 1.32 | 4.27 | 65.71 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 701 | 0 | 1.52 | 2.70 | 12.27 |
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
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `layer_fixed_latency` | 657 | 0 | 1.15 | 1.45 | 6.07 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,381 | 516 | 1.16 | 6.64 | 65.79 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 71 | 0 | 1.17 | 2.66 | 4.62 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 511 | 6 | 1.72 | 2.67 | 26.39 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 842 | 235 | 4.70 | 7.49 | 15.89 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 846 | 100 | 1.48 | 4.15 | 10.50 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 936 | 120 | 1.47 | 2.63 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 664 | 129 | 1.06 | 5.38 | 16.41 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 842 | 842 | 8.16 | 35.25 | 135.06 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 846 | 438 | 2.22 | 8.17 | 75.38 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 936 | 282 | 1.58 | 6.05 | 41.23 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 664 | 611 | 5.53 | 18.90 | 181.83 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 3 | 3 | 8.14 | 8.18 | 8.31 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 973 | 305 | 1.32 | 4.63 | 65.75 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 694 | 2 | 1.34 | 2.73 | 21.63 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 796 | 299 | 5.09 | 8.22 | 25.48 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 740 | 98 | 1.48 | 4.85 | 18.28 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 909 | 114 | 1.47 | 2.67 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 533 | 153 | 1.06 | 6.62 | 22.80 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 796 | 794 | 7.33 | 44.58 | 146.75 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 740 | 410 | 2.37 | 8.19 | 84.88 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 909 | 228 | 1.60 | 5.62 | 37.29 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 533 | 494 | 5.68 | 19.92 | 181.83 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `layer_fixed_latency` | 566 | 0 | 1.16 | 1.52 | 6.63 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 910 | 373 | 1.16 | 7.50 | 65.79 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `thermal` | 65 | 0 | 1.17 | 2.25 | 4.49 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 399 | 5 | 1.87 | 2.67 | 23.43 |
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
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `compute` | 5 | 4 | 7.62 | 8.18 | 8.19 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 787 | 274 | 1.32 | 5.38 | 65.77 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 648 | 3 | 1.38 | 2.68 | 16.71 |
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
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 115 | 0 | 1.21 | 1.47 | 16.65 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 396 | 0 | 1.11 | 1.37 | 8.01 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 604 | 162 | 1.12 | 4.63 | 65.38 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 25 | 0 | 1.29 | 1.62 | 2.34 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 209 | 0 | 1.41 | 2.27 | 7.75 |
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
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 47 | 0 | 1.25 | 1.39 | 4.38 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 94 | 0 | 1.30 | 1.50 | 1.64 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 511 | 111 | 1.22 | 3.96 | 65.23 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 359 | 0 | 1.39 | 1.84 | 16.20 |
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
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 396 | 5 | 1.19 | 1.93 | 20.66 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 320 | 0 | 1.10 | 1.27 | 6.51 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 406 | 82 | 1.09 | 2.92 | 64.89 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 34 | 0 | 1.32 | 1.78 | 2.06 |
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
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 364 | 0 | 1.12 | 1.44 | 19.05 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 454 | 49 | 1.10 | 1.87 | 61.98 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 37 | 0 | 1.72 | 3.08 | 6.53 |
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
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 18 | 0 | 2.81 | 3.73 | 4.87 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 435 | 0 | 1.11 | 1.48 | 8.54 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 597 | 248 | 1.13 | 7.43 | 65.49 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 35 | 0 | 1.13 | 1.19 | 1.55 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 325 | 0 | 1.40 | 2.46 | 12.81 |
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
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `compute` | 19 | 0 | 5.57 | 6.46 | 7.97 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 106 | 0 | 1.44 | 1.60 | 1.83 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 605 | 236 | 1.33 | 6.36 | 65.48 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 630 | 2 | 1.12 | 2.26 | 17.89 |
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
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 65 | 0 | 1.28 | 1.61 | 2.71 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `layer_fixed_latency` | 298 | 0 | 1.12 | 1.44 | 6.18 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 523 | 125 | 1.11 | 4.66 | 64.87 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 17 | 0 | 1.28 | 2.59 | 2.98 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 200 | 0 | 1.71 | 2.27 | 13.37 |
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
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 364 | 71 | 1.49 | 3.56 | 64.63 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 392 | 0 | 1.19 | 1.91 | 16.33 |
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
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 349 | 0 | 1.26 | 1.95 | 14.92 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `layer_fixed_latency` | 233 | 0 | 1.11 | 1.28 | 5.72 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 708 | 98 | 1.06 | 2.78 | 62.97 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 22 | 0 | 1.48 | 2.06 | 2.08 |
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
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 294 | 0 | 1.15 | 1.47 | 17.03 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 407 | 45 | 1.43 | 2.00 | 58.79 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 162 | 0 | 1.07 | 2.08 | 12.50 |
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
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 2 | 0 | 3.98 | 4.47 | 4.47 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `layer_fixed_latency` | 499 | 0 | 1.12 | 1.51 | 7.28 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 942 | 339 | 1.16 | 6.19 | 65.02 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 44 | 0 | 1.14 | 1.65 | 2.87 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 453 | 3 | 1.48 | 2.43 | 21.72 |
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
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `compute` | 2 | 0 | 5.89 | 6.99 | 6.99 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 571 | 198 | 1.50 | 5.70 | 65.00 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 666 | 1 | 1.20 | 2.12 | 18.94 |
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
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `layer_fixed_latency` | 203 | 0 | 1.94 | 2.06 | 2.97 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 864 | 325 | 1.66 | 7.32 | 60.93 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 10 | 0 | 1.97 | 2.27 | 2.54 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 304 | 0 | 2.29 | 2.67 | 4.93 |
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
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `layer_fixed_latency` | 410 | 0 | 1.26 | 1.57 | 4.55 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 861 | 365 | 1.23 | 7.78 | 65.62 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 44 | 0 | 1.23 | 1.39 | 2.25 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 335 | 0 | 2.32 | 2.66 | 11.25 |
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
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `layer_fixed_latency` | 416 | 0 | 1.25 | 1.60 | 4.47 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 784 | 344 | 1.21 | 7.92 | 65.63 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 44 | 0 | 1.23 | 1.42 | 4.62 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 336 | 2 | 2.13 | 2.74 | 14.83 |
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
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `layer_fixed_latency` | 381 | 0 | 1.49 | 1.85 | 2.60 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,239 | 518 | 1.41 | 7.78 | 64.82 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 60 | 0 | 1.55 | 3.46 | 4.73 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 475 | 0 | 2.56 | 2.94 | 4.72 |
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
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `layer_fixed_latency` | 377 | 0 | 1.37 | 1.74 | 3.47 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,135 | 459 | 1.30 | 7.71 | 65.13 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 59 | 0 | 1.22 | 2.92 | 4.79 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 399 | 0 | 2.37 | 2.95 | 8.57 |
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
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `layer_fixed_latency` | 350 | 0 | 1.34 | 1.74 | 3.46 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,028 | 411 | 1.29 | 7.70 | 65.09 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 56 | 0 | 1.25 | 2.92 | 4.80 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 386 | 2 | 2.33 | 2.94 | 18.98 |
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
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 669 | 249 | 2.05 | 6.90 | 51.19 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 298 | 0 | 2.52 | 2.95 | 11.16 |
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
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 2 | 1 | 7.65 | 8.20 | 8.20 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 949 | 316 | 1.40 | 6.09 | 65.56 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 489 | 0 | 1.44 | 3.03 | 7.17 |
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
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 882 | 292 | 1.39 | 6.07 | 65.57 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 507 | 0 | 1.40 | 2.98 | 12.14 |
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
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 536 | 285 | 2.56 | 8.27 | 63.65 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 727 | 0 | 1.65 | 3.11 | 5.88 |
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
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 475 | 266 | 3.15 | 8.27 | 64.87 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 724 | 1 | 1.45 | 3.09 | 14.91 |
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
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 1 | 1 | 8.37 | 8.37 | 8.37 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 482 | 284 | 2.83 | 8.35 | 65.08 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 797 | 1 | 1.45 | 3.09 | 19.11 |
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
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `layer_fixed_latency` | 291 | 0 | 1.39 | 1.64 | 2.63 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 818 | 312 | 1.32 | 7.43 | 65.31 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 24 | 0 | 1.23 | 1.56 | 2.23 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 300 | 0 | 2.29 | 2.55 | 3.66 |
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
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `layer_fixed_latency` | 154 | 0 | 2.14 | 2.26 | 2.71 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 977 | 386 | 1.68 | 7.47 | 59.78 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 20 | 0 | 3.35 | 4.13 | 4.41 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 335 | 0 | 2.55 | 2.89 | 5.91 |
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
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 853 | 288 | 1.56 | 6.03 | 64.63 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 406 | 0 | 1.77 | 3.05 | 5.58 |
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
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 568 | 228 | 1.94 | 7.70 | 50.89 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 399 | 0 | 2.56 | 3.34 | 12.47 |
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
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,228.3 | 665.8-665.8 | 39.26 | **no** | `b200_sxm-x93-nvl72-hybrid` | 697.7 | 2,980.8-2,980.8 | 1.17 | yes | 7.493x | 0.223x | 0.030x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,338.7 | 699.2-699.2 | 38.18 | **no** | `b200_sxm-x87-nvl72-hybrid` | 696.4 | 2,967.0-2,967.0 | 1.17 | yes | 7.666x | 0.236x | 0.031x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,228.3 | 665.8-665.8 | 39.26 | **no** | `b200_sxm-x93-nvl72-hybrid` | 697.7 | 2,980.8-2,980.8 | 1.17 | yes | 7.493x | 0.223x | 0.030x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,338.7 | 699.2-699.2 | 38.18 | **no** | `b200_sxm-x87-nvl72-hybrid` | 696.4 | 2,967.0-2,967.0 | 1.17 | yes | 7.666x | 0.236x | 0.031x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,228.3 | 665.8-665.8 | 39.26 | **no** | `b200_sxm-x93-nvl72-hybrid` | 686.9 | 2,773.4-2,773.4 | 1.24 | yes | 7.611x | 0.240x | 0.032x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,338.7 | 699.2-699.2 | 38.18 | **no** | `b200_sxm-x87-nvl72-hybrid` | 685.2 | 2,756.8-2,756.8 | 1.24 | yes | 7.791x | 0.254x | 0.033x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,228.3 | 665.8-665.8 | 39.26 | **no** | `b200_sxm-x93-nvl72-hybrid` | 667.1 | 2,570.3-2,570.3 | 1.30 | yes | 7.837x | 0.259x | 0.033x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,338.7 | 699.2-699.2 | 38.18 | **no** | `b200_sxm-x87-nvl72-hybrid` | 664.3 | 2,545.1-2,545.1 | 1.31 | yes | 8.036x | 0.275x | 0.034x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,228.3 | 665.8-665.8 | 39.26 | **no** | `b200_sxm-x93-nvl72-hybrid` | 637.4 | 2,234.0-2,234.0 | 1.43 | yes | 8.202x | 0.298x | 0.036x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,338.7 | 699.2-699.2 | 38.18 | **no** | `b200_sxm-x87-nvl72-hybrid` | 635.9 | 2,211.3-2,211.3 | 1.44 | yes | 8.396x | 0.316x | 0.038x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,087.5 | 339.7-339.7 | 74.88 | **no** | `b200_sxm-x93-nvl72-hybrid` | 594.1 | 1,896.3-1,896.3 | 1.57 | yes | 8.564x | 0.179x | 0.021x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,204.7 | 845.0-845.0 | 30.80 | **no** | `b200_sxm-x231-nvl72-hybrid` | 641.2 | 2,264.3-2,264.3 | 1.42 | yes | 8.117x | 0.373x | 0.046x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 4,850.1 | 405.0-405.0 | 59.88 | **no** | `b200_sxm-x134-nvl72-hybrid` | 563.2 | 1,714.5-1,714.5 | 1.64 | yes | 8.611x | 0.236x | 0.027x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,201.5 | 840.4-840.4 | 30.95 | **no** | `b200_sxm-x347-nvl72-hybrid` | 618.6 | 2,069.5-2,069.5 | 1.49 | yes | 8.409x | 0.406x | 0.048x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 3,322.9 | 177.7-177.7 | 93.48 | **no** | `b200_sxm-x179-nvl72-hybrid` | 418.9 | 1,022.9-1,022.9 | 2.05 | yes | 7.933x | 0.174x | 0.022x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,179.1 | 422.8-422.8 | 49.42 | **no** | `b200_sxm-x347-nvl72-hybrid` | 501.3 | 1,358.8-1,358.8 | 1.84 | yes | 8.336x | 0.311x | 0.037x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 1,640.8 | 86.8-86.8 | 94.49 | **no** | `b200_sxm-x179-nvl72-hybrid` | 235.5 | 449.1-449.1 | 2.62 | yes | 6.967x | 0.193x | 0.028x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,147.3 | 107.6-107.6 | 99.83 | **no** | `b200_sxm-x347-nvl72-hybrid` | 302.6 | 685.5-685.5 | 2.21 | yes | 7.096x | 0.157x | 0.022x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 558.9 | 41.2-41.2 | 67.83 | **no** | `b200_sxm-x179-nvl72-hybrid` | 133.2 | 154.1-154.1 | 4.32 | yes | 4.194x | 0.267x | 0.064x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 685.8 | 85.1-85.1 | 40.30 | **no** | `b200_sxm-x347-nvl72-hybrid` | 159.6 | 202.5-202.5 | 3.94 | yes | 4.298x | 0.420x | 0.098x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.021x to 0.098x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 469.3-469.3 | 52.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 358.7 | 951.0-951.0 | 1.89 | yes | 13.806x | 0.494x | 0.036x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,055.1 | 533.3-533.3 | 47.40 | **no** | `a100_sxm_80gb-x224-hybrid` | 363.9 | 989.4-989.4 | 1.84 | yes | 13.893x | 0.539x | 0.039x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 469.3-469.3 | 52.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 358.7 | 951.0-951.0 | 1.89 | yes | 13.806x | 0.494x | 0.036x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,055.1 | 533.3-533.3 | 47.40 | **no** | `a100_sxm_80gb-x224-hybrid` | 363.9 | 989.4-989.4 | 1.84 | yes | 13.893x | 0.539x | 0.039x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 469.3-469.3 | 52.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 358.7 | 951.0-951.0 | 1.89 | yes | 13.806x | 0.494x | 0.036x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,055.1 | 533.3-533.3 | 47.40 | **no** | `a100_sxm_80gb-x224-hybrid` | 363.9 | 989.4-989.4 | 1.84 | yes | 13.893x | 0.539x | 0.039x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 469.3-469.3 | 52.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 358.7 | 951.0-951.0 | 1.89 | yes | 13.806x | 0.494x | 0.036x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,055.1 | 533.3-533.3 | 47.40 | **no** | `a100_sxm_80gb-x224-hybrid` | 363.9 | 989.4-989.4 | 1.84 | yes | 13.893x | 0.539x | 0.039x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 469.3-469.3 | 52.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 358.7 | 951.0-951.0 | 1.89 | yes | 13.806x | 0.494x | 0.036x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,055.1 | 533.3-533.3 | 47.40 | **no** | `a100_sxm_80gb-x224-hybrid` | 363.9 | 989.4-989.4 | 1.84 | yes | 13.893x | 0.539x | 0.039x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 469.3-469.3 | 52.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 358.7 | 951.0-951.0 | 1.89 | yes | 13.806x | 0.494x | 0.036x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4,931.7 | 615.8-615.8 | 40.04 | **no** | `a100_sxm_80gb-x448-hybrid` | 357.8 | 884.0-884.0 | 2.02 | yes | 13.783x | 0.697x | 0.051x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,669.0 | 238.2-238.2 | 98.00 | **no** | `a100_sxm_80gb-x258-hybrid` | 317.5 | 720.3-720.3 | 2.20 | yes | 14.706x | 0.331x | 0.022x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,927.4 | 612.4-612.4 | 40.23 | **no** | `a100_sxm_80gb-x672-hybrid` | 357.8 | 829.9-829.9 | 2.16 | yes | 13.771x | 0.738x | 0.054x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 2,994.5 | 93.1-93.1 | 160.87 | **no** | `a100_sxm_80gb-x335-hybrid` | 210.7 | 375.8-375.8 | 2.80 | yes | 14.212x | 0.248x | 0.017x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,673.9 | 306.3-306.3 | 59.97 | **no** | `a100_sxm_80gb-x672-hybrid` | 278.5 | 514.8-514.8 | 2.70 | yes | 13.191x | 0.595x | 0.045x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,194.1 | 45.2-45.2 | 132.17 | **no** | `a100_sxm_80gb-x337-hybrid` | 94.1 | 176.9-176.9 | 2.66 | yes | 12.692x | 0.255x | 0.020x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,680.0 | 91.2-91.2 | 92.07 | **no** | `a100_sxm_80gb-x672-hybrid` | 144.9 | 249.0-249.0 | 2.91 | yes | 11.596x | 0.366x | 0.032x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 331.5 | 39.0-39.0 | 42.48 | **no** | `a100_sxm_80gb-x337-hybrid` | 36.8 | 49.1-49.1 | 3.75 | yes | 9.020x | 0.795x | 0.088x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 606.9 | 44.2-44.2 | 68.71 | **no** | `a100_sxm_80gb-x672-hybrid` | 57.8 | 115.4-115.4 | 2.51 | yes | 10.492x | 0.383x | 0.036x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.017x to 0.088x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,977.8 | 530.7-530.7 | 46.90 | **no** | `b200_sxm-x116-nvl72-hybrid` | 701.2 | 3,019.6-3,019.6 | 1.16 | yes | 7.099x | 0.176x | 0.025x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,818.5 | 844.0-844.0 | 28.55 | **no** | `b200_sxm-x144-nvl72-hybrid` | 704.1 | 3,045.9-3,045.9 | 1.16 | yes | 6.844x | 0.277x | 0.040x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,977.8 | 530.7-530.7 | 46.90 | **no** | `b200_sxm-x116-nvl72-hybrid` | 701.2 | 3,019.6-3,019.6 | 1.16 | yes | 7.099x | 0.176x | 0.025x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,818.5 | 844.0-844.0 | 28.55 | **no** | `b200_sxm-x144-nvl72-hybrid` | 704.1 | 3,045.9-3,045.9 | 1.16 | yes | 6.844x | 0.277x | 0.040x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,977.8 | 530.7-530.7 | 46.90 | **no** | `b200_sxm-x116-nvl72-hybrid` | 691.3 | 2,819.5-2,819.5 | 1.23 | yes | 7.200x | 0.188x | 0.026x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,818.5 | 844.0-844.0 | 28.55 | **no** | `b200_sxm-x144-nvl72-hybrid` | 695.0 | 2,849.0-2,849.0 | 1.22 | yes | 6.933x | 0.296x | 0.043x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,977.8 | 530.7-530.7 | 46.90 | **no** | `b200_sxm-x116-nvl72-hybrid` | 672.6 | 2,511.5-2,511.5 | 1.34 | yes | 7.401x | 0.211x | 0.029x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,818.5 | 844.0-844.0 | 28.55 | **no** | `b200_sxm-x144-nvl72-hybrid` | 678.0 | 2,629.7-2,629.7 | 1.29 | yes | 7.107x | 0.321x | 0.045x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,977.8 | 530.7-530.7 | 46.90 | **no** | `b200_sxm-x116-nvl72-hybrid` | 645.7 | 2,341.0-2,341.0 | 1.38 | yes | 7.710x | 0.227x | 0.029x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,818.5 | 844.0-844.0 | 28.55 | **no** | `b200_sxm-x144-nvl72-hybrid` | 653.2 | 2,421.1-2,421.1 | 1.35 | yes | 7.377x | 0.349x | 0.047x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 4,903.9 | 470.3-470.3 | 52.14 | **no** | `b200_sxm-x134-nvl72-hybrid` | 615.5 | 2,064.7-2,064.7 | 1.49 | yes | 7.967x | 0.228x | 0.029x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,675.1 | 1,547.5-1,547.5 | 15.10 | **no** | `b200_sxm-x347-nvl72-hybrid` | 653.1 | 2,369.0-2,369.0 | 1.38 | yes | 7.158x | 0.653x | 0.091x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 4,584.6 | 238.8-238.8 | 96.01 | **no** | `b200_sxm-x134-nvl72-hybrid` | 558.8 | 1,705.0-1,705.0 | 1.64 | yes | 8.205x | 0.140x | 0.017x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,504.6 | 818.9-818.9 | 27.50 | **no** | `b200_sxm-x347-nvl72-hybrid` | 616.5 | 2,064.3-2,064.3 | 1.49 | yes | 7.307x | 0.397x | 0.054x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 3,058.6 | 174.8-174.8 | 87.47 | **no** | `b200_sxm-x179-nvl72-hybrid` | 411.5 | 1,012.3-1,012.3 | 2.03 | yes | 7.432x | 0.173x | 0.023x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,071.9 | 409.1-409.1 | 37.55 | **no** | `b200_sxm-x347-nvl72-hybrid` | 495.9 | 1,349.9-1,349.9 | 1.84 | yes | 6.195x | 0.303x | 0.049x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 1,269.4 | 44.2-44.2 | 143.71 | **no** | `b200_sxm-x179-nvl72-hybrid` | 226.5 | 442.2-442.2 | 2.56 | yes | 5.605x | 0.100x | 0.018x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,259.4 | 46.8-46.8 | 134.63 | **no** | `b200_sxm-x347-nvl72-hybrid` | 294.8 | 676.7-676.7 | 2.18 | yes | 4.272x | 0.069x | 0.016x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 363.9 | 38.7-38.7 | 46.97 | **no** | `b200_sxm-x179-nvl72-hybrid` | 122.2 | 150.9-150.9 | 4.05 | yes | 2.978x | 0.257x | 0.086x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 359.4 | 23.0-23.0 | 78.26 | **no** | `b200_sxm-x347-nvl72-hybrid` | 151.1 | 199.7-199.7 | 3.78 | yes | 2.378x | 0.115x | 0.048x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.016x to 0.091x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,695.2 | 753.2-753.2 | 31.17 | **no** | `a100_sxm_80gb-x312-hybrid` | 356.5 | 923.4-923.4 | 1.93 | yes | 13.172x | 0.816x | 0.062x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 4,457.6 | 1,269.8-1,269.8 | 17.55 | **no** | `a100_sxm_80gb-x168-hybrid` | 365.5 | 1,025.5-1,025.5 | 1.78 | yes | 12.194x | 1.238x | 0.102x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,695.2 | 753.2-753.2 | 31.17 | **no** | `a100_sxm_80gb-x312-hybrid` | 356.5 | 923.4-923.4 | 1.93 | yes | 13.172x | 0.816x | 0.062x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,256.3 | 699.4-699.4 | 30.43 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 827.7-827.7 | 2.15 | yes | 11.958x | 0.845x | 0.071x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,695.2 | 753.2-753.2 | 31.17 | **no** | `a100_sxm_80gb-x312-hybrid` | 356.5 | 923.4-923.4 | 1.93 | yes | 13.172x | 0.816x | 0.062x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,256.3 | 699.4-699.4 | 30.43 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 827.7-827.7 | 2.15 | yes | 11.958x | 0.845x | 0.071x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,695.2 | 753.2-753.2 | 31.17 | **no** | `a100_sxm_80gb-x312-hybrid` | 356.5 | 923.4-923.4 | 1.93 | yes | 13.172x | 0.816x | 0.062x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,256.3 | 699.4-699.4 | 30.43 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 827.7-827.7 | 2.15 | yes | 11.958x | 0.845x | 0.071x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,695.2 | 753.2-753.2 | 31.17 | **no** | `a100_sxm_80gb-x312-hybrid` | 356.5 | 923.4-923.4 | 1.93 | yes | 13.172x | 0.816x | 0.062x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,256.3 | 699.4-699.4 | 30.43 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 827.7-827.7 | 2.15 | yes | 11.958x | 0.845x | 0.071x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 4,658.6 | 362.2-362.2 | 64.31 | **no** | `a100_sxm_80gb-x337-hybrid` | 353.6 | 903.4-903.4 | 1.96 | yes | 13.174x | 0.401x | 0.030x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,142.7 | 367.5-367.5 | 56.36 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 827.7-827.7 | 2.15 | yes | 11.638x | 0.444x | 0.038x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 4,239.1 | 185.4-185.4 | 114.31 | **no** | `a100_sxm_80gb-x335-hybrid` | 330.5 | 773.7-773.7 | 2.14 | yes | 12.825x | 0.240x | 0.019x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,559.7 | 364.0-364.0 | 48.89 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 827.7-827.7 | 2.15 | yes | 10.001x | 0.440x | 0.044x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 2,465.2 | 91.3-91.3 | 134.94 | **no** | `a100_sxm_80gb-x337-hybrid` | 207.3 | 375.2-375.2 | 2.76 | yes | 11.891x | 0.243x | 0.020x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,875.7 | 93.6-93.6 | 100.18 | **no** | `a100_sxm_80gb-x672-hybrid` | 275.1 | 512.2-512.2 | 2.69 | yes | 6.817x | 0.183x | 0.027x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 833.5 | 44.0-44.0 | 94.67 | **no** | `a100_sxm_80gb-x337-hybrid` | 91.1 | 174.6-174.6 | 2.61 | yes | 9.154x | 0.252x | 0.028x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 597.6 | 23.6-23.6 | 126.73 | **no** | `a100_sxm_80gb-x672-hybrid` | 141.3 | 246.7-246.7 | 2.86 | yes | 4.231x | 0.096x | 0.023x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 223.3 | 35.7-35.7 | 31.23 | **no** | `a100_sxm_80gb-x337-hybrid` | 34.9 | 44.8-44.8 | 3.90 | yes | 6.390x | 0.798x | 0.125x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 156.6 | 22.5-22.5 | 34.78 | **no** | `a100_sxm_80gb-x672-hybrid` | 55.6 | 113.4-113.4 | 2.45 | yes | 2.819x | 0.198x | 0.070x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.019x to 0.125x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,280.8 | 696.2-696.2 | 37.93 | **no** | `b200_sxm-x90-nvl72-hybrid` | 697.2 | 2,974.4-2,974.4 | 1.17 | yes | 7.575x | 0.234x | 0.031x |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,479.0 | 703.6-703.6 | 38.93 | **no** | `b200_sxm-x87-nvl72-hybrid` | 696.5 | 2,967.3-2,967.3 | 1.17 | yes | 7.866x | 0.237x | 0.030x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,280.8 | 696.2-696.2 | 37.93 | **no** | `b200_sxm-x90-nvl72-hybrid` | 697.2 | 2,974.4-2,974.4 | 1.17 | yes | 7.575x | 0.234x | 0.031x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,479.0 | 703.6-703.6 | 38.93 | **no** | `b200_sxm-x87-nvl72-hybrid` | 696.5 | 2,967.3-2,967.3 | 1.17 | yes | 7.866x | 0.237x | 0.030x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,280.8 | 696.2-696.2 | 37.93 | **no** | `b200_sxm-x90-nvl72-hybrid` | 686.3 | 2,766.0-2,766.0 | 1.24 | yes | 7.695x | 0.252x | 0.033x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,479.0 | 703.6-703.6 | 38.93 | **no** | `b200_sxm-x87-nvl72-hybrid` | 685.4 | 2,757.5-2,757.5 | 1.24 | yes | 7.994x | 0.255x | 0.032x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,280.8 | 696.2-696.2 | 37.93 | **no** | `b200_sxm-x90-nvl72-hybrid` | 666.1 | 2,559.1-2,559.1 | 1.30 | yes | 7.929x | 0.272x | 0.034x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,479.0 | 703.6-703.6 | 38.93 | **no** | `b200_sxm-x87-nvl72-hybrid` | 664.6 | 2,546.1-2,546.1 | 1.31 | yes | 8.244x | 0.276x | 0.034x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,280.8 | 696.2-696.2 | 37.93 | **no** | `b200_sxm-x90-nvl72-hybrid` | 634.9 | 2,173.1-2,173.1 | 1.46 | yes | 8.317x | 0.320x | 0.039x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,479.0 | 703.6-703.6 | 38.93 | **no** | `b200_sxm-x87-nvl72-hybrid` | 636.4 | 2,212.9-2,212.9 | 1.44 | yes | 8.609x | 0.318x | 0.037x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,211.3 | 355.5-355.5 | 73.29 | **no** | `b200_sxm-x90-nvl72-hybrid` | 590.7 | 1,872.2-1,872.2 | 1.58 | yes | 8.822x | 0.190x | 0.022x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,349.8 | 851.9-851.9 | 31.40 | **no** | `b200_sxm-x231-nvl72-hybrid` | 641.6 | 2,265.6-2,265.6 | 1.42 | yes | 8.338x | 0.376x | 0.045x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 5,024.6 | 407.0-407.0 | 61.73 | **no** | `b200_sxm-x134-nvl72-hybrid` | 564.4 | 1,717.0-1,717.0 | 1.64 | yes | 8.903x | 0.237x | 0.027x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,346.7 | 847.1-847.1 | 31.56 | **no** | `b200_sxm-x347-nvl72-hybrid` | 619.1 | 2,070.9-2,070.9 | 1.49 | yes | 8.636x | 0.409x | 0.047x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 3,402.3 | 202.1-202.1 | 84.18 | **no** | `b200_sxm-x179-nvl72-hybrid` | 420.8 | 1,025.7-1,025.7 | 2.05 | yes | 8.086x | 0.197x | 0.024x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,457.5 | 427.1-427.1 | 52.19 | **no** | `b200_sxm-x347-nvl72-hybrid` | 502.8 | 1,361.2-1,361.2 | 1.85 | yes | 8.866x | 0.314x | 0.035x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,713.1 | 90.2-90.2 | 94.91 | **no** | `b200_sxm-x173-nvl72-hybrid` | 235.8 | 431.8-431.8 | 2.73 | yes | 7.265x | 0.209x | 0.029x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,433.4 | 108.5-108.5 | 112.14 | **no** | `b200_sxm-x347-nvl72-hybrid` | 304.7 | 687.7-687.7 | 2.22 | yes | 7.987x | 0.158x | 0.020x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 620.7 | 43.0-43.0 | 72.16 | **no** | `b200_sxm-x173-nvl72-hybrid` | 133.8 | 144.3-144.3 | 4.64 | yes | 4.639x | 0.298x | 0.064x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 769.7 | 93.5-93.5 | 41.16 | **no** | `b200_sxm-x347-nvl72-hybrid` | 161.9 | 203.3-203.3 | 3.98 | yes | 4.755x | 0.460x | 0.097x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.020x to 0.097x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 5,026.9 | 499.4-499.4 | 50.33 | **no** | `a100_sxm_80gb-x244-hybrid` | 361.0 | 966.0-966.0 | 1.87 | yes | 13.927x | 0.517x | 0.037x |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,233.2 | 536.6-536.6 | 48.76 | **no** | `a100_sxm_80gb-x224-hybrid` | 364.4 | 990.2-990.2 | 1.84 | yes | 14.362x | 0.542x | 0.038x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 5,026.9 | 499.4-499.4 | 50.33 | **no** | `a100_sxm_80gb-x244-hybrid` | 361.0 | 966.0-966.0 | 1.87 | yes | 13.927x | 0.517x | 0.037x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,233.2 | 536.6-536.6 | 48.76 | **no** | `a100_sxm_80gb-x224-hybrid` | 364.4 | 990.2-990.2 | 1.84 | yes | 14.362x | 0.542x | 0.038x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 5,026.9 | 499.4-499.4 | 50.33 | **no** | `a100_sxm_80gb-x244-hybrid` | 361.0 | 966.0-966.0 | 1.87 | yes | 13.927x | 0.517x | 0.037x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,233.2 | 536.6-536.6 | 48.76 | **no** | `a100_sxm_80gb-x224-hybrid` | 364.4 | 990.2-990.2 | 1.84 | yes | 14.362x | 0.542x | 0.038x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 5,026.9 | 499.4-499.4 | 50.33 | **no** | `a100_sxm_80gb-x244-hybrid` | 361.0 | 966.0-966.0 | 1.87 | yes | 13.927x | 0.517x | 0.037x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,233.2 | 536.6-536.6 | 48.76 | **no** | `a100_sxm_80gb-x224-hybrid` | 364.4 | 990.2-990.2 | 1.84 | yes | 14.362x | 0.542x | 0.038x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 5,026.9 | 499.4-499.4 | 50.33 | **no** | `a100_sxm_80gb-x244-hybrid` | 361.0 | 966.0-966.0 | 1.87 | yes | 13.927x | 0.517x | 0.037x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,233.2 | 536.6-536.6 | 48.76 | **no** | `a100_sxm_80gb-x224-hybrid` | 364.4 | 990.2-990.2 | 1.84 | yes | 14.362x | 0.542x | 0.038x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342-romfill` | 4,869.3 | 576.0-576.0 | 42.27 | **no** | `a100_sxm_80gb-x337-hybrid` | 356.0 | 906.7-906.7 | 1.96 | yes | 13.680x | 0.635x | 0.046x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,116.8 | 620.6-620.6 | 41.23 | **no** | `a100_sxm_80gb-x448-hybrid` | 358.3 | 884.6-884.6 | 2.03 | yes | 14.282x | 0.701x | 0.049x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 4,654.3 | 253.4-253.4 | 91.83 | **no** | `a100_sxm_80gb-x244-hybrid` | 315.5 | 711.1-711.1 | 2.22 | yes | 14.754x | 0.356x | 0.024x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,112.2 | 617.0-617.0 | 41.42 | **no** | `a100_sxm_80gb-x672-hybrid` | 358.3 | 830.5-830.5 | 2.16 | yes | 14.269x | 0.743x | 0.052x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,166.8 | 178.9-178.9 | 88.50 | **no** | `a100_sxm_80gb-x337-hybrid` | 212.2 | 378.7-378.7 | 2.80 | yes | 14.923x | 0.472x | 0.032x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,973.2 | 309.4-309.4 | 64.21 | **no** | `a100_sxm_80gb-x672-hybrid` | 279.4 | 515.5-515.5 | 2.71 | yes | 14.220x | 0.600x | 0.042x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,344.0 | 45.5-45.5 | 147.75 | **no** | `a100_sxm_80gb-x337-hybrid` | 94.9 | 177.5-177.5 | 2.67 | yes | 14.164x | 0.256x | 0.018x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,899.7 | 78.2-78.2 | 121.39 | **no** | `a100_sxm_80gb-x672-hybrid` | 145.8 | 249.6-249.6 | 2.92 | yes | 13.026x | 0.314x | 0.024x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 379.6 | 40.0-40.0 | 47.47 | **no** | `a100_sxm_80gb-x337-hybrid` | 37.2 | 50.3-50.3 | 3.70 | yes | 10.190x | 0.795x | 0.078x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 721.6 | 83.1-83.1 | 43.39 | **no** | `a100_sxm_80gb-x672-hybrid` | 58.5 | 115.9-115.9 | 2.52 | yes | 12.344x | 0.717x | 0.058x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.018x to 0.078x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 701.4 | 3,016.3-3,016.3 | 1.16 | yes | 7.658x | 0.404x | 0.053x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 5,419.7 | 1,222.8-1,222.8 | 22.16 | **no** | `b200_sxm-x347-nvl72-hybrid` | 699.4 | 2,970.8-2,970.8 | 1.18 | yes | 7.749x | 0.412x | 0.053x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 691.5 | 2,826.1-2,826.1 | 1.22 | yes | 7.767x | 0.431x | 0.055x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 1,289.0-1,289.0 | 20.83 | **no** | `b200_sxm-x58-nvl72-tensor` | 694.8 | 2,856.4-2,856.4 | 1.22 | yes | 7.728x | 0.451x | 0.058x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 672.8 | 2,516.7-2,516.7 | 1.34 | yes | 7.983x | 0.484x | 0.061x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 1,289.0-1,289.0 | 20.83 | **no** | `b200_sxm-x58-nvl72-tensor` | 677.4 | 2,552.9-2,552.9 | 1.33 | yes | 7.927x | 0.505x | 0.064x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 639.3 | 2,089.9-2,089.9 | 1.53 | yes | 8.402x | 0.583x | 0.069x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 1,289.0-1,289.0 | 20.83 | **no** | `b200_sxm-x58-nvl72-tensor` | 645.9 | 2,125.0-2,125.0 | 1.52 | yes | 8.314x | 0.607x | 0.073x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,361.8 | 632.2-632.2 | 42.40 | **no** | `b200_sxm-x49-hybrid` | 590.3 | 1,816.2-1,816.2 | 1.63 | yes | 9.083x | 0.348x | 0.038x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5,363.4 | 1,315.6-1,315.6 | 20.38 | **no** | `b200_sxm-x87-nvl72-hybrid` | 635.9 | 2,211.3-2,211.3 | 1.44 | yes | 8.435x | 0.595x | 0.071x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 5,209.0 | 657.3-657.3 | 39.62 | **no** | `b200_sxm-x110-nvl72-hybrid` | 606.5 | 1,984.7-1,984.7 | 1.53 | yes | 8.589x | 0.331x | 0.039x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,337.0 | 1,350.1-1,350.1 | 19.77 | **no** | `b200_sxm-x231-nvl72-hybrid` | 641.2 | 2,264.3-2,264.3 | 1.42 | yes | 8.323x | 0.596x | 0.072x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,209.0 | 657.3-657.3 | 39.62 | **no** | `b200_sxm-x173-nvl72-hybrid` | 583.0 | 1,825.3-1,825.3 | 1.60 | yes | 8.934x | 0.360x | 0.040x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,334.9 | 1,342.9-1,342.9 | 19.86 | **no** | `b200_sxm-x347-nvl72-hybrid` | 618.6 | 2,069.5-2,069.5 | 1.49 | yes | 8.625x | 0.649x | 0.075x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,572.7 | 325.7-325.7 | 54.84 | **no** | `b200_sxm-x173-nvl72-hybrid` | 414.3 | 1,013.7-1,013.7 | 2.04 | yes | 8.624x | 0.321x | 0.037x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,536.9 | 684.4-684.4 | 33.15 | **no** | `b200_sxm-x347-nvl72-hybrid` | 501.3 | 1,358.8-1,358.8 | 1.84 | yes | 9.050x | 0.504x | 0.056x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,474.7 | 152.9-152.9 | 48.23 | **no** | `b200_sxm-x173-nvl72-hybrid` | 233.3 | 430.1-430.1 | 2.71 | yes | 6.320x | 0.355x | 0.056x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,637.2 | 175.8-175.8 | 74.99 | **no** | `b200_sxm-x347-nvl72-hybrid` | 302.6 | 685.5-685.5 | 2.21 | yes | 8.715x | 0.257x | 0.029x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 434.2 | 127.1-127.1 | 17.08 | **no** | `b200_sxm-x173-nvl72-hybrid` | 130.7 | 143.6-143.6 | 4.55 | yes | 3.323x | 0.886x | 0.267x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 872.6 | 144.5-144.5 | 30.20 | **no** | `b200_sxm-x347-nvl72-hybrid` | 159.6 | 202.5-202.5 | 3.94 | yes | 5.469x | 0.713x | 0.130x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.029x to 0.267x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 366.0 | 1,031.9-1,031.9 | 1.77 | yes | 14.085x | 0.850x | 0.060x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 5,184.8 | 863.6-863.6 | 30.02 | **no** | `a100_sxm_80gb-x672-hybrid` | 357.8 | 829.9-829.9 | 2.16 | yes | 14.491x | 1.041x | 0.072x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 366.0 | 1,031.9-1,031.9 | 1.77 | yes | 14.085x | 0.850x | 0.060x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.0 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 13.867x | 0.939x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 366.0 | 1,031.9-1,031.9 | 1.77 | yes | 14.085x | 0.850x | 0.060x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.0 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 13.867x | 0.939x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 366.0 | 1,031.9-1,031.9 | 1.77 | yes | 14.085x | 0.850x | 0.060x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.0 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 13.867x | 0.939x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 366.0 | 1,031.9-1,031.9 | 1.77 | yes | 14.085x | 0.850x | 0.060x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.0 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 13.867x | 0.939x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,021.1 | 916.5-916.5 | 27.39 | **no** | `a100_sxm_80gb-x272-hybrid` | 360.8 | 954.3-954.3 | 1.89 | yes | 13.916x | 0.960x | 0.069x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,079.3 | 992.0-992.0 | 25.60 | **no** | `a100_sxm_80gb-x448-hybrid` | 357.8 | 884.0-884.0 | 2.02 | yes | 14.196x | 1.122x | 0.079x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,830.1 | 478.9-478.9 | 50.43 | **no** | `a100_sxm_80gb-x335-hybrid` | 333.0 | 776.7-776.7 | 2.14 | yes | 14.506x | 0.617x | 0.043x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,076.0 | 986.6-986.6 | 25.72 | **no** | `a100_sxm_80gb-x672-hybrid` | 357.8 | 829.9-829.9 | 2.16 | yes | 14.187x | 1.189x | 0.084x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,068.8 | 236.2-236.2 | 64.96 | **no** | `a100_sxm_80gb-x335-hybrid` | 210.7 | 375.8-375.8 | 2.80 | yes | 14.565x | 0.629x | 0.043x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,987.7 | 497.6-497.6 | 40.07 | **no** | `a100_sxm_80gb-x672-hybrid` | 278.5 | 514.8-514.8 | 2.70 | yes | 14.317x | 0.967x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 1,176.6 | 163.6-163.6 | 35.96 | **no** | `a100_sxm_80gb-x335-hybrid` | 93.8 | 176.4-176.4 | 2.66 | yes | 12.548x | 0.927x | 0.074x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,977.6 | 127.0-127.0 | 77.84 | **no** | `a100_sxm_80gb-x672-hybrid` | 144.9 | 249.0-249.0 | 2.91 | yes | 13.650x | 0.510x | 0.037x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 428.3 | 114.1-114.1 | 18.76 | **no** | `a100_sxm_80gb-x335-hybrid` | 36.7 | 48.2-48.2 | 3.80 | yes | 11.682x | 2.368x | 0.203x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 602.7 | 104.5-104.5 | 28.84 | **no** | `a100_sxm_80gb-x672-hybrid` | 57.8 | 115.4-115.4 | 2.51 | yes | 10.419x | 0.906x | 0.087x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.037x to 0.203x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 5,145.7 | 1,045.1-1,045.1 | 24.62 | **no** | `b200_sxm-x57-nvl72-tensor` | 703.5 | 3,038.7-3,038.7 | 1.16 | yes | 7.314x | 0.344x | 0.047x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 5,125.9 | 1,195.8-1,195.8 | 21.43 | **no** | `b200_sxm-x347-nvl72-hybrid` | 699.2 | 2,970.0-2,970.0 | 1.18 | yes | 7.331x | 0.403x | 0.055x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 5,145.7 | 1,045.1-1,045.1 | 24.62 | **no** | `b200_sxm-x57-nvl72-tensor` | 694.0 | 2,851.7-2,851.7 | 1.22 | yes | 7.414x | 0.366x | 0.049x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,830.4 | 848.3-848.3 | 28.47 | **no** | `b200_sxm-x144-nvl72-hybrid` | 704.1 | 3,045.9-3,045.9 | 1.16 | yes | 6.861x | 0.278x | 0.041x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 5,145.7 | 1,045.1-1,045.1 | 24.62 | **no** | `b200_sxm-x57-nvl72-tensor` | 676.0 | 2,546.4-2,546.4 | 1.33 | yes | 7.612x | 0.410x | 0.054x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,830.4 | 848.3-848.3 | 28.47 | **no** | `b200_sxm-x144-nvl72-hybrid` | 695.0 | 2,849.0-2,849.0 | 1.22 | yes | 6.950x | 0.298x | 0.043x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 5,145.7 | 1,045.1-1,045.1 | 24.62 | **no** | `b200_sxm-x57-nvl72-tensor` | 643.5 | 2,117.5-2,117.5 | 1.52 | yes | 7.996x | 0.494x | 0.062x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,830.4 | 848.3-848.3 | 28.47 | **no** | `b200_sxm-x144-nvl72-hybrid` | 678.0 | 2,629.7-2,629.7 | 1.29 | yes | 7.125x | 0.323x | 0.045x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 4,966.0 | 1,194.7-1,194.7 | 20.78 | **no** | `b200_sxm-x83-nvl72-hybrid` | 628.5 | 2,168.7-2,168.7 | 1.45 | yes | 7.901x | 0.551x | 0.070x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,830.4 | 848.3-848.3 | 28.47 | **no** | `b200_sxm-x144-nvl72-hybrid` | 653.2 | 2,421.1-2,421.1 | 1.35 | yes | 7.395x | 0.350x | 0.047x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,887.4 | 1,216.4-1,216.4 | 20.09 | **no** | `b200_sxm-x173-nvl72-hybrid` | 626.7 | 2,163.5-2,163.5 | 1.45 | yes | 7.799x | 0.562x | 0.072x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,675.0 | 2,377.7-2,377.7 | 9.83 | **no** | `b200_sxm-x347-nvl72-hybrid` | 653.1 | 2,369.0-2,369.0 | 1.38 | yes | 7.158x | 1.004x | 0.140x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,638.1 | 641.3-641.3 | 36.16 | **no** | `b200_sxm-x173-nvl72-hybrid` | 579.3 | 1,817.0-1,817.0 | 1.59 | yes | 8.006x | 0.353x | 0.044x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,504.6 | 1,298.8-1,298.8 | 17.34 | **no** | `b200_sxm-x347-nvl72-hybrid` | 616.5 | 2,064.3-2,064.3 | 1.49 | yes | 7.307x | 0.629x | 0.086x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,839.3 | 313.9-313.9 | 45.23 | **no** | `b200_sxm-x173-nvl72-hybrid` | 406.9 | 1,002.9-1,002.9 | 2.03 | yes | 6.978x | 0.313x | 0.045x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,071.8 | 654.1-654.1 | 23.48 | **no** | `b200_sxm-x347-nvl72-hybrid` | 495.9 | 1,349.9-1,349.9 | 1.84 | yes | 6.194x | 0.485x | 0.078x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,053.7 | 161.7-161.7 | 32.58 | **no** | `b200_sxm-x173-nvl72-hybrid` | 224.2 | 423.6-423.6 | 2.65 | yes | 4.700x | 0.382x | 0.081x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,249.0 | 169.0-169.0 | 36.96 | **no** | `b200_sxm-x347-nvl72-hybrid` | 294.8 | 676.7-676.7 | 2.18 | yes | 4.237x | 0.250x | 0.059x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 366.7 | 110.3-110.3 | 16.62 | **no** | `b200_sxm-x173-nvl72-hybrid` | 119.7 | 140.7-140.7 | 4.25 | yes | 3.064x | 0.784x | 0.256x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 359.7 | 44.8-44.8 | 40.12 | **no** | `b200_sxm-x347-nvl72-hybrid` | 151.1 | 199.7-199.7 | 3.78 | yes | 2.380x | 0.224x | 0.094x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.041x to 0.256x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,881.0 | 746.0-746.0 | 32.72 | **no** | `a100_sxm_80gb-x155-hybrid` | 362.2 | 1,014.4-1,014.4 | 1.79 | yes | 13.475x | 0.735x | 0.055x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | 4,989.2 | 1,614.0-1,614.0 | 15.46 | **no** | `a100_sxm_80gb-x616-hybrid` | 356.0 | 840.2-840.2 | 2.12 | yes | 14.017x | 1.921x | 0.137x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,881.0 | 746.0-746.0 | 32.72 | **no** | `a100_sxm_80gb-x155-hybrid` | 362.2 | 1,014.4-1,014.4 | 1.79 | yes | 13.475x | 0.735x | 0.055x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 4,273.7 | 1,001.9-1,001.9 | 21.33 | **no** | `a100_sxm_80gb-x448-hybrid` | 356.0 | 881.5-881.5 | 2.02 | yes | 12.006x | 1.137x | 0.095x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,881.0 | 746.0-746.0 | 32.72 | **no** | `a100_sxm_80gb-x155-hybrid` | 362.2 | 1,014.4-1,014.4 | 1.79 | yes | 13.475x | 0.735x | 0.055x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 4,273.7 | 1,001.9-1,001.9 | 21.33 | **no** | `a100_sxm_80gb-x448-hybrid` | 356.0 | 881.5-881.5 | 2.02 | yes | 12.006x | 1.137x | 0.095x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,881.0 | 746.0-746.0 | 32.72 | **no** | `a100_sxm_80gb-x155-hybrid` | 362.2 | 1,014.4-1,014.4 | 1.79 | yes | 13.475x | 0.735x | 0.055x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 4,273.7 | 1,001.9-1,001.9 | 21.33 | **no** | `a100_sxm_80gb-x448-hybrid` | 356.0 | 881.5-881.5 | 2.02 | yes | 12.006x | 1.137x | 0.095x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,881.0 | 746.0-746.0 | 32.72 | **no** | `a100_sxm_80gb-x155-hybrid` | 362.2 | 1,014.4-1,014.4 | 1.79 | yes | 13.475x | 0.735x | 0.055x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,267.0 | 701.2-701.2 | 30.43 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 827.7-827.7 | 2.15 | yes | 11.988x | 0.847x | 0.071x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,654.1 | 895.8-895.8 | 25.98 | **no** | `a100_sxm_80gb-x272-hybrid` | 358.9 | 951.4-951.4 | 1.89 | yes | 12.967x | 0.942x | 0.073x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,079.4 | 368.5-368.5 | 55.36 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 827.7-827.7 | 2.15 | yes | 11.461x | 0.445x | 0.039x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,200.2 | 467.7-467.7 | 44.90 | **no** | `a100_sxm_80gb-x272-hybrid` | 319.1 | 731.0-731.0 | 2.18 | yes | 13.165x | 0.640x | 0.049x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,615.9 | 365.5-365.5 | 49.47 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 827.7-827.7 | 2.15 | yes | 10.158x | 0.442x | 0.043x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 2,413.0 | 214.2-214.2 | 56.32 | **no** | `a100_sxm_80gb-x272-hybrid` | 189.4 | 341.5-341.5 | 2.77 | yes | 12.738x | 0.627x | 0.049x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,901.6 | 94.0-94.0 | 101.13 | **no** | `a100_sxm_80gb-x672-hybrid` | 275.1 | 512.2-512.2 | 2.69 | yes | 6.912x | 0.184x | 0.027x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 1,032.0 | 153.3-153.3 | 33.66 | **no** | `a100_sxm_80gb-x335-hybrid` | 90.7 | 174.1-174.1 | 2.61 | yes | 11.373x | 0.880x | 0.077x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 601.7 | 23.7-23.7 | 127.03 | **no** | `a100_sxm_80gb-x672-hybrid` | 141.3 | 246.7-246.7 | 2.86 | yes | 4.260x | 0.096x | 0.023x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 329.6 | 66.2-66.2 | 24.91 | **no** | `a100_sxm_80gb-x335-hybrid` | 34.8 | 44.0-44.0 | 3.96 | yes | 9.460x | 1.503x | 0.159x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 157.6 | 22.9-22.9 | 34.39 | **no** | `a100_sxm_80gb-x672-hybrid` | 55.6 | 113.4-113.4 | 2.45 | yes | 2.835x | 0.202x | 0.071x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.023x to 0.159x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5,462.9 | 660.5-660.5 | 41.35 | **no** | `b200_sxm-x47-nvl72-tensor` | 700.7 | 3,009.4-3,009.4 | 1.16 | yes | 7.796x | 0.219x | 0.028x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.8 | 1,305.2-1,305.2 | 21.16 | **no** | `b200_sxm-x58-nvl72-tensor` | 704.1 | 3,042.5-3,042.5 | 1.16 | yes | 7.845x | 0.429x | 0.055x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5,462.9 | 660.5-660.5 | 41.35 | **no** | `b200_sxm-x47-nvl72-tensor` | 690.7 | 2,818.1-2,818.1 | 1.23 | yes | 7.909x | 0.234x | 0.030x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.8 | 1,305.2-1,305.2 | 21.16 | **no** | `b200_sxm-x58-nvl72-tensor` | 695.0 | 2,856.9-2,856.9 | 1.22 | yes | 7.948x | 0.457x | 0.057x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5,462.9 | 660.5-660.5 | 41.35 | **no** | `b200_sxm-x47-nvl72-tensor` | 671.9 | 2,507.3-2,507.3 | 1.34 | yes | 8.131x | 0.263x | 0.032x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.8 | 1,305.2-1,305.2 | 21.16 | **no** | `b200_sxm-x58-nvl72-tensor` | 677.7 | 2,553.7-2,553.7 | 1.33 | yes | 8.151x | 0.511x | 0.063x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5,462.9 | 660.5-660.5 | 41.35 | **no** | `b200_sxm-x47-hybrid` | 639.0 | 2,197.8-2,197.8 | 1.45 | yes | 8.550x | 0.301x | 0.035x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.8 | 1,305.2-1,305.2 | 21.16 | **no** | `b200_sxm-x58-nvl72-tensor` | 646.3 | 2,126.2-2,126.2 | 1.52 | yes | 8.547x | 0.614x | 0.072x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5,462.9 | 660.5-660.5 | 41.35 | **no** | `b200_sxm-x47-hybrid` | 594.8 | 1,820.7-1,820.7 | 1.63 | yes | 9.185x | 0.363x | 0.039x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5,515.1 | 1,332.4-1,332.4 | 20.70 | **no** | `b200_sxm-x87-nvl72-hybrid` | 636.4 | 2,212.9-2,212.9 | 1.44 | yes | 8.666x | 0.602x | 0.069x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 5,356.6 | 661.5-661.5 | 40.49 | **no** | `b200_sxm-x110-nvl72-hybrid` | 607.3 | 1,986.7-1,986.7 | 1.53 | yes | 8.821x | 0.333x | 0.038x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,484.8 | 1,367.5-1,367.5 | 20.05 | **no** | `b200_sxm-x231-nvl72-hybrid` | 641.6 | 2,265.6-2,265.6 | 1.42 | yes | 8.548x | 0.604x | 0.071x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,356.6 | 661.5-661.5 | 40.49 | **no** | `b200_sxm-x173-nvl72-hybrid` | 584.0 | 1,827.5-1,827.5 | 1.60 | yes | 9.172x | 0.362x | 0.039x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,483.1 | 1,360.2-1,360.2 | 20.16 | **no** | `b200_sxm-x347-nvl72-hybrid` | 619.1 | 2,070.9-2,070.9 | 1.49 | yes | 8.856x | 0.657x | 0.074x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,825.6 | 328.9-328.9 | 58.15 | **no** | `b200_sxm-x173-nvl72-hybrid` | 416.2 | 1,016.5-1,016.5 | 2.05 | yes | 9.191x | 0.324x | 0.035x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,845.1 | 693.3-693.3 | 34.94 | **no** | `b200_sxm-x347-nvl72-hybrid` | 502.8 | 1,361.2-1,361.2 | 1.85 | yes | 9.637x | 0.509x | 0.053x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,658.6 | 155.8-155.8 | 53.24 | **no** | `b200_sxm-x173-nvl72-hybrid` | 235.8 | 431.8-431.8 | 2.73 | yes | 7.034x | 0.361x | 0.051x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,988.1 | 177.8-177.8 | 84.02 | **no** | `b200_sxm-x347-nvl72-hybrid` | 304.7 | 687.7-687.7 | 2.22 | yes | 9.807x | 0.259x | 0.026x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 483.4 | 114.0-114.0 | 21.19 | **no** | `b200_sxm-x173-nvl72-hybrid` | 133.8 | 144.3-144.3 | 4.64 | yes | 3.613x | 0.790x | 0.219x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,022.9 | 149.5-149.5 | 34.22 | **no** | `b200_sxm-x347-nvl72-hybrid` | 161.9 | 203.3-203.3 | 3.98 | yes | 6.319x | 0.735x | 0.116x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.026x to 0.219x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 5,219.2 | 931.8-931.8 | 28.01 | **no** | `a100_sxm_80gb-x126-hybrid` | 368.7 | 1,044.6-1,044.6 | 1.77 | yes | 14.154x | 0.892x | 0.063x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,352.7 | 978.1-978.1 | 27.36 | **no** | `a100_sxm_80gb-x168-hybrid` | 368.0 | 1,029.9-1,029.9 | 1.79 | yes | 14.545x | 0.950x | 0.065x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 5,219.2 | 931.8-931.8 | 28.01 | **no** | `a100_sxm_80gb-x126-hybrid` | 368.7 | 1,044.6-1,044.6 | 1.77 | yes | 14.154x | 0.892x | 0.063x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,352.7 | 978.1-978.1 | 27.36 | **no** | `a100_sxm_80gb-x168-hybrid` | 368.0 | 1,029.9-1,029.9 | 1.79 | yes | 14.545x | 0.950x | 0.065x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 5,219.2 | 931.8-931.8 | 28.01 | **no** | `a100_sxm_80gb-x126-hybrid` | 368.7 | 1,044.6-1,044.6 | 1.77 | yes | 14.154x | 0.892x | 0.063x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,352.7 | 978.1-978.1 | 27.36 | **no** | `a100_sxm_80gb-x168-hybrid` | 368.0 | 1,029.9-1,029.9 | 1.79 | yes | 14.545x | 0.950x | 0.065x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 5,219.2 | 931.8-931.8 | 28.01 | **no** | `a100_sxm_80gb-x126-hybrid` | 368.7 | 1,044.6-1,044.6 | 1.77 | yes | 14.154x | 0.892x | 0.063x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,352.7 | 978.1-978.1 | 27.36 | **no** | `a100_sxm_80gb-x168-hybrid` | 368.0 | 1,029.9-1,029.9 | 1.79 | yes | 14.545x | 0.950x | 0.065x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 5,219.2 | 931.8-931.8 | 28.01 | **no** | `a100_sxm_80gb-x126-hybrid` | 368.7 | 1,044.6-1,044.6 | 1.77 | yes | 14.154x | 0.892x | 0.063x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,352.7 | 978.1-978.1 | 27.36 | **no** | `a100_sxm_80gb-x168-hybrid` | 368.0 | 1,029.9-1,029.9 | 1.79 | yes | 14.545x | 0.950x | 0.065x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,102.9 | 922.0-922.0 | 27.67 | **no** | `a100_sxm_80gb-x272-hybrid` | 361.3 | 955.1-955.1 | 1.89 | yes | 14.124x | 0.965x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,332.6 | 1,004.9-1,004.9 | 26.53 | **no** | `a100_sxm_80gb-x448-hybrid` | 358.3 | 884.6-884.6 | 2.03 | yes | 14.884x | 1.136x | 0.076x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,014.1 | 481.9-481.9 | 52.03 | **no** | `a100_sxm_80gb-x272-hybrid` | 322.6 | 735.2-735.2 | 2.19 | yes | 15.543x | 0.655x | 0.042x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,329.3 | 999.3-999.3 | 26.66 | **no** | `a100_sxm_80gb-x672-hybrid` | 358.3 | 830.5-830.5 | 2.16 | yes | 14.875x | 1.203x | 0.081x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,324.4 | 238.4-238.4 | 69.73 | **no** | `a100_sxm_80gb-x335-hybrid` | 211.7 | 376.5-376.5 | 2.81 | yes | 15.702x | 0.633x | 0.040x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,424.0 | 503.9-503.9 | 43.90 | **no** | `a100_sxm_80gb-x672-hybrid` | 279.4 | 515.5-515.5 | 2.71 | yes | 15.834x | 0.978x | 0.062x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,285.4 | 112.7-112.7 | 57.01 | **no** | `a100_sxm_80gb-x335-hybrid` | 94.6 | 177.0-177.0 | 2.67 | yes | 13.592x | 0.637x | 0.047x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,403.2 | 128.4-128.4 | 93.61 | **no** | `a100_sxm_80gb-x672-hybrid` | 145.8 | 249.6-249.6 | 2.92 | yes | 16.479x | 0.514x | 0.031x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 455.1 | 120.2-120.2 | 18.93 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.2 | 49.4-49.4 | 3.76 | yes | 12.249x | 2.434x | 0.199x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 759.1 | 107.8-107.8 | 35.21 | **no** | `a100_sxm_80gb-x672-hybrid` | 58.5 | 115.9-115.9 | 2.52 | yes | 12.986x | 0.930x | 0.072x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.031x to 0.199x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 701.4 | 3,016.3-3,016.3 | 1.16 | yes | 7.658x | 0.404x | 0.053x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 1,289.0-1,289.0 | 20.83 | **no** | `b200_sxm-x58-nvl72-tensor` | 704.0 | 3,042.2-3,042.2 | 1.16 | yes | 7.628x | 0.424x | 0.056x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 691.5 | 2,826.1-2,826.1 | 1.22 | yes | 7.767x | 0.431x | 0.055x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 1,289.0-1,289.0 | 20.83 | **no** | `b200_sxm-x58-nvl72-tensor` | 694.8 | 2,856.4-2,856.4 | 1.22 | yes | 7.728x | 0.451x | 0.058x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 672.8 | 2,516.7-2,516.7 | 1.34 | yes | 7.983x | 0.484x | 0.061x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 1,289.0-1,289.0 | 20.83 | **no** | `b200_sxm-x58-nvl72-tensor` | 677.4 | 2,552.9-2,552.9 | 1.33 | yes | 7.927x | 0.505x | 0.064x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 1,217.8-1,217.8 | 22.05 | **no** | `b200_sxm-x49-nvl72-tensor` | 639.3 | 2,089.9-2,089.9 | 1.53 | yes | 8.402x | 0.583x | 0.069x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 1,289.0-1,289.0 | 20.83 | **no** | `b200_sxm-x58-nvl72-tensor` | 645.9 | 2,125.0-2,125.0 | 1.52 | yes | 8.314x | 0.607x | 0.073x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,361.9 | 632.2-632.2 | 42.40 | **no** | `b200_sxm-x49-hybrid` | 590.3 | 1,816.2-1,816.2 | 1.63 | yes | 9.083x | 0.348x | 0.038x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5,363.4 | 1,315.6-1,315.6 | 20.38 | **no** | `b200_sxm-x87-nvl72-hybrid` | 635.9 | 2,211.3-2,211.3 | 1.44 | yes | 8.435x | 0.595x | 0.071x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 5,209.1 | 657.3-657.3 | 39.62 | **no** | `b200_sxm-x110-nvl72-hybrid` | 606.5 | 1,984.7-1,984.7 | 1.53 | yes | 8.589x | 0.331x | 0.039x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,337.0 | 1,350.1-1,350.1 | 19.77 | **no** | `b200_sxm-x231-nvl72-hybrid` | 641.2 | 2,264.3-2,264.3 | 1.42 | yes | 8.323x | 0.596x | 0.072x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,209.1 | 657.3-657.3 | 39.62 | **no** | `b200_sxm-x173-nvl72-hybrid` | 583.0 | 1,825.3-1,825.3 | 1.60 | yes | 8.934x | 0.360x | 0.040x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,335.0 | 1,342.9-1,342.9 | 19.86 | **no** | `b200_sxm-x347-nvl72-hybrid` | 618.6 | 2,069.5-2,069.5 | 1.49 | yes | 8.625x | 0.649x | 0.075x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,572.7 | 325.7-325.7 | 54.84 | **no** | `b200_sxm-x173-nvl72-hybrid` | 414.3 | 1,013.7-1,013.7 | 2.04 | yes | 8.624x | 0.321x | 0.037x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,537.0 | 684.4-684.4 | 33.15 | **no** | `b200_sxm-x347-nvl72-hybrid` | 501.3 | 1,358.8-1,358.8 | 1.84 | yes | 9.050x | 0.504x | 0.056x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,474.7 | 152.9-152.9 | 48.23 | **no** | `b200_sxm-x173-nvl72-hybrid` | 233.3 | 430.1-430.1 | 2.71 | yes | 6.320x | 0.355x | 0.056x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,637.2 | 175.8-175.8 | 74.99 | **no** | `b200_sxm-x347-nvl72-hybrid` | 302.6 | 685.5-685.5 | 2.21 | yes | 8.715x | 0.257x | 0.029x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 434.2 | 127.1-127.1 | 17.08 | **no** | `b200_sxm-x173-nvl72-hybrid` | 130.7 | 143.6-143.6 | 4.55 | yes | 3.323x | 0.886x | 0.267x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 872.6 | 144.5-144.5 | 30.20 | **no** | `b200_sxm-x347-nvl72-hybrid` | 159.6 | 202.5-202.5 | 3.94 | yes | 5.469x | 0.713x | 0.130x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.029x to 0.267x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 366.0 | 1,031.9-1,031.9 | 1.77 | yes | 14.085x | 0.850x | 0.060x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.2 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 13.867x | 0.939x | 0.068x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 366.0 | 1,031.9-1,031.9 | 1.77 | yes | 14.085x | 0.850x | 0.060x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.2 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 13.867x | 0.939x | 0.068x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 366.0 | 1,031.9-1,031.9 | 1.77 | yes | 14.085x | 0.850x | 0.060x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.2 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 13.867x | 0.939x | 0.068x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 366.0 | 1,031.9-1,031.9 | 1.77 | yes | 14.085x | 0.850x | 0.060x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.2 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 13.867x | 0.939x | 0.068x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 877.5-877.5 | 29.37 | **no** | `a100_sxm_80gb-x132-hybrid` | 366.0 | 1,031.9-1,031.9 | 1.77 | yes | 14.085x | 0.850x | 0.060x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.2 | 965.9-965.9 | 26.38 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 13.867x | 0.939x | 0.068x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,021.1 | 916.5-916.5 | 27.39 | **no** | `a100_sxm_80gb-x272-hybrid` | 360.8 | 954.3-954.3 | 1.89 | yes | 13.916x | 0.960x | 0.069x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,079.5 | 992.0-992.0 | 25.60 | **no** | `a100_sxm_80gb-x448-hybrid` | 357.8 | 884.0-884.0 | 2.02 | yes | 14.196x | 1.122x | 0.079x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,830.1 | 478.9-478.9 | 50.43 | **no** | `a100_sxm_80gb-x272-hybrid` | 321.9 | 734.3-734.3 | 2.19 | yes | 15.007x | 0.652x | 0.043x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,076.2 | 986.6-986.6 | 25.73 | **no** | `a100_sxm_80gb-x672-hybrid` | 357.8 | 829.9-829.9 | 2.16 | yes | 14.187x | 1.189x | 0.084x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,068.8 | 236.2-236.2 | 64.96 | **no** | `a100_sxm_80gb-x335-hybrid` | 210.7 | 375.8-375.8 | 2.80 | yes | 14.565x | 0.629x | 0.043x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,988.1 | 497.6-497.6 | 40.07 | **no** | `a100_sxm_80gb-x672-hybrid` | 278.5 | 514.8-514.8 | 2.70 | yes | 14.319x | 0.967x | 0.068x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 1,176.6 | 163.6-163.6 | 35.96 | **no** | `a100_sxm_80gb-x335-hybrid` | 93.8 | 176.4-176.4 | 2.66 | yes | 12.548x | 0.927x | 0.074x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,978.0 | 127.0-127.0 | 77.86 | **no** | `a100_sxm_80gb-x672-hybrid` | 144.9 | 249.0-249.0 | 2.91 | yes | 13.653x | 0.510x | 0.037x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 428.3 | 114.1-114.1 | 18.76 | **no** | `a100_sxm_80gb-x335-hybrid` | 36.7 | 48.2-48.2 | 3.80 | yes | 11.682x | 2.368x | 0.203x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 602.8 | 104.5-104.5 | 28.84 | **no** | `a100_sxm_80gb-x672-hybrid` | 57.8 | 115.4-115.4 | 2.51 | yes | 10.421x | 0.906x | 0.087x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.037x to 0.203x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-kimi-k3`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | 1,428.2 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 288.3 | not applicable | -- | -- | 4.954x | -- | -- |
| Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 1,779.5 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 288.4 | not applicable | -- | -- | 6.169x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,322.3 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 288.4 | not applicable | -- | -- | 4.584x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,760.7 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 286.0 | not applicable | -- | -- | 6.156x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,322.3 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 286.0 | not applicable | -- | -- | 4.623x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,760.7 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 286.0 | not applicable | -- | -- | 6.156x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,301.1 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 276.9 | not applicable | -- | -- | 4.699x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,760.7 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 284.8 | not applicable | -- | -- | 6.182x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,154.8 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 260.6 | not applicable | -- | -- | 4.431x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,760.7 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 275.6 | not applicable | -- | -- | 6.389x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 911.1 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 234.2 | not applicable | -- | -- | 3.890x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,537.9 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 259.0 | not applicable | -- | -- | 5.937x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 580.6 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 197.6 | not applicable | -- | -- | 2.939x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,264.7 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 232.1 | not applicable | -- | -- | 5.450x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 176.3 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 117.0 | not applicable | -- | -- | 1.506x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 509.1 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 152.2 | not applicable | -- | -- | 3.346x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 45.9 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 58.0 | not applicable | -- | -- | 0.790x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 144.4 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 78.2 | not applicable | -- | -- | 1.845x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 11.5 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 25.1 | not applicable | -- | -- | 0.458x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 36.9 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 36.7 | not applicable | -- | -- | 1.006x | -- | -- |

### `n6_vs_a100-kimi-k3`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x398` | 1,092.5 | not applicable | -- | -- | `a100_sxm_80gb-x393-hybrid` | 108.2 | not applicable | -- | -- | 10.093x | -- | -- |
| Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x10` | 1,701.7 | not applicable | -- | -- | `a100_sxm_80gb-x560-hybrid` | 109.7 | not applicable | -- | -- | 15.511x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 885.7 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 108.3 | not applicable | -- | -- | 8.179x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,402.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 108.3 | not applicable | -- | -- | 12.946x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 885.7 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 108.3 | not applicable | -- | -- | 8.179x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,402.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 108.3 | not applicable | -- | -- | 12.946x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 810.2 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 106.8 | not applicable | -- | -- | 7.588x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,402.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 108.3 | not applicable | -- | -- | 12.946x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 600.3 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 96.0 | not applicable | -- | -- | 6.252x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,402.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 108.3 | not applicable | -- | -- | 12.946x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 372.0 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 82.3 | not applicable | -- | -- | 4.519x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,164.3 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 101.8 | not applicable | -- | -- | 11.443x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 205.7 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 67.0 | not applicable | -- | -- | 3.071x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 851.0 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 87.7 | not applicable | -- | -- | 9.705x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 55.3 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 39.4 | not applicable | -- | -- | 1.404x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 301.9 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 58.1 | not applicable | -- | -- | 5.194x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 14.0 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 16.8 | not applicable | -- | -- | 0.832x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 81.8 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 32.3 | not applicable | -- | -- | 2.536x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 3.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 6.6 | not applicable | -- | -- | 0.528x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x22` | 20.8 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 12.8 | not applicable | -- | -- | 1.624x | -- | -- |

### `n5_vs_b200-kimi-k3-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x383` | 946.4 | not applicable | -- | -- | `b200_sxm-x195-nvl72-hybrid` | 285.4 | not applicable | -- | -- | 3.317x | -- | -- |
| Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | 1,533.1 | not applicable | -- | -- | `b200_sxm-x520-nvl72-hybrid` | 283.0 | not applicable | -- | -- | 5.417x | -- | -- |
| Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,293.4 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | not applicable | -- | -- | 4.685x | -- | -- |
| Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,293.4 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | not applicable | -- | -- | 4.685x | -- | -- |
| Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,293.4 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | not applicable | -- | -- | 4.685x | -- | -- |
| Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,293.4 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | not applicable | -- | -- | 4.685x | -- | -- |
| Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,207.7 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 273.9 | not applicable | -- | -- | 4.410x | -- | -- |
| Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,143.4 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 257.6 | not applicable | -- | -- | 4.439x | -- | -- |
| Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 518.2 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 196.9 | not applicable | -- | -- | 2.632x | -- | -- |
| Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 151.9 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 120.5 | not applicable | -- | -- | 1.260x | -- | -- |
| Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x68` | 39.3 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 49.4 | not applicable | -- | -- | 0.795x | -- | -- |

### `n6_vs_a100-kimi-k3-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 722.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 106.9 | not applicable | -- | -- | 6.757x | -- | -- |
| Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x23` | 1,333.7 | not applicable | -- | -- | `a100_sxm_80gb-x1287-hybrid` | 106.9 | not applicable | -- | -- | 12.480x | -- | -- |
| Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 1,084.9 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 100.9 | not applicable | -- | -- | 10.751x | -- | -- |
| Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 1,084.9 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 100.9 | not applicable | -- | -- | 10.751x | -- | -- |
| Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 1,084.9 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 100.9 | not applicable | -- | -- | 10.751x | -- | -- |
| Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 1,084.9 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 100.9 | not applicable | -- | -- | 10.751x | -- | -- |
| Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 956.7 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 100.9 | not applicable | -- | -- | 9.480x | -- | -- |
| Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 750.1 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 100.9 | not applicable | -- | -- | 7.434x | -- | -- |
| Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 313.0 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 81.1 | not applicable | -- | -- | 3.862x | -- | -- |
| Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 87.5 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 55.1 | not applicable | -- | -- | 1.588x | -- | -- |
| Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 22.4 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 28.7 | not applicable | -- | -- | 0.779x | -- | -- |

### `n5_vs_b200-kimi-k3-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,928.0 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 288.8 | not applicable | -- | -- | 6.675x | -- | -- |
| Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,162.9 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 288.9 | not applicable | -- | -- | 7.486x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,928.0 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 288.8 | not applicable | -- | -- | 6.675x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,162.9 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 288.9 | not applicable | -- | -- | 7.486x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,928.0 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 286.6 | not applicable | -- | -- | 6.728x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,162.9 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 286.7 | not applicable | -- | -- | 7.544x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,928.0 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 278.0 | not applicable | -- | -- | 6.936x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,162.9 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 278.1 | not applicable | -- | -- | 7.777x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,928.0 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 262.6 | not applicable | -- | -- | 7.341x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,162.9 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 262.8 | not applicable | -- | -- | 8.230x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,731.2 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 237.6 | not applicable | -- | -- | 7.285x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,152.4 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 255.1 | not applicable | -- | -- | 8.438x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,499.1 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 202.5 | not applicable | -- | -- | 7.404x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,873.9 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 225.8 | not applicable | -- | -- | 8.299x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 719.1 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 124.3 | not applicable | -- | -- | 5.783x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,089.9 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 144.8 | not applicable | -- | -- | 7.525x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 219.5 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 65.9 | not applicable | -- | -- | 3.331x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 369.4 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 77.5 | not applicable | -- | -- | 4.764x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 57.8 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 33.4 | not applicable | -- | -- | 1.729x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 99.2 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 39.6 | not applicable | -- | -- | 2.507x | -- | -- |

### `n6_vs_a100-kimi-k3-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,383.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 108.6 | not applicable | -- | -- | 12.737x | -- | -- |
| Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,860.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 109.5 | not applicable | -- | -- | 16.987x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,383.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 108.6 | not applicable | -- | -- | 12.737x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,860.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 109.5 | not applicable | -- | -- | 16.987x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,383.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 108.6 | not applicable | -- | -- | 12.737x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,860.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 109.5 | not applicable | -- | -- | 16.987x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,383.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 107.1 | not applicable | -- | -- | 12.913x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,860.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 109.5 | not applicable | -- | -- | 16.987x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,251.6 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 96.6 | not applicable | -- | -- | 12.953x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,855.7 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 104.8 | not applicable | -- | -- | 17.705x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,069.6 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 83.2 | not applicable | -- | -- | 12.853x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,648.8 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 92.2 | not applicable | -- | -- | 17.877x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 742.9 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 68.1 | not applicable | -- | -- | 10.901x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,327.9 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 79.0 | not applicable | -- | -- | 16.809x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 249.6 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 41.1 | not applicable | -- | -- | 6.077x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554.8 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 49.3 | not applicable | -- | -- | 11.245x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 66.6 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 18.1 | not applicable | -- | -- | 3.685x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 159.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 23.7 | not applicable | -- | -- | 6.712x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 16.8 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 7.4 | not applicable | -- | -- | 2.253x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 40.9 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 9.2 | not applicable | -- | -- | 4.467x | -- | -- |

### `n5_vs_b200-mimo-v26-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | 5,396.1 | 3,274.0-3,274.0 | 8.24 | **no** | `b200_sxm-x23-nvl72-tensor` | 713.1 | 2,994.0-2,994.0 | 1.19 | yes | 7.567x | 1.094x | 0.145x |
| MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 5,503.2 | 8,245.3-8,245.3 | 3.34 | yes | `b200_sxm-x29-nvl72-tensor` | 725.5 | 3,109.5-3,109.5 | 1.17 | yes | 7.586x | 2.652x | 0.350x |
| MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,797.9 | 1,220.5-1,220.5 | 19.66 | **no** | `b200_sxm-x192-nvl72-hybrid` | 749.3 | 3,373.3-3,373.3 | 1.11 | yes | 6.403x | 0.362x | 0.057x |
| MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,663.1 | 2,224.7-2,224.7 | 8.23 | **no** | `b200_sxm-x636-nvl72-hybrid` | 744.2 | 3,359.8-3,359.8 | 1.11 | yes | 4.922x | 0.662x | 0.135x |
| MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,797.9 | 1,220.5-1,220.5 | 19.66 | **no** | `b200_sxm-x192-nvl72-hybrid` | 744.3 | 3,314.9-3,314.9 | 1.12 | yes | 6.446x | 0.368x | 0.057x |
| MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,663.1 | 2,224.7-2,224.7 | 8.23 | **no** | `b200_sxm-x636-nvl72-hybrid` | 744.2 | 3,359.8-3,359.8 | 1.11 | yes | 4.922x | 0.662x | 0.135x |
| MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,797.9 | 1,220.5-1,220.5 | 19.66 | **no** | `b200_sxm-x192-nvl72-hybrid` | 725.2 | 3,131.0-3,131.0 | 1.16 | yes | 6.616x | 0.390x | 0.059x |
| MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,496.8 | 1,322.6-1,322.6 | 13.22 | **no** | `b200_sxm-x636-nvl72-hybrid` | 744.2 | 3,359.8-3,359.8 | 1.11 | yes | 4.699x | 0.394x | 0.084x |
| MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x282` | 4,634.9 | 841.0-841.0 | 27.55 | **no** | `b200_sxm-x144-nvl72-hybrid` | 671.4 | 2,650.9-2,650.9 | 1.27 | yes | 6.903x | 0.317x | 0.046x |
| MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,364.9 | 701.1-701.1 | 24.00 | **no** | `b200_sxm-x636-nvl72-hybrid` | 733.3 | 3,232.3-3,232.3 | 1.13 | yes | 4.589x | 0.217x | 0.047x |
| MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,038.8 | 634.0-634.0 | 31.85 | **no** | `b200_sxm-x192-nvl72-hybrid` | 633.4 | 2,414.6-2,414.6 | 1.31 | yes | 6.376x | 0.263x | 0.041x |
| MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 2,771.2 | 690.2-690.2 | 20.07 | **no** | `b200_sxm-x636-nvl72-hybrid` | 710.0 | 2,992.9-2,992.9 | 1.19 | yes | 3.903x | 0.231x | 0.059x |
| MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 2,943.2 | 331.2-331.2 | 44.43 | **no** | `b200_sxm-x192-nvl72-hybrid` | 550.0 | 1,918.6-1,918.6 | 1.43 | yes | 5.351x | 0.173x | 0.032x |
| MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 1,859.8 | 396.4-396.4 | 23.46 | **no** | `b200_sxm-x636-nvl72-hybrid` | 668.9 | 2,639.9-2,639.9 | 1.27 | yes | 2.780x | 0.150x | 0.054x |
| MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 951.4 | 433.2-433.2 | 10.98 | **no** | `b200_sxm-x192-nvl72-hybrid` | 339.1 | 909.8-909.8 | 1.86 | yes | 2.806x | 0.476x | 0.170x |
| MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 600.3 | 101.0-101.0 | 29.72 | **no** | `b200_sxm-x636-nvl72-hybrid` | 512.4 | 1,605.3-1,605.3 | 1.60 | yes | 1.171x | 0.063x | 0.054x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 238.5 | 224.3-224.3 | 5.32 | **no** | `b200_sxm-x192-nvl72-hybrid` | 152.4 | 433.8-433.8 | 1.76 | yes | 1.565x | 0.517x | 0.330x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 159.0 | 25.3-25.3 | 31.40 | **no** | `b200_sxm-x636-nvl72-hybrid` | 297.9 | 688.0-688.0 | 2.16 | yes | 0.534x | 0.037x | 0.069x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 59.7 | 76.2-76.2 | 3.92 | yes | `b200_sxm-x192-nvl72-hybrid` | 51.4 | 171.2-171.2 | 1.50 | yes | 1.162x | 0.445x | 0.383x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x22` | 40.2 | 12.3-12.3 | 16.38 | **no** | `b200_sxm-x636-nvl72-hybrid` | 128.8 | 321.3-321.3 | 2.00 | yes | 0.312x | 0.038x | 0.122x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.032x to 0.383x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 2 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x64` | 5,173.0 | 2,664.9-2,664.9 | 9.71 | **no** | `a100_sxm_80gb-x63-hybrid` | 331.6 | 1,047.1-1,047.1 | 1.58 | yes | 15.600x | 2.545x | 0.163x |
| MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 5,440.2 | 7,708.8-7,708.8 | 3.53 | yes | `a100_sxm_80gb-x56-hybrid` | 334.2 | 1,051.1-1,051.1 | 1.59 | yes | 16.280x | 7.334x | 0.451x |
| MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3,903.2 | 1,928.9-1,928.9 | 10.12 | **no** | `a100_sxm_80gb-x391-hybrid` | 327.2 | 1,145.2-1,145.2 | 1.43 | yes | 11.928x | 1.684x | 0.141x |
| MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3,134.8 | 1,722.7-1,722.7 | 9.10 | **no** | `a100_sxm_80gb-x1735-hybrid` | 323.9 | 1,139.6-1,139.6 | 1.42 | yes | 9.677x | 1.512x | 0.156x |
| MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3,903.2 | 1,928.9-1,928.9 | 10.12 | **no** | `a100_sxm_80gb-x391-hybrid` | 327.2 | 1,145.2-1,145.2 | 1.43 | yes | 11.928x | 1.684x | 0.141x |
| MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3,134.8 | 1,722.7-1,722.7 | 9.10 | **no** | `a100_sxm_80gb-x1735-hybrid` | 323.9 | 1,139.6-1,139.6 | 1.42 | yes | 9.677x | 1.512x | 0.156x |
| MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x287` | 3,860.3 | 1,558.9-1,558.9 | 12.38 | **no** | `a100_sxm_80gb-x283-hybrid` | 324.2 | 1,120.0-1,120.0 | 1.45 | yes | 11.906x | 1.392x | 0.117x |
| MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3,134.8 | 1,722.7-1,722.7 | 9.10 | **no** | `a100_sxm_80gb-x1735-hybrid` | 323.9 | 1,139.6-1,139.6 | 1.42 | yes | 9.677x | 1.512x | 0.156x |
| MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3,415.0 | 1,110.4-1,110.4 | 15.38 | **no** | `a100_sxm_80gb-x391-hybrid` | 323.4 | 1,131.3-1,131.3 | 1.43 | yes | 10.561x | 0.982x | 0.093x |
| MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2,577.1 | 925.7-925.7 | 13.92 | **no** | `a100_sxm_80gb-x1735-hybrid` | 323.9 | 1,139.6-1,139.6 | 1.42 | yes | 7.956x | 0.812x | 0.102x |
| MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 2,658.9 | 605.7-605.7 | 21.95 | **no** | `a100_sxm_80gb-x391-hybrid` | 323.4 | 1,131.3-1,131.3 | 1.43 | yes | 8.223x | 0.535x | 0.065x |
| MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,983.5 | 495.9-495.9 | 20.00 | **no** | `a100_sxm_80gb-x1735-hybrid` | 323.6 | 1,240.1-1,240.1 | 1.30 | yes | 6.129x | 0.400x | 0.065x |
| MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,676.6 | 309.9-309.9 | 27.05 | **no** | `a100_sxm_80gb-x391-hybrid` | 301.0 | 1,025.0-1,025.0 | 1.47 | yes | 5.570x | 0.302x | 0.054x |
| MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,213.9 | 282.0-282.0 | 21.53 | **no** | `a100_sxm_80gb-x1735-hybrid` | 323.6 | 1,240.1-1,240.1 | 1.30 | yes | 3.751x | 0.227x | 0.061x |
| MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 503.9 | 79.1-79.1 | 31.85 | **no** | `a100_sxm_80gb-x391-hybrid` | 162.2 | 533.4-533.4 | 1.52 | yes | 3.108x | 0.148x | 0.048x |
| MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 356.1 | 71.2-71.2 | 25.02 | **no** | `a100_sxm_80gb-x1735-hybrid` | 310.1 | 1,152.7-1,152.7 | 1.35 | yes | 1.148x | 0.062x | 0.054x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 131.0 | 38.2-38.2 | 17.17 | **no** | `a100_sxm_80gb-x391-hybrid` | 62.0 | 220.7-220.7 | 1.41 | yes | 2.112x | 0.173x | 0.082x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 92.0 | 17.8-17.8 | 25.80 | **no** | `a100_sxm_80gb-x1735-hybrid` | 172.4 | 584.9-584.9 | 1.47 | yes | 0.534x | 0.030x | 0.057x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 33.0 | 31.3-31.3 | 5.29 | **no** | `a100_sxm_80gb-x391-hybrid` | 22.2 | 65.6-65.6 | 1.69 | yes | 1.492x | 0.477x | 0.319x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x31` | 23.1 | 8.6-8.6 | 13.48 | **no** | `a100_sxm_80gb-x1735-hybrid` | 67.0 | 247.8-247.8 | 1.35 | yes | 0.345x | 0.035x | 0.100x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.048x to 0.451x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 1 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 4,359.9 | 2,564.7-2,564.7 | 8.50 | **no** | `b200_sxm-x53-nvl72-tensor` | 719.2 | 3,209.4-3,209.4 | 1.12 | yes | 6.062x | 0.799x | 0.132x |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 5,253.1 | 2,916.6-2,916.6 | 9.01 | **no** | `b200_sxm-x58-nvl72-tensor` | 723.9 | 3,240.7-3,240.7 | 1.12 | yes | 7.257x | 0.900x | 0.124x |
| MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,458.8 | 550.3-550.3 | 22.34 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 3,052.8-3,052.8 | 1.12 | yes | 3.589x | 0.180x | 0.050x |
| MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,458.8 | 550.3-550.3 | 22.34 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 3,052.8-3,052.8 | 1.12 | yes | 3.589x | 0.180x | 0.050x |
| MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,458.8 | 550.3-550.3 | 22.34 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 3,052.8-3,052.8 | 1.12 | yes | 3.589x | 0.180x | 0.050x |
| MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,458.8 | 550.3-550.3 | 22.34 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 3,052.8-3,052.8 | 1.12 | yes | 3.589x | 0.180x | 0.050x |
| MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,302.8 | 547.2-547.2 | 21.04 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 3,052.8-3,052.8 | 1.12 | yes | 3.362x | 0.179x | 0.053x |
| MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,626.6 | 285.0-285.0 | 28.54 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 670.2 | 2,916.3-2,916.3 | 1.15 | yes | 2.427x | 0.098x | 0.040x |
| MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 586.9 | 81.7-81.7 | 35.91 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 565.7 | 2,400.0-2,400.0 | 1.18 | yes | 1.037x | 0.034x | 0.033x |
| MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 157.8 | 20.6-20.6 | 38.37 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 351.3 | 1,478.4-1,478.4 | 1.19 | yes | 0.449x | 0.014x | 0.031x |
| MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 40.0 | 5.1-5.1 | 38.91 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 144.8 | 534.2-534.2 | 1.36 | yes | 0.276x | 0.010x | 0.035x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.031x to 0.132x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | 4,193.4 | 2,125.7-2,125.7 | 9.86 | **no** | `a100_sxm_80gb-x139-tensor` | 331.5 | 1,161.1-1,161.1 | 1.43 | yes | 12.650x | 1.831x | 0.145x |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 5,049.5 | 4,558.8-4,558.8 | 5.54 | **no** | `a100_sxm_80gb-x112-tensor` | 327.6 | 1,149.5-1,149.5 | 1.43 | yes | 15.412x | 3.966x | 0.257x |
| MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 1,661.2 | 4,110.0-4,110.0 | 2.02 | yes | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 1,086.0-1,086.0 | 1.39 | yes | 5.488x | 3.785x | 0.690x |
| MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,535.4 | 394.5-394.5 | 19.46 | **no** | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 1,086.0-1,086.0 | 1.39 | yes | 5.073x | 0.363x | 0.072x |
| MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,535.4 | 394.5-394.5 | 19.46 | **no** | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 1,086.0-1,086.0 | 1.39 | yes | 5.073x | 0.363x | 0.072x |
| MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,535.4 | 394.5-394.5 | 19.46 | **no** | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 1,086.0-1,086.0 | 1.39 | yes | 5.073x | 0.363x | 0.072x |
| MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,535.4 | 394.5-394.5 | 19.46 | **no** | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 1,086.0-1,086.0 | 1.39 | yes | 5.073x | 0.363x | 0.072x |
| MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,085.8 | 384.3-384.3 | 14.13 | **no** | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 1,086.0-1,086.0 | 1.39 | yes | 3.587x | 0.354x | 0.099x |
| MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 346.8 | 100.4-100.4 | 17.28 | **no** | `a100_sxm_80gb-x8562-hybrid` | 275.8 | 1,033.4-1,033.4 | 1.33 | yes | 1.258x | 0.097x | 0.077x |
| MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 90.9 | 28.2-28.2 | 16.13 | **no** | `a100_sxm_80gb-x8562-hybrid` | 222.9 | 993.4-993.4 | 1.12 | yes | 0.408x | 0.028x | 0.070x |
| MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 22.9 | 7.1-7.1 | 16.26 | **no** | `a100_sxm_80gb-x8562-hybrid` | 95.2 | 390.7-390.7 | 1.22 | yes | 0.241x | 0.018x | 0.075x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.070x to 0.690x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 1 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,140.0 | 2,168.6-2,168.6 | 16.46 | **no** | `b200_sxm-x61-nvl72-tensor` | 758.2 | 3,384.7-3,384.7 | 1.12 | yes | 9.418x | 0.641x | 0.068x |
| MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,526.2 | 1,833.2-1,833.2 | 17.80 | **no** | `b200_sxm-x58-nvl72-tensor` | 757.2 | 3,373.7-3,373.7 | 1.12 | yes | 8.619x | 0.543x | 0.063x |
| MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,140.0 | 2,168.6-2,168.6 | 16.46 | **no** | `b200_sxm-x61-nvl72-tensor` | 748.9 | 3,246.5-3,246.5 | 1.15 | yes | 9.534x | 0.668x | 0.070x |
| MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,526.2 | 1,833.2-1,833.2 | 17.80 | **no** | `b200_sxm-x58-nvl72-tensor` | 747.6 | 3,231.8-3,231.8 | 1.16 | yes | 8.730x | 0.567x | 0.065x |
| MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,140.0 | 2,168.6-2,168.6 | 16.46 | **no** | `b200_sxm-x61-nvl72-tensor` | 731.6 | 3,012.3-3,012.3 | 1.21 | yes | 9.760x | 0.720x | 0.074x |
| MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,526.2 | 1,833.2-1,833.2 | 17.80 | **no** | `b200_sxm-x58-nvl72-tensor` | 729.7 | 2,993.2-2,993.2 | 1.22 | yes | 8.944x | 0.612x | 0.068x |
| MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,140.0 | 2,168.6-2,168.6 | 16.46 | **no** | `b200_sxm-x61-nvl72-tensor` | 701.4 | 2,692.7-2,692.7 | 1.30 | yes | 10.180x | 0.805x | 0.079x |
| MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,526.2 | 1,833.2-1,833.2 | 17.80 | **no** | `b200_sxm-x58-nvl72-tensor` | 698.5 | 2,671.1-2,671.1 | 1.31 | yes | 9.344x | 0.686x | 0.073x |
| MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 7,074.1 | 2,100.2-2,100.2 | 16.84 | **no** | `b200_sxm-x87-nvl72-hybrid` | 676.9 | 2,553.8-2,553.8 | 1.33 | yes | 10.451x | 0.822x | 0.079x |
| MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 6,388.4 | 3,972.7-3,972.7 | 8.04 | **no** | `b200_sxm-x173-nvl72-hybrid` | 714.3 | 2,886.9-2,886.9 | 1.24 | yes | 8.943x | 1.376x | 0.154x |
| MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,967.4 | 2,139.2-2,139.2 | 16.29 | **no** | `b200_sxm-x173-nvl72-hybrid` | 675.7 | 2,517.3-2,517.3 | 1.34 | yes | 10.312x | 0.850x | 0.082x |
| MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6,305.2 | 4,036.3-4,036.3 | 7.81 | **no** | `b200_sxm-x347-nvl72-hybrid` | 711.5 | 2,846.3-2,846.3 | 1.25 | yes | 8.862x | 1.418x | 0.160x |
| MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,929.3 | 1,140.0-1,140.0 | 30.39 | **no** | `b200_sxm-x173-nvl72-hybrid` | 619.2 | 2,069.7-2,069.7 | 1.50 | yes | 11.191x | 0.551x | 0.049x |
| MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6,075.1 | 2,270.4-2,270.4 | 13.38 | **no** | `b200_sxm-x347-nvl72-hybrid` | 671.7 | 2,431.8-2,431.8 | 1.38 | yes | 9.045x | 0.934x | 0.103x |
| MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,651.0 | 559.8-559.8 | 41.54 | **no** | `b200_sxm-x173-nvl72-hybrid` | 479.3 | 1,079.3-1,079.3 | 2.22 | yes | 9.704x | 0.519x | 0.053x |
| MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,129.5 | 1,164.0-1,164.0 | 17.74 | **no** | `b200_sxm-x347-nvl72-hybrid` | 545.1 | 1,409.0-1,409.0 | 1.93 | yes | 7.576x | 0.826x | 0.109x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,847.6 | 256.5-256.5 | 36.01 | **no** | `b200_sxm-x173-nvl72-hybrid` | 329.6 | 626.6-626.6 | 2.63 | yes | 5.605x | 0.409x | 0.073x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,614.2 | 304.5-304.5 | 26.51 | **no** | `b200_sxm-x347-nvl72-hybrid` | 388.1 | 611.1-611.1 | 3.18 | yes | 4.159x | 0.498x | 0.120x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 527.4 | 164.8-164.8 | 16.00 | **no** | `b200_sxm-x173-nvl72-hybrid` | 195.2 | 316.0-316.0 | 3.09 | yes | 2.702x | 0.521x | 0.193x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 452.3 | 237.3-237.3 | 9.53 | **no** | `b200_sxm-x347-nvl72-hybrid` | 242.8 | 306.4-306.4 | 3.96 | yes | 1.863x | 0.775x | 0.416x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.049x to 0.416x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,845.8 | 1,569.2-1,569.2 | 21.81 | **no** | `a100_sxm_80gb-x77-hybrid` | 369.9 | 1,123.9-1,123.9 | 1.65 | yes | 18.505x | 1.396x | 0.075x |
| MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,680.5 | 1,822.0-1,822.0 | 15.59 | **no** | `a100_sxm_80gb-x224-hybrid` | 369.3 | 1,216.5-1,216.5 | 1.52 | yes | 15.381x | 1.498x | 0.097x |
| MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,845.8 | 1,569.2-1,569.2 | 21.81 | **no** | `a100_sxm_80gb-x77-hybrid` | 369.9 | 1,123.9-1,123.9 | 1.65 | yes | 18.505x | 1.396x | 0.075x |
| MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,680.5 | 1,822.0-1,822.0 | 15.59 | **no** | `a100_sxm_80gb-x224-hybrid` | 369.3 | 1,216.5-1,216.5 | 1.52 | yes | 15.381x | 1.498x | 0.097x |
| MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,845.8 | 1,569.2-1,569.2 | 21.81 | **no** | `a100_sxm_80gb-x77-hybrid` | 369.9 | 1,123.9-1,123.9 | 1.65 | yes | 18.505x | 1.396x | 0.075x |
| MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,680.5 | 1,822.0-1,822.0 | 15.59 | **no** | `a100_sxm_80gb-x224-hybrid` | 369.3 | 1,216.5-1,216.5 | 1.52 | yes | 15.381x | 1.498x | 0.097x |
| MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,845.8 | 1,569.2-1,569.2 | 21.81 | **no** | `a100_sxm_80gb-x77-hybrid` | 369.9 | 1,123.9-1,123.9 | 1.65 | yes | 18.505x | 1.396x | 0.075x |
| MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,680.5 | 1,822.0-1,822.0 | 15.59 | **no** | `a100_sxm_80gb-x224-hybrid` | 369.3 | 1,216.5-1,216.5 | 1.52 | yes | 15.381x | 1.498x | 0.097x |
| MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 6,790.9 | 1,567.9-1,567.9 | 21.66 | **no** | `a100_sxm_80gb-x154-hybrid` | 366.7 | 1,168.0-1,168.0 | 1.57 | yes | 18.517x | 1.342x | 0.072x |
| MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,547.9 | 5,122.4-5,122.4 | 5.42 | **no** | `a100_sxm_80gb-x672-hybrid` | 363.0 | 1,258.4-1,258.4 | 1.44 | yes | 15.283x | 4.070x | 0.266x |
| MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,679.9 | 1,584.8-1,584.8 | 21.08 | **no** | `a100_sxm_80gb-x335-hybrid` | 364.5 | 1,223.7-1,223.7 | 1.49 | yes | 18.326x | 1.295x | 0.071x |
| MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,370.5 | 3,078.0-3,078.0 | 8.72 | **no** | `a100_sxm_80gb-x672-hybrid` | 363.0 | 1,258.4-1,258.4 | 1.44 | yes | 14.794x | 2.446x | 0.165x |
| MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,338.1 | 831.7-831.7 | 38.10 | **no** | `a100_sxm_80gb-x335-hybrid` | 337.9 | 1,064.2-1,064.2 | 1.59 | yes | 18.755x | 0.782x | 0.042x |
| MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,465.8 | 1,681.4-1,681.4 | 13.28 | **no** | `a100_sxm_80gb-x672-hybrid` | 363.0 | 1,258.4-1,258.4 | 1.44 | yes | 12.302x | 1.336x | 0.109x |
| MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,960.9 | 406.7-406.7 | 48.70 | **no** | `a100_sxm_80gb-x335-hybrid` | 212.3 | 605.9-605.9 | 1.75 | yes | 18.653x | 0.671x | 0.036x |
| MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,332.7 | 849.5-849.5 | 13.73 | **no** | `a100_sxm_80gb-x672-hybrid` | 279.3 | 839.4-839.4 | 1.66 | yes | 8.353x | 1.012x | 0.121x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,434.4 | 186.3-186.3 | 38.50 | **no** | `a100_sxm_80gb-x335-hybrid` | 101.5 | 301.4-301.4 | 1.68 | yes | 14.135x | 0.618x | 0.044x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 723.5 | 220.1-220.1 | 16.44 | **no** | `a100_sxm_80gb-x672-hybrid` | 148.4 | 432.1-432.1 | 1.72 | yes | 4.876x | 0.509x | 0.104x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 396.7 | 120.7-120.7 | 16.44 | **no** | `a100_sxm_80gb-x335-hybrid` | 56.2 | 119.3-119.3 | 2.36 | yes | 7.058x | 1.011x | 0.143x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 190.0 | 171.5-171.5 | 5.54 | **no** | `a100_sxm_80gb-x672-hybrid` | 71.9 | 207.3-207.3 | 1.73 | yes | 2.645x | 0.827x | 0.313x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.036x to 0.313x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | 3,064.9 | 2,001.7-2,001.7 | 7.66 | **no** | `b200_sxm-x71-nvl72-tensor` | 503.6 | 2,223.4-2,223.4 | 1.13 | yes | 6.086x | 0.900x | 0.148x |
| MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 3,548.1 | 2,048.0-2,048.0 | 8.66 | **no** | `b200_sxm-x87-nvl72-hybrid` | 485.8 | 2,085.5-2,085.5 | 1.16 | yes | 7.303x | 0.982x | 0.134x |
| MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,345.5 | 1,086.3-1,086.3 | 10.80 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 492.3 | 2,205.7-2,205.7 | 1.12 | yes | 4.765x | 0.492x | 0.103x |
| MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,345.5 | 1,086.3-1,086.3 | 10.80 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 492.3 | 2,205.7-2,205.7 | 1.12 | yes | 4.765x | 0.492x | 0.103x |
| MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,345.5 | 1,086.3-1,086.3 | 10.80 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 492.3 | 2,205.7-2,205.7 | 1.12 | yes | 4.765x | 0.492x | 0.103x |
| MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,179.3 | 1,070.8-1,070.8 | 10.18 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 492.3 | 2,205.7-2,205.7 | 1.12 | yes | 4.427x | 0.485x | 0.110x |
| MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,903.5 | 594.7-594.7 | 16.00 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 483.9 | 2,094.8-2,094.8 | 1.16 | yes | 3.934x | 0.284x | 0.072x |
| MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,576.3 | 316.4-316.4 | 24.91 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 463.2 | 1,880.3-1,880.3 | 1.23 | yes | 3.404x | 0.168x | 0.049x |
| MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 575.6 | 90.7-90.7 | 31.73 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 371.7 | 1,213.8-1,213.8 | 1.53 | yes | 1.549x | 0.075x | 0.048x |
| MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 158.2 | 22.8-22.8 | 34.68 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 221.5 | 533.1-533.1 | 2.08 | yes | 0.714x | 0.043x | 0.060x |
| MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x49` | 40.3 | 5.7-5.7 | 35.33 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 99.0 | 260.8-260.8 | 1.90 | yes | 0.407x | 0.022x | 0.054x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.048x to 0.148x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | 2,984.6 | 1,710.7-1,710.7 | 8.72 | **no** | `a100_sxm_80gb-x178-tensor` | 224.9 | 710.0-710.0 | 1.58 | yes | 13.268x | 2.409x | 0.182x |
| MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 3,483.3 | 3,148.7-3,148.7 | 5.53 | **no** | `a100_sxm_80gb-x168-tensor` | 224.5 | 708.7-708.7 | 1.58 | yes | 15.516x | 4.443x | 0.286x |
| MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,895.0 | 844.7-844.7 | 11.22 | **no** | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 665.2-665.2 | 1.54 | yes | 9.245x | 1.270x | 0.137x |
| MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,895.0 | 844.7-844.7 | 11.22 | **no** | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 665.2-665.2 | 1.54 | yes | 9.245x | 1.270x | 0.137x |
| MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,895.0 | 844.7-844.7 | 11.22 | **no** | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 665.2-665.2 | 1.54 | yes | 9.245x | 1.270x | 0.137x |
| MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,895.0 | 844.7-844.7 | 11.22 | **no** | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 665.2-665.2 | 1.54 | yes | 9.245x | 1.270x | 0.137x |
| MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,455.4 | 444.7-444.7 | 16.37 | **no** | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 665.2-665.2 | 1.54 | yes | 7.100x | 0.668x | 0.094x |
| MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,032.2 | 228.5-228.5 | 22.58 | **no** | `a100_sxm_80gb-x3805-hybrid` | 203.5 | 647.7-647.7 | 1.57 | yes | 5.071x | 0.353x | 0.070x |
| MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 342.9 | 64.8-64.8 | 26.44 | **no** | `a100_sxm_80gb-x3805-hybrid` | 163.4 | 431.4-431.4 | 1.89 | yes | 2.099x | 0.150x | 0.072x |
| MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 90.5 | 16.3-16.3 | 27.76 | **no** | `a100_sxm_80gb-x3805-hybrid` | 120.9 | 400.9-400.9 | 1.51 | yes | 0.749x | 0.041x | 0.054x |
| MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x68` | 22.9 | 4.1-4.1 | 28.02 | **no** | `a100_sxm_80gb-x3805-hybrid` | 53.9 | 172.3-172.3 | 1.57 | yes | 0.424x | 0.024x | 0.056x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.054x to 0.286x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | 2,556.9 | 1,743.7-1,743.7 | 7.33 | **no** | `b200_sxm-x170-nvl72-hybrid` | 469.2 | 2,077.8-2,077.8 | 1.13 | yes | 5.449x | 0.839x | 0.154x |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 3,359.6 | 2,529.4-2,529.4 | 6.64 | **no** | `b200_sxm-x116-nvl72-hybrid` | 471.0 | 2,078.7-2,078.7 | 1.13 | yes | 7.133x | 1.217x | 0.171x |
| MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,385.2 | 256.0-256.0 | 27.05 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,981.3-1,981.3 | 1.13 | yes | 3.093x | 0.129x | 0.042x |
| MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,385.2 | 256.0-256.0 | 27.05 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,981.3-1,981.3 | 1.13 | yes | 3.093x | 0.129x | 0.042x |
| MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,385.2 | 256.0-256.0 | 27.05 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,981.3-1,981.3 | 1.13 | yes | 3.093x | 0.129x | 0.042x |
| MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,385.2 | 256.0-256.0 | 27.05 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,981.3-1,981.3 | 1.13 | yes | 3.093x | 0.129x | 0.042x |
| MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,385.2 | 256.0-256.0 | 27.05 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,981.3-1,981.3 | 1.13 | yes | 3.093x | 0.129x | 0.042x |
| MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,342.8 | 255.5-255.5 | 26.27 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,981.3-1,981.3 | 1.13 | yes | 2.998x | 0.129x | 0.043x |
| MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 554.4 | 66.1-66.1 | 41.97 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 401.8 | 1,593.9-1,593.9 | 1.26 | yes | 1.380x | 0.041x | 0.030x |
| MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 155.8 | 18.6-18.6 | 41.97 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 278.1 | 1,095.4-1,095.4 | 1.27 | yes | 0.560x | 0.017x | 0.030x |
| MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 39.9 | 4.6-4.6 | 42.96 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 126.7 | 475.3-475.3 | 1.33 | yes | 0.315x | 0.010x | 0.031x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.030x to 0.171x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | 2,389.5 | 1,701.2-1,701.2 | 7.02 | **no** | `a100_sxm_80gb-x316-tensor` | 224.4 | 713.7-713.7 | 1.57 | yes | 10.646x | 2.383x | 0.224x |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 3,205.3 | 1,850.1-1,850.1 | 8.66 | **no** | `a100_sxm_80gb-x336-hybrid` | 190.6 | 626.1-626.1 | 1.52 | yes | 16.821x | 2.955x | 0.176x |
| MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 873.9 | 2,598.6-2,598.6 | 1.68 | yes | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 636.0-636.0 | 1.49 | yes | 4.622x | 4.086x | 0.884x |
| MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 805.6 | 2,090.1-2,090.1 | 1.93 | yes | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 636.0-636.0 | 1.49 | yes | 4.260x | 3.287x | 0.771x |
| MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 796.3 | 182.5-182.5 | 21.81 | **no** | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 636.0-636.0 | 1.49 | yes | 4.211x | 0.287x | 0.068x |
| MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 796.3 | 182.5-182.5 | 21.81 | **no** | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 636.0-636.0 | 1.49 | yes | 4.211x | 0.287x | 0.068x |
| MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 796.3 | 182.5-182.5 | 21.81 | **no** | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 636.0-636.0 | 1.49 | yes | 4.211x | 0.287x | 0.068x |
| MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 796.3 | 182.5-182.5 | 21.81 | **no** | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 636.0-636.0 | 1.49 | yes | 4.211x | 0.287x | 0.068x |
| MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 327.2 | 91.0-91.0 | 17.97 | **no** | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 636.0-636.0 | 1.49 | yes | 1.730x | 0.143x | 0.083x |
| MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 90.0 | 25.6-25.6 | 17.57 | **no** | `a100_sxm_80gb-x18971-hybrid` | 139.5 | 447.1-447.1 | 1.56 | yes | 0.645x | 0.057x | 0.089x |
| MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 22.9 | 6.4-6.4 | 17.83 | **no** | `a100_sxm_80gb-x18971-hybrid` | 77.4 | 335.4-335.4 | 1.15 | yes | 0.295x | 0.019x | 0.065x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.065x to 0.884x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 2 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,293.8 | 1,377.1-1,377.1 | 15.59 | **no** | `b200_sxm-x78-nvl72-hybrid` | 490.3 | 2,078.5-2,078.5 | 1.18 | yes | 8.758x | 0.663x | 0.076x |
| MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,202.7 | 1,300.6-1,300.6 | 16.16 | **no** | `b200_sxm-x87-nvl72-hybrid` | 494.2 | 2,116.2-2,116.2 | 1.17 | yes | 8.504x | 0.615x | 0.072x |
| MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,293.8 | 1,377.1-1,377.1 | 15.59 | **no** | `b200_sxm-x78-nvl72-hybrid` | 490.3 | 2,078.5-2,078.5 | 1.18 | yes | 8.758x | 0.663x | 0.076x |
| MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,202.7 | 1,300.6-1,300.6 | 16.16 | **no** | `b200_sxm-x87-nvl72-hybrid` | 494.2 | 2,116.2-2,116.2 | 1.17 | yes | 8.504x | 0.615x | 0.072x |
| MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,293.8 | 1,377.1-1,377.1 | 15.59 | **no** | `b200_sxm-x78-nvl72-hybrid` | 477.9 | 1,928.0-1,928.0 | 1.24 | yes | 8.984x | 0.714x | 0.080x |
| MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,202.7 | 1,300.6-1,300.6 | 16.16 | **no** | `b200_sxm-x87-nvl72-hybrid` | 482.8 | 1,972.2-1,972.2 | 1.22 | yes | 8.706x | 0.659x | 0.076x |
| MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,293.8 | 1,377.1-1,377.1 | 15.59 | **no** | `b200_sxm-x78-nvl72-hybrid` | 455.6 | 1,686.9-1,686.9 | 1.35 | yes | 9.424x | 0.816x | 0.087x |
| MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,202.7 | 1,300.6-1,300.6 | 16.16 | **no** | `b200_sxm-x87-nvl72-hybrid` | 461.9 | 1,739.0-1,739.0 | 1.33 | yes | 9.099x | 0.748x | 0.082x |
| MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 4,249.4 | 1,287.8-1,287.8 | 16.50 | **no** | `b200_sxm-x150-nvl72-hybrid` | 456.9 | 1,700.4-1,700.4 | 1.34 | yes | 9.301x | 0.757x | 0.081x |
| MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 4,172.4 | 1,383.3-1,383.3 | 15.08 | **no** | `b200_sxm-x173-nvl72-hybrid` | 464.5 | 1,757.7-1,757.7 | 1.32 | yes | 8.983x | 0.787x | 0.088x |
| MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 4,179.8 | 697.3-697.3 | 29.97 | **no** | `b200_sxm-x150-nvl72-hybrid` | 417.5 | 1,394.9-1,394.9 | 1.50 | yes | 10.012x | 0.500x | 0.050x |
| MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,144.5 | 1,410.8-1,410.8 | 14.69 | **no** | `b200_sxm-x347-nvl72-hybrid` | 464.2 | 1,750.1-1,750.1 | 1.33 | yes | 8.928x | 0.806x | 0.090x |
| MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 3,902.5 | 686.3-686.3 | 28.43 | **no** | `b200_sxm-x200-nvl72-hybrid` | 387.1 | 1,163.0-1,163.0 | 1.66 | yes | 10.082x | 0.590x | 0.059x |
| MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,697.7 | 746.0-746.0 | 24.78 | **no** | `b200_sxm-x347-nvl72-hybrid` | 426.2 | 1,415.6-1,415.6 | 1.51 | yes | 8.675x | 0.527x | 0.061x |
| MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 2,400.0 | 177.8-177.8 | 67.50 | **no** | `b200_sxm-x200-nvl72-hybrid` | 266.4 | 551.6-551.6 | 2.41 | yes | 9.009x | 0.322x | 0.036x |
| MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,259.3 | 372.8-372.8 | 30.30 | **no** | `b200_sxm-x347-nvl72-hybrid` | 310.8 | 741.2-741.2 | 2.10 | yes | 7.269x | 0.503x | 0.069x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 881.9 | 153.4-153.4 | 28.75 | **no** | `b200_sxm-x173-nvl72-hybrid` | 152.2 | 184.9-184.9 | 4.12 | yes | 5.793x | 0.830x | 0.143x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 792.0 | 94.9-94.9 | 41.75 | **no** | `b200_sxm-x347-nvl72-hybrid` | 197.6 | 307.0-307.0 | 3.22 | yes | 4.007x | 0.309x | 0.077x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 345.6 | 96.9-96.9 | 17.84 | **no** | `b200_sxm-x200-nvl72-hybrid` | 89.2 | 102.3-102.3 | 4.36 | yes | 3.875x | 0.947x | 0.244x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 215.4 | 23.0-23.0 | 46.76 | **no** | `b200_sxm-x347-nvl72-hybrid` | 114.4 | 151.3-151.3 | 3.78 | yes | 1.884x | 0.152x | 0.081x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.036x to 0.244x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,100.9 | 1,011.9-1,011.9 | 20.26 | **no** | `a100_sxm_80gb-x208-tensor` | 227.6 | 717.2-717.2 | 1.59 | yes | 18.019x | 1.411x | 0.078x |
| MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,649.2 | 1,549.1-1,549.1 | 11.78 | **no** | `a100_sxm_80gb-x280-tensor` | 229.0 | 722.3-722.3 | 1.59 | yes | 15.936x | 2.145x | 0.135x |
| MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,100.9 | 1,011.9-1,011.9 | 20.26 | **no** | `a100_sxm_80gb-x208-hybrid` | 211.6 | 662.3-662.3 | 1.60 | yes | 19.385x | 1.528x | 0.079x |
| MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,649.2 | 1,549.1-1,549.1 | 11.78 | **no** | `a100_sxm_80gb-x280-hybrid` | 212.9 | 671.3-671.3 | 1.59 | yes | 17.138x | 2.308x | 0.135x |
| MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,100.9 | 1,011.9-1,011.9 | 20.26 | **no** | `a100_sxm_80gb-x208-hybrid` | 211.6 | 662.3-662.3 | 1.60 | yes | 19.385x | 1.528x | 0.079x |
| MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,649.2 | 1,549.1-1,549.1 | 11.78 | **no** | `a100_sxm_80gb-x280-hybrid` | 212.9 | 671.3-671.3 | 1.59 | yes | 17.138x | 2.308x | 0.135x |
| MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,100.9 | 1,011.9-1,011.9 | 20.26 | **no** | `a100_sxm_80gb-x208-hybrid` | 195.4 | 591.7-591.7 | 1.65 | yes | 20.982x | 1.710x | 0.082x |
| MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,649.2 | 1,549.1-1,549.1 | 11.78 | **no** | `a100_sxm_80gb-x280-hybrid` | 202.3 | 549.1-549.1 | 1.84 | yes | 18.035x | 2.821x | 0.156x |
| MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 4,086.5 | 969.9-969.9 | 21.07 | **no** | `a100_sxm_80gb-x249-hybrid` | 182.3 | 470.1-470.1 | 1.94 | yes | 22.419x | 2.063x | 0.092x |
| MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,642.9 | 696.4-696.4 | 26.16 | **no** | `a100_sxm_80gb-x672-hybrid` | 205.8 | 583.0-583.0 | 1.77 | yes | 17.699x | 1.194x | 0.067x |
| MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 3,837.2 | 504.6-504.6 | 38.02 | **no** | `a100_sxm_80gb-x249-hybrid` | 178.1 | 527.2-527.2 | 1.69 | yes | 21.541x | 0.957x | 0.044x |
| MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,274.2 | 367.1-367.1 | 44.60 | **no** | `a100_sxm_80gb-x672-hybrid` | 189.6 | 541.6-541.6 | 1.75 | yes | 17.265x | 0.678x | 0.039x |
| MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 3,568.8 | 493.6-493.6 | 36.15 | **no** | `a100_sxm_80gb-x373-hybrid` | 168.9 | 490.6-490.6 | 1.72 | yes | 21.129x | 1.006x | 0.048x |
| MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,736.1 | 363.4-363.4 | 37.64 | **no** | `a100_sxm_80gb-x672-hybrid` | 177.8 | 559.3-559.3 | 1.59 | yes | 15.390x | 0.650x | 0.042x |
| MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 1,932.0 | 128.3-128.3 | 75.27 | **no** | `a100_sxm_80gb-x373-hybrid` | 105.4 | 271.9-271.9 | 1.94 | yes | 18.326x | 0.472x | 0.026x |
| MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,183.6 | 93.6-93.6 | 63.22 | **no** | `a100_sxm_80gb-x672-hybrid` | 133.9 | 363.2-363.2 | 1.84 | yes | 8.840x | 0.258x | 0.029x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 782.0 | 130.2-130.2 | 30.02 | **no** | `a100_sxm_80gb-x373-hybrid` | 47.0 | 130.7-130.7 | 1.80 | yes | 16.643x | 0.996x | 0.060x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 345.9 | 23.6-23.6 | 73.35 | **no** | `a100_sxm_80gb-x672-hybrid` | 67.2 | 177.6-177.6 | 1.89 | yes | 5.150x | 0.133x | 0.026x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 231.4 | 33.4-33.4 | 34.59 | **no** | `a100_sxm_80gb-x373-hybrid` | 22.0 | 58.1-58.1 | 1.89 | yes | 10.535x | 0.576x | 0.055x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 89.5 | 22.5-22.5 | 19.86 | **no** | `a100_sxm_80gb-x672-hybrid` | 28.7 | 82.4-82.4 | 1.74 | yes | 3.120x | 0.274x | 0.088x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.026x to 0.156x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-qwen3-8b-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x180` | 3,783.5 | not applicable | -- | -- | `b200_sxm-x92-nvl72-hybrid` | 772.6 | not applicable | -- | -- | 4.897x | -- | -- |
| Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 8,249.0 | not applicable | -- | -- | `b200_sxm-x58-nvl72-tensor` | 849.5 | not applicable | -- | -- | 9.711x | -- | -- |

### `n6_vs_a100-qwen3-8b-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x227` | 3,567.0 | not applicable | -- | -- | `a100_sxm_80gb-x224-tensor` | 468.9 | not applicable | -- | -- | 7.606x | -- | -- |
| Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 8,205.5 | not applicable | -- | -- | `a100_sxm_80gb-x112-tensor` | 389.3 | not applicable | -- | -- | 21.076x | -- | -- |

### `n5_vs_b200-qwen3-8b-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x60-romfill` | 7,120.3 | not applicable | -- | -- | `b200_sxm-x31-nvl72-tensor` | 1,034.4 | not applicable | -- | -- | 6.883x | -- | -- |
| Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 9,134.8 | not applicable | -- | -- | `b200_sxm-x29-nvl72-tensor` | 1,018.3 | not applicable | -- | -- | 8.971x | -- | -- |
| Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x139-romfill` | 3,018.8 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,087.6 | not applicable | -- | -- | 2.776x | -- | -- |
| Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,737.9 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,087.6 | not applicable | -- | -- | 2.517x | -- | -- |
| Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,737.9 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,087.6 | not applicable | -- | -- | 2.517x | -- | -- |
| Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,737.9 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,087.6 | not applicable | -- | -- | 2.517x | -- | -- |
| Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,737.9 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,087.6 | not applicable | -- | -- | 2.517x | -- | -- |
| Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1,809.5 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,075.6 | not applicable | -- | -- | 1.682x | -- | -- |
| Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 602.2 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 851.3 | not applicable | -- | -- | 0.707x | -- | -- |
| Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 158.3 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 481.1 | not applicable | -- | -- | 0.329x | -- | -- |
| Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 40.0 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 177.1 | not applicable | -- | -- | 0.226x | -- | -- |

### `n6_vs_a100-qwen3-8b-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 7,114.3 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 461.8 | not applicable | -- | -- | 15.405x | -- | -- |
| Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 9,194.4 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 461.8 | not applicable | -- | -- | 19.909x | -- | -- |
| Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196-romfill` | 2,704.1 | not applicable | -- | -- | `a100_sxm_80gb-x10969-tensor` | 475.1 | not applicable | -- | -- | 5.692x | -- | -- |
| Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 2,461.8 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 456.0 | not applicable | -- | -- | 5.398x | -- | -- |
| Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 2,041.1 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 456.0 | not applicable | -- | -- | 4.476x | -- | -- |
| Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 1,518.6 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 456.0 | not applicable | -- | -- | 3.330x | -- | -- |
| Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,490.4 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 456.0 | not applicable | -- | -- | 3.268x | -- | -- |
| Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,191.2 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 456.0 | not applicable | -- | -- | 2.612x | -- | -- |
| Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 354.2 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 419.8 | not applicable | -- | -- | 0.844x | -- | -- |
| Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 91.5 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 256.3 | not applicable | -- | -- | 0.357x | -- | -- |
| Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 23.0 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 112.7 | not applicable | -- | -- | 0.204x | -- | -- |

### `n5_vs_b200-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 3,387.3 | 501.3-501.3 | 33.79 | **no** | `b200_sxm-x58-nvl72-tensor` | 559.2 | 1,436.7-1,436.7 | 1.95 | yes | 6.058x | 0.349x | 0.058x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3,790.6 | 1,671.8-1,671.8 | 11.34 | **no** | `b200_sxm-x58-nvl72-tensor` | 559.2 | 1,436.7-1,436.7 | 1.95 | yes | 6.779x | 1.164x | 0.172x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2,745.8 | 1,471.8-1,471.8 | 9.33 | **no** | `b200_sxm-x142-nvl72-hybrid` | 558.7 | 1,429.0-1,429.0 | 1.95 | yes | 4.915x | 1.030x | 0.210x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,786.1 | 6,026.0-6,026.0 | 2.31 | yes | `b200_sxm-x953-nvl72-hybrid` | 548.5 | 1,353.4-1,353.4 | 2.03 | yes | 5.079x | 4.452x | 0.877x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2,745.8 | 1,471.8-1,471.8 | 9.33 | **no** | `b200_sxm-x142-nvl72-hybrid` | 548.5 | 1,402.2-1,402.2 | 1.96 | yes | 5.006x | 1.050x | 0.210x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,786.1 | 6,026.0-6,026.0 | 2.31 | yes | `b200_sxm-x953-nvl72-hybrid` | 548.5 | 1,353.4-1,353.4 | 2.03 | yes | 5.079x | 4.452x | 0.877x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2,745.8 | 1,471.8-1,471.8 | 9.33 | **no** | `b200_sxm-x142-nvl72-hybrid` | 535.4 | 1,364.6-1,364.6 | 1.96 | yes | 5.128x | 1.078x | 0.210x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,786.1 | 6,026.0-6,026.0 | 2.31 | yes | `b200_sxm-x953-nvl72-hybrid` | 548.5 | 1,353.4-1,353.4 | 2.03 | yes | 5.079x | 4.452x | 0.877x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2,745.8 | 1,471.8-1,471.8 | 9.33 | **no** | `b200_sxm-x142-nvl72-hybrid` | 535.2 | 1,313.4-1,313.4 | 2.04 | yes | 5.130x | 1.121x | 0.218x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,786.1 | 6,026.0-6,026.0 | 2.31 | yes | `b200_sxm-x953-nvl72-hybrid` | 543.1 | 1,304.6-1,304.6 | 2.08 | yes | 5.130x | 4.619x | 0.900x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2,745.8 | 1,471.8-1,471.8 | 9.33 | **no** | `b200_sxm-x142-nvl72-hybrid` | 482.5 | 957.3-957.3 | 2.52 | yes | 5.691x | 1.537x | 0.270x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,786.1 | 6,026.0-6,026.0 | 2.31 | yes | `b200_sxm-x953-nvl72-hybrid` | 531.8 | 1,249.9-1,249.9 | 2.13 | yes | 5.239x | 4.821x | 0.920x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,713.1 | 914.2-914.2 | 14.84 | **no** | `b200_sxm-x173-nvl72-hybrid` | 445.9 | 939.5-939.5 | 2.37 | yes | 6.084x | 0.973x | 0.160x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,585.1 | 4,566.2-4,566.2 | 2.83 | yes | `b200_sxm-x953-nvl72-hybrid` | 525.7 | 1,062.9-1,062.9 | 2.47 | yes | 4.917x | 4.296x | 0.874x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 1,579.6 | 169.2-169.2 | 46.69 | **no** | `b200_sxm-x178-pipeline` | 320.0 | 583.2-583.2 | 2.74 | yes | 4.936x | 0.290x | 0.059x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,697.1 | 1,759.8-1,759.8 | 4.82 | yes | `b200_sxm-x953-nvl72-hybrid` | 473.6 | 803.9-803.9 | 2.95 | yes | 3.583x | 2.189x | 0.611x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 576.3 | 79.4-79.4 | 36.29 | **no** | `b200_sxm-x178-pipeline` | 160.8 | 248.4-248.4 | 3.24 | yes | 3.583x | 0.320x | 0.089x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 635.2 | 67.7-67.7 | 46.89 | **no** | `b200_sxm-x953-pipeline` | 349.3 | 354.1-354.1 | 4.93 | yes | 1.818x | 0.191x | 0.105x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 144.5 | 55.1-55.1 | 13.12 | **no** | `b200_sxm-x178-pipeline` | 58.3 | 147.4-147.4 | 1.98 | yes | 2.477x | 0.374x | 0.151x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 175.7 | 17.0-17.0 | 51.61 | **no** | `b200_sxm-x953-pipeline` | 192.5 | 222.0-222.0 | 4.34 | yes | 0.913x | 0.077x | 0.084x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.058x to 0.920x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 7 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x44` | 4,377.2 | 1,268.2-1,268.2 | 17.26 | **no** | `b200_sxm-x22-nvl72-tensor` | 604.9 | 2,326.7-2,326.7 | 1.30 | yes | 7.236x | 0.545x | 0.075x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,240.3 | 1,201.4-1,201.4 | 17.65 | **no** | `b200_sxm-x58-nvl72-tensor` | 619.0 | 2,463.7-2,463.7 | 1.26 | yes | 6.850x | 0.488x | 0.071x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 4,351.3 | 1,103.8-1,103.8 | 19.71 | **no** | `b200_sxm-x26-nvl72-tensor` | 592.1 | 2,067.4-2,067.4 | 1.43 | yes | 7.349x | 0.534x | 0.073x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,240.3 | 1,201.4-1,201.4 | 17.65 | **no** | `b200_sxm-x58-nvl72-tensor` | 603.9 | 2,135.5-2,135.5 | 1.41 | yes | 7.022x | 0.563x | 0.080x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 4,351.3 | 1,103.8-1,103.8 | 19.71 | **no** | `b200_sxm-x26-hybrid` | 578.4 | 1,987.7-1,987.7 | 1.45 | yes | 7.524x | 0.555x | 0.074x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,240.3 | 1,201.4-1,201.4 | 17.65 | **no** | `b200_sxm-x58-hybrid` | 583.3 | 2,006.8-2,006.8 | 1.45 | yes | 7.269x | 0.599x | 0.082x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 4,351.3 | 1,103.8-1,103.8 | 19.71 | **no** | `b200_sxm-x26-hybrid` | 548.5 | 1,623.1-1,623.1 | 1.69 | yes | 7.933x | 0.680x | 0.086x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,240.3 | 1,201.4-1,201.4 | 17.65 | **no** | `b200_sxm-x58-hybrid` | 583.3 | 2,006.8-2,006.8 | 1.45 | yes | 7.269x | 0.599x | 0.082x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 4,311.3 | 1,133.3-1,133.3 | 19.02 | **no** | `b200_sxm-x44-hybrid` | 540.4 | 1,519.3-1,519.3 | 1.78 | yes | 7.978x | 0.746x | 0.094x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,240.3 | 1,201.4-1,201.4 | 17.65 | **no** | `b200_sxm-x58-hybrid` | 554.6 | 1,652.2-1,652.2 | 1.68 | yes | 7.646x | 0.727x | 0.095x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,249.7 | 1,141.4-1,141.4 | 18.62 | **no** | `b200_sxm-x173-nvl72-hybrid` | 573.4 | 1,784.4-1,784.4 | 1.61 | yes | 7.412x | 0.640x | 0.086x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,230.4 | 1,220.3-1,220.3 | 17.33 | **no** | `b200_sxm-x116-nvl72-hybrid` | 557.9 | 1,648.2-1,648.2 | 1.69 | yes | 7.583x | 0.740x | 0.098x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,249.7 | 1,141.4-1,141.4 | 18.62 | **no** | `b200_sxm-x173-nvl72-hybrid` | 537.4 | 1,454.1-1,454.1 | 1.85 | yes | 7.908x | 0.785x | 0.099x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,230.4 | 1,220.3-1,220.3 | 17.33 | **no** | `b200_sxm-x231-nvl72-hybrid` | 551.7 | 1,540.1-1,540.1 | 1.79 | yes | 7.667x | 0.792x | 0.103x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,282.0 | 569.7-569.7 | 28.81 | **no** | `b200_sxm-x173-nvl72-hybrid` | 395.0 | 782.9-782.9 | 2.52 | yes | 8.310x | 0.728x | 0.088x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,892.8 | 633.6-633.6 | 30.72 | **no** | `b200_sxm-x347-nvl72-hybrid` | 469.7 | 1,028.1-1,028.1 | 2.28 | yes | 8.288x | 0.616x | 0.074x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,633.5 | 262.4-262.4 | 31.13 | **no** | `b200_sxm-x173-nvl72-hybrid` | 222.1 | 427.7-427.7 | 2.60 | yes | 7.355x | 0.613x | 0.083x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,697.5 | 311.7-311.7 | 43.27 | **no** | `b200_sxm-x347-nvl72-hybrid` | 303.6 | 567.9-567.9 | 2.67 | yes | 8.884x | 0.549x | 0.062x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 503.6 | 166.3-166.3 | 15.14 | **no** | `b200_sxm-x173-nvl72-hybrid` | 115.4 | 182.7-182.7 | 3.16 | yes | 4.364x | 0.911x | 0.209x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,013.1 | 238.6-238.6 | 21.23 | **no** | `b200_sxm-x347-nvl72-hybrid` | 159.4 | 279.2-279.2 | 2.86 | yes | 6.354x | 0.855x | 0.135x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.062x to 0.209x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4,355.9 | 1,187.0-1,187.0 | 18.35 | **no** | `b200_sxm-x24-nvl72-tensor` | 607.1 | 2,417.4-2,417.4 | 1.26 | yes | 7.175x | 0.491x | 0.068x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,268.0 | 1,211.4-1,211.4 | 17.62 | **no** | `b200_sxm-x58-nvl72-tensor` | 620.0 | 2,477.5-2,477.5 | 1.25 | yes | 6.884x | 0.489x | 0.071x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4,355.9 | 1,187.0-1,187.0 | 18.35 | **no** | `b200_sxm-x24-hybrid` | 595.5 | 2,128.5-2,128.5 | 1.40 | yes | 7.315x | 0.558x | 0.076x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,268.0 | 1,211.4-1,211.4 | 17.62 | **no** | `b200_sxm-x58-nvl72-tensor` | 607.1 | 2,205.0-2,205.0 | 1.38 | yes | 7.030x | 0.549x | 0.078x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4,355.9 | 1,187.0-1,187.0 | 18.35 | **no** | `b200_sxm-x24-hybrid` | 586.2 | 2,004.7-2,004.7 | 1.46 | yes | 7.430x | 0.592x | 0.080x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,268.0 | 1,211.4-1,211.4 | 17.62 | **no** | `b200_sxm-x58-hybrid` | 583.6 | 2,023.4-2,023.4 | 1.44 | yes | 7.313x | 0.599x | 0.082x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4,355.9 | 1,187.0-1,187.0 | 18.35 | **no** | `b200_sxm-x24-hybrid` | 552.6 | 1,639.1-1,639.1 | 1.69 | yes | 7.883x | 0.724x | 0.092x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,268.0 | 1,211.4-1,211.4 | 17.62 | **no** | `b200_sxm-x58-hybrid` | 583.6 | 2,023.4-2,023.4 | 1.44 | yes | 7.313x | 0.599x | 0.082x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 4,340.6 | 1,140.1-1,140.1 | 19.04 | **no** | `b200_sxm-x44-hybrid` | 541.0 | 1,580.5-1,580.5 | 1.71 | yes | 8.023x | 0.721x | 0.090x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,268.0 | 1,211.4-1,211.4 | 17.62 | **no** | `b200_sxm-x58-hybrid` | 555.0 | 1,709.5-1,709.5 | 1.62 | yes | 7.690x | 0.709x | 0.092x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,278.1 | 1,148.2-1,148.2 | 18.63 | **no** | `b200_sxm-x173-nvl72-hybrid` | 573.7 | 1,836.9-1,836.9 | 1.56 | yes | 7.457x | 0.625x | 0.084x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,257.6 | 1,230.9-1,230.9 | 17.30 | **no** | `b200_sxm-x116-nvl72-hybrid` | 558.4 | 1,708.1-1,708.1 | 1.63 | yes | 7.625x | 0.721x | 0.095x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,278.1 | 1,148.2-1,148.2 | 18.63 | **no** | `b200_sxm-x173-nvl72-hybrid` | 538.0 | 1,514.2-1,514.2 | 1.78 | yes | 7.951x | 0.758x | 0.095x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,257.6 | 1,230.9-1,230.9 | 17.30 | **no** | `b200_sxm-x231-nvl72-hybrid` | 552.2 | 1,593.8-1,593.8 | 1.73 | yes | 7.710x | 0.772x | 0.100x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,393.8 | 574.8-574.8 | 29.52 | **no** | `b200_sxm-x173-nvl72-hybrid` | 401.0 | 828.1-828.1 | 2.42 | yes | 8.462x | 0.694x | 0.082x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,018.6 | 638.3-638.3 | 31.48 | **no** | `b200_sxm-x347-nvl72-hybrid` | 472.1 | 1,063.5-1,063.5 | 2.22 | yes | 8.512x | 0.600x | 0.071x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,747.7 | 266.8-266.8 | 32.75 | **no** | `b200_sxm-x173-nvl72-hybrid` | 229.8 | 362.7-362.7 | 3.17 | yes | 7.606x | 0.736x | 0.097x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,867.5 | 314.7-314.7 | 45.56 | **no** | `b200_sxm-x347-nvl72-hybrid` | 305.2 | 596.7-596.7 | 2.56 | yes | 9.396x | 0.527x | 0.056x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 547.7 | 173.7-173.7 | 15.76 | **no** | `b200_sxm-x173-nvl72-hybrid` | 120.8 | 201.7-201.7 | 3.00 | yes | 4.534x | 0.862x | 0.190x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,113.7 | 246.3-246.3 | 22.61 | **no** | `b200_sxm-x347-nvl72-hybrid` | 162.1 | 301.1-301.1 | 2.69 | yes | 6.869x | 0.818x | 0.119x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.056x to 0.190x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 375.6-375.6 | 26.18 | **no** | `b200_sxm-x157-nvl72-hybrid` | 409.5 | 1,347.4-1,347.4 | 1.52 | yes | 4.804x | 0.279x | 0.058x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 2,132.7 | 913.5-913.5 | 11.67 | **no** | `b200_sxm-x116-nvl72-hybrid` | 411.6 | 1,367.7-1,367.7 | 1.50 | yes | 5.181x | 0.668x | 0.129x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 375.6-375.6 | 26.18 | **no** | `b200_sxm-x157-nvl72-hybrid` | 409.5 | 1,347.4-1,347.4 | 1.52 | yes | 4.804x | 0.279x | 0.058x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,080.6 | 875.8-875.8 | 11.88 | **no** | `b200_sxm-x289-nvl72-hybrid` | 410.0 | 1,332.1-1,332.1 | 1.54 | yes | 5.075x | 0.657x | 0.130x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 375.6-375.6 | 26.18 | **no** | `b200_sxm-x157-nvl72-hybrid` | 400.8 | 1,215.0-1,215.0 | 1.65 | yes | 4.907x | 0.309x | 0.063x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,080.6 | 875.8-875.8 | 11.88 | **no** | `b200_sxm-x289-nvl72-hybrid` | 410.0 | 1,332.1-1,332.1 | 1.54 | yes | 5.075x | 0.657x | 0.130x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 375.6-375.6 | 26.18 | **no** | `b200_sxm-x157-nvl72-hybrid` | 397.3 | 1,192.4-1,192.4 | 1.67 | yes | 4.951x | 0.315x | 0.064x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,080.6 | 875.8-875.8 | 11.88 | **no** | `b200_sxm-x289-nvl72-hybrid` | 396.2 | 1,241.9-1,241.9 | 1.60 | yes | 5.251x | 0.705x | 0.134x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 375.6-375.6 | 26.18 | **no** | `b200_sxm-x157-nvl72-hybrid` | 377.8 | 991.7-991.7 | 1.90 | yes | 5.207x | 0.379x | 0.073x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,080.6 | 875.8-875.8 | 11.88 | **no** | `b200_sxm-x289-nvl72-hybrid` | 393.2 | 1,122.0-1,122.0 | 1.75 | yes | 5.291x | 0.781x | 0.148x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 375.6-375.6 | 26.18 | **no** | `b200_sxm-x157-nvl72-hybrid` | 334.3 | 710.2-710.2 | 2.35 | yes | 5.883x | 0.529x | 0.090x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,080.6 | 875.8-875.8 | 11.88 | **no** | `b200_sxm-x289-nvl72-hybrid` | 371.0 | 920.3-920.3 | 2.02 | yes | 5.608x | 0.952x | 0.170x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,953.8 | 198.2-198.2 | 49.30 | **no** | `b200_sxm-x157-nvl72-hybrid` | 281.9 | 567.6-567.6 | 2.48 | yes | 6.930x | 0.349x | 0.050x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,998.4 | 471.0-471.0 | 21.21 | **no** | `b200_sxm-x289-nvl72-hybrid` | 326.0 | 653.0-653.0 | 2.50 | yes | 6.131x | 0.721x | 0.118x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,320.2 | 89.6-89.6 | 73.66 | **no** | `b200_sxm-x173-nvl72-hybrid` | 165.2 | 251.5-251.5 | 3.29 | yes | 7.990x | 0.356x | 0.045x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,479.2 | 233.7-233.7 | 31.64 | **no** | `b200_sxm-x347-nvl72-hybrid` | 227.4 | 375.6-375.6 | 3.03 | yes | 6.504x | 0.622x | 0.096x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 529.2 | 42.7-42.7 | 62.03 | **no** | `b200_sxm-x173-nvl72-hybrid` | 71.3 | 118.5-118.5 | 3.01 | yes | 7.421x | 0.360x | 0.048x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 671.5 | 59.7-59.7 | 56.25 | **no** | `b200_sxm-x347-nvl72-hybrid` | 113.2 | 173.0-173.0 | 3.27 | yes | 5.930x | 0.345x | 0.058x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 149.7 | 32.1-32.1 | 23.29 | **no** | `b200_sxm-x173-nvl72-hybrid` | 28.9 | 48.6-48.6 | 2.97 | yes | 5.182x | 0.661x | 0.128x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 198.8 | 22.2-22.2 | 44.68 | **no** | `b200_sxm-x347-nvl72-hybrid` | 44.2 | 74.8-74.8 | 2.95 | yes | 4.499x | 0.297x | 0.066x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.045x to 0.170x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 431.6-431.6 | 23.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 421.6 | 1,522.6-1,522.6 | 1.38 | yes | 4.854x | 0.283x | 0.058x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,253.4 | 898.3-898.3 | 12.54 | **no** | `b200_sxm-x144-nvl72-hybrid` | 422.2 | 1,541.5-1,541.5 | 1.37 | yes | 5.337x | 0.583x | 0.109x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 431.6-431.6 | 23.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 421.6 | 1,522.6-1,522.6 | 1.38 | yes | 4.854x | 0.283x | 0.058x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,253.4 | 898.3-898.3 | 12.54 | **no** | `b200_sxm-x144-nvl72-hybrid` | 422.2 | 1,541.5-1,541.5 | 1.37 | yes | 5.337x | 0.583x | 0.109x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 431.6-431.6 | 23.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 408.3 | 1,356.3-1,356.3 | 1.51 | yes | 5.011x | 0.318x | 0.064x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,253.4 | 898.3-898.3 | 12.54 | **no** | `b200_sxm-x144-nvl72-hybrid` | 409.4 | 1,363.3-1,363.3 | 1.50 | yes | 5.504x | 0.659x | 0.120x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 431.6-431.6 | 23.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 399.1 | 1,304.5-1,304.5 | 1.53 | yes | 5.127x | 0.331x | 0.065x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,253.4 | 898.3-898.3 | 12.54 | **no** | `b200_sxm-x144-nvl72-hybrid` | 402.0 | 1,320.9-1,320.9 | 1.52 | yes | 5.606x | 0.680x | 0.121x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 431.6-431.6 | 23.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 378.9 | 1,079.6-1,079.6 | 1.76 | yes | 5.400x | 0.400x | 0.074x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,253.4 | 898.3-898.3 | 12.54 | **no** | `b200_sxm-x144-nvl72-hybrid` | 382.2 | 1,094.4-1,094.4 | 1.75 | yes | 5.895x | 0.821x | 0.139x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 431.6-431.6 | 23.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 340.3 | 801.6-801.6 | 2.12 | yes | 6.013x | 0.539x | 0.090x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,237.3 | 901.0-901.0 | 12.42 | **no** | `b200_sxm-x347-nvl72-hybrid` | 385.7 | 1,082.9-1,082.9 | 1.78 | yes | 5.801x | 0.832x | 0.143x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,024.2 | 226.9-226.9 | 44.60 | **no** | `b200_sxm-x137-nvl72-hybrid` | 284.0 | 540.6-540.6 | 2.63 | yes | 7.128x | 0.420x | 0.059x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,190.2 | 474.1-474.1 | 23.10 | **no** | `b200_sxm-x347-nvl72-hybrid` | 352.2 | 816.2-816.2 | 2.16 | yes | 6.219x | 0.581x | 0.093x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,406.1 | 90.9-90.9 | 77.38 | **no** | `b200_sxm-x173-nvl72-hybrid` | 177.0 | 308.4-308.4 | 2.87 | yes | 7.943x | 0.295x | 0.037x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,826.7 | 238.9-238.9 | 38.23 | **no** | `b200_sxm-x347-nvl72-hybrid` | 237.1 | 443.6-443.6 | 2.67 | yes | 7.703x | 0.538x | 0.070x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 661.6 | 43.8-43.8 | 75.55 | **no** | `b200_sxm-x173-nvl72-hybrid` | 78.3 | 127.4-127.4 | 3.07 | yes | 8.444x | 0.344x | 0.041x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,015.4 | 60.9-60.9 | 83.35 | **no** | `b200_sxm-x347-nvl72-hybrid` | 119.1 | 191.1-191.1 | 3.12 | yes | 8.523x | 0.319x | 0.037x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 193.8 | 34.9-34.9 | 27.80 | **no** | `b200_sxm-x173-nvl72-hybrid` | 36.7 | 44.9-44.9 | 4.09 | yes | 5.278x | 0.776x | 0.147x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 396.8 | 76.4-76.4 | 25.98 | **no** | `b200_sxm-x347-nvl72-hybrid` | 51.7 | 73.8-73.8 | 3.50 | yes | 7.671x | 1.035x | 0.135x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.037x to 0.147x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 445.2-445.2 | 24.26 | **no** | `b200_sxm-x134-nvl72-hybrid` | 421.3 | 1,562.4-1,562.4 | 1.35 | yes | 5.128x | 0.285x | 0.056x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,309.2 | 903.5-903.5 | 12.78 | **no** | `b200_sxm-x144-nvl72-hybrid` | 422.3 | 1,555.1-1,555.1 | 1.36 | yes | 5.468x | 0.581x | 0.106x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 445.2-445.2 | 24.26 | **no** | `b200_sxm-x134-nvl72-hybrid` | 421.3 | 1,562.4-1,562.4 | 1.35 | yes | 5.128x | 0.285x | 0.056x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,309.2 | 903.5-903.5 | 12.78 | **no** | `b200_sxm-x144-nvl72-hybrid` | 422.3 | 1,555.1-1,555.1 | 1.36 | yes | 5.468x | 0.581x | 0.106x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 445.2-445.2 | 24.26 | **no** | `b200_sxm-x134-nvl72-hybrid` | 407.8 | 1,394.4-1,394.4 | 1.46 | yes | 5.297x | 0.319x | 0.060x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,309.2 | 903.5-903.5 | 12.78 | **no** | `b200_sxm-x144-nvl72-hybrid` | 409.4 | 1,405.1-1,405.1 | 1.46 | yes | 5.640x | 0.643x | 0.114x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 445.2-445.2 | 24.26 | **no** | `b200_sxm-x134-nvl72-hybrid` | 397.8 | 1,304.6-1,304.6 | 1.52 | yes | 5.430x | 0.341x | 0.063x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,309.2 | 903.5-903.5 | 12.78 | **no** | `b200_sxm-x144-nvl72-hybrid` | 402.0 | 1,330.8-1,330.8 | 1.51 | yes | 5.744x | 0.679x | 0.118x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 445.2-445.2 | 24.26 | **no** | `b200_sxm-x134-nvl72-hybrid` | 377.6 | 1,090.3-1,090.3 | 1.73 | yes | 5.721x | 0.408x | 0.071x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,309.2 | 903.5-903.5 | 12.78 | **no** | `b200_sxm-x144-nvl72-hybrid` | 382.4 | 1,114.5-1,114.5 | 1.72 | yes | 6.039x | 0.811x | 0.134x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 445.2-445.2 | 24.26 | **no** | `b200_sxm-x134-nvl72-hybrid` | 338.8 | 827.7-827.7 | 2.05 | yes | 6.377x | 0.538x | 0.084x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,306.9 | 474.4-474.4 | 24.32 | **no** | `b200_sxm-x144-nvl72-hybrid` | 344.3 | 846.7-846.7 | 2.03 | yes | 6.699x | 0.560x | 0.084x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 2,103.9 | 229.1-229.1 | 45.92 | **no** | `b200_sxm-x157-nvl72-hybrid` | 296.3 | 611.6-611.6 | 2.42 | yes | 7.100x | 0.375x | 0.053x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,298.1 | 476.3-476.3 | 24.12 | **no** | `b200_sxm-x347-nvl72-hybrid` | 352.4 | 843.8-843.8 | 2.09 | yes | 6.522x | 0.564x | 0.087x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,465.3 | 171.6-171.6 | 42.69 | **no** | `b200_sxm-x173-nvl72-hybrid` | 177.4 | 321.4-321.4 | 2.76 | yes | 8.260x | 0.534x | 0.065x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,914.2 | 240.0-240.0 | 39.88 | **no** | `b200_sxm-x347-nvl72-hybrid` | 237.5 | 452.9-452.9 | 2.62 | yes | 8.061x | 0.530x | 0.066x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 687.0 | 44.0-44.0 | 78.14 | **no** | `b200_sxm-x173-nvl72-hybrid` | 78.6 | 136.8-136.8 | 2.87 | yes | 8.735x | 0.321x | 0.037x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,050.0 | 61.1-61.1 | 85.92 | **no** | `b200_sxm-x347-nvl72-hybrid` | 119.5 | 201.5-201.5 | 2.97 | yes | 8.788x | 0.303x | 0.035x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 202.6 | 35.3-35.3 | 28.70 | **no** | `b200_sxm-x173-nvl72-hybrid` | 38.3 | 48.9-48.9 | 3.91 | yes | 5.296x | 0.722x | 0.136x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 415.4 | 120.6-120.6 | 17.22 | **no** | `b200_sxm-x347-nvl72-hybrid` | 52.1 | 79.1-79.1 | 3.29 | yes | 7.974x | 1.525x | 0.191x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.035x to 0.191x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x152` | 3,050.2 | 385.0-385.0 | 39.61 | **no** | `a100_sxm_80gb-x150-hybrid` | 286.1 | 510.7-510.7 | 2.80 | yes | 10.660x | 0.754x | 0.071x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 3,722.8 | 1,268.4-1,268.4 | 14.67 | **no** | `a100_sxm_80gb-x168-hybrid` | 286.5 | 507.5-507.5 | 2.82 | yes | 12.993x | 2.499x | 0.192x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,523.9 | 556.4-556.4 | 22.68 | **no** | `a100_sxm_80gb-x387-hybrid` | 279.8 | 447.3-447.3 | 3.13 | yes | 9.022x | 1.244x | 0.138x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,432.9 | 341.0-341.0 | 35.67 | **no** | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 268.6-268.6 | 5.22 | **no** | 8.672x | 1.269x | 0.146x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,523.9 | 556.4-556.4 | 22.68 | **no** | `a100_sxm_80gb-x387-hybrid` | 279.8 | 447.3-447.3 | 3.13 | yes | 9.022x | 1.244x | 0.138x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,432.9 | 341.0-341.0 | 35.67 | **no** | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 268.6-268.6 | 5.22 | **no** | 8.672x | 1.269x | 0.146x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,523.9 | 556.4-556.4 | 22.68 | **no** | `a100_sxm_80gb-x387-hybrid` | 279.8 | 447.3-447.3 | 3.13 | yes | 9.022x | 1.244x | 0.138x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,432.9 | 341.0-341.0 | 35.67 | **no** | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 268.6-268.6 | 5.22 | **no** | 8.672x | 1.269x | 0.146x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,523.9 | 556.4-556.4 | 22.68 | **no** | `a100_sxm_80gb-x387-hybrid` | 279.8 | 447.3-447.3 | 3.13 | yes | 9.022x | 1.244x | 0.138x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,432.9 | 341.0-341.0 | 35.67 | **no** | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 268.6-268.6 | 5.22 | **no** | 8.672x | 1.269x | 0.146x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,444.6 | 306.8-306.8 | 39.84 | **no** | `a100_sxm_80gb-x387-hybrid` | 279.8 | 447.3-447.3 | 3.13 | yes | 8.738x | 0.686x | 0.079x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,432.9 | 341.0-341.0 | 35.67 | **no** | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 268.6-268.6 | 5.22 | **no** | 8.672x | 1.269x | 0.146x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 2,178.3 | 677.6-677.6 | 16.07 | **no** | `a100_sxm_80gb-x387-hybrid` | 259.3 | 381.0-381.0 | 3.40 | yes | 8.400x | 1.778x | 0.212x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,234.3 | 338.4-338.4 | 33.01 | **no** | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 268.6-268.6 | 5.22 | **no** | 7.964x | 1.260x | 0.158x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,189.6 | 79.4-79.4 | 74.91 | **no** | `a100_sxm_80gb-x387-hybrid` | 161.4 | 202.4-202.4 | 3.99 | yes | 7.368x | 0.392x | 0.053x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,232.5 | 97.6-97.6 | 63.12 | **no** | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 268.6-268.6 | 5.22 | **no** | 4.393x | 0.363x | 0.083x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 359.8 | 38.3-38.3 | 46.92 | **no** | `a100_sxm_80gb-x387-hybrid` | 77.9 | 101.5-101.5 | 3.83 | yes | 4.620x | 0.378x | 0.082x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 390.1 | 24.6-24.6 | 79.12 | **no** | `a100_sxm_80gb-x2574-hybrid` | 200.3 | 136.7-136.7 | 7.32 | **no** | 1.948x | 0.180x | 0.093x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 93.6 | 31.1-31.1 | 15.07 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 103.3 | 6.2-6.2 | 83.67 | **no** | `a100_sxm_80gb-x2574-hybrid` | 106.2 | 60.4-60.4 | 8.80 | **no** | 0.972x | 0.102x | 0.105x |

**Does the ratio compress?** Of 19 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.053x to 0.212x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 10 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 4,175.0 | 774.3-774.3 | 26.96 | **no** | `a100_sxm_80gb-x73-hybrid` | 337.6 | 887.7-887.7 | 1.90 | yes | 12.367x | 0.872x | 0.071x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,951.3 | 991.7-991.7 | 19.92 | **no** | `a100_sxm_80gb-x112-hybrid` | 344.2 | 898.4-898.4 | 1.92 | yes | 11.480x | 1.104x | 0.096x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 4,175.0 | 774.3-774.3 | 26.96 | **no** | `a100_sxm_80gb-x73-hybrid` | 337.6 | 887.7-887.7 | 1.90 | yes | 12.367x | 0.872x | 0.071x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,951.3 | 991.7-991.7 | 19.92 | **no** | `a100_sxm_80gb-x112-hybrid` | 344.2 | 898.4-898.4 | 1.92 | yes | 11.480x | 1.104x | 0.096x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 4,175.0 | 774.3-774.3 | 26.96 | **no** | `a100_sxm_80gb-x73-hybrid` | 337.6 | 887.7-887.7 | 1.90 | yes | 12.367x | 0.872x | 0.071x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,951.3 | 991.7-991.7 | 19.92 | **no** | `a100_sxm_80gb-x112-hybrid` | 344.2 | 898.4-898.4 | 1.92 | yes | 11.480x | 1.104x | 0.096x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 4,175.0 | 774.3-774.3 | 26.96 | **no** | `a100_sxm_80gb-x73-hybrid` | 337.6 | 887.7-887.7 | 1.90 | yes | 12.367x | 0.872x | 0.071x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,951.3 | 991.7-991.7 | 19.92 | **no** | `a100_sxm_80gb-x112-hybrid` | 344.2 | 898.4-898.4 | 1.92 | yes | 11.480x | 1.104x | 0.096x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 4,175.0 | 774.3-774.3 | 26.96 | **no** | `a100_sxm_80gb-x73-hybrid` | 316.4 | 745.1-745.1 | 2.12 | yes | 13.197x | 1.039x | 0.079x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 3,948.7 | 1,634.5-1,634.5 | 12.08 | **no** | `a100_sxm_80gb-x168-hybrid` | 341.4 | 852.7-852.7 | 2.00 | yes | 11.565x | 1.917x | 0.166x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 4,116.2 | 840.7-840.7 | 24.48 | **no** | `a100_sxm_80gb-x146-hybrid` | 314.6 | 692.5-692.5 | 2.27 | yes | 13.083x | 1.214x | 0.093x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,936.2 | 1,674.8-1,674.8 | 11.75 | **no** | `a100_sxm_80gb-x448-hybrid` | 333.1 | 674.8-674.8 | 2.47 | yes | 11.817x | 2.482x | 0.210x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,098.7 | 840.1-840.1 | 24.40 | **no** | `a100_sxm_80gb-x335-hybrid` | 313.9 | 620.0-620.0 | 2.53 | yes | 13.058x | 1.355x | 0.104x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,934.1 | 1,666.3-1,666.3 | 11.80 | **no** | `a100_sxm_80gb-x672-hybrid` | 333.1 | 601.2-601.2 | 2.77 | yes | 11.811x | 2.772x | 0.235x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,917.5 | 415.1-415.1 | 35.14 | **no** | `a100_sxm_80gb-x335-hybrid` | 211.0 | 310.9-310.9 | 3.39 | yes | 13.829x | 1.335x | 0.097x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,261.4 | 860.9-860.9 | 18.94 | **no** | `a100_sxm_80gb-x672-hybrid` | 269.0 | 388.1-388.1 | 3.46 | yes | 12.126x | 2.218x | 0.183x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,290.7 | 190.5-190.5 | 33.88 | **no** | `a100_sxm_80gb-x335-hybrid` | 106.5 | 160.7-160.7 | 3.31 | yes | 12.116x | 1.185x | 0.098x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,776.8 | 225.5-225.5 | 39.40 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.0 | 193.6-193.6 | 4.00 | yes | 11.461x | 1.165x | 0.102x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 378.6 | 121.4-121.4 | 15.60 | **no** | `a100_sxm_80gb-x335-hybrid` | 45.8 | 72.4-72.4 | 3.16 | yes | 8.259x | 1.676x | 0.203x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 567.0 | 172.6-172.6 | 16.42 | **no** | `a100_sxm_80gb-x672-hybrid` | 69.3 | 101.0-101.0 | 3.43 | yes | 8.184x | 1.709x | 0.209x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.071x to 0.235x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 4,192.4 | 857.5-857.5 | 24.44 | **no** | `a100_sxm_80gb-x67-hybrid` | 341.4 | 917.7-917.7 | 1.86 | yes | 12.278x | 0.934x | 0.076x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,182.6 | 1,628.6-1,628.6 | 12.84 | **no** | `a100_sxm_80gb-x112-hybrid` | 345.9 | 915.1-915.1 | 1.89 | yes | 12.092x | 1.780x | 0.147x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 4,192.4 | 857.5-857.5 | 24.44 | **no** | `a100_sxm_80gb-x67-hybrid` | 341.4 | 917.7-917.7 | 1.86 | yes | 12.278x | 0.934x | 0.076x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,182.6 | 1,628.6-1,628.6 | 12.84 | **no** | `a100_sxm_80gb-x112-hybrid` | 345.9 | 915.1-915.1 | 1.89 | yes | 12.092x | 1.780x | 0.147x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 4,192.4 | 857.5-857.5 | 24.44 | **no** | `a100_sxm_80gb-x67-hybrid` | 341.4 | 917.7-917.7 | 1.86 | yes | 12.278x | 0.934x | 0.076x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,182.6 | 1,628.6-1,628.6 | 12.84 | **no** | `a100_sxm_80gb-x112-hybrid` | 345.9 | 915.1-915.1 | 1.89 | yes | 12.092x | 1.780x | 0.147x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 4,192.4 | 857.5-857.5 | 24.44 | **no** | `a100_sxm_80gb-x67-hybrid` | 341.4 | 917.7-917.7 | 1.86 | yes | 12.278x | 0.934x | 0.076x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,182.6 | 1,628.6-1,628.6 | 12.84 | **no** | `a100_sxm_80gb-x112-hybrid` | 345.9 | 915.1-915.1 | 1.89 | yes | 12.092x | 1.780x | 0.147x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 4,192.4 | 857.5-857.5 | 24.44 | **no** | `a100_sxm_80gb-x67-hybrid` | 315.0 | 739.7-739.7 | 2.13 | yes | 13.310x | 1.159x | 0.087x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 4,177.5 | 1,660.8-1,660.8 | 12.58 | **no** | `a100_sxm_80gb-x168-hybrid` | 343.1 | 867.7-867.7 | 1.98 | yes | 12.175x | 1.914x | 0.157x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 4,141.3 | 845.7-845.7 | 24.48 | **no** | `a100_sxm_80gb-x146-hybrid` | 316.9 | 704.0-704.0 | 2.25 | yes | 13.070x | 1.201x | 0.092x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4,156.0 | 1,702.1-1,702.1 | 12.21 | **no** | `a100_sxm_80gb-x448-hybrid` | 334.7 | 684.1-684.1 | 2.45 | yes | 12.418x | 2.488x | 0.200x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,123.6 | 845.1-845.1 | 24.40 | **no** | `a100_sxm_80gb-x335-hybrid` | 316.0 | 632.1-632.1 | 2.50 | yes | 13.048x | 1.337x | 0.102x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,155.1 | 1,693.4-1,693.4 | 12.27 | **no** | `a100_sxm_80gb-x672-hybrid` | 334.7 | 608.6-608.6 | 2.75 | yes | 12.415x | 2.782x | 0.224x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,039.8 | 418.8-418.8 | 36.30 | **no** | `a100_sxm_80gb-x335-hybrid` | 214.1 | 321.8-321.8 | 3.33 | yes | 14.198x | 1.301x | 0.092x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,706.8 | 873.4-873.4 | 21.22 | **no** | `a100_sxm_80gb-x672-hybrid` | 271.7 | 395.8-395.8 | 3.43 | yes | 13.641x | 2.207x | 0.162x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,385.4 | 193.6-193.6 | 35.78 | **no** | `a100_sxm_80gb-x335-hybrid` | 107.3 | 167.8-167.8 | 3.20 | yes | 12.910x | 1.154x | 0.089x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,386.5 | 227.5-227.5 | 52.44 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.9 | 198.9-198.9 | 3.92 | yes | 15.313x | 1.144x | 0.075x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 412.1 | 126.7-126.7 | 16.27 | **no** | `a100_sxm_80gb-x335-hybrid` | 46.4 | 79.1-79.1 | 2.94 | yes | 8.876x | 1.602x | 0.180x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 845.0 | 177.9-177.9 | 23.75 | **no** | `a100_sxm_80gb-x672-hybrid` | 69.9 | 106.6-106.6 | 3.28 | yes | 12.081x | 1.669x | 0.138x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.075x to 0.224x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 295.2-295.2 | 31.31 | **no** | `a100_sxm_80gb-x391-hybrid` | 166.4 | 280.7-280.7 | 2.96 | yes | 11.106x | 1.052x | 0.095x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 2,091.7 | 652.0-652.0 | 16.04 | **no** | `a100_sxm_80gb-x336-hybrid` | 167.5 | 294.1-294.1 | 2.85 | yes | 12.489x | 2.217x | 0.178x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 295.2-295.2 | 31.31 | **no** | `a100_sxm_80gb-x391-hybrid` | 166.4 | 280.7-280.7 | 2.96 | yes | 11.106x | 1.052x | 0.095x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,891.3 | 591.6-591.6 | 15.98 | **no** | `a100_sxm_80gb-x783-hybrid` | 165.1 | 225.8-225.8 | 3.66 | yes | 11.454x | 2.620x | 0.229x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 295.2-295.2 | 31.31 | **no** | `a100_sxm_80gb-x391-hybrid` | 166.4 | 280.7-280.7 | 2.96 | yes | 11.106x | 1.052x | 0.095x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,891.3 | 591.6-591.6 | 15.98 | **no** | `a100_sxm_80gb-x783-hybrid` | 165.1 | 225.8-225.8 | 3.66 | yes | 11.454x | 2.620x | 0.229x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 295.2-295.2 | 31.31 | **no** | `a100_sxm_80gb-x391-hybrid` | 166.4 | 280.7-280.7 | 2.96 | yes | 11.106x | 1.052x | 0.095x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,891.3 | 591.6-591.6 | 15.98 | **no** | `a100_sxm_80gb-x783-hybrid` | 165.1 | 225.8-225.8 | 3.66 | yes | 11.454x | 2.620x | 0.229x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 295.2-295.2 | 31.31 | **no** | `a100_sxm_80gb-x391-hybrid` | 166.4 | 280.7-280.7 | 2.96 | yes | 11.106x | 1.052x | 0.095x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,891.3 | 591.6-591.6 | 15.98 | **no** | `a100_sxm_80gb-x783-hybrid` | 165.1 | 225.8-225.8 | 3.66 | yes | 11.454x | 2.620x | 0.229x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 295.2-295.2 | 31.31 | **no** | `a100_sxm_80gb-x391-hybrid` | 166.4 | 280.7-280.7 | 2.96 | yes | 11.106x | 1.052x | 0.095x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,847.6 | 309.7-309.7 | 29.83 | **no** | `a100_sxm_80gb-x783-hybrid` | 165.1 | 225.8-225.8 | 3.66 | yes | 11.190x | 1.372x | 0.123x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,737.9 | 153.8-153.8 | 56.48 | **no** | `a100_sxm_80gb-x391-hybrid` | 156.9 | 250.4-250.4 | 3.13 | yes | 11.075x | 0.614x | 0.055x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,715.0 | 307.1-307.1 | 27.92 | **no** | `a100_sxm_80gb-x783-hybrid` | 165.1 | 225.8-225.8 | 3.66 | yes | 10.387x | 1.360x | 0.131x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,116.4 | 76.3-76.3 | 73.12 | **no** | `a100_sxm_80gb-x391-hybrid` | 89.7 | 113.8-113.8 | 3.94 | yes | 12.441x | 0.671x | 0.054x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,024.8 | 79.7-79.7 | 64.25 | **no** | `a100_sxm_80gb-x783-hybrid` | 123.8 | 144.9-144.9 | 4.27 | yes | 8.276x | 0.550x | 0.066x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 403.9 | 36.0-36.0 | 56.17 | **no** | `a100_sxm_80gb-x391-hybrid` | 36.2 | 50.6-50.6 | 3.58 | yes | 11.152x | 0.710x | 0.064x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 364.5 | 20.1-20.1 | 90.78 | **no** | `a100_sxm_80gb-x783-hybrid` | 57.4 | 64.4-64.4 | 4.45 | yes | 6.351x | 0.312x | 0.049x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 110.7 | 26.1-26.1 | 21.20 | **no** | `a100_sxm_80gb-x391-hybrid` | 13.1 | 21.8-21.8 | 3.02 | yes | 8.428x | 1.199x | 0.142x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 99.0 | 18.9-18.9 | 26.19 | **no** | `a100_sxm_80gb-x783-hybrid` | 21.8 | 30.4-30.4 | 3.59 | yes | 4.538x | 0.621x | 0.137x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.049x to 0.229x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,987.3 | 569.1-569.1 | 17.46 | **no** | `a100_sxm_80gb-x391-hybrid` | 167.2 | 298.2-298.2 | 2.80 | yes | 11.885x | 1.908x | 0.161x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,220.4 | 660.7-660.7 | 16.80 | **no** | `a100_sxm_80gb-x448-hybrid` | 166.6 | 285.4-285.4 | 2.92 | yes | 13.331x | 2.315x | 0.174x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,987.3 | 569.1-569.1 | 17.46 | **no** | `a100_sxm_80gb-x391-hybrid` | 167.2 | 298.2-298.2 | 2.80 | yes | 11.885x | 1.908x | 0.161x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,220.4 | 660.7-660.7 | 16.80 | **no** | `a100_sxm_80gb-x448-hybrid` | 166.6 | 285.4-285.4 | 2.92 | yes | 13.331x | 2.315x | 0.174x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,987.3 | 569.1-569.1 | 17.46 | **no** | `a100_sxm_80gb-x391-hybrid` | 167.2 | 298.2-298.2 | 2.80 | yes | 11.885x | 1.908x | 0.161x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,220.4 | 660.7-660.7 | 16.80 | **no** | `a100_sxm_80gb-x448-hybrid` | 166.6 | 285.4-285.4 | 2.92 | yes | 13.331x | 2.315x | 0.174x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,987.3 | 569.1-569.1 | 17.46 | **no** | `a100_sxm_80gb-x391-hybrid` | 167.2 | 298.2-298.2 | 2.80 | yes | 11.885x | 1.908x | 0.161x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,220.4 | 660.7-660.7 | 16.80 | **no** | `a100_sxm_80gb-x448-hybrid` | 166.6 | 285.4-285.4 | 2.92 | yes | 13.331x | 2.315x | 0.174x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,987.3 | 569.1-569.1 | 17.46 | **no** | `a100_sxm_80gb-x391-hybrid` | 167.2 | 298.2-298.2 | 2.80 | yes | 11.885x | 1.908x | 0.161x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,220.4 | 660.7-660.7 | 16.80 | **no** | `a100_sxm_80gb-x448-hybrid` | 166.6 | 285.4-285.4 | 2.92 | yes | 13.331x | 2.315x | 0.174x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 1,974.4 | 317.6-317.6 | 31.08 | **no** | `a100_sxm_80gb-x368-hybrid` | 167.8 | 304.7-304.7 | 2.75 | yes | 11.768x | 1.042x | 0.089x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,213.2 | 667.5-667.5 | 16.58 | **no** | `a100_sxm_80gb-x672-hybrid` | 166.0 | 250.6-250.6 | 3.31 | yes | 13.335x | 2.663x | 0.200x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,859.7 | 155.7-155.7 | 59.73 | **no** | `a100_sxm_80gb-x391-hybrid` | 158.0 | 267.7-267.7 | 2.95 | yes | 11.771x | 0.581x | 0.049x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,093.1 | 346.1-346.1 | 30.23 | **no** | `a100_sxm_80gb-x672-hybrid` | 166.0 | 250.6-250.6 | 3.31 | yes | 12.612x | 1.381x | 0.110x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,297.8 | 77.5-77.5 | 83.71 | **no** | `a100_sxm_80gb-x391-hybrid` | 93.6 | 130.3-130.3 | 3.59 | yes | 13.861x | 0.595x | 0.043x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,632.0 | 173.2-173.2 | 47.10 | **no** | `a100_sxm_80gb-x672-hybrid` | 119.3 | 152.5-152.5 | 3.91 | yes | 13.685x | 1.136x | 0.083x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 505.5 | 37.0-37.0 | 68.29 | **no** | `a100_sxm_80gb-x391-hybrid` | 37.4 | 52.0-52.0 | 3.60 | yes | 13.507x | 0.712x | 0.053x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 893.2 | 86.5-86.5 | 51.62 | **no** | `a100_sxm_80gb-x672-hybrid` | 54.2 | 68.2-68.2 | 3.97 | yes | 16.489x | 1.269x | 0.077x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 142.2 | 28.5-28.5 | 24.96 | **no** | `a100_sxm_80gb-x391-hybrid` | 14.3 | 18.6-18.6 | 3.86 | yes | 9.914x | 1.535x | 0.155x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 333.4 | 40.2-40.2 | 41.45 | **no** | `a100_sxm_80gb-x672-hybrid` | 20.0 | 32.9-32.9 | 3.04 | yes | 16.672x | 1.222x | 0.073x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.043x to 0.200x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 324.8-324.8 | 31.92 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 302.2-302.2 | 2.75 | yes | 12.464x | 1.075x | 0.086x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,266.7 | 665.1-665.1 | 17.04 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.4 | 313.4-313.4 | 2.69 | yes | 13.463x | 2.122x | 0.158x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 324.8-324.8 | 31.92 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 302.2-302.2 | 2.75 | yes | 12.464x | 1.075x | 0.086x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,266.7 | 665.1-665.1 | 17.04 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.4 | 313.4-313.4 | 2.69 | yes | 13.463x | 2.122x | 0.158x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 324.8-324.8 | 31.92 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 302.2-302.2 | 2.75 | yes | 12.464x | 1.075x | 0.086x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,266.7 | 665.1-665.1 | 17.04 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.4 | 313.4-313.4 | 2.69 | yes | 13.463x | 2.122x | 0.158x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 324.8-324.8 | 31.92 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 302.2-302.2 | 2.75 | yes | 12.464x | 1.075x | 0.086x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,266.7 | 665.1-665.1 | 17.04 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.4 | 313.4-313.4 | 2.69 | yes | 13.463x | 2.122x | 0.158x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 324.8-324.8 | 31.92 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 302.2-302.2 | 2.75 | yes | 12.464x | 1.075x | 0.086x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,266.7 | 665.1-665.1 | 17.04 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.4 | 313.4-313.4 | 2.69 | yes | 13.463x | 2.122x | 0.158x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 324.8-324.8 | 31.92 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 302.2-302.2 | 2.75 | yes | 12.464x | 1.075x | 0.086x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,257.9 | 670.9-670.9 | 16.83 | **no** | `a100_sxm_80gb-x672-hybrid` | 166.1 | 250.7-250.7 | 3.31 | yes | 13.596x | 2.676x | 0.197x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,948.6 | 297.1-297.1 | 32.80 | **no** | `a100_sxm_80gb-x391-hybrid` | 158.1 | 267.8-267.8 | 2.95 | yes | 12.323x | 1.109x | 0.090x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,220.5 | 347.6-347.6 | 31.94 | **no** | `a100_sxm_80gb-x672-hybrid` | 166.1 | 250.7-250.7 | 3.31 | yes | 13.371x | 1.387x | 0.104x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,330.3 | 77.7-77.7 | 85.62 | **no** | `a100_sxm_80gb-x391-hybrid` | 93.8 | 131.7-131.7 | 3.56 | yes | 14.180x | 0.590x | 0.042x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,714.1 | 173.9-173.9 | 49.27 | **no** | `a100_sxm_80gb-x672-hybrid` | 119.4 | 153.1-153.1 | 3.90 | yes | 14.353x | 1.136x | 0.079x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 525.1 | 37.2-37.2 | 70.62 | **no** | `a100_sxm_80gb-x391-hybrid` | 37.5 | 53.7-53.7 | 3.49 | yes | 13.987x | 0.692x | 0.049x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 950.4 | 156.2-156.2 | 30.42 | **no** | `a100_sxm_80gb-x672-hybrid` | 54.3 | 69.8-69.8 | 3.89 | yes | 17.497x | 2.237x | 0.128x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 148.5 | 28.9-28.9 | 25.71 | **no** | `a100_sxm_80gb-x391-hybrid` | 14.4 | 19.8-19.8 | 3.65 | yes | 10.305x | 1.461x | 0.142x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 365.5 | 69.6-69.6 | 26.25 | **no** | `a100_sxm_80gb-x672-hybrid` | 20.1 | 33.0-33.0 | 3.04 | yes | 18.207x | 2.109x | 0.116x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.042x to 0.197x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 10,692.4 | not applicable | -- | -- | `b200_sxm-x8-tensor` | 943.8 | not applicable | -- | -- | 11.330x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 9,245.0 | not applicable | -- | -- | `b200_sxm-x29-nvl72-tensor` | 1,202.6 | not applicable | -- | -- | 7.687x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 9,796.1 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 1,202.3 | not applicable | -- | -- | 8.148x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 7,483.5 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,258.3 | not applicable | -- | -- | 5.947x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 9,796.1 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 1,178.6 | not applicable | -- | -- | 8.312x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 7,483.5 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,255.0 | not applicable | -- | -- | 5.963x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 9,712.9 | not applicable | -- | -- | `b200_sxm-x87-nvl72-hybrid` | 1,207.9 | not applicable | -- | -- | 8.041x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 7,471.7 | not applicable | -- | -- | `b200_sxm-x231-nvl72-hybrid` | 1,245.1 | not applicable | -- | -- | 6.001x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9,591.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,217.5 | not applicable | -- | -- | 7.878x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6,532.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,242.6 | not applicable | -- | -- | 5.257x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8,722.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,170.8 | not applicable | -- | -- | 7.450x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,236.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,214.0 | not applicable | -- | -- | 4.313x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7,119.0 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,087.4 | not applicable | -- | -- | 6.547x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,678.1 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,160.5 | not applicable | -- | -- | 3.169x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,148.4 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 811.6 | not applicable | -- | -- | 3.879x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,238.5 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 951.5 | not applicable | -- | -- | 1.302x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 801.0 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 439.4 | not applicable | -- | -- | 1.823x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 331.2 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 613.1 | not applicable | -- | -- | 0.540x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 201.1 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 166.6 | not applicable | -- | -- | 1.207x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 84.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 280.0 | not applicable | -- | -- | 0.300x | -- | -- |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 4,202.4 | 1,013.6-1,013.6 | 20.73 | **no** | `b200_sxm-x29-nvl72-tensor` | 599.7 | 2,149.1-2,149.1 | 1.40 | yes | 7.007x | 0.472x | 0.067x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3,943.5 | 990.6-990.6 | 19.90 | **no** | `b200_sxm-x58-nvl72-tensor` | 607.7 | 2,192.7-2,192.7 | 1.39 | yes | 6.489x | 0.452x | 0.070x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 4,142.4 | 952.1-952.1 | 21.75 | **no** | `b200_sxm-x31-hybrid` | 585.0 | 1,899.5-1,899.5 | 1.54 | yes | 7.081x | 0.501x | 0.071x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,601.2 | 3,594.6-3,594.6 | 5.01 | **no** | `b200_sxm-x202-nvl72-hybrid` | 605.8 | 2,159.8-2,159.8 | 1.40 | yes | 5.945x | 1.664x | 0.280x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 4,142.4 | 952.1-952.1 | 21.75 | **no** | `b200_sxm-x31-hybrid` | 585.0 | 1,899.5-1,899.5 | 1.54 | yes | 7.081x | 0.501x | 0.071x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,601.2 | 3,594.6-3,594.6 | 5.01 | **no** | `b200_sxm-x202-nvl72-hybrid` | 602.4 | 2,132.6-2,132.6 | 1.41 | yes | 5.978x | 1.686x | 0.282x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 4,142.4 | 952.1-952.1 | 21.75 | **no** | `b200_sxm-x31-hybrid` | 547.7 | 1,498.9-1,498.9 | 1.83 | yes | 7.563x | 0.635x | 0.084x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,601.2 | 3,594.6-3,594.6 | 5.01 | **no** | `b200_sxm-x202-nvl72-hybrid` | 590.6 | 2,009.1-2,009.1 | 1.47 | yes | 6.097x | 1.789x | 0.293x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x61` | 4,118.7 | 897.9-897.9 | 22.94 | **no** | `b200_sxm-x31-hybrid` | 486.8 | 1,072.5-1,072.5 | 2.27 | yes | 8.462x | 0.837x | 0.099x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,601.2 | 3,594.6-3,594.6 | 5.01 | **no** | `b200_sxm-x202-nvl72-hybrid` | 576.5 | 1,779.8-1,779.8 | 1.62 | yes | 6.247x | 2.020x | 0.323x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 3,916.7 | 1,097.0-1,097.0 | 17.85 | **no** | `b200_sxm-x86-nvl72-hybrid` | 517.7 | 1,274.3-1,274.3 | 2.03 | yes | 7.565x | 0.861x | 0.114x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,571.7 | 3,577.0-3,577.0 | 4.99 | yes | `b200_sxm-x347-nvl72-hybrid` | 569.6 | 1,662.1-1,662.1 | 1.71 | yes | 6.271x | 2.152x | 0.343x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,914.0 | 1,096.8-1,096.8 | 17.84 | **no** | `b200_sxm-x173-nvl72-hybrid` | 513.7 | 1,228.6-1,228.6 | 2.09 | yes | 7.619x | 0.893x | 0.117x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,458.0 | 2,112.7-2,112.7 | 8.18 | **no** | `b200_sxm-x347-nvl72-hybrid` | 552.7 | 1,489.5-1,489.5 | 1.86 | yes | 6.256x | 1.418x | 0.227x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,667.9 | 536.2-536.2 | 24.88 | **no** | `b200_sxm-x173-nvl72-hybrid` | 364.6 | 701.8-701.8 | 2.60 | yes | 7.318x | 0.764x | 0.104x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,439.2 | 1,089.5-1,089.5 | 11.19 | **no** | `b200_sxm-x347-nvl72-hybrid` | 442.1 | 890.6-890.6 | 2.48 | yes | 5.518x | 1.223x | 0.222x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,133.1 | 235.9-235.9 | 24.02 | **no** | `b200_sxm-x173-nvl72-hybrid` | 197.9 | 368.7-368.7 | 2.68 | yes | 5.726x | 0.640x | 0.112x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,035.3 | 293.0-293.0 | 17.67 | **no** | `b200_sxm-x347-nvl72-hybrid` | 275.2 | 449.6-449.6 | 3.06 | yes | 3.763x | 0.652x | 0.173x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 344.6 | 118.7-118.7 | 14.52 | **no** | `b200_sxm-x173-nvl72-hybrid` | 87.7 | 182.9-182.9 | 2.40 | yes | 3.930x | 0.649x | 0.165x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 298.0 | 84.2-84.2 | 17.70 | **no** | `b200_sxm-x347-nvl72-hybrid` | 132.3 | 249.7-249.7 | 2.65 | yes | 2.252x | 0.337x | 0.150x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340` | 1,581.9 | 321.0-321.0 | 24.64 | **no** | `b200_sxm-x173-nvl72-hybrid` | 376.7 | 907.1-907.1 | 2.08 | yes | 4.199x | 0.354x | 0.084x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 2,052.1 | 644.6-644.6 | 15.92 | **no** | `b200_sxm-x173-nvl72-hybrid` | 376.7 | 907.1-907.1 | 2.08 | yes | 5.448x | 0.711x | 0.130x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,575.6 | 282.2-282.2 | 27.92 | **no** | `b200_sxm-x203-nvl72-hybrid` | 378.3 | 909.3-909.3 | 2.08 | yes | 4.165x | 0.310x | 0.075x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,678.4 | 327.7-327.7 | 25.61 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 833.4-833.4 | 2.23 | yes | 4.515x | 0.393x | 0.087x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,575.6 | 282.2-282.2 | 27.92 | **no** | `b200_sxm-x203-nvl72-hybrid` | 374.4 | 896.3-896.3 | 2.09 | yes | 4.208x | 0.315x | 0.075x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,678.4 | 327.7-327.7 | 25.61 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 833.4-833.4 | 2.23 | yes | 4.515x | 0.393x | 0.087x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,575.6 | 282.2-282.2 | 27.92 | **no** | `b200_sxm-x203-nvl72-hybrid` | 363.9 | 829.5-829.5 | 2.19 | yes | 4.330x | 0.340x | 0.079x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,678.4 | 327.7-327.7 | 25.61 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 833.4-833.4 | 2.23 | yes | 4.515x | 0.393x | 0.087x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,575.6 | 282.2-282.2 | 27.92 | **no** | `b200_sxm-x203-nvl72-hybrid` | 350.8 | 739.4-739.4 | 2.37 | yes | 4.491x | 0.382x | 0.085x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,678.4 | 327.7-327.7 | 25.61 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 833.4-833.4 | 2.23 | yes | 4.515x | 0.393x | 0.087x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,575.6 | 282.2-282.2 | 27.92 | **no** | `b200_sxm-x203-nvl72-hybrid` | 310.8 | 635.9-635.9 | 2.44 | yes | 5.070x | 0.444x | 0.088x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,678.4 | 327.7-327.7 | 25.61 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 356.5 | 749.4-749.4 | 2.38 | yes | 4.708x | 0.437x | 0.093x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,568.9 | 150.2-150.2 | 52.21 | **no** | `b200_sxm-x203-nvl72-hybrid` | 257.2 | 416.2-416.2 | 3.09 | yes | 6.101x | 0.361x | 0.059x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,654.7 | 1,447.9-1,447.9 | 5.71 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 354.1 | 652.3-652.3 | 2.71 | yes | 4.673x | 2.220x | 0.475x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 958.0 | 74.3-74.3 | 64.44 | **no** | `b200_sxm-x203-nvl72-hybrid` | 148.6 | 212.6-212.6 | 3.49 | yes | 6.449x | 0.350x | 0.054x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,301.3 | 95.6-95.6 | 68.07 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 293.7 | 401.7-401.7 | 3.66 | yes | 4.430x | 0.238x | 0.054x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 339.6 | 34.8-34.8 | 48.83 | **no** | `b200_sxm-x203-nvl72-hybrid` | 64.8 | 90.2-90.2 | 3.59 | yes | 5.238x | 0.386x | 0.074x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 568.5 | 24.2-24.2 | 117.48 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 189.8 | 201.2-201.2 | 4.72 | yes | 2.995x | 0.120x | 0.040x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 92.0 | 24.1-24.1 | 19.07 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 168.7 | 6.1-6.1 | 139.08 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 92.1 | 95.3-95.3 | 4.83 | yes | 1.832x | 0.064x | 0.035x |

**Does the ratio compress?** Of 39 class rows in this study, 39 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.035x to 0.475x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 1 of 40 ROM rows and 39 of 40 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 10,396.4 | not applicable | -- | -- | `a100_sxm_80gb-x16-hybrid` | 458.7 | not applicable | -- | -- | 22.666x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 9,289.5 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 537.8 | not applicable | -- | -- | 17.274x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8,012.3 | not applicable | -- | -- | `a100_sxm_80gb-x272-tensor` | 544.1 | not applicable | -- | -- | 14.726x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,951.9 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 539.0 | not applicable | -- | -- | 11.043x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8,012.3 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 532.5 | not applicable | -- | -- | 15.046x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,537.5 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 539.0 | not applicable | -- | -- | 10.274x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8,012.3 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 514.3 | not applicable | -- | -- | 15.580x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,459.7 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 534.5 | not applicable | -- | -- | 10.215x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 7,650.1 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 474.5 | not applicable | -- | -- | 16.124x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,524.5 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 520.1 | not applicable | -- | -- | 8.700x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,230.8 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 447.1 | not applicable | -- | -- | 13.937x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,092.1 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 479.6 | not applicable | -- | -- | 6.448x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,555.8 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 430.7 | not applicable | -- | -- | 10.577x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,856.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 442.4 | not applicable | -- | -- | 4.196x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,594.7 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 354.0 | not applicable | -- | -- | 4.505x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 531.7 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 402.4 | not applicable | -- | -- | 1.321x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 431.0 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 206.7 | not applicable | -- | -- | 2.085x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 136.7 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 286.6 | not applicable | -- | -- | 0.477x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 111.0 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 77.9 | not applicable | -- | -- | 1.424x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 34.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 133.3 | not applicable | -- | -- | 0.258x | -- | -- |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | 3,949.8 | 725.8-725.8 | 27.21 | **no** | `a100_sxm_80gb-x79-hybrid` | 333.5 | 814.8-814.8 | 2.05 | yes | 11.843x | 0.891x | 0.075x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 3,943.5 | 982.7-982.7 | 20.06 | **no** | `a100_sxm_80gb-x112-hybrid` | 333.1 | 799.3-799.3 | 2.08 | yes | 11.840x | 1.229x | 0.104x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,844.6 | 663.0-663.0 | 28.99 | **no** | `a100_sxm_80gb-x85-hybrid` | 331.3 | 803.4-803.4 | 2.06 | yes | 11.606x | 0.825x | 0.071x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,238.6 | 836.6-836.6 | 19.36 | **no** | `a100_sxm_80gb-x560-hybrid` | 322.7 | 583.8-583.8 | 2.76 | yes | 10.037x | 1.433x | 0.143x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,844.6 | 663.0-663.0 | 28.99 | **no** | `a100_sxm_80gb-x85-hybrid` | 331.3 | 803.4-803.4 | 2.06 | yes | 11.606x | 0.825x | 0.071x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,238.6 | 836.6-836.6 | 19.36 | **no** | `a100_sxm_80gb-x560-hybrid` | 322.7 | 583.8-583.8 | 2.76 | yes | 10.037x | 1.433x | 0.143x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,844.6 | 663.0-663.0 | 28.99 | **no** | `a100_sxm_80gb-x85-hybrid` | 331.3 | 803.4-803.4 | 2.06 | yes | 11.606x | 0.825x | 0.071x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,238.6 | 836.6-836.6 | 19.36 | **no** | `a100_sxm_80gb-x560-hybrid` | 322.7 | 583.8-583.8 | 2.76 | yes | 10.037x | 1.433x | 0.143x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,844.6 | 663.0-663.0 | 28.99 | **no** | `a100_sxm_80gb-x85-hybrid` | 311.7 | 678.8-678.8 | 2.30 | yes | 12.335x | 0.977x | 0.079x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,238.6 | 836.6-836.6 | 19.36 | **no** | `a100_sxm_80gb-x560-hybrid` | 322.7 | 583.8-583.8 | 2.76 | yes | 10.037x | 1.433x | 0.143x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 3,628.0 | 807.5-807.5 | 22.47 | **no** | `a100_sxm_80gb-x312-hybrid` | 324.1 | 671.9-671.9 | 2.41 | yes | 11.196x | 1.202x | 0.107x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,106.7 | 435.3-435.3 | 35.69 | **no** | `a100_sxm_80gb-x560-hybrid` | 322.7 | 583.8-583.8 | 2.76 | yes | 9.629x | 0.746x | 0.077x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 3,628.0 | 807.5-807.5 | 22.47 | **no** | `a100_sxm_80gb-x312-hybrid` | 296.6 | 539.7-539.7 | 2.75 | yes | 12.231x | 1.496x | 0.122x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,774.5 | 364.1-364.1 | 38.10 | **no** | `a100_sxm_80gb-x672-hybrid` | 322.7 | 555.2-555.2 | 2.91 | yes | 8.599x | 0.656x | 0.076x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,291.5 | 391.8-391.8 | 29.24 | **no** | `a100_sxm_80gb-x335-hybrid` | 195.1 | 283.0-283.0 | 3.45 | yes | 11.747x | 1.384x | 0.118x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,464.3 | 182.7-182.7 | 40.08 | **no** | `a100_sxm_80gb-x672-hybrid` | 249.1 | 333.7-333.7 | 3.73 | yes | 5.877x | 0.547x | 0.093x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 883.5 | 171.9-171.9 | 25.69 | **no** | `a100_sxm_80gb-x335-hybrid` | 95.1 | 130.1-130.1 | 3.66 | yes | 9.290x | 1.322x | 0.142x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 480.3 | 46.8-46.8 | 51.30 | **no** | `a100_sxm_80gb-x672-hybrid` | 143.1 | 169.7-169.7 | 4.22 | yes | 3.356x | 0.276x | 0.082x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 313.9 | 106.0-106.0 | 14.81 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.6 | 69.2-69.2 | 2.72 | yes | 8.345x | 1.531x | 0.183x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 128.2 | 23.0-23.0 | 27.84 | **no** | `a100_sxm_80gb-x672-hybrid` | 60.1 | 82.8-82.8 | 3.63 | yes | 2.134x | 0.278x | 0.130x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 1,467.1 | 488.0-488.0 | 15.03 | **no** | `a100_sxm_80gb-x384-hybrid` | 149.5 | 221.3-221.3 | 3.38 | yes | 9.816x | 2.205x | 0.225x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 1,978.5 | 456.9-456.9 | 21.65 | **no** | `a100_sxm_80gb-x504-hybrid` | 148.2 | 206.6-206.6 | 3.59 | yes | 13.349x | 2.212x | 0.166x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 236.5-236.5 | 31.62 | **no** | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 97.1-97.1 | 7.63 | **no** | 10.095x | 2.437x | 0.241x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 236.5-236.5 | 31.62 | **no** | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 97.1-97.1 | 7.63 | **no** | 10.095x | 2.437x | 0.241x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 236.5-236.5 | 31.62 | **no** | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 97.1-97.1 | 7.63 | **no** | 10.095x | 2.437x | 0.241x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 236.5-236.5 | 31.62 | **no** | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 97.1-97.1 | 7.63 | **no** | 10.095x | 2.437x | 0.241x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 236.5-236.5 | 31.62 | **no** | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 97.1-97.1 | 7.63 | **no** | 10.095x | 2.437x | 0.241x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 236.5-236.5 | 31.62 | **no** | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 97.1-97.1 | 7.63 | **no** | 10.095x | 2.437x | 0.241x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 989.0 | 68.6-68.6 | 72.08 | **no** | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 97.1-97.1 | 7.63 | **no** | 6.674x | 0.707x | 0.106x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 361.2 | 17.3-17.3 | 104.66 | **no** | `a100_sxm_80gb-x3694-hybrid` | 109.3 | 64.0-64.0 | 8.53 | **no** | 3.305x | 0.269x | 0.082x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 100.3 | 4.3-4.3 | 116.15 | **no** | `a100_sxm_80gb-x3694-hybrid` | 53.1 | 28.6-28.6 | 9.28 | **no** | 1.888x | 0.151x | 0.080x |

**Does the ratio compress?** Of 31 class rows in this study, 31 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.071x to 0.241x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 31 ROM rows and 22 of 31 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 12,043.2 | not applicable | -- | -- | `b200_sxm-x2-tensor` | 872.0 | not applicable | -- | -- | 13.811x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 9,137.9 | not applicable | -- | -- | `b200_sxm-x29-nvl72-tensor` | 1,294.7 | not applicable | -- | -- | 7.058x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 9,519.0 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 1,285.1 | not applicable | -- | -- | 7.407x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 7,387.4 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,307.2 | not applicable | -- | -- | 5.651x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 9,519.0 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 1,258.1 | not applicable | -- | -- | 7.566x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 7,387.4 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,303.7 | not applicable | -- | -- | 5.666x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x170-romfill` | 9,440.2 | not applicable | -- | -- | `b200_sxm-x87-nvl72-hybrid` | 1,268.3 | not applicable | -- | -- | 7.443x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 7,375.9 | not applicable | -- | -- | `b200_sxm-x231-nvl72-hybrid` | 1,292.9 | not applicable | -- | -- | 5.705x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 9,325.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,263.3 | not applicable | -- | -- | 7.382x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 6,402.3 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,282.0 | not applicable | -- | -- | 4.994x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 8,516.1 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,214.9 | not applicable | -- | -- | 7.010x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 5,147.2 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,251.5 | not applicable | -- | -- | 4.113x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 6,884.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,145.4 | not applicable | -- | -- | 6.011x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,595.4 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,199.0 | not applicable | -- | -- | 2.999x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3,271.6 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 877.5 | not applicable | -- | -- | 3.728x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,227.3 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,010.0 | not applicable | -- | -- | 1.215x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 832.2 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 480.0 | not applicable | -- | -- | 1.734x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 331.1 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 671.6 | not applicable | -- | -- | 0.493x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 208.3 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 179.0 | not applicable | -- | -- | 1.164x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 84.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 306.9 | not applicable | -- | -- | 0.274x | -- | -- |

### `n6_vs_a100-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x8-romfill` | 11,594.0 | not applicable | -- | -- | `a100_sxm_80gb-x8-tensor` | 749.4 | not applicable | -- | -- | 15.471x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 9,155.9 | not applicable | -- | -- | `a100_sxm_80gb-x56-hybrid` | 740.4 | not applicable | -- | -- | 12.366x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,820.6 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 707.1 | not applicable | -- | -- | 11.060x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,928.2 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 704.7 | not applicable | -- | -- | 8.412x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,820.6 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 707.1 | not applicable | -- | -- | 11.060x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,498.6 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 704.7 | not applicable | -- | -- | 7.802x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,820.6 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 707.1 | not applicable | -- | -- | 11.060x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,385.8 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 704.7 | not applicable | -- | -- | 7.642x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,461.6 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 707.1 | not applicable | -- | -- | 10.553x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 4,472.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 704.7 | not applicable | -- | -- | 6.346x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 5,990.2 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 704.1 | not applicable | -- | -- | 8.507x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,047.9 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 704.7 | not applicable | -- | -- | 4.325x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4,417.1 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 676.7 | not applicable | -- | -- | 6.528x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,832.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 704.7 | not applicable | -- | -- | 2.600x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 1,587.4 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 504.8 | not applicable | -- | -- | 3.144x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 529.8 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 608.4 | not applicable | -- | -- | 0.871x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 430.0 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 250.4 | not applicable | -- | -- | 1.717x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 136.7 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 377.7 | not applicable | -- | -- | 0.362x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340` | 111.0 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 89.7 | not applicable | -- | -- | 1.237x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12` | 34.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 156.9 | not applicable | -- | -- | 0.219x | -- | -- |

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

