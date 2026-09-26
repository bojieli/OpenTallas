`timescale 1ns/1ps
// ot_sram_1rw_256x64_m4_r2c2: ASAP7 1RW SRAM 256 x 64, mux 4, 1 bank(s), 2 spare row(s), 2 spare IO column(s); OpenTallas tools/mem_compiler/sram_gen.py v1.0
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_sram_1rw_256x64_m4_r2c2 (
    input wire clk,
    input wire ce_in,
    input wire we_in,
    input wire [7:0] addr_in,
    input wire [63:0] wd_in,
    input wire [63:0] w_mask_in,
    output wire [63:0] rd_out,
    input wire [1:0] rr_en,
    input wire [11:0] rr_addr,
    input wire [1:0] cr_en,
    input wire [11:0] cr_sel
);
endmodule
