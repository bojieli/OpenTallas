# Speculative decoding on the area-constrained roofline: sota_block_diffusion

> The DFlash / MiMo-UltraSpeed class: a block-diffusion drafter decoding a whole block in one parallel pass. Every figure below is derived from the roofline artifacts
> this repository has already published, by re-assembling each point's own five
> critical-path terms for a speculative cycle. Nothing here re-runs the machine
> model, and nothing here invents an acceptance rate.

## What this layer says

1. **Every term the speculative arithmetic needs is already in the published artifact, exactly.** 180,578 feasible points across 52 studies were rebuilt from their own five critical-path terms and every one reproduced its published step time to 1e-9 relative. Nothing here re-ran the machine model, and the layer is additive by construction rather than by promise.
2. **The headline is a break-even, not a speedup.** `tau* = T_cycle / step_time_s`, and `tau <= gamma+1` always. Of 285,599 (point, draft-placement) pairs where this profile's drafter applies, 78,734 (27.6%) cannot be sped up by speculation at ANY acceptance rate, at any block size on the ladder, even charging the drafter no KV traffic at all.
3. **The ROM-versus-GPU ratio under speculation carries no acceptance rate.** It is `T_cycle(GPU) / T_cycle(ROM)`: `tau` is a property of the model and its drafter, not of the machine, so it is identical on both sides and cancels. Every movement this report shows is a machine effect and nothing else, which is why it can be published without inventing an acceptance rate.
4. **The ratio moves, and it mostly compresses.** Across 983 model-context-batch-class rows, 924 move the ROM-versus-GPU per-user ratio DOWN under speculation and 59 move it UP, spanning 0.083x to 3.307x. The ROM advantage compresses on most operating points.
5. **At batch 1 the two extremes are opposite in sign, and they are the result.** DeepSeek-V4.1-Flash on `array` silicon goes from 3.98x to 0.33x -- a 0.083x movement -- while DeepSeek-V4-Flash-0731 on `wafer` silicon goes from 11.17x to 10.61x, a 0.950x movement. A layer that multiplied both sides by `tau` would have reported neither.
6. **A moving ratio is not a win for either side, and the report says so on every table.** At the most favourable sourced acceptance (7.87) speculation is worth having on 489 of 985 ROM class rows and 896 of 985 GPU rows; everywhere else the design runs SLOWER with a drafter than without one. Where both sides lose, a rising ratio means only that the comparator lost more.
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
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,601 | 481 | 1.42 | 8.68 | 295.30 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 89 | 2 | 2.12 | 6.24 | 17.44 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 440 | 244 | 3.64 | 20.17 | 104.39 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 755 | 755 | 22.67 | 98.83 | 1,861.52 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 48 | 48 | 1,770.60 | 2,147.91 | 2,425.41 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 485 | 403 | 2.50 | 53.95 | 969.02 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 963 | 307 | 1.91 | 12.52 | 625.95 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 345 | 305 | 4.45 | 44.71 | 984.24 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 755 | 755 | 17.37 | 37.17 | 59.44 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 48 | 14 | 4.37 | 12.21 | 45.59 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 485 | 147 | 2.60 | 15.51 | 68.16 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 963 | 170 | 1.82 | 7.05 | 25.33 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 345 | 247 | 4.66 | 31.82 | 37.24 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 1 | 1 | 26.96 | 26.96 | 26.96 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 779 | 273 | 1.68 | 10.71 | 295.22 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 540 | 252 | 3.50 | 17.88 | 99.99 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 739 | 739 | 23.81 | 191.58 | 2,079.02 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 46 | 46 | 30.91 | 2,137.30 | 2,425.41 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 425 | 366 | 3.84 | 62.00 | 928.01 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 919 | 329 | 2.11 | 15.94 | 626.13 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 295 | 278 | 10.83 | 67.99 | 1,835.84 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 739 | 739 | 18.07 | 41.45 | 61.89 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 46 | 19 | 6.00 | 16.56 | 31.03 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 425 | 192 | 2.61 | 15.75 | 71.19 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 919 | 186 | 1.82 | 7.24 | 27.66 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 295 | 197 | 5.19 | 31.64 | 38.33 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,571 | 457 | 1.42 | 8.30 | 295.26 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 82 | 2 | 2.09 | 6.58 | 17.27 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 399 | 232 | 3.95 | 19.94 | 30.18 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 751 | 751 | 21.99 | 67.63 | 444.46 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 126 | 126 | 29.79 | 525.22 | 602.76 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 438 | 352 | 2.54 | 27.88 | 328.66 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 1,008 | 277 | 1.91 | 12.17 | 133.96 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 309 | 266 | 4.62 | 33.49 | 577.28 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 751 | 751 | 18.02 | 39.07 | 59.81 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 126 | 90 | 6.39 | 24.55 | 39.12 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 438 | 154 | 2.65 | 15.27 | 66.59 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 1,008 | 204 | 1.82 | 7.55 | 25.68 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 309 | 206 | 3.29 | 31.54 | 36.88 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 2 | 2 | 20.49 | 20.51 | 20.51 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 780 | 272 | 1.68 | 10.54 | 295.01 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 529 | 249 | 4.24 | 17.63 | 53.76 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 684 | 684 | 23.45 | 111.14 | 489.20 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 125 | 120 | 14.65 | 521.08 | 720.46 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 345 | 275 | 3.87 | 58.26 | 356.95 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 958 | 297 | 2.12 | 15.58 | 134.22 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 244 | 232 | 13.73 | 56.18 | 398.36 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 684 | 684 | 18.18 | 41.99 | 60.95 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 125 | 70 | 3.44 | 19.59 | 48.09 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 345 | 126 | 2.65 | 14.86 | 64.59 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 958 | 196 | 1.83 | 8.03 | 24.74 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 244 | 157 | 5.00 | 31.85 | 43.17 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,485 | 449 | 1.42 | 8.73 | 295.30 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 86 | 3 | 2.14 | 6.46 | 17.54 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 419 | 230 | 3.12 | 20.06 | 119.65 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 736 | 736 | 22.53 | 102.25 | 10,135.28 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 64 | 64 | 4,612.61 | 11,424.36 | 12,020.57 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 470 | 388 | 2.51 | 51.12 | 4,647.95 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 989 | 368 | 1.91 | 12.98 | 5,469.94 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 381 | 337 | 4.46 | 53.03 | 7,241.48 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 736 | 735 | 16.73 | 35.94 | 59.38 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 64 | 8 | 1.82 | 3.55 | 49.04 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 470 | 162 | 2.33 | 15.67 | 65.94 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 989 | 172 | 1.81 | 6.86 | 25.22 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 381 | 270 | 4.62 | 31.48 | 37.41 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 2 | 2 | 25.23 | 25.59 | 25.59 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 719 | 253 | 1.68 | 10.68 | 295.09 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 509 | 240 | 3.33 | 17.94 | 95.86 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 780 | 780 | 24.17 | 175.60 | 10,866.59 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 46 | 46 | 4,627.44 | 11,608.02 | 12,020.57 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 420 | 362 | 3.85 | 61.97 | 4,647.95 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 982 | 390 | 2.11 | 15.99 | 4,680.59 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 312 | 290 | 10.85 | 68.45 | 6,051.26 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 780 | 780 | 18.22 | 39.95 | 62.85 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 46 | 6 | 2.11 | 4.61 | 51.44 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 420 | 223 | 2.50 | 17.14 | 67.59 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 982 | 188 | 1.81 | 7.88 | 26.61 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 312 | 207 | 4.43 | 31.23 | 38.59 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,963 | 563 | 1.36 | 8.63 | 295.32 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 105 | 0 | 1.30 | 3.72 | 7.80 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 542 | 5 | 2.78 | 5.68 | 103.91 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 828 | 156 | 9.84 | 15.35 | 27.75 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 5 | 1 | 8.07 | 11.81 | 17.62 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 631 | 90 | 1.92 | 8.27 | 37.08 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 1,127 | 141 | 1.79 | 5.17 | 21.42 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 628 | 123 | 1.49 | 10.42 | 24.02 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 828 | 628 | 10.43 | 17.51 | 28.00 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 5 | 1 | 11.62 | 14.41 | 18.14 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 631 | 100 | 2.63 | 9.96 | 70.92 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 1,127 | 149 | 1.82 | 5.99 | 26.41 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 628 | 428 | 3.66 | 21.91 | 34.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 3 | 3 | 17.39 | 17.66 | 17.68 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 996 | 341 | 1.61 | 10.53 | 295.22 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 681 | 3 | 1.93 | 4.15 | 99.19 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 717 | 288 | 10.68 | 16.69 | 17.71 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 107 | 89 | 5.00 | 36.95 | 44.76 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 547 | 83 | 1.92 | 9.38 | 39.29 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 1,077 | 152 | 1.79 | 5.27 | 20.37 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 510 | 143 | 2.23 | 12.12 | 39.26 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 717 | 580 | 10.72 | 18.11 | 31.60 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 107 | 66 | 6.34 | 22.17 | 22.96 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 547 | 93 | 2.61 | 10.74 | 71.25 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 1,077 | 156 | 1.82 | 6.08 | 22.83 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 510 | 347 | 3.92 | 23.63 | 34.15 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 2,124 | 595 | 1.36 | 8.32 | 295.26 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 104 | 0 | 1.30 | 4.02 | 7.63 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 536 | 0 | 2.84 | 5.63 | 31.15 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 738 | 82 | 9.39 | 15.29 | 17.17 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 70 | 32 | 4.12 | 13.31 | 17.01 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 551 | 71 | 1.94 | 7.74 | 36.71 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 1,011 | 126 | 1.79 | 5.30 | 21.66 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 411 | 60 | 2.23 | 9.39 | 20.00 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 738 | 552 | 9.75 | 17.28 | 28.23 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 70 | 0 | 4.93 | 12.96 | 15.04 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 551 | 125 | 2.66 | 10.25 | 66.65 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 1,011 | 130 | 1.82 | 6.10 | 26.19 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 411 | 291 | 3.30 | 22.80 | 34.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 1 | 0 | 14.46 | 14.46 | 14.46 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,013 | 339 | 1.61 | 10.07 | 294.96 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 657 | 0 | 2.34 | 4.10 | 53.86 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 671 | 196 | 8.89 | 16.66 | 17.71 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 86 | 0 | 2.62 | 12.80 | 15.99 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 390 | 46 | 1.94 | 6.75 | 36.68 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 982 | 136 | 1.79 | 5.29 | 20.45 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 334 | 74 | 2.63 | 12.54 | 24.82 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 671 | 567 | 8.99 | 18.18 | 30.73 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 86 | 9 | 2.76 | 9.14 | 18.82 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 390 | 57 | 2.64 | 8.56 | 63.84 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 982 | 140 | 1.82 | 5.86 | 22.59 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 334 | 234 | 4.06 | 24.14 | 34.12 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,865 | 537 | 1.36 | 8.83 | 295.32 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 99 | 0 | 1.30 | 3.84 | 7.85 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 526 | 7 | 2.13 | 5.70 | 119.09 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 838 | 168 | 9.46 | 15.31 | 28.97 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 643 | 96 | 1.92 | 9.10 | 34.12 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 1,135 | 142 | 1.79 | 5.11 | 21.23 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 660 | 133 | 1.28 | 10.12 | 25.26 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 838 | 650 | 10.08 | 17.64 | 28.67 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 643 | 107 | 2.54 | 12.03 | 67.71 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 1,135 | 153 | 1.82 | 6.02 | 26.24 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 660 | 434 | 3.65 | 21.67 | 34.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 4 | 4 | 17.53 | 17.71 | 17.80 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,008 | 345 | 1.61 | 10.48 | 295.15 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 698 | 3 | 1.79 | 4.16 | 95.02 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 800 | 392 | 10.32 | 16.97 | 50.51 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 530 | 88 | 1.92 | 9.31 | 35.65 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 1,095 | 154 | 1.79 | 5.36 | 20.19 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 553 | 154 | 1.94 | 12.38 | 39.88 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 800 | 667 | 10.39 | 18.41 | 31.14 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 530 | 92 | 2.57 | 10.52 | 67.66 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 1,095 | 160 | 1.82 | 5.99 | 22.66 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 553 | 377 | 3.88 | 23.58 | 34.15 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 1,455 | 435 | 1.36 | 8.84 | 295.32 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `thermal` | 95 | 0 | 1.29 | 3.21 | 7.80 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 450 | 6 | 2.62 | 5.68 | 107.02 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 828 | 198 | 9.84 | 15.73 | 37.05 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 51 | 49 | 7.54 | 35.06 | 38.28 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `layer_fixed_latency` | 654 | 95 | 2.25 | 9.50 | 37.52 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 1,109 | 141 | 1.79 | 5.46 | 21.42 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 566 | 105 | 2.64 | 11.20 | 25.18 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 828 | 618 | 10.43 | 17.31 | 22.79 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 51 | 3 | 2.09 | 9.11 | 18.14 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `layer_fixed_latency` | 654 | 102 | 2.34 | 9.96 | 68.22 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 1,109 | 149 | 1.82 | 5.98 | 26.41 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 566 | 388 | 4.98 | 21.91 | 34.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `compute` | 6 | 6 | 17.40 | 17.66 | 17.68 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 830 | 306 | 1.61 | 11.96 | 295.23 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 684 | 5 | 1.93 | 4.15 | 74.59 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 692 | 302 | 10.68 | 16.88 | 40.86 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 151 | 133 | 5.00 | 36.90 | 44.77 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `layer_fixed_latency` | 548 | 87 | 2.25 | 11.76 | 39.29 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 1,058 | 152 | 1.79 | 5.30 | 20.37 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 499 | 139 | 2.64 | 12.12 | 39.26 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 692 | 545 | 10.72 | 17.73 | 25.98 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 151 | 66 | 2.63 | 16.47 | 22.97 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `layer_fixed_latency` | 548 | 93 | 2.45 | 10.70 | 71.26 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 1,058 | 156 | 1.82 | 5.91 | 22.83 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 499 | 335 | 3.86 | 23.51 | 34.15 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `compute` | 5 | 0 | 12.57 | 14.29 | 16.72 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 1,030 | 313 | 1.42 | 11.29 | 291.39 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `thermal` | 288 | 0 | 3.92 | 4.03 | 15.01 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 403 | 0 | 2.05 | 4.09 | 69.61 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 522 | 226 | 9.85 | 16.97 | 19.74 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 61 | 11 | 3.52 | 11.52 | 18.17 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 215 | 41 | 2.46 | 14.28 | 24.84 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 651 | 60 | 1.88 | 7.16 | 18.19 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 147 | 33 | 3.19 | 16.78 | 18.61 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `compute` | 522 | 412 | 10.31 | 17.50 | 19.07 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 61 | 14 | 3.92 | 13.25 | 28.48 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 215 | 56 | 3.03 | 15.04 | 35.79 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 651 | 64 | 1.87 | 7.49 | 19.78 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 147 | 89 | 5.21 | 27.15 | 34.26 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `compute` | 4 | 1 | 15.35 | 16.54 | 17.07 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 454 | 144 | 2.40 | 7.83 | 290.44 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 436 | 3 | 2.15 | 3.21 | 111.91 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 392 | 274 | 10.35 | 17.19 | 20.30 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 65 | 1 | 3.28 | 8.74 | 17.36 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 168 | 27 | 2.55 | 13.92 | 23.37 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 432 | 42 | 1.84 | 6.57 | 18.08 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 143 | 71 | 2.98 | 16.90 | 18.25 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `compute` | 392 | 274 | 10.41 | 17.23 | 19.56 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 65 | 0 | 3.48 | 7.95 | 16.20 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 168 | 38 | 3.11 | 14.94 | 33.44 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 432 | 44 | 1.83 | 6.93 | 18.96 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 143 | 85 | 3.89 | 28.59 | 34.26 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `compute` | 20 | 1 | 8.03 | 10.14 | 62.37 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 723 | 184 | 1.28 | 7.46 | 290.21 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `thermal` | 239 | 0 | 4.84 | 4.84 | 15.97 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 183 | 0 | 1.86 | 3.99 | 65.40 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 45 | 40 | 8.29 | 17.32 | 17.69 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 58 | 0 | 2.06 | 4.57 | 14.94 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 69 | 0 | 2.58 | 12.55 | 24.63 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 158 | 0 | 1.61 | 3.37 | 9.99 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 48 | 13 | 2.31 | 8.61 | 17.16 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `compute` | 45 | 40 | 8.46 | 17.35 | 20.22 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 58 | 0 | 2.00 | 8.14 | 14.63 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 69 | 12 | 3.10 | 14.92 | 35.31 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 158 | 0 | 1.61 | 3.43 | 14.92 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 48 | 20 | 3.74 | 16.76 | 34.26 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `compute` | 39 | 4 | 13.11 | 16.16 | 17.12 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 399 | 98 | 2.42 | 8.19 | 286.06 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 345 | 3 | 1.73 | 6.46 | 107.62 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 51 | 35 | 10.13 | 17.41 | 17.69 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 59 | 0 | 2.19 | 3.51 | 8.95 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 66 | 2 | 2.53 | 13.51 | 23.40 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 136 | 0 | 1.55 | 3.29 | 11.10 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 45 | 12 | 2.52 | 10.06 | 17.29 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `compute` | 51 | 35 | 10.13 | 17.41 | 19.83 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 59 | 0 | 1.79 | 5.30 | 8.33 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 66 | 12 | 3.21 | 13.79 | 33.34 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 136 | 0 | 1.55 | 3.47 | 14.14 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 45 | 24 | 4.14 | 19.62 | 34.26 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 840 | 271 | 1.46 | 11.36 | 291.65 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `thermal` | 210 | 0 | 2.21 | 3.79 | 5.58 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 369 | 3 | 2.05 | 3.81 | 76.42 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 458 | 116 | 10.43 | 16.86 | 29.44 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 95 | 67 | 8.50 | 22.11 | 25.57 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 347 | 40 | 2.43 | 9.57 | 24.81 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 562 | 54 | 1.88 | 6.22 | 18.79 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 206 | 37 | 3.14 | 15.10 | 25.75 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `compute` | 458 | 388 | 10.66 | 18.20 | 22.76 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 95 | 40 | 9.27 | 14.72 | 19.31 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 347 | 56 | 3.02 | 10.76 | 36.51 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 562 | 58 | 1.82 | 6.61 | 20.53 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 206 | 108 | 6.14 | 22.60 | 34.26 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `compute` | 2 | 0 | 14.04 | 14.07 | 14.07 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 405 | 125 | 2.40 | 8.30 | 291.31 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 391 | 2 | 2.18 | 3.22 | 113.67 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 278 | 234 | 9.98 | 17.26 | 30.02 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 104 | 68 | 8.52 | 21.75 | 28.89 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 217 | 24 | 2.52 | 12.37 | 22.02 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 454 | 36 | 2.08 | 6.91 | 18.42 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 195 | 90 | 3.52 | 14.99 | 25.92 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `compute` | 278 | 232 | 10.29 | 17.70 | 18.90 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 104 | 16 | 7.40 | 13.18 | 18.49 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 217 | 40 | 3.08 | 12.38 | 32.07 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 454 | 38 | 2.03 | 7.20 | 19.35 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 195 | 105 | 4.77 | 25.76 | 34.26 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 125 | 0 | 1.58 | 2.47 | 75.50 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 950 | 193 | 1.26 | 4.13 | 293.76 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 63 | 0 | 1.65 | 2.41 | 4.66 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 259 | 0 | 1.82 | 4.69 | 34.22 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 8 | 0 | 14.81 | 15.74 | 15.80 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 224 | 0 | 1.18 | 4.21 | 14.98 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 169 | 5 | 2.32 | 12.61 | 36.95 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 589 | 45 | 1.70 | 3.74 | 21.91 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `thermal` | 301 | 0 | 3.26 | 4.23 | 7.99 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 129 | 18 | 2.39 | 11.84 | 17.27 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 8 | 4 | 16.24 | 17.23 | 17.28 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 224 | 26 | 1.11 | 6.86 | 28.10 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 169 | 22 | 2.31 | 12.87 | 66.43 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 589 | 48 | 1.74 | 4.57 | 28.44 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `thermal` | 301 | 0 | 3.41 | 8.46 | 11.80 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 129 | 70 | 3.90 | 22.55 | 34.30 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 36 | 0 | 2.12 | 2.80 | 9.67 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 422 | 103 | 1.44 | 8.87 | 293.00 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 373 | 0 | 1.84 | 3.34 | 39.16 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 22 | 2 | 14.64 | 16.18 | 17.04 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 434 | 0 | 1.23 | 3.44 | 12.86 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 125 | 0 | 2.32 | 10.92 | 32.55 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 515 | 36 | 1.69 | 3.27 | 20.60 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 128 | 29 | 2.61 | 10.88 | 17.28 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 22 | 12 | 16.06 | 17.16 | 17.86 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 434 | 0 | 1.06 | 5.18 | 14.50 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 125 | 12 | 2.54 | 11.79 | 57.20 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 515 | 37 | 1.71 | 3.38 | 24.32 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 128 | 74 | 4.29 | 20.57 | 34.30 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 336 | 7 | 1.53 | 2.15 | 92.03 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 598 | 91 | 1.19 | 3.65 | 291.56 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 222 | 0 | 1.74 | 3.36 | 3.36 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 3 | 3 | 17.14 | 17.14 | 17.16 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 89 | 0 | 1.16 | 1.23 | 15.51 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 150 | 20 | 2.46 | 12.85 | 36.39 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 181 | 0 | 1.52 | 3.26 | 8.79 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 49 | 11 | 2.98 | 13.87 | 17.03 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 3 | 3 | 17.27 | 17.27 | 17.28 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 89 | 1 | 1.06 | 1.82 | 17.36 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 150 | 39 | 2.89 | 13.14 | 65.10 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 181 | 0 | 1.53 | 3.49 | 15.47 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 49 | 28 | 5.69 | 27.69 | 34.30 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 400 | 3 | 1.92 | 2.31 | 85.45 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 475 | 55 | 1.26 | 3.70 | 278.01 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 39 | 0 | 2.98 | 10.22 | 27.70 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 41 | 27 | 16.25 | 17.30 | 17.78 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 107 | 0 | 1.11 | 1.47 | 16.88 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 80 | 7 | 2.47 | 10.76 | 32.12 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 195 | 0 | 1.48 | 3.73 | 10.45 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 49 | 11 | 3.09 | 14.63 | 17.05 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 41 | 28 | 16.86 | 17.40 | 18.76 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 107 | 2 | 1.03 | 1.53 | 18.72 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 80 | 20 | 2.96 | 10.91 | 56.19 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 195 | 0 | 1.48 | 3.92 | 14.36 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 49 | 28 | 5.94 | 29.24 | 34.31 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 19 | 0 | 6.22 | 8.35 | 10.83 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 969 | 285 | 1.28 | 7.42 | 294.27 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 61 | 0 | 1.27 | 1.61 | 3.86 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 421 | 0 | 1.91 | 5.46 | 60.05 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 478 | 121 | 9.90 | 16.26 | 28.47 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 182 | 117 | 2.52 | 22.00 | 33.00 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 562 | 62 | 2.28 | 9.47 | 42.14 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 899 | 92 | 1.66 | 4.68 | 25.44 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 583 | 46 | 2.37 | 12.50 | 27.18 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 478 | 213 | 9.93 | 16.87 | 18.46 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 182 | 2 | 1.30 | 7.03 | 27.40 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 562 | 82 | 2.20 | 9.07 | 79.71 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 899 | 100 | 1.67 | 4.60 | 36.45 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 583 | 214 | 5.47 | 15.03 | 34.30 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `compute` | 18 | 4 | 12.32 | 14.29 | 17.49 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 604 | 262 | 1.61 | 14.46 | 294.23 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 738 | 4 | 1.54 | 4.00 | 83.77 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 614 | 339 | 10.76 | 17.02 | 31.83 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 275 | 150 | 1.85 | 20.79 | 33.30 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 558 | 68 | 2.28 | 10.25 | 37.18 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 1,067 | 114 | 1.67 | 4.86 | 21.86 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 562 | 176 | 3.28 | 14.37 | 31.65 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 614 | 304 | 10.45 | 16.96 | 20.71 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 275 | 18 | 1.39 | 6.01 | 28.21 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 558 | 73 | 2.25 | 9.73 | 67.45 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 1,067 | 118 | 1.67 | 4.84 | 27.01 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 562 | 231 | 4.22 | 15.23 | 34.30 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 65 | 0 | 1.68 | 3.10 | 5.73 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 674 | 140 | 1.25 | 6.95 | 291.92 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 41 | 0 | 1.65 | 4.01 | 4.85 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 323 | 0 | 2.08 | 4.24 | 60.98 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 10 | 2 | 16.45 | 16.82 | 17.15 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 104 | 0 | 1.25 | 2.54 | 14.40 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 68 | 0 | 2.30 | 11.00 | 31.35 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 189 | 0 | 1.64 | 2.80 | 10.27 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 49 | 13 | 2.36 | 10.15 | 17.09 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 10 | 10 | 17.09 | 17.29 | 17.87 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 104 | 0 | 1.16 | 5.26 | 16.50 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 68 | 16 | 2.71 | 11.84 | 51.47 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 189 | 0 | 1.66 | 2.98 | 15.07 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 49 | 28 | 3.99 | 19.73 | 34.17 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 16 | 0 | 2.44 | 2.74 | 3.19 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 363 | 78 | 2.34 | 7.80 | 290.81 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 392 | 1 | 1.49 | 2.89 | 74.31 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 18 | 6 | 15.99 | 16.93 | 17.30 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 94 | 0 | 1.34 | 1.72 | 16.42 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 45 | 0 | 2.14 | 7.93 | 28.49 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 200 | 0 | 1.59 | 3.03 | 9.33 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 81 | 12 | 2.52 | 11.22 | 17.18 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 18 | 18 | 17.05 | 17.35 | 18.94 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 94 | 8 | 1.11 | 3.97 | 18.68 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 45 | 0 | 2.86 | 9.36 | 46.13 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 200 | 0 | 1.58 | 3.14 | 13.99 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 81 | 44 | 4.28 | 21.85 | 34.17 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 254 | 0 | 1.60 | 2.24 | 68.79 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 832 | 114 | 1.15 | 4.55 | 283.29 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 221 | 0 | 1.81 | 3.14 | 3.20 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 6 | 0 | 9.06 | 11.82 | 24.91 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 12 | 7 | 10.50 | 17.03 | 17.61 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 90 | 0 | 1.12 | 1.19 | 13.00 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 157 | 26 | 2.28 | 14.06 | 30.96 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 167 | 0 | 1.41 | 3.09 | 9.45 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 51 | 11 | 2.76 | 14.72 | 17.02 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 12 | 8 | 10.50 | 18.01 | 19.20 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 90 | 0 | 1.08 | 1.62 | 15.27 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 157 | 60 | 2.98 | 14.70 | 50.62 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 167 | 0 | 1.41 | 3.23 | 15.19 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 51 | 28 | 5.32 | 29.38 | 34.19 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 276 | 0 | 1.81 | 2.17 | 75.68 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 381 | 46 | 2.15 | 4.31 | 263.40 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 150 | 0 | 1.22 | 4.19 | 55.30 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 39 | 26 | 9.38 | 17.17 | 17.48 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 85 | 0 | 1.09 | 1.15 | 12.04 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 91 | 9 | 2.28 | 12.17 | 28.21 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 167 | 0 | 1.38 | 3.37 | 9.01 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 50 | 11 | 2.84 | 15.31 | 17.04 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 39 | 35 | 9.38 | 17.55 | 19.79 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 85 | 0 | 1.04 | 1.38 | 14.79 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 91 | 26 | 3.00 | 12.55 | 45.53 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 167 | 0 | 1.38 | 3.41 | 14.26 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 50 | 28 | 5.49 | 30.20 | 34.19 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 2 | 0 | 8.76 | 9.81 | 9.81 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 1,125 | 352 | 1.35 | 9.89 | 292.60 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 68 | 0 | 1.29 | 2.76 | 6.09 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 625 | 6 | 1.92 | 4.73 | 102.03 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 604 | 80 | 9.79 | 16.35 | 28.01 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 170 | 83 | 2.54 | 16.95 | 27.74 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 469 | 58 | 2.37 | 7.79 | 34.11 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 1,136 | 124 | 1.66 | 5.94 | 20.51 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 577 | 45 | 2.96 | 12.56 | 22.07 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 604 | 500 | 10.24 | 17.63 | 23.17 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 170 | 2 | 1.87 | 9.57 | 17.89 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 469 | 74 | 2.33 | 8.39 | 58.24 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 1,136 | 137 | 1.68 | 5.94 | 24.49 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 577 | 334 | 4.57 | 19.20 | 34.17 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `compute` | 2 | 0 | 12.78 | 15.14 | 15.14 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 571 | 225 | 2.35 | 12.65 | 292.49 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 666 | 6 | 1.67 | 3.27 | 85.05 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 566 | 256 | 10.38 | 16.98 | 27.91 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 201 | 104 | 1.74 | 17.23 | 28.75 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 373 | 39 | 2.10 | 8.40 | 31.48 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 1,003 | 110 | 1.68 | 5.83 | 19.51 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 401 | 127 | 2.95 | 15.27 | 28.06 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 566 | 479 | 10.44 | 17.92 | 24.88 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 201 | 2 | 2.15 | 8.53 | 18.05 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 373 | 45 | 2.49 | 9.18 | 52.38 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 1,003 | 121 | 1.70 | 5.89 | 22.37 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 401 | 278 | 4.45 | 21.92 | 34.17 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 261 | 0 | 1.03 | 1.41 | 8.80 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 108 | 4 | 1.51 | 2.04 | 17.36 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 171 | 0 | 1.01 | 1.03 | 1.11 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 9 | 0 | 1.17 | 2.29 | 6.04 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 107 | 14 | 2.33 | 12.18 | 17.24 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 95 | 0 | 1.51 | 5.95 | 8.72 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 23 | 0 | 1.02 | 4.61 | 16.79 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 9 | 0 | 1.17 | 2.29 | 6.04 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 107 | 24 | 2.33 | 13.49 | 22.29 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 95 | 0 | 2.02 | 6.14 | 9.25 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 23 | 4 | 2.27 | 5.72 | 37.19 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 330 | 0 | 1.02 | 1.42 | 9.00 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 51 | 2 | 1.84 | 3.00 | 17.66 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 9 | 0 | 1.21 | 3.23 | 11.19 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 95 | 12 | 2.46 | 12.29 | 17.32 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 87 | 0 | 1.51 | 4.79 | 7.42 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 25 | 0 | 1.03 | 3.93 | 16.79 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 9 | 0 | 1.21 | 3.23 | 12.19 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 95 | 20 | 2.46 | 12.83 | 23.36 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 87 | 0 | 2.02 | 5.31 | 9.25 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 25 | 4 | 2.27 | 5.08 | 37.19 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 238 | 0 | 1.07 | 1.20 | 8.42 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 221 | 10 | 1.18 | 2.63 | 18.90 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 197 | 0 | 1.04 | 1.09 | 1.59 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 83 | 0 | 1.02 | 1.20 | 10.41 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 136 | 6 | 2.10 | 10.37 | 17.35 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 125 | 0 | 1.49 | 3.14 | 7.45 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 104 | 24 | 1.02 | 14.55 | 17.03 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 83 | 0 | 1.02 | 1.21 | 10.41 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 136 | 30 | 2.10 | 11.79 | 22.39 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 125 | 0 | 1.61 | 3.41 | 15.24 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 104 | 56 | 2.18 | 31.10 | 38.00 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 326 | 0 | 1.04 | 1.07 | 8.02 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 175 | 5 | 1.47 | 2.48 | 19.03 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 91 | 0 | 1.02 | 1.37 | 11.08 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 92 | 6 | 2.18 | 10.31 | 17.59 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 144 | 0 | 1.49 | 3.26 | 8.11 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 103 | 24 | 1.03 | 14.27 | 17.03 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 91 | 0 | 1.01 | 1.29 | 11.08 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 92 | 22 | 2.18 | 11.76 | 23.36 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 144 | 0 | 1.57 | 3.39 | 14.18 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 103 | 56 | 2.18 | 30.47 | 38.00 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,068 | 398 | 2.83 | 14.61 | 272.04 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 25 | 0 | 2.00 | 2.97 | 4.54 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 294 | 0 | 2.99 | 4.26 | 5.99 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 133 | 1 | 11.86 | 14.29 | 17.02 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 57 | 0 | 1.94 | 4.90 | 13.98 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 123 | 0 | 2.17 | 7.01 | 10.88 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 505 | 128 | 2.63 | 10.33 | 23.18 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `thermal` | 14 | 0 | 10.16 | 10.61 | 11.96 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 266 | 28 | 1.84 | 6.63 | 17.04 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 133 | 12 | 13.88 | 16.17 | 20.47 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 57 | 0 | 1.94 | 6.91 | 14.42 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 123 | 0 | 2.27 | 7.67 | 16.92 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 505 | 131 | 2.67 | 11.12 | 31.43 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `thermal` | 14 | 0 | 11.56 | 12.54 | 15.41 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 266 | 128 | 3.99 | 16.79 | 34.15 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,221 | 399 | 1.54 | 10.95 | 294.65 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 67 | 0 | 1.32 | 2.21 | 4.55 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 302 | 0 | 3.34 | 4.58 | 48.49 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 461 | 77 | 10.36 | 15.78 | 17.34 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 44 | 36 | 6.13 | 22.49 | 26.17 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 795 | 89 | 2.05 | 8.91 | 33.54 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,093 | 244 | 2.01 | 7.24 | 24.58 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 419 | 38 | 1.84 | 6.86 | 19.55 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 461 | 75 | 10.75 | 16.05 | 17.66 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 44 | 0 | 2.05 | 10.88 | 14.23 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 795 | 46 | 2.14 | 11.73 | 63.14 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,093 | 250 | 2.02 | 7.45 | 36.45 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 419 | 133 | 4.86 | 13.61 | 34.15 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,184 | 391 | 1.50 | 10.67 | 294.70 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 69 | 0 | 1.32 | 2.29 | 9.29 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 327 | 2 | 3.05 | 4.60 | 65.44 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 465 | 92 | 10.32 | 15.82 | 34.58 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 52 | 51 | 11.00 | 49.17 | 59.70 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 813 | 103 | 2.05 | 8.62 | 39.35 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,081 | 224 | 1.97 | 7.04 | 20.00 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 417 | 36 | 1.73 | 6.53 | 37.34 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 465 | 75 | 10.54 | 16.01 | 17.72 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 52 | 0 | 1.61 | 8.15 | 16.44 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 813 | 55 | 2.06 | 12.08 | 62.46 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,081 | 232 | 1.99 | 7.17 | 22.39 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 417 | 130 | 4.83 | 13.46 | 34.14 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,548 | 578 | 2.00 | 14.44 | 291.43 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 82 | 0 | 1.57 | 5.46 | 7.39 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 455 | 0 | 3.59 | 5.50 | 8.90 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 647 | 24 | 10.10 | 14.84 | 17.06 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 48 | 0 | 3.88 | 14.12 | 15.68 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 273 | 6 | 1.77 | 6.67 | 17.56 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 998 | 280 | 2.27 | 10.23 | 23.60 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 302 | 23 | 2.35 | 11.12 | 17.56 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 647 | 511 | 10.26 | 17.58 | 24.33 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 48 | 26 | 5.88 | 17.12 | 19.17 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 273 | 8 | 2.17 | 8.56 | 18.31 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 998 | 290 | 2.29 | 10.82 | 33.22 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 302 | 188 | 3.67 | 23.02 | 34.08 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,518 | 547 | 1.76 | 13.42 | 292.93 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 87 | 0 | 1.31 | 5.09 | 7.49 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 435 | 0 | 2.54 | 5.53 | 32.63 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 687 | 132 | 10.14 | 15.55 | 34.43 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 24 | 24 | 29.92 | 32.45 | 33.88 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 398 | 20 | 1.79 | 6.20 | 29.03 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 949 | 233 | 2.11 | 8.91 | 19.95 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 360 | 30 | 2.55 | 10.70 | 20.15 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 687 | 542 | 9.75 | 17.83 | 23.76 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 24 | 2 | 6.65 | 13.72 | 17.43 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 398 | 25 | 2.08 | 9.02 | 47.69 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 949 | 239 | 2.11 | 9.93 | 24.89 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 360 | 225 | 4.32 | 21.83 | 34.08 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,385 | 498 | 1.73 | 13.33 | 292.73 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 82 | 0 | 1.31 | 5.10 | 7.51 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 423 | 2 | 2.54 | 5.54 | 82.46 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 696 | 118 | 10.15 | 15.46 | 62.80 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 34 | 34 | 57.64 | 60.86 | 66.48 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 405 | 40 | 1.79 | 6.16 | 26.91 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 983 | 238 | 2.07 | 9.51 | 19.85 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 378 | 34 | 2.54 | 10.85 | 32.30 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 696 | 550 | 11.37 | 17.93 | 23.82 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 34 | 4 | 3.58 | 9.65 | 18.13 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 405 | 26 | 2.07 | 9.24 | 45.93 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 983 | 244 | 2.07 | 9.91 | 25.02 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 378 | 235 | 4.22 | 21.22 | 34.08 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 668 | 286 | 3.77 | 15.56 | 224.97 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 295 | 0 | 3.13 | 3.23 | 7.73 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 56 | 4 | 12.38 | 14.89 | 17.27 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 128 | 0 | 1.57 | 5.28 | 15.18 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 63 | 0 | 2.22 | 2.70 | 11.24 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 421 | 89 | 2.69 | 9.16 | 23.08 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 166 | 37 | 2.22 | 7.61 | 17.16 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 56 | 26 | 15.53 | 16.96 | 21.86 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 128 | 24 | 1.46 | 9.34 | 25.99 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 63 | 2 | 2.08 | 4.92 | 17.59 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 421 | 103 | 2.72 | 10.56 | 30.21 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 166 | 93 | 4.26 | 17.53 | 34.30 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 2 | 1 | 15.87 | 17.00 | 17.00 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 904 | 333 | 1.85 | 14.10 | 294.40 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 454 | 0 | 1.90 | 3.62 | 14.88 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 573 | 96 | 9.19 | 16.01 | 21.79 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 137 | 91 | 3.54 | 22.98 | 26.38 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 644 | 32 | 2.05 | 9.02 | 35.30 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,202 | 282 | 2.01 | 8.40 | 25.25 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 448 | 52 | 2.86 | 8.81 | 22.59 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 573 | 137 | 9.19 | 16.47 | 18.32 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 137 | 0 | 2.72 | 12.50 | 15.51 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 644 | 108 | 2.22 | 11.52 | 63.58 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,202 | 296 | 2.03 | 8.60 | 36.77 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 448 | 168 | 5.07 | 14.79 | 34.15 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 1 | 1 | 17.20 | 17.20 | 17.20 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 846 | 308 | 1.78 | 14.11 | 294.43 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 463 | 0 | 1.84 | 3.65 | 49.62 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 558 | 146 | 10.62 | 16.36 | 44.92 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 62 | 58 | 6.34 | 46.75 | 59.70 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 741 | 96 | 2.05 | 10.30 | 34.94 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,202 | 271 | 1.97 | 8.03 | 24.83 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 465 | 58 | 2.85 | 9.67 | 33.85 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 558 | 125 | 11.35 | 16.40 | 18.37 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 62 | 2 | 1.80 | 8.73 | 18.25 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 741 | 97 | 2.10 | 11.43 | 63.92 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,202 | 286 | 1.99 | 8.12 | 37.31 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 465 | 169 | 5.04 | 14.59 | 34.15 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 585 | 347 | 4.74 | 18.16 | 285.79 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 794 | 0 | 2.17 | 3.81 | 18.39 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 622 | 68 | 9.55 | 15.74 | 18.44 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 44 | 5 | 2.67 | 12.19 | 18.15 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 207 | 6 | 1.83 | 6.39 | 17.41 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 964 | 260 | 2.13 | 10.75 | 23.59 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 239 | 28 | 2.63 | 13.35 | 19.79 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 622 | 530 | 9.82 | 18.09 | 26.09 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 44 | 21 | 3.48 | 15.24 | 23.59 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 207 | 6 | 2.16 | 8.36 | 17.41 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 964 | 272 | 2.29 | 11.28 | 31.82 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 239 | 126 | 4.56 | 25.41 | 34.08 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 491 | 306 | 6.34 | 18.29 | 291.68 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 748 | 1 | 1.99 | 3.83 | 61.64 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 609 | 146 | 9.74 | 15.95 | 38.05 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 23 | 20 | 5.46 | 34.31 | 37.85 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 312 | 16 | 1.79 | 7.42 | 28.85 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 854 | 218 | 2.10 | 9.73 | 20.16 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 248 | 45 | 2.57 | 13.78 | 22.57 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 609 | 535 | 10.03 | 18.41 | 26.57 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 23 | 7 | 8.83 | 15.61 | 20.42 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 312 | 22 | 2.10 | 8.28 | 45.15 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 854 | 223 | 2.08 | 10.03 | 24.89 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 248 | 152 | 4.81 | 24.55 | 34.09 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 1 | 1 | 17.58 | 17.58 | 17.58 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 483 | 314 | 5.44 | 18.30 | 292.68 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 796 | 1 | 1.95 | 3.84 | 81.14 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 677 | 147 | 9.77 | 15.80 | 67.26 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 29 | 28 | 10.48 | 63.17 | 69.80 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 359 | 35 | 1.80 | 7.50 | 29.65 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 890 | 232 | 2.14 | 9.87 | 19.95 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 259 | 51 | 2.56 | 14.78 | 29.27 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 677 | 595 | 10.07 | 18.27 | 26.63 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 29 | 8 | 4.92 | 11.24 | 18.64 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 359 | 22 | 2.08 | 8.60 | 48.13 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 890 | 238 | 2.12 | 10.16 | 24.90 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 259 | 161 | 4.78 | 24.32 | 34.09 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 1,056 | 355 | 1.79 | 11.98 | 293.18 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 42 | 0 | 1.39 | 2.21 | 4.65 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 275 | 0 | 3.14 | 4.45 | 7.15 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 229 | 27 | 10.84 | 16.03 | 17.15 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 68 | 0 | 2.47 | 9.68 | 12.03 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 589 | 13 | 2.04 | 8.78 | 29.14 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,015 | 261 | 2.04 | 9.21 | 22.71 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 411 | 30 | 2.31 | 6.11 | 17.55 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 229 | 48 | 12.94 | 16.67 | 18.29 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 68 | 0 | 2.98 | 8.12 | 14.10 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 589 | 14 | 2.19 | 12.74 | 49.04 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,015 | 266 | 2.13 | 9.85 | 30.29 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 411 | 121 | 3.81 | 14.65 | 34.15 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,131 | 451 | 2.83 | 15.19 | 267.15 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 40 | 0 | 3.69 | 6.36 | 6.94 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 315 | 0 | 3.89 | 5.35 | 6.36 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 106 | 2 | 12.80 | 14.76 | 17.05 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 44 | 0 | 2.19 | 6.95 | 14.15 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 88 | 0 | 1.95 | 3.22 | 12.24 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 366 | 78 | 2.68 | 9.30 | 20.17 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 194 | 14 | 2.54 | 8.50 | 17.06 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 106 | 98 | 12.81 | 19.29 | 24.83 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 44 | 16 | 2.72 | 7.78 | 25.42 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 88 | 1 | 2.32 | 5.11 | 19.04 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 366 | 84 | 2.73 | 11.30 | 23.49 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 194 | 99 | 3.57 | 21.50 | 34.08 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 115 | 0 | 1.38 | 2.55 | 9.31 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 325 | 46 | 1.25 | 4.31 | 19.10 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 66 | 0 | 1.25 | 1.60 | 2.41 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 279 | 0 | 1.20 | 1.24 | 1.70 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 8 | 0 | 14.87 | 15.70 | 15.88 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 187 | 0 | 1.16 | 3.96 | 15.63 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 301 | 18 | 2.40 | 10.02 | 17.87 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 789 | 86 | 1.54 | 4.75 | 18.87 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `thermal` | 484 | 0 | 3.54 | 9.69 | 10.48 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 526 | 38 | 1.08 | 1.79 | 17.37 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `compute` | 8 | 0 | 14.87 | 15.70 | 15.88 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 187 | 0 | 1.09 | 2.29 | 15.63 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 301 | 36 | 2.09 | 10.31 | 20.68 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 789 | 94 | 1.87 | 5.21 | 27.45 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `thermal` | 484 | 0 | 3.57 | 9.29 | 10.48 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 526 | 182 | 1.96 | 2.42 | 37.99 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 880 | 335 | 2.29 | 14.08 | 289.96 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 418 | 0 | 2.39 | 3.35 | 11.01 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 399 | 19 | 11.06 | 13.85 | 17.12 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 99 | 0 | 2.00 | 8.49 | 16.00 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 274 | 0 | 2.04 | 6.88 | 12.14 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,008 | 251 | 2.07 | 9.33 | 29.12 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 370 | 24 | 2.95 | 7.89 | 17.56 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 399 | 178 | 13.90 | 16.78 | 20.01 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 99 | 9 | 1.96 | 7.88 | 19.81 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 274 | 0 | 2.21 | 8.31 | 16.20 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,008 | 259 | 2.12 | 9.58 | 46.80 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 370 | 123 | 4.83 | 15.37 | 34.15 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 574 | 265 | 3.41 | 16.99 | 224.06 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 393 | 0 | 3.70 | 3.70 | 6.67 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 53 | 6 | 14.36 | 15.41 | 17.22 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 54 | 0 | 1.98 | 3.93 | 14.93 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 55 | 0 | 1.98 | 2.79 | 9.99 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 193 | 18 | 2.82 | 8.70 | 20.06 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 68 | 12 | 2.57 | 9.06 | 17.11 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 53 | 51 | 14.79 | 19.19 | 24.75 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 54 | 11 | 1.90 | 8.95 | 26.05 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 55 | 0 | 2.17 | 3.99 | 11.10 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 193 | 20 | 2.87 | 10.34 | 22.72 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 68 | 34 | 3.82 | 17.46 | 34.08 |
| `n6_vs_a100` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 101 | 0 | 1.39 | 2.69 | 9.74 |
| `n6_vs_a100` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 275 | 46 | 1.66 | 5.47 | 19.13 |
| `n6_vs_a100` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 316 | 0 | 1.15 | 1.20 | 2.62 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 20 | 6 | 11.76 | 16.75 | 18.48 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 658 | 0 | 1.15 | 5.56 | 9.22 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 178 | 1 | 2.40 | 12.53 | 17.01 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 823 | 81 | 1.63 | 4.43 | 18.91 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 459 | 62 | 1.17 | 1.83 | 17.67 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `compute` | 20 | 6 | 11.76 | 16.75 | 18.48 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 658 | 0 | 1.12 | 5.17 | 9.34 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 178 | 29 | 2.15 | 13.87 | 23.45 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 823 | 93 | 1.75 | 4.18 | 24.39 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 459 | 166 | 1.98 | 2.38 | 37.99 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 140 | 0 | 1.09 | 1.68 | 9.10 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 428 | 45 | 1.21 | 2.58 | 19.10 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 36 | 0 | 1.10 | 1.14 | 1.57 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 133 | 0 | 1.12 | 1.17 | 1.23 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 310 | 0 | 1.06 | 4.22 | 10.45 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 315 | 10 | 2.25 | 10.28 | 17.68 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 773 | 77 | 1.47 | 4.51 | 18.81 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `thermal` | 352 | 0 | 1.66 | 4.28 | 6.31 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 503 | 28 | 1.03 | 1.37 | 17.37 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 310 | 0 | 1.05 | 4.22 | 10.87 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 315 | 20 | 2.04 | 10.92 | 20.64 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 773 | 85 | 1.71 | 4.84 | 27.45 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `thermal` | 352 | 0 | 1.71 | 4.36 | 6.70 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 503 | 166 | 1.96 | 2.38 | 37.99 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 133 | 0 | 1.43 | 2.58 | 4.32 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 291 | 48 | 1.26 | 3.60 | 19.13 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 170 | 0 | 1.15 | 1.17 | 1.34 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 6 | 0 | 12.00 | 13.29 | 13.49 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 657 | 0 | 1.04 | 2.85 | 9.17 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 170 | 0 | 2.25 | 12.08 | 16.76 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 810 | 80 | 1.42 | 3.96 | 18.87 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 458 | 34 | 1.06 | 1.40 | 17.37 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `compute` | 6 | 0 | 12.00 | 13.29 | 13.49 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 657 | 0 | 1.06 | 2.73 | 9.20 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 170 | 16 | 2.05 | 12.93 | 21.17 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 810 | 92 | 1.66 | 4.16 | 24.39 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 458 | 174 | 1.98 | 2.38 | 37.99 |

## Per model, per context, per batch and per design class

Each row is that class's **fastest** feasible design at that batch, read against the iso-area GPU comparator the published study already chose for it. The `densest` pick of every class is in `analytical.json` beside it.

**The ROM-versus-GPU ratio under speculation is `T_cycle(GPU) / T_cycle(ROM)` and carries no `tau` at all.** The acceptance length is a property of the model and its drafter, not of the machine, so it is the same on both sides and cancels out of the ratio. Every movement in the last column is therefore a machine effect and nothing else.

### `n5_vs_b200-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 4,107.2 | 1,183.6-2,196.9 | 14.71 | **no** | `b200_sxm-x93-nvl72-hybrid` | 1,056.7 | 2,120.3-3,935.5 | 2.11 | yes | 3.887x | 0.558x | 0.144x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,326.1 | 2,367.2-4,393.9 | 9.54 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,053.8 | 2,060.7-3,824.9 | 2.17 | yes | 5.054x | 1.149x | 0.227x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 4,107.2 | 1,183.6-2,196.9 | 14.71 | **no** | `b200_sxm-x93-nvl72-hybrid` | 1,056.7 | 2,120.3-3,935.5 | 2.11 | yes | 3.887x | 0.558x | 0.144x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,326.1 | 2,367.2-4,393.9 | 9.54 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,053.8 | 2,060.7-3,824.9 | 2.17 | yes | 5.054x | 1.149x | 0.227x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 4,107.2 | 1,183.6-2,196.9 | 14.71 | **no** | `b200_sxm-x93-nvl72-hybrid` | 1,032.2 | 1,890.4-3,508.8 | 2.32 | yes | 3.979x | 0.626x | 0.157x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,326.1 | 2,367.2-4,393.9 | 9.54 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,028.4 | 1,839.6-3,414.5 | 2.37 | yes | 5.179x | 1.287x | 0.248x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 4,107.2 | 1,183.6-2,196.9 | 14.71 | **no** | `b200_sxm-x93-nvl72-hybrid` | 988.2 | 1,521.0-2,823.2 | 2.75 | yes | 4.156x | 0.778x | 0.187x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,326.1 | 2,367.2-4,393.9 | 9.54 | **no** | `b200_sxm-x87-nvl72-hybrid` | 982.2 | 1,469.9-2,728.4 | 2.83 | yes | 5.423x | 1.610x | 0.297x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 4,107.2 | 1,183.6-2,196.9 | 14.71 | **no** | `b200_sxm-x93-nvl72-hybrid` | 925.7 | 670.7-1,245.0 | 5.85 | yes | 4.437x | 1.765x | 0.398x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,326.1 | 2,367.2-4,393.9 | 9.54 | **no** | `b200_sxm-x87-nvl72-hybrid` | 922.5 | 670.1-1,243.7 | 5.84 | yes | 5.774x | 3.533x | 0.612x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 4,107.2 | 1,183.6-2,196.9 | 14.71 | **no** | `b200_sxm-x93-nvl72-hybrid` | 837.4 | 557.5-1,034.9 | 6.37 | yes | 4.905x | 2.123x | 0.433x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,186.8 | 2,054.1-3,812.6 | 10.71 | **no** | `b200_sxm-x231-nvl72-hybrid` | 932.5 | 1,290.9-2,396.1 | 3.06 | yes | 5.562x | 1.591x | 0.286x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x185` | 4,035.9 | 648.4-1,203.6 | 26.39 | **no** | `b200_sxm-x94-nvl72-hybrid` | 709.0 | 468.6-869.8 | 6.42 | yes | 5.692x | 1.384x | 0.243x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,183.6 | 2,044.6-3,795.0 | 10.75 | **no** | `b200_sxm-x347-nvl72-hybrid` | 886.5 | 668.1-1,240.2 | 5.63 | yes | 5.847x | 3.060x | 0.523x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 3,044.5 | 444.7-825.3 | 29.03 | **no** | `b200_sxm-x179-nvl72-hybrid` | 526.9 | 410.9-762.7 | 5.44 | yes | 5.778x | 1.082x | 0.187x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,173.4 | 927.6-1,721.8 | 19.08 | **no** | `b200_sxm-x347-nvl72-hybrid` | 664.4 | 462.6-858.6 | 6.09 | yes | 6.281x | 2.005x | 0.319x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 1,567.7 | 285.6-530.1 | 23.27 | **no** | `b200_sxm-x179-nvl72-hybrid` | 265.4 | 201.2-373.5 | 5.59 | yes | 5.907x | 1.419x | 0.240x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,147.3 | 242.8-450.7 | 37.50 | **no** | `b200_sxm-x347-nvl72-hybrid` | 355.2 | 321.3-596.3 | 4.69 | yes | 6.045x | 0.756x | 0.125x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 551.2 | 87.3-162.0 | 26.77 | **no** | `b200_sxm-x179-nvl72-hybrid` | 142.2 | 57.6-106.9 | 10.47 | **no** | 3.875x | 1.516x | 0.391x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 685.6 | 200.8-372.6 | 14.48 | **no** | `b200_sxm-x347-nvl72-hybrid` | 172.6 | 82.2-152.5 | 8.91 | **no** | 3.971x | 2.444x | 0.615x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.125x to 0.615x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 0 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,830.0 | 880.9-1,635.1 | 18.43 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 199.5-370.4 | 9.24 | **no** | 8.809x | 4.415x | 0.501x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,041.0 | 1,718.6-3,190.0 | 12.44 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 204.6-379.8 | 9.17 | **no** | 11.395x | 8.400x | 0.737x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,830.0 | 880.9-1,635.1 | 18.43 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 199.5-370.4 | 9.24 | **no** | 8.809x | 4.415x | 0.501x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,041.0 | 1,718.6-3,190.0 | 12.44 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 204.6-379.8 | 9.17 | **no** | 11.395x | 8.400x | 0.737x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,830.0 | 880.9-1,635.1 | 18.43 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 199.5-370.4 | 9.24 | **no** | 8.809x | 4.415x | 0.501x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,041.0 | 1,718.6-3,190.0 | 12.44 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 204.6-379.8 | 9.17 | **no** | 11.395x | 8.400x | 0.737x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,830.0 | 880.9-1,635.1 | 18.43 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 199.5-370.4 | 9.24 | **no** | 8.809x | 4.415x | 0.501x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,041.0 | 1,718.6-3,190.0 | 12.44 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 204.6-379.8 | 9.17 | **no** | 11.395x | 8.400x | 0.737x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,830.0 | 880.9-1,635.1 | 18.43 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 199.5-370.4 | 9.24 | **no** | 8.809x | 4.415x | 0.501x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,041.0 | 1,718.6-3,190.0 | 12.44 | **no** | `a100_sxm_80gb-x224-hybrid` | 442.4 | 204.6-379.8 | 9.17 | **no** | 11.395x | 8.400x | 0.737x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,830.0 | 880.9-1,635.1 | 18.43 | **no** | `a100_sxm_80gb-x258-hybrid` | 434.8 | 199.5-370.4 | 9.24 | **no** | 8.809x | 4.415x | 0.501x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4,915.6 | 1,541.4-2,861.0 | 13.52 | **no** | `a100_sxm_80gb-x448-hybrid` | 433.5 | 203.8-378.2 | 9.02 | **no** | 11.341x | 7.565x | 0.667x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,830.0 | 880.9-1,635.1 | 18.43 | **no** | `a100_sxm_80gb-x258-hybrid` | 375.9 | 178.4-331.2 | 8.93 | **no** | 10.188x | 4.937x | 0.485x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,911.3 | 1,533.8-2,846.9 | 13.58 | **no** | `a100_sxm_80gb-x672-hybrid` | 433.5 | 205.2-380.9 | 8.96 | **no** | 11.331x | 7.475x | 0.660x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 2,891.3 | 424.5-787.9 | 28.88 | **no** | `a100_sxm_80gb-x335-hybrid` | 234.9 | 126.7-235.2 | 7.86 | yes | 12.307x | 3.350x | 0.272x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,669.5 | 679.0-1,260.3 | 22.91 | **no** | `a100_sxm_80gb-x672-hybrid` | 322.5 | 162.4-301.4 | 8.42 | **no** | 11.378x | 4.182x | 0.368x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,181.8 | 156.5-290.4 | 32.03 | **no** | `a100_sxm_80gb-x337-hybrid` | 98.0 | 67.0-124.4 | 6.20 | yes | 12.058x | 2.335x | 0.194x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,679.0 | 367.9-682.8 | 19.35 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.6 | 92.7-172.0 | 7.12 | yes | 10.791x | 3.970x | 0.368x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 328.7 | 50.4-93.5 | 27.66 | **no** | `a100_sxm_80gb-x337-hybrid` | 37.3 | 16.7-30.9 | 9.50 | **no** | 8.804x | 3.023x | 0.343x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 606.8 | 134.5-249.7 | 19.13 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.3 | 51.2-95.0 | 4.91 | yes | 10.232x | 2.627x | 0.257x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.194x to 0.737x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 0 of 20 ROM rows and 4 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 3,851.3 | 997.0-1,850.6 | 16.38 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,064.7 | 2,310.7-4,288.9 | 1.95 | yes | 3.617x | 0.431x | 0.119x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,803.1 | 3,111.3-5,775.0 | 6.55 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,071.3 | 2,476.9-4,597.4 | 1.83 | yes | 4.484x | 1.256x | 0.280x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 3,851.3 | 997.0-1,850.6 | 16.38 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,064.7 | 2,310.7-4,288.9 | 1.95 | yes | 3.617x | 0.431x | 0.119x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,803.1 | 3,111.3-5,775.0 | 6.55 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,071.3 | 2,476.9-4,597.4 | 1.83 | yes | 4.484x | 1.256x | 0.280x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 3,851.3 | 997.0-1,850.6 | 16.38 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,042.0 | 2,051.0-3,807.0 | 2.15 | yes | 3.696x | 0.486x | 0.132x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,803.1 | 3,111.3-5,775.0 | 6.55 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,050.4 | 2,184.5-4,054.7 | 2.04 | yes | 4.573x | 1.424x | 0.311x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 3,851.3 | 997.0-1,850.6 | 16.38 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,000.0 | 1,685.6-3,128.7 | 2.52 | yes | 3.851x | 0.591x | 0.154x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,803.1 | 3,111.3-5,775.0 | 6.55 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,012.0 | 1,759.2-3,265.4 | 2.44 | yes | 4.746x | 1.769x | 0.373x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 3,851.3 | 997.0-1,850.6 | 16.38 | **no** | `b200_sxm-x116-nvl72-hybrid` | 941.9 | 1,334.6-2,477.2 | 2.99 | yes | 4.089x | 0.747x | 0.183x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,803.1 | 3,111.3-5,775.0 | 6.55 | yes | `b200_sxm-x144-nvl72-hybrid` | 958.0 | 1,390.2-2,580.4 | 2.92 | yes | 5.014x | 2.238x | 0.446x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 3,851.3 | 997.0-1,850.6 | 16.38 | **no** | `b200_sxm-x116-nvl72-hybrid` | 860.9 | 590.9-1,096.7 | 6.18 | yes | 4.474x | 1.687x | 0.377x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,641.4 | 2,456.3-4,559.2 | 8.01 | **no** | `b200_sxm-x347-nvl72-hybrid` | 957.9 | 1,416.1-2,628.4 | 2.87 | yes | 4.846x | 1.735x | 0.358x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 3,773.0 | 1,047.7-1,944.7 | 15.27 | **no** | `b200_sxm-x134-nvl72-hybrid` | 769.2 | 513.6-953.4 | 6.35 | yes | 4.905x | 2.040x | 0.416x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,491.2 | 1,456.2-2,702.9 | 13.08 | **no** | `b200_sxm-x347-nvl72-hybrid` | 882.2 | 667.0-1,238.0 | 5.61 | yes | 5.091x | 2.183x | 0.429x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 2,731.9 | 433.4-804.5 | 26.73 | **no** | `b200_sxm-x173-nvl72-hybrid` | 508.1 | 410.5-761.9 | 5.25 | yes | 5.377x | 1.056x | 0.196x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,068.8 | 649.7-1,206.0 | 20.03 | **no** | `b200_sxm-x347-nvl72-hybrid` | 654.9 | 460.7-855.2 | 6.03 | yes | 4.686x | 1.410x | 0.301x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 1,255.7 | 170.3-316.0 | 31.27 | **no** | `b200_sxm-x179-nvl72-hybrid` | 254.0 | 199.6-370.5 | 5.40 | yes | 4.944x | 0.853x | 0.173x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,259.1 | 234.7-435.6 | 22.75 | **no** | `b200_sxm-x347-nvl72-hybrid` | 344.5 | 319.0-592.2 | 4.58 | yes | 3.654x | 0.736x | 0.201x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 360.6 | 58.5-108.7 | 26.12 | **no** | `b200_sxm-x179-nvl72-hybrid` | 129.7 | 55.8-103.5 | 9.86 | **no** | 2.780x | 1.050x | 0.378x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 359.4 | 93.5-173.5 | 16.30 | **no** | `b200_sxm-x347-nvl72-hybrid` | 162.8 | 80.3-149.0 | 8.60 | **no** | 2.208x | 1.165x | 0.528x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.119x to 0.528x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 5 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,552.7 | 1,321.1-2,452.1 | 11.40 | **no** | `a100_sxm_80gb-x337-hybrid` | 427.3 | 198.7-368.9 | 9.12 | **no** | 8.313x | 6.648x | 0.800x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 4,448.8 | 1,656.8-3,075.2 | 11.39 | **no** | `a100_sxm_80gb-x168-hybrid` | 444.9 | 205.5-381.4 | 9.18 | **no** | 10.000x | 8.062x | 0.806x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,552.7 | 1,321.1-2,452.1 | 11.40 | **no** | `a100_sxm_80gb-x337-hybrid` | 427.3 | 198.7-368.9 | 9.12 | **no** | 8.313x | 6.648x | 0.800x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,212.6 | 2,843.8-5,278.4 | 6.28 | yes | `a100_sxm_80gb-x672-hybrid` | 430.7 | 205.0-380.6 | 8.91 | **no** | 9.780x | 13.870x | 1.418x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,552.7 | 1,321.1-2,452.1 | 11.40 | **no** | `a100_sxm_80gb-x337-hybrid` | 427.3 | 198.7-368.9 | 9.12 | **no** | 8.313x | 6.648x | 0.800x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,212.6 | 2,843.8-5,278.4 | 6.28 | yes | `a100_sxm_80gb-x672-hybrid` | 430.7 | 205.0-380.6 | 8.91 | **no** | 9.780x | 13.870x | 1.418x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,552.7 | 1,321.1-2,452.1 | 11.40 | **no** | `a100_sxm_80gb-x337-hybrid` | 427.3 | 198.7-368.9 | 9.12 | **no** | 8.313x | 6.648x | 0.800x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,212.6 | 2,843.8-5,278.4 | 6.28 | yes | `a100_sxm_80gb-x672-hybrid` | 430.7 | 205.0-380.6 | 8.91 | **no** | 9.780x | 13.870x | 1.418x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,552.7 | 1,321.1-2,452.1 | 11.40 | **no** | `a100_sxm_80gb-x337-hybrid` | 427.3 | 198.7-368.9 | 9.12 | **no** | 8.313x | 6.648x | 0.800x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,212.6 | 2,843.8-5,278.4 | 6.28 | yes | `a100_sxm_80gb-x672-hybrid` | 430.7 | 205.0-380.6 | 8.91 | **no** | 9.780x | 13.870x | 1.418x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,552.7 | 1,321.1-2,452.1 | 11.40 | **no** | `a100_sxm_80gb-x337-hybrid` | 427.3 | 198.7-368.9 | 9.12 | **no** | 8.313x | 6.648x | 0.800x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,116.3 | 1,792.4-3,327.0 | 9.74 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 205.0-380.6 | 8.91 | **no** | 9.556x | 8.742x | 0.915x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 3,535.8 | 748.8-1,389.9 | 20.02 | **no** | `a100_sxm_80gb-x335-hybrid` | 394.2 | 187.6-348.2 | 8.91 | **no** | 8.969x | 3.991x | 0.445x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,540.0 | 1,598.0-2,966.1 | 9.39 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 205.0-380.6 | 8.91 | **no** | 8.218x | 7.794x | 0.948x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 2,395.1 | 323.4-600.2 | 31.40 | **no** | `a100_sxm_80gb-x337-hybrid` | 230.7 | 126.1-234.1 | 7.76 | yes | 10.380x | 2.564x | 0.247x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,874.5 | 494.7-918.3 | 16.06 | **no** | `a100_sxm_80gb-x672-hybrid` | 318.0 | 162.0-300.8 | 8.32 | **no** | 5.895x | 3.053x | 0.518x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 827.5 | 109.1-202.4 | 32.17 | **no** | `a100_sxm_80gb-x337-hybrid` | 94.7 | 66.6-123.6 | 6.03 | yes | 8.735x | 1.637x | 0.187x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 597.6 | 127.5-236.7 | 19.87 | **no** | `a100_sxm_80gb-x672-hybrid` | 151.4 | 90.8-168.5 | 7.07 | yes | 3.947x | 1.404x | 0.356x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 222.0 | 34.7-64.4 | 27.14 | **no** | `a100_sxm_80gb-x337-hybrid` | 35.5 | 14.6-27.1 | 10.30 | **no** | 6.259x | 2.375x | 0.379x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 156.6 | 77.8-144.4 | 8.54 | **no** | `a100_sxm_80gb-x672-hybrid` | 56.9 | 45.5-84.5 | 5.30 | yes | 2.752x | 1.709x | 0.621x |

**Does the ratio compress?** Of 20 class rows in this study, 16 move the ROM-versus-GPU ratio DOWN under speculation and 4 move it UP. The movement spans 0.187x to 1.418x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 4 of 20 ROM rows and 4 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,200.2 | 694.3-1,288.8 | 25.65 | **no** | `b200_sxm-x90-nvl72-hybrid` | 1,055.5 | 2,091.3-3,881.7 | 2.14 | yes | 3.979x | 0.332x | 0.083x |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,465.8 | 2,672.0-4,959.7 | 8.67 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,054.0 | 2,060.9-3,825.3 | 2.17 | yes | 5.186x | 1.297x | 0.250x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,200.2 | 694.3-1,288.8 | 25.65 | **no** | `b200_sxm-x90-nvl72-hybrid` | 1,055.5 | 2,091.3-3,881.7 | 2.14 | yes | 3.979x | 0.332x | 0.083x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,465.8 | 2,672.0-4,959.7 | 8.67 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,054.0 | 2,060.9-3,825.3 | 2.17 | yes | 5.186x | 1.297x | 0.250x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,200.2 | 694.3-1,288.8 | 25.65 | **no** | `b200_sxm-x90-nvl72-hybrid` | 1,030.7 | 1,865.9-3,463.3 | 2.34 | yes | 4.075x | 0.372x | 0.091x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,465.8 | 2,672.0-4,959.7 | 8.67 | **no** | `b200_sxm-x87-nvl72-hybrid` | 1,028.8 | 1,839.9-3,415.2 | 2.37 | yes | 5.313x | 1.452x | 0.273x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,200.2 | 694.3-1,288.8 | 25.65 | **no** | `b200_sxm-x90-nvl72-hybrid` | 985.9 | 1,496.4-2,777.5 | 2.79 | yes | 4.260x | 0.464x | 0.109x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,465.8 | 2,672.0-4,959.7 | 8.67 | **no** | `b200_sxm-x87-nvl72-hybrid` | 982.9 | 1,470.4-2,729.2 | 2.83 | yes | 5.561x | 1.817x | 0.327x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,200.2 | 694.3-1,288.8 | 25.65 | **no** | `b200_sxm-x90-nvl72-hybrid` | 919.6 | 649.4-1,205.4 | 6.00 | yes | 4.567x | 1.069x | 0.234x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,465.8 | 2,672.0-4,959.7 | 8.67 | **no** | `b200_sxm-x87-nvl72-hybrid` | 923.7 | 670.4-1,244.3 | 5.84 | yes | 5.918x | 3.986x | 0.674x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,200.2 | 694.3-1,288.8 | 25.65 | **no** | `b200_sxm-x90-nvl72-hybrid` | 830.9 | 539.9-1,002.1 | 6.53 | yes | 5.055x | 1.286x | 0.254x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,330.9 | 2,311.5-4,290.4 | 9.78 | **no** | `b200_sxm-x231-nvl72-hybrid` | 933.4 | 1,291.4-2,397.0 | 3.06 | yes | 5.711x | 1.790x | 0.313x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,200.2 | 694.3-1,288.8 | 25.65 | **no** | `b200_sxm-x90-nvl72-hybrid` | 699.3 | 449.1-833.6 | 6.60 | yes | 6.006x | 1.546x | 0.257x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,327.8 | 2,300.4-4,269.8 | 9.82 | **no** | `b200_sxm-x347-nvl72-hybrid` | 887.6 | 668.4-1,240.7 | 5.63 | yes | 6.002x | 3.441x | 0.573x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 3,271.8 | 496.2-921.0 | 27.96 | **no** | `b200_sxm-x179-nvl72-hybrid` | 529.9 | 411.6-764.0 | 5.46 | yes | 6.174x | 1.206x | 0.195x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,450.9 | 1,050.3-1,949.5 | 17.97 | **no** | `b200_sxm-x347-nvl72-hybrid` | 666.9 | 463.0-859.4 | 6.11 | yes | 6.674x | 2.268x | 0.340x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 1,632.6 | 307.0-569.8 | 22.55 | **no** | `b200_sxm-x179-nvl72-hybrid` | 268.5 | 201.6-374.3 | 5.65 | yes | 6.081x | 1.522x | 0.250x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,433.4 | 271.8-504.6 | 37.96 | **no** | `b200_sxm-x347-nvl72-hybrid` | 358.1 | 321.8-597.4 | 4.72 | yes | 6.795x | 0.845x | 0.124x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 610.9 | 95.6-177.4 | 27.11 | **no** | `b200_sxm-x173-nvl72-hybrid` | 142.9 | 53.9-100.1 | 11.23 | **no** | 4.275x | 1.772x | 0.414x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 769.7 | 108.8-202.0 | 29.99 | **no** | `b200_sxm-x347-nvl72-hybrid` | 175.3 | 82.7-153.4 | 8.99 | **no** | 4.389x | 1.316x | 0.300x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.083x to 0.674x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 0 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 3,927.6 | 943.6-1,751.4 | 17.65 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 201.2-373.4 | 9.23 | **no** | 8.965x | 4.691x | 0.523x |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,218.1 | 1,939.9-3,600.6 | 11.41 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 204.6-379.8 | 9.18 | **no** | 11.776x | 9.479x | 0.805x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 3,927.6 | 943.6-1,751.4 | 17.65 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 201.2-373.4 | 9.23 | **no** | 8.965x | 4.691x | 0.523x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,218.1 | 1,939.9-3,600.6 | 11.41 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 204.6-379.8 | 9.18 | **no** | 11.776x | 9.479x | 0.805x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 3,927.6 | 943.6-1,751.4 | 17.65 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 201.2-373.4 | 9.23 | **no** | 8.965x | 4.691x | 0.523x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,218.1 | 1,939.9-3,600.6 | 11.41 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 204.6-379.8 | 9.18 | **no** | 11.776x | 9.479x | 0.805x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 3,927.6 | 943.6-1,751.4 | 17.65 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 201.2-373.4 | 9.23 | **no** | 8.965x | 4.691x | 0.523x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,218.1 | 1,939.9-3,600.6 | 11.41 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 204.6-379.8 | 9.18 | **no** | 11.776x | 9.479x | 0.805x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 3,927.6 | 943.6-1,751.4 | 17.65 | **no** | `a100_sxm_80gb-x244-hybrid` | 438.1 | 201.2-373.4 | 9.23 | **no** | 8.965x | 4.691x | 0.523x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,218.1 | 1,939.9-3,600.6 | 11.41 | **no** | `a100_sxm_80gb-x224-hybrid` | 443.1 | 204.6-379.8 | 9.18 | **no** | 11.776x | 9.479x | 0.805x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 3,927.6 | 943.6-1,751.4 | 17.65 | **no** | `a100_sxm_80gb-x244-hybrid` | 435.8 | 200.3-371.8 | 9.23 | **no** | 9.012x | 4.711x | 0.523x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,099.5 | 1,737.1-3,224.3 | 12.45 | **no** | `a100_sxm_80gb-x448-hybrid` | 434.2 | 203.8-378.3 | 9.03 | **no** | 11.746x | 8.523x | 0.726x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 3,817.9 | 929.9-1,726.1 | 17.41 | **no** | `a100_sxm_80gb-x244-hybrid` | 373.1 | 178.0-330.5 | 8.88 | **no** | 10.233x | 5.223x | 0.510x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,094.9 | 1,728.1-3,207.6 | 12.50 | **no** | `a100_sxm_80gb-x672-hybrid` | 434.2 | 205.2-381.0 | 8.97 | **no** | 11.735x | 8.420x | 0.718x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 2,963.7 | 442.0-820.4 | 28.43 | **no** | `a100_sxm_80gb-x335-hybrid` | 236.2 | 126.8-235.4 | 7.90 | **no** | 12.547x | 3.485x | 0.278x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,968.0 | 768.0-1,425.6 | 21.91 | **no** | `a100_sxm_80gb-x672-hybrid` | 323.7 | 162.5-301.5 | 8.45 | **no** | 12.259x | 4.728x | 0.386x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,328.4 | 176.1-326.9 | 31.98 | **no** | `a100_sxm_80gb-x337-hybrid` | 98.9 | 67.1-124.6 | 6.25 | yes | 13.435x | 2.624x | 0.195x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,899.7 | 196.1-364.0 | 41.08 | **no** | `a100_sxm_80gb-x672-hybrid` | 156.7 | 92.8-172.2 | 7.16 | yes | 12.123x | 2.114x | 0.174x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 375.9 | 57.1-105.9 | 27.92 | **no** | `a100_sxm_80gb-x337-hybrid` | 37.8 | 17.3-32.1 | 9.28 | **no** | 9.931x | 3.302x | 0.332x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 721.4 | 155.0-287.7 | 19.73 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.9 | 52.8-98.0 | 4.81 | yes | 12.033x | 2.936x | 0.244x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.174x to 0.805x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 0 of 20 ROM rows and 3 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 2,050.3-3,805.6 | 8.96 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,065.2 | 3,251.2-6,034.7 | 1.39 | yes | 4.067x | 0.631x | 0.155x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 5,400.3 | 3,887.3-7,215.4 | 5.89 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,060.6 | 3,196.2-5,932.5 | 1.41 | yes | 5.092x | 1.216x | 0.239x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 2,050.3-3,805.6 | 8.96 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,042.5 | 2,801.1-5,199.2 | 1.58 | yes | 4.155x | 0.732x | 0.176x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,360.5 | 3,799.3-7,052.1 | 5.98 | yes | `b200_sxm-x58-nvl72-tensor` | 1,050.0 | 2,846.4-5,283.2 | 1.56 | yes | 5.105x | 1.335x | 0.261x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 2,050.3-3,805.6 | 8.96 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,000.6 | 2,214.6-4,110.6 | 1.92 | yes | 4.330x | 0.926x | 0.214x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,360.5 | 3,799.3-7,052.1 | 5.98 | yes | `b200_sxm-x58-nvl72-tensor` | 1,010.6 | 2,250.4-4,177.0 | 1.90 | yes | 5.304x | 1.688x | 0.318x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 2,050.3-3,805.6 | 8.96 | **no** | `b200_sxm-x49-nvl72-tensor` | 927.9 | 1,601.8-2,973.1 | 2.46 | yes | 4.669x | 1.280x | 0.274x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,360.5 | 3,799.3-7,052.1 | 5.98 | yes | `b200_sxm-x58-nvl72-tensor` | 941.7 | 1,617.8-3,002.9 | 2.47 | yes | 5.692x | 2.348x | 0.413x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 2,050.3-3,805.6 | 8.96 | **no** | `b200_sxm-x49-hybrid` | 830.0 | 1,266.3-2,350.4 | 2.78 | yes | 5.219x | 1.619x | 0.310x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5,350.7 | 3,843.5-7,134.1 | 5.90 | yes | `b200_sxm-x87-nvl72-hybrid` | 922.5 | 1,965.2-3,647.7 | 1.99 | yes | 5.800x | 1.956x | 0.337x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,259.9 | 1,162.0-2,156.9 | 15.54 | **no** | `b200_sxm-x49-hybrid` | 701.7 | 843.3-1,565.2 | 3.53 | yes | 6.071x | 1.378x | 0.227x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,318.2 | 3,893.8-7,227.4 | 5.79 | yes | `b200_sxm-x231-nvl72-hybrid` | 932.5 | 1,926.5-3,575.8 | 2.05 | yes | 5.703x | 2.021x | 0.354x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,186.0 | 2,005.5-3,722.4 | 8.85 | **no** | `b200_sxm-x173-nvl72-hybrid` | 815.7 | 1,217.9-2,260.5 | 2.84 | yes | 5.132x | 1.647x | 0.321x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,316.1 | 3,880.8-7,203.4 | 5.81 | yes | `b200_sxm-x347-nvl72-hybrid` | 886.5 | 1,959.5-3,637.2 | 1.92 | yes | 5.997x | 1.980x | 0.330x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,426.8 | 936.2-1,737.8 | 15.52 | **no** | `b200_sxm-x173-nvl72-hybrid` | 519.7 | 704.0-1,306.7 | 3.13 | yes | 6.594x | 1.330x | 0.202x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,530.1 | 1,961.4-3,640.5 | 9.79 | **no** | `b200_sxm-x347-nvl72-hybrid` | 664.4 | 853.4-1,583.9 | 3.30 | yes | 6.818x | 2.298x | 0.337x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,455.9 | 317.7-589.6 | 19.43 | **no** | `b200_sxm-x173-nvl72-hybrid` | 262.6 | 210.0-389.8 | 5.30 | yes | 5.544x | 1.513x | 0.273x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,637.2 | 548.5-1,018.1 | 20.39 | **no** | `b200_sxm-x347-nvl72-hybrid` | 355.2 | 459.4-852.7 | 3.28 | yes | 7.424x | 1.194x | 0.161x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 416.4 | 99.6-184.8 | 17.73 | **no** | `b200_sxm-x173-nvl72-hybrid` | 139.3 | 56.9-105.7 | 10.37 | **no** | 2.989x | 1.749x | 0.585x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 872.6 | 203.4-377.6 | 18.19 | **no** | `b200_sxm-x347-nvl72-hybrid` | 172.6 | 86.2-159.9 | 8.50 | **no** | 5.054x | 2.361x | 0.467x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.155x to 0.585x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 1,539.8-2,858.0 | 11.08 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 809.6-1,502.8 | 2.36 | yes | 8.927x | 1.902x | 0.213x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 5,167.1 | 2,946.2-5,468.5 | 7.44 | yes | `a100_sxm_80gb-x672-hybrid` | 433.5 | 797.4-1,480.1 | 2.30 | yes | 11.921x | 3.695x | 0.310x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 1,539.8-2,858.0 | 11.08 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 809.6-1,502.8 | 2.36 | yes | 8.927x | 1.902x | 0.213x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.6 | 3,027.0-5,618.4 | 7.12 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.355x | 3.762x | 0.331x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 1,539.8-2,858.0 | 11.08 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 809.6-1,502.8 | 2.36 | yes | 8.927x | 1.902x | 0.213x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.6 | 3,027.0-5,618.4 | 7.12 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.355x | 3.762x | 0.331x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 1,539.8-2,858.0 | 11.08 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 809.6-1,502.8 | 2.36 | yes | 8.927x | 1.902x | 0.213x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.6 | 3,027.0-5,618.4 | 7.12 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.355x | 3.762x | 0.331x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 1,539.8-2,858.0 | 11.08 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 809.6-1,502.8 | 2.36 | yes | 8.927x | 1.902x | 0.213x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.6 | 3,027.0-5,618.4 | 7.12 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.355x | 3.762x | 0.331x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 1,539.8-2,858.0 | 11.08 | **no** | `a100_sxm_80gb-x136-hybrid` | 396.2 | 594.6-1,103.7 | 2.82 | yes | 10.159x | 2.589x | 0.255x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,062.2 | 3,076.8-5,711.0 | 6.98 | yes | `a100_sxm_80gb-x448-hybrid` | 433.5 | 776.2-1,440.7 | 2.37 | yes | 11.679x | 3.964x | 0.339x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 3,937.8 | 1,564.4-2,903.7 | 10.67 | **no** | `a100_sxm_80gb-x272-hybrid` | 382.0 | 539.9-1,002.1 | 3.00 | yes | 10.307x | 2.898x | 0.281x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,059.0 | 3,065.0-5,689.0 | 7.00 | yes | `a100_sxm_80gb-x672-hybrid` | 433.5 | 797.4-1,480.1 | 2.30 | yes | 11.671x | 3.844x | 0.329x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,960.5 | 701.8-1,302.6 | 17.89 | **no** | `a100_sxm_80gb-x335-hybrid` | 234.9 | 234.7-435.6 | 4.24 | yes | 12.601x | 2.991x | 0.237x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,982.4 | 1,468.8-2,726.3 | 11.50 | **no** | `a100_sxm_80gb-x672-hybrid` | 322.5 | 393.8-730.9 | 3.47 | yes | 12.349x | 3.730x | 0.302x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,129.9 | 234.6-435.4 | 20.43 | **no** | `a100_sxm_80gb-x335-hybrid` | 97.7 | 130.6-242.3 | 3.17 | yes | 11.570x | 1.797x | 0.155x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,977.6 | 398.9-740.3 | 21.02 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.6 | 139.4-258.8 | 4.73 | yes | 12.710x | 2.860x | 0.225x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 401.3 | 104.0-193.1 | 16.35 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.2 | 19.2-35.6 | 8.23 | **no** | 10.774x | 5.422x | 0.503x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 602.7 | 147.9-274.6 | 17.27 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.3 | 81.3-151.0 | 3.09 | yes | 10.162x | 1.819x | 0.179x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.155x to 0.503x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4,034.1 | 1,694.8-3,145.7 | 10.09 | **no** | `b200_sxm-x57-nvl72-tensor` | 1,070.0 | 3,295.1-6,116.2 | 1.38 | yes | 3.770x | 0.514x | 0.136x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 5,108.5 | 3,304.0-6,132.7 | 6.56 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,060.1 | 3,195.0-5,930.3 | 1.41 | yes | 4.819x | 1.034x | 0.215x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4,034.1 | 1,694.8-3,145.7 | 10.09 | **no** | `b200_sxm-x57-nvl72-tensor` | 1,048.2 | 2,839.8-5,271.0 | 1.57 | yes | 3.849x | 0.597x | 0.155x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,815.0 | 3,260.1-6,051.2 | 6.26 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,071.3 | 3,319.6-6,161.7 | 1.37 | yes | 4.495x | 0.982x | 0.219x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4,034.1 | 1,694.8-3,145.7 | 10.09 | **no** | `b200_sxm-x57-nvl72-tensor` | 1,007.6 | 2,244.1-4,165.4 | 1.90 | yes | 4.004x | 0.755x | 0.189x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,815.0 | 3,260.1-6,051.2 | 6.26 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,050.4 | 2,814.7-5,224.5 | 1.58 | yes | 4.584x | 1.158x | 0.253x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4,034.1 | 1,694.8-3,145.7 | 10.09 | **no** | `b200_sxm-x57-nvl72-tensor` | 936.7 | 1,613.5-2,994.9 | 2.46 | yes | 4.306x | 1.050x | 0.244x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,815.0 | 3,260.1-6,051.2 | 6.26 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,012.0 | 2,411.5-4,476.0 | 1.78 | yes | 4.758x | 1.352x | 0.284x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4,034.1 | 1,694.8-3,145.7 | 10.09 | **no** | `b200_sxm-x57-hybrid` | 845.3 | 1,406.0-2,609.8 | 2.55 | yes | 4.772x | 1.205x | 0.253x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 4,815.0 | 3,260.1-6,051.2 | 6.26 | yes | `b200_sxm-x144-nvl72-hybrid` | 958.0 | 2,159.5-4,008.3 | 1.88 | yes | 5.026x | 1.510x | 0.300x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x113` | 3,831.6 | 1,585.0-2,941.9 | 10.25 | **no** | `b200_sxm-x58-hybrid` | 727.4 | 930.1-1,726.4 | 3.32 | yes | 5.267x | 1.704x | 0.324x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,641.4 | 4,459.7-8,277.8 | 4.41 | yes | `b200_sxm-x347-nvl72-hybrid` | 957.9 | 2,117.5-3,930.4 | 1.92 | yes | 4.846x | 2.106x | 0.435x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,809.2 | 1,684.6-3,126.8 | 9.59 | **no** | `b200_sxm-x173-nvl72-hybrid` | 808.5 | 1,212.6-2,250.7 | 2.83 | yes | 4.712x | 1.389x | 0.295x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,491.2 | 3,115.8-5,783.3 | 6.11 | yes | `b200_sxm-x347-nvl72-hybrid` | 882.2 | 1,952.7-3,624.4 | 1.92 | yes | 5.091x | 1.596x | 0.313x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,746.3 | 735.8-1,365.7 | 15.83 | **no** | `b200_sxm-x173-nvl72-hybrid` | 508.1 | 697.0-1,293.6 | 3.09 | yes | 5.405x | 1.056x | 0.195x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,068.7 | 1,470.5-2,729.5 | 8.85 | **no** | `b200_sxm-x347-nvl72-hybrid` | 654.9 | 848.2-1,574.3 | 3.27 | yes | 4.686x | 1.734x | 0.370x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,021.5 | 231.4-429.5 | 18.72 | **no** | `b200_sxm-x173-nvl72-hybrid` | 251.0 | 208.2-386.4 | 5.11 | yes | 4.069x | 1.112x | 0.273x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,249.0 | 416.6-773.4 | 12.71 | **no** | `b200_sxm-x347-nvl72-hybrid` | 344.5 | 454.8-844.2 | 3.21 | yes | 3.625x | 0.916x | 0.253x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 348.1 | 97.9-181.8 | 15.07 | **no** | `b200_sxm-x173-nvl72-hybrid` | 126.9 | 55.8-103.6 | 9.64 | **no** | 2.743x | 1.755x | 0.640x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 359.6 | 151.5-281.3 | 10.06 | **no** | `b200_sxm-x347-nvl72-hybrid` | 162.8 | 84.9-157.6 | 8.13 | **no** | 2.209x | 1.784x | 0.808x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.136x to 0.808x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 3,724.2 | 2,143.4-3,978.5 | 7.37 | yes | `a100_sxm_80gb-x155-hybrid` | 440.0 | 787.2-1,461.2 | 2.37 | yes | 8.464x | 2.723x | 0.322x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | 4,953.7 | 4,192.3-7,781.4 | 5.01 | yes | `a100_sxm_80gb-x616-hybrid` | 430.7 | 791.1-1,468.4 | 2.31 | yes | 11.500x | 5.299x | 0.461x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 3,724.2 | 2,143.4-3,978.5 | 7.37 | yes | `a100_sxm_80gb-x155-hybrid` | 440.0 | 787.2-1,461.2 | 2.37 | yes | 8.464x | 2.723x | 0.322x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 4,243.6 | 3,556.6-6,601.5 | 5.06 | yes | `a100_sxm_80gb-x448-hybrid` | 430.7 | 773.8-1,436.3 | 2.36 | yes | 9.852x | 4.596x | 0.467x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 3,724.2 | 2,143.4-3,978.5 | 7.37 | yes | `a100_sxm_80gb-x155-hybrid` | 440.0 | 787.2-1,461.2 | 2.37 | yes | 8.464x | 2.723x | 0.322x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 4,243.6 | 3,556.6-6,601.5 | 5.06 | yes | `a100_sxm_80gb-x448-hybrid` | 430.7 | 773.8-1,436.3 | 2.36 | yes | 9.852x | 4.596x | 0.467x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 3,724.2 | 2,143.4-3,978.5 | 7.37 | yes | `a100_sxm_80gb-x155-hybrid` | 440.0 | 787.2-1,461.2 | 2.37 | yes | 8.464x | 2.723x | 0.322x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 4,243.6 | 3,556.6-6,601.5 | 5.06 | yes | `a100_sxm_80gb-x448-hybrid` | 430.7 | 773.8-1,436.3 | 2.36 | yes | 9.852x | 4.596x | 0.467x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 3,724.2 | 2,143.4-3,978.5 | 7.37 | yes | `a100_sxm_80gb-x155-hybrid` | 440.0 | 787.2-1,461.2 | 2.37 | yes | 8.464x | 2.723x | 0.322x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,223.1 | 2,917.2-5,414.7 | 6.14 | yes | `a100_sxm_80gb-x672-hybrid` | 430.7 | 794.9-1,475.5 | 2.30 | yes | 9.804x | 3.670x | 0.374x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156` | 3,695.0 | 1,294.3-2,402.4 | 12.10 | **no** | `a100_sxm_80gb-x154-hybrid` | 398.9 | 619.4-1,149.8 | 2.73 | yes | 9.262x | 2.089x | 0.226x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,053.8 | 1,848.4-3,430.8 | 9.30 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 794.9-1,475.5 | 2.30 | yes | 9.411x | 2.325x | 0.247x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 3,508.8 | 1,309.0-2,429.7 | 11.37 | **no** | `a100_sxm_80gb-x272-hybrid` | 378.1 | 537.6-997.9 | 2.98 | yes | 9.280x | 2.435x | 0.262x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,595.6 | 1,670.0-3,099.7 | 9.13 | **no** | `a100_sxm_80gb-x672-hybrid` | 430.7 | 794.9-1,475.5 | 2.30 | yes | 8.347x | 2.101x | 0.252x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,310.6 | 556.0-1,032.1 | 17.62 | **no** | `a100_sxm_80gb-x335-hybrid` | 230.1 | 233.4-433.2 | 4.18 | yes | 10.041x | 2.382x | 0.237x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,900.4 | 524.2-973.0 | 15.37 | **no** | `a100_sxm_80gb-x672-hybrid` | 318.0 | 391.9-727.4 | 3.44 | yes | 5.977x | 1.338x | 0.224x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 983.0 | 217.9-404.4 | 19.13 | **no** | `a100_sxm_80gb-x335-hybrid` | 94.4 | 129.0-239.5 | 3.10 | yes | 10.415x | 1.689x | 0.162x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 601.7 | 135.5-251.6 | 18.82 | **no** | `a100_sxm_80gb-x672-hybrid` | 151.4 | 135.3-251.0 | 4.75 | yes | 3.974x | 1.002x | 0.252x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340` | 325.4 | 69.0-128.2 | 19.98 | **no** | `a100_sxm_80gb-x335-hybrid` | 35.4 | 17.5-32.5 | 8.56 | **no** | 9.200x | 3.942x | 0.428x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 157.6 | 91.2-169.3 | 7.32 | yes | `a100_sxm_80gb-x672-hybrid` | 56.9 | 67.9-126.0 | 3.55 | yes | 2.768x | 1.344x | 0.485x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.162x to 0.485x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,404.8 | 1,232.0-2,286.8 | 15.16 | **no** | `b200_sxm-x47-nvl72-tensor` | 1,063.7 | 3,237.5-6,009.2 | 1.39 | yes | 4.141x | 0.381x | 0.092x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,513.7 | 4,182.3-7,762.9 | 5.59 | yes | `b200_sxm-x58-nvl72-tensor` | 1,071.4 | 3,301.9-6,128.8 | 1.38 | yes | 5.147x | 1.267x | 0.246x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,404.8 | 1,232.0-2,286.8 | 15.16 | **no** | `b200_sxm-x47-nvl72-tensor` | 1,040.8 | 2,788.6-5,176.0 | 1.58 | yes | 4.232x | 0.442x | 0.104x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,513.7 | 4,182.3-7,762.9 | 5.59 | yes | `b200_sxm-x58-nvl72-tensor` | 1,050.3 | 2,847.0-5,284.5 | 1.56 | yes | 5.250x | 1.469x | 0.280x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,404.8 | 1,232.0-2,286.8 | 15.16 | **no** | `b200_sxm-x47-nvl72-tensor` | 998.4 | 2,204.7-4,092.3 | 1.92 | yes | 4.412x | 0.559x | 0.127x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,513.7 | 4,182.3-7,762.9 | 5.59 | yes | `b200_sxm-x58-nvl72-tensor` | 1,011.2 | 2,251.2-4,178.5 | 1.90 | yes | 5.453x | 1.858x | 0.341x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,404.8 | 1,232.0-2,286.8 | 15.16 | **no** | `b200_sxm-x47-hybrid` | 929.0 | 1,898.7-3,524.2 | 2.07 | yes | 4.742x | 0.649x | 0.137x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,513.7 | 4,182.3-7,762.9 | 5.59 | yes | `b200_sxm-x58-nvl72-tensor` | 942.6 | 1,618.7-3,004.4 | 2.47 | yes | 5.849x | 2.584x | 0.442x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,404.8 | 1,232.0-2,286.8 | 15.16 | **no** | `b200_sxm-x47-hybrid` | 838.8 | 1,282.7-2,380.8 | 2.77 | yes | 5.251x | 0.961x | 0.183x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5,501.7 | 4,232.6-7,856.3 | 5.51 | yes | `b200_sxm-x87-nvl72-hybrid` | 923.7 | 1,967.0-3,650.9 | 1.99 | yes | 5.956x | 2.152x | 0.361x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,404.8 | 1,232.0-2,286.8 | 15.16 | **no** | `b200_sxm-x47-hybrid` | 705.2 | 880.3-1,633.9 | 3.40 | yes | 6.246x | 1.400x | 0.224x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,464.9 | 4,288.6-7,960.2 | 5.40 | yes | `b200_sxm-x231-nvl72-hybrid` | 933.4 | 1,927.6-3,577.9 | 2.05 | yes | 5.855x | 2.225x | 0.380x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 4,397.6 | 1,232.2-2,287.2 | 15.13 | **no** | `b200_sxm-x83-nvl72-hybrid` | 682.6 | 817.7-1,517.8 | 3.54 | yes | 6.443x | 1.507x | 0.234x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,463.3 | 4,273.9-7,933.0 | 5.42 | yes | `b200_sxm-x347-nvl72-hybrid` | 887.6 | 1,961.3-3,640.5 | 1.92 | yes | 6.155x | 2.179x | 0.354x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,658.7 | 1,006.4-1,868.0 | 15.41 | **no** | `b200_sxm-x173-nvl72-hybrid` | 522.7 | 705.8-1,310.1 | 3.14 | yes | 6.999x | 1.426x | 0.204x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,837.3 | 2,162.6-4,014.1 | 9.48 | **no** | `b200_sxm-x347-nvl72-hybrid` | 666.9 | 854.7-1,586.4 | 3.31 | yes | 7.253x | 2.530x | 0.349x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,634.9 | 351.4-652.2 | 19.73 | **no** | `b200_sxm-x173-nvl72-hybrid` | 265.7 | 210.5-390.7 | 5.35 | yes | 6.152x | 1.669x | 0.271x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,988.1 | 595.9-1,106.1 | 21.26 | **no** | `b200_sxm-x347-nvl72-hybrid` | 358.1 | 460.6-854.9 | 3.30 | yes | 8.344x | 1.294x | 0.155x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 477.4 | 113.5-210.7 | 17.83 | **no** | `b200_sxm-x173-nvl72-hybrid` | 142.9 | 57.2-106.2 | 10.58 | **no** | 3.341x | 1.983x | 0.594x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,022.9 | 228.9-424.8 | 18.95 | **no** | `b200_sxm-x347-nvl72-hybrid` | 175.3 | 86.5-160.5 | 8.60 | **no** | 5.834x | 2.647x | 0.454x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.092x to 0.594x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,114.4 | 1,662.7-3,086.2 | 10.49 | **no** | `a100_sxm_80gb-x126-hybrid` | 449.6 | 802.4-1,489.4 | 2.38 | yes | 9.151x | 2.072x | 0.226x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,340.1 | 3,354.3-6,226.0 | 6.75 | yes | `a100_sxm_80gb-x168-hybrid` | 448.5 | 805.4-1,494.9 | 2.36 | yes | 11.906x | 4.165x | 0.350x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,114.4 | 1,662.7-3,086.2 | 10.49 | **no** | `a100_sxm_80gb-x126-hybrid` | 449.6 | 802.4-1,489.4 | 2.38 | yes | 9.151x | 2.072x | 0.226x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,340.1 | 3,354.3-6,226.0 | 6.75 | yes | `a100_sxm_80gb-x168-hybrid` | 448.5 | 805.4-1,494.9 | 2.36 | yes | 11.906x | 4.165x | 0.350x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,114.4 | 1,662.7-3,086.2 | 10.49 | **no** | `a100_sxm_80gb-x126-hybrid` | 449.6 | 802.4-1,489.4 | 2.38 | yes | 9.151x | 2.072x | 0.226x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,340.1 | 3,354.3-6,226.0 | 6.75 | yes | `a100_sxm_80gb-x168-hybrid` | 448.5 | 805.4-1,494.9 | 2.36 | yes | 11.906x | 4.165x | 0.350x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,114.4 | 1,662.7-3,086.2 | 10.49 | **no** | `a100_sxm_80gb-x126-hybrid` | 449.6 | 802.4-1,489.4 | 2.38 | yes | 9.151x | 2.072x | 0.226x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,340.1 | 3,354.3-6,226.0 | 6.75 | yes | `a100_sxm_80gb-x168-hybrid` | 448.5 | 805.4-1,494.9 | 2.36 | yes | 11.906x | 4.165x | 0.350x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,114.4 | 1,662.7-3,086.2 | 10.49 | **no** | `a100_sxm_80gb-x126-hybrid` | 449.6 | 802.4-1,489.4 | 2.38 | yes | 9.151x | 2.072x | 0.226x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,340.1 | 3,354.3-6,226.0 | 6.75 | yes | `a100_sxm_80gb-x168-hybrid` | 448.5 | 805.4-1,494.9 | 2.36 | yes | 11.906x | 4.165x | 0.350x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,114.4 | 1,662.7-3,086.2 | 10.49 | **no** | `a100_sxm_80gb-x126-hybrid` | 389.1 | 572.8-1,063.2 | 2.88 | yes | 10.574x | 2.903x | 0.275x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,313.8 | 3,416.2-6,340.8 | 6.60 | yes | `a100_sxm_80gb-x448-hybrid` | 434.2 | 776.8-1,441.8 | 2.37 | yes | 12.239x | 4.398x | 0.359x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,059.2 | 1,647.7-3,058.3 | 10.45 | **no** | `a100_sxm_80gb-x272-hybrid` | 383.1 | 540.5-1,003.2 | 3.01 | yes | 10.596x | 3.048x | 0.288x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,310.5 | 3,401.5-6,313.6 | 6.62 | yes | `a100_sxm_80gb-x672-hybrid` | 434.2 | 798.0-1,481.2 | 2.31 | yes | 12.232x | 4.262x | 0.348x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,197.7 | 752.9-1,397.5 | 18.01 | **no** | `a100_sxm_80gb-x335-hybrid` | 236.2 | 235.0-436.2 | 4.26 | yes | 13.538x | 3.204x | 0.237x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,417.5 | 1,619.6-3,006.2 | 11.56 | **no** | `a100_sxm_80gb-x672-hybrid` | 323.7 | 394.3-731.9 | 3.48 | yes | 13.647x | 4.108x | 0.301x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,271.0 | 258.5-479.8 | 20.85 | **no** | `a100_sxm_80gb-x335-hybrid` | 98.5 | 131.0-243.1 | 3.19 | yes | 12.899x | 1.974x | 0.153x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,403.2 | 430.0-798.2 | 23.69 | **no** | `a100_sxm_80gb-x672-hybrid` | 156.7 | 139.7-259.2 | 4.76 | yes | 15.336x | 3.079x | 0.201x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 424.2 | 96.9-179.9 | 18.56 | **no** | `a100_sxm_80gb-x272-hybrid` | 35.1 | 17.7-32.8 | 8.42 | **no** | 12.080x | 5.482x | 0.454x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 759.1 | 165.1-306.4 | 19.50 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.9 | 85.5-158.6 | 2.97 | yes | 12.662x | 1.932x | 0.153x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.153x to 0.454x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 2,050.3-3,805.6 | 8.96 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,065.2 | 3,251.2-6,034.7 | 1.39 | yes | 4.067x | 0.631x | 0.155x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,360.5 | 3,799.4-7,052.2 | 5.98 | yes | `b200_sxm-x58-nvl72-tensor` | 1,071.2 | 3,301.5-6,127.9 | 1.38 | yes | 5.004x | 1.151x | 0.230x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 2,050.3-3,805.6 | 8.96 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,042.5 | 2,801.1-5,199.2 | 1.58 | yes | 4.155x | 0.732x | 0.176x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,360.5 | 3,799.4-7,052.2 | 5.98 | yes | `b200_sxm-x58-nvl72-tensor` | 1,050.0 | 2,846.4-5,283.2 | 1.56 | yes | 5.105x | 1.335x | 0.261x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 2,050.3-3,805.6 | 8.96 | **no** | `b200_sxm-x49-nvl72-tensor` | 1,000.6 | 2,214.6-4,110.6 | 1.92 | yes | 4.330x | 0.926x | 0.214x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,360.5 | 3,799.4-7,052.2 | 5.98 | yes | `b200_sxm-x58-nvl72-tensor` | 1,010.6 | 2,250.4-4,177.0 | 1.90 | yes | 5.304x | 1.688x | 0.318x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 2,050.3-3,805.6 | 8.96 | **no** | `b200_sxm-x49-nvl72-tensor` | 927.9 | 1,601.8-2,973.1 | 2.46 | yes | 4.669x | 1.280x | 0.274x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,360.5 | 3,799.4-7,052.2 | 5.98 | yes | `b200_sxm-x58-nvl72-tensor` | 941.7 | 1,617.8-3,002.9 | 2.47 | yes | 5.692x | 2.348x | 0.413x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,332.0 | 2,050.3-3,805.6 | 8.96 | **no** | `b200_sxm-x49-hybrid` | 830.0 | 1,266.3-2,350.4 | 2.78 | yes | 5.219x | 1.619x | 0.310x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5,350.8 | 3,843.6-7,134.2 | 5.90 | yes | `b200_sxm-x87-nvl72-hybrid` | 922.5 | 1,965.2-3,647.7 | 1.99 | yes | 5.801x | 1.956x | 0.337x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,259.9 | 1,162.0-2,156.9 | 15.54 | **no** | `b200_sxm-x49-hybrid` | 701.7 | 843.3-1,565.2 | 3.53 | yes | 6.071x | 1.378x | 0.227x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,318.2 | 3,893.9-7,227.5 | 5.79 | yes | `b200_sxm-x231-nvl72-hybrid` | 932.5 | 1,926.5-3,575.8 | 2.05 | yes | 5.703x | 2.021x | 0.354x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,186.0 | 2,005.5-3,722.4 | 8.85 | **no** | `b200_sxm-x173-nvl72-hybrid` | 815.7 | 1,217.9-2,260.5 | 2.84 | yes | 5.132x | 1.647x | 0.321x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,316.2 | 3,880.9-7,203.5 | 5.81 | yes | `b200_sxm-x347-nvl72-hybrid` | 886.5 | 1,959.5-3,637.2 | 1.92 | yes | 5.997x | 1.981x | 0.330x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,426.8 | 936.2-1,737.8 | 15.52 | **no** | `b200_sxm-x173-nvl72-hybrid` | 519.7 | 704.0-1,306.7 | 3.13 | yes | 6.594x | 1.330x | 0.202x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,530.2 | 1,961.4-3,640.6 | 9.79 | **no** | `b200_sxm-x347-nvl72-hybrid` | 664.4 | 853.4-1,583.9 | 3.30 | yes | 6.818x | 2.298x | 0.337x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,455.9 | 317.7-589.6 | 19.43 | **no** | `b200_sxm-x173-nvl72-hybrid` | 262.6 | 210.0-389.8 | 5.30 | yes | 5.544x | 1.513x | 0.273x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,637.2 | 548.5-1,018.1 | 20.39 | **no** | `b200_sxm-x347-nvl72-hybrid` | 355.2 | 459.4-852.7 | 3.28 | yes | 7.424x | 1.194x | 0.161x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 416.4 | 99.6-184.8 | 17.73 | **no** | `b200_sxm-x173-nvl72-hybrid` | 139.3 | 56.9-105.7 | 10.37 | **no** | 2.989x | 1.749x | 0.585x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 872.6 | 203.4-377.6 | 18.19 | **no** | `b200_sxm-x347-nvl72-hybrid` | 172.6 | 86.2-159.9 | 8.50 | **no** | 5.054x | 2.361x | 0.467x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.155x to 0.585x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 1,539.8-2,858.0 | 11.08 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 809.6-1,502.8 | 2.36 | yes | 8.927x | 1.902x | 0.213x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.7 | 3,027.0-5,618.5 | 7.12 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.356x | 3.762x | 0.331x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 1,539.8-2,858.0 | 11.08 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 809.6-1,502.8 | 2.36 | yes | 8.927x | 1.902x | 0.213x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.7 | 3,027.0-5,618.5 | 7.12 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.356x | 3.762x | 0.331x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 1,539.8-2,858.0 | 11.08 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 809.6-1,502.8 | 2.36 | yes | 8.927x | 1.902x | 0.213x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.7 | 3,027.0-5,618.5 | 7.12 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.356x | 3.762x | 0.331x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 1,539.8-2,858.0 | 11.08 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 809.6-1,502.8 | 2.36 | yes | 8.927x | 1.902x | 0.213x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.7 | 3,027.0-5,618.5 | 7.12 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.356x | 3.762x | 0.331x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 1,539.8-2,858.0 | 11.08 | **no** | `a100_sxm_80gb-x136-hybrid` | 450.9 | 809.6-1,502.8 | 2.36 | yes | 8.927x | 1.902x | 0.213x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 5,084.7 | 3,027.0-5,618.5 | 7.12 | yes | `a100_sxm_80gb-x168-hybrid` | 447.8 | 804.7-1,493.6 | 2.36 | yes | 11.356x | 3.762x | 0.331x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,024.9 | 1,539.8-2,858.0 | 11.08 | **no** | `a100_sxm_80gb-x136-hybrid` | 396.2 | 594.6-1,103.7 | 2.82 | yes | 10.159x | 2.589x | 0.255x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,062.4 | 3,076.9-5,711.1 | 6.98 | yes | `a100_sxm_80gb-x448-hybrid` | 433.5 | 776.2-1,440.7 | 2.37 | yes | 11.679x | 3.964x | 0.339x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 3,937.8 | 1,564.4-2,903.7 | 10.67 | **no** | `a100_sxm_80gb-x272-hybrid` | 382.0 | 539.9-1,002.1 | 3.00 | yes | 10.307x | 2.898x | 0.281x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,059.2 | 3,065.0-5,689.1 | 7.00 | yes | `a100_sxm_80gb-x672-hybrid` | 433.5 | 797.4-1,480.1 | 2.30 | yes | 11.672x | 3.844x | 0.329x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,960.5 | 701.8-1,302.6 | 17.89 | **no** | `a100_sxm_80gb-x335-hybrid` | 234.9 | 234.7-435.6 | 4.24 | yes | 12.601x | 2.991x | 0.237x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,982.8 | 1,468.8-2,726.3 | 11.50 | **no** | `a100_sxm_80gb-x672-hybrid` | 322.5 | 393.8-730.9 | 3.47 | yes | 12.350x | 3.730x | 0.302x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,129.9 | 234.6-435.4 | 20.43 | **no** | `a100_sxm_80gb-x335-hybrid` | 97.7 | 130.6-242.3 | 3.17 | yes | 11.570x | 1.797x | 0.155x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,978.0 | 398.9-740.3 | 21.03 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.6 | 139.4-258.8 | 4.73 | yes | 12.712x | 2.860x | 0.225x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 401.3 | 104.0-193.1 | 16.35 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.2 | 19.2-35.6 | 8.23 | **no** | 10.774x | 5.422x | 0.503x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 602.8 | 147.9-274.6 | 17.28 | **no** | `a100_sxm_80gb-x672-hybrid` | 59.3 | 81.3-151.0 | 3.09 | yes | 10.165x | 1.819x | 0.179x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.155x to 0.503x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-kimi-k3`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | 927.8 | 431.8-801.5 | 9.11 | **no** | `b200_sxm-x201-nvl72-hybrid` | 486.8 | 1,328.9-2,466.5 | 1.55 | yes | 1.906x | 0.325x | 0.171x |
| Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 1,776.9 | 1,482.7-2,752.0 | 5.08 | yes | `b200_sxm-x202-nvl72-hybrid` | 487.2 | 1,331.0-2,470.5 | 1.55 | yes | 3.647x | 1.114x | 0.305x |
| Kimi-K3 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 862.2 | 552.0-1,024.7 | 6.62 | yes | `b200_sxm-x202-nvl72-hybrid` | 487.2 | 1,331.0-2,470.5 | 1.55 | yes | 1.770x | 0.415x | 0.234x |
| Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,755.0 | 1,693.4-3,143.3 | 4.39 | yes | `b200_sxm-x462-nvl72-hybrid` | 480.3 | 1,243.1-2,307.5 | 1.64 | yes | 3.654x | 1.362x | 0.373x |
| Kimi-K3 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 862.2 | 552.0-1,024.7 | 6.62 | yes | `b200_sxm-x202-nvl72-hybrid` | 480.4 | 1,248.6-2,317.7 | 1.63 | yes | 1.795x | 0.442x | 0.246x |
| Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,755.0 | 1,693.4-3,143.3 | 4.39 | yes | `b200_sxm-x462-nvl72-hybrid` | 480.3 | 1,243.1-2,307.5 | 1.64 | yes | 3.654x | 1.362x | 0.373x |
| Kimi-K3 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 862.2 | 552.0-1,024.7 | 6.62 | yes | `b200_sxm-x202-nvl72-hybrid` | 455.1 | 996.8-1,850.1 | 1.94 | yes | 1.895x | 0.554x | 0.292x |
| Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,755.0 | 1,693.4-3,143.3 | 4.39 | yes | `b200_sxm-x462-nvl72-hybrid` | 476.9 | 1,196.8-2,221.5 | 1.69 | yes | 3.680x | 1.415x | 0.385x |
| Kimi-K3 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 823.8 | 348.4-646.6 | 10.03 | **no** | `b200_sxm-x202-nvl72-hybrid` | 412.7 | 731.6-1,357.9 | 2.39 | yes | 1.996x | 0.476x | 0.239x |
| Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,755.0 | 1,693.4-3,143.3 | 4.39 | yes | `b200_sxm-x462-nvl72-hybrid` | 451.6 | 944.1-1,752.4 | 2.03 | yes | 3.886x | 1.794x | 0.462x |
| Kimi-K3 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 717.4 | 279.7-519.2 | 10.87 | **no** | `b200_sxm-x202-nvl72-hybrid` | 350.3 | 474.0-879.8 | 3.13 | yes | 2.048x | 0.590x | 0.288x |
| Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,529.9 | 1,125.2-2,088.6 | 5.76 | yes | `b200_sxm-x462-nvl72-hybrid` | 408.8 | 659.6-1,224.3 | 2.63 | yes | 3.742x | 1.706x | 0.456x |
| Kimi-K3 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 530.9 | 156.6-290.6 | 14.38 | **no** | `b200_sxm-x202-nvl72-hybrid` | 274.2 | 263.9-489.7 | 4.41 | yes | 1.936x | 0.593x | 0.306x |
| Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,261.2 | 680.8-1,263.7 | 7.85 | yes | `b200_sxm-x462-nvl72-hybrid` | 345.5 | 406.5-754.6 | 3.60 | yes | 3.651x | 1.675x | 0.459x |
| Kimi-K3 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 174.4 | 42.0-78.0 | 17.60 | **no** | `b200_sxm-x202-nvl72-hybrid` | 140.2 | 72.0-133.6 | 8.26 | **no** | 1.244x | 0.584x | 0.469x |
| Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 508.9 | 190.9-354.4 | 11.30 | **no** | `b200_sxm-x462-nvl72-hybrid` | 193.9 | 172.8-320.8 | 4.76 | yes | 2.625x | 1.105x | 0.421x |
| Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 45.8 | 11.1-20.6 | 17.53 | **no** | `b200_sxm-x202-nvl72-hybrid` | 63.2 | 18.3-34.1 | 14.62 | **no** | 0.724x | 0.604x | 0.834x |
| Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 144.4 | 48.4-89.8 | 12.65 | **no** | `b200_sxm-x462-nvl72-hybrid` | 88.0 | 45.7-84.9 | 8.16 | **no** | 1.641x | 1.058x | 0.645x |
| Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 11.5 | 2.8-5.3 | 17.14 | **no** | `b200_sxm-x202-nvl72-hybrid` | 25.1 | 8.2-15.3 | 12.96 | **no** | 0.457x | 0.346x | 0.756x |
| Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 36.9 | 17.3-32.0 | 9.07 | **no** | `b200_sxm-x462-nvl72-hybrid` | 38.7 | 11.6-21.5 | 14.19 | **no** | 0.954x | 1.493x | 1.565x |

**Does the ratio compress?** Of 20 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.171x to 1.565x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 10 of 20 ROM rows and 15 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-kimi-k3`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x398` | 687.6 | 334.2-620.3 | 8.72 | **no** | `a100_sxm_80gb-x393-hybrid` | 127.8 | 198.2-367.8 | 2.73 | yes | 5.380x | 1.687x | 0.313x |
| Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x10` | 1,698.4 | 1,244.0-2,309.1 | 5.79 | yes | `a100_sxm_80gb-x560-hybrid` | 129.9 | 200.9-372.9 | 2.74 | yes | 13.078x | 6.192x | 0.473x |
| Kimi-K3 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 564.8 | 345.6-641.5 | 6.93 | yes | `a100_sxm_80gb-x394-hybrid` | 127.9 | 198.3-368.0 | 2.73 | yes | 4.417x | 1.743x | 0.395x |
| Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,397.1 | 1,344.2-2,495.0 | 4.41 | yes | `a100_sxm_80gb-x1231-hybrid` | 127.9 | 190.0-352.8 | 2.85 | yes | 10.924x | 7.073x | 0.647x |
| Kimi-K3 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 564.8 | 345.6-641.5 | 6.93 | yes | `a100_sxm_80gb-x394-hybrid` | 127.9 | 198.3-368.0 | 2.73 | yes | 4.417x | 1.743x | 0.395x |
| Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,397.1 | 1,344.2-2,495.0 | 4.41 | yes | `a100_sxm_80gb-x1231-hybrid` | 127.9 | 190.0-352.8 | 2.85 | yes | 10.924x | 7.073x | 0.647x |
| Kimi-K3 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 549.7 | 224.0-415.8 | 10.41 | **no** | `a100_sxm_80gb-x394-hybrid` | 125.8 | 183.4-340.4 | 2.91 | yes | 4.371x | 1.221x | 0.279x |
| Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,397.1 | 1,344.2-2,495.0 | 4.41 | yes | `a100_sxm_80gb-x1231-hybrid` | 127.9 | 190.0-352.8 | 2.85 | yes | 10.924x | 7.073x | 0.647x |
| Kimi-K3 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 484.6 | 184.2-341.9 | 11.15 | **no** | `a100_sxm_80gb-x394-hybrid` | 111.1 | 115.4-214.2 | 4.08 | yes | 4.361x | 1.596x | 0.366x |
| Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,397.1 | 1,344.2-2,495.0 | 4.41 | yes | `a100_sxm_80gb-x1231-hybrid` | 127.9 | 190.0-352.8 | 2.85 | yes | 10.924x | 7.073x | 0.647x |
| Kimi-K3 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 335.1 | 100.2-186.0 | 14.18 | **no** | `a100_sxm_80gb-x394-hybrid` | 93.2 | 98.7-183.2 | 4.00 | yes | 3.596x | 1.015x | 0.282x |
| Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,158.2 | 914.8-1,698.0 | 5.37 | yes | `a100_sxm_80gb-x1231-hybrid` | 118.9 | 138.8-257.7 | 3.63 | yes | 9.745x | 6.589x | 0.676x |
| Kimi-K3 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 199.1 | 52.6-97.7 | 16.03 | **no** | `a100_sxm_80gb-x394-hybrid` | 74.0 | 53.3-98.9 | 5.89 | yes | 2.691x | 0.988x | 0.367x |
| Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 847.6 | 653.5-1,213.1 | 5.50 | yes | `a100_sxm_80gb-x1231-hybrid` | 100.1 | 78.7-146.1 | 5.39 | yes | 8.468x | 8.306x | 0.981x |
| Kimi-K3 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 55.1 | 13.6-25.2 | 17.20 | **no** | `a100_sxm_80gb-x394-hybrid` | 41.7 | 33.7-62.6 | 5.24 | yes | 1.322x | 0.403x | 0.305x |
| Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 301.7 | 202.4-375.7 | 6.32 | yes | `a100_sxm_80gb-x1231-hybrid` | 63.3 | 76.0-141.1 | 3.53 | yes | 4.765x | 2.664x | 0.559x |
| Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 14.0 | 3.4-6.4 | 17.20 | **no** | `a100_sxm_80gb-x394-hybrid` | 17.2 | 8.6-16.0 | 8.49 | **no** | 0.812x | 0.401x | 0.494x |
| Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 81.8 | 52.2-96.9 | 6.65 | yes | `a100_sxm_80gb-x1231-hybrid` | 33.8 | 21.3-39.6 | 6.72 | yes | 2.420x | 2.448x | 1.012x |
| Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 3.5 | 0.9-1.6 | 17.14 | **no** | `a100_sxm_80gb-x394-hybrid` | 6.7 | 2.2-4.0 | 13.14 | **no** | 0.523x | 0.401x | 0.767x |
| Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x22` | 20.8 | 15.4-28.5 | 5.74 | yes | `a100_sxm_80gb-x1231-hybrid` | 13.0 | 7.9-14.7 | 6.99 | yes | 1.595x | 1.943x | 1.218x |

**Does the ratio compress?** Of 20 class rows in this study, 18 move the ROM-versus-GPU ratio DOWN under speculation and 2 move it UP. The movement spans 0.279x to 1.218x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 12 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-kimi-k3-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x383` | 589.0 | 388.3-720.8 | 6.43 | yes | `b200_sxm-x195-nvl72-hybrid` | 478.5 | 1,235.4-2,293.1 | 1.64 | yes | 1.231x | 0.314x | 0.255x |
| Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | 1,528.2 | 883.2-1,639.3 | 7.34 | yes | `b200_sxm-x520-nvl72-hybrid` | 472.0 | 1,122.7-2,083.9 | 1.78 | yes | 3.238x | 0.787x | 0.243x |
| Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,160.8 | 1,507.5-2,798.2 | 3.26 | yes | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | 837.0-1,553.6 | 2.29 | yes | 2.563x | 1.801x | 0.703x |
| Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,160.8 | 1,507.5-2,798.2 | 3.26 | yes | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | 837.0-1,553.6 | 2.29 | yes | 2.563x | 1.801x | 0.703x |
| Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,160.8 | 1,507.5-2,798.2 | 3.26 | yes | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | 837.0-1,553.6 | 2.29 | yes | 2.563x | 1.801x | 0.703x |
| Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,160.8 | 1,507.5-2,798.2 | 3.26 | yes | `b200_sxm-x1965-nvl72-hybrid` | 452.8 | 837.0-1,553.6 | 2.29 | yes | 2.563x | 1.801x | 0.703x |
| Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,142.7 | 1,079.9-2,004.4 | 4.49 | yes | `b200_sxm-x1965-nvl72-hybrid` | 447.0 | 768.1-1,425.8 | 2.47 | yes | 2.557x | 1.406x | 0.550x |
| Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 1,133.2 | 684.5-1,270.5 | 7.02 | yes | `b200_sxm-x1965-nvl72-hybrid` | 405.2 | 463.2-859.7 | 3.71 | yes | 2.797x | 1.478x | 0.528x |
| Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 517.3 | 213.6-396.4 | 10.27 | **no** | `b200_sxm-x1965-nvl72-hybrid` | 272.8 | 193.6-359.4 | 5.97 | yes | 1.896x | 1.103x | 0.582x |
| Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 151.8 | 54.6-101.4 | 11.78 | **no** | `b200_sxm-x1965-nvl72-hybrid` | 145.3 | 71.2-132.2 | 8.64 | **no** | 1.045x | 0.767x | 0.734x |
| Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x68` | 39.3 | 13.7-25.4 | 12.19 | **no** | `b200_sxm-x1965-nvl72-hybrid` | 49.4 | 23.0-42.7 | 9.10 | **no** | 0.795x | 0.594x | 0.747x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.243x to 0.747x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 11 ROM rows and 9 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-kimi-k3-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x399` | 379.3 | 155.2-288.2 | 10.36 | **no** | `a100_sxm_80gb-x394-hybrid` | 126.0 | 155.4-288.4 | 3.44 | yes | 3.012x | 0.999x | 0.332x |
| Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x23` | 1,329.0 | 638.1-1,184.4 | 8.83 | **no** | `a100_sxm_80gb-x1287-hybrid` | 125.9 | 149.5-277.5 | 3.57 | yes | 10.557x | 4.267x | 0.404x |
| Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 989.3 | 1,227.8-2,279.0 | 3.42 | yes | `a100_sxm_80gb-x5316-hybrid` | 117.7 | 115.8-215.0 | 4.31 | yes | 8.404x | 10.601x | 1.261x |
| Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 989.3 | 1,227.8-2,279.0 | 3.42 | yes | `a100_sxm_80gb-x5316-hybrid` | 117.7 | 115.8-215.0 | 4.31 | yes | 8.404x | 10.601x | 1.261x |
| Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 989.3 | 1,227.8-2,279.0 | 3.42 | yes | `a100_sxm_80gb-x5316-hybrid` | 117.7 | 115.8-215.0 | 4.31 | yes | 8.404x | 10.601x | 1.261x |
| Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 989.3 | 1,227.8-2,279.0 | 3.42 | yes | `a100_sxm_80gb-x5316-hybrid` | 117.7 | 115.8-215.0 | 4.31 | yes | 8.404x | 10.601x | 1.261x |
| Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 881.4 | 1,039.9-1,930.2 | 3.59 | yes | `a100_sxm_80gb-x5316-hybrid` | 117.7 | 115.8-215.0 | 4.31 | yes | 7.488x | 8.979x | 1.199x |
| Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 723.6 | 687.9-1,276.8 | 4.46 | yes | `a100_sxm_80gb-x5316-hybrid` | 117.7 | 115.8-215.0 | 4.31 | yes | 6.148x | 5.939x | 0.966x |
| Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 312.0 | 229.1-425.2 | 5.77 | yes | `a100_sxm_80gb-x5316-hybrid` | 91.5 | 64.0-118.7 | 6.07 | yes | 3.408x | 3.581x | 1.051x |
| Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 87.5 | 60.5-112.3 | 6.13 | yes | `a100_sxm_80gb-x5316-hybrid` | 59.8 | 31.9-59.2 | 7.94 | **no** | 1.464x | 1.895x | 1.294x |
| Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 22.4 | 15.2-28.2 | 6.25 | yes | `a100_sxm_80gb-x5316-hybrid` | 29.9 | 8.2-15.2 | 15.54 | **no** | 0.748x | 1.859x | 2.486x |

**Does the ratio compress?** Of 11 class rows in this study, 3 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.332x to 2.486x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 9 of 11 ROM rows and 9 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-kimi-k3-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,365.7 | 563.6-1,046.0 | 10.28 | **no** | `b200_sxm-x201-nvl72-hybrid` | 488.3 | 1,331.6-2,471.6 | 1.55 | yes | 2.797x | 0.423x | 0.151x |
| Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,158.1 | 1,382.8-2,566.7 | 6.62 | yes | `b200_sxm-x202-nvl72-hybrid` | 488.6 | 1,333.8-2,475.6 | 1.55 | yes | 4.417x | 1.037x | 0.235x |
| Kimi-K3 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,365.7 | 563.6-1,046.0 | 10.28 | **no** | `b200_sxm-x201-nvl72-hybrid` | 488.3 | 1,331.6-2,471.6 | 1.55 | yes | 2.797x | 0.423x | 0.151x |
| Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,158.1 | 1,382.8-2,566.7 | 6.62 | yes | `b200_sxm-x202-nvl72-hybrid` | 488.6 | 1,333.8-2,475.6 | 1.55 | yes | 4.417x | 1.037x | 0.235x |
| Kimi-K3 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,365.7 | 563.6-1,046.0 | 10.28 | **no** | `b200_sxm-x201-nvl72-hybrid` | 481.9 | 1,249.8-2,319.8 | 1.63 | yes | 2.834x | 0.451x | 0.159x |
| Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,158.1 | 1,382.8-2,566.7 | 6.62 | yes | `b200_sxm-x202-nvl72-hybrid` | 482.2 | 1,251.9-2,323.6 | 1.63 | yes | 4.475x | 1.105x | 0.247x |
| Kimi-K3 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,365.7 | 563.6-1,046.0 | 10.28 | **no** | `b200_sxm-x201-nvl72-hybrid` | 458.1 | 999.0-1,854.3 | 1.94 | yes | 2.981x | 0.564x | 0.189x |
| Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,158.1 | 1,382.8-2,566.7 | 6.62 | yes | `b200_sxm-x202-nvl72-hybrid` | 458.5 | 1,000.9-1,857.8 | 1.94 | yes | 4.707x | 1.382x | 0.294x |
| Kimi-K3 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,365.7 | 563.6-1,046.0 | 10.28 | **no** | `b200_sxm-x201-nvl72-hybrid` | 417.8 | 734.7-1,363.7 | 2.41 | yes | 3.269x | 0.767x | 0.235x |
| Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 2,158.1 | 1,382.8-2,566.7 | 6.62 | yes | `b200_sxm-x202-nvl72-hybrid` | 418.3 | 736.0-1,366.1 | 2.41 | yes | 5.159x | 1.879x | 0.364x |
| Kimi-K3 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,365.7 | 563.6-1,046.0 | 10.28 | **no** | `b200_sxm-x201-nvl72-hybrid` | 357.9 | 500.2-928.4 | 3.03 | yes | 3.816x | 1.127x | 0.295x |
| Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,144.4 | 1,398.5-2,595.8 | 6.50 | yes | `b200_sxm-x347-nvl72-hybrid` | 399.0 | 606.9-1,126.5 | 2.79 | yes | 5.374x | 2.304x | 0.429x |
| Kimi-K3 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,207.4 | 472.8-877.5 | 10.83 | **no** | `b200_sxm-x201-nvl72-hybrid` | 283.7 | 315.4-585.5 | 3.81 | yes | 4.255x | 1.499x | 0.352x |
| Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,868.6 | 846.4-1,571.1 | 9.36 | **no** | `b200_sxm-x347-nvl72-hybrid` | 331.7 | 386.4-717.2 | 3.64 | yes | 5.633x | 2.191x | 0.389x |
| Kimi-K3 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 688.8 | 151.2-280.6 | 19.32 | **no** | `b200_sxm-x201-nvl72-hybrid` | 150.9 | 102.0-189.3 | 6.27 | yes | 4.565x | 1.482x | 0.325x |
| Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,089.0 | 349.9-649.5 | 13.19 | **no** | `b200_sxm-x347-nvl72-hybrid` | 182.1 | 127.1-236.0 | 6.07 | yes | 5.978x | 2.753x | 0.460x |
| Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 217.0 | 47.3-87.8 | 19.45 | **no** | `b200_sxm-x201-nvl72-hybrid` | 72.7 | 26.9-50.0 | 11.45 | **no** | 2.985x | 1.757x | 0.589x |
| Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 369.4 | 95.8-177.8 | 16.35 | **no** | `b200_sxm-x347-nvl72-hybrid` | 87.1 | 60.2-111.8 | 6.13 | yes | 4.241x | 1.590x | 0.375x |
| Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 57.1 | 13.7-25.5 | 17.66 | **no** | `b200_sxm-x201-nvl72-hybrid` | 35.1 | 19.1-35.5 | 7.77 | yes | 1.629x | 0.717x | 0.440x |
| Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 99.2 | 39.7-73.8 | 10.58 | **no** | `b200_sxm-x347-nvl72-hybrid` | 41.9 | 15.7-29.1 | 11.36 | **no** | 2.366x | 2.539x | 1.073x |

**Does the ratio compress?** Of 20 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.151x to 1.073x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 6 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-kimi-k3-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 920.8 | 422.5-784.2 | 9.24 | **no** | `a100_sxm_80gb-x394-hybrid` | 128.3 | 198.6-368.5 | 2.74 | yes | 7.174x | 2.128x | 0.297x |
| Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,855.5 | 1,994.0-3,701.2 | 3.95 | yes | `a100_sxm_80gb-x672-hybrid` | 129.6 | 198.6-368.5 | 2.77 | yes | 14.319x | 10.043x | 0.701x |
| Kimi-K3 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 920.8 | 422.5-784.2 | 9.24 | **no** | `a100_sxm_80gb-x394-hybrid` | 128.3 | 198.6-368.5 | 2.74 | yes | 7.174x | 2.128x | 0.297x |
| Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,855.5 | 1,994.0-3,701.2 | 3.95 | yes | `a100_sxm_80gb-x672-hybrid` | 129.6 | 198.6-368.5 | 2.77 | yes | 14.319x | 10.043x | 0.701x |
| Kimi-K3 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 920.8 | 422.5-784.2 | 9.24 | **no** | `a100_sxm_80gb-x394-hybrid` | 128.3 | 198.6-368.5 | 2.74 | yes | 7.174x | 2.128x | 0.297x |
| Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,855.5 | 1,994.0-3,701.2 | 3.95 | yes | `a100_sxm_80gb-x672-hybrid` | 129.6 | 198.6-368.5 | 2.77 | yes | 14.319x | 10.043x | 0.701x |
| Kimi-K3 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 920.8 | 422.5-784.2 | 9.24 | **no** | `a100_sxm_80gb-x394-hybrid` | 126.3 | 183.7-340.9 | 2.92 | yes | 7.292x | 2.300x | 0.315x |
| Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,855.5 | 1,994.0-3,701.2 | 3.95 | yes | `a100_sxm_80gb-x672-hybrid` | 129.6 | 198.6-368.5 | 2.77 | yes | 14.319x | 10.043x | 0.701x |
| Kimi-K3 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 920.8 | 422.5-784.2 | 9.24 | **no** | `a100_sxm_80gb-x394-hybrid` | 111.9 | 116.1-215.5 | 4.09 | yes | 8.227x | 3.639x | 0.442x |
| Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,847.0 | 1,476.4-2,740.4 | 5.30 | yes | `a100_sxm_80gb-x672-hybrid` | 123.1 | 157.1-291.5 | 3.32 | yes | 15.009x | 9.400x | 0.626x |
| Kimi-K3 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 812.1 | 341.4-633.6 | 10.09 | **no** | `a100_sxm_80gb-x394-hybrid` | 94.3 | 100.8-187.1 | 3.97 | yes | 8.611x | 3.386x | 0.393x |
| Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,644.1 | 955.4-1,773.4 | 7.30 | yes | `a100_sxm_80gb-x672-hybrid` | 106.1 | 95.1-176.5 | 4.73 | yes | 15.501x | 10.047x | 0.648x |
| Kimi-K3 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 663.4 | 204.6-379.8 | 13.75 | **no** | `a100_sxm_80gb-x394-hybrid` | 75.4 | 59.1-109.7 | 5.41 | yes | 8.797x | 3.462x | 0.393x |
| Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,324.8 | 736.6-1,367.3 | 7.63 | yes | `a100_sxm_80gb-x672-hybrid` | 88.9 | 83.2-154.4 | 4.53 | yes | 14.895x | 8.855x | 0.594x |
| Kimi-K3 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 245.9 | 58.4-108.4 | 17.86 | **no** | `a100_sxm_80gb-x394-hybrid` | 43.6 | 45.4-84.3 | 4.07 | yes | 5.639x | 1.285x | 0.228x |
| Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554.6 | 220.0-408.3 | 10.69 | **no** | `a100_sxm_80gb-x672-hybrid` | 53.0 | 55.4-102.7 | 4.06 | yes | 10.456x | 3.974x | 0.380x |
| Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 66.4 | 15.8-29.4 | 17.76 | **no** | `a100_sxm_80gb-x394-hybrid` | 18.5 | 17.6-32.6 | 4.47 | yes | 3.584x | 0.902x | 0.252x |
| Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 159.4 | 56.1-104.1 | 12.04 | **no** | `a100_sxm_80gb-x672-hybrid` | 24.6 | 19.7-36.7 | 5.27 | yes | 6.489x | 2.841x | 0.438x |
| Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 16.7 | 4.1-7.6 | 17.20 | **no** | `a100_sxm_80gb-x394-hybrid` | 7.5 | 4.8-8.8 | 6.69 | yes | 2.224x | 0.865x | 0.389x |
| Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 40.9 | 19.0-35.2 | 9.14 | **no** | `a100_sxm_80gb-x672-hybrid` | 9.3 | 11.7-21.7 | 3.35 | yes | 4.415x | 1.621x | 0.367x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.228x to 0.701x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | 3,851.6 | 1,981.6-3,678.1 | 8.24 | **no** | `b200_sxm-x23-nvl72-tensor` | 1,267.3 | 3,454.4-6,411.8 | 1.56 | yes | 3.039x | 0.574x | 0.189x |
| MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 5,503.2 | 7,700.0-14,292.3 | 3.03 | yes | `b200_sxm-x29-nvl72-tensor` | 1,307.1 | 3,755.6-6,970.8 | 1.48 | yes | 4.210x | 2.050x | 0.487x |
| MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 3,177.8 | 2,885.6-5,356.0 | 4.67 | yes | `b200_sxm-x96-nvl72-hybrid` | 1,364.4 | 4,337.1-8,050.3 | 1.33 | yes | 2.329x | 0.665x | 0.286x |
| MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,337.9 | 3,046.6-5,654.9 | 4.65 | yes | `b200_sxm-x636-nvl72-hybrid` | 1,369.1 | 4,545.9-8,437.9 | 1.28 | yes | 2.438x | 0.670x | 0.275x |
| MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 3,177.8 | 2,885.6-5,356.0 | 4.67 | yes | `b200_sxm-x96-nvl72-hybrid` | 1,303.6 | 3,831.9-7,112.5 | 1.44 | yes | 2.438x | 0.753x | 0.309x |
| MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,337.9 | 3,046.6-5,654.9 | 4.65 | yes | `b200_sxm-x636-nvl72-hybrid` | 1,369.1 | 4,545.9-8,437.9 | 1.28 | yes | 2.438x | 0.670x | 0.275x |
| MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 3,177.8 | 2,885.6-5,356.0 | 4.67 | yes | `b200_sxm-x96-nvl72-hybrid` | 1,198.9 | 3,161.0-5,867.3 | 1.61 | yes | 2.651x | 0.913x | 0.344x |
| MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,337.9 | 3,046.6-5,654.9 | 4.65 | yes | `b200_sxm-x636-nvl72-hybrid` | 1,369.1 | 4,545.9-8,437.9 | 1.28 | yes | 2.438x | 0.670x | 0.275x |
| MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x282` | 3,164.1 | 2,501.3-4,642.8 | 5.36 | yes | `b200_sxm-x144-nvl72-hybrid` | 1,141.4 | 2,674.1-4,963.6 | 1.81 | yes | 2.772x | 0.935x | 0.337x |
| MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3,337.9 | 3,046.6-5,654.9 | 4.65 | yes | `b200_sxm-x636-nvl72-hybrid` | 1,332.7 | 4,088.5-7,588.7 | 1.38 | yes | 2.505x | 0.745x | 0.298x |
| MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 2,999.7 | 1,430.5-2,655.2 | 8.89 | **no** | `b200_sxm-x192-nvl72-hybrid` | 1,035.8 | 2,251.4-4,178.9 | 1.95 | yes | 2.896x | 0.635x | 0.219x |
| MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 2,752.9 | 2,707.2-5,025.0 | 4.31 | yes | `b200_sxm-x636-nvl72-hybrid` | 1,257.7 | 3,396.8-6,304.9 | 1.57 | yes | 2.189x | 0.797x | 0.364x |
| MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 2,528.9 | 1,277.9-2,371.9 | 8.39 | **no** | `b200_sxm-x192-nvl72-hybrid` | 830.0 | 1,498.0-2,780.5 | 2.35 | yes | 3.047x | 0.853x | 0.280x |
| MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 1,845.1 | 1,763.9-3,274.0 | 4.44 | yes | `b200_sxm-x636-nvl72-hybrid` | 1,134.2 | 2,586.3-4,800.6 | 1.86 | yes | 1.627x | 0.682x | 0.419x |
| MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 951.4 | 488.9-907.5 | 8.25 | **no** | `b200_sxm-x192-nvl72-hybrid` | 428.1 | 489.0-907.7 | 3.71 | yes | 2.222x | 1.000x | 0.450x |
| MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 600.0 | 540.6-1,003.5 | 4.71 | yes | `b200_sxm-x636-nvl72-hybrid` | 747.3 | 1,084.4-2,012.8 | 2.92 | yes | 0.803x | 0.499x | 0.621x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 238.5 | 134.3-249.3 | 7.53 | yes | `b200_sxm-x192-nvl72-hybrid` | 168.1 | 210.8-391.2 | 3.38 | yes | 1.419x | 0.637x | 0.449x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 159.0 | 138.9-257.9 | 4.85 | yes | `b200_sxm-x636-nvl72-hybrid` | 364.5 | 339.5-630.1 | 4.55 | yes | 0.436x | 0.409x | 0.938x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 59.7 | 33.9-62.9 | 7.47 | yes | `b200_sxm-x192-nvl72-hybrid` | 53.1 | 79.2-146.9 | 2.84 | yes | 1.125x | 0.428x | 0.381x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x22` | 40.2 | 57.8-107.3 | 2.95 | yes | `b200_sxm-x636-nvl72-hybrid` | 139.9 | 147.6-274.0 | 4.02 | yes | 0.287x | 0.392x | 1.362x |

**Does the ratio compress?** Of 20 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.189x to 1.362x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 16 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x61` | 3,551.3 | 1,641.3-3,046.4 | 9.17 | **no** | `a100_sxm_80gb-x60-tensor` | 414.3 | 795.6-1,476.8 | 2.21 | yes | 8.571x | 2.063x | 0.241x |
| MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 5,440.2 | 6,621.5-12,290.4 | 3.48 | yes | `a100_sxm_80gb-x56-hybrid` | 420.3 | 758.7-1,408.3 | 2.35 | yes | 12.943x | 8.727x | 0.674x |
| MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 2,500.3 | 2,975.1-5,522.2 | 3.56 | yes | `a100_sxm_80gb-x335-hybrid` | 409.8 | 803.4-1,491.2 | 2.16 | yes | 6.102x | 3.703x | 0.607x |
| MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2,846.5 | 4,428.3-8,219.4 | 2.73 | yes | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 794.0-1,473.7 | 2.16 | yes | 7.041x | 5.577x | 0.792x |
| MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 2,500.3 | 2,975.1-5,522.2 | 3.56 | yes | `a100_sxm_80gb-x335-hybrid` | 409.8 | 803.4-1,491.2 | 2.16 | yes | 6.102x | 3.703x | 0.607x |
| MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2,846.5 | 4,428.3-8,219.4 | 2.73 | yes | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 794.0-1,473.7 | 2.16 | yes | 7.041x | 5.577x | 0.792x |
| MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 2,500.3 | 2,975.1-5,522.2 | 3.56 | yes | `a100_sxm_80gb-x335-hybrid` | 405.6 | 866.8-1,608.8 | 1.98 | yes | 6.165x | 3.432x | 0.557x |
| MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2,846.5 | 4,428.3-8,219.4 | 2.73 | yes | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 794.0-1,473.7 | 2.16 | yes | 7.041x | 5.577x | 0.792x |
| MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 2,372.9 | 2,085.0-3,870.0 | 4.83 | yes | `a100_sxm_80gb-x391-hybrid` | 403.4 | 873.6-1,621.5 | 1.96 | yes | 5.883x | 2.387x | 0.406x |
| MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2,466.1 | 3,281.6-6,091.1 | 3.19 | yes | `a100_sxm_80gb-x1735-hybrid` | 404.3 | 794.0-1,473.7 | 2.16 | yes | 6.100x | 4.133x | 0.678x |
| MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 2,087.2 | 1,861.3-3,454.9 | 4.75 | yes | `a100_sxm_80gb-x391-hybrid` | 403.4 | 873.6-1,621.5 | 1.96 | yes | 5.175x | 2.131x | 0.412x |
| MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,970.3 | 2,190.5-4,065.9 | 3.81 | yes | `a100_sxm_80gb-x1735-hybrid` | 403.8 | 929.9-1,726.0 | 1.84 | yes | 4.880x | 2.356x | 0.483x |
| MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,533.9 | 1,198.8-2,225.1 | 5.43 | yes | `a100_sxm_80gb-x391-hybrid` | 369.2 | 768.4-1,426.2 | 2.04 | yes | 4.155x | 1.560x | 0.376x |
| MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,206.2 | 1,342.6-2,492.0 | 3.81 | yes | `a100_sxm_80gb-x1735-hybrid` | 403.8 | 929.9-1,726.0 | 1.84 | yes | 2.987x | 1.444x | 0.483x |
| MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 501.8 | 342.5-635.8 | 6.21 | yes | `a100_sxm_80gb-x391-hybrid` | 180.1 | 367.3-681.8 | 2.08 | yes | 2.787x | 0.932x | 0.335x |
| MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 356.0 | 372.1-690.8 | 4.06 | yes | `a100_sxm_80gb-x1735-hybrid` | 383.0 | 833.4-1,546.9 | 1.95 | yes | 0.930x | 0.447x | 0.480x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 131.0 | 126.3-234.4 | 4.40 | yes | `a100_sxm_80gb-x391-hybrid` | 64.5 | 101.5-188.4 | 2.69 | yes | 2.031x | 1.245x | 0.613x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 92.0 | 94.3-175.0 | 4.14 | yes | `a100_sxm_80gb-x1735-hybrid` | 192.8 | 401.2-744.6 | 2.04 | yes | 0.477x | 0.235x | 0.493x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 33.0 | 48.1-89.3 | 2.91 | yes | `a100_sxm_80gb-x391-hybrid` | 22.5 | 26.0-48.2 | 3.67 | yes | 1.471x | 1.854x | 1.261x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x31` | 23.1 | 38.1-70.7 | 2.58 | yes | `a100_sxm_80gb-x1735-hybrid` | 69.9 | 112.2-208.2 | 2.64 | yes | 0.331x | 0.339x | 1.025x |

**Does the ratio compress?** Of 20 class rows in this study, 18 move the ROM-versus-GPU ratio DOWN under speculation and 2 move it UP. The movement spans 0.241x to 1.261x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 19 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 2,931.9 | 1,674.5-3,108.1 | 7.42 | yes | `b200_sxm-x53-nvl72-tensor` | 1,286.9 | 4,150.8-7,704.4 | 1.31 | yes | 2.278x | 0.403x | 0.177x |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 5,241.1 | 4,123.6-7,654.0 | 5.39 | yes | `b200_sxm-x58-nvl72-tensor` | 1,301.9 | 4,235.8-7,862.3 | 1.30 | yes | 4.026x | 0.974x | 0.242x |
| MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,266.6 | 2,367.7-4,394.7 | 4.06 | yes | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 3,699.9-6,867.4 | 1.35 | yes | 1.919x | 0.640x | 0.334x |
| MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,266.6 | 2,367.7-4,394.7 | 4.06 | yes | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 3,699.9-6,867.4 | 1.35 | yes | 1.919x | 0.640x | 0.334x |
| MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,266.6 | 2,367.7-4,394.7 | 4.06 | yes | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 3,699.9-6,867.4 | 1.35 | yes | 1.919x | 0.640x | 0.334x |
| MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,266.6 | 2,367.7-4,394.7 | 4.06 | yes | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 3,699.9-6,867.4 | 1.35 | yes | 1.919x | 0.640x | 0.334x |
| MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2,133.3 | 2,278.7-4,229.6 | 3.97 | yes | `b200_sxm-x3149-nvl72-hybrid` | 1,181.4 | 3,699.9-6,867.4 | 1.35 | yes | 1.806x | 0.616x | 0.341x |
| MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,573.0 | 1,410.0-2,617.2 | 4.73 | yes | `b200_sxm-x3149-nvl72-hybrid` | 1,138.1 | 3,335.2-6,190.5 | 1.45 | yes | 1.382x | 0.423x | 0.306x |
| MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 585.1 | 455.4-845.2 | 5.45 | yes | `b200_sxm-x3149-nvl72-hybrid` | 866.4 | 2,503.3-4,646.4 | 1.47 | yes | 0.675x | 0.182x | 0.269x |
| MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 157.7 | 116.8-216.7 | 5.73 | yes | `b200_sxm-x3149-nvl72-hybrid` | 447.8 | 1,073.5-1,992.6 | 1.77 | yes | 0.352x | 0.109x | 0.309x |
| MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 40.0 | 29.3-54.4 | 5.79 | yes | `b200_sxm-x3149-nvl72-hybrid` | 158.9 | 295.0-547.5 | 2.28 | yes | 0.252x | 0.099x | 0.395x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.177x to 0.395x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | 2,769.4 | 1,420.8-2,637.3 | 8.26 | **no** | `a100_sxm_80gb-x139-tensor` | 416.1 | 803.5-1,491.3 | 2.20 | yes | 6.656x | 1.768x | 0.266x |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 5,043.9 | 4,613.9-8,564.1 | 4.64 | yes | `a100_sxm_80gb-x112-tensor` | 410.0 | 796.9-1,479.2 | 2.18 | yes | 12.302x | 5.790x | 0.471x |
| MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,455.6 | 1,742.9-3,235.1 | 3.54 | yes | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 718.2-1,333.1 | 2.19 | yes | 3.916x | 2.427x | 0.620x |
| MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,455.6 | 1,742.9-3,235.1 | 3.54 | yes | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 718.2-1,333.1 | 2.19 | yes | 3.916x | 2.427x | 0.620x |
| MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,455.6 | 1,742.9-3,235.1 | 3.54 | yes | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 718.2-1,333.1 | 2.19 | yes | 3.916x | 2.427x | 0.620x |
| MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,455.6 | 1,742.9-3,235.1 | 3.54 | yes | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 718.2-1,333.1 | 2.19 | yes | 3.916x | 2.427x | 0.620x |
| MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,455.6 | 1,742.9-3,235.1 | 3.54 | yes | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 718.2-1,333.1 | 2.19 | yes | 3.916x | 2.427x | 0.620x |
| MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,045.2 | 1,483.1-2,752.9 | 2.99 | yes | `a100_sxm_80gb-x8562-hybrid` | 371.7 | 718.2-1,333.1 | 2.19 | yes | 2.812x | 2.065x | 0.734x |
| MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 346.2 | 473.2-878.3 | 3.10 | yes | `a100_sxm_80gb-x8562-hybrid` | 331.9 | 669.1-1,242.0 | 2.10 | yes | 1.043x | 0.707x | 0.678x |
| MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 90.9 | 132.0-245.0 | 2.92 | yes | `a100_sxm_80gb-x8562-hybrid` | 258.2 | 559.1-1,037.8 | 1.96 | yes | 0.352x | 0.236x | 0.670x |
| MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 22.9 | 33.2-61.7 | 2.93 | yes | `a100_sxm_80gb-x8562-hybrid` | 101.1 | 171.5-318.3 | 2.50 | yes | 0.227x | 0.194x | 0.854x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.266x to 0.854x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 10 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 5,716.5 | 3,084.3-5,724.9 | 7.86 | yes | `b200_sxm-x31-nvl72-tensor` | 1,356.6 | 3,914.3-7,265.5 | 1.47 | yes | 4.214x | 0.788x | 0.187x |
| MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,512.3 | 5,629.5-10,449.1 | 4.90 | yes | `b200_sxm-x58-nvl72-tensor` | 1,413.8 | 4,509.8-8,370.7 | 1.33 | yes | 4.606x | 1.248x | 0.271x |
| MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 5,716.5 | 3,084.3-5,724.9 | 7.86 | yes | `b200_sxm-x31-nvl72-tensor` | 1,305.7 | 3,394.6-6,300.8 | 1.63 | yes | 4.378x | 0.909x | 0.208x |
| MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,512.3 | 5,629.5-10,449.1 | 4.90 | yes | `b200_sxm-x58-nvl72-tensor` | 1,380.6 | 4,042.3-7,503.0 | 1.45 | yes | 4.717x | 1.393x | 0.295x |
| MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 5,716.5 | 3,084.3-5,724.9 | 7.86 | yes | `b200_sxm-x31-nvl72-tensor` | 1,217.9 | 2,815.1-5,225.3 | 1.83 | yes | 4.694x | 1.096x | 0.233x |
| MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,512.3 | 5,629.5-10,449.1 | 4.90 | yes | `b200_sxm-x58-nvl72-tensor` | 1,320.7 | 3,409.9-6,329.2 | 1.64 | yes | 4.931x | 1.651x | 0.335x |
| MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 5,716.5 | 3,084.3-5,724.9 | 7.86 | yes | `b200_sxm-x31-nvl72-tensor` | 1,083.1 | 2,254.4-4,184.4 | 2.04 | yes | 5.278x | 1.368x | 0.259x |
| MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6,512.3 | 5,629.5-10,449.1 | 4.90 | yes | `b200_sxm-x58-nvl72-tensor` | 1,222.0 | 2,704.1-5,019.1 | 1.92 | yes | 5.329x | 2.082x | 0.391x |
| MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill` | 5,630.3 | 3,019.3-5,604.2 | 7.91 | **no** | `b200_sxm-x46-nvl72-tensor` | 1,023.3 | 1,882.0-3,493.3 | 2.31 | yes | 5.502x | 1.604x | 0.292x |
| MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 6,352.9 | 6,828.1-12,673.9 | 3.94 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,271.3 | 3,133.1-5,815.4 | 1.72 | yes | 4.997x | 2.179x | 0.436x |
| MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 5,495.4 | 3,011.1-5,589.1 | 7.74 | yes | `b200_sxm-x87-nvl72-hybrid` | 1,001.3 | 1,834.7-3,405.4 | 2.31 | yes | 5.488x | 1.641x | 0.299x |
| MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6,240.7 | 6,834.1-12,684.9 | 3.87 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,262.4 | 2,966.5-5,506.3 | 1.80 | yes | 4.943x | 2.304x | 0.466x |
| MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,472.4 | 3,030.0-5,624.1 | 7.66 | yes | `b200_sxm-x173-nvl72-hybrid` | 998.3 | 1,605.9-2,980.8 | 2.64 | yes | 5.481x | 1.887x | 0.344x |
| MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6,047.0 | 5,180.2-9,615.1 | 4.95 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,142.3 | 2,129.2-3,952.0 | 2.27 | yes | 5.294x | 2.433x | 0.460x |
| MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,472.1 | 1,356.0-2,516.9 | 13.98 | **no** | `b200_sxm-x173-nvl72-hybrid` | 678.9 | 575.4-1,068.1 | 5.00 | yes | 6.587x | 2.356x | 0.358x |
| MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,122.1 | 2,646.3-4,911.9 | 6.60 | yes | `b200_sxm-x347-nvl72-hybrid` | 818.9 | 828.4-1,537.6 | 4.19 | yes | 5.034x | 3.195x | 0.635x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,830.9 | 432.9-803.5 | 17.93 | **no** | `b200_sxm-x173-nvl72-hybrid` | 413.1 | 295.7-548.9 | 5.92 | yes | 4.432x | 1.464x | 0.330x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,614.2 | 807.6-1,499.0 | 8.47 | **no** | `b200_sxm-x347-nvl72-hybrid` | 509.4 | 277.4-514.9 | 7.79 | yes | 3.169x | 2.911x | 0.919x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 525.0 | 128.8-239.1 | 17.28 | **no** | `b200_sxm-x173-nvl72-hybrid` | 221.7 | 130.2-241.8 | 7.22 | yes | 2.368x | 0.989x | 0.418x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 452.3 | 280.4-520.4 | 6.84 | yes | `b200_sxm-x347-nvl72-hybrid` | 285.3 | 125.8-233.6 | 9.61 | **no** | 1.585x | 2.228x | 1.405x |

**Does the ratio compress?** Of 20 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.187x to 1.405x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 15 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 5,316.5 | 2,350.2-4,362.4 | 9.59 | **no** | `a100_sxm_80gb-x67-hybrid` | 471.2 | 779.0-1,445.9 | 2.56 | yes | 11.283x | 3.017x | 0.267x |
| MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,652.5 | 5,552.0-10,305.2 | 4.32 | yes | `a100_sxm_80gb-x224-hybrid` | 477.5 | 913.9-1,696.2 | 2.22 | yes | 11.838x | 6.075x | 0.513x |
| MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 5,316.5 | 2,350.2-4,362.4 | 9.59 | **no** | `a100_sxm_80gb-x67-hybrid` | 471.2 | 779.0-1,445.9 | 2.56 | yes | 11.283x | 3.017x | 0.267x |
| MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,652.5 | 5,552.0-10,305.2 | 4.32 | yes | `a100_sxm_80gb-x224-hybrid` | 477.5 | 913.9-1,696.2 | 2.22 | yes | 11.838x | 6.075x | 0.513x |
| MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 5,316.5 | 2,350.2-4,362.4 | 9.59 | **no** | `a100_sxm_80gb-x67-hybrid` | 471.2 | 779.0-1,445.9 | 2.56 | yes | 11.283x | 3.017x | 0.267x |
| MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,652.5 | 5,552.0-10,305.2 | 4.32 | yes | `a100_sxm_80gb-x224-hybrid` | 477.5 | 913.9-1,696.2 | 2.22 | yes | 11.838x | 6.075x | 0.513x |
| MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 5,316.5 | 2,350.2-4,362.4 | 9.59 | **no** | `a100_sxm_80gb-x67-hybrid` | 471.2 | 779.0-1,445.9 | 2.56 | yes | 11.283x | 3.017x | 0.267x |
| MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,652.5 | 5,552.0-10,305.2 | 4.32 | yes | `a100_sxm_80gb-x224-hybrid` | 477.5 | 913.9-1,696.2 | 2.22 | yes | 11.838x | 6.075x | 0.513x |
| MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 5,316.5 | 2,350.2-4,362.4 | 9.59 | **no** | `a100_sxm_80gb-x67-hybrid` | 407.5 | 639.5-1,187.0 | 2.70 | yes | 13.048x | 3.675x | 0.282x |
| MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,474.8 | 7,229.6-13,419.1 | 3.21 | yes | `a100_sxm_80gb-x672-hybrid` | 467.0 | 999.6-1,855.3 | 1.98 | yes | 11.724x | 7.233x | 0.617x |
| MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 5,152.8 | 2,349.3-4,360.7 | 9.30 | **no** | `a100_sxm_80gb-x154-hybrid` | 423.0 | 729.2-1,353.5 | 2.46 | yes | 12.181x | 3.222x | 0.264x |
| MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,323.7 | 5,895.0-10,941.9 | 3.83 | yes | `a100_sxm_80gb-x672-hybrid` | 467.0 | 999.6-1,855.3 | 1.98 | yes | 11.400x | 5.898x | 0.517x |
| MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,096.9 | 2,340.6-4,344.5 | 9.23 | **no** | `a100_sxm_80gb-x335-hybrid` | 426.3 | 781.1-1,449.7 | 2.31 | yes | 11.956x | 2.997x | 0.251x |
| MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,450.6 | 4,153.9-7,710.2 | 4.54 | yes | `a100_sxm_80gb-x672-hybrid` | 467.0 | 999.6-1,855.3 | 1.98 | yes | 9.531x | 4.156x | 0.436x |
| MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,830.4 | 1,015.8-1,885.5 | 15.99 | **no** | `a100_sxm_80gb-x335-hybrid` | 244.1 | 429.2-796.7 | 2.41 | yes | 15.689x | 2.367x | 0.151x |
| MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,330.3 | 2,006.1-3,723.6 | 4.93 | yes | `a100_sxm_80gb-x672-hybrid` | 337.0 | 572.1-1,061.9 | 2.50 | yes | 6.915x | 3.507x | 0.507x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,424.3 | 320.9-595.5 | 18.82 | **no** | `a100_sxm_80gb-x335-hybrid` | 108.2 | 182.7-339.1 | 2.51 | yes | 13.163x | 1.756x | 0.133x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 723.5 | 587.9-1,091.2 | 5.22 | yes | `a100_sxm_80gb-x672-hybrid` | 163.2 | 293.2-544.3 | 2.36 | yes | 4.433x | 2.005x | 0.452x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 395.4 | 95.7-177.6 | 17.52 | **no** | `a100_sxm_80gb-x335-hybrid` | 58.2 | 47.7-88.5 | 5.18 | yes | 6.791x | 2.007x | 0.295x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 190.0 | 203.0-376.7 | 3.97 | yes | `a100_sxm_80gb-x672-hybrid` | 75.2 | 90.6-168.1 | 3.52 | yes | 2.528x | 2.241x | 0.887x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.133x to 0.887x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 10 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | 2,097.3 | 1,358.2-2,521.0 | 6.55 | yes | `b200_sxm-x71-nvl72-tensor` | 916.0 | 2,790.2-5,179.0 | 1.39 | yes | 2.290x | 0.487x | 0.213x |
| MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 3,539.9 | 3,335.7-6,191.6 | 4.50 | yes | `b200_sxm-x87-nvl72-hybrid` | 858.9 | 2,458.1-4,562.5 | 1.48 | yes | 4.121x | 1.357x | 0.329x |
| MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,111.3 | 3,000.6-5,569.5 | 2.98 | yes | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 2,775.2-5,151.1 | 1.34 | yes | 2.401x | 1.081x | 0.450x |
| MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,111.3 | 3,000.6-5,569.5 | 2.98 | yes | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 2,775.2-5,151.1 | 1.34 | yes | 2.401x | 1.081x | 0.450x |
| MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2,111.3 | 3,000.6-5,569.5 | 2.98 | yes | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 2,775.2-5,151.1 | 1.34 | yes | 2.401x | 1.081x | 0.450x |
| MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,995.9 | 2,278.9-4,229.9 | 3.71 | yes | `b200_sxm-x1416-nvl72-hybrid` | 879.2 | 2,775.2-5,151.1 | 1.34 | yes | 2.270x | 0.821x | 0.362x |
| MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,836.2 | 1,537.9-2,854.5 | 5.06 | yes | `b200_sxm-x1416-nvl72-hybrid` | 852.9 | 2,467.7-4,580.4 | 1.47 | yes | 2.153x | 0.623x | 0.289x |
| MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,563.1 | 1,426.1-2,646.9 | 4.65 | yes | `b200_sxm-x1416-nvl72-hybrid` | 790.5 | 1,915.3-3,555.0 | 1.75 | yes | 1.977x | 0.745x | 0.377x |
| MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 574.7 | 486.9-903.8 | 5.00 | yes | `b200_sxm-x1416-nvl72-hybrid` | 556.6 | 882.7-1,638.4 | 2.67 | yes | 1.033x | 0.552x | 0.534x |
| MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 158.1 | 127.5-236.7 | 5.26 | yes | `b200_sxm-x1416-nvl72-hybrid` | 276.2 | 286.0-530.9 | 4.09 | yes | 0.573x | 0.446x | 0.779x |
| MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x49` | 40.3 | 32.1-59.6 | 5.32 | yes | `b200_sxm-x1416-nvl72-hybrid` | 108.7 | 132.4-245.8 | 3.48 | yes | 0.371x | 0.242x | 0.654x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.213x to 0.779x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | 1,970.2 | 1,071.7-1,989.1 | 7.80 | yes | `a100_sxm_80gb-x178-tensor` | 281.6 | 453.1-841.0 | 2.64 | yes | 6.997x | 2.365x | 0.338x |
| MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 3,479.3 | 3,355.0-6,227.2 | 4.40 | yes | `a100_sxm_80gb-x168-tensor` | 280.9 | 452.6-840.0 | 2.63 | yes | 12.387x | 7.413x | 0.598x |
| MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,737.8 | 2,555.7-4,743.7 | 2.88 | yes | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 424.2-787.4 | 2.51 | yes | 6.924x | 6.025x | 0.870x |
| MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,737.8 | 2,555.7-4,743.7 | 2.88 | yes | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 424.2-787.4 | 2.51 | yes | 6.924x | 6.025x | 0.870x |
| MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,737.8 | 2,555.7-4,743.7 | 2.88 | yes | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 424.2-787.4 | 2.51 | yes | 6.924x | 6.025x | 0.870x |
| MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,737.8 | 2,555.7-4,743.7 | 2.88 | yes | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 424.2-787.4 | 2.51 | yes | 6.924x | 6.025x | 0.870x |
| MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,401.1 | 1,769.4-3,284.2 | 3.36 | yes | `a100_sxm_80gb-x3805-hybrid` | 251.0 | 424.2-787.4 | 2.51 | yes | 5.583x | 4.171x | 0.747x |
| MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,024.4 | 1,095.1-2,032.7 | 3.97 | yes | `a100_sxm_80gb-x3805-hybrid` | 248.8 | 407.4-756.2 | 2.59 | yes | 4.117x | 2.688x | 0.653x |
| MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 342.6 | 342.8-636.3 | 4.24 | yes | `a100_sxm_80gb-x3805-hybrid` | 191.3 | 247.9-460.1 | 3.27 | yes | 1.791x | 1.383x | 0.772x |
| MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 90.5 | 87.7-162.8 | 4.37 | yes | `a100_sxm_80gb-x3805-hybrid` | 135.5 | 226.6-420.6 | 2.54 | yes | 0.668x | 0.387x | 0.580x |
| MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x68` | 22.9 | 22.0-40.9 | 4.40 | yes | `a100_sxm_80gb-x3805-hybrid` | 56.7 | 105.2-195.3 | 2.28 | yes | 0.403x | 0.209x | 0.519x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.338x to 0.870x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | 1,631.6 | 1,233.2-2,288.9 | 5.61 | yes | `b200_sxm-x170-nvl72-hybrid` | 808.3 | 2,522.1-4,681.4 | 1.36 | yes | 2.019x | 0.489x | 0.242x |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 3,354.6 | 2,870.3-5,327.6 | 4.96 | yes | `b200_sxm-x116-nvl72-hybrid` | 813.5 | 2,515.4-4,669.0 | 1.37 | yes | 4.124x | 1.141x | 0.277x |
| MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,291.2 | 1,215.5-2,256.2 | 4.50 | yes | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 2,220.2-4,120.9 | 1.43 | yes | 1.729x | 0.547x | 0.317x |
| MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,291.2 | 1,215.5-2,256.2 | 4.50 | yes | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 2,220.2-4,120.9 | 1.43 | yes | 1.729x | 0.547x | 0.317x |
| MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,291.2 | 1,215.5-2,256.2 | 4.50 | yes | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 2,220.2-4,120.9 | 1.43 | yes | 1.729x | 0.547x | 0.317x |
| MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,291.2 | 1,215.5-2,256.2 | 4.50 | yes | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 2,220.2-4,120.9 | 1.43 | yes | 1.729x | 0.547x | 0.317x |
| MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,291.2 | 1,215.5-2,256.2 | 4.50 | yes | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 2,220.2-4,120.9 | 1.43 | yes | 1.729x | 0.547x | 0.317x |
| MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 1,254.3 | 1,201.3-2,229.9 | 4.43 | yes | `b200_sxm-x6992-nvl72-hybrid` | 746.9 | 2,220.2-4,120.9 | 1.43 | yes | 1.679x | 0.541x | 0.322x |
| MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 552.1 | 376.7-699.2 | 6.21 | yes | `b200_sxm-x6992-nvl72-hybrid` | 627.0 | 1,454.5-2,699.7 | 1.83 | yes | 0.880x | 0.259x | 0.294x |
| MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 155.8 | 107.1-198.7 | 6.17 | yes | `b200_sxm-x6992-nvl72-hybrid` | 370.2 | 911.6-1,692.0 | 1.72 | yes | 0.421x | 0.117x | 0.279x |
| MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 39.9 | 26.9-50.0 | 6.28 | yes | `b200_sxm-x6992-nvl72-hybrid` | 142.9 | 292.6-543.1 | 2.07 | yes | 0.279x | 0.092x | 0.330x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.242x to 0.330x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x340` | 1,478.5 | 823.6-1,528.6 | 7.61 | yes | `a100_sxm_80gb-x335-hybrid` | 229.5 | 407.5-756.4 | 2.39 | yes | 6.442x | 2.021x | 0.314x |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 3,198.6 | 2,362.8-4,385.6 | 5.74 | yes | `a100_sxm_80gb-x336-hybrid` | 229.7 | 407.7-756.8 | 2.39 | yes | 13.926x | 5.795x | 0.416x |
| MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 763.8 | 868.2-1,611.4 | 3.73 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 389.6-723.2 | 2.48 | yes | 3.356x | 2.228x | 0.664x |
| MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 763.8 | 868.2-1,611.4 | 3.73 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 389.6-723.2 | 2.48 | yes | 3.356x | 2.228x | 0.664x |
| MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 763.8 | 868.2-1,611.4 | 3.73 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 389.6-723.2 | 2.48 | yes | 3.356x | 2.228x | 0.664x |
| MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 763.8 | 868.2-1,611.4 | 3.73 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 389.6-723.2 | 2.48 | yes | 3.356x | 2.228x | 0.664x |
| MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 763.8 | 868.2-1,611.4 | 3.73 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 389.6-723.2 | 2.48 | yes | 3.356x | 2.228x | 0.664x |
| MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 763.8 | 868.2-1,611.4 | 3.73 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 389.6-723.2 | 2.48 | yes | 3.356x | 2.228x | 0.664x |
| MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 323.9 | 428.2-794.8 | 3.21 | yes | `a100_sxm_80gb-x18971-hybrid` | 227.6 | 389.6-723.2 | 2.48 | yes | 1.423x | 1.099x | 0.772x |
| MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 89.9 | 123.0-228.4 | 3.10 | yes | `a100_sxm_80gb-x18971-hybrid` | 159.3 | 237.0-439.9 | 2.85 | yes | 0.564x | 0.519x | 0.920x |
| MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 22.9 | 31.1-57.6 | 3.12 | yes | `a100_sxm_80gb-x18971-hybrid` | 83.1 | 166.0-308.1 | 2.12 | yes | 0.275x | 0.187x | 0.680x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.314x to 0.920x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 3,210.4 | 1,842.7-3,420.3 | 7.39 | yes | `b200_sxm-x77-nvl72-hybrid` | 871.3 | 2,403.1-4,460.4 | 1.54 | yes | 3.685x | 0.767x | 0.208x |
| MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,195.0 | 3,472.6-6,445.7 | 5.12 | yes | `b200_sxm-x87-nvl72-hybrid` | 885.4 | 2,508.7-4,656.6 | 1.50 | yes | 4.738x | 1.384x | 0.292x |
| MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 3,210.4 | 1,842.7-3,420.3 | 7.39 | yes | `b200_sxm-x77-nvl72-hybrid` | 871.3 | 2,403.1-4,460.4 | 1.54 | yes | 3.685x | 0.767x | 0.208x |
| MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,195.0 | 3,472.6-6,445.7 | 5.12 | yes | `b200_sxm-x87-nvl72-hybrid` | 885.4 | 2,508.7-4,656.6 | 1.50 | yes | 4.738x | 1.384x | 0.292x |
| MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 3,210.4 | 1,842.7-3,420.3 | 7.39 | yes | `b200_sxm-x77-nvl72-hybrid` | 832.7 | 2,042.9-3,791.9 | 1.73 | yes | 3.855x | 0.902x | 0.234x |
| MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,195.0 | 3,472.6-6,445.7 | 5.12 | yes | `b200_sxm-x87-nvl72-hybrid` | 849.4 | 2,144.6-3,980.7 | 1.68 | yes | 4.939x | 1.619x | 0.328x |
| MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 3,210.4 | 1,842.7-3,420.3 | 7.39 | yes | `b200_sxm-x77-nvl72-hybrid` | 766.5 | 1,606.4-2,981.6 | 2.02 | yes | 4.188x | 1.147x | 0.274x |
| MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,195.0 | 3,472.6-6,445.7 | 5.12 | yes | `b200_sxm-x87-nvl72-hybrid` | 786.8 | 1,695.5-3,147.0 | 1.97 | yes | 5.332x | 2.048x | 0.384x |
| MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 3,210.4 | 1,842.7-3,420.3 | 7.39 | yes | `b200_sxm-x77-nvl72-hybrid` | 666.0 | 1,202.6-2,232.2 | 2.35 | yes | 4.821x | 1.532x | 0.318x |
| MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 4,157.2 | 3,474.4-6,449.0 | 5.07 | yes | `b200_sxm-x173-nvl72-hybrid` | 794.3 | 1,697.9-3,151.4 | 1.98 | yes | 5.234x | 2.046x | 0.391x |
| MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 3,152.0 | 1,879.1-3,487.9 | 7.11 | yes | `b200_sxm-x150-nvl72-hybrid` | 666.1 | 1,164.9-2,162.2 | 2.42 | yes | 4.732x | 1.613x | 0.341x |
| MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,116.5 | 3,502.1-6,500.3 | 4.98 | yes | `b200_sxm-x347-nvl72-hybrid` | 793.6 | 1,644.4-3,052.2 | 2.05 | yes | 5.187x | 2.130x | 0.411x |
| MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,000.5 | 1,126.7-2,091.3 | 11.29 | **no** | `b200_sxm-x173-nvl72-hybrid` | 564.3 | 801.9-1,488.4 | 2.98 | yes | 5.318x | 1.405x | 0.264x |
| MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,682.8 | 2,304.6-4,277.7 | 6.78 | yes | `b200_sxm-x347-nvl72-hybrid` | 688.7 | 1,125.1-2,088.3 | 2.60 | yes | 5.348x | 2.048x | 0.383x |
| MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 2,326.9 | 528.7-981.3 | 18.66 | **no** | `b200_sxm-x200-nvl72-hybrid` | 349.7 | 282.0-523.4 | 5.26 | yes | 6.654x | 1.875x | 0.282x |
| MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,256.5 | 1,046.1-1,941.8 | 9.15 | **no** | `b200_sxm-x347-nvl72-hybrid` | 430.4 | 414.9-770.1 | 4.40 | yes | 5.243x | 2.521x | 0.481x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x392-romfill` | 844.7 | 173.3-321.6 | 20.67 | **no** | `b200_sxm-x200-nvl72-hybrid` | 191.9 | 97.4-180.7 | 8.36 | **no** | 4.403x | 1.780x | 0.404x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 791.9 | 279.9-519.5 | 12.00 | **no** | `b200_sxm-x347-nvl72-hybrid` | 240.0 | 138.5-257.1 | 7.35 | yes | 3.299x | 2.020x | 0.612x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 318.3 | 79.8-148.1 | 16.91 | **no** | `b200_sxm-x200-nvl72-hybrid` | 96.9 | 41.1-76.3 | 10.00 | **no** | 3.284x | 1.943x | 0.591x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 215.4 | 96.4-179.0 | 9.47 | **no** | `b200_sxm-x347-nvl72-hybrid` | 127.4 | 61.7-114.4 | 8.76 | **no** | 1.691x | 1.564x | 0.925x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.208x to 0.925x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 13 of 20 ROM rows and 17 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 3,007.4 | 1,440.1-2,673.1 | 8.85 | **no** | `a100_sxm_80gb-x208-tensor` | 285.7 | 456.9-848.1 | 2.65 | yes | 10.526x | 3.152x | 0.299x |
| MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,636.1 | 3,837.2-7,122.3 | 4.02 | yes | `a100_sxm_80gb-x280-tensor` | 287.9 | 459.5-852.9 | 2.66 | yes | 12.628x | 8.350x | 0.661x |
| MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 3,007.4 | 1,440.1-2,673.1 | 8.85 | **no** | `a100_sxm_80gb-x208-hybrid` | 260.9 | 426.7-792.0 | 2.59 | yes | 11.527x | 3.375x | 0.293x |
| MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,636.1 | 3,837.2-7,122.3 | 4.02 | yes | `a100_sxm_80gb-x280-hybrid` | 263.0 | 433.3-804.3 | 2.57 | yes | 13.825x | 8.856x | 0.641x |
| MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 3,007.4 | 1,440.1-2,673.1 | 8.85 | **no** | `a100_sxm_80gb-x208-hybrid` | 260.9 | 426.7-792.0 | 2.59 | yes | 11.527x | 3.375x | 0.293x |
| MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,636.1 | 3,837.2-7,122.3 | 4.02 | yes | `a100_sxm_80gb-x280-hybrid` | 263.0 | 433.3-804.3 | 2.57 | yes | 13.825x | 8.856x | 0.641x |
| MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 3,007.4 | 1,440.1-2,673.1 | 8.85 | **no** | `a100_sxm_80gb-x208-hybrid` | 236.8 | 378.7-702.9 | 2.65 | yes | 12.699x | 3.803x | 0.299x |
| MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 3,636.1 | 3,837.2-7,122.3 | 4.02 | yes | `a100_sxm_80gb-x280-hybrid` | 247.0 | 321.4-596.6 | 3.26 | yes | 14.719x | 11.937x | 0.811x |
| MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 3,007.4 | 1,440.1-2,673.1 | 8.85 | **no** | `a100_sxm_80gb-x208-hybrid` | 216.5 | 369.3-685.5 | 2.48 | yes | 13.894x | 3.899x | 0.281x |
| MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,611.2 | 2,750.0-5,104.4 | 5.57 | yes | `a100_sxm_80gb-x672-hybrid` | 252.2 | 348.4-646.6 | 3.07 | yes | 14.317x | 7.894x | 0.551x |
| MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 2,958.5 | 1,469.2-2,727.0 | 8.54 | **no** | `a100_sxm_80gb-x249-hybrid` | 211.9 | 367.4-681.9 | 2.45 | yes | 13.963x | 3.999x | 0.286x |
| MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,256.7 | 1,772.2-3,289.5 | 7.79 | yes | `a100_sxm_80gb-x672-hybrid` | 228.4 | 330.1-612.6 | 2.93 | yes | 14.261x | 5.370x | 0.377x |
| MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 2,762.3 | 1,244.2-2,309.3 | 9.41 | **no** | `a100_sxm_80gb-x373-hybrid` | 198.9 | 337.3-626.1 | 2.50 | yes | 13.884x | 3.689x | 0.266x |
| MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,723.8 | 1,573.5-2,920.6 | 7.34 | yes | `a100_sxm_80gb-x672-hybrid` | 211.4 | 418.2-776.2 | 2.14 | yes | 12.886x | 3.763x | 0.292x |
| MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 1,884.0 | 382.6-710.2 | 20.88 | **no** | `a100_sxm_80gb-x373-hybrid` | 116.4 | 163.8-304.1 | 3.01 | yes | 16.187x | 2.335x | 0.144x |
| MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,182.9 | 492.6-914.3 | 10.18 | **no** | `a100_sxm_80gb-x672-hybrid` | 152.1 | 209.9-389.6 | 3.07 | yes | 7.777x | 2.347x | 0.302x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 731.2 | 163.3-303.2 | 18.98 | **no** | `a100_sxm_80gb-x373-hybrid` | 49.0 | 89.6-166.2 | 2.32 | yes | 14.907x | 1.824x | 0.122x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 345.9 | 127.2-236.2 | 11.53 | **no** | `a100_sxm_80gb-x672-hybrid` | 71.5 | 119.9-222.6 | 2.53 | yes | 4.840x | 1.061x | 0.219x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 230.6 | 49.2-91.3 | 19.87 | **no** | `a100_sxm_80gb-x373-hybrid` | 22.4 | 23.3-43.3 | 4.07 | yes | 10.293x | 2.109x | 0.205x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 89.5 | 78.2-145.2 | 4.85 | yes | `a100_sxm_80gb-x672-hybrid` | 29.5 | 37.8-70.2 | 3.30 | yes | 3.040x | 2.068x | 0.680x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.122x to 0.811x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-qwen3-8b-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340-romfill` | 2,695.1 | 1,442.0-2,676.6 | 7.92 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,262.0 | 4,693.0-8,710.8 | 1.14 | yes | 2.135x | 0.307x | 0.144x |
| Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 8,234.2 | 10,570.7-19,620.5 | 3.30 | yes | `b200_sxm-x58-nvl72-tensor` | 1,276.4 | 4,777.1-8,867.0 | 1.13 | yes | 6.451x | 2.213x | 0.343x |

**Does the ratio compress?** Of 2 class rows in this study, 2 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.144x to 0.343x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 1 of 2 ROM rows and 2 of 2 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-qwen3-8b-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x308-romfill` | 2,733.5 | 1,427.2-2,649.1 | 8.12 | **no** | `a100_sxm_80gb-x304-tensor` | 615.8 | 1,134.9-2,106.5 | 2.30 | yes | 4.439x | 1.258x | 0.283x |
| Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 8,190.8 | 8,189.3-15,200.4 | 4.24 | yes | `a100_sxm_80gb-x112-tensor` | 459.8 | 1,004.8-1,865.1 | 1.94 | yes | 17.813x | 8.150x | 0.458x |

**Does the ratio compress?** Of 2 class rows in this study, 2 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.283x to 0.458x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 1 of 2 ROM rows and 2 of 2 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-qwen3-8b-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x60-romfill` | 4,696.5 | 2,778.7-5,157.6 | 7.17 | yes | `b200_sxm-x31-nvl72-tensor` | 1,745.3 | 6,201.4-11,510.6 | 1.19 | yes | 2.691x | 0.448x | 0.167x |
| Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 9,134.8 | 13,001.9-24,133.3 | 2.98 | yes | `b200_sxm-x29-nvl72-tensor` | 1,699.9 | 6,057.0-11,242.6 | 1.19 | yes | 5.374x | 2.147x | 0.399x |
| Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,597.2 | 7,215.7-13,393.3 | 1.53 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | 5,700.5-10,580.8 | 1.41 | yes | 1.365x | 1.266x | 0.927x |
| Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,597.2 | 7,215.7-13,393.3 | 1.53 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | 5,700.5-10,580.8 | 1.41 | yes | 1.365x | 1.266x | 0.927x |
| Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,597.2 | 7,215.7-13,393.3 | 1.53 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | 5,700.5-10,580.8 | 1.41 | yes | 1.365x | 1.266x | 0.927x |
| Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,597.2 | 7,215.7-13,393.3 | 1.53 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | 5,700.5-10,580.8 | 1.41 | yes | 1.365x | 1.266x | 0.927x |
| Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 2,597.2 | 7,215.7-13,393.3 | 1.53 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,902.3 | 5,700.5-10,580.8 | 1.41 | yes | 1.365x | 1.266x | 0.927x |
| Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1,746.9 | 4,578.3-8,498.0 | 1.62 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,865.9 | 5,464.8-10,143.4 | 1.45 | yes | 0.936x | 0.838x | 0.895x |
| Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 600.7 | 2,284.9-4,241.0 | 1.11 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,280.5 | 4,009.3-7,441.8 | 1.35 | yes | 0.469x | 0.570x | 1.215x |
| Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 158.3 | 646.5-1,199.9 | 1.04 | yes | `b200_sxm-x4016-nvl72-hybrid` | 593.6 | 1,646.2-3,055.5 | 1.53 | yes | 0.267x | 0.393x | 1.472x |
| Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 40.0 | 166.4-308.9 | 1.02 | yes | `b200_sxm-x4016-nvl72-hybrid` | 190.4 | 646.3-1,199.7 | 1.25 | yes | 0.210x | 0.258x | 1.227x |

**Does the ratio compress?** Of 11 class rows in this study, 8 move the ROM-versus-GPU ratio DOWN under speculation and 3 move it UP. The movement spans 0.167x to 1.472x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-qwen3-8b-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 4,687.2 | 3,881.9-7,205.3 | 5.12 | yes | `a100_sxm_80gb-x56-tensor` | 564.5 | 1,142.9-2,121.4 | 2.09 | yes | 8.304x | 3.396x | 0.409x |
| Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 9,194.4 | 12,256.1-22,749.0 | 3.18 | yes | `a100_sxm_80gb-x56-tensor` | 564.5 | 1,142.9-2,121.4 | 2.09 | yes | 16.289x | 10.723x | 0.658x |
| Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196-romfill` | 1,731.8 | 3,915.1-7,267.0 | 1.88 | yes | `a100_sxm_80gb-x10969-tensor` | 584.4 | 720.3-1,336.9 | 3.44 | yes | 2.963x | 5.436x | 1.834x |
| Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 1,626.8 | 2,756.0-5,115.4 | 2.50 | yes | `a100_sxm_80gb-x10969-hybrid` | 555.9 | 1,064.1-1,975.1 | 2.21 | yes | 2.927x | 2.590x | 0.885x |
| Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,447.5 | 4,739.9-8,797.8 | 1.29 | yes | `a100_sxm_80gb-x10969-hybrid` | 555.9 | 1,064.1-1,975.1 | 2.21 | yes | 2.604x | 4.454x | 1.711x |
| Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,447.5 | 4,739.9-8,797.8 | 1.29 | yes | `a100_sxm_80gb-x10969-hybrid` | 555.9 | 1,064.1-1,975.1 | 2.21 | yes | 2.604x | 4.454x | 1.711x |
| Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,447.5 | 4,739.9-8,797.8 | 1.29 | yes | `a100_sxm_80gb-x10969-hybrid` | 555.9 | 1,064.1-1,975.1 | 2.21 | yes | 2.604x | 4.454x | 1.711x |
| Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,163.7 | 3,791.0-7,036.6 | 1.30 | yes | `a100_sxm_80gb-x10969-hybrid` | 555.9 | 1,064.1-1,975.1 | 2.21 | yes | 2.093x | 3.563x | 1.702x |
| Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 353.7 | 1,381.7-2,564.6 | 1.09 | yes | `a100_sxm_80gb-x10969-hybrid` | 502.9 | 824.8-1,530.9 | 2.59 | yes | 0.703x | 1.675x | 2.382x |
| Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 91.4 | 376.7-699.2 | 1.03 | yes | `a100_sxm_80gb-x10969-hybrid` | 285.1 | 470.8-873.8 | 2.57 | yes | 0.321x | 0.800x | 2.495x |
| Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 23.0 | 96.4-178.9 | 1.01 | yes | `a100_sxm_80gb-x10969-hybrid` | 117.9 | 432.1-802.1 | 1.16 | yes | 0.195x | 0.223x | 1.143x |

**Does the ratio compress?** Of 11 class rows in this study, 3 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.409x to 2.495x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 2,488.0 | 696.7-1,293.2 | 15.14 | **no** | `b200_sxm-x58-nvl72-tensor` | 767.6 | 827.2-1,535.3 | 3.93 | yes | 3.241x | 0.842x | 0.260x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3,785.9 | 3,557.5-6,603.2 | 4.51 | yes | `b200_sxm-x58-nvl72-tensor` | 767.6 | 827.2-1,535.3 | 3.93 | yes | 4.932x | 4.301x | 0.872x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,959.9 | 768.5-1,426.5 | 10.81 | **no** | `b200_sxm-x173-nvl72-hybrid` | 762.6 | 822.0-1,525.7 | 3.93 | yes | 2.570x | 0.935x | 0.364x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,758.2 | 4,577.9-8,497.2 | 2.55 | yes | `b200_sxm-x953-nvl72-hybrid` | 747.6 | 798.2-1,481.5 | 3.97 | yes | 3.689x | 5.736x | 1.555x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,959.9 | 768.5-1,426.5 | 10.81 | **no** | `b200_sxm-x173-nvl72-hybrid` | 747.5 | 827.2-1,535.4 | 3.83 | yes | 2.622x | 0.929x | 0.354x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,758.2 | 4,577.9-8,497.2 | 2.55 | yes | `b200_sxm-x953-nvl72-hybrid` | 747.6 | 798.2-1,481.5 | 3.97 | yes | 3.689x | 5.736x | 1.555x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,959.9 | 768.5-1,426.5 | 10.81 | **no** | `b200_sxm-x173-nvl72-hybrid` | 722.3 | 828.0-1,536.9 | 3.70 | yes | 2.713x | 0.928x | 0.342x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,758.2 | 4,577.9-8,497.2 | 2.55 | yes | `b200_sxm-x953-nvl72-hybrid` | 747.6 | 798.2-1,481.5 | 3.97 | yes | 3.689x | 5.736x | 1.555x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,959.9 | 768.5-1,426.5 | 10.81 | **no** | `b200_sxm-x173-nvl72-hybrid` | 720.6 | 836.3-1,552.3 | 3.65 | yes | 2.720x | 0.919x | 0.338x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,758.2 | 4,577.9-8,497.2 | 2.55 | yes | `b200_sxm-x953-nvl72-hybrid` | 737.6 | 759.9-1,410.6 | 4.12 | yes | 3.739x | 6.024x | 1.611x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,959.9 | 768.5-1,426.5 | 10.81 | **no** | `b200_sxm-x173-nvl72-hybrid` | 663.3 | 630.6-1,170.5 | 4.46 | yes | 2.955x | 1.219x | 0.412x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,758.2 | 4,577.9-8,497.2 | 2.55 | yes | `b200_sxm-x953-nvl72-hybrid` | 717.0 | 765.3-1,420.4 | 3.97 | yes | 3.847x | 5.982x | 1.555x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,959.9 | 768.5-1,426.5 | 10.81 | **no** | `b200_sxm-x173-nvl72-hybrid` | 570.4 | 623.3-1,156.9 | 3.88 | yes | 3.436x | 1.233x | 0.359x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2,553.8 | 3,754.4-6,968.7 | 2.88 | yes | `b200_sxm-x953-nvl72-hybrid` | 707.0 | 850.3-1,578.2 | 3.53 | yes | 3.612x | 4.416x | 1.222x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349-romfill` | 1,403.7 | 420.6-780.6 | 14.15 | **no** | `b200_sxm-x178-pipeline` | 375.3 | 336.6-624.7 | 4.73 | yes | 3.741x | 1.250x | 0.334x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,694.8 | 1,905.7-3,537.3 | 3.77 | yes | `b200_sxm-x953-nvl72-hybrid` | 616.5 | 822.6-1,526.9 | 3.18 | yes | 2.749x | 2.317x | 0.843x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 576.3 | 158.6-294.3 | 15.41 | **no** | `b200_sxm-x178-pipeline` | 173.4 | 167.5-310.9 | 4.39 | yes | 3.323x | 0.947x | 0.285x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 634.8 | 333.0-618.0 | 8.08 | **no** | `b200_sxm-x953-pipeline` | 417.8 | 409.8-760.6 | 4.32 | yes | 1.520x | 0.813x | 0.535x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 144.5 | 48.8-90.6 | 12.55 | **no** | `b200_sxm-x178-pipeline` | 58.3 | 122.8-227.9 | 2.02 | yes | 2.477x | 0.398x | 0.161x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 175.7 | 89.5-166.1 | 8.33 | **no** | `b200_sxm-x953-pipeline` | 210.8 | 185.4-344.2 | 4.82 | yes | 0.834x | 0.482x | 0.579x |

**Does the ratio compress?** Of 20 class rows in this study, 14 move the ROM-versus-GPU ratio DOWN under speculation and 6 move it UP. The movement spans 0.161x to 1.611x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 3,778.7 | 1,643.3-3,050.2 | 9.75 | **no** | `b200_sxm-x26-nvl72-tensor` | 864.3 | 2,138.2-3,968.8 | 1.71 | yes | 4.372x | 0.769x | 0.176x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,234.4 | 3,184.4-5,910.7 | 5.64 | yes | `b200_sxm-x58-nvl72-tensor` | 885.0 | 2,215.2-4,111.8 | 1.69 | yes | 4.785x | 1.438x | 0.300x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 3,778.7 | 1,643.3-3,050.2 | 9.75 | **no** | `b200_sxm-x26-nvl72-tensor` | 831.0 | 1,616.3-3,000.0 | 2.18 | yes | 4.547x | 1.017x | 0.224x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,234.4 | 3,184.4-5,910.7 | 5.64 | yes | `b200_sxm-x58-nvl72-tensor` | 854.2 | 1,649.9-3,062.5 | 2.20 | yes | 4.957x | 1.930x | 0.389x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 3,778.7 | 1,643.3-3,050.2 | 9.75 | **no** | `b200_sxm-x26-hybrid` | 814.8 | 1,674.3-3,107.7 | 2.06 | yes | 4.638x | 0.982x | 0.212x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,234.4 | 3,184.4-5,910.7 | 5.64 | yes | `b200_sxm-x58-hybrid` | 823.4 | 1,768.7-3,283.0 | 1.97 | yes | 5.143x | 1.800x | 0.350x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 3,778.7 | 1,643.3-3,050.2 | 9.75 | **no** | `b200_sxm-x26-hybrid` | 755.4 | 1,255.0-2,329.4 | 2.55 | yes | 5.002x | 1.309x | 0.262x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,234.4 | 3,184.4-5,910.7 | 5.64 | yes | `b200_sxm-x58-hybrid` | 823.4 | 1,768.7-3,283.0 | 1.97 | yes | 5.143x | 1.800x | 0.350x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 3,778.7 | 1,643.3-3,050.2 | 9.75 | **no** | `b200_sxm-x26-hybrid` | 661.5 | 871.9-1,618.4 | 3.22 | yes | 5.712x | 1.885x | 0.330x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,234.4 | 3,184.4-5,910.7 | 5.64 | yes | `b200_sxm-x58-hybrid` | 765.5 | 1,326.3-2,461.9 | 2.45 | yes | 5.532x | 2.401x | 0.434x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x116-romfill` | 3,689.8 | 1,635.4-3,035.5 | 9.57 | **no** | `b200_sxm-x59-hybrid` | 676.1 | 915.1-1,698.5 | 3.13 | yes | 5.458x | 1.787x | 0.327x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,222.5 | 3,214.1-5,965.7 | 5.57 | yes | `b200_sxm-x116-nvl72-hybrid` | 770.8 | 1,414.3-2,625.2 | 2.31 | yes | 5.478x | 2.273x | 0.415x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 3,689.8 | 1,635.4-3,035.5 | 9.57 | **no** | `b200_sxm-x87-nvl72-hybrid` | 632.7 | 805.4-1,494.9 | 3.33 | yes | 5.832x | 2.030x | 0.348x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,222.5 | 3,214.1-5,965.7 | 5.57 | yes | `b200_sxm-x231-nvl72-hybrid` | 758.6 | 1,396.5-2,592.1 | 2.30 | yes | 5.566x | 2.301x | 0.413x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,169.5 | 1,278.4-2,372.8 | 10.51 | **no** | `b200_sxm-x173-nvl72-hybrid` | 489.5 | 494.7-918.3 | 4.20 | yes | 6.474x | 2.584x | 0.399x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,889.5 | 1,864.9-3,461.6 | 8.84 | **no** | `b200_sxm-x347-nvl72-hybrid` | 609.6 | 791.8-1,469.8 | 3.26 | yes | 6.380x | 2.355x | 0.369x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,612.8 | 426.3-791.2 | 16.04 | **no** | `b200_sxm-x173-nvl72-hybrid` | 251.0 | 273.3-507.3 | 3.89 | yes | 6.424x | 1.560x | 0.243x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,697.5 | 786.8-1,460.4 | 14.54 | **no** | `b200_sxm-x347-nvl72-hybrid` | 360.7 | 448.7-832.9 | 3.41 | yes | 7.478x | 1.753x | 0.234x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 498.2 | 126.2-234.3 | 16.73 | **no** | `b200_sxm-x173-nvl72-hybrid` | 121.3 | 87.3-162.0 | 5.90 | yes | 4.106x | 1.447x | 0.352x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,013.1 | 268.2-497.9 | 16.01 | **no** | `b200_sxm-x347-nvl72-hybrid` | 171.1 | 157.6-292.5 | 4.60 | yes | 5.922x | 1.702x | 0.287x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.176x to 0.434x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 3,818.2 | 1,732.6-3,216.0 | 9.34 | **no** | `b200_sxm-x30-nvl72-tensor` | 872.8 | 2,258.6-4,192.3 | 1.64 | yes | 4.374x | 0.767x | 0.175x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,262.0 | 3,364.2-6,244.4 | 5.37 | yes | `b200_sxm-x58-nvl72-tensor` | 888.4 | 2,313.9-4,294.9 | 1.63 | yes | 4.797x | 1.454x | 0.303x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 3,818.2 | 1,732.6-3,216.0 | 9.34 | **no** | `b200_sxm-x30-nvl72-tensor` | 843.3 | 1,743.1-3,235.5 | 2.05 | yes | 4.528x | 0.994x | 0.220x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,262.0 | 3,364.2-6,244.4 | 5.37 | yes | `b200_sxm-x58-nvl72-tensor` | 860.7 | 1,761.8-3,270.2 | 2.07 | yes | 4.952x | 1.909x | 0.386x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 3,818.2 | 1,732.6-3,216.0 | 9.34 | **no** | `b200_sxm-x30-hybrid` | 838.6 | 1,829.3-3,395.4 | 1.94 | yes | 4.553x | 0.947x | 0.208x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,262.0 | 3,364.2-6,244.4 | 5.37 | yes | `b200_sxm-x58-hybrid` | 826.5 | 1,824.8-3,387.0 | 1.92 | yes | 5.157x | 1.844x | 0.358x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 3,818.2 | 1,732.6-3,216.0 | 9.34 | **no** | `b200_sxm-x30-hybrid` | 784.4 | 1,398.7-2,596.2 | 2.38 | yes | 4.868x | 1.239x | 0.254x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,262.0 | 3,364.2-6,244.4 | 5.37 | yes | `b200_sxm-x58-hybrid` | 826.5 | 1,824.8-3,387.0 | 1.92 | yes | 5.157x | 1.844x | 0.358x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 3,818.2 | 1,732.6-3,216.0 | 9.34 | **no** | `b200_sxm-x30-hybrid` | 696.5 | 987.0-1,832.0 | 2.99 | yes | 5.482x | 1.755x | 0.320x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,262.0 | 3,364.2-6,244.4 | 5.37 | yes | `b200_sxm-x58-hybrid` | 770.9 | 1,390.4-2,580.8 | 2.35 | yes | 5.528x | 2.420x | 0.438x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x116-romfill` | 3,754.2 | 1,709.9-3,173.9 | 9.31 | **no** | `b200_sxm-x59-hybrid` | 684.6 | 977.1-1,813.7 | 2.97 | yes | 5.484x | 1.750x | 0.319x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,249.6 | 3,401.8-6,314.2 | 5.30 | yes | `b200_sxm-x116-nvl72-hybrid` | 776.6 | 1,492.4-2,770.1 | 2.21 | yes | 5.472x | 2.279x | 0.417x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 3,754.2 | 1,709.9-3,173.9 | 9.31 | **no** | `b200_sxm-x87-nvl72-hybrid` | 643.4 | 876.6-1,627.0 | 3.11 | yes | 5.835x | 1.951x | 0.334x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,249.6 | 3,401.8-6,314.2 | 5.30 | yes | `b200_sxm-x231-nvl72-hybrid` | 764.4 | 1,475.3-2,738.3 | 2.20 | yes | 5.559x | 2.306x | 0.415x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 3,279.3 | 948.0-1,759.6 | 14.67 | **no** | `b200_sxm-x173-nvl72-hybrid` | 502.6 | 549.5-1,019.9 | 3.88 | yes | 6.525x | 1.725x | 0.264x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,015.0 | 1,971.8-3,659.8 | 8.63 | **no** | `b200_sxm-x347-nvl72-hybrid` | 619.6 | 860.5-1,597.1 | 3.05 | yes | 6.480x | 2.292x | 0.354x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,724.0 | 457.3-848.8 | 15.99 | **no** | `b200_sxm-x173-nvl72-hybrid` | 258.8 | 178.4-331.2 | 6.15 | yes | 6.661x | 2.563x | 0.385x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,867.5 | 836.5-1,552.7 | 14.53 | **no** | `b200_sxm-x347-nvl72-hybrid` | 362.9 | 504.9-937.1 | 3.05 | yes | 7.901x | 1.657x | 0.210x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 541.4 | 137.4-255.0 | 16.71 | **no** | `b200_sxm-x173-nvl72-hybrid` | 127.9 | 97.9-181.7 | 5.54 | yes | 4.235x | 1.403x | 0.331x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,113.7 | 293.6-545.0 | 16.08 | **no** | `b200_sxm-x347-nvl72-hybrid` | 175.1 | 174.7-324.3 | 4.25 | yes | 6.359x | 1.681x | 0.264x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.175x to 0.438x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,566.6 | 607.5-1,127.6 | 10.93 | **no** | `b200_sxm-x157-nvl72-hybrid` | 570.7 | 995.5-1,847.9 | 2.43 | yes | 2.745x | 0.610x | 0.222x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 2,130.2 | 2,149.7-3,990.1 | 4.20 | yes | `b200_sxm-x116-nvl72-hybrid` | 574.9 | 1,004.0-1,863.5 | 2.43 | yes | 3.705x | 2.141x | 0.578x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,566.6 | 607.5-1,127.6 | 10.93 | **no** | `b200_sxm-x157-nvl72-hybrid` | 570.7 | 995.5-1,847.9 | 2.43 | yes | 2.745x | 0.610x | 0.222x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,074.9 | 2,141.8-3,975.4 | 4.11 | yes | `b200_sxm-x289-nvl72-hybrid` | 571.7 | 999.0-1,854.3 | 2.43 | yes | 3.629x | 2.144x | 0.591x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,566.6 | 607.5-1,127.6 | 10.93 | **no** | `b200_sxm-x157-nvl72-hybrid` | 554.1 | 834.9-1,549.6 | 2.81 | yes | 2.827x | 0.728x | 0.257x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,074.9 | 2,141.8-3,975.4 | 4.11 | yes | `b200_sxm-x289-nvl72-hybrid` | 571.7 | 999.0-1,854.3 | 2.43 | yes | 3.629x | 2.144x | 0.591x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,566.6 | 607.5-1,127.6 | 10.93 | **no** | `b200_sxm-x157-nvl72-hybrid` | 547.6 | 945.8-1,755.6 | 2.45 | yes | 2.861x | 0.642x | 0.225x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,074.9 | 2,141.8-3,975.4 | 4.11 | yes | `b200_sxm-x289-nvl72-hybrid` | 545.3 | 985.4-1,829.0 | 2.35 | yes | 3.805x | 2.174x | 0.571x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,566.6 | 607.5-1,127.6 | 10.93 | **no** | `b200_sxm-x157-nvl72-hybrid` | 511.2 | 711.9-1,321.3 | 3.04 | yes | 3.065x | 0.853x | 0.278x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,074.9 | 2,141.8-3,975.4 | 4.11 | yes | `b200_sxm-x289-nvl72-hybrid` | 539.9 | 952.2-1,767.4 | 2.40 | yes | 3.843x | 2.249x | 0.585x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,566.6 | 607.5-1,127.6 | 10.93 | **no** | `b200_sxm-x157-nvl72-hybrid` | 434.7 | 441.1-818.8 | 4.18 | yes | 3.603x | 1.377x | 0.382x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2,074.9 | 2,141.8-3,975.4 | 4.11 | yes | `b200_sxm-x289-nvl72-hybrid` | 498.8 | 688.8-1,278.5 | 3.07 | yes | 4.159x | 3.110x | 0.748x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,566.6 | 607.5-1,127.6 | 10.93 | **no** | `b200_sxm-x157-nvl72-hybrid` | 350.1 | 387.6-719.4 | 3.83 | yes | 4.475x | 1.567x | 0.350x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,994.5 | 1,402.3-2,602.9 | 6.03 | yes | `b200_sxm-x289-nvl72-hybrid` | 420.7 | 420.9-781.3 | 4.24 | yes | 4.740x | 3.332x | 0.703x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,286.4 | 297.9-553.0 | 18.31 | **no** | `b200_sxm-x173-nvl72-hybrid` | 188.3 | 149.3-277.0 | 5.35 | yes | 6.833x | 1.996x | 0.292x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,478.0 | 629.8-1,169.0 | 9.95 | **no** | `b200_sxm-x347-nvl72-hybrid` | 269.8 | 252.8-469.2 | 4.53 | yes | 5.477x | 2.492x | 0.455x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 524.8 | 104.2-193.5 | 21.35 | **no** | `b200_sxm-x173-nvl72-hybrid` | 74.5 | 73.9-137.2 | 4.27 | yes | 7.046x | 1.410x | 0.200x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 671.4 | 168.9-313.5 | 16.85 | **no** | `b200_sxm-x347-nvl72-hybrid` | 121.6 | 124.6-231.2 | 4.14 | yes | 5.523x | 1.356x | 0.246x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 148.6 | 34.5-64.1 | 18.25 | **no** | `b200_sxm-x173-nvl72-hybrid` | 29.4 | 23.9-44.4 | 5.21 | yes | 5.056x | 1.445x | 0.286x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 198.8 | 70.7-131.2 | 11.93 | **no** | `b200_sxm-x347-nvl72-hybrid` | 45.4 | 42.2-78.3 | 4.56 | yes | 4.380x | 1.676x | 0.383x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.200x to 0.748x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,673.3 | 715.2-1,327.5 | 9.92 | **no** | `b200_sxm-x137-nvl72-hybrid` | 594.5 | 1,254.9-2,329.3 | 2.01 | yes | 2.814x | 0.570x | 0.202x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,250.0 | 2,496.5-4,633.9 | 3.82 | yes | `b200_sxm-x144-nvl72-hybrid` | 595.8 | 1,260.0-2,338.7 | 2.01 | yes | 3.776x | 1.981x | 0.525x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,673.3 | 715.2-1,327.5 | 9.92 | **no** | `b200_sxm-x137-nvl72-hybrid` | 594.5 | 1,254.9-2,329.3 | 2.01 | yes | 2.814x | 0.570x | 0.202x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,250.0 | 2,496.5-4,633.9 | 3.82 | yes | `b200_sxm-x144-nvl72-hybrid` | 595.8 | 1,260.0-2,338.7 | 2.01 | yes | 3.776x | 1.981x | 0.525x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,673.3 | 715.2-1,327.5 | 9.92 | **no** | `b200_sxm-x137-nvl72-hybrid` | 568.7 | 1,052.8-1,954.2 | 2.29 | yes | 2.943x | 0.679x | 0.231x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,250.0 | 2,496.5-4,633.9 | 3.82 | yes | `b200_sxm-x144-nvl72-hybrid` | 570.6 | 1,059.2-1,966.0 | 2.28 | yes | 3.943x | 2.357x | 0.598x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,673.3 | 715.2-1,327.5 | 9.92 | **no** | `b200_sxm-x137-nvl72-hybrid` | 559.1 | 1,133.3-2,103.5 | 2.09 | yes | 2.993x | 0.631x | 0.211x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,250.0 | 2,496.5-4,633.9 | 3.82 | yes | `b200_sxm-x144-nvl72-hybrid` | 564.3 | 1,152.3-2,138.8 | 2.08 | yes | 3.987x | 2.167x | 0.543x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,673.3 | 715.2-1,327.5 | 9.92 | **no** | `b200_sxm-x137-nvl72-hybrid` | 520.0 | 843.1-1,564.9 | 2.62 | yes | 3.218x | 0.848x | 0.264x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,250.0 | 2,496.5-4,633.9 | 3.82 | yes | `b200_sxm-x144-nvl72-hybrid` | 525.6 | 856.9-1,590.5 | 2.60 | yes | 4.281x | 2.913x | 0.681x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,673.3 | 715.2-1,327.5 | 9.92 | **no** | `b200_sxm-x137-nvl72-hybrid` | 449.0 | 553.0-1,026.5 | 3.44 | yes | 3.727x | 1.293x | 0.347x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,229.0 | 2,484.9-4,612.3 | 3.80 | yes | `b200_sxm-x347-nvl72-hybrid` | 532.6 | 964.2-1,789.7 | 2.34 | yes | 4.186x | 2.577x | 0.616x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,673.3 | 715.2-1,327.5 | 9.92 | **no** | `b200_sxm-x137-nvl72-hybrid` | 354.7 | 331.3-614.9 | 4.54 | yes | 4.718x | 2.159x | 0.458x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,185.5 | 1,570.9-2,915.9 | 5.90 | yes | `b200_sxm-x347-nvl72-hybrid` | 469.9 | 634.5-1,177.8 | 3.14 | yes | 4.651x | 2.476x | 0.532x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,367.7 | 336.0-623.6 | 17.26 | **no** | `b200_sxm-x173-nvl72-hybrid` | 203.7 | 198.4-368.2 | 4.35 | yes | 6.714x | 1.694x | 0.252x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,824.8 | 737.4-1,368.7 | 10.49 | **no** | `b200_sxm-x347-nvl72-hybrid` | 287.6 | 300.9-558.5 | 4.05 | yes | 6.344x | 2.451x | 0.386x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 654.8 | 123.8-229.9 | 22.42 | **no** | `b200_sxm-x173-nvl72-hybrid` | 82.5 | 66.1-122.7 | 5.29 | yes | 7.934x | 1.873x | 0.236x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,015.2 | 197.1-365.8 | 21.84 | **no** | `b200_sxm-x347-nvl72-hybrid` | 129.4 | 114.4-212.3 | 4.80 | yes | 7.847x | 1.723x | 0.220x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 192.0 | 43.8-81.2 | 18.61 | **no** | `b200_sxm-x173-nvl72-hybrid` | 37.5 | 19.2-35.6 | 8.30 | **no** | 5.114x | 2.280x | 0.446x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 396.7 | 124.8-231.7 | 13.47 | **no** | `b200_sxm-x347-nvl72-hybrid` | 53.4 | 34.9-64.8 | 6.49 | yes | 7.431x | 3.578x | 0.482x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.202x to 0.681x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,737.2 | 729.3-1,353.6 | 10.10 | **no** | `b200_sxm-x157-nvl72-hybrid` | 588.6 | 1,284.6-2,384.3 | 1.94 | yes | 2.951x | 0.568x | 0.192x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,305.6 | 2,580.1-4,789.1 | 3.79 | yes | `b200_sxm-x144-nvl72-hybrid` | 598.2 | 1,307.8-2,427.4 | 1.94 | yes | 3.854x | 1.973x | 0.512x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,737.2 | 729.3-1,353.6 | 10.10 | **no** | `b200_sxm-x157-nvl72-hybrid` | 588.6 | 1,284.6-2,384.3 | 1.94 | yes | 2.951x | 0.568x | 0.192x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,305.6 | 2,580.1-4,789.1 | 3.79 | yes | `b200_sxm-x144-nvl72-hybrid` | 598.2 | 1,307.8-2,427.4 | 1.94 | yes | 3.854x | 1.973x | 0.512x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,737.2 | 729.3-1,353.6 | 10.10 | **no** | `b200_sxm-x157-nvl72-hybrid` | 576.8 | 1,115.5-2,070.6 | 2.19 | yes | 3.012x | 0.654x | 0.217x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,305.6 | 2,580.1-4,789.1 | 3.79 | yes | `b200_sxm-x144-nvl72-hybrid` | 573.6 | 1,104.4-2,049.8 | 2.20 | yes | 4.020x | 2.336x | 0.581x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,737.2 | 729.3-1,353.6 | 10.10 | **no** | `b200_sxm-x157-nvl72-hybrid` | 564.2 | 1,188.8-2,206.7 | 2.01 | yes | 3.079x | 0.613x | 0.199x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,305.6 | 2,580.1-4,789.1 | 3.79 | yes | `b200_sxm-x144-nvl72-hybrid` | 566.5 | 1,190.3-2,209.4 | 2.02 | yes | 4.070x | 2.168x | 0.533x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,737.2 | 729.3-1,353.6 | 10.10 | **no** | `b200_sxm-x157-nvl72-hybrid` | 534.6 | 944.4-1,752.9 | 2.40 | yes | 3.249x | 0.772x | 0.238x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,305.6 | 2,580.1-4,789.1 | 3.79 | yes | `b200_sxm-x144-nvl72-hybrid` | 529.0 | 894.7-1,660.6 | 2.51 | yes | 4.358x | 2.884x | 0.662x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,737.2 | 729.3-1,353.6 | 10.10 | **no** | `b200_sxm-x157-nvl72-hybrid` | 469.8 | 634.8-1,178.3 | 3.14 | yes | 3.698x | 1.149x | 0.311x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2,303.4 | 1,615.8-2,999.1 | 6.04 | yes | `b200_sxm-x144-nvl72-hybrid` | 460.2 | 594.2-1,103.0 | 3.28 | yes | 5.005x | 2.719x | 0.543x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,737.2 | 729.3-1,353.6 | 10.10 | **no** | `b200_sxm-x157-nvl72-hybrid` | 379.7 | 384.4-713.5 | 4.19 | yes | 4.576x | 1.897x | 0.415x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,292.9 | 1,617.8-3,002.9 | 6.01 | yes | `b200_sxm-x347-nvl72-hybrid` | 474.4 | 668.7-1,241.2 | 3.01 | yes | 4.834x | 2.419x | 0.501x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,376.2 | 331.6-615.5 | 17.60 | **no** | `b200_sxm-x157-nvl72-hybrid` | 193.1 | 199.8-370.9 | 4.10 | yes | 7.128x | 1.660x | 0.233x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,912.2 | 759.0-1,408.9 | 10.68 | **no** | `b200_sxm-x347-nvl72-hybrid` | 288.1 | 301.1-558.9 | 4.06 | yes | 6.636x | 2.521x | 0.380x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 679.7 | 127.4-236.4 | 22.63 | **no** | `b200_sxm-x173-nvl72-hybrid` | 82.9 | 73.3-136.1 | 4.79 | yes | 8.202x | 1.737x | 0.212x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,049.8 | 202.2-375.4 | 22.01 | **no** | `b200_sxm-x347-nvl72-hybrid` | 129.8 | 125.2-232.3 | 4.40 | yes | 8.089x | 1.616x | 0.200x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 200.7 | 45.5-84.5 | 18.68 | **no** | `b200_sxm-x173-nvl72-hybrid` | 39.2 | 21.0-39.0 | 7.91 | **no** | 5.115x | 2.167x | 0.424x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 415.1 | 121.1-224.8 | 14.53 | **no** | `b200_sxm-x347-nvl72-hybrid` | 53.9 | 37.8-70.2 | 6.04 | yes | 7.699x | 3.202x | 0.416x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.192x to 0.662x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x170` | 2,142.2 | 516.5-958.7 | 17.59 | **no** | `a100_sxm_80gb-x168-hybrid` | 332.9 | 290.6-539.3 | 4.86 | yes | 6.435x | 1.777x | 0.276x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 3,716.7 | 3,082.1-5,720.7 | 5.11 | yes | `a100_sxm_80gb-x168-hybrid` | 332.9 | 290.6-539.3 | 4.86 | yes | 11.165x | 10.607x | 0.950x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,771.6 | 711.1-1,319.8 | 10.56 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 285.4-529.7 | 4.81 | yes | 5.471x | 2.491x | 0.455x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,405.2 | 1,644.0-3,051.5 | 6.20 | yes | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 289.6-537.5 | 4.76 | yes | 7.404x | 5.677x | 0.767x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,771.6 | 711.1-1,319.8 | 10.56 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 285.4-529.7 | 4.81 | yes | 5.471x | 2.491x | 0.455x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,405.2 | 1,644.0-3,051.5 | 6.20 | yes | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 289.6-537.5 | 4.76 | yes | 7.404x | 5.677x | 0.767x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,771.6 | 711.1-1,319.8 | 10.56 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 285.4-529.7 | 4.81 | yes | 5.471x | 2.491x | 0.455x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,405.2 | 1,644.0-3,051.5 | 6.20 | yes | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 289.6-537.5 | 4.76 | yes | 7.404x | 5.677x | 0.767x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,771.6 | 711.1-1,319.8 | 10.56 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 285.4-529.7 | 4.81 | yes | 5.471x | 2.491x | 0.455x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,405.2 | 1,644.0-3,051.5 | 6.20 | yes | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 289.6-537.5 | 4.76 | yes | 7.404x | 5.677x | 0.767x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,771.6 | 711.1-1,319.8 | 10.56 | **no** | `a100_sxm_80gb-x387-hybrid` | 323.8 | 285.4-529.7 | 4.81 | yes | 5.471x | 2.491x | 0.455x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,405.2 | 1,644.0-3,051.5 | 6.20 | yes | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 289.6-537.5 | 4.76 | yes | 7.404x | 5.677x | 0.767x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 1,664.8 | 639.3-1,186.6 | 11.04 | **no** | `a100_sxm_80gb-x387-hybrid` | 296.8 | 228.4-423.9 | 5.51 | yes | 5.610x | 2.799x | 0.499x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,210.8 | 1,530.2-2,840.2 | 6.13 | yes | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 289.6-537.5 | 4.76 | yes | 6.805x | 5.284x | 0.776x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,177.0 | 311.0-577.2 | 16.05 | **no** | `a100_sxm_80gb-x387-hybrid` | 175.3 | 121.0-224.7 | 6.14 | yes | 6.714x | 2.569x | 0.383x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,229.9 | 556.1-1,032.2 | 9.38 | **no** | `a100_sxm_80gb-x2574-hybrid` | 324.9 | 289.6-537.5 | 4.76 | yes | 3.786x | 1.920x | 0.507x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 358.8 | 114.9-213.3 | 13.24 | **no** | `a100_sxm_80gb-x387-hybrid` | 80.5 | 60.1-111.5 | 5.68 | yes | 4.456x | 1.912x | 0.429x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 390.0 | 150.1-278.6 | 11.02 | **no** | `a100_sxm_80gb-x2574-hybrid` | 222.0 | 194.3-360.7 | 4.85 | yes | 1.756x | 0.772x | 0.440x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 93.4 | 41.5-77.1 | 9.54 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 103.3 | 37.8-70.2 | 11.57 | **no** | `a100_sxm_80gb-x2574-hybrid` | 111.7 | 98.0-182.0 | 4.83 | yes | 0.925x | 0.386x | 0.417x |

**Does the ratio compress?** Of 19 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.276x to 0.950x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,425.7 | 1,255.0-2,329.4 | 11.57 | **no** | `a100_sxm_80gb-x73-hybrid` | 404.0 | 683.8-1,269.2 | 2.50 | yes | 8.480x | 1.835x | 0.216x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,946.2 | 3,301.5-6,128.1 | 5.07 | yes | `a100_sxm_80gb-x112-hybrid` | 413.4 | 722.4-1,340.8 | 2.43 | yes | 9.547x | 4.570x | 0.479x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,425.7 | 1,255.0-2,329.4 | 11.57 | **no** | `a100_sxm_80gb-x73-hybrid` | 404.0 | 683.8-1,269.2 | 2.50 | yes | 8.480x | 1.835x | 0.216x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,946.2 | 3,301.5-6,128.1 | 5.07 | yes | `a100_sxm_80gb-x112-hybrid` | 413.4 | 722.4-1,340.8 | 2.43 | yes | 9.547x | 4.570x | 0.479x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,425.7 | 1,255.0-2,329.4 | 11.57 | **no** | `a100_sxm_80gb-x73-hybrid` | 404.0 | 683.8-1,269.2 | 2.50 | yes | 8.480x | 1.835x | 0.216x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,946.2 | 3,301.5-6,128.1 | 5.07 | yes | `a100_sxm_80gb-x112-hybrid` | 413.4 | 722.4-1,340.8 | 2.43 | yes | 9.547x | 4.570x | 0.479x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,425.7 | 1,255.0-2,329.4 | 11.57 | **no** | `a100_sxm_80gb-x73-hybrid` | 404.0 | 683.8-1,269.2 | 2.50 | yes | 8.480x | 1.835x | 0.216x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,946.2 | 3,301.5-6,128.1 | 5.07 | yes | `a100_sxm_80gb-x112-hybrid` | 413.4 | 722.4-1,340.8 | 2.43 | yes | 9.547x | 4.570x | 0.479x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,425.7 | 1,255.0-2,329.4 | 11.57 | **no** | `a100_sxm_80gb-x73-hybrid` | 374.0 | 544.1-1,010.0 | 2.91 | yes | 9.159x | 2.306x | 0.252x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 3,941.8 | 3,691.8-6,852.4 | 4.53 | yes | `a100_sxm_80gb-x168-hybrid` | 409.4 | 719.8-1,336.1 | 2.41 | yes | 9.628x | 5.129x | 0.533x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,425.7 | 1,255.0-2,329.4 | 11.57 | **no** | `a100_sxm_80gb-x73-hybrid` | 313.2 | 369.3-685.5 | 3.60 | yes | 10.937x | 3.398x | 0.311x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,924.3 | 3,731.6-6,926.4 | 4.46 | yes | `a100_sxm_80gb-x448-hybrid` | 397.4 | 696.7-1,293.1 | 2.42 | yes | 9.874x | 5.356x | 0.542x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 3,369.8 | 1,241.6-2,304.5 | 11.51 | **no** | `a100_sxm_80gb-x146-hybrid` | 309.0 | 356.8-662.3 | 3.67 | yes | 10.906x | 3.480x | 0.319x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,922.2 | 3,720.9-6,906.5 | 4.47 | yes | `a100_sxm_80gb-x672-hybrid` | 397.4 | 708.9-1,315.8 | 2.38 | yes | 9.869x | 5.249x | 0.532x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,828.2 | 969.0-1,798.6 | 12.38 | **no** | `a100_sxm_80gb-x335-hybrid` | 235.3 | 203.9-378.4 | 4.89 | yes | 12.022x | 4.753x | 0.395x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,256.7 | 1,931.7-3,585.6 | 7.15 | yes | `a100_sxm_80gb-x672-hybrid` | 309.6 | 343.9-638.3 | 3.82 | yes | 10.519x | 5.617x | 0.534x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,277.8 | 315.2-585.0 | 17.19 | **no** | `a100_sxm_80gb-x335-hybrid` | 112.0 | 119.9-222.6 | 3.96 | yes | 11.410x | 2.627x | 0.230x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,776.8 | 573.4-1,064.4 | 13.14 | **no** | `a100_sxm_80gb-x672-hybrid` | 168.7 | 204.1-378.8 | 3.50 | yes | 10.535x | 2.810x | 0.267x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 375.6 | 93.3-173.1 | 17.08 | **no** | `a100_sxm_80gb-x335-hybrid` | 46.8 | 32.6-60.4 | 6.10 | yes | 8.022x | 2.864x | 0.357x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 567.0 | 194.5-360.9 | 12.36 | **no** | `a100_sxm_80gb-x672-hybrid` | 71.5 | 64.4-119.5 | 4.71 | yes | 7.925x | 3.021x | 0.381x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.216x to 0.542x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 3,498.1 | 1,302.8-2,418.2 | 11.38 | **no** | `a100_sxm_80gb-x73-hybrid` | 406.3 | 709.1-1,316.3 | 2.43 | yes | 8.609x | 1.837x | 0.213x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,176.9 | 3,990.3-7,406.6 | 4.44 | yes | `a100_sxm_80gb-x112-hybrid` | 415.8 | 750.7-1,393.4 | 2.35 | yes | 10.045x | 5.316x | 0.529x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 3,498.1 | 1,302.8-2,418.2 | 11.38 | **no** | `a100_sxm_80gb-x73-hybrid` | 406.3 | 709.1-1,316.3 | 2.43 | yes | 8.609x | 1.837x | 0.213x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,176.9 | 3,990.3-7,406.6 | 4.44 | yes | `a100_sxm_80gb-x112-hybrid` | 415.8 | 750.7-1,393.4 | 2.35 | yes | 10.045x | 5.316x | 0.529x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 3,498.1 | 1,302.8-2,418.2 | 11.38 | **no** | `a100_sxm_80gb-x73-hybrid` | 406.3 | 709.1-1,316.3 | 2.43 | yes | 8.609x | 1.837x | 0.213x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,176.9 | 3,990.3-7,406.6 | 4.44 | yes | `a100_sxm_80gb-x112-hybrid` | 415.8 | 750.7-1,393.4 | 2.35 | yes | 10.045x | 5.316x | 0.529x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 3,498.1 | 1,302.8-2,418.2 | 11.38 | **no** | `a100_sxm_80gb-x73-hybrid` | 406.3 | 709.1-1,316.3 | 2.43 | yes | 8.609x | 1.837x | 0.213x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,176.9 | 3,990.3-7,406.6 | 4.44 | yes | `a100_sxm_80gb-x112-hybrid` | 415.8 | 750.7-1,393.4 | 2.35 | yes | 10.045x | 5.316x | 0.529x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 3,498.1 | 1,302.8-2,418.2 | 11.38 | **no** | `a100_sxm_80gb-x73-hybrid` | 377.3 | 570.1-1,058.2 | 2.81 | yes | 9.272x | 2.285x | 0.246x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 4,169.8 | 4,031.3-7,482.5 | 4.39 | yes | `a100_sxm_80gb-x168-hybrid` | 411.8 | 747.9-1,388.3 | 2.33 | yes | 10.126x | 5.390x | 0.532x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 3,498.1 | 1,302.8-2,418.2 | 11.38 | **no** | `a100_sxm_80gb-x73-hybrid` | 317.9 | 393.6-730.7 | 3.42 | yes | 11.005x | 3.310x | 0.301x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4,142.7 | 4,074.2-7,562.2 | 4.31 | yes | `a100_sxm_80gb-x448-hybrid` | 399.7 | 722.9-1,341.8 | 2.34 | yes | 10.365x | 5.636x | 0.544x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 3,474.8 | 1,297.3-2,407.9 | 11.36 | **no** | `a100_sxm_80gb-x146-hybrid` | 313.7 | 380.7-706.6 | 3.49 | yes | 11.077x | 3.408x | 0.308x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,141.9 | 4,062.3-7,540.2 | 4.32 | yes | `a100_sxm_80gb-x672-hybrid` | 399.7 | 736.1-1,366.2 | 2.30 | yes | 10.362x | 5.519x | 0.533x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,943.0 | 1,021.0-1,895.2 | 12.22 | **no** | `a100_sxm_80gb-x335-hybrid` | 240.2 | 218.0-404.6 | 4.67 | yes | 12.254x | 4.684x | 0.382x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,700.8 | 2,107.3-3,911.4 | 7.45 | yes | `a100_sxm_80gb-x672-hybrid` | 313.8 | 363.8-675.2 | 3.66 | yes | 11.793x | 5.793x | 0.491x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,370.5 | 337.7-626.8 | 17.21 | **no** | `a100_sxm_80gb-x335-hybrid` | 112.9 | 131.8-244.7 | 3.63 | yes | 12.145x | 2.561x | 0.211x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,386.5 | 608.4-1,129.3 | 16.63 | **no** | `a100_sxm_80gb-x672-hybrid` | 169.6 | 222.1-412.3 | 3.24 | yes | 14.068x | 2.739x | 0.195x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 408.5 | 101.4-188.2 | 17.08 | **no** | `a100_sxm_80gb-x335-hybrid` | 47.4 | 36.9-68.5 | 5.45 | yes | 8.612x | 2.747x | 0.319x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 845.0 | 212.1-393.7 | 16.89 | **no** | `a100_sxm_80gb-x672-hybrid` | 72.3 | 72.8-135.2 | 4.21 | yes | 11.695x | 2.912x | 0.249x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.195x to 0.544x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,430.0 | 476.0-883.6 | 12.74 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 261.4-485.1 | 3.06 | yes | 7.580x | 1.821x | 0.240x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 2,087.8 | 1,805.3-3,351.0 | 4.90 | yes | `a100_sxm_80gb-x336-hybrid` | 190.0 | 262.8-487.8 | 3.06 | yes | 10.990x | 6.870x | 0.625x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,430.0 | 476.0-883.6 | 12.74 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 261.4-485.1 | 3.06 | yes | 7.580x | 1.821x | 0.240x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,881.4 | 1,999.8-3,711.9 | 3.99 | yes | `a100_sxm_80gb-x783-hybrid` | 186.9 | 264.6-491.1 | 3.00 | yes | 10.065x | 7.558x | 0.751x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,430.0 | 476.0-883.6 | 12.74 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 261.4-485.1 | 3.06 | yes | 7.580x | 1.821x | 0.240x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,881.4 | 1,999.8-3,711.9 | 3.99 | yes | `a100_sxm_80gb-x783-hybrid` | 186.9 | 264.6-491.1 | 3.00 | yes | 10.065x | 7.558x | 0.751x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,430.0 | 476.0-883.6 | 12.74 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 261.4-485.1 | 3.06 | yes | 7.580x | 1.821x | 0.240x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,881.4 | 1,999.8-3,711.9 | 3.99 | yes | `a100_sxm_80gb-x783-hybrid` | 186.9 | 264.6-491.1 | 3.00 | yes | 10.065x | 7.558x | 0.751x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,430.0 | 476.0-883.6 | 12.74 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 261.4-485.1 | 3.06 | yes | 7.580x | 1.821x | 0.240x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,881.4 | 1,999.8-3,711.9 | 3.99 | yes | `a100_sxm_80gb-x783-hybrid` | 186.9 | 264.6-491.1 | 3.00 | yes | 10.065x | 7.558x | 0.751x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,430.0 | 476.0-883.6 | 12.74 | **no** | `a100_sxm_80gb-x391-hybrid` | 188.6 | 261.4-485.1 | 3.06 | yes | 7.580x | 1.821x | 0.240x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,841.2 | 1,326.3-2,461.8 | 5.89 | yes | `a100_sxm_80gb-x783-hybrid` | 186.9 | 264.6-491.1 | 3.00 | yes | 9.849x | 5.012x | 0.509x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,430.0 | 476.0-883.6 | 12.74 | **no** | `a100_sxm_80gb-x391-hybrid` | 176.0 | 215.5-400.1 | 3.46 | yes | 8.125x | 2.209x | 0.272x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,709.4 | 1,225.1-2,273.9 | 5.92 | yes | `a100_sxm_80gb-x783-hybrid` | 186.9 | 264.6-491.1 | 3.00 | yes | 9.144x | 4.630x | 0.506x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,093.9 | 239.9-445.2 | 19.34 | **no** | `a100_sxm_80gb-x391-hybrid` | 95.6 | 75.1-139.5 | 5.40 | yes | 11.436x | 3.192x | 0.279x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,024.3 | 389.7-723.4 | 11.14 | **no** | `a100_sxm_80gb-x783-hybrid` | 135.4 | 127.4-236.6 | 4.51 | yes | 7.564x | 3.058x | 0.404x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 401.6 | 80.4-149.2 | 21.19 | **no** | `a100_sxm_80gb-x391-hybrid` | 37.1 | 37.9-70.3 | 4.15 | yes | 10.828x | 2.122x | 0.196x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 364.5 | 101.4-188.2 | 15.24 | **no** | `a100_sxm_80gb-x783-hybrid` | 59.6 | 62.5-116.0 | 4.05 | yes | 6.114x | 1.623x | 0.265x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 110.1 | 25.7-47.7 | 18.16 | **no** | `a100_sxm_80gb-x391-hybrid` | 13.2 | 10.6-19.7 | 5.29 | yes | 8.323x | 2.425x | 0.291x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 99.0 | 56.6-105.0 | 7.41 | yes | `a100_sxm_80gb-x783-hybrid` | 22.1 | 20.7-38.4 | 4.54 | yes | 4.474x | 2.737x | 0.612x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.196x to 0.751x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,567.1 | 546.6-1,014.6 | 12.16 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 304.9-565.9 | 2.65 | yes | 8.212x | 1.793x | 0.218x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,216.0 | 1,993.6-3,700.4 | 4.71 | yes | `a100_sxm_80gb-x336-hybrid` | 192.2 | 306.8-569.5 | 2.66 | yes | 11.529x | 6.497x | 0.564x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,567.1 | 546.6-1,014.6 | 12.16 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 304.9-565.9 | 2.65 | yes | 8.212x | 1.793x | 0.218x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,216.0 | 1,993.6-3,700.4 | 4.71 | yes | `a100_sxm_80gb-x336-hybrid` | 192.2 | 306.8-569.5 | 2.66 | yes | 11.529x | 6.497x | 0.564x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,567.1 | 546.6-1,014.6 | 12.16 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 304.9-565.9 | 2.65 | yes | 8.212x | 1.793x | 0.218x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,216.0 | 1,993.6-3,700.4 | 4.71 | yes | `a100_sxm_80gb-x336-hybrid` | 192.2 | 306.8-569.5 | 2.66 | yes | 11.529x | 6.497x | 0.564x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,567.1 | 546.6-1,014.6 | 12.16 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 304.9-565.9 | 2.65 | yes | 8.212x | 1.793x | 0.218x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,216.0 | 1,993.6-3,700.4 | 4.71 | yes | `a100_sxm_80gb-x336-hybrid` | 192.2 | 306.8-569.5 | 2.66 | yes | 11.529x | 6.497x | 0.564x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,567.1 | 546.6-1,014.6 | 12.16 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 304.9-565.9 | 2.65 | yes | 8.212x | 1.793x | 0.218x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,216.0 | 1,993.6-3,700.4 | 4.71 | yes | `a100_sxm_80gb-x336-hybrid` | 192.2 | 306.8-569.5 | 2.66 | yes | 11.529x | 6.497x | 0.564x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,567.1 | 546.6-1,014.6 | 12.16 | **no** | `a100_sxm_80gb-x391-hybrid` | 190.8 | 304.9-565.9 | 2.65 | yes | 8.212x | 1.793x | 0.218x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,205.0 | 2,012.0-3,734.5 | 4.65 | yes | `a100_sxm_80gb-x672-hybrid` | 189.2 | 306.9-569.7 | 2.61 | yes | 11.653x | 6.555x | 0.563x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,567.1 | 546.6-1,014.6 | 12.16 | **no** | `a100_sxm_80gb-x391-hybrid` | 178.9 | 254.7-472.7 | 2.98 | yes | 8.759x | 2.146x | 0.245x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,088.7 | 1,199.7-2,226.7 | 7.38 | yes | `a100_sxm_80gb-x672-hybrid` | 189.2 | 306.9-569.7 | 2.61 | yes | 11.039x | 3.909x | 0.354x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,267.4 | 272.2-505.3 | 19.74 | **no** | `a100_sxm_80gb-x391-hybrid` | 100.6 | 95.6-177.4 | 4.46 | yes | 12.600x | 2.849x | 0.226x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,630.5 | 543.6-1,009.0 | 12.72 | **no** | `a100_sxm_80gb-x672-hybrid` | 130.8 | 137.5-255.3 | 4.03 | yes | 12.465x | 3.952x | 0.317x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 501.9 | 95.7-177.7 | 22.23 | **no** | `a100_sxm_80gb-x391-hybrid` | 38.4 | 30.1-55.8 | 5.41 | yes | 13.086x | 3.185x | 0.243x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 892.8 | 240.5-446.4 | 15.74 | **no** | `a100_sxm_80gb-x672-hybrid` | 56.1 | 46.0-85.3 | 5.18 | yes | 15.902x | 5.231x | 0.329x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 141.3 | 32.4-60.2 | 18.49 | **no** | `a100_sxm_80gb-x391-hybrid` | 14.5 | 7.7-14.3 | 7.98 | **no** | 9.764x | 4.214x | 0.432x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 333.3 | 77.2-143.2 | 18.32 | **no** | `a100_sxm_80gb-x672-hybrid` | 20.3 | 25.3-47.0 | 3.39 | yes | 16.454x | 3.048x | 0.185x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.185x to 0.564x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,630.8 | 561.2-1,041.6 | 12.32 | **no** | `a100_sxm_80gb-x391-hybrid` | 191.0 | 308.0-571.7 | 2.63 | yes | 8.539x | 1.822x | 0.213x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,262.2 | 2,058.7-3,821.3 | 4.66 | yes | `a100_sxm_80gb-x336-hybrid` | 192.4 | 309.6-574.6 | 2.63 | yes | 11.761x | 6.650x | 0.565x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,630.8 | 561.2-1,041.6 | 12.32 | **no** | `a100_sxm_80gb-x391-hybrid` | 191.0 | 308.0-571.7 | 2.63 | yes | 8.539x | 1.822x | 0.213x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,262.2 | 2,058.7-3,821.3 | 4.66 | yes | `a100_sxm_80gb-x336-hybrid` | 192.4 | 309.6-574.6 | 2.63 | yes | 11.761x | 6.650x | 0.565x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,630.8 | 561.2-1,041.6 | 12.32 | **no** | `a100_sxm_80gb-x391-hybrid` | 191.0 | 308.0-571.7 | 2.63 | yes | 8.539x | 1.822x | 0.213x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,262.2 | 2,058.7-3,821.3 | 4.66 | yes | `a100_sxm_80gb-x336-hybrid` | 192.4 | 309.6-574.6 | 2.63 | yes | 11.761x | 6.650x | 0.565x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,630.8 | 561.2-1,041.6 | 12.32 | **no** | `a100_sxm_80gb-x391-hybrid` | 191.0 | 308.0-571.7 | 2.63 | yes | 8.539x | 1.822x | 0.213x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,262.2 | 2,058.7-3,821.3 | 4.66 | yes | `a100_sxm_80gb-x336-hybrid` | 192.4 | 309.6-574.6 | 2.63 | yes | 11.761x | 6.650x | 0.565x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,630.8 | 561.2-1,041.6 | 12.32 | **no** | `a100_sxm_80gb-x391-hybrid` | 191.0 | 308.0-571.7 | 2.63 | yes | 8.539x | 1.822x | 0.213x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,262.2 | 2,058.7-3,821.3 | 4.66 | yes | `a100_sxm_80gb-x336-hybrid` | 192.4 | 309.6-574.6 | 2.63 | yes | 11.761x | 6.650x | 0.565x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,630.8 | 561.2-1,041.6 | 12.32 | **no** | `a100_sxm_80gb-x391-hybrid` | 191.0 | 308.0-571.7 | 2.63 | yes | 8.539x | 1.822x | 0.213x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,249.4 | 2,079.0-3,858.8 | 4.59 | yes | `a100_sxm_80gb-x672-hybrid` | 189.4 | 311.5-578.2 | 2.58 | yes | 11.879x | 6.674x | 0.562x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,630.8 | 561.2-1,041.6 | 12.32 | **no** | `a100_sxm_80gb-x391-hybrid` | 179.1 | 258.0-479.0 | 2.94 | yes | 9.106x | 2.175x | 0.239x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,215.6 | 1,235.6-2,293.5 | 7.60 | yes | `a100_sxm_80gb-x672-hybrid` | 189.4 | 311.5-578.2 | 2.58 | yes | 11.700x | 3.967x | 0.339x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,298.4 | 277.8-515.6 | 19.82 | **no** | `a100_sxm_80gb-x391-hybrid` | 100.8 | 99.2-184.0 | 4.31 | yes | 12.881x | 2.801x | 0.217x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,712.5 | 559.5-1,038.5 | 12.98 | **no** | `a100_sxm_80gb-x672-hybrid` | 131.0 | 141.8-263.2 | 3.92 | yes | 13.071x | 3.946x | 0.302x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 521.2 | 98.5-182.8 | 22.43 | **no** | `a100_sxm_80gb-x391-hybrid` | 38.5 | 32.0-59.4 | 5.10 | yes | 13.546x | 3.079x | 0.227x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 949.3 | 284.3-527.6 | 14.16 | **no** | `a100_sxm_80gb-x672-hybrid` | 56.3 | 47.9-88.9 | 4.98 | yes | 16.863x | 5.933x | 0.352x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 147.6 | 33.7-62.6 | 18.55 | **no** | `a100_sxm_80gb-x391-hybrid` | 14.5 | 8.3-15.4 | 7.46 | yes | 10.145x | 4.078x | 0.402x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 365.4 | 89.3-165.8 | 17.35 | **no** | `a100_sxm_80gb-x672-hybrid` | 20.3 | 26.8-49.7 | 3.22 | yes | 17.965x | 3.337x | 0.186x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.186x to 0.565x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x8-romfill` | 8,382.2 | 6,115.7-11,351.5 | 5.81 | yes | `b200_sxm-x4-tensor` | 1,019.6 | 3,569.5-6,625.5 | 1.21 | yes | 8.221x | 1.713x | 0.208x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 9,245.0 | 13,725.9-25,477.0 | 2.86 | yes | `b200_sxm-x29-nvl72-tensor` | 2,284.3 | 7,716.0-14,321.9 | 1.26 | yes | 4.047x | 1.779x | 0.440x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 7,221.4 | 5,681.2-10,545.0 | 5.39 | yes | `b200_sxm-x32-nvl72-tensor` | 2,283.2 | 7,126.8-13,228.3 | 1.36 | yes | 3.163x | 0.797x | 0.252x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 7,446.9 | 13,141.9-24,393.1 | 2.40 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,493.8 | 8,279.5-15,367.9 | 1.28 | yes | 2.986x | 1.587x | 0.532x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 7,221.4 | 5,681.2-10,545.0 | 5.39 | yes | `b200_sxm-x32-nvl72-tensor` | 2,199.2 | 6,014.6-11,163.9 | 1.55 | yes | 3.284x | 0.945x | 0.288x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 7,446.9 | 13,141.9-24,393.1 | 2.40 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,481.1 | 7,970.6-14,794.4 | 1.32 | yes | 3.001x | 1.649x | 0.549x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 7,221.4 | 5,681.2-10,545.0 | 5.39 | yes | `b200_sxm-x32-nvl72-tensor` | 2,048.4 | 4,583.9-8,508.4 | 1.89 | yes | 3.525x | 1.239x | 0.352x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 7,423.2 | 13,113.5-24,340.3 | 2.40 | yes | `b200_sxm-x231-nvl72-hybrid` | 2,442.5 | 7,307.4-13,563.6 | 1.42 | yes | 3.039x | 1.795x | 0.590x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x147-romfill` | 7,085.2 | 5,612.4-10,417.4 | 5.35 | yes | `b200_sxm-x75-nvl72-hybrid` | 2,099.4 | 4,503.3-8,358.6 | 1.98 | yes | 3.375x | 1.246x | 0.369x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6,431.0 | 11,705.2-21,726.3 | 2.33 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,432.9 | 6,441.0-11,955.3 | 1.60 | yes | 2.643x | 1.817x | 0.687x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,925.7 | 5,579.0-10,355.3 | 5.26 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,172.2 | 3,896.3-7,232.1 | 2.36 | yes | 3.188x | 1.432x | 0.449x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,170.8 | 8,697.6-16,144.0 | 2.52 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,325.6 | 4,886.7-9,070.3 | 2.02 | yes | 2.223x | 1.780x | 0.801x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,086.3 | 3,686.9-6,843.3 | 7.00 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,901.6 | 2,447.6-4,543.0 | 3.29 | yes | 3.201x | 1.506x | 0.471x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,660.4 | 6,688.0-12,413.9 | 2.32 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,137.1 | 3,291.1-6,108.8 | 2.75 | yes | 1.713x | 2.032x | 1.186x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,148.4 | 1,385.3-2,571.3 | 9.64 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,192.8 | 1,313.5-2,438.0 | 3.85 | yes | 2.639x | 1.055x | 0.400x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,238.0 | 2,801.2-5,199.3 | 1.87 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,521.5 | 1,928.2-3,579.1 | 3.35 | yes | 0.814x | 1.453x | 1.785x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 801.0 | 343.7-637.9 | 9.88 | **no** | `b200_sxm-x173-nvl72-hybrid` | 531.3 | 587.2-1,090.0 | 3.84 | yes | 1.507x | 0.585x | 0.388x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 331.2 | 822.4-1,526.4 | 1.71 | yes | `b200_sxm-x347-nvl72-hybrid` | 808.3 | 972.7-1,805.4 | 3.52 | yes | 0.410x | 0.845x | 2.063x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 201.1 | 83.7-155.4 | 10.18 | **no** | `b200_sxm-x173-nvl72-hybrid` | 178.3 | 247.7-459.7 | 3.05 | yes | 1.128x | 0.338x | 0.300x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 84.0 | 203.7-378.0 | 1.75 | yes | `b200_sxm-x347-nvl72-hybrid` | 314.7 | 456.2-846.8 | 2.92 | yes | 0.267x | 0.446x | 1.672x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 3,459.7 | 1,389.5-2,579.1 | 10.56 | **no** | `b200_sxm-x29-nvl72-tensor` | 846.3 | 1,689.6-3,136.1 | 2.12 | yes | 4.088x | 0.822x | 0.201x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3,938.3 | 3,267.7-6,065.2 | 5.11 | yes | `b200_sxm-x58-nvl72-tensor` | 862.2 | 1,717.2-3,187.3 | 2.13 | yes | 4.568x | 1.903x | 0.417x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 3,398.5 | 1,331.9-2,472.3 | 10.82 | **no** | `b200_sxm-x31-hybrid` | 818.6 | 1,481.1-2,749.1 | 2.34 | yes | 4.152x | 0.899x | 0.217x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,588.4 | 4,724.9-8,770.0 | 3.22 | yes | `b200_sxm-x202-nvl72-hybrid` | 858.2 | 1,695.3-3,146.6 | 2.15 | yes | 4.181x | 2.787x | 0.667x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 3,398.5 | 1,331.9-2,472.3 | 10.82 | **no** | `b200_sxm-x31-hybrid` | 818.6 | 1,481.1-2,749.1 | 2.34 | yes | 4.152x | 0.899x | 0.217x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,588.4 | 4,724.9-8,770.0 | 3.22 | yes | `b200_sxm-x202-nvl72-hybrid` | 851.5 | 1,682.4-3,122.7 | 2.15 | yes | 4.214x | 2.808x | 0.666x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 3,398.5 | 1,331.9-2,472.3 | 10.82 | **no** | `b200_sxm-x31-hybrid` | 747.5 | 1,024.5-1,901.5 | 3.09 | yes | 4.547x | 1.300x | 0.286x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,588.4 | 4,724.9-8,770.0 | 3.22 | yes | `b200_sxm-x202-nvl72-hybrid` | 828.3 | 1,577.0-2,927.1 | 2.23 | yes | 4.332x | 2.996x | 0.692x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 3,398.5 | 1,331.9-2,472.3 | 10.82 | **no** | `b200_sxm-x31-hybrid` | 638.5 | 648.7-1,204.1 | 4.17 | yes | 5.323x | 2.053x | 0.386x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3,588.4 | 4,724.9-8,770.0 | 3.22 | yes | `b200_sxm-x202-nvl72-hybrid` | 802.0 | 1,583.7-2,939.6 | 2.15 | yes | 4.474x | 2.983x | 0.667x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x70` | 3,349.4 | 1,314.4-2,439.8 | 10.80 | **no** | `b200_sxm-x36-hybrid` | 545.6 | 625.7-1,161.4 | 3.70 | yes | 6.139x | 2.101x | 0.342x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,550.7 | 4,687.3-8,700.2 | 3.21 | yes | `b200_sxm-x347-nvl72-hybrid` | 788.7 | 1,580.9-2,934.4 | 2.12 | yes | 4.502x | 2.965x | 0.659x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 3,151.8 | 1,266.9-2,351.5 | 10.55 | **no** | `b200_sxm-x86-nvl72-hybrid` | 571.5 | 759.4-1,409.6 | 3.19 | yes | 5.515x | 1.668x | 0.302x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,448.8 | 3,579.2-6,643.5 | 4.09 | yes | `b200_sxm-x347-nvl72-hybrid` | 756.8 | 1,302.8-2,418.2 | 2.46 | yes | 4.557x | 2.747x | 0.603x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,595.2 | 948.2-1,760.0 | 11.60 | **no** | `b200_sxm-x173-nvl72-hybrid` | 443.8 | 493.2-915.5 | 3.81 | yes | 5.848x | 1.922x | 0.329x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,436.5 | 1,785.2-3,313.6 | 5.79 | yes | `b200_sxm-x347-nvl72-hybrid` | 564.1 | 793.7-1,473.1 | 3.01 | yes | 4.320x | 2.249x | 0.521x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,123.1 | 292.5-542.9 | 16.28 | **no** | `b200_sxm-x173-nvl72-hybrid` | 217.7 | 292.1-542.3 | 3.16 | yes | 5.158x | 1.001x | 0.194x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,035.3 | 562.3-1,043.7 | 7.81 | yes | `b200_sxm-x347-nvl72-hybrid` | 320.0 | 354.3-657.6 | 3.83 | yes | 3.235x | 1.587x | 0.491x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 324.5 | 81.7-151.7 | 16.83 | **no** | `b200_sxm-x173-nvl72-hybrid` | 91.1 | 108.3-201.0 | 3.57 | yes | 3.564x | 0.755x | 0.212x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 297.9 | 199.4-370.2 | 6.33 | yes | `b200_sxm-x347-nvl72-hybrid` | 140.2 | 186.2-345.6 | 3.19 | yes | 2.125x | 1.071x | 0.504x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340` | 1,165.4 | 377.9-701.4 | 13.08 | **no** | `b200_sxm-x173-nvl72-hybrid` | 509.0 | 515.6-957.0 | 4.19 | yes | 2.290x | 0.733x | 0.320x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 2,048.4 | 1,674.3-3,107.7 | 5.19 | yes | `b200_sxm-x173-nvl72-hybrid` | 509.0 | 515.6-957.0 | 4.19 | yes | 4.025x | 3.247x | 0.807x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,163.0 | 358.8-666.0 | 13.74 | **no** | `b200_sxm-x203-nvl72-hybrid` | 511.9 | 515.4-956.6 | 4.21 | yes | 2.272x | 0.696x | 0.306x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,663.8 | 1,392.9-2,585.5 | 5.06 | yes | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 497.1-922.7 | 4.26 | yes | 3.328x | 2.802x | 0.842x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,163.0 | 358.8-666.0 | 13.74 | **no** | `b200_sxm-x203-nvl72-hybrid` | 504.9 | 512.4-951.1 | 4.18 | yes | 2.303x | 0.700x | 0.304x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,663.8 | 1,392.9-2,585.5 | 5.06 | yes | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 497.1-922.7 | 4.26 | yes | 3.328x | 2.802x | 0.842x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,163.0 | 358.8-666.0 | 13.74 | **no** | `b200_sxm-x203-nvl72-hybrid` | 486.0 | 511.5-949.4 | 4.03 | yes | 2.393x | 0.701x | 0.293x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,663.8 | 1,392.9-2,585.5 | 5.06 | yes | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 497.1-922.7 | 4.26 | yes | 3.328x | 2.802x | 0.842x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,163.0 | 358.8-666.0 | 13.74 | **no** | `b200_sxm-x203-nvl72-hybrid` | 463.0 | 434.9-807.3 | 4.51 | yes | 2.512x | 0.825x | 0.328x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,663.8 | 1,392.9-2,585.5 | 5.06 | yes | `b200_sxm-x1358-nvl72-hybrid` | 499.9 | 497.1-922.7 | 4.26 | yes | 3.328x | 2.802x | 0.842x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,163.0 | 358.8-666.0 | 13.74 | **no** | `b200_sxm-x203-nvl72-hybrid` | 395.7 | 409.6-760.2 | 4.10 | yes | 2.939x | 0.876x | 0.298x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,663.8 | 1,392.9-2,585.5 | 5.06 | yes | `b200_sxm-x1358-nvl72-hybrid` | 472.8 | 496.6-921.8 | 4.04 | yes | 3.519x | 2.805x | 0.797x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,163.0 | 358.8-666.0 | 13.74 | **no** | `b200_sxm-x203-nvl72-hybrid` | 312.7 | 236.2-438.4 | 5.61 | yes | 3.719x | 1.519x | 0.409x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,636.3 | 2,109.2-3,914.9 | 3.29 | yes | `b200_sxm-x1358-nvl72-hybrid` | 468.8 | 506.6-940.3 | 3.92 | yes | 3.491x | 4.164x | 1.193x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 943.2 | 210.1-389.9 | 19.04 | **no** | `b200_sxm-x203-nvl72-hybrid` | 165.5 | 124.9-231.7 | 5.62 | yes | 5.697x | 1.683x | 0.295x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,297.3 | 507.1-941.3 | 10.85 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 368.5 | 366.7-680.6 | 4.26 | yes | 3.521x | 1.383x | 0.393x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 338.0 | 69.6-129.2 | 20.58 | **no** | `b200_sxm-x203-nvl72-hybrid` | 67.5 | 61.8-114.7 | 4.63 | yes | 5.011x | 1.126x | 0.225x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 568.3 | 140.9-261.6 | 17.10 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 218.5 | 201.7-374.4 | 4.59 | yes | 2.601x | 0.699x | 0.269x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 91.7 | 21.6-40.1 | 17.99 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 168.7 | 35.7-66.3 | 20.02 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 97.4 | 73.1-135.6 | 5.65 | yes | 1.731x | 0.489x | 0.282x |

**Does the ratio compress?** Of 59 class rows in this study, 54 move the ROM-versus-GPU ratio DOWN under speculation and 5 move it UP. The movement spans 0.194x to 2.063x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 34 of 60 ROM rows and 59 of 60 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x16-romfill` | 7,885.6 | 5,039.1-9,353.2 | 6.64 | yes | `a100_sxm_80gb-x16-hybrid` | 559.8 | 1,897.6-3,522.1 | 1.25 | yes | 14.087x | 2.656x | 0.189x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 9,289.5 | 13,151.8-24,411.5 | 2.99 | yes | `a100_sxm_80gb-x56-tensor` | 682.2 | 1,245.6-2,312.0 | 2.32 | yes | 13.617x | 10.559x | 0.775x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill` | 5,514.8 | 5,774.8-10,718.8 | 4.05 | yes | `a100_sxm_80gb-x204-tensor` | 687.0 | 775.3-1,439.1 | 3.76 | yes | 8.027x | 7.448x | 0.928x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,433.8 | 11,650.4-21,624.6 | 1.98 | yes | `a100_sxm_80gb-x448-hybrid` | 684.2 | 1,223.8-2,271.6 | 2.37 | yes | 7.942x | 9.519x | 1.199x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill` | 5,514.8 | 5,774.8-10,718.8 | 4.05 | yes | `a100_sxm_80gb-x204-hybrid` | 669.4 | 1,216.4-2,257.9 | 2.33 | yes | 8.239x | 4.747x | 0.576x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,433.8 | 11,650.4-21,624.6 | 1.98 | yes | `a100_sxm_80gb-x448-hybrid` | 684.2 | 1,223.8-2,271.6 | 2.37 | yes | 7.942x | 9.519x | 1.199x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill` | 5,514.8 | 5,774.8-10,718.8 | 4.05 | yes | `a100_sxm_80gb-x204-hybrid` | 622.8 | 787.5-1,461.7 | 3.35 | yes | 8.854x | 7.333x | 0.828x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,433.8 | 11,650.4-21,624.6 | 1.98 | yes | `a100_sxm_80gb-x448-hybrid` | 676.9 | 1,134.3-2,105.4 | 2.53 | yes | 8.027x | 10.271x | 1.280x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,429.1 | 5,670.4-10,525.0 | 4.06 | yes | `a100_sxm_80gb-x272-hybrid` | 583.5 | 884.9-1,642.6 | 2.80 | yes | 9.305x | 6.408x | 0.689x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,497.8 | 9,309.6-17,279.9 | 2.05 | yes | `a100_sxm_80gb-x672-hybrid` | 654.0 | 965.8-1,792.7 | 2.87 | yes | 6.878x | 9.639x | 1.402x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,053.4 | 4,523.2-8,395.7 | 4.74 | yes | `a100_sxm_80gb-x335-hybrid` | 542.6 | 626.7-1,163.2 | 3.67 | yes | 9.314x | 7.218x | 0.775x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,069.3 | 7,115.0-13,206.4 | 1.83 | yes | `a100_sxm_80gb-x672-hybrid` | 591.2 | 587.8-1,091.1 | 4.26 | yes | 5.191x | 12.104x | 2.331x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,991.7 | 3,097.0-5,748.4 | 5.46 | yes | `a100_sxm_80gb-x335-hybrid` | 518.7 | 1,532.1-2,843.8 | 1.44 | yes | 7.696x | 2.021x | 0.263x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,851.7 | 4,983.2-9,249.6 | 1.58 | yes | `a100_sxm_80gb-x672-hybrid` | 535.7 | 1,676.7-3,112.2 | 1.35 | yes | 3.456x | 2.972x | 0.860x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,578.5 | 1,034.1-1,919.5 | 6.47 | yes | `a100_sxm_80gb-x335-hybrid` | 411.4 | 876.5-1,626.8 | 1.99 | yes | 3.837x | 1.180x | 0.307x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 531.6 | 1,780.6-3,304.9 | 1.27 | yes | `a100_sxm_80gb-x672-hybrid` | 478.2 | 1,231.2-2,285.2 | 1.65 | yes | 1.112x | 1.446x | 1.301x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 430.3 | 265.7-493.1 | 6.87 | yes | `a100_sxm_80gb-x335-hybrid` | 225.0 | 273.2-507.1 | 3.49 | yes | 1.912x | 0.972x | 0.509x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 136.7 | 491.4-912.1 | 1.18 | yes | `a100_sxm_80gb-x672-hybrid` | 323.1 | 523.6-971.8 | 2.62 | yes | 0.423x | 0.939x | 2.219x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 110.7 | 127.7-237.0 | 3.68 | yes | `a100_sxm_80gb-x335-hybrid` | 80.4 | 115.7-214.8 | 2.94 | yes | 1.378x | 1.103x | 0.801x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 34.4 | 72.7-134.9 | 2.00 | yes | `a100_sxm_80gb-x672-hybrid` | 140.6 | 139.9-259.7 | 4.26 | yes | 0.244x | 0.520x | 2.126x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | 3,111.9 | 1,051.8-1,952.2 | 12.55 | **no** | `a100_sxm_80gb-x79-hybrid` | 398.0 | 568.4-1,055.1 | 2.97 | yes | 7.818x | 1.850x | 0.237x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 3,938.3 | 3,061.9-5,683.3 | 5.45 | yes | `a100_sxm_80gb-x112-hybrid` | 397.4 | 574.9-1,067.2 | 2.93 | yes | 9.910x | 5.326x | 0.537x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,019.3 | 991.0-1,839.4 | 12.92 | **no** | `a100_sxm_80gb-x85-hybrid` | 394.9 | 564.7-1,048.2 | 2.96 | yes | 7.647x | 1.755x | 0.229x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,217.9 | 3,110.2-5,772.9 | 4.39 | yes | `a100_sxm_80gb-x560-hybrid` | 382.7 | 563.4-1,045.8 | 2.88 | yes | 8.409x | 5.520x | 0.656x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,019.3 | 991.0-1,839.4 | 12.92 | **no** | `a100_sxm_80gb-x85-hybrid` | 394.9 | 564.7-1,048.2 | 2.96 | yes | 7.647x | 1.755x | 0.229x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,217.9 | 3,110.2-5,772.9 | 4.39 | yes | `a100_sxm_80gb-x560-hybrid` | 382.7 | 563.4-1,045.8 | 2.88 | yes | 8.409x | 5.520x | 0.656x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,019.3 | 991.0-1,839.4 | 12.92 | **no** | `a100_sxm_80gb-x85-hybrid` | 394.9 | 564.7-1,048.2 | 2.96 | yes | 7.647x | 1.755x | 0.229x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,217.9 | 3,110.2-5,772.9 | 4.39 | yes | `a100_sxm_80gb-x560-hybrid` | 382.7 | 563.4-1,045.8 | 2.88 | yes | 8.409x | 5.520x | 0.656x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,019.3 | 991.0-1,839.4 | 12.92 | **no** | `a100_sxm_80gb-x85-hybrid` | 367.4 | 450.9-836.9 | 3.46 | yes | 8.218x | 2.198x | 0.267x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,217.9 | 3,110.2-5,772.9 | 4.39 | yes | `a100_sxm_80gb-x560-hybrid` | 382.7 | 563.4-1,045.8 | 2.88 | yes | 8.409x | 5.520x | 0.656x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,019.3 | 991.0-1,839.4 | 12.92 | **no** | `a100_sxm_80gb-x85-hybrid` | 301.2 | 284.0-527.2 | 4.50 | yes | 10.024x | 3.489x | 0.348x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 3,094.0 | 2,050.0-3,805.0 | 6.40 | yes | `a100_sxm_80gb-x560-hybrid` | 382.7 | 563.4-1,045.8 | 2.88 | yes | 8.085x | 3.638x | 0.450x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 2,805.9 | 1,438.1-2,669.3 | 8.27 | **no** | `a100_sxm_80gb-x312-hybrid` | 346.7 | 397.5-737.8 | 3.70 | yes | 8.094x | 3.618x | 0.447x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,761.8 | 1,653.4-3,068.9 | 7.08 | yes | `a100_sxm_80gb-x672-hybrid` | 382.7 | 566.6-1,051.6 | 2.86 | yes | 7.217x | 2.918x | 0.404x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,237.6 | 719.4-1,335.3 | 13.19 | **no** | `a100_sxm_80gb-x335-hybrid` | 215.7 | 239.4-444.3 | 3.82 | yes | 10.375x | 3.005x | 0.290x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,462.6 | 821.8-1,525.3 | 7.55 | yes | `a100_sxm_80gb-x672-hybrid` | 283.6 | 250.7-465.4 | 4.80 | yes | 5.157x | 3.278x | 0.636x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 877.4 | 217.8-404.2 | 17.08 | **no** | `a100_sxm_80gb-x335-hybrid` | 99.1 | 78.0-144.8 | 5.39 | yes | 8.853x | 2.792x | 0.315x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 480.3 | 245.3-455.4 | 8.30 | **no** | `a100_sxm_80gb-x672-hybrid` | 153.9 | 149.4-277.3 | 4.37 | yes | 3.121x | 1.642x | 0.526x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 296.6 | 85.1-157.9 | 14.79 | **no** | `a100_sxm_80gb-x312-hybrid` | 36.4 | 35.1-65.1 | 4.40 | yes | 8.142x | 2.424x | 0.298x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 128.2 | 101.5-188.4 | 5.35 | yes | `a100_sxm_80gb-x672-hybrid` | 61.8 | 72.5-134.5 | 3.61 | yes | 2.075x | 1.401x | 0.675x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 1,066.2 | 416.4-772.9 | 10.86 | **no** | `a100_sxm_80gb-x384-hybrid` | 166.7 | 157.1-291.7 | 4.50 | yes | 6.397x | 2.650x | 0.414x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 1,973.7 | 1,334.2-2,476.5 | 6.27 | yes | `a100_sxm_80gb-x504-hybrid` | 165.1 | 155.8-289.3 | 4.49 | yes | 11.953x | 8.561x | 0.716x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,480.8 | 1,100.2-2,042.2 | 5.71 | yes | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 165.1-306.5 | 4.24 | yes | 8.970x | 6.664x | 0.743x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,480.8 | 1,100.2-2,042.2 | 5.71 | yes | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 165.1-306.5 | 4.24 | yes | 8.970x | 6.664x | 0.743x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,480.8 | 1,100.2-2,042.2 | 5.71 | yes | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 165.1-306.5 | 4.24 | yes | 8.970x | 6.664x | 0.743x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,480.8 | 1,100.2-2,042.2 | 5.71 | yes | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 165.1-306.5 | 4.24 | yes | 8.970x | 6.664x | 0.743x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,480.8 | 1,100.2-2,042.2 | 5.71 | yes | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 165.1-306.5 | 4.24 | yes | 8.970x | 6.664x | 0.743x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,480.8 | 1,100.2-2,042.2 | 5.71 | yes | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 165.1-306.5 | 4.24 | yes | 8.970x | 6.664x | 0.743x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 986.7 | 395.0-733.2 | 10.59 | **no** | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 165.1-306.5 | 4.24 | yes | 5.977x | 2.392x | 0.400x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 361.1 | 104.9-194.7 | 14.60 | **no** | `a100_sxm_80gb-x3694-hybrid` | 118.2 | 82.3-152.7 | 6.09 | yes | 3.055x | 1.275x | 0.417x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 100.3 | 26.4-49.1 | 16.08 | **no** | `a100_sxm_80gb-x3694-hybrid` | 54.9 | 41.6-77.3 | 5.59 | yes | 1.828x | 0.635x | 0.348x |

**Does the ratio compress?** Of 51 class rows in this study, 43 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.189x to 2.331x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 36 of 51 ROM rows and 51 of 51 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 9,973.4 | 7,011.2-13,013.8 | 6.03 | yes | `b200_sxm-x2-tensor` | 1,328.0 | 4,760.3-8,835.8 | 1.18 | yes | 7.510x | 1.473x | 0.196x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 9,137.9 | 14,967.9-27,782.5 | 2.59 | yes | `b200_sxm-x29-nvl72-tensor` | 2,641.2 | 8,871.2-16,466.1 | 1.26 | yes | 3.460x | 1.687x | 0.488x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 7,078.7 | 7,956.9-14,769.1 | 3.77 | yes | `b200_sxm-x32-nvl72-tensor` | 2,601.6 | 7,998.6-14,846.5 | 1.38 | yes | 2.721x | 0.995x | 0.366x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 7,351.8 | 13,886.9-25,775.9 | 2.24 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,693.6 | 8,905.3-16,529.4 | 1.28 | yes | 2.729x | 1.559x | 0.571x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 7,078.7 | 7,956.9-14,769.1 | 3.77 | yes | `b200_sxm-x32-nvl72-tensor` | 2,493.1 | 6,624.0-12,294.9 | 1.60 | yes | 2.839x | 1.201x | 0.423x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 7,351.8 | 13,886.9-25,775.9 | 2.24 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,678.9 | 8,548.9-15,867.9 | 1.33 | yes | 2.744x | 1.624x | 0.592x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 7,078.7 | 7,956.9-14,769.1 | 3.77 | yes | `b200_sxm-x32-nvl72-tensor` | 2,301.1 | 4,928.3-9,147.6 | 1.98 | yes | 3.076x | 1.615x | 0.525x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 7,328.7 | 13,855.1-25,716.9 | 2.24 | yes | `b200_sxm-x231-nvl72-hybrid` | 2,633.5 | 7,789.9-14,459.0 | 1.43 | yes | 2.783x | 1.779x | 0.639x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x147-romfill` | 6,947.7 | 7,828.9-14,531.5 | 3.76 | yes | `b200_sxm-x75-nvl72-hybrid` | 2,322.4 | 4,783.5-8,878.7 | 2.06 | yes | 2.992x | 1.637x | 0.547x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 6,327.0 | 11,239.0-20,861.1 | 2.39 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,588.6 | 6,747.5-12,524.2 | 1.63 | yes | 2.444x | 1.666x | 0.681x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 6,794.8 | 7,687.7-14,269.3 | 3.75 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,328.9 | 5,527.0-10,258.8 | 1.79 | yes | 2.918x | 1.391x | 0.477x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 5,084.2 | 9,657.5-17,925.6 | 2.23 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,467.4 | 5,061.1-9,394.0 | 2.07 | yes | 2.061x | 1.908x | 0.926x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 5,997.7 | 6,289.8-11,674.7 | 4.04 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,086.3 | 3,846.1-7,138.8 | 2.30 | yes | 2.875x | 1.635x | 0.569x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,578.6 | 7,889.6-14,644.2 | 1.92 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,271.2 | 4,935.6-9,161.1 | 1.95 | yes | 1.576x | 1.599x | 1.015x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3,204.0 | 2,846.3-5,283.1 | 4.77 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,340.8 | 2,074.8-3,851.0 | 2.74 | yes | 2.390x | 1.372x | 0.574x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,226.9 | 3,775.0-7,007.0 | 1.38 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,676.9 | 3,043.3-5,648.7 | 2.34 | yes | 0.732x | 1.240x | 1.695x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 832.2 | 714.6-1,326.3 | 4.94 | yes | `b200_sxm-x173-nvl72-hybrid` | 591.8 | 1,001.4-1,858.8 | 2.51 | yes | 1.406x | 0.714x | 0.507x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 331.1 | 1,197.2-2,222.2 | 1.17 | yes | `b200_sxm-x347-nvl72-hybrid` | 913.1 | 1,684.9-3,127.5 | 2.30 | yes | 0.363x | 0.711x | 1.960x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 208.3 | 178.7-331.7 | 4.94 | yes | `b200_sxm-x173-nvl72-hybrid` | 192.6 | 431.3-800.5 | 1.89 | yes | 1.081x | 0.414x | 0.383x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 84.0 | 208.4-386.9 | 1.71 | yes | `b200_sxm-x347-nvl72-hybrid` | 349.1 | 810.1-1,503.6 | 1.83 | yes | 0.241x | 0.257x | 1.070x |

**Does the ratio compress?** Of 20 class rows in this study, 16 move the ROM-versus-GPU ratio DOWN under speculation and 4 move it UP. The movement spans 0.196x to 1.960x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 20 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-hw-hybrid-x8-romfill` | 9,483.0 | 6,102.6-11,327.2 | 6.59 | yes | `a100_sxm_80gb-x8-tensor` | 1,063.1 | 3,516.5-6,527.1 | 1.28 | yes | 8.920x | 1.735x | 0.195x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 9,155.9 | 14,641.5-27,176.6 | 2.65 | yes | `a100_sxm_80gb-x56-hybrid` | 1,045.1 | 3,365.1-6,246.0 | 1.32 | yes | 8.761x | 4.351x | 0.497x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x207-romfill` | 5,414.9 | 7,228.1-13,416.3 | 3.18 | yes | `a100_sxm_80gb-x204-hybrid` | 990.7 | 2,957.8-5,490.1 | 1.42 | yes | 5.466x | 2.444x | 0.447x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,409.8 | 11,210.3-20,807.8 | 2.05 | yes | `a100_sxm_80gb-x448-hybrid` | 975.4 | 2,806.0-5,208.4 | 1.47 | yes | 5.546x | 3.995x | 0.720x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x207-romfill` | 5,414.9 | 7,228.1-13,416.3 | 3.18 | yes | `a100_sxm_80gb-x204-hybrid` | 990.7 | 2,957.8-5,490.1 | 1.42 | yes | 5.466x | 2.444x | 0.447x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,360.6 | 11,857.6-22,009.3 | 1.92 | yes | `a100_sxm_80gb-x448-hybrid` | 975.4 | 2,806.0-5,208.4 | 1.47 | yes | 5.496x | 4.226x | 0.769x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x207-romfill` | 5,414.9 | 7,228.1-13,416.3 | 3.18 | yes | `a100_sxm_80gb-x204-hybrid` | 990.7 | 2,957.8-5,490.1 | 1.42 | yes | 5.466x | 2.444x | 0.447x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,360.6 | 11,857.6-22,009.3 | 1.92 | yes | `a100_sxm_80gb-x448-hybrid` | 975.4 | 2,806.0-5,208.4 | 1.47 | yes | 5.496x | 4.226x | 0.769x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 5,333.5 | 7,133.5-13,240.7 | 3.17 | yes | `a100_sxm_80gb-x272-hybrid` | 979.9 | 2,838.6-5,268.7 | 1.46 | yes | 5.443x | 2.513x | 0.462x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 4,446.1 | 9,504.5-17,641.6 | 1.98 | yes | `a100_sxm_80gb-x672-hybrid` | 975.4 | 2,806.0-5,208.4 | 1.47 | yes | 4.558x | 3.387x | 0.743x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4,977.3 | 6,887.3-12,783.7 | 3.06 | yes | `a100_sxm_80gb-x335-hybrid` | 974.3 | 2,803.5-5,203.6 | 1.47 | yes | 5.109x | 2.457x | 0.481x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,025.7 | 7,351.4-13,645.1 | 1.75 | yes | `a100_sxm_80gb-x672-hybrid` | 975.4 | 2,806.0-5,208.4 | 1.47 | yes | 3.102x | 2.620x | 0.845x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3,884.8 | 4,838.5-8,980.9 | 3.40 | yes | `a100_sxm_80gb-x335-hybrid` | 922.5 | 2,423.7-4,498.7 | 1.61 | yes | 4.211x | 1.996x | 0.474x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,827.8 | 5,215.7-9,681.1 | 1.49 | yes | `a100_sxm_80gb-x672-hybrid` | 975.4 | 2,806.0-5,208.4 | 1.47 | yes | 1.874x | 1.859x | 0.992x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 1,571.3 | 2,270.5-4,214.4 | 2.93 | yes | `a100_sxm_80gb-x335-hybrid` | 630.0 | 963.2-1,787.9 | 2.77 | yes | 2.494x | 2.357x | 0.945x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 529.7 | 1,905.4-3,536.7 | 1.18 | yes | `a100_sxm_80gb-x672-hybrid` | 800.0 | 1,664.9-3,090.4 | 2.04 | yes | 0.662x | 1.144x | 1.728x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 429.3 | 631.7-1,172.6 | 2.88 | yes | `a100_sxm_80gb-x335-hybrid` | 277.8 | 273.2-507.1 | 4.31 | yes | 1.545x | 2.312x | 1.496x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 136.7 | 533.3-989.9 | 1.09 | yes | `a100_sxm_80gb-x672-hybrid` | 443.7 | 523.6-971.8 | 3.59 | yes | 0.308x | 1.019x | 3.307x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340` | 110.7 | 211.3-392.2 | 2.22 | yes | `a100_sxm_80gb-x335-hybrid` | 93.0 | 115.7-214.8 | 3.41 | yes | 1.191x | 1.826x | 1.533x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12` | 34.4 | 72.7-134.9 | 2.00 | yes | `a100_sxm_80gb-x672-hybrid` | 167.3 | 227.5-422.3 | 3.12 | yes | 0.205x | 0.320x | 1.555x |

**Does the ratio compress?** Of 20 class rows in this study, 15 move the ROM-versus-GPU ratio DOWN under speculation and 5 move it UP. The movement spans 0.195x to 3.307x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 20 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

## Where the drafter lives on a ROM machine

The locality rule -- `stored/peak` is a technology constant -- is the load-bearing assumption of the whole ROM verdict. A pass that reads only the drafter's region uses only that region's read ports and takes exactly as long as sweeping the entire array. Two placements are therefore priced side by side, and the second is an architectural proposal this study **has not costed in silicon area**.

The same rule is what makes a SEQUENTIAL draft step expensive here. A per-position operation that moves only a small table is nearly free on a global-bandwidth store and costs a full array sweep on this one, so a drafter with `gamma` sequential applications pays `gamma` sweeps for them. That term is charged in full below; on a bandwidth store the bytes it moves are not separately charged at all, because this repository's model configs carry no size for the table -- an omission whose size, on DeepSeek-V4-Pro-0813, is the externally published 132,382,720 B per draft token, 0.33% of the 39,666,603,980 B target pass.

| study | model | ctx | batch | class | design | tau* draft in ROM | tau* draft in KV store | KV placement feasible | why not |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 14.71 | 57.88 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 9.54 | 234.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 14.71 | 57.88 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 9.54 | 234.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 14.71 | 57.88 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 9.54 | 234.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 14.71 | 57.88 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 9.54 | 234.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 14.71 | 57.88 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 9.54 | 234.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x183` | 14.71 | 57.88 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 10.71 | 222.39 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x185` | 26.39 | 111.40 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 10.75 | 223.54 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 29.03 | 87.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 19.08 | 358.63 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 23.27 | 52.54 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 37.50 | 733.25 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 26.77 | 44.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 14.48 | 66.94 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 18.43 | 126.95 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 12.44 | 534.16 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 18.43 | 126.95 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 12.44 | 534.16 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 18.43 | 126.95 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 12.44 | 534.16 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 18.43 | 126.95 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 12.44 | 534.16 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 18.43 | 126.95 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 12.44 | 534.16 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 18.43 | 126.95 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 13.52 | 512.33 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 18.43 | 126.95 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 13.58 | 514.86 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 28.88 | 190.25 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 22.91 | 766.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 32.03 | 162.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 19.35 | 355.18 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 27.66 | 57.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 19.13 | 261.15 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 16.38 | 55.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.55 | 105.45 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 16.38 | 55.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.55 | 105.45 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 16.38 | 55.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.55 | 105.45 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 16.38 | 55.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.55 | 105.45 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 16.38 | 55.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.55 | 105.45 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 16.38 | 55.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 8.01 | 102.10 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 15.27 | 53.67 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 13.08 | 195.17 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 26.73 | 78.36 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 20.03 | 266.31 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 31.27 | 78.16 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 22.75 | 217.79 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 26.12 | 34.70 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 16.30 | 127.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 11.40 | 60.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 11.39 | 120.80 | NO | the KV store has no room for it |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 11.40 | 60.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 6.28 | 114.68 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 11.40 | 60.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 6.28 | 114.68 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 11.40 | 60.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 6.28 | 114.68 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 11.40 | 60.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 6.28 | 114.68 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 11.40 | 60.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 9.74 | 216.77 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 20.02 | 117.10 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 9.39 | 187.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 31.40 | 161.20 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 16.06 | 390.99 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 32.17 | 118.64 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 19.87 | 495.90 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 27.14 | 44.29 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 8.54 | 133.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 25.65 | 114.67 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 8.67 | 240.21 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 25.65 | 114.67 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 8.67 | 240.21 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 25.65 | 114.67 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 8.67 | 240.21 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 25.65 | 114.67 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 8.67 | 240.21 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 25.65 | 114.67 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 8.67 | 240.21 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 25.65 | 114.67 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 9.78 | 228.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 25.65 | 114.67 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.82 | 229.22 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 27.96 | 93.20 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 17.97 | 381.37 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 22.55 | 53.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 37.96 | 829.14 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 27.11 | 46.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 29.99 | 274.35 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 17.65 | 128.83 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 11.41 | 552.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 17.65 | 128.83 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 11.41 | 552.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 17.65 | 128.83 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 11.41 | 552.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 17.65 | 128.83 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 11.41 | 552.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 17.65 | 128.83 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 11.41 | 552.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 17.65 | 128.83 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 12.45 | 530.82 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 17.41 | 125.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 12.50 | 533.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 28.43 | 193.84 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 21.91 | 827.31 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 31.98 | 180.16 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 41.08 | 1,576.63 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 27.92 | 63.19 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 19.73 | 160.78 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 8.96 | 5.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 5.89 | 3.47 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 8.96 | 5.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.98 | 7.28 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 8.96 | 5.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.98 | 7.28 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 8.96 | 5.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.98 | 7.28 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 8.96 | 5.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5.90 | 7.17 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 15.54 | 9.35 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5.79 | 7.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8.85 | 5.98 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.81 | 7.04 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 15.52 | 10.82 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.79 | 11.87 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 19.43 | 15.44 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 20.39 | 25.21 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.73 | 16.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 18.19 | 19.78 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 11.08 | 7.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 7.44 | 4.10 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 11.08 | 7.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.12 | 12.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 11.08 | 7.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.12 | 12.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 11.08 | 7.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.12 | 12.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 11.08 | 7.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.12 | 12.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 11.08 | 7.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 6.98 | 12.06 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 10.67 | 7.74 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.00 | 12.11 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 17.89 | 13.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 11.50 | 19.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 20.43 | 17.06 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 21.02 | 36.84 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 16.35 | 14.12 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 17.27 | 22.09 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 10.09 | 6.55 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 6.56 | 4.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 10.09 | 6.55 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.26 | 4.50 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 10.09 | 6.55 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.26 | 4.50 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 10.09 | 6.55 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.26 | 4.50 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 10.09 | 6.55 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 6.26 | 4.50 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x113` | 10.25 | 6.75 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.41 | 4.95 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9.59 | 6.98 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.11 | 7.15 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 15.83 | 12.06 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 8.85 | 10.26 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 18.72 | 15.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 12.71 | 15.00 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 15.07 | 12.93 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 10.06 | 6.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 7.37 | 5.41 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | 5.01 | 3.42 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 7.37 | 5.41 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 5.06 | 4.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 7.37 | 5.41 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 5.06 | 4.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 7.37 | 5.41 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 5.06 | 4.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 7.37 | 5.41 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 6.14 | 4.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156` | 12.10 | 8.33 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 9.30 | 5.82 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 11.37 | 8.76 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 9.13 | 6.04 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 17.62 | 14.18 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 15.37 | 8.89 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 19.13 | 13.65 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 18.82 | 10.65 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340` | 19.98 | 16.35 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 7.32 | 5.18 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 15.16 | 9.09 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.59 | 6.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 15.16 | 9.09 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.59 | 6.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 15.16 | 9.09 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.59 | 6.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 15.16 | 9.09 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.59 | 6.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 15.16 | 9.09 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5.51 | 6.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 15.16 | 9.09 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5.40 | 6.66 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 15.13 | 9.10 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.42 | 6.68 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 15.41 | 10.40 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.48 | 11.71 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 19.73 | 15.24 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 21.26 | 26.73 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.83 | 16.52 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 18.95 | 20.82 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 10.49 | 7.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 6.75 | 12.27 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 10.49 | 7.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 6.75 | 12.27 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 10.49 | 7.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 6.75 | 12.27 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 10.49 | 7.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 6.75 | 12.27 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 10.49 | 7.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 6.75 | 12.27 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 10.49 | 7.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 6.60 | 11.93 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 10.45 | 7.43 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 6.62 | 11.98 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.01 | 13.25 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 11.56 | 20.43 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 20.85 | 17.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 23.69 | 42.91 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 18.56 | 16.72 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 19.50 | 25.57 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 8.96 | 5.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.98 | 7.28 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 8.96 | 5.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.98 | 7.28 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 8.96 | 5.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.98 | 7.28 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 8.96 | 5.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.98 | 7.28 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 8.96 | 5.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5.90 | 7.17 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 15.54 | 9.35 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5.79 | 7.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8.85 | 5.98 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.81 | 7.04 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 15.52 | 10.82 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.79 | 11.87 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 19.43 | 15.44 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 20.39 | 25.21 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.73 | 16.59 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 18.19 | 19.78 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 11.08 | 7.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.12 | 12.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 11.08 | 7.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.12 | 12.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 11.08 | 7.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.12 | 12.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 11.08 | 7.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.12 | 12.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 11.08 | 7.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 7.12 | 12.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 11.08 | 7.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 6.98 | 12.06 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 10.67 | 7.74 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.00 | 12.11 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 17.89 | 13.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 11.50 | 19.49 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 20.43 | 17.06 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 21.03 | 36.84 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 16.35 | 14.12 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 17.28 | 22.10 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | 9.11 | 9.33 | NO | the KV store has no room for it |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 5.08 | 5.20 | NO | the KV store has no room for it |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 6.62 | 6.29 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 4.39 | 4.06 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 6.62 | 6.29 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 4.39 | 4.06 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 6.62 | 6.29 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 4.39 | 4.06 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 10.03 | 9.42 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 4.39 | 4.06 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 10.87 | 10.35 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 5.76 | 5.24 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 14.38 | 13.60 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 7.85 | 7.01 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 17.60 | 16.59 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 11.30 | 9.94 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 17.53 | 17.05 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 12.65 | 11.11 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 17.14 | 17.10 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 9.07 | 8.67 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x398` | 8.72 | 8.81 | NO | the KV store has no room for it |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x10` | 5.79 | 5.95 | NO | the KV store has no room for it |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 6.93 | 6.90 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 4.41 | 4.69 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 6.93 | 6.90 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 4.41 | 4.69 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 10.41 | 10.35 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 4.41 | 4.69 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 11.15 | 11.12 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 4.41 | 4.69 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 14.18 | 14.14 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 5.37 | 5.79 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 16.03 | 15.99 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 5.50 | 5.81 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 17.20 | 17.15 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 6.32 | 6.76 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 17.20 | 17.20 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 6.65 | 7.12 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 17.14 | 17.14 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x22` | 5.74 | 5.98 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x383` | 6.43 | 6.41 | NO | the KV store has no room for it |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | 7.34 | 6.57 | NO | the KV store has no room for it |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3.26 | 2.63 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3.26 | 2.63 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3.26 | 2.63 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3.26 | 2.63 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 4.49 | 3.23 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 7.02 | 4.53 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 10.27 | 6.23 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 11.78 | 7.06 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x68` | 12.19 | 7.30 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x399` | 10.36 | 10.36 | NO | the KV store has no room for it |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x23` | 8.83 | 7.98 | NO | the KV store has no room for it |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 3.42 | 2.76 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 3.42 | 2.76 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 3.42 | 2.76 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 3.42 | 2.76 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 3.59 | 3.01 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 4.46 | 3.51 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 5.77 | 4.32 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 6.13 | 4.51 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 6.25 | 4.59 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 10.28 | 8.28 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 6.62 | 7.84 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 10.28 | 8.28 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 6.62 | 7.84 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 10.28 | 8.28 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 6.62 | 7.84 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 10.28 | 8.28 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 6.62 | 7.84 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 10.28 | 8.28 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 6.62 | 7.84 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 10.28 | 8.28 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.50 | 7.52 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 10.83 | 9.06 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.36 | 11.14 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 19.32 | 15.33 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 13.19 | 12.67 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 19.45 | 16.94 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 16.35 | 19.15 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 17.66 | 17.00 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 10.58 | 10.39 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 9.24 | 8.88 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3.95 | 5.04 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 9.24 | 8.88 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3.95 | 5.04 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 9.24 | 8.88 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3.95 | 5.04 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 9.24 | 8.88 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3.95 | 5.04 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 9.24 | 8.88 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 5.30 | 7.30 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 10.09 | 9.76 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.30 | 10.77 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 13.75 | 13.22 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.63 | 10.42 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 17.86 | 17.08 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 10.69 | 15.35 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 17.76 | 17.34 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 12.04 | 17.37 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 17.20 | 17.10 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 9.14 | 10.50 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | 8.24 | 7.61 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 3.03 | 2.89 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 4.67 | 3.44 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.65 | 2.27 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 4.67 | 3.44 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.65 | 2.27 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 4.67 | 3.44 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.65 | 2.27 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x282` | 5.36 | 3.40 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.65 | 2.27 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 8.89 | 3.89 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.31 | 2.35 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 8.39 | 4.17 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.44 | 2.11 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 8.25 | 7.87 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.71 | 1.68 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 7.53 | 7.44 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.85 | 1.65 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 7.47 | 7.47 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x22` | 2.95 | 1.33 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x61` | 9.17 | 8.41 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 3.48 | 3.37 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 3.56 | 2.74 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2.73 | 2.10 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 3.56 | 2.74 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2.73 | 2.10 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 3.56 | 2.74 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 2.73 | 2.10 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4.83 | 2.97 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3.19 | 2.10 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4.75 | 3.12 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3.81 | 2.13 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 5.43 | 3.03 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3.81 | 1.98 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 6.21 | 3.11 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 4.06 | 1.89 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 4.40 | 2.78 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 4.14 | 1.90 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 2.91 | 2.50 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x31` | 2.58 | 1.45 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 7.42 | 6.84 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 5.39 | 4.77 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 4.06 | 1.69 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 4.06 | 1.69 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 4.06 | 1.69 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 4.06 | 1.69 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 3.97 | 1.74 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 4.73 | 1.50 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5.45 | 1.21 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5.73 | 1.17 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5.79 | 1.16 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | 8.26 | 7.58 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 4.64 | 4.41 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 3.54 | 1.47 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 3.54 | 1.47 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 3.54 | 1.47 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 3.54 | 1.47 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 3.54 | 1.47 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 2.99 | 1.50 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 3.10 | 1.17 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 2.92 | 1.12 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 2.93 | 1.11 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 7.86 | 6.72 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4.90 | 6.52 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 7.86 | 6.72 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4.90 | 6.52 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 7.86 | 6.72 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4.90 | 6.52 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 7.86 | 6.72 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4.90 | 6.52 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill` | 7.91 | 6.76 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 3.94 | 6.42 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 7.74 | 6.63 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.87 | 6.25 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7.66 | 6.57 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.95 | 9.56 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 13.98 | 12.21 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.60 | 12.85 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.93 | 16.48 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 8.47 | 18.22 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.28 | 16.87 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 6.84 | 9.57 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 9.59 | 10.00 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.32 | 6.43 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 9.59 | 10.00 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.32 | 6.43 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 9.59 | 10.00 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.32 | 6.43 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 9.59 | 10.00 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 4.32 | 6.43 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 9.59 | 10.00 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.21 | 6.18 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 9.30 | 9.53 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.83 | 9.47 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 9.23 | 9.46 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4.54 | 13.98 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 15.99 | 16.32 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4.93 | 14.75 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 18.82 | 19.07 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 5.22 | 17.37 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.52 | 17.59 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 3.97 | 7.16 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | 6.55 | 5.96 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 4.50 | 3.84 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2.98 | 2.04 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2.98 | 2.04 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 2.98 | 2.04 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 3.71 | 2.00 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 5.06 | 1.98 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 4.65 | 2.02 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 5.00 | 1.58 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 5.26 | 1.49 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x49` | 5.32 | 1.49 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | 7.80 | 7.06 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 4.40 | 4.08 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 2.88 | 1.97 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 2.88 | 1.97 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 2.88 | 1.97 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 2.88 | 1.97 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3.36 | 1.88 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3.97 | 1.81 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 4.24 | 1.67 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 4.37 | 1.67 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x68` | 4.40 | 1.67 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | 5.61 | 4.99 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 4.96 | 4.55 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 4.50 | 1.54 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 4.50 | 1.54 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 4.50 | 1.54 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 4.50 | 1.54 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 4.50 | 1.54 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 4.43 | 1.55 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 6.21 | 1.20 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 6.17 | 1.14 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 6.28 | 1.12 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x340` | 7.61 | 7.10 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 5.74 | 5.14 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.73 | 1.33 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.73 | 1.33 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.73 | 1.33 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.73 | 1.33 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.73 | 1.33 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.73 | 1.33 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.21 | 1.18 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.10 | 1.10 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.12 | 1.09 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 7.39 | 5.76 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.12 | 6.57 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 7.39 | 5.76 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.12 | 6.57 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 7.39 | 5.76 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.12 | 6.57 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 7.39 | 5.76 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.12 | 6.57 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 7.39 | 5.76 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 5.07 | 6.63 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 7.11 | 5.25 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.98 | 6.49 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 11.29 | 7.77 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.78 | 9.47 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 18.66 | 13.20 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.15 | 12.43 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x392-romfill` | 20.67 | 16.71 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 12.00 | 16.59 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 16.91 | 15.86 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 9.47 | 6.38 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 8.85 | 7.43 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 4.02 | 6.12 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 8.85 | 7.43 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 4.02 | 6.12 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 8.85 | 7.43 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 4.02 | 6.12 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 8.85 | 7.43 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 4.02 | 6.12 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 8.85 | 7.43 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 5.57 | 5.91 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 8.54 | 6.81 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.79 | 8.39 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 9.41 | 7.80 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.34 | 7.84 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 20.88 | 16.55 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 10.18 | 11.05 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 18.98 | 15.27 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 11.53 | 12.53 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 19.87 | 17.54 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 4.85 | 5.11 | yes | -- |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340-romfill` | 7.92 | 7.92 | NO | the KV store has no room for it |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 3.30 | 3.30 | NO | the KV store has no room for it |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x308-romfill` | 8.12 | 8.12 | NO | the KV store has no room for it |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 4.24 | 4.24 | NO | the KV store has no room for it |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x60-romfill` | 7.17 | 7.17 | NO | the KV store has no room for it |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 2.98 | 2.98 | NO | the KV store has no room for it |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.53 | 1.58 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.53 | 1.58 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.53 | 1.58 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.53 | 1.58 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.53 | 1.58 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.62 | 1.65 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.11 | 1.20 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.04 | 1.13 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.02 | 1.11 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 5.12 | 5.12 | NO | the KV store has no room for it |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 3.18 | 3.18 | NO | the KV store has no room for it |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196-romfill` | 1.88 | 1.88 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 2.50 | 2.44 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.29 | 1.37 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.29 | 1.37 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.29 | 1.37 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.30 | 1.36 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.09 | 1.16 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.03 | 1.09 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.01 | 1.08 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 15.14 | 10.06 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 4.51 | 3.43 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.81 | 10.09 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.55 | 2.61 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.81 | 10.09 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.55 | 2.61 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.81 | 10.09 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.55 | 2.61 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.81 | 10.09 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.55 | 2.61 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.81 | 10.09 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.55 | 2.61 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.81 | 10.09 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.88 | 2.97 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349-romfill` | 14.15 | 13.11 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 3.77 | 4.00 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 15.41 | 11.66 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 8.08 | 2.60 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 12.55 | 11.66 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 8.33 | 2.26 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 9.75 | 6.81 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.64 | 6.81 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 9.75 | 6.81 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.64 | 6.81 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 9.75 | 6.81 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.64 | 6.81 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 9.75 | 6.81 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.64 | 6.81 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 9.75 | 6.81 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.64 | 6.81 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x116-romfill` | 9.57 | 6.84 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 5.57 | 6.72 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 9.57 | 6.84 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5.57 | 6.72 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.51 | 8.17 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 8.84 | 10.96 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.04 | 13.66 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 14.54 | 17.46 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.73 | 16.00 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 16.01 | 17.11 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 9.34 | 6.53 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.37 | 6.55 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 9.34 | 6.53 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.37 | 6.55 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 9.34 | 6.53 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.37 | 6.55 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 9.34 | 6.53 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.37 | 6.55 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 9.34 | 6.53 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5.37 | 6.55 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x116-romfill` | 9.31 | 6.54 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 5.30 | 6.45 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 9.31 | 6.54 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5.30 | 6.45 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 14.67 | 9.83 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 8.63 | 10.82 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 15.99 | 13.44 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 14.53 | 17.65 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.71 | 15.91 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 16.08 | 17.29 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 10.93 | 6.67 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 4.20 | 3.61 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 10.93 | 6.67 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.11 | 3.67 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 10.93 | 6.67 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.11 | 3.67 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 10.93 | 6.67 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.11 | 3.67 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 10.93 | 6.67 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.11 | 3.67 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 10.93 | 6.67 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.11 | 3.67 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 10.93 | 6.67 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 6.03 | 5.20 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 18.31 | 10.52 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.95 | 8.72 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 21.35 | 15.00 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 16.85 | 14.63 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 18.25 | 16.45 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 11.93 | 7.97 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 9.92 | 6.01 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.82 | 3.35 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 9.92 | 6.01 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.82 | 3.35 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 9.92 | 6.01 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.82 | 3.35 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 9.92 | 6.01 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.82 | 3.35 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 9.92 | 6.01 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.82 | 3.35 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 9.92 | 6.01 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.80 | 3.34 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 9.92 | 6.01 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.90 | 4.98 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 17.26 | 8.99 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 10.49 | 8.97 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 22.42 | 14.50 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 21.84 | 18.48 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 18.61 | 16.29 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 13.47 | 11.49 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 10.10 | 6.08 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.79 | 3.30 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 10.10 | 6.08 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.79 | 3.30 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 10.10 | 6.08 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.79 | 3.30 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 10.10 | 6.08 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.79 | 3.30 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 10.10 | 6.08 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3.79 | 3.30 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 10.10 | 6.08 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 6.04 | 5.08 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 10.10 | 6.08 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.01 | 5.05 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 17.60 | 10.11 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 10.68 | 9.09 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 22.63 | 14.40 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 22.01 | 18.53 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 18.68 | 16.25 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 14.53 | 13.49 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x170` | 17.59 | 11.07 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 5.11 | 3.65 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 10.56 | 7.46 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.20 | 2.25 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 10.56 | 7.46 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.20 | 2.25 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 10.56 | 7.46 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.20 | 2.25 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 10.56 | 7.46 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.20 | 2.25 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 10.56 | 7.46 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.20 | 2.25 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 11.04 | 10.38 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.13 | 2.49 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 16.05 | 7.81 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 9.38 | 2.17 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 13.24 | 8.22 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 11.02 | 1.91 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 9.54 | 8.23 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 11.57 | 1.94 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 11.57 | 8.53 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5.07 | 6.47 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 11.57 | 8.53 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5.07 | 6.47 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 11.57 | 8.53 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5.07 | 6.47 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 11.57 | 8.53 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5.07 | 6.47 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 11.57 | 8.53 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 4.53 | 6.85 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 11.57 | 8.53 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4.46 | 6.71 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 11.51 | 8.84 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4.47 | 6.73 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 12.38 | 10.14 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.15 | 10.88 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.19 | 15.17 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 13.14 | 21.25 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.08 | 16.48 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 12.36 | 14.95 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 11.38 | 8.62 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4.44 | 6.96 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 11.38 | 8.62 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4.44 | 6.96 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 11.38 | 8.62 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4.44 | 6.96 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 11.38 | 8.62 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4.44 | 6.96 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 11.38 | 8.62 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 4.39 | 6.85 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | 11.38 | 8.62 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4.31 | 6.69 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 11.36 | 8.61 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4.32 | 6.71 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 12.22 | 9.89 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.45 | 11.69 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.21 | 15.04 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 16.63 | 27.53 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.08 | 16.44 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 16.89 | 20.75 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 12.74 | 8.13 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 4.90 | 4.06 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 12.74 | 8.13 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3.99 | 3.09 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 12.74 | 8.13 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3.99 | 3.09 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 12.74 | 8.13 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3.99 | 3.09 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 12.74 | 8.13 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3.99 | 3.09 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 12.74 | 8.13 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 5.89 | 4.13 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 12.74 | 8.13 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 5.92 | 4.28 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 19.34 | 12.29 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 11.14 | 7.25 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 21.19 | 16.02 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 15.24 | 9.71 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 18.16 | 16.74 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 7.41 | 5.91 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 12.16 | 7.11 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.71 | 5.03 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 12.16 | 7.11 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.71 | 5.03 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 12.16 | 7.11 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.71 | 5.03 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 12.16 | 7.11 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.71 | 5.03 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 12.16 | 7.11 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.71 | 5.03 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 12.16 | 7.11 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4.65 | 4.93 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 12.16 | 7.11 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.38 | 7.92 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 19.74 | 11.58 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 12.72 | 13.56 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 22.23 | 15.77 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 15.74 | 13.31 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 18.49 | 16.67 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 18.32 | 16.51 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 12.32 | 7.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.66 | 4.99 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 12.32 | 7.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.66 | 4.99 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 12.32 | 7.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.66 | 4.99 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 12.32 | 7.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.66 | 4.99 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 12.32 | 7.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.66 | 4.99 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 12.32 | 7.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4.59 | 4.88 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 12.32 | 7.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 7.60 | 8.18 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 19.82 | 11.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 12.98 | 13.86 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 22.43 | 15.72 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 14.16 | 12.86 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 18.55 | 16.65 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 17.35 | 16.35 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x8-romfill` | 5.81 | 5.81 | NO | the KV store has no room for it |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 2.86 | 3.00 | NO | the KV store has no room for it |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 5.39 | 5.55 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 2.40 | 3.01 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 5.39 | 5.55 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 2.40 | 3.01 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 5.39 | 5.55 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2.40 | 3.00 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x147-romfill` | 5.35 | 5.51 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.33 | 3.28 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5.26 | 5.41 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.52 | 3.24 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7.00 | 7.26 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.32 | 3.32 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9.64 | 9.64 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.87 | 3.21 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9.88 | 9.88 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1.71 | 3.13 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.18 | 10.18 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1.75 | 1.89 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 10.56 | 8.11 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 5.11 | 3.62 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 10.82 | 7.64 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3.22 | 3.47 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 10.82 | 7.64 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3.22 | 3.47 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 10.82 | 7.64 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3.22 | 3.47 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 10.82 | 7.64 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 3.22 | 3.47 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x70` | 10.80 | 7.03 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.21 | 3.46 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 10.55 | 8.22 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.09 | 4.56 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 11.60 | 9.69 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.79 | 6.45 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.28 | 14.62 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 7.81 | 8.93 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.83 | 16.38 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 6.33 | 4.59 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340` | 13.08 | 9.67 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 5.19 | 3.64 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 13.74 | 9.56 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 5.06 | 2.25 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 13.74 | 9.56 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 5.06 | 2.25 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 13.74 | 9.56 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 5.06 | 2.25 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 13.74 | 9.56 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 5.06 | 2.25 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 13.74 | 9.56 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 5.06 | 2.25 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 13.74 | 9.56 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3.29 | 3.12 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 19.04 | 12.24 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 10.85 | 3.04 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 20.58 | 15.73 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 17.10 | 3.44 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 17.99 | 16.67 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 20.02 | 3.82 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x16-romfill` | 6.64 | 6.64 | NO | the KV store has no room for it |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 2.99 | 3.10 | NO | the KV store has no room for it |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill` | 4.05 | 4.42 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.98 | 3.12 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill` | 4.05 | 4.42 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.98 | 3.12 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill` | 4.05 | 4.42 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.98 | 3.12 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4.06 | 4.44 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.05 | 2.97 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4.74 | 5.42 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.83 | 2.97 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 5.46 | 5.79 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.58 | 2.92 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6.47 | 6.97 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.27 | 2.80 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 6.87 | 6.87 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1.18 | 2.75 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 3.68 | 3.40 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 2.00 | 1.44 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | 12.55 | 9.40 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 5.45 | 3.96 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 12.92 | 9.54 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 4.39 | 2.88 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 12.92 | 9.54 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 4.39 | 2.88 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 12.92 | 9.54 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 4.39 | 2.88 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 12.92 | 9.54 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 4.39 | 2.88 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 12.92 | 9.54 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 6.40 | 3.50 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 8.27 | 7.16 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.08 | 3.75 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 13.19 | 11.42 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.55 | 4.01 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.08 | 15.69 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 8.30 | 3.70 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 14.79 | 13.14 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 5.35 | 2.90 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 10.86 | 9.06 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 6.27 | 4.10 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.71 | 2.36 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.71 | 2.36 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.71 | 2.36 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.71 | 2.36 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.71 | 2.36 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.71 | 2.36 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 10.59 | 2.67 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 14.60 | 3.01 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 16.08 | 3.20 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 6.03 | 6.03 | NO | the KV store has no room for it |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 2.59 | 2.62 | NO | the KV store has no room for it |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 3.77 | 3.77 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 2.24 | 2.40 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 3.77 | 3.77 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 2.24 | 2.40 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 3.77 | 3.77 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 2.24 | 2.39 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x147-romfill` | 3.76 | 3.76 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 2.39 | 2.51 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3.75 | 3.75 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 2.23 | 2.41 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4.04 | 4.04 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.92 | 2.17 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4.77 | 4.77 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.38 | 1.71 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4.94 | 4.94 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 1.17 | 1.53 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4.94 | 4.94 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 1.71 | 1.14 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-hw-hybrid-x8-romfill` | 6.59 | 6.59 | NO | the KV store has no room for it |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 2.65 | 2.67 | NO | the KV store has no room for it |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x207-romfill` | 3.18 | 3.25 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 2.05 | 2.12 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x207-romfill` | 3.18 | 3.25 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 1.92 | 2.21 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x207-romfill` | 3.18 | 3.25 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 1.92 | 2.21 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 3.17 | 3.24 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.98 | 2.22 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3.06 | 3.20 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.75 | 2.03 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3.40 | 3.43 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.49 | 1.83 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 2.93 | 2.98 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.18 | 1.57 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 2.88 | 2.88 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 1.09 | 1.49 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340` | 2.22 | 1.60 | yes | -- |
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
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | no | 850,275,640 | 116.6 | 0.0% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | no | 850,275,640 | 90.7 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | no | 850,275,640 | 90.7 | 0.1% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | no | 850,275,640 | 90.7 | 0.0% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
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
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | no | 11,706,065,920 | 1,248.0 | 0.4% | 1.0075x |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | no | 11,706,065,920 | 1,248.0 | 0.4% | 1.0075x |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x398` | no | 11,706,065,920 | 1,604.6 | 0.5% | 1.0075x |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `ROM-N6-native-SRAMKV-wafer-hybrid-x10` | no | 11,706,065,920 | 1,604.6 | 0.3% | 1.0075x |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x383` | no | 11,706,065,920 | 1,248.0 | 0.4% | 1.0075x |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | no | 11,706,065,920 | 1,248.0 | 0.1% | 1.0075x |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x399` | no | 11,706,065,920 | 1,604.6 | 0.5% | 1.0075x |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `ROM-N6-native-SRAMKV-wafer-hybrid-x23` | no | 11,706,065,920 | 1,604.6 | 0.2% | 1.0075x |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | no | 11,706,065,920 | 1,248.0 | 0.4% | 1.0075x |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | no | 11,706,065,920 | 1,248.0 | 0.4% | 1.0075x |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | no | 11,706,065,920 | 1,604.6 | 0.5% | 1.0075x |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | no | 11,706,065,920 | 1,604.6 | 0.3% | 1.0075x |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | no | 1,620,446,720 | 172.8 | 0.5% | 1.0094x |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | no | 1,620,446,720 | 172.8 | 0.4% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x61` | no | 1,620,446,720 | 222.1 | 0.4% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | no | 1,620,446,720 | 222.1 | 0.5% | 1.0094x |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | no | 1,620,446,720 | 172.8 | 0.2% | 1.0094x |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | no | 1,620,446,720 | 172.8 | 0.2% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | no | 1,620,446,720 | 222.1 | 0.2% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | no | 1,620,446,720 | 222.1 | 0.2% | 1.0094x |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | no | 1,620,446,720 | 172.8 | 0.4% | 1.0094x |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | no | 1,620,446,720 | 172.8 | 0.2% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | no | 1,620,446,720 | 222.1 | 0.4% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | no | 1,620,446,720 | 222.1 | 0.1% | 1.0094x |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | no | 3,350,899,200 | 357.3 | 0.3% | 1.0059x |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | no | 3,350,899,200 | 357.3 | 0.3% | 1.0059x |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | no | 3,350,899,200 | 459.3 | 0.3% | 1.0059x |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | no | 3,350,899,200 | 459.3 | 0.3% | 1.0059x |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | no | 3,350,899,200 | 357.3 | 0.1% | 1.0059x |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | no | 3,350,899,200 | 357.3 | 0.2% | 1.0059x |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-hybrid-x340` | no | 3,350,899,200 | 459.3 | 0.2% | 1.0059x |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | no | 3,350,899,200 | 459.3 | 0.2% | 1.0059x |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | no | 3,350,899,200 | 357.3 | 0.3% | 1.0059x |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | no | 3,350,899,200 | 357.3 | 0.3% | 1.0059x |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | no | 3,350,899,200 | 459.3 | 0.3% | 1.0059x |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | no | 3,350,899,200 | 459.3 | 0.2% | 1.0059x |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340-romfill` | no | 1,929,464,320 | 205.7 | 0.1% | 1.1178x |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | no | 1,929,464,320 | 205.7 | 0.2% | 1.1178x |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-hybrid-x308-romfill` | no | 1,929,464,320 | 264.5 | 0.1% | 1.1178x |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | no | 1,929,464,320 | 264.5 | 0.3% | 1.1178x |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-hybrid-x60-romfill` | no | 1,929,464,320 | 205.7 | 0.4% | 1.1178x |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | no | 1,929,464,320 | 205.7 | 0.4% | 1.1178x |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | no | 1,929,464,320 | 264.5 | 0.6% | 1.1178x |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | no | 1,929,464,320 | 264.5 | 0.6% | 1.1178x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hw-hybrid-x51` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x170` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | no | 686,957,240 | 94.2 | 0.2% | 1.0041x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-array-hw-hybrid-x74-romfill` | no | 686,957,240 | 94.2 | 0.2% | 1.0041x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x8-romfill` | no | 1,929,464,320 | 205.7 | 3.2% | 1.1178x |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | no | 1,929,464,320 | 205.7 | 0.4% | 1.1178x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x340` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-hybrid-x16-romfill` | no | 1,929,464,320 | 264.5 | 2.0% | 1.1178x |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | no | 1,929,464,320 | 264.5 | 0.6% | 1.1178x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | no | 512,513,960 | 54.6 | 1.7% | 1.1178x |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | no | 512,513,960 | 54.6 | 0.1% | 1.1178x |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-array-hw-hybrid-x8-romfill` | no | 512,513,960 | 70.3 | 1.1% | 1.1178x |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | no | 512,513,960 | 70.3 | 0.2% | 1.1178x |

## Which design the published rule chooses once a block is verified

A re-ranking of designs the study already evaluated, under the study's own selection rule (non-dominated on per-user tokens/s and tokens/s per 1,000 mm2, then a marginal-return walk from the smallest feasible machine). `tau` is a common factor on both axes, so the choice is independent of the acceptance rate. The rule's reproduction of the published autoregressive recommendation is reported first, because a re-ranking whose baseline does not reproduce is not evidence of anything.

| study | model | published recommendation | rule reproduces it | under speculation, draft in ROM | draft in KV store | moves |
| --- | --- | --- | --- | --- | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-array-hw-tensor-x110` | yes |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-array-hw-tensor-x125` | yes |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-array-hw-tensor-x110` | yes |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-array-hw-tensor-x125` | yes |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-array-hw-tensor-x110` | yes |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-array-hw-tensor-x125` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x68` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x2-romfill` | `ROM-N5-native-HBMKV-wafer-tensor-x2` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-wafer-tensor-x2` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x68` | yes | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x87` | yes | `ROM-N6-native-HBMKV-array-hw-tensor-x87` | `ROM-N6-native-HBMKV-array-hw-tensor-x87` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | no |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-wafer-tensor-x2` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | no |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-wafer-tensor-x2` | yes |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x6` | `ROM-N5-native-HBMKV-array-hw-tensor-x327` | yes |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `ROM-N6-native-SRAMKV-wafer-hybrid-x7` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x7` | `ROM-N6-native-HBMKV-array-hw-tensor-x380` | yes |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x6` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | yes |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `ROM-N6-native-SRAMKV-wafer-hybrid-x8` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x9` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | yes |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x5` | `ROM-N5-native-HBMKV-wafer-tensor-x5` | yes |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x6` | `ROM-N6-native-HBMKV-wafer-tensor-x7` | yes |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | no |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | no |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | no |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x2` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | yes |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-array-hw-tensor-x38` | yes |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-tensor-x49` | yes |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | yes |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | yes |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | yes |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | yes |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-wafer-tensor-x3` | yes |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-wafer-tensor-x4` | yes |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | yes | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | `None` | no |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | yes | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | `None` | yes |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x21` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | yes |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | yes |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | no |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-array-hw-tensor-x32` | yes |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-hybrid-x10` | yes |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-tensor-x3` | yes |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-tensor-x3` | yes |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | no |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x44` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-tensor-x45` | yes |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x44` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | yes |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | yes |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-tensor-x4` | yes |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-tensor-x4` | yes |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x6` | `ROM-N5-native-HBMKV-array-hw-hybrid-x49` | yes |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x35` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-array-hw-tensor-x56` | yes |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399-romfill` | no |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x8` | `ROM-N6-native-HBMKV-array-hw-tensor-x69` | yes |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-tensor-x79` | no |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | no |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | yes | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x49` | yes |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | yes | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x4` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x69` | yes |

**The rule reproduces the published autoregressive recommendation on 56 of 56 model-and-study rows.** Of the 56 rows where it reproduces and the drafter applies, verifying a block moves the chosen rung on 45. Where it moves, it moves toward machines with compute headroom for a block, which is exactly what the arithmetic predicts: a verification pass raises arithmetic intensity by the block size, and a machine sized with just enough compute for one token per sweep has no room for it. **This is a re-ranking of rungs that already exist. The speculative-optimal design has not been computed: that would need the area split re-solved, which is `balanced_area_split`'s job and not this layer's.**

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

GPU cluster sizes this study evaluates for DeepSeek-V4-Pro-0813: 8, 14, 18, 29, 32, 38, 40, 41, 44, 56, 58, 74, 75, 76, 77, 78, 79, 80, 82, 83, 85, 87, 90, 91, 92, 93, 94, 95, 96, 98, 100, 101, 103, 106, 110, 111, 112, 113, 116, 117, 118, 120, 125, 126, 127, 128, 130, 132, 133, 134, 137, 142, 144, 146, 147, 150, 151, 157, 160, 168, 170, 171, 173, 185, 187, 188, 189, 193, 198, 199, 203, 205, 207, 216, 218, 221, 224, 227, 229, 231, 234, 237, 241, 245, 255, 257, 259, 262, 263, 268, 272, 274, 280, 289, 292, 293, 315, 320, 321, 324, 334, 335, 336, 337, 342, 344, 346, 347, 351, 352, 354, 355, 356, 360, 361, 363, 365, 366, 368, 373, 383, 384, 391, 392, 448, 504, 574, 672, 783, 1358, 3694 packages.

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

