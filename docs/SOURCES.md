# Source and evidence register

**Status:** analytical-baseline source register

**Last checked:** 2026-08-27 UTC
**Scope:** public, non-NDA evidence only

This register records the primary evidence used by the executable analytical
model. `rom-inference-brief.md` is an input hypothesis, not a source. A value is
not considered published merely because it appeared in that brief or in an
earlier generated report.

## Evidence classes

- `measured`: extracted from a pinned public artifact by repository code, with
  integrity metadata sufficient to reproduce the extraction.
- `published`: stated by the model or hardware vendor, or in a cited primary
  technical report.
- `derived`: arithmetic or structural interpretation of measured/published
  inputs. The derivation must be stated.
- `simulated`: emitted by an executable model from identified inputs.
- `assumed`: a hypothesis or sweep point with no qualifying measurement.
- `synthetic`: generated stimulus used to exercise behavior; never a production
  trace.

The repository does not use secondary press reports for a value when an official
model card, checkpoint, report, or vendor datasheet is available.

## Model primary sources

| ID | Primary artifact | Immutable pin | Evidence used |
|---|---|---|---|
| SRC-DSV4-REPORT | [DeepSeek-V4 technical report, arXiv:2606.19348v1](https://arxiv.org/abs/2606.19348v1) | arXiv v1, published 2026-04-26 | Flash 284B total/13B active; Pro 1.6T total/49B active; one-million-token context; CSA/HCA architecture. |
| SRC-DSV4-FLASH-CARD | [DeepSeek-V4-Flash-0731 model card](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/README.md) | `7872f01b1d1fe23eabc4c98b48bffcef5a386062` | Official release identity; attached DSpark module; serving recipe uses FP8 KV and FP4 indexer cache; target and draft are in the same checkpoint. |
| SRC-DSV4-FLASH-CONFIG | [DeepSeek-V4-Flash-0731 config](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/config.json) | same revision; local SHA-256 `6c8f3d2d3b48707541b88f32f22ef3f0f8a6b57d8523281e2b8d3cdb0ae9a023` | 43-layer compression sequence, hidden dimensions, expert count/top-k, index dimensions/top-k, context limit, and sliding window. |
| SRC-DSV4-FLASH-INDEX | [DeepSeek-V4-Flash-0731 safetensors index](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/model.safetensors.index.json) and pinned shard headers | same revision; index SHA-256 `98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b` | Exact released storage, dtype, tensor-role, per-layer, dense/routed, draft-only, and resident-only inventory. |
| SRC-DSV4-PRO-CARD | [DeepSeek-V4-Pro-0813 model card](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/blob/72e1d3230f6c080a530b0a1d46f8eb4602340597/README.md) | `72e1d3230f6c080a530b0a1d46f8eb4602340597` | Official release identity; attached DSpark module; FP8 KV/FP4 indexer serving recipe; shared target/draft checkpoint. |
| SRC-DSV4-PRO-CONFIG | [DeepSeek-V4-Pro-0813 config](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/blob/72e1d3230f6c080a530b0a1d46f8eb4602340597/config.json) | same revision; local SHA-256 `9dd2a89255469e120b333668ef5a169b7ae46c00f6bbab786bf0be457546aec0` | 61-layer compression sequence, hidden dimensions, 384 experts/top-6, index dimensions/top-1024, and context limit. |
| SRC-DSV4-PRO-INDEX | [DeepSeek-V4-Pro-0813 safetensors index](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/blob/72e1d3230f6c080a530b0a1d46f8eb4602340597/model.safetensors.index.json) and pinned shard headers | same revision; index SHA-256 `2de2ac1e43134f8b03bf6156067715b7c3c73b1a507329e606023c601a56d30a` | Exact released-format inventory and decode-role split. |
| SRC-K3-CARD | [Kimi-K3 model card](https://huggingface.co/moonshotai/Kimi-K3/blob/a590ce090cb049c93a33dfe8c208ec652aa20503/README.md) | `a590ce090cb049c93a33dfe8c208ec652aa20503` | 2.8T total/104B active, 93 layers, 69 KDA + 24 gated MLA, 896 experts/top-16, and 1,048,576-token context. |
| SRC-K3-CONFIG | [Kimi-K3 config](https://huggingface.co/moonshotai/Kimi-K3/blob/a590ce090cb049c93a33dfe8c208ec652aa20503/config.json) | same revision; local SHA-256 `9710e121a58d03ac92c8d6da287a19541994319afbbe6d6202af001ffd379213` | Exact layer IDs, KDA state dimensions, latent dimensions, hidden size, experts, and context limit used by the profiler. |
| SRC-K3-INDEX | [Kimi-K3 safetensors index](https://huggingface.co/moonshotai/Kimi-K3/blob/a590ce090cb049c93a33dfe8c208ec652aa20503/model.safetensors.index.json) and pinned shard headers | same revision; index SHA-256 `a1c5210650ce71d2d3ae9ec5a101ac4afd3cf4b10091be589853437eb967febd` | Exact released-format inventory and text-decode versus multimodal/resident-only split. |
| SRC-QWEN3-8B-CARD | [Qwen3-8B model card](https://huggingface.co/Qwen/Qwen3-8B/blob/b968826d9c46dd6066d109eabc6255188de91218/README.md) | `b968826d9c46dd6066d109eabc6255188de91218` | Official dense-model identity; 8.2B total, 6.95B non-embedding, 36 layers, GQA with 32 query/8 KV heads, 32,768 native context, and no attached draft module. |
| SRC-QWEN3-8B-CONFIG | [Qwen3-8B config](https://huggingface.co/Qwen/Qwen3-8B/blob/b968826d9c46dd6066d109eabc6255188de91218/config.json) | same revision; local SHA-256 `f7c4eadfbbf522470667b797a3c89be2524832d2d599797248dc304fff447c30` | 36 layers, 4,096 hidden size, 32 query/8 KV heads, 128 head dimension, BF16 storage declaration, untied embeddings, and 40,960 configured position allocation. |
| SRC-QWEN3-8B-INDEX | [Qwen3-8B safetensors index](https://huggingface.co/Qwen/Qwen3-8B/blob/b968826d9c46dd6066d109eabc6255188de91218/model.safetensors.index.json) and pinned shard headers | same revision; index SHA-256 `f9fdbcb91c23971c13ec5d5f2573d2349e8f61f2f049371ec699281748fdb1bc` | 399 all-BF16 tensors, exactly 8,190,735,360 parameters/16,381,470,720 bytes; exact layer, input-embedding, and untied output-head accounting. |

The generated inventories are committed under `data/inventory/`. The profiler
reads only `config.json`, the safetensors index, and HTTP byte ranges covering
each safetensors JSON header. It checks that every indexed tensor appears exactly
once, that no extra tensor appears, and that the sum of header data offsets equals
the index's declared total size. It does **not** download or execute the full
checkpoint and therefore makes no quality, numerical-accuracy, acceptance-rate,
or production-throughput claim.

## NVIDIA primary sources and normalization

| ID | Primary artifact | Published system values used | Derived per-GPU-equivalent values |
|---|---|---|---|
| SRC-NV-B200 | [NVIDIA DGX B200 product specifications](https://www.nvidia.com/en-us/data-center/dgx-b200/) | 8 Blackwell GPUs; 1,440 GB total HBM; 64 TB/s aggregate HBM3e; 72 dense FP4 PFLOPS (144 sparse); 72 sparse FP8 PFLOPS, hence 36 dense by NVIDIA's half-sparse footnote; approximately 14.3 kW maximum system power; 14.4 TB/s aggregate NVLink. | 180 GB capacity, 8 TB/s HBM, 9 dense FP4 POP/s, 4.5 dense FP8 POP/s, and 1,787.5 W allocated system-power envelope per GPU-equivalent. |
| SRC-NV-B300 | [NVIDIA DGX B300 February 2026 datasheet](https://dam-cdn.nvd.orangelogic.com/AssetLink/625w0j7hnw6f07ui7fo63211mti2v08o.pdf) and [NVIDIA DGX B300 system guide](https://docs.nvidia.com/dgx/dgxb300-user-guide/introduction-to-dgxb300.html) | Datasheet: 2.1 TB total label, 62 TB/s aggregate HBM3e, 108 dense FP4 PFLOPS (144 sparse), 72 sparse / 36 dense FP8 PFLOPS, 14.4 TB/s aggregate NVLink, and 14.5 kW busbar / 15.1 kW PSU. System guide: exact **8 × 288 GB = 2.3 TB total** population. | **288 GB** physical capacity, 7.75 TB/s HBM, 13.5 dense FP4 POP/s, 4.5 dense FP8 POP/s, and 1,812.5 W busbar envelope per GPU-equivalent. |

The checked B300 PDF identifies itself as document `4868000`, `Feb26`; its
downloaded SHA-256 was
`bf7b1cac562749d5d6f486a817130b24e13f0f3ff8a2989049aefd966f9afee0`.

The two official B300 documents use different total-memory labels. The system
guide is device-explicit (`8 × 288 GB = 2.3 TB`) and therefore controls capacity
accounting. The datasheet's `2.1 TB` label is retained as published provenance but
is not interpreted as eight 262.5 GB devices. A separate 90% usable-HBM assumption
provides the runtime/workspace reserve.

The x1, x2, x4, and x16 profiles are analytical fractional/two-node normalizations;
NVIDIA does not publish them as DGX B200/B300 SKUs. They are included so model
size and feasible cluster size are not confounded, particularly for Qwen3-8B.
Peak arithmetic is not measured application
performance; the simulator applies explicit assumed compute, bandwidth,
load-balance, clock, and synchronization efficiencies. Published 14.4 TB/s NVLink
is retained as a source fact but is **not** substituted directly for the assumed
effective collective payload bandwidth or per-layer latency.

## Internally generated evidence

| ID | Artifact | Class | Boundary |
|---|---|---|---|
| GEN-INVENTORY | `data/inventory/*.json` | measured from pinned public metadata | Exact encoded storage only; no model execution. |
| GEN-ANALYTICAL | `results/standard/analytical.json`, `sweep.csv`, `REPORT.md`, and `QWEN3_8B_ADDENDUM.md` | simulated/derived | Conditional on every hardware and runtime assumption in `docs/ASSUMPTIONS.md`. |
| GEN-ROUTING | `results/routing/*.json` | synthetic/simulated | Uniform and correlated stress routing; not production activation traces. |
| GEN-NOC | `results/noc/*` | simulated | Purpose-built topology/serialization model; not placed-and-routed timing. |
| GEN-SENSITIVITY | `results/sensitivity/*` | simulated/derived | One-factor and bounded-grid results, not probability distributions. |

## Explicitly unavailable evidence

No public source currently establishes the target-node via-ROM density, full-array
read bandwidth, sense margin, yield, repair overhead, MAC density, wafer HBM
beachfront, stitched-wafer timing, power delivery, cooling, unit cost, NRE, or
production DeepSeek/Kimi router traces or any model's production KV traces. Those
inputs remain assumptions or
open gates. Open-PDK work can test methodology and topology but cannot promote any
of them to leading-node measured evidence.
