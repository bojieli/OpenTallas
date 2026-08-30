# What the weight-to-KV ratio and the KV capacity decide

Before any simulation, the architecture follows from two quantities computed
from the released checkpoints. This document derives them and states what design
each one forces. Every figure comes from `configs/models/*.json` through
`opentallas.workload`; nothing here is an assumed hardware number.

## 1. The two quantities

**Weight bytes read per token** is fixed by the checkpoint (for a dense model)
or by the experts one token activates (for an MoE). It does not grow with
context.

**KV bytes read per token** grows **linearly with context**. Sparse attention
lowers the constant; it does not change the growth. And **KV storage** grows
linearly with context *and* with batch, and sparsity does not reduce it at all —
a sparsely-attended cache is still a full cache.

Those are different constraints and they push in different directions. The first
sets how much a ROM weight path is worth. The second sets whether the KV can
live on-die.

## 2. The weight-to-KV read ratio

| model | context | weight read/token | KV read/token | **W:KV** |
|---|---:|---:|---:|---:|
| Qwen3-8B | 1,024 | 15.14 GB | 0.151 GB | **100** |
| Qwen3-8B | 8,192 | 15.14 GB | 1.208 GB | **12.5** |
| Qwen3-8B | 32,768 | 15.14 GB | 4.832 GB | **3.1** |
| DeepSeek-V4-Flash | 200,000 | 11.22 GB | 0.099 GB | **113** |
| DeepSeek-V4-Flash | 1,000,000 | 11.22 GB | 0.458 GB | **24.5** |
| DeepSeek-V4-Pro | 200,000 | 39.67 GB | 0.153 GB | **260** |
| DeepSeek-V4-Pro | 1,000,000 | 39.67 GB | 0.674 GB | **59** |

**The result is the opposite of the intuition that long context erodes the ROM
case.** Sparse attention keeps DeepSeek's KV read tiny: at 200,000 tokens Flash
reads 99 MB of KV against 11.2 GB of weights. The models that need wafer-scale
are precisely the ones where the weight path dominates *most*.

Dense attention behaves the other way. Qwen3-8B falls from 100:1 at 1K to 3.1:1
at 32K, because it rereads the whole cache every token. A dense 8B model's ROM
advantage is a **short-context** advantage.

## 3. KV capacity, and where SRAM stops working

On-die SRAM area to hold the KV cache, at N6 (0.024 µm²/bit, 60% array
efficiency). One reticle die is 815–858 mm².

| model | context | KV/user | B=1 | B=8 | B=64 |
|---|---:|---:|---:|---:|---:|
| Qwen3-8B | 1,024 | 0.15 GB | 48 mm² | 387 mm² | 4 dies |
| Qwen3-8B | 8,192 | 1.21 GB | **387 mm²** | 4 dies | 30 dies |
| Qwen3-8B | 32,768 | 4.83 GB | 2 dies | 15 dies | 121 dies |
| DeepSeek-V4-Flash | 200,000 | 0.70 GB | 226 mm² | 2 dies | 18 dies |
| DeepSeek-V4-Pro | 1,000,000 | 5.03 GB | 2 dies | 16 dies | 126 dies |

SRAM holds the KV only for a small model, at short context, at low batch. That
is exactly the Taalas HC1 regime, and it is why its published figure is quoted
**per user**.

## 4. Bandwidth versus capacity: they bind different machines

| target | KV bandwidth demand | stacks for BW | KV capacity at B=64 | stacks for capacity |
|---|---:|---:|---:|---:|
| Qwen3-8B @8K, 10,000 tok/s | **12.08 TB/s** | 10.1 | 77 GB | 3.2 |
| DeepSeek-Flash @200K, 6,600 tok/s | 0.65 TB/s | 0.5 | 45 GB | **1.9** |
| DeepSeek-Pro @1M, 3,000 tok/s | 2.02 TB/s | 1.7 | 322 GB | **13.4** |

(HBM3E: 24 GB and ~1.2 TB/s per stack.)

**Dense Qwen is KV-bandwidth-bound; sparse DeepSeek is KV-capacity-bound.** That
single distinction determines the memory technology:

- Qwen at 8K needs 12 TB/s of KV bandwidth. Ten HBM stacks would supply it; a
  few hundred mm² of SRAM supplies it trivially. **SRAM is chosen for
  bandwidth**, and the capacity limit is what caps context and batch.
- DeepSeek at 200K needs only 0.65 TB/s but tens to hundreds of GB. **HBM is
  chosen for capacity**, and its bandwidth is never the constraint.

## 5. Why the big models need a wafer — and it is the weights, not the KV

ROM array area the weights demand, at the derived N6/N7 density of 19.7 MB/mm²:

| model | representation | ROM array | reticles | wafer |
|---|---|---:|---:|---:|
| Qwen3-8B | native BF16 | 832 mm² | 1.0 | 1.8% |
| Qwen3-8B | FP8 | 416 mm² | 0.5 | 0.9% |
| DeepSeek-V4-Flash | native (MXFP4+FP8) | 8,471 mm² | 9.9 | 18.3% |
| DeepSeek-V4-Flash | FP8 | 14,416 mm² | 16.8 | 31.2% |
| DeepSeek-V4-Pro | native | 45,316 mm² | 52.8 | **98.0%** |
| DeepSeek-V4-Pro | FP8 | 81,218 mm² | 94.7 | **175.7%** |

Qwen3-8B is a **single reticle-class chip** — half a die of ROM in FP8. Flash
needs ~10 reticles, so a wafer. Pro in its native MXFP4 representation consumes
a whole wafer in ROM alone, leaving nothing for compute; in FP8 it needs two.
**That is where the area balance genuinely binds, and it is why the stored
representation is a design variable rather than an inherited constant** — mask
ROM freezes it at manufacture.

## 6. The architecture this forces

| | Qwen3-8B | DeepSeek-V4-Flash | DeepSeek-V4-Pro |
|---|---|---|---|
| part | one reticle chip | wafer | 2+ wafers |
| weights | ROM, 416 mm² | ROM, ~10 reticles | ROM, ~53 reticles |
| KV | **SRAM** (bandwidth) | **HBM** (capacity) | **HBM** (capacity) |
| binds at low batch | KV bandwidth | weight read | weight read |
| binds at high batch | KV capacity | KV capacity | KV capacity |
| compared against | **one** GPU die | ~56 GPU dies | ~112 GPU dies |

The hybrid is not a compromise; each memory is chosen for the quantity that
actually binds. Weights go to ROM in every case, because W:KV is between 3 and
260 and never inverts. KV goes wherever the binding quantity — bandwidth for
dense, capacity for sparse — can be met.

## 7. What this means for the comparison

The ROM advantage is largest exactly where W:KV is largest: **DeepSeek-V4-Pro at
200,000 tokens, at 260:1**. It is smallest for a dense model at long context,
where it falls to 3:1 and the machine becomes a KV engine that happens to have
its weights on-die.

This should be stated as the headline of any write-up, because it is
counter-intuitive and it is the project's actual finding: **sparsity plus long
context is the ROM-favourable regime, not the adverse one.**
