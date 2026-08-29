# DeepSeek V4 compressor reference evidence

**Evidence status:** operator-level target semantics, exact released APE payload,
and bounded unmodified-method differential

**Official source:** `deepseek-ai/DeepSeek-V4-Flash-0731` revision
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`

**Model source SHA-256:**
`c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f`

**Graph contract:**
`8357b3d82b443750c7849047997048438325a078cb9a8284408eb6ea2c05f27a`

## What is qualified

The independent references define the complete compressor boundary after the
already-qualified learned projections:

- `runtime/reference/compression_state.py` defines FP32 APE addition, raw
  incomplete-state update, ratio-four overlap assembly, ratio-128 grouping,
  the pool predicate, fresh-session reset, exact decode cursor, and monotonic
  per-lane version;
- `runtime/reference/compression_pool.py` defines deterministic FP32 stable
  softmax and weighted pooling;
- `runtime/reference/conversion.py` defines the official post-pool
  `kv.to(dtype)` FP32-to-BF16 boundary; and
- `runtime/reference/compressed_kv.py` defines session-bound BF16
  complete-prefix commit, causal cursor/version transitions, lane retirement,
  and a view that exposes only the exact active sessions' valid prefixes after
  normalization, position transformation, and activation QDQ.

The official graph has 21 main ratio-four, 21 indexer ratio-four, and 20 main
ratio-128 sites. It now contains 62 each of `COMPRESS_PROJECT`,
`COMPRESS_STATE_UPDATE`, `COMPRESS_POOL`, `BINARY32_TO_BF16`, and
`COMPRESS_KV_WRITE`, and `COMPRESSED_KV_VALID_VIEW`. Main and indexer raw state
and compressed caches use different namespaces. Learned index scoring consumes
only a validated committed index prefix; sparse attention consumes only a
validated committed main prefix through the still-pending complete attention-KV
view.

## Official source behavior and target adaptations

The released compressor projections retain FP32 KV and gate scores, and APE is
FP32. Ratio four projects `2D` values per token and pools eight `D`-wide rows:
the previous group's first feature half followed by the current group's second
half. The first group has four positive-zero KV rows and four
negative-infinity-score rows. Ratio 128 pools an ordinary non-overlapping group.

Prefill exposes only complete groups and retains the incomplete suffix. Decode
updates raw state on every token but emits a pool result only at a ratio
boundary. The source may add APE independently for pool operands and retained
state, so the logical counters do not assume those operations were shared. The
official method converts the pooled FP32 result to BF16 before RMSNorm and writes
compressed KV only after normalization, position transformation, and FP8/FP4
QDQ.

Three target adaptations are explicit:

1. Pool arithmetic uses finite binary32 maximum, correctly rounded binary32
   exponential, NUM-6.1 balanced sums, binary32 RNE division/multiplication,
   preserved subnormals, and positive-zero canonicalization. PyTorch does not
   make one backend reduction tree or exponential approximation architectural.
2. Raw compressor state carries canonical session identity, exact next position,
   and monotonic version. Fresh prefill resets every active raw slot before
   applying rows; stale-session, skipped, or replayed decode is rejected. The
   released `Compressor.forward` itself overwrites only addressed rows and
   trusts its caller for this causality.
3. Compressed KV binds its contiguous prefix to active sessions, cursor, lane
   status, and monotonic versions. Retired lanes keep their last identity as a
   tombstone until reassignment, and a separate valid-view operation never
   exposes payload beyond the authoritative prefix. The released PyTorch object
   has payload storage but no equivalent causal metadata.

Every reference validates the complete input and prior state before constructing
and committing a new immutable result. Malformed shapes, nonfinite public values,
illegal positions, prefix mismatches, or intermediate overflow fail closed.

## Exact APE checkpoint payload

The audit byte-range fetched all compressor APE tensors through the pinned
safetensors index and headers. All values are finite FP32.

| Shape | Tensors | Bytes | SHA-256 |
|---|---:|---:|---|
| `[4,256]` | 21 | 86,016 | `fed11b86399a41f1e89255f993a17aa7f889e7d69ffcb3f7175211f7c3336dfd` |
| `[4,1024]` | 21 | 344,064 | `0005f188b47d4183093f7c20b8a351462a3eaaef6b4e2c562924baf3d2a3a65e` |
| `[128,512]` | 20 | 5,242,880 | `73c7f7030dd68cd8715571272915b1ae11253fe08fd63ae41043b988df60a4aa` |
| **Total** | **62** | **5,672,960** | `ad6333d91c83b72c3fc426ea712b91446ef4020eac1dc39a299d9e56ab288ea4` |

The 1,418,240 values contain 799,732 negative, 618,508 positive, and no exact
zeros. The minimum is `-3.3454201221466064` (`0xc0561b5d`) in
`layers.2.attn.indexer.compressor.ape`; the maximum is `1.1580443382263184`
(`0x3f943acc`) in `layers.8.attn.indexer.compressor.ape`.

## Exact source-method lock

The deterministic report retains hashes of the exact official slices it
executes:

| Source slice | Inclusive lines | Bytes | SHA-256 |
|---|---:|---:|---|
| `Compressor` | 285–383 | 5,484 | `7d1cc51b4e19ccd10d083d00a57b4fd3e219d65ab17cd72febe328c2c7fb9ef5` |
| `Compressor.overlap_transform` | 313–320 | 387 | `6b956922a6c32d1c3986e20730a69a81326c5b904e70cd6abf7a6da2775088cd` |
| `Compressor.forward` | 322–383 | 3,241 | `892ce7ca46af7a150a7370253743c33602bb63edd3736960a700756ac38c8bac` |

## Unmodified official-method differential

The audit loads and executes the unmodified official `Compressor.forward` and
`overlap_transform`. Projection, normalization capture, RoPE, and QDQ test
doubles isolate the APE/overlap/pool/BF16-conversion path; they do not replace
the official operations under comparison.

This differential has a deliberately narrower scope than the reference
contracts above. It establishes the official APE identities and bounded
ratio-four prefill APE/overlap/pool/BF16 behavior. It does not independently
differential-test session-safe raw decode traces, compressed-cache address or
validity traces, cursor/session transitions, lane retirement, or tombstones.
Those state/cache behaviors are source-derived accelerator contracts with
adversarial unit tests, not claims supported by this official-method audit.

The governed environment was Python 3.10.12, PyTorch 2.10.0+cu128, CUDA 12.8,
NVIDIA driver 595.71.05, and an RTX PRO 6000 Blackwell Workstation Edition at
SM120.

| Corpus | Target output | CPU | SM120 |
|---|---|---:|---:|
| APE-cancelled exact | `539d6235e9e75c4e4dd051b1dec413a5e21ea4b7670f22f7431141039ba9bcef` | 0 / 1,024 differences | 0 / 1,024 differences |
| broad exact eighths, seed `0x434f4d504e415449` | `545368262c0155f705ba9c5c691df299f5d3de15c0f49ea6da01a175f2294bb9` | 1 / 1,024 | 1 / 1,024 |

Both broad-corpus devices produced official `0x3d08` versus target `0x3d09` at
flat index 672, a one-code same-sign difference. This bounded result is
consistent with the declared deterministic-target versus backend-arithmetic
boundary. It is retained rather than used to infer universal backend
equivalence.

The deterministic report is
`results/model-execution/deepseek-v4-compressor-audit.json`, SHA-256
`d14c2b33d9cfc105af9ba3dc18c4ac3b749a203bd0a6b0d3f1d8592315651324`.

## Logical traffic boundary

The references count source projection values, APE values and additions, raw
state reads/writes, resets, causal metadata records, overlap fill, state rolls,
pool operands and arithmetic, FP32-to-BF16 reads/writes, compressed BF16 payload
reads/writes, preserved rows, valid-prefix fields, session/cursor/version fields,
and excluded capacity rows separately. These are logical source/operator counts. They are
not HBM bursts, SRAM transactions, NoC packets, cache behavior, cycles, achieved
bandwidth, latency, energy, area, or PPA.

This matters to the ROM thesis: immutable checkpoint weights can be placed in a
read-only tier, while raw compressor state and compressed KV are mutable and
must use writable storage. A future comparison must combine these exact logical
streams with an executable placement and schedule. It cannot turn their sum
directly into inference bytes per second.

## Reproduction

The governed driver is `tools/audit_deepseek_v4_compressor.py`. With the pinned
source, index metadata, headers, PyTorch/CUDA stack, and checkpoint access:

```bash
python tools/audit_deepseek_v4_compressor.py \
  --model /path/to/pinned/inference/model.py \
  --index /path/to/model.safetensors.index.json \
  --header-dir /path/to/pinned/safetensors-headers \
  --output /tmp/deepseek-v4-compressor-audit.json
```

The driver rejects source, index, tensor-profile, payload, environment,
differential, or report-hash drift. The expected output-file SHA-256 is
`d14c2b33d9cfc105af9ba3dc18c4ac3b749a203bd0a6b0d3f1d8592315651324`.

## Claim boundary

The independent references establish deterministic compressor target semantics,
immutable causal raw-state and compressed-cache contracts, and stale-capacity
exclusion. The official-method audit separately establishes exact official APE
identity and range plus bounded ratio-four prefill pool/BF16 behavior under one
declared development stack. It does not extend that differential evidence to
the state/cache transactions, and it does not establish:

- checkpoint-derived compressor projection activations or a complete layer;
- session-controller or service-engine execution of the transactions;
- generated microcode, a certified schedule, or RTL conformance;
- cycles, physical bandwidth, storage placement, energy, area, or PPA;
- complete-model prefill/decode correctness; or
- OpenTallas throughput or superiority over any GPU.

Those remain later M4–M9 gates in the executable-system recovery plan.
