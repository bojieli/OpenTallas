// S81-P8 (2026-10-23, COORD R3-INTERNAL / R7): dsfd_cfifo_crs4 with the landing offsets as a PARAMETER LK instead of
// the static port lk[11:0] (12 TIEHI/TIELO on the hard macro's pins in col_h9_r0_p3).  Body line for line
// dsfd_cfifo_crs4's; LK[3k +: 3] = lane k's K (default {4{3'd2}} = the band strap).  Requires a re-harden of the
// cfifo macro under this name (GEOM REQ first).  dsfd_cfifo_crs4 itself is unchanged.
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
`timescale 1ns/1ps
module dsfd_cfifo_crs4p #(
    parameter [11:0] LK = {4{3'd2}}
) (
    output wire [14:0] cc,
    input wire cr,
    input wire cr_s,
    output wire [69:0] rd,
    input wire [65:0] ri,
    output wire rs,
    input wire rst,
    input wire [1:0] st,
    output wire [282:0] xa,
    output wire [265:0] xb,
    output wire [535:0] x2,
    input wire [275:0] xl0,      // lane k word = {old xd2, xd}[276k +: 276] (S81-DIE7/CRS4 10-18: one port per lane, so
    input wire [275:0] xl1,      // every lane port belongs to exactly ONE forwarded-clock domain xk[k] in the hardened
    input wire [275:0] xl2,      // view's multi-root ownership check; dsfd_cfifo_crs's xd / xd2 split lane 2 across
    input wire [275:0] xl3,      // two ports).  Bit order and S-face pin order unchanged.
    input wire [3:0] xk          // lane k forwarded clock (lane k's last station ck_o)
);
    reg [1:0] rsync_q; always @(posedge cr or negedge rst) if (!rst) rsync_q <= 2'b00; else rsync_q <= {rsync_q[0], 1'b1};
    wire rsync = rsync_q[1];
    reg [1:0] rsyncs_q; always @(posedge cr_s or negedge rsync) if (!rsync) rsyncs_q <= 2'b00; else rsyncs_q <= {rsyncs_q[0], 1'b1};
    wire rsync_s = rsyncs_q[1];
    reg [65:0] ri_q; always @(posedge cr) ri_q <= ri;
    assign rs = rsync;
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
        ot_s81_land #(.W(276), .D(4)) u_l (.k(LK[3 * g +: 3]), .ck_f(ckl), .i(xin[276 * g +: 276]), .ck(cr), .rs(rsync),
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
    always @(posedge cr_s or negedge rsync_s) if (!rsync_s) begin rr <= 68'd0; flt <= 1'b0; end
        else begin rr <= {sti[1] | flt, sti[0], ri_q}; flt <= flt | xflt; end
    assign rd = {rr, rr[0], rsync_s};
endmodule
