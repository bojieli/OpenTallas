`default_nettype none
// Exact key-line adapter for ot_hbm_idx_client_static_quad's released 2-stack,
// 4-quarter key ABI. All clocks are the one die clock. Only the key path is here;
// IDXN calendar controls must be bound by the composing parent, never tied off.
module ot_hnx_idxn_quad_key_replay(
 input wire clk,rst_n,
 input wire[3:0] clear,live_v,pre_v,replay_v,
 input wire[31:0] live_index,pre_index,replay_index,
 input wire[17583:0] key_in,
 output wire[17583:0] key_out,
 output wire[3:0] fault
);
 // Matches QS=4'b1100,QH=4'b1010 in ot_hbm_idx_client_static_quad.
 for(genvar q=0;q<4;q=q+1)begin:gq
  localparam integer STACK=q/2, HALF=q%2;
  ot_hnx_idxn_keybuf_quarter keybuf(.clk(clk),.rst_n(rst_n),.clear(clear[q]),.half(1'(HALF)),
   .live_v(live_v[q]),.live_index(live_index[q*8+:8]),
   .key_in(key_in[STACK*8792+HALF*4396+:4396]),
   .pre_v(pre_v[q]),.pre_index(pre_index[q*8+:8]),
   .replay_v(replay_v[q]),.replay_index(replay_index[q*8+:8]),
   .key_out(key_out[STACK*8792+HALF*4396+:4396]),.fault(fault[q]));
 end
endmodule
`default_nettype wire
