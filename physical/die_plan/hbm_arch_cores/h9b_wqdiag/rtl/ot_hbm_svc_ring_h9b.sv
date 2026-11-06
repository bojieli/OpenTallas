`timescale 1ns/1ps
// H9b (H-PC 2026-10-16): DEPTH-entry ring buffer for the PC leaf K/KR boundary. Writes land at wp (in_v is a flop or a
// shallow internal signal); a pop only advances rp, so no data moves on pop and the pop select never reaches the payload
// flops. rp is replicated per 64-bit slice (each slice reads mem[rp_s] through a DEPTH:1 mux). cnt is a register.
// The caller guarantees no push when full (k_rdy credit / in_r); an overflow or a pop when empty latches fault.
// MUT 1 (bench): every slice except slice 0 reads the entry one behind (rp-1).
module ot_hbm_svc_ring_h9b #(parameter integer WIDTH=1,DEPTH=3,MUT=0)(
 input wire clk,rst_n,
 input wire in_v,input wire [WIDTH-1:0]in_data,
 output wire out_v,input wire pop,output wire [WIDTH-1:0]out_data,
 output reg [2:0]cnt,output wire [2:0]cnt_next,output reg fault
);
 localparam N=(WIDTH+63)/64;
 reg [WIDTH-1:0] mem [0:DEPTH-1];
 reg [1:0] wp;
 assign out_v=cnt!=3'd0;
 assign cnt_next=cnt+{2'b0,in_v}-{2'b0,pop};
 always @(posedge clk) if(in_v) mem[wp]<=in_data;
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
  assign out_data[s*64+:B]=mem[rs][s*64+:B];
 end
endmodule
