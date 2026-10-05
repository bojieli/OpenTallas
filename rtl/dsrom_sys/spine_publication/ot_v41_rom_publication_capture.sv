`timescale 1ns/1ps
// One aligned publication edge, not a FIFO/ACK/retirement authority.
// The enclosing capture owns identity and debt until actual VM acceptance.
// rst_n must be the existing coordinated COLD fence. Warm quarantine must
// never reset this stage or the downstream retained capture records.
module ot_v41_rom_publication_capture #(
    parameter integer ENABLE = 0,
    parameter integer WIDTH = 128
)(
    input wire clk, rst_n,
    input wire [WIDTH-1:0] publication_in,
    output wire [WIDTH-1:0] publication_out
);
    generate if (ENABLE != 0) begin : g_capture
        reg [WIDTH-1:0] held;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) held <= '0;
            else held <= publication_in;
        assign publication_out = held;
    end else begin : g_original
        assign publication_out = publication_in;
    end endgenerate
endmodule
