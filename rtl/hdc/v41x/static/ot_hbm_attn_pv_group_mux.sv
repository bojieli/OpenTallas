`timescale 1ns/1ps
`default_nettype none
// Physical leaf request: eight tile-local512b+16flag buses in one fixed
// tile%4 affinity group. Select exactly tile=4*block+group. Combinational;
// no hidden pipeline, clock, extra native port, changed record or format.
module ot_hbm_attn_pv_group_mux(
 input wire[4095:0]tile_data,input wire[127:0]tile_flags,
 input wire[2:0]block_select,
 output wire[511:0]bankpair_data,output wire[15:0]bankpair_flags
);
 assign bankpair_data=tile_data[int'(block_select)*512+:512];
 assign bankpair_flags=tile_flags[int'(block_select)*16+:16];
endmodule
`default_nettype wire
