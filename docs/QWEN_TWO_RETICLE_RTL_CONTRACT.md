# Qwen3-8B two-reticle RTL contract

This is the integration contract for the proposed Qwen3-8B package, based on
the 28 September 2026 architecture decision. It is an implementation plan,
not a measured package result. The package has two reticles, each allocated
6,144 lane groups, with layers divided across a UCIe boundary. Both the ROM
design and its iso-area HBM-weight comparator use two reticles and eight HBM3E
stacks per package. Weights are signed INT8 with one BF16 scale per output
channel; KV is in HBM in both designs. Autoregressive decode uses `m=1` and
the DFlash verification path uses multiplier `m=5`. The layer cut, activation
format, exact quantization rounding and saturation, and stack allocation
remain open until the model and package rebaseline fixes them.

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

For a contiguous layer cut at layer `P`, reticle A executes its assigned
embedding and layers before `P`, sends the hidden state for one token, and
reticle B executes the remaining layers and final token selection. This
contiguous cut is a *proposed* minimum-transfer topology, not a fixed layer
assignment. The compiler must place every weight and layer-local KV segment
on the reticle that executes that layer. Normal decode should therefore
transfer activations, not the full KV cache, across UCIe. Any alternative
partition must declare its additional transfers before performance modeling.

One logical handoff consists of a header followed by the complete activation
vector. The header must identify at least the transaction, user, token
position, layer-cut revision, activation format, payload length, and an end
marker. The receiver may start the next layer only after accepting all beats
for that transaction. A credit or ready/valid interface must hold payload and
metadata stable through stalls, provide bounded buffering, and prove no beat
is dropped, duplicated, reordered within a transaction, or attributed to
another user/position. Reset and link error behavior needs an explicit
abort/replay rule before a multi-user gate. Exact bit widths and packet layout
are deliberately unset until the activation representation and UCIe endpoint
are selected.

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

Each die needs an address ownership map for its weights, K/V, boot traffic,
and any program or scratch traffic. The eight package HBM3E stacks require a
declared per-reticle allocation; four per reticle is a candidate, not an
assumption of this contract. K/V requests remain physical in both ROM and
HBM-weight modes. The HBM-weight comparator must arbitrate its weight and KV
requests over the assigned controllers with backpressure and response tags;
accepted, scheduled, delivered, and outstanding sectors are separate
counters. The ROM mode still pays the same physical K/V traffic. Neither
mode may claim production bandwidth or energy from the present behavioral
HBM timing model.

## Integration gates

1. Freeze the model cut, embedding and final-head ownership, exact INT8/BF16
   quantization arithmetic, activation format, and eight-stack address map in
   a versioned manifest. The manifest must have unique layer and HBM
   ownership, capacity bounds for 6,144 groups on each die, and a
   compiler-generated image for each reticle.
2. Prove a standalone UCIe handoff with variable latency, credit exhaustion,
   reset/abort, and two interleaved user/position tags. Compare every payload
   byte and all accepted/completed/queued counts.
3. Compose two reduced vector reticles around that handoff. Run one exact
   token, then consecutive tokens including a K-tile close, with local timed
   physical HBM K/V on both sides. Check logits, intermediate boundary
   activations, VM/KV state, cross-token V reads, and committed physical K
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
