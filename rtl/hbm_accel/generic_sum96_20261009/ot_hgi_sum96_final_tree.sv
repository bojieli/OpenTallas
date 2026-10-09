`timescale 1ns/1ps
// The twelve inputs are FP32 results of contiguous8-rank subtrees, BEFORE
// any BF16 conversion. Fixedtopology completes the real96-rank pairwise tree.
// Receiver must supply all12 protected-bank outputcaptures in wordindexorder.
module ot_hgi_sum96_final_tree #(parameter integer LAT=7)(
 input wire clk,rst_n,valid_in,
 input wire [6143:0] partials,
 output wire valid_out,output wire [511:0] data_out,output wire fault);
 wire [511:0] l0[0:11],l1[0:5],l2[0:2],l3[0:1],l4;
 wire [4:0] v;
 wire [31:0] e1[0:5],e2[0:2],e3,e4;
 wire [15:0] v1[0:5],v2[0:2],v3,v4;
 assign v[0]=valid_in;
 for(genvar j=0;j<12;j=j+1) assign l0[j]=partials[j*512+:512];
 for(genvar j=0;j<6;j=j+1) begin:g_l1
 for(genvar k=0;k<16;k=k+1) begin:g_lane
 ot_hdc_fp32_add_lat #(.LAT(LAT)) a(.clk(clk),.rst_n(rst_n),.valid_in(v[0]),.a(l0[2*j][k*32+:32]),.b(l0[2*j+1][k*32+:32]),.y(l1[j][k*32+:32]),.err(e1[j][2*k+:2]),.valid_out(v1[j][k]));
 end end
 assign v[1]=v1[0][0];
 for(genvar j=0;j<3;j=j+1) begin:g_l2
 for(genvar k=0;k<16;k=k+1) begin:g_lane
 ot_hdc_fp32_add_lat #(.LAT(LAT)) a(.clk(clk),.rst_n(rst_n),.valid_in(v[1]),.a(l1[2*j][k*32+:32]),.b(l1[2*j+1][k*32+:32]),.y(l2[j][k*32+:32]),.err(e2[j][2*k+:2]),.valid_out(v2[j][k]));
 end end
 assign v[2]=v2[0][0];
 for(genvar k=0;k<16;k=k+1) begin:g_l3
 ot_hdc_fp32_add_lat #(.LAT(LAT)) a(.clk(clk),.rst_n(rst_n),.valid_in(v[2]),.a(l2[0][k*32+:32]),.b(l2[1][k*32+:32]),.y(l3[0][k*32+:32]),.err(e3[2*k+:2]),.valid_out(v3[k]));
 end
 // Oddsubtree is carried exactly; no artificial+0 arithmetic at this level.
 reg [511:0] carry[0:LAT-1];
 integer i;
 always @(posedge clk) begin carry[0]<=l2[2];for(i=1;i<LAT;i=i+1)carry[i]<=carry[i-1];end
 assign l3[1]=carry[LAT-1];
 assign v[3]=v3[0];
 for(genvar k=0;k<16;k=k+1) begin:g_l4
 ot_hdc_fp32_add_lat #(.LAT(LAT)) a(.clk(clk),.rst_n(rst_n),.valid_in(v[3]),.a(l3[0][k*32+:32]),.b(l3[1][k*32+:32]),.y(l4[k*32+:32]),.err(e4[2*k+:2]),.valid_out(v4[k]));
 // U2: zeroresults emitted ascanonical+0.
 assign data_out[k*32+:32]=(l4[k*32+:31]==0)?32'd0:l4[k*32+:32];
 end
 assign valid_out=v4[0];
 // Per-command sticky fault: adapter clears byreset/rearm beforeeachcommand.
 reg error;
 wire e1_any=|e1[0]|| |e1[1]|| |e1[2]|| |e1[3]|| |e1[4]|| |e1[5];
 wire e2_any=|e2[0]|| |e2[1]|| |e2[2];
 always @(posedge clk or negedge rst_n)
 if(!rst_n)error<=0;else if((v[1]&&e1_any)||(v[2]&&e2_any)||(v[3]&&|e3)||(valid_out&&|e4))error<=1;
 assign fault=error;
endmodule
