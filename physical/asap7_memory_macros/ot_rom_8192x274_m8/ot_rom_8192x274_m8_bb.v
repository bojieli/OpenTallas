`timescale 1ns/1ps
// ot_rom_8192x274_m8: ASAP7 via-programmed NOR mask ROM 8192 x 274, mux 8; layout and timing content-independent; OpenTallas tools/mem_compiler/rom_gen.py v1.0
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_rom_8192x274_m8 (
    input wire clk,
    input wire ce_in,
    input wire [12:0] addr_in,
    output wire [273:0] rd_out
);
endmodule
