// Opt-in BW safe variant: identical H9b ring edge semantics, per8b write
// and read pointer copies. No new stage, unchanged payload storage/count.
`timescale 1ns/1ps
// H9b (H-PC 2026-10-16): DEPTH-entry ring buffer for the PC leaf K/KR boundary. Writes land at wp (in_v is a flop or a
// shallow internal signal); a pop only advances rp, so no data moves on pop and the pop select never reaches the payload
// flops. rp is replicated per 64-bit slice (each slice reads mem[rp_s] through a DEPTH:1 mux). cnt is a register.
// The caller guarantees no push when full (k_rdy credit / in_r); an overflow or a pop when empty latches fault.
// MUT 1 (bench): every slice except slice 0 reads the entry one behind (rp-1).
module ot_hbm_svc_ring_bw_safe #(parameter integer WIDTH=1,DEPTH=3,MUT=0,REGIONAL=0,REGIONAL_RESET=0,REGIONAL_NONEMPTY=0,NONEMPTY_GROUP=1)(
 input wire clk,rst_n,
 input wire in_v,input wire [WIDTH-1:0]in_data,
 output wire out_v,input wire pop,output wire [WIDTH-1:0]out_data,
 output reg [2:0]cnt,output wire [2:0]cnt_next,output reg fault,
 input wire [(WIDTH+15)/16-1:0] in_v_regions,pop_regions,
 input wire [(WIDTH+15)/16-1:0] rst_n_regions,
 output wire [(WIDTH+15)/16-1:0] out_v_regions
);
 localparam N=(WIDTH+7)/8;
 reg [WIDTH-1:0] mem [0:DEPTH-1];
 assign out_v=cnt!=3'd0;
 assign cnt_next=cnt+{2'b0,in_v}-{2'b0,pop};
 always @(posedge clk)
  if(!rst_n)begin cnt<=0;fault<=0;end
  else begin
   cnt<=cnt_next;
   if((in_v&&!pop&&cnt==DEPTH)||(pop&&cnt==0)) fault<=1'b1;
  end
 // Regional occupancies track identical transactions but remain independent
 // state cones. A region's count drives only its local consumer decision.
 for(genvar r=0;r<(WIDTH+15)/16;r=r+1)begin:g_control
  wire local_rst_n=(REGIONAL_RESET!=0)?rst_n_regions[r]:rst_n;
  if(REGIONAL!=0&&REGIONAL_NONEMPTY==0)begin:g_local
   (* keep="true",dont_touch="true" *) reg[2:0] count_q;
   always @(posedge clk)if(!local_rst_n)count_q<=0;
    else count_q<=cnt_next;
   assign out_v_regions[r]=count_q!=0;
  end else if(REGIONAL!=0)begin:g_nonempty
   if(r%NONEMPTY_GROUP==0)begin:g_owner
    (* keep="true",dont_touch="true" *) reg live_q;
    always @(posedge clk)if(!local_rst_n)live_q<=0;
     else live_q<=cnt_next!=0;
    assign out_v_regions[r]=live_q;
   end else begin:g_group_member
    assign out_v_regions[r]=out_v_regions[r-r%NONEMPTY_GROUP];
   end
  end else begin:g_common
   assign out_v_regions[r]=out_v;
  end
 end
 for(genvar s=0;s<N;s=s+1)begin:g_slice
  wire slice_rst_n=(REGIONAL_RESET!=0)?rst_n_regions[s/2]:rst_n;
  wire push_s=(REGIONAL!=0)?in_v_regions[s/2]:in_v;
  wire pop_s=(REGIONAL!=0)?pop_regions[s/2]:pop;
  localparam B=(WIDTH-s*8<8)?WIDTH-s*8:8;
  // Kept write pointer copies prevent one bank-enable cone driving all
  // WIDTH payload muxes. A decode controls at most8 bits per bank.
  (* keep="true",dont_touch="true" *) reg [1:0] wp;
  always @(posedge clk)if(push_s)mem[wp][s*8+:B]<=in_data[s*8+:B];
  always @(posedge clk)if(!slice_rst_n)wp<=0;
   else if(push_s)wp<=(wp==DEPTH-1)?2'd0:wp+2'd1;
  (* keep="true",dont_touch="true" *) reg [1:0] rp;
  always @(posedge clk)
   if(!slice_rst_n) rp<=0; else if(pop_s) rp<=(rp==DEPTH-1)?2'd0:rp+2'd1;
  wire [1:0] rs=(MUT==1&&s!=0)?((rp==0)?2'(DEPTH-1):rp-2'd1):rp;
  assign out_data[s*8+:B]=mem[rs][s*8+:B];
 end
endmodule
