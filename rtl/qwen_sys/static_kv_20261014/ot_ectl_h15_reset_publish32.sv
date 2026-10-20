`timescale 1ns/1ps
// PRIVATE C-H15 structural building block, not yet connected to the candidate.
// Publication copies preserve original RP3 -> R0/4 -> RC,RSC/5 edges and async
// assertion. Every consumer bank must independently prove <=32 mapped loads.
module ot_ectl_h15_reset_publish32 #(parameter integer MUT=0)(
 input wire clk,rst_n,
 output wire [23:0] rp,
 output wire [11:0] rc,
 output wire [8:0] rsc);
 ot_rst_relay_bounded32 #(.REGIONS(24)) roots(.clk(clk),.rst_n_in(rst_n),.rst_n(rp));
 (* keep="true",dont_touch="true" *) reg [1:0] r0;
 always @(posedge clk or negedge rp[23])if(!rp[23])r0<=0;else r0<=2'b11;
 (* keep="true",dont_touch="true" *) reg [11:0] rc_pub;
 (* keep="true",dont_touch="true" *) reg [8:0] rsc_pub;
 genvar i;
 generate
 for(i=0;i<12;i=i+1)begin:control
  always @(posedge clk or negedge rp[i])if(!rp[i])rc_pub[i]<=0;else rc_pub[i]<=r0[i/6];
 end
 for(i=0;i<9;i=i+1)begin:score
  always @(posedge clk or negedge rp[12+i])if(!rp[12+i])rsc_pub[i]<=0;else rsc_pub[i]<=r0[i/5];
 end
 endgenerate
 assign rc=(MUT==1)?{12{r0[0]}}:rc_pub;
 assign rsc=rsc_pub;
endmodule
