# DeepSeek V4 DSpark Markov microprogram evidence

- **Evidence date:** 2026-08-29
- **Qualified boundary:** fixed microprogram structure and bounded
  reference-independent service execution
- **Official model:** `deepseek-ai/DeepSeek-V4-Flash-0731`
- **Official revision:** `7872f01b1d1fe23eabc4c98b48bffcef5a386062`
- **Reference profile:** `opentallas.deepseek_v4_markov_loop_binary32.v1`
- **Service profile:**
  `opentallas.deepseek_v4_markov_microprogram_service.v1`

## What executes

The compiler emits one fixed 388-byte program for the five-step DSpark Markov
transaction. Its complete SHA-256 is:

```text
993f099a7fa78937de8eaa93e50cb883884a65fd2e50614b83134d0a30224584
```

The body contains exactly 21 fixed-width semantic records:

```text
5 TOKEN_LOOKUP
5 VOCABULARY_PROJECT
5 BINARY32_BIAS_ADD
5 SAMPLE_AND_CARRY
1 COMPLETE
```

At step zero the lookup consumes the initial token and sampling consumes the
request entropy. At steps one through four those operands are the token and
entropy continuation produced by the preceding step. `COMPLETE` is legal only
after all five samples exist. These records are semantic operations, not
cycles, pipeline slots, physical reads, messages, or flits.

The compiler-side verifier requires byte-for-byte equality with this causal
program. A separately implemented checker reconstructs the wire ABI, all 21
records, register/resource contract, numeric contract, source identity, and
explicit nonclaims without importing the assembler or decoder. Rehashed record
forgeries, unknown opcodes/registers/resources, header drift, truncation, and
contract drift fail closed.

The service engine independently decodes and verifies the same program. It
imports no compiler, checkpoint reader, target reference, expected output,
implicit RNG, or framework runtime. Given caller-supplied BF16 W1/W2
vocabulary shards, finite binary32 base logits, initial tokens, temperature,
and an optional immutable entropy stream, it executes lookup, increasing-rank
BF16-storage/binary32-runtime projection, separate binary32 bias addition,
sampling/carry, and one atomic completion in program order.

## Bounded complete differential

A rank-four, four-token identity/permutation fixture under tensor-parallel
world size two produces:

```text
batch 0: 0, 1, 2, 3, 0, 1
batch 1: 2, 3, 0, 1, 2, 3
```

The complete output-token hash is:

```text
cc0f413587e898b8508fc9ede8925ec37a0fca07c03dd22eb859fc2efb6f67d5
```

Every retained embedding, projected bias, adjusted logit, output token, hash,
and source-logical counter matches the independent target reference. The
fixture executes 21 semantic records, 10 lookups, 160 exact product-accumulates,
40 separate bias additions, 30 argmax comparisons, and one transaction commit.
Those counts describe functional coverage only.

Fifty deterministic randomized cases vary batch, vocabulary, Markov rank,
tensor-parallel world size, finite BF16 weights, finite binary32 base logits,
initial tokens, and greedy versus explicit-entropy target sampling. Service and
reference outputs agree exactly. Additional sentinels freeze:

- increasing-rank product-add rounding separately from the later bias add;
- positive/negative binary32 zero equality and first-index argmax;
- preservation of the supplied signed-zero base-logit and temperature records;
- immutable entropy continuation across all five causal steps;
- late entropy exhaustion as an atomic poison with no caller-state mutation;
- rejection of corrupted or rehashed-but-semantically-forged microcode; and
- rejection of reconstructed result records whose token history does not follow
  their own adjusted logits and entropy stream.

## Official selected-row replay

The service test independently reads the eight official W1 and W2 rows already
governed by `DEEPSEEK_V4_MARKOV_LOOP_EVIDENCE.md`. The rows cross both sides of
all four MP=4 vocabulary boundaries and retain the complete Markov rank of 256.
Executing W1 row zero through the fixed microprogram against those eight W2
rows reproduces the frozen binary32 stream hash:

```text
cd2d68aff994647705aee41fd16a5f13f8219fe61ee824eae6f054d43127470d
```

This establishes the same selected-row arithmetic through the independently
decoded program and service lane. It remains an eight-row projection with zero
base logits, not a complete 129,280-row vocabulary execution or a real DSpark
request.

## Logical accounting and claim boundary

The service result reconciles all reference logical counters plus the exact
micro-op-family counts. Weight validation counts cover the supplied logical
tables. Widen, product, add, comparison, entropy, and token counts cover
source-visible semantics. They do not identify cache residency, ROM/HBM/SRAM
transactions, bursts, banks, collectives, instructions, cycles, stalls,
latency, bandwidth, inference bytes/s, throughput, energy, area, routing, or
PPA.

This slice accepts caller-supplied, already authenticated weight shards and
base logits. It does **not** yet provide:

- a deployment manifest or content-addressed W1/W2 image;
- checkpoint authentication inside the service boundary;
- checkpoint-derived DSpark hidden state or base logits;
- complete official-vocabulary execution;
- physical lookup-owner reduction or vocabulary all-gather;
- exact nonzero-temperature PyTorch/CUDA replay;
- confidence projection, target verification, or speculative acceptance;
- a certified physical schedule or generated-artifact RTL execution; or
- full-model, physical, performance, cost, or GPU-comparison evidence.

It therefore advances M4 and M6 without closing either gate. The next required
step remains a checkpoint-derived transformer-block path through canonical
resources, legal ROM/HBM placement, generated deployment artifacts, service
execution, and independent output/counter reconciliation.

## Reproduction

```bash
pytest -q \
  tests/compiler/test_deepseek_v4_markov_microcode.py \
  tests/runtime/test_deepseek_v4_markov_service.py \
  tests/runtime/test_deepseek_v4_hc_pre_service_numeric.py \
  tests/runtime/test_deepseek_v4_markov_loop.py \
  tests/runtime/test_deepseek_v4_sampling.py

ruff check \
  compiler/microcode/deepseek_v4_markov.py \
  compiler/checking/deepseek_v4_markov.py \
  runtime/service_engine/deepseek_v4_markov.py \
  runtime/service_engine/hc_pre_numeric.py \
  tests/compiler/test_deepseek_v4_markov_microcode.py \
  tests/runtime/test_deepseek_v4_markov_service.py \
  tests/runtime/test_deepseek_v4_hc_pre_service_numeric.py
```
