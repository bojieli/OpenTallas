`timescale 1ns/1ps
// Actual256-entry external host landing FIFO matching endpoint FCR256.
// Two real256x256 SRAMs; no initialized/software on-chip memory substitute.
// Single requested read, one registered SRAM edge, one output capture edge.
//
// PINREG=1 (default, HBM die d4f host_cp_landing tile; HBMA-HOST 2026-10-17): every tile pin is registered.
//  * in_v/in_data land in pin flops (in_q*) and write the SRAM from there: +1 edge endpoint face -> FIFO.
//  * out_ready lands in a pin flop; the pop is decided on that flop AND a mirror of this tile's own out_v
//    (ov_m = out_v as the consumer sampled it), i.e. a word is consumed one edge after the edge on which the
//    consumer saw out_v && out_ready.  out_v/out_data stay unchanged through that edge (they change only on
//    consume), so the consumer's capture is the head word.  CONSUMER CONTRACT: out_ready is asserted at most
//    every other edge (ot_hbm_host_packet_static pulses rx_ready this way and evaluates the same mirrored
//    handshake), otherwise one word could be seen twice.
//  * pop (credit return to the endpoint face) is a flop Q: +1 edge on the elastic credit loop.
//  * fault is a flop Q (as before), computed from the input pin flops.
// Fixed added latency: write +1 edge; pop +1 edge; head-to-next-head +1 edge (configuration path only; the host
// link is elastic, so no schedule depends on it).  PINREG=0 keeps the original unregistered behaviour (the
// legacy hfd_host_native composition with ot_hbm_host_packet).
module ot_hbm_host_landing256 #(parameter integer PINREG=1)(input wire clk,rst_n,
 input wire in_v,input wire[544:0]in_data,
 output reg out_v,output reg[511:0]out_data,input wire out_ready,
 output wire pop,output reg fault);
 reg[7:0]wp,rp;reg[8:0]count;reg pending;
 // ---------------- pin flops (PINREG=1) or pass-through (PINREG=0)
 reg iv_q,or_q,ov_m,pop_q;reg[544:0]id_q;
 always @(posedge clk)id_q<=in_data;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin iv_q<=0;or_q<=0;ov_m<=0;end
  else begin iv_q<=in_v;or_q<=out_ready;ov_m<=out_v;end
 wire w_v=(PINREG!=0)?iv_q:in_v;
 wire[544:0]w_d=(PINREG!=0)?id_q:in_data;
`ifdef OT_HOST_LANDING_MUT_NOMIRROR
 wire consume=(PINREG!=0)?(out_v&&or_q):(out_v&&out_ready);
`else
 wire consume=(PINREG!=0)?(ov_m&&or_q):(out_v&&out_ready);
`endif
 wire read_en=!out_v&&!pending&&(count!=0);
 wire[511:0]mem_data;
`ifdef OT_HOST_LANDING_MUT_ADDR
 wire[7:0]read_addr=rp^8'd1;
`else
 wire[7:0]read_addr=rp;
`endif
 always @(posedge clk or negedge rst_n)if(!rst_n)pop_q<=0;else pop_q<=consume;
 assign pop=(PINREG!=0)?pop_q:consume;
 genvar b;generate for(b=0;b<2;b=b+1)begin:g_bank
 ot_sram_1r1w_256x256_m2_r2c2 u_mem(.clk(clk),.r_ce_in(read_en),.r_addr_in(read_addr),.rd_out(mem_data[b*256+:256]),
 .w_ce_in(w_v&&(count!=256)),.w_addr_in(wp),.wd_in(w_d[b*256+:256]),.w_mask_in({256{1'b1}}),
 .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
 end endgenerate
 always @(posedge clk)if(pending)out_data<=mem_data;
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin wp<=0;rp<=0;count<=0;pending<=0;out_v<=0;fault<=0;end
 else begin
  pending<=read_en;
  if(w_v)begin
   if(count==256)fault<=1;else wp<=wp+1'b1;
   if(w_d[544:512]!==33'd0)fault<=1;
  end
  if(pending)out_v<=1;
  if(consume)begin out_v<=0;rp<=rp+1'b1;end
  case({w_v&&(count!=256),consume})
  2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;
  endcase
 end end
endmodule
