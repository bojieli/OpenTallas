`timescale 1ns/1ps
// Timing probes for the three pieces of the pipelined lane's accumulate adder.
// Each registers its inputs and its result so that OpenSTA reports exactly one
// piece's combinational depth between two flip-flops.
module ot_probe_acc_align (
    input  wire clk,
    input  wire rst_n,
    input  wire [31:0] acc_in,
    input  wire g_zero,
    input  wire g_sign,
    input  wire [47:0] g_mag,
    input  wire [11:0] g_pow,
    output reg  [118:0] q
);
    reg [31:0] a_r; reg z_r, s_r; reg [47:0] m_r; reg [11:0] p_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin a_r<=32'b0; z_r<=1'b0; s_r<=1'b0; m_r<=48'b0; p_r<=12'b0; q<=119'b0; end
        else begin
            a_r<=acc_in; z_r<=g_zero; s_r<=g_sign; m_r<=g_mag; p_r<=g_pow;
            q <= ot_a3_lane_pkg::acc_align(a_r, z_r, s_r, m_r, p_r);
        end
    end
endmodule

module ot_probe_acc_sum_normalise (
    input  wire clk,
    input  wire rst_n,
    input  wire [118:0] d,
    output reg  [65:0]  q
);
    reg [118:0] r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin r<=119'b0; q<=66'b0; end
        else begin r<=d; q <= ot_a3_lane_pkg::acc_sum_normalise(r); end
    end
endmodule

module ot_probe_acc_round_pack (
    input  wire clk,
    input  wire rst_n,
    input  wire [65:0] d,
    output reg  [33:0] q
);
    reg [65:0] r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin r<=66'b0; q<=34'b0; end
        else begin r<=d; q <= ot_a3_lane_pkg::acc_round_pack(r); end
    end
endmodule
