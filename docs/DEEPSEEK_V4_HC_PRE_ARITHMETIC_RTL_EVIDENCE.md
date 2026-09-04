# DeepSeek V4 HC_PRE arithmetic RTL evidence

- **Evidence date:** 2026-09-04
- **ABI:** 3.0
- **HBM target site:** current PC 14, descriptor 545; prior qualified scheduler descriptor 546
- **ROM target site:** PC 15, descriptor 381
- **T=1 implementation:** `0da6107`
- **Stable-softmax implementation:** `bc06fcb`
- **Stable-softmax/Sinkhorn implementation:** `4bc65f5`
- **Transcendental campaign:** `results/rtl/a3_hc_transcendental_campaign.json`
- **Stable-softmax campaign:** `results/rtl/a3_hc_stable_softmax_campaign.json`
- **Stable-softmax/Sinkhorn campaign:** `results/rtl/a3_hc_softmax_sinkhorn20_campaign.json`
- **Divider/Sinkhorn campaign:** `results/rtl/a3_hc_numeric_campaign.json`
- **Full T=1 coefficient campaign:** `results/rtl/a3_hc_pre_t1_campaign.json`
- **Status:** passing authenticated T=1 descriptor-facing coefficient evidence; neither release gate is closed

## Outcome

The current ROM PC 15 / operator 381 and HBM PC 14 / operator 545 semantic
configurations now drive one common synthesizable T=1 arithmetic path. It
computes, rather than looks up:

- all 16,384 BF16 input squares and the exact 16,383-add balanced RMS tree;
- the `2^-14` mean scale, epsilon addition, and correctly rounded reciprocal
  square root;
- 24 rows of increasing-K BF16-by-FP32 exact-product, single-rounded FP32
  accumulation, using eight physical field lanes and 393,216 fused
  product-adds;
- all 24 normalized projection and separately rounded affine values;
- eight sigmoid-derived pre/post weight words; and
- the sixteen source-major stable-softmax/Sinkhorn-20 combination words.

The authenticated input is position zero, token ID 18,042, from the exact
200,000-token `TA-DS-CTX-200K-1` workload. The retained input is extracted from
the pinned official checkpoint and contains 16,384 BF16 hidden codes, 393,216
FP32 projection codes, 24 bases, and three scales. Full checkpoint shard,
tensor, selected-row, extracted-file, workload, and current descriptor-image
identities are retained. An independent immutable exact-rational reference
recomputes every expected value. The final 24 words also equal the first token
of the separately authenticated T=512 functional qualification byte for byte.

The exact checkpoint witness is:

```text
mean square = 0x3b98e318
inverse RMS = 0x416a36cf
raw projection SHA-256 = 53df982fa534d5f09851f5632840ecad1327ec56512e64eb3e442a3d63e9390a
normalized projection SHA-256 = 74c6f22532fd9c459f042175afb28ba17224f41ba3abff2d977af920279428d1
final 8+16 coefficient SHA-256 = 230486960b73611968868cb0999567ec2085a3e6e37cca0fe8d063c174d61a02
```

The independent FMA oracle additionally covers 4,112 cases: 3,571 finite
successes, six nonfinite refusals, and 535 finite overflows. In 118 successful
cases the required fused boundary differs from a separately rounded multiply
then add, preventing that common implementation substitution from passing.

Icarus 11.0 and pinned Verilator 5.050 agree on 1,379,450 checks per simulator.
Both descriptor profiles reproduce all 74 retained numeric boundary words;
their 24 public coefficient words are identical. The campaign continuously
checks 685,335 in-flight cycles for all-zero public outputs and also covers
busy input refusal/input latching, active reset, output backpressure, an
active-token descriptor refusal, an early nonfinite-hidden refusal, and a late
nonfinite-base refusal after projection. The late failure produces exactly one
all-zero error transaction; it cannot leak or double-complete. Pinned Yosys
0.68 generically elaborates and checks the integrated top with zero reported
structural problems; the 16,384-word reduction scratch remains one 524,288-bit
memory with two read ports and one write port rather than expanding into a
controller-reset register array.

The campaign records 236,126 conservative controller cycles for either
descriptor profile. That number is deliberately **not TPOT**: it is the
operation count of this standalone, serial verification implementation, is not
a whole-token execution, and has no SKY130/ASAP7 characterized clock or full
memory/interconnect schedule.

## Reusable arithmetic foundation

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
| 1 | The governed 200,000-context DeepSeek transaction produces every expected output token, includes the first EOS token (or exact governed cap), and emits no post-EOS transaction | **Open.** One layer-zero T=1 coefficient boundary passes; it emits no logit or token. |
| 2 | Desired TPOT measured from that same Gate-1-passing execution using characterized SKY130 or ASAP7 timing | **Blocked by Gate 1.** Operator/testbench cycles and simulator wall time are verification costs, not token latency. |

This work shortens the Gate-1 path by closing exact T=1 layer-zero coefficient
arithmetic behind both current semantic descriptor configurations. It remains
outside the ordinary shipped-prefix microsequencer/decoder/view-resolver and
does not execute the downstream layer or model-token path.

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
python3 tools/extract_a3_hc_pre_t1_checkpoint.py
python3 tools/build_a3_hc_pre_t1_vectors.py
python3 tools/run_a3_hc_pre_t1_rtl_campaign.py
pytest -q tests/compiler/test_a3_hc_pre_t1_rtl.py
```

The campaign regenerates and byte-compares the vectors, runs the complete
matrix on both simulators, compares normalized summaries, and performs generic
Yosys elaboration. The retained result hashes every authoritative source,
vector, and simulator log.

## Remaining Gate-1 work

The shortest remaining Gate-1 path is:

1. connect this semantic-config wrapper to the ordinary shipped-prefix
   microsequencer, descriptor decoder, view resolver, and real memory ports;
2. extend the same arithmetic beyond T=1, first to the authenticated T=512
   block, the final T=320 block, and then all `390 * 512 + 320 = 200,000`
   prompt positions without changing reduction order;
3. connect the coefficient outputs through the remaining layer-zero branch,
   attention/MLP/residual state, then repeat through every transformer layer;
4. execute final RMS, LM head, deterministic selection, token append/KV-state
   advance, and first-EOS-or-exact-cap stopping;
5. compare every generated token ID, decoded natural/agentic text, stop reason,
   and absence of post-EOS work with the independent checkpoint oracle.

Only after step 5 closes Gate 1 may raw token-commit events from that identical
execution be converted with a characterized SKY130 or ASAP7 timebase and
assessed against the pre-frozen TPOT SLO at each governed batch size.

## Explicit nonclaims

The 4,112 FMA and 4,200 transcendental samples are not exhaustive over every
operand encoding. The integrated arithmetic evidence covers one authentic
T=1 position, not the full T=512/T=320 shapes or every one of the 391 prompt
blocks. It consumes a derived semantic configuration rather than the raw
records through the full shipped-prefix control path. This evidence does not
establish a complete transformer layer, checkpoint-backed full-model RTL
execution, output-token correctness, decoded-text quality, EOS behavior, the
complete 200,000-context transaction, architectural token latency, TPOT,
technology timing, power, area, or ROM-versus-HBM superiority.
