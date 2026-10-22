// Exact hard interfaces from the Col8 source wrappers. Bodies supplied by explicit hard views.
`default_nettype none
(* blackbox *) module ot_hidx_score_pair8_r0(input wire clk,rst_n,qv_b,input wire [567:0] q_b,
 input wire [543:0] key,input wire [15:0] hid,
 output wire [31:0] cs_out,output wire cf_out,output wire prdy);
endmodule
(* blackbox *) module ot_hidx_score_pair8_r1(input wire clk,rst_n,qv_b,input wire [567:0] q_b,
 input wire [543:0] key,input wire [15:0] hid,input wire [31:0] cs_in,input wire cf_in,
 output wire [31:0] cs_out,output wire cf_out,output wire prdy);
endmodule
(* blackbox *) module ot_hidx_score_pair8_r2(input wire clk,rst_n,qv_b,input wire [567:0] q_b,
 input wire [543:0] key,input wire [15:0] hid,input wire [31:0] cs_in,input wire cf_in,
 output wire [31:0] cs_out,output wire cf_out,output wire prdy);
endmodule
(* blackbox *) module ot_hidx_score_pair8_r3(input wire clk,rst_n,qv_b,input wire [567:0] q_b,
 input wire [543:0] key,input wire [15:0] hid,input wire [31:0] cs_in,input wire cf_in,
 output wire [31:0] cs_out,output wire cf_out,output wire prdy);
endmodule
`default_nettype wire
