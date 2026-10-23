`timescale 1ns/1ps
`default_nettype none
// QW-CB16FULL (2026-10-19): qfd_c_land_r with the runtime-indexed read part-select bank[sel*W +: W] (a 514-bit
// $shiftx, safe-design checklist items 4/5; pre_route_gate WARN runtime_partselect on qfd_c_b16_full/_fullb) replaced
// by a REGISTERED one-hot select and a constant-index AND-OR (the CLOSED qfd_c_land_safe_r_slice form, without its
// extra reset stage, so the epochs stay those of qfd_c_land_w / qfd_c_land_r: read slot (rc - K) mod D, E = K).
// Ports, parameters, latency and the LAND_FAULT assertion are identical to qfd_c_land_r; the one-hot register oh is
// onehot((rc - K) mod D) on every edge (reset value onehot((D - K) mod D), rotate left once per edge).  The select is
// replicated per G-bit group (KEEP copies; group count ceil(W/G)) so no select flop drives more than ~G AND gates.
// Bench: tools/qwen_cluster/bench_land_r1h.sh (lockstep vs qfd_c_land_r, Verilator 5.050).  No added cycle.
module qfd_c_land_r1h #(
    parameter integer W  = 514,
    parameter integer D  = 4,
    parameter integer K  = 2,
    parameter integer G  = 32,                         // bits per replicated select copy
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input  wire              ck,
    input  wire              rsi,
    input  wire [D*W-1:0]    bank,
    input  wire [D*(AW+1)-1:0] epo,
    input  wire [D-1:0]      vld,
    output reg  [W-1:0]      o
);
    localparam integer NG = (W + G - 1) / G;
    localparam integer S0 = (D - K) % D;
    reg            rq;
    reg [AW:0]     rc;
    reg            warm;
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) begin rc <= {(AW + 1){1'b0}}; warm <= 1'b0; end
        else begin
            rc <= rc + 1'b1;
            if (rc == K - 1) warm <= 1'b1;
        end
    genvar g, s;
    generate for (g = 0; g < NG; g = g + 1) begin : g_grp
        localparam integer N = (W - g * G < G) ? W - g * G : G;
        (* keep = 1 *) reg [D-1:0] oh;                // onehot(sel) for this group
        (* keep = 1 *) reg         wg;                // warm copy for this group
        wire [N-1:0] term [0:D-1];
        always @(posedge ck)
            if (!rq) begin oh <= {{(D-1){1'b0}}, 1'b1} << S0; wg <= 1'b0; end
            else begin
                oh <= {oh[D-2:0], oh[D-1]};
                if (rc == K - 1) wg <= 1'b1;
            end
        for (s = 0; s < D; s = s + 1) begin : g_s
            assign term[s] = bank[s*W + g*G +: N] & {N{oh[s] & vld[s]}};
        end
        reg [N-1:0] chosen;
        integer t;
        always @* begin
            chosen = {N{1'b0}};
            for (t = 0; t < D; t = t + 1) chosen = chosen | term[t];
        end
        always @(posedge ck) o[g*G +: N] <= wg ? chosen : {N{1'b0}};
    end endgenerate
`ifndef SYNTHESIS
    wire [AW:0]    kk = K;
    wire [AW:0]    exp_ = rc - kk;
    wire [AW-1:0]  sel = exp_[AW-1:0];
    reg fault = 1'b0;
    always @(posedge ck)
        if (warm && vld[sel] && epo[sel*(AW+1) +: AW+1] != exp_ && !fault) begin
            fault <= 1'b1;
            $error("LAND_FAULT %m: read slot %0d epoch %0d, expected %0d (calendar slip)", sel, epo[sel*(AW+1) +: AW+1], exp_);
        end
    initial if (D < 2 || (D & (D - 1)) != 0) $fatal(1, "qfd_c_land_r1h: D must be a power of two >= 2");
    initial if (K < 1 || K > D - 1) $fatal(1, "qfd_c_land_r1h: K must be in 1..D-1");
`endif
endmodule
`default_nettype wire
