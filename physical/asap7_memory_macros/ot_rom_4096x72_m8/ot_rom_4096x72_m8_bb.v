// ot_rom_4096x72_m8: ASAP7 via-programmed NOR mask ROM 4096 x 72, mux 8; layout and timing content-independent; OpenTallas tools/mem_compiler/rom_gen.py v1.0
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_rom_4096x72_m8 (
    input wire clk,
    input wire ce_in,
    input wire [11:0] addr_in,
    output wire [71:0] rd_out
);
endmodule
