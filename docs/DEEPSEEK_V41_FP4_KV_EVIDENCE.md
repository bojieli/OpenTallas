# DeepSeek-V4.1-Flash FP4 main-KV evidence

**Evidence class:** executed cross-check of a repository reference against the
pinned vendor CUDA kernel, on sampled inputs. Not a checkpoint-derived value,
not a token, not a performance number.
**Qualified boundary:** the DEQUANTIZE direction of the main compressed-KV
latent — E2M1 elements with one E4M3FN scale per 16 — for one latent row of the
released extent.
**Numeric contract:** `fp4_e2m1_s16_e4m3_to_fp8_v1`
**Reference profile id:** `deepseek_v41_flash_target_precision_v1`
**Release:** `deepseek-ai/DeepSeek-V4.1-Flash`
**Revision:** `dba1be0a40aa45a94ad051997016db3960a90277`
**Checkpoint lock:** `3035f90f54bdb46150c7c45a0fa8224c459583d0849c51d2c24fdb055e627a53`
(96,085 tensors, 510,286,023,000 payload bytes, 48 shards)

**Graph-contract digest at qualification: NONE EXISTS.** `compiler/frontends/v3/
deepseek_v41.py::export_deepseek_v41_kernel_graph` refuses today with

```
every deepseek-v4.1-flash checkpoint artifact is present and 96,085 tensor specs
resolve, so the remainder of gate DS41-I2 is the node-by-node lowering itself,
which this front end does not emit yet.
```

so there is no V4.1 graph contract to digest and none is invented here. The
identities that do exist, and that this document is bound to instead, are the
planned census digest `44f53d34427faacb81cbbc148d42932c930e5cc33dcedaa80498c47bd1ee4cbc`
(3,131 planned kernels over 40 layers) and the release's
`tensor_structure_sha256 834a3fd1840230036c63b3edf4467d9356784f69bcc4a7fb156ffec536b8ef2c`.
This document must be revisited when the graph contract first exists.

## Pinned authority

| Artifact | Pinned identity | Use |
|---|---|---|
| `inference/model.py` | SHA-256 `4e9ae23620edc8028ccc5d5fef552ab7fdc7dcd6f79608754fe9f67644056f65` | `Attention._compress_kv` calls `fp4_act_quant(latent, 16, True, scale_dtype=torch.float8_e4m3fn)` after RoPE |
| `inference/kernel.py` | SHA-256 `1236c3507019ed176f5dba5e04bcea58867cf654818c6cf138ed4845398c2455` | `fp4_act_quant` and `fp4_quant_kernel`, the executed kernel |
| `config.json` | SHA-256 `8be45ce0476004a3f529fd896115a4a2e800a129ad2d3ec05b16050f52e21879` | `head_dim` 512, the latent extent |
| Reference | `runtime/reference/fp4_kv.py` SHA-256 `7b1e216e89a7df717a23ebc2d0f358b44de314ca9898a226c1e487465220ed4a` | The contract under test |
| Producer | `tools/run_deepseek_v41_reference_oracle.py` SHA-256 `8339288c26c144255938baa54dafdace4fa6c7cf2432e89dffed0112c978c5b7` | The comparator |
| Record | `results/abi3/deepseek_v41_reference_oracle_probe.json`, stage `fp4_kv` | The executed evidence |

## What was executed

The pinned `fp4_act_quant` was called twice on the same bfloat16 input of the
released latent extent (512 elements per row, 8 rows, scale group 16, scale
dtype `torch.float8_e4m3fn`): once with `inplace=False`, returning the packed
E2M1 codes and the E4M3 scales, and once with `inplace=True`, returning the
kernel's own dequantized reconstruction.
`runtime.reference.fp4_kv.dequantize_to_bf16_values` was then given the kernel's
own codes and scales, and its exact rational products were compared against the
kernel's reconstruction element by element.

```
fp4 main KV: reference dequantize reproduces the pinned kernel exactly on
4,096 elements (low_nibble_first), mismatches 0
```

The comparison is exact rational equality, not a tolerance. The element packing
order was **determined, not assumed**: both nibble readings were tried, and
`low_nibble_first` is the one that reproduces the kernel — `high_nibble_first`
does not.

## Measured storage width, beside the recipe

The same run measured what the vendor's own cache holds, by reading
`buffer.size(-1) * buffer.element_size()` off the buffer `Attention` itself
registered. No width is transcribed in the producer; a test
(`test_no_entry_width_is_transcribed_in_the_oracle`) enforces that.

| Role | Measured (grade `executed`) | Profile recipe (grade `read_from_profile`) | measured / recipe |
|---|---|---|---|
| main | 1,024 B | 288.0 B | 3.5556 |
| index | 256 B | 68.0 B | 3.7647 |
| window | 1,024 B | 528.0 B | 1.9394 |

Measured from `Attention.compress_kv_cache` at layer 20, `Indexer.k_cache` at
layer 20, and `Attention.window_kv_cache` at layer 24, all `torch.bfloat16`.
The recipe widths are read from
`configs/models/candidates/deepseek-v4.1-flash.json` and are never restated in
the producer.

**Why the measured width is not the recipe width, and why that is not an error.**
`fp4_act_quant(..., inplace=True)` writes DEQUANTIZED values back at the INPUT
dtype. `inference/generate.py` calls `torch.set_default_dtype(torch.bfloat16)`
before constructing the `Transformer`, and every cache is registered with
`torch.zeros` at the default dtype. So on the vendor's own reference path the
compressed KV cache holds bfloat16 round-tripped values and **the FP4 codes are
never stored**. The 288 B recipe is the serving format the model card and
technical report describe; 1,024 B is what the reference implementation holds.
Neither number is corrected into the other here. The ratio is the size of the
storage-format decision the accelerator makes, and it is 3.5556 for the main
entry, not the 1.8x that the V4 program saw.

## Not established

- **The FORWARD direction.** `quantize_group_to_fp4` is documented in the
  reference as representative and was NOT compared against the kernel. The
  kernel's rule is `scale = cast_e4m3(max(amax, 6 * 2**-9) / 6)`; the reference
  documents `amax / 6` and carries no statement of the `6 * 2**-9` floor. Whether
  the two agree is open.
- **Any released latent value.** The inputs are a seeded sample. No checkpoint
  row was quantized, because reading released rows needs the layer-streaming
  engine that does not exist (below).
- **The FP8 destination rounding.** What was checked is the reference's claim
  that BF16 represents every product exactly. The accelerator's FP8 destination
  and its saturation behaviour are untested against the vendor.
- **Whole-latent partial QDQ.** The `passthrough` region of the reference's
  third DEQUANTIZE operand was not exercised.
- **Any RTL correlation.** `results/rtl/a3_v41_fp4kv_dequant_campaign.json`
  exists but is not evidence in this document and was not re-run here.
- **Any token, TPOT, throughput, bandwidth, latency, area or energy.** None is
  claimed and none was measured.
- **The greedy token ladder.** Not run. `model.sparse_attn` cannot launch on the
  available device: at the released `n_heads` 64 and `head_dim` 512 it fails with
  `InternalError: Failed to set the allowed dynamic shared memory size to
  141312`, against 101,376 B of opt-in shared memory per block on an
  NVIDIA RTX PRO 6000 Blackwell Workstation Edition (compute capability 12.0).
  The two repository prerequisites that are also absent are listed in the
  record's `tokens.prerequisites`.

## Reproduce

```bash
PATH=/usr/local/cuda/bin:$PATH python3 tools/run_deepseek_v41_reference_oracle.py \
  --stage widths --stage fp4_kv \
  --output results/abi3/deepseek_v41_reference_oracle_probe.json
pytest -q tests/test_deepseek_v41_reference_boundaries.py
```

`/usr/local/cuda/bin` must precede the default `nvcc` on `PATH`: the default is
release 11.5, whose newest target is `sm_87`, and every tilelang kernel in
`inference/kernel.py` fails to compile for this `sm_120` device without release
12.8.
