`timescale 1ns/1ps
// A separate kept issue-address bank for each ROM. Captures the SAME next
// counter value on the SAME edge as the original issue counter: zero cycles.
(* keep_hierarchy = "yes" *)
module ot_s81hd_rom_addr_copy #(parameter integer BANK=0) (
    input wire clk, rst_n, clear, advance,
    input wire [11:0] next_addr,
    output wire [11:0] addr
);
    (* keep *) reg [11:0] q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) q <= 12'd0;
        else if (clear) q <= 12'd0;
        else if (advance) q <= next_addr;
`ifdef OT_S81HD_MUT_ADDR_BANK1
    assign addr = BANK == 1 ? (q ^ 12'd1) : q;
`else
    assign addr = q;
`endif
endmodule
