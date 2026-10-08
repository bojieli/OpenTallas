// Black-box declaration only; missing or unqualified LEF/LIB forbids routing.
(* blackbox *) module qfd_embed_ingress_scale(
 input clk,rst_n,input [17:0] address,input valid,credit,
 output [17:0] address_q,address_n,output valid_q,valid_n,credit_q,credit_n);
endmodule
