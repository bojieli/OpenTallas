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
// ``stride[a] * step``, the ``iteration * bound_divisor`` product and the
// bounding-range products below, evaluated in successive cycles.  All of them
// are compared and accumulated at 64 bits, so a product that does not fit in
// 32 fails the axis test rather than wrapping into passing it.  The two
// divisions by ``u`` go to the front end's one shared divider
// (ot_a3_shared_divider; docs/CHIP_ARCHITECTURE_DESIGN.md section 3.5) through
// the div_* request port; a numerator and unit of one -- every view written
// before A18 -- bypasses it entirely, so the A13 path costs exactly the cycles
// it always did.  The block therefore has a bounded, data-independent cost and
// no wide arithmetic in the caller's control path.
//
// This block is one lane of the six-lane resolver bank (ot_a3_resolver_bank,
// section 3.5).  Two things are new with the asynchronous front end:
//
//   * the symbol file is 64 bits wide (section 3.3).  A RUNTIME_SYMBOL term
//     multiplies the low word first and, only when the high word is nonzero,
//     takes a second pass on the same multiplier for ``(hi * stride) << 32``;
//     every shipped binding fits 32 bits, so the second pass is never taken
//     on a shipped program and the offset arithmetic is what it always was;
//
//   * a B stage after the extent (section 3.5 "B"): the bounding byte range
//     of the resolved view for the dependence table (section 3.6), computed
//     in *bits* so MXFP4's half-byte elements round outward -- lo =
//     floor(offset x bits / 8), hi = ceil((offset x bits + span) / 8) with
//     span = sum_i (dim_i - 1) x stride_i x bits + bits over the resolved
//     dims (the clamped axis included), strides as the unsigned fields they
//     are, and a range that does not fit 40 bits widened to the whole object
//     rather than truncated.  The object is the descriptor header's
//     primary_object_id and the write bit its WRITE permission; the scale
//     object (payload byte 4) is reported beside it so the caller can enter
//     it as a whole-object read range.  Conservative by construction: the
//     range is never narrower than the bytes the engine may touch.
// ---------------------------------------------------------------------------
module ot_a3_view_resolver
    // The package is referenced by scope rather than wildcard-imported: a
    // wildcard import is not accepted by every open synthesis front end this
    // program pins, and a block that only elaborates in a simulator is not an
    // implementable block.  [OI-43] docs/UNIFIED_EXECUTION_CHECKLIST.md
#(
    // FAST_WALK (measured, not asserted).  A per-state census of the Qwen ROM
    // deployment (Icarus, case 0: 2,143 views, 2,240 dynamic terms, mean rank
    // 2.18) charged this block 31,097 cycles, 14.51 per view.  Two of its
    // states did no arithmetic:
    //
    //   * S_SELECT, 4,383 cycles -- one per term plus one per view to notice
    //     the terms were finished.  All it did was drive the loop-stack and
    //     symbol selects, which the state that advances the slot already knows
    //     one cycle earlier: the payload is held from start to done, so the
    //     *next* term's index is readable from the same registered payload
    //     through a second mux.  FAST_WALK drives them there and folds the
    //     terms-exhausted decision in with them.
    //   * the bounding walk's fill, 4,674 - 2,143 = 2,531 cycles -- S_BOUND_MUL
    //     presented (dim_i - 1, stride_i) and S_BOUND_ACC accumulated the
    //     product a cycle later, two cycles for each of 2.18 axes.  The
    //     accumulate of axis i and the operand presentation of axis i + 1 are
    //     two *parallel* paths from two different registers, not one path in
    //     series, so FAST_WALK does both in one cycle and pays a single fill
    //     cycle per view instead of one per axis.
    //
    // Neither change puts new logic in series: no product feeds an adder or a
    // comparator it did not already feed, and no arithmetic result is consumed
    // in the cycle it is produced that was not already.  What is added is a
    // second copy of the term-index mux (16 bits, selected by slot + 1) and a
    // second copy of the dim/stride mux (selected by b_axis + 1), each of which
    // is the same depth as the copy it sits beside.  The 32x32 product, the
    // 64-bit compare in S_AXIS and the 70-bit span accumulate are untouched.
    //
    // 0 restores the walk exactly as it shipped, and is the default, so a
    // build that does not name the parameter is the block as it shipped.  Both
    // builds are driven from one stimulus by
    // rtl/test/tb_a3_resolver_bank_equiv.sv, and the 0 build is driven against
    // a verbatim copy of the shipped source by
    // rtl/test/tb_a3_resolver_bank_inert.sv.
    //
    // This default decides NOTHING in the shipped hierarchy.  Every lane is
    // instantiated by ot_a3_resolver_bank, which passes its own FAST_WALK
    // down, so an override there wins over this line.  Editing this default on
    // its own to turn the optimisation off is a no-op, and reading a cycle
    // count from a build made that way is how this change was once measured
    // "not inert" when the residual was simply this parameter still on.  Set
    // it from the top: a3_microsequencer_top -> ot_a3_device_top ->
    // ot_a3_microsequencer -> ot_a3_resolver_bank.
    parameter integer FAST_WALK = 0
) (
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
    // Descriptor header fields the B stage reports: primary_object_id (byte
    // 16) and permissions (byte 32).
    input  wire [31:0]   object_id,
    input  wire [31:0]   permissions,

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

    // B stage: the bounding byte range for the dependence table.
    output wire [15:0]   out_object,
    output wire          out_write,
    output reg  [39:0]   out_lo,
    output reg  [39:0]   out_hi,
    output wire [31:0]   out_scale_object,
    output wire          out_scale_valid,

    // Loop stack query port (combinational).
    output reg  [31:0]   loop_query_id,
    input  wire          loop_query_active,
    input  wire [31:0]   loop_query_value,
    input  wire          loop_query_symbol_bounded,
    input  wire [31:0]   loop_query_divisor,
    input  wire [31:0]   loop_query_bound_value,

    // Runtime symbol file (combinational, 64-bit).
    output reg  [3:0]    sym_index,
    input  wire [63:0]   sym_value,
    input  wire          sym_bound,

    // Shared divider request port.
    output reg           div_req,
    output reg  [63:0]   div_num,
    output reg  [31:0]   div_den,
    input  wire          div_done,
    input  wire [63:0]   div_quot,
    input  wire [63:0]   div_rem
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

    wire [31:0] view_scale_object = payload[63:32];

    assign out_rank        = view_rank;
    assign out_dtype       = view_dtype;
    assign out_term_count  = view_terms;
    assign out_extent_axis = view_extent_axis;
    assign out_object      = object_id[15:0];
    assign out_write       = permissions[1];     // Permission.WRITE
    assign out_scale_object = view_scale_object;
    assign out_scale_valid  = (view_scale_object != ot_a3_pkg::A3_NO_ID);

    // dim[i] and stride[i] for the bounding-range walk (B stage).
    reg [2:0]  b_axis;
    reg [31:0] b_dim;
    reg [31:0] b_stride;
    always @* begin
        case (b_axis)
            3'd0: begin b_dim = payload[223:192]; b_stride = payload[415:384]; end
            3'd1: begin b_dim = payload[255:224]; b_stride = payload[447:416]; end
            3'd2: begin b_dim = payload[287:256]; b_stride = payload[479:448]; end
            3'd3: begin b_dim = payload[319:288]; b_stride = payload[511:480]; end
            3'd4: begin b_dim = payload[351:320]; b_stride = payload[543:512]; end
            default: begin b_dim = payload[383:352]; b_stride = payload[575:544]; end
        endcase
    end
    wire [31:0] b_dim_resolved = ({5'd0, b_axis} == view_extent_axis) ? out_extent : b_dim;
    // FAST_WALK presents axis i + 1's operands in the cycle that accumulates
    // axis i's product, so it needs the same two fields one axis ahead.  This
    // is a second copy of the mux above, selected by b_axis + 1: the same
    // depth from the same registered payload, not a longer path.
    wire [2:0]  b_axis_next = b_axis + 3'd1;
    reg [31:0]  b_dim_n;
    reg [31:0]  b_stride_n;
    always @* begin
        case (b_axis_next)
            3'd0: begin b_dim_n = payload[223:192]; b_stride_n = payload[415:384]; end
            3'd1: begin b_dim_n = payload[255:224]; b_stride_n = payload[447:416]; end
            3'd2: begin b_dim_n = payload[287:256]; b_stride_n = payload[479:448]; end
            3'd3: begin b_dim_n = payload[319:288]; b_stride_n = payload[511:480]; end
            3'd4: begin b_dim_n = payload[351:320]; b_stride_n = payload[543:512]; end
            default: begin b_dim_n = payload[383:352]; b_stride_n = payload[575:544]; end
        endcase
    end
    wire [31:0] b_dim_resolved_n =
        ({5'd0, b_axis_next} == view_extent_axis) ? out_extent : b_dim_n;
    wire [6:0]  b_bits = ot_a3_pkg::a3_dtype_bits(view_dtype);
    // log2(bits): 4 -> 2, 8 -> 3, 16 -> 4, 32 -> 5, 64 -> 6
    wire [2:0]  b_shift = (b_bits == 7'd4)  ? 3'd2 :
                          (b_bits == 7'd8)  ? 3'd3 :
                          (b_bits == 7'd16) ? 3'd4 :
                          (b_bits == 7'd32) ? 3'd5 : 3'd6;
    reg  [69:0] b_span;              // sum (dim_i - 1) * stride_i, elements
    wire [69:0] b_lo_bits   = {6'd0, out_element_offset} << b_shift;
    wire [69:0] b_span_bits = (b_span + 70'd1) << b_shift;
    wire [69:0] b_hi_bits   = b_lo_bits + b_span_bits + 70'd7;
    wire [66:0] b_lo_bytes  = b_lo_bits[69:3];
    wire [66:0] b_hi_bytes  = b_hi_bits[69:3];
    wire        b_overflow  = (b_lo_bytes[66:40] != 27'd0) || (b_hi_bytes[66:40] != 27'd0);

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

    // FAST_WALK drives the loop-stack and symbol selects for term ``slot + 1``
    // from the state that advances the slot, so it reads that term's index a
    // cycle early through a second copy of the mux above.  Only the index is
    // needed early; the kind and the stride are still read at ``slot``, which
    // by then names the term being read.
    wire [2:0] slot_next = slot + 3'd1;
    reg [15:0] term_index_n;
    always @* begin
        case (slot_next)
            3'd0:    term_index_n = payload[607:592];
            3'd1:    term_index_n = payload[671:656];
            3'd2:    term_index_n = payload[735:720];
            default: term_index_n = payload[799:784];
        endcase
    end
    wire [15:0] term_index_0 = payload[607:592];
    // ``slot`` has not advanced yet when this is evaluated, so the test is the
    // one S_SELECT would make on the next cycle's counter, unchanged.
    wire       terms_done_next = ({5'd0, slot_next} >= view_terms);
    wire       terms_done_zero = (view_terms == 8'd0);
    wire       edge_pending    = (view_edge_mask != ot_a3_pkg::A3_NO_ID);

    // Any non-zero parameter selects the fast build, so an instantiation that
    // passes 2 does not silently get the slow one.
    localparam FAST_WALK_ON = (FAST_WALK != 0);

    localparam [4:0] S_IDLE      = 5'd0;
    localparam [4:0] S_SELECT    = 5'd1;
    localparam [4:0] S_READ      = 5'd2;
    localparam [4:0] S_OFFSET    = 5'd3;
    localparam [4:0] S_BLOCK     = 5'd4;
    localparam [4:0] S_NUM_STEP  = 5'd5;
    localparam [4:0] S_DIV_STEP  = 5'd6;
    localparam [4:0] S_AXIS_MUL  = 5'd7;
    localparam [4:0] S_AXIS      = 5'd8;
    localparam [4:0] S_REMAIN    = 5'd9;
    localparam [4:0] S_SCALE     = 5'd10;
    localparam [4:0] S_NUM_EXT   = 5'd11;
    localparam [4:0] S_DIV_EXT   = 5'd12;
    localparam [4:0] S_FOLD      = 5'd13;
    localparam [4:0] S_FINISH    = 5'd14;
    localparam [4:0] S_EDGE_READ = 5'd15;
    localparam [4:0] S_OFFSET_HI = 5'd16;
    localparam [4:0] S_BOUND_MUL = 5'd17;
    localparam [4:0] S_BOUND_ACC = 5'd18;
    localparam [4:0] S_BOUND_END = 5'd19;

    reg [4:0]  state;
    reg [31:0] sym_hi;           // high word of a RUNTIME_SYMBOL value
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

    // FAST_WALK: leave one term for the next, driving that term's loop-stack
    // and symbol selects in the same cycle.  This is S_SELECT's entire body,
    // executed one state earlier by the state that already knows the slot is
    // advancing; the terms-exhausted test is the same comparison against the
    // same counter value, one cycle sooner.
    task advance_term;
        begin
            slot <= slot + 3'd1;
            if (terms_done_next) begin
                if (!edge_done && edge_pending) begin
                    loop_query_id <= view_edge_mask;
                    edge_phase <= 1'b1;
                    state <= S_EDGE_READ;
                end else begin
                    state <= S_FINISH;
                end
            end else begin
                edge_phase <= 1'b0;
                loop_query_id <= {16'd0, term_index_n};
                sym_index <= term_index_n[3:0];
                state <= S_READ;
            end
        end
    endtask

    task fail_closed;
        input [15:0] class_value;
        begin
            busy <= 1'b0;
            done <= 1'b1;
            fault <= 1'b1;
            trap_class <= class_value;
            div_req <= 1'b0;
            state <= S_IDLE;
        end
    endtask

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            fault <= 1'b0;
            trap_class <= ot_a3_pkg::A3_TRAP_NONE;
            out_element_offset <= 64'd0;
            out_extent <= 32'd0;
            loop_query_id <= ot_a3_pkg::A3_NO_ID;
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
            div_req <= 1'b0;
            div_num <= 64'd0;
            div_den <= 32'd1;
            sym_hi <= 32'd0;
            b_axis <= 3'd0;
            b_span <= 70'd0;
            out_lo <= 40'd0;
            out_hi <= 40'd0;
        end else begin
            done <= 1'b0;
            if (clear) begin
                state <= S_IDLE;
                busy <= 1'b0;
                fault <= 1'b0;
                div_req <= 1'b0;
            end else begin
                case (state)
                    S_IDLE: begin
                        if (start) begin
                            busy <= 1'b1;
                            fault <= 1'b0;
                            trap_class <= ot_a3_pkg::A3_TRAP_NONE;
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
                                (view_extent_axis >= view_rank)) begin
                                fail_closed(ot_a3_pkg::A3_TRAP_MEMORY);
                            end else if (FAST_WALK_ON) begin
                                // What S_SELECT would decide next cycle, made
                                // now: term zero's index is a fixed slice of
                                // the payload, so no mux is even needed.
                                if (terms_done_zero) begin
                                    if (edge_pending) begin
                                        loop_query_id <= view_edge_mask;
                                        edge_phase <= 1'b1;
                                        state <= S_EDGE_READ;
                                    end else begin
                                        state <= S_FINISH;
                                    end
                                end else begin
                                    loop_query_id <= {16'd0, term_index_0};
                                    sym_index <= term_index_0[3:0];
                                    state <= S_READ;
                                end
                            end else begin
                                state <= S_SELECT;
                            end
                        end
                    end
                    // Drive the loop and symbol selects for this term; both
                    // reads are combinational and are consumed next cycle.
                    S_SELECT: begin
                        if ({5'd0, slot} >= view_terms) begin
                            if (!edge_done && (view_edge_mask != ot_a3_pkg::A3_NO_ID)) begin
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
                            fail_closed(ot_a3_pkg::A3_TRAP_MEMORY);
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
                                // The terms are finished and the edge mask is
                                // the last thing a view carries, so S_SELECT
                                // had nothing left to decide.
                                state <= FAST_WALK_ON ? S_FINISH : S_SELECT;
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
                        if (term_kind == {8'd0, ot_a3_pkg::A3_SELECTOR_LOOP_INDUCTION}) begin
                            if (!loop_query_active) begin
                                // "view N: loop M is not active"
                                fail_closed(ot_a3_pkg::A3_TRAP_MEMORY);
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
                                     {8'd0, ot_a3_pkg::A3_SELECTOR_RUNTIME_SYMBOL}) begin
                            if (({16'd0, term_index} >= ot_a3_pkg::A3_SYMBOL_COUNT) ||
                                !sym_bound) begin
                                // "view N: symbol S is unbound"
                                fail_closed(ot_a3_pkg::A3_TRAP_MEMORY);
                            end else begin
                                value <= sym_value[31:0];
                                value_is_loop <= 1'b0;
                                sym_hi <= sym_value[63:32];
                                mul_a <= sym_value[31:0];
                                mul_b <= term_stride;
                                state <= S_OFFSET;
                            end
                        end else begin
                            // "view N: bad selector kind K".  CONSTANT lands
                            // here, exactly as the reference resolver does.
                            fail_closed(ot_a3_pkg::A3_TRAP_MEMORY);
                        end
                    end
                    S_OFFSET: begin
                        product <= product_w;
                        if (!value_is_loop && (sym_hi != 32'd0)) begin
                            // Second pass for a symbol above 2^32: the high
                            // word's product lands 32 bits up.
                            mul_a <= sym_hi;
                            state <= S_OFFSET_HI;
                        end else begin
                            state <= S_BLOCK;
                        end
                    end
                    S_OFFSET_HI: begin
                        out_element_offset <= out_element_offset + product;
                        product <= {product_w[31:0], 32'd0};
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
                        end else if (FAST_WALK_ON) begin
                            advance_term;
                        end else begin
                            slot <= slot + 3'd1;
                            state <= S_SELECT;
                        end
                    end
                    S_NUM_STEP: begin
                        // product_w is numerator * bound_divisor this cycle.
                        div_req <= 1'b1;
                        div_num <= product_w;
                        div_den <= view_unit;
                        state <= S_DIV_STEP;
                    end
                    S_DIV_STEP: begin
                        if (div_done) begin
                            div_req <= 1'b0;
                            axis_step <= div_quot;
                            // A unit that does not divide ``n * d`` means one
                            // iteration is not a whole number of this axis's
                            // elements, so the term walks nothing.
                            unit_divides <= (div_rem == 64'd0);
                            if (edge_phase) begin
                                if (div_rem == 64'd0) begin
                                    mul_a <= value;
                                    mul_b <= loop_divisor;
                                    state <= S_REMAIN;
                                end else begin
                                    // iteration_extent() is undefined: no
                                    // clamp, matching _remaining_extent.
                                    state <= FAST_WALK_ON ? S_FINISH : S_SELECT;
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
                        end else if (FAST_WALK_ON) begin
                            advance_term;
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
                            if (FAST_WALK_ON) begin
                                advance_term;
                            end else begin
                                slot <= slot + 3'd1;
                                state <= S_SELECT;
                            end
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
                        div_req <= 1'b1;
                        div_num <= product_w;
                        div_den <= view_unit;
                        state <= S_DIV_EXT;
                    end
                    S_DIV_EXT: begin
                        if (div_done) begin
                            div_req <= 1'b0;
                            // The bias is added after the division, because it
                            // is a count the operand carries whatever the
                            // request is rather than a scaling of it.
                            axis_extent <= div_quot + {32'd0, view_bias};
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
                        if (FAST_WALK_ON) begin
                            // After the edge phase the terms are finished and
                            // edge_done is set, which is the only thing
                            // S_SELECT would have looked at.
                            if (!edge_phase) advance_term;
                            else             state <= S_FINISH;
                        end else begin
                            if (!edge_phase)
                                slot <= slot + 3'd1;
                            state <= S_SELECT;
                        end
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
                        b_axis <= 3'd0;
                        b_span <= 70'd0;
                        if (view_rank == 8'd0)
                            state <= S_BOUND_END;
                        else
                            state <= S_BOUND_MUL;
                    end
                    // -- B stage: bounding byte range ----------------------
                    S_BOUND_MUL: begin
                        // (dim_i - 1) * stride_i for the resolved dims; an
                        // empty axis contributes nothing.
                        mul_a <= (b_dim_resolved == 32'd0) ? 32'd0
                                                           : (b_dim_resolved - 32'd1);
                        mul_b <= b_stride;
                        state <= S_BOUND_ACC;
                    end
                    S_BOUND_ACC: begin
                        b_span <= b_span + {6'd0, product_w};
                        if ({5'd0, b_axis} + 8'd1 >= view_rank) begin
                            state <= S_BOUND_END;
                        end else if (FAST_WALK_ON) begin
                            // Accumulate axis i and present axis i + 1 in the
                            // same cycle.  The accumulate reads the product of
                            // operands registered last cycle and the
                            // presentation reads the payload: two paths from
                            // two registers, in parallel, neither feeding the
                            // other.  S_BOUND_MUL stays as the one fill cycle.
                            b_axis <= b_axis_next;
                            mul_a <= (b_dim_resolved_n == 32'd0)
                                     ? 32'd0 : (b_dim_resolved_n - 32'd1);
                            mul_b <= b_stride_n;
                            state <= S_BOUND_ACC;
                        end else begin
                            b_axis <= b_axis + 3'd1;
                            state <= S_BOUND_MUL;
                        end
                    end
                    S_BOUND_END: begin
                        if (b_overflow) begin
                            out_lo <= 40'd0;
                            out_hi <= {40{1'b1}};
                        end else begin
                            out_lo <= b_lo_bytes[39:0];
                            out_hi <= b_hi_bytes[39:0];
                        end
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
