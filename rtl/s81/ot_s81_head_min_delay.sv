`timescale 1ns/1ps
// Identity logic with a retained physical minimum-delay cell at every bit.
module ot_s81_head_min_buffer #(parameter integer W=1, ENABLE=0)
(input wire [W-1:0] d, output wire [W-1:0] q);
 genvar b;
 generate if(ENABLE) begin:g_physical
  for(b=0;b<W;b=b+1) begin:g_bit
   (* keep = 1, dont_touch = 1 *) BUFx2_ASAP7_75t_R u_min_delay (.A(d[b]),.Y(q[b]));
  end
 end else begin:g_wire
  assign q=d;
 end endgenerate
endmodule

// Exact fixed-cycle line; native min-delay option changes no arithmetic/cycles.
module ot_s81_head_min_delay #(parameter integer W=32,D=1,ENABLE=0)
(input wire clk,rst_n,input wire [W-1:0] d,output wire [W-1:0] q);
 genvar s;
 generate if(!ENABLE) begin:g_original
  ot_hdc_delay #(.W(W),.D(D)) u_delay(.clk(clk),.rst_n(rst_n),.d(d),.q(q));
 end else if(D==0) begin:g_zero
  assign q=d;
 end else begin:g_delay
  wire [W-1:0] tap[0:D];
  assign tap[0]=d;
  for(s=0;s<D;s=s+1) begin:g_stage
   wire [W-1:0] bounded_d;
   reg [W-1:0] stage_q;
   ot_s81_head_min_buffer #(.W(W),.ENABLE(1)) u_bound(.d(tap[s]),.q(bounded_d));
   always @(posedge clk) stage_q<=bounded_d;
   assign tap[s+1]=stage_q;
  end
  assign q=tap[D];
 end endgenerate
endmodule
