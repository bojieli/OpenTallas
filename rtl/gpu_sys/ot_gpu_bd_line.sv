`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_bd_line: weight-line assembly for the block-dot tensor core
// (rtl/gpu/ot_gpu_sm_bd.sv) of a DeepSeek-V4.1 HBM comparator SM.  The
// TMA-style bulk copy streams 32-byte sectors in order; every 9 sectors form
// one block-scaled MMA line: sectors 0..7 = bd-lane j's 32 codes (E4M3 bytes,
// or E2M1 in the low nibble), sector 8 = the 8 lanes' block exponents as
// little-endian int16 words holding the sign-extended 10-bit exponent.  Output
// lane j = {we[9:0], wq[255:0]} as ot_gpu_sm_bd's w_data expects.
// ENABLE = 0: inert, every output 0.
// ---------------------------------------------------------------------------
module ot_gpu_bd_line #(
    parameter integer ENABLE = 0,
    parameter integer LB     = 8
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                s_valid,
    output wire                s_ready,
    input  wire [255:0]        s_data,
    output wire                w_valid,
    input  wire                w_ready,
    output wire [LB*266-1:0]   w_data
);
generate if (ENABLE == 0) begin : g_off
    assign s_ready = 1'b0; assign w_valid = 1'b0; assign w_data = {LB*266{1'b0}};
end else begin : g_on
    reg [255:0] codes [0:LB-1];
    reg [3:0]   k;
    reg         full;
    reg [LB*266-1:0] line;
    assign s_ready = !full;
    assign w_valid = full;
    assign w_data = line;
    integer j;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin k <= 0; full <= 1'b0; end
        else begin
            if (full && w_ready) full <= 1'b0;
            if (s_valid && !full) begin
                if (k < LB) begin codes[k[2:0]] <= s_data; k <= k + 1'b1; end
                else begin
                    for (j = 0; j < LB; j = j + 1)
                        line[j*266 +: 266] <= {s_data[j*16 +: 10], codes[j]};
                    full <= 1'b1; k <= 0;
                end
            end
        end
    end
end endgenerate
endmodule
