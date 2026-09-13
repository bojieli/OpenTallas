# Speculative decoding on the area-constrained roofline: sota_block_diffusion

> The DFlash / MiMo-UltraSpeed class: a block-diffusion drafter decoding a whole block in one parallel pass. Every figure below is derived from the roofline artifacts
> this repository has already published, by re-assembling each point's own five
> critical-path terms for a speculative cycle. Nothing here re-runs the machine
> model, and nothing here invents an acceptance rate.

## What this layer says

1. **Every term the speculative arithmetic needs is already in the published artifact, exactly.** 42,899 feasible points across 22 studies were rebuilt from their own five critical-path terms and every one reproduced its published step time to 1e-9 relative. Nothing here re-ran the machine model, and the layer is additive by construction rather than by promise.
2. **The headline is a break-even, not a speedup.** `tau* = T_cycle / step_time_s`, and `tau <= gamma+1` always. Of 72,029 (point, draft-placement) pairs where this profile's drafter applies, 6,606 (9.2%) cannot be sped up by speculation at ANY acceptance rate, at any block size on the ladder, even charging the drafter no KV traffic at all.
3. **The ROM-versus-GPU ratio under speculation carries no acceptance rate.** It is `T_cycle(GPU) / T_cycle(ROM)`: `tau` is a property of the model and its drafter, not of the machine, so it is identical on both sides and cancels. Every movement this report shows is a machine effect and nothing else, which is why it can be published without inventing an acceptance rate.
4. **The ratio moves, and which way it moves depends on the machine.** Across 416 model-context-batch-class rows, 187 move the ROM-versus-GPU per-user ratio DOWN under speculation and 229 move it UP, spanning 0.069x to 13.447x. The ROM advantage does not compress on most operating points.
5. **At batch 1 the two extremes are opposite in sign, and they are the result.** Qwen3-8B on `array` silicon goes from 6.08x to 0.42x -- a 0.069x movement -- while DeepSeek-V4.1-Flash-engram-host on `wafer` silicon goes from 5.66x to 13.03x, a 2.303x movement. A layer that multiplied both sides by `tau` would have reported neither.
6. **A moving ratio is not a win for either side, and the report says so on every table.** At the most favourable sourced acceptance (7.87) speculation is worth having on 315 of 416 ROM class rows and 301 of 416 GPU rows; everywhere else the design runs SLOWER with a drafter than without one. Where both sides lose, a rising ratio means only that the comparator lost more.
7. **Compute is never a gain and always a loss.** A verification pass over `n` positions charges `n` times the arithmetic exactly, so per accepted token compute costs `(n/tau) >= 1` times what it did. A compute-bound design cannot be sped up by speculation at any acceptance rate; it can only be slowed. That is where the recommended ROM designs live, because the sizing rule gives them just enough compute for one token per sweep.
8. **On a mask-ROM machine the draft pass costs a full array sweep, and that is the load-bearing assumption of the whole ROM verdict.** `stored/peak` is a technology constant in `src/opentallas/roofline.py`, so a pass reading only the drafter's region takes as long as sweeping the entire array. The alternative -- holding the drafter in the KV store -- is priced beside it on every ROM row and has NOT been costed in silicon area.
9. **The overhead factor lands below the only published measurement of it, and the gap is reported as a residual.** This layer models 1.208 on `b200_sxm-x3-tensor` against a published 1.26-1.32 measured on an H200 with the authors' own kernels. The named causes are the drafter's unsourced KV traffic at the bottom of its band, no sampler or scheduler cost anywhere in this model, and a different part. It is a band check and it validates nothing about the machine.
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
| `n5_vs_b200-deepseek-v41-flash` | 1,804 | 0 |
| `n6_vs_a100-deepseek-v41-flash` | 1,642 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | 1,947 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | 1,969 | 0 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | 1,822 | 0 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | 1,906 | 0 |
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
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 192 | 10 | 2.79 | 8.10 | 17.68 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 400 | 3 | 2.45 | 5.12 | 18.02 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 21 | 21 | 23.02 | 25.78 | 38.43 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 497 | 152 | 1.62 | 12.02 | 448.71 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 694 | 400 | 5.07 | 17.81 | 1,480.34 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 21 | 19 | 16.02 | 23.85 | 38.43 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 497 | 51 | 1.28 | 5.46 | 25.08 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 694 | 138 | 1.62 | 3.71 | 60.40 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 183 | 11 | 2.68 | 8.20 | 17.39 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 385 | 0 | 2.54 | 4.09 | 15.01 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 63 | 63 | 21.77 | 41.03 | 274.78 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 442 | 137 | 1.51 | 12.31 | 401.93 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 569 | 398 | 3.60 | 24.63 | 1,068.61 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 63 | 62 | 16.59 | 40.45 | 61.81 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 442 | 57 | 1.28 | 6.07 | 22.75 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 569 | 127 | 1.62 | 4.21 | 54.42 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 216 | 13 | 2.65 | 7.58 | 17.71 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 448 | 0 | 1.59 | 3.18 | 6.75 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 41 | 10 | 10.83 | 14.86 | 18.94 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 528 | 28 | 1.08 | 4.31 | 18.41 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 714 | 40 | 1.00 | 2.45 | 18.25 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 41 | 10 | 10.81 | 14.87 | 17.76 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 528 | 39 | 1.27 | 4.63 | 25.19 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 714 | 122 | 1.62 | 2.15 | 34.04 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 239 | 14 | 2.55 | 7.71 | 17.49 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 497 | 0 | 1.99 | 2.77 | 6.60 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 40 | 20 | 11.07 | 17.07 | 17.50 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 6 | 0 | 7.37 | 11.52 | 13.27 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 553 | 52 | 1.09 | 5.32 | 18.63 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 634 | 40 | 1.00 | 2.44 | 19.44 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 40 | 20 | 11.12 | 17.12 | 17.54 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 6 | 0 | 7.23 | 11.27 | 13.10 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 553 | 66 | 1.24 | 5.57 | 22.82 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 634 | 104 | 1.62 | 2.03 | 34.05 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 176 | 5 | 2.66 | 7.52 | 17.67 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 368 | 0 | 1.46 | 3.44 | 7.10 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 37 | 8 | 10.83 | 14.86 | 18.94 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 526 | 28 | 1.27 | 4.15 | 18.41 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 715 | 54 | 1.15 | 2.55 | 38.42 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 37 | 8 | 10.81 | 14.87 | 17.76 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 526 | 39 | 1.27 | 4.58 | 25.19 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 715 | 115 | 1.62 | 2.11 | 34.04 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 215 | 6 | 2.57 | 7.71 | 17.35 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 449 | 0 | 1.97 | 3.06 | 6.65 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 36 | 18 | 11.07 | 17.07 | 17.12 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 6 | 0 | 7.37 | 11.53 | 13.27 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 558 | 52 | 1.28 | 5.34 | 18.63 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 642 | 51 | 1.22 | 2.94 | 28.02 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 36 | 18 | 11.12 | 17.12 | 17.36 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 6 | 0 | 7.23 | 11.27 | 13.11 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 558 | 63 | 1.27 | 5.57 | 22.82 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 642 | 106 | 1.62 | 2.01 | 34.04 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 174 | 2 | 2.38 | 6.09 | 17.34 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 354 | 0 | 1.56 | 3.18 | 5.10 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 85 | 10 | 10.34 | 15.94 | 17.53 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 95 | 0 | 1.06 | 4.71 | 15.62 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 580 | 26 | 1.10 | 4.21 | 18.08 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `thermal` | 8 | 0 | 4.56 | 10.93 | 15.48 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 514 | 10 | 1.04 | 3.41 | 17.40 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 85 | 32 | 10.61 | 15.94 | 17.53 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 95 | 11 | 1.54 | 4.28 | 29.11 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 580 | 40 | 1.24 | 4.58 | 25.78 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `thermal` | 8 | 0 | 8.02 | 11.28 | 16.19 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 514 | 110 | 1.60 | 5.82 | 34.08 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 184 | 4 | 2.39 | 6.30 | 17.56 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 4 | 0 | 1.32 | 2.70 | 2.93 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 380 | 0 | 1.42 | 3.29 | 6.05 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 59 | 12 | 11.21 | 16.74 | 18.16 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 3 | 1 | 7.40 | 12.42 | 27.63 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 620 | 30 | 1.22 | 3.39 | 18.10 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 630 | 22 | 1.09 | 2.86 | 21.33 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 59 | 26 | 11.21 | 16.74 | 17.48 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 3 | 0 | 1.99 | 7.46 | 12.42 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 620 | 41 | 1.23 | 3.60 | 25.78 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 630 | 106 | 1.60 | 2.26 | 34.07 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 184 | 4 | 2.39 | 6.31 | 17.57 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 3 | 0 | 1.32 | 1.92 | 2.74 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 381 | 0 | 1.42 | 3.29 | 6.07 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 56 | 8 | 10.92 | 16.70 | 17.50 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 2 | 2 | 61.35 | 61.52 | 61.52 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 624 | 32 | 1.22 | 3.94 | 24.98 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 644 | 34 | 1.13 | 2.77 | 57.27 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 56 | 24 | 10.92 | 16.70 | 17.50 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 2 | 0 | 1.56 | 1.83 | 1.83 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 624 | 41 | 1.23 | 3.69 | 25.78 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 644 | 116 | 1.60 | 2.17 | 34.07 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 151 | 0 | 2.94 | 7.79 | 16.91 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 329 | 0 | 1.48 | 3.20 | 8.62 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 56 | 20 | 9.76 | 15.61 | 17.19 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 6 | 0 | 5.68 | 9.29 | 11.67 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 404 | 20 | 1.27 | 4.67 | 17.89 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 482 | 19 | 1.08 | 2.67 | 17.56 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 56 | 20 | 9.77 | 15.70 | 17.56 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 6 | 0 | 5.94 | 9.35 | 11.71 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 404 | 30 | 1.28 | 4.80 | 23.76 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 482 | 85 | 1.58 | 3.92 | 34.00 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 151 | 0 | 2.94 | 7.79 | 16.93 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 321 | 0 | 1.73 | 3.18 | 7.16 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 55 | 20 | 10.34 | 15.60 | 18.95 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 417 | 20 | 1.27 | 4.69 | 17.89 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 500 | 39 | 1.12 | 2.74 | 20.58 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 55 | 20 | 10.43 | 15.69 | 17.56 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 417 | 32 | 1.27 | 4.95 | 23.76 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 500 | 79 | 1.58 | 3.34 | 34.00 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 135 | 0 | 2.94 | 7.79 | 16.94 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 289 | 0 | 1.73 | 3.23 | 7.17 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 55 | 22 | 10.20 | 15.72 | 25.30 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 421 | 20 | 1.27 | 5.32 | 17.89 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 508 | 47 | 1.18 | 2.81 | 33.06 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 55 | 20 | 10.30 | 15.38 | 17.53 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 421 | 33 | 1.27 | 5.16 | 23.76 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 508 | 83 | 1.58 | 3.25 | 34.00 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 204 | 5 | 2.35 | 6.91 | 17.27 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 420 | 0 | 1.87 | 3.04 | 7.91 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 80 | 6 | 10.32 | 16.61 | 17.07 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 144 | 0 | 1.03 | 3.18 | 14.15 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 606 | 27 | 1.10 | 4.22 | 18.20 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 392 | 10 | 1.07 | 4.02 | 18.04 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 80 | 10 | 10.39 | 16.95 | 17.08 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 144 | 0 | 1.14 | 2.43 | 15.30 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 606 | 37 | 1.24 | 4.43 | 23.23 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 392 | 61 | 1.60 | 5.79 | 34.08 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 215 | 6 | 2.35 | 6.81 | 17.33 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 449 | 0 | 1.67 | 3.12 | 8.68 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 46 | 4 | 10.84 | 16.68 | 17.66 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 11 | 0 | 4.93 | 8.79 | 12.41 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 726 | 30 | 1.23 | 3.69 | 18.36 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 549 | 20 | 1.11 | 3.05 | 23.03 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 46 | 4 | 10.93 | 16.91 | 17.07 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 11 | 0 | 4.99 | 9.02 | 12.41 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 726 | 42 | 1.23 | 4.11 | 23.23 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 549 | 85 | 1.60 | 2.26 | 34.08 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 215 | 7 | 2.35 | 6.82 | 17.33 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 449 | 0 | 1.65 | 3.12 | 8.58 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 50 | 4 | 9.92 | 16.63 | 22.25 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 2 | 1 | 10.67 | 61.52 | 61.52 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 738 | 30 | 1.23 | 4.19 | 18.36 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 554 | 29 | 1.21 | 3.26 | 55.26 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 50 | 4 | 9.74 | 16.63 | 17.05 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 2 | 0 | 1.77 | 10.57 | 10.57 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 738 | 43 | 1.23 | 4.14 | 23.23 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 554 | 88 | 1.60 | 2.17 | 34.08 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 134 | 0 | 2.74 | 8.72 | 16.52 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 370 | 0 | 1.90 | 2.71 | 7.90 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 78 | 18 | 9.81 | 15.45 | 17.10 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 10 | 0 | 4.01 | 5.11 | 6.59 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 313 | 24 | 1.27 | 4.47 | 18.04 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 337 | 19 | 1.16 | 2.31 | 18.01 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 78 | 34 | 9.60 | 15.41 | 17.65 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 10 | 0 | 4.28 | 6.25 | 7.52 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 313 | 34 | 1.28 | 4.52 | 23.70 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 337 | 39 | 1.58 | 2.76 | 34.01 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 133 | 0 | 2.74 | 8.69 | 16.52 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 371 | 0 | 1.91 | 2.72 | 9.96 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 79 | 18 | 10.59 | 15.11 | 18.69 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 325 | 24 | 1.28 | 4.74 | 18.04 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 352 | 22 | 1.16 | 3.00 | 20.26 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 79 | 34 | 10.54 | 15.05 | 17.65 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 325 | 35 | 1.28 | 4.83 | 23.70 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 352 | 45 | 1.58 | 3.06 | 34.01 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 141 | 0 | 2.74 | 8.69 | 16.53 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 387 | 0 | 1.91 | 2.68 | 9.77 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 55 | 18 | 10.46 | 15.04 | 24.35 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 363 | 28 | 1.28 | 5.84 | 18.04 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 452 | 42 | 1.23 | 3.18 | 29.24 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 55 | 20 | 10.40 | 14.87 | 17.54 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 363 | 44 | 1.28 | 5.80 | 23.70 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 452 | 95 | 1.58 | 4.14 | 34.01 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 176 | 4 | 2.38 | 6.26 | 17.52 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 368 | 0 | 1.37 | 3.23 | 5.50 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 61 | 8 | 10.76 | 16.12 | 17.51 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 25 | 0 | 2.05 | 4.28 | 7.76 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 597 | 30 | 1.19 | 3.35 | 18.10 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 617 | 18 | 1.04 | 2.56 | 18.20 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 61 | 26 | 10.84 | 16.12 | 17.51 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 25 | 0 | 2.88 | 4.29 | 7.29 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 597 | 41 | 1.23 | 3.53 | 25.78 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 617 | 101 | 1.60 | 2.89 | 34.07 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 155 | 0 | 2.94 | 7.77 | 16.81 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 325 | 0 | 1.56 | 3.17 | 6.93 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 82 | 36 | 12.51 | 16.45 | 17.13 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 32 | 0 | 1.75 | 4.62 | 14.23 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 386 | 20 | 1.15 | 4.76 | 17.88 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 436 | 17 | 1.10 | 3.04 | 17.51 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 82 | 36 | 12.98 | 16.47 | 17.74 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 32 | 0 | 3.00 | 4.68 | 14.23 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 386 | 30 | 1.28 | 4.97 | 23.76 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 436 | 69 | 1.58 | 4.48 | 34.00 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 17 | 0 | 1.43 | 1.82 | 2.57 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 59 | 5 | 2.02 | 7.88 | 18.23 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 102 | 0 | 1.25 | 1.25 | 2.23 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 68 | 0 | 1.20 | 1.34 | 1.69 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 174 | 0 | 1.13 | 4.01 | 14.61 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 429 | 9 | 1.25 | 3.30 | 18.33 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `thermal` | 285 | 0 | 3.97 | 8.90 | 13.22 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 244 | 22 | 1.06 | 1.59 | 19.28 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 174 | 8 | 1.08 | 1.69 | 22.67 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 429 | 15 | 1.15 | 3.25 | 19.08 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `thermal` | 285 | 96 | 3.97 | 8.75 | 25.72 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 244 | 60 | 1.78 | 2.23 | 37.96 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 216 | 6 | 2.35 | 6.78 | 17.32 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 448 | 0 | 1.69 | 3.11 | 9.41 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 50 | 4 | 10.16 | 16.52 | 17.06 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 41 | 0 | 1.29 | 3.09 | 6.16 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 697 | 30 | 1.19 | 3.52 | 18.35 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 526 | 17 | 1.09 | 3.26 | 19.47 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 50 | 6 | 10.23 | 16.67 | 17.06 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 41 | 0 | 2.02 | 3.21 | 4.79 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 697 | 42 | 1.23 | 4.05 | 23.23 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 526 | 78 | 1.60 | 2.90 | 34.08 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 137 | 0 | 2.74 | 8.65 | 16.51 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 367 | 0 | 2.09 | 2.69 | 7.67 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 76 | 20 | 11.18 | 16.12 | 17.10 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 37 | 0 | 1.11 | 2.77 | 4.03 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 292 | 24 | 1.28 | 4.77 | 18.02 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 315 | 17 | 1.10 | 3.62 | 18.01 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 76 | 34 | 11.60 | 16.14 | 17.67 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 37 | 0 | 1.93 | 2.88 | 4.03 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 292 | 33 | 1.29 | 4.81 | 23.70 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 315 | 34 | 1.66 | 4.29 | 34.01 |
| `n6_vs_a100` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 49 | 0 | 1.39 | 2.47 | 9.78 |
| `n6_vs_a100` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 103 | 8 | 1.65 | 7.49 | 18.28 |
| `n6_vs_a100` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 248 | 0 | 1.15 | 1.20 | 2.61 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 4 | 4 | 19.40 | 19.92 | 19.92 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 479 | 0 | 1.01 | 5.96 | 12.15 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 400 | 8 | 1.25 | 2.91 | 18.26 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 183 | 2 | 1.15 | 1.70 | 17.63 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `compute` | 4 | 4 | 19.40 | 19.92 | 19.92 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 479 | 18 | 1.08 | 5.88 | 17.10 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 400 | 10 | 1.15 | 2.91 | 19.08 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 183 | 28 | 1.78 | 2.23 | 37.82 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 27 | 0 | 1.19 | 1.60 | 2.73 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 117 | 5 | 1.22 | 2.12 | 18.24 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 55 | 0 | 1.10 | 1.16 | 1.63 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 56 | 0 | 1.16 | 1.18 | 1.23 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 3 | 3 | 17.51 | 17.84 | 18.21 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 184 | 1 | 1.01 | 1.70 | 17.07 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 422 | 8 | 1.15 | 2.33 | 18.16 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `thermal` | 281 | 0 | 1.23 | 3.18 | 12.58 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 240 | 16 | 1.02 | 1.19 | 17.54 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `compute` | 3 | 3 | 17.51 | 17.84 | 18.21 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 184 | 5 | 1.03 | 1.20 | 27.03 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 422 | 14 | 1.12 | 2.40 | 19.08 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `thermal` | 281 | 22 | 1.23 | 3.31 | 27.22 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 240 | 56 | 1.78 | 2.23 | 37.96 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 79 | 0 | 1.50 | 2.53 | 9.97 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 173 | 8 | 1.26 | 2.53 | 18.28 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 128 | 0 | 1.15 | 1.17 | 1.36 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 5 | 4 | 16.24 | 17.48 | 18.47 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 535 | 0 | 1.01 | 2.21 | 9.84 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 403 | 8 | 1.15 | 2.15 | 18.08 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 181 | 0 | 1.04 | 1.25 | 16.92 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `compute` | 5 | 4 | 16.24 | 17.48 | 18.47 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 535 | 16 | 1.03 | 2.29 | 17.10 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 403 | 10 | 1.11 | 2.25 | 19.08 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 181 | 28 | 1.78 | 2.23 | 37.82 |

## Per model, per context, per batch and per design class

Each row is that class's **fastest** feasible design at that batch, read against the iso-area GPU comparator the published study already chose for it. The `densest` pick of every class is in `analytical.json` beside it.

**The ROM-versus-GPU ratio under speculation is `T_cycle(GPU) / T_cycle(ROM)` and carries no `tau` at all.** The acceptance length is a property of the model and its drafter, not of the machine, so it is the same on both sides and cancels out of the ratio. Every movement in the last column is therefore a machine effect and nothing else.

### `n5_vs_b200-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-tensor-x352-romfill` | 1,686.2 | 2,645.0-4,909.5 | 2.70 | yes | `b200_sxm-x179-tensor` | 1,411.0 | 2,022.7-3,754.4 | 2.96 | yes | 1.195x | 1.308x | 1.094x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 4,069.8 | 7,524.1-13,965.7 | 2.29 | yes | `b200_sxm-x58-tensor` | 1,356.9 | 1,623.9-3,014.3 | 3.54 | yes | 2.999x | 4.633x | 1.545x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x352-romfill` | 1,554.1 | 1,643.6-3,050.7 | 4.01 | yes | `b200_sxm-x179-tensor` | 1,275.2 | 1,340.3-2,487.7 | 4.03 | yes | 1.219x | 1.226x | 1.006x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4,069.8 | 7,332.5-13,610.0 | 2.35 | yes | `b200_sxm-x58-tensor` | 1,194.7 | 1,136.9-2,110.3 | 4.46 | yes | 3.407x | 6.449x | 1.893x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x91` | 1,452.3 | 163.3-303.2 | 37.70 | **no** | `b200_sxm-x46-tensor` | 976.6 | 715.1-1,327.4 | 5.79 | yes | 1.487x | 0.228x | 0.154x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4,068.7 | 5,745.4-10,664.3 | 3.00 | yes | `b200_sxm-x58-tensor` | 993.9 | 735.0-1,364.3 | 5.73 | yes | 4.094x | 7.817x | 1.909x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x91` | 1,452.3 | 163.3-303.2 | 37.70 | **no** | `b200_sxm-x46-tensor` | 751.9 | 443.5-823.2 | 7.19 | yes | 1.931x | 0.368x | 0.191x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4,066.4 | 4,044.5-7,507.1 | 4.26 | yes | `b200_sxm-x58-tensor` | 767.0 | 446.1-828.0 | 7.29 | yes | 5.302x | 9.066x | 1.710x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x110` | 1,298.1 | 968.0-1,796.7 | 5.69 | yes | `b200_sxm-x56-tensor` | 544.8 | 259.3-481.2 | 8.91 | **no** | 2.383x | 3.734x | 1.567x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4,061.9 | 2,506.1-4,651.6 | 6.87 | yes | `b200_sxm-x58-tensor` | 543.6 | 255.9-475.0 | 9.01 | **no** | 7.472x | 9.793x | 1.311x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x110` | 1,288.5 | 679.7-1,261.7 | 8.04 | **no** | `b200_sxm-x56-hybrid` | 405.0 | 321.2-596.1 | 5.35 | yes | 3.182x | 2.117x | 0.665x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,722.8 | 1,385.6-2,571.8 | 11.39 | **no** | `b200_sxm-x58-hybrid` | 382.7 | 299.4-555.8 | 5.42 | yes | 9.729x | 4.628x | 0.476x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x110` | 1,269.6 | 427.9-794.3 | 12.58 | **no** | `b200_sxm-x56-hybrid` | 295.4 | 278.1-516.2 | 4.50 | yes | 4.298x | 1.539x | 0.358x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 3,662.7 | 1,562.7-2,900.7 | 9.94 | **no** | `b200_sxm-x87-hybrid` | 277.5 | 262.7-487.7 | 4.48 | yes | 13.200x | 5.948x | 0.451x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x132` | 1,030.0 | 240.8-447.0 | 18.14 | **no** | `b200_sxm-x67-hybrid` | 145.0 | 217.7-404.2 | 2.82 | yes | 7.101x | 1.106x | 0.156x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,022.3 | 1,409.6-2,616.4 | 9.09 | **no** | `b200_sxm-x347-hybrid` | 102.0 | 145.5-270.1 | 2.97 | yes | 29.640x | 9.688x | 0.327x |

**Does the ratio compress?** Of 16 class rows in this study, 8 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.154x to 1.909x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 16 ROM rows and 14 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x315-romfill` | 1,160.7 | 1,479.4-2,746.0 | 3.33 | yes | `a100_sxm_80gb-x311-tensor` | 751.8 | 954.4-1,771.5 | 3.34 | yes | 1.544x | 1.550x | 1.004x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 4,069.8 | 1,858.8-3,450.1 | 9.28 | **no** | `a100_sxm_80gb-x112-tensor` | 719.2 | 757.9-1,406.8 | 4.02 | yes | 5.659x | 2.452x | 0.433x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x143` | 1,027.6 | 829.0-1,538.7 | 5.26 | yes | `a100_sxm_80gb-x141-tensor` | 627.3 | 549.6-1,020.1 | 4.84 | yes | 1.638x | 1.508x | 0.921x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4,069.8 | 1,621.2-3,009.1 | 10.64 | **no** | `a100_sxm_80gb-x112-tensor` | 612.2 | 522.3-969.5 | 4.97 | yes | 6.647x | 3.104x | 0.467x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x118` | 974.9 | 137.1-254.4 | 30.15 | **no** | `a100_sxm_80gb-x116-tensor` | 480.4 | 337.2-625.9 | 6.04 | yes | 2.029x | 0.407x | 0.200x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4,059.7 | 1,174.7-2,180.3 | 14.65 | **no** | `a100_sxm_80gb-x112-tensor` | 478.7 | 335.7-623.0 | 6.05 | yes | 8.480x | 3.500x | 0.413x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x118` | 974.9 | 137.1-254.4 | 30.15 | **no** | `a100_sxm_80gb-x116-tensor` | 360.2 | 204.2-379.1 | 7.48 | yes | 2.706x | 0.671x | 0.248x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,456.6 | 4,611.7-8,560.0 | 3.18 | yes | `a100_sxm_80gb-x168-tensor` | 376.9 | 211.2-392.1 | 7.56 | yes | 9.172x | 21.833x | 2.380x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x118` | 974.0 | 133.3-247.4 | 30.99 | **no** | `a100_sxm_80gb-x116-tensor` | 248.6 | 117.2-217.6 | 8.99 | **no** | 3.919x | 1.137x | 0.290x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,452.3 | 3,061.7-5,682.9 | 4.78 | yes | `a100_sxm_80gb-x168-tensor` | 260.3 | 118.8-220.4 | 9.29 | **no** | 13.262x | 25.783x | 1.944x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x143` | 862.8 | 482.8-896.1 | 7.58 | yes | `a100_sxm_80gb-x141-tensor` | 164.8 | 63.7-118.2 | 10.97 | **no** | 5.236x | 7.578x | 1.447x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,443.6 | 1,793.0-3,328.1 | 8.14 | **no** | `a100_sxm_80gb-x168-tensor` | 168.2 | 63.7-118.2 | 11.20 | **no** | 20.475x | 28.154x | 1.375x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x143` | 844.5 | 315.6-585.7 | 11.35 | **no** | `a100_sxm_80gb-x141-tensor` | 100.8 | 33.0-61.3 | 12.94 | **no** | 8.376x | 9.550x | 1.140x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 3,169.3 | 1,495.5-2,775.9 | 8.99 | **no** | `a100_sxm_80gb-x224-tensor` | 105.0 | 32.8-60.8 | 13.59 | **no** | 30.173x | 45.651x | 1.513x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x170` | 676.3 | 172.4-320.0 | 16.63 | **no** | `a100_sxm_80gb-x168-hybrid` | 35.0 | 48.3-89.6 | 3.07 | yes | 19.316x | 3.570x | 0.185x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,715.4 | 1,069.0-1,984.2 | 10.77 | **no** | `a100_sxm_80gb-x672-tensor` | 33.8 | 8.2-15.3 | 17.39 | **no** | 80.414x | 129.822x | 1.614x |

**Does the ratio compress?** Of 16 class rows in this study, 8 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.185x to 2.380x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 5 of 16 ROM rows and 9 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x55` | 2,058.0 | 839.8-1,558.8 | 10.39 | **no** | `b200_sxm-x28-tensor` | 1,287.0 | 1,889.9-3,507.9 | 2.89 | yes | 1.599x | 0.444x | 0.278x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 5,037.3 | 11,502.8-21,350.7 | 1.86 | yes | `b200_sxm-x29-tensor` | 1,291.8 | 1,905.3-3,536.5 | 2.87 | yes | 3.899x | 6.037x | 1.548x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x55` | 2,058.0 | 839.8-1,558.8 | 10.39 | **no** | `b200_sxm-x28-tensor` | 1,120.7 | 1,240.5-2,302.6 | 3.83 | yes | 1.836x | 0.677x | 0.369x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 5,037.3 | 8,183.8-15,190.3 | 2.61 | yes | `b200_sxm-x29-tensor` | 1,125.8 | 1,251.2-2,322.4 | 3.81 | yes | 4.475x | 6.541x | 1.462x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x55` | 2,058.0 | 839.8-1,558.8 | 10.39 | **no** | `b200_sxm-x28-hybrid` | 948.0 | 1,089.5-2,022.2 | 3.69 | yes | 2.171x | 0.771x | 0.355x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 5,019.4 | 5,189.3-9,632.0 | 4.10 | yes | `b200_sxm-x29-hybrid` | 958.7 | 1,110.1-2,060.6 | 3.66 | yes | 5.236x | 4.674x | 0.893x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x55` | 1,927.3 | 744.2-1,381.4 | 10.98 | **no** | `b200_sxm-x28-hybrid` | 734.2 | 751.2-1,394.4 | 4.14 | yes | 2.625x | 0.991x | 0.377x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,401.1 | 9,406.6-17,459.8 | 1.98 | yes | `b200_sxm-x58-tensor` | 767.0 | 472.9-877.9 | 6.88 | yes | 5.738x | 19.889x | 3.466x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x57` | 1,885.8 | 735.0-1,364.2 | 10.88 | **no** | `b200_sxm-x29-hybrid` | 558.6 | 550.4-1,021.6 | 4.30 | yes | 3.376x | 1.335x | 0.396x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,395.9 | 6,490.5-12,047.2 | 2.87 | yes | `b200_sxm-x58-tensor` | 543.6 | 264.5-491.0 | 8.71 | **no** | 8.086x | 24.536x | 3.034x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x68` | 1,732.3 | 1,192.2-2,213.0 | 6.16 | yes | `b200_sxm-x35-hybrid` | 395.5 | 422.8-784.8 | 3.97 | yes | 4.380x | 2.820x | 0.644x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,385.3 | 4,006.4-7,436.5 | 4.64 | yes | `b200_sxm-x58-hybrid` | 382.7 | 430.7-799.4 | 3.77 | yes | 11.460x | 9.302x | 0.812x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x68` | 1,690.4 | 650.2-1,206.8 | 11.02 | **no** | `b200_sxm-x35-hybrid` | 278.1 | 362.9-673.5 | 3.25 | yes | 6.078x | 1.792x | 0.295x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 4,186.5 | 3,113.5-5,779.1 | 5.70 | yes | `b200_sxm-x87-hybrid` | 277.5 | 348.0-646.0 | 3.38 | yes | 15.087x | 8.946x | 0.593x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x216-romfill` | 1,340.0 | 773.2-1,435.1 | 7.35 | yes | `b200_sxm-x110-hybrid` | 144.4 | 251.7-467.2 | 2.43 | yes | 9.281x | 3.072x | 0.331x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,369.2 | 2,554.0-4,740.5 | 5.59 | yes | `b200_sxm-x347-hybrid` | 102.0 | 168.4-312.6 | 2.57 | yes | 33.042x | 15.164x | 0.459x |

**Does the ratio compress?** Of 16 class rows in this study, 12 move the ROM-versus-GPU ratio DOWN under speculation and 4 move it UP. The movement spans 0.278x to 3.466x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 10 of 16 ROM rows and 15 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x72` | 1,279.8 | 764.1-1,418.3 | 7.10 | yes | `a100_sxm_80gb-x71-tensor` | 693.2 | 880.9-1,635.1 | 3.34 | yes | 1.846x | 0.867x | 0.470x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4,069.8 | 12,286.5-22,805.4 | 1.40 | yes | `a100_sxm_80gb-x112-tensor` | 719.2 | 942.6-1,749.6 | 3.23 | yes | 5.659x | 13.035x | 2.303x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x72` | 1,279.8 | 764.1-1,418.3 | 7.10 | yes | `a100_sxm_80gb-x71-tensor` | 578.3 | 567.1-1,052.6 | 4.32 | yes | 2.213x | 1.347x | 0.609x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4,069.8 | 12,286.5-22,805.4 | 1.40 | yes | `a100_sxm_80gb-x112-tensor` | 612.2 | 603.9-1,120.9 | 4.30 | yes | 6.647x | 20.346x | 3.061x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x72` | 1,279.8 | 764.1-1,418.3 | 7.10 | yes | `a100_sxm_80gb-x71-tensor` | 453.2 | 349.8-649.3 | 5.49 | yes | 2.824x | 2.184x | 0.773x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4,068.7 | 10,230.3-18,988.8 | 1.69 | yes | `a100_sxm_80gb-x112-tensor` | 478.7 | 367.5-682.2 | 5.52 | yes | 8.499x | 27.834x | 3.275x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x72` | 1,279.8 | 764.1-1,418.3 | 7.10 | yes | `a100_sxm_80gb-x71-tensor` | 334.5 | 209.5-388.9 | 6.77 | yes | 3.826x | 3.647x | 0.953x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4,066.4 | 7,545.5-14,005.4 | 2.29 | yes | `a100_sxm_80gb-x112-tensor` | 358.7 | 215.2-399.4 | 7.07 | yes | 11.335x | 35.063x | 3.093x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x87` | 1,152.1 | 1,486.3-2,758.7 | 3.29 | yes | `a100_sxm_80gb-x86-tensor` | 237.7 | 120.7-224.0 | 8.35 | **no** | 4.847x | 12.314x | 2.540x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4,061.9 | 4,948.3-9,184.6 | 3.48 | yes | `a100_sxm_80gb-x112-tensor` | 247.6 | 121.0-224.6 | 8.68 | **no** | 16.406x | 40.902x | 2.493x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x87` | 1,130.8 | 883.5-1,639.9 | 5.43 | yes | `a100_sxm_80gb-x86-tensor` | 154.0 | 65.5-121.6 | 9.96 | **no** | 7.345x | 13.486x | 1.836x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4,052.9 | 2,930.7-5,439.8 | 5.86 | yes | `a100_sxm_80gb-x112-tensor` | 160.1 | 65.0-120.7 | 10.44 | **no** | 25.310x | 45.077x | 1.781x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x87` | 1,090.4 | 487.8-905.5 | 9.48 | **no** | `a100_sxm_80gb-x86-tensor` | 95.3 | 34.2-63.6 | 11.80 | **no** | 11.437x | 14.247x | 1.246x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 3,808.0 | 2,946.6-5,469.3 | 5.48 | yes | `a100_sxm_80gb-x224-tensor` | 105.0 | 33.0-61.2 | 13.50 | **no** | 36.254x | 89.329x | 2.464x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x340-romfill` | 817.6 | 622.9-1,156.3 | 5.57 | yes | `a100_sxm_80gb-x335-tensor` | 33.5 | 8.3-15.4 | 17.05 | **no** | 24.434x | 74.875x | 3.064x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,038.1 | 2,026.4-3,761.2 | 6.36 | yes | `a100_sxm_80gb-x672-tensor` | 33.8 | 8.3-15.3 | 17.35 | **no** | 89.972x | 245.525x | 2.729x |

**Does the ratio compress?** Of 16 class rows in this study, 4 move the ROM-versus-GPU ratio DOWN under speculation and 12 move it UP. The movement spans 0.470x to 3.275x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 15 of 16 ROM rows and 8 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hybrid-x51` | 2,058.0 | 858.1-1,592.8 | 10.17 | **no** | `b200_sxm-x26-tensor` | 1,276.3 | 1,856.8-3,446.4 | 2.91 | yes | 1.612x | 0.462x | 0.287x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 5,037.3 | 11,866.5-22,025.9 | 1.80 | yes | `b200_sxm-x29-tensor` | 1,291.8 | 1,905.3-3,536.5 | 2.87 | yes | 3.899x | 6.228x | 1.597x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x55` | 2,058.0 | 839.8-1,558.8 | 10.39 | **no** | `b200_sxm-x28-tensor` | 1,120.7 | 1,240.5-2,302.6 | 3.83 | yes | 1.836x | 0.677x | 0.369x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 5,037.3 | 8,183.8-15,190.3 | 2.61 | yes | `b200_sxm-x29-tensor` | 1,125.8 | 1,251.2-2,322.4 | 3.81 | yes | 4.475x | 6.541x | 1.462x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x55` | 2,058.0 | 839.8-1,558.8 | 10.39 | **no** | `b200_sxm-x28-hybrid` | 948.0 | 1,089.5-2,022.2 | 3.69 | yes | 2.171x | 0.771x | 0.355x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 5,019.4 | 5,189.3-9,632.0 | 4.10 | yes | `b200_sxm-x29-hybrid` | 958.7 | 1,110.1-2,060.6 | 3.66 | yes | 5.236x | 4.674x | 0.893x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x55` | 1,927.3 | 744.2-1,381.4 | 10.98 | **no** | `b200_sxm-x28-hybrid` | 734.2 | 751.2-1,394.4 | 4.14 | yes | 2.625x | 0.991x | 0.377x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,401.1 | 9,406.6-17,459.8 | 1.98 | yes | `b200_sxm-x58-tensor` | 767.0 | 472.9-877.9 | 6.88 | yes | 5.738x | 19.889x | 3.466x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x57` | 1,885.8 | 735.0-1,364.2 | 10.88 | **no** | `b200_sxm-x29-hybrid` | 558.6 | 550.4-1,021.6 | 4.30 | yes | 3.376x | 1.335x | 0.396x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,395.9 | 6,490.5-12,047.2 | 2.87 | yes | `b200_sxm-x58-tensor` | 543.6 | 264.5-491.0 | 8.71 | **no** | 8.086x | 24.536x | 3.034x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x68` | 1,732.3 | 1,192.2-2,213.0 | 6.16 | yes | `b200_sxm-x35-hybrid` | 395.5 | 422.8-784.8 | 3.97 | yes | 4.380x | 2.820x | 0.644x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,385.3 | 4,006.4-7,436.5 | 4.64 | yes | `b200_sxm-x58-hybrid` | 382.7 | 430.7-799.4 | 3.77 | yes | 11.460x | 9.302x | 0.812x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x68` | 1,690.4 | 650.2-1,206.8 | 11.02 | **no** | `b200_sxm-x35-hybrid` | 278.1 | 362.9-673.5 | 3.25 | yes | 6.078x | 1.792x | 0.295x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 4,186.5 | 3,113.5-5,779.1 | 5.70 | yes | `b200_sxm-x87-hybrid` | 277.5 | 348.0-646.0 | 3.38 | yes | 15.087x | 8.946x | 0.593x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x216-romfill` | 1,340.0 | 773.2-1,435.1 | 7.35 | yes | `b200_sxm-x110-hybrid` | 144.4 | 251.7-467.2 | 2.43 | yes | 9.281x | 3.072x | 0.331x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,369.2 | 2,554.0-4,740.5 | 5.59 | yes | `b200_sxm-x347-hybrid` | 102.0 | 168.4-312.6 | 2.57 | yes | 33.042x | 15.164x | 0.459x |

**Does the ratio compress?** Of 16 class rows in this study, 12 move the ROM-versus-GPU ratio DOWN under speculation and 4 move it UP. The movement spans 0.287x to 3.466x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 10 of 16 ROM rows and 15 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x66` | 1,279.8 | 635.5-1,179.6 | 8.54 | **no** | `a100_sxm_80gb-x65-tensor` | 686.7 | 864.6-1,604.9 | 3.37 | yes | 1.864x | 0.735x | 0.394x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 4,069.8 | 12,286.5-22,805.4 | 1.40 | yes | `a100_sxm_80gb-x112-tensor` | 719.2 | 942.6-1,749.6 | 3.23 | yes | 5.659x | 13.035x | 2.303x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x72` | 1,279.8 | 764.1-1,418.3 | 7.10 | yes | `a100_sxm_80gb-x71-tensor` | 578.3 | 567.1-1,052.6 | 4.32 | yes | 2.213x | 1.347x | 0.609x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4,069.8 | 12,286.5-22,805.4 | 1.40 | yes | `a100_sxm_80gb-x112-tensor` | 612.2 | 603.9-1,120.9 | 4.30 | yes | 6.647x | 20.346x | 3.061x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x72` | 1,279.8 | 764.1-1,418.3 | 7.10 | yes | `a100_sxm_80gb-x71-tensor` | 453.2 | 349.8-649.3 | 5.49 | yes | 2.824x | 2.184x | 0.773x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4,068.7 | 10,230.3-18,988.8 | 1.69 | yes | `a100_sxm_80gb-x112-tensor` | 478.7 | 367.5-682.2 | 5.52 | yes | 8.499x | 27.834x | 3.275x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x72` | 1,279.8 | 764.1-1,418.3 | 7.10 | yes | `a100_sxm_80gb-x71-tensor` | 334.5 | 209.5-388.9 | 6.77 | yes | 3.826x | 3.647x | 0.953x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4,066.4 | 7,545.5-14,005.4 | 2.29 | yes | `a100_sxm_80gb-x112-tensor` | 358.7 | 215.2-399.4 | 7.07 | yes | 11.335x | 35.063x | 3.093x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x87` | 1,152.1 | 1,486.3-2,758.7 | 3.29 | yes | `a100_sxm_80gb-x86-tensor` | 237.7 | 120.7-224.0 | 8.35 | **no** | 4.847x | 12.314x | 2.540x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4,061.9 | 4,948.3-9,184.6 | 3.48 | yes | `a100_sxm_80gb-x112-tensor` | 247.6 | 121.0-224.6 | 8.68 | **no** | 16.406x | 40.902x | 2.493x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x87` | 1,130.8 | 883.5-1,639.9 | 5.43 | yes | `a100_sxm_80gb-x86-tensor` | 154.0 | 65.5-121.6 | 9.96 | **no** | 7.345x | 13.486x | 1.836x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4,052.9 | 2,930.7-5,439.8 | 5.86 | yes | `a100_sxm_80gb-x112-tensor` | 160.1 | 65.0-120.7 | 10.44 | **no** | 25.310x | 45.077x | 1.781x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x87` | 1,090.4 | 487.8-905.5 | 9.48 | **no** | `a100_sxm_80gb-x86-tensor` | 95.3 | 34.2-63.6 | 11.80 | **no** | 11.437x | 14.247x | 1.246x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 3,808.0 | 2,946.6-5,469.3 | 5.48 | yes | `a100_sxm_80gb-x224-tensor` | 105.0 | 33.0-61.2 | 13.50 | **no** | 36.254x | 89.329x | 2.464x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x340-romfill` | 817.6 | 622.9-1,156.3 | 5.57 | yes | `a100_sxm_80gb-x335-tensor` | 33.5 | 8.3-15.4 | 17.05 | **no** | 24.434x | 74.875x | 3.064x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,038.3 | 2,026.4-3,761.2 | 6.36 | yes | `a100_sxm_80gb-x672-tensor` | 33.8 | 8.3-15.3 | 17.35 | **no** | 89.979x | 245.525x | 2.729x |

**Does the ratio compress?** Of 16 class rows in this study, 4 move the ROM-versus-GPU ratio DOWN under speculation and 12 move it UP. The movement spans 0.394x to 3.275x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 14 of 16 ROM rows and 8 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,374.7 | 1,450.6-2,692.4 | 6.94 | yes | `b200_sxm-x19-tensor` | 1,232.8 | 2,057.3-3,818.6 | 2.54 | yes | 1.926x | 0.705x | 0.366x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 4,824.6 | 11,336.2-21,041.5 | 1.80 | yes | `b200_sxm-x29-tensor` | 1,290.0 | 2,191.9-4,068.4 | 2.50 | yes | 3.740x | 5.172x | 1.383x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,374.7 | 1,450.6-2,692.4 | 6.94 | yes | `b200_sxm-x19-hybrid` | 1,157.2 | 1,485.9-2,758.0 | 3.30 | yes | 2.052x | 0.976x | 0.476x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 4,315.7 | 10,607.3-19,688.5 | 1.73 | yes | `b200_sxm-x87-tensor` | 1,244.9 | 1,584.8-2,941.7 | 3.33 | yes | 3.467x | 6.693x | 1.931x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,374.7 | 1,450.6-2,692.4 | 6.94 | yes | `b200_sxm-x19-hybrid` | 1,050.1 | 1,283.1-2,381.6 | 3.47 | yes | 2.262x | 1.131x | 0.500x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,223.6 | 10,434.5-19,367.8 | 1.72 | yes | `b200_sxm-x116-tensor` | 1,077.7 | 978.9-1,817.0 | 4.67 | yes | 3.919x | 10.659x | 2.720x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,175.9 | 961.6-1,784.8 | 9.59 | **no** | `b200_sxm-x19-hybrid` | 802.6 | 925.7-1,718.2 | 3.68 | yes | 2.711x | 1.039x | 0.383x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,891.3 | 9,796.3-18,183.3 | 1.68 | yes | `b200_sxm-x231-tensor` | 894.5 | 558.9-1,037.4 | 6.79 | yes | 4.350x | 17.528x | 4.029x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 2,069.1 | 878.7-1,630.9 | 9.98 | **no** | `b200_sxm-x22-hybrid` | 620.6 | 800.7-1,486.3 | 3.29 | yes | 3.334x | 1.097x | 0.329x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,425.1 | 8,229.9-15,275.9 | 1.76 | yes | `b200_sxm-x347-tensor` | 668.3 | 298.8-554.6 | 9.48 | **no** | 5.125x | 27.545x | 5.375x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x87-romfill` | 2,038.5 | 1,010.2-1,875.1 | 8.56 | **no** | `b200_sxm-x44-hybrid` | 463.0 | 644.6-1,196.5 | 3.05 | yes | 4.402x | 1.567x | 0.356x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,849.2 | 5,738.9-10,652.2 | 2.11 | yes | `b200_sxm-x347-tensor` | 442.3 | 154.9-287.6 | 12.11 | **no** | 6.442x | 37.045x | 5.751x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 1,909.1 | 961.6-1,784.9 | 8.42 | **no** | `b200_sxm-x87-hybrid` | 333.8 | 515.8-957.4 | 2.74 | yes | 5.720x | 1.864x | 0.326x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,132.2 | 3,574.9-6,635.5 | 2.53 | yes | `b200_sxm-x347-tensor` | 268.7 | 78.9-146.5 | 14.43 | **no** | 7.936x | 45.297x | 5.708x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 1,287.2 | 486.0-902.1 | 11.23 | **no** | `b200_sxm-x173-hybrid` | 163.8 | 327.6-608.1 | 2.12 | yes | 7.858x | 1.484x | 0.189x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 849.5 | 1,746.9-3,242.4 | 2.06 | yes | `b200_sxm-x347-hybrid` | 129.4 | 243.6-452.1 | 2.25 | yes | 6.563x | 7.172x | 1.093x |

**Does the ratio compress?** Of 16 class rows in this study, 8 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.189x to 5.751x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 16 ROM rows and 13 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hybrid-x29` | 2,627.4 | 2,023.4-3,755.7 | 5.51 | yes | `b200_sxm-x15-hybrid` | 1,476.2 | 1,884.8-3,498.5 | 3.32 | yes | 1.780x | 1.074x | 0.603x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 4,855.8 | 16,171.3-30,016.1 | 1.27 | yes | `b200_sxm-x29-tensor` | 1,303.0 | 2,200.7-4,084.7 | 2.51 | yes | 3.727x | 7.348x | 1.972x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 2,627.4 | 1,860.5-3,453.3 | 5.99 | yes | `b200_sxm-x16-hybrid` | 1,510.3 | 1,955.8-3,630.2 | 3.27 | yes | 1.740x | 0.951x | 0.547x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,849.3 | 14,198.7-26,354.6 | 1.45 | yes | `b200_sxm-x29-tensor` | 1,165.2 | 1,497.7-2,779.9 | 3.30 | yes | 4.162x | 9.480x | 2.278x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 2,627.4 | 1,860.5-3,453.3 | 5.99 | yes | `b200_sxm-x16-hybrid` | 1,230.1 | 1,391.8-2,583.4 | 3.75 | yes | 2.136x | 1.337x | 0.626x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,849.3 | 11,452.7-21,257.8 | 1.80 | yes | `b200_sxm-x29-hybrid` | 1,123.0 | 1,458.2-2,706.6 | 3.27 | yes | 4.318x | 7.854x | 1.819x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,365.6 | 2,797.7-5,192.9 | 3.59 | yes | `b200_sxm-x19-hybrid` | 868.5 | 945.2-1,754.4 | 3.90 | yes | 2.724x | 2.960x | 1.087x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,849.3 | 8,258.5-15,328.8 | 2.49 | yes | `b200_sxm-x29-hybrid` | 892.1 | 1,057.1-1,962.2 | 3.58 | yes | 5.436x | 7.812x | 1.437x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,341.6 | 1,639.9-3,043.9 | 6.05 | yes | `b200_sxm-x19-hybrid` | 646.9 | 751.3-1,394.5 | 3.65 | yes | 3.620x | 2.183x | 0.603x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,725.1 | 5,301.3-9,839.9 | 3.78 | yes | `b200_sxm-x29-hybrid` | 686.8 | 814.6-1,512.0 | 3.57 | yes | 6.880x | 6.508x | 0.946x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 2,109.5 | 1,456.3-2,703.1 | 6.14 | yes | `b200_sxm-x22-hybrid` | 496.2 | 732.3-1,359.3 | 2.87 | yes | 4.251x | 1.989x | 0.468x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 4,534.7 | 6,165.2-11,443.5 | 3.12 | yes | `b200_sxm-x87-hybrid` | 454.8 | 630.1-1,169.5 | 3.06 | yes | 9.971x | 9.785x | 0.981x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x87-romfill` | 1,994.8 | 1,576.3-2,925.9 | 5.37 | yes | `b200_sxm-x44-hybrid` | 367.7 | 590.4-1,095.8 | 2.64 | yes | 5.424x | 2.670x | 0.492x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,291.8 | 4,544.1-8,434.4 | 4.00 | yes | `b200_sxm-x116-hybrid` | 319.5 | 480.2-891.4 | 2.82 | yes | 13.431x | 9.462x | 0.705x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 1,761.1 | 796.8-1,479.0 | 9.37 | **no** | `b200_sxm-x87-hybrid` | 198.0 | 433.5-804.6 | 1.94 | yes | 8.892x | 1.838x | 0.207x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,382.1 | 3,065.1-5,689.1 | 4.68 | yes | `b200_sxm-x347-hybrid` | 132.3 | 245.9-456.5 | 2.28 | yes | 25.570x | 12.464x | 0.487x |

**Does the ratio compress?** Of 16 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 5 move it UP. The movement spans 0.207x to 2.278x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 15 of 16 ROM rows and 16 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hybrid-x28` | 2,627.4 | 1,402.7-2,603.5 | 7.94 | **no** | `b200_sxm-x14-hybrid` | 1,441.3 | 1,811.1-3,361.7 | 3.37 | yes | 1.823x | 0.774x | 0.425x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 4,856.6 | 16,340.2-30,329.5 | 1.26 | yes | `b200_sxm-x29-tensor` | 1,303.3 | 2,200.9-4,085.1 | 2.51 | yes | 3.726x | 7.424x | 1.992x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 2,627.4 | 1,978.5-3,672.4 | 5.63 | yes | `b200_sxm-x16-hybrid` | 1,511.9 | 1,956.4-3,631.4 | 3.28 | yes | 1.738x | 1.011x | 0.582x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,849.3 | 14,456.7-26,833.6 | 1.42 | yes | `b200_sxm-x29-tensor` | 1,165.8 | 1,497.9-2,780.3 | 3.30 | yes | 4.160x | 9.651x | 2.320x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 2,627.4 | 1,978.5-3,672.4 | 5.63 | yes | `b200_sxm-x16-hybrid` | 1,232.3 | 1,392.4-2,584.6 | 3.75 | yes | 2.132x | 1.421x | 0.666x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,849.3 | 11,792.3-21,888.1 | 1.74 | yes | `b200_sxm-x29-hybrid` | 1,124.0 | 1,458.6-2,707.3 | 3.27 | yes | 4.314x | 8.085x | 1.874x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,365.6 | 2,940.3-5,457.6 | 3.41 | yes | `b200_sxm-x19-hybrid` | 870.3 | 945.7-1,755.3 | 3.90 | yes | 2.718x | 3.109x | 1.144x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,849.3 | 8,616.3-15,993.0 | 2.39 | yes | `b200_sxm-x29-hybrid` | 893.4 | 1,057.6-1,963.0 | 3.58 | yes | 5.428x | 8.147x | 1.501x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,341.6 | 1,738.8-3,227.4 | 5.71 | yes | `b200_sxm-x19-hybrid` | 648.9 | 751.9-1,395.7 | 3.66 | yes | 3.608x | 2.312x | 0.641x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,781.8 | 5,599.9-10,394.1 | 3.62 | yes | `b200_sxm-x29-hybrid` | 688.2 | 815.1-1,512.9 | 3.58 | yes | 6.948x | 6.870x | 0.989x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,177.0 | 956.8-1,776.0 | 9.65 | **no** | `b200_sxm-x19-hybrid` | 462.3 | 668.1-1,240.0 | 2.93 | yes | 4.709x | 1.432x | 0.304x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,577.4 | 5,039.3-9,353.7 | 3.85 | yes | `b200_sxm-x58-hybrid` | 480.3 | 631.9-1,172.9 | 3.22 | yes | 9.531x | 7.975x | 0.837x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 2,032.5 | 844.8-1,568.1 | 10.20 | **no** | `b200_sxm-x22-hybrid` | 351.2 | 670.5-1,244.6 | 2.22 | yes | 5.788x | 1.260x | 0.218x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,343.8 | 4,787.1-8,885.5 | 3.85 | yes | `b200_sxm-x116-hybrid` | 319.9 | 480.4-891.7 | 2.82 | yes | 13.580x | 9.965x | 0.734x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 1,784.6 | 857.3-1,591.3 | 8.83 | **no** | `b200_sxm-x87-hybrid` | 198.7 | 434.2-806.0 | 1.94 | yes | 8.981x | 1.974x | 0.220x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,428.5 | 3,223.9-5,984.0 | 4.51 | yes | `b200_sxm-x347-hybrid` | 132.3 | 246.0-456.6 | 2.28 | yes | 25.906x | 13.106x | 0.506x |

**Does the ratio compress?** Of 16 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 5 move it UP. The movement spans 0.218x to 2.320x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 12 of 16 ROM rows and 16 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 1,062.6 | 1,458.4-2,707.0 | 3.09 | yes | `b200_sxm-x173-tensor` | 773.9 | 1,084.0-2,012.1 | 3.03 | yes | 1.373x | 1.345x | 0.980x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 2,648.8 | 4,953.5-9,194.3 | 2.27 | yes | `b200_sxm-x87-tensor` | 748.5 | 1,019.2-1,891.8 | 3.11 | yes | 3.539x | 4.860x | 1.373x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 951.6 | 861.5-1,599.1 | 4.68 | yes | `b200_sxm-x173-tensor` | 678.4 | 683.4-1,268.5 | 4.21 | yes | 1.403x | 1.261x | 0.899x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.8 | 4,837.8-8,979.6 | 2.32 | yes | `b200_sxm-x87-tensor` | 640.8 | 647.1-1,201.1 | 4.20 | yes | 4.133x | 7.476x | 1.809x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x161` | 857.6 | 292.8-543.5 | 12.42 | **no** | `b200_sxm-x82-tensor` | 506.4 | 386.1-716.6 | 5.56 | yes | 1.693x | 0.758x | 0.448x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.3 | 4,094.5-7,599.9 | 2.74 | yes | `b200_sxm-x87-tensor` | 509.8 | 389.1-722.3 | 5.56 | yes | 5.194x | 10.522x | 2.026x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x161` | 857.6 | 292.8-543.5 | 12.42 | **no** | `b200_sxm-x82-tensor` | 377.7 | 223.7-415.2 | 7.16 | yes | 2.271x | 1.309x | 0.576x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,646.5 | 2,535.9-4,707.0 | 4.42 | yes | `b200_sxm-x87-tensor` | 381.0 | 225.0-417.6 | 7.18 | yes | 6.946x | 11.271x | 1.623x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x161` | 857.6 | 292.8-543.5 | 12.42 | **no** | `b200_sxm-x82-tensor` | 259.4 | 124.7-231.4 | 8.82 | **no** | 3.306x | 2.348x | 0.710x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,426.5 | 1,439.8-2,672.5 | 7.15 | yes | `b200_sxm-x87-tensor` | 261.9 | 125.1-232.3 | 8.87 | **no** | 9.265x | 11.506x | 1.242x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 825.3 | 411.7-764.2 | 8.50 | **no** | `b200_sxm-x87-tensor` | 167.5 | 66.8-123.9 | 10.64 | **no** | 4.927x | 6.166x | 1.251x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 2,364.4 | 2,040.5-3,787.5 | 4.91 | yes | `b200_sxm-x116-tensor` | 172.3 | 65.8-122.1 | 11.11 | **no** | 13.724x | 31.029x | 2.261x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x193` | 742.3 | 464.4-862.1 | 6.78 | yes | `b200_sxm-x98-tensor` | 102.2 | 34.1-63.4 | 12.69 | **no** | 7.265x | 13.602x | 1.872x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 2,219.3 | 1,764.5-3,275.2 | 5.33 | yes | `b200_sxm-x173-tensor` | 106.4 | 33.3-61.9 | 13.53 | **no** | 20.859x | 52.936x | 2.538x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227` | 627.5 | 222.3-412.6 | 11.97 | **no** | `b200_sxm-x116-hybrid` | 50.6 | 90.0-167.1 | 2.38 | yes | 12.393x | 2.469x | 0.199x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,613.7 | 922.8-1,712.9 | 7.41 | yes | `b200_sxm-x347-hybrid` | 36.3 | 60.8-112.8 | 2.53 | yes | 44.422x | 15.181x | 0.342x |

**Does the ratio compress?** Of 16 class rows in this study, 7 move the ROM-versus-GPU ratio DOWN under speculation and 9 move it UP. The movement spans 0.199x to 2.538x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 16 ROM rows and 10 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 1,062.6 | 1,458.8-2,707.7 | 3.09 | yes | `b200_sxm-x173-tensor` | 774.1 | 1,084.1-2,012.2 | 3.03 | yes | 1.373x | 1.346x | 0.980x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 2,648.8 | 5,615.8-10,423.7 | 2.00 | yes | `b200_sxm-x87-tensor` | 748.9 | 1,019.4-1,892.1 | 3.11 | yes | 3.537x | 5.509x | 1.558x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 952.4 | 864.2-1,604.0 | 4.67 | yes | `b200_sxm-x173-tensor` | 678.7 | 683.5-1,268.7 | 4.21 | yes | 1.403x | 1.264x | 0.901x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.8 | 5,438.5-10,094.7 | 2.07 | yes | `b200_sxm-x87-tensor` | 641.3 | 647.2-1,201.3 | 4.20 | yes | 4.130x | 8.403x | 2.035x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x160` | 888.6 | 328.7-610.1 | 11.46 | **no** | `b200_sxm-x82-tensor` | 507.1 | 386.2-716.8 | 5.57 | yes | 1.752x | 0.851x | 0.486x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.3 | 4,677.5-8,682.1 | 2.40 | yes | `b200_sxm-x87-tensor` | 510.5 | 389.2-722.5 | 5.56 | yes | 5.188x | 12.017x | 2.317x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x160` | 888.6 | 328.7-610.1 | 11.46 | **no** | `b200_sxm-x82-tensor` | 378.5 | 223.7-415.3 | 7.17 | yes | 2.348x | 1.469x | 0.626x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,646.5 | 2,999.0-5,566.5 | 3.74 | yes | `b200_sxm-x87-tensor` | 381.8 | 225.1-417.7 | 7.19 | yes | 6.932x | 13.325x | 1.922x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x160` | 888.6 | 328.7-610.1 | 11.46 | **no** | `b200_sxm-x82-tensor` | 260.1 | 124.7-231.5 | 8.84 | **no** | 3.416x | 2.636x | 0.772x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,619.5 | 1,745.9-3,240.7 | 6.36 | yes | `b200_sxm-x87-tensor` | 262.6 | 125.2-232.3 | 8.90 | **no** | 9.975x | 13.948x | 1.398x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 825.3 | 498.5-925.3 | 7.02 | yes | `b200_sxm-x87-tensor` | 168.1 | 66.8-124.0 | 10.67 | **no** | 4.910x | 7.464x | 1.520x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 2,364.4 | 2,419.5-4,490.9 | 4.14 | yes | `b200_sxm-x116-tensor` | 172.7 | 65.8-122.1 | 11.14 | **no** | 13.687x | 36.783x | 2.687x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 814.4 | 268.6-498.6 | 12.86 | **no** | `b200_sxm-x87-tensor` | 101.9 | 34.6-64.2 | 12.50 | **no** | 7.992x | 7.770x | 0.972x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 2,351.7 | 1,384.7-2,570.2 | 7.20 | yes | `b200_sxm-x116-tensor` | 104.0 | 33.9-62.9 | 13.01 | **no** | 22.622x | 40.862x | 1.806x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227` | 627.5 | 266.3-494.3 | 9.99 | **no** | `b200_sxm-x116-hybrid` | 50.9 | 90.3-167.6 | 2.39 | yes | 12.316x | 2.950x | 0.240x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,991.3 | 1,103.4-2,048.1 | 7.65 | yes | `b200_sxm-x347-hybrid` | 36.4 | 60.8-112.9 | 2.54 | yes | 54.735x | 18.142x | 0.331x |

**Does the ratio compress?** Of 16 class rows in this study, 8 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.240x to 2.687x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 16 ROM rows and 10 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 1,062.6 | 1,458.8-2,707.8 | 3.09 | yes | `b200_sxm-x173-tensor` | 774.1 | 1,084.1-2,012.3 | 3.03 | yes | 1.373x | 1.346x | 0.980x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 2,648.8 | 5,725.4-10,627.1 | 1.96 | yes | `b200_sxm-x87-tensor` | 748.9 | 1,019.4-1,892.2 | 3.11 | yes | 3.537x | 5.616x | 1.588x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 952.8 | 864.7-1,604.9 | 4.67 | yes | `b200_sxm-x173-tensor` | 678.8 | 683.5-1,268.7 | 4.21 | yes | 1.404x | 1.265x | 0.901x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.8 | 5,539.7-10,282.3 | 2.03 | yes | `b200_sxm-x87-tensor` | 641.4 | 647.2-1,201.4 | 4.20 | yes | 4.130x | 8.559x | 2.073x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x157` | 888.6 | 317.0-588.3 | 11.89 | **no** | `b200_sxm-x80-tensor` | 506.8 | 387.4-719.0 | 5.55 | yes | 1.753x | 0.818x | 0.467x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.3 | 4,777.5-8,867.8 | 2.35 | yes | `b200_sxm-x87-tensor` | 510.6 | 389.2-722.5 | 5.56 | yes | 5.187x | 12.274x | 2.366x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x157` | 888.6 | 317.0-588.3 | 11.89 | **no** | `b200_sxm-x80-tensor` | 378.3 | 224.9-417.4 | 7.13 | yes | 2.349x | 1.410x | 0.600x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,646.5 | 3,081.7-5,720.0 | 3.64 | yes | `b200_sxm-x87-tensor` | 381.9 | 225.1-417.8 | 7.19 | yes | 6.930x | 13.692x | 1.976x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x157` | 888.6 | 317.0-588.3 | 11.89 | **no** | `b200_sxm-x80-tensor` | 260.2 | 125.6-233.1 | 8.79 | **no** | 3.414x | 2.524x | 0.739x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,643.0 | 1,802.2-3,345.2 | 6.22 | yes | `b200_sxm-x87-tensor` | 262.7 | 125.2-232.3 | 8.90 | **no** | 10.061x | 14.397x | 1.431x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 825.3 | 649.4-1,205.4 | 5.39 | yes | `b200_sxm-x87-tensor` | 168.2 | 66.8-124.0 | 10.67 | **no** | 4.908x | 9.723x | 1.981x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 2,364.4 | 2,487.4-4,616.9 | 4.03 | yes | `b200_sxm-x116-tensor` | 172.8 | 65.8-122.1 | 11.14 | **no** | 13.682x | 37.814x | 2.764x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 814.4 | 358.4-665.2 | 9.64 | **no** | `b200_sxm-x87-tensor` | 102.0 | 34.6-64.2 | 12.50 | **no** | 7.987x | 10.366x | 1.298x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 2,351.7 | 1,429.4-2,653.1 | 6.98 | yes | `b200_sxm-x116-tensor` | 104.0 | 33.9-62.9 | 13.01 | **no** | 22.611x | 42.178x | 1.865x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227` | 627.5 | 294.9-547.3 | 9.02 | **no** | `b200_sxm-x116-hybrid` | 51.0 | 90.3-167.6 | 2.39 | yes | 12.304x | 3.265x | 0.265x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,008.8 | 1,136.9-2,110.2 | 7.49 | yes | `b200_sxm-x347-hybrid` | 36.4 | 60.8-112.9 | 2.54 | yes | 55.203x | 18.690x | 0.339x |

**Does the ratio compress?** Of 16 class rows in this study, 7 move the ROM-versus-GPU ratio DOWN under speculation and 9 move it UP. The movement spans 0.265x to 2.764x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 16 ROM rows and 10 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x48` | 1,449.0 | 1,021.8-1,896.5 | 6.01 | yes | `a100_sxm_80gb-x47-tensor` | 699.8 | 980.0-1,819.0 | 3.03 | yes | 2.071x | 1.043x | 0.504x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 4,707.9 | 8,495.2-15,768.2 | 2.35 | yes | `a100_sxm_80gb-x56-tensor` | 715.0 | 1,010.1-1,874.9 | 3.00 | yes | 6.585x | 8.410x | 1.277x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 1,449.0 | 934.9-1,735.3 | 6.57 | yes | `a100_sxm_80gb-x46-tensor` | 584.2 | 646.1-1,199.3 | 3.83 | yes | 2.480x | 1.447x | 0.583x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 3,388.5 | 8,976.1-16,660.8 | 1.60 | yes | `a100_sxm_80gb-x168-tensor` | 684.0 | 750.0-1,392.1 | 3.87 | yes | 4.954x | 11.968x | 2.416x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 1,449.0 | 934.9-1,735.3 | 6.57 | yes | `a100_sxm_80gb-x46-tensor` | 463.5 | 413.0-766.7 | 4.76 | yes | 3.126x | 2.263x | 0.724x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 3,331.4 | 8,852.1-16,430.6 | 1.60 | yes | `a100_sxm_80gb-x224-tensor` | 565.2 | 464.1-861.4 | 5.16 | yes | 5.895x | 19.074x | 3.236x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 1,366.3 | 1,206.1-2,238.6 | 4.80 | yes | `a100_sxm_80gb-x55-tensor` | 355.3 | 256.9-476.9 | 5.86 | yes | 3.846x | 4.694x | 1.221x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,121.2 | 8,388.5-15,570.1 | 1.58 | yes | `a100_sxm_80gb-x448-tensor` | 391.8 | 262.4-487.0 | 6.33 | yes | 7.966x | 31.971x | 4.013x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 1,290.9 | 677.9-1,258.3 | 8.07 | **no** | `a100_sxm_80gb-x55-tensor` | 245.8 | 145.4-269.8 | 7.17 | yes | 5.252x | 4.663x | 0.888x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,656.1 | 6,973.9-12,944.5 | 1.61 | yes | `a100_sxm_80gb-x672-tensor` | 298.2 | 142.7-264.9 | 8.86 | **no** | 8.908x | 48.874x | 5.487x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x111-romfill` | 1,211.2 | 831.8-1,544.0 | 6.17 | yes | `a100_sxm_80gb-x110-tensor` | 182.6 | 74.8-138.8 | 10.35 | **no** | 6.635x | 11.125x | 1.677x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,922.9 | 4,648.1-8,627.6 | 1.75 | yes | `a100_sxm_80gb-x672-tensor` | 201.6 | 74.4-138.1 | 11.48 | **no** | 9.540x | 62.461x | 6.547x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x170-romfill` | 1,149.9 | 647.3-1,201.4 | 7.53 | yes | `a100_sxm_80gb-x168-tensor` | 118.5 | 37.9-70.3 | 13.26 | **no** | 9.707x | 17.088x | 1.760x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,238.9 | 3,132.4-5,814.2 | 1.68 | yes | `a100_sxm_80gb-x672-tensor` | 124.3 | 38.0-70.5 | 13.88 | **no** | 9.966x | 82.491x | 8.277x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x340-romfill` | 746.5 | 324.5-602.3 | 9.75 | **no** | `a100_sxm_80gb-x335-tensor` | 38.4 | 9.6-17.7 | 17.03 | **no** | 19.450x | 33.958x | 1.746x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 395.3 | 1,304.6-2,421.6 | 1.28 | yes | `a100_sxm_80gb-x672-tensor` | 39.0 | 9.6-17.8 | 17.27 | **no** | 10.133x | 136.252x | 13.447x |

**Does the ratio compress?** Of 16 class rows in this study, 4 move the ROM-versus-GPU ratio DOWN under speculation and 12 move it UP. The movement spans 0.504x to 13.447x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 14 of 16 ROM rows and 9 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x37` | 1,539.7 | 1,199.6-2,226.5 | 5.44 | yes | `a100_sxm_80gb-x37-tensor` | 687.1 | 938.5-1,742.0 | 3.10 | yes | 2.241x | 1.278x | 0.570x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 4,707.9 | 14,576.0-27,055.1 | 1.37 | yes | `a100_sxm_80gb-x56-tensor` | 723.1 | 1,013.9-1,881.9 | 3.02 | yes | 6.511x | 14.376x | 2.208x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 1,539.7 | 1,241.2-2,303.9 | 5.26 | yes | `a100_sxm_80gb-x39-tensor` | 583.2 | 633.9-1,176.7 | 3.90 | yes | 2.640x | 1.958x | 0.742x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 4,707.9 | 12,068.6-22,400.9 | 1.65 | yes | `a100_sxm_80gb-x56-tensor` | 614.5 | 670.9-1,245.2 | 3.88 | yes | 7.662x | 17.990x | 2.348x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 1,539.7 | 1,241.2-2,303.9 | 5.26 | yes | `a100_sxm_80gb-x39-tensor` | 467.8 | 409.8-760.7 | 4.84 | yes | 3.292x | 3.029x | 0.920x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 4,707.9 | 9,032.7-16,765.8 | 2.21 | yes | `a100_sxm_80gb-x56-tensor` | 495.2 | 425.7-790.2 | 4.93 | yes | 9.508x | 21.217x | 2.232x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 1,443.6 | 1,952.0-3,623.2 | 3.14 | yes | `a100_sxm_80gb-x46-tensor` | 360.8 | 257.4-477.8 | 5.94 | yes | 4.001x | 7.584x | 1.895x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 4,707.9 | 6,009.3-11,154.0 | 3.32 | yes | `a100_sxm_80gb-x56-tensor` | 373.5 | 259.6-481.9 | 6.10 | yes | 12.604x | 23.146x | 1.836x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 1,422.2 | 1,175.1-2,181.1 | 5.13 | yes | `a100_sxm_80gb-x46-tensor` | 253.7 | 150.2-278.9 | 7.16 | yes | 5.606x | 7.821x | 1.395x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,406.4 | 6,078.9-11,283.2 | 3.07 | yes | `a100_sxm_80gb-x112-tensor` | 290.7 | 146.0-270.9 | 8.45 | **no** | 15.155x | 41.644x | 2.748x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 1,316.1 | 1,036.6-1,924.1 | 5.38 | yes | `a100_sxm_80gb-x55-tensor` | 174.7 | 81.1-150.5 | 9.13 | **no** | 7.535x | 12.787x | 1.697x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 4,205.0 | 5,846.3-10,851.5 | 3.05 | yes | `a100_sxm_80gb-x224-tensor` | 204.7 | 75.8-140.8 | 11.44 | **no** | 20.543x | 77.094x | 3.753x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x57` | 1,203.9 | 600.8-1,115.2 | 8.50 | **no** | `a100_sxm_80gb-x56-tensor` | 112.3 | 42.1-78.2 | 11.30 | **no** | 10.720x | 14.255x | 1.330x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill` | 3,915.3 | 4,639.5-8,611.5 | 3.58 | yes | `a100_sxm_80gb-x336-tensor` | 122.6 | 38.4-71.2 | 13.55 | **no** | 31.935x | 120.926x | 3.787x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 1,028.9 | 586.0-1,087.7 | 7.44 | yes | `a100_sxm_80gb-x224-hybrid` | 42.4 | 81.3-150.8 | 2.21 | yes | 24.290x | 7.212x | 0.297x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,899.7 | 2,459.9-4,565.9 | 5.00 | yes | `a100_sxm_80gb-x672-tensor` | 39.5 | 9.7-17.9 | 17.33 | **no** | 73.359x | 254.371x | 3.467x |

**Does the ratio compress?** Of 16 class rows in this study, 4 move the ROM-versus-GPU ratio DOWN under speculation and 12 move it UP. The movement spans 0.297x to 3.787x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 15 of 16 ROM rows and 10 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x37` | 1,539.7 | 1,301.7-2,416.2 | 5.02 | yes | `a100_sxm_80gb-x37-tensor` | 687.3 | 938.6-1,742.2 | 3.10 | yes | 2.240x | 1.387x | 0.619x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 4,707.9 | 14,804.6-27,479.3 | 1.35 | yes | `a100_sxm_80gb-x56-tensor` | 723.3 | 1,014.0-1,882.1 | 3.02 | yes | 6.509x | 14.600x | 2.243x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 1,539.7 | 1,315.2-2,441.1 | 4.96 | yes | `a100_sxm_80gb-x39-tensor` | 583.6 | 634.0-1,176.9 | 3.90 | yes | 2.639x | 2.074x | 0.786x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 4,707.9 | 12,378.3-22,975.8 | 1.61 | yes | `a100_sxm_80gb-x56-tensor` | 614.8 | 671.0-1,245.4 | 3.89 | yes | 7.658x | 18.449x | 2.409x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 1,539.7 | 1,315.2-2,441.1 | 4.96 | yes | `a100_sxm_80gb-x39-tensor` | 468.3 | 409.9-760.9 | 4.84 | yes | 3.288x | 3.208x | 0.976x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 4,707.9 | 9,384.1-17,418.2 | 2.13 | yes | `a100_sxm_80gb-x56-tensor` | 495.6 | 425.8-790.3 | 4.93 | yes | 9.500x | 22.039x | 2.320x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 1,455.3 | 894.3-1,659.9 | 6.90 | yes | `a100_sxm_80gb-x39-tensor` | 350.7 | 257.4-477.7 | 5.78 | yes | 4.149x | 3.475x | 0.837x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 4,707.9 | 6,324.5-11,739.1 | 3.16 | yes | `a100_sxm_80gb-x56-tensor` | 374.0 | 259.7-482.0 | 6.11 | yes | 12.589x | 24.355x | 1.935x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 1,422.2 | 1,238.4-2,298.6 | 4.87 | yes | `a100_sxm_80gb-x46-tensor` | 254.2 | 150.3-279.0 | 7.17 | yes | 5.595x | 8.240x | 1.473x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,406.4 | 6,379.3-11,840.9 | 2.93 | yes | `a100_sxm_80gb-x112-tensor` | 291.0 | 146.0-271.0 | 8.45 | **no** | 15.141x | 43.698x | 2.886x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 1,316.1 | 1,088.3-2,020.0 | 5.13 | yes | `a100_sxm_80gb-x55-tensor` | 175.1 | 81.1-150.5 | 9.15 | **no** | 7.518x | 13.420x | 1.785x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,312.9 | 3,921.1-7,278.0 | 4.66 | yes | `a100_sxm_80gb-x112-tensor` | 192.3 | 77.4-143.7 | 10.53 | **no** | 22.434x | 50.638x | 2.257x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 1,230.1 | 604.4-1,121.8 | 8.63 | **no** | `a100_sxm_80gb-x55-tensor` | 112.2 | 42.3-78.4 | 11.26 | **no** | 10.961x | 14.302x | 1.305x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 4,104.9 | 3,766.6-6,991.4 | 4.62 | yes | `a100_sxm_80gb-x224-tensor` | 125.6 | 38.8-72.1 | 13.71 | **no** | 32.692x | 96.977x | 2.966x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 1,040.2 | 620.3-1,151.4 | 7.11 | yes | `a100_sxm_80gb-x224-hybrid` | 42.4 | 81.3-150.9 | 2.21 | yes | 24.530x | 7.630x | 0.311x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,227.7 | 2,591.6-4,810.4 | 5.28 | yes | `a100_sxm_80gb-x672-tensor` | 39.5 | 9.7-18.0 | 17.33 | **no** | 81.627x | 267.922x | 3.282x |

**Does the ratio compress?** Of 16 class rows in this study, 5 move the ROM-versus-GPU ratio DOWN under speculation and 11 move it UP. The movement spans 0.311x to 3.282x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 15 of 16 ROM rows and 10 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x194` | 725.7 | 722.5-1,341.1 | 4.26 | yes | `a100_sxm_80gb-x191-tensor` | 355.1 | 451.9-838.7 | 3.33 | yes | 2.044x | 1.599x | 0.782x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 2,375.7 | 4,118.6-7,644.6 | 2.45 | yes | `a100_sxm_80gb-x224-tensor` | 358.3 | 461.4-856.3 | 3.29 | yes | 6.630x | 8.927x | 1.346x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x227` | 626.1 | 435.6-808.6 | 6.09 | yes | `a100_sxm_80gb-x224-tensor` | 307.4 | 294.6-546.8 | 4.42 | yes | 2.037x | 1.479x | 0.726x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,375.7 | 4,030.7-7,481.5 | 2.50 | yes | `a100_sxm_80gb-x224-tensor` | 307.4 | 294.6-546.8 | 4.42 | yes | 7.729x | 13.681x | 1.770x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x208` | 578.9 | 216.3-401.4 | 11.35 | **no** | `a100_sxm_80gb-x205-tensor` | 230.8 | 176.7-328.1 | 5.54 | yes | 2.508x | 1.224x | 0.488x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,375.7 | 4,030.7-7,481.5 | 2.50 | yes | `a100_sxm_80gb-x224-tensor` | 233.7 | 178.3-331.0 | 5.56 | yes | 10.167x | 22.602x | 2.223x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x208` | 578.9 | 216.3-401.4 | 11.35 | **no** | `a100_sxm_80gb-x205-tensor` | 170.1 | 103.0-191.2 | 7.00 | yes | 3.405x | 2.100x | 0.617x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,374.1 | 2,552.8-4,738.2 | 3.94 | yes | `a100_sxm_80gb-x224-tensor` | 171.8 | 103.6-192.3 | 7.03 | yes | 13.822x | 24.645x | 1.783x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x208` | 578.9 | 216.3-401.4 | 11.35 | **no** | `a100_sxm_80gb-x205-tensor` | 116.3 | 57.6-106.9 | 8.57 | **no** | 4.977x | 3.757x | 0.755x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,370.9 | 1,472.7-2,733.6 | 6.83 | yes | `a100_sxm_80gb-x224-tensor` | 117.8 | 57.7-107.1 | 8.66 | **no** | 20.124x | 25.519x | 1.268x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 546.6 | 429.0-796.3 | 5.40 | yes | `a100_sxm_80gb-x224-tensor` | 76.0 | 30.8-57.2 | 10.45 | **no** | 7.196x | 13.924x | 1.935x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,961.6 | 2,261.6-4,197.9 | 3.68 | yes | `a100_sxm_80gb-x336-tensor` | 76.5 | 30.7-56.9 | 10.58 | **no** | 25.635x | 73.747x | 2.877x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 536.4 | 236.7-439.3 | 9.61 | **no** | `a100_sxm_80gb-x224-tensor` | 46.4 | 16.0-29.6 | 12.34 | **no** | 11.558x | 14.838x | 1.284x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,831.2 | 2,179.5-4,045.4 | 3.56 | yes | `a100_sxm_80gb-x672-tensor` | 49.5 | 15.7-29.2 | 13.32 | **no** | 37.010x | 138.378x | 3.739x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x297` | 416.0 | 175.9-326.5 | 10.03 | **no** | `a100_sxm_80gb-x293-tensor` | 15.4 | 4.0-7.5 | 16.19 | **no** | 26.950x | 43.521x | 1.615x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 961.1 | 951.7-1,766.5 | 4.28 | yes | `a100_sxm_80gb-x672-tensor` | 15.6 | 4.0-7.4 | 16.52 | **no** | 61.480x | 237.145x | 3.857x |

**Does the ratio compress?** Of 16 class rows in this study, 5 move the ROM-versus-GPU ratio DOWN under speculation and 11 move it UP. The movement spans 0.488x to 3.857x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 16 ROM rows and 8 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x191` | 725.9 | 721.7-1,339.7 | 4.26 | yes | `a100_sxm_80gb-x188-tensor` | 354.9 | 450.9-836.8 | 3.34 | yes | 2.045x | 1.601x | 0.783x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 2,375.7 | 4,700.6-8,725.0 | 2.14 | yes | `a100_sxm_80gb-x224-tensor` | 358.4 | 461.4-856.4 | 3.29 | yes | 6.628x | 10.188x | 1.537x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x227` | 626.1 | 439.9-816.5 | 6.03 | yes | `a100_sxm_80gb-x224-tensor` | 307.6 | 294.7-546.9 | 4.43 | yes | 2.036x | 1.493x | 0.733x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,375.7 | 4,566.2-8,475.5 | 2.21 | yes | `a100_sxm_80gb-x224-tensor` | 307.6 | 294.7-546.9 | 4.43 | yes | 7.724x | 15.497x | 2.006x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 581.5 | 217.7-404.1 | 11.33 | **no** | `a100_sxm_80gb-x203-tensor` | 230.7 | 176.6-327.7 | 5.54 | yes | 2.520x | 1.233x | 0.489x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,375.7 | 4,566.2-8,475.5 | 2.21 | yes | `a100_sxm_80gb-x224-tensor` | 233.9 | 178.4-331.1 | 5.56 | yes | 10.158x | 25.601x | 2.520x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 581.5 | 217.7-404.1 | 11.33 | **no** | `a100_sxm_80gb-x203-tensor` | 170.1 | 102.9-191.0 | 7.01 | yes | 3.419x | 2.115x | 0.619x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,374.1 | 2,998.1-5,564.9 | 3.36 | yes | `a100_sxm_80gb-x224-tensor` | 172.0 | 103.6-192.3 | 7.04 | yes | 13.803x | 28.939x | 2.097x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 581.5 | 217.7-404.1 | 11.33 | **no** | `a100_sxm_80gb-x203-tensor` | 116.4 | 57.5-106.8 | 8.57 | **no** | 4.997x | 3.783x | 0.757x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,370.9 | 1,777.4-3,299.0 | 5.66 | yes | `a100_sxm_80gb-x224-tensor` | 118.0 | 57.7-107.1 | 8.67 | **no** | 20.087x | 30.791x | 1.533x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 546.6 | 506.4-939.9 | 4.58 | yes | `a100_sxm_80gb-x224-tensor` | 76.1 | 30.8-57.2 | 10.48 | **no** | 7.179x | 16.433x | 2.289x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,016.9 | 979.6-1,818.3 | 8.73 | **no** | `a100_sxm_80gb-x224-tensor` | 76.1 | 30.8-57.2 | 10.48 | **no** | 26.490x | 31.789x | 1.200x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 536.4 | 284.7-528.5 | 7.99 | **no** | `a100_sxm_80gb-x224-tensor` | 46.5 | 16.0-29.6 | 12.37 | **no** | 11.524x | 17.844x | 1.548x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,951.9 | 1,576.9-2,926.9 | 5.25 | yes | `a100_sxm_80gb-x336-tensor` | 47.2 | 15.8-29.4 | 12.64 | **no** | 41.366x | 99.615x | 2.408x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x297` | 416.0 | 206.2-382.8 | 8.55 | **no** | `a100_sxm_80gb-x293-tensor` | 15.5 | 4.1-7.5 | 16.19 | **no** | 26.870x | 50.884x | 1.894x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,758.1 | 841.2-1,561.5 | 8.86 | **no** | `a100_sxm_80gb-x672-tensor` | 15.7 | 4.0-7.5 | 16.52 | **no** | 112.323x | 209.445x | 1.865x |

**Does the ratio compress?** Of 16 class rows in this study, 5 move the ROM-versus-GPU ratio DOWN under speculation and 11 move it UP. The movement spans 0.489x to 2.520x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 9 of 16 ROM rows and 8 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x191` | 725.9 | 725.9-1,347.4 | 4.24 | yes | `a100_sxm_80gb-x188-tensor` | 354.9 | 450.9-836.9 | 3.34 | yes | 2.045x | 1.610x | 0.787x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 2,375.7 | 4,798.1-8,906.0 | 2.10 | yes | `a100_sxm_80gb-x224-tensor` | 358.4 | 461.4-856.4 | 3.29 | yes | 6.628x | 10.399x | 1.569x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x227` | 626.1 | 440.5-817.7 | 6.03 | yes | `a100_sxm_80gb-x224-tensor` | 307.6 | 294.7-546.9 | 4.43 | yes | 2.035x | 1.495x | 0.734x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,375.7 | 4,657.2-8,644.3 | 2.16 | yes | `a100_sxm_80gb-x224-tensor` | 307.6 | 294.7-546.9 | 4.43 | yes | 7.723x | 15.805x | 2.046x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 587.0 | 225.2-418.0 | 11.05 | **no** | `a100_sxm_80gb-x203-tensor` | 230.8 | 176.6-327.7 | 5.54 | yes | 2.544x | 1.276x | 0.501x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,375.7 | 4,657.2-8,644.3 | 2.16 | yes | `a100_sxm_80gb-x224-tensor` | 233.9 | 178.4-331.1 | 5.56 | yes | 10.157x | 26.110x | 2.571x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 587.0 | 225.2-418.0 | 11.05 | **no** | `a100_sxm_80gb-x203-tensor` | 170.1 | 102.9-191.0 | 7.01 | yes | 3.450x | 2.188x | 0.634x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,374.1 | 3,077.0-5,711.4 | 3.27 | yes | `a100_sxm_80gb-x224-tensor` | 172.0 | 103.6-192.3 | 7.04 | yes | 13.800x | 29.699x | 2.152x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 587.0 | 225.2-418.0 | 11.05 | **no** | `a100_sxm_80gb-x203-tensor` | 116.4 | 57.6-106.8 | 8.58 | **no** | 5.042x | 3.913x | 0.776x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,370.9 | 1,833.1-3,402.5 | 5.48 | yes | `a100_sxm_80gb-x224-tensor` | 118.1 | 57.7-107.1 | 8.67 | **no** | 20.081x | 31.756x | 1.581x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 546.6 | 520.2-965.6 | 4.45 | yes | `a100_sxm_80gb-x224-tensor` | 76.2 | 30.8-57.2 | 10.48 | **no** | 7.176x | 16.880x | 2.352x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2,052.2 | 1,013.6-1,881.4 | 8.58 | **no** | `a100_sxm_80gb-x224-tensor` | 76.2 | 30.8-57.2 | 10.48 | **no** | 26.945x | 32.890x | 1.221x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 536.4 | 293.5-544.7 | 7.75 | yes | `a100_sxm_80gb-x224-tensor` | 46.6 | 16.0-29.6 | 12.37 | **no** | 11.519x | 18.392x | 1.597x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,951.9 | 1,624.0-3,014.3 | 5.10 | yes | `a100_sxm_80gb-x336-tensor` | 47.2 | 15.8-29.4 | 12.64 | **no** | 41.354x | 102.585x | 2.481x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x297` | 416.0 | 218.3-405.2 | 8.08 | **no** | `a100_sxm_80gb-x293-tensor` | 15.5 | 4.1-7.5 | 16.19 | **no** | 26.858x | 53.838x | 2.005x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,776.5 | 867.6-1,610.4 | 8.68 | **no** | `a100_sxm_80gb-x672-tensor` | 15.7 | 4.0-7.5 | 16.53 | **no** | 113.474x | 216.013x | 1.904x |

**Does the ratio compress?** Of 16 class rows in this study, 5 move the ROM-versus-GPU ratio DOWN under speculation and 11 move it UP. The movement spans 0.501x to 2.571x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 10 of 16 ROM rows and 8 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-pipeline-x8-romfill` | 5,027.2 | 1,208.6-2,243.4 | 17.64 | **no** | `b200_sxm-x4-tensor` | 1,232.0 | 4,299.1-7,979.7 | 1.22 | yes | 4.080x | 0.281x | 0.069x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | 19,432.8-36,069.8 | 1.41 | yes | `b200_sxm-x29-hybrid` | 1,866.3 | 6,329.8-11,748.9 | 1.25 | yes | 3.464x | 3.070x | 0.886x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x16-romfill` | 4,528.6 | 6,169.2-11,450.8 | 3.11 | yes | `b200_sxm-x8-tensor` | 1,917.0 | 6,318.0-11,727.0 | 1.29 | yes | 2.362x | 0.976x | 0.413x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,400.8 | 18,357.8-34,074.5 | 1.25 | yes | `b200_sxm-x58-hybrid` | 1,836.2 | 6,129.1-11,376.3 | 1.27 | yes | 2.941x | 2.995x | 1.018x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x57-romfill` | 4,191.8 | 5,473.0-10,158.7 | 3.25 | yes | `b200_sxm-x29-hybrid` | 1,866.3 | 6,329.8-11,748.9 | 1.25 | yes | 2.246x | 0.865x | 0.385x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 5,121.2 | 17,343.8-32,192.3 | 1.25 | yes | `b200_sxm-x116-hybrid` | 1,858.0 | 6,021.0-11,175.7 | 1.31 | yes | 2.756x | 2.881x | 1.045x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x57-romfill` | 4,191.8 | 5,473.0-10,158.7 | 3.25 | yes | `b200_sxm-x29-hybrid` | 1,773.8 | 5,741.8-10,657.6 | 1.31 | yes | 2.363x | 0.953x | 0.403x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,640.7 | 15,618.3-28,989.7 | 1.26 | yes | `b200_sxm-x231-hybrid` | 1,787.5 | 5,509.2-10,225.7 | 1.38 | yes | 2.596x | 2.835x | 1.092x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x113-romfill` | 3,928.4 | 5,153.8-9,566.2 | 3.23 | yes | `b200_sxm-x58-hybrid` | 1,744.6 | 5,484.7-10,180.3 | 1.35 | yes | 2.252x | 0.940x | 0.417x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,040.9 | 13,172.1-24,449.2 | 1.30 | yes | `b200_sxm-x347-hybrid` | 1,730.2 | 5,222.9-9,694.4 | 1.40 | yes | 2.336x | 2.522x | 1.080x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227-romfill` | 3,503.0 | 4,686.6-8,699.0 | 3.17 | yes | `b200_sxm-x116-hybrid` | 1,754.1 | 5,172.9-9,601.5 | 1.44 | yes | 1.997x | 0.906x | 0.454x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,395.4 | 10,203.8-18,939.7 | 1.41 | yes | `b200_sxm-x347-hybrid` | 1,730.2 | 5,222.9-9,694.4 | 1.40 | yes | 1.962x | 1.954x | 0.996x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 3,145.5 | 3,627.6-6,733.4 | 3.68 | yes | `b200_sxm-x173-hybrid` | 1,657.6 | 4,361.0-8,094.6 | 1.61 | yes | 1.898x | 0.832x | 0.438x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,573.2 | 7,033.8-13,055.6 | 1.55 | yes | `b200_sxm-x347-hybrid` | 1,688.9 | 4,773.8-8,860.8 | 1.50 | yes | 1.524x | 1.473x | 0.967x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-pipeline-x340-romfill` | 2,343.2 | 1,168.4-2,168.7 | 8.50 | **no** | `b200_sxm-x173-hybrid` | 1,169.3 | 2,057.2-3,818.5 | 2.41 | yes | 2.004x | 0.568x | 0.283x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,049.1 | 2,448.8-4,545.2 | 1.82 | yes | `b200_sxm-x347-hybrid` | 1,374.0 | 2,615.1-4,854.0 | 2.23 | yes | 0.764x | 0.936x | 1.226x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hybrid-x30` | 2,627.4 | 1,734.6-3,219.6 | 6.42 | yes | `b200_sxm-x15-hybrid` | 1,465.1 | 1,880.5-3,490.5 | 3.30 | yes | 1.793x | 0.922x | 0.514x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 4,850.6 | 15,100.0-28,027.7 | 1.36 | yes | `b200_sxm-x29-tensor` | 1,300.7 | 2,199.1-4,081.9 | 2.51 | yes | 3.729x | 6.866x | 1.841x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x32` | 2,627.4 | 1,803.6-3,347.8 | 6.18 | yes | `b200_sxm-x16-hybrid` | 1,499.3 | 1,951.4-3,622.1 | 3.26 | yes | 1.752x | 0.924x | 0.527x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,849.3 | 12,661.0-23,500.6 | 1.62 | yes | `b200_sxm-x29-tensor` | 1,161.6 | 1,496.3-2,777.3 | 3.29 | yes | 4.175x | 8.462x | 2.027x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x32` | 2,627.4 | 1,803.6-3,347.8 | 6.18 | yes | `b200_sxm-x16-hybrid` | 1,215.6 | 1,387.4-2,575.2 | 3.72 | yes | 2.161x | 1.300x | 0.601x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 4,744.7 | 9,576.5-17,775.3 | 2.10 | yes | `b200_sxm-x29-hybrid` | 1,116.3 | 1,455.5-2,701.6 | 3.25 | yes | 4.250x | 6.579x | 1.548x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,365.6 | 2,103.3-3,904.0 | 4.77 | yes | `b200_sxm-x19-hybrid` | 856.3 | 941.7-1,748.0 | 3.86 | yes | 2.762x | 2.233x | 0.809x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,553.2 | 8,840.7-16,409.5 | 2.18 | yes | `b200_sxm-x58-tensor` | 832.4 | 569.7-1,057.4 | 6.20 | yes | 5.470x | 15.519x | 2.837x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 2,341.6 | 1,182.3-2,194.5 | 8.40 | **no** | `b200_sxm-x19-hybrid` | 633.5 | 747.0-1,386.5 | 3.60 | yes | 3.696x | 1.583x | 0.428x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4,346.7 | 8,496.1-15,769.8 | 2.17 | yes | `b200_sxm-x116-tensor` | 639.9 | 306.0-567.9 | 8.87 | **no** | 6.792x | 27.767x | 4.088x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 2,109.5 | 1,062.0-1,971.2 | 8.42 | **no** | `b200_sxm-x22-hybrid` | 482.7 | 725.2-1,346.1 | 2.82 | yes | 4.371x | 1.464x | 0.335x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,985.1 | 7,881.6-14,629.3 | 2.14 | yes | `b200_sxm-x231-tensor` | 440.6 | 156.4-290.2 | 11.95 | **no** | 9.045x | 50.410x | 5.573x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x87-romfill` | 1,994.8 | 1,181.7-2,193.4 | 7.16 | yes | `b200_sxm-x44-hybrid` | 360.3 | 585.8-1,087.3 | 2.61 | yes | 5.537x | 2.017x | 0.364x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,511.7 | 6,309.8-11,711.9 | 2.36 | yes | `b200_sxm-x347-tensor` | 271.2 | 79.0-146.6 | 14.56 | **no** | 12.950x | 79.900x | 6.170x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227-romfill` | 1,731.6 | 736.1-1,366.2 | 9.97 | **no** | `b200_sxm-x116-hybrid` | 184.7 | 385.5-715.6 | 2.03 | yes | 9.376x | 1.909x | 0.204x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,271.5 | 2,338.5-4,340.5 | 4.12 | yes | `b200_sxm-x347-hybrid` | 131.8 | 245.5-455.7 | 2.28 | yes | 17.239x | 9.525x | 0.553x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 1,062.3 | 1,444.2-2,680.6 | 3.12 | yes | `b200_sxm-x173-tensor` | 773.0 | 1,083.6-2,011.3 | 3.02 | yes | 1.374x | 1.333x | 0.970x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 2,648.8 | 3,000.0-5,568.4 | 3.74 | yes | `b200_sxm-x87-tensor` | 746.8 | 1,018.5-1,890.4 | 3.11 | yes | 3.547x | 2.946x | 0.830x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 951.6 | 851.1-1,579.8 | 4.74 | yes | `b200_sxm-x173-tensor` | 677.0 | 683.1-1,267.9 | 4.20 | yes | 1.406x | 1.246x | 0.886x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.8 | 3,165.0-5,874.7 | 3.55 | yes | `b200_sxm-x87-tensor` | 638.3 | 646.5-1,200.0 | 4.19 | yes | 4.150x | 4.896x | 1.180x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x167` | 843.5 | 275.5-511.4 | 12.98 | **no** | `b200_sxm-x85-tensor` | 505.3 | 387.5-719.3 | 5.53 | yes | 1.669x | 0.711x | 0.426x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,648.3 | 2,564.8-4,760.6 | 4.38 | yes | `b200_sxm-x87-tensor` | 506.7 | 388.7-721.5 | 5.53 | yes | 5.227x | 6.598x | 1.262x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x167` | 843.5 | 275.5-511.4 | 12.98 | **no** | `b200_sxm-x85-tensor` | 376.1 | 224.2-416.1 | 7.11 | yes | 2.243x | 1.229x | 0.548x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 2,374.1 | 3,416.8-6,342.1 | 2.95 | yes | `b200_sxm-x116-tensor` | 390.3 | 225.9-419.3 | 7.33 | yes | 6.082x | 15.124x | 2.487x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x167` | 843.5 | 275.5-511.4 | 12.98 | **no** | `b200_sxm-x85-tensor` | 257.5 | 124.8-231.6 | 8.75 | **no** | 3.275x | 2.208x | 0.674x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 2,233.4 | 3,024.2-5,613.4 | 3.13 | yes | `b200_sxm-x173-tensor` | 278.2 | 123.8-229.8 | 9.53 | **no** | 8.028x | 24.424x | 3.042x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x193` | 750.8 | 483.7-897.8 | 6.58 | yes | `b200_sxm-x98-tensor` | 166.8 | 66.0-122.5 | 10.71 | **no** | 4.502x | 7.326x | 1.627x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,086.5 | 2,899.0-5,380.8 | 3.05 | yes | `b200_sxm-x347-tensor` | 185.6 | 64.2-119.2 | 12.25 | **no** | 11.239x | 45.124x | 4.015x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x193` | 742.3 | 262.0-486.3 | 12.01 | **no** | `b200_sxm-x98-tensor` | 100.4 | 34.1-63.3 | 12.48 | **no** | 7.394x | 7.684x | 1.039x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,535.9 | 1,749.1-3,246.5 | 3.72 | yes | `b200_sxm-x347-tensor` | 109.5 | 32.8-60.8 | 14.16 | **no** | 14.032x | 53.378x | 3.804x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x308-romfill` | 561.1 | 203.5-377.8 | 11.69 | **no** | `b200_sxm-x157-hybrid` | 47.1 | 80.9-150.2 | 2.47 | yes | 11.914x | 2.515x | 0.211x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 594.5 | 832.1-1,544.6 | 3.03 | yes | `b200_sxm-x347-hybrid` | 36.1 | 60.6-112.5 | 2.52 | yes | 16.483x | 13.729x | 0.833x |

**Does the ratio compress?** Of 48 class rows in this study, 28 move the ROM-versus-GPU ratio DOWN under speculation and 20 move it UP. The movement spans 0.069x to 6.170x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 38 of 48 ROM rows and 39 of 48 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-pipeline-x8-romfill` | 3,524.3 | 855.3-1,587.5 | 17.47 | **no** | `a100_sxm_80gb-x8-tensor` | 621.5 | 2,125.1-3,944.5 | 1.24 | yes | 5.671x | 0.402x | 0.071x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | 17,763.6-32,971.6 | 1.54 | yes | `a100_sxm_80gb-x56-tensor` | 1,109.0 | 1,896.0-3,519.3 | 2.48 | yes | 5.829x | 9.369x | 1.607x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x15` | 2,119.2 | 4,492.4-8,338.5 | 2.00 | yes | `a100_sxm_80gb-x15-tensor` | 690.2 | 1,342.7-2,492.3 | 2.18 | yes | 3.070x | 3.346x | 1.090x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 4,245.8 | 12,340.3-22,905.2 | 1.46 | yes | `a100_sxm_80gb-x112-tensor` | 1,116.3 | 1,175.3-2,181.5 | 4.03 | yes | 3.803x | 10.500x | 2.761x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x57-romfill` | 2,036.0 | 3,340.0-6,199.4 | 2.58 | yes | `a100_sxm_80gb-x56-tensor` | 878.5 | 695.2-1,290.4 | 5.36 | yes | 2.318x | 4.804x | 2.073x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 4,071.0 | 14,867.8-27,596.6 | 1.16 | yes | `a100_sxm_80gb-x224-tensor` | 993.3 | 652.4-1,211.0 | 6.45 | yes | 4.099x | 22.788x | 5.560x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x57-romfill` | 2,036.0 | 3,340.0-6,199.4 | 2.58 | yes | `a100_sxm_80gb-x56-tensor` | 687.8 | 376.4-698.6 | 7.75 | yes | 2.960x | 8.874x | 2.998x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,761.4 | 13,581.6-25,209.3 | 1.17 | yes | `a100_sxm_80gb-x448-tensor` | 632.0 | 334.1-620.2 | 8.02 | **no** | 5.952x | 40.648x | 6.829x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x113-romfill` | 1,963.8 | 3,143.6-5,835.0 | 2.65 | yes | `a100_sxm_80gb-x111-hybrid` | 600.5 | 1,962.7-3,643.1 | 1.30 | yes | 3.270x | 1.602x | 0.490x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,178.4 | 11,271.4-20,921.2 | 1.20 | yes | `a100_sxm_80gb-x672-hybrid` | 591.2 | 1,845.0-3,424.5 | 1.36 | yes | 5.376x | 6.109x | 1.136x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 1,843.0 | 2,859.1-5,306.8 | 2.73 | yes | `a100_sxm_80gb-x224-hybrid` | 592.5 | 1,859.1-3,450.7 | 1.35 | yes | 3.111x | 1.538x | 0.494x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,331.9 | 8,090.2-15,016.4 | 1.22 | yes | `a100_sxm_80gb-x672-hybrid` | 591.2 | 1,845.0-3,424.5 | 1.36 | yes | 3.945x | 4.385x | 1.112x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x340-romfill` | 1,665.8 | 2,225.8-4,131.4 | 3.17 | yes | `a100_sxm_80gb-x335-hybrid` | 570.8 | 1,683.0-3,123.9 | 1.44 | yes | 2.918x | 1.323x | 0.453x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,521.5 | 5,171.2-9,598.4 | 1.25 | yes | `a100_sxm_80gb-x672-hybrid` | 591.2 | 1,845.0-3,424.5 | 1.36 | yes | 2.574x | 2.803x | 1.089x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-pipeline-x340-romfill` | 1,210.5 | 836.0-1,551.7 | 6.14 | yes | `a100_sxm_80gb-x335-hybrid` | 445.0 | 955.5-1,773.6 | 1.97 | yes | 2.720x | 0.875x | 0.322x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 493.2 | 1,509.9-2,802.6 | 1.38 | yes | `a100_sxm_80gb-x672-hybrid` | 522.8 | 1,348.2-2,502.4 | 1.64 | yes | 0.943x | 1.120x | 1.187x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x39` | 1,539.7 | 1,218.3-2,261.4 | 5.36 | yes | `a100_sxm_80gb-x38-tensor` | 687.9 | 944.3-1,752.8 | 3.09 | yes | 2.238x | 1.290x | 0.576x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 4,707.9 | 13,152.7-24,413.1 | 1.52 | yes | `a100_sxm_80gb-x56-tensor` | 721.7 | 1,013.2-1,880.7 | 3.02 | yes | 6.523x | 12.981x | 1.990x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 1,456.6 | 897.9-1,666.5 | 6.88 | yes | `a100_sxm_80gb-x39-tensor` | 580.5 | 633.2-1,175.3 | 3.89 | yes | 2.509x | 1.418x | 0.565x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 4,583.4 | 10,312.8-19,142.0 | 1.88 | yes | `a100_sxm_80gb-x56-tensor` | 612.4 | 670.3-1,244.1 | 3.87 | yes | 7.484x | 15.386x | 2.056x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 1,456.6 | 897.9-1,666.5 | 6.88 | yes | `a100_sxm_80gb-x39-tensor` | 464.4 | 409.2-759.5 | 4.81 | yes | 3.137x | 2.194x | 0.700x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4,390.6 | 10,187.0-18,908.4 | 1.83 | yes | `a100_sxm_80gb-x112-tensor` | 533.8 | 447.9-831.4 | 5.05 | yes | 8.225x | 22.743x | 2.765x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 1,443.6 | 1,514.5-2,811.1 | 4.04 | yes | `a100_sxm_80gb-x46-tensor` | 357.4 | 257.0-477.0 | 5.90 | yes | 4.039x | 5.893x | 1.459x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 4,202.1 | 9,825.6-18,237.6 | 1.81 | yes | `a100_sxm_80gb-x224-tensor` | 437.5 | 266.0-493.8 | 6.97 | yes | 9.605x | 36.933x | 3.845x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 1,422.2 | 871.8-1,618.2 | 6.92 | yes | `a100_sxm_80gb-x46-tensor` | 250.3 | 150.0-278.4 | 7.08 | yes | 5.682x | 5.813x | 1.023x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,869.7 | 9,174.7-17,029.4 | 1.79 | yes | `a100_sxm_80gb-x448-tensor` | 294.6 | 142.7-264.8 | 8.75 | **no** | 13.136x | 64.301x | 4.895x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 1,316.1 | 783.5-1,454.3 | 7.12 | yes | `a100_sxm_80gb-x55-tensor` | 172.0 | 80.9-150.2 | 9.01 | **no** | 7.652x | 9.684x | 1.265x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,399.6 | 7,629.2-14,160.9 | 1.89 | yes | `a100_sxm_80gb-x672-tensor` | 203.0 | 74.5-138.2 | 11.56 | **no** | 16.748x | 102.449x | 6.117x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x111-romfill` | 1,177.3 | 908.8-1,686.8 | 5.49 | yes | `a100_sxm_80gb-x110-tensor` | 118.4 | 39.6-73.5 | 12.67 | **no** | 9.946x | 22.936x | 2.306x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,814.0 | 5,249.2-9,743.2 | 2.27 | yes | `a100_sxm_80gb-x672-tensor` | 125.4 | 38.1-70.6 | 13.97 | **no** | 22.442x | 137.939x | 6.147x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 1,028.9 | 463.6-860.6 | 9.41 | **no** | `a100_sxm_80gb-x224-hybrid` | 42.0 | 81.0-150.3 | 2.20 | yes | 24.469x | 5.725x | 0.234x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,383.8 | 2,316.8-4,300.3 | 2.53 | yes | `a100_sxm_80gb-x672-tensor` | 39.4 | 9.7-17.9 | 17.32 | **no** | 35.089x | 239.987x | 6.839x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x207` | 725.5 | 719.4-1,335.2 | 4.28 | yes | `a100_sxm_80gb-x204-tensor` | 355.8 | 455.4-845.3 | 3.31 | yes | 2.039x | 1.580x | 0.775x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 2,375.7 | 2,474.2-4,592.5 | 4.07 | yes | `a100_sxm_80gb-x224-tensor` | 357.7 | 461.1-855.9 | 3.29 | yes | 6.642x | 5.366x | 0.808x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x248` | 625.8 | 431.8-801.5 | 6.14 | yes | `a100_sxm_80gb-x245-tensor` | 309.3 | 297.5-552.2 | 4.41 | yes | 2.023x | 1.451x | 0.718x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 2,153.7 | 3,766.4-6,990.9 | 2.42 | yes | `a100_sxm_80gb-x280-tensor` | 313.3 | 302.0-560.6 | 4.40 | yes | 6.873x | 12.471x | 1.814x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x218` | 554.6 | 202.8-376.4 | 11.60 | **no** | `a100_sxm_80gb-x215-tensor` | 231.3 | 177.5-329.4 | 5.53 | yes | 2.398x | 1.143x | 0.477x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 2,153.7 | 3,766.4-6,990.9 | 2.42 | yes | `a100_sxm_80gb-x280-tensor` | 239.9 | 181.8-337.4 | 5.60 | yes | 8.978x | 20.723x | 2.308x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x218` | 554.6 | 202.8-376.4 | 11.60 | **no** | `a100_sxm_80gb-x215-tensor` | 169.9 | 103.2-191.6 | 6.98 | yes | 3.265x | 1.965x | 0.602x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,969.0 | 3,582.2-6,649.0 | 2.33 | yes | `a100_sxm_80gb-x336-tensor` | 163.4 | 104.4-193.7 | 6.64 | yes | 12.051x | 34.323x | 2.848x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x218` | 554.6 | 202.8-376.4 | 11.60 | **no** | `a100_sxm_80gb-x215-tensor` | 116.1 | 57.6-106.9 | 8.55 | **no** | 4.778x | 3.522x | 0.737x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,845.4 | 3,467.2-6,435.6 | 2.26 | yes | `a100_sxm_80gb-x672-tensor` | 124.0 | 58.4-108.4 | 9.00 | **no** | 14.887x | 59.342x | 3.986x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 546.6 | 247.8-459.9 | 9.35 | **no** | `a100_sxm_80gb-x224-tensor` | 75.1 | 30.8-57.1 | 10.35 | **no** | 7.278x | 8.052x | 1.106x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,379.9 | 2,255.8-4,187.1 | 2.59 | yes | `a100_sxm_80gb-x672-tensor` | 80.9 | 30.7-57.0 | 11.18 | **no** | 17.051x | 73.513x | 4.311x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x248` | 514.7 | 210.4-390.6 | 10.37 | **no** | `a100_sxm_80gb-x245-tensor` | 46.2 | 15.9-29.5 | 12.34 | **no** | 11.132x | 13.245x | 1.190x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 875.7 | 1,694.1-3,144.4 | 2.19 | yes | `a100_sxm_80gb-x672-tensor` | 49.2 | 15.7-29.2 | 13.26 | **no** | 17.786x | 107.602x | 6.050x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x340` | 385.5 | 138.2-256.5 | 11.83 | **no** | `a100_sxm_80gb-x335-tensor` | 15.2 | 4.0-7.4 | 16.16 | **no** | 25.376x | 34.670x | 1.366x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 274.3 | 555.6-1,031.2 | 2.09 | yes | `a100_sxm_80gb-x672-tensor` | 15.5 | 4.0-7.4 | 16.51 | **no** | 17.658x | 139.259x | 7.887x |

**Does the ratio compress?** Of 48 class rows in this study, 15 move the ROM-versus-GPU ratio DOWN under speculation and 33 move it UP. The movement spans 0.071x to 7.887x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 40 of 48 ROM rows and 33 of 48 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-pipeline-x5-romfill` | 13,519.8 | 3,273.3-6,075.6 | 17.51 | **no** | `b200_sxm-x3-tensor` | 2,222.7 | 7,817.0-14,509.4 | 1.21 | yes | 6.083x | 0.419x | 0.069x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | 23,018.0-42,724.4 | 1.19 | yes | `b200_sxm-x29-hybrid` | 3,342.0 | 11,052.6-20,515.0 | 1.28 | yes | 1.934x | 2.083x | 1.077x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x16-romfill` | 4,528.6 | 10,591.8-19,659.8 | 1.81 | yes | `b200_sxm-x8-tensor` | 3,254.9 | 10,298.6-19,115.6 | 1.34 | yes | 1.391x | 1.028x | 0.739x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x2-romfill` | 5,400.8 | 20,122.1-37,349.3 | 1.14 | yes | `b200_sxm-x58-hybrid` | 3,246.8 | 10,454.8-19,405.4 | 1.32 | yes | 1.663x | 1.925x | 1.157x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x57-romfill` | 4,191.8 | 9,370.4-17,392.7 | 1.90 | yes | `b200_sxm-x29-hybrid` | 3,342.0 | 11,052.6-20,515.0 | 1.28 | yes | 1.254x | 0.848x | 0.676x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x4-romfill` | 5,121.2 | 18,910.2-35,099.9 | 1.15 | yes | `b200_sxm-x116-hybrid` | 3,160.6 | 9,727.8-18,056.1 | 1.38 | yes | 1.620x | 1.944x | 1.200x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x57-romfill` | 4,191.8 | 9,370.4-17,392.7 | 1.90 | yes | `b200_sxm-x29-hybrid` | 3,056.7 | 9,376.2-17,403.4 | 1.38 | yes | 1.371x | 0.999x | 0.729x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 4,640.7 | 16,877.3-31,326.6 | 1.17 | yes | `b200_sxm-x231-hybrid` | 2,906.4 | 8,328.3-15,458.4 | 1.48 | yes | 1.597x | 2.027x | 1.269x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x113-romfill` | 3,928.4 | 8,520.6-15,815.3 | 1.95 | yes | `b200_sxm-x58-hybrid` | 2,971.1 | 8,709.3-16,165.6 | 1.45 | yes | 1.322x | 0.978x | 0.740x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 4,040.9 | 14,378.2-26,687.8 | 1.19 | yes | `b200_sxm-x347-hybrid` | 2,774.4 | 7,727.7-14,343.6 | 1.52 | yes | 1.457x | 1.861x | 1.277x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x227-romfill` | 3,503.0 | 7,296.9-13,544.1 | 2.04 | yes | `b200_sxm-x116-hybrid` | 2,871.4 | 7,690.6-14,274.8 | 1.58 | yes | 1.220x | 0.949x | 0.778x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,395.4 | 11,728.0-21,768.8 | 1.23 | yes | `b200_sxm-x347-hybrid` | 2,774.4 | 7,727.7-14,343.6 | 1.52 | yes | 1.224x | 1.518x | 1.240x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x340-romfill` | 3,145.5 | 5,755.7-10,683.4 | 2.32 | yes | `b200_sxm-x173-hybrid` | 2,596.5 | 5,985.7-11,110.2 | 1.84 | yes | 1.211x | 0.962x | 0.794x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 2,573.2 | 8,569.1-15,905.4 | 1.27 | yes | `b200_sxm-x347-hybrid` | 2,669.7 | 6,783.5-12,591.0 | 1.67 | yes | 0.964x | 1.263x | 1.311x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-pipeline-x340-romfill` | 2,486.0 | 3,180.4-5,903.3 | 3.31 | yes | `b200_sxm-x173-hybrid` | 1,569.6 | 2,360.1-4,380.7 | 2.82 | yes | 1.584x | 1.348x | 0.851x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 1,049.1 | 2,448.8-4,545.2 | 1.82 | yes | `b200_sxm-x347-hybrid` | 1,959.8 | 3,121.7-5,794.3 | 2.66 | yes | 0.535x | 0.784x | 1.465x |

**Does the ratio compress?** Of 16 class rows in this study, 8 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.069x to 1.465x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 15 of 16 ROM rows and 16 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-pipeline-x5-romfill` | 9,438.0 | 2,289.3-4,249.3 | 17.48 | **no** | `a100_sxm_80gb-x5-tensor` | 995.3 | 3,406.5-6,322.8 | 1.24 | yes | 9.483x | 0.672x | 0.071x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | 22,146.5-41,106.9 | 1.24 | yes | `a100_sxm_80gb-x56-tensor` | 1,279.6 | 2,027.9-3,764.0 | 2.68 | yes | 5.052x | 10.921x | 2.162x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x15` | 2,119.2 | 5,974.6-11,089.6 | 1.50 | yes | `a100_sxm_80gb-x15-hybrid` | 1,255.6 | 4,170.3-7,740.5 | 1.28 | yes | 1.688x | 1.433x | 0.849x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x2` | 4,245.8 | 12,340.3-22,905.2 | 1.46 | yes | `a100_sxm_80gb-x112-hybrid` | 1,252.6 | 3,890.1-7,220.5 | 1.37 | yes | 3.390x | 3.172x | 0.936x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x57-romfill` | 2,036.0 | 5,154.1-9,566.6 | 1.67 | yes | `a100_sxm_80gb-x56-hybrid` | 1,279.0 | 4,119.1-7,645.6 | 1.32 | yes | 1.592x | 1.251x | 0.786x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x4-romfill` | 4,071.0 | 15,358.2-28,506.8 | 1.12 | yes | `a100_sxm_80gb-x224-hybrid` | 1,202.8 | 3,500.8-6,498.0 | 1.46 | yes | 3.385x | 4.387x | 1.296x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x57-romfill` | 2,036.0 | 5,154.1-9,566.6 | 1.67 | yes | `a100_sxm_80gb-x56-hybrid` | 1,256.4 | 3,991.9-7,409.5 | 1.33 | yes | 1.621x | 1.291x | 0.797x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 3,761.4 | 13,989.6-25,966.6 | 1.14 | yes | `a100_sxm_80gb-x448-hybrid` | 1,176.1 | 3,311.5-6,146.6 | 1.51 | yes | 3.198x | 4.225x | 1.321x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x113-romfill` | 1,963.8 | 4,721.6-8,764.0 | 1.76 | yes | `a100_sxm_80gb-x111-hybrid` | 1,224.8 | 3,741.1-6,944.0 | 1.39 | yes | 1.603x | 1.262x | 0.787x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,178.4 | 11,647.3-21,618.9 | 1.16 | yes | `a100_sxm_80gb-x672-hybrid` | 1,176.1 | 3,311.5-6,146.6 | 1.51 | yes | 2.702x | 3.517x | 1.302x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x227-romfill` | 1,843.0 | 4,099.7-7,609.6 | 1.91 | yes | `a100_sxm_80gb-x224-hybrid` | 1,181.4 | 3,357.2-6,231.3 | 1.49 | yes | 1.560x | 1.221x | 0.783x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 2,331.9 | 8,483.2-15,745.9 | 1.17 | yes | `a100_sxm_80gb-x672-hybrid` | 1,176.1 | 3,311.5-6,146.6 | 1.51 | yes | 1.983x | 2.562x | 1.292x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x340-romfill` | 1,665.8 | 3,247.4-6,027.7 | 2.17 | yes | `a100_sxm_80gb-x335-hybrid` | 1,101.1 | 2,824.2-5,242.2 | 1.65 | yes | 1.513x | 1.150x | 0.760x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,521.5 | 5,496.7-10,202.6 | 1.17 | yes | `a100_sxm_80gb-x672-hybrid` | 1,176.1 | 3,311.5-6,146.6 | 1.51 | yes | 1.294x | 1.660x | 1.283x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-q4p25-HBMKV-array-pipeline-x340-romfill` | 1,210.5 | 2,245.5-4,168.0 | 2.29 | yes | `a100_sxm_80gb-x335-hybrid` | 712.5 | 1,059.6-1,966.8 | 2.85 | yes | 1.699x | 2.119x | 1.247x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12` | 493.2 | 1,509.9-2,802.6 | 1.38 | yes | `a100_sxm_80gb-x672-hybrid` | 933.3 | 1,886.3-3,501.3 | 2.10 | yes | 0.528x | 0.800x | 1.515x |

**Does the ratio compress?** Of 16 class rows in this study, 8 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.071x to 2.162x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 15 of 16 ROM rows and 16 of 16 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

## Where the drafter lives on a ROM machine

The locality rule -- `stored/peak` is a technology constant -- is the load-bearing assumption of the whole ROM verdict. A pass that reads only the drafter's region uses only that region's read ports and takes exactly as long as sweeping the entire array. Two placements are therefore priced side by side, and the second is an architectural proposal this study **has not costed in silicon area**.

The same rule is what makes a SEQUENTIAL draft step expensive here. A per-position operation that moves only a small table is nearly free on a global-bandwidth store and costs a full array sweep on this one, so a drafter with `gamma` sequential applications pays `gamma` sweeps for them. That term is charged in full below; on a bandwidth store the bytes it moves are not separately charged at all, because this repository's model configs carry no size for the table -- an omission whose size, on DeepSeek-V4-Pro-0813, is the externally published 132,382,720 B per draft token, 0.33% of the 39,666,603,980 B target pass.

| study | model | ctx | batch | class | design | tau* draft in ROM | tau* draft in KV store | KV placement feasible | why not |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-tensor-x352-romfill` | 2.70 | 3.26 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 2.29 | 96.76 | NO | the KV store has no room for it |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x352-romfill` | 4.01 | 4.51 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 2.35 | 25.26 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x91` | 37.70 | 37.70 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3.00 | 25.69 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x91` | 37.70 | 37.70 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4.26 | 26.54 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x110` | 5.69 | 12.49 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 6.87 | 28.23 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x110` | 8.04 | 14.05 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 11.39 | 29.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x110` | 12.58 | 17.09 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 9.94 | 27.89 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x132` | 18.14 | 22.69 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.09 | 29.33 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x315-romfill` | 3.33 | 16.90 | NO | the KV store has no room for it |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 9.28 | 98.65 | NO | the KV store has no room for it |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x143` | 5.26 | 5.86 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 10.64 | 62.45 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x118` | 30.15 | 30.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 14.65 | 64.96 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x118` | 30.15 | 30.15 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3.18 | 51.88 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x118` | 30.99 | 30.99 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 4.78 | 52.90 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x143` | 7.58 | 16.84 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 8.14 | 54.94 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x143` | 11.35 | 19.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 8.99 | 51.57 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x170` | 16.63 | 21.70 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 10.77 | 46.33 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x55` | 10.39 | 10.22 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 1.86 | 2.09 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x55` | 10.39 | 10.22 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 2.61 | 2.85 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x55` | 10.39 | 10.22 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 4.10 | 4.34 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x55` | 10.98 | 10.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 1.98 | 2.13 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x57` | 10.88 | 10.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 2.87 | 3.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x68` | 6.16 | 5.74 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4.64 | 4.78 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x68` | 11.02 | 10.61 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5.70 | 5.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x216-romfill` | 7.35 | 7.11 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.59 | 5.79 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x72` | 7.10 | 6.96 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1.40 | 1.99 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x72` | 7.10 | 6.96 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1.40 | 1.99 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x72` | 7.10 | 6.96 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1.69 | 2.27 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x72` | 7.10 | 6.96 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 2.29 | 2.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x87` | 3.29 | 3.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3.48 | 4.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x87` | 5.43 | 5.22 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5.86 | 6.45 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x87` | 9.48 | 9.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 5.48 | 6.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x340-romfill` | 5.57 | 5.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 6.36 | 6.79 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hybrid-x51` | 10.17 | 12.20 | NO | the KV store has no room for it |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 1.80 | 2.44 | NO | the KV store has no room for it |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x55` | 10.39 | 10.22 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 2.61 | 2.85 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x55` | 10.39 | 10.22 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 4.10 | 4.34 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x55` | 10.98 | 10.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 1.98 | 2.13 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x57` | 10.88 | 10.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 2.87 | 3.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x68` | 6.16 | 5.74 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4.64 | 4.78 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x68` | 11.02 | 10.61 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 5.70 | 5.84 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x216-romfill` | 7.35 | 7.11 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5.59 | 5.79 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x66` | 8.54 | 10.16 | NO | the KV store has no room for it |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 1.40 | 2.55 | NO | the KV store has no room for it |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x72` | 7.10 | 6.96 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1.40 | 1.99 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x72` | 7.10 | 6.96 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1.69 | 2.27 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x72` | 7.10 | 6.96 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 2.29 | 2.87 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x87` | 3.29 | 3.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3.48 | 4.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x87` | 5.43 | 5.22 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5.86 | 6.45 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x87` | 9.48 | 9.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 5.48 | 6.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x340-romfill` | 5.57 | 5.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 6.36 | 6.79 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 6.94 | 6.66 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 1.80 | 1.68 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 6.94 | 6.66 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 1.73 | 1.81 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 6.94 | 6.66 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 1.72 | 1.80 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 9.59 | 9.37 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 1.68 | 1.76 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 9.98 | 9.65 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.76 | 1.83 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x87-romfill` | 8.56 | 8.18 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.11 | 2.16 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 8.42 | 8.06 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.53 | 2.57 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 11.23 | 11.03 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 2.06 | 1.71 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hybrid-x29` | 5.51 | 5.93 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 1.27 | 1.48 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 5.99 | 5.73 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 1.45 | 1.53 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 5.99 | 5.73 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 1.80 | 1.88 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 3.59 | 3.27 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 2.49 | 2.57 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 6.05 | 5.74 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 3.78 | 3.86 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 6.14 | 5.78 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 3.12 | 3.21 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x87-romfill` | 5.37 | 4.99 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 4.00 | 4.09 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 9.37 | 9.07 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.68 | 4.74 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hybrid-x28` | 7.94 | 10.62 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 1.26 | 2.41 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 5.63 | 5.37 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 1.42 | 1.51 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x31` | 5.63 | 5.37 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 1.74 | 1.83 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 3.41 | 3.10 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 2.39 | 2.47 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 5.71 | 5.40 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 3.62 | 3.70 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 9.65 | 9.36 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3.85 | 3.94 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 10.20 | 9.85 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 3.85 | 3.93 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 8.83 | 8.66 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.51 | 4.78 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 3.09 | 3.08 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 2.27 | 2.12 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 4.68 | 4.66 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2.32 | 2.31 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x161` | 12.42 | 11.92 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2.74 | 2.73 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x161` | 12.42 | 11.92 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4.42 | 4.41 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x161` | 12.42 | 11.92 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 7.15 | 7.13 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 8.50 | 7.90 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 4.91 | 4.81 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x193` | 6.78 | 6.16 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 5.33 | 5.20 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227` | 11.97 | 11.35 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 7.41 | 7.32 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 3.09 | 3.19 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 2.00 | 2.64 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 4.67 | 4.65 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2.07 | 2.05 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x160` | 11.46 | 10.96 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2.40 | 2.39 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x160` | 11.46 | 10.96 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3.74 | 3.73 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x160` | 11.46 | 10.96 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 6.36 | 6.35 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 7.02 | 6.42 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 4.14 | 4.04 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 12.86 | 12.27 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 7.20 | 7.10 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227` | 9.99 | 9.37 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 7.65 | 7.54 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 3.09 | 3.53 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 1.96 | 5.19 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 4.67 | 4.65 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2.03 | 2.01 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x157` | 11.89 | 11.39 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2.35 | 2.34 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x157` | 11.89 | 11.39 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3.64 | 3.63 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x157` | 11.89 | 11.39 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 6.22 | 6.20 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 5.39 | 4.86 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 4.03 | 3.93 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x170` | 9.64 | 9.11 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 6.98 | 6.87 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227` | 9.02 | 8.45 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 7.49 | 7.39 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x48` | 6.01 | 5.83 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 2.35 | 2.23 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 6.57 | 6.44 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 1.60 | 1.87 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 6.57 | 6.44 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 1.60 | 1.86 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 4.80 | 4.62 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.58 | 1.83 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 8.07 | 7.90 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.61 | 1.83 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x111-romfill` | 6.17 | 5.93 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.75 | 1.91 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x170-romfill` | 7.53 | 7.30 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1.68 | 1.26 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x340-romfill` | 9.75 | 9.61 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1.28 | 1.15 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x37` | 5.44 | 5.75 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 1.37 | 1.54 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 5.26 | 5.17 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 1.65 | 2.02 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 5.26 | 5.17 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 2.21 | 2.57 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 3.14 | 3.00 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 3.32 | 3.69 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 5.13 | 5.00 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3.07 | 3.43 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 5.38 | 5.20 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 3.05 | 3.39 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x57` | 8.50 | 8.31 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill` | 3.58 | 3.89 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 7.44 | 7.24 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.00 | 5.23 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x37` | 5.02 | 6.98 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 1.35 | 2.43 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 4.96 | 4.87 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 1.61 | 1.98 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 4.96 | 4.87 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 2.13 | 2.49 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 6.90 | 6.81 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 3.16 | 3.52 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 4.87 | 4.74 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 2.93 | 3.28 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 5.13 | 4.95 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 4.66 | 5.01 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 8.63 | 8.46 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 4.62 | 4.95 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 7.11 | 7.01 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.28 | 5.54 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x194` | 4.26 | 4.25 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 2.45 | 2.27 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x227` | 6.09 | 6.08 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2.50 | 2.78 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x208` | 11.35 | 10.95 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2.50 | 2.78 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x208` | 11.35 | 10.95 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3.94 | 4.22 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x208` | 11.35 | 10.95 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 6.83 | 7.10 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 5.40 | 4.96 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3.68 | 3.76 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 9.61 | 9.17 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.56 | 3.63 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x297` | 10.03 | 9.54 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4.28 | 4.10 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x191` | 4.26 | 4.32 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 2.14 | 2.91 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x227` | 6.03 | 6.02 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2.21 | 2.48 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 11.33 | 10.92 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2.21 | 2.48 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 11.33 | 10.92 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3.36 | 3.63 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 11.33 | 10.92 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5.66 | 5.93 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 4.58 | 4.13 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 8.73 | 8.96 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 7.99 | 7.55 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 5.25 | 5.33 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x297` | 8.55 | 8.07 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 8.86 | 8.92 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x191` | 4.24 | 4.54 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 2.10 | 5.97 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x227` | 6.03 | 6.01 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2.16 | 2.44 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 11.05 | 10.64 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2.16 | 2.44 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 11.05 | 10.64 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3.27 | 3.55 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x206` | 11.05 | 10.64 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5.48 | 5.76 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 4.45 | 4.01 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 8.58 | 8.82 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 7.75 | 7.31 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 5.10 | 5.17 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x297` | 8.08 | 7.63 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 8.68 | 8.75 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-pipeline-x8-romfill` | 17.64 | 17.64 | NO | the KV store has no room for it |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 1.41 | 1.51 | NO | the KV store has no room for it |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x16-romfill` | 3.11 | 3.21 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 1.25 | 1.68 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x57-romfill` | 3.25 | 3.35 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 1.25 | 1.67 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x57-romfill` | 3.25 | 3.35 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 1.26 | 1.64 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x113-romfill` | 3.23 | 3.30 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.30 | 1.61 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227-romfill` | 3.17 | 3.22 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.41 | 1.63 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 3.68 | 3.68 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.55 | 1.65 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-pipeline-x340-romfill` | 8.50 | 8.90 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1.82 | 1.37 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hybrid-x30` | 6.42 | 6.18 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 1.36 | 1.28 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x32` | 6.18 | 5.93 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 1.62 | 1.71 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x32` | 6.18 | 5.93 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 2.10 | 2.18 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 4.77 | 4.45 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 2.18 | 2.27 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x37` | 8.40 | 8.09 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 2.17 | 2.25 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x44` | 8.42 | 8.06 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2.14 | 2.22 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x87-romfill` | 7.16 | 6.79 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.36 | 2.43 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x227-romfill` | 9.97 | 9.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.12 | 4.16 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 3.12 | 3.09 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 3.74 | 3.49 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 4.74 | 4.71 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3.55 | 3.53 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x167` | 12.98 | 12.51 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4.38 | 4.36 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x167` | 12.98 | 12.51 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 2.95 | 2.84 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x167` | 12.98 | 12.51 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 3.13 | 3.00 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x193` | 6.58 | 5.95 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.05 | 2.93 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x193` | 12.01 | 11.39 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.72 | 3.63 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x308-romfill` | 11.69 | 11.03 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 3.03 | 2.82 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-pipeline-x8-romfill` | 17.47 | 17.47 | NO | the KV store has no room for it |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 1.54 | 1.62 | NO | the KV store has no room for it |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x15` | 2.00 | 2.36 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1.46 | 2.04 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x57-romfill` | 2.58 | 2.89 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 1.16 | 2.01 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x57-romfill` | 2.58 | 2.89 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.17 | 1.96 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x113-romfill` | 2.65 | 2.91 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.20 | 1.85 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 2.73 | 2.96 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.22 | 1.66 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x340-romfill` | 3.17 | 3.31 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.25 | 1.47 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-pipeline-x340-romfill` | 6.14 | 7.43 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1.38 | 1.24 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hybrid-x39` | 5.36 | 5.19 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 1.52 | 1.41 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 6.88 | 6.79 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 1.88 | 2.24 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x40` | 6.88 | 6.79 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 1.83 | 2.18 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 4.04 | 3.91 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 1.81 | 2.15 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x47` | 6.92 | 6.78 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.79 | 2.10 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x56` | 7.12 | 6.94 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.89 | 2.16 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x111-romfill` | 5.49 | 5.26 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.27 | 2.50 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 9.41 | 9.20 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2.53 | 2.07 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-tensor-x207` | 4.28 | 4.26 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 4.07 | 3.76 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-tensor-x248` | 6.14 | 6.13 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 2.42 | 2.59 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x218` | 11.60 | 11.18 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 2.42 | 2.59 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x218` | 11.60 | 11.18 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2.33 | 2.41 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x218` | 11.60 | 11.18 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.26 | 2.32 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x227` | 9.35 | 8.91 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.59 | 2.64 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x248` | 10.37 | 9.91 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2.19 | 2.02 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hybrid-x340` | 11.83 | 11.30 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2.09 | 2.04 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-pipeline-x5-romfill` | 17.51 | 17.51 | NO | the KV store has no room for it |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 1.19 | 1.21 | NO | the KV store has no room for it |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x16-romfill` | 1.81 | 1.81 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x2-romfill` | 1.14 | 1.25 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x57-romfill` | 1.90 | 1.90 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x4-romfill` | 1.15 | 1.25 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x57-romfill` | 1.90 | 1.90 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 1.17 | 1.26 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x113-romfill` | 1.95 | 1.95 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.19 | 1.27 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x227-romfill` | 2.04 | 2.04 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.23 | 1.28 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x340-romfill` | 2.32 | 2.32 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.27 | 1.29 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-pipeline-x340-romfill` | 3.31 | 3.31 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 1.82 | 1.31 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-pipeline-x5-romfill` | 17.48 | 17.48 | NO | the KV store has no room for it |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 1.24 | 1.25 | NO | the KV store has no room for it |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x15` | 1.50 | 1.47 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x2` | 1.46 | 1.35 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x57-romfill` | 1.67 | 1.73 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x4-romfill` | 1.12 | 1.35 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x57-romfill` | 1.67 | 1.73 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 1.14 | 1.34 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x113-romfill` | 1.76 | 1.81 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.16 | 1.32 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x227-romfill` | 1.91 | 1.95 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.17 | 1.27 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hybrid-x340-romfill` | 2.17 | 2.19 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.17 | 1.22 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-q4p25-HBMKV-array-pipeline-x340-romfill` | 2.29 | 2.54 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12` | 1.38 | 1.16 | yes | -- |

## The capacity requirement, stated as a requirement

Every evaluated ROM design carries `weight_capacity_bytes == stored_weight_bytes` (the `romfill` variants reach 1.0039x), so no evaluated design has spare array for a drafter it does not already store. Re-solving the area split is `balanced_area_split`'s job and that file is not touched here, so what follows is a requirement -- this much extra array, or this much extra sweep on every pass -- and not a new design. **The speculative-optimal ROM design has not been computed, only bounded by the rungs that already exist.**

| study | model | design | drafter already in the checkpoint | extra stored bytes | extra array mm2 | as a fraction of the design | sweep inflation if area is held fixed |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-tensor-x352-romfill` | no | 850,275,640 | 90.7 | 0.0% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | no | 850,275,640 | 90.7 | 0.1% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-array-tensor-x315-romfill` | no | 850,275,640 | 116.6 | 0.0% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hybrid-x55` | no | 850,275,640 | 90.7 | 0.2% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-wafer-tensor-x1` | no | 850,275,640 | 90.7 | 0.2% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hybrid-x72` | no | 850,275,640 | 116.6 | 0.2% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-SRAMKV-array-hybrid-x51` | no | 850,275,640 | 90.7 | 0.2% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | no | 850,275,640 | 90.7 | 0.2% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-SRAMKV-array-hybrid-x66` | no | 850,275,640 | 116.6 | 0.2% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hybrid-x37` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hybrid-x29` | no | 686,957,240 | 73.2 | 0.3% | 1.0041x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hybrid-x28` | no | 686,957,240 | 73.2 | 0.3% | 1.0041x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | no | 1,959,810,680 | 208.9 | 0.2% | 1.0022x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | no | 1,959,810,680 | 208.9 | 0.2% | 1.0022x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | no | 1,959,810,680 | 208.9 | 0.2% | 1.0022x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hybrid-x48` | no | 686,957,240 | 94.2 | 0.2% | 1.0041x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | no | 686,957,240 | 94.2 | 0.2% | 1.0041x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hybrid-x37` | no | 686,957,240 | 94.2 | 0.3% | 1.0041x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | no | 686,957,240 | 94.2 | 0.2% | 1.0041x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hybrid-x37` | no | 686,957,240 | 94.2 | 0.3% | 1.0041x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | no | 686,957,240 | 94.2 | 0.2% | 1.0041x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-tensor-x194` | no | 1,959,810,680 | 268.6 | 0.2% | 1.0022x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-tensor-x191` | no | 1,959,810,680 | 268.6 | 0.2% | 1.0022x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-tensor-x191` | no | 1,959,810,680 | 268.6 | 0.2% | 1.0022x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-pipeline-x8-romfill` | no | 1,929,464,320 | 205.7 | 3.2% | 1.1178x |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | no | 1,929,464,320 | 205.7 | 0.4% | 1.1178x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hybrid-x30` | no | 686,957,240 | 73.2 | 0.3% | 1.0041x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | no | 1,959,810,680 | 208.9 | 0.2% | 1.0022x |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-pipeline-x8-romfill` | no | 1,929,464,320 | 264.5 | 4.1% | 1.1178x |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | no | 1,929,464,320 | 264.5 | 0.6% | 1.1178x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hybrid-x39` | no | 686,957,240 | 94.2 | 0.3% | 1.0041x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | no | 686,957,240 | 94.2 | 0.2% | 1.0041x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-tensor-x207` | no | 1,959,810,680 | 268.6 | 0.2% | 1.0022x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-array-pipeline-x5-romfill` | no | 512,513,960 | 54.6 | 1.3% | 1.1178x |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | no | 512,513,960 | 54.6 | 0.1% | 1.1178x |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-array-pipeline-x5-romfill` | no | 512,513,960 | 70.3 | 1.7% | 1.1178x |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | no | 512,513,960 | 70.3 | 0.2% | 1.1178x |

## Which design the published rule chooses once a block is verified

A re-ranking of designs the study already evaluated, under the study's own selection rule (non-dominated on per-user tokens/s and tokens/s per 1,000 mm2, then a marginal-return walk from the smallest feasible machine). `tau` is a common factor on both axes, so the choice is independent of the acceptance rate. The rule's reproduction of the published autoregressive recommendation is reported first, because a re-ranking whose baseline does not reproduce is not evidence of anything.

| study | model | published recommendation | rule reproduces it | under speculation, draft in ROM | draft in KV store | moves |
| --- | --- | --- | --- | --- | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | `ROM-N5-native-HBMKV-array-tensor-x110` | yes |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | `ROM-N6-native-HBMKV-array-tensor-x143` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | no |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | no |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | yes | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | no |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hybrid-x29` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hybrid-x28` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | yes |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | yes |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | yes |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | yes |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | no |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | yes |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-tensor-x1` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | yes |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | yes |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-pipeline-x5-romfill` | yes | `ROM-N5-native-SRAMKV-array-tensor-x8` | `ROM-N5-native-HBMKV-array-tensor-x7` | yes |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hybrid-x30` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-tensor-x1` | yes |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | yes |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-pipeline-x6` | yes | `ROM-N6-native-HBMKV-array-tensor-x8` | `ROM-N6-native-HBMKV-array-tensor-x7` | yes |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-tensor-x1` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-tensor-x1` | no |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | yes | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | yes |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-array-pipeline-x2` | yes | `ROM-N5-q4p25-SRAMKV-array-tensor-x3` | `ROM-N5-q4p25-HBMKV-array-tensor-x4` | yes |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-array-pipeline-x3-romfill` | yes | `ROM-N6-q4p25-SRAMKV-array-tensor-x3` | `ROM-N6-q4p25-HBMKV-array-tensor-x5` | yes |

**The rule reproduces the published autoregressive recommendation on 26 of 26 model-and-study rows.** Of the 26 rows where it reproduces and the drafter applies, verifying a block moves the chosen rung on 21. Where it moves, it moves toward machines with compute headroom for a block, which is exactly what the arithmetic predicts: a verification pass raises arithmetic intensity by the block size, and a machine sized with just enough compute for one token per sweep has no room for it. **This is a re-ranking of rungs that already exist. The speculative-optimal design has not been computed: that would need the area split re-solved, which is `balanced_area_split`'s job and not this layer's.**

## Gate: the DFlash overhead factor

_band check, never an equality._

- modelled on `Qwen3-8B/b200_sxm-x3-tensor` at batch 1, 8,192 tokens of context, gamma 16
- modelled overhead factor: **1.208** with the drafter charged no KV, **1.216** at the top of the band
- published band: 1.26-1.32, outlier MT-Bench at 1.54
- source: arXiv:2602.06036v2, ICML 2026, Table 1, tau divided by reported speedup
- inside the published band: **no**

**Residual.** this layer models an overhead factor of 1.208 at the low end of the unsourced drafter-KV band and 1.216 at the high end, against a published 1.26-1.32 measured on an H200. The gap is the gate residual and its named causes are: the drafter's own KV traffic at the low bound of an unsourced band, no sampler and no scheduler cost anywhere in this model, and a modelled B200-class cluster against their measured H200.

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

_This study evaluates no eight-device GPU cluster for DeepSeek-V4-Pro-0813. Eight B200-class packages is 12,800 mm2 of silicon; the GPU comparator ladder in this study is anchored to the areas the ROM designs need for a 1.6-trillion-parameter checkpoint, and it contains no eight-package rung. The rows below are the nearest rungs it does contain -- 6, 7, 9 packages -- and they are NOT an eight-device figure. Producing one would mean evaluating a design this study has not evaluated, which this tool does not do._

**Every row below is evaluated at gamma = 8, the block size Xiaomi's own deployment uses, so the verification pass carries 9 positions. The acceptance lengths applied to it are the ones Xiaomi publishes at that same block size. This is NOT this profile's served block size, and the cycle and the acceptance length are never taken from different configurations.**

GPU cluster sizes this study evaluates for DeepSeek-V4-Pro-0813: 6, 7, 9, 13, 14, 20, 22, 29, 48, 56, 58, 74, 75, 76, 79, 80, 81, 82, 83, 85, 87, 91, 92, 94, 97, 98, 110, 112, 113, 116, 118, 146, 147, 149, 150, 151, 155, 157, 158, 165, 168, 173, 185, 187, 188, 191, 196, 200, 201, 203, 204, 205, 207, 215, 224, 227, 229, 231, 234, 245, 272, 274, 280, 293, 335, 336, 347, 363, 365, 371, 372, 373, 377, 391, 392, 394, 448, 672 packages.

DeepSeek-V4-Pro-0813 is 1.6 trillion total parameters with 49 billion active; the model Xiaomi describes is 1 trillion total, and its active count is ASSUMED at 42 billion -- the blog states no active parameter count, that figure comes from secondary reporting, and it is graded `assumed` here and used for nothing but this sentence. They are the same class and they are not the same model.

| design | packages | batch | ctx | block (gamma) | positions verified | AR per-user tok/s | AR aggregate tok/s | resident sessions | binds on | tau* | coding tau 6.30 | maths tau 5.56 | agent tau 4.29 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| `b200_sxm-x6-pipeline` | 6 | 1 | 8,192 | 8 | 9 | 116.82 | 701 | 6 | `weight_read` | 3.32 | 222.00 | 195.92 | 151.17 |
| `b200_sxm-x6-tensor` | 6 | 1 | 8,192 | 8 | 9 | 575.37 | 575 | 1 | `weight_read` | 2.94 | 1,233.24 | 1,088.38 | 839.78 |
| `b200_sxm-x6-pipeline` | 6 | 2 | 8,192 | 8 | 9 | 116.82 | 701 | 6 | `weight_read` | 3.32 | 222.00 | 195.92 | 151.17 |
| `b200_sxm-x6-tensor` | 6 | 2 | 8,192 | 8 | 9 | 448.41 | 897 | 2 | `weight_read` | 3.58 | 788.33 | 695.73 | 536.82 |
| `b200_sxm-x6-pipeline` | 6 | 4 | 8,192 | 8 | 9 | 116.82 | 701 | 6 | `weight_read` | 3.32 | 222.00 | 195.92 | 151.17 |
| `b200_sxm-x6-tensor` | 6 | 4 | 8,192 | 8 | 9 | 322.72 | 1,291 | 4 | `weight_read` | 4.04 | 503.46 | 444.32 | 342.83 |
| `b200_sxm-x6-pipeline` | 6 | 8 | 8,192 | 8 | 9 | 104.39 | 835 | 8 | `weight_read` | 3.59 | 183.08 | 161.58 | 124.67 |
| `b200_sxm-x6-tensor` | 6 | 8 | 8,192 | 8 | 9 | 215.74 | 1,726 | 8 | `weight_read` | 3.97 | 342.27 | 302.07 | 233.07 |
| `b200_sxm-x6-pipeline` | 6 | 16 | 8,192 | 8 | 9 | 75.34 | 1,205 | 16 | `weight_read` | 4.16 | 114.14 | 100.73 | 77.72 |
| `b200_sxm-x6-tensor` | 6 | 16 | 8,192 | 8 | 9 | 137.26 | 2,196 | 16 | `weight_read` | 3.27 | 264.84 | 233.73 | 180.34 |
| `b200_sxm-x6-pipeline` | 6 | 32 | 8,192 | 8 | 9 | 50.49 | 1,616 | 32 | `weight_read` | 4.33 | 73.55 | 64.91 | 50.08 |
| `b200_sxm-x6-tensor` | 6 | 32 | 8,192 | 8 | 9 | 86.74 | 2,776 | 32 | `weight_read` | 2.31 | 236.15 | 208.41 | 160.81 |
| `b200_sxm-x6-pipeline` | 6 | 64 | 8,192 | 8 | 9 | 31.98 | 2,047 | 64 | `weight_read` | 3.84 | 52.44 | 46.28 | 35.71 |
| `b200_sxm-x6-tensor` | 6 | 64 | 8,192 | 8 | 9 | 57.80 | 3,699 | 64 | `weight_read` | 1.65 | 221.21 | 195.22 | 150.63 |
| `b200_sxm-x6-pipeline` | 6 | 256 | 8,192 | 8 | 9 | 12.56 | 3,214 | 256 | `weight_read` | 1.89 | 41.93 | 37.00 | 28.55 |
| `b200_sxm-x6-tensor` | 6 | 256 | 8,192 | 8 | 9 | 37.80 | 9,677 | 256 | `weight_read` | 1.43 | 166.44 | 146.89 | 113.34 |
| `b200_sxm-x7-pipeline` | 7 | 1 | 32,768 | 8 | 9 | 110.81 | 776 | 7 | `weight_read` | 3.28 | 212.79 | 187.80 | 144.90 |
| `b200_sxm-x7-tensor` | 7 | 1 | 32,768 | 8 | 9 | 624.57 | 625 | 1 | `weight_read` | 2.88 | 1,366.58 | 1,206.06 | 930.57 |
| `b200_sxm-x7-pipeline` | 7 | 2 | 32,768 | 8 | 9 | 110.81 | 776 | 7 | `weight_read` | 3.28 | 212.79 | 187.80 | 144.90 |
| `b200_sxm-x7-tensor` | 7 | 2 | 32,768 | 8 | 9 | 488.08 | 976 | 2 | `weight_read` | 3.49 | 881.10 | 777.60 | 599.98 |
| `b200_sxm-x7-pipeline` | 7 | 4 | 32,768 | 8 | 9 | 110.81 | 776 | 7 | `weight_read` | 3.28 | 212.79 | 187.80 | 144.90 |
| `b200_sxm-x7-tensor` | 7 | 4 | 32,768 | 8 | 9 | 353.37 | 1,413 | 4 | `weight_read` | 3.93 | 566.73 | 500.16 | 385.92 |
| `b200_sxm-x7-pipeline` | 7 | 8 | 32,768 | 8 | 9 | 105.28 | 842 | 8 | `weight_read` | 3.40 | 194.95 | 172.05 | 132.75 |
| `b200_sxm-x7-tensor` | 7 | 8 | 32,768 | 8 | 9 | 238.17 | 1,905 | 8 | `weight_read` | 3.88 | 387.02 | 341.56 | 263.54 |
| `b200_sxm-x7-pipeline` | 7 | 16 | 32,768 | 8 | 9 | 77.26 | 1,236 | 16 | `weight_read` | 3.98 | 122.39 | 108.02 | 83.34 |
| `b200_sxm-x7-tensor` | 7 | 16 | 32,768 | 8 | 9 | 152.82 | 2,445 | 16 | `weight_read` | 3.21 | 299.71 | 264.51 | 204.09 |
| `b200_sxm-x7-pipeline` | 7 | 32 | 32,768 | 8 | 9 | 52.75 | 1,688 | 32 | `weight_read` | 4.24 | 78.32 | 69.12 | 53.33 |
| `b200_sxm-x7-tensor` | 7 | 32 | 32,768 | 8 | 9 | 97.24 | 3,112 | 32 | `weight_read` | 2.30 | 266.19 | 234.93 | 181.27 |
| `b200_sxm-x7-pipeline` | 7 | 64 | 32,768 | 8 | 9 | 33.95 | 2,173 | 64 | `weight_read` | 3.93 | 54.48 | 48.08 | 37.10 |
| `b200_sxm-x7-tensor` | 7 | 64 | 32,768 | 8 | 9 | 65.06 | 4,164 | 64 | `weight_read` | 1.66 | 246.95 | 217.95 | 168.16 |
| `b200_sxm-x7-pipeline` | 7 | 256 | 32,768 | 8 | 9 | 13.37 | 3,422 | 256 | `weight_read` | 2.05 | 41.11 | 36.28 | 27.99 |
| `b200_sxm-x7-tensor` | 7 | 256 | 32,768 | 8 | 9 | 42.22 | 10,808 | 256 | `weight_read` | 1.49 | 178.34 | 157.39 | 121.44 |
| `b200_sxm-x9-hybrid` | 9 | 1 | 200,000 | 8 | 9 | 395.91 | 792 | 2 | `weight_read` | 2.97 | 841.18 | 742.37 | 572.80 |
| `b200_sxm-x9-pipeline` | 9 | 1 | 200,000 | 8 | 9 | 100.36 | 903 | 9 | `weight_read` | 3.21 | 197.00 | 173.86 | 134.15 |
| `b200_sxm-x9-tensor` | 9 | 1 | 200,000 | 8 | 9 | 508.31 | 508 | 1 | `weight_read` | 2.53 | 1,264.59 | 1,116.05 | 861.12 |
| `b200_sxm-x9-hybrid` | 9 | 2 | 200,000 | 8 | 9 | 395.91 | 792 | 2 | `weight_read` | 2.97 | 841.18 | 742.37 | 572.80 |
| `b200_sxm-x9-pipeline` | 9 | 2 | 200,000 | 8 | 9 | 100.36 | 903 | 9 | `weight_read` | 3.21 | 197.00 | 173.86 | 134.15 |
| `b200_sxm-x9-tensor` | 9 | 2 | 200,000 | 8 | 9 | 414.82 | 830 | 2 | `weight_read` | 3.14 | 831.92 | 734.20 | 566.50 |
| `b200_sxm-x9-hybrid` | 9 | 4 | 200,000 | 8 | 9 | 302.76 | 1,211 | 4 | `weight_read` | 3.51 | 542.98 | 479.20 | 369.74 |
| `b200_sxm-x9-pipeline` | 9 | 4 | 200,000 | 8 | 9 | 100.36 | 903 | 9 | `weight_read` | 3.21 | 197.00 | 173.86 | 134.15 |
| `b200_sxm-x9-tensor` | 9 | 4 | 200,000 | 8 | 9 | 313.93 | 1,256 | 4 | `weight_read` | 3.71 | 533.03 | 470.42 | 362.96 |
| `b200_sxm-x9-hybrid` | 9 | 8 | 200,000 | 8 | 9 | 215.86 | 1,727 | 8 | `weight_read` | 3.88 | 350.82 | 309.61 | 238.89 |
| `b200_sxm-x9-pipeline` | 9 | 8 | 200,000 | 8 | 9 | 100.36 | 903 | 9 | `weight_read` | 3.21 | 197.00 | 173.86 | 134.15 |
| `b200_sxm-x9-tensor` | 9 | 8 | 200,000 | 8 | 9 | 219.62 | 1,757 | 8 | `weight_read` | 3.97 | 348.91 | 307.92 | 237.59 |
| `b200_sxm-x9-hybrid` | 9 | 16 | 200,000 | 8 | 9 | 144.31 | 2,309 | 16 | `weight_read` | 3.77 | 240.85 | 212.56 | 164.01 |
| `b200_sxm-x9-pipeline` | 9 | 16 | 200,000 | 8 | 9 | 78.67 | 1,259 | 16 | `weight_read` | 3.66 | 135.48 | 119.56 | 92.25 |
| `b200_sxm-x9-tensor` | 9 | 16 | 200,000 | 8 | 9 | 144.11 | 2,306 | 16 | `weight_read` | 3.75 | 241.79 | 213.39 | 164.65 |
| `b200_sxm-x9-hybrid` | 9 | 32 | 200,000 | 8 | 9 | 92.39 | 2,957 | 32 | `weight_read` | 3.10 | 187.47 | 165.45 | 127.66 |
| `b200_sxm-x9-pipeline` | 9 | 32 | 200,000 | 8 | 9 | 55.17 | 1,766 | 32 | `weight_read` | 4.02 | 86.42 | 76.27 | 58.85 |
| `b200_sxm-x9-tensor` | 9 | 32 | 200,000 | 8 | 9 | 91.68 | 2,934 | 32 | `weight_read` | 3.36 | 172.09 | 151.88 | 117.19 |
| `b200_sxm-x9-hybrid` | 9 | 64 | 200,000 | 8 | 9 | 58.81 | 3,764 | 64 | `weight_read` | 2.21 | 167.50 | 147.83 | 114.06 |
| `b200_sxm-x9-pipeline` | 9 | 64 | 200,000 | 8 | 9 | 36.41 | 2,331 | 64 | `weight_read` | 3.94 | 58.29 | 51.44 | 39.69 |
| `b200_sxm-x9-tensor` | 9 | 64 | 200,000 | 8 | 9 | 59.21 | 3,789 | 64 | `weight_read` | 3.26 | 114.60 | 101.14 | 78.04 |
| `b200_sxm-x9-hybrid` | 9 | 256 | 200,000 | 8 | 9 | 29.25 | 7,489 | 256 | `weight_read` | 1.30 | 141.44 | 124.83 | 96.31 |
| `b200_sxm-x9-pipeline` | 9 | 256 | 200,000 | 8 | 9 | 14.51 | 3,714 | 256 | `weight_read` | 2.31 | 39.61 | 34.95 | 26.97 |
| `b200_sxm-x9-tensor` | 9 | 256 | 200,000 | 8 | 9 | 28.59 | 7,318 | 256 | `weight_read` | 4.69 | 38.37 | 33.87 | 26.13 |

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

