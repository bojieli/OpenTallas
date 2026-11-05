// RF-H estimate-only wrapper: ot_v41_bf16_half at the ot_v41_bf_col3 production parameters (TRW = HTG = 7)
module est_h (input clk, rst_c, ze_c, v, input [127:0] w, x, input [12:0] t, output ov, oerr, fault, output [31:0] oval, output [7:0] otag);
    ot_v41_bf16_half #(.NCHB(8), .GRADUAL_RNE(1), .TRW(7), .RC(1), .TNODE(1), .RNECUT(1)) u (.*);
endmodule
