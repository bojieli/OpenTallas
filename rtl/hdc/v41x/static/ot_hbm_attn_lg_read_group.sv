`timescale 1ns/1ps
`default_nettype none
// GEO-H LG read port group of the attention query/P front (v15 engine_lg_port_group_rule): one registered
// cluster per VM bank pair, bits rq[(2k)*17,(2k+2)*17) and rr[(2k)*257,(2k+2)*257).
// rq: the group registers the SAME next state the query/P prefetch registers hold today ({fetch_v,base+bank},
// query owner first) -> identical request cycle, the face mux moves inside the group (no added edge).
// rr: one registered capture edge (+1), priced by the front as FILL_LAT 8 -> 9. No ready/credit/arbitration.
module ot_hbm_attn_lg_read_group #(parameter integer GROUP=0)(
 input wire clk,rst_n,
 input wire q_fetch_v,input wire[15:0]q_fetch_base,
 input wire p_fetch_v,input wire[15:0]p_fetch_base,
 output reg[33:0]rq,
 input wire[513:0]rr_i,output reg[513:0]rr_o
);
 always @(posedge clk or negedge rst_n)
  if(!rst_n)for(integer b=0;b<2;b=b+1)begin rq[b*17+16]<=0;rr_o[b*257+256]<=0;end
  else for(integer b=0;b<2;b=b+1)begin rq[b*17+16]<=q_fetch_v|p_fetch_v;rr_o[b*257+256]<=rr_i[b*257+256];end
 always @(posedge clk)for(integer b=0;b<2;b=b+1)begin
  rq[b*17+:16]<=q_fetch_v?16'(q_fetch_base+16'(2*GROUP+b)):p_fetch_v?16'(p_fetch_base+16'(2*GROUP+b)):16'd0;
  rr_o[b*257+:256]<=rr_i[b*257+:256];
 end
endmodule
`default_nettype wire
