# DeepSeek V4 routed/shared SwiGLU reference evidence

**Evidence status:** complete operator-level target semantics, exact canonical
layer-0 tensor identities, and full-column selected-row payload known answers

**Official source:** `deepseek-ai/DeepSeek-V4-Flash-0731` revision
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`

**Model / kernel / inference-config SHA-256:**
`c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f` /
`59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2` /
`c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71`

**Graph contract:**
`87eeb9d3a73818318a4f24b6185bece850770c6b2df2dd93586807078f373993`

## What is qualified

`runtime/reference/swiglu.py` defines the complete deterministic target
semantics of both expert kinds at all 43 main blocks and three DSpark blocks:

- `MXFP4_SWIGLU` executes routed `w1`, `w3`, and `w2` with low-nibble-first
  packed E2M1 weights, one E8M0 weight scale per 32 reduction values, FP8
  activations, and a binary32 route weight;
- `FP8_SWIGLU` executes the shared expert's three E4M3FN/E8M0 projections by
  composing the already-qualified dense FP8 linear operation; and
- both paths preserve the official `4096 -> 2048 -> 4096` shape, BF16 learned
  projection boundaries, limit 10, FP32 vector section, and final BF16 output.

The graph has 46 nodes of each kind. With these two kinds qualified, its
2,136-node/46-kind ledger has 34 qualified and 12 pending reference kinds. All
46 service-engine and RTL kinds remain pending, so this does not close M1, M4,
M6, M7, M8, or M9.

## Frozen numeric order

The official source fixes this high-level order:

```text
BF16 input
  -> BF16 w1 gate + BF16 w3 up
  -> exact widen to binary32
  -> up clamp [-10,10], gate clamp only above at 10
  -> binary32 gate * correctly-rounded sigmoid(gate)
  -> binary32 SiLU * clamped up
  -> optional binary32 route-weight multiply
  -> one BF16 conversion
  -> BF16 w2 output
```

The released matrix kernel quantizes activation columns in blocks of 128. A
routed weight scale covers 32 columns, so the same activation scale feeds four
successive MXFP4 block dots. Each 32-value dot uses increasing reduction-index
binary32 accumulation. Its completed partial is then added to
`C_local_accum` in increasing 32-value block order with one RNE addition per
block. The shared FP8 path retains its previously qualified 128-value block dot
and balanced cross-block tree.

The source does not make a tensor-core reduction tree or fused SiLU
approximation portable across backends. The target therefore uses the exact
rational correctly-rounded binary32 logistic already qualified for HC and
separate binary32 RNE multiplication boundaries. These are explicit
deterministic target adaptations, not claims that every CUDA backend returns the
same internal bits.

All BF16, binary32, E4M3FN, packed-weight, shape, and E8M0 resources validate
before the first projection executes. E4M3FN NaN, E8M0 `0xff`, nonfinite input,
malformed layout, or intermediate binary32 overflow poisons the whole operation.
Finite BF16 saturation is sticky and counted. A successful immutable result has
exactly one logical transaction commit.

## Exact canonical layer-0 payloads

The optional cache-backed test re-reads all twelve canonical rank-0 payloads,
checks size and SHA-256, and evaluates rows 0 and last over every input column.

### Routed expert 0

| Tensor | Canonical storage / logical shape | Bytes | SHA-256 |
|---|---|---:|---|
| `w1.weight` | packed E2M1 `[2048,2048]` / `[2048,4096]` | 4,194,304 | `8b8124ab561c2954c4f8d590c60c5478efb7b6726035d1328d89e806988ccceb` |
| `w1.scale` | E8M0 `[2048,128]` | 262,144 | `e2e52dd1cf8e590514eec022f7115e5c1cf7c2305bbe8372f03b1af517b5871a` |
| `w2.weight` | packed E2M1 `[4096,1024]` / `[4096,2048]` | 4,194,304 | `c013d9e37391314d6b8d9e7cadb4d0863aa39e249863c0694cd35e0c17a5e871` |
| `w2.scale` | E8M0 `[4096,64]` | 262,144 | `7c60715f1e31b4c2e64dfa01713c6293e7fa3af437e1d988be0a1b06cc01d579` |
| `w3.weight` | packed E2M1 `[2048,2048]` / `[2048,4096]` | 4,194,304 | `9b074300e23226efb9632565279943358bb15d522275d8bd077c768c563133b9` |
| `w3.scale` | E8M0 `[2048,128]` | 262,144 | `0bb0ec2d1eeaab088ba595dadc674a2646326e156d51e8837b58e739cd0b972d` |
| **Total** | three matrices plus scales | **13,369,344** | individual hashes above |

### Shared expert

| Tensor | Canonical storage / logical shape | Bytes | SHA-256 |
|---|---|---:|---|
| `w1.weight` | E4M3FN `[2048,4096]` | 8,388,608 | `e77b1555b824ef58e4a957ec42624a2b4195970521f88b97ed347a6ea918599c` |
| `w1.scale` | E8M0 `[16,32]` | 512 | `57ef9b4e3281fc835bcd778876d3e1287549bd3335903999f238cacd135c21d1` |
| `w2.weight` | E4M3FN `[4096,2048]` | 8,388,608 | `fd2d66a842dca0a101a0af6f4659a33225fbd884ce5ba030aed9de699f648638` |
| `w2.scale` | E8M0 `[32,16]` | 512 | `81f89eb49523d54f82bca47c7efba13d4e673d44d92c23e74bcc4960d02c68ae` |
| `w3.weight` | E4M3FN `[2048,4096]` | 8,388,608 | `98c88381ebf2e836db0efcdc0c1e6da02664bb7b733c7b8f46562759d6628b8c` |
| `w3.scale` | E8M0 `[16,32]` | 512 | `b88b7a0cf6bb368f3c92c5bfe3f569e42ef6782e0c05f3dbc8f06af1a4a7b862` |
| **Total** | three matrices plus scales | **25,167,360** | individual hashes above |

The test activation is an explicit deterministic full-width row:
`BF16_RNE(((column mod 17) - 8) / 8)`. It is not a checkpoint-derived hidden
state. Rows 0 and last produce these exact BF16 codes:

| Projection | Routed rows 0 / last | Shared rows 0 / last |
|---|---|---|
| `w1` | `0x3fa9`, `0x3e8d` | `0xbf97`, `0x3e64` |
| `w2` | `0xbf65`, `0xbfab` | `0x3eed`, `0x3f42` |
| `w3` | `0xbf69`, `0xbf86` | `0xbf59`, `0xbe1b` |

The routed selected rows also match a separately assembled test oracle that
quantizes each 128-value activation block, invokes four explicit 32-value block
dots per group, and performs the increasing-block adds without calling the
complete operator. Fixed selected-row answers do not qualify the other output
rows or a complete official expert invocation.

## Test scope

`tests/runtime/test_deepseek_v4_swiglu.py` covers:

- exact source/config constants, official shapes, dtypes, sizes, and hashes;
- low/high nibble order, per-32 scale addressing, and 128-to-32 scale reuse;
- an order-sensitive three-block cancellation that distinguishes serial
  block-partial addition from one exact end-of-dot sum;
- complete reduced routed and shared experts through all three projections;
- upper-only gate clamp, two-sided up clamp, direct logistic, multiplication,
  route-weight, and BF16 conversion boundaries;
- exact per-linear and complete-transaction counters;
- separately assembled and seeded randomized compositions;
- malformed/nonrectangular resources, nonfinite BF16/binary32, E4M3FN NaN,
  reserved E8M0, binary32 overflow, and validation-before-execution behavior;
- immutable result publication and one logical commit; and
- full-column selected rows from all twelve official layer-0 payloads when the
  canonical MP=4 cache is present.

The ordinary focused gate is:

```bash
python -m pytest -q \
  tests/runtime/test_deepseek_v4_swiglu.py \
  tests/compiler/test_deepseek_v4_graph.py
```

## Capacity, logical traffic, and the ROM boundary

Counters deliberately separate four concepts:

1. canonical weight and scale payload bytes describe unique immutable capacity;
2. logical matrix reads count source operands consumed by one reference command;
3. BF16 gate/up/intermediate/final traffic records each architectural dtype
   boundary; and
4. scalar-work counters record quantization, dots, block adds, nonlinear
   evaluations, multiplications, conversions, saturation, and commit.

The route tensor is a mutable/runtime binary32 input, not an immutable weight.
The learned matrices and scales are immutable ROM candidates; activations,
routing records, expert outputs, and subsequent KV/session state require writable
storage. A shared E8M0 tile may be broadcast or cached physically, while the
scalar reference counts every logical use. Conversely, one logical read may
become more than one physical transaction. No counter here is automatically an
HBM burst, SRAM port access, ROM word-line activation, NoC packet, cache miss,
cycle, or achieved byte/s value.

This distinction is mandatory for the ROM thesis: payload density and logical
weight/KV ratios alone cannot establish bandwidth, latency, cost, or advantage.
Those claims require generated placement, an executable schedule, characterized
macros, exact mutable-state traffic, and a measured same-scope comparator at M9.

## Claim boundary and next gate

This evidence qualifies deterministic target-reference semantics for the two
SwiGLU graph kinds and exact identity of one routed and one shared layer-0 expert
payload set. It does **not** establish:

- checkpoint-derived inputs, router choices, or a complete official expert
  output;
- dispatch/reduction composition through one checkpoint-derived transformer
  block;
- generated ROM/scale placement, microcode, or service-engine execution;
- a certified physical schedule or RTL conformance;
- physical memory transactions, cycles, bandwidth, token rate, energy, area,
  PPA, manufacturability, or yield;
- complete DeepSeek V4 Flash prefill/decode correctness; or
- a ROM-wafer performance or cost advantage over any GPU, Graphcore, or
  Cerebras system.

The next SwiGLU-specific gate is an artifact-only service-engine program that
streams a complete official projection (or a rigorously declared selected-row
slice), consumes a checkpoint-derived activation, persists its result, and
passes an independent payload/result/counter checker. The system-level gates
remain the M4–M9 sequence in `EXECUTABLE_SYSTEM_RECOVERY_PLAN.md`.
