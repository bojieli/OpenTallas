# DeepSeek V4 DSpark main-projection reference evidence

- **Evidence date:** 2026-08-29
- **Qualified boundary:** target-precision `DSPARK_MAIN_PROJECT` reference semantics
- **Official model:** `deepseek-ai/DeepSeek-V4-Flash-0731`
- **Official revision:** `7872f01b1d1fe23eabc4c98b48bffcef5a386062`
- **Reference profile:** `opentallas.deepseek_v4_dspark_main_project_bf16.v1`
- **Independent service profile:** `opentallas.deepseek_v4_dspark_main_project_service.v1`
- **Graph contract:** `60801be7ee10cee3e3b7aa61132834843230ab7358c1dccbb6722bb09f25fc20`

## Qualified boundary

The pinned source captures the mean of the four HC streams after main layers
40, 41, and 42, appends those three BF16 width-4,096 rows in execution order,
concatenates them to width 12,288, applies `mtp.0.main_proj`, and then applies
weighted `mtp.0.main_norm`. The qualified reference begins at the three
already-captured BF16 tensors and ends at the normalized BF16 DSpark
conditioning tensor. Target-hidden capture itself remains the separate
`TARGET_HIDDEN_CAPTURE` operation.

The exact released resource contract is:

| Resource | Shape | Architectural encoding | Bytes |
|---|---:|---|---:|
| `mtp.0.main_proj.weight` | `[4096,12288]` | FP8 E4M3FN | 50,331,648 |
| `mtp.0.main_proj.scale` | `[32,96]` | E8M0 | 3,072 |
| `mtp.0.main_norm.weight` | `[4096]` | BF16 | 8,192 |

Projection arithmetic is the already qualified dense-FP8 rule: each BF16
activation row is quantized in 96 increasing blocks of 128 values, each output
row selects its E8M0 scale tile by `floor(output_row/128)`, block products use
the frozen FP8 dot rule, and the 96 binary32 partials reduce through the
canonical padded tree before one BF16 conversion. The padded 96-leaf tree has
96 additions per output because its three-element intermediate level is padded
to four. The following weighted RMS operation is exactly NUM-6.8 at width
4,096 with binary32 epsilon `0x358637bd`.

All complete resources validate before the exact-zero optimizations. A zero
activation may return a zero projection without multiplying, and a byte-exact
zero weight row may be omitted, but the counters retain all declared blocks,
products, reductions, conversions, and resource values. The transaction bound
is `B*S` in `1..4`.

## Source and checkpoint authority

The source audit re-reads and hashes the pinned files before checking the exact
capture, concatenation, projection, and normalization expressions:

| Official file | SHA-256 |
|---|---|
| `inference/model.py` | `c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f` |
| `inference/config.json` | `c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71` |

The complete checkpoint and canonical application remain governed by lock ID
`30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760`.
The independently verified MP=4 rank-zero resource identities are:

| Canonical resource | SHA-256 |
|---|---|
| projection weight | `1b405d7483945533ca2195df653940e4a536775e1be6cdbd735fc80b9070c9bd` |
| projection scale | `fa8ca8b8728b715805cd2722d3f27da8e47397d8fe70ebea8dbd38c0753e656b` |
| normalization weight | `c794bc276bb502e0a60f4c817da6c3fd31d3f6b3ad848643d94d9f221771a684` |

Every FP8/E8M0 code and every finite BF16 norm weight validates even when the
activation is zero. E4M3FN NaN encodings and reserved E8M0 `0xff` poison the
complete transaction.

## Independent numeric differential

The production reference composes `runtime.reference.matrix` and
`runtime.reference.normalization`. The separate functional service lane imports
neither the reference nor compiler and instead composes the independent FP8
and RMS arithmetic under `runtime.service_engine`. Both lanes retain the
projection boundary, normalized boundary, RMS mean/inverse diagnostics,
saturation counts, and the same complete semantic counter map.

Three locked corpora cover different claims:

| Corpus | Coverage | Aggregate identity |
|---|---|---|
| nonzero synthetic composition | complete `[T=2,12288]` input, complete declared 4,096-row output, sparse nonzero rows spanning both activation sources and output scale tiles | `8a2a512e9a14ba1c7b7e6f753d463eba2d9d94333005d0492206b0732bf8a876` |
| official-resource extent | all 50,342,912 official resource bytes, zero activation at `T=1,2,3,4`, complete projection/RMS outputs and counters | `d478a402269b768d8ddc4b00ffa4ae6076bbef009fc50690dc174bbaca868dde` |
| official nonzero selected rows | real projection rows 0, 127, 128, and 4,095 at full reduction width 12,288, crossing the output-scale tile boundary | `782257f37cfa74289ec796442fcfaef9f94f9f5cb2df76764f40c795b6a6782d` |

The lanes match bit-for-bit on every observable in their common boundary.
Layer-order mutation 40→41 versus 41→40 changes both projection and normalized
output in both lanes. Tests also cover malformed/ragged/oversized axes,
nonfinite BF16, FP8 NaN, reserved E8M0, binary32 overflow, atomic poison, deep
immutability, mutable-backing-map detachment, constructor forgery, exact-class
authority, and full counter reconciliation.

The official-resource extent corpus deliberately uses zero activation. It
proves complete resource validation, dimensional composition, zero semantics,
RMS behavior, and full declared logical accounting; it is not a
checkpoint-derived nonzero activation. The real selected-row corpus proves
four nonzero official rows, not complete official 4,096-row projection. The
nonzero complete-output corpus uses synthetic resources. These boundaries may
not be combined into a claim that a checkpoint-derived DSpark activation has
executed.

Public result constructors retain the projection, normalization weight, and
RMS result, so they independently reconstruct the projection-to-RMS
relationship. They do not retain the capture payloads or the 50,331,648-byte
projection resource and therefore cannot authenticate the projection
arithmetic or provenance merely by being constructed.

## Logical accounting boundary

For `T=B*S`, the complete declared operator reports, among other values:

```text
captured_bf16_values       = T * 12,288
activation_blocks          = T * 96
projection_block_dots      = T * 4,096 * 96
projection_products        = T * 4,096 * 12,288
projection_tree_adds       = T * 4,096 * 96
projection_conversions     = T * 4,096
rms_square_multiplies      = T * 4,096
rms_tree_adds              = T * 4,095
rms_pointwise_multiplies   = T * 8,192
transaction_commits        = 1
```

Resource-value counters record 50,331,648 E4M3FN values, 3,072 E8M0 values,
and 4,096 BF16 norm weights once per transaction. They are logical semantic
coverage, not claims that the bytes were physically read per token. In
particular, they do not choose ROM, SRAM, or HBM placement and do not represent
bursts, cache hits, NoC flits, cycles, latency, throughput, inference bytes/s,
power, energy, area, PPA, or a GPU comparison.

## Reproduction

```bash
export OPENTALLAS_DEEPSEEK_V4_EVIDENCE_ROOT=/path/to/deepseek-v4-flash-0731
python -m pytest -q \
  tests/runtime/test_deepseek_v4_dspark_main_project.py \
  tests/runtime/test_deepseek_v4_dspark_main_project_differential.py \
  tests/compiler/test_deepseek_v4_graph.py
```

Without the external cache, official-payload cases skip; deterministic
full-shape reference, mutation, poison, immutability, and independent
differential tests remain runnable.

## Explicit nonclaims

This qualification does not establish target-hidden capture execution,
checkpoint-derived activation, a complete DSpark block or autoregressive loop,
generated deployment artifacts, artifact-driven service execution, RTL,
physical placement or scheduling, physical ROM/SRAM/HBM traffic, cycles,
latency, bandwidth, inference bytes/s, throughput, energy, area, PPA,
manufacturability, end-to-end logits, task quality, or GPU advantage.
