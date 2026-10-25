`timescale 1ns/1ps
`default_nettype none
// HBM-BIND2 (2026-10-25): scheduled multi-beat lane (COORD 2026-10-25 00:21 ruling 1: hub -> root L74 "RTL multi-beat,
// scheduled 2-3 beats").  A W-bit word qualified by NV valid bits crosses a lane of LW = ceil(W / BEATS) wires in BEATS
// consecutive beats.  Static schedule, no flow control: the compiler spaces the words of one group >= BEATS edges apart
// (a closer word is a schedule fault: sticky `fault` on both ends, never stalled or re-sent).
//
//   ot_hbm_b2_beat_tx (source partition, e.g. NW_hub / NE_hub):  edge t: v (= |vin) and d presented
//       edge t+1 .. t+BEATS : beat k = d[k*LW +: LW] on ld (registered), lv = 1 with beat 0 only.
//   ot_hbm_b2_beat_rx (sink partition, e.g. root): beat 0 seen with lv at edge s, beat BEATS-1 at s+BEATS-1;
//       edge s+BEATS : v = 1 and d = the word (registered, held until the next word).
//   word latency (vin -> v) = BEATS + 1 edges + the lane's own cycles (plan latency.lanes); BEATS = 1 is a plain
//   2-register pipe of the word (no width saving).
// The valid bits are carried INSIDE the word (vin is also d's low NV bits at the binder), so every qualified sink sees
// its own valid with its payload after the same fixed latency.
// Reset: control state only (beat counter, lv, v, fault); beat / word data registers have no reset (decision 13d).
// MUT (bench only): 1 = tx sends the beats in reverse order; 2 = rx asserts v one edge early; 3 = tx never faults on a
//   close word; 4 = rx drops the last beat (reuses beat BEATS-2).
module ot_hbm_b2_beat_tx #(
    parameter integer W = 8,
    parameter integer NV = 1,
    parameter integer BEATS = 2,
    parameter integer MUT = 0,
    localparam integer LW = (W + BEATS - 1) / BEATS
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [NV-1:0] vin,
    input  wire [W-1:0]  d,
    output reg           lv,
    output reg  [LW-1:0] ld,
    output reg           fault
);
    initial if (BEATS < 1 || W < 1 || NV < 1) $fatal(1, "ot_hbm_b2_beat_tx params");
    localparam integer CW = (BEATS > 1) ? $clog2(BEATS) : 1;
    wire v = |vin;
    wire [LW*BEATS-1:0] dp = {{(LW*BEATS-W){1'b0}}, d};
    reg [CW-1:0] left;                                    // beats still to send after this edge's
    generate if (BEATS == 1) begin : g_b1
        always @(posedge clk) ld <= dp[LW-1:0];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin lv <= 1'b0; left <= 0; fault <= 1'b0; end
            else lv <= v;
    end else begin : g_bn
        reg [LW*(BEATS-1)-1:0] sh;                        // beats 1..BEATS-1 of the word in flight (data: no reset)
        integer k;
        always @(posedge clk) begin
            if (v) begin
                if (MUT == 1) begin
                    ld <= dp[LW*(BEATS-1) +: LW];
                    for (k = 1; k < BEATS; k = k + 1) sh[LW*(k-1) +: LW] <= dp[LW*(BEATS-1-k) +: LW];
                end else begin
                    ld <= dp[LW-1:0];
                    sh <= dp[LW*BEATS-1:LW];
                end
            end else begin
                ld <= sh[LW-1:0];
                sh <= sh >> LW;
            end
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin lv <= 1'b0; left <= 0; fault <= 1'b0; end
            else begin
                lv <= v;
                if (v) begin
                    if (left != 0 && MUT != 3) fault <= 1'b1;   // a word inside the previous word's beats
                    left <= CW'(BEATS - 1);
                end else if (left != 0) left <= left - 1'b1;
            end
    end endgenerate
endmodule

module ot_hbm_b2_beat_rx #(
    parameter integer W = 8,
    parameter integer BEATS = 2,
    parameter integer MUT = 0,
    localparam integer LW = (W + BEATS - 1) / BEATS
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          lv,
    input  wire [LW-1:0] ld,
    output reg           v,
    output reg  [W-1:0]  d,
    output reg           fault
);
    initial if (BEATS < 1 || W < 1) $fatal(1, "ot_hbm_b2_beat_rx params");
    generate if (BEATS == 1) begin : g_b1
        always @(posedge clk) d <= ld[W-1:0];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin v <= 1'b0; fault <= 1'b0; end
            else v <= lv;
    end else begin : g_bn
        localparam integer CW = $clog2(BEATS);
        reg [LW*(BEATS-1)-1:0] acc;                       // beats 0..BEATS-2 (beat 0 lowest once BEATS-1 are in)
        reg [CW-1:0] got;                                 // beats of the current word received before this edge
        reg [BEATS-1:0] vp;                               // lv delayed: vp[BEATS-2] = beat 0 was BEATS-1 edges ago
        wire last = vp[BEATS-2];
        wire [LW*BEATS-1:0] word = (MUT == 4) ? {acc[LW*(BEATS-1)-1 -: LW], acc} : {ld, acc};
        if (BEATS == 2) begin : g_a2
            always @(posedge clk) acc <= ld;
        end else begin : g_an
            always @(posedge clk) acc <= {ld, acc[LW*(BEATS-1)-1:LW]};
        end
        always @(posedge clk) if (last) d <= word[W-1:0];
        wire early = (BEATS > 2) ? vp[(BEATS > 2) ? BEATS-3 : 0] : lv;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin v <= 1'b0; fault <= 1'b0; got <= 0; vp <= 0; end
            else begin
                vp <= {vp[BEATS-2:0], lv};
                v <= (MUT == 2) ? early : last;
                if (lv) begin
                    if (got != 0) fault <= 1'b1;               // beat 0 of a word inside the previous word's beats
                    got <= CW'(1);
                end else if (got != 0) got <= (got == CW'(BEATS - 1)) ? {CW{1'b0}} : got + 1'b1;
            end
    end endgenerate
endmodule
`default_nettype wire
