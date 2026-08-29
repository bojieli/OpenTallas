# Source and evidence register

**Status:** analytical-baseline source register

**Last checked:** 2026-08-28 UTC
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

## 2026-08-28 online identity and reachability recheck

Fresh downloads of the pinned DeepSeek Flash and Pro `config.json` and
`model.safetensors.index.json` files produced the four SHA-256 values recorded
below exactly. The DeepSeek report, NVIDIA A100 page, NVIDIA B300 datasheet and
system guide, NVIDIA Blackwell page, Cerebras chip page, and Graphcore IPU page
all returned successful public responses after redirects. The fabricated 28-nm
ROM paper's IEEE DOI resolver also responded and resolved to IEEE Xplore.

The YOLoC and 3D-METRO DOI resolvers reached their ACM Digital Library landing
pages, but those pages returned HTTP 403 to the automated recheck. Their DOI
identities remain pinned citations; this run does **not** claim fresh access to
or content validation of the ACM papers. Reachability never upgrades a
published or simulated result to measured product evidence.

## Model primary sources

| ID | Primary artifact | Immutable pin | Evidence used |
|---|---|---|---|
| SRC-DSV4-REPORT | [DeepSeek-V4 technical report, arXiv:2606.19348v1](https://arxiv.org/abs/2606.19348v1) | arXiv v1, published 2026-04-26 | Flash 284B total/13B active; Pro 1.6T total/49B active; one-million-token context; CSA/HCA architecture; routed experts use MXFP4 weights with FP8 activations; dense/shared matrices remain FP8-class; the report explicitly says current hardware executes FP4×FP8 at the FP8×FP8 peak, while a future native implementation could theoretically be one-third more efficient. |
| SRC-DSV4-FLASH-CARD | [DeepSeek-V4-Flash-0731 model card](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/README.md) | `7872f01b1d1fe23eabc4c98b48bffcef5a386062` | Official release identity; attached DSpark module; serving recipe uses FP8 KV and FP4 indexer cache; target and draft are in the same checkpoint. |
| SRC-DSV4-FLASH-CONFIG | [DeepSeek-V4-Flash-0731 config](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/config.json) | same revision; local SHA-256 `6c8f3d2d3b48707541b88f32f22ef3f0f8a6b57d8523281e2b8d3cdb0ae9a023` | 43-layer compression sequence, hidden dimensions, expert count/top-k, index dimensions/top-k, context limit, and sliding window. |
| SRC-DSV4-FLASH-MODEL | [DeepSeek-V4-Flash-0731 inference model](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/inference/model.py) | same revision; local SHA-256 `c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f` | Official decode graph and tensor/operator ordering, including normalization, compressor pooling, index scoring/top-k, routing, SwiGLU, RoPE, hyper-connections, and logits. `RMSNorm.forward` explicitly widens BF16 input, squares and means in FP32, adds `1e-6`, applies `torch.rsqrt`, multiplies the FP32-loaded BF16 checkpoint weight, and returns the input dtype. Separately, `Attention.forward` applies unweighted square/mean/epsilon/rsqrt normalization in place to the BF16 query expansion returned by `fp8_gemm`; native dtype checks retain BF16 at each visible boundary. `Indexer` constructs its 4,096-to-64 `weights_proj` with BF16 weights, and `linear` dispatches that bias-free path to `F.linear`; official headers confirm all 21 tensors are `[64, 4096]` BF16. `Gate.forward` explicitly widens hidden state and router weight before the same bias-free dispatcher, retaining binary32 scores; all 46 official gate tensors are `[256, 4096]` BF16. The source defines work but does not fix backend GEMM/reduction trees, reciprocal-square-root approximations, or a custom-wafer service roof. |
| SRC-DSV4-FLASH-REQUIREMENTS | [DeepSeek-V4-Flash-0731 inference requirements](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/inference/requirements.txt) | same revision; SHA-256 `857e0b8b58e41cabe16e55bf4ab7ff791677c53b25f0f3e104ef85227cd11eab` | Declares `torch>=2.10.0` and unversioned `fast_hadamard_transform` rather than exact implementations. Backend-incidental reduction trees, reciprocal-square-root approximations, equal-score ordering, FTZ behavior, and dependency-specific Hadamard rounding therefore cannot silently become architectural contracts. |
| SRC-DSV4-FLASH-GENERATE | [DeepSeek-V4-Flash-0731 local generation loop](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/inference/generate.py) | same revision; local SHA-256 `775fcfee2344e21a7b02c73161c517763e4348b84cf2eb266353e0857b9c8812` | Exact target-only prefill/decode spans, prompt override, EOS/length termination, and exponential-race sampling expression. The independent controller reproduces this control behavior with synthetic executor transcripts; the source does not invoke DSpark, implement top-p filtering, or pin Torch/CUDA RNG replay. |
| SRC-DSV4-FLASH-ENCODING | [DeepSeek-V4-Flash-0731 message encoding](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/encoding/encoding_dsv4.py) and [official tests](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/encoding/test_encoding_dsv4.py) | same revision; source SHA-256 `abc0d26120250dda0ae077dc64aa28836026e61e970854aaeb792445e6a0dde6`; test SHA-256 `c2bc54c4c934f5c64096bd9c555efa7d1ddf179c1eff58f01ceb2dcd60adcf28`; eight exact fixture payloads are independently size/hash checked | Official prompt-text and completion-parser grammar for chat/thinking modes, DSML tool calls/results, reasoning-effort prefixes, developer/latest-reminder messages, and quick-task tokens. The independent fail-closed implementation matches all four published valid fixtures; by itself this does not establish tokenizer or model execution semantics. |
| SRC-DSV4-FLASH-TOKENIZER | [DeepSeek-V4-Flash-0731 tokenizer](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/tokenizer.json) and [tokenizer config](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/tokenizer_config.json) | same revision; tokenizer SHA-256 `8f9f37ca37fdc4f5fd36d5cf4d3b0e8392edb4e894fd10cc0d70b4957c8633cf`; config SHA-256 `6ac8c8dc065ed118161d02dd532749ae3f52c243deac27872134fae2f50d8547` | Exact BPE and special-token data for the independently hash-verified local-only loader. It establishes prompt/token-ID and decode-text behavior under pinned `tokenizers==0.22.2`; it does not establish model inference or generated-token correctness. |
| SRC-DSV4-FLASH-KERNEL | [DeepSeek-V4-Flash-0731 inference kernels](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/inference/kernel.py) | same revision; local SHA-256 `59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2` | Official sparse-attention online-softmax, `hc_split_sinkhorn`, block-64 KV `act_quant`, and block-32 indexer `fp4_act_quant` structure. The FP8 path fixes the binary32 `1e-4` floor, rounded `1/448`, bit-ceiling power-of-two scale, E4M3FN clamp/cast, and in-place BF16 reconstruction; the FP4 path analogously fixes the `6·2^-126` floor, rounded `1/6`, E2M1 clamp/cast, and reconstruction. GPU kernel code is not ported into an assumed ROM-wafer throughput. |
| SRC-FHT-1.1.0 | [`fast_hadamard_transform` v1.1.0 source](https://github.com/Dao-AILab/fast-hadamard-transform/tree/1cc807efbd6cc001df359822d60bf6052dd66859) | Git revision `1cc807efbd6cc001df359822d60bf6052dd66859`; interface SHA-256 `a2f32a615b03c83d075fd49eba266c9f6c13df790cbe549db3bf8c0c1f3e8877`; common CUDA header SHA-256 `e51345eb6be7b43cb657d73b8db9b2debcb4060de2266c7b42fc45bb3b86b473`; CUDA translation unit SHA-256 `aed649e84fe379d1adfdb061fc6f622f55612ddcd103f51f08ee984ff4dff34f` | Development cross-check for the release's unversioned dependency, not evidence that this exact tag was installed by DeepSeek. It documents Sylvester-matrix equivalence and exposes the width-128 seven-stage FP32 butterfly, one scale multiply, BF16 store, and fast-math FTZ behavior used to qualify the governed NUM-3.6 adaptation. |
| SRC-DSV4-FLASH-CONVERT | [DeepSeek-V4-Flash-0731 checkpoint conversion](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/inference/convert.py) | same revision; local SHA-256 `6efe65ebc66b18c9f2656816608f941cacfe20da79c2dee19040ecbee8b42bfe` | Official tensor naming, model-parallel slicing, expert assignment, E2M1 lookup/nibble order, native-FP4 view, and `wo_a` dequantization rules reproduced by the deterministic canonical plan and independent numeric checks. Full official-payload application remains open. |
| SRC-DSV4-FLASH-INDEX | [DeepSeek-V4-Flash-0731 safetensors index](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/model.safetensors.index.json) and pinned shard headers | same revision; index SHA-256 `98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b` | Exact released storage, dtype, tensor-role, per-layer, dense/routed, draft-only, and resident-only inventory. |
| SRC-DSV4-PRO-CARD | [DeepSeek-V4-Pro-0813 model card](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/blob/72e1d3230f6c080a530b0a1d46f8eb4602340597/README.md) | `72e1d3230f6c080a530b0a1d46f8eb4602340597` | Official release identity; attached DSpark module; FP8 KV/FP4 indexer serving recipe; shared target/draft checkpoint. |
| SRC-DSV4-PRO-CONFIG | [DeepSeek-V4-Pro-0813 config](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/blob/72e1d3230f6c080a530b0a1d46f8eb4602340597/config.json) | same revision; local SHA-256 `9dd2a89255469e120b333668ef5a169b7ae46c00f6bbab786bf0be457546aec0` | 61-layer compression sequence, hidden dimensions, 384 experts/top-6, index dimensions/top-1024, and context limit. |
| SRC-DSV4-PRO-MODEL | [DeepSeek-V4-Pro-0813 inference model](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/blob/72e1d3230f6c080a530b0a1d46f8eb4602340597/inference/model.py) | same revision; local SHA-256 `c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f`; byte-identical to the pinned Flash file | Official Pro decode graph and tensor/operator ordering. The identical source hash permits the same source-level operator derivation with Pro's independently pinned configuration and tensor inventory. |
| SRC-DSV4-PRO-KERNEL | [DeepSeek-V4-Pro-0813 inference kernels](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/blob/72e1d3230f6c080a530b0a1d46f8eb4602340597/inference/kernel.py) | same revision; local SHA-256 `59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2`; byte-identical to the pinned Flash file | Official Pro sparse-attention online-softmax, `hc_split_sinkhorn`, and block-32 indexer FP4 QDQ structure. The source identity does not imply identical dimensions; those remain configuration- and checkpoint-derived. |
| SRC-DSV4-PRO-CONVERT | [DeepSeek-V4-Pro-0813 checkpoint conversion](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/blob/72e1d3230f6c080a530b0a1d46f8eb4602340597/inference/convert.py) | same revision; local SHA-256 `6efe65ebc66b18c9f2656816608f941cacfe20da79c2dee19040ecbee8b42bfe`; byte-identical to the pinned Flash file | Confirms the same official packed E2M1 values and nibble order for Pro. |
| SRC-DSV4-PRO-INDEX | [DeepSeek-V4-Pro-0813 safetensors index](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/blob/72e1d3230f6c080a530b0a1d46f8eb4602340597/model.safetensors.index.json) and pinned shard headers | same revision; index SHA-256 `2de2ac1e43134f8b03bf6156067715b7c3c73b1a507329e606023c601a56d30a` | Exact released-format inventory and decode-role split. |
| SRC-PYTORCH-210-TOPK | [PyTorch 2.10 `torch.topk` documentation](https://docs.pytorch.org/docs/2.10/generated/torch.topk.html) | versioned 2.10 documentation; checked 2026-08-28 UTC | States that indices of tied elements are not guaranteed stable. OpenTallas therefore defines score-descending/index-ascending selection as an explicit deterministic target adaptation and tests non-tied results against the installed PyTorch implementation. |
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
| SRC-NV-B200 | [NVIDIA DGX B200 product specifications](https://www.nvidia.com/en-us/data-center/dgx-b200/) | 8 Blackwell GPUs; 1,440 GB total HBM; 64 TB/s aggregate HBM3e; 72 dense FP4 PFLOPS (144 sparse); 72 sparse FP8 PFLOPS, hence 36 dense by NVIDIA's half-sparse footnote; approximately 14.3 kW maximum system power; 14.4 TB/s aggregate NVLink. | 180 GB capacity, 8 TB/s HBM, 9 pure-FP4 POP/s, 4.5 dense FP8 POP/s, 2.25 derived dense BF16 POP/s, and 1,787.5 W allocated system-power envelope per GPU-equivalent. The 9 POP/s pure-FP4 peak is retained as a source fact but is not used for DeepSeek's FP4-weight×FP8-activation experts. |
| SRC-NV-B300 | [NVIDIA DGX B300 February 2026 datasheet](https://dam-cdn.nvd.orangelogic.com/AssetLink/625w0j7hnw6f07ui7fo63211mti2v08o.pdf) and [NVIDIA DGX B300 system guide](https://docs.nvidia.com/dgx/dgxb300-user-guide/introduction-to-dgxb300.html) | Datasheet: 2.1 TB total label, 62 TB/s aggregate HBM3e, 108 dense FP4 PFLOPS (144 sparse), 72 sparse / 36 dense FP8 PFLOPS, 14.4 TB/s aggregate NVLink, and 14.5 kW busbar / 15.1 kW PSU. System guide: exact **8 × 288 GB = 2.3 TB total** population. | **288 GB** physical capacity, 7.75 TB/s HBM, 13.5 pure-FP4 POP/s, 4.5 dense FP8 POP/s, 2.25 derived dense BF16 POP/s, and 1,812.5 W busbar envelope per GPU-equivalent. The 13.5 POP/s pure-FP4 peak is not used for DeepSeek's mixed expert GEMMs. |

The checked B300 PDF identifies itself as document `4868000`, `Feb26`; its
downloaded SHA-256 was
`bf7b1cac562749d5d6f486a817130b24e13f0f3ff8a2989049aefd966f9afee0`.

Neither checked official B300 artifact states a full-FP32 throughput roof. The
configured 90 TOP/s per GPU value is therefore `assumed`, not published. The
leading-node report executes a 19.5/45/90/180-TOP/s sweep; 19.5 TOP/s is the
published A100 value used only as a deliberately low stress endpoint, not an
estimate of B300 performance.

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

Model storage dtype and matrix operand dtype are kept separate. In particular,
DeepSeek's routed weights occupy MXFP4 storage, but their GEMMs consume FP8
activations. Following the DeepSeek report, B200/B300 therefore apply the dense
FP8 roof to both `mxfp4_e2m1_x_fp8_e4m3` and `fp8_e4m3_x_fp8_e4m3`; the larger
pure-FP4 marketing peak is not a compatible roof for this workload.

## Iso-node architecture-attribution sources

The architecture-attribution study is intentionally restricted to N7 and
HBM2e-era technology. Its executable hardware file is
`configs/hardware/n7_architecture_attribution.json`; it is derived from
`configs/hardware/technology_inputs.json`, not copied from the exploratory ROM
brief.

| ID | Primary artifact | Published fact used | Simulation boundary |
|---|---|---|---|
| SRC-NV-A100 | [NVIDIA A100 product page](https://www.nvidia.com/en-us/data-center/a100/) and [NVIDIA Ampere Architecture whitepaper](https://images.nvidia.com/aem-dam/en-zz/Solutions/data-center/nvidia-ampere-architecture-whitepaper.pdf) | A100 uses TSMC N7; the 80-GB SXM part provides 2,039 GB/s HBM2e, 312 dense BF16 Tensor-Core TFLOP/s, 19.5 FP32 TFLOP/s, 600 GB/s NVLink, and 400 W TDP. The published Tensor Core formats do not include floating FP8 or FP4. | DeepSeek FP8/MXFP4/FP4 tensors are expanded offline to BF16; cluster collective efficiency and acquisition cost remain assumptions. The exact expanded bytes are generated tensor-role by tensor-role. |
| SRC-CEREBRAS-NODE | Cerebras Systems Form S-1 filed 2026-04-17, `cerebras-sx1april2026.htm` | WSE-2 was manufactured on TSMC 7 nm; WSE-3 on TSMC 5 nm. | Establishes wafer-scale fabrication by node only. It does not establish this project's ROM density, HBM integration, or inference throughput. |
| SRC-CEREBRAS-WSE2 | Cerebras WSE-2 public product disclosures | 46,225-mm² wafer-scale silicon, 850,000 cores, 40 GB on-wafer SRAM, and 20 PB/s advertised local memory bandwidth. | Used as an N7 physical-feasibility/storage-tier anchor. The proposed ROM design does not inherit WSE-2 bandwidth, compute, topology efficiency, yield, or power. |
| SRC-GC200 | [Graphcore GC200 product page](https://www.graphcore.ai/products/ipu) | TSMC 7 nm, 900 MB in-processor SRAM, 1,472 cores, and 250 FP16 TFLOP/s. Public GC200 architecture disclosures give an approximately 823-mm² die and 47.5 TB/s aggregate local-memory bandwidth. | Product values are area-scaled at fixed composition solely to create an iso-node SRAM-rich storage control. The resulting wafer is not a Graphcore product or measured Graphcore performance. |

The A100 deployment is not a lossy re-quantization. It expands the released
quantized values and scale tensors into BF16 storage ahead of service, then maps
logical FP8/MXFP4 operations to A100's native BF16 Tensor Core roof. This is the
primary compatibility case because it does not assume free just-in-time unpacking.

## Wafer-scale and leading-node anchors

| ID | Primary artifact | Published fact used | Simulation boundary |
|---|---|---|---|
| SRC-NV-BLACKWELL-NODE | [NVIDIA Blackwell architecture page](https://www.nvidia.com/en-us/data-center/technologies/blackwell-architecture/) | NVIDIA states that Blackwell products use custom TSMC 4NP. B200/B300 product specifications use HBM3e, not HBM4. | The commercial study pairs an N4-class ROM hypothesis and HBM3e with B300. It does not compare an N7 ROM wafer with Blackwell. |
| SRC-CEREBRAS-WSE3 | [Cerebras WSE-3 product page](https://www.cerebras.ai/product-chip) and *The Cerebras Wafer-Scale Architecture for Deep Learning* public architecture paper | 46,225 mm², TSMC 5 nm, over four trillion transistors, 900,000 cores, 44 GB SRAM, 21 PB/s memory bandwidth, 214 Pb/s (26.75 PB/s) fabric bandwidth, 125 advertised peak PFLOP/s, a 2-D mesh, and one-clock nearest-neighbour routing. | Node, area, SRAM, fabric, and peak compute are feasibility ceilings. The 125-PFLOP/s precision/utilization contract is not sufficiently specific to calibrate DeepSeek format roofs, so the study uses explicit bounded fractions and labels them assumed. |

## Tau scaling and vertical-integration boundary

| ID | Primary artifact | Published fact used | Simulation boundary |
|---|---|---|---|
| SRC-HUAWEI-TAU | Huawei, [*HUAWEI Presents the Tau (τ) Scaling Law*](https://www.huawei.com/en/news/2026/5/ieee-iscas-tau-scaling), ISCAS 2026 keynote release, 2026-05-25; [official Chinese release](https://www.huawei.com/cn/news/2026/5/ieee-iscas-tau-scaling) | Huawei defines Tau/韬 scaling as reducing delay at the device, circuit, chip, and system levels. It names LogicFolding, full-stack workload co-design, and UnifiedBus; says LogicFolding breaks conventional planar-layout boundaries; and projects 14 Å/1.4-nm-equivalent transistor density by 2031. | The release does not specify a physical 3-D integration method, tier count, bond pitch, vertical-link characteristics, thermal behavior, yield, or a fabricated 1.4-nm-equivalent part. Tau is an optimization framework, not a density/performance multiplier. The 2031 claim is retained as a vendor projection and is not an input to the iso-node studies. |

## ROM and compute-in-memory primary evidence

No public fabricated N7 or N4 mask-ROM macro matching this product was found.
Consequently, every target-node ROM number is a deterministic extrapolation band,
not a target-node measurement.

| ID | Artifact | Evidence class | Value used and boundary |
|---|---|---|---|
| SRC-ROM-65 | [JSSC DOI 10.1109/JSSC.2023.3326955](https://doi.org/10.1109/JSSC.2023.3326955) | fabricated silicon | 65-nm 2-Mb custom ROM-CIM, 3.984 Mb/mm². Retained as a cross-check; it is not the density anchor selected for the study. |
| SRC-ROM-28 | [JSSC DOI 10.1109/JSSC.2025.3556008](https://doi.org/10.1109/JSSC.2025.3556008) | fabricated silicon | 28-nm hybrid SRAM/ROM-CIM with 22 Mb ROM and 8.928 Mb/mm². This is the planar capacity-density anchor. Target-node cases explicitly use linear, intermediate, or ideal-area scaling and preserve the label `derived`. |
| SRC-YOLOC | [YOLoC, DAC 2022, DOI 10.1145/3489517.3530576](https://doi.org/10.1145/3489517.3530576) | circuit/architecture simulation, not fabrication | 28-nm, 1.2-Mb/0.24-mm² ROM-CIM, 5 Mb/mm², 8.9 ns, 28.8 GOPS, and 8-bit × 8-bit operands. The operation rate converts to 60 GB/s/mm² of encoded 8-bit weight service using two operations per weight. It is the bandwidth-density anchor only; whole-wafer scaling receives separate array, clock, repair, power, and communication derates. |
| SRC-3DMETRO | [3D-METRO, ASP-DAC 2025, DOI 10.1145/3658617.3697570](https://doi.org/10.1145/3658617.3697570) | architecture/evaluation, not fabrication | Transistorless 3-D-metal ROM evaluation at 165.6 Mb/mm² = 20.7 MB/mm². Used only as the leading-node aggressive density ceiling; it is never called measured silicon. |
| SRC-SRAM7-CIM | [ISSCC 2020 DOI 10.1109/ISSCC19947.2020.9062985](https://doi.org/10.1109/ISSCC19947.2020.9062985) | fabricated 7-nm SRAM-CIM macro | 372.4 GOPS and 351 TOPS/W headline macro result. Retained as a compute-in-memory plausibility cross-check, not used to assign ROM capacity or a full-wafer application roof. |

The derivation script `tools/build_iso_node_studies.py` recomputes capacity,
local read service, HBM stack totals, perimeter pitch usage, and the SRAM-rich
control. Committed study files include the input SHA-256 and all intermediate
values so a source or scaling-rule change is diffable.

## Open-PDK and physical-methodology primary evidence

The public PDK is selected for a reproducible legal-layout, DRC, LVS,
capacitance-extraction, and circuit-methodology experiment—not because its node
name predicts the proposed product. The selection and its hard claim boundary
are in `docs/OPEN_PDK_SELECTION.md`.

| ID | Primary artifact | Published fact used | Role and boundary |
|---|---|---|---|
| SRC-PDK-SKY130 | SkyWater/Google, [SKY130 open-PDK repository and status statement](https://github.com/google/skywater-pdk) | The PDK is a Google/SkyWater collaboration intended to create designs manufacturable at SkyWater; the public release is an experimental preview derived from a process used for commercially manufactured designs. The documented stack includes 1.8-V internal devices, local interconnect, and five metal levels. | Primary physical-methodology PDK. A passing public-deck experiment is not production signoff and says nothing about N7/N4 PPA or late-via mask economics. |
| SRC-PDK-IHP | IHP, [IHP Open Source PDK repository](https://github.com/IHP-GmbH/IHP-Open-PDK) | SG13G2 is a foundry-backed 0.13-µm BiCMOS process with 1.2-V thin-oxide and 3.3-V thick-oxide CMOS. The preview PDK publishes primitive/device models plus KLayout/Magic DRC, LVS, and extraction collateral and ngspice/Xyce support. | Selected independent replication after the primary SKY130 topology is stable. It is not an N7/N4 proxy. |
| SRC-PDK-IHP-LOCK | IHP, [Open PDK release `v0.3.0`](https://github.com/IHP-GmbH/IHP-Open-PDK/releases/tag/v0.3.0) and [exact source commit](https://github.com/IHP-GmbH/IHP-Open-PDK/tree/5cccb161f7492697cfa52eb14dc03beb00bdca9e) | Release `v0.3.0` was published 2026-03-11. The exact root commit, five gitlinks, all recursively tracked files, the tracked symlink, Git modes, sizes and hashes are locked by `configs/pdk/ihp_sg13g2_physical_lock.json`. | Establishes reproducible public-PDK identity only. The 5,121-entry/812,058,771-byte semantic payload is not target-node or silicon evidence. |
| SRC-PDK-IHP-OSDI | IHP, [official Verilog-A compile script](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/5cccb161f7492697cfa52eb14dc03beb00bdca9e/ihp-sg13g2/libs.tech/verilog-a/openvaf-compile-va.sh) and [ngspice flow notes](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/5cccb161f7492697cfa52eb14dc03beb00bdca9e/ihp-sg13g2/libs.tech/xschem/README.md) | The public PDK compiles `psp103`, `psp103_nqs`, `r3_cmc`, and `mosvar` for ngspice OSDI and requires ngspice 40+ built with OSDI support. | Governs the official-device prerequisite; generated modules stay outside the immutable PDK checkout. |
| SRC-PDK-OPENVAF | OpenVAF, [release 23.5.0](https://github.com/pascalkuthe/OpenVAF/releases/tag/OpenVAF-v23.5.0), [build instructions](https://github.com/pascalkuthe/OpenVAF/tree/d4079e776f4b54b23e158b7857c4e238e5cacd05), and [official binary download](https://openvaf.semimod.de/download/) | OpenVAF 23.5.0 implements the OSDI compiler path and documents LLVM 15.0.7. Its documented `--target_cpu generic` path has a one-line Clap type mismatch in this release; the exact source-only fix is stored and hashed. | The patch changes CLI String borrowing only, not model equations or compiler backend semantics. The governed compiler and each generated module are hash-recorded. |
| SRC-PDK-NGSPICE43 | ngspice, [release archive 43](https://sourceforge.net/projects/ngspice/files/ng-spice-rework/old-releases/43/) and [OSDI documentation](https://ngspice.sourceforge.io/osdi.html) | ngspice 43 can be configured with `--enable-osdi`; the exact source archive, configure flags and installed executable are locked. | Official IHP device simulation tool. A passing smoke test is not production compact-model or silicon qualification. |
| SRC-PDK-GF180 | GlobalFoundries/Google, [GF180MCU open-PDK repository](https://github.com/google/gf180mcu-pdk) | The kit targets designs manufacturable on GlobalFoundries' 0.18-µm 3.3/6-V MCU process and is explicitly an experimental preview. | Secondary older/high-voltage topology-portability check; its device regime is a weaker first analogue for the compact low-voltage read path. |
| SRC-PDK-ASAP7 | Clark et al., [*ASAP: A 7-nm FinFET Predictive Process Design Kit*](https://doi.org/10.1016/j.mejo.2016.04.006), and the [public ASAP7 repository](https://github.com/The-OpenROAD-Project/asap7) | ASAP7 identifies itself as a predictive 7-nm FinFET PDK and research cell-library environment. | Useful only for explicitly predictive digital experiments; it is not foundry manufacturing evidence for a custom ROM read path. |
| SRC-PDK-FREE45 | NC State, [FreePDK45 manual and release page](https://eda.ncsu.edu/freepdk/freepdk45/) | The manual calls the process generic, says the technology was compiled from published papers, predictive models, and rule scaling, and documents non-comprehensive research rules. Nangate45 is a standard-cell library built on this environment. | Existing digital synthesis/place-route work remains a methodology proxy, not transistor or manufacturability evidence. |
| SRC-PDK-INSTALL | FOSSi Foundation, [Ciel SKY130 release `sky130-f6eeac7…`](https://github.com/fossi-foundation/ciel-releases/releases/tag/sky130-f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7), and open_pdks [tag `1.0.605`](https://github.com/RTimothyEdwards/open_pdks/tree/1.0.605) | The enabled custom-transistor payload is generated from open_pdks commit/tag `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`. | The exact archives, SHA-256 values, 3,204-file/104,965,496-byte tree identity, and forbidden inferences are locked in `configs/pdk/sky130_physical_lock.json`. |
| SRC-PDK-TOOLS | Magic [8.3.674](https://github.com/RTimothyEdwards/magic/tree/8.3.674), Netgen [1.5.322](https://github.com/RTimothyEdwards/netgen/tree/1.5.322), and [ngspice](https://ngspice.sourceforge.io/) | Public layout, extraction, LVS, and BSIM simulation engines. | The governed physical result records and hashes the exact installed launchers/engines. Magic commit `17ac06a24a952380ade3a7d33cd2f0c3943dfc12`, Netgen peeled commit `5e48c4e8762d7b58e296b59392572633ba9b184d`, and the canonical ngspice executable are checked rather than relying on command names. |
| SRC-PDK-NGSEED | ngspice, [statistical-analysis and seed documentation](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf) and [ngspice-36 input implementation](https://sourceforge.net/p/ngspice/ngspice/ci/ngspice-36/tree/src/frontend/inp.c) | Random `.param` functions including `AGAUSS` are evaluated during input/model expansion. A netlist `.option seed=<positive integer>` is processed before that expansion and resets the generator; this is distinct from an interactive `setseed` issued before this build's later Wallace initialization. | The mismatch runner puts the seed in every generated netlist and proves control with an exact same-seed replay plus cross-seed variation. This establishes reproducibility only, not statistical correctness or silicon yield. |

## Internally generated evidence

| ID | Artifact | Class | Boundary |
|---|---|---|---|
| GEN-INVENTORY | `data/inventory/*.json` | measured from pinned public metadata | Exact encoded storage only; no model execution. |
| GEN-ANALYTICAL-LEGACY | `results/standard/analytical.json`, `sweep.csv`, `REPORT.md`, and `QWEN3_8B_ADDENDUM.md` | simulated/derived | Superseded single-midpoint exploration. Retained for provenance and control behavior; not an authoritative technology comparison. |
| GEN-ROUTING | `results/routing/*.json` | synthetic/simulated | Uniform and correlated stress routing; not production activation traces. |
| GEN-NOC | `results/noc/*` | simulated | Purpose-built topology/serialization model; not placed-and-routed timing. |
| GEN-ISO-NODE | `configs/hardware/n7_architecture_attribution.json` and `leading_node_market.json` | derived/assumed envelopes | Exact arithmetic from cited macro/product facts plus visible scaling and floorplan inputs. No target-node ROM measurement. |
| GEN-MODEL-TRAFFIC | `results/model-traffic/` | derived | Hardware-independent active-weight/KV traffic matrices for Flash, Pro, and Kimi; not a speedup prediction. |
| GEN-SENSITIVITY | `results/sensitivity/*` | simulated/derived | One-factor and bounded-grid results, not probability distributions. |
| GEN-SKY130-TOPOLOGY | `results/spice/sky130_rom_read.json` and `ROM_READ_REPORT.md` | simulated | 51/51 deterministic BSIM cases over declared PVT and synthetic bitline/load envelopes. Array rows alter a declared lumped capacitance only; this is not extracted array geometry. |
| GEN-SKY130-PHYSICAL | `results/spice/sky130_physical/physical.json`, `REPORT.md`, and hashed artifacts | open-PDK DRC/LVS/extraction | Exact installed SKY130A tree and pinned tools; zero Magic DRC errors; unique Netgen LVS match for 10 MOS devices, 15 nets, and 10 ports; one physical via1 programming delta; 59 extracted capacitance elements. The 373.75-µm² deliberately roomy test slice is not a ROM-cell density. |
| GEN-SKY130-PEX-PVT | `results/spice/sky130_extracted_pvt.json` and `SKY130_EXTRACTED_PVT_REPORT.md` | simulated from extracted public-PDK geometry | 33/33 deterministic capacitance-extracted cases over SS/TT/FF, 1.62/1.80/1.98 V, -40/25/125 °C, and 5/20/80-fF output loads. This baseline intentionally omits distributed resistance; the separate full-RC row below does not close statistical/yield sign-off, target-node correlation, or silicon. |
| GEN-SKY130-PEX-MM | `results/spice/sky130_extracted_mismatch.json` and `SKY130_EXTRACTED_MISMATCH_REPORT.md` | simulated from extracted public-PDK geometry and public per-instance mismatch equations | 256/256 fixed-seed nominal-TT local samples pass; a same-seed replay has zero parsed-measure delta; different seeds produce 256 distinct delay values. Process variation is disabled. This is finite public-model sensitivity, not silicon yield, defect coverage, statistical sign-off, compact-array behavior, or target-node evidence. |
| GEN-SKY130-PEX-RC | `results/spice/sky130_resistance/resistance.json`, `REPORT.md`, and 50 hashed primary/replay artifacts | simulated from integrated Magic detailed-resistance extraction of the archived public-PDK geometry | Five declared interconnect styles each produce ten MOS devices, 630 resistor elements, and 269 capacitor elements; all five semantic replays and 165/165 deterministic electrical cases pass. Nominal local delay is 0.0412 ns versus 0.0354 ns for capacitance-only PEX. Network subdivision changes both R and C, and this roomy local slice is not compact-array, full-array, silicon, target-node, wafer, or GPU evidence. |
| GEN-IHP-DEVICE-SMOKE | `results/spice/ihp_device_smoke/device_smoke.json`, `REPORT.md`, and nine hashed logs | compiled/simulated from the exact locked IHP SG13G2 public release | All four official Verilog-A modules compile twice byte-identically with `-D__NGSPICE__ --target_cpu generic`; official 1.2-V NMOS/PMOS TT DC and transient checks pass. This closes the independent device/toolchain prerequisite only—not IHP ROM layout, DRC, LVS, PEX, PVT, density, yield, target-node scaling, wafer behavior, or GPU performance. |
| GEN-IHP-PHYSICAL | `results/spice/ihp_sg13g2_physical/physical.json`, `REPORT.md`, and 12 hashed artifacts | independent public-PDK DRC/LVS/extraction | Exact locked IHP SG13G2 v0.3.0 and pinned tools; zero full Magic DRC errors; unique Netgen LVS for 10 MOS devices, 15 nets, and all 10 ports; six via1 shapes on the programmed side versus five on the absent side; 59 capacitance elements. The 373.75-µm² slice is deliberately roomy, not a density macro. |
| GEN-IHP-PEX-PVT | `results/spice/ihp_sg13g2_extracted_pvt.json` and `IHP_SG13G2_EXTRACTED_PVT_REPORT.md` | simulated from exact IHP PEX with official PSP103 models | 33/33 deterministic SS/TT/FF, 1.08/1.20/1.32-V, -40/27/125-°C, and 5/20/80-fF cases pass using pinned ngspice 43 and four hash-verified OSDI modules. This is local public-model behavior, not mismatch yield, target-node timing, or silicon. |
| GEN-IHP-PEX-RC | `results/spice/ihp_sg13g2_resistance/resistance.json`, `REPORT.md`, and 50 hashed primary/replay artifacts | simulated from integrated Magic detailed-resistance extraction of the archived IHP geometry | All five public IHP RC styles produce 10 MOS, 41 resistor, and 68 capacitor elements; all five semantic replays, resistor-graph programming/body-path checks, and 165/165 deterministic electrical cases pass. Nominal local delay is 0.0448 ns versus 0.0432 ns capacitance-only. Network subdivision changes both R and C; this is not compact/full-array, target-node, wafer, GPU, yield, or silicon evidence. |
| GEN-RTL-IMPL | `results/rtl/implementation_campaign.json`, `IMPLEMENTATION_REPORT.md`, `clean_baseline_replay.json`, and `CLEAN_BASELINE_REPLAY.md` | synthetic open-library synthesis/STA/equivalence/physical proxy | Clean-baseline fingerprint `87e057764094b9ed` closes 7/7 mapped cases, 2/2 generic proofs, 1/1 actual mapped proof, 2/2 physical proxies, and 2/2 post-route proofs; 386 referenced artifacts verify after archival. Nangate45 is generic methodology collateral, not target-node, ROM-macro, full-chip/wafer, manufacturing, or product-PPA evidence. |
| GEN-PRE-NDA | `results/PRE_NDA_READINESS.md` | reviewed gate record | Distinguishes completed public analytical work from model-owner, GPU-lab, foundry, OSAT, package, yield, and silicon gates. |

## Explicitly unavailable evidence

No public source currently establishes the target-node via-ROM density, full-array
read bandwidth, sense margin, yield, repair overhead, MAC density, wafer HBM
beachfront, stitched-wafer timing, power delivery, cooling, unit cost, NRE, or
production DeepSeek/Kimi router traces, exact A100/B300 application traces, or any
model's production KV traces. Those
inputs remain assumptions or
open gates. Open-PDK work can test methodology and topology but cannot promote any
of them to leading-node measured evidence.
