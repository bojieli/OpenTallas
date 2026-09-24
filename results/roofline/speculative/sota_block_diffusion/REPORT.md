# Speculative decoding on the area-constrained roofline: sota_block_diffusion

> The DFlash / MiMo-UltraSpeed class: a block-diffusion drafter decoding a whole block in one parallel pass. Every figure below is derived from the roofline artifacts
> this repository has already published, by re-assembling each point's own five
> critical-path terms for a speculative cycle. Nothing here re-runs the machine
> model, and nothing here invents an acceptance rate.

## What this layer says

1. **Every term the speculative arithmetic needs is already in the published artifact, exactly.** 181,238 feasible points across 52 studies were rebuilt from their own five critical-path terms and every one reproduced its published step time to 1e-9 relative. Nothing here re-ran the machine model, and the layer is additive by construction rather than by promise.
2. **The headline is a break-even, not a speedup.** `tau* = T_cycle / step_time_s`, and `tau <= gamma+1` always. Of 287,270 (point, draft-placement) pairs where this profile's drafter applies, 78,191 (27.2%) cannot be sped up by speculation at ANY acceptance rate, at any block size on the ladder, even charging the drafter no KV traffic at all.
3. **The ROM-versus-GPU ratio under speculation carries no acceptance rate.** It is `T_cycle(GPU) / T_cycle(ROM)`: `tau` is a property of the model and its drafter, not of the machine, so it is identical on both sides and cancels. Every movement this report shows is a machine effect and nothing else, which is why it can be published without inventing an acceptance rate.
4. **The ratio moves, and it mostly compresses.** Across 983 model-context-batch-class rows, 903 move the ROM-versus-GPU per-user ratio DOWN under speculation and 80 move it UP, spanning 0.096x to 2.971x. The ROM advantage compresses on most operating points.
5. **At batch 1 the two extremes are opposite in sign, and they are the result.** DeepSeek-V4.1-Flash-engram-hbm on `wafer` silicon goes from 5.84x to 0.56x -- a 0.096x movement -- while DeepSeek-V4.1-Flash on `array` silicon goes from 11.56x to 13.35x, a 1.156x movement. A layer that multiplied both sides by `tau` would have reported neither.
6. **A moving ratio is not a win for either side, and the report says so on every table.** At the most favourable sourced acceptance (7.87) speculation is worth having on 600 of 985 ROM class rows and 948 of 985 GPU rows; everywhere else the design runs SLOWER with a drafter than without one. Where both sides lose, a rising ratio means only that the comparator lost more.
7. **Compute is never a gain and always a loss.** A verification pass over `n` positions charges `n` times the arithmetic exactly, so per accepted token compute costs `(n/tau) >= 1` times what it did. A compute-bound design cannot be sped up by speculation at any acceptance rate; it can only be slowed. That is where the recommended ROM designs live, because the sizing rule gives them just enough compute for one token per sweep.
8. **On a mask-ROM machine the draft pass costs a full array sweep, and that is the load-bearing assumption of the whole ROM verdict.** `stored/peak` is a technology constant in `src/opentallas/roofline.py`, so a pass reading only the drafter's region takes as long as sweeping the entire array. The alternative -- holding the drafter in the KV store -- is priced beside it on every ROM row and has NOT been costed in silicon area.
9. **The overhead factor lands below the only published measurement of it, and the gap is reported as a residual.** This layer models 1.188 on `b200_sxm-x3-tensor` against a published 1.26-1.32 measured on an H200 with the authors' own kernels. The named causes are the drafter's unsourced KV traffic at the bottom of its band, no sampler or scheduler cost anywhere in this model, and a different part. It is a band check and it validates nothing about the machine.
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
| `n5_vs_b200-deepseek-v41-flash` | 4,732 | 0 |
| `n6_vs_a100-deepseek-v41-flash` | 3,752 | 0 |
| `n5_vs_b200-deepseek-v41-flash-1m` | 4,794 | 0 |
| `n6_vs_a100-deepseek-v41-flash-1m` | 3,707 | 0 |
| `n5_vs_b200-deepseek-v41-flash-8k` | 4,990 | 0 |
| `n6_vs_a100-deepseek-v41-flash-8k` | 3,730 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | 5,753 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | 4,586 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | 5,652 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | 4,487 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | 5,532 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | 4,648 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | 4,956 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | 4,404 | 0 |
| `n5_vs_b200-kimi-k3` | 3,407 | 0 |
| `n6_vs_a100-kimi-k3` | 1,750 | 0 |
| `n5_vs_b200-kimi-k3-1m` | 1,611 | 0 |
| `n6_vs_a100-kimi-k3-1m` | 1,092 | 0 |
| `n5_vs_b200-kimi-k3-8k` | 3,075 | 0 |
| `n6_vs_a100-kimi-k3-8k` | 2,298 | 0 |
| `n5_vs_b200-mimo-v26-flash` | 2,781 | 0 |
| `n6_vs_a100-mimo-v26-flash` | 2,451 | 0 |
| `n5_vs_b200-mimo-v26-flash-1m` | 1,634 | 0 |
| `n6_vs_a100-mimo-v26-flash-1m` | 1,309 | 0 |
| `n5_vs_b200-mimo-v26-flash-8k` | 4,354 | 0 |
| `n6_vs_a100-mimo-v26-flash-8k` | 4,556 | 0 |
| `n5_vs_b200-mimo-v26-pro` | 1,598 | 0 |
| `n6_vs_a100-mimo-v26-pro` | 1,209 | 0 |
| `n5_vs_b200-mimo-v26-pro-1m` | 1,789 | 0 |
| `n6_vs_a100-mimo-v26-pro-1m` | 1,319 | 0 |
| `n5_vs_b200-mimo-v26-pro-8k` | 4,908 | 0 |
| `n6_vs_a100-mimo-v26-pro-8k` | 3,719 | 0 |
| `n5_vs_b200-qwen3-8b-1m` | 762 | 0 |
| `n6_vs_a100-qwen3-8b-1m` | 597 | 0 |
| `n5_vs_b200-qwen3-8b-200k` | 1,110 | 0 |
| `n6_vs_a100-qwen3-8b-200k` | 937 | 0 |
| `n5_vs_b200-flash-1m` | 2,533 | 0 |
| `n5_vs_b200-flash-32k` | 4,462 | 0 |
| `n5_vs_b200-flash-8k` | 4,408 | 0 |
| `n5_vs_b200-pro-200k` | 4,353 | 0 |
| `n5_vs_b200-pro-32k` | 4,388 | 0 |
| `n5_vs_b200-pro-8k` | 4,316 | 0 |
| `n6_vs_a100-flash-1m` | 1,725 | 0 |
| `n6_vs_a100-flash-32k` | 4,456 | 0 |
| `n6_vs_a100-flash-8k` | 4,286 | 0 |
| `n6_vs_a100-pro-200k` | 3,259 | 0 |
| `n6_vs_a100-pro-32k` | 3,365 | 0 |
| `n6_vs_a100-pro-8k` | 3,522 | 0 |
| `n5_vs_b200` | 8,937 | 0 |
| `n6_vs_a100` | 7,614 | 0 |
| `n5_vs_b200-quantised_variant` | 2,942 | 0 |
| `n6_vs_a100-quantised_variant` | 2,683 | 0 |

The identity checked is: `max(max(memory, compute)/stage_balance, serial path) x thermal_scale == step_time_s, with memory assembled by designs[].shared_memory_path and the compute-in-ROM fusion rule, and the serial path -- link_latency + layer_fixed_latency + the sweep on the path -- independently rebuilt from the model profile, the technology file and the token's operator graph (opentallas.critical_path)`.

## Headline: where speculation cannot pay at any acceptance rate

Counted at the LOW end of the unsourced drafter-KV band, which is the most favourable assumption available to speculation. `tau*` is the break-even acceptance at this profile's served block size.

| study | model | family | draft placement | binds on (autoregressive) | points | cannot pay at any gamma | tau* min | tau* median | tau* max |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 528 | 0 | 1.61 | 4.21 | 21.71 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 963 | 414 | 1.35 | 15.97 | 295.30 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 58 | 0 | 2.12 | 4.18 | 10.95 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 371 | 35 | 3.42 | 16.99 | 98.48 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 798 | 798 | 22.68 | 92.98 | 1,828.82 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 48 | 48 | 1,728.59 | 2,144.98 | 2,423.70 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 648 | 417 | 6.05 | 18.09 | 1,055.44 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 910 | 283 | 1.79 | 12.69 | 811.17 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 408 | 346 | 4.45 | 43.12 | 977.60 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 798 | 798 | 17.38 | 37.28 | 59.61 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 48 | 14 | 4.37 | 12.22 | 44.71 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 648 | 198 | 3.39 | 14.04 | 68.17 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 910 | 154 | 1.61 | 6.98 | 25.33 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 408 | 282 | 5.12 | 31.73 | 37.12 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 1 | 1 | 26.81 | 26.81 | 26.81 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 738 | 258 | 1.59 | 10.56 | 295.22 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 541 | 243 | 3.50 | 16.02 | 94.61 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 739 | 739 | 23.82 | 180.90 | 2,054.07 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 47 | 47 | 30.83 | 2,151.73 | 2,423.70 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 528 | 389 | 7.74 | 22.70 | 1,179.50 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 833 | 300 | 2.46 | 15.83 | 811.30 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 325 | 300 | 10.12 | 71.21 | 1,826.37 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 739 | 739 | 18.07 | 42.33 | 61.97 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 47 | 19 | 5.99 | 15.63 | 31.18 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 528 | 167 | 3.40 | 13.64 | 71.32 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 833 | 150 | 1.62 | 6.51 | 27.34 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 325 | 214 | 3.77 | 31.71 | 38.57 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 565 | 0 | 1.59 | 4.17 | 21.29 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,036 | 433 | 1.35 | 15.60 | 295.26 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 57 | 0 | 2.10 | 4.18 | 10.00 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 384 | 0 | 3.77 | 16.83 | 25.79 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 747 | 747 | 22.00 | 69.41 | 431.41 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 124 | 124 | 29.74 | 526.13 | 600.27 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 600 | 351 | 6.08 | 17.47 | 393.39 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 919 | 258 | 1.81 | 12.17 | 225.74 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 362 | 310 | 4.61 | 30.74 | 575.00 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 747 | 747 | 18.04 | 39.90 | 59.93 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 124 | 89 | 6.37 | 24.10 | 38.59 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 600 | 171 | 3.43 | 12.98 | 66.97 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 919 | 174 | 1.62 | 7.19 | 25.68 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 362 | 242 | 4.90 | 31.57 | 36.77 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 2 | 2 | 20.34 | 20.35 | 20.35 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 795 | 271 | 1.59 | 10.15 | 295.01 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 554 | 242 | 4.23 | 16.88 | 49.36 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 678 | 678 | 23.45 | 111.47 | 478.81 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 125 | 120 | 14.58 | 524.19 | 719.00 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 452 | 320 | 6.37 | 19.47 | 290.57 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 858 | 279 | 2.47 | 15.73 | 225.89 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 243 | 228 | 12.80 | 56.32 | 397.93 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 678 | 678 | 18.19 | 42.37 | 61.02 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 125 | 70 | 3.43 | 19.55 | 48.27 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 452 | 151 | 3.44 | 14.34 | 64.99 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 858 | 147 | 1.63 | 7.00 | 24.75 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 243 | 157 | 4.75 | 31.84 | 43.64 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 578 | 0 | 1.61 | 4.21 | 21.72 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,054 | 457 | 1.35 | 16.27 | 295.30 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 65 | 0 | 2.14 | 4.04 | 11.04 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 413 | 215 | 3.02 | 17.03 | 115.64 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 796 | 796 | 22.54 | 94.41 | 10,119.64 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 62 | 62 | 4,891.82 | 11,427.94 | 12,018.23 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 651 | 430 | 6.08 | 18.09 | 3,999.50 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 927 | 328 | 1.79 | 12.80 | 5,475.99 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 444 | 379 | 4.46 | 43.73 | 7,230.27 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 796 | 795 | 16.74 | 36.54 | 59.59 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 62 | 8 | 1.82 | 3.55 | 48.90 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 651 | 204 | 2.96 | 13.60 | 65.94 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 927 | 157 | 1.60 | 6.86 | 25.22 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 444 | 306 | 5.03 | 31.35 | 37.29 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 2 | 2 | 25.01 | 25.53 | 25.53 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 682 | 237 | 1.59 | 10.56 | 295.08 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 506 | 230 | 3.33 | 16.81 | 94.14 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 781 | 781 | 24.18 | 158.05 | 10,894.08 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 50 | 50 | 4,908.56 | 11,592.87 | 12,018.23 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 547 | 430 | 7.73 | 22.16 | 4,004.07 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 849 | 329 | 2.46 | 16.04 | 4,683.78 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 313 | 289 | 10.12 | 68.30 | 5,969.87 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 781 | 781 | 18.23 | 41.85 | 62.85 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 50 | 10 | 2.11 | 4.76 | 51.55 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 547 | 217 | 3.05 | 15.42 | 67.60 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 849 | 155 | 1.61 | 6.52 | 26.62 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 313 | 212 | 5.14 | 31.30 | 38.47 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `layer_fixed_latency` | 698 | 0 | 1.28 | 1.78 | 24.66 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,376 | 557 | 1.30 | 15.39 | 295.32 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 74 | 0 | 1.30 | 2.77 | 6.22 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 512 | 4 | 2.47 | 4.79 | 98.02 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 783 | 100 | 9.85 | 15.04 | 25.07 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 5 | 1 | 8.07 | 11.49 | 17.60 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 768 | 175 | 1.94 | 9.11 | 37.13 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 981 | 124 | 1.54 | 4.33 | 21.42 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 556 | 103 | 1.49 | 10.07 | 20.72 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 783 | 574 | 10.44 | 17.37 | 28.32 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 5 | 1 | 11.62 | 14.03 | 18.12 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 768 | 187 | 3.02 | 11.05 | 71.06 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 981 | 131 | 1.59 | 5.27 | 26.41 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 556 | 383 | 3.63 | 21.85 | 34.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 3 | 2 | 16.36 | 17.30 | 17.53 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 962 | 325 | 1.53 | 10.34 | 295.21 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 675 | 2 | 1.93 | 3.96 | 93.86 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 715 | 298 | 7.70 | 16.70 | 17.71 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 106 | 88 | 5.00 | 40.84 | 43.16 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 651 | 115 | 2.16 | 9.19 | 39.34 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 984 | 138 | 1.54 | 4.61 | 20.37 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 490 | 150 | 2.22 | 12.51 | 39.04 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 715 | 590 | 8.36 | 18.06 | 31.45 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 106 | 65 | 6.34 | 22.14 | 22.20 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 651 | 130 | 3.40 | 10.27 | 71.38 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 984 | 143 | 1.59 | 5.18 | 22.83 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 490 | 340 | 3.98 | 23.72 | 34.15 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `layer_fixed_latency` | 706 | 0 | 1.28 | 1.75 | 24.10 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,460 | 567 | 1.30 | 14.86 | 295.26 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 72 | 0 | 1.30 | 2.85 | 5.76 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 510 | 0 | 2.45 | 4.75 | 26.77 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 754 | 80 | 9.40 | 15.38 | 17.17 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 69 | 0 | 4.11 | 12.69 | 16.59 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 692 | 104 | 2.21 | 9.05 | 36.85 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 944 | 121 | 1.55 | 4.70 | 21.66 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 445 | 65 | 2.31 | 10.22 | 19.95 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 754 | 563 | 9.76 | 17.32 | 28.53 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 69 | 0 | 4.93 | 12.81 | 14.57 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 692 | 148 | 3.13 | 10.58 | 67.03 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 944 | 126 | 1.59 | 5.41 | 26.19 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 445 | 321 | 3.69 | 23.15 | 34.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 1 | 0 | 14.35 | 14.35 | 14.35 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,063 | 349 | 1.53 | 9.68 | 294.96 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 723 | 0 | 2.24 | 3.92 | 49.49 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 721 | 301 | 10.52 | 16.77 | 17.71 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 92 | 0 | 2.61 | 11.55 | 15.95 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 538 | 88 | 2.68 | 8.93 | 36.87 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 969 | 137 | 1.55 | 4.84 | 20.45 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 380 | 94 | 2.63 | 13.03 | 24.78 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 721 | 596 | 10.56 | 17.93 | 31.00 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 92 | 9 | 2.75 | 9.12 | 18.80 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 538 | 105 | 3.42 | 10.61 | 64.30 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 969 | 140 | 1.59 | 5.38 | 22.59 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 380 | 268 | 4.54 | 24.98 | 34.12 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `layer_fixed_latency` | 622 | 0 | 1.28 | 1.75 | 22.16 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,314 | 520 | 1.30 | 15.22 | 295.32 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 67 | 0 | 1.30 | 2.99 | 6.27 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 487 | 6 | 2.08 | 4.80 | 115.10 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 745 | 115 | 9.47 | 15.12 | 27.85 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 751 | 164 | 1.87 | 10.49 | 34.20 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 950 | 118 | 1.54 | 4.32 | 21.23 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 596 | 119 | 1.28 | 9.69 | 25.11 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 745 | 555 | 10.09 | 17.50 | 28.58 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 751 | 178 | 3.42 | 11.92 | 67.94 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 950 | 128 | 1.59 | 5.24 | 26.24 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 596 | 398 | 3.62 | 21.64 | 34.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 3 | 3 | 17.38 | 17.55 | 17.76 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 977 | 329 | 1.53 | 10.32 | 295.15 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 690 | 2 | 1.80 | 3.97 | 93.32 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 800 | 387 | 7.23 | 16.95 | 50.14 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 654 | 133 | 2.04 | 11.55 | 35.65 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 990 | 140 | 1.54 | 4.60 | 20.19 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 534 | 153 | 1.94 | 12.58 | 39.64 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 800 | 651 | 7.96 | 18.28 | 30.98 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 654 | 131 | 3.41 | 10.71 | 67.66 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 990 | 146 | 1.59 | 5.24 | 22.66 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 534 | 369 | 3.98 | 23.74 | 34.16 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `layer_fixed_latency` | 546 | 0 | 1.29 | 1.96 | 24.66 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 883 | 391 | 1.30 | 17.24 | 295.32 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `thermal` | 63 | 0 | 1.29 | 2.34 | 5.93 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 388 | 5 | 2.50 | 4.79 | 101.52 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 785 | 142 | 9.85 | 15.55 | 35.96 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 47 | 45 | 7.54 | 34.87 | 38.25 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `layer_fixed_latency` | 799 | 175 | 3.14 | 9.14 | 37.52 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 949 | 124 | 1.60 | 4.88 | 21.42 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 496 | 85 | 2.63 | 10.45 | 25.11 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 785 | 564 | 10.44 | 17.27 | 23.14 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 47 | 1 | 2.09 | 9.00 | 18.13 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `layer_fixed_latency` | 799 | 189 | 2.80 | 10.66 | 68.23 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 949 | 130 | 1.60 | 5.33 | 26.41 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 496 | 345 | 4.97 | 21.80 | 34.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `compute` | 6 | 4 | 16.31 | 17.51 | 17.53 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 802 | 295 | 1.53 | 11.44 | 295.23 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 672 | 3 | 1.93 | 3.96 | 69.24 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 684 | 306 | 10.68 | 16.84 | 40.56 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 150 | 132 | 5.00 | 36.99 | 43.17 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `layer_fixed_latency` | 662 | 115 | 3.15 | 9.35 | 39.34 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 961 | 138 | 1.62 | 4.70 | 20.37 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 467 | 140 | 2.64 | 12.51 | 39.04 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 684 | 554 | 10.73 | 17.84 | 26.32 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 150 | 65 | 2.63 | 16.34 | 22.20 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `layer_fixed_latency` | 662 | 131 | 3.33 | 9.86 | 71.38 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 961 | 142 | 1.60 | 5.15 | 22.83 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 467 | 325 | 4.40 | 23.64 | 34.15 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `compute` | 9 | 0 | 11.47 | 13.50 | 16.13 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `layer_fixed_latency` | 199 | 0 | 1.32 | 1.71 | 6.75 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 905 | 313 | 1.31 | 13.51 | 291.38 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `thermal` | 290 | 0 | 3.92 | 4.03 | 15.03 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 402 | 0 | 1.83 | 3.33 | 63.67 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 458 | 196 | 10.21 | 16.99 | 19.72 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 85 | 11 | 3.51 | 8.22 | 18.15 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 335 | 41 | 6.07 | 12.73 | 24.94 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 527 | 60 | 1.53 | 7.90 | 18.19 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 197 | 38 | 2.19 | 16.78 | 18.64 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `compute` | 458 | 366 | 10.44 | 17.60 | 19.05 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 85 | 14 | 3.34 | 11.88 | 28.48 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 335 | 66 | 6.56 | 13.73 | 36.00 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 527 | 66 | 1.58 | 9.05 | 19.78 |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 197 | 117 | 3.54 | 27.17 | 34.26 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `compute` | 4 | 0 | 15.24 | 16.43 | 16.96 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 412 | 130 | 2.20 | 7.16 | 290.43 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 398 | 2 | 2.04 | 3.16 | 108.29 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 248 | 172 | 10.83 | 17.19 | 20.29 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 60 | 1 | 3.28 | 8.73 | 17.36 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 172 | 21 | 5.27 | 13.50 | 23.47 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 308 | 30 | 1.54 | 5.24 | 18.08 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 148 | 69 | 2.35 | 16.52 | 18.25 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `compute` | 248 | 172 | 10.83 | 17.29 | 19.55 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 60 | 0 | 3.29 | 7.95 | 16.19 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 172 | 33 | 5.61 | 14.44 | 33.63 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 308 | 32 | 1.56 | 5.41 | 18.96 |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 148 | 82 | 3.54 | 27.94 | 34.26 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `compute` | 27 | 0 | 7.17 | 11.83 | 58.07 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `layer_fixed_latency` | 146 | 0 | 1.36 | 2.08 | 8.03 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 627 | 161 | 1.22 | 10.81 | 290.13 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `thermal` | 228 | 0 | 4.84 | 4.84 | 14.30 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 193 | 0 | 1.69 | 3.24 | 56.54 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 50 | 40 | 11.20 | 17.32 | 17.69 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 54 | 0 | 2.05 | 5.60 | 14.94 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 74 | 3 | 5.91 | 14.22 | 24.77 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 171 | 0 | 1.49 | 3.43 | 9.48 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 41 | 12 | 2.38 | 7.85 | 17.16 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `compute` | 50 | 40 | 11.20 | 17.35 | 20.22 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 54 | 0 | 2.00 | 8.79 | 14.63 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 74 | 14 | 6.02 | 14.95 | 35.58 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 171 | 0 | 1.50 | 3.69 | 15.83 |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 41 | 19 | 3.72 | 15.26 | 34.26 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `compute` | 39 | 0 | 12.85 | 15.60 | 16.97 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 379 | 94 | 2.21 | 7.48 | 286.32 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 329 | 2 | 1.67 | 6.46 | 104.43 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 41 | 29 | 10.27 | 17.42 | 17.69 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 59 | 0 | 2.19 | 3.31 | 8.95 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 58 | 3 | 8.48 | 13.77 | 23.52 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 153 | 0 | 1.48 | 3.13 | 11.10 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 34 | 12 | 3.41 | 16.83 | 17.29 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `compute` | 41 | 29 | 10.27 | 17.42 | 19.83 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 59 | 0 | 1.79 | 5.13 | 8.33 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 58 | 12 | 8.79 | 14.48 | 33.56 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 153 | 0 | 1.48 | 3.13 | 15.82 |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 34 | 19 | 6.28 | 33.10 | 34.26 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `layer_fixed_latency` | 158 | 0 | 1.33 | 1.79 | 6.90 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 702 | 258 | 1.34 | 13.67 | 291.65 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `thermal` | 52 | 0 | 2.21 | 4.27 | 5.58 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 507 | 0 | 1.83 | 3.72 | 70.29 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 382 | 84 | 10.80 | 16.91 | 29.53 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 97 | 67 | 8.50 | 22.08 | 25.55 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 347 | 40 | 4.26 | 10.99 | 24.84 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 540 | 54 | 1.53 | 6.22 | 18.79 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 290 | 36 | 2.15 | 11.65 | 25.73 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `compute` | 382 | 336 | 10.81 | 18.73 | 22.92 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 97 | 40 | 5.26 | 14.34 | 19.27 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 347 | 60 | 4.61 | 12.11 | 36.57 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 540 | 60 | 1.59 | 6.48 | 20.53 |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 290 | 140 | 3.50 | 15.84 | 34.26 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `compute` | 2 | 0 | 13.95 | 13.98 | 13.98 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `link_latency` | 468 | 136 | 2.20 | 7.29 | 291.31 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `gpu` | `in_hbm` | `weight_read` | 448 | 2 | 2.18 | 3.18 | 109.91 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `compute` | 342 | 284 | 9.90 | 17.26 | 30.09 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `kv_read` | 103 | 66 | 8.22 | 21.73 | 28.87 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `layer_fixed_latency` | 246 | 30 | 4.12 | 12.61 | 22.04 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `link_latency` | 478 | 42 | 1.54 | 7.01 | 18.42 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_kv_store` | `weight_read` | 211 | 90 | 2.32 | 14.25 | 25.90 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `compute` | 342 | 282 | 8.87 | 17.72 | 18.94 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `kv_read` | 103 | 16 | 5.90 | 13.17 | 18.48 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `layer_fixed_latency` | 246 | 44 | 4.42 | 13.04 | 32.12 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `link_latency` | 478 | 44 | 1.60 | 6.96 | 19.35 |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `rom` | `in_rom` | `weight_read` | 211 | 104 | 3.50 | 15.26 | 34.26 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 115 | 0 | 1.50 | 2.47 | 71.97 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 396 | 0 | 1.20 | 1.68 | 31.53 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 604 | 177 | 1.21 | 9.80 | 293.75 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 25 | 0 | 1.68 | 2.03 | 2.78 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 209 | 0 | 1.67 | 3.91 | 31.00 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 8 | 0 | 14.83 | 15.82 | 15.89 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 196 | 0 | 1.18 | 5.89 | 14.91 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 289 | 3 | 3.00 | 9.63 | 37.13 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 516 | 45 | 1.53 | 3.53 | 21.91 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `thermal` | 303 | 0 | 3.26 | 4.23 | 7.99 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 120 | 18 | 3.34 | 13.55 | 17.23 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 8 | 4 | 16.26 | 17.32 | 17.37 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 196 | 26 | 1.11 | 7.32 | 27.96 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 289 | 26 | 3.05 | 10.43 | 66.83 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 516 | 48 | 1.55 | 4.27 | 28.44 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `thermal` | 303 | 0 | 3.39 | 8.45 | 11.80 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 120 | 69 | 5.05 | 24.50 | 34.30 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 47 | 0 | 2.10 | 2.74 | 9.59 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 94 | 0 | 1.62 | 1.92 | 2.21 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 511 | 121 | 1.38 | 8.11 | 293.06 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 359 | 1 | 1.86 | 3.16 | 68.73 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 26 | 2 | 14.66 | 16.21 | 17.08 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 521 | 0 | 1.23 | 4.72 | 15.34 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 244 | 0 | 3.10 | 10.00 | 32.69 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 525 | 46 | 1.54 | 3.18 | 20.60 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 124 | 29 | 2.84 | 11.88 | 17.27 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 26 | 14 | 16.08 | 17.20 | 17.95 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 521 | 2 | 1.06 | 5.32 | 17.17 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 244 | 18 | 3.25 | 10.26 | 57.50 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 525 | 48 | 1.51 | 3.59 | 24.32 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 124 | 72 | 4.75 | 21.34 | 34.30 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 396 | 5 | 1.40 | 3.08 | 90.60 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 320 | 0 | 1.19 | 1.50 | 25.01 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 406 | 86 | 1.17 | 6.21 | 291.51 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 34 | 0 | 1.74 | 2.29 | 3.00 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 3 | 3 | 17.11 | 17.11 | 17.13 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 79 | 0 | 1.16 | 1.23 | 15.55 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 179 | 19 | 3.65 | 11.05 | 36.60 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 168 | 0 | 1.35 | 2.63 | 8.80 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 49 | 12 | 2.65 | 11.64 | 17.03 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 3 | 3 | 17.23 | 17.24 | 17.25 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 79 | 1 | 1.06 | 3.92 | 17.41 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 179 | 40 | 4.44 | 11.99 | 65.56 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 168 | 0 | 1.38 | 2.90 | 15.53 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 49 | 28 | 4.88 | 23.06 | 34.30 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 364 | 2 | 1.80 | 2.24 | 83.57 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 454 | 53 | 1.23 | 3.45 | 277.68 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 37 | 0 | 2.62 | 9.07 | 25.35 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 40 | 25 | 8.17 | 17.32 | 17.77 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 81 | 0 | 1.11 | 1.22 | 16.92 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 104 | 6 | 3.87 | 9.64 | 32.29 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 180 | 0 | 1.35 | 3.18 | 10.46 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 49 | 12 | 2.81 | 12.77 | 17.05 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 40 | 26 | 8.23 | 17.42 | 18.80 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 81 | 2 | 1.03 | 1.41 | 18.77 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 104 | 18 | 4.63 | 10.05 | 56.55 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 180 | 0 | 1.34 | 3.27 | 14.97 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 49 | 28 | 5.27 | 25.37 | 34.31 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 18 | 0 | 6.06 | 8.10 | 10.65 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 435 | 0 | 1.20 | 1.88 | 33.85 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 597 | 259 | 1.26 | 16.58 | 294.27 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 35 | 0 | 1.27 | 1.39 | 2.89 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 325 | 0 | 1.79 | 4.34 | 53.63 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 534 | 135 | 9.92 | 16.38 | 28.67 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 176 | 117 | 2.52 | 22.08 | 32.83 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 714 | 83 | 2.92 | 9.46 | 42.17 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 880 | 104 | 1.59 | 4.36 | 25.44 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 640 | 50 | 2.37 | 12.54 | 27.04 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 534 | 232 | 9.94 | 16.92 | 18.79 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 176 | 2 | 1.30 | 6.97 | 27.26 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 714 | 112 | 2.71 | 9.83 | 79.78 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 880 | 113 | 1.57 | 4.60 | 36.45 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 640 | 260 | 5.46 | 15.08 | 34.30 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `compute` | 19 | 4 | 12.09 | 14.03 | 17.33 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 106 | 0 | 1.79 | 2.09 | 2.62 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 605 | 253 | 1.51 | 13.82 | 294.23 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 630 | 2 | 1.54 | 3.72 | 76.21 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 606 | 375 | 10.95 | 17.11 | 32.08 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 285 | 147 | 1.84 | 18.47 | 33.19 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 664 | 85 | 3.31 | 10.35 | 37.20 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 1,033 | 120 | 1.62 | 5.03 | 21.86 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 608 | 208 | 3.27 | 15.38 | 31.51 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 606 | 303 | 10.63 | 17.01 | 21.03 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 285 | 18 | 1.39 | 5.99 | 28.21 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 664 | 88 | 2.76 | 10.94 | 67.49 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 1,033 | 125 | 1.57 | 4.17 | 27.01 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 608 | 275 | 5.14 | 15.27 | 34.30 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 69 | 0 | 1.61 | 2.74 | 5.60 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `layer_fixed_latency` | 311 | 0 | 1.22 | 1.79 | 22.75 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 559 | 141 | 1.20 | 10.18 | 291.90 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 18 | 0 | 1.75 | 3.18 | 4.18 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 209 | 0 | 1.96 | 3.82 | 56.71 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 6 | 0 | 16.46 | 16.69 | 16.85 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 96 | 0 | 1.25 | 2.54 | 14.45 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 96 | 0 | 3.31 | 10.12 | 31.56 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 196 | 0 | 1.50 | 2.66 | 8.25 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 38 | 12 | 2.82 | 15.82 | 17.09 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 6 | 6 | 17.24 | 17.66 | 17.84 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 96 | 0 | 1.16 | 6.19 | 16.56 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 96 | 18 | 3.81 | 11.07 | 51.91 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 196 | 0 | 1.51 | 2.95 | 15.41 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 38 | 23 | 4.71 | 28.44 | 34.17 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 15 | 0 | 2.48 | 2.71 | 3.16 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 364 | 76 | 2.12 | 6.99 | 290.79 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 392 | 0 | 1.43 | 2.81 | 69.69 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 18 | 6 | 16.00 | 16.87 | 17.31 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 90 | 0 | 1.34 | 1.72 | 16.47 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 52 | 0 | 3.54 | 7.70 | 28.65 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 210 | 0 | 1.49 | 2.98 | 10.47 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 68 | 13 | 2.79 | 15.77 | 17.18 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 18 | 18 | 17.06 | 17.44 | 18.91 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 90 | 8 | 1.11 | 4.30 | 18.73 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 52 | 0 | 4.04 | 8.05 | 46.47 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 210 | 1 | 1.43 | 3.17 | 18.42 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 68 | 38 | 4.75 | 25.71 | 34.17 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 349 | 0 | 1.55 | 3.07 | 63.41 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `layer_fixed_latency` | 233 | 0 | 1.21 | 1.52 | 20.94 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 708 | 105 | 1.13 | 5.28 | 282.92 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 22 | 0 | 1.87 | 3.10 | 3.20 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 10 | 7 | 11.54 | 17.03 | 17.61 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 62 | 0 | 1.12 | 1.16 | 12.99 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 169 | 28 | 4.86 | 14.01 | 31.22 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 185 | 0 | 1.35 | 3.06 | 9.54 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 51 | 11 | 2.53 | 12.94 | 17.02 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 10 | 8 | 11.54 | 18.00 | 19.17 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 62 | 0 | 1.08 | 1.38 | 15.29 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 169 | 60 | 5.39 | 14.34 | 51.15 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 185 | 0 | 1.40 | 3.22 | 16.46 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 51 | 28 | 4.76 | 25.70 | 34.19 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 294 | 0 | 1.74 | 2.14 | 74.01 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 407 | 47 | 1.99 | 3.33 | 262.97 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 162 | 0 | 1.20 | 3.87 | 52.73 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 41 | 30 | 11.25 | 17.19 | 17.47 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 85 | 0 | 1.09 | 1.15 | 12.04 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 117 | 9 | 6.52 | 10.97 | 28.43 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 163 | 0 | 1.39 | 3.53 | 9.14 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 50 | 11 | 2.65 | 13.87 | 17.04 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 41 | 39 | 11.25 | 17.51 | 19.77 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 85 | 0 | 1.04 | 1.29 | 14.78 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 117 | 28 | 6.88 | 12.06 | 45.97 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 163 | 0 | 1.39 | 3.58 | 15.90 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 50 | 28 | 5.04 | 27.62 | 34.19 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 2 | 0 | 8.57 | 9.64 | 9.64 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `layer_fixed_latency` | 499 | 0 | 1.22 | 1.93 | 27.55 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 942 | 356 | 1.31 | 14.63 | 292.60 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 44 | 0 | 1.29 | 1.73 | 3.13 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 453 | 6 | 1.86 | 4.19 | 94.56 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 602 | 76 | 9.80 | 16.51 | 27.45 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 174 | 87 | 2.53 | 17.02 | 27.90 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 589 | 70 | 3.39 | 9.94 | 34.17 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 1,023 | 114 | 1.59 | 5.22 | 20.51 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 580 | 44 | 2.96 | 12.59 | 22.03 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 602 | 498 | 10.26 | 17.65 | 23.45 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 174 | 2 | 1.87 | 9.46 | 17.99 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 589 | 89 | 3.29 | 10.78 | 58.36 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 1,023 | 122 | 1.58 | 5.25 | 24.49 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 580 | 342 | 4.09 | 19.25 | 34.17 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `compute` | 2 | 0 | 12.65 | 15.02 | 15.02 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 552 | 211 | 2.13 | 12.06 | 292.49 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 645 | 4 | 1.67 | 3.16 | 80.13 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 564 | 291 | 10.92 | 17.02 | 28.02 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 183 | 96 | 1.73 | 17.20 | 28.88 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 420 | 55 | 3.59 | 11.10 | 31.53 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 944 | 96 | 1.50 | 5.53 | 19.51 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 409 | 127 | 2.64 | 15.30 | 28.01 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 564 | 478 | 11.61 | 17.94 | 25.13 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 183 | 2 | 2.15 | 8.51 | 18.13 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 420 | 59 | 3.82 | 11.54 | 52.51 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 944 | 104 | 1.58 | 4.82 | 21.55 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 409 | 284 | 4.01 | 21.45 | 34.17 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 260 | 0 | 1.03 | 1.37 | 8.70 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `layer_fixed_latency` | 33 | 0 | 1.11 | 1.14 | 1.25 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 108 | 4 | 1.44 | 1.80 | 17.33 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 139 | 0 | 1.01 | 1.03 | 1.12 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 8 | 0 | 1.17 | 2.92 | 6.03 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 102 | 12 | 5.73 | 13.37 | 17.24 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 91 | 0 | 1.32 | 4.62 | 8.72 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 21 | 0 | 1.02 | 4.63 | 16.78 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 8 | 0 | 1.17 | 3.28 | 6.03 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 102 | 20 | 6.04 | 14.49 | 22.30 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 91 | 0 | 1.63 | 4.74 | 11.81 |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 21 | 2 | 2.33 | 5.74 | 37.17 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 330 | 0 | 1.02 | 1.41 | 8.95 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 51 | 2 | 1.74 | 2.70 | 17.65 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 8 | 0 | 1.21 | 4.90 | 11.18 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 96 | 12 | 5.90 | 13.27 | 17.33 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 88 | 0 | 1.34 | 4.25 | 7.43 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 24 | 0 | 1.03 | 4.76 | 16.78 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 8 | 0 | 1.21 | 4.90 | 12.17 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 96 | 20 | 6.04 | 14.11 | 23.37 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 88 | 0 | 1.64 | 5.14 | 11.81 |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 24 | 2 | 2.33 | 5.78 | 37.17 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 349 | 0 | 1.06 | 1.11 | 8.27 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `layer_fixed_latency` | 87 | 0 | 1.13 | 1.19 | 1.47 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 186 | 9 | 1.37 | 3.03 | 18.87 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 34 | 0 | 1.05 | 1.06 | 1.25 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 64 | 0 | 1.02 | 1.11 | 10.43 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 150 | 7 | 3.36 | 11.49 | 17.37 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 138 | 0 | 1.30 | 2.73 | 7.46 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 102 | 24 | 1.02 | 13.86 | 17.04 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 64 | 0 | 1.02 | 1.03 | 10.43 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 150 | 33 | 3.78 | 12.05 | 22.41 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 138 | 0 | 1.38 | 2.99 | 15.34 |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 102 | 56 | 2.09 | 30.65 | 38.00 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 326 | 0 | 1.04 | 1.07 | 7.98 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 175 | 5 | 1.43 | 2.28 | 19.01 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 90 | 0 | 1.02 | 1.31 | 11.10 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 106 | 6 | 3.37 | 11.33 | 17.61 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 137 | 0 | 1.31 | 3.24 | 8.12 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 103 | 24 | 1.03 | 14.39 | 17.04 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 90 | 0 | 1.01 | 1.25 | 11.10 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 106 | 24 | 3.78 | 12.03 | 23.38 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 137 | 0 | 1.52 | 3.34 | 14.80 |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 103 | 56 | 2.14 | 30.92 | 38.00 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `layer_fixed_latency` | 210 | 0 | 2.65 | 3.11 | 4.15 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 900 | 390 | 2.49 | 16.76 | 272.03 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 10 | 0 | 2.00 | 2.32 | 2.65 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 315 | 0 | 2.73 | 3.54 | 5.88 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 132 | 1 | 11.64 | 14.32 | 17.02 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 57 | 0 | 1.93 | 4.87 | 13.98 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 141 | 0 | 2.77 | 6.73 | 12.92 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 499 | 128 | 1.57 | 10.24 | 23.38 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `thermal` | 14 | 0 | 10.11 | 10.61 | 11.84 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 255 | 29 | 1.84 | 6.64 | 17.04 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 132 | 8 | 11.64 | 16.15 | 19.59 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 57 | 0 | 1.94 | 6.83 | 14.42 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 141 | 5 | 2.65 | 7.99 | 20.40 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 499 | 133 | 1.64 | 11.33 | 32.00 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `thermal` | 14 | 0 | 11.52 | 12.42 | 15.38 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 255 | 126 | 5.79 | 16.95 | 34.15 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `layer_fixed_latency` | 379 | 0 | 1.51 | 2.06 | 15.01 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 800 | 372 | 1.43 | 17.76 | 294.65 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 40 | 0 | 1.32 | 1.71 | 4.51 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 311 | 0 | 2.27 | 3.74 | 43.90 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 489 | 82 | 10.29 | 15.68 | 17.20 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 40 | 32 | 6.11 | 22.10 | 26.14 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 978 | 76 | 2.39 | 8.69 | 33.63 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,014 | 228 | 1.53 | 6.57 | 19.93 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 411 | 37 | 1.82 | 6.83 | 19.46 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 489 | 77 | 10.76 | 16.09 | 17.70 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 40 | 0 | 2.03 | 10.94 | 14.20 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 978 | 78 | 2.16 | 11.61 | 63.41 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,014 | 230 | 1.54 | 6.95 | 21.99 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 411 | 132 | 3.47 | 13.68 | 34.15 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `layer_fixed_latency` | 382 | 0 | 1.49 | 2.04 | 14.82 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 725 | 345 | 1.40 | 17.96 | 294.70 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 40 | 0 | 1.32 | 1.79 | 9.29 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 313 | 2 | 2.28 | 3.76 | 61.26 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 487 | 90 | 10.33 | 15.70 | 30.21 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 47 | 46 | 11.01 | 49.27 | 59.65 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 1,027 | 106 | 2.40 | 8.95 | 37.03 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 974 | 190 | 1.53 | 6.27 | 23.72 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 413 | 36 | 1.71 | 6.50 | 37.18 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 487 | 78 | 10.55 | 16.08 | 17.77 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 47 | 0 | 1.61 | 8.06 | 16.44 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 1,027 | 107 | 2.65 | 12.17 | 62.46 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 974 | 192 | 1.54 | 6.26 | 22.39 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 413 | 130 | 4.81 | 13.54 | 34.14 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `layer_fixed_latency` | 369 | 0 | 2.00 | 2.31 | 3.85 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,199 | 553 | 1.86 | 17.46 | 291.43 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 58 | 0 | 1.57 | 3.71 | 6.72 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 459 | 0 | 3.51 | 5.02 | 8.83 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 649 | 24 | 10.10 | 15.01 | 17.06 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 48 | 0 | 3.84 | 14.14 | 15.77 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 315 | 12 | 1.73 | 5.63 | 17.62 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 964 | 274 | 1.54 | 11.10 | 23.80 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 292 | 23 | 2.61 | 11.72 | 17.55 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 649 | 511 | 10.27 | 17.61 | 24.53 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 48 | 26 | 5.84 | 17.21 | 19.29 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 315 | 14 | 2.25 | 7.31 | 18.61 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 964 | 288 | 1.61 | 11.34 | 33.75 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 292 | 184 | 4.35 | 23.07 | 34.08 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `layer_fixed_latency` | 377 | 0 | 1.73 | 2.02 | 9.53 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,135 | 505 | 1.61 | 17.07 | 292.93 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 59 | 0 | 1.31 | 2.96 | 6.73 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 399 | 0 | 3.21 | 5.04 | 30.24 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 685 | 130 | 10.15 | 15.56 | 34.70 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 24 | 24 | 29.97 | 32.61 | 33.85 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 422 | 30 | 1.72 | 6.67 | 29.14 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 931 | 222 | 1.50 | 9.22 | 20.47 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 356 | 33 | 2.54 | 10.67 | 20.13 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 685 | 538 | 9.76 | 17.82 | 23.98 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 24 | 2 | 6.64 | 13.77 | 17.54 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 422 | 34 | 2.30 | 8.33 | 48.00 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 931 | 231 | 1.56 | 10.01 | 26.98 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 356 | 221 | 4.34 | 21.73 | 34.08 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `layer_fixed_latency` | 350 | 0 | 1.65 | 2.02 | 9.44 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,028 | 450 | 1.60 | 17.01 | 292.73 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 56 | 0 | 1.31 | 2.96 | 6.75 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 386 | 2 | 3.21 | 5.05 | 79.82 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 694 | 118 | 10.16 | 15.50 | 63.19 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 34 | 34 | 57.71 | 61.12 | 66.34 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 436 | 38 | 1.73 | 6.79 | 27.00 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 963 | 228 | 1.49 | 9.80 | 20.32 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 369 | 34 | 2.54 | 11.04 | 32.27 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 694 | 547 | 11.38 | 17.90 | 24.04 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 34 | 4 | 3.58 | 9.63 | 18.09 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 436 | 34 | 2.32 | 7.74 | 46.22 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 963 | 238 | 1.55 | 10.00 | 27.09 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 369 | 230 | 4.37 | 21.55 | 34.08 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 626 | 253 | 3.46 | 15.17 | 224.96 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 277 | 0 | 2.97 | 3.10 | 7.65 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 58 | 4 | 12.40 | 14.82 | 17.28 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 128 | 0 | 1.57 | 5.28 | 15.18 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 81 | 0 | 3.33 | 7.34 | 10.86 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 406 | 90 | 1.57 | 7.44 | 23.28 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 149 | 36 | 2.22 | 7.63 | 17.16 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 58 | 26 | 12.96 | 16.92 | 22.01 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 128 | 24 | 1.46 | 9.04 | 26.01 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 81 | 0 | 3.41 | 8.17 | 15.53 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 406 | 102 | 1.65 | 9.80 | 30.74 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 149 | 85 | 5.97 | 18.05 | 34.30 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 2 | 0 | 15.79 | 16.92 | 16.92 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 952 | 343 | 1.74 | 13.79 | 294.40 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 486 | 0 | 1.92 | 3.49 | 14.79 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 555 | 85 | 10.18 | 15.67 | 18.82 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 133 | 87 | 3.54 | 22.90 | 26.31 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 779 | 77 | 2.93 | 8.57 | 35.40 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,091 | 246 | 1.53 | 7.19 | 19.40 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 458 | 56 | 2.81 | 9.35 | 22.52 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 555 | 129 | 10.18 | 16.44 | 18.34 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 133 | 0 | 2.72 | 12.40 | 13.57 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 779 | 140 | 2.37 | 9.20 | 63.84 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,091 | 251 | 1.54 | 7.54 | 20.19 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 458 | 177 | 3.47 | 14.89 | 34.15 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 1 | 1 | 17.20 | 17.20 | 17.20 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 805 | 292 | 1.74 | 13.67 | 294.43 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 464 | 0 | 1.84 | 3.47 | 48.03 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 565 | 125 | 10.65 | 16.03 | 38.42 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 53 | 48 | 6.34 | 49.81 | 59.65 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 854 | 148 | 2.90 | 10.32 | 43.64 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,074 | 230 | 1.53 | 6.94 | 23.72 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 470 | 58 | 2.85 | 9.89 | 33.73 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 565 | 123 | 12.17 | 16.36 | 18.42 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 53 | 2 | 1.80 | 8.49 | 18.21 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 854 | 159 | 3.07 | 11.60 | 63.92 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,074 | 234 | 1.55 | 7.05 | 20.32 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 470 | 175 | 5.02 | 14.69 | 34.14 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 553 | 327 | 4.41 | 18.13 | 285.79 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 750 | 0 | 2.17 | 3.71 | 17.37 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 616 | 68 | 11.60 | 15.75 | 18.54 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 44 | 5 | 2.66 | 12.17 | 18.23 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 250 | 8 | 1.74 | 5.88 | 17.31 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 864 | 244 | 1.55 | 11.26 | 23.80 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 182 | 28 | 2.62 | 14.59 | 19.77 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 616 | 528 | 11.87 | 18.16 | 26.27 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 44 | 21 | 3.47 | 15.23 | 23.53 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 250 | 8 | 2.41 | 6.49 | 17.31 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 864 | 255 | 1.62 | 11.50 | 32.35 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 182 | 97 | 4.34 | 26.98 | 34.08 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 475 | 291 | 5.89 | 18.22 | 291.68 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 724 | 1 | 1.92 | 3.73 | 59.13 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 609 | 144 | 11.22 | 15.87 | 38.30 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 23 | 20 | 5.46 | 34.49 | 38.10 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 332 | 20 | 1.73 | 6.45 | 29.01 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 896 | 232 | 1.50 | 10.09 | 20.77 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 306 | 50 | 2.56 | 13.85 | 22.50 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 609 | 533 | 11.30 | 18.45 | 26.78 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 23 | 7 | 8.83 | 15.67 | 20.53 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 332 | 25 | 2.43 | 6.30 | 45.56 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 896 | 242 | 1.57 | 10.25 | 27.04 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 306 | 183 | 2.96 | 23.44 | 34.09 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 1 | 1 | 17.54 | 17.54 | 17.54 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 452 | 287 | 5.06 | 18.28 | 292.68 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 747 | 1 | 1.91 | 3.74 | 78.59 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 645 | 115 | 11.20 | 15.78 | 67.60 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 29 | 28 | 10.48 | 63.38 | 69.69 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 362 | 25 | 1.73 | 6.55 | 29.77 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 943 | 246 | 1.49 | 10.11 | 20.48 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 343 | 72 | 2.55 | 13.97 | 29.25 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 645 | 562 | 11.30 | 18.29 | 26.84 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 29 | 8 | 4.92 | 11.25 | 18.63 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 362 | 26 | 2.44 | 8.07 | 48.43 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 943 | 257 | 1.57 | 10.25 | 26.99 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 343 | 206 | 4.37 | 23.14 | 34.09 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `layer_fixed_latency` | 291 | 0 | 1.81 | 2.07 | 4.72 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 819 | 346 | 1.64 | 16.88 | 293.18 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 24 | 0 | 1.33 | 1.60 | 2.21 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 299 | 0 | 2.42 | 3.68 | 7.05 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 195 | 22 | 11.90 | 16.10 | 17.13 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 62 | 0 | 2.47 | 9.22 | 11.44 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 601 | 12 | 2.52 | 7.69 | 29.41 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 956 | 243 | 1.54 | 9.21 | 24.05 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 390 | 31 | 2.57 | 6.50 | 17.49 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 195 | 43 | 12.94 | 16.69 | 18.33 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 62 | 0 | 2.98 | 7.83 | 14.10 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 601 | 13 | 2.31 | 10.99 | 49.80 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 956 | 251 | 1.60 | 10.05 | 34.27 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 390 | 115 | 5.11 | 14.70 | 34.15 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `layer_fixed_latency` | 155 | 0 | 3.08 | 3.25 | 3.93 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 976 | 439 | 2.52 | 17.01 | 267.10 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 20 | 0 | 3.69 | 5.29 | 6.25 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 335 | 0 | 3.40 | 4.90 | 6.75 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 106 | 2 | 12.81 | 14.76 | 17.06 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 45 | 0 | 2.18 | 6.95 | 14.14 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 115 | 0 | 1.79 | 5.88 | 12.32 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 347 | 84 | 1.77 | 10.31 | 20.27 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 185 | 14 | 2.68 | 9.48 | 17.06 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 106 | 99 | 12.81 | 19.26 | 24.97 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 45 | 15 | 2.71 | 7.78 | 25.41 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 115 | 1 | 2.35 | 7.89 | 19.24 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 347 | 87 | 1.83 | 11.78 | 23.76 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 185 | 101 | 5.25 | 21.52 | 34.08 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 105 | 0 | 1.26 | 2.34 | 9.18 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `layer_fixed_latency` | 238 | 0 | 1.19 | 1.28 | 3.77 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 209 | 42 | 1.55 | 8.32 | 19.07 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 28 | 0 | 1.42 | 1.66 | 1.84 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 169 | 0 | 1.17 | 1.19 | 1.38 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 8 | 0 | 14.92 | 15.81 | 15.95 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 180 | 0 | 1.16 | 3.96 | 15.75 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 390 | 15 | 2.91 | 11.22 | 17.72 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 644 | 83 | 1.35 | 4.13 | 18.87 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `thermal` | 461 | 0 | 3.53 | 9.63 | 10.48 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 584 | 40 | 1.08 | 2.32 | 17.32 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `compute` | 8 | 0 | 14.92 | 15.81 | 15.95 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 180 | 0 | 1.09 | 2.01 | 15.75 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 390 | 35 | 2.67 | 11.52 | 21.73 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 644 | 91 | 1.58 | 4.31 | 27.45 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `thermal` | 461 | 0 | 3.56 | 9.27 | 10.48 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 584 | 196 | 1.86 | 2.75 | 37.99 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 874 | 327 | 2.13 | 13.46 | 289.90 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 417 | 0 | 2.39 | 3.26 | 10.92 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 324 | 16 | 11.29 | 13.82 | 17.10 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 102 | 0 | 1.99 | 8.45 | 15.95 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 342 | 6 | 3.06 | 4.89 | 29.42 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 992 | 236 | 1.54 | 9.17 | 24.58 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 348 | 24 | 2.67 | 7.52 | 17.55 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 324 | 141 | 13.84 | 16.77 | 20.15 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 102 | 10 | 1.96 | 8.80 | 19.45 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 342 | 39 | 2.40 | 6.06 | 47.59 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 992 | 244 | 1.61 | 9.65 | 34.44 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 348 | 113 | 4.46 | 15.35 | 34.15 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 567 | 256 | 3.21 | 16.89 | 224.05 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 400 | 0 | 3.61 | 3.61 | 6.27 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 54 | 4 | 13.25 | 15.49 | 17.23 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 54 | 0 | 1.98 | 3.92 | 14.91 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 47 | 0 | 1.83 | 6.65 | 9.32 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 214 | 18 | 1.77 | 6.70 | 20.15 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 57 | 12 | 2.73 | 13.36 | 17.11 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 54 | 50 | 13.25 | 19.02 | 24.70 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 54 | 11 | 1.90 | 8.81 | 26.00 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 47 | 0 | 2.55 | 8.38 | 14.36 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 214 | 20 | 1.80 | 7.72 | 22.96 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 57 | 30 | 5.25 | 26.56 | 34.08 |
| `n6_vs_a100` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 100 | 0 | 1.39 | 2.57 | 9.65 |
| `n6_vs_a100` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 275 | 46 | 1.58 | 4.66 | 19.12 |
| `n6_vs_a100` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 317 | 0 | 1.15 | 1.19 | 2.45 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 20 | 6 | 13.16 | 16.84 | 18.52 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 639 | 0 | 1.15 | 5.99 | 9.19 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 324 | 0 | 2.95 | 10.74 | 16.75 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 649 | 81 | 1.44 | 4.13 | 18.91 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 498 | 64 | 1.17 | 2.10 | 17.67 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `compute` | 20 | 6 | 13.16 | 16.84 | 18.52 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 639 | 0 | 1.12 | 5.77 | 9.30 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 324 | 22 | 2.72 | 11.16 | 23.56 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 649 | 95 | 1.59 | 4.22 | 24.39 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 498 | 160 | 1.98 | 2.58 | 37.99 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 134 | 0 | 1.08 | 1.46 | 8.97 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `layer_fixed_latency` | 371 | 0 | 1.13 | 1.22 | 3.80 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 218 | 42 | 1.56 | 8.34 | 19.07 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 14 | 0 | 1.10 | 1.16 | 1.44 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 300 | 0 | 1.06 | 4.22 | 7.76 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 380 | 7 | 2.81 | 11.19 | 17.50 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 627 | 77 | 1.31 | 3.73 | 18.81 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `thermal` | 338 | 0 | 1.65 | 4.26 | 8.51 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 560 | 28 | 1.03 | 1.76 | 17.27 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 300 | 0 | 1.05 | 4.22 | 8.08 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 380 | 9 | 2.62 | 11.41 | 21.21 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 627 | 85 | 1.55 | 3.93 | 27.45 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `thermal` | 338 | 0 | 1.70 | 4.35 | 8.99 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 560 | 180 | 1.86 | 2.55 | 37.99 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 128 | 0 | 1.44 | 2.57 | 4.00 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `layer_fixed_latency` | 131 | 0 | 1.21 | 1.36 | 2.45 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 168 | 46 | 2.10 | 10.39 | 19.12 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 167 | 0 | 1.15 | 1.17 | 1.33 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 6 | 0 | 12.06 | 13.40 | 13.59 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 639 | 0 | 1.04 | 2.85 | 9.13 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `layer_fixed_latency` | 311 | 0 | 2.81 | 10.56 | 16.46 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 638 | 80 | 1.34 | 4.09 | 18.87 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 495 | 34 | 1.06 | 1.76 | 17.27 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `compute` | 6 | 0 | 12.06 | 13.40 | 13.59 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 639 | 0 | 1.06 | 2.73 | 9.16 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `layer_fixed_latency` | 311 | 12 | 2.63 | 10.64 | 21.22 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 638 | 94 | 1.56 | 4.21 | 24.39 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 495 | 166 | 1.98 | 2.46 | 37.99 |

## Per model, per context, per batch and per design class

Each row is that class's **fastest** feasible design at that batch, read against the iso-area GPU comparator the published study already chose for it. The `densest` pick of every class is in `analytical.json` beside it.

**The ROM-versus-GPU ratio under speculation is `T_cycle(GPU) / T_cycle(ROM)` and carries no `tau` at all.** The acceptance length is a property of the model and its drafter, not of the machine, so it is the same on both sides and cancels out of the ratio. Every movement in the last column is therefore a machine effect and nothing else.

### `n5_vs_b200-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,178.5 | 3,157.1-5,860.0 | 5.61 | yes | `b200_sxm-x90-nvl72-hybrid` | 697.1 | 1,647.5-3,058.1 | 1.79 | yes | 5.994x | 1.916x | 0.320x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3,806.2 | 1,310.9-2,433.2 | 12.31 | **no** | `b200_sxm-x87-nvl72-hybrid` | 696.4 | 1,628.6-3,022.9 | 1.81 | yes | 5.465x | 0.805x | 0.147x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,178.5 | 3,157.1-5,860.0 | 5.61 | yes | `b200_sxm-x90-nvl72-hybrid` | 697.1 | 1,647.5-3,058.1 | 1.79 | yes | 5.994x | 1.916x | 0.320x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3,806.2 | 1,310.9-2,433.2 | 12.31 | **no** | `b200_sxm-x87-nvl72-hybrid` | 696.4 | 1,628.6-3,022.9 | 1.81 | yes | 5.465x | 0.805x | 0.147x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,178.5 | 3,157.1-5,860.0 | 5.61 | yes | `b200_sxm-x90-nvl72-hybrid` | 686.1 | 1,509.9-2,802.5 | 1.93 | yes | 6.090x | 2.091x | 0.343x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3,806.2 | 1,310.9-2,433.2 | 12.31 | **no** | `b200_sxm-x87-nvl72-hybrid` | 685.2 | 1,492.8-2,770.8 | 1.95 | yes | 5.555x | 0.878x | 0.158x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,178.5 | 3,157.1-5,860.0 | 5.61 | yes | `b200_sxm-x90-nvl72-hybrid` | 665.8 | 1,258.4-2,335.7 | 2.24 | yes | 6.276x | 2.509x | 0.400x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3,806.2 | 1,310.9-2,433.2 | 12.31 | **no** | `b200_sxm-x87-nvl72-hybrid` | 664.3 | 1,240.0-2,301.5 | 2.27 | yes | 5.729x | 1.057x | 0.185x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,177.6 | 2,126.4-3,946.9 | 8.33 | **no** | `b200_sxm-x90-nvl72-hybrid` | 634.4 | 1,063.0-1,973.1 | 2.53 | yes | 6.585x | 2.000x | 0.304x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3,806.2 | 1,310.9-2,433.2 | 12.31 | **no** | `b200_sxm-x87-nvl72-hybrid` | 635.9 | 642.5-1,192.5 | 4.20 | yes | 5.986x | 2.040x | 0.341x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 4,126.3 | 2,087.1-3,874.0 | 8.38 | **no** | `b200_sxm-x134-nvl72-hybrid` | 618.2 | 624.5-1,159.2 | 4.20 | yes | 6.675x | 3.342x | 0.501x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3,806.2 | 1,310.9-2,433.2 | 12.31 | **no** | `b200_sxm-x87-nvl72-hybrid` | 590.0 | 555.2-1,030.6 | 4.51 | yes | 6.451x | 2.361x | 0.366x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 4,055.8 | 1,191.9-2,212.3 | 14.43 | **no** | `b200_sxm-x134-nvl72-hybrid` | 563.2 | 515.2-956.2 | 4.64 | yes | 7.201x | 2.314x | 0.321x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 3,742.6 | 1,329.6-2,467.9 | 11.94 | **no** | `b200_sxm-x116-nvl72-hybrid` | 548.5 | 488.9-907.5 | 4.76 | yes | 6.824x | 2.720x | 0.399x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 3,337.7 | 742.6-1,378.3 | 19.06 | **no** | `b200_sxm-x179-nvl72-hybrid` | 418.9 | 410.9-762.7 | 4.32 | yes | 7.969x | 1.807x | 0.227x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,452.7 | 578.1-1,073.1 | 25.32 | **no** | `b200_sxm-x347-nvl72-hybrid` | 501.3 | 462.6-858.6 | 4.60 | yes | 6.887x | 1.250x | 0.181x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 1,644.4 | 294.2-546.1 | 23.70 | **no** | `b200_sxm-x179-nvl72-hybrid` | 235.5 | 196.2-364.3 | 5.09 | yes | 6.982x | 1.499x | 0.215x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,136.9 | 242.8-450.7 | 37.31 | **no** | `b200_sxm-x347-nvl72-hybrid` | 302.6 | 308.8-573.3 | 4.15 | yes | 7.062x | 0.786x | 0.111x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 559.3 | 88.1-163.5 | 26.93 | **no** | `b200_sxm-x179-nvl72-hybrid` | 133.2 | 57.2-106.1 | 9.88 | **no** | 4.197x | 1.540x | 0.367x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 670.3 | 201.4-373.8 | 14.11 | **no** | `b200_sxm-x347-nvl72-hybrid` | 159.6 | 81.3-150.9 | 8.32 | **no** | 4.201x | 2.477x | 0.590x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.111x to 0.590x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 4 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,144.8 | 2,597.6-4,821.5 | 6.77 | yes | `a100_sxm_80gb-x258-hybrid` | 358.7 | 194.5-361.0 | 7.82 | yes | 11.556x | 13.354x | 1.156x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,636.7 | 1,668.5-3,096.9 | 9.24 | **no** | `a100_sxm_80gb-x224-hybrid` | 363.9 | 199.3-370.0 | 7.74 | yes | 9.995x | 8.371x | 0.838x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,144.8 | 2,597.6-4,821.5 | 6.77 | yes | `a100_sxm_80gb-x258-hybrid` | 358.7 | 194.5-361.0 | 7.82 | yes | 11.556x | 13.354x | 1.156x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,636.7 | 1,668.5-3,096.9 | 9.24 | **no** | `a100_sxm_80gb-x224-hybrid` | 363.9 | 199.3-370.0 | 7.74 | yes | 9.995x | 8.371x | 0.838x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,144.8 | 2,597.6-4,821.5 | 6.77 | yes | `a100_sxm_80gb-x258-hybrid` | 358.7 | 194.5-361.0 | 7.82 | yes | 11.556x | 13.354x | 1.156x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,636.7 | 1,668.5-3,096.9 | 9.24 | **no** | `a100_sxm_80gb-x224-hybrid` | 363.9 | 199.3-370.0 | 7.74 | yes | 9.995x | 8.371x | 0.838x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,144.8 | 2,597.6-4,821.5 | 6.77 | yes | `a100_sxm_80gb-x258-hybrid` | 358.7 | 194.5-361.0 | 7.82 | yes | 11.556x | 13.354x | 1.156x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,636.7 | 1,668.5-3,096.9 | 9.24 | **no** | `a100_sxm_80gb-x224-hybrid` | 363.9 | 199.3-370.0 | 7.74 | yes | 9.995x | 8.371x | 0.838x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,144.8 | 2,597.6-4,821.5 | 6.77 | yes | `a100_sxm_80gb-x258-hybrid` | 358.7 | 194.5-361.0 | 7.82 | yes | 11.556x | 13.354x | 1.156x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,636.7 | 1,668.5-3,096.9 | 9.24 | **no** | `a100_sxm_80gb-x224-hybrid` | 363.9 | 199.3-370.0 | 7.74 | yes | 9.995x | 8.371x | 0.838x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,089.0 | 1,644.6-3,052.7 | 10.54 | **no** | `a100_sxm_80gb-x258-hybrid` | 358.7 | 194.5-361.0 | 7.82 | yes | 11.400x | 8.455x | 0.742x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3,582.7 | 1,667.0-3,094.2 | 9.11 | **no** | `a100_sxm_80gb-x336-hybrid` | 357.8 | 197.2-366.0 | 7.69 | yes | 10.013x | 8.453x | 0.844x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,982.2 | 903.5-1,677.1 | 18.69 | **no** | `a100_sxm_80gb-x258-hybrid` | 317.5 | 174.6-324.0 | 7.71 | yes | 12.543x | 5.176x | 0.413x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,551.0 | 1,493.0-2,771.2 | 10.08 | **no** | `a100_sxm_80gb-x672-hybrid` | 357.8 | 199.9-371.0 | 7.59 | yes | 9.924x | 7.469x | 0.753x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 3,006.5 | 429.6-797.4 | 29.67 | **no** | `a100_sxm_80gb-x335-hybrid` | 210.7 | 125.0-231.9 | 7.15 | yes | 14.269x | 3.438x | 0.241x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,082.4 | 674.6-1,252.1 | 19.37 | **no** | `a100_sxm_80gb-x672-hybrid` | 278.5 | 159.1-295.3 | 7.42 | yes | 11.067x | 4.240x | 0.383x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,196.0 | 157.1-291.6 | 32.28 | **no** | `a100_sxm_80gb-x337-hybrid` | 94.1 | 66.5-123.5 | 6.00 | yes | 12.713x | 2.362x | 0.186x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,667.0 | 175.6-326.0 | 40.25 | **no** | `a100_sxm_80gb-x672-hybrid` | 144.9 | 84.2-156.4 | 7.29 | yes | 11.506x | 2.085x | 0.181x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 331.6 | 50.6-94.0 | 27.77 | **no** | `a100_sxm_80gb-x337-hybrid` | 36.8 | 16.6-30.9 | 9.37 | **no** | 9.024x | 3.045x | 0.337x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 602.0 | 134.6-249.8 | 18.97 | **no** | `a100_sxm_80gb-x672-hybrid` | 57.8 | 50.9-94.5 | 4.82 | yes | 10.408x | 2.643x | 0.254x |

**Does the ratio compress?** Of 20 class rows in this study, 15 move the ROM-versus-GPU ratio DOWN under speculation and 5 move it UP. The movement spans 0.181x to 1.156x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 5 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 4,105.0 | 2,783.6-5,166.8 | 6.25 | yes | `b200_sxm-x112-nvl72-hybrid` | 700.7 | 1,763.5-3,273.2 | 1.68 | yes | 5.859x | 1.579x | 0.269x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 3,405.8 | 1,686.2-3,129.9 | 8.56 | **no** | `b200_sxm-x173-nvl72-hybrid` | 699.6 | 1,768.8-3,283.2 | 1.68 | yes | 4.868x | 0.953x | 0.196x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 4,105.0 | 2,783.6-5,166.8 | 6.25 | yes | `b200_sxm-x112-nvl72-hybrid` | 700.7 | 1,763.5-3,273.2 | 1.68 | yes | 5.859x | 1.579x | 0.269x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 3,405.8 | 1,686.2-3,129.9 | 8.56 | **no** | `b200_sxm-x173-nvl72-hybrid` | 699.6 | 1,768.8-3,283.2 | 1.68 | yes | 4.868x | 0.953x | 0.196x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 4,105.0 | 2,783.6-5,166.8 | 6.25 | yes | `b200_sxm-x112-nvl72-hybrid` | 690.6 | 1,613.4-2,994.7 | 1.81 | yes | 5.944x | 1.725x | 0.290x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 3,405.8 | 1,686.2-3,129.9 | 8.56 | **no** | `b200_sxm-x173-nvl72-hybrid` | 696.2 | 1,710.8-3,175.4 | 1.73 | yes | 4.892x | 0.986x | 0.201x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 4,105.0 | 2,783.6-5,166.8 | 6.25 | yes | `b200_sxm-x112-nvl72-hybrid` | 671.6 | 1,377.3-2,556.4 | 2.07 | yes | 6.113x | 2.021x | 0.331x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 3,405.8 | 1,686.2-3,129.9 | 8.56 | **no** | `b200_sxm-x173-nvl72-hybrid` | 682.7 | 1,515.5-2,812.9 | 1.91 | yes | 4.989x | 1.113x | 0.223x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 4,095.4 | 2,868.2-5,323.8 | 6.05 | yes | `b200_sxm-x134-nvl72-hybrid` | 649.6 | 1,146.7-2,128.4 | 2.40 | yes | 6.304x | 2.501x | 0.397x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 3,405.8 | 1,686.2-3,129.9 | 8.56 | **no** | `b200_sxm-x173-nvl72-hybrid` | 659.8 | 1,230.0-2,283.0 | 2.27 | yes | 5.162x | 1.371x | 0.266x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 4,000.6 | 1,924.3-3,571.8 | 8.81 | **no** | `b200_sxm-x134-nvl72-hybrid` | 615.5 | 623.3-1,156.9 | 4.19 | yes | 6.500x | 3.087x | 0.475x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 3,405.8 | 1,686.2-3,129.9 | 8.56 | **no** | `b200_sxm-x173-nvl72-hybrid` | 626.7 | 645.2-1,197.5 | 4.12 | yes | 5.435x | 2.614x | 0.481x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 3,833.7 | 1,476.6-2,740.8 | 11.01 | **no** | `b200_sxm-x179-nvl72-hybrid` | 581.3 | 551.8-1,024.3 | 4.47 | yes | 6.595x | 2.676x | 0.406x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,312.3 | 1,419.5-2,634.9 | 9.89 | **no** | `b200_sxm-x347-nvl72-hybrid` | 616.5 | 646.7-1,200.3 | 4.04 | yes | 5.373x | 2.195x | 0.409x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 3,022.0 | 632.2-1,173.5 | 20.27 | **no** | `b200_sxm-x179-nvl72-hybrid` | 411.5 | 408.2-757.6 | 4.28 | yes | 7.343x | 1.549x | 0.211x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,613.1 | 645.5-1,198.1 | 17.17 | **no** | `b200_sxm-x347-nvl72-hybrid` | 495.9 | 460.7-855.2 | 4.56 | yes | 5.269x | 1.401x | 0.266x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 1,271.5 | 171.0-317.4 | 31.52 | **no** | `b200_sxm-x179-nvl72-hybrid` | 226.5 | 194.7-361.4 | 4.93 | yes | 5.614x | 0.878x | 0.156x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,244.9 | 169.6-314.8 | 31.12 | **no** | `b200_sxm-x347-nvl72-hybrid` | 294.8 | 306.7-569.3 | 4.08 | yes | 4.223x | 0.553x | 0.131x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 364.1 | 58.9-109.3 | 26.21 | **no** | `b200_sxm-x179-nvl72-hybrid` | 122.2 | 55.4-102.8 | 9.36 | **no** | 2.979x | 1.063x | 0.357x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 359.2 | 93.5-173.6 | 16.29 | **no** | `b200_sxm-x347-nvl72-hybrid` | 151.1 | 79.5-147.5 | 8.06 | **no** | 2.377x | 1.177x | 0.495x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.131x to 0.495x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 5 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,023.9 | 2,232.7-4,144.2 | 7.64 | yes | `a100_sxm_80gb-x312-hybrid` | 356.5 | 197.0-365.7 | 7.67 | yes | 11.289x | 11.331x | 1.004x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 3,061.6 | 904.9-1,679.6 | 14.35 | **no** | `a100_sxm_80gb-x168-hybrid` | 365.5 | 200.2-371.6 | 7.74 | yes | 8.375x | 4.520x | 0.540x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,023.9 | 2,232.7-4,144.2 | 7.64 | yes | `a100_sxm_80gb-x312-hybrid` | 356.5 | 197.0-365.7 | 7.67 | yes | 11.289x | 11.331x | 1.004x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,838.2 | 2,382.7-4,422.6 | 5.05 | yes | `a100_sxm_80gb-x336-hybrid` | 356.0 | 197.1-365.8 | 7.66 | yes | 7.974x | 12.092x | 1.516x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,023.9 | 2,232.7-4,144.2 | 7.64 | yes | `a100_sxm_80gb-x312-hybrid` | 356.5 | 197.0-365.7 | 7.67 | yes | 11.289x | 11.331x | 1.004x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,838.2 | 2,382.7-4,422.6 | 5.05 | yes | `a100_sxm_80gb-x336-hybrid` | 356.0 | 197.1-365.8 | 7.66 | yes | 7.974x | 12.092x | 1.516x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,023.9 | 2,232.7-4,144.2 | 7.64 | yes | `a100_sxm_80gb-x312-hybrid` | 356.5 | 197.0-365.7 | 7.67 | yes | 11.289x | 11.331x | 1.004x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,838.2 | 2,382.7-4,422.6 | 5.05 | yes | `a100_sxm_80gb-x336-hybrid` | 356.0 | 197.1-365.8 | 7.66 | yes | 7.974x | 12.092x | 1.516x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,023.9 | 2,232.7-4,144.2 | 7.64 | yes | `a100_sxm_80gb-x312-hybrid` | 356.5 | 197.0-365.7 | 7.67 | yes | 11.289x | 11.331x | 1.004x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,838.2 | 2,382.7-4,422.6 | 5.05 | yes | `a100_sxm_80gb-x336-hybrid` | 356.0 | 197.1-365.8 | 7.66 | yes | 7.974x | 12.092x | 1.516x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,868.8 | 1,400.4-2,599.3 | 11.71 | **no** | `a100_sxm_80gb-x337-hybrid` | 353.6 | 193.7-359.6 | 7.74 | yes | 10.941x | 7.228x | 0.661x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,819.4 | 1,708.0-3,170.3 | 7.00 | yes | `a100_sxm_80gb-x672-hybrid` | 356.0 | 199.7-370.7 | 7.56 | yes | 7.921x | 8.551x | 1.080x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,628.0 | 1,138.4-2,113.0 | 13.51 | **no** | `a100_sxm_80gb-x337-hybrid` | 330.1 | 181.4-336.7 | 7.71 | yes | 10.992x | 6.275x | 0.571x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,770.9 | 992.2-1,841.7 | 11.84 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 199.7-370.7 | 7.56 | yes | 7.785x | 4.968x | 0.638x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 2,473.4 | 326.3-605.7 | 32.14 | **no** | `a100_sxm_80gb-x337-hybrid` | 207.3 | 124.4-230.8 | 7.07 | yes | 11.930x | 2.624x | 0.220x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,747.9 | 492.6-914.4 | 15.04 | **no** | `a100_sxm_80gb-x672-hybrid` | 275.1 | 158.8-294.7 | 7.35 | yes | 6.353x | 3.103x | 0.488x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 834.4 | 109.4-203.0 | 32.35 | **no** | `a100_sxm_80gb-x337-hybrid` | 91.1 | 66.1-122.7 | 5.84 | yes | 9.164x | 1.654x | 0.181x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 596.8 | 127.5-236.7 | 19.85 | **no** | `a100_sxm_80gb-x672-hybrid` | 141.3 | 83.9-155.8 | 7.14 | yes | 4.225x | 1.519x | 0.360x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 223.3 | 34.8-64.6 | 27.20 | **no** | `a100_sxm_80gb-x337-hybrid` | 34.9 | 14.6-27.1 | 10.16 | **no** | 6.392x | 2.387x | 0.374x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 156.6 | 77.8-144.4 | 8.53 | **no** | `a100_sxm_80gb-x672-hybrid` | 55.6 | 45.3-84.1 | 5.20 | yes | 2.818x | 1.718x | 0.610x |

**Does the ratio compress?** Of 20 class rows in this study, 10 move the ROM-versus-GPU ratio DOWN under speculation and 10 move it UP. The movement spans 0.181x to 1.516x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 10 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,207.2 | 2,325.6-4,316.7 | 7.67 | yes | `b200_sxm-x90-nvl72-hybrid` | 697.2 | 1,647.7-3,058.3 | 1.79 | yes | 6.035x | 1.411x | 0.234x |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,011.9 | 1,468.3-2,725.4 | 11.58 | **no** | `b200_sxm-x87-nvl72-hybrid` | 696.5 | 1,628.7-3,023.2 | 1.81 | yes | 5.760x | 0.902x | 0.157x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,207.2 | 2,325.6-4,316.7 | 7.67 | yes | `b200_sxm-x90-nvl72-hybrid` | 697.2 | 1,647.7-3,058.3 | 1.79 | yes | 6.035x | 1.411x | 0.234x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,011.9 | 1,468.3-2,725.4 | 11.58 | **no** | `b200_sxm-x87-nvl72-hybrid` | 696.5 | 1,628.7-3,023.2 | 1.81 | yes | 5.760x | 0.902x | 0.157x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,207.2 | 2,325.6-4,316.7 | 7.67 | yes | `b200_sxm-x90-nvl72-hybrid` | 686.3 | 1,510.1-2,802.9 | 1.93 | yes | 6.130x | 1.540x | 0.251x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,011.9 | 1,468.3-2,725.4 | 11.58 | **no** | `b200_sxm-x87-nvl72-hybrid` | 685.4 | 1,493.0-2,771.3 | 1.95 | yes | 5.853x | 0.983x | 0.168x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,207.2 | 2,325.6-4,316.7 | 7.67 | yes | `b200_sxm-x90-nvl72-hybrid` | 666.1 | 1,258.7-2,336.4 | 2.24 | yes | 6.317x | 1.848x | 0.292x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,011.9 | 1,468.3-2,725.4 | 11.58 | **no** | `b200_sxm-x87-nvl72-hybrid` | 664.6 | 1,240.3-2,302.1 | 2.27 | yes | 6.036x | 1.184x | 0.196x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,207.2 | 2,325.6-4,316.7 | 7.67 | yes | `b200_sxm-x90-nvl72-hybrid` | 634.9 | 1,063.5-1,974.0 | 2.53 | yes | 6.626x | 2.187x | 0.330x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,011.9 | 1,468.3-2,725.4 | 11.58 | **no** | `b200_sxm-x87-nvl72-hybrid` | 636.4 | 642.6-1,192.8 | 4.20 | yes | 6.304x | 2.285x | 0.362x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,160.7 | 1,322.0-2,453.7 | 13.34 | **no** | `b200_sxm-x90-nvl72-hybrid` | 590.7 | 539.9-1,002.1 | 4.64 | yes | 7.043x | 2.449x | 0.348x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,011.9 | 1,468.3-2,725.4 | 11.58 | **no** | `b200_sxm-x87-nvl72-hybrid` | 591.0 | 555.6-1,031.2 | 4.51 | yes | 6.789x | 2.643x | 0.389x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 4,140.5 | 1,135.7-2,108.1 | 15.46 | **no** | `b200_sxm-x134-nvl72-hybrid` | 564.4 | 515.6-957.0 | 4.64 | yes | 7.336x | 2.203x | 0.300x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3,980.3 | 783.6-1,454.5 | 21.54 | **no** | `b200_sxm-x87-nvl72-hybrid` | 519.1 | 464.4-861.9 | 4.74 | yes | 7.668x | 1.687x | 0.220x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 3,417.9 | 503.0-933.5 | 28.81 | **no** | `b200_sxm-x179-nvl72-hybrid` | 420.8 | 411.6-764.0 | 4.33 | yes | 8.123x | 1.222x | 0.150x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,822.3 | 649.3-1,205.2 | 24.96 | **no** | `b200_sxm-x347-nvl72-hybrid` | 502.8 | 463.0-859.4 | 4.60 | yes | 7.603x | 1.402x | 0.184x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,717.0 | 315.4-585.4 | 23.08 | **no** | `b200_sxm-x173-nvl72-hybrid` | 235.8 | 186.9-346.9 | 5.35 | yes | 7.281x | 1.687x | 0.232x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,420.0 | 271.8-504.6 | 37.75 | **no** | `b200_sxm-x347-nvl72-hybrid` | 304.7 | 309.4-574.3 | 4.18 | yes | 7.943x | 0.879x | 0.111x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 621.2 | 96.5-179.1 | 27.29 | **no** | `b200_sxm-x173-nvl72-hybrid` | 133.8 | 53.6-99.4 | 10.59 | **no** | 4.642x | 1.802x | 0.388x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 768.7 | 108.8-202.0 | 29.95 | **no** | `b200_sxm-x347-nvl72-hybrid` | 161.9 | 81.8-151.8 | 8.39 | **no** | 4.749x | 1.330x | 0.280x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.111x to 0.389x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 5 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 4,186.3 | 2,499.6-4,639.6 | 7.10 | yes | `a100_sxm_80gb-x203-hybrid` | 362.5 | 195.5-362.8 | 7.86 | yes | 11.548x | 12.789x | 1.107x |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,855.8 | 1,044.4-1,938.5 | 15.65 | **no** | `a100_sxm_80gb-x224-hybrid` | 364.4 | 199.4-370.0 | 7.75 | yes | 10.582x | 5.239x | 0.495x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 4,186.3 | 2,499.6-4,639.6 | 7.10 | yes | `a100_sxm_80gb-x203-hybrid` | 362.5 | 195.5-362.8 | 7.86 | yes | 11.548x | 12.789x | 1.107x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,855.8 | 1,044.4-1,938.5 | 15.65 | **no** | `a100_sxm_80gb-x224-hybrid` | 364.4 | 199.4-370.0 | 7.75 | yes | 10.582x | 5.239x | 0.495x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 4,186.3 | 2,499.6-4,639.6 | 7.10 | yes | `a100_sxm_80gb-x203-hybrid` | 362.5 | 195.5-362.8 | 7.86 | yes | 11.548x | 12.789x | 1.107x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,855.8 | 1,044.4-1,938.5 | 15.65 | **no** | `a100_sxm_80gb-x224-hybrid` | 364.4 | 199.4-370.0 | 7.75 | yes | 10.582x | 5.239x | 0.495x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 4,186.3 | 2,499.6-4,639.6 | 7.10 | yes | `a100_sxm_80gb-x203-hybrid` | 362.5 | 195.5-362.8 | 7.86 | yes | 11.548x | 12.789x | 1.107x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,855.8 | 1,044.4-1,938.5 | 15.65 | **no** | `a100_sxm_80gb-x224-hybrid` | 364.4 | 199.4-370.0 | 7.75 | yes | 10.582x | 5.239x | 0.495x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 4,180.4 | 2,745.9-5,096.8 | 6.46 | yes | `a100_sxm_80gb-x244-hybrid` | 361.0 | 196.1-363.9 | 7.81 | yes | 11.582x | 14.006x | 1.209x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,855.8 | 1,044.4-1,938.5 | 15.65 | **no** | `a100_sxm_80gb-x224-hybrid` | 364.4 | 199.4-370.0 | 7.75 | yes | 10.582x | 5.239x | 0.495x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 4,125.1 | 1,730.7-3,212.4 | 10.11 | **no** | `a100_sxm_80gb-x244-hybrid` | 359.4 | 195.2-362.4 | 7.81 | yes | 11.479x | 8.865x | 0.772x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,855.8 | 1,044.4-1,938.5 | 15.65 | **no** | `a100_sxm_80gb-x224-hybrid` | 357.5 | 195.8-363.5 | 7.74 | yes | 10.785x | 5.333x | 0.494x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 4,094.0 | 955.9-1,774.3 | 18.16 | **no** | `a100_sxm_80gb-x244-hybrid` | 315.5 | 174.2-323.4 | 7.68 | yes | 12.977x | 5.487x | 0.423x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,768.1 | 914.9-1,698.2 | 17.46 | **no** | `a100_sxm_80gb-x448-hybrid` | 351.3 | 194.7-361.4 | 7.65 | yes | 10.727x | 4.699x | 0.438x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,180.2 | 646.2-1,199.4 | 20.87 | **no** | `a100_sxm_80gb-x337-hybrid` | 212.2 | 124.8-231.7 | 7.21 | yes | 14.987x | 5.177x | 0.345x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,449.4 | 471.5-875.1 | 31.02 | **no** | `a100_sxm_80gb-x672-hybrid` | 279.4 | 159.2-295.4 | 7.44 | yes | 12.346x | 2.962x | 0.240x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,346.4 | 177.0-328.5 | 32.26 | **no** | `a100_sxm_80gb-x337-hybrid` | 94.9 | 66.6-123.7 | 6.04 | yes | 14.190x | 2.656x | 0.187x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,891.5 | 196.1-364.0 | 40.90 | **no** | `a100_sxm_80gb-x672-hybrid` | 145.8 | 84.3-156.5 | 7.33 | yes | 12.970x | 2.325x | 0.179x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 379.7 | 57.4-106.6 | 28.04 | **no** | `a100_sxm_80gb-x337-hybrid` | 37.2 | 17.3-32.0 | 9.15 | **no** | 10.195x | 3.328x | 0.326x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 704.5 | 155.4-288.4 | 19.22 | **no** | `a100_sxm_80gb-x672-hybrid` | 58.5 | 52.5-97.4 | 4.72 | yes | 12.051x | 2.960x | 0.246x |

**Does the ratio compress?** Of 20 class rows in this study, 15 move the ROM-versus-GPU ratio DOWN under speculation and 5 move it UP. The movement spans 0.179x to 1.209x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 5 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 3,529.6-6,551.4 | 5.07 | yes | `b200_sxm-x49-nvl72-tensor` | 701.4 | 2,291.9-4,254.0 | 1.30 | yes | 6.021x | 1.540x | 0.256x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x10-romfill` | 4,004.0 | 2,129.9-3,953.4 | 7.97 | **no** | `b200_sxm-x289-nvl72-hybrid` | 697.0 | 2,250.8-4,177.9 | 1.31 | yes | 5.744x | 0.946x | 0.165x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 3,529.6-6,551.4 | 5.07 | yes | `b200_sxm-x49-nvl72-tensor` | 691.5 | 2,060.5-3,824.6 | 1.42 | yes | 6.107x | 1.713x | 0.280x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 2,155.9-4,001.7 | 7.59 | yes | `b200_sxm-x58-nvl72-tensor` | 694.8 | 2,084.9-3,869.9 | 1.41 | yes | 5.551x | 1.034x | 0.186x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 3,529.6-6,551.4 | 5.07 | yes | `b200_sxm-x49-nvl72-tensor` | 672.8 | 1,725.0-3,201.8 | 1.65 | yes | 6.277x | 2.046x | 0.326x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 2,155.9-4,001.7 | 7.59 | yes | `b200_sxm-x58-nvl72-tensor` | 677.4 | 1,746.6-3,241.9 | 1.64 | yes | 5.694x | 1.234x | 0.217x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 3,529.6-6,551.4 | 5.07 | yes | `b200_sxm-x49-nvl72-tensor` | 639.3 | 1,329.5-2,467.7 | 2.04 | yes | 6.606x | 2.655x | 0.402x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 2,155.9-4,001.7 | 7.59 | yes | `b200_sxm-x58-nvl72-tensor` | 645.9 | 1,340.5-2,488.2 | 2.04 | yes | 5.972x | 1.608x | 0.269x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 4,185.8 | 3,413.6-6,336.1 | 5.20 | yes | `b200_sxm-x83-nvl72-hybrid` | 630.8 | 1,570.4-2,914.8 | 1.70 | yes | 6.636x | 2.174x | 0.328x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 2,155.9-4,001.7 | 7.59 | yes | `b200_sxm-x58-hybrid` | 603.2 | 1,297.1-2,407.5 | 1.97 | yes | 6.395x | 1.662x | 0.260x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,120.6 | 3,355.9-6,229.0 | 5.21 | yes | `b200_sxm-x173-nvl72-hybrid` | 628.8 | 1,639.5-3,043.2 | 1.63 | yes | 6.553x | 2.047x | 0.312x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 3,820.4 | 2,310.8-4,289.1 | 7.01 | yes | `b200_sxm-x116-nvl72-hybrid` | 608.9 | 1,456.9-2,704.3 | 1.77 | yes | 6.275x | 1.586x | 0.253x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,097.3 | 2,135.9-3,964.4 | 8.13 | **no** | `b200_sxm-x173-nvl72-hybrid` | 583.0 | 1,217.9-2,260.5 | 2.03 | yes | 7.028x | 1.754x | 0.250x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,820.4 | 2,310.8-4,289.1 | 7.01 | yes | `b200_sxm-x231-nvl72-hybrid` | 601.3 | 1,455.2-2,701.1 | 1.75 | yes | 6.354x | 1.588x | 0.250x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,564.4 | 959.5-1,781.0 | 15.75 | **no** | `b200_sxm-x173-nvl72-hybrid` | 414.3 | 704.0-1,306.7 | 2.50 | yes | 8.604x | 1.363x | 0.158x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,659.2 | 1,298.1-2,409.5 | 11.95 | **no** | `b200_sxm-x347-nvl72-hybrid` | 501.3 | 853.4-1,583.9 | 2.49 | yes | 7.299x | 1.521x | 0.208x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,477.7 | 320.4-594.7 | 19.56 | **no** | `b200_sxm-x173-nvl72-hybrid` | 233.3 | 204.4-379.4 | 4.84 | yes | 6.333x | 1.567x | 0.247x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,613.9 | 548.1-1,017.3 | 20.22 | **no** | `b200_sxm-x347-nvl72-hybrid` | 302.6 | 434.4-806.3 | 2.95 | yes | 8.638x | 1.262x | 0.146x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 434.5 | 134.6-249.8 | 13.69 | **no** | `b200_sxm-x173-nvl72-hybrid` | 130.7 | 56.5-104.9 | 9.80 | **no** | 3.325x | 2.381x | 0.716x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 871.3 | 203.6-377.8 | 18.15 | **no** | `b200_sxm-x347-nvl72-hybrid` | 159.6 | 85.2-158.2 | 7.94 | **no** | 5.461x | 2.388x | 0.437x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.146x to 0.716x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 12 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 3,785.1-7,025.6 | 4.68 | yes | `a100_sxm_80gb-x136-hybrid` | 369.6 | 732.8-1,360.2 | 2.14 | yes | 11.302x | 5.165x | 0.457x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 3,902.1 | 1,611.3-2,990.8 | 10.27 | **no** | `a100_sxm_80gb-x672-hybrid` | 357.8 | 722.8-1,341.7 | 2.10 | yes | 10.906x | 2.229x | 0.204x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 3,785.1-7,025.6 | 4.68 | yes | `a100_sxm_80gb-x136-hybrid` | 369.6 | 732.8-1,360.2 | 2.14 | yes | 11.302x | 5.165x | 0.457x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 2,626.2-4,874.5 | 5.94 | yes | `a100_sxm_80gb-x168-hybrid` | 367.5 | 728.8-1,352.7 | 2.14 | yes | 10.004x | 3.604x | 0.360x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 3,785.1-7,025.6 | 4.68 | yes | `a100_sxm_80gb-x136-hybrid` | 369.6 | 732.8-1,360.2 | 2.14 | yes | 11.302x | 5.165x | 0.457x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 2,626.2-4,874.5 | 5.94 | yes | `a100_sxm_80gb-x168-hybrid` | 367.5 | 728.8-1,352.7 | 2.14 | yes | 10.004x | 3.604x | 0.360x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 3,785.1-7,025.6 | 4.68 | yes | `a100_sxm_80gb-x136-hybrid` | 369.6 | 732.8-1,360.2 | 2.14 | yes | 11.302x | 5.165x | 0.457x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 2,626.2-4,874.5 | 5.94 | yes | `a100_sxm_80gb-x168-hybrid` | 367.5 | 728.8-1,352.7 | 2.14 | yes | 10.004x | 3.604x | 0.360x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 4,159.2 | 2,785.7-5,170.6 | 6.33 | yes | `a100_sxm_80gb-x132-hybrid` | 366.0 | 719.7-1,335.8 | 2.16 | yes | 11.365x | 3.871x | 0.341x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 2,626.2-4,874.5 | 5.94 | yes | `a100_sxm_80gb-x168-hybrid` | 367.5 | 728.8-1,352.7 | 2.14 | yes | 10.004x | 3.604x | 0.360x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,087.6 | 2,733.7-5,074.2 | 6.34 | yes | `a100_sxm_80gb-x272-hybrid` | 360.8 | 701.4-1,301.8 | 2.18 | yes | 11.329x | 3.898x | 0.344x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,614.4 | 2,917.6-5,415.5 | 5.25 | yes | `a100_sxm_80gb-x448-hybrid` | 357.8 | 705.3-1,309.1 | 2.15 | yes | 10.102x | 4.137x | 0.410x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 3,995.9 | 1,638.5-3,041.2 | 10.34 | **no** | `a100_sxm_80gb-x272-hybrid` | 321.9 | 504.7-936.9 | 2.70 | yes | 12.415x | 3.246x | 0.261x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,613.0 | 2,907.0-5,395.7 | 5.27 | yes | `a100_sxm_80gb-x672-hybrid` | 357.8 | 722.8-1,341.7 | 2.10 | yes | 10.098x | 4.022x | 0.398x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,081.4 | 715.8-1,328.7 | 18.25 | **no** | `a100_sxm_80gb-x335-hybrid` | 210.7 | 228.7-424.4 | 3.91 | yes | 14.625x | 3.130x | 0.214x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,260.9 | 1,447.3-2,686.3 | 9.55 | **no** | `a100_sxm_80gb-x672-hybrid` | 278.5 | 375.0-696.1 | 3.15 | yes | 11.708x | 3.859x | 0.330x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 1,178.4 | 332.4-616.9 | 15.03 | **no** | `a100_sxm_80gb-x335-hybrid` | 93.8 | 128.7-238.9 | 3.09 | yes | 12.568x | 2.583x | 0.205x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,968.8 | 398.9-740.4 | 20.93 | **no** | `a100_sxm_80gb-x672-hybrid` | 144.9 | 167.2-310.4 | 3.67 | yes | 13.589x | 2.385x | 0.176x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 428.5 | 103.3-191.8 | 17.58 | **no** | `a100_sxm_80gb-x335-hybrid` | 36.7 | 19.1-35.5 | 8.12 | **no** | 11.688x | 5.396x | 0.462x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 602.0 | 148.0-274.7 | 17.25 | **no** | `a100_sxm_80gb-x672-hybrid` | 57.8 | 80.6-149.6 | 3.04 | yes | 10.408x | 1.836x | 0.176x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.176x to 0.462x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 12 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x192` | 4,153.1 | 3,332.3-6,185.2 | 5.28 | yes | `b200_sxm-x98-nvl72-hybrid` | 698.4 | 2,273.5-4,219.9 | 1.30 | yes | 5.947x | 1.466x | 0.246x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 3,781.0 | 1,832.4-3,401.1 | 8.75 | **no** | `b200_sxm-x347-nvl72-hybrid` | 699.2 | 2,264.5-4,203.2 | 1.31 | yes | 5.408x | 0.809x | 0.150x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4,134.7 | 3,932.2-7,298.7 | 4.46 | yes | `b200_sxm-x57-nvl72-tensor` | 694.0 | 2,081.4-3,863.3 | 1.41 | yes | 5.957x | 1.889x | 0.317x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 3,396.5 | 1,896.6-3,520.4 | 7.59 | yes | `b200_sxm-x144-nvl72-hybrid` | 704.1 | 2,326.3-4,317.9 | 1.28 | yes | 4.824x | 0.815x | 0.169x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4,134.7 | 3,932.2-7,298.7 | 4.46 | yes | `b200_sxm-x57-nvl72-tensor` | 676.0 | 1,742.8-3,235.0 | 1.64 | yes | 6.116x | 2.256x | 0.369x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 3,396.5 | 1,896.6-3,520.4 | 7.59 | yes | `b200_sxm-x144-nvl72-hybrid` | 695.0 | 2,076.9-3,854.9 | 1.42 | yes | 4.887x | 0.913x | 0.187x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x113` | 4,125.7 | 3,771.2-6,999.8 | 4.64 | yes | `b200_sxm-x58-nvl72-tensor` | 644.2 | 1,338.3-2,484.1 | 2.04 | yes | 6.405x | 2.818x | 0.440x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 3,396.5 | 1,896.6-3,520.4 | 7.59 | yes | `b200_sxm-x144-nvl72-hybrid` | 678.0 | 1,848.9-3,431.8 | 1.55 | yes | 5.010x | 1.026x | 0.205x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,064.8 | 3,063.6-5,686.5 | 5.63 | yes | `b200_sxm-x116-nvl72-hybrid` | 645.7 | 1,610.6-2,989.4 | 1.70 | yes | 6.295x | 1.902x | 0.302x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 3,396.5 | 1,896.6-3,520.4 | 7.59 | yes | `b200_sxm-x144-nvl72-hybrid` | 653.2 | 1,697.2-3,150.2 | 1.63 | yes | 5.200x | 1.118x | 0.215x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 3,956.8 | 2,281.9-4,235.5 | 7.35 | yes | `b200_sxm-x173-nvl72-hybrid` | 626.7 | 1,635.3-3,035.2 | 1.62 | yes | 6.314x | 1.395x | 0.221x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 3,396.5 | 1,896.6-3,520.4 | 7.59 | yes | `b200_sxm-x144-nvl72-hybrid` | 620.3 | 1,563.5-2,902.1 | 1.68 | yes | 5.476x | 1.213x | 0.222x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,762.8 | 1,775.7-3,295.9 | 8.98 | **no** | `b200_sxm-x173-nvl72-hybrid` | 579.3 | 1,212.6-2,250.7 | 2.03 | yes | 6.495x | 1.464x | 0.225x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,312.2 | 2,952.7-5,480.5 | 4.76 | yes | `b200_sxm-x347-nvl72-hybrid` | 616.5 | 1,637.7-3,039.8 | 1.60 | yes | 5.373x | 1.803x | 0.336x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,838.1 | 750.1-1,392.3 | 16.04 | **no** | `b200_sxm-x173-nvl72-hybrid` | 406.9 | 697.0-1,293.6 | 2.48 | yes | 6.975x | 1.076x | 0.154x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,613.0 | 1,449.0-2,689.5 | 7.65 | yes | `b200_sxm-x347-nvl72-hybrid` | 495.9 | 848.2-1,574.3 | 2.48 | yes | 5.269x | 1.708x | 0.324x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,055.2 | 313.9-582.7 | 14.25 | **no** | `b200_sxm-x173-nvl72-hybrid` | 224.2 | 202.7-376.2 | 4.69 | yes | 4.707x | 1.549x | 0.329x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,244.9 | 416.4-772.9 | 12.68 | **no** | `b200_sxm-x347-nvl72-hybrid` | 294.8 | 430.2-798.5 | 2.91 | yes | 4.223x | 0.968x | 0.229x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 366.9 | 95.9-177.9 | 16.23 | **no** | `b200_sxm-x173-nvl72-hybrid` | 119.7 | 55.4-102.9 | 9.16 | **no** | 3.065x | 1.730x | 0.564x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 358.0 | 151.6-281.5 | 10.01 | **no** | `b200_sxm-x347-nvl72-hybrid` | 151.1 | 84.0-156.0 | 7.63 | yes | 2.369x | 1.805x | 0.762x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.150x to 0.762x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 13 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x250` | 4,126.0 | 2,736.8-5,079.8 | 6.39 | yes | `a100_sxm_80gb-x247-hybrid` | 360.0 | 705.2-1,308.9 | 2.16 | yes | 11.462x | 3.881x | 0.339x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 3,597.6 | 1,344.8-2,496.1 | 11.34 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 720.8-1,337.9 | 2.09 | yes | 10.107x | 1.866x | 0.185x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,067.6 | 3,361.3-6,239.1 | 5.13 | yes | `a100_sxm_80gb-x155-hybrid` | 362.2 | 714.4-1,326.1 | 2.15 | yes | 11.229x | 4.705x | 0.419x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 2,866.0 | 2,436.2-4,521.9 | 4.99 | yes | `a100_sxm_80gb-x392-hybrid` | 356.0 | 696.1-1,292.0 | 2.17 | yes | 8.052x | 3.500x | 0.435x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,067.6 | 3,361.3-6,239.1 | 5.13 | yes | `a100_sxm_80gb-x155-hybrid` | 362.2 | 714.4-1,326.1 | 2.15 | yes | 11.229x | 4.705x | 0.419x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 2,866.0 | 2,436.2-4,521.9 | 4.99 | yes | `a100_sxm_80gb-x392-hybrid` | 356.0 | 696.1-1,292.0 | 2.17 | yes | 8.052x | 3.500x | 0.435x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,067.6 | 3,361.3-6,239.1 | 5.13 | yes | `a100_sxm_80gb-x155-hybrid` | 362.2 | 714.4-1,326.1 | 2.15 | yes | 11.229x | 4.705x | 0.419x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 2,866.0 | 2,436.2-4,521.9 | 4.99 | yes | `a100_sxm_80gb-x392-hybrid` | 356.0 | 696.1-1,292.0 | 2.17 | yes | 8.052x | 3.500x | 0.435x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 4,032.7 | 2,844.3-5,279.4 | 6.01 | yes | `a100_sxm_80gb-x272-hybrid` | 358.9 | 699.4-1,298.1 | 2.18 | yes | 11.236x | 4.067x | 0.362x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 2,866.0 | 2,436.2-4,521.9 | 4.99 | yes | `a100_sxm_80gb-x392-hybrid` | 356.0 | 696.1-1,292.0 | 2.17 | yes | 8.052x | 3.500x | 0.435x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 3,880.4 | 2,211.2-4,104.2 | 7.44 | yes | `a100_sxm_80gb-x335-hybrid` | 355.6 | 686.0-1,273.4 | 2.20 | yes | 10.912x | 3.223x | 0.295x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,790.6 | 1,758.7-3,264.4 | 6.73 | yes | `a100_sxm_80gb-x672-hybrid` | 356.0 | 720.8-1,337.9 | 2.09 | yes | 7.840x | 2.440x | 0.311x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 3,631.8 | 1,452.6-2,696.2 | 10.60 | **no** | `a100_sxm_80gb-x335-hybrid` | 330.5 | 546.6-1,014.5 | 2.56 | yes | 10.988x | 2.658x | 0.242x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,714.4 | 1,028.0-1,908.2 | 11.20 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 720.8-1,337.9 | 2.09 | yes | 7.626x | 1.426x | 0.187x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 2,420.8 | 590.7-1,096.4 | 17.38 | **no** | `a100_sxm_80gb-x272-hybrid` | 189.4 | 206.0-382.3 | 3.90 | yes | 12.779x | 2.868x | 0.224x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,770.4 | 521.8-968.6 | 14.38 | **no** | `a100_sxm_80gb-x672-hybrid` | 275.1 | 373.3-692.9 | 3.13 | yes | 6.435x | 1.398x | 0.217x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 1,033.4 | 247.9-460.1 | 17.68 | **no** | `a100_sxm_80gb-x335-hybrid` | 90.7 | 127.2-236.1 | 3.02 | yes | 11.389x | 1.948x | 0.171x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 600.9 | 135.5-251.6 | 18.80 | **no** | `a100_sxm_80gb-x672-hybrid` | 141.3 | 166.2-308.5 | 3.60 | yes | 4.254x | 0.816x | 0.192x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 329.8 | 75.3-139.7 | 18.58 | **no** | `a100_sxm_80gb-x335-hybrid` | 34.8 | 17.5-32.5 | 8.45 | **no** | 9.464x | 4.305x | 0.455x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 157.5 | 91.3-169.4 | 7.32 | yes | `a100_sxm_80gb-x672-hybrid` | 55.6 | 67.4-125.1 | 3.50 | yes | 2.835x | 1.354x | 0.478x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.171x to 0.478x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 12 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,247.4 | 3,601.3-6,684.5 | 5.00 | yes | `b200_sxm-x47-nvl72-tensor` | 700.7 | 2,285.0-4,241.2 | 1.30 | yes | 6.061x | 1.576x | 0.260x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 4,085.0 | 1,266.4-2,350.6 | 13.68 | **no** | `b200_sxm-x347-nvl72-hybrid` | 699.5 | 2,265.2-4,204.6 | 1.31 | yes | 5.840x | 0.559x | 0.096x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,247.4 | 3,601.3-6,684.5 | 5.00 | yes | `b200_sxm-x47-nvl72-tensor` | 690.7 | 2,053.7-3,812.0 | 1.43 | yes | 6.149x | 1.754x | 0.285x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,064.5 | 2,449.3-4,546.3 | 7.04 | yes | `b200_sxm-x58-nvl72-tensor` | 695.0 | 2,085.3-3,870.5 | 1.41 | yes | 5.848x | 1.175x | 0.201x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,247.4 | 3,601.3-6,684.5 | 5.00 | yes | `b200_sxm-x47-nvl72-tensor` | 671.9 | 1,719.0-3,190.7 | 1.66 | yes | 6.322x | 2.095x | 0.331x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,064.5 | 2,449.3-4,546.3 | 7.04 | yes | `b200_sxm-x58-nvl72-tensor` | 677.7 | 1,747.1-3,242.9 | 1.64 | yes | 5.998x | 1.402x | 0.234x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,247.4 | 3,601.3-6,684.5 | 5.00 | yes | `b200_sxm-x47-hybrid` | 639.0 | 1,523.4-2,827.7 | 1.78 | yes | 6.647x | 2.364x | 0.356x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,064.5 | 2,449.3-4,546.3 | 7.04 | yes | `b200_sxm-x58-nvl72-tensor` | 646.3 | 1,341.1-2,489.2 | 2.04 | yes | 6.289x | 1.826x | 0.290x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,235.9 | 2,292.0-4,254.3 | 7.84 | yes | `b200_sxm-x47-hybrid` | 594.8 | 1,213.9-2,253.1 | 2.08 | yes | 7.122x | 1.888x | 0.265x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,064.5 | 2,449.3-4,546.3 | 7.04 | yes | `b200_sxm-x58-hybrid` | 603.9 | 1,298.2-2,409.6 | 1.97 | yes | 6.730x | 1.887x | 0.280x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x113-romfill` | 4,174.8 | 2,133.7-3,960.5 | 8.30 | **no** | `b200_sxm-x58-hybrid` | 542.3 | 936.0-1,737.3 | 2.46 | yes | 7.698x | 2.280x | 0.296x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,045.5 | 1,399.6-2,597.8 | 12.26 | **no** | `b200_sxm-x231-nvl72-hybrid` | 641.6 | 1,550.7-2,878.4 | 1.75 | yes | 6.305x | 0.903x | 0.143x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,174.4 | 2,249.7-4,175.7 | 7.87 | yes | `b200_sxm-x173-nvl72-hybrid` | 584.0 | 1,219.2-2,263.1 | 2.03 | yes | 7.148x | 1.845x | 0.258x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,045.5 | 1,399.6-2,597.8 | 12.26 | **no** | `b200_sxm-x231-nvl72-hybrid` | 602.1 | 1,456.5-2,703.5 | 1.75 | yes | 6.719x | 0.961x | 0.143x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,813.2 | 1,034.2-1,919.6 | 15.63 | **no** | `b200_sxm-x173-nvl72-hybrid` | 416.2 | 705.8-1,310.1 | 2.50 | yes | 9.162x | 1.465x | 0.160x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,044.6 | 1,397.7-2,594.3 | 12.27 | **no** | `b200_sxm-x347-nvl72-hybrid` | 502.8 | 854.7-1,586.4 | 2.49 | yes | 8.045x | 1.635x | 0.203x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,662.3 | 354.7-658.4 | 19.87 | **no** | `b200_sxm-x173-nvl72-hybrid` | 235.8 | 204.9-380.3 | 4.88 | yes | 7.049x | 1.731x | 0.246x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,967.9 | 595.9-1,106.1 | 21.12 | **no** | `b200_sxm-x347-nvl72-hybrid` | 304.7 | 435.5-808.3 | 2.97 | yes | 9.741x | 1.368x | 0.140x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 483.7 | 114.9-213.2 | 17.85 | **no** | `b200_sxm-x173-nvl72-hybrid` | 133.8 | 56.8-105.5 | 9.98 | **no** | 3.615x | 2.021x | 0.559x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,021.1 | 228.9-424.8 | 18.92 | **no** | `b200_sxm-x347-nvl72-hybrid` | 161.9 | 85.5-158.8 | 8.02 | **no** | 6.308x | 2.676x | 0.424x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.096x to 0.559x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 10 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,217.9 | 2,966.9-5,507.0 | 6.03 | yes | `a100_sxm_80gb-x126-hybrid` | 368.7 | 726.9-1,349.2 | 2.15 | yes | 11.439x | 4.082x | 0.357x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 3,975.2 | 1,697.5-3,150.8 | 9.93 | **no** | `a100_sxm_80gb-x672-hybrid` | 358.3 | 723.4-1,342.6 | 2.10 | yes | 11.095x | 2.347x | 0.212x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,217.9 | 2,966.9-5,507.0 | 6.03 | yes | `a100_sxm_80gb-x126-hybrid` | 368.7 | 726.9-1,349.2 | 2.15 | yes | 11.439x | 4.082x | 0.357x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,932.1 | 1,887.9-3,504.2 | 8.83 | **no** | `a100_sxm_80gb-x112-hybrid` | 371.7 | 733.3-1,361.1 | 2.15 | yes | 10.578x | 2.574x | 0.243x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,217.9 | 2,966.9-5,507.0 | 6.03 | yes | `a100_sxm_80gb-x126-hybrid` | 368.7 | 726.9-1,349.2 | 2.15 | yes | 11.439x | 4.082x | 0.357x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,932.1 | 1,887.9-3,504.2 | 8.83 | **no** | `a100_sxm_80gb-x112-hybrid` | 371.7 | 733.3-1,361.1 | 2.15 | yes | 10.578x | 2.574x | 0.243x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,217.9 | 2,966.9-5,507.0 | 6.03 | yes | `a100_sxm_80gb-x126-hybrid` | 368.7 | 726.9-1,349.2 | 2.15 | yes | 11.439x | 4.082x | 0.357x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,932.1 | 1,887.9-3,504.2 | 8.83 | **no** | `a100_sxm_80gb-x112-hybrid` | 371.7 | 733.3-1,361.1 | 2.15 | yes | 10.578x | 2.574x | 0.243x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,217.9 | 2,966.9-5,507.0 | 6.03 | yes | `a100_sxm_80gb-x126-hybrid` | 368.7 | 726.9-1,349.2 | 2.15 | yes | 11.439x | 4.082x | 0.357x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,932.1 | 1,887.9-3,504.2 | 8.83 | **no** | `a100_sxm_80gb-x112-hybrid` | 365.1 | 693.5-1,287.2 | 2.23 | yes | 10.770x | 2.722x | 0.253x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,164.9 | 1,739.2-3,228.3 | 10.15 | **no** | `a100_sxm_80gb-x126-hybrid` | 326.8 | 534.7-992.5 | 2.59 | yes | 12.743x | 3.253x | 0.255x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 3,927.2 | 1,910.1-3,545.4 | 8.72 | **no** | `a100_sxm_80gb-x224-hybrid` | 357.5 | 672.5-1,248.3 | 2.25 | yes | 10.984x | 2.840x | 0.259x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,135.8 | 1,728.7-3,208.7 | 10.14 | **no** | `a100_sxm_80gb-x272-hybrid` | 322.6 | 505.2-937.8 | 2.71 | yes | 12.821x | 3.422x | 0.267x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,927.2 | 1,910.1-3,545.4 | 8.72 | **no** | `a100_sxm_80gb-x448-hybrid` | 351.3 | 659.5-1,224.1 | 2.26 | yes | 11.180x | 2.896x | 0.259x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,339.2 | 769.1-1,427.6 | 18.41 | **no** | `a100_sxm_80gb-x335-hybrid` | 211.7 | 229.0-425.0 | 3.92 | yes | 15.773x | 3.359x | 0.213x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,751.4 | 1,025.2-1,902.8 | 15.52 | **no** | `a100_sxm_80gb-x672-hybrid` | 279.4 | 375.5-696.9 | 3.16 | yes | 13.426x | 2.730x | 0.203x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,287.6 | 260.3-483.1 | 20.97 | **no** | `a100_sxm_80gb-x335-hybrid` | 94.6 | 129.1-239.6 | 3.11 | yes | 13.615x | 2.016x | 0.148x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,390.2 | 430.0-798.2 | 23.57 | **no** | `a100_sxm_80gb-x672-hybrid` | 145.8 | 167.5-310.9 | 3.69 | yes | 16.389x | 2.567x | 0.157x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 455.4 | 116.7-216.6 | 16.55 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.2 | 19.6-36.4 | 8.03 | **no** | 12.256x | 5.946x | 0.485x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 758.1 | 165.1-306.4 | 19.47 | **no** | `a100_sxm_80gb-x672-hybrid` | 58.5 | 84.7-157.2 | 2.93 | yes | 12.969x | 1.950x | 0.150x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.148x to 0.485x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 5 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 3,529.6-6,551.4 | 5.07 | yes | `b200_sxm-x49-nvl72-tensor` | 701.4 | 2,291.9-4,254.0 | 1.30 | yes | 6.021x | 1.540x | 0.256x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 2,156.0-4,001.7 | 7.59 | yes | `b200_sxm-x58-nvl72-tensor` | 704.0 | 2,317.0-4,300.6 | 1.29 | yes | 5.479x | 0.931x | 0.170x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 3,529.6-6,551.4 | 5.07 | yes | `b200_sxm-x49-nvl72-tensor` | 691.5 | 2,060.5-3,824.6 | 1.42 | yes | 6.107x | 1.713x | 0.280x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 2,156.0-4,001.7 | 7.59 | yes | `b200_sxm-x58-nvl72-tensor` | 694.8 | 2,084.9-3,869.9 | 1.41 | yes | 5.551x | 1.034x | 0.186x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 3,529.6-6,551.4 | 5.07 | yes | `b200_sxm-x49-nvl72-tensor` | 672.8 | 1,725.0-3,201.8 | 1.65 | yes | 6.277x | 2.046x | 0.326x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 2,156.0-4,001.7 | 7.59 | yes | `b200_sxm-x58-nvl72-tensor` | 677.4 | 1,746.6-3,241.9 | 1.64 | yes | 5.694x | 1.234x | 0.217x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 3,529.6-6,551.4 | 5.07 | yes | `b200_sxm-x49-nvl72-tensor` | 639.3 | 1,329.5-2,467.7 | 2.04 | yes | 6.606x | 2.655x | 0.402x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 2,156.0-4,001.7 | 7.59 | yes | `b200_sxm-x58-nvl72-tensor` | 645.9 | 1,340.5-2,488.2 | 2.04 | yes | 5.972x | 1.608x | 0.269x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 4,185.8 | 3,413.6-6,336.1 | 5.20 | yes | `b200_sxm-x83-nvl72-hybrid` | 630.8 | 1,570.4-2,914.8 | 1.70 | yes | 6.636x | 2.174x | 0.328x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 2,156.0-4,001.7 | 7.59 | yes | `b200_sxm-x58-hybrid` | 603.2 | 1,297.1-2,407.5 | 1.97 | yes | 6.395x | 1.662x | 0.260x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,120.6 | 3,355.9-6,229.0 | 5.21 | yes | `b200_sxm-x173-nvl72-hybrid` | 628.8 | 1,639.5-3,043.2 | 1.63 | yes | 6.553x | 2.047x | 0.312x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 3,820.4 | 2,310.8-4,289.1 | 7.01 | yes | `b200_sxm-x116-nvl72-hybrid` | 608.9 | 1,456.9-2,704.3 | 1.77 | yes | 6.275x | 1.586x | 0.253x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,097.3 | 2,135.9-3,964.4 | 8.13 | **no** | `b200_sxm-x173-nvl72-hybrid` | 583.0 | 1,217.9-2,260.5 | 2.03 | yes | 7.028x | 1.754x | 0.250x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,820.4 | 2,310.8-4,289.1 | 7.01 | yes | `b200_sxm-x231-nvl72-hybrid` | 601.3 | 1,455.2-2,701.1 | 1.75 | yes | 6.354x | 1.588x | 0.250x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,564.5 | 959.5-1,781.0 | 15.75 | **no** | `b200_sxm-x173-nvl72-hybrid` | 414.3 | 704.0-1,306.7 | 2.50 | yes | 8.604x | 1.363x | 0.158x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,659.2 | 1,298.1-2,409.5 | 11.95 | **no** | `b200_sxm-x347-nvl72-hybrid` | 501.3 | 853.4-1,583.9 | 2.49 | yes | 7.299x | 1.521x | 0.208x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,477.7 | 320.4-594.7 | 19.56 | **no** | `b200_sxm-x173-nvl72-hybrid` | 233.3 | 204.4-379.4 | 4.84 | yes | 6.333x | 1.567x | 0.247x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,614.0 | 548.1-1,017.3 | 20.22 | **no** | `b200_sxm-x347-nvl72-hybrid` | 302.6 | 434.4-806.3 | 2.95 | yes | 8.638x | 1.262x | 0.146x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 434.5 | 134.6-249.8 | 13.69 | **no** | `b200_sxm-x173-nvl72-hybrid` | 130.7 | 56.5-104.9 | 9.80 | **no** | 3.325x | 2.381x | 0.716x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 871.3 | 203.6-377.8 | 18.15 | **no** | `b200_sxm-x347-nvl72-hybrid` | 159.6 | 85.2-158.2 | 7.94 | **no** | 5.461x | 2.388x | 0.437x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.146x to 0.716x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 13 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 3,785.1-7,025.7 | 4.68 | yes | `a100_sxm_80gb-x136-hybrid` | 369.6 | 732.8-1,360.2 | 2.14 | yes | 11.302x | 5.165x | 0.457x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 2,626.2-4,874.6 | 5.94 | yes | `a100_sxm_80gb-x168-hybrid` | 367.5 | 728.8-1,352.7 | 2.14 | yes | 10.004x | 3.604x | 0.360x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 3,785.1-7,025.7 | 4.68 | yes | `a100_sxm_80gb-x136-hybrid` | 369.6 | 732.8-1,360.2 | 2.14 | yes | 11.302x | 5.165x | 0.457x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 2,626.2-4,874.6 | 5.94 | yes | `a100_sxm_80gb-x168-hybrid` | 367.5 | 728.8-1,352.7 | 2.14 | yes | 10.004x | 3.604x | 0.360x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 3,785.1-7,025.7 | 4.68 | yes | `a100_sxm_80gb-x136-hybrid` | 369.6 | 732.8-1,360.2 | 2.14 | yes | 11.302x | 5.165x | 0.457x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 2,626.2-4,874.6 | 5.94 | yes | `a100_sxm_80gb-x168-hybrid` | 367.5 | 728.8-1,352.7 | 2.14 | yes | 10.004x | 3.604x | 0.360x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 3,785.1-7,025.7 | 4.68 | yes | `a100_sxm_80gb-x136-hybrid` | 369.6 | 732.8-1,360.2 | 2.14 | yes | 11.302x | 5.165x | 0.457x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 2,626.2-4,874.6 | 5.94 | yes | `a100_sxm_80gb-x168-hybrid` | 367.5 | 728.8-1,352.7 | 2.14 | yes | 10.004x | 3.604x | 0.360x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 4,159.2 | 2,785.7-5,170.6 | 6.33 | yes | `a100_sxm_80gb-x132-hybrid` | 366.0 | 719.7-1,335.8 | 2.16 | yes | 11.365x | 3.871x | 0.341x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 2,626.2-4,874.6 | 5.94 | yes | `a100_sxm_80gb-x168-hybrid` | 367.5 | 728.8-1,352.7 | 2.14 | yes | 10.004x | 3.604x | 0.360x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,087.6 | 2,733.8-5,074.2 | 6.34 | yes | `a100_sxm_80gb-x272-hybrid` | 360.8 | 701.4-1,301.8 | 2.18 | yes | 11.329x | 3.898x | 0.344x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,614.5 | 2,917.7-5,415.6 | 5.25 | yes | `a100_sxm_80gb-x448-hybrid` | 357.8 | 705.3-1,309.1 | 2.15 | yes | 10.102x | 4.137x | 0.410x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 3,996.0 | 1,638.5-3,041.2 | 10.34 | **no** | `a100_sxm_80gb-x272-hybrid` | 321.9 | 504.7-936.9 | 2.70 | yes | 12.415x | 3.246x | 0.261x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,613.1 | 2,907.0-5,395.8 | 5.27 | yes | `a100_sxm_80gb-x672-hybrid` | 357.8 | 722.8-1,341.7 | 2.10 | yes | 10.098x | 4.022x | 0.398x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,081.4 | 715.8-1,328.7 | 18.25 | **no** | `a100_sxm_80gb-x335-hybrid` | 210.7 | 228.7-424.4 | 3.91 | yes | 14.625x | 3.130x | 0.214x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,261.1 | 1,447.3-2,686.4 | 9.55 | **no** | `a100_sxm_80gb-x672-hybrid` | 278.5 | 375.0-696.1 | 3.15 | yes | 11.709x | 3.859x | 0.330x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 1,178.4 | 332.4-616.9 | 15.03 | **no** | `a100_sxm_80gb-x335-hybrid` | 93.8 | 128.7-238.9 | 3.09 | yes | 12.568x | 2.583x | 0.205x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,969.2 | 398.9-740.4 | 20.93 | **no** | `a100_sxm_80gb-x672-hybrid` | 144.9 | 167.2-310.4 | 3.67 | yes | 13.592x | 2.385x | 0.175x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 428.5 | 103.3-191.8 | 17.58 | **no** | `a100_sxm_80gb-x335-hybrid` | 36.7 | 19.1-35.5 | 8.12 | **no** | 11.688x | 5.396x | 0.462x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 602.2 | 148.0-274.7 | 17.25 | **no** | `a100_sxm_80gb-x672-hybrid` | 57.8 | 80.6-149.6 | 3.04 | yes | 10.411x | 1.836x | 0.176x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.175x to 0.462x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 13 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-kimi-k3`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | 1,435.6 | 744.0-1,381.0 | 8.18 | **no** | `b200_sxm-x201-nvl72-hybrid` | 288.3 | 905.8-1,681.2 | 1.35 | yes | 4.979x | 0.821x | 0.165x |
| Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 1,096.0 | 571.6-1,060.9 | 8.13 | **no** | `b200_sxm-x202-nvl72-hybrid` | 288.4 | 906.8-1,683.1 | 1.35 | yes | 3.800x | 0.630x | 0.166x |
| Kimi-K3 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,328.5 | 858.6-1,593.7 | 6.56 | yes | `b200_sxm-x202-nvl72-hybrid` | 288.4 | 906.8-1,683.1 | 1.35 | yes | 4.606x | 0.947x | 0.206x |
| Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,043.1 | 706.6-1,311.6 | 6.26 | yes | `b200_sxm-x462-nvl72-hybrid` | 286.0 | 865.1-1,605.8 | 1.40 | yes | 3.647x | 0.817x | 0.224x |
| Kimi-K3 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,328.5 | 858.6-1,593.7 | 6.56 | yes | `b200_sxm-x202-nvl72-hybrid` | 286.0 | 867.8-1,610.7 | 1.40 | yes | 4.645x | 0.989x | 0.213x |
| Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,043.1 | 706.6-1,311.6 | 6.26 | yes | `b200_sxm-x462-nvl72-hybrid` | 286.0 | 865.1-1,605.8 | 1.40 | yes | 3.647x | 0.817x | 0.224x |
| Kimi-K3 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,307.3 | 614.8-1,141.1 | 9.02 | **no** | `b200_sxm-x202-nvl72-hybrid` | 276.9 | 738.1-1,370.1 | 1.59 | yes | 4.721x | 0.833x | 0.176x |
| Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,043.1 | 706.6-1,311.6 | 6.26 | yes | `b200_sxm-x462-nvl72-hybrid` | 284.8 | 842.4-1,563.6 | 1.43 | yes | 3.662x | 0.839x | 0.229x |
| Kimi-K3 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,159.6 | 511.0-948.4 | 9.62 | **no** | `b200_sxm-x202-nvl72-hybrid` | 260.6 | 581.9-1,080.1 | 1.90 | yes | 4.450x | 0.878x | 0.197x |
| Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,043.1 | 706.6-1,311.6 | 6.26 | yes | `b200_sxm-x462-nvl72-hybrid` | 275.6 | 708.9-1,315.8 | 1.65 | yes | 3.785x | 0.997x | 0.263x |
| Kimi-K3 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 914.1 | 300.1-557.0 | 12.92 | **no** | `b200_sxm-x202-nvl72-hybrid` | 234.2 | 406.3-754.1 | 2.44 | yes | 3.902x | 0.739x | 0.189x |
| Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,043.1 | 706.6-1,311.6 | 6.26 | yes | `b200_sxm-x462-nvl72-hybrid` | 259.0 | 535.4-993.9 | 2.05 | yes | 4.027x | 1.320x | 0.328x |
| Kimi-K3 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 581.8 | 160.5-297.9 | 15.37 | **no** | `b200_sxm-x202-nvl72-hybrid` | 197.6 | 241.5-448.2 | 3.47 | yes | 2.945x | 0.665x | 0.226x |
| Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 976.3 | 658.6-1,222.4 | 6.29 | yes | `b200_sxm-x462-nvl72-hybrid` | 232.1 | 355.7-660.3 | 2.77 | yes | 4.207x | 1.851x | 0.440x |
| Kimi-K3 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 176.4 | 42.4-78.7 | 17.65 | **no** | `b200_sxm-x202-nvl72-hybrid` | 117.0 | 70.2-130.3 | 7.07 | yes | 1.507x | 0.604x | 0.401x |
| Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 487.7 | 190.4-353.4 | 10.86 | **no** | `b200_sxm-x462-nvl72-hybrid` | 152.2 | 162.9-302.5 | 3.96 | yes | 3.205x | 1.168x | 0.365x |
| Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 45.9 | 11.1-20.6 | 17.53 | **no** | `b200_sxm-x202-nvl72-hybrid` | 58.0 | 18.2-33.8 | 13.50 | **no** | 0.791x | 0.609x | 0.770x |
| Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 144.3 | 48.4-89.8 | 12.65 | **no** | `b200_sxm-x462-nvl72-hybrid` | 78.2 | 45.0-83.5 | 7.37 | yes | 1.844x | 1.075x | 0.583x |
| Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 11.5 | 2.8-5.3 | 17.14 | **no** | `b200_sxm-x202-nvl72-hybrid` | 25.1 | 8.2-15.2 | 13.00 | **no** | 0.458x | 0.347x | 0.758x |
| Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 36.9 | 17.3-32.0 | 9.06 | **no** | `b200_sxm-x462-nvl72-hybrid` | 36.7 | 11.5-21.4 | 13.51 | **no** | 1.006x | 1.500x | 1.490x |

**Does the ratio compress?** Of 20 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.165x to 1.490x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 20 ROM rows and 17 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-kimi-k3`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x398` | 1,096.9 | 555.6-1,031.2 | 8.37 | **no** | `a100_sxm_80gb-x393-hybrid` | 108.2 | 185.3-343.9 | 2.48 | yes | 10.133x | 2.999x | 0.296x |
| Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x10` | 1,003.7 | 768.3-1,426.1 | 5.54 | yes | `a100_sxm_80gb-x560-hybrid` | 109.7 | 187.7-348.3 | 2.48 | yes | 9.148x | 4.094x | 0.448x |
| Kimi-K3 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 888.6 | 375.2-696.4 | 10.04 | **no** | `a100_sxm_80gb-x394-hybrid` | 108.3 | 185.4-344.0 | 2.48 | yes | 8.206x | 2.024x | 0.247x |
| Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 814.1 | 849.1-1,576.1 | 4.07 | yes | `a100_sxm_80gb-x1231-hybrid` | 108.3 | 178.1-330.7 | 2.58 | yes | 7.517x | 4.766x | 0.634x |
| Kimi-K3 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 888.6 | 375.2-696.4 | 10.04 | **no** | `a100_sxm_80gb-x394-hybrid` | 108.3 | 185.4-344.0 | 2.48 | yes | 8.206x | 2.024x | 0.247x |
| Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 814.1 | 849.1-1,576.1 | 4.07 | yes | `a100_sxm_80gb-x1231-hybrid` | 108.3 | 178.1-330.7 | 2.58 | yes | 7.517x | 4.766x | 0.634x |
| Kimi-K3 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 812.6 | 330.4-613.2 | 10.43 | **no** | `a100_sxm_80gb-x394-hybrid` | 106.8 | 172.3-319.8 | 2.63 | yes | 7.610x | 1.918x | 0.252x |
| Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 814.1 | 849.1-1,576.1 | 4.07 | yes | `a100_sxm_80gb-x1231-hybrid` | 108.3 | 178.1-330.7 | 2.58 | yes | 7.517x | 4.766x | 0.634x |
| Kimi-K3 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 601.6 | 191.4-355.3 | 13.33 | **no** | `a100_sxm_80gb-x394-hybrid` | 96.0 | 110.9-205.9 | 3.67 | yes | 6.266x | 1.726x | 0.275x |
| Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 814.1 | 849.1-1,576.1 | 4.07 | yes | `a100_sxm_80gb-x1231-hybrid` | 108.3 | 178.1-330.7 | 2.58 | yes | 7.517x | 4.766x | 0.634x |
| Kimi-K3 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 372.5 | 102.6-190.5 | 15.39 | **no** | `a100_sxm_80gb-x394-hybrid` | 82.3 | 95.4-177.0 | 3.66 | yes | 4.525x | 1.076x | 0.238x |
| Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 814.1 | 849.1-1,576.1 | 4.07 | yes | `a100_sxm_80gb-x1231-hybrid` | 101.8 | 132.4-245.7 | 3.26 | yes | 8.001x | 6.415x | 0.802x |
| Kimi-K3 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 205.8 | 53.1-98.5 | 16.44 | **no** | `a100_sxm_80gb-x394-hybrid` | 67.0 | 52.3-97.1 | 5.43 | yes | 3.074x | 1.015x | 0.330x |
| Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 666.5 | 514.0-954.0 | 5.50 | yes | `a100_sxm_80gb-x1231-hybrid` | 87.7 | 76.6-142.1 | 4.86 | yes | 7.601x | 6.712x | 0.883x |
| Kimi-K3 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 55.3 | 13.6-25.3 | 17.21 | **no** | `a100_sxm_80gb-x394-hybrid` | 39.4 | 33.3-61.9 | 5.01 | yes | 1.405x | 0.409x | 0.291x |
| Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 288.1 | 201.4-373.8 | 6.07 | yes | `a100_sxm_80gb-x1231-hybrid` | 58.1 | 74.0-137.4 | 3.33 | yes | 4.957x | 2.721x | 0.549x |
| Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 14.0 | 3.4-6.4 | 17.20 | **no** | `a100_sxm_80gb-x394-hybrid` | 16.8 | 8.6-15.9 | 8.32 | **no** | 0.832x | 0.402x | 0.483x |
| Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 81.6 | 52.2-96.9 | 6.62 | yes | `a100_sxm_80gb-x1231-hybrid` | 32.3 | 21.2-39.3 | 6.46 | yes | 2.528x | 2.466x | 0.976x |
| Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 3.5 | 0.9-1.6 | 17.14 | **no** | `a100_sxm_80gb-x394-hybrid` | 6.6 | 2.2-4.0 | 13.03 | **no** | 0.528x | 0.401x | 0.760x |
| Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x22` | 20.8 | 15.4-28.5 | 5.74 | yes | `a100_sxm_80gb-x1231-hybrid` | 12.8 | 7.9-14.6 | 6.88 | yes | 1.624x | 1.949x | 1.200x |

**Does the ratio compress?** Of 20 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.238x to 1.200x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 10 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-kimi-k3-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x383` | 949.7 | 425.9-790.5 | 9.46 | **no** | `b200_sxm-x195-nvl72-hybrid` | 285.4 | 861.4-1,598.8 | 1.40 | yes | 3.328x | 0.494x | 0.149x |
| Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | 894.0 | 522.7-970.2 | 7.25 | yes | `b200_sxm-x520-nvl72-hybrid` | 283.0 | 805.0-1,494.2 | 1.49 | yes | 3.159x | 0.649x | 0.206x |
| Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 717.5 | 632.7-1,174.4 | 4.81 | yes | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | 646.7-1,200.4 | 1.81 | yes | 2.599x | 0.978x | 0.376x |
| Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 717.5 | 632.7-1,174.4 | 4.81 | yes | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | 646.7-1,200.4 | 1.81 | yes | 2.599x | 0.978x | 0.376x |
| Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 717.5 | 632.7-1,174.4 | 4.81 | yes | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | 646.7-1,200.4 | 1.81 | yes | 2.599x | 0.978x | 0.376x |
| Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 717.5 | 632.7-1,174.4 | 4.81 | yes | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | 646.7-1,200.4 | 1.81 | yes | 2.599x | 0.978x | 0.376x |
| Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 717.5 | 632.7-1,174.4 | 4.81 | yes | `b200_sxm-x1965-nvl72-hybrid` | 273.9 | 604.8-1,122.6 | 1.92 | yes | 2.620x | 1.046x | 0.399x |
| Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 717.5 | 632.7-1,174.4 | 4.81 | yes | `b200_sxm-x1965-nvl72-hybrid` | 257.6 | 398.3-739.3 | 2.74 | yes | 2.786x | 1.589x | 0.570x |
| Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 460.3 | 211.3-392.2 | 9.24 | **no** | `b200_sxm-x1965-nvl72-hybrid` | 196.9 | 181.3-336.5 | 4.60 | yes | 2.338x | 1.165x | 0.498x |
| Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 149.9 | 54.6-101.4 | 11.64 | **no** | `b200_sxm-x1965-nvl72-hybrid` | 120.5 | 69.5-129.0 | 7.35 | yes | 1.244x | 0.786x | 0.632x |
| Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x68` | 39.3 | 13.7-25.4 | 12.19 | **no** | `b200_sxm-x1965-nvl72-hybrid` | 49.4 | 22.8-42.4 | 9.17 | **no** | 0.795x | 0.599x | 0.753x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.149x to 0.753x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 11 ROM rows and 10 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-kimi-k3-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 724.4 | 580.8-1,078.0 | 5.29 | yes | `a100_sxm_80gb-x394-hybrid` | 106.9 | 147.3-273.5 | 3.08 | yes | 6.775x | 3.942x | 0.582x |
| Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x23` | 788.1 | 591.9-1,098.7 | 5.64 | yes | `a100_sxm_80gb-x1287-hybrid` | 106.9 | 142.1-263.7 | 3.19 | yes | 7.375x | 4.167x | 0.565x |
| Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 553.2 | 1,000.1-1,856.3 | 2.35 | yes | `a100_sxm_80gb-x5316-hybrid` | 100.9 | 111.3-206.6 | 3.84 | yes | 5.482x | 8.987x | 1.639x |
| Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 553.2 | 1,000.1-1,856.3 | 2.35 | yes | `a100_sxm_80gb-x5316-hybrid` | 100.9 | 111.3-206.6 | 3.84 | yes | 5.482x | 8.987x | 1.639x |
| Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 553.2 | 1,000.1-1,856.3 | 2.35 | yes | `a100_sxm_80gb-x5316-hybrid` | 100.9 | 111.3-206.6 | 3.84 | yes | 5.482x | 8.987x | 1.639x |
| Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 553.2 | 1,000.1-1,856.3 | 2.35 | yes | `a100_sxm_80gb-x5316-hybrid` | 100.9 | 111.3-206.6 | 3.84 | yes | 5.482x | 8.987x | 1.639x |
| Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 518.3 | 874.0-1,622.2 | 2.51 | yes | `a100_sxm_80gb-x5316-hybrid` | 100.9 | 111.3-206.6 | 3.84 | yes | 5.136x | 7.853x | 1.529x |
| Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 498.2 | 461.8-857.2 | 4.57 | yes | `a100_sxm_80gb-x5316-hybrid` | 100.9 | 111.3-206.6 | 3.84 | yes | 4.937x | 4.150x | 0.841x |
| Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 280.7 | 225.1-417.8 | 5.29 | yes | `a100_sxm_80gb-x5316-hybrid` | 81.1 | 62.6-116.1 | 5.49 | yes | 3.463x | 3.597x | 1.039x |
| Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 86.3 | 60.4-112.1 | 6.06 | yes | `a100_sxm_80gb-x5316-hybrid` | 55.1 | 31.6-58.6 | 7.40 | yes | 1.567x | 1.913x | 1.221x |
| Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 22.4 | 15.2-28.2 | 6.25 | yes | `a100_sxm_80gb-x5316-hybrid` | 28.7 | 8.1-15.1 | 14.95 | **no** | 0.779x | 1.864x | 2.393x |

**Does the ratio compress?** Of 11 class rows in this study, 3 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.565x to 2.393x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 10 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-kimi-k3-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,940.4 | 968.1-1,796.9 | 8.50 | **no** | `b200_sxm-x201-nvl72-hybrid` | 288.8 | 907.0-1,683.6 | 1.35 | yes | 6.718x | 1.067x | 0.159x |
| Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 1,462.3 | 835.2-1,550.3 | 7.42 | yes | `b200_sxm-x231-nvl72-hybrid` | 284.3 | 868.0-1,611.1 | 1.39 | yes | 5.143x | 0.962x | 0.187x |
| Kimi-K3 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,940.4 | 968.1-1,796.9 | 8.50 | **no** | `b200_sxm-x201-nvl72-hybrid` | 288.8 | 907.0-1,683.6 | 1.35 | yes | 6.718x | 1.067x | 0.159x |
| Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 1,462.3 | 835.2-1,550.3 | 7.42 | yes | `b200_sxm-x231-nvl72-hybrid` | 284.3 | 868.0-1,611.1 | 1.39 | yes | 5.143x | 0.962x | 0.187x |
| Kimi-K3 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,940.4 | 968.1-1,796.9 | 8.50 | **no** | `b200_sxm-x201-nvl72-hybrid` | 286.6 | 868.3-1,611.7 | 1.40 | yes | 6.771x | 1.115x | 0.165x |
| Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 1,462.3 | 835.2-1,550.3 | 7.42 | yes | `b200_sxm-x231-nvl72-hybrid` | 284.3 | 868.0-1,611.1 | 1.39 | yes | 5.143x | 0.962x | 0.187x |
| Kimi-K3 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,940.4 | 968.1-1,796.9 | 8.50 | **no** | `b200_sxm-x201-nvl72-hybrid` | 278.0 | 739.4-1,372.4 | 1.59 | yes | 6.980x | 1.309x | 0.188x |
| Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 1,462.3 | 835.2-1,550.3 | 7.42 | yes | `b200_sxm-x231-nvl72-hybrid` | 276.9 | 757.8-1,406.6 | 1.55 | yes | 5.281x | 1.102x | 0.209x |
| Kimi-K3 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,940.4 | 968.1-1,796.9 | 8.50 | **no** | `b200_sxm-x201-nvl72-hybrid` | 262.6 | 583.9-1,083.8 | 1.91 | yes | 7.388x | 1.658x | 0.224x |
| Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 1,462.3 | 835.2-1,550.3 | 7.42 | yes | `b200_sxm-x231-nvl72-hybrid` | 263.4 | 604.2-1,121.4 | 1.85 | yes | 5.552x | 1.382x | 0.249x |
| Kimi-K3 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,741.2 | 608.5-1,129.4 | 12.13 | **no** | `b200_sxm-x201-nvl72-hybrid` | 237.6 | 425.4-789.5 | 2.37 | yes | 7.328x | 1.430x | 0.195x |
| Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 1,462.3 | 835.2-1,550.3 | 7.42 | yes | `b200_sxm-x231-nvl72-hybrid` | 240.7 | 447.8-831.2 | 2.28 | yes | 6.075x | 1.865x | 0.307x |
| Kimi-K3 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,506.6 | 510.8-948.2 | 12.51 | **no** | `b200_sxm-x201-nvl72-hybrid` | 202.5 | 284.0-527.0 | 3.02 | yes | 7.441x | 1.799x | 0.242x |
| Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,444.2 | 824.4-1,530.2 | 7.43 | yes | `b200_sxm-x347-nvl72-hybrid` | 225.8 | 340.2-631.4 | 2.81 | yes | 6.396x | 2.423x | 0.379x |
| Kimi-K3 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 720.8 | 155.9-289.4 | 19.60 | **no** | `b200_sxm-x201-nvl72-hybrid` | 124.3 | 98.5-182.7 | 5.36 | yes | 5.797x | 1.584x | 0.273x |
| Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 996.8 | 348.5-646.8 | 12.13 | **no** | `b200_sxm-x347-nvl72-hybrid` | 144.8 | 121.7-225.9 | 5.05 | yes | 6.882x | 2.864x | 0.416x |
| Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 219.7 | 47.8-88.6 | 19.50 | **no** | `b200_sxm-x201-nvl72-hybrid` | 65.9 | 26.7-49.5 | 10.48 | **no** | 3.333x | 1.791x | 0.537x |
| Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 369.0 | 95.8-177.8 | 16.33 | **no** | `b200_sxm-x347-nvl72-hybrid` | 77.5 | 59.0-109.5 | 5.57 | yes | 4.758x | 1.624x | 0.341x |
| Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 57.8 | 13.9-25.7 | 17.67 | **no** | `b200_sxm-x201-nvl72-hybrid` | 33.4 | 19.0-35.3 | 7.45 | yes | 1.729x | 0.730x | 0.422x |
| Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 99.2 | 39.7-73.8 | 10.59 | **no** | `b200_sxm-x347-nvl72-hybrid` | 39.6 | 15.6-28.9 | 10.78 | **no** | 2.507x | 2.553x | 1.018x |

**Does the ratio compress?** Of 20 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.159x to 1.018x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-kimi-k3-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,390.0 | 688.2-1,277.4 | 8.56 | **no** | `a100_sxm_80gb-x394-hybrid` | 108.6 | 185.6-344.5 | 2.48 | yes | 12.797x | 3.708x | 0.290x |
| Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 1,198.4 | 729.8-1,354.5 | 6.96 | yes | `a100_sxm_80gb-x392-hybrid` | 108.5 | 185.4-344.1 | 2.48 | yes | 11.041x | 3.936x | 0.357x |
| Kimi-K3 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,390.0 | 688.2-1,277.4 | 8.56 | **no** | `a100_sxm_80gb-x394-hybrid` | 108.6 | 185.6-344.5 | 2.48 | yes | 12.797x | 3.708x | 0.290x |
| Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 1,198.4 | 729.8-1,354.5 | 6.96 | yes | `a100_sxm_80gb-x392-hybrid` | 108.5 | 185.4-344.1 | 2.48 | yes | 11.041x | 3.936x | 0.357x |
| Kimi-K3 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,390.0 | 688.2-1,277.4 | 8.56 | **no** | `a100_sxm_80gb-x394-hybrid` | 108.6 | 185.6-344.5 | 2.48 | yes | 12.797x | 3.708x | 0.290x |
| Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 1,198.4 | 729.8-1,354.5 | 6.96 | yes | `a100_sxm_80gb-x392-hybrid` | 108.5 | 185.4-344.1 | 2.48 | yes | 11.041x | 3.936x | 0.357x |
| Kimi-K3 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,390.0 | 688.2-1,277.4 | 8.56 | **no** | `a100_sxm_80gb-x394-hybrid` | 107.1 | 172.5-320.2 | 2.63 | yes | 12.974x | 3.989x | 0.307x |
| Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 1,198.4 | 729.8-1,354.5 | 6.96 | yes | `a100_sxm_80gb-x392-hybrid` | 107.1 | 172.4-319.9 | 2.63 | yes | 11.194x | 4.234x | 0.378x |
| Kimi-K3 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,256.9 | 461.4-856.4 | 11.55 | **no** | `a100_sxm_80gb-x394-hybrid` | 96.6 | 111.5-207.0 | 3.67 | yes | 13.008x | 4.136x | 0.318x |
| Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 1,198.4 | 729.8-1,354.5 | 6.96 | yes | `a100_sxm_80gb-x392-hybrid` | 96.5 | 111.5-206.9 | 3.67 | yes | 12.413x | 6.548x | 0.527x |
| Kimi-K3 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,073.5 | 371.3-689.2 | 12.26 | **no** | `a100_sxm_80gb-x394-hybrid` | 83.2 | 97.4-180.7 | 3.62 | yes | 12.900x | 3.813x | 0.296x |
| Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,195.1 | 911.6-1,692.0 | 5.56 | yes | `a100_sxm_80gb-x672-hybrid` | 92.2 | 92.0-170.8 | 4.25 | yes | 12.958x | 9.906x | 0.765x |
| Kimi-K3 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 744.7 | 211.2-392.0 | 14.95 | **no** | `a100_sxm_80gb-x394-hybrid` | 68.1 | 57.9-107.5 | 4.99 | yes | 10.928x | 3.647x | 0.334x |
| Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,018.1 | 711.7-1,321.1 | 6.06 | yes | `a100_sxm_80gb-x672-hybrid` | 79.0 | 80.8-150.0 | 4.14 | yes | 12.887x | 8.806x | 0.683x |
| Kimi-K3 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 249.8 | 59.1-109.6 | 17.93 | **no** | `a100_sxm_80gb-x394-hybrid` | 41.1 | 44.8-83.1 | 3.89 | yes | 6.082x | 1.319x | 0.217x |
| Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 529.6 | 219.4-407.3 | 10.23 | **no** | `a100_sxm_80gb-x672-hybrid` | 49.3 | 54.4-100.9 | 3.85 | yes | 10.734x | 4.035x | 0.376x |
| Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 66.6 | 15.9-29.5 | 17.77 | **no** | `a100_sxm_80gb-x394-hybrid` | 18.1 | 17.5-32.4 | 4.39 | yes | 3.686x | 0.910x | 0.247x |
| Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 159.3 | 56.1-104.1 | 12.04 | **no** | `a100_sxm_80gb-x672-hybrid` | 23.7 | 19.6-36.4 | 5.13 | yes | 6.708x | 2.860x | 0.426x |
| Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 16.8 | 4.1-7.7 | 17.20 | **no** | `a100_sxm_80gb-x394-hybrid` | 7.4 | 4.8-8.8 | 6.63 | yes | 2.253x | 0.869x | 0.386x |
| Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 40.9 | 19.0-35.2 | 9.14 | **no** | `a100_sxm_80gb-x672-hybrid` | 9.2 | 11.7-21.7 | 3.33 | yes | 4.468x | 1.627x | 0.364x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.217x to 0.765x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | 5,431.5 | 3,358.5-6,233.9 | 6.86 | yes | `b200_sxm-x23-nvl72-tensor` | 713.1 | 2,226.1-4,132.0 | 1.36 | yes | 7.617x | 1.509x | 0.198x |
| MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3,419.6 | 4,211.1-7,816.4 | 3.44 | yes | `b200_sxm-x58-nvl72-tensor` | 750.5 | 2,602.5-4,830.6 | 1.22 | yes | 4.556x | 1.618x | 0.355x |
| MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,825.9 | 3,594.1-6,671.2 | 5.69 | yes | `b200_sxm-x192-nvl72-hybrid` | 749.3 | 2,639.6-4,899.4 | 1.20 | yes | 6.440x | 1.362x | 0.211x |
| MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 2,054.1 | 2,665.1-4,946.8 | 3.27 | yes | `b200_sxm-x636-nvl72-hybrid` | 744.2 | 2,633.6-4,888.4 | 1.20 | yes | 2.760x | 1.012x | 0.367x |
| MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,825.9 | 3,594.1-6,671.2 | 5.69 | yes | `b200_sxm-x192-nvl72-hybrid` | 744.3 | 2,573.6-4,777.0 | 1.23 | yes | 6.484x | 1.397x | 0.215x |
| MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 2,054.1 | 2,665.1-4,946.8 | 3.27 | yes | `b200_sxm-x636-nvl72-hybrid` | 744.2 | 2,633.6-4,888.4 | 1.20 | yes | 2.760x | 1.012x | 0.367x |
| MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,825.9 | 3,594.1-6,671.2 | 5.69 | yes | `b200_sxm-x192-nvl72-hybrid` | 725.2 | 2,366.9-4,393.3 | 1.30 | yes | 6.654x | 1.518x | 0.228x |
| MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 2,054.1 | 2,665.1-4,946.8 | 3.27 | yes | `b200_sxm-x636-nvl72-hybrid` | 744.2 | 2,633.6-4,888.4 | 1.20 | yes | 2.760x | 1.012x | 0.367x |
| MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x282` | 4,661.0 | 2,896.5-5,376.3 | 6.82 | yes | `b200_sxm-x144-nvl72-hybrid` | 671.4 | 1,873.8-3,478.0 | 1.52 | yes | 6.942x | 1.546x | 0.223x |
| MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 2,054.1 | 2,665.1-4,946.8 | 3.27 | yes | `b200_sxm-x636-nvl72-hybrid` | 733.3 | 2,473.3-4,590.8 | 1.26 | yes | 2.801x | 1.078x | 0.385x |
| MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,058.7 | 2,221.5-4,123.3 | 7.75 | yes | `b200_sxm-x192-nvl72-hybrid` | 633.4 | 1,655.9-3,073.6 | 1.62 | yes | 6.408x | 1.342x | 0.209x |
| MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 1,928.7 | 1,889.9-3,508.0 | 4.33 | yes | `b200_sxm-x636-nvl72-hybrid` | 710.0 | 2,202.0-4,087.3 | 1.37 | yes | 2.716x | 0.858x | 0.316x |
| MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 2,953.7 | 1,337.0-2,481.7 | 9.37 | **no** | `b200_sxm-x192-nvl72-hybrid` | 550.0 | 1,208.8-2,243.7 | 1.93 | yes | 5.370x | 1.106x | 0.206x |
| MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 1,487.3 | 1,670.1-3,099.9 | 3.78 | yes | `b200_sxm-x636-nvl72-hybrid` | 668.9 | 1,830.2-3,397.2 | 1.55 | yes | 2.223x | 0.912x | 0.410x |
| MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 951.4 | 490.6-910.6 | 8.22 | **no** | `b200_sxm-x192-nvl72-hybrid` | 339.1 | 453.6-841.9 | 3.17 | yes | 2.806x | 1.082x | 0.386x |
| MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 579.1 | 536.5-995.9 | 4.58 | yes | `b200_sxm-x636-nvl72-hybrid` | 512.4 | 924.3-1,715.7 | 2.35 | yes | 1.130x | 0.580x | 0.514x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 238.5 | 134.7-250.0 | 7.51 | yes | `b200_sxm-x192-nvl72-hybrid` | 152.4 | 203.9-378.5 | 3.17 | yes | 1.565x | 0.661x | 0.422x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 158.6 | 138.9-257.7 | 4.84 | yes | `b200_sxm-x636-nvl72-hybrid` | 297.9 | 322.0-597.7 | 3.92 | yes | 0.532x | 0.431x | 0.810x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 59.7 | 34.0-63.1 | 7.45 | yes | `b200_sxm-x192-nvl72-hybrid` | 51.4 | 78.2-145.1 | 2.79 | yes | 1.162x | 0.435x | 0.374x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x22` | 40.2 | 57.8-107.3 | 2.95 | yes | `b200_sxm-x636-nvl72-hybrid` | 128.8 | 144.2-267.7 | 3.79 | yes | 0.312x | 0.401x | 1.284x |

**Does the ratio compress?** Of 20 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.198x to 1.284x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 18 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x64` | 5,205.6 | 3,046.5-5,654.8 | 7.24 | yes | `a100_sxm_80gb-x63-hybrid` | 331.6 | 676.5-1,255.6 | 2.08 | yes | 15.699x | 4.504x | 0.287x |
| MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 3,418.9 | 3,669.9-6,811.8 | 3.95 | yes | `a100_sxm_80gb-x112-tensor` | 338.7 | 724.7-1,345.2 | 1.98 | yes | 10.095x | 5.064x | 0.502x |
| MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3,921.8 | 4,269.7-7,925.1 | 3.89 | yes | `a100_sxm_80gb-x391-hybrid` | 327.2 | 712.5-1,322.6 | 1.95 | yes | 11.985x | 5.992x | 0.500x |
| MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,573.2 | 3,376.3-6,266.8 | 1.98 | yes | `a100_sxm_80gb-x1735-hybrid` | 323.9 | 704.6-1,307.8 | 1.95 | yes | 4.856x | 4.792x | 0.987x |
| MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3,921.8 | 4,269.7-7,925.1 | 3.89 | yes | `a100_sxm_80gb-x391-hybrid` | 327.2 | 712.5-1,322.6 | 1.95 | yes | 11.985x | 5.992x | 0.500x |
| MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,573.2 | 3,376.3-6,266.8 | 1.98 | yes | `a100_sxm_80gb-x1735-hybrid` | 323.9 | 704.6-1,307.8 | 1.95 | yes | 4.856x | 4.792x | 0.987x |
| MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x287` | 3,878.5 | 3,819.5-7,089.5 | 4.31 | yes | `a100_sxm_80gb-x283-hybrid` | 324.2 | 749.3-1,390.7 | 1.83 | yes | 11.961x | 5.098x | 0.426x |
| MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,573.2 | 3,376.3-6,266.8 | 1.98 | yes | `a100_sxm_80gb-x1735-hybrid` | 323.9 | 704.6-1,307.8 | 1.95 | yes | 4.856x | 4.792x | 0.987x |
| MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3,429.1 | 3,030.0-5,624.1 | 4.80 | yes | `a100_sxm_80gb-x391-hybrid` | 323.4 | 766.6-1,423.0 | 1.79 | yes | 10.605x | 3.952x | 0.373x |
| MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,469.8 | 2,010.7-3,732.0 | 3.10 | yes | `a100_sxm_80gb-x1735-hybrid` | 323.9 | 704.6-1,307.8 | 1.95 | yes | 4.537x | 2.854x | 0.629x |
| MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 2,667.5 | 2,110.7-3,917.7 | 5.36 | yes | `a100_sxm_80gb-x391-hybrid` | 323.4 | 766.6-1,423.0 | 1.79 | yes | 8.249x | 2.753x | 0.334x |
| MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,441.4 | 1,987.3-3,688.6 | 3.08 | yes | `a100_sxm_80gb-x1735-hybrid` | 323.6 | 844.6-1,567.7 | 1.62 | yes | 4.454x | 2.353x | 0.528x |
| MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,680.0 | 1,248.8-2,318.0 | 5.70 | yes | `a100_sxm_80gb-x391-hybrid` | 301.0 | 684.4-1,270.3 | 1.86 | yes | 5.581x | 1.825x | 0.327x |
| MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,043.0 | 1,287.2-2,389.2 | 3.44 | yes | `a100_sxm_80gb-x1735-hybrid` | 323.6 | 844.6-1,567.7 | 1.62 | yes | 3.223x | 1.524x | 0.473x |
| MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 504.3 | 343.3-637.3 | 6.23 | yes | `a100_sxm_80gb-x391-hybrid` | 162.2 | 347.0-644.0 | 1.98 | yes | 3.109x | 0.989x | 0.318x |
| MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 348.5 | 370.1-687.0 | 3.99 | yes | `a100_sxm_80gb-x1735-hybrid` | 310.1 | 794.5-1,474.7 | 1.65 | yes | 1.124x | 0.466x | 0.415x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 131.1 | 126.4-234.6 | 4.40 | yes | `a100_sxm_80gb-x391-hybrid` | 62.0 | 99.9-185.4 | 2.63 | yes | 2.113x | 1.266x | 0.599x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 91.8 | 94.3-175.0 | 4.13 | yes | `a100_sxm_80gb-x1735-hybrid` | 172.4 | 377.0-699.8 | 1.94 | yes | 0.533x | 0.250x | 0.469x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 33.0 | 48.2-89.4 | 2.91 | yes | `a100_sxm_80gb-x391-hybrid` | 22.2 | 25.9-48.0 | 3.63 | yes | 1.492x | 1.864x | 1.249x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x31` | 23.1 | 38.1-70.7 | 2.58 | yes | `a100_sxm_80gb-x1735-hybrid` | 67.0 | 110.2-204.5 | 2.58 | yes | 0.345x | 0.346x | 1.001x |

**Does the ratio compress?** Of 20 class rows in this study, 18 move the ROM-versus-GPU ratio DOWN under speculation and 2 move it UP. The movement spans 0.287x to 1.249x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 20 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 4,383.4 | 2,797.8-5,193.1 | 6.64 | yes | `b200_sxm-x53-nvl72-tensor` | 719.2 | 2,496.0-4,632.8 | 1.22 | yes | 6.095x | 1.121x | 0.184x |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3,406.7 | 2,434.4-4,518.5 | 5.93 | yes | `b200_sxm-x58-nvl72-tensor` | 723.9 | 2,526.5-4,689.5 | 1.21 | yes | 4.706x | 0.964x | 0.205x |
| MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,382.5 | 2,032.0-3,771.7 | 2.88 | yes | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 2,325.5-4,316.5 | 1.25 | yes | 2.018x | 0.874x | 0.433x |
| MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,382.5 | 2,032.0-3,771.7 | 2.88 | yes | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 2,325.5-4,316.5 | 1.25 | yes | 2.018x | 0.874x | 0.433x |
| MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,382.5 | 2,032.0-3,771.7 | 2.88 | yes | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 2,325.5-4,316.5 | 1.25 | yes | 2.018x | 0.874x | 0.433x |
| MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,382.5 | 2,032.0-3,771.7 | 2.88 | yes | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 2,325.5-4,316.5 | 1.25 | yes | 2.018x | 0.874x | 0.433x |
| MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,332.1 | 1,967.4-3,651.7 | 2.87 | yes | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 2,325.5-4,316.5 | 1.25 | yes | 1.945x | 0.846x | 0.435x |
| MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,073.9 | 1,278.3-2,372.8 | 3.56 | yes | `b200_sxm-x3149-nvl72-hybrid` | 670.2 | 2,176.0-4,038.9 | 1.31 | yes | 1.602x | 0.587x | 0.367x |
| MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 543.8 | 448.8-833.1 | 5.14 | yes | `b200_sxm-x3149-nvl72-hybrid` | 565.7 | 1,788.3-3,319.3 | 1.34 | yes | 0.961x | 0.251x | 0.261x |
| MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 156.3 | 116.6-216.3 | 5.68 | yes | `b200_sxm-x3149-nvl72-hybrid` | 351.3 | 1,067.3-1,981.0 | 1.40 | yes | 0.445x | 0.109x | 0.246x |
| MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 40.0 | 29.3-54.4 | 5.78 | yes | `b200_sxm-x3149-nvl72-hybrid` | 144.8 | 281.7-522.9 | 2.18 | yes | 0.276x | 0.104x | 0.377x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.184x to 0.435x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | 4,215.1 | 2,410.7-4,474.6 | 7.41 | yes | `a100_sxm_80gb-x139-tensor` | 331.5 | 712.1-1,321.7 | 1.97 | yes | 12.716x | 3.385x | 0.266x |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 3,075.4 | 1,946.8-3,613.5 | 6.70 | yes | `a100_sxm_80gb-x168-tensor` | 334.3 | 716.8-1,330.5 | 1.98 | yes | 9.198x | 2.716x | 0.295x |
| MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 1,090.2 | 2,584.2-4,796.6 | 1.79 | yes | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 644.3-1,195.9 | 1.99 | yes | 3.602x | 4.011x | 1.114x |
| MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,033.2 | 1,554.8-2,885.9 | 2.82 | yes | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 644.3-1,195.9 | 1.99 | yes | 3.413x | 2.413x | 0.707x |
| MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,033.2 | 1,554.8-2,885.9 | 2.82 | yes | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 644.3-1,195.9 | 1.99 | yes | 3.413x | 2.413x | 0.707x |
| MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,033.2 | 1,554.8-2,885.9 | 2.82 | yes | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 644.3-1,195.9 | 1.99 | yes | 3.413x | 2.413x | 0.707x |
| MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,033.2 | 1,554.8-2,885.9 | 2.82 | yes | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 644.3-1,195.9 | 1.99 | yes | 3.413x | 2.413x | 0.707x |
| MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 808.6 | 1,347.2-2,500.6 | 2.54 | yes | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 644.3-1,195.9 | 1.99 | yes | 2.671x | 2.091x | 0.783x |
| MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 325.4 | 463.2-859.7 | 2.98 | yes | `a100_sxm_80gb-x8562-hybrid` | 275.8 | 604.5-1,122.1 | 1.93 | yes | 1.180x | 0.766x | 0.649x |
| MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 90.2 | 131.6-244.4 | 2.90 | yes | `a100_sxm_80gb-x8562-hybrid` | 222.9 | 513.3-952.7 | 1.84 | yes | 0.405x | 0.256x | 0.634x |
| MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 22.9 | 33.2-61.7 | 2.93 | yes | `a100_sxm_80gb-x8562-hybrid` | 95.2 | 166.9-309.8 | 2.42 | yes | 0.241x | 0.199x | 0.827x |

**Does the ratio compress?** Of 11 class rows in this study, 10 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.266x to 1.114x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,200.0 | 5,133.5-9,528.4 | 5.95 | yes | `b200_sxm-x61-nvl72-tensor` | 758.2 | 2,633.9-4,888.8 | 1.22 | yes | 9.497x | 1.949x | 0.205x |
| MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4,579.3 | 3,830.7-7,110.3 | 5.07 | yes | `b200_sxm-x58-nvl72-tensor` | 757.2 | 2,621.5-4,865.8 | 1.22 | yes | 6.048x | 1.461x | 0.242x |
| MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,200.0 | 5,133.5-9,528.4 | 5.95 | yes | `b200_sxm-x61-nvl72-tensor` | 748.9 | 2,471.2-4,586.8 | 1.28 | yes | 9.614x | 2.077x | 0.216x |
| MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4,579.3 | 3,830.7-7,110.3 | 5.07 | yes | `b200_sxm-x58-nvl72-tensor` | 747.6 | 2,456.3-4,559.3 | 1.29 | yes | 6.126x | 1.560x | 0.255x |
| MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,200.0 | 5,133.5-9,528.4 | 5.95 | yes | `b200_sxm-x61-nvl72-tensor` | 731.6 | 2,223.5-4,127.2 | 1.40 | yes | 9.842x | 2.309x | 0.235x |
| MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4,579.3 | 3,830.7-7,110.3 | 5.07 | yes | `b200_sxm-x58-nvl72-tensor` | 729.7 | 2,207.6-4,097.5 | 1.40 | yes | 6.276x | 1.735x | 0.276x |
| MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,200.0 | 5,133.5-9,528.4 | 5.95 | yes | `b200_sxm-x61-nvl72-tensor` | 701.4 | 1,902.6-3,531.5 | 1.56 | yes | 10.266x | 2.698x | 0.263x |
| MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4,579.3 | 3,830.7-7,110.3 | 5.07 | yes | `b200_sxm-x58-nvl72-tensor` | 698.5 | 1,888.4-3,505.2 | 1.57 | yes | 6.556x | 2.029x | 0.309x |
| MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 7,132.9 | 5,015.2-9,308.8 | 6.03 | yes | `b200_sxm-x87-nvl72-hybrid` | 676.9 | 1,802.2-3,345.2 | 1.59 | yes | 10.538x | 2.783x | 0.264x |
| MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 4,533.9 | 4,794.8-8,899.7 | 4.01 | yes | `b200_sxm-x87-nvl72-hybrid` | 676.9 | 1,802.2-3,345.2 | 1.59 | yes | 6.699x | 2.660x | 0.397x |
| MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7,024.5 | 5,023.4-9,324.1 | 5.93 | yes | `b200_sxm-x173-nvl72-hybrid` | 675.7 | 1,710.9-3,175.7 | 1.67 | yes | 10.396x | 2.936x | 0.282x |
| MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 4,454.8 | 4,819.1-8,944.9 | 3.92 | yes | `b200_sxm-x173-nvl72-hybrid` | 675.7 | 1,710.9-3,175.7 | 1.67 | yes | 6.593x | 2.817x | 0.427x |
| MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,985.7 | 3,216.9-5,970.9 | 9.21 | **no** | `b200_sxm-x173-nvl72-hybrid` | 619.2 | 1,278.1-2,372.3 | 2.05 | yes | 11.282x | 2.517x | 0.223x |
| MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,430.1 | 4,811.5-8,930.8 | 3.90 | yes | `b200_sxm-x347-nvl72-hybrid` | 671.7 | 1,588.8-2,949.1 | 1.79 | yes | 6.595x | 3.028x | 0.459x |
| MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,676.4 | 1,370.1-2,543.1 | 14.47 | **no** | `b200_sxm-x173-nvl72-hybrid` | 479.3 | 527.0-978.2 | 3.86 | yes | 9.756x | 2.600x | 0.266x |
| MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,616.0 | 2,590.5-4,808.2 | 5.92 | yes | `b200_sxm-x347-nvl72-hybrid` | 545.1 | 731.6-1,357.9 | 3.16 | yes | 6.634x | 3.541x | 0.534x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,851.5 | 434.2-805.8 | 18.08 | **no** | `b200_sxm-x173-nvl72-hybrid` | 329.6 | 282.4-524.2 | 4.95 | yes | 5.617x | 1.537x | 0.274x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,605.5 | 807.2-1,498.2 | 8.43 | **no** | `b200_sxm-x347-nvl72-hybrid` | 388.1 | 265.6-493.1 | 6.19 | yes | 4.137x | 3.039x | 0.735x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 527.7 | 129.2-239.8 | 17.32 | **no** | `b200_sxm-x173-nvl72-hybrid` | 195.2 | 127.6-236.8 | 6.49 | yes | 2.704x | 1.012x | 0.374x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 451.7 | 280.4-520.4 | 6.83 | yes | `b200_sxm-x347-nvl72-hybrid` | 242.8 | 123.3-229.0 | 8.35 | **no** | 1.860x | 2.273x | 1.222x |

**Does the ratio compress?** Of 20 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.205x to 1.222x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 15 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,900.9 | 4,101.9-7,613.7 | 7.13 | yes | `a100_sxm_80gb-x77-hybrid` | 369.9 | 717.7-1,332.1 | 2.19 | yes | 18.654x | 5.716x | 0.306x |
| MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,786.0 | 4,318.9-8,016.4 | 3.72 | yes | `a100_sxm_80gb-x168-hybrid` | 371.6 | 784.6-1,456.3 | 2.01 | yes | 10.189x | 5.505x | 0.540x |
| MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,900.9 | 4,101.9-7,613.7 | 7.13 | yes | `a100_sxm_80gb-x77-hybrid` | 369.9 | 717.7-1,332.1 | 2.19 | yes | 18.654x | 5.716x | 0.306x |
| MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,786.0 | 4,318.9-8,016.4 | 3.72 | yes | `a100_sxm_80gb-x168-hybrid` | 371.6 | 784.6-1,456.3 | 2.01 | yes | 10.189x | 5.505x | 0.540x |
| MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,900.9 | 4,101.9-7,613.7 | 7.13 | yes | `a100_sxm_80gb-x77-hybrid` | 369.9 | 717.7-1,332.1 | 2.19 | yes | 18.654x | 5.716x | 0.306x |
| MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,786.0 | 4,318.9-8,016.4 | 3.72 | yes | `a100_sxm_80gb-x168-hybrid` | 371.6 | 784.6-1,456.3 | 2.01 | yes | 10.189x | 5.505x | 0.540x |
| MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,900.9 | 4,101.9-7,613.7 | 7.13 | yes | `a100_sxm_80gb-x77-hybrid` | 369.9 | 717.7-1,332.1 | 2.19 | yes | 18.654x | 5.716x | 0.306x |
| MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,786.0 | 4,318.9-8,016.4 | 3.72 | yes | `a100_sxm_80gb-x168-hybrid` | 371.6 | 784.6-1,456.3 | 2.01 | yes | 10.189x | 5.505x | 0.540x |
| MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 6,845.1 | 4,084.1-7,580.6 | 7.11 | yes | `a100_sxm_80gb-x154-hybrid` | 366.7 | 761.1-1,412.6 | 2.04 | yes | 18.665x | 5.366x | 0.288x |
| MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill` | 3,694.8 | 5,231.8-9,711.0 | 2.99 | yes | `a100_sxm_80gb-x336-hybrid` | 364.9 | 811.8-1,506.7 | 1.91 | yes | 10.126x | 6.445x | 0.636x |
| MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,732.4 | 4,079.3-7,571.8 | 7.00 | yes | `a100_sxm_80gb-x335-hybrid` | 364.5 | 810.2-1,503.8 | 1.91 | yes | 18.470x | 5.035x | 0.273x |
| MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,606.0 | 5,220.0-9,689.1 | 2.93 | yes | `a100_sxm_80gb-x672-hybrid` | 363.0 | 861.9-1,599.9 | 1.79 | yes | 9.933x | 6.056x | 0.610x |
| MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,385.3 | 2,450.6-4,548.6 | 11.05 | **no** | `a100_sxm_80gb-x335-hybrid` | 337.9 | 694.4-1,288.9 | 2.06 | yes | 18.894x | 3.529x | 0.187x |
| MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,508.2 | 3,913.5-7,263.9 | 3.80 | yes | `a100_sxm_80gb-x672-hybrid` | 363.0 | 861.9-1,599.9 | 1.79 | yes | 9.664x | 4.540x | 0.470x |
| MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,979.3 | 1,023.7-1,900.2 | 16.48 | **no** | `a100_sxm_80gb-x335-hybrid` | 212.3 | 401.7-745.6 | 2.24 | yes | 18.739x | 2.549x | 0.136x |
| MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,159.4 | 1,973.8-3,663.7 | 4.64 | yes | `a100_sxm_80gb-x672-hybrid` | 279.3 | 548.8-1,018.7 | 2.16 | yes | 7.733x | 3.597x | 0.465x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,436.8 | 321.5-596.8 | 18.95 | **no** | `a100_sxm_80gb-x335-hybrid` | 101.5 | 177.5-329.5 | 2.42 | yes | 14.159x | 1.811x | 0.128x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 721.8 | 587.6-1,090.7 | 5.21 | yes | `a100_sxm_80gb-x672-hybrid` | 148.4 | 280.1-519.9 | 2.25 | yes | 4.865x | 2.098x | 0.431x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 396.9 | 95.9-178.0 | 17.55 | **no** | `a100_sxm_80gb-x335-hybrid` | 56.2 | 47.3-87.9 | 5.04 | yes | 7.061x | 2.026x | 0.287x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 189.9 | 203.0-376.7 | 3.97 | yes | `a100_sxm_80gb-x672-hybrid` | 71.9 | 89.3-165.7 | 3.41 | yes | 2.643x | 2.273x | 0.860x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.128x to 0.860x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 16 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | 3,083.8 | 2,133.3-3,959.7 | 6.13 | yes | `b200_sxm-x71-nvl72-tensor` | 503.6 | 1,711.4-3,176.6 | 1.25 | yes | 6.124x | 1.247x | 0.204x |
| MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 2,362.7 | 2,225.9-4,131.5 | 4.50 | yes | `b200_sxm-x87-nvl72-hybrid` | 485.8 | 1,580.4-2,933.5 | 1.30 | yes | 4.863x | 1.408x | 0.290x |
| MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,226.9 | 1,397.5-2,593.9 | 3.72 | yes | `b200_sxm-x1416-nvl72-hybrid` | 492.3 | 1,705.7-3,166.1 | 1.22 | yes | 2.492x | 0.819x | 0.329x |
| MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,226.9 | 1,397.5-2,593.9 | 3.72 | yes | `b200_sxm-x1416-nvl72-hybrid` | 492.3 | 1,705.7-3,166.1 | 1.22 | yes | 2.492x | 0.819x | 0.329x |
| MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,226.9 | 1,397.5-2,593.9 | 3.72 | yes | `b200_sxm-x1416-nvl72-hybrid` | 492.3 | 1,705.7-3,166.1 | 1.22 | yes | 2.492x | 0.819x | 0.329x |
| MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,226.9 | 1,397.5-2,593.9 | 3.72 | yes | `b200_sxm-x1416-nvl72-hybrid` | 492.3 | 1,705.7-3,166.1 | 1.22 | yes | 2.492x | 0.819x | 0.329x |
| MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,226.9 | 1,397.5-2,593.9 | 3.72 | yes | `b200_sxm-x1416-nvl72-hybrid` | 483.9 | 1,584.4-2,940.8 | 1.30 | yes | 2.535x | 0.882x | 0.348x |
| MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,099.2 | 1,305.6-2,423.4 | 3.57 | yes | `b200_sxm-x1416-nvl72-hybrid` | 463.2 | 1,336.8-2,481.4 | 1.47 | yes | 2.373x | 0.977x | 0.412x |
| MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 534.5 | 480.0-890.9 | 4.72 | yes | `b200_sxm-x1416-nvl72-hybrid` | 371.7 | 735.9-1,366.0 | 2.14 | yes | 1.438x | 0.652x | 0.454x |
| MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 156.9 | 127.4-236.4 | 5.22 | yes | `b200_sxm-x1416-nvl72-hybrid` | 221.5 | 268.7-498.7 | 3.50 | yes | 0.708x | 0.474x | 0.669x |
| MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x49` | 40.3 | 32.1-59.6 | 5.32 | yes | `b200_sxm-x1416-nvl72-hybrid` | 99.0 | 128.6-238.7 | 3.27 | yes | 0.407x | 0.250x | 0.614x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.204x to 0.669x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | 3,002.6 | 1,861.3-3,454.8 | 6.84 | yes | `a100_sxm_80gb-x178-tensor` | 224.9 | 411.0-762.9 | 2.32 | yes | 13.348x | 4.529x | 0.339x |
| MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 2,254.0 | 1,352.2-2,509.8 | 7.07 | yes | `a100_sxm_80gb-x168-tensor` | 224.5 | 410.6-762.1 | 2.32 | yes | 10.040x | 3.293x | 0.328x |
| MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,011.9 | 2,043.8-3,793.5 | 2.10 | yes | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 387.1-718.5 | 2.25 | yes | 4.936x | 5.280x | 1.070x |
| MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,011.9 | 2,043.8-3,793.5 | 2.10 | yes | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 387.1-718.5 | 2.25 | yes | 4.936x | 5.280x | 1.070x |
| MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,011.9 | 2,043.8-3,793.5 | 2.10 | yes | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 387.1-718.5 | 2.25 | yes | 4.936x | 5.280x | 1.070x |
| MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,011.9 | 2,043.8-3,793.5 | 2.10 | yes | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 387.1-718.5 | 2.25 | yes | 4.936x | 5.280x | 1.070x |
| MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 871.4 | 1,495.3-2,775.5 | 2.47 | yes | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 387.1-718.5 | 2.25 | yes | 4.251x | 3.863x | 0.909x |
| MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 803.5 | 1,022.6-1,898.1 | 3.33 | yes | `a100_sxm_80gb-x3805-hybrid` | 203.5 | 373.1-692.4 | 2.31 | yes | 3.947x | 2.741x | 0.694x |
| MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 327.8 | 339.3-629.7 | 4.10 | yes | `a100_sxm_80gb-x3805-hybrid` | 163.4 | 234.7-435.7 | 2.95 | yes | 2.007x | 1.445x | 0.720x |
| MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 90.1 | 87.6-162.7 | 4.36 | yes | `a100_sxm_80gb-x3805-hybrid` | 120.9 | 226.6-420.6 | 2.26 | yes | 0.745x | 0.387x | 0.519x |
| MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x68` | 22.9 | 22.0-40.9 | 4.40 | yes | `a100_sxm_80gb-x3805-hybrid` | 53.9 | 102.8-190.8 | 2.23 | yes | 0.424x | 0.214x | 0.506x |

**Does the ratio compress?** Of 11 class rows in this study, 7 move the ROM-versus-GPU ratio DOWN under speculation and 4 move it UP. The movement spans 0.328x to 1.070x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | 2,570.2 | 2,016.9-3,743.6 | 5.40 | yes | `b200_sxm-x170-nvl72-hybrid` | 469.2 | 1,606.6-2,982.1 | 1.24 | yes | 5.478x | 1.255x | 0.229x |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 2,022.5 | 1,028.1-1,908.4 | 8.34 | **no** | `b200_sxm-x116-nvl72-hybrid` | 471.0 | 1,603.9-2,977.1 | 1.25 | yes | 4.294x | 0.641x | 0.149x |
| MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 845.7 | 1,087.7-2,018.9 | 3.30 | yes | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,478.6-2,744.4 | 1.28 | yes | 1.888x | 0.736x | 0.390x |
| MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 845.7 | 1,087.7-2,018.9 | 3.30 | yes | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,478.6-2,744.4 | 1.28 | yes | 1.888x | 0.736x | 0.390x |
| MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 845.7 | 1,087.7-2,018.9 | 3.30 | yes | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,478.6-2,744.4 | 1.28 | yes | 1.888x | 0.736x | 0.390x |
| MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 845.7 | 1,087.7-2,018.9 | 3.30 | yes | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,478.6-2,744.4 | 1.28 | yes | 1.888x | 0.736x | 0.390x |
| MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 845.7 | 1,087.7-2,018.9 | 3.30 | yes | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,478.6-2,744.4 | 1.28 | yes | 1.888x | 0.736x | 0.390x |
| MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 829.8 | 1,076.6-1,998.2 | 3.27 | yes | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,478.6-2,744.4 | 1.28 | yes | 1.853x | 0.728x | 0.393x |
| MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 480.9 | 367.8-682.6 | 5.54 | yes | `b200_sxm-x6992-nvl72-hybrid` | 401.8 | 1,094.8-2,032.0 | 1.56 | yes | 1.197x | 0.336x | 0.281x |
| MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 152.6 | 106.7-198.1 | 6.07 | yes | `b200_sxm-x6992-nvl72-hybrid` | 278.1 | 775.7-1,439.8 | 1.52 | yes | 0.549x | 0.138x | 0.251x |
| MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 39.8 | 26.9-50.0 | 6.27 | yes | `b200_sxm-x6992-nvl72-hybrid` | 126.7 | 274.5-509.4 | 1.96 | yes | 0.314x | 0.098x | 0.312x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.149x to 0.393x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 10 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | 2,401.1 | 1,479.0-2,745.2 | 6.88 | yes | `a100_sxm_80gb-x316-tensor` | 224.4 | 412.4-765.5 | 2.31 | yes | 10.698x | 3.586x | 0.335x |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 1,874.2 | 1,402.9-2,604.0 | 5.66 | yes | `a100_sxm_80gb-x336-hybrid` | 190.6 | 373.3-693.0 | 2.16 | yes | 9.836x | 3.758x | 0.382x |
| MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 624.3 | 1,587.2-2,946.1 | 1.67 | yes | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 358.1-664.7 | 2.24 | yes | 3.301x | 4.432x | 1.343x |
| MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 590.7 | 1,173.6-2,178.3 | 2.13 | yes | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 358.1-664.7 | 2.24 | yes | 3.124x | 3.277x | 1.049x |
| MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 582.6 | 801.1-1,486.9 | 3.08 | yes | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 358.1-664.7 | 2.24 | yes | 3.081x | 2.237x | 0.726x |
| MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 582.6 | 801.1-1,486.9 | 3.08 | yes | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 358.1-664.7 | 2.24 | yes | 3.081x | 2.237x | 0.726x |
| MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 582.6 | 801.1-1,486.9 | 3.08 | yes | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 358.1-664.7 | 2.24 | yes | 3.081x | 2.237x | 0.726x |
| MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 582.6 | 801.1-1,486.9 | 3.08 | yes | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 358.1-664.7 | 2.24 | yes | 3.081x | 2.237x | 0.726x |
| MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 284.4 | 410.6-762.1 | 2.94 | yes | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 358.1-664.7 | 2.24 | yes | 1.504x | 1.147x | 0.762x |
| MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 88.4 | 122.4-227.1 | 3.06 | yes | `a100_sxm_80gb-x18971-hybrid` | 139.5 | 224.9-417.5 | 2.63 | yes | 0.634x | 0.544x | 0.858x |
| MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 22.8 | 31.0-57.6 | 3.12 | yes | `a100_sxm_80gb-x18971-hybrid` | 77.4 | 160.0-296.9 | 2.05 | yes | 0.295x | 0.194x | 0.658x |

**Does the ratio compress?** Of 11 class rows in this study, 9 move the ROM-versus-GPU ratio DOWN under speculation and 2 move it UP. The movement spans 0.335x to 1.343x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,330.1 | 3,076.9-5,711.1 | 5.97 | yes | `b200_sxm-x78-nvl72-hybrid` | 490.3 | 1,562.3-2,899.8 | 1.33 | yes | 8.832x | 1.969x | 0.223x |
| MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,857.5 | 2,181.2-4,048.6 | 5.55 | yes | `b200_sxm-x87-nvl72-hybrid` | 494.2 | 1,601.2-2,972.1 | 1.31 | yes | 5.782x | 1.362x | 0.236x |
| MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,330.1 | 3,076.9-5,711.1 | 5.97 | yes | `b200_sxm-x78-nvl72-hybrid` | 490.3 | 1,562.3-2,899.8 | 1.33 | yes | 8.832x | 1.969x | 0.223x |
| MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,857.5 | 2,181.2-4,048.6 | 5.55 | yes | `b200_sxm-x87-nvl72-hybrid` | 494.2 | 1,601.2-2,972.1 | 1.31 | yes | 5.782x | 1.362x | 0.236x |
| MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,330.1 | 3,076.9-5,711.1 | 5.97 | yes | `b200_sxm-x78-nvl72-hybrid` | 477.9 | 1,402.9-2,604.0 | 1.44 | yes | 9.060x | 2.193x | 0.242x |
| MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,857.5 | 2,181.2-4,048.6 | 5.55 | yes | `b200_sxm-x87-nvl72-hybrid` | 482.8 | 1,444.7-2,681.5 | 1.42 | yes | 5.919x | 1.510x | 0.255x |
| MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,330.1 | 3,076.9-5,711.1 | 5.97 | yes | `b200_sxm-x78-nvl72-hybrid` | 455.6 | 1,183.8-2,197.2 | 1.63 | yes | 9.504x | 2.599x | 0.273x |
| MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,857.5 | 2,181.2-4,048.6 | 5.55 | yes | `b200_sxm-x87-nvl72-hybrid` | 461.9 | 1,225.9-2,275.4 | 1.60 | yes | 6.186x | 1.779x | 0.288x |
| MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 4,285.0 | 3,112.4-5,777.0 | 5.84 | yes | `b200_sxm-x150-nvl72-hybrid` | 456.9 | 1,185.0-2,199.5 | 1.63 | yes | 9.379x | 2.626x | 0.280x |
| MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,857.5 | 2,181.2-4,048.6 | 5.55 | yes | `b200_sxm-x87-nvl72-hybrid` | 426.8 | 984.8-1,827.9 | 1.84 | yes | 6.695x | 2.215x | 0.331x |
| MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 4,214.3 | 2,071.1-3,844.3 | 8.63 | **no** | `b200_sxm-x150-nvl72-hybrid` | 417.5 | 922.2-1,711.7 | 1.92 | yes | 10.095x | 2.246x | 0.222x |
| MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 2,833.9 | 2,210.5-4,103.0 | 5.44 | yes | `b200_sxm-x173-nvl72-hybrid` | 427.7 | 953.8-1,770.4 | 1.90 | yes | 6.625x | 2.318x | 0.350x |
| MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 3,932.5 | 1,784.8-3,312.9 | 9.34 | **no** | `b200_sxm-x200-nvl72-hybrid` | 387.1 | 695.8-1,291.5 | 2.36 | yes | 10.159x | 2.565x | 0.253x |
| MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,784.0 | 2,202.2-4,087.5 | 5.36 | yes | `b200_sxm-x347-nvl72-hybrid` | 426.2 | 897.1-1,665.1 | 2.01 | yes | 6.531x | 2.455x | 0.376x |
| MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 2,411.3 | 532.4-988.2 | 19.20 | **no** | `b200_sxm-x200-nvl72-hybrid` | 266.4 | 265.1-492.1 | 4.26 | yes | 9.051x | 2.008x | 0.222x |
| MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,030.3 | 1,034.2-1,919.7 | 8.32 | **no** | `b200_sxm-x347-nvl72-hybrid` | 310.8 | 379.4-704.1 | 3.47 | yes | 6.532x | 2.726x | 0.417x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 883.4 | 248.6-461.4 | 15.07 | **no** | `b200_sxm-x173-nvl72-hybrid` | 152.2 | 75.0-139.2 | 8.61 | **no** | 5.803x | 3.315x | 0.571x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 789.2 | 279.8-519.4 | 11.96 | **no** | `b200_sxm-x347-nvl72-hybrid` | 197.6 | 134.3-249.3 | 6.24 | yes | 3.993x | 2.083x | 0.522x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 345.8 | 85.6-158.9 | 17.13 | **no** | `b200_sxm-x200-nvl72-hybrid` | 89.2 | 40.7-75.6 | 9.29 | **no** | 3.877x | 2.103x | 0.542x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 215.2 | 96.4-179.0 | 9.46 | **no** | `b200_sxm-x347-nvl72-hybrid` | 114.4 | 60.8-112.9 | 7.97 | **no** | 1.882x | 1.586x | 0.843x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.222x to 0.843x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 12 of 20 ROM rows and 17 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,134.0 | 2,476.5-4,596.7 | 7.08 | yes | `a100_sxm_80gb-x208-tensor` | 227.6 | 414.1-768.7 | 2.33 | yes | 18.165x | 5.980x | 0.329x |
| MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 2,383.2 | 2,455.1-4,557.0 | 4.12 | yes | `a100_sxm_80gb-x168-tensor` | 226.3 | 412.0-764.7 | 2.33 | yes | 10.531x | 5.959x | 0.566x |
| MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,134.0 | 2,476.5-4,596.7 | 7.08 | yes | `a100_sxm_80gb-x208-hybrid` | 211.6 | 389.2-722.4 | 2.30 | yes | 19.541x | 6.363x | 0.326x |
| MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,340.4 | 2,356.8-4,374.6 | 4.21 | yes | `a100_sxm_80gb-x336-hybrid` | 212.8 | 395.7-734.5 | 2.28 | yes | 10.997x | 5.956x | 0.542x |
| MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,134.0 | 2,476.5-4,596.7 | 7.08 | yes | `a100_sxm_80gb-x208-hybrid` | 211.6 | 389.2-722.4 | 2.30 | yes | 19.541x | 6.363x | 0.326x |
| MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,340.4 | 2,356.8-4,374.6 | 4.21 | yes | `a100_sxm_80gb-x336-hybrid` | 212.8 | 395.7-734.5 | 2.28 | yes | 10.997x | 5.956x | 0.542x |
| MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,134.0 | 2,476.5-4,596.7 | 7.08 | yes | `a100_sxm_80gb-x208-hybrid` | 195.4 | 348.9-647.5 | 2.38 | yes | 21.152x | 7.099x | 0.336x |
| MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,340.4 | 2,356.8-4,374.6 | 4.21 | yes | `a100_sxm_80gb-x336-hybrid` | 206.8 | 335.8-623.4 | 2.61 | yes | 11.318x | 7.018x | 0.620x |
| MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 4,119.4 | 2,573.2-4,776.2 | 6.79 | yes | `a100_sxm_80gb-x249-hybrid` | 182.3 | 256.5-476.0 | 3.01 | yes | 22.600x | 10.034x | 0.444x |
| MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,340.4 | 2,356.8-4,374.6 | 4.21 | yes | `a100_sxm_80gb-x336-hybrid` | 190.4 | 310.6-576.6 | 2.60 | yes | 12.295x | 7.587x | 0.617x |
| MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 3,866.1 | 1,582.9-2,938.1 | 10.36 | **no** | `a100_sxm_80gb-x249-hybrid` | 178.1 | 339.2-629.7 | 2.23 | yes | 21.704x | 4.666x | 0.215x |
| MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,310.2 | 1,684.8-3,127.3 | 5.81 | yes | `a100_sxm_80gb-x672-hybrid` | 189.6 | 307.2-570.1 | 2.62 | yes | 12.182x | 5.485x | 0.450x |
| MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 3,593.9 | 1,346.0-2,498.4 | 11.32 | **no** | `a100_sxm_80gb-x373-hybrid` | 168.9 | 315.8-586.2 | 2.27 | yes | 21.278x | 4.262x | 0.200x |
| MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,032.8 | 1,682.8-3,123.5 | 5.12 | yes | `a100_sxm_80gb-x672-hybrid` | 177.8 | 382.1-709.2 | 1.97 | yes | 11.434x | 4.404x | 0.385x |
| MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 1,939.3 | 384.6-713.9 | 21.38 | **no** | `a100_sxm_80gb-x373-hybrid` | 105.4 | 163.8-304.1 | 2.73 | yes | 18.395x | 2.347x | 0.128x |
| MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,117.6 | 489.9-909.3 | 9.67 | **no** | `a100_sxm_80gb-x672-hybrid` | 133.9 | 209.9-389.6 | 2.70 | yes | 8.347x | 2.334x | 0.280x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 783.2 | 182.4-338.6 | 18.20 | **no** | `a100_sxm_80gb-x373-hybrid` | 47.0 | 87.8-162.9 | 2.27 | yes | 16.669x | 2.078x | 0.125x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 345.4 | 127.2-236.2 | 11.51 | **no** | `a100_sxm_80gb-x672-hybrid` | 67.2 | 116.7-216.7 | 2.44 | yes | 5.142x | 1.090x | 0.212x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 231.5 | 49.3-91.5 | 19.91 | **no** | `a100_sxm_80gb-x373-hybrid` | 22.0 | 23.2-43.1 | 4.01 | yes | 10.540x | 2.125x | 0.202x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 89.5 | 78.2-145.2 | 4.85 | yes | `a100_sxm_80gb-x672-hybrid` | 28.7 | 37.5-69.6 | 3.24 | yes | 3.119x | 2.086x | 0.669x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.125x to 0.669x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 13 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-qwen3-8b-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x180` | 3,799.1 | 2,540.1-4,714.8 | 6.34 | yes | `b200_sxm-x92-nvl72-hybrid` | 772.6 | 2,906.2-5,394.3 | 1.13 | yes | 4.917x | 0.874x | 0.178x |
| Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 5,035.0 | 7,582.4-14,074.0 | 2.82 | yes | `b200_sxm-x58-nvl72-tensor` | 849.5 | 3,173.7-5,890.7 | 1.13 | yes | 5.927x | 2.389x | 0.403x |

**Does the ratio compress?** Of 2 class rows in this study, 2 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.178x to 0.403x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 2 of 2 ROM rows and 2 of 2 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-qwen3-8b-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x227` | 3,580.9 | 2,512.6-4,663.7 | 6.04 | yes | `a100_sxm_80gb-x224-tensor` | 468.9 | 989.5-1,836.6 | 2.01 | yes | 7.636x | 2.539x | 0.333x |
| Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 5,016.0 | 5,581.0-10,359.1 | 3.81 | yes | `a100_sxm_80gb-x112-tensor` | 389.3 | 908.3-1,685.9 | 1.82 | yes | 12.884x | 6.144x | 0.477x |

**Does the ratio compress?** Of 2 class rows in this study, 2 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.333x to 0.477x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 2 of 2 ROM rows and 2 of 2 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-qwen3-8b-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x60-romfill` | 7,172.1 | 4,669.6-8,667.4 | 6.51 | yes | `b200_sxm-x31-nvl72-tensor` | 1,034.4 | 3,745.1-6,951.4 | 1.17 | yes | 6.933x | 1.247x | 0.180x |
| Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 5,049.6 | 9,486.3-17,607.8 | 2.26 | yes | `b200_sxm-x58-nvl72-tensor` | 1,158.3 | 4,148.2-7,699.6 | 1.18 | yes | 4.359x | 2.287x | 0.525x |
| Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x139-romfill` | 1,919.2 | 4,373.8-8,118.4 | 1.86 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,087.6 | 3,556.4-6,601.1 | 1.30 | yes | 1.765x | 1.230x | 0.697x |
| Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x139` | 1,805.6 | 3,085.3-5,726.7 | 2.48 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,087.6 | 3,556.4-6,601.1 | 1.30 | yes | 1.660x | 0.868x | 0.523x |
| Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1,798.4 | 5,507.0-10,221.7 | 1.38 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,087.6 | 3,556.4-6,601.1 | 1.30 | yes | 1.654x | 1.548x | 0.936x |
| Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1,798.4 | 5,507.0-10,221.7 | 1.38 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,087.6 | 3,556.4-6,601.1 | 1.30 | yes | 1.654x | 1.548x | 0.936x |
| Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1,798.4 | 5,507.0-10,221.7 | 1.38 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,087.6 | 3,556.4-6,601.1 | 1.30 | yes | 1.654x | 1.548x | 0.936x |
| Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1,346.6 | 3,847.1-7,140.7 | 1.48 | yes | `b200_sxm-x4016-nvl72-hybrid` | 1,075.6 | 3,463.2-6,428.1 | 1.32 | yes | 1.252x | 1.111x | 0.887x |
| Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 578.5 | 2,204.7-4,092.2 | 1.11 | yes | `b200_sxm-x4016-nvl72-hybrid` | 851.3 | 2,815.5-5,225.8 | 1.28 | yes | 0.680x | 0.783x | 1.152x |
| Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 157.5 | 643.2-1,193.9 | 1.04 | yes | `b200_sxm-x4016-nvl72-hybrid` | 481.1 | 1,402.1-2,602.4 | 1.45 | yes | 0.327x | 0.459x | 1.401x |
| Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 40.0 | 166.4-308.8 | 1.02 | yes | `b200_sxm-x4016-nvl72-hybrid` | 177.1 | 605.0-1,122.9 | 1.24 | yes | 0.226x | 0.275x | 1.219x |

**Does the ratio compress?** Of 11 class rows in this study, 8 move the ROM-versus-GPU ratio DOWN under speculation and 3 move it UP. The movement spans 0.180x to 1.401x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-qwen3-8b-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 7,166.0 | 4,504.9-8,361.7 | 6.74 | yes | `a100_sxm_80gb-x56-tensor` | 461.8 | 1,019.7-1,892.6 | 1.92 | yes | 15.517x | 4.418x | 0.285x |
| Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 5,071.3 | 8,643.7-16,043.9 | 2.49 | yes | `a100_sxm_80gb-x112-tensor` | 517.9 | 1,052.0-1,952.7 | 2.09 | yes | 9.792x | 8.216x | 0.839x |
| Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196-romfill` | 1,787.0 | 4,153.9-7,710.2 | 1.82 | yes | `a100_sxm_80gb-x10969-tensor` | 475.1 | 669.3-1,242.3 | 3.01 | yes | 3.761x | 6.206x | 1.650x |
| Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 1,683.6 | 2,989.8-5,549.5 | 2.39 | yes | `a100_sxm_80gb-x10969-hybrid` | 456.0 | 956.4-1,775.3 | 2.02 | yes | 3.692x | 3.126x | 0.847x |
| Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 1,484.4 | 1,918.2-3,560.4 | 3.28 | yes | `a100_sxm_80gb-x10969-hybrid` | 456.0 | 956.4-1,775.3 | 2.02 | yes | 3.255x | 2.006x | 0.616x |
| Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 1,190.3 | 1,115.9-2,071.3 | 4.52 | yes | `a100_sxm_80gb-x10969-hybrid` | 456.0 | 956.4-1,775.3 | 2.02 | yes | 2.610x | 1.167x | 0.447x |
| Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,160.4 | 3,937.8-7,309.1 | 1.25 | yes | `a100_sxm_80gb-x10969-hybrid` | 456.0 | 956.4-1,775.3 | 2.02 | yes | 2.544x | 4.117x | 1.618x |
| Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 970.9 | 3,265.8-6,061.8 | 1.26 | yes | `a100_sxm_80gb-x10969-hybrid` | 456.0 | 956.4-1,775.3 | 2.02 | yes | 2.129x | 3.415x | 1.604x |
| Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 342.6 | 1,339.3-2,485.9 | 1.08 | yes | `a100_sxm_80gb-x10969-hybrid` | 419.8 | 758.6-1,408.1 | 2.35 | yes | 0.816x | 1.765x | 2.163x |
| Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 91.0 | 375.1-696.3 | 1.03 | yes | `a100_sxm_80gb-x10969-hybrid` | 256.3 | 448.4-832.3 | 2.42 | yes | 0.355x | 0.837x | 2.355x |
| Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 23.0 | 96.3-178.8 | 1.01 | yes | `a100_sxm_80gb-x10969-hybrid` | 112.7 | 413.2-767.0 | 1.16 | yes | 0.204x | 0.233x | 1.142x |

**Does the ratio compress?** Of 11 class rows in this study, 5 move the ROM-versus-GPU ratio DOWN under speculation and 6 move it UP. The movement spans 0.285x to 2.355x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 2,959.9 | 1,311.1-2,433.6 | 9.57 | **no** | `b200_sxm-x58-nvl72-tensor` | 559.2 | 748.5-1,389.4 | 3.17 | yes | 5.294x | 1.752x | 0.331x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 2,778.1 | 2,388.1-4,432.6 | 4.93 | yes | `b200_sxm-x58-nvl72-tensor` | 559.2 | 748.5-1,389.4 | 3.17 | yes | 4.968x | 3.190x | 0.642x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 2,513.2 | 1,175.9-2,182.6 | 9.06 | **no** | `b200_sxm-x142-nvl72-hybrid` | 558.7 | 745.1-1,383.0 | 3.18 | yes | 4.498x | 1.578x | 0.351x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,809.5 | 2,894.6-5,372.9 | 2.65 | yes | `b200_sxm-x953-nvl72-hybrid` | 548.5 | 724.7-1,345.1 | 3.21 | yes | 3.299x | 3.994x | 1.211x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 2,513.2 | 1,175.9-2,182.6 | 9.06 | **no** | `b200_sxm-x142-nvl72-hybrid` | 548.5 | 747.7-1,387.9 | 3.11 | yes | 4.582x | 1.573x | 0.343x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,809.5 | 2,894.6-5,372.9 | 2.65 | yes | `b200_sxm-x953-nvl72-hybrid` | 548.5 | 724.7-1,345.1 | 3.21 | yes | 3.299x | 3.994x | 1.211x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 2,513.2 | 1,175.9-2,182.6 | 9.06 | **no** | `b200_sxm-x142-nvl72-hybrid` | 535.4 | 748.3-1,389.0 | 3.03 | yes | 4.694x | 1.571x | 0.335x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,809.5 | 2,894.6-5,372.9 | 2.65 | yes | `b200_sxm-x953-nvl72-hybrid` | 548.5 | 724.7-1,345.1 | 3.21 | yes | 3.299x | 3.994x | 1.211x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 2,513.2 | 1,175.9-2,182.6 | 9.06 | **no** | `b200_sxm-x142-nvl72-hybrid` | 535.2 | 755.7-1,402.7 | 3.00 | yes | 4.695x | 1.556x | 0.331x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,809.5 | 2,894.6-5,372.9 | 2.65 | yes | `b200_sxm-x953-nvl72-hybrid` | 543.1 | 693.0-1,286.4 | 3.32 | yes | 3.332x | 4.177x | 1.254x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 2,513.2 | 1,175.9-2,182.6 | 9.06 | **no** | `b200_sxm-x142-nvl72-hybrid` | 482.5 | 503.9-935.3 | 4.06 | yes | 5.209x | 2.334x | 0.448x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,809.5 | 2,894.6-5,372.9 | 2.65 | yes | `b200_sxm-x953-nvl72-hybrid` | 531.8 | 697.5-1,294.6 | 3.23 | yes | 3.403x | 4.150x | 1.220x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 2,479.0 | 910.0-1,689.1 | 11.55 | **no** | `b200_sxm-x142-nvl72-hybrid` | 428.3 | 503.2-933.9 | 3.61 | yes | 5.789x | 1.809x | 0.312x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,809.5 | 2,894.6-5,372.9 | 2.65 | yes | `b200_sxm-x953-nvl72-hybrid` | 525.7 | 767.1-1,423.9 | 2.91 | yes | 3.442x | 3.773x | 1.096x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 1,582.7 | 487.0-903.9 | 13.78 | **no** | `b200_sxm-x178-pipeline` | 320.0 | 336.6-624.7 | 4.03 | yes | 4.945x | 1.447x | 0.293x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,463.1 | 1,807.8-3,355.5 | 3.43 | yes | `b200_sxm-x953-nvl72-hybrid` | 473.6 | 744.1-1,381.1 | 2.70 | yes | 3.089x | 2.430x | 0.787x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 576.3 | 159.8-296.7 | 15.29 | **no** | `b200_sxm-x178-pipeline` | 160.8 | 167.5-310.9 | 4.07 | yes | 3.583x | 0.954x | 0.266x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 610.6 | 615.0-1,141.6 | 4.21 | yes | `b200_sxm-x953-pipeline` | 349.3 | 409.8-760.6 | 3.61 | yes | 1.748x | 1.501x | 0.859x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 144.5 | 49.3-91.5 | 12.43 | **no** | `b200_sxm-x178-pipeline` | 58.3 | 122.8-227.9 | 2.02 | yes | 2.477x | 0.402x | 0.162x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 175.2 | 89.5-166.1 | 8.30 | **no** | `b200_sxm-x953-pipeline` | 192.5 | 185.4-344.2 | 4.40 | yes | 0.910x | 0.482x | 0.530x |

**Does the ratio compress?** Of 20 class rows in this study, 14 move the ROM-versus-GPU ratio DOWN under speculation and 6 move it UP. The movement spans 0.162x to 1.254x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 9 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 3,478.9 | 2,913.4-5,407.7 | 5.06 | yes | `b200_sxm-x24-nvl72-tensor` | 607.0 | 1,604.1-2,977.4 | 1.60 | yes | 5.732x | 1.816x | 0.317x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3,172.0 | 3,076.3-5,710.0 | 4.37 | yes | `b200_sxm-x58-nvl72-tensor` | 619.0 | 1,728.8-3,208.8 | 1.52 | yes | 5.125x | 1.779x | 0.347x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 3,478.9 | 2,913.4-5,407.7 | 5.06 | yes | `b200_sxm-x24-hybrid` | 595.2 | 1,472.4-2,733.0 | 1.71 | yes | 5.845x | 1.979x | 0.339x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3,172.0 | 3,076.3-5,710.0 | 4.37 | yes | `b200_sxm-x58-nvl72-tensor` | 603.9 | 1,364.3-2,532.3 | 1.88 | yes | 5.253x | 2.255x | 0.429x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 3,478.9 | 2,913.4-5,407.7 | 5.06 | yes | `b200_sxm-x24-hybrid` | 585.9 | 1,296.6-2,406.8 | 1.92 | yes | 5.938x | 2.247x | 0.378x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3,172.0 | 3,076.3-5,710.0 | 4.37 | yes | `b200_sxm-x58-hybrid` | 583.3 | 1,449.0-2,689.5 | 1.71 | yes | 5.438x | 2.123x | 0.390x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 3,478.9 | 2,913.4-5,407.7 | 5.06 | yes | `b200_sxm-x24-hybrid` | 552.0 | 991.1-1,839.7 | 2.36 | yes | 6.303x | 2.940x | 0.466x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3,172.0 | 3,076.3-5,710.0 | 4.37 | yes | `b200_sxm-x58-hybrid` | 583.3 | 1,449.0-2,689.5 | 1.71 | yes | 5.438x | 2.123x | 0.390x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 3,461.4 | 2,882.7-5,350.7 | 5.09 | yes | `b200_sxm-x44-hybrid` | 540.4 | 977.4-1,814.1 | 2.34 | yes | 6.405x | 2.949x | 0.461x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3,172.0 | 3,076.3-5,710.0 | 4.37 | yes | `b200_sxm-x58-hybrid` | 554.6 | 1,100.2-2,042.1 | 2.14 | yes | 5.720x | 2.796x | 0.489x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,419.4 | 2,844.3-5,279.5 | 5.10 | yes | `b200_sxm-x173-nvl72-hybrid` | 573.4 | 1,337.9-2,483.3 | 1.82 | yes | 5.964x | 2.126x | 0.356x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 3,141.5 | 3,099.3-5,752.7 | 4.30 | yes | `b200_sxm-x116-nvl72-hybrid` | 557.9 | 1,160.0-2,153.1 | 2.04 | yes | 5.631x | 2.672x | 0.474x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,419.4 | 2,844.3-5,279.5 | 5.10 | yes | `b200_sxm-x173-nvl72-hybrid` | 537.4 | 1,024.3-1,901.2 | 2.22 | yes | 6.363x | 2.777x | 0.436x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,141.5 | 3,099.3-5,752.7 | 4.30 | yes | `b200_sxm-x231-nvl72-hybrid` | 551.7 | 1,147.7-2,130.3 | 2.04 | yes | 5.694x | 2.700x | 0.474x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 3,093.8 | 908.7-1,686.6 | 14.44 | **no** | `b200_sxm-x173-nvl72-hybrid` | 395.0 | 465.7-864.4 | 3.60 | yes | 7.833x | 1.951x | 0.249x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,121.4 | 1,842.6-3,420.0 | 7.18 | yes | `b200_sxm-x347-nvl72-hybrid` | 469.7 | 719.6-1,335.7 | 2.77 | yes | 6.645x | 2.560x | 0.385x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,636.9 | 430.1-798.4 | 16.14 | **no** | `b200_sxm-x173-nvl72-hybrid` | 222.1 | 259.3-481.3 | 3.63 | yes | 7.371x | 1.659x | 0.225x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,522.0 | 785.8-1,458.5 | 13.61 | **no** | `b200_sxm-x347-nvl72-hybrid` | 303.6 | 424.7-788.2 | 3.03 | yes | 8.306x | 1.850x | 0.223x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 503.9 | 127.5-236.7 | 16.75 | **no** | `b200_sxm-x173-nvl72-hybrid` | 115.4 | 86.4-160.4 | 5.66 | yes | 4.367x | 1.476x | 0.338x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,010.8 | 268.4-498.1 | 15.97 | **no** | `b200_sxm-x347-nvl72-hybrid` | 159.4 | 154.7-287.2 | 4.37 | yes | 6.339x | 1.734x | 0.274x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.223x to 0.489x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 15 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 3,485.7 | 3,032.0-5,627.8 | 4.87 | yes | `b200_sxm-x24-nvl72-tensor` | 607.1 | 1,729.7-3,210.5 | 1.49 | yes | 5.742x | 1.753x | 0.305x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,234.6 | 1,949.1-3,617.7 | 7.04 | yes | `b200_sxm-x231-nvl72-hybrid` | 615.9 | 1,692.1-3,140.7 | 1.54 | yes | 5.252x | 1.152x | 0.219x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 3,485.7 | 3,032.0-5,627.8 | 4.87 | yes | `b200_sxm-x24-hybrid` | 595.5 | 1,507.0-2,797.1 | 1.68 | yes | 5.854x | 2.012x | 0.344x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,234.6 | 1,949.1-3,617.7 | 7.04 | yes | `b200_sxm-x231-nvl72-hybrid` | 615.9 | 1,692.1-3,140.7 | 1.54 | yes | 5.252x | 1.152x | 0.219x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 3,485.7 | 3,032.0-5,627.8 | 4.87 | yes | `b200_sxm-x24-hybrid` | 586.2 | 1,388.0-2,576.4 | 1.79 | yes | 5.946x | 2.184x | 0.367x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,234.6 | 1,949.1-3,617.7 | 7.04 | yes | `b200_sxm-x231-nvl72-hybrid` | 615.9 | 1,692.1-3,140.7 | 1.54 | yes | 5.252x | 1.152x | 0.219x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 3,485.7 | 3,032.0-5,627.8 | 4.87 | yes | `b200_sxm-x24-hybrid` | 552.6 | 1,077.0-1,999.1 | 2.18 | yes | 6.308x | 2.815x | 0.446x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,234.6 | 1,949.1-3,617.7 | 7.04 | yes | `b200_sxm-x231-nvl72-hybrid` | 605.2 | 1,683.7-3,125.2 | 1.52 | yes | 5.344x | 1.158x | 0.217x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 3,468.2 | 2,994.6-5,558.4 | 4.91 | yes | `b200_sxm-x44-hybrid` | 541.0 | 1,060.8-1,969.1 | 2.16 | yes | 6.410x | 2.823x | 0.440x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,234.6 | 1,949.1-3,617.7 | 7.04 | yes | `b200_sxm-x231-nvl72-hybrid` | 591.0 | 1,363.0-2,529.9 | 1.84 | yes | 5.473x | 1.430x | 0.261x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,426.0 | 2,952.2-5,479.6 | 4.92 | yes | `b200_sxm-x173-nvl72-hybrid` | 573.7 | 1,440.9-2,674.5 | 1.69 | yes | 5.972x | 2.049x | 0.343x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,234.6 | 1,949.1-3,617.7 | 7.04 | yes | `b200_sxm-x231-nvl72-hybrid` | 580.6 | 1,568.8-2,911.9 | 1.57 | yes | 5.571x | 1.242x | 0.223x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,426.0 | 2,952.2-5,479.6 | 4.92 | yes | `b200_sxm-x173-nvl72-hybrid` | 538.0 | 1,123.0-2,084.4 | 2.03 | yes | 6.368x | 2.629x | 0.413x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,234.6 | 1,949.1-3,617.7 | 7.04 | yes | `b200_sxm-x231-nvl72-hybrid` | 552.2 | 1,248.2-2,316.9 | 1.88 | yes | 5.857x | 1.561x | 0.267x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 3,217.9 | 953.7-1,770.2 | 14.31 | **no** | `b200_sxm-x173-nvl72-hybrid` | 401.0 | 503.7-934.9 | 3.38 | yes | 8.024x | 1.893x | 0.236x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,234.2 | 1,946.7-3,613.2 | 7.04 | yes | `b200_sxm-x347-nvl72-hybrid` | 472.1 | 758.0-1,407.0 | 2.64 | yes | 6.851x | 2.568x | 0.375x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,751.7 | 461.7-857.1 | 16.08 | **no** | `b200_sxm-x173-nvl72-hybrid` | 229.8 | 174.3-323.4 | 5.59 | yes | 7.623x | 2.650x | 0.348x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,752.2 | 835.4-1,550.5 | 13.97 | **no** | `b200_sxm-x347-nvl72-hybrid` | 305.2 | 474.6-881.0 | 2.73 | yes | 9.018x | 1.760x | 0.195x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 548.1 | 138.9-257.9 | 16.73 | **no** | `b200_sxm-x173-nvl72-hybrid` | 120.8 | 96.8-179.7 | 5.29 | yes | 4.538x | 1.435x | 0.316x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,111.0 | 293.8-545.3 | 16.03 | **no** | `b200_sxm-x347-nvl72-hybrid` | 162.1 | 171.2-317.8 | 4.02 | yes | 6.852x | 1.716x | 0.250x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.195x to 0.446x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 15 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,823.8 | 698.0-1,295.6 | 11.08 | **no** | `b200_sxm-x157-nvl72-hybrid` | 409.5 | 846.9-1,572.0 | 2.05 | yes | 4.454x | 0.824x | 0.185x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 1,617.0 | 1,329.4-2,467.6 | 5.16 | yes | `b200_sxm-x116-nvl72-hybrid` | 411.6 | 853.0-1,583.3 | 2.05 | yes | 3.928x | 1.559x | 0.397x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,823.8 | 698.0-1,295.6 | 11.08 | **no** | `b200_sxm-x157-nvl72-hybrid` | 409.5 | 846.9-1,572.0 | 2.05 | yes | 4.454x | 0.824x | 0.185x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,557.3 | 1,353.1-2,511.5 | 4.88 | yes | `b200_sxm-x289-nvl72-hybrid` | 410.0 | 849.5-1,576.8 | 2.05 | yes | 3.799x | 1.593x | 0.419x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,823.8 | 698.0-1,295.6 | 11.08 | **no** | `b200_sxm-x157-nvl72-hybrid` | 400.8 | 727.8-1,350.8 | 2.34 | yes | 4.550x | 0.959x | 0.211x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,557.3 | 1,353.1-2,511.5 | 4.88 | yes | `b200_sxm-x289-nvl72-hybrid` | 410.0 | 849.5-1,576.8 | 2.05 | yes | 3.799x | 1.593x | 0.419x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,823.8 | 698.0-1,295.6 | 11.08 | **no** | `b200_sxm-x157-nvl72-hybrid` | 397.3 | 810.6-1,504.6 | 2.08 | yes | 4.591x | 0.861x | 0.188x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,557.3 | 1,353.1-2,511.5 | 4.88 | yes | `b200_sxm-x289-nvl72-hybrid` | 396.2 | 839.6-1,558.3 | 2.00 | yes | 3.930x | 1.612x | 0.410x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,823.8 | 698.0-1,295.6 | 11.08 | **no** | `b200_sxm-x157-nvl72-hybrid` | 377.8 | 632.5-1,174.0 | 2.53 | yes | 4.828x | 1.104x | 0.229x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,557.3 | 1,353.1-2,511.5 | 4.88 | yes | `b200_sxm-x289-nvl72-hybrid` | 393.2 | 815.3-1,513.4 | 2.04 | yes | 3.960x | 1.660x | 0.419x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,823.8 | 698.0-1,295.6 | 11.08 | **no** | `b200_sxm-x157-nvl72-hybrid` | 334.3 | 409.3-759.7 | 3.46 | yes | 5.455x | 1.705x | 0.313x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,557.3 | 1,353.1-2,511.5 | 4.88 | yes | `b200_sxm-x289-nvl72-hybrid` | 371.0 | 614.2-1,140.0 | 2.56 | yes | 4.198x | 2.203x | 0.525x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,823.8 | 698.0-1,295.6 | 11.08 | **no** | `b200_sxm-x157-nvl72-hybrid` | 281.9 | 362.9-673.6 | 3.29 | yes | 6.469x | 1.923x | 0.297x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,557.3 | 1,353.1-2,511.5 | 4.88 | yes | `b200_sxm-x289-nvl72-hybrid` | 326.0 | 391.8-727.3 | 3.53 | yes | 4.777x | 3.453x | 0.723x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,324.0 | 301.7-560.0 | 18.61 | **no** | `b200_sxm-x173-nvl72-hybrid` | 165.2 | 149.3-277.0 | 4.69 | yes | 8.013x | 2.021x | 0.252x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,314.2 | 625.6-1,161.3 | 8.91 | **no** | `b200_sxm-x347-nvl72-hybrid` | 227.4 | 242.5-450.0 | 3.98 | yes | 5.778x | 2.580x | 0.447x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 529.8 | 104.8-194.5 | 21.44 | **no** | `b200_sxm-x173-nvl72-hybrid` | 71.3 | 73.1-135.7 | 4.14 | yes | 7.430x | 1.433x | 0.193x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 670.2 | 168.9-313.6 | 16.82 | **no** | `b200_sxm-x347-nvl72-hybrid` | 113.2 | 121.5-225.6 | 3.95 | yes | 5.918x | 1.390x | 0.235x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 149.7 | 34.8-64.5 | 18.27 | **no** | `b200_sxm-x173-nvl72-hybrid` | 28.9 | 23.8-44.2 | 5.14 | yes | 5.183x | 1.459x | 0.282x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 198.7 | 70.7-131.2 | 11.92 | **no** | `b200_sxm-x347-nvl72-hybrid` | 44.2 | 41.9-77.8 | 4.47 | yes | 4.497x | 1.687x | 0.375x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.185x to 0.723x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,892.4 | 784.8-1,456.7 | 10.22 | **no** | `b200_sxm-x137-nvl72-hybrid` | 421.6 | 1,000.0-1,856.1 | 1.79 | yes | 4.489x | 0.785x | 0.175x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,733.1 | 884.1-1,641.0 | 8.31 | **no** | `b200_sxm-x144-nvl72-hybrid` | 422.2 | 1,031.2-1,914.0 | 1.74 | yes | 4.105x | 0.857x | 0.209x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,892.4 | 784.8-1,456.7 | 10.22 | **no** | `b200_sxm-x137-nvl72-hybrid` | 421.6 | 1,000.0-1,856.1 | 1.79 | yes | 4.489x | 0.785x | 0.175x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,733.1 | 884.1-1,641.0 | 8.31 | **no** | `b200_sxm-x144-nvl72-hybrid` | 422.2 | 1,031.2-1,914.0 | 1.74 | yes | 4.105x | 0.857x | 0.209x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,892.4 | 784.8-1,456.7 | 10.22 | **no** | `b200_sxm-x137-nvl72-hybrid` | 408.3 | 866.3-1,607.9 | 2.00 | yes | 4.635x | 0.906x | 0.195x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,733.1 | 884.1-1,641.0 | 8.31 | **no** | `b200_sxm-x144-nvl72-hybrid` | 409.4 | 870.5-1,615.8 | 1.99 | yes | 4.233x | 1.016x | 0.240x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,892.4 | 784.8-1,456.7 | 10.22 | **no** | `b200_sxm-x137-nvl72-hybrid` | 399.1 | 948.2-1,760.0 | 1.78 | yes | 4.742x | 0.828x | 0.175x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,733.1 | 884.1-1,641.0 | 8.31 | **no** | `b200_sxm-x144-nvl72-hybrid` | 402.0 | 961.5-1,784.6 | 1.77 | yes | 4.312x | 0.920x | 0.213x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,892.4 | 784.8-1,456.7 | 10.22 | **no** | `b200_sxm-x137-nvl72-hybrid` | 378.9 | 737.9-1,369.7 | 2.18 | yes | 4.994x | 1.064x | 0.213x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,733.1 | 884.1-1,641.0 | 8.31 | **no** | `b200_sxm-x144-nvl72-hybrid` | 382.2 | 748.5-1,389.3 | 2.17 | yes | 4.534x | 1.181x | 0.261x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,892.4 | 784.8-1,456.7 | 10.22 | **no** | `b200_sxm-x137-nvl72-hybrid` | 340.3 | 494.9-918.5 | 2.92 | yes | 5.561x | 1.586x | 0.285x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,733.1 | 884.1-1,641.0 | 8.31 | **no** | `b200_sxm-x144-nvl72-hybrid` | 344.1 | 501.5-930.9 | 2.91 | yes | 5.036x | 1.763x | 0.350x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,892.4 | 784.8-1,456.7 | 10.22 | **no** | `b200_sxm-x137-nvl72-hybrid` | 284.0 | 308.3-572.2 | 3.91 | yes | 6.664x | 2.546x | 0.382x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,733.1 | 884.1-1,641.0 | 8.31 | **no** | `b200_sxm-x144-nvl72-hybrid` | 288.3 | 312.2-579.4 | 3.92 | yes | 6.012x | 2.832x | 0.471x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,410.4 | 341.6-634.0 | 17.51 | **no** | `b200_sxm-x173-nvl72-hybrid` | 177.0 | 192.4-357.2 | 3.90 | yes | 7.968x | 1.775x | 0.223x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,614.8 | 468.1-868.9 | 14.63 | **no** | `b200_sxm-x347-nvl72-hybrid` | 237.1 | 300.9-558.5 | 3.34 | yes | 6.810x | 1.556x | 0.228x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 662.5 | 124.6-231.3 | 22.55 | **no** | `b200_sxm-x173-nvl72-hybrid` | 78.3 | 65.4-121.5 | 5.08 | yes | 8.457x | 1.904x | 0.225x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,012.3 | 197.1-365.9 | 21.77 | **no** | `b200_sxm-x347-nvl72-hybrid` | 119.1 | 112.3-208.5 | 4.50 | yes | 8.497x | 1.755x | 0.207x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 193.9 | 44.1-81.9 | 18.63 | **no** | `b200_sxm-x173-nvl72-hybrid` | 36.7 | 19.1-35.5 | 8.14 | **no** | 5.280x | 2.306x | 0.437x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 390.0 | 126.1-234.0 | 13.12 | **no** | `b200_sxm-x347-nvl72-hybrid` | 51.7 | 34.7-64.4 | 6.32 | yes | 7.539x | 3.633x | 0.482x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.175x to 0.482x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 0 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 1,967.4 | 1,298.9-2,411.0 | 6.42 | yes | `b200_sxm-x134-nvl72-hybrid` | 421.3 | 1,060.0-1,967.5 | 1.69 | yes | 4.670x | 1.225x | 0.262x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,815.1 | 906.8-1,683.2 | 8.49 | **no** | `b200_sxm-x144-nvl72-hybrid` | 422.3 | 1,035.4-1,921.8 | 1.73 | yes | 4.298x | 0.876x | 0.204x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 1,967.4 | 1,298.9-2,411.0 | 6.42 | yes | `b200_sxm-x134-nvl72-hybrid` | 421.3 | 1,060.0-1,967.5 | 1.69 | yes | 4.670x | 1.225x | 0.262x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,815.1 | 906.8-1,683.2 | 8.49 | **no** | `b200_sxm-x144-nvl72-hybrid` | 422.3 | 1,035.4-1,921.8 | 1.73 | yes | 4.298x | 0.876x | 0.204x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 1,967.4 | 1,298.9-2,411.0 | 6.42 | yes | `b200_sxm-x134-nvl72-hybrid` | 407.8 | 919.7-1,707.1 | 1.88 | yes | 4.824x | 1.412x | 0.293x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,815.1 | 906.8-1,683.2 | 8.49 | **no** | `b200_sxm-x144-nvl72-hybrid` | 409.4 | 926.8-1,720.2 | 1.87 | yes | 4.433x | 0.978x | 0.221x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 1,967.4 | 1,298.9-2,411.0 | 6.42 | yes | `b200_sxm-x134-nvl72-hybrid` | 397.8 | 965.2-1,791.6 | 1.75 | yes | 4.945x | 1.346x | 0.272x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,815.1 | 906.8-1,683.2 | 8.49 | **no** | `b200_sxm-x144-nvl72-hybrid` | 402.0 | 985.7-1,829.7 | 1.73 | yes | 4.515x | 0.920x | 0.204x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 1,967.4 | 1,298.9-2,411.0 | 6.42 | yes | `b200_sxm-x134-nvl72-hybrid` | 377.6 | 758.5-1,407.9 | 2.11 | yes | 5.210x | 1.712x | 0.329x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,815.1 | 906.8-1,683.2 | 8.49 | **no** | `b200_sxm-x144-nvl72-hybrid` | 382.4 | 774.9-1,438.4 | 2.09 | yes | 4.747x | 1.170x | 0.247x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 1,967.4 | 1,298.9-2,411.0 | 6.42 | yes | `b200_sxm-x134-nvl72-hybrid` | 338.8 | 528.8-981.5 | 2.72 | yes | 5.807x | 2.456x | 0.423x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,815.1 | 906.8-1,683.2 | 8.49 | **no** | `b200_sxm-x144-nvl72-hybrid` | 344.3 | 540.0-1,002.3 | 2.70 | yes | 5.271x | 1.679x | 0.319x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,957.5 | 801.1-1,487.0 | 10.36 | **no** | `b200_sxm-x157-nvl72-hybrid` | 296.3 | 366.2-679.8 | 3.43 | yes | 6.605x | 2.187x | 0.331x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,815.1 | 906.8-1,683.2 | 8.49 | **no** | `b200_sxm-x144-nvl72-hybrid` | 288.6 | 339.8-630.8 | 3.60 | yes | 6.290x | 2.668x | 0.424x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,470.0 | 447.6-830.8 | 13.92 | **no** | `b200_sxm-x173-nvl72-hybrid` | 177.4 | 208.0-386.0 | 3.62 | yes | 8.286x | 2.152x | 0.260x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,697.9 | 754.2-1,399.9 | 9.54 | **no** | `b200_sxm-x347-nvl72-hybrid` | 237.5 | 301.1-558.9 | 3.34 | yes | 7.150x | 2.505x | 0.350x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 688.0 | 128.2-237.9 | 22.76 | **no** | `b200_sxm-x173-nvl72-hybrid` | 78.6 | 72.5-134.6 | 4.60 | yes | 8.748x | 1.767x | 0.202x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,046.7 | 202.3-375.4 | 21.94 | **no** | `b200_sxm-x347-nvl72-hybrid` | 119.5 | 122.7-227.8 | 4.13 | yes | 8.760x | 1.648x | 0.188x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 202.7 | 45.9-85.3 | 18.71 | **no** | `b200_sxm-x173-nvl72-hybrid` | 38.3 | 21.0-38.9 | 7.74 | yes | 5.298x | 2.193x | 0.414x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 404.7 | 124.6-231.2 | 13.78 | **no** | `b200_sxm-x347-nvl72-hybrid` | 52.1 | 37.6-69.8 | 5.87 | yes | 7.769x | 3.312x | 0.426x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.188x to 0.426x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 6 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x152` | 2,753.2 | 1,027.1-1,906.4 | 11.37 | **no** | `a100_sxm_80gb-x150-hybrid` | 286.1 | 279.8-519.3 | 4.34 | yes | 9.622x | 3.671x | 0.382x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 2,674.3 | 1,783.0-3,309.5 | 6.36 | yes | `a100_sxm_80gb-x168-hybrid` | 286.5 | 280.2-520.2 | 4.33 | yes | 9.334x | 6.362x | 0.682x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,374.0 | 1,183.7-2,197.0 | 8.50 | **no** | `a100_sxm_80gb-x387-hybrid` | 279.8 | 275.4-511.2 | 4.31 | yes | 8.486x | 4.298x | 0.506x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,445.1 | 1,015.7-1,885.2 | 6.03 | yes | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 279.3-518.5 | 4.26 | yes | 5.151x | 3.636x | 0.706x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,374.0 | 1,183.7-2,197.0 | 8.50 | **no** | `a100_sxm_80gb-x387-hybrid` | 279.8 | 275.4-511.2 | 4.31 | yes | 8.486x | 4.298x | 0.506x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,445.1 | 1,015.7-1,885.2 | 6.03 | yes | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 279.3-518.5 | 4.26 | yes | 5.151x | 3.636x | 0.706x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,374.0 | 1,183.7-2,197.0 | 8.50 | **no** | `a100_sxm_80gb-x387-hybrid` | 279.8 | 275.4-511.2 | 4.31 | yes | 8.486x | 4.298x | 0.506x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,445.1 | 1,015.7-1,885.2 | 6.03 | yes | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 279.3-518.5 | 4.26 | yes | 5.151x | 3.636x | 0.706x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,374.0 | 1,183.7-2,197.0 | 8.50 | **no** | `a100_sxm_80gb-x387-hybrid` | 279.8 | 275.4-511.2 | 4.31 | yes | 8.486x | 4.298x | 0.506x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,445.1 | 1,015.7-1,885.2 | 6.03 | yes | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 279.3-518.5 | 4.26 | yes | 5.151x | 3.636x | 0.706x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,317.2 | 958.7-1,779.4 | 10.25 | **no** | `a100_sxm_80gb-x387-hybrid` | 279.8 | 275.4-511.2 | 4.31 | yes | 8.283x | 3.481x | 0.420x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,445.1 | 1,015.7-1,885.2 | 6.03 | yes | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 279.3-518.5 | 4.26 | yes | 5.151x | 3.636x | 0.706x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,135.8 | 676.2-1,255.1 | 13.39 | **no** | `a100_sxm_80gb-x387-hybrid` | 259.3 | 222.0-412.0 | 4.95 | yes | 8.236x | 3.046x | 0.370x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,445.1 | 1,015.7-1,885.2 | 6.03 | yes | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 279.3-518.5 | 4.26 | yes | 5.151x | 3.636x | 0.706x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,191.4 | 312.2-579.5 | 16.18 | **no** | `a100_sxm_80gb-x387-hybrid` | 161.4 | 119.4-221.6 | 5.73 | yes | 7.379x | 2.615x | 0.354x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,058.3 | 550.3-1,021.4 | 8.15 | **no** | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 279.3-518.5 | 4.26 | yes | 3.772x | 1.970x | 0.522x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 359.9 | 115.2-213.7 | 13.25 | **no** | `a100_sxm_80gb-x387-hybrid` | 77.9 | 59.7-110.8 | 5.53 | yes | 4.622x | 1.929x | 0.417x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 384.3 | 149.9-278.2 | 10.87 | **no** | `a100_sxm_80gb-x2574-hybrid` | 200.3 | 189.6-351.9 | 4.48 | yes | 1.919x | 0.791x | 0.412x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 93.6 | 41.7-77.3 | 9.53 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 103.2 | 37.8-70.2 | 11.57 | **no** | `a100_sxm_80gb-x2574-hybrid` | 106.2 | 96.9-179.8 | 4.65 | yes | 0.972x | 0.390x | 0.402x |

**Does the ratio compress?** Of 19 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.354x to 0.706x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,431.3 | 2,253.7-4,183.2 | 6.46 | yes | `a100_sxm_80gb-x73-hybrid` | 337.6 | 628.7-1,167.0 | 2.28 | yes | 10.164x | 3.584x | 0.353x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 2,917.0 | 2,112.4-3,920.8 | 5.86 | yes | `a100_sxm_80gb-x112-hybrid` | 344.2 | 661.6-1,228.0 | 2.21 | yes | 8.475x | 3.193x | 0.377x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,431.3 | 2,253.7-4,183.2 | 6.46 | yes | `a100_sxm_80gb-x73-hybrid` | 337.6 | 628.7-1,167.0 | 2.28 | yes | 10.164x | 3.584x | 0.353x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 2,917.0 | 2,112.4-3,920.8 | 5.86 | yes | `a100_sxm_80gb-x112-hybrid` | 344.2 | 661.6-1,228.0 | 2.21 | yes | 8.475x | 3.193x | 0.377x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,431.3 | 2,253.7-4,183.2 | 6.46 | yes | `a100_sxm_80gb-x73-hybrid` | 337.6 | 628.7-1,167.0 | 2.28 | yes | 10.164x | 3.584x | 0.353x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 2,917.0 | 2,112.4-3,920.8 | 5.86 | yes | `a100_sxm_80gb-x112-hybrid` | 344.2 | 661.6-1,228.0 | 2.21 | yes | 8.475x | 3.193x | 0.377x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,431.3 | 2,253.7-4,183.2 | 6.46 | yes | `a100_sxm_80gb-x73-hybrid` | 337.6 | 628.7-1,167.0 | 2.28 | yes | 10.164x | 3.584x | 0.353x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 2,917.0 | 2,112.4-3,920.8 | 5.86 | yes | `a100_sxm_80gb-x112-hybrid` | 344.2 | 661.6-1,228.0 | 2.21 | yes | 8.475x | 3.193x | 0.377x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,431.3 | 2,253.7-4,183.2 | 6.46 | yes | `a100_sxm_80gb-x73-hybrid` | 316.4 | 508.9-944.7 | 2.64 | yes | 10.846x | 4.428x | 0.408x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 2,917.0 | 2,112.4-3,920.8 | 5.86 | yes | `a100_sxm_80gb-x112-hybrid` | 338.9 | 622.7-1,155.9 | 2.31 | yes | 8.607x | 3.392x | 0.394x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 3,390.4 | 2,258.6-4,192.2 | 6.36 | yes | `a100_sxm_80gb-x146-hybrid` | 314.6 | 503.4-934.3 | 2.65 | yes | 10.776x | 4.487x | 0.416x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 2,891.2 | 2,413.0-4,478.8 | 5.08 | yes | `a100_sxm_80gb-x224-hybrid` | 333.3 | 610.8-1,133.8 | 2.31 | yes | 8.674x | 3.950x | 0.455x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,378.5 | 2,247.9-4,172.3 | 6.37 | yes | `a100_sxm_80gb-x335-hybrid` | 313.9 | 500.7-929.4 | 2.66 | yes | 10.764x | 4.489x | 0.417x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,891.2 | 2,413.0-4,478.8 | 5.08 | yes | `a100_sxm_80gb-x448-hybrid` | 327.6 | 597.1-1,108.2 | 2.33 | yes | 8.827x | 4.041x | 0.458x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,833.9 | 987.8-1,833.5 | 12.16 | **no** | `a100_sxm_80gb-x335-hybrid` | 211.0 | 199.0-369.4 | 4.49 | yes | 13.433x | 4.963x | 0.369x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,675.7 | 1,375.7-2,553.5 | 8.25 | **no** | `a100_sxm_80gb-x672-hybrid` | 269.0 | 329.6-611.8 | 3.46 | yes | 9.948x | 4.174x | 0.420x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,292.9 | 317.3-588.9 | 17.28 | **no** | `a100_sxm_80gb-x335-hybrid` | 106.5 | 118.4-219.7 | 3.82 | yes | 12.136x | 2.681x | 0.221x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,739.9 | 572.9-1,063.4 | 12.88 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.0 | 199.5-370.3 | 3.30 | yes | 11.223x | 2.872x | 0.256x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 378.8 | 94.0-174.4 | 17.09 | **no** | `a100_sxm_80gb-x335-hybrid` | 45.8 | 32.4-60.2 | 5.99 | yes | 8.263x | 2.896x | 0.350x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 566.3 | 194.5-361.1 | 12.34 | **no** | `a100_sxm_80gb-x672-hybrid` | 69.3 | 63.9-118.6 | 4.60 | yes | 8.174x | 3.044x | 0.372x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.221x to 0.458x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 14 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 3,440.9 | 2,389.1-4,434.6 | 6.11 | yes | `a100_sxm_80gb-x67-hybrid` | 341.4 | 654.1-1,214.0 | 2.21 | yes | 10.078x | 3.653x | 0.362x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3,133.6 | 2,520.6-4,678.5 | 5.27 | yes | `a100_sxm_80gb-x112-hybrid` | 345.9 | 685.2-1,271.9 | 2.14 | yes | 9.059x | 3.678x | 0.406x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 3,440.9 | 2,389.1-4,434.6 | 6.11 | yes | `a100_sxm_80gb-x67-hybrid` | 341.4 | 654.1-1,214.0 | 2.21 | yes | 10.078x | 3.653x | 0.362x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3,133.6 | 2,520.6-4,678.5 | 5.27 | yes | `a100_sxm_80gb-x112-hybrid` | 345.9 | 685.2-1,271.9 | 2.14 | yes | 9.059x | 3.678x | 0.406x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 3,440.9 | 2,389.1-4,434.6 | 6.11 | yes | `a100_sxm_80gb-x67-hybrid` | 341.4 | 654.1-1,214.0 | 2.21 | yes | 10.078x | 3.653x | 0.362x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3,133.6 | 2,520.6-4,678.5 | 5.27 | yes | `a100_sxm_80gb-x112-hybrid` | 345.9 | 685.2-1,271.9 | 2.14 | yes | 9.059x | 3.678x | 0.406x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 3,440.9 | 2,389.1-4,434.6 | 6.11 | yes | `a100_sxm_80gb-x67-hybrid` | 341.4 | 654.1-1,214.0 | 2.21 | yes | 10.078x | 3.653x | 0.362x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3,133.6 | 2,520.6-4,678.5 | 5.27 | yes | `a100_sxm_80gb-x112-hybrid` | 345.9 | 685.2-1,271.9 | 2.14 | yes | 9.059x | 3.678x | 0.406x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 3,440.9 | 2,389.1-4,434.6 | 6.11 | yes | `a100_sxm_80gb-x67-hybrid` | 315.0 | 498.0-924.3 | 2.68 | yes | 10.924x | 4.798x | 0.439x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3,133.6 | 2,520.6-4,678.5 | 5.27 | yes | `a100_sxm_80gb-x112-hybrid` | 340.8 | 646.8-1,200.5 | 2.23 | yes | 9.195x | 3.897x | 0.424x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 3,402.5 | 2,352.3-4,366.1 | 6.13 | yes | `a100_sxm_80gb-x146-hybrid` | 316.9 | 513.1-952.3 | 2.62 | yes | 10.738x | 4.585x | 0.427x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 3,105.4 | 2,548.4-4,730.2 | 5.17 | yes | `a100_sxm_80gb-x224-hybrid` | 335.2 | 633.9-1,176.6 | 2.24 | yes | 9.265x | 4.020x | 0.434x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,390.5 | 2,340.6-4,344.5 | 6.14 | yes | `a100_sxm_80gb-x335-hybrid` | 316.0 | 521.5-967.9 | 2.57 | yes | 10.728x | 4.489x | 0.418x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,105.4 | 2,548.4-4,730.2 | 5.17 | yes | `a100_sxm_80gb-x448-hybrid` | 329.3 | 619.1-1,149.1 | 2.26 | yes | 9.430x | 4.116x | 0.437x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,971.8 | 1,042.0-1,934.0 | 12.09 | **no** | `a100_sxm_80gb-x335-hybrid` | 214.1 | 209.3-388.5 | 4.34 | yes | 13.881x | 4.979x | 0.359x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,064.1 | 1,455.4-2,701.4 | 8.93 | **no** | `a100_sxm_80gb-x672-hybrid` | 271.7 | 341.0-633.0 | 3.38 | yes | 11.276x | 4.268x | 0.378x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,387.9 | 340.1-631.3 | 17.30 | **no** | `a100_sxm_80gb-x335-hybrid` | 107.3 | 129.9-241.2 | 3.50 | yes | 12.933x | 2.618x | 0.202x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,330.5 | 607.8-1,128.2 | 16.26 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.9 | 216.7-402.2 | 3.05 | yes | 14.953x | 2.805x | 0.188x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 412.3 | 102.2-189.7 | 17.10 | **no** | `a100_sxm_80gb-x335-hybrid` | 46.4 | 36.7-68.2 | 5.36 | yes | 8.881x | 2.781x | 0.313x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 843.4 | 212.2-393.9 | 16.85 | **no** | `a100_sxm_80gb-x672-hybrid` | 69.9 | 72.2-134.1 | 4.10 | yes | 12.059x | 2.937x | 0.244x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.188x to 0.439x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 14 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,734.0 | 1,214.9-2,254.9 | 6.05 | yes | `a100_sxm_80gb-x391-hybrid` | 166.4 | 244.3-453.5 | 2.89 | yes | 10.418x | 4.972x | 0.477x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 1,564.9 | 1,036.9-1,924.6 | 6.40 | yes | `a100_sxm_80gb-x336-hybrid` | 167.5 | 245.8-456.2 | 2.89 | yes | 9.344x | 4.219x | 0.452x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,734.0 | 1,214.9-2,254.9 | 6.05 | yes | `a100_sxm_80gb-x391-hybrid` | 166.4 | 244.3-453.5 | 2.89 | yes | 10.418x | 4.972x | 0.477x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,350.3 | 1,259.6-2,337.9 | 4.55 | yes | `a100_sxm_80gb-x783-hybrid` | 165.1 | 247.1-458.6 | 2.83 | yes | 8.178x | 5.098x | 0.623x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,734.0 | 1,214.9-2,254.9 | 6.05 | yes | `a100_sxm_80gb-x391-hybrid` | 166.4 | 244.3-453.5 | 2.89 | yes | 10.418x | 4.972x | 0.477x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,350.3 | 1,259.6-2,337.9 | 4.55 | yes | `a100_sxm_80gb-x783-hybrid` | 165.1 | 247.1-458.6 | 2.83 | yes | 8.178x | 5.098x | 0.623x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,734.0 | 1,214.9-2,254.9 | 6.05 | yes | `a100_sxm_80gb-x391-hybrid` | 166.4 | 244.3-453.5 | 2.89 | yes | 10.418x | 4.972x | 0.477x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,350.3 | 1,259.6-2,337.9 | 4.55 | yes | `a100_sxm_80gb-x783-hybrid` | 165.1 | 247.1-458.6 | 2.83 | yes | 8.178x | 5.098x | 0.623x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,734.0 | 1,214.9-2,254.9 | 6.05 | yes | `a100_sxm_80gb-x391-hybrid` | 166.4 | 244.3-453.5 | 2.89 | yes | 10.418x | 4.972x | 0.477x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,350.3 | 1,259.6-2,337.9 | 4.55 | yes | `a100_sxm_80gb-x783-hybrid` | 165.1 | 247.1-458.6 | 2.83 | yes | 8.178x | 5.098x | 0.623x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,731.6 | 859.6-1,595.5 | 8.54 | **no** | `a100_sxm_80gb-x391-hybrid` | 166.4 | 244.3-453.5 | 2.89 | yes | 10.404x | 3.518x | 0.338x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,350.3 | 1,259.6-2,337.9 | 4.55 | yes | `a100_sxm_80gb-x783-hybrid` | 165.1 | 247.1-458.6 | 2.83 | yes | 8.178x | 5.098x | 0.623x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,666.7 | 527.5-979.0 | 13.40 | **no** | `a100_sxm_80gb-x391-hybrid` | 156.9 | 208.4-386.8 | 3.19 | yes | 10.621x | 2.531x | 0.238x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,313.4 | 759.7-1,410.1 | 7.33 | yes | `a100_sxm_80gb-x783-hybrid` | 165.1 | 247.1-458.6 | 2.83 | yes | 7.955x | 3.075x | 0.387x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,119.1 | 242.3-449.8 | 19.58 | **no** | `a100_sxm_80gb-x391-hybrid` | 89.7 | 74.2-137.8 | 5.12 | yes | 12.471x | 3.264x | 0.262x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 961.1 | 388.0-720.1 | 10.50 | **no** | `a100_sxm_80gb-x783-hybrid` | 123.8 | 125.0-232.0 | 4.20 | yes | 7.762x | 3.104x | 0.400x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 404.3 | 80.6-149.7 | 21.26 | **no** | `a100_sxm_80gb-x391-hybrid` | 36.2 | 37.7-69.9 | 4.08 | yes | 11.162x | 2.142x | 0.192x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 364.1 | 101.4-188.2 | 15.23 | **no** | `a100_sxm_80gb-x783-hybrid` | 57.4 | 62.5-116.0 | 3.90 | yes | 6.343x | 1.623x | 0.256x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 110.7 | 25.8-47.9 | 18.17 | **no** | `a100_sxm_80gb-x391-hybrid` | 13.1 | 10.6-19.6 | 5.26 | yes | 8.430x | 2.440x | 0.289x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 98.9 | 56.6-105.1 | 7.41 | yes | `a100_sxm_80gb-x783-hybrid` | 21.8 | 20.6-38.3 | 4.49 | yes | 4.537x | 2.746x | 0.605x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.192x to 0.623x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 13 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 1,862.0 | 1,458.1-2,706.5 | 5.41 | yes | `a100_sxm_80gb-x368-hybrid` | 167.8 | 290.7-539.5 | 2.45 | yes | 11.099x | 5.017x | 0.452x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,632.1 | 1,141.5-2,118.7 | 6.06 | yes | `a100_sxm_80gb-x336-hybrid` | 168.3 | 291.5-541.0 | 2.45 | yes | 9.700x | 3.916x | 0.404x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 1,862.0 | 1,458.1-2,706.5 | 5.41 | yes | `a100_sxm_80gb-x368-hybrid` | 167.8 | 290.7-539.5 | 2.45 | yes | 11.099x | 5.017x | 0.452x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,632.1 | 1,141.5-2,118.7 | 6.06 | yes | `a100_sxm_80gb-x336-hybrid` | 168.3 | 291.5-541.0 | 2.45 | yes | 9.700x | 3.916x | 0.404x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 1,862.0 | 1,458.1-2,706.5 | 5.41 | yes | `a100_sxm_80gb-x368-hybrid` | 167.8 | 290.7-539.5 | 2.45 | yes | 11.099x | 5.017x | 0.452x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,632.1 | 1,141.5-2,118.7 | 6.06 | yes | `a100_sxm_80gb-x336-hybrid` | 168.3 | 291.5-541.0 | 2.45 | yes | 9.700x | 3.916x | 0.404x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 1,862.0 | 1,458.1-2,706.5 | 5.41 | yes | `a100_sxm_80gb-x368-hybrid` | 167.8 | 290.7-539.5 | 2.45 | yes | 11.099x | 5.017x | 0.452x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,632.1 | 1,141.5-2,118.7 | 6.06 | yes | `a100_sxm_80gb-x336-hybrid` | 168.3 | 291.5-541.0 | 2.45 | yes | 9.700x | 3.916x | 0.404x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 1,862.0 | 1,458.1-2,706.5 | 5.41 | yes | `a100_sxm_80gb-x368-hybrid` | 167.8 | 290.7-539.5 | 2.45 | yes | 11.099x | 5.017x | 0.452x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,632.1 | 1,141.5-2,118.7 | 6.06 | yes | `a100_sxm_80gb-x336-hybrid` | 168.3 | 291.5-541.0 | 2.45 | yes | 9.700x | 3.916x | 0.404x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 1,849.5 | 1,001.1-1,858.2 | 7.83 | yes | `a100_sxm_80gb-x368-hybrid` | 167.8 | 290.7-539.5 | 2.45 | yes | 11.024x | 3.444x | 0.312x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,632.1 | 1,141.5-2,118.7 | 6.06 | yes | `a100_sxm_80gb-x336-hybrid` | 168.3 | 291.5-541.0 | 2.45 | yes | 9.700x | 3.916x | 0.404x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,796.0 | 586.7-1,088.9 | 12.98 | **no** | `a100_sxm_80gb-x391-hybrid` | 158.0 | 244.7-454.2 | 2.74 | yes | 11.367x | 2.397x | 0.211x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1,624.3 | 654.6-1,215.1 | 10.52 | **no** | `a100_sxm_80gb-x448-hybrid` | 162.1 | 264.6-491.0 | 2.60 | yes | 10.020x | 2.475x | 0.247x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,301.5 | 275.4-511.2 | 20.04 | **no** | `a100_sxm_80gb-x391-hybrid` | 93.6 | 94.1-174.7 | 4.22 | yes | 13.900x | 2.927x | 0.211x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,466.9 | 538.2-999.0 | 11.56 | **no** | `a100_sxm_80gb-x672-hybrid` | 119.3 | 134.7-250.0 | 3.75 | yes | 12.301x | 3.997x | 0.325x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 506.1 | 96.1-178.4 | 22.32 | **no** | `a100_sxm_80gb-x391-hybrid` | 37.4 | 30.4-56.4 | 5.22 | yes | 13.522x | 3.164x | 0.234x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 847.5 | 240.9-447.2 | 14.92 | **no** | `a100_sxm_80gb-x672-hybrid` | 54.2 | 45.6-84.7 | 5.03 | yes | 15.645x | 5.277x | 0.337x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 142.2 | 32.6-60.5 | 18.50 | **no** | `a100_sxm_80gb-x391-hybrid` | 14.3 | 7.7-14.3 | 7.91 | **no** | 9.917x | 4.242x | 0.428x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 331.3 | 77.3-143.5 | 18.17 | **no** | `a100_sxm_80gb-x672-hybrid` | 20.0 | 25.2-46.8 | 3.36 | yes | 16.566x | 3.066x | 0.185x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.185x to 0.452x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 12 of 20 ROM rows and 19 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 1,936.6 | 1,022.8-1,898.4 | 8.03 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 289.0-536.5 | 2.44 | yes | 11.640x | 3.538x | 0.304x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,717.0 | 1,200.7-2,228.6 | 6.06 | yes | `a100_sxm_80gb-x336-hybrid` | 168.4 | 292.9-543.7 | 2.44 | yes | 10.198x | 4.099x | 0.402x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 1,936.6 | 1,022.8-1,898.4 | 8.03 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 289.0-536.5 | 2.44 | yes | 11.640x | 3.538x | 0.304x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,717.0 | 1,200.7-2,228.6 | 6.06 | yes | `a100_sxm_80gb-x336-hybrid` | 168.4 | 292.9-543.7 | 2.44 | yes | 10.198x | 4.099x | 0.402x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 1,936.6 | 1,022.8-1,898.4 | 8.03 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 289.0-536.5 | 2.44 | yes | 11.640x | 3.538x | 0.304x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,717.0 | 1,200.7-2,228.6 | 6.06 | yes | `a100_sxm_80gb-x336-hybrid` | 168.4 | 292.9-543.7 | 2.44 | yes | 10.198x | 4.099x | 0.402x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 1,936.6 | 1,022.8-1,898.4 | 8.03 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 289.0-536.5 | 2.44 | yes | 11.640x | 3.538x | 0.304x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,717.0 | 1,200.7-2,228.6 | 6.06 | yes | `a100_sxm_80gb-x336-hybrid` | 168.4 | 292.9-543.7 | 2.44 | yes | 10.198x | 4.099x | 0.402x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 1,936.6 | 1,022.8-1,898.4 | 8.03 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 289.0-536.5 | 2.44 | yes | 11.640x | 3.538x | 0.304x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,717.0 | 1,200.7-2,228.6 | 6.06 | yes | `a100_sxm_80gb-x336-hybrid` | 168.4 | 292.9-543.7 | 2.44 | yes | 10.198x | 4.099x | 0.402x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 1,936.6 | 1,022.8-1,898.4 | 8.03 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 289.0-536.5 | 2.44 | yes | 11.640x | 3.538x | 0.304x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,717.0 | 1,200.7-2,228.6 | 6.06 | yes | `a100_sxm_80gb-x336-hybrid` | 168.4 | 292.9-543.7 | 2.44 | yes | 10.198x | 4.099x | 0.402x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,870.2 | 603.1-1,119.5 | 13.15 | **no** | `a100_sxm_80gb-x391-hybrid` | 158.1 | 247.1-458.7 | 2.71 | yes | 11.827x | 2.440x | 0.206x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1,716.4 | 669.9-1,243.3 | 10.86 | **no** | `a100_sxm_80gb-x448-hybrid` | 162.2 | 267.1-495.7 | 2.58 | yes | 10.580x | 2.508x | 0.237x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,334.2 | 281.1-521.7 | 20.13 | **no** | `a100_sxm_80gb-x391-hybrid` | 93.8 | 97.6-181.1 | 4.08 | yes | 14.221x | 2.881x | 0.203x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,541.0 | 557.0-1,033.8 | 11.73 | **no** | `a100_sxm_80gb-x672-hybrid` | 119.4 | 138.5-257.1 | 3.66 | yes | 12.903x | 4.021x | 0.312x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 525.7 | 98.9-183.6 | 22.53 | **no** | `a100_sxm_80gb-x391-hybrid` | 37.5 | 31.8-59.1 | 5.00 | yes | 14.003x | 3.107x | 0.222x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 873.0 | 249.9-463.8 | 14.81 | **no** | `a100_sxm_80gb-x672-hybrid` | 54.3 | 47.6-88.3 | 4.84 | yes | 16.072x | 5.253x | 0.327x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 148.5 | 33.9-63.0 | 18.57 | **no** | `a100_sxm_80gb-x391-hybrid` | 14.4 | 8.3-15.3 | 7.40 | yes | 10.308x | 4.106x | 0.398x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 359.7 | 89.9-166.9 | 16.96 | **no** | `a100_sxm_80gb-x672-hybrid` | 20.1 | 26.7-49.5 | 3.19 | yes | 17.918x | 3.374x | 0.188x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.188x to 0.402x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 6 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 10,793.3 | 9,224.0-17,121.0 | 4.96 | yes | `b200_sxm-x8-tensor` | 943.8 | 3,349.0-6,216.3 | 1.19 | yes | 11.436x | 2.754x | 0.241x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 5,080.9 | 9,815.7-18,219.2 | 2.19 | yes | `b200_sxm-x58-nvl72-tensor` | 1,268.9 | 4,477.9-8,311.5 | 1.20 | yes | 4.004x | 2.192x | 0.547x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 9,880.7 | 8,630.8-16,020.0 | 4.85 | yes | `b200_sxm-x32-nvl72-tensor` | 1,202.3 | 4,063.7-7,542.9 | 1.25 | yes | 8.218x | 2.124x | 0.258x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 4,545.7 | 9,873.1-18,325.8 | 1.95 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,258.3 | 4,414.2-8,193.3 | 1.21 | yes | 3.613x | 2.237x | 0.619x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 9,880.7 | 8,630.8-16,020.0 | 4.85 | yes | `b200_sxm-x32-nvl72-tensor` | 1,178.6 | 3,676.1-6,823.4 | 1.36 | yes | 8.383x | 2.348x | 0.280x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 4,545.7 | 9,873.1-18,325.8 | 1.95 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,255.0 | 4,324.8-8,027.4 | 1.23 | yes | 3.622x | 2.283x | 0.630x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 9,796.1 | 8,565.4-15,898.6 | 4.85 | yes | `b200_sxm-x87-nvl72-hybrid` | 1,207.9 | 3,705.1-6,877.2 | 1.38 | yes | 8.110x | 2.312x | 0.285x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 4,545.7 | 9,873.1-18,325.8 | 1.95 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,242.3 | 4,000.8-7,426.0 | 1.32 | yes | 3.659x | 2.468x | 0.674x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9,672.8 | 8,477.6-15,735.5 | 4.84 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,217.5 | 3,479.5-6,458.3 | 1.48 | yes | 7.945x | 2.436x | 0.307x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,521.9 | 9,817.9-18,223.3 | 1.95 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,242.6 | 3,831.2-7,111.1 | 1.38 | yes | 3.639x | 2.563x | 0.704x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8,789.7 | 6,257.3-11,614.4 | 5.96 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,170.8 | 2,759.3-5,121.6 | 1.80 | yes | 7.507x | 2.268x | 0.302x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,937.8 | 8,528.9-15,830.8 | 1.96 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,214.0 | 3,221.6-5,979.8 | 1.60 | yes | 3.244x | 2.647x | 0.816x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7,163.6 | 4,253.3-7,894.7 | 7.14 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,087.4 | 1,944.3-3,608.8 | 2.37 | yes | 6.588x | 2.188x | 0.332x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,112.9 | 6,212.0-11,530.3 | 2.12 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,160.5 | 2,441.3-4,531.5 | 2.02 | yes | 2.682x | 2.545x | 0.949x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,148.4 | 1,396.6-2,592.3 | 9.56 | **no** | `b200_sxm-x173-nvl72-hybrid` | 811.6 | 1,153.3-2,140.7 | 2.98 | yes | 3.879x | 1.211x | 0.312x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,209.8 | 2,766.1-5,134.3 | 1.85 | yes | `b200_sxm-x347-nvl72-hybrid` | 951.5 | 1,601.6-2,972.8 | 2.52 | yes | 1.271x | 1.727x | 1.358x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 801.0 | 345.8-641.9 | 9.82 | **no** | `b200_sxm-x173-nvl72-hybrid` | 439.4 | 552.9-1,026.2 | 3.37 | yes | 1.823x | 0.626x | 0.343x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 330.9 | 822.0-1,525.7 | 1.71 | yes | `b200_sxm-x347-nvl72-hybrid` | 613.1 | 882.0-1,637.0 | 2.95 | yes | 0.540x | 0.932x | 1.727x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 201.1 | 84.2-156.3 | 10.13 | **no** | `b200_sxm-x173-nvl72-hybrid` | 166.6 | 241.3-448.0 | 2.93 | yes | 1.207x | 0.349x | 0.289x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 84.0 | 203.7-378.0 | 1.75 | yes | `b200_sxm-x347-nvl72-hybrid` | 280.0 | 435.2-807.8 | 2.73 | yes | 0.300x | 0.468x | 1.560x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 3,374.2 | 2,492.7-4,626.7 | 5.74 | yes | `b200_sxm-x29-nvl72-tensor` | 599.7 | 1,390.6-2,581.2 | 1.83 | yes | 5.626x | 1.792x | 0.319x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 2,899.9 | 2,092.6-3,884.1 | 5.88 | yes | `b200_sxm-x58-nvl72-tensor` | 607.7 | 1,409.7-2,616.5 | 1.83 | yes | 4.772x | 1.484x | 0.311x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 3,373.9 | 2,403.8-4,461.7 | 5.95 | yes | `b200_sxm-x31-hybrid` | 585.0 | 1,244.7-2,310.3 | 1.99 | yes | 5.767x | 1.931x | 0.335x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2,543.0 | 3,342.3-6,203.8 | 3.23 | yes | `b200_sxm-x231-nvl72-hybrid` | 603.8 | 1,391.9-2,583.5 | 1.84 | yes | 4.212x | 2.401x | 0.570x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 3,373.9 | 2,403.8-4,461.7 | 5.95 | yes | `b200_sxm-x31-hybrid` | 585.0 | 1,244.7-2,310.3 | 1.99 | yes | 5.767x | 1.931x | 0.335x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2,543.0 | 3,342.3-6,203.8 | 3.23 | yes | `b200_sxm-x231-nvl72-hybrid` | 603.8 | 1,391.9-2,583.5 | 1.84 | yes | 4.212x | 2.401x | 0.570x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 3,373.9 | 2,403.8-4,461.7 | 5.95 | yes | `b200_sxm-x31-hybrid` | 547.7 | 906.1-1,681.8 | 2.56 | yes | 6.160x | 2.653x | 0.431x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2,543.0 | 3,342.3-6,203.8 | 3.23 | yes | `b200_sxm-x231-nvl72-hybrid` | 594.1 | 1,390.3-2,580.6 | 1.81 | yes | 4.280x | 2.404x | 0.562x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x70` | 3,362.0 | 2,327.9-4,320.8 | 6.12 | yes | `b200_sxm-x36-hybrid` | 501.7 | 679.5-1,261.3 | 3.13 | yes | 6.702x | 3.426x | 0.511x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2,543.0 | 3,342.3-6,203.8 | 3.23 | yes | `b200_sxm-x231-nvl72-hybrid` | 576.4 | 1,321.1-2,452.2 | 1.85 | yes | 4.412x | 2.530x | 0.573x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 3,253.3 | 2,276.5-4,225.4 | 6.06 | yes | `b200_sxm-x86-nvl72-hybrid` | 517.7 | 770.9-1,430.9 | 2.85 | yes | 6.284x | 2.953x | 0.470x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2,543.0 | 3,342.3-6,203.8 | 3.23 | yes | `b200_sxm-x231-nvl72-hybrid` | 572.4 | 1,268.4-2,354.3 | 1.91 | yes | 4.443x | 2.635x | 0.593x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,251.5 | 2,274.6-4,222.0 | 6.06 | yes | `b200_sxm-x173-nvl72-hybrid` | 513.7 | 775.9-1,440.2 | 2.81 | yes | 6.330x | 2.932x | 0.463x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,541.0 | 3,333.5-6,187.4 | 3.23 | yes | `b200_sxm-x347-nvl72-hybrid` | 552.7 | 1,117.3-2,073.9 | 2.10 | yes | 4.597x | 2.983x | 0.649x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,536.0 | 964.9-1,791.0 | 11.14 | **no** | `b200_sxm-x173-nvl72-hybrid` | 364.6 | 464.0-861.3 | 3.33 | yes | 6.956x | 2.079x | 0.299x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,071.6 | 1,751.4-3,250.9 | 5.01 | yes | `b200_sxm-x347-nvl72-hybrid` | 442.1 | 720.3-1,337.0 | 2.60 | yes | 4.686x | 2.431x | 0.519x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,134.8 | 294.3-546.3 | 16.35 | **no** | `b200_sxm-x173-nvl72-hybrid` | 197.9 | 282.4-524.2 | 2.97 | yes | 5.735x | 1.042x | 0.182x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,018.1 | 561.8-1,042.7 | 7.68 | yes | `b200_sxm-x347-nvl72-hybrid` | 275.2 | 285.2-529.4 | 4.09 | yes | 3.700x | 1.970x | 0.532x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 344.7 | 113.1-210.0 | 12.92 | **no** | `b200_sxm-x173-nvl72-hybrid` | 87.7 | 107.0-198.6 | 3.47 | yes | 3.932x | 1.057x | 0.269x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 295.8 | 173.1-321.2 | 7.25 | yes | `b200_sxm-x347-nvl72-hybrid` | 132.3 | 182.5-338.7 | 3.07 | yes | 2.236x | 0.949x | 0.424x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,491.0 | 466.7-866.3 | 13.54 | **no** | `b200_sxm-x203-nvl72-hybrid` | 378.3 | 472.5-877.0 | 3.39 | yes | 3.942x | 0.988x | 0.251x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 1,539.2 | 974.2-1,808.3 | 6.70 | yes | `b200_sxm-x173-nvl72-hybrid` | 376.7 | 472.7-877.3 | 3.38 | yes | 4.086x | 2.061x | 0.504x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,491.0 | 466.7-866.3 | 13.54 | **no** | `b200_sxm-x203-nvl72-hybrid` | 378.3 | 472.5-877.0 | 3.39 | yes | 3.942x | 0.988x | 0.251x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,156.1 | 1,443.3-2,678.9 | 3.40 | yes | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 457.1-848.4 | 3.45 | yes | 3.110x | 3.157x | 1.015x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,491.0 | 466.7-866.3 | 13.54 | **no** | `b200_sxm-x203-nvl72-hybrid` | 374.4 | 470.0-872.3 | 3.38 | yes | 3.982x | 0.993x | 0.249x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,156.1 | 1,443.3-2,678.9 | 3.40 | yes | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 457.1-848.4 | 3.45 | yes | 3.110x | 3.157x | 1.015x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,491.0 | 466.7-866.3 | 13.54 | **no** | `b200_sxm-x203-nvl72-hybrid` | 363.9 | 469.2-870.9 | 3.29 | yes | 4.098x | 0.995x | 0.243x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,156.1 | 1,443.3-2,678.9 | 3.40 | yes | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 457.1-848.4 | 3.45 | yes | 3.110x | 3.157x | 1.015x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,491.0 | 466.7-866.3 | 13.54 | **no** | `b200_sxm-x203-nvl72-hybrid` | 350.8 | 404.0-749.8 | 3.68 | yes | 4.250x | 1.155x | 0.272x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,156.1 | 1,443.3-2,678.9 | 3.40 | yes | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 457.1-848.4 | 3.45 | yes | 3.110x | 3.157x | 1.015x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,491.0 | 466.7-866.3 | 13.54 | **no** | `b200_sxm-x203-nvl72-hybrid` | 310.8 | 382.0-709.0 | 3.45 | yes | 4.798x | 1.222x | 0.255x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,156.1 | 1,443.3-2,678.9 | 3.40 | yes | `b200_sxm-x1358-nvl72-hybrid` | 356.5 | 456.6-847.6 | 3.31 | yes | 3.243x | 3.161x | 0.975x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,491.0 | 466.7-866.3 | 13.54 | **no** | `b200_sxm-x203-nvl72-hybrid` | 257.2 | 226.7-420.8 | 4.81 | yes | 5.798x | 2.059x | 0.355x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,156.1 | 1,443.3-2,678.9 | 3.40 | yes | `b200_sxm-x1358-nvl72-hybrid` | 354.1 | 465.1-863.2 | 3.23 | yes | 3.265x | 3.103x | 0.951x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 959.9 | 211.6-392.7 | 19.24 | **no** | `b200_sxm-x203-nvl72-hybrid` | 148.6 | 122.5-227.4 | 5.14 | yes | 6.462x | 1.727x | 0.267x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,038.8 | 502.9-933.5 | 8.76 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 293.7 | 344.4-639.3 | 3.62 | yes | 3.537x | 1.460x | 0.413x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 339.9 | 69.8-129.6 | 20.64 | **no** | `b200_sxm-x203-nvl72-hybrid` | 64.8 | 61.8-114.7 | 4.45 | yes | 5.242x | 1.130x | 0.216x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 551.7 | 140.6-261.0 | 16.64 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 189.8 | 195.5-362.8 | 4.12 | yes | 2.907x | 0.719x | 0.247x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 92.1 | 21.7-40.3 | 18.00 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 168.6 | 35.7-66.3 | 20.01 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 92.1 | 73.1-135.6 | 5.34 | yes | 1.831x | 0.489x | 0.267x |

**Does the ratio compress?** Of 59 class rows in this study, 52 move the ROM-versus-GPU ratio DOWN under speculation and 7 move it UP. The movement spans 0.182x to 1.727x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 41 of 60 ROM rows and 59 of 60 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 10,491.8 | 8,157.0-15,140.5 | 5.45 | yes | `a100_sxm_80gb-x16-hybrid` | 458.7 | 1,580.4-2,933.4 | 1.23 | yes | 22.873x | 5.161x | 0.226x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 5,099.4 | 9,058.2-16,813.3 | 2.39 | yes | `a100_sxm_80gb-x112-tensor` | 562.5 | 1,093.5-2,029.7 | 2.18 | yes | 9.066x | 8.284x | 0.914x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8,068.9 | 8,206.0-15,231.4 | 4.17 | yes | `a100_sxm_80gb-x272-tensor` | 544.1 | 714.4-1,326.1 | 3.23 | yes | 14.830x | 11.486x | 0.774x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,585.9 | 9,096.9-16,885.0 | 1.67 | yes | `a100_sxm_80gb-x448-hybrid` | 539.0 | 1,083.6-2,011.3 | 2.11 | yes | 6.653x | 8.395x | 1.262x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8,068.9 | 8,206.0-15,231.4 | 4.17 | yes | `a100_sxm_80gb-x272-hybrid` | 532.5 | 1,079.4-2,003.5 | 2.09 | yes | 15.153x | 7.603x | 0.502x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,585.9 | 9,096.9-16,885.0 | 1.67 | yes | `a100_sxm_80gb-x448-hybrid` | 539.0 | 1,083.6-2,011.3 | 2.11 | yes | 6.653x | 8.395x | 1.262x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8,068.9 | 8,206.0-15,231.4 | 4.17 | yes | `a100_sxm_80gb-x272-hybrid` | 514.3 | 836.2-1,552.1 | 2.61 | yes | 15.690x | 9.814x | 0.625x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,585.9 | 9,096.9-16,885.0 | 1.67 | yes | `a100_sxm_80gb-x448-hybrid` | 534.5 | 1,012.8-1,879.9 | 2.24 | yes | 6.709x | 8.982x | 1.339x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 7,701.6 | 7,148.0-13,267.6 | 4.57 | yes | `a100_sxm_80gb-x272-hybrid` | 474.5 | 809.2-1,502.0 | 2.49 | yes | 16.233x | 8.833x | 0.544x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,199.3 | 8,374.4-15,543.9 | 1.62 | yes | `a100_sxm_80gb-x672-hybrid` | 520.1 | 876.3-1,626.6 | 2.52 | yes | 6.152x | 9.556x | 1.553x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,264.9 | 4,993.2-9,268.0 | 5.32 | yes | `a100_sxm_80gb-x335-hybrid` | 447.1 | 587.7-1,090.9 | 3.23 | yes | 14.013x | 8.496x | 0.606x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,555.8 | 6,385.7-11,852.7 | 1.70 | yes | `a100_sxm_80gb-x672-hybrid` | 479.6 | 553.4-1,027.2 | 3.67 | yes | 5.329x | 11.538x | 2.165x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,574.0 | 3,359.6-6,235.9 | 5.77 | yes | `a100_sxm_80gb-x335-hybrid` | 430.7 | 1,318.5-2,447.3 | 1.39 | yes | 10.619x | 2.548x | 0.240x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,700.4 | 4,714.1-8,750.0 | 1.53 | yes | `a100_sxm_80gb-x672-hybrid` | 442.4 | 1,424.2-2,643.4 | 1.32 | yes | 3.843x | 3.310x | 0.861x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,597.0 | 1,040.4-1,931.2 | 6.51 | yes | `a100_sxm_80gb-x335-hybrid` | 354.0 | 802.1-1,488.8 | 1.87 | yes | 4.511x | 1.297x | 0.288x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 526.4 | 1,766.3-3,278.5 | 1.26 | yes | `a100_sxm_80gb-x672-hybrid` | 402.4 | 1,089.3-2,022.0 | 1.57 | yes | 1.308x | 1.621x | 1.240x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 431.2 | 266.0-493.8 | 6.87 | yes | `a100_sxm_80gb-x335-hybrid` | 206.7 | 265.5-492.9 | 3.30 | yes | 2.086x | 1.002x | 0.480x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 136.6 | 491.3-911.9 | 1.18 | yes | `a100_sxm_80gb-x672-hybrid` | 286.6 | 496.1-920.8 | 2.45 | yes | 0.477x | 0.990x | 2.078x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 111.0 | 128.8-239.0 | 3.65 | yes | `a100_sxm_80gb-x335-hybrid` | 77.9 | 114.3-212.2 | 2.89 | yes | 1.425x | 1.127x | 0.791x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 34.4 | 72.7-134.9 | 2.00 | yes | `a100_sxm_80gb-x672-hybrid` | 133.3 | 137.9-255.9 | 4.10 | yes | 0.258x | 0.527x | 2.044x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x79` | 3,263.9 | 2,571.1-4,772.3 | 5.38 | yes | `a100_sxm_80gb-x78-hybrid` | 332.4 | 527.4-979.0 | 2.67 | yes | 9.819x | 4.875x | 0.496x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 2,899.9 | 1,853.7-3,440.7 | 6.63 | yes | `a100_sxm_80gb-x112-hybrid` | 333.1 | 535.8-994.5 | 2.64 | yes | 8.707x | 3.460x | 0.397x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,233.0 | 2,481.4-4,605.9 | 5.52 | yes | `a100_sxm_80gb-x85-hybrid` | 331.3 | 526.8-977.7 | 2.67 | yes | 9.760x | 4.711x | 0.483x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 2,141.3 | 1,924.6-3,572.3 | 4.72 | yes | `a100_sxm_80gb-x560-hybrid` | 322.7 | 525.8-976.0 | 2.60 | yes | 6.636x | 3.660x | 0.552x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,233.0 | 2,481.4-4,605.9 | 5.52 | yes | `a100_sxm_80gb-x85-hybrid` | 331.3 | 526.8-977.7 | 2.67 | yes | 9.760x | 4.711x | 0.483x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 2,141.3 | 1,924.6-3,572.3 | 4.72 | yes | `a100_sxm_80gb-x560-hybrid` | 322.7 | 525.8-976.0 | 2.60 | yes | 6.636x | 3.660x | 0.552x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,233.0 | 2,481.4-4,605.9 | 5.52 | yes | `a100_sxm_80gb-x85-hybrid` | 331.3 | 526.8-977.7 | 2.67 | yes | 9.760x | 4.711x | 0.483x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 2,141.3 | 1,924.6-3,572.3 | 4.72 | yes | `a100_sxm_80gb-x560-hybrid` | 322.7 | 525.8-976.0 | 2.60 | yes | 6.636x | 3.660x | 0.552x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,212.2 | 1,811.3-3,362.0 | 7.52 | yes | `a100_sxm_80gb-x85-hybrid` | 311.7 | 426.5-791.6 | 3.10 | yes | 10.306x | 4.247x | 0.412x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 2,141.3 | 1,924.6-3,572.3 | 4.72 | yes | `a100_sxm_80gb-x560-hybrid` | 322.7 | 525.8-976.0 | 2.60 | yes | 6.636x | 3.660x | 0.552x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 3,127.9 | 2,406.6-4,467.0 | 5.51 | yes | `a100_sxm_80gb-x312-hybrid` | 324.1 | 519.9-965.0 | 2.64 | yes | 9.653x | 4.629x | 0.480x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 2,141.3 | 1,924.6-3,572.3 | 4.72 | yes | `a100_sxm_80gb-x560-hybrid` | 322.7 | 525.8-976.0 | 2.60 | yes | 6.636x | 3.660x | 0.552x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 3,082.3 | 1,765.9-3,277.7 | 7.40 | yes | `a100_sxm_80gb-x312-hybrid` | 296.6 | 378.4-702.5 | 3.32 | yes | 10.391x | 4.666x | 0.449x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 2,081.0 | 1,189.9-2,208.7 | 7.41 | yes | `a100_sxm_80gb-x560-hybrid` | 322.7 | 525.8-976.0 | 2.60 | yes | 6.449x | 2.263x | 0.351x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,198.9 | 729.0-1,353.1 | 12.79 | **no** | `a100_sxm_80gb-x335-hybrid` | 195.1 | 233.0-432.5 | 3.55 | yes | 11.272x | 3.128x | 0.278x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,360.1 | 535.5-994.0 | 10.77 | **no** | `a100_sxm_80gb-x672-hybrid` | 249.1 | 243.0-451.1 | 4.35 | yes | 5.459x | 2.203x | 0.404x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 884.5 | 218.8-406.1 | 17.14 | **no** | `a100_sxm_80gb-x335-hybrid` | 95.1 | 77.3-143.6 | 5.21 | yes | 9.301x | 2.829x | 0.304x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 477.9 | 414.5-769.4 | 4.89 | yes | `a100_sxm_80gb-x672-hybrid` | 143.1 | 146.9-272.7 | 4.13 | yes | 3.339x | 2.821x | 0.845x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 314.0 | 88.0-163.3 | 15.13 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.6 | 37.5-69.7 | 4.25 | yes | 8.348x | 2.344x | 0.281x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 128.2 | 101.5-188.5 | 5.35 | yes | `a100_sxm_80gb-x672-hybrid` | 60.1 | 71.9-133.4 | 3.54 | yes | 2.133x | 1.413x | 0.662x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 1,397.4 | 700.6-1,300.4 | 8.46 | **no** | `a100_sxm_80gb-x384-hybrid` | 149.5 | 152.9-283.8 | 4.14 | yes | 9.350x | 4.582x | 0.490x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 1,451.0 | 743.5-1,380.0 | 8.28 | **no** | `a100_sxm_80gb-x504-hybrid` | 148.2 | 151.7-281.5 | 4.14 | yes | 9.790x | 4.902x | 0.501x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 950.4 | 692.5-1,285.4 | 5.82 | yes | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 160.4-297.8 | 3.92 | yes | 6.414x | 4.316x | 0.673x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 950.4 | 692.5-1,285.4 | 5.82 | yes | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 160.4-297.8 | 3.92 | yes | 6.414x | 4.316x | 0.673x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 950.4 | 692.5-1,285.4 | 5.82 | yes | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 160.4-297.8 | 3.92 | yes | 6.414x | 4.316x | 0.673x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 950.4 | 692.5-1,285.4 | 5.82 | yes | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 160.4-297.8 | 3.92 | yes | 6.414x | 4.316x | 0.673x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 950.4 | 692.5-1,285.4 | 5.82 | yes | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 160.4-297.8 | 3.92 | yes | 6.414x | 4.316x | 0.673x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 950.4 | 692.5-1,285.4 | 5.82 | yes | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 160.4-297.8 | 3.92 | yes | 6.414x | 4.316x | 0.673x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 832.3 | 391.0-725.7 | 9.03 | **no** | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 160.4-297.8 | 3.92 | yes | 5.617x | 2.437x | 0.434x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 354.3 | 104.8-194.5 | 14.34 | **no** | `a100_sxm_80gb-x3694-hybrid` | 109.3 | 81.2-150.7 | 5.71 | yes | 3.242x | 1.291x | 0.398x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 100.3 | 26.4-49.1 | 16.08 | **no** | `a100_sxm_80gb-x3694-hybrid` | 53.1 | 41.4-76.8 | 5.45 | yes | 1.887x | 0.639x | 0.339x |

**Does the ratio compress?** Of 51 class rows in this study, 43 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.226x to 2.165x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 42 of 51 ROM rows and 51 of 51 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 12,166.3 | 7,554.2-14,021.5 | 6.83 | yes | `b200_sxm-x2-tensor` | 872.0 | 3,166.2-5,877.0 | 1.17 | yes | 13.952x | 2.386x | 0.171x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-hybrid-x2-romfill` | 5,002.6 | 11,321.3-21,013.8 | 1.87 | yes | `b200_sxm-x58-nvl72-tensor` | 1,318.4 | 4,653.7-8,637.9 | 1.20 | yes | 3.794x | 2.433x | 0.641x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 9,598.9 | 10,618.1-19,708.6 | 3.83 | yes | `b200_sxm-x32-nvl72-tensor` | 1,285.1 | 4,333.1-8,042.7 | 1.26 | yes | 7.469x | 2.450x | 0.328x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 4,482.5 | 10,652.9-19,773.3 | 1.78 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,307.2 | 4,586.0-8,512.2 | 1.21 | yes | 3.429x | 2.323x | 0.677x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 9,598.9 | 10,618.1-19,708.6 | 3.83 | yes | `b200_sxm-x32-nvl72-tensor` | 1,258.1 | 3,895.1-7,229.9 | 1.37 | yes | 7.630x | 2.726x | 0.357x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 4,482.5 | 10,652.9-19,773.3 | 1.78 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,303.7 | 4,489.6-8,333.3 | 1.23 | yes | 3.438x | 2.373x | 0.690x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x170-romfill` | 9,518.8 | 10,526.4-19,538.5 | 3.83 | yes | `b200_sxm-x87-nvl72-hybrid` | 1,268.3 | 3,866.3-7,176.4 | 1.39 | yes | 7.505x | 2.723x | 0.363x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 4,482.5 | 10,652.9-19,773.3 | 1.78 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,289.9 | 4,141.4-7,687.0 | 1.32 | yes | 3.475x | 2.572x | 0.740x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 9,402.4 | 10,394.1-19,292.8 | 3.84 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,263.3 | 3,585.3-6,654.9 | 1.49 | yes | 7.443x | 2.899x | 0.390x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 4,459.3 | 10,588.7-19,654.0 | 1.79 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,282.0 | 3,937.5-7,308.6 | 1.38 | yes | 3.479x | 2.689x | 0.773x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 8,579.9 | 9,037.7-16,775.2 | 4.03 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,214.9 | 3,488.1-6,474.3 | 1.48 | yes | 7.062x | 2.591x | 0.367x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,878.2 | 9,732.1-18,064.1 | 1.69 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,251.5 | 3,296.5-6,118.8 | 1.61 | yes | 3.099x | 2.952x | 0.953x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 6,926.4 | 6,840.3-12,696.5 | 4.29 | yes | `b200_sxm-x173-nvl72-hybrid` | 1,145.4 | 2,734.0-5,074.6 | 1.78 | yes | 6.047x | 2.502x | 0.414x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,053.5 | 7,235.6-13,430.2 | 1.79 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,199.0 | 3,242.8-6,019.1 | 1.57 | yes | 2.547x | 2.231x | 0.876x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3,281.0 | 2,894.5-5,372.6 | 4.81 | yes | `b200_sxm-x173-nvl72-hybrid` | 877.5 | 1,701.4-3,158.1 | 2.19 | yes | 3.739x | 1.701x | 0.455x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,199.2 | 3,711.7-6,889.4 | 1.37 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,010.0 | 2,302.3-4,273.3 | 1.86 | yes | 1.187x | 1.612x | 1.358x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 832.2 | 724.0-1,343.8 | 4.87 | yes | `b200_sxm-x173-nvl72-hybrid` | 480.0 | 905.5-1,680.8 | 2.25 | yes | 1.734x | 0.800x | 0.461x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 330.8 | 1,196.5-2,220.8 | 1.17 | yes | `b200_sxm-x347-nvl72-hybrid` | 671.6 | 1,430.1-2,654.4 | 1.99 | yes | 0.493x | 0.837x | 1.699x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 208.3 | 180.9-335.8 | 4.88 | yes | `b200_sxm-x173-nvl72-hybrid` | 179.0 | 412.5-765.6 | 1.84 | yes | 1.164x | 0.439x | 0.377x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 83.9 | 208.6-387.2 | 1.70 | yes | `b200_sxm-x347-nvl72-hybrid` | 306.9 | 746.1-1,384.9 | 1.74 | yes | 0.273x | 0.280x | 1.023x |

**Does the ratio compress?** Of 20 class rows in this study, 17 move the ROM-versus-GPU ratio DOWN under speculation and 3 move it UP. The movement spans 0.171x to 1.699x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 20 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x8-romfill` | 11,712.7 | 9,297.5-17,257.5 | 5.34 | yes | `a100_sxm_80gb-x8-tensor` | 749.4 | 2,563.2-4,757.6 | 1.24 | yes | 15.630x | 3.627x | 0.232x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-hybrid-x2-romfill` | 5,014.9 | 11,088.8-20,582.2 | 1.92 | yes | `a100_sxm_80gb-x112-hybrid` | 731.5 | 2,396.8-4,448.8 | 1.29 | yes | 6.856x | 4.626x | 0.675x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,874.5 | 9,624.5-17,864.4 | 3.47 | yes | `a100_sxm_80gb-x272-hybrid` | 707.1 | 2,183.1-4,052.2 | 1.37 | yes | 11.137x | 4.409x | 0.396x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 3,553.8 | 9,222.7-17,118.6 | 1.63 | yes | `a100_sxm_80gb-x448-hybrid` | 704.7 | 2,163.9-4,016.4 | 1.38 | yes | 5.043x | 4.262x | 0.845x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,874.5 | 9,624.5-17,864.4 | 3.47 | yes | `a100_sxm_80gb-x272-hybrid` | 707.1 | 2,183.1-4,052.2 | 1.37 | yes | 11.137x | 4.409x | 0.396x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 3,553.8 | 9,222.7-17,118.6 | 1.63 | yes | `a100_sxm_80gb-x448-hybrid` | 704.7 | 2,163.9-4,016.4 | 1.38 | yes | 5.043x | 4.262x | 0.845x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,874.5 | 9,624.5-17,864.4 | 3.47 | yes | `a100_sxm_80gb-x272-hybrid` | 707.1 | 2,183.1-4,052.2 | 1.37 | yes | 11.137x | 4.409x | 0.396x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 3,553.8 | 9,222.7-17,118.6 | 1.63 | yes | `a100_sxm_80gb-x448-hybrid` | 704.7 | 2,163.9-4,016.4 | 1.38 | yes | 5.043x | 4.262x | 0.845x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,510.6 | 9,640.6-17,894.2 | 3.30 | yes | `a100_sxm_80gb-x272-hybrid` | 707.1 | 2,183.1-4,052.2 | 1.37 | yes | 10.622x | 4.416x | 0.416x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,163.6 | 8,566.4-15,900.4 | 1.57 | yes | `a100_sxm_80gb-x672-hybrid` | 704.7 | 2,163.9-4,016.4 | 1.38 | yes | 4.489x | 3.959x | 0.882x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 6,021.8 | 6,966.2-12,930.1 | 3.67 | yes | `a100_sxm_80gb-x335-hybrid` | 704.1 | 2,162.3-4,013.6 | 1.38 | yes | 8.552x | 3.222x | 0.377x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 2,525.5 | 6,575.5-12,204.9 | 1.63 | yes | `a100_sxm_80gb-x672-hybrid` | 704.7 | 2,163.9-4,016.4 | 1.38 | yes | 3.584x | 3.039x | 0.848x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4,434.2 | 5,511.8-10,230.6 | 3.41 | yes | `a100_sxm_80gb-x335-hybrid` | 676.7 | 1,929.2-3,580.8 | 1.49 | yes | 6.553x | 2.857x | 0.436x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,680.2 | 4,921.6-9,135.2 | 1.45 | yes | `a100_sxm_80gb-x672-hybrid` | 704.7 | 2,163.9-4,016.4 | 1.38 | yes | 2.384x | 2.274x | 0.954x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 1,589.6 | 2,301.1-4,271.2 | 2.93 | yes | `a100_sxm_80gb-x335-hybrid` | 504.8 | 874.2-1,622.6 | 2.45 | yes | 3.149x | 2.632x | 0.836x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 524.5 | 1,889.1-3,506.5 | 1.18 | yes | `a100_sxm_80gb-x672-hybrid` | 608.4 | 1,415.7-2,627.7 | 1.82 | yes | 0.862x | 1.334x | 1.548x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 430.2 | 633.8-1,176.4 | 2.88 | yes | `a100_sxm_80gb-x335-hybrid` | 250.4 | 265.5-492.9 | 4.00 | yes | 1.718x | 2.387x | 1.389x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 136.6 | 533.1-989.6 | 1.09 | yes | `a100_sxm_80gb-x672-hybrid` | 377.7 | 496.1-920.8 | 3.23 | yes | 0.362x | 1.075x | 2.971x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340` | 111.0 | 214.4-397.9 | 2.19 | yes | `a100_sxm_80gb-x335-hybrid` | 89.7 | 114.3-212.2 | 3.33 | yes | 1.237x | 1.875x | 1.515x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12` | 34.4 | 72.7-134.9 | 2.00 | yes | `a100_sxm_80gb-x672-hybrid` | 156.9 | 222.2-412.4 | 3.00 | yes | 0.219x | 0.327x | 1.494x |

**Does the ratio compress?** Of 20 class rows in this study, 15 move the ROM-versus-GPU ratio DOWN under speculation and 5 move it UP. The movement spans 0.232x to 2.971x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 20 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

## Where the drafter lives on a ROM machine

The locality rule -- `stored/peak` is a technology constant -- is the load-bearing assumption of the whole ROM verdict. A pass that reads only the drafter's region uses only that region's read ports and takes exactly as long as sweeping the entire array. Two placements are therefore priced side by side, and the second is an architectural proposal this study **has not costed in silicon area**.

The same rule is what makes a SEQUENTIAL draft step expensive here. A per-position operation that moves only a small table is nearly free on a global-bandwidth store and costs a full array sweep on this one, so a drafter with `gamma` sequential applications pays `gamma` sweeps for them. That term is charged in full below; on a bandwidth store the bytes it moves are not separately charged at all, because this repository's model configs carry no size for the table -- an omission whose size, on DeepSeek-V4-Pro-0813, is the externally published 132,382,720 B per draft token, 0.33% of the 39,666,603,980 B target pass.

| study | model | ctx | batch | class | design | tau* draft in ROM | tau* draft in KV store | KV placement feasible | why not |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5.61 | 16.44 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 12.31 | 326.65 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5.61 | 16.44 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 12.31 | 326.65 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5.61 | 16.44 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 12.31 | 326.65 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 5.61 | 16.44 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 12.31 | 326.65 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 8.33 | 29.98 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 12.31 | 326.65 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 8.38 | 29.38 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 12.31 | 326.65 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 14.43 | 55.71 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 11.94 | 319.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 19.06 | 50.21 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 25.32 | 587.32 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 23.70 | 54.40 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 37.31 | 729.69 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 26.93 | 44.45 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 14.11 | 65.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 6.77 | 37.01 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 9.24 | 385.63 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 6.77 | 37.01 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 9.24 | 385.63 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 6.77 | 37.01 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 9.24 | 385.63 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 6.77 | 37.01 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 9.24 | 385.63 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 6.77 | 37.01 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 9.24 | 385.63 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 10.54 | 68.47 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 9.11 | 375.42 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 18.69 | 131.52 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 10.08 | 372.52 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 29.67 | 197.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 19.37 | 643.82 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 32.28 | 163.97 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 40.25 | 1,385.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 27.77 | 57.77 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 18.97 | 259.10 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 6.25 | 16.71 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 8.56 | 147.24 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 6.25 | 16.71 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 8.56 | 147.24 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 6.25 | 16.71 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 8.56 | 147.24 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 6.25 | 16.71 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 8.56 | 147.24 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 6.05 | 16.79 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 8.56 | 147.24 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 8.81 | 29.17 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 8.56 | 147.24 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 11.01 | 28.90 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.89 | 144.19 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 20.27 | 48.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 17.17 | 226.88 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 31.52 | 79.00 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 31.12 | 428.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 26.21 | 34.88 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 16.29 | 127.41 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 7.64 | 35.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 14.35 | 164.93 | NO | the KV store has no room for it |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 7.64 | 35.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 5.05 | 153.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 7.64 | 35.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 5.05 | 153.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 7.64 | 35.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 5.05 | 153.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 7.64 | 35.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 5.05 | 153.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 11.71 | 65.16 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.00 | 148.81 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 13.51 | 62.96 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 11.84 | 290.57 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 32.14 | 166.18 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 15.04 | 364.65 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 32.35 | 119.54 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 19.85 | 495.23 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 27.20 | 44.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 8.53 | 133.26 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 7.67 | 29.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 11.58 | 343.76 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 7.67 | 29.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 11.58 | 343.76 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 7.67 | 29.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 11.58 | 343.76 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 7.67 | 29.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 11.58 | 343.76 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 7.67 | 29.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 11.58 | 343.76 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 13.34 | 57.44 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 11.58 | 343.76 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 15.46 | 57.70 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 21.54 | 680.65 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 28.81 | 96.97 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 24.96 | 649.09 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 23.08 | 55.54 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 37.75 | 824.58 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 27.29 | 47.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 29.95 | 273.99 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 7.10 | 36.26 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 15.65 | 801.22 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 7.10 | 36.26 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 15.65 | 801.22 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 7.10 | 36.26 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 15.65 | 801.22 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 7.10 | 36.26 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 15.65 | 801.22 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 6.46 | 36.99 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 15.65 | 801.22 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 10.11 | 68.45 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 15.65 | 801.22 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 18.16 | 133.97 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 17.46 | 783.53 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 20.87 | 110.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 31.02 | 1,429.47 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 32.26 | 182.45 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 40.90 | 1,569.86 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 28.04 | 63.68 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 19.22 | 156.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5.07 | 3.54 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x10-romfill` | 7.97 | 4.32 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5.07 | 3.54 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 7.59 | 8.34 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5.07 | 3.54 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 7.59 | 8.34 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5.07 | 3.54 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 7.59 | 8.34 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 5.20 | 3.71 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 7.59 | 8.34 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5.21 | 3.78 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 7.01 | 8.76 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8.13 | 5.33 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 7.01 | 8.76 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 15.75 | 10.86 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 11.95 | 15.30 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 19.56 | 15.50 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 20.22 | 25.00 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 13.69 | 12.35 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 18.15 | 19.74 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4.68 | 3.75 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 10.27 | 5.25 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4.68 | 3.75 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 5.94 | 8.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4.68 | 3.75 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 5.94 | 8.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4.68 | 3.75 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 5.94 | 8.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 6.33 | 4.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 5.94 | 8.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 6.34 | 4.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5.25 | 8.88 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 10.34 | 7.37 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.27 | 8.92 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.25 | 13.67 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 9.55 | 16.10 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 15.03 | 11.75 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 20.93 | 36.67 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 17.58 | 16.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 17.25 | 22.06 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x192` | 5.28 | 3.42 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 8.75 | 5.42 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4.46 | 3.55 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 7.59 | 5.11 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4.46 | 3.55 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 7.59 | 5.11 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x113` | 4.64 | 3.60 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 7.59 | 5.11 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 5.63 | 3.49 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 7.59 | 5.11 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 7.35 | 4.21 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 7.59 | 5.11 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8.98 | 6.41 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.76 | 5.52 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 16.04 | 12.15 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 7.65 | 8.85 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 14.25 | 11.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 12.68 | 14.95 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 16.23 | 15.13 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 10.01 | 6.24 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x250` | 6.39 | 3.93 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 11.34 | 6.78 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 5.13 | 4.06 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 4.99 | 4.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 5.13 | 4.06 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 4.99 | 4.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 5.13 | 4.06 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 4.99 | 4.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 6.01 | 3.72 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 4.99 | 4.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 7.44 | 4.64 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 6.73 | 4.33 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 10.60 | 5.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 11.20 | 6.54 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 17.38 | 12.12 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 14.38 | 8.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 17.68 | 14.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 18.80 | 10.63 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 18.58 | 16.74 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 7.32 | 5.18 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5.00 | 3.47 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 13.68 | 6.39 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5.00 | 3.47 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 7.04 | 8.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5.00 | 3.47 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 7.04 | 8.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 5.00 | 3.47 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 7.04 | 8.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 7.84 | 4.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 7.04 | 8.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x113-romfill` | 8.30 | 5.36 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 12.26 | 15.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7.87 | 5.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 12.26 | 15.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 15.63 | 10.41 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 12.27 | 15.97 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 19.87 | 15.31 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 21.12 | 26.55 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.85 | 16.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 18.92 | 20.78 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 6.03 | 4.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 9.93 | 4.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 6.03 | 4.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 8.83 | 17.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 6.03 | 4.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 8.83 | 17.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 6.03 | 4.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 8.83 | 17.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 6.03 | 4.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 8.83 | 17.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 10.15 | 7.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 8.72 | 16.60 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 10.14 | 7.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 8.72 | 16.60 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.41 | 13.44 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 15.52 | 30.54 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 20.97 | 17.14 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 23.57 | 42.68 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 16.55 | 15.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 19.47 | 25.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5.07 | 3.54 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 7.59 | 8.34 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5.07 | 3.54 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 7.59 | 8.34 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5.07 | 3.54 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 7.59 | 8.34 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 5.07 | 3.54 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 7.59 | 8.34 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 5.20 | 3.71 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 7.59 | 8.34 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5.21 | 3.78 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 7.01 | 8.76 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8.13 | 5.33 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 7.01 | 8.76 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 15.75 | 10.86 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 11.95 | 15.30 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 19.56 | 15.50 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 20.22 | 25.00 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 13.69 | 12.35 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 18.15 | 19.74 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4.68 | 3.75 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 5.94 | 8.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4.68 | 3.75 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 5.94 | 8.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4.68 | 3.75 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 5.94 | 8.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4.68 | 3.75 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 5.94 | 8.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 6.33 | 4.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 5.94 | 8.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 6.34 | 4.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5.25 | 8.88 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 10.34 | 7.37 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.27 | 8.92 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.25 | 13.67 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 9.55 | 16.10 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 15.03 | 11.75 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 20.93 | 36.68 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 17.58 | 16.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 17.25 | 22.07 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | 8.18 | 8.36 | NO | the KV store has no room for it |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 8.13 | 8.39 | NO | the KV store has no room for it |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 6.56 | 6.29 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 6.26 | 5.56 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 6.56 | 6.29 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 6.26 | 5.56 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 9.02 | 8.52 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 6.26 | 5.56 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 9.62 | 9.18 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 6.26 | 5.56 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 12.92 | 12.25 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 6.26 | 5.56 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 15.37 | 14.52 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 6.29 | 5.63 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 17.65 | 16.63 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 10.86 | 9.56 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 17.53 | 17.05 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 12.65 | 11.11 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 17.14 | 17.10 | yes | -- |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 9.06 | 8.67 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x398` | 8.37 | 8.44 | NO | the KV store has no room for it |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x10` | 5.54 | 5.71 | NO | the KV store has no room for it |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 10.04 | 10.00 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 4.07 | 4.36 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 10.04 | 10.00 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 4.07 | 4.36 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 10.43 | 10.40 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 4.07 | 4.36 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 13.33 | 13.29 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 4.07 | 4.36 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 15.39 | 15.35 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 4.07 | 4.36 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 16.44 | 16.40 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 5.50 | 5.98 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 17.21 | 17.16 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 6.07 | 6.48 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 17.20 | 17.20 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 6.62 | 7.10 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 17.14 | 17.14 | yes | -- |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x22` | 5.74 | 5.98 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x383` | 9.46 | 9.42 | NO | the KV store has no room for it |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | 7.25 | 6.46 | NO | the KV store has no room for it |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 4.81 | 3.23 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 4.81 | 3.23 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 4.81 | 3.23 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 4.81 | 3.23 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 4.81 | 3.23 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 4.81 | 3.23 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 9.24 | 5.64 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 11.64 | 6.97 | yes | -- |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x68` | 12.19 | 7.30 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 5.29 | 5.29 | NO | the KV store has no room for it |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x23` | 5.64 | 5.14 | NO | the KV store has no room for it |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 2.35 | 1.98 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 2.35 | 1.98 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 2.35 | 1.98 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 2.35 | 1.98 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 2.51 | 2.17 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 4.57 | 3.27 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 5.29 | 3.98 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 6.06 | 4.46 | yes | -- |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 6.25 | 4.59 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 8.50 | 7.08 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 7.42 | 8.68 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 8.50 | 7.08 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 7.42 | 8.68 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 8.50 | 7.08 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 7.42 | 8.68 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 8.50 | 7.08 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 7.42 | 8.68 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 8.50 | 7.08 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 7.42 | 8.68 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 12.13 | 9.59 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 7.42 | 8.68 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 12.51 | 10.30 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 7.43 | 8.81 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 19.60 | 15.43 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 12.13 | 11.65 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 19.50 | 16.97 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 16.33 | 19.12 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 17.67 | 17.00 | yes | -- |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 10.59 | 10.40 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 8.56 | 8.28 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 6.96 | 10.31 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 8.56 | 8.28 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 6.96 | 10.31 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 8.56 | 8.28 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 6.96 | 10.31 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 8.56 | 8.28 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 6.96 | 10.31 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 11.55 | 11.05 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 6.96 | 10.31 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 12.26 | 11.83 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 5.56 | 8.08 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 14.95 | 14.36 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 6.06 | 8.22 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 17.93 | 17.14 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 10.23 | 14.68 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 17.77 | 17.35 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 12.04 | 17.36 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 17.20 | 17.10 | yes | -- |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 9.14 | 10.50 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | 6.86 | 6.42 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3.44 | 2.68 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 5.69 | 3.64 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3.27 | 1.81 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 5.69 | 3.64 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3.27 | 1.81 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 5.69 | 3.64 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3.27 | 1.81 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x282` | 6.82 | 3.94 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3.27 | 1.81 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 7.75 | 4.29 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.33 | 1.90 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 9.37 | 4.44 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 3.78 | 1.90 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 8.22 | 7.84 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.58 | 1.66 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 7.51 | 7.41 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 4.84 | 1.64 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 7.45 | 7.45 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x22` | 2.95 | 1.33 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x64` | 7.24 | 6.66 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 3.95 | 3.19 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3.89 | 3.04 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1.98 | 1.63 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3.89 | 3.04 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1.98 | 1.63 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x287` | 4.31 | 3.31 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1.98 | 1.63 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4.80 | 3.41 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3.10 | 1.84 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 5.36 | 3.28 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3.08 | 1.84 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 5.70 | 3.08 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3.44 | 1.85 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 6.23 | 3.11 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 3.99 | 1.87 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 4.40 | 2.78 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 4.13 | 1.90 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 2.91 | 2.50 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x31` | 2.58 | 1.45 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 6.64 | 6.14 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 5.93 | 5.13 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2.88 | 1.44 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2.88 | 1.44 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2.88 | 1.44 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2.88 | 1.44 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 2.87 | 1.48 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 3.56 | 1.35 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5.14 | 1.19 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5.68 | 1.17 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5.78 | 1.16 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | 7.41 | 6.84 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 6.70 | 5.68 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 1.79 | 1.75 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 2.82 | 1.35 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 2.82 | 1.35 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 2.82 | 1.35 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 2.82 | 1.35 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 2.54 | 1.40 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 2.98 | 1.17 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 2.90 | 1.12 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 2.93 | 1.11 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 5.95 | 5.23 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 5.07 | 7.20 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 5.95 | 5.23 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 5.07 | 7.20 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 5.95 | 5.23 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 5.07 | 7.20 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 5.95 | 5.23 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 5.07 | 7.20 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 6.03 | 5.30 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 4.01 | 7.55 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5.93 | 5.22 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 3.92 | 7.32 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9.21 | 7.82 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.90 | 7.28 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 14.47 | 12.62 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.92 | 11.40 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 18.08 | 16.61 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 8.43 | 18.13 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.32 | 16.90 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 6.83 | 9.56 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 7.13 | 7.29 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3.72 | 6.85 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 7.13 | 7.29 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3.72 | 6.85 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 7.13 | 7.29 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3.72 | 6.85 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 7.13 | 7.29 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3.72 | 6.85 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 7.11 | 7.26 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill` | 2.99 | 7.00 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 7.00 | 7.15 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.93 | 6.75 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 11.05 | 11.33 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.80 | 11.24 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 16.48 | 16.83 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4.64 | 13.74 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 18.95 | 19.20 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 5.21 | 17.33 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.55 | 17.62 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 3.97 | 7.16 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | 6.13 | 5.65 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 4.50 | 3.69 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 3.72 | 1.66 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 3.72 | 1.66 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 3.72 | 1.66 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 3.72 | 1.66 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 3.72 | 1.66 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 3.57 | 1.73 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 4.72 | 1.54 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 5.22 | 1.49 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x49` | 5.32 | 1.49 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | 6.84 | 6.28 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 7.07 | 6.31 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 2.10 | 1.57 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 2.10 | 1.57 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 2.10 | 1.57 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 2.10 | 1.57 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 2.47 | 1.55 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3.33 | 1.64 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 4.10 | 1.64 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 4.36 | 1.67 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x68` | 4.40 | 1.67 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | 5.40 | 4.87 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 8.34 | 7.42 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 3.30 | 1.35 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 3.30 | 1.35 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 3.30 | 1.35 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 3.30 | 1.35 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 3.30 | 1.35 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 3.27 | 1.36 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 5.54 | 1.18 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 6.07 | 1.13 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 6.27 | 1.12 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | 6.88 | 6.52 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 5.66 | 5.02 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 1.67 | 1.64 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 2.13 | 2.11 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.08 | 1.25 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.08 | 1.25 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.08 | 1.25 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.08 | 1.25 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 2.94 | 1.16 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.06 | 1.10 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 3.12 | 1.09 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 5.97 | 4.81 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.55 | 7.52 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 5.97 | 4.81 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.55 | 7.52 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 5.97 | 4.81 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.55 | 7.52 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 5.97 | 4.81 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.55 | 7.52 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 5.84 | 4.54 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5.55 | 7.52 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 8.63 | 6.14 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 5.44 | 7.51 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 9.34 | 7.03 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.36 | 7.40 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 19.20 | 13.54 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 8.32 | 11.28 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 15.07 | 12.57 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 11.96 | 16.54 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 17.13 | 15.99 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 9.46 | 6.37 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 7.08 | 6.06 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 4.12 | 7.40 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 7.08 | 6.06 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.21 | 6.63 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 7.08 | 6.06 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.21 | 6.63 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 7.08 | 6.06 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.21 | 6.63 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 6.79 | 5.59 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 4.21 | 6.63 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 10.36 | 8.10 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 5.81 | 6.24 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 11.32 | 9.23 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.12 | 10.44 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 21.38 | 16.93 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 9.67 | 10.49 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 18.20 | 16.21 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 11.51 | 12.51 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 19.91 | 17.56 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 4.85 | 5.11 | yes | -- |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x180` | 6.34 | 6.18 | NO | the KV store has no room for it |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 2.82 | 2.82 | NO | the KV store has no room for it |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x227` | 6.04 | 5.90 | NO | the KV store has no room for it |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 3.81 | 3.81 | NO | the KV store has no room for it |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x60-romfill` | 6.51 | 6.51 | NO | the KV store has no room for it |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 2.26 | 2.26 | NO | the KV store has no room for it |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x139-romfill` | 1.86 | 1.86 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x139` | 2.48 | 2.40 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.38 | 1.42 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.38 | 1.42 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.38 | 1.42 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.48 | 1.51 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.11 | 1.20 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.04 | 1.13 | yes | -- |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1.02 | 1.11 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 6.74 | 6.74 | NO | the KV store has no room for it |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 2.49 | 2.49 | NO | the KV store has no room for it |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196-romfill` | 1.82 | 1.83 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 2.39 | 2.32 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 3.28 | 3.22 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 4.52 | 4.47 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.25 | 1.31 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.26 | 1.31 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.08 | 1.15 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.03 | 1.09 | yes | -- |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1.01 | 1.08 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 9.57 | 6.50 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 4.93 | 3.44 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 9.06 | 5.82 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.65 | 2.77 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 9.06 | 5.82 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.65 | 2.77 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 9.06 | 5.82 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.65 | 2.77 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 9.06 | 5.82 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.65 | 2.77 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 9.06 | 5.82 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.65 | 2.77 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 11.55 | 5.15 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.65 | 2.77 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 13.78 | 8.60 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 3.43 | 3.63 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 15.29 | 11.54 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 4.21 | 4.54 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 12.43 | 11.54 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 8.30 | 2.25 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 5.06 | 3.84 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4.37 | 5.25 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 5.06 | 3.84 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4.37 | 5.25 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 5.06 | 3.84 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4.37 | 5.25 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 5.06 | 3.84 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4.37 | 5.25 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 5.09 | 3.80 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4.37 | 5.25 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5.10 | 3.84 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4.30 | 5.15 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5.10 | 3.84 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4.30 | 5.15 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 14.44 | 9.87 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 7.18 | 8.88 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.14 | 13.72 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 13.61 | 16.34 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.75 | 16.01 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 15.97 | 17.07 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4.87 | 3.65 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 7.04 | 8.79 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4.87 | 3.65 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 7.04 | 8.79 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4.87 | 3.65 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 7.04 | 8.79 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 4.87 | 3.65 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 7.04 | 8.79 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 4.91 | 3.62 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 7.04 | 8.79 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4.92 | 3.66 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 7.04 | 8.79 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4.92 | 3.66 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 7.04 | 8.79 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 14.31 | 9.56 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 7.04 | 8.80 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.08 | 13.50 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 13.97 | 16.96 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.73 | 15.92 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 16.03 | 17.24 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 11.08 | 6.12 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 5.16 | 4.29 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 11.08 | 6.12 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.88 | 4.23 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 11.08 | 6.12 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.88 | 4.23 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 11.08 | 6.12 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.88 | 4.23 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 11.08 | 6.12 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.88 | 4.23 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 11.08 | 6.12 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.88 | 4.23 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 11.08 | 6.12 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.88 | 4.23 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 18.61 | 10.59 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 8.91 | 7.81 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 21.44 | 15.03 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 16.82 | 14.60 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 18.27 | 16.45 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 11.92 | 7.97 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 10.22 | 5.81 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 8.31 | 6.87 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 10.22 | 5.81 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 8.31 | 6.87 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 10.22 | 5.81 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 8.31 | 6.87 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 10.22 | 5.81 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 8.31 | 6.87 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 10.22 | 5.81 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 8.31 | 6.87 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 10.22 | 5.81 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 8.31 | 6.87 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 10.22 | 5.81 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 8.31 | 6.87 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 17.51 | 8.97 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 14.63 | 11.95 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 22.55 | 14.53 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 21.77 | 18.42 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 18.63 | 16.29 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 13.12 | 11.17 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 6.42 | 4.16 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 8.49 | 6.98 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 6.42 | 4.16 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 8.49 | 6.98 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 6.42 | 4.16 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 8.49 | 6.98 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 6.42 | 4.16 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 8.49 | 6.98 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 6.42 | 4.16 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 8.49 | 6.98 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 6.42 | 4.16 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 8.49 | 6.98 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 10.36 | 5.83 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 8.49 | 6.98 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 13.92 | 9.48 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.54 | 8.13 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 22.76 | 14.44 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 21.94 | 18.47 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 18.71 | 16.26 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 13.78 | 12.76 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x152` | 11.37 | 7.62 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 6.36 | 4.25 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 8.50 | 6.38 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.03 | 1.80 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 8.50 | 6.38 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.03 | 1.80 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 8.50 | 6.38 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.03 | 1.80 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 8.50 | 6.38 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.03 | 1.80 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 10.25 | 6.19 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.03 | 1.80 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 13.39 | 5.91 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.03 | 1.80 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 16.18 | 7.84 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 8.15 | 1.95 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 13.25 | 8.21 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 10.87 | 1.90 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 9.53 | 8.22 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 11.57 | 1.94 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 6.46 | 4.89 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5.86 | 7.86 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 6.46 | 4.89 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5.86 | 7.86 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 6.46 | 4.89 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5.86 | 7.86 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 6.46 | 4.89 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5.86 | 7.86 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 6.46 | 4.89 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5.86 | 7.86 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 6.36 | 5.02 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 5.08 | 8.40 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6.37 | 5.04 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5.08 | 8.40 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 12.16 | 9.92 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 8.25 | 14.37 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.28 | 15.23 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 12.88 | 20.83 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.09 | 16.49 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 12.34 | 14.93 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 6.11 | 4.78 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 5.27 | 8.93 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 6.11 | 4.78 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 5.27 | 8.93 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 6.11 | 4.78 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 5.27 | 8.93 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 6.11 | 4.78 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 5.27 | 8.93 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 6.11 | 4.78 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 5.27 | 8.93 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 6.13 | 4.79 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 5.17 | 8.73 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6.14 | 4.80 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5.17 | 8.73 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 12.09 | 9.74 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 8.93 | 15.94 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.30 | 15.10 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 16.26 | 26.90 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.10 | 16.45 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 16.85 | 20.71 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 6.05 | 4.64 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 6.40 | 5.16 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 6.05 | 4.64 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 4.55 | 3.26 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 6.05 | 4.64 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 4.55 | 3.26 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 6.05 | 4.64 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 4.55 | 3.26 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 6.05 | 4.64 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 4.55 | 3.26 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 8.54 | 5.73 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 4.55 | 3.26 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 13.40 | 8.03 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 7.33 | 4.82 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 19.58 | 12.38 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 10.50 | 6.85 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 21.26 | 16.05 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 15.23 | 9.69 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 18.17 | 16.75 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 7.41 | 5.91 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 5.41 | 3.98 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 6.06 | 6.52 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 5.41 | 3.98 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 6.06 | 6.52 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 5.41 | 3.98 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 6.06 | 6.52 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 5.41 | 3.98 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 6.06 | 6.52 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 5.41 | 3.98 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 6.06 | 6.52 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 7.83 | 5.04 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 6.06 | 6.52 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 12.98 | 7.20 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 10.52 | 11.36 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 20.04 | 11.66 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 11.56 | 12.31 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 22.32 | 15.81 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 14.92 | 12.61 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 18.50 | 16.67 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 18.17 | 16.37 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 8.03 | 5.17 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 6.06 | 6.55 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 8.03 | 5.17 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 6.06 | 6.55 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 8.03 | 5.17 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 6.06 | 6.55 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 8.03 | 5.17 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 6.06 | 6.55 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 8.03 | 5.17 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 6.06 | 6.55 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 8.03 | 5.17 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 6.06 | 6.55 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 13.15 | 7.61 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 10.86 | 11.75 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 20.13 | 11.53 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 11.73 | 12.53 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 22.53 | 15.76 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 14.81 | 12.44 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 18.57 | 16.66 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 16.96 | 15.98 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 4.96 | 4.96 | NO | the KV store has no room for it |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 2.19 | 2.64 | NO | the KV store has no room for it |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 4.85 | 4.96 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 1.95 | 2.63 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 4.85 | 4.96 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 1.95 | 2.63 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 4.85 | 4.96 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 1.95 | 2.63 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4.84 | 4.94 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.95 | 2.62 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5.96 | 6.14 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.96 | 3.10 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7.14 | 7.14 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.12 | 2.97 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9.56 | 9.56 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.85 | 3.16 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9.82 | 9.82 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1.71 | 3.13 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 10.13 | 10.13 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1.75 | 1.89 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 5.74 | 4.54 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 5.88 | 3.75 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 5.95 | 4.37 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3.23 | 3.57 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 5.95 | 4.37 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3.23 | 3.57 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 5.95 | 4.37 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3.23 | 3.57 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x70` | 6.12 | 4.17 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3.23 | 3.57 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 6.06 | 4.86 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3.23 | 3.57 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6.06 | 4.86 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.23 | 3.58 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 11.14 | 9.27 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.01 | 5.58 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.35 | 14.67 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 7.68 | 8.79 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 12.92 | 11.87 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 7.25 | 7.57 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 13.54 | 8.18 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 6.70 | 4.42 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 13.54 | 8.18 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3.40 | 3.16 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 13.54 | 8.18 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3.40 | 3.16 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 13.54 | 8.18 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3.40 | 3.16 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 13.54 | 8.18 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3.40 | 3.16 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 13.54 | 8.18 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3.40 | 3.16 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 13.54 | 8.18 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3.40 | 3.16 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 19.24 | 12.32 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 8.76 | 2.51 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 20.64 | 15.75 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 16.64 | 3.37 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 18.00 | 16.67 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 20.01 | 3.82 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 5.45 | 5.45 | NO | the KV store has no room for it |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 2.39 | 2.80 | NO | the KV store has no room for it |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4.17 | 4.45 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.67 | 2.42 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4.17 | 4.45 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.67 | 2.42 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4.17 | 4.45 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.67 | 2.42 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4.57 | 5.10 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.62 | 2.85 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 5.32 | 5.60 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.70 | 2.65 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 5.77 | 6.15 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.53 | 2.76 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6.51 | 7.02 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.26 | 2.78 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 6.87 | 6.87 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1.18 | 2.75 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 3.65 | 3.38 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 2.00 | 1.44 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x79` | 5.38 | 4.56 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 6.63 | 4.51 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 5.52 | 4.60 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 4.72 | 2.71 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 5.52 | 4.60 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 4.72 | 2.71 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 5.52 | 4.60 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 4.72 | 2.71 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 7.52 | 5.68 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 4.72 | 2.71 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 5.51 | 4.88 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 4.72 | 2.71 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 7.40 | 6.18 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 7.41 | 3.57 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 12.79 | 11.05 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 10.77 | 4.23 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.14 | 15.74 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 4.89 | 7.07 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 15.13 | 14.22 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 5.35 | 2.90 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 8.46 | 7.26 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 8.28 | 5.08 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.82 | 2.01 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.82 | 2.01 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.82 | 2.01 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.82 | 2.01 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.82 | 2.01 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.82 | 2.01 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 9.03 | 2.35 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 14.34 | 2.97 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 16.08 | 3.20 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 6.83 | 6.83 | NO | the KV store has no room for it |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-hybrid-x2-romfill` | 1.87 | 1.98 | NO | the KV store has no room for it |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 3.83 | 3.83 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 1.78 | 1.95 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 3.83 | 3.83 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 1.78 | 1.95 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x170-romfill` | 3.83 | 3.83 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 1.78 | 1.95 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3.84 | 3.84 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.79 | 1.95 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4.03 | 4.03 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.69 | 1.98 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4.29 | 4.29 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.79 | 2.00 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4.81 | 4.81 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.37 | 1.69 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4.87 | 4.87 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 1.17 | 1.53 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4.88 | 4.88 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 1.70 | 1.13 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x8-romfill` | 5.34 | 5.34 | NO | the KV store has no room for it |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-hybrid-x2-romfill` | 1.92 | 2.01 | NO | the KV store has no room for it |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 3.47 | 3.52 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 1.63 | 1.83 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 3.47 | 3.52 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 1.63 | 1.83 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 3.47 | 3.52 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 1.63 | 1.83 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 3.30 | 3.41 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.57 | 1.88 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3.67 | 3.69 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.63 | 1.87 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3.41 | 3.45 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.45 | 1.76 | yes | -- |
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
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | no | 850,275,640 | 90.7 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | no | 850,275,640 | 90.7 | 0.1% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | no | 850,275,640 | 90.7 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | no | 850,275,640 | 90.7 | 0.0% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | no | 850,275,640 | 116.6 | 0.0% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | no | 850,275,640 | 90.7 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | no | 850,275,640 | 90.7 | 0.1% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-SRAMKV-wafer-hybrid-x10-romfill` | no | 850,275,640 | 90.7 | 0.0% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | no | 850,275,640 | 116.6 | 0.0% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-SRAMKV-array-hw-hybrid-x192` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | no | 850,275,640 | 90.7 | 0.0% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-SRAMKV-array-hw-hybrid-x250` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | no | 850,275,640 | 116.6 | 0.0% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | no | 850,275,640 | 90.7 | 0.0% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | no | 850,275,640 | 116.6 | 0.0% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | no | 11,706,065,920 | 1,248.0 | 0.4% | 1.0075x |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | no | 11,706,065,920 | 1,248.0 | 0.4% | 1.0075x |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x398` | no | 11,706,065,920 | 1,604.6 | 0.5% | 1.0075x |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `ROM-N6-native-SRAMKV-wafer-hybrid-x10` | no | 11,706,065,920 | 1,604.6 | 0.3% | 1.0075x |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x383` | no | 11,706,065,920 | 1,248.0 | 0.4% | 1.0075x |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | no | 11,706,065,920 | 1,248.0 | 0.1% | 1.0075x |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | no | 11,706,065,920 | 1,604.6 | 0.5% | 1.0075x |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `ROM-N6-native-SRAMKV-wafer-hybrid-x23` | no | 11,706,065,920 | 1,604.6 | 0.2% | 1.0075x |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | no | 11,706,065,920 | 1,248.0 | 0.4% | 1.0075x |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | no | 11,706,065,920 | 1,248.0 | 0.3% | 1.0075x |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | no | 11,706,065,920 | 1,604.6 | 0.5% | 1.0075x |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | no | 11,706,065,920 | 1,604.6 | 0.5% | 1.0075x |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | no | 1,620,446,720 | 172.8 | 0.5% | 1.0094x |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | no | 1,620,446,720 | 172.8 | 0.2% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x64` | no | 1,620,446,720 | 222.1 | 0.4% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | no | 1,620,446,720 | 222.1 | 0.2% | 1.0094x |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | no | 1,620,446,720 | 172.8 | 0.2% | 1.0094x |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | no | 1,620,446,720 | 172.8 | 0.2% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | no | 1,620,446,720 | 222.1 | 0.2% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | no | 1,620,446,720 | 222.1 | 0.2% | 1.0094x |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | no | 1,620,446,720 | 172.8 | 0.2% | 1.0094x |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | no | 1,620,446,720 | 172.8 | 0.2% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | no | 1,620,446,720 | 222.1 | 0.3% | 1.0094x |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | no | 1,620,446,720 | 222.1 | 0.2% | 1.0094x |
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
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | no | 3,350,899,200 | 459.3 | 0.3% | 1.0059x |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x180` | no | 1,929,464,320 | 205.7 | 0.1% | 1.1178x |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | no | 1,929,464,320 | 205.7 | 0.2% | 1.1178x |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x227` | no | 1,929,464,320 | 264.5 | 0.1% | 1.1178x |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | no | 1,929,464,320 | 264.5 | 0.3% | 1.1178x |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-hybrid-x60-romfill` | no | 1,929,464,320 | 205.7 | 0.4% | 1.1178x |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | no | 1,929,464,320 | 205.7 | 0.2% | 1.1178x |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | no | 1,929,464,320 | 264.5 | 0.6% | 1.1178x |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | no | 1,929,464,320 | 264.5 | 0.3% | 1.1178x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | no | 686,957,240 | 73.2 | 0.0% | 1.0041x |
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
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | no | 1,929,464,320 | 205.7 | 1.6% | 1.1178x |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | no | 1,929,464,320 | 205.7 | 0.2% | 1.1178x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | no | 1,929,464,320 | 264.5 | 2.0% | 1.1178x |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | no | 1,929,464,320 | 264.5 | 0.3% | 1.1178x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x79` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | no | 512,513,960 | 54.6 | 1.7% | 1.1178x |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-wafer-hybrid-x2-romfill` | no | 512,513,960 | 54.6 | 0.1% | 1.1178x |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x8-romfill` | no | 512,513,960 | 70.3 | 1.1% | 1.1178x |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-wafer-hybrid-x2-romfill` | no | 512,513,960 | 70.3 | 0.1% | 1.1178x |

## Which design the published rule chooses once a block is verified

A re-ranking of designs the study already evaluated, under the study's own selection rule (non-dominated on per-user tokens/s and tokens/s per 1,000 mm2, then a marginal-return walk from the smallest feasible machine). `tau` is a common factor on both axes, so the choice is independent of the acceptance rate. The rule's reproduction of the published autoregressive recommendation is reported first, because a re-ranking whose baseline does not reproduce is not evidence of anything.

| study | model | published recommendation | rule reproduces it | under speculation, draft in ROM | draft in KV store | moves |
| --- | --- | --- | --- | --- | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x98` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x98` | `ROM-N5-native-HBMKV-array-hw-tensor-x110` | yes |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x126` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x132` | `ROM-N6-native-HBMKV-array-hw-tensor-x143` | yes |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x98` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x104` | `ROM-N5-native-HBMKV-array-hw-tensor-x110` | yes |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x115` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x136` | `ROM-N6-native-HBMKV-array-hw-tensor-x143` | yes |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x97` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x103` | `ROM-N5-native-HBMKV-array-hw-tensor-x107` | yes |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x141` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x132` | `ROM-N6-native-HBMKV-array-hw-tensor-x141` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | yes | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x75` | yes | `ROM-N6-native-HBMKV-array-hw-tensor-x86` | `ROM-N6-native-HBMKV-array-hw-tensor-x86` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | yes | `ROM-N5-native-HBMKV-array-hw-tensor-x68` | `ROM-N5-native-HBMKV-array-hw-tensor-x68` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x75` | yes | `ROM-N6-native-HBMKV-array-hw-tensor-x87` | `ROM-N6-native-HBMKV-array-hw-tensor-x87` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x75` | yes | `ROM-N6-native-HBMKV-array-hw-tensor-x85` | `ROM-N6-native-HBMKV-array-hw-tensor-x85` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-SRAMKV-array-hw-hybrid-x76` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x76` | `ROM-N6-native-HBMKV-array-hw-tensor-x86` | yes |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x313` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x5` | `ROM-N5-native-HBMKV-array-hw-tensor-x327` | yes |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x398` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x7` | `ROM-N6-native-HBMKV-array-hw-tensor-x398` | yes |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `ROM-N5-native-SRAMKV-array-hw-tensor-x312` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x6` | `ROM-N5-native-HBMKV-wafer-tensor-x68` | yes |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `ROM-N6-native-SRAMKV-array-hw-tensor-x391` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x8` | `ROM-N6-native-HBMKV-wafer-tensor-x95` | yes |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x5` | `ROM-N5-native-HBMKV-wafer-tensor-x5` | yes |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x357` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x6` | `ROM-N6-native-HBMKV-wafer-tensor-x6` | yes |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-tensor-x36` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x44` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | yes |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-tensor-x46` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | yes |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x55-romfill` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | yes |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-tensor-x64-romfill` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x71` | `ROM-N6-native-HBMKV-wafer-tensor-x153` | yes |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x34` | `ROM-N5-native-HBMKV-array-hw-tensor-x38` | yes |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x43` | `ROM-N6-native-HBMKV-array-hw-tensor-x47` | yes |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x2` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | yes |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-hybrid-x153` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | yes |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-array-hw-tensor-x132` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | yes |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-tensor-x170` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | yes |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x109` | `ROM-N5-native-HBMKV-array-hw-tensor-x123` | yes |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-hybrid-x139` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x139` | `ROM-N6-native-HBMKV-array-hw-tensor-x138` | yes |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | yes | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | `None` | yes |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | yes | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | `None` | yes |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x21` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-tensor-x139` | yes |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x27` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | yes |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | yes |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x32` | `ROM-N5-native-HBMKV-array-hw-tensor-x32` | yes |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x32` | `ROM-N5-native-HBMKV-array-hw-tensor-x32` | yes |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x156` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-array-hw-hybrid-x208` | yes |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x156` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-tensor-x3` | yes |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x171` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-wafer-tensor-x3` | yes |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x46` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | yes |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x40` | yes | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | `ROM-N6-native-HBMKV-array-hw-tensor-x45` | yes |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x41` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x41` | `ROM-N6-native-HBMKV-array-hw-tensor-x45` | yes |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x227` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-array-hw-tensor-x217` | yes |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x227` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-tensor-x4` | yes |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x219` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-tensor-x4` | yes |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x8` | `ROM-N5-native-HBMKV-array-hw-hybrid-x49` | yes |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x30` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | `ROM-N5-native-HBMKV-array-hw-hybrid-x56` | yes |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399-romfill` | yes |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x12` | `ROM-N6-native-HBMKV-array-hw-tensor-x69` | yes |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x41` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-hybrid-x79` | yes |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x227` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | yes |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | yes | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x49` | yes |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | yes | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x4` | `ROM-N6-q4p25-HBMKV-array-hw-tensor-x69` | yes |

**The rule reproduces the published autoregressive recommendation on 56 of 56 model-and-study rows.** Of the 56 rows where it reproduces and the drafter applies, verifying a block moves the chosen rung on 56. Where it moves, it moves toward machines with compute headroom for a block, which is exactly what the arithmetic predicts: a verification pass raises arithmetic intensity by the block size, and a machine sized with just enough compute for one token per sweep has no room for it. **This is a re-ranking of rungs that already exist. The speculative-optimal design has not been computed: that would need the area split re-solved, which is `balanced_area_split`'s job and not this layer's.**

## Gate: the DFlash overhead factor

_band check, never an equality._

- modelled on `Qwen3-8B/b200_sxm-x3-tensor` at batch 1, 8,192 tokens of context, gamma 16
- modelled overhead factor: **1.188** with the drafter charged no KV, **1.194** at the top of the band
- published band: 1.26-1.32, outlier MT-Bench at 1.54
- source: arXiv:2602.06036v2, ICML 2026, Table 1, tau divided by reported speedup
- inside the published band: **no**

**Residual.** this layer models an overhead factor of 1.188 at the low end of the unsourced drafter-KV band and 1.194 at the high end, against a published 1.26-1.32 measured on an H200. The gap is the gate residual and its named causes are: the drafter's own KV traffic at the low bound of an unsourced band, no sampler and no scheduler cost anywhere in this model, and a modelled B200-class cluster against their measured H200.

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

GPU cluster sizes this study evaluates for DeepSeek-V4-Pro-0813: 8, 14, 18, 29, 32, 38, 40, 41, 42, 43, 56, 58, 74, 75, 76, 79, 80, 82, 83, 85, 87, 90, 91, 92, 93, 94, 95, 98, 100, 101, 103, 106, 110, 111, 112, 113, 116, 117, 118, 120, 121, 125, 130, 132, 133, 134, 137, 144, 146, 147, 150, 151, 157, 168, 170, 171, 173, 185, 187, 189, 197, 198, 199, 202, 203, 208, 214, 216, 221, 224, 227, 229, 231, 234, 237, 241, 245, 253, 255, 258, 262, 263, 268, 272, 274, 276, 280, 289, 293, 295, 300, 302, 305, 309, 313, 320, 321, 334, 335, 336, 347, 354, 355, 356, 360, 361, 363, 365, 366, 368, 373, 383, 384, 391, 392, 448, 504, 574, 672, 783, 1358, 3694 packages.

DeepSeek-V4-Pro-0813 is 1.6 trillion total parameters with 49 billion active; the model Xiaomi describes is 1 trillion total, and its active count is ASSUMED at 42 billion -- the blog states no active parameter count, that figure comes from secondary reporting, and it is graded `assumed` here and used for nothing but this sentence. They are the same class and they are not the same model.

| design | packages | batch | ctx | block (gamma) | positions verified | AR per-user tok/s | AR aggregate tok/s | resident sessions | binds on | tau* | coding tau 6.30 | maths tau 5.56 | agent tau 4.29 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| `b200_sxm-x8-expert` | 8 | 1 | 8,192 | 8 | 9 | 299.54 | 300 | 1 | `layer_fixed_latency` | 1.93 | 976.62 | 861.90 | 665.03 |
| `b200_sxm-x8-nvl72-expert` | 8 | 1 | 8,192 | 8 | 9 | 299.54 | 300 | 1 | `layer_fixed_latency` | 1.93 | 976.62 | 861.90 | 665.03 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 1 | 8,192 | 8 | 9 | 354.63 | 355 | 1 | `layer_fixed_latency` | 1.77 | 1,261.09 | 1,112.97 | 858.74 |
| `b200_sxm-x8-pipeline` | 8 | 1 | 8,192 | 8 | 9 | 140.22 | 1,122 | 8 | `weight_read` | 3.18 | 278.22 | 245.54 | 189.45 |
| `b200_sxm-x8-tensor` | 8 | 1 | 8,192 | 8 | 9 | 354.63 | 355 | 1 | `layer_fixed_latency` | 1.77 | 1,261.09 | 1,112.97 | 858.74 |
| `b200_sxm-x8-expert` | 8 | 2 | 8,192 | 8 | 9 | 266.09 | 532 | 2 | `weight_read` | 2.46 | 680.86 | 600.89 | 463.63 |
| `b200_sxm-x8-nvl72-expert` | 8 | 2 | 8,192 | 8 | 9 | 266.09 | 532 | 2 | `weight_read` | 2.46 | 680.86 | 600.89 | 463.63 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 2 | 8,192 | 8 | 9 | 323.67 | 647 | 2 | `layer_fixed_latency` | 2.16 | 941.96 | 831.32 | 641.43 |
| `b200_sxm-x8-pipeline` | 8 | 2 | 8,192 | 8 | 9 | 140.22 | 1,122 | 8 | `weight_read` | 3.18 | 278.22 | 245.54 | 189.45 |
| `b200_sxm-x8-tensor` | 8 | 2 | 8,192 | 8 | 9 | 323.67 | 647 | 2 | `layer_fixed_latency` | 2.16 | 941.96 | 831.32 | 641.43 |
| `b200_sxm-x8-expert` | 8 | 4 | 8,192 | 8 | 9 | 222.15 | 889 | 4 | `weight_read` | 3.25 | 430.14 | 379.62 | 292.91 |
| `b200_sxm-x8-nvl72-expert` | 8 | 4 | 8,192 | 8 | 9 | 222.15 | 889 | 4 | `weight_read` | 3.25 | 430.14 | 379.62 | 292.91 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 4 | 8,192 | 8 | 9 | 276.36 | 1,105 | 4 | `layer_fixed_latency` | 2.68 | 649.50 | 573.21 | 442.28 |
| `b200_sxm-x8-pipeline` | 8 | 4 | 8,192 | 8 | 9 | 140.22 | 1,122 | 8 | `weight_read` | 3.18 | 278.22 | 245.54 | 189.45 |
| `b200_sxm-x8-tensor` | 8 | 4 | 8,192 | 8 | 9 | 276.36 | 1,105 | 4 | `layer_fixed_latency` | 2.68 | 649.50 | 573.21 | 442.28 |
| `b200_sxm-x8-expert` | 8 | 8 | 8,192 | 8 | 9 | 170.95 | 1,368 | 8 | `weight_read` | 4.46 | 241.60 | 213.22 | 164.52 |
| `b200_sxm-x8-nvl72-expert` | 8 | 8 | 8,192 | 8 | 9 | 170.95 | 1,368 | 8 | `weight_read` | 4.46 | 241.60 | 213.22 | 164.52 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 8 | 8,192 | 8 | 9 | 215.70 | 1,726 | 8 | `weight_read` | 3.16 | 429.85 | 379.36 | 292.71 |
| `b200_sxm-x8-pipeline` | 8 | 8 | 8,192 | 8 | 9 | 140.22 | 1,122 | 8 | `weight_read` | 3.18 | 278.22 | 245.54 | 189.45 |
| `b200_sxm-x8-tensor` | 8 | 8 | 8,192 | 8 | 9 | 215.70 | 1,726 | 8 | `weight_read` | 3.16 | 429.85 | 379.36 | 292.71 |
| `b200_sxm-x8-expert` | 8 | 16 | 8,192 | 8 | 9 | 119.87 | 1,918 | 16 | `weight_read` | 6.71 | 112.53 | 99.31 | 76.63 |
| `b200_sxm-x8-nvl72-expert` | 8 | 16 | 8,192 | 8 | 9 | 119.87 | 1,918 | 16 | `weight_read` | 6.71 | 112.53 | 99.31 | 76.63 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 16 | 8,192 | 8 | 9 | 153.37 | 2,454 | 16 | `weight_read` | 3.28 | 294.55 | 259.95 | 200.57 |
| `b200_sxm-x8-pipeline` | 8 | 16 | 8,192 | 8 | 9 | 110.62 | 1,770 | 16 | `weight_read` | 4.20 | 165.78 | 146.30 | 112.89 |
| `b200_sxm-x8-tensor` | 8 | 16 | 8,192 | 8 | 9 | 153.37 | 2,454 | 16 | `weight_read` | 3.28 | 294.55 | 259.95 | 200.57 |
| `b200_sxm-x8-expert` | 8 | 32 | 8,192 | 8 | 9 | 76.45 | 2,446 | 32 | `weight_read` | 12.00 | 40.13 | 35.42 | 27.33 |
| `b200_sxm-x8-nvl72-expert` | 8 | 32 | 8,192 | 8 | 9 | 76.45 | 2,446 | 32 | `weight_read` | 12.00 | 40.13 | 35.42 | 27.33 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 32 | 8,192 | 8 | 9 | 101.85 | 3,259 | 32 | `weight_read` | 3.12 | 205.87 | 181.69 | 140.19 |
| `b200_sxm-x8-pipeline` | 8 | 32 | 8,192 | 8 | 9 | 78.32 | 2,506 | 32 | `weight_read` | 4.93 | 100.10 | 88.34 | 68.16 |
| `b200_sxm-x8-tensor` | 8 | 32 | 8,192 | 8 | 9 | 101.85 | 3,259 | 32 | `weight_read` | 3.12 | 205.87 | 181.69 | 140.19 |
| `b200_sxm-x8-expert` | 8 | 64 | 8,192 | 8 | 9 | 43.79 | 2,803 | 64 | `weight_read` | 23.82 | 11.58 | 10.22 | 7.89 |
| `b200_sxm-x8-nvl72-expert` | 8 | 64 | 8,192 | 8 | 9 | 43.79 | 2,803 | 64 | `weight_read` | 23.82 | 11.58 | 10.22 | 7.89 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 64 | 8,192 | 8 | 9 | 66.96 | 4,285 | 64 | `weight_read` | 3.12 | 135.17 | 119.29 | 92.04 |
| `b200_sxm-x8-pipeline` | 8 | 64 | 8,192 | 8 | 9 | 49.40 | 3,161 | 64 | `thermal` | 4.74 | 65.62 | 57.91 | 44.69 |
| `b200_sxm-x8-tensor` | 8 | 64 | 8,192 | 8 | 9 | 66.96 | 4,285 | 64 | `weight_read` | 3.12 | 135.17 | 119.29 | 92.04 |
| `b200_sxm-x8-expert` | 8 | 256 | 8,192 | 8 | 9 | 7.94 | 2,033 | 256 | `link_latency` | 64.20 | 0.78 | 0.69 | 0.53 |
| `b200_sxm-x8-nvl72-expert` | 8 | 256 | 8,192 | 8 | 9 | 7.94 | 2,033 | 256 | `link_latency` | 64.20 | 0.78 | 0.69 | 0.53 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 256 | 8,192 | 8 | 9 | 34.44 | 8,817 | 256 | `weight_read` | 4.82 | 45.04 | 39.75 | 30.67 |
| `b200_sxm-x8-pipeline` | 8 | 256 | 8,192 | 8 | 9 | 17.35 | 4,442 | 256 | `thermal` | 2.43 | 45.05 | 39.76 | 30.67 |
| `b200_sxm-x8-tensor` | 8 | 256 | 8,192 | 8 | 9 | 34.44 | 8,817 | 256 | `weight_read` | 4.82 | 45.04 | 39.75 | 30.67 |
| `b200_sxm-x8-expert` | 8 | 1024 | 8,192 | 8 | 9 | 0.63 | 642 | 1,024 | `link_latency` | 80.05 | 0.05 | 0.04 | 0.03 |
| `b200_sxm-x8-nvl72-expert` | 8 | 1024 | 8,192 | 8 | 9 | 0.63 | 642 | 1,024 | `link_latency` | 80.05 | 0.05 | 0.04 | 0.03 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 1024 | 8,192 | 8 | 9 | 14.70 | 15,050 | 1,024 | `link_latency` | 8.01 | 11.55 | 10.20 | 7.87 |
| `b200_sxm-x8-pipeline` | 8 | 1024 | 8,192 | 8 | 9 | 8.19 | 8,383 | 1,024 | `thermal` | 1.24 | 41.68 | 36.78 | 28.38 |
| `b200_sxm-x8-tensor` | 8 | 1024 | 8,192 | 8 | 9 | 14.70 | 15,050 | 1,024 | `link_latency` | 8.01 | 11.55 | 10.20 | 7.87 |
| `b200_sxm-x8-expert` | 8 | 4096 | 8,192 | 8 | 9 | 0.04 | 166 | 4,096 | `link_latency` | 82.58 | 0.00 | 0.00 | 0.00 |
| `b200_sxm-x8-nvl72-expert` | 8 | 4096 | 8,192 | 8 | 9 | 0.04 | 166 | 4,096 | `link_latency` | 82.58 | 0.00 | 0.00 | 0.00 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 4096 | 8,192 | 8 | 9 | 4.41 | 18,044 | 4,096 | `link_latency` | 9.60 | 2.89 | 2.55 | 1.97 |
| `b200_sxm-x8-pipeline` | 8 | 4096 | 8,192 | 8 | 9 | 6.79 | 27,794 | 4,096 | `thermal` | 1.55 | 27.60 | 24.36 | 18.80 |
| `b200_sxm-x8-tensor` | 8 | 4096 | 8,192 | 8 | 9 | 4.41 | 18,044 | 4,096 | `link_latency` | 9.60 | 2.89 | 2.55 | 1.97 |

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

