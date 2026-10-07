# Architecture Atlas feasibility review

Date: 2026-09-27  
Reviewed checkout: `1a5a66d1`  
Primary document: [ARCHITECTURE_ATLAS.html](ARCHITECTURE_ATLAS.html)

## Assessment

**The single-user speeds are physically plausible, but the project has not yet demonstrated that its proposed machines can achieve them.** Several assumptions in the atlas are reasonable engineering targets; others are presented with stronger evidence labels than their sources support.

Treat **8,910 tok/s for Qwen as an optimistic, reproducible compute-model projection**, and **8,622 tok/s for DeepSeek as a conditional system-design projection**. The exact rates, speculative gains, and energy ratios are not yet sufficiently established for a hardware commitment.

High decode speed means high tokens/s and **low time per output token (TPOT)**.

| Atlas headline | Implied TPOT | Assessment |
|---|---:|---|
| Qwen3-8B, 8K: 8,910 tok/s | 112.2 µs | Plausible target; integrated memory/compute timing unproven |
| V4.1-Flash, 1M: 8,622 tok/s | 116.0 µs | Conceivable on the proposed rack; substantially more conditional |
| V4.1 with MTP: 23,578 tok/s | 42.4 µs per emitted token, averaged | Speculative projection with additional acceptance and verification assumptions |

## Review scope and verification

The review covered the atlas, supporting models and physical-methodology documents, selected cited commits, and relevant primary external sources. Qwen's 123,301-cycle result was reproduced from commit `74359092` using its Python timing model in a temporary directory.

Place-and-route and RTL campaigns were **not** rerun. This is an architectural and evidence review, not a physical sign-off or an exhaustive RTL correctness audit. No implementation files were changed during the review.

Selected historical artifacts inspected:

| Commit | Artifact or source | Purpose |
|---|---|---|
| `74359092` | `tools/arch_budget_qwen3.py`, `tools/hdc_timing.py`, `results/arch/qwen3_budget.json` | Reproduce and inspect Qwen headline timing |
| `b07a5745` | `tools/arch_lanes_v41.py`, `tools/arch_budget_v41.py`, `tools/arch_utilization_v41.py`, `results/arch/v41_lanes.json`, `results/arch/v41_hbm_switched.json` | Inspect DeepSeek system assumptions and projected rates |
| `0facdc17` | `results/arch/v41_rack.json` | Inspect rack and physical-link assumptions |
| `872da542` | `configs/hardware/technology.json`, `results/arch/power_assumptions.json` | Trace energy constants and their evidence boundaries |
| `f04f3c17` | `tools/arch_budget_qwen3.py` | Inspect production power accounting |

Historical paths above refer to the named commits; some are absent or different in the reviewed checkout. They can be inspected with `git show <commit>:<path>`.

## Why the basic idea is credible

There is no fundamental sequential-generation limit that forces an 8B model to run at only hundreds of tokens/s. Autoregression serializes successive tokens, but the arithmetic within a token can be massively parallel. Local weights, short synchronization paths, and dedicated operators can make a large difference.

There is also a relevant external precedent: Taalas reports approximately **17,000 tokens/s per user** for Llama-3.1-8B on HC1. Its published benchmark uses a much shorter sequence setting, so it supports the general speed scale rather than validating OpenTallas's 8K or 1M claims. This remains a vendor-reported result. [Taalas product page](https://taalas.com/products/)

The Qwen bandwidth calculation checks out. Using the official dimensions—36 layers, eight KV heads, head dimension 128—the FP8 KV payload at 8,192 tokens is:

```text
2 × 36 × 8 × 128 × 8,192 × 1 byte = 603,979,776 bytes

603,979,776 / 5.4 TB/s = 111.85 µs
Bandwidth-only ceiling = 8,940.7 tokens/s
```

Those dimensions match the [official Qwen configuration](https://huggingface.co/Qwen/Qwen3-8B/raw/main/config.json). A 1 TB/s raw bandwidth assumption per HBM3E stack is also credible; Micron advertises more than 1.2 TB/s per placement. Sustaining the assumed 90% on this controller and access pattern remains an implementation question. [Micron HBM3E specifications](https://www.micron.com/products/memory/hbm/hbm3e)

The project's approximately 10 billion MACs per Qwen token would require about 89 TMAC/s at the headline rate, against approximately 144 TMAC/s provisioned by 131,072 lanes at 1.0986 GHz. **The arithmetic capacity does not rule the target out.**

## Findings

### 1. Qwen's headline does not include a demonstrated HBM-fed execution schedule

This is the most important performance qualification.

In the cited version of `tools/arch_budget_qwen3.py`, `as_built()` explicitly models **“KV on core (the KV stream is priced separately)”**. Its call to `T.simulate()` supplies no KV streaming configuration. The reproduced results were:

```text
8K context: 123,301 cycles → 8,910.23 tokens/s
2K context: 108,393 cycles → 10,135.71 tokens/s
```

The separate analytical model combines compute and KV time using `max(compute, kv)`. That is an optimistic overlap model. It does not establish that every attention operand arrives before consumption, with bounded buffers, bank conflicts, refresh, writeback, and the actual K-split read order.

Prefetching is legitimate: old KV addresses do not depend on the current token, so next-layer reads can overlap current-layer computation. **The problem is the missing integrated schedule, not the prefetch concept.**

Also, 123,301 compute cycles are slightly **greater** than the 122,881-cycle KV floor. Those numbers establish that compute and bandwidth are closely balanced; they do not establish the atlas's repeated statement that KV alone now limits the machine.

References: atlas §6.3, around line 578, and §8.5, around line 1235; `74359092:tools/arch_budget_qwen3.py`, functions `as_built()` and `rom_token()`.

**Required evidence:** a coupled memory/compute schedule, followed by an integrated token campaign, that enforces finite buffer capacity, real read ordering, refresh, writeback, and consecutive-token behavior.

### 2. Block timing and estimated memory macros do not establish a routable, manufacturable full die

The headline Qwen configuration extrapolates to 8,192 lane groups and a 1,024-wide vector unit. Its specified weight path must deliver about **63 TB/s of aggregate local ROM bandwidth**. That is possible in principle through many distributed banks, but capacity, read bandwidth, wire delivery, and clock frequency must all close together.

The atlas explicitly describes the ROM/SRAM views as analytical models calibrated to a published SRAM macro, rather than qualified silicon macros. It also states that the whole-core route is pending.

The slowest isolated block's typical-corner Fmax is a useful target, but it is not a system clock guarantee. Clock distribution, fanout, memory ports, routing congestion, power delivery, and operating corners remain material risks. Applying ASAP7 areas unscaled to an N6/N5 design does not, by itself, prove that the estimate is conservative.

References: atlas §6.7, around line 704; §7.4, around line 1001; [ROM physical methodology](ROM_PHYSICAL_METHODOLOGY.md); [ROM density node transfer](ROM_DENSITY_NODE_TRANSFER.md).

**Required evidence:** a representative routed compute-and-memory tile with the intended banking, operand distribution, and clocking, followed by hierarchical full-core closure using qualified target-process collateral.

### 3. Power claims combine different arithmetic implementations and contain a problematic memory-power allocation

The implemented BF16 lane's reported energy is **3.97 pJ/MAC**. The atlas's own cross-check says that this would cap Qwen at approximately **7,720 tok/s**, and its speculative configuration at approximately **4,909 tok/s** under its cooling assumptions.

The more favorable production model instead assumes **0.09 pJ per W4A8 MAC** for a future specialized lane. A lower-energy lane is a reasonable development objective, but this is not measured evidence for the existing implementation.

Two source problems matter:

- The atlas table labels Keller's result as a measured **FP4 MAC** result. The referenced accelerator uses per-vector scaled **integer** arithmetic; its published datapath includes 24-bit partial sums. That does not directly establish the energy of OpenTallas's floating-point formats and accumulation contract. [NVIDIA conference paper](https://d1qx31qr3h6wln.cloudfront.net/publications/C02-1.PDF), [journal publication page](https://research.nvidia.com/publication/2023-01_956-topsw-deep-learning-inference-accelerator-vector-scaled-4-bit-quantization)
- The **13.11 pJ/bit** memory number does have an underlying source, but it is an **A100 HBM-path measurement including controller energy**. The atlas cites the older O'Connor paper in its table, which instead discusses roughly 3.97 pJ/bit for HBM2. More importantly, the Qwen production model subtracts 0.8 pJ/bit for the die interface and assigns the remainder to the stacks. The A100 source does not justify that physical allocation: its HBM category explicitly includes memory-controller energy. This weakens the claimed split between die cooling and stack power. [Underlying SC'25 study, Figure 1 and Table 3](https://escholarship.org/content/qt6189368s/qt6189368s.pdf), [O'Connor et al., MICRO 2017](https://d1qx31qr3h6wln.cloudfront.net/publications/MICRO_2017_Fine_Grained_DRAM.pdf)

The inspected Qwen code does subtract the interface portion before charging the remainder to the stacks; the finding is **unsupported physical allocation and cross-architecture extrapolation**, not a claim that this code simply adds the interface twice.

“Conservative production values” is too strong as a blanket description. These are cross-architecture estimates with different measurement boundaries.

References: atlas §6.8, around line 745, and Table 8-21, around line 1373; `f04f3c17:tools/arch_budget_qwen3.py`, functions `_prod_inputs()` and `_rom_step()`.

**Required evidence:** characterize the actual arithmetic lane and memory subsystem, preserve consistent measurement boundaries, and allocate power to the physical components that must dissipate it. Keep the measured implementation and proposed production implementation as distinct scenarios.

### 4. “Bit-exact” verifies the chosen arithmetic contract, not unchanged model quality

Changing sequential sums into trees is a sensible hardware optimization. However, agreement between RTL and a golden model that was changed alongside it establishes implementation correctness against that specification.

The atlas itself reports that changed summation order can flip expert selection in the reduced model. Qwen's 3.5-bit weights, FP8 KV, and the proposed energy-efficient arithmetic add further quality questions.

This does not make the design invalid. It means the claim needs two separate demonstrations: hardware correctness against the adopted arithmetic, and acceptable quality on the full quantized model. Reduced-model token matches cannot establish the latter.

Reference: atlas §6.5, around line 660.

**Required evidence:** full-model quality evaluations with the exact weight quantization, KV formats, accumulation order, normalization, and attention arithmetic intended for deployment.

### 5. DeepSeek's rate depends particularly on collective overlap and complete system timing

The design distributes a token across 28 layer stages, with a four-die tensor group per stage. Pipeline stages help aggregate throughput, but a single user's next token still waits for the whole dependency chain and feedback path.

The cited model marks collective nodes as streaming behind their producers, then prices link serialization and latency. That is a reasonable hypothesis, but it needs evidence that outputs emerge in the required order and that reduction, buffering, link contention, and consumer dependencies permit the assumed overlap.

The sensitivity is meaningful: starting from 116 µs/token, an additional **100 ns exposed on each of 209 serial critical-path collectives** would add 20.9 µs and reduce the rate to about **7,306 tok/s**. This is an illustrative sensitivity, not a prediction that all 209 incur that penalty.

Sparse/compressed attention makes the 1M-context target much more plausible than dense attention at 1M. The official model supports cross-layer KV reuse and bounded deeper indexing. Those architectural properties do not validate this rack's timing. [Official DeepSeek model description](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash)

References: atlas §8.9, around line 1393; `b07a5745:tools/arch_budget_v41.py`, `price()`; `b07a5745:tools/arch_lanes_v41.py`.

**Required evidence:** a representative producer–collective–consumer stage with bounded queues, actual output ordering, backpressure, and modeled physical link delays, followed by a full-token system schedule and whole-core clock closure.

### 6. Speculative gains and evidence packaging need further qualification

Qwen's block-three acceptance is derived by truncating a measured block-16 acceptance histogram. The code correctly notes that this is approximate because DFlash drafts jointly. It also prices drafter MACs while assuming their additional latency is overlapped. DeepSeek's headline acceptance of five comes from a different model/workload setting.

These are useful sensitivity studies, but neither establishes the quoted speculative rate on the final hardware arithmetic. The 42.4 µs MTP figure is also an average per emitted token; tokens arrive in verification bursts.

Separately, the reviewed checkout's `results/arch/qwen3_budget.json` is an older result, while `results/arch/v41_lanes.json` and `results/arch/v41_hbm_switched.json` are absent. Their cited commits exist locally and were inspected, so this is a reproducibility/integration defect rather than evidence that the figures were invented.

References: atlas §8.6; `74359092:tools/arch_budget_qwen3.py`, `tokens_per_step()` and `rom_block_sweep()`.

**Required evidence:** acceptance measurements at the selected block sizes and final arithmetic, complete draft/verify/commit timing, and a single pinned source/configuration/result bundle for every headline comparison.

## Sensitivity of the Qwen bandwidth ceiling

Even the bandwidth-only ceiling moves appreciably with modest assumption changes:

| Qwen KV scenario | Bandwidth-only ceiling |
|---|---:|
| 8K FP8, 90% of 6 TB/s | 8,941 tok/s |
| 8K FP8, 80% | 7,947 tok/s |
| 8K FP8, 70% | 6,954 tok/s |
| 8K BF16, 90% | 4,470 tok/s |
| 32K FP8, 90% | 2,235 tok/s |

These calculations use the atlas's full-cache streaming assumption. Actual rates must also satisfy compute, dependency, and power limits. Being within 0.3% of a calculated ceiling leaves almost no room for unmodeled overhead.

## Recommended next milestones

Continue the project, with the next milestone focused on evidence rather than higher analytical rates:

1. Freeze the full-model arithmetic and quality target.
2. Run a bounded-buffer, HBM-backed Qwen token schedule across consecutive tokens.
3. Close a representative physical tile including its real memory and operand delivery.
4. Demonstrate DeepSeek's producer–collective–consumer overlap on a representative stage.
5. Reconcile power measurement boundaries and characterize the intended arithmetic lane.
6. Publish one reproducible source/configuration/result bundle, with explicit evidence classes and sensitivity ranges.

The architectural direction is credible. The atlas should currently say **“targets approximately 9,000 tokens/s under these assumptions”**, while reserving “achieves” and “validated” for the integrated evidence that remains to be produced.
