`timescale 1ns/1ps
// One ROM-column half of an existing north/south RQR register. Fixed 512 bits;
// four independent hard leaves replace gs_q[1023:0]/gn_q[1023:0], one edge unchanged.
module ot_qwen_tile_rqr_half (
    input wire clk,
    input wire [511:0] d,
    output wire [511:0] q
);
    (* keep *) reg [511:0] word_q;
    always @(posedge clk) word_q<=d;
    assign q=word_q;
endmodule
