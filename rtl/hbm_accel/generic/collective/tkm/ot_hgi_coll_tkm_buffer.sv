`timescale 1ns/1ps
// Own-flop pass-1/pass-2 buffer root: both actual SRAM clocks are local to clk.
// Actual control/address/payload pins captured; three-edge read reply.
// SRAM-adjacent rd_local separates measured221.68ps macro-to-boundary wire from publication.
module ot_hgi_coll_tkm_buffer #(parameter integer MUT=0,DW=340,DELIVERED_RESET=0)(
 input wire clk,rst_n,w_v,input wire[9:0]w_addr,input wire[DW-1:0]w_data,
 input wire r_v,input wire[9:0]r_addr,output reg rd_v,output reg[DW-1:0]rd_data
);
 // DELIVERED_RESET consumes a timed, already die-synchronized reset. The
 // three ordinary data registers preserve the legacy release depth; they do
 // not resynchronize an asynchronous source. Hold reset low for >=3 edges.
 wire[0:0]rr;
 generate if(DELIVERED_RESET)begin:g_delivered
  (* keep = "true" *) reg[2:0] reset_q;
  always @(posedge clk) reset_q <= {reset_q[1:0],rst_n};
  assign rr[0]=(MUT==2)?reset_q[1]:reset_q[2];
 end else begin:g_legacy
  ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1))u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 end endgenerate
 reg wp,rp,r_delay,r_publish;reg[DW-1:0]rd_local;reg[9:0]wa,ra;reg[DW-1:0]wd;wire[511:0]q;
 always @(posedge clk)begin wa<=w_addr;ra<=r_addr;wd<=w_data;rd_local<=q[DW-1:0];rd_data<=rd_local;end
 generate if(DELIVERED_RESET)begin:g_controls_delivered
  always @(posedge clk)begin
   if(!rr[0])begin wp<=0;rp<=0;r_delay<=0;r_publish<=0;rd_v<=0;end
   else begin wp<=w_v;rp<=r_v;r_delay<=rp;r_publish<=r_delay;rd_v<=r_publish;end
  end
 end else begin:g_controls_legacy
  always @(posedge clk or negedge rr[0])begin
   if(!rr[0])begin wp<=0;rp<=0;r_delay<=0;r_publish<=0;rd_v<=0;end
   else begin wp<=w_v;rp<=r_v;r_delay<=rp;r_publish<=r_delay;rd_v<=r_publish;end
  end
 end endgenerate
 for(genvar m=0;m<2;m=m+1)begin:g_bm
  wire[511:0]wide=512'(wd);
  ot_sram_1r1w_1024x256_m2_r2c2 u_b(.clk(clk),.r_ce_in(rp),.r_addr_in((MUT==1)?(ra^10'd1):ra),.rd_out(q[256*m+:256]),
   .w_ce_in(wp),.w_addr_in(wa),.wd_in(wide[256*m+:256]),.w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(18'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end
endmodule
