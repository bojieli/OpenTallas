`default_nettype none
// HBM-NEXT-UNITS-IDXN 2026-10-19: key REPLAY buffer of one IDX scorer (one key stream for N query rows).
// Row 0 of an N-row IDX.INDEX record scores the LIVE key lines from the HBM key-line service (key_slot edges, exactly as
// d4g) and this buffer captures every live beat (8 lines x 1,088 data bits = 8,704 b = 34 macros 256 x 256, beat b at
// address b <= 170). Rows 1..N-1 re-score the SAME keys from the buffer: the calendar's PRE class reads beat b one edge
// before the replay beat (registered SRAM read), so the scorer sees the replayed line on the replay edge exactly as it
// sees a live line on a key_slot edge. The service tag of a replayed line is regenerated (valid = 1, tag = (128 p + b)
// mod 1024: the tag the scorer checks; the live tags were checked when captured). The HBM service is asked for keys
// ONCE per record (key_slot only for row 0). Faults (static schedule, no flow control): replay of a beat not captured
// in this record, a replay beat without its PRE read on the edge before (or another index), live and replay together.
// NP / pbase (HBM-NEXT-UNITS IDXQ 2026-10-19, quad form): the buffer holds NP key lines (8 = one stack scorer, 34
// macros; 4 = one quadrant quarter scorer, PCs pbase .. pbase+3 of its stack, 17 macros); the regenerated tag of line p
// is that of stack port pbase + p. pbase is a die strap (0 for a stack scorer; 4 x half for a quarter), so the two
// quarter halves share ONE master. NP = 8, pbase = 0 is the original buffer bit for bit.
module ot_hnx_idxn_keybuf #(parameter integer NP=8)(
 input wire clk,rst_n,clear,input wire[2:0]pbase,
 input wire live_v,input wire[7:0]live_index,input wire[NP*1099-1:0]key_in,
 input wire pre_v,input wire[7:0]pre_index,
 input wire replay_v,input wire[7:0]replay_index,
 output wire[NP*1099-1:0]key_out,output reg fault
);
 localparam integer NM=NP*1088/256;
 wire[NP*1088-1:0]wd,rd;
 for(genvar p=0;p<NP;p=p+1)begin:gp
  assign wd[p*1088+:1088]=key_in[p*1099+11+:1088];
 end
 for(genvar m=0;m<NM;m=m+1)begin:gm
  ot_sram_1r1w_256x256_m2_r2c2 mem(.clk(clk),.r_ce_in(pre_v),.r_addr_in(pre_index),.rd_out(rd[m*256+:256]),
   .w_ce_in(live_v),.w_addr_in(live_index),.wd_in(wd[m*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
 end
 reg[NP*1099-1:0]regen;
 always @*for(integer p=0;p<NP;p=p+1)regen[p*1099+:1099]={rd[p*1088+:1088],10'((int'(pbase)+p)*128+int'(replay_index)),1'b1};
 assign key_out=replay_v?regen:key_in;
 reg[170:0]have;reg pre_q;reg[7:0]pre_iq;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin have<=0;pre_q<=0;pre_iq<=0;fault<=0;end
  else begin
   pre_q<=pre_v;pre_iq<=pre_index;
   if(clear)have<=0;
   else if(live_v&&live_index<=8'd170)have[live_index]<=1;
   if(live_v&&(replay_v||live_index>8'd170))fault<=1;
   if(replay_v&&(!pre_q||pre_iq!=replay_index||replay_index>8'd170||!have[replay_index]))fault<=1;
   if(pre_v&&(pre_index>8'd170||!have[pre_index]))fault<=1;
  end
 end
endmodule
`default_nettype wire
