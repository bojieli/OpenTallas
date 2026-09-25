`timescale 1ns/1ps
// ot_sram_2rw_512x64_m4_r2c2: ASAP7 2RW SRAM 512 x 64, mux 4, 1 bank(s), 2 spare row(s), 2 spare IO column(s); OpenTallas tools/mem_compiler/sram_gen.py v1.0
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_sram_2rw_512x64_m4_r2c2 (
    input wire clk,
    input wire a_ce_in,
    input wire a_we_in,
    input wire [8:0] a_addr_in,
    input wire [63:0] a_wd_in,
    input wire [63:0] a_w_mask_in,
    output wire [63:0] a_rd_out,
    input wire b_ce_in,
    input wire b_we_in,
    input wire [8:0] b_addr_in,
    input wire [63:0] b_wd_in,
    input wire [63:0] b_w_mask_in,
    output wire [63:0] b_rd_out,
    input wire [1:0] rr_en,
    input wire [13:0] rr_addr,
    input wire [1:0] cr_en,
    input wire [11:0] cr_sel
);
endmodule
