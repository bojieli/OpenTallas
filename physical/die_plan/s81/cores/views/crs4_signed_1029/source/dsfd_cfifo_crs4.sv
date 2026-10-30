// S81-LAND2 (2026-10-17, HANDOFF 0dm+ decision (1)): SUCCESSOR of dsfd_cfifo_crs with the two landing gaps of the
// S81-LAND audit closed (results/arch/s81_dv_1016/landing/audit.json, LANDING-CONTRACT.md section 4):
//   gap 1  lanes 0 and 3 were captured on the NEIGHBOUR lane's forwarded clock (xd = lanes 0, 1 + 14 b of lane 2 on
//          xf = xk[1]; xd2 = 262 b of lane 2 + lane 3 on xf2 = xk[2]).  Here every 276-b lane k = port xl<k> (= the old
//          {xd2, xd}[276k +: 276]) lands on ITS OWN forwarded clock xk[k] (one ot_s81_land ring per lane, contract L1).
//   gap 2  the read epoch was a 2-flop sample of the in-band marker on cr_s, so the column epoch followed the lane phase
//          (fixed only while the marker edge stays out of the sampling aperture).  Here the read epoch is the contract
//          L3 one: rc counts cr edges from the release of the frame's regional reset (rsync); the write epoch counts
//          each lane's forwarded edges from its first one (hop-0 ICG at the source, opened at or after the frame's
//          release).  The latency is the compile-time E + 1 of each lane, the same at every corner (L4); lk[3k +: 3] =
//          lane k's K, an identity strap tied by the die binder (L7).
// The marker bits (xin[0] = xl0[0] and xin[566] = xl2[14], the source's released reset) are no longer epochs: a word read while its
// bundle's marker is 0 is a bubble (masked to zero, exactly the words dsfd_cfifo_crs never wrote).  Everything after
// the lane rings -- xa / xb / cc / x2 registers on cr, the south status path ri -> rr -> rd on cr_s, the fault OR -- is
// dsfd_cfifo_crs's, line for line.  Default die instances and dsfd_cfifo_crs stay byte-identical (opt-in successor).
// No ready / occupancy / credit / training: bubbles are written and read like data.
// S81-CORE-LAT-R14 (2026-10-27, face_guard CP1-R10 / OWNER 10-15 "register every pin"): every pin has its OWN face flop.
//   * rs, rd[0], rd[1] were shared nets (rsync -> 34 reset loads, rsync_s -> 69, rr[0] on rd[2] AND rd[1] = port to port
//     feedthrough).  Each now has a dedicated (* keep *) duplicate (originals kept too, so opt_merge cannot fold them) of the same register (same D, same clock, same reset):
//     rs = rsync_q[1], rd0_q = rsyncs_q[1], rr0_d = rr[0].  CYCLE BEHAVIOUR UNCHANGED (bit-identical outputs).
//   * lk (static identity strap) was read combinationally by the ring compare logic; it now lands in a cr face register
//     lk_q.  The strap is quasi-static (tied by the die binder) and rsync releases >= 2 cr edges after rst, so the rings
//     see the same K from their first post-reset edge: CYCLE BEHAVIOUR UNCHANGED.
//   * LFACE = 1 (default 0 = the frozen L1-L7 contract): one face capture flop per xl<k> bit on its own forwarded clock
//     xk[k] in front of the ring (the ring slots then load the capture flop, not the pin: 1 load per pin instead of
//     D = 4).  CONTRACT CHANGE: lane latency from the last relay station to the slot write grows by ONE xk[k] edge
//     (E + 1 -> E + 2 edges; same window, same K) -- a die calendar change that needs a COORD ruling before any die uses it.
// S81-CORE-LAT-R21 (2026-10-27, COORD S81-CORE-LAT-R20 ruling (a) "replicate face registers per landing slot, no added
//   cycle"): LGATE = 1 (release kit: define DSFD_CRS4_LGATE; default 0 = the form above, unchanged) lands each lane in
//   ot_s81_land with GSLOT = 1, whose D ring slots are written through their own ICG.  The slots then ARE the pin's
//   face registers, one per landing slot: each xl<k> bit drives exactly D = 4 flop D pins on its own forwarded clock
//   xk[k], no recirculation mux (face_guard land declaration: class land_slot).  Same edges, same K, same window,
//   ZERO added cycles (bench tools/s81_dv/crs4_bench.py --lgate: LGATE 1 vs the closed reference).  LFACE (+1 edge)
//   is not used.  Instance paths are unchanged (g_lane[k].u_l).
`timescale 1ns/1ps
module dsfd_cfifo_crs4 #(
    parameter integer LFACE = 0,     // 1 = per-bit lane face capture flop on xk[k] (+1 lane edge, see header)
`ifdef DSFD_CRS4_LGATE
    parameter integer LGATE = 1      // 1 = gated landing slots (face register per landing slot, 0 added edges)
`else
    parameter integer LGATE = 0
`endif
) (
    output wire [14:0] cc,
    input wire cr,
    input wire cr_s,
    output wire [69:0] rd,
    input wire [65:0] ri,
    output reg rs,               // face flop = the port itself (a kept alias wire would hang a buffer on the port net)
    input wire rst,
    input wire [1:0] st,
    output wire [282:0] xa,
    output wire [265:0] xb,
    output wire [535:0] x2,
    input wire [275:0] xl0,      // lane k word = {old xd2, xd}[276k +: 276] (S81-DIE7/CRS4 10-18: one port per lane, so
    input wire [275:0] xl1,      // every lane port belongs to exactly ONE forwarded-clock domain xk[k] in the hardened
    input wire [275:0] xl2,      // view's multi-root ownership check; dsfd_cfifo_crs's xd / xd2 split lane 2 across
    input wire [275:0] xl3,      // two ports).  Bit order and S-face pin order unchanged.
    input wire [3:0] xk,         // lane k forwarded clock (lane k's last station ck_o)
    input wire [11:0] lk         // lane k read offset K = lk[3k +: 3] (identity strap, die STA window rule L5)
);
    (* keep *) reg [1:0] rsync_q; always @(posedge cr or negedge rst) if (!rst) rsync_q <= 2'b00; else rsync_q <= {rsync_q[0], 1'b1};
    wire rsync = rsync_q[1];
    (* keep *) reg [1:0] rsyncs_q; always @(posedge cr_s or negedge rsync) if (!rsync) rsyncs_q <= 2'b00; else rsyncs_q <= {rsyncs_q[0], 1'b1};
    wire rsync_s = rsyncs_q[1];
    reg [65:0] ri_q; always @(posedge cr) ri_q <= ri;
    always @(posedge cr or negedge rst) if (!rst) rs <= 1'b0; else rs <= rsync_q[0];   // rs face flop: duplicate of rsync_q[1]
    (* keep *) reg rd0_q;                // rd[0] face flop: duplicate of rsyncs_q[1]
    always @(posedge cr_s or negedge rsync) if (!rsync) rd0_q <= 1'b0; else rd0_q <= rsyncs_q[0];
    reg [11:0] lk_q; always @(posedge cr) lk_q <= lk;   // strap face register (static value)
    reg [1:0] sti; always @(posedge cr) sti <= st;
    // ---- per-lane landing (contract L1-L3): ring on xk[k], read on cr from the rsync release
    wire [1103:0] xin = {xl3, xl2, xl1, xl0};
    wire [1103:0] xl;
    wire [3:0] lf;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_lane
`ifdef OT_CRS4_MUT_NBR   // bench mutant: the dsfd_cfifo_crs gap -- lanes 0 / 3 written on the neighbour lane's clock
        wire ckl = xk[g == 0 ? 1 : (g == 3 ? 2 : g)];
`else
        wire ckl = xk[g];
`endif
        wire [275:0] xi;
        if (LFACE != 0) begin : g_face
            reg [275:0] xc; always @(posedge ckl) xc <= xin[276 * g +: 276];   // lane face capture (+1 xk[k] edge)
            assign xi = xc;
        end else begin : g_pin
            assign xi = xin[276 * g +: 276];
        end
        ot_s81_land #(.W(276), .D(4), .GSLOT(LGATE)) u_l (.k(lk_q[3 * g +: 3]), .ck_f(ckl), .i(xi), .ck(cr), .rs(rsync),
                                                          .o(xl[276 * g +: 276]), .fault(lf[g]));
    end endgenerate
    // bundle words as dsfd_cfifo_crs's ingress delivered them ({W:1} of each, marker stripped), bubbles before the marker
    wire [564:0] oa_ = xl[565:1] & {565{xl[0]}};
    wire [536:0] ob_ = xl[1103:567] & {537{xl[566]}};
    wire [1100:0] xw_ = {ob_[536:1], oa_};
    wire xflt = (|lf) | (oa_[0] ^ ob_[0]);
    wire xv = xw_[0];
    reg [282:0] xa_r; reg [265:0] xb_r; reg [14:0] cc_r; reg [535:0] x2_r;
    always @(posedge cr) begin xa_r <= {xw_[283] & xv, xw_[282:1]}; xb_r <= xw_[549:284];
        cc_r <= {xw_[564:552], xw_[551] & xv, xw_[550] & xv};
        x2_r <= {xw_[1100:570], xw_[569] & xv, xw_[568:566], xw_[565] & xv}; end
    assign xa = xa_r; assign xb = xb_r; assign cc = cc_r; assign x2 = x2_r;
    reg [67:0] rr; reg flt;
    (* keep *) reg rr0_d;                // rd[1] face flop: duplicate of rr[0] (was rr[0] on rd[2] and rd[1])
    always @(posedge cr_s or negedge rsync_s) if (!rsync_s) begin rr <= 68'd0; flt <= 1'b0; rr0_d <= 1'b0; end
        else begin rr <= {sti[1] | flt, sti[0], ri_q}; flt <= flt | xflt; rr0_d <= ri_q[0]; end
    assign rd = {rr, rr0_d, rd0_q};
endmodule
