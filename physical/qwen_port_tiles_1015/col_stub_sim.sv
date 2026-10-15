`timescale 1ns/1ps
// Simulation-only stand-in for the CLOSED ot_qwen_slab_pg_col view in the hierarchy-equivalence bench: a registered,
// address-dependent pseudo-ROM word (identical in the old and new hierarchy, so it only exercises the wiring).
module ot_qwen_slab_pg_col #(parameter string ROM_INSTANCE = "") (
    input wire clk, input wire gre1, input wire [23:0] addr1, input wire [3:0] cid, output reg [255:0] m5);
    integer k;
    always @(posedge clk) begin
        for (k=0;k<8;k=k+1) m5[32*k +: 32] <= gre1 ? ({addr1[15:0],4'(cid),12'(k)} ^ 32'h3f80_0000) & 32'h3fff_ffff : 32'd0;
    end
endmodule
