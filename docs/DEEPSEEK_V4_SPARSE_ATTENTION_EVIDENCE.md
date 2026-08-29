# DeepSeek V4 sparse-attention reference evidence

**Evidence status:** operator-level target semantics and bounded official-kernel
differential

**Official source:** `deepseek-ai/DeepSeek-V4-Flash-0731` revision
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`

**Kernel SHA-256:**
`59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2`

**Graph contract:**
`8357b3d82b443750c7849047997048438325a078cb9a8284408eb6ea2c05f27a`

## What is qualified

The independent reference in `runtime/reference/sparse_attention.py` defines all
46 Flash `SPARSE_ATTENTION` sites. It implements the released block-64 gather
and online-softmax structure while freezing the numeric boundaries that the
TileLang source leaves backend-dependent:

- BF16 query and mutable KV, binary32 QK/output accumulation, and BF16 output;
- increasing-dimension QK product-add order;
- binary32 score-scale multiplication using `0x3d3504f3`;
- finite numeric maximum and a NUM-6.1 balanced 64-lane score sum;
- correctly rounded binary32 exponentials with gradual underflow;
- separate online rescale multiply and denominator add;
- exactly one binary32-to-BF16 probability conversion before AV;
- increasing selected-slot AV product-add order;
- the learned binary32 sink added to the denominator after all blocks; and
- one final binary32 division and BF16 conversion.

Malformed shapes, nonfinite public inputs, illegal indices, an all-padding first
block, intermediate binary32 overflow, or a nonpositive denominator poison the
whole result. Explicit `-1` padding, implicit tail padding, and duplicate valid
indices are all tested. Duplicate selections remain distinct contributions.

## Mutable-KV byte boundary

One valid selected row contains 512 BF16 values, so the semantic mutable-KV
read is exactly:

```text
1 valid selected occurrence × 512 values × 2 bytes = 1,024 bytes
```

The counter uses valid occurrences, not unique indices: a duplicate selection
is another logical read and contribution. Explicit `-1` and implicit tail lanes
consume source block lanes but read zero KV bytes. Query, sink, index, selected
KV, output, and padded-work counters remain separate. They do not predict HBM
transactions, SRAM hits, cache reuse, coalescing, cycles, or achieved bandwidth.

## Exact exponential evidence

`runtime/reference/transcendental.py` computes `CR32(exp(x))` without host
floating point. Negative inputs use exact alternating-Taylor bounds after
power-of-two argument reduction. Positive inputs invert the exact enclosure of
`exp(-x)`. Precision doubles until both rational bounds round to one IEEE
binary32 code. Correct underflow is legal; a finite result that rounds beyond
binary32 is poison.

Tests retain known answers from underflow through the positive overflow edge
and compare 68 signed inputs with an independent 220-decimal-digit calculation.
They also expose sink-overflow poison through the complete attention operator.

## Real checkpoint sink payload

The canonical MP=4 checkpoint audit concatenates `layers.0..42`, followed by
`mtp.0..2`, and rank `0..3` within every layer. The result is:

| Field | Result |
|---|---:|
| Shards | 184 |
| Binary32 values | 2,944 |
| Bytes | 11,776 |
| SHA-256 | `2f93e2a35c5ad1dbd4aaff353a46082d6811e7b896bf388583bd05e023c2844f` |
| Minimum | `-2.4585509300231934` / `0xc01d58e6` |
| Maximum | `2.4927473068237305` / `0x401f892c` |
| Positive / negative / zero | 2,680 / 264 / 0 |

The TileLang differential uses the actual rank-0 layer-0 sink shard, SHA-256
`71685540a438556a8c98f009de9e8026ebca43b09c810bb4bf06be26de1f8616`.
This qualifies the released sink payload, not checkpoint-derived query or KV
activations.

## Official TileLang 0.1.8 differential

The reproducible result is
`results/model-execution/deepseek-v4-sparse-attention-tilelang018.json`,
SHA-256
`57834785ff91628950e59f90222548f7088d13984366c1ee12f86f1a8edcbc4d`.
The audit executed the unmodified content-pinned kernel with:

| Component | Governed value |
|---|---|
| Python | 3.10.12 |
| PyTorch | 2.10.0+cu128 |
| TileLang | 0.1.8 |
| `apache-tvm-ffi` | 0.1.8.post2 |
| `torch-c-dlpack-ext` | 0.1.5 |
| `z3-solver` | 4.14.1.0 |
| CUDA compiler | 12.8, V12.8.93 |
| NVIDIA driver | 595.71.05 |
| GPU | RTX PRO 6000 Blackwell, SM120 |

TileLang 0.1.8 pins its own version but declares a broad transitive
`apache-tvm-ffi~=0.1.0` range. The current 0.1.10 installation failed inside the
TileLang nested-loop checker. The audit therefore pins the contemporaneous
0.1.8.post2 wheel and records every selected wheel hash. This is a governed
development environment, not a claim that DeepSeek used the same transitive
wheel, CUDA compiler, driver, or GPU.

Both corpora use one full 16-head tensor-parallel partition, dimension 512, 12
KV rows, 70 selected-axis entries, two source blocks, holes, one duplicate, 58
explicit padding entries, and 58 implicit tail lanes. Each executes 8,192 BF16
outputs and uses the real sink shard.

| Corpus | Input SHA-256 | Official output | Target output | Differences |
|---|---|---|---|---:|
| exact eighths, seed `0x5350415253455841` | `87c7dea88b04c90289062d486bd06b7f0636adc4a641295fd917676d636950c2` | `ba327ffb5c554ff940aa0175dd6584c04cdb8b166f345bc466a940f179af9a6b` | same | 0 / 8,192 |
| broad BF16, seed `0x5350415253454f46` | `c6693d9bc07368d6ba94be6067b238f9088fe651235c8d23622b8766dcbd4e2d` | `bb527d4d81562448cbbcaa0af9083f4789de79994090a27d7fc19c1358d3897c` | `9f90441e6f04c9beec175c46f27c7794eaf361c12cbe6320f6958783921656b8` | 3 / 8,192 |

The three broad-corpus differences occur at flattened output indices 5,066,
5,651, and 6,124. Each is one same-sign BF16 encoding step. This bounded
divergence is expected: the released kernel uses Tensor Core MMA association,
TileLang reduction trees, and `expf`, whereas the target deliberately fixes
increasing-index product accumulation, a canonical balanced sum, and CR32
exponential. The result is evidence for an explicit target profile, not a basis
for declaring either backend universally correct or equivalent.

## Reproduction

The governed audit driver is
`tools/audit_deepseek_v4_sparse_attention.py`. From an isolated environment with
the report's exact wheels and PyTorch/CUDA stack:

```bash
PATH=/usr/local/cuda-12.8/bin:/usr/bin:/bin \
CUDA_HOME=/usr/local/cuda-12.8 \
python tools/audit_deepseek_v4_sparse_attention.py \
  --kernel /path/to/pinned/inference/kernel.py \
  --canonical-mp4 /path/to/canonical-mp4 \
  --wheel-dir /path/to/governed-wheels \
  --output /tmp/deepseek-v4-sparse-attention-tilelang018.json
```

The expected output-file SHA-256 is
`57834785ff91628950e59f90222548f7088d13984366c1ee12f86f1a8edcbc4d`.
The driver validates source, wheel, input, checkpoint-sink, output, and result
hashes before writing the report.

## Claim boundary

This evidence establishes an independent deterministic operator definition,
logical selected-KV byte accounting, real sink identity, and bounded behavior
against the exact released kernel under one declared development stack. It does
not establish:

- checkpoint-derived query/KV attention known answers;
- mutable KV prepare/commit behavior;
- a service-engine micro-op or generated schedule;
- RTL numerical conformance;
- cycles, physical bandwidth, cache behavior, energy, area, or PPA;
- complete-model decode correctness; or
- OpenTallas throughput or superiority over any GPU.

Those remain later M4–M9 gates in the executable-system recovery plan.
