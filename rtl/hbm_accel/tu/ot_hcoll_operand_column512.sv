`timescale 1ns/1ps
// Actual retained operand column: sixty-four 512-bit words, two catalog SRAMs.
// Request and reply pins belong to this root. Reply is three rising edges after
// the request capture; parent issue/index/inactive-column pipelines must match.
module ot_hcoll_operand_column512 #(parameter integer MUT=0)(
 input wire clk,rst_n,w_v,input wire[5:0]w_addr,input wire[511:0]w_data,
 input wire r_v,input wire[5:0]r_addr,output reg rd_v,output reg[511:0]rd_data
);
 wire[0:0]rr;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1))u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 reg wp,rp,rp1,rp2;reg[5:0]wa,ra;reg[511:0]wd,read_local;wire[511:0]q;
 always @(posedge clk)begin wa<=w_addr;ra<=r_addr;wd<=w_data;read_local<=q;rd_data<=read_local;end
 always @(posedge clk or negedge rr[0])begin
  if(!rr[0])begin wp<=0;rp<=0;rp1<=0;rp2<=0;rd_v<=0;end
  else begin wp<=w_v;rp<=r_v;rp1<=rp;rp2<=rp1;rd_v<=rp2;end
 end
 for(genvar b=0;b<2;b=b+1)begin:g_bank
  ot_sram_1r1w_128x256_m1_r2c2 u_mem(.clk(clk),.r_ce_in(rp),.r_addr_in({1'b0,(MUT==1)?(ra^6'd1):ra}),
   .rd_out(q[256*b+:256]),.w_ce_in(wp),.w_addr_in({1'b0,wa}),.wd_in(wd[256*b+:256]),
   .w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr('0),.cr_en(2'b0),.cr_sel(16'b0));
 end
endmodule
