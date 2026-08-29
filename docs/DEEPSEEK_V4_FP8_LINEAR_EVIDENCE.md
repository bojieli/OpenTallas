# DeepSeek V4 Flash selected-row FP8-linear evidence

**Evidence date:** 2026-08-28

**Evidence status:** exact official-checkpoint differential for four selected
layer-0 query-A output rows

**Not established:** the complete query projection, attention, a transformer
block, prefill/decode, RTL correctness, manufacturability, PPA, or a comparison
with NVIDIA

## Result

This record closes the first real-checkpoint arithmetic path through the
OpenTallas compiler and software service engine:

```text
two explicit 4,096-element BF16 activation rows
  -> verified selected-row semantic IR
  -> fixed two-instruction microcode
  -> memory-mapped official E4M3 weight and E8M0 scale artifacts
  -> exact selected-row FP8 linear arithmetic
  -> persisted BF16 result and functional counters
  -> independent replay from the original locked checkpoint
```

The selected logical output rows are `0`, `127`, `128`, and `1023`. Rows 127
and 128 deliberately cross the 128-row scale-tile boundary. The service result
and independent checkpoint reference matched for all eight output elements:

| Record | Identity or result |
|---|---|
| Deployment build | `98595e348deb0e879d6ed4fe0f6875e7d31d38d5240521581c2b987bf5c876c2` |
| Canonical query-A application | `680d30d3a92898178b52acc55302252f1e7bb3ec003b36b009f5295b799da5ea` |
| Canonical query-A verification | `a1890e807e61b01ea9c555ad51695a63579f9f95e4cd5a3ec1521c6f2799f67b` |
| Deployment payload roundtrip | `a2a873b0ff14a30792efd49794786c66aef857baf84009a7e83b2606c140f2de` |
| Request SHA-256 | `63de598d132e86171ba0b7b0dbc300c5fe8010af2ee98eb7f25b298469ce3b4c` |
| Expected output SHA-256 | `e82f4e4b057e66bc0378cd6c25a973a868a48dd4cfba40434ee80521ffdf5cd9` |
| Observed output SHA-256 | `e82f4e4b057e66bc0378cd6c25a973a868a48dd4cfba40434ee80521ffdf5cd9` |
| Independent differential | `9b4cacd415df0fbd77b08c24bbb4b48b737f0b3305abfd08ba719d4302e3b800` |
| Differential status | `exact_locked_checkpoint_selected_row_differential` |
| Numeric status | zero activation saturations, zero output saturations, no poison |

The functional counters also reconciled exactly:

| Counter | Value |
|---|---:|
| Activation blocks quantized | 64 |
| Activation values quantized | 8,192 |
| Matrix block dots | 256 |
| Binary32 product accumulates | 32,768 |
| Binary32 cross-block reduction adds | 248 |
| BF16 outputs written | 8 |
| Logical input bytes read | 16,384 |
| Logical ROM bytes read | 33,024 |
| Logical output bytes written | 16 |
| Semantic operations executed | 1 |
| Micro-operations executed | 2 |
| Completion events | 1 |

These are semantic and logical-access counters. They are not cycles, physical
memory transactions, energy, utilization, stalls, or throughput.

## Immutable source identities

The source is the official `deepseek-ai/DeepSeek-V4-Flash-0731` snapshot at
revision `7872f01b1d1fe23eabc4c98b48bffcef5a386062`.

| Source record | Identity |
|---|---|
| Checkpoint lock | `30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760` |
| Tensor-content SHA-256 | `7ca2e951786c4cd46b64b437d975da3565a1692bdceeb804c09d5fe9e1503b3f` |
| Locked tensors | 72,317 |
| Locked shards | 48 |
| Locked tensor payload | 166,878,536,440 bytes |
| Complete MP=4 plan | `7b87ee6168e13cf9be7c5e812a13490b6f264bda78a96ceb2e7c02580c49b3a7` |
| Complete MP=4 application | `0f0f5177460c599059c971cbfd43e4299d6537f0cedb6055a83b77ecb52e16cb` |
| Independent complete-application verification | `b20ac53d48714c2328470b45f44b06aed11bed4c6dc7ef48f27185c5ba813f28` |

The independent complete-application verifier re-read all 77,116 canonical
assignments derived from all 72,317 locked tensors. The smaller query-A
application is a separately identified partial materialization used to avoid
copying the 166.9-GB source again for this operator slice.

The deployment carries complete, byte-identical copies of these two official
rank-replicated tensors:

| Tensor | Storage and shape | Payload bytes | SHA-256 |
|---|---|---:|---|
| `layers.0.attn.wq_a.weight` | E4M3, `[1024, 4096]` | 4,194,304 | `d8646783efb3c0bda83bcd2c64b03cb25d1677d27b0c45ffe143a4175922932c` |
| `layers.0.attn.wq_a.scale` | E8M0, `[8, 32]` | 256 | `aea19c77d256ca30999de59a811b152a2dfc82673a43877d9cd67b80578bc5e2` |

## Separation of implementations

The service engine consumes only deployment artifacts and the request. It:

1. enforces exact manifest, semantic, tensor, expectation, coverage, roundtrip,
   microcode, request, and result contracts;
2. hashes every deployment artifact before execution;
3. rejects symlinks, path escapes, reserved FP8/scale encodings, malformed BF16
   requests, and nonfinite BF16 inputs;
4. memory-maps the 4-MiB weight matrix and scale table instead of materializing
   either through `Path.read_bytes`;
5. interprets exactly one `FP8_LINEAR_SELECTED_ROWS` instruction followed by
   terminal `COMPLETE`; and
6. uses a service-engine numeric implementation that does not import the target
   reference implementation.

The runtime reopens every deployment artifact through directory-relative,
no-symlink descriptors, hashes the exact descriptors before mapping, verifies
descriptor identity and content after execution, and independently reopens the
current deployment tree before returning. It therefore rejects payload changes
after `load()`, in-place mutation, and atomic path replacement during execution,
including replacement with byte-identical content.

The independent execution checker does not import or invoke the service engine.
It revalidates the persisted deployment and result, streams and hashes every
byte of the original locked weight and scale tensors, retains only the four
selected weight rows, executes `runtime.reference.matrix` independently, and
recomputes all functional counters. Tests prove that a one-bit change in a
persisted output is rejected. They also prove that a self-consistent forged
manifest/request/result set with a recomputed build ID cannot overstate operator
coverage, because the checker independently enforces the fixed coverage,
expectation, roundtrip, microcode, source, and claim-boundary contracts.

Nine Draft 2020-12 schemas cover every JSON boundary under
`schemas/compiler/deepseek_v4_fp8_linear`. Runtime checks are stricter where
relationships such as shape products, row ordering, scale orientation, and
cross-document identities cannot be expressed locally by one schema.

## Reproduction

Large official payloads and generated evidence remain outside Git. With the
immutable local snapshot and lock present, the governed sequence is:

```bash
DSV4_SNAPSHOT=/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4-Flash-0731/snapshots/7872f01b1d1fe23eabc4c98b48bffcef5a386062
DSV4_EVIDENCE=/home/ubuntu/.cache/opentallas/deepseek-v4-flash-0731

python3 -m compiler.cli compile-deepseek-v4-fp8-linear-slice \
  --snapshot "$DSV4_SNAPSHOT" \
  --lock "$DSV4_EVIDENCE/checkpoint.lock.json" \
  --application "$DSV4_EVIDENCE/fp8-linear-canonical" \
  --output "$DSV4_EVIDENCE/fp8-linear-deployment"

python3 -m runtime.service_engine \
  --deployment "$DSV4_EVIDENCE/fp8-linear-deployment" \
  --inputs "$DSV4_EVIDENCE/fp8-linear-request.json" \
  --output "$DSV4_EVIDENCE/fp8-linear-result.json"

python3 -m compiler.cli verify-deepseek-v4-fp8-linear-execution \
  --snapshot "$DSV4_SNAPSHOT" \
  --lock "$DSV4_EVIDENCE/checkpoint.lock.json" \
  --deployment "$DSV4_EVIDENCE/fp8-linear-deployment" \
  --request "$DSV4_EVIDENCE/fp8-linear-request.json" \
  --result "$DSV4_EVIDENCE/fp8-linear-result.json" \
  --output "$DSV4_EVIDENCE/fp8-linear-differential.json"
```

The request has two explicit deterministic finite-BF16 rows. The first is a
signed repeating finite-value pattern with periodic zeros. The second repeats
positive/negative zero, minimum subnormal, and moderate finite boundary values.
No expected output is embedded in the request.

## Claim boundary and next gate

This evidence proves that one compiled artifact path can load official query-A
weight and scale bytes, execute the frozen selected-row FP8 arithmetic contract,
and match an independent replay from the original checkpoint exactly.

It does **not** prove:

- the layer-0 RMS-normalized activation that would feed query-A in the complete
  model;
- the other 1,020 query-A outputs or the complete projection operator;
- query-B, key/value projections, rotary position encoding, attention, routing,
  experts, residual state, logits, token generation, or text decoding;
- complete DeepSeek V4 Flash prefill or decode;
- correct HBM/SRAM scheduling, transactional state, generated RTL, or physical
  timing; or
- any throughput, area, energy, manufacturability, or NVIDIA-relative result.

The next arithmetic gate is a complete operator execution with bounded streamed
output persistence, followed by composition with the qualified normalization
and attention dependencies. Full-model validation remains blocked until every
ordinary-path operator, state transition, and compiler schedule has the same
artifact-only execution and independent differential discipline.
