# Independent target-format reference

This directory is outside compiler lowering and RTL. Its implementations may
share versioned interface definitions, but they do not call compiler image,
placement, microcode, schedule, or service-engine algorithms to calculate an
expected result.

`formats.py` is the first DeepSeek V4 target-precision slice. It provides exact
rational scalar semantics for:

- E2M1 values, RNE conversion, saturation, and the official low-nibble-first
  packed layout;
- E8M0 scales, including the reserved `0xff` poison value;
- FP8 E4M3FN classification and round-to-nearest-ties-to-even conversion;
- BF16 classification and binary32-to-BF16 conversion;
- direct exact-value BF16 RNE, exact IEEE binary32 decode/rounding, correctly
  rounded BF16 and binary32 reciprocal square root, and ordered fused-product
  accumulation;
- packed MXFP4 block decoding; and
- NUM-3.3 BF16 activation-block microscaling;
- 32-value MXFP4×FP8 routed block dots; and
- 128-value FP8×FP8 dense block dots.

The tests exhaust every E2M1, E8M0, E4M3FN, and BF16 code, exercise rounding,
saturation, poison, scale-selection, and packing boundaries, and compare every
E4M3FN encoding with the public RTL decoder. A separate development audit also
matched every E4M3FN, BF16, and E8M0 decode against the installed PyTorch dtype
implementation with zero differences. Binary32 tests include deterministic
round trips over 20,000 random finite encodings and cases where ordered
per-product accumulation intentionally differs from one final exact reduction.
A separate SM120 development audit compared E2M1 conversion for all 65,280
finite BF16 encodings with CUDA's native `cvt.rn.satfinite.e2m1x2.f32`. After
the governed positive-zero canonicalization, there were zero differences.

This closes neither `M1` nor numerical qualification. Matrix operators beyond
the qualified routed-MXFP4/shared-FP8 SwiGLU, dense FP8, index-head BF16,
router-score, compressor, confidence, grouped attention-output, and DSpark
main-conditioning projection paths, vector operators beyond the SwiGLU
nonlinear section, weighted and head RMS normalization,
target-hidden capture, and HC post-mixing, attention operators
beyond the qualified KV row-space composition, learned index scoring/top-k, and
sparse-attention boundary,
mutable attention-state operations beyond the qualified circular-window and
compressed-KV transactions, remaining routing and nonlinear operators,
real-checkpoint known answers, layer differentials, end-to-end logits, and task
quality remain open.
The earlier exact-integer evaluator remains fixture-only evidence.

`matrix.py` composes the scalar/block rules into complete `FP8_LINEAR`
semantics. It quantizes each BF16 activation block once, applies the released
128-by-128 E8M0 scale orientation, executes ordered 128-value FP8 block dots,
reduces block partials through the canonical balanced tree, and rounds the
binary32 result to BF16. It returns explicit activation-block and output-element
saturation counts. Tests cross the output scale-tile boundary and compare
multi-block randomized matrices with an independently assembled composition.
This does not yet provide a checkpoint-derived known answer or service-engine
opcode.

`swiglu.py` implements all 46 routed `MXFP4_SWIGLU` and shared `FP8_SWIGLU`
sites. It preserves the source's three BF16-output learned projections, the
released 128-value activation quantization block, the routed 32-value E8M0
weight-scale block, low-nibble-first MXFP4 packing, asymmetric clamp
(`up` in `[-10,10]`, `gate` upper-only at `10`), direct correctly rounded
binary32 logistic, separate SiLU/up/route binary32 multiplies, and one BF16
conversion before `w2`. Routed block partials add in increasing 32-value order;
the shared path reuses the qualified dense balanced tree unchanged. Every
resource validates before arithmetic and the immutable result has one commit.
Counters distinguish canonical payload capacity from logical per-command reads
and scalar work; none is a physical transaction, cycle, bandwidth, throughput,
energy, area, or PPA claim. Tests include complete reduced operators,
order-sensitive cancellation, clamp asymmetry, route placement, independent
composition, malformed/nonfinite/overflow rejection, and full-column selected
rows from all twelve hash-locked layer-0 routed/shared tensors. Those selected
rows are payload evidence, not a checkpoint-derived hidden activation, complete
official expert output, service-engine opcode, schedule, RTL, or model result.

The same module separately implements all 21 `BF16_LINEAR` index-head weight
projections. Official headers confirm every checkpoint matrix is `[64, 4096]`
BF16. Exact BF16 products accumulate in increasing K order with binary32 RNE at
each fused product-add, followed by one BF16 output conversion. Tests cover the
complete graph shape, an order-sensitive cancellation, subnormal and malformed
inputs, finite output saturation, binary32 overflow, independent randomized
composition, and native CPU/CUDA differentials. A governed full-width audit
matched all 64 CPU outputs; native SM120 tensor-core tiling differed in 27,
each by at most six same-sign BF16 encoding steps. This freezes target order; it
does not declare CUDA's backend-dependent tree incorrect.

`grouped_output.py` implements all 46 `GROUPED_OUTPUT_PROJECT` sites between
inverse RoPE and the downstream `wo_b` FP8 projection. It freezes the released
eight-group/eight-head-per-group orientation, increasing-feature binary32 FMA
order, one final BF16 conversion, contiguous tensor-parallel group ownership,
and group-major flattened alias. Public result records reconcile exact tuple
shape, alias, topology, counters, and numeric profile. Tests cover every legal
world-size/rank mapping, full 4,096-value reduction width, all four bounded
command extents, all four hash-locked MP=4 layer-0 canonical weight payloads,
and exact agreement with a separately implemented service arithmetic lane.
The locked corpus uses deterministic synthetic attention outputs and selected
weight rows; it is not complete `wo_a`, downstream `wo_b`, a collective, a
checkpoint-derived activation, physical execution, or performance evidence.

`dspark_main_project.py` implements the single `DSPARK_MAIN_PROJECT` graph
site. It fixes capture order 40→41→42, BF16 concatenation to width 12,288, the
complete `[4096,12288]` E4M3FN/E8M0 projection, and width-4,096 weighted RMS
normalization. Every resource code validates before exact-zero acceleration,
and counters retain the full declared semantic work. A separately implemented
service arithmetic lane matches a nonzero full-shape synthetic composition,
complete official resources at zero input for `T=1..4`, and real official
projection rows 0, 127, 128, and 4,095. None of those corpora is a
checkpoint-derived nonzero captured activation or artifact-driven service
execution, and logical counters are not physical bytes, cycles, bandwidth,
latency, throughput, energy, area, or PPA.

`normalization.py` implements the weighted `RMS_NORM` operation at all 251
Flash graph sites and all four observed widths. It widens BF16 input and BF16
checkpoint weights exactly, squares with binary32 RNE, reduces with the NUM-6.1
balanced tree, divides once, adds binary32 `0x358637bd`, applies correctly
rounded binary32 reciprocal square root, performs the two ordered pointwise
multiplies, and converts once to BF16. Tests retain mean-square and inverse-RMS
codes, cover signed zero, BF16 subnormals, finite saturation, overflow, every
qualified width, and an independently assembled randomized composition.

The same module separately implements all 46 unweighted `HEAD_RMS_NORM` sites
at width 512. It rounds squares immediately to BF16, widens them for the
NUM-6.1 binary32 reduction, converts the mean once to BF16, adds BF16 epsilon
`0x3586`, applies correctly rounded BF16 reciprocal square root, and rounds the
final unweighted multiply directly to BF16. Tests cover exact BF16
intermediates, direct-rounding behavior, signs, signed zero, subnormals,
malformed/nonfinite input, intermediate overflow, an independently assembled
composition, and native CPU/CUDA differentials.

A deterministic development audit used seed `0x524d534e41554449`, PyTorch
2.10.0+cu128, CUDA 12.8, and native SM120 on 16 rows per width. The explicit
balanced tree matched all 64 target mean-square codes on CPU and CUDA; the
source reduction differed in 30 CPU and 15 CUDA rows. Native `rsqrt` fed the
canonical means differed from correct RNE in 22 CPU and 14 CUDA rows, always by
one binary32 code. After positive-zero canonicalization, the complete source
expression differed in 22 of 92,160 CPU BF16 outputs and zero CUDA outputs.
These are bounded development observations, not a replacement for target RTL,
full-checkpoint, layer, or task-quality qualification.

For the head path, seed `0x48454144524d534e` covered 16 width-512 rows on the
same software and hardware. Canonical and ordinary source means matched all 16
target codes on CPU and CUDA. Native BF16 reciprocal square root differed in
one CPU row and zero CUDA rows; the complete expression differed in 427 of
8,192 CPU BF16 outputs and zero CUDA outputs. Every CPU difference was one
same-sign BF16 code after zero canonicalization. This is likewise bounded
development evidence, not a backend-equivalence guarantee.

`quantization.py` implements the complete indexer `FP4_QDQ` boundary. It
flattens leading dimensions into source-order rows, selects an independent
power-of-two E8M0 scale for every 32 BF16 values using the pinned binary32
reciprocal/bit-ceiling sequence, applies E2M1 RNE, and reconstructs BF16 through
the declared binary32 operations. It exposes internal scale and E2M1 codes for
checking even though the official in-place wrapper returns only BF16. Tests
cover every quantization midpoint, the unusual all-zero `0x01` scale, lower and
upper scale transitions, independent blocks, malformed shapes, nonfinite
input, and intermediate overflow. A development differential matched 2,047
successful random/boundary rows on native SM120 in scale, E2M1 code, and BF16
output; the single extreme-overflow row was rejected by the target fail-closed
rule.

The same module independently implements the complete KV `FP8_QDQ` boundary.
It consumes the non-RoPE prefix as source-order rows, selects an independent
power-of-two E8M0 scale for each 64 BF16 values using the pinned binary32 `1e-4`
floor, rounded `1/448`, and bit-ceiling sequence, applies finite E4M3FN RNE, and
reconstructs BF16 through the declared binary32 operations. The graph profile
fixes a 448-value prefix, seven blocks, and an untouched 64-value RoPE suffix.
Tests cover E4M3FN subnormal and normal midpoints, the lower and upper scale
transitions, independent blocks, malformed shapes, nonfinite input, and internal
overflow. A separate PyTorch 2.10.0/CUDA 12.8 audit on native SM120 compared
2,048 successful boundary/random blocks: all 2,048 scale bytes and all 131,072
E4M3FN and reconstructed BF16 values matched after governed signed-zero
canonicalization. Thirty-seven naturally sampled overflow candidates and an
explicit maximum-BF16 block were rejected; the native path independently
produced binary32 infinity for the explicit case.

`hadamard.py` implements the complete 128-point `HADAMARD_ROTATE` boundary used
for both index queries and compressed index KV. It widens BF16 exactly, applies
seven ascending-stride binary32 Sylvester butterfly stages, multiplies once by
the pinned binary32 scale `0x3db504f3`, and converts once to BF16. Tests fix
matrix orientation, rounding order, signed zero, subnormal preservation,
overflow, and malformed input. A separate native SM120 audit compared 1,024
rows against public `fast_hadamard_transform` v1.1.0: all 131,072 ordinary
outputs matched after positive-zero canonicalization. The audit also confirmed
the documented target adaptations: the native fast-math build flushes one
all-minimum-subnormal case to zero where NUM-3.6 preserves `0x000b`, and it emits
infinity for an extreme block that the target rejects.

`indexing.py` independently implements the three source-constructed integer
index tensors used by `WINDOW_INDEX`, `COMPRESSED_DENSE_INDEX`, and
`DSPARK_WINDOW_INDEX`. It preserves the pinned prefill/decode branch behavior,
circular-window order, compression-completion boundary, offsets, padding, and
DSpark history/draft address split. Inputs and signed-int32 output bounds fail
closed. These structural references do not implement learned index scoring,
top-k tie order, KV mutation, sparse attention, or any service-engine lowering.

`kv_window.py` implements every `KV_WINDOW_WRITE` site and the target-owned
retirement/valid-view operations needed to make the released circular cache
safe across requests. It preserves the official prefill split assignments and
decode slot `start_pos % 128`, while binding every fixed-capacity lane to an
exact lowercase SHA-256 session identity, active/tombstone status, absolute
next position, and monotonic uint64 version. Prefill establishes a fresh
session epoch, decode requires exact full-capacity version authority and one
shared active-prefix cursor, and removal retires only a trailing active suffix.
The valid view returns exactly `[max(0,N-128),N)` in chronological order and
excludes unused, inactive, or preserved stale capacity. Public result records
retain the complete prior state and source activation, reconstruct the exact
successor/view relation, and reconcile payload plus metadata counters. This is
a pure immutable semantic reference: it does not supply atomic service-level
compare-and-swap, `ATTENTION_KV_VIEW` composition, HBM placement, schedules,
cycles, RTL, or checkpoint-derived attention output.

`attention_kv_view.py` implements all 46 `ATTENTION_KV_VIEW` sites. Main
prefill retains complete current KV and appends only the valid compressed
prefix; main decode retains physical 128-row circular capacity and appends only
that prefix. DSpark decode instead appends the five current draft KV rows after
the physical main window—the main-conditioning KV row updates the window but is
not the draft suffix. Exact sessions, shared cursor, complete window versions,
current writes, compressed-view records, row widths, and finite payloads are
revalidated before an immutable result is returned. Explicit valid physical
indices make unused or preserved stale capacity nonselectable. The reference
does not construct attention indices, execute sparse-attention arithmetic,
authenticate producers, provide service-level atomicity, or make physical or
performance claims.

`lookup.py` implements the two pinned pure-gather paths. `TOKEN_EMBED` selects
global embedding rows while carrying BF16 as exact 16-bit encodings; this is
equivalent to the source vocabulary-shard masking and all-reduce because one
and only one shard owns a valid token. `HASH_ROUTE` selects the checkpoint's
ordered expert-ID row for each flattened token ID and intentionally preserves
duplicates. It does not implement router scoring, selected-weight gathering, or
expert dispatch.

`structural.py` implements the bit-preserving `HC_EXPAND` copy and the integer
noise-block construction that precedes `DSPARK_NOISE_EMBED`. The HC result
copies every BF16 encoding without arithmetic. The DSpark helper fixes the
current token at column zero and fills later draft columns with the pinned noise
token. The qualified composite then applies the shared global BF16 embedding
lookup and HC expansion without changing any payload bit. Main-hidden projection
remains a separate matrix operator.

`selection.py` resolves the source's intentionally unpinned `torch.topk` tie
behavior. The official release requires `torch>=2.10.0`, while PyTorch 2.10
states that tied indices are not stable. The target rule is therefore score
descending, then logical index ascending. Router scores use raw binary32
encodings; learned index scores use raw BF16 encodings. Both are compared as
exact rationals and NaNs fail closed. `BIASED_TOPK_ROUTE` performs one
binary32-rounded selection-bias add before this ordering; `INDEX_TOPK` applies
the BF16 causal completion mask, deterministic top-k, `-1` padding, and the
compressed-cache offset. Score formation is the separately qualified
`INDEX_SCORE` boundary in `index_score.py`; selection does not duplicate its
arithmetic.

`routing.py` implements `ROUTER_WEIGHT_NORMALIZE` over raw FP32 encodings. It
gathers unbiased scores in selected slot order, retains duplicate selection
slots, reduces the denominator with the NUM-6.1 canonical balanced tree, rounds
each division once, and rounds the subsequent route-scale multiplication once.
Zero denominators, negative scores, nonfinite values, malformed indices, and
overflow fail closed. This fixes a deterministic accelerator tree rather than
claiming that all PyTorch backends use one reduction order.

The same module separately implements all 46 `ROUTER_SCORE` projections.
Official headers confirm every router matrix is `[256, 4096]` BF16. The target
widens BF16 hidden state and weights exactly, executes increasing-K binary32 RNE
fused product-adds, and retains the binary32 result for the following score
function. Full-shape, order-sensitive, randomized, malformed, subnormal, and
overflow tests are retained. On a governed 64-output full-width corpus, native
CPU and SM120 reassociation differed from the explicit target in 63 and 62
outputs respectively, without a sign change and by at most 290 binary32 codes.

`sampling.py` implements the complete target contract for `SAMPLE` without
inventing an unrecorded CUDA RNG state. For finite binary32 logits and zero
temperature, it exactly applies the released first-index argmax rule. The
nonzero-temperature PyTorch/CUDA path fails closed when source equivalence is
requested because the release pins only `torch>=2.10.0`, not the generator,
post-`exponential_(1)` mapping, softmax implementation, or reduction order. A
separately named deterministic target adaptation accepts immutable positive
binary32 post-exponential draws, consumes them in row-major order, and freezes
every division, exponential, balanced softmax reduction, and race comparison.
Its entropy continuation, intermediate-array digests, numeric profile, and
logical work counters are immutable and atomically reconciled. This qualifies
the accelerator's explicit sampling boundary; it does not claim bit-exact
stochastic replay of the official CUDA program, RNG generation, a complete
generation loop, DSpark acceptance, checkpoint logits, or physical behavior.

`confidence.py` implements the single `CONFIDENCE_SCORE` projection. It
concatenates each BF16 final-DSpark hidden row before its BF16 Markov embedding,
widens the official `[1, 4352]` BF16 checkpoint weight exactly, and executes an
increasing-K binary32 RNE fused-product accumulation. The output remains
binary32; there is no bias, quantization, activation, or final BF16 conversion.
Tests cover the full five-position 4,096+256 graph profile, concatenation order,
rounding order, subnormal and malformed inputs, overflow, 200 independent
randomized compositions, and CPU/SM120 differentials. A separate audit using
the actual 8,704-byte official weight payload recorded only bounded same-sign
native reassociation differences; NUM-4.6 retains the hashes and counts.

`compression.py` implements all 62 paired `COMPRESS_PROJECT` sites. It widens
the BF16 hidden tensor and both BF16 checkpoint matrices exactly, executes the
KV projection followed by the independent gate-score projection, and retains
both outputs in binary32. The graph qualifies 21 main `[1024, 4096]`, 20 main
`[512, 4096]`, and 21 indexer `[256, 4096]` profiles for each projection role.
Tests cover orientation and output independence, increasing-K rounding,
subnormals, the full 4,096-column reduction, malformed/nonfinite input,
overflow, 200 independent randomized compositions, and CPU/SM120
differentials. A separate audit used the first four rows from six actual
official tensors spanning all three profiles; NUM-4.7 retains complete payload
and output hashes, source order, counts, and native reassociation bounds.

`compression_state.py` implements all 62 `COMPRESS_STATE_UPDATE` sites after
projection. It adds the official FP32 APE with one binary32 RNE operation,
retains incomplete prefill/decode windows, assembles complete ratio-four overlap
or ratio-128 groups, and emits an explicit `should_compress` predicate. Ratio
four keeps separate previous/current raw groups and reproduces the first-group
zero-KV/negative-infinity-score padding. Full prior state and all inputs validate
before immutable commit; inactive batches are preserved. New-session reset is
an explicit target transaction because the official method overwrites only
addressed rows and trusts its caller to maintain request identity and position.
Each lane carries a canonical session ID, exact next position, and monotonic
version; fresh prefill resets every active raw slot, while skipped, replayed, or
stale-session decode fails before a new immutable state is returned. Counters
distinguish projected input, APE, raw-state, metadata, reset, overlap, roll, and
pool-operand traffic without assigning those bytes to a physical memory.

`compression_pool.py` implements all 62 `COMPRESS_POOL` sites over the prepared
groups. It fixes finite numeric maximum, correctly rounded binary32 exponential,
NUM-6.1 balanced denominators and weighted reductions, binary32 RNE division and
multiplication, gradual underflow, and positive-zero output. Direct prepared-
state, prefill, and complete decode-window APIs agree on the three official
profiles. The latter two are functional-equivalence adapters; state ownership
remains in `compression_state.py`. The real-checkpoint audit in
`docs/DEEPSEEK_V4_COMPRESSOR_EVIDENCE.md` locks every official APE payload and
executes the unmodified official pool path on CPU and SM120.

`conversion.py` implements the 62 explicit `BINARY32_TO_BF16` boundaries for
the official `kv.to(dtype)` immediately after pooling. It validates finite
rank-three input, converts once with BF16 RNE and gradual underflow, counts
finite saturation and exact four-byte-read/two-byte-write logical traffic, and
commits an immutable result atomically. This prevents the binary32 pool output
from being passed silently into the BF16-only RMSNorm reference.

`compressed_kv.py` implements all 62 `COMPRESS_KV_WRITE` and
`COMPRESSED_KV_VALID_VIEW` sites after RMSNorm, position transform, and
activation QDQ. Prefill commits only the complete
`floor(sequence_length / ratio)` prefix; decode commits one row only at a ratio
boundary, but advances the session cursor and version on every token. Each lane
tracks active status, exact session, next position, valid-prefix length, and a
monotonic version; removed lanes retain a tombstone until reassignment. The
valid-view operation exposes only each exact active session's contiguous prefix,
never preserved stale capacity rows. These are accelerator adaptations because
the released PyTorch cache has no causal metadata. Payload and logical metadata
fields remain separate counters, and main and indexer caches remain distinct
state objects.

`index_score.py` implements all 21 `INDEX_SCORE` sites. It contracts BF16
FP4-QDQ query heads against BF16 compressed index KV with increasing-dimension
binary32 RNE accumulation, converts each dot once to BF16, canonicalizes the
BF16 ReLU zero, and applies each BF16 head weight after a direct multiplication
by binary32 scale `0x3c3504f3`. The resulting BF16 head contributions reduce in
ascending logical-head order with the NUM-6.1 tree and convert once to BF16.
The graph-qualified profile is 64 heads by 128 values at compression ratio four;
causal masking and top-k remain `INDEX_TOPK`. Tests cover the full profile,
rounding and tree discriminators, signed zero, subnormals, every finite
saturation boundary, binary32 overflow, empty short-prefill candidates, 200
independent randomized compositions, and malformed/nonfinite inputs. With seed
`0x494e44584e415449`, all 28 final BF16 outputs matched both PyTorch
2.10.0+cu128 CPU and CUDA 12.8 SM120 after positive-zero canonicalization. This
is a bounded synthetic differential, not checkpoint or sparse-attention
closure.

`transcendental.py` defines a general correctly rounded binary32 exponential
without calling host `libm`. Exact rational Taylor bounds enclose `exp(x)` for
negative arguments; positive arguments use the monotone reciprocal enclosure
of `exp(-x)`. The interval precision doubles until both endpoints round to one
binary32 code. Gradual underflow is legal and finite overflow poisons. Fixed
answers and 68 independently evaluated 220-digit `decimal` cases cover both
signs, underflow, signed zero, and the positive overflow boundary.

`sparse_attention.py` implements all 46 `SPARSE_ATTENTION` sites. It preserves
the official block-64 gather order, `-1` padding, duplicate selected rows,
BF16 Q/K/V inputs, binary32 online maximum and denominator, the learned
binary32 sink logit, and the one BF16 probability conversion before AV. The
target fixes increasing-dimension QK and increasing-slot AV product-add order,
NUM-6.1 balanced 64-lane score sums, separate rescale multiply/add boundaries,
general CR32 sink exponential, and one final BF16 conversion. These are
deterministic target adaptations where TileLang leaves a backend tree or
approximation unspecified.

Traffic counters keep storage tiers distinct. For every valid selected slot,
the source gather reads one 512-value BF16 mutable-KV row, exactly 1,024 logical
bytes. A duplicate is another selected occurrence and another logical read;
explicit `-1` and implicit tail lanes consume block-compute lanes but read zero
KV bytes. Index, query, sink, output, valid-KV, and padded-work counters are
reported separately. They are logical source traffic, not a claim about HBM
transactions, caches, coalescing, cycles, or achieved bandwidth.

The canonical MP=4 checkpoint audit concatenated `layers.0..42` and then
`mtp.0..2`, each in rank `0..3` order. All 184 sink shards contained 2,944
finite binary32 values (11,776 bytes), SHA-256
`2f93e2a35c5ad1dbd4aaff353a46082d6811e7b896bf388583bd05e023c2844f`.
The range was `-2.4585509300231934` (`0xc01d58e6`) through
`2.4927473068237305` (`0x401f892c`), with 2,680 positive, 264 negative, and no
zero values. This qualifies the real sink payload only; real Q/KV layer outputs
and complete attention known answers remain open.

With seed `0x5350415253454456`, a bounded source-structure differential exercised
two blocks, holes, and duplicates. All 96 BF16 outputs matched PyTorch
2.10.0+cu128 on CPU and CUDA 12.8/SM120.

The exact released kernel was then executed through TileLang 0.1.8 on the same
CUDA/SM120 stack with all broad transitive dependencies and wheel hashes
recorded in `docs/DEEPSEEK_V4_SPARSE_ATTENTION_EVIDENCE.md`. The exact-eighths
corpus matched all 8,192 BF16 outputs. A broader BF16 corpus differed in three
of 8,192 outputs, each by one same-sign BF16 encoding step, consistent with the
declared Tensor Core/reduction/`expf` versus deterministic-target boundary. The
audit does not establish a service-engine opcode, KV transaction path,
schedule, cycle count, or PPA.

`dispatch.py` implements `EXPERT_DISPATCH`. It applies the source's row-major
batch/sequence flattening, emits only nonempty expert groups in ascending
logical expert-ID order, and orders each group's assignments by flattened token
then selected slot. BF16 hidden rows and binary32 route weights are copied
bit-for-bit. Duplicate expert IDs for one token remain distinct assignments, so
later expert execution/reduction cannot silently discard a selected slot.
Malformed shapes, out-of-range experts, or nonfinite payloads fail closed. A
known answer reuses all 48 expert IDs from the independently checked official
lookup slice in `docs/DEEPSEEK_V4_LOOKUP_EVIDENCE.md`.

The same module implements all 46 `EXPERT_REDUCE` sites. Routed BF16 outputs
remain aligned to the qualified dispatch, duplicate slots reduce first in
selected-slot order, and distinct experts reduce in ascending logical ID order
with the NUM-6.1 tree. The shared BF16 expert is added last with one binary32
RNE addition, followed by one BF16 conversion. Forged dispatches, malformed or
nonfinite outputs, and intermediate overflow fail closed; final finite BF16
saturation is counted. A native PyTorch 2.10.0+cu128 witness confirms why this
is a governed target rule: advanced-index mutation discarded the first of two
duplicate contributions on CPU and the second on SM120. A separate seeded
no-duplicate audit matched both backends in all 2,048 BF16 outputs.

`vector.py` implements `TARGET_HIDDEN_CAPTURE` and `HC_POST` over finite BF16
encodings and binary32 coefficients. Capture widens the four official HC
streams, reduces the source axis with the NUM-6.1 balanced tree, divides once,
and converts once to BF16. HC post-mixing interprets `comb[source][destination]`,
rounds each branch/residual product once, reduces residual sources with the same
tree, adds the branch contribution, and converts once to BF16 while counting
finite output saturation. Shape mismatch, nonfinite input, and intermediate
overflow fail closed. Both trees are deterministic target adaptations rather
than claims about incidental backend reduction order.
