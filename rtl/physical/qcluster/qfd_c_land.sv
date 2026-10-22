`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// Q-CL16-LAND (2026-10-18): LANDING of one qfd_c_b16_dv region-seam crossing (LANDING-CONTRACT L1-L7,
// /home/ubuntu/claude-takeover-20261007/lanes/LANDING-CONTRACT.md), for crossings whose in-cluster clock skew does not
// fit a single registered hop (Q-CL16-EARLY: u_leg_3_1b_0 c3r3 -> u_leg_3_1b_1 c2r2, TT setup -16 ps with the 60 ps die
// residual).  Same semantics as ot_qfd_land (claude/q-die11-rly-1018 rtl/qwen_split/qfd_fwd_lane.sv) and ot_s81_land
// (claude/s81land-1017), split into TWO instances so each half sits in its own clock region and gets its own placement
// site (fabric_sites_place.tcl places soft flops per u_fab.<instance> prefix):
//   qfd_c_land_w  RING, on the SOURCE region root (ck = ck_<src>), placed beside the source station (flop-first: the
//                 slots ARE the capture flops of the source station's word; one short in-region hop).  Every edge writes
//                 the word into slot wc mod D.  Bubbles are written like data.
//   qfd_c_land_r  READ, on the DESTINATION region root (ck = ck_<dst>), placed beside the destination station: every
//                 edge after warm-up reads slot (rc - K) mod D into the registered output o (flop-last) -> the next
//                 station.  The bank -> o paths are the only paths of the crossing: SDC set_multicycle_path -setup E
//                 -hold (D - 1) (qc_kit.py), window (E - D) T + t_hold < dL < E T - t_cq - t_setup at TT and FF.
// No ready, no credit, no occupancy, no training (owner static-schedule rule 10-14): both pointers free-run.
// EPOCHS (contract L3, released-reset form; both regions are die roots of one cluster, neither clock ever stops):
//   rsi of each half is a leaf of the cluster's equal-depth reset tree (depth RD), re-registered once on the half's own
//   clock (depth RD + 1 on both sides), so write epoch G and read epoch R0 are the SAME nominal edge: E = K + R0 - G = K.
//   Synchronous: while the local reset is low wc / rc / warm / written flags are held at 0 (no writes, o = 0 bubbles).
// LATENCY (contract L4): the word the source station launches at edge e is written at e + 1 and is in o after
//   e + 1 + E; the destination station captures it at e + 2 + E.  Added vs the plain hop: E + 1 edges (compiler record
//   results/arch/qwen_cluster_1017/q_cluster16/die_clock_contract.json "landings").
// FAULT (contract L6, ASSERTION ONLY per the Q-CL16-LAND brief): each slot stores its write epoch and a written flag;
//   after warm-up a written read slot whose epoch is not rc - K is a calendar slip -> $error (simulation).  The epoch
//   tags only feed the assertion, so synthesis removes them; the calendar never changes.
// K: a compile-time constant of the hardened cluster (one landing, one master: no strap variants).
// ---------------------------------------------------------------------------------------------------------------------
module qfd_c_land_w #(
    parameter integer W  = 514,
    parameter integer D  = 4,                          // ring depth, power of two >= 2
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input  wire              ck,                       // source region root
    input  wire              rsi,                      // reset-tree leaf (active low), re-registered here
    input  wire [W-1:0]      i,                        // source station q (one in-region hop)
    output wire [D*W-1:0]    bank,                     // ring slots -> qfd_c_land_r (multicycle E / D-1 paths)
    output wire [D*(AW+1)-1:0] epo,                    // slot write epochs (assertion only)
    output wire [D-1:0]      vld                       // slot written since the epoch
);
    reg            rq;
    reg [AW:0]     wc;
    reg [W-1:0]    b [0:D-1];
    reg [AW:0]     e [0:D-1];
    reg [D-1:0]    v;
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) wc <= {(AW + 1){1'b0}};
        else     wc <= wc + 1'b1;
    always @(posedge ck)
        if (!rq) v <= {D{1'b0}};
        else     v[wc[AW-1:0]] <= 1'b1;
    genvar s;
    generate for (s = 0; s < D; s = s + 1) begin : g_slot
        always @(posedge ck) if (rq && wc[AW-1:0] == s) begin b[s] <= i; e[s] <= wc; end
        assign bank[s*W +: W] = b[s];
        assign epo[s*(AW+1) +: AW+1] = e[s];
    end endgenerate
    assign vld = v;
`ifndef SYNTHESIS
    initial if (D < 2 || (D & (D - 1)) != 0) $fatal(1, "qfd_c_land_w: D must be a power of two >= 2");
`endif
endmodule

module qfd_c_land_r #(
    parameter integer W  = 514,
    parameter integer D  = 4,
    parameter integer K  = 2,                          // read offset = E (G == R0); 1 <= K <= D - 1
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input  wire              ck,                       // destination region root
    input  wire              rsi,                      // reset-tree leaf (active low), re-registered here
    input  wire [D*W-1:0]    bank,
    input  wire [D*(AW+1)-1:0] epo,
    input  wire [D-1:0]      vld,
    output reg  [W-1:0]      o                         // flop-last -> destination station
);
    reg            rq;
    reg [AW:0]     rc;
    reg            warm;
    wire [AW:0]    kk = K;
    wire [AW:0]    exp_ = rc - kk;
    wire [AW-1:0]  sel = exp_[AW-1:0];
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) begin rc <= {(AW + 1){1'b0}}; warm <= 1'b0; end
        else begin
            rc <= rc + 1'b1;
            if (rc == kk - 1'b1) warm <= 1'b1;
        end
    always @(posedge ck) o <= (warm && vld[sel]) ? bank[sel*W +: W] : {W{1'b0}};
`ifndef SYNTHESIS
    reg fault = 1'b0;
    always @(posedge ck)
        if (warm && vld[sel] && epo[sel*(AW+1) +: AW+1] != exp_ && !fault) begin
            fault <= 1'b1;
            $error("LAND_FAULT %m: read slot %0d epoch %0d, expected %0d (calendar slip)", sel, epo[sel*(AW+1) +: AW+1], exp_);
        end
    initial if (D < 2 || (D & (D - 1)) != 0) $fatal(1, "qfd_c_land_r: D must be a power of two >= 2");
    initial if (K < 1 || K > D - 1) $fatal(1, "qfd_c_land_r: K must be in 1..D-1");
`endif
endmodule
`default_nettype wire
