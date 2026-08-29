# DeepSeek V4 grouped-output reference evidence

- **Evidence date:** 2026-08-29
- **Qualified boundary:** target-precision `GROUPED_OUTPUT_PROJECT` reference semantics
- **Official model:** `deepseek-ai/DeepSeek-V4-Flash-0731`
- **Official revision:** `7872f01b1d1fe23eabc4c98b48bffcef5a386062`
- **Reference profile:** `opentallas.deepseek_v4_grouped_output_bf16.v1`
- **Independent service profile:** `opentallas.deepseek_v4_grouped_output_service_bf16.v1`
- **Graph contract:** `14ca0f60959ef3674f25691e409b269bb18c3d956b37407e1dfda8ef2d33f08c`

## Qualified operator boundary

The reference implements the 43 main-model and three DSpark grouped
attention-output sites after sparse attention and inverse RoPE. It covers the
official group reshape, the BF16 `wo_a` contraction, and the group-major
flattened alias consumed by `wo_b`. It does not include inverse RoPE, raw
FP8/E8M0 checkpoint conversion, `wo_b`, or a tensor-parallel collective.

The released global shape is eight groups, eight contiguous attention heads per
group, head dimension 512, reduction width 4,096, output rank 1,024 per group,
and canonical weight shape `[8192,4096]`. World sizes 1, 2, 4, and 8 own
contiguous intervals of 8, 4, 2, and 1 groups per rank. Every dot begins at
binary32 positive zero, accumulates exact BF16 products with one binary32 RNE
fused-product-add in increasing flattened feature order, and converts once to
BF16 RNE. The grouped and flattened outputs are two views of the same semantic
result.

Public reference records now use slots and deeply immutable exact tuples. Their
constructors reject subclass authority and reconcile the numeric profile,
tensor-parallel ownership, selected-rank coverage, grouped/flattened alias,
dimensions, finite BF16 payload, saturation bounds, and every derivable logical
counter. They cannot authenticate the omitted activation and learned-weight
inputs and therefore are not checkpoint-result attestations.

## Source and checkpoint authority

The independent evidence checker re-reads the following pinned files:

| Official file | SHA-256 |
|---|---|
| `inference/model.py` | `c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f` |
| `inference/convert.py` | `6efe65ebc66b18c9f2656816608f941cacfe20da79c2dee19040ecbee8b42bfe` |
| `inference/config.json` | `c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71` |
| `model.safetensors.index.json` | `98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b` |
| checkpoint lock | `3ea51c39bf788d3ec86b628d050b6d0a82539d85c0672634e7381bf287b9424b` |

The checker also verifies the exact official source operation sequence, raw
layer-0 `wo_a` FP8 and E8M0 payload identities, the canonical transformation,
and its independently replayed full-payload verification. Governing identities
are:

| Artifact | Identity |
|---|---|
| Checkpoint lock | `30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760` |
| Canonical application | `0f0f5177460c599059c971cbfd43e4299d6537f0cedb6055a83b77ecb52e16cb` |
| Independent verification | `b20ac53d48714c2328470b45f44b06aed11bed4c6dc7ef48f27185c5ba813f28` |
| Source contract | `f0220c70a30456e76276add36821ca7fff12c3944b2d202c2b0118ffdcd29bd9` |
| Official-evidence certificate | `57d86552d860aadc779bcfc69a2bffe4fbfdb1908159054661646e1192e02838` |

The four independently verified MP=4 canonical BF16 assignments are each
16,777,216 bytes:

| MP rank | Canonical `wo_a` SHA-256 |
|---:|---|
| 0 | `eefc9e67cf4cffd43050c96006bdafd37802cf3059678808f0fae2920bf9cf7b` |
| 1 | `ab08dafc884593f7b4526c3ad7a74c551ca7eece7414cce2432db782f4c7e016` |
| 2 | `d9abb5935224997d525ad2889e1082e056515aababfea32492476d7ec26476fc` |
| 3 | `0bee532ef7196984f664e07e9442adbe073ba34f8fdd5f6afb4b9974503f446b` |

Those four resources are independently resegmented and hash-checked into all
15 legal `(world_size, rank)` local mappings. This is content and topology
evidence, not an activation execution.

## Independent numeric differential

The production reference uses exact rational BF16 decoding and the governed
binary32 primitives. The separate service lane has no reference, compiler,
checkpoint, or expected-output dependency; it implements its own BF16 decode,
binary32 fused-product-add, and BF16 conversion path.

The locked differential reads the real four canonical layer-0 weight payloads
and evaluates selected output ranks 0 and 1,023 at the complete 4,096-value
reduction width. It covers every one of the 15 legal tensor-parallel mappings at
one token and MP=4 rank zero at `T=1,2,3,4`. The lanes match exactly on:

- global-group ownership and selected-rank coverage;
- grouped and flattened BF16 payloads;
- finite-saturation count; and
- every corresponding source-derived logical counter.

The aggregate identity over 18 records, four canonical assignment hashes,
synthetic input hashes, selected-weight hashes, output hashes, and both counter
maps is:

```text
7966492eeeed82bfd9b8cc7555bef3c31f3c4ec65079e235379ddc957906aaed
```

The activation corpus is deterministic synthetic data with values distributed
across head and feature boundaries. It is not a checkpoint-derived
sparse-attention output. The selected-row differential is not complete
1,024-row execution. Separate service tests execute all 1,024 rows at official
dimensions with controlled nonzero data, but do not give that controlled input
official activation provenance.

Randomized small-shape tests compare the reference with a separately assembled
exact scalar oracle. Reduction-order, head/group orientation, TP partition,
BF16 tie, subnormal, signed-zero, finite-saturation, overflow, poison, atomicity,
and input-mutation cases are explicit. Native PyTorch CPU/CUDA `einsum` tests
are bounded development observations; backend tensor-core association is not
the target rule.

## Logical program evidence

The exact grouped-output wire program is two instructions:
`GROUPED_OUTPUT_PROJECT; COMPLETE`. It binds one authenticated local canonical
weight resource and produces grouped and flattened alias registers. All 15
topology/rank programs have frozen byte hashes, contracts, deterministic logical
schedules, and fresh certificates from a checker that imports neither the
schedule builder nor runtime arithmetic.

These schedules contain instruction ordinals, register causality, aliases, and
resource ordering only. A slot is not a cycle or a physical pipeline stage.

## Reproduction

```bash
export OPENTALLAS_DEEPSEEK_V4_EVIDENCE_ROOT=/path/to/deepseek-v4-flash-0731
export OPENTALLAS_DEEPSEEK_V4_SNAPSHOT=/path/to/pinned/huggingface/snapshot
python -m pytest -q \
  tests/runtime/test_deepseek_v4_grouped_output.py \
  tests/runtime/test_deepseek_v4_grouped_output_differential.py \
  tests/runtime/test_deepseek_v4_grouped_output_service_numeric.py \
  tests/compiler/test_deepseek_v4_grouped_output_schedule.py
```

Without the external cache, official payload/source cases skip. The
redistributable deterministic arithmetic, mutation, contract, and logical
schedule cases remain runnable.

## Explicit nonclaims

This qualification does not establish a checkpoint-derived activation or
complete grouped output, inverse RoPE, raw checkpoint conversion inside the
operator, downstream `wo_b`, tensor-parallel collective, complete attention or
transformer block, artifact-driven service execution, RTL, physical placement,
physical scheduling, cycles, bandwidth, latency, throughput, energy, area,
PPA, manufacturability, complete-model decode, task quality, or GPU advantage.
Logical counters are functional accounting only.
