`timescale 1ns/1ps
// d2d_sram_1r1w_64x137_m1_r2c2_p288: ASAP7 1R1W SRAM 64 x 137, mux 1, 1 bank(s), 2 spare row(s), 2 spare IO column(s); OpenTallas tools/mem_compiler/sram_gen.py v1.0+aligned-v2+p288
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module d2d_sram_1r1w_64x137_m1_r2c2_p288 (
    input wire clk,
    input wire r_ce_in,
    input wire [5:0] r_addr_in,
    output wire [136:0] rd_out,
    input wire w_ce_in,
    input wire [5:0] w_addr_in,
    input wire [136:0] wd_in,
    input wire [136:0] w_mask_in,
    input wire [1:0] rr_en,
    input wire [11:0] rr_addr,
    input wire [1:0] cr_en,
    input wire [15:0] cr_sel
);
endmodule
