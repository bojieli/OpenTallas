`timescale 1ns/1ps
// bench-only behavioural SRAM views (identical in the reference and the new copy; from results/s81_rck_11_reform_1108/stubs.sv)
module ot_sram_1r1w2c_64x546_m1 (input wire wclk, input wire rclk, input wire r_ce_in, input wire [5:0] r_addr_in,
    output reg [545:0] rd_out, input wire w_ce_in, input wire [5:0] w_addr_in, input wire [545:0] wd_in, input wire [545:0] w_mask_in);
    reg [545:0] m [0:63];
    always @(posedge wclk) if (w_ce_in) m[w_addr_in] <= (m[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in);
    always @(posedge rclk) if (r_ce_in) rd_out <= m[r_addr_in];
endmodule
module ot_sram_1r1w_32x546_m1 (input wire clk, input wire r_ce_in, input wire [4:0] r_addr_in, output reg [545:0] rd_out,
    input wire w_ce_in, input wire [4:0] w_addr_in, input wire [545:0] wd_in, input wire [545:0] w_mask_in);
    reg [545:0] m [0:31];
    always @(posedge clk) if (w_ce_in) m[w_addr_in] <= (m[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in);
    always @(posedge clk) if (r_ce_in) rd_out <= m[r_addr_in];
endmodule
