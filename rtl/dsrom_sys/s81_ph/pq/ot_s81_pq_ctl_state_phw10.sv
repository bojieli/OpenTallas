`timescale 1ns/1ps
`default_nettype none
module ot_s81_pq_ctl_state_phw10 (
 input wire clk,
 input wire rst_n,
 output wire q_consume,
 output wire b_consume,
 output wire aq_vin,
 input wire [1:0] aqf,
 output wire [9:0] aqi_o,
 output wire ba_v_o,
 output reg [1:0] ba_wv_o,
 output wire [7:0] ba_blk_o,
 output wire [47:0] hw_o,
 output wire [35:0] h_hi_o,
 output wire [15:0] h_b0_o,
 output wire [15:0] h_b1_o,
 output wire [457:0] mdr_o,
 input wire [11:0] q2f_i,
 input wire [191:0] ga_i,
 output wire [609:0] bc_hr_o,
 input wire calendar_v,input wire[74:0] calendar_action,
 input wire go,
 input wire [9:0] i_ph,
 input wire [2:0] i_np,
 input wire [18:0] i_xbase,
 input wire [18:0] i_xps,
 input wire [18:0] i_obase,
 input wire [18:0] i_ops,
 input wire [1:0] i_fmt,
 output wire ready,
 output wire idle,
 output reg x_re,
 output reg [18:0] x_addr,
 input wire x_rv,
 input wire f_fault,
 output reg fault,
 output reg [31:0] phase_cycles,
 output reg ev_go,
 output reg ev_end,
 output reg stream_end_v,output reg[1:0] stream_end_tag,
 output reg [1:0] ev_tag,
 input wire [63:0] rom_pq0,
 input wire [63:0] rom_pq1,
 input wire [47:0] rom_sq
);
 // Phase and stream address wires belong to the real registered command
 // endpoint and calendar reader, respectively. They do not cross this hard
 // control-state leaf as combinational input->output bypasses.
 ot_s81_pq_ctl_static_native u_state (.rom_pa0(),.rom_pa1(),.rom_sa(),.*);
endmodule
`default_nettype wire
