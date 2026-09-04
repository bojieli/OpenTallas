# DeepSeek V4 HC_PRE descriptor and tile-scheduler RTL evidence

- **Evidence date:** 2026-09-04
- **ABI:** 3.0
- **ROM site:** wafer decode PC 15, `VECTOR.MHC`, descriptor 381
- **HBM site:** qualified scheduler snapshot PC 14, `VECTOR.MHC`, descriptor 546; current main descriptor 545
- **Campaign:** `results/rtl/a3_mhc_pre_tile_campaign.json`
- **Arithmetic continuation:** `docs/DEEPSEEK_V4_HC_PRE_ARITHMETIC_RTL_EVIDENCE.md`
- **Status:** passing prerequisite evidence; neither release gate is closed

## Outcome and acceptance position

The standalone synthesizable scheduler admits the exact retained-snapshot ROM
and HBM `HYPER_CONNECT_PRE` records and emits every required projection and output
coordinate once, in deterministic token/field/increasing-K order. Icarus and
pinned Verilator 5.050 produce identical results, and pinned Yosys 0.68 reports
zero generic elaboration problems.

This is deliberately below the project's two ordered release gates:

| Priority | Release outcome | Status after this work |
|---:|---|---|
| 1 | Correct end-to-end output tokens, legitimate decoded text, first-EOS-inclusive or exact-cap stopping, and no post-EOS transaction | **Open.** The scheduler produces no arithmetic result, logit, token, or EOS decision. |
| 2 | Desired TPOT from the same token-correct execution at the governed batch/process point | **Blocked by Gate 1 and not evaluable.** Scheduler cycles and simulator wall time are verification cost, not architectural token latency. |

The evidence therefore closes one concrete Gate-1 prerequisite without
claiming Gate 1. It must not be counted as a correctness-qualified TPOT point.

## Exact admitted work

The vector builder derives the instruction and all consumed descriptors from
the retained four-deployment images. For the HBM T=512 profile it additionally
byte-compares the selected instruction and eleven records with the independent
checkpoint-backed functional qualification. The complete 256-bit numeric
contract digest is part of admission.

| Profile | Active extent | Projection tiles | Commit tiles | Logical projection FMAs | Output words |
|---|---:|---:|---:|---:|---:|
| ROM wafer decode | 1 | 16 | 2 | 393,216 | 24 |
| HBM authenticated full block | 512 | 393,216 | 24 | 201,326,592 | 12,288 |
| HBM final prefill block | 320 | 245,760 | 15 | 125,829,120 | 7,680 |
| HBM decode | 1 | 49,152 | 3 | 393,216 | 24 |

The HBM 512- and 320-token extents are the two block shapes needed by the exact
200,000-token partition (`390 * 512 + 320`). This campaign executes one of each
shape; it does not claim that all 391 model blocks or the complete 200,000-token
model ran.

Projection tiles cover `[T,16384] x [24,16384]^T`. A consumer must retain one
accumulator across consecutive increasing-K tiles; split-K reassociation is
forbidden. Commit tiles cover weights `[T,2,4]` and source-major combination
matrices `[T,4,4]` without gaps or overlap.

## Correlation and failure evidence

The independent scoreboard performs 11,346,434 comparisons across 688,188
accepted tiles. It injects 181,605 deterministic backpressure cycles and checks
that all output metadata and all accounting counters remain stable. An
additional active-reset case discards a 37-tile prefix and verifies that the
interface and counters return to the empty state.

Eighteen mutations fail before any tile is emitted. They cover instruction,
operator/counter, numeric digest and epsilon, view geometry/permissions, active
extent, and schedule fields. The two simulators agree on every rejection class
and every positive case summary.

The authenticated T=512 functional golden remains separately bound:

- 4,096 weight words: `f4d046389962e663ae789177c9e86f2643df701270d5b385ab9840f7c6148a63`;
- 8,192 combination words: `5d9a46a955239c39d423edcdfa0d3cce4b51b93aeebd585fb357ecd7eba186fa`;
- weights followed by combination, 12,288 FP32 words:
  `421774b7a8157549784615466e7868d2e44e11ed93fe3a060efd923ed3b75565`.

The RTL scheduler binds that golden's instruction/descriptors and covers its
logical coordinates. It does not inject, replay, or compute the golden output.

## Artifacts and reproduction

The implementation and evidence are intentionally standalone so that the
shared shipped-prefix bridge can integrate them after arithmetic closure:

- `rtl/abi3/ot_a3_vector_mhc_pre_tile_scheduler.sv`;
- `rtl/test/tb_a3_mhc_pre_tile_scheduler.sv`;
- `tools/build_a3_mhc_pre_tile_vectors.py`;
- `testdata/rtl/a3_mhc_pre_tiles/`;
- `tools/run_a3_mhc_pre_tile_rtl_campaign.py`;
- `results/rtl/a3_mhc_pre_tile_campaign.json`; and
- `tests/compiler/test_a3_mhc_pre_tile_rtl.py`.

Focused reproduction is:

```bash
python3 tools/build_a3_mhc_pre_tile_vectors.py
python3 tools/run_a3_mhc_pre_tile_rtl_campaign.py
pytest -q tests/compiler/test_a3_mhc_pre_tile_rtl.py
```

## Required continuation

Gate 1 still requires correctly rounded RMS/projection and exact weight and
combination commits to be integrated behind this scheduler. Standalone
certifying sigmoid/nonpositive-exponential, source-major 4x4 stable-softmax,
and Sinkhorn-tail blocks now pass focused dual-simulator campaigns. They are
also composed under one atomic boundary over all 512 matrices in the first
checkpoint block, all 320 in the final partial block, and a T=1 witness. That
composition is not wired to this scheduler, and the intervening 389 full-sized
blocks remain outside the checkpoint-derived RTL campaign. The
complete operator must reproduce all authenticated T=512 output words from
computation, then be connected at ROM PC 15 and HBM PC 14. The RTL path must subsequently
continue through all remaining model operators, communication, logits, argmax,
token append, and first-EOS control and pass the governed natural and agentic
token suites plus the exact Qwen-8K and DeepSeek-200K workloads.

Only after those same executions match every oracle token may their raw
token-commit ticks be converted through a characterized SKY130 or ASAP7
timebase and compared with a pre-frozen numerical TPOT SLO for B=1/2/4/8.

## Explicit nonclaims

This evidence does not establish full `HC_PRE` RTL arithmetic, a complete
transformer layer, checkpoint-backed model execution, output-token correctness,
token legitimacy, decoded-text quality, EOS behavior, a complete 200,000-token
transaction, shipped-prefix integration, architectural cycles, latency, TPOT,
throughput, technology timing, power, area, or ROM-versus-HBM superiority.
