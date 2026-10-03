`timescale 1ns/1ps
// Full-bundle return merge. Sources MUST hold valid and their entire bundle
// until in_ready. Selection is frozen on the first stalled offer, even if a
// higher-priority source arrives later. No truncation/retagging/ownership
// allocation occurs here. Sizing: tools/hbm_held_return_model.py.
// Replace existing RR pointer/mux once: +IW+1 FF, zero payload FF, no extra
// unstalled edge, one output per edge. Physical clock/home not qualified.
module ot_gpu_held_return_merge #(
    parameter integer ENABLE = 0,
    parameter integer N = 2,
    parameter integer W = 291,
    parameter integer IW = (N > 1) ? $clog2(N) : 1
)(
    input wire clk, rst_n,
    input wire [N-1:0] in_valid,
    output wire [N-1:0] in_ready,
    input wire [N*W-1:0] in_payload,
    output wire out_valid,
    input wire out_ready,
    output wire [W-1:0] out_payload,
    output wire [IW-1:0] out_index
);
    initial begin
        if (N < 1 || W < 1 || IW < ((N > 1) ? $clog2(N) : 1))
            $fatal(1, "invalid held return geometry");
    end
    generate if (ENABLE == 0) begin : g_off
        assign in_ready = '0;
        assign out_valid = 1'b0;
        assign out_payload = '0;
        assign out_index = '0;
    end else begin : g_on
        reg [IW-1:0] cursor, held_index;
        reg held;
        reg [IW-1:0] chosen;
        reg found;
        reg [N-1:0] ready_bits;
        integer k, candidate;
        always @* begin
            chosen = held_index;
            found = held && in_valid[held_index];
            if (!held) begin
                chosen = '0;
                found = 1'b0;
                for (k = N-1; k >= 0; k = k-1) begin
                    candidate = (integer'(cursor) + k) % N;
                    if (in_valid[candidate]) begin
                        chosen = IW'(candidate);
                        found = 1'b1;
                    end
                end
            end
            ready_bits = '0;
            if (rst_n && found && out_ready) ready_bits[chosen] = 1'b1;
        end
        assign in_ready = ready_bits;
        assign out_valid = rst_n && found;
        assign out_index = chosen;
        assign out_payload = found ? in_payload[integer'(chosen)*W +: W] : '0;
        always @(posedge clk) begin
            if (!rst_n) begin
                cursor <= '0;
                held_index <= '0;
                held <= 1'b0;
            end else if (out_valid && out_ready) begin
                cursor <= (integer'(chosen) == N-1) ? '0 : chosen + 1'b1;
                held <= 1'b0;
            end else if (out_valid && !held) begin
                held <= 1'b1;
                held_index <= chosen;
            end
        end
    end endgenerate
endmodule
