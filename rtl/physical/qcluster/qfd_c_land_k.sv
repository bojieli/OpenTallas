`timescale 1ns/1ps
`default_nettype none
// QW-CB16FULL2 (2026-10-20): native-census-safe soft landing ring halves (safe-design checklist 3 / pre-gate native census:
// no driver above 32 loads, reset nets included).  The 10-19 qfd_c_b16_full gate (ep9 191242 / ep5 000552) mapped
//   u_land_rs_0_w.wc[1]           -> 1,546 loads  (qfd_c_land_w: the write pointer decodes into the 4 x 514 slot enables)
//   u_rr_l_rs_0_w_0 / ring rq     -> 1,038-1,039  (qfd_c_land_w / _r1h: one rq resets / enables the whole ring)
// These two modules keep the ports, parameters, epochs and latency of qfd_c_land_w / qfd_c_land_r1h EXACTLY (lockstep
// bench tools/qwen_cluster/bench_land_k.sh, Verilator 5.050), and replicate the control per G-bit group:
//   qfd_c_land_w1k  writer: per group a KEPT re-registered reset copy rqg (D = rsi, same edge as rq) and a KEPT one-hot
//                   write-slot register woh (reset onehot(0), rotate left each edge while rqg = 1) == onehot(wc mod D).
//                   Slot enables = rqg & woh[s] -> G data bits.  rsi loads: 1 + NG.
//   qfd_c_land_r1k  reader: qfd_c_land_r1h with a KEPT reset copy per group (its oh / wg copies reset from it).
//                   rsi loads: 1 + NG.
// G = 24 (NG = 22 for W 514): every control flop drives <= G mux bits, vld[s] drives NG <= 32 select ANDs.
// No added cycle, no credit, no ready: both pointers free-run (static schedule).
module qfd_c_land_w1k #(
    parameter integer W  = 514,
    parameter integer D  = 4,
    parameter integer G  = 24,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input  wire              ck,
    input  wire              rsi,
    input  wire [W-1:0]      i,
    output wire [D*W-1:0]    bank,
    output wire [D*(AW+1)-1:0] epo,                    // slot write epochs (assertion only; synthesis removes them)
    output wire [D-1:0]      vld
);
    localparam integer NG = (W + G - 1) / G;
    reg            rq;
    reg [AW:0]     wc;
    reg [AW:0]     e [0:D-1];
    reg [D-1:0]    v;
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) wc <= {(AW + 1){1'b0}};
        else     wc <= wc + 1'b1;
    always @(posedge ck)
        if (!rq) v <= {D{1'b0}};
        else     v[wc[AW-1:0]] <= 1'b1;
    genvar g, s;
    generate for (s = 0; s < D; s = s + 1) begin : g_ep
        always @(posedge ck) if (rq && wc[AW-1:0] == s) e[s] <= wc;
        assign epo[s*(AW+1) +: AW+1] = e[s];
    end
    for (g = 0; g < NG; g = g + 1) begin : g_grp
        localparam integer N = (W - g * G < G) ? W - g * G : G;
        (* keep = 1 *) reg         rqg;               // reset copy of this group (same edge as rq)
        (* keep = 1 *) reg [D-1:0] woh;               // onehot(wc mod D) for this group
        always @(posedge ck) rqg <= rsi;
        always @(posedge ck)
            if (!rqg) woh <= {{(D-1){1'b0}}, 1'b1};
            else      woh <= {woh[D-2:0], woh[D-1]};
        for (s = 0; s < D; s = s + 1) begin : g_s
            reg [N-1:0] b;
            always @(posedge ck) if (rqg && woh[s]) b <= i[g*G +: N];
            assign bank[s*W + g*G +: N] = b;
        end
    end endgenerate
    assign vld = v;
`ifndef SYNTHESIS
    initial if (D < 2 || (D & (D - 1)) != 0) $fatal(1, "qfd_c_land_w1k: D must be a power of two >= 2");
`endif
endmodule

module qfd_c_land_r1k #(
    parameter integer W  = 514,
    parameter integer D  = 4,
    parameter integer K  = 2,
    parameter integer G  = 24,
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
        (* keep = 1 *) reg         rqg;               // reset copy of this group
        (* keep = 1 *) reg [D-1:0] oh;                // onehot((rc - K) mod D) for this group
        (* keep = 1 *) reg         wg;                // warm copy for this group
        wire [N-1:0] term [0:D-1];
        always @(posedge ck) rqg <= rsi;
        always @(posedge ck)
            if (!rqg) begin oh <= {{(D-1){1'b0}}, 1'b1} << S0; wg <= 1'b0; end
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
    initial if (D < 2 || (D & (D - 1)) != 0) $fatal(1, "qfd_c_land_r1k: D must be a power of two >= 2");
    initial if (K < 1 || K > D - 1) $fatal(1, "qfd_c_land_r1k: K must be in 1..D-1");
`endif
endmodule
`default_nettype wire
