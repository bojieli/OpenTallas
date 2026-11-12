`timescale 1ns/1ps
// bench-only behavioural 1R1W macros (registered read, one clock), same ports as the sram_gen views
module ot_sram_1r1w_64x272_m1_g272 (input wire clk, input wire r_ce_in, input wire [5:0] r_addr_in, output reg [271:0] rd_out,
    input wire w_ce_in, input wire [5:0] w_addr_in, input wire [271:0] wd_in, input wire w_mask_in);
    reg [271:0] m [0:63];
    always @(posedge clk) begin
        if (r_ce_in) rd_out <= m[r_addr_in];
        if (w_ce_in && w_mask_in) m[w_addr_in] <= wd_in;
    end
endmodule
module ot_sram_1r1w_32x272_m1_g272 (input wire clk, input wire r_ce_in, input wire [4:0] r_addr_in, output reg [271:0] rd_out,
    input wire w_ce_in, input wire [4:0] w_addr_in, input wire [271:0] wd_in, input wire w_mask_in);
    reg [271:0] m [0:31];
    always @(posedge clk) begin
        if (r_ce_in) rd_out <= m[r_addr_in];
        if (w_ce_in && w_mask_in) m[w_addr_in] <= wd_in;
    end
endmodule
