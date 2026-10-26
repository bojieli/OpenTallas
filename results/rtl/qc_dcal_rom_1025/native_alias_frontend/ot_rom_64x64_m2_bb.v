`timescale 1ns/1ps
// ot_rom_64x64_m2: ASAP7 via-programmed NOR mask ROM 64 x 64, mux 2; layout and timing content-independent; OpenTallas tools/mem_compiler/rom_gen.py v1.0+aligned-v2
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_rom_64x64_m2 #(parameter VIAMAP = "", parameter INSTANCE = "") (
    input wire clk,
    input wire ce_in,
    input wire [5:0] addr_in,
    output wire [63:0] rd_out
);
endmodule
