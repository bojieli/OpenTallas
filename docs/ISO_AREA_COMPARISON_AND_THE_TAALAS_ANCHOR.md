# Iso-area comparison, and the shipping part that anchors it

This document exists because the project derived an impossible result from a
placeholder it never checked, and then compared it unfairly. Both failures have
the same root: a configured number was treated as ground truth.

## 1. The anchor

**Taalas HC1** is a shipping mask-ROM inference accelerator. AMD announced an
acquisition of the company in August 2026.

| | published |
|---|---|
| process | TSMC 6 nm |
| die area | **815 mm²** |
| transistors | **53 billion** |
| weights | mask ROM on-die |
| KV cache | on-die SRAM |
| throughput | **~17,000 tokens/s per user**, Llama 3.1 8B |

Sources: [ServeTheHome](https://www.servethehome.com/amd-to-acquire-taalas-for-model-specific-ai-inference-chips/),
[The Register](https://www.theregister.com/systems/2026/08/06/amd-acquires-ai-chip-startup-taalas-to-boost-inference-performance-by-etching-models-into-silicon/5284344),
[HC1 analysis](https://medium.com/@bmilew/a-look-at-taalas-hc1-chip-reaching-new-heights-in-llm-inference-56cd079f59a3).

**Any model of a ROM accelerator must reproduce this.** A methodology that
predicts 2,000 tok/s or 200,000 tok/s for an 8B model on 815 mm² at N6 is wrong,
however internally consistent it is, because a real part says otherwise. The
anchor is a test the model must pass, not a datapoint to be averaged in.

## 2. The iso-area comparison

An NVIDIA A100 80GB is 826 mm² at TSMC N7 with 54.2 billion transistors —
essentially the same die as HC1, one node apart. That is the comparison:

| | Taalas HC1 | NVIDIA A100 80GB |
|---|---:|---:|
| node / die | N6 / 815 mm² | N7 / 826 mm² |
| transistors | 53 B | 54.2 B |
| weights live in | mask ROM on-die | HBM at 2.04 TB/s |
| 8B model, batch 1 | **17,000 tok/s** | 254 tok/s (FP8) · 127 (BF16) |
| ratio | | **67× · 134×** |

HC1's implied compute is ~273 TFLOPS on 815 mm², against A100's published 312
TFLOPS on 826 mm². So HC1 is **not** compute-starved and **not** weight-bound:
it carries GPU-class compute and simply does not pay for weight traffic. That is
the thesis, in silicon.

**Every comparison in this program must state the silicon area on both sides.**

- A reticle-class ROM chip is compared against **one** GPU die.
- A wafer-scale part (46,225 mm²) is compared against **~56 A100-equivalent
  dies**, because that is equal silicon. Blackwell is a two-die package, so
  count per package accordingly.

## 3. What went wrong, twice

**The legacy study's ROM profile was compute-starved by assumption.** It gave a
whole wafer a 5.00e14 ops/s FP8 roof — 0.11× the compute of a single B200 die —
across 29× the area, an assumed compute density 0.0038× NVIDIA's per mm². Its
own evidence field said `"assumed:midpoint hypothesis only"`. Every ROM point
was therefore `compute_C5`-bound, and that was read as a property of ROM
architectures rather than of the placeholder.

**The current study's comparison was not iso-area.** It reported ROM-wafer-N7 at
4,125 tok/s for Qwen3-8B against A100-x32 and A100-x64 — one 46,225 mm² wafer
against 26,432–52,864 mm² of GPU. Per unit area that ROM model is **234× more
pessimistic than a shipping part**: 0.089 tok/s/mm² against HC1's 20.9.

**The design error underneath it is nameable.** The study's ROM wafer is
`kv_beachfront_C8`-bound at every batch for Qwen, because it puts the KV cache
behind HBM2e. Taalas keeps KV in on-die SRAM. For an 8B model that is the whole
difference — the study penalised ROM with a memory technology the real product
does not use for that data.

## 4. The method, stated so it is checkable

1. **Fix the silicon area first.** It is the binding constraint; everything else
   is an allocation decision within it.
2. **Derive capacity, bandwidth and compute roof from area and published
   densities.** They are outputs. A profile that states them as free inputs is
   not a design.
3. **Search for current published data** rather than inheriting a configured
   number. Grade every figure published / derived / measured / assumed, with a
   source.
4. **Validate against a shipping part** before predicting one that does not
   exist.
5. **Compare at equal area**, and say the area on both sides.

The failure mode this replaces is not arithmetic error. It is accepting a number
because it was already in the file.
