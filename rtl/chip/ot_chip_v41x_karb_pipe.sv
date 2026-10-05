`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// N-stage register delay line (a registered trunk repeater chain) for the
// pipelined local K arbitration (ot_chip_v41x_hbm_karb_pipe).  Each stage is
// one register a trunk segment ends in; V bits (the low V bits: valids,
// pulses) reset, the rest do not.  N = 0 is a wire.
// ---------------------------------------------------------------------------
module ot_chip_v41x_karb_pipe #(
    parameter integer W = 8,
    parameter integer V = 1,
    parameter integer N = 1
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (N == 0) begin : g_wire
        assign q = d;
    end else begin : g_regs
        if (V > 0) begin : g_v
            reg [V-1:0] sv [0:N-1];
            integer i;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) for (i = 0; i < N; i = i + 1) sv[i] <= '0;
                else begin
                    sv[0] <= d[V-1:0];
                    for (i = 1; i < N; i = i + 1) sv[i] <= sv[i-1];
                end
            assign q[V-1:0] = sv[N-1];
        end
        if (W > V) begin : g_d
            reg [W-V-1:0] sd [0:N-1];
            integer j;
            always @(posedge clk) begin
                sd[0] <= d[W-1:V];
                for (j = 1; j < N; j = j + 1) sd[j] <= sd[j-1];
            end
            assign q[W-1:V] = sd[N-1];
        end
    end endgenerate
endmodule
