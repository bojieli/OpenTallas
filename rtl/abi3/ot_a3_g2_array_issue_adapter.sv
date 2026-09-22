`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// G2 array issue adapter: the sequencer's issue stream to one LQ8 contraction
// array, and back.
//
// WHY AN ADAPTER EXISTS AT ALL.  ot_a3_microsequencer issues an operation as
// (family, sub, descriptor_id, index, serial, slot, queue) with an
// issue_ready handshake, and expects an asynchronous (complete_valid,
// complete_slot, complete_fault, complete_trap_class) some cycles later.
// ot_a3_lq8 takes a registered geometry bundle (cfg_rows, cfg_cols,
// cfg_depth, the two dtypes, the group and block sizes, five base addresses)
// and a start pulse, and answers with done plus a per-lane error class.  The
// two interfaces do not meet anywhere: nothing in the issue tuple is a
// geometry and nothing in the LQ8 is a slot.  This block is the minimum
// logic that turns one into the other.  It is modelled on
// rtl/abi3/ot_a3_engine_issue_bridge.sv, whose scalar 32-bit engine ports do
// not fit the LQ8's 128-bit weight stream, so it cannot simply be reused.
//
// WHERE THE GEOMETRY COMES FROM, EXACTLY.
//   * The sequencer publishes one resolved view per operand just before it
//     issues (publish_view: view_valid, view_descriptor_id, view_slot,
//     view_extent, view_element_offset, view_rank, view_irs_slot).  This
//     block captures operand slots 0, 1 and 4 for C = A x transpose(B).
//     Input slots 2/3 and output slot 5 are outside this contraction mapping.
//   * view_element_offset IS the resolved element offset of that operand, so
//     cfg_a_base, cfg_w_base and cfg_out_base are taken straight from the
//     views.  Nothing is invented.
//   * The view port carries ONE extent (the amendment-A18 axis extent), not a
//     shape, so M, N and K cannot come from it.  They come from the operand
//     TENSOR_VIEW descriptors themselves, read back over this block's own
//     descriptor-store port: dim[0] at payload[223:192] and dim[1] at
//     payload[255:224], the same two fields ot_a3_view_resolver decodes for
//     its bounding-range walk. A is rows x depth; B is cols x depth,
//     following the ABI N-major weight layout. C is read as rows x cols
//     before launch; its BF16/FP32 dtype selects the output representation.
//   * cfg_dtype_a and cfg_dtype_b are the dtype byte at payload[7:0] of the
//     two operand views.  The ABI dtype codes and ot_a3_format_pkg's FMT_*
//     codes are the same numbers (BF16 = 0x10, FP8_E4M3FN = 0x20,
//     MXFP4_E2M1 = 0x30), so the byte passes through unchanged and the lane
//     fails closed on anything it does not implement.
//   * cfg_scale_a and cfg_scale_b are the views' scale bindings: payload
//     bytes 4..7 hold scale_object, and A3_NO_ID there means unscaled.  This
//     is ot_a3_view_resolver's own out_scale_valid rule.
//
// WHAT IS NOT DERIVED, AND WHY -- the interface gap this block names rather
// than papers over.  The MX block geometry (cfg_group, cfg_block_a,
// cfg_block_rows_a, cfg_block_b), the two scale-table base addresses
// (cfg_scale_a_base, cfg_ws_base) are ABI NUMERIC-descriptor
// and schedule properties.  The TENSOR_VIEW payload does not carry them and
// the sequencer's view port does not publish them, so this block cannot read
// them from anywhere without a change to ot_a3_view_resolver or
// ot_a3_microsequencer -- both of which are open on another track and must
// not be touched here.  They are therefore per-transaction inputs of the
// cluster, written by the host beside the program base, and they are REAL
// primary inputs: nothing is tied to a constant, so no lane logic folds away.
// Closing the gap properly means widening the resolved-view stream to carry
// the operand's full dim vector and its numeric binding; that is a change to
// the control plane, not to this adapter.
//
// ONE OPERATION AT A TIME, AND WHAT THAT COSTS.  issue_ready is asserted only
// in S_IDLE, so the sequencer's 32-slot asynchronous issue window is
// serialised to one operation outstanding on this array.  That is a real
// restriction of this cluster, not of the control plane: the sequencer still
// tracks its slots, the dependence table and the scoreboard exactly as it
// does elsewhere, but no measurement of issue concurrency taken on this
// cluster describes the machine section 3.8 specifies.  A concurrent array
// needs a per-slot operation queue in front of the LQ8, which is more than
// the minimum this file is allowed to be.
//
// REFUSALS ARE PRECISE, NOT STUBS.  This cluster holds exactly one
// contraction array.  A TENSOR issue runs on it.  Every other family is
// answered with a CAPABILITY trap in the completion, which is what
// ot_a3_engine_issue_bridge already does for the opcodes it does not serve
// ("Every other opcode returns a precise CAPABILITY trap").  A malformed or
// out-of-range operand descriptor returns a DESCRIPTOR trap; a lane error
// returns an ENGINE trap.  No issue is ever accepted and dropped, so the
// sequencer cannot hang on this block: issue_ready is withheld while an
// operation is in flight and every accepted issue produces exactly one
// completion.
// ---------------------------------------------------------------------------
module ot_a3_g2_array_issue_adapter #(
    parameter integer LANES = 8
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          clear,

    // -- sequencer issue -------------------------------------------------
    input  wire          issue_valid,
    output wire          issue_ready,
    input  wire [7:0]    issue_family,
    /* verilator lint_off UNUSEDSIGNAL */
    input  wire [7:0]    issue_sub,
    input  wire [31:0]   issue_descriptor_id,
    /* verilator lint_on UNUSEDSIGNAL */
    input  wire [4:0]    issue_slot,

    // -- resolved views, published just before the issue -----------------
    input  wire          view_valid,
    input  wire [31:0]   view_descriptor_id,
    input  wire [2:0]    view_slot,
    // The current service addresses are 32 bits. Capture an overflow bit per
    // view and refuse before launch; never alias a 64-bit ABI offset by truncation.
    input  wire [63:0]   view_element_offset,
    input  wire [4:0]    view_irs_slot,

    // -- completion back to the sequencer --------------------------------
    output reg           complete_valid,
    output reg  [4:0]    complete_slot,
    output reg           complete_fault,
    output reg  [15:0]   complete_trap_class,

    // -- descriptor store, this block's own read port --------------------
    output reg           desc_req,
    output reg  [31:0]   desc_id,
    input  wire          desc_valid,
    input  wire          desc_fault,
    // The fixed header, shape, dtype and scale binding are read for A/B/C.
    // Object mapping and stride transport are still external to this adapter.
    /* verilator lint_off UNUSEDSIGNAL */
    input  wire [1535:0] desc_data,
    /* verilator lint_on UNUSEDSIGNAL */

    // -- per-transaction numeric configuration (the named gap above) -----
    input  wire [7:0]    cfg_group,
    input  wire [15:0]   cfg_block_a,
    input  wire [15:0]   cfg_block_rows_a,
    input  wire [15:0]   cfg_block_b,
    input  wire [31:0]   cfg_scale_a_base,
    input  wire [31:0]   cfg_ws_base,
    // Retained for source compatibility; output precision comes from C.
    /* verilator lint_off UNUSEDSIGNAL */
    input  wire          cfg_out_fp32,
    /* verilator lint_on UNUSEDSIGNAL */

    // -- LQ8 control ------------------------------------------------------
    output reg           array_start,
    output reg  [15:0]   array_rows,
    output reg  [15:0]   array_cols,
    output reg  [15:0]   array_depth,
    output reg  [7:0]    array_dtype_a,
    output reg  [7:0]    array_dtype_b,
    output reg  [7:0]    array_group,
    output reg  [31:0]   array_a_base,
    output reg           array_scale_a,
    output reg  [15:0]   array_block_a,
    output reg  [15:0]   array_block_rows_a,
    output reg  [31:0]   array_scale_a_base,
    output reg  [31:0]   array_w_base,
    output reg           array_scale_b,
    output reg  [15:0]   array_block_b,
    output reg  [31:0]   array_ws_base,
    output reg  [31:0]   array_out_base,
    output reg           array_out_fp32,
    // Captured descriptor metadata, owned through array completion/drain.
    output wire          output_layout_valid,
    output reg [31:0]    output_object,
    output wire [15:0]   output_logical_cols,
    input  wire          array_done,
    input  wire [7:0]    array_error_code,

    // -- observation ------------------------------------------------------
    output reg  [31:0]   launch_count,
    output reg  [31:0]   capability_refusals,
    output reg  [31:0]   descriptor_refusals,
    output reg  [31:0]   engine_faults,
    output reg  [31:0]   views_captured
);
    // LANES is a power of two (ot_a3_lq8's own requirement), so rounding a
    // column count up to a whole number of lane groups is a mask, not a
    // divide.
    localparam integer LANE_MASK_I = LANES - 1;
    localparam [15:0]  LANE_MASK   = LANE_MASK_I[15:0];

    localparam [2:0] S_IDLE   = 3'd0;
    localparam [2:0] S_DESC_A = 3'd1;
    localparam [2:0] S_DESC_B = 3'd2;
    localparam [2:0] S_CHECK  = 3'd3;
    localparam [2:0] S_RUN    = 3'd4;
    localparam [2:0] S_REFUSE = 3'd5;
    localparam [2:0] S_DESC_C = 3'd6;
    // Logical N is distinct from the array's lane-padded column count.
    reg [15:0] logical_cols;
    assign output_logical_cols=logical_cols;
    assign output_layout_valid=rst_n && !clear && state==S_RUN;

    reg  [2:0]  state;
    reg  [4:0]  slot_q;
    reg  [15:0] refuse_class;

    // -- the captured view set -------------------------------------------
    reg  [4:0]  view_irs_q;
    reg  [2:0]  view_have;
    reg  [2:0]  view_offset_overflow;
    reg         view_reset;
    reg  [31:0] view_id   [0:2];
    reg  [31:0] view_off  [0:2];

    // -- descriptor payload fields (ot_a3_resolver_bank's own slices) -----
    wire [31:0] d_magic          = desc_data[31:0];
    wire [15:0] d_type           = desc_data[47:32];
    wire [7:0]  d_type_major     = desc_data[55:48];
    wire [31:0] d_payload_offset = desc_data[351:320];
    wire [7:0]  d_dtype          = desc_data[519:512];    // payload[7:0]
    wire [31:0] d_scale_object   = desc_data[575:544];    // payload[63:32]
    wire [31:0] d_dim0           = desc_data[735:704];    // payload[223:192]
    wire [31:0] d_dim1           = desc_data[767:736];    // payload[255:224]

    wire d_header_ok = !desc_fault &&
                       (d_magic == ot_a3_pkg::A3_DESCRIPTOR_MAGIC) &&
                       (d_type_major == ot_a3_pkg::A3_TYPE_MAJOR) &&
                       (d_payload_offset == 32'd64) &&
                       (d_type == ot_a3_pkg::A3_DESC_TENSOR_VIEW);

    // A dimension the LQ8 can hold: non-zero and inside its 16-bit
    // configuration fields.
    function automatic dim_ok;
        input [31:0] value;
        begin
            dim_ok = (value != 32'd0) && (value[31:16] == 16'd0);
        end
    endfunction

    assign issue_ready = rst_n && !clear && (state == S_IDLE);

    // ABI slots 0..3 are inputs and 4..5 are outputs. Compact only the
    // two contraction inputs and first output into this adapter's three slots.
    wire contraction_view = (view_slot == 3'd0) || (view_slot == 3'd1) ||
                            (view_slot == 3'd4);
    wire [1:0] contraction_slot = (view_slot == 3'd4) ? 2'd2 : view_slot[1:0];
    wire all_views = (view_have == 3'b111) && (view_irs_q == issue_slot);

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state               <= S_IDLE;
            slot_q              <= 5'd0;
            refuse_class        <= ot_a3_pkg::A3_TRAP_NONE;
            view_irs_q          <= 5'd0;
            view_have           <= 3'b000;
            view_offset_overflow<=3'b000;
            view_reset          <= 1'b0;
            for (i = 0; i < 3; i = i + 1) begin
                view_id[i]  <= 32'd0;
                view_off[i] <= 32'd0;
            end
            complete_valid      <= 1'b0;
            complete_slot       <= 5'd0;
            complete_fault      <= 1'b0;
            complete_trap_class <= ot_a3_pkg::A3_TRAP_NONE;
            desc_req            <= 1'b0;
            desc_id             <= 32'd0;
            array_start         <= 1'b0;
            array_rows          <= 16'd0;
            array_cols          <= 16'd0;
            array_depth         <= 16'd0;
            array_dtype_a       <= 8'd0;
            array_dtype_b       <= 8'd0;
            array_group         <= 8'd0;
            array_a_base        <= 32'd0;
            array_scale_a       <= 1'b0;
            array_block_a       <= 16'd0;
            array_block_rows_a  <= 16'd0;
            array_scale_a_base  <= 32'd0;
            array_w_base        <= 32'd0;
            array_scale_b       <= 1'b0;
            array_block_b       <= 16'd0;
            array_ws_base       <= 32'd0;
            array_out_base      <= 32'd0;
            array_out_fp32      <= 1'b0;
            launch_count        <= 32'd0;
            capability_refusals <= 32'd0;
            descriptor_refusals <= 32'd0;
            engine_faults       <= 32'd0;
            views_captured      <= 32'd0;
        end else begin
            complete_valid <= 1'b0;
            desc_req       <= 1'b0;
            array_start    <= 1'b0;

            if (clear) begin
                state      <= S_IDLE;
                view_have  <= 3'b000;
                view_offset_overflow<=3'b000;
                view_reset <= 1'b0;
            end else begin

            // -- capture the resolved views ------------------------------
            // The captured set is dropped as soon as an issue consumes it.
            // Without that, an instruction whose operator names only two
            // views could inherit the third view of the previous instruction
            // when the sequencer recycles the same IRS slot number, and this
            // block would size an operation from a stale operand.  The views
            // of instruction N + 1 are always published after instruction N's
            // issue handshake, so the drop is safe.
            if (view_reset)begin
                view_have <= 3'b000;
                view_offset_overflow<=3'b000;
            end

            if (view_valid) begin
                views_captured <= views_captured + 32'd1;
                if (view_reset || (view_irs_q != view_irs_slot)) begin
                    view_irs_q <= view_irs_slot;
                    view_have  <= contraction_view ? (3'b001 << contraction_slot) : 3'b000;
                    view_offset_overflow<=contraction_view && (|view_element_offset[63:32]) ?
                                          (3'b001 << contraction_slot) : 3'b000;
                end else if (contraction_view) begin
                    view_have[contraction_slot] <= 1'b1;
                    view_offset_overflow[contraction_slot]<=|view_element_offset[63:32];
                end
                if (contraction_view) begin
                    view_id[contraction_slot]  <= view_descriptor_id;
                    view_off[contraction_slot] <= view_element_offset[31:0];
                end
            end
            if (view_reset)
                view_reset <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (issue_valid) begin
                        slot_q     <= issue_slot;
                        view_reset <= 1'b1;
                        if (issue_family != ot_a3_pkg::A3_MAJOR_TENSOR) begin
                            refuse_class <= ot_a3_pkg::A3_TRAP_CAPABILITY;
                            state        <= S_REFUSE;
                        end else if (!all_views) begin
                            // A TENSOR issue whose three operand views did not
                            // resolve is not runnable here.
                            refuse_class <= ot_a3_pkg::A3_TRAP_DESCRIPTOR;
                            state        <= S_REFUSE;
                        end else if (|view_offset_overflow) begin
                            refuse_class <= ot_a3_pkg::A3_TRAP_CAPABILITY;
                            state        <= S_REFUSE;
                        end else begin
                            // The two configuration values the ABI does carry
                            // reach the array unchanged.
                            array_group        <= cfg_group;
                            array_block_a      <= cfg_block_a;
                            array_block_rows_a <= cfg_block_rows_a;
                            array_block_b      <= cfg_block_b;
                            array_scale_a_base <= cfg_scale_a_base;
                            array_ws_base      <= cfg_ws_base;
                            // Output precision is captured from its descriptor.
                            array_a_base       <= view_off[0];
                            array_w_base       <= view_off[1];
                            array_out_base     <= view_off[2];
                            desc_req           <= 1'b1;
                            desc_id            <= view_id[0];
                            state              <= S_DESC_A;
                        end
                    end
                end

                // Operand A: rows x depth, its dtype and its scale binding.
                S_DESC_A: begin
                    if (desc_valid) begin
                        if (!d_header_ok || !dim_ok(d_dim0) || !dim_ok(d_dim1)) begin
                            refuse_class <= ot_a3_pkg::A3_TRAP_DESCRIPTOR;
                            state        <= S_REFUSE;
                        end else begin
                            array_rows    <= d_dim0[15:0];
                            array_depth   <= d_dim1[15:0];
                            array_dtype_a <= d_dtype;
                            array_scale_a <= (d_scale_object != ot_a3_pkg::A3_NO_ID);
                            desc_req      <= 1'b1;
                            desc_id       <= view_id[1];
                            state         <= S_DESC_B;
                        end
                    end
                end

                // Operand B: cols x depth, its dtype and its scale binding.
                S_DESC_B: begin
                    if (desc_valid) begin
                        if (!d_header_ok || !dim_ok(d_dim0) || !dim_ok(d_dim1)) begin
                            refuse_class <= ot_a3_pkg::A3_TRAP_DESCRIPTOR;
                            state        <= S_REFUSE;
                        end else if (d_dim1[15:0] != array_depth) begin
                            // A's inner extent and B's inner extent are the
                            // same K or the operation is not this contraction.
                            refuse_class <= ot_a3_pkg::A3_TRAP_DESCRIPTOR;
                            state        <= S_REFUSE;
                        end else begin
                            array_dtype_b <= d_dtype;
                            array_scale_b <= (d_scale_object != ot_a3_pkg::A3_NO_ID);
                            // cfg_cols must be a multiple of LANES: the LQ8
                            // gives lane i block columns c * LANES + i, so a
                            // short final group needs padded execution. Runtime
                            // output enqueue masks the trailing columns; legacy
                            // consumers must apply the published logical shape.
                            array_cols    <= (d_dim0[15:0] + LANE_MASK) & ~LANE_MASK;
                            logical_cols  <= d_dim0[15:0];
                            desc_req      <= 1'b1;
                            desc_id       <= view_id[2];
                            state         <= S_DESC_C;
                        end
                    end
                end

                // C is rows x logical columns. Its descriptor owns output
                // precision; a host hint cannot silently change the ABI object.
                S_DESC_C: begin
                    if (desc_valid) begin
                        if (!d_header_ok || d_dim0 != {16'd0,array_rows} ||
                            d_dim1 != {16'd0,logical_cols}) begin
                            refuse_class <= ot_a3_pkg::A3_TRAP_DESCRIPTOR;
                            state <= S_REFUSE;
                        end else if ((d_dtype != 8'h10 && d_dtype != 8'h12) ||
                                     d_scale_object != ot_a3_pkg::A3_NO_ID) begin
                            // The lane emits BF16 or FP32, without output scales.
                            refuse_class <= ot_a3_pkg::A3_TRAP_CAPABILITY;
                            state <= S_REFUSE;
                        end else begin
                            output_object <= desc_data[159:128];
                            array_out_fp32 <= (d_dtype == 8'h12);
                            state <= S_CHECK;
                        end
                    end
                end

                S_CHECK: begin
                    if (array_cols == 16'd0) begin
                        refuse_class <= ot_a3_pkg::A3_TRAP_CAPABILITY;
                        state        <= S_REFUSE;
                    end else begin
                        array_start  <= 1'b1;
                        launch_count <= launch_count + 32'd1;
                        state        <= S_RUN;
                    end
                end

                S_RUN: begin
                    if (array_done) begin
                        complete_valid      <= 1'b1;
                        complete_slot       <= slot_q;
                        complete_fault      <= (array_error_code != 8'd0);
                        complete_trap_class <= (array_error_code != 8'd0) ?
                                               ot_a3_pkg::A3_TRAP_ENGINE :
                                               ot_a3_pkg::A3_TRAP_NONE;
                        if (array_error_code != 8'd0)
                            engine_faults <= engine_faults + 32'd1;
                        state <= S_IDLE;
                    end
                end

                S_REFUSE: begin
                    complete_valid      <= 1'b1;
                    complete_slot       <= slot_q;
                    complete_fault      <= 1'b1;
                    complete_trap_class <= refuse_class;
                    if (refuse_class == ot_a3_pkg::A3_TRAP_CAPABILITY)
                        capability_refusals <= capability_refusals + 32'd1;
                    else
                        descriptor_refusals <= descriptor_refusals + 32'd1;
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
            end // clear has priority over all capture and state transitions
        end
    end
endmodule
