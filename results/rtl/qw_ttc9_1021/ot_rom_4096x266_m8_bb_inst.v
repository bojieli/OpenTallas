`timescale 1ns/1ps
// QW-TTC9 10-21: ot_rom_4096x266_m8 blackbox (= physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_bb.v,
// same ports) plus the content-binding string parameter INSTANCE that the CALR netlist (lp9d_np/_npl) sets on the two
// calendar ROMs (calendar_m0 / calendar_m1 -> die ROM_BIND). Layout and timing are content-independent.
(* blackbox *)
module ot_rom_4096x266_m8 #(parameter INSTANCE = "") (
    input wire clk,
    input wire ce_in,
    input wire [11:0] addr_in,
    output wire [265:0] rd_out
);
endmodule
