`timescale 1ns/1ps
// ot_sram_1r1w_64x137_m1_r2c2_p192: name alias of the hard macro d2d_sram_1r1w_64x137_m1_r2c2_p192
// (physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p192, identical ports).
// ELEM-QK 10-24: ot_qwen_d2d_safe7.sv (ot_qkvd_llr_replay_sram_leaf_s7) instantiates this name, which no file defined
// (asbuilt_tie lint_waive "AS-BUILT RTL DEFECT"); the closed ucie_kv d2d view was built from a kit copy of the same
// macro.  Pure wiring (exact): G3 kits of partitions holding the d2d replay store (QC glue) then place the real macro.
module ot_sram_1r1w_64x137_m1_r2c2_p192 (
    input  wire         clk,
    input  wire         r_ce_in,
    input  wire [5:0]   r_addr_in,
    output wire [136:0] rd_out,
    input  wire         w_ce_in,
    input  wire [5:0]   w_addr_in,
    input  wire [136:0] wd_in,
    input  wire [136:0] w_mask_in,
    input  wire [1:0]   rr_en,
    input  wire [11:0]  rr_addr,
    input  wire [1:0]   cr_en,
    input  wire [15:0]  cr_sel
);
    d2d_sram_1r1w_64x137_m1_r2c2_p192 u_m (
        .clk(clk), .r_ce_in(r_ce_in), .r_addr_in(r_addr_in), .rd_out(rd_out), .w_ce_in(w_ce_in),
        .w_addr_in(w_addr_in), .wd_in(wd_in), .w_mask_in(w_mask_in), .rr_en(rr_en), .rr_addr(rr_addr),
        .cr_en(cr_en), .cr_sel(cr_sel));
endmodule
