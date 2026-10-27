(* blackbox *) module ot_sram_1r1w_32x64_m1 (
    input  wire clk,
    input  wire r_ce_in,
    input  wire [4:0] r_addr_in,
    output reg  [63:0] rd_out,
    input  wire w_ce_in,
    input  wire [4:0] w_addr_in,
    input  wire [63:0] wd_in,
    input  wire [63:0] w_mask_in
);
endmodule
