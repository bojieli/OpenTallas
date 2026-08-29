`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 tensor-view resolver: amendments A4 and A13.
//
// This block is the RTL transcription of runtime/sim/memory.ViewResolver.resolve
// and its helper _remaining_rows.  Those two functions are the normative
// reference: where this block and the functional simulator could disagree, the
// simulator is right, and tools/build_abi3_rtl_vectors.py cross-checks every
// vector against the simulator's own result rather than a hand-computed one.
//
// Amendment A4 (wire format section 12.1).  A tensor view carries up to four
// dynamic terms, each { uint16 selector_kind, uint16 selector_index,
// uint32 element_stride }, contributing selector_value * element_stride
// elements to the view's element offset.  LOOP_INDUCTION reads the induction
// *value* of an open loop -- lower_bound + n*step, which is what the golden
// model puts in its ``loops`` mapping -- and RUNTIME_SYMBOL reads the request's
// binding for a symbol in the section 12.2 registry.
//
// Amendment A13 (wire format section 12.4).  A view states static extents, so a
// block loop over a symbolic extent would present rows the request does not
// have on its final iteration.  When a view's leading axis is indexed by a
// LOOP_INDUCTION term over a symbol-bounded loop, the resolved leading extent
// is
//
//     remaining = symbol_value - iteration * bound_divisor
//     dim0      = remaining if 0 < remaining < dim0 else dim0
//
// with three refinements the reference resolver applies and the prose summary
// leaves implicit, all transcribed here:
//
//   * the clamp reaches only a term that walks the *leading* axis, and which
//     terms those are is derived rather than assumed: one iteration advances
//     by one whole block of leading rows, so the term's stride is
//     ``stride0 * bound_divisor`` (ViewResolver._indexes_leading_axis).  A view
//     may perfectly well be indexed by a loop along some other axis -- the mHC
//     branch reduction's leading axis is four hyper-connection streams while
//     its loop steps over tokens -- and clamping that view would present four
//     streams as one, which is not a partial final iteration of anything.
//   * _remaining_rows treats a loop as partial only while
//     0 < remaining < bound_divisor.  A remaining count at or above the block
//     size is a full iteration and contributes no bound at all.
//   * when more than one term indexes the view through a symbol-bounded loop,
//     the smallest remaining count wins (``min(current, remaining)``).
//
// The leading-axis test is a property of one term and one loop, so it is
// evaluated per term against that term's own stride and that loop's own
// divisor: one view may carry a term that clamps and a term that does not.
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
// outside the frozen registry, and any selector kind that is neither.  Note
// that CONSTANT (=2) is listed by section 12.1 but is *rejected* by the
// reference resolver; this block follows the reference.
//
// One 32x32 product is unavoidable -- ``selector_value * element_stride`` is
// the A4 term itself -- so a single multiplier is shared between the offset
// term, the A13 leading-axis test ``stride0 * bound_divisor`` and the A13
// ``iteration * bound_divisor`` product, evaluated in successive cycles.  All
// three are compared and accumulated at 64 bits, so a product that does not fit
// in 32 fails the leading-axis test rather than wrapping into passing it.  The
// block therefore has a bounded, data-independent cost and no wide arithmetic
// in the caller's control path.
// ---------------------------------------------------------------------------
module ot_a3_view_resolver
    import ot_a3_pkg::*;
(
    input  wire          clk,
    input  wire          rst_n,
    input  wire          clear,

    // The 128-byte TENSOR_VIEW payload, held stable by the caller from
    // ``start`` until ``done``.  Layout fields this block does not consume --
    // strides, trailing dims, the scale binding -- belong to an engine
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
    output reg  [31:0]   out_dim0,
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
    // stride u32}@72+8i.
    wire [7:0]  view_dtype      = payload[7:0];
    wire [7:0]  view_rank       = payload[15:8];
    wire [7:0]  view_terms      = payload[31:24];
    wire [63:0] view_offset     = payload[191:128];
    wire [31:0] view_dim0       = payload[223:192];
    // stride0 lives at payload offset 48 (Field("stride{i}", 48 + 4*i, 4)).
    // A13's leading-axis test is stated in terms of it.
    wire [31:0] view_stride0    = payload[415:384];

    assign out_rank       = view_rank;
    assign out_dtype      = view_dtype;
    assign out_term_count = view_terms;

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

    localparam [3:0] S_IDLE    = 4'd0;
    localparam [3:0] S_SELECT  = 4'd1;
    localparam [3:0] S_READ    = 4'd2;
    localparam [3:0] S_OFFSET  = 4'd3;
    localparam [3:0] S_BLOCK   = 4'd4;
    localparam [3:0] S_AXIS    = 4'd5;
    localparam [3:0] S_REMAIN  = 4'd6;
    localparam [3:0] S_FOLD    = 4'd7;
    localparam [3:0] S_FINISH  = 4'd8;

    reg [3:0]  state;
    reg [31:0] value;            // the selector's resolved value
    reg        value_is_loop;
    reg        loop_symbolic;
    reg [31:0] loop_divisor;
    reg [31:0] loop_bound;
    reg        remain_valid;     // "leading_loop is not None"
    reg [31:0] remain;           // the smallest remaining row count so far

    // -- one shared 32x32 product ------------------------------------------
    reg  [31:0] mul_a;
    reg  [31:0] mul_b;
    reg  [63:0] product;
    wire [63:0] product_w = mul_a * mul_b;

    // remaining = symbol_value - iteration * bound_divisor, evaluated wide and
    // signed so that an iteration past the extent is negative rather than
    // wrapping to a huge positive count.
    wire signed [64:0] remaining_s =
        $signed({33'd0, loop_bound}) - $signed({1'b0, product});
    wire signed [64:0] divisor_s = $signed({33'd0, loop_divisor});
    wire remaining_partial = (remaining_s > 65'sd0) && (remaining_s < divisor_s);
    wire [31:0] remaining_rows = remaining_s[31:0];

    // _indexes_leading_axis: this term walks the leading axis exactly when one
    // iteration advances by one whole block of it.  ``product_w`` holds
    // ``stride0 * bound_divisor`` while the walk is in S_AXIS; the comparison
    // is 64 bits wide on both sides so a product too large for a 32-bit stride
    // is unequal rather than truncated into equality.
    wire indexes_leading_axis = (product_w == {32'd0, term_stride});

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
            out_dim0 <= 32'd0;
            loop_query_id <= A3_NO_ID;
            sym_index <= 4'd0;
            slot <= 3'd0;
            value <= 32'd0;
            value_is_loop <= 1'b0;
            loop_symbolic <= 1'b0;
            loop_divisor <= 32'd1;
            loop_bound <= 32'd0;
            remain_valid <= 1'b0;
            remain <= 32'd0;
            mul_a <= 32'd0;
            mul_b <= 32'd0;
            product <= 64'd0;
        end else begin
            done <= 1'b0;
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
                            state <= S_SELECT;
                        end
                    end
                    // Drive the loop and symbol selects for this term; both
                    // reads are combinational and are consumed next cycle.
                    S_SELECT: begin
                        if ({5'd0, slot} >= view_terms) begin
                            state <= S_FINISH;
                        end else begin
                            loop_query_id <= {16'd0, term_index};
                            sym_index <= term_index[3:0];
                            state <= S_READ;
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
                            // Ask the leading-axis question first: this term
                            // bounds the leading extent only if it walks that
                            // axis, and the arithmetic answers it.
                            mul_a <= view_stride0;
                            mul_b <= loop_divisor;
                            state <= S_AXIS;
                        end else begin
                            slot <= slot + 3'd1;
                            state <= S_SELECT;
                        end
                    end
                    S_AXIS: begin
                        // product_w is stride0 * bound_divisor this cycle, and
                        // term_stride is still this term's own stride: the
                        // slot counter has not advanced.  A term along any
                        // other axis is not a partial final iteration of the
                        // leading one, so it contributes no bound and the walk
                        // moves on without touching ``remain``.
                        if (indexes_leading_axis) begin
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
                        state <= S_FOLD;
                    end
                    S_FOLD: begin
                        // _remaining_rows: a loop bounds the leading extent
                        // only while 0 < remaining < bound_divisor, and the
                        // smallest bound across terms wins.
                        if (remaining_partial &&
                            (!remain_valid || (remaining_rows < remain))) begin
                            remain <= remaining_rows;
                            remain_valid <= 1'b1;
                        end
                        slot <= slot + 3'd1;
                        state <= S_SELECT;
                    end
                    S_FINISH: begin
                        // resolve(): dim0 = remaining if 0 < remaining < dim0.
                        // ``dims`` is empty at rank zero, which the reference
                        // guards with ``and dims``.
                        if (remain_valid && (view_rank != 8'd0) &&
                            (remain != 32'd0) && (remain < view_dim0))
                            out_dim0 <= remain;
                        else
                            out_dim0 <= view_dim0;
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
