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
// S81-P9-CF (2026-10-23, NATIVE CENSUS <= 32 loads per dynamic/reset driver, mandatory pre-gate admission): the first
// gate of this top REFUSED at floorplan -- the four 276-b ot_s81_land rings had one wc / rc / slot enable per lane
// (1,116 loads), the bubble masks one landed marker bit per bundle (563 / 536 loads), rsync / rsync_s 150 / 69 async
// pins.  Structural fix, same calendar, same ports / pins / outline:
//   * every lane ring is cut into <= 4-bit ot_s81_land rings (69 per lane), each with ITS OWN reset leaf (gate 2: 8-bit
//     rings left rc[0] at 44 loads = 4 per bit + 12; 4 bits -> 28);
//   * the two marker bits (xl0[0], xl2[14]) land in 3 ot_s81_land_fo rings each (7 kept output copies per ring, port
//     load 12), one copy per <= 27 masked bits;
//   * rsync = a kept 2-level reset tree (stage 1 per 16 leaves, all async-reset by rst; leaves async-reset by stage 1)
//     released on the SAME cr edge as the old 2-flop rsync_q[1]; rsync_s = one stage 1 + 5 kept leaves, same edge.
// The value of every output is unchanged edge for edge (tools/s81_dv/crs4p_bench.py vs the closed dsfd_cfifo_crs).
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
    // ---- reset tree (rsync): NL leaves, each released on the 2nd cr edge after rst (the old rsync_q[1])
    localparam integer NR = 69;                        // rings per lane (4 bits each)
    localparam integer NF = 3;                         // marker fan-out rings per marker bit
    localparam integer NO = 7;                         // kept output copies per marker ring
    localparam integer NL = 4 * NR + 2 * NF + 2;       // ring leaves + rs port + rsync_s tree
    wire [NL-1:0] rl;
    dsfd_crs4p_rtree #(.N(NL)) u_rt (.clk(cr), .rst_n(rst), .q(rl));
    assign rs = rl[NL-1];
    wire rls = rl[NL-2];
    (* keep *) reg rsyncs_b;
    (* keep *) reg [4:0] rsyncs_l;
    always @(posedge cr_s or negedge rls) if (!rls) rsyncs_b <= 1'b0; else rsyncs_b <= 1'b1;
    genvar r;
    generate for (r = 0; r < 5; r = r + 1) begin : g_rss
        always @(posedge cr_s or negedge rls) if (!rls) rsyncs_l[r] <= 1'b0; else rsyncs_l[r] <= rsyncs_b;
    end endgenerate
    reg [65:0] ri_q; always @(posedge cr) ri_q <= ri;
    reg [1:0] sti; always @(posedge cr) sti <= st;
    // ---- per-lane landing (contract L1-L3): <= 4-bit rings on xk[k], read on cr from the leaf release
    wire [1103:0] xin = {xl3, xl2, xl1, xl0};
    wire [1103:0] xl;
    wire [4 * NR - 1:0] lfc;
    wire [2 * NF - 1:0] lfm;
    wire [2 * NF * NO - 1:0] mk;                       // landed marker copies: lane 0 bit 0 (low half), lane 2 bit 14
    wire [NF * NO - 1:0] mka = mk[NF * NO - 1:0], mkb = mk[2 * NF * NO - 1:NF * NO];
    genvar g, c;
    generate for (g = 0; g < 4; g = g + 1) begin : g_lane
`ifdef OT_CRS4_MUT_NBR   // bench mutant: the dsfd_cfifo_crs gap -- lanes 0 / 3 written on the neighbour lane's clock
        wire ckl = xk[g == 0 ? 1 : (g == 3 ? 2 : g)];
`else
        wire ckl = xk[g];
`endif
        // lane bits other than the marker (lane 0 bit 0, lane 2 bit 14): 275 (lanes 0, 2) or 276 bits
        localparam integer MB = (g == 0) ? 0 : ((g == 2) ? 14 : -1);
        localparam integer NBIT = (MB >= 0) ? 275 : 276;
        wire [275:0] li = xin[276 * g +: 276];
        wire [NBIT-1:0] ld;                            // data bits, marker removed
        wire [NBIT-1:0] lo;
        if (MB == 0) begin : g_m0
            assign ld = li[275:1];
            assign xl[276 * g +: 276] = {lo, mka[0]};
        end else if (MB == 14) begin : g_m14
            assign ld = {li[275:15], li[13:0]};
            assign xl[276 * g +: 276] = {lo[274:14], mkb[0], lo[13:0]};
        end else begin : g_nm
            assign ld = li;
            assign xl[276 * g +: 276] = lo;
        end
        for (c = 0; c < NR; c = c + 1) begin : g_c
            localparam integer LO = 4 * c;
            localparam integer WC = (LO + 4 <= NBIT) ? 4 : NBIT - LO;
            ot_s81_land #(.W(WC), .D(4)) u_l (.k(LK[3 * g +: 3]), .ck_f(ckl), .i(ld[LO +: WC]), .ck(cr), .rs(rl[NR * g + c]),
                                              .o(lo[LO +: WC]), .fault(lfc[NR * g + c]));
        end
        if (MB >= 0) begin : g_mk
            for (c = 0; c < NF; c = c + 1) begin : g_f
                ot_s81_land_fo #(.NO(NO), .D(4)) u_f (.k(LK[3 * g +: 3]), .ck_f(ckl), .i(li[MB]), .ck(cr),
                    .rs(rl[4 * NR + NF * (g / 2) + c]), .o(mk[NF * NO * (g / 2) + NO * c +: NO]),
                    .fault(lfm[NF * (g / 2) + c]));
            end
        end
    end endgenerate
    // bundle words as dsfd_cfifo_crs's ingress delivered them ({W:1} of each, marker stripped), bubbles before the marker;
    // mask bit j by marker copy j / 27 (<= 27 + 2 loads per copy)
    wire [564:0] oa_;
    wire [536:0] ob_;
    genvar j;
    generate for (j = 0; j < 565; j = j + 1) begin : g_ma
        assign oa_[j] = xl[1 + j] & mka[j / 27];
    end
    for (j = 0; j < 537; j = j + 1) begin : g_mb
        assign ob_[j] = xl[567 + j] & mkb[j / 27];
    end endgenerate
    wire [1100:0] xw_ = {ob_[536:1], oa_};
    wire xflt = (|lfc) | (|lfm) | (oa_[0] ^ ob_[0]);
    wire xv = xw_[0];
    reg [282:0] xa_r; reg [265:0] xb_r; reg [14:0] cc_r; reg [535:0] x2_r;
    always @(posedge cr) begin xa_r <= {xw_[283] & xv, xw_[282:1]}; xb_r <= xw_[549:284];
        cc_r <= {xw_[564:552], xw_[551] & xv, xw_[550] & xv};
        x2_r <= {xw_[1100:570], xw_[569] & xv, xw_[568:566], xw_[565] & xv}; end
    assign xa = xa_r; assign xb = xb_r; assign cc = cc_r; assign x2 = x2_r;
    reg [67:0] rr; reg flt;
    wire [67:0] rr_d = {sti[1] | flt, sti[0], ri_q};
    generate for (r = 0; r < 4; r = r + 1) begin : g_rr      // 17 rr bits per leaf (+ flt on leaf 3)
        always @(posedge cr_s or negedge rsyncs_l[r]) if (!rsyncs_l[r]) rr[17 * r +: 17] <= 17'd0;
            else rr[17 * r +: 17] <= rr_d[17 * r +: 17];
    end endgenerate
    always @(posedge cr_s or negedge rsyncs_l[3]) if (!rsyncs_l[3]) flt <= 1'b0; else flt <= flt | xflt;
    assign rd = {rr, rr[0], rsyncs_l[4]};
endmodule

// kept 2-level reset tree: stage 1 (one per 16 leaves) async-reset by rst_n, each leaf async-reset by its stage 1;
// every leaf releases on the 2nd clk edge after rst_n (= a 2-flop synchroniser), <= 16 + 1 loads per driver.
module dsfd_crs4p_rtree #(parameter integer N = 1) (input wire clk, input wire rst_n, output wire [N-1:0] q);
    localparam integer NB = (N + 15) / 16;
    (* keep *) reg [NB-1:0] br;
    (* keep *) reg [N-1:0]  lf;
    always @(posedge clk or negedge rst_n) if (!rst_n) br <= {NB{1'b0}}; else br <= {NB{1'b1}};
    genvar i;
    generate for (i = 0; i < N; i = i + 1) begin : g_l
        always @(posedge clk or negedge br[i / 16]) if (!br[i / 16]) lf[i] <= 1'b0; else lf[i] <= 1'b1;
    end endgenerate
    assign q = lf;
endmodule
