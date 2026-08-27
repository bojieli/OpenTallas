# ROM Inference Silicon — Brief

Companion to the full program plan. All figures are outputs of `infersim.py` with **estimated** inputs, not measurements. Treat as provisional.

---

## 1. Models evaluated

| Model | Total / active | Attention | Weights @MXFP4 | Wafers |
|---|---|---|---|---|
| Llama-3.1-8B | 8B / 7.5B dense | GQA, dense | small | 1 |
| DeepSeek-V4-Flash | 284B / 13B | CSA + HCA sparse | ~142 GB | 1 |
| **DeepSeek-V4-Pro** | **1.6T / 49B** | **CSA + HCA sparse** | **~800 GB** | **6** |
| Kimi-K3 | 2.8T / 104B | KDA 3:1 + dense Gated MLA | ~1.4 TB | 9 |
| Qwen3.5-397B-A17B | 397B / 17B | Gated DeltaNet 3:1 + GQA | ~200 GB | 2 |

**ρ₁ = active weight bytes ÷ KV read per token** — the screening metric, a pure model property with no hardware in it:

| Model | 8K | 32K | 200K | 1M |
|---|---|---|---|---|
| Llama-3.1-8B | 7.2 | 1.8 | 0.3 | 0.1 |
| V4-Flash | 75 | 49 | 14 | 3.3 |
| **V4-Pro** | — | **137** | **40** | **9.2** |
| Kimi-K3 | 209 | 91 | 19 | 3.9 |
| Qwen3.5-397B | 24 | 7.3 | 1.3 | 0.3 |

Note K3's ρ₁ leads at short context but collapses fastest, because its Gated-MLA layers read the full cache. V4-Pro is the flattest across context.

---

## 2. Recommended operating points

**Primary target — DeepSeek-V4-Pro @ 200K, 6 wafers.** Remarkably flat from 8K to 200K (~74× advantage at both), which no other candidate achieves.

| Tier | Batch/stage | Per-user tok/s | ROM $/M tok | vs GPU |
|---|---|---|---|---|
| Ultra | 1–4 | ~7,000–9,200 | high | GPU cannot reach at any batch |
| **Interactive** | **8** | **~5,500** | low | ~6× faster, ~130× cheaper |
| **Balanced (recommended)** | **32** | **~2,250** | lowest useful | ~3–4× faster, ~46–68× cheaper |
| Throughput | 128+ | <700 | floor | GPU wins per-user speed |

**Secondary — V4-Flash @ 32K–200K, 1 wafer.** Cheapest entry, highest absolute speed (~11,200 tok/s at 32K, B=8), simplest build. Best vehicle for proving the fabric. Weak business case alone: the model's list price is low, so revenue per box is roughly 25× below V4-Pro's.

**Not recommended:**
- **Kimi-K3** — 9 wafers, and compute-bound at every batch ≥4 (208 GFLOP/token). Compute is where GPUs are strong, and speculative decoding rescues them there but barely helps a compute-bound ROM machine.
- **Qwen3.5-397B @ 200K** — the only configuration where ROM is *slower* than the GPU. Cause is GQA rather than latent compression, plus no top-k selection. Passes at 32K; the model isn't the problem, long context is. Their next generation adds sparse indexing and would likely pass.
- **Any dense model** — ρ₁ falls below 2 by 32K.
- **1M as the primary operating point for anything.** Advantage drops 2.5–3.3× across all candidates. Support it as a degraded mode.

---

## 3. Major conclusions

**Structural (properties of the equations, reliable):**

1. **Advantage = 1 + ρ(B), where ρ(B) = W(B)/(B·K).** Monotonically decreasing in batch. The product is low-to-moderate batch; at throughput-optimized batch the advantage shrinks toward noise.

2. **Attention mechanism dominates model size.** Counterfactuals swapping attention at fixed size move ρ₁ by ~4.4× in both directions. Swapping size at fixed attention moves it less.

3. **Larger models are better targets, holding attention constant.** Active weight bytes grow with size; compressed KV read barely does. The optimum trades this against capital and compute — V4-Pro sits there, K3 overshoots.

4. **Speed superiority, not cost, is the defensible claim.** If ROM is only cheaper, a GPU price cut erases it. The product is the batch range where ROM exceeds the best per-user speed *any* GPU configuration can reach.

5. **Interleaved weight placement beats layer-local by roughly 15×**, converting the central problem from bandwidth into collective latency. This is the architectural pivot.

6. **Multi-wafer pipelining is nearly free in communication** (one hop per stage boundary, small payload) but forfeits compute pooling. Concurrency multiplies by stage count, which usually more than compensates.

7. **The HBM beachfront limit is the genuine structural disadvantage.** Wafer HBM scales with perimeter; a GPU cluster's scales with unit count.

**Empirical (model outputs, provisional):**

8. Compound bounds at the recommended operating point: all-optimistic ~115× and ~6,650 tok/s; **all-pessimistic ~7× and ~254 tok/s — the only case where ROM loses on speed.** No single unknown at its pessimistic bound drops the advantage below ~21×.

9. The fabric question is **not** the critical path. Coarse-tile vs Cerebras-mesh spans ~46× to ~25× — it determines how good, not whether.

10. NRE (revised to ~$80–150M for a wafer-scale program) is 3–6% of cost per token at 1,000-wafer volume. Breakeven ~30 wafers. Not the binding constraint at frontier volume.

---

## 4. To be verified

Ranked by how much each moves the answer. Four of the top five need no foundry relationship.

| # | Item | Owner | Method | Phase |
|---|---|---|---|---|
| 1 | **Engineering derate** — MoE load imbalance, defect-repair indirection, clock skew, sync jitter, pipeline fill | Us | Trace-driven simulation | 2 |
| 2 | ROM read bandwidth per unit area at required port width | Foundry | SPICE → test chip | 3 |
| 3 | MAC density at required operand-delivery width | Foundry | Synthesis | 3 |
| 4 | Collective latency vs tile granularity | Us | NoC simulation | 2 |
| 5 | **True per-token KV read volume** for the target model | Us | Profile open weights | 0 |
| 6 | ROM cell density | Foundry | PDK → test chip | 3 |
| 7 | HBM beachfront achievable | OSAT | Packaging study | 3 |
| 8 | **Wordline-masked expert selection** — if viable, eliminates the dynamic-NoC risk entirely | Us → foundry | Circuit design, open PDK | 2b |
| 9 | Reticle stitching yield and repair | Foundry | Test vehicle | 4 |

**Gating, non-technical, do first (free):** will a model owner commit a checkpoint for a multi-year service life? Nothing downstream matters otherwise.

**Model limitations to fix before trusting outputs:** speculative decoding is a pure multiplier with no draft-generation cost (optimistic, and it's the main competing approach); no prefill, no P/D disaggregation, no prefix caching; pipeline stages assumed balanced; single lumped derate constant.

**Comparison hygiene** — each of these was violated during exploration and each violation changed a conclusion: compare against GPU *cost* not list price; enable speculative decoding on both sides; match capacity not unit count; use production operating points not dedicated-cluster figures; always report per-user speed and cost per token together.

---

## 5. One-line summary

ROM storage removes weight traffic from the memory tier, which is worth a large multiple at low-to-moderate batch on a large sparse MoE with aggressively compressed attention — DeepSeek-V4-Pro at 200K being the best candidate found — and the decision now rests on four measurable quantities, most of which can be settled for a few hundred thousand dollars without a foundry NDA, plus one organizational question that costs nothing to ask and gates everything.
