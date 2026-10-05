# DeepSeek V4 DSpark prefill-KV reference evidence

- **Evidence date:** 2026-08-29
- **Qualified boundary:** target-precision `DSPARK_PREFILL_KV` reference semantics
- **Official model:** `deepseek-ai/DeepSeek-V4-Flash-0731`
- **Official revision:** `7872f01b1d1fe23eabc4c98b48bffcef5a386062`
- **Reference profile:** `opentallas.deepseek_v4_dspark_prefill_kv_bf16.v1`
- **Graph contract at qualification:** `95c51d73b94acbf7990c18776a180e0f87404e183e55fcbb3844397d8b38b709`

## Qualified boundary

The released DSpark path does not execute its ordinary transformer block during
prefill. For each of three stages, it consumes the already-normalized BF16
main-model conditioning tensor, projects one stage-local main-KV row, applies
weighted normalization, base RoPE and FP8 QDQ, then commits the row to that
stage's session-bound circular window:

```text
conditioning [B,S,4096] BF16
  -> wkv [512,4096] E4M3FN + [4,32] E8M0
  -> kv_norm [512] BF16
  -> base RoPE on final 64 channels
  -> block-64 E4M3FN/E8M0 QDQ on first 448 channels
  -> window [B,128,1,512] BF16
```

The wrapper starts after `DSPARK_MAIN_PROJECT`; it neither produces nor
authenticates the conditioning tensor. It ends at the immutable successor
window. It does not execute the draft hidden path, the ordinary DSpark block,
the five-token Markov loop, confidence scoring, speculative verification, or
acceptance.

Projection is the qualified dense-FP8 rule over 32 increasing 128-value blocks
and four 128-row output-scale tiles. RMSNorm is NUM-6.8 at width 512. Base RoPE
starts at position zero and applies only to channels 448 through 511. The first
448 channels then pass through seven independent 64-value FP8 QDQ blocks; the
rotated final 64 channels bypass QDQ. The resulting row is committed under the
complete NUM-6.15 freshness, session, retirement, and capacity-wide version
contract.

All dimensions, all resource encodings, every finite BF16 value, `start_pos`,
stage ID, state shape, session identity, and complete version vector validate
before a successor is exposed. Exact-zero activation and byte-exact zero
weight-row acceleration preserve complete declared logical counters. Any
malformed value, FP8 NaN, reserved E8M0 scale, overflow, stale authority,
non-fresh prefill, or session violation poisons the whole transaction.

## Source and checkpoint authority

The source audit re-reads the pinned files and checks the exact prefill control
flow and operation order:

| Official file | SHA-256 |
|---|---|
| `inference/model.py` | `c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f` |
| `inference/config.json` | `c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71` |

The complete checkpoint and canonical application remain governed by lock ID
`30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760`.
The relevant official configuration fixes three MTP stages, FP8 activation
format, unsigned E8M0 scales, RoPE width 64, and circular-window width 128.

Each stage contributes exactly these canonical resources:

| Resource | Shape | Encoding | Bytes |
|---|---:|---|---:|
| `mtp.N.attn.wkv.weight` | `[512,4096]` | FP8 E4M3FN | 2,097,152 |
| `mtp.N.attn.wkv.scale` | `[4,32]` | E8M0 | 128 |
| `mtp.N.attn.kv_norm.weight` | `[512]` | BF16 | 1,024 |

The independently read MP=4 rank-zero resource identities are:

| Stage | Weight SHA-256 | Scale SHA-256 | Norm-weight SHA-256 |
|---:|---|---|---|
| 0 | `20c0fa4ef0ae2ef220c961ef65c5f3eabaea222076045f079598f256af69f879` | `54f9be7d804c9fb80089795165c60096bb09e41f4ac2fe6b49cae5dfe128cfdb` | `1019ee0ee1beae3b42168430434f61e11315c6a5597d99483f0c6410015b9d7d` |
| 1 | `f07ed5151bfb40f806ffa38d9690e15edad187784014f18af3794a15402b2fbe` | `d21da0046a704b7c13202583b9b25630c200fc5ed4a8f7b7f71553b5c0d535d2` | `ba6cb6d2cd77bce562feebd727810d82d6971d28f16aa1f992ed498bd0756fc6` |
| 2 | `bb8763965211a702de6774c88c3029870287053acd3d0bc3f8bf13e9da95dd2d` | `977c8ed4b4a12c1c6f9fa3f71f41d1bb95758e55b8dfc9df50b1c327e8557370` | `d509478a1a195bea335f2a29f96c8d2df6e00e94c88721a58b377c6a0f91150c` |

## Locked numeric evidence

Three corpora deliberately establish different boundaries:

| Corpus | Coverage | Aggregate identity |
|---|---|---|
| nonzero synthetic composition | complete `[B=1,S=2,4096]` conditioning and declared 512-row projection shape; sparse nonzero synthetic resources make projection, RMS, RoPE, QDQ, and window state data-bearing | `ac40a0164a66e9bffd2b35c96c8e4ab40da383777be2a26b90cce2ecfed2d793` |
| official-resource extent | all three complete official resource sets, exact-zero conditioning at `T=1,2,3,4`, every retained boundary, successor state, and complete counters | `b46f98c555cbf8c7c04fbf35116c66de63e77af82e75067bc48e21a58c6b4459` |
| official nonzero selected rows | real projection rows 0, 127, 128, and 511 for all stages at full width 4,096, crossing output-scale tile boundaries and checked through the independent service FP8 lane | `a6a2e504bc02a860ec744a2fe7a4756608aaf2732c697cc80b43e22113f128cb` |

The nonzero complete composition uses synthetic resources. The complete
official-resource corpus uses zero conditioning and therefore proves resource
validation, dimensional extent, exact-zero semantics, every downstream
boundary, state transition, and declared accounting—but not a nonzero official
projection. The selected-row corpus proves four nonzero rows per official
stage, not all 512 outputs and not the downstream composition. There is no
checkpoint-derived nonzero DSpark conditioning corpus. These facts may not be
combined into a stronger claim.

The reference implementation composes only already-qualified independent
semantic components. Its test lane directly recomposes RMS, RoPE, and QDQ, and
compares the selected official FP8 rows with the separately implemented service
arithmetic. This is a numeric differential, not artifact-driven execution of a
complete service opcode.

Tests also cover pinned-source hashes and expressions, forbidden resource codes
before zero acceleration, nonfinite and malformed input, start-position and
stage rejection, binary32 overflow before state commit, wrong window shape,
stale versions, session reuse on a non-fresh prefill, deep immutability,
exact-class authority, downstream constructor forgery, and complete counter
reconciliation.

## Result authority and state boundary

The public immutable result retains projection and normalized BF16 values,
normalization weights and binary32 diagnostics, rotated values, QDQ codes and
scales, committed KV, the entire prior/successor window transaction, and exact
counters. It can therefore reconstruct every boundary after projection.

It deliberately omits the conditioning tensor, projection weights, and
projection scales. A caller can construct a self-consistent downstream result
around an arbitrary finite projection, so construction alone does not
authenticate projection arithmetic, official resource identity, or producer
provenance. Those claims require entry through the qualified function and the
separately locked evidence resources.

The window is mutable architectural state and cannot reside in ROM. Session
IDs and the complete capacity-wide version vector authorize one fresh prefill
commit. For `S>128`, the result retains all `S` arithmetic rows but the circular
transaction reads and writes only the final 128 rows per active lane. Removed
trailing lanes are retired under the qualified state contract.

## Logical accounting boundary

For `T=B*S`, the principal declared counts include:

```text
conditioning_bf16_values          = T * 4,096
projection_weight_e4m3_values     = 2,097,152
projection_scale_e8m0_values      = 128
activation_blocks_quantized       = T * 32
projection_block_dots             = T * 512 * 32
projection_products               = T * 512 * 4,096
projection_tree_adds              = T * 512 * 31
projection_bf16_conversions       = T * 512
rms_square_multiplies             = T * 512
rms_reduction_adds                = T * 511
rms_pointwise_multiplies          = T * 1,024
rope_rotated_bf16_values          = T * 64
qdq_blocks_quantized              = T * 7
qdq_output_bf16_values            = T * 448
window_rows_written               = B * min(S,128)
transaction_commits               = 1
```

The record also reconciles saturation, phasor and arithmetic operations, QDQ
codes/scales, state capacity and preserved rows, removed lanes, BF16 state
values and logical bytes, and session/active/cursor/version metadata fields.
These are semantic counts. They do not state that every weight byte is fetched
per token, choose ROM/SRAM/HBM placement, or measure physical transactions,
bursts, NoC traffic, cycles, bandwidth, latency, inference bytes/s, throughput,
power, energy, area, routing, PPA, or GPU advantage.

## Reproduction

```bash
export OPENTALLAS_DEEPSEEK_V4_EVIDENCE_ROOT=/path/to/deepseek-v4-flash-0731
pytest -q tests/runtime/test_deepseek_v4_dspark_prefill_kv.py
pytest -q tests/compiler/test_deepseek_v4_graph.py
```

Without the external canonical cache, the two official-payload evidence tests
skip. The nonzero synthetic composition, source checks when the pinned source
snapshot is present, poison/authority cases, immutability, and counter tests
remain runnable.

## Explicit nonclaims

This qualification does not establish `DSPARK_MAIN_PROJECT`, provenance of its
conditioning output, a complete DSpark block, Markov autoregressive execution,
speculative verification or acceptance, checkpoint-derived nonzero activation,
generated deployment artifacts, artifact-driven service execution, RTL,
physical placement or schedule, ROM/SRAM/HBM traffic, cycles, latency,
inference bytes/s, throughput, energy, area, PPA, manufacturability, end-to-end
logits, task quality, or GPU advantage.
