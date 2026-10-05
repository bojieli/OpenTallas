# Third-party speculative-decoding acceptance (2026-10-04)

> OWNER RULE 2026-10-04: speculative-decoding acceptance and the DeepSeek-V4.1 GPU decode baseline must come from PUBLISHED THIRD-PARTY sources (MLCommons, LMSys/SGLang, vLLM, model vendors, NVIDIA/AMD, ...), never from our own measurement. OWNER CORRECTION: cite this registry instead of re-researching.

Convention: tau = mean tokens committed per verify step INCLUDING the bonus token (EAGLE/DSpark 'accepted length'). Sources are ids in [`results/external/registry.json`](../../external/registry.json). Read by `tools/third_party_tau.py`, which every composition uses (`OT_TAU_SOURCE=adopted` is the default; `third_party` gives the published DS sensitivity; `self_measured` reproduces the superseded records).

## Owner decision 2026-10-05

DeepSeek-V4.1 composition default tau = 4.159, the owner 6-class workload blend (harmonic, greedy, gamma 5) in results/speculative/v41_mtp_acceptance_qualified_20261003/blend_owner6.json; the published V4.1 value 3.8879 and the published V4.1 gamma-5 range 3.43-4.32 are kept as a SENSITIVITY (OT_TAU_SOURCE=third_party). Qwen3-8B keeps the third-party derived 3.1445.

Reason: OWNER: a single GSM8K dataset (the 3.8879 primary) makes no sense as the headline workload, and several published sources are V4-Flash, not V4.1.

Supersedes: the 2026-10-04 owner rule's DS default (published 3.8879); the third-party figures below are unchanged.

| Model | Draft tokens | Composition default tau | Basis | Published primary (third-party) | Published range | Superseded (ours) |
|---|---|---|---|---|---|---|
| Qwen3-8B + DSpark | 3 | **3.1445** | derived-from-published | 3.1445 | 2.5649-3.5676 | 3.0375 |
| DeepSeek-V4.1-Flash + DSpark | 5 | **4.159** | owner 6-class workload blend (adopted 2026-10-05) | 3.8879 (sensitivity) | 3.43-4.31748 (sensitivity) | - |

## Qwen3-8B

The Qwen ROM DSpark composition (results/rtl/qwen_dspark_system_20261004/ctx8k/step_composed_ctx8k.json) verifies a block of 4 positions = 3 draft tokens + bonus (S=3 drafter slots, n_emit 4 at a=3), so it takes tau at 3 draft tokens; values at 4 and 5 draft tokens are listed for a gamma-4/5 configuration.

No source publishes a Qwen3-8B DSpark acceptance length at 3-5 draft tokens. DeepSeek's DSpark paper (Table 1) publishes it at gamma 7, and its drafters are released only as block-7 checkpoints. The primary is therefore DERIVED from Table 1. For each benchmark, the constant conditional acceptance r is solved from tau7 = 1 + sum r^i; the paper reports that DSpark's per-position acceptance is stable across positions 1-7. The tau at k draft tokens then follows, and the 9 benchmarks (3 math, 3 code, 3 chat) are weighted equally.

| k | derived tau |
|---|---|
| 3 | 3.1445 |
| 4 | 3.6579 |
| 5 | 4.0996 |

Published gamma-7 mean: 4.8133. A cross-check on the published InferenceX DSpark k-curve (V4-Pro) shows that the truncation under-estimates by about 7-8% at k=3, so the derived primary is conservative:

| k | published | geometric from k=7 | ratio |
|---|---|---|---|
| 3 | 3.01 | 2.787 | 1.0798 |
| 4 | 3.36 | 3.126 | 1.075 |
| 5 | 3.61 | 3.383 | 1.067 |

Mismatch labels: draft length: published only at gamma 7; truncated to 3 by a constant-conditional model (DSpark's per-position conditional acceptance is published as stable across positions 1-7); temperature 1.0, non-thinking (paper's offline protocol); dataset: 9 public benchmarks, not the owner 6-class mix.

Corroborating values (other drafters): the RedHat EAGLE-3 card gives k=3 2.13-2.48 and k=5 2.25-2.72 at T=0.6. The Eagle3 gamma-7 mean in DSpark Table 1 is 3.7978. DeepSeek's dspark_qwen3_8b_block7 measured 3.41 on SPEED-Bench coding with a community harness (k=7). AngelSlim EAGLE-3 gives 1.99 at k=2.

## DeepSeek-V4.1-Flash (DSpark, block 5)

Composition default: **4.159**, the owner 6-class workload blend (adopted 2026-10-05) (`results/speculative/v41_mtp_acceptance_qualified_20261003/blend_owner6.json blends['owner 6-class equal'].greedy.tau_blend_harmonic`). The published values below are kept as a sensitivity.

Published primary 3.8879 (vLLM PR #57432, TP4, same model revision, after the acceptance fix). It is within 1% of the median (3.856) of the published V4.1-Flash gamma-5 set. Mismatch: dataset GSM8K (reasoning) only, greedy, short outputs (<=1,024).

| Source | tau | Conditions |
|---|---|---|
| `acc:VLLM_57432` | 3.8879 | GSM8K 1,319, greedy, thinking off, 4x GB200 vLLM TP4 (post-fix, same revision) |
| `acc:VLLM_57432` | 3.8248 | same, DEP4 |
| `acc:INFX_V41` | 4.07 | SPEED-Bench coding, T=1.0, thinking off, B300 vLLM TP4 (pre-fix image) |
| `acc:INFX_V41` | 3.51 | SPEED-Bench coding, T=1.0, thinking on (pre-fix image) |
| `acc:SGL_38929` | 4.31748 | GSM8K, greedy, thinking off, SGLang PD B300 (closed PR) |
| `acc:VLLM_56797_AGENTIC` | 3.43 | production agentic traffic, thinking max, 4x H200 (community counters) |

Other members of the family (labelled, not used): V4-Flash TRT-LLM 4.07, V4-Pro DSpark k=5 3.61 (thinking on), V4-Pro native MTP k=5 3.10 (thinking off), V3 MTP-1 1.85-1.90.
