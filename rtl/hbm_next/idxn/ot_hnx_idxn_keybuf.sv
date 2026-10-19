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
// RS = 1 (HBM-NEXT-UNITS IDXQ 2026-10-19, quad tile hnx_idxq_kb; RS = 0 = the structure above, unchanged): the replay
// select is NOT the replay_v port (gate: one port fanned to 8,764 mux loads over 1.2 mm, combinational to key_out) but
// the registered PRE strobe (pre_v one edge earlier = replay_v on every correct edge), replicated per macro (one kept
// copy per 256-bit column, <= 300 loads each, local); the regenerated tag uses the registered pre_index. Same key_out
// on every edge of a correct schedule; a replay_v that is not exactly the registered PRE strobe (either way) FAULTs.
// PR = 1 (HBM-NEXT-UNITS IDXQ 2026-10-19, quad tile hnx_idxq_kb2; PR = 0 = everything above, bit for bit): the tile is
// PIN-REGISTERED (gate hnx_idxq_kb FAIL: key_in -> key_out combinational over 1,202 um, pbase -> tag -> key_out
// unregistered, pin-flop spread 149/132 ps). Every input lands in ONE kept flop at the face and key_out / fault leave a
// flop: the key path is +2 edges. The scorer's beat strobe / index ride the same 2 edges inside this tile
// (beat_in_* -> beat_out_*), and the calendar issues KEY / PRE 2 edges earlier (hnx_idxn_calendar.py --kb-pipe 2,
// qctl G2MIN 23 + 2), so the scorer core sees exactly the PR = 0 timeline (same score / TX / done edges); only the HBM
// key-line delivery edge (key_slot) moves 2 edges earlier. PR = 0: beat_out_* = beat_in_* (wires; may stay unconnected).
module ot_hnx_idxn_keybuf #(parameter integer NP=8,RS=0,PR=0)(
 input wire clk,rst_n,clear,input wire[2:0]pbase,
 input wire live_v,input wire[7:0]live_index,input wire[NP*1099-1:0]key_in,
 input wire pre_v,input wire[7:0]pre_index,
 input wire replay_v,input wire[7:0]replay_index,
 input wire beat_in_v,input wire[7:0]beat_in_index,
 output wire beat_out_v,output wire[7:0]beat_out_index,
 output wire[NP*1099-1:0]key_out,output wire fault
);
 wire c_clear,c_live,c_pre,c_replay;wire[2:0]c_pbase;wire[7:0]c_li,c_pi,c_ri;
 wire[NP*1099-1:0]c_key,c_out;reg c_fault;
 if(PR==0)begin:gnp
  assign {c_clear,c_pbase,c_live,c_li,c_pre,c_pi,c_replay,c_ri}={clear,pbase,live_v,live_index,pre_v,pre_index,replay_v,replay_index};
  assign c_key=key_in;assign key_out=c_out;assign fault=c_fault;
  assign beat_out_v=beat_in_v;assign beat_out_index=beat_in_index;
 end else begin:gpr
  (* keep *) reg clear_r,live_r,pre_r,replay_r;(* keep *) reg[2:0]pbase_r;(* keep *) reg[7:0]li_r,pi_r,ri_r;
  (* keep *) reg[NP*1099-1:0]key_r,out_r;(* keep *) reg fault_r;
  (* keep *) reg bv1,bv2;(* keep *) reg[7:0]bi1,bi2;
  always @(posedge clk)begin
   clear_r<=clear;pbase_r<=pbase;live_r<=live_v;li_r<=live_index;pre_r<=pre_v;pi_r<=pre_index;replay_r<=replay_v;ri_r<=replay_index;
   key_r<=key_in;out_r<=c_out;fault_r<=c_fault;bv1<=beat_in_v;bi1<=beat_in_index;bv2<=bv1;bi2<=bi1;
  end
  assign {c_clear,c_pbase,c_live,c_li,c_pre,c_pi,c_replay,c_ri}={clear_r,pbase_r,live_r,li_r,pre_r,pi_r,replay_r,ri_r};
  assign c_key=key_r;assign key_out=out_r;assign fault=fault_r;
  assign beat_out_v=bv2;assign beat_out_index=bi2;
 end
 localparam integer NM=NP*1088/256;
 wire[NP*1088-1:0]wd,rd;
 for(genvar p=0;p<NP;p=p+1)begin:gp
  assign wd[p*1088+:1088]=c_key[p*1099+11+:1088];
 end
 for(genvar m=0;m<NM;m=m+1)begin:gm
  ot_sram_1r1w_256x256_m2_r2c2 mem(.clk(clk),.r_ce_in(c_pre),.r_addr_in(c_pi),.rd_out(rd[m*256+:256]),
   .w_ce_in(c_live),.w_addr_in(c_li),.wd_in(wd[m*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
 end
 reg[170:0]have;reg pre_q;reg[7:0]pre_iq;
 reg[NP*1099-1:0]regen;
 always @*for(integer p=0;p<NP;p=p+1)regen[p*1099+:1099]={rd[p*1088+:1088],10'((int'(c_pbase)+p)*128+int'(RS==0?c_ri:pre_iq)),1'b1};
 if(RS==0)begin:gsel
  assign c_out=c_replay?regen:c_key;
 end else begin:gsel_rs
  (* keep *) reg[NM-1:0]sel_q;                // one copy of the registered PRE strobe per 256-bit macro column
  always @(posedge clk)sel_q<={NM{c_pre}};
  for(genvar p=0;p<NP;p=p+1)begin:gl
   for(genvar i=0;i<1099;i=i+1)begin:gb
    localparam integer M=(i<11)?(p*1088)/256:(p*1088+i-11)/256;
    assign c_out[p*1099+i]=sel_q[M]?regen[p*1099+i]:c_key[p*1099+i];
   end
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin have<=0;pre_q<=0;pre_iq<=0;c_fault<=0;end
  else begin
   pre_q<=c_pre;pre_iq<=c_pi;
   if(c_clear)have<=0;
   else if(c_live&&c_li<=8'd170)have[c_li]<=1;
   if(c_live&&(c_replay||c_li>8'd170))c_fault<=1;
   if(c_replay&&(!pre_q||pre_iq!=c_ri||c_ri>8'd170||!have[c_ri]))c_fault<=1;
   if(RS!=0&&pre_q&&!c_replay)c_fault<=1;     // RS = 1 replays on the registered PRE strobe: c_replay must match it
   if(c_pre&&(c_pi>8'd170||!have[c_pi]))c_fault<=1;
  end
 end
endmodule
`default_nettype wire
