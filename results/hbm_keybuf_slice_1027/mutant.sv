`default_nettype none
// Eight parallel instances replace one keybuf without changing any sampled edge.
// lane_id is a declared quasi-static plan strap. Five SRAMs hold one 1088-bit line;
// the last SRAM uses 64 bits. No arithmetic or reduction order changes.
module ot_hnx_idxn_keybuf_slice(
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
 wire [9:0] tag={strap_lane_id,7'b0}+{2'b0,replay_index}+10'd1;
 assign key_out=replay_v?{rd[1087:0],tag,1'b1}:key_in;
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

// Composition vehicle: same public interface as the original. Each physical slice
// independently checks the identical control stream; their sticky faults are ORed.
module ot_hnx_idxn_keybuf_sliced(
 input wire clk,rst_n,clear,
 input wire live_v,input wire[7:0]live_index,input wire[8791:0]key_in,
 input wire pre_v,input wire[7:0]pre_index,
 input wire replay_v,input wire[7:0]replay_index,
 output wire[8791:0]key_out,output wire fault
);
 wire [7:0] lane_fault;
 for(genvar p=0;p<8;p=p+1)begin:gp
  ot_hnx_idxn_keybuf_slice u_line(.clk(clk),.rst_n(rst_n),.clear(clear),.strap_lane_id(3'(p)),
   .live_v(live_v),.live_index(live_index),.key_in(key_in[p*1099+:1099]),
   .pre_v(pre_v),.pre_index(pre_index),.replay_v(replay_v),.replay_index(replay_index),
   .key_out(key_out[p*1099+:1099]),.fault(lane_fault[p]));
 end
 assign fault=|lane_fault;
endmodule
`default_nettype wire
