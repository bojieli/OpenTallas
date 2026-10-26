`timescale 1ns/1ps
// TOK-QW xdie_bound BENCH SHIM (not die RTL): the bound compute d2d_rom (ot_qwen_d2d_safe7.sv u_sram) instantiates
// ot_sram_1r1w_64x137_m1_r2c2_p192, which no file on main defines (bound_r8 verify_report: AS-BUILT RTL DEFECT; the macro
// is d2d_sram_1r1w_64x137_m1_r2c2_p192).  This alias forwards every pin to that macro model so the master elaborates.
module ot_sram_1r1w_64x137_m1_r2c2_p192 (input wire clk, input wire r_ce_in, input wire [5:0] r_addr_in, output wire [136:0] rd_out,
    input wire w_ce_in, input wire [5:0] w_addr_in, input wire [136:0] wd_in, input wire [136:0] w_mask_in,
    input wire [1:0] rr_en, input wire [11:0] rr_addr, input wire [1:0] cr_en, input wire [15:0] cr_sel);
    d2d_sram_1r1w_64x137_m1_r2c2_p192 u (.clk(clk), .r_ce_in(r_ce_in), .r_addr_in(r_addr_in), .rd_out(rd_out), .w_ce_in(w_ce_in),
        .w_addr_in(w_addr_in), .wd_in(wd_in), .w_mask_in(w_mask_in), .rr_en(rr_en), .rr_addr(rr_addr), .cr_en(cr_en), .cr_sel(cr_sel));
endmodule
