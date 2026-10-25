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
    parameter integer MUT = 0,
    // JREG 1 (default, every unit): in_* land in the stop's own inject flops.  JREG 0 (S81-NATIVE3 10-17, gunit L2):
    // the caller already registers its inject sources at its pins (in_* are flop outputs, e.g. an OR of two pin-captured
    // CTL rows), so the stop uses them as its inject flops: identical cycle behaviour, no second edge.
    parameter integer JREG = 1,
    // Opt-in BK drain namespace: consume only the uniquely addressed accepted command.
    parameter integer BK_DRAIN_SINK = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    tap_k,        // strap: kinds delivered (single-beat kinds only)
    input  wire [7:0]    bk_uid,       // ignored unless BK_DRAIN_SINK=1; captured with rung inputs
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
    output reg           fault,
    // second consumer taps (S81-NATIVE3 10-17, gunit L2's HP copy; unconnected elsewhere, so synthesis drops them):
    // ra_s / ra_n = the rung input flops (northbound / southbound arrivals, one edge after the pin), dk_n / dk_s = a
    // separate registered "tapped single-beat kind == k7" flag on the dl_*v edge, so a consumer on the far face does not
    // load the dl_* output flops that sit at their own pins
    output wire [V-1:0]  ra_s,
    output wire [V-1:0]  ra_n,
    output reg           dk_n,
    output reg           dk_s
);
    localparam [2:0] K_XQ = 3'd1, K_XB = 3'd2;
    // ---------------------------------------------------------------- input flops
    reg [V-1:0] is_, in_; reg [7:0] tap_c, sink_c, bk_uid_c;
    wire [V-1:0] jn, js; wire jnv, jsv;
    always @(posedge clk) begin is_ <= vi_s; in_ <= vi_n; tap_c <= tap_k; sink_c <= sink_k; bk_uid_c <= bk_uid; end
    generate
        if (JREG != 0) begin : g_jreg
            reg [V-1:0] jn_q, js_q; reg jnv_q, jsv_q;
            always @(posedge clk) begin jn_q <= in_n; js_q <= in_s; end
            always @(posedge clk or negedge rst_n) if (!rst_n) begin jnv_q <= 1'b0; jsv_q <= 1'b0; end else begin jnv_q <= in_nv; jsv_q <= in_sv; end
            assign jn = jn_q; assign js = js_q; assign jnv = jnv_q; assign jsv = jsv_q;
        end else begin : g_jpin
            assign jn = in_n; assign js = in_s; assign jnv = in_nv; assign jsv = in_sv;
        end
    endgenerate

    // ---------------------------------------------------------------- one direction: classify / forward / tap / inject
    // fr_* : continuation fragments still to pass (arrivals); ij_* : injected fragments still owed (injector)
    reg [1:0] fr_n, fr_s, ij_n, ij_s;
    wire hn = is_[0] && (fr_n == 2'd0 || MUT == 1), hs = in_[0] && (fr_s == 2'd0 || MUT == 1);
    wire [2:0] kn = is_[3:1], ks = in_[3:1];
    wire xn = kn == K_XQ || kn == K_XB, xs = ks == K_XQ || ks == K_XB;
    wire bk_n = BK_DRAIN_SINK != 0 && hn && kn == 3'd0 && (tap_c[0] || sink_c[0]) && is_[28:21] == bk_uid_c && is_[31:29] == 3'd1;
    wire bk_s = BK_DRAIN_SINK != 0 && hs && ks == 3'd0 && (tap_c[0] || sink_c[0]) && in_[28:21] == bk_uid_c && in_[31:29] == 3'd1;
    // A duplicate command remains visible and faults in BK vin; it is not a valid sole acceptance.
    wire sn = hn && !xn && (sink_c[kn] || (bk_n && !bk_s)) && MUT != 3;
    wire ss = hs && !xs && (sink_c[ks] || (bk_s && !bk_n)) && MUT != 3;
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
    assign ra_s = is_; assign ra_n = in_;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin dk_n <= 1'b0; dk_s <= 1'b0; end else begin dk_n <= tn && kn == 3'd7; dk_s <= ts && ks == 3'd7; end
endmodule
