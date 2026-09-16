`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Small ABI 3.0 sequencer-to-engine bridge.
//
// This is deliberately a bounded production profile, not a claim that every
// shipped operator has an RTL datapath.  It admits the exact dense one-index
// DMA.GATHER, BF16 TENSOR.EMBED_LOOKUP, Qwen BF16 VECTOR.RMS_NORM and the
// descriptor-driven layer-zero query/key/value TENSOR.MATMUL family, Qwen
// weighted VECTOR.HEAD_RMS_NORM, Qwen whole-head VECTOR.ROPE, and DeepSeek
// stride-zero DMA.TRANSFER forms at the head of the shipped decode programs.
// EMBED_LOOKUP and TRANSFER are row movements and lower internally to the
// existing index mover; both RMSNorm forms use the same exact row-configured
// buffered arithmetic slice, MATMUL reuses the qualified ABI 3.0 MAC lane,
// and RoPE is adapted to the unchanged qualified Qwen RoPE datapath.  The
// sequencer continues to observe each original opcode and descriptor.
//
// Six further families are admitted, and each is one the governed Qwen decode
// program actually issues -- VECTOR.ADD (PCs 44 and 62), VECTOR.SILU_MUL (PC
// 56), DMA.SCATTER (PCs 32 and 35), ATTENTION.GQA (PC 38), SELECTION.ARGMAX
// (PC 70) and SELECTION.TOKEN_APPEND (PC 72).  They share one admission walk
// rather than one state chain each: the operator record is checked, every
// bound TENSOR_VIEW is fetched in slot order into a per-slot register file,
// the NUMERIC record is checked against the family's frozen contract digest,
// and only then is the family's shape predicate evaluated over the captured
// slots.  Nothing is guessed from a convenience field.
//
// PLACEMENT IS OBJECT-ADDRESSED, FOR EVERY OPERAND AND EVERY RESULT OF EVERY
// FAMILY, THROUGH ONE TABLE.  There used to be ten placement surfaces here --
// six per-role object tables, three unkeyed single bases, and an append
// cursor -- and they could not express a whole transformer layer.  The rule
// now has no exceptions:
//
//     address = cfg_place_base_N of the view's own primary object
//               + the sequencer's resolved element offset for that slot
//
// Three consequences, and each was a separate defect before:
//   * an object has ONE base.  The old surfaces bound the same object through
//     several ports -- a layer's trunk activation is a MATMUL input, an
//     RMS_NORM input, a RoPE input, a mapped operand and a result -- and
//     nothing made those agree.  A table that names an object twice is a
//     DESCRIPTOR trap at admission (``placement_table_unique``), so the
//     disagreement cannot be configured at all rather than being trusted.
//   * a REWRITE is expressible.  The seven original families used to write at
//     ``cfg_output_base + result_word_cursor``: every write got a fresh
//     address, so an object written twice occupied two addresses and a later
//     read of it read the wrong one.  A layer writes 19 intermediates into 10
//     buffers and rewrites 4 of them, so the cursor could not run one.  The
//     cursor is gone; a result lands at its object's base, and a second write
//     to that object lands where the first one did, which is what the
//     dependence table's WAW ranges (§3.6) already describe.
//   * the surface is one number, not ten.  ``cfg_place_object_N`` /
//     ``cfg_place_base_N`` for N in 0..31 -- sized in the header note below.
//
// An object the table does not name is a DESCRIPTOR trap, never a guess.
// Completion is returned only after the datapath finishes.
//
// The six mapped families remain separately gated by
// ``cfg_extended_placement_valid``: that flag says this instantiation admits
// them at all, and it is not what supplies their addresses.  The bank a base
// lives in is still chosen by the reading slot (``m0_reads_result``,
// ``m1_reads_result``, ``m1_reads_matmul_weight``), so two objects in
// different banks may share a base value; one object in two banks may not,
// and no shipped program asks for it.
// Every other opcode returns a precise CAPABILITY trap.  Malformed metadata
// returns a DESCRIPTOR trap, and a datapath failure returns an ENGINE trap.
//
// The descriptor port is independent of the sequencer's descriptor port.  A
// real descriptor store may arbitrate those reads; the verification top uses
// two registered read ports over one immutable image.  Operand addresses are
// compact verification-bank addresses.  Geometry, dtype, arity, permissions,
// resolved extents and the exact numeric-contract digest all come from the
// ABI descriptors and the sequencer's resolved-view stream.
// ---------------------------------------------------------------------------
module ot_a3_engine_issue_bridge #(
    // The attention geometry, forwarded to ot_a3_qwen_gqa.  Defaults are
    // Qwen3-8B's, so every existing instantiation is unchanged.  Rung G1f's
    // reduced regression configuration needs 8 query heads of 16 over 2 KV
    // heads with the scale that head width implies; ot_a3_vector_rms_norm needs
    // no parameter here because its shape check admits any width whose
    // reciprocal is exact.
    parameter integer GQA_QUERY_HEADS = 32,
    parameter integer GQA_KV_HEADS    = 8,
    parameter integer GQA_HEAD_WIDTH  = 128,
    parameter [31:0]  GQA_SCALE_CODE  = 32'h3db5_0000,

    //: MODEL GEOMETRY, not a property of this bridge.
    //:
    //: These four were localparams frozen to the two shipped checkpoints, which
    //: made the admission rule reject any other model's embedding table on
    //: shape alone -- a control-path limit with no datapath reason behind it.
    //: A vocabulary size is a deployment fact; the engine that moves the row
    //: does not care what it is.  Defaults reproduce the shipped values exactly,
    //: so every existing instantiation is unchanged.
    parameter [31:0]  EMBEDDING_WIDTH     = 32'd4096,
    //: Two admitted vocabularies, because one bridge serves both shipped
    //: checkpoints.  A deployment that needs only one may set both alike.
    parameter [31:0]  QWEN_VOCABULARY     = 32'd151936,
    parameter [31:0]  DEEPSEEK_VOCABULARY = 32'd129280,

    //: DOES TENSOR.EMBED_LOOKUP ACTUALLY LOOK ANYTHING UP?
    //:
    //: With this at 0 -- the default, and what every retained vector set was
    //: recorded against -- the embedding row address is
    //: ``cfg_embedding_source_base + embedding_launch_count * EMBEDDING_WIDTH``:
    //: a legacy unkeyed base advanced by a LAUNCH COUNTER.  The row that comes
    //: back is whichever one the harness planted for that launch, so the
    //: operator verifies a row movement and the token id is never read.  Feed
    //: the same program two different token ids and it emits the same logits.
    //:
    //: With it at 1 the row is ``<table object's placement base> + token *
    //: EMBEDDING_WIDTH``, where ``token`` is the value the operator's own index
    //: view resolves to, read from memory before the engine starts.  That is an
    //: embedding lookup.  It is opt-in because the retained vectors place rows
    //: for the counter form and would otherwise all move at once.
    parameter integer EMBEDDING_TOKEN_INDEXED = 0,

    //: WHERE DOES A GATHER READ FROM?
    //:
    //: At 0 -- the default, and what every retained vector set was recorded
    //: against -- a DMA.GATHER's source address is
    //: ``cfg_source_base + dma_gather_launch_count * cfg_source_launch_stride``:
    //: the same legacy unkeyed base as the embedding's, advanced by a launch
    //: counter, and it ignores the placement table entirely.  The object the
    //: operator's own view names is validated and then not used to address
    //: anything.  A harness that plants the right rows at those strides gets
    //: right answers; one that does not reads whatever is at the base.
    //:
    //: At 1 the source address is the slot-1 object's placement base plus the
    //: offset its view resolves to, and the read is routed to the result bank.
    //: Both halves are needed together: a gather that selects a row the program
    //: just computed must address it by object AND find it where results live.
    //: A static gather source is then staged into the result bank too, which is
    //: a harness bank-routing choice -- architecturally there is one address
    //: space and the placement table already gives every object a base in it.
    parameter integer GATHER_PLACEMENT_ADDRESSED = 0,

    //: THE LARGEST RESOLVED SEQUENCE EXTENT THIS INSTANTIATION ADMITS.
    //:
    //: The golden device issues the SAME 83 launches for a prefill as for a
    //: decode; what differs is the span each one covers -- the sequencer's
    //: resolved view extent on the sequence axis, 1 for a decode row and S for
    //: an S-token prompt.  Sixteen admission clauses used to compare that
    //: extent against the literal 1, which refused every span but one, and the
    //: engine configuration below derived one row from the same literal.  Both
    //: now read the resolved extent and are bounded by this parameter instead.
    //:
    //: The default is 1, so every existing instantiation admits exactly the set
    //: it admitted before (``span >= 1 && span <= 1`` IS ``span == 1``) and
    //: configures exactly the same single row.  Raising it costs the result
    //: buffers the all-or-nothing engines need -- ot_a3_qwen_gqa's
    //: MAX_QUERY_SPAN output buffer and ot_a3_vector_rms_norm's row ceiling,
    //: both forwarded from here -- and nothing else: no datapath is sized by it.
    parameter integer MAX_SEQUENCE_SPAN = 1,

    //: ROUTE.WEIGHT_NORMALIZE's per-group slot count, which is the routing
    //: gate's k. The shipped operators carry 6 and V4.1's gate is also 6; the
    //: default matches ot_a3_route_weight_normalize's own MAX_SLOTS, so the
    //: admission rule is the engine's real limit rather than a pin at the one
    //: value that happens to ship.
    parameter integer WEIGHT_NORMALIZE_MAX_SLOTS = 8,
    //: How many correctly-rounded dividers the normalizer gets. One group costs
    //: ceil(slots / DIVIDERS) * 32 cycles in division against 5 * (slots - 1)
    //: in the fold, so this is the only throughput knob that matters. One is
    //: the small-area default.
    parameter integer WEIGHT_NORMALIZE_DIVIDERS = 1,

    //: ROUTE.WINDOW_INDEX's slots per query row -- the sliding window's width in
    //: the output view. The shipped operators carry 128. Parameterised for the
    //: same reason every other geometry here is: a pin at the one shipped value
    //: is a control-path limit with no datapath reason behind it.
    parameter integer WINDOW_INDEX_MAX_SLOTS = 128,

    //: ROUTE.BIASED_TOPK's k, bounded by ot_a3_route_biased_topk's own MAX_K.
    //: The shipped gate selects 6 of 256 (V4.1: 6 of 384).
    parameter integer BIASED_TOPK_MAX_K = 8,

    //: REDUCTION.EXPERT_SUM's expert count, bounded by this bridge's FOUR
    //: operand read ports rather than by the engine, which is parameterised
    //: wider. Raising it requires a wider operand surface, not a bigger number.
    parameter integer EXPERT_SUM_MAX_EXPERTS = 4,

    //: IS THE INDEX OPERAND OF A GATHER OR AN EMBED LOOKUP ADDRESSED BY ITS OWN
    //: VIEW?
    //:
    //: At 0 -- the default, and what every retained vector set was recorded
    //: against -- the index address of DMA.GATHER and TENSOR.EMBED_LOOKUP is
    //: ``cfg_index_base + real_launch_count``: a LAUNCH COUNTER, which ignores
    //: the operator's own index view.  One index word per launch is all such a
    //: base can name, so a span of S has nowhere to read S indices from, and
    //: even at S=1 the word it reads is whatever the harness planted for that
    //: launch rather than the one the view resolves to.
    //:
    //: At 1 the index address is the slot-0 object's placement base plus the
    //: element offset that slot resolves to, and S consecutive index words are
    //: read from there -- which is what makes ``DMA.GATHER`` select the row its
    //: index view names and ``TENSOR.EMBED_LOOKUP`` embed S prompt tokens.  The
    //: table a lookup indexes is then addressed by object with no token
    //: pre-multiplied into it, because the mover applies the index itself.
    parameter integer INDEX_VIEW_ADDRESSED = 0,

    //: THE RMSNorm OPERATING PROFILE, forwarded.  Defaults are the engine's own
    //: defaults, so at MAX_SEQUENCE_SPAN == 1 the forwarded values are the ones
    //: the engine would have chosen and nothing moves.  A span of S normalises
    //: S times as many rows in one launch, so the row ceiling and the result
    //: buffer are the profile scaled by the span bound -- derived, not a second
    //: hand-kept constant.
    parameter [31:0] RMS_PROFILE_MAX_COUNT   = 32'd4096,
    parameter [31:0] RMS_PROFILE_MAX_ROWS    = 32'd32,
    parameter [31:0] RMS_PROFILE_MODEL_WIDTH = 32'd4096,
    parameter [31:0] RMS_PROFILE_HEAD_WIDTH  = 32'd128,

    //: HOW MANY OBJECTS THIS INSTANTIATION CAN PLACE.
    //:
    //: The placement table is a memory, not a register file, and this is its
    //: depth.  It must be a power of two.  64 is the default because the 32
    //: legacy configuration ports below can bind at most 32 objects and an
    //: open-addressed table wants headroom: measured over Qwen3-reduced's own
    //: 32 object ids, 32 entries is a 100%-loaded table whose worst probe is
    //: 21 and whose mean is 3.62, while 64 entries probe 5 in the worst case
    //: and 1.28 on average.  So the default admits exactly the set the 32
    //: ports could ever express and no existing elaboration says anything.
    //:
    //: A DeepSeek deployment says something.  Measured from the certified
    //: images, deepseek-v41-flash-rom-wafer-2 places 675 distinct objects
    //: (ids 1..9,442), deepseek-v41-flash-rom-array-64 678, and
    //: deepseek-v4-flash-rom 264, against Qwen3-reduced's 32.  2,048 holds
    //: any of them at or below 33% load.
    parameter integer PLACE_ENTRIES = 64
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          clear,

    // Sequencer completion interface.
    input  wire          issue_valid,
    output wire          issue_ready,
    output wire          issue_fault,
    output wire [15:0]   issue_trap_class,
    // The completion record's EOS reason byte for THIS completion (wire
    // format section 7, byte 108).  Valid with issue_ready and non-zero only
    // on a clean SELECTION.TOKEN_APPEND, which is the only operator the ABI
    // gives one (operator conventions section 8).  ``selected_eos_reason``
    // below is the sticky register a checker reads at the end of a run; this
    // is the per-completion value the control plane latches its session
    // retirement from, and the two are not interchangeable -- the sticky one
    // updates a cycle late and would retire the session on the wrong
    // completion.
    output wire [7:0]    issue_eos_reason,
    input  wire [7:0]    issue_family,
    input  wire [7:0]    issue_sub,
    input  wire [31:0]   issue_descriptor_id,
    input  wire [31:0]   issue_index,

    // Resolved operand observation, emitted before issue.
    input  wire          view_valid,
    input  wire [31:0]   view_descriptor_id,
    input  wire [2:0]    view_slot,
    input  wire [31:0]   view_extent,
    input  wire [7:0]    view_extent_axis,
    input  wire [63:0]   view_element_offset,
    input  wire [7:0]    view_rank,

    // Immutable descriptor-store read port, one-cycle response.
    output reg           desc_req,
    output reg  [31:0]   desc_id,
    //: The RAW port.  Admission does not look at it directly: a descriptor
    //: names an object, the object's base now comes from a memory read rather
    //: than from a combinational compare against 32 ports, and the checks
    //: below need both at once.  So the record is HELD and the placement probe
    //: is launched from it; ``desc_valid`` / ``desc_data`` / ``desc_fault``
    //: further down are the held record, presented the cycle the probe
    //: answers.  Every admission clause reads those and is unchanged.
    input  wire          desc_rd_valid,
    input  wire          desc_rd_fault,
    input  wire [1535:0] desc_rd_data,

    // Per-transaction compact verification-bank placement.  The first
    // supported operation uses one index word.  Gathers advance through the
    // generated-row source region by the stated stride; embeddings use the
    // separately packed checkpoint-row region.  These four name staged
    // REGIONS that the vehicle sweeps by launch counter rather than ABI
    // objects, and no operand of a transformer layer is drawn from them.
    input  wire [31:0]   cfg_index_base,
    input  wire [31:0]   cfg_source_base,
    input  wire [31:0]   cfg_source_launch_stride,
    input  wire [31:0]   cfg_embedding_source_base,
    input  wire [31:0]   cfg_transfer_index_base,
    input  wire [31:0]   cfg_transfer_source_base,

    // The object placement table.  Each entry binds one ABI object id to its
    // compact verification-bank base; an object no entry names is refused,
    // and there is no default base.  This is the ONLY placement surface for
    // operands and results.
    //
    // SIZED FROM MEASURED DEMAND, not from a round number.  The distinct ABI
    // objects the governed decode program's issued operators name, derived
    // from each deployment's own descriptors by
    // tools/build_abi3_g1b_layer_closure.py: 32 on the ROM lowering and 31 on
    // the HBM lowering over the whole program, 23 over one transformer layer
    // on both, 26 over the span that reaches the layer's end and 9 over the
    // head span.  32 entries is the maximum of those, so the headroom is 9
    // entries over the layer this vehicle must place and NONE over the whole
    // program on the ROM lowering.  A program that names a 33rd object does
    // not mis-address it; it fails admission with a DESCRIPTOR trap on the
    // first operand the table cannot resolve.
    //
    // ``cfg_extended_placement_valid`` states that this *instantiation*
    // admits the six mapped families at all.  It is not a switch for turning
    // correctness off and it is not what supplies an address: an instance
    // that has not bound the table has no operand addresses for ANY family
    // and refuses each of them where it needs one.  An unconnected input
    // reads as z or 0 and both take the else branch, so an integration that
    // has not wired this keeps its previous refusals rather than acquiring a
    // half-configured placement.
    input  wire          cfg_extended_placement_valid,
    input  wire [31:0]   cfg_place_object_0,
    input  wire [31:0]   cfg_place_base_0,
    input  wire [31:0]   cfg_place_object_1,
    input  wire [31:0]   cfg_place_base_1,
    input  wire [31:0]   cfg_place_object_2,
    input  wire [31:0]   cfg_place_base_2,
    input  wire [31:0]   cfg_place_object_3,
    input  wire [31:0]   cfg_place_base_3,
    input  wire [31:0]   cfg_place_object_4,
    input  wire [31:0]   cfg_place_base_4,
    input  wire [31:0]   cfg_place_object_5,
    input  wire [31:0]   cfg_place_base_5,
    input  wire [31:0]   cfg_place_object_6,
    input  wire [31:0]   cfg_place_base_6,
    input  wire [31:0]   cfg_place_object_7,
    input  wire [31:0]   cfg_place_base_7,
    input  wire [31:0]   cfg_place_object_8,
    input  wire [31:0]   cfg_place_base_8,
    input  wire [31:0]   cfg_place_object_9,
    input  wire [31:0]   cfg_place_base_9,
    input  wire [31:0]   cfg_place_object_10,
    input  wire [31:0]   cfg_place_base_10,
    input  wire [31:0]   cfg_place_object_11,
    input  wire [31:0]   cfg_place_base_11,
    input  wire [31:0]   cfg_place_object_12,
    input  wire [31:0]   cfg_place_base_12,
    input  wire [31:0]   cfg_place_object_13,
    input  wire [31:0]   cfg_place_base_13,
    input  wire [31:0]   cfg_place_object_14,
    input  wire [31:0]   cfg_place_base_14,
    input  wire [31:0]   cfg_place_object_15,
    input  wire [31:0]   cfg_place_base_15,
    input  wire [31:0]   cfg_place_object_16,
    input  wire [31:0]   cfg_place_base_16,
    input  wire [31:0]   cfg_place_object_17,
    input  wire [31:0]   cfg_place_base_17,
    input  wire [31:0]   cfg_place_object_18,
    input  wire [31:0]   cfg_place_base_18,
    input  wire [31:0]   cfg_place_object_19,
    input  wire [31:0]   cfg_place_base_19,
    input  wire [31:0]   cfg_place_object_20,
    input  wire [31:0]   cfg_place_base_20,
    input  wire [31:0]   cfg_place_object_21,
    input  wire [31:0]   cfg_place_base_21,
    input  wire [31:0]   cfg_place_object_22,
    input  wire [31:0]   cfg_place_base_22,
    input  wire [31:0]   cfg_place_object_23,
    input  wire [31:0]   cfg_place_base_23,
    input  wire [31:0]   cfg_place_object_24,
    input  wire [31:0]   cfg_place_base_24,
    input  wire [31:0]   cfg_place_object_25,
    input  wire [31:0]   cfg_place_base_25,
    input  wire [31:0]   cfg_place_object_26,
    input  wire [31:0]   cfg_place_base_26,
    input  wire [31:0]   cfg_place_object_27,
    input  wire [31:0]   cfg_place_base_27,
    input  wire [31:0]   cfg_place_object_28,
    input  wire [31:0]   cfg_place_base_28,
    input  wire [31:0]   cfg_place_object_29,
    input  wire [31:0]   cfg_place_base_29,
    input  wire [31:0]   cfg_place_object_30,
    input  wire [31:0]   cfg_place_base_30,
    input  wire [31:0]   cfg_place_object_31,
    input  wire [31:0]   cfg_place_base_31,

    // -- the placement table's LOAD PORT ---------------------------------
    // The 32 ports above cannot express a model.  A deployment with more
    // objects than that loads its bindings here, one per accepted cycle, the
    // way the program store, the descriptor store and the symbol file are
    // loaded -- and into THE SAME TABLE, through the same hash, the same
    // probe and the same uniqueness detection.  There is no second lookup
    // surface, which is the failure this module's header note is about.
    //
    // A load is accepted on ``place_ld_en && place_ld_ready``.  The FIRST
    // accepted load LOCKS the surface: from then on the legacy ports are not
    // consulted and must read NO_ID, because a table built from both at once
    // is two statements about one object's base.  A non-NO_ID legacy port
    // after a load sets ``place_surface_conflict`` and the bridge refuses the
    // transaction exactly as it refuses a table that names an object twice.
    input  wire          place_ld_en,
    input  wire [31:0]   place_ld_object,
    input  wire [31:0]   place_ld_base,
    output wire          place_ld_ready,
    // Observability: bindings the table holds, and why it was refused.
    output wire [31:0]   place_bound_count,
    output wire          place_bound_twice,
    output wire          place_overflowed,
    output wire          place_surface_conflict,

    // The request's active context length, checked against the position the
    // scatter and attention index views actually resolve to; the compact KV
    // bank's fixed K-to-V plane stride in rows, which does not move as the
    // context grows; and the bound GENERATION_POLICY with the authenticated
    // request bound and the tokens already produced.
    input  wire [31:0]   cfg_context_length,
    input  wire [31:0]   cfg_kv_plane_rows,
    input  wire [31:0]   cfg_generation_policy_id,
    input  wire [31:0]   cfg_request_max_new_tokens,
    input  wire [31:0]   cfg_generated_before,

    // Operand/result ports of the integrated engine array.
    output wire          m0_rd_en,
    output wire [31:0]   m0_rd_addr,
    input  wire [31:0]   m0_rd_data,
    output wire          m1_rd_en,
    output wire [31:0]   m1_rd_addr,
    input  wire [31:0]   m1_rd_data,
    output wire          m2_rd_en,
    output wire [31:0]   m2_rd_addr,
    input  wire [31:0]   m2_rd_data,
    output wire          m3_rd_en,
    output wire [31:0]   m3_rd_addr,
    input  wire [31:0]   m3_rd_data,
    output wire          out_we,
    output wire [31:0]   out_addr,
    output wire [31:0]   out_data,
    output wire          m0_reads_result,
    output wire          m1_reads_result,
    output wire          m1_reads_matmul_weight,

    // Non-control observation for the focused checker.
    output wire          engine_busy,
    output wire [7:0]    engine_error_code,
    output wire [31:0]   engine_result_count,
    output wire [31:0]   engine_work_count,
    output reg  [31:0]   real_launch_count,
    output reg  [31:0]   dma_gather_launch_count,
    output reg  [31:0]   embedding_launch_count,
    output reg  [31:0]   rms_norm_launch_count,
    output reg  [31:0]   head_rms_norm_launch_count,
    output reg  [31:0]   rope_launch_count,
    output reg  [31:0]   dma_transfer_launch_count,
    output reg  [31:0]   matmul_launch_count,
    output reg  [31:0]   vector_add_launch_count,
    output reg  [31:0]   vector_silu_mul_launch_count,
    output reg  [31:0]   dma_scatter_launch_count,
    output reg  [31:0]   attention_gqa_launch_count,
    output reg  [31:0]   selection_argmax_launch_count,
    output reg  [31:0]   selection_token_append_launch_count,
    output reg  [31:0]   selected_token,
    output reg  [31:0]   selected_tie_multiplicity,
    output reg  [7:0]    selected_eos_reason,
    output reg  [31:0]   capability_fault_count,
    output reg  [31:0]   descriptor_fault_count,
    output reg  [31:0]   engine_fault_count,
    output reg  [31:0]   last_response_index,
    output reg  [7:0]    last_response_family,
    output reg  [7:0]    last_response_sub,
    output reg  [31:0]   last_response_descriptor_id
);
    //: Set +OT_BRIDGE_TRACE=1 to report which descriptor check rejected.
    //: Sites are numbered in source order, so `grep 'site=%0d", <n>'` lands
    //: on the check that refused.  Several sites also print the fields they
    //: latched, because twice a predicate looked satisfiable on paper and the
    //: register feeding it was a state behind.
    reg trace_bridge = 1'b0;
`ifndef YOSYS
    // Yosys 0.68 has no $test$plusargs and refuses the whole file on it, so
    // the simulation-only plusarg probe is hidden from synthesis; trace_bridge
    // keeps its 1'b0 initialiser there and every trace branch folds away.
    initial if ($test$plusargs("OT_BRIDGE_TRACE")) trace_bridge = 1'b1;
`endif

    localparam [31:0] NO_ID = 32'hffff_ffff;
    localparam [31:0] DESC_MAGIC = 32'h4433_4154;
    localparam [7:0] TYPE_MAJOR = 8'd1;
    localparam [7:0] TYPE_MINOR = 8'd0;
    localparam [15:0] DESC_TENSOR_VIEW = 16'h0002;
    localparam [15:0] DESC_NUMERIC = 16'h0003;
    localparam [15:0] DESC_OPERATOR = 16'h000a;
    localparam [15:0] DESC_GENERATION_POLICY = 16'h000b;
    localparam [15:0] TRAP_NONE = 16'd0;
    localparam [15:0] TRAP_DESCRIPTOR = 16'd3;
    localparam [15:0] TRAP_CAPABILITY = 16'd4;
    localparam [15:0] TRAP_ENGINE = 16'd8;

    localparam [7:0] FAMILY_DMA = 8'h10;
    localparam [7:0] FAMILY_TENSOR = 8'h20;
    localparam [7:0] FAMILY_VECTOR = 8'h30;
    localparam [7:0] DMA_TRANSFER = 8'h00;
    localparam [7:0] DMA_GATHER = 8'h02;
    localparam [7:0] TENSOR_EMBED_LOOKUP = 8'h03;
    localparam [7:0] TENSOR_MATMUL = 8'h00;
    localparam [7:0] VECTOR_RMS_NORM = 8'h00;
    localparam [7:0] VECTOR_HEAD_RMS_NORM = 8'h01;
    localparam [7:0] VECTOR_ROPE = 8'h02;
    localparam [7:0] FAMILY_ATTENTION = 8'h40;
    localparam [7:0] FAMILY_ROUTE = 8'h50;
    localparam [7:0] FAMILY_SELECTION = 8'h70;
    localparam [7:0] ROUTE_WEIGHT_NORMALIZE = 8'h02;
    localparam [7:0] ROUTE_WINDOW_INDEX = 8'h06;
    localparam [7:0] ROUTE_BIASED_TOPK = 8'h01;
    localparam [7:0] FAMILY_REDUCTION = 8'h60;
    localparam [7:0] REDUCTION_EXPERT_SUM = 8'h05;
    localparam [7:0] DMA_SCATTER = 8'h03;
    localparam [7:0] VECTOR_ADD = 8'h03;
    localparam [7:0] VECTOR_SILU_MUL = 8'h04;
    localparam [7:0] ATTENTION_GQA = 8'h01;
    localparam [7:0] SELECTION_ARGMAX = 8'h00;
    localparam [7:0] SELECTION_TOKEN_APPEND = 8'h01;
    localparam [7:0] FMT_U32 = 8'h04;
    localparam [7:0] FMT_I32 = 8'h05;
    localparam [7:0] FMT_BF16 = 8'h10;
    localparam [7:0] FMT_FP32 = 8'h12;
    localparam [7:0] ERR_NONE = 8'd0;

    // The raw little-endian 256-bit value held in NUMERIC payload bytes
    // 32..63 for SHA-256("exact_index_select_v1").  Comparing the descriptor
    // bytes avoids silently accepting another contract with the same dtypes.
    localparam [255:0] CONTRACT_EXACT_INDEX_SELECT_RAW =
        256'heeda7776a6f13afec895e72e1caa26c9dbf71599e6a35ecc51380dc89741a212;
    localparam [255:0] CONTRACT_QWEN_EMBED_RAW =
        256'hccfb3965ab85c67667ddda70e90d7dafe030d6ce65f4179ee161b1e0182fead1;
    localparam [255:0] CONTRACT_DEEPSEEK_EMBED_RAW =
        256'hd380012f2a885dbd0aebdd47859b1407945d8d1f7f5a091fc23201aa20e762ca;
    localparam [255:0] CONTRACT_QWEN_RMS_NORM_RAW =
        256'hda3fc0b8b5271a03bfb1f0c1e6d2be46af1896d484db57fd6dc3d4c46bf89e99;
    localparam [255:0] CONTRACT_DEEPSEEK_TRANSFER_RAW =
        256'h94180f7a2a2d20609236e96941dde296643a19e8e71ff1ab239c3ac09ae5e14a;
    localparam [255:0] CONTRACT_QWEN_MATMUL_RAW =
        256'ha15a76a03cd9c4212365014f8ebb77b73f61872818463b77d5d93f776adc5075;
    localparam [255:0] CONTRACT_QWEN_ROPE_RAW =
        256'hcf36189f7564a37bc093ee69e108bdae3e75853a46b8efe51eabb1765c15ad34;
    // The six admitted here.  Same little-endian raw form: comparing the
    // descriptor bytes refuses a familiar dtype tuple carrying an unrelated
    // contract, which is the fail-open hole this whole block exists to close.
    // bf16_add_rne_v1
    localparam [255:0] CONTRACT_BF16_ADD_RAW =
        256'h090bde3d8e998a255f7ca88358c3c3d94a9b8da02141f5ba440a6cff6825973c;
    // qwen3_silu_mul_bf16_v1
    localparam [255:0] CONTRACT_QWEN_SILU_MUL_RAW =
        256'hca5ac4642d9de6ef1d150b327b755569f8aeb3fe1c0e4f2b48b2350176b3f51e;
    // greedy_lowest_token_id_argmax_v1
    localparam [255:0] CONTRACT_ARGMAX_RAW =
        256'h3a7c5eeca987ccb78dc04cc46ef10cad9227f9a3197c5b1f2173f5e56523df27;
    // exact_token_append_eos_v1
    localparam [255:0] CONTRACT_TOKEN_APPEND_RAW =
        256'hfc3d3f9eeff351b981d65d175e5c80b5c253a298e4b7915fd9586f8b7c08708d;
    //: The contract every shipped ROUTE.WEIGHT_NORMALIZE carries -- read off the
    //: descriptor tables at HEAD, identical across all 4 operators in
    //: deepseek-v4-flash-rom and all 16 in deepseek-v41-flash-rom-array-64.
    //:
    //: THIS DIGEST IS WHAT LETS THE ENGINE'S ORDER PORT BE TIED TO ZERO.  The
    //: profile's reduction_order is not a field this bridge reads, so pinning
    //: the whole contract is the sound way to know the association is
    //: SEQUENTIAL_ASCENDING -- the only one ot_a3_route_weight_normalize
    //: admits, and the only one the shipped operators declare.
    localparam [255:0] CONTRACT_WEIGHT_NORMALIZE_RAW =
        256'h2b0b65aecc1a32791670f069fd0e71850d941ff8fba8913fe10984834d88c3c2;
    //: The contract every shipped ROUTE.WINDOW_INDEX carries -- identical across
    //: all 4 operators in deepseek-v4-flash-rom and all 16 in
    //: deepseek-v41-flash-rom-array-64.
    localparam [255:0] CONTRACT_WINDOW_INDEX_RAW =
        256'h8afab2aedbd62798bcbab3568e9f75a1e333df6db9f32c70d87a23d1eb224bf5;
    //: The contract every shipped ROUTE.BIASED_TOPK carries.
    localparam [255:0] CONTRACT_BIASED_TOPK_RAW =
        256'h01377eb4aa1a4fe0d58f7b60e68b8a5a769537f50a1e1fc25918f743163479b5;
    //: The contract every shipped REDUCTION.EXPERT_SUM carries. It declares
    //: PAIRWISE_TREE, which ot_a3_reduction_expert_sum is BY CONSTRUCTION -- it
    //: has no order port -- so the digest is what makes that agreement checked
    //: rather than assumed.
    localparam [255:0] CONTRACT_EXPERT_SUM_RAW =
        256'h202e8be635a9cf690f3d81f322698168c72912faf735bd5b76fd29fd462cd586;
    // bf16_byte_preserving_state_v1
    localparam [255:0] CONTRACT_KV_SCATTER_RAW =
        256'h6fe100be19c00c87797983af8409335999bfd793cdcf3862af5ba6bdcc9bf355;
    // qwen3_gqa_fp32_softmax_bf16_v1
    localparam [255:0] CONTRACT_QWEN_GQA_RAW =
        256'h81e12c87d89ead473983a0898c3fbfe08d7b0a3864b55fb1f0171a4698f53a62;
    //: ADMISSION USED ITS OWN COPY OF THE GEOMETRY.
    //:
    //: The datapath instances below are handed GQA_QUERY_HEADS, GQA_KV_HEADS,
    //: GQA_HEAD_WIDTH and GQA_SCALE_CODE.  The admission predicates read these
    //: localparams instead, which were frozen at 32/8/128 and 0x3db50000 -- so
    //: the bridge would reject shapes the engines behind it could compute, and
    //: two knobs had to be kept in step by hand.  One source of truth: the
    //: parameters.  The defaults are the shipped values, so nothing moves.
    localparam [31:0] HEAD_WIDTH = GQA_HEAD_WIDTH[31:0];
    //: The head-RMS row bound is the query head count.
    localparam [31:0] MAX_HEAD_ROWS = GQA_QUERY_HEADS[31:0];
    localparam [31:0] RMS_EPSILON = 32'h3586_37bd;
    localparam [31:0] TRANSFER_COPIES = 32'd4;
    localparam [31:0] QUERY_HEADS = GQA_QUERY_HEADS[31:0];
    localparam [31:0] KV_HEADS = GQA_KV_HEADS[31:0];
    localparam [31:0] KV_PLANE_WORDS = KV_HEADS * HEAD_WIDTH;
    localparam [31:0] KV_ROW_STRIDE = 32'd2 * KV_PLANE_WORDS;
    localparam [31:0] GQA_SCALE_BITS = GQA_SCALE_CODE;
    localparam [31:0] GQA_OUTPUT_WORDS = QUERY_HEADS * HEAD_WIDTH;
    //: The span bound as a 32-bit value, so every comparison against it is an
    //: explicitly bounded one at the width the extents arrive at.
    localparam [31:0] SPAN_BOUND = MAX_SEQUENCE_SPAN[31:0];

    localparam [4:0] S_IDLE        = 5'd0;
    localparam [4:0] S_OP_WAIT     = 5'd1;
    localparam [4:0] S_INDEX_WAIT  = 5'd2;
    localparam [4:0] S_SOURCE_WAIT = 5'd3;
    localparam [4:0] S_OUTPUT_WAIT = 5'd4;
    localparam [4:0] S_NUM_WAIT    = 5'd5;
    localparam [4:0] S_START       = 5'd6;
    localparam [4:0] S_ENGINE_WAIT = 5'd7;
    localparam [4:0] S_RESPONSE    = 5'd8;
    localparam [4:0] S_RMS_INPUT_WAIT = 5'd9;
    // The mapped families walk one shared admission path instead of one
    // state chain each.
    localparam [4:0] S_MAP_VIEW_WAIT   = 5'd10;
    localparam [4:0] S_MAP_NUM_WAIT    = 5'd11;
    localparam [4:0] S_MAP_POLICY_WAIT = 5'd12;
    localparam [4:0] S_MAP_INDEX_ISSUE = 5'd13;
    localparam [4:0] S_MAP_INDEX_WAIT  = 5'd14;
    localparam [4:0] S_MAP_ADMIT       = 5'd15;
    //: The embedding's own index probe.  The four-bit state field was full, so
    //: adding a real lookup meant widening it.
    localparam [4:0] S_EMBED_INDEX_ISSUE = 5'd16;
    localparam [4:0] S_EMBED_INDEX_WAIT  = 5'd17;

    // -- the object placement table ---------------------------------------
    // One table, consulted by every operand slot and every result slot of
    // every family.  It is a MEMORY now (ot_a3_place_table): hashed by object
    // id, read through a registered port, and sized by PLACE_ENTRIES.  What
    // used to be here was a function that compared an object id against all
    // 32 entries combinationally, in front of every operand address.
    //
    // The 32 scalar ports remain, so the surface can still be counted from
    // this module's declaration and every shipped vehicle drives what it
    // always drove.  They are not a second mechanism: they are SEEDED into
    // the table below, through the same load port a host uses.
    localparam integer PLACE_SLOTS = 32;
    wire [31:0] place_object [0:PLACE_SLOTS-1];
    wire [31:0] place_base   [0:PLACE_SLOTS-1];
    assign place_object[0] = cfg_place_object_0;
    assign place_base[0]   = cfg_place_base_0;
    assign place_object[1] = cfg_place_object_1;
    assign place_base[1]   = cfg_place_base_1;
    assign place_object[2] = cfg_place_object_2;
    assign place_base[2]   = cfg_place_base_2;
    assign place_object[3] = cfg_place_object_3;
    assign place_base[3]   = cfg_place_base_3;
    assign place_object[4] = cfg_place_object_4;
    assign place_base[4]   = cfg_place_base_4;
    assign place_object[5] = cfg_place_object_5;
    assign place_base[5]   = cfg_place_base_5;
    assign place_object[6] = cfg_place_object_6;
    assign place_base[6]   = cfg_place_base_6;
    assign place_object[7] = cfg_place_object_7;
    assign place_base[7]   = cfg_place_base_7;
    assign place_object[8] = cfg_place_object_8;
    assign place_base[8]   = cfg_place_base_8;
    assign place_object[9] = cfg_place_object_9;
    assign place_base[9]   = cfg_place_base_9;
    assign place_object[10] = cfg_place_object_10;
    assign place_base[10]   = cfg_place_base_10;
    assign place_object[11] = cfg_place_object_11;
    assign place_base[11]   = cfg_place_base_11;
    assign place_object[12] = cfg_place_object_12;
    assign place_base[12]   = cfg_place_base_12;
    assign place_object[13] = cfg_place_object_13;
    assign place_base[13]   = cfg_place_base_13;
    assign place_object[14] = cfg_place_object_14;
    assign place_base[14]   = cfg_place_base_14;
    assign place_object[15] = cfg_place_object_15;
    assign place_base[15]   = cfg_place_base_15;
    assign place_object[16] = cfg_place_object_16;
    assign place_base[16]   = cfg_place_base_16;
    assign place_object[17] = cfg_place_object_17;
    assign place_base[17]   = cfg_place_base_17;
    assign place_object[18] = cfg_place_object_18;
    assign place_base[18]   = cfg_place_base_18;
    assign place_object[19] = cfg_place_object_19;
    assign place_base[19]   = cfg_place_base_19;
    assign place_object[20] = cfg_place_object_20;
    assign place_base[20]   = cfg_place_base_20;
    assign place_object[21] = cfg_place_object_21;
    assign place_base[21]   = cfg_place_base_21;
    assign place_object[22] = cfg_place_object_22;
    assign place_base[22]   = cfg_place_base_22;
    assign place_object[23] = cfg_place_object_23;
    assign place_base[23]   = cfg_place_base_23;
    assign place_object[24] = cfg_place_object_24;
    assign place_base[24]   = cfg_place_base_24;
    assign place_object[25] = cfg_place_object_25;
    assign place_base[25]   = cfg_place_base_25;
    assign place_object[26] = cfg_place_object_26;
    assign place_base[26]   = cfg_place_base_26;
    assign place_object[27] = cfg_place_object_27;
    assign place_base[27]   = cfg_place_base_27;
    assign place_object[28] = cfg_place_object_28;
    assign place_base[28]   = cfg_place_base_28;
    assign place_object[29] = cfg_place_object_29;
    assign place_base[29]   = cfg_place_base_29;
    assign place_object[30] = cfg_place_object_30;
    assign place_base[30]   = cfg_place_base_30;
    assign place_object[31] = cfg_place_object_31;
    assign place_base[31]   = cfg_place_base_31;

    // -- the table instance ------------------------------------------------
    wire        place_flush_w;
    wire        place_flushing;
    wire        place_ld_en_w;
    wire [31:0] place_ld_object_w;
    wire [31:0] place_ld_base_w;
    wire        place_ld_ready_w;
    wire        place_lk_req_w;
    wire [31:0] place_lk_object_w;
    wire        place_lk_done_w;
    wire        place_lk_found_w;
    wire [31:0] place_lk_base_w;

    ot_a3_place_table #(
        .ENTRIES(PLACE_ENTRIES)
    ) u_place_table (
        .clk(clk),
        .rst_n(rst_n),
        .flush(place_flush_w),
        .flushing(place_flushing),
        .ld_en(place_ld_en_w),
        .ld_object(place_ld_object_w),
        .ld_base(place_ld_base_w),
        .ld_ready(place_ld_ready_w),
        .bound_twice(place_bound_twice),
        .overflowed(place_overflowed),
        .bound_count(place_bound_count),
        .lk_req(place_lk_req_w),
        .lk_object(place_lk_object_w),
        .lk_done(place_lk_done_w),
        .lk_found(place_lk_found_w),
        .lk_base(place_lk_base_w)
    );

    // -- ONE WAY IN: the seeder ------------------------------------------
    // The legacy ports are a CONTINUOUS surface and the table is a loaded
    // store, so the two are reconciled by replaying the ports into the store.
    // ``clear`` is the trigger, because ``clear`` is what a testbench pulses
    // between two cases that carry different placements
    // (rtl/test/tb_a3_operator_admission.sv drives cfg_map_object/base per
    // case and pulses clear between them, without a reset), and in the
    // shipped verification top ``clear`` is tied to ``start``.  A seed is a
    // flush plus at most 32 accepted loads, which is why it is cheap enough
    // to redo per transaction: measured below against a run of 7.9 M cycles.
    //
    // Once the host load port has been used the seed is RETIRED, because the
    // host's bindings are an image that must survive the next ``start`` just
    // as the program image does.
    localparam [1:0] SEED_FLUSH = 2'd0;
    localparam [1:0] SEED_WALK  = 2'd1;
    localparam [1:0] SEED_DONE  = 2'd2;
    reg [1:0] seed_state;
    // Counts 0..PLACE_SLOTS, so it is one bit wider than an index into them --
    // derived from PLACE_SLOTS rather than written as a literal, and compared
    // against a constant of its own width so the comparison cannot be the
    // 32-bit one an integer parameter silently promotes it to.
    localparam integer SEED_W = $clog2(PLACE_SLOTS) + 1;
    /* verilator lint_off WIDTHTRUNC */
    localparam [SEED_W-1:0] SEED_SLOTS = PLACE_SLOTS;
    /* verilator lint_on WIDTHTRUNC */
    reg [SEED_W-1:0] seed_index;
    reg       place_host_locked;
    reg       place_surface_conflict_r;
    reg       seed_flush_pulse;

    // The legacy port the seeder is presenting.  A mux from a registered
    // index, not a compare against all of them.
    wire seed_index_in_range = (seed_index < SEED_SLOTS);
    wire [31:0] seed_object = seed_index_in_range
        ? place_object[seed_index[SEED_W-2:0]] : NO_ID;
    wire [31:0] seed_base = seed_index_in_range
        ? place_base[seed_index[SEED_W-2:0]] : 32'd0;

    // Any legacy port still naming an object after the host has loaded one is
    // two surfaces disagreeing, and it is refused rather than resolved.  This
    // is 32 equality comparisons feeding one flop's D input -- not the 1,024
    // the pairwise uniqueness check used to make, and not on an address path.
    reg  legacy_any_named_r;
    integer legacy_i;
    always @* begin
        legacy_any_named_r = 1'b0;
        for (legacy_i = 0; legacy_i < PLACE_SLOTS; legacy_i = legacy_i + 1)
            if (place_object[legacy_i] != NO_ID)
                legacy_any_named_r = 1'b1;
    end

    assign place_flush_w = seed_flush_pulse;
    // The seeder owns the load port until it is done; then the host does.
    assign place_ld_en_w = (seed_state == SEED_WALK)
        ? seed_index_in_range
        : (place_ld_en && !place_flushing);
    assign place_ld_object_w = (seed_state == SEED_WALK) ? seed_object
                                                         : place_ld_object;
    assign place_ld_base_w = (seed_state == SEED_WALK) ? seed_base
                                                       : place_ld_base;
    assign place_ld_ready = (seed_state == SEED_DONE) && place_ld_ready_w;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            //: NOT SEED_FLUSH.  Reset leaves the table EMPTY and the load port
            //: open, and the legacy surface is seeded on the first ``clear``.
            //: Seeding at reset instead read the configuration ports before
            //: anything had driven them -- 32 copies of object 0 -- and the
            //: table's own uniqueness detection correctly refused the second
            //: of them, so a perfectly good deployment came up refused.  An
            //: empty table is the honest state before a transaction is
            //: configured: it names no object, and an object it does not name
            //: is a trap rather than a guess.
            seed_state <= SEED_DONE;
            seed_index <= {SEED_W{1'b0}};
            seed_flush_pulse <= 1'b0;
            place_host_locked <= 1'b0;
            place_surface_conflict_r <= 1'b0;
        end else begin
            seed_flush_pulse <= 1'b0;
            if (place_ld_en && place_ld_ready)
                place_host_locked <= 1'b1;
            if (place_host_locked && legacy_any_named_r)
                place_surface_conflict_r <= 1'b1;

            if (clear && !place_host_locked) begin
                seed_state <= SEED_FLUSH;
                seed_index <= {SEED_W{1'b0}};
                seed_flush_pulse <= 1'b1;
            end else begin
                case (seed_state)
                    SEED_FLUSH: begin
                        // wait out the table's own flush sweep
                        if (!place_flushing && !seed_flush_pulse)
                            seed_state <= SEED_WALK;
                    end
                    SEED_WALK: begin
                        if (!seed_index_in_range)
                            seed_state <= SEED_DONE;
                        else if (place_ld_ready_w)
                            seed_index <= seed_index + {{(SEED_W-1){1'b0}}, 1'b1};
                    end
                    default: ;   // SEED_DONE: the host owns the port
                endcase
            end
        end
    end

    assign place_surface_conflict = place_surface_conflict_r;

    // An object bound twice is a configuration that cannot be honoured: two
    // entries disagree about where one object is, and every rule in this
    // module assumes an object has one place.  NO_ID is the empty entry and
    // may repeat.  The check is no longer an O(N^2) comparison of the ports
    // against each other -- 1,024 comparisons at 32 entries and 4 million at
    // 2,048 -- it is the ONE insertion path every binding passes through,
    // which sees the collision by probing to its own key.  A binding that
    // finds no free entry is refused for the same reason: a table that cannot
    // hold the program's objects must not place some of them and guess the
    // rest.  A surface conflict is refused with them.
    wire placement_table_unique = !place_bound_twice && !place_overflowed &&
                                  !place_surface_conflict;

    //: AND IT IS ONLY A VERDICT ONCE THE TABLE IS BUILT.  The refusal above
    //: used to be a combinational function of the 32 ports, so it was true or
    //: false the instant a request arrived.  It is now the residue of a seed
    //: that takes a flush plus one accepted load per binding, and a request
    //: admitted while that seed is still running would be judged against a
    //: half-built table -- both a refusal missed and a base read before it was
    //: written.  So S_IDLE waits.  The sequencer holds ``issue_valid`` until
    //: the bridge answers, which is the handshake every instantiation already
    //: implements, and the wait is bounded by PLACE_ENTRIES + 3*32 cycles.
    //: AND THE TABLE MUST BE QUIESCENT, not merely finished ACCEPTING.
    //:
    //: SEED_DONE is reached when the LAST legacy binding is accepted at the load
    //: port, but that binding's probe walk (T_ISSUE -> T_CMP) is still in flight
    //: for a further cycle or more, and place_bound_twice / place_overflowed are
    //: only set when it lands.  Gating on SEED_DONE alone therefore released the
    //: held request inside exactly that window -- and because this gate is what
    //: had been holding the sequencer, the first issue arrived precisely there.
    //: Measured: a duplicate seeded into an early legacy slot refused at the
    //: first launch, while the same duplicate in the LAST slot was not refused
    //: at all, because its bound_twice had not yet been raised.
    //:
    //: place_ld_ready_w is the table's own ``tstate == T_IDLE``, so requiring it
    //: here means no probe is outstanding and every flag the seed can raise has
    //: been raised.  The wait stays bounded: one walk is a fixed few cycles.
    wire placement_table_ready = (seed_state == SEED_DONE) && !place_flushing &&
                                 place_ld_ready_w;

    // -- THE HELD DESCRIPTOR AND ITS PLACEMENT PROBE ----------------------
    // The descriptor port is registered and so is the placement table, so an
    // admission clause that needs a record AND the base of the object it
    // names needs both to have arrived.  The record is held, the probe is
    // launched from it, and ``desc_valid`` is presented for exactly one cycle
    // when the probe answers -- so every admission clause below reads the same
    // ``desc_data`` / ``desc_valid`` / ``desc_fault`` names it always read and
    // is textually unchanged.
    reg  [1535:0] desc_hold_q;
    reg           desc_hold_fault_q;
    reg           desc_hold_pending;
    reg           desc_place_done_q;
    reg           desc_place_found_q;
    reg  [31:0]   desc_place_base_q;

    wire [1535:0] desc_data  = desc_hold_q;
    wire          desc_fault = desc_hold_fault_q;
    wire          desc_valid = desc_hold_pending && desc_place_done_q;

    assign place_lk_req_w = desc_rd_valid;
    assign place_lk_object_w = desc_rd_data[159:128];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            desc_hold_q <= {1536{1'b0}};
            desc_hold_fault_q <= 1'b0;
            desc_hold_pending <= 1'b0;
            desc_place_done_q <= 1'b0;
            desc_place_found_q <= 1'b0;
            desc_place_base_q <= 32'd0;
        end else if (clear) begin
            desc_hold_pending <= 1'b0;
            desc_place_done_q <= 1'b0;
        end else begin
            //: A newly read record always wins: it invalidates any probe
            //: answer still in flight for the previous one.
            if (desc_rd_valid) begin
                desc_hold_q <= desc_rd_data;
                desc_hold_fault_q <= desc_rd_fault;
                desc_hold_pending <= 1'b1;
                desc_place_done_q <= 1'b0;
            end else begin
                if (desc_hold_pending && desc_place_done_q) begin
                    //: presented for one cycle and consumed; every wait state
                    //: below acts on ``desc_valid`` unconditionally
                    desc_hold_pending <= 1'b0;
                    desc_place_done_q <= 1'b0;
                end
                if (place_lk_done_w) begin
                    desc_place_done_q <= 1'b1;
                    desc_place_found_q <= place_lk_found_w;
                    desc_place_base_q <= place_lk_base_w;
                end
            end
        end
    end

    reg [4:0] state;
    reg       response_fault;
    reg [15:0] response_trap;
    reg       engine_start;

    reg [7:0]  issue_family_q;
    reg [7:0]  issue_sub_q;
    reg [31:0] issue_descriptor_q;
    reg [31:0] issue_index_q;
    reg        embedding_q;
    reg        rms_norm_q;
    reg        head_rms_norm_q;
    reg        rope_q;
    reg        dma_transfer_q;
    reg        matmul_q;

    reg [5:0]  captured_valid;
    reg [31:0] captured_id [0:5];
    reg [31:0] captured_extent [0:5];
    reg [7:0]  captured_axis [0:5];
    reg [63:0] captured_offset [0:5];
    reg [7:0]  captured_rank [0:5];

    reg [31:0] op_input0;
    reg [31:0] op_input1;
    reg [31:0] op_output0;
    reg [31:0] op_numeric;
    reg [31:0] op_aux0;
    //: ROUTE.WINDOW_INDEX is the first admitted operator to carry aux BEYOND
    //: slot 0: aux_id_1 is its mask mode and aux_id_2 names the context symbol.
    //: Both are IMMEDIATES in the operator record, not descriptor ids -- the
    //: reference uses aux_id_0 directly as the window width -- so capturing the
    //: fields is the whole of reading them.
    reg [31:0] op_aux1;
    reg [31:0] op_aux2;
    reg [31:0] index_raw_dim0;
    reg [31:0] source_rows;
    reg [31:0] source_trailing;
    reg [7:0]  source_dtype;
    reg [31:0] rms_input_base_q;
    reg [31:0] rms_weight_base_q;
    reg [31:0] rope_input_base_q;
    reg [31:0] rope_coefficient_base_q;
    reg [31:0] matmul_weight_base_q;
    reg [31:0] numeric_profile_dtypes;
    // Where the result of the operation now being admitted goes: its own
    // object's base plus the resolved element offset of its output view.
    reg [31:0] launch_output_base_q;

    // -- the six mapped families ----------------------------------------
    reg        vector_add_q;
    reg        vector_silu_mul_q;
    reg        dma_scatter_q;
    reg        attention_gqa_q;
    reg        selection_argmax_q;
    reg        selection_token_append_q;
    reg        route_weight_normalize_q;
    reg        route_window_index_q;
    reg        route_biased_topk_q;
    reg        reduction_expert_sum_q;
    wire       mapped_family_q = vector_add_q | vector_silu_mul_q |
                                 dma_scatter_q | attention_gqa_q |
                                 selection_argmax_q | selection_token_append_q |
                                 route_weight_normalize_q |
                                 route_window_index_q | route_biased_topk_q |
                                 reduction_expert_sum_q;

    // Per-slot capture of every bound TENSOR_VIEW record, filled by the shared
    // admission walk in slot order.  Flat arrays rather than a packed struct:
    // the pinned Yosys 0.68 frontend and Icarus 11 agree on these.
    reg [5:0]  slot_bound;
    reg [31:0] slot_view_id [0:5];
    reg [7:0]  slot_dtype [0:5];
    reg [7:0]  slot_rank [0:5];
    reg [7:0]  slot_terms [0:5];
    reg [31:0] slot_object [0:5];
    //: WHERE THAT SLOT'S OBJECT LIVES, captured from the same registered table
    //: probe the record itself was held for.  The base is not re-derived at
    //: admission: a second lookup is a second chance to disagree.
    reg [31:0] slot_place_base [0:5];
    reg        slot_place_found [0:5];
    reg [31:0] slot_permissions [0:5];
    reg [31:0] slot_dim0 [0:5];
    reg [31:0] slot_dim1 [0:5];
    reg [31:0] slot_dim2 [0:5];
    reg [31:0] slot_stride0 [0:5];
    reg [31:0] slot_stride1 [0:5];
    reg [31:0] slot_stride2 [0:5];
    reg [31:0] slot_tail_dims [0:5];
    reg [31:0] slot_tail_strides [0:5];
    //: A slot's OWN static offset and term count, so the resolved offset
    //: can be checked against what the view declares instead of against
    //: zero.  Comparing to zero admits only the first iteration of any
    //: indexed loop, which for a transformer means layer 0 alone.
    reg [63:0] slot_offset [0:5];
    //: The embedding's resolved index address, its table base, and the token id
    //: read back from that address.
    reg [31:0] embed_index_addr_q;
    reg [31:0] embed_table_base_q;
    reg [31:0] embed_token_q;
    //: A gather's source, addressed by object rather than by launch counter.
    reg [31:0] gather_source_base_q;
    reg [2:0]  slot_cursor;

    reg [31:0] op_input2;
    reg [31:0] op_input3;
    reg [31:0] mapped_element_count;
    reg [31:0] mapped_left_base;
    reg [31:0] mapped_right_base;
    reg [31:0] mapped_third_base;
    reg [31:0] mapped_index_base;
    reg [31:0] mapped_output_base;
    reg [31:0] mapped_prior_base;
    reg [31:0] mapped_result_words;
    reg [31:0] mapped_work_words;
    reg [31:0] mapped_context;
    reg [31:0] mapped_vocabulary;
    reg [7:0]  mapped_dtype_a;
    reg [31:0] observed_index_value;
    reg        policy_ring_bound;
    reg [7:0]  policy_selection_mode;
    reg [15:0] policy_eos_count;
    reg [31:0] policy_max_new_tokens;
    reg [31:0] policy_vocabulary;
    reg [31:0] policy_eos_token [0:7];

    function automatic descriptor_header_ok;
        input [1535:0] data;
        input fault;
        input [15:0] expected_type;
        input [31:0] expected_total;
        input [31:0] expected_payload;
        begin
            descriptor_header_ok = !fault &&
                (data[31:0] == DESC_MAGIC) &&
                (data[47:32] == expected_type) &&
                (data[55:48] == TYPE_MAJOR) &&
                (data[63:56] == TYPE_MINOR) &&
                (data[95:64] == expected_total) &&
                (data[351:320] == 32'd64) &&
                (data[383:352] == expected_payload);
        end
    endfunction

    wire response_fire = (state == S_RESPONSE) && issue_valid;
    assign issue_ready = (state == S_RESPONSE);
    assign issue_fault = response_fault;
    assign issue_trap_class = response_trap;
    assign issue_eos_reason =
        ((state == S_RESPONSE) && !response_fault && selection_token_append_q)
            ? append_eos_reason : 8'd0;

    // Descriptor fields shared by the three view checks.
    wire [7:0] desc_view_dtype = desc_data[519:512];
    wire [7:0] desc_view_rank = desc_data[527:520];
    wire [7:0] desc_view_layout = desc_data[535:528];
    wire [7:0] desc_view_terms = desc_data[543:536];
    wire [31:0] desc_view_scale_object = desc_data[575:544];
    wire [31:0] desc_view_scale_block = desc_data[607:576];
    wire [63:0] desc_view_offset = desc_data[703:640];
    wire [31:0] desc_view_dim0 = desc_data[735:704];
    wire [31:0] desc_view_dim1 = desc_data[767:736];
    wire [31:0] desc_view_dim2 = desc_data[799:768];
    wire [31:0] desc_view_dim3 = desc_data[831:800];
    wire [31:0] desc_view_dim4 = desc_data[863:832];
    wire [31:0] desc_view_dim5 = desc_data[895:864];
    wire [31:0] desc_view_stride0 = desc_data[927:896];
    wire [31:0] desc_view_stride1 = desc_data[959:928];
    wire [31:0] desc_view_stride2 = desc_data[991:960];
    wire [31:0] desc_view_stride3 = desc_data[1023:992];
    wire [31:0] desc_view_stride4 = desc_data[1055:1024];
    wire [31:0] desc_view_stride5 = desc_data[1087:1056];
    wire [31:0] desc_permissions = desc_data[287:256];
    wire [31:0] desc_primary_object = desc_data[159:128];
    // Where this descriptor's object lives, for whichever slot is being
    // fetched.  One rule for every role that used to have its own port -- and
    // it is now a REGISTERED table read, answered before this record is
    // presented, rather than a combinational compare against 32 ports.
    wire [32:0] desc_place = {desc_place_found_q, desc_place_base_q};
    wire        desc_object_placed = desc_place[32];

    //: A VIEW WITH A DYNAMIC TERM DOES NOT RESOLVE TO ITS STATIC OFFSET.
    //:
    //: Nine admission clauses asserted ``captured_offset[slot] ==
    //: desc_view_offset``, which says the resolver contributed nothing -- true
    //: of an unindexed view, and true of an indexed one only on its first
    //: iteration.  A transformer's per-layer weights are indexed by the layer
    //: loop, so layer 0 was admitted and layer 1 was refused.  The invariant
    //: that actually holds is stated by the view's own term count: no terms
    //: means exactly the static offset, and terms mean at or beyond it, since
    //: every stride in these views is non-negative.  An offset that resolves
    //: past the end of its object is caught where the object's size is known,
    //: which is the bank bound at the read, not here.
    //: The slot-array form of view_offset_consistent, for the mapped
    //: families whose shape predicates run after every slot is captured.
    function automatic slot_offset_consistent;
        input integer slot;
        begin
            slot_offset_consistent = (slot_terms[slot] == 8'd0)
                ? (captured_offset[slot] == slot_offset[slot])
                : (captured_offset[slot] >= slot_offset[slot]);
        end
    endfunction

    function automatic view_offset_consistent;
        input integer slot;
        begin
            view_offset_consistent = (desc_view_terms == 0)
                ? (captured_offset[slot] == desc_view_offset)
                : (captured_offset[slot] >= desc_view_offset);
        end
    endfunction

    // -- THE REQUEST'S SEQUENCE SPAN -------------------------------------
    //
    // One number per launch, and it is not a new descriptor field: it is the
    // resolved extent the sequencer already emits for the operator's leading
    // slot.  For every family whose operands carry a sequence axis that slot is
    // slot 0 -- the model row of a MATMUL or an RMSNorm, the whole-head row of a
    // head norm or a RoPE, the index vector of a gather, a scatter or an
    // embedding, the query rows of an attention, the left operand of an
    // elementwise -- so one expression serves all of them.
    //
    // THREE FAMILIES ARE SPAN-1 BY CONSTRUCTION rather than by a pin, and the
    // distinction matters: a family in this set must still be REFUSED a slot-0
    // extent other than one, so the bound it is checked against is 1 and not
    // SPAN_BOUND.  Folding them into ``request_span`` alone would have made
    // ``span_admitted`` the constant true for them and DELETED a check that
    // the literal comparisons used to perform.
    //
    //   SELECTION.ARGMAX     a prefill still selects ONE token, from the last
    //                        position, and slot 0 is the vocabulary it scans
    //                        rather than a sequence axis at all -- which is why
    //                        argmax_shape_ok compares slot 0 to
    //                        ``argmax_vocabulary`` itself and never consults
    //                        ``span_admitted``.
    //   SELECTION.TOKEN_APPEND  appends one id.
    //   DMA.TRANSFER         its row count is TRANSFER_COPIES, a staged fan-out
    //                        of one embedding row, and its slot-0 extent is not
    //                        a sequence span.  Admitting a span here would have
    //                        scaled counts the staged region cannot supply.
    //:   REDUCTION.EXPERT_SUM  its slot-0 extent is the EXPERT COUNT and its
    //:                        output is one row of the view's width, so slot 0
    //:                        is not a sequence axis either. Like ARGMAX, its
    //:                        own predicate compares slot 0 against the expert
    //:                        count and never consults ``span_admitted``.
    wire span_is_one_by_construction = selection_argmax_q ||
                                      selection_token_append_q ||
                                      dma_transfer_q ||
                                      reduction_expert_sum_q;
    wire [31:0] slot0_extent = captured_extent[0];
    //: The largest slot-0 extent this family may present.  Explicitly bounded,
    //: not arithmetic: ``<= span_limit`` cannot wrap the way a subtraction can.
    wire [31:0] span_limit = span_is_one_by_construction ? 32'd1 : SPAN_BOUND;
    // A span of zero has no rows and a span past the bound has no buffer, and
    // both are refusals rather than clamps.  At MAX_SEQUENCE_SPAN == 1 this is
    // exactly the ``extent == 1`` the sites below used to spell out.
    wire span_admitted = (slot0_extent >= 32'd1) && (slot0_extent <= span_limit);
    //: The span every count, every row configuration and every peer-slot extent
    //: below is derived from.  It is ``slot0_extent`` wherever slot 0 IS the
    //: sequence axis, and the constant one for the three families above -- so a
    //: vocabulary scan never reaches an engine as a span of 4,096.
    wire [31:0] request_span =
        span_is_one_by_construction ? 32'd1 : slot0_extent;

    wire input_view_common_ok = descriptor_header_ok(
        desc_data, desc_fault, DESC_TENSOR_VIEW, 32'd192, 32'd128
    ) &&
        (desc_view_layout == 0) &&
        (desc_view_scale_object == NO_ID) &&
        (desc_view_scale_block == 0) &&
        (desc_primary_object != NO_ID) &&
        ((desc_permissions & 32'd1) != 0);
    // The element type of a dense-row source.  A ``TENSOR.EMBED_LOOKUP``
    // table is BF16 and nothing else.  A plain ``DMA.GATHER`` used to be
    // pinned to FP32 here, which was never a property of this design: the
    // only gather the predicate had been written against was the shipped
    // program's FP32 RoPE coefficient row at PC 1, and the constant froze
    // that one instance into the admission rule.  ``ot_a3_dma_index_mover``
    // -- the block every gathered element actually crosses -- carries no
    // dtype port at all and says so in its own header ("Element width does
    // not appear here.  Both operand images carry one element per 32-bit
    // word, so a move is a word copy whatever the storage format is"), and
    // ABI 3.0 section 7 gives ``GATHER`` an index view and a source with no
    // dtype constraint.  The pin therefore refused the governed program's
    // own PC 68, whose source row is BF16 under the SAME
    // ``exact_index_select_v1`` contract digest PC 1 carries.
    //
    // Widening is not weakening, because the element type is still pinned
    // three further ways and all three are equalities against this same
    // captured ``source_dtype``: ``output_view_common_ok`` requires the
    // destination view to carry it, ``numeric_common_ok`` requires the
    // NUMERIC profile's output_dtype to carry it, and ``gather_numeric_ok``
    // requires the profile's second_input_dtype to carry it.  What the two
    // named codes do is keep the admitted set closed: an unrecognised
    // storage code is still a TRAP_DESCRIPTOR rather than a word copy of
    // something this design has never qualified.
    wire dense_row_source_ok = !rms_norm_q && !rope_q &&
        !dma_transfer_q && !matmul_q &&
        (embedding_q
            ? (desc_view_dtype == FMT_BF16)
            : ((desc_view_dtype == FMT_BF16) ||
               (desc_view_dtype == FMT_FP32))) &&
        (desc_view_rank == 2) && (desc_view_terms == 0) &&
        (desc_view_dim0 != 0) && (desc_view_dim1 != 0) &&
        (desc_view_dim2 == 0) && (desc_view_dim3 == 0) &&
        (desc_view_dim4 == 0) && (desc_view_dim5 == 0) &&
        (desc_view_stride0 == desc_view_dim1) &&
        (desc_view_stride1 == 1) && (desc_view_stride2 == 0) &&
        (desc_view_stride3 == 0) && (desc_view_stride4 == 0) &&
        (desc_view_stride5 == 0) &&
        (captured_rank[1] == 2) && (captured_axis[1] == 0) &&
        (captured_extent[1] == desc_view_dim0) &&
        (view_offset_consistent(1)) &&
        (!embedding_q || ((desc_view_dim1 == EMBEDDING_WIDTH) &&
         ((desc_view_dim0 == QWEN_VOCABULARY) ||
          (desc_view_dim0 == DEEPSEEK_VOCABULARY))));
    //: A MATMUL'S REDUCTION LENGTH IS NOT THE EMBEDDING WIDTH.
    //:
    //: This row and the weight below were both pinned to EMBEDDING_WIDTH, which
    //: is true of the attention projections and false of the MLP: a gate
    //: projection is [intermediate, hidden] and a down projection reduces over
    //: the intermediate width.  The shipped prefix fail-stops before the MLP,
    //: so the pin was never contradicted -- it was never reached.  What the
    //: datapath requires is that the weight's reduction axis equal the input
    //: row's width, whatever that width is, and that both fit the 16-bit
    //: cfg_cols/cfg_depth fields the engine array is configured through.
    wire model_row_input_source_ok =
        (matmul_q || (rms_norm_q && !head_rms_norm_q)) &&
        (desc_view_dtype == FMT_BF16) && (desc_view_rank == 2) &&
        (desc_view_terms <= 4) &&
        (desc_view_dim0 != 0) &&
        (desc_view_dim1 != 0) && (desc_view_dim1 <= 32'hffff) &&
        (desc_view_dim2 == 0) && (desc_view_dim3 == 0) &&
        (desc_view_dim4 == 0) && (desc_view_dim5 == 0) &&
        (desc_view_stride0 == desc_view_dim1) &&
        (desc_view_stride1 == 1) && (desc_view_stride2 == 0) &&
        (desc_view_stride3 == 0) && (desc_view_stride4 == 0) &&
        (desc_view_stride5 == 0) &&
        (captured_rank[0] == 2) && (captured_axis[0] == 0) &&
        //: Slot 0 is where the span is READ, so the check here is the bound and
        //: not an equality against a literal row count.
        span_admitted &&
        (view_offset_consistent(0));
    wire head_rms_input_source_ok = rms_norm_q && head_rms_norm_q &&
        (desc_view_dtype == FMT_BF16) && (desc_view_rank == 3) &&
        (desc_view_terms <= 4) &&
        (desc_view_dim0 != 0) &&
        (desc_view_dim1 != 0) && (desc_view_dim1 <= MAX_HEAD_ROWS) &&
        (desc_view_dim2 == HEAD_WIDTH) &&
        (desc_view_dim3 == 0) && (desc_view_dim4 == 0) &&
        (desc_view_dim5 == 0) &&
        (desc_view_stride0 == desc_view_dim1 * HEAD_WIDTH) &&
        (desc_view_stride1 == HEAD_WIDTH) &&
        (desc_view_stride2 == 1) && (desc_view_stride3 == 0) &&
        (desc_view_stride4 == 0) && (desc_view_stride5 == 0) &&
        (captured_rank[0] == 3) && (captured_axis[0] == 0) &&
        span_admitted &&
        (view_offset_consistent(0));
    wire rope_input_source_ok = rope_q &&
        (desc_view_dtype == FMT_BF16) && (desc_view_rank == 3) &&
        (desc_view_terms <= 4) &&
        (desc_view_dim0 != 0) &&
        //: A RoPE view covers either the query heads or the key heads.  These
        //: were the literals 32 and 8, so a model whose key count was neither
        //: was refused -- and one whose query count happened to equal 8 was
        //: admitted by coincidence.
        ((desc_view_dim1 == QUERY_HEADS) || (desc_view_dim1 == KV_HEADS)) &&
        (desc_view_dim2 == HEAD_WIDTH) &&
        (desc_view_dim3 == 0) && (desc_view_dim4 == 0) &&
        (desc_view_dim5 == 0) &&
        (desc_view_stride0 == desc_view_dim1 * HEAD_WIDTH) &&
        (desc_view_stride1 == HEAD_WIDTH) &&
        (desc_view_stride2 == 1) && (desc_view_stride3 == 0) &&
        (desc_view_stride4 == 0) && (desc_view_stride5 == 0) &&
        (captured_rank[0] == 3) && (captured_axis[0] == 0) &&
        span_admitted &&
        (view_offset_consistent(0));
    wire rms_weight_source_ok = rms_norm_q &&
        (desc_view_dtype == FMT_BF16) && (desc_view_rank == 1) &&
        (desc_view_terms <= 4) &&
        (desc_view_dim0 == source_trailing) &&
        (desc_view_dim1 == 0) && (desc_view_dim2 == 0) &&
        (desc_view_dim3 == 0) && (desc_view_dim4 == 0) &&
        (desc_view_dim5 == 0) && (desc_view_stride0 == 1) &&
        (desc_view_stride1 == 0) && (desc_view_stride2 == 0) &&
        (desc_view_stride3 == 0) && (desc_view_stride4 == 0) &&
        (desc_view_stride5 == 0) &&
        (captured_rank[1] == 1) && (captured_axis[1] == 0) &&
        (captured_extent[1] == source_trailing) &&
        (view_offset_consistent(1));
    wire rope_coefficient_source_ok = rope_q &&
        (desc_view_dtype == FMT_FP32) && (desc_view_rank == 3) &&
        (desc_view_terms <= 4) &&
        (desc_view_dim0 == index_raw_dim0) &&
        (desc_view_dim1 == source_rows) &&
        (desc_view_dim2 == 2 * HEAD_WIDTH) &&
        (desc_view_dim3 == 0) && (desc_view_dim4 == 0) &&
        (desc_view_dim5 == 0) &&
        (desc_view_stride0 == 2 * HEAD_WIDTH) &&
        (desc_view_stride1 == 0) &&
        (desc_view_stride2 == 1) && (desc_view_stride3 == 0) &&
        (desc_view_stride4 == 0) && (desc_view_stride5 == 0) &&
        (captured_rank[1] == 3) && (captured_axis[1] == 0) &&
        (captured_extent[1] == captured_extent[0]) &&
        (view_offset_consistent(1));
    wire matmul_weight_source_ok = matmul_q &&
        (desc_view_dtype == FMT_BF16) && (desc_view_rank == 2) &&
        (desc_view_terms <= 4) &&
        (desc_view_dim0 != 0) && (desc_view_dim0 <= 32'hffff) &&
        //: source_trailing holds the input row's width, captured one state ago.
        (desc_view_dim1 == source_trailing) &&
        (desc_view_dim2 == 0) && (desc_view_dim3 == 0) &&
        (desc_view_dim4 == 0) && (desc_view_dim5 == 0) &&
        (desc_view_stride0 == desc_view_dim1) &&
        (desc_view_stride1 == 1) && (desc_view_stride2 == 0) &&
        (desc_view_stride3 == 0) && (desc_view_stride4 == 0) &&
        (desc_view_stride5 == 0) &&
        (captured_rank[1] == 2) && (captured_axis[1] == 0) &&
        (captured_extent[1] == desc_view_dim0) &&
        (view_offset_consistent(1));
    wire transfer_source_ok = dma_transfer_q &&
        (desc_view_dtype == FMT_BF16) && (desc_view_rank == 3) &&
        (desc_view_terms <= 4) && (desc_view_dim0 != 0) &&
        (desc_view_dim1 == TRANSFER_COPIES) &&
        (desc_view_dim2 == EMBEDDING_WIDTH) &&
        (desc_view_dim3 == 0) && (desc_view_dim4 == 0) &&
        (desc_view_dim5 == 0) &&
        (desc_view_stride0 == EMBEDDING_WIDTH) &&
        (desc_view_stride1 == 0) && (desc_view_stride2 == 1) &&
        (desc_view_stride3 == 0) && (desc_view_stride4 == 0) &&
        (desc_view_stride5 == 0) &&
        (captured_rank[0] == 3) && (captured_axis[0] == 0) &&
        span_admitted &&
        (view_offset_consistent(0));

    wire output_view_common_ok = descriptor_header_ok(
        desc_data, desc_fault, DESC_TENSOR_VIEW, 32'd192, 32'd128
    ) &&
        (desc_view_dtype == source_dtype) &&
        (desc_view_layout == 0) && (desc_view_terms <= 4) &&
        (desc_view_scale_object == NO_ID) &&
        (desc_view_scale_block == 0) &&
        (desc_primary_object != NO_ID) &&
        ((desc_permissions & 32'd2) != 0);
    wire dense_row_output_ok = !dma_transfer_q && !matmul_q && !rope_q &&
        !head_rms_norm_q &&
        (desc_view_rank == 2) && (desc_view_dim0 == index_raw_dim0) &&
        (desc_view_dim1 == source_trailing) &&
        (desc_view_dim2 == 0) && (desc_view_dim3 == 0) &&
        (desc_view_dim4 == 0) && (desc_view_dim5 == 0) &&
        (desc_view_stride0 == source_trailing) &&
        (desc_view_stride1 == 1) && (desc_view_stride2 == 0) &&
        (desc_view_stride3 == 0) && (desc_view_stride4 == 0) &&
        (desc_view_stride5 == 0) &&
        (captured_rank[4] == 2) && (captured_axis[4] == 0) &&
        (captured_extent[4] == captured_extent[0]);
    wire head_rms_output_ok = head_rms_norm_q &&
        (desc_view_rank == 3) && (desc_view_dim0 == index_raw_dim0) &&
        (desc_view_dim1 == source_rows) &&
        (desc_view_dim2 == source_trailing) &&
        (desc_view_dim3 == 0) && (desc_view_dim4 == 0) &&
        (desc_view_dim5 == 0) &&
        (desc_view_stride0 == source_rows * source_trailing) &&
        (desc_view_stride1 == source_trailing) &&
        (desc_view_stride2 == 1) && (desc_view_stride3 == 0) &&
        (desc_view_stride4 == 0) && (desc_view_stride5 == 0) &&
        (captured_rank[4] == 3) && (captured_axis[4] == 0) &&
        (captured_extent[4] == captured_extent[0]);
    wire rope_output_ok = rope_q &&
        (desc_view_rank == 3) && (desc_view_dim0 == index_raw_dim0) &&
        (desc_view_dim1 == source_rows) &&
        (desc_view_dim2 == source_trailing) &&
        (desc_view_dim3 == 0) && (desc_view_dim4 == 0) &&
        (desc_view_dim5 == 0) &&
        (desc_view_stride0 == source_rows * source_trailing) &&
        (desc_view_stride1 == source_trailing) &&
        (desc_view_stride2 == 1) && (desc_view_stride3 == 0) &&
        (desc_view_stride4 == 0) && (desc_view_stride5 == 0) &&
        (captured_rank[4] == 3) && (captured_axis[4] == 0) &&
        (captured_extent[4] == captured_extent[0]) &&
        (view_offset_consistent(4));
    wire matmul_output_ok = matmul_q &&
        (desc_view_rank == 2) && (desc_view_dim0 == index_raw_dim0) &&
        (desc_view_dim1 == source_rows) &&
        (desc_view_dim2 == 0) && (desc_view_dim3 == 0) &&
        (desc_view_dim4 == 0) && (desc_view_dim5 == 0) &&
        (desc_view_stride0 == source_rows) &&
        (desc_view_stride1 == 1) && (desc_view_stride2 == 0) &&
        (desc_view_stride3 == 0) && (desc_view_stride4 == 0) &&
        (desc_view_stride5 == 0) &&
        (captured_rank[4] == 2) && (captured_axis[4] == 0) &&
        (captured_extent[4] == captured_extent[0]);
    wire transfer_output_ok = dma_transfer_q &&
        (desc_view_rank == 3) && (desc_view_dim0 == index_raw_dim0) &&
        (desc_view_dim1 == TRANSFER_COPIES) &&
        (desc_view_dim2 == EMBEDDING_WIDTH) &&
        (desc_view_dim3 == 0) && (desc_view_dim4 == 0) &&
        (desc_view_dim5 == 0) &&
        (desc_view_stride0 == TRANSFER_COPIES * EMBEDDING_WIDTH) &&
        (desc_view_stride1 == EMBEDDING_WIDTH) &&
        (desc_view_stride2 == 1) && (desc_view_stride3 == 0) &&
        (desc_view_stride4 == 0) && (desc_view_stride5 == 0) &&
        (captured_rank[4] == 3) && (captured_axis[4] == 0) &&
        (captured_extent[4] == captured_extent[0]);

    wire numeric_common_ok = descriptor_header_ok(
        desc_data, desc_fault, DESC_NUMERIC, 32'd128, 32'd64
    ) &&
        (desc_data[535:528] == FMT_FP32) &&
        (desc_data[543:536] == source_dtype) &&
        (desc_data[551:544] == 0) &&
        (desc_data[567:560] == 0) &&
        (desc_data[575:568] == 0) &&
        (desc_data[639:608] == 0) &&
        (desc_data[671:640] == 0) &&
        (desc_data[703:672] == 0) &&
        (desc_data[767:704] == 0);
    wire gather_numeric_ok = !embedding_q && !rms_norm_q &&
        !dma_transfer_q &&
        ((desc_data[519:512] == FMT_U32) ||
         (desc_data[519:512] == FMT_I32)) &&
        (desc_data[527:520] == source_dtype) &&
        (desc_data[559:552] == 0) &&
        (desc_data[607:576] == 0) &&
        (desc_data[1023:768] == CONTRACT_EXACT_INDEX_SELECT_RAW);
    wire embedding_numeric_ok = embedding_q &&
        (desc_data[519:512] == FMT_U32) &&
        (desc_data[527:520] == source_dtype) &&
        (desc_data[559:552] == 0) &&
        (desc_data[607:576] == 0) &&
        (((source_rows == QWEN_VOCABULARY) &&
          (desc_data[1023:768] == CONTRACT_QWEN_EMBED_RAW)) ||
         ((source_rows == DEEPSEEK_VOCABULARY) &&
          (desc_data[1023:768] == CONTRACT_DEEPSEEK_EMBED_RAW)));
    wire rms_numeric_ok = rms_norm_q &&
        (desc_data[519:512] == FMT_BF16) &&
        (desc_data[527:520] == FMT_BF16) &&
        (desc_data[559:552] == 1) &&
        (desc_data[607:576] == RMS_EPSILON) &&
        (desc_data[1023:768] == CONTRACT_QWEN_RMS_NORM_RAW);
    wire transfer_numeric_ok = dma_transfer_q &&
        (desc_data[519:512] == FMT_BF16) &&
        (desc_data[527:520] == FMT_BF16) &&
        (desc_data[559:552] == 0) &&
        (desc_data[607:576] == 0) &&
        (desc_data[1023:768] == CONTRACT_DEEPSEEK_TRANSFER_RAW);
    wire matmul_numeric_ok = matmul_q &&
        (desc_data[519:512] == FMT_BF16) &&
        (desc_data[527:520] == FMT_BF16) &&
        (desc_data[559:552] == 2) &&
        (desc_data[607:576] == 0) &&
        (desc_data[1023:768] == CONTRACT_QWEN_MATMUL_RAW);
    wire rope_numeric_ok = rope_q &&
        (desc_data[519:512] == FMT_BF16) &&
        (desc_data[527:520] == FMT_FP32) &&
        (desc_data[559:552] == 0) &&
        (desc_data[607:576] == 0) &&
        (desc_data[1023:768] == CONTRACT_QWEN_ROPE_RAW);


    // ------------------------------------------------------------------
    // The six mapped families: shared admission walk, per-family predicates.
    // ------------------------------------------------------------------
    function automatic integer cursor_as_integer;
        input [2:0] value;
        begin
            cursor_as_integer = {29'd0, value};
        end
    endfunction

    function automatic [2:0] next_bound_slot;
        input [5:0] mask;
        input [2:0] from_slot;
        integer scan;
        begin
            // 6 means "no further bound slot".  Descending order leaves the
            // smallest matching slot as the final assignment.
            next_bound_slot = 3'd6;
            for (scan = 5; scan >= 0; scan = scan - 1)
                if ((scan > cursor_as_integer(from_slot)) && mask[scan])
                    next_bound_slot = scan[2:0];
        end
    endfunction

    wire [5:0] expected_slot_mask =
        //: The first mask to name slot 5: scores, bias, selected ids and the
        //: selected weights that ride beside them.
        route_biased_topk_q ? 6'b110011
      : attention_gqa_q ? 6'b011111
      : (selection_argmax_q || selection_token_append_q ||
         route_weight_normalize_q || route_window_index_q) ? 6'b010001
      : 6'b010011;

    wire [2:0] next_slot_w = next_bound_slot(slot_bound, slot_cursor);
    wire [31:0] next_slot_descriptor_id =
        (next_slot_w == 3'd1) ? op_input1
      : (next_slot_w == 3'd2) ? op_input2
      : (next_slot_w == 3'd3) ? op_input3
      : op_output0;

    wire mapped_view_header_ok = descriptor_header_ok(
        desc_data, desc_fault, DESC_TENSOR_VIEW, 32'd192, 32'd128
    ) &&
        (desc_view_layout == 8'd0) &&
        (desc_view_terms <= 8'd4) &&
        (desc_view_scale_object == NO_ID) &&
        (desc_view_scale_block == 32'd0) &&
        (desc_primary_object != NO_ID) &&
        ((slot_cursor == 3'd4)
            ? ((desc_permissions & 32'd2) != 32'd0)
            : ((desc_permissions & 32'd1) != 32'd0)) &&
        (desc_view_offset[63:32] == 32'd0);

    // -- shape predicates over the captured slots ------------------------
    wire [31:0] elementwise_width = slot_dim1[0];
    wire elementwise_shape_ok =
        (slot_dtype[0] == FMT_BF16) && (slot_dtype[1] == FMT_BF16) &&
        (slot_dtype[4] == FMT_BF16) &&
        (slot_rank[0] == 8'd2) && (slot_rank[1] == 8'd2) &&
        (slot_rank[4] == 8'd2) &&
        (elementwise_width != 32'd0) &&
        (slot_dim1[1] == elementwise_width) &&
        (slot_dim1[4] == elementwise_width) &&
        (slot_dim2[0] == 32'd0) && (slot_dim2[1] == 32'd0) &&
        (slot_dim2[4] == 32'd0) &&
        (slot_tail_dims[0] == 32'd0) && (slot_tail_dims[1] == 32'd0) &&
        (slot_tail_dims[4] == 32'd0) &&
        (slot_stride0[0] == elementwise_width) &&
        (slot_stride0[1] == elementwise_width) &&
        (slot_stride0[4] == elementwise_width) &&
        (slot_stride1[0] == 32'd1) && (slot_stride1[1] == 32'd1) &&
        (slot_stride1[4] == 32'd1) &&
        (slot_stride2[0] == 32'd0) && (slot_stride2[1] == 32'd0) &&
        (slot_stride2[4] == 32'd0) &&
        (slot_tail_strides[0] == 32'd0) && (slot_tail_strides[1] == 32'd0) &&
        (slot_tail_strides[4] == 32'd0) &&
        (captured_rank[0] == 8'd2) && (captured_axis[0] == 8'd0) &&
        //: Slot 0 carries the span; the other two operands must agree with it
        //: rather than each being pinned to one row of their own.
        span_admitted &&
        (captured_rank[1] == 8'd2) && (captured_axis[1] == 8'd0) &&
        (captured_extent[1] == request_span) &&
        (captured_rank[4] == 8'd2) && (captured_axis[4] == 8'd0) &&
        (captured_extent[4] == request_span);

    wire [31:0] argmax_vocabulary = slot_dim0[0];
    wire argmax_shape_ok =
        ((slot_dtype[0] == FMT_BF16) || (slot_dtype[0] == FMT_FP32)) &&
        (slot_rank[0] == 8'd1) && (slot_terms[0] == 8'd0) &&
        (argmax_vocabulary != 32'd0) &&
        (slot_dim1[0] == 32'd0) && (slot_dim2[0] == 32'd0) &&
        (slot_tail_dims[0] == 32'd0) &&
        (slot_stride0[0] == 32'd1) && (slot_stride1[0] == 32'd0) &&
        (slot_stride2[0] == 32'd0) && (slot_tail_strides[0] == 32'd0) &&
        (captured_rank[0] == 8'd1) && (captured_axis[0] == 8'd0) &&
        (captured_extent[0] == argmax_vocabulary) &&
        (slot_dtype[4] == FMT_U32) && (slot_rank[4] == 8'd1) &&
        (slot_dim0[4] == 32'd1) && (slot_dim1[4] == 32'd0) &&
        (slot_dim2[4] == 32'd0) && (slot_tail_dims[4] == 32'd0) &&
        (slot_stride0[4] == 32'd1) && (slot_stride1[4] == 32'd0) &&
        (slot_stride2[4] == 32'd0) && (slot_tail_strides[4] == 32'd0) &&
        (captured_rank[4] == 8'd1) && (captured_axis[4] == 8'd0) &&
        //: ONE selected id, whatever the prompt length: ``request_span`` is the
        //: constant one on this leg by construction, so this reads as the span
        //: every other family's output extent is checked against rather than as
        //: a second, unexplained literal.
        (captured_extent[4] == request_span);

    wire token_append_shape_ok =
        (slot_dtype[0] == FMT_U32) && (slot_rank[0] == 8'd1) &&
        (slot_dim0[0] == 32'd1) && (slot_dim1[0] == 32'd0) &&
        (slot_dim2[0] == 32'd0) && (slot_tail_dims[0] == 32'd0) &&
        (slot_stride0[0] == 32'd1) && (slot_stride1[0] == 32'd0) &&
        (slot_stride2[0] == 32'd0) && (slot_tail_strides[0] == 32'd0) &&
        (captured_rank[0] == 8'd1) && (captured_axis[0] == 8'd0) &&
        //: ``span_limit`` is one for this family, so this is the same refusal
        //: the literal performed -- and it is now the SAME predicate the other
        //: families use, so there is one statement of what a span is.
        span_admitted &&
        (slot_dtype[4] == FMT_U32) && (slot_rank[4] == 8'd1) &&
        (slot_dim0[4] == 32'd1) && (slot_dim1[4] == 32'd0) &&
        (slot_dim2[4] == 32'd0) && (slot_tail_dims[4] == 32'd0) &&
        (slot_stride0[4] == 32'd1) && (slot_stride1[4] == 32'd0) &&
        (slot_stride2[4] == 32'd0) && (slot_tail_strides[4] == 32'd0) &&
        (captured_rank[4] == 8'd1) && (captured_axis[4] == 8'd0) &&
        (captured_extent[4] == request_span);

    // One decode row of eight KV heads by 128 elements, presented as the
    // second operand of a scatter or as the query of an attention.
    function automatic head_row_view_ok;
        input [7:0] dtype;
        input [7:0] rank;
        input [31:0] heads;
        input [31:0] dim1;
        input [31:0] dim2;
        input [31:0] tail_dims;
        input [31:0] stride0;
        input [31:0] stride1;
        input [31:0] stride2;
        input [31:0] tail_strides;
        begin
            head_row_view_ok = (dtype == FMT_BF16) && (rank == 8'd3) &&
                (dim1 == heads) && (dim2 == HEAD_WIDTH) &&
                (tail_dims == 32'd0) &&
                (stride0 == heads * HEAD_WIDTH) &&
                (stride1 == HEAD_WIDTH) && (stride2 == 32'd1) &&
                (tail_strides == 32'd0);
        end
    endfunction

    // The interleaved KV cache plane: one context row is a key row of
    // KV_PLANE_WORDS followed by a value row of the same width, so the row
    // stride is twice the plane and the plane offset is 0 or KV_PLANE_WORDS.
    function automatic kv_cache_view_ok;
        input [7:0] dtype;
        input [7:0] rank;
        input [31:0] dim1;
        input [31:0] dim2;
        input [31:0] tail_dims;
        input [31:0] stride0;
        input [31:0] stride1;
        input [31:0] stride2;
        input [31:0] tail_strides;
        begin
            kv_cache_view_ok = (dtype == FMT_BF16) && (rank == 8'd3) &&
                (dim1 == KV_HEADS) && (dim2 == HEAD_WIDTH) &&
                (tail_dims == 32'd0) &&
                (stride0 == KV_ROW_STRIDE) &&
                (stride1 == HEAD_WIDTH) && (stride2 == 32'd1) &&
                (tail_strides == 32'd0);
        end
    endfunction

    function automatic index_element_view_ok;
        input [7:0] dtype;
        input [7:0] rank;
        input [31:0] dim0;
        input [31:0] dim1;
        input [31:0] dim2;
        input [31:0] tail_dims;
        input [31:0] stride0;
        input [31:0] stride1;
        input [31:0] stride2;
        input [31:0] tail_strides;
        begin
            index_element_view_ok = (dtype == FMT_U32) && (rank == 8'd1) &&
                (dim0 != 32'd0) && (dim1 == 32'd0) && (dim2 == 32'd0) &&
                (tail_dims == 32'd0) && (stride0 == 32'd1) &&
                (stride1 == 32'd0) && (stride2 == 32'd0) &&
                (tail_strides == 32'd0);
        end
    endfunction

    //: WHICH KV PLANE, AND WHICH LAYER.  Two different questions, and one
    //: comparison used to answer both -- wrongly.
    //:
    //: A KV view's RESOLVED element offset is its declared static offset plus
    //: its dynamic terms.  For this program the static part IS the plane (0 for
    //: the key view, KV_PLANE_WORDS for the value view -- a property of the
    //: descriptor, identical at every layer) and the dynamic part is the LAYER
    //: (the loop term, one KV plane pair per layer).  ``scatter_plane_is_value``
    //: compared the RESOLVED offset against KV_PLANE_WORDS, which is true only
    //: where the dynamic part is zero: layer 0.
    //:
    //: MEASURED, not reasoned.  At layer 0 that comparison holds and the value
    //: scatter lands on the value plane; at layers 1-3 it does not, so those
    //: three value scatters were classified as KEY writes -- and because
    //: ``slot4_base`` also dropped the dynamic part, all eight scatters of a
    //: four-layer program wrote into LAYER 0's two planes.  Dumping the RTL's KV
    //: object after a 16-token prefill showed layer 1's key region still zero
    //: and layer 0's key row 0 holding layer 3's VALUE row, against a golden
    //: device that had four distinct layers of KV.  ``slot2_base`` -- the
    //: attention's value plane -- had the same omission, so every layer read
    //: layer 0's values.
    //:
    //: Stated as the two separate facts they are: the plane comes from the
    //: view's OWN static offset, and the layer is whatever the sequencer
    //: resolved on top of it.
    wire scatter_plane_is_value =
        (slot_offset[4][31:0] == KV_PLANE_WORDS);
    //: The resolved offset minus the declared one: the dynamic terms alone.
    //: ``slot_offset_consistent`` refuses a resolved offset below the declared
    //: one, so an admitted launch never takes the guarded branch -- and an
    //: inadmissible one yields the object's own base rather than a wrapped
    //: address 4 GiB away, which is the difference between a refusal and a
    //: write into another object.
    wire [63:0] slot2_dynamic_wide = (captured_offset[2] >= slot_offset[2])
        ? (captured_offset[2] - slot_offset[2]) : 64'd0;
    wire [63:0] slot4_dynamic_wide = (captured_offset[4] >= slot_offset[4])
        ? (captured_offset[4] - slot_offset[4]) : 64'd0;
    wire [31:0] slot2_dynamic_offset = slot2_dynamic_wide[31:0];
    wire [31:0] slot4_dynamic_offset = slot4_dynamic_wide[31:0];
    wire scatter_shape_ok =
        index_element_view_ok(
            slot_dtype[0], slot_rank[0], slot_dim0[0], slot_dim1[0],
            slot_dim2[0], slot_tail_dims[0], slot_stride0[0],
            slot_stride1[0], slot_stride2[0], slot_tail_strides[0]
        ) &&
        (captured_rank[0] == 8'd1) && (captured_axis[0] == 8'd0) &&
        //: The index vector IS the span: a prefill scatters S KV rows, one per
        //: position, and reads S indices to place them.
        span_admitted &&
        head_row_view_ok(
            slot_dtype[1], slot_rank[1], KV_HEADS, slot_dim1[1],
            slot_dim2[1], slot_tail_dims[1], slot_stride0[1],
            slot_stride1[1], slot_stride2[1], slot_tail_strides[1]
        ) &&
        (captured_rank[1] == 8'd3) && (captured_axis[1] == 8'd0) &&
        (captured_extent[1] == request_span) && slot_offset_consistent(1) &&
        kv_cache_view_ok(
            slot_dtype[4], slot_rank[4], slot_dim1[4], slot_dim2[4],
            slot_tail_dims[4], slot_stride0[4], slot_stride1[4],
            slot_stride2[4], slot_tail_strides[4]
        ) &&
        (captured_rank[4] == 8'd3) && (captured_axis[4] == 8'd0) &&
        (captured_extent[4] == slot_dim0[4]) &&
        (slot_dim0[4] >= cfg_kv_plane_rows) &&
        (slot_offset_consistent(4) || scatter_plane_is_value);

    wire gqa_shape_ok =
        head_row_view_ok(
            slot_dtype[0], slot_rank[0], QUERY_HEADS, slot_dim1[0],
            slot_dim2[0], slot_tail_dims[0], slot_stride0[0],
            slot_stride1[0], slot_stride2[0], slot_tail_strides[0]
        ) &&
        (captured_rank[0] == 8'd3) && (captured_axis[0] == 8'd0) &&
        //: The query rows are the span.
        span_admitted && slot_offset_consistent(0) &&
        kv_cache_view_ok(
            slot_dtype[1], slot_rank[1], slot_dim1[1], slot_dim2[1],
            slot_tail_dims[1], slot_stride0[1], slot_stride1[1],
            slot_stride2[1], slot_tail_strides[1]
        ) &&
        slot_offset_consistent(1) &&
        kv_cache_view_ok(
            slot_dtype[2], slot_rank[2], slot_dim1[2], slot_dim2[2],
            slot_tail_dims[2], slot_stride0[2], slot_stride1[2],
            slot_stride2[2], slot_tail_strides[2]
        ) &&
        //: The value plane sits one KV plane above the key plane.  That is a
        //: RELATIVE fact, and writing it as an absolute constant asserted the
        //: key plane starts at zero -- true only of layer 0.  Stated relatively
        //: it is the same check at layer 0 and the right one at every other.
        (captured_offset[2] ==
         captured_offset[1] + {32'd0, KV_PLANE_WORDS}) &&
        (slot_object[1] == slot_object[2]) &&
        (slot_dim0[1] == slot_dim0[2]) &&
        (slot_dim0[1] >= cfg_kv_plane_rows) &&
        index_element_view_ok(
            slot_dtype[3], slot_rank[3], slot_dim0[3], slot_dim1[3],
            slot_dim2[3], slot_tail_dims[3], slot_stride0[3],
            slot_stride1[3], slot_stride2[3], slot_tail_strides[3]
        ) &&
        (captured_rank[3] == 8'd1) && (captured_axis[3] == 8'd0) &&
        //: One position per query row, so the position vector spans with them.
        (captured_extent[3] == request_span) &&
        head_row_view_ok(
            slot_dtype[4], slot_rank[4], QUERY_HEADS, slot_dim1[4],
            slot_dim2[4], slot_tail_dims[4], slot_stride0[4],
            slot_stride1[4], slot_stride2[4], slot_tail_strides[4]
        ) &&
        (captured_rank[4] == 8'd3) && (captured_axis[4] == 8'd0) &&
        (captured_extent[4] == request_span) && slot_offset_consistent(4);

    //: ROUTE.WEIGHT_NORMALIZE presents [groups, slots] in and the same shape
    //: out, and slot 0 IS the sequence axis -- one routed group per token
    //: position -- so it needs no span special case: ``request_span`` is the
    //: group count and ``span_admitted`` bounds it like every other family.
    //:
    //: The slot count comes from the VIEW, not a constant.  The shipped
    //: operators carry 6, and a pin at 6 would refuse the V4.1 gate's own
    //: shape for no reason; MAX_SLOTS in the engine is the real limit and is
    //: the only bound asserted here.
    wire [31:0] weight_normalize_slots = slot_dim1[0];
    wire weight_normalize_shape_ok =
        (slot_dtype[0] == FMT_FP32) && (slot_rank[0] == 8'd2) &&
        (slot_terms[0] == 8'd0) &&
        (weight_normalize_slots != 32'd0) &&
        (weight_normalize_slots <= WEIGHT_NORMALIZE_MAX_SLOTS) &&
        (slot_dim2[0] == 32'd0) && (slot_tail_dims[0] == 32'd0) &&
        //: Row-major and contiguous, which is what makes ``base + row + slot``
        //: the right address; a padded row would silently read its neighbour.
        (slot_stride0[0] == weight_normalize_slots) &&
        (slot_stride1[0] == 32'd1) &&
        (slot_stride2[0] == 32'd0) && (slot_tail_strides[0] == 32'd0) &&
        (captured_rank[0] == 8'd2) && (captured_axis[0] == 8'd0) &&
        slot_offset_consistent(0) &&
        (slot_dtype[4] == FMT_FP32) && (slot_rank[4] == 8'd2) &&
        (slot_dim1[4] == weight_normalize_slots) &&
        (slot_dim2[4] == 32'd0) && (slot_tail_dims[4] == 32'd0) &&
        (slot_stride0[4] == weight_normalize_slots) &&
        (slot_stride1[4] == 32'd1) &&
        (slot_stride2[4] == 32'd0) && (slot_tail_strides[4] == 32'd0) &&
        (captured_rank[4] == 8'd2) && (captured_axis[4] == 8'd0) &&
        //: The output covers exactly the groups the input presented.
        (captured_extent[4] == captured_extent[0]) &&
        slot_offset_consistent(4);

    //: ROUTE.WINDOW_INDEX presents [span] U32 absolute positions and writes
    //: [span, slots] U32 KV rows padded with 0xffffffff. Slot 0 IS the sequence
    //: axis -- one position per query row -- so it needs no span special case.
    //:
    //: THE WINDOW IS AN AUX IMMEDIATE, not a view dimension, and the reference
    //: requires 0 < window <= slots. aux_id_1 is the mask mode, and the
    //: reference refuses full-visibility mode unless aux_id_2 names the context
    //: symbol, so that pairing is checked here rather than left to the engine.
    wire [31:0] window_index_slots = slot_dim1[4];
    wire [31:0] window_index_window =
        (op_aux0 == NO_ID) ? window_index_slots : op_aux0;
    wire        window_index_mask_full = (op_aux1 != 32'd0) && (op_aux1 != NO_ID);
    wire window_index_shape_ok =
        (slot_dtype[0] == FMT_U32) && (slot_rank[0] == 8'd1) &&
        (slot_terms[0] == 8'd0) &&
        (slot_dim1[0] == 32'd0) && (slot_dim2[0] == 32'd0) &&
        (slot_tail_dims[0] == 32'd0) &&
        (slot_stride0[0] == 32'd1) && (slot_stride1[0] == 32'd0) &&
        (slot_stride2[0] == 32'd0) && (slot_tail_strides[0] == 32'd0) &&
        (captured_rank[0] == 8'd1) && (captured_axis[0] == 8'd0) &&
        span_admitted && slot_offset_consistent(0) &&
        (slot_dtype[4] == FMT_U32) && (slot_rank[4] == 8'd2) &&
        (window_index_slots != 32'd0) &&
        (window_index_slots <= WINDOW_INDEX_MAX_SLOTS) &&
        (slot_dim2[4] == 32'd0) && (slot_tail_dims[4] == 32'd0) &&
        (slot_stride0[4] == window_index_slots) &&
        (slot_stride1[4] == 32'd1) &&
        (slot_stride2[4] == 32'd0) && (slot_tail_strides[4] == 32'd0) &&
        (captured_rank[4] == 8'd2) && (captured_axis[4] == 8'd0) &&
        //: One output row per query position.
        (captured_extent[4] == request_span) &&
        slot_offset_consistent(4) &&
        //: The reference's own bound on the window.
        (window_index_window != 32'd0) &&
        (window_index_window <= window_index_slots) &&
        //: Full visibility without a named context symbol is refused by the
        //: reference, so it is refused here.
        (!window_index_mask_full || (op_aux2 != NO_ID));

    //: ROUTE.BIASED_TOPK: [span, experts] FP32 scores, an [experts] FP32 bias,
    //: [span, k] U32 selected ids and [span, k] FP32 UNBIASED selected weights.
    //: Slot 0 IS the sequence axis -- one routing group per token position.
    //:
    //: k COMES FROM aux_id_0 AND MUST AGREE WITH THE OUTPUT VIEW. The reference
    //: takes k from aux_id_0 when present and from the output extent otherwise,
    //: and requires topk == slots; checking both and their equality is what
    //: stops a k that indexes past the ids the program allocated.
    wire [31:0] biased_topk_experts = slot_dim1[0];
    wire [31:0] biased_topk_slots = slot_dim1[4];
    wire [31:0] biased_topk_k =
        (op_aux0 == NO_ID) ? biased_topk_slots : op_aux0;
    wire biased_topk_shape_ok =
        (slot_dtype[0] == FMT_FP32) && (slot_rank[0] == 8'd2) &&
        (slot_terms[0] == 8'd0) &&
        (biased_topk_experts != 32'd0) &&
        (slot_dim2[0] == 32'd0) && (slot_tail_dims[0] == 32'd0) &&
        (slot_stride0[0] == biased_topk_experts) &&
        (slot_stride1[0] == 32'd1) &&
        (slot_stride2[0] == 32'd0) && (slot_tail_strides[0] == 32'd0) &&
        (captured_rank[0] == 8'd2) && (captured_axis[0] == 8'd0) &&
        span_admitted && slot_offset_consistent(0) &&
        //: The bias broadcasts over every group, so it is rank 1 [experts].
        (slot_dtype[1] == FMT_FP32) && (slot_rank[1] == 8'd1) &&
        (slot_dim0[1] == biased_topk_experts) &&
        (slot_dim1[1] == 32'd0) && (slot_dim2[1] == 32'd0) &&
        (slot_tail_dims[1] == 32'd0) &&
        (slot_stride0[1] == 32'd1) && (slot_stride1[1] == 32'd0) &&
        (slot_stride2[1] == 32'd0) && (slot_tail_strides[1] == 32'd0) &&
        (captured_rank[1] == 8'd1) && (captured_axis[1] == 8'd0) &&
        (captured_extent[1] == biased_topk_experts) &&
        slot_offset_consistent(1) &&
        (slot_dtype[4] == FMT_U32) && (slot_rank[4] == 8'd2) &&
        (biased_topk_slots != 32'd0) &&
        (biased_topk_slots <= BIASED_TOPK_MAX_K) &&
        (biased_topk_slots <= biased_topk_experts) &&
        (slot_dim2[4] == 32'd0) && (slot_tail_dims[4] == 32'd0) &&
        (slot_stride0[4] == biased_topk_slots) &&
        (slot_stride1[4] == 32'd1) &&
        (slot_stride2[4] == 32'd0) && (slot_tail_strides[4] == 32'd0) &&
        (captured_rank[4] == 8'd2) && (captured_axis[4] == 8'd0) &&
        (captured_extent[4] == request_span) && slot_offset_consistent(4) &&
        //: The weights are FP32 and cover exactly the ids.
        (slot_dtype[5] == FMT_FP32) && (slot_rank[5] == 8'd2) &&
        (slot_dim1[5] == biased_topk_slots) &&
        (slot_dim2[5] == 32'd0) && (slot_tail_dims[5] == 32'd0) &&
        (slot_stride0[5] == biased_topk_slots) &&
        (slot_stride1[5] == 32'd1) &&
        (slot_stride2[5] == 32'd0) && (slot_tail_strides[5] == 32'd0) &&
        (captured_rank[5] == 8'd2) && (captured_axis[5] == 8'd0) &&
        (captured_extent[5] == request_span) && slot_offset_consistent(5) &&
        //: k is the declared one AND the allocated one, or it is refused.
        (biased_topk_k == biased_topk_slots);

    //: REDUCTION.EXPERT_SUM: [experts, width] BF16 contributions, an [experts]
    //: FP32 routing-weight vector, and one [width] BF16 row out. Slot 0's axis
    //: is the EXPERT axis, so span_admitted is not consulted -- the extent is
    //: compared against the expert count here, exactly as argmax compares slot 0
    //: against its vocabulary.
    //:
    //: THE EXPERT COUNT IS BOUNDED BY THE BRIDGE'S OPERAND PORTS, not by the
    //: engine. ot_a3_reduction_expert_sum reads one bank per term -- val_rd_en
    //: is [EXPERTS-1:0] -- and this bridge has four (m0..m3). Four experts fit
    //: exactly and a fifth has nowhere to read from, so a wider operator is
    //: REFUSED rather than silently reading one expert's row twice. Every
    //: shipped V4-Flash instance is 4; V4.1's wafer program has instances at 6,
    //: and those need a wider operand surface before they can be admitted.
    wire [31:0] expert_sum_experts = slot_dim0[0];
    wire [31:0] expert_sum_width = slot_dim1[0];
    wire expert_sum_shape_ok =
        (slot_dtype[0] == FMT_BF16) && (slot_rank[0] == 8'd2) &&
        (slot_terms[0] == 8'd0) &&
        (expert_sum_experts != 32'd0) &&
        (expert_sum_experts <= EXPERT_SUM_MAX_EXPERTS) &&
        (expert_sum_width != 32'd0) &&
        (slot_dim2[0] == 32'd0) && (slot_tail_dims[0] == 32'd0) &&
        (slot_stride0[0] == expert_sum_width) &&
        (slot_stride1[0] == 32'd1) &&
        (slot_stride2[0] == 32'd0) && (slot_tail_strides[0] == 32'd0) &&
        (captured_rank[0] == 8'd2) && (captured_axis[0] == 8'd0) &&
        (captured_extent[0] == expert_sum_experts) &&
        slot_offset_consistent(0) &&
        //: One FP32 routing weight per expert.
        (slot_dtype[1] == FMT_FP32) && (slot_rank[1] == 8'd1) &&
        (slot_dim0[1] == expert_sum_experts) &&
        (slot_dim1[1] == 32'd0) && (slot_dim2[1] == 32'd0) &&
        (slot_tail_dims[1] == 32'd0) &&
        (slot_stride0[1] == 32'd1) && (slot_stride1[1] == 32'd0) &&
        (slot_stride2[1] == 32'd0) && (slot_tail_strides[1] == 32'd0) &&
        (captured_rank[1] == 8'd1) && (captured_axis[1] == 8'd0) &&
        (captured_extent[1] == expert_sum_experts) &&
        slot_offset_consistent(1) &&
        //: ONE row out, of the contributions' own width.
        (slot_dtype[4] == FMT_BF16) && (slot_rank[4] == 8'd1) &&
        (slot_dim0[4] == expert_sum_width) &&
        (slot_dim1[4] == 32'd0) && (slot_dim2[4] == 32'd0) &&
        (slot_tail_dims[4] == 32'd0) &&
        (slot_stride0[4] == 32'd1) && (slot_stride1[4] == 32'd0) &&
        (slot_stride2[4] == 32'd0) && (slot_tail_strides[4] == 32'd0) &&
        (captured_rank[4] == 8'd1) && (captured_axis[4] == 8'd0) &&
        (captured_extent[4] == expert_sum_width) &&
        slot_offset_consistent(4);

    wire mapped_shape_ok =
        (vector_add_q || vector_silu_mul_q) ? elementwise_shape_ok
      : selection_argmax_q ? argmax_shape_ok
      : selection_token_append_q ? token_append_shape_ok
      : route_weight_normalize_q ? weight_normalize_shape_ok
      : route_window_index_q ? window_index_shape_ok
      : route_biased_topk_q ? biased_topk_shape_ok
      : reduction_expert_sum_q ? expert_sum_shape_ok
      : dma_scatter_q ? scatter_shape_ok
      : gqa_shape_ok;

    // -- the frozen numeric contract of each admitted family --------------
    wire [7:0] numeric_input_dtype = desc_data[519:512];
    wire [7:0] numeric_second_dtype = desc_data[527:520];
    wire [7:0] numeric_accumulator_dtype = desc_data[535:528];
    wire [7:0] numeric_output_dtype = desc_data[543:536];
    wire mapped_numeric_frame_ok = descriptor_header_ok(
        desc_data, desc_fault, DESC_NUMERIC, 32'd128, 32'd64
    ) &&
        (numeric_accumulator_dtype == FMT_FP32) &&
        (desc_data[551:544] == 8'd0) &&
        (desc_data[559:552] == 8'd0) &&
        (desc_data[567:560] == 8'd0) &&
        (desc_data[575:568] == 8'd0) &&
        (desc_data[607:576] == 32'd0) &&
        (desc_data[671:640] == 32'd0) &&
        (desc_data[703:672] == 32'd0) &&
        (desc_data[767:704] == 64'd0);
    wire mapped_numeric_ok = mapped_numeric_frame_ok &&
        ((vector_add_q &&
          (numeric_input_dtype == FMT_BF16) &&
          (numeric_second_dtype == FMT_BF16) &&
          (numeric_output_dtype == FMT_BF16) &&
          (desc_data[639:608] == 32'd0) &&
          (desc_data[1023:768] == CONTRACT_BF16_ADD_RAW)) ||
         (vector_silu_mul_q &&
          (numeric_input_dtype == FMT_BF16) &&
          (numeric_second_dtype == FMT_BF16) &&
          (numeric_output_dtype == FMT_BF16) &&
          (desc_data[639:608] == 32'd0) &&
          (desc_data[1023:768] == CONTRACT_QWEN_SILU_MUL_RAW)) ||
         (selection_argmax_q &&
          (numeric_input_dtype == slot_dtype[0]) &&
          (numeric_second_dtype == slot_dtype[0]) &&
          (numeric_output_dtype == FMT_U32) &&
          (desc_data[639:608] == 32'd0) &&
          (desc_data[1023:768] == CONTRACT_ARGMAX_RAW)) ||
         (selection_token_append_q &&
          (numeric_input_dtype == FMT_U32) &&
          (numeric_second_dtype == FMT_U32) &&
          (numeric_output_dtype == FMT_U32) &&
          (desc_data[639:608] == 32'd0) &&
          (desc_data[1023:768] == CONTRACT_TOKEN_APPEND_RAW)) ||
         (route_weight_normalize_q &&
          (numeric_input_dtype == FMT_FP32) &&
          (numeric_second_dtype == FMT_FP32) &&
          (numeric_accumulator_dtype == FMT_FP32) &&
          (numeric_output_dtype == FMT_FP32) &&
          //: scale_bits zero, so the reference's trailing multiply is the
          //: identity and the engine's ENABLE_SCALE == 0 is the whole contract
          //: rather than a shortcut. A scaled profile is refused HERE, before
          //: the engine's own ERR_SCALE_RANGE ever has to fire.
          (desc_data[639:608] == 32'd0) &&
          (desc_data[1023:768] == CONTRACT_WEIGHT_NORMALIZE_RAW)) ||
         (route_window_index_q &&
          //: I32 in, I32 second, U32 out -- an index operator carries no
          //: floating-point operand at all.
          (numeric_input_dtype == FMT_I32) &&
          (numeric_second_dtype == FMT_I32) &&
          (numeric_output_dtype == FMT_U32) &&
          (desc_data[639:608] == 32'd0) &&
          (desc_data[1023:768] == CONTRACT_WINDOW_INDEX_RAW)) ||
         (route_biased_topk_q &&
          (numeric_input_dtype == FMT_FP32) &&
          (numeric_second_dtype == FMT_FP32) &&
          (numeric_accumulator_dtype == FMT_FP32) &&
          //: The profile's output dtype is the ID view's -- U32. The weights'
          //: FP32 is stated by slot 5 and checked there.
          (numeric_output_dtype == FMT_U32) &&
          (desc_data[639:608] == 32'd0) &&
          (desc_data[1023:768] == CONTRACT_BIASED_TOPK_RAW)) ||
         (reduction_expert_sum_q &&
          (numeric_input_dtype == FMT_BF16) &&
          //: The routing weights are FP32 while the contributions are BF16,
          //: which is why the weighting needed a real binary32 multiplier.
          (numeric_second_dtype == FMT_FP32) &&
          (numeric_accumulator_dtype == FMT_FP32) &&
          (numeric_output_dtype == FMT_BF16) &&
          (desc_data[639:608] == 32'd0) &&
          (desc_data[1023:768] == CONTRACT_EXPERT_SUM_RAW)) ||
         (dma_scatter_q &&
          (((numeric_input_dtype == FMT_BF16) &&
            (numeric_second_dtype == FMT_U32)) ||
           ((numeric_input_dtype == FMT_U32) &&
            (numeric_second_dtype == FMT_BF16))) &&
          (numeric_output_dtype == FMT_BF16) &&
          (desc_data[639:608] == 32'd0) &&
          (desc_data[1023:768] == CONTRACT_KV_SCATTER_RAW)) ||
         (attention_gqa_q &&
          (numeric_input_dtype == FMT_BF16) &&
          (numeric_second_dtype == FMT_BF16) &&
          (numeric_output_dtype == FMT_BF16) &&
          (desc_data[639:608] == GQA_SCALE_BITS) &&
          (desc_data[1023:768] == CONTRACT_QWEN_GQA_RAW)));

    // -- the bound GENERATION_POLICY record -------------------------------
    wire policy_record_ok = descriptor_header_ok(
        desc_data, desc_fault, DESC_GENERATION_POLICY, 32'd128, 32'd64
    ) &&
        (desc_data[527:520] == 8'd0) &&
        (desc_data[543:528] <= 16'd8) &&
        (desc_data[575:544] != 32'd0) &&
        (desc_data[607:576] != 32'd0);

    // -- operator-record admission for the mapped families ----------------
    wire mapped_operator_frame_ok = descriptor_header_ok(
        desc_data, desc_fault, DESC_OPERATOR, 32'd128, 32'd64
    ) &&
        (desc_data[519:512] == issue_family_q) &&
        (desc_data[527:520] == issue_sub_q) &&
        (desc_data[543:528] == 16'd0) &&
        (desc_data[575:544] == NO_ID) &&
        (desc_data[607:576] != NO_ID) &&
        (desc_data[639:608] != NO_ID) &&
        (desc_data[671:640] != NO_ID) &&
        (desc_data[703:672] != NO_ID) &&
        (desc_data[223:192] == desc_data[671:640]) &&
        (desc_data[735:704] != NO_ID) &&
        (desc_data[863:832] != NO_ID) &&
        //: A SECOND OUTPUT VIEW IS NO LONGER FORBIDDEN OUTRIGHT.  This was
        //: ``== NO_ID`` for every mapped family, which refused ROUTE.BIASED_TOPK
        //: and ROUTE.EXPERT_DISPATCH on their frame before any predicate of
        //: theirs ran. Whether it may be bound is now a per-family question,
        //: answered by mapped_operator_arity_ok's own legs -- which still
        //: require it UNBOUND for all seven families that do not declare one, so
        //: nothing is weakened for them.
        (mapped_second_output_allowed || (desc_data[895:864] == NO_ID));
    //: Which families may bind output_view_1. Deliberately an explicit list and
    //: not a default: an operator that gains a second output without saying so
    //: here is refused, which is the direction a mistake should fall.
    wire mapped_second_output_allowed = route_biased_topk_q;

    wire mapped_operator_arity_ok =
        ((vector_add_q || vector_silu_mul_q || dma_scatter_q ||
          reduction_expert_sum_q) &&
         (desc_data[767:736] != NO_ID) &&
         (desc_data[799:768] == NO_ID) &&
         (desc_data[831:800] == NO_ID) &&
         (desc_data[927:896] == NO_ID) && (desc_data[959:928] == NO_ID) &&
         (desc_data[991:960] == NO_ID) && (desc_data[1023:992] == NO_ID)) ||
        //: THE FIRST ADMITTED OPERATOR WITH AUX BEYOND SLOT 0. Every other
        //: mapped family requires all four aux fields unbound; this one requires
        //: the first three BOUND (window, mask mode, context symbol) and the
        //: fourth unbound, so it needs its own leg rather than a relaxation of
        //: theirs -- widening the shared leg would stop refusing an aux nobody
        //: reads on six other operators.
        //: input_view_1 BOUND (the bias), 2 and 3 unbound, aux_id_0 BOUND (k)
        //: and the other three unbound. output_view_1 is bound and permitted by
        //: mapped_second_output_allowed, which names this family.
        (route_biased_topk_q &&
         (desc_data[767:736] != NO_ID) &&
         (desc_data[799:768] == NO_ID) &&
         (desc_data[831:800] == NO_ID) &&
         (desc_data[895:864] != NO_ID) &&
         (desc_data[927:896] != NO_ID) && (desc_data[959:928] == NO_ID) &&
         (desc_data[991:960] == NO_ID) && (desc_data[1023:992] == NO_ID)) ||
        (route_window_index_q &&
         (desc_data[767:736] == NO_ID) &&
         (desc_data[799:768] == NO_ID) &&
         (desc_data[831:800] == NO_ID) &&
         (desc_data[927:896] != NO_ID) && (desc_data[959:928] != NO_ID) &&
         (desc_data[991:960] != NO_ID) && (desc_data[1023:992] == NO_ID)) ||
        ((selection_argmax_q || selection_token_append_q ||
          route_weight_normalize_q) &&
         (desc_data[767:736] == NO_ID) &&
         (desc_data[799:768] == NO_ID) &&
         (desc_data[831:800] == NO_ID) &&
         (desc_data[927:896] == NO_ID) && (desc_data[959:928] == NO_ID) &&
         (desc_data[991:960] == NO_ID) && (desc_data[1023:992] == NO_ID)) ||
        (attention_gqa_q &&
         (desc_data[767:736] != NO_ID) &&
         (desc_data[799:768] != NO_ID) &&
         (desc_data[831:800] != NO_ID) &&
         (desc_data[927:896] == QUERY_HEADS / KV_HEADS) &&
         (desc_data[959:928] == 32'd0) &&
         (desc_data[991:960] == 32'd3) &&
         (desc_data[1023:992] == 32'd1));
    wire mapped_operator_ok = mapped_operator_frame_ok &&
        mapped_operator_arity_ok &&
        (captured_valid == expected_slot_mask);

    // -- the base map, CAPTURED WITH EACH SLOT ---------------------------
    // A slot's object and the object's base arrive together: the probe for a
    // view's primary object is launched from the view record itself, so
    // S_MAP_VIEW_WAIT stores the answer beside everything else it stores about
    // that slot.  Five combinational 32-way scans became five register reads,
    // and at PLACE_ENTRIES = 2,048 they would have been five 2,048-way ones.
    wire [32:0] slot0_map = {slot_place_found[0], slot_place_base[0]};
    wire [32:0] slot1_map = {slot_place_found[1], slot_place_base[1]};
    wire [32:0] slot2_map = {slot_place_found[2], slot_place_base[2]};
    wire [32:0] slot3_map = {slot_place_found[3], slot_place_base[3]};
    wire [32:0] slot4_map = {slot_place_found[4], slot_place_base[4]};
    //: SLOT 5 IS output_view_1, and its placement was already being looked up --
    //: slot_place_base and slot_place_found are both [0:5] and the admission walk
    //: fills every bound slot -- it simply had no name here, because no admitted
    //: operator bound a second output. ROUTE.BIASED_TOPK and
    //: ROUTE.EXPERT_DISPATCH both do.
    wire [32:0] slot5_map = {slot_place_found[5], slot_place_base[5]};
    wire mapped_bases_found =
        slot0_map[32] && slot4_map[32] &&
        (!expected_slot_mask[1] || slot1_map[32]) &&
        (!expected_slot_mask[2] || slot2_map[32]) &&
        (!expected_slot_mask[3] || slot3_map[32]) &&
        (!expected_slot_mask[5] || slot5_map[32]);
    wire [31:0] kv_plane_span = cfg_kv_plane_rows * KV_PLANE_WORDS;
    wire [31:0] slot0_base = slot0_map[31:0] + captured_offset[0][31:0];
    wire [31:0] slot1_base = slot1_map[31:0] + captured_offset[1][31:0];
    //: THE ATTENTION'S VALUE PLANE.  Its layer is the dynamic offset, exactly as
    //: the key plane's is on the line above (the key view's declared offset is
    //: zero, so ``slot1_base``'s use of the resolved offset is already the
    //: dynamic part and needs no change).  The plane sits one KV plane above the
    //: key plane in THIS device's planar layout, which is a relative fact --
    //: ``gqa_shape_ok`` checks the declared views state the same relation.
    wire [31:0] slot2_base =
        slot2_map[31:0] + slot2_dynamic_offset + kv_plane_span;
    wire [31:0] slot3_base = slot3_map[31:0] + captured_offset[3][31:0];
    //: A SCATTER'S DESTINATION: object base, plus the layer the sequencer
    //: resolved, plus the plane the descriptor declares.  Every other family's
    //: result goes to the resolved offset unchanged, because only the KV cache
    //: is presented interleaved to the program and stored planar here.
    wire [31:0] slot4_base = dma_scatter_q
        ? (slot4_map[31:0] + slot4_dynamic_offset +
           (scatter_plane_is_value ? kv_plane_span : 32'd0))
        : (slot4_map[31:0] + captured_offset[4][31:0]);
    wire [31:0] slot5_base = slot5_map[31:0] + captured_offset[5][31:0];
    wire [31:0] mapped_index_slot_base =
        attention_gqa_q ? slot3_base : slot0_base;

    // The context the request declares must be the position the index view
    // actually resolves to, plus one.  Neither is trusted alone.
    wire mapped_context_ok =
        (cfg_context_length != 32'd0) &&
        (cfg_kv_plane_rows != 32'd0) &&
        (cfg_context_length <= cfg_kv_plane_rows) &&
        //: The span's LAST row ends at the context, so its FIRST row -- the
        //: position the index view resolves to -- sits at C - S.  The
        //: subtraction is guarded by the comparison before it rather than
        //: written as ``observed + S == C``: a 32-bit MODULAR equality of that
        //: shape accepted an underflowed bound in this very design, and a
        //: refusal is the only acceptable answer to a context shorter than the
        //: span it is asked to cover.
        (cfg_context_length >= request_span) &&
        (observed_index_value == cfg_context_length - request_span);

    integer slot;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            response_fault <= 1'b0;
            response_trap <= TRAP_NONE;
            engine_start <= 1'b0;
            desc_req <= 1'b0;
            desc_id <= NO_ID;
            issue_family_q <= 8'd0;
            issue_sub_q <= 8'd0;
            issue_descriptor_q <= NO_ID;
            issue_index_q <= NO_ID;
            embedding_q <= 1'b0;
            embed_index_addr_q <= 32'd0;
            embed_table_base_q <= 32'd0;
            embed_token_q <= 32'd0;
            gather_source_base_q <= 32'd0;
            rms_norm_q <= 1'b0;
            head_rms_norm_q <= 1'b0;
            rope_q <= 1'b0;
            dma_transfer_q <= 1'b0;
            matmul_q <= 1'b0;
            vector_add_q <= 1'b0;
            vector_silu_mul_q <= 1'b0;
            dma_scatter_q <= 1'b0;
            attention_gqa_q <= 1'b0;
            selection_argmax_q <= 1'b0;
            selection_token_append_q <= 1'b0;
            route_weight_normalize_q <= 1'b0;
            route_window_index_q <= 1'b0;
            route_biased_topk_q <= 1'b0;
            reduction_expert_sum_q <= 1'b0;
            slot_bound <= 6'd0;
            slot_cursor <= 3'd0;
            op_input2 <= NO_ID;
            op_input3 <= NO_ID;
            mapped_element_count <= 32'd0;
            mapped_left_base <= 32'd0;
            mapped_right_base <= 32'd0;
            mapped_third_base <= 32'd0;
            mapped_index_base <= 32'd0;
            mapped_output_base <= 32'd0;
            mapped_prior_base <= 32'd0;
            mapped_result_words <= 32'd0;
            mapped_work_words <= 32'd0;
            mapped_context <= 32'd0;
            mapped_vocabulary <= 32'd0;
            mapped_dtype_a <= 8'd0;
            observed_index_value <= 32'hffff_ffff;
            policy_ring_bound <= 1'b0;
            policy_selection_mode <= 8'hff;
            policy_eos_count <= 16'd0;
            policy_max_new_tokens <= 32'd0;
            policy_vocabulary <= 32'd0;
            captured_valid <= 6'd0;
            op_input0 <= NO_ID;
            op_input1 <= NO_ID;
            op_output0 <= NO_ID;
            op_numeric <= NO_ID;
            op_aux0 <= NO_ID;
            op_aux1 <= NO_ID;
            op_aux2 <= NO_ID;
            index_raw_dim0 <= 32'd0;
            source_rows <= 32'd0;
            source_trailing <= 32'd0;
            source_dtype <= 8'd0;
            rms_input_base_q <= 32'd0;
            rms_weight_base_q <= 32'd0;
            rope_input_base_q <= 32'd0;
            rope_coefficient_base_q <= 32'd0;
            matmul_weight_base_q <= 32'd0;
            numeric_profile_dtypes <= 32'd0;
            launch_output_base_q <= 32'd0;
            real_launch_count <= 32'd0;
            dma_gather_launch_count <= 32'd0;
            embedding_launch_count <= 32'd0;
            rms_norm_launch_count <= 32'd0;
            head_rms_norm_launch_count <= 32'd0;
            rope_launch_count <= 32'd0;
            dma_transfer_launch_count <= 32'd0;
            matmul_launch_count <= 32'd0;
            vector_add_launch_count <= 32'd0;
            vector_silu_mul_launch_count <= 32'd0;
            dma_scatter_launch_count <= 32'd0;
            attention_gqa_launch_count <= 32'd0;
            selection_argmax_launch_count <= 32'd0;
            selection_token_append_launch_count <= 32'd0;
            selected_token <= 32'd0;
            selected_tie_multiplicity <= 32'd0;
            selected_eos_reason <= 8'd0;
            capability_fault_count <= 32'd0;
            descriptor_fault_count <= 32'd0;
            engine_fault_count <= 32'd0;
            last_response_index <= NO_ID;
            last_response_family <= 8'd0;
            last_response_sub <= 8'd0;
            last_response_descriptor_id <= NO_ID;
            for (slot = 0; slot < 8; slot = slot + 1)
                policy_eos_token[slot] <= NO_ID;
            for (slot = 0; slot < 6; slot = slot + 1) begin
                slot_view_id[slot] <= NO_ID;
                slot_dtype[slot] <= 8'd0;
                slot_offset[slot] <= 64'd0;
                slot_rank[slot] <= 8'd0;
                slot_terms[slot] <= 8'd0;
                slot_object[slot] <= NO_ID;
                slot_permissions[slot] <= 32'd0;
                slot_dim0[slot] <= 32'd0;
                slot_dim1[slot] <= 32'd0;
                slot_dim2[slot] <= 32'd0;
                slot_stride0[slot] <= 32'd0;
                slot_stride1[slot] <= 32'd0;
                slot_stride2[slot] <= 32'd0;
                slot_tail_dims[slot] <= 32'd0;
                slot_tail_strides[slot] <= 32'd0;
                captured_id[slot] <= NO_ID;
                captured_extent[slot] <= 32'd0;
                captured_axis[slot] <= 8'd0;
                captured_offset[slot] <= 64'd0;
                captured_rank[slot] <= 8'd0;
            end
        end else begin
            engine_start <= 1'b0;
            desc_req <= 1'b0;

            if (clear) begin
                state <= S_IDLE;
                response_fault <= 1'b0;
                response_trap <= TRAP_NONE;
                captured_valid <= 6'd0;
                embedding_q <= 1'b0;
                rms_norm_q <= 1'b0;
                head_rms_norm_q <= 1'b0;
                rope_q <= 1'b0;
                dma_transfer_q <= 1'b0;
                matmul_q <= 1'b0;
                vector_add_q <= 1'b0;
                vector_silu_mul_q <= 1'b0;
                dma_scatter_q <= 1'b0;
                attention_gqa_q <= 1'b0;
                selection_argmax_q <= 1'b0;
                selection_token_append_q <= 1'b0;
                route_weight_normalize_q <= 1'b0;
                route_window_index_q <= 1'b0;
                route_biased_topk_q <= 1'b0;
                reduction_expert_sum_q <= 1'b0;
                slot_bound <= 6'd0;
                slot_cursor <= 3'd0;
                op_input2 <= NO_ID;
                op_input3 <= NO_ID;
                mapped_element_count <= 32'd0;
                mapped_left_base <= 32'd0;
                mapped_right_base <= 32'd0;
                mapped_third_base <= 32'd0;
                mapped_index_base <= 32'd0;
                mapped_output_base <= 32'd0;
                mapped_prior_base <= 32'd0;
                mapped_result_words <= 32'd0;
                mapped_work_words <= 32'd0;
                mapped_context <= 32'd0;
                mapped_vocabulary <= 32'd0;
                mapped_dtype_a <= 8'd0;
                observed_index_value <= 32'hffff_ffff;
                policy_ring_bound <= 1'b0;
                policy_selection_mode <= 8'hff;
                policy_eos_count <= 16'd0;
                policy_max_new_tokens <= 32'd0;
                policy_vocabulary <= 32'd0;
                rms_input_base_q <= 32'd0;
                rms_weight_base_q <= 32'd0;
                rope_input_base_q <= 32'd0;
                rope_coefficient_base_q <= 32'd0;
                matmul_weight_base_q <= 32'd0;
                op_aux0 <= NO_ID;
                op_aux1 <= NO_ID;
                op_aux2 <= NO_ID;
                launch_output_base_q <= 32'd0;
                real_launch_count <= 32'd0;
                dma_gather_launch_count <= 32'd0;
                embedding_launch_count <= 32'd0;
                rms_norm_launch_count <= 32'd0;
                head_rms_norm_launch_count <= 32'd0;
                rope_launch_count <= 32'd0;
                dma_transfer_launch_count <= 32'd0;
                matmul_launch_count <= 32'd0;
                vector_add_launch_count <= 32'd0;
                vector_silu_mul_launch_count <= 32'd0;
                dma_scatter_launch_count <= 32'd0;
                attention_gqa_launch_count <= 32'd0;
                selection_argmax_launch_count <= 32'd0;
                selection_token_append_launch_count <= 32'd0;
                selected_token <= 32'd0;
                selected_tie_multiplicity <= 32'd0;
                selected_eos_reason <= 8'd0;
                capability_fault_count <= 32'd0;
                descriptor_fault_count <= 32'd0;
                engine_fault_count <= 32'd0;
                last_response_index <= NO_ID;
                last_response_family <= 8'd0;
                last_response_sub <= 8'd0;
                last_response_descriptor_id <= NO_ID;
            end else begin
                if (view_valid && (view_slot < 6)) begin
                    captured_valid[view_slot] <= 1'b1;
                    captured_id[view_slot] <= view_descriptor_id;
                    captured_extent[view_slot] <= view_extent;
                    captured_axis[view_slot] <= view_extent_axis;
                    captured_offset[view_slot] <= view_element_offset;
                    captured_rank[view_slot] <= view_rank;
                end

                case (state)
                    S_IDLE: begin
                        if (issue_valid && placement_table_ready) begin
                            issue_family_q <= issue_family;
                            issue_sub_q <= issue_sub;
                            issue_descriptor_q <= issue_descriptor_id;
                            issue_index_q <= issue_index;
                            last_response_index <= issue_index;
                            last_response_family <= issue_family;
                            last_response_sub <= issue_sub;
                            last_response_descriptor_id <=
                                issue_descriptor_id;
                            if (!placement_table_unique) begin
                                // One object, one base.  A table that says
                                // otherwise is refused before anything is
                                // fetched, decoded or launched.
                                response_fault <= 1'b1;
                                //: Set +OT_BRIDGE_TRACE=1 to name which admission check rejected.
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display text into the mapped netlist
                                if (trace_bridge) $display("OT_BRIDGE_DESC_TRAP site=%0d", 1);
`endif
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else if (!(((issue_family == FAMILY_DMA) &&
                                   (issue_sub == DMA_GATHER)) ||
                                  ((issue_family == FAMILY_TENSOR) &&
                                   (issue_sub == TENSOR_EMBED_LOOKUP)) ||
                                  ((issue_family == FAMILY_TENSOR) &&
                                   (issue_sub == TENSOR_MATMUL)) ||
                                  ((issue_family == FAMILY_VECTOR) &&
                                   ((issue_sub == VECTOR_RMS_NORM) ||
                                    (issue_sub == VECTOR_HEAD_RMS_NORM) ||
                                    (issue_sub == VECTOR_ROPE))) ||
                                  ((issue_family == FAMILY_DMA) &&
                                   (issue_sub == DMA_TRANSFER)) ||
                                  (cfg_extended_placement_valid &&
                                   (((issue_family == FAMILY_VECTOR) &&
                                     ((issue_sub == VECTOR_ADD) ||
                                      (issue_sub == VECTOR_SILU_MUL))) ||
                                    ((issue_family == FAMILY_DMA) &&
                                     (issue_sub == DMA_SCATTER)) ||
                                    ((issue_family == FAMILY_ATTENTION) &&
                                     (issue_sub == ATTENTION_GQA)) ||
                                    ((issue_family == FAMILY_SELECTION) &&
                                     ((issue_sub == SELECTION_ARGMAX) ||
                                      (issue_sub == SELECTION_TOKEN_APPEND))) ||
                                    ((issue_family == FAMILY_ROUTE) &&
                                     ((issue_sub == ROUTE_WEIGHT_NORMALIZE) ||
                                      (issue_sub == ROUTE_WINDOW_INDEX) ||
                                      (issue_sub == ROUTE_BIASED_TOPK))) ||
                                    ((issue_family == FAMILY_REDUCTION) &&
                                     (issue_sub == REDUCTION_EXPERT_SUM)))))) begin
                                // No speculative launch and no shape guess.
                                response_fault <= 1'b1;
                                response_trap <= TRAP_CAPABILITY;
                                state <= S_RESPONSE;
                            end else begin
                                embedding_q <=
                                    (issue_family == FAMILY_TENSOR) &&
                                    (issue_sub == TENSOR_EMBED_LOOKUP);
                                rms_norm_q <=
                                    (issue_family == FAMILY_VECTOR) &&
                                    ((issue_sub == VECTOR_RMS_NORM) ||
                                     (issue_sub == VECTOR_HEAD_RMS_NORM));
                                head_rms_norm_q <=
                                    (issue_family == FAMILY_VECTOR) &&
                                    (issue_sub == VECTOR_HEAD_RMS_NORM);
                                rope_q <=
                                    (issue_family == FAMILY_VECTOR) &&
                                    (issue_sub == VECTOR_ROPE);
                                dma_transfer_q <=
                                    (issue_family == FAMILY_DMA) &&
                                    (issue_sub == DMA_TRANSFER);
                                matmul_q <=
                                    (issue_family == FAMILY_TENSOR) &&
                                    (issue_sub == TENSOR_MATMUL);
                                vector_add_q <= cfg_extended_placement_valid &&
                                    (issue_family == FAMILY_VECTOR) &&
                                    (issue_sub == VECTOR_ADD);
                                vector_silu_mul_q <=
                                    cfg_extended_placement_valid &&
                                    (issue_family == FAMILY_VECTOR) &&
                                    (issue_sub == VECTOR_SILU_MUL);
                                dma_scatter_q <= cfg_extended_placement_valid &&
                                    (issue_family == FAMILY_DMA) &&
                                    (issue_sub == DMA_SCATTER);
                                attention_gqa_q <=
                                    cfg_extended_placement_valid &&
                                    (issue_family == FAMILY_ATTENTION) &&
                                    (issue_sub == ATTENTION_GQA);
                                selection_argmax_q <=
                                    cfg_extended_placement_valid &&
                                    (issue_family == FAMILY_SELECTION) &&
                                    (issue_sub == SELECTION_ARGMAX);
                                selection_token_append_q <=
                                    cfg_extended_placement_valid &&
                                    (issue_family == FAMILY_SELECTION) &&
                                    (issue_sub == SELECTION_TOKEN_APPEND);
                                route_weight_normalize_q <=
                                    cfg_extended_placement_valid &&
                                    (issue_family == FAMILY_ROUTE) &&
                                    (issue_sub == ROUTE_WEIGHT_NORMALIZE);
                                route_window_index_q <=
                                    cfg_extended_placement_valid &&
                                    (issue_family == FAMILY_ROUTE) &&
                                    (issue_sub == ROUTE_WINDOW_INDEX);
                                route_biased_topk_q <=
                                    cfg_extended_placement_valid &&
                                    (issue_family == FAMILY_ROUTE) &&
                                    (issue_sub == ROUTE_BIASED_TOPK);
                                reduction_expert_sum_q <=
                                    cfg_extended_placement_valid &&
                                    (issue_family == FAMILY_REDUCTION) &&
                                    (issue_sub == REDUCTION_EXPERT_SUM);
                                observed_index_value <= 32'hffff_ffff;
                                desc_req <= 1'b1;
                                desc_id <= issue_descriptor_id;
                                state <= S_OP_WAIT;
                            end
                        end
                    end

                    S_OP_WAIT: begin
                        if (desc_valid && mapped_family_q) begin
                            // The six mapped families take the shared walk.
                            if (!mapped_operator_ok) begin
                                response_fault <= 1'b1;
                                //: Set +OT_BRIDGE_TRACE=1 to name which admission check rejected.
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display text into the mapped netlist
                                if (trace_bridge) $display("OT_BRIDGE_DESC_TRAP site=%0d", 2);
`endif
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                op_numeric <= desc_data[671:640];
                                op_input0 <= desc_data[735:704];
                                op_input1 <= desc_data[767:736];
                                op_input2 <= desc_data[799:768];
                                op_input3 <= desc_data[831:800];
                                op_output0 <= desc_data[863:832];
                                slot_bound <= expected_slot_mask;
                                slot_cursor <= 3'd0;
                                desc_req <= 1'b1;
                                desc_id <= desc_data[735:704];
                                state <= S_MAP_VIEW_WAIT;
                            end
                        end else if (desc_valid) begin
                            if (!descriptor_header_ok(
                                    desc_data, desc_fault, DESC_OPERATOR,
                                    32'd128, 32'd64
                                ) ||
                                (desc_data[519:512] != issue_family_q) ||
                                (desc_data[527:520] != issue_sub_q) ||
                                (desc_data[543:528] != 0) ||
                                (desc_data[639:608] == NO_ID) ||
                                (desc_data[671:640] == NO_ID) ||
                                (desc_data[703:672] == NO_ID) ||
                                (desc_data[735:704] == NO_ID) ||
                                (!dma_transfer_q &&
                                 (desc_data[767:736] == NO_ID)) ||
                                (dma_transfer_q &&
                                 (desc_data[767:736] != NO_ID)) ||
                                (desc_data[799:768] != NO_ID) ||
                                (desc_data[831:800] != NO_ID) ||
                                (desc_data[863:832] == NO_ID) ||
                                (desc_data[895:864] != NO_ID) ||
                                ((head_rms_norm_q || rope_q) &&
                                 (desc_data[927:896] == NO_ID)) ||
                                (!(head_rms_norm_q || rope_q) &&
                                 (desc_data[927:896] != NO_ID)) ||
                                (rope_q &&
                                 (desc_data[927:896] != HEAD_WIDTH) &&
                                 (desc_data[927:896] != 2 * HEAD_WIDTH)) ||
                                (desc_data[959:928] != NO_ID) ||
                                (desc_data[991:960] != NO_ID) ||
                                (desc_data[1023:992] != NO_ID) ||
                                (desc_data[223:192] !=
                                 desc_data[671:640]) ||
                                (!dma_transfer_q &&
                                 (captured_valid != 6'b010011)) ||
                                (dma_transfer_q &&
                                 (captured_valid != 6'b010001)) ||
                                (captured_id[0] != desc_data[735:704]) ||
                                (!dma_transfer_q &&
                                 (captured_id[1] != desc_data[767:736])) ||
                                (captured_id[4] != desc_data[863:832])) begin
                                response_fault <= 1'b1;
                                //: Set +OT_BRIDGE_TRACE=1 to name which admission check rejected.
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display text into the mapped netlist
                                if (trace_bridge) $display("OT_BRIDGE_DESC_TRAP site=%0d", 3);
`endif
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                op_numeric <= desc_data[671:640];
                                op_input0 <= desc_data[735:704];
                                op_input1 <= desc_data[767:736];
                                op_output0 <= desc_data[863:832];
                                op_aux0 <= desc_data[927:896];
                                op_aux1 <= desc_data[959:928];
                                op_aux2 <= desc_data[991:960];
                                desc_req <= 1'b1;
                                desc_id <= desc_data[735:704];
                                state <= (rms_norm_q || matmul_q || rope_q)
                                      ? S_RMS_INPUT_WAIT
                                      : dma_transfer_q ? S_SOURCE_WAIT
                                      : S_INDEX_WAIT;
                            end
                        end
                    end

                    S_INDEX_WAIT: begin
                        if (desc_valid) begin
                            if (!descriptor_header_ok(
                                    desc_data, desc_fault, DESC_TENSOR_VIEW,
                                    32'd192, 32'd128
                                ) ||
                                (desc_view_dtype != FMT_U32) ||
                                (desc_view_rank != 8'd1) ||
                                (desc_view_layout != 8'd0) ||
                                (desc_view_terms > 8'd4) ||
                                (desc_view_scale_object != NO_ID) ||
                                (desc_view_scale_block != 32'd0) ||
                                (desc_primary_object == NO_ID) ||
                                ((desc_permissions & 32'd1) == 0) ||
                                (desc_view_dim0 == 0) ||
                                (desc_view_dim1 != 0) ||
                                (desc_view_dim2 != 0) ||
                                (desc_view_dim3 != 0) ||
                                (desc_view_dim4 != 0) ||
                                (desc_view_dim5 != 0) ||
                                (desc_view_stride0 != 1) ||
                                (desc_view_stride1 != 0) ||
                                (desc_view_stride2 != 0) ||
                                (desc_view_stride3 != 0) ||
                                (desc_view_stride4 != 0) ||
                                (desc_view_stride5 != 0) ||
                                (captured_rank[0] != 1) ||
                                (captured_axis[0] != 0) ||
                                //: The index vector's extent IS the span: one
                                //: index per gathered row, S of them for an
                                //: S-token prompt.
                                !span_admitted) begin
                                response_fault <= 1'b1;
                                //: Set +OT_BRIDGE_TRACE=1 to name which admission check rejected.
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display text into the mapped netlist
                                if (trace_bridge) $display("OT_BRIDGE_DESC_TRAP site=%0d", 4);
`endif
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                index_raw_dim0 <= desc_view_dim0;
                                //: Where the token id lives, for the lookup below.
                                embed_index_addr_q <= desc_place[31:0] +
                                    captured_offset[0][31:0];
                                desc_req <= 1'b1;
                                desc_id <= op_input1;
                                state <= S_SOURCE_WAIT;
                            end
                        end
                    end

                    S_RMS_INPUT_WAIT: begin
                        if (desc_valid) begin
                            if (!input_view_common_ok ||
                                !(model_row_input_source_ok ||
                                  head_rms_input_source_ok ||
                                  rope_input_source_ok) ||
                                // Every one of these four families reads its
                                // input at the object's own base now; the
                                // three that used to take an unkeyed base
                                // are checked the same way as the two that
                                // did not.
                                !desc_object_placed ||
                                (head_rms_norm_q &&
                                 (op_aux0 != desc_view_dim1))) begin
                                response_fault <= 1'b1;
                                //: Set +OT_BRIDGE_TRACE=1 to name which admission check rejected.
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display text into the mapped netlist
                                if (trace_bridge) $display("OT_BRIDGE_DESC_TRAP site=%0d", 5);
`endif
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                index_raw_dim0 <= desc_view_dim0;
                                source_rows <= (head_rms_norm_q || rope_q)
                                    ? desc_view_dim1
                                    : (matmul_q ? 32'd0 : 32'd1);
                                //: The reduction length the weight must match.
                                source_trailing <= (head_rms_norm_q || rope_q)
                                    ? desc_view_dim2 : desc_view_dim1;
                                source_dtype <= FMT_BF16;
                                rms_input_base_q <= desc_place[31:0] +
                                    captured_offset[0][31:0];
                                if (rope_q)
                                    rope_input_base_q <= desc_place[31:0] +
                                        captured_offset[0][31:0];
                                desc_req <= 1'b1;
                                desc_id <= op_input1;
                                state <= S_SOURCE_WAIT;
                            end
                        end
                    end


                    // -- the shared admission walk of the six mapped
                    // families.  Every bound view is fetched in slot order
                    // into the slot register file; nothing about a slot is
                    // inferred from another slot's record.
                    S_MAP_VIEW_WAIT: begin
                        if (desc_valid) begin
                            if (!mapped_view_header_ok) begin
                                response_fault <= 1'b1;
                                //: Set +OT_BRIDGE_TRACE=1 to name which admission check rejected.
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display text into the mapped netlist
                                if (trace_bridge) $display("OT_BRIDGE_DESC_TRAP site=%0d", 6);
`endif
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                slot_view_id[slot_cursor] <= desc_id;
                                slot_dtype[slot_cursor] <= desc_view_dtype;
                                slot_offset[slot_cursor] <= desc_view_offset;
                                slot_rank[slot_cursor] <= desc_view_rank;
                                slot_terms[slot_cursor] <= desc_view_terms;
                                slot_object[slot_cursor] <= desc_primary_object;
                                slot_place_base[slot_cursor] <= desc_place[31:0];
                                slot_place_found[slot_cursor] <= desc_object_placed;
                                slot_permissions[slot_cursor] <= desc_permissions;
                                slot_dim0[slot_cursor] <= desc_view_dim0;
                                slot_dim1[slot_cursor] <= desc_view_dim1;
                                slot_dim2[slot_cursor] <= desc_view_dim2;
                                slot_stride0[slot_cursor] <= desc_view_stride0;
                                slot_stride1[slot_cursor] <= desc_view_stride1;
                                slot_stride2[slot_cursor] <= desc_view_stride2;
                                slot_tail_dims[slot_cursor] <=
                                    desc_view_dim3 | desc_view_dim4 |
                                    desc_view_dim5;
                                slot_tail_strides[slot_cursor] <=
                                    desc_view_stride3 | desc_view_stride4 |
                                    desc_view_stride5;
                                if (next_slot_w == 3'd6) begin
                                    desc_req <= 1'b1;
                                    desc_id <= op_numeric;
                                    state <= S_MAP_NUM_WAIT;
                                end else begin
                                    slot_cursor <= next_slot_w;
                                    desc_req <= 1'b1;
                                    desc_id <= next_slot_descriptor_id;
                                end
                            end
                        end
                    end

                    S_MAP_NUM_WAIT: begin
                        if (desc_valid) begin
                            if (!mapped_numeric_ok) begin
                                response_fault <= 1'b1;
                                //: Set +OT_BRIDGE_TRACE=1 to name which admission check rejected.
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display text into the mapped netlist
                                if (trace_bridge) begin
                                    $display("OT_BRIDGE_DESC_TRAP site=%0d gqa=%0b in=0x%0h second=0x%0h out=0x%0h scale=0x%08h want_scale=0x%08h",
                                             7, attention_gqa_q, numeric_input_dtype,
                                             numeric_second_dtype, numeric_output_dtype,
                                             desc_data[639:608], GQA_SCALE_BITS);
                                    $display("  contract=0x%h", desc_data[1023:768]);
                                    $display("  want    =0x%h", CONTRACT_QWEN_GQA_RAW);
                                end
`endif
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                numeric_profile_dtypes <= {
                                    desc_data[535:528],
                                    desc_data[543:536],
                                    desc_data[527:520],
                                    desc_data[519:512]
                                };
                                // The placement map is checked here, before
                                // any operand address is formed, so an
                                // instance with no bank bound to an object
                                // performs no read at all.  A missing bank is
                                // a capability this instance does not have,
                                // not a malformed descriptor.
                                if (!mapped_bases_found) begin
                                    response_fault <= 1'b1;
                                    response_trap <= TRAP_CAPABILITY;
                                    state <= S_RESPONSE;
                                end else if (!mapped_shape_ok) begin
                                    response_fault <= 1'b1;
                                    //: Set +OT_BRIDGE_TRACE=1 to name which admission check rejected.
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display text into the mapped netlist
                                    if (trace_bridge) $display("OT_BRIDGE_DESC_TRAP site=%0d", 8);
`endif
                                    response_trap <= TRAP_DESCRIPTOR;
                                    state <= S_RESPONSE;
                                end else if (selection_token_append_q) begin
                                    desc_req <= 1'b1;
                                    desc_id <= cfg_generation_policy_id;
                                    state <= S_MAP_POLICY_WAIT;
                                end else if (dma_scatter_q ||
                                             attention_gqa_q) begin
                                    state <= S_MAP_INDEX_ISSUE;
                                end else begin
                                    state <= S_MAP_ADMIT;
                                end
                            end
                        end
                    end

                    S_MAP_POLICY_WAIT: begin
                        if (desc_valid) begin
                            if (!policy_record_ok) begin
                                response_fault <= 1'b1;
                                //: Set +OT_BRIDGE_TRACE=1 to name which admission check rejected.
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display text into the mapped netlist
                                if (trace_bridge) $display("OT_BRIDGE_DESC_TRAP site=%0d", 9);
`endif
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                policy_selection_mode <= desc_data[519:512];
                                policy_eos_count <= desc_data[543:528];
                                policy_max_new_tokens <= desc_data[575:544];
                                policy_vocabulary <= desc_data[607:576];
                                policy_eos_token[0] <= desc_data[671:640];
                                policy_eos_token[1] <= desc_data[703:672];
                                policy_eos_token[2] <= desc_data[735:704];
                                policy_eos_token[3] <= desc_data[767:736];
                                policy_eos_token[4] <= desc_data[799:768];
                                policy_eos_token[5] <= desc_data[831:800];
                                policy_eos_token[6] <= desc_data[863:832];
                                policy_eos_token[7] <= desc_data[895:864];
                                policy_ring_bound <= 1'b1;
                                state <= S_MAP_ADMIT;
                            end
                        end
                    end

                    // The scatter row and the attention context are the same
                    // position, and the index view is the only architectural
                    // statement of it.  It is read before either engine runs.
                    S_MAP_INDEX_ISSUE: state <= S_MAP_INDEX_WAIT;

                    S_MAP_INDEX_WAIT: begin
                        observed_index_value <= m0_rd_data;
                        state <= S_MAP_ADMIT;
                    end

                    S_MAP_ADMIT: begin
                        if ((dma_scatter_q || attention_gqa_q) &&
                            !mapped_context_ok) begin
                            response_fault <= 1'b1;
                            //: Set +OT_BRIDGE_TRACE=1 to name which admission check rejected.
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display
                //: text into the mapped netlist, where OpenSTA cannot parse it
                            if (trace_bridge)
                                $display("OT_BRIDGE_DESC_TRAP site=%0d ctxlen=%0d planerows=%0d observed=%0d | slot0_map=%0d found=%0b off0=%0d slot0_base=%0d obj0=%0d",
                                         10, cfg_context_length, cfg_kv_plane_rows,
                                         observed_index_value, slot0_map[31:0], slot0_map[32],
                                         captured_offset[0][31:0], slot0_base, slot_object[0]);
`endif
                            response_trap <= TRAP_DESCRIPTOR;
                            state <= S_RESPONSE;
                        end else begin
                            mapped_left_base <= slot0_base;
                            mapped_right_base <= slot1_base;
                            mapped_third_base <= slot2_base;
                            mapped_index_base <= mapped_index_slot_base;
                            mapped_output_base <= slot4_base;
                            mapped_prior_base <= slot4_base;
                            mapped_context <= cfg_context_length;
                            mapped_vocabulary <= argmax_vocabulary;
                            mapped_dtype_a <= slot_dtype[0];
                            //: THE SAME THREE COUNTS FOR THE MAPPED FAMILIES,
                            //: each the per-position figure times the span.
                            //: ``elementwise_width`` and ``KV_PLANE_WORDS`` are
                            //: one row's worth; a span-S launch presents S rows
                            //: contiguously, which is what makes the product --
                            //: and not a second base or stride -- the whole
                            //: change on this path.
                            //:
                            //:   ADD / SILU_MUL  S rows of elementwise_width,
                            //:     one flat count; SILU_MUL reads two operands
                            //:     per output, hence the leading two.
                            //:   SCATTER  S KV rows written (moved_elements)
                            //:     and S indices validated (indices_checked).
                            //:   GQA  S query rows of GQA_OUTPUT_WORDS, and one
                            //:     score multiply per query element per context
                            //:     position per row.  The engine's own header
                            //:     states score_multiply_count = S * C *
                            //:     QUERY_HEADS * HEAD_WIDTH: a MASKED position
                            //:     is still read and multiplied, the mask is
                            //:     applied to the score afterwards, so the
                            //:     count does not shrink with causality.
                            //:   ARGMAX / TOKEN_APPEND  span-1 by
                            //:     construction, so the span factor is one and
                            //:     these legs are unchanged.
                            mapped_element_count <=
                                (vector_add_q || vector_silu_mul_q)
                                ? (request_span * elementwise_width)
                                : selection_argmax_q ? argmax_vocabulary
                                : 32'd1;
                            //: AN OPERATOR THAT WRITES MORE THAN ONE WORD MUST
                            //: SAY SO HERE.  The fallthrough is 32'd1, and the
                            //: bridge refuses an engine whose own counters
                            //: disagree with this expectation -- so a new mapped
                            //: family that omits its leg is admitted, runs
                            //: correctly, and is then failed by its own bridge
                            //: with TRAP_ENGINE. The prefix regression cannot
                            //: catch it, because no Qwen3 program issues the
                            //: operator whose leg is missing.
                            mapped_result_words <=
                                (vector_add_q || vector_silu_mul_q)
                                ? (request_span * elementwise_width)
                                : dma_scatter_q
                                ? (request_span * KV_PLANE_WORDS)
                                : attention_gqa_q
                                ? (request_span * GQA_OUTPUT_WORDS)
                                //: groups x slots, which is the reference's own
                                //: reduction.elements for this operator.
                                : route_weight_normalize_q
                                ? (request_span * weight_normalize_slots)
                                //: Every slot of every query row is written,
                                //: padding included -- the engine's out_count.
                                : route_window_index_q
                                ? (request_span * window_index_slots)
                                //: The IDS only. The weights are a second view
                                //: and the engine counts ids, so counting both
                                //: here would refuse a correct launch.
                                : route_biased_topk_q
                                ? (request_span * biased_topk_slots)
                                //: One row of the view's width. request_span is
                                //: one by construction for this family.
                                : reduction_expert_sum_q ? expert_sum_width
                                : 32'd1;
                            mapped_work_words <=
                                vector_add_q
                                ? (request_span * elementwise_width)
                                : vector_silu_mul_q
                                ? (32'd2 * request_span * elementwise_width)
                                : selection_argmax_q ? argmax_vocabulary
                                : attention_gqa_q
                                ? (request_span * cfg_context_length *
                                   QUERY_HEADS * HEAD_WIDTH)
                                : dma_scatter_q ? request_span
                                : route_weight_normalize_q
                                ? (request_span * weight_normalize_slots)
                                //: The engine counts CANDIDATES -- the real KV
                                //: rows it selected, padding excluded -- which
                                //: is not the same as the words it wrote.
                                : route_window_index_q ? widx_candidates
                                //: Every expert is ranked, not just the winners.
                                : route_biased_topk_q
                                ? (request_span * biased_topk_experts)
                                : reduction_expert_sum_q ? expert_sum_width
                                : 32'd1;
                            state <= S_START;
                        end
                    end

                    S_SOURCE_WAIT: begin
                        if (desc_valid) begin
                            if (!input_view_common_ok ||
                                !(dense_row_source_ok ||
                                  rms_weight_source_ok ||
                                  rope_coefficient_source_ok ||
                                  matmul_weight_source_ok ||
                                  transfer_source_ok) ||
                                // The weight-side operand of every family
                                // that has one: the RMSNorm gain, the head
                                // gain, the RoPE coefficient table and the
                                // projection matrix all resolve through the
                                // one table.  DMA.TRANSFER and DMA.GATHER
                                // sweep a staged region instead and are not
                                // asked for an object.
                                ((matmul_q || rms_norm_q || rope_q) &&
                                 !desc_object_placed)) begin
                                response_fault <= 1'b1;
                                //: Set +OT_BRIDGE_TRACE=1 to name which admission check rejected.
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display text into the mapped netlist
                                if (trace_bridge) begin
                                    $display("OT_BRIDGE_DESC_TRAP site=%0d common=%0b dense=%0b rmsw=%0b rope=%0b mmw=%0b xfer=%0b placed=%0b emb=%0b",
                                             11, input_view_common_ok, dense_row_source_ok,
                                             rms_weight_source_ok, rope_coefficient_source_ok,
                                             matmul_weight_source_ok, transfer_source_ok,
                                             desc_object_placed, embedding_q);
                                    $display("  regs: source_rows=%0d source_trailing=%0d rms=%0b hrms=%0b matmul=%0b rope=%0b",
                                             source_rows, source_trailing, rms_norm_q,
                                             head_rms_norm_q, matmul_q, rope_q);
                                    $display("  view: rank=%0d dtype=0x%0h terms=%0d dims=%0d,%0d,%0d,%0d strides=%0d,%0d obj=%0d perm=0x%0h",
                                             desc_view_rank, desc_view_dtype, desc_view_terms,
                                             desc_view_dim0, desc_view_dim1, desc_view_dim2,
                                             desc_view_dim3, desc_view_stride0, desc_view_stride1,
                                             desc_primary_object, desc_permissions);
                                end
`endif
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                if (dma_transfer_q) begin
                                    index_raw_dim0 <= desc_view_dim0;
                                    source_rows <= 32'd1;
                                    source_trailing <= EMBEDDING_WIDTH;
                                    source_dtype <= FMT_BF16;
                                end else if (rms_norm_q) begin
                                    rms_weight_base_q <= desc_place[31:0] +
                                        captured_offset[1][31:0];
                                end else if (rope_q) begin
                                    rope_coefficient_base_q <=
                                        desc_place[31:0] +
                                        captured_offset[1][31:0];
                                end else if (!rms_norm_q) begin
                                    source_rows <= desc_view_dim0;
                                    source_trailing <= desc_view_dim1;
                                    source_dtype <= desc_view_dtype;
                                    if (embedding_q)
                                        embed_table_base_q <= desc_place[31:0] +
                                            captured_offset[1][31:0];
                                    else if (!matmul_q)
                                        gather_source_base_q <=
                                            desc_place[31:0] +
                                            captured_offset[1][31:0];
                                    if (matmul_q)
                                        matmul_weight_base_q <=
                                            desc_place[31:0] +
                                            captured_offset[1][31:0];
                                end
                                desc_req <= 1'b1;
                                desc_id <= op_output0;
                                state <= S_OUTPUT_WAIT;
                            end
                        end
                    end

                    S_OUTPUT_WAIT: begin
                        if (desc_valid) begin
                            if (!output_view_common_ok ||
                                !(dense_row_output_ok ||
                                  head_rms_output_ok ||
                                  rope_output_ok ||
                                  matmul_output_ok ||
                                  transfer_output_ok) ||
                                // A result has an address because its own
                                // object has one.  There is no cursor to
                                // fall back on any more, so an unplaced
                                // result object is a refusal and not a
                                // write to wherever the last one ended.
                                !desc_object_placed) begin
                                response_fault <= 1'b1;
                                //: Set +OT_BRIDGE_TRACE=1 to name which admission check rejected.
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display text into the mapped netlist
                                if (trace_bridge) $display("OT_BRIDGE_DESC_TRAP site=%0d", 12);
`endif
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                launch_output_base_q <= desc_place[31:0] +
                                    captured_offset[4][31:0];
                                desc_req <= 1'b1;
                                desc_id <= op_numeric;
                                state <= S_NUM_WAIT;
                            end
                        end
                    end

                    S_NUM_WAIT: begin
                        if (desc_valid) begin
                            if (!numeric_common_ok ||
                                !(gather_numeric_ok ||
                                  embedding_numeric_ok ||
                                  rms_numeric_ok ||
                                  rope_numeric_ok ||
                                  matmul_numeric_ok ||
                                  transfer_numeric_ok)) begin
                                response_fault <= 1'b1;
                                //: Set +OT_BRIDGE_TRACE=1 to name which admission check rejected.
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display text into the mapped netlist
                                if (trace_bridge) $display("OT_BRIDGE_DESC_TRAP site=%0d", 13);
`endif
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                numeric_profile_dtypes <= {
                                    desc_data[535:528],
                                    desc_data[543:536],
                                    desc_data[527:520],
                                    desc_data[519:512]
                                };
                                state <= (embedding_q &&
                                          (EMBEDDING_TOKEN_INDEXED != 0))
                                    ? S_EMBED_INDEX_ISSUE : S_START;
                            end
                        end
                    end

                    //: One registered read of the resolved index, then start.
                    //: Two states because the bank answers on the cycle after
                    //: the address, exactly as the mapped families' probe does.
                    S_EMBED_INDEX_ISSUE: state <= S_EMBED_INDEX_WAIT;

                    S_EMBED_INDEX_WAIT: begin
                        embed_token_q <= m0_rd_data;
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display
                //: text into the mapped netlist, where OpenSTA cannot parse it
                        if (trace_bridge)
                            $display("OT_BRIDGE_EMBED addr=%0d token=%0d table_base=%0d row=%0d",
                                     embed_index_addr_q, m0_rd_data,
                                     embed_table_base_q,
                                     embed_table_base_q + m0_rd_data * EMBEDDING_WIDTH);
`endif
                        state <= S_START;
                    end

                    S_START: begin
                        engine_start <= 1'b1;
                        state <= S_ENGINE_WAIT;
                    end

                    S_ENGINE_WAIT: begin
                        if (engine_done) begin
                            if ((engine_error_code != ERR_NONE) ||
                                (engine_result_count != expected_result_count) ||
                                (engine_work_count != expected_work_count)) begin
                                response_fault <= 1'b1;
                                //: Set +OT_BRIDGE_TRACE=1 to see which of the
                                //: three completion conditions failed.
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display
                //: text into the mapped netlist, where OpenSTA cannot parse it
                                if (trace_bridge)
                                    $display("OT_BRIDGE_ENGINE_FAULT err=%0d results=%0d/%0d work=%0d/%0d fam=0x%0h sub=0x%0h rows=%0d trailing=%0d",
                                             engine_error_code, engine_result_count,
                                             expected_result_count, engine_work_count,
                                             expected_work_count, issue_family_q,
                                             issue_sub_q, source_rows, source_trailing);
`endif
                                response_trap <= mapped_capability_refusal
                                    ? TRAP_CAPABILITY : TRAP_ENGINE;
                            end else begin
                                response_fault <= 1'b0;
                                response_trap <= TRAP_NONE;
                            end
                            state <= S_RESPONSE;
                        end
                    end

                    S_RESPONSE: begin
                        if (response_fire) begin
                            if (!response_fault) begin
                                real_launch_count <= real_launch_count + 1;
                                if (vector_add_q)
                                    vector_add_launch_count <=
                                        vector_add_launch_count + 1;
                                else if (vector_silu_mul_q)
                                    vector_silu_mul_launch_count <=
                                        vector_silu_mul_launch_count + 1;
                                else if (dma_scatter_q)
                                    dma_scatter_launch_count <=
                                        dma_scatter_launch_count + 1;
                                else if (attention_gqa_q)
                                    attention_gqa_launch_count <=
                                        attention_gqa_launch_count + 1;
                                else if (selection_argmax_q) begin
                                    selection_argmax_launch_count <=
                                        selection_argmax_launch_count + 1;
                                    selected_token <= array_token;
                                    selected_tie_multiplicity <=
                                        array_tie_multiplicity;
                                end
                                else if (selection_token_append_q) begin
                                    selection_token_append_launch_count <=
                                        selection_token_append_launch_count + 1;
                                    selected_token <= append_token;
                                    selected_eos_reason <= append_eos_reason;
                                end
                                else if (head_rms_norm_q)
                                    head_rms_norm_launch_count <=
                                        head_rms_norm_launch_count + 1;
                                else if (rope_q)
                                    rope_launch_count <=
                                        rope_launch_count + 1;
                                else if (rms_norm_q)
                                    rms_norm_launch_count <=
                                        rms_norm_launch_count + 1;
                                else if (matmul_q)
                                    matmul_launch_count <=
                                        matmul_launch_count + 1;
                                else if (dma_transfer_q)
                                    dma_transfer_launch_count <=
                                        dma_transfer_launch_count + 1;
                                else if (embedding_q)
                                    embedding_launch_count <=
                                        embedding_launch_count + 1;
                                else
                                    dma_gather_launch_count <=
                                        dma_gather_launch_count + 1;
                            end else if (response_trap == TRAP_CAPABILITY)
                                capability_fault_count <=
                                    capability_fault_count + 1;
                            else if (response_trap == TRAP_DESCRIPTOR)
                                descriptor_fault_count <=
                                    descriptor_fault_count + 1;
                            else
                                engine_fault_count <= engine_fault_count + 1;
                            captured_valid <= 6'd0;
                            state <= S_IDLE;
                        end
                    end

                    default: state <= S_IDLE;
                endcase
            end
        end
    end

    wire array_m0_rd_en;
    wire [31:0] array_m0_rd_addr;
    wire array_m1_rd_en;
    wire [31:0] array_m1_rd_addr;
    wire array_m2_rd_en;
    wire [31:0] array_m2_rd_addr;
    wire array_m3_rd_en;
    wire [31:0] array_m3_rd_addr;
    wire array_out_we;
    wire [31:0] array_out_addr;
    wire [31:0] array_out_data;
    wire array_busy;
    wire array_done;
    wire [7:0] array_error_code;
    wire [31:0] array_result_count;
    wire [31:0] array_saturation_count;
    wire [31:0] array_work_count;
    wire [31:0] array_token;
    wire [31:0] array_tie_multiplicity;

    wire rms_input_rd_en;
    wire [31:0] rms_input_rd_addr;
    wire rms_weight_rd_en;
    wire [31:0] rms_weight_rd_addr;
    wire rms_out_we;
    wire [31:0] rms_out_addr;
    wire [31:0] rms_out_data;
    wire rms_busy;
    wire rms_done;
    wire [7:0] rms_error_code;
    wire [31:0] rms_result_count;
    wire [31:0] rms_saturation_count;
    wire [31:0] rms_work_count;

    wire silu_a_rd_en;
    wire [31:0] silu_a_rd_addr;
    wire silu_b_rd_en;
    wire [31:0] silu_b_rd_addr;
    wire silu_out_we;
    wire [31:0] silu_out_addr;
    wire [31:0] silu_out_data;
    wire silu_busy;
    wire silu_done;
    wire [7:0] silu_error_code;
    wire [31:0] silu_result_count;
    wire [31:0] silu_work_count;
    wire [31:0] silu_saturation_count;
    wire [31:0] silu_activation_saturation_count;

    wire append_a_rd_en;
    wire [31:0] append_a_rd_addr;
    wire append_out_we;
    wire [31:0] append_out_addr;
    wire [31:0] append_out_data;
    wire append_busy;
    wire append_done;
    wire [7:0] append_error_code;
    wire append_refusal_capability;
    wire [31:0] append_token;
    wire [7:0] append_eos_reason;
    wire [31:0] append_result_count;
    wire [31:0] append_work_count;

    wire gqa_mem_req_valid;
    wire [31:0] gqa_mem_req_addr;
    reg  gqa_mem_rsp_valid;
    wire gqa_out_valid;
    wire [31:0] gqa_out_addr;
    wire [31:0] gqa_out_data;
    wire gqa_busy;
    wire gqa_done;
    wire gqa_failed;
    wire [7:0] gqa_error_code;
    wire [31:0] gqa_memory_read_count;
    wire [31:0] gqa_result_count;
    wire [31:0] gqa_work_count;
    wire [31:0] gqa_exponential_count;
    wire [31:0] gqa_value_multiply_count;
    wire [31:0] gqa_saturation_count;

    // The attention engine speaks one-outstanding ready/valid; the operand
    // bank answers one cycle after an enabled address.  The two are the same
    // contract with different spellings, so the adaptation is exactly this
    // one register and no queue.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            gqa_mem_rsp_valid <= 1'b0;
        else
            gqa_mem_rsp_valid <= gqa_mem_req_valid & attention_gqa_q;
    end

    wire [EXPERT_SUM_MAX_EXPERTS-1:0]    esum_val_rd_en;
    wire [EXPERT_SUM_MAX_EXPERTS*32-1:0] esum_val_rd_addr;
    wire esum_wgt_rd_en;
    wire [31:0] esum_wgt_rd_addr;
    wire esum_base_rd_en;
    wire [31:0] esum_base_rd_addr;
    wire esum_out_we;
    wire [31:0] esum_out_addr;
    wire [31:0] esum_out_data;
    wire esum_busy;
    wire esum_done;
    wire [7:0] esum_error_code;
    wire [31:0] esum_out_count;
    wire [31:0] esum_saturation_count;
    //: THE WEIGHT READ AND THE VALUE WALK DO NOT OVERLAP IN TIME.  The engine
    //: asserts wgt_rd_en only in S_WEIGHT and val_rd_en only in S_WALK, so m0
    //: carries the weight vector first and expert 0's row afterwards. That is
    //: what lets a four-expert reduction fit four ports when it nominally wants
    //: five; the engine's own testbench fails on any cycle where both fire.
    wire esum_m0_rd_en = esum_wgt_rd_en | esum_val_rd_en[0];
    wire [31:0] esum_m0_rd_addr =
        esum_wgt_rd_en ? esum_wgt_rd_addr : esum_val_rd_addr[31:0];

    wire btk_score_rd_en;
    wire [31:0] btk_score_rd_addr;
    wire btk_bias_rd_en;
    wire [31:0] btk_bias_rd_addr;
    wire btk_id_we;
    wire [31:0] btk_id_addr;
    wire [31:0] btk_id_data;
    wire btk_wgt_we;
    wire [31:0] btk_wgt_addr;
    wire [31:0] btk_wgt_data;
    wire btk_busy;
    wire btk_done;
    wire [7:0] btk_error_code;
    wire [31:0] btk_selected;
    wire [31:0] btk_candidates;
    //: THE ENGINE EMITS IN TWO PASSES, so exactly one of these is high on any
    //: cycle and the bridge's single result port carries both views. The
    //: engine's own testbench fails on any cycle where both fire, which is what
    //: makes this mux sound rather than lucky.
    wire btk_out_we = btk_id_we | btk_wgt_we;
    wire [31:0] btk_out_addr = btk_id_we ? btk_id_addr : btk_wgt_addr;
    wire [31:0] btk_out_data = btk_id_we ? btk_id_data : btk_wgt_data;

    wire widx_pos_rd_en;
    wire [31:0] widx_pos_rd_addr;
    wire widx_out_we;
    wire [31:0] widx_out_addr;
    wire [31:0] widx_out_data;
    wire widx_busy;
    wire widx_done;
    wire [7:0] widx_error_code;
    wire [31:0] widx_out_count;
    wire [31:0] widx_candidates;

    wire norm_wgt_rd_en;
    wire [31:0] norm_wgt_rd_addr;
    wire norm_out_we;
    wire [31:0] norm_out_addr;
    wire [31:0] norm_out_data;
    wire norm_busy;
    wire norm_done;
    wire [7:0] norm_error_code;
    wire [31:0] norm_result_count;
    wire [31:0] norm_saturation_count;

    wire rope_input_rd_en;
    wire [31:0] rope_input_rd_addr;
    wire rope_coefficient_rd_en;
    wire [31:0] rope_coefficient_rd_addr;
    wire rope_out_we;
    wire [31:0] rope_out_addr;
    wire [31:0] rope_out_data;
    wire rope_busy;
    wire rope_done;
    wire [7:0] rope_error_code;
    wire [31:0] rope_result_count;
    wire [31:0] rope_saturation_count;
    wire [31:0] rope_work_count;

    wire engine_done = rope_q ? rope_done
        : rms_norm_q ? rms_done
        : vector_silu_mul_q ? silu_done
        : selection_token_append_q ? append_done
        : route_weight_normalize_q ? norm_done
        : route_window_index_q ? widx_done
        : route_biased_topk_q ? btk_done
        : reduction_expert_sum_q ? esum_done
        : attention_gqa_q ? gqa_done : array_done;
    assign engine_busy = rope_q ? rope_busy
        : rms_norm_q ? rms_busy
        : vector_silu_mul_q ? silu_busy
        : selection_token_append_q ? append_busy
        : route_weight_normalize_q ? norm_busy
        : route_window_index_q ? widx_busy
        : route_biased_topk_q ? btk_busy
        : reduction_expert_sum_q ? esum_busy
        : attention_gqa_q ? gqa_busy : array_busy;
    assign engine_error_code = rope_q ? rope_error_code
        : rms_norm_q ? rms_error_code
        : vector_silu_mul_q ? silu_error_code
        : selection_token_append_q ? append_error_code
        : route_weight_normalize_q ? norm_error_code
        : route_window_index_q ? widx_error_code
        : route_biased_topk_q ? btk_error_code
        : reduction_expert_sum_q ? esum_error_code
        : attention_gqa_q ? gqa_error_code : array_error_code;
    assign engine_result_count = rope_q ? rope_result_count
        : rms_norm_q ? rms_result_count
        : vector_silu_mul_q ? silu_result_count
        : selection_token_append_q ? append_result_count
        : route_weight_normalize_q ? norm_result_count
        : route_window_index_q ? widx_out_count
        : route_biased_topk_q ? btk_selected
        : reduction_expert_sum_q ? esum_out_count
        : attention_gqa_q ? gqa_result_count : array_result_count;
    assign engine_work_count = rope_q ? rope_work_count
        : rms_norm_q ? rms_work_count
        : vector_silu_mul_q ? silu_work_count
        : selection_token_append_q ? append_work_count
        : route_weight_normalize_q ? norm_result_count
        : route_window_index_q ? widx_candidates
        : route_biased_topk_q ? btk_candidates
        : reduction_expert_sum_q ? esum_out_count
        : attention_gqa_q ? gqa_work_count : array_work_count;
    //: THE TWO SELF-CHECKS THE BRIDGE HOLDS AN ENGINE TO, and the reason a
    //: correct 16-row launch used to come back as TRAP_ENGINE.
    //:
    //: Neither expression read the span.  ``source_rows`` and
    //: ``source_trailing`` are the DECLARED row and column counts of ONE
    //: sequence position -- captured from the descriptor image, which carries no
    //: span -- so both counts described a single row however many the sequencer
    //: resolved.  An engine that correctly retired S rows then reported S times
    //: the expected result count and was refused by its own bridge.
    //:
    //: Each leg is the per-position count multiplied by the span, because that
    //: is precisely what a span-S launch is; the multiplication is written once
    //: per leg rather than hoisted, because the three families factor
    //: differently and a shared product would hide which one is which.
    //:
    //:   RMSNorm / RoPE   S rows of source_rows x source_trailing elements, and
    //:                    both engines report result_count == work_count ==
    //:                    cfg_count, which is this same product.
    //:   MATMUL           S output rows of source_rows columns; the work is one
    //:                    multiply-accumulate per output element per reduction
    //:                    step, so the depth multiplies in as well.
    //:   GATHER / EMBED   S gathered rows of source_trailing words (the mover's
    //:                    moved_elements), and S validated indices (its
    //:                    indices_checked) -- which is why the work leg is the
    //:                    span itself and not one.
    //:   TRANSFER         span-1 by construction, so ``request_span`` is one
    //:                    here and the staged fan-out counts are unchanged.
    wire [31:0] expected_result_count = mapped_family_q
        ? mapped_result_words
        : rms_norm_q ? (request_span * source_rows * source_trailing)
        : rope_q ? (request_span * source_rows * source_trailing)
        : matmul_q ? (request_span * source_rows)
        : dma_transfer_q ? (TRANSFER_COPIES * EMBEDDING_WIDTH)
        : (request_span * source_trailing);
    wire [31:0] expected_work_count = mapped_family_q
        ? mapped_work_words
        : rms_norm_q ? (request_span * source_rows * source_trailing)
        : rope_q ? (request_span * source_rows * source_trailing)
        : matmul_q ? (request_span * source_rows * source_trailing)
        : dma_transfer_q ? TRANSFER_COPIES : request_span;

    // The index read the bridge itself performs before a scatter or an
    // attention: the position is architecture, not configuration.
    wire bridge_index_read = (state == S_MAP_INDEX_ISSUE) ||
                             (state == S_EMBED_INDEX_ISSUE);
    wire [31:0] bridge_index_addr = (state == S_EMBED_INDEX_ISSUE)
        ? embed_index_addr_q : mapped_index_slot_base;

    assign m0_rd_en = bridge_index_read ? 1'b1
        : rope_q ? rope_input_rd_en
        : rms_norm_q ? rms_input_rd_en
        : vector_silu_mul_q ? silu_a_rd_en
        : selection_token_append_q ? append_a_rd_en
        : route_weight_normalize_q ? norm_wgt_rd_en
        : route_window_index_q ? widx_pos_rd_en
        : route_biased_topk_q ? btk_score_rd_en
        : reduction_expert_sum_q ? esum_m0_rd_en
        : attention_gqa_q ? gqa_mem_req_valid : array_m0_rd_en;
    assign m0_rd_addr = bridge_index_read ? bridge_index_addr
        : rope_q ? rope_input_rd_addr
        : rms_norm_q ? rms_input_rd_addr
        : vector_silu_mul_q ? silu_a_rd_addr
        : selection_token_append_q ? append_a_rd_addr
        : route_weight_normalize_q ? norm_wgt_rd_addr
        : route_window_index_q ? widx_pos_rd_addr
        : route_biased_topk_q ? btk_score_rd_addr
        : reduction_expert_sum_q ? esum_m0_rd_addr
        : attention_gqa_q ? gqa_mem_req_addr : array_m0_rd_addr;
    assign m1_rd_en = rope_q ? rope_coefficient_rd_en
        : rms_norm_q ? rms_weight_rd_en
        : vector_silu_mul_q ? silu_b_rd_en
        : route_biased_topk_q ? btk_bias_rd_en
        : reduction_expert_sum_q ? esum_val_rd_en[1]
        : (selection_token_append_q || attention_gqa_q ||
           route_weight_normalize_q || route_window_index_q) ? 1'b0
        : array_m1_rd_en;
    assign m1_rd_addr = rope_q ? rope_coefficient_rd_addr
        : rms_norm_q ? rms_weight_rd_addr
        : vector_silu_mul_q ? silu_b_rd_addr
        : route_biased_topk_q ? btk_bias_rd_addr
        : reduction_expert_sum_q ? esum_val_rd_addr[63:32]
        : (selection_token_append_q || attention_gqa_q ||
           route_weight_normalize_q || route_window_index_q) ? 32'd0
        : array_m1_rd_addr;
    //: m2 and m3 exist for EXPERT_SUM's third and fourth expert rows. Every
    //: other mapped family still leaves them idle, which is what they did
    //: before -- the condition is narrowed, not inverted.
    assign m2_rd_en = reduction_expert_sum_q ? esum_val_rd_en[2]
        : (rms_norm_q || rope_q || mapped_family_q) ? 1'b0 : array_m2_rd_en;
    assign m2_rd_addr = reduction_expert_sum_q ? esum_val_rd_addr[95:64]
        : (rms_norm_q || rope_q || mapped_family_q) ? 32'd0 : array_m2_rd_addr;
    assign m3_rd_en = reduction_expert_sum_q ? esum_val_rd_en[3]
        : (rms_norm_q || rope_q || mapped_family_q) ? 1'b0 : array_m3_rd_en;
    assign m3_rd_addr = reduction_expert_sum_q ? esum_val_rd_addr[127:96]
        : (rms_norm_q || rope_q || mapped_family_q) ? 32'd0 : array_m3_rd_addr;
    assign out_we = rope_q ? rope_out_we
        : rms_norm_q ? rms_out_we
        : vector_silu_mul_q ? silu_out_we
        : selection_token_append_q ? append_out_we
        : route_weight_normalize_q ? norm_out_we
        : route_window_index_q ? widx_out_we
        : route_biased_topk_q ? btk_out_we
        : reduction_expert_sum_q ? esum_out_we
        : attention_gqa_q ? gqa_out_valid : array_out_we;
    assign out_addr = rope_q ? rope_out_addr
        : rms_norm_q ? rms_out_addr
        : vector_silu_mul_q ? silu_out_addr
        : selection_token_append_q ? append_out_addr
        : route_weight_normalize_q ? norm_out_addr
        : route_window_index_q ? widx_out_addr
        : route_biased_topk_q ? btk_out_addr
        : reduction_expert_sum_q ? esum_out_addr
        : attention_gqa_q ? gqa_out_addr : array_out_addr;
    assign out_data = rope_q ? rope_out_data
        : rms_norm_q ? rms_out_data
        : vector_silu_mul_q ? silu_out_data
        : selection_token_append_q ? append_out_data
        : route_weight_normalize_q ? norm_out_data
        : route_window_index_q ? widx_out_data
        : route_biased_topk_q ? btk_out_data
        : reduction_expert_sum_q ? esum_out_data
        : attention_gqa_q ? gqa_out_data : array_out_data;
    // The bridge's own index read and the scatter's index read address the
    // index bank; every other mapped operand and result is a plane of the
    // result bank the earlier operators produced.
    assign m0_reads_result = bridge_index_read ? 1'b0
        : (rms_norm_q || rope_q || matmul_q || vector_add_q ||
           vector_silu_mul_q || selection_argmax_q ||
           selection_token_append_q || attention_gqa_q ||
           route_weight_normalize_q || route_window_index_q ||
           route_biased_topk_q || reduction_expert_sum_q);
    wire dma_gather_q = (issue_family_q == FAMILY_DMA) &&
                        (issue_sub_q == DMA_GATHER);
    assign m1_reads_result = rope_q || dma_transfer_q || vector_add_q ||
        vector_silu_mul_q || dma_scatter_q || route_biased_topk_q ||
        reduction_expert_sum_q ||
        ((GATHER_PLACEMENT_ADDRESSED != 0) && dma_gather_q);
    assign m1_reads_matmul_weight = matmul_q;

    //: WHERE A GATHER OR AN EMBED LOOKUP READS ITS INDICES.
    //:
    //: ``cfg_index_base + real_launch_count`` is a LAUNCH COUNTER.  It names
    //: exactly one index word per launch, so a span of S has nowhere to read S
    //: indices from -- and at S=1 the word it reads is whatever the host staged
    //: for that launch ordinal rather than the one the operator's own index view
    //: resolves to.  ``embed_index_addr_q`` is that view's address, formed in
    //: S_INDEX_WAIT for BOTH families as the index object's placement base plus
    //: the element offset slot 0 resolves to, and the mover reads S consecutive
    //: words from there.
    //:
    //: At INDEX_VIEW_ADDRESSED == 0 -- the default, and what every retained
    //: vector set was recorded against -- this is the launch counter unchanged.
    wire index_view_addressed_q = (INDEX_VIEW_ADDRESSED != 0) &&
                                  (embedding_q || dma_gather_q);
    wire [31:0] launch_index_base = dma_transfer_q
        ? cfg_transfer_index_base
        : index_view_addressed_q
            ? embed_index_addr_q
            : (cfg_index_base + real_launch_count);
    //: WHAT AN EMBED LOOKUP'S TABLE BASE IS.
    //:
    //: With the index applied by the bridge (EMBEDDING_TOKEN_INDEXED), the table
    //: base carries ``token * EMBEDDING_WIDTH`` already and the mover's own row
    //: index must be zero for the address to come out right -- which is a second
    //: place the token is used and a launch that can only embed ONE token.  With
    //: the index applied by the mover instead, the base is the table's own and
    //: the mover's S row indices select S rows of it.  The two are not composed:
    //: pre-multiplying and then adding a row would address the wrong row, so the
    //: index-view path takes the table base unmodified.
    wire [31:0] launch_source_base = dma_transfer_q
        ? cfg_transfer_source_base
        : embedding_q
            ? ((INDEX_VIEW_ADDRESSED != 0)
                ? embed_table_base_q
                : (EMBEDDING_TOKEN_INDEXED != 0)
                ? (embed_table_base_q + embed_token_q * EMBEDDING_WIDTH)
                : (cfg_embedding_source_base +
                   embedding_launch_count * EMBEDDING_WIDTH))
            : ((GATHER_PLACEMENT_ADDRESSED != 0)
                ? gather_source_base_q
                : (cfg_source_base +
                   dma_gather_launch_count * cfg_source_launch_stride));
    wire [31:0] launch_output_base = launch_output_base_q;

    //: THE RMSNorm PROFILE, scaled by the span bound.  A span-S launch of an
    //: R-row profile presents S*R rows in one launch -- 16 positions x 8 heads
    //: for a head norm, where the shipped ceiling was 32 -- and S*C elements.
    //: Both ceilings are therefore the declared profile times the bound, which
    //: is a DERIVATION and not a second hand-kept constant: raise
    //: MAX_SEQUENCE_SPAN and neither has to be revisited.  The engine derives
    //: every index width from these, so a raised ceiling refuses rather than
    //: hangs.  At MAX_SEQUENCE_SPAN == 1 both products are the declared profile
    //: and the engine's defaults are what the shipped elaboration forwarded.
    ot_a3_vector_rms_norm #(
        .PROFILE_MAX_COUNT(RMS_PROFILE_MAX_COUNT * SPAN_BOUND),
        .PROFILE_MAX_ROWS(RMS_PROFILE_MAX_ROWS * SPAN_BOUND),
        .PROFILE_MODEL_WIDTH(RMS_PROFILE_MODEL_WIDTH),
        .PROFILE_HEAD_WIDTH(RMS_PROFILE_HEAD_WIDTH)
    ) rms_norm (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & rms_norm_q),
        .cfg_count(expected_result_count),
        //: ROWS PER LAUNCH, NOT ROWS PER POSITION.  ``source_rows`` is the
        //: declared row count of one position -- 1 for a body norm, the head
        //: count for a head norm -- and the engine refuses unless
        //: ``cfg_rows * cfg_cols == cfg_count``.  Scaling the count without the
        //: rows is exactly the ERR_SHAPE a correct 16-position launch came back
        //: with: 2,048 elements offered as 1 x 128.  The rows a span-S launch
        //: presents are S * source_rows, contiguously, because a position's rows
        //: are adjacent and the positions are adjacent -- which is what
        //: ``stride0 == dim1 * HEAD_WIDTH`` on the input view already states.
        .cfg_rows(request_span * source_rows),
        .cfg_cols(source_trailing),
        .cfg_epsilon_bits(RMS_EPSILON),
        .cfg_input_base(rms_input_base_q),
        .cfg_weight_base(rms_weight_base_q),
        .cfg_output_base(launch_output_base),
        .input_rd_en(rms_input_rd_en),
        .input_rd_addr(rms_input_rd_addr),
        .input_rd_data(m0_rd_data),
        .weight_rd_en(rms_weight_rd_en),
        .weight_rd_addr(rms_weight_rd_addr),
        .weight_rd_data(m1_rd_data),
        .out_we(rms_out_we),
        .out_addr(rms_out_addr),
        .out_data(rms_out_data),
        .busy(rms_busy),
        .done(rms_done),
        .error_code(rms_error_code),
        .result_count(rms_result_count),
        .saturation_count(rms_saturation_count),
        .work_count(rms_work_count)
    );

    ot_a3_vector_rope #(
        //: RoPE rotates the same heads attention then reads, so its geometry
        //: is the bridge's attention geometry and not a second opinion.
        .QUERY_HEADS(GQA_QUERY_HEADS[31:0]),
        .KEY_HEADS(GQA_KV_HEADS[31:0]),
        .HEAD_WIDTH(GQA_HEAD_WIDTH[31:0])
    ) rope (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & rope_q),
        //: cfg_count CARRIES THE SPAN and cfg_rows deliberately does not.  This
        //: engine recovers S by subtracting one position block of
        //: ``cfg_rows * cfg_cols`` from the count until nothing is left -- it
        //: reloads the coefficient row per position, so it has to know where a
        //: position ends.  Scaling cfg_rows here as the RMSNorm above does would
        //: present S positions as one, and the span would come out as 1.
        .cfg_count(expected_result_count),
        .cfg_rows(source_rows),
        .cfg_cols(source_trailing),
        .cfg_input_base(rope_input_base_q),
        .cfg_coefficient_base(rope_coefficient_base_q),
        .cfg_output_base(launch_output_base),
        .input_rd_en(rope_input_rd_en),
        .input_rd_addr(rope_input_rd_addr),
        .input_rd_data(m0_rd_data),
        .coefficient_rd_en(rope_coefficient_rd_en),
        .coefficient_rd_addr(rope_coefficient_rd_addr),
        .coefficient_rd_data(m1_rd_data),
        .out_we(rope_out_we),
        .out_addr(rope_out_addr),
        .out_data(rope_out_data),
        .busy(rope_busy),
        .done(rope_done),
        .error_code(rope_error_code),
        .result_count(rope_result_count),
        .saturation_count(rope_saturation_count),
        .work_count(rope_work_count)
    );

    ot_a3_vector_silu_mul silu_mul (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & vector_silu_mul_q),
        .cfg_count(mapped_element_count),
        .cfg_gate_base(mapped_left_base),
        .cfg_up_base(mapped_right_base),
        .cfg_out_base(mapped_output_base),
        .a_rd_en(silu_a_rd_en),
        .a_rd_addr(silu_a_rd_addr),
        .a_rd_data(m0_rd_data),
        .b_rd_en(silu_b_rd_en),
        .b_rd_addr(silu_b_rd_addr),
        .b_rd_data(m1_rd_data),
        .out_we(silu_out_we),
        .out_addr(silu_out_addr),
        .out_data(silu_out_data),
        .busy(silu_busy),
        .done(silu_done),
        .error_code(silu_error_code),
        .out_count(silu_result_count),
        .saturation_count(silu_saturation_count),
        .activation_saturation_count(silu_activation_saturation_count),
        .work_count(silu_work_count)
    );

    ot_a3_selection_token_append token_append (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & selection_token_append_q),
        .cfg_token_base(mapped_left_base),
        .cfg_ring_bound(policy_ring_bound),
        .cfg_out_base(mapped_output_base),
        .cfg_selection_mode(policy_selection_mode),
        .cfg_eos_count(policy_eos_count),
        .cfg_policy_max_new_tokens(policy_max_new_tokens),
        .cfg_vocabulary(policy_vocabulary),
        .cfg_eos_token_0(policy_eos_token[0]),
        .cfg_eos_token_1(policy_eos_token[1]),
        .cfg_eos_token_2(policy_eos_token[2]),
        .cfg_eos_token_3(policy_eos_token[3]),
        .cfg_eos_token_4(policy_eos_token[4]),
        .cfg_eos_token_5(policy_eos_token[5]),
        .cfg_eos_token_6(policy_eos_token[6]),
        .cfg_eos_token_7(policy_eos_token[7]),
        .cfg_request_max_new_tokens(cfg_request_max_new_tokens),
        .cfg_generated_before(cfg_generated_before),
        .a_rd_en(append_a_rd_en),
        .a_rd_addr(append_a_rd_addr),
        .a_rd_data(m0_rd_data),
        .out_we(append_out_we),
        .out_addr(append_out_addr),
        .out_data(append_out_data),
        .busy(append_busy),
        .done(append_done),
        .error_code(append_error_code),
        .refusal_capability(append_refusal_capability),
        .token(append_token),
        .eos_reason(append_eos_reason),
        .appended_count(append_work_count),
        .out_count(append_result_count)
    );

    ot_a3_qwen_gqa #(
        .QUERY_HEADS(GQA_QUERY_HEADS),
        .KV_HEADS(GQA_KV_HEADS),
        .HEAD_WIDTH(GQA_HEAD_WIDTH),
        .SCALE_CODE(GQA_SCALE_CODE),
        //: THE QUERY-SPAN BOUND IS THE BRIDGE'S SPAN BOUND.  This engine is the
        //: one all-or-nothing block on the path: it buffers the whole result
        //: before publishing a word, so MAX_QUERY_SPAN * QUERY_HEADS *
        //: HEAD_WIDTH BF16 words of buffer is what raising the bound costs, and
        //: forwarding rather than restating it is what keeps the two from
        //: drifting.  At MAX_SEQUENCE_SPAN == 1 this is the engine's own default
        //: and the netlist is the pre-span one.
        .MAX_QUERY_SPAN(MAX_SEQUENCE_SPAN)
    ) gqa (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & attention_gqa_q),
        .cfg_context_length(mapped_context),
        //: THE QUERY ROWS AND WHERE THEY SIT.  These were tied to one row
        //: ending at the context, which is a decode and only a decode.  The
        //: span is the resolved extent of the query view; the first position is
        //: the context minus it, because a causal span is a TAIL of its KV plane
        //: -- the same identity ``mapped_context_ok`` checked the resolved index
        //: value against, so the position the index view names and the position
        //: handed to the engine are one statement, not two.
        //:
        //: The subtraction cannot underflow: ``mapped_context_ok`` refused the
        //: launch unless ``cfg_context_length >= request_span``, and the engine
        //: independently refuses a span wider than its context
        //: (``span_within_context``) rather than trusting this arithmetic.
        .cfg_query_span(request_span),
        .cfg_first_position(mapped_context - request_span),
        .cfg_query_base(mapped_left_base),
        .cfg_key_base(mapped_right_base),
        .cfg_value_base(mapped_third_base),
        .cfg_output_base(mapped_output_base),
        .mem_req_valid(gqa_mem_req_valid),
        .mem_req_ready(1'b1),
        .mem_req_addr(gqa_mem_req_addr),
        .mem_rsp_valid(gqa_mem_rsp_valid),
        .mem_rsp_data(m0_rd_data),
        .out_valid(gqa_out_valid),
        .out_ready(1'b1),
        .out_addr(gqa_out_addr),
        .out_data(gqa_out_data),
        .busy(gqa_busy),
        .done(gqa_done),
        .failed(gqa_failed),
        .error_code(gqa_error_code),
        .memory_read_count(gqa_memory_read_count),
        .output_write_count(gqa_result_count),
        .score_multiply_count(gqa_work_count),
        .exponential_count(gqa_exponential_count),
        .value_multiply_count(gqa_value_multiply_count),
        .saturation_count(gqa_saturation_count)
    );

    //: ROUTE.WEIGHT_NORMALIZE. The group count is ``request_span`` because slot
    //: 0 IS the sequence axis here -- one routed group per token position -- so
    //: this engine inherits the same span admission every other family gets
    //: rather than needing a bound of its own.
    ot_a3_route_weight_normalize #(
        .MAX_SLOTS(WEIGHT_NORMALIZE_MAX_SLOTS),
        .DIVIDERS(WEIGHT_NORMALIZE_DIVIDERS),
        //: Zero, and the contract digest above is what makes that sound: every
        //: shipped profile carries scale_bits 0, so the reference's trailing
        //: multiply is the identity. A scaled profile never reaches here.
        .ENABLE_SCALE(0)
    ) weight_normalize (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & route_weight_normalize_q),
        .cfg_groups(request_span),
        .cfg_slots(weight_normalize_slots),
        //: SEQUENTIAL_ASCENDING, pinned by CONTRACT_WEIGHT_NORMALIZE_RAW rather
        //: than read from the profile: the reduction_order field is not one this
        //: bridge decodes, and the digest covers the whole contract including
        //: the association. The engine refuses any other value, so a contract
        //: that ever changed order would fail closed here instead of quietly
        //: re-associating.
        .cfg_reduction_order(8'd0),
        .cfg_has_scale(1'b0),
        .cfg_scale_code(32'h3f80_0000),
        .cfg_in_base(mapped_left_base),
        .cfg_out_base(mapped_output_base),
        //: FP32 out, which weight_normalize_shape_ok and the numeric contract
        //: both already require, so the narrowing path is never taken.
        .cfg_out_fp32(1'b1),
        .wgt_rd_en(norm_wgt_rd_en),
        .wgt_rd_addr(norm_wgt_rd_addr),
        .wgt_rd_data(m0_rd_data),
        .out_we(norm_out_we),
        .out_addr(norm_out_addr),
        .out_data(norm_out_data),
        .busy(norm_busy),
        .done(norm_done),
        .error_code(norm_error_code),
        .out_count(norm_result_count),
        .saturation_count(norm_saturation_count)
    );

    //: ROUTE.WINDOW_INDEX. The context comes from the device's own
    //: cfg_context_length rather than by resolving aux_id_2's symbol: this
    //: bridge has no symbol file, the shape check already refuses full
    //: visibility unless aux_id_2 is bound, and CONTRACT_WINDOW_INDEX_RAW pins
    //: the operator whose context that symbol names. A bridge that grows symbol
    //: access should read it there instead and drop this note.
    //: REDUCTION.EXPERT_SUM. EXPERTS is the bridge's operand-port budget, and
    //: expert_sum_shape_ok refuses any operator that declares more.
    ot_a3_reduction_expert_sum #(
        .EXPERTS(EXPERT_SUM_MAX_EXPERTS)
    ) expert_sum (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & reduction_expert_sum_q),
        .cfg_experts(expert_sum_experts[7:0]),
        .cfg_count(expert_sum_width),
        .cfg_in_base(mapped_left_base),
        //: Elements between one expert's row and the next, which slot 0's
        //: stride0 states and the shape check ties to the width.
        .cfg_stride(expert_sum_width),
        //: input_view_1 is bound in every shipped operator and the arity leg
        //: requires it, so the routing weights are always present.
        .cfg_has_weights(1'b1),
        .cfg_weight_base(slot1_base),
        //: input_view_2 is unbound in every shipped operator, so there is no
        //: base leaf and no base row read -- which is also what frees m1..m3 to
        //: carry experts 1 through 3.
        .cfg_has_base(1'b0),
        .cfg_base_base(32'd0),
        .cfg_base_after_terms(1'b0),
        .cfg_out_base(mapped_output_base),
        .val_rd_en(esum_val_rd_en),
        .val_rd_addr(esum_val_rd_addr),
        .val_rd_data({m3_rd_data, m2_rd_data, m1_rd_data, m0_rd_data}),
        .wgt_rd_en(esum_wgt_rd_en),
        .wgt_rd_addr(esum_wgt_rd_addr),
        .wgt_rd_data(m0_rd_data),
        .base_rd_en(esum_base_rd_en),
        .base_rd_addr(esum_base_rd_addr),
        .base_rd_data(32'd0),
        .out_we(esum_out_we),
        .out_addr(esum_out_addr),
        .out_data(esum_out_data),
        .busy(esum_busy),
        .done(esum_done),
        .error_code(esum_error_code),
        .out_count(esum_out_count),
        .saturation_count(esum_saturation_count)
    );

    //: ROUTE.BIASED_TOPK.
    ot_a3_route_biased_topk #(
        .MAX_K(BIASED_TOPK_MAX_K)
    ) biased_topk (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & route_biased_topk_q),
        .cfg_groups(request_span),
        .cfg_experts(biased_topk_experts),
        .cfg_topk(biased_topk_slots),
        //: input_view_1 is bound in every shipped operator and the arity leg
        //: requires it, so the bias is always present here.
        .cfg_has_bias(1'b1),
        //: Rank 1 [experts], which biased_topk_shape_ok requires, so it
        //: broadcasts over every group.
        .cfg_bias_broadcast(1'b1),
        //: FP32 operands, which the numeric contract and slot 0 both require.
        .cfg_operand_fp32(1'b1),
        .cfg_score_base(mapped_left_base),
        .cfg_bias_base(slot1_base),
        .cfg_id_out_base(mapped_output_base),
        .cfg_has_weight_out(1'b1),
        //: Slot 5 is FP32, so the weight is stored as the binary32 code.
        .cfg_weight_fp32(1'b1),
        .cfg_weight_out_base(slot5_base),
        .score_rd_en(btk_score_rd_en),
        .score_rd_addr(btk_score_rd_addr),
        .score_rd_data(m0_rd_data),
        .bias_rd_en(btk_bias_rd_en),
        .bias_rd_addr(btk_bias_rd_addr),
        .bias_rd_data(m1_rd_data),
        .id_we(btk_id_we),
        .id_addr(btk_id_addr),
        .id_data(btk_id_data),
        .wgt_we(btk_wgt_we),
        .wgt_addr(btk_wgt_addr),
        .wgt_data(btk_wgt_data),
        .busy(btk_busy),
        .done(btk_done),
        .error_code(btk_error_code),
        .selected_experts(btk_selected),
        .candidates(btk_candidates)
    );

    ot_a3_route_window_index window_index (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & route_window_index_q),
        .cfg_span(request_span),
        .cfg_slots(window_index_slots),
        .cfg_window(window_index_window),
        .cfg_mask_full(window_index_mask_full),
        .cfg_context(cfg_context_length),
        //: Prefill: the output is absolute KV rows. A decode step's circular
        //: window is a different addressing mode and no shipped operator
        //: declares it, so it is not offered here rather than guessed.
        .cfg_decode(1'b0),
        .cfg_pos_base(mapped_left_base),
        .cfg_out_base(mapped_output_base),
        .pos_rd_en(widx_pos_rd_en),
        .pos_rd_addr(widx_pos_rd_addr),
        .pos_rd_data(m0_rd_data),
        .out_we(widx_out_we),
        .out_addr(widx_out_addr),
        .out_data(widx_out_data),
        .busy(widx_busy),
        .done(widx_done),
        .error_code(widx_error_code),
        .out_count(widx_out_count),
        .candidates(widx_candidates)
    );

    ot_a3_engine_array engines (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & !rms_norm_q & !rope_q &
               !vector_silu_mul_q & !attention_gqa_q &
               !selection_token_append_q & !route_weight_normalize_q &
               !route_window_index_q & !route_biased_topk_q &
               !reduction_expert_sum_q),
        .cfg_family(matmul_q ? FAMILY_TENSOR
                  : vector_add_q ? FAMILY_VECTOR
                  : selection_argmax_q ? FAMILY_SELECTION
                  : FAMILY_DMA),
        .cfg_sub(matmul_q ? TENSOR_MATMUL
               : vector_add_q ? VECTOR_ADD
               : selection_argmax_q ? SELECTION_ARGMAX
               : dma_scatter_q ? DMA_SCATTER
               : DMA_GATHER),
        //: M, THE MATMUL'S OUTPUT ROW COUNT.  This was the literal one, which
        //: is the only place a 16-row prefill projection differed from a decode
        //: projection in the datapath: both mac lanes already walk M rows and
        //: were measured identical at M=16.  ``request_span`` is bounded by
        //: SPAN_BOUND at admission, and SPAN_BOUND is itself bounded by the
        //: 16-bit field this port is, so the slice cannot truncate a span the
        //: bridge admitted.
        .cfg_rows(matmul_q ? request_span[15:0] : 16'd0),
        .cfg_cols(matmul_q ? source_rows[15:0] : source_trailing[15:0]),
        .cfg_depth(matmul_q ? source_trailing[15:0] : 16'd0),
        .cfg_count(mapped_family_q
                   ? mapped_element_count : expected_result_count),
        .cfg_dtype_a((matmul_q || vector_add_q) ? FMT_BF16
                   : selection_argmax_q ? mapped_dtype_a
                   : FMT_U32),
        .cfg_dtype_b(mapped_family_q ? FMT_BF16 : source_dtype),
        .cfg_a_base(matmul_q ? rms_input_base_q
                  : mapped_family_q ? mapped_left_base
                  : launch_index_base),
        .cfg_b_base(matmul_q ? matmul_weight_base_q
                  : mapped_family_q ? mapped_right_base
                  : launch_source_base),
        .cfg_c_base(dma_scatter_q ? mapped_prior_base : 32'd0),
        .cfg_out_base(mapped_family_q
                      ? mapped_output_base : launch_output_base),
        .cfg_scale_a(1'b0),
        .cfg_scale_b(1'b0),
        .cfg_block_a(16'd0),
        .cfg_block_b(16'd0),
        .cfg_block_rows_a(16'd0),
        .cfg_block_rows_b(16'd0),
        .cfg_scale_a_base(32'd0),
        .cfg_scale_b_base(32'd0),
        //: THE INDEX-MOVER'S ROW COUNT, which is what ot_a3_dma_index_mover
        //: calls cfg_slots and its port comment calls "index count": one index
        //: word, and one moved row, per slot.  The literal one is what made a
        //: gather, an embed lookup and a scatter single-row operations; the row
        //: count of a span-S launch is S, and the mover is already a row walker
        //: that validates every index before it moves anything.  TRANSFER keeps
        //: its staged fan-out, and every family that does not reach the mover
        //: leaves cfg_slots unread.
        .cfg_slots(dma_transfer_q ? TRANSFER_COPIES : request_span),
        .cfg_trailing(dma_scatter_q ? KV_PLANE_WORDS : source_trailing),
        .cfg_extent(dma_scatter_q ? cfg_kv_plane_rows
                  : dma_transfer_q ? 32'd1 : source_rows),
        .cfg_input_valid(selection_argmax_q ? 4'b0001 : 4'b0011),
        .cfg_output_valid(2'b01),
        .cfg_input_dtypes({16'd0, source_dtype,
            matmul_q ? FMT_BF16 : FMT_U32}),
        .cfg_output_dtypes({8'd0, source_dtype}),
        .cfg_view_ranks(matmul_q ? 24'h02_00_22 : 24'h02_00_21),
        .cfg_view_scaled(6'd0),
        .cfg_profile_valid(1'b1),
        .cfg_profile_dtypes(numeric_profile_dtypes),
        .cfg_rounding_mode(8'd0),
        .cfg_reduction_order(matmul_q ? 8'd2 : 8'd0),
        .cfg_profile_saturate(1'b0),
        .cfg_nan_policy(8'd0),
        .cfg_profile_scale_bits(32'd0),
        .cfg_epsilon_bits(32'd0),
        .cfg_profile_flags(32'd0),
        //: THE DECLARED SHAPES THAT ACCOMPANY THE CONFIGURATION.  The leading
        //: term of each was the literal one -- the same frozen single row, said
        //: a third time -- so a span-S launch described itself as a one-row
        //: launch to the engine it was configuring.  It is the span here too.
        //: (``descriptor_admitted`` is the constant true for MATMUL, DMA, ADD
        //: and ARGMAX, so these shapes gate nothing today; that is exactly why
        //: leaving them at one would have been a latent trap for the first
        //: family that started reading them.)
        .cfg_input0_dims(matmul_q
            ? {64'd0, source_trailing, request_span}
            : {96'd0, dma_transfer_q ? TRANSFER_COPIES : request_span}),
        .cfg_input1_dims({64'd0, source_trailing,
            dma_transfer_q ? 32'd1 : source_rows}),
        .cfg_input2_dims(128'd0),
        .cfg_input3_dims(128'd0),
        .cfg_output0_dims(matmul_q
            ? {64'd0, source_rows, request_span}
            : {64'd0, source_trailing,
               dma_transfer_q ? TRANSFER_COPIES : request_span}),
        .cfg_output1_dims(128'd0),
        .cfg_contract_0(matmul_q ? 32'h7550dc6a : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'hd1ea2f18 : 32'hca62e720)
            : 32'h12a24197),
        .cfg_contract_1(matmul_q ? 32'h773fd9d5 : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'he0b161e1 : 32'haa0132c2)
            : 32'hc80d3851),
        .cfg_contract_2(matmul_q ? 32'h773b4618 : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'h9e17f465 : 32'h1f095a7f)
            : 32'hcc5ea3e6),
        .cfg_contract_3(matmul_q ? 32'h2887613f : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'hced630e0 : 32'h1f8d5d94)
            : 32'h9915f7db),
        .cfg_contract_4(matmul_q ? 32'hb777bb8e : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'haf7d0de9 : 32'h07149b85)
            : 32'hc926aa1c),
        .cfg_contract_5(matmul_q ? 32'h4f016523 : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'h70dadd67 : 32'h47ddeb0a)
            : 32'h2ee795c8),
        .cfg_contract_6(matmul_q ? 32'h21c4d93c : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'h76c685ab : 32'hbd5d882a)
            : 32'hfe3af1a6),
        .cfg_contract_7(matmul_q ? 32'ha0765aa1 : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'h6539fbcc : 32'h2f0180d3)
            : 32'h7677daee),
        .cfg_aux_valid(4'd0),
        .cfg_aux0(NO_ID),
        .cfg_aux1(NO_ID),
        .cfg_aux2(NO_ID),
        .cfg_aux3(NO_ID),
        .m0_rd_en(array_m0_rd_en),
        .m0_rd_addr(array_m0_rd_addr),
        .m0_rd_data(m0_rd_data),
        .m1_rd_en(array_m1_rd_en),
        .m1_rd_addr(array_m1_rd_addr),
        .m1_rd_data(m1_rd_data),
        .m2_rd_en(array_m2_rd_en),
        .m2_rd_addr(array_m2_rd_addr),
        .m2_rd_data(m2_rd_data),
        .m3_rd_en(array_m3_rd_en),
        .m3_rd_addr(array_m3_rd_addr),
        .m3_rd_data(m3_rd_data),
        .out_we(array_out_we),
        .out_addr(array_out_addr),
        .out_data(array_out_data),
        .busy(array_busy),
        .done(array_done),
        .error_code(array_error_code),
        .result_count(array_result_count),
        .saturation_count(array_saturation_count),
        .work_count(array_work_count),
        .token(array_token),
        .tie_multiplicity(array_tie_multiplicity)
    );

    // A refused GENERATION_POLICY is a capability refusal, not a shape one.
    wire mapped_capability_refusal =
        selection_token_append_q && append_refusal_capability;

    wire _unused_rope_saturation = &{1'b0, rope_saturation_count,
        silu_saturation_count, silu_activation_saturation_count,
        gqa_memory_read_count, gqa_exponential_count,
        gqa_value_multiply_count, gqa_saturation_count, gqa_failed,
        norm_saturation_count, esum_saturation_count,
        esum_base_rd_en, esum_base_rd_addr,
        slot_view_id[0], slot_terms[1], mapped_vocabulary};
endmodule
