`timescale 1ns/1ps
// ot_rom_16384x266_m16: ASAP7 via-programmed NOR mask ROM 16384 x 266, mux 16; layout and timing content-independent; OpenTallas tools/mem_compiler/rom_gen.py v1.0
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_rom_16384x266_m16 (
    input wire clk,
    input wire ce_in,
    input wire [13:0] addr_in,
    output wire [265:0] rd_out
);
endmodule
