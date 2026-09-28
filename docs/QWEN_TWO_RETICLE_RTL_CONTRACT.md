# Qwen3-8B two-reticle RTL contract

This is the integration contract for the proposed Qwen3-8B package, based on
the 28 September 2026 architecture decision. It is an implementation plan,
not a measured package result. The package has two reticles, each allocated
6,144 lane groups, with every layer partitioned across the two dies (TP-2)
and reductions crossing a UCIe boundary. Both the ROM
design and its iso-area HBM-weight comparator use two reticles and eight HBM3E
stacks per package. Weights are signed INT8 with one BF16 scale per output
channel; KV is in HBM in both designs. Autoregressive decode uses `m=1` and
the DFlash verification path uses multiplier `m=5`. The tensor slices,
activation and partial-sum formats, exact quantization rounding and saturation,
and stack address map must be pinned before a package exactness claim.

`docs/ARCH_QWEN3_O4_RTL_SPEC.md` is the advisory O4 requirement and gap audit.
Its model says TP-2 is needed for the O4 rates; the best contiguous layer cut
falls to 5,960 autoregressive and 12,461 DFlash tokens/s. Those are model
figures, not package RTL measurements. The audit also identifies a mismatch
between its proposed post-accumulation INT8 scale order and the current
quality harness's per-product order. The deployed numerical contract remains
open until the quality and arithmetic paths agree.

## Current source boundary

The source audit is pinned to `e29c63e3`. The exact Qwen RTL gates currently
instantiate one reduced `G=4, SW=16` vector core. Its weight read port is
`G*W*16` bits of BF16 values (`rtl/hdc/ot_hdc_core_vector_weight.sv`), and its
physical KV path uses `ot_hdc_qwen_kv_system` with a four-pseudo-channel
behavioral HBM model. The long-context gates check one such core, not the
two-reticle package or the 6,144 groups per reticle.

`rtl/chip/ot_chip_die2x2.sv` is a reduced four-tile composition. It connects
512-bit tile mesh ports to `ot_phy_ucie` instances whose macro placement is
described by `tools/chip_assembly/floorplans.py`; there is no Qwen two-reticle
activation-handoff RTL or behavioral UCIe endpoint in this source. Its
`ot_chip_hdc_tile` uses a scalar core and a fixed `LWIN=8` KV window, so it
cannot serve as the current vector long-context package top.

## Logical token path

Under TP-2, each die owns a tensor slice of every layer. QKV and gate/up use
output-row slices; o and down use input-column slices and a rank-ordered
cross-die reduction. Embedding, lm_head and the drafter are also split. Each
die holds the KV heads for its slice on its local HBM stacks. The advisory O4
audit counts 73 exchanges per token across the pair; a single hidden-state
handoff at one layer cut cannot represent that schedule or its rate.

The logical UCIe endpoint must carry repeated tagged transfers for partial
reductions, token control and any activation payload. A transfer header must
identify at least transaction, user, token position, layer, operation, slot,
payload format and length, plus an end marker. The receiver may consume a
reduction only after every beat of that tagged transfer is accepted. A credit
or ready/valid interface must hold payload and metadata stable through
stalls, provide bounded buffering, and prove no beat is dropped, duplicated,
reordered within a transfer or attributed to another user, position or slot.
Reset and link errors need an explicit abort/replay rule before a multi-user
gate. Exact bit widths and packet layout remain open until the partial-sum
representation and UCIe endpoint are pinned. The advisory audit says the
current golden fold needs FP32 partials while the O4 rate model priced BF16
partials; the two must be reconciled before claiming the modeled rate.

The package controller owns token ordering and final output. A reticle must
not report `done` merely because its local layers drained: it must also prove
that its outgoing handoff or incoming final result was accepted. The package
gate must count pre-token boot separately from per-token core cycles and from
UCIe transfer/wait cycles. This prevents link latency from disappearing from
the end-to-end measurement.

## Weight and HBM interfaces

Signed INT8 weights and per-output-channel BF16 scales require a pinned
reference model and transport layout. Scale placement, quantization rounding
and saturation, INT8 product/dequantization order, and accumulation precision
must be fixed before a numerical gate. The RTL must unpack INT8 values and
apply the matching BF16 scale in the shared arithmetic lane; the current BF16
weight port and exact reduced BF16 oracle do not establish INT8 numerical
equivalence. ROM and HBM modes must use the same quantized tensors, layer
placement, arithmetic, ISA image, activation format, KV format, and UCIe
schedule. Only the weight supply changes.

Each die needs an address ownership map for its tensor-slice weights, K/V,
boot traffic, and any program or scratch traffic. The O4 model assigns four
of the eight package HBM3E stacks to each die; the RTL manifest must pin the
corresponding address and ownership map. K/V requests remain physical in both ROM and
HBM-weight modes. The HBM-weight comparator must arbitrate its weight and KV
requests over the assigned controllers with backpressure and response tags;
accepted, scheduled, delivered, and outstanding sectors are separate
counters. The ROM mode still pays the same physical K/V traffic. Neither
mode may claim production bandwidth or energy from the present behavioral
HBM timing model.

## Integration gates

1. Freeze the TP-2 tensor slices, embedding/drafter/final-head ownership,
   exact INT8/BF16 quantization arithmetic, partial-sum representation and
   four-stack-per-die address map in a versioned manifest. The manifest must
   have unique slice and HBM ownership, capacity bounds for 6,144 groups on each die, and a
   compiler-generated image for each reticle.
2. Prove a standalone UCIe handoff with variable latency, credit exhaustion,
   reset/abort, and two interleaved user/position tags. Compare every payload
   byte and all accepted/completed/queued counts.
3. Compose two reduced vector reticles around repeated TP-2 exchanges. Run one exact
   token, then consecutive tokens including a K-tile close, with local timed
   physical HBM K/V on both sides. Check logits, intermediate boundary
   cross-die partials, VM/KV state, cross-token V reads, and committed physical K
   bytes under deterministic link and HBM stalls.
4. Repeat the same image in ROM-weight and HBM-weight modes, changing only the
   weight source. Check identical numerical results and report link, weight,
   KV, and boot counters separately. Run correctness and performance gates
   for both autoregressive `m=1` and DFlash verify `m=5` using the same
   deployed INT8/BF16 arithmetic. The DFlash gate must record verification
   outcomes and accepted tokens as well as work spent on rejected candidates.
   Reduced-model cycle counters are not production package throughput.
   Extend to a long-context sequence only after the small pair passes.
5. Elaborate a parameterized 6,144-group-per-reticle top and run capacity,
   fanout, clock, reset, and package-pin checks. Representative tile and link
   routes are separate physical evidence; a reduced functional gate is not
   full-reticle timing closure.

Every gate records source, compiler image, model, and executable hashes plus
its exact accepted/completed traffic. A failure remains a pinned failure
record until a new source snapshot passes. The running 2047→2048 and 8191
single-core gates remain useful reduced functional controls; they do not
measure the two-reticle package.
