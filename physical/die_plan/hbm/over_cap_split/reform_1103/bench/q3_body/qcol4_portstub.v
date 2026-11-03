// Port-only stub of ot_hfd_coll_q3_qcol4 for facewrap.py (its yosys JSON read rejects always blocks); bench input only.
module ot_hfd_coll_q3_qcol4 #(parameter integer MUT = 0) (input wire clk, input wire [63:0] sel,
    input wire [4*11*32-1:0] src, output wire [4*16*32-1:0] dst);
    assign dst = {src[639:0], src} ^ {2048{clk & sel[0]}};   // non-empty so yosys keeps it (not a blackbox)
endmodule
