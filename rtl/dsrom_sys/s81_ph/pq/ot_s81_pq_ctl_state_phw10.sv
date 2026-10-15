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
`ifdef OT_PQ_CTL_CALCAP
 // CALCAP (native audit 10-15 of the closed INCAP view: calendar_action/calendar_v/go capture 343-386 ps > 190,
 // they decode straight into the state machine): every command/calendar input is captured in a pin register.
 // The whole PQ timeline moves +1 edge uniformly against the reader/endpoint (calendar, go and its i_* fields
 // together); responses (ROM, VM, roots, AQ) stay relative to this leaf's own outputs. Endpoint completion +1.
 reg cv_q,go_q;reg[74:0] ca_q;reg[9:0] iph_q;reg[2:0] inp_q;reg[18:0] ixb_q,ixps_q,iob_q,iops_q;reg[1:0] ifm_q;
 always @(posedge clk) begin
  cv_q<=calendar_v;ca_q<=calendar_action;iph_q<=i_ph;inp_q<=i_np;ixb_q<=i_xbase;ixps_q<=i_xps;
  iob_q<=i_obase;iops_q<=i_ops;ifm_q<=i_fmt;
`ifdef OT_S81_PQ_CALCAP_MUT_GO
 end
 always @(*) go_q=go;   // mutant: go bypasses its capture (accept one edge ahead of its calendar)
`else
  go_q<=go;
 end
`endif
 ot_s81_pq_ctl_static_native u_state (.rom_pa0(),.rom_pa1(),.rom_sa(),.calendar_v(cv_q),.calendar_action(ca_q),.go(go_q),
  .i_ph(iph_q),.i_np(inp_q),.i_xbase(ixb_q),.i_xps(ixps_q),.i_obase(iob_q),.i_ops(iops_q),.i_fmt(ifm_q),.*);
`else
 ot_s81_pq_ctl_static_native u_state (.rom_pa0(),.rom_pa1(),.rom_sa(),.*);
`endif
endmodule
`default_nettype wire
