`default_nettype none
// Eight parallel instances replace one keybuf without changing any sampled edge.
// lane_id is a declared quasi-static plan strap. Five SRAMs hold one 1088-bit line;
// the last SRAM uses 64 bits. No arithmetic or reduction order changes.
// RS (DIE-HBM-61/RTL-C3 RE-FORM 11-03, the ot_hnx_idxn_keybuf RS = 1 form of 10-19 applied to one slice):
//   RS = 1 (default, the hardened slice): the replay select is NOT the replay_v port (pre-build gate: one face flop
//          fanned to 1,099 mux loads over the 5-SRAM column, TT -219 ps) but the registered PRE strobe (pre_v one edge
//          earlier = replay_v on every correct edge), one kept copy per 256-bit SRAM column (<= 267 loads, local); the
//          regenerated tag uses the registered pre_index.  Same key_out on every edge of a correct schedule, 0 edges of
//          latency; a replay_v that is not exactly the registered PRE strobe (either way) FAULTs.
//   RS = 0: the structure above, unchanged.
module ot_hnx_idxn_keybuf_slice #(parameter integer RS=1)(
 input wire clk,rst_n,clear,
 input wire [2:0] strap_lane_id,
 input wire live_v,input wire[7:0]live_index,input wire[1098:0]key_in,
 input wire pre_v,input wire[7:0]pre_index,
 input wire replay_v,input wire[7:0]replay_index,
 output wire[1098:0]key_out,output reg fault
);
 wire [1279:0] wd={192'b0,key_in[1098:11]};
 wire [1279:0] rd;
 for(genvar m=0;m<5;m=m+1)begin:gm
  ot_sram_1r1w_256x256_m2_r2c2 mem(.clk(clk),.r_ce_in(pre_v),.r_addr_in(pre_index),.rd_out(rd[m*256+:256]),
   .w_ce_in(live_v),.w_addr_in(live_index),.wd_in(wd[m*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
 end
 reg[170:0]have;reg pre_q;reg[7:0]pre_iq;
`ifdef C3MUT_KB_TAG
 wire [9:0] tag={strap_lane_id,7'b0}+{2'b0,replay_index};
`else
 wire [9:0] tag={strap_lane_id,7'b0}+{2'b0,(RS==0)?replay_index:pre_iq};
`endif
 wire [1098:0] regen={rd[1087:0],tag,1'b1};
 if(RS==0)begin:gsel
  assign key_out=replay_v?regen:key_in;
 end else begin:gsel_rs
  (* keep *) reg[4:0]sel_q;                   // one copy of the registered PRE strobe per 256-bit SRAM column
`ifdef C3MUT_KB_SELREPLAY
  always @(posedge clk)sel_q<={5{replay_v}};
`else
  always @(posedge clk)sel_q<={5{pre_v}};
`endif
  // bit i uses copy (i<11 ? 0 : (i-11)/256): bits [266:0] copy 0, then one copy per 256 bits, [1098:1035] copy 4
  wire [1098:0] selv={{64{sel_q[4]}},{256{sel_q[3]}},{256{sel_q[2]}},{256{sel_q[1]}},{267{sel_q[0]}}};
  assign key_out=(selv&regen)|(~selv&key_in);
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin have<=0;pre_q<=0;pre_iq<=0;fault<=0;end
  else begin
   pre_q<=pre_v;pre_iq<=pre_index;
   if(clear)have<=0;
   else if(live_v&&live_index<=8'd170)have[live_index]<=1;
   if(live_v&&(replay_v||live_index>8'd170))fault<=1;
   if(replay_v&&(!pre_q||pre_iq!=replay_index||replay_index>8'd170||!have[replay_index]))fault<=1;
`ifndef C3MUT_KB_NOFAULT
   if(RS!=0&&pre_q&&!replay_v)fault<=1;     // RS = 1 replays on the registered PRE strobe: replay_v must match it
`endif
   if(pre_v&&(pre_index>8'd170||!have[pre_index]))fault<=1;
  end
 end
endmodule

// Composition vehicle: same public interface as the original. Each physical slice
// independently checks the identical control stream; their sticky faults are ORed.
module ot_hnx_idxn_keybuf_sliced #(parameter integer RS=0)(
 input wire clk,rst_n,clear,
 input wire live_v,input wire[7:0]live_index,input wire[8791:0]key_in,
 input wire pre_v,input wire[7:0]pre_index,
 input wire replay_v,input wire[7:0]replay_index,
 output wire[8791:0]key_out,output wire fault
);
 wire [7:0] lane_fault;
 for(genvar p=0;p<8;p=p+1)begin:gp
  ot_hnx_idxn_keybuf_slice #(.RS(RS)) u_line(.clk(clk),.rst_n(rst_n),.clear(clear),.strap_lane_id(3'(p)),
   .live_v(live_v),.live_index(live_index),.key_in(key_in[p*1099+:1099]),
   .pre_v(pre_v),.pre_index(pre_index),.replay_v(replay_v),.replay_index(replay_index),
   .key_out(key_out[p*1099+:1099]),.fault(lane_fault[p]));
 end
 assign fault=|lane_fault;
endmodule
`default_nettype wire
