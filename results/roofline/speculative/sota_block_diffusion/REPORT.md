# Speculative decoding on the area-constrained roofline: sota_block_diffusion

> The DFlash / MiMo-UltraSpeed class: a block-diffusion drafter decoding a whole block in one parallel pass. Every figure below is derived from the roofline artifacts
> this repository has already published, by re-assembling each point's own five
> critical-path terms for a speculative cycle. Nothing here re-runs the machine
> model, and nothing here invents an acceptance rate.

## What this layer says

1. **Every term the speculative arithmetic needs is already in the published artifact, exactly.** 183,227 feasible points across 52 studies were rebuilt from their own five critical-path terms and every one reproduced its published step time to 1e-9 relative. Nothing here re-ran the machine model, and the layer is additive by construction rather than by promise.
2. **The headline is a break-even, not a speedup.** `tau* = T_cycle / step_time_s`, and `tau <= gamma+1` always. Of 290,038 (point, draft-placement) pairs where this profile's drafter applies, 80,799 (27.9%) cannot be sped up by speculation at ANY acceptance rate, at any block size on the ladder, even charging the drafter no KV traffic at all.
3. **The ROM-versus-GPU ratio under speculation carries no acceptance rate.** It is `T_cycle(GPU) / T_cycle(ROM)`: `tau` is a property of the model and its drafter, not of the machine, so it is identical on both sides and cancels. Every movement this report shows is a machine effect and nothing else, which is why it can be published without inventing an acceptance rate.
4. **The ratio moves, and it mostly compresses.** Across 983 model-context-batch-class rows, 919 move the ROM-versus-GPU per-user ratio DOWN under speculation and 64 move it UP, spanning 0.124x to 3.307x. The ROM advantage compresses on most operating points.
5. **At batch 1 the two extremes are opposite in sign, and they are the result.** DeepSeek-V4.1-Flash-engram-hbm on `array` silicon goes from 5.14x to 0.71x -- a 0.138x movement -- while DeepSeek-V4.1-Flash on `array` silicon goes from 10.88x to 11.23x, a 1.032x movement. A layer that multiplied both sides by `tau` would have reported neither.
6. **A moving ratio is not a win for either side, and the report says so on every table.** At the most favourable sourced acceptance (7.87) speculation is worth having on 586 of 985 ROM class rows and 896 of 985 GPU rows; everywhere else the design runs SLOWER with a drafter than without one. Where both sides lose, a rising ratio means only that the comparator lost more.
7. **Compute is never a gain and always a loss.** A verification pass over `n` positions charges `n` times the arithmetic exactly, so per accepted token compute costs `(n/tau) >= 1` times what it did. A compute-bound design cannot be sped up by speculation at any acceptance rate; it can only be slowed. That is where the recommended ROM designs live, because the sizing rule gives them just enough compute for one token per sweep.
8. **On a mask-ROM machine the draft pass costs a full array sweep, and that is the load-bearing assumption of the whole ROM verdict.** `stored/peak` is a technology constant in `src/opentallas/roofline.py`, so a pass reading only the drafter's region takes as long as sweeping the entire array. The alternative -- holding the drafter in the KV store -- is priced beside it on every ROM row and has NOT been costed in silicon area.
9. **The overhead factor lands below the only published measurement of it, and the gap is reported as a residual.** This layer models 1.205 on `b200_sxm-x3-tensor` against a published 1.26-1.32 measured on an H200 with the authors' own kernels. The named causes are the drafter's unsourced KV traffic at the bottom of its band, no sampler or scheduler cost anywhere in this model, and a different part. It is a band check and it validates nothing about the machine.
10. **Every number here is conditional on inputs nobody has measured.** The drafter's own KV traffic is unsourced for both drafters and is published as a band on every row; the compute efficiency derate that decides which designs are compute-bound is graded `assumed` at 0.55; and no speculative decoder has ever been executed in this repository.

## What this layer is, and what it is not

It **is** an arithmetic layer over `results/roofline/**/analytical.json`. Every term it uses -- weight read, KV read, compute, link latency, the per-layer serial floor, the thermal throttle -- is recovered exactly from the published artifact, and the reconstruction is gated on every feasible point before any speculative arithmetic runs.

It is **not** a measurement of a speculative system. No token in this repository has been produced by a speculative decoder. The only quantities taken from outside are the drafter's shape and the acceptance lengths, both published by their authors and both measured on hardware that is not in this study.

The headline is therefore **not a speedup**. It is the break-even acceptance `tau* = T_cycle / step_time_s`: speculation pays if and only if `tau >= tau*`, and `tau <= gamma+1` always. A design whose `tau*` exceeds `gamma+1` at every block size **cannot be sped up by speculation at any acceptance rate** -- a verdict that needs no acceptance rate to state, and the only kind of verdict this study can honestly publish for a model whose acceptance nobody has measured.

## The arithmetic

Write `n = gamma + 1` for the positions one verification pass carries, the extra one
being the target's own bonus token. DFlash equation (1) is `L = (T_draft + T_verify)/tau`
with `tau` in `[1, gamma+1]` counting accepted tokens INCLUDING that bonus token.

**`gamma` is the block size, taken from each source's own definition and never derived as `block_size - 1`.** DFlash states that the block size IS the speculation budget, so a block of 16 proposes 16 draft tokens and caps `tau` at 17. DSpark treats the anchor itself as the first prediction position, so a block of `gamma` (anchor plus `gamma-1` masks) yields `gamma` draft logits and caps `tau` at `gamma+1`. A ladder rung above the block size a source actually configures is an extension this study states rather than a configuration anyone has served.

**Every headline figure in this report is at gamma = 16, so a verification pass carries 17 positions and `tau` is capped at 17.** The break-even ladder runs over gamma = 1, 2, 3, 4, 5, 7, 8, 15, 16. Of those, 8, 16 are block sizes a source names for this drafter; 1, 2, 3, 4, 5, 7, 15 are rungs no source configures, carried so the parameter-free verdict below is tested over a wider range than anyone serves, and never quoted as a served figure.

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
| `acceptance_length` | (a block of values; see the tables in this report) | `published` | arXiv:2602.06036v2, ICML 2026, Table 1: Qwen3-8B, temperature 0, NVIDIA H200, DFlash block 16 |
| `baseline_comparators` | (a block of values; see the tables in this report) | `published` | arXiv:2602.06036v2, ICML 2026, Table 1 |
| `external_acceptance_cross_check` | (a block of values; see the tables in this report) | `published` | https://mimo.xiaomi.com/blog/mimo-tilert-1000tps (2026) |
| `parameters.block_size` | 16 | `published` | arXiv:2602.06036v2 (2026), DFlash block size 16 (10 for LLaMA-3.1): 'the block size IS the speculation budget. With block size ... |
| `parameters.draft_block_passes` | 1 | `published` | arXiv:2602.06036v2 (2026), equation (3): T_draft = t_parallel, independent of the speculation budget gamma -- all masked positi... |
| `parameters.draft_compute_ops_ratio_rule` | engaged draft weight bytes / engaged target weight bytes at the same block, at equal da... | `assumed` | explicit modelling convention; operations = 2 x active parameters (configs/hardware/technology.json counting convention) makes ... |
| `parameters.draft_layers` | 5 | `published` | Chen, Liang, Liu, DFlash: Block Diffusion for Flash Speculative Decoding, ICML 2026, arXiv:2602.06036v2 (28 May 2026): 5 draft ... |
| `parameters.draft_sequential_passes_per_draft_token` | 0 | `published` | arXiv:2602.06036v2 (2026), equation (3): the draft pass carries no per-position sequential term |
| `parameters.drafter_derivation_when_absent` | stored bytes = draft_layers x layer_dense_weight_bytes[0]; traffic bytes = stored bytes... | `derived` | arXiv:2602.06036v2 (2026) states a dense N-layer drafter sharing the frozen target's embedding and LM head; per-layer byte coun... |
| `parameters.drafter_kv_traffic` | BAND [0.0, target KV time x draft_layers / num_layers] | `assumed` | no primary source: arXiv:2602.06036v2 (2026) gives no KV byte count for the injected Key/Value features |
| `parameters.mimo_block_size` | 8 | `published` | https://mimo.xiaomi.com/blog/mimo-tilert-1000tps (2026): a DFlash block-diffusion drafter with block size limited to 8 |

**The acceptance length is an input, never an output, and it is task-dependent.** The range carried here is 4.24 to 7.87, graded `published`, from arXiv:2602.06036v2, ICML 2026, Table 1: Qwen3-8B, temperature 0, NVIDIA H200, DFlash block 16. Every speculative rate below is published across that range.

| workload | tau | source's own reported speedup |
| --- | ---: | ---: |
| GSM8K | 6.54 | 5.15 |
| MATH-500 | 7.87 | 6.08 |
| AIME25 | 7.08 | 5.62 |
| HumanEval | 6.50 | 5.14 |
| MBPP | 5.95 | 4.65 |
| LiveCodeBench | 7.27 | 5.51 |
| MT-Bench | 4.24 | 2.75 |

_ACCEPTANCE IS TASK-DEPENDENT AND THE SPREAD IS LARGER THAN MOST OF THE EFFECTS THIS STUDY MEASURES: 4.24 on MT-Bench against 7.87 on MATH-500, a 1.86x range on the same model and the same drafter. Every speculative rate in the report is therefore published across the range, never at the mean alone._

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
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,599 | 477 | 1.42 | 8.67 | 295.30 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 89 | 1 | 2.12 | 6.24 | 17.44 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 432 | 244 | 3.64 | 20.17 | 104.39 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 807 | 807 | 22.67 | 94.52 | 1,875.97 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 48 | 48 | 1,770.60 | 2,147.91 | 2,425.41 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 723 | 500 | 2.50 | 19.47 | 716.78 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 837 | 278 | 2.63 | 12.72 | 570.50 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 409 | 354 | 4.45 | 42.43 | 984.24 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 807 | 807 | 17.37 | 37.17 | 59.57 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 48 | 14 | 4.37 | 12.21 | 45.89 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 723 | 210 | 2.60 | 12.72 | 68.16 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 837 | 156 | 2.22 | 7.08 | 25.33 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 409 | 285 | 5.13 | 31.65 | 37.24 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 1 | 1 | 26.96 | 26.96 | 26.96 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 772 | 273 | 1.68 | 11.10 | 295.22 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 547 | 254 | 3.50 | 17.83 | 99.99 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 737 | 737 | 23.79 | 191.58 | 2,079.02 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 46 | 46 | 30.91 | 2,148.65 | 2,425.41 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 618 | 478 | 3.84 | 25.03 | 915.67 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 714 | 261 | 3.11 | 15.94 | 363.00 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 297 | 277 | 10.83 | 67.99 | 1,835.84 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 737 | 737 | 18.07 | 41.32 | 61.96 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 46 | 19 | 6.00 | 16.60 | 31.16 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 618 | 177 | 2.38 | 13.78 | 71.32 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 714 | 141 | 2.24 | 6.69 | 27.32 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 297 | 201 | 5.19 | 31.64 | 38.46 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,660 | 484 | 1.42 | 8.26 | 295.26 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 88 | 2 | 2.09 | 6.20 | 17.27 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 424 | 246 | 3.95 | 19.94 | 30.18 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 745 | 745 | 21.99 | 70.02 | 444.46 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 126 | 126 | 29.79 | 525.24 | 602.76 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 658 | 421 | 2.54 | 18.70 | 329.08 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 857 | 242 | 2.63 | 12.26 | 121.70 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 366 | 310 | 4.62 | 30.72 | 577.28 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 745 | 745 | 18.02 | 39.47 | 59.90 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 126 | 90 | 6.39 | 24.55 | 39.36 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 658 | 190 | 2.65 | 13.64 | 66.97 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 857 | 174 | 2.24 | 7.44 | 25.68 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 366 | 246 | 3.97 | 31.54 | 36.88 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 2 | 2 | 20.49 | 20.51 | 20.51 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 816 | 287 | 1.68 | 10.70 | 295.01 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 569 | 263 | 4.24 | 17.63 | 53.76 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 683 | 683 | 23.45 | 111.14 | 492.28 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 125 | 120 | 14.65 | 523.52 | 720.46 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 531 | 370 | 3.87 | 19.99 | 357.75 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 771 | 221 | 3.12 | 15.62 | 77.43 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 246 | 229 | 13.06 | 56.29 | 398.36 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 683 | 683 | 18.18 | 42.29 | 61.00 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 125 | 70 | 3.44 | 19.59 | 48.34 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 531 | 177 | 2.65 | 14.06 | 64.99 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 771 | 146 | 2.26 | 7.52 | 24.74 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 246 | 161 | 5.01 | 31.87 | 43.53 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,535 | 463 | 1.42 | 8.73 | 295.30 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 88 | 2 | 2.14 | 6.44 | 17.54 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 427 | 238 | 3.12 | 20.20 | 119.65 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 792 | 792 | 22.53 | 97.95 | 10,163.24 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 60 | 60 | 6,173.28 | 11,577.96 | 12,020.57 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 722 | 506 | 2.51 | 19.24 | 3,849.51 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 861 | 323 | 2.63 | 13.03 | 5,469.94 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 445 | 387 | 4.46 | 43.70 | 7,241.48 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 792 | 791 | 16.73 | 36.26 | 59.55 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 60 | 8 | 1.82 | 3.57 | 49.15 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 722 | 218 | 2.47 | 12.92 | 65.94 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 861 | 157 | 2.17 | 6.97 | 25.22 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 445 | 309 | 5.04 | 31.26 | 37.41 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 2 | 2 | 25.23 | 25.59 | 25.59 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 713 | 254 | 1.68 | 11.11 | 295.09 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 515 | 242 | 3.33 | 17.90 | 95.86 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 776 | 776 | 24.17 | 173.73 | 10,891.26 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 48 | 48 | 10,492.37 | 11,623.28 | 12,020.57 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 631 | 496 | 3.85 | 23.56 | 3,849.51 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 771 | 300 | 3.12 | 16.02 | 4,680.59 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 314 | 289 | 10.85 | 68.27 | 5,966.08 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 776 | 776 | 18.22 | 39.34 | 62.85 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 48 | 10 | 2.11 | 6.85 | 51.53 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 631 | 203 | 2.62 | 13.66 | 67.59 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 771 | 146 | 2.19 | 6.63 | 26.61 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 314 | 212 | 5.14 | 31.23 | 38.59 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 2,078 | 589 | 1.36 | 8.56 | 295.32 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 109 | 0 | 1.30 | 3.80 | 7.80 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 553 | 4 | 2.78 | 5.68 | 103.91 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 830 | 148 | 9.84 | 15.27 | 27.75 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 5 | 1 | 8.07 | 11.81 | 17.62 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 841 | 127 | 1.92 | 7.58 | 37.13 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 924 | 130 | 2.07 | 4.58 | 21.42 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 625 | 127 | 1.49 | 10.66 | 24.02 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 830 | 625 | 10.43 | 17.56 | 28.23 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 5 | 1 | 11.62 | 14.41 | 18.14 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 841 | 142 | 2.30 | 10.02 | 71.06 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 924 | 138 | 2.18 | 5.40 | 26.41 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 625 | 434 | 3.63 | 22.20 | 34.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 3 | 2 | 16.50 | 17.39 | 17.66 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,042 | 357 | 1.61 | 10.53 | 295.22 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 715 | 3 | 1.93 | 4.15 | 99.19 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 713 | 296 | 10.68 | 16.67 | 17.71 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 107 | 89 | 5.00 | 36.95 | 44.76 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 755 | 127 | 1.92 | 9.64 | 39.34 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 894 | 138 | 2.07 | 4.75 | 20.37 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 489 | 150 | 2.23 | 12.54 | 39.26 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 713 | 576 | 10.72 | 18.18 | 31.60 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 107 | 66 | 6.34 | 22.17 | 22.96 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 755 | 132 | 2.33 | 9.76 | 71.38 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 894 | 142 | 2.19 | 5.28 | 22.83 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 489 | 345 | 5.10 | 23.79 | 34.15 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 2,219 | 617 | 1.36 | 8.22 | 295.26 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 110 | 0 | 1.30 | 4.15 | 7.63 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 559 | 0 | 2.84 | 5.63 | 31.15 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 738 | 80 | 9.39 | 15.36 | 17.17 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 71 | 32 | 4.12 | 12.82 | 17.01 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 766 | 105 | 1.94 | 9.25 | 36.85 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 876 | 121 | 2.07 | 4.73 | 21.66 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 450 | 65 | 2.31 | 10.19 | 20.00 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 738 | 548 | 9.75 | 17.28 | 28.45 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 71 | 0 | 4.93 | 12.71 | 15.05 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 766 | 164 | 2.66 | 11.24 | 67.02 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 876 | 125 | 2.18 | 5.33 | 26.19 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 450 | 326 | 3.69 | 23.09 | 34.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 1 | 0 | 14.46 | 14.46 | 14.46 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,060 | 355 | 1.61 | 10.44 | 294.96 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 690 | 0 | 2.34 | 4.10 | 53.86 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 727 | 300 | 10.51 | 16.73 | 17.71 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 92 | 0 | 2.62 | 11.55 | 15.99 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 617 | 88 | 1.95 | 8.49 | 36.87 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 888 | 138 | 2.08 | 4.83 | 20.45 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 385 | 94 | 2.63 | 13.06 | 24.82 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 727 | 599 | 10.56 | 17.96 | 30.93 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 92 | 9 | 2.76 | 9.14 | 18.82 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 617 | 104 | 2.69 | 9.49 | 64.30 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 888 | 140 | 2.19 | 5.37 | 22.59 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 385 | 272 | 5.25 | 24.94 | 34.12 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,980 | 563 | 1.36 | 8.67 | 295.32 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 103 | 0 | 1.30 | 3.94 | 7.85 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 537 | 6 | 2.13 | 5.70 | 119.09 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 842 | 162 | 9.46 | 15.34 | 28.97 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 846 | 130 | 1.92 | 7.88 | 34.20 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 936 | 130 | 2.07 | 4.62 | 21.23 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 664 | 135 | 1.28 | 10.21 | 25.26 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 842 | 647 | 10.08 | 17.65 | 28.67 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 846 | 146 | 2.33 | 10.16 | 67.94 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 936 | 141 | 2.18 | 5.39 | 26.24 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 664 | 441 | 3.62 | 21.83 | 34.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 3 | 3 | 17.53 | 17.70 | 17.80 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 983 | 337 | 1.61 | 10.55 | 295.15 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 684 | 3 | 1.79 | 4.16 | 95.02 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 796 | 385 | 10.32 | 16.95 | 50.51 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 740 | 131 | 1.92 | 9.66 | 35.65 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 909 | 140 | 2.07 | 4.78 | 20.19 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 533 | 155 | 1.94 | 12.85 | 39.88 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 796 | 663 | 10.39 | 18.45 | 31.14 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 740 | 135 | 2.38 | 10.09 | 67.66 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 909 | 145 | 2.19 | 5.27 | 22.66 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 533 | 372 | 5.04 | 23.84 | 34.16 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 1,420 | 423 | 1.36 | 8.84 | 295.32 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `thermal` | 91 | 0 | 1.29 | 3.21 | 7.80 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 429 | 5 | 2.62 | 5.68 | 107.02 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 832 | 194 | 9.84 | 15.74 | 37.37 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 51 | 49 | 7.54 | 35.23 | 38.28 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `layer_fixed_latency` | 870 | 127 | 2.25 | 8.78 | 37.52 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 901 | 130 | 2.06 | 5.21 | 21.42 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 566 | 107 | 2.64 | 11.25 | 25.18 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 832 | 615 | 10.43 | 17.35 | 23.04 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 51 | 3 | 2.09 | 9.11 | 18.14 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `layer_fixed_latency` | 870 | 144 | 2.34 | 9.92 | 68.22 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 901 | 138 | 2.19 | 5.56 | 26.41 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 566 | 393 | 4.98 | 21.92 | 34.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `compute` | 5 | 4 | 16.50 | 17.64 | 17.66 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 797 | 290 | 1.61 | 11.78 | 295.23 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 638 | 4 | 1.93 | 4.15 | 74.59 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 680 | 304 | 10.68 | 16.85 | 41.16 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 151 | 133 | 5.00 | 36.96 | 44.77 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `layer_fixed_latency` | 763 | 127 | 2.25 | 10.03 | 39.34 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 864 | 138 | 1.99 | 4.93 | 20.37 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 466 | 145 | 2.64 | 12.72 | 39.26 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 680 | 537 | 10.72 | 17.86 | 26.23 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 151 | 66 | 2.63 | 16.47 | 22.97 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `layer_fixed_latency` | 763 | 133 | 2.33 | 9.76 | 71.38 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 864 | 142 | 2.20 | 5.31 | 22.83 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 466 | 328 | 5.06 | 23.79 | 34.15 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `compute` | 5 | 0 | 12.57 | 14.29 | 16.72 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 1,038 | 317 | 1.42 | 11.30 | 291.39 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `thermal` | 289 | 0 | 3.92 | 4.03 | 15.01 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 403 | 0 | 2.05 | 4.03 | 69.61 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 456 | 194 | 10.17 | 16.98 | 19.74 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 61 | 11 | 3.52 | 11.52 | 18.17 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 397 | 41 | 2.46 | 11.38 | 24.94 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 493 | 60 | 2.16 | 8.96 | 18.19 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 189 | 38 | 3.19 | 16.78 | 18.64 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `compute` | 456 | 364 | 10.40 | 17.59 | 19.07 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 61 | 14 | 3.92 | 13.25 | 28.48 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 397 | 70 | 3.04 | 12.59 | 36.00 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 493 | 66 | 2.17 | 9.29 | 19.78 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 189 | 117 | 5.21 | 27.15 | 34.26 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `compute` | 4 | 1 | 15.35 | 16.54 | 17.07 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 412 | 130 | 2.40 | 7.83 | 290.44 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 398 | 3 | 2.15 | 3.22 | 111.91 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 246 | 170 | 10.81 | 17.19 | 20.30 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 65 | 1 | 3.28 | 8.74 | 17.36 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 217 | 21 | 2.55 | 12.16 | 23.47 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 265 | 30 | 2.09 | 5.71 | 18.08 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 137 | 69 | 3.52 | 17.01 | 18.25 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `compute` | 246 | 170 | 10.81 | 17.24 | 19.56 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 65 | 0 | 3.48 | 7.95 | 16.20 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 217 | 34 | 3.11 | 13.49 | 33.63 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 265 | 32 | 2.07 | 6.23 | 18.96 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 137 | 83 | 6.21 | 28.63 | 34.26 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `compute` | 21 | 1 | 8.03 | 10.00 | 62.37 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 755 | 191 | 1.28 | 7.47 | 290.21 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `thermal` | 251 | 0 | 4.84 | 4.84 | 15.97 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 194 | 0 | 1.86 | 3.99 | 65.40 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 50 | 40 | 11.17 | 17.32 | 17.69 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 58 | 0 | 2.06 | 4.57 | 14.94 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 95 | 3 | 2.58 | 12.13 | 24.77 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 139 | 0 | 1.84 | 3.64 | 8.99 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 48 | 13 | 2.39 | 9.13 | 17.16 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `compute` | 50 | 40 | 11.17 | 17.35 | 20.23 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 58 | 0 | 2.00 | 8.20 | 14.63 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 95 | 15 | 3.10 | 12.93 | 35.58 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 139 | 0 | 1.86 | 3.66 | 13.39 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 48 | 25 | 3.92 | 17.84 | 34.26 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `compute` | 38 | 4 | 13.11 | 16.17 | 17.12 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 378 | 92 | 2.42 | 8.18 | 285.77 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 330 | 3 | 1.73 | 6.46 | 107.62 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 45 | 31 | 10.83 | 17.39 | 17.69 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 59 | 0 | 2.19 | 3.59 | 8.95 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 75 | 3 | 2.53 | 12.13 | 23.52 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 121 | 0 | 1.79 | 3.49 | 11.10 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 45 | 12 | 2.60 | 10.57 | 17.29 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `compute` | 45 | 31 | 10.83 | 17.42 | 19.83 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 59 | 0 | 1.79 | 5.44 | 8.33 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 75 | 13 | 3.21 | 12.97 | 33.56 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 121 | 0 | 1.79 | 3.64 | 12.81 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 45 | 24 | 4.31 | 20.69 | 34.26 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 836 | 271 | 1.46 | 11.41 | 291.65 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `thermal` | 210 | 0 | 2.21 | 3.79 | 5.58 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 373 | 3 | 2.05 | 3.79 | 76.42 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 380 | 80 | 10.79 | 16.89 | 29.51 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 95 | 67 | 8.50 | 22.14 | 25.57 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 446 | 40 | 2.43 | 10.23 | 24.84 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 466 | 54 | 2.19 | 6.00 | 18.79 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 269 | 36 | 3.14 | 14.35 | 25.75 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `compute` | 380 | 336 | 11.19 | 18.75 | 22.89 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 95 | 40 | 9.27 | 14.72 | 19.31 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 446 | 65 | 3.02 | 11.41 | 36.57 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 466 | 60 | 2.24 | 6.47 | 20.53 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 269 | 141 | 5.30 | 22.39 | 34.26 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `compute` | 2 | 0 | 14.04 | 14.07 | 14.07 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 468 | 145 | 2.40 | 8.02 | 291.31 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 448 | 2 | 2.18 | 3.20 | 113.67 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 340 | 284 | 11.16 | 17.26 | 30.08 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 104 | 68 | 8.52 | 21.75 | 28.89 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 357 | 30 | 2.52 | 10.34 | 22.04 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 388 | 42 | 2.22 | 6.89 | 18.42 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 191 | 90 | 3.52 | 16.27 | 25.92 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `compute` | 340 | 282 | 11.25 | 17.73 | 18.93 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 104 | 16 | 7.41 | 13.18 | 18.50 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 357 | 48 | 3.08 | 10.33 | 32.12 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 388 | 44 | 2.26 | 7.23 | 19.35 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 191 | 105 | 5.98 | 27.37 | 34.26 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 117 | 0 | 1.58 | 2.51 | 75.50 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 926 | 188 | 1.26 | 4.15 | 293.76 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 60 | 0 | 1.65 | 2.43 | 4.66 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 246 | 0 | 1.82 | 4.69 | 34.22 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 8 | 0 | 14.81 | 15.80 | 15.86 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 198 | 0 | 1.18 | 5.03 | 14.98 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 327 | 3 | 2.32 | 8.34 | 37.13 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 464 | 45 | 1.95 | 3.55 | 21.91 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `thermal` | 303 | 0 | 3.26 | 4.23 | 7.99 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 132 | 18 | 2.48 | 11.98 | 17.23 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 8 | 4 | 16.24 | 17.30 | 17.35 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 198 | 26 | 1.11 | 7.33 | 28.10 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 327 | 26 | 2.32 | 9.82 | 66.83 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 464 | 47 | 2.00 | 4.43 | 28.44 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `thermal` | 303 | 0 | 3.39 | 8.45 | 11.80 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 132 | 76 | 4.10 | 22.55 | 34.30 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 47 | 0 | 2.10 | 2.78 | 9.67 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 511 | 125 | 1.44 | 8.93 | 293.07 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 453 | 1 | 1.84 | 3.34 | 73.93 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 26 | 2 | 14.64 | 16.21 | 17.07 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 522 | 0 | 1.23 | 4.72 | 15.32 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 280 | 0 | 2.32 | 8.49 | 32.69 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 478 | 46 | 1.93 | 3.28 | 20.60 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 134 | 30 | 2.70 | 10.88 | 17.27 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 26 | 14 | 16.06 | 17.19 | 17.93 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 522 | 2 | 1.06 | 5.32 | 17.15 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 280 | 18 | 2.54 | 9.24 | 57.50 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 478 | 48 | 1.92 | 3.58 | 24.32 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 134 | 78 | 4.48 | 20.57 | 34.30 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 336 | 7 | 1.53 | 2.15 | 92.03 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 598 | 91 | 1.19 | 3.65 | 291.56 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 222 | 0 | 1.74 | 3.36 | 3.36 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 3 | 3 | 17.14 | 17.14 | 17.16 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 107 | 0 | 1.16 | 1.63 | 15.54 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 203 | 19 | 2.46 | 10.46 | 36.60 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 115 | 0 | 1.71 | 3.15 | 8.79 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 50 | 12 | 3.03 | 14.21 | 17.03 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 3 | 3 | 17.27 | 17.27 | 17.28 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 107 | 1 | 1.06 | 1.78 | 17.39 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 203 | 40 | 2.89 | 11.38 | 65.56 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 115 | 0 | 1.74 | 3.31 | 13.93 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 50 | 29 | 5.81 | 28.39 | 34.30 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 364 | 2 | 1.92 | 2.31 | 85.45 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 454 | 53 | 1.26 | 3.88 | 278.01 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 37 | 0 | 2.98 | 10.22 | 27.70 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 39 | 25 | 11.75 | 17.31 | 17.78 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 105 | 0 | 1.11 | 1.49 | 16.91 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 127 | 6 | 2.47 | 8.79 | 32.29 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 133 | 0 | 1.68 | 3.38 | 10.45 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 50 | 12 | 3.14 | 14.91 | 17.05 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 39 | 26 | 11.75 | 17.41 | 18.79 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 105 | 2 | 1.03 | 1.53 | 18.76 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 127 | 18 | 2.96 | 9.16 | 56.54 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 133 | 0 | 1.68 | 3.54 | 13.06 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 50 | 29 | 6.04 | 29.82 | 34.31 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 18 | 0 | 6.22 | 8.35 | 10.83 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 931 | 273 | 1.28 | 7.42 | 294.27 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 58 | 0 | 1.27 | 1.64 | 3.86 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 403 | 0 | 1.91 | 5.46 | 60.05 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 534 | 135 | 9.90 | 16.35 | 28.61 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 177 | 117 | 2.52 | 22.07 | 33.00 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 810 | 83 | 2.28 | 8.88 | 42.17 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 783 | 104 | 1.85 | 4.62 | 25.44 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 640 | 52 | 2.37 | 12.50 | 27.18 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 534 | 231 | 9.93 | 16.90 | 18.71 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 177 | 2 | 1.30 | 7.04 | 27.40 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 810 | 114 | 2.20 | 9.26 | 79.78 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 783 | 113 | 1.77 | 4.62 | 36.45 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 640 | 264 | 5.47 | 15.03 | 34.30 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `compute` | 19 | 4 | 12.32 | 14.26 | 17.49 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 605 | 263 | 1.61 | 14.46 | 294.23 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 736 | 3 | 1.54 | 4.00 | 83.77 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 606 | 368 | 10.94 | 17.10 | 32.02 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 280 | 150 | 1.85 | 19.89 | 33.30 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 808 | 82 | 2.28 | 9.21 | 37.20 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 893 | 120 | 1.86 | 4.59 | 21.86 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 609 | 208 | 3.28 | 15.41 | 31.65 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 606 | 302 | 10.62 | 16.99 | 20.95 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 280 | 18 | 1.39 | 6.01 | 28.21 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 808 | 88 | 2.26 | 9.02 | 67.49 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 893 | 125 | 1.81 | 4.57 | 27.01 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 609 | 277 | 6.14 | 15.39 | 34.30 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 64 | 0 | 1.68 | 3.10 | 5.73 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 668 | 141 | 1.25 | 6.98 | 291.92 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 45 | 0 | 1.65 | 3.57 | 4.85 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 326 | 0 | 2.08 | 4.24 | 60.98 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 6 | 0 | 16.45 | 16.72 | 16.84 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 102 | 0 | 1.25 | 2.54 | 14.44 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 114 | 0 | 2.31 | 7.42 | 31.56 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 148 | 0 | 1.86 | 2.76 | 8.00 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 50 | 13 | 2.43 | 10.66 | 17.09 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 6 | 6 | 17.24 | 17.65 | 17.87 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 102 | 0 | 1.16 | 5.32 | 16.54 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 114 | 16 | 2.72 | 9.89 | 51.91 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 148 | 0 | 1.88 | 3.00 | 13.01 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 50 | 29 | 4.15 | 20.78 | 34.17 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 15 | 0 | 2.51 | 2.74 | 3.19 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 364 | 78 | 2.34 | 7.80 | 290.81 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 392 | 1 | 1.49 | 2.89 | 74.31 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 18 | 6 | 15.99 | 16.87 | 17.31 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 94 | 0 | 1.34 | 1.72 | 16.45 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 86 | 0 | 2.14 | 5.40 | 28.65 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 159 | 0 | 1.81 | 3.02 | 9.93 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 81 | 13 | 2.59 | 11.70 | 17.18 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 18 | 18 | 17.05 | 17.43 | 18.95 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 94 | 8 | 1.11 | 3.99 | 18.71 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 86 | 0 | 2.86 | 6.81 | 46.47 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 159 | 1 | 1.80 | 3.09 | 17.28 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 81 | 45 | 4.44 | 22.84 | 34.17 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 251 | 0 | 1.60 | 2.23 | 68.79 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 834 | 113 | 1.15 | 4.55 | 283.29 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 221 | 0 | 1.81 | 3.14 | 3.20 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 6 | 0 | 9.06 | 11.82 | 24.91 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 12 | 7 | 10.78 | 17.03 | 17.61 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 90 | 0 | 1.12 | 1.19 | 13.00 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 193 | 27 | 2.28 | 12.08 | 31.22 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 130 | 0 | 1.59 | 3.31 | 9.45 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 52 | 12 | 2.79 | 14.98 | 17.02 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 12 | 8 | 10.78 | 18.02 | 19.20 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 90 | 0 | 1.08 | 1.65 | 15.29 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 193 | 60 | 2.98 | 13.37 | 51.15 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 130 | 0 | 1.60 | 3.54 | 14.19 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 52 | 29 | 5.41 | 29.87 | 34.19 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 294 | 0 | 1.81 | 2.17 | 75.68 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 407 | 48 | 2.15 | 3.84 | 263.40 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 162 | 0 | 1.22 | 4.23 | 55.30 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 43 | 30 | 9.39 | 17.20 | 17.48 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 85 | 0 | 1.09 | 1.15 | 12.04 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 140 | 9 | 2.28 | 9.73 | 28.43 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 138 | 0 | 1.55 | 3.53 | 10.61 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 50 | 12 | 2.86 | 15.52 | 17.04 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 43 | 39 | 9.39 | 17.48 | 19.79 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 85 | 0 | 1.04 | 1.39 | 14.79 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 140 | 28 | 3.00 | 10.27 | 45.97 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 138 | 1 | 1.55 | 3.59 | 18.45 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 50 | 28 | 5.56 | 30.38 | 34.19 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 2 | 0 | 8.76 | 9.81 | 9.81 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 1,188 | 374 | 1.35 | 9.83 | 292.60 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 74 | 0 | 1.29 | 2.76 | 6.09 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 676 | 6 | 1.92 | 4.75 | 102.03 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 600 | 76 | 9.79 | 16.48 | 27.41 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 172 | 87 | 2.54 | 17.14 | 27.86 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 683 | 70 | 2.37 | 9.31 | 34.16 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 932 | 114 | 2.18 | 5.45 | 20.51 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 581 | 45 | 2.96 | 12.56 | 22.07 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 600 | 494 | 10.24 | 17.63 | 23.38 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 172 | 2 | 1.87 | 9.89 | 17.96 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 683 | 91 | 2.34 | 9.56 | 58.36 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 932 | 122 | 2.16 | 5.28 | 24.49 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 581 | 345 | 5.67 | 19.20 | 34.17 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `compute` | 2 | 0 | 12.78 | 15.14 | 15.14 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 571 | 225 | 2.35 | 12.65 | 292.49 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 666 | 6 | 1.67 | 3.27 | 85.05 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 564 | 291 | 10.91 | 17.02 | 27.99 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 198 | 104 | 1.74 | 17.24 | 28.85 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 542 | 55 | 2.10 | 9.24 | 31.53 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 830 | 96 | 2.11 | 5.30 | 19.51 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 410 | 128 | 2.95 | 15.27 | 28.06 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 564 | 478 | 11.61 | 17.92 | 25.06 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 198 | 2 | 2.15 | 8.53 | 18.11 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 542 | 61 | 2.50 | 10.60 | 52.51 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 830 | 104 | 2.17 | 5.44 | 21.55 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 410 | 286 | 4.46 | 22.05 | 34.17 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 261 | 0 | 1.03 | 1.41 | 8.80 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 108 | 4 | 1.51 | 2.04 | 17.36 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 171 | 0 | 1.01 | 1.03 | 1.11 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 8 | 0 | 1.17 | 2.92 | 6.04 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 108 | 12 | 2.33 | 13.15 | 17.24 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 80 | 0 | 1.73 | 6.08 | 8.72 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 26 | 0 | 1.02 | 4.63 | 16.79 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 8 | 0 | 1.17 | 3.28 | 6.04 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 108 | 20 | 2.33 | 14.26 | 22.29 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 80 | 0 | 2.14 | 6.23 | 9.62 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 26 | 4 | 2.08 | 5.74 | 37.19 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 330 | 0 | 1.02 | 1.42 | 9.00 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 51 | 2 | 1.84 | 3.00 | 17.66 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 8 | 0 | 1.21 | 4.91 | 11.19 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 103 | 12 | 2.47 | 12.79 | 17.32 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 76 | 0 | 1.74 | 5.33 | 7.42 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 29 | 0 | 1.03 | 4.73 | 16.79 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 8 | 0 | 1.21 | 4.91 | 12.19 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 103 | 20 | 2.47 | 13.53 | 23.37 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 76 | 0 | 2.14 | 5.41 | 9.62 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 29 | 4 | 2.08 | 5.42 | 37.19 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 238 | 0 | 1.07 | 1.20 | 8.42 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 221 | 10 | 1.18 | 2.63 | 18.90 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 197 | 0 | 1.04 | 1.09 | 1.59 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 82 | 0 | 1.02 | 1.20 | 10.43 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 164 | 7 | 2.10 | 11.21 | 17.36 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 99 | 0 | 1.70 | 3.19 | 6.73 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 109 | 24 | 1.02 | 11.99 | 17.04 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 82 | 0 | 1.02 | 1.21 | 10.43 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 164 | 33 | 2.10 | 11.56 | 22.40 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 99 | 0 | 1.82 | 3.29 | 13.61 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 109 | 58 | 2.06 | 25.42 | 38.00 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 326 | 0 | 1.04 | 1.07 | 8.02 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 175 | 5 | 1.47 | 2.48 | 19.03 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 90 | 0 | 1.02 | 1.37 | 11.10 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 120 | 6 | 2.18 | 10.97 | 17.60 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 118 | 0 | 1.67 | 3.32 | 8.96 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 108 | 24 | 1.03 | 13.81 | 17.04 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 90 | 0 | 1.01 | 1.30 | 11.10 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 120 | 24 | 2.18 | 11.18 | 23.37 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 118 | 2 | 1.76 | 3.39 | 18.63 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 108 | 56 | 2.06 | 29.48 | 38.00 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,062 | 394 | 2.83 | 14.61 | 272.04 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 25 | 0 | 2.00 | 2.97 | 4.54 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 294 | 0 | 2.99 | 4.27 | 5.99 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 135 | 1 | 11.62 | 14.32 | 17.02 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 58 | 0 | 1.94 | 4.90 | 13.98 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 161 | 0 | 2.18 | 6.51 | 9.66 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 463 | 128 | 2.90 | 12.10 | 23.38 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `thermal` | 14 | 0 | 10.11 | 10.61 | 11.84 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 267 | 29 | 1.84 | 6.63 | 17.04 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 135 | 12 | 11.62 | 16.23 | 20.47 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 58 | 0 | 1.94 | 7.26 | 14.42 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 161 | 0 | 2.38 | 8.63 | 15.96 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 463 | 134 | 2.98 | 12.17 | 32.00 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `thermal` | 14 | 0 | 11.52 | 12.42 | 15.38 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 267 | 133 | 4.17 | 16.98 | 34.15 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,266 | 416 | 1.54 | 11.08 | 294.65 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 70 | 0 | 1.32 | 2.12 | 4.55 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 314 | 0 | 3.34 | 4.57 | 48.49 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 484 | 82 | 10.26 | 15.78 | 17.34 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 44 | 36 | 6.13 | 22.61 | 26.17 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 1,056 | 119 | 2.05 | 8.91 | 33.63 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 933 | 234 | 2.13 | 7.89 | 19.93 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 415 | 38 | 1.82 | 6.86 | 19.55 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 484 | 75 | 10.75 | 16.10 | 17.69 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 44 | 0 | 2.05 | 10.88 | 14.23 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 1,056 | 77 | 2.12 | 10.60 | 63.41 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 933 | 236 | 2.12 | 7.99 | 21.99 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 415 | 138 | 4.86 | 13.67 | 34.15 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,185 | 391 | 1.50 | 10.65 | 294.70 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 69 | 0 | 1.32 | 2.22 | 9.29 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 326 | 2 | 3.05 | 4.59 | 65.44 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 483 | 89 | 10.32 | 15.84 | 34.83 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 51 | 50 | 11.00 | 49.47 | 59.70 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 1,125 | 150 | 2.05 | 8.98 | 39.73 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 885 | 186 | 2.10 | 6.74 | 20.00 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 416 | 38 | 1.71 | 6.70 | 37.34 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 483 | 72 | 10.54 | 16.09 | 17.75 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 51 | 0 | 1.61 | 8.15 | 16.44 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 1,125 | 111 | 2.07 | 12.17 | 62.46 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 885 | 192 | 2.10 | 6.75 | 22.39 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 416 | 134 | 4.83 | 13.56 | 34.14 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,600 | 599 | 2.00 | 14.42 | 291.43 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 86 | 0 | 1.57 | 5.57 | 7.39 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 469 | 0 | 3.59 | 5.50 | 8.90 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 649 | 24 | 10.10 | 15.00 | 17.06 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 48 | 0 | 3.88 | 14.12 | 15.74 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 345 | 12 | 1.77 | 5.56 | 17.62 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 934 | 274 | 2.55 | 11.80 | 23.79 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 292 | 23 | 2.61 | 11.70 | 17.56 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 649 | 511 | 10.26 | 17.61 | 24.48 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 48 | 26 | 5.88 | 17.18 | 19.26 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 345 | 14 | 2.17 | 7.59 | 18.56 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 934 | 287 | 2.56 | 12.14 | 33.75 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 292 | 186 | 4.61 | 23.02 | 34.08 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,463 | 528 | 1.76 | 13.46 | 292.93 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 84 | 0 | 1.31 | 5.09 | 7.49 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 423 | 0 | 2.52 | 5.53 | 32.63 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 685 | 130 | 10.14 | 15.61 | 34.63 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 24 | 24 | 29.92 | 32.60 | 33.88 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 517 | 30 | 1.79 | 5.32 | 29.14 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 838 | 222 | 2.39 | 10.51 | 20.47 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 354 | 33 | 2.55 | 11.04 | 20.15 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 685 | 538 | 9.75 | 17.83 | 23.92 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 24 | 2 | 6.65 | 13.75 | 17.50 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 517 | 35 | 2.13 | 6.86 | 47.99 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 838 | 231 | 2.41 | 10.64 | 26.98 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 354 | 224 | 4.92 | 21.83 | 34.08 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,328 | 479 | 1.73 | 13.72 | 292.73 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 79 | 0 | 1.31 | 4.97 | 7.51 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 413 | 2 | 2.52 | 5.54 | 82.46 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 694 | 118 | 10.15 | 15.49 | 63.10 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 34 | 34 | 57.64 | 61.06 | 66.49 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 531 | 36 | 1.79 | 5.37 | 27.00 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 878 | 228 | 2.37 | 10.81 | 20.32 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 371 | 36 | 2.54 | 11.94 | 32.31 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 694 | 548 | 11.50 | 17.93 | 23.98 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 34 | 4 | 3.58 | 9.65 | 18.13 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 531 | 35 | 2.12 | 7.08 | 46.22 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 878 | 238 | 2.38 | 10.56 | 27.09 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 371 | 235 | 4.90 | 21.63 | 34.08 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 669 | 288 | 3.77 | 15.56 | 224.97 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 298 | 0 | 3.13 | 3.23 | 7.73 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 58 | 4 | 12.38 | 14.86 | 17.28 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 128 | 0 | 1.57 | 5.27 | 15.18 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 124 | 0 | 2.22 | 6.79 | 10.84 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 358 | 90 | 2.92 | 12.45 | 23.28 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 166 | 37 | 2.22 | 7.62 | 17.16 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 58 | 28 | 12.94 | 16.96 | 21.97 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 128 | 24 | 1.46 | 9.32 | 26.00 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 124 | 0 | 2.08 | 7.00 | 16.10 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 358 | 103 | 3.00 | 13.05 | 30.74 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 166 | 93 | 4.44 | 17.53 | 34.30 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 2 | 1 | 15.87 | 17.00 | 17.00 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 951 | 353 | 1.85 | 14.22 | 294.40 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 487 | 0 | 1.90 | 3.64 | 14.88 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 566 | 92 | 10.18 | 15.82 | 22.53 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 137 | 91 | 3.54 | 23.12 | 26.38 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 857 | 65 | 2.05 | 7.95 | 35.40 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,006 | 246 | 2.20 | 8.61 | 19.40 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 462 | 54 | 2.86 | 9.58 | 22.59 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 566 | 136 | 10.18 | 16.36 | 18.33 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 137 | 0 | 2.72 | 12.50 | 15.63 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 857 | 141 | 2.13 | 8.21 | 63.84 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,006 | 251 | 2.14 | 8.65 | 20.19 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 462 | 183 | 5.07 | 14.88 | 34.15 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 1 | 1 | 17.20 | 17.20 | 17.20 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 898 | 328 | 1.78 | 14.12 | 294.43 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 491 | 0 | 1.84 | 3.65 | 49.62 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 583 | 141 | 10.62 | 16.17 | 45.35 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 61 | 57 | 6.34 | 46.92 | 59.70 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 934 | 131 | 2.05 | 10.30 | 34.94 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 983 | 228 | 2.18 | 8.01 | 19.40 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 467 | 57 | 2.85 | 9.94 | 33.85 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 583 | 121 | 12.11 | 16.37 | 18.41 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 61 | 2 | 1.80 | 8.73 | 18.25 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 934 | 162 | 2.10 | 10.03 | 63.92 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 983 | 235 | 2.12 | 8.10 | 20.32 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 467 | 175 | 5.04 | 14.66 | 34.14 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 536 | 318 | 4.74 | 18.16 | 285.79 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 727 | 0 | 2.17 | 3.81 | 18.39 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 616 | 66 | 11.57 | 15.74 | 18.51 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 44 | 5 | 2.67 | 12.19 | 18.19 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 285 | 8 | 1.78 | 5.78 | 17.31 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 895 | 262 | 2.55 | 11.84 | 23.80 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 236 | 29 | 2.63 | 14.05 | 19.79 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 616 | 528 | 11.86 | 18.15 | 26.22 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 44 | 21 | 3.48 | 15.24 | 23.60 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 285 | 8 | 2.16 | 6.67 | 17.31 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 895 | 277 | 2.57 | 13.24 | 32.35 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 236 | 126 | 5.04 | 26.58 | 34.08 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 475 | 296 | 6.34 | 18.29 | 291.68 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 724 | 1 | 1.99 | 3.83 | 61.64 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 607 | 144 | 11.22 | 15.86 | 38.24 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 23 | 20 | 5.46 | 34.44 | 38.04 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 410 | 20 | 1.79 | 5.63 | 29.01 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 825 | 232 | 2.42 | 10.83 | 20.77 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 301 | 50 | 2.57 | 14.02 | 22.57 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 607 | 533 | 11.30 | 18.44 | 26.73 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 23 | 7 | 8.83 | 15.65 | 20.49 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 410 | 26 | 2.16 | 6.15 | 45.56 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 825 | 241 | 2.42 | 11.54 | 27.04 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 301 | 186 | 5.00 | 24.56 | 34.09 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 1 | 1 | 17.58 | 17.58 | 17.58 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 483 | 315 | 5.44 | 18.30 | 292.68 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 796 | 1 | 1.95 | 3.84 | 81.14 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 675 | 145 | 11.17 | 15.81 | 67.52 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 29 | 28 | 10.48 | 63.33 | 69.81 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 445 | 41 | 1.80 | 5.84 | 29.77 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 872 | 246 | 2.40 | 11.01 | 20.48 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 313 | 57 | 2.56 | 14.75 | 29.27 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 675 | 591 | 11.30 | 18.27 | 26.78 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 29 | 8 | 4.92 | 11.24 | 18.64 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 445 | 26 | 2.14 | 7.92 | 48.43 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 872 | 257 | 2.40 | 11.51 | 26.99 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 313 | 194 | 4.99 | 24.32 | 34.09 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,101 | 371 | 1.79 | 12.16 | 293.18 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 45 | 0 | 1.33 | 2.20 | 4.90 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 287 | 0 | 3.14 | 4.45 | 7.15 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 220 | 23 | 10.84 | 15.93 | 17.13 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 68 | 0 | 2.47 | 9.68 | 12.09 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 629 | 13 | 2.04 | 7.16 | 29.41 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 944 | 252 | 2.16 | 10.27 | 24.05 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 397 | 32 | 2.56 | 6.49 | 17.55 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 220 | 44 | 12.94 | 16.64 | 18.32 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 68 | 0 | 2.98 | 8.12 | 14.10 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 629 | 15 | 2.19 | 10.52 | 49.80 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 944 | 259 | 2.28 | 10.50 | 34.27 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 397 | 119 | 4.84 | 14.71 | 34.15 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,131 | 451 | 2.83 | 15.19 | 267.15 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 41 | 0 | 3.69 | 6.36 | 6.94 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 314 | 0 | 3.89 | 5.35 | 6.24 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 106 | 2 | 12.80 | 14.79 | 17.06 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 44 | 0 | 2.19 | 6.95 | 14.15 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 133 | 0 | 1.95 | 4.46 | 12.30 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 318 | 84 | 3.10 | 12.69 | 20.27 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 197 | 14 | 2.61 | 8.50 | 17.06 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 106 | 99 | 12.81 | 19.28 | 24.94 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 44 | 16 | 2.72 | 7.78 | 25.43 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 133 | 1 | 2.32 | 6.43 | 19.20 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 318 | 88 | 3.14 | 12.83 | 23.76 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 197 | 102 | 3.70 | 21.50 | 34.08 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 109 | 0 | 1.38 | 2.55 | 9.31 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 310 | 46 | 1.25 | 4.46 | 19.10 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 64 | 0 | 1.25 | 1.60 | 2.41 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 266 | 0 | 1.20 | 1.24 | 1.70 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 8 | 0 | 14.87 | 15.76 | 15.90 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 181 | 0 | 1.16 | 3.96 | 15.70 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 447 | 15 | 2.40 | 10.18 | 17.72 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 574 | 83 | 1.77 | 4.54 | 18.87 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `thermal` | 460 | 0 | 3.53 | 9.63 | 10.48 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 597 | 40 | 1.08 | 2.35 | 17.32 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `compute` | 8 | 0 | 14.87 | 15.76 | 15.90 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 181 | 0 | 1.09 | 2.17 | 15.70 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 447 | 35 | 2.09 | 10.60 | 21.61 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 574 | 89 | 2.02 | 5.06 | 27.45 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `thermal` | 460 | 0 | 3.56 | 9.27 | 10.48 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 597 | 202 | 1.96 | 2.83 | 37.99 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 853 | 326 | 2.29 | 14.06 | 289.90 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 406 | 0 | 2.39 | 3.35 | 11.01 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 400 | 19 | 11.06 | 13.92 | 17.10 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 103 | 0 | 2.00 | 8.49 | 15.95 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 319 | 6 | 2.04 | 5.88 | 29.42 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 965 | 245 | 2.15 | 10.49 | 24.58 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 363 | 25 | 2.95 | 8.01 | 17.55 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 400 | 179 | 13.90 | 16.81 | 20.12 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 103 | 10 | 1.96 | 8.69 | 19.82 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 319 | 7 | 2.21 | 8.00 | 47.59 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 965 | 255 | 2.30 | 10.88 | 34.44 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 363 | 124 | 4.97 | 15.39 | 34.15 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 568 | 265 | 3.41 | 17.06 | 224.06 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 399 | 0 | 3.70 | 3.70 | 6.67 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 54 | 4 | 13.24 | 15.46 | 17.23 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 54 | 0 | 1.98 | 3.93 | 14.94 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 83 | 0 | 1.98 | 3.32 | 9.30 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 161 | 18 | 3.12 | 9.18 | 20.15 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 68 | 12 | 2.62 | 9.56 | 17.11 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 54 | 50 | 13.24 | 19.01 | 24.75 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 54 | 11 | 1.90 | 8.97 | 26.05 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 83 | 0 | 2.18 | 4.55 | 14.33 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 161 | 20 | 3.16 | 9.73 | 22.96 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 68 | 34 | 3.95 | 18.48 | 34.08 |
| `n6_vs_a100` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 100 | 0 | 1.39 | 2.70 | 9.74 |
| `n6_vs_a100` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 275 | 46 | 1.66 | 5.47 | 19.13 |
| `n6_vs_a100` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 317 | 0 | 1.15 | 1.20 | 2.62 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 20 | 6 | 13.10 | 16.80 | 18.50 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 646 | 0 | 1.15 | 5.95 | 9.19 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 348 | 0 | 2.40 | 10.26 | 16.75 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 604 | 81 | 1.63 | 4.22 | 18.91 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 512 | 66 | 1.17 | 2.13 | 17.67 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `compute` | 20 | 6 | 13.10 | 16.80 | 18.50 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 646 | 0 | 1.12 | 5.72 | 9.30 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 348 | 22 | 2.15 | 10.83 | 23.48 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 604 | 93 | 1.75 | 4.26 | 24.39 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 512 | 168 | 1.98 | 2.59 | 37.99 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 139 | 0 | 1.09 | 1.67 | 9.10 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 429 | 45 | 1.21 | 2.58 | 19.10 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 36 | 0 | 1.10 | 1.14 | 1.57 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 133 | 0 | 1.12 | 1.17 | 1.23 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 297 | 0 | 1.06 | 4.22 | 7.75 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 442 | 7 | 2.25 | 9.88 | 17.50 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 557 | 77 | 1.69 | 4.13 | 18.81 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `thermal` | 336 | 0 | 1.65 | 4.26 | 8.51 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 573 | 28 | 1.03 | 1.76 | 17.27 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 297 | 0 | 1.05 | 4.22 | 8.06 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 442 | 9 | 2.04 | 10.50 | 21.11 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 557 | 83 | 1.71 | 4.35 | 27.45 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `thermal` | 336 | 0 | 1.70 | 4.34 | 8.99 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 573 | 186 | 1.96 | 2.55 | 37.99 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 140 | 0 | 1.46 | 2.60 | 4.32 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 294 | 48 | 1.26 | 3.51 | 19.13 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 176 | 0 | 1.15 | 1.17 | 1.34 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 8 | 0 | 12.00 | 13.33 | 13.52 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 646 | 0 | 1.04 | 2.85 | 9.13 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 337 | 0 | 2.25 | 10.19 | 16.46 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 594 | 80 | 1.42 | 4.21 | 18.87 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 509 | 34 | 1.06 | 1.79 | 17.27 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `compute` | 8 | 0 | 12.00 | 13.33 | 13.52 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 646 | 0 | 1.06 | 2.73 | 9.16 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 337 | 12 | 2.05 | 10.56 | 21.12 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 594 | 92 | 1.66 | 4.26 | 24.39 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 509 | 174 | 1.98 | 2.47 | 37.99 |

## Per model, per context, per batch and per design class

Each row is that class's **fastest** feasible design at that batch, read against the iso-area GPU comparator the published study already chose for it. The `densest` pick of every class is in `analytical.json` beside it.

**The ROM-versus-GPU ratio under speculation is `T_cycle(GPU) / T_cycle(ROM)` and carries no `tau` at all.** The acceptance length is a property of the model and its drafter, not of the machine, so it is the same on both sides and cancels out of the ratio. Every movement in the last column is therefore a machine effect and nothing else.

### `n5_vs_b200-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,228.3 | 2,180.2-4,046.7 | 10.17 | **no** | `b200_sxm-x93-nvl72-hybrid` | 1,056.7 | 2,120.3-3,935.5 | 2.11 | yes | 4.948x | 1.028x | 0.208x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,338.7 | 2,368.0-4,395.4 | 9.56 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,053.8 | 2,060.7-3,824.9 | 2.17 | yes | 5.066x | 1.149x | 0.227x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,228.3 | 2,180.2-4,046.7 | 10.17 | **no** | `b200_sxm-x93-nvl72-hybrid` | 1,056.7 | 2,120.3-3,935.5 | 2.11 | yes | 4.948x | 1.028x | 0.208x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,338.7 | 2,368.0-4,395.4 | 9.56 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,053.8 | 2,060.7-3,824.9 | 2.17 | yes | 5.066x | 1.149x | 0.227x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,228.3 | 2,180.2-4,046.7 | 10.17 | **no** | `b200_sxm-x93-nvl72-hybrid` | 1,032.2 | 1,890.4-3,508.8 | 2.32 | yes | 5.065x | 1.153x | 0.228x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,338.7 | 2,368.0-4,395.4 | 9.56 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,028.4 | 1,839.6-3,414.5 | 2.37 | yes | 5.191x | 1.287x | 0.248x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,228.3 | 2,180.2-4,046.7 | 10.17 | **no** | `b200_sxm-x93-nvl72-hybrid` | 988.2 | 1,521.0-2,823.2 | 2.75 | yes | 5.291x | 1.433x | 0.271x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,338.7 | 2,368.0-4,395.4 | 9.56 | **no** | `b200_sxm-x87-nvl72-hybrid` | 982.2 | 1,469.9-2,728.4 | 2.83 | yes | 5.436x | 1.611x | 0.296x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,228.3 | 2,180.2-4,046.7 | 10.17 | **no** | `b200_sxm-x93-nvl72-hybrid` | 925.7 | 670.7-1,245.0 | 5.85 | yes | 5.648x | 3.250x | 0.576x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,338.7 | 2,368.0-4,395.4 | 9.56 | **no** | `b200_sxm-x87-nvl72-hybrid` | 922.5 | 670.1-1,243.7 | 5.84 | yes | 5.787x | 3.534x | 0.611x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 5,087.5 | 1,230.7-2,284.3 | 17.53 | **no** | `b200_sxm-x93-nvl72-hybrid` | 837.4 | 557.5-1,034.9 | 6.37 | yes | 6.075x | 2.207x | 0.363x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,204.7 | 2,055.0-3,814.3 | 10.74 | **no** | `b200_sxm-x231-nvl72-hybrid` | 932.5 | 1,290.9-2,396.1 | 3.06 | yes | 5.581x | 1.592x | 0.285x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 4,850.1 | 1,026.1-1,904.6 | 20.04 | **no** | `b200_sxm-x134-nvl72-hybrid` | 777.7 | 515.2-956.2 | 6.40 | yes | 6.237x | 1.992x | 0.319x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,201.5 | 2,045.5-3,796.7 | 10.78 | **no** | `b200_sxm-x347-nvl72-hybrid` | 886.5 | 668.1-1,240.2 | 5.63 | yes | 5.867x | 3.061x | 0.522x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 3,322.9 | 742.4-1,378.0 | 18.98 | **no** | `b200_sxm-x179-nvl72-hybrid` | 526.9 | 410.9-762.7 | 5.44 | yes | 6.306x | 1.807x | 0.286x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,179.1 | 927.7-1,721.9 | 19.10 | **no** | `b200_sxm-x347-nvl72-hybrid` | 664.4 | 462.6-858.6 | 6.09 | yes | 6.290x | 2.006x | 0.319x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 1,640.8 | 294.2-546.1 | 23.65 | **no** | `b200_sxm-x179-nvl72-hybrid` | 265.4 | 201.2-373.5 | 5.59 | yes | 6.183x | 1.462x | 0.236x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,147.3 | 242.8-450.7 | 37.50 | **no** | `b200_sxm-x347-nvl72-hybrid` | 355.2 | 321.3-596.3 | 4.69 | yes | 6.045x | 0.756x | 0.125x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 558.9 | 88.1-163.5 | 26.91 | **no** | `b200_sxm-x179-nvl72-hybrid` | 142.2 | 57.6-106.9 | 10.47 | **no** | 3.929x | 1.529x | 0.389x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 685.8 | 200.8-372.7 | 14.48 | **no** | `b200_sxm-x347-nvl72-hybrid` | 172.6 | 82.2-152.5 | 8.91 | **no** | 3.972x | 2.444x | 0.615x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.125x to 0.615x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 0 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 1,646.9-3,056.8 | 12.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 199.5-370.4 | 9.24 | **no** | 11.390x | 8.253x | 0.725x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,055.1 | 1,719.1-3,191.0 | 12.47 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 204.6-379.8 | 9.17 | **no** | 11.427x | 8.403x | 0.735x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 1,646.9-3,056.8 | 12.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 199.5-370.4 | 9.24 | **no** | 11.390x | 8.253x | 0.725x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,055.1 | 1,719.1-3,191.0 | 12.47 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 204.6-379.8 | 9.17 | **no** | 11.427x | 8.403x | 0.735x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 1,646.9-3,056.8 | 12.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 199.5-370.4 | 9.24 | **no** | 11.390x | 8.253x | 0.725x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,055.1 | 1,719.1-3,191.0 | 12.47 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 204.6-379.8 | 9.17 | **no** | 11.427x | 8.403x | 0.735x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 1,646.9-3,056.8 | 12.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 199.5-370.4 | 9.24 | **no** | 11.390x | 8.253x | 0.725x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,055.1 | 1,719.1-3,191.0 | 12.47 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 204.6-379.8 | 9.17 | **no** | 11.427x | 8.403x | 0.735x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 1,646.9-3,056.8 | 12.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 199.5-370.4 | 9.24 | **no** | 11.390x | 8.253x | 0.725x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,055.1 | 1,719.1-3,191.0 | 12.47 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 204.6-379.8 | 9.17 | **no** | 11.427x | 8.403x | 0.735x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,951.9 | 1,646.9-3,056.8 | 12.75 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 199.5-370.4 | 9.24 | **no** | 11.390x | 8.253x | 0.725x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4,931.7 | 1,541.9-2,862.0 | 13.56 | **no** | `a100_sxm_80gb-x448-hybrid` | 433.5 | 203.8-378.2 | 9.02 | **no** | 11.378x | 7.567x | 0.665x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,669.0 | 905.1-1,679.9 | 21.87 | **no** | `a100_sxm_80gb-x258-hybrid` | 375.9 | 178.4-331.2 | 8.93 | **no** | 12.420x | 5.072x | 0.408x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,927.4 | 1,534.3-2,847.8 | 13.62 | **no** | `a100_sxm_80gb-x672-hybrid` | 433.5 | 205.2-380.9 | 8.96 | **no** | 11.368x | 7.477x | 0.658x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 2,994.5 | 429.5-797.3 | 29.56 | **no** | `a100_sxm_80gb-x335-hybrid` | 234.9 | 126.7-235.2 | 7.86 | yes | 12.746x | 3.390x | 0.266x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,673.9 | 679.1-1,260.4 | 22.94 | **no** | `a100_sxm_80gb-x672-hybrid` | 322.5 | 162.4-301.4 | 8.42 | **no** | 11.392x | 4.182x | 0.367x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,194.1 | 157.1-291.6 | 32.23 | **no** | `a100_sxm_80gb-x337-hybrid` | 98.0 | 67.0-124.4 | 6.20 | yes | 12.184x | 2.344x | 0.192x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,680.0 | 367.9-682.9 | 19.36 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.6 | 92.7-172.0 | 7.12 | yes | 10.797x | 3.970x | 0.368x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 331.5 | 50.6-94.0 | 27.76 | **no** | `a100_sxm_80gb-x337-hybrid` | 37.3 | 16.7-30.9 | 9.50 | **no** | 8.878x | 3.039x | 0.342x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 606.9 | 134.5-249.7 | 19.13 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.3 | 51.2-95.0 | 4.91 | yes | 10.233x | 2.627x | 0.257x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.192x to 0.735x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 0 of 20 ROM rows and 4 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,977.8 | 1,825.8-3,388.8 | 11.56 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,064.7 | 2,310.7-4,288.9 | 1.95 | yes | 4.675x | 0.790x | 0.169x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,818.5 | 3,113.4-5,778.9 | 6.56 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,071.3 | 2,476.9-4,597.4 | 1.83 | yes | 4.498x | 1.257x | 0.279x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,977.8 | 1,825.8-3,388.8 | 11.56 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,064.7 | 2,310.7-4,288.9 | 1.95 | yes | 4.675x | 0.790x | 0.169x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,818.5 | 3,113.4-5,778.9 | 6.56 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,071.3 | 2,476.9-4,597.4 | 1.83 | yes | 4.498x | 1.257x | 0.279x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,977.8 | 1,825.8-3,388.8 | 11.56 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,042.0 | 2,051.0-3,807.0 | 2.15 | yes | 4.777x | 0.890x | 0.186x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,818.5 | 3,113.4-5,778.9 | 6.56 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,050.4 | 2,184.5-4,054.7 | 2.04 | yes | 4.587x | 1.425x | 0.311x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,977.8 | 1,825.8-3,388.8 | 11.56 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,000.0 | 1,685.6-3,128.7 | 2.52 | yes | 4.978x | 1.083x | 0.218x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,818.5 | 3,113.4-5,778.9 | 6.56 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,012.0 | 1,759.2-3,265.4 | 2.44 | yes | 4.761x | 1.770x | 0.372x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,977.8 | 1,825.8-3,388.8 | 11.56 | **no** | `b200_sxm-x116-nvl72-hybrid` | 941.9 | 1,334.6-2,477.2 | 2.99 | yes | 5.285x | 1.368x | 0.259x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,818.5 | 3,113.4-5,778.9 | 6.56 | yes | `b200_sxm-x144-nvl72-hybrid` | 958.0 | 1,390.2-2,580.4 | 2.92 | yes | 5.030x | 2.239x | 0.445x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 4,903.9 | 1,927.4-3,577.5 | 10.79 | **no** | `b200_sxm-x134-nvl72-hybrid` | 880.3 | 623.3-1,156.9 | 5.99 | yes | 5.571x | 3.092x | 0.555x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,675.1 | 2,459.4-4,565.0 | 8.06 | **no** | `b200_sxm-x347-nvl72-hybrid` | 957.9 | 1,416.1-2,628.4 | 2.87 | yes | 4.881x | 1.737x | 0.356x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 4,584.6 | 1,084.4-2,012.8 | 17.93 | **no** | `b200_sxm-x134-nvl72-hybrid` | 769.2 | 513.6-953.4 | 6.35 | yes | 5.960x | 2.111x | 0.354x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,504.6 | 1,456.7-2,703.8 | 13.11 | **no** | `b200_sxm-x347-nvl72-hybrid` | 882.2 | 667.0-1,238.0 | 5.61 | yes | 5.106x | 2.184x | 0.428x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 3,058.6 | 632.6-1,174.1 | 20.50 | **no** | `b200_sxm-x179-nvl72-hybrid` | 515.4 | 408.2-757.6 | 5.35 | yes | 5.934x | 1.550x | 0.261x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,071.9 | 649.8-1,206.0 | 20.05 | **no** | `b200_sxm-x347-nvl72-hybrid` | 654.9 | 460.7-855.2 | 6.03 | yes | 4.691x | 1.410x | 0.301x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 1,269.4 | 171.0-317.4 | 31.47 | **no** | `b200_sxm-x179-nvl72-hybrid` | 254.0 | 199.6-370.5 | 5.40 | yes | 4.998x | 0.857x | 0.171x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,259.4 | 234.7-435.6 | 22.75 | **no** | `b200_sxm-x347-nvl72-hybrid` | 344.5 | 319.0-592.2 | 4.58 | yes | 3.655x | 0.736x | 0.201x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 363.9 | 58.9-109.3 | 26.20 | **no** | `b200_sxm-x179-nvl72-hybrid` | 129.7 | 55.8-103.5 | 9.86 | **no** | 2.805x | 1.056x | 0.376x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 359.4 | 93.5-173.5 | 16.30 | **no** | `b200_sxm-x347-nvl72-hybrid` | 162.8 | 80.3-149.0 | 8.60 | **no** | 2.208x | 1.165x | 0.528x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.169x to 0.555x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 5 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,695.2 | 2,270.2-4,213.9 | 8.77 | **no** | `a100_sxm_80gb-x312-hybrid` | 431.5 | 202.2-375.3 | 9.05 | **no** | 10.882x | 11.228x | 1.032x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 4,457.6 | 1,657.1-3,075.9 | 11.41 | **no** | `a100_sxm_80gb-x168-hybrid` | 444.9 | 205.5-381.4 | 9.18 | **no** | 10.020x | 8.064x | 0.805x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,695.2 | 2,270.2-4,213.9 | 8.77 | **no** | `a100_sxm_80gb-x312-hybrid` | 431.5 | 202.2-375.3 | 9.05 | **no** | 10.882x | 11.228x | 1.032x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,256.3 | 2,850.3-5,290.5 | 6.33 | yes | `a100_sxm_80gb-x672-hybrid` | 430.7 | 205.0-380.6 | 8.91 | **no** | 9.881x | 13.902x | 1.407x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,695.2 | 2,270.2-4,213.9 | 8.77 | **no** | `a100_sxm_80gb-x312-hybrid` | 431.5 | 202.2-375.3 | 9.05 | **no** | 10.882x | 11.228x | 1.032x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,256.3 | 2,850.3-5,290.5 | 6.33 | yes | `a100_sxm_80gb-x672-hybrid` | 430.7 | 205.0-380.6 | 8.91 | **no** | 9.881x | 13.902x | 1.407x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,695.2 | 2,270.2-4,213.9 | 8.77 | **no** | `a100_sxm_80gb-x312-hybrid` | 431.5 | 202.2-375.3 | 9.05 | **no** | 10.882x | 11.228x | 1.032x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,256.3 | 2,850.3-5,290.5 | 6.33 | yes | `a100_sxm_80gb-x672-hybrid` | 430.7 | 205.0-380.6 | 8.91 | **no** | 9.881x | 13.902x | 1.407x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,695.2 | 2,270.2-4,213.9 | 8.77 | **no** | `a100_sxm_80gb-x312-hybrid` | 431.5 | 202.2-375.3 | 9.05 | **no** | 10.882x | 11.228x | 1.032x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,256.3 | 2,850.3-5,290.5 | 6.33 | yes | `a100_sxm_80gb-x672-hybrid` | 430.7 | 205.0-380.6 | 8.91 | **no** | 9.881x | 13.902x | 1.407x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 4,658.6 | 1,402.0-2,602.3 | 14.09 | **no** | `a100_sxm_80gb-x337-hybrid` | 427.3 | 198.7-368.9 | 9.12 | **no** | 10.901x | 7.055x | 0.647x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,142.7 | 1,794.1-3,330.0 | 9.79 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 205.0-380.6 | 8.91 | **no** | 9.618x | 8.750x | 0.910x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 4,239.1 | 766.2-1,422.2 | 23.46 | **no** | `a100_sxm_80gb-x335-hybrid` | 394.2 | 187.6-348.2 | 8.91 | **no** | 10.753x | 4.084x | 0.380x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,559.7 | 1,599.4-2,968.8 | 9.44 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 205.0-380.6 | 8.91 | **no** | 8.264x | 7.801x | 0.944x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 2,465.2 | 326.3-605.6 | 32.04 | **no** | `a100_sxm_80gb-x337-hybrid` | 230.7 | 126.1-234.1 | 7.76 | yes | 10.684x | 2.587x | 0.242x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,875.7 | 494.8-918.4 | 16.07 | **no** | `a100_sxm_80gb-x672-hybrid` | 318.0 | 162.0-300.8 | 8.32 | **no** | 5.899x | 3.053x | 0.518x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 833.5 | 109.4-203.0 | 32.31 | **no** | `a100_sxm_80gb-x337-hybrid` | 94.7 | 66.6-123.6 | 6.03 | yes | 8.799x | 1.642x | 0.187x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 597.6 | 127.5-236.7 | 19.87 | **no** | `a100_sxm_80gb-x672-hybrid` | 151.4 | 90.8-168.5 | 7.07 | yes | 3.947x | 1.404x | 0.356x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 223.3 | 34.8-64.6 | 27.19 | **no** | `a100_sxm_80gb-x337-hybrid` | 35.5 | 14.6-27.1 | 10.30 | **no** | 6.295x | 2.384x | 0.379x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 156.6 | 77.8-144.4 | 8.54 | **no** | `a100_sxm_80gb-x672-hybrid` | 56.9 | 45.5-84.5 | 5.30 | yes | 2.752x | 1.709x | 0.621x |

**Does the ratio compress?** Of 20 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 9 move it UP. The movement spans 0.187x to 1.407x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 4 of 20 ROM rows and 4 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,280.8 | 2,329.8-4,324.4 | 9.61 | **no** | `b200_sxm-x90-nvl72-hybrid` | 1,055.5 | 2,091.3-3,881.7 | 2.14 | yes | 5.003x | 1.114x | 0.223x |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,479.0 | 2,673.1-4,961.5 | 8.69 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,054.0 | 2,060.9-3,825.3 | 2.17 | yes | 5.198x | 1.297x | 0.250x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,280.8 | 2,329.8-4,324.4 | 9.61 | **no** | `b200_sxm-x90-nvl72-hybrid` | 1,055.5 | 2,091.3-3,881.7 | 2.14 | yes | 5.003x | 1.114x | 0.223x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,479.0 | 2,673.1-4,961.5 | 8.69 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,054.0 | 2,060.9-3,825.3 | 2.17 | yes | 5.198x | 1.297x | 0.250x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,280.8 | 2,329.8-4,324.4 | 9.61 | **no** | `b200_sxm-x90-nvl72-hybrid` | 1,030.7 | 1,865.9-3,463.3 | 2.34 | yes | 5.124x | 1.249x | 0.244x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,479.0 | 2,673.1-4,961.5 | 8.69 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,028.8 | 1,839.9-3,415.2 | 2.37 | yes | 5.326x | 1.453x | 0.273x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,280.8 | 2,329.8-4,324.4 | 9.61 | **no** | `b200_sxm-x90-nvl72-hybrid` | 985.9 | 1,496.4-2,777.5 | 2.79 | yes | 5.356x | 1.557x | 0.291x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,479.0 | 2,673.1-4,961.5 | 8.69 | **no** | `b200_sxm-x87-nvl72-hybrid` | 982.9 | 1,470.4-2,729.2 | 2.83 | yes | 5.575x | 1.818x | 0.326x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,280.8 | 2,329.8-4,324.4 | 9.61 | **no** | `b200_sxm-x90-nvl72-hybrid` | 919.6 | 649.4-1,205.4 | 6.00 | yes | 5.743x | 3.588x | 0.625x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,479.0 | 2,673.1-4,961.5 | 8.69 | **no** | `b200_sxm-x87-nvl72-hybrid` | 923.7 | 670.4-1,244.3 | 5.84 | yes | 5.932x | 3.987x | 0.672x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5,211.3 | 1,325.3-2,459.9 | 16.67 | **no** | `b200_sxm-x90-nvl72-hybrid` | 830.9 | 539.9-1,002.1 | 6.53 | yes | 6.272x | 2.455x | 0.391x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,349.8 | 2,312.6-4,292.5 | 9.81 | **no** | `b200_sxm-x231-nvl72-hybrid` | 933.4 | 1,291.4-2,397.0 | 3.06 | yes | 5.731x | 1.791x | 0.312x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 5,024.6 | 1,138.2-2,112.6 | 18.72 | **no** | `b200_sxm-x134-nvl72-hybrid` | 779.9 | 515.6-957.0 | 6.41 | yes | 6.443x | 2.208x | 0.343x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,346.7 | 2,301.5-4,271.9 | 9.85 | **no** | `b200_sxm-x347-nvl72-hybrid` | 887.6 | 668.4-1,240.7 | 5.63 | yes | 6.024x | 3.443x | 0.572x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 3,402.3 | 502.9-933.4 | 28.69 | **no** | `b200_sxm-x179-nvl72-hybrid` | 529.9 | 411.6-764.0 | 5.46 | yes | 6.420x | 1.222x | 0.190x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,457.5 | 1,050.4-1,949.8 | 17.99 | **no** | `b200_sxm-x347-nvl72-hybrid` | 666.9 | 463.0-859.4 | 6.11 | yes | 6.684x | 2.269x | 0.339x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,713.1 | 315.3-585.3 | 23.03 | **no** | `b200_sxm-x173-nvl72-hybrid` | 265.7 | 191.6-355.6 | 5.88 | yes | 6.447x | 1.646x | 0.255x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,433.4 | 271.8-504.6 | 37.96 | **no** | `b200_sxm-x347-nvl72-hybrid` | 358.1 | 321.8-597.4 | 4.72 | yes | 6.795x | 0.845x | 0.124x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 620.7 | 96.5-179.1 | 27.27 | **no** | `b200_sxm-x173-nvl72-hybrid` | 142.9 | 53.9-100.1 | 11.23 | **no** | 4.344x | 1.789x | 0.412x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 769.7 | 108.8-202.0 | 29.99 | **no** | `b200_sxm-x347-nvl72-hybrid` | 175.3 | 82.7-153.4 | 8.99 | **no** | 4.389x | 1.316x | 0.300x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.124x to 0.672x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 0 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 5,026.9 | 1,760.0-3,266.7 | 12.11 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 201.2-373.4 | 9.23 | **no** | 11.474x | 8.749x | 0.763x |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,233.2 | 1,940.5-3,601.9 | 11.43 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 204.6-379.8 | 9.18 | **no** | 11.810x | 9.483x | 0.803x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 5,026.9 | 1,760.0-3,266.7 | 12.11 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 201.2-373.4 | 9.23 | **no** | 11.474x | 8.749x | 0.763x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,233.2 | 1,940.5-3,601.9 | 11.43 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 204.6-379.8 | 9.18 | **no** | 11.810x | 9.483x | 0.803x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 5,026.9 | 1,760.0-3,266.7 | 12.11 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 201.2-373.4 | 9.23 | **no** | 11.474x | 8.749x | 0.763x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,233.2 | 1,940.5-3,601.9 | 11.43 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 204.6-379.8 | 9.18 | **no** | 11.810x | 9.483x | 0.803x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 5,026.9 | 1,760.0-3,266.7 | 12.11 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 201.2-373.4 | 9.23 | **no** | 11.474x | 8.749x | 0.763x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,233.2 | 1,940.5-3,601.9 | 11.43 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 204.6-379.8 | 9.18 | **no** | 11.810x | 9.483x | 0.803x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 5,026.9 | 1,760.0-3,266.7 | 12.11 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 201.2-373.4 | 9.23 | **no** | 11.474x | 8.749x | 0.763x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,233.2 | 1,940.5-3,601.9 | 11.43 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 204.6-379.8 | 9.18 | **no** | 11.810x | 9.483x | 0.803x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342-romfill` | 4,869.3 | 1,533.6-2,846.6 | 13.46 | **no** | `a100_sxm_80gb-x337-hybrid` | 430.8 | 198.9-369.2 | 9.18 | **no** | 11.304x | 7.709x | 0.682x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,116.8 | 1,737.7-3,225.5 | 12.48 | **no** | `a100_sxm_80gb-x448-hybrid` | 434.2 | 203.8-378.3 | 9.03 | **no** | 11.786x | 8.526x | 0.723x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 4,654.3 | 957.7-1,777.6 | 20.61 | **no** | `a100_sxm_80gb-x244-hybrid` | 373.1 | 178.0-330.5 | 8.88 | **no** | 12.475x | 5.379x | 0.431x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,112.2 | 1,728.8-3,208.8 | 12.54 | **no** | `a100_sxm_80gb-x672-hybrid` | 434.2 | 205.2-381.0 | 8.97 | **no** | 11.775x | 8.423x | 0.715x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,166.8 | 646.0-1,199.1 | 20.78 | **no** | `a100_sxm_80gb-x337-hybrid` | 236.8 | 126.6-235.0 | 7.93 | **no** | 13.373x | 5.103x | 0.382x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,973.2 | 768.1-1,425.7 | 21.93 | **no** | `a100_sxm_80gb-x672-hybrid` | 323.7 | 162.5-301.5 | 8.45 | **no** | 12.275x | 4.728x | 0.385x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,344.0 | 176.9-328.4 | 32.20 | **no** | `a100_sxm_80gb-x337-hybrid` | 98.9 | 67.1-124.6 | 6.25 | yes | 13.592x | 2.636x | 0.194x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,899.7 | 196.1-364.0 | 41.08 | **no** | `a100_sxm_80gb-x672-hybrid` | 156.7 | 92.8-172.2 | 7.16 | yes | 12.123x | 2.114x | 0.174x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 379.6 | 57.4-106.6 | 28.03 | **no** | `a100_sxm_80gb-x337-hybrid` | 37.8 | 17.3-32.1 | 9.28 | **no** | 10.028x | 3.321x | 0.331x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 721.6 | 155.0-287.7 | 19.74 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.9 | 52.8-98.0 | 4.81 | yes | 12.037x | 2.936x | 0.244x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.174x to 0.803x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 0 of 20 ROM rows and 3 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 3,539.2-6,569.2 | 6.43 | yes | `b200_sxm-x49-nvl72-tensor` | 1,065.2 | 3,251.2-6,034.7 | 1.39 | yes | 5.043x | 1.089x | 0.216x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 5,419.7 | 3,890.6-7,221.4 | 5.91 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,060.6 | 3,196.2-5,932.5 | 1.41 | yes | 5.110x | 1.217x | 0.238x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 3,539.2-6,569.2 | 6.43 | yes | `b200_sxm-x49-nvl72-tensor` | 1,042.5 | 2,801.1-5,199.2 | 1.58 | yes | 5.152x | 1.263x | 0.245x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 3,800.8-7,054.8 | 5.99 | yes | `b200_sxm-x58-nvl72-tensor` | 1,050.0 | 2,846.4-5,283.2 | 1.56 | yes | 5.114x | 1.335x | 0.261x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 3,539.2-6,569.2 | 6.43 | yes | `b200_sxm-x49-nvl72-tensor` | 1,000.6 | 2,214.6-4,110.6 | 1.92 | yes | 5.368x | 1.598x | 0.298x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 3,800.8-7,054.8 | 5.99 | yes | `b200_sxm-x58-nvl72-tensor` | 1,010.6 | 2,250.4-4,177.0 | 1.90 | yes | 5.314x | 1.689x | 0.318x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 3,539.2-6,569.2 | 6.43 | yes | `b200_sxm-x49-nvl72-tensor` | 927.9 | 1,601.8-2,973.1 | 2.46 | yes | 5.788x | 2.210x | 0.382x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 3,800.8-7,054.8 | 5.99 | yes | `b200_sxm-x58-nvl72-tensor` | 941.7 | 1,617.8-3,002.9 | 2.47 | yes | 5.702x | 2.349x | 0.412x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,361.8 | 2,175.5-4,038.1 | 10.45 | **no** | `b200_sxm-x49-hybrid` | 830.0 | 1,266.3-2,350.4 | 2.78 | yes | 6.460x | 1.718x | 0.266x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5,363.4 | 3,845.6-7,137.9 | 5.91 | yes | `b200_sxm-x87-nvl72-hybrid` | 922.5 | 1,965.2-3,647.7 | 1.99 | yes | 5.814x | 1.957x | 0.337x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 5,209.0 | 2,144.5-3,980.4 | 10.30 | **no** | `b200_sxm-x110-nvl72-hybrid` | 862.1 | 1,421.4-2,638.3 | 2.57 | yes | 6.042x | 1.509x | 0.250x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,337.0 | 3,897.1-7,233.4 | 5.81 | yes | `b200_sxm-x231-nvl72-hybrid` | 932.5 | 1,926.5-3,575.8 | 2.05 | yes | 5.723x | 2.023x | 0.353x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,209.0 | 2,144.5-3,980.4 | 10.30 | **no** | `b200_sxm-x173-nvl72-hybrid` | 815.7 | 1,217.9-2,260.5 | 2.84 | yes | 6.386x | 1.761x | 0.276x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,334.9 | 3,884.1-7,209.4 | 5.82 | yes | `b200_sxm-x347-nvl72-hybrid` | 886.5 | 1,959.5-3,637.2 | 1.92 | yes | 6.018x | 1.982x | 0.329x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,572.7 | 961.1-1,783.9 | 15.76 | **no** | `b200_sxm-x173-nvl72-hybrid` | 519.7 | 704.0-1,306.7 | 3.13 | yes | 6.875x | 1.365x | 0.199x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,536.9 | 1,961.8-3,641.3 | 9.81 | **no** | `b200_sxm-x347-nvl72-hybrid` | 664.4 | 853.4-1,583.9 | 3.30 | yes | 6.828x | 2.299x | 0.337x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,474.7 | 320.4-594.6 | 19.52 | **no** | `b200_sxm-x173-nvl72-hybrid` | 262.6 | 210.0-389.8 | 5.30 | yes | 5.616x | 1.525x | 0.272x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,637.2 | 548.5-1,018.1 | 20.39 | **no** | `b200_sxm-x347-nvl72-hybrid` | 355.2 | 459.4-852.7 | 3.28 | yes | 7.424x | 1.194x | 0.161x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 434.2 | 134.6-249.8 | 13.68 | **no** | `b200_sxm-x173-nvl72-hybrid` | 139.3 | 56.9-105.7 | 10.37 | **no** | 3.117x | 2.363x | 0.758x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 872.6 | 203.4-377.6 | 18.19 | **no** | `b200_sxm-x347-nvl72-hybrid` | 172.6 | 86.2-159.9 | 8.50 | **no** | 5.054x | 2.361x | 0.467x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.161x to 0.758x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 2,792.1-5,182.4 | 7.83 | yes | `a100_sxm_80gb-x132-hybrid` | 445.6 | 793.6-1,473.0 | 2.38 | yes | 11.569x | 3.518x | 0.304x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 5,184.8 | 2,948.0-5,471.9 | 7.46 | yes | `a100_sxm_80gb-x672-hybrid` | 433.5 | 797.4-1,480.1 | 2.30 | yes | 11.962x | 3.697x | 0.309x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 2,792.1-5,182.4 | 7.83 | yes | `a100_sxm_80gb-x132-hybrid` | 445.6 | 793.6-1,473.0 | 2.38 | yes | 11.569x | 3.518x | 0.304x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.0 | 3,028.3-5,620.8 | 7.14 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.381x | 3.763x | 0.331x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 2,792.1-5,182.4 | 7.83 | yes | `a100_sxm_80gb-x132-hybrid` | 445.6 | 793.6-1,473.0 | 2.38 | yes | 11.569x | 3.518x | 0.304x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.0 | 3,028.3-5,620.8 | 7.14 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.381x | 3.763x | 0.331x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 2,792.1-5,182.4 | 7.83 | yes | `a100_sxm_80gb-x132-hybrid` | 445.6 | 793.6-1,473.0 | 2.38 | yes | 11.569x | 3.518x | 0.304x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.0 | 3,028.3-5,620.8 | 7.14 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.381x | 3.763x | 0.331x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 2,792.1-5,182.4 | 7.83 | yes | `a100_sxm_80gb-x132-hybrid` | 445.6 | 793.6-1,473.0 | 2.38 | yes | 11.569x | 3.518x | 0.304x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.0 | 3,028.3-5,620.8 | 7.14 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.381x | 3.763x | 0.331x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,021.1 | 2,739.9-5,085.6 | 7.77 | yes | `a100_sxm_80gb-x272-hybrid` | 437.9 | 771.4-1,431.8 | 2.41 | yes | 11.467x | 3.552x | 0.310x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,079.3 | 3,078.9-5,714.8 | 6.99 | yes | `a100_sxm_80gb-x448-hybrid` | 433.5 | 776.2-1,440.7 | 2.37 | yes | 11.718x | 3.967x | 0.339x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,830.1 | 1,643.5-3,050.6 | 12.46 | **no** | `a100_sxm_80gb-x335-hybrid` | 397.7 | 590.3-1,095.7 | 2.86 | yes | 12.145x | 2.784x | 0.229x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,076.0 | 3,067.0-5,692.8 | 7.02 | yes | `a100_sxm_80gb-x672-hybrid` | 433.5 | 797.4-1,480.1 | 2.30 | yes | 11.711x | 3.846x | 0.328x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,068.8 | 715.7-1,328.4 | 18.18 | **no** | `a100_sxm_80gb-x335-hybrid` | 234.9 | 234.7-435.6 | 4.24 | yes | 13.062x | 3.050x | 0.233x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,987.7 | 1,469.0-2,726.7 | 11.51 | **no** | `a100_sxm_80gb-x672-hybrid` | 322.5 | 393.8-730.9 | 3.47 | yes | 12.365x | 3.730x | 0.302x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 1,176.6 | 332.3-616.9 | 15.01 | **no** | `a100_sxm_80gb-x335-hybrid` | 97.7 | 130.6-242.3 | 3.17 | yes | 12.048x | 2.546x | 0.211x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,977.6 | 398.9-740.3 | 21.02 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.6 | 139.4-258.8 | 4.73 | yes | 12.710x | 2.860x | 0.225x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 428.3 | 103.3-191.8 | 17.57 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.2 | 19.2-35.6 | 8.23 | **no** | 11.499x | 5.385x | 0.468x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 602.7 | 147.9-274.6 | 17.27 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.3 | 81.3-151.0 | 3.09 | yes | 10.162x | 1.819x | 0.179x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.179x to 0.468x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 13 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 5,145.7 | 2,995.7-5,560.5 | 7.28 | yes | `b200_sxm-x57-nvl72-tensor` | 1,070.0 | 3,295.1-6,116.2 | 1.38 | yes | 4.809x | 0.909x | 0.189x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 5,125.9 | 3,306.4-6,137.1 | 6.57 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,060.1 | 3,195.0-5,930.3 | 1.41 | yes | 4.835x | 1.035x | 0.214x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 5,145.7 | 2,995.7-5,560.5 | 7.28 | yes | `b200_sxm-x57-nvl72-tensor` | 1,048.2 | 2,839.8-5,271.0 | 1.57 | yes | 4.909x | 1.055x | 0.215x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,830.4 | 3,262.4-6,055.5 | 6.28 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,071.3 | 3,319.6-6,161.7 | 1.37 | yes | 4.509x | 0.983x | 0.218x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 5,145.7 | 2,995.7-5,560.5 | 7.28 | yes | `b200_sxm-x57-nvl72-tensor` | 1,007.6 | 2,244.1-4,165.4 | 1.90 | yes | 5.107x | 1.335x | 0.261x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,830.4 | 3,262.4-6,055.5 | 6.28 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,050.4 | 2,814.7-5,224.5 | 1.58 | yes | 4.599x | 1.159x | 0.252x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 5,145.7 | 2,995.7-5,560.5 | 7.28 | yes | `b200_sxm-x57-nvl72-tensor` | 936.7 | 1,613.5-2,994.9 | 2.46 | yes | 5.493x | 1.857x | 0.338x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,830.4 | 3,262.4-6,055.5 | 6.28 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,012.0 | 2,411.5-4,476.0 | 1.78 | yes | 4.773x | 1.353x | 0.283x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 4,966.0 | 2,939.5-5,456.2 | 7.16 | yes | `b200_sxm-x83-nvl72-hybrid` | 907.2 | 1,868.3-3,467.8 | 2.06 | yes | 5.474x | 1.573x | 0.287x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,830.4 | 3,262.4-6,055.5 | 6.28 | yes | `b200_sxm-x144-nvl72-hybrid` | 958.0 | 2,159.5-4,008.3 | 1.88 | yes | 5.042x | 1.511x | 0.300x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,887.4 | 2,903.4-5,389.0 | 7.14 | yes | `b200_sxm-x173-nvl72-hybrid` | 903.3 | 1,947.1-3,614.0 | 1.97 | yes | 5.411x | 1.491x | 0.276x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,675.0 | 4,469.9-8,296.7 | 4.43 | yes | `b200_sxm-x347-nvl72-hybrid` | 957.9 | 2,117.5-3,930.4 | 1.92 | yes | 4.881x | 2.111x | 0.432x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,638.1 | 1,781.6-3,306.9 | 11.04 | **no** | `b200_sxm-x173-nvl72-hybrid` | 808.5 | 1,212.6-2,250.7 | 2.83 | yes | 5.737x | 1.469x | 0.256x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,504.6 | 3,117.9-5,787.2 | 6.13 | yes | `b200_sxm-x347-nvl72-hybrid` | 882.2 | 1,952.7-3,624.4 | 1.92 | yes | 5.106x | 1.597x | 0.313x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,839.3 | 751.1-1,394.1 | 16.03 | **no** | `b200_sxm-x173-nvl72-hybrid` | 508.1 | 697.0-1,293.6 | 3.09 | yes | 5.588x | 1.078x | 0.193x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,071.8 | 1,470.8-2,729.9 | 8.86 | **no** | `b200_sxm-x347-nvl72-hybrid` | 654.9 | 848.2-1,574.3 | 3.27 | yes | 4.690x | 1.734x | 0.370x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,053.7 | 313.9-582.7 | 14.23 | **no** | `b200_sxm-x173-nvl72-hybrid` | 251.0 | 208.2-386.4 | 5.11 | yes | 4.197x | 1.508x | 0.359x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,249.0 | 416.6-773.4 | 12.71 | **no** | `b200_sxm-x347-nvl72-hybrid` | 344.5 | 454.8-844.2 | 3.21 | yes | 3.625x | 0.916x | 0.253x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 366.7 | 95.9-177.9 | 16.22 | **no** | `b200_sxm-x173-nvl72-hybrid` | 126.9 | 55.8-103.6 | 9.64 | **no** | 2.890x | 1.717x | 0.594x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 359.7 | 151.5-281.3 | 10.06 | **no** | `b200_sxm-x347-nvl72-hybrid` | 162.8 | 84.9-157.6 | 8.13 | **no** | 2.209x | 1.784x | 0.808x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.189x to 0.808x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 13 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,881.0 | 2,335.6-4,335.2 | 8.86 | **no** | `a100_sxm_80gb-x155-hybrid` | 440.0 | 787.2-1,461.2 | 2.37 | yes | 11.093x | 2.967x | 0.267x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | 4,989.2 | 4,200.6-7,796.9 | 5.04 | yes | `a100_sxm_80gb-x616-hybrid` | 430.7 | 791.1-1,468.4 | 2.31 | yes | 11.583x | 5.310x | 0.458x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,881.0 | 2,335.6-4,335.2 | 8.86 | **no** | `a100_sxm_80gb-x155-hybrid` | 440.0 | 787.2-1,461.2 | 2.37 | yes | 11.093x | 2.967x | 0.267x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 4,273.7 | 3,563.5-6,614.4 | 5.08 | yes | `a100_sxm_80gb-x448-hybrid` | 430.7 | 773.8-1,436.3 | 2.36 | yes | 9.922x | 4.605x | 0.464x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,881.0 | 2,335.6-4,335.2 | 8.86 | **no** | `a100_sxm_80gb-x155-hybrid` | 440.0 | 787.2-1,461.2 | 2.37 | yes | 11.093x | 2.967x | 0.267x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 4,273.7 | 3,563.5-6,614.4 | 5.08 | yes | `a100_sxm_80gb-x448-hybrid` | 430.7 | 773.8-1,436.3 | 2.36 | yes | 9.922x | 4.605x | 0.464x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,881.0 | 2,335.6-4,335.2 | 8.86 | **no** | `a100_sxm_80gb-x155-hybrid` | 440.0 | 787.2-1,461.2 | 2.37 | yes | 11.093x | 2.967x | 0.267x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 4,273.7 | 3,563.5-6,614.4 | 5.08 | yes | `a100_sxm_80gb-x448-hybrid` | 430.7 | 773.8-1,436.3 | 2.36 | yes | 9.922x | 4.605x | 0.464x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,881.0 | 2,335.6-4,335.2 | 8.86 | **no** | `a100_sxm_80gb-x155-hybrid` | 440.0 | 787.2-1,461.2 | 2.37 | yes | 11.093x | 2.967x | 0.267x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,267.0 | 2,924.1-5,427.5 | 6.19 | yes | `a100_sxm_80gb-x672-hybrid` | 430.7 | 794.9-1,475.5 | 2.30 | yes | 9.906x | 3.678x | 0.371x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,654.1 | 2,336.1-4,336.2 | 8.45 | **no** | `a100_sxm_80gb-x272-hybrid` | 435.1 | 769.0-1,427.4 | 2.40 | yes | 10.696x | 3.038x | 0.284x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,079.4 | 1,850.1-3,434.1 | 9.35 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 794.9-1,475.5 | 2.30 | yes | 9.471x | 2.327x | 0.246x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,200.2 | 1,365.9-2,535.3 | 13.04 | **no** | `a100_sxm_80gb-x272-hybrid` | 378.1 | 537.6-997.9 | 2.98 | yes | 11.109x | 2.541x | 0.229x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,615.9 | 1,671.5-3,102.6 | 9.17 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 794.9-1,475.5 | 2.30 | yes | 8.395x | 2.103x | 0.250x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 2,413.0 | 590.5-1,096.1 | 17.32 | **no** | `a100_sxm_80gb-x272-hybrid` | 208.8 | 210.8-391.3 | 4.20 | yes | 11.556x | 2.801x | 0.242x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,901.6 | 524.3-973.1 | 15.38 | **no** | `a100_sxm_80gb-x672-hybrid` | 318.0 | 391.9-727.4 | 3.44 | yes | 5.981x | 1.338x | 0.224x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 1,032.0 | 247.9-460.1 | 17.65 | **no** | `a100_sxm_80gb-x335-hybrid` | 94.4 | 129.0-239.5 | 3.10 | yes | 10.934x | 1.921x | 0.176x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 601.7 | 135.5-251.6 | 18.82 | **no** | `a100_sxm_80gb-x672-hybrid` | 151.4 | 135.3-251.0 | 4.75 | yes | 3.974x | 1.002x | 0.252x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 329.6 | 75.3-139.7 | 18.57 | **no** | `a100_sxm_80gb-x335-hybrid` | 35.4 | 17.5-32.5 | 8.56 | **no** | 9.320x | 4.297x | 0.461x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 157.6 | 91.2-169.3 | 7.32 | yes | `a100_sxm_80gb-x672-hybrid` | 56.9 | 67.9-126.0 | 3.55 | yes | 2.768x | 1.344x | 0.485x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.176x to 0.485x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 6 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5,462.9 | 2,301.9-4,272.7 | 10.06 | **no** | `b200_sxm-x47-nvl72-tensor` | 1,063.7 | 3,237.5-6,009.2 | 1.39 | yes | 5.136x | 0.711x | 0.138x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.8 | 4,184.1-7,766.3 | 5.60 | yes | `b200_sxm-x58-nvl72-tensor` | 1,071.4 | 3,301.9-6,128.8 | 1.38 | yes | 5.156x | 1.267x | 0.246x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5,462.9 | 2,301.9-4,272.7 | 10.06 | **no** | `b200_sxm-x47-nvl72-tensor` | 1,040.8 | 2,788.6-5,176.0 | 1.58 | yes | 5.249x | 0.825x | 0.157x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.8 | 4,184.1-7,766.3 | 5.60 | yes | `b200_sxm-x58-nvl72-tensor` | 1,050.3 | 2,847.0-5,284.5 | 1.56 | yes | 5.259x | 1.470x | 0.279x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5,462.9 | 2,301.9-4,272.7 | 10.06 | **no** | `b200_sxm-x47-nvl72-tensor` | 998.4 | 2,204.7-4,092.3 | 1.92 | yes | 5.472x | 1.044x | 0.191x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.8 | 4,184.1-7,766.3 | 5.60 | yes | `b200_sxm-x58-nvl72-tensor` | 1,011.2 | 2,251.2-4,178.5 | 1.90 | yes | 5.463x | 1.859x | 0.340x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5,462.9 | 2,301.9-4,272.7 | 10.06 | **no** | `b200_sxm-x47-hybrid` | 929.0 | 1,898.7-3,524.2 | 2.07 | yes | 5.881x | 1.212x | 0.206x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.8 | 4,184.1-7,766.3 | 5.60 | yes | `b200_sxm-x58-nvl72-tensor` | 942.6 | 1,618.7-3,004.4 | 2.47 | yes | 5.860x | 2.585x | 0.441x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5,462.9 | 2,301.9-4,272.7 | 10.06 | **no** | `b200_sxm-x47-hybrid` | 838.8 | 1,282.7-2,380.8 | 2.77 | yes | 6.513x | 1.795x | 0.276x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5,515.1 | 4,235.1-7,861.0 | 5.52 | yes | `b200_sxm-x87-nvl72-hybrid` | 923.7 | 1,967.0-3,650.9 | 1.99 | yes | 5.971x | 2.153x | 0.361x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 5,356.6 | 2,259.3-4,193.5 | 10.05 | **no** | `b200_sxm-x110-nvl72-hybrid` | 863.8 | 1,422.8-2,641.0 | 2.57 | yes | 6.202x | 1.588x | 0.256x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,484.8 | 4,292.5-7,967.5 | 5.42 | yes | `b200_sxm-x231-nvl72-hybrid` | 933.4 | 1,927.6-3,577.9 | 2.05 | yes | 5.876x | 2.227x | 0.379x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,356.6 | 2,259.3-4,193.5 | 10.05 | **no** | `b200_sxm-x173-nvl72-hybrid` | 817.6 | 1,219.2-2,263.1 | 2.84 | yes | 6.552x | 1.853x | 0.283x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,483.1 | 4,277.8-7,940.2 | 5.43 | yes | `b200_sxm-x347-nvl72-hybrid` | 887.6 | 1,961.3-3,640.5 | 1.92 | yes | 6.177x | 2.181x | 0.353x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,825.6 | 1,035.2-1,921.5 | 15.67 | **no** | `b200_sxm-x173-nvl72-hybrid` | 522.7 | 705.8-1,310.1 | 3.14 | yes | 7.318x | 1.467x | 0.200x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,845.1 | 2,163.1-4,015.1 | 9.50 | **no** | `b200_sxm-x347-nvl72-hybrid` | 666.9 | 854.7-1,586.4 | 3.31 | yes | 7.265x | 2.531x | 0.348x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,658.6 | 354.7-658.3 | 19.83 | **no** | `b200_sxm-x173-nvl72-hybrid` | 265.7 | 210.5-390.7 | 5.35 | yes | 6.242x | 1.685x | 0.270x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,988.1 | 595.9-1,106.1 | 21.26 | **no** | `b200_sxm-x347-nvl72-hybrid` | 358.1 | 460.6-854.9 | 3.30 | yes | 8.344x | 1.294x | 0.155x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 483.4 | 114.9-213.2 | 17.84 | **no** | `b200_sxm-x173-nvl72-hybrid` | 142.9 | 57.2-106.2 | 10.58 | **no** | 3.383x | 2.007x | 0.593x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,022.9 | 228.9-424.8 | 18.95 | **no** | `b200_sxm-x347-nvl72-hybrid` | 175.3 | 86.5-160.5 | 8.60 | **no** | 5.834x | 2.647x | 0.454x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.138x to 0.593x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 5,219.2 | 2,974.1-5,520.4 | 7.44 | yes | `a100_sxm_80gb-x126-hybrid` | 449.6 | 802.4-1,489.4 | 2.38 | yes | 11.608x | 3.707x | 0.319x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,352.7 | 3,355.9-6,228.9 | 6.76 | yes | `a100_sxm_80gb-x168-hybrid` | 448.5 | 805.4-1,494.9 | 2.36 | yes | 11.934x | 4.167x | 0.349x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 5,219.2 | 2,974.1-5,520.4 | 7.44 | yes | `a100_sxm_80gb-x126-hybrid` | 449.6 | 802.4-1,489.4 | 2.38 | yes | 11.608x | 3.707x | 0.319x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,352.7 | 3,355.9-6,228.9 | 6.76 | yes | `a100_sxm_80gb-x168-hybrid` | 448.5 | 805.4-1,494.9 | 2.36 | yes | 11.934x | 4.167x | 0.349x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 5,219.2 | 2,974.1-5,520.4 | 7.44 | yes | `a100_sxm_80gb-x126-hybrid` | 449.6 | 802.4-1,489.4 | 2.38 | yes | 11.608x | 3.707x | 0.319x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,352.7 | 3,355.9-6,228.9 | 6.76 | yes | `a100_sxm_80gb-x168-hybrid` | 448.5 | 805.4-1,494.9 | 2.36 | yes | 11.934x | 4.167x | 0.349x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 5,219.2 | 2,974.1-5,520.4 | 7.44 | yes | `a100_sxm_80gb-x126-hybrid` | 449.6 | 802.4-1,489.4 | 2.38 | yes | 11.608x | 3.707x | 0.319x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,352.7 | 3,355.9-6,228.9 | 6.76 | yes | `a100_sxm_80gb-x168-hybrid` | 448.5 | 805.4-1,494.9 | 2.36 | yes | 11.934x | 4.167x | 0.349x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 5,219.2 | 2,974.1-5,520.4 | 7.44 | yes | `a100_sxm_80gb-x126-hybrid` | 449.6 | 802.4-1,489.4 | 2.38 | yes | 11.608x | 3.707x | 0.319x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,352.7 | 3,355.9-6,228.9 | 6.76 | yes | `a100_sxm_80gb-x168-hybrid` | 448.5 | 805.4-1,494.9 | 2.36 | yes | 11.934x | 4.167x | 0.349x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,102.9 | 2,868.1-5,323.6 | 7.54 | yes | `a100_sxm_80gb-x272-hybrid` | 438.6 | 772.0-1,433.0 | 2.41 | yes | 11.635x | 3.715x | 0.319x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,332.6 | 3,418.7-6,345.5 | 6.61 | yes | `a100_sxm_80gb-x448-hybrid` | 434.2 | 776.8-1,441.8 | 2.37 | yes | 12.283x | 4.401x | 0.358x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,014.1 | 1,734.3-3,219.2 | 12.26 | **no** | `a100_sxm_80gb-x272-hybrid` | 383.1 | 540.5-1,003.2 | 3.01 | yes | 13.089x | 3.209x | 0.245x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,329.3 | 3,403.9-6,318.2 | 6.64 | yes | `a100_sxm_80gb-x672-hybrid` | 434.2 | 798.0-1,481.2 | 2.31 | yes | 12.275x | 4.265x | 0.347x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,324.4 | 768.9-1,427.2 | 18.33 | **no** | `a100_sxm_80gb-x335-hybrid` | 236.2 | 235.0-436.2 | 4.26 | yes | 14.075x | 3.272x | 0.232x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,424.0 | 1,619.9-3,006.8 | 11.58 | **no** | `a100_sxm_80gb-x672-hybrid` | 323.7 | 394.3-731.9 | 3.48 | yes | 13.668x | 4.108x | 0.301x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,285.4 | 260.3-483.1 | 20.94 | **no** | `a100_sxm_80gb-x335-hybrid` | 98.5 | 131.0-243.1 | 3.19 | yes | 13.044x | 1.987x | 0.152x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,403.2 | 430.0-798.2 | 23.69 | **no** | `a100_sxm_80gb-x672-hybrid` | 156.7 | 139.7-259.2 | 4.76 | yes | 15.336x | 3.079x | 0.201x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 455.1 | 116.7-216.6 | 16.54 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.8 | 19.7-36.5 | 8.14 | **no** | 12.055x | 5.933x | 0.492x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 759.1 | 165.1-306.4 | 19.50 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.9 | 85.5-158.6 | 2.97 | yes | 12.662x | 1.932x | 0.153x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.152x to 0.492x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 13 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 3,539.2-6,569.2 | 6.43 | yes | `b200_sxm-x49-nvl72-tensor` | 1,065.2 | 3,251.2-6,034.7 | 1.39 | yes | 5.043x | 1.089x | 0.216x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 3,800.9-7,055.0 | 5.99 | yes | `b200_sxm-x58-nvl72-tensor` | 1,071.2 | 3,301.5-6,127.9 | 1.38 | yes | 5.013x | 1.151x | 0.230x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 3,539.2-6,569.2 | 6.43 | yes | `b200_sxm-x49-nvl72-tensor` | 1,042.5 | 2,801.1-5,199.2 | 1.58 | yes | 5.152x | 1.263x | 0.245x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 3,800.9-7,055.0 | 5.99 | yes | `b200_sxm-x58-nvl72-tensor` | 1,050.0 | 2,846.4-5,283.2 | 1.56 | yes | 5.114x | 1.335x | 0.261x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 3,539.2-6,569.2 | 6.43 | yes | `b200_sxm-x49-nvl72-tensor` | 1,000.6 | 2,214.6-4,110.6 | 1.92 | yes | 5.368x | 1.598x | 0.298x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 3,800.9-7,055.0 | 5.99 | yes | `b200_sxm-x58-nvl72-tensor` | 1,010.6 | 2,250.4-4,177.0 | 1.90 | yes | 5.314x | 1.689x | 0.318x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,371.2 | 3,539.2-6,569.2 | 6.43 | yes | `b200_sxm-x49-nvl72-tensor` | 927.9 | 1,601.8-2,973.1 | 2.46 | yes | 5.788x | 2.210x | 0.382x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,370.0 | 3,800.9-7,055.0 | 5.99 | yes | `b200_sxm-x58-nvl72-tensor` | 941.7 | 1,617.8-3,002.9 | 2.47 | yes | 5.702x | 2.349x | 0.412x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5,361.9 | 2,175.5-4,038.1 | 10.45 | **no** | `b200_sxm-x49-hybrid` | 830.0 | 1,266.3-2,350.4 | 2.78 | yes | 6.460x | 1.718x | 0.266x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5,363.4 | 3,845.7-7,138.0 | 5.91 | yes | `b200_sxm-x87-nvl72-hybrid` | 922.5 | 1,965.2-3,647.7 | 1.99 | yes | 5.814x | 1.957x | 0.337x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 5,209.1 | 2,144.5-3,980.4 | 10.30 | **no** | `b200_sxm-x110-nvl72-hybrid` | 862.1 | 1,421.4-2,638.3 | 2.57 | yes | 6.042x | 1.509x | 0.250x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,337.0 | 3,897.1-7,233.6 | 5.81 | yes | `b200_sxm-x231-nvl72-hybrid` | 932.5 | 1,926.5-3,575.8 | 2.05 | yes | 5.723x | 2.023x | 0.353x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,209.1 | 2,144.5-3,980.4 | 10.30 | **no** | `b200_sxm-x173-nvl72-hybrid` | 815.7 | 1,217.9-2,260.5 | 2.84 | yes | 6.386x | 1.761x | 0.276x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,335.0 | 3,884.1-7,209.5 | 5.82 | yes | `b200_sxm-x347-nvl72-hybrid` | 886.5 | 1,959.5-3,637.2 | 1.92 | yes | 6.018x | 1.982x | 0.329x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,572.7 | 961.1-1,783.9 | 15.76 | **no** | `b200_sxm-x173-nvl72-hybrid` | 519.7 | 704.0-1,306.7 | 3.13 | yes | 6.875x | 1.365x | 0.199x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,537.0 | 1,961.8-3,641.4 | 9.81 | **no** | `b200_sxm-x347-nvl72-hybrid` | 664.4 | 853.4-1,583.9 | 3.30 | yes | 6.828x | 2.299x | 0.337x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,474.7 | 320.4-594.6 | 19.52 | **no** | `b200_sxm-x173-nvl72-hybrid` | 262.6 | 210.0-389.8 | 5.30 | yes | 5.616x | 1.525x | 0.272x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,637.2 | 548.5-1,018.1 | 20.39 | **no** | `b200_sxm-x347-nvl72-hybrid` | 355.2 | 459.4-852.7 | 3.28 | yes | 7.424x | 1.194x | 0.161x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 434.2 | 134.6-249.8 | 13.68 | **no** | `b200_sxm-x173-nvl72-hybrid` | 139.3 | 56.9-105.7 | 10.37 | **no** | 3.117x | 2.364x | 0.758x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 872.6 | 203.4-377.6 | 18.19 | **no** | `b200_sxm-x347-nvl72-hybrid` | 172.6 | 86.2-159.9 | 8.50 | **no** | 5.054x | 2.361x | 0.467x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.161x to 0.758x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 2,792.1-5,182.5 | 7.83 | yes | `a100_sxm_80gb-x132-hybrid` | 445.6 | 793.6-1,473.0 | 2.38 | yes | 11.569x | 3.518x | 0.304x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.2 | 3,028.3-5,620.9 | 7.14 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.381x | 3.763x | 0.331x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 2,792.1-5,182.5 | 7.83 | yes | `a100_sxm_80gb-x132-hybrid` | 445.6 | 793.6-1,473.0 | 2.38 | yes | 11.569x | 3.518x | 0.304x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.2 | 3,028.3-5,620.9 | 7.14 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.381x | 3.763x | 0.331x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 2,792.1-5,182.5 | 7.83 | yes | `a100_sxm_80gb-x132-hybrid` | 445.6 | 793.6-1,473.0 | 2.38 | yes | 11.569x | 3.518x | 0.304x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.2 | 3,028.3-5,620.9 | 7.14 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.381x | 3.763x | 0.331x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 2,792.1-5,182.5 | 7.83 | yes | `a100_sxm_80gb-x132-hybrid` | 445.6 | 793.6-1,473.0 | 2.38 | yes | 11.569x | 3.518x | 0.304x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.2 | 3,028.3-5,620.9 | 7.14 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.381x | 3.763x | 0.331x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 5,154.7 | 2,792.1-5,182.5 | 7.83 | yes | `a100_sxm_80gb-x132-hybrid` | 445.6 | 793.6-1,473.0 | 2.38 | yes | 11.569x | 3.518x | 0.304x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,096.2 | 3,028.3-5,620.9 | 7.14 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.381x | 3.763x | 0.331x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,021.1 | 2,739.9-5,085.6 | 7.77 | yes | `a100_sxm_80gb-x272-hybrid` | 437.9 | 771.4-1,431.8 | 2.41 | yes | 11.467x | 3.552x | 0.310x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,079.5 | 3,078.9-5,714.9 | 7.00 | yes | `a100_sxm_80gb-x448-hybrid` | 433.5 | 776.2-1,440.7 | 2.37 | yes | 11.719x | 3.967x | 0.339x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,830.1 | 1,643.5-3,050.6 | 12.46 | **no** | `a100_sxm_80gb-x272-hybrid` | 382.0 | 539.9-1,002.1 | 3.00 | yes | 12.643x | 3.044x | 0.241x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,076.2 | 3,067.0-5,692.8 | 7.02 | yes | `a100_sxm_80gb-x672-hybrid` | 433.5 | 797.4-1,480.1 | 2.30 | yes | 11.711x | 3.846x | 0.328x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,068.8 | 715.7-1,328.4 | 18.18 | **no** | `a100_sxm_80gb-x335-hybrid` | 234.9 | 234.7-435.6 | 4.24 | yes | 13.062x | 3.050x | 0.233x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,988.1 | 1,469.0-2,726.7 | 11.51 | **no** | `a100_sxm_80gb-x672-hybrid` | 322.5 | 393.8-730.9 | 3.47 | yes | 12.366x | 3.730x | 0.302x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 1,176.6 | 332.3-616.9 | 15.01 | **no** | `a100_sxm_80gb-x335-hybrid` | 97.7 | 130.6-242.3 | 3.17 | yes | 12.048x | 2.546x | 0.211x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,978.0 | 398.9-740.3 | 21.03 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.6 | 139.4-258.8 | 4.73 | yes | 12.712x | 2.860x | 0.225x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 428.3 | 103.3-191.8 | 17.57 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.2 | 19.2-35.6 | 8.23 | **no** | 11.499x | 5.385x | 0.468x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 602.8 | 147.9-274.6 | 17.28 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.3 | 81.3-151.0 | 3.09 | yes | 10.165x | 1.819x | 0.179x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.179x to 0.468x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 13 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-kimi-k3`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | 1,428.2 | 743.5-1,380.1 | 8.14 | **no** | `b200_sxm-x201-nvl72-hybrid` | 486.8 | 1,328.9-2,466.5 | 1.55 | yes | 2.934x | 0.560x | 0.191x |
| Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 1,779.5 | 1,483.5-2,753.5 | 5.09 | yes | `b200_sxm-x202-nvl72-hybrid` | 487.2 | 1,331.0-2,470.5 | 1.55 | yes | 3.653x | 1.115x | 0.305x |
| Kimi-K3 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,322.3 | 857.9-1,592.5 | 6.53 | yes | `b200_sxm-x202-nvl72-hybrid` | 487.2 | 1,331.0-2,470.5 | 1.55 | yes | 2.714x | 0.645x | 0.237x |
| Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,760.7 | 1,696.0-3,148.0 | 4.40 | yes | `b200_sxm-x462-nvl72-hybrid` | 480.3 | 1,243.1-2,307.5 | 1.64 | yes | 3.666x | 1.364x | 0.372x |
| Kimi-K3 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,322.3 | 857.9-1,592.5 | 6.53 | yes | `b200_sxm-x202-nvl72-hybrid` | 480.4 | 1,248.6-2,317.7 | 1.63 | yes | 2.753x | 0.687x | 0.250x |
| Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,760.7 | 1,696.0-3,148.0 | 4.40 | yes | `b200_sxm-x462-nvl72-hybrid` | 480.3 | 1,243.1-2,307.5 | 1.64 | yes | 3.666x | 1.364x | 0.372x |
| Kimi-K3 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,301.1 | 614.4-1,140.5 | 8.98 | **no** | `b200_sxm-x202-nvl72-hybrid` | 455.1 | 996.8-1,850.1 | 1.94 | yes | 2.859x | 0.616x | 0.216x |
| Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,760.7 | 1,696.0-3,148.0 | 4.40 | yes | `b200_sxm-x462-nvl72-hybrid` | 476.9 | 1,196.8-2,221.5 | 1.69 | yes | 3.692x | 1.417x | 0.384x |
| Kimi-K3 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,154.8 | 510.7-948.0 | 9.59 | **no** | `b200_sxm-x202-nvl72-hybrid` | 412.7 | 731.6-1,357.9 | 2.39 | yes | 2.798x | 0.698x | 0.250x |
| Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,760.7 | 1,696.0-3,148.0 | 4.40 | yes | `b200_sxm-x462-nvl72-hybrid` | 451.6 | 944.1-1,752.4 | 2.03 | yes | 3.899x | 1.796x | 0.461x |
| Kimi-K3 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 911.1 | 300.0-556.9 | 12.88 | **no** | `b200_sxm-x202-nvl72-hybrid` | 350.3 | 474.0-879.8 | 3.13 | yes | 2.601x | 0.633x | 0.243x |
| Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,537.9 | 1,127.4-2,092.6 | 5.78 | yes | `b200_sxm-x462-nvl72-hybrid` | 408.8 | 659.6-1,224.3 | 2.63 | yes | 3.762x | 1.709x | 0.454x |
| Kimi-K3 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 580.6 | 160.5-297.9 | 15.34 | **no** | `b200_sxm-x202-nvl72-hybrid` | 274.2 | 263.9-489.7 | 4.41 | yes | 2.118x | 0.608x | 0.287x |
| Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,264.7 | 681.4-1,264.7 | 7.87 | **no** | `b200_sxm-x462-nvl72-hybrid` | 345.5 | 406.5-754.6 | 3.60 | yes | 3.661x | 1.676x | 0.458x |
| Kimi-K3 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 176.3 | 42.4-78.7 | 17.64 | **no** | `b200_sxm-x202-nvl72-hybrid` | 140.2 | 72.0-133.6 | 8.26 | **no** | 1.257x | 0.589x | 0.468x |
| Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 509.1 | 190.9-354.4 | 11.31 | **no** | `b200_sxm-x462-nvl72-hybrid` | 193.9 | 172.8-320.8 | 4.76 | yes | 2.626x | 1.105x | 0.421x |
| Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 45.9 | 11.1-20.6 | 17.53 | **no** | `b200_sxm-x202-nvl72-hybrid` | 63.2 | 18.3-34.1 | 14.62 | **no** | 0.726x | 0.605x | 0.834x |
| Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 144.4 | 48.4-89.8 | 12.65 | **no** | `b200_sxm-x462-nvl72-hybrid` | 88.0 | 45.7-84.9 | 8.16 | **no** | 1.641x | 1.058x | 0.645x |
| Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 11.5 | 2.8-5.3 | 17.14 | **no** | `b200_sxm-x202-nvl72-hybrid` | 25.1 | 8.2-15.3 | 12.96 | **no** | 0.458x | 0.346x | 0.756x |
| Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 36.9 | 17.3-32.0 | 9.07 | **no** | `b200_sxm-x462-nvl72-hybrid` | 38.7 | 11.6-21.5 | 14.19 | **no** | 0.954x | 1.493x | 1.565x |

**Does the ratio compress?** Of 20 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.191x to 1.565x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 20 ROM rows and 15 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-kimi-k3`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x398` | 1,092.5 | 555.3-1,030.7 | 8.34 | **no** | `a100_sxm_80gb-x393-hybrid` | 127.8 | 198.2-367.8 | 2.73 | yes | 8.548x | 2.802x | 0.328x |
| Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x10` | 1,701.7 | 1,244.9-2,310.6 | 5.80 | yes | `a100_sxm_80gb-x560-hybrid` | 129.9 | 200.9-372.9 | 2.74 | yes | 13.104x | 6.196x | 0.473x |
| Kimi-K3 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 885.7 | 375.1-696.2 | 10.01 | **no** | `a100_sxm_80gb-x394-hybrid` | 127.9 | 198.3-368.0 | 2.73 | yes | 6.927x | 1.892x | 0.273x |
| Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,402.1 | 1,346.4-2,499.1 | 4.42 | yes | `a100_sxm_80gb-x1231-hybrid` | 127.9 | 190.0-352.8 | 2.85 | yes | 10.963x | 7.085x | 0.646x |
| Kimi-K3 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 885.7 | 375.1-696.2 | 10.01 | **no** | `a100_sxm_80gb-x394-hybrid` | 127.9 | 198.3-368.0 | 2.73 | yes | 6.927x | 1.892x | 0.273x |
| Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,402.1 | 1,346.4-2,499.1 | 4.42 | yes | `a100_sxm_80gb-x1231-hybrid` | 127.9 | 190.0-352.8 | 2.85 | yes | 10.963x | 7.085x | 0.646x |
| Kimi-K3 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 810.2 | 330.3-613.0 | 10.40 | **no** | `a100_sxm_80gb-x394-hybrid` | 125.8 | 183.4-340.4 | 2.91 | yes | 6.442x | 1.801x | 0.280x |
| Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,402.1 | 1,346.4-2,499.1 | 4.42 | yes | `a100_sxm_80gb-x1231-hybrid` | 127.9 | 190.0-352.8 | 2.85 | yes | 10.963x | 7.085x | 0.646x |
| Kimi-K3 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 600.3 | 191.4-355.2 | 13.30 | **no** | `a100_sxm_80gb-x394-hybrid` | 111.1 | 115.4-214.2 | 4.08 | yes | 5.403x | 1.658x | 0.307x |
| Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,402.1 | 1,346.4-2,499.1 | 4.42 | yes | `a100_sxm_80gb-x1231-hybrid` | 127.9 | 190.0-352.8 | 2.85 | yes | 10.963x | 7.085x | 0.646x |
| Kimi-K3 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 372.0 | 102.6-190.5 | 15.37 | **no** | `a100_sxm_80gb-x394-hybrid` | 93.2 | 98.7-183.2 | 4.00 | yes | 3.993x | 1.040x | 0.260x |
| Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,164.3 | 916.7-1,701.4 | 5.39 | yes | `a100_sxm_80gb-x1231-hybrid` | 118.9 | 138.8-257.7 | 3.63 | yes | 9.796x | 6.603x | 0.674x |
| Kimi-K3 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 205.7 | 53.1-98.5 | 16.43 | **no** | `a100_sxm_80gb-x394-hybrid` | 74.0 | 53.3-98.9 | 5.89 | yes | 2.781x | 0.996x | 0.358x |
| Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 851.0 | 654.8-1,215.4 | 5.51 | yes | `a100_sxm_80gb-x1231-hybrid` | 100.1 | 78.7-146.1 | 5.39 | yes | 8.502x | 8.322x | 0.979x |
| Kimi-K3 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 55.3 | 13.6-25.3 | 17.21 | **no** | `a100_sxm_80gb-x394-hybrid` | 41.7 | 33.7-62.6 | 5.24 | yes | 1.326x | 0.404x | 0.305x |
| Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 301.9 | 202.5-375.8 | 6.32 | yes | `a100_sxm_80gb-x1231-hybrid` | 63.3 | 76.0-141.1 | 3.53 | yes | 4.767x | 2.664x | 0.559x |
| Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 14.0 | 3.4-6.4 | 17.20 | **no** | `a100_sxm_80gb-x394-hybrid` | 17.2 | 8.6-16.0 | 8.49 | **no** | 0.812x | 0.401x | 0.494x |
| Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 81.8 | 52.2-96.9 | 6.65 | yes | `a100_sxm_80gb-x1231-hybrid` | 33.8 | 21.3-39.6 | 6.72 | yes | 2.420x | 2.448x | 1.011x |
| Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 3.5 | 0.9-1.6 | 17.14 | **no** | `a100_sxm_80gb-x394-hybrid` | 6.7 | 2.2-4.0 | 13.14 | **no** | 0.523x | 0.401x | 0.767x |
| Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x22` | 20.8 | 15.4-28.5 | 5.74 | yes | `a100_sxm_80gb-x1231-hybrid` | 13.0 | 7.9-14.7 | 6.99 | yes | 1.595x | 1.943x | 1.218x |

**Does the ratio compress?** Of 20 class rows in this study, 18 move the ROM-versus-GPU ratio DOWN under speculation and 2 move it UP. The movement spans 0.260x to 1.218x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 10 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-kimi-k3-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x383` | 946.4 | 425.7-790.2 | 9.43 | **no** | `b200_sxm-x195-nvl72-hybrid` | 478.5 | 1,235.4-2,293.1 | 1.64 | yes | 1.978x | 0.345x | 0.174x |
| Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | 1,533.1 | 884.0-1,640.8 | 7.35 | yes | `b200_sxm-x520-nvl72-hybrid` | 472.0 | 1,122.7-2,083.9 | 1.78 | yes | 3.248x | 0.787x | 0.242x |
| Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,293.4 | 1,562.2-2,899.6 | 3.51 | yes | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | 837.0-1,553.6 | 2.29 | yes | 2.856x | 1.866x | 0.653x |
| Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,293.4 | 1,562.2-2,899.6 | 3.51 | yes | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | 837.0-1,553.6 | 2.29 | yes | 2.856x | 1.866x | 0.653x |
| Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,293.4 | 1,562.2-2,899.6 | 3.51 | yes | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | 837.0-1,553.6 | 2.29 | yes | 2.856x | 1.866x | 0.653x |
| Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,293.4 | 1,562.2-2,899.6 | 3.51 | yes | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | 837.0-1,553.6 | 2.29 | yes | 2.856x | 1.866x | 0.653x |
| Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,207.7 | 1,095.2-2,032.8 | 4.68 | yes | `b200_sxm-x1965-nvl72-hybrid` | 447.0 | 768.1-1,425.8 | 2.47 | yes | 2.702x | 1.426x | 0.528x |
| Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,143.4 | 686.3-1,273.9 | 7.06 | yes | `b200_sxm-x1965-nvl72-hybrid` | 405.2 | 463.2-859.7 | 3.71 | yes | 2.822x | 1.482x | 0.525x |
| Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 518.2 | 213.6-396.6 | 10.28 | **no** | `b200_sxm-x1965-nvl72-hybrid` | 272.8 | 193.6-359.4 | 5.97 | yes | 1.899x | 1.103x | 0.581x |
| Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 151.9 | 54.6-101.4 | 11.79 | **no** | `b200_sxm-x1965-nvl72-hybrid` | 145.3 | 71.2-132.2 | 8.64 | **no** | 1.045x | 0.767x | 0.733x |
| Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x68` | 39.3 | 13.7-25.4 | 12.19 | **no** | `b200_sxm-x1965-nvl72-hybrid` | 49.4 | 23.0-42.7 | 9.10 | **no** | 0.795x | 0.594x | 0.747x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.174x to 0.747x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 11 ROM rows and 9 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-kimi-k3-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 722.5 | 580.5-1,077.5 | 5.28 | yes | `a100_sxm_80gb-x394-hybrid` | 126.0 | 155.4-288.4 | 3.44 | yes | 5.736x | 3.736x | 0.651x |
| Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x23` | 1,333.7 | 638.6-1,185.3 | 8.85 | **no** | `a100_sxm_80gb-x1287-hybrid` | 125.9 | 149.5-277.5 | 3.57 | yes | 10.594x | 4.271x | 0.403x |
| Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 1,084.9 | 1,264.5-2,347.0 | 3.64 | yes | `a100_sxm_80gb-x5316-hybrid` | 117.7 | 115.8-215.0 | 4.31 | yes | 9.217x | 10.918x | 1.185x |
| Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 1,084.9 | 1,264.5-2,347.0 | 3.64 | yes | `a100_sxm_80gb-x5316-hybrid` | 117.7 | 115.8-215.0 | 4.31 | yes | 9.217x | 10.918x | 1.185x |
| Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 1,084.9 | 1,264.5-2,347.0 | 3.64 | yes | `a100_sxm_80gb-x5316-hybrid` | 117.7 | 115.8-215.0 | 4.31 | yes | 9.217x | 10.918x | 1.185x |
| Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 1,084.9 | 1,264.5-2,347.0 | 3.64 | yes | `a100_sxm_80gb-x5316-hybrid` | 117.7 | 115.8-215.0 | 4.31 | yes | 9.217x | 10.918x | 1.185x |
| Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 956.7 | 1,066.6-1,979.8 | 3.80 | yes | `a100_sxm_80gb-x5316-hybrid` | 117.7 | 115.8-215.0 | 4.31 | yes | 8.127x | 9.210x | 1.133x |
| Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 750.1 | 694.7-1,289.5 | 4.58 | yes | `a100_sxm_80gb-x5316-hybrid` | 117.7 | 115.8-215.0 | 4.31 | yes | 6.373x | 5.998x | 0.941x |
| Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 313.0 | 229.5-425.9 | 5.78 | yes | `a100_sxm_80gb-x5316-hybrid` | 91.5 | 64.0-118.7 | 6.07 | yes | 3.420x | 3.587x | 1.049x |
| Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 87.5 | 60.5-112.3 | 6.14 | yes | `a100_sxm_80gb-x5316-hybrid` | 59.8 | 31.9-59.2 | 7.94 | **no** | 1.465x | 1.895x | 1.294x |
| Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 22.4 | 15.2-28.2 | 6.25 | yes | `a100_sxm_80gb-x5316-hybrid` | 29.9 | 8.2-15.2 | 15.54 | **no** | 0.748x | 1.859x | 2.486x |

**Does the ratio compress?** Of 11 class rows in this study, 3 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.403x to 2.486x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 10 of 11 ROM rows and 9 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-kimi-k3-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,928.0 | 967.3-1,795.5 | 8.45 | **no** | `b200_sxm-x201-nvl72-hybrid` | 488.3 | 1,331.6-2,471.6 | 1.55 | yes | 3.949x | 0.726x | 0.184x |
| Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,162.9 | 1,383.8-2,568.4 | 6.63 | yes | `b200_sxm-x202-nvl72-hybrid` | 488.6 | 1,333.8-2,475.6 | 1.55 | yes | 4.426x | 1.037x | 0.234x |
| Kimi-K3 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,928.0 | 967.3-1,795.5 | 8.45 | **no** | `b200_sxm-x201-nvl72-hybrid` | 488.3 | 1,331.6-2,471.6 | 1.55 | yes | 3.949x | 0.726x | 0.184x |
| Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,162.9 | 1,383.8-2,568.4 | 6.63 | yes | `b200_sxm-x202-nvl72-hybrid` | 488.6 | 1,333.8-2,475.6 | 1.55 | yes | 4.426x | 1.037x | 0.234x |
| Kimi-K3 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,928.0 | 967.3-1,795.5 | 8.45 | **no** | `b200_sxm-x201-nvl72-hybrid` | 481.9 | 1,249.8-2,319.8 | 1.63 | yes | 4.001x | 0.774x | 0.193x |
| Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,162.9 | 1,383.8-2,568.4 | 6.63 | yes | `b200_sxm-x202-nvl72-hybrid` | 482.2 | 1,251.9-2,323.6 | 1.63 | yes | 4.485x | 1.105x | 0.246x |
| Kimi-K3 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,928.0 | 967.3-1,795.5 | 8.45 | **no** | `b200_sxm-x201-nvl72-hybrid` | 458.1 | 999.0-1,854.3 | 1.94 | yes | 4.209x | 0.968x | 0.230x |
| Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,162.9 | 1,383.8-2,568.4 | 6.63 | yes | `b200_sxm-x202-nvl72-hybrid` | 458.5 | 1,000.9-1,857.8 | 1.94 | yes | 4.717x | 1.383x | 0.293x |
| Kimi-K3 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,928.0 | 967.3-1,795.5 | 8.45 | **no** | `b200_sxm-x201-nvl72-hybrid` | 417.8 | 734.7-1,363.7 | 2.41 | yes | 4.614x | 1.317x | 0.285x |
| Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,162.9 | 1,383.8-2,568.4 | 6.63 | yes | `b200_sxm-x202-nvl72-hybrid` | 418.3 | 736.0-1,366.1 | 2.41 | yes | 5.171x | 1.880x | 0.364x |
| Kimi-K3 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,731.2 | 608.1-1,128.8 | 12.07 | **no** | `b200_sxm-x201-nvl72-hybrid` | 357.9 | 500.2-928.4 | 3.03 | yes | 4.837x | 1.216x | 0.251x |
| Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,152.4 | 1,400.2-2,598.9 | 6.52 | yes | `b200_sxm-x347-nvl72-hybrid` | 399.0 | 606.9-1,126.5 | 2.79 | yes | 5.394x | 2.307x | 0.428x |
| Kimi-K3 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,499.1 | 510.6-947.8 | 12.45 | **no** | `b200_sxm-x201-nvl72-hybrid` | 283.7 | 315.4-585.5 | 3.81 | yes | 5.283x | 1.619x | 0.306x |
| Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,873.9 | 847.0-1,572.1 | 9.38 | **no** | `b200_sxm-x347-nvl72-hybrid` | 331.7 | 386.4-717.2 | 3.64 | yes | 5.649x | 2.192x | 0.388x |
| Kimi-K3 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 719.1 | 155.9-289.4 | 19.56 | **no** | `b200_sxm-x201-nvl72-hybrid` | 150.9 | 102.0-189.3 | 6.27 | yes | 4.766x | 1.529x | 0.321x |
| Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,089.9 | 350.0-649.6 | 13.20 | **no** | `b200_sxm-x347-nvl72-hybrid` | 182.1 | 127.1-236.0 | 6.07 | yes | 5.984x | 2.753x | 0.460x |
| Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 219.5 | 47.8-88.6 | 19.49 | **no** | `b200_sxm-x201-nvl72-hybrid` | 72.7 | 26.9-50.0 | 11.45 | **no** | 3.020x | 1.774x | 0.587x |
| Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 369.4 | 95.8-177.8 | 16.35 | **no** | `b200_sxm-x347-nvl72-hybrid` | 87.1 | 60.2-111.8 | 6.13 | yes | 4.242x | 1.590x | 0.375x |
| Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 57.8 | 13.9-25.7 | 17.66 | **no** | `b200_sxm-x201-nvl72-hybrid` | 35.1 | 19.1-35.5 | 7.77 | yes | 1.647x | 0.725x | 0.440x |
| Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 99.2 | 39.7-73.8 | 10.58 | **no** | `b200_sxm-x347-nvl72-hybrid` | 41.9 | 15.7-29.1 | 11.36 | **no** | 2.366x | 2.539x | 1.073x |

**Does the ratio compress?** Of 20 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.184x to 1.073x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 6 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-kimi-k3-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,383.5 | 687.8-1,276.7 | 8.53 | **no** | `a100_sxm_80gb-x394-hybrid` | 128.3 | 198.6-368.5 | 2.74 | yes | 10.780x | 3.464x | 0.321x |
| Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,860.2 | 1,996.7-3,706.1 | 3.95 | yes | `a100_sxm_80gb-x672-hybrid` | 129.6 | 198.6-368.5 | 2.77 | yes | 14.356x | 10.056x | 0.700x |
| Kimi-K3 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,383.5 | 687.8-1,276.7 | 8.53 | **no** | `a100_sxm_80gb-x394-hybrid` | 128.3 | 198.6-368.5 | 2.74 | yes | 10.780x | 3.464x | 0.321x |
| Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,860.2 | 1,996.7-3,706.1 | 3.95 | yes | `a100_sxm_80gb-x672-hybrid` | 129.6 | 198.6-368.5 | 2.77 | yes | 14.356x | 10.056x | 0.700x |
| Kimi-K3 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,383.5 | 687.8-1,276.7 | 8.53 | **no** | `a100_sxm_80gb-x394-hybrid` | 128.3 | 198.6-368.5 | 2.74 | yes | 10.780x | 3.464x | 0.321x |
| Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,860.2 | 1,996.7-3,706.1 | 3.95 | yes | `a100_sxm_80gb-x672-hybrid` | 129.6 | 198.6-368.5 | 2.77 | yes | 14.356x | 10.056x | 0.700x |
| Kimi-K3 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,383.5 | 687.8-1,276.7 | 8.53 | **no** | `a100_sxm_80gb-x394-hybrid` | 126.3 | 183.7-340.9 | 2.92 | yes | 10.956x | 3.745x | 0.342x |
| Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,860.2 | 1,996.7-3,706.1 | 3.95 | yes | `a100_sxm_80gb-x672-hybrid` | 129.6 | 198.6-368.5 | 2.77 | yes | 14.356x | 10.056x | 0.700x |
| Kimi-K3 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,251.6 | 461.2-856.1 | 11.51 | **no** | `a100_sxm_80gb-x394-hybrid` | 111.9 | 116.1-215.5 | 4.09 | yes | 11.183x | 3.973x | 0.355x |
| Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,855.7 | 1,479.1-2,745.4 | 5.32 | yes | `a100_sxm_80gb-x672-hybrid` | 123.1 | 157.1-291.5 | 3.32 | yes | 15.080x | 9.417x | 0.625x |
| Kimi-K3 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,069.6 | 371.2-689.0 | 12.22 | **no** | `a100_sxm_80gb-x394-hybrid` | 94.3 | 100.8-187.1 | 3.97 | yes | 11.340x | 3.682x | 0.325x |
| Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,648.8 | 956.2-1,774.8 | 7.31 | yes | `a100_sxm_80gb-x672-hybrid` | 106.1 | 95.1-176.5 | 4.73 | yes | 15.545x | 10.055x | 0.647x |
| Kimi-K3 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 742.9 | 211.2-391.9 | 14.92 | **no** | `a100_sxm_80gb-x394-hybrid` | 75.4 | 59.1-109.7 | 5.41 | yes | 9.850x | 3.572x | 0.363x |
| Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,327.9 | 737.2-1,368.4 | 7.64 | yes | `a100_sxm_80gb-x672-hybrid` | 88.9 | 83.2-154.4 | 4.53 | yes | 14.931x | 8.862x | 0.594x |
| Kimi-K3 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 249.6 | 59.1-109.6 | 17.92 | **no** | `a100_sxm_80gb-x394-hybrid` | 43.6 | 45.4-84.3 | 4.07 | yes | 5.724x | 1.300x | 0.227x |
| Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554.8 | 220.0-408.4 | 10.69 | **no** | `a100_sxm_80gb-x672-hybrid` | 53.0 | 55.4-102.7 | 4.06 | yes | 10.460x | 3.975x | 0.380x |
| Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 66.6 | 15.9-29.5 | 17.77 | **no** | `a100_sxm_80gb-x394-hybrid` | 18.5 | 17.6-32.6 | 4.47 | yes | 3.597x | 0.905x | 0.252x |
| Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 159.4 | 56.1-104.1 | 12.04 | **no** | `a100_sxm_80gb-x672-hybrid` | 24.6 | 19.7-36.7 | 5.27 | yes | 6.490x | 2.841x | 0.438x |
| Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 16.8 | 4.1-7.7 | 17.20 | **no** | `a100_sxm_80gb-x394-hybrid` | 7.5 | 4.8-8.8 | 6.69 | yes | 2.231x | 0.868x | 0.389x |
| Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 40.9 | 19.0-35.2 | 9.14 | **no** | `a100_sxm_80gb-x672-hybrid` | 9.3 | 11.7-21.7 | 3.35 | yes | 4.415x | 1.621x | 0.367x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.227x to 0.700x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | 5,396.1 | 3,355.0-6,227.3 | 6.82 | yes | `b200_sxm-x23-nvl72-tensor` | 1,267.3 | 3,454.4-6,411.8 | 1.56 | yes | 4.258x | 0.971x | 0.228x |
| MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 5,503.2 | 7,700.0-14,292.3 | 3.03 | yes | `b200_sxm-x29-nvl72-tensor` | 1,307.1 | 3,755.6-6,970.8 | 1.48 | yes | 4.210x | 2.050x | 0.487x |
| MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,797.9 | 3,590.1-6,663.7 | 5.67 | yes | `b200_sxm-x192-nvl72-hybrid` | 1,386.6 | 4,563.7-8,470.9 | 1.29 | yes | 3.460x | 0.787x | 0.227x |
| MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,663.1 | 5,289.1-9,817.3 | 2.94 | yes | `b200_sxm-x636-nvl72-hybrid` | 1,369.1 | 4,545.9-8,437.9 | 1.28 | yes | 2.676x | 1.163x | 0.435x |
| MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,797.9 | 3,590.1-6,663.7 | 5.67 | yes | `b200_sxm-x192-nvl72-hybrid` | 1,369.6 | 4,370.1-8,111.4 | 1.33 | yes | 3.503x | 0.822x | 0.235x |
| MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,663.1 | 5,289.1-9,817.3 | 2.94 | yes | `b200_sxm-x636-nvl72-hybrid` | 1,369.1 | 4,545.9-8,437.9 | 1.28 | yes | 2.676x | 1.163x | 0.435x |
| MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,797.9 | 3,590.1-6,663.7 | 5.67 | yes | `b200_sxm-x192-nvl72-hybrid` | 1,306.3 | 3,805.7-7,063.8 | 1.46 | yes | 3.673x | 0.943x | 0.257x |
| MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,496.8 | 4,283.5-7,950.7 | 3.46 | yes | `b200_sxm-x636-nvl72-hybrid` | 1,369.1 | 4,545.9-8,437.9 | 1.28 | yes | 2.554x | 0.942x | 0.369x |
| MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x282` | 4,634.9 | 2,893.9-5,371.4 | 6.79 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,141.4 | 2,674.1-4,963.6 | 1.81 | yes | 4.061x | 1.082x | 0.267x |
| MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,364.9 | 3,052.7-5,666.2 | 4.67 | yes | `b200_sxm-x636-nvl72-hybrid` | 1,332.7 | 4,088.5-7,588.7 | 1.38 | yes | 2.525x | 0.747x | 0.296x |
| MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,038.8 | 2,219.9-4,120.5 | 7.71 | yes | `b200_sxm-x192-nvl72-hybrid` | 1,035.8 | 2,251.4-4,178.9 | 1.95 | yes | 3.899x | 0.986x | 0.253x |
| MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 2,771.2 | 2,712.1-5,034.1 | 4.33 | yes | `b200_sxm-x636-nvl72-hybrid` | 1,257.7 | 3,396.8-6,304.9 | 1.57 | yes | 2.203x | 0.798x | 0.362x |
| MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 2,943.2 | 1,336.5-2,480.7 | 9.34 | **no** | `b200_sxm-x192-nvl72-hybrid` | 830.0 | 1,498.0-2,780.5 | 2.35 | yes | 3.546x | 0.892x | 0.252x |
| MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 1,859.8 | 1,767.6-3,280.9 | 4.46 | yes | `b200_sxm-x636-nvl72-hybrid` | 1,134.2 | 2,586.3-4,800.6 | 1.86 | yes | 1.640x | 0.683x | 0.417x |
| MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 951.4 | 490.5-910.5 | 8.22 | **no** | `b200_sxm-x192-nvl72-hybrid` | 428.1 | 489.0-907.7 | 3.71 | yes | 2.222x | 1.003x | 0.451x |
| MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 600.3 | 540.7-1,003.6 | 4.71 | yes | `b200_sxm-x636-nvl72-hybrid` | 747.3 | 1,084.4-2,012.8 | 2.92 | yes | 0.803x | 0.499x | 0.621x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 238.5 | 134.7-250.0 | 7.51 | yes | `b200_sxm-x192-nvl72-hybrid` | 168.1 | 210.8-391.2 | 3.38 | yes | 1.419x | 0.639x | 0.450x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 159.0 | 138.9-257.9 | 4.85 | yes | `b200_sxm-x636-nvl72-hybrid` | 364.5 | 339.5-630.1 | 4.55 | yes | 0.436x | 0.409x | 0.938x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 59.7 | 34.0-63.1 | 7.45 | yes | `b200_sxm-x192-nvl72-hybrid` | 53.1 | 79.2-146.9 | 2.84 | yes | 1.125x | 0.429x | 0.382x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x22` | 40.2 | 57.8-107.3 | 2.95 | yes | `b200_sxm-x636-nvl72-hybrid` | 139.9 | 147.6-274.0 | 4.02 | yes | 0.287x | 0.392x | 1.362x |

**Does the ratio compress?** Of 20 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.227x to 1.362x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 18 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x64` | 5,173.0 | 3,043.6-5,649.3 | 7.21 | yes | `a100_sxm_80gb-x63-hybrid` | 416.3 | 758.4-1,407.7 | 2.33 | yes | 12.427x | 4.013x | 0.323x |
| MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 5,440.2 | 6,621.5-12,290.4 | 3.48 | yes | `a100_sxm_80gb-x56-hybrid` | 420.3 | 758.7-1,408.3 | 2.35 | yes | 12.943x | 8.727x | 0.674x |
| MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3,903.2 | 4,263.9-7,914.4 | 3.88 | yes | `a100_sxm_80gb-x391-hybrid` | 409.4 | 804.1-1,492.4 | 2.16 | yes | 9.534x | 5.303x | 0.556x |
| MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3,134.8 | 4,603.9-8,545.5 | 2.89 | yes | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 794.0-1,473.7 | 2.16 | yes | 7.754x | 5.799x | 0.748x |
| MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3,903.2 | 4,263.9-7,914.4 | 3.88 | yes | `a100_sxm_80gb-x391-hybrid` | 409.4 | 804.1-1,492.4 | 2.16 | yes | 9.534x | 5.303x | 0.556x |
| MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3,134.8 | 4,603.9-8,545.5 | 2.89 | yes | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 794.0-1,473.7 | 2.16 | yes | 7.754x | 5.799x | 0.748x |
| MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x287` | 3,860.3 | 3,814.9-7,080.9 | 4.29 | yes | `a100_sxm_80gb-x283-hybrid` | 404.7 | 851.1-1,579.8 | 2.02 | yes | 9.538x | 4.482x | 0.470x |
| MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3,134.8 | 4,603.9-8,545.5 | 2.89 | yes | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 794.0-1,473.7 | 2.16 | yes | 7.754x | 5.799x | 0.748x |
| MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3,415.0 | 3,027.1-5,618.7 | 4.78 | yes | `a100_sxm_80gb-x391-hybrid` | 403.4 | 873.6-1,621.5 | 1.96 | yes | 8.466x | 3.465x | 0.409x |
| MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2,577.1 | 3,332.2-6,185.1 | 3.28 | yes | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 794.0-1,473.7 | 2.16 | yes | 6.375x | 4.197x | 0.658x |
| MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 2,658.9 | 2,109.3-3,915.1 | 5.34 | yes | `a100_sxm_80gb-x391-hybrid` | 403.4 | 873.6-1,621.5 | 1.96 | yes | 6.592x | 2.414x | 0.366x |
| MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,983.5 | 2,194.9-4,074.1 | 3.83 | yes | `a100_sxm_80gb-x1735-hybrid` | 403.8 | 929.9-1,726.0 | 1.84 | yes | 4.912x | 2.360x | 0.480x |
| MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,676.6 | 1,248.3-2,317.0 | 5.69 | yes | `a100_sxm_80gb-x391-hybrid` | 369.2 | 768.4-1,426.2 | 2.04 | yes | 4.541x | 1.625x | 0.358x |
| MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,213.9 | 1,345.2-2,496.9 | 3.83 | yes | `a100_sxm_80gb-x1735-hybrid` | 403.8 | 929.9-1,726.0 | 1.84 | yes | 3.006x | 1.447x | 0.481x |
| MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 503.9 | 343.3-637.2 | 6.22 | yes | `a100_sxm_80gb-x391-hybrid` | 180.1 | 367.3-681.8 | 2.08 | yes | 2.798x | 0.935x | 0.334x |
| MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 356.1 | 372.2-690.8 | 4.06 | yes | `a100_sxm_80gb-x1735-hybrid` | 383.0 | 833.4-1,546.9 | 1.95 | yes | 0.930x | 0.447x | 0.480x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 131.0 | 126.4-234.6 | 4.40 | yes | `a100_sxm_80gb-x391-hybrid` | 64.5 | 101.5-188.4 | 2.69 | yes | 2.032x | 1.245x | 0.613x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 92.0 | 94.3-175.0 | 4.14 | yes | `a100_sxm_80gb-x1735-hybrid` | 192.8 | 401.2-744.6 | 2.04 | yes | 0.477x | 0.235x | 0.493x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 33.0 | 48.2-89.4 | 2.91 | yes | `a100_sxm_80gb-x391-hybrid` | 22.5 | 26.0-48.2 | 3.67 | yes | 1.471x | 1.856x | 1.261x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x31` | 23.1 | 38.1-70.7 | 2.58 | yes | `a100_sxm_80gb-x1735-hybrid` | 69.9 | 112.2-208.2 | 2.64 | yes | 0.331x | 0.339x | 1.025x |

**Does the ratio compress?** Of 20 class rows in this study, 18 move the ROM-versus-GPU ratio DOWN under speculation and 2 move it UP. The movement spans 0.323x to 1.261x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 20 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 4,359.9 | 2,795.3-5,188.5 | 6.61 | yes | `b200_sxm-x53-nvl72-tensor` | 1,286.9 | 4,150.8-7,704.4 | 1.31 | yes | 3.388x | 0.673x | 0.199x |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 5,253.1 | 4,125.7-7,657.8 | 5.40 | yes | `b200_sxm-x58-nvl72-tensor` | 1,301.9 | 4,235.8-7,862.3 | 1.30 | yes | 4.035x | 0.974x | 0.241x |
| MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,458.8 | 2,420.5-4,492.7 | 4.31 | yes | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 3,699.9-6,867.4 | 1.35 | yes | 2.081x | 0.654x | 0.314x |
| MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,458.8 | 2,420.5-4,492.7 | 4.31 | yes | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 3,699.9-6,867.4 | 1.35 | yes | 2.081x | 0.654x | 0.314x |
| MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,458.8 | 2,420.5-4,492.7 | 4.31 | yes | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 3,699.9-6,867.4 | 1.35 | yes | 2.081x | 0.654x | 0.314x |
| MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,458.8 | 2,420.5-4,492.7 | 4.31 | yes | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 3,699.9-6,867.4 | 1.35 | yes | 2.081x | 0.654x | 0.314x |
| MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,302.8 | 2,327.8-4,320.7 | 4.19 | yes | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 3,699.9-6,867.4 | 1.35 | yes | 1.949x | 0.629x | 0.323x |
| MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,626.6 | 1,421.3-2,638.0 | 4.85 | yes | `b200_sxm-x3149-nvl72-hybrid` | 1,138.1 | 3,335.2-6,190.5 | 1.45 | yes | 1.429x | 0.426x | 0.298x |
| MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 586.9 | 455.7-845.8 | 5.46 | yes | `b200_sxm-x3149-nvl72-hybrid` | 866.4 | 2,503.3-4,646.4 | 1.47 | yes | 0.677x | 0.182x | 0.269x |
| MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 157.8 | 116.8-216.7 | 5.73 | yes | `b200_sxm-x3149-nvl72-hybrid` | 447.8 | 1,073.5-1,992.6 | 1.77 | yes | 0.352x | 0.109x | 0.309x |
| MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 40.0 | 29.3-54.4 | 5.79 | yes | `b200_sxm-x3149-nvl72-hybrid` | 158.9 | 295.0-547.5 | 2.28 | yes | 0.252x | 0.099x | 0.395x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.199x to 0.395x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | 4,193.4 | 2,408.8-4,471.1 | 7.38 | yes | `a100_sxm_80gb-x139-tensor` | 416.1 | 803.5-1,491.3 | 2.20 | yes | 10.078x | 2.998x | 0.297x |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 5,049.5 | 4,615.2-8,566.4 | 4.64 | yes | `a100_sxm_80gb-x112-tensor` | 410.0 | 796.9-1,479.2 | 2.18 | yes | 12.315x | 5.791x | 0.470x |
| MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 1,661.2 | 3,226.6-5,988.9 | 2.18 | yes | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 718.2-1,333.1 | 2.19 | yes | 4.469x | 4.492x | 1.005x |
| MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,535.4 | 1,772.4-3,289.8 | 3.67 | yes | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 718.2-1,333.1 | 2.19 | yes | 4.131x | 2.468x | 0.597x |
| MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,535.4 | 1,772.4-3,289.8 | 3.67 | yes | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 718.2-1,333.1 | 2.19 | yes | 4.131x | 2.468x | 0.597x |
| MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,535.4 | 1,772.4-3,289.8 | 3.67 | yes | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 718.2-1,333.1 | 2.19 | yes | 4.131x | 2.468x | 0.597x |
| MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,535.4 | 1,772.4-3,289.8 | 3.67 | yes | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 718.2-1,333.1 | 2.19 | yes | 4.131x | 2.468x | 0.597x |
| MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,085.8 | 1,504.8-2,793.1 | 3.06 | yes | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 718.2-1,333.1 | 2.19 | yes | 2.921x | 2.095x | 0.717x |
| MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 346.8 | 473.5-878.9 | 3.11 | yes | `a100_sxm_80gb-x8562-hybrid` | 331.9 | 669.1-1,242.0 | 2.10 | yes | 1.045x | 0.708x | 0.677x |
| MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 90.9 | 132.0-245.1 | 2.92 | yes | `a100_sxm_80gb-x8562-hybrid` | 258.2 | 559.1-1,037.8 | 1.96 | yes | 0.352x | 0.236x | 0.670x |
| MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 22.9 | 33.2-61.7 | 2.93 | yes | `a100_sxm_80gb-x8562-hybrid` | 101.1 | 171.5-318.3 | 2.50 | yes | 0.227x | 0.194x | 0.854x |

**Does the ratio compress?** Of 11 class rows in this study, 10 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.297x to 1.005x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,140.0 | 5,125.5-9,513.6 | 5.91 | yes | `b200_sxm-x61-nvl72-tensor` | 1,417.2 | 4,546.7-8,439.2 | 1.32 | yes | 5.038x | 1.127x | 0.224x |
| MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,526.2 | 5,632.3-10,454.2 | 4.91 | yes | `b200_sxm-x58-nvl72-tensor` | 1,413.8 | 4,509.8-8,370.7 | 1.33 | yes | 4.616x | 1.249x | 0.271x |
| MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,140.0 | 5,125.5-9,513.6 | 5.91 | yes | `b200_sxm-x61-nvl72-tensor` | 1,385.1 | 4,082.6-7,577.9 | 1.44 | yes | 5.155x | 1.255x | 0.244x |
| MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,526.2 | 5,632.3-10,454.2 | 4.91 | yes | `b200_sxm-x58-nvl72-tensor` | 1,380.6 | 4,042.3-7,503.0 | 1.45 | yes | 4.727x | 1.393x | 0.295x |
| MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,140.0 | 5,125.5-9,513.6 | 5.91 | yes | `b200_sxm-x61-nvl72-tensor` | 1,327.0 | 3,448.2-6,400.2 | 1.63 | yes | 5.380x | 1.486x | 0.276x |
| MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,526.2 | 5,632.3-10,454.2 | 4.91 | yes | `b200_sxm-x58-nvl72-tensor` | 1,320.7 | 3,409.9-6,329.2 | 1.64 | yes | 4.941x | 1.652x | 0.334x |
| MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,140.0 | 5,125.5-9,513.6 | 5.91 | yes | `b200_sxm-x61-nvl72-tensor` | 1,230.9 | 2,733.2-5,073.2 | 1.91 | yes | 5.801x | 1.875x | 0.323x |
| MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,526.2 | 5,632.3-10,454.2 | 4.91 | yes | `b200_sxm-x58-nvl72-tensor` | 1,222.0 | 2,704.1-5,019.1 | 1.92 | yes | 5.341x | 2.083x | 0.390x |
| MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 7,074.1 | 5,007.5-9,294.6 | 5.99 | yes | `b200_sxm-x87-nvl72-hybrid` | 1,157.3 | 2,530.7-4,697.4 | 1.94 | yes | 6.113x | 1.979x | 0.324x |
| MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 6,388.4 | 6,839.2-12,694.4 | 3.96 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,271.3 | 3,133.1-5,815.4 | 1.72 | yes | 5.025x | 2.183x | 0.434x |
| MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,967.4 | 5,015.7-9,309.9 | 5.89 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,153.9 | 2,354.3-4,370.0 | 2.08 | yes | 6.038x | 2.130x | 0.353x |
| MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6,305.2 | 6,854.9-12,723.7 | 3.90 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,262.4 | 2,966.5-5,506.3 | 1.80 | yes | 4.994x | 2.311x | 0.463x |
| MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,929.3 | 3,213.7-5,965.1 | 9.14 | **no** | `b200_sxm-x173-nvl72-hybrid` | 998.3 | 1,605.9-2,980.8 | 2.64 | yes | 6.941x | 2.001x | 0.288x |
| MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6,075.1 | 5,185.7-9,625.4 | 4.97 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,142.3 | 2,129.2-3,952.0 | 2.27 | yes | 5.318x | 2.436x | 0.458x |
| MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,651.0 | 1,369.5-2,542.0 | 14.40 | **no** | `b200_sxm-x173-nvl72-hybrid` | 678.9 | 575.4-1,068.1 | 5.00 | yes | 6.851x | 2.380x | 0.347x |
| MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,129.5 | 2,647.2-4,913.5 | 6.61 | yes | `b200_sxm-x347-nvl72-hybrid` | 818.9 | 828.4-1,537.6 | 4.19 | yes | 5.043x | 3.196x | 0.634x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,847.6 | 434.1-805.7 | 18.05 | **no** | `b200_sxm-x173-nvl72-hybrid` | 413.1 | 295.7-548.9 | 5.92 | yes | 4.472x | 1.468x | 0.328x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,614.2 | 807.6-1,499.0 | 8.47 | **no** | `b200_sxm-x347-nvl72-hybrid` | 509.4 | 277.4-514.9 | 7.79 | yes | 3.169x | 2.911x | 0.919x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 527.4 | 129.2-239.8 | 17.31 | **no** | `b200_sxm-x173-nvl72-hybrid` | 221.7 | 130.2-241.8 | 7.22 | yes | 2.379x | 0.992x | 0.417x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 452.3 | 280.4-520.4 | 6.84 | yes | `b200_sxm-x347-nvl72-hybrid` | 285.3 | 125.8-233.6 | 9.61 | **no** | 1.585x | 2.228x | 1.405x |

**Does the ratio compress?** Of 20 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.224x to 1.405x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 15 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,845.8 | 4,096.8-7,604.3 | 7.09 | yes | `a100_sxm_80gb-x77-hybrid` | 478.5 | 810.6-1,504.5 | 2.50 | yes | 14.306x | 5.054x | 0.353x |
| MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,680.5 | 5,559.3-10,318.8 | 4.33 | yes | `a100_sxm_80gb-x224-hybrid` | 477.5 | 913.9-1,696.2 | 2.22 | yes | 11.896x | 6.083x | 0.511x |
| MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,845.8 | 4,096.8-7,604.3 | 7.09 | yes | `a100_sxm_80gb-x77-hybrid` | 478.5 | 810.6-1,504.5 | 2.50 | yes | 14.306x | 5.054x | 0.353x |
| MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,680.5 | 5,559.3-10,318.8 | 4.33 | yes | `a100_sxm_80gb-x224-hybrid` | 477.5 | 913.9-1,696.2 | 2.22 | yes | 11.896x | 6.083x | 0.511x |
| MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,845.8 | 4,096.8-7,604.3 | 7.09 | yes | `a100_sxm_80gb-x77-hybrid` | 478.5 | 810.6-1,504.5 | 2.50 | yes | 14.306x | 5.054x | 0.353x |
| MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,680.5 | 5,559.3-10,318.8 | 4.33 | yes | `a100_sxm_80gb-x224-hybrid` | 477.5 | 913.9-1,696.2 | 2.22 | yes | 11.896x | 6.083x | 0.511x |
| MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,845.8 | 4,096.8-7,604.3 | 7.09 | yes | `a100_sxm_80gb-x77-hybrid` | 478.5 | 810.6-1,504.5 | 2.50 | yes | 14.306x | 5.054x | 0.353x |
| MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,680.5 | 5,559.3-10,318.8 | 4.33 | yes | `a100_sxm_80gb-x224-hybrid` | 477.5 | 913.9-1,696.2 | 2.22 | yes | 11.896x | 6.083x | 0.511x |
| MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 6,790.9 | 4,079.0-7,571.2 | 7.06 | yes | `a100_sxm_80gb-x154-hybrid` | 473.2 | 866.4-1,608.1 | 2.32 | yes | 14.352x | 4.708x | 0.328x |
| MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,547.9 | 7,264.0-13,482.9 | 3.24 | yes | `a100_sxm_80gb-x672-hybrid` | 467.0 | 999.6-1,855.3 | 1.98 | yes | 11.880x | 7.267x | 0.612x |
| MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,679.9 | 4,074.3-7,562.4 | 6.95 | yes | `a100_sxm_80gb-x335-hybrid` | 469.5 | 930.6-1,727.3 | 2.14 | yes | 14.229x | 4.378x | 0.308x |
| MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,370.5 | 5,910.5-10,970.7 | 3.85 | yes | `a100_sxm_80gb-x672-hybrid` | 467.0 | 999.6-1,855.3 | 1.98 | yes | 11.500x | 5.913x | 0.514x |
| MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,338.1 | 2,448.7-4,545.2 | 10.97 | **no** | `a100_sxm_80gb-x335-hybrid` | 426.3 | 781.1-1,449.7 | 2.31 | yes | 14.867x | 3.135x | 0.211x |
| MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,465.8 | 4,157.5-7,716.9 | 4.55 | yes | `a100_sxm_80gb-x672-hybrid` | 467.0 | 999.6-1,855.3 | 1.98 | yes | 9.563x | 4.159x | 0.435x |
| MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,960.9 | 1,023.4-1,899.6 | 16.41 | **no** | `a100_sxm_80gb-x335-hybrid` | 244.1 | 429.2-796.7 | 2.41 | yes | 16.223x | 2.384x | 0.147x |
| MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,332.7 | 2,006.6-3,724.5 | 4.93 | yes | `a100_sxm_80gb-x672-hybrid` | 337.0 | 572.1-1,061.9 | 2.50 | yes | 6.922x | 3.507x | 0.507x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,434.4 | 321.5-596.8 | 18.92 | **no** | `a100_sxm_80gb-x335-hybrid` | 108.2 | 182.7-339.1 | 2.51 | yes | 13.255x | 1.760x | 0.133x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 723.5 | 587.9-1,091.2 | 5.22 | yes | `a100_sxm_80gb-x672-hybrid` | 163.2 | 293.2-544.3 | 2.36 | yes | 4.433x | 2.005x | 0.452x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 396.7 | 95.9-178.0 | 17.54 | **no** | `a100_sxm_80gb-x335-hybrid` | 58.2 | 47.7-88.5 | 5.18 | yes | 6.814x | 2.011x | 0.295x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 190.0 | 203.0-376.7 | 3.97 | yes | `a100_sxm_80gb-x672-hybrid` | 75.2 | 90.6-168.1 | 3.52 | yes | 2.528x | 2.241x | 0.887x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.133x to 0.887x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 16 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | 3,064.9 | 2,131.0-3,955.4 | 6.10 | yes | `b200_sxm-x71-nvl72-tensor` | 916.0 | 2,790.2-5,179.0 | 1.39 | yes | 3.346x | 0.764x | 0.228x |
| MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 3,548.1 | 3,337.7-6,195.2 | 4.51 | yes | `b200_sxm-x87-nvl72-hybrid` | 858.9 | 2,458.1-4,562.5 | 1.48 | yes | 4.131x | 1.358x | 0.329x |
| MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,345.5 | 3,116.4-5,784.4 | 3.19 | yes | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 2,775.2-5,151.1 | 1.34 | yes | 2.668x | 1.123x | 0.421x |
| MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,345.5 | 3,116.4-5,784.4 | 3.19 | yes | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 2,775.2-5,151.1 | 1.34 | yes | 2.668x | 1.123x | 0.421x |
| MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,345.5 | 3,116.4-5,784.4 | 3.19 | yes | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 2,775.2-5,151.1 | 1.34 | yes | 2.668x | 1.123x | 0.421x |
| MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,179.3 | 2,866.6-5,320.8 | 3.22 | yes | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 2,775.2-5,151.1 | 1.34 | yes | 2.479x | 1.033x | 0.417x |
| MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,903.5 | 2,130.4-3,954.3 | 3.79 | yes | `b200_sxm-x1416-nvl72-hybrid` | 852.9 | 2,467.7-4,580.4 | 1.47 | yes | 2.232x | 0.863x | 0.387x |
| MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,576.3 | 1,429.1-2,652.5 | 4.68 | yes | `b200_sxm-x1416-nvl72-hybrid` | 790.5 | 1,915.3-3,555.0 | 1.75 | yes | 1.994x | 0.746x | 0.374x |
| MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 575.6 | 487.1-904.1 | 5.01 | yes | `b200_sxm-x1416-nvl72-hybrid` | 556.6 | 882.7-1,638.4 | 2.67 | yes | 1.034x | 0.552x | 0.534x |
| MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 158.2 | 127.5-236.7 | 5.26 | yes | `b200_sxm-x1416-nvl72-hybrid` | 276.2 | 286.0-530.9 | 4.09 | yes | 0.573x | 0.446x | 0.779x |
| MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x49` | 40.3 | 32.1-59.6 | 5.32 | yes | `b200_sxm-x1416-nvl72-hybrid` | 108.7 | 132.4-245.8 | 3.48 | yes | 0.371x | 0.242x | 0.654x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.228x to 0.779x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | 2,984.6 | 1,859.5-3,451.6 | 6.81 | yes | `a100_sxm_80gb-x178-tensor` | 281.6 | 453.1-841.0 | 2.64 | yes | 10.600x | 4.104x | 0.387x |
| MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 3,483.3 | 3,355.9-6,229.0 | 4.40 | yes | `a100_sxm_80gb-x168-tensor` | 280.9 | 452.6-840.0 | 2.63 | yes | 12.402x | 7.415x | 0.598x |
| MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,895.0 | 2,640.0-4,900.2 | 3.04 | yes | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 424.2-787.4 | 2.51 | yes | 7.550x | 6.223x | 0.824x |
| MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,895.0 | 2,640.0-4,900.2 | 3.04 | yes | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 424.2-787.4 | 2.51 | yes | 7.550x | 6.223x | 0.824x |
| MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,895.0 | 2,640.0-4,900.2 | 3.04 | yes | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 424.2-787.4 | 2.51 | yes | 7.550x | 6.223x | 0.824x |
| MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,895.0 | 2,640.0-4,900.2 | 3.04 | yes | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 424.2-787.4 | 2.51 | yes | 7.550x | 6.223x | 0.824x |
| MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,455.4 | 1,791.3-3,324.9 | 3.44 | yes | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 424.2-787.4 | 2.51 | yes | 5.799x | 4.223x | 0.728x |
| MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,032.2 | 1,097.5-2,037.1 | 3.99 | yes | `a100_sxm_80gb-x3805-hybrid` | 248.8 | 407.4-756.2 | 2.59 | yes | 4.148x | 2.694x | 0.649x |
| MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 342.9 | 342.9-636.5 | 4.24 | yes | `a100_sxm_80gb-x3805-hybrid` | 191.3 | 247.9-460.1 | 3.27 | yes | 1.793x | 1.383x | 0.772x |
| MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 90.5 | 87.7-162.8 | 4.37 | yes | `a100_sxm_80gb-x3805-hybrid` | 135.5 | 226.6-420.6 | 2.54 | yes | 0.668x | 0.387x | 0.580x |
| MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x68` | 22.9 | 22.0-40.9 | 4.40 | yes | `a100_sxm_80gb-x3805-hybrid` | 56.7 | 105.2-195.3 | 2.28 | yes | 0.403x | 0.209x | 0.519x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.387x to 0.824x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | 2,556.9 | 2,014.8-3,739.8 | 5.38 | yes | `b200_sxm-x170-nvl72-hybrid` | 808.3 | 2,522.1-4,681.4 | 1.36 | yes | 3.163x | 0.799x | 0.253x |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 3,359.6 | 2,871.2-5,329.4 | 4.96 | yes | `b200_sxm-x116-nvl72-hybrid` | 813.5 | 2,515.4-4,669.0 | 1.37 | yes | 4.130x | 1.141x | 0.276x |
| MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,385.2 | 1,236.3-2,294.7 | 4.75 | yes | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 2,220.2-4,120.9 | 1.43 | yes | 1.855x | 0.557x | 0.300x |
| MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,385.2 | 1,236.3-2,294.7 | 4.75 | yes | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 2,220.2-4,120.9 | 1.43 | yes | 1.855x | 0.557x | 0.300x |
| MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,385.2 | 1,236.3-2,294.7 | 4.75 | yes | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 2,220.2-4,120.9 | 1.43 | yes | 1.855x | 0.557x | 0.300x |
| MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,385.2 | 1,236.3-2,294.7 | 4.75 | yes | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 2,220.2-4,120.9 | 1.43 | yes | 1.855x | 0.557x | 0.300x |
| MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,385.2 | 1,236.3-2,294.7 | 4.75 | yes | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 2,220.2-4,120.9 | 1.43 | yes | 1.855x | 0.557x | 0.300x |
| MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,342.8 | 1,221.6-2,267.5 | 4.66 | yes | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 2,220.2-4,120.9 | 1.43 | yes | 1.798x | 0.550x | 0.306x |
| MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 554.4 | 377.0-699.8 | 6.24 | yes | `b200_sxm-x6992-nvl72-hybrid` | 627.0 | 1,454.5-2,699.7 | 1.83 | yes | 0.884x | 0.259x | 0.293x |
| MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 155.8 | 107.1-198.7 | 6.17 | yes | `b200_sxm-x6992-nvl72-hybrid` | 370.2 | 911.6-1,692.0 | 1.72 | yes | 0.421x | 0.117x | 0.279x |
| MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 39.9 | 26.9-50.0 | 6.28 | yes | `b200_sxm-x6992-nvl72-hybrid` | 142.9 | 292.6-543.1 | 2.07 | yes | 0.279x | 0.092x | 0.330x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.253x to 0.330x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | 2,389.5 | 1,477.9-2,743.1 | 6.86 | yes | `a100_sxm_80gb-x316-tensor` | 280.8 | 454.8-844.1 | 2.62 | yes | 8.510x | 3.250x | 0.382x |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 3,205.3 | 2,363.7-4,387.4 | 5.75 | yes | `a100_sxm_80gb-x336-hybrid` | 229.7 | 407.7-756.8 | 2.39 | yes | 13.956x | 5.797x | 0.415x |
| MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 873.9 | 1,910.7-3,546.6 | 1.94 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 389.6-723.2 | 2.48 | yes | 3.840x | 4.904x | 1.277x |
| MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 805.6 | 1,330.6-2,469.7 | 2.57 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 389.6-723.2 | 2.48 | yes | 3.540x | 3.415x | 0.965x |
| MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 796.3 | 878.9-1,631.4 | 3.84 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 389.6-723.2 | 2.48 | yes | 3.499x | 2.256x | 0.645x |
| MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 796.3 | 878.9-1,631.4 | 3.84 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 389.6-723.2 | 2.48 | yes | 3.499x | 2.256x | 0.645x |
| MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 796.3 | 878.9-1,631.4 | 3.84 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 389.6-723.2 | 2.48 | yes | 3.499x | 2.256x | 0.645x |
| MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 796.3 | 878.9-1,631.4 | 3.84 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 389.6-723.2 | 2.48 | yes | 3.499x | 2.256x | 0.645x |
| MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 327.2 | 429.7-797.6 | 3.23 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 389.6-723.2 | 2.48 | yes | 1.438x | 1.103x | 0.767x |
| MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 90.0 | 123.1-228.4 | 3.10 | yes | `a100_sxm_80gb-x18971-hybrid` | 159.3 | 237.0-439.9 | 2.85 | yes | 0.565x | 0.519x | 0.920x |
| MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 22.9 | 31.1-57.6 | 3.12 | yes | `a100_sxm_80gb-x18971-hybrid` | 83.1 | 166.0-308.1 | 2.12 | yes | 0.275x | 0.187x | 0.680x |

**Does the ratio compress?** Of 11 class rows in this study, 10 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.382x to 1.277x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,293.8 | 3,072.2-5,702.5 | 5.93 | yes | `b200_sxm-x78-nvl72-hybrid` | 872.8 | 2,414.5-4,481.6 | 1.53 | yes | 4.919x | 1.272x | 0.259x |
| MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,202.7 | 3,474.0-6,448.3 | 5.13 | yes | `b200_sxm-x87-nvl72-hybrid` | 885.4 | 2,508.7-4,656.6 | 1.50 | yes | 4.747x | 1.385x | 0.292x |
| MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,293.8 | 3,072.2-5,702.5 | 5.93 | yes | `b200_sxm-x78-nvl72-hybrid` | 872.8 | 2,414.5-4,481.6 | 1.53 | yes | 4.919x | 1.272x | 0.259x |
| MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,202.7 | 3,474.0-6,448.3 | 5.13 | yes | `b200_sxm-x87-nvl72-hybrid` | 885.4 | 2,508.7-4,656.6 | 1.50 | yes | 4.747x | 1.385x | 0.292x |
| MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,293.8 | 3,072.2-5,702.5 | 5.93 | yes | `b200_sxm-x78-nvl72-hybrid` | 834.5 | 2,053.9-3,812.3 | 1.72 | yes | 5.145x | 1.496x | 0.291x |
| MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,202.7 | 3,474.0-6,448.3 | 5.13 | yes | `b200_sxm-x87-nvl72-hybrid` | 849.4 | 2,144.6-3,980.7 | 1.68 | yes | 4.948x | 1.620x | 0.327x |
| MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,293.8 | 3,072.2-5,702.5 | 5.93 | yes | `b200_sxm-x78-nvl72-hybrid` | 768.8 | 1,615.9-2,999.3 | 2.02 | yes | 5.585x | 1.901x | 0.340x |
| MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,202.7 | 3,474.0-6,448.3 | 5.13 | yes | `b200_sxm-x87-nvl72-hybrid` | 786.8 | 1,695.5-3,147.0 | 1.97 | yes | 5.341x | 2.049x | 0.384x |
| MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 4,249.4 | 3,107.6-5,768.1 | 5.80 | yes | `b200_sxm-x150-nvl72-hybrid` | 772.4 | 1,618.3-3,003.7 | 2.02 | yes | 5.502x | 1.920x | 0.349x |
| MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 4,172.4 | 3,477.3-6,454.3 | 5.09 | yes | `b200_sxm-x173-nvl72-hybrid` | 794.3 | 1,697.9-3,151.4 | 1.98 | yes | 5.253x | 2.048x | 0.390x |
| MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 4,179.8 | 2,069.0-3,840.4 | 8.57 | **no** | `b200_sxm-x150-nvl72-hybrid` | 666.1 | 1,164.9-2,162.2 | 2.42 | yes | 6.275x | 1.776x | 0.283x |
| MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,144.5 | 3,507.5-6,510.3 | 5.01 | yes | `b200_sxm-x347-nvl72-hybrid` | 793.6 | 1,644.4-3,052.2 | 2.05 | yes | 5.222x | 2.133x | 0.408x |
| MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 3,902.5 | 1,783.3-3,310.0 | 9.28 | **no** | `b200_sxm-x200-nvl72-hybrid` | 592.0 | 825.6-1,532.4 | 3.04 | yes | 6.593x | 2.160x | 0.328x |
| MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,697.7 | 2,306.2-4,280.6 | 6.80 | yes | `b200_sxm-x347-nvl72-hybrid` | 688.7 | 1,125.1-2,088.3 | 2.60 | yes | 5.369x | 2.050x | 0.382x |
| MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 2,400.0 | 532.3-987.9 | 19.12 | **no** | `b200_sxm-x200-nvl72-hybrid` | 349.7 | 282.0-523.4 | 5.26 | yes | 6.863x | 1.887x | 0.275x |
| MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,259.3 | 1,046.3-1,942.1 | 9.16 | **no** | `b200_sxm-x347-nvl72-hybrid` | 430.4 | 414.9-770.1 | 4.40 | yes | 5.249x | 2.522x | 0.480x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 881.9 | 248.6-461.4 | 15.04 | **no** | `b200_sxm-x173-nvl72-hybrid` | 176.2 | 76.3-141.6 | 9.79 | **no** | 5.005x | 3.258x | 0.651x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 792.0 | 279.9-519.5 | 12.00 | **no** | `b200_sxm-x347-nvl72-hybrid` | 240.0 | 138.5-257.1 | 7.35 | yes | 3.299x | 2.020x | 0.612x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 345.6 | 85.6-158.9 | 17.11 | **no** | `b200_sxm-x200-nvl72-hybrid` | 96.9 | 41.1-76.3 | 10.00 | **no** | 3.566x | 2.084x | 0.584x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 215.4 | 96.4-179.0 | 9.47 | **no** | `b200_sxm-x347-nvl72-hybrid` | 127.4 | 61.7-114.4 | 8.76 | **no** | 1.691x | 1.564x | 0.925x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.259x to 0.925x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 12 of 20 ROM rows and 17 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,100.9 | 2,473.5-4,591.1 | 7.03 | yes | `a100_sxm_80gb-x208-tensor` | 285.7 | 456.9-848.1 | 2.65 | yes | 14.353x | 5.414x | 0.377x |
| MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,649.2 | 3,841.1-7,129.5 | 4.03 | yes | `a100_sxm_80gb-x280-tensor` | 287.9 | 459.5-852.9 | 2.66 | yes | 12.673x | 8.359x | 0.660x |
| MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,100.9 | 2,473.5-4,591.1 | 7.03 | yes | `a100_sxm_80gb-x208-hybrid` | 260.9 | 426.7-792.0 | 2.59 | yes | 15.718x | 5.796x | 0.369x |
| MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,649.2 | 3,841.1-7,129.5 | 4.03 | yes | `a100_sxm_80gb-x280-hybrid` | 263.0 | 433.3-804.3 | 2.57 | yes | 13.875x | 8.865x | 0.639x |
| MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,100.9 | 2,473.5-4,591.1 | 7.03 | yes | `a100_sxm_80gb-x208-hybrid` | 260.9 | 426.7-792.0 | 2.59 | yes | 15.718x | 5.796x | 0.369x |
| MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,649.2 | 3,841.1-7,129.5 | 4.03 | yes | `a100_sxm_80gb-x280-hybrid` | 263.0 | 433.3-804.3 | 2.57 | yes | 13.875x | 8.865x | 0.639x |
| MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,100.9 | 2,473.5-4,591.1 | 7.03 | yes | `a100_sxm_80gb-x208-hybrid` | 236.8 | 378.7-702.9 | 2.65 | yes | 17.316x | 6.531x | 0.377x |
| MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,649.2 | 3,841.1-7,129.5 | 4.03 | yes | `a100_sxm_80gb-x280-hybrid` | 247.0 | 321.4-596.6 | 3.26 | yes | 14.772x | 11.950x | 0.809x |
| MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 4,086.5 | 2,569.9-4,770.1 | 6.74 | yes | `a100_sxm_80gb-x249-hybrid` | 217.8 | 272.2-505.3 | 3.39 | yes | 18.766x | 9.440x | 0.503x |
| MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,642.9 | 2,754.9-5,113.5 | 5.61 | yes | `a100_sxm_80gb-x672-hybrid` | 252.2 | 348.4-646.6 | 3.07 | yes | 14.442x | 7.908x | 0.548x |
| MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 3,837.2 | 1,581.7-2,935.8 | 10.29 | **no** | `a100_sxm_80gb-x249-hybrid` | 211.9 | 367.4-681.9 | 2.45 | yes | 18.110x | 4.305x | 0.238x |
| MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,274.2 | 1,773.6-3,292.1 | 7.83 | yes | `a100_sxm_80gb-x672-hybrid` | 228.4 | 330.1-612.6 | 2.93 | yes | 14.338x | 5.374x | 0.375x |
| MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 3,568.8 | 1,345.1-2,496.8 | 11.25 | **no** | `a100_sxm_80gb-x373-hybrid` | 198.9 | 337.3-626.1 | 2.50 | yes | 17.939x | 3.988x | 0.222x |
| MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,736.1 | 1,574.6-2,922.7 | 7.37 | yes | `a100_sxm_80gb-x672-hybrid` | 211.4 | 418.2-776.2 | 2.14 | yes | 12.944x | 3.765x | 0.291x |
| MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 1,932.0 | 384.5-713.7 | 21.30 | **no** | `a100_sxm_80gb-x373-hybrid` | 116.4 | 163.8-304.1 | 3.01 | yes | 16.599x | 2.347x | 0.141x |
| MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,183.6 | 492.6-914.3 | 10.19 | **no** | `a100_sxm_80gb-x672-hybrid` | 152.1 | 209.9-389.6 | 3.07 | yes | 7.782x | 2.347x | 0.302x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 782.0 | 182.4-338.6 | 18.18 | **no** | `a100_sxm_80gb-x373-hybrid` | 49.0 | 89.6-166.2 | 2.32 | yes | 15.944x | 2.037x | 0.128x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 345.9 | 127.2-236.2 | 11.53 | **no** | `a100_sxm_80gb-x672-hybrid` | 71.5 | 119.9-222.6 | 2.53 | yes | 4.840x | 1.061x | 0.219x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 231.4 | 49.3-91.5 | 19.90 | **no** | `a100_sxm_80gb-x373-hybrid` | 22.4 | 23.3-43.3 | 4.07 | yes | 10.328x | 2.114x | 0.205x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 89.5 | 78.2-145.2 | 4.85 | yes | `a100_sxm_80gb-x672-hybrid` | 29.5 | 37.8-70.2 | 3.30 | yes | 3.040x | 2.068x | 0.680x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.128x to 0.809x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 13 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-qwen3-8b-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x180` | 3,783.5 | 2,538.2-4,711.3 | 6.32 | yes | `b200_sxm-x92-nvl72-hybrid` | 1,110.5 | 4,195.9-7,788.2 | 1.12 | yes | 3.407x | 0.605x | 0.178x |
| Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 8,249.0 | 10,577.4-19,633.0 | 3.31 | yes | `b200_sxm-x58-nvl72-tensor` | 1,276.4 | 4,777.1-8,867.0 | 1.13 | yes | 6.463x | 2.214x | 0.343x |

**Does the ratio compress?** Of 2 class rows in this study, 2 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.178x to 0.343x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 2 of 2 ROM rows and 2 of 2 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-qwen3-8b-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x227` | 3,567.0 | 2,510.8-4,660.3 | 6.02 | yes | `a100_sxm_80gb-x224-tensor` | 575.1 | 1,105.1-2,051.2 | 2.21 | yes | 6.202x | 2.272x | 0.366x |
| Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 8,205.5 | 8,193.3-15,207.9 | 4.25 | yes | `a100_sxm_80gb-x112-tensor` | 459.8 | 1,004.8-1,865.1 | 1.94 | yes | 17.845x | 8.154x | 0.457x |

**Does the ratio compress?** Of 2 class rows in this study, 2 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.366x to 0.457x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 2 of 2 ROM rows and 2 of 2 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-qwen3-8b-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x60-romfill` | 7,120.3 | 4,663.7-8,656.4 | 6.47 | yes | `b200_sxm-x31-nvl72-tensor` | 1,745.3 | 6,201.4-11,510.6 | 1.19 | yes | 4.080x | 0.752x | 0.184x |
| Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 9,134.8 | 13,001.9-24,133.3 | 2.98 | yes | `b200_sxm-x29-nvl72-tensor` | 1,699.9 | 6,057.0-11,242.6 | 1.19 | yes | 5.374x | 2.147x | 0.399x |
| Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x139-romfill` | 3,018.8 | 5,503.5-10,215.2 | 2.33 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | 5,700.5-10,580.8 | 1.41 | yes | 1.587x | 0.965x | 0.608x |
| Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,737.9 | 7,514.2-13,947.4 | 1.54 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | 5,700.5-10,580.8 | 1.41 | yes | 1.439x | 1.318x | 0.916x |
| Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,737.9 | 7,514.2-13,947.4 | 1.54 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | 5,700.5-10,580.8 | 1.41 | yes | 1.439x | 1.318x | 0.916x |
| Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,737.9 | 7,514.2-13,947.4 | 1.54 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | 5,700.5-10,580.8 | 1.41 | yes | 1.439x | 1.318x | 0.916x |
| Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,737.9 | 7,514.2-13,947.4 | 1.54 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | 5,700.5-10,580.8 | 1.41 | yes | 1.439x | 1.318x | 0.916x |
| Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1,809.5 | 4,700.5-8,724.7 | 1.63 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,865.9 | 5,464.8-10,143.4 | 1.45 | yes | 0.970x | 0.860x | 0.887x |
| Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 602.2 | 2,290.7-4,251.8 | 1.11 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,280.5 | 4,009.3-7,441.8 | 1.35 | yes | 0.470x | 0.571x | 1.215x |
| Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 158.3 | 646.5-1,200.1 | 1.04 | yes | `b200_sxm-x4016-nvl72-hybrid` | 593.6 | 1,646.2-3,055.5 | 1.53 | yes | 0.267x | 0.393x | 1.472x |
| Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 40.0 | 166.4-309.0 | 1.02 | yes | `b200_sxm-x4016-nvl72-hybrid` | 190.4 | 646.3-1,199.7 | 1.25 | yes | 0.210x | 0.258x | 1.227x |

**Does the ratio compress?** Of 11 class rows in this study, 8 move the ROM-versus-GPU ratio DOWN under speculation and 3 move it UP. The movement spans 0.184x to 1.472x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-qwen3-8b-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 7,114.3 | 4,499.4-8,351.4 | 6.70 | yes | `a100_sxm_80gb-x56-tensor` | 564.5 | 1,142.9-2,121.4 | 2.09 | yes | 12.604x | 3.937x | 0.312x |
| Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 9,194.4 | 12,256.1-22,749.0 | 3.18 | yes | `a100_sxm_80gb-x56-tensor` | 564.5 | 1,142.9-2,121.4 | 2.09 | yes | 16.289x | 10.723x | 0.658x |
| Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196-romfill` | 2,704.1 | 5,159.5-9,576.8 | 2.22 | yes | `a100_sxm_80gb-x10969-tensor` | 584.4 | 720.3-1,336.9 | 3.44 | yes | 4.627x | 7.163x | 1.548x |
| Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 2,461.8 | 3,439.8-6,384.7 | 3.03 | yes | `a100_sxm_80gb-x10969-hybrid` | 555.9 | 1,064.1-1,975.1 | 2.21 | yes | 4.429x | 3.233x | 0.730x |
| Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 2,041.1 | 2,080.0-3,860.7 | 4.16 | yes | `a100_sxm_80gb-x10969-hybrid` | 555.9 | 1,064.1-1,975.1 | 2.21 | yes | 3.672x | 1.955x | 0.532x |
| Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 1,518.6 | 1,156.2-2,146.1 | 5.57 | yes | `a100_sxm_80gb-x10969-hybrid` | 555.9 | 1,064.1-1,975.1 | 2.21 | yes | 2.732x | 1.087x | 0.398x |
| Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,490.4 | 4,867.6-9,034.9 | 1.30 | yes | `a100_sxm_80gb-x10969-hybrid` | 555.9 | 1,064.1-1,975.1 | 2.21 | yes | 2.681x | 4.574x | 1.706x |
| Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,191.2 | 3,873.2-7,189.3 | 1.30 | yes | `a100_sxm_80gb-x10969-hybrid` | 555.9 | 1,064.1-1,975.1 | 2.21 | yes | 2.143x | 3.640x | 1.698x |
| Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 354.2 | 1,383.9-2,568.6 | 1.09 | yes | `a100_sxm_80gb-x10969-hybrid` | 502.9 | 824.8-1,530.9 | 2.59 | yes | 0.704x | 1.678x | 2.383x |
| Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 91.5 | 376.8-699.3 | 1.03 | yes | `a100_sxm_80gb-x10969-hybrid` | 285.1 | 470.8-873.8 | 2.57 | yes | 0.321x | 0.800x | 2.495x |
| Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 23.0 | 96.4-178.9 | 1.01 | yes | `a100_sxm_80gb-x10969-hybrid` | 117.9 | 432.1-802.1 | 1.16 | yes | 0.195x | 0.223x | 1.143x |

**Does the ratio compress?** Of 11 class rows in this study, 5 move the ROM-versus-GPU ratio DOWN under speculation and 6 move it UP. The movement spans 0.312x to 2.495x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 3,387.3 | 1,313.2-2,437.5 | 10.94 | **no** | `b200_sxm-x58-nvl72-tensor` | 767.6 | 827.2-1,535.3 | 3.93 | yes | 4.413x | 1.588x | 0.360x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3,790.6 | 3,558.7-6,605.5 | 4.52 | yes | `b200_sxm-x58-nvl72-tensor` | 767.6 | 827.2-1,535.3 | 3.93 | yes | 4.939x | 4.302x | 0.871x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2,745.8 | 1,323.1-2,455.9 | 8.80 | **no** | `b200_sxm-x142-nvl72-hybrid` | 766.7 | 823.0-1,527.6 | 3.95 | yes | 3.581x | 1.608x | 0.449x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,786.1 | 4,601.7-8,541.3 | 2.57 | yes | `b200_sxm-x953-nvl72-hybrid` | 747.6 | 798.2-1,481.5 | 3.97 | yes | 3.727x | 5.765x | 1.547x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2,745.8 | 1,323.1-2,455.9 | 8.80 | **no** | `b200_sxm-x142-nvl72-hybrid` | 747.7 | 826.2-1,533.5 | 3.84 | yes | 3.672x | 1.601x | 0.436x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,786.1 | 4,601.7-8,541.3 | 2.57 | yes | `b200_sxm-x953-nvl72-hybrid` | 747.6 | 798.2-1,481.5 | 3.97 | yes | 3.727x | 5.765x | 1.547x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2,745.8 | 1,323.1-2,455.9 | 8.80 | **no** | `b200_sxm-x142-nvl72-hybrid` | 724.3 | 836.5-1,552.6 | 3.67 | yes | 3.791x | 1.582x | 0.417x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,786.1 | 4,601.7-8,541.3 | 2.57 | yes | `b200_sxm-x953-nvl72-hybrid` | 747.6 | 798.2-1,481.5 | 3.97 | yes | 3.727x | 5.765x | 1.547x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2,745.8 | 1,323.1-2,455.9 | 8.80 | **no** | `b200_sxm-x142-nvl72-hybrid` | 724.3 | 836.5-1,552.6 | 3.67 | yes | 3.791x | 1.582x | 0.417x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,786.1 | 4,601.7-8,541.3 | 2.57 | yes | `b200_sxm-x953-nvl72-hybrid` | 737.6 | 759.9-1,410.6 | 4.12 | yes | 3.777x | 6.055x | 1.603x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2,745.8 | 1,323.1-2,455.9 | 8.80 | **no** | `b200_sxm-x142-nvl72-hybrid` | 631.0 | 538.4-999.4 | 4.97 | yes | 4.351x | 2.457x | 0.565x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,786.1 | 4,601.7-8,541.3 | 2.57 | yes | `b200_sxm-x953-nvl72-hybrid` | 717.0 | 765.3-1,420.4 | 3.97 | yes | 3.886x | 6.013x | 1.548x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,713.1 | 1,115.2-2,070.0 | 10.32 | **no** | `b200_sxm-x173-nvl72-hybrid` | 570.4 | 623.3-1,156.9 | 3.88 | yes | 4.757x | 1.789x | 0.376x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,585.1 | 3,775.6-7,008.0 | 2.90 | yes | `b200_sxm-x953-nvl72-hybrid` | 707.0 | 850.3-1,578.2 | 3.53 | yes | 3.656x | 4.440x | 1.214x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 1,579.6 | 486.9-903.7 | 13.76 | **no** | `b200_sxm-x178-pipeline` | 375.3 | 336.6-624.7 | 4.73 | yes | 4.209x | 1.447x | 0.344x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,697.1 | 1,906.6-3,538.9 | 3.77 | yes | `b200_sxm-x953-nvl72-hybrid` | 616.5 | 822.6-1,526.9 | 3.18 | yes | 2.753x | 2.318x | 0.842x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 576.3 | 159.8-296.7 | 15.29 | **no** | `b200_sxm-x178-pipeline` | 173.4 | 167.5-310.9 | 4.39 | yes | 3.323x | 0.954x | 0.287x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 635.2 | 333.0-618.1 | 8.09 | **no** | `b200_sxm-x953-pipeline` | 417.8 | 409.8-760.6 | 4.32 | yes | 1.520x | 0.813x | 0.535x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 144.5 | 49.3-91.5 | 12.43 | **no** | `b200_sxm-x178-pipeline` | 58.3 | 122.8-227.9 | 2.02 | yes | 2.477x | 0.402x | 0.162x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 175.7 | 89.5-166.1 | 8.33 | **no** | `b200_sxm-x953-pipeline` | 210.8 | 185.4-344.2 | 4.82 | yes | 0.834x | 0.482x | 0.579x |

**Does the ratio compress?** Of 20 class rows in this study, 14 move the ROM-versus-GPU ratio DOWN under speculation and 6 move it UP. The movement spans 0.162x to 1.603x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x44` | 4,377.2 | 2,960.0-5,494.2 | 6.27 | yes | `b200_sxm-x22-nvl72-tensor` | 857.3 | 2,098.8-3,895.6 | 1.73 | yes | 5.106x | 1.410x | 0.276x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,240.3 | 3,185.4-5,912.6 | 5.64 | yes | `b200_sxm-x58-nvl72-tensor` | 885.0 | 2,215.2-4,111.8 | 1.69 | yes | 4.791x | 1.438x | 0.300x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 4,351.3 | 2,915.9-5,412.2 | 6.33 | yes | `b200_sxm-x26-nvl72-tensor` | 831.0 | 1,616.3-3,000.0 | 2.18 | yes | 5.236x | 1.804x | 0.345x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,240.3 | 3,185.4-5,912.6 | 5.64 | yes | `b200_sxm-x58-nvl72-tensor` | 854.2 | 1,649.9-3,062.5 | 2.20 | yes | 4.964x | 1.931x | 0.389x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 4,351.3 | 2,915.9-5,412.2 | 6.33 | yes | `b200_sxm-x26-hybrid` | 814.8 | 1,674.3-3,107.7 | 2.06 | yes | 5.341x | 1.742x | 0.326x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,240.3 | 3,185.4-5,912.6 | 5.64 | yes | `b200_sxm-x58-hybrid` | 823.4 | 1,768.7-3,283.0 | 1.97 | yes | 5.150x | 1.801x | 0.350x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 4,351.3 | 2,915.9-5,412.2 | 6.33 | yes | `b200_sxm-x26-hybrid` | 755.4 | 1,255.0-2,329.4 | 2.55 | yes | 5.760x | 2.323x | 0.403x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,240.3 | 3,185.4-5,912.6 | 5.64 | yes | `b200_sxm-x58-hybrid` | 823.4 | 1,768.7-3,283.0 | 1.97 | yes | 5.150x | 1.801x | 0.350x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 4,311.3 | 2,894.3-5,372.2 | 6.32 | yes | `b200_sxm-x44-hybrid` | 737.6 | 1,154.0-2,142.0 | 2.71 | yes | 5.845x | 2.508x | 0.429x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,240.3 | 3,185.4-5,912.6 | 5.64 | yes | `b200_sxm-x58-hybrid` | 765.5 | 1,326.3-2,461.9 | 2.45 | yes | 5.539x | 2.402x | 0.434x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,249.7 | 2,855.6-5,300.4 | 6.31 | yes | `b200_sxm-x173-nvl72-hybrid` | 801.8 | 1,683.2-3,124.2 | 2.02 | yes | 5.300x | 1.697x | 0.320x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,230.4 | 3,215.4-5,968.3 | 5.58 | yes | `b200_sxm-x116-nvl72-hybrid` | 770.8 | 1,414.3-2,625.2 | 2.31 | yes | 5.488x | 2.273x | 0.414x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,249.7 | 2,855.6-5,300.4 | 6.31 | yes | `b200_sxm-x173-nvl72-hybrid` | 730.7 | 1,221.1-2,266.6 | 2.54 | yes | 5.816x | 2.338x | 0.402x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,230.4 | 3,215.4-5,968.3 | 5.58 | yes | `b200_sxm-x231-nvl72-hybrid` | 758.6 | 1,396.5-2,592.1 | 2.30 | yes | 5.576x | 2.302x | 0.413x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,282.0 | 1,313.1-2,437.4 | 10.60 | **no** | `b200_sxm-x173-nvl72-hybrid` | 489.5 | 494.7-918.3 | 4.20 | yes | 6.704x | 2.654x | 0.396x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,892.8 | 1,865.2-3,462.0 | 8.85 | **no** | `b200_sxm-x347-nvl72-hybrid` | 609.6 | 791.8-1,469.8 | 3.26 | yes | 6.386x | 2.355x | 0.369x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,633.5 | 430.1-798.3 | 16.10 | **no** | `b200_sxm-x173-nvl72-hybrid` | 251.0 | 273.3-507.3 | 3.89 | yes | 6.507x | 1.574x | 0.242x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,697.5 | 786.8-1,460.4 | 14.54 | **no** | `b200_sxm-x347-nvl72-hybrid` | 360.7 | 448.7-832.9 | 3.41 | yes | 7.478x | 1.753x | 0.234x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 503.6 | 127.5-236.7 | 16.74 | **no** | `b200_sxm-x173-nvl72-hybrid` | 121.3 | 87.3-162.0 | 5.90 | yes | 4.150x | 1.462x | 0.352x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,013.1 | 268.2-497.9 | 16.01 | **no** | `b200_sxm-x347-nvl72-hybrid` | 171.1 | 157.6-292.5 | 4.60 | yes | 5.922x | 1.702x | 0.287x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.234x to 0.434x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 14 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4,355.9 | 3,045.9-5,653.6 | 6.06 | yes | `b200_sxm-x24-nvl72-tensor` | 864.4 | 2,208.9-4,100.0 | 1.66 | yes | 5.039x | 1.379x | 0.274x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,268.0 | 3,365.3-6,246.4 | 5.38 | yes | `b200_sxm-x58-nvl72-tensor` | 888.4 | 2,313.9-4,294.9 | 1.63 | yes | 4.804x | 1.454x | 0.303x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4,355.9 | 3,045.9-5,653.6 | 6.06 | yes | `b200_sxm-x24-hybrid` | 849.3 | 1,861.9-3,455.8 | 1.93 | yes | 5.129x | 1.636x | 0.319x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,268.0 | 3,365.3-6,246.4 | 5.38 | yes | `b200_sxm-x58-nvl72-tensor` | 860.7 | 1,761.8-3,270.2 | 2.07 | yes | 4.959x | 1.910x | 0.385x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4,355.9 | 3,045.9-5,653.6 | 6.06 | yes | `b200_sxm-x24-hybrid` | 830.8 | 1,681.7-3,121.5 | 2.09 | yes | 5.243x | 1.811x | 0.345x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,268.0 | 3,365.3-6,246.4 | 5.38 | yes | `b200_sxm-x58-hybrid` | 826.5 | 1,824.8-3,387.0 | 1.92 | yes | 5.164x | 1.844x | 0.357x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4,355.9 | 3,045.9-5,653.6 | 6.06 | yes | `b200_sxm-x24-hybrid` | 765.1 | 1,240.8-2,303.0 | 2.61 | yes | 5.693x | 2.455x | 0.431x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,268.0 | 3,365.3-6,246.4 | 5.38 | yes | `b200_sxm-x58-hybrid` | 826.5 | 1,824.8-3,387.0 | 1.92 | yes | 5.164x | 1.844x | 0.357x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 4,340.6 | 3,008.2-5,583.6 | 6.12 | yes | `b200_sxm-x44-hybrid` | 744.4 | 1,219.2-2,263.0 | 2.59 | yes | 5.831x | 2.467x | 0.423x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,268.0 | 3,365.3-6,246.4 | 5.38 | yes | `b200_sxm-x58-hybrid` | 770.9 | 1,390.4-2,580.8 | 2.35 | yes | 5.536x | 2.420x | 0.437x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,278.1 | 2,965.4-5,504.1 | 6.12 | yes | `b200_sxm-x173-nvl72-hybrid` | 806.1 | 1,757.7-3,262.6 | 1.94 | yes | 5.307x | 1.687x | 0.318x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,257.6 | 3,403.3-6,317.0 | 5.30 | yes | `b200_sxm-x116-nvl72-hybrid` | 776.6 | 1,492.4-2,770.1 | 2.21 | yes | 5.482x | 2.280x | 0.416x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,278.1 | 2,965.4-5,504.1 | 6.12 | yes | `b200_sxm-x173-nvl72-hybrid` | 737.8 | 1,301.2-2,415.2 | 2.40 | yes | 5.798x | 2.279x | 0.393x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,257.6 | 3,403.3-6,317.0 | 5.30 | yes | `b200_sxm-x231-nvl72-hybrid` | 764.4 | 1,475.3-2,738.3 | 2.20 | yes | 5.570x | 2.307x | 0.414x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,393.8 | 1,384.4-2,569.7 | 10.39 | **no** | `b200_sxm-x173-nvl72-hybrid` | 502.6 | 549.5-1,019.9 | 3.88 | yes | 6.753x | 2.520x | 0.373x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,018.6 | 1,972.0-3,660.3 | 8.64 | **no** | `b200_sxm-x347-nvl72-hybrid` | 619.6 | 860.5-1,597.1 | 3.05 | yes | 6.486x | 2.292x | 0.353x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,747.7 | 461.7-856.9 | 16.05 | **no** | `b200_sxm-x173-nvl72-hybrid` | 258.8 | 178.4-331.2 | 6.15 | yes | 6.752x | 2.587x | 0.383x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,867.5 | 836.5-1,552.7 | 14.53 | **no** | `b200_sxm-x347-nvl72-hybrid` | 362.9 | 504.9-937.1 | 3.05 | yes | 7.901x | 1.657x | 0.210x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 547.7 | 138.9-257.8 | 16.72 | **no** | `b200_sxm-x173-nvl72-hybrid` | 127.9 | 97.9-181.7 | 5.54 | yes | 4.284x | 1.419x | 0.331x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,113.7 | 293.6-545.0 | 16.08 | **no** | `b200_sxm-x347-nvl72-hybrid` | 175.1 | 174.7-324.3 | 4.25 | yes | 6.359x | 1.681x | 0.264x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.210x to 0.437x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 14 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 1,069.0-1,984.1 | 7.80 | yes | `b200_sxm-x157-nvl72-hybrid` | 570.7 | 995.5-1,847.9 | 2.43 | yes | 3.446x | 1.074x | 0.312x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 2,132.7 | 2,150.5-3,991.7 | 4.20 | yes | `b200_sxm-x116-nvl72-hybrid` | 574.9 | 1,004.0-1,863.5 | 2.43 | yes | 3.710x | 2.142x | 0.577x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 1,069.0-1,984.1 | 7.80 | yes | `b200_sxm-x157-nvl72-hybrid` | 570.7 | 995.5-1,847.9 | 2.43 | yes | 3.446x | 1.074x | 0.312x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,080.6 | 2,143.8-3,979.2 | 4.12 | yes | `b200_sxm-x289-nvl72-hybrid` | 571.7 | 999.0-1,854.3 | 2.43 | yes | 3.639x | 2.146x | 0.590x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 1,069.0-1,984.1 | 7.80 | yes | `b200_sxm-x157-nvl72-hybrid` | 554.1 | 834.9-1,549.6 | 2.81 | yes | 3.550x | 1.280x | 0.361x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,080.6 | 2,143.8-3,979.2 | 4.12 | yes | `b200_sxm-x289-nvl72-hybrid` | 571.7 | 999.0-1,854.3 | 2.43 | yes | 3.639x | 2.146x | 0.590x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 1,069.0-1,984.1 | 7.80 | yes | `b200_sxm-x157-nvl72-hybrid` | 547.6 | 945.8-1,755.6 | 2.45 | yes | 3.592x | 1.130x | 0.315x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,080.6 | 2,143.8-3,979.2 | 4.12 | yes | `b200_sxm-x289-nvl72-hybrid` | 545.3 | 985.4-1,829.0 | 2.35 | yes | 3.816x | 2.176x | 0.570x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 1,069.0-1,984.1 | 7.80 | yes | `b200_sxm-x157-nvl72-hybrid` | 511.2 | 711.9-1,321.3 | 3.04 | yes | 3.848x | 1.502x | 0.390x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,080.6 | 2,143.8-3,979.2 | 4.12 | yes | `b200_sxm-x289-nvl72-hybrid` | 539.9 | 952.2-1,767.4 | 2.40 | yes | 3.853x | 2.251x | 0.584x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,967.0 | 1,069.0-1,984.1 | 7.80 | yes | `b200_sxm-x157-nvl72-hybrid` | 434.7 | 441.1-818.8 | 4.18 | yes | 4.524x | 2.423x | 0.536x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,080.6 | 2,143.8-3,979.2 | 4.12 | yes | `b200_sxm-x289-nvl72-hybrid` | 498.8 | 688.8-1,278.5 | 3.07 | yes | 4.171x | 3.112x | 0.746x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,953.8 | 698.4-1,296.4 | 11.86 | **no** | `b200_sxm-x157-nvl72-hybrid` | 350.1 | 387.6-719.4 | 3.83 | yes | 5.581x | 1.802x | 0.323x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,998.4 | 1,402.9-2,604.1 | 6.04 | yes | `b200_sxm-x289-nvl72-hybrid` | 420.7 | 420.9-781.3 | 4.24 | yes | 4.750x | 3.333x | 0.702x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,320.2 | 301.7-559.9 | 18.56 | **no** | `b200_sxm-x173-nvl72-hybrid` | 188.3 | 149.3-277.0 | 5.35 | yes | 7.013x | 2.021x | 0.288x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,479.2 | 629.9-1,169.2 | 9.96 | **no** | `b200_sxm-x347-nvl72-hybrid` | 269.8 | 252.8-469.2 | 4.53 | yes | 5.482x | 2.492x | 0.455x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 529.2 | 104.8-194.5 | 21.42 | **no** | `b200_sxm-x173-nvl72-hybrid` | 74.5 | 73.9-137.2 | 4.27 | yes | 7.105x | 1.417x | 0.199x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 671.5 | 168.9-313.5 | 16.86 | **no** | `b200_sxm-x347-nvl72-hybrid` | 121.6 | 124.6-231.2 | 4.14 | yes | 5.524x | 1.356x | 0.246x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 149.7 | 34.8-64.5 | 18.26 | **no** | `b200_sxm-x173-nvl72-hybrid` | 29.4 | 23.9-44.4 | 5.21 | yes | 5.092x | 1.454x | 0.286x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 198.8 | 70.7-131.2 | 11.93 | **no** | `b200_sxm-x347-nvl72-hybrid` | 45.4 | 42.2-78.3 | 4.56 | yes | 4.380x | 1.676x | 0.383x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.199x to 0.746x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 13 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 1,264.1-2,346.3 | 6.86 | yes | `b200_sxm-x137-nvl72-hybrid` | 594.5 | 1,254.9-2,329.3 | 2.01 | yes | 3.441x | 1.007x | 0.293x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,253.4 | 2,497.9-4,636.4 | 3.82 | yes | `b200_sxm-x144-nvl72-hybrid` | 595.8 | 1,260.0-2,338.7 | 2.01 | yes | 3.782x | 1.982x | 0.524x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 1,264.1-2,346.3 | 6.86 | yes | `b200_sxm-x137-nvl72-hybrid` | 594.5 | 1,254.9-2,329.3 | 2.01 | yes | 3.441x | 1.007x | 0.293x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,253.4 | 2,497.9-4,636.4 | 3.82 | yes | `b200_sxm-x144-nvl72-hybrid` | 595.8 | 1,260.0-2,338.7 | 2.01 | yes | 3.782x | 1.982x | 0.524x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 1,264.1-2,346.3 | 6.86 | yes | `b200_sxm-x137-nvl72-hybrid` | 568.7 | 1,052.8-1,954.2 | 2.29 | yes | 3.598x | 1.201x | 0.334x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,253.4 | 2,497.9-4,636.4 | 3.82 | yes | `b200_sxm-x144-nvl72-hybrid` | 570.6 | 1,059.2-1,966.0 | 2.28 | yes | 3.949x | 2.358x | 0.597x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 1,264.1-2,346.3 | 6.86 | yes | `b200_sxm-x137-nvl72-hybrid` | 559.1 | 1,133.3-2,103.5 | 2.09 | yes | 3.659x | 1.115x | 0.305x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,253.4 | 2,497.9-4,636.4 | 3.82 | yes | `b200_sxm-x144-nvl72-hybrid` | 564.3 | 1,152.3-2,138.8 | 2.08 | yes | 3.993x | 2.168x | 0.543x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 1,264.1-2,346.3 | 6.86 | yes | `b200_sxm-x137-nvl72-hybrid` | 520.0 | 843.1-1,564.9 | 2.62 | yes | 3.935x | 1.499x | 0.381x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,253.4 | 2,497.9-4,636.4 | 3.82 | yes | `b200_sxm-x144-nvl72-hybrid` | 525.6 | 856.9-1,590.5 | 2.60 | yes | 4.287x | 2.915x | 0.680x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,046.1 | 1,264.1-2,346.3 | 6.86 | yes | `b200_sxm-x137-nvl72-hybrid` | 449.0 | 553.0-1,026.5 | 3.44 | yes | 4.557x | 2.286x | 0.502x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,237.3 | 2,488.3-4,618.6 | 3.81 | yes | `b200_sxm-x347-nvl72-hybrid` | 532.6 | 964.2-1,789.7 | 2.34 | yes | 4.201x | 2.581x | 0.614x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 2,024.2 | 785.9-1,458.7 | 10.92 | **no** | `b200_sxm-x137-nvl72-hybrid` | 354.7 | 331.3-614.9 | 4.54 | yes | 5.707x | 2.372x | 0.416x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,190.2 | 1,571.8-2,917.4 | 5.91 | yes | `b200_sxm-x347-nvl72-hybrid` | 469.9 | 634.5-1,177.8 | 3.14 | yes | 4.661x | 2.477x | 0.531x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,406.1 | 341.5-633.9 | 17.46 | **no** | `b200_sxm-x173-nvl72-hybrid` | 203.7 | 198.4-368.2 | 4.35 | yes | 6.902x | 1.722x | 0.249x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,826.7 | 737.5-1,368.9 | 10.50 | **no** | `b200_sxm-x347-nvl72-hybrid` | 287.6 | 300.9-558.5 | 4.05 | yes | 6.351x | 2.451x | 0.386x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 661.6 | 124.6-231.2 | 22.52 | **no** | `b200_sxm-x173-nvl72-hybrid` | 82.5 | 66.1-122.7 | 5.29 | yes | 8.016x | 1.885x | 0.235x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,015.4 | 197.1-365.8 | 21.84 | **no** | `b200_sxm-x347-nvl72-hybrid` | 129.4 | 114.4-212.3 | 4.80 | yes | 7.849x | 1.723x | 0.220x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 193.8 | 44.1-81.9 | 18.63 | **no** | `b200_sxm-x173-nvl72-hybrid` | 37.5 | 19.2-35.6 | 8.30 | **no** | 5.162x | 2.299x | 0.445x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 396.8 | 124.8-231.7 | 13.48 | **no** | `b200_sxm-x347-nvl72-hybrid` | 53.4 | 34.9-64.8 | 6.49 | yes | 7.433x | 3.579x | 0.481x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.220x to 0.680x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 13 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 1,306.9-2,425.8 | 7.01 | yes | `b200_sxm-x134-nvl72-hybrid` | 596.4 | 1,299.8-2,412.7 | 1.95 | yes | 3.622x | 1.005x | 0.278x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,309.2 | 2,581.6-4,791.7 | 3.79 | yes | `b200_sxm-x144-nvl72-hybrid` | 598.2 | 1,307.8-2,427.4 | 1.94 | yes | 3.860x | 1.974x | 0.511x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 1,306.9-2,425.8 | 7.01 | yes | `b200_sxm-x134-nvl72-hybrid` | 596.4 | 1,299.8-2,412.7 | 1.95 | yes | 3.622x | 1.005x | 0.278x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,309.2 | 2,581.6-4,791.7 | 3.79 | yes | `b200_sxm-x144-nvl72-hybrid` | 598.2 | 1,307.8-2,427.4 | 1.94 | yes | 3.860x | 1.974x | 0.511x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 1,306.9-2,425.8 | 7.01 | yes | `b200_sxm-x134-nvl72-hybrid` | 570.7 | 1,094.3-2,031.2 | 2.21 | yes | 3.785x | 1.194x | 0.316x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,309.2 | 2,581.6-4,791.7 | 3.79 | yes | `b200_sxm-x144-nvl72-hybrid` | 573.6 | 1,104.4-2,049.8 | 2.20 | yes | 4.026x | 2.338x | 0.581x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 1,306.9-2,425.8 | 7.01 | yes | `b200_sxm-x134-nvl72-hybrid` | 558.9 | 1,160.8-2,154.7 | 2.04 | yes | 3.865x | 1.126x | 0.291x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,309.2 | 2,581.6-4,791.7 | 3.79 | yes | `b200_sxm-x144-nvl72-hybrid` | 566.5 | 1,190.3-2,209.4 | 2.02 | yes | 4.076x | 2.169x | 0.532x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 1,306.9-2,425.8 | 7.01 | yes | `b200_sxm-x134-nvl72-hybrid` | 520.7 | 872.8-1,620.1 | 2.53 | yes | 4.148x | 1.497x | 0.361x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,309.2 | 2,581.6-4,791.7 | 3.79 | yes | `b200_sxm-x144-nvl72-hybrid` | 529.0 | 894.7-1,660.6 | 2.51 | yes | 4.365x | 2.886x | 0.661x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 2,160.2 | 1,306.9-2,425.8 | 7.01 | yes | `b200_sxm-x134-nvl72-hybrid` | 451.2 | 580.7-1,077.8 | 3.29 | yes | 4.788x | 2.251x | 0.470x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,306.9 | 1,616.3-3,000.1 | 6.05 | yes | `b200_sxm-x144-nvl72-hybrid` | 460.2 | 594.2-1,103.0 | 3.28 | yes | 5.013x | 2.720x | 0.543x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 2,103.9 | 802.3-1,489.1 | 11.12 | **no** | `b200_sxm-x157-nvl72-hybrid` | 379.7 | 384.4-713.5 | 4.19 | yes | 5.542x | 2.087x | 0.377x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,298.1 | 1,618.7-3,004.5 | 6.02 | yes | `b200_sxm-x347-nvl72-hybrid` | 474.4 | 668.7-1,241.2 | 3.01 | yes | 4.845x | 2.421x | 0.500x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,465.3 | 447.5-830.6 | 13.88 | **no** | `b200_sxm-x173-nvl72-hybrid` | 204.2 | 214.9-398.9 | 4.03 | yes | 7.175x | 2.082x | 0.290x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,914.2 | 759.2-1,409.1 | 10.69 | **no** | `b200_sxm-x347-nvl72-hybrid` | 288.1 | 301.1-558.9 | 4.06 | yes | 6.643x | 2.521x | 0.380x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 687.0 | 128.1-237.9 | 22.73 | **no** | `b200_sxm-x173-nvl72-hybrid` | 82.9 | 73.3-136.1 | 4.79 | yes | 8.290x | 1.747x | 0.211x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,050.0 | 202.2-375.4 | 22.01 | **no** | `b200_sxm-x347-nvl72-hybrid` | 129.8 | 125.2-232.3 | 4.40 | yes | 8.091x | 1.616x | 0.200x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 202.6 | 45.9-85.3 | 18.70 | **no** | `b200_sxm-x173-nvl72-hybrid` | 39.2 | 21.0-39.0 | 7.91 | **no** | 5.165x | 2.186x | 0.423x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 415.4 | 121.2-224.9 | 14.54 | **no** | `b200_sxm-x347-nvl72-hybrid` | 53.9 | 37.8-70.2 | 6.04 | yes | 7.705x | 3.204x | 0.416x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.200x to 0.661x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 13 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x152` | 3,050.2 | 1,028.4-1,908.8 | 12.58 | **no** | `a100_sxm_80gb-x150-hybrid` | 332.4 | 290.1-538.5 | 4.86 | yes | 9.177x | 3.545x | 0.386x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 3,722.8 | 3,083.3-5,723.0 | 5.12 | yes | `a100_sxm_80gb-x168-hybrid` | 332.9 | 290.6-539.3 | 4.86 | yes | 11.184x | 10.611x | 0.949x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,523.9 | 1,183.7-2,197.1 | 9.04 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 285.4-529.7 | 4.81 | yes | 7.795x | 4.148x | 0.532x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,432.9 | 1,648.0-3,058.9 | 6.26 | yes | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 289.6-537.5 | 4.76 | yes | 7.489x | 5.691x | 0.760x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,523.9 | 1,183.7-2,197.1 | 9.04 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 285.4-529.7 | 4.81 | yes | 7.795x | 4.148x | 0.532x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,432.9 | 1,648.0-3,058.9 | 6.26 | yes | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 289.6-537.5 | 4.76 | yes | 7.489x | 5.691x | 0.760x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,523.9 | 1,183.7-2,197.1 | 9.04 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 285.4-529.7 | 4.81 | yes | 7.795x | 4.148x | 0.532x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,432.9 | 1,648.0-3,058.9 | 6.26 | yes | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 289.6-537.5 | 4.76 | yes | 7.489x | 5.691x | 0.760x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,523.9 | 1,183.7-2,197.1 | 9.04 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 285.4-529.7 | 4.81 | yes | 7.795x | 4.148x | 0.532x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,432.9 | 1,648.0-3,058.9 | 6.26 | yes | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 289.6-537.5 | 4.76 | yes | 7.489x | 5.691x | 0.760x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,444.6 | 959.3-1,780.6 | 10.80 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 285.4-529.7 | 4.81 | yes | 7.550x | 3.361x | 0.445x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,432.9 | 1,648.0-3,058.9 | 6.26 | yes | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 289.6-537.5 | 4.76 | yes | 7.489x | 5.691x | 0.760x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 2,178.3 | 862.2-1,600.4 | 10.71 | **no** | `a100_sxm_80gb-x387-hybrid` | 296.8 | 228.4-423.9 | 5.51 | yes | 7.340x | 3.775x | 0.514x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,234.3 | 1,533.9-2,847.0 | 6.18 | yes | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 289.6-537.5 | 4.76 | yes | 6.878x | 5.297x | 0.770x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,189.6 | 312.2-579.5 | 16.16 | **no** | `a100_sxm_80gb-x387-hybrid` | 175.3 | 121.0-224.7 | 6.14 | yes | 6.786x | 2.579x | 0.380x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,232.5 | 556.3-1,032.5 | 9.39 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 289.6-537.5 | 4.76 | yes | 3.794x | 1.921x | 0.506x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 359.8 | 115.1-213.7 | 13.25 | **no** | `a100_sxm_80gb-x387-hybrid` | 80.5 | 60.1-111.5 | 5.68 | yes | 4.467x | 1.916x | 0.429x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 390.1 | 150.1-278.6 | 11.02 | **no** | `a100_sxm_80gb-x2574-hybrid` | 222.0 | 194.3-360.7 | 4.85 | yes | 1.757x | 0.772x | 0.440x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 93.6 | 41.7-77.3 | 9.53 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 103.3 | 37.8-70.2 | 11.57 | **no** | `a100_sxm_80gb-x2574-hybrid` | 111.7 | 98.0-182.0 | 4.83 | yes | 0.925x | 0.386x | 0.417x |

**Does the ratio compress?** Of 19 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.380x to 0.949x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 4,175.0 | 2,260.8-4,196.4 | 7.83 | yes | `a100_sxm_80gb-x73-hybrid` | 404.0 | 683.8-1,269.2 | 2.50 | yes | 10.335x | 3.306x | 0.320x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,951.3 | 3,302.6-6,130.0 | 5.07 | yes | `a100_sxm_80gb-x112-hybrid` | 413.4 | 722.4-1,340.8 | 2.43 | yes | 9.559x | 4.572x | 0.478x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 4,175.0 | 2,260.8-4,196.4 | 7.83 | yes | `a100_sxm_80gb-x73-hybrid` | 404.0 | 683.8-1,269.2 | 2.50 | yes | 10.335x | 3.306x | 0.320x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,951.3 | 3,302.6-6,130.0 | 5.07 | yes | `a100_sxm_80gb-x112-hybrid` | 413.4 | 722.4-1,340.8 | 2.43 | yes | 9.559x | 4.572x | 0.478x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 4,175.0 | 2,260.8-4,196.4 | 7.83 | yes | `a100_sxm_80gb-x73-hybrid` | 404.0 | 683.8-1,269.2 | 2.50 | yes | 10.335x | 3.306x | 0.320x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,951.3 | 3,302.6-6,130.0 | 5.07 | yes | `a100_sxm_80gb-x112-hybrid` | 413.4 | 722.4-1,340.8 | 2.43 | yes | 9.559x | 4.572x | 0.478x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 4,175.0 | 2,260.8-4,196.4 | 7.83 | yes | `a100_sxm_80gb-x73-hybrid` | 404.0 | 683.8-1,269.2 | 2.50 | yes | 10.335x | 3.306x | 0.320x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,951.3 | 3,302.6-6,130.0 | 5.07 | yes | `a100_sxm_80gb-x112-hybrid` | 413.4 | 722.4-1,340.8 | 2.43 | yes | 9.559x | 4.572x | 0.478x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 4,175.0 | 2,260.8-4,196.4 | 7.83 | yes | `a100_sxm_80gb-x73-hybrid` | 374.0 | 544.1-1,010.0 | 2.91 | yes | 11.163x | 4.155x | 0.372x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 3,948.7 | 3,693.5-6,855.7 | 4.53 | yes | `a100_sxm_80gb-x168-hybrid` | 409.4 | 719.8-1,336.1 | 2.41 | yes | 9.645x | 5.131x | 0.532x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 4,116.2 | 2,265.7-4,205.4 | 7.70 | yes | `a100_sxm_80gb-x146-hybrid` | 371.6 | 537.7-998.0 | 2.93 | yes | 11.078x | 4.214x | 0.380x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,936.2 | 3,734.9-6,932.5 | 4.47 | yes | `a100_sxm_80gb-x448-hybrid` | 397.4 | 696.7-1,293.1 | 2.42 | yes | 9.904x | 5.361x | 0.541x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,098.7 | 2,254.9-4,185.4 | 7.71 | yes | `a100_sxm_80gb-x335-hybrid` | 370.5 | 534.6-992.3 | 2.94 | yes | 11.063x | 4.218x | 0.381x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,934.1 | 3,724.1-6,912.5 | 4.48 | yes | `a100_sxm_80gb-x672-hybrid` | 397.4 | 708.9-1,315.8 | 2.38 | yes | 9.899x | 5.254x | 0.531x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,917.5 | 988.8-1,835.4 | 12.51 | **no** | `a100_sxm_80gb-x335-hybrid` | 235.3 | 203.9-378.4 | 4.89 | yes | 12.401x | 4.850x | 0.391x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,261.4 | 1,932.3-3,586.6 | 7.16 | yes | `a100_sxm_80gb-x672-hybrid` | 309.6 | 343.9-638.3 | 3.82 | yes | 10.534x | 5.619x | 0.533x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,290.7 | 317.2-588.8 | 17.25 | **no** | `a100_sxm_80gb-x335-hybrid` | 112.0 | 119.9-222.6 | 3.96 | yes | 11.526x | 2.645x | 0.229x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,776.8 | 573.4-1,064.4 | 13.14 | **no** | `a100_sxm_80gb-x672-hybrid` | 168.7 | 204.1-378.8 | 3.50 | yes | 10.535x | 2.810x | 0.267x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 378.6 | 94.0-174.4 | 17.09 | **no** | `a100_sxm_80gb-x335-hybrid` | 46.8 | 32.6-60.4 | 6.10 | yes | 8.086x | 2.886x | 0.357x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 567.0 | 194.5-360.9 | 12.36 | **no** | `a100_sxm_80gb-x672-hybrid` | 71.5 | 64.4-119.5 | 4.71 | yes | 7.925x | 3.021x | 0.381x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.229x to 0.541x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 15 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 4,192.4 | 2,397.8-4,450.7 | 7.41 | yes | `a100_sxm_80gb-x67-hybrid` | 409.5 | 713.8-1,325.0 | 2.43 | yes | 10.239x | 3.359x | 0.328x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,182.6 | 3,991.9-7,409.5 | 4.44 | yes | `a100_sxm_80gb-x112-hybrid` | 415.8 | 750.7-1,393.4 | 2.35 | yes | 10.059x | 5.318x | 0.529x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 4,192.4 | 2,397.8-4,450.7 | 7.41 | yes | `a100_sxm_80gb-x67-hybrid` | 409.5 | 713.8-1,325.0 | 2.43 | yes | 10.239x | 3.359x | 0.328x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,182.6 | 3,991.9-7,409.5 | 4.44 | yes | `a100_sxm_80gb-x112-hybrid` | 415.8 | 750.7-1,393.4 | 2.35 | yes | 10.059x | 5.318x | 0.529x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 4,192.4 | 2,397.8-4,450.7 | 7.41 | yes | `a100_sxm_80gb-x67-hybrid` | 409.5 | 713.8-1,325.0 | 2.43 | yes | 10.239x | 3.359x | 0.328x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,182.6 | 3,991.9-7,409.5 | 4.44 | yes | `a100_sxm_80gb-x112-hybrid` | 415.8 | 750.7-1,393.4 | 2.35 | yes | 10.059x | 5.318x | 0.529x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 4,192.4 | 2,397.8-4,450.7 | 7.41 | yes | `a100_sxm_80gb-x67-hybrid` | 409.5 | 713.8-1,325.0 | 2.43 | yes | 10.239x | 3.359x | 0.328x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,182.6 | 3,991.9-7,409.5 | 4.44 | yes | `a100_sxm_80gb-x112-hybrid` | 415.8 | 750.7-1,393.4 | 2.35 | yes | 10.059x | 5.318x | 0.529x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 4,192.4 | 2,397.8-4,450.7 | 7.41 | yes | `a100_sxm_80gb-x67-hybrid` | 372.7 | 546.3-1,014.0 | 2.89 | yes | 11.248x | 4.389x | 0.390x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 4,177.5 | 4,033.4-7,486.5 | 4.39 | yes | `a100_sxm_80gb-x168-hybrid` | 411.8 | 747.9-1,388.3 | 2.33 | yes | 10.144x | 5.393x | 0.532x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 4,141.3 | 2,360.7-4,381.7 | 7.44 | yes | `a100_sxm_80gb-x146-hybrid` | 374.9 | 564.4-1,047.5 | 2.82 | yes | 11.046x | 4.183x | 0.379x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4,156.0 | 4,078.1-7,569.5 | 4.32 | yes | `a100_sxm_80gb-x448-hybrid` | 399.7 | 722.9-1,341.8 | 2.34 | yes | 10.398x | 5.641x | 0.543x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,123.6 | 2,349.0-4,360.0 | 7.44 | yes | `a100_sxm_80gb-x335-hybrid` | 373.5 | 558.4-1,036.4 | 2.84 | yes | 11.041x | 4.207x | 0.381x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,155.1 | 4,066.2-7,547.4 | 4.33 | yes | `a100_sxm_80gb-x672-hybrid` | 399.7 | 736.1-1,366.2 | 2.30 | yes | 10.396x | 5.524x | 0.531x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,039.8 | 1,043.1-1,936.1 | 12.36 | **no** | `a100_sxm_80gb-x335-hybrid` | 240.2 | 218.0-404.6 | 4.67 | yes | 12.657x | 4.785x | 0.378x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,706.8 | 2,107.9-3,912.6 | 7.46 | yes | `a100_sxm_80gb-x672-hybrid` | 313.8 | 363.8-675.2 | 3.66 | yes | 11.812x | 5.795x | 0.491x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,385.4 | 340.1-631.3 | 17.27 | **no** | `a100_sxm_80gb-x335-hybrid` | 112.9 | 131.8-244.7 | 3.63 | yes | 12.277x | 2.580x | 0.210x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,386.5 | 608.4-1,129.3 | 16.63 | **no** | `a100_sxm_80gb-x672-hybrid` | 169.6 | 222.1-412.3 | 3.24 | yes | 14.068x | 2.739x | 0.195x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 412.1 | 102.2-189.7 | 17.09 | **no** | `a100_sxm_80gb-x335-hybrid` | 47.4 | 36.9-68.5 | 5.45 | yes | 8.687x | 2.770x | 0.319x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 845.0 | 212.1-393.7 | 16.89 | **no** | `a100_sxm_80gb-x672-hybrid` | 72.3 | 72.8-135.2 | 4.21 | yes | 11.695x | 2.912x | 0.249x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.195x to 0.543x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 15 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 859.7-1,595.7 | 9.12 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 261.4-485.1 | 3.06 | yes | 9.799x | 3.289x | 0.336x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 2,091.7 | 1,806.3-3,352.7 | 4.91 | yes | `a100_sxm_80gb-x336-hybrid` | 190.0 | 262.8-487.8 | 3.06 | yes | 11.011x | 6.873x | 0.624x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 859.7-1,595.7 | 9.12 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 261.4-485.1 | 3.06 | yes | 9.799x | 3.289x | 0.336x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,891.3 | 2,003.5-3,718.7 | 4.00 | yes | `a100_sxm_80gb-x783-hybrid` | 186.9 | 264.6-491.1 | 3.00 | yes | 10.117x | 7.572x | 0.748x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 859.7-1,595.7 | 9.12 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 261.4-485.1 | 3.06 | yes | 9.799x | 3.289x | 0.336x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,891.3 | 2,003.5-3,718.7 | 4.00 | yes | `a100_sxm_80gb-x783-hybrid` | 186.9 | 264.6-491.1 | 3.00 | yes | 10.117x | 7.572x | 0.748x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 859.7-1,595.7 | 9.12 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 261.4-485.1 | 3.06 | yes | 9.799x | 3.289x | 0.336x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,891.3 | 2,003.5-3,718.7 | 4.00 | yes | `a100_sxm_80gb-x783-hybrid` | 186.9 | 264.6-491.1 | 3.00 | yes | 10.117x | 7.572x | 0.748x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 859.7-1,595.7 | 9.12 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 261.4-485.1 | 3.06 | yes | 9.799x | 3.289x | 0.336x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,891.3 | 2,003.5-3,718.7 | 4.00 | yes | `a100_sxm_80gb-x783-hybrid` | 186.9 | 264.6-491.1 | 3.00 | yes | 10.117x | 7.572x | 0.748x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,848.6 | 859.7-1,595.7 | 9.12 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 261.4-485.1 | 3.06 | yes | 9.799x | 3.289x | 0.336x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,847.6 | 1,327.4-2,463.9 | 5.90 | yes | `a100_sxm_80gb-x783-hybrid` | 186.9 | 264.6-491.1 | 3.00 | yes | 9.884x | 5.017x | 0.508x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,737.9 | 527.7-979.5 | 13.96 | **no** | `a100_sxm_80gb-x391-hybrid` | 176.0 | 215.5-400.1 | 3.46 | yes | 9.874x | 2.448x | 0.248x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,715.0 | 1,226.1-2,275.7 | 5.93 | yes | `a100_sxm_80gb-x783-hybrid` | 186.9 | 264.6-491.1 | 3.00 | yes | 9.174x | 4.634x | 0.505x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,116.4 | 242.3-449.7 | 19.54 | **no** | `a100_sxm_80gb-x391-hybrid` | 95.6 | 75.1-139.5 | 5.40 | yes | 11.672x | 3.224x | 0.276x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,024.8 | 389.7-723.4 | 11.15 | **no** | `a100_sxm_80gb-x783-hybrid` | 135.4 | 127.4-236.6 | 4.51 | yes | 7.568x | 3.058x | 0.404x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 403.9 | 80.6-149.7 | 21.24 | **no** | `a100_sxm_80gb-x391-hybrid` | 37.1 | 37.9-70.3 | 4.15 | yes | 10.890x | 2.129x | 0.196x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 364.5 | 101.4-188.2 | 15.24 | **no** | `a100_sxm_80gb-x783-hybrid` | 59.6 | 62.5-116.0 | 4.05 | yes | 6.114x | 1.623x | 0.265x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 110.7 | 25.8-47.9 | 18.17 | **no** | `a100_sxm_80gb-x391-hybrid` | 13.2 | 10.6-19.7 | 5.29 | yes | 8.361x | 2.436x | 0.291x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 99.0 | 56.6-105.0 | 7.41 | yes | `a100_sxm_80gb-x783-hybrid` | 22.1 | 20.7-38.4 | 4.54 | yes | 4.474x | 2.737x | 0.612x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.196x to 0.748x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,987.3 | 1,459.9-2,709.7 | 5.77 | yes | `a100_sxm_80gb-x391-hybrid` | 190.8 | 304.9-565.9 | 2.65 | yes | 10.414x | 4.789x | 0.460x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,220.4 | 2,005.1-3,721.8 | 4.70 | yes | `a100_sxm_80gb-x448-hybrid` | 190.0 | 302.6-561.8 | 2.66 | yes | 11.687x | 6.625x | 0.567x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,987.3 | 1,459.9-2,709.7 | 5.77 | yes | `a100_sxm_80gb-x391-hybrid` | 190.8 | 304.9-565.9 | 2.65 | yes | 10.414x | 4.789x | 0.460x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,220.4 | 2,005.1-3,721.8 | 4.70 | yes | `a100_sxm_80gb-x448-hybrid` | 190.0 | 302.6-561.8 | 2.66 | yes | 11.687x | 6.625x | 0.567x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,987.3 | 1,459.9-2,709.7 | 5.77 | yes | `a100_sxm_80gb-x391-hybrid` | 190.8 | 304.9-565.9 | 2.65 | yes | 10.414x | 4.789x | 0.460x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,220.4 | 2,005.1-3,721.8 | 4.70 | yes | `a100_sxm_80gb-x448-hybrid` | 190.0 | 302.6-561.8 | 2.66 | yes | 11.687x | 6.625x | 0.567x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,987.3 | 1,459.9-2,709.7 | 5.77 | yes | `a100_sxm_80gb-x391-hybrid` | 190.8 | 304.9-565.9 | 2.65 | yes | 10.414x | 4.789x | 0.460x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,220.4 | 2,005.1-3,721.8 | 4.70 | yes | `a100_sxm_80gb-x448-hybrid` | 190.0 | 302.6-561.8 | 2.66 | yes | 11.687x | 6.625x | 0.567x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,987.3 | 1,459.9-2,709.7 | 5.77 | yes | `a100_sxm_80gb-x391-hybrid` | 190.8 | 304.9-565.9 | 2.65 | yes | 10.414x | 4.789x | 0.460x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,220.4 | 2,005.1-3,721.8 | 4.70 | yes | `a100_sxm_80gb-x448-hybrid` | 190.0 | 302.6-561.8 | 2.66 | yes | 11.687x | 6.625x | 0.567x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 1,974.4 | 1,001.2-1,858.4 | 8.36 | **no** | `a100_sxm_80gb-x368-hybrid` | 191.6 | 306.1-568.2 | 2.65 | yes | 10.306x | 3.271x | 0.317x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,213.2 | 2,014.2-3,738.7 | 4.66 | yes | `a100_sxm_80gb-x672-hybrid` | 189.2 | 306.9-569.7 | 2.61 | yes | 11.696x | 6.563x | 0.561x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,859.7 | 587.0-1,089.5 | 13.43 | **no** | `a100_sxm_80gb-x391-hybrid` | 178.9 | 254.7-472.7 | 2.98 | yes | 10.394x | 2.305x | 0.222x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,093.1 | 1,200.1-2,227.6 | 7.39 | yes | `a100_sxm_80gb-x672-hybrid` | 189.2 | 306.9-569.7 | 2.61 | yes | 11.062x | 3.910x | 0.353x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,297.8 | 275.4-511.1 | 19.98 | **no** | `a100_sxm_80gb-x391-hybrid` | 100.6 | 95.6-177.4 | 4.46 | yes | 12.902x | 2.881x | 0.223x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,632.0 | 543.7-1,009.1 | 12.73 | **no** | `a100_sxm_80gb-x672-hybrid` | 130.8 | 137.5-255.3 | 4.03 | yes | 12.476x | 3.953x | 0.317x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 505.5 | 96.1-178.4 | 22.30 | **no** | `a100_sxm_80gb-x391-hybrid` | 38.4 | 30.1-55.8 | 5.41 | yes | 13.180x | 3.198x | 0.243x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 893.2 | 240.5-446.4 | 15.75 | **no** | `a100_sxm_80gb-x672-hybrid` | 56.1 | 46.0-85.3 | 5.18 | yes | 15.911x | 5.232x | 0.329x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 142.2 | 32.6-60.5 | 18.50 | **no** | `a100_sxm_80gb-x391-hybrid` | 14.5 | 7.7-14.3 | 7.98 | **no** | 9.822x | 4.237x | 0.431x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 333.4 | 77.2-143.2 | 18.32 | **no** | `a100_sxm_80gb-x672-hybrid` | 20.3 | 25.3-47.0 | 3.39 | yes | 16.456x | 3.048x | 0.185x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.185x to 0.567x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 12 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 1,027.7-1,907.6 | 8.56 | **no** | `a100_sxm_80gb-x361-hybrid` | 189.8 | 305.2-566.5 | 2.64 | yes | 10.928x | 3.367x | 0.308x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,266.7 | 2,060.0-3,823.6 | 4.67 | yes | `a100_sxm_80gb-x336-hybrid` | 192.4 | 309.6-574.6 | 2.63 | yes | 11.784x | 6.654x | 0.565x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 1,027.7-1,907.6 | 8.56 | **no** | `a100_sxm_80gb-x361-hybrid` | 189.8 | 305.2-566.5 | 2.64 | yes | 10.928x | 3.367x | 0.308x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,266.7 | 2,060.0-3,823.6 | 4.67 | yes | `a100_sxm_80gb-x336-hybrid` | 192.4 | 309.6-574.6 | 2.63 | yes | 11.784x | 6.654x | 0.565x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 1,027.7-1,907.6 | 8.56 | **no** | `a100_sxm_80gb-x361-hybrid` | 189.8 | 305.2-566.5 | 2.64 | yes | 10.928x | 3.367x | 0.308x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,266.7 | 2,060.0-3,823.6 | 4.67 | yes | `a100_sxm_80gb-x336-hybrid` | 192.4 | 309.6-574.6 | 2.63 | yes | 11.784x | 6.654x | 0.565x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 1,027.7-1,907.6 | 8.56 | **no** | `a100_sxm_80gb-x361-hybrid` | 189.8 | 305.2-566.5 | 2.64 | yes | 10.928x | 3.367x | 0.308x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,266.7 | 2,060.0-3,823.6 | 4.67 | yes | `a100_sxm_80gb-x336-hybrid` | 192.4 | 309.6-574.6 | 2.63 | yes | 11.784x | 6.654x | 0.565x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 1,027.7-1,907.6 | 8.56 | **no** | `a100_sxm_80gb-x361-hybrid` | 189.8 | 305.2-566.5 | 2.64 | yes | 10.928x | 3.367x | 0.308x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,266.7 | 2,060.0-3,823.6 | 4.67 | yes | `a100_sxm_80gb-x336-hybrid` | 192.4 | 309.6-574.6 | 2.63 | yes | 11.784x | 6.654x | 0.565x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 2,073.7 | 1,027.7-1,907.6 | 8.56 | **no** | `a100_sxm_80gb-x361-hybrid` | 189.8 | 305.2-566.5 | 2.64 | yes | 10.928x | 3.367x | 0.308x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,257.9 | 2,081.4-3,863.3 | 4.60 | yes | `a100_sxm_80gb-x672-hybrid` | 189.4 | 311.5-578.2 | 2.58 | yes | 11.924x | 6.682x | 0.560x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,948.6 | 897.7-1,666.3 | 9.20 | **no** | `a100_sxm_80gb-x391-hybrid` | 179.1 | 258.0-479.0 | 2.94 | yes | 10.880x | 3.479x | 0.320x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,220.5 | 1,236.1-2,294.4 | 7.62 | yes | `a100_sxm_80gb-x672-hybrid` | 189.4 | 311.5-578.2 | 2.58 | yes | 11.726x | 3.968x | 0.338x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,330.3 | 281.0-521.6 | 20.07 | **no** | `a100_sxm_80gb-x391-hybrid` | 100.8 | 99.2-184.0 | 4.31 | yes | 13.197x | 2.834x | 0.215x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,714.1 | 559.6-1,038.6 | 12.99 | **no** | `a100_sxm_80gb-x672-hybrid` | 131.0 | 141.8-263.2 | 3.92 | yes | 13.083x | 3.946x | 0.302x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 525.1 | 98.9-183.6 | 22.51 | **no** | `a100_sxm_80gb-x391-hybrid` | 38.5 | 32.0-59.4 | 5.10 | yes | 13.646x | 3.091x | 0.227x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 950.4 | 284.4-527.8 | 14.17 | **no** | `a100_sxm_80gb-x672-hybrid` | 56.3 | 47.9-88.9 | 4.98 | yes | 16.882x | 5.935x | 0.352x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 148.5 | 33.9-63.0 | 18.56 | **no** | `a100_sxm_80gb-x391-hybrid` | 14.5 | 8.3-15.4 | 7.46 | yes | 10.208x | 4.101x | 0.402x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 365.5 | 89.3-165.8 | 17.35 | **no** | `a100_sxm_80gb-x672-hybrid` | 20.3 | 26.8-49.7 | 3.22 | yes | 17.970x | 3.337x | 0.186x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.186x to 0.565x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 10,692.4 | 9,204.1-17,084.0 | 4.93 | yes | `b200_sxm-x8-tensor` | 1,501.9 | 5,185.9-9,625.7 | 1.23 | yes | 7.119x | 1.775x | 0.249x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 9,245.0 | 13,725.9-25,477.0 | 2.86 | yes | `b200_sxm-x29-nvl72-tensor` | 2,284.3 | 7,716.0-14,321.9 | 1.26 | yes | 4.047x | 1.779x | 0.440x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 9,796.1 | 8,613.4-15,987.6 | 4.82 | yes | `b200_sxm-x32-nvl72-tensor` | 2,283.2 | 7,126.8-13,228.3 | 1.36 | yes | 4.291x | 1.209x | 0.282x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 7,483.5 | 13,173.6-24,451.9 | 2.41 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,493.8 | 8,279.5-15,367.9 | 1.28 | yes | 3.001x | 1.591x | 0.530x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 9,796.1 | 8,613.4-15,987.6 | 4.82 | yes | `b200_sxm-x32-nvl72-tensor` | 2,199.2 | 6,014.6-11,163.9 | 1.55 | yes | 4.454x | 1.432x | 0.321x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 7,483.5 | 13,173.6-24,451.9 | 2.41 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,481.1 | 7,970.6-14,794.4 | 1.32 | yes | 3.016x | 1.653x | 0.548x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 9,712.9 | 8,548.2-15,866.7 | 4.82 | yes | `b200_sxm-x87-nvl72-hybrid` | 2,303.4 | 6,092.6-11,308.6 | 1.60 | yes | 4.217x | 1.403x | 0.333x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 7,471.7 | 13,155.6-24,418.6 | 2.41 | yes | `b200_sxm-x231-nvl72-hybrid` | 2,442.5 | 7,307.4-13,563.6 | 1.42 | yes | 3.059x | 1.800x | 0.589x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9,591.7 | 8,460.7-15,704.3 | 4.81 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,338.6 | 5,505.4-10,218.8 | 1.80 | yes | 4.101x | 1.537x | 0.375x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6,532.0 | 11,798.3-21,899.3 | 2.35 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,432.9 | 6,441.0-11,955.3 | 1.60 | yes | 2.685x | 1.832x | 0.682x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8,722.7 | 6,248.1-11,597.4 | 5.92 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,172.2 | 3,896.3-7,232.1 | 2.36 | yes | 4.016x | 1.604x | 0.399x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,236.0 | 8,750.0-16,241.2 | 2.54 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,325.6 | 4,886.7-9,070.3 | 2.02 | yes | 2.251x | 1.791x | 0.795x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7,119.0 | 4,249.0-7,886.8 | 7.10 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,901.6 | 2,447.6-4,543.0 | 3.29 | yes | 3.744x | 1.736x | 0.464x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,678.1 | 6,704.9-12,445.1 | 2.33 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,137.1 | 3,291.1-6,108.8 | 2.75 | yes | 1.721x | 2.037x | 1.184x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,148.4 | 1,396.2-2,591.5 | 9.56 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,192.8 | 1,313.5-2,438.0 | 3.85 | yes | 2.639x | 1.063x | 0.403x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,238.5 | 2,801.9-5,200.6 | 1.87 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,521.5 | 1,928.2-3,579.1 | 3.35 | yes | 0.814x | 1.453x | 1.785x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 801.0 | 345.8-641.9 | 9.82 | **no** | `b200_sxm-x173-nvl72-hybrid` | 531.3 | 587.2-1,090.0 | 3.84 | yes | 1.507x | 0.589x | 0.391x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 331.2 | 822.4-1,526.4 | 1.71 | yes | `b200_sxm-x347-nvl72-hybrid` | 808.3 | 972.7-1,805.4 | 3.52 | yes | 0.410x | 0.845x | 2.063x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 201.1 | 84.2-156.3 | 10.13 | **no** | `b200_sxm-x173-nvl72-hybrid` | 178.3 | 247.7-459.7 | 3.05 | yes | 1.128x | 0.340x | 0.301x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 84.0 | 203.7-378.0 | 1.75 | yes | `b200_sxm-x347-nvl72-hybrid` | 314.7 | 456.2-846.8 | 2.92 | yes | 0.267x | 0.446x | 1.672x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 4,202.4 | 2,496.4-4,633.6 | 7.14 | yes | `b200_sxm-x29-nvl72-tensor` | 846.3 | 1,689.6-3,136.1 | 2.12 | yes | 4.966x | 1.478x | 0.298x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3,943.5 | 3,268.7-6,067.2 | 5.12 | yes | `b200_sxm-x58-nvl72-tensor` | 862.2 | 1,717.2-3,187.3 | 2.13 | yes | 4.574x | 1.904x | 0.416x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 4,142.4 | 2,407.2-4,468.1 | 7.30 | yes | `b200_sxm-x31-hybrid` | 818.6 | 1,481.1-2,749.1 | 2.34 | yes | 5.061x | 1.625x | 0.321x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,601.2 | 4,731.7-8,782.6 | 3.23 | yes | `b200_sxm-x202-nvl72-hybrid` | 858.2 | 1,695.3-3,146.6 | 2.15 | yes | 4.196x | 2.791x | 0.665x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 4,142.4 | 2,407.2-4,468.1 | 7.30 | yes | `b200_sxm-x31-hybrid` | 818.6 | 1,481.1-2,749.1 | 2.34 | yes | 5.061x | 1.625x | 0.321x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,601.2 | 4,731.7-8,782.6 | 3.23 | yes | `b200_sxm-x202-nvl72-hybrid` | 851.5 | 1,682.4-3,122.7 | 2.15 | yes | 4.229x | 2.812x | 0.665x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 4,142.4 | 2,407.2-4,468.1 | 7.30 | yes | `b200_sxm-x31-hybrid` | 747.5 | 1,024.5-1,901.5 | 3.09 | yes | 5.542x | 2.350x | 0.424x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,601.2 | 4,731.7-8,782.6 | 3.23 | yes | `b200_sxm-x202-nvl72-hybrid` | 828.3 | 1,577.0-2,927.1 | 2.23 | yes | 4.348x | 3.000x | 0.690x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x61` | 4,118.7 | 2,327.2-4,319.5 | 7.50 | yes | `b200_sxm-x31-hybrid` | 638.5 | 648.7-1,204.1 | 4.17 | yes | 6.451x | 3.587x | 0.556x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,601.2 | 4,731.7-8,782.6 | 3.23 | yes | `b200_sxm-x202-nvl72-hybrid` | 802.0 | 1,583.7-2,939.6 | 2.15 | yes | 4.490x | 2.988x | 0.665x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 3,916.7 | 2,279.5-4,231.1 | 7.29 | yes | `b200_sxm-x86-nvl72-hybrid` | 692.8 | 854.6-1,586.2 | 3.44 | yes | 5.653x | 2.667x | 0.472x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,571.7 | 4,698.5-8,721.0 | 3.22 | yes | `b200_sxm-x347-nvl72-hybrid` | 788.7 | 1,580.9-2,934.4 | 2.12 | yes | 4.529x | 2.972x | 0.656x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,914.0 | 2,277.7-4,227.7 | 7.29 | yes | `b200_sxm-x173-nvl72-hybrid` | 685.6 | 860.8-1,597.7 | 3.38 | yes | 5.709x | 2.646x | 0.464x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,458.0 | 3,582.2-6,649.1 | 4.09 | yes | `b200_sxm-x347-nvl72-hybrid` | 756.8 | 1,302.8-2,418.2 | 2.46 | yes | 4.569x | 2.750x | 0.602x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,667.9 | 965.9-1,792.8 | 11.71 | **no** | `b200_sxm-x173-nvl72-hybrid` | 443.8 | 493.2-915.5 | 3.81 | yes | 6.012x | 1.958x | 0.326x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,439.2 | 1,785.7-3,314.4 | 5.79 | yes | `b200_sxm-x347-nvl72-hybrid` | 564.1 | 793.7-1,473.1 | 3.01 | yes | 4.324x | 2.250x | 0.520x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,133.1 | 294.3-546.2 | 16.33 | **no** | `b200_sxm-x173-nvl72-hybrid` | 217.7 | 292.1-542.3 | 3.16 | yes | 5.204x | 1.007x | 0.194x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,035.3 | 562.3-1,043.7 | 7.81 | yes | `b200_sxm-x347-nvl72-hybrid` | 320.0 | 354.3-657.6 | 3.83 | yes | 3.235x | 1.587x | 0.491x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 344.6 | 113.1-209.9 | 12.92 | **no** | `b200_sxm-x173-nvl72-hybrid` | 91.1 | 108.3-201.0 | 3.57 | yes | 3.784x | 1.044x | 0.276x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 298.0 | 199.5-370.2 | 6.33 | yes | `b200_sxm-x347-nvl72-hybrid` | 140.2 | 186.2-345.6 | 3.19 | yes | 2.125x | 1.071x | 0.504x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340` | 1,581.9 | 665.3-1,234.9 | 10.08 | **no** | `b200_sxm-x173-nvl72-hybrid` | 509.0 | 515.6-957.0 | 4.19 | yes | 3.108x | 1.290x | 0.415x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 2,052.1 | 1,675.1-3,109.2 | 5.19 | yes | `b200_sxm-x173-nvl72-hybrid` | 509.0 | 515.6-957.0 | 4.19 | yes | 4.032x | 3.249x | 0.806x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,575.6 | 639.2-1,186.5 | 10.45 | **no** | `b200_sxm-x203-nvl72-hybrid` | 511.9 | 515.4-956.6 | 4.21 | yes | 3.078x | 1.240x | 0.403x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,678.4 | 1,396.3-2,591.8 | 5.10 | yes | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 497.1-922.7 | 4.26 | yes | 3.357x | 2.809x | 0.837x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,575.6 | 639.2-1,186.5 | 10.45 | **no** | `b200_sxm-x203-nvl72-hybrid` | 504.9 | 512.4-951.1 | 4.18 | yes | 3.121x | 1.247x | 0.400x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,678.4 | 1,396.3-2,591.8 | 5.10 | yes | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 497.1-922.7 | 4.26 | yes | 3.357x | 2.809x | 0.837x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,575.6 | 639.2-1,186.5 | 10.45 | **no** | `b200_sxm-x203-nvl72-hybrid` | 486.0 | 511.5-949.4 | 4.03 | yes | 3.242x | 1.250x | 0.385x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,678.4 | 1,396.3-2,591.8 | 5.10 | yes | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 497.1-922.7 | 4.26 | yes | 3.357x | 2.809x | 0.837x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,575.6 | 639.2-1,186.5 | 10.45 | **no** | `b200_sxm-x203-nvl72-hybrid` | 463.0 | 434.9-807.3 | 4.51 | yes | 3.403x | 1.470x | 0.432x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,678.4 | 1,396.3-2,591.8 | 5.10 | yes | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 497.1-922.7 | 4.26 | yes | 3.357x | 2.809x | 0.837x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,575.6 | 639.2-1,186.5 | 10.45 | **no** | `b200_sxm-x203-nvl72-hybrid` | 395.7 | 409.6-760.2 | 4.10 | yes | 3.982x | 1.561x | 0.392x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,678.4 | 1,396.3-2,591.8 | 5.10 | yes | `b200_sxm-x1358-nvl72-hybrid` | 472.8 | 496.6-921.8 | 4.04 | yes | 3.550x | 2.812x | 0.792x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,568.9 | 466.9-866.7 | 14.25 | **no** | `b200_sxm-x203-nvl72-hybrid` | 312.7 | 236.2-438.4 | 5.61 | yes | 5.017x | 1.977x | 0.394x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,654.7 | 2,119.4-3,933.8 | 3.31 | yes | `b200_sxm-x1358-nvl72-hybrid` | 468.8 | 506.6-940.3 | 3.92 | yes | 3.530x | 4.184x | 1.185x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 958.0 | 211.6-392.7 | 19.20 | **no** | `b200_sxm-x203-nvl72-hybrid` | 165.5 | 124.9-231.7 | 5.62 | yes | 5.787x | 1.694x | 0.293x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,301.3 | 507.4-941.7 | 10.87 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 368.5 | 366.7-680.6 | 4.26 | yes | 3.531x | 1.384x | 0.392x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 339.6 | 69.8-129.6 | 20.62 | **no** | `b200_sxm-x203-nvl72-hybrid` | 67.5 | 61.8-114.7 | 4.63 | yes | 5.035x | 1.130x | 0.224x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 568.5 | 140.9-261.6 | 17.10 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 218.5 | 201.7-374.4 | 4.59 | yes | 2.602x | 0.699x | 0.268x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 92.0 | 21.7-40.3 | 17.99 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 168.7 | 35.7-66.3 | 20.02 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 97.4 | 73.1-135.6 | 5.65 | yes | 1.731x | 0.489x | 0.282x |

**Does the ratio compress?** Of 59 class rows in this study, 54 move the ROM-versus-GPU ratio DOWN under speculation and 5 move it UP. The movement spans 0.194x to 2.063x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 41 of 60 ROM rows and 59 of 60 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 10,396.4 | 8,141.4-15,111.5 | 5.41 | yes | `a100_sxm_80gb-x16-hybrid` | 559.8 | 1,897.6-3,522.1 | 1.25 | yes | 18.572x | 4.290x | 0.231x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 9,289.5 | 13,151.8-24,411.5 | 2.99 | yes | `a100_sxm_80gb-x56-tensor` | 682.2 | 1,245.6-2,312.0 | 2.32 | yes | 13.617x | 10.559x | 0.775x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8,012.3 | 8,190.2-15,202.1 | 4.15 | yes | `a100_sxm_80gb-x272-tensor` | 692.4 | 772.8-1,434.5 | 3.80 | yes | 11.572x | 10.597x | 0.916x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,951.9 | 11,752.9-21,814.9 | 2.15 | yes | `a100_sxm_80gb-x448-hybrid` | 684.2 | 1,223.8-2,271.6 | 2.37 | yes | 8.699x | 9.603x | 1.104x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8,012.3 | 8,190.2-15,202.1 | 4.15 | yes | `a100_sxm_80gb-x272-hybrid` | 673.8 | 1,218.5-2,261.6 | 2.34 | yes | 11.892x | 6.722x | 0.565x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,537.5 | 11,497.8-21,341.5 | 2.04 | yes | `a100_sxm_80gb-x448-hybrid` | 684.2 | 1,223.8-2,271.6 | 2.37 | yes | 8.094x | 9.395x | 1.161x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8,012.3 | 8,190.2-15,202.1 | 4.15 | yes | `a100_sxm_80gb-x272-hybrid` | 644.8 | 917.3-1,702.7 | 2.98 | yes | 12.426x | 8.928x | 0.719x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,459.7 | 11,683.6-21,686.4 | 1.98 | yes | `a100_sxm_80gb-x448-hybrid` | 676.9 | 1,134.3-2,105.4 | 2.53 | yes | 8.065x | 10.300x | 1.277x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 7,650.1 | 7,136.0-13,245.4 | 4.55 | yes | `a100_sxm_80gb-x272-hybrid` | 583.5 | 884.9-1,642.6 | 2.80 | yes | 13.112x | 8.064x | 0.615x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,524.5 | 9,342.0-17,340.0 | 2.05 | yes | `a100_sxm_80gb-x672-hybrid` | 654.0 | 965.8-1,792.7 | 2.87 | yes | 6.918x | 9.673x | 1.398x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,230.8 | 4,987.3-9,257.2 | 5.30 | yes | `a100_sxm_80gb-x335-hybrid` | 542.6 | 626.7-1,163.2 | 3.67 | yes | 11.484x | 7.959x | 0.693x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,092.1 | 7,150.0-13,271.4 | 1.83 | yes | `a100_sxm_80gb-x672-hybrid` | 591.2 | 587.8-1,091.1 | 4.26 | yes | 5.230x | 12.163x | 2.326x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,555.8 | 3,357.0-6,231.0 | 5.75 | yes | `a100_sxm_80gb-x335-hybrid` | 518.7 | 1,532.1-2,843.8 | 1.44 | yes | 8.783x | 2.191x | 0.249x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,856.2 | 4,992.6-9,266.9 | 1.58 | yes | `a100_sxm_80gb-x672-hybrid` | 535.7 | 1,676.7-3,112.2 | 1.35 | yes | 3.465x | 2.978x | 0.859x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,594.7 | 1,040.2-1,930.7 | 6.50 | yes | `a100_sxm_80gb-x335-hybrid` | 411.4 | 876.5-1,626.8 | 1.99 | yes | 3.877x | 1.187x | 0.306x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 531.7 | 1,780.8-3,305.5 | 1.27 | yes | `a100_sxm_80gb-x672-hybrid` | 478.2 | 1,231.2-2,285.2 | 1.65 | yes | 1.112x | 1.446x | 1.301x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 431.0 | 266.0-493.7 | 6.87 | yes | `a100_sxm_80gb-x335-hybrid` | 225.0 | 273.2-507.1 | 3.49 | yes | 1.915x | 0.974x | 0.508x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 136.7 | 491.4-912.1 | 1.18 | yes | `a100_sxm_80gb-x672-hybrid` | 323.1 | 523.6-971.8 | 2.62 | yes | 0.423x | 0.939x | 2.219x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 111.0 | 128.8-239.0 | 3.65 | yes | `a100_sxm_80gb-x335-hybrid` | 80.4 | 115.7-214.8 | 2.94 | yes | 1.381x | 1.113x | 0.806x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 34.4 | 72.7-134.9 | 2.00 | yes | `a100_sxm_80gb-x672-hybrid` | 140.6 | 139.9-259.7 | 4.26 | yes | 0.244x | 0.520x | 2.126x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | 3,949.8 | 1,945.6-3,611.3 | 8.61 | **no** | `a100_sxm_80gb-x79-hybrid` | 398.0 | 568.4-1,055.1 | 2.97 | yes | 9.923x | 3.423x | 0.345x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 3,943.5 | 3,062.8-5,685.0 | 5.46 | yes | `a100_sxm_80gb-x112-hybrid` | 397.4 | 574.9-1,067.2 | 2.93 | yes | 9.923x | 5.327x | 0.537x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,844.6 | 1,813.2-3,365.6 | 8.99 | **no** | `a100_sxm_80gb-x85-hybrid` | 394.9 | 564.7-1,048.2 | 2.96 | yes | 9.737x | 3.211x | 0.330x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,238.6 | 3,116.1-5,783.9 | 4.41 | yes | `a100_sxm_80gb-x560-hybrid` | 382.7 | 563.4-1,045.8 | 2.88 | yes | 8.463x | 5.530x | 0.653x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,844.6 | 1,813.2-3,365.6 | 8.99 | **no** | `a100_sxm_80gb-x85-hybrid` | 394.9 | 564.7-1,048.2 | 2.96 | yes | 9.737x | 3.211x | 0.330x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,238.6 | 3,116.1-5,783.9 | 4.41 | yes | `a100_sxm_80gb-x560-hybrid` | 382.7 | 563.4-1,045.8 | 2.88 | yes | 8.463x | 5.530x | 0.653x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,844.6 | 1,813.2-3,365.6 | 8.99 | **no** | `a100_sxm_80gb-x85-hybrid` | 394.9 | 564.7-1,048.2 | 2.96 | yes | 9.737x | 3.211x | 0.330x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,238.6 | 3,116.1-5,783.9 | 4.41 | yes | `a100_sxm_80gb-x560-hybrid` | 382.7 | 563.4-1,045.8 | 2.88 | yes | 8.463x | 5.530x | 0.653x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,844.6 | 1,813.2-3,365.6 | 8.99 | **no** | `a100_sxm_80gb-x85-hybrid` | 367.4 | 450.9-836.9 | 3.46 | yes | 10.464x | 4.022x | 0.384x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,238.6 | 3,116.1-5,783.9 | 4.41 | yes | `a100_sxm_80gb-x560-hybrid` | 382.7 | 563.4-1,045.8 | 2.88 | yes | 8.463x | 5.530x | 0.653x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 3,628.0 | 1,775.0-3,294.6 | 8.67 | **no** | `a100_sxm_80gb-x312-hybrid` | 384.6 | 556.6-1,033.2 | 2.93 | yes | 9.432x | 3.189x | 0.338x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,106.7 | 2,051.7-3,808.2 | 6.42 | yes | `a100_sxm_80gb-x560-hybrid` | 382.7 | 563.4-1,045.8 | 2.88 | yes | 8.118x | 3.641x | 0.449x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 3,628.0 | 1,775.0-3,294.6 | 8.67 | **no** | `a100_sxm_80gb-x312-hybrid` | 346.7 | 397.5-737.8 | 3.70 | yes | 10.465x | 4.465x | 0.427x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,774.5 | 1,654.9-3,071.7 | 7.11 | yes | `a100_sxm_80gb-x672-hybrid` | 382.7 | 566.6-1,051.6 | 2.86 | yes | 7.250x | 2.921x | 0.403x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,291.5 | 729.5-1,354.1 | 13.32 | **no** | `a100_sxm_80gb-x335-hybrid` | 215.7 | 239.4-444.3 | 3.82 | yes | 10.625x | 3.048x | 0.287x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,464.3 | 822.0-1,525.7 | 7.55 | yes | `a100_sxm_80gb-x672-hybrid` | 283.6 | 250.7-465.4 | 4.80 | yes | 5.163x | 3.278x | 0.635x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 883.5 | 218.8-406.1 | 17.12 | **no** | `a100_sxm_80gb-x335-hybrid` | 99.1 | 78.0-144.8 | 5.39 | yes | 8.915x | 2.805x | 0.315x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 480.3 | 245.3-455.4 | 8.30 | **no** | `a100_sxm_80gb-x672-hybrid` | 153.9 | 149.4-277.3 | 4.37 | yes | 3.121x | 1.642x | 0.526x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 313.9 | 88.0-163.3 | 15.13 | **no** | `a100_sxm_80gb-x335-hybrid` | 38.2 | 37.7-70.0 | 4.30 | yes | 8.211x | 2.335x | 0.284x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 128.2 | 101.5-188.4 | 5.35 | yes | `a100_sxm_80gb-x672-hybrid` | 61.8 | 72.5-134.5 | 3.61 | yes | 2.075x | 1.401x | 0.675x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 1,467.1 | 700.2-1,299.7 | 8.88 | **no** | `a100_sxm_80gb-x384-hybrid` | 166.7 | 157.1-291.7 | 4.50 | yes | 8.802x | 4.456x | 0.506x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 1,978.5 | 1,335.0-2,477.9 | 6.28 | yes | `a100_sxm_80gb-x504-hybrid` | 165.1 | 155.8-289.3 | 4.49 | yes | 11.982x | 8.566x | 0.715x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 1,103.0-2,047.3 | 5.75 | yes | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 165.1-306.5 | 4.24 | yes | 9.061x | 6.680x | 0.737x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 1,103.0-2,047.3 | 5.75 | yes | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 165.1-306.5 | 4.24 | yes | 9.061x | 6.680x | 0.737x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 1,103.0-2,047.3 | 5.75 | yes | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 165.1-306.5 | 4.24 | yes | 9.061x | 6.680x | 0.737x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 1,103.0-2,047.3 | 5.75 | yes | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 165.1-306.5 | 4.24 | yes | 9.061x | 6.680x | 0.737x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 1,103.0-2,047.3 | 5.75 | yes | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 165.1-306.5 | 4.24 | yes | 9.061x | 6.680x | 0.737x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,495.8 | 1,103.0-2,047.3 | 5.75 | yes | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 165.1-306.5 | 4.24 | yes | 9.061x | 6.680x | 0.737x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 989.0 | 395.1-733.4 | 10.61 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 165.1-306.5 | 4.24 | yes | 5.991x | 2.393x | 0.399x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 361.2 | 104.9-194.7 | 14.60 | **no** | `a100_sxm_80gb-x3694-hybrid` | 118.2 | 82.3-152.7 | 6.09 | yes | 3.055x | 1.275x | 0.417x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 100.3 | 26.4-49.1 | 16.08 | **no** | `a100_sxm_80gb-x3694-hybrid` | 54.9 | 41.6-77.3 | 5.59 | yes | 1.828x | 0.635x | 0.348x |

**Does the ratio compress?** Of 51 class rows in this study, 43 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.231x to 2.326x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 36 of 51 ROM rows and 51 of 51 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 12,043.2 | 7,541.3-13,997.7 | 6.77 | yes | `b200_sxm-x2-tensor` | 1,328.0 | 4,760.3-8,835.8 | 1.18 | yes | 9.069x | 1.584x | 0.175x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 9,137.9 | 14,967.9-27,782.5 | 2.59 | yes | `b200_sxm-x29-nvl72-tensor` | 2,641.2 | 8,871.2-16,466.1 | 1.26 | yes | 3.460x | 1.687x | 0.488x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 9,519.0 | 10,591.7-19,659.5 | 3.81 | yes | `b200_sxm-x32-nvl72-tensor` | 2,601.6 | 7,998.6-14,846.5 | 1.38 | yes | 3.659x | 1.324x | 0.362x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 7,387.4 | 13,922.2-25,841.5 | 2.25 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,693.6 | 8,905.3-16,529.4 | 1.28 | yes | 2.743x | 1.563x | 0.570x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 9,519.0 | 10,591.7-19,659.5 | 3.81 | yes | `b200_sxm-x32-nvl72-tensor` | 2,493.1 | 6,624.0-12,294.9 | 1.60 | yes | 3.818x | 1.599x | 0.419x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 7,387.4 | 13,922.2-25,841.5 | 2.25 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,678.9 | 8,548.9-15,867.9 | 1.33 | yes | 2.758x | 1.629x | 0.591x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x170-romfill` | 9,440.2 | 10,500.5-19,490.3 | 3.81 | yes | `b200_sxm-x87-nvl72-hybrid` | 2,533.6 | 6,541.0-12,140.9 | 1.64 | yes | 3.726x | 1.605x | 0.431x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 7,375.9 | 13,902.2-25,804.3 | 2.25 | yes | `b200_sxm-x231-nvl72-hybrid` | 2,633.5 | 7,789.9-14,459.0 | 1.43 | yes | 2.801x | 1.785x | 0.637x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 9,325.7 | 10,368.8-19,245.8 | 3.81 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,513.5 | 5,775.3-10,719.7 | 1.85 | yes | 3.710x | 1.795x | 0.484x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 6,402.3 | 12,929.4-23,998.6 | 2.10 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,588.6 | 6,747.5-12,524.2 | 1.63 | yes | 2.473x | 1.916x | 0.775x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 8,516.1 | 9,018.6-16,739.7 | 4.00 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,328.9 | 5,527.0-10,258.8 | 1.79 | yes | 3.657x | 1.632x | 0.446x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 5,147.2 | 9,722.1-18,045.6 | 2.24 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,467.4 | 5,061.1-9,394.0 | 2.07 | yes | 2.086x | 1.921x | 0.921x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 6,884.7 | 6,829.3-12,676.2 | 4.27 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,086.3 | 3,846.1-7,138.8 | 2.30 | yes | 3.300x | 1.776x | 0.538x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,595.4 | 7,913.0-14,687.6 | 1.93 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,271.2 | 4,935.6-9,161.1 | 1.95 | yes | 1.583x | 1.603x | 1.013x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3,271.6 | 2,892.6-5,369.0 | 4.80 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,340.8 | 2,074.8-3,851.0 | 2.74 | yes | 2.440x | 1.394x | 0.571x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,227.3 | 3,776.4-7,009.4 | 1.38 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,676.9 | 3,043.3-5,648.7 | 2.34 | yes | 0.732x | 1.241x | 1.695x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 832.2 | 723.9-1,343.6 | 4.87 | yes | `b200_sxm-x173-nvl72-hybrid` | 591.8 | 1,001.4-1,858.8 | 2.51 | yes | 1.406x | 0.723x | 0.514x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 331.1 | 1,197.2-2,222.2 | 1.17 | yes | `b200_sxm-x347-nvl72-hybrid` | 913.1 | 1,684.9-3,127.5 | 2.30 | yes | 0.363x | 0.711x | 1.960x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 208.3 | 180.9-335.8 | 4.88 | yes | `b200_sxm-x173-nvl72-hybrid` | 192.6 | 431.3-800.5 | 1.89 | yes | 1.081x | 0.419x | 0.388x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 84.0 | 208.4-386.9 | 1.71 | yes | `b200_sxm-x347-nvl72-hybrid` | 349.1 | 810.1-1,503.6 | 1.83 | yes | 0.241x | 0.257x | 1.070x |

**Does the ratio compress?** Of 20 class rows in this study, 16 move the ROM-versus-GPU ratio DOWN under speculation and 4 move it UP. The movement spans 0.175x to 1.960x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 20 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x8-romfill` | 11,594.0 | 9,277.3-17,219.9 | 5.30 | yes | `a100_sxm_80gb-x8-tensor` | 1,063.1 | 3,516.5-6,527.1 | 1.28 | yes | 10.906x | 2.638x | 0.242x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 9,155.9 | 14,641.5-27,176.6 | 2.65 | yes | `a100_sxm_80gb-x56-hybrid` | 1,045.1 | 3,365.1-6,246.0 | 1.32 | yes | 8.761x | 4.351x | 0.497x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,820.6 | 9,602.8-17,824.1 | 3.45 | yes | `a100_sxm_80gb-x272-hybrid` | 979.9 | 2,838.6-5,268.7 | 1.46 | yes | 7.981x | 3.383x | 0.424x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,928.2 | 11,804.6-21,911.0 | 2.13 | yes | `a100_sxm_80gb-x448-hybrid` | 975.4 | 2,806.0-5,208.4 | 1.47 | yes | 6.078x | 4.207x | 0.692x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,820.6 | 9,602.8-17,824.1 | 3.45 | yes | `a100_sxm_80gb-x272-hybrid` | 979.9 | 2,838.6-5,268.7 | 1.46 | yes | 7.981x | 3.383x | 0.424x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,498.6 | 11,597.6-21,526.7 | 2.01 | yes | `a100_sxm_80gb-x448-hybrid` | 975.4 | 2,806.0-5,208.4 | 1.47 | yes | 5.637x | 4.133x | 0.733x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,820.6 | 9,602.8-17,824.1 | 3.45 | yes | `a100_sxm_80gb-x272-hybrid` | 979.9 | 2,838.6-5,268.7 | 1.46 | yes | 7.981x | 3.383x | 0.424x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,385.8 | 11,892.1-22,073.3 | 1.92 | yes | `a100_sxm_80gb-x448-hybrid` | 975.4 | 2,806.0-5,208.4 | 1.47 | yes | 5.522x | 4.238x | 0.768x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,461.6 | 9,618.8-17,853.7 | 3.29 | yes | `a100_sxm_80gb-x272-hybrid` | 979.9 | 2,838.6-5,268.7 | 1.46 | yes | 7.615x | 3.389x | 0.445x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 4,472.2 | 9,538.3-17,704.3 | 1.99 | yes | `a100_sxm_80gb-x672-hybrid` | 975.4 | 2,806.0-5,208.4 | 1.47 | yes | 4.585x | 3.399x | 0.741x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 5,990.2 | 6,954.8-12,909.0 | 3.65 | yes | `a100_sxm_80gb-x335-hybrid` | 974.3 | 2,803.5-5,203.6 | 1.47 | yes | 6.148x | 2.481x | 0.403x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,047.9 | 7,388.8-13,714.5 | 1.75 | yes | `a100_sxm_80gb-x672-hybrid` | 975.4 | 2,806.0-5,208.4 | 1.47 | yes | 3.125x | 2.633x | 0.843x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4,417.1 | 5,504.7-10,217.4 | 3.40 | yes | `a100_sxm_80gb-x335-hybrid` | 922.5 | 2,423.7-4,498.7 | 1.61 | yes | 4.788x | 2.271x | 0.474x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,832.2 | 5,225.9-9,700.0 | 1.49 | yes | `a100_sxm_80gb-x672-hybrid` | 975.4 | 2,806.0-5,208.4 | 1.47 | yes | 1.878x | 1.862x | 0.991x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 1,587.4 | 2,299.9-4,268.9 | 2.93 | yes | `a100_sxm_80gb-x335-hybrid` | 630.0 | 963.2-1,787.9 | 2.77 | yes | 2.519x | 2.388x | 0.948x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 529.8 | 1,905.7-3,537.3 | 1.18 | yes | `a100_sxm_80gb-x672-hybrid` | 800.0 | 1,664.9-3,090.4 | 2.04 | yes | 0.662x | 1.145x | 1.728x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 430.0 | 633.7-1,176.2 | 2.88 | yes | `a100_sxm_80gb-x335-hybrid` | 277.8 | 273.2-507.1 | 4.31 | yes | 1.548x | 2.319x | 1.499x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 136.7 | 533.3-989.9 | 1.09 | yes | `a100_sxm_80gb-x672-hybrid` | 443.7 | 523.6-971.8 | 3.59 | yes | 0.308x | 1.019x | 3.307x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340` | 111.0 | 214.3-397.8 | 2.19 | yes | `a100_sxm_80gb-x335-hybrid` | 93.0 | 115.7-214.8 | 3.41 | yes | 1.194x | 1.852x | 1.552x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12` | 34.4 | 72.7-134.9 | 2.00 | yes | `a100_sxm_80gb-x672-hybrid` | 167.3 | 227.5-422.3 | 3.12 | yes | 0.205x | 0.320x | 1.555x |

**Does the ratio compress?** Of 20 class rows in this study, 15 move the ROM-versus-GPU ratio DOWN under speculation and 5 move it UP. The movement spans 0.242x to 3.307x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 20 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

## Where the drafter lives on a ROM machine

The locality rule -- `stored/peak` is a technology constant -- is the load-bearing assumption of the whole ROM verdict. A pass that reads only the drafter's region uses only that region's read ports and takes exactly as long as sweeping the entire array. Two placements are therefore priced side by side, and the second is an architectural proposal this study **has not costed in silicon area**.

The same rule is what makes a SEQUENTIAL draft step expensive here. A per-position operation that moves only a small table is nearly free on a global-bandwidth store and costs a full array sweep on this one, so a drafter with `gamma` sequential applications pays `gamma` sweeps for them. That term is charged in full below; on a bandwidth store the bytes it moves are not separately charged at all, because this repository's model configs carry no size for the table -- an omission whose size, on DeepSeek-V4-Pro-0813, is the externally published 132,382,720 B per draft token, 0.33% of the 39,666,603,980 B target pass.

| study | model | ctx | batch | class | design | tau* draft in ROM | tau* draft in KV store | KV placement feasible | why not |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 10.17 | 37.64 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 9.56 | 235.13 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 10.17 | 37.64 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 9.56 | 235.13 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 10.17 | 37.64 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 9.56 | 235.13 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 10.17 | 37.64 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 9.56 | 235.13 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 10.17 | 37.64 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 9.56 | 235.13 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 17.53 | 71.00 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 10.74 | 223.15 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 20.04 | 68.19 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 10.78 | 224.31 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 18.98 | 50.00 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 19.10 | 359.12 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 23.65 | 54.28 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 37.50 | 733.25 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 26.91 | 44.41 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 14.48 | 66.95 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 12.75 | 82.90 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 12.47 | 535.64 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 12.75 | 82.90 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 12.47 | 535.64 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 12.75 | 82.90 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 12.47 | 535.64 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 12.75 | 82.90 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 12.47 | 535.64 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 12.75 | 82.90 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 12.47 | 535.64 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 12.75 | 82.90 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 13.56 | 514.00 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 21.87 | 154.16 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 13.62 | 516.54 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 29.56 | 196.69 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 22.94 | 767.22 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 32.23 | 163.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 19.36 | 355.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 27.76 | 57.74 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 19.13 | 261.19 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 11.56 | 37.15 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.56 | 105.78 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 11.56 | 37.15 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.56 | 105.78 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 11.56 | 37.15 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.56 | 105.78 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 11.56 | 37.15 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.56 | 105.78 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 11.56 | 37.15 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.56 | 105.78 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 10.79 | 35.74 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 8.06 | 102.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 17.93 | 64.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 13.11 | 195.75 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 20.50 | 49.05 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 20.05 | 266.58 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 31.47 | 78.87 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 22.75 | 217.85 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 26.20 | 34.87 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 16.30 | 127.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 8.77 | 41.23 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 11.41 | 121.03 | NO | the KV store has no room for it |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 8.77 | 41.23 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 6.33 | 115.86 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 8.77 | 41.23 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 6.33 | 115.86 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 8.77 | 41.23 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 6.33 | 115.86 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 8.77 | 41.23 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 6.33 | 115.86 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 14.09 | 78.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 9.79 | 218.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 23.46 | 139.85 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 9.44 | 188.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 32.04 | 165.64 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 16.07 | 391.24 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 32.31 | 119.41 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 19.87 | 495.90 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 27.19 | 44.45 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 8.54 | 133.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 9.61 | 37.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 8.69 | 240.79 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 9.61 | 37.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 8.69 | 240.79 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 9.61 | 37.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 8.69 | 240.79 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 9.61 | 37.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 8.69 | 240.79 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 9.61 | 37.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 8.69 | 240.79 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 16.67 | 71.90 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 9.81 | 228.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 18.72 | 69.98 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.85 | 230.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 28.69 | 96.54 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 17.99 | 381.93 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 23.03 | 55.41 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 37.96 | 829.14 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 27.27 | 47.44 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 29.99 | 274.35 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 12.11 | 83.26 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 11.43 | 553.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 12.11 | 83.26 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 11.43 | 553.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 12.11 | 83.26 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 11.43 | 553.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 12.11 | 83.26 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 11.43 | 553.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 12.11 | 83.26 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 11.43 | 553.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342-romfill` | 13.46 | 81.27 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 12.48 | 532.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 20.61 | 152.26 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 12.54 | 535.24 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 20.78 | 109.61 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 21.93 | 828.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 32.20 | 182.12 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 41.08 | 1,576.63 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 28.03 | 63.64 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 19.74 | 160.82 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 6.43 | 4.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 5.91 | 3.47 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 6.43 | 4.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.99 | 7.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 6.43 | 4.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.99 | 7.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 6.43 | 4.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.99 | 7.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 10.45 | 6.55 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5.91 | 7.18 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 10.30 | 6.73 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5.81 | 7.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.30 | 6.73 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.82 | 7.06 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 15.76 | 10.86 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.81 | 11.89 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 19.52 | 15.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 20.39 | 25.21 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 13.68 | 12.35 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 18.19 | 19.78 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 7.83 | 5.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 7.46 | 4.11 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 7.83 | 5.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.14 | 12.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 7.83 | 5.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.14 | 12.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 7.83 | 5.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.14 | 12.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 7.83 | 5.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.14 | 12.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 7.77 | 5.88 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 6.99 | 12.09 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 12.46 | 8.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.02 | 12.14 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.18 | 13.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 11.51 | 19.52 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 15.01 | 11.73 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 21.02 | 36.84 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 17.57 | 16.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 17.27 | 22.09 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 7.28 | 5.02 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 6.57 | 4.30 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 7.28 | 5.02 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.28 | 4.51 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 7.28 | 5.02 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.28 | 4.51 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 7.28 | 5.02 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.28 | 4.51 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 7.16 | 5.40 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.28 | 4.51 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7.14 | 5.44 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.43 | 4.97 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 11.04 | 7.86 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.13 | 7.17 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 16.03 | 12.14 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 8.86 | 10.27 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 14.23 | 11.00 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 12.71 | 15.00 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 16.22 | 15.12 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 10.06 | 6.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 8.86 | 6.30 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | 5.04 | 3.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 8.86 | 6.30 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 5.08 | 4.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 8.86 | 6.30 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 5.08 | 4.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 8.86 | 6.30 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 5.08 | 4.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 8.86 | 6.30 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 6.19 | 4.31 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8.45 | 6.69 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 9.35 | 5.85 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 13.04 | 9.91 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 9.17 | 6.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 17.32 | 12.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 15.38 | 8.89 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 17.65 | 14.78 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 18.82 | 10.65 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 18.57 | 16.73 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 7.32 | 5.18 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 10.06 | 6.30 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.60 | 6.93 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 10.06 | 6.30 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.60 | 6.93 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 10.06 | 6.30 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.60 | 6.93 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 10.06 | 6.30 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.60 | 6.93 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 10.06 | 6.30 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5.52 | 6.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 10.05 | 6.38 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5.42 | 6.68 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.05 | 6.38 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.43 | 6.70 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 15.67 | 10.42 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.50 | 11.72 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 19.83 | 15.28 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 21.26 | 26.73 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.84 | 16.52 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 18.95 | 20.82 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 7.44 | 5.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 6.76 | 12.29 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 7.44 | 5.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 6.76 | 12.29 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 7.44 | 5.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 6.76 | 12.29 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 7.44 | 5.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 6.76 | 12.29 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 7.44 | 5.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 6.76 | 12.29 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 7.54 | 5.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 6.61 | 11.97 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 12.26 | 8.53 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 6.64 | 12.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.33 | 13.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 11.58 | 20.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 20.94 | 17.12 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 23.69 | 42.91 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 16.54 | 15.27 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 19.50 | 25.57 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 6.43 | 4.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.99 | 7.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 6.43 | 4.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.99 | 7.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 6.43 | 4.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.99 | 7.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 6.43 | 4.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.99 | 7.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 10.45 | 6.55 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5.91 | 7.18 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 10.30 | 6.73 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5.81 | 7.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.30 | 6.73 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.82 | 7.06 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 15.76 | 10.86 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.81 | 11.89 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 19.52 | 15.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 20.39 | 25.21 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 13.68 | 12.35 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 18.19 | 19.78 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 7.83 | 5.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.14 | 12.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 7.83 | 5.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.14 | 12.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 7.83 | 5.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.14 | 12.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 7.83 | 5.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.14 | 12.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 7.83 | 5.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.14 | 12.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 7.77 | 5.88 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 7.00 | 12.09 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 12.46 | 8.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.02 | 12.14 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.18 | 13.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 11.51 | 19.52 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 15.01 | 11.73 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 21.03 | 36.84 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 17.57 | 16.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 17.28 | 22.10 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | 8.14 | 8.32 | NO | the KV store has no room for it |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 5.09 | 5.20 | NO | the KV store has no room for it |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 6.53 | 6.26 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 4.40 | 4.07 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 6.53 | 6.26 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 4.40 | 4.07 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 8.98 | 8.48 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 4.40 | 4.07 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 9.59 | 9.15 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 4.40 | 4.07 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 12.88 | 12.21 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 5.78 | 5.26 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 15.34 | 14.49 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 7.87 | 7.02 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 17.64 | 16.62 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 11.31 | 9.95 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 17.53 | 17.05 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 12.65 | 11.11 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 17.14 | 17.10 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 9.07 | 8.67 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x398` | 8.34 | 8.41 | NO | the KV store has no room for it |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x10` | 5.80 | 5.96 | NO | the KV store has no room for it |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 10.01 | 9.97 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 4.42 | 4.70 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 10.01 | 9.97 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 4.42 | 4.70 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 10.40 | 10.37 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 4.42 | 4.70 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 13.30 | 13.26 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 4.42 | 4.70 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 15.37 | 15.33 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 5.39 | 5.81 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 16.43 | 16.39 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 5.51 | 5.82 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 17.21 | 17.16 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 6.32 | 6.76 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 17.20 | 17.20 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 6.65 | 7.12 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 17.14 | 17.14 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x22` | 5.74 | 5.98 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x383` | 9.43 | 9.40 | NO | the KV store has no room for it |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | 7.35 | 6.59 | NO | the KV store has no room for it |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3.51 | 2.80 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3.51 | 2.80 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3.51 | 2.80 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3.51 | 2.80 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 4.68 | 3.35 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 7.06 | 4.55 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 10.28 | 6.24 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 11.79 | 7.06 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x68` | 12.19 | 7.30 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 5.28 | 5.28 | NO | the KV store has no room for it |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x23` | 8.85 | 8.00 | NO | the KV store has no room for it |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 3.64 | 2.92 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 3.64 | 2.92 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 3.64 | 2.92 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 3.64 | 2.92 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 3.80 | 3.17 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 4.58 | 3.59 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 5.78 | 4.33 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 6.14 | 4.51 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 6.25 | 4.59 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 8.45 | 7.04 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 6.63 | 7.86 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 8.45 | 7.04 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 6.63 | 7.86 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 8.45 | 7.04 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 6.63 | 7.86 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 8.45 | 7.04 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 6.63 | 7.86 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 8.45 | 7.04 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 6.63 | 7.86 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 12.07 | 9.54 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.52 | 7.55 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 12.45 | 10.26 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.38 | 11.17 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 19.56 | 15.39 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 13.20 | 12.68 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 19.49 | 16.96 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 16.35 | 19.15 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 17.66 | 17.00 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 10.58 | 10.39 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 8.53 | 8.24 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3.95 | 5.05 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 8.53 | 8.24 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3.95 | 5.05 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 8.53 | 8.24 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3.95 | 5.05 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 8.53 | 8.24 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3.95 | 5.05 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 11.51 | 11.01 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 5.32 | 7.33 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 12.22 | 11.79 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.31 | 10.79 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 14.92 | 14.33 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.64 | 10.44 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 17.92 | 17.13 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 10.69 | 15.35 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 17.77 | 17.35 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 12.04 | 17.37 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 17.20 | 17.10 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 9.14 | 10.50 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | 6.82 | 6.38 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 3.03 | 2.89 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 5.67 | 3.62 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 2.94 | 2.23 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 5.67 | 3.62 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 2.94 | 2.23 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 5.67 | 3.62 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3.46 | 2.22 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x282` | 6.79 | 3.92 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.67 | 2.28 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 7.71 | 4.28 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.33 | 2.36 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 9.34 | 4.43 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.46 | 2.12 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 8.22 | 7.85 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.71 | 1.68 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 7.51 | 7.41 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.85 | 1.65 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 7.45 | 7.45 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x22` | 2.95 | 1.33 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x64` | 7.21 | 6.63 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 3.48 | 3.37 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3.88 | 3.03 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2.89 | 2.19 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3.88 | 3.03 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2.89 | 2.19 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x287` | 4.29 | 3.30 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2.89 | 2.19 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4.78 | 3.40 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3.28 | 2.14 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 5.34 | 3.27 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3.83 | 2.13 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 5.69 | 3.08 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3.83 | 1.98 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 6.22 | 3.11 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 4.06 | 1.89 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 4.40 | 2.78 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 4.14 | 1.90 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 2.91 | 2.50 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x31` | 2.58 | 1.45 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 6.61 | 6.12 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 5.40 | 4.78 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 4.31 | 1.73 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 4.31 | 1.73 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 4.31 | 1.73 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 4.31 | 1.73 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 4.19 | 1.78 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 4.85 | 1.51 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5.46 | 1.21 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5.73 | 1.17 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5.79 | 1.16 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | 7.38 | 6.81 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 4.64 | 4.41 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 2.18 | 2.12 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 3.67 | 1.49 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 3.67 | 1.49 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 3.67 | 1.49 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 3.67 | 1.49 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 3.06 | 1.52 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 3.11 | 1.17 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 2.92 | 1.12 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 2.93 | 1.11 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 5.91 | 5.20 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4.91 | 6.53 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 5.91 | 5.20 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4.91 | 6.53 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 5.91 | 5.20 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4.91 | 6.53 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 5.91 | 5.20 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4.91 | 6.53 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 5.99 | 5.26 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 3.96 | 6.45 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5.89 | 5.19 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.90 | 6.30 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9.14 | 7.77 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.97 | 9.60 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 14.40 | 12.55 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.61 | 12.87 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 18.05 | 16.58 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 8.47 | 18.22 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.31 | 16.89 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 6.84 | 9.57 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 7.09 | 7.24 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.33 | 6.46 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 7.09 | 7.24 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.33 | 6.46 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 7.09 | 7.24 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.33 | 6.46 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 7.09 | 7.24 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.33 | 6.46 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 7.06 | 7.21 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.24 | 6.25 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6.95 | 7.10 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.85 | 9.55 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.97 | 11.25 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4.55 | 14.02 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 16.41 | 16.76 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4.93 | 14.76 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 18.92 | 19.17 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 5.22 | 17.37 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.54 | 17.61 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 3.97 | 7.16 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | 6.10 | 5.62 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 4.51 | 3.84 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 3.19 | 2.15 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 3.19 | 2.15 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 3.19 | 2.15 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 3.22 | 2.25 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 3.79 | 2.16 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 4.68 | 2.03 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 5.01 | 1.58 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 5.26 | 1.49 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x49` | 5.32 | 1.49 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | 6.81 | 6.25 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 4.40 | 4.08 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3.04 | 2.05 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3.04 | 2.05 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3.04 | 2.05 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3.04 | 2.05 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3.44 | 1.91 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3.99 | 1.81 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 4.24 | 1.67 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 4.37 | 1.67 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x68` | 4.40 | 1.67 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | 5.38 | 4.85 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 4.96 | 4.55 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 4.75 | 1.57 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 4.75 | 1.57 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 4.75 | 1.57 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 4.75 | 1.57 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 4.75 | 1.57 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 4.66 | 1.58 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 6.24 | 1.20 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 6.17 | 1.14 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 6.28 | 1.12 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | 6.86 | 6.49 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 5.75 | 5.15 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 1.94 | 1.91 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 2.57 | 2.54 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.84 | 1.34 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.84 | 1.34 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.84 | 1.34 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.84 | 1.34 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.23 | 1.18 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.10 | 1.10 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.12 | 1.09 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 5.93 | 4.77 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.13 | 6.58 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 5.93 | 4.77 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.13 | 6.58 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 5.93 | 4.77 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.13 | 6.58 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 5.93 | 4.77 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.13 | 6.58 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 5.80 | 4.51 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 5.09 | 6.65 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 8.57 | 6.10 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.01 | 6.53 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 9.28 | 6.99 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.80 | 9.51 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 19.12 | 13.48 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.16 | 12.45 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 15.04 | 12.55 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 12.00 | 16.59 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 17.11 | 15.98 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 9.47 | 6.38 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 7.03 | 6.02 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 4.03 | 6.14 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 7.03 | 6.02 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 4.03 | 6.14 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 7.03 | 6.02 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 4.03 | 6.14 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 7.03 | 6.02 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 4.03 | 6.14 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 6.74 | 5.55 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 5.61 | 5.95 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 10.29 | 8.05 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.83 | 8.43 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 11.25 | 9.17 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.37 | 7.87 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 21.30 | 16.87 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 10.19 | 11.05 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 18.18 | 16.18 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 11.53 | 12.53 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 19.90 | 17.55 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 4.85 | 5.11 | yes | -- |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x180` | 6.32 | 6.16 | NO | the KV store has no room for it |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 3.31 | 3.31 | NO | the KV store has no room for it |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x227` | 6.02 | 5.88 | NO | the KV store has no room for it |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 4.25 | 4.25 | NO | the KV store has no room for it |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x60-romfill` | 6.47 | 6.47 | NO | the KV store has no room for it |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 2.98 | 2.98 | NO | the KV store has no room for it |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x139-romfill` | 2.33 | 2.33 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.54 | 1.60 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.54 | 1.60 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.54 | 1.60 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.54 | 1.60 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.63 | 1.67 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.11 | 1.20 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.04 | 1.13 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.02 | 1.11 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 6.70 | 6.70 | NO | the KV store has no room for it |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 3.18 | 3.18 | NO | the KV store has no room for it |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196-romfill` | 2.22 | 2.22 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 3.03 | 2.93 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 4.16 | 4.08 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 5.57 | 5.51 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.30 | 1.38 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.30 | 1.37 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.09 | 1.16 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.03 | 1.09 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.01 | 1.08 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 10.94 | 7.42 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 4.52 | 3.43 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 8.80 | 8.29 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.57 | 2.62 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 8.80 | 8.29 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.57 | 2.62 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 8.80 | 8.29 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.57 | 2.62 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 8.80 | 8.29 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.57 | 2.62 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 8.80 | 8.29 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.57 | 2.62 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.32 | 9.31 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.90 | 2.99 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 13.76 | 8.58 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 3.77 | 4.00 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 15.29 | 11.54 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 8.09 | 2.60 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 12.43 | 11.54 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 8.33 | 2.26 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x44` | 6.27 | 8.21 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.64 | 6.82 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 6.33 | 4.64 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.64 | 6.82 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 6.33 | 4.64 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.64 | 6.82 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 6.33 | 4.64 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.64 | 6.82 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 6.32 | 4.71 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.64 | 6.82 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6.31 | 4.74 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 5.58 | 6.73 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6.31 | 4.74 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5.58 | 6.73 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.60 | 8.18 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 8.85 | 10.96 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.10 | 13.69 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 14.54 | 17.46 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.74 | 16.00 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 16.01 | 17.11 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 6.06 | 4.53 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.38 | 6.56 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 6.06 | 4.53 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.38 | 6.56 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 6.06 | 4.53 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.38 | 6.56 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 6.06 | 4.53 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.38 | 6.56 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 6.12 | 4.50 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.38 | 6.56 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6.12 | 4.54 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 5.30 | 6.46 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6.12 | 4.54 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5.30 | 6.46 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.39 | 7.89 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 8.64 | 10.82 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.05 | 13.47 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 14.53 | 17.65 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.72 | 15.91 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 16.08 | 17.29 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 7.80 | 5.09 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 4.20 | 3.62 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 7.80 | 5.09 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.12 | 3.68 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 7.80 | 5.09 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.12 | 3.68 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 7.80 | 5.09 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.12 | 3.68 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 7.80 | 5.09 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.12 | 3.68 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 7.80 | 5.09 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.12 | 3.68 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 11.86 | 6.55 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 6.04 | 5.21 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 18.56 | 10.57 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.96 | 8.73 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 21.42 | 15.01 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 16.86 | 14.63 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 18.26 | 16.45 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 11.93 | 7.97 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 6.86 | 4.44 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.82 | 3.35 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 6.86 | 4.44 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.82 | 3.35 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 6.86 | 4.44 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.82 | 3.35 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 6.86 | 4.44 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.82 | 3.35 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 6.86 | 4.44 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.82 | 3.35 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 6.86 | 4.44 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.81 | 3.34 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 10.92 | 6.19 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.91 | 4.99 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 17.46 | 8.95 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 10.50 | 8.98 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 22.52 | 14.51 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 21.84 | 18.48 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 18.63 | 16.28 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 13.48 | 11.49 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 7.01 | 4.53 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.79 | 3.31 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 7.01 | 4.53 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.79 | 3.31 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 7.01 | 4.53 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.79 | 3.31 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 7.01 | 4.53 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.79 | 3.31 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 7.01 | 4.53 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.79 | 3.31 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 7.01 | 4.53 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 6.05 | 5.08 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 11.12 | 6.25 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.02 | 5.06 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 13.88 | 9.45 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 10.69 | 9.10 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 22.73 | 14.42 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 22.01 | 18.53 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 18.70 | 16.25 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 14.54 | 13.49 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x152` | 12.58 | 8.42 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 5.12 | 3.65 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 9.04 | 6.79 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.26 | 2.26 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 9.04 | 6.79 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.26 | 2.26 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 9.04 | 6.79 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.26 | 2.26 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 9.04 | 6.79 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.26 | 2.26 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 10.80 | 6.53 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.26 | 2.26 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 10.71 | 9.85 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.18 | 2.50 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 16.16 | 7.83 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 9.39 | 2.17 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 13.25 | 8.21 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 11.02 | 1.91 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 9.53 | 8.22 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 11.57 | 1.94 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 7.83 | 5.93 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5.07 | 6.48 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 7.83 | 5.93 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5.07 | 6.48 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 7.83 | 5.93 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5.07 | 6.48 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 7.83 | 5.93 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5.07 | 6.48 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 7.83 | 5.93 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 4.53 | 6.86 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 7.70 | 6.07 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4.47 | 6.73 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 7.71 | 6.09 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4.48 | 6.75 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 12.51 | 10.20 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.16 | 10.90 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.25 | 15.21 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 13.14 | 21.25 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.09 | 16.49 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 12.36 | 14.95 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 7.41 | 5.79 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4.44 | 6.97 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 7.41 | 5.79 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4.44 | 6.97 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 7.41 | 5.79 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4.44 | 6.97 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 7.41 | 5.79 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4.44 | 6.97 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 7.41 | 5.79 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 4.39 | 6.86 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 7.44 | 5.80 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4.32 | 6.70 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 7.44 | 5.81 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4.33 | 6.73 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 12.36 | 9.95 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.46 | 11.71 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.27 | 15.08 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 16.63 | 27.53 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.09 | 16.44 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 16.89 | 20.75 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 9.12 | 6.11 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 4.91 | 4.06 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 9.12 | 6.11 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 4.00 | 3.10 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 9.12 | 6.11 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 4.00 | 3.10 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 9.12 | 6.11 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 4.00 | 3.10 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 9.12 | 6.11 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 4.00 | 3.10 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 9.12 | 6.11 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 5.90 | 4.14 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 13.96 | 8.37 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 5.93 | 4.29 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 19.54 | 12.35 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 11.15 | 7.25 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 21.24 | 16.04 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 15.24 | 9.71 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 18.17 | 16.74 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 7.41 | 5.91 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 5.77 | 4.16 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4.70 | 4.99 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 5.77 | 4.16 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4.70 | 4.99 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 5.77 | 4.16 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4.70 | 4.99 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 5.77 | 4.16 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4.70 | 4.99 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 5.77 | 4.16 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4.70 | 4.99 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 8.36 | 5.38 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4.66 | 4.95 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 13.43 | 7.45 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.39 | 7.94 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 19.98 | 11.63 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 12.73 | 13.57 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 22.30 | 15.79 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 15.75 | 13.32 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 18.50 | 16.67 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 18.32 | 16.51 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 8.56 | 5.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.67 | 4.99 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 8.56 | 5.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.67 | 4.99 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 8.56 | 5.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.67 | 4.99 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 8.56 | 5.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.67 | 4.99 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 8.56 | 5.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.67 | 4.99 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 8.56 | 5.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4.60 | 4.89 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 9.20 | 6.04 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.62 | 8.19 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 20.07 | 11.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 12.99 | 13.87 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 22.51 | 15.75 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 14.17 | 12.87 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 18.56 | 16.65 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 17.35 | 16.36 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 4.93 | 4.93 | NO | the KV store has no room for it |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 2.86 | 3.00 | NO | the KV store has no room for it |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 4.82 | 4.93 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 2.41 | 3.01 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 4.82 | 4.93 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 2.41 | 3.01 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 4.82 | 4.92 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2.41 | 3.01 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4.81 | 4.91 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.35 | 3.32 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5.92 | 6.10 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.54 | 3.27 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7.10 | 7.10 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.33 | 3.33 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9.56 | 9.56 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.87 | 3.21 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9.82 | 9.82 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1.71 | 3.13 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.13 | 10.13 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1.75 | 1.89 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 7.14 | 5.65 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 5.12 | 3.62 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 7.30 | 5.36 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3.23 | 3.47 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 7.30 | 5.36 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3.23 | 3.47 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 7.30 | 5.36 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3.23 | 3.47 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x61` | 7.50 | 5.44 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3.23 | 3.47 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 7.29 | 5.84 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.22 | 3.47 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7.29 | 5.84 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.09 | 4.57 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 11.71 | 9.74 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.79 | 6.46 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.33 | 14.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 7.81 | 8.93 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 12.92 | 11.87 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 6.33 | 4.59 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340` | 10.08 | 7.74 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 5.19 | 3.64 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 10.45 | 7.61 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 5.10 | 2.25 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 10.45 | 7.61 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 5.10 | 2.25 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 10.45 | 7.61 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 5.10 | 2.25 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 10.45 | 7.61 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 5.10 | 2.25 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 10.45 | 7.61 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 5.10 | 2.25 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 14.25 | 8.60 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3.31 | 3.14 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 19.20 | 12.30 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 10.87 | 3.04 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 20.62 | 15.74 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 17.10 | 3.44 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 17.99 | 16.67 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 20.02 | 3.82 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 5.41 | 5.41 | NO | the KV store has no room for it |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 2.99 | 3.10 | NO | the KV store has no room for it |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4.15 | 4.43 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2.15 | 2.46 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4.15 | 4.43 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2.04 | 2.62 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4.15 | 4.43 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.98 | 3.12 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4.55 | 5.08 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.05 | 2.98 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 5.30 | 5.57 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.83 | 2.98 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 5.75 | 6.13 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.58 | 2.92 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6.50 | 7.01 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.27 | 2.80 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 6.87 | 6.87 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1.18 | 2.75 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 3.65 | 3.38 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 2.00 | 1.44 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | 8.61 | 6.61 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 5.46 | 3.96 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 8.99 | 6.79 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 4.41 | 2.89 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 8.99 | 6.79 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 4.41 | 2.89 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 8.99 | 6.79 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 4.41 | 2.89 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 8.99 | 6.79 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 4.41 | 2.89 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 8.67 | 7.23 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 6.42 | 3.51 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 8.67 | 7.23 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.11 | 3.76 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 13.32 | 11.50 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.55 | 4.01 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.12 | 15.72 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 8.30 | 3.70 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 15.13 | 14.21 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 5.35 | 2.90 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 8.88 | 7.62 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 6.28 | 4.11 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.75 | 2.36 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.75 | 2.36 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.75 | 2.36 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.75 | 2.36 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.75 | 2.36 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.75 | 2.36 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 10.61 | 2.68 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 14.60 | 3.01 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 16.08 | 3.20 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 6.77 | 6.77 | NO | the KV store has no room for it |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 2.59 | 2.62 | NO | the KV store has no room for it |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 3.81 | 3.81 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 2.25 | 2.40 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 3.81 | 3.81 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 2.25 | 2.40 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x170-romfill` | 3.81 | 3.81 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 2.25 | 2.40 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3.81 | 3.81 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 2.10 | 2.34 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4.00 | 4.00 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 2.24 | 2.42 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4.27 | 4.27 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.93 | 2.17 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4.80 | 4.80 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.38 | 1.71 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4.87 | 4.87 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 1.17 | 1.53 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4.88 | 4.88 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 1.71 | 1.14 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x8-romfill` | 5.30 | 5.30 | NO | the KV store has no room for it |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 2.65 | 2.67 | NO | the KV store has no room for it |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 3.45 | 3.51 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 2.13 | 2.21 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 3.45 | 3.51 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 2.01 | 2.16 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 3.45 | 3.51 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 1.92 | 2.21 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 3.29 | 3.39 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.99 | 2.22 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3.65 | 3.68 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.75 | 2.04 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3.40 | 3.44 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.49 | 1.83 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 2.93 | 2.97 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.18 | 1.57 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 2.88 | 2.88 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 1.09 | 1.49 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340` | 2.19 | 1.57 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12` | 2.00 | 1.12 | yes | -- |

## The capacity requirement, stated as a requirement

Every evaluated ROM design carries `weight_capacity_bytes == stored_weight_bytes` (the `romfill` variants reach 1.0039x), so no evaluated design has spare array for a drafter it does not already store. Re-solving the area split is `balanced_area_split`'s job and that file is not touched here, so what follows is a requirement -- this much extra array, or this much extra sweep on every pass -- and not a new design. **The speculative-optimal ROM design has not been computed, only bounded by the rungs that already exist.**

| study | model | design | drafter already in the checkpoint | extra stored bytes | extra array mm2 | as a fraction of the design | sweep inflation if area is held fixed |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | no | 850,275,640 | 90.7 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | no | 850,275,640 | 90.7 | 0.1% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | no | 850,275,640 | 90.7 | 0.0% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | no | 850,275,640 | 90.7 | 0.0% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | no | 850,275,640 | 116.6 | 0.0% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | no | 850,275,640 | 90.7 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | no | 850,275,640 | 90.7 | 0.1% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | no | 850,275,640 | 90.7 | 0.0% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | no | 850,275,640 | 116.6 | 0.0% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | no | 850,275,640 | 90.7 | 0.0% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | no | 850,275,640 | 116.6 | 0.0% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | no | 11,706,065,920 | 1,248.0 | 0.4% | 1.0075x |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | no | 11,706,065,920 | 1,248.0 | 0.4% | 1.0075x |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x398` | no | 11,706,065,920 | 1,604.6 | 0.5% | 1.0075x |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `ROM-N6-native-SRAMKV-wafer-hybrid-x10` | no | 11,706,065,920 | 1,604.6 | 0.3% | 1.0075x |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x383` | no | 11,706,065,920 | 1,248.0 | 0.4% | 1.0075x |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | no | 11,706,065,920 | 1,248.0 | 0.1% | 1.0075x |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | no | 11,706,065,920 | 1,604.6 | 0.5% | 1.0075x |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `ROM-N6-native-SRAMKV-wafer-hybrid-x23` | no | 11,706,065,920 | 1,604.6 | 0.2% | 1.0075x |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | no | 11,706,065,920 | 1,248.0 | 0.4% | 1.0075x |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | no | 11,706,065,920 | 1,248.0 | 0.4% | 1.0075x |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | no | 11,706,065,920 | 1,604.6 | 0.5% | 1.0075x |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | no | 11,706,065,920 | 1,604.6 | 0.3% | 1.0075x |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | no | 1,620,446,720 | 172.8 | 0.5% | 1.0094x |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | no | 1,620,446,720 | 172.8 | 0.4% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x64` | no | 1,620,446,720 | 222.1 | 0.4% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | no | 1,620,446,720 | 222.1 | 0.5% | 1.0094x |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | no | 1,620,446,720 | 172.8 | 0.2% | 1.0094x |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | no | 1,620,446,720 | 172.8 | 0.2% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | no | 1,620,446,720 | 222.1 | 0.2% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | no | 1,620,446,720 | 222.1 | 0.2% | 1.0094x |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | no | 1,620,446,720 | 172.8 | 0.2% | 1.0094x |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | no | 1,620,446,720 | 172.8 | 0.2% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | no | 1,620,446,720 | 222.1 | 0.3% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | no | 1,620,446,720 | 222.1 | 0.1% | 1.0094x |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | no | 3,350,899,200 | 357.3 | 0.3% | 1.0059x |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | no | 3,350,899,200 | 357.3 | 0.3% | 1.0059x |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | no | 3,350,899,200 | 459.3 | 0.3% | 1.0059x |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | no | 3,350,899,200 | 459.3 | 0.3% | 1.0059x |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | no | 3,350,899,200 | 357.3 | 0.1% | 1.0059x |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | no | 3,350,899,200 | 357.3 | 0.2% | 1.0059x |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | no | 3,350,899,200 | 459.3 | 0.2% | 1.0059x |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | no | 3,350,899,200 | 459.3 | 0.2% | 1.0059x |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | no | 3,350,899,200 | 357.3 | 0.3% | 1.0059x |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | no | 3,350,899,200 | 357.3 | 0.3% | 1.0059x |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | no | 3,350,899,200 | 459.3 | 0.3% | 1.0059x |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | no | 3,350,899,200 | 459.3 | 0.2% | 1.0059x |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x180` | no | 1,929,464,320 | 205.7 | 0.1% | 1.1178x |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | no | 1,929,464,320 | 205.7 | 0.2% | 1.1178x |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x227` | no | 1,929,464,320 | 264.5 | 0.1% | 1.1178x |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | no | 1,929,464,320 | 264.5 | 0.3% | 1.1178x |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-hybrid-x60-romfill` | no | 1,929,464,320 | 205.7 | 0.4% | 1.1178x |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | no | 1,929,464,320 | 205.7 | 0.4% | 1.1178x |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | no | 1,929,464,320 | 264.5 | 0.6% | 1.1178x |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | no | 1,929,464,320 | 264.5 | 0.6% | 1.1178x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x44` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x152` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | no | 686,957,240 | 94.2 | 0.2% | 1.0041x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | no | 686,957,240 | 94.2 | 0.2% | 1.0041x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | no | 1,929,464,320 | 205.7 | 1.6% | 1.1178x |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | no | 1,929,464,320 | 205.7 | 0.4% | 1.1178x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | no | 1,929,464,320 | 264.5 | 2.0% | 1.1178x |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | no | 1,929,464,320 | 264.5 | 0.6% | 1.1178x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | no | 512,513,960 | 54.6 | 1.7% | 1.1178x |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | no | 512,513,960 | 54.6 | 0.1% | 1.1178x |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x8-romfill` | no | 512,513,960 | 70.3 | 1.1% | 1.1178x |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | no | 512,513,960 | 70.3 | 0.2% | 1.1178x |

## Which design the published rule chooses once a block is verified

A re-ranking of designs the study already evaluated, under the study's own selection rule (non-dominated on per-user tokens/s and tokens/s per 1,000 mm2, then a marginal-return walk from the smallest feasible machine). `tau` is a common factor on both axes, so the choice is independent of the acceptance rate. The rule's reproduction of the published autoregressive recommendation is reported first, because a re-ranking whose baseline does not reproduce is not evidence of anything.

| study | model | published recommendation | rule reproduces it | under speculation, draft in ROM | draft in KV store | moves |
| --- | --- | --- | --- | --- | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-array-hw-tensor-x110` | yes |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-array-hw-tensor-x143` | yes |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-array-hw-tensor-x110` | yes |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-array-hw-tensor-x143` | yes |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-array-hw-tensor-x97` | yes |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-array-hw-tensor-x141` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | yes | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-wafer-tensor-x2` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x68` | yes | `ROM-N5-native-HBMKV-array-hw-tensor-x68` | `ROM-N5-native-HBMKV-array-hw-tensor-x68` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x87` | yes | `ROM-N6-native-HBMKV-array-hw-tensor-x87` | `ROM-N6-native-HBMKV-array-hw-tensor-x87` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | no |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x85` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-wafer-tensor-x2` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-SRAMKV-array-hw-hybrid-x59` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-SRAMKV-array-hw-hybrid-x76` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-wafer-tensor-x2` | yes |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x6` | `ROM-N5-native-HBMKV-array-hw-tensor-x327` | yes |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `ROM-N6-native-SRAMKV-wafer-hybrid-x8` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x8` | `ROM-N6-native-HBMKV-array-hw-tensor-x398` | yes |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-tensor-x6` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x6` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | no |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `ROM-N6-native-SRAMKV-wafer-tensor-x8` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x9` | `ROM-N6-native-HBMKV-wafer-tensor-x95` | yes |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x5` | `ROM-N5-native-HBMKV-wafer-tensor-x5` | yes |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x7` | `ROM-N6-native-HBMKV-wafer-tensor-x7` | yes |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-tensor-x36` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | yes |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | no |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | no |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-wafer-tensor-x153` | yes |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x34` | `ROM-N5-native-HBMKV-array-hw-tensor-x38` | yes |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-tensor-x47` | yes |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | yes |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | yes |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | yes |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | yes |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-wafer-tensor-x3` | yes |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-hybrid-x139` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-array-hw-tensor-x138` | yes |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | yes | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | `None` | no |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | yes | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | `None` | yes |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x21` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-tensor-x139` | yes |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x27` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | yes |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x38` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | yes |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-array-hw-tensor-x36` | yes |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-array-hw-hybrid-x208` | yes |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-tensor-x3` | yes |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-tensor-x3` | yes |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | no |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-tensor-x45` | yes |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x41` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | yes |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-array-hw-tensor-x217` | yes |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-tensor-x4` | yes |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-tensor-x4` | yes |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x8` | `ROM-N5-native-HBMKV-array-hw-hybrid-x49` | yes |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x31` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-array-hw-hybrid-x56` | yes |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | no |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x12` | `ROM-N6-native-HBMKV-array-hw-tensor-x69` | yes |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x42` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-tensor-x79` | yes |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | no |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | yes | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x49` | yes |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | yes | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x4` | `ROM-N6-q4p25-HBMKV-array-hw-tensor-x69` | yes |

**The rule reproduces the published autoregressive recommendation on 56 of 56 model-and-study rows.** Of the 56 rows where it reproduces and the drafter applies, verifying a block moves the chosen rung on 48. Where it moves, it moves toward machines with compute headroom for a block, which is exactly what the arithmetic predicts: a verification pass raises arithmetic intensity by the block size, and a machine sized with just enough compute for one token per sweep has no room for it. **This is a re-ranking of rungs that already exist. The speculative-optimal design has not been computed: that would need the area split re-solved, which is `balanced_area_split`'s job and not this layer's.**

## Gate: the DFlash overhead factor

_band check, never an equality._

- modelled on `Qwen3-8B/b200_sxm-x3-tensor` at batch 1, 8,192 tokens of context, gamma 16
- modelled overhead factor: **1.205** with the drafter charged no KV, **1.212** at the top of the band
- published band: 1.26-1.32, outlier MT-Bench at 1.54
- source: arXiv:2602.06036v2, ICML 2026, Table 1, tau divided by reported speedup
- inside the published band: **no**

**Residual.** this layer models an overhead factor of 1.205 at the low end of the unsourced drafter-KV band and 1.212 at the high end, against a published 1.26-1.32 measured on an H200. The gap is the gate residual and its named causes are: the drafter's own KV traffic at the low bound of an unsourced band, no sampler and no scheduler cost anywhere in this model, and a modelled B200-class cluster against their measured H200.

**Their speedups are measured with their kernels on their part. Nothing here measures a speedup, and no sentence in this artifact may be read as though it did.**

## Cross-check: Xiaomi MiMo-V2.5-Pro-UltraSpeed

**This is a cross-check. It is not a calibration target, and nothing in this study is fitted to it.**

_Our own model, run on the GPU clusters this study evaluates that are nearest in size to an eight-package node, carrying DeepSeek-V4-Pro-0813 -- a 1.6-trillion-parameter fine-grained MoE, the closest thing in this study to the model Xiaomi describes -- with the block-diffusion drafter at gamma = 8, the block size Xiaomi's deployment uses, and with the acceptance lengths Xiaomi publishes at that same block size. It is put beside Xiaomi's claim, and it does not calibrate to it._

Xiaomi reports **1,000 tokens/s** decode on a 1-trillion-parameter model, with a figure caption reading up to about 1,200 tokens/s, on "a single standard 8-GPU commodity node" (https://mimo.xiaomi.com/blog/mimo-tilert-1000tps (2026)).

**What the blog does not state, and what therefore cannot be inferred from it:**

- the GPU model is not stated
- the batch size or concurrency is not stated
- whether the figure is per-user or aggregate is not stated
- the attribution of the speedup among the three stacked techniques is explicitly declined by Xiaomi

The claimed rate is the product of three stacked techniques, and Xiaomi explicitly declines to attribute it among them:

- MXFP4 quantisation of MoE experts only, with routers and attention at higher precision, quantisation-aware trained
- a DFlash block-diffusion drafter with block size limited to 8
- the TileRT runtime

**How this study's model differs from that deployment:**

- Xiaomi quantises MoE experts to MXFP4 with quantisation-aware training; the DeepSeek-V4-Pro-0813 profile in this repository is evaluated at the released checkpoint's own packing and no quantised Pro variant exists in this study.
- Xiaomi runs the TileRT runtime; this model charges an assumed 0.55 compute efficiency and an assumed 0.9 stage balance and knows nothing about any runtime.
- Xiaomi declines to attribute the speedup among quantisation, drafter and runtime, so no part of the claim can be read as a speculative-decoding result on its own.
- The model is not the same model. DeepSeek-V4-Pro-0813 and MiMo-V2.5-Pro share only a parameter count.

**What our model says for the closest thing this study evaluates.**

_Eight packages is an evaluated rung for this model and the rows below include it._

**Every row below is evaluated at gamma = 8, the block size Xiaomi's own deployment uses, so the verification pass carries 9 positions. The acceptance lengths applied to it are the ones Xiaomi publishes at that same block size. This is NOT this profile's served block size, and the cycle and the acceptance length are never taken from different configurations.**

GPU cluster sizes this study evaluates for DeepSeek-V4-Pro-0813: 8, 14, 18, 29, 32, 38, 40, 41, 42, 43, 56, 58, 74, 75, 76, 79, 80, 82, 83, 85, 87, 90, 91, 92, 93, 94, 95, 98, 100, 101, 103, 106, 110, 111, 112, 113, 114, 116, 118, 120, 121, 124, 125, 132, 133, 134, 137, 144, 146, 147, 150, 151, 157, 168, 170, 171, 173, 185, 187, 189, 197, 198, 199, 202, 203, 208, 214, 216, 217, 221, 224, 227, 229, 231, 234, 237, 241, 245, 255, 257, 261, 262, 263, 268, 272, 274, 280, 289, 293, 302, 311, 313, 320, 321, 322, 324, 325, 334, 335, 336, 347, 354, 355, 356, 360, 361, 363, 365, 366, 368, 373, 383, 384, 391, 392, 448, 504, 574, 672, 783, 1358, 3694 packages.

DeepSeek-V4-Pro-0813 is 1.6 trillion total parameters with 49 billion active; the model Xiaomi describes is 1 trillion total, and its active count is ASSUMED at 42 billion -- the blog states no active parameter count, that figure comes from secondary reporting, and it is graded `assumed` here and used for nothing but this sentence. They are the same class and they are not the same model.

| design | packages | batch | ctx | block (gamma) | positions verified | AR per-user tok/s | AR aggregate tok/s | resident sessions | binds on | tau* | coding tau 6.30 | maths tau 5.56 | agent tau 4.29 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| `b200_sxm-x8-expert` | 8 | 1 | 8,192 | 8 | 9 | 384.89 | 385 | 1 | `weight_read` | 2.17 | 1,115.03 | 984.06 | 759.28 |
| `b200_sxm-x8-nvl72-expert` | 8 | 1 | 8,192 | 8 | 9 | 384.89 | 385 | 1 | `weight_read` | 2.17 | 1,115.03 | 984.06 | 759.28 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 1 | 8,192 | 8 | 9 | 480.92 | 481 | 1 | `link_latency` | 2.02 | 1,501.98 | 1,325.56 | 1,022.78 |
| `b200_sxm-x8-pipeline` | 8 | 1 | 8,192 | 8 | 9 | 154.01 | 1,232 | 8 | `weight_read` | 3.49 | 278.22 | 245.54 | 189.45 |
| `b200_sxm-x8-tensor` | 8 | 1 | 8,192 | 8 | 9 | 480.92 | 481 | 1 | `link_latency` | 2.02 | 1,501.98 | 1,325.56 | 1,022.78 |
| `b200_sxm-x8-expert` | 8 | 2 | 8,192 | 8 | 9 | 331.38 | 663 | 2 | `weight_read` | 2.80 | 745.40 | 657.85 | 507.58 |
| `b200_sxm-x8-nvl72-expert` | 8 | 2 | 8,192 | 8 | 9 | 331.38 | 663 | 2 | `weight_read` | 2.80 | 745.40 | 657.85 | 507.58 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 2 | 8,192 | 8 | 9 | 425.70 | 851 | 2 | `weight_read` | 2.51 | 1,070.16 | 944.46 | 728.73 |
| `b200_sxm-x8-pipeline` | 8 | 2 | 8,192 | 8 | 9 | 154.01 | 1,232 | 8 | `weight_read` | 3.49 | 278.22 | 245.54 | 189.45 |
| `b200_sxm-x8-tensor` | 8 | 2 | 8,192 | 8 | 9 | 425.70 | 851 | 2 | `weight_read` | 2.51 | 1,070.16 | 944.46 | 728.73 |
| `b200_sxm-x8-expert` | 8 | 4 | 8,192 | 8 | 9 | 265.89 | 1,064 | 4 | `weight_read` | 3.68 | 455.00 | 401.56 | 309.84 |
| `b200_sxm-x8-nvl72-expert` | 8 | 4 | 8,192 | 8 | 9 | 265.89 | 1,064 | 4 | `weight_read` | 3.68 | 455.00 | 401.56 | 309.84 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 4 | 8,192 | 8 | 9 | 347.46 | 1,390 | 4 | `weight_read` | 3.12 | 700.67 | 618.37 | 477.12 |
| `b200_sxm-x8-pipeline` | 8 | 4 | 8,192 | 8 | 9 | 154.01 | 1,232 | 8 | `weight_read` | 3.49 | 278.22 | 245.54 | 189.45 |
| `b200_sxm-x8-tensor` | 8 | 4 | 8,192 | 8 | 9 | 347.46 | 1,390 | 4 | `weight_read` | 3.12 | 700.67 | 618.37 | 477.12 |
| `b200_sxm-x8-expert` | 8 | 8 | 8,192 | 8 | 9 | 195.72 | 1,566 | 8 | `weight_read` | 4.95 | 249.25 | 219.97 | 169.73 |
| `b200_sxm-x8-nvl72-expert` | 8 | 8 | 8,192 | 8 | 9 | 195.72 | 1,566 | 8 | `weight_read` | 4.95 | 249.25 | 219.97 | 169.73 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 8 | 8,192 | 8 | 9 | 256.71 | 2,054 | 8 | `weight_read` | 3.58 | 451.68 | 398.63 | 307.57 |
| `b200_sxm-x8-pipeline` | 8 | 8 | 8,192 | 8 | 9 | 154.01 | 1,232 | 8 | `weight_read` | 3.49 | 278.22 | 245.54 | 189.45 |
| `b200_sxm-x8-tensor` | 8 | 8 | 8,192 | 8 | 9 | 256.71 | 2,054 | 8 | `weight_read` | 3.58 | 451.68 | 398.63 | 307.57 |
| `b200_sxm-x8-expert` | 8 | 16 | 8,192 | 8 | 9 | 131.55 | 2,105 | 16 | `weight_read` | 7.26 | 114.16 | 100.75 | 77.74 |
| `b200_sxm-x8-nvl72-expert` | 8 | 16 | 8,192 | 8 | 9 | 131.55 | 2,105 | 16 | `weight_read` | 7.26 | 114.16 | 100.75 | 77.74 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 16 | 8,192 | 8 | 9 | 172.85 | 2,766 | 16 | `weight_read` | 3.57 | 304.89 | 269.08 | 207.62 |
| `b200_sxm-x8-pipeline` | 8 | 16 | 8,192 | 8 | 9 | 117.59 | 1,881 | 16 | `thermal` | 4.47 | 165.78 | 146.30 | 112.89 |
| `b200_sxm-x8-tensor` | 8 | 16 | 8,192 | 8 | 9 | 172.85 | 2,766 | 16 | `weight_read` | 3.57 | 304.89 | 269.08 | 207.62 |
| `b200_sxm-x8-expert` | 8 | 32 | 8,192 | 8 | 9 | 81.03 | 2,593 | 32 | `weight_read` | 12.66 | 40.32 | 35.59 | 27.46 |
| `b200_sxm-x8-nvl72-expert` | 8 | 32 | 8,192 | 8 | 9 | 81.03 | 2,593 | 32 | `weight_read` | 12.66 | 40.32 | 35.59 | 27.46 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 32 | 8,192 | 8 | 9 | 109.05 | 3,490 | 32 | `weight_read` | 3.27 | 210.35 | 185.64 | 143.24 |
| `b200_sxm-x8-pipeline` | 8 | 32 | 8,192 | 8 | 9 | 79.75 | 2,552 | 32 | `thermal` | 5.02 | 100.10 | 88.34 | 68.16 |
| `b200_sxm-x8-tensor` | 8 | 32 | 8,192 | 8 | 9 | 109.05 | 3,490 | 32 | `weight_read` | 3.27 | 210.35 | 185.64 | 143.24 |
| `b200_sxm-x8-expert` | 8 | 64 | 8,192 | 8 | 9 | 45.26 | 2,896 | 64 | `weight_read` | 24.58 | 11.60 | 10.24 | 7.90 |
| `b200_sxm-x8-nvl72-expert` | 8 | 64 | 8,192 | 8 | 9 | 45.26 | 2,896 | 64 | `weight_read` | 24.58 | 11.60 | 10.24 | 7.90 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 64 | 8,192 | 8 | 9 | 69.99 | 4,480 | 64 | `weight_read` | 3.22 | 137.09 | 120.98 | 93.35 |
| `b200_sxm-x8-pipeline` | 8 | 64 | 8,192 | 8 | 9 | 49.40 | 3,161 | 64 | `thermal` | 4.74 | 65.62 | 57.91 | 44.69 |
| `b200_sxm-x8-tensor` | 8 | 64 | 8,192 | 8 | 9 | 69.99 | 4,480 | 64 | `weight_read` | 3.22 | 137.09 | 120.98 | 93.35 |
| `b200_sxm-x8-expert` | 8 | 256 | 8,192 | 8 | 9 | 7.99 | 2,045 | 256 | `link_latency` | 64.57 | 0.78 | 0.69 | 0.53 |
| `b200_sxm-x8-nvl72-expert` | 8 | 256 | 8,192 | 8 | 9 | 7.99 | 2,045 | 256 | `link_latency` | 64.57 | 0.78 | 0.69 | 0.53 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 256 | 8,192 | 8 | 9 | 35.17 | 9,003 | 256 | `weight_read` | 4.90 | 45.24 | 39.93 | 30.81 |
| `b200_sxm-x8-pipeline` | 8 | 256 | 8,192 | 8 | 9 | 17.35 | 4,442 | 256 | `thermal` | 2.43 | 45.05 | 39.76 | 30.67 |
| `b200_sxm-x8-tensor` | 8 | 256 | 8,192 | 8 | 9 | 35.17 | 9,003 | 256 | `weight_read` | 4.90 | 45.24 | 39.93 | 30.81 |
| `b200_sxm-x8-expert` | 8 | 1024 | 8,192 | 8 | 9 | 0.63 | 642 | 1,024 | `link_latency` | 80.08 | 0.05 | 0.04 | 0.03 |
| `b200_sxm-x8-nvl72-expert` | 8 | 1024 | 8,192 | 8 | 9 | 0.63 | 642 | 1,024 | `link_latency` | 80.08 | 0.05 | 0.04 | 0.03 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 1024 | 8,192 | 8 | 9 | 14.83 | 15,184 | 1,024 | `link_latency` | 8.08 | 11.57 | 10.21 | 7.88 |
| `b200_sxm-x8-pipeline` | 8 | 1024 | 8,192 | 8 | 9 | 8.19 | 8,383 | 1,024 | `thermal` | 1.24 | 41.68 | 36.78 | 28.38 |
| `b200_sxm-x8-tensor` | 8 | 1024 | 8,192 | 8 | 9 | 14.83 | 15,184 | 1,024 | `link_latency` | 8.08 | 11.57 | 10.21 | 7.88 |
| `b200_sxm-x8-expert` | 8 | 4096 | 8,192 | 8 | 9 | 0.04 | 166 | 4,096 | `link_latency` | 82.58 | 0.00 | 0.00 | 0.00 |
| `b200_sxm-x8-nvl72-expert` | 8 | 4096 | 8,192 | 8 | 9 | 0.04 | 166 | 4,096 | `link_latency` | 82.58 | 0.00 | 0.00 | 0.00 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 4096 | 8,192 | 8 | 9 | 4.42 | 18,091 | 4,096 | `link_latency` | 9.62 | 2.89 | 2.55 | 1.97 |
| `b200_sxm-x8-pipeline` | 8 | 4096 | 8,192 | 8 | 9 | 6.79 | 27,794 | 4,096 | `thermal` | 1.55 | 27.61 | 24.37 | 18.80 |
| `b200_sxm-x8-tensor` | 8 | 4096 | 8,192 | 8 | 9 | 4.42 | 18,091 | 4,096 | `link_latency` | 9.62 | 2.89 | 2.55 | 1.97 |

The per-user columns are what one session sees; the aggregate column is what the machine delivers with every slot full. Xiaomi does not say which of those two its number is, and the two differ here by orders of magnitude, so the comparison cannot be closed from the published side.

## Evidence ledger

| grade | entries |
| --- | ---: |
| `assumed` | 2 |
| `derived` | 1 |
| `published` | 8 |

**`assumed`**: `parameters.draft_compute_ops_ratio_rule`; `parameters.drafter_kv_traffic`

**`derived`**: `parameters.drafter_derivation_when_absent`

**`published`**: `acceptance_length`; `baseline_comparators`; `external_acceptance_cross_check`; `parameters.block_size`; `parameters.draft_block_passes`; `parameters.draft_layers`; `parameters.draft_sequential_passes_per_draft_token`; `parameters.mimo_block_size`

## What would change the answer

- The drafter's own KV traffic is not sourced for either drafter and is published as a band. DFlash injects target hidden features from five uniformly selected layers as Key/Value into every draft layer and gives no byte count; DSpark's three MTP stages carry their own cache and the paper gives no byte count. At 200K-1M context this term could dominate the draft pass.
- The ROM draft sweep is the largest single modelled penalty and it rests entirely on the locality rule in src/opentallas/roofline.py. If a designer replicates the drafter across the array, gives it dedicated wide ports, or holds it off-array, the draft weight term collapses and the ROM verdict can change sign. The alternative placement is priced beside it and has not been costed in silicon area.
- The compute headroom that decides whether a verification block flips a design from memory-bound to compute-bound is downstream of the compute efficiency derate, which is graded `assumed` at 0.55 and has never been measured. The block size at which the flip happens is reported on every point so the exposure is visible.
- The DeepSeek-V4-Pro-0813 draft-traffic decomposition published externally (3,770,773,788 B constant plus 132,382,720 B per draft token) does not reproduce from this repository's own configs/models/deepseek-v4-pro-0813.json inventory. Both are reported; neither is silently preferred.
- No speculative decoder has been executed anywhere in this repository. Every rate here is modelled, and the acceptance lengths that turn a break-even into a speedup were measured by other people on other hardware.

