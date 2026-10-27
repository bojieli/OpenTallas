(* blackbox *) module ot_sram_1r1w2c_128x64_m1 (
    input  wire wclk,
    input  wire rclk,
    input  wire r_ce_in,
    input  wire [6:0] r_addr_in,
    output reg  [63:0] rd_out,
    input  wire w_ce_in,
    input  wire [6:0] w_addr_in,
    input  wire [63:0] wd_in,
    input  wire [63:0] w_mask_in
);
endmodule
