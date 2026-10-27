`default_nettype none
// Native quarter-scorer key replay: four 1099-bit PC lines, not query data.
// half selects original stack ports 0..3 or 4..7; it is a static die strap.
// Controls are the local IDXN calendar stream. No cycles are added here.
module ot_hnx_idxn_keybuf_quarter(
 input wire clk,rst_n,clear,half,
 input wire live_v,input wire[7:0]live_index,input wire[4395:0]key_in,
 input wire pre_v,input wire[7:0]pre_index,
 input wire replay_v,input wire[7:0]replay_index,
 output wire[4395:0]key_out,output wire fault
);
 wire[3:0] lane_fault;
 for(genvar p=0;p<4;p=p+1)begin:gp
  wire[2:0] pc={half,2'(p)};
  ot_hnx_idxn_keybuf_slice u_line(.clk(clk),.rst_n(rst_n),.clear(clear),.strap_lane_id(pc),
   .live_v(live_v),.live_index(live_index),.key_in(key_in[p*1099+:1099]),
   .pre_v(pre_v),.pre_index(pre_index),.replay_v(replay_v),.replay_index(replay_index),
   .key_out(key_out[p*1099+:1099]),.fault(lane_fault[p]));
 end
 assign fault=|lane_fault;
endmodule
`default_nettype wire
