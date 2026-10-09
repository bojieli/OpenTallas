`timescale 1ns/1ps
// ot_dsrom_mtp_skid: 2-entry FIFO used on the valid / ready side of the MTP blocks (stream mtp-rom, 2026-10-08).
// in_ready and out_valid come straight from the count flops (no input-to-output combinational path); full rate.
// OREG 1: out_data also straight from a flop (an output register + one skid register; no read mux at the pins).
module ot_dsrom_mtp_skid #(parameter integer W = 32, parameter integer OREG = 0) (
    input  wire         clk,
    input  wire         rst_n,            // synchronous, active low
    input  wire         in_valid,
    output wire         in_ready,
    input  wire [W-1:0] in_data,
    output wire         out_valid,
    input  wire         out_ready,
    output wire [W-1:0] out_data
);
generate if (OREG) begin : g_oreg
    reg [W-1:0] o_d, s_d; reg o_v, s_v;
    assign in_ready = rst_n && !s_v;
    assign out_valid = o_v;
    assign out_data = o_d;
    wire push = in_valid && in_ready;
    wire take = !o_v || out_ready;                 // the output register is free this cycle
    always @(posedge clk) begin
        if (!rst_n) begin o_v <= 1'b0; s_v <= 1'b0; end
        else if (take) begin
            if (s_v) begin o_v <= 1'b1; s_v <= push; end
            else o_v <= push;
        end else if (push) s_v <= 1'b1;
        if (take) o_d <= s_v ? s_d : in_data;
        if (push && !(take && !s_v)) s_d <= in_data;
    end
end else begin : g_mux
    reg [W-1:0] m [0:1];
    reg [1:0] n; reg r, w;
    assign in_ready = rst_n && n != 2'd2;
    assign out_valid = n != 2'd0;
    assign out_data = m[r];
    wire push = in_valid && in_ready, pop = out_valid && out_ready;
    always @(posedge clk) begin
        if (push) m[w] <= in_data;
        if (!rst_n) begin n <= 2'd0; r <= 1'b0; w <= 1'b0; end
        else begin
            if (push) w <= ~w;
            if (pop) r <= ~r;
            n <= n + (push ? 2'd1 : 2'd0) - (pop ? 2'd1 : 2'd0);
        end
    end
end endgenerate
endmodule
