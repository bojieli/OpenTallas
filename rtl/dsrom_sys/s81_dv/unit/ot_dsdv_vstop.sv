`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-1 (2026-10-17): ot_dsdv_vstop -- the V-rung stop of the S81-DV void units (one hardened leaf, replicated).
//
// S81-DV p4c..p4f (SPEC 0b): each slice column links its S and N slice on ONE 276-b V rung per direction, and every void
// unit of that column sits ON the rung (plan links tvN_* / tvS_*):
//     col 0 / 7 : s_cS <-> coll_cS <-> coll_cN <-> s_cN          col 3 : s_3S <-> gunit <-> s_3N
//     col 4     : s_4S <-> bk_sel <-> seqhost <-> s_4N           col 1/2/5/6 : bk_col / mix4_w / mix4_e likewise
// The slice ring stop (ot_s81sl_rstop, "V receive / V send") treats the rung as a point-to-point partner link, so every
// unit on it must be a FIXED-LATENCY, TRANSPARENT stop.  This leaf is that stop; the unit's own logic hangs off its
// deliver / inject ports.  V beat format (ot_s81sl_rstop): header fragment lane 0 = {.. [12:9] src, [8:4] hops,
// [3:1] kind, [0] valid}, payload from bit 21; kinds XQ (1) / XB (2) cross as 4 fragments (header first, then 3 raw
// fragments whose bit 0 is payload); every other kind is one V beat.  Idle = all-zero.
//
//   forward   every beat and every continuation fragment passes S->N (and N->S) in 2 edges (input flop, output flop);
//             a header whose kind is set in the SINK strap is removed (slot becomes free downstream).
//   deliver   a single-beat header whose kind is set in the TAP strap is copied to dl_* (registered, same edge as the
//             forward output).  XQ / XB are never tapped or sunk (fragment streams always pass).
//   inject    in_*v / in_* (flop-first) replace the forwarded slot on the same output edge as a beat arriving at the
//             vi pin on the same cycle.  The compiler places injections only in free slots (static schedule, no
//             credit / ready / arbitration); an injection into an occupied slot, or an injected XQ / XB header not
//             followed by its 3 injected fragments, is a sticky FAULT (an assertion, never a reschedule).
// Straps tap_k / sink_k (8 kinds) are captured pins, never parameters (one master for every unit).
// Every input lands in a flop; every output leaves a flop.  MUT (bench only): 1 = no continuation tracking,
// 2 = injection wins without the occupancy check, 3 = sunk header still forwarded.
// ---------------------------------------------------------------------------------------------------------------------
module ot_dsdv_vstop #(
    parameter integer V   = 276,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    tap_k,        // strap: kinds delivered (single-beat kinds only)
    input  wire [7:0]    sink_k,       // strap: kinds removed from the rung (subset of tap_k by convention)
    // rung, S side (toward the S slice) and N side (toward the N slice)
    input  wire [V-1:0]  vi_s,         // northbound arrivals
    output reg  [V-1:0]  vo_n,
    input  wire [V-1:0]  vi_n,         // southbound arrivals
    output reg  [V-1:0]  vo_s,
    // unit side
    output reg           dl_nv,        // northbound tapped beat
    output reg  [V-1:0]  dl_n,
    output reg           dl_sv,        // southbound tapped beat
    output reg  [V-1:0]  dl_s,
    input  wire          in_nv,        // inject northbound (onto vo_n)
    input  wire [V-1:0]  in_n,
    input  wire          in_sv,        // inject southbound (onto vo_s)
    input  wire [V-1:0]  in_s,
    output reg           fault
);
    localparam [2:0] K_XQ = 3'd1, K_XB = 3'd2;
    // ---------------------------------------------------------------- input flops
    reg [V-1:0] is_, in_, jn, js; reg jnv, jsv; reg [7:0] tap_c, sink_c;
    always @(posedge clk) begin is_ <= vi_s; in_ <= vi_n; jn <= in_n; js <= in_s; tap_c <= tap_k; sink_c <= sink_k; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin jnv <= 1'b0; jsv <= 1'b0; end else begin jnv <= in_nv; jsv <= in_sv; end

    // ---------------------------------------------------------------- one direction: classify / forward / tap / inject
    // fr_* : continuation fragments still to pass (arrivals); ij_* : injected fragments still owed (injector)
    reg [1:0] fr_n, fr_s, ij_n, ij_s;
    wire hn = is_[0] && (fr_n == 2'd0 || MUT == 1), hs = in_[0] && (fr_s == 2'd0 || MUT == 1);
    wire [2:0] kn = is_[3:1], ks = in_[3:1];
    wire xn = kn == K_XQ || kn == K_XB, xs = ks == K_XQ || ks == K_XB;
    wire sn = hn && !xn && sink_c[kn] && MUT != 3, ss = hs && !xs && sink_c[ks] && MUT != 3;
    wire tn = hn && !xn && (tap_c[kn] || sink_c[kn]), ts = hs && !xs && (tap_c[ks] || sink_c[ks]);
    wire on = (fr_n != 2'd0) || (hn && !sn), os = (fr_s != 2'd0) || (hs && !ss);   // forwarded slot occupied
    wire jxn = jn[0] && (jn[3:1] == K_XQ || jn[3:1] == K_XB) && ij_n == 2'd0;
    wire jxs = js[0] && (js[3:1] == K_XQ || js[3:1] == K_XB) && ij_s == 2'd0;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            vo_n <= {V{1'b0}}; vo_s <= {V{1'b0}}; dl_nv <= 1'b0; dl_sv <= 1'b0; fault <= 1'b0;
            fr_n <= 2'd0; fr_s <= 2'd0; ij_n <= 2'd0; ij_s <= 2'd0;
        end else begin
            fr_n <= (fr_n != 2'd0) ? fr_n - 2'd1 : (hn && xn) ? 2'd3 : 2'd0;
            fr_s <= (fr_s != 2'd0) ? fr_s - 2'd1 : (hs && xs) ? 2'd3 : 2'd0;
            ij_n <= (ij_n != 2'd0) ? ij_n - 2'd1 : (jnv && jxn) ? 2'd3 : 2'd0;
            ij_s <= (ij_s != 2'd0) ? ij_s - 2'd1 : (jsv && jxs) ? 2'd3 : 2'd0;
            vo_n <= jnv ? jn : on ? is_ : {V{1'b0}};
            vo_s <= jsv ? js : os ? in_ : {V{1'b0}};
            if (MUT == 2) begin
                if ((ij_n != 2'd0 && !jnv) || (ij_s != 2'd0 && !jsv)) fault <= 1'b1;
            end else if ((jnv && on) || (jsv && os) || (ij_n != 2'd0 && !jnv) || (ij_s != 2'd0 && !jsv)) fault <= 1'b1;
            dl_nv <= tn; dl_sv <= ts;
        end
    always @(posedge clk) begin dl_n <= is_; dl_s <= in_; end
endmodule
