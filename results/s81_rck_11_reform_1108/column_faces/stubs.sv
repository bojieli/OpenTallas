`timescale 1ns/1ps
// bench-only behavioural views (identical in the reference and the new copy)
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
// Chien/Forney macro stand-in: a registered, input-sensitive function (both copies identical, so any change in the
// time or value of k_* at the tile reaches dout and the outputs).
module ot_s81_kp4_dchn #(parameter integer MUT = 0, parameter integer ROOT_COUNT_SPLIT = 0) (
    input wire clk, input wire rst_n, input wire [3:0] k_v, input wire [309:0] k_lo, input wire [4:0] k_L, input wire k_any,
    output reg [543:0] cw_q, output reg [7:0] apply, output reg o_unc, output reg [4:0] o_ne, output reg fs,
    output reg [31:0] n_corr, n_unc);
    reg [309:0] h;
    always @(posedge clk) begin
        h <= k_v[0] ? (k_lo ^ {k_lo[0], k_lo[309:1]}) : {h[0], h[309:1]};
        cw_q <= {h[233:0], h} ^ {539'd0, k_L} ^ {543'd0, k_any};
        apply <= {k_v, k_L[3:0]} ^ h[7:0];
        o_unc <= k_any ^ h[8]; o_ne <= k_L ^ h[13:9]; fs <= k_v[1];
        if (!rst_n) begin n_corr <= 0; n_unc <= 0; end
        else begin if (k_v[2]) n_corr <= n_corr + k_L; if (k_v[3] && k_any) n_unc <= n_unc + 1; end
    end
endmodule
