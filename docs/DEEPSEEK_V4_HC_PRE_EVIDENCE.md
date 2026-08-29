# DeepSeek V4 HC_PRE reference evidence

- **Evidence date:** 2026-08-29
- **Qualified boundary:** target-precision `HC_PRE` reference semantics only
- **Official model:** `deepseek-ai/DeepSeek-V4-Flash-0731`
- **Official revision:** `7872f01b1d1fe23eabc4c98b48bffcef5a386062`
- **Numeric profile:** `opentallas.deepseek_v4_hc_pre_numeric.v1`
- **Graph contract:** `78ad4c98d9c8397ab6cd8ec82cbdcb91751e2cba4aac96a1275a6c783a38db6f`

## What is qualified

`runtime.reference.hyper_connection.hc_pre_bf16` defines the deterministic
target result for all 92 `HC_PRE` sites in the pinned 2,136-node graph: attention
and FFN pre-mixing in each of 43 main blocks and three DSpark blocks. The graph
ledger now has 39 qualified and seven pending reference kinds. All 46 RTL kinds
remain pending; the graph-wide service-engine ledger also remains pending.

The bounded reference transaction accepts one through four tokens. Each token
contains four BF16 streams of width 4,096. Learned parameters are binary32 with
official shapes `[24,16384]`, `[3]`, and `[24]`. The reference fixes:

- balanced width-16,384 RMS reduction, binary32 epsilon, and correctly rounded
  reciprocal square root;
- 24 increasing-K exact-product/binary32-RNE projection rows;
- separate affine multiply/add boundaries;
- correctly rounded binary32 sigmoid and nonpositive exponential;
- stable row softmax, one initial column normalization, and exactly 19 further
  row/column stages, for 20 row and 20 column stages total;
- `[source][destination]` combination-matrix orientation;
- balanced four-stream branch reduction and one final BF16 conversion; and
- atomic poison, immutable results, and exact logical-counter reconciliation.

Public result and diagnostic records require deeply immutable exact tuples,
bind the numeric profile, reject subclass authority, and reconstruct every
numeric relationship their retained fields can prove. They do not retain the
learned inputs or provenance needed to authenticate a checkpoint transaction.

## Source authority

The cache-optional source audit re-reads all three pinned files before checking
the exact source expressions and configuration fields.

| Official file | SHA-256 |
|---|---|
| `inference/model.py` | `c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f` |
| `inference/kernel.py` | `59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2` |
| `inference/config.json` | `c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71` |

The official source specifies the shapes and expression/loop structure, but
does not make PyTorch GEMM/reduction association, TileLang transcendental bits,
or device FTZ behavior portable. The explicit OpenTallas arithmetic is therefore
a target adaptation, not a claim of CUDA or TileLang bit equivalence.

## Independent numeric evidence

The production reference uses exact rational enclosures and imports neither a
host math library nor the compiler or service engine. Its conformance tests
include:

- a correctly rounded sigmoid/exponential corpus independently regenerated at
  both 180 and 260 decimal digits;
- a 4,096-code deterministic transcendental differential against a separately
  implemented Decimal-based service lane;
- 64 asymmetric Sinkhorn matrices compared between the independent lanes;
- a sentinel that distinguishes stage 19 from stage 20 and transposed matrix
  orientation;
- separate balanced-versus-left-fold sentinels for RMS, softmax, and branch
  reduction;
- exhaustive bounded token extents `T=1,2,3,4`; and
- malformed-shape, nonfinite, early/late overflow, immutable-input, constructor
  forgery, and atomic-poison mutations.

## Locked-checkpoint extent corpus

The official corpus uses the independently verified layer-0 attention HC
parameter application and the independently verified tokenizer/lookup-derived
hidden state for the text `Hello` (token ID 19,923). The exact source payloads
are:

| Payload | SHA-256 |
|---|---|
| HC hidden BF16 `[1,1,4,4096]` | `f0ea58b5da876ba4fd41b5a72b2721d7d300c1bd6377db558eac08f57e7dc9e6` |
| `layers.0.hc_attn_fn` F32 `[24,16384]` | `f5c1ffdfb92df2c04ac17e9a31e38701f2b7a5cac0cd427a2df2aa3e239987fc` |
| `layers.0.hc_attn_scale` F32 `[3]` | `0b0e327d2f4d1a104c53d6e0a9172cf532028383e82cdf6d70537cb83092c63f` |
| `layers.0.hc_attn_base` F32 `[24]` | `edaa695cf5de59f919415f6e71dcb35be5ad817a06fa7222ee3021d9f388adda` |

The extent test deliberately repeats that same authentic token from one to four
positions. This isolates transaction extent from token-value variation; the
heterogeneous sparse corpora above test value variation separately. It is not a
claim that a four-token prompt with four distinct official embeddings was run.

For every extent, the independent reference and service arithmetic match exactly
on branch, pre, post, combination, residual, RMS mean, RMS inverse, projection,
normalized mix, stable-softmax payloads, saturation count, and all logical
counters. Each record hash binds that complete payload-hash and counter-hash map.

| T | Record SHA-256 |
|---:|---|
| 1 | `0eff4d087d2ad25518ddcd0a5d3592bf5a0237586d7e425eb64ba1ffe68b41b3` |
| 2 | `0e681964b79cc613bcf482b66a7812223223e95e29e5f99a7437e5f5cfe4e1d3` |
| 3 | `490ae6c24ee98ac9e56ac7fcdacd96bfda191a6537207efdf39b258bc45f11fa` |
| 4 | `60448b7b4c080dc9ab13ec68c74986eb7a91132ef207babb7495d499ade76835` |

The canonical aggregate of the four records and four source hashes is:

```text
6582fb14ce5ed2657bab39211bd33787ce40b4b3c815f67a0413fbf87bbd9b55
```

## Reproduction

The source and locked-checkpoint checks use the ordinary cache locations or the
following environment variable when evidence lives elsewhere:

```bash
export OPENTALLAS_DEEPSEEK_V4_EVIDENCE_ROOT=/path/to/deepseek-v4-flash-0731
python -m pytest -q \
  tests/runtime/test_deepseek_v4_hc_pre.py \
  tests/runtime/test_deepseek_v4_hc_pre_differential.py
```

Without the optional cache, the locked source/checkpoint cases skip; all
redistributable deterministic reference and differential cases still run.

## Explicit nonclaims

This evidence does not establish official-backend bit equivalence, an HC_POST or
attention transaction, a complete transformer block, full checkpoint execution,
graph-wide service execution, RTL correctness, physical scheduling, ROM/HBM
traffic, cycles, latency, throughput, energy, area, PPA, manufacturability, or a
GPU performance advantage. Logical counters are functional accounting only.
