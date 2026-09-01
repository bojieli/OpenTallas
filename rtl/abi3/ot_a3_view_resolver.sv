`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 tensor-view resolver: amendments A4, A13, A18 and A26.
//
// This block is the RTL transcription of runtime/sim/memory.ViewResolver.resolve
// and its helpers _walks_extent_axis and _remaining_extent.  Those functions are
// the normative reference: where this block and the functional simulator could
// disagree, the simulator is right, and tools/build_abi3_rtl_vectors.py
// cross-checks every vector against the simulator's own result rather than a
// hand-computed one.
//
// Amendment A4 (wire format section 12.1).  A tensor view carries up to four
// dynamic terms, each { uint16 selector_kind, uint16 selector_index,
// uint32 element_stride }, contributing selector_value * element_stride
// elements to the view's element offset.  LOOP_INDUCTION reads the induction
// *value* of an open loop -- lower_bound + n*step, which is what the golden
// model puts in its ``loops`` mapping -- and RUNTIME_SYMBOL reads the request's
// binding for a symbol in the section 12.2 registry.
//
// Amendment A13 (wire format section 12.4) and amendment A18 (section 12.8).  A
// view states static extents, so a block loop over a symbolic extent would
// present elements the request does not have on its final iteration.  A18 lets
// the view say *which* axis the request determines and what affine function of
// the bound symbol gives it; A13 is the ``axis = 0, numerator = 1, unit = 1,
// bias = 0`` case of it, exactly.  With ``n`` the numerator, ``u`` the unit,
// ``b`` the bias, ``a`` the axis and a loop divisor ``d``:
//
//     step      = n * d / u                             (elements per iteration)
//     tokens    = symbol_value - iteration * d          (symbol units left)
//     extent    = n * tokens / u + b                    (floored, then biased)
//     dim[a]    = extent if 0 < extent < dim[a] else dim[a]
//
// with four refinements the reference resolver applies and the prose summary
// leaves implicit, all transcribed here:
//
//   * the clamp reaches only a term that walks the *declared* axis, and which
//     terms those are is derived rather than assumed: one iteration advances
//     by one whole block of that axis, so ``term_stride == stride[a] * step``
//     (ViewResolver._walks_extent_axis).  A view may perfectly well be indexed
//     by a loop along some other axis -- the mHC branch reduction's leading
//     axis is four hyper-connection streams while its loop steps over tokens --
//     and clamping that view would present four streams as one, which is not a
//     partial final iteration of anything.
//   * a unit that does not divide ``n * d`` means one iteration is not a whole
//     number of that axis's elements, so the term walks nothing and bounds
//     nothing;
//   * _remaining_extent treats a loop as partial only while
//     0 < extent < step + b.  An extent at or above what a whole iteration
//     covers is a full iteration and contributes no bound at all;
//   * when more than one term indexes the view through a symbol-bounded loop,
//     the smallest extent wins (``min(current, extent)``).
//
// The bias is added *after* the division and does not enter ``step``: it is a
// count every iteration carries rather than one an iteration advances by, which
// is what lets an attention KV join state ``span + 128`` for its 128-row
// sliding window.
//
// The axis test is a property of one term and one loop, so it is evaluated per
// term against that term's own stride and that loop's own divisor: one view may
// carry a term that clamps and a term that does not.
//
// A loop that is not symbol-bounded, or whose bound symbol this request did not
// bind, contributes no partial extent: its iterations are all full by
// construction.  The bound kind, the divisor and the symbol's value are read
// from the loop stack's query port, which caches them at LOOP_SETUP, so no
// LOOP_CONTROL descriptor is re-fetched here.
//
// Fail-closed paths mirror the reference, which raises MemoryError_ (trap class
// 7) rather than resolving: a LOOP_INDUCTION term naming a loop that is not
// open, a RUNTIME_SYMBOL term naming a symbol this request did not bind or one
// outside the frozen registry, an A18 extent axis at or beyond the view's rank,
// and any selector kind that is neither of the two.  Note that CONSTANT (=2) is
// listed by section 12.1 but is *rejected* by the reference resolver; this
// block follows the reference.
//
// One 32x32 product is unavoidable -- ``selector_value * element_stride`` is
// the A4 term itself -- so a single multiplier is shared between the offset
// term, A18's ``n * d`` and ``n * tokens`` numerators, the axis test's
// ``stride[a] * step`` and the ``iteration * bound_divisor`` product, evaluated
// in successive cycles.  All of them are compared and accumulated at 64 bits,
// so a product that does not fit in 32 fails the axis test rather than wrapping
// into passing it.  The two divisions by ``u`` use one shared restoring divider
// over a 64-bit numerator, the same structure ot_a3_loop_stack already uses for
// ``bound_divisor``; a numerator and unit of one -- every view written before
// A18 -- bypasses it entirely, so the A13 path costs exactly the cycles it
// always did.  The block therefore has a bounded, data-independent cost and no
// wide arithmetic in the caller's control path.
// ---------------------------------------------------------------------------
module ot_a3_view_resolver
    import ot_a3_pkg::*;
(
    input  wire          clk,
    input  wire          rst_n,
    input  wire          clear,

    // The 128-byte TENSOR_VIEW payload, held stable by the caller from
    // ``start`` until ``done``.  Layout fields this block does not consume --
    // trailing dims and strides, the scale binding -- belong to an engine
    // datapath, not to view resolution.
    input  wire          start,
    /* verilator lint_off UNUSED */
    input  wire [1023:0] payload,
    /* verilator lint_on UNUSED */

    output reg           busy,
    output reg           done,
    output reg           fault,
    output reg  [15:0]   trap_class,

    output reg  [63:0]   out_element_offset,
    // The resolved extent of the axis amendment A18 names, and that axis.  For
    // every view written before A18 the axis is zero and this is the leading
    // extent A13 has always published.
    output reg  [31:0]   out_extent,
    output wire [7:0]    out_extent_axis,
    output wire [7:0]    out_rank,
    output wire [7:0]    out_dtype,
    output wire [7:0]    out_term_count,

    // Loop stack query port (combinational).
    output reg  [31:0]   loop_query_id,
    input  wire          loop_query_active,
    input  wire [31:0]   loop_query_value,
    input  wire          loop_query_symbol_bounded,
    input  wire [31:0]   loop_query_divisor,
    input  wire [31:0]   loop_query_bound_value,

    // Runtime symbol file (combinational).
    output reg  [3:0]    sym_index,
    input  wire [31:0]   sym_value,
    input  wire          sym_bound
);
    // -- TENSOR_VIEW payload view (runtime/abi3/descriptors.TENSOR_VIEW_PAYLOAD)
    // dtype@0 rank@1 layout_class@2 dynamic_term_count@3, element_offset@16,
    // dim{i}@24+4i, stride{i}@48+4i, term{i} = {kind u16, index u16,
    // stride u32}@72+8i, extent_unit@108, extent_numerator@112, extent_bias@116,
    // edge_mask_id@12, extent_axis@120.
    wire [7:0]  view_dtype       = payload[7:0];
    wire [7:0]  view_rank        = payload[15:8];
    wire [7:0]  view_terms       = payload[31:24];
    // Amendment A26: an edge mask names an active loop whose final partial
    // extent clamps the view but whose induction contributes no address
    // offset.  This is the fixed-address rolling-buffer form.
    wire [31:0] view_edge_mask   = payload[127:96];
    wire [63:0] view_offset      = payload[191:128];
    // Amendment A18: the unit at byte 108, the numerator at 112, the bias at
    // 116 and the axis at 120.  All four are zero on every view written before
    // the amendment, and that is axis 0, the symbol's own value and no bias --
    // amendment A13 unchanged.
    wire [31:0] view_unit_raw    = payload[895:864];
    wire [31:0] view_num_raw     = payload[927:896];
    wire [31:0] view_bias        = payload[959:928];
    wire [7:0]  view_extent_axis = payload[967:960];
    wire [31:0] view_unit        = (view_unit_raw == 32'd0) ? 32'd1 : view_unit_raw;
    wire [31:0] view_numerator   = (view_num_raw  == 32'd0) ? 32'd1 : view_num_raw;
    //: True when the affine function is the identity, which is A13's own case
    //: and every view written before this amendment.  It bypasses the divider.
    wire        view_identity    = (view_unit == 32'd1) && (view_numerator == 32'd1);

    assign out_rank        = view_rank;
    assign out_dtype       = view_dtype;
    assign out_term_count  = view_terms;
    assign out_extent_axis = view_extent_axis;

    // dim[a] and stride[a] for the declared axis.  A13 read dim0 and stride0
    // because axis zero was the only axis it could clamp; the mux is the whole
    // structural difference A18 makes to this block's read surface.
    reg [31:0] view_dim_axis;
    reg [31:0] view_stride_axis;
    always @* begin
        case (view_extent_axis)
            8'd0: begin
                view_dim_axis    = payload[223:192];
                view_stride_axis = payload[415:384];
            end
            8'd1: begin
                view_dim_axis    = payload[255:224];
                view_stride_axis = payload[447:416];
            end
            8'd2: begin
                view_dim_axis    = payload[287:256];
                view_stride_axis = payload[479:448];
            end
            8'd3: begin
                view_dim_axis    = payload[319:288];
                view_stride_axis = payload[511:480];
            end
            8'd4: begin
                view_dim_axis    = payload[351:320];
                view_stride_axis = payload[543:512];
            end
            default: begin
                view_dim_axis    = payload[383:352];
                view_stride_axis = payload[575:544];
            end
        endcase
    end

    reg [15:0] term_kind;
    reg [15:0] term_index;
    reg [31:0] term_stride;
    // Three bits, not two: the walk runs to dynamic_term_count inclusive, so a
    // view carrying the maximum four terms needs a slot counter that can reach
    // four without wrapping back onto term zero.
    reg [2:0]  slot;
    always @* begin
        case (slot)
            3'd0: begin
                term_kind   = payload[591:576];
                term_index  = payload[607:592];
                term_stride = payload[639:608];
            end
            3'd1: begin
                term_kind   = payload[655:640];
                term_index  = payload[671:656];
                term_stride = payload[703:672];
            end
            3'd2: begin
                term_kind   = payload[719:704];
                term_index  = payload[735:720];
                term_stride = payload[767:736];
            end
            default: begin
                term_kind   = payload[783:768];
                term_index  = payload[799:784];
                term_stride = payload[831:800];
            end
        endcase
    end

    localparam [3:0] S_IDLE      = 4'd0;
    localparam [3:0] S_SELECT    = 4'd1;
    localparam [3:0] S_READ      = 4'd2;
    localparam [3:0] S_OFFSET    = 4'd3;
    localparam [3:0] S_BLOCK     = 4'd4;
    localparam [3:0] S_NUM_STEP  = 4'd5;
    localparam [3:0] S_DIV_STEP  = 4'd6;
    localparam [3:0] S_AXIS_MUL  = 4'd7;
    localparam [3:0] S_AXIS      = 4'd8;
    localparam [3:0] S_REMAIN    = 4'd9;
    localparam [3:0] S_SCALE     = 4'd10;
    localparam [3:0] S_NUM_EXT   = 4'd11;
    localparam [3:0] S_DIV_EXT   = 4'd12;
    localparam [3:0] S_FOLD      = 4'd13;
    localparam [3:0] S_FINISH    = 4'd14;
    localparam [3:0] S_EDGE_READ = 4'd15;

    reg [3:0]  state;
    reg [31:0] value;            // the selector's resolved value
    reg        value_is_loop;
    reg        loop_symbolic;
    reg [31:0] loop_divisor;
    reg [31:0] loop_bound;
    reg [63:0] axis_step;        // n * bound_divisor / unit, elements per iteration
    reg        unit_divides;     // (n * bound_divisor) % unit == 0
    reg [63:0] axis_extent;      // n * tokens / unit + bias, elements of the axis
    reg        remain_valid;     // "leading_loop is not None"
    reg [31:0] remain;           // the smallest resolved extent so far
    reg        edge_phase;       // resolving edge_mask_id, not a dynamic term
    reg        edge_done;

    // -- one shared 32x32 product ------------------------------------------
    reg  [31:0] mul_a;
    reg  [31:0] mul_b;
    reg  [63:0] product;
    wire [63:0] product_w = mul_a * mul_b;

    // -- shared restoring divider: quotient = floor(numerator / divisor) ----
    // The same structure ot_a3_loop_stack uses for ``bound_divisor``; A18's two
    // divisions are both by ``extent_unit``, and a unit of one bypasses it.
    reg         div_start;
    reg  [63:0] div_numerator;
    reg  [31:0] div_divisor;
    reg  [63:0] div_shift;
    reg  [63:0] div_remainder;
    reg  [63:0] div_quotient;
    reg  [6:0]  div_count;
    reg         div_busy;
    reg         div_done;
    wire [63:0] div_trial = {div_remainder[62:0], div_shift[63]};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            div_busy <= 1'b0;
            div_done <= 1'b0;
            div_shift <= 64'd0;
            div_remainder <= 64'd0;
            div_quotient <= 64'd0;
            div_count <= 7'd0;
        end else begin
            div_done <= 1'b0;
            if (div_start) begin
                div_busy <= 1'b1;
                div_shift <= div_numerator;
                div_remainder <= 64'd0;
                div_quotient <= 64'd0;
                div_count <= 7'd64;
            end else if (div_busy) begin
                if (div_trial >= {32'd0, div_divisor}) begin
                    div_remainder <= div_trial - {32'd0, div_divisor};
                    div_quotient <= {div_quotient[62:0], 1'b1};
                end else begin
                    div_remainder <= div_trial;
                    div_quotient <= {div_quotient[62:0], 1'b0};
                end
                div_shift <= {div_shift[62:0], 1'b0};
                div_count <= div_count - 7'd1;
                if (div_count == 7'd1) begin
                    div_busy <= 1'b0;
                    div_done <= 1'b1;
                end
            end
        end
    end

    // tokens = symbol_value - iteration * bound_divisor, evaluated wide and
    // signed so that an iteration past the extent is negative rather than
    // wrapping to a huge positive count.  It is in the *bound symbol's* units;
    // A18's affine function converts it to the axis's own.
    wire signed [64:0] remaining_s =
        $signed({33'd0, loop_bound}) - $signed({1'b0, product});
    wire remaining_positive = remaining_s > 65'sd0;
    wire [31:0] remaining_units = remaining_s[31:0];
    // A resolved extent bounds the axis only while it is a *partial* iteration:
    // strictly below what a whole one covers, which is the step plus the bias.
    wire [63:0] axis_iteration = axis_step + {32'd0, view_bias};
    // The extent is published as 32 bits, so one wider than that is not a bound
    // this block can state; it fails closed to the declared extent rather than
    // truncating into a smaller one.
    wire extent_partial = (axis_extent != 64'd0) &&
                          (axis_extent[63:32] == 32'd0) &&
                          (axis_extent < axis_iteration);

    // _walks_extent_axis: this term walks the declared axis exactly when one
    // iteration advances by one whole block of it.  ``product_w`` holds
    // ``stride[axis] * step`` while the walk is in S_AXIS; the comparison is 64
    // bits wide on both sides so a product too large for a 32-bit stride is
    // unequal rather than truncated into equality.
    wire walks_extent_axis = unit_divides && (product_w == {32'd0, term_stride});

    task fail_closed;
        input [15:0] class_value;
        begin
            busy <= 1'b0;
            done <= 1'b1;
            fault <= 1'b1;
            trap_class <= class_value;
            state <= S_IDLE;
        end
    endtask

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            fault <= 1'b0;
            trap_class <= A3_TRAP_NONE;
            out_element_offset <= 64'd0;
            out_extent <= 32'd0;
            loop_query_id <= A3_NO_ID;
            sym_index <= 4'd0;
            slot <= 3'd0;
            value <= 32'd0;
            value_is_loop <= 1'b0;
            loop_symbolic <= 1'b0;
            loop_divisor <= 32'd1;
            loop_bound <= 32'd0;
            axis_step <= 64'd1;
            unit_divides <= 1'b1;
            axis_extent <= 64'd0;
            remain_valid <= 1'b0;
            remain <= 32'd0;
            edge_phase <= 1'b0;
            edge_done <= 1'b0;
            mul_a <= 32'd0;
            mul_b <= 32'd0;
            product <= 64'd0;
            div_start <= 1'b0;
            div_numerator <= 64'd0;
            div_divisor <= 32'd1;
        end else begin
            done <= 1'b0;
            div_start <= 1'b0;
            if (clear) begin
                state <= S_IDLE;
                busy <= 1'b0;
                fault <= 1'b0;
            end else begin
                case (state)
                    S_IDLE: begin
                        if (start) begin
                            busy <= 1'b1;
                            fault <= 1'b0;
                            trap_class <= A3_TRAP_NONE;
                            out_element_offset <= view_offset;
                            slot <= 3'd0;
                            remain_valid <= 1'b0;
                            remain <= 32'd0;
                            edge_phase <= 1'b0;
                            edge_done <= 1'b0;
                            // "amendment A18 extent axis A is outside the
                            // rank-R view that declares it".  Rank zero has no
                            // axes at all, which the reference guards with
                            // ``if rank and ...``.
                            if ((view_rank != 8'd0) &&
                                (view_extent_axis >= view_rank))
                                fail_closed(A3_TRAP_MEMORY);
                            else
                                state <= S_SELECT;
                        end
                    end
                    // Drive the loop and symbol selects for this term; both
                    // reads are combinational and are consumed next cycle.
                    S_SELECT: begin
                        if ({5'd0, slot} >= view_terms) begin
                            if (!edge_done && (view_edge_mask != A3_NO_ID)) begin
                                // The same loop-stack query used by an A4 term,
                                // but A26 deliberately skips S_OFFSET.
                                loop_query_id <= view_edge_mask;
                                edge_phase <= 1'b1;
                                state <= S_EDGE_READ;
                            end else begin
                                state <= S_FINISH;
                            end
                        end else begin
                            edge_phase <= 1'b0;
                            loop_query_id <= {16'd0, term_index};
                            sym_index <= term_index[3:0];
                            state <= S_READ;
                        end
                    end
                    S_EDGE_READ: begin
                        if (!loop_query_active) begin
                            // "view N: edge-mask loop M is not active"
                            fail_closed(A3_TRAP_MEMORY);
                        end else begin
                            value <= loop_query_value;
                            loop_symbolic <= loop_query_symbol_bounded;
                            loop_divisor <= loop_query_divisor;
                            loop_bound <= loop_query_bound_value;
                            edge_done <= 1'b1;
                            if (!loop_query_symbol_bounded) begin
                                // The functional resolver gives a non-symbolic
                                // loop no partial extent.  Admission rejects
                                // this form, but the resolver still fails
                                // closed to the declared dimension if reached.
                                state <= S_SELECT;
                            end else if (view_identity) begin
                                axis_step <= {32'd0, loop_query_divisor};
                                unit_divides <= 1'b1;
                                mul_a <= loop_query_value;
                                mul_b <= loop_query_divisor;
                                state <= S_REMAIN;
                            end else begin
                                mul_a <= view_numerator;
                                mul_b <= loop_query_divisor;
                                state <= S_NUM_STEP;
                            end
                        end
                    end
                    S_READ: begin
                        if (term_kind == {8'd0, A3_SELECTOR_LOOP_INDUCTION}) begin
                            if (!loop_query_active) begin
                                // "view N: loop M is not active"
                                fail_closed(A3_TRAP_MEMORY);
                            end else begin
                                value <= loop_query_value;
                                value_is_loop <= 1'b1;
                                loop_symbolic <= loop_query_symbol_bounded;
                                loop_divisor <= loop_query_divisor;
                                loop_bound <= loop_query_bound_value;
                                mul_a <= loop_query_value;
                                mul_b <= term_stride;
                                state <= S_OFFSET;
                            end
                        end else if (term_kind ==
                                     {8'd0, A3_SELECTOR_RUNTIME_SYMBOL}) begin
                            if (({16'd0, term_index} >= A3_SYMBOL_COUNT) ||
                                !sym_bound) begin
                                // "view N: symbol S is unbound"
                                fail_closed(A3_TRAP_MEMORY);
                            end else begin
                                value <= sym_value;
                                value_is_loop <= 1'b0;
                                mul_a <= sym_value;
                                mul_b <= term_stride;
                                state <= S_OFFSET;
                            end
                        end else begin
                            // "view N: bad selector kind K".  CONSTANT lands
                            // here, exactly as the reference resolver does.
                            fail_closed(A3_TRAP_MEMORY);
                        end
                    end
                    S_OFFSET: begin
                        product <= product_w;
                        state <= S_BLOCK;
                    end
                    S_BLOCK: begin
                        out_element_offset <= out_element_offset + product;
                        if (value_is_loop && loop_symbolic) begin
                            if (view_identity) begin
                                // A13's own function: one iteration is one
                                // whole block of the axis, in the symbol's own
                                // units, and no division is needed.
                                axis_step <= {32'd0, loop_divisor};
                                unit_divides <= 1'b1;
                                mul_a <= view_stride_axis;
                                mul_b <= loop_divisor;
                                state <= S_AXIS;
                            end else begin
                                mul_a <= view_numerator;
                                mul_b <= loop_divisor;
                                state <= S_NUM_STEP;
                            end
                        end else begin
                            slot <= slot + 3'd1;
                            state <= S_SELECT;
                        end
                    end
                    S_NUM_STEP: begin
                        // product_w is numerator * bound_divisor this cycle.
                        div_start <= 1'b1;
                        div_numerator <= product_w;
                        div_divisor <= view_unit;
                        state <= S_DIV_STEP;
                    end
                    S_DIV_STEP: begin
                        if (div_done) begin
                            axis_step <= div_quotient;
                            // A unit that does not divide ``n * d`` means one
                            // iteration is not a whole number of this axis's
                            // elements, so the term walks nothing.
                            unit_divides <= (div_remainder == 64'd0);
                            if (edge_phase) begin
                                if (div_remainder == 64'd0) begin
                                    mul_a <= value;
                                    mul_b <= loop_divisor;
                                    state <= S_REMAIN;
                                end else begin
                                    // iteration_extent() is undefined: no
                                    // clamp, matching _remaining_extent.
                                    state <= S_SELECT;
                                end
                            end else begin
                                state <= S_AXIS_MUL;
                            end
                        end
                    end
                    S_AXIS_MUL: begin
                        // A step wider than 32 bits cannot equal any
                        // ``stride[axis] * step`` a 32-bit stride can name, so
                        // the walk test would fail anyway; the multiplier takes
                        // the low half and the wide compare in S_AXIS decides.
                        mul_a <= view_stride_axis;
                        mul_b <= axis_step[31:0];
                        state <= S_AXIS;
                    end
                    S_AXIS: begin
                        // product_w is stride[axis] * step this cycle and
                        // term_stride is still this term's own: the slot
                        // counter has not advanced.  A term along any other
                        // axis is not a partial final iteration of this one, so
                        // it contributes no bound and the walk moves on without
                        // touching ``remain``.
                        if (walks_extent_axis && (axis_step[63:32] == 32'd0)) begin
                            mul_a <= value;
                            mul_b <= loop_divisor;
                            state <= S_REMAIN;
                        end else begin
                            slot <= slot + 3'd1;
                            state <= S_SELECT;
                        end
                    end
                    S_REMAIN: begin
                        // product_w is iteration * bound_divisor this cycle;
                        // register it so remaining_s is evaluated from a
                        // settled value on the next.
                        product <= product_w;
                        state <= S_SCALE;
                    end
                    S_SCALE: begin
                        if (!remaining_positive) begin
                            // An iteration at or past the extent bounds
                            // nothing: the affine image of a count the loop
                            // never poses is not an extent, so the divider is
                            // not needed to know that.
                            slot <= slot + 3'd1;
                            state <= S_SELECT;
                        end else if (view_identity) begin
                            axis_extent <= {32'd0, remaining_units} +
                                           {32'd0, view_bias};
                            state <= S_FOLD;
                        end else begin
                            mul_a <= view_numerator;
                            mul_b <= remaining_units;
                            state <= S_NUM_EXT;
                        end
                    end
                    S_NUM_EXT: begin
                        // product_w is numerator * tokens this cycle; the same
                        // shared multiplier, one state later.
                        div_start <= 1'b1;
                        div_numerator <= product_w;
                        div_divisor <= view_unit;
                        state <= S_DIV_EXT;
                    end
                    S_DIV_EXT: begin
                        if (div_done) begin
                            // The bias is added after the division, because it
                            // is a count the operand carries whatever the
                            // request is rather than a scaling of it.
                            axis_extent <= div_quotient + {32'd0, view_bias};
                            state <= S_FOLD;
                        end
                    end
                    S_FOLD: begin
                        // _remaining_extent: a loop bounds the axis only while
                        // 0 < extent < step + bias, and the smallest bound
                        // across terms wins.
                        if (extent_partial &&
                            (!remain_valid ||
                             (axis_extent < {32'd0, remain}))) begin
                            remain <= axis_extent[31:0];
                            remain_valid <= 1'b1;
                        end
                        if (!edge_phase)
                            slot <= slot + 3'd1;
                        state <= S_SELECT;
                    end
                    S_FINISH: begin
                        // resolve(): dim[axis] = extent if 0 < extent <
                        // dim[axis].  ``dims`` is empty at rank zero, which the
                        // reference guards with ``and dims``.
                        if (remain_valid && (view_rank != 8'd0) &&
                            (remain != 32'd0) && (remain < view_dim_axis))
                            out_extent <= remain;
                        else
                            out_extent <= view_dim_axis;
                        busy <= 1'b0;
                        done <= 1'b1;
                        fault <= 1'b0;
                        state <= S_IDLE;
                    end
                    default: state <= S_IDLE;
                endcase
            end
        end
    end
endmodule
