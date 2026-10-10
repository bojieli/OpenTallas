`timescale 1ps/1fs
`default_nettype none
// hbm-system 2026-10-08: the K-port sector address of a stream-PC (pc, bank, row, column) location.
//
// The die's stream service talks to the HBM3E PHY + controller abstract (ot_hbm3e_phy_v41x_aw30_e8p5) through
// request-level K ports: one valid/ready port per pseudo-channel carrying a 30-bit SECTOR address s.  The
// controller decodes s with permutation interleaving (rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv, NPC 32, LPC 5):
//   pc   = (s[6:2] ^ s[11:7] ^ s[16:12])            bank = {(s[14:12] ^ row[4:2]), (s[1:0] ^ row[1:0])}
//   col  = s[11:7]                                   row  = s >> 15
// ot_hbm_accel_dskv_wb (and the stream PCs it mirrors) name a sector by (pc, bank5, row, col5).  This is the
// inverse: the unique s with those four fields.  Every K-port writer AND reader of the KV / CKV / index-key
// regions uses this one map, so a written row is read back at the same DRAM location.
// fault = the row does not fit the 30-bit address (row >= 2^15).
module ot_hbm_kport_map (
  input  wire [4:0]  pc, input wire [4:0] bank, input wire [18:0] row, input wire [4:0] col,
  output wire [29:0] s, output wire fault
);
  wire [2:0] bhi = bank[4:2] ^ row[4:2];
  wire [1:0] blo = bank[1:0] ^ row[1:0];
  wire [4:0] hi5 = {row[1:0], bhi};                  // s[16:12]
  assign s = {row[14:0], bhi, col, pc ^ col ^ hi5, blo};
  assign fault = |row[18:15];
endmodule
`default_nettype wire
