`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DMA.FILL -- one code written across an output view.
//
// The fill code comes from one of two places and the operator must name exactly
// one: ``input_view_0``, a *one-element* view holding the code, or ``aux_id_0``
// as a raw immediate bit pattern.  An operator that declares neither is refused
// rather than filled with zero, which is the reference engine's behaviour and
// the only one that cannot silently produce a plausible-looking buffer.
//
// The immediate is checked against the output element width: the reference
// requires ``width >= 32 or immediate < (1 << width)``, so a 16-bit output may
// not be handed a 17-bit pattern.  Truncating it here would write a different
// buffer than the functional device and agree with nothing.
//
// FULLY PIPELINED, AND NOTHING MORE.  The code is fetched once (or taken as an
// immediate) and then one element is written every cycle with no read in the
// loop at all, so the initiation interval is 1 and the block never stalls.  The
// address counter is the whole datapath; there is deliberately no operand
// pipeline to drain.
// ---------------------------------------------------------------------------
module ot_a3_dma_fill (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [31:0] cfg_count,
    input  wire [31:0] cfg_out_base,
    //: The code is in a view; cfg_source_addr is that one element's address.
    input  wire        cfg_has_source,
    input  wire [31:0] cfg_source_addr,
    //: Or the code is an immediate, valid only when cfg_has_source is 0.
    input  wire        cfg_has_immediate,
    input  wire [31:0] cfg_immediate,
    //: Output element width in bits, which bounds the immediate.
    input  wire [7:0]  cfg_element_bits,

    output reg         src_rd_en,
    output reg  [31:0] src_rd_addr,
    input  wire [31:0] src_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count
);
    // Re-declared rather than wildcard-imported: Icarus 11 turns a
    // wildcard-imported name used only in a port connection into an implicit
    // net, and the pinned Yosys 0.68 frontend rejects ``import`` outright.
    localparam [7:0] ERR_NONE  = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [2:0] S_IDLE  = 3'd0;
    localparam [2:0] S_FETCH = 3'd1;
    localparam [2:0] S_WAIT  = 3'd2;
    localparam [2:0] S_WRITE = 3'd3;
    localparam [2:0] S_DONE  = 3'd4;

    reg [2:0]  state;
    reg [31:0] index;
    reg [31:0] code;
    reg [1:0]  wait_count;

    //: ``width >= 32`` admits any 32-bit pattern; below that the pattern has to
    //: fit, and a shift by 32 or more is what makes the first half necessary.
    wire immediate_fits =
        ({24'd0, cfg_element_bits} >= 32'd32) ||
        (cfg_immediate < (32'd1 << cfg_element_bits[4:0]));

    wire cfg_bad = (cfg_count == 32'd0) ||
                   (!cfg_has_source && !cfg_has_immediate) ||
                   (!cfg_has_source && !immediate_fits);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            index <= 32'd0;
            code <= 32'd0;
            wait_count <= 2'd0;
            src_rd_en <= 1'b0;
            src_rd_addr <= 32'd0;
            out_we <= 1'b0;
            out_addr <= 32'd0;
            out_data <= 32'd0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            out_count <= 32'd0;
        end else begin
            src_rd_en <= 1'b0;
            out_we <= 1'b0;
            done <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (start) begin
                        index <= 32'd0;
                        out_count <= 32'd0;
                        if (cfg_bad) begin
                            error_code <= ERR_SHAPE;
                            busy <= 1'b0;
                            done <= 1'b1;
                            state <= S_DONE;
                        end else begin
                            error_code <= ERR_NONE;
                            busy <= 1'b1;
                            if (cfg_has_source) begin
                                state <= S_FETCH;
                            end else begin
                                code <= cfg_immediate;
                                state <= S_WRITE;
                            end
                        end
                    end
                end
                S_FETCH: begin
                    src_rd_en <= 1'b1;
                    src_rd_addr <= cfg_source_addr;
                    wait_count <= 2'd0;
                    state <= S_WAIT;
                end
                // The address register sits on the port, so the one-element
                // fetch answers two cycles after S_FETCH drove it.
                S_WAIT: begin
                    if (wait_count >= 2'd1) begin
                        code <= src_rd_data;
                        state <= S_WRITE;
                    end else begin
                        wait_count <= wait_count + 2'd1;
                    end
                end
                // One element per cycle, no read in the loop.
                S_WRITE: begin
                    out_we <= 1'b1;
                    out_addr <= cfg_out_base + index;
                    out_data <= code;
                    out_count <= out_count + 32'd1;
                    if (index + 32'd1 >= cfg_count) begin
                        busy <= 1'b1;
                        state <= S_DONE;
                    end else begin
                        index <= index + 32'd1;
                    end
                end
                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
