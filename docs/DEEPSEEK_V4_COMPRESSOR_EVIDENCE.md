# DeepSeek V4 compressor reference evidence

**Evidence status:** operator-level target semantics, exact released APE payload,
bounded unmodified-method differential, and one generated full-width controlled
post-projection transactional known answer

**Official source:** `deepseek-ai/DeepSeek-V4-Flash-0731` revision
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`

**Model source SHA-256:**
`c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f`

**Graph contract at evidence capture (before later reference qualifications):**
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

## Generated post-projection executable slice

The first stateful artifact-driven slice packages the complete official layer-2
main-compressor APE and executes this declared boundary:

```text
caller-supplied finite FP32 wkv/wgate projection results
  -> causal ratio-four raw-state prepare/update
  -> conditional deterministic FP32 pool
  -> conditional FP32-to-BF16 conversion
  -> transactional compressed-cache harness commit
  -> session-bound valid-prefix view
  -> atomic immutable successor-state/result publication
```

The deployment is generated, content-addressed, independently checked without
importing its builder, and consumed as artifacts by the service engine. Its six
fixed semantic micro-ops have an independently reconstructed logical schedule
and certificate. A schedule slot records only causality and order; it is not a
cycle or physical pipeline stage.

| Record | Identity or result |
|---|---|
| Complete canonical checkpoint application | `0f0f5177460c599059c971cbfd43e4299d6537f0cedb6055a83b77ecb52e16cb` |
| Independent canonical verification | `b20ac53d48714c2328470b45f44b06aed11bed4c6dc7ef48f27185c5ba813f28` |
| Packaged tensor | `layers.2.attn.compressor.ape`, F32 `[4,1024]`, 16,384 bytes |
| Packaged APE SHA-256 | `f93afef4a88371262663f89f026a48b79f7187bd9d6498742c1db2860ae73554` |
| Deployment build | `6c92812e400d49627e2a735c1be0bb6e0d9364605f0547145885c34845791e9c` |
| Program SHA-256 | `7fba505367f95ce4c39155678fe299999e13445813781c8b0e45ba1e6525a1fc` |
| Logical schedule SHA-256 | `5fe1e1e91b87458ef7c19a08b7248d6fb2a5b6f29afd084c682a7c1568e364b2` |
| Known-answer record SHA-256 | `89920f941c0a2938fef9cfe15254bf2ce58341a8712a0a6ce5173b7cfdcdb80c` |
| Initial state ID | `4af26c08a44ab99361023a8e64b6bbd24432d4ebc9c7bf2e5bfc59a6005f388c` |
| Request ID | `0f6642770d4a5f94a2e5c9a466e637181e5f8f5f19957c7453f91af321d525b8` |
| Transition ID | `0bda0c6444ddae1be750a4f6ad754d1bdd32f2f204be8b9a6db0ad879717bb7d` |
| Successor state ID | `73475bf9a4c2d88ff8315cc01261a8154fe91a044bdb089faf67621e73a9602e` |
| Machine-readable report SHA-256 | `bc051b0184a668fc84a8e9802d613d785cdd81fe2779325843a9dfe984ac71f8` |

The known answer uses one active lane and four official-width projected rows.
Each score code is the bitwise sign-negation of the packaged APE, so every
post-addition finite score is exact positive zero. The four current KV halves
are exact binary32 constants 1, 2, 3, and 4. The eight-lane overlap group
therefore contains four excluded padding rows and four equally weighted finite
rows, producing all 512 outputs as exact binary32 `2.5` (`0x40200000`). The
conversion and valid view contain all 512 values as exact BF16 `2.5`
(`0x4020`).

This deliberately controlled APE-cancellation stimulus is not a
checkpoint-derived activation. The package is eligible as evidence of the exact
checkpoint APE identity and of the declared operator-harness transaction only;
it is explicitly ineligible as model-execution evidence.

| Output | Bytes | SHA-256 |
|---|---:|---|
| Pooled F32 `[1,1,512]` | 2,048 | `82e6cd231578fb0cf94081d02aea9c4532abcf21233eb80887ac2f041d12c019` |
| Converted BF16 `[1,1,512]` | 1,024 | `da38a9ffc905c62b3f92ca9d3addabd2616e113c9a19434633651cc9820d09c7` |
| Valid-prefix BF16 `[1,1,1,512]` | 1,024 | `da38a9ffc905c62b3f92ca9d3addabd2616e113c9a19434633651cc9820d09c7` |

The exact logical accounting includes 8,192 APE reads/additions at the raw
prepare boundary, 4,096 KV and 4,096 score pool operands, 2,048 finite
exponentials, 512 pooled F32 writes, 512 BF16 conversions, one 512-value
compressed-cache row write, and one 512-value valid-prefix row read. The
governed JSON retains every reference counter rather than only these selected
figures.

State authority is entirely artifact-based. Every version hashes the raw
payload, compressed payload, session IDs, active flags, cursors, valid-prefix
lengths, versions, prior-state ID, and transition ID. A fresh engine can resume
from the published successor without hidden process state. Downstream poison,
replay, skipped position, stale session identity, retired-lane reactivation,
payload mutation, and create-once collisions fail without mutating the supplied
prior state or publishing a partial result. The whole successor state and
result share one atomic create-once tree.

Two boundaries must not be elided:

- learned `wkv` and `wgate` projections are request inputs, so this is not a
  checkpoint-derived activation or complete compressor invocation; and
- the service commits the immediate BF16 conversion as a **transactional
  harness payload**. Official compressor RMS normalization, rotary embedding,
  and activation QDQ between conversion and attention-cache write are not in
  this slice. Its output must not be represented as the final official
  attention KV value.

The machine-readable record is
`results/model-execution/deepseek-v4-compressor-executable.json`. It contains no
time measurement or inferred performance field.

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

The generated executable slice has a separate offline reproduction path from
the complete canonical application:

```bash
python tools/audit_deepseek_v4_compressor_executable.py \
  --ape "$HOME"/.cache/opentallas/deepseek-v4-flash-0731/canonical-mp4/ranks/rank-000/layers.2.attn.compressor.ape.bin \
  --output /tmp/deepseek-v4-compressor-executable.json
```

It rejects APE, deployment, program, schedule, known-answer, output, state-chain,
counter, or final-report drift. Its expected report SHA-256 is
`bc051b0184a668fc84a8e9802d613d785cdd81fe2779325843a9dfe984ac71f8`.
Ordinary CI builds a full-size synthetic APE through the same package, checker,
state, request, service, and result path. The real-cache test is an optional
gate and becomes active only when the official canonical payload is present.

## Claim boundary

The independent references establish deterministic compressor target semantics,
immutable causal raw-state and compressed-cache contracts, and stale-capacity
exclusion. The official-method audit separately establishes exact official APE
identity and range plus bounded ratio-four prefill pool/BF16 behavior under one
declared development stack. The generated service slice establishes artifact-only
execution of its explicitly narrower controlled post-projection transactional
harness. It
does not extend the official-method differential to state/cache transactions,
and it does not establish:

- checkpoint-derived compressor projection activations or a complete layer;
- official RMSNorm, RoPE, QDQ, or final attention-cache values in the executable
  slice;
- a physical certified schedule or RTL conformance;
- cycles, physical bandwidth, storage placement, energy, area, or PPA;
- complete-model prefill/decode correctness; or
- OpenTallas throughput or superiority over any GPU.

Those remain later M4–M9 gates in the executable-system recovery plan.
