`default_nettype none
// Opt-in NPC=2 physical ABI. Each native bit appears at exactly one real input.
// The two 128x256 SRAM masters expose WD[136:0] on W and WD[255:137] on E.
// No registers, clocks, enables, or added cycles in this adapter.
module ot_hbm_vmdel_fill_faces (
 input wire [273:0] fill_data_w,
 input wire [237:0] fill_data_e,
 output wire [511:0] fill_data_native
);
 assign fill_data_native[136:0]   = fill_data_w[136:0];
 assign fill_data_native[255:137] = fill_data_e[118:0];
 assign fill_data_native[392:256] = fill_data_w[273:137];
 assign fill_data_native[511:393] = fill_data_e[237:119];
endmodule

// This is a separate, opt-in physical type. The native 512-bit port is internal;
// the die must bind the two real buses with the published source-bit manifest.
module ot_hbm_svc_vmdel_lane_n_faces (
 input wire clk, rst_n,
 input wire [2:0] bank_id,
 input wire begin_v_i, begin_bank_i,
 input wire [15:0] begin_epoch_i,
 input wire start_i, start_bank_i,
 input wire [15:0] start_epoch_i, start_base_sector_i,
 input wire [1:0] fill_v_i, fill_bank_i,
 input wire [11:0] fill_slot_i,
 input wire [31:0] fill_epoch_i,
 input wire [273:0] fill_data_w,
 input wire [237:0] fill_data_e,
 input wire [7:0] full0_all, full1_all, pcbad_all,
 output wire full0, full1, pcbad,
 output wire [1:0] block_ready,
 output wire busy, fault,
 output wire [280:0] dq
);
 wire [511:0] fill_data_native;
 ot_hbm_vmdel_fill_faces u_fill (
  .fill_data_w(fill_data_w), .fill_data_e(fill_data_e),
  .fill_data_native(fill_data_native)
 );
 ot_hbm_svc_vmdel_lane_n #(.NPC(2)) u_native (
  .clk(clk), .rst_n(rst_n), .bank_id(bank_id),
  .begin_v_i(begin_v_i), .begin_bank_i(begin_bank_i), .begin_epoch_i(begin_epoch_i),
  .start_i(start_i), .start_bank_i(start_bank_i), .start_epoch_i(start_epoch_i),
  .start_base_sector_i(start_base_sector_i),
  .fill_v_i(fill_v_i), .fill_bank_i(fill_bank_i), .fill_slot_i(fill_slot_i),
  .fill_epoch_i(fill_epoch_i), .fill_data_i(fill_data_native),
  .full0_all(full0_all), .full1_all(full1_all), .pcbad_all(pcbad_all),
  .full0(full0), .full1(full1), .pcbad(pcbad), .block_ready(block_ready),
  .busy(busy), .fault(fault), .dq(dq)
 );
endmodule
`default_nettype wire
