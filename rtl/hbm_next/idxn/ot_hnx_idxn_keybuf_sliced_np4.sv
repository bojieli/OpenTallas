`default_nettype none
// Opt-in quarter replay buffer. Same RS=0 public sampled edges as the packed
// buffer, but each 1088-bit line owns five 256-bit SRAMs (last 192 bits unused).
// Four active slices therefore use 20 SRAMs instead of 17 packed SRAMs. Existing
// fixed-eight composition and packed implementations remain unchanged.
module ot_hnx_idxn_keybuf_sliced_np4 #(
 parameter integer NP=4, RS=0
)(
 input wire clk,rst_n,clear,input wire[2:0]pbase,
 input wire live_v,input wire[7:0]live_index,input wire[NP*1099-1:0]key_in,
 input wire pre_v,input wire[7:0]pre_index,
 input wire replay_v,input wire[7:0]replay_index,
 output wire[NP*1099-1:0]key_out,output wire fault
);
 // Unsupported configurations fail elaboration.  RS is passed to every slice (DIE-HBM-61/RTL-C3 11-03): RS=1 is the
 // packed RS=1 contract (registered PRE strobe select, per-column copies), the hardened slice form; RS=0 unchanged.
 if(RS!=0&&RS!=1)begin:g_unsupported_rs
  ERROR_keybuf_sliced_np4_requires_RS_zero_or_one invalid_configuration();
 end
 if(NP!=4 && NP!=8)begin:g_unsupported_np
  ERROR_keybuf_sliced_np4_requires_NP_four_or_eight invalid_configuration();
 end
 wire[NP-1:0]lane_fault;
 for(genvar p=0;p<NP;p=p+1)begin:gp
  wire[2:0]lane_id=pbase+3'(p);
  ot_hnx_idxn_keybuf_slice #(.RS(RS)) u_line(.clk(clk),.rst_n(rst_n),.clear(clear),.strap_lane_id(lane_id),
   .live_v(live_v),.live_index(live_index),.key_in(key_in[p*1099+:1099]),
   .pre_v(pre_v),.pre_index(pre_index),.replay_v(replay_v),.replay_index(replay_index),
   .key_out(key_out[p*1099+:1099]),.fault(lane_fault[p]));
 end
 assign fault=|lane_fault;
endmodule
`default_nettype wire
