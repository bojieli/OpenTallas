`timescale 1ns/1ps
// Check the two row identities on a packed QDQ8 window write.  The KVT alias
// uses a saturated local row; HBM uses the absolute position modulo 128.
module ot_chip_v41x_window_block_guard #(
    parameter integer AW = 30,
    parameter integer POS_W = 21,
    parameter integer KVT_SH = 13,
    parameter integer MAX_CONTEXT = 1048576
) (
    input wire [POS_W-1:0] step_pos,
    input wire [POS_W-1:0] blk_abs_row,
    input wire [POS_W-1:0] blk_kvt_row,
    input wire [3:0] blk_idx,
    input wire [AW-1:0] kvt_base,
    input wire [AW-1:0] first_elem,
    output wire [6:0] hbm_slot,
    output wire [AW:0] expected_first,
    output wire bad
);
    wire [POS_W-1:0] expected_local =
        (blk_abs_row < POS_W'(128)) ? blk_abs_row : POS_W'(127);
    assign hbm_slot = blk_abs_row[6:0];
    assign expected_first = {1'b0, kvt_base} +
        ((AW+1)'(blk_kvt_row >> 4) << KVT_SH) +
        ((AW+1)'(blk_idx) << 9) + (AW+1)'(blk_kvt_row[3:0]);
    assign bad = blk_abs_row != step_pos ||
                 blk_abs_row >= POS_W'(MAX_CONTEXT) ||
                 blk_kvt_row != expected_local ||
                 expected_first[AW] || first_elem != expected_first[AW-1:0];
`ifndef SYNTHESIS
    initial if (AW < 30 || POS_W < 21 || KVT_SH != 13 || MAX_CONTEXT != 1048576)
        $fatal(1, "window block guard parameter contract failed");
`endif
endmodule
