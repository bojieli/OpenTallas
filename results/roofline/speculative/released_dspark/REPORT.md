# Speculative decoding on the area-constrained roofline: released_dspark

> DeepSeek-V4's own speculative module, as shipped. Every figure below is derived from the roofline artifacts
> this repository has already published, by re-assembling each point's own five
> critical-path terms for a speculative cycle. Nothing here re-runs the machine
> model, and nothing here invents an acceptance rate.

## What this layer says

1. **Every term the speculative arithmetic needs is already in the published artifact, exactly.** 181,238 feasible points across 52 studies were rebuilt from their own five critical-path terms and every one reproduced its published step time to 1e-9 relative. Nothing here re-ran the machine model, and the layer is additive by construction rather than by promise.
2. **The headline is a break-even, not a speedup.** `tau* = T_cycle / step_time_s`, and `tau <= gamma+1` always. Of 242,840 (point, draft-placement) pairs where this profile's drafter applies, 85,817 (35.3%) cannot be sped up by speculation at ANY acceptance rate, at any block size on the ladder, even charging the drafter no KV traffic at all.
3. **The ROM-versus-GPU ratio under speculation carries no acceptance rate.** It is `T_cycle(GPU) / T_cycle(ROM)`: `tau` is a property of the model and its drafter, not of the machine, so it is identical on both sides and cancels. Every movement this report shows is a machine effect and nothing else, which is why it can be published without inventing an acceptance rate.
4. **The ratio moves, and it mostly compresses.** Across 775 model-context-batch-class rows, 775 move the ROM-versus-GPU per-user ratio DOWN under speculation and 0 move it UP, spanning 0.017x to 1.000x. The ROM advantage compresses on most operating points.
5. **At batch 1 the two extremes are opposite in sign, and they are the result.** DeepSeek-V4.1-Flash-engram-hbm on `wafer` silicon goes from 5.84x to 0.11x -- a 0.019x movement -- while DeepSeek-V4-Pro-0813 on `array` silicon goes from 9.35x to 2.21x, a 0.236x movement. A layer that multiplied both sides by `tau` would have reported neither.
6. **A moving ratio is not a win for either side, and the report says so on every table.** At the most favourable sourced acceptance (5.00) speculation is worth having on 11 of 777 ROM class rows and 757 of 777 GPU rows; everywhere else the design runs SLOWER with a drafter than without one. Where both sides lose, a rising ratio means only that the comparator lost more.
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
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 528 | 0 | 1.15 | 1.47 | 5.88 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 963 | 371 | 1.16 | 7.00 | 65.78 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 58 | 0 | 1.17 | 2.41 | 4.59 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 371 | 2 | 1.91 | 2.67 | 22.66 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 798 | 218 | 5.01 | 7.47 | 20.33 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 48 | 48 | 17.28 | 18.43 | 20.28 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 648 | 88 | 1.87 | 4.83 | 13.04 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 910 | 105 | 1.28 | 2.86 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 408 | 94 | 2.01 | 5.98 | 11.91 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 798 | 798 | 8.18 | 55.79 | 181.94 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 48 | 48 | 13.97 | 54.44 | 64.24 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 648 | 393 | 2.83 | 8.26 | 167.56 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 910 | 318 | 1.35 | 6.47 | 67.48 |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 408 | 372 | 6.88 | 17.29 | 276.41 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 1 | 1 | 8.17 | 8.17 | 8.17 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 738 | 238 | 1.32 | 4.87 | 65.77 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 541 | 1 | 1.35 | 2.72 | 22.17 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 739 | 337 | 5.13 | 8.29 | 22.10 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 47 | 42 | 4.48 | 18.31 | 20.32 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 528 | 74 | 1.93 | 4.97 | 15.08 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 833 | 94 | 1.29 | 3.06 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 325 | 120 | 2.08 | 7.28 | 18.08 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 739 | 739 | 8.16 | 52.08 | 208.58 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 47 | 43 | 5.68 | 54.87 | 124.96 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 528 | 301 | 2.97 | 8.19 | 151.00 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 833 | 224 | 1.38 | 6.09 | 40.76 |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 325 | 294 | 5.00 | 16.22 | 274.95 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 565 | 0 | 1.15 | 1.45 | 5.79 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,036 | 374 | 1.16 | 6.76 | 65.78 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 57 | 0 | 1.19 | 2.46 | 4.37 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 384 | 0 | 2.02 | 2.65 | 6.89 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 747 | 150 | 5.09 | 7.47 | 9.72 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 124 | 36 | 3.19 | 7.71 | 9.39 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 600 | 71 | 1.95 | 4.10 | 8.29 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 919 | 105 | 1.26 | 2.70 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 362 | 66 | 2.07 | 6.01 | 9.14 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 747 | 747 | 8.18 | 44.48 | 185.31 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 124 | 122 | 4.36 | 69.54 | 187.81 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 600 | 342 | 2.85 | 8.22 | 111.56 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 919 | 316 | 1.35 | 6.60 | 65.96 |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 362 | 323 | 5.67 | 16.14 | 263.06 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 2 | 0 | 6.71 | 6.72 | 6.72 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 795 | 245 | 1.32 | 4.55 | 65.72 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 554 | 0 | 1.64 | 2.67 | 12.16 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 678 | 215 | 4.86 | 8.15 | 10.50 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 125 | 8 | 2.56 | 7.45 | 10.27 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 452 | 57 | 1.93 | 4.57 | 8.27 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 858 | 100 | 1.28 | 2.89 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 243 | 71 | 2.14 | 7.60 | 10.65 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 678 | 678 | 8.18 | 42.65 | 204.82 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 125 | 111 | 2.70 | 55.02 | 183.30 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 452 | 225 | 2.97 | 8.18 | 97.79 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 858 | 250 | 1.36 | 6.53 | 39.23 |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 243 | 223 | 4.97 | 16.10 | 222.03 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 578 | 0 | 1.15 | 1.47 | 5.89 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 1,054 | 411 | 1.16 | 7.06 | 65.78 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `thermal` | 65 | 0 | 1.17 | 2.37 | 4.62 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 413 | 4 | 1.72 | 2.67 | 26.39 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 796 | 226 | 4.83 | 7.49 | 84.45 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 62 | 62 | 38.55 | 88.08 | 92.53 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 651 | 118 | 1.86 | 4.95 | 31.85 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 927 | 141 | 1.28 | 3.22 | 43.05 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 444 | 133 | 2.01 | 6.01 | 62.60 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 796 | 796 | 8.18 | 54.68 | 189.06 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 62 | 51 | 4.59 | 17.53 | 21.90 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 651 | 375 | 2.84 | 8.21 | 123.29 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 927 | 283 | 1.35 | 6.11 | 67.90 |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 444 | 405 | 6.88 | 16.42 | 280.64 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `compute` | 2 | 2 | 8.14 | 8.31 | 8.31 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `link_latency` | 682 | 217 | 1.32 | 4.78 | 65.74 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `gpu` | `in_hbm` | `weight_read` | 506 | 1 | 1.36 | 2.72 | 21.63 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `compute` | 781 | 357 | 5.28 | 8.26 | 90.47 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `kv_read` | 50 | 50 | 38.68 | 89.79 | 92.78 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 547 | 107 | 1.94 | 6.42 | 33.61 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `link_latency` | 849 | 132 | 1.29 | 3.33 | 37.11 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_kv_store` | `weight_read` | 313 | 118 | 2.08 | 7.31 | 53.15 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `compute` | 781 | 781 | 8.16 | 53.75 | 210.48 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `kv_read` | 50 | 48 | 5.97 | 17.88 | 22.76 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 547 | 300 | 3.00 | 8.18 | 123.36 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `link_latency` | 849 | 217 | 1.38 | 6.04 | 40.89 |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `rom` | `in_rom` | `weight_read` | 313 | 293 | 6.79 | 16.22 | 280.55 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `layer_fixed_latency` | 698 | 0 | 1.15 | 1.46 | 6.63 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,376 | 517 | 1.16 | 6.79 | 65.79 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 74 | 0 | 1.17 | 2.64 | 4.59 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 512 | 4 | 1.91 | 2.67 | 22.66 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 783 | 173 | 4.87 | 7.36 | 15.54 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 5 | 2 | 5.85 | 7.60 | 11.96 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 768 | 142 | 1.31 | 4.69 | 13.20 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 981 | 114 | 1.24 | 2.48 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 556 | 100 | 1.11 | 5.22 | 14.21 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 783 | 783 | 8.16 | 28.22 | 130.25 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 5 | 2 | 7.30 | 8.60 | 26.57 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 768 | 456 | 3.25 | 8.25 | 113.01 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 981 | 274 | 1.30 | 5.82 | 40.97 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 556 | 514 | 5.22 | 20.71 | 180.29 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 3 | 2 | 7.62 | 8.17 | 8.18 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 962 | 302 | 1.32 | 4.63 | 65.77 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 675 | 2 | 1.38 | 2.72 | 22.17 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 715 | 210 | 3.90 | 8.16 | 9.67 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 106 | 97 | 3.99 | 21.15 | 21.38 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 651 | 79 | 1.42 | 4.81 | 15.05 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 984 | 114 | 1.24 | 2.63 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 490 | 139 | 1.11 | 6.70 | 19.41 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 715 | 713 | 7.34 | 40.36 | 150.67 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 106 | 103 | 4.03 | 94.38 | 108.61 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 651 | 384 | 2.96 | 8.24 | 84.48 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 984 | 224 | 1.30 | 5.21 | 38.93 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 490 | 450 | 5.49 | 20.50 | 180.29 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `layer_fixed_latency` | 706 | 0 | 1.15 | 1.45 | 6.50 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,460 | 522 | 1.16 | 6.51 | 65.78 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 72 | 0 | 1.19 | 2.74 | 4.37 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 510 | 0 | 1.99 | 2.65 | 7.21 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 754 | 154 | 4.66 | 7.40 | 8.33 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 69 | 0 | 2.99 | 7.68 | 8.16 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 692 | 74 | 1.43 | 4.51 | 8.29 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 944 | 111 | 1.25 | 2.61 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 445 | 64 | 1.28 | 5.14 | 9.58 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 754 | 754 | 8.15 | 22.89 | 128.43 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 69 | 61 | 3.32 | 48.56 | 81.23 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 692 | 389 | 2.86 | 8.21 | 103.82 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 944 | 259 | 1.30 | 5.95 | 39.81 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 445 | 415 | 5.50 | 20.04 | 175.85 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 1 | 0 | 6.71 | 6.71 | 6.71 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,063 | 324 | 1.32 | 4.33 | 65.71 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 723 | 0 | 1.52 | 2.70 | 12.27 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 721 | 211 | 5.17 | 8.14 | 9.19 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `kv_read` | 92 | 0 | 2.76 | 6.47 | 7.87 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 538 | 63 | 1.66 | 4.51 | 8.28 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 969 | 111 | 1.25 | 2.68 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 380 | 84 | 1.61 | 6.65 | 11.96 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 721 | 719 | 7.27 | 33.77 | 143.57 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `kv_read` | 92 | 66 | 2.29 | 33.65 | 126.86 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 538 | 275 | 2.72 | 8.17 | 81.40 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 969 | 227 | 1.30 | 5.49 | 38.80 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 380 | 357 | 5.25 | 18.49 | 176.17 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `layer_fixed_latency` | 622 | 0 | 1.15 | 1.45 | 6.07 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 1,314 | 490 | 1.16 | 6.64 | 65.79 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `thermal` | 67 | 0 | 1.17 | 2.66 | 4.62 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 487 | 6 | 1.72 | 2.67 | 26.39 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 745 | 184 | 4.70 | 7.38 | 15.87 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 751 | 137 | 1.29 | 5.31 | 14.19 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 950 | 108 | 1.24 | 2.47 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 596 | 113 | 1.06 | 5.07 | 16.32 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 745 | 745 | 8.16 | 30.27 | 134.22 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 751 | 446 | 3.24 | 8.24 | 102.27 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 950 | 271 | 1.30 | 5.79 | 41.29 |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 596 | 549 | 5.51 | 20.85 | 181.46 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `compute` | 3 | 3 | 8.14 | 8.18 | 8.31 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `link_latency` | 977 | 305 | 1.32 | 4.54 | 65.75 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `gpu` | `in_hbm` | `weight_read` | 690 | 2 | 1.34 | 2.75 | 21.63 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `compute` | 800 | 301 | 3.69 | 8.22 | 25.44 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `layer_fixed_latency` | 654 | 88 | 1.36 | 5.60 | 17.21 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `link_latency` | 990 | 114 | 1.24 | 2.60 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_kv_store` | `weight_read` | 534 | 153 | 1.06 | 6.52 | 22.75 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `compute` | 800 | 798 | 7.33 | 44.67 | 146.01 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `layer_fixed_latency` | 654 | 393 | 2.97 | 8.24 | 87.52 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `link_latency` | 990 | 234 | 1.30 | 5.28 | 39.04 |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `rom` | `in_rom` | `weight_read` | 534 | 493 | 5.51 | 20.62 | 181.46 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `layer_fixed_latency` | 546 | 0 | 1.16 | 1.52 | 6.63 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 883 | 361 | 1.16 | 7.47 | 65.79 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `thermal` | 63 | 0 | 1.17 | 2.25 | 4.49 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 388 | 5 | 1.87 | 2.67 | 23.43 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 785 | 215 | 4.87 | 7.56 | 17.71 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 47 | 46 | 5.14 | 17.48 | 19.57 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `layer_fixed_latency` | 799 | 144 | 1.84 | 4.73 | 13.20 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 949 | 114 | 1.28 | 2.72 | 8.56 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 496 | 81 | 1.98 | 5.58 | 14.21 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 785 | 785 | 8.16 | 26.82 | 104.93 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 47 | 46 | 6.67 | 44.48 | 64.57 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `layer_fixed_latency` | 799 | 433 | 3.13 | 8.18 | 113.02 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 949 | 257 | 1.32 | 5.83 | 40.97 |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 496 | 468 | 5.61 | 20.71 | 179.30 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `compute` | 6 | 4 | 7.61 | 8.18 | 8.19 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `link_latency` | 802 | 281 | 1.32 | 5.40 | 65.77 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `gpu` | `in_hbm` | `weight_read` | 672 | 3 | 1.38 | 2.68 | 16.71 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `compute` | 684 | 222 | 5.23 | 8.19 | 19.96 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `kv_read` | 150 | 141 | 3.99 | 18.66 | 21.39 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `layer_fixed_latency` | 662 | 79 | 2.01 | 4.86 | 15.05 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `link_latency` | 961 | 114 | 1.29 | 2.68 | 8.58 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_kv_store` | `weight_read` | 467 | 129 | 2.00 | 6.74 | 19.41 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `compute` | 684 | 682 | 7.34 | 38.27 | 121.57 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `kv_read` | 150 | 147 | 4.03 | 56.27 | 108.63 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `layer_fixed_latency` | 662 | 384 | 2.96 | 8.22 | 84.48 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `link_latency` | 961 | 215 | 1.34 | 5.15 | 38.67 |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `rom` | `in_rom` | `weight_read` | 467 | 430 | 5.82 | 19.79 | 178.25 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 115 | 0 | 1.21 | 1.47 | 16.65 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 396 | 0 | 1.11 | 1.37 | 8.01 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 604 | 162 | 1.12 | 4.63 | 65.38 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 25 | 0 | 1.29 | 1.62 | 2.34 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 209 | 0 | 1.41 | 2.27 | 7.75 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 8 | 0 | 6.92 | 7.35 | 7.37 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 196 | 0 | 1.05 | 2.66 | 6.90 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 289 | 0 | 1.82 | 4.76 | 17.46 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 516 | 31 | 1.24 | 2.03 | 10.10 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `thermal` | 303 | 0 | 1.52 | 1.96 | 3.64 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 120 | 12 | 2.29 | 6.48 | 8.07 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 8 | 8 | 22.40 | 23.91 | 24.72 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 196 | 102 | 1.16 | 8.57 | 51.04 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 289 | 83 | 2.70 | 7.10 | 36.15 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 516 | 98 | 1.26 | 4.29 | 21.91 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `thermal` | 303 | 223 | 2.35 | 13.66 | 67.21 |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 120 | 106 | 5.34 | 12.94 | 22.96 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 47 | 0 | 1.25 | 1.39 | 4.38 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 94 | 0 | 1.30 | 1.50 | 1.64 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 511 | 111 | 1.22 | 3.96 | 65.23 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 359 | 0 | 1.39 | 1.84 | 16.20 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 26 | 0 | 6.84 | 7.48 | 7.85 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 521 | 0 | 1.06 | 2.19 | 7.11 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 244 | 0 | 1.80 | 4.87 | 15.37 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 525 | 31 | 1.24 | 1.92 | 9.43 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 124 | 14 | 1.94 | 5.76 | 8.07 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 26 | 26 | 14.24 | 23.29 | 27.23 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 521 | 251 | 1.10 | 6.98 | 41.63 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 244 | 50 | 2.54 | 6.00 | 26.84 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 525 | 92 | 1.26 | 3.67 | 13.02 |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 124 | 105 | 5.13 | 13.07 | 22.97 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 396 | 5 | 1.19 | 1.93 | 20.66 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 320 | 0 | 1.10 | 1.27 | 6.51 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 406 | 82 | 1.09 | 2.92 | 64.89 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 34 | 0 | 1.32 | 1.78 | 2.06 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 3 | 0 | 7.80 | 7.80 | 7.81 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 79 | 0 | 1.04 | 1.06 | 7.20 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 179 | 0 | 2.07 | 5.42 | 17.21 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 168 | 0 | 1.11 | 1.71 | 4.35 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 49 | 10 | 1.92 | 5.66 | 8.01 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 3 | 3 | 16.66 | 16.72 | 16.75 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 79 | 34 | 1.11 | 3.80 | 51.29 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 179 | 77 | 3.21 | 6.93 | 30.61 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 168 | 19 | 1.22 | 2.20 | 19.19 |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 49 | 41 | 7.50 | 14.77 | 22.99 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 364 | 0 | 1.12 | 1.44 | 19.05 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 454 | 49 | 1.10 | 1.87 | 61.98 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 37 | 0 | 1.72 | 3.08 | 6.53 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 40 | 2 | 4.04 | 7.96 | 8.09 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 81 | 0 | 1.03 | 1.05 | 7.78 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 104 | 0 | 2.17 | 4.77 | 15.18 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 180 | 0 | 1.11 | 1.96 | 5.04 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 49 | 10 | 2.01 | 6.14 | 8.01 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 40 | 37 | 6.95 | 13.84 | 27.50 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 81 | 35 | 1.05 | 1.24 | 33.68 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 104 | 35 | 3.55 | 5.67 | 26.40 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 180 | 15 | 1.19 | 2.30 | 13.43 |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 49 | 41 | 7.74 | 14.75 | 22.99 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `kv_read` | 18 | 0 | 2.81 | 3.73 | 4.87 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 435 | 0 | 1.11 | 1.48 | 8.54 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 597 | 248 | 1.13 | 7.43 | 65.49 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `thermal` | 35 | 0 | 1.13 | 1.19 | 1.55 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 325 | 0 | 1.40 | 2.46 | 12.81 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 534 | 54 | 4.78 | 7.47 | 10.38 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 176 | 1 | 1.33 | 6.21 | 11.20 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 714 | 64 | 1.64 | 4.32 | 19.86 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 880 | 72 | 1.26 | 2.39 | 11.77 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 640 | 27 | 1.30 | 5.29 | 10.03 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 534 | 534 | 8.04 | 16.45 | 65.39 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 176 | 139 | 2.27 | 25.93 | 80.06 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 714 | 335 | 2.65 | 7.99 | 47.62 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 880 | 213 | 1.30 | 4.97 | 39.77 |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 640 | 614 | 5.78 | 22.43 | 105.15 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `compute` | 19 | 0 | 5.57 | 6.46 | 7.97 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `layer_fixed_latency` | 106 | 0 | 1.44 | 1.60 | 1.83 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `link_latency` | 605 | 236 | 1.33 | 6.36 | 65.48 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `gpu` | `in_hbm` | `weight_read` | 630 | 2 | 1.12 | 2.26 | 17.89 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `compute` | 606 | 58 | 5.21 | 7.91 | 11.25 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `kv_read` | 285 | 7 | 1.21 | 6.04 | 11.07 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `layer_fixed_latency` | 664 | 66 | 1.80 | 4.70 | 17.51 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `link_latency` | 1,033 | 112 | 1.28 | 2.51 | 10.02 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_kv_store` | `weight_read` | 608 | 24 | 1.70 | 6.07 | 11.17 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `compute` | 606 | 606 | 8.02 | 20.07 | 75.00 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `kv_read` | 285 | 202 | 1.64 | 16.46 | 74.28 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `layer_fixed_latency` | 664 | 272 | 3.02 | 7.68 | 56.48 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `link_latency` | 1,033 | 212 | 1.31 | 4.54 | 39.87 |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `rom` | `in_rom` | `weight_read` | 608 | 570 | 5.22 | 20.20 | 105.15 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 69 | 0 | 1.28 | 1.61 | 2.71 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `layer_fixed_latency` | 311 | 0 | 1.12 | 1.45 | 6.18 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 559 | 133 | 1.11 | 4.67 | 64.87 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 18 | 0 | 1.28 | 2.59 | 2.98 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 209 | 0 | 1.71 | 2.27 | 13.37 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 6 | 0 | 7.69 | 7.76 | 7.86 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 96 | 0 | 1.09 | 1.25 | 6.77 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 96 | 0 | 1.93 | 5.07 | 7.85 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 196 | 0 | 1.22 | 1.72 | 4.18 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 38 | 10 | 1.92 | 7.47 | 8.03 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 6 | 6 | 17.28 | 17.70 | 21.57 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 96 | 54 | 1.39 | 16.48 | 51.44 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 96 | 35 | 3.28 | 7.07 | 19.58 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 196 | 31 | 1.24 | 2.34 | 19.55 |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 38 | 36 | 5.19 | 14.14 | 22.97 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 15 | 0 | 1.31 | 1.36 | 1.49 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 364 | 71 | 1.49 | 3.56 | 64.63 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 392 | 0 | 1.19 | 1.91 | 16.33 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 18 | 0 | 7.51 | 7.87 | 8.05 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 90 | 0 | 1.11 | 1.24 | 7.71 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 52 | 0 | 2.04 | 3.91 | 6.17 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 210 | 0 | 1.20 | 1.87 | 5.15 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 68 | 11 | 1.95 | 7.45 | 8.06 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 18 | 18 | 12.02 | 18.77 | 30.92 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 90 | 46 | 1.27 | 14.51 | 32.11 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 52 | 10 | 3.46 | 6.00 | 9.76 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 210 | 17 | 1.23 | 2.58 | 12.16 |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 68 | 66 | 5.75 | 14.08 | 22.98 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 349 | 0 | 1.26 | 1.95 | 14.92 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `layer_fixed_latency` | 233 | 0 | 1.11 | 1.28 | 5.72 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 708 | 98 | 1.06 | 2.78 | 62.97 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 22 | 0 | 1.48 | 2.06 | 2.08 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 10 | 2 | 5.55 | 7.91 | 8.16 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 62 | 0 | 1.04 | 1.05 | 6.03 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 169 | 6 | 2.65 | 6.62 | 8.12 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 185 | 0 | 1.12 | 1.90 | 4.72 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 51 | 10 | 1.88 | 6.22 | 8.01 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 10 | 8 | 5.88 | 20.03 | 31.25 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 62 | 22 | 1.17 | 1.58 | 51.30 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 169 | 93 | 3.96 | 8.78 | 18.70 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 185 | 13 | 1.20 | 2.25 | 16.91 |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 51 | 42 | 7.53 | 13.99 | 22.99 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 294 | 0 | 1.15 | 1.47 | 17.03 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 407 | 45 | 1.43 | 2.00 | 58.79 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 162 | 0 | 1.07 | 2.08 | 12.50 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 41 | 8 | 5.44 | 8.01 | 8.10 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 85 | 0 | 1.03 | 1.05 | 5.59 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 117 | 2 | 3.40 | 5.33 | 8.08 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 163 | 0 | 1.19 | 2.10 | 4.57 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 50 | 10 | 1.95 | 6.63 | 8.01 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 41 | 39 | 7.54 | 15.95 | 34.50 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 85 | 23 | 1.07 | 1.25 | 33.89 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 117 | 42 | 4.00 | 6.53 | 22.93 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 163 | 10 | 1.19 | 2.50 | 12.41 |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 50 | 49 | 8.65 | 14.21 | 22.99 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `kv_read` | 2 | 0 | 3.98 | 4.47 | 4.47 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `layer_fixed_latency` | 499 | 0 | 1.12 | 1.51 | 7.28 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 942 | 339 | 1.16 | 6.19 | 65.02 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `thermal` | 44 | 0 | 1.14 | 1.65 | 2.87 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 453 | 3 | 1.48 | 2.43 | 21.72 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 602 | 32 | 4.82 | 7.55 | 11.39 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 174 | 4 | 1.38 | 6.28 | 11.46 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 589 | 68 | 1.91 | 4.73 | 8.14 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 1,023 | 76 | 1.25 | 2.74 | 8.28 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 580 | 30 | 2.01 | 5.75 | 9.59 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 602 | 602 | 8.09 | 27.28 | 86.57 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 174 | 155 | 2.48 | 29.61 | 80.92 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 589 | 338 | 3.15 | 8.13 | 52.36 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 1,023 | 297 | 1.34 | 5.59 | 31.74 |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 580 | 542 | 5.11 | 20.66 | 108.05 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `compute` | 2 | 0 | 5.89 | 6.99 | 6.99 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `link_latency` | 552 | 192 | 1.50 | 5.74 | 65.00 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `gpu` | `in_hbm` | `weight_read` | 645 | 1 | 1.20 | 2.12 | 18.94 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `compute` | 564 | 32 | 5.27 | 7.95 | 11.62 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `kv_read` | 183 | 4 | 1.23 | 6.21 | 11.77 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `layer_fixed_latency` | 420 | 52 | 2.11 | 5.25 | 8.13 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `link_latency` | 944 | 96 | 1.22 | 2.85 | 8.30 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_kv_store` | `weight_read` | 409 | 35 | 1.93 | 6.74 | 11.63 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `compute` | 564 | 564 | 8.07 | 26.90 | 93.56 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `kv_read` | 183 | 142 | 1.82 | 29.41 | 107.02 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `layer_fixed_latency` | 420 | 218 | 4.10 | 8.06 | 59.95 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `link_latency` | 944 | 214 | 1.37 | 5.97 | 31.76 |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `rom` | `in_rom` | `weight_read` | 409 | 377 | 5.03 | 20.39 | 102.10 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `layer_fixed_latency` | 210 | 0 | 1.94 | 2.06 | 2.97 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 900 | 340 | 1.66 | 7.30 | 60.93 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 10 | 0 | 1.97 | 2.27 | 2.54 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 315 | 0 | 2.25 | 2.61 | 4.93 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 132 | 14 | 5.75 | 7.14 | 8.37 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 57 | 0 | 2.09 | 3.24 | 6.68 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 141 | 0 | 1.96 | 3.54 | 6.72 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 499 | 121 | 1.26 | 4.93 | 10.73 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `thermal` | 14 | 0 | 5.08 | 5.61 | 5.99 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 255 | 38 | 1.86 | 3.74 | 8.16 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 132 | 130 | 6.54 | 23.49 | 62.68 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 57 | 11 | 1.79 | 4.81 | 51.45 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 141 | 78 | 3.14 | 8.40 | 71.27 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 499 | 174 | 1.40 | 6.04 | 38.68 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `thermal` | 14 | 14 | 10.50 | 20.16 | 44.49 |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 255 | 234 | 6.86 | 16.76 | 116.72 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `layer_fixed_latency` | 379 | 0 | 1.26 | 1.57 | 4.55 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 800 | 338 | 1.23 | 7.78 | 65.62 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 40 | 0 | 1.23 | 1.39 | 2.25 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 311 | 0 | 2.32 | 2.67 | 11.25 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 489 | 225 | 5.38 | 8.19 | 20.08 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 40 | 34 | 5.66 | 27.71 | 34.72 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 978 | 140 | 1.78 | 5.38 | 22.50 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,014 | 202 | 1.24 | 3.57 | 10.37 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 411 | 63 | 1.65 | 5.11 | 14.95 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 489 | 485 | 8.03 | 12.54 | 44.43 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 40 | 36 | 5.57 | 29.15 | 98.73 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 978 | 701 | 2.58 | 15.44 | 61.08 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,014 | 308 | 1.30 | 6.01 | 30.55 |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 411 | 393 | 5.99 | 18.59 | 112.90 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `layer_fixed_latency` | 382 | 0 | 1.25 | 1.59 | 4.47 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 725 | 318 | 1.21 | 7.91 | 65.63 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 40 | 0 | 1.23 | 1.42 | 4.62 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 313 | 2 | 2.13 | 2.74 | 14.83 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 487 | 228 | 5.29 | 8.23 | 30.82 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 47 | 46 | 9.72 | 64.10 | 79.73 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 1,027 | 183 | 1.76 | 5.72 | 43.79 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 974 | 188 | 1.24 | 3.43 | 31.01 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 413 | 57 | 1.63 | 5.28 | 38.75 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 487 | 483 | 8.08 | 12.57 | 38.62 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 47 | 45 | 5.10 | 33.49 | 62.25 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 1,027 | 712 | 2.55 | 15.38 | 58.94 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 974 | 281 | 1.31 | 5.67 | 30.70 |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 413 | 395 | 7.13 | 18.63 | 113.13 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `layer_fixed_latency` | 369 | 0 | 1.49 | 1.85 | 2.60 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,199 | 500 | 1.41 | 7.78 | 64.82 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 58 | 0 | 1.55 | 3.46 | 4.73 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 459 | 0 | 2.56 | 2.94 | 4.72 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 649 | 220 | 5.14 | 7.72 | 13.87 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 48 | 42 | 6.74 | 13.28 | 14.38 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 315 | 13 | 1.42 | 3.44 | 9.96 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 964 | 242 | 1.25 | 5.38 | 8.39 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 292 | 60 | 1.88 | 6.93 | 10.89 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 649 | 635 | 7.13 | 25.37 | 107.78 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 48 | 45 | 5.21 | 74.23 | 106.54 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 315 | 228 | 2.72 | 15.42 | 73.87 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 964 | 357 | 1.41 | 7.57 | 33.38 |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 292 | 261 | 4.63 | 16.27 | 144.11 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `layer_fixed_latency` | 377 | 0 | 1.37 | 1.74 | 3.47 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,135 | 459 | 1.30 | 7.71 | 65.13 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 59 | 0 | 1.22 | 2.92 | 4.79 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 399 | 0 | 2.37 | 2.95 | 8.57 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 685 | 306 | 5.52 | 7.93 | 42.71 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 24 | 24 | 41.32 | 45.35 | 52.39 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 422 | 33 | 1.41 | 4.11 | 15.17 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 931 | 204 | 1.23 | 4.89 | 8.39 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 356 | 88 | 1.86 | 7.57 | 23.11 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 685 | 681 | 7.06 | 33.17 | 107.74 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 24 | 24 | 30.06 | 66.47 | 80.33 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 422 | 282 | 2.48 | 9.69 | 77.61 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 931 | 299 | 1.41 | 7.13 | 34.48 |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 356 | 314 | 5.13 | 16.20 | 146.43 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `layer_fixed_latency` | 350 | 0 | 1.34 | 1.73 | 3.46 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 1,028 | 411 | 1.29 | 7.70 | 65.09 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 56 | 0 | 1.25 | 2.92 | 4.80 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 386 | 2 | 2.33 | 2.94 | 18.98 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 694 | 297 | 5.53 | 7.89 | 88.09 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 34 | 34 | 85.96 | 93.79 | 105.24 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 436 | 57 | 1.42 | 4.34 | 37.53 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 963 | 228 | 1.22 | 4.90 | 21.40 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 369 | 90 | 1.87 | 7.57 | 34.85 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 694 | 692 | 7.69 | 34.26 | 109.23 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 34 | 34 | 16.65 | 40.43 | 44.38 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 436 | 293 | 2.46 | 9.91 | 71.77 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 963 | 300 | 1.41 | 7.20 | 34.63 |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 369 | 325 | 5.17 | 16.19 | 146.87 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 626 | 233 | 2.05 | 6.90 | 51.19 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 277 | 0 | 2.59 | 2.98 | 11.16 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 58 | 4 | 6.38 | 7.31 | 8.44 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 128 | 0 | 2.01 | 3.75 | 7.66 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 81 | 0 | 2.19 | 3.79 | 5.37 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 406 | 74 | 1.26 | 3.77 | 10.67 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 149 | 37 | 2.23 | 4.41 | 8.10 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 58 | 56 | 6.75 | 24.70 | 74.78 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 128 | 63 | 1.47 | 8.22 | 83.64 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 81 | 31 | 4.13 | 6.80 | 66.85 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 406 | 117 | 1.44 | 6.20 | 37.47 |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 149 | 138 | 6.71 | 18.18 | 117.81 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 2 | 1 | 7.65 | 8.20 | 8.20 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 952 | 315 | 1.40 | 6.16 | 65.56 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 486 | 0 | 1.45 | 3.03 | 7.17 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 555 | 329 | 5.17 | 8.48 | 14.43 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 133 | 118 | 4.18 | 24.54 | 34.72 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 779 | 88 | 1.98 | 6.28 | 22.69 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,091 | 215 | 1.24 | 3.78 | 10.37 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 458 | 149 | 2.07 | 6.92 | 23.29 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 555 | 527 | 5.93 | 14.88 | 60.51 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 133 | 121 | 3.04 | 44.64 | 98.73 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 779 | 531 | 2.72 | 16.28 | 68.09 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,091 | 284 | 1.31 | 5.56 | 28.82 |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 458 | 424 | 6.00 | 18.25 | 112.67 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `compute` | 1 | 1 | 8.56 | 8.56 | 8.56 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 805 | 266 | 1.39 | 6.05 | 65.57 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 464 | 0 | 1.40 | 3.00 | 12.14 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 565 | 360 | 6.11 | 8.51 | 41.85 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 53 | 52 | 7.85 | 63.92 | 79.73 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 854 | 178 | 1.96 | 7.19 | 50.88 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 1,074 | 209 | 1.24 | 3.94 | 31.01 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 470 | 152 | 2.06 | 7.18 | 33.66 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 565 | 547 | 7.28 | 14.61 | 61.93 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 53 | 50 | 5.33 | 33.64 | 62.25 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 854 | 596 | 2.71 | 17.21 | 68.54 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 1,074 | 264 | 1.32 | 5.35 | 29.38 |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 470 | 439 | 6.91 | 18.46 | 113.01 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 553 | 294 | 2.56 | 8.27 | 63.65 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 750 | 0 | 1.65 | 3.11 | 5.88 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 616 | 390 | 5.88 | 8.54 | 15.30 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 44 | 37 | 7.27 | 13.58 | 15.62 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 250 | 8 | 1.43 | 3.55 | 8.19 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 864 | 232 | 1.25 | 5.46 | 8.39 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 182 | 63 | 2.01 | 7.94 | 13.93 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 616 | 602 | 7.01 | 37.25 | 113.12 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 44 | 40 | 3.45 | 77.82 | 112.75 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 250 | 170 | 3.76 | 11.40 | 54.17 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 864 | 293 | 1.43 | 7.26 | 23.56 |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 182 | 159 | 5.25 | 15.34 | 23.00 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 475 | 266 | 3.15 | 8.27 | 64.87 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 724 | 1 | 1.45 | 3.09 | 14.91 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 609 | 420 | 5.59 | 8.68 | 47.66 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 23 | 21 | 7.70 | 48.86 | 52.97 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 332 | 38 | 1.42 | 4.54 | 22.94 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 896 | 206 | 1.23 | 5.00 | 8.39 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 306 | 116 | 1.89 | 8.10 | 34.46 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 609 | 607 | 7.00 | 43.57 | 122.02 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 23 | 21 | 6.22 | 69.52 | 80.64 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 332 | 226 | 2.51 | 11.48 | 83.95 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 896 | 259 | 1.40 | 6.84 | 24.79 |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 306 | 265 | 5.14 | 16.08 | 146.85 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `compute` | 1 | 1 | 8.37 | 8.37 | 8.37 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 452 | 266 | 2.83 | 8.35 | 65.08 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 747 | 1 | 1.45 | 3.05 | 19.11 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 645 | 436 | 5.59 | 8.69 | 94.68 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 29 | 28 | 9.50 | 96.73 | 105.24 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 362 | 61 | 1.43 | 4.74 | 37.53 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 943 | 236 | 1.22 | 5.20 | 14.65 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 343 | 145 | 1.90 | 8.18 | 40.17 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 645 | 643 | 7.06 | 41.40 | 123.26 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 29 | 29 | 8.74 | 42.56 | 45.04 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 362 | 232 | 2.49 | 10.62 | 85.86 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 943 | 281 | 1.40 | 6.88 | 24.99 |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 343 | 298 | 4.86 | 16.09 | 147.41 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `layer_fixed_latency` | 291 | 0 | 1.39 | 1.64 | 2.63 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 819 | 313 | 1.32 | 7.42 | 65.31 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `thermal` | 24 | 0 | 1.23 | 1.59 | 2.23 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 299 | 0 | 2.29 | 2.55 | 3.66 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 195 | 91 | 6.48 | 8.22 | 8.81 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 62 | 0 | 3.15 | 7.94 | 8.14 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 601 | 5 | 1.97 | 4.69 | 13.70 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 956 | 218 | 1.24 | 4.74 | 11.10 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 390 | 39 | 1.74 | 4.10 | 12.09 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 195 | 195 | 8.23 | 11.99 | 45.25 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 62 | 48 | 2.44 | 21.64 | 40.98 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 601 | 476 | 2.45 | 29.58 | 68.05 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 956 | 336 | 1.32 | 6.66 | 41.26 |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 390 | 366 | 5.26 | 22.29 | 111.60 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `layer_fixed_latency` | 155 | 0 | 2.14 | 2.26 | 2.71 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 976 | 386 | 1.68 | 7.48 | 59.78 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `thermal` | 20 | 0 | 3.35 | 4.13 | 4.41 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 335 | 0 | 2.55 | 2.89 | 5.91 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 106 | 15 | 6.30 | 7.72 | 8.58 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 45 | 10 | 2.77 | 5.15 | 8.55 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 115 | 0 | 1.45 | 3.24 | 6.65 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 347 | 78 | 1.34 | 4.98 | 8.39 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 185 | 21 | 2.09 | 5.46 | 8.17 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 106 | 104 | 7.51 | 49.94 | 97.89 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 45 | 30 | 3.60 | 16.66 | 139.01 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 115 | 55 | 3.23 | 8.11 | 64.56 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 347 | 110 | 1.51 | 6.63 | 33.04 |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 185 | 161 | 6.29 | 14.36 | 168.25 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `link_latency` | 874 | 293 | 1.56 | 6.03 | 64.63 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `gpu` | `in_hbm` | `weight_read` | 417 | 0 | 1.77 | 3.05 | 5.58 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `compute` | 324 | 125 | 6.72 | 8.59 | 10.11 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `kv_read` | 102 | 16 | 3.30 | 8.09 | 10.60 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `layer_fixed_latency` | 342 | 4 | 2.21 | 3.03 | 13.69 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `link_latency` | 992 | 215 | 1.24 | 4.60 | 11.35 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_kv_store` | `weight_read` | 348 | 41 | 2.11 | 5.72 | 8.82 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `compute` | 324 | 324 | 8.23 | 38.68 | 62.70 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `kv_read` | 102 | 74 | 1.79 | 15.04 | 72.21 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `layer_fixed_latency` | 342 | 264 | 2.95 | 15.96 | 74.88 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `link_latency` | 992 | 320 | 1.32 | 6.58 | 28.51 |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `rom` | `in_rom` | `weight_read` | 348 | 326 | 5.57 | 31.62 | 111.00 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `link_latency` | 567 | 229 | 1.94 | 7.71 | 50.89 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `gpu` | `in_hbm` | `weight_read` | 400 | 0 | 2.56 | 3.34 | 12.47 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `compute` | 54 | 11 | 6.48 | 7.94 | 9.22 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `kv_read` | 54 | 1 | 2.54 | 3.86 | 8.65 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `layer_fixed_latency` | 47 | 0 | 1.47 | 3.46 | 4.64 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `link_latency` | 214 | 18 | 1.34 | 3.46 | 8.32 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_kv_store` | `weight_read` | 57 | 12 | 2.13 | 6.48 | 8.18 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `compute` | 54 | 50 | 6.71 | 38.21 | 91.60 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `kv_read` | 54 | 36 | 2.84 | 9.26 | 126.62 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `layer_fixed_latency` | 47 | 26 | 4.06 | 8.73 | 31.07 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `link_latency` | 214 | 31 | 1.54 | 5.31 | 35.25 |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `rom` | `in_rom` | `weight_read` | 57 | 55 | 7.35 | 16.11 | 23.00 |

## Per model, per context, per batch and per design class

Each row is that class's **fastest** feasible design at that batch, read against the iso-area GPU comparator the published study already chose for it. The `densest` pick of every class is in `analytical.json` beside it.

**The ROM-versus-GPU ratio under speculation is `T_cycle(GPU) / T_cycle(ROM)` and carries no `tau` at all.** The acceptance length is a property of the model and its drafter, not of the machine, so it is the same on both sides and cancels out of the ratio. Every movement in the last column is therefore a machine effect and nothing else.

### `n5_vs_b200-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,178.5 | 1,311.5-1,311.5 | 15.93 | **no** | `b200_sxm-x90-nvl72-hybrid` | 697.1 | 2,974.1-2,974.1 | 1.17 | yes | 5.994x | 0.441x | 0.074x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3,806.2 | 362.8-362.8 | 52.45 | **no** | `b200_sxm-x87-nvl72-hybrid` | 696.4 | 2,967.0-2,967.0 | 1.17 | yes | 5.465x | 0.122x | 0.022x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,178.5 | 1,311.5-1,311.5 | 15.93 | **no** | `b200_sxm-x90-nvl72-hybrid` | 697.1 | 2,974.1-2,974.1 | 1.17 | yes | 5.994x | 0.441x | 0.074x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3,806.2 | 362.8-362.8 | 52.45 | **no** | `b200_sxm-x87-nvl72-hybrid` | 696.4 | 2,967.0-2,967.0 | 1.17 | yes | 5.465x | 0.122x | 0.022x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,178.5 | 1,311.5-1,311.5 | 15.93 | **no** | `b200_sxm-x90-nvl72-hybrid` | 686.1 | 2,765.4-2,765.4 | 1.24 | yes | 6.090x | 0.474x | 0.078x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3,806.2 | 362.8-362.8 | 52.45 | **no** | `b200_sxm-x87-nvl72-hybrid` | 685.2 | 2,756.8-2,756.8 | 1.24 | yes | 5.555x | 0.132x | 0.024x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,178.5 | 1,311.5-1,311.5 | 15.93 | **no** | `b200_sxm-x90-nvl72-hybrid` | 665.8 | 2,558.1-2,558.1 | 1.30 | yes | 6.276x | 0.513x | 0.082x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3,806.2 | 362.8-362.8 | 52.45 | **no** | `b200_sxm-x87-nvl72-hybrid` | 664.3 | 2,545.1-2,545.1 | 1.31 | yes | 5.729x | 0.143x | 0.025x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,177.6 | 693.4-693.4 | 30.12 | **no** | `b200_sxm-x90-nvl72-hybrid` | 634.4 | 2,171.6-2,171.6 | 1.46 | yes | 6.585x | 0.319x | 0.048x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3,806.2 | 362.8-362.8 | 52.45 | **no** | `b200_sxm-x87-nvl72-hybrid` | 635.9 | 2,211.3-2,211.3 | 1.44 | yes | 5.986x | 0.164x | 0.027x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 4,126.3 | 473.8-473.8 | 43.55 | **no** | `b200_sxm-x134-nvl72-hybrid` | 618.2 | 2,071.7-2,071.7 | 1.49 | yes | 6.675x | 0.229x | 0.034x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3,806.2 | 362.8-362.8 | 52.45 | **no** | `b200_sxm-x87-nvl72-hybrid` | 590.0 | 1,863.8-1,863.8 | 1.58 | yes | 6.451x | 0.195x | 0.030x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 4,055.8 | 240.7-240.7 | 84.26 | **no** | `b200_sxm-x134-nvl72-hybrid` | 563.2 | 1,714.5-1,714.5 | 1.64 | yes | 7.201x | 0.140x | 0.019x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 3,742.6 | 277.2-277.2 | 67.50 | **no** | `b200_sxm-x116-nvl72-hybrid` | 548.5 | 1,623.2-1,623.2 | 1.69 | yes | 6.824x | 0.171x | 0.025x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 3,337.7 | 177.7-177.7 | 93.89 | **no** | `b200_sxm-x179-nvl72-hybrid` | 418.9 | 1,022.9-1,022.9 | 2.05 | yes | 7.969x | 0.174x | 0.022x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,452.7 | 218.2-218.2 | 79.10 | **no** | `b200_sxm-x347-nvl72-hybrid` | 501.3 | 1,358.8-1,358.8 | 1.84 | yes | 6.887x | 0.161x | 0.023x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 1,644.4 | 86.8-86.8 | 94.70 | **no** | `b200_sxm-x179-nvl72-hybrid` | 235.5 | 449.1-449.1 | 2.62 | yes | 6.982x | 0.193x | 0.028x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,136.9 | 107.5-107.5 | 99.35 | **no** | `b200_sxm-x347-nvl72-hybrid` | 302.6 | 685.5-685.5 | 2.21 | yes | 7.062x | 0.157x | 0.022x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 559.3 | 41.2-41.2 | 67.88 | **no** | `b200_sxm-x179-nvl72-hybrid` | 133.2 | 154.1-154.1 | 4.32 | yes | 4.197x | 0.267x | 0.064x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 670.3 | 85.1-85.1 | 39.39 | **no** | `b200_sxm-x347-nvl72-hybrid` | 159.6 | 202.5-202.5 | 3.94 | yes | 4.201x | 0.420x | 0.100x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.019x to 0.100x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,144.8 | 880.9-880.9 | 23.52 | **no** | `a100_sxm_80gb-x258-hybrid` | 358.7 | 951.0-951.0 | 1.89 | yes | 11.556x | 0.926x | 0.080x |
| DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,636.7 | 529.1-529.1 | 34.37 | **no** | `a100_sxm_80gb-x224-hybrid` | 363.9 | 989.4-989.4 | 1.84 | yes | 9.995x | 0.535x | 0.054x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,144.8 | 880.9-880.9 | 23.52 | **no** | `a100_sxm_80gb-x258-hybrid` | 358.7 | 951.0-951.0 | 1.89 | yes | 11.556x | 0.926x | 0.080x |
| DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,636.7 | 529.1-529.1 | 34.37 | **no** | `a100_sxm_80gb-x224-hybrid` | 363.9 | 989.4-989.4 | 1.84 | yes | 9.995x | 0.535x | 0.054x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,144.8 | 880.9-880.9 | 23.52 | **no** | `a100_sxm_80gb-x258-hybrid` | 358.7 | 951.0-951.0 | 1.89 | yes | 11.556x | 0.926x | 0.080x |
| DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,636.7 | 529.1-529.1 | 34.37 | **no** | `a100_sxm_80gb-x224-hybrid` | 363.9 | 989.4-989.4 | 1.84 | yes | 9.995x | 0.535x | 0.054x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,144.8 | 880.9-880.9 | 23.52 | **no** | `a100_sxm_80gb-x258-hybrid` | 358.7 | 951.0-951.0 | 1.89 | yes | 11.556x | 0.926x | 0.080x |
| DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,636.7 | 529.1-529.1 | 34.37 | **no** | `a100_sxm_80gb-x224-hybrid` | 363.9 | 989.4-989.4 | 1.84 | yes | 9.995x | 0.535x | 0.054x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,144.8 | 880.9-880.9 | 23.52 | **no** | `a100_sxm_80gb-x258-hybrid` | 358.7 | 951.0-951.0 | 1.89 | yes | 11.556x | 0.926x | 0.080x |
| DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,636.7 | 529.1-529.1 | 34.37 | **no** | `a100_sxm_80gb-x224-hybrid` | 363.9 | 989.4-989.4 | 1.84 | yes | 9.995x | 0.535x | 0.054x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 4,089.0 | 469.2-469.2 | 43.57 | **no** | `a100_sxm_80gb-x258-hybrid` | 358.7 | 951.0-951.0 | 1.89 | yes | 11.400x | 0.493x | 0.043x |
| DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3,582.7 | 364.9-364.9 | 49.10 | **no** | `a100_sxm_80gb-x336-hybrid` | 357.8 | 915.8-915.8 | 1.95 | yes | 10.013x | 0.398x | 0.040x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 3,982.2 | 238.2-238.2 | 83.60 | **no** | `a100_sxm_80gb-x258-hybrid` | 317.5 | 720.3-720.3 | 2.20 | yes | 12.543x | 0.331x | 0.026x |
| DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,551.0 | 606.7-606.7 | 29.26 | **no** | `a100_sxm_80gb-x672-hybrid` | 357.8 | 829.9-829.9 | 2.16 | yes | 9.924x | 0.731x | 0.074x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 3,006.5 | 93.1-93.1 | 161.52 | **no** | `a100_sxm_80gb-x335-hybrid` | 210.7 | 375.8-375.8 | 2.80 | yes | 14.269x | 0.248x | 0.017x |
| DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,082.4 | 305.5-305.5 | 50.44 | **no** | `a100_sxm_80gb-x672-hybrid` | 278.5 | 514.8-514.8 | 2.70 | yes | 11.067x | 0.593x | 0.054x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,196.0 | 45.2-45.2 | 132.38 | **no** | `a100_sxm_80gb-x337-hybrid` | 94.1 | 176.9-176.9 | 2.66 | yes | 12.713x | 0.255x | 0.020x |
| DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,667.0 | 77.6-77.6 | 107.37 | **no** | `a100_sxm_80gb-x672-hybrid` | 144.9 | 249.0-249.0 | 2.91 | yes | 11.506x | 0.312x | 0.027x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 331.6 | 39.0-39.0 | 42.50 | **no** | `a100_sxm_80gb-x337-hybrid` | 36.8 | 49.1-49.1 | 3.75 | yes | 9.024x | 0.795x | 0.088x |
| DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 602.0 | 44.2-44.2 | 68.16 | **no** | `a100_sxm_80gb-x672-hybrid` | 57.8 | 115.4-115.4 | 2.51 | yes | 10.408x | 0.383x | 0.037x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.017x to 0.088x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 4,105.0 | 1,048.6-1,048.6 | 19.57 | **no** | `b200_sxm-x112-nvl72-hybrid` | 700.7 | 3,013.8-3,013.8 | 1.16 | yes | 5.859x | 0.348x | 0.059x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 3,405.8 | 364.8-364.8 | 46.68 | **no** | `b200_sxm-x173-nvl72-hybrid` | 699.6 | 2,998.4-2,998.4 | 1.17 | yes | 4.868x | 0.122x | 0.025x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 4,105.0 | 1,048.6-1,048.6 | 19.57 | **no** | `b200_sxm-x112-nvl72-hybrid` | 700.7 | 3,013.8-3,013.8 | 1.16 | yes | 5.859x | 0.348x | 0.059x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 3,405.8 | 364.8-364.8 | 46.68 | **no** | `b200_sxm-x173-nvl72-hybrid` | 699.6 | 2,998.4-2,998.4 | 1.17 | yes | 4.868x | 0.122x | 0.025x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 4,105.0 | 1,048.6-1,048.6 | 19.57 | **no** | `b200_sxm-x112-nvl72-hybrid` | 690.6 | 2,812.5-2,812.5 | 1.23 | yes | 5.944x | 0.373x | 0.063x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 3,405.8 | 364.8-364.8 | 46.68 | **no** | `b200_sxm-x173-nvl72-hybrid` | 696.2 | 2,921.3-2,921.3 | 1.19 | yes | 4.892x | 0.125x | 0.026x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 4,105.0 | 1,048.6-1,048.6 | 19.57 | **no** | `b200_sxm-x112-nvl72-hybrid` | 671.6 | 2,502.7-2,502.7 | 1.34 | yes | 6.113x | 0.419x | 0.069x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 3,405.8 | 364.8-364.8 | 46.68 | **no** | `b200_sxm-x173-nvl72-hybrid` | 682.7 | 2,669.5-2,669.5 | 1.28 | yes | 4.989x | 0.137x | 0.027x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 4,095.4 | 879.8-879.8 | 23.27 | **no** | `b200_sxm-x134-nvl72-hybrid` | 649.6 | 2,393.3-2,393.3 | 1.36 | yes | 6.304x | 0.368x | 0.058x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 3,405.8 | 364.8-364.8 | 46.68 | **no** | `b200_sxm-x173-nvl72-hybrid` | 659.8 | 2,501.6-2,501.6 | 1.32 | yes | 5.162x | 0.146x | 0.028x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 4,000.6 | 470.2-470.2 | 42.54 | **no** | `b200_sxm-x134-nvl72-hybrid` | 615.5 | 2,064.7-2,064.7 | 1.49 | yes | 6.500x | 0.228x | 0.035x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 3,405.8 | 364.8-364.8 | 46.68 | **no** | `b200_sxm-x173-nvl72-hybrid` | 626.7 | 2,163.5-2,163.5 | 1.45 | yes | 5.435x | 0.169x | 0.031x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 3,833.7 | 354.1-354.1 | 54.14 | **no** | `b200_sxm-x179-nvl72-hybrid` | 581.3 | 1,828.6-1,828.6 | 1.59 | yes | 6.595x | 0.194x | 0.029x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,312.3 | 808.9-808.9 | 20.47 | **no** | `b200_sxm-x347-nvl72-hybrid` | 616.5 | 2,064.3-2,064.3 | 1.49 | yes | 5.373x | 0.392x | 0.073x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 3,022.0 | 174.8-174.8 | 86.43 | **no** | `b200_sxm-x179-nvl72-hybrid` | 411.5 | 1,012.3-1,012.3 | 2.03 | yes | 7.343x | 0.173x | 0.024x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,613.1 | 407.7-407.7 | 32.05 | **no** | `b200_sxm-x347-nvl72-hybrid` | 495.9 | 1,349.9-1,349.9 | 1.84 | yes | 5.269x | 0.302x | 0.057x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 1,271.5 | 44.2-44.2 | 143.96 | **no** | `b200_sxm-x179-nvl72-hybrid` | 226.5 | 442.2-442.2 | 2.56 | yes | 5.614x | 0.100x | 0.018x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,244.9 | 104.3-104.3 | 59.71 | **no** | `b200_sxm-x347-nvl72-hybrid` | 294.8 | 676.7-676.7 | 2.18 | yes | 4.223x | 0.154x | 0.036x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 364.1 | 38.7-38.7 | 46.99 | **no** | `b200_sxm-x179-nvl72-hybrid` | 122.2 | 150.9-150.9 | 4.05 | yes | 2.979x | 0.257x | 0.086x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 359.2 | 23.0-23.0 | 78.21 | **no** | `b200_sxm-x347-nvl72-hybrid` | 151.1 | 199.7-199.7 | 3.78 | yes | 2.377x | 0.115x | 0.048x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.018x to 0.086x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,023.9 | 752.1-752.1 | 26.75 | **no** | `a100_sxm_80gb-x312-hybrid` | 356.5 | 923.4-923.4 | 1.93 | yes | 11.289x | 0.814x | 0.072x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 3,061.6 | 657.0-657.0 | 23.30 | **no** | `a100_sxm_80gb-x168-hybrid` | 365.5 | 1,025.5-1,025.5 | 1.78 | yes | 8.375x | 0.641x | 0.076x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,023.9 | 752.1-752.1 | 26.75 | **no** | `a100_sxm_80gb-x312-hybrid` | 356.5 | 923.4-923.4 | 1.93 | yes | 11.289x | 0.814x | 0.072x |
| DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,838.2 | 683.0-683.0 | 20.78 | **no** | `a100_sxm_80gb-x336-hybrid` | 356.0 | 913.1-913.1 | 1.95 | yes | 7.974x | 0.748x | 0.094x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,023.9 | 752.1-752.1 | 26.75 | **no** | `a100_sxm_80gb-x312-hybrid` | 356.5 | 923.4-923.4 | 1.93 | yes | 11.289x | 0.814x | 0.072x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,838.2 | 683.0-683.0 | 20.78 | **no** | `a100_sxm_80gb-x336-hybrid` | 356.0 | 913.1-913.1 | 1.95 | yes | 7.974x | 0.748x | 0.094x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,023.9 | 752.1-752.1 | 26.75 | **no** | `a100_sxm_80gb-x312-hybrid` | 356.5 | 923.4-923.4 | 1.93 | yes | 11.289x | 0.814x | 0.072x |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,838.2 | 683.0-683.0 | 20.78 | **no** | `a100_sxm_80gb-x336-hybrid` | 356.0 | 913.1-913.1 | 1.95 | yes | 7.974x | 0.748x | 0.094x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 4,023.9 | 752.1-752.1 | 26.75 | **no** | `a100_sxm_80gb-x312-hybrid` | 356.5 | 923.4-923.4 | 1.93 | yes | 11.289x | 0.814x | 0.072x |
| DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,838.2 | 683.0-683.0 | 20.78 | **no** | `a100_sxm_80gb-x336-hybrid` | 356.0 | 913.1-913.1 | 1.95 | yes | 7.974x | 0.748x | 0.094x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,868.8 | 362.1-362.1 | 53.41 | **no** | `a100_sxm_80gb-x337-hybrid` | 353.6 | 903.4-903.4 | 1.96 | yes | 10.941x | 0.401x | 0.037x |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,819.4 | 364.4-364.4 | 38.69 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 827.7-827.7 | 2.15 | yes | 7.921x | 0.440x | 0.056x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,628.0 | 356.1-356.1 | 50.94 | **no** | `a100_sxm_80gb-x337-hybrid` | 330.1 | 774.0-774.0 | 2.13 | yes | 10.992x | 0.460x | 0.042x |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,770.9 | 185.7-185.7 | 74.62 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 827.7-827.7 | 2.15 | yes | 7.785x | 0.224x | 0.029x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 2,473.4 | 91.3-91.3 | 135.38 | **no** | `a100_sxm_80gb-x337-hybrid` | 207.3 | 375.2-375.2 | 2.76 | yes | 11.930x | 0.243x | 0.020x |
| DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,747.9 | 93.5-93.5 | 93.43 | **no** | `a100_sxm_80gb-x672-hybrid` | 275.1 | 512.2-512.2 | 2.69 | yes | 6.353x | 0.183x | 0.029x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 834.4 | 44.0-44.0 | 94.78 | **no** | `a100_sxm_80gb-x337-hybrid` | 91.1 | 174.6-174.6 | 2.61 | yes | 9.164x | 0.252x | 0.028x |
| DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 596.8 | 23.6-23.6 | 126.56 | **no** | `a100_sxm_80gb-x672-hybrid` | 141.3 | 246.7-246.7 | 2.86 | yes | 4.225x | 0.096x | 0.023x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 223.3 | 35.7-35.7 | 31.24 | **no** | `a100_sxm_80gb-x337-hybrid` | 34.9 | 44.8-44.8 | 3.90 | yes | 6.392x | 0.798x | 0.125x |
| DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 156.6 | 22.5-22.5 | 34.77 | **no** | `a100_sxm_80gb-x672-hybrid` | 55.6 | 113.4-113.4 | 2.45 | yes | 2.818x | 0.198x | 0.070x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.020x to 0.125x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,207.2 | 696.0-696.0 | 30.23 | **no** | `b200_sxm-x90-nvl72-hybrid` | 697.2 | 2,974.4-2,974.4 | 1.17 | yes | 6.035x | 0.234x | 0.039x |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,011.9 | 364.5-364.5 | 55.03 | **no** | `b200_sxm-x87-nvl72-hybrid` | 696.5 | 2,967.3-2,967.3 | 1.17 | yes | 5.760x | 0.123x | 0.021x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,207.2 | 696.0-696.0 | 30.23 | **no** | `b200_sxm-x90-nvl72-hybrid` | 697.2 | 2,974.4-2,974.4 | 1.17 | yes | 6.035x | 0.234x | 0.039x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,011.9 | 364.5-364.5 | 55.03 | **no** | `b200_sxm-x87-nvl72-hybrid` | 696.5 | 2,967.3-2,967.3 | 1.17 | yes | 5.760x | 0.123x | 0.021x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,207.2 | 696.0-696.0 | 30.23 | **no** | `b200_sxm-x90-nvl72-hybrid` | 686.3 | 2,766.0-2,766.0 | 1.24 | yes | 6.130x | 0.252x | 0.041x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,011.9 | 364.5-364.5 | 55.03 | **no** | `b200_sxm-x87-nvl72-hybrid` | 685.4 | 2,757.5-2,757.5 | 1.24 | yes | 5.853x | 0.132x | 0.023x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,207.2 | 696.0-696.0 | 30.23 | **no** | `b200_sxm-x90-nvl72-hybrid` | 666.1 | 2,559.1-2,559.1 | 1.30 | yes | 6.317x | 0.272x | 0.043x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,011.9 | 364.5-364.5 | 55.03 | **no** | `b200_sxm-x87-nvl72-hybrid` | 664.6 | 2,546.1-2,546.1 | 1.31 | yes | 6.036x | 0.143x | 0.024x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,207.2 | 696.0-696.0 | 30.23 | **no** | `b200_sxm-x90-nvl72-hybrid` | 634.9 | 2,173.1-2,173.1 | 1.46 | yes | 6.626x | 0.320x | 0.048x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,011.9 | 364.5-364.5 | 55.03 | **no** | `b200_sxm-x87-nvl72-hybrid` | 636.4 | 2,212.9-2,212.9 | 1.44 | yes | 6.304x | 0.165x | 0.026x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 4,160.7 | 355.4-355.4 | 58.54 | **no** | `b200_sxm-x90-nvl72-hybrid` | 590.7 | 1,872.2-1,872.2 | 1.58 | yes | 7.043x | 0.190x | 0.027x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 4,011.9 | 364.5-364.5 | 55.03 | **no** | `b200_sxm-x87-nvl72-hybrid` | 591.0 | 1,866.1-1,866.1 | 1.58 | yes | 6.789x | 0.195x | 0.029x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 4,140.5 | 406.8-406.8 | 50.89 | **no** | `b200_sxm-x134-nvl72-hybrid` | 564.4 | 1,717.0-1,717.0 | 1.64 | yes | 7.336x | 0.237x | 0.032x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 3,980.3 | 184.2-184.2 | 108.06 | **no** | `b200_sxm-x87-nvl72-hybrid` | 519.1 | 1,431.3-1,431.3 | 1.81 | yes | 7.668x | 0.129x | 0.017x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 3,417.9 | 202.1-202.1 | 84.56 | **no** | `b200_sxm-x179-nvl72-hybrid` | 420.8 | 1,025.7-1,025.7 | 2.05 | yes | 8.123x | 0.197x | 0.024x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,822.3 | 219.5-219.5 | 87.05 | **no** | `b200_sxm-x347-nvl72-hybrid` | 502.8 | 1,361.2-1,361.2 | 1.85 | yes | 7.603x | 0.161x | 0.021x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,717.0 | 90.3-90.3 | 95.13 | **no** | `b200_sxm-x173-nvl72-hybrid` | 235.8 | 431.8-431.8 | 2.73 | yes | 7.281x | 0.209x | 0.029x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,420.0 | 108.5-108.5 | 111.53 | **no** | `b200_sxm-x347-nvl72-hybrid` | 304.7 | 687.7-687.7 | 2.22 | yes | 7.943x | 0.158x | 0.020x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 621.2 | 43.0-43.0 | 72.22 | **no** | `b200_sxm-x173-nvl72-hybrid` | 133.8 | 144.3-144.3 | 4.64 | yes | 4.642x | 0.298x | 0.064x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 768.7 | 93.5-93.5 | 41.11 | **no** | `b200_sxm-x347-nvl72-hybrid` | 161.9 | 203.3-203.3 | 3.98 | yes | 4.749x | 0.460x | 0.097x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.017x to 0.097x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 4,186.3 | 1,125.5-1,125.5 | 18.60 | **no** | `a100_sxm_80gb-x203-hybrid` | 362.5 | 990.7-990.7 | 1.83 | yes | 11.548x | 1.136x | 0.098x |
| DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,855.8 | 275.7-275.7 | 69.94 | **no** | `a100_sxm_80gb-x224-hybrid` | 364.4 | 990.2-990.2 | 1.84 | yes | 10.582x | 0.278x | 0.026x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 4,186.3 | 1,125.5-1,125.5 | 18.60 | **no** | `a100_sxm_80gb-x203-hybrid` | 362.5 | 990.7-990.7 | 1.83 | yes | 11.548x | 1.136x | 0.098x |
| DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,855.8 | 275.7-275.7 | 69.94 | **no** | `a100_sxm_80gb-x224-hybrid` | 364.4 | 990.2-990.2 | 1.84 | yes | 10.582x | 0.278x | 0.026x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 4,186.3 | 1,125.5-1,125.5 | 18.60 | **no** | `a100_sxm_80gb-x203-hybrid` | 362.5 | 990.7-990.7 | 1.83 | yes | 11.548x | 1.136x | 0.098x |
| DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,855.8 | 275.7-275.7 | 69.94 | **no** | `a100_sxm_80gb-x224-hybrid` | 364.4 | 990.2-990.2 | 1.84 | yes | 10.582x | 0.278x | 0.026x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 4,186.3 | 1,125.5-1,125.5 | 18.60 | **no** | `a100_sxm_80gb-x203-hybrid` | 362.5 | 990.7-990.7 | 1.83 | yes | 11.548x | 1.136x | 0.098x |
| DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,855.8 | 275.7-275.7 | 69.94 | **no** | `a100_sxm_80gb-x224-hybrid` | 364.4 | 990.2-990.2 | 1.84 | yes | 10.582x | 0.278x | 0.026x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 4,180.4 | 934.2-934.2 | 22.38 | **no** | `a100_sxm_80gb-x244-hybrid` | 361.0 | 966.0-966.0 | 1.87 | yes | 11.582x | 0.967x | 0.084x |
| DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,855.8 | 275.7-275.7 | 69.94 | **no** | `a100_sxm_80gb-x224-hybrid` | 364.4 | 990.2-990.2 | 1.84 | yes | 10.582x | 0.278x | 0.026x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 4,125.1 | 498.6-498.6 | 41.37 | **no** | `a100_sxm_80gb-x244-hybrid` | 359.4 | 955.4-955.4 | 1.88 | yes | 11.479x | 0.522x | 0.045x |
| DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 3,855.8 | 275.7-275.7 | 69.94 | **no** | `a100_sxm_80gb-x224-hybrid` | 357.5 | 944.2-944.2 | 1.89 | yes | 10.785x | 0.292x | 0.027x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 4,094.0 | 253.4-253.4 | 80.80 | **no** | `a100_sxm_80gb-x244-hybrid` | 315.5 | 711.1-711.1 | 2.22 | yes | 12.977x | 0.356x | 0.027x |
| DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,768.1 | 313.9-313.9 | 60.02 | **no** | `a100_sxm_80gb-x448-hybrid` | 351.3 | 841.1-841.1 | 2.09 | yes | 10.727x | 0.373x | 0.035x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 3,180.2 | 178.9-178.9 | 88.87 | **no** | `a100_sxm_80gb-x337-hybrid` | 212.2 | 378.7-378.7 | 2.80 | yes | 14.987x | 0.472x | 0.032x |
| DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,449.4 | 158.6-158.6 | 108.73 | **no** | `a100_sxm_80gb-x672-hybrid` | 279.4 | 515.5-515.5 | 2.71 | yes | 12.346x | 0.308x | 0.025x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 1,346.4 | 45.5-45.5 | 148.02 | **no** | `a100_sxm_80gb-x337-hybrid` | 94.9 | 177.5-177.5 | 2.67 | yes | 14.190x | 0.256x | 0.018x |
| DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,891.5 | 78.2-78.2 | 120.86 | **no** | `a100_sxm_80gb-x672-hybrid` | 145.8 | 249.6-249.6 | 2.92 | yes | 12.970x | 0.314x | 0.024x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 379.7 | 40.0-40.0 | 47.50 | **no** | `a100_sxm_80gb-x337-hybrid` | 37.2 | 50.3-50.3 | 3.70 | yes | 10.195x | 0.795x | 0.078x |
| DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 704.5 | 83.2-83.2 | 42.36 | **no** | `a100_sxm_80gb-x672-hybrid` | 58.5 | 115.9-115.9 | 2.52 | yes | 12.051x | 0.718x | 0.060x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.018x to 0.098x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 1,217.1-1,217.1 | 17.35 | **no** | `b200_sxm-x49-nvl72-tensor` | 701.4 | 3,016.3-3,016.3 | 1.16 | yes | 6.021x | 0.404x | 0.067x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x10-romfill` | 4,004.0 | 614.8-614.8 | 32.57 | **no** | `b200_sxm-x289-nvl72-hybrid` | 697.0 | 2,953.2-2,953.2 | 1.18 | yes | 5.744x | 0.208x | 0.036x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 1,217.1-1,217.1 | 17.35 | **no** | `b200_sxm-x49-nvl72-tensor` | 691.5 | 2,826.1-2,826.1 | 1.22 | yes | 6.107x | 0.431x | 0.071x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 533.0-533.0 | 36.18 | **no** | `b200_sxm-x58-nvl72-tensor` | 694.8 | 2,856.4-2,856.4 | 1.22 | yes | 5.551x | 0.187x | 0.034x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 1,217.1-1,217.1 | 17.35 | **no** | `b200_sxm-x49-nvl72-tensor` | 672.8 | 2,516.7-2,516.7 | 1.34 | yes | 6.277x | 0.484x | 0.077x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 533.0-533.0 | 36.18 | **no** | `b200_sxm-x58-nvl72-tensor` | 677.4 | 2,552.9-2,552.9 | 1.33 | yes | 5.694x | 0.209x | 0.037x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 1,217.1-1,217.1 | 17.35 | **no** | `b200_sxm-x49-nvl72-tensor` | 639.3 | 2,089.9-2,089.9 | 1.53 | yes | 6.606x | 0.582x | 0.088x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 533.0-533.0 | 36.18 | **no** | `b200_sxm-x58-nvl72-tensor` | 645.9 | 2,125.0-2,125.0 | 1.52 | yes | 5.972x | 0.251x | 0.042x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 4,185.8 | 1,221.9-1,221.9 | 17.13 | **no** | `b200_sxm-x83-nvl72-hybrid` | 630.8 | 2,174.9-2,174.9 | 1.45 | yes | 6.636x | 0.562x | 0.085x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 533.0-533.0 | 36.18 | **no** | `b200_sxm-x58-hybrid` | 603.2 | 1,914.4-1,914.4 | 1.58 | yes | 6.395x | 0.278x | 0.044x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,120.6 | 1,244.2-1,244.2 | 16.56 | **no** | `b200_sxm-x173-nvl72-hybrid` | 628.8 | 2,169.4-2,169.4 | 1.45 | yes | 6.553x | 0.574x | 0.088x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 3,820.4 | 697.4-697.4 | 27.39 | **no** | `b200_sxm-x116-nvl72-hybrid` | 608.9 | 2,004.5-2,004.5 | 1.52 | yes | 6.275x | 0.348x | 0.055x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,097.3 | 656.9-656.9 | 31.18 | **no** | `b200_sxm-x173-nvl72-hybrid` | 583.0 | 1,825.3-1,825.3 | 1.60 | yes | 7.028x | 0.360x | 0.051x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,820.4 | 697.4-697.4 | 27.39 | **no** | `b200_sxm-x231-nvl72-hybrid` | 601.3 | 1,925.7-1,925.7 | 1.56 | yes | 6.354x | 0.362x | 0.057x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,564.4 | 325.7-325.7 | 54.72 | **no** | `b200_sxm-x173-nvl72-hybrid` | 414.3 | 1,013.7-1,013.7 | 2.04 | yes | 8.604x | 0.321x | 0.037x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,659.2 | 356.9-356.9 | 51.26 | **no** | `b200_sxm-x347-nvl72-hybrid` | 501.3 | 1,358.8-1,358.8 | 1.84 | yes | 7.299x | 0.263x | 0.036x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,477.7 | 152.9-152.9 | 48.32 | **no** | `b200_sxm-x173-nvl72-hybrid` | 233.3 | 430.1-430.1 | 2.71 | yes | 6.333x | 0.355x | 0.056x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,613.9 | 175.8-175.8 | 74.34 | **no** | `b200_sxm-x347-nvl72-hybrid` | 302.6 | 685.5-685.5 | 2.21 | yes | 8.638x | 0.256x | 0.030x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 434.5 | 127.1-127.1 | 17.09 | **no** | `b200_sxm-x173-nvl72-hybrid` | 130.7 | 143.6-143.6 | 4.55 | yes | 3.325x | 0.886x | 0.266x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 871.3 | 144.5-144.5 | 30.15 | **no** | `b200_sxm-x347-nvl72-hybrid` | 159.6 | 202.5-202.5 | 3.94 | yes | 5.461x | 0.713x | 0.131x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.030x to 0.266x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 1,558.6-1,558.6 | 13.40 | **no** | `a100_sxm_80gb-x136-hybrid` | 369.6 | 1,048.0-1,048.0 | 1.76 | yes | 11.302x | 1.487x | 0.132x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 3,902.1 | 441.4-441.4 | 44.21 | **no** | `a100_sxm_80gb-x672-hybrid` | 357.8 | 829.9-829.9 | 2.16 | yes | 10.906x | 0.532x | 0.049x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 1,558.6-1,558.6 | 13.40 | **no** | `a100_sxm_80gb-x136-hybrid` | 369.6 | 1,048.0-1,048.0 | 1.76 | yes | 11.302x | 1.487x | 0.132x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 691.9-691.9 | 26.56 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 10.004x | 0.672x | 0.067x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 1,558.6-1,558.6 | 13.40 | **no** | `a100_sxm_80gb-x136-hybrid` | 369.6 | 1,048.0-1,048.0 | 1.76 | yes | 11.302x | 1.487x | 0.132x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 691.9-691.9 | 26.56 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 10.004x | 0.672x | 0.067x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 1,558.6-1,558.6 | 13.40 | **no** | `a100_sxm_80gb-x136-hybrid` | 369.6 | 1,048.0-1,048.0 | 1.76 | yes | 11.302x | 1.487x | 0.132x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 691.9-691.9 | 26.56 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 10.004x | 0.672x | 0.067x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 4,159.2 | 877.1-877.1 | 23.71 | **no** | `a100_sxm_80gb-x132-hybrid` | 366.0 | 1,031.9-1,031.9 | 1.77 | yes | 11.365x | 0.850x | 0.075x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 691.9-691.9 | 26.56 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 10.004x | 0.672x | 0.067x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,087.6 | 916.1-916.1 | 22.31 | **no** | `a100_sxm_80gb-x272-hybrid` | 360.8 | 954.3-954.3 | 1.89 | yes | 11.329x | 0.960x | 0.085x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,614.4 | 977.4-977.4 | 18.49 | **no** | `a100_sxm_80gb-x448-hybrid` | 357.8 | 884.0-884.0 | 2.02 | yes | 10.102x | 1.106x | 0.109x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 3,995.9 | 478.7-478.7 | 41.74 | **no** | `a100_sxm_80gb-x272-hybrid` | 321.9 | 734.3-734.3 | 2.19 | yes | 12.415x | 0.652x | 0.053x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,613.0 | 972.1-972.1 | 18.58 | **no** | `a100_sxm_80gb-x672-hybrid` | 357.8 | 829.9-829.9 | 2.16 | yes | 10.098x | 1.171x | 0.116x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,081.4 | 236.2-236.2 | 65.22 | **no** | `a100_sxm_80gb-x335-hybrid` | 210.7 | 375.8-375.8 | 2.80 | yes | 14.625x | 0.629x | 0.043x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,260.9 | 495.5-495.5 | 32.90 | **no** | `a100_sxm_80gb-x672-hybrid` | 278.5 | 514.8-514.8 | 2.70 | yes | 11.708x | 0.962x | 0.082x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 1,178.4 | 163.6-163.6 | 36.02 | **no** | `a100_sxm_80gb-x335-hybrid` | 93.8 | 176.4-176.4 | 2.66 | yes | 12.568x | 0.927x | 0.074x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,968.8 | 127.0-127.0 | 77.50 | **no** | `a100_sxm_80gb-x672-hybrid` | 144.9 | 249.0-249.0 | 2.91 | yes | 13.589x | 0.510x | 0.038x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 428.5 | 114.1-114.1 | 18.77 | **no** | `a100_sxm_80gb-x335-hybrid` | 36.7 | 48.2-48.2 | 3.80 | yes | 11.688x | 2.368x | 0.203x |
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 602.0 | 104.5-104.5 | 28.80 | **no** | `a100_sxm_80gb-x672-hybrid` | 57.8 | 115.4-115.4 | 2.51 | yes | 10.408x | 0.906x | 0.087x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.038x to 0.203x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x192` | 4,153.1 | 1,206.6-1,206.6 | 17.21 | **no** | `b200_sxm-x98-nvl72-hybrid` | 698.4 | 2,989.8-2,989.8 | 1.17 | yes | 5.947x | 0.404x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 3,781.0 | 615.0-615.0 | 30.74 | **no** | `b200_sxm-x347-nvl72-hybrid` | 699.2 | 2,970.0-2,970.0 | 1.18 | yes | 5.408x | 0.207x | 0.038x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4,134.7 | 1,914.5-1,914.5 | 10.80 | **no** | `b200_sxm-x57-nvl72-tensor` | 694.0 | 2,851.7-2,851.7 | 1.22 | yes | 5.957x | 0.671x | 0.113x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 3,396.5 | 433.3-433.3 | 39.19 | **no** | `b200_sxm-x144-nvl72-hybrid` | 704.1 | 3,045.9-3,045.9 | 1.16 | yes | 4.824x | 0.142x | 0.029x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 4,134.7 | 1,914.5-1,914.5 | 10.80 | **no** | `b200_sxm-x57-nvl72-tensor` | 676.0 | 2,546.4-2,546.4 | 1.33 | yes | 6.116x | 0.752x | 0.123x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 3,396.5 | 433.3-433.3 | 39.19 | **no** | `b200_sxm-x144-nvl72-hybrid` | 695.0 | 2,849.0-2,849.0 | 1.22 | yes | 4.887x | 0.152x | 0.031x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x113` | 4,125.7 | 1,711.4-1,711.4 | 12.05 | **no** | `b200_sxm-x58-nvl72-tensor` | 644.2 | 2,120.6-2,120.6 | 1.52 | yes | 6.405x | 0.807x | 0.126x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 3,396.5 | 433.3-433.3 | 39.19 | **no** | `b200_sxm-x144-nvl72-hybrid` | 678.0 | 2,629.7-2,629.7 | 1.29 | yes | 5.010x | 0.165x | 0.033x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 4,064.8 | 987.5-987.5 | 20.58 | **no** | `b200_sxm-x116-nvl72-hybrid` | 645.7 | 2,341.0-2,341.0 | 1.38 | yes | 6.295x | 0.422x | 0.067x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 3,396.5 | 433.3-433.3 | 39.19 | **no** | `b200_sxm-x144-nvl72-hybrid` | 653.2 | 2,421.1-2,421.1 | 1.35 | yes | 5.200x | 0.179x | 0.034x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 3,956.8 | 684.4-684.4 | 28.91 | **no** | `b200_sxm-x173-nvl72-hybrid` | 626.7 | 2,163.5-2,163.5 | 1.45 | yes | 6.314x | 0.316x | 0.050x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 3,396.5 | 433.3-433.3 | 39.19 | **no** | `b200_sxm-x144-nvl72-hybrid` | 620.3 | 2,100.1-2,100.1 | 1.48 | yes | 5.476x | 0.206x | 0.038x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,762.8 | 641.0-641.0 | 29.35 | **no** | `b200_sxm-x173-nvl72-hybrid` | 579.3 | 1,817.0-1,817.0 | 1.59 | yes | 6.495x | 0.353x | 0.054x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,312.2 | 1,273.8-1,273.8 | 13.00 | **no** | `b200_sxm-x347-nvl72-hybrid` | 616.5 | 2,064.3-2,064.3 | 1.49 | yes | 5.373x | 0.617x | 0.115x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,838.1 | 313.8-313.8 | 45.22 | **no** | `b200_sxm-x173-nvl72-hybrid` | 406.9 | 1,002.9-1,002.9 | 2.03 | yes | 6.975x | 0.313x | 0.045x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,613.0 | 650.5-650.5 | 20.08 | **no** | `b200_sxm-x347-nvl72-hybrid` | 495.9 | 1,349.9-1,349.9 | 1.84 | yes | 5.269x | 0.482x | 0.091x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,055.2 | 161.7-161.7 | 32.63 | **no** | `b200_sxm-x173-nvl72-hybrid` | 224.2 | 423.6-423.6 | 2.65 | yes | 4.707x | 0.382x | 0.081x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,244.9 | 168.9-168.9 | 36.84 | **no** | `b200_sxm-x347-nvl72-hybrid` | 294.8 | 676.7-676.7 | 2.18 | yes | 4.223x | 0.250x | 0.059x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 366.9 | 110.3-110.3 | 16.63 | **no** | `b200_sxm-x173-nvl72-hybrid` | 119.7 | 140.7-140.7 | 4.25 | yes | 3.065x | 0.784x | 0.256x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 358.0 | 44.8-44.8 | 39.93 | **no** | `b200_sxm-x347-nvl72-hybrid` | 151.1 | 199.7-199.7 | 3.78 | yes | 2.369x | 0.224x | 0.095x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.029x to 0.256x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x250` | 4,126.0 | 921.3-921.3 | 22.39 | **no** | `a100_sxm_80gb-x247-hybrid` | 360.0 | 967.2-967.2 | 1.86 | yes | 11.462x | 0.953x | 0.083x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 3,597.6 | 432.0-432.0 | 41.64 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 827.7-827.7 | 2.15 | yes | 10.107x | 0.522x | 0.052x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,067.6 | 1,403.4-1,403.4 | 14.49 | **no** | `a100_sxm_80gb-x155-hybrid` | 362.2 | 1,014.4-1,014.4 | 1.79 | yes | 11.229x | 1.383x | 0.123x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 2,866.0 | 611.3-611.3 | 23.44 | **no** | `a100_sxm_80gb-x392-hybrid` | 356.0 | 896.9-896.9 | 1.98 | yes | 8.052x | 0.682x | 0.085x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,067.6 | 1,403.4-1,403.4 | 14.49 | **no** | `a100_sxm_80gb-x155-hybrid` | 362.2 | 1,014.4-1,014.4 | 1.79 | yes | 11.229x | 1.383x | 0.123x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 2,866.0 | 611.3-611.3 | 23.44 | **no** | `a100_sxm_80gb-x392-hybrid` | 356.0 | 896.9-896.9 | 1.98 | yes | 8.052x | 0.682x | 0.085x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 4,067.6 | 1,403.4-1,403.4 | 14.49 | **no** | `a100_sxm_80gb-x155-hybrid` | 362.2 | 1,014.4-1,014.4 | 1.79 | yes | 11.229x | 1.383x | 0.123x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 2,866.0 | 611.3-611.3 | 23.44 | **no** | `a100_sxm_80gb-x392-hybrid` | 356.0 | 896.9-896.9 | 1.98 | yes | 8.052x | 0.682x | 0.085x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 4,032.7 | 836.5-836.5 | 24.11 | **no** | `a100_sxm_80gb-x272-hybrid` | 358.9 | 951.4-951.4 | 1.89 | yes | 11.236x | 0.879x | 0.078x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 2,866.0 | 611.3-611.3 | 23.44 | **no** | `a100_sxm_80gb-x392-hybrid` | 356.0 | 896.9-896.9 | 1.98 | yes | 8.052x | 0.682x | 0.085x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 3,880.4 | 681.7-681.7 | 28.46 | **no** | `a100_sxm_80gb-x335-hybrid` | 355.6 | 912.0-912.0 | 1.95 | yes | 10.912x | 0.747x | 0.068x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,790.6 | 365.3-365.3 | 38.19 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 827.7-827.7 | 2.15 | yes | 7.840x | 0.441x | 0.056x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 3,631.8 | 361.1-361.1 | 50.29 | **no** | `a100_sxm_80gb-x335-hybrid` | 330.5 | 773.7-773.7 | 2.14 | yes | 10.988x | 0.467x | 0.042x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,714.4 | 186.2-186.2 | 72.91 | **no** | `a100_sxm_80gb-x672-hybrid` | 356.0 | 827.7-827.7 | 2.15 | yes | 7.626x | 0.225x | 0.029x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 2,420.8 | 214.2-214.2 | 56.50 | **no** | `a100_sxm_80gb-x272-hybrid` | 189.4 | 341.5-341.5 | 2.77 | yes | 12.779x | 0.627x | 0.049x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,770.4 | 93.9-93.9 | 94.22 | **no** | `a100_sxm_80gb-x672-hybrid` | 275.1 | 512.2-512.2 | 2.69 | yes | 6.435x | 0.183x | 0.029x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 1,033.4 | 153.3-153.3 | 33.70 | **no** | `a100_sxm_80gb-x335-hybrid` | 90.7 | 174.1-174.1 | 2.61 | yes | 11.389x | 0.880x | 0.077x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 600.9 | 23.7-23.7 | 126.86 | **no** | `a100_sxm_80gb-x672-hybrid` | 141.3 | 246.7-246.7 | 2.86 | yes | 4.254x | 0.096x | 0.023x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 329.8 | 66.2-66.2 | 24.92 | **no** | `a100_sxm_80gb-x335-hybrid` | 34.8 | 44.0-44.0 | 3.96 | yes | 9.464x | 1.503x | 0.159x |
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 157.5 | 22.9-22.9 | 34.38 | **no** | `a100_sxm_80gb-x672-hybrid` | 55.6 | 113.4-113.4 | 2.45 | yes | 2.835x | 0.202x | 0.071x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.023x to 0.159x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,247.4 | 1,220.4-1,220.4 | 17.40 | **no** | `b200_sxm-x47-nvl72-tensor` | 700.7 | 3,009.4-3,009.4 | 1.16 | yes | 6.061x | 0.406x | 0.067x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 4,085.0 | 322.8-322.8 | 63.28 | **no** | `b200_sxm-x347-nvl72-hybrid` | 699.5 | 2,971.0-2,971.0 | 1.18 | yes | 5.840x | 0.109x | 0.019x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,247.4 | 1,220.4-1,220.4 | 17.40 | **no** | `b200_sxm-x47-nvl72-tensor` | 690.7 | 2,818.1-2,818.1 | 1.23 | yes | 6.149x | 0.433x | 0.070x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,064.5 | 691.7-691.7 | 29.38 | **no** | `b200_sxm-x58-nvl72-tensor` | 695.0 | 2,856.9-2,856.9 | 1.22 | yes | 5.848x | 0.242x | 0.041x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,247.4 | 1,220.4-1,220.4 | 17.40 | **no** | `b200_sxm-x47-nvl72-tensor` | 671.9 | 2,507.3-2,507.3 | 1.34 | yes | 6.322x | 0.487x | 0.077x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,064.5 | 691.7-691.7 | 29.38 | **no** | `b200_sxm-x58-nvl72-tensor` | 677.7 | 2,553.7-2,553.7 | 1.33 | yes | 5.998x | 0.271x | 0.045x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,247.4 | 1,220.4-1,220.4 | 17.40 | **no** | `b200_sxm-x47-hybrid` | 639.0 | 2,197.8-2,197.8 | 1.45 | yes | 6.647x | 0.555x | 0.084x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,064.5 | 691.7-691.7 | 29.38 | **no** | `b200_sxm-x58-nvl72-tensor` | 646.3 | 2,126.2-2,126.2 | 1.52 | yes | 6.289x | 0.325x | 0.052x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 4,235.9 | 660.1-660.1 | 32.08 | **no** | `b200_sxm-x47-hybrid` | 594.8 | 1,820.7-1,820.7 | 1.63 | yes | 7.122x | 0.363x | 0.051x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 4,064.5 | 691.7-691.7 | 29.38 | **no** | `b200_sxm-x58-hybrid` | 603.9 | 1,916.2-1,916.2 | 1.58 | yes | 6.730x | 0.361x | 0.054x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x113-romfill` | 4,174.8 | 642.1-642.1 | 32.51 | **no** | `b200_sxm-x58-hybrid` | 542.3 | 1,489.2-1,489.2 | 1.82 | yes | 7.698x | 0.431x | 0.056x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,045.5 | 360.5-360.5 | 56.11 | **no** | `b200_sxm-x231-nvl72-hybrid` | 641.6 | 2,265.6-2,265.6 | 1.42 | yes | 6.305x | 0.159x | 0.025x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,174.4 | 661.1-661.1 | 31.57 | **no** | `b200_sxm-x173-nvl72-hybrid` | 584.0 | 1,827.5-1,827.5 | 1.60 | yes | 7.148x | 0.362x | 0.051x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 4,045.5 | 360.5-360.5 | 56.11 | **no** | `b200_sxm-x231-nvl72-hybrid` | 602.1 | 1,927.5-1,927.5 | 1.56 | yes | 6.719x | 0.187x | 0.028x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,813.2 | 328.9-328.9 | 57.97 | **no** | `b200_sxm-x173-nvl72-hybrid` | 416.2 | 1,016.5-1,016.5 | 2.05 | yes | 9.162x | 0.324x | 0.035x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,044.6 | 360.0-360.0 | 56.18 | **no** | `b200_sxm-x347-nvl72-hybrid` | 502.8 | 1,361.2-1,361.2 | 1.85 | yes | 8.045x | 0.264x | 0.033x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,662.3 | 155.8-155.8 | 53.36 | **no** | `b200_sxm-x173-nvl72-hybrid` | 235.8 | 431.8-431.8 | 2.73 | yes | 7.049x | 0.361x | 0.051x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,967.9 | 177.8-177.8 | 83.46 | **no** | `b200_sxm-x347-nvl72-hybrid` | 304.7 | 687.7-687.7 | 2.22 | yes | 9.741x | 0.259x | 0.027x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 483.7 | 114.0-114.0 | 21.20 | **no** | `b200_sxm-x173-nvl72-hybrid` | 133.8 | 144.3-144.3 | 4.64 | yes | 3.615x | 0.790x | 0.219x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,021.1 | 149.5-149.5 | 34.16 | **no** | `b200_sxm-x347-nvl72-hybrid` | 161.9 | 203.3-203.3 | 3.98 | yes | 6.308x | 0.735x | 0.117x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.019x to 0.219x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,217.9 | 931.3-931.3 | 22.64 | **no** | `a100_sxm_80gb-x126-hybrid` | 368.7 | 1,044.6-1,044.6 | 1.77 | yes | 11.439x | 0.892x | 0.078x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 3,975.2 | 443.7-443.7 | 44.79 | **no** | `a100_sxm_80gb-x672-hybrid` | 358.3 | 830.5-830.5 | 2.16 | yes | 11.095x | 0.534x | 0.048x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,217.9 | 931.3-931.3 | 22.64 | **no** | `a100_sxm_80gb-x126-hybrid` | 368.7 | 1,044.6-1,044.6 | 1.77 | yes | 11.439x | 0.892x | 0.078x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,932.1 | 525.3-525.3 | 37.42 | **no** | `a100_sxm_80gb-x112-hybrid` | 371.7 | 1,060.4-1,060.4 | 1.75 | yes | 10.578x | 0.495x | 0.047x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,217.9 | 931.3-931.3 | 22.64 | **no** | `a100_sxm_80gb-x126-hybrid` | 368.7 | 1,044.6-1,044.6 | 1.77 | yes | 11.439x | 0.892x | 0.078x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,932.1 | 525.3-525.3 | 37.42 | **no** | `a100_sxm_80gb-x112-hybrid` | 371.7 | 1,060.4-1,060.4 | 1.75 | yes | 10.578x | 0.495x | 0.047x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,217.9 | 931.3-931.3 | 22.64 | **no** | `a100_sxm_80gb-x126-hybrid` | 368.7 | 1,044.6-1,044.6 | 1.77 | yes | 11.439x | 0.892x | 0.078x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,932.1 | 525.3-525.3 | 37.42 | **no** | `a100_sxm_80gb-x112-hybrid` | 371.7 | 1,060.4-1,060.4 | 1.75 | yes | 10.578x | 0.495x | 0.047x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,217.9 | 931.3-931.3 | 22.64 | **no** | `a100_sxm_80gb-x126-hybrid` | 368.7 | 1,044.6-1,044.6 | 1.77 | yes | 11.439x | 0.892x | 0.078x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 3,932.1 | 525.3-525.3 | 37.42 | **no** | `a100_sxm_80gb-x112-hybrid` | 365.1 | 1,009.5-1,009.5 | 1.81 | yes | 10.770x | 0.520x | 0.048x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 4,164.9 | 478.8-478.8 | 43.49 | **no** | `a100_sxm_80gb-x126-hybrid` | 326.8 | 799.1-799.1 | 2.05 | yes | 12.743x | 0.599x | 0.047x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 3,927.2 | 512.4-512.4 | 38.32 | **no** | `a100_sxm_80gb-x224-hybrid` | 357.5 | 944.2-944.2 | 1.89 | yes | 10.984x | 0.543x | 0.049x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,135.8 | 481.7-481.7 | 42.93 | **no** | `a100_sxm_80gb-x272-hybrid` | 322.6 | 735.2-735.2 | 2.19 | yes | 12.821x | 0.655x | 0.051x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,927.2 | 512.4-512.4 | 38.32 | **no** | `a100_sxm_80gb-x448-hybrid` | 351.3 | 841.1-841.1 | 2.09 | yes | 11.180x | 0.609x | 0.054x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,339.2 | 238.4-238.4 | 70.03 | **no** | `a100_sxm_80gb-x335-hybrid` | 211.7 | 376.5-376.5 | 2.81 | yes | 15.773x | 0.633x | 0.040x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,751.4 | 260.5-260.5 | 72.02 | **no** | `a100_sxm_80gb-x672-hybrid` | 279.4 | 515.5-515.5 | 2.71 | yes | 13.426x | 0.505x | 0.038x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,287.6 | 112.7-112.7 | 57.11 | **no** | `a100_sxm_80gb-x335-hybrid` | 94.6 | 177.0-177.0 | 2.67 | yes | 13.615x | 0.637x | 0.047x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,390.2 | 128.4-128.4 | 93.11 | **no** | `a100_sxm_80gb-x672-hybrid` | 145.8 | 249.6-249.6 | 2.92 | yes | 16.389x | 0.514x | 0.031x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 455.4 | 120.2-120.2 | 18.94 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.2 | 49.4-49.4 | 3.76 | yes | 12.256x | 2.434x | 0.199x |
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 758.1 | 107.8-107.8 | 35.16 | **no** | `a100_sxm_80gb-x672-hybrid` | 58.5 | 115.9-115.9 | 2.52 | yes | 12.969x | 0.930x | 0.072x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.031x to 0.199x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 1,217.1-1,217.1 | 17.35 | **no** | `b200_sxm-x49-nvl72-tensor` | 701.4 | 3,016.3-3,016.3 | 1.16 | yes | 6.021x | 0.404x | 0.067x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 533.0-533.0 | 36.18 | **no** | `b200_sxm-x58-nvl72-tensor` | 704.0 | 3,042.2-3,042.2 | 1.16 | yes | 5.479x | 0.175x | 0.032x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 1,217.1-1,217.1 | 17.35 | **no** | `b200_sxm-x49-nvl72-tensor` | 691.5 | 2,826.1-2,826.1 | 1.22 | yes | 6.107x | 0.431x | 0.071x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 533.0-533.0 | 36.18 | **no** | `b200_sxm-x58-nvl72-tensor` | 694.8 | 2,856.4-2,856.4 | 1.22 | yes | 5.551x | 0.187x | 0.034x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 1,217.1-1,217.1 | 17.35 | **no** | `b200_sxm-x49-nvl72-tensor` | 672.8 | 2,516.7-2,516.7 | 1.34 | yes | 6.277x | 0.484x | 0.077x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 533.0-533.0 | 36.18 | **no** | `b200_sxm-x58-nvl72-tensor` | 677.4 | 2,552.9-2,552.9 | 1.33 | yes | 5.694x | 0.209x | 0.037x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 4,223.2 | 1,217.1-1,217.1 | 17.35 | **no** | `b200_sxm-x49-nvl72-tensor` | 639.3 | 2,089.9-2,089.9 | 1.53 | yes | 6.606x | 0.582x | 0.088x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 533.0-533.0 | 36.18 | **no** | `b200_sxm-x58-nvl72-tensor` | 645.9 | 2,125.0-2,125.0 | 1.52 | yes | 5.972x | 0.251x | 0.042x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 4,185.8 | 1,221.9-1,221.9 | 17.13 | **no** | `b200_sxm-x83-nvl72-hybrid` | 630.8 | 2,174.9-2,174.9 | 1.45 | yes | 6.636x | 0.562x | 0.085x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 3,857.0 | 533.0-533.0 | 36.18 | **no** | `b200_sxm-x58-hybrid` | 603.2 | 1,914.4-1,914.4 | 1.58 | yes | 6.395x | 0.278x | 0.044x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,120.6 | 1,244.2-1,244.2 | 16.56 | **no** | `b200_sxm-x173-nvl72-hybrid` | 628.8 | 2,169.4-2,169.4 | 1.45 | yes | 6.553x | 0.574x | 0.088x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 3,820.4 | 697.4-697.4 | 27.39 | **no** | `b200_sxm-x116-nvl72-hybrid` | 608.9 | 2,004.5-2,004.5 | 1.52 | yes | 6.275x | 0.348x | 0.055x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,097.3 | 656.9-656.9 | 31.19 | **no** | `b200_sxm-x173-nvl72-hybrid` | 583.0 | 1,825.3-1,825.3 | 1.60 | yes | 7.028x | 0.360x | 0.051x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,820.4 | 697.4-697.4 | 27.39 | **no** | `b200_sxm-x231-nvl72-hybrid` | 601.3 | 1,925.7-1,925.7 | 1.56 | yes | 6.354x | 0.362x | 0.057x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,564.5 | 325.7-325.7 | 54.72 | **no** | `b200_sxm-x173-nvl72-hybrid` | 414.3 | 1,013.7-1,013.7 | 2.04 | yes | 8.604x | 0.321x | 0.037x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,659.2 | 356.9-356.9 | 51.26 | **no** | `b200_sxm-x347-nvl72-hybrid` | 501.3 | 1,358.8-1,358.8 | 1.84 | yes | 7.299x | 0.263x | 0.036x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,477.7 | 152.9-152.9 | 48.32 | **no** | `b200_sxm-x173-nvl72-hybrid` | 233.3 | 430.1-430.1 | 2.71 | yes | 6.333x | 0.355x | 0.056x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,614.0 | 175.8-175.8 | 74.34 | **no** | `b200_sxm-x347-nvl72-hybrid` | 302.6 | 685.5-685.5 | 2.21 | yes | 8.638x | 0.256x | 0.030x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 434.5 | 127.1-127.1 | 17.09 | **no** | `b200_sxm-x173-nvl72-hybrid` | 130.7 | 143.6-143.6 | 4.55 | yes | 3.325x | 0.886x | 0.266x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 871.3 | 144.5-144.5 | 30.15 | **no** | `b200_sxm-x347-nvl72-hybrid` | 159.6 | 202.5-202.5 | 3.94 | yes | 5.461x | 0.713x | 0.131x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.030x to 0.266x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-deepseek-v41-flash-engram-host`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 1,558.6-1,558.6 | 13.40 | **no** | `a100_sxm_80gb-x136-hybrid` | 369.6 | 1,048.0-1,048.0 | 1.76 | yes | 11.302x | 1.487x | 0.132x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 691.9-691.9 | 26.56 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 10.004x | 0.672x | 0.067x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 1,558.6-1,558.6 | 13.40 | **no** | `a100_sxm_80gb-x136-hybrid` | 369.6 | 1,048.0-1,048.0 | 1.76 | yes | 11.302x | 1.487x | 0.132x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 691.9-691.9 | 26.56 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 10.004x | 0.672x | 0.067x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 1,558.6-1,558.6 | 13.40 | **no** | `a100_sxm_80gb-x136-hybrid` | 369.6 | 1,048.0-1,048.0 | 1.76 | yes | 11.302x | 1.487x | 0.132x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 691.9-691.9 | 26.56 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 10.004x | 0.672x | 0.067x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 4,177.1 | 1,558.6-1,558.6 | 13.40 | **no** | `a100_sxm_80gb-x136-hybrid` | 369.6 | 1,048.0-1,048.0 | 1.76 | yes | 11.302x | 1.487x | 0.132x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 691.9-691.9 | 26.56 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 10.004x | 0.672x | 0.067x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 4,159.2 | 877.1-877.1 | 23.71 | **no** | `a100_sxm_80gb-x132-hybrid` | 366.0 | 1,031.9-1,031.9 | 1.77 | yes | 11.365x | 0.850x | 0.075x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,676.3 | 691.9-691.9 | 26.56 | **no** | `a100_sxm_80gb-x168-hybrid` | 367.5 | 1,029.0-1,029.0 | 1.79 | yes | 10.004x | 0.672x | 0.067x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 4,087.6 | 916.1-916.1 | 22.31 | **no** | `a100_sxm_80gb-x272-hybrid` | 360.8 | 954.3-954.3 | 1.89 | yes | 11.329x | 0.960x | 0.085x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,614.5 | 977.4-977.4 | 18.49 | **no** | `a100_sxm_80gb-x448-hybrid` | 357.8 | 884.0-884.0 | 2.02 | yes | 10.102x | 1.106x | 0.109x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 3,996.0 | 478.7-478.7 | 41.74 | **no** | `a100_sxm_80gb-x272-hybrid` | 321.9 | 734.3-734.3 | 2.19 | yes | 12.415x | 0.652x | 0.053x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,613.1 | 972.1-972.1 | 18.58 | **no** | `a100_sxm_80gb-x672-hybrid` | 357.8 | 829.9-829.9 | 2.16 | yes | 10.098x | 1.171x | 0.116x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,081.4 | 236.2-236.2 | 65.22 | **no** | `a100_sxm_80gb-x335-hybrid` | 210.7 | 375.8-375.8 | 2.80 | yes | 14.625x | 0.629x | 0.043x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,261.1 | 495.5-495.5 | 32.91 | **no** | `a100_sxm_80gb-x672-hybrid` | 278.5 | 514.8-514.8 | 2.70 | yes | 11.709x | 0.962x | 0.082x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 1,178.4 | 163.6-163.6 | 36.02 | **no** | `a100_sxm_80gb-x335-hybrid` | 93.8 | 176.4-176.4 | 2.66 | yes | 12.568x | 0.927x | 0.074x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,969.2 | 127.0-127.0 | 77.51 | **no** | `a100_sxm_80gb-x672-hybrid` | 144.9 | 249.0-249.0 | 2.91 | yes | 13.592x | 0.510x | 0.038x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 428.5 | 114.1-114.1 | 18.77 | **no** | `a100_sxm_80gb-x335-hybrid` | 36.7 | 48.2-48.2 | 3.80 | yes | 11.688x | 2.368x | 0.203x |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 602.2 | 104.5-104.5 | 28.81 | **no** | `a100_sxm_80gb-x672-hybrid` | 57.8 | 115.4-115.4 | 2.51 | yes | 10.411x | 0.906x | 0.087x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.038x to 0.203x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-kimi-k3`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | 1,435.6 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 288.3 | not applicable | -- | -- | 4.979x | -- | -- |
| Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 1,096.0 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 288.4 | not applicable | -- | -- | 3.800x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,328.5 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 288.4 | not applicable | -- | -- | 4.606x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,043.1 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 286.0 | not applicable | -- | -- | 3.647x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,328.5 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 286.0 | not applicable | -- | -- | 4.645x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,043.1 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 286.0 | not applicable | -- | -- | 3.647x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,307.3 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 276.9 | not applicable | -- | -- | 4.721x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,043.1 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 284.8 | not applicable | -- | -- | 3.662x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 1,159.6 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 260.6 | not applicable | -- | -- | 4.450x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,043.1 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 275.6 | not applicable | -- | -- | 3.785x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 914.1 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 234.2 | not applicable | -- | -- | 3.902x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1,043.1 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 259.0 | not applicable | -- | -- | 4.027x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 581.8 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 197.6 | not applicable | -- | -- | 2.945x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 976.3 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 232.1 | not applicable | -- | -- | 4.207x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 176.4 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 117.0 | not applicable | -- | -- | 1.507x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 487.7 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 152.2 | not applicable | -- | -- | 3.205x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 45.9 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 58.0 | not applicable | -- | -- | 0.791x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 144.3 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 78.2 | not applicable | -- | -- | 1.844x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 11.5 | not applicable | -- | -- | `b200_sxm-x202-nvl72-hybrid` | 25.1 | not applicable | -- | -- | 0.458x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 36.9 | not applicable | -- | -- | `b200_sxm-x462-nvl72-hybrid` | 36.7 | not applicable | -- | -- | 1.006x | -- | -- |

### `n6_vs_a100-kimi-k3`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x398` | 1,096.9 | not applicable | -- | -- | `a100_sxm_80gb-x393-hybrid` | 108.2 | not applicable | -- | -- | 10.133x | -- | -- |
| Kimi-K3 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x10` | 1,003.7 | not applicable | -- | -- | `a100_sxm_80gb-x560-hybrid` | 109.7 | not applicable | -- | -- | 9.148x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 888.6 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 108.3 | not applicable | -- | -- | 8.206x | -- | -- |
| Kimi-K3 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 814.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 108.3 | not applicable | -- | -- | 7.517x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 888.6 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 108.3 | not applicable | -- | -- | 8.206x | -- | -- |
| Kimi-K3 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 814.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 108.3 | not applicable | -- | -- | 7.517x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 812.6 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 106.8 | not applicable | -- | -- | 7.610x | -- | -- |
| Kimi-K3 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 814.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 108.3 | not applicable | -- | -- | 7.517x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 601.6 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 96.0 | not applicable | -- | -- | 6.266x | -- | -- |
| Kimi-K3 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 814.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 108.3 | not applicable | -- | -- | 7.517x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 372.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 82.3 | not applicable | -- | -- | 4.525x | -- | -- |
| Kimi-K3 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 814.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 101.8 | not applicable | -- | -- | 8.001x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 205.8 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 67.0 | not applicable | -- | -- | 3.074x | -- | -- |
| Kimi-K3 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 666.5 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 87.7 | not applicable | -- | -- | 7.601x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 55.3 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 39.4 | not applicable | -- | -- | 1.405x | -- | -- |
| Kimi-K3 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 288.1 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 58.1 | not applicable | -- | -- | 4.957x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 14.0 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 16.8 | not applicable | -- | -- | 0.832x | -- | -- |
| Kimi-K3 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 81.6 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 32.3 | not applicable | -- | -- | 2.528x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 3.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 6.6 | not applicable | -- | -- | 0.528x | -- | -- |
| Kimi-K3 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x22` | 20.8 | not applicable | -- | -- | `a100_sxm_80gb-x1231-hybrid` | 12.8 | not applicable | -- | -- | 1.624x | -- | -- |

### `n5_vs_b200-kimi-k3-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x383` | 949.7 | not applicable | -- | -- | `b200_sxm-x195-nvl72-hybrid` | 285.4 | not applicable | -- | -- | 3.328x | -- | -- |
| Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | 894.0 | not applicable | -- | -- | `b200_sxm-x520-nvl72-hybrid` | 283.0 | not applicable | -- | -- | 3.159x | -- | -- |
| Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 717.5 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | not applicable | -- | -- | 2.599x | -- | -- |
| Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 717.5 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | not applicable | -- | -- | 2.599x | -- | -- |
| Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 717.5 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | not applicable | -- | -- | 2.599x | -- | -- |
| Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 717.5 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | not applicable | -- | -- | 2.599x | -- | -- |
| Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 717.5 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 273.9 | not applicable | -- | -- | 2.620x | -- | -- |
| Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 717.5 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 257.6 | not applicable | -- | -- | 2.786x | -- | -- |
| Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 460.3 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 196.9 | not applicable | -- | -- | 2.338x | -- | -- |
| Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 149.9 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 120.5 | not applicable | -- | -- | 1.244x | -- | -- |
| Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x68` | 39.3 | not applicable | -- | -- | `b200_sxm-x1965-nvl72-hybrid` | 49.4 | not applicable | -- | -- | 0.795x | -- | -- |

### `n6_vs_a100-kimi-k3-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 724.4 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 106.9 | not applicable | -- | -- | 6.775x | -- | -- |
| Kimi-K3 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x23` | 788.1 | not applicable | -- | -- | `a100_sxm_80gb-x1287-hybrid` | 106.9 | not applicable | -- | -- | 7.375x | -- | -- |
| Kimi-K3 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 553.2 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 100.9 | not applicable | -- | -- | 5.482x | -- | -- |
| Kimi-K3 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 553.2 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 100.9 | not applicable | -- | -- | 5.482x | -- | -- |
| Kimi-K3 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 553.2 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 100.9 | not applicable | -- | -- | 5.482x | -- | -- |
| Kimi-K3 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 553.2 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 100.9 | not applicable | -- | -- | 5.482x | -- | -- |
| Kimi-K3 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 518.3 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 100.9 | not applicable | -- | -- | 5.136x | -- | -- |
| Kimi-K3 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 498.2 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 100.9 | not applicable | -- | -- | 4.937x | -- | -- |
| Kimi-K3 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 280.7 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 81.1 | not applicable | -- | -- | 3.463x | -- | -- |
| Kimi-K3 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 86.3 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 55.1 | not applicable | -- | -- | 1.567x | -- | -- |
| Kimi-K3 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 22.4 | not applicable | -- | -- | `a100_sxm_80gb-x5316-hybrid` | 28.7 | not applicable | -- | -- | 0.779x | -- | -- |

### `n5_vs_b200-kimi-k3-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,940.4 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 288.8 | not applicable | -- | -- | 6.718x | -- | -- |
| Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 1,462.3 | not applicable | -- | -- | `b200_sxm-x231-nvl72-hybrid` | 284.3 | not applicable | -- | -- | 5.143x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,940.4 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 288.8 | not applicable | -- | -- | 6.718x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 1,462.3 | not applicable | -- | -- | `b200_sxm-x231-nvl72-hybrid` | 284.3 | not applicable | -- | -- | 5.143x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,940.4 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 286.6 | not applicable | -- | -- | 6.771x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 1,462.3 | not applicable | -- | -- | `b200_sxm-x231-nvl72-hybrid` | 284.3 | not applicable | -- | -- | 5.143x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,940.4 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 278.0 | not applicable | -- | -- | 6.980x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 1,462.3 | not applicable | -- | -- | `b200_sxm-x231-nvl72-hybrid` | 276.9 | not applicable | -- | -- | 5.281x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,940.4 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 262.6 | not applicable | -- | -- | 7.388x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 1,462.3 | not applicable | -- | -- | `b200_sxm-x231-nvl72-hybrid` | 263.4 | not applicable | -- | -- | 5.552x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,741.2 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 237.6 | not applicable | -- | -- | 7.328x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 1,462.3 | not applicable | -- | -- | `b200_sxm-x231-nvl72-hybrid` | 240.7 | not applicable | -- | -- | 6.075x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 1,506.6 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 202.5 | not applicable | -- | -- | 7.441x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,444.2 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 225.8 | not applicable | -- | -- | 6.396x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x395` | 720.8 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 124.3 | not applicable | -- | -- | 5.797x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 996.8 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 144.8 | not applicable | -- | -- | 6.882x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 219.7 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 65.9 | not applicable | -- | -- | 3.333x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 369.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 77.5 | not applicable | -- | -- | 4.758x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x395` | 57.8 | not applicable | -- | -- | `b200_sxm-x201-nvl72-hybrid` | 33.4 | not applicable | -- | -- | 1.729x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 99.2 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 39.6 | not applicable | -- | -- | 2.507x | -- | -- |

### `n6_vs_a100-kimi-k3-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Kimi-K3 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,390.0 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 108.6 | not applicable | -- | -- | 12.797x | -- | -- |
| Kimi-K3 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 1,198.4 | not applicable | -- | -- | `a100_sxm_80gb-x392-hybrid` | 108.5 | not applicable | -- | -- | 11.041x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,390.0 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 108.6 | not applicable | -- | -- | 12.797x | -- | -- |
| Kimi-K3 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 1,198.4 | not applicable | -- | -- | `a100_sxm_80gb-x392-hybrid` | 108.5 | not applicable | -- | -- | 11.041x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,390.0 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 108.6 | not applicable | -- | -- | 12.797x | -- | -- |
| Kimi-K3 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 1,198.4 | not applicable | -- | -- | `a100_sxm_80gb-x392-hybrid` | 108.5 | not applicable | -- | -- | 11.041x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,390.0 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 107.1 | not applicable | -- | -- | 12.974x | -- | -- |
| Kimi-K3 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 1,198.4 | not applicable | -- | -- | `a100_sxm_80gb-x392-hybrid` | 107.1 | not applicable | -- | -- | 11.194x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,256.9 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 96.6 | not applicable | -- | -- | 13.008x | -- | -- |
| Kimi-K3 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 1,198.4 | not applicable | -- | -- | `a100_sxm_80gb-x392-hybrid` | 96.5 | not applicable | -- | -- | 12.413x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 1,073.5 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 83.2 | not applicable | -- | -- | 12.900x | -- | -- |
| Kimi-K3 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,195.1 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 92.2 | not applicable | -- | -- | 12.958x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 744.7 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 68.1 | not applicable | -- | -- | 10.928x | -- | -- |
| Kimi-K3 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,018.1 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 79.0 | not applicable | -- | -- | 12.887x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 249.8 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 41.1 | not applicable | -- | -- | 6.082x | -- | -- |
| Kimi-K3 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 529.6 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 49.3 | not applicable | -- | -- | 10.734x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 66.6 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 18.1 | not applicable | -- | -- | 3.686x | -- | -- |
| Kimi-K3 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 159.3 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 23.7 | not applicable | -- | -- | 6.708x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 16.8 | not applicable | -- | -- | `a100_sxm_80gb-x394-hybrid` | 7.4 | not applicable | -- | -- | 2.253x | -- | -- |
| Kimi-K3 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 40.9 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 9.2 | not applicable | -- | -- | 4.468x | -- | -- |

### `n5_vs_b200-mimo-v26-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | 5,431.5 | 3,276.8-3,276.8 | 8.29 | **no** | `b200_sxm-x23-nvl72-tensor` | 713.1 | 2,994.0-2,994.0 | 1.19 | yes | 7.617x | 1.094x | 0.144x |
| MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3,419.6 | 1,729.3-1,729.3 | 9.89 | **no** | `b200_sxm-x58-nvl72-tensor` | 750.5 | 3,347.1-3,347.1 | 1.12 | yes | 4.556x | 0.517x | 0.113x |
| MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,825.9 | 1,220.8-1,220.8 | 19.76 | **no** | `b200_sxm-x192-nvl72-hybrid` | 749.3 | 3,373.3-3,373.3 | 1.11 | yes | 6.440x | 0.362x | 0.056x |
| MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 2,054.1 | 682.3-682.3 | 15.05 | **no** | `b200_sxm-x636-nvl72-hybrid` | 744.2 | 3,359.8-3,359.8 | 1.11 | yes | 2.760x | 0.203x | 0.074x |
| MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,825.9 | 1,220.8-1,220.8 | 19.76 | **no** | `b200_sxm-x192-nvl72-hybrid` | 744.3 | 3,314.9-3,314.9 | 1.12 | yes | 6.484x | 0.368x | 0.057x |
| MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 2,054.1 | 682.3-682.3 | 15.05 | **no** | `b200_sxm-x636-nvl72-hybrid` | 744.2 | 3,359.8-3,359.8 | 1.11 | yes | 2.760x | 0.203x | 0.074x |
| MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,825.9 | 1,220.8-1,220.8 | 19.76 | **no** | `b200_sxm-x192-nvl72-hybrid` | 725.2 | 3,131.0-3,131.0 | 1.16 | yes | 6.654x | 0.390x | 0.059x |
| MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 2,054.1 | 682.3-682.3 | 15.05 | **no** | `b200_sxm-x636-nvl72-hybrid` | 744.2 | 3,359.8-3,359.8 | 1.11 | yes | 2.760x | 0.203x | 0.074x |
| MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x282` | 4,661.0 | 841.2-841.2 | 27.70 | **no** | `b200_sxm-x144-nvl72-hybrid` | 671.4 | 2,650.9-2,650.9 | 1.27 | yes | 6.942x | 0.317x | 0.046x |
| MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 2,054.1 | 682.3-682.3 | 15.05 | **no** | `b200_sxm-x636-nvl72-hybrid` | 733.3 | 3,232.3-3,232.3 | 1.13 | yes | 2.801x | 0.211x | 0.075x |
| MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 4,058.7 | 634.1-634.1 | 32.00 | **no** | `b200_sxm-x192-nvl72-hybrid` | 633.4 | 2,414.6-2,414.6 | 1.31 | yes | 6.408x | 0.263x | 0.041x |
| MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 1,928.7 | 398.9-398.9 | 24.18 | **no** | `b200_sxm-x636-nvl72-hybrid` | 710.0 | 2,992.9-2,992.9 | 1.19 | yes | 2.716x | 0.133x | 0.049x |
| MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 2,953.7 | 331.2-331.2 | 44.59 | **no** | `b200_sxm-x192-nvl72-hybrid` | 550.0 | 1,918.6-1,918.6 | 1.43 | yes | 5.370x | 0.173x | 0.032x |
| MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 1,487.3 | 392.1-392.1 | 18.97 | **no** | `b200_sxm-x636-nvl72-hybrid` | 668.9 | 2,639.9-2,639.9 | 1.27 | yes | 2.223x | 0.149x | 0.067x |
| MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 951.4 | 433.2-433.2 | 10.98 | **no** | `b200_sxm-x192-nvl72-hybrid` | 339.1 | 909.8-909.8 | 1.86 | yes | 2.806x | 0.476x | 0.170x |
| MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 579.1 | 100.9-100.9 | 28.71 | **no** | `b200_sxm-x636-nvl72-hybrid` | 512.4 | 1,605.3-1,605.3 | 1.60 | yes | 1.130x | 0.063x | 0.056x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 238.5 | 224.3-224.3 | 5.32 | **no** | `b200_sxm-x192-nvl72-hybrid` | 152.4 | 433.8-433.8 | 1.76 | yes | 1.565x | 0.517x | 0.330x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 158.6 | 25.3-25.3 | 31.32 | **no** | `b200_sxm-x636-nvl72-hybrid` | 297.9 | 688.0-688.0 | 2.16 | yes | 0.532x | 0.037x | 0.069x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 59.7 | 76.2-76.2 | 3.92 | yes | `b200_sxm-x192-nvl72-hybrid` | 51.4 | 171.2-171.2 | 1.50 | yes | 1.162x | 0.445x | 0.383x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x22` | 40.2 | 12.3-12.3 | 16.38 | **no** | `b200_sxm-x636-nvl72-hybrid` | 128.8 | 321.3-321.3 | 2.00 | yes | 0.312x | 0.038x | 0.122x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.032x to 0.383x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 1 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x64` | 5,205.6 | 2,666.7-2,666.7 | 9.76 | **no** | `a100_sxm_80gb-x63-hybrid` | 331.6 | 1,047.1-1,047.1 | 1.58 | yes | 15.699x | 2.547x | 0.162x |
| MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 3,418.9 | 1,688.5-1,688.5 | 10.12 | **no** | `a100_sxm_80gb-x112-tensor` | 338.7 | 1,176.4-1,176.4 | 1.44 | yes | 10.095x | 1.435x | 0.142x |
| MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3,921.8 | 1,929.9-1,929.9 | 10.16 | **no** | `a100_sxm_80gb-x391-hybrid` | 327.2 | 1,145.2-1,145.2 | 1.43 | yes | 11.985x | 1.685x | 0.141x |
| MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,573.2 | 1,548.5-1,548.5 | 5.08 | **no** | `a100_sxm_80gb-x1735-hybrid` | 323.9 | 1,139.6-1,139.6 | 1.42 | yes | 4.856x | 1.359x | 0.280x |
| MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3,921.8 | 1,929.9-1,929.9 | 10.16 | **no** | `a100_sxm_80gb-x391-hybrid` | 327.2 | 1,145.2-1,145.2 | 1.43 | yes | 11.985x | 1.685x | 0.141x |
| MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,573.2 | 1,548.5-1,548.5 | 5.08 | **no** | `a100_sxm_80gb-x1735-hybrid` | 323.9 | 1,139.6-1,139.6 | 1.42 | yes | 4.856x | 1.359x | 0.280x |
| MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x287` | 3,878.5 | 1,559.5-1,559.5 | 12.43 | **no** | `a100_sxm_80gb-x283-hybrid` | 324.2 | 1,120.0-1,120.0 | 1.45 | yes | 11.961x | 1.393x | 0.116x |
| MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,573.2 | 1,548.5-1,548.5 | 5.08 | **no** | `a100_sxm_80gb-x1735-hybrid` | 323.9 | 1,139.6-1,139.6 | 1.42 | yes | 4.856x | 1.359x | 0.280x |
| MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 3,429.1 | 1,110.7-1,110.7 | 15.44 | **no** | `a100_sxm_80gb-x391-hybrid` | 323.4 | 1,131.3-1,131.3 | 1.43 | yes | 10.605x | 0.982x | 0.093x |
| MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,469.8 | 487.6-487.6 | 15.07 | **no** | `a100_sxm_80gb-x1735-hybrid` | 323.9 | 1,139.6-1,139.6 | 1.42 | yes | 4.537x | 0.428x | 0.094x |
| MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 2,667.5 | 605.8-605.8 | 22.02 | **no** | `a100_sxm_80gb-x391-hybrid` | 323.4 | 1,131.3-1,131.3 | 1.43 | yes | 8.249x | 0.536x | 0.065x |
| MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,441.4 | 486.4-486.4 | 14.82 | **no** | `a100_sxm_80gb-x1735-hybrid` | 323.6 | 1,240.1-1,240.1 | 1.30 | yes | 4.454x | 0.392x | 0.088x |
| MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,680.0 | 309.9-309.9 | 27.10 | **no** | `a100_sxm_80gb-x391-hybrid` | 301.0 | 1,025.0-1,025.0 | 1.47 | yes | 5.581x | 0.302x | 0.054x |
| MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 1,043.0 | 279.8-279.8 | 18.64 | **no** | `a100_sxm_80gb-x1735-hybrid` | 323.6 | 1,240.1-1,240.1 | 1.30 | yes | 3.223x | 0.226x | 0.070x |
| MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 504.3 | 79.1-79.1 | 31.87 | **no** | `a100_sxm_80gb-x391-hybrid` | 162.2 | 533.4-533.4 | 1.52 | yes | 3.109x | 0.148x | 0.048x |
| MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 348.5 | 71.1-71.1 | 24.51 | **no** | `a100_sxm_80gb-x1735-hybrid` | 310.1 | 1,152.7-1,152.7 | 1.35 | yes | 1.124x | 0.062x | 0.055x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 131.1 | 38.2-38.2 | 17.17 | **no** | `a100_sxm_80gb-x391-hybrid` | 62.0 | 220.7-220.7 | 1.41 | yes | 2.113x | 0.173x | 0.082x |
| MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 91.8 | 17.8-17.8 | 25.76 | **no** | `a100_sxm_80gb-x1735-hybrid` | 172.4 | 584.9-584.9 | 1.47 | yes | 0.533x | 0.030x | 0.057x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 33.0 | 31.3-31.3 | 5.29 | **no** | `a100_sxm_80gb-x391-hybrid` | 22.2 | 65.6-65.6 | 1.69 | yes | 1.492x | 0.477x | 0.319x |
| MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x31` | 23.1 | 8.6-8.6 | 13.47 | **no** | `a100_sxm_80gb-x1735-hybrid` | 67.0 | 247.8-247.8 | 1.35 | yes | 0.345x | 0.035x | 0.100x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.048x to 0.319x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 4,383.4 | 2,566.4-2,566.4 | 8.54 | **no** | `b200_sxm-x53-nvl72-tensor` | 719.2 | 3,209.4-3,209.4 | 1.12 | yes | 6.095x | 0.800x | 0.131x |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3,406.7 | 1,544.6-1,544.6 | 11.03 | **no** | `b200_sxm-x58-nvl72-tensor` | 723.9 | 3,240.7-3,240.7 | 1.12 | yes | 4.706x | 0.477x | 0.101x |
| MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,382.5 | 531.2-531.2 | 13.01 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 3,052.8-3,052.8 | 1.12 | yes | 2.018x | 0.174x | 0.086x |
| MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,382.5 | 531.2-531.2 | 13.01 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 3,052.8-3,052.8 | 1.12 | yes | 2.018x | 0.174x | 0.086x |
| MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,382.5 | 531.2-531.2 | 13.01 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 3,052.8-3,052.8 | 1.12 | yes | 2.018x | 0.174x | 0.086x |
| MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,382.5 | 531.2-531.2 | 13.01 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 3,052.8-3,052.8 | 1.12 | yes | 2.018x | 0.174x | 0.086x |
| MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,332.1 | 528.3-528.3 | 12.61 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 3,052.8-3,052.8 | 1.12 | yes | 1.945x | 0.173x | 0.089x |
| MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 1,073.9 | 279.8-279.8 | 19.19 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 670.2 | 2,916.3-2,916.3 | 1.15 | yes | 1.602x | 0.096x | 0.060x |
| MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 543.8 | 81.5-81.5 | 33.35 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 565.7 | 2,400.0-2,400.0 | 1.18 | yes | 0.961x | 0.034x | 0.035x |
| MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 156.3 | 20.6-20.6 | 38.01 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 351.3 | 1,478.4-1,478.4 | 1.19 | yes | 0.445x | 0.014x | 0.031x |
| MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 40.0 | 5.1-5.1 | 38.89 | **no** | `b200_sxm-x3149-nvl72-hybrid` | 144.8 | 534.2-534.2 | 1.36 | yes | 0.276x | 0.010x | 0.035x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.031x to 0.131x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | 4,215.1 | 2,126.9-2,126.9 | 9.91 | **no** | `a100_sxm_80gb-x139-tensor` | 331.5 | 1,161.1-1,161.1 | 1.43 | yes | 12.716x | 1.832x | 0.144x |
| MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 3,075.4 | 1,160.8-1,160.8 | 13.25 | **no** | `a100_sxm_80gb-x168-tensor` | 334.3 | 1,170.5-1,170.5 | 1.43 | yes | 9.198x | 0.992x | 0.108x |
| MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 1,090.2 | 3,247.8-3,247.8 | 1.68 | yes | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 1,086.0-1,086.0 | 1.39 | yes | 3.602x | 2.991x | 0.830x |
| MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,033.2 | 384.6-384.6 | 13.43 | **no** | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 1,086.0-1,086.0 | 1.39 | yes | 3.413x | 0.354x | 0.104x |
| MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,033.2 | 384.6-384.6 | 13.43 | **no** | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 1,086.0-1,086.0 | 1.39 | yes | 3.413x | 0.354x | 0.104x |
| MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,033.2 | 384.6-384.6 | 13.43 | **no** | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 1,086.0-1,086.0 | 1.39 | yes | 3.413x | 0.354x | 0.104x |
| MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 1,033.2 | 384.6-384.6 | 13.43 | **no** | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 1,086.0-1,086.0 | 1.39 | yes | 3.413x | 0.354x | 0.104x |
| MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 808.6 | 375.0-375.0 | 10.78 | **no** | `a100_sxm_80gb-x8562-hybrid` | 302.7 | 1,086.0-1,086.0 | 1.39 | yes | 2.671x | 0.345x | 0.129x |
| MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 325.4 | 100.0-100.0 | 16.28 | **no** | `a100_sxm_80gb-x8562-hybrid` | 275.8 | 1,033.4-1,033.4 | 1.33 | yes | 1.180x | 0.097x | 0.082x |
| MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 90.2 | 28.2-28.2 | 16.01 | **no** | `a100_sxm_80gb-x8562-hybrid` | 222.9 | 993.4-993.4 | 1.12 | yes | 0.405x | 0.028x | 0.070x |
| MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 22.9 | 7.1-7.1 | 16.24 | **no** | `a100_sxm_80gb-x8562-hybrid` | 95.2 | 390.7-390.7 | 1.22 | yes | 0.241x | 0.018x | 0.075x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.070x to 0.830x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 1 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,200.0 | 2,169.7-2,169.7 | 16.59 | **no** | `b200_sxm-x61-nvl72-tensor` | 758.2 | 3,384.7-3,384.7 | 1.12 | yes | 9.497x | 0.641x | 0.068x |
| MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4,579.3 | 1,013.0-1,013.0 | 22.60 | **no** | `b200_sxm-x58-nvl72-tensor` | 757.2 | 3,373.7-3,373.7 | 1.12 | yes | 6.048x | 0.300x | 0.050x |
| MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,200.0 | 2,169.7-2,169.7 | 16.59 | **no** | `b200_sxm-x61-nvl72-tensor` | 748.9 | 3,246.5-3,246.5 | 1.15 | yes | 9.614x | 0.668x | 0.070x |
| MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4,579.3 | 1,013.0-1,013.0 | 22.60 | **no** | `b200_sxm-x58-nvl72-tensor` | 747.6 | 3,231.8-3,231.8 | 1.16 | yes | 6.126x | 0.313x | 0.051x |
| MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,200.0 | 2,169.7-2,169.7 | 16.59 | **no** | `b200_sxm-x61-nvl72-tensor` | 731.6 | 3,012.3-3,012.3 | 1.21 | yes | 9.842x | 0.720x | 0.073x |
| MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4,579.3 | 1,013.0-1,013.0 | 22.60 | **no** | `b200_sxm-x58-nvl72-tensor` | 729.7 | 2,993.2-2,993.2 | 1.22 | yes | 6.276x | 0.338x | 0.054x |
| MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 7,200.0 | 2,169.7-2,169.7 | 16.59 | **no** | `b200_sxm-x61-nvl72-tensor` | 701.4 | 2,692.7-2,692.7 | 1.30 | yes | 10.266x | 0.806x | 0.078x |
| MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 4,579.3 | 1,013.0-1,013.0 | 22.60 | **no** | `b200_sxm-x58-nvl72-tensor` | 698.5 | 2,671.1-2,671.1 | 1.31 | yes | 6.556x | 0.379x | 0.058x |
| MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 7,132.9 | 2,101.3-2,101.3 | 16.97 | **no** | `b200_sxm-x87-nvl72-hybrid` | 676.9 | 2,553.8-2,553.8 | 1.33 | yes | 10.538x | 0.823x | 0.078x |
| MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 4,533.9 | 2,169.7-2,169.7 | 10.45 | **no** | `b200_sxm-x87-nvl72-hybrid` | 676.9 | 2,553.8-2,553.8 | 1.33 | yes | 6.699x | 0.850x | 0.127x |
| MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7,024.5 | 2,140.3-2,140.3 | 16.41 | **no** | `b200_sxm-x173-nvl72-hybrid` | 675.7 | 2,517.3-2,517.3 | 1.34 | yes | 10.396x | 0.850x | 0.082x |
| MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 4,454.8 | 2,208.2-2,208.2 | 10.09 | **no** | `b200_sxm-x173-nvl72-hybrid` | 675.7 | 2,517.3-2,517.3 | 1.34 | yes | 6.593x | 0.877x | 0.133x |
| MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,985.7 | 1,140.3-1,140.3 | 30.63 | **no** | `b200_sxm-x173-nvl72-hybrid` | 619.2 | 2,069.7-2,069.7 | 1.50 | yes | 11.282x | 0.551x | 0.049x |
| MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,430.1 | 2,206.9-2,206.9 | 10.04 | **no** | `b200_sxm-x347-nvl72-hybrid` | 671.7 | 2,431.8-2,431.8 | 1.38 | yes | 6.595x | 0.908x | 0.138x |
| MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,676.4 | 559.9-559.9 | 41.76 | **no** | `b200_sxm-x173-nvl72-hybrid` | 479.3 | 1,079.3-1,079.3 | 2.22 | yes | 9.756x | 0.519x | 0.053x |
| MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,616.0 | 1,154.5-1,154.5 | 15.66 | **no** | `b200_sxm-x347-nvl72-hybrid` | 545.1 | 1,409.0-1,409.0 | 1.93 | yes | 6.634x | 0.819x | 0.124x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,851.5 | 256.5-256.5 | 36.09 | **no** | `b200_sxm-x173-nvl72-hybrid` | 329.6 | 626.6-626.6 | 2.63 | yes | 5.617x | 0.409x | 0.073x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,605.5 | 304.4-304.4 | 26.37 | **no** | `b200_sxm-x347-nvl72-hybrid` | 388.1 | 611.1-611.1 | 3.18 | yes | 4.137x | 0.498x | 0.120x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 527.7 | 164.8-164.8 | 16.01 | **no** | `b200_sxm-x173-nvl72-hybrid` | 195.2 | 316.0-316.0 | 3.09 | yes | 2.704x | 0.522x | 0.193x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 451.7 | 237.3-237.3 | 9.52 | **no** | `b200_sxm-x347-nvl72-hybrid` | 242.8 | 306.4-306.4 | 3.96 | yes | 1.860x | 0.775x | 0.416x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.049x to 0.416x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,900.9 | 1,569.8-1,569.8 | 21.98 | **no** | `a100_sxm_80gb-x77-hybrid` | 369.9 | 1,123.9-1,123.9 | 1.65 | yes | 18.654x | 1.397x | 0.075x |
| MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,786.0 | 1,334.7-1,334.7 | 14.18 | **no** | `a100_sxm_80gb-x168-hybrid` | 371.6 | 1,199.6-1,199.6 | 1.55 | yes | 10.189x | 1.113x | 0.109x |
| MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,900.9 | 1,569.8-1,569.8 | 21.98 | **no** | `a100_sxm_80gb-x77-hybrid` | 369.9 | 1,123.9-1,123.9 | 1.65 | yes | 18.654x | 1.397x | 0.075x |
| MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,786.0 | 1,334.7-1,334.7 | 14.18 | **no** | `a100_sxm_80gb-x168-hybrid` | 371.6 | 1,199.6-1,199.6 | 1.55 | yes | 10.189x | 1.113x | 0.109x |
| MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,900.9 | 1,569.8-1,569.8 | 21.98 | **no** | `a100_sxm_80gb-x77-hybrid` | 369.9 | 1,123.9-1,123.9 | 1.65 | yes | 18.654x | 1.397x | 0.075x |
| MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,786.0 | 1,334.7-1,334.7 | 14.18 | **no** | `a100_sxm_80gb-x168-hybrid` | 371.6 | 1,199.6-1,199.6 | 1.55 | yes | 10.189x | 1.113x | 0.109x |
| MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 6,900.9 | 1,569.8-1,569.8 | 21.98 | **no** | `a100_sxm_80gb-x77-hybrid` | 369.9 | 1,123.9-1,123.9 | 1.65 | yes | 18.654x | 1.397x | 0.075x |
| MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 3,786.0 | 1,334.7-1,334.7 | 14.18 | **no** | `a100_sxm_80gb-x168-hybrid` | 371.6 | 1,199.6-1,199.6 | 1.55 | yes | 10.189x | 1.113x | 0.109x |
| MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 6,845.1 | 1,568.5-1,568.5 | 21.82 | **no** | `a100_sxm_80gb-x154-hybrid` | 366.7 | 1,168.0-1,168.0 | 1.57 | yes | 18.665x | 1.343x | 0.072x |
| MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill` | 3,694.8 | 2,871.5-2,871.5 | 6.43 | **no** | `a100_sxm_80gb-x336-hybrid` | 364.9 | 1,225.7-1,225.7 | 1.49 | yes | 10.126x | 2.343x | 0.231x |
| MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,732.4 | 1,585.4-1,585.4 | 21.23 | **no** | `a100_sxm_80gb-x335-hybrid` | 364.5 | 1,223.7-1,223.7 | 1.49 | yes | 18.470x | 1.296x | 0.070x |
| MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,606.0 | 2,910.3-2,910.3 | 6.20 | **no** | `a100_sxm_80gb-x672-hybrid` | 363.0 | 1,258.4-1,258.4 | 1.44 | yes | 9.933x | 2.313x | 0.233x |
| MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,385.3 | 831.9-831.9 | 38.38 | **no** | `a100_sxm_80gb-x335-hybrid` | 337.9 | 1,064.2-1,064.2 | 1.59 | yes | 18.894x | 0.782x | 0.041x |
| MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,508.2 | 1,646.4-1,646.4 | 10.65 | **no** | `a100_sxm_80gb-x672-hybrid` | 363.0 | 1,258.4-1,258.4 | 1.44 | yes | 9.664x | 1.308x | 0.135x |
| MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,979.3 | 406.7-406.7 | 48.92 | **no** | `a100_sxm_80gb-x335-hybrid` | 212.3 | 605.9-605.9 | 1.75 | yes | 18.739x | 0.671x | 0.036x |
| MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,159.4 | 844.5-844.5 | 12.79 | **no** | `a100_sxm_80gb-x672-hybrid` | 279.3 | 839.4-839.4 | 1.66 | yes | 7.733x | 1.006x | 0.130x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,436.8 | 186.3-186.3 | 38.56 | **no** | `a100_sxm_80gb-x335-hybrid` | 101.5 | 301.4-301.4 | 1.68 | yes | 14.159x | 0.618x | 0.044x |
| MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 721.8 | 220.0-220.0 | 16.40 | **no** | `a100_sxm_80gb-x672-hybrid` | 148.4 | 432.1-432.1 | 1.72 | yes | 4.865x | 0.509x | 0.105x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 396.9 | 120.7-120.7 | 16.45 | **no** | `a100_sxm_80gb-x335-hybrid` | 56.2 | 119.3-119.3 | 2.36 | yes | 7.061x | 1.011x | 0.143x |
| MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 189.9 | 171.5-171.5 | 5.54 | **no** | `a100_sxm_80gb-x672-hybrid` | 71.9 | 207.3-207.3 | 1.73 | yes | 2.643x | 0.827x | 0.313x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.036x to 0.313x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | 3,083.8 | 2,003.4-2,003.4 | 7.70 | **no** | `b200_sxm-x71-nvl72-tensor` | 503.6 | 2,223.4-2,223.4 | 1.13 | yes | 6.124x | 0.901x | 0.147x |
| MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 2,362.7 | 1,181.9-1,181.9 | 10.00 | **no** | `b200_sxm-x87-nvl72-hybrid` | 485.8 | 2,085.5-2,085.5 | 1.16 | yes | 4.863x | 0.567x | 0.117x |
| MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,226.9 | 313.7-313.7 | 19.55 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 492.3 | 2,205.7-2,205.7 | 1.12 | yes | 2.492x | 0.142x | 0.057x |
| MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,226.9 | 313.7-313.7 | 19.55 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 492.3 | 2,205.7-2,205.7 | 1.12 | yes | 2.492x | 0.142x | 0.057x |
| MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,226.9 | 313.7-313.7 | 19.55 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 492.3 | 2,205.7-2,205.7 | 1.12 | yes | 2.492x | 0.142x | 0.057x |
| MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,226.9 | 313.7-313.7 | 19.55 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 492.3 | 2,205.7-2,205.7 | 1.12 | yes | 2.492x | 0.142x | 0.057x |
| MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,226.9 | 313.7-313.7 | 19.55 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 483.9 | 2,094.8-2,094.8 | 1.16 | yes | 2.535x | 0.150x | 0.059x |
| MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 1,099.2 | 310.9-310.9 | 17.68 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 463.2 | 1,880.3-1,880.3 | 1.23 | yes | 2.373x | 0.165x | 0.070x |
| MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 534.5 | 90.5-90.5 | 29.53 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 371.7 | 1,213.8-1,213.8 | 1.53 | yes | 1.438x | 0.075x | 0.052x |
| MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 156.9 | 22.8-22.8 | 34.42 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 221.5 | 533.1-533.1 | 2.08 | yes | 0.708x | 0.043x | 0.060x |
| MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x49` | 40.3 | 5.7-5.7 | 35.32 | **no** | `b200_sxm-x1416-nvl72-hybrid` | 99.0 | 260.8-260.8 | 1.90 | yes | 0.407x | 0.022x | 0.054x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.052x to 0.147x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | 3,002.6 | 1,711.9-1,711.9 | 8.77 | **no** | `a100_sxm_80gb-x178-tensor` | 224.9 | 710.0-710.0 | 1.58 | yes | 13.348x | 2.411x | 0.181x |
| MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 2,254.0 | 1,039.6-1,039.6 | 10.84 | **no** | `a100_sxm_80gb-x168-tensor` | 224.5 | 708.7-708.7 | 1.58 | yes | 10.040x | 1.467x | 0.146x |
| MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,011.9 | 783.2-783.2 | 6.46 | **no** | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 665.2-665.2 | 1.54 | yes | 4.936x | 1.177x | 0.239x |
| MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,011.9 | 783.2-783.2 | 6.46 | **no** | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 665.2-665.2 | 1.54 | yes | 4.936x | 1.177x | 0.239x |
| MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,011.9 | 783.2-783.2 | 6.46 | **no** | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 665.2-665.2 | 1.54 | yes | 4.936x | 1.177x | 0.239x |
| MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 1,011.9 | 783.2-783.2 | 6.46 | **no** | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 665.2-665.2 | 1.54 | yes | 4.936x | 1.177x | 0.239x |
| MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 871.4 | 427.0-427.0 | 10.20 | **no** | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 665.2-665.2 | 1.54 | yes | 4.251x | 0.642x | 0.151x |
| MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 803.5 | 225.7-225.7 | 17.80 | **no** | `a100_sxm_80gb-x3805-hybrid` | 203.5 | 647.7-647.7 | 1.57 | yes | 3.947x | 0.348x | 0.088x |
| MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 327.8 | 64.7-64.7 | 25.32 | **no** | `a100_sxm_80gb-x3805-hybrid` | 163.4 | 431.4-431.4 | 1.89 | yes | 2.007x | 0.150x | 0.075x |
| MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 90.1 | 16.3-16.3 | 27.64 | **no** | `a100_sxm_80gb-x3805-hybrid` | 120.9 | 400.9-400.9 | 1.51 | yes | 0.745x | 0.041x | 0.055x |
| MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x68` | 22.9 | 4.1-4.1 | 28.02 | **no** | `a100_sxm_80gb-x3805-hybrid` | 53.9 | 172.3-172.3 | 1.57 | yes | 0.424x | 0.024x | 0.056x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.055x to 0.239x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | 2,570.2 | 1,745.0-1,745.0 | 7.36 | **no** | `b200_sxm-x170-nvl72-hybrid` | 469.2 | 2,077.8-2,077.8 | 1.13 | yes | 5.478x | 0.840x | 0.153x |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 2,022.5 | 777.8-777.8 | 13.00 | **no** | `b200_sxm-x116-nvl72-hybrid` | 471.0 | 2,078.7-2,078.7 | 1.13 | yes | 4.294x | 0.374x | 0.087x |
| MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 845.7 | 250.1-250.1 | 16.91 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,981.3-1,981.3 | 1.13 | yes | 1.888x | 0.126x | 0.067x |
| MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 845.7 | 250.1-250.1 | 16.91 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,981.3-1,981.3 | 1.13 | yes | 1.888x | 0.126x | 0.067x |
| MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 845.7 | 250.1-250.1 | 16.91 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,981.3-1,981.3 | 1.13 | yes | 1.888x | 0.126x | 0.067x |
| MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 845.7 | 250.1-250.1 | 16.91 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,981.3-1,981.3 | 1.13 | yes | 1.888x | 0.126x | 0.067x |
| MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 845.7 | 250.1-250.1 | 16.91 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,981.3-1,981.3 | 1.13 | yes | 1.888x | 0.126x | 0.067x |
| MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 829.8 | 249.6-249.6 | 16.62 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 447.8 | 1,981.3-1,981.3 | 1.13 | yes | 1.853x | 0.126x | 0.068x |
| MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 480.9 | 65.8-65.8 | 36.54 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 401.8 | 1,593.9-1,593.9 | 1.26 | yes | 1.197x | 0.041x | 0.034x |
| MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 152.6 | 18.6-18.6 | 41.13 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 278.1 | 1,095.4-1,095.4 | 1.27 | yes | 0.549x | 0.017x | 0.031x |
| MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 39.8 | 4.6-4.6 | 42.87 | **no** | `b200_sxm-x6992-nvl72-hybrid` | 126.7 | 475.3-475.3 | 1.33 | yes | 0.314x | 0.010x | 0.031x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.031x to 0.153x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | 2,401.1 | 1,702.4-1,702.4 | 7.05 | **no** | `a100_sxm_80gb-x316-tensor` | 224.4 | 713.7-713.7 | 1.57 | yes | 10.698x | 2.385x | 0.223x |
| MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 1,874.2 | 1,039.2-1,039.2 | 9.02 | **no** | `a100_sxm_80gb-x336-hybrid` | 190.6 | 626.1-626.1 | 1.52 | yes | 9.836x | 1.660x | 0.169x |
| MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 624.3 | 2,099.3-2,099.3 | 1.49 | yes | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 636.0-636.0 | 1.49 | yes | 3.301x | 3.301x | 1.000x |
| MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 590.7 | 1,762.1-1,762.1 | 1.68 | yes | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 636.0-636.0 | 1.49 | yes | 3.124x | 2.771x | 0.887x |
| MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 582.6 | 179.5-179.5 | 16.23 | **no** | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 636.0-636.0 | 1.49 | yes | 3.081x | 0.282x | 0.092x |
| MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 582.6 | 179.5-179.5 | 16.23 | **no** | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 636.0-636.0 | 1.49 | yes | 3.081x | 0.282x | 0.092x |
| MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 582.6 | 179.5-179.5 | 16.23 | **no** | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 636.0-636.0 | 1.49 | yes | 3.081x | 0.282x | 0.092x |
| MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 582.6 | 179.5-179.5 | 16.23 | **no** | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 636.0-636.0 | 1.49 | yes | 3.081x | 0.282x | 0.092x |
| MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 284.4 | 90.3-90.3 | 15.76 | **no** | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 636.0-636.0 | 1.49 | yes | 1.504x | 0.142x | 0.094x |
| MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 88.4 | 25.6-25.6 | 17.29 | **no** | `a100_sxm_80gb-x18971-hybrid` | 139.5 | 447.1-447.1 | 1.56 | yes | 0.634x | 0.057x | 0.090x |
| MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 22.8 | 6.4-6.4 | 17.80 | **no** | `a100_sxm_80gb-x18971-hybrid` | 77.4 | 335.4-335.4 | 1.15 | yes | 0.295x | 0.019x | 0.065x |

**Does the ratio compress?** Of 11 class rows in this study, 11 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.065x to 1.000x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 2 of 11 ROM rows and 11 of 11 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-mimo-v26-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,330.1 | 1,377.9-1,377.9 | 15.71 | **no** | `b200_sxm-x78-nvl72-hybrid` | 490.3 | 2,078.5-2,078.5 | 1.18 | yes | 8.832x | 0.663x | 0.075x |
| MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,857.5 | 676.7-676.7 | 21.11 | **no** | `b200_sxm-x87-nvl72-hybrid` | 494.2 | 2,116.2-2,116.2 | 1.17 | yes | 5.782x | 0.320x | 0.055x |
| MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,330.1 | 1,377.9-1,377.9 | 15.71 | **no** | `b200_sxm-x78-nvl72-hybrid` | 490.3 | 2,078.5-2,078.5 | 1.18 | yes | 8.832x | 0.663x | 0.075x |
| MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,857.5 | 676.7-676.7 | 21.11 | **no** | `b200_sxm-x87-nvl72-hybrid` | 494.2 | 2,116.2-2,116.2 | 1.17 | yes | 5.782x | 0.320x | 0.055x |
| MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,330.1 | 1,377.9-1,377.9 | 15.71 | **no** | `b200_sxm-x78-nvl72-hybrid` | 477.9 | 1,928.0-1,928.0 | 1.24 | yes | 9.060x | 0.715x | 0.079x |
| MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,857.5 | 676.7-676.7 | 21.11 | **no** | `b200_sxm-x87-nvl72-hybrid` | 482.8 | 1,972.2-1,972.2 | 1.22 | yes | 5.919x | 0.343x | 0.058x |
| MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 4,330.1 | 1,377.9-1,377.9 | 15.71 | **no** | `b200_sxm-x78-nvl72-hybrid` | 455.6 | 1,686.9-1,686.9 | 1.35 | yes | 9.504x | 0.817x | 0.086x |
| MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,857.5 | 676.7-676.7 | 21.11 | **no** | `b200_sxm-x87-nvl72-hybrid` | 461.9 | 1,739.0-1,739.0 | 1.33 | yes | 6.186x | 0.389x | 0.063x |
| MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 4,285.0 | 1,288.5-1,288.5 | 16.63 | **no** | `b200_sxm-x150-nvl72-hybrid` | 456.9 | 1,700.4-1,700.4 | 1.34 | yes | 9.379x | 0.758x | 0.081x |
| MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 2,857.5 | 676.7-676.7 | 21.11 | **no** | `b200_sxm-x87-nvl72-hybrid` | 426.8 | 1,449.2-1,449.2 | 1.47 | yes | 6.695x | 0.467x | 0.070x |
| MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 4,214.3 | 697.5-697.5 | 30.21 | **no** | `b200_sxm-x150-nvl72-hybrid` | 417.5 | 1,394.9-1,394.9 | 1.50 | yes | 10.095x | 0.500x | 0.050x |
| MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 2,833.9 | 736.9-736.9 | 19.23 | **no** | `b200_sxm-x173-nvl72-hybrid` | 427.7 | 1,449.5-1,449.5 | 1.48 | yes | 6.625x | 0.508x | 0.077x |
| MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 3,932.5 | 686.4-686.4 | 28.64 | **no** | `b200_sxm-x200-nvl72-hybrid` | 387.1 | 1,163.0-1,163.0 | 1.66 | yes | 10.159x | 0.590x | 0.058x |
| MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,784.0 | 736.2-736.2 | 18.91 | **no** | `b200_sxm-x347-nvl72-hybrid` | 426.2 | 1,415.6-1,415.6 | 1.51 | yes | 6.531x | 0.520x | 0.080x |
| MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 2,411.3 | 177.8-177.8 | 67.81 | **no** | `b200_sxm-x200-nvl72-hybrid` | 266.4 | 551.6-551.6 | 2.41 | yes | 9.051x | 0.322x | 0.036x |
| MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,030.3 | 371.4-371.4 | 27.33 | **no** | `b200_sxm-x347-nvl72-hybrid` | 310.8 | 741.2-741.2 | 2.10 | yes | 6.532x | 0.501x | 0.077x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 883.4 | 153.4-153.4 | 28.80 | **no** | `b200_sxm-x173-nvl72-hybrid` | 152.2 | 184.9-184.9 | 4.12 | yes | 5.803x | 0.830x | 0.143x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 789.2 | 94.8-94.8 | 41.61 | **no** | `b200_sxm-x347-nvl72-hybrid` | 197.6 | 307.0-307.0 | 3.22 | yes | 3.993x | 0.309x | 0.077x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 345.8 | 96.9-96.9 | 17.85 | **no** | `b200_sxm-x200-nvl72-hybrid` | 89.2 | 102.3-102.3 | 4.36 | yes | 3.877x | 0.947x | 0.244x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 215.2 | 23.0-23.0 | 46.71 | **no** | `b200_sxm-x347-nvl72-hybrid` | 114.4 | 151.3-151.3 | 3.78 | yes | 1.882x | 0.152x | 0.081x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.036x to 0.244x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-mimo-v26-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,134.0 | 1,012.3-1,012.3 | 20.42 | **no** | `a100_sxm_80gb-x208-tensor` | 227.6 | 717.2-717.2 | 1.59 | yes | 18.165x | 1.411x | 0.078x |
| MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 2,383.2 | 1,207.3-1,207.3 | 9.87 | **no** | `a100_sxm_80gb-x168-tensor` | 226.3 | 712.3-712.3 | 1.59 | yes | 10.531x | 1.695x | 0.161x |
| MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,134.0 | 1,012.3-1,012.3 | 20.42 | **no** | `a100_sxm_80gb-x208-hybrid` | 211.6 | 662.3-662.3 | 1.60 | yes | 19.541x | 1.528x | 0.078x |
| MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,340.4 | 680.0-680.0 | 17.21 | **no** | `a100_sxm_80gb-x336-hybrid` | 212.8 | 672.3-672.3 | 1.58 | yes | 10.997x | 1.011x | 0.092x |
| MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,134.0 | 1,012.3-1,012.3 | 20.42 | **no** | `a100_sxm_80gb-x208-hybrid` | 211.6 | 662.3-662.3 | 1.60 | yes | 19.541x | 1.528x | 0.078x |
| MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,340.4 | 680.0-680.0 | 17.21 | **no** | `a100_sxm_80gb-x336-hybrid` | 212.8 | 672.3-672.3 | 1.58 | yes | 10.997x | 1.011x | 0.092x |
| MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 4,134.0 | 1,012.3-1,012.3 | 20.42 | **no** | `a100_sxm_80gb-x208-hybrid` | 195.4 | 591.7-591.7 | 1.65 | yes | 21.152x | 1.711x | 0.081x |
| MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,340.4 | 680.0-680.0 | 17.21 | **no** | `a100_sxm_80gb-x336-hybrid` | 206.8 | 598.3-598.3 | 1.73 | yes | 11.318x | 1.136x | 0.100x |
| MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 4,119.4 | 970.3-970.3 | 21.23 | **no** | `a100_sxm_80gb-x249-hybrid` | 182.3 | 470.1-470.1 | 1.94 | yes | 22.600x | 2.064x | 0.091x |
| MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 2,340.4 | 680.0-680.0 | 17.21 | **no** | `a100_sxm_80gb-x336-hybrid` | 190.4 | 544.6-544.6 | 1.75 | yes | 12.295x | 1.249x | 0.102x |
| MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 3,866.1 | 504.7-504.7 | 38.30 | **no** | `a100_sxm_80gb-x249-hybrid` | 178.1 | 527.2-527.2 | 1.69 | yes | 21.704x | 0.957x | 0.044x |
| MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 2,310.2 | 363.7-363.7 | 31.76 | **no** | `a100_sxm_80gb-x672-hybrid` | 189.6 | 541.6-541.6 | 1.75 | yes | 12.182x | 0.671x | 0.055x |
| MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 3,593.9 | 493.7-493.7 | 36.40 | **no** | `a100_sxm_80gb-x373-hybrid` | 168.9 | 490.6-490.6 | 1.72 | yes | 21.278x | 1.006x | 0.047x |
| MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,032.8 | 538.2-538.2 | 18.89 | **no** | `a100_sxm_80gb-x672-hybrid` | 177.8 | 559.3-559.3 | 1.59 | yes | 11.434x | 0.962x | 0.084x |
| MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 1,939.3 | 128.3-128.3 | 75.55 | **no** | `a100_sxm_80gb-x373-hybrid` | 105.4 | 271.9-271.9 | 1.94 | yes | 18.395x | 0.472x | 0.026x |
| MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,117.6 | 93.5-93.5 | 59.75 | **no** | `a100_sxm_80gb-x672-hybrid` | 133.9 | 363.2-363.2 | 1.84 | yes | 8.347x | 0.257x | 0.031x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 783.2 | 130.2-130.2 | 30.07 | **no** | `a100_sxm_80gb-x373-hybrid` | 47.0 | 130.7-130.7 | 1.80 | yes | 16.669x | 0.996x | 0.060x |
| MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 345.4 | 23.6-23.6 | 73.24 | **no** | `a100_sxm_80gb-x672-hybrid` | 67.2 | 177.6-177.6 | 1.89 | yes | 5.142x | 0.133x | 0.026x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 231.5 | 33.4-33.4 | 34.61 | **no** | `a100_sxm_80gb-x373-hybrid` | 22.0 | 58.1-58.1 | 1.89 | yes | 10.540x | 0.576x | 0.055x |
| MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 89.5 | 22.5-22.5 | 19.86 | **no** | `a100_sxm_80gb-x672-hybrid` | 28.7 | 82.4-82.4 | 1.74 | yes | 3.119x | 0.274x | 0.088x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.026x to 0.161x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-qwen3-8b-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x180` | 3,799.1 | not applicable | -- | -- | `b200_sxm-x92-nvl72-hybrid` | 772.6 | not applicable | -- | -- | 4.917x | -- | -- |
| Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 5,035.0 | not applicable | -- | -- | `b200_sxm-x58-nvl72-tensor` | 849.5 | not applicable | -- | -- | 5.927x | -- | -- |

### `n6_vs_a100-qwen3-8b-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x227` | 3,580.9 | not applicable | -- | -- | `a100_sxm_80gb-x224-tensor` | 468.9 | not applicable | -- | -- | 7.636x | -- | -- |
| Qwen3-8B | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 5,016.0 | not applicable | -- | -- | `a100_sxm_80gb-x112-tensor` | 389.3 | not applicable | -- | -- | 12.884x | -- | -- |

### `n5_vs_b200-qwen3-8b-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x60-romfill` | 7,172.1 | not applicable | -- | -- | `b200_sxm-x31-nvl72-tensor` | 1,034.4 | not applicable | -- | -- | 6.933x | -- | -- |
| Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 5,049.6 | not applicable | -- | -- | `b200_sxm-x58-nvl72-tensor` | 1,158.3 | not applicable | -- | -- | 4.359x | -- | -- |
| Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x139-romfill` | 1,919.2 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,087.6 | not applicable | -- | -- | 1.765x | -- | -- |
| Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-tensor-x139` | 1,805.6 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,087.6 | not applicable | -- | -- | 1.660x | -- | -- |
| Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1,798.4 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,087.6 | not applicable | -- | -- | 1.654x | -- | -- |
| Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1,798.4 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,087.6 | not applicable | -- | -- | 1.654x | -- | -- |
| Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1,798.4 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,087.6 | not applicable | -- | -- | 1.654x | -- | -- |
| Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 1,346.6 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 1,075.6 | not applicable | -- | -- | 1.252x | -- | -- |
| Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 578.5 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 851.3 | not applicable | -- | -- | 0.680x | -- | -- |
| Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 157.5 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 481.1 | not applicable | -- | -- | 0.327x | -- | -- |
| Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 40.0 | not applicable | -- | -- | `b200_sxm-x4016-nvl72-hybrid` | 177.1 | not applicable | -- | -- | 0.226x | -- | -- |

### `n6_vs_a100-qwen3-8b-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 7,166.0 | not applicable | -- | -- | `a100_sxm_80gb-x56-tensor` | 461.8 | not applicable | -- | -- | 15.517x | -- | -- |
| Qwen3-8B | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 5,071.3 | not applicable | -- | -- | `a100_sxm_80gb-x112-tensor` | 517.9 | not applicable | -- | -- | 9.792x | -- | -- |
| Qwen3-8B | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196-romfill` | 1,787.0 | not applicable | -- | -- | `a100_sxm_80gb-x10969-tensor` | 475.1 | not applicable | -- | -- | 3.761x | -- | -- |
| Qwen3-8B | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 1,683.6 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 456.0 | not applicable | -- | -- | 3.692x | -- | -- |
| Qwen3-8B | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 1,484.4 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 456.0 | not applicable | -- | -- | 3.255x | -- | -- |
| Qwen3-8B | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 1,190.3 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 456.0 | not applicable | -- | -- | 2.610x | -- | -- |
| Qwen3-8B | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 1,160.4 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 456.0 | not applicable | -- | -- | 2.544x | -- | -- |
| Qwen3-8B | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 970.9 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 456.0 | not applicable | -- | -- | 2.129x | -- | -- |
| Qwen3-8B | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 342.6 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 419.8 | not applicable | -- | -- | 0.816x | -- | -- |
| Qwen3-8B | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 91.0 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 256.3 | not applicable | -- | -- | 0.355x | -- | -- |
| Qwen3-8B | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 23.0 | not applicable | -- | -- | `a100_sxm_80gb-x10969-hybrid` | 112.7 | not applicable | -- | -- | 0.204x | -- | -- |

### `n5_vs_b200-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 2,959.9 | 501.1-501.1 | 29.53 | **no** | `b200_sxm-x58-nvl72-tensor` | 559.2 | 1,436.7-1,436.7 | 1.95 | yes | 5.294x | 0.349x | 0.066x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 2,778.1 | 939.8-939.8 | 14.78 | **no** | `b200_sxm-x58-nvl72-tensor` | 559.2 | 1,436.7-1,436.7 | 1.95 | yes | 4.968x | 0.654x | 0.132x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 2,513.2 | 420.9-420.9 | 29.85 | **no** | `b200_sxm-x142-nvl72-hybrid` | 558.7 | 1,429.0-1,429.0 | 1.95 | yes | 4.498x | 0.295x | 0.065x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,809.5 | 2,882.4-2,882.4 | 3.14 | yes | `b200_sxm-x953-nvl72-hybrid` | 548.5 | 1,353.4-1,353.4 | 2.03 | yes | 3.299x | 2.130x | 0.646x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 2,513.2 | 420.9-420.9 | 29.85 | **no** | `b200_sxm-x142-nvl72-hybrid` | 548.5 | 1,402.2-1,402.2 | 1.96 | yes | 4.582x | 0.300x | 0.066x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,809.5 | 2,882.4-2,882.4 | 3.14 | yes | `b200_sxm-x953-nvl72-hybrid` | 548.5 | 1,353.4-1,353.4 | 2.03 | yes | 3.299x | 2.130x | 0.646x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 2,513.2 | 420.9-420.9 | 29.85 | **no** | `b200_sxm-x142-nvl72-hybrid` | 535.4 | 1,364.6-1,364.6 | 1.96 | yes | 4.694x | 0.308x | 0.066x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,809.5 | 2,882.4-2,882.4 | 3.14 | yes | `b200_sxm-x953-nvl72-hybrid` | 548.5 | 1,353.4-1,353.4 | 2.03 | yes | 3.299x | 2.130x | 0.646x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 2,513.2 | 420.9-420.9 | 29.85 | **no** | `b200_sxm-x142-nvl72-hybrid` | 535.2 | 1,313.4-1,313.4 | 2.04 | yes | 4.695x | 0.320x | 0.068x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,809.5 | 2,882.4-2,882.4 | 3.14 | yes | `b200_sxm-x953-nvl72-hybrid` | 543.1 | 1,304.6-1,304.6 | 2.08 | yes | 3.332x | 2.209x | 0.663x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 2,513.2 | 420.9-420.9 | 29.85 | **no** | `b200_sxm-x142-nvl72-hybrid` | 482.5 | 957.3-957.3 | 2.52 | yes | 5.209x | 0.440x | 0.084x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,809.5 | 2,882.4-2,882.4 | 3.14 | yes | `b200_sxm-x953-nvl72-hybrid` | 531.8 | 1,249.9-1,249.9 | 2.13 | yes | 3.403x | 2.306x | 0.678x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 2,479.0 | 222.5-222.5 | 55.70 | **no** | `b200_sxm-x142-nvl72-hybrid` | 428.3 | 857.1-857.1 | 2.50 | yes | 5.789x | 0.260x | 0.045x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,809.5 | 2,882.4-2,882.4 | 3.14 | yes | `b200_sxm-x953-nvl72-hybrid` | 525.7 | 1,062.9-1,062.9 | 2.47 | yes | 3.442x | 2.712x | 0.788x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 1,582.7 | 169.2-169.2 | 46.78 | **no** | `b200_sxm-x178-pipeline` | 320.0 | 583.2-583.2 | 2.74 | yes | 4.945x | 0.290x | 0.059x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,463.1 | 1,705.3-1,705.3 | 4.29 | yes | `b200_sxm-x953-nvl72-hybrid` | 473.6 | 803.9-803.9 | 2.95 | yes | 3.089x | 2.121x | 0.687x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 576.3 | 79.4-79.4 | 36.29 | **no** | `b200_sxm-x178-pipeline` | 160.8 | 248.4-248.4 | 3.24 | yes | 3.583x | 0.320x | 0.089x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 610.6 | 496.5-496.5 | 6.15 | **no** | `b200_sxm-x953-pipeline` | 349.3 | 354.1-354.1 | 4.93 | yes | 1.748x | 1.402x | 0.802x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 144.5 | 55.1-55.1 | 13.12 | **no** | `b200_sxm-x178-pipeline` | 58.3 | 147.4-147.4 | 1.98 | yes | 2.477x | 0.374x | 0.151x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 175.2 | 17.0-17.0 | 51.45 | **no** | `b200_sxm-x953-pipeline` | 192.5 | 222.0-222.0 | 4.34 | yes | 0.910x | 0.077x | 0.084x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.045x to 0.802x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 7 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 3,478.9 | 1,178.5-1,178.5 | 14.76 | **no** | `b200_sxm-x24-nvl72-tensor` | 607.0 | 2,343.3-2,343.3 | 1.30 | yes | 5.732x | 0.503x | 0.088x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3,172.0 | 1,188.2-1,188.2 | 13.35 | **no** | `b200_sxm-x58-nvl72-tensor` | 619.0 | 2,463.7-2,463.7 | 1.26 | yes | 5.125x | 0.482x | 0.094x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 3,478.9 | 1,178.5-1,178.5 | 14.76 | **no** | `b200_sxm-x24-hybrid` | 595.2 | 2,109.7-2,109.7 | 1.41 | yes | 5.845x | 0.559x | 0.096x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3,172.0 | 1,188.2-1,188.2 | 13.35 | **no** | `b200_sxm-x58-nvl72-tensor` | 603.9 | 2,135.5-2,135.5 | 1.41 | yes | 5.253x | 0.556x | 0.106x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 3,478.9 | 1,178.5-1,178.5 | 14.76 | **no** | `b200_sxm-x24-hybrid` | 585.9 | 1,950.2-1,950.2 | 1.50 | yes | 5.938x | 0.604x | 0.102x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3,172.0 | 1,188.2-1,188.2 | 13.35 | **no** | `b200_sxm-x58-hybrid` | 583.3 | 2,006.8-2,006.8 | 1.45 | yes | 5.438x | 0.592x | 0.109x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 3,478.9 | 1,178.5-1,178.5 | 14.76 | **no** | `b200_sxm-x24-hybrid` | 552.0 | 1,573.4-1,573.4 | 1.75 | yes | 6.303x | 0.749x | 0.119x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3,172.0 | 1,188.2-1,188.2 | 13.35 | **no** | `b200_sxm-x58-hybrid` | 583.3 | 2,006.8-2,006.8 | 1.45 | yes | 5.438x | 0.592x | 0.109x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 3,461.4 | 1,132.4-1,132.4 | 15.28 | **no** | `b200_sxm-x44-hybrid` | 540.4 | 1,519.3-1,519.3 | 1.78 | yes | 6.405x | 0.745x | 0.116x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 3,172.0 | 1,188.2-1,188.2 | 13.35 | **no** | `b200_sxm-x58-hybrid` | 554.6 | 1,652.2-1,652.2 | 1.68 | yes | 5.720x | 0.719x | 0.126x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,419.4 | 1,140.5-1,140.5 | 14.99 | **no** | `b200_sxm-x173-nvl72-hybrid` | 573.4 | 1,784.4-1,784.4 | 1.61 | yes | 5.964x | 0.639x | 0.107x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 3,141.5 | 1,205.9-1,205.9 | 13.03 | **no** | `b200_sxm-x116-nvl72-hybrid` | 557.9 | 1,648.2-1,648.2 | 1.69 | yes | 5.631x | 0.732x | 0.130x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,419.4 | 1,140.5-1,140.5 | 14.99 | **no** | `b200_sxm-x173-nvl72-hybrid` | 537.4 | 1,454.1-1,454.1 | 1.85 | yes | 6.363x | 0.784x | 0.123x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,141.5 | 1,205.9-1,205.9 | 13.03 | **no** | `b200_sxm-x231-nvl72-hybrid` | 551.7 | 1,540.1-1,540.1 | 1.79 | yes | 5.694x | 0.783x | 0.138x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 3,093.8 | 301.0-301.0 | 51.39 | **no** | `b200_sxm-x173-nvl72-hybrid` | 395.0 | 782.9-782.9 | 2.52 | yes | 7.833x | 0.384x | 0.049x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,121.4 | 631.5-631.5 | 24.71 | **no** | `b200_sxm-x347-nvl72-hybrid` | 469.7 | 1,028.1-1,028.1 | 2.28 | yes | 6.645x | 0.614x | 0.092x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,636.9 | 262.4-262.4 | 31.19 | **no** | `b200_sxm-x173-nvl72-hybrid` | 222.1 | 427.7-427.7 | 2.60 | yes | 7.371x | 0.614x | 0.083x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,522.0 | 311.6-311.6 | 40.47 | **no** | `b200_sxm-x347-nvl72-hybrid` | 303.6 | 567.9-567.9 | 2.67 | yes | 8.306x | 0.549x | 0.066x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 503.9 | 166.3-166.3 | 15.15 | **no** | `b200_sxm-x173-nvl72-hybrid` | 115.4 | 182.7-182.7 | 3.16 | yes | 4.367x | 0.911x | 0.209x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,010.8 | 238.7-238.7 | 21.18 | **no** | `b200_sxm-x347-nvl72-hybrid` | 159.4 | 279.2-279.2 | 2.86 | yes | 6.339x | 0.855x | 0.135x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.049x to 0.209x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 3,485.7 | 1,186.0-1,186.0 | 14.70 | **no** | `b200_sxm-x24-nvl72-tensor` | 607.1 | 2,417.4-2,417.4 | 1.26 | yes | 5.742x | 0.491x | 0.085x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,234.6 | 637.1-637.1 | 25.39 | **no** | `b200_sxm-x231-nvl72-hybrid` | 615.9 | 2,413.1-2,413.1 | 1.28 | yes | 5.252x | 0.264x | 0.050x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 3,485.7 | 1,186.0-1,186.0 | 14.70 | **no** | `b200_sxm-x24-hybrid` | 595.5 | 2,128.5-2,128.5 | 1.40 | yes | 5.854x | 0.557x | 0.095x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,234.6 | 637.1-637.1 | 25.39 | **no** | `b200_sxm-x231-nvl72-hybrid` | 615.9 | 2,413.1-2,413.1 | 1.28 | yes | 5.252x | 0.264x | 0.050x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 3,485.7 | 1,186.0-1,186.0 | 14.70 | **no** | `b200_sxm-x24-hybrid` | 586.2 | 2,004.7-2,004.7 | 1.46 | yes | 5.946x | 0.592x | 0.099x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,234.6 | 637.1-637.1 | 25.39 | **no** | `b200_sxm-x231-nvl72-hybrid` | 615.9 | 2,413.1-2,413.1 | 1.28 | yes | 5.252x | 0.264x | 0.050x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 3,485.7 | 1,186.0-1,186.0 | 14.70 | **no** | `b200_sxm-x24-hybrid` | 552.6 | 1,639.1-1,639.1 | 1.69 | yes | 6.308x | 0.724x | 0.115x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,234.6 | 637.1-637.1 | 25.39 | **no** | `b200_sxm-x231-nvl72-hybrid` | 605.2 | 2,320.5-2,320.5 | 1.30 | yes | 5.344x | 0.275x | 0.051x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 3,468.2 | 1,139.1-1,139.1 | 15.22 | **no** | `b200_sxm-x44-hybrid` | 541.0 | 1,580.5-1,580.5 | 1.71 | yes | 6.410x | 0.721x | 0.112x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,234.6 | 637.1-637.1 | 25.39 | **no** | `b200_sxm-x231-nvl72-hybrid` | 591.0 | 2,025.2-2,025.2 | 1.46 | yes | 5.473x | 0.315x | 0.057x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,426.0 | 1,147.2-1,147.2 | 14.93 | **no** | `b200_sxm-x173-nvl72-hybrid` | 573.7 | 1,836.9-1,836.9 | 1.56 | yes | 5.972x | 0.625x | 0.105x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,234.6 | 637.1-637.1 | 25.39 | **no** | `b200_sxm-x231-nvl72-hybrid` | 580.6 | 1,907.0-1,907.0 | 1.52 | yes | 5.571x | 0.334x | 0.060x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,426.0 | 1,147.2-1,147.2 | 14.93 | **no** | `b200_sxm-x173-nvl72-hybrid` | 538.0 | 1,514.2-1,514.2 | 1.78 | yes | 6.368x | 0.758x | 0.119x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 3,234.6 | 637.1-637.1 | 25.39 | **no** | `b200_sxm-x231-nvl72-hybrid` | 552.2 | 1,593.8-1,593.8 | 1.73 | yes | 5.857x | 0.400x | 0.068x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 3,217.9 | 302.9-302.9 | 53.12 | **no** | `b200_sxm-x173-nvl72-hybrid` | 401.0 | 828.1-828.1 | 2.42 | yes | 8.024x | 0.366x | 0.046x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,234.2 | 636.2-636.2 | 25.42 | **no** | `b200_sxm-x347-nvl72-hybrid` | 472.1 | 1,063.5-1,063.5 | 2.22 | yes | 6.851x | 0.598x | 0.087x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,751.7 | 266.9-266.9 | 32.82 | **no** | `b200_sxm-x173-nvl72-hybrid` | 229.8 | 362.7-362.7 | 3.17 | yes | 7.623x | 0.736x | 0.097x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 2,752.2 | 314.5-314.5 | 43.75 | **no** | `b200_sxm-x347-nvl72-hybrid` | 305.2 | 596.7-596.7 | 2.56 | yes | 9.018x | 0.527x | 0.058x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 548.1 | 173.8-173.8 | 15.77 | **no** | `b200_sxm-x173-nvl72-hybrid` | 120.8 | 201.7-201.7 | 3.00 | yes | 4.538x | 0.862x | 0.190x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,111.0 | 246.3-246.3 | 22.55 | **no** | `b200_sxm-x347-nvl72-hybrid` | 162.1 | 301.1-301.1 | 2.69 | yes | 6.852x | 0.818x | 0.119x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.046x to 0.190x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,823.8 | 198.1-198.1 | 46.02 | **no** | `b200_sxm-x157-nvl72-hybrid` | 409.5 | 1,347.4-1,347.4 | 1.52 | yes | 4.454x | 0.147x | 0.033x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 1,617.0 | 493.4-493.4 | 16.39 | **no** | `b200_sxm-x116-nvl72-hybrid` | 411.6 | 1,367.7-1,367.7 | 1.50 | yes | 3.928x | 0.361x | 0.092x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,823.8 | 198.1-198.1 | 46.02 | **no** | `b200_sxm-x157-nvl72-hybrid` | 409.5 | 1,347.4-1,347.4 | 1.52 | yes | 4.454x | 0.147x | 0.033x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,557.3 | 465.7-465.7 | 16.72 | **no** | `b200_sxm-x289-nvl72-hybrid` | 410.0 | 1,332.1-1,332.1 | 1.54 | yes | 3.799x | 0.350x | 0.092x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,823.8 | 198.1-198.1 | 46.02 | **no** | `b200_sxm-x157-nvl72-hybrid` | 400.8 | 1,215.0-1,215.0 | 1.65 | yes | 4.550x | 0.163x | 0.036x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,557.3 | 465.7-465.7 | 16.72 | **no** | `b200_sxm-x289-nvl72-hybrid` | 410.0 | 1,332.1-1,332.1 | 1.54 | yes | 3.799x | 0.350x | 0.092x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,823.8 | 198.1-198.1 | 46.02 | **no** | `b200_sxm-x157-nvl72-hybrid` | 397.3 | 1,192.4-1,192.4 | 1.67 | yes | 4.591x | 0.166x | 0.036x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,557.3 | 465.7-465.7 | 16.72 | **no** | `b200_sxm-x289-nvl72-hybrid` | 396.2 | 1,241.9-1,241.9 | 1.60 | yes | 3.930x | 0.375x | 0.095x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,823.8 | 198.1-198.1 | 46.02 | **no** | `b200_sxm-x157-nvl72-hybrid` | 377.8 | 991.7-991.7 | 1.90 | yes | 4.828x | 0.200x | 0.041x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,557.3 | 465.7-465.7 | 16.72 | **no** | `b200_sxm-x289-nvl72-hybrid` | 393.2 | 1,122.0-1,122.0 | 1.75 | yes | 3.960x | 0.415x | 0.105x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,823.8 | 198.1-198.1 | 46.02 | **no** | `b200_sxm-x157-nvl72-hybrid` | 334.3 | 710.2-710.2 | 2.35 | yes | 5.455x | 0.279x | 0.051x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,557.3 | 465.7-465.7 | 16.72 | **no** | `b200_sxm-x289-nvl72-hybrid` | 371.0 | 920.3-920.3 | 2.02 | yes | 4.198x | 0.506x | 0.121x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 1,823.8 | 198.1-198.1 | 46.02 | **no** | `b200_sxm-x157-nvl72-hybrid` | 281.9 | 567.6-567.6 | 2.48 | yes | 6.469x | 0.349x | 0.054x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1,557.3 | 465.7-465.7 | 16.72 | **no** | `b200_sxm-x289-nvl72-hybrid` | 326.0 | 653.0-653.0 | 2.50 | yes | 4.777x | 0.713x | 0.149x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,324.0 | 89.6-89.6 | 73.87 | **no** | `b200_sxm-x173-nvl72-hybrid` | 165.2 | 251.5-251.5 | 3.29 | yes | 8.013x | 0.356x | 0.044x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,314.2 | 233.1-233.1 | 28.19 | **no** | `b200_sxm-x347-nvl72-hybrid` | 227.4 | 375.6-375.6 | 3.03 | yes | 5.778x | 0.621x | 0.107x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 529.8 | 42.7-42.7 | 62.11 | **no** | `b200_sxm-x173-nvl72-hybrid` | 71.3 | 118.5-118.5 | 3.01 | yes | 7.430x | 0.360x | 0.048x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 670.2 | 59.7-59.7 | 56.14 | **no** | `b200_sxm-x347-nvl72-hybrid` | 113.2 | 173.0-173.0 | 3.27 | yes | 5.918x | 0.345x | 0.058x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 149.7 | 32.1-32.1 | 23.30 | **no** | `b200_sxm-x173-nvl72-hybrid` | 28.9 | 48.6-48.6 | 2.97 | yes | 5.183x | 0.661x | 0.128x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 198.7 | 22.2-22.2 | 44.66 | **no** | `b200_sxm-x347-nvl72-hybrid` | 44.2 | 74.8-74.8 | 2.95 | yes | 4.497x | 0.297x | 0.066x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.033x to 0.149x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,892.4 | 226.9-226.9 | 41.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 421.6 | 1,522.6-1,522.6 | 1.38 | yes | 4.489x | 0.149x | 0.033x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,733.1 | 244.4-244.4 | 35.45 | **no** | `b200_sxm-x144-nvl72-hybrid` | 422.2 | 1,541.5-1,541.5 | 1.37 | yes | 4.105x | 0.159x | 0.039x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,892.4 | 226.9-226.9 | 41.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 421.6 | 1,522.6-1,522.6 | 1.38 | yes | 4.489x | 0.149x | 0.033x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,733.1 | 244.4-244.4 | 35.45 | **no** | `b200_sxm-x144-nvl72-hybrid` | 422.2 | 1,541.5-1,541.5 | 1.37 | yes | 4.105x | 0.159x | 0.039x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,892.4 | 226.9-226.9 | 41.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 408.3 | 1,356.3-1,356.3 | 1.51 | yes | 4.635x | 0.167x | 0.036x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,733.1 | 244.4-244.4 | 35.45 | **no** | `b200_sxm-x144-nvl72-hybrid` | 409.4 | 1,363.3-1,363.3 | 1.50 | yes | 4.233x | 0.179x | 0.042x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,892.4 | 226.9-226.9 | 41.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 399.1 | 1,304.5-1,304.5 | 1.53 | yes | 4.742x | 0.174x | 0.037x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,733.1 | 244.4-244.4 | 35.45 | **no** | `b200_sxm-x144-nvl72-hybrid` | 402.0 | 1,320.9-1,320.9 | 1.52 | yes | 4.312x | 0.185x | 0.043x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,892.4 | 226.9-226.9 | 41.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 378.9 | 1,079.6-1,079.6 | 1.76 | yes | 4.994x | 0.210x | 0.042x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,733.1 | 244.4-244.4 | 35.45 | **no** | `b200_sxm-x144-nvl72-hybrid` | 382.2 | 1,094.4-1,094.4 | 1.75 | yes | 4.534x | 0.223x | 0.049x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,892.4 | 226.9-226.9 | 41.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 340.3 | 801.6-801.6 | 2.12 | yes | 5.561x | 0.283x | 0.051x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,733.1 | 244.4-244.4 | 35.45 | **no** | `b200_sxm-x144-nvl72-hybrid` | 344.1 | 813.7-813.7 | 2.11 | yes | 5.036x | 0.300x | 0.060x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 1,892.4 | 226.9-226.9 | 41.70 | **no** | `b200_sxm-x137-nvl72-hybrid` | 284.0 | 540.6-540.6 | 2.63 | yes | 6.664x | 0.420x | 0.063x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,733.1 | 244.4-244.4 | 35.45 | **no** | `b200_sxm-x144-nvl72-hybrid` | 288.3 | 549.7-549.7 | 2.62 | yes | 6.012x | 0.445x | 0.074x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,410.4 | 90.9-90.9 | 77.61 | **no** | `b200_sxm-x173-nvl72-hybrid` | 177.0 | 308.4-308.4 | 2.87 | yes | 7.968x | 0.295x | 0.037x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,614.8 | 123.7-123.7 | 65.26 | **no** | `b200_sxm-x347-nvl72-hybrid` | 237.1 | 443.6-443.6 | 2.67 | yes | 6.810x | 0.279x | 0.041x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 662.5 | 43.8-43.8 | 75.66 | **no** | `b200_sxm-x173-nvl72-hybrid` | 78.3 | 127.4-127.4 | 3.07 | yes | 8.457x | 0.344x | 0.041x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,012.3 | 60.9-60.9 | 83.09 | **no** | `b200_sxm-x347-nvl72-hybrid` | 119.1 | 191.1-191.1 | 3.12 | yes | 8.497x | 0.319x | 0.038x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 193.9 | 34.9-34.9 | 27.81 | **no** | `b200_sxm-x173-nvl72-hybrid` | 36.7 | 44.9-44.9 | 4.09 | yes | 5.280x | 0.776x | 0.147x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 390.0 | 76.5-76.5 | 25.49 | **no** | `b200_sxm-x347-nvl72-hybrid` | 51.7 | 73.8-73.8 | 3.50 | yes | 7.539x | 1.036x | 0.137x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.033x to 0.147x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 1,967.4 | 445.0-445.0 | 22.10 | **no** | `b200_sxm-x134-nvl72-hybrid` | 421.3 | 1,562.4-1,562.4 | 1.35 | yes | 4.670x | 0.285x | 0.061x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,815.1 | 245.2-245.2 | 37.01 | **no** | `b200_sxm-x144-nvl72-hybrid` | 422.3 | 1,555.1-1,555.1 | 1.36 | yes | 4.298x | 0.158x | 0.037x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 1,967.4 | 445.0-445.0 | 22.10 | **no** | `b200_sxm-x134-nvl72-hybrid` | 421.3 | 1,562.4-1,562.4 | 1.35 | yes | 4.670x | 0.285x | 0.061x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,815.1 | 245.2-245.2 | 37.01 | **no** | `b200_sxm-x144-nvl72-hybrid` | 422.3 | 1,555.1-1,555.1 | 1.36 | yes | 4.298x | 0.158x | 0.037x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 1,967.4 | 445.0-445.0 | 22.10 | **no** | `b200_sxm-x134-nvl72-hybrid` | 407.8 | 1,394.4-1,394.4 | 1.46 | yes | 4.824x | 0.319x | 0.066x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,815.1 | 245.2-245.2 | 37.01 | **no** | `b200_sxm-x144-nvl72-hybrid` | 409.4 | 1,405.1-1,405.1 | 1.46 | yes | 4.433x | 0.175x | 0.039x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 1,967.4 | 445.0-445.0 | 22.10 | **no** | `b200_sxm-x134-nvl72-hybrid` | 397.8 | 1,304.6-1,304.6 | 1.52 | yes | 4.945x | 0.341x | 0.069x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,815.1 | 245.2-245.2 | 37.01 | **no** | `b200_sxm-x144-nvl72-hybrid` | 402.0 | 1,330.8-1,330.8 | 1.51 | yes | 4.515x | 0.184x | 0.041x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 1,967.4 | 445.0-445.0 | 22.10 | **no** | `b200_sxm-x134-nvl72-hybrid` | 377.6 | 1,090.3-1,090.3 | 1.73 | yes | 5.210x | 0.408x | 0.078x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,815.1 | 245.2-245.2 | 37.01 | **no** | `b200_sxm-x144-nvl72-hybrid` | 382.4 | 1,114.5-1,114.5 | 1.72 | yes | 4.747x | 0.220x | 0.046x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 1,967.4 | 445.0-445.0 | 22.10 | **no** | `b200_sxm-x134-nvl72-hybrid` | 338.8 | 827.7-827.7 | 2.05 | yes | 5.807x | 0.538x | 0.093x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,815.1 | 245.2-245.2 | 37.01 | **no** | `b200_sxm-x144-nvl72-hybrid` | 344.3 | 846.7-846.7 | 2.03 | yes | 5.271x | 0.290x | 0.055x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 1,957.5 | 229.0-229.0 | 42.73 | **no** | `b200_sxm-x157-nvl72-hybrid` | 296.3 | 611.6-611.6 | 2.42 | yes | 6.605x | 0.375x | 0.057x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 1,815.1 | 245.2-245.2 | 37.01 | **no** | `b200_sxm-x144-nvl72-hybrid` | 288.6 | 578.5-578.5 | 2.49 | yes | 6.290x | 0.424x | 0.067x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 1,470.0 | 171.6-171.6 | 42.82 | **no** | `b200_sxm-x173-nvl72-hybrid` | 177.4 | 321.4-321.4 | 2.76 | yes | 8.286x | 0.534x | 0.064x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,697.9 | 239.3-239.3 | 35.47 | **no** | `b200_sxm-x347-nvl72-hybrid` | 237.5 | 452.9-452.9 | 2.62 | yes | 7.150x | 0.528x | 0.074x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 688.0 | 44.0-44.0 | 78.26 | **no** | `b200_sxm-x173-nvl72-hybrid` | 78.6 | 136.8-136.8 | 2.87 | yes | 8.748x | 0.321x | 0.037x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,046.7 | 61.1-61.1 | 85.64 | **no** | `b200_sxm-x347-nvl72-hybrid` | 119.5 | 201.5-201.5 | 2.97 | yes | 8.760x | 0.303x | 0.035x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 202.7 | 35.3-35.3 | 28.71 | **no** | `b200_sxm-x173-nvl72-hybrid` | 38.3 | 48.9-48.9 | 3.91 | yes | 5.298x | 0.722x | 0.136x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 404.7 | 121.7-121.7 | 16.63 | **no** | `b200_sxm-x347-nvl72-hybrid` | 52.1 | 79.1-79.1 | 3.29 | yes | 7.769x | 1.539x | 0.198x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.035x to 0.198x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-1m`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x152` | 2,753.2 | 384.9-384.9 | 35.76 | **no** | `a100_sxm_80gb-x150-hybrid` | 286.1 | 510.7-510.7 | 2.80 | yes | 9.622x | 0.754x | 0.078x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 2,674.3 | 657.6-657.6 | 20.33 | **no** | `a100_sxm_80gb-x168-hybrid` | 286.5 | 507.5-507.5 | 2.82 | yes | 9.334x | 1.296x | 0.139x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,374.0 | 556.3-556.3 | 21.34 | **no** | `a100_sxm_80gb-x387-hybrid` | 279.8 | 447.3-447.3 | 3.13 | yes | 8.486x | 1.244x | 0.147x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,445.1 | 192.8-192.8 | 37.47 | **no** | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 268.6-268.6 | 5.22 | **no** | 5.151x | 0.718x | 0.139x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,374.0 | 556.3-556.3 | 21.34 | **no** | `a100_sxm_80gb-x387-hybrid` | 279.8 | 447.3-447.3 | 3.13 | yes | 8.486x | 1.244x | 0.147x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,445.1 | 192.8-192.8 | 37.47 | **no** | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 268.6-268.6 | 5.22 | **no** | 5.151x | 0.718x | 0.139x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,374.0 | 556.3-556.3 | 21.34 | **no** | `a100_sxm_80gb-x387-hybrid` | 279.8 | 447.3-447.3 | 3.13 | yes | 8.486x | 1.244x | 0.147x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,445.1 | 192.8-192.8 | 37.47 | **no** | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 268.6-268.6 | 5.22 | **no** | 5.151x | 0.718x | 0.139x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,374.0 | 556.3-556.3 | 21.34 | **no** | `a100_sxm_80gb-x387-hybrid` | 279.8 | 447.3-447.3 | 3.13 | yes | 8.486x | 1.244x | 0.147x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,445.1 | 192.8-192.8 | 37.47 | **no** | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 268.6-268.6 | 5.22 | **no** | 5.151x | 0.718x | 0.139x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,317.2 | 306.8-306.8 | 37.77 | **no** | `a100_sxm_80gb-x387-hybrid` | 279.8 | 447.3-447.3 | 3.13 | yes | 8.283x | 0.686x | 0.083x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,445.1 | 192.8-192.8 | 37.47 | **no** | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 268.6-268.6 | 5.22 | **no** | 5.151x | 0.718x | 0.139x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 2,135.8 | 159.8-159.8 | 66.85 | **no** | `a100_sxm_80gb-x387-hybrid` | 259.3 | 381.0-381.0 | 3.40 | yes | 8.236x | 0.419x | 0.051x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,445.1 | 192.8-192.8 | 37.47 | **no** | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 268.6-268.6 | 5.22 | **no** | 5.151x | 0.718x | 0.139x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 1,191.4 | 79.4-79.4 | 75.02 | **no** | `a100_sxm_80gb-x387-hybrid` | 161.4 | 202.4-202.4 | 3.99 | yes | 7.379x | 0.392x | 0.053x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 1,058.3 | 97.4-97.4 | 54.32 | **no** | `a100_sxm_80gb-x2574-hybrid` | 280.6 | 268.6-268.6 | 5.22 | **no** | 3.772x | 0.363x | 0.096x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 359.9 | 38.3-38.3 | 46.94 | **no** | `a100_sxm_80gb-x387-hybrid` | 77.9 | 101.5-101.5 | 3.83 | yes | 4.622x | 0.378x | 0.082x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 384.3 | 24.6-24.6 | 77.98 | **no** | `a100_sxm_80gb-x2574-hybrid` | 200.3 | 136.7-136.7 | 7.32 | **no** | 1.919x | 0.180x | 0.094x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 93.6 | 31.1-31.1 | 15.07 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 103.2 | 6.2-6.2 | 83.64 | **no** | `a100_sxm_80gb-x2574-hybrid` | 106.2 | 60.4-60.4 | 8.80 | **no** | 0.972x | 0.102x | 0.105x |

**Does the ratio compress?** Of 19 class rows in this study, 19 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.051x to 0.147x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 10 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,431.3 | 773.8-773.8 | 22.17 | **no** | `a100_sxm_80gb-x73-hybrid` | 337.6 | 887.7-887.7 | 1.90 | yes | 10.164x | 0.872x | 0.086x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 2,917.0 | 529.9-529.9 | 27.52 | **no** | `a100_sxm_80gb-x112-hybrid` | 344.2 | 898.4-898.4 | 1.92 | yes | 8.475x | 0.590x | 0.070x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,431.3 | 773.8-773.8 | 22.17 | **no** | `a100_sxm_80gb-x73-hybrid` | 337.6 | 887.7-887.7 | 1.90 | yes | 10.164x | 0.872x | 0.086x |
| DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 2,917.0 | 529.9-529.9 | 27.52 | **no** | `a100_sxm_80gb-x112-hybrid` | 344.2 | 898.4-898.4 | 1.92 | yes | 8.475x | 0.590x | 0.070x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,431.3 | 773.8-773.8 | 22.17 | **no** | `a100_sxm_80gb-x73-hybrid` | 337.6 | 887.7-887.7 | 1.90 | yes | 10.164x | 0.872x | 0.086x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 2,917.0 | 529.9-529.9 | 27.52 | **no** | `a100_sxm_80gb-x112-hybrid` | 344.2 | 898.4-898.4 | 1.92 | yes | 8.475x | 0.590x | 0.070x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,431.3 | 773.8-773.8 | 22.17 | **no** | `a100_sxm_80gb-x73-hybrid` | 337.6 | 887.7-887.7 | 1.90 | yes | 10.164x | 0.872x | 0.086x |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 2,917.0 | 529.9-529.9 | 27.52 | **no** | `a100_sxm_80gb-x112-hybrid` | 344.2 | 898.4-898.4 | 1.92 | yes | 8.475x | 0.590x | 0.070x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 3,431.3 | 773.8-773.8 | 22.17 | **no** | `a100_sxm_80gb-x73-hybrid` | 316.4 | 745.1-745.1 | 2.12 | yes | 10.846x | 1.039x | 0.096x |
| DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 2,917.0 | 529.9-529.9 | 27.52 | **no** | `a100_sxm_80gb-x112-hybrid` | 338.9 | 854.6-854.6 | 1.98 | yes | 8.607x | 0.620x | 0.072x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 3,390.4 | 840.2-840.2 | 20.18 | **no** | `a100_sxm_80gb-x146-hybrid` | 314.6 | 692.5-692.5 | 2.27 | yes | 10.776x | 1.213x | 0.113x |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 2,891.2 | 887.8-887.8 | 16.28 | **no** | `a100_sxm_80gb-x224-hybrid` | 333.3 | 769.6-769.6 | 2.17 | yes | 8.674x | 1.154x | 0.133x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,378.5 | 839.6-839.6 | 20.12 | **no** | `a100_sxm_80gb-x335-hybrid` | 313.9 | 620.0-620.0 | 2.53 | yes | 10.764x | 1.354x | 0.126x |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 2,891.2 | 887.8-887.8 | 16.28 | **no** | `a100_sxm_80gb-x448-hybrid` | 327.6 | 642.7-642.7 | 2.55 | yes | 8.827x | 1.381x | 0.156x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,833.9 | 415.0-415.0 | 34.14 | **no** | `a100_sxm_80gb-x335-hybrid` | 211.0 | 310.9-310.9 | 3.39 | yes | 13.433x | 1.335x | 0.099x |
| DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,675.7 | 459.4-459.4 | 29.12 | **no** | `a100_sxm_80gb-x672-hybrid` | 269.0 | 388.1-388.1 | 3.46 | yes | 9.948x | 1.184x | 0.119x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,292.9 | 190.5-190.5 | 33.93 | **no** | `a100_sxm_80gb-x335-hybrid` | 106.5 | 160.7-160.7 | 3.31 | yes | 12.136x | 1.185x | 0.098x |
| DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 1,739.9 | 225.4-225.4 | 38.59 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.0 | 193.6-193.6 | 4.00 | yes | 11.223x | 1.164x | 0.104x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 378.8 | 121.4-121.4 | 15.60 | **no** | `a100_sxm_80gb-x335-hybrid` | 45.8 | 72.4-72.4 | 3.16 | yes | 8.263x | 1.676x | 0.203x |
| DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 566.3 | 172.6-172.6 | 16.40 | **no** | `a100_sxm_80gb-x672-hybrid` | 69.3 | 101.0-101.0 | 3.43 | yes | 8.174x | 1.709x | 0.209x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.070x to 0.209x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-flash-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 3,440.9 | 857.0-857.0 | 20.08 | **no** | `a100_sxm_80gb-x67-hybrid` | 341.4 | 917.7-917.7 | 1.86 | yes | 10.078x | 0.934x | 0.093x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3,133.6 | 880.8-880.8 | 17.79 | **no** | `a100_sxm_80gb-x112-hybrid` | 345.9 | 915.1-915.1 | 1.89 | yes | 9.059x | 0.963x | 0.106x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 3,440.9 | 857.0-857.0 | 20.08 | **no** | `a100_sxm_80gb-x67-hybrid` | 341.4 | 917.7-917.7 | 1.86 | yes | 10.078x | 0.934x | 0.093x |
| DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3,133.6 | 880.8-880.8 | 17.79 | **no** | `a100_sxm_80gb-x112-hybrid` | 345.9 | 915.1-915.1 | 1.89 | yes | 9.059x | 0.963x | 0.106x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 3,440.9 | 857.0-857.0 | 20.08 | **no** | `a100_sxm_80gb-x67-hybrid` | 341.4 | 917.7-917.7 | 1.86 | yes | 10.078x | 0.934x | 0.093x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3,133.6 | 880.8-880.8 | 17.79 | **no** | `a100_sxm_80gb-x112-hybrid` | 345.9 | 915.1-915.1 | 1.89 | yes | 9.059x | 0.963x | 0.106x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 3,440.9 | 857.0-857.0 | 20.08 | **no** | `a100_sxm_80gb-x67-hybrid` | 341.4 | 917.7-917.7 | 1.86 | yes | 10.078x | 0.934x | 0.093x |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3,133.6 | 880.8-880.8 | 17.79 | **no** | `a100_sxm_80gb-x112-hybrid` | 345.9 | 915.1-915.1 | 1.89 | yes | 9.059x | 0.963x | 0.106x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 3,440.9 | 857.0-857.0 | 20.08 | **no** | `a100_sxm_80gb-x67-hybrid` | 315.0 | 739.7-739.7 | 2.13 | yes | 10.924x | 1.159x | 0.106x |
| DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 3,133.6 | 880.8-880.8 | 17.79 | **no** | `a100_sxm_80gb-x112-hybrid` | 340.8 | 871.9-871.9 | 1.95 | yes | 9.195x | 1.010x | 0.110x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 3,402.5 | 845.2-845.2 | 20.13 | **no** | `a100_sxm_80gb-x146-hybrid` | 316.9 | 704.0-704.0 | 2.25 | yes | 10.738x | 1.201x | 0.112x |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 3,105.4 | 894.8-894.8 | 17.35 | **no** | `a100_sxm_80gb-x224-hybrid` | 335.2 | 783.6-783.6 | 2.14 | yes | 9.265x | 1.142x | 0.123x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,390.5 | 844.5-844.5 | 20.07 | **no** | `a100_sxm_80gb-x335-hybrid` | 316.0 | 632.1-632.1 | 2.50 | yes | 10.728x | 1.336x | 0.125x |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,105.4 | 894.8-894.8 | 17.35 | **no** | `a100_sxm_80gb-x448-hybrid` | 329.3 | 652.5-652.5 | 2.52 | yes | 9.430x | 1.371x | 0.145x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,971.8 | 418.7-418.7 | 35.49 | **no** | `a100_sxm_80gb-x335-hybrid` | 214.1 | 321.8-321.8 | 3.33 | yes | 13.881x | 1.301x | 0.094x |
| DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,064.1 | 462.8-462.8 | 33.10 | **no** | `a100_sxm_80gb-x672-hybrid` | 271.7 | 395.8-395.8 | 3.43 | yes | 11.276x | 1.169x | 0.104x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,387.9 | 193.6-193.6 | 35.84 | **no** | `a100_sxm_80gb-x335-hybrid` | 107.3 | 167.8-167.8 | 3.20 | yes | 12.933x | 1.154x | 0.089x |
| DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 2,330.5 | 227.5-227.5 | 51.22 | **no** | `a100_sxm_80gb-x672-hybrid` | 155.9 | 198.9-198.9 | 3.92 | yes | 14.953x | 1.144x | 0.077x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 412.3 | 126.7-126.7 | 16.27 | **no** | `a100_sxm_80gb-x335-hybrid` | 46.4 | 79.1-79.1 | 2.94 | yes | 8.881x | 1.602x | 0.180x |
| DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 843.4 | 177.9-177.9 | 23.70 | **no** | `a100_sxm_80gb-x672-hybrid` | 69.9 | 106.6-106.6 | 3.28 | yes | 12.059x | 1.670x | 0.138x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.077x to 0.180x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-200k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,734.0 | 551.6-551.6 | 15.72 | **no** | `a100_sxm_80gb-x391-hybrid` | 166.4 | 280.7-280.7 | 2.96 | yes | 10.418x | 1.965x | 0.189x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 1,564.9 | 343.0-343.0 | 22.81 | **no** | `a100_sxm_80gb-x336-hybrid` | 167.5 | 294.1-294.1 | 2.85 | yes | 9.344x | 1.166x | 0.125x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,734.0 | 551.6-551.6 | 15.72 | **no** | `a100_sxm_80gb-x391-hybrid` | 166.4 | 280.7-280.7 | 2.96 | yes | 10.418x | 1.965x | 0.189x |
| DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,350.3 | 306.1-306.1 | 22.05 | **no** | `a100_sxm_80gb-x783-hybrid` | 165.1 | 225.8-225.8 | 3.66 | yes | 8.178x | 1.356x | 0.166x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,734.0 | 551.6-551.6 | 15.72 | **no** | `a100_sxm_80gb-x391-hybrid` | 166.4 | 280.7-280.7 | 2.96 | yes | 10.418x | 1.965x | 0.189x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,350.3 | 306.1-306.1 | 22.05 | **no** | `a100_sxm_80gb-x783-hybrid` | 165.1 | 225.8-225.8 | 3.66 | yes | 8.178x | 1.356x | 0.166x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,734.0 | 551.6-551.6 | 15.72 | **no** | `a100_sxm_80gb-x391-hybrid` | 166.4 | 280.7-280.7 | 2.96 | yes | 10.418x | 1.965x | 0.189x |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,350.3 | 306.1-306.1 | 22.05 | **no** | `a100_sxm_80gb-x783-hybrid` | 165.1 | 225.8-225.8 | 3.66 | yes | 8.178x | 1.356x | 0.166x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,734.0 | 551.6-551.6 | 15.72 | **no** | `a100_sxm_80gb-x391-hybrid` | 166.4 | 280.7-280.7 | 2.96 | yes | 10.418x | 1.965x | 0.189x |
| DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,350.3 | 306.1-306.1 | 22.05 | **no** | `a100_sxm_80gb-x783-hybrid` | 165.1 | 225.8-225.8 | 3.66 | yes | 8.178x | 1.356x | 0.166x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,731.6 | 295.2-295.2 | 29.33 | **no** | `a100_sxm_80gb-x391-hybrid` | 166.4 | 280.7-280.7 | 2.96 | yes | 10.404x | 1.052x | 0.101x |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,350.3 | 306.1-306.1 | 22.05 | **no** | `a100_sxm_80gb-x783-hybrid` | 165.1 | 225.8-225.8 | 3.66 | yes | 8.178x | 1.356x | 0.166x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,666.7 | 153.8-153.8 | 54.17 | **no** | `a100_sxm_80gb-x391-hybrid` | 156.9 | 250.4-250.4 | 3.13 | yes | 10.621x | 0.614x | 0.058x |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1,313.4 | 157.5-157.5 | 41.68 | **no** | `a100_sxm_80gb-x783-hybrid` | 165.1 | 225.8-225.8 | 3.66 | yes | 7.955x | 0.698x | 0.088x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,119.1 | 76.3-76.3 | 73.29 | **no** | `a100_sxm_80gb-x391-hybrid` | 89.7 | 113.8-113.8 | 3.94 | yes | 12.471x | 0.671x | 0.054x |
| DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 961.1 | 79.7-79.7 | 60.32 | **no** | `a100_sxm_80gb-x783-hybrid` | 123.8 | 144.9-144.9 | 4.27 | yes | 7.762x | 0.550x | 0.071x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 404.3 | 36.0-36.0 | 56.22 | **no** | `a100_sxm_80gb-x391-hybrid` | 36.2 | 50.6-50.6 | 3.58 | yes | 11.162x | 0.710x | 0.064x |
| DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 364.1 | 20.1-20.1 | 90.68 | **no** | `a100_sxm_80gb-x783-hybrid` | 57.4 | 64.4-64.4 | 4.45 | yes | 6.343x | 0.312x | 0.049x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 110.7 | 26.1-26.1 | 21.21 | **no** | `a100_sxm_80gb-x391-hybrid` | 13.1 | 21.8-21.8 | 3.02 | yes | 8.430x | 1.199x | 0.142x |
| DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 98.9 | 18.9-18.9 | 26.18 | **no** | `a100_sxm_80gb-x783-hybrid` | 21.8 | 30.4-30.4 | 3.59 | yes | 4.537x | 0.621x | 0.137x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.049x to 0.189x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-32k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 1,862.0 | 588.3-588.3 | 15.83 | **no** | `a100_sxm_80gb-x368-hybrid` | 167.8 | 304.7-304.7 | 2.75 | yes | 11.099x | 1.931x | 0.174x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,632.1 | 347.1-347.1 | 23.51 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.3 | 313.3-313.3 | 2.69 | yes | 9.700x | 1.108x | 0.114x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 1,862.0 | 588.3-588.3 | 15.83 | **no** | `a100_sxm_80gb-x368-hybrid` | 167.8 | 304.7-304.7 | 2.75 | yes | 11.099x | 1.931x | 0.174x |
| DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,632.1 | 347.1-347.1 | 23.51 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.3 | 313.3-313.3 | 2.69 | yes | 9.700x | 1.108x | 0.114x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 1,862.0 | 588.3-588.3 | 15.83 | **no** | `a100_sxm_80gb-x368-hybrid` | 167.8 | 304.7-304.7 | 2.75 | yes | 11.099x | 1.931x | 0.174x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,632.1 | 347.1-347.1 | 23.51 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.3 | 313.3-313.3 | 2.69 | yes | 9.700x | 1.108x | 0.114x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 1,862.0 | 588.3-588.3 | 15.83 | **no** | `a100_sxm_80gb-x368-hybrid` | 167.8 | 304.7-304.7 | 2.75 | yes | 11.099x | 1.931x | 0.174x |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,632.1 | 347.1-347.1 | 23.51 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.3 | 313.3-313.3 | 2.69 | yes | 9.700x | 1.108x | 0.114x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 1,862.0 | 588.3-588.3 | 15.83 | **no** | `a100_sxm_80gb-x368-hybrid` | 167.8 | 304.7-304.7 | 2.75 | yes | 11.099x | 1.931x | 0.174x |
| DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,632.1 | 347.1-347.1 | 23.51 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.3 | 313.3-313.3 | 2.69 | yes | 9.700x | 1.108x | 0.114x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 1,849.5 | 317.6-317.6 | 29.12 | **no** | `a100_sxm_80gb-x368-hybrid` | 167.8 | 304.7-304.7 | 2.75 | yes | 11.024x | 1.042x | 0.095x |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,632.1 | 347.1-347.1 | 23.51 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.3 | 313.3-313.3 | 2.69 | yes | 9.700x | 1.108x | 0.114x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,796.0 | 155.7-155.7 | 57.69 | **no** | `a100_sxm_80gb-x391-hybrid` | 158.0 | 267.7-267.7 | 2.95 | yes | 11.367x | 0.581x | 0.051x |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1,624.3 | 176.8-176.8 | 45.94 | **no** | `a100_sxm_80gb-x448-hybrid` | 162.1 | 270.0-270.0 | 3.00 | yes | 10.020x | 0.655x | 0.065x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,301.5 | 77.5-77.5 | 83.95 | **no** | `a100_sxm_80gb-x391-hybrid` | 93.6 | 130.3-130.3 | 3.59 | yes | 13.900x | 0.595x | 0.043x |
| DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,466.9 | 172.8-172.8 | 42.44 | **no** | `a100_sxm_80gb-x672-hybrid` | 119.3 | 152.5-152.5 | 3.91 | yes | 12.301x | 1.134x | 0.092x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 506.1 | 37.0-37.0 | 68.36 | **no** | `a100_sxm_80gb-x391-hybrid` | 37.4 | 52.0-52.0 | 3.60 | yes | 13.522x | 0.712x | 0.053x |
| DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 847.5 | 86.5-86.5 | 49.00 | **no** | `a100_sxm_80gb-x672-hybrid` | 54.2 | 68.2-68.2 | 3.97 | yes | 15.645x | 1.269x | 0.081x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 142.2 | 28.5-28.5 | 24.97 | **no** | `a100_sxm_80gb-x391-hybrid` | 14.3 | 18.6-18.6 | 3.86 | yes | 9.917x | 1.535x | 0.155x |
| DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 331.3 | 40.2-40.2 | 41.18 | **no** | `a100_sxm_80gb-x672-hybrid` | 20.0 | 32.9-32.9 | 3.04 | yes | 16.566x | 1.222x | 0.074x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.043x to 0.174x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100-pro-8k`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 1,936.6 | 324.7-324.7 | 29.82 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 302.2-302.2 | 2.75 | yes | 11.640x | 1.074x | 0.092x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,717.0 | 349.1-349.1 | 24.59 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.4 | 313.4-313.4 | 2.69 | yes | 10.198x | 1.114x | 0.109x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 1,936.6 | 324.7-324.7 | 29.82 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 302.2-302.2 | 2.75 | yes | 11.640x | 1.074x | 0.092x |
| DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,717.0 | 349.1-349.1 | 24.59 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.4 | 313.4-313.4 | 2.69 | yes | 10.198x | 1.114x | 0.109x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 1,936.6 | 324.7-324.7 | 29.82 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 302.2-302.2 | 2.75 | yes | 11.640x | 1.074x | 0.092x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,717.0 | 349.1-349.1 | 24.59 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.4 | 313.4-313.4 | 2.69 | yes | 10.198x | 1.114x | 0.109x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 1,936.6 | 324.7-324.7 | 29.82 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 302.2-302.2 | 2.75 | yes | 11.640x | 1.074x | 0.092x |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,717.0 | 349.1-349.1 | 24.59 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.4 | 313.4-313.4 | 2.69 | yes | 10.198x | 1.114x | 0.109x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 1,936.6 | 324.7-324.7 | 29.82 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 302.2-302.2 | 2.75 | yes | 11.640x | 1.074x | 0.092x |
| DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,717.0 | 349.1-349.1 | 24.59 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.4 | 313.4-313.4 | 2.69 | yes | 10.198x | 1.114x | 0.109x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 1,936.6 | 324.7-324.7 | 29.82 | **no** | `a100_sxm_80gb-x361-hybrid` | 166.4 | 302.2-302.2 | 2.75 | yes | 11.640x | 1.074x | 0.092x |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1,717.0 | 349.1-349.1 | 24.59 | **no** | `a100_sxm_80gb-x336-hybrid` | 168.4 | 313.4-313.4 | 2.69 | yes | 10.198x | 1.114x | 0.109x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 1,870.2 | 166.3-166.3 | 56.22 | **no** | `a100_sxm_80gb-x391-hybrid` | 158.1 | 267.8-267.8 | 2.95 | yes | 11.827x | 0.621x | 0.053x |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1,716.4 | 177.3-177.3 | 48.39 | **no** | `a100_sxm_80gb-x448-hybrid` | 162.2 | 270.1-270.1 | 3.00 | yes | 10.580x | 0.657x | 0.062x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 1,334.2 | 77.7-77.7 | 85.86 | **no** | `a100_sxm_80gb-x391-hybrid` | 93.8 | 131.7-131.7 | 3.56 | yes | 14.221x | 0.590x | 0.041x |
| DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,541.0 | 173.7-173.7 | 44.37 | **no** | `a100_sxm_80gb-x672-hybrid` | 119.4 | 153.1-153.1 | 3.90 | yes | 12.903x | 1.135x | 0.088x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 525.7 | 37.2-37.2 | 70.70 | **no** | `a100_sxm_80gb-x391-hybrid` | 37.5 | 53.7-53.7 | 3.49 | yes | 14.003x | 0.692x | 0.049x |
| DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 873.0 | 87.0-87.0 | 50.20 | **no** | `a100_sxm_80gb-x672-hybrid` | 54.3 | 69.8-69.8 | 3.89 | yes | 16.072x | 1.245x | 0.077x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 148.5 | 28.9-28.9 | 25.72 | **no** | `a100_sxm_80gb-x391-hybrid` | 14.4 | 19.8-19.8 | 3.65 | yes | 10.308x | 1.461x | 0.142x |
| DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 359.7 | 69.7-69.7 | 25.79 | **no** | `a100_sxm_80gb-x672-hybrid` | 20.1 | 33.0-33.0 | 3.04 | yes | 17.918x | 2.112x | 0.118x |

**Does the ratio compress?** Of 20 class rows in this study, 20 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.041x to 0.142x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 20 ROM rows and 20 of 20 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 10,793.3 | not applicable | -- | -- | `b200_sxm-x8-tensor` | 943.8 | not applicable | -- | -- | 11.436x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 5,080.9 | not applicable | -- | -- | `b200_sxm-x58-nvl72-tensor` | 1,268.9 | not applicable | -- | -- | 4.004x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 9,880.7 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 1,202.3 | not applicable | -- | -- | 8.218x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 4,545.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,258.3 | not applicable | -- | -- | 3.613x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 9,880.7 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 1,178.6 | not applicable | -- | -- | 8.383x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 4,545.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,255.0 | not applicable | -- | -- | 3.622x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 9,796.1 | not applicable | -- | -- | `b200_sxm-x87-nvl72-hybrid` | 1,207.9 | not applicable | -- | -- | 8.110x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 4,545.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,242.3 | not applicable | -- | -- | 3.659x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 9,672.8 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,217.5 | not applicable | -- | -- | 7.945x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 4,521.9 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,242.6 | not applicable | -- | -- | 3.639x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 8,789.7 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,170.8 | not applicable | -- | -- | 7.507x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,937.8 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,214.0 | not applicable | -- | -- | 3.244x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 7,163.6 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,087.4 | not applicable | -- | -- | 6.588x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 3,112.9 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,160.5 | not applicable | -- | -- | 2.682x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,148.4 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 811.6 | not applicable | -- | -- | 3.879x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 1,209.8 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 951.5 | not applicable | -- | -- | 1.271x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 801.0 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 439.4 | not applicable | -- | -- | 1.823x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 330.9 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 613.1 | not applicable | -- | -- | 0.540x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 201.1 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 166.6 | not applicable | -- | -- | 1.207x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 84.0 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 280.0 | not applicable | -- | -- | 0.300x | -- | -- |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 3,374.2 | 1,013.1-1,013.1 | 16.65 | **no** | `b200_sxm-x29-nvl72-tensor` | 599.7 | 2,149.1-2,149.1 | 1.40 | yes | 5.626x | 0.471x | 0.084x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 2,899.9 | 529.5-529.5 | 27.39 | **no** | `b200_sxm-x58-nvl72-tensor` | 607.7 | 2,192.7-2,192.7 | 1.39 | yes | 4.772x | 0.241x | 0.051x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 3,373.9 | 951.6-951.6 | 17.73 | **no** | `b200_sxm-x31-hybrid` | 585.0 | 1,899.5-1,899.5 | 1.54 | yes | 5.767x | 0.501x | 0.087x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2,543.0 | 2,043.9-2,043.9 | 6.22 | **no** | `b200_sxm-x231-nvl72-hybrid` | 603.8 | 2,141.8-2,141.8 | 1.41 | yes | 4.212x | 0.954x | 0.227x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 3,373.9 | 951.6-951.6 | 17.73 | **no** | `b200_sxm-x31-hybrid` | 585.0 | 1,899.5-1,899.5 | 1.54 | yes | 5.767x | 0.501x | 0.087x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2,543.0 | 2,043.9-2,043.9 | 6.22 | **no** | `b200_sxm-x231-nvl72-hybrid` | 603.8 | 2,141.8-2,141.8 | 1.41 | yes | 4.212x | 0.954x | 0.227x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 3,373.9 | 951.6-951.6 | 17.73 | **no** | `b200_sxm-x31-hybrid` | 547.7 | 1,498.9-1,498.9 | 1.83 | yes | 6.160x | 0.635x | 0.103x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2,543.0 | 2,043.9-2,043.9 | 6.22 | **no** | `b200_sxm-x231-nvl72-hybrid` | 594.1 | 2,071.6-2,071.6 | 1.43 | yes | 4.280x | 0.987x | 0.230x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x70` | 3,362.0 | 813.5-813.5 | 20.66 | **no** | `b200_sxm-x36-hybrid` | 501.7 | 1,177.9-1,177.9 | 2.13 | yes | 6.702x | 0.691x | 0.103x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2,543.0 | 2,043.9-2,043.9 | 6.22 | **no** | `b200_sxm-x231-nvl72-hybrid` | 576.4 | 1,763.9-1,763.9 | 1.63 | yes | 4.412x | 1.159x | 0.263x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 3,253.3 | 1,096.4-1,096.4 | 14.84 | **no** | `b200_sxm-x86-nvl72-hybrid` | 517.7 | 1,274.3-1,274.3 | 2.03 | yes | 6.284x | 0.860x | 0.137x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 2,543.0 | 2,043.9-2,043.9 | 6.22 | **no** | `b200_sxm-x231-nvl72-hybrid` | 572.4 | 1,716.6-1,716.6 | 1.67 | yes | 4.443x | 1.191x | 0.268x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 3,251.5 | 1,096.2-1,096.2 | 14.83 | **no** | `b200_sxm-x173-nvl72-hybrid` | 513.7 | 1,228.6-1,228.6 | 2.09 | yes | 6.330x | 0.892x | 0.141x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,541.0 | 2,034.4-2,034.4 | 6.25 | **no** | `b200_sxm-x347-nvl72-hybrid` | 552.7 | 1,489.5-1,489.5 | 1.86 | yes | 4.597x | 1.366x | 0.297x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,536.0 | 536.1-536.1 | 23.65 | **no** | `b200_sxm-x173-nvl72-hybrid` | 364.6 | 701.8-701.8 | 2.60 | yes | 6.956x | 0.764x | 0.110x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 2,071.6 | 1,078.3-1,078.3 | 9.61 | **no** | `b200_sxm-x347-nvl72-hybrid` | 442.1 | 890.6-890.6 | 2.48 | yes | 4.686x | 1.211x | 0.258x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 1,134.8 | 235.9-235.9 | 24.05 | **no** | `b200_sxm-x173-nvl72-hybrid` | 197.9 | 368.7-368.7 | 2.68 | yes | 5.735x | 0.640x | 0.112x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 1,018.1 | 292.9-292.9 | 17.38 | **no** | `b200_sxm-x347-nvl72-hybrid` | 275.2 | 449.6-449.6 | 3.06 | yes | 3.700x | 0.651x | 0.176x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 344.7 | 118.7-118.7 | 14.53 | **no** | `b200_sxm-x173-nvl72-hybrid` | 87.7 | 182.9-182.9 | 2.40 | yes | 3.932x | 0.649x | 0.165x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 295.8 | 199.6-199.6 | 7.41 | **no** | `b200_sxm-x347-nvl72-hybrid` | 132.3 | 249.7-249.7 | 2.65 | yes | 2.236x | 0.799x | 0.357x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,491.0 | 150.2-150.2 | 49.62 | **no** | `b200_sxm-x203-nvl72-hybrid` | 378.3 | 909.3-909.3 | 2.08 | yes | 3.942x | 0.165x | 0.042x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 1,539.2 | 340.1-340.1 | 22.63 | **no** | `b200_sxm-x173-nvl72-hybrid` | 376.7 | 907.1-907.1 | 2.08 | yes | 4.086x | 0.375x | 0.092x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,491.0 | 150.2-150.2 | 49.62 | **no** | `b200_sxm-x203-nvl72-hybrid` | 378.3 | 909.3-909.3 | 2.08 | yes | 3.942x | 0.165x | 0.042x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,156.1 | 804.4-804.4 | 7.19 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 833.4-833.4 | 2.23 | yes | 3.110x | 0.965x | 0.310x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,491.0 | 150.2-150.2 | 49.62 | **no** | `b200_sxm-x203-nvl72-hybrid` | 374.4 | 896.3-896.3 | 2.09 | yes | 3.982x | 0.168x | 0.042x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,156.1 | 804.4-804.4 | 7.19 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 833.4-833.4 | 2.23 | yes | 3.110x | 0.965x | 0.310x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,491.0 | 150.2-150.2 | 49.62 | **no** | `b200_sxm-x203-nvl72-hybrid` | 363.9 | 829.5-829.5 | 2.19 | yes | 4.098x | 0.181x | 0.044x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,156.1 | 804.4-804.4 | 7.19 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 833.4-833.4 | 2.23 | yes | 3.110x | 0.965x | 0.310x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,491.0 | 150.2-150.2 | 49.62 | **no** | `b200_sxm-x203-nvl72-hybrid` | 350.8 | 739.4-739.4 | 2.37 | yes | 4.250x | 0.203x | 0.048x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,156.1 | 804.4-804.4 | 7.19 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 833.4-833.4 | 2.23 | yes | 3.110x | 0.965x | 0.310x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,491.0 | 150.2-150.2 | 49.62 | **no** | `b200_sxm-x203-nvl72-hybrid` | 310.8 | 635.9-635.9 | 2.44 | yes | 4.798x | 0.236x | 0.049x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,156.1 | 804.4-804.4 | 7.19 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 356.5 | 749.4-749.4 | 2.38 | yes | 3.243x | 1.073x | 0.331x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1,491.0 | 150.2-150.2 | 49.62 | **no** | `b200_sxm-x203-nvl72-hybrid` | 257.2 | 416.2-416.2 | 3.09 | yes | 5.798x | 0.361x | 0.062x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 1,156.1 | 804.4-804.4 | 7.19 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 354.1 | 652.3-652.3 | 2.71 | yes | 3.265x | 1.233x | 0.378x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 959.9 | 74.3-74.3 | 64.56 | **no** | `b200_sxm-x203-nvl72-hybrid` | 148.6 | 212.6-212.6 | 3.49 | yes | 6.462x | 0.350x | 0.054x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1,038.8 | 95.3-95.3 | 54.49 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 293.7 | 401.7-401.7 | 3.66 | yes | 3.537x | 0.237x | 0.067x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 339.9 | 34.8-34.8 | 48.86 | **no** | `b200_sxm-x203-nvl72-hybrid` | 64.8 | 90.2-90.2 | 3.59 | yes | 5.242x | 0.386x | 0.074x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 551.7 | 24.2-24.2 | 114.05 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 189.8 | 201.2-201.2 | 4.72 | yes | 2.907x | 0.120x | 0.041x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 92.1 | 24.1-24.1 | 19.08 | **no** | `--` | -- | ----- | -- | **no** | --x | --x | --x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 168.6 | 6.1-6.1 | 139.01 | **no** | `b200_sxm-x1358-nvl72-hybrid` | 92.1 | 95.3-95.3 | 4.83 | yes | 1.831x | 0.064x | 0.035x |

**Does the ratio compress?** Of 39 class rows in this study, 39 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.035x to 0.378x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 40 ROM rows and 39 of 40 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n6_vs_a100`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 10,491.8 | not applicable | -- | -- | `a100_sxm_80gb-x16-hybrid` | 458.7 | not applicable | -- | -- | 22.873x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 5,099.4 | not applicable | -- | -- | `a100_sxm_80gb-x112-tensor` | 562.5 | not applicable | -- | -- | 9.066x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8,068.9 | not applicable | -- | -- | `a100_sxm_80gb-x272-tensor` | 544.1 | not applicable | -- | -- | 14.830x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,585.9 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 539.0 | not applicable | -- | -- | 6.653x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8,068.9 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 532.5 | not applicable | -- | -- | 15.153x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,585.9 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 539.0 | not applicable | -- | -- | 6.653x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 8,068.9 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 514.3 | not applicable | -- | -- | 15.690x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 3,585.9 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 534.5 | not applicable | -- | -- | 6.709x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 7,701.6 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 474.5 | not applicable | -- | -- | 16.233x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 3,199.3 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 520.1 | not applicable | -- | -- | 6.152x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 6,264.9 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 447.1 | not applicable | -- | -- | 14.013x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2,555.8 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 479.6 | not applicable | -- | -- | 5.329x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 4,574.0 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 430.7 | not applicable | -- | -- | 10.619x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1,700.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 442.4 | not applicable | -- | -- | 3.843x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 1,597.0 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 354.0 | not applicable | -- | -- | 4.511x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 526.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 402.4 | not applicable | -- | -- | 1.308x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 431.2 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 206.7 | not applicable | -- | -- | 2.086x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 136.6 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 286.6 | not applicable | -- | -- | 0.477x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 111.0 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 77.9 | not applicable | -- | -- | 1.425x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 34.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 133.3 | not applicable | -- | -- | 0.258x | -- | -- |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x79` | 3,263.9 | 1,328.0-1,328.0 | 12.29 | **no** | `a100_sxm_80gb-x78-hybrid` | 332.4 | 810.9-810.9 | 2.05 | yes | 9.819x | 1.638x | 0.167x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 2,899.9 | 522.7-522.7 | 27.74 | **no** | `a100_sxm_80gb-x112-hybrid` | 333.1 | 799.3-799.3 | 2.08 | yes | 8.707x | 0.654x | 0.075x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,233.0 | 1,224.8-1,224.8 | 13.20 | **no** | `a100_sxm_80gb-x85-hybrid` | 331.3 | 803.4-803.4 | 2.06 | yes | 9.760x | 1.525x | 0.156x |
| DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 2,141.3 | 429.9-429.9 | 24.90 | **no** | `a100_sxm_80gb-x560-hybrid` | 322.7 | 583.8-583.8 | 2.76 | yes | 6.636x | 0.736x | 0.111x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,233.0 | 1,224.8-1,224.8 | 13.20 | **no** | `a100_sxm_80gb-x85-hybrid` | 331.3 | 803.4-803.4 | 2.06 | yes | 9.760x | 1.525x | 0.156x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 2,141.3 | 429.9-429.9 | 24.90 | **no** | `a100_sxm_80gb-x560-hybrid` | 322.7 | 583.8-583.8 | 2.76 | yes | 6.636x | 0.736x | 0.111x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,233.0 | 1,224.8-1,224.8 | 13.20 | **no** | `a100_sxm_80gb-x85-hybrid` | 331.3 | 803.4-803.4 | 2.06 | yes | 9.760x | 1.525x | 0.156x |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 2,141.3 | 429.9-429.9 | 24.90 | **no** | `a100_sxm_80gb-x560-hybrid` | 322.7 | 583.8-583.8 | 2.76 | yes | 6.636x | 0.736x | 0.111x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 3,212.2 | 662.8-662.8 | 24.23 | **no** | `a100_sxm_80gb-x85-hybrid` | 311.7 | 678.8-678.8 | 2.30 | yes | 10.306x | 0.976x | 0.095x |
| DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 2,141.3 | 429.9-429.9 | 24.90 | **no** | `a100_sxm_80gb-x560-hybrid` | 322.7 | 583.8-583.8 | 2.76 | yes | 6.636x | 0.736x | 0.111x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 3,127.9 | 1,448.2-1,448.2 | 10.80 | **no** | `a100_sxm_80gb-x312-hybrid` | 324.1 | 671.9-671.9 | 2.41 | yes | 9.653x | 2.155x | 0.223x |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 2,141.3 | 429.9-429.9 | 24.90 | **no** | `a100_sxm_80gb-x560-hybrid` | 322.7 | 583.8-583.8 | 2.76 | yes | 6.636x | 0.736x | 0.111x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 3,082.3 | 806.8-806.8 | 19.10 | **no** | `a100_sxm_80gb-x312-hybrid` | 296.6 | 539.7-539.7 | 2.75 | yes | 10.391x | 1.495x | 0.144x |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 2,081.0 | 223.9-223.9 | 46.47 | **no** | `a100_sxm_80gb-x560-hybrid` | 322.7 | 583.8-583.8 | 2.76 | yes | 6.449x | 0.384x | 0.059x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 2,198.9 | 391.7-391.7 | 28.07 | **no** | `a100_sxm_80gb-x335-hybrid` | 195.1 | 283.0-283.0 | 3.45 | yes | 11.272x | 1.384x | 0.123x |
| DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1,360.1 | 93.9-93.9 | 72.40 | **no** | `a100_sxm_80gb-x672-hybrid` | 249.1 | 333.7-333.7 | 3.73 | yes | 5.459x | 0.281x | 0.052x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 884.5 | 172.0-172.0 | 25.72 | **no** | `a100_sxm_80gb-x335-hybrid` | 95.1 | 130.1-130.1 | 3.66 | yes | 9.301x | 1.322x | 0.142x |
| DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 477.9 | 212.6-212.6 | 11.24 | **no** | `a100_sxm_80gb-x672-hybrid` | 143.1 | 169.7-169.7 | 4.22 | yes | 3.339x | 1.253x | 0.375x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 314.0 | 106.0-106.0 | 14.81 | **no** | `a100_sxm_80gb-x335-hybrid` | 37.6 | 69.2-69.2 | 2.72 | yes | 8.348x | 1.531x | 0.183x |
| DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 128.2 | 23.0-23.0 | 27.83 | **no** | `a100_sxm_80gb-x672-hybrid` | 60.1 | 82.8-82.8 | 3.63 | yes | 2.133x | 0.278x | 0.130x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 1,397.4 | 488.1-488.1 | 14.31 | **no** | `a100_sxm_80gb-x384-hybrid` | 149.5 | 221.3-221.3 | 3.38 | yes | 9.350x | 2.206x | 0.236x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 1,451.0 | 233.5-233.5 | 31.07 | **no** | `a100_sxm_80gb-x504-hybrid` | 148.2 | 206.6-206.6 | 3.59 | yes | 9.790x | 1.130x | 0.115x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 950.4 | 134.8-134.8 | 35.25 | **no** | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 97.1-97.1 | 7.63 | **no** | 6.414x | 1.389x | 0.217x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 950.4 | 134.8-134.8 | 35.25 | **no** | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 97.1-97.1 | 7.63 | **no** | 6.414x | 1.389x | 0.217x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 950.4 | 134.8-134.8 | 35.25 | **no** | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 97.1-97.1 | 7.63 | **no** | 6.414x | 1.389x | 0.217x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 950.4 | 134.8-134.8 | 35.25 | **no** | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 97.1-97.1 | 7.63 | **no** | 6.414x | 1.389x | 0.217x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 950.4 | 134.8-134.8 | 35.25 | **no** | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 97.1-97.1 | 7.63 | **no** | 6.414x | 1.389x | 0.217x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 950.4 | 134.8-134.8 | 35.25 | **no** | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 97.1-97.1 | 7.63 | **no** | 6.414x | 1.389x | 0.217x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 832.3 | 68.4-68.4 | 60.80 | **no** | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 97.1-97.1 | 7.63 | **no** | 5.617x | 0.705x | 0.126x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 354.3 | 17.3-17.3 | 102.69 | **no** | `a100_sxm_80gb-x3694-hybrid` | 109.3 | 64.0-64.0 | 8.53 | **no** | 3.242x | 0.269x | 0.083x |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 100.3 | 4.3-4.3 | 116.12 | **no** | `a100_sxm_80gb-x3694-hybrid` | 53.1 | 28.6-28.6 | 9.28 | **no** | 1.887x | 0.151x | 0.080x |

**Does the ratio compress?** Of 31 class rows in this study, 31 move the ROM-versus-GPU ratio DOWN under speculation and 0 move it UP. The movement spans 0.052x to 0.375x. The ratio compresses: speculation is worth more to the GPU comparator than to the ROM design on most of this study's operating points.

**A moving ratio is not a win for either side.** At the most favourable sourced acceptance (5.00) speculation is worth having on 0 of 31 ROM rows and 22 of 31 GPU rows; on every other row the honest reading is that the design runs SLOWER with a drafter than without one. Where both sides lose, a ratio that rises means only that the comparator lost more.

### `n5_vs_b200-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 12,166.3 | not applicable | -- | -- | `b200_sxm-x2-tensor` | 872.0 | not applicable | -- | -- | 13.952x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N5-q4p25-SRAMKV-wafer-hybrid-x2-romfill` | 5,002.6 | not applicable | -- | -- | `b200_sxm-x58-nvl72-tensor` | 1,318.4 | not applicable | -- | -- | 3.794x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 9,598.9 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 1,285.1 | not applicable | -- | -- | 7.469x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 4,482.5 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,307.2 | not applicable | -- | -- | 3.429x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 9,598.9 | not applicable | -- | -- | `b200_sxm-x32-nvl72-tensor` | 1,258.1 | not applicable | -- | -- | 7.630x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 4,482.5 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,303.7 | not applicable | -- | -- | 3.438x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x170-romfill` | 9,518.8 | not applicable | -- | -- | `b200_sxm-x87-nvl72-hybrid` | 1,268.3 | not applicable | -- | -- | 7.505x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 4,482.5 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,289.9 | not applicable | -- | -- | 3.475x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 9,402.4 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,263.3 | not applicable | -- | -- | 7.443x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 4,459.3 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,282.0 | not applicable | -- | -- | 3.479x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 8,579.9 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,214.9 | not applicable | -- | -- | 7.062x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,878.2 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,251.5 | not applicable | -- | -- | 3.099x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 6,926.4 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 1,145.4 | not applicable | -- | -- | 6.047x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,053.5 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,199.0 | not applicable | -- | -- | 2.547x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 3,281.0 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 877.5 | not applicable | -- | -- | 3.739x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,199.2 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 1,010.0 | not applicable | -- | -- | 1.187x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 832.2 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 480.0 | not applicable | -- | -- | 1.734x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 330.8 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 671.6 | not applicable | -- | -- | 0.493x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 208.3 | not applicable | -- | -- | `b200_sxm-x173-nvl72-hybrid` | 179.0 | not applicable | -- | -- | 1.164x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 83.9 | not applicable | -- | -- | `b200_sxm-x347-nvl72-hybrid` | 306.9 | not applicable | -- | -- | 0.273x | -- | -- |

### `n6_vs_a100-quantised_variant`

| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau 5.00-5.00) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Qwen3-8B | 8,192 | 1 | `array` | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x8-romfill` | 11,712.7 | not applicable | -- | -- | `a100_sxm_80gb-x8-tensor` | 749.4 | not applicable | -- | -- | 15.630x | -- | -- |
| Qwen3-8B | 8,192 | 1 | `wafer` | `ROM-N6-q4p25-SRAMKV-wafer-hybrid-x2-romfill` | 5,014.9 | not applicable | -- | -- | `a100_sxm_80gb-x112-hybrid` | 731.5 | not applicable | -- | -- | 6.856x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,874.5 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 707.1 | not applicable | -- | -- | 11.137x | -- | -- |
| Qwen3-8B | 8,192 | 2 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 3,553.8 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 704.7 | not applicable | -- | -- | 5.043x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,874.5 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 707.1 | not applicable | -- | -- | 11.137x | -- | -- |
| Qwen3-8B | 8,192 | 4 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 3,553.8 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 704.7 | not applicable | -- | -- | 5.043x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,874.5 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 707.1 | not applicable | -- | -- | 11.137x | -- | -- |
| Qwen3-8B | 8,192 | 8 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 3,553.8 | not applicable | -- | -- | `a100_sxm_80gb-x448-hybrid` | 704.7 | not applicable | -- | -- | 5.043x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 7,510.6 | not applicable | -- | -- | `a100_sxm_80gb-x272-hybrid` | 707.1 | not applicable | -- | -- | 10.622x | -- | -- |
| Qwen3-8B | 8,192 | 16 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 3,163.6 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 704.7 | not applicable | -- | -- | 4.489x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 6,021.8 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 704.1 | not applicable | -- | -- | 8.552x | -- | -- |
| Qwen3-8B | 8,192 | 32 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 2,525.5 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 704.7 | not applicable | -- | -- | 3.584x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 4,434.2 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 676.7 | not applicable | -- | -- | 6.553x | -- | -- |
| Qwen3-8B | 8,192 | 64 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 1,680.2 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 704.7 | not applicable | -- | -- | 2.384x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 1,589.6 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 504.8 | not applicable | -- | -- | 3.149x | -- | -- |
| Qwen3-8B | 8,192 | 256 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 524.5 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 608.4 | not applicable | -- | -- | 0.862x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 430.2 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 250.4 | not applicable | -- | -- | 1.718x | -- | -- |
| Qwen3-8B | 8,192 | 1024 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 136.6 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 377.7 | not applicable | -- | -- | 0.362x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `array` | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340` | 111.0 | not applicable | -- | -- | `a100_sxm_80gb-x335-hybrid` | 89.7 | not applicable | -- | -- | 1.237x | -- | -- |
| Qwen3-8B | 8,192 | 4096 | `wafer` | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12` | 34.4 | not applicable | -- | -- | `a100_sxm_80gb-x672-hybrid` | 156.9 | not applicable | -- | -- | 0.219x | -- | -- |

## Where the drafter lives on a ROM machine

The locality rule -- `stored/peak` is a technology constant -- is the load-bearing assumption of the whole ROM verdict. A pass that reads only the drafter's region uses only that region's read ports and takes exactly as long as sweeping the entire array. Two placements are therefore priced side by side, and the second is an architectural proposal this study **has not costed in silicon area**.

The same rule is what makes a SEQUENTIAL draft step expensive here. A per-position operation that moves only a small table is nearly free on a global-bandwidth store and costs a full array sweep on this one, so a drafter with `gamma` sequential applications pays `gamma` sweeps for them. That term is charged in full below; on a bandwidth store the bytes it moves are not separately charged at all, because this repository's model configs carry no size for the table -- an omission whose size, on DeepSeek-V4-Pro-0813, is the externally published 132,382,720 B per draft token, 0.33% of the 39,666,603,980 B target pass.

| study | model | ctx | batch | class | design | tau* draft in ROM | tau* draft in KV store | KV placement feasible | why not |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 15.93 | 1.95 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 52.45 | 4.77 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 15.93 | 1.95 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 52.45 | 4.77 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 15.93 | 1.95 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 52.45 | 4.77 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 15.93 | 1.95 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 52.45 | 4.77 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 30.12 | 2.17 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 52.45 | 4.77 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 43.55 | 2.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 52.45 | 4.77 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 84.26 | 2.65 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 67.50 | 4.69 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 93.89 | 4.51 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 79.10 | 8.13 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 94.70 | 6.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 99.35 | 12.98 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 67.88 | 8.43 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 39.39 | 6.35 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 23.52 | 2.19 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 34.37 | 4.97 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 23.52 | 2.19 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 34.37 | 4.97 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 23.52 | 2.19 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 34.37 | 4.97 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 23.52 | 2.19 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 34.37 | 4.97 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 23.52 | 2.19 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 34.37 | 4.97 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 43.57 | 2.72 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 49.10 | 4.73 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 83.60 | 4.04 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 29.26 | 4.95 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 161.52 | 6.72 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 50.44 | 9.68 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 132.38 | 9.23 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 107.37 | 19.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 42.50 | 9.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 68.16 | 12.91 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 19.57 | 2.07 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 46.68 | 2.91 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 19.57 | 2.07 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 46.68 | 2.91 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 19.57 | 2.07 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 46.68 | 2.91 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | 19.57 | 2.07 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 46.68 | 2.91 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 23.27 | 2.05 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 46.68 | 2.91 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 42.54 | 2.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 46.68 | 2.91 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 54.14 | 2.69 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 20.47 | 3.30 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 86.43 | 5.51 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 32.05 | 5.52 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 143.96 | 7.76 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 59.71 | 9.39 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | 46.99 | 8.29 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 78.21 | 5.94 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 26.75 | 2.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 23.30 | 3.88 | NO | the KV store has no room for it |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 26.75 | 2.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 20.78 | 2.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 26.75 | 2.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 20.78 | 2.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 26.75 | 2.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 20.78 | 2.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 26.75 | 2.34 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 20.78 | 2.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 53.41 | 2.91 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 38.69 | 2.66 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 50.94 | 3.69 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 74.62 | 3.81 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 135.38 | 7.27 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 93.43 | 5.29 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 94.78 | 8.86 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 126.56 | 6.72 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 31.24 | 8.69 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 34.77 | 4.95 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 30.23 | 2.07 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 55.03 | 4.77 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 30.23 | 2.07 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 55.03 | 4.77 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 30.23 | 2.07 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 55.03 | 4.77 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 30.23 | 2.07 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 55.03 | 4.77 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 30.23 | 2.07 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 55.03 | 4.77 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 58.54 | 2.85 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 55.03 | 4.77 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 50.89 | 3.08 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 108.06 | 8.33 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 84.56 | 5.78 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 87.05 | 8.48 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 95.13 | 6.67 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 111.53 | 13.72 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 72.22 | 8.49 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 41.11 | 13.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 18.60 | 2.18 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 69.94 | 8.67 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 18.60 | 2.18 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 69.94 | 8.67 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 18.60 | 2.18 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 69.94 | 8.67 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 18.60 | 2.18 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 69.94 | 8.67 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 22.38 | 2.14 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 69.94 | 8.67 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 41.37 | 2.69 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 69.94 | 8.67 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 80.80 | 4.02 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 60.02 | 8.73 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 88.87 | 6.52 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 108.73 | 15.10 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 148.02 | 9.38 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 120.86 | 21.29 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 47.50 | 9.17 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 42.36 | 10.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17.35 | 2.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x10-romfill` | 32.57 | 2.41 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17.35 | 2.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 36.18 | 4.43 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17.35 | 2.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 36.18 | 4.43 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17.35 | 2.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 36.18 | 4.43 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 17.13 | 2.11 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 36.18 | 4.43 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 16.56 | 2.13 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 27.39 | 4.63 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 31.18 | 2.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 27.39 | 4.63 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 54.72 | 5.56 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 51.26 | 7.79 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 48.32 | 7.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 74.34 | 13.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 17.09 | 5.98 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 30.15 | 13.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13.40 | 2.14 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 44.21 | 2.83 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13.40 | 2.14 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 26.56 | 4.76 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13.40 | 2.14 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 26.56 | 4.76 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13.40 | 2.14 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 26.56 | 4.76 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 23.71 | 2.55 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 26.56 | 4.76 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 22.31 | 2.63 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 18.49 | 4.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 41.74 | 3.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 18.58 | 4.81 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 65.22 | 7.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 32.90 | 9.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 36.02 | 6.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 77.50 | 21.16 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 18.77 | 8.13 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 28.80 | 17.81 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x192` | 17.21 | 1.96 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 30.74 | 2.92 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 10.80 | 2.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 39.19 | 2.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x111` | 10.80 | 2.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 39.19 | 2.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x113` | 12.05 | 2.06 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 39.19 | 2.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 20.58 | 2.01 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 39.19 | 2.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 28.91 | 2.36 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5` | 39.19 | 2.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 29.35 | 3.31 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 13.00 | 3.08 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 45.22 | 6.08 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 20.08 | 4.93 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 32.63 | 5.56 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 36.84 | 8.10 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 16.63 | 7.25 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 39.93 | 4.39 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x250` | 22.39 | 2.20 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 41.64 | 3.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 14.49 | 2.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 23.44 | 2.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 14.49 | 2.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 23.44 | 2.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 14.49 | 2.28 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 23.44 | 2.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 24.11 | 2.12 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 23.44 | 2.62 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 28.46 | 2.60 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 38.19 | 2.54 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 50.29 | 2.99 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 72.91 | 3.54 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 56.50 | 6.57 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 94.22 | 4.95 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 33.70 | 7.79 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 126.86 | 6.20 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 24.92 | 8.50 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 34.38 | 4.38 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 17.40 | 2.00 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | 63.28 | 3.32 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 17.40 | 2.00 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 29.38 | 4.74 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 17.40 | 2.00 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 29.38 | 4.74 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 17.40 | 2.00 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 29.38 | 4.74 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 32.08 | 2.65 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 29.38 | 4.74 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x113-romfill` | 32.51 | 2.87 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 56.11 | 8.12 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 31.57 | 2.69 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 56.11 | 8.12 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 57.97 | 5.38 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 56.18 | 8.13 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 53.36 | 7.93 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 83.46 | 14.93 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 21.20 | 8.39 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 34.16 | 14.89 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 22.64 | 2.47 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 44.79 | 2.64 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 22.64 | 2.47 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 37.42 | 8.78 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 22.64 | 2.47 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 37.42 | 8.78 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 22.64 | 2.47 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 37.42 | 8.78 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 22.64 | 2.47 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 37.42 | 8.78 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 43.49 | 3.65 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 38.32 | 8.56 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 42.93 | 3.67 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 38.32 | 8.56 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 70.03 | 7.03 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 72.02 | 15.33 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 57.11 | 9.33 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 93.11 | 24.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 18.94 | 7.63 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 35.16 | 21.31 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17.35 | 2.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 36.18 | 4.43 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17.35 | 2.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 36.18 | 4.43 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17.35 | 2.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 36.18 | 4.43 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 17.35 | 2.03 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 36.18 | 4.43 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 17.13 | 2.11 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 36.18 | 4.43 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 16.56 | 2.13 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 27.39 | 4.63 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 31.19 | 2.83 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 27.39 | 4.63 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 54.72 | 5.56 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 51.26 | 7.79 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 48.32 | 7.94 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 74.34 | 13.99 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 17.09 | 5.98 | yes | -- |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 30.15 | 13.71 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13.40 | 2.14 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 26.56 | 4.76 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13.40 | 2.14 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 26.56 | 4.76 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13.40 | 2.14 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 26.56 | 4.76 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 13.40 | 2.14 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 26.56 | 4.76 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 23.71 | 2.55 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 26.56 | 4.76 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 22.31 | 2.63 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 18.49 | 4.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 41.74 | 3.80 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 18.58 | 4.81 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 65.22 | 7.08 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 32.91 | 9.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 36.02 | 6.46 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 77.51 | 21.16 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 18.77 | 8.13 | yes | -- |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 28.81 | 17.81 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | 8.29 | 3.34 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 9.89 | 1.58 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 19.76 | 2.07 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 15.05 | 1.28 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 19.76 | 2.07 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 15.05 | 1.28 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 19.76 | 2.07 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 15.05 | 1.28 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x282` | 27.70 | 2.09 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 15.05 | 1.28 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 32.00 | 2.24 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 24.18 | 1.25 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376` | 44.59 | 2.16 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 18.97 | 1.29 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 10.98 | 3.61 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 28.71 | 1.17 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 5.32 | 3.47 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x22` | 31.32 | 1.16 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill` | 3.92 | 3.46 | yes | -- |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x22` | 16.38 | 1.08 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x64` | 9.76 | 3.44 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 10.12 | 1.82 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 10.16 | 1.80 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 5.08 | 1.26 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 10.16 | 1.80 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 5.08 | 1.26 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x287` | 12.43 | 1.83 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 5.08 | 1.26 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 15.44 | 1.86 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 15.07 | 1.24 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 22.02 | 1.71 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 14.82 | 1.25 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 27.10 | 1.52 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 18.64 | 1.22 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 31.87 | 1.46 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 24.51 | 1.22 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 17.17 | 1.37 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x31` | 25.76 | 1.22 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 5.29 | 1.30 | yes | -- |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x31` | 13.47 | 1.11 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 8.54 | 3.20 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 11.03 | 2.73 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 13.01 | 1.17 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 13.01 | 1.17 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 13.01 | 1.17 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 13.01 | 1.17 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 12.61 | 1.19 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 19.19 | 1.11 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 33.35 | 1.06 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 38.01 | 1.04 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 38.89 | 1.04 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | 9.91 | 3.50 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 13.25 | 2.94 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 1.68 | 1.34 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 13.43 | 1.11 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 13.43 | 1.11 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 13.43 | 1.11 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 13.43 | 1.11 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 10.78 | 1.14 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 16.28 | 1.05 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 16.01 | 1.03 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 16.24 | 1.03 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 16.59 | 2.65 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 22.60 | 2.73 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 16.59 | 2.65 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 22.60 | 2.73 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 16.59 | 2.65 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 22.60 | 2.73 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 16.59 | 2.65 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 22.60 | 2.73 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 16.97 | 2.67 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 10.45 | 2.93 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 16.41 | 2.65 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 10.09 | 2.86 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 30.63 | 3.58 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 10.04 | 2.85 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 41.76 | 5.54 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 15.66 | 4.00 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 36.09 | 7.41 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 26.37 | 5.76 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.01 | 7.84 | yes | -- |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 9.52 | 3.72 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 21.98 | 3.25 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 14.18 | 2.59 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 21.98 | 3.25 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 14.18 | 2.59 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 21.98 | 3.25 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 14.18 | 2.59 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 21.98 | 3.25 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 14.18 | 2.59 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 21.82 | 3.25 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill` | 6.43 | 2.68 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 21.23 | 3.21 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 6.20 | 2.61 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 38.38 | 4.59 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 10.65 | 3.68 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 48.92 | 6.81 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 12.79 | 4.25 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 38.56 | 8.15 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 16.40 | 5.04 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.45 | 8.05 | yes | -- |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 5.54 | 2.55 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | 7.70 | 3.01 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 10.00 | 2.10 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 19.55 | 1.22 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 19.55 | 1.22 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 19.55 | 1.22 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 19.55 | 1.22 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 19.55 | 1.22 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 17.68 | 1.26 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 29.53 | 1.17 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | 34.42 | 1.17 | yes | -- |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x49` | 35.32 | 1.16 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | 8.77 | 3.29 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 10.84 | 3.31 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 6.46 | 1.23 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 6.46 | 1.23 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 6.46 | 1.23 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 6.46 | 1.23 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 10.20 | 1.20 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 17.80 | 1.20 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 25.32 | 1.22 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 27.64 | 1.23 | yes | -- |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x68` | 28.02 | 1.23 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x333` | 7.36 | 2.66 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 13.00 | 3.77 | NO | the KV store has no room for it |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 16.91 | 1.12 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 16.91 | 1.12 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 16.91 | 1.12 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 16.91 | 1.12 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 16.91 | 1.12 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 16.62 | 1.13 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 36.54 | 1.06 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 41.13 | 1.05 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 42.87 | 1.04 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | 7.05 | 3.40 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 9.02 | 2.74 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 1.49 | 1.30 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 1.68 | 1.50 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 16.23 | 1.08 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 16.23 | 1.08 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 16.23 | 1.08 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 16.23 | 1.08 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 15.76 | 1.06 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 17.29 | 1.03 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 17.80 | 1.03 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 15.71 | 2.62 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 21.11 | 3.34 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 15.71 | 2.62 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 21.11 | 3.34 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 15.71 | 2.62 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 21.11 | 3.34 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 15.71 | 2.62 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 21.11 | 3.34 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 16.63 | 2.49 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 21.11 | 3.34 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 30.21 | 3.13 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 19.23 | 3.35 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 28.64 | 3.55 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 18.91 | 3.31 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 67.81 | 6.26 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 27.33 | 4.72 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 28.80 | 5.93 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 41.61 | 6.60 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 17.85 | 7.52 | yes | -- |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 46.71 | 2.68 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 20.42 | 3.10 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 9.87 | 3.29 | NO | the KV store has no room for it |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 20.42 | 3.10 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 17.21 | 2.92 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 20.42 | 3.10 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 17.21 | 2.92 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 20.42 | 3.10 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 17.21 | 2.92 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 21.23 | 2.88 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 17.21 | 2.92 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 38.30 | 3.86 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 31.76 | 2.76 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 36.40 | 4.38 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 18.89 | 4.19 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 75.55 | 7.53 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 59.75 | 3.97 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 30.07 | 7.57 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 73.24 | 4.58 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 34.61 | 8.14 | yes | -- |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 19.86 | 2.07 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 29.53 | 3.54 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 14.78 | 2.16 | NO | the KV store has no room for it |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 29.85 | 3.09 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 3.14 | 1.96 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 29.85 | 3.09 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 3.14 | 1.96 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 29.85 | 3.09 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 3.14 | 1.96 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 29.85 | 3.09 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 3.14 | 1.96 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 29.85 | 3.09 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 3.14 | 1.96 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 55.70 | 2.90 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 3.14 | 1.96 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 46.78 | 4.59 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 4.29 | 2.43 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 36.29 | 5.93 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 6.15 | 3.05 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 13.12 | 5.62 | yes | -- |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 51.45 | 2.13 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 14.76 | 2.48 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 13.35 | 4.92 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 14.76 | 2.48 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 13.35 | 4.92 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 14.76 | 2.48 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 13.35 | 4.92 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 14.76 | 2.48 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 13.35 | 4.92 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 15.28 | 2.46 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 13.35 | 4.92 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 14.99 | 2.47 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 13.03 | 4.82 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 14.99 | 2.47 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 13.03 | 4.82 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 51.39 | 6.08 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 24.71 | 8.46 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 31.19 | 8.30 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 40.47 | 17.42 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 15.15 | 8.69 | yes | -- |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 21.18 | 19.25 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 14.70 | 2.39 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 25.39 | 8.57 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 14.70 | 2.39 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 25.39 | 8.57 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 14.70 | 2.39 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 25.39 | 8.57 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 14.70 | 2.39 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 25.39 | 8.57 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 15.22 | 2.38 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 25.39 | 8.57 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 14.93 | 2.39 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 25.39 | 8.57 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 14.93 | 2.39 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 25.39 | 8.57 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 53.12 | 5.99 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 25.42 | 8.58 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 32.82 | 8.33 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 43.75 | 18.60 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 15.77 | 8.75 | yes | -- |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 22.55 | 20.43 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 46.02 | 3.71 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 16.39 | 3.57 | NO | the KV store has no room for it |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 46.02 | 3.71 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 16.72 | 3.87 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 46.02 | 3.71 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 16.72 | 3.87 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 46.02 | 3.71 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 16.72 | 3.87 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 46.02 | 3.71 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 16.72 | 3.87 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 46.02 | 3.71 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 16.72 | 3.87 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 46.02 | 3.71 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 16.72 | 3.87 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 73.87 | 6.31 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 28.19 | 7.59 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 62.11 | 8.79 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 56.14 | 14.32 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 23.30 | 8.92 | yes | -- |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 44.66 | 10.65 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 41.70 | 3.60 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 35.45 | 6.85 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 41.70 | 3.60 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 35.45 | 6.85 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 41.70 | 3.60 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 35.45 | 6.85 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 41.70 | 3.60 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 35.45 | 6.85 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 41.70 | 3.60 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 35.45 | 6.85 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 41.70 | 3.60 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 35.45 | 6.85 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 41.70 | 3.60 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 35.45 | 6.85 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 77.61 | 5.64 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 65.26 | 11.91 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 75.66 | 8.99 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 83.09 | 19.93 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 27.81 | 9.19 | yes | -- |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 25.49 | 11.44 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 22.10 | 2.60 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 37.01 | 7.05 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 22.10 | 2.60 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 37.01 | 7.05 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 22.10 | 2.60 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 37.01 | 7.05 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 22.10 | 2.60 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 37.01 | 7.05 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 22.10 | 2.60 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 37.01 | 7.05 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 22.10 | 2.60 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 37.01 | 7.05 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x308-romfill` | 42.73 | 3.62 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 37.01 | 7.05 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 42.82 | 5.84 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 35.47 | 8.85 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 78.26 | 9.03 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 85.64 | 20.33 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 28.71 | 9.25 | yes | -- |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 16.63 | 9.46 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x152` | 35.76 | 4.08 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 20.33 | 2.52 | NO | the KV store has no room for it |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 21.34 | 3.37 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 37.47 | 1.60 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 21.34 | 3.37 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 37.47 | 1.60 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 21.34 | 3.37 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 37.47 | 1.60 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 21.34 | 3.37 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 37.47 | 1.60 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 37.77 | 3.40 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 37.47 | 1.60 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 66.85 | 3.49 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 37.47 | 1.60 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 75.02 | 4.51 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 54.32 | 2.01 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 46.94 | 4.72 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 77.98 | 2.34 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 15.07 | 4.36 | yes | -- |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 83.64 | 2.43 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 22.17 | 3.46 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 27.52 | 8.66 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 22.17 | 3.46 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 27.52 | 8.66 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 22.17 | 3.46 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 27.52 | 8.66 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 22.17 | 3.46 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 27.52 | 8.66 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 22.17 | 3.46 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 27.52 | 8.66 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 20.18 | 3.49 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 16.28 | 8.80 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 20.12 | 3.49 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 16.28 | 8.80 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 34.14 | 6.91 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 29.12 | 15.31 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 33.93 | 10.59 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 38.59 | 26.04 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 15.60 | 9.85 | yes | -- |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 16.40 | 22.36 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 20.08 | 3.39 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 17.79 | 9.53 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 20.08 | 3.39 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 17.79 | 9.53 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 20.08 | 3.39 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 17.79 | 9.53 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 20.08 | 3.39 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 17.79 | 9.53 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 20.08 | 3.39 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 17.79 | 9.53 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 20.13 | 3.38 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 17.35 | 9.31 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 20.07 | 3.39 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 17.35 | 9.31 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 35.49 | 6.94 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 33.10 | 17.29 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 35.84 | 10.78 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 51.22 | 34.41 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 16.27 | 10.02 | yes | -- |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 23.70 | 32.57 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 15.72 | 2.86 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 22.81 | 4.42 | NO | the KV store has no room for it |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 15.72 | 2.86 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 22.05 | 3.52 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 15.72 | 2.86 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 22.05 | 3.52 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 15.72 | 2.86 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 22.05 | 3.52 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 15.72 | 2.86 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 22.05 | 3.52 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 29.33 | 3.64 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 22.05 | 3.52 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 54.17 | 5.22 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 41.68 | 5.63 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 73.29 | 7.99 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 60.32 | 9.03 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 56.22 | 10.31 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 90.68 | 13.07 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 21.21 | 9.86 | yes | -- |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 26.18 | 10.33 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 15.83 | 2.60 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 23.51 | 7.23 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 15.83 | 2.60 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 23.51 | 7.23 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 15.83 | 2.60 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 23.51 | 7.23 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 15.83 | 2.60 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 23.51 | 7.23 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 15.83 | 2.60 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 23.51 | 7.23 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | 29.12 | 3.38 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 23.51 | 7.23 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 57.69 | 4.94 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 45.94 | 13.11 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 83.95 | 8.01 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 42.44 | 15.98 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 68.36 | 10.89 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 49.00 | 24.13 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 24.97 | 10.38 | yes | -- |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | 32,768 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 41.18 | 28.50 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 29.82 | 3.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 24.59 | 7.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 29.82 | 3.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 24.59 | 7.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 29.82 | 3.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 24.59 | 7.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 29.82 | 3.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 24.59 | 7.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 29.82 | 3.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 24.59 | 7.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | 29.82 | 3.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 24.59 | 7.46 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 56.22 | 5.18 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 48.39 | 13.71 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 85.86 | 8.02 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 44.37 | 16.57 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 70.70 | 11.00 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 50.20 | 24.58 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 25.72 | 10.49 | yes | -- |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | 8,192 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 25.79 | 21.39 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 16.65 | 3.02 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 27.39 | 3.11 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 17.73 | 2.72 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 6.22 | 2.90 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 17.73 | 2.72 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 6.22 | 2.90 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 17.73 | 2.72 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 6.22 | 2.90 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x70` | 20.66 | 2.63 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 6.22 | 2.90 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 14.84 | 2.92 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 6.22 | 2.90 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 14.83 | 2.93 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 6.25 | 2.91 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 23.65 | 5.32 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 9.61 | 4.84 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 24.05 | 8.19 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 17.38 | 8.07 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 14.53 | 5.78 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 7.41 | 6.85 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 49.62 | 4.53 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 22.63 | 2.79 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 49.62 | 4.53 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 7.19 | 2.41 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 49.62 | 4.53 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 7.19 | 2.41 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 49.62 | 4.53 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 7.19 | 2.41 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 49.62 | 4.53 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 7.19 | 2.41 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 49.62 | 4.53 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 7.19 | 2.41 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 49.62 | 4.53 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 7.19 | 2.41 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `array` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 64.56 | 6.65 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 54.49 | 2.26 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 48.86 | 8.39 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 114.05 | 3.26 | yes | -- |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `array` | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 19.08 | 8.52 | NO | the KV store has no room for it |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 139.01 | 3.71 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x79` | 12.29 | 2.87 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 27.74 | 3.46 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 13.20 | 2.90 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 24.90 | 2.57 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 13.20 | 2.90 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 24.90 | 2.57 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 13.20 | 2.90 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 24.90 | 2.57 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 24.23 | 3.76 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 24.90 | 2.57 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 10.80 | 3.01 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 24.90 | 2.57 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 19.10 | 3.93 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 46.47 | 3.67 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 28.07 | 6.94 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 72.40 | 5.42 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `array` | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 25.72 | 9.75 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 11.24 | 7.79 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `array` | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 14.81 | 7.15 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | 200,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 27.83 | 4.97 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `array` | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 14.31 | 3.84 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | `wafer` | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 31.07 | 3.23 | NO | the KV store has no room for it |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 2 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 35.25 | 1.93 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 35.25 | 1.93 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 35.25 | 1.93 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 16 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 35.25 | 1.93 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 35.25 | 1.93 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 35.25 | 1.93 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 256 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 60.80 | 2.54 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 1024 | `wafer` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 102.69 | 3.48 | yes | -- |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | 1,000,000 | 4096 | `wafer` | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 116.12 | 3.80 | yes | -- |

## The capacity requirement, stated as a requirement

Every evaluated ROM design carries `weight_capacity_bytes == stored_weight_bytes` (the `romfill` variants reach 1.0039x), so no evaluated design has spare array for a drafter it does not already store. Re-solving the area split is `balanced_area_split`'s job and that file is not touched here, so what follows is a requirement -- this much extra array, or this much extra sweep on every pass -- and not a new design. **The speculative-optimal ROM design has not been computed, only bounded by the rungs that already exist.**

| study | model | design | drafter already in the checkpoint | extra stored bytes | extra array mm2 | as a fraction of the design | sweep inflation if area is held fixed |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x220` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-SRAMKV-wafer-hybrid-x10-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-SRAMKV-array-hw-hybrid-x192` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-SRAMKV-array-hw-hybrid-x250` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-SRAMKV-wafer-hybrid-x12-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x64` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x141` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
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
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
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
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x373` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-array-hw-hybrid-x366` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x79` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | YES -- it costs nothing extra to store | 0 | 0.0 | 0.0% | 1.0000x |

## Which design the published rule chooses once a block is verified

A re-ranking of designs the study already evaluated, under the study's own selection rule (non-dominated on per-user tokens/s and tokens/s per 1,000 mm2, then a marginal-return walk from the smallest feasible machine). `tau` is a common factor on both axes, so the choice is independent of the acceptance rate. The rule's reproduction of the published autoregressive recommendation is reported first, because a re-ranking whose baseline does not reproduce is not evidence of anything.

| study | model | published recommendation | rule reproduces it | under speculation, draft in ROM | draft in KV store | moves |
| --- | --- | --- | --- | --- | --- | --- |
| `n5_vs_b200-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x98` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x98` | `ROM-N5-native-HBMKV-array-hw-hybrid-x110` | yes |
| `n6_vs_a100-deepseek-v41-flash` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x126` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x115` | `ROM-N6-native-HBMKV-array-hw-tensor-x143` | yes |
| `n5_vs_b200-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x98` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x98` | `ROM-N5-native-HBMKV-array-hw-tensor-x97` | yes |
| `n6_vs_a100-deepseek-v41-flash-1m` | DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x115` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x115` | `ROM-N6-native-HBMKV-array-hw-tensor-x143` | yes |
| `n5_vs_b200-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x97` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x89` | `ROM-N5-native-HBMKV-array-hw-hybrid-x112` | yes |
| `n6_vs_a100-deepseek-v41-flash-8k` | DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-array-hw-hybrid-x141` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x114` | `ROM-N6-native-HBMKV-array-hw-tensor-x141` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | yes | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | `ROM-N5-native-HBMKV-array-hw-hybrid-x70` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x75` | yes | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | yes | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-1m` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x75` | yes | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | `ROM-N6-native-HBMKV-array-hw-tensor-x87` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-array-hw-tensor-x59` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-hbm-8k` | DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x75` | yes | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | yes |
| `n5_vs_b200-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x59` | `ROM-N5-native-HBMKV-array-hw-hybrid-x70` | yes |
| `n6_vs_a100-deepseek-v41-flash-engram-host` | DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-SRAMKV-array-hw-hybrid-x76` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x76` | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | yes |
| `n5_vs_b200-kimi-k3` | Kimi-K3 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x313` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-kimi-k3` | Kimi-K3 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x398` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200-kimi-k3-1m` | Kimi-K3 | `ROM-N5-native-SRAMKV-array-hw-tensor-x312` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-kimi-k3-1m` | Kimi-K3 | `ROM-N6-native-SRAMKV-array-hw-tensor-x391` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200-kimi-k3-8k` | Kimi-K3 | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-kimi-k3-8k` | Kimi-K3 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x357` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-tensor-x36` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x36` | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | no |
| `n6_vs_a100-mimo-v26-flash` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-tensor-x46` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x46` | `ROM-N6-native-HBMKV-array-hw-hybrid-x264` | no |
| `n5_vs_b200-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x55-romfill` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | yes |
| `n6_vs_a100-mimo-v26-flash-1m` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-tensor-x64-romfill` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | yes |
| `n5_vs_b200-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x32` | `ROM-N5-native-HBMKV-array-hw-tensor-x34` | yes |
| `n6_vs_a100-mimo-v26-flash-8k` | MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x43` | `ROM-N6-native-HBMKV-array-hw-tensor-x47` | yes |
| `n5_vs_b200-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x113` | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | yes |
| `n6_vs_a100-mimo-v26-pro` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-hybrid-x153` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x153` | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | yes |
| `n5_vs_b200-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-array-hw-tensor-x132` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x164` | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | yes |
| `n6_vs_a100-mimo-v26-pro-1m` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-tensor-x170` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | `ROM-N6-native-HBMKV-wafer-tensor-x339` | yes |
| `n5_vs_b200-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x99` | `ROM-N5-native-HBMKV-array-hw-tensor-x112` | yes |
| `n6_vs_a100-mimo-v26-pro-8k` | MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-hybrid-x139` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x139` | `ROM-N6-native-HBMKV-array-hw-tensor-x138` | yes |
| `n5_vs_b200-qwen3-8b-1m` | Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-qwen3-8b-1m` | Qwen3-8B | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200-qwen3-8b-200k` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x21` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-qwen3-8b-200k` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x27` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | yes |
| `n5_vs_b200-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x32` | `ROM-N5-native-HBMKV-array-hw-tensor-x32` | yes |
| `n5_vs_b200-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x32` | `ROM-N5-native-HBMKV-array-hw-tensor-x32` | yes |
| `n5_vs_b200-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x156` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-array-hw-hybrid-x208` | yes |
| `n5_vs_b200-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x156` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-array-hw-hybrid-x198` | yes |
| `n5_vs_b200-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x171` | yes | `ROM-N5-native-HBMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-array-hw-hybrid-x193` | yes |
| `n6_vs_a100-flash-1m` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x46` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | yes |
| `n6_vs_a100-flash-32k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x40` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x40` | `ROM-N6-native-HBMKV-array-hw-tensor-x45` | yes |
| `n6_vs_a100-flash-8k` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x41` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x41` | `ROM-N6-native-HBMKV-array-hw-tensor-x45` | yes |
| `n6_vs_a100-pro-200k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x227` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-array-hw-tensor-x217` | yes |
| `n6_vs_a100-pro-32k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x227` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-tensor-x4` | yes |
| `n6_vs_a100-pro-8k` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x219` | yes | `ROM-N6-native-HBMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-tensor-x4` | yes |
| `n5_vs_b200` | Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | yes | `--` | `--` | the drafter does not apply to this model |
| `n5_vs_b200` | DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x30` | yes | `ROM-N5-native-SRAMKV-array-hw-tensor-x30` | `ROM-N5-native-HBMKV-array-hw-hybrid-x56` | yes |
| `n5_vs_b200` | DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | yes | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | `ROM-N5-native-HBMKV-array-hw-hybrid-x399-romfill` | yes |
| `n6_vs_a100` | Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100` | DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x41` | yes | `ROM-N6-native-SRAMKV-array-hw-tensor-x41` | `ROM-N6-native-HBMKV-array-hw-hybrid-x79` | yes |
| `n6_vs_a100` | DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x227` | yes | `ROM-N6-native-SRAMKV-wafer-tensor-x4` | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | yes |
| `n5_vs_b200-quantised_variant` | Qwen3-8B | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | yes | `--` | `--` | the drafter does not apply to this model |
| `n6_vs_a100-quantised_variant` | Qwen3-8B | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | yes | `--` | `--` | the drafter does not apply to this model |

**The rule reproduces the published autoregressive recommendation on 56 of 56 model-and-study rows.** Of the 42 rows where it reproduces and the drafter applies, verifying a block moves the chosen rung on 40. Where it moves, it moves toward machines with compute headroom for a block, which is exactly what the arithmetic predicts: a verification pass raises arithmetic intensity by the block size, and a machine sized with just enough compute for one token per sweep has no room for it. **This is a re-ranking of rungs that already exist. The speculative-optimal design has not been computed: that would need the area split re-solved, which is `balanced_area_split`'s job and not this layer's.**

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

