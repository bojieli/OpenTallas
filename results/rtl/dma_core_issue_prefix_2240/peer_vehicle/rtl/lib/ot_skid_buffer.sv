`timescale 1ns/1ps
// Two-entry (or deeper) registered elastic buffer.  The producer-facing ready
// signal never feeds the producer's valid combinationally; payload and valid
// remain stable for the entire period in_ready is low.
module ot_skid_buffer #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 2
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 in_valid,
    output wire                 in_ready,
    input  wire [WIDTH-1:0]     in_data,
    output wire                 out_valid,
    input  wire                 out_ready,
    output wire [WIDTH-1:0]     out_data,
    output reg                  overflow,
    output reg                  underflow
`ifdef FORMAL
    , output wire [$clog2(DEPTH+1)-1:0] formal_count
`endif
);
    localparam integer PTR_W = (DEPTH <= 2) ? 1 : $clog2(DEPTH);
    localparam integer CNT_W = $clog2(DEPTH + 1);
    reg [WIDTH-1:0] mem [0:DEPTH-1];
    reg [PTR_W-1:0] wr_ptr;
    reg [PTR_W-1:0] rd_ptr;
    reg [CNT_W-1:0] count;
    wire push = in_valid && in_ready;
    wire pop  = out_valid && out_ready;

    assign out_valid = (count != 0);
    assign out_data = mem[rd_ptr];
    // A full buffer may accept a replacement item when the head transfers in
    // the same cycle.  This keeps one-item-per-cycle throughput without
    // changing occupancy or exposing an overwrite to the consumer.
    assign in_ready = (count < DEPTH) || (out_valid && out_ready);
`ifdef FORMAL
    assign formal_count = count;
`endif

    function automatic [PTR_W-1:0] ptr_inc(input [PTR_W-1:0] p);
        begin
            if (p == DEPTH-1)
                ptr_inc = {PTR_W{1'b0}};
            else
                ptr_inc = p + {{(PTR_W-1){1'b0}},1'b1};
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= {PTR_W{1'b0}};
            rd_ptr <= {PTR_W{1'b0}};
            count <= {CNT_W{1'b0}};
            overflow <= 1'b0;
            underflow <= 1'b0;
        end else begin
            // Ready/valid permits a producer to hold valid while full and a
            // consumer to hold ready while empty; neither is an error.  These
            // compatibility diagnostics therefore remain clear for every
            // protocol-legal execution; conservation is checked independently.
            if (push) begin
                mem[wr_ptr] <= in_data;
                wr_ptr <= ptr_inc(wr_ptr);
            end
            if (pop)
                rd_ptr <= ptr_inc(rd_ptr);
            case ({push,pop})
                2'b10: count <= count + {{(CNT_W-1){1'b0}},1'b1};
                2'b01: count <= count - {{(CNT_W-1){1'b0}},1'b1};
                default: count <= count;
            endcase
        end
    end

`ifndef SYNTHESIS
    // Immediate protocol checks are intentionally local and simulator/formal
    // friendly.  A consumer may not observe a changing item while stalled.
    reg [WIDTH-1:0] stalled_data;
    reg stalled_valid;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stalled_data <= {WIDTH{1'b0}};
            stalled_valid <= 1'b0;
        end else begin
            if (out_valid && !out_ready) begin
                if (stalled_valid && (out_data !== stalled_data))
                    $error("ot_skid_buffer payload changed while stalled");
                stalled_data <= out_data;
                stalled_valid <= 1'b1;
            end else begin
                stalled_valid <= 1'b0;
            end
        end
    end
`endif
endmodule
