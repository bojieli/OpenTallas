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
    parameter [31:0]  GQA_SCALE_CODE  = 32'h3db5_0000
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
    input  wire          desc_valid,
    input  wire          desc_fault,
    input  wire [1535:0] desc_data,

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
    localparam [7:0] FAMILY_SELECTION = 8'h70;
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
    // bf16_byte_preserving_state_v1
    localparam [255:0] CONTRACT_KV_SCATTER_RAW =
        256'h6fe100be19c00c87797983af8409335999bfd793cdcf3862af5ba6bdcc9bf355;
    // qwen3_gqa_fp32_softmax_bf16_v1
    localparam [255:0] CONTRACT_QWEN_GQA_RAW =
        256'h81e12c87d89ead473983a0898c3fbfe08d7b0a3864b55fb1f0171a4698f53a62;
    localparam [31:0] QWEN_VOCABULARY = 32'd151936;
    localparam [31:0] DEEPSEEK_VOCABULARY = 32'd129280;
    localparam [31:0] EMBEDDING_WIDTH = 32'd4096;
    localparam [31:0] HEAD_WIDTH = 32'd128;
    localparam [31:0] MAX_HEAD_ROWS = 32'd32;
    localparam [31:0] RMS_EPSILON = 32'h3586_37bd;
    localparam [31:0] TRANSFER_COPIES = 32'd4;
    localparam [31:0] QUERY_HEADS = 32'd32;
    localparam [31:0] KV_HEADS = 32'd8;
    localparam [31:0] KV_PLANE_WORDS = KV_HEADS * HEAD_WIDTH;
    localparam [31:0] KV_ROW_STRIDE = 32'd2 * KV_PLANE_WORDS;
    localparam [31:0] GQA_SCALE_BITS = 32'h3db5_0000;
    localparam [31:0] GQA_OUTPUT_WORDS = QUERY_HEADS * HEAD_WIDTH;

    localparam [3:0] S_IDLE        = 4'd0;
    localparam [3:0] S_OP_WAIT     = 4'd1;
    localparam [3:0] S_INDEX_WAIT  = 4'd2;
    localparam [3:0] S_SOURCE_WAIT = 4'd3;
    localparam [3:0] S_OUTPUT_WAIT = 4'd4;
    localparam [3:0] S_NUM_WAIT    = 4'd5;
    localparam [3:0] S_START       = 4'd6;
    localparam [3:0] S_ENGINE_WAIT = 4'd7;
    localparam [3:0] S_RESPONSE    = 4'd8;
    localparam [3:0] S_RMS_INPUT_WAIT = 4'd9;
    // The mapped families walk one shared admission path instead of one
    // state chain each.
    localparam [3:0] S_MAP_VIEW_WAIT   = 4'd10;
    localparam [3:0] S_MAP_NUM_WAIT    = 4'd11;
    localparam [3:0] S_MAP_POLICY_WAIT = 4'd12;
    localparam [3:0] S_MAP_INDEX_ISSUE = 4'd13;
    localparam [3:0] S_MAP_INDEX_WAIT  = 4'd14;
    localparam [3:0] S_MAP_ADMIT       = 4'd15;

    // -- the object placement table ---------------------------------------
    // One table, consulted by every operand slot and every result slot of
    // every family.  The ports are scalar so the surface can be counted from
    // the module's own declaration; they are gathered here once.
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

    // {found, base}.  Descending order leaves entry 0 as the final
    // assignment, but a table that names an object twice never reaches this
    // function: admission refuses such a table first, so "entry 0 wins" is a
    // tie-break that cannot be exercised rather than a policy for resolving a
    // contradiction.
    function automatic [32:0] place_lookup;
        input [31:0] object_id;
        integer scan;
        begin
            place_lookup = 33'd0;
            for (scan = PLACE_SLOTS - 1; scan >= 0; scan = scan - 1)
                if ((object_id != NO_ID) &&
                    (object_id == place_object[scan]))
                    place_lookup = {1'b1, place_base[scan]};
        end
    endfunction

    // An object bound twice is a configuration that cannot be honoured: two
    // entries disagree about where one object is, and every rule in this
    // module assumes an object has one place.  NO_ID is the empty entry and
    // may repeat.
    reg placement_unique_r;
    integer place_i;
    integer place_j;
    always @* begin
        placement_unique_r = 1'b1;
        for (place_i = 0; place_i < PLACE_SLOTS; place_i = place_i + 1)
            for (place_j = 0; place_j < PLACE_SLOTS; place_j = place_j + 1)
                if ((place_j > place_i) &&
                    (place_object[place_i] != NO_ID) &&
                    (place_object[place_i] == place_object[place_j]))
                    placement_unique_r = 1'b0;
    end
    wire placement_table_unique = placement_unique_r;

    reg [3:0] state;
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
    wire       mapped_family_q = vector_add_q | vector_silu_mul_q |
                                 dma_scatter_q | attention_gqa_q |
                                 selection_argmax_q | selection_token_append_q;

    // Per-slot capture of every bound TENSOR_VIEW record, filled by the shared
    // admission walk in slot order.  Flat arrays rather than a packed struct:
    // the pinned Yosys 0.68 frontend and Icarus 11 agree on these.
    reg [5:0]  slot_bound;
    reg [31:0] slot_view_id [0:5];
    reg [7:0]  slot_dtype [0:5];
    reg [7:0]  slot_rank [0:5];
    reg [7:0]  slot_terms [0:5];
    reg [31:0] slot_object [0:5];
    reg [31:0] slot_permissions [0:5];
    reg [31:0] slot_dim0 [0:5];
    reg [31:0] slot_dim1 [0:5];
    reg [31:0] slot_dim2 [0:5];
    reg [31:0] slot_stride0 [0:5];
    reg [31:0] slot_stride1 [0:5];
    reg [31:0] slot_stride2 [0:5];
    reg [31:0] slot_tail_dims [0:5];
    reg [31:0] slot_tail_strides [0:5];
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
    // fetched.  One rule for every role that used to have its own port.
    wire [32:0] desc_place = place_lookup(desc_primary_object);
    wire        desc_object_placed = desc_place[32];

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
        (captured_offset[1] == desc_view_offset) &&
        (!embedding_q || ((desc_view_dim1 == EMBEDDING_WIDTH) &&
         ((desc_view_dim0 == QWEN_VOCABULARY) ||
          (desc_view_dim0 == DEEPSEEK_VOCABULARY))));
    wire model_row_input_source_ok =
        (matmul_q || (rms_norm_q && !head_rms_norm_q)) &&
        (desc_view_dtype == FMT_BF16) && (desc_view_rank == 2) &&
        (desc_view_terms <= 4) &&
        (desc_view_dim0 != 0) && (desc_view_dim1 == EMBEDDING_WIDTH) &&
        (desc_view_dim2 == 0) && (desc_view_dim3 == 0) &&
        (desc_view_dim4 == 0) && (desc_view_dim5 == 0) &&
        (desc_view_stride0 == EMBEDDING_WIDTH) &&
        (desc_view_stride1 == 1) && (desc_view_stride2 == 0) &&
        (desc_view_stride3 == 0) && (desc_view_stride4 == 0) &&
        (desc_view_stride5 == 0) &&
        (captured_rank[0] == 2) && (captured_axis[0] == 0) &&
        (captured_extent[0] == 1) &&
        (captured_offset[0] == desc_view_offset);
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
        (captured_extent[0] == 1) &&
        (captured_offset[0] == desc_view_offset);
    wire rope_input_source_ok = rope_q &&
        (desc_view_dtype == FMT_BF16) && (desc_view_rank == 3) &&
        (desc_view_terms <= 4) &&
        (desc_view_dim0 != 0) &&
        ((desc_view_dim1 == 32'd32) || (desc_view_dim1 == 32'd8)) &&
        (desc_view_dim2 == HEAD_WIDTH) &&
        (desc_view_dim3 == 0) && (desc_view_dim4 == 0) &&
        (desc_view_dim5 == 0) &&
        (desc_view_stride0 == desc_view_dim1 * HEAD_WIDTH) &&
        (desc_view_stride1 == HEAD_WIDTH) &&
        (desc_view_stride2 == 1) && (desc_view_stride3 == 0) &&
        (desc_view_stride4 == 0) && (desc_view_stride5 == 0) &&
        (captured_rank[0] == 3) && (captured_axis[0] == 0) &&
        (captured_extent[0] == 1) &&
        (captured_offset[0] == desc_view_offset);
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
        (captured_offset[1] == desc_view_offset);
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
        (captured_offset[1] == desc_view_offset);
    wire matmul_weight_source_ok = matmul_q &&
        (desc_view_dtype == FMT_BF16) && (desc_view_rank == 2) &&
        (desc_view_terms <= 4) &&
        (desc_view_dim0 != 0) && (desc_view_dim0 <= EMBEDDING_WIDTH) &&
        (desc_view_dim1 == EMBEDDING_WIDTH) &&
        (desc_view_dim2 == 0) && (desc_view_dim3 == 0) &&
        (desc_view_dim4 == 0) && (desc_view_dim5 == 0) &&
        (desc_view_stride0 == EMBEDDING_WIDTH) &&
        (desc_view_stride1 == 1) && (desc_view_stride2 == 0) &&
        (desc_view_stride3 == 0) && (desc_view_stride4 == 0) &&
        (desc_view_stride5 == 0) &&
        (captured_rank[1] == 2) && (captured_axis[1] == 0) &&
        (captured_extent[1] == desc_view_dim0) &&
        (captured_offset[1] == desc_view_offset);
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
        (captured_extent[0] == 1) &&
        (captured_offset[0] == desc_view_offset);

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
        (captured_offset[4] == desc_view_offset);
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
        attention_gqa_q ? 6'b011111
      : (selection_argmax_q || selection_token_append_q) ? 6'b010001
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
        (captured_extent[0] == 32'd1) &&
        (captured_rank[1] == 8'd2) && (captured_axis[1] == 8'd0) &&
        (captured_extent[1] == 32'd1) &&
        (captured_rank[4] == 8'd2) && (captured_axis[4] == 8'd0) &&
        (captured_extent[4] == 32'd1);

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
        (captured_extent[4] == 32'd1);

    wire token_append_shape_ok =
        (slot_dtype[0] == FMT_U32) && (slot_rank[0] == 8'd1) &&
        (slot_dim0[0] == 32'd1) && (slot_dim1[0] == 32'd0) &&
        (slot_dim2[0] == 32'd0) && (slot_tail_dims[0] == 32'd0) &&
        (slot_stride0[0] == 32'd1) && (slot_stride1[0] == 32'd0) &&
        (slot_stride2[0] == 32'd0) && (slot_tail_strides[0] == 32'd0) &&
        (captured_rank[0] == 8'd1) && (captured_axis[0] == 8'd0) &&
        (captured_extent[0] == 32'd1) &&
        (slot_dtype[4] == FMT_U32) && (slot_rank[4] == 8'd1) &&
        (slot_dim0[4] == 32'd1) && (slot_dim1[4] == 32'd0) &&
        (slot_dim2[4] == 32'd0) && (slot_tail_dims[4] == 32'd0) &&
        (slot_stride0[4] == 32'd1) && (slot_stride1[4] == 32'd0) &&
        (slot_stride2[4] == 32'd0) && (slot_tail_strides[4] == 32'd0) &&
        (captured_rank[4] == 8'd1) && (captured_axis[4] == 8'd0) &&
        (captured_extent[4] == 32'd1);

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

    wire scatter_plane_is_value = (captured_offset[4] == {32'd0, KV_PLANE_WORDS});
    wire scatter_shape_ok =
        index_element_view_ok(
            slot_dtype[0], slot_rank[0], slot_dim0[0], slot_dim1[0],
            slot_dim2[0], slot_tail_dims[0], slot_stride0[0],
            slot_stride1[0], slot_stride2[0], slot_tail_strides[0]
        ) &&
        (captured_rank[0] == 8'd1) && (captured_axis[0] == 8'd0) &&
        (captured_extent[0] == 32'd1) &&
        head_row_view_ok(
            slot_dtype[1], slot_rank[1], KV_HEADS, slot_dim1[1],
            slot_dim2[1], slot_tail_dims[1], slot_stride0[1],
            slot_stride1[1], slot_stride2[1], slot_tail_strides[1]
        ) &&
        (captured_rank[1] == 8'd3) && (captured_axis[1] == 8'd0) &&
        (captured_extent[1] == 32'd1) && (captured_offset[1] == 64'd0) &&
        kv_cache_view_ok(
            slot_dtype[4], slot_rank[4], slot_dim1[4], slot_dim2[4],
            slot_tail_dims[4], slot_stride0[4], slot_stride1[4],
            slot_stride2[4], slot_tail_strides[4]
        ) &&
        (captured_rank[4] == 8'd3) && (captured_axis[4] == 8'd0) &&
        (captured_extent[4] == slot_dim0[4]) &&
        (slot_dim0[4] >= cfg_kv_plane_rows) &&
        ((captured_offset[4] == 64'd0) || scatter_plane_is_value);

    wire gqa_shape_ok =
        head_row_view_ok(
            slot_dtype[0], slot_rank[0], QUERY_HEADS, slot_dim1[0],
            slot_dim2[0], slot_tail_dims[0], slot_stride0[0],
            slot_stride1[0], slot_stride2[0], slot_tail_strides[0]
        ) &&
        (captured_rank[0] == 8'd3) && (captured_axis[0] == 8'd0) &&
        (captured_extent[0] == 32'd1) && (captured_offset[0] == 64'd0) &&
        kv_cache_view_ok(
            slot_dtype[1], slot_rank[1], slot_dim1[1], slot_dim2[1],
            slot_tail_dims[1], slot_stride0[1], slot_stride1[1],
            slot_stride2[1], slot_tail_strides[1]
        ) &&
        (captured_offset[1] == 64'd0) &&
        kv_cache_view_ok(
            slot_dtype[2], slot_rank[2], slot_dim1[2], slot_dim2[2],
            slot_tail_dims[2], slot_stride0[2], slot_stride1[2],
            slot_stride2[2], slot_tail_strides[2]
        ) &&
        (captured_offset[2] == {32'd0, KV_PLANE_WORDS}) &&
        (slot_object[1] == slot_object[2]) &&
        (slot_dim0[1] == slot_dim0[2]) &&
        (slot_dim0[1] >= cfg_kv_plane_rows) &&
        index_element_view_ok(
            slot_dtype[3], slot_rank[3], slot_dim0[3], slot_dim1[3],
            slot_dim2[3], slot_tail_dims[3], slot_stride0[3],
            slot_stride1[3], slot_stride2[3], slot_tail_strides[3]
        ) &&
        (captured_rank[3] == 8'd1) && (captured_axis[3] == 8'd0) &&
        (captured_extent[3] == 32'd1) &&
        head_row_view_ok(
            slot_dtype[4], slot_rank[4], QUERY_HEADS, slot_dim1[4],
            slot_dim2[4], slot_tail_dims[4], slot_stride0[4],
            slot_stride1[4], slot_stride2[4], slot_tail_strides[4]
        ) &&
        (captured_rank[4] == 8'd3) && (captured_axis[4] == 8'd0) &&
        (captured_extent[4] == 32'd1) && (captured_offset[4] == 64'd0);

    wire mapped_shape_ok =
        (vector_add_q || vector_silu_mul_q) ? elementwise_shape_ok
      : selection_argmax_q ? argmax_shape_ok
      : selection_token_append_q ? token_append_shape_ok
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
        (desc_data[895:864] == NO_ID);
    wire mapped_operator_arity_ok =
        ((vector_add_q || vector_silu_mul_q || dma_scatter_q) &&
         (desc_data[767:736] != NO_ID) &&
         (desc_data[799:768] == NO_ID) &&
         (desc_data[831:800] == NO_ID) &&
         (desc_data[927:896] == NO_ID) && (desc_data[959:928] == NO_ID) &&
         (desc_data[991:960] == NO_ID) && (desc_data[1023:992] == NO_ID)) ||
        ((selection_argmax_q || selection_token_append_q) &&
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

    // -- the base map, evaluated over the captured slots ------------------
    wire [32:0] slot0_map = place_lookup(slot_object[0]);
    wire [32:0] slot1_map = place_lookup(slot_object[1]);
    wire [32:0] slot2_map = place_lookup(slot_object[2]);
    wire [32:0] slot3_map = place_lookup(slot_object[3]);
    wire [32:0] slot4_map = place_lookup(slot_object[4]);
    wire mapped_bases_found =
        slot0_map[32] && slot4_map[32] &&
        (!expected_slot_mask[1] || slot1_map[32]) &&
        (!expected_slot_mask[2] || slot2_map[32]) &&
        (!expected_slot_mask[3] || slot3_map[32]);
    wire [31:0] kv_plane_span = cfg_kv_plane_rows * KV_PLANE_WORDS;
    wire [31:0] slot0_base = slot0_map[31:0] + captured_offset[0][31:0];
    wire [31:0] slot1_base = slot1_map[31:0] + captured_offset[1][31:0];
    wire [31:0] slot2_base = slot2_map[31:0] + kv_plane_span;
    wire [31:0] slot3_base = slot3_map[31:0] + captured_offset[3][31:0];
    wire [31:0] slot4_base = dma_scatter_q
        ? (slot4_map[31:0] + (scatter_plane_is_value ? kv_plane_span : 32'd0))
        : (slot4_map[31:0] + captured_offset[4][31:0]);
    wire [31:0] mapped_index_slot_base =
        attention_gqa_q ? slot3_base : slot0_base;

    // The context the request declares must be the position the index view
    // actually resolves to, plus one.  Neither is trusted alone.
    wire mapped_context_ok =
        (cfg_context_length != 32'd0) &&
        (cfg_kv_plane_rows != 32'd0) &&
        (cfg_context_length <= cfg_kv_plane_rows) &&
        (observed_index_value + 32'd1 == cfg_context_length);

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
                        if (issue_valid) begin
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
                                      (issue_sub == SELECTION_TOKEN_APPEND))))))) begin
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
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                op_numeric <= desc_data[671:640];
                                op_input0 <= desc_data[735:704];
                                op_input1 <= desc_data[767:736];
                                op_output0 <= desc_data[863:832];
                                op_aux0 <= desc_data[927:896];
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
                                (captured_extent[0] != 1)) begin
                                response_fault <= 1'b1;
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                index_raw_dim0 <= desc_view_dim0;
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
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                index_raw_dim0 <= desc_view_dim0;
                                source_rows <= (head_rms_norm_q || rope_q)
                                    ? desc_view_dim1
                                    : (matmul_q ? 32'd0 : 32'd1);
                                source_trailing <= (head_rms_norm_q || rope_q)
                                    ? desc_view_dim2 : EMBEDDING_WIDTH;
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
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                slot_view_id[slot_cursor] <= desc_id;
                                slot_dtype[slot_cursor] <= desc_view_dtype;
                                slot_rank[slot_cursor] <= desc_view_rank;
                                slot_terms[slot_cursor] <= desc_view_terms;
                                slot_object[slot_cursor] <= desc_primary_object;
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
                            mapped_element_count <=
                                (vector_add_q || vector_silu_mul_q)
                                ? elementwise_width
                                : selection_argmax_q ? argmax_vocabulary
                                : 32'd1;
                            mapped_result_words <=
                                (vector_add_q || vector_silu_mul_q)
                                ? elementwise_width
                                : dma_scatter_q ? KV_PLANE_WORDS
                                : attention_gqa_q ? GQA_OUTPUT_WORDS
                                : 32'd1;
                            mapped_work_words <=
                                vector_add_q ? elementwise_width
                                : vector_silu_mul_q
                                ? (32'd2 * elementwise_width)
                                : selection_argmax_q ? argmax_vocabulary
                                : attention_gqa_q
                                ? (cfg_context_length * QUERY_HEADS *
                                   HEAD_WIDTH)
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
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                numeric_profile_dtypes <= {
                                    desc_data[535:528],
                                    desc_data[543:536],
                                    desc_data[527:520],
                                    desc_data[519:512]
                                };
                                state <= S_START;
                            end
                        end
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
        : attention_gqa_q ? gqa_done : array_done;
    assign engine_busy = rope_q ? rope_busy
        : rms_norm_q ? rms_busy
        : vector_silu_mul_q ? silu_busy
        : selection_token_append_q ? append_busy
        : attention_gqa_q ? gqa_busy : array_busy;
    assign engine_error_code = rope_q ? rope_error_code
        : rms_norm_q ? rms_error_code
        : vector_silu_mul_q ? silu_error_code
        : selection_token_append_q ? append_error_code
        : attention_gqa_q ? gqa_error_code : array_error_code;
    assign engine_result_count = rope_q ? rope_result_count
        : rms_norm_q ? rms_result_count
        : vector_silu_mul_q ? silu_result_count
        : selection_token_append_q ? append_result_count
        : attention_gqa_q ? gqa_result_count : array_result_count;
    assign engine_work_count = rope_q ? rope_work_count
        : rms_norm_q ? rms_work_count
        : vector_silu_mul_q ? silu_work_count
        : selection_token_append_q ? append_work_count
        : attention_gqa_q ? gqa_work_count : array_work_count;
    wire [31:0] expected_result_count = mapped_family_q
        ? mapped_result_words
        : rms_norm_q ? (source_rows * source_trailing)
        : rope_q ? (source_rows * source_trailing)
        : matmul_q ? source_rows
        : dma_transfer_q ? (TRANSFER_COPIES * EMBEDDING_WIDTH)
        : source_trailing;
    wire [31:0] expected_work_count = mapped_family_q
        ? mapped_work_words
        : rms_norm_q ? (source_rows * source_trailing)
        : rope_q ? (source_rows * source_trailing)
        : matmul_q ? (source_rows * source_trailing)
        : dma_transfer_q ? TRANSFER_COPIES : 32'd1;

    // The index read the bridge itself performs before a scatter or an
    // attention: the position is architecture, not configuration.
    wire bridge_index_read = (state == S_MAP_INDEX_ISSUE);

    assign m0_rd_en = bridge_index_read ? 1'b1
        : rope_q ? rope_input_rd_en
        : rms_norm_q ? rms_input_rd_en
        : vector_silu_mul_q ? silu_a_rd_en
        : selection_token_append_q ? append_a_rd_en
        : attention_gqa_q ? gqa_mem_req_valid : array_m0_rd_en;
    assign m0_rd_addr = bridge_index_read ? mapped_index_slot_base
        : rope_q ? rope_input_rd_addr
        : rms_norm_q ? rms_input_rd_addr
        : vector_silu_mul_q ? silu_a_rd_addr
        : selection_token_append_q ? append_a_rd_addr
        : attention_gqa_q ? gqa_mem_req_addr : array_m0_rd_addr;
    assign m1_rd_en = rope_q ? rope_coefficient_rd_en
        : rms_norm_q ? rms_weight_rd_en
        : vector_silu_mul_q ? silu_b_rd_en
        : (selection_token_append_q || attention_gqa_q) ? 1'b0
        : array_m1_rd_en;
    assign m1_rd_addr = rope_q ? rope_coefficient_rd_addr
        : rms_norm_q ? rms_weight_rd_addr
        : vector_silu_mul_q ? silu_b_rd_addr
        : (selection_token_append_q || attention_gqa_q) ? 32'd0
        : array_m1_rd_addr;
    assign m2_rd_en = (rms_norm_q || rope_q || mapped_family_q)
        ? 1'b0 : array_m2_rd_en;
    assign m2_rd_addr = (rms_norm_q || rope_q || mapped_family_q)
        ? 32'd0 : array_m2_rd_addr;
    assign m3_rd_en = (rms_norm_q || rope_q || mapped_family_q)
        ? 1'b0 : array_m3_rd_en;
    assign m3_rd_addr = (rms_norm_q || rope_q || mapped_family_q)
        ? 32'd0 : array_m3_rd_addr;
    assign out_we = rope_q ? rope_out_we
        : rms_norm_q ? rms_out_we
        : vector_silu_mul_q ? silu_out_we
        : selection_token_append_q ? append_out_we
        : attention_gqa_q ? gqa_out_valid : array_out_we;
    assign out_addr = rope_q ? rope_out_addr
        : rms_norm_q ? rms_out_addr
        : vector_silu_mul_q ? silu_out_addr
        : selection_token_append_q ? append_out_addr
        : attention_gqa_q ? gqa_out_addr : array_out_addr;
    assign out_data = rope_q ? rope_out_data
        : rms_norm_q ? rms_out_data
        : vector_silu_mul_q ? silu_out_data
        : selection_token_append_q ? append_out_data
        : attention_gqa_q ? gqa_out_data : array_out_data;
    // The bridge's own index read and the scatter's index read address the
    // index bank; every other mapped operand and result is a plane of the
    // result bank the earlier operators produced.
    assign m0_reads_result = bridge_index_read ? 1'b0
        : (rms_norm_q || rope_q || matmul_q || vector_add_q ||
           vector_silu_mul_q || selection_argmax_q ||
           selection_token_append_q || attention_gqa_q);
    assign m1_reads_result = rope_q || dma_transfer_q || vector_add_q ||
        vector_silu_mul_q || dma_scatter_q;
    assign m1_reads_matmul_weight = matmul_q;

    wire [31:0] launch_index_base = dma_transfer_q
        ? cfg_transfer_index_base
        : (cfg_index_base + real_launch_count);
    wire [31:0] launch_source_base = dma_transfer_q
        ? cfg_transfer_source_base
        : embedding_q
            ? (cfg_embedding_source_base +
               embedding_launch_count * EMBEDDING_WIDTH)
            : (cfg_source_base +
               dma_gather_launch_count * cfg_source_launch_stride);
    wire [31:0] launch_output_base = launch_output_base_q;

    ot_a3_vector_rms_norm rms_norm (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & rms_norm_q),
        .cfg_count(expected_result_count),
        .cfg_rows(source_rows),
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

    ot_a3_vector_rope rope (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & rope_q),
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
        .SCALE_CODE(GQA_SCALE_CODE)
    ) gqa (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & attention_gqa_q),
        .cfg_context_length(mapped_context),
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

    ot_a3_engine_array engines (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & !rms_norm_q & !rope_q &
               !vector_silu_mul_q & !attention_gqa_q &
               !selection_token_append_q),
        .cfg_family(matmul_q ? FAMILY_TENSOR
                  : vector_add_q ? FAMILY_VECTOR
                  : selection_argmax_q ? FAMILY_SELECTION
                  : FAMILY_DMA),
        .cfg_sub(matmul_q ? TENSOR_MATMUL
               : vector_add_q ? VECTOR_ADD
               : selection_argmax_q ? SELECTION_ARGMAX
               : dma_scatter_q ? DMA_SCATTER
               : DMA_GATHER),
        .cfg_rows(matmul_q ? 16'd1 : 16'd0),
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
        .cfg_slots(dma_transfer_q ? TRANSFER_COPIES : 32'd1),
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
        .cfg_input0_dims(matmul_q
            ? {64'd0, source_trailing, 32'd1}
            : {96'd0, dma_transfer_q ? TRANSFER_COPIES : 32'd1}),
        .cfg_input1_dims({64'd0, source_trailing,
            dma_transfer_q ? 32'd1 : source_rows}),
        .cfg_input2_dims(128'd0),
        .cfg_input3_dims(128'd0),
        .cfg_output0_dims(matmul_q
            ? {64'd0, source_rows, 32'd1}
            : {64'd0, source_trailing,
               dma_transfer_q ? TRANSFER_COPIES : 32'd1}),
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
        slot_view_id[0], slot_terms[1], mapped_vocabulary};
endmodule
