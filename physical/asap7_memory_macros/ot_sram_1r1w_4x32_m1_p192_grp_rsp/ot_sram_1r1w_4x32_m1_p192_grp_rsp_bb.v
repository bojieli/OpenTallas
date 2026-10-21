`timescale 1ns/1ps
// ot_sram_1r1w_4x32_m1_p192_grp_rsp: ASAP7 1R1W SRAM 4 x 32, mux 1, 1 bank(s), 0 spare row(s), 0 spare IO column(s); OpenTallas tools/mem_compiler/sram_gen.py v1.0
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_sram_1r1w_4x32_m1_p192_grp_rsp (
    input wire clk,
    input wire r_ce_in,
    input wire [1:0] r_addr_in,
    output wire [31:0] rd_out,
    input wire w_ce_in,
    input wire [1:0] w_addr_in,
    input wire [31:0] wd_in,
    input wire [31:0] w_mask_in
);
endmodule
