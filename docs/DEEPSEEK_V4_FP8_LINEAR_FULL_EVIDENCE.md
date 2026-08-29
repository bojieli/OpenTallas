# DeepSeek V4 Flash complete-output FP8-linear evidence

**Evidence date:** 2026-08-29

**Evidence status:** exact official-checkpoint differential for all 1,024
layer-0 query-A FP8-linear outputs for one explicit finite-BF16 input row

**Not established:** the checkpoint-derived layer-0 activation, HC_PRE,
normalization composition, attention, a transformer block, prefill/decode, RTL,
physical implementation, PPA, manufacturability, or an NVIDIA comparison

## Result

This record closes one complete arithmetic operator through the OpenTallas
compiler and software service engine:

```text
one explicit 4,096-element BF16 validation row
  -> complete FP8_LINEAR semantic IR
  -> fixed microcode with exhaustive logical rows 0..1023
  -> memory-mapped official E4M3 weight and E8M0 scale artifacts
  -> all 1,024 BF16 query-A outputs
  -> persisted result and exact functional counters
  -> independent dense replay from the original locked checkpoint
```

The request contains no expected output. The service engine consumes only the
generated deployment and request. The independent checker does not import the
service engine and uses the complete `dense_fp8_linear_bf16` reference, not the
selected-row projection helper.

| Record | Identity or result |
|---|---|
| Deployment build | `45ed6eadfb5516aa808cb3740c4db3f0b7cc0c02ca8f7664ce4cc511a72fc714` |
| Canonical query-A application | `680d30d3a92898178b52acc55302252f1e7bb3ec003b36b009f5295b799da5ea` |
| Canonical query-A verification | `a1890e807e61b01ea9c555ad51695a63579f9f95e4cd5a3ec1521c6f2799f67b` |
| Request file SHA-256 | `fb757d39e213ad4461da66a716371ccbf7130b009edd08c61ae829dd4d0aa23e` |
| Expected output SHA-256 | `f3ab906e293b5130cef680dd153120fa404c185458ce896b1a1c2d8927dfc9db` |
| Observed output SHA-256 | `f3ab906e293b5130cef680dd153120fa404c185458ce896b1a1c2d8927dfc9db` |
| Independent differential | `f8d95b84c683b9772755b6146da0af84955987e19e0ea05fe4a5ad05c7f0c499` |
| Differential status | `exact_locked_checkpoint_complete_fp8_linear_differential` |
| Numeric status | zero activation saturations, zero output saturations, no poison |

The generated evidence files are deliberately outside Git. Their retained file
hashes are:

| File | SHA-256 |
|---|---|
| `deployment_manifest.json` | `760d1bb56c5d99bad5df9bdeb0321a7ece0effcd4a8c2e7a36c33cefc4dd5e97` |
| `fp8-linear-full-result.json` | `1abe8c7f8a1236b6c3e4549c4c384b518be508e2c27260f5b98a3597a0f96503` |
| `fp8-linear-full-differential.json` | `dd56f2a8009c09e670802ad9e57fb7e21d491941d82af136ccb51eb4aebd92c0` |

## Functional accounting

The exact counters for the one-row execution are:

| Counter | Value |
|---|---:|
| Activation blocks quantized | 32 |
| Activation values quantized | 4,096 |
| Matrix block dots | 32,768 |
| Binary32 product accumulates | 4,194,304 |
| Binary32 cross-block reduction adds | 31,744 |
| BF16 outputs written | 1,024 |
| Logical input bytes read | 8,192 |
| Logical ROM bytes read | 4,227,072 |
| Logical output bytes written | 2,048 |
| Semantic operations executed | 1 |
| Micro-operations executed | 2 |
| Completion events | 1 |

These are semantic-operation and logical-byte counters. They are not hardware
cycles, physical memory transactions, NoC traffic, utilization, stalls, energy,
area, or throughput.

## Immutable official source

The source is `deepseek-ai/DeepSeek-V4-Flash-0731` at revision
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`.

| Source record | Identity |
|---|---|
| Checkpoint lock | `30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760` |
| Tensor-content SHA-256 | `7ca2e951786c4cd46b64b437d975da3565a1692bdceeb804c09d5fe9e1503b3f` |
| Locked tensors | 72,317 |
| Locked shards | 48 |
| Locked tensor payload | 166,878,536,440 bytes |
| Complete canonical application | `0f0f5177460c599059c971cbfd43e4299d6537f0cedb6055a83b77ecb52e16cb` |
| Independent complete-application verification | `b20ac53d48714c2328470b45f44b06aed11bed4c6dc7ef48f27185c5ba813f28` |

This deployment carries byte-identical copies of:

| Tensor | Storage and shape | Payload bytes | SHA-256 |
|---|---|---:|---|
| `layers.0.attn.wq_a.weight` | E4M3 `[1024, 4096]` | 4,194,304 | `d8646783efb3c0bda83bcd2c64b03cb25d1677d27b0c45ffe143a4175922932c` |
| `layers.0.attn.wq_a.scale` | E8M0 `[8, 32]` | 256 | `aea19c77d256ca30999de59a811b152a2dfc82673a43877d9cd67b80578bc5e2` |

The compiler and checker pin both the complete official checkpoint lock ID and
the tensor-content digest. Repository and revision strings alone cannot create
official evidence.

## Artifact and checker hardening

The complete-output profile is distinct from the retained selected-row v1
profile. It has separate deployment, semantic, tensor, coverage, result, and
differential schemas. All object schemas are recursively closed.

The service and independent checker enforce:

- exhaustive little-endian U32 logical row selection `0..output_features-1`;
- complete-output dimensions and exact weight/scale orientation;
- bounded weight payload, exact-arithmetic work, request JSON, and result JSON;
- reserved-code and nonfinite-input rejection;
- content-addressed artifacts and fixed microcode;
- no-follow, directory-relative descriptors and inode/metadata fingerprints;
- exact descriptor hashing before and after execution/checking;
- rejection of in-place mutation and atomic replacement, including
  byte-identical replacement;
- exact result shape, row identity, counters, saturation status, and source
  tensor hashes; and
- rejection of self-consistent manifests that overstate transformer coverage.

The retained selected-row deployment was independently rebuilt after this
change. Its build remains
`98595e348deb0e879d6ed4fe0f6875e7d31d38d5240521581c2b987bf5c876c2`;
all 11 deployment files and the persisted service result are byte-identical.

## Reproduction

```bash
DSV4_SNAPSHOT=/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4-Flash-0731/snapshots/7872f01b1d1fe23eabc4c98b48bffcef5a386062
DSV4_EVIDENCE=/home/ubuntu/.cache/opentallas/deepseek-v4-flash-0731

python3 -m compiler.cli compile-deepseek-v4-fp8-linear \
  --snapshot "$DSV4_SNAPSHOT" \
  --lock "$DSV4_EVIDENCE/checkpoint.lock.json" \
  --application "$DSV4_EVIDENCE/fp8-linear-canonical" \
  --output "$DSV4_EVIDENCE/fp8-linear-full-deployment"

python3 -m runtime.service_engine \
  --deployment "$DSV4_EVIDENCE/fp8-linear-full-deployment" \
  --inputs "$DSV4_EVIDENCE/fp8-linear-full-request.json" \
  --output "$DSV4_EVIDENCE/fp8-linear-full-result.json"

python3 -m compiler.cli verify-deepseek-v4-fp8-linear-execution \
  --snapshot "$DSV4_SNAPSHOT" \
  --lock "$DSV4_EVIDENCE/checkpoint.lock.json" \
  --deployment "$DSV4_EVIDENCE/fp8-linear-full-deployment" \
  --request "$DSV4_EVIDENCE/fp8-linear-full-request.json" \
  --result "$DSV4_EVIDENCE/fp8-linear-full-result.json" \
  --output "$DSV4_EVIDENCE/fp8-linear-full-differential.json"
```

Outputs are create-once. Reproduction into an existing evidence path must use a
new directory or first preserve and deliberately retire the prior generated
record.

## Claim boundary and next dependency

This evidence proves complete arithmetic for one official layer-0 query-A
projection when supplied a valid BF16 input row. The validation row is explicit
and deterministic, but it is not the checkpoint-derived activation that the
real model supplies.

The actual layer-0 dependency chain is:

```text
TOKEN_EMBED
  -> HC_EXPAND
  -> layer-0 HC_PRE
  -> weighted RMS_NORM
  -> complete query-A FP8_LINEAR
```

A direct embedding-to-normalization composition would skip learned HC mixing
and is not valid DeepSeek V4 execution. HC_PRE target-precision semantics,
artifact lowering, and independent differential must therefore close before
this operator can participate in a real checkpoint-derived transformer path.
