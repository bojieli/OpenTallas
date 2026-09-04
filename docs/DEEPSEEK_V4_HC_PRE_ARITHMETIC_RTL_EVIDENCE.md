# DeepSeek V4 HC_PRE arithmetic RTL evidence

- **Evidence date:** 2026-09-04
- **ABI:** 3.0
- **HBM target site:** current PC 14, descriptor 545; prior qualified scheduler descriptor 546
- **ROM target site:** PC 15, descriptor 381
- **Stable-softmax implementation:** `bc06fcb`
- **Stable-softmax/Sinkhorn implementation:** `4bc65f5`
- **Transcendental campaign:** `results/rtl/a3_hc_transcendental_campaign.json`
- **Stable-softmax campaign:** `results/rtl/a3_hc_stable_softmax_campaign.json`
- **Stable-softmax/Sinkhorn campaign:** `results/rtl/a3_hc_softmax_sinkhorn20_campaign.json`
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
The source-major 4x4 stable-softmax front end is now synthesizable and
qualified separately. For every row it executes the frozen sequence exactly:

```text
shifted[i] = RN32(logit[i] - max(logit))
exp[i]     = CR32_EXP_NONPOS(shifted[i])
denom      = RN32(RN32(exp[0] + exp[1]) + RN32(exp[2] + exp[3]))
output[i]  = RN32(RN32(exp[i] / denom) + 0x358637bd)
```

All sixteen inputs are latched on one handshake, signed zero is canonicalized,
and no output word is architecturally visible until the complete matrix has
succeeded. A nonfinite input or arithmetic refusal publishes one nonzero error
with an all-zero 4x4 result. The RTL contains no checkpoint- or output-indexed
lookup table: it composes the general FP32 adder, certifying exponential, exact
divider, and balanced add tree.

The retained stable-softmax campaign covers 853 matrices. Of those, 832 are
derived from the authenticated DeepSeek checkpoint and exact 200,000-token
workload: all 512 matrices in the first prefill block and all 320 matrices in
the final partial block. The remaining 21 cover maximum position and ordering,
signed zero, near-equal normal values, subnormal subtraction, exponential
underflow, finite extremes, subtraction overflow, and five nonfinite refusal
kinds. Its independent oracle uses exact `Fraction` arithmetic and integer RNE
for every algebraic operation and the separate exact-rational adaptive-interval
exponential reference; it uses no host floating point, service arithmetic, or
RTL helper. The first four matrices reproduce the retained service sentinels,
and the complete 832-matrix expected stream has SHA-256
`a3e540a4cfaf1ef499cf98199fc60d64b75e782cefdb56af4b12605b15142892`.

Icarus 11.0 and pinned Verilator 5.050 agree on all 2,394,764 checks per
simulator: 13,312 checkpoint output words, six atomic failures, 1,696 busy
refusals, 250 output-stall cycles, active reset, and 2,375,812 checks that no
partial matrix becomes visible while work is in flight. Pinned Yosys 0.68
elaborates the composed block and reports zero problems. The observed 1,410
maximum controller cycles and simulator wall times are verification metadata
for this conservative time-multiplexed block, not architectural latency or
TPOT.

The stable-softmax and Sinkhorn blocks are now composed behind one atomic
request/response boundary. A complete stable-softmax matrix remains private,
enters the frozen initial-column plus nineteen row/column Sinkhorn sequence,
and only the sixteen final combination coefficients can commit. Any refusal in
either child produces one all-zero matrix with the child error. Active reset
was exercised after Sinkhorn began; a poison request held throughout each live
transaction was refused without changing the accepted input; and every final
matrix remained stable under output backpressure.

The composed campaign reuses the same 853 affine-logit matrices and recomputes
all expected values with independent exact-rational arithmetic. All 847 valid
transactions complete 528,528 divisions; five nonfinite and one finite
subtraction-overflow case fail atomically. The first 512 final matrices are
byte-identical to the authenticated full functional `HC_PRE` combination
output, SHA-256
`5d9a46a955239c39d423edcdfa0d3cce4b51b93aeebd585fb357ecd7eba186fa`.
The first-plus-final checkpoint-block stream has SHA-256
`51684cad947f996d08e01b7674b2be7b864874bed137eff03582012af8f3e63b`;
the final T=320 segment alone is
`dbdc4f90828960793c1a5f31bd0d223c402df6d77e1939f314648a9c4d4684bd`.

Icarus 11.0 and pinned Verilator 5.050 agree on 19,313,653 result, protocol,
and private-output checks per simulator. Pinned Yosys 0.68 reports zero generic
elaboration problems. The manifest binds current main's ROM PC 15 descriptor
381 and HBM PC 14 descriptor 545, their instruction/operator/numeric/output
view bytes, deployment identities, and common numeric contract digest. This is
source identity binding, not descriptor execution or integration at those PCs.
Generation fails closed unless both current deployment-certificate artifacts,
the authenticated functional qualification, its qualification vector, and the
retained T=512 combination payload rehash and agree on checkpoint, exact-200K
workload, output, and explicit token/EOS/TPOT nonclaims.
The observed maximum 22,786 controller cycles and host wall times are only
verification metadata for a conservative serial implementation—not token
latency or TPOT.

## Position against the two release gates

| Priority | Required release result | Status after this work |
|---:|---|---|
| 1 | The governed 200,000-context DeepSeek transaction produces every expected output token, includes the first EOS token, and emits no post-EOS transaction | **Open.** This block emits FP32 arithmetic values, not logits or tokens. |
| 2 | Desired TPOT measured from that same Gate-1-passing execution using characterized SKY130 or ASAP7 timing | **Blocked by Gate 1.** Testbench cycles and simulator wall time are verification costs, not token latency. |

This work shortens the Gate-1 path by replacing previously absent reusable
numeric primitives and completing the bit-exact stable-softmax-to-Sinkhorn
combination-coefficient composition. It is still standalone: neither input
logit production nor its final result is driven by the real PC-14/PC-15
descriptor path.

## Reproduction

```bash
python3 tools/build_a3_hc_transcendental_vectors.py
python3 tools/run_a3_hc_transcendental_rtl_campaign.py
pytest -q tests/compiler/test_a3_hc_transcendental_rtl.py
python3 tools/build_a3_hc_stable_softmax_vectors.py
python3 tools/run_a3_hc_stable_softmax_rtl_campaign.py
pytest -q tests/compiler/test_a3_hc_stable_softmax_rtl.py
python3 tools/build_a3_hc_softmax_sinkhorn20_vectors.py
python3 tools/run_a3_hc_softmax_sinkhorn20_rtl_campaign.py
pytest -q tests/compiler/test_a3_hc_softmax_sinkhorn20_rtl.py
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
3. retain projection accumulators across the scheduler's increasing-K tiles,
   implement the affine/pre/post output paths, and atomically commit weights
   and combination matrices;
4. reproduce from arithmetic all 24 T=1 words, all 7,680 T=320 words, and all
   12,288 authenticated T=512 words, then integrate at HBM PC 14 and ROM PC 15;
5. continue through every downstream layer, logits, argmax, token append, and
   first-EOS control until the exact 200,000-context token transaction passes.

Only after step 5 closes Gate 1 can architectural token-commit events from that
same execution be converted through a physical timebase and assessed against
the frozen TPOT target.

## Explicit nonclaims

The 4,200-vector transcendental sample is not exhaustive over every binary32
encoding. The stable-softmax evidence covers the first T=512 and final T=320
checkpoint blocks, not every one of the 391 blocks in the 200,000-token
transaction. This evidence does not establish full `HC_PRE`, descriptor
retirement, a transformer layer, checkpoint-backed full-model RTL execution,
output-token correctness, decoded-text quality, EOS behavior, a complete
200,000-token transaction, architectural latency, TPOT, technology timing,
power, area, or ROM-versus-HBM superiority.
