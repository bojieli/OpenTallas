`timescale 1ns/1ps
// reset leaf (moved from ot_rom_oneshot_die_m.sv, el1011-q-coll 2026-10-11): async assert, 2-flop synchronous release
module ot_coll_rst_leaf (input wire clk, input wire arst_n, output wire q);
    (* async_reg = "true" *) reg [1:0] s;
    always @(posedge clk or negedge arst_n) if (!arst_n) s <= 2'b00; else s <= {s[0], 1'b1};
    assign q = s[1];
endmodule
