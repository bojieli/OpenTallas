`default_nettype none
// TOK-HBM-3 2026-10-28: IDXN key-replay control provider of ONE quarter (closes the 7 hb_idx__s_<q> keybuf control ports
// of the unified 4-role HBM top: clear, live_v/_index, pre_v/_index, replay_v/_index). NO new logic: it is the exact
// class decode of the IDXQ quad client (codex/p3-compiler-2018 e938fd6db rtl/hbm_next/idxq/ot_hnx_idxq_client_quad.sv,
// lines 72-75): row 0 key beats are LIVE (scored and captured), rows >= 1 key beats are REPLAY (same index), PRE is the
// calendar's replay-read class (one edge ahead), the buffer clears on the record's frame_start. Wires only: every input
// leaves a flop of the quarter calendar copy (ot_hbm_idx_qctl_static / ot_hnx_idxq_qctl) and every output lands on the
// keybuf's SRAM ports or fault flops, so 0 added edges and no new timing stage.
// SOURCES: d4g qctl (ot_hbm_idx_qctl_static, the current native top): key_v = key_slot, key_row = 0, pre_v = 0 -> every
// record is 1 row: live capture only, never replay (exact, the keybuf is a pass-through). IDXQ qctl (N-row records):
// key_v / key_row / pre_v / pre_index from its KEY and PRE classes. Static schedule: a wrong schedule FAULTs in the keybuf.
module ot_hnx_idxn_kb_ctl(
 input wire frame_start,
 input wire key_v,input wire[7:0]key_index,input wire[4:0]key_row,
 input wire pre_v_in,input wire[7:0]pre_index_in,
 output wire clear,
 output wire live_v,output wire[7:0]live_index,
 output wire pre_v,output wire[7:0]pre_index,
 output wire replay_v,output wire[7:0]replay_index
);
 assign clear=frame_start;
 assign live_v=key_v&&key_row==5'd0;
 assign replay_v=key_v&&key_row!=5'd0;
 assign live_index=key_index;
 assign replay_index=key_index;
 assign pre_v=pre_v_in;
 assign pre_index=pre_index_in;
endmodule
`default_nettype wire
