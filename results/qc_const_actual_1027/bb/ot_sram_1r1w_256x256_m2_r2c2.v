(* blackbox *) module ot_sram_1r1w_256x256_m2_r2c2 (
    input  wire clk,
    input  wire r_ce_in,
    input  wire [7:0] r_addr_in,
    output reg  [255:0] rd_out,
    input  wire w_ce_in,
    input  wire [7:0] w_addr_in,
    input  wire [255:0] wd_in,
    input  wire [255:0] w_mask_in,
    input  wire [1:0] rr_en,
    input  wire [13:0] rr_addr,
    input  wire [1:0] cr_en,
    input  wire [15:0] cr_sel
);
endmodule
