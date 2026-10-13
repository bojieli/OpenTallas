// Parent synthesis uses this only after verified leaf views exist.
(* blackbox *) module ot_qkh_recip_leaf (
 input wire clk, rst_n, v,
 input wire [31:0] x,
 output wire [31:0] y,
 output wire vo, fault
);
endmodule
