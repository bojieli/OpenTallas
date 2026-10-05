`timescale 1ns/1ps
// Local exact unsigned comparison; every valid/key/id/payload bit participates.
// Named keep nodes retain balanced compare partitions for technology mapping.
module ot_gpu_topk_compare_bal #(parameter integer W=42)(
 input wire [W-1:0] a,b, output wire gt);
 localparam integer L=$clog2(W), T=1<<L;
 (* keep *) wire [T-1:0] g[0:L], p[0:L];
 assign g[0]={{(T-W){1'b0}},(a & ~b) & {1'b0,{(W-1){1'b1}}}};
 assign p[0]={{(T-W){1'b1}},~(a ^ b)};
 genvar k,j;
 generate for(k=1;k<=L;k=k+1) begin:level
   for(j=0;j<(T>>k);j=j+1) begin:pair
    assign g[k][j]=g[k-1][2*j+1] | (p[k-1][2*j+1] & g[k-1][2*j]);
    assign p[k][j]=p[k-1][2*j+1] & p[k-1][2*j];
   end
   assign g[k][T-1:(T>>k)]=0;
   assign p[k][T-1:(T>>k)]={(T-(T>>k)){1'b1}};
 end endgenerate
 assign gt=g[L][0];
endmodule

module ot_gpu_topk_cs_bal #(parameter integer W=42,N=8,KB=8,J=4,DESC=1)(
 input wire clk,input wire [N*W-1:0] d,output reg [N*W-1:0] q);
 genvar i;
 generate for(i=0;i<N;i=i+1) begin:pair
  if((i^J)>i) begin:active
   localparam integer A=i,B=i^J;
   localparam integer UP=(((i & KB)==0)?1:0) ^ (DESC!=0);
   wire swap;
   ot_gpu_topk_compare_bal #(.W(W)) c
    (.a(UP?d[A*W+:W]:d[B*W+:W]),.b(UP?d[B*W+:W]:d[A*W+:W]),.gt(swap));
   always @(posedge clk) begin
    q[A*W+:W]<=swap?d[B*W+:W]:d[A*W+:W];
    q[B*W+:W]<=swap?d[A*W+:W]:d[B*W+:W];
   end
  end
 end endgenerate
endmodule

module ot_gpu_topk_merge_bal #(parameter integer W=42)(
 input wire clk,input wire [8*W-1:0] a,b,output wire [8*W-1:0] q);
 reg [8*W-1:0] s0;
 genvar i;
 generate for(i=0;i<8;i=i+1) begin:pick
  wire choose_a;
  ot_gpu_topk_compare_bal #(.W(W)) c(.a(a[i*W+:W]),.b(b[(7-i)*W+:W]),.gt(choose_a));
  always @(posedge clk) s0[i*W+:W]<=choose_a?a[i*W+:W]:b[(7-i)*W+:W];
 end endgenerate
 wire [8*W-1:0] s1,s2;
 ot_gpu_topk_cs_bal #(.W(W),.KB(8),.J(4),.DESC(1)) c1(.clk(clk),.d(s0),.q(s1));
 ot_gpu_topk_cs_bal #(.W(W),.KB(8),.J(2),.DESC(1)) c2(.clk(clk),.d(s1),.q(s2));
 ot_gpu_topk_cs_bal #(.W(W),.KB(8),.J(1),.DESC(1)) c3(.clk(clk),.d(s2),.q(q));
endmodule
