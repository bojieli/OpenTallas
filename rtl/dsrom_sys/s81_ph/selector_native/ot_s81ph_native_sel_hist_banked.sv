`timescale 1ns/1ps
// TOPK5 one-level composition prototype: eight copies of the SAME realBANK0
// hard leaf. Constant digit/group inversions preserve exact original bin IDs.
// Not bound into releasequarter. +2GS, +3group-query, +3busy edges; startup+6.
module ot_s81ph_native_sel_hist_banked #(parameter integer MUT=0)(
 input wire clk,rst_n,clr,i_v,input wire[15:0]i_en,input wire[127:0]i_dg,
 input wire[3:0]gsel,output reg[239:0]gsum,output reg[175:0]gbin,output reg busy);
 wire[7:0] local_rst;
 ot_rst_relay #(.REGIONS(8),.SYNC_STAGES(2),.TREE_STAGES(1))u_parent_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(local_rst));
 reg rv;reg[15:0]re;reg[127:0]rd;
 always@(posedge clk or negedge local_rst[0])if(!local_rst[0])rv<=0;else rv<=i_v;
 always@(posedge clk)begin re<=i_en;rd<=i_dg;end
 wire[239:0]sum_bus;wire[8*176-1:0]bin_bus;wire[7:0]busy_bus;
 genvar b,l;
 generate for(b=0;b<8;b=b+1)begin:bank
  (* keep="true" *) reg rc;
  (* keep="true" *) reg[3:0]rg;
  always@(posedge clk or negedge local_rst[b])if(!local_rst[b])rc<=0;else rc<=clr;
  always@(posedge clk)rg<=gsel;
  wire[127:0]nd;
  for(l=0;l<16;l=l+1)begin:digit
   assign nd[8*l+:8]=rd[8*l+:8]^(8'(b)<<5);
  end
  wire[3:0]ng=rg^(4'(b)<<1)^((MUT==1 && b==3)?4'h1:4'h0);
  wire nc=(MUT==2 && b==3)?1'b0:rc;
`ifdef OT_HARD_CHILDREN
  ot_s81ph_native_sel_hist_bank u_bank(
`else
  ot_s81ph_native_sel_hist_bank #(.W(16),.CB(11),.BANK(0),.NB(32),.HPIPE(1)) u_bank(
`endif
   .clk(clk),.rst_n(local_rst[b]),.clr(nc),.i_v(rv),.i_en(re),.i_dg(nd),.gsel(ng),
   .gsum(sum_bus[30*b+:30]),.gbin(bin_bus[176*b+:176]),.busy(busy_bus[b]));
 end endgenerate
 reg[175:0]joined;integer j;
 always@*begin joined=0;for(j=0;j<8;j=j+1)joined=joined|bin_bus[176*j+:176];end
 always@(posedge clk)begin gsum<=sum_bus;gbin<=joined;end
 always@(posedge clk or negedge local_rst[0])if(!local_rst[0])busy<=0;else busy<=|busy_bus;
endmodule
