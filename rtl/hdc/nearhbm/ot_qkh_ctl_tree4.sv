`timescale 1ns/1ps
// Default-off same-age replacement for shared W-bit D=4 control delay.
// 2 -> 8 -> 32 -> DEST kept captures distribute at existing edges, no added cycles.
module ot_qkh_ctl_tree4 #(parameter integer W=12,DEST=100,MUT=0)(
 input wire clk,rst_n,input wire [W-1:0] d,output wire [DEST*W-1:0] q);
 localparam integer NR=1+4+16+(DEST+1)/2;
 wire [NR-1:0] rr;
 ot_rst_relay_bounded32 #(.REGIONS(NR)) u_reset(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 (* keep="true",dont_touch="true" *) reg [W-1:0] s1[0:1];
 (* keep="true",dont_touch="true" *) reg [W-1:0] s2[0:7];
 (* keep="true",dont_touch="true" *) reg [W-1:0] s3[0:31];
 (* keep="true",dont_touch="true" *) reg [W-1:0] s4[0:DEST-1];
 genvar g;
 generate
 if(W<1 || W>16 || DEST<1 || DEST>128)begin:bad ot_qkh_ctl_tree4_bad_shape trap();end
 for(g=0;g<2;g=g+1)begin:a
  always @(posedge clk or negedge rr[0])if(!rr[0])s1[g]<={W{1'b0}};else s1[g]<=d;
 end
 for(g=0;g<8;g=g+1)begin:b
  always @(posedge clk or negedge rr[1+g/2])if(!rr[1+g/2])s2[g]<={W{1'b0}};else s2[g]<=s1[g/4];
 end
 for(g=0;g<32;g=g+1)begin:c
  always @(posedge clk or negedge rr[5+g/2])if(!rr[5+g/2])s3[g]<={W{1'b0}};else s3[g]<=s2[g/4];
 end
 for(g=0;g<DEST;g=g+1)begin:e
  always @(posedge clk or negedge rr[21+g/2])if(!rr[21+g/2])s4[g]<={W{1'b0}};else s4[g]<=s3[g%32];
  assign q[g*W+:W]=(MUT==1)?s3[g%32]:((MUT==2 && g==0)?(s4[g]^{{(W-1){1'b0}},1'b1}):s4[g]);
 end
 endgenerate
endmodule
