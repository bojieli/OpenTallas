`timescale 1ns/1ps
// SVC-SMALL 2026-10-18: ot_hbm_svc_ring_h9b with the DEPTH entries as explicit flop registers (no inferred memory), for
// leaves under the async_gray_fifo kit profile, whose source audit needs an explicit flop graph (no Yosys $mem).  Same
// ports, parameters and cycle behaviour as ot_hbm_svc_ring_h9b (DEPTH 2 or 3): writes land at wp, a pop only advances
// the per-64-bit-slice read pointers rp, cnt is a register, overflow / empty pop latch fault.  MUT 1 as the original.
module ot_hbm_svc_ring_h9b_ff #(parameter integer WIDTH=1,DEPTH=3,MUT=0)(
 input wire clk,rst_n,
 input wire in_v,input wire [WIDTH-1:0]in_data,
 output wire out_v,input wire pop,output wire [WIDTH-1:0]out_data,
 output reg [2:0]cnt,output wire [2:0]cnt_next,output reg fault
);
 localparam N=(WIDTH+63)/64;
 reg [WIDTH-1:0] e0,e1,e2;
 reg [1:0] wp;
 assign out_v=cnt!=3'd0;
 assign cnt_next=cnt+{2'b0,in_v}-{2'b0,pop};
 always @(posedge clk) begin
  if(in_v&&wp==2'd0) e0<=in_data;
  if(in_v&&wp==2'd1) e1<=in_data;
  if(in_v&&wp==2'd2&&DEPTH>2) e2<=in_data;
 end
 always @(posedge clk)
  if(!rst_n)begin wp<=0;cnt<=0;fault<=0;end
  else begin
   if(in_v) wp<=(wp==DEPTH-1)?2'd0:wp+2'd1;
   cnt<=cnt_next;
   if((in_v&&!pop&&cnt==DEPTH)||(pop&&cnt==0)) fault<=1'b1;
  end
 for(genvar s=0;s<N;s=s+1)begin:g_slice
  localparam B=(WIDTH-s*64<64)?WIDTH-s*64:64;
  (* keep="true",dont_touch="true" *) reg [1:0] rp;
  always @(posedge clk)
   if(!rst_n) rp<=0; else if(pop) rp<=(rp==DEPTH-1)?2'd0:rp+2'd1;
  wire [1:0] rs=(MUT==1&&s!=0)?((rp==0)?2'(DEPTH-1):rp-2'd1):rp;
  assign out_data[s*64+:B]=(rs==2'd0)?e0[s*64+:B]:(rs==2'd1)?e1[s*64+:B]:e2[s*64+:B];
 end
endmodule
