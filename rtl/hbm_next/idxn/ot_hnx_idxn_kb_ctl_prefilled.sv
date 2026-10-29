`default_nettype none
// Both key cohorts are preloaded before row0. The actual provider must issue
// prefill_clear before loading; record frame_start MUST NOT erase the SRAM.
// The matched calendar profile supplies PRE for row0 as well as later rows.
module ot_hnx_idxn_kb_ctl_prefilled(
 input wire prefill_clear,
 input wire key_v,input wire[7:0]key_index,
 input wire pre_v_in,input wire[7:0]pre_index_in,
 output wire clear,live_v,output wire[7:0]live_index,
 output wire pre_v,output wire[7:0]pre_index,
 output wire replay_v,output wire[7:0]replay_index
);
 assign clear=prefill_clear;
 assign live_v=1'b0;assign live_index=8'd0;
 assign pre_v=pre_v_in;assign pre_index=pre_index_in;
 assign replay_v=key_v;assign replay_index=key_index;
endmodule
`default_nettype wire
