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
// 10-20 gate census (fullk 024547) of the first form (one copy per 24 bits): 5,691 write enables of 48-49 loads (the mapped
// enable mux uses the enable on 2 pins per bit) and vld[s] absorbed into every read bit (517 loads).  Now TWO levels:
//   super-group of GS = 30 bits: one KEPT reset copy (rsi loads 1 + NGS = 19 for W 514/516);
//   sub-group of N = 15 bits: one KEPT one-hot slot register; write enable = rqg & woh[s] -> 2 x 15 + 1 = 31 loads;
//   vld is replicated per super-group in the writer (vg, set from the sub-group enable) and carried as D x NGS bits, so
//   a reader super-group reads its own copy (<= 30 bit loads).  Reader: reset copy + warm per super-group, one-hot per
//   sub-group.  Same epochs / latency / ports semantics; vld port is D * NGS wide (copy g = bits [g*D +: D]).
// No added cycle, no credit, no ready: both pointers free-run (static schedule).
module qfd_c_land_w1k #(
    parameter integer W  = 514,
    parameter integer D  = 4,
    parameter integer GS = 30,                         // bits per reset copy / vld copy (super-group)
    parameter integer G  = 15,                         // bits per one-hot write-slot copy (sub-group); GS = 2 G
    parameter integer AW = (D <= 2) ? 1 : $clog2(D),
    parameter integer NGS = (W + GS - 1) / GS
) (
    input  wire              ck,
    input  wire              rsi,
    input  wire [W-1:0]      i,
    output wire [D*W-1:0]    bank,
    output wire [D*(AW+1)-1:0] epo,                    // slot write epochs (assertion only; synthesis removes them)
    output wire [D*NGS-1:0]  vld                       // written flags, one KEPT copy per super-group
);
    reg            rq;
    reg [AW:0]     wc;
    reg [AW:0]     e [0:D-1];
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) wc <= {(AW + 1){1'b0}};
        else     wc <= wc + 1'b1;
    genvar g, h, s;
    generate for (s = 0; s < D; s = s + 1) begin : g_ep
        always @(posedge ck) if (rq && wc[AW-1:0] == s) e[s] <= wc;
        assign epo[s*(AW+1) +: AW+1] = e[s];
    end
    for (g = 0; g < NGS; g = g + 1) begin : g_grp
        localparam integer B0 = g * GS;
        localparam integer NS = (W - B0 < GS) ? W - B0 : GS;           // bits in this super-group
        localparam integer NH = (NS + G - 1) / G;                        // sub-groups (1 or 2)
        (* keep = 1 *) reg         rqg;               // reset copy of this super-group (same edge as rq)
        (* keep = 1 *) reg [D-1:0] vg;                // written flags copy of this super-group
        wire [D-1:0] en0;
        always @(posedge ck) rqg <= rsi;
        always @(posedge ck)
            if (!rqg) vg <= {D{1'b0}};
            else      vg <= vg | en0;
        assign vld[g*D +: D] = vg;
        for (h = 0; h < NH; h = h + 1) begin : g_sub
            localparam integer L = B0 + h * G;
            localparam integer N = (NS - h * G < G) ? NS - h * G : G;
            (* keep = 1 *) reg [D-1:0] woh;           // onehot(wc mod D) for this sub-group
            always @(posedge ck)
                if (!rqg) woh <= {{(D-1){1'b0}}, 1'b1};
                else      woh <= {woh[D-2:0], woh[D-1]};
            for (s = 0; s < D; s = s + 1) begin : g_s
                wire en = rqg && woh[s];
                reg [N-1:0] b;
                always @(posedge ck) if (en) b <= i[L +: N];
                assign bank[s*W + L +: N] = b;
                if (h == 0) begin : g_v
                    assign en0[s] = en;
                end
            end
        end
    end endgenerate
`ifndef SYNTHESIS
    initial if (D < 2 || (D & (D - 1)) != 0) $fatal(1, "qfd_c_land_w1k: D must be a power of two >= 2");
    initial if (GS != 2 * G) $fatal(1, "qfd_c_land_w1k: GS must be 2 G");
`endif
endmodule

module qfd_c_land_r1k #(
    parameter integer W  = 514,
    parameter integer D  = 4,
    parameter integer K  = 2,
    parameter integer GS = 30,
    parameter integer G  = 15,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D),
    parameter integer NGS = (W + GS - 1) / GS
) (
    input  wire              ck,
    input  wire              rsi,
    input  wire [D*W-1:0]    bank,
    input  wire [D*(AW+1)-1:0] epo,
    input  wire [D*NGS-1:0]  vld,
    output reg  [W-1:0]      o
);
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
    genvar g, h, s;
    generate for (g = 0; g < NGS; g = g + 1) begin : g_grp
        localparam integer B0 = g * GS;
        localparam integer NS = (W - B0 < GS) ? W - B0 : GS;
        localparam integer NH = (NS + G - 1) / G;
        (* keep = 1 *) reg         rqg;               // reset copy of this super-group
        (* keep = 1 *) reg         wg;                // warm copy of this super-group
        always @(posedge ck) rqg <= rsi;
        always @(posedge ck)
            if (!rqg) wg <= 1'b0;
            else if (rc == K - 1) wg <= 1'b1;
        for (h = 0; h < NH; h = h + 1) begin : g_sub
            localparam integer L = B0 + h * G;
            localparam integer N = (NS - h * G < G) ? NS - h * G : G;
            (* keep = 1 *) reg [D-1:0] oh;            // onehot((rc - K) mod D) for this sub-group
            wire [N-1:0] term [0:D-1];
            always @(posedge ck)
                if (!rqg) oh <= {{(D-1){1'b0}}, 1'b1} << S0;
                else      oh <= {oh[D-2:0], oh[D-1]};
            for (s = 0; s < D; s = s + 1) begin : g_s
                assign term[s] = bank[s*W + L +: N] & {N{oh[s] & vld[g*D + s]}};
            end
            reg [N-1:0] chosen;
            integer t;
            always @* begin
                chosen = {N{1'b0}};
                for (t = 0; t < D; t = t + 1) chosen = chosen | term[t];
            end
            always @(posedge ck) o[L +: N] <= wg ? chosen : {N{1'b0}};
        end
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
