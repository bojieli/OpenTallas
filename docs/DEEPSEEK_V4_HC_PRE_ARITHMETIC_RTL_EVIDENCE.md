# DeepSeek V4 HC_PRE arithmetic RTL evidence

- **Evidence date:** 2026-09-04
- **ABI:** 3.0
- **HBM target site:** PC 14, descriptor 546
- **ROM target site:** PC 15, descriptor 381
- **Transcendental campaign:** `results/rtl/a3_hc_transcendental_campaign.json`
- **Divider/Sinkhorn campaign:** `results/rtl/a3_hc_numeric_campaign.json`
- **Status:** passing reusable-block evidence; neither release gate is closed

## Outcome

A standalone synthesizable engine now computes the two mathematical-function
boundaries required by `HC_PRE`:

- correctly rounded binary32 `exp(x)` for finite `x <= 0`, including gradual
  underflow to positive zero; and
- direct correctly rounded binary32 `1 / (1 + exp(-x))` for every finite
  binary32 sigmoid input, without exposing a separately rounded exponential,
  addition, or division.

This is arithmetic, not a result table. The engine converts the exact binary32
argument to a 160-fraction-bit fixed-point value, encloses a range-reduced
alternating Taylor series, rounds every squaring outward, transforms the
sigmoid interval monotonically, and independently rounds both endpoints to
binary32 RNE. It publishes a result only if both endpoint encodings agree;
otherwise it fails closed. The bounded restoring dividers are value-independent
arithmetic circuits and contain no checkpoint or expected-output contents.

The full retained matrix has 4,200 cases: 2,100 exponentials and 2,100
sigmoids. It includes signed zeros, subnormals, normals, analytic saturation
and underflow thresholds, nonfinite and positive-exponential refusals, directed
rounding sentinels, and deterministic samples across the complete encoding
space. Icarus 11.0 and pinned Verilator 5.050 agree on all 169,962 protocol and
result checks. Pinned Yosys 0.68 elaborates the implementation and reports zero
problems. Expected codes come from the independent exact-rational reference
lane; host floating point and RTL helpers are not used by the oracle.

The earlier numeric campaign remains complementary evidence. It qualifies the
finite binary32 divider and the post-stable-softmax Sinkhorn tail, including
four matrices extracted from authenticated DeepSeek T=512 functional output.
It does not include the row-max/exponential/softmax front end.

## Position against the two release gates

| Priority | Required release result | Status after this work |
|---:|---|---|
| 1 | The governed 200,000-context DeepSeek transaction produces every expected output token, includes the first EOS token, and emits no post-EOS transaction | **Open.** This block emits FP32 arithmetic values, not logits or tokens. |
| 2 | Desired TPOT measured from that same Gate-1-passing execution using characterized SKY130 or ASAP7 timing | **Blocked by Gate 1.** Testbench cycles and simulator wall time are verification costs, not token latency. |

This work shortens the Gate-1 path by replacing two previously absent reusable
numeric primitives with bit-exact RTL. It also makes the remaining dependency
chain more specific: stable softmax can now be assembled from row max, existing
FP32 addition, this exponential engine, the qualified divider, and the
qualified Sinkhorn tail.

## Reproduction

```bash
python3 tools/build_a3_hc_transcendental_vectors.py
python3 tools/run_a3_hc_transcendental_rtl_campaign.py
pytest -q tests/compiler/test_a3_hc_transcendental_rtl.py
```

The campaign regenerates and byte-compares the vectors, runs the complete
matrix on both simulators, compares normalized summaries, and performs generic
Yosys elaboration. The retained result hashes every authoritative source,
vector, and simulator log.

## Remaining Gate-1 work

The next `HC_PRE` closure steps are:

1. implement and differentially qualify exact BF16-by-FP32 fused product-add;
2. implement the balanced 16,384-element RMS path and reuse the existing
   correctly rounded reciprocal-square-root unit;
3. assemble the source-major 4x4 stable-softmax controller and connect its
   output to the already-qualified Sinkhorn tail;
4. retain projection accumulators across the scheduler's increasing-K tiles,
   implement the affine/pre/post output paths, and atomically commit weights
   and combination matrices;
5. reproduce from arithmetic all 24 T=1 words, all 7,680 T=320 words, and all
   12,288 authenticated T=512 words, then integrate at HBM PC 14 and ROM PC 15;
6. continue through every downstream layer, logits, argmax, token append, and
   first-EOS control until the exact 200,000-context token transaction passes.

Only after step 6 closes Gate 1 can architectural token-commit events from that
same execution be converted through a physical timebase and assessed against
the frozen TPOT target.

## Explicit nonclaims

The 4,200-vector sample is not exhaustive over every binary32 encoding and is
not yet the complete checkpoint-reachable T=512 argument corpus. This evidence
does not establish full `HC_PRE`, descriptor retirement, a transformer layer,
checkpoint-backed RTL execution, output-token correctness, decoded-text
quality, EOS behavior, a 200,000-token transaction, architectural latency,
TPOT, technology timing, power, area, or ROM-versus-HBM superiority.
