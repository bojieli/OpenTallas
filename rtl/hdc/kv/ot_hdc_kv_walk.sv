`timescale 1ns/1ps
// Line walker of the KV streaming engine: steps (r, k, jh) through one
// KV-sourced op's lines in the matrix engine's consumption order -- round r,
// then k, then jh = j >> jsh (the slots that share one KV word) -- and flags
// the op's last line.  Three copies run in ot_hdc_kv_stream: the completion
// pointer and the consumer (the fetcher steps by blocks and has its own loop).
module ot_hdc_kv_walk #(
    parameter integer NW = 16,
    parameter integer LIL = 3            // log2(interleave)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          load,           // start an op at line (0, 0, 0)
    input  wire          step,           // advance one line
    input  wire [NW-1:0] tiles,          // rounds
    input  wire [NW-1:0] kk,             // k per round
    input  wire [2:0]    jsh,
    output reg  [NW-1:0] r,
    output reg  [NW-1:0] k,
    output reg  [LIL-1:0] jh,
    output wire          last,
    output wire          rend            // the current line is its round's last
);
    reg [NW-1:0]  r_end, k_end;
    reg [LIL-1:0] jh_end;
    reg           r_l, k_l, jh_l;
    assign last = r_l && k_l && jh_l;
    assign rend = k_l && jh_l;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            r <= 0; k <= 0; jh <= 0; r_l <= 1'b0; k_l <= 1'b0; jh_l <= 1'b0;
            r_end <= 0; k_end <= 0; jh_end <= 0;
        end else if (load) begin
            r <= 0; k <= 0; jh <= 0;
            r_end <= tiles - 1'b1; k_end <= kk - 1'b1;
            jh_end <= (1 << (LIL - jsh)) - 1;
            r_l <= (tiles == 1); k_l <= (kk == 1); jh_l <= (jsh == LIL);
        end else if (step) begin
            if (!jh_l) begin
                jh <= jh + 1'b1; jh_l <= (jh + 1'b1 == jh_end);
            end else begin
                jh <= 0; jh_l <= (jh_end == 0);
                if (!k_l) begin
                    k <= k + 1'b1; k_l <= (k + 1'b1 == k_end);
                end else begin
                    k <= 0; k_l <= (k_end == 0);
                    r <= r + 1'b1; r_l <= (r + 1'b1 == r_end);
                end
            end
        end
    end
endmodule
