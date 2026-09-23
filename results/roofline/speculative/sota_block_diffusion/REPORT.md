# Speculative decoding on the area-constrained roofline: sota_block_diffusion

> The DFlash / MiMo-UltraSpeed class: a block-diffusion drafter decoding a whole block in one parallel pass. Every figure below is derived from the roofline artifacts
> this repository has already published, by re-assembling each point's own five
> critical-path terms for a speculative cycle. Nothing here re-runs the machine
> model, and nothing here invents an acceptance rate.

## What this layer says

1. **Every term the speculative arithmetic needs is already in the published artifact, exactly.** 98,262 feasible points across 22 studies were rebuilt from their own five critical-path terms and every one reproduced its published step time to 1e-9 relative. Nothing here re-ran the machine model, and the layer is additive by construction rather than by promise.
2. **The headline is a break-even, not a speedup.** `tau* = T_cycle / step_time_s`, and `tau <= gamma+1` always. Of 159,547 (point, draft-placement) pairs where this profile's drafter applies, 48,243 (30.2%) cannot be sped up by speculation at ANY acceptance rate, at any block size on the ladder, even charging the drafter no KV traffic at all.
3. **The ROM-versus-GPU ratio under speculation carries no acceptance rate.** It is `T_cycle(GPU) / T_cycle(ROM)`: `tau` is a property of the model and its drafter, not of the machine, so it is identical on both sides and cancels. Every movement this report shows is a machine effect and nothing else, which is why it can be published without inventing an acceptance rate.
4. **The ratio moves, and it mostly compresses.** Across 509 model-context-batch-class rows, 354 move the ROM-versus-GPU per-user ratio DOWN under speculation and 155 move it UP, spanning 0.055x to 6.972x. The ROM advantage compresses on most operating points.
5. **At batch 1 the two extremes are opposite in sign, and they are the result.** DeepSeek-V4-Pro-0813 on `array` silicon goes from 2.77x to 0.15x -- a 0.056x movement -- while Qwen3-8B on `wafer` silicon goes from 5.05x to 10.92x, a 2.162x movement. A layer that multiplied both sides by `tau` would have reported neither.
6. **A moving ratio is not a win for either side, and the report says so on every table.** At the most favourable sourced acceptance (7.87) speculation is worth having on 238 of 511 ROM class rows and 441 of 511 GPU rows; everywhere else the design runs SLOWER with a drafter than without one. Where both sides lose, a rising ratio means only that the comparator lost more.
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
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,110 | 216 | 1.70 | 8.34 | 21.54 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 340 | 248 | 2.12 | 21.62 | 21.62 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 730 | 0 | 1.67 | 4.82 | 13.96 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 1,030 | 1,030 | 17.43 | 104.66 | 2,384.74 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 78 | 76 | 14.43 | 2,394.88 | 2,482.64 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 1,232 | 669 | 1.70 | 18.22 | 1,023.77 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 700 | 602 | 4.42 | 30.68 | 1,426.49 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 1,030 | 1,028 | 16.21 | 49.98 | 62.34 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 78 | 35 | 4.39 | 14.94 | 707.87 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 1,232 | 256 | 1.23 | 8.17 | 522.83 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 700 | 456 | 3.38 | 32.96 | 49.52 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 1 | 1 | 27.16 | 27.16 | 27.16 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 360 | 131 | 2.89 | 14.18 | 23.90 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 959 | 258 | 1.47 | 11.82 | 21.45 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 993 | 993 | 18.57 | 181.22 | 2,865.48 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 78 | 63 | 6.56 | 2,267.93 | 2,483.10 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 1,174 | 736 | 3.04 | 19.34 | 708.54 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 545 | 515 | 11.98 | 56.24 | 2,374.46 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 993 | 992 | 15.48 | 51.13 | 62.55 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 78 | 33 | 5.50 | 15.60 | 533.16 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 1,174 | 229 | 1.26 | 7.68 | 518.39 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 545 | 352 | 5.06 | 32.58 | 49.51 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,299 | 200 | 1.52 | 5.96 | 19.07 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 380 | 0 | 1.30 | 6.09 | 7.80 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 791 | 0 | 1.59 | 3.44 | 12.74 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 1,026 | 469 | 9.81 | 16.96 | 44.23 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 23 | 1 | 2.83 | 11.35 | 570.34 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 1,359 | 162 | 1.16 | 4.43 | 276.03 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 883 | 213 | 1.39 | 10.89 | 36.35 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 1,026 | 901 | 9.72 | 20.07 | 38.71 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 23 | 2 | 5.06 | 11.50 | 1,140.34 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 1,359 | 190 | 1.19 | 5.64 | 540.88 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 883 | 606 | 3.66 | 25.50 | 39.01 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 3 | 3 | 17.37 | 17.38 | 17.38 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 427 | 141 | 2.72 | 14.12 | 19.08 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 1,130 | 0 | 1.36 | 3.28 | 14.18 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 855 | 758 | 11.03 | 17.63 | 24.20 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 152 | 73 | 1.53 | 17.56 | 266.89 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 1,249 | 163 | 1.16 | 4.78 | 249.35 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 627 | 194 | 2.20 | 13.32 | 53.08 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 855 | 790 | 11.15 | 21.98 | 39.01 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 152 | 67 | 2.99 | 16.47 | 533.61 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 1,249 | 184 | 1.20 | 5.08 | 488.31 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 627 | 452 | 3.67 | 26.97 | 38.71 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 864 | 140 | 1.52 | 7.04 | 19.07 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `thermal` | 300 | 0 | 1.30 | 6.09 | 7.80 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 716 | 0 | 1.59 | 3.52 | 12.74 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 1,028 | 508 | 9.81 | 16.99 | 51.46 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 85 | 67 | 2.89 | 38.82 | 353.37 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 1,322 | 164 | 1.19 | 5.21 | 276.03 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 797 | 223 | 2.62 | 10.86 | 36.35 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 1,028 | 895 | 9.72 | 19.82 | 37.29 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 85 | 9 | 2.02 | 10.08 | 708.65 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 1,322 | 187 | 1.17 | 5.62 | 540.88 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 797 | 541 | 5.04 | 25.48 | 35.55 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `compute` | 5 | 5 | 17.36 | 17.37 | 17.44 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 362 | 123 | 2.72 | 13.55 | 19.08 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 953 | 0 | 1.36 | 3.50 | 14.18 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 823 | 758 | 11.03 | 17.66 | 53.01 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 212 | 133 | 1.53 | 38.08 | 266.96 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 1,248 | 163 | 1.25 | 5.02 | 249.38 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 593 | 213 | 2.63 | 13.74 | 53.08 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 823 | 758 | 11.15 | 21.23 | 37.89 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 212 | 71 | 2.60 | 14.35 | 533.74 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 1,248 | 182 | 1.19 | 5.05 | 488.36 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 593 | 428 | 4.97 | 27.13 | 38.71 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `kv_read` | 100 | 0 | 2.58 | 5.12 | 8.92 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 833 | 41 | 1.26 | 2.67 | 18.82 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 253 | 0 | 1.99 | 4.76 | 5.42 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 393 | 0 | 1.48 | 2.68 | 4.99 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 188 | 71 | 10.93 | 16.36 | 17.78 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 58 | 0 | 1.03 | 4.71 | 379.82 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 492 | 34 | 1.14 | 3.23 | 231.48 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `thermal` | 35 | 0 | 1.61 | 7.61 | 9.95 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 343 | 34 | 1.59 | 6.31 | 17.66 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 188 | 179 | 11.14 | 18.36 | 30.45 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 58 | 1 | 1.14 | 4.28 | 758.95 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 492 | 41 | 1.14 | 5.07 | 454.75 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `thermal` | 35 | 0 | 1.62 | 9.32 | 15.24 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 343 | 222 | 5.17 | 19.43 | 34.14 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 804 | 127 | 1.42 | 4.24 | 18.92 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 250 | 0 | 1.32 | 5.20 | 6.32 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 476 | 0 | 1.50 | 3.11 | 12.28 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 904 | 440 | 9.65 | 16.91 | 39.18 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 86 | 62 | 2.20 | 27.43 | 80.23 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,127 | 112 | 1.16 | 3.94 | 275.77 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `thermal` | 2 | 0 | 11.73 | 12.37 | 12.37 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 597 | 78 | 1.74 | 8.16 | 491.82 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 904 | 779 | 9.62 | 18.46 | 28.55 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 86 | 15 | 1.99 | 13.28 | 161.02 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,127 | 123 | 1.15 | 4.32 | 543.82 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `thermal` | 2 | 2 | 22.28 | 23.55 | 23.55 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 597 | 296 | 3.83 | 16.98 | 987.63 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 4 | 4 | 17.50 | 17.74 | 17.74 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 803 | 137 | 1.42 | 4.24 | 18.92 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 264 | 0 | 1.32 | 5.21 | 9.29 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 509 | 0 | 1.50 | 3.12 | 13.82 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 968 | 459 | 9.35 | 16.86 | 71.14 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 72 | 68 | 3.65 | 59.41 | 180.36 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,153 | 121 | 1.16 | 4.33 | 275.77 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 599 | 82 | 1.65 | 7.81 | 537.18 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 968 | 830 | 9.31 | 18.58 | 28.84 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 72 | 2 | 1.56 | 8.96 | 362.12 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,153 | 126 | 1.15 | 4.30 | 543.82 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 599 | 281 | 3.73 | 16.59 | 1,078.72 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 788 | 110 | 1.68 | 9.48 | 18.34 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 284 | 0 | 1.57 | 5.61 | 7.39 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 825 | 0 | 1.53 | 3.39 | 8.07 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 796 | 330 | 10.18 | 16.87 | 24.14 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 71 | 27 | 1.30 | 14.53 | 298.88 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 937 | 124 | 1.17 | 5.67 | 137.62 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `thermal` | 5 | 0 | 7.52 | 7.54 | 7.64 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 633 | 110 | 2.18 | 12.73 | 19.04 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 796 | 694 | 11.05 | 20.34 | 37.29 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 71 | 39 | 2.49 | 19.25 | 592.49 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 937 | 147 | 1.18 | 7.21 | 262.56 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `thermal` | 5 | 0 | 14.52 | 14.56 | 14.74 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 633 | 384 | 3.43 | 26.94 | 37.97 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 889 | 157 | 1.68 | 10.45 | 18.36 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 321 | 0 | 1.31 | 5.65 | 7.49 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 930 | 0 | 1.54 | 3.47 | 13.03 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 913 | 398 | 9.98 | 16.85 | 49.69 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 45 | 32 | 4.56 | 38.79 | 314.95 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 1,100 | 129 | 1.16 | 5.12 | 155.88 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 714 | 135 | 2.27 | 12.33 | 25.48 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 913 | 766 | 10.55 | 21.06 | 37.30 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 45 | 16 | 7.25 | 15.87 | 627.38 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 1,100 | 146 | 1.19 | 6.71 | 297.41 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 714 | 443 | 3.41 | 27.76 | 34.66 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 2 | 2 | 17.56 | 17.56 | 17.56 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 851 | 164 | 1.68 | 10.48 | 18.36 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 310 | 0 | 1.31 | 5.65 | 7.50 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 897 | 0 | 1.54 | 3.47 | 8.99 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 893 | 380 | 9.84 | 16.88 | 82.41 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 44 | 40 | 8.58 | 68.74 | 326.21 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 1,098 | 147 | 1.16 | 5.42 | 245.24 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 743 | 142 | 2.27 | 12.60 | 493.85 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 893 | 746 | 10.41 | 20.40 | 37.35 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 44 | 10 | 3.71 | 11.15 | 647.69 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 1,098 | 148 | 1.17 | 6.68 | 482.49 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 743 | 457 | 3.43 | 27.38 | 983.74 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `kv_read` | 22 | 0 | 8.21 | 9.68 | 13.67 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 256 | 39 | 2.40 | 10.18 | 18.91 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 745 | 0 | 1.14 | 3.20 | 8.82 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 78 | 30 | 14.45 | 16.39 | 17.52 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 179 | 0 | 1.02 | 7.39 | 239.72 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 363 | 18 | 1.15 | 2.94 | 25.54 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 232 | 24 | 2.05 | 7.63 | 17.07 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 78 | 78 | 17.01 | 18.94 | 29.39 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 179 | 37 | 1.08 | 8.80 | 478.98 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 363 | 22 | 1.14 | 3.26 | 32.71 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 232 | 137 | 5.02 | 21.32 | 34.14 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 21 | 14 | 15.50 | 17.25 | 17.43 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 381 | 129 | 2.41 | 12.97 | 18.92 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 918 | 0 | 1.27 | 3.09 | 14.44 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 843 | 528 | 10.51 | 17.16 | 39.98 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 208 | 113 | 1.28 | 26.90 | 275.10 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,248 | 130 | 1.18 | 4.24 | 151.79 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 669 | 180 | 2.96 | 10.63 | 29.57 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 843 | 727 | 10.59 | 18.21 | 29.68 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 208 | 75 | 2.40 | 14.06 | 552.40 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,248 | 149 | 1.16 | 4.32 | 294.33 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 669 | 376 | 5.17 | 18.40 | 34.14 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 19 | 19 | 17.19 | 17.29 | 17.49 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 348 | 117 | 2.41 | 12.97 | 18.92 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 863 | 0 | 1.27 | 3.10 | 15.69 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 899 | 565 | 9.70 | 17.17 | 72.21 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 101 | 76 | 2.59 | 58.47 | 311.33 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,246 | 133 | 1.18 | 4.81 | 269.26 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 686 | 185 | 2.88 | 10.63 | 40.60 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 899 | 752 | 9.48 | 18.46 | 29.45 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 101 | 14 | 1.77 | 10.54 | 625.17 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,246 | 153 | 1.15 | 4.37 | 530.55 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 686 | 377 | 5.08 | 18.03 | 34.14 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 23 | 7 | 14.58 | 16.88 | 17.17 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 305 | 86 | 3.13 | 12.85 | 18.36 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 891 | 0 | 1.30 | 3.15 | 13.57 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 754 | 474 | 10.06 | 17.18 | 24.26 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 71 | 16 | 1.05 | 12.29 | 203.50 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 890 | 131 | 1.20 | 6.12 | 113.15 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 463 | 139 | 2.47 | 15.36 | 21.06 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 754 | 664 | 10.37 | 20.25 | 35.38 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 71 | 25 | 1.69 | 14.02 | 403.29 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 890 | 143 | 1.18 | 7.24 | 215.78 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 463 | 267 | 3.91 | 29.05 | 34.07 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 22 | 13 | 16.29 | 17.04 | 17.48 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 310 | 90 | 3.13 | 13.03 | 18.36 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 907 | 0 | 1.33 | 3.23 | 15.93 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 880 | 561 | 9.96 | 17.27 | 49.91 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 40 | 26 | 2.54 | 39.80 | 203.88 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 990 | 125 | 1.21 | 5.57 | 154.88 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 382 | 125 | 2.64 | 16.30 | 29.83 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 880 | 755 | 10.03 | 21.00 | 37.65 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 40 | 20 | 5.01 | 17.94 | 405.31 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 990 | 138 | 1.22 | 6.09 | 295.39 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 382 | 243 | 5.09 | 31.00 | 37.36 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 24 | 18 | 16.37 | 17.13 | 17.60 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 294 | 86 | 3.13 | 13.08 | 18.36 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 882 | 0 | 1.33 | 3.31 | 16.30 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 833 | 526 | 9.82 | 17.25 | 82.48 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 53 | 38 | 4.71 | 70.20 | 261.35 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 984 | 140 | 1.21 | 5.64 | 154.88 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 422 | 140 | 2.64 | 16.36 | 37.82 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 833 | 710 | 9.89 | 20.89 | 37.59 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 53 | 14 | 5.14 | 11.10 | 520.58 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 984 | 134 | 1.20 | 6.08 | 295.39 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 422 | 268 | 5.09 | 30.52 | 36.78 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `kv_read` | 13 | 0 | 5.08 | 7.15 | 9.49 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 806 | 62 | 1.42 | 3.14 | 18.87 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 227 | 0 | 1.33 | 5.12 | 6.13 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 387 | 0 | 1.49 | 3.02 | 6.67 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 629 | 254 | 12.22 | 16.50 | 21.17 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 95 | 3 | 1.03 | 8.99 | 396.39 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 964 | 110 | 1.16 | 3.47 | 233.91 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `thermal` | 22 | 2 | 3.09 | 14.86 | 17.01 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 566 | 50 | 2.32 | 7.27 | 21.74 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 629 | 567 | 12.62 | 19.74 | 29.29 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 95 | 4 | 1.49 | 8.24 | 792.52 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 964 | 116 | 1.16 | 4.58 | 459.95 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `thermal` | 22 | 6 | 5.84 | 15.76 | 20.43 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 566 | 298 | 3.81 | 17.59 | 34.14 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `kv_read` | 7 | 0 | 6.77 | 7.07 | 7.88 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 633 | 59 | 1.46 | 6.86 | 18.33 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 250 | 0 | 1.73 | 5.44 | 6.94 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 722 | 0 | 1.26 | 3.22 | 6.90 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 144 | 53 | 10.18 | 16.79 | 18.26 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 53 | 0 | 1.05 | 7.08 | 289.24 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 357 | 22 | 1.13 | 3.32 | 136.29 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `thermal` | 4 | 0 | 2.42 | 3.75 | 3.83 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 276 | 43 | 2.14 | 10.12 | 17.37 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 144 | 135 | 11.07 | 23.45 | 34.56 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 53 | 17 | 1.37 | 7.99 | 572.85 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 357 | 38 | 1.13 | 4.09 | 259.67 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `thermal` | 4 | 0 | 4.64 | 7.17 | 7.25 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 276 | 155 | 3.46 | 24.33 | 34.07 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 114 | 0 | 1.43 | 3.00 | 8.86 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 328 | 41 | 1.28 | 5.11 | 19.04 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 220 | 0 | 1.25 | 1.25 | 2.66 |
| `n5_vs_b200` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 147 | 0 | 1.20 | 1.31 | 1.70 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 18 | 15 | 10.40 | 18.64 | 19.81 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 218 | 3 | 1.01 | 4.01 | 19.71 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 786 | 68 | 1.17 | 3.60 | 19.13 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `thermal` | 778 | 0 | 2.39 | 8.61 | 13.02 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 649 | 87 | 1.07 | 1.41 | 19.83 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `compute` | 18 | 15 | 10.40 | 18.64 | 19.81 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 218 | 3 | 1.08 | 2.10 | 19.71 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 786 | 90 | 1.11 | 3.94 | 26.82 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `thermal` | 778 | 0 | 3.20 | 8.35 | 13.02 |
| `n5_vs_b200` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 649 | 207 | 1.84 | 2.33 | 38.00 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 48 | 11 | 11.94 | 14.99 | 17.54 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 336 | 83 | 2.41 | 10.78 | 18.92 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 950 | 0 | 1.27 | 3.08 | 12.18 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 541 | 292 | 12.20 | 17.03 | 21.38 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 146 | 1 | 1.03 | 9.16 | 251.78 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 924 | 96 | 1.19 | 3.56 | 26.06 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 497 | 69 | 2.60 | 8.83 | 18.12 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 541 | 502 | 12.34 | 19.00 | 29.76 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 146 | 26 | 1.27 | 8.24 | 503.28 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 924 | 100 | 1.16 | 4.35 | 33.80 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 497 | 311 | 4.42 | 18.89 | 34.14 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 4 | 0 | 10.97 | 11.12 | 13.34 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 242 | 51 | 3.13 | 12.40 | 18.36 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 721 | 0 | 1.12 | 3.33 | 10.86 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 71 | 31 | 10.59 | 16.92 | 18.46 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 64 | 1 | 1.05 | 4.77 | 200.27 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 208 | 0 | 1.12 | 2.49 | 8.47 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 92 | 19 | 2.57 | 15.62 | 17.14 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 71 | 69 | 11.06 | 22.35 | 30.50 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 64 | 11 | 1.21 | 6.41 | 396.61 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 208 | 0 | 1.12 | 3.21 | 15.42 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 92 | 49 | 4.86 | 31.01 | 34.07 |
| `n6_vs_a100` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 105 | 0 | 1.39 | 2.60 | 8.93 |
| `n6_vs_a100` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 196 | 42 | 1.65 | 11.18 | 19.07 |
| `n6_vs_a100` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 397 | 0 | 1.15 | 1.20 | 2.58 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 27 | 21 | 10.45 | 19.08 | 20.30 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 956 | 0 | 1.01 | 5.74 | 11.39 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 720 | 77 | 1.22 | 3.36 | 18.95 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 575 | 99 | 1.16 | 1.73 | 20.02 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `compute` | 27 | 21 | 10.45 | 19.08 | 20.30 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 956 | 0 | 1.08 | 5.72 | 11.39 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 720 | 103 | 1.13 | 3.58 | 26.04 |
| `n6_vs_a100` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 575 | 199 | 1.84 | 2.33 | 38.00 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 113 | 0 | 1.19 | 2.73 | 8.68 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 430 | 41 | 1.22 | 3.10 | 19.04 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `thermal` | 94 | 0 | 1.10 | 1.14 | 1.63 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 100 | 0 | 1.16 | 1.18 | 1.23 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 9 | 6 | 14.02 | 17.84 | 18.76 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 240 | 2 | 1.01 | 1.77 | 18.43 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 770 | 51 | 1.15 | 3.03 | 18.95 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `thermal` | 765 | 0 | 1.15 | 3.15 | 7.71 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 629 | 54 | 1.02 | 1.14 | 18.05 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `compute` | 9 | 6 | 14.02 | 17.84 | 18.76 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 240 | 8 | 1.03 | 1.86 | 27.21 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 770 | 61 | 1.09 | 3.09 | 26.82 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `thermal` | 765 | 0 | 1.16 | 3.15 | 7.71 |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 629 | 188 | 1.84 | 2.33 | 38.00 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `kv_read` | 147 | 0 | 1.46 | 2.58 | 5.01 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `link_latency` | 309 | 44 | 1.26 | 4.05 | 19.07 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `gpu` | `in_hbm` | `weight_read` | 184 | 0 | 1.15 | 1.17 | 1.36 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `compute` | 18 | 10 | 15.11 | 17.48 | 19.30 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `kv_read` | 962 | 0 | 1.01 | 2.42 | 11.39 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `link_latency` | 710 | 67 | 1.15 | 2.86 | 18.83 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_kv_store` | `weight_read` | 560 | 50 | 1.04 | 1.21 | 17.18 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `compute` | 18 | 10 | 15.11 | 17.48 | 19.30 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `kv_read` | 962 | 4 | 1.03 | 2.35 | 23.92 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `link_latency` | 710 | 85 | 1.10 | 2.89 | 26.04 |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `rom` | `in_rom` | `weight_read` | 560 | 184 | 1.84 | 2.33 | 38.00 |

## Per model, per context, per batch and per design class

Each row is that class's **fastest** feasible design at that batch, read against the iso-area GPU comparator the published study already chose for it. The `densest` pick of every class is in `analytical.json` beside it.

**The ROM-versus-GPU ratio under speculation is `T_cycle(GPU) / T_cycle(ROM)` and carries no `tau` at all.** The acceptance length is a property of the model and its drafter, not of the machine, so it is the same on both sides and cancels out of the ratio. Every movement in the last column is therefore a machine effect and nothing else.

### `n5_vs_b200-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 15,555.9 | 1,390.0-2,580.1 | 47.45 | **no** | `b200_sxm-x96-nvl72-hybrid` | 4,014.6 | 3,907.3-7,252.5 | 4.36 | yes | 3.875x | 0.356x | 0.092x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,969.3 | 10,864.0-20,165.1 | 2.33 | yes | `b200_sxm-x87-nvl72-hybrid` | 3,945.6 | 3,620.1-6,719.4 | 4.62 | yes | 1.513x | 3.001x | 1.984x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 15,555.9 | 1,390.0-2,580.1 | 47.45 | **no** | `b200_sxm-x96-nvl72-hybrid` | 4,014.6 | 3,907.3-7,252.5 | 4.36 | yes | 3.875x | 0.356x | 0.092x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 5,969.3 | 10,864.0-20,165.1 | 2.33 | yes | `b200_sxm-x87-nvl72-hybrid` | 3,945.6 | 3,620.1-6,719.4 | 4.62 | yes | 1.513x | 3.001x | 1.984x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 15,555.9 | 1,390.0-2,580.1 | 47.45 | **no** | `b200_sxm-x96-nvl72-hybrid` | 3,752.8 | 3,529.0-6,550.4 | 4.51 | yes | 4.145x | 0.394x | 0.095x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 5,942.8 | 11,057.6-20,524.4 | 2.28 | yes | `b200_sxm-x116-nvl72-hybrid` | 3,895.4 | 4,047.4-7,512.5 | 4.08 | yes | 1.526x | 2.732x | 1.791x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 15,555.9 | 1,390.0-2,580.1 | 47.45 | **no** | `b200_sxm-x96-nvl72-hybrid` | 3,327.1 | 3,024.9-5,614.6 | 4.66 | yes | 4.675x | 0.460x | 0.098x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,925.3 | 9,696.6-17,998.1 | 2.59 | yes | `b200_sxm-x231-nvl72-hybrid` | 3,819.8 | 4,026.3-7,473.3 | 4.02 | yes | 1.551x | 2.408x | 1.553x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 15,555.9 | 1,390.0-2,580.1 | 47.45 | **no** | `b200_sxm-x96-nvl72-hybrid` | 2,730.9 | 2,407.1-4,467.9 | 4.81 | yes | 5.696x | 0.577x | 0.101x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,864.5 | 8,957.1-16,625.6 | 2.78 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,671.5 | 4,033.5-7,486.7 | 3.86 | yes | 1.597x | 2.221x | 1.390x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 15,555.9 | 1,390.0-2,580.1 | 47.45 | **no** | `b200_sxm-x96-nvl72-hybrid` | 2,049.8 | 1,805.4-3,351.0 | 4.81 | yes | 7.589x | 0.770x | 0.101x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,685.6 | 6,972.2-12,941.2 | 3.46 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,184.1 | 3,206.1-5,950.9 | 4.21 | yes | 1.786x | 2.175x | 1.218x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 13,436.0 | 1,404.5-2,607.0 | 40.56 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,589.9 | 1,356.5-2,517.8 | 4.97 | yes | 8.451x | 1.035x | 0.123x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,358.7 | 4,825.4-8,956.5 | 4.71 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,544.0 | 2,291.6-4,253.5 | 4.71 | yes | 2.106x | 2.106x | 1.000x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 6,357.0 | 834.2-1,548.3 | 32.31 | **no** | `b200_sxm-x173-nvl72-hybrid` | 926.6 | 645.5-1,198.1 | 6.09 | yes | 6.860x | 1.292x | 0.188x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 4,186.1 | 2,028.2-3,764.7 | 8.75 | **no** | `b200_sxm-x231-nvl72-hybrid` | 1,060.1 | 770.9-1,430.8 | 5.83 | yes | 3.949x | 2.631x | 0.666x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 2,380.6 | 359.6-667.5 | 28.07 | **no** | `b200_sxm-x179-expert` | 483.8 | 262.2-486.6 | 7.82 | yes | 4.921x | 1.372x | 0.279x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,803.6 | 245.0-454.8 | 48.52 | **no** | `b200_sxm-x347-expert` | 664.0 | 496.9-922.3 | 5.67 | yes | 4.222x | 0.493x | 0.117x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 625.4 | 91.1-169.2 | 29.10 | **no** | `b200_sxm-x179-expert` | 235.1 | 66.8-124.0 | 14.92 | **no** | 2.660x | 1.364x | 0.513x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,209.7 | 221.3-410.8 | 23.17 | **no** | `b200_sxm-x347-expert` | 379.9 | 128.9-239.2 | 12.50 | **no** | 3.185x | 1.717x | 0.539x |

**Does the ratio compress?** Of 20 class rows in this study, 14 move the ROM-versus-GPU ratio DOWN under speculation and 6 move it UP. The movement spans 0.092x to 1.984x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 11,839.5 | 981.8-1,822.4 | 51.13 | **no** | `a100_sxm_80gb-x260-tensor` | 1,152.3 | 1,266.9-2,351.5 | 3.86 | yes | 10.275x | 0.775x | 0.075x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,910.8 | 8,684.9-16,120.2 | 2.89 | yes | `a100_sxm_80gb-x224-tensor` | 1,146.5 | 1,236.1-2,294.4 | 3.93 | yes | 5.156x | 7.026x | 1.363x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 11,839.5 | 981.8-1,822.4 | 51.13 | **no** | `a100_sxm_80gb-x260-tensor` | 1,019.5 | 792.8-1,471.6 | 5.45 | yes | 11.612x | 1.238x | 0.107x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,910.8 | 8,684.9-16,120.2 | 2.89 | yes | `a100_sxm_80gb-x224-tensor` | 1,013.8 | 781.1-1,449.9 | 5.50 | yes | 5.830x | 11.118x | 1.907x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 11,839.5 | 981.8-1,822.4 | 51.13 | **no** | `a100_sxm_80gb-x260-tensor` | 829.0 | 455.0-844.6 | 7.72 | yes | 14.282x | 2.158x | 0.151x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 5,910.8 | 8,684.9-16,120.2 | 2.89 | yes | `a100_sxm_80gb-x224-tensor` | 823.7 | 451.7-838.4 | 7.73 | yes | 7.176x | 19.227x | 2.679x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 11,839.5 | 981.8-1,822.4 | 51.13 | **no** | `a100_sxm_80gb-x260-hybrid` | 665.9 | 218.5-405.6 | 12.92 | **no** | 17.781x | 4.493x | 0.253x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,871.4 | 7,931.3-14,721.5 | 3.14 | yes | `a100_sxm_80gb-x448-hybrid` | 665.0 | 224.7-417.1 | 12.55 | **no** | 8.829x | 35.299x | 3.998x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 11,839.5 | 981.8-1,822.4 | 51.13 | **no** | `a100_sxm_80gb-x260-hybrid` | 665.9 | 218.5-405.6 | 12.92 | **no** | 17.781x | 4.493x | 0.253x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,794.4 | 7,255.6-13,467.3 | 3.39 | yes | `a100_sxm_80gb-x672-hybrid` | 665.0 | 226.7-420.7 | 12.44 | **no** | 8.713x | 32.010x | 3.674x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 11,839.5 | 981.8-1,822.4 | 51.13 | **no** | `a100_sxm_80gb-x260-hybrid` | 665.9 | 218.5-405.6 | 12.92 | **no** | 17.781x | 4.493x | 0.253x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,555.2 | 5,498.8-10,206.6 | 4.28 | yes | `a100_sxm_80gb-x672-hybrid` | 665.0 | 226.7-420.7 | 12.44 | **no** | 8.353x | 24.260x | 2.904x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 11,839.5 | 981.8-1,822.4 | 51.13 | **no** | `a100_sxm_80gb-x260-hybrid` | 541.7 | 201.5-374.0 | 11.40 | **no** | 21.858x | 4.873x | 0.223x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 5,157.9 | 4,587.2-8,514.4 | 4.77 | yes | `a100_sxm_80gb-x672-hybrid` | 665.0 | 226.7-420.7 | 12.44 | **no** | 7.756x | 20.238x | 2.609x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 5,207.3 | 635.2-1,179.0 | 34.76 | **no** | `a100_sxm_80gb-x337-hybrid` | 302.0 | 164.6-305.6 | 7.78 | yes | 17.241x | 3.858x | 0.224x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,852.0 | 2,051.8-3,808.3 | 7.96 | **no** | `a100_sxm_80gb-x672-hybrid` | 445.7 | 194.2-360.4 | 9.73 | **no** | 8.642x | 10.567x | 1.223x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,409.5 | 160.3-297.6 | 37.27 | **no** | `a100_sxm_80gb-x337-expert` | 222.3 | 109.3-202.9 | 8.62 | **no** | 6.340x | 1.467x | 0.231x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,045.7 | 176.7-328.1 | 49.07 | **no** | `a100_sxm_80gb-x672-expert` | 285.0 | 214.5-398.1 | 5.63 | yes | 7.179x | 0.824x | 0.115x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 356.6 | 51.9-96.3 | 29.14 | **no** | `a100_sxm_80gb-x337-expert` | 139.7 | 27.7-51.4 | 21.40 | **no** | 2.554x | 1.875x | 0.734x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 596.5 | 140.2-260.3 | 18.04 | **no** | `a100_sxm_80gb-x672-expert` | 206.5 | 55.0-102.0 | 15.93 | **no** | 2.889x | 2.551x | 0.883x |

**Does the ratio compress?** Of 20 class rows in this study, 12 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.075x to 3.998x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 8 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 2,566.8-4,764.3 | 29.54 | **no** | `b200_sxm-x49-nvl72-tensor` | 4,065.4 | 9,553.4-17,732.3 | 1.80 | yes | 4.399x | 0.269x | 0.061x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,986.1 | 14,516.8-26,945.1 | 1.75 | yes | `b200_sxm-x58-nvl72-tensor` | 4,173.9 | 10,240.8-19,008.3 | 1.73 | yes | 1.434x | 1.418x | 0.988x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 2,566.8-4,764.3 | 29.54 | **no** | `b200_sxm-x49-nvl72-tensor` | 3,804.6 | 7,550.2-14,014.1 | 2.14 | yes | 4.701x | 0.340x | 0.072x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,986.1 | 14,516.8-26,945.1 | 1.75 | yes | `b200_sxm-x58-nvl72-tensor` | 3,933.1 | 8,161.7-15,149.2 | 2.04 | yes | 1.522x | 1.779x | 1.169x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 2,566.8-4,764.3 | 29.54 | **no** | `b200_sxm-x49-nvl72-tensor` | 3,379.4 | 5,461.4-10,137.0 | 2.62 | yes | 5.292x | 0.470x | 0.089x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 5,978.8 | 14,502.4-26,918.3 | 1.75 | yes | `b200_sxm-x116-nvl72-hybrid` | 3,895.4 | 8,344.7-15,488.8 | 1.98 | yes | 1.535x | 1.738x | 1.132x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 2,566.8-4,764.3 | 29.54 | **no** | `b200_sxm-x49-nvl72-tensor` | 2,781.4 | 3,760.9-6,980.8 | 3.14 | yes | 6.430x | 0.682x | 0.106x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,964.3 | 14,473.6-26,865.0 | 1.75 | yes | `b200_sxm-x231-nvl72-hybrid` | 3,819.8 | 8,293.2-15,393.2 | 1.95 | yes | 1.561x | 1.745x | 1.118x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 2,566.8-4,764.3 | 29.54 | **no** | `b200_sxm-x49-nvl72-tensor` | 2,094.6 | 2,526.1-4,688.8 | 3.52 | yes | 8.539x | 1.016x | 0.119x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,915.6 | 13,673.5-25,379.9 | 1.83 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,671.5 | 7,062.7-13,109.3 | 2.20 | yes | 1.611x | 1.936x | 1.202x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 16,612.5 | 2,558.1-4,748.2 | 27.53 | **no** | `b200_sxm-x110-nvl72-hybrid` | 2,185.1 | 2,629.9-4,881.4 | 3.52 | yes | 7.603x | 0.973x | 0.128x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,782.4 | 11,266.7-20,912.4 | 2.18 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,184.1 | 4,864.4-9,029.0 | 2.78 | yes | 1.816x | 2.316x | 1.275x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 16,612.5 | 2,558.1-4,748.2 | 27.53 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,926.0 | 2,131.2-3,955.7 | 3.83 | yes | 8.625x | 1.200x | 0.139x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 5,568.7 | 693.9-1,288.0 | 34.03 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,589.9 | 1,639.4-3,042.9 | 4.11 | yes | 3.503x | 0.423x | 0.121x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,666.3 | 1,330.3-2,469.3 | 21.25 | **no** | `b200_sxm-x173-nvl72-hybrid` | 926.6 | 703.6-1,305.9 | 5.58 | yes | 7.194x | 1.891x | 0.263x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 5,568.7 | 693.9-1,288.0 | 34.03 | **no** | `b200_sxm-x231-nvl72-hybrid` | 1,060.1 | 855.1-1,587.2 | 5.26 | yes | 5.253x | 0.812x | 0.154x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,847.6 | 338.1-627.5 | 23.17 | **no** | `b200_sxm-x173-expert` | 474.9 | 272.7-506.2 | 7.38 | yes | 3.890x | 1.240x | 0.319x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 3,809.5 | 563.8-1,046.6 | 28.65 | **no** | `b200_sxm-x347-expert` | 664.0 | 534.4-992.0 | 5.27 | yes | 5.737x | 1.055x | 0.184x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 566.8 | 193.8-359.6 | 12.40 | **no** | `b200_sxm-x173-expert` | 228.7 | 69.6-129.1 | 13.94 | **no** | 2.478x | 2.786x | 1.124x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,273.2 | 503.6-934.8 | 10.72 | **no** | `b200_sxm-x347-expert` | 379.9 | 139.0-258.0 | 11.59 | **no** | 3.352x | 3.624x | 1.081x |

**Does the ratio compress?** Of 20 class rows in this study, 13 move the ROM-versus-GPU ratio DOWN under speculation and 7 move it UP. The movement spans 0.061x to 1.275x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 6 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 1,814.8-3,368.6 | 32.22 | **no** | `a100_sxm_80gb-x136-tensor` | 1,120.0 | 1,449.8-2,691.1 | 3.28 | yes | 12.312x | 1.252x | 0.102x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5,932.5 | 12,697.1-23,567.5 | 1.98 | yes | `a100_sxm_80gb-x112-tensor` | 1,106.1 | 1,436.8-2,666.8 | 3.26 | yes | 5.364x | 8.837x | 1.648x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 1,814.8-3,368.6 | 32.22 | **no** | `a100_sxm_80gb-x136-tensor` | 987.6 | 863.0-1,601.8 | 4.85 | yes | 13.963x | 2.103x | 0.151x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5,932.5 | 12,697.1-23,567.5 | 1.98 | yes | `a100_sxm_80gb-x112-tensor` | 973.8 | 859.1-1,594.7 | 4.81 | yes | 6.092x | 14.779x | 2.426x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 1,814.8-3,368.6 | 32.22 | **no** | `a100_sxm_80gb-x136-tensor` | 799.3 | 479.9-890.8 | 7.06 | yes | 17.253x | 3.782x | 0.219x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 5,925.3 | 12,699.0-23,571.0 | 1.98 | yes | `a100_sxm_80gb-x224-tensor` | 823.7 | 479.7-890.4 | 7.28 | yes | 7.194x | 26.472x | 3.680x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 1,814.8-3,368.6 | 32.22 | **no** | `a100_sxm_80gb-x136-hybrid` | 690.8 | 1,031.9-1,915.3 | 2.84 | yes | 19.961x | 1.759x | 0.088x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,911.1 | 12,677.0-23,530.1 | 1.98 | yes | `a100_sxm_80gb-x448-hybrid` | 665.0 | 1,031.9-1,915.3 | 2.73 | yes | 8.888x | 12.285x | 1.382x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 1,814.8-3,368.6 | 32.22 | **no** | `a100_sxm_80gb-x136-hybrid` | 690.8 | 1,031.9-1,915.3 | 2.84 | yes | 19.961x | 1.759x | 0.088x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,846.0 | 11,844.8-21,985.5 | 2.09 | yes | `a100_sxm_80gb-x672-hybrid` | 665.0 | 1,031.9-1,915.3 | 2.73 | yes | 8.790x | 11.479x | 1.306x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 1,814.8-3,368.6 | 32.22 | **no** | `a100_sxm_80gb-x136-hybrid` | 567.9 | 650.5-1,207.4 | 3.70 | yes | 24.280x | 2.790x | 0.115x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,650.9 | 9,429.8-17,503.0 | 2.54 | yes | `a100_sxm_80gb-x672-hybrid` | 665.0 | 1,031.9-1,915.3 | 2.73 | yes | 8.497x | 9.138x | 1.075x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 12,954.3 | 1,854.3-3,441.9 | 29.62 | **no** | `a100_sxm_80gb-x335-hybrid` | 588.8 | 754.0-1,399.5 | 3.31 | yes | 22.003x | 2.459x | 0.112x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,297.4 | 6,698.4-12,433.2 | 3.35 | yes | `a100_sxm_80gb-x672-hybrid` | 665.0 | 1,031.9-1,915.3 | 2.73 | yes | 7.965x | 6.491x | 0.815x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,970.1 | 964.2-1,789.6 | 21.86 | **no** | `a100_sxm_80gb-x335-hybrid` | 301.9 | 333.5-619.0 | 3.84 | yes | 16.464x | 2.891x | 0.176x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,851.6 | 2,446.5-4,541.1 | 6.68 | yes | `a100_sxm_80gb-x672-hybrid` | 445.7 | 473.9-879.6 | 3.99 | yes | 8.641x | 5.163x | 0.597x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 1,623.3 | 344.0-638.5 | 20.01 | **no** | `a100_sxm_80gb-x272-expert` | 202.4 | 117.1-217.3 | 7.33 | yes | 8.018x | 2.939x | 0.367x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,556.0 | 406.9-755.2 | 26.64 | **no** | `a100_sxm_80gb-x672-expert` | 285.0 | 281.8-523.1 | 4.29 | yes | 8.970x | 1.444x | 0.161x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 566.8 | 129.1-239.5 | 18.62 | **no** | `a100_sxm_80gb-x335-expert` | 139.1 | 36.4-67.6 | 16.20 | **no** | 4.075x | 3.545x | 0.870x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 657.8 | 151.8-281.8 | 18.37 | **no** | `a100_sxm_80gb-x672-expert` | 206.5 | 72.8-135.1 | 12.03 | **no** | 3.186x | 2.085x | 0.655x |

**Does the ratio compress?** Of 20 class rows in this study, 14 move the ROM-versus-GPU ratio DOWN under speculation and 6 move it UP. The movement spans 0.088x to 3.680x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 2,566.8-4,764.3 | 29.54 | **no** | `b200_sxm-x49-nvl72-tensor` | 4,065.4 | 9,553.4-17,732.3 | 1.80 | yes | 4.399x | 0.269x | 0.061x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,986.1 | 14,516.8-26,945.1 | 1.75 | yes | `b200_sxm-x58-nvl72-tensor` | 4,173.9 | 10,240.8-19,008.3 | 1.73 | yes | 1.434x | 1.418x | 0.988x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 2,566.8-4,764.3 | 29.54 | **no** | `b200_sxm-x49-nvl72-tensor` | 3,804.6 | 7,550.2-14,014.1 | 2.14 | yes | 4.701x | 0.340x | 0.072x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 5,986.1 | 14,516.8-26,945.1 | 1.75 | yes | `b200_sxm-x58-nvl72-tensor` | 3,933.1 | 8,161.7-15,149.2 | 2.04 | yes | 1.522x | 1.779x | 1.169x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 2,566.8-4,764.3 | 29.54 | **no** | `b200_sxm-x49-nvl72-tensor` | 3,379.4 | 5,461.4-10,137.0 | 2.62 | yes | 5.292x | 0.470x | 0.089x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 5,978.8 | 14,502.4-26,918.3 | 1.75 | yes | `b200_sxm-x116-nvl72-hybrid` | 3,895.4 | 8,344.7-15,488.8 | 1.98 | yes | 1.535x | 1.738x | 1.132x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 2,566.8-4,764.3 | 29.54 | **no** | `b200_sxm-x49-nvl72-tensor` | 2,781.4 | 3,760.9-6,980.8 | 3.14 | yes | 6.430x | 0.682x | 0.106x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,964.3 | 14,473.6-26,865.0 | 1.75 | yes | `b200_sxm-x231-nvl72-hybrid` | 3,819.8 | 8,293.2-15,393.2 | 1.95 | yes | 1.561x | 1.745x | 1.118x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17,885.6 | 2,566.8-4,764.3 | 29.54 | **no** | `b200_sxm-x49-nvl72-tensor` | 2,094.6 | 2,526.1-4,688.8 | 3.52 | yes | 8.539x | 1.016x | 0.119x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,915.6 | 13,673.5-25,379.9 | 1.83 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,671.5 | 7,062.7-13,109.3 | 2.20 | yes | 1.611x | 1.936x | 1.202x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 16,612.5 | 2,558.1-4,748.2 | 27.53 | **no** | `b200_sxm-x110-nvl72-hybrid` | 2,185.1 | 2,629.9-4,881.4 | 3.52 | yes | 7.603x | 0.973x | 0.128x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,782.4 | 11,266.7-20,912.4 | 2.18 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,184.1 | 4,864.4-9,029.0 | 2.78 | yes | 1.816x | 2.316x | 1.275x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 16,612.5 | 2,558.1-4,748.2 | 27.53 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,926.1 | 2,131.2-3,955.7 | 3.83 | yes | 8.625x | 1.200x | 0.139x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 5,568.7 | 693.9-1,288.0 | 34.03 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,589.9 | 1,639.4-3,042.9 | 4.11 | yes | 3.503x | 0.423x | 0.121x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,666.3 | 1,330.3-2,469.3 | 21.25 | **no** | `b200_sxm-x173-nvl72-hybrid` | 926.6 | 703.6-1,305.9 | 5.58 | yes | 7.194x | 1.891x | 0.263x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 5,568.7 | 693.9-1,288.0 | 34.03 | **no** | `b200_sxm-x231-nvl72-hybrid` | 1,060.1 | 855.1-1,587.2 | 5.26 | yes | 5.253x | 0.812x | 0.154x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,847.6 | 338.1-627.5 | 23.17 | **no** | `b200_sxm-x173-expert` | 474.9 | 272.7-506.2 | 7.38 | yes | 3.890x | 1.240x | 0.319x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 3,809.5 | 563.8-1,046.6 | 28.65 | **no** | `b200_sxm-x347-expert` | 664.0 | 534.4-992.0 | 5.27 | yes | 5.737x | 1.055x | 0.184x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 566.8 | 193.8-359.6 | 12.40 | **no** | `b200_sxm-x173-expert` | 228.7 | 69.6-129.1 | 13.94 | **no** | 2.478x | 2.786x | 1.124x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,273.5 | 503.6-934.8 | 10.72 | **no** | `b200_sxm-x347-expert` | 379.9 | 139.0-258.0 | 11.59 | **no** | 3.352x | 3.624x | 1.081x |

**Does the ratio compress?** Of 20 class rows in this study, 13 move the ROM-versus-GPU ratio DOWN under speculation and 7 move it UP. The movement spans 0.061x to 1.275x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 6 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 1,814.8-3,368.6 | 32.22 | **no** | `a100_sxm_80gb-x136-tensor` | 1,120.0 | 1,449.8-2,691.1 | 3.28 | yes | 12.312x | 1.252x | 0.102x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5,932.5 | 12,697.1-23,567.5 | 1.98 | yes | `a100_sxm_80gb-x112-tensor` | 1,106.1 | 1,436.8-2,666.8 | 3.26 | yes | 5.364x | 8.837x | 1.648x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 1,814.8-3,368.6 | 32.22 | **no** | `a100_sxm_80gb-x136-tensor` | 987.6 | 863.0-1,601.8 | 4.85 | yes | 13.963x | 2.103x | 0.151x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 5,932.5 | 12,697.1-23,567.5 | 1.98 | yes | `a100_sxm_80gb-x112-tensor` | 973.8 | 859.1-1,594.7 | 4.81 | yes | 6.092x | 14.779x | 2.426x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 1,814.8-3,368.6 | 32.22 | **no** | `a100_sxm_80gb-x136-tensor` | 799.3 | 479.9-890.8 | 7.06 | yes | 17.253x | 3.782x | 0.219x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 5,925.4 | 12,699.0-23,571.0 | 1.98 | yes | `a100_sxm_80gb-x224-tensor` | 823.7 | 479.7-890.4 | 7.28 | yes | 7.194x | 26.472x | 3.680x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 1,814.8-3,368.6 | 32.22 | **no** | `a100_sxm_80gb-x136-hybrid` | 690.8 | 1,031.9-1,915.3 | 2.84 | yes | 19.961x | 1.759x | 0.088x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,911.1 | 12,677.0-23,530.1 | 1.98 | yes | `a100_sxm_80gb-x448-hybrid` | 665.0 | 1,031.9-1,915.3 | 2.73 | yes | 8.888x | 12.285x | 1.382x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 1,814.8-3,368.6 | 32.22 | **no** | `a100_sxm_80gb-x136-hybrid` | 690.8 | 1,031.9-1,915.3 | 2.84 | yes | 19.961x | 1.759x | 0.088x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,846.1 | 11,844.8-21,985.5 | 2.09 | yes | `a100_sxm_80gb-x672-hybrid` | 665.0 | 1,031.9-1,915.3 | 2.73 | yes | 8.790x | 11.479x | 1.306x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13,789.7 | 1,814.8-3,368.6 | 32.22 | **no** | `a100_sxm_80gb-x136-hybrid` | 567.9 | 650.5-1,207.4 | 3.70 | yes | 24.280x | 2.790x | 0.115x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,651.0 | 9,429.8-17,503.0 | 2.54 | yes | `a100_sxm_80gb-x672-hybrid` | 665.0 | 1,031.9-1,915.3 | 2.73 | yes | 8.497x | 9.138x | 1.075x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 12,954.3 | 1,854.3-3,441.9 | 29.62 | **no** | `a100_sxm_80gb-x335-hybrid` | 588.8 | 754.0-1,399.5 | 3.31 | yes | 22.003x | 2.459x | 0.112x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,297.6 | 6,698.4-12,433.2 | 3.35 | yes | `a100_sxm_80gb-x672-hybrid` | 665.0 | 1,031.9-1,915.3 | 2.73 | yes | 7.966x | 6.491x | 0.815x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,970.1 | 964.2-1,789.6 | 21.86 | **no** | `a100_sxm_80gb-x335-hybrid` | 301.9 | 333.5-619.0 | 3.84 | yes | 16.464x | 2.891x | 0.176x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,852.0 | 2,446.5-4,541.1 | 6.68 | yes | `a100_sxm_80gb-x672-hybrid` | 445.7 | 473.9-879.6 | 3.99 | yes | 8.642x | 5.163x | 0.597x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 1,623.3 | 344.0-638.5 | 20.01 | **no** | `a100_sxm_80gb-x272-expert` | 202.4 | 117.1-217.3 | 7.33 | yes | 8.018x | 2.939x | 0.367x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,556.6 | 406.9-755.2 | 26.64 | **no** | `a100_sxm_80gb-x672-expert` | 285.0 | 281.8-523.1 | 4.29 | yes | 8.972x | 1.444x | 0.161x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 566.8 | 129.1-239.5 | 18.62 | **no** | `a100_sxm_80gb-x335-expert` | 139.1 | 36.4-67.6 | 16.20 | **no** | 4.075x | 3.545x | 0.870x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 658.0 | 151.8-281.8 | 18.38 | **no** | `a100_sxm_80gb-x672-expert` | 206.5 | 72.8-135.1 | 12.03 | **no** | 3.187x | 2.085x | 0.654x |

**Does the ratio compress?** Of 20 class rows in this study, 14 move the ROM-versus-GPU ratio DOWN under speculation and 6 move it UP. The movement spans 0.088x to 3.680x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x63` | 12,688.5 | 16,595.9-30,804.2 | 3.24 | yes | `b200_sxm-x32-nvl72-tensor` | 3,539.8 | 8,309.5-15,423.6 | 1.81 | yes | 3.584x | 1.997x | 0.557x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 5,458.3 | 11,666.7-21,655.0 | 1.98 | yes | `b200_sxm-x58-nvl72-tensor` | 3,921.7 | 10,593.1-19,662.2 | 1.57 | yes | 1.392x | 1.101x | 0.791x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,320.2 | 1,473.2-2,734.5 | 18.19 | **no** | `b200_sxm-x173-nvl72-hybrid` | 3,852.3 | 10,822.1-20,087.2 | 1.51 | yes | 1.641x | 0.136x | 0.083x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 4,447.5 | 10,847.0-20,133.4 | 1.74 | yes | `b200_sxm-x953-nvl72-hybrid` | 3,590.6 | 10,165.5-18,868.5 | 1.50 | yes | 1.239x | 1.067x | 0.861x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,320.2 | 1,473.2-2,734.5 | 18.19 | **no** | `b200_sxm-x173-nvl72-hybrid` | 3,775.7 | 10,027.0-18,611.4 | 1.60 | yes | 1.674x | 0.147x | 0.088x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 4,447.5 | 10,847.0-20,133.4 | 1.74 | yes | `b200_sxm-x953-nvl72-hybrid` | 3,590.6 | 10,165.5-18,868.5 | 1.50 | yes | 1.239x | 1.067x | 0.861x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,320.2 | 1,473.2-2,734.5 | 18.19 | **no** | `b200_sxm-x173-nvl72-hybrid` | 3,500.4 | 8,020.5-14,887.2 | 1.85 | yes | 1.806x | 0.184x | 0.102x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 4,447.5 | 10,847.0-20,133.4 | 1.74 | yes | `b200_sxm-x953-nvl72-hybrid` | 3,590.6 | 10,165.5-18,868.5 | 1.50 | yes | 1.239x | 1.067x | 0.861x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,320.2 | 1,473.2-2,734.5 | 18.19 | **no** | `b200_sxm-x173-nvl72-hybrid` | 3,065.2 | 5,942.9-11,030.8 | 2.19 | yes | 2.062x | 0.248x | 0.120x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 4,447.5 | 10,847.0-20,133.4 | 1.74 | yes | `b200_sxm-x953-nvl72-hybrid` | 3,562.1 | 9,795.6-18,181.9 | 1.54 | yes | 1.249x | 1.107x | 0.887x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,320.2 | 1,473.2-2,734.5 | 18.19 | **no** | `b200_sxm-x173-nvl72-hybrid` | 2,479.7 | 3,996.0-7,417.0 | 2.63 | yes | 2.549x | 0.369x | 0.145x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 4,447.5 | 10,847.0-20,133.4 | 1.74 | yes | `b200_sxm-x953-nvl72-hybrid` | 3,350.8 | 7,599.7-14,106.0 | 1.87 | yes | 1.327x | 1.427x | 1.075x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,320.2 | 1,473.2-2,734.5 | 18.19 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,840.8 | 2,498.5-4,637.6 | 3.12 | yes | 3.433x | 0.590x | 0.172x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 3,760.8 | 7,873.5-14,614.3 | 2.03 | yes | `b200_sxm-x953-nvl72-hybrid` | 3,001.6 | 5,343.1-9,917.5 | 2.38 | yes | 1.253x | 1.474x | 1.176x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349-romfill` | 2,332.0 | 566.5-1,051.5 | 17.45 | **no** | `b200_sxm-x178-nvl72-hybrid` | 878.5 | 756.4-1,403.9 | 4.92 | yes | 2.655x | 0.749x | 0.282x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 1,922.4 | 2,124.5-3,943.3 | 3.84 | yes | `b200_sxm-x953-nvl72-hybrid` | 1,906.5 | 2,037.5-3,781.8 | 3.97 | yes | 1.008x | 1.043x | 1.034x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x349-romfill` | 606.4 | 142.6-264.7 | 18.03 | **no** | `b200_sxm-x178-nvl72-hybrid` | 347.5 | 195.6-363.1 | 7.53 | yes | 1.745x | 0.729x | 0.418x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 650.5 | 1,187.7-2,204.6 | 2.32 | yes | `b200_sxm-x953-nvl72-hybrid` | 896.9 | 585.0-1,085.7 | 6.50 | yes | 0.725x | 2.030x | 2.800x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x349-romfill` | 152.5 | 37.5-69.6 | 17.26 | **no** | `b200_sxm-x178-expert` | 114.1 | 68.6-127.3 | 7.06 | yes | 1.337x | 0.547x | 0.409x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill` | 183.9 | 199.9-371.0 | 3.90 | yes | `b200_sxm-x953-expert` | 442.7 | 356.5-661.7 | 5.27 | yes | 0.415x | 0.561x | 1.350x |

**Does the ratio compress?** Of 20 class rows in this study, 15 move the ROM-versus-GPU ratio DOWN under speculation and 5 move it UP. The movement spans 0.083x to 2.800x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 11 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 20,313.6 | 3,876.0-7,194.3 | 22.22 | **no** | `b200_sxm-x26-nvl72-tensor` | 3,471.9 | 7,562.4-14,036.8 | 1.95 | yes | 5.851x | 0.513x | 0.088x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 6,648.0 | 1,042.6-1,935.1 | 27.04 | **no** | `b200_sxm-x116-nvl72-hybrid` | 3,947.5 | 10,903.5-20,238.3 | 1.54 | yes | 1.684x | 0.096x | 0.057x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 20,313.6 | 3,876.0-7,194.3 | 22.22 | **no** | `b200_sxm-x26-nvl72-tensor` | 3,218.9 | 6,038.4-11,208.1 | 2.26 | yes | 6.311x | 0.642x | 0.102x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 6,648.0 | 1,042.6-1,935.1 | 27.04 | **no** | `b200_sxm-x116-nvl72-hybrid` | 3,947.5 | 10,903.5-20,238.3 | 1.54 | yes | 1.684x | 0.096x | 0.057x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 20,313.6 | 3,876.0-7,194.3 | 22.22 | **no** | `b200_sxm-x26-nvl72-tensor` | 2,820.4 | 4,588.2-8,516.3 | 2.61 | yes | 7.202x | 0.845x | 0.117x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 6,648.0 | 1,042.6-1,935.1 | 27.04 | **no** | `b200_sxm-x116-nvl72-hybrid` | 3,774.4 | 9,037.0-16,773.8 | 1.77 | yes | 1.761x | 0.115x | 0.065x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 20,313.6 | 3,876.0-7,194.3 | 22.22 | **no** | `b200_sxm-x26-nvl72-tensor` | 2,288.0 | 3,450.9-6,405.3 | 2.81 | yes | 8.878x | 1.123x | 0.127x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 6,648.0 | 1,042.6-1,935.1 | 27.04 | **no** | `b200_sxm-x116-nvl72-hybrid` | 3,477.6 | 7,043.4-13,073.5 | 2.09 | yes | 1.912x | 0.148x | 0.077x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 19,024.5 | 3,784.1-7,023.9 | 21.32 | **no** | `b200_sxm-x44-nvl72-tensor` | 2,224.9 | 3,129.0-5,807.9 | 3.01 | yes | 8.551x | 1.209x | 0.141x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 6,648.0 | 1,042.6-1,935.1 | 27.04 | **no** | `b200_sxm-x116-nvl72-hybrid` | 3,026.6 | 5,003.6-9,287.3 | 2.56 | yes | 2.197x | 0.208x | 0.095x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18,398.7 | 3,812.3-7,076.1 | 20.46 | **no** | `b200_sxm-x173-nvl72-hybrid` | 2,764.3 | 4,158.7-7,719.1 | 2.82 | yes | 6.656x | 0.917x | 0.138x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 6,648.0 | 1,042.6-1,935.1 | 27.04 | **no** | `b200_sxm-x116-nvl72-hybrid` | 2,453.2 | 3,314.3-6,151.9 | 3.14 | yes | 2.710x | 0.315x | 0.116x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18,398.7 | 3,812.3-7,076.1 | 20.46 | **no** | `b200_sxm-x173-nvl72-hybrid` | 2,173.0 | 2,627.1-4,876.2 | 3.51 | yes | 8.467x | 1.451x | 0.171x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 6,648.0 | 1,042.6-1,935.1 | 27.04 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,870.2 | 2,027.1-3,762.6 | 3.91 | yes | 3.555x | 0.514x | 0.145x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7,883.1 | 1,806.5-3,353.1 | 18.50 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,210.5 | 858.0-1,592.6 | 5.98 | yes | 6.512x | 2.105x | 0.323x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 6,648.0 | 1,042.6-1,935.1 | 27.04 | **no** | `b200_sxm-x231-nvl72-hybrid` | 1,344.7 | 1,047.2-1,943.8 | 5.44 | yes | 4.944x | 0.996x | 0.201x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 2,266.9 | 461.2-856.0 | 20.84 | **no** | `b200_sxm-x173-nvl72-hybrid` | 625.0 | 224.5-416.8 | 11.80 | **no** | 3.627x | 2.054x | 0.566x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 4,602.0 | 814.8-1,512.3 | 23.95 | **no** | `b200_sxm-x347-nvl72-hybrid` | 828.2 | 337.7-626.9 | 10.40 | **no** | 5.557x | 2.412x | 0.434x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 580.2 | 136.8-253.9 | 17.98 | **no** | `b200_sxm-x173-expert` | 271.7 | 81.4-151.1 | 14.15 | **no** | 2.136x | 1.680x | 0.787x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,225.1 | 275.6-511.5 | 18.85 | **no** | `b200_sxm-x347-expert` | 448.2 | 162.4-301.5 | 11.70 | **no** | 2.734x | 1.697x | 0.621x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.057x to 0.787x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 0 of 20 ROM rows and 16 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 20,317.2 | 3,919.7-7,275.6 | 21.98 | **no** | `b200_sxm-x26-nvl72-tensor` | 3,474.6 | 7,565.4-14,042.3 | 1.95 | yes | 5.847x | 0.518x | 0.089x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 7,768.0 | 1,202.4-2,231.8 | 27.39 | **no** | `b200_sxm-x29-nvl72-tensor` | 3,559.9 | 8,020.8-14,887.6 | 1.88 | yes | 2.182x | 0.150x | 0.069x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 20,317.2 | 3,919.7-7,275.6 | 21.98 | **no** | `b200_sxm-x26-nvl72-tensor` | 3,223.4 | 6,042.2-11,215.1 | 2.26 | yes | 6.303x | 0.649x | 0.103x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 7,768.0 | 1,202.4-2,231.8 | 27.39 | **no** | `b200_sxm-x29-nvl72-tensor` | 3,319.5 | 6,457.4-11,985.9 | 2.18 | yes | 2.340x | 0.186x | 0.080x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 20,317.2 | 3,919.7-7,275.6 | 21.98 | **no** | `b200_sxm-x26-nvl72-tensor` | 2,827.4 | 4,592.6-8,524.4 | 2.61 | yes | 7.186x | 0.853x | 0.119x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 7,768.0 | 1,202.4-2,231.8 | 27.39 | **no** | `b200_sxm-x29-nvl72-tensor` | 2,935.2 | 4,919.2-9,130.8 | 2.53 | yes | 2.647x | 0.244x | 0.092x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 20,317.2 | 3,919.7-7,275.6 | 21.98 | **no** | `b200_sxm-x26-nvl72-tensor` | 2,297.2 | 3,455.8-6,414.5 | 2.82 | yes | 8.844x | 1.134x | 0.128x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 7,768.0 | 1,202.4-2,231.8 | 27.39 | **no** | `b200_sxm-x29-nvl72-tensor` | 2,410.5 | 3,681.2-6,832.7 | 2.78 | yes | 3.223x | 0.327x | 0.101x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 20,042.4 | 3,943.9-7,320.4 | 21.55 | **no** | `b200_sxm-x44-nvl72-tensor` | 2,235.2 | 3,133.8-5,816.8 | 3.02 | yes | 8.967x | 1.258x | 0.140x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 7,768.0 | 1,202.4-2,231.8 | 27.39 | **no** | `b200_sxm-x29-nvl72-tensor` | 1,830.9 | 2,668.0-4,952.2 | 2.91 | yes | 4.243x | 0.451x | 0.106x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 19,337.7 | 3,972.5-7,373.5 | 20.64 | **no** | `b200_sxm-x173-nvl72-hybrid` | 2,772.4 | 4,163.0-7,727.1 | 2.82 | yes | 6.975x | 0.954x | 0.137x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 7,768.0 | 1,202.4-2,231.8 | 27.39 | **no** | `b200_sxm-x29-nvl72-tensor` | 1,326.0 | 1,797.6-3,336.6 | 3.13 | yes | 5.858x | 0.669x | 0.114x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 19,337.7 | 3,972.5-7,373.5 | 20.64 | **no** | `b200_sxm-x173-nvl72-hybrid` | 2,183.1 | 2,630.5-4,882.6 | 3.52 | yes | 8.858x | 1.510x | 0.170x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 7,115.6 | 1,087.5-2,018.5 | 27.74 | **no** | `b200_sxm-x116-nvl72-hybrid` | 1,881.2 | 2,030.2-3,768.3 | 3.93 | yes | 3.782x | 0.536x | 0.142x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8,410.1 | 1,916.9-3,558.0 | 18.60 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,223.0 | 859.5-1,595.3 | 6.03 | yes | 6.876x | 2.230x | 0.324x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 7,115.6 | 1,087.5-2,018.5 | 27.74 | **no** | `b200_sxm-x231-nvl72-hybrid` | 1,356.2 | 1,048.9-1,946.8 | 5.48 | yes | 5.247x | 1.037x | 0.198x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 2,443.0 | 490.0-909.5 | 21.14 | **no** | `b200_sxm-x173-nvl72-hybrid` | 638.5 | 225.4-418.4 | 12.01 | **no** | 3.826x | 2.174x | 0.568x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 4,939.9 | 856.4-1,589.5 | 24.46 | **no** | `b200_sxm-x347-nvl72-hybrid` | 839.9 | 338.7-628.8 | 10.51 | **no** | 5.881x | 2.528x | 0.430x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 626.5 | 147.1-273.0 | 18.06 | **no** | `b200_sxm-x173-expert` | 282.0 | 81.9-152.0 | 14.60 | **no** | 2.221x | 1.796x | 0.808x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,637.4 | 676.2-1,255.2 | 10.27 | **no** | `b200_sxm-x347-expert` | 462.1 | 163.4-303.2 | 11.99 | **no** | 3.543x | 4.140x | 1.168x |

**Does the ratio compress?** Of 20 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 1 move it UP. The movement spans 0.069x to 1.168x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 0 of 20 ROM rows and 16 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 6,308.0 | 813.5-1,510.0 | 32.88 | **no** | `b200_sxm-x157-nvl72-hybrid` | 2,277.1 | 5,210.4-9,671.2 | 1.85 | yes | 2.770x | 0.156x | 0.056x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 3,784.7 | 6,817.6-12,654.4 | 2.35 | yes | `b200_sxm-x116-nvl72-hybrid` | 2,351.4 | 5,355.5-9,940.4 | 1.86 | yes | 1.610x | 1.273x | 0.791x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 6,308.0 | 813.5-1,510.0 | 32.88 | **no** | `b200_sxm-x157-nvl72-hybrid` | 2,277.1 | 5,210.4-9,671.2 | 1.85 | yes | 2.770x | 0.156x | 0.056x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 3,745.8 | 6,888.9-12,786.7 | 2.31 | yes | `b200_sxm-x289-nvl72-hybrid` | 2,311.6 | 5,612.8-10,418.2 | 1.75 | yes | 1.620x | 1.227x | 0.757x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 6,308.0 | 813.5-1,510.0 | 32.88 | **no** | `b200_sxm-x157-nvl72-hybrid` | 2,201.6 | 4,646.0-8,623.6 | 2.01 | yes | 2.865x | 0.175x | 0.061x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 3,745.8 | 6,888.9-12,786.7 | 2.31 | yes | `b200_sxm-x289-nvl72-hybrid` | 2,311.6 | 5,612.8-10,418.2 | 1.75 | yes | 1.620x | 1.227x | 0.757x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 6,308.0 | 813.5-1,510.0 | 32.88 | **no** | `b200_sxm-x157-nvl72-hybrid` | 1,946.2 | 3,013.6-5,593.6 | 2.74 | yes | 3.241x | 0.270x | 0.083x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 3,745.8 | 6,888.9-12,786.7 | 2.31 | yes | `b200_sxm-x289-nvl72-hybrid` | 2,184.3 | 4,607.9-8,552.9 | 2.01 | yes | 1.715x | 1.495x | 0.872x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 6,308.0 | 813.5-1,510.0 | 32.88 | **no** | `b200_sxm-x157-nvl72-hybrid` | 1,587.3 | 2,061.0-3,825.5 | 3.27 | yes | 3.974x | 0.395x | 0.099x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,680.5 | 6,295.8-11,685.8 | 2.48 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,026.6 | 3,568.6-6,623.8 | 2.41 | yes | 1.816x | 1.764x | 0.971x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 6,308.0 | 813.5-1,510.0 | 32.88 | **no** | `b200_sxm-x157-nvl72-hybrid` | 1,175.5 | 1,524.9-2,830.5 | 3.27 | yes | 5.366x | 0.533x | 0.099x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 3,450.0 | 4,317.6-8,014.0 | 3.39 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,654.8 | 2,426.9-4,504.7 | 2.89 | yes | 2.085x | 1.779x | 0.853x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 6,308.0 | 813.5-1,510.0 | 32.88 | **no** | `b200_sxm-x157-nvl72-hybrid` | 800.1 | 963.5-1,788.3 | 3.52 | yes | 7.884x | 0.844x | 0.107x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 3,066.1 | 3,449.5-6,402.7 | 3.77 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,229.1 | 1,493.0-2,771.2 | 3.49 | yes | 2.495x | 2.310x | 0.926x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 2,584.2 | 449.5-834.4 | 24.37 | **no** | `b200_sxm-x173-nvl72-hybrid` | 376.0 | 341.7-634.3 | 4.66 | yes | 6.874x | 1.315x | 0.191x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,838.5 | 1,563.4-2,901.9 | 4.99 | yes | `b200_sxm-x347-nvl72-hybrid` | 556.5 | 508.3-943.5 | 4.64 | yes | 3.304x | 3.076x | 0.931x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 691.3 | 113.6-210.8 | 25.81 | **no** | `b200_sxm-x173-nvl72-hybrid` | 193.6 | 91.8-170.5 | 8.94 | **no** | 3.572x | 1.237x | 0.346x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 844.4 | 174.4-323.8 | 20.53 | **no** | `b200_sxm-x347-expert` | 267.1 | 245.2-455.2 | 4.62 | yes | 3.161x | 0.711x | 0.225x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 174.6 | 38.5-71.5 | 19.22 | **no** | `b200_sxm-x173-expert` | 90.1 | 31.4-58.4 | 12.14 | **no** | 1.939x | 1.225x | 0.632x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 214.5 | 73.6-136.6 | 12.36 | **no** | `b200_sxm-x347-expert` | 151.2 | 63.0-116.9 | 10.18 | **no** | 1.418x | 1.169x | 0.824x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.056x to 0.971x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 20 ROM rows and 17 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 6,790.3 | 902.0-1,674.2 | 31.92 | **no** | `b200_sxm-x138-nvl72-hybrid` | 2,454.4 | 5,838.5-10,837.1 | 1.78 | yes | 2.767x | 0.154x | 0.056x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3,832.3 | 7,317.1-13,581.5 | 2.22 | yes | `b200_sxm-x144-nvl72-hybrid` | 2,476.9 | 5,951.7-11,047.1 | 1.76 | yes | 1.547x | 1.229x | 0.795x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 6,790.3 | 902.0-1,674.2 | 31.92 | **no** | `b200_sxm-x138-nvl72-hybrid` | 2,454.4 | 5,838.5-10,837.1 | 1.78 | yes | 2.767x | 0.154x | 0.056x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3,832.3 | 7,317.1-13,581.5 | 2.22 | yes | `b200_sxm-x144-nvl72-hybrid` | 2,476.9 | 5,951.7-11,047.1 | 1.76 | yes | 1.547x | 1.229x | 0.795x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 6,790.3 | 902.0-1,674.2 | 31.92 | **no** | `b200_sxm-x138-nvl72-hybrid` | 2,262.5 | 4,436.3-8,234.3 | 2.16 | yes | 3.001x | 0.203x | 0.068x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3,832.3 | 7,317.1-13,581.5 | 2.22 | yes | `b200_sxm-x144-nvl72-hybrid` | 2,287.8 | 4,526.5-8,401.9 | 2.14 | yes | 1.675x | 1.616x | 0.965x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 6,790.3 | 902.0-1,674.2 | 31.92 | **no** | `b200_sxm-x138-nvl72-hybrid` | 1,961.5 | 3,139.1-5,826.6 | 2.65 | yes | 3.462x | 0.287x | 0.083x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,827.8 | 7,311.3-13,570.8 | 2.22 | yes | `b200_sxm-x231-nvl72-hybrid` | 2,127.2 | 4,046.4-7,510.6 | 2.23 | yes | 1.799x | 1.807x | 1.004x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 6,790.3 | 902.0-1,674.2 | 31.92 | **no** | `b200_sxm-x138-nvl72-hybrid` | 1,561.7 | 2,082.0-3,864.5 | 3.18 | yes | 4.348x | 0.433x | 0.100x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,782.7 | 6,768.2-12,562.7 | 2.37 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,037.2 | 3,581.9-6,648.5 | 2.41 | yes | 1.857x | 1.890x | 1.018x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 6,790.3 | 902.0-1,674.2 | 31.92 | **no** | `b200_sxm-x138-nvl72-hybrid` | 1,133.2 | 1,326.2-2,461.7 | 3.62 | yes | 5.992x | 0.680x | 0.113x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,634.2 | 5,233.5-9,714.2 | 2.94 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,669.1 | 2,434.1-4,518.0 | 2.91 | yes | 2.177x | 2.150x | 0.987x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 6,790.3 | 902.0-1,674.2 | 31.92 | **no** | `b200_sxm-x138-nvl72-hybrid` | 768.5 | 806.9-1,497.7 | 4.04 | yes | 8.836x | 1.118x | 0.127x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 3,379.6 | 3,361.8-6,239.9 | 4.26 | yes | `b200_sxm-x231-nvl72-hybrid` | 1,012.2 | 1,217.3-2,259.5 | 3.53 | yes | 3.339x | 2.762x | 0.827x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 3,183.6 | 517.5-960.5 | 26.08 | **no** | `b200_sxm-x173-nvl72-hybrid` | 388.0 | 344.0-638.6 | 4.78 | yes | 8.204x | 1.504x | 0.183x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 2,572.8 | 1,835.4-3,406.7 | 5.94 | yes | `b200_sxm-x347-nvl72-hybrid` | 569.6 | 510.9-948.2 | 4.73 | yes | 4.517x | 3.593x | 0.795x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 865.8 | 131.0-243.1 | 28.03 | **no** | `b200_sxm-x173-nvl72-hybrid` | 206.8 | 93.9-174.3 | 9.34 | **no** | 4.186x | 1.395x | 0.333x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,602.5 | 602.6-1,118.5 | 11.28 | **no** | `b200_sxm-x347-expert` | 279.4 | 252.6-468.8 | 4.69 | yes | 5.735x | 2.386x | 0.416x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 219.2 | 47.0-87.2 | 19.79 | **no** | `b200_sxm-x173-expert` | 102.3 | 32.4-60.2 | 13.38 | **no** | 2.144x | 1.449x | 0.676x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 576.2 | 163.5-303.4 | 14.95 | **no** | `b200_sxm-x347-expert` | 168.0 | 64.9-120.5 | 10.98 | **no** | 3.430x | 2.519x | 0.734x |

**Does the ratio compress?** Of 20 class rows in this study, 18 move the ROM-versus-GPU ratio DOWN under speculation and 2 move it UP. The movement spans 0.056x to 1.018x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 20 ROM rows and 17 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 6,893.2 | 916.8-1,701.6 | 31.88 | **no** | `b200_sxm-x136-nvl72-hybrid` | 2,447.2 | 5,800.3-10,766.2 | 1.79 | yes | 2.817x | 0.158x | 0.056x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3,836.7 | 7,383.1-13,704.0 | 2.20 | yes | `b200_sxm-x144-nvl72-hybrid` | 2,477.6 | 5,952.6-11,048.8 | 1.76 | yes | 1.549x | 1.240x | 0.801x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 6,893.2 | 916.8-1,701.6 | 31.88 | **no** | `b200_sxm-x136-nvl72-hybrid` | 2,447.2 | 5,800.3-10,766.2 | 1.79 | yes | 2.817x | 0.158x | 0.056x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3,836.7 | 7,383.1-13,704.0 | 2.20 | yes | `b200_sxm-x144-nvl72-hybrid` | 2,477.6 | 5,952.6-11,048.8 | 1.76 | yes | 1.549x | 1.240x | 0.801x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 6,893.2 | 916.8-1,701.6 | 31.88 | **no** | `b200_sxm-x136-nvl72-hybrid` | 2,254.9 | 4,406.2-8,178.5 | 2.17 | yes | 3.057x | 0.208x | 0.068x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 3,836.7 | 7,383.1-13,704.0 | 2.20 | yes | `b200_sxm-x144-nvl72-hybrid` | 2,289.0 | 4,527.6-8,403.9 | 2.14 | yes | 1.676x | 1.631x | 0.973x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 6,893.2 | 916.8-1,701.6 | 31.88 | **no** | `b200_sxm-x136-nvl72-hybrid` | 1,953.6 | 3,095.5-5,745.6 | 2.68 | yes | 3.528x | 0.296x | 0.084x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,832.2 | 7,377.2-13,693.1 | 2.20 | yes | `b200_sxm-x231-nvl72-hybrid` | 2,128.5 | 4,048.3-7,514.1 | 2.23 | yes | 1.800x | 1.822x | 1.012x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 6,893.2 | 916.8-1,701.6 | 31.88 | **no** | `b200_sxm-x136-nvl72-hybrid` | 1,554.1 | 2,068.6-3,839.5 | 3.19 | yes | 4.436x | 0.443x | 0.100x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,788.5 | 6,843.7-12,702.8 | 2.35 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,038.8 | 3,583.9-6,652.2 | 2.41 | yes | 1.858x | 1.910x | 1.028x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 6,893.2 | 916.8-1,701.6 | 31.88 | **no** | `b200_sxm-x136-nvl72-hybrid` | 1,126.8 | 1,319.4-2,448.9 | 3.62 | yes | 6.118x | 0.695x | 0.114x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,645.0 | 5,324.4-9,882.7 | 2.90 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,671.2 | 2,435.2-4,520.0 | 2.91 | yes | 2.181x | 2.186x | 1.002x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 6,893.2 | 916.8-1,701.6 | 31.88 | **no** | `b200_sxm-x136-nvl72-hybrid` | 763.9 | 804.1-1,492.5 | 4.03 | yes | 9.024x | 1.140x | 0.126x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,388.2 | 3,687.2-6,843.9 | 3.90 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,247.2 | 1,499.2-2,782.8 | 3.53 | yes | 2.717x | 2.459x | 0.905x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 3,295.9 | 529.2-982.3 | 26.41 | **no** | `b200_sxm-x173-nvl72-hybrid` | 389.9 | 344.4-639.2 | 4.80 | yes | 8.454x | 1.537x | 0.182x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 2,572.8 | 1,883.5-3,496.1 | 5.79 | yes | `b200_sxm-x347-nvl72-hybrid` | 571.6 | 511.2-948.9 | 4.74 | yes | 4.501x | 3.684x | 0.818x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 899.1 | 134.0-248.7 | 28.45 | **no** | `b200_sxm-x173-nvl72-hybrid` | 208.9 | 94.2-174.8 | 9.40 | **no** | 4.303x | 1.422x | 0.331x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,639.0 | 623.6-1,157.4 | 11.14 | **no** | `b200_sxm-x347-expert` | 281.3 | 253.7-470.9 | 4.70 | yes | 5.826x | 2.458x | 0.422x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 227.8 | 48.5-90.1 | 19.90 | **no** | `b200_sxm-x173-expert` | 104.3 | 32.6-60.4 | 13.59 | **no** | 2.183x | 1.490x | 0.683x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 595.3 | 169.6-314.9 | 14.88 | **no** | `b200_sxm-x347-expert` | 170.8 | 65.2-121.0 | 11.11 | **no** | 3.486x | 2.602x | 0.747x |

**Does the ratio compress?** Of 20 class rows in this study, 17 move the ROM-versus-GPU ratio DOWN under speculation and 3 move it UP. The movement spans 0.056x to 1.028x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 20 ROM rows and 17 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x63-romfill` | 11,704.1 | 11,516.5-21,376.2 | 4.31 | yes | `a100_sxm_80gb-x62-tensor` | 1,003.9 | 1,508.0-2,799.0 | 2.82 | yes | 11.658x | 7.637x | 0.655x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 5,380.2 | 9,597.5-17,814.2 | 2.38 | yes | `a100_sxm_80gb-x168-tensor` | 1,082.1 | 1,597.4-2,965.1 | 2.87 | yes | 4.972x | 6.008x | 1.208x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 5,202.7 | 12,554.4-23,302.6 | 1.76 | yes | `a100_sxm_80gb-x387-tensor` | 742.8 | 896.3-1,663.6 | 3.51 | yes | 7.004x | 14.007x | 2.000x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 3,457.0 | 9,120.1-16,928.1 | 1.61 | yes | `a100_sxm_80gb-x2574-tensor` | 754.3 | 898.7-1,668.1 | 3.56 | yes | 4.583x | 10.148x | 2.214x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 4,999.4 | 9,833.6-18,252.4 | 2.16 | yes | `a100_sxm_80gb-x387-hybrid` | 656.1 | 1,315.3-2,441.3 | 2.12 | yes | 7.620x | 7.477x | 0.981x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 3,457.0 | 9,120.1-16,928.1 | 1.61 | yes | `a100_sxm_80gb-x2574-tensor` | 662.7 | 519.5-964.2 | 5.41 | yes | 5.216x | 17.557x | 3.366x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 4,637.1 | 6,860.1-12,733.3 | 2.87 | yes | `a100_sxm_80gb-x387-hybrid` | 656.1 | 1,315.3-2,441.3 | 2.12 | yes | 7.068x | 5.216x | 0.738x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 3,457.0 | 9,120.1-16,928.1 | 1.61 | yes | `a100_sxm_80gb-x2574-hybrid` | 661.2 | 1,354.6-2,514.3 | 2.07 | yes | 5.229x | 6.733x | 1.288x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 4,050.1 | 4,274.9-7,934.7 | 4.02 | yes | `a100_sxm_80gb-x387-hybrid` | 656.1 | 1,315.3-2,441.3 | 2.12 | yes | 6.173x | 3.250x | 0.527x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 3,457.0 | 9,120.1-16,928.1 | 1.61 | yes | `a100_sxm_80gb-x2574-hybrid` | 661.2 | 1,354.6-2,514.3 | 2.07 | yes | 5.229x | 6.733x | 1.288x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 4,014.6 | 1,065.7-1,978.0 | 15.97 | **no** | `a100_sxm_80gb-x387-hybrid` | 656.1 | 1,315.3-2,441.3 | 2.12 | yes | 6.119x | 0.810x | 0.132x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 3,457.0 | 9,120.1-16,928.1 | 1.61 | yes | `a100_sxm_80gb-x2574-hybrid` | 661.2 | 1,354.6-2,514.3 | 2.07 | yes | 5.229x | 6.733x | 1.288x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 4,014.6 | 1,065.7-1,978.0 | 15.97 | **no** | `a100_sxm_80gb-x387-hybrid` | 607.7 | 1,115.2-2,070.0 | 2.31 | yes | 6.607x | 0.956x | 0.145x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 3,019.5 | 1,997.5-3,707.6 | 6.41 | yes | `a100_sxm_80gb-x2574-hybrid` | 661.2 | 1,354.6-2,514.3 | 2.07 | yes | 4.567x | 1.475x | 0.323x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,609.9 | 516.6-958.9 | 13.21 | **no** | `a100_sxm_80gb-x387-hybrid` | 317.3 | 336.1-623.8 | 4.00 | yes | 5.073x | 1.537x | 0.303x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,284.9 | 1,647.0-3,057.1 | 3.31 | yes | `a100_sxm_80gb-x2574-hybrid` | 661.2 | 1,354.6-2,514.3 | 2.07 | yes | 1.943x | 1.216x | 0.626x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 413.4 | 129.9-241.0 | 13.50 | **no** | `a100_sxm_80gb-x387-expert` | 177.6 | 81.9-152.0 | 9.20 | **no** | 2.328x | 1.586x | 0.681x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 389.6 | 967.8-1,796.4 | 1.71 | yes | `a100_sxm_80gb-x2574-hybrid` | 424.5 | 537.5-997.6 | 3.35 | yes | 0.918x | 1.801x | 1.962x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 103.8 | 49.7-92.2 | 8.86 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 104.7 | 38.6-71.6 | 11.51 | **no** | `a100_sxm_80gb-x2574-expert` | 261.2 | 135.0-250.5 | 8.21 | **no** | 0.401x | 0.286x | 0.713x |

**Does the ratio compress?** Of 19 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 8 move it UP. The movement spans 0.132x to 3.366x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 14 of 20 ROM rows and 17 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 15,837.4 | 2,798.1-5,193.6 | 24.00 | **no** | `a100_sxm_80gb-x71-tensor` | 1,031.9 | 1,535.2-2,849.5 | 2.85 | yes | 15.348x | 1.823x | 0.119x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 5,514.7 | 14,576.0-27,055.1 | 1.60 | yes | `a100_sxm_80gb-x56-tensor` | 1,007.9 | 1,504.3-2,792.1 | 2.84 | yes | 5.472x | 9.690x | 1.771x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 15,837.4 | 2,798.1-5,193.6 | 24.00 | **no** | `a100_sxm_80gb-x71-tensor` | 926.2 | 960.5-1,782.8 | 4.09 | yes | 17.100x | 2.913x | 0.170x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 5,473.8 | 14,244.1-26,438.9 | 1.63 | yes | `a100_sxm_80gb-x112-tensor` | 961.1 | 972.6-1,805.2 | 4.19 | yes | 5.695x | 14.646x | 2.572x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 15,837.4 | 2,798.1-5,193.6 | 24.00 | **no** | `a100_sxm_80gb-x71-tensor` | 769.9 | 554.2-1,028.6 | 5.89 | yes | 20.571x | 5.049x | 0.245x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 5,467.7 | 14,231.0-26,414.5 | 1.63 | yes | `a100_sxm_80gb-x224-tensor` | 833.3 | 551.2-1,023.1 | 6.41 | yes | 6.561x | 25.818x | 3.935x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 15,837.4 | 2,798.1-5,193.6 | 24.00 | **no** | `a100_sxm_80gb-x71-hybrid` | 749.9 | 1,147.1-2,129.2 | 2.77 | yes | 21.118x | 2.439x | 0.116x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,455.6 | 14,204.7-26,365.9 | 1.63 | yes | `a100_sxm_80gb-x448-hybrid` | 713.5 | 1,401.5-2,601.3 | 2.16 | yes | 7.646x | 10.135x | 1.326x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 15,837.4 | 2,798.1-5,193.6 | 24.00 | **no** | `a100_sxm_80gb-x71-hybrid` | 646.9 | 914.3-1,697.1 | 3.00 | yes | 24.482x | 3.060x | 0.125x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,397.9 | 13,353.4-24,785.6 | 1.71 | yes | `a100_sxm_80gb-x672-hybrid` | 713.5 | 1,403.3-2,604.7 | 2.16 | yes | 7.566x | 9.516x | 1.258x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 14,829.5 | 2,773.3-5,147.6 | 22.67 | **no** | `a100_sxm_80gb-x146-hybrid` | 635.3 | 957.2-1,776.8 | 2.81 | yes | 23.344x | 2.897x | 0.124x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,222.7 | 10,831.7-20,105.0 | 2.04 | yes | `a100_sxm_80gb-x672-hybrid` | 713.5 | 1,403.3-2,604.7 | 2.16 | yes | 7.320x | 7.719x | 1.054x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 14,692.8 | 2,771.1-5,143.6 | 22.48 | **no** | `a100_sxm_80gb-x335-hybrid` | 645.4 | 1,058.2-1,964.2 | 2.59 | yes | 22.764x | 2.619x | 0.115x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,904.4 | 7,862.2-14,593.3 | 2.64 | yes | `a100_sxm_80gb-x672-hybrid` | 713.5 | 1,403.3-2,604.7 | 2.16 | yes | 6.874x | 5.603x | 0.815x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,947.4 | 1,311.2-2,433.7 | 19.23 | **no** | `a100_sxm_80gb-x335-hybrid` | 361.1 | 557.9-1,035.6 | 2.74 | yes | 16.468x | 2.350x | 0.143x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,591.1 | 2,972.6-5,517.6 | 5.12 | yes | `a100_sxm_80gb-x672-hybrid` | 508.1 | 718.0-1,332.7 | 3.00 | yes | 7.068x | 4.140x | 0.586x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,649.4 | 332.8-617.7 | 21.01 | **no** | `a100_sxm_80gb-x335-expert` | 287.5 | 171.6-318.5 | 7.10 | yes | 5.737x | 1.939x | 0.338x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,415.2 | 588.2-1,091.8 | 17.41 | **no** | `a100_sxm_80gb-x672-expert` | 360.7 | 335.7-623.0 | 4.56 | yes | 6.695x | 1.752x | 0.262x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 493.9 | 116.5-216.2 | 17.98 | **no** | `a100_sxm_80gb-x224-expert` | 117.1 | 29.4-54.7 | 16.87 | **no** | 4.217x | 3.956x | 0.938x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 623.7 | 198.8-369.0 | 13.30 | **no** | `a100_sxm_80gb-x672-expert` | 253.0 | 87.5-162.4 | 12.26 | **no** | 2.466x | 2.272x | 0.921x |

**Does the ratio compress?** Of 20 class rows in this study, 14 move the ROM-versus-GPU ratio DOWN under speculation and 6 move it UP. The movement spans 0.115x to 3.935x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 8 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 16,019.5 | 2,891.7-5,367.4 | 23.49 | **no** | `a100_sxm_80gb-x67-tensor` | 1,026.2 | 1,522.3-2,825.6 | 2.86 | yes | 15.611x | 1.900x | 0.122x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.4 | 14,443.3-26,808.8 | 1.62 | yes | `a100_sxm_80gb-x112-tensor` | 1,067.2 | 1,579.1-2,931.0 | 2.87 | yes | 5.176x | 9.147x | 1.767x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 16,019.5 | 2,891.7-5,367.4 | 23.49 | **no** | `a100_sxm_80gb-x67-tensor` | 920.4 | 953.9-1,770.6 | 4.09 | yes | 17.405x | 3.031x | 0.174x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 5,523.4 | 14,443.3-26,808.8 | 1.62 | yes | `a100_sxm_80gb-x112-tensor` | 961.5 | 972.7-1,805.4 | 4.19 | yes | 5.745x | 14.849x | 2.585x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 16,019.5 | 2,891.7-5,367.4 | 23.49 | **no** | `a100_sxm_80gb-x67-tensor` | 764.3 | 551.1-1,023.0 | 5.88 | yes | 20.960x | 5.247x | 0.250x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 5,517.2 | 14,429.8-26,783.7 | 1.62 | yes | `a100_sxm_80gb-x224-tensor` | 833.6 | 551.2-1,023.2 | 6.41 | yes | 6.619x | 26.177x | 3.955x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 16,019.5 | 2,891.7-5,367.4 | 23.49 | **no** | `a100_sxm_80gb-x67-hybrid` | 723.5 | 1,085.4-2,014.6 | 2.83 | yes | 22.141x | 2.664x | 0.120x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 5,504.9 | 14,402.9-26,733.6 | 1.62 | yes | `a100_sxm_80gb-x448-hybrid` | 714.9 | 1,402.8-2,603.8 | 2.16 | yes | 7.700x | 10.267x | 1.333x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 16,019.5 | 2,891.7-5,367.4 | 23.49 | **no** | `a100_sxm_80gb-x67-hybrid` | 623.3 | 865.6-1,606.7 | 3.05 | yes | 25.703x | 3.341x | 0.130x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,462.5 | 13,587.7-25,220.5 | 1.70 | yes | `a100_sxm_80gb-x672-hybrid` | 714.9 | 1,404.5-2,607.0 | 2.16 | yes | 7.641x | 9.674x | 1.266x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 15,680.6 | 2,890.9-5,366.0 | 23.00 | **no** | `a100_sxm_80gb-x146-hybrid` | 637.2 | 958.3-1,778.7 | 2.82 | yes | 24.607x | 3.017x | 0.123x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5,345.0 | 11,143.4-20,683.6 | 2.03 | yes | `a100_sxm_80gb-x672-hybrid` | 714.9 | 1,404.5-2,607.0 | 2.16 | yes | 7.476x | 7.934x | 1.061x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 15,527.8 | 2,888.6-5,361.6 | 22.79 | **no** | `a100_sxm_80gb-x335-hybrid` | 647.2 | 1,059.3-1,966.2 | 2.59 | yes | 23.992x | 2.727x | 0.114x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 5,317.6 | 785.3-1,457.7 | 28.71 | **no** | `a100_sxm_80gb-x672-hybrid` | 714.9 | 1,404.5-2,607.0 | 2.16 | yes | 7.438x | 0.559x | 0.075x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,364.6 | 1,391.8-2,583.4 | 19.39 | **no** | `a100_sxm_80gb-x335-hybrid` | 363.4 | 559.2-1,037.9 | 2.76 | yes | 17.515x | 2.489x | 0.142x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 5,317.6 | 785.3-1,457.7 | 28.71 | **no** | `a100_sxm_80gb-x672-hybrid` | 510.3 | 719.0-1,334.5 | 3.01 | yes | 10.421x | 1.092x | 0.105x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,778.8 | 353.6-656.3 | 21.33 | **no** | `a100_sxm_80gb-x335-expert` | 293.3 | 178.0-330.4 | 6.98 | yes | 6.065x | 1.986x | 0.327x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 3,651.1 | 618.3-1,147.6 | 25.04 | **no** | `a100_sxm_80gb-x672-expert` | 365.2 | 347.9-645.7 | 4.45 | yes | 9.997x | 1.777x | 0.178x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 532.3 | 125.0-232.0 | 18.06 | **no** | `a100_sxm_80gb-x224-expert` | 121.5 | 30.6-56.8 | 16.85 | **no** | 4.380x | 4.088x | 0.933x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,134.4 | 457.6-849.4 | 10.51 | **no** | `a100_sxm_80gb-x672-expert` | 262.0 | 90.8-168.6 | 12.23 | **no** | 4.330x | 5.038x | 1.164x |

**Does the ratio compress?** Of 20 class rows in this study, 13 move the ROM-versus-GPU ratio DOWN under speculation and 7 move it UP. The movement spans 0.075x to 3.955x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 6 of 20 ROM rows and 18 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x196` | 4,637.4 | 5,126.7-9,515.8 | 3.84 | yes | `a100_sxm_80gb-x193-tensor` | 682.3 | 761.6-1,413.6 | 3.80 | yes | 6.797x | 6.731x | 0.990x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 3,734.7 | 5,706.8-10,592.6 | 2.77 | yes | `a100_sxm_80gb-x336-tensor` | 523.4 | 708.3-1,314.8 | 3.13 | yes | 7.136x | 8.057x | 1.129x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4,443.3 | 587.8-1,091.1 | 32.05 | **no** | `a100_sxm_80gb-x391-tensor` | 466.7 | 419.4-778.5 | 4.72 | yes | 9.520x | 1.402x | 0.147x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3,483.1 | 4,430.4-8,223.4 | 3.33 | yes | `a100_sxm_80gb-x783-tensor` | 474.9 | 421.6-782.5 | 4.78 | yes | 7.334x | 10.510x | 1.433x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4,443.3 | 587.8-1,091.1 | 32.05 | **no** | `a100_sxm_80gb-x391-tensor` | 381.1 | 231.3-429.3 | 6.99 | yes | 11.659x | 2.541x | 0.218x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3,483.1 | 4,430.4-8,223.4 | 3.33 | yes | `a100_sxm_80gb-x783-tensor` | 388.9 | 231.5-429.7 | 7.12 | yes | 8.957x | 19.136x | 2.137x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4,443.3 | 587.8-1,091.1 | 32.05 | **no** | `a100_sxm_80gb-x391-tensor` | 279.1 | 122.2-226.7 | 9.69 | **no** | 15.923x | 4.812x | 0.302x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3,483.1 | 4,430.4-8,223.4 | 3.33 | yes | `a100_sxm_80gb-x783-tensor` | 285.6 | 121.9-226.3 | 9.93 | **no** | 12.196x | 36.338x | 2.979x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4,443.3 | 587.8-1,091.1 | 32.05 | **no** | `a100_sxm_80gb-x391-hybrid` | 262.2 | 364.7-677.0 | 3.05 | yes | 16.945x | 1.612x | 0.095x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3,426.3 | 4,336.4-8,048.9 | 3.35 | yes | `a100_sxm_80gb-x783-hybrid` | 260.4 | 365.2-677.9 | 3.02 | yes | 13.160x | 11.874x | 0.902x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4,443.3 | 587.8-1,091.1 | 32.05 | **no** | `a100_sxm_80gb-x391-hybrid` | 262.2 | 364.7-677.0 | 3.05 | yes | 16.945x | 1.612x | 0.095x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3,030.6 | 3,707.4-6,881.3 | 3.47 | yes | `a100_sxm_80gb-x783-hybrid` | 260.4 | 365.2-677.9 | 3.02 | yes | 11.640x | 10.151x | 0.872x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 4,443.3 | 587.8-1,091.1 | 32.05 | **no** | `a100_sxm_80gb-x391-hybrid` | 242.0 | 298.5-554.1 | 3.44 | yes | 18.364x | 1.969x | 0.107x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 2,462.0 | 2,873.6-5,333.8 | 3.63 | yes | `a100_sxm_80gb-x783-hybrid` | 260.4 | 365.2-677.9 | 3.02 | yes | 9.456x | 7.869x | 0.832x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,849.6 | 337.0-625.5 | 23.27 | **no** | `a100_sxm_80gb-x391-hybrid` | 123.5 | 124.8-231.6 | 4.20 | yes | 14.978x | 2.700x | 0.180x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,158.1 | 1,223.2-2,270.4 | 4.01 | yes | `a100_sxm_80gb-x783-hybrid` | 181.3 | 183.5-340.6 | 4.19 | yes | 6.389x | 6.667x | 1.044x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 484.6 | 84.9-157.5 | 24.21 | **no** | `a100_sxm_80gb-x391-expert` | 87.3 | 60.6-112.6 | 6.10 | yes | 5.551x | 1.399x | 0.252x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 406.2 | 103.1-191.4 | 16.70 | **no** | `a100_sxm_80gb-x783-expert` | 111.7 | 119.9-222.6 | 3.95 | yes | 3.637x | 0.860x | 0.236x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 122.0 | 27.5-51.0 | 18.82 | **no** | `a100_sxm_80gb-x391-expert` | 55.6 | 15.3-28.4 | 15.39 | **no** | 2.194x | 1.795x | 0.818x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 102.3 | 58.2-108.0 | 7.45 | yes | `a100_sxm_80gb-x783-expert` | 81.9 | 30.6-56.8 | 11.35 | **no** | 1.249x | 1.903x | 1.523x |

**Does the ratio compress?** Of 20 class rows in this study, 14 move the ROM-versus-GPU ratio DOWN under speculation and 6 move it UP. The movement spans 0.095x to 2.979x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 10 of 20 ROM rows and 16 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 5,167.5 | 653.8-1,213.6 | 33.51 | **no** | `a100_sxm_80gb-x371-tensor` | 525.2 | 709.8-1,317.4 | 3.14 | yes | 9.838x | 0.921x | 0.094x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3,782.8 | 6,076.7-11,279.2 | 2.64 | yes | `a100_sxm_80gb-x336-tensor` | 523.5 | 708.4-1,314.9 | 3.13 | yes | 7.226x | 8.578x | 1.187x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 5,167.5 | 653.8-1,213.6 | 33.51 | **no** | `a100_sxm_80gb-x371-tensor` | 466.1 | 419.1-778.0 | 4.72 | yes | 11.087x | 1.560x | 0.141x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3,782.8 | 6,076.7-11,279.2 | 2.64 | yes | `a100_sxm_80gb-x336-tensor` | 464.4 | 418.7-777.2 | 4.70 | yes | 8.145x | 14.512x | 1.782x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 5,167.5 | 653.8-1,213.6 | 33.51 | **no** | `a100_sxm_80gb-x371-tensor` | 380.6 | 231.3-429.3 | 6.98 | yes | 13.578x | 2.827x | 0.208x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3,782.8 | 6,076.7-11,279.2 | 2.64 | yes | `a100_sxm_80gb-x336-tensor` | 379.0 | 231.3-429.2 | 6.95 | yes | 9.981x | 26.278x | 2.633x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 5,167.5 | 653.8-1,213.6 | 33.51 | **no** | `a100_sxm_80gb-x371-tensor` | 278.7 | 122.2-226.7 | 9.67 | **no** | 18.541x | 5.352x | 0.289x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,782.5 | 6,073.3-11,272.9 | 2.64 | yes | `a100_sxm_80gb-x448-tensor` | 281.0 | 122.1-226.7 | 9.76 | **no** | 13.461x | 49.730x | 3.694x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 5,167.5 | 653.8-1,213.6 | 33.51 | **no** | `a100_sxm_80gb-x371-hybrid` | 262.2 | 361.8-671.5 | 3.07 | yes | 19.708x | 1.807x | 0.092x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,724.1 | 5,561.7-10,323.2 | 2.84 | yes | `a100_sxm_80gb-x672-hybrid` | 262.5 | 366.6-680.5 | 3.04 | yes | 14.187x | 15.169x | 1.069x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 5,167.5 | 653.8-1,213.6 | 33.51 | **no** | `a100_sxm_80gb-x371-hybrid` | 262.2 | 361.8-671.5 | 3.07 | yes | 19.708x | 1.807x | 0.092x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,527.5 | 4,169.7-7,739.6 | 3.59 | yes | `a100_sxm_80gb-x672-hybrid` | 262.5 | 366.6-680.5 | 3.04 | yes | 13.438x | 11.373x | 0.846x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 5,167.5 | 653.8-1,213.6 | 33.51 | **no** | `a100_sxm_80gb-x371-hybrid` | 239.0 | 287.1-532.9 | 3.53 | yes | 21.623x | 2.277x | 0.105x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,315.7 | 3,063.9-5,687.1 | 4.59 | yes | `a100_sxm_80gb-x672-hybrid` | 262.5 | 366.6-680.5 | 3.04 | yes | 12.632x | 8.357x | 0.662x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 2,292.1 | 392.3-728.2 | 24.77 | **no** | `a100_sxm_80gb-x391-hybrid` | 125.7 | 125.4-232.7 | 4.25 | yes | 18.232x | 3.129x | 0.172x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,379.9 | 1,273.0-2,362.9 | 7.93 | **no** | `a100_sxm_80gb-x672-hybrid` | 170.3 | 167.3-310.6 | 4.32 | yes | 13.975x | 7.607x | 0.544x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 607.5 | 98.9-183.6 | 26.04 | **no** | `a100_sxm_80gb-x391-expert` | 91.9 | 69.6-129.3 | 5.60 | yes | 6.610x | 1.420x | 0.215x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,086.9 | 381.4-707.9 | 12.08 | **no** | `a100_sxm_80gb-x672-expert` | 110.0 | 118.6-220.1 | 3.93 | yes | 9.881x | 3.216x | 0.326x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 153.2 | 33.7-62.5 | 19.28 | **no** | `a100_sxm_80gb-x391-expert` | 63.8 | 17.6-32.7 | 15.35 | **no** | 2.403x | 1.913x | 0.796x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 342.5 | 100.3-186.2 | 14.48 | **no** | `a100_sxm_80gb-x672-expert` | 84.2 | 30.2-56.1 | 11.81 | **no** | 4.068x | 3.317x | 0.815x |

**Does the ratio compress?** Of 20 class rows in this study, 15 move the ROM-versus-GPU ratio DOWN under speculation and 5 move it UP. The movement spans 0.092x to 3.694x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 16 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 5,241.4 | 665.7-1,235.6 | 33.38 | **no** | `a100_sxm_80gb-x391-tensor` | 526.1 | 710.6-1,319.0 | 3.14 | yes | 9.962x | 0.937x | 0.094x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3,789.0 | 6,141.0-11,398.6 | 2.62 | yes | `a100_sxm_80gb-x336-tensor` | 523.6 | 708.4-1,314.9 | 3.13 | yes | 7.237x | 8.668x | 1.198x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 5,241.4 | 665.7-1,235.6 | 33.38 | **no** | `a100_sxm_80gb-x391-tensor` | 467.0 | 419.5-778.6 | 4.72 | yes | 11.223x | 1.587x | 0.141x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3,789.0 | 6,141.0-11,398.6 | 2.62 | yes | `a100_sxm_80gb-x336-tensor` | 464.4 | 418.7-777.2 | 4.70 | yes | 8.158x | 14.666x | 1.798x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 5,241.4 | 665.7-1,235.6 | 33.38 | **no** | `a100_sxm_80gb-x391-tensor` | 381.5 | 231.3-429.4 | 6.99 | yes | 13.740x | 2.877x | 0.209x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3,789.0 | 6,141.0-11,398.6 | 2.62 | yes | `a100_sxm_80gb-x336-tensor` | 379.1 | 231.3-429.2 | 6.95 | yes | 9.996x | 26.555x | 2.657x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 5,241.4 | 665.7-1,235.6 | 33.38 | **no** | `a100_sxm_80gb-x391-tensor` | 279.5 | 122.2-226.8 | 9.70 | **no** | 18.756x | 5.449x | 0.291x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,788.6 | 6,136.5-11,390.2 | 2.62 | yes | `a100_sxm_80gb-x448-tensor` | 281.0 | 122.1-226.7 | 9.76 | **no** | 13.480x | 50.246x | 3.727x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 5,241.4 | 665.7-1,235.6 | 33.38 | **no** | `a100_sxm_80gb-x391-hybrid` | 264.4 | 365.8-679.1 | 3.06 | yes | 19.823x | 1.820x | 0.092x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,731.9 | 5,632.4-10,454.6 | 2.81 | yes | `a100_sxm_80gb-x672-hybrid` | 262.8 | 366.8-680.8 | 3.04 | yes | 14.202x | 15.357x | 1.081x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 5,241.4 | 665.7-1,235.6 | 33.38 | **no** | `a100_sxm_80gb-x391-hybrid` | 264.4 | 365.8-679.1 | 3.06 | yes | 19.823x | 1.820x | 0.092x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,541.5 | 4,249.8-7,888.3 | 3.53 | yes | `a100_sxm_80gb-x672-hybrid` | 262.8 | 366.8-680.8 | 3.04 | yes | 13.478x | 11.587x | 0.860x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 5,241.4 | 665.7-1,235.6 | 33.38 | **no** | `a100_sxm_80gb-x391-hybrid` | 244.4 | 299.5-555.9 | 3.46 | yes | 21.447x | 2.223x | 0.104x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,315.7 | 3,118.9-5,789.1 | 4.51 | yes | `a100_sxm_80gb-x672-hybrid` | 262.8 | 366.8-680.8 | 3.04 | yes | 12.618x | 8.504x | 0.674x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 2,375.6 | 402.0-746.2 | 25.05 | **no** | `a100_sxm_80gb-x391-hybrid` | 126.0 | 125.5-232.9 | 4.26 | yes | 18.847x | 3.204x | 0.170x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,497.1 | 1,311.4-2,434.2 | 8.07 | **no** | `a100_sxm_80gb-x672-hybrid` | 170.7 | 167.4-310.8 | 4.32 | yes | 14.632x | 7.833x | 0.535x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 631.0 | 101.4-188.2 | 26.39 | **no** | `a100_sxm_80gb-x391-expert` | 92.6 | 71.2-132.1 | 5.52 | yes | 6.813x | 1.424x | 0.209x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,188.8 | 395.2-733.6 | 12.75 | **no** | `a100_sxm_80gb-x672-expert` | 110.6 | 121.2-224.9 | 3.87 | yes | 10.749x | 3.261x | 0.303x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 159.2 | 34.9-64.7 | 19.37 | **no** | `a100_sxm_80gb-x391-expert` | 65.2 | 18.0-33.4 | 15.34 | **no** | 2.444x | 1.935x | 0.792x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 384.0 | 104.2-193.3 | 15.63 | **no** | `a100_sxm_80gb-x672-expert` | 85.6 | 30.9-57.4 | 11.74 | **no** | 4.485x | 3.368x | 0.751x |

**Does the ratio compress?** Of 20 class rows in this study, 15 move the ROM-versus-GPU ratio DOWN under speculation and 5 move it UP. The movement spans 0.092x to 3.727x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 7 of 20 ROM rows and 16 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 28,190.4 | 16,327.9-30,306.7 | 7.32 | yes | `b200_sxm-x8-tensor` | 2,013.6 | 6,900.6-12,808.3 | 1.24 | yes | 14.000x | 2.366x | 0.169x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | 19,432.8-36,069.8 | 1.41 | yes | `b200_sxm-x29-nvl72-tensor` | 3,724.5 | 12,282.7-22,798.4 | 1.29 | yes | 1.736x | 1.582x | 0.912x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-tensor-x62-romfill` | 14,725.8 | 18,709.6-34,727.5 | 3.34 | yes | `b200_sxm-x32-nvl72-tensor` | 3,730.3 | 11,208.1-20,803.7 | 1.41 | yes | 3.948x | 1.669x | 0.423x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 5,536.7 | 18,851.6-34,991.1 | 1.25 | yes | `b200_sxm-x173-nvl72-hybrid` | 4,353.8 | 13,887.4-25,776.9 | 1.33 | yes | 1.272x | 1.357x | 1.067x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-tensor-x62-romfill` | 12,494.2 | 10,879.7-20,194.1 | 4.87 | yes | `b200_sxm-x32-nvl72-tensor` | 3,526.8 | 9,143.4-16,971.3 | 1.64 | yes | 3.543x | 1.190x | 0.336x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 5,536.7 | 18,851.6-34,991.1 | 1.25 | yes | `b200_sxm-x173-nvl72-hybrid` | 4,319.3 | 13,208.0-24,515.7 | 1.39 | yes | 1.282x | 1.427x | 1.113x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-tensor-x62` | 9,588.1 | 9,066.7-16,829.0 | 4.48 | yes | `b200_sxm-x32-nvl72-tensor` | 3,180.0 | 6,681.6-12,401.9 | 2.02 | yes | 3.015x | 1.357x | 0.450x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,530.5 | 18,828.1-34,947.4 | 1.25 | yes | `b200_sxm-x231-nvl72-hybrid` | 4,211.0 | 11,744.9-21,800.1 | 1.52 | yes | 1.313x | 1.603x | 1.221x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9,373.0 | 4,655.5-8,641.2 | 8.54 | **no** | `b200_sxm-x173-nvl72-hybrid` | 3,944.5 | 8,321.9-15,446.5 | 2.01 | yes | 2.376x | 0.559x | 0.235x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,187.1 | 17,278.9-32,071.9 | 1.27 | yes | `b200_sxm-x347-nvl72-hybrid` | 4,196.5 | 10,003.2-18,567.2 | 1.78 | yes | 1.236x | 1.727x | 1.397x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9,373.0 | 4,655.5-8,641.2 | 8.54 | **no** | `b200_sxm-x173-nvl72-hybrid` | 3,535.5 | 5,569.6-10,337.9 | 2.69 | yes | 2.651x | 0.836x | 0.315x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,183.1 | 13,090.3-24,297.4 | 1.35 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,918.6 | 7,147.7-13,267.0 | 2.32 | yes | 1.068x | 1.831x | 1.716x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9,373.0 | 4,655.5-8,641.2 | 8.54 | **no** | `b200_sxm-x173-nvl72-hybrid` | 2,928.2 | 3,331.1-6,183.0 | 3.73 | yes | 3.201x | 1.398x | 0.437x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,015.8 | 8,816.1-16,363.9 | 1.45 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,460.3 | 4,540.9-8,428.4 | 3.23 | yes | 0.872x | 1.942x | 2.228x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,185.2 | 1,561.1-2,897.6 | 8.65 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,442.0 | 970.9-1,802.0 | 6.30 | yes | 2.209x | 1.608x | 0.728x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1,127.6 | 2,968.8-5,510.5 | 1.61 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,033.5 | 1,416.8-2,629.9 | 6.09 | yes | 0.555x | 2.095x | 3.779x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 803.3 | 391.7-727.1 | 8.70 | **no** | `b200_sxm-x173-hybrid` | 536.8 | 643.1-1,193.6 | 3.54 | yes | 1.497x | 0.609x | 0.407x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 336.6 | 845.8-1,569.9 | 1.69 | yes | `b200_sxm-x347-hybrid` | 787.1 | 914.8-1,698.0 | 3.65 | yes | 0.428x | 0.925x | 2.162x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 201.3 | 74.6-138.5 | 11.44 | **no** | `b200_sxm-x173-hybrid` | 169.7 | 166.4-308.9 | 4.32 | yes | 1.187x | 0.448x | 0.378x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 84.4 | 211.9-393.2 | 1.69 | yes | `b200_sxm-x347-hybrid` | 290.6 | 249.1-462.4 | 4.95 | yes | 0.290x | 0.850x | 2.928x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x59` | 18,118.9 | 3,339.8-6,199.1 | 23.00 | **no** | `b200_sxm-x30-nvl72-tensor` | 3,566.3 | 8,138.3-15,105.8 | 1.86 | yes | 5.081x | 0.410x | 0.081x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | 6,168.1 | 953.1-1,769.1 | 27.44 | **no** | `b200_sxm-x29-nvl72-tensor` | 3,540.5 | 7,997.5-14,844.5 | 1.88 | yes | 1.742x | 0.119x | 0.068x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 17,197.9 | 3,125.3-5,801.0 | 23.33 | **no** | `b200_sxm-x32-nvl72-tensor` | 3,369.9 | 6,800.7-12,623.0 | 2.10 | yes | 5.103x | 0.460x | 0.090x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 5,328.6 | 14,574.2-27,051.6 | 1.55 | yes | `b200_sxm-x202-nvl72-hybrid` | 3,969.3 | 11,354.9-21,076.2 | 1.48 | yes | 1.342x | 1.284x | 0.956x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 17,197.9 | 3,125.3-5,801.0 | 23.33 | **no** | `b200_sxm-x32-nvl72-tensor` | 2,978.7 | 5,179.3-9,613.5 | 2.44 | yes | 5.774x | 0.603x | 0.105x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 5,328.6 | 14,574.2-27,051.6 | 1.55 | yes | `b200_sxm-x202-nvl72-hybrid` | 3,911.6 | 10,560.2-19,601.1 | 1.57 | yes | 1.362x | 1.380x | 1.013x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 17,197.9 | 3,125.3-5,801.0 | 23.33 | **no** | `b200_sxm-x32-nvl72-tensor` | 2,442.8 | 3,844.3-7,135.6 | 2.69 | yes | 7.040x | 0.813x | 0.115x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 5,325.7 | 14,567.3-27,038.8 | 1.55 | yes | `b200_sxm-x231-nvl72-hybrid` | 3,687.7 | 8,919.9-16,556.5 | 1.75 | yes | 1.444x | 1.633x | 1.131x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 17,197.9 | 3,125.3-5,801.0 | 23.33 | **no** | `b200_sxm-x32-nvl72-tensor` | 1,847.5 | 2,743.6-5,092.4 | 2.86 | yes | 9.309x | 1.139x | 0.122x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 5,229.6 | 13,603.6-25,250.0 | 1.63 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,573.1 | 7,765.7-14,414.2 | 1.95 | yes | 1.464x | 1.752x | 1.197x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 13,849.4 | 2,991.6-5,552.8 | 19.63 | **no** | `b200_sxm-x86-nvl72-hybrid` | 2,112.4 | 3,018.0-5,601.8 | 2.97 | yes | 6.556x | 0.991x | 0.151x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,916.6 | 10,817.4-20,078.5 | 1.93 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,186.7 | 5,588.3-10,372.7 | 2.42 | yes | 1.543x | 1.936x | 1.255x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 13,829.4 | 2,991.2-5,552.1 | 19.60 | **no** | `b200_sxm-x173-nvl72-hybrid` | 2,107.3 | 2,603.9-4,833.2 | 3.43 | yes | 6.563x | 1.149x | 0.175x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,390.9 | 7,673.9-14,243.8 | 2.43 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,653.0 | 3,608.5-6,697.8 | 3.12 | yes | 1.655x | 2.127x | 1.285x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 5,526.7 | 1,298.0-2,409.3 | 18.05 | **no** | `b200_sxm-x173-nvl72-hybrid` | 1,131.8 | 842.4-1,563.6 | 5.70 | yes | 4.883x | 1.541x | 0.316x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 2,675.0 | 3,452.6-6,408.6 | 3.28 | yes | `b200_sxm-x347-nvl72-hybrid` | 1,509.3 | 1,220.5-2,265.4 | 5.24 | yes | 1.772x | 2.829x | 1.596x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,521.0 | 329.4-611.4 | 19.58 | **no** | `b200_sxm-x173-nvl72-hybrid` | 546.5 | 218.7-405.9 | 10.60 | **no** | 2.783x | 1.506x | 0.541x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,257.0 | 612.4-1,136.8 | 8.70 | **no** | `b200_sxm-x347-nvl72-hybrid` | 756.4 | 331.1-614.6 | 9.69 | **no** | 1.662x | 1.850x | 1.113x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 464.4 | 177.0-328.5 | 11.13 | **no** | `b200_sxm-x173-expert` | 217.4 | 78.4-145.5 | 11.76 | **no** | 2.136x | 2.258x | 1.057x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 319.6 | 190.4-353.5 | 7.11 | yes | `b200_sxm-x347-expert` | 371.8 | 156.4-290.3 | 10.08 | **no** | 0.859x | 1.218x | 1.417x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x184` | 5,063.9 | 8,181.4-15,185.8 | 2.62 | yes | `b200_sxm-x94-nvl72-hybrid` | 2,193.2 | 4,728.7-8,777.2 | 1.97 | yes | 2.309x | 1.730x | 0.749x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 3,736.6 | 5,628.1-10,446.6 | 2.81 | yes | `b200_sxm-x173-nvl72-hybrid` | 2,310.3 | 5,441.3-10,099.7 | 1.80 | yes | 1.617x | 1.034x | 0.640x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 4,226.3 | 569.3-1,056.7 | 31.48 | **no** | `b200_sxm-x203-nvl72-hybrid` | 2,402.2 | 5,865.0-10,886.2 | 1.74 | yes | 1.759x | 0.097x | 0.055x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3,119.7 | 5,368.5-9,964.6 | 2.46 | yes | `b200_sxm-x1358-nvl72-hybrid` | 2,230.8 | 5,591.2-10,378.0 | 1.69 | yes | 1.398x | 0.960x | 0.687x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 4,226.3 | 569.3-1,056.7 | 31.48 | **no** | `b200_sxm-x203-nvl72-hybrid` | 2,327.0 | 5,250.0-9,744.6 | 1.88 | yes | 1.816x | 0.108x | 0.060x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3,119.7 | 5,368.5-9,964.6 | 2.46 | yes | `b200_sxm-x1358-nvl72-hybrid` | 2,230.8 | 5,591.2-10,378.0 | 1.69 | yes | 1.398x | 0.960x | 0.687x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 4,226.3 | 569.3-1,056.7 | 31.48 | **no** | `b200_sxm-x203-nvl72-hybrid` | 2,070.3 | 3,832.8-7,114.2 | 2.29 | yes | 2.041x | 0.149x | 0.073x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3,119.7 | 5,368.5-9,964.6 | 2.46 | yes | `b200_sxm-x1358-nvl72-hybrid` | 2,230.8 | 5,591.2-10,378.0 | 1.69 | yes | 1.398x | 0.960x | 0.687x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 4,226.3 | 569.3-1,056.7 | 31.48 | **no** | `b200_sxm-x203-nvl72-hybrid` | 1,702.9 | 2,605.7-4,836.5 | 2.77 | yes | 2.482x | 0.218x | 0.088x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3,119.7 | 5,368.5-9,964.6 | 2.46 | yes | `b200_sxm-x1358-nvl72-hybrid` | 2,230.8 | 5,591.2-10,378.0 | 1.69 | yes | 1.398x | 0.960x | 0.687x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 4,226.3 | 569.3-1,056.7 | 31.48 | **no** | `b200_sxm-x203-nvl72-hybrid` | 1,271.2 | 1,686.0-3,129.5 | 3.20 | yes | 3.325x | 0.338x | 0.102x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 3,119.7 | 5,368.5-9,964.6 | 2.46 | yes | `b200_sxm-x1358-nvl72-hybrid` | 2,093.3 | 4,457.1-8,273.0 | 1.99 | yes | 1.490x | 1.204x | 0.808x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 4,226.3 | 569.3-1,056.7 | 31.48 | **no** | `b200_sxm-x203-nvl72-hybrid` | 867.4 | 1,037.7-1,926.1 | 3.54 | yes | 4.873x | 0.549x | 0.113x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2,911.1 | 4,639.2-8,610.9 | 2.66 | yes | `b200_sxm-x1358-nvl72-hybrid` | 1,820.3 | 2,975.3-5,522.5 | 2.59 | yes | 1.599x | 1.559x | 0.975x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,769.6 | 325.3-603.8 | 23.07 | **no** | `b200_sxm-x203-nvl72-hybrid` | 366.2 | 336.6-624.7 | 4.61 | yes | 4.832x | 0.966x | 0.200x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,658.7 | 1,451.8-2,694.7 | 4.84 | yes | `b200_sxm-x1358-nvl72-hybrid` | 1,046.7 | 1,107.1-2,055.0 | 4.01 | yes | 1.585x | 1.311x | 0.827x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 462.6 | 81.9-152.1 | 23.94 | **no** | `b200_sxm-x203-nvl72-hybrid` | 163.4 | 85.9-159.4 | 8.07 | **no** | 2.831x | 0.954x | 0.337x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 609.6 | 779.9-1,447.6 | 3.31 | yes | `b200_sxm-x1358-nvl72-hybrid` | 441.5 | 331.4-615.1 | 5.65 | yes | 1.381x | 2.354x | 1.704x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 116.5 | 26.3-48.9 | 18.75 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 180.2 | 36.7-68.1 | 20.83 | **no** | `b200_sxm-x1358-expert` | 254.4 | 210.9-391.4 | 5.12 | yes | 0.708x | 0.174x | 0.246x |

**Does the ratio compress?** Of 59 class rows in this study, 40 move the ROM-versus-GPU ratio DOWN under speculation and 19 move it UP. The movement spans 0.055x to 3.779x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 32 of 60 ROM rows and 54 of 60 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 25,281.1 | 12,324.9-22,876.7 | 8.70 | **no** | `a100_sxm_80gb-x16-tensor` | 758.6 | 1,864.1-3,460.1 | 1.73 | yes | 33.326x | 6.612x | 0.198x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | 17,763.6-32,971.6 | 1.54 | yes | `a100_sxm_80gb-x56-tensor` | 1,109.0 | 1,896.0-3,519.3 | 2.48 | yes | 5.829x | 9.369x | 1.607x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x87-romfill` | 10,992.1 | 17,379.9-32,259.4 | 2.68 | yes | `a100_sxm_80gb-x86-tensor` | 1,084.9 | 1,181.7-2,193.4 | 3.89 | yes | 10.132x | 14.708x | 1.452x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x8-romfill` | 5,028.2 | 17,926.8-33,274.5 | 1.19 | yes | `a100_sxm_80gb-x448-tensor` | 889.3 | 1,059.1-1,965.9 | 3.56 | yes | 5.654x | 16.926x | 2.993x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x87-romfill` | 9,063.7 | 10,434.2-19,367.3 | 3.68 | yes | `a100_sxm_80gb-x86-tensor` | 927.9 | 673.4-1,249.9 | 5.84 | yes | 9.768x | 15.495x | 1.586x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x8` | 4,531.9 | 13,806.5-25,626.7 | 1.39 | yes | `a100_sxm_80gb-x448-tensor` | 783.0 | 614.7-1,140.9 | 5.40 | yes | 5.788x | 22.462x | 3.881x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x138` | 7,134.8 | 9,338.8-17,334.0 | 3.24 | yes | `a100_sxm_80gb-x136-tensor` | 744.2 | 353.4-655.9 | 8.93 | **no** | 9.588x | 26.429x | 2.757x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 4,325.6 | 15,945.5-29,596.9 | 1.15 | yes | `a100_sxm_80gb-x448-tensor` | 632.0 | 334.1-620.2 | 8.02 | **no** | 6.845x | 47.723x | 6.972x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x227` | 5,223.1 | 5,925.3-10,998.2 | 3.74 | yes | `a100_sxm_80gb-x224-hybrid` | 597.8 | 1,902.3-3,530.9 | 1.33 | yes | 8.737x | 3.115x | 0.357x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,846.9 | 14,149.0-26,262.4 | 1.15 | yes | `a100_sxm_80gb-x672-hybrid` | 591.2 | 1,845.0-3,424.5 | 1.36 | yes | 6.507x | 7.669x | 1.179x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,125.0 | 3,381.0-6,275.5 | 6.43 | yes | `a100_sxm_80gb-x272-hybrid` | 592.8 | 1,859.0-3,450.5 | 1.35 | yes | 8.645x | 1.819x | 0.210x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,678.3 | 9,804.2-18,197.9 | 1.16 | yes | `a100_sxm_80gb-x672-hybrid` | 591.2 | 1,845.0-3,424.5 | 1.36 | yes | 4.530x | 5.314x | 1.173x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 5,125.0 | 3,381.0-6,275.5 | 6.43 | yes | `a100_sxm_80gb-x272-hybrid` | 561.3 | 1,609.4-2,987.2 | 1.48 | yes | 9.131x | 2.101x | 0.230x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,666.0 | 3,665.5-6,803.7 | 1.93 | yes | `a100_sxm_80gb-x672-hybrid` | 591.2 | 1,845.0-3,424.5 | 1.36 | yes | 2.818x | 1.987x | 0.705x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,773.0 | 1,130.7-2,098.6 | 6.65 | yes | `a100_sxm_80gb-x335-hybrid` | 445.0 | 955.5-1,773.6 | 1.97 | yes | 3.984x | 1.183x | 0.297x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 509.8 | 1,692.7-3,141.9 | 1.28 | yes | `a100_sxm_80gb-x672-hybrid` | 522.8 | 1,348.2-2,502.4 | 1.64 | yes | 0.975x | 1.256x | 1.287x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 452.2 | 285.6-530.1 | 6.71 | yes | `a100_sxm_80gb-x335-hybrid` | 236.5 | 292.2-542.4 | 3.43 | yes | 1.912x | 0.977x | 0.511x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 137.6 | 499.6-927.3 | 1.17 | yes | `a100_sxm_80gb-x672-hybrid` | 344.7 | 565.7-1,050.0 | 2.58 | yes | 0.399x | 0.883x | 2.213x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 113.4 | 71.4-132.6 | 6.73 | yes | `a100_sxm_80gb-x335-hybrid` | 82.3 | 75.0-139.2 | 4.65 | yes | 1.378x | 0.953x | 0.691x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 34.4 | 72.8-135.1 | 2.01 | yes | `a100_sxm_80gb-x672-hybrid` | 145.9 | 148.9-276.3 | 4.16 | yes | 0.236x | 0.489x | 2.072x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x83` | 13,876.3 | 2,385.2-4,427.2 | 24.67 | **no** | `a100_sxm_80gb-x82-tensor` | 1,041.9 | 1,545.4-2,868.5 | 2.86 | yes | 13.318x | 1.543x | 0.116x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 5,467.3 | 13,048.9-24,220.5 | 1.78 | yes | `a100_sxm_80gb-x112-tensor` | 1,065.4 | 1,578.2-2,929.3 | 2.86 | yes | 5.131x | 8.268x | 1.611x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 13,172.6 | 2,255.4-4,186.2 | 24.76 | **no** | `a100_sxm_80gb-x87-tensor` | 940.3 | 966.0-1,793.0 | 4.13 | yes | 14.009x | 2.335x | 0.167x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10-romfill` | 4,970.0 | 12,978.0-24,088.9 | 1.62 | yes | `a100_sxm_80gb-x560-tensor` | 748.4 | 899.9-1,670.3 | 3.53 | yes | 6.641x | 14.422x | 2.172x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 13,172.6 | 2,255.4-4,186.2 | 24.76 | **no** | `a100_sxm_80gb-x87-tensor` | 781.7 | 553.7-1,027.8 | 5.99 | yes | 16.851x | 4.073x | 0.242x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10-romfill` | 4,970.0 | 12,978.0-24,088.9 | 1.62 | yes | `a100_sxm_80gb-x560-hybrid` | 703.9 | 1,394.8-2,588.9 | 2.14 | yes | 7.060x | 9.305x | 1.318x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 13,172.6 | 2,255.4-4,186.2 | 24.76 | **no** | `a100_sxm_80gb-x87-hybrid` | 737.9 | 1,173.4-2,177.9 | 2.67 | yes | 17.851x | 1.922x | 0.108x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10-romfill` | 4,970.0 | 12,978.0-24,088.9 | 1.62 | yes | `a100_sxm_80gb-x560-hybrid` | 703.9 | 1,394.8-2,588.9 | 2.14 | yes | 7.060x | 9.305x | 1.318x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 13,172.6 | 2,255.4-4,186.2 | 24.76 | **no** | `a100_sxm_80gb-x87-hybrid` | 671.8 | 1,003.9-1,863.4 | 2.84 | yes | 19.607x | 2.247x | 0.115x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4,787.7 | 11,951.2-22,183.1 | 1.70 | yes | `a100_sxm_80gb-x672-hybrid` | 703.9 | 1,394.8-2,588.9 | 2.14 | yes | 6.801x | 8.568x | 1.260x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x99` | 11,363.0 | 1,930.4-3,583.1 | 24.96 | **no** | `a100_sxm_80gb-x98-hybrid` | 540.9 | 747.1-1,386.7 | 3.07 | yes | 21.006x | 2.584x | 0.123x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4,189.5 | 5,504.8-10,217.7 | 3.23 | yes | `a100_sxm_80gb-x672-hybrid` | 703.9 | 1,394.8-2,588.9 | 2.14 | yes | 5.952x | 3.947x | 0.663x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 10,757.0 | 2,170.6-4,028.9 | 21.01 | **no** | `a100_sxm_80gb-x312-hybrid` | 624.0 | 1,005.6-1,866.6 | 2.63 | yes | 17.240x | 2.158x | 0.125x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3,351.8 | 4,822.7-8,951.6 | 2.95 | yes | `a100_sxm_80gb-x672-hybrid` | 703.9 | 1,394.8-2,588.9 | 2.14 | yes | 4.762x | 3.458x | 0.726x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,112.9 | 940.4-1,745.5 | 18.54 | **no** | `a100_sxm_80gb-x335-hybrid` | 346.6 | 549.5-1,020.0 | 2.67 | yes | 11.867x | 1.711x | 0.144x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,523.8 | 2,766.2-5,134.4 | 2.34 | yes | `a100_sxm_80gb-x672-hybrid` | 493.5 | 711.3-1,320.2 | 2.94 | yes | 3.088x | 3.889x | 1.260x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x237` | 1,164.2 | 293.1-544.0 | 16.84 | **no** | `a100_sxm_80gb-x234-expert` | 212.1 | 97.0-180.1 | 9.27 | **no** | 5.488x | 3.021x | 0.550x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 519.4 | 442.0-820.4 | 4.98 | yes | `a100_sxm_80gb-x672-expert` | 332.9 | 270.9-502.8 | 5.21 | yes | 1.560x | 1.632x | 1.046x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 423.3 | 119.9-222.5 | 14.97 | **no** | `a100_sxm_80gb-x335-expert` | 129.6 | 35.0-65.0 | 15.68 | **no** | 3.267x | 3.421x | 1.047x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 130.8 | 105.9-196.5 | 5.24 | yes | `a100_sxm_80gb-x672-expert` | 204.9 | 70.0-130.0 | 12.40 | **no** | 0.638x | 1.512x | 2.368x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x237` | 4,414.2 | 7,246.3-13,450.0 | 2.58 | yes | `a100_sxm_80gb-x234-tensor` | 689.9 | 767.9-1,425.3 | 3.81 | yes | 6.398x | 9.436x | 1.475x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 3,649.0 | 4,403.2-8,172.9 | 3.51 | yes | `a100_sxm_80gb-x504-tensor` | 529.0 | 713.0-1,323.5 | 3.15 | yes | 6.898x | 6.175x | 0.895x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 2,415.3 | 1,392.0-2,583.8 | 7.36 | yes | `a100_sxm_80gb-x3694-tensor` | 481.5 | 422.5-784.2 | 4.83 | yes | 5.017x | 3.295x | 0.657x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 2,415.3 | 1,392.0-2,583.8 | 7.36 | yes | `a100_sxm_80gb-x3694-tensor` | 395.1 | 231.4-429.6 | 7.24 | yes | 6.114x | 6.015x | 0.984x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 2,415.3 | 1,392.0-2,583.8 | 7.36 | yes | `a100_sxm_80gb-x3694-tensor` | 290.8 | 121.5-225.6 | 10.14 | **no** | 8.307x | 11.455x | 1.379x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 2,415.3 | 1,392.0-2,583.8 | 7.36 | yes | `a100_sxm_80gb-x3694-hybrid` | 251.9 | 360.9-669.9 | 2.96 | yes | 9.589x | 3.857x | 0.402x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 2,415.3 | 1,392.0-2,583.8 | 7.36 | yes | `a100_sxm_80gb-x3694-hybrid` | 251.9 | 360.9-669.9 | 2.96 | yes | 9.589x | 3.857x | 0.402x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 2,415.3 | 1,392.0-2,583.8 | 7.36 | yes | `a100_sxm_80gb-x3694-hybrid` | 251.9 | 360.9-669.9 | 2.96 | yes | 9.589x | 3.857x | 0.402x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1,160.3 | 1,140.5-2,117.0 | 4.31 | yes | `a100_sxm_80gb-x3694-hybrid` | 251.9 | 360.9-669.9 | 2.96 | yes | 4.606x | 3.160x | 0.686x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 374.2 | 659.2-1,223.5 | 2.41 | yes | `a100_sxm_80gb-x3694-hybrid` | 185.3 | 201.6-374.2 | 3.90 | yes | 2.020x | 3.269x | 1.619x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 103.4 | 26.8-49.8 | 16.34 | **no** | `a100_sxm_80gb-x3694-expert` | 121.8 | 87.6-162.7 | 5.89 | yes | 0.849x | 0.306x | 0.361x |

**Does the ratio compress?** Of 51 class rows in this study, 27 move the ROM-versus-GPU ratio DOWN under speculation and 24 move it UP. The movement spans 0.108x to 6.972x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 39 of 51 ROM rows and 45 of 51 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 40,683.1 | 12,302.2-22,834.5 | 14.02 | **no** | `b200_sxm-x2-tensor` | 1,712.2 | 6,124.6-11,368.0 | 1.19 | yes | 23.761x | 2.009x | 0.085x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | 23,018.0-42,724.4 | 1.19 | yes | `b200_sxm-x29-nvl72-tensor` | 4,776.9 | 15,494.7-28,760.1 | 1.31 | yes | 1.353x | 1.486x | 1.098x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-tensor-x62-romfill` | 14,725.8 | 27,791.7-51,585.2 | 2.25 | yes | `b200_sxm-x32-nvl72-tensor` | 4,662.6 | 13,526.9-25,107.8 | 1.46 | yes | 3.158x | 2.055x | 0.651x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 5,536.7 | 20,716.9-38,453.4 | 1.13 | yes | `b200_sxm-x173-nvl72-hybrid` | 5,001.5 | 15,743.0-29,221.1 | 1.35 | yes | 1.107x | 1.316x | 1.189x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-tensor-x62-romfill` | 12,494.2 | 17,549.6-32,574.4 | 3.02 | yes | `b200_sxm-x32-nvl72-tensor` | 4,349.1 | 10,629.9-19,730.5 | 1.73 | yes | 2.873x | 1.651x | 0.575x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 5,536.7 | 20,716.9-38,453.4 | 1.13 | yes | `b200_sxm-x173-nvl72-hybrid` | 4,956.1 | 14,875.5-27,610.8 | 1.41 | yes | 1.117x | 1.393x | 1.247x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x196-romfill` | 9,944.2 | 12,588.9-23,366.6 | 3.35 | yes | `b200_sxm-x100-nvl72-hybrid` | 4,600.2 | 10,608.8-19,691.3 | 1.84 | yes | 2.162x | 1.187x | 0.549x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 5,530.5 | 20,688.6-38,400.7 | 1.13 | yes | `b200_sxm-x231-nvl72-hybrid` | 4,813.0 | 13,043.2-24,209.8 | 1.56 | yes | 1.149x | 1.586x | 1.380x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x196-romfill` | 9,944.2 | 12,588.9-23,366.6 | 3.35 | yes | `b200_sxm-x100-nvl72-hybrid` | 4,154.4 | 7,340.9-13,625.6 | 2.40 | yes | 2.394x | 1.715x | 0.716x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 5,187.1 | 19,415.3-36,037.4 | 1.13 | yes | `b200_sxm-x347-nvl72-hybrid` | 4,682.1 | 10,762.4-19,976.5 | 1.84 | yes | 1.108x | 1.804x | 1.628x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x196-romfill` | 9,944.2 | 12,588.9-23,366.6 | 3.35 | yes | `b200_sxm-x100-nvl72-hybrid` | 3,480.0 | 4,530.5-8,409.1 | 3.26 | yes | 2.858x | 2.779x | 0.972x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 4,183.1 | 15,709.5-29,158.9 | 1.13 | yes | `b200_sxm-x347-nvl72-hybrid` | 4,338.9 | 7,527.1-13,971.3 | 2.44 | yes | 0.964x | 2.087x | 2.165x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 9,944.2 | 12,588.9-23,366.6 | 3.35 | yes | `b200_sxm-x173-nvl72-hybrid` | 3,207.6 | 3,442.9-6,390.5 | 3.95 | yes | 3.100x | 3.656x | 1.179x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,015.8 | 11,369.4-21,103.1 | 1.12 | yes | `b200_sxm-x347-nvl72-hybrid` | 3,784.0 | 4,694.2-8,713.0 | 3.42 | yes | 0.797x | 2.422x | 3.039x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3,323.3 | 4,294.0-7,970.1 | 3.28 | yes | `b200_sxm-x173-hybrid` | 1,569.6 | 2,360.1-4,380.7 | 2.82 | yes | 2.117x | 1.819x | 0.859x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 1,127.6 | 2,968.8-5,510.5 | 1.61 | yes | `b200_sxm-x347-nvl72-hybrid` | 2,141.1 | 1,439.9-2,672.6 | 6.31 | yes | 0.527x | 2.062x | 3.915x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 832.8 | 1,084.5-2,013.0 | 3.26 | yes | `b200_sxm-x173-hybrid` | 607.9 | 685.0-1,271.4 | 3.76 | yes | 1.370x | 1.583x | 1.156x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 336.6 | 1,290.8-2,395.9 | 1.11 | yes | `b200_sxm-x347-hybrid` | 949.7 | 980.4-1,819.7 | 4.11 | yes | 0.354x | 1.317x | 3.715x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x340-romfill` | 208.4 | 145.4-269.9 | 6.08 | yes | `b200_sxm-x173-pipeline` | 188.7 | 714.1-1,325.4 | 1.12 | yes | 1.104x | 0.204x | 0.184x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 84.4 | 323.6-600.7 | 1.11 | yes | `b200_sxm-x347-pipeline` | 336.8 | 1,277.2-2,370.6 | 1.12 | yes | 0.251x | 0.253x | 1.011x |

**Does the ratio compress?** Of 20 class rows in this study, 8 move the ROM-versus-GPU ratio DOWN under speculation and 12 move it UP. The movement spans 0.085x to 3.915x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 19 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 4.24-7.87) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-hw-hybrid-x8-romfill` | 33,480.9 | 9,392.1-17,433.0 | 15.11 | **no** | `a100_sxm_80gb-x8-tensor` | 1,302.6 | 4,338.0-8,051.8 | 1.27 | yes | 25.704x | 2.165x | 0.084x |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 6,464.4 | 22,146.5-41,106.9 | 1.24 | yes | `a100_sxm_80gb-x56-tensor` | 1,279.6 | 2,027.9-3,764.0 | 2.68 | yes | 5.052x | 10.921x | 2.162x |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-tensor-x87-romfill` | 10,992.1 | 24,828.0-46,084.1 | 1.88 | yes | `a100_sxm_80gb-x86-hybrid` | 1,249.2 | 3,945.4-7,323.2 | 1.34 | yes | 8.799x | 6.293x | 0.715x |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-tensor-x8-romfill` | 5,028.2 | 18,101.0-33,597.9 | 1.18 | yes | `a100_sxm_80gb-x448-hybrid` | 1,176.1 | 3,311.5-6,146.6 | 1.51 | yes | 4.275x | 5.466x | 1.279x |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-tensor-x87-romfill` | 9,063.7 | 16,308.7-30,271.2 | 2.36 | yes | `a100_sxm_80gb-x86-hybrid` | 1,249.2 | 3,945.4-7,323.2 | 1.34 | yes | 7.255x | 4.134x | 0.570x |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-tensor-x8` | 4,531.9 | 13,806.5-25,626.7 | 1.39 | yes | `a100_sxm_80gb-x448-hybrid` | 1,176.1 | 3,311.5-6,146.6 | 1.51 | yes | 3.853x | 4.169x | 1.082x |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-tensor-x138` | 7,134.8 | 11,036.0-20,484.2 | 2.74 | yes | `a100_sxm_80gb-x136-hybrid` | 1,241.6 | 3,799.6-7,052.5 | 1.39 | yes | 5.747x | 2.905x | 0.505x |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 4,325.6 | 16,510.8-30,646.3 | 1.11 | yes | `a100_sxm_80gb-x448-hybrid` | 1,176.1 | 3,311.5-6,146.6 | 1.51 | yes | 3.678x | 4.986x | 1.356x |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-tensor-x227` | 5,223.1 | 6,707.7-12,450.4 | 3.30 | yes | `a100_sxm_80gb-x224-hybrid` | 1,202.8 | 3,500.8-6,498.0 | 1.46 | yes | 4.342x | 1.916x | 0.441x |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,846.9 | 14,746.4-27,371.3 | 1.11 | yes | `a100_sxm_80gb-x672-hybrid` | 1,176.1 | 3,311.5-6,146.6 | 1.51 | yes | 3.271x | 4.453x | 1.361x |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 5,125.0 | 9,253.9-17,176.4 | 2.35 | yes | `a100_sxm_80gb-x272-hybrid` | 1,182.7 | 3,356.9-6,230.8 | 1.49 | yes | 4.333x | 2.757x | 0.636x |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 2,678.3 | 10,387.4-19,280.4 | 1.09 | yes | `a100_sxm_80gb-x672-hybrid` | 1,176.1 | 3,311.5-6,146.6 | 1.51 | yes | 2.277x | 3.137x | 1.377x |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 5,125.0 | 9,253.9-17,176.4 | 2.35 | yes | `a100_sxm_80gb-x272-hybrid` | 1,063.5 | 2,592.9-4,812.9 | 1.74 | yes | 4.819x | 3.569x | 0.741x |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12` | 1,666.0 | 3,665.5-6,803.7 | 1.93 | yes | `a100_sxm_80gb-x672-hybrid` | 1,176.1 | 3,311.5-6,146.6 | 1.51 | yes | 1.417x | 1.107x | 0.781x |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 1,773.0 | 3,133.8-5,816.7 | 2.40 | yes | `a100_sxm_80gb-x335-hybrid` | 712.5 | 1,059.6-1,966.8 | 2.85 | yes | 2.488x | 2.957x | 1.189x |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12` | 509.8 | 1,692.7-3,141.9 | 1.28 | yes | `a100_sxm_80gb-x672-hybrid` | 933.3 | 1,886.3-3,501.3 | 2.10 | yes | 0.546x | 0.897x | 1.643x |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 452.2 | 806.3-1,496.7 | 2.38 | yes | `a100_sxm_80gb-x335-hybrid` | 295.5 | 292.2-542.4 | 4.29 | yes | 1.531x | 2.759x | 1.803x |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 137.6 | 549.9-1,020.8 | 1.06 | yes | `a100_sxm_80gb-x672-hybrid` | 485.5 | 565.7-1,050.0 | 3.64 | yes | 0.283x | 0.972x | 3.431x |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 113.4 | 201.8-374.7 | 2.38 | yes | `a100_sxm_80gb-x335-hybrid` | 88.4 | 75.0-139.2 | 5.00 | yes | 1.282x | 2.692x | 2.100x |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12` | 34.4 | 72.8-135.1 | 2.01 | yes | `a100_sxm_80gb-x672-hybrid` | 166.3 | 148.9-276.3 | 4.74 | yes | 0.207x | 0.489x | 2.362x |

**Does the ratio compress?** Of 20 class rows in this study, 8 move the ROM-versus-GPU ratio DOWN under speculation and 12 move it UP. The movement spans 0.084x to 3.431x. The ratio does not compress on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (7.87) speculation is worth having on 19 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

## Where the drafter lives on a ROM machine

The locality rule -- `stored/peak` is a technology constant -- is the load-bearing assumption of the whole ROM verdict. A pass that reads only the drafter's region uses only that region's read ports and takes exactly as long as sweeping the entire array. Two placements are therefore priced side by side, and the second is an architectural proposal this study **has not costed in silicon area**.

The same rule is what makes a SEQUENTIAL draft step expensive here. A per-position operation that moves only a small table is nearly free on a global-bandwidth store and costs a full array sweep on this one, so a drafter with `gamma` sequential applications pays `gamma` sweeps for them. That term is charged in full below; on a bandwidth store the bytes it moves are not separately charged at all, because this repository's model configs carry no size for the table -- an omission whose size, on DeepSeek-V4-Pro-0813, is the externally published 132,382,720 B per draft token, 0.33% of the 39,666,603,980 B target pass.

| study | model | ctx | batch | class | design | tau* draft in ROM | tau* draft in KV store | KV placement feasible | why not |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 47.45 | 210.90 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2.33 | 36.72 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 47.45 | 210.90 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2.33 | 36.72 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 47.45 | 210.90 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 2.28 | 36.50 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 47.45 | 210.90 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2.59 | 36.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 47.45 | 210.90 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.78 | 36.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | 47.45 | 210.90 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.46 | 35.71 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 40.56 | 182.71 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4.71 | 34.63 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 32.31 | 92.38 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 8.75 | 30.25 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 28.07 | 46.71 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 48.52 | 956.91 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 29.10 | 48.69 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 23.17 | 23.17 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 51.13 | 383.10 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2.89 | 87.26 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 51.13 | 383.10 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2.89 | 87.26 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 51.13 | 383.10 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2.89 | 87.26 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 51.13 | 383.10 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3.14 | 86.76 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 51.13 | 383.10 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.39 | 85.81 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 51.13 | 383.10 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 4.28 | 82.97 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | 51.13 | 383.10 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4.77 | 77.16 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 34.76 | 178.98 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.96 | 60.84 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 37.27 | 192.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 49.07 | 1,699.45 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 29.14 | 61.40 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 18.04 | 19.38 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 29.54 | 16.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 1.75 | 1.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 29.54 | 16.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 1.75 | 1.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 29.54 | 16.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 1.75 | 1.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 29.54 | 16.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 1.75 | 1.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 29.54 | 16.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.83 | 2.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 27.53 | 16.15 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.18 | 2.36 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 27.53 | 16.15 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 34.03 | 44.21 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 21.25 | 16.68 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 34.03 | 44.21 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 23.17 | 18.11 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 28.65 | 35.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 12.40 | 10.66 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 10.72 | 10.25 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 32.22 | 20.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1.98 | 2.84 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 32.22 | 20.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1.98 | 2.84 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 32.22 | 20.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 1.98 | 2.81 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 32.22 | 20.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.98 | 2.81 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 32.22 | 20.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.09 | 2.92 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 32.22 | 20.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.54 | 3.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 29.62 | 19.99 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.35 | 4.10 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 21.86 | 18.16 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 6.68 | 7.22 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 20.01 | 16.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 26.64 | 47.07 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 18.62 | 17.04 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 18.37 | 23.63 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 29.54 | 16.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 1.75 | 1.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 29.54 | 16.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 1.75 | 1.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 29.54 | 16.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 1.75 | 1.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 29.54 | 16.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 1.75 | 1.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 29.54 | 16.53 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.83 | 2.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 27.53 | 16.15 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.18 | 2.36 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 27.53 | 16.15 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 34.03 | 44.21 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 21.25 | 16.68 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 34.03 | 44.21 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 23.17 | 18.11 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 28.65 | 35.62 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 12.40 | 10.66 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 10.72 | 10.25 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 32.22 | 20.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1.98 | 2.84 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 32.22 | 20.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1.98 | 2.84 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 32.22 | 20.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 1.98 | 2.81 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 32.22 | 20.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.98 | 2.81 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 32.22 | 20.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.09 | 2.92 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 32.22 | 20.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.54 | 3.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 29.62 | 19.99 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.35 | 4.10 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 21.86 | 18.16 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 6.68 | 7.22 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 20.01 | 16.48 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 26.64 | 47.09 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 18.62 | 17.04 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 18.38 | 23.64 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x63` | 3.24 | 2.80 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 1.98 | 1.59 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.19 | 15.86 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1.74 | 1.82 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.19 | 15.86 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1.74 | 1.82 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.19 | 15.86 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1.74 | 1.82 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.19 | 15.86 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1.74 | 1.82 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.19 | 15.86 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1.74 | 1.82 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.19 | 15.86 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 2.03 | 2.10 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349-romfill` | 17.45 | 16.59 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 3.84 | 1.49 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x349-romfill` | 18.03 | 17.14 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 2.32 | 1.53 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x349-romfill` | 17.26 | 17.16 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill` | 3.90 | 4.10 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 22.22 | 14.28 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 27.04 | 34.25 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 22.22 | 14.28 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 27.04 | 34.25 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 22.22 | 14.28 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 27.04 | 34.25 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 22.22 | 14.28 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 27.04 | 34.25 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 21.32 | 14.22 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 27.04 | 34.25 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 20.46 | 13.67 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 27.04 | 34.25 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 20.46 | 13.67 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 27.04 | 34.25 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.50 | 15.59 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 27.04 | 34.25 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 20.84 | 17.50 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 23.95 | 28.94 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 17.98 | 17.13 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 18.85 | 20.18 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 21.98 | 14.33 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 27.39 | 35.01 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 21.98 | 14.33 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 27.39 | 35.01 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 21.98 | 14.33 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 27.39 | 35.01 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 21.98 | 14.33 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 27.39 | 35.01 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 21.55 | 14.07 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 27.39 | 35.01 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 20.64 | 13.50 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | 27.39 | 35.01 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 20.64 | 13.50 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 27.74 | 35.46 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.60 | 15.50 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 27.74 | 35.46 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 21.14 | 17.53 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 24.46 | 29.82 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 18.06 | 17.14 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 10.27 | 9.61 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 32.88 | 15.73 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 2.35 | 2.07 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 32.88 | 15.73 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2.31 | 2.09 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 32.88 | 15.73 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2.31 | 2.09 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 32.88 | 15.73 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2.31 | 2.09 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 32.88 | 15.73 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.48 | 2.26 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 32.88 | 15.73 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 3.39 | 2.18 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 32.88 | 15.73 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 3.77 | 2.69 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 24.37 | 16.56 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 4.99 | 4.34 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 25.81 | 17.44 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 20.53 | 17.73 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 19.22 | 17.11 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 12.36 | 8.10 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 31.92 | 15.81 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2.22 | 2.00 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 31.92 | 15.81 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2.22 | 2.00 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 31.92 | 15.81 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2.22 | 2.00 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 31.92 | 15.81 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2.22 | 2.00 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 31.92 | 15.81 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.37 | 2.15 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 31.92 | 15.81 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.94 | 2.73 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | 31.92 | 15.81 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 4.26 | 3.60 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 26.08 | 16.45 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 5.94 | 5.04 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 28.03 | 17.55 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 11.28 | 10.71 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 19.79 | 17.14 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 14.95 | 14.75 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 31.88 | 15.79 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2.20 | 1.98 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 31.88 | 15.79 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2.20 | 1.98 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 31.88 | 15.79 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 2.20 | 1.98 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 31.88 | 15.79 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2.20 | 1.98 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 31.88 | 15.79 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.35 | 2.13 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 31.88 | 15.79 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.90 | 2.69 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | 31.88 | 15.79 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3.90 | 3.70 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 26.41 | 16.43 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 5.79 | 4.89 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 28.45 | 17.57 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 11.14 | 10.57 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 19.90 | 17.15 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 14.88 | 14.67 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x63-romfill` | 4.31 | 3.94 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 2.38 | 1.80 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 1.76 | 1.57 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 1.61 | 1.89 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 2.16 | 1.98 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 1.61 | 1.89 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 2.87 | 2.70 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 1.61 | 1.89 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 4.02 | 3.87 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 1.61 | 1.89 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 15.97 | 14.38 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 1.61 | 1.89 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 15.97 | 14.38 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 6.41 | 1.44 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 13.21 | 7.58 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 3.31 | 1.19 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 13.50 | 7.71 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1.71 | 1.07 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 8.86 | 7.40 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 11.51 | 1.74 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 24.00 | 17.27 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 1.60 | 1.80 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 24.00 | 17.27 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 1.63 | 2.07 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 24.00 | 17.27 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 1.63 | 2.07 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 24.00 | 17.27 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.63 | 2.07 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | 24.00 | 17.27 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.71 | 2.15 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 22.67 | 16.81 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.04 | 2.46 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 22.48 | 16.67 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.64 | 3.04 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 19.23 | 16.88 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 5.12 | 5.41 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 21.01 | 18.40 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 17.41 | 28.44 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 17.98 | 17.09 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 13.30 | 16.15 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 23.49 | 17.30 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 1.62 | 2.07 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 23.49 | 17.30 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 1.62 | 2.07 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 23.49 | 17.30 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 1.62 | 2.07 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 23.49 | 17.30 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.62 | 2.06 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 23.49 | 17.30 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.70 | 2.14 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 23.00 | 16.79 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.03 | 2.46 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 22.79 | 16.65 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 28.71 | 53.00 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 19.39 | 16.87 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 28.71 | 53.00 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 21.33 | 18.51 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 25.04 | 41.72 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 18.06 | 17.08 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 10.51 | 10.13 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x196` | 3.84 | 3.75 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 2.77 | 2.36 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 32.05 | 17.74 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3.33 | 2.40 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 32.05 | 17.74 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3.33 | 2.40 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 32.05 | 17.74 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3.33 | 2.40 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 32.05 | 17.74 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3.35 | 2.43 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 32.05 | 17.74 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3.47 | 2.66 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 32.05 | 17.74 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 3.63 | 2.97 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 23.27 | 17.32 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 4.01 | 3.70 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 24.21 | 17.97 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 16.70 | 10.53 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 18.82 | 17.25 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 7.45 | 5.90 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 33.51 | 17.87 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2.64 | 2.79 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 33.51 | 17.87 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2.64 | 2.79 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 33.51 | 17.87 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2.64 | 2.79 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 33.51 | 17.87 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2.64 | 2.78 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 33.51 | 17.87 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.84 | 2.97 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 33.51 | 17.87 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.59 | 3.71 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 33.51 | 17.87 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4.59 | 3.96 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 24.77 | 17.39 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 7.93 | 7.47 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 26.04 | 18.22 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 12.08 | 11.88 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 19.28 | 17.31 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 14.48 | 14.41 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 33.38 | 17.88 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2.62 | 2.77 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 33.38 | 17.88 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2.62 | 2.77 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 33.38 | 17.88 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2.62 | 2.77 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 33.38 | 17.88 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2.62 | 2.76 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 33.38 | 17.88 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.81 | 2.94 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 33.38 | 17.88 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3.53 | 3.66 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 33.38 | 17.88 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 4.51 | 3.87 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 25.05 | 17.41 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 8.07 | 7.60 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 26.39 | 18.27 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 12.75 | 12.53 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 19.37 | 17.32 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 15.63 | 15.56 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 7.32 | 7.32 | NO | the KV store has no room for it |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 1.41 | 1.51 | NO | the KV store has no room for it |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-tensor-x62-romfill` | 3.34 | 3.34 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 1.25 | 1.69 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-tensor-x62-romfill` | 4.87 | 4.87 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 1.25 | 1.69 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-tensor-x62` | 4.48 | 4.41 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 1.25 | 1.69 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8.54 | 8.93 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.27 | 1.68 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8.54 | 8.93 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.35 | 1.62 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8.54 | 8.93 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.45 | 1.56 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8.65 | 8.65 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 1.61 | 1.13 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8.70 | 8.70 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1.69 | 3.14 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 11.44 | 11.44 | yes | -- |
| `n5_vs_b200` | Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1.69 | 1.83 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x59` | 23.00 | 16.13 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | 27.44 | 19.44 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 23.33 | 14.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 1.55 | 1.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 23.33 | 14.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 1.55 | 1.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 23.33 | 14.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 1.55 | 1.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 23.33 | 14.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.63 | 1.73 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 19.63 | 14.52 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1.93 | 2.02 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 19.60 | 14.50 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2.43 | 2.51 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.05 | 16.01 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 3.28 | 2.19 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 19.58 | 17.33 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 8.70 | 10.07 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 11.13 | 9.72 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 7.11 | 7.46 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x184` | 2.62 | 2.45 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 2.81 | 2.04 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 31.48 | 16.26 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2.46 | 2.28 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 31.48 | 16.26 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2.46 | 2.28 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 31.48 | 16.26 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2.46 | 2.28 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 31.48 | 16.26 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2.46 | 2.28 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 31.48 | 16.26 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2.46 | 2.28 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 31.48 | 16.26 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2.66 | 2.49 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 23.07 | 16.70 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 4.84 | 2.03 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 23.94 | 17.29 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 3.31 | 2.28 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 18.75 | 17.07 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 20.83 | 3.52 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 8.70 | 8.70 | NO | the KV store has no room for it |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 1.54 | 1.62 | NO | the KV store has no room for it |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x87-romfill` | 2.68 | 2.71 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x8-romfill` | 1.19 | 1.31 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x87-romfill` | 3.68 | 3.68 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x8` | 1.39 | 1.32 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x138` | 3.24 | 3.10 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.15 | 2.06 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-tensor-x227` | 3.74 | 3.66 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.15 | 1.94 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 6.43 | 7.80 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.16 | 1.66 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 6.43 | 7.80 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1.93 | 1.41 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6.65 | 6.65 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1.28 | 1.13 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 6.71 | 6.71 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1.17 | 2.75 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 6.73 | 6.73 | yes | -- |
| `n6_vs_a100` | Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 2.01 | 1.44 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x83` | 24.67 | 17.30 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 1.78 | 1.68 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 24.76 | 17.14 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10-romfill` | 1.62 | 2.02 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 24.76 | 17.14 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10-romfill` | 1.62 | 2.02 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 24.76 | 17.14 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10-romfill` | 1.62 | 2.02 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 24.76 | 17.14 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.70 | 2.08 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x99` | 24.96 | 17.10 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 3.23 | 1.81 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 21.01 | 16.76 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2.95 | 1.82 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 18.54 | 16.92 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2.34 | 1.82 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x237` | 16.84 | 14.47 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 4.98 | 7.36 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 14.97 | 13.74 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 5.24 | 2.74 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x237` | 2.58 | 2.43 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 3.51 | 2.38 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 7.36 | 1.89 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 7.36 | 1.89 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 7.36 | 1.89 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 7.36 | 1.89 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 7.36 | 1.89 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 7.36 | 1.89 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 4.31 | 1.69 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 2.41 | 1.56 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 16.34 | 3.07 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 14.02 | 14.02 | NO | the KV store has no room for it |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 1.19 | 1.21 | NO | the KV store has no room for it |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-tensor-x62-romfill` | 2.25 | 2.25 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 1.13 | 1.25 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-tensor-x62-romfill` | 3.02 | 3.02 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 1.13 | 1.25 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x196-romfill` | 3.35 | 3.35 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 1.13 | 1.25 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x196-romfill` | 3.35 | 3.35 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.13 | 1.23 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x196-romfill` | 3.35 | 3.35 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.13 | 1.19 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3.35 | 3.35 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.12 | 1.14 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3.28 | 3.28 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 1.61 | 1.07 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3.26 | 3.26 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 1.11 | 1.46 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-q4p25-HBMKV-array-hybrid-x340-romfill` | 6.08 | 6.08 | yes | -- |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 1.11 | 1.12 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-hw-hybrid-x8-romfill` | 15.11 | 15.11 | NO | the KV store has no room for it |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 1.24 | 1.25 | NO | the KV store has no room for it |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-tensor-x87-romfill` | 1.88 | 1.88 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-tensor-x8-romfill` | 1.18 | 1.21 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-tensor-x87-romfill` | 2.36 | 2.36 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-tensor-x8` | 1.39 | 1.23 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-tensor-x138` | 2.74 | 2.49 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 1.11 | 1.35 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-tensor-x227` | 3.30 | 3.13 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.11 | 1.31 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 2.35 | 2.62 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1.09 | 1.22 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 2.35 | 2.62 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12` | 1.93 | 1.14 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 2.40 | 2.40 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12` | 1.28 | 1.05 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 2.38 | 2.38 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 1.06 | 1.47 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 2.38 | 2.38 | yes | -- |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12` | 2.01 | 1.12 | yes | -- |

## The capacity requirement, stated as a requirement

Every evaluated ROM design carries `weight_capacity_bytes == stored_weight_bytes` (the `romfill` variants reach 1.0039x), so no evaluated design has spare array for a drafter it does not already store. Re-solving the area split is `balanced_area_split`'s job and that file is not touched here, so what follows is a requirement -- this much extra array, or this much extra sweep on every pass -- and not a new design. **The speculative-optimal ROM design has not been computed, only bounded by the rungs that already exist.**

| study | model | design | drafter already in the checkpoint | extra stored bytes | extra array mm2 | as a fraction of the design | sweep inflation if area is held fixed |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | no | 850,275,640 | 90.7 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | no | 850,275,640 | 90.7 | 0.1% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | no | 850,275,640 | 116.6 | 0.1% | 1.0017x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | no | 850,275,640 | 90.7 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | no | 850,275,640 | 116.6 | 0.1% | 1.0028x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-tensor-x63` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | no | 686,957,240 | 73.2 | 0.1% | 1.0041x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | no | 686,957,240 | 73.2 | 0.0% | 1.0041x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-pipeline-x1-romfill` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x271` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x267` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-tensor-x63-romfill` | no | 686,957,240 | 94.2 | 0.2% | 1.0041x |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-array-hw-hybrid-x72` | no | 686,957,240 | 94.2 | 0.2% | 1.0041x |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | no | 686,957,240 | 94.2 | 0.2% | 1.0041x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | no | 686,957,240 | 94.2 | 0.2% | 1.0041x |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-tensor-x196` | no | 1,959,810,680 | 268.6 | 0.2% | 1.0022x |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | no | 1,929,464,320 | 205.7 | 1.6% | 1.1178x |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | no | 1,929,464,320 | 205.7 | 0.4% | 1.1178x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x59` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | no | 686,957,240 | 73.2 | 0.2% | 1.0041x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-tensor-x184` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | no | 1,959,810,680 | 208.9 | 0.1% | 1.0022x |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | no | 1,929,464,320 | 264.5 | 2.0% | 1.1178x |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | no | 1,929,464,320 | 264.5 | 0.6% | 1.1178x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x83` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | no | 686,957,240 | 94.2 | 0.1% | 1.0041x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-tensor-x237` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | no | 1,959,810,680 | 268.6 | 0.1% | 1.0022x |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | no | 512,513,960 | 54.6 | 1.7% | 1.1178x |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | no | 512,513,960 | 54.6 | 0.1% | 1.1178x |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-array-hw-hybrid-x8-romfill` | no | 512,513,960 | 70.3 | 1.1% | 1.1178x |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | no | 512,513,960 | 70.3 | 0.2% | 1.1178x |

## Which design the published rule chooses once a block is verified

A re-ranking of designs the study already evaluated, under the study's own selection rule (non-dominated on per-user tokens/s and tokens/s per 1,000 mm2, then a marginal-return walk from the smallest feasible machine). `tau` is a common factor on both axes, so the choice is independent of the acceptance rate. The rule's reproduction of the published autoregressive recommendation is reported first, because a re-ranking whose baseline does not reproduce is not evidence of anything.

| study | model | published recommendation | rule reproduces it | under speculation, draft in ROM | draft in KV store | moves |
| --- | --- | --- | --- | --- | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-SRAMKV-array-hw-tensor-x88` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x123` | `ROM-N5-native-HBMKV-array-hw-tensor-x127` | yes |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-array-hw-tensor-x113` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x170` | `ROM-N6-native-HBMKV-array-hw-tensor-x143` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-tensor-x63` | yes | `ROM-N5-native-HBMKV-array-hw-tensor-x78` | `ROM-N5-native-HBMKV-array-hw-tensor-x78` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-tensor-x74` | yes | `ROM-N6-native-HBMKV-array-hw-tensor-x96` | `ROM-N6-native-HBMKV-array-hw-tensor-x96` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-SRAMKV-array-hw-tensor-x57` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x64` | `ROM-N5-native-HBMKV-array-hw-tensor-x78` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-SRAMKV-array-hw-tensor-x68` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x85` | `ROM-N6-native-HBMKV-array-hw-tensor-x96` | yes |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-tensor-x36` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x57` | `ROM-N5-native-HBMKV-array-hw-tensor-x279` | yes |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-tensor-x34` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | `ROM-N5-native-HBMKV-array-hw-tensor-x44` | yes |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-tensor-x34` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x36` | `ROM-N5-native-HBMKV-array-hw-tensor-x44` | yes |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-tensor-x154` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x180` | `ROM-N5-native-HBMKV-array-hw-tensor-x193` | yes |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-tensor-x151` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x179` | `ROM-N5-native-HBMKV-array-hw-tensor-x193` | yes |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-tensor-x160` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x179` | `ROM-N5-native-HBMKV-array-hw-tensor-x193` | yes |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-tensor-x50` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x63-romfill` | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | yes |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x53` | `ROM-N6-native-HBMKV-array-hw-tensor-x57` | yes |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x51` | `ROM-N6-native-HBMKV-array-hw-tensor-x57` | yes |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-tensor-x196` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x232` | `ROM-N6-native-HBMKV-array-hw-tensor-x248` | yes |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-tensor-x195` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x230` | `ROM-N6-native-HBMKV-array-hw-tensor-x248` | yes |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-tensor-x194` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x230` | `ROM-N6-native-HBMKV-array-hw-tensor-x248` | yes |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x8` | `ROM-N5-native-HBMKV-array-hw-tensor-x49` | yes |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x44-romfill` | `ROM-N5-native-HBMKV-array-hw-tensor-x56` | yes |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-tensor-x166-romfill` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x184` | `ROM-N5-native-HBMKV-array-hw-tensor-x399` | yes |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x7-romfill` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x12` | `ROM-N6-native-HBMKV-array-hw-tensor-x69` | yes |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x57` | `ROM-N6-native-HBMKV-array-hw-tensor-x79` | yes |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-tensor-x209` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x237` | `ROM-N6-native-HBMKV-wafer-tensor-x66` | yes |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | yes | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4` | `ROM-N5-q4p25-HBMKV-array-hw-tensor-x49-romfill` | yes |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | yes | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x4` | `ROM-N6-q4p25-HBMKV-array-hw-tensor-x69-romfill` | yes |

**The rule reproduces the published autoregressive recommendation on 26 of 26 model-and-study rows.** Of the 26 rows where it reproduces and the drafter applies, verifying a block moves the chosen rung on 26. Where it moves, it moves toward machines with compute headroom for a block, which is exactly what the arithmetic predicts: a verification pass raises arithmetic intensity by the block size, and a machine sized with just enough compute for one token per sweep has no room for it. **This is a re-ranking of rungs that already exist. The speculative-optimal design has not been computed: that would need the area split re-solved, which is `balanced_area_split`'s job and not this layer's.**

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

_Eight packages is an evaluated rung for this model and the rows below include it._

**Every row below is evaluated at gamma = 8, the block size Xiaomi's own deployment uses, so the verification pass carries 9 positions. The acceptance lengths applied to it are the ones Xiaomi publishes at that same block size. This is NOT this profile's served block size, and the cycle and the acceptance length are never taken from different configurations.**

GPU cluster sizes this study evaluates for DeepSeek-V4-Pro-0813: 8, 14, 18, 29, 32, 38, 39, 40, 41, 42, 43, 44, 46, 56, 58, 63, 70, 71, 76, 77, 78, 82, 83, 84, 85, 86, 87, 88, 91, 92, 93, 94, 95, 97, 98, 100, 103, 110, 111, 112, 113, 114, 116, 117, 118, 121, 125, 126, 133, 134, 135, 136, 138, 144, 146, 147, 150, 152, 153, 157, 166, 168, 173, 174, 175, 177, 189, 190, 191, 192, 193, 203, 205, 206, 208, 218, 221, 222, 224, 227, 228, 229, 231, 233, 234, 245, 255, 261, 262, 272, 274, 280, 282, 283, 289, 293, 298, 308, 322, 323, 324, 335, 336, 338, 347, 357, 358, 363, 364, 365, 369, 370, 371, 373, 386, 387, 391, 392, 448, 504, 574, 672, 783, 1358, 3694 packages.

DeepSeek-V4-Pro-0813 is 1.6 trillion total parameters with 49 billion active; the model Xiaomi describes is 1 trillion total, and its active count is ASSUMED at 42 billion -- the blog states no active parameter count, that figure comes from secondary reporting, and it is graded `assumed` here and used for nothing but this sentence. They are the same class and they are not the same model.

| design | packages | batch | ctx | block (gamma) | positions verified | AR per-user tok/s | AR aggregate tok/s | resident sessions | binds on | tau* | coding tau 6.30 | maths tau 5.56 | agent tau 4.29 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| `b200_sxm-x8-expert` | 8 | 1 | 8,192 | 8 | 9 | 608.67 | 609 | 1 | `weight_read` | 2.68 | 1,431.43 | 1,263.29 | 974.73 |
| `b200_sxm-x8-nvl72-expert` | 8 | 1 | 8,192 | 8 | 9 | 608.67 | 609 | 1 | `weight_read` | 2.68 | 1,431.43 | 1,263.29 | 974.73 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 1 | 8,192 | 8 | 9 | 924.40 | 924 | 1 | `weight_read` | 2.69 | 2,167.05 | 1,912.51 | 1,475.66 |
| `b200_sxm-x8-pipeline` | 8 | 1 | 8,192 | 8 | 9 | 155.32 | 1,243 | 8 | `thermal` | 3.52 | 278.22 | 245.54 | 189.45 |
| `b200_sxm-x8-tensor` | 8 | 1 | 8,192 | 8 | 9 | 924.40 | 924 | 1 | `weight_read` | 2.69 | 2,167.05 | 1,912.51 | 1,475.66 |
| `b200_sxm-x8-expert` | 8 | 2 | 8,192 | 8 | 9 | 486.38 | 973 | 2 | `weight_read` | 3.26 | 941.18 | 830.63 | 640.90 |
| `b200_sxm-x8-nvl72-expert` | 8 | 2 | 8,192 | 8 | 9 | 486.38 | 973 | 2 | `weight_read` | 3.26 | 941.18 | 830.63 | 640.90 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 2 | 8,192 | 8 | 9 | 750.81 | 1,502 | 2 | `weight_read` | 3.57 | 1,326.20 | 1,170.43 | 903.08 |
| `b200_sxm-x8-pipeline` | 8 | 2 | 8,192 | 8 | 9 | 155.32 | 1,243 | 8 | `thermal` | 3.52 | 278.22 | 245.54 | 189.45 |
| `b200_sxm-x8-tensor` | 8 | 2 | 8,192 | 8 | 9 | 750.81 | 1,502 | 2 | `weight_read` | 3.57 | 1,326.20 | 1,170.43 | 903.08 |
| `b200_sxm-x8-expert` | 8 | 4 | 8,192 | 8 | 9 | 361.15 | 1,445 | 4 | `weight_read` | 3.71 | 613.78 | 541.68 | 417.95 |
| `b200_sxm-x8-nvl72-expert` | 8 | 4 | 8,192 | 8 | 9 | 361.15 | 1,445 | 4 | `weight_read` | 3.71 | 613.78 | 541.68 | 417.95 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 4 | 8,192 | 8 | 9 | 549.23 | 2,197 | 4 | `weight_read` | 4.32 | 800.78 | 706.72 | 545.29 |
| `b200_sxm-x8-pipeline` | 8 | 4 | 8,192 | 8 | 9 | 155.32 | 1,243 | 8 | `thermal` | 3.52 | 278.22 | 245.54 | 189.45 |
| `b200_sxm-x8-tensor` | 8 | 4 | 8,192 | 8 | 9 | 549.23 | 2,197 | 4 | `weight_read` | 4.32 | 800.78 | 706.72 | 545.29 |
| `b200_sxm-x8-expert` | 8 | 8 | 8,192 | 8 | 9 | 249.51 | 1,996 | 8 | `weight_read` | 3.72 | 422.16 | 372.58 | 287.47 |
| `b200_sxm-x8-nvl72-expert` | 8 | 8 | 8,192 | 8 | 9 | 249.51 | 1,996 | 8 | `weight_read` | 3.72 | 422.16 | 372.58 | 287.47 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 8 | 8,192 | 8 | 9 | 363.03 | 2,904 | 8 | `weight_read` | 4.36 | 524.98 | 463.31 | 357.48 |
| `b200_sxm-x8-pipeline` | 8 | 8 | 8,192 | 8 | 9 | 155.32 | 1,243 | 8 | `thermal` | 3.52 | 278.22 | 245.54 | 189.45 |
| `b200_sxm-x8-tensor` | 8 | 8 | 8,192 | 8 | 9 | 363.03 | 2,904 | 8 | `weight_read` | 4.36 | 524.98 | 463.31 | 357.48 |
| `b200_sxm-x8-expert` | 8 | 16 | 8,192 | 8 | 9 | 163.49 | 2,616 | 16 | `weight_read` | 3.15 | 326.76 | 288.38 | 222.51 |
| `b200_sxm-x8-nvl72-expert` | 8 | 16 | 8,192 | 8 | 9 | 163.49 | 2,616 | 16 | `weight_read` | 3.15 | 326.76 | 288.38 | 222.51 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 16 | 8,192 | 8 | 9 | 224.26 | 3,588 | 16 | `weight_read` | 3.53 | 400.45 | 353.41 | 272.69 |
| `b200_sxm-x8-pipeline` | 8 | 16 | 8,192 | 8 | 9 | 117.59 | 1,881 | 16 | `thermal` | 4.47 | 165.78 | 146.30 | 112.89 |
| `b200_sxm-x8-tensor` | 8 | 16 | 8,192 | 8 | 9 | 224.26 | 3,588 | 16 | `weight_read` | 3.53 | 400.45 | 353.41 | 272.69 |
| `b200_sxm-x8-expert` | 8 | 32 | 8,192 | 8 | 9 | 105.64 | 3,381 | 32 | `weight_read` | 2.32 | 287.18 | 253.45 | 195.55 |
| `b200_sxm-x8-nvl72-expert` | 8 | 32 | 8,192 | 8 | 9 | 105.64 | 3,381 | 32 | `weight_read` | 2.32 | 287.18 | 253.45 | 195.55 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 32 | 8,192 | 8 | 9 | 136.92 | 4,381 | 32 | `weight_read` | 2.39 | 360.38 | 318.05 | 245.40 |
| `b200_sxm-x8-pipeline` | 8 | 32 | 8,192 | 8 | 9 | 79.75 | 2,552 | 32 | `thermal` | 5.02 | 100.10 | 88.34 | 68.16 |
| `b200_sxm-x8-tensor` | 8 | 32 | 8,192 | 8 | 9 | 136.92 | 4,381 | 32 | `weight_read` | 2.39 | 360.38 | 318.05 | 245.40 |
| `b200_sxm-x8-expert` | 8 | 64 | 8,192 | 8 | 9 | 71.35 | 4,566 | 64 | `weight_read` | 1.73 | 260.31 | 229.74 | 177.26 |
| `b200_sxm-x8-nvl72-expert` | 8 | 64 | 8,192 | 8 | 9 | 71.35 | 4,566 | 64 | `weight_read` | 1.73 | 260.31 | 229.74 | 177.26 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 64 | 8,192 | 8 | 9 | 88.54 | 5,666 | 64 | `weight_read` | 1.72 | 324.12 | 286.05 | 220.71 |
| `b200_sxm-x8-pipeline` | 8 | 64 | 8,192 | 8 | 9 | 49.40 | 3,161 | 64 | `thermal` | 4.74 | 65.62 | 57.91 | 44.69 |
| `b200_sxm-x8-tensor` | 8 | 64 | 8,192 | 8 | 9 | 88.54 | 5,666 | 64 | `weight_read` | 1.72 | 324.12 | 286.05 | 220.71 |
| `b200_sxm-x8-expert` | 8 | 256 | 8,192 | 8 | 9 | 46.33 | 11,859 | 256 | `weight_read` | 1.70 | 171.75 | 151.58 | 116.96 |
| `b200_sxm-x8-nvl72-expert` | 8 | 256 | 8,192 | 8 | 9 | 46.33 | 11,859 | 256 | `weight_read` | 1.70 | 171.75 | 151.58 | 116.96 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 256 | 8,192 | 8 | 9 | 55.58 | 14,228 | 256 | `weight_read` | 1.65 | 211.66 | 186.80 | 144.13 |
| `b200_sxm-x8-pipeline` | 8 | 256 | 8,192 | 8 | 9 | 17.35 | 4,442 | 256 | `thermal` | 2.43 | 45.05 | 39.76 | 30.67 |
| `b200_sxm-x8-tensor` | 8 | 256 | 8,192 | 8 | 9 | 55.58 | 14,228 | 256 | `weight_read` | 1.65 | 211.66 | 186.80 | 144.13 |
| `b200_sxm-x8-expert` | 8 | 1024 | 8,192 | 8 | 9 | 36.00 | 36,860 | 1,024 | `weight_read` | 4.42 | 51.27 | 45.24 | 34.91 |
| `b200_sxm-x8-nvl72-expert` | 8 | 1024 | 8,192 | 8 | 9 | 36.00 | 36,860 | 1,024 | `weight_read` | 4.42 | 51.27 | 45.24 | 34.91 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 1024 | 8,192 | 8 | 9 | 43.40 | 44,443 | 1,024 | `weight_read` | 4.70 | 58.23 | 51.39 | 39.65 |
| `b200_sxm-x8-pipeline` | 8 | 1024 | 8,192 | 8 | 9 | 8.19 | 8,383 | 1,024 | `thermal` | 1.24 | 41.68 | 36.78 | 28.38 |
| `b200_sxm-x8-tensor` | 8 | 1024 | 8,192 | 8 | 9 | 43.40 | 44,443 | 1,024 | `weight_read` | 4.70 | 58.23 | 51.39 | 39.65 |
| `b200_sxm-x8-expert` | 8 | 4096 | 8,192 | 8 | 9 | 19.03 | 77,963 | 4,096 | `link_latency` | 9.33 | 12.86 | 11.35 | 8.75 |
| `b200_sxm-x8-nvl72-expert` | 8 | 4096 | 8,192 | 8 | 9 | 19.03 | 77,963 | 4,096 | `link_latency` | 9.33 | 12.86 | 11.35 | 8.75 |
| `b200_sxm-x8-nvl72-tensor` | 8 | 4096 | 8,192 | 8 | 9 | 21.54 | 88,235 | 4,096 | `compute` | 9.30 | 14.59 | 12.88 | 9.94 |
| `b200_sxm-x8-pipeline` | 8 | 4096 | 8,192 | 8 | 9 | 6.79 | 27,794 | 4,096 | `thermal` | 1.55 | 27.56 | 24.33 | 18.77 |
| `b200_sxm-x8-tensor` | 8 | 4096 | 8,192 | 8 | 9 | 21.54 | 88,235 | 4,096 | `compute` | 9.30 | 14.59 | 12.88 | 9.94 |

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

