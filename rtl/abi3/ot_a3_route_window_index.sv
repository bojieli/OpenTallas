`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ROUTE.WINDOW_INDEX -- the visible KV rows ending at each query position.
//
// ``input_view_0`` is U32 absolute query positions [span]; ``output_view_0`` is
// U32 [span, slots] of the visible rows ending at each query, tail-padded with
// 0xffffffff.  ``aux_id_0`` is the window (absent means the output extent),
// ``aux_id_1`` the mask mode and ``aux_id_2`` the runtime symbol bounding the
// context, whose value the caller passes in ``cfg_context``.
//
// In PREFILL the emitted rows are absolute indices into the current request's KV
// tensor.  In DECODE they are physical slots of the circular window, so each is
// taken modulo the window, in causal oldest-to-newest order.
//
// THE MODULO IS A MASK, AND A WINDOW THAT WOULD NEED MORE IS REFUSED.  Every
// shipped instance has window 128 -- 4 instructions in deepseek-v4-flash-rom and
// 16 in deepseek-v41-flash-rom-wafer-2, all of them [262144, 128] causal -- so
// the circular wrap is ``& (window - 1)``.  A window that is not a power of two
// would need an integer modulo of an absolute position, which this block does not
// carry and no deployment asks for, so it is refused rather than approximated.
//
// NO DIVIDER AND NO MODULO IN THE WALK.  The first emitted row's wrapped value is
// masked once per query row and the rest follow by incrementing a counter that
// wraps at the window, so the per-element path is an increment and a compare.
//
// FULLY PIPELINED.  One output element per cycle across the whole [span, slots]
// output, pads included: the position read is registered, the write is registered
// behind it, and the walk never stalls between rows.
// ---------------------------------------------------------------------------
module ot_a3_route_window_index (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [31:0] cfg_span,
    input  wire [31:0] cfg_slots,
    input  wire [31:0] cfg_window,
    //: 0 causal, 1 full -- amendment's aux_id_1.
    input  wire        cfg_mask_full,
    //: Symbol.CONTEXT_LENGTH's binding; aux_id_2 names it and it is mandatory.
    input  wire [31:0] cfg_context,
    //: 1 while the request is a decode step, so the rows are circular slots.
    input  wire        cfg_decode,
    input  wire [31:0] cfg_pos_base,
    input  wire [31:0] cfg_out_base,

    output reg         pos_rd_en,
    output reg  [31:0] pos_rd_addr,
    input  wire [31:0] pos_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    output reg  [31:0] candidates
);
    // Re-declared rather than wildcard-imported: Icarus 11 turns a
    // wildcard-imported name used only in a port connection into an implicit
    // net, and the pinned Yosys 0.68 frontend rejects ``import`` outright.
    localparam [7:0] ERR_NONE        = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_INDEX_RANGE = ot_a3_engine_pkg::ERR_INDEX_RANGE;
    localparam [7:0] ERR_SHAPE       = ot_a3_engine_pkg::ERR_SHAPE;
    localparam [31:0] PAD_INDEX      = 32'hffff_ffff;

    localparam [2:0] S_IDLE  = 3'd0;
    localparam [2:0] S_POS   = 3'd1;   //: this row's position is in flight
    localparam [2:0] S_SETUP = 3'd2;
    localparam [2:0] S_EMIT  = 3'd3;
    localparam [2:0] S_NEXT  = 3'd4;
    localparam [2:0] S_DRAIN = 3'd5;
    localparam [2:0] S_DONE  = 3'd6;

    reg [2:0]  state;
    reg [31:0] row;
    reg [31:0] slot;            //: which of cfg_slots this row is filling
    reg [31:0] count;           //: how many real rows this query sees
    reg [31:0] value;           //: the next emitted row, already wrapped
    reg [31:0] out_cursor;
    reg [1:0]  tail;
    reg [31:0] drain;

    //: The position read is registered, so it answers two cycles after its
    //: address; ``tail`` waits exactly that long.  Checking a stage earlier or
    //: later is the off-by-one this session hit three times on operand ports.
    wire [31:0] position = pos_rd_data;
    wire [31:0] last_row = cfg_mask_full ? (cfg_context - 32'd1) : position;
    wire        has_full_window = (last_row + 32'd1) >= cfg_window;
    wire [31:0] first_row = has_full_window ? (last_row - cfg_window + 32'd1)
                                            : 32'd0;
    wire [31:0] window_mask = cfg_window - 32'd1;

    //: A power-of-two window has exactly one bit set, so ``w & (w-1)`` is zero.
    wire window_is_pow2 = ((cfg_window & window_mask) == 32'd0);
    wire cfg_bad = (cfg_span == 32'd0) || (cfg_slots == 32'd0) ||
                   (cfg_window == 32'd0) || (cfg_window > cfg_slots) ||
                   (cfg_context == 32'd0) ||
                   //: The circular wrap is a mask, so decode needs a power of
                   //: two.  Prefill emits absolute rows and never wraps.
                   (cfg_decode && !window_is_pow2);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            row <= 32'd0; slot <= 32'd0; count <= 32'd0; value <= 32'd0;
            out_cursor <= 32'd0; tail <= 2'd0; drain <= 32'd0;
            pos_rd_en <= 1'b0; pos_rd_addr <= 32'd0;
            out_we <= 1'b0; out_addr <= 32'd0; out_data <= 32'd0;
            busy <= 1'b0; done <= 1'b0; error_code <= ERR_NONE;
            out_count <= 32'd0; candidates <= 32'd0;
        end else begin
            pos_rd_en <= 1'b0;
            out_we <= 1'b0;
            done <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (start) begin
                        row <= 32'd0; slot <= 32'd0; out_cursor <= 32'd0;
                        out_count <= 32'd0; candidates <= 32'd0;
                        tail <= 2'd0; drain <= 32'd0;
                        if (cfg_bad) begin
                            error_code <= ERR_SHAPE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            error_code <= ERR_NONE;
                            busy <= 1'b1; state <= S_POS;
                        end
                    end
                end
                S_POS: begin
                    pos_rd_en <= 1'b1;
                    pos_rd_addr <= cfg_pos_base + row;
                    tail <= 2'd0;
                    state <= S_SETUP;
                end
                S_SETUP: begin
                    if (tail >= 2'd2) begin
                        //: A query outside the visible context is a fault, not a
                        //: clamp: the row it would emit does not exist.
                        if (position >= cfg_context) begin
                            error_code <= ERR_INDEX_RANGE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            count <= last_row - first_row + 32'd1;
                            //: Wrapped ONCE here; the walk then increments.
                            value <= cfg_decode ? (first_row & window_mask)
                                                : first_row;
                            slot <= 32'd0;
                            state <= S_EMIT;
                        end
                    end else begin
                        tail <= tail + 2'd1;
                    end
                end
                S_EMIT: begin
                    out_we <= 1'b1;
                    out_addr <= cfg_out_base + out_cursor;
                    out_cursor <= out_cursor + 32'd1;
                    out_count <= out_count + 32'd1;
                    if (slot < count) begin
                        out_data <= value;
                        candidates <= candidates + 32'd1;
                        //: Increment and wrap, rather than a second modulo.
                        value <= cfg_decode ? ((value + 32'd1) & window_mask)
                                            : (value + 32'd1);
                    end else begin
                        out_data <= PAD_INDEX;
                    end
                    if (slot + 32'd1 >= cfg_slots)
                        state <= S_NEXT;
                    else
                        slot <= slot + 32'd1;
                end
                S_NEXT: begin
                    if (row + 32'd1 >= cfg_span) begin
                        drain <= 32'd0;
                        state <= S_DRAIN;
                    end else begin
                        row <= row + 32'd1;
                        state <= S_POS;
                    end
                end
                S_DRAIN: begin
                    busy <= 1'b1;
                    if (drain >= 32'd1) state <= S_DONE;
                    else drain <= drain + 32'd1;
                end
                S_DONE: begin
                    busy <= 1'b0; done <= 1'b1; state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
