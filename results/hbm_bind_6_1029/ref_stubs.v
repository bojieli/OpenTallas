(* blackbox *) module ot_hnx_fused_lane #(parameter integer D = 5120, parameter integer KX = 4, parameter integer RR = 10, parameter integer MUT = 0) (
  input wire clk, input wire rst_n, input wire [4:0] lid, output wire rq_v, output wire [15:0] rq_s, input wire rr_v, input wire [255:0] rr_d,
  output wire wq_v, output wire [15:0] wq_s, output wire [255:0] wq_d, input wire dn_v, input wire [2:0] dn_op, input wire [7:0] dn_x,
  input wire [127:0] dn_d, input wire r_v, input wire [31:0] r_d, output wire up_v, output wire up_t, output wire [9:0] up_x,
  output wire [255:0] up_d, output wire fin, output wire flt);
endmodule
(* blackbox *) module ot_hnx_fused_tnode #(parameter integer LA = 6, parameter integer UW = 271, parameter integer DW = 173, parameter integer DELIVERED_RESET = 0) (
  input wire clk, input wire rst_n, input wire [5:0] pad_k, input wire pad_b, input wire [UW-1:0] ua, input wire [UW-1:0] ub,
  output wire [UW-1:0] uo, input wire [DW-1:0] dn, output wire [DW-1:0] da, output wire [DW-1:0] db);
endmodule
(* blackbox *) module ot_hnx_fused_hub #(parameter integer D = 5120, parameter integer RR = 10, parameter integer NMAX = 8, parameter integer MUT = 0,
  parameter integer UW = 271, parameter integer DW = 173, parameter integer N4EXT = 0, parameter integer DELIVERED_RESET = 0) (
  input wire clk, input wire rst_n, input wire job_v, input wire [216:0] job, output wire done, output wire fault, output wire busy,
  input wire [7:0] wsc, input wire [5:0] pk4a, input wire [5:0] pk4b, input wire [5:0] pk5, input wire pb4a, input wire pb4b, input wire pb5,
  input wire [UW-1:0] uq0, input wire [UW-1:0] uq1, input wire [UW-1:0] uq2, input wire [UW-1:0] uq3,
  output wire [DW-1:0] dq0, output wire [DW-1:0] dq1, output wire [DW-1:0] dq2, output wire [DW-1:0] dq3);
endmodule
(* blackbox *) module ot_hdc_delay #(parameter integer W = 1, parameter integer D = 1, parameter integer RESET = 0) (
  input wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
endmodule
