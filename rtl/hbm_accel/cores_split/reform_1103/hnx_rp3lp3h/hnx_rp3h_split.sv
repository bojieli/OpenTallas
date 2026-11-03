`timescale 1ns/1ps
// DIE-HBM-61/SPLIT 11-03 (OWNER TWO-STRIKES RE-FORM, HBM batch HBM-RF1 / plan event d44v): hnx_rp3lp3h_n (680k census,
// 807k ORFS synth) and hnx_rp3lp3h_s (658k / 785k) cut on their natural RTL boundaries into hardened sub-blocks of
// <= 150k cells.  Measured ORFS synth (uncut children): hnx_rp4_tcc 164k (= 2 x ot_hbm_accel_smh_tcl + tct),
// ot_hbm_accel_smh_bdc 60k, hnx_xs3 83k (12 SRAM macros): one P = 3 leaf (hnx_rp4lp4_lfx) is ~760k, so the leaf is cut.
//
// Sub-blocks (one clock each; FIVE masters for both halves; the three leaf masters are shared by _n and _s):
//   hnx_rp3h_xs   x1 / half : lfx lane front (lane select, kept rq/bd/wl copies, reset copies) + the shared x store
//                             hnx_xs3 (12 x 128x256 macros) + per-consumer operand output buses (one face flop per copy)
//   hnx_rp3h_tl   x6 / half : one BF16 column half = ot_hbm_accel_smh_tcl (verbatim; was hard child u_h0 / u_h1 of tcc)
//   hnx_rp3h_lc   x3 / half : lane core = the lane's XREL stations (block-dot + BF16 control), block-dot column
//                             ot_hbm_accel_smh_bdc, BF16 tree ot_hbm_accel_smh_tct, G1 merge register
//   hnx_rp3h_gn   x1 (n)    : the n half's fcore without u_lf0 (pins, regional reset, strap, transport rows / beats,
//                             landings, gather relays hnx_rp4l_gn, seam landing ring) + the leaf publish hnx_rp4lp4_pub
//   hnx_rp3h_gs   x1 (s)    : the s half's fcore without u_lf1 (+ hnx_rp4lp4_pub)
//
// Every sub-block pin is registered at its face by the kit face shell (+1 in / +1 out; reset pins pass through), so a
// seam between two sub-blocks costs 2 edges.  Leaf result timing (vs the uncut core, every SM leaf alike):
//   glue -> xs (rl1 / bk1 / strap)                                   +2
//   xs -> tl (BF16 operands; the tl input face flop takes the place of the lane's xf_w / xf_x station)   +1
//   tl -> lc (column-half sums + sticky faults)                       +2   => BF16 result +3
//   xs -> lc (block-dot operands, BF16 control; stations kept)        +2   => block-dot result +2, matched by +1 here
//   lc tct control (xf_v / last / tag) delayed +1 to meet the +3 sums (pure delay, LC_FD)
//   lc -> glue (gather word g_p)                                      +2
//   => g_p at the publish +2 +3 +2 = +7; act (lane-select active mask, xs -> glue +2 after the front's +2) delayed
//      3 more edges in the glue (pure delay, ACT_D = 3) so the publish sees g_p and act aligned as in the uncut leaf.
//   LEAF RESULT LATENCY +7 edges: n sb_bank leaf-0 lane (g0m, bits [49:0] of every 150-b slot) and s gout[49:0]
//   (leaf-1 lane) and therefore gout[99:50] (leaf 0 via the seam) are +7; the pass lanes (gin -> gpm -> gout[199:100]),
//   rout_n / rout_s / bout and the landing slot valids are +0 (unchanged).  1.2 GHz kept; no other cycle changes.
// MUT (bench only): 1 = lc tct control not re-aligned (BF16 sums one edge late at the tree), 2 = lc block-dot result
//                   not re-aligned, 3 = glue act delay one short.
`ifndef OT_RP4_AR
`ifdef OT_SMH_RP4_SRST
`define OT_RP4_AR(c, r) posedge c
`else
`define OT_RP4_AR(c, r) posedge c or negedge r
`endif
`endif

// ---------------------------------------------------------------------------------------------------------------------
// hnx_rp3h_xs: lane front + shared x store (P = 3), body of hnx_rp4lp4_lfx up to the x store outputs (verbatim)
module hnx_rp3h_xs #(parameter integer MUT = 0) (
    input  wire clk, input wire rst_lf,
    input  wire [25:0] st, input wire [817:0] rl1, input wire [2068:0] bk1,
    output wire [2:0] act,
    output wire [12:0] rst_ln,                        // reset copies rr[12:1] (lane p: {r_x, r_g, r_tcc, r_bdc})
    // lane-core operand buses, one copy per lane p (block-dot ops + BF16 tree control)
    output wire [3*1102-1:0] lc_op,
    // BF16 column-half operand buses, one copy per (lane p, half h): {v, first, w[127:0], x[127:0]}
    output wire [6*258-1:0] tl_op
);
    localparam integer P = 3, TAGW = 16, LBS = 2, LSB = 16;
    wire rst_n = rst_lf;
    wire sel = bk1[2068] && (bk1[2060:2048] == 13'd0);
    reg [P-1:0] tgt_q, act_q;
    always @(posedge clk)
        if (!rst_n) begin tgt_q <= {{(P-1){1'b0}}, 1'b1}; act_q <= {{(P-1){1'b0}}, 1'b1}; end
        else if (sel) begin tgt_q <= bk1[P-1:0]; act_q <= bk1[8 +: P]; end
    (* keep *) reg [817:0] rq;
    (* keep *) reg bv;
    (* keep *) reg [2067:0] bd;
    (* keep *) reg [P-1:0] wl;
    always @(posedge clk) rq <= rl1;
    always @(posedge clk)
        if (!rst_n) bv <= 1'b0;
        else bv <= bk1[2068] && !sel && (|tgt_q);
    always @(posedge clk) begin bd <= bk1[2067:0]; wl <= tgt_q; end
    (* keep *) reg [1+4*P-1:0] rr;
    always @(posedge clk) rr <= {(1+4*P){rst_n}};
    assign act = act_q;
    assign rst_ln = rr;
    wire iv_b, iv_f, ifirst, ilast, ifp4, ifirst_e, ilast_e;
    wire [TAGW-1:0] itag, itag_e;
    localparam integer PW = (P + 1) / 2, PEW = (P - PW) > 0 ? (P - PW) : 1;
    wire iv_fw, ifirst_w, ilast_w;
    wire [TAGW-1:0] itag_w;
    wire [LBS*266-1:0] iwb;
    wire [P*LBS*266-1:0] ixb;
    wire [LSB*16-1:0] iwf_e, iwf_w;
    wire [PEW*LSB*16-1:0] ixf_e;
    wire [PW*LSB*16-1:0] ixf_w;
    hnx_xs3 u_xs (.clk(clk), .rst_a(rr[0]), .xs_a1(st[8:0]), .xs_g1(st[13:9]),
        .xs_a2(st[20:14]), .xs_g2(st[25:21]), .rl1(rq), .bk1({bv, bd}), .ohl1(bd[2060:2048]), .wl(wl),
        .o_iv_b(iv_b), .o_iv_f(iv_f), .o_ifirst(ifirst), .o_ilast(ilast), .o_ifp4(ifp4), .o_itag(itag), .o_iwb(iwb), .o_ixb(ixb),
        .o_iwf_e(iwf_e), .o_ixf_e(ixf_e), .o_iwf_w(iwf_w), .o_ixf_w(ixf_w),
        .o_ifirst_e(ifirst_e), .o_ilast_e(ilast_e), .o_itag_e(itag_e),
        .o_iv_fw(iv_fw), .o_ifirst_w(ifirst_w), .o_ilast_w(ilast_w), .o_itag_w(itag_w));
    genvar p, h;
    generate for (p = 0; p < P; p = p + 1) begin : g_ln
        wire sv_f = (p < PW) ? iv_fw : iv_f, sfirst = (p < PW) ? ifirst_w : ifirst_e, slast = (p < PW) ? ilast_w : ilast_e;
        wire [TAGW-1:0] stag = (p < PW) ? itag_w : itag_e;
        wire [LSB*16-1:0] swf = (p < PW) ? iwf_w : iwf_e;
        wire [LSB*16-1:0] sxf = (p < PW) ? ixf_w[((p < PW) ? p : 0)*LSB*16 +: LSB*16] : ixf_e[((p < PW) ? 0 : p - PW)*LSB*16 +: LSB*16];
        // lc_op lane p = {iv_b, ifirst, ilast, ifp4, itag, iwb, ixb[p], sv_f, slast, stag}  (1 + 3 + 16 + 532 + 532 + 1 + 1 + 16)
        assign lc_op[p*1102 +: 1102] = {iv_b, ifirst, ilast, ifp4, itag, iwb, ixb[p*LBS*266 +: LBS*266], sv_f, slast, stag};
        for (h = 0; h < 2; h = h + 1) begin : g_h
            assign tl_op[(2*p+h)*258 +: 258] = {sv_f, sfirst, swf[h*128 +: 128], sxf[h*128 +: 128]};
        end
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// hnx_rp3h_tl: one BF16 column half (the tcc hard child ot_hbm_accel_smh_tcl, verbatim).  Its input face flops are the
// lane's xf_v / xf_first / xf_w / xf_x XREL station (the face flop carries no reset: v is flushed by the reset-held xs).
module hnx_rp3h_tl (
    input wire clk, input wire rst_tcc,
    input wire [257:0] op,                           // {v, first, w[127:0], x[127:0]}
    output wire [255:0] sum_o, output wire lfault
);
    ot_hbm_accel_smh_tcl u_h (.clk(clk), .rst_a(rst_tcc), .i_v(op[257]), .i_first(op[256]), .i_w(op[255:128]),
        .i_x(op[127:0]), .sum_o(sum_o), .lfault(lfault));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// hnx_rp3h_lc: one lane core (lfx g_ln[p] body without the tcc column halves)
module hnx_rp3h_lc #(parameter integer MUT = 0) (
    input wire clk, input wire rst_bdc, input wire rst_tcc, input wire rst_g, input wire rst_x,
    input wire [1101:0] op,                          // hnx_rp3h_xs lc_op lane p
    input wire [255:0] sum0, input wire [255:0] sum1, input wire lf0, input wire lf1,
    output wire [49:0] g
);
    localparam integer TAGW = 16, LBS = 2;
    wire r_bdc = rst_bdc, r_tcc = rst_tcc, r_g = rst_g, r_x = rst_x;
    wire iv_b = op[1101], ifirst = op[1100], ilast = op[1099], ifp4 = op[1098];
    wire [TAGW-1:0] itag = op[1097 -: 16];
    wire [LBS*266-1:0] iwb = op[1081 -: 532], ixb = op[549 -: 532];
    wire sv_f = op[17], slast = op[16];
    wire [TAGW-1:0] stag = op[15:0];
    reg xb_v, xf_v, xb_first, xb_last, xb_fp4, xf_last;
    reg [TAGW-1:0] xb_tag, xf_tag;
    reg [LBS*266-1:0] xb_w, xb_x;
    always @(`OT_RP4_AR(clk, r_x)) if (!r_x) xb_v <= 0; else xb_v <= iv_b;
    always @(`OT_RP4_AR(clk, r_x)) if (!r_x) xf_v <= 0; else xf_v <= sv_f;
    always @(posedge clk) begin
        xb_first <= ifirst; xb_last <= ilast; xb_fp4 <= ifp4; xb_tag <= itag;
        xb_w <= iwb; xb_x <= ixb;
        xf_last <= slast; xf_tag <= stag;
    end
    // LC_FD: BF16 tree control +1 (pure delay) to meet the column-half sums (tl seam: +1 operand, +2 sums)
    reg fd_v, fd_last; reg [TAGW-1:0] fd_tag;
    always @(`OT_RP4_AR(clk, r_x)) if (!r_x) fd_v <= 0; else fd_v <= xf_v;
    always @(posedge clk) begin fd_last <= xf_last; fd_tag <= xf_tag; end
    wire t_v = (MUT == 1) ? xf_v : fd_v, t_last = (MUT == 1) ? xf_last : fd_last;
    wire [TAGW-1:0] t_tag = (MUT == 1) ? xf_tag : fd_tag;
    wire bov0, bfault0, fov, ffault;
    wire [31:0] by0, fy;
    wire [TAGW-1:0] btag0, ftag;
    ot_hbm_accel_smh_bdc u_bdc (.clk(clk), .rst_a(r_bdc), .i_v(xb_v), .i_first(xb_first), .i_last(xb_last), .i_fp4(xb_fp4),
        .i_tag(xb_tag), .i_w(xb_w), .i_x(xb_x), .ov(bov0), .y(by0), .otag(btag0), .fault(bfault0));
    // block-dot result +1 (pure delay) to meet the BF16 result (+3 vs +2)
    reg bd_v, bd_f; reg [31:0] bd_y; reg [TAGW-1:0] bd_t;
    always @(`OT_RP4_AR(clk, r_g)) if (!r_g) begin bd_v <= 1'b0; bd_f <= 1'b0; end else begin bd_v <= bov0; bd_f <= bfault0; end
    always @(posedge clk) begin bd_y <= by0; bd_t <= btag0; end
    wire bov = (MUT == 2) ? bov0 : bd_v, bfault = (MUT == 2) ? bfault0 : bd_f;
    wire [31:0] by = (MUT == 2) ? by0 : bd_y;
    wire [TAGW-1:0] btag = (MUT == 2) ? btag0 : bd_t;
    ot_hbm_accel_smh_tct u_tr (.clk(clk), .rst_a(r_tcc), .i_v(t_v), .i_last(t_last), .i_tag(t_tag), .sum_i({sum1, sum0}),
        .lf_a(lf0), .lf_b(lf1), .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
    reg gv_q, gf_q;
    reg [31:0] gy_q;
    reg [TAGW-1:0] gt_q;
    always @(`OT_RP4_AR(clk, r_g))
        if (!r_g) begin gv_q <= 1'b0; gf_q <= 1'b0; end
        else begin gv_q <= bov | fov; gf_q <= bfault | ffault | (bov & fov); end
    always @(posedge clk) begin gy_q <= bov ? by : fy; gt_q <= bov ? btag : ftag; end
    assign g = {gv_q, gf_q, gy_q, gt_q};
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// act delay of the glue (pure delay, reset like act_q in the front: 3'b001)
module hnx_rp3h_actd #(parameter integer D = 3) (input wire clk, input wire rst_n, input wire [2:0] d, output wire [2:0] q);
    reg [2:0] r [0:D-1];
    integer j;
    always @(posedge clk)
        if (!rst_n) for (j = 0; j < D; j = j + 1) r[j] <= 3'b001;
        else begin r[0] <= d; for (j = 1; j < D; j = j + 1) r[j] <= r[j-1]; end
    assign q = r[D-1];
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// hnx_rp3h_gn: hnx_rp3lp3h_n__fcore without u_lf0 (verbatim) + the leaf publish
module hnx_rp3h_gn #(parameter integer MUT = 0) (
    input wire ck_n, input wire rst_n,
    input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
    input wire [817:0] rin_n, input wire [2068:0] bin, input wire [99:0] gin,
    output wire [817:0] rout_n, output wire [2068:0] bout,
    output wire [599:0] sb_bank, output wire [3:0] sb_vld,
    // leaf seam (to / from the leaf sub-blocks)
    output wire rst_lf, output wire [25:0] lf_st, output wire [817:0] lf_rl1, output wire [2068:0] lf_bk1,
    input wire [2:0] lf_act, input wire [149:0] lf_g
);
    wire [25:0] st_n;
    wire [817:0] rl_n, rl1_n, rpm_n;
    wire [2068:0] bin_l, bm, bk1_n;
    wire [49:0] g0, g0m;
    wire [99:0] gpm;
    wire [11:0] epo_w;
    wire lpr_root; ot_pl_pad #(.W(1), .N(1)) u_lpr_root (.ck(ck_n), .d(rst_n), .q(lpr_root));
    wire lpr_n;    ot_pl_pad #(.W(1), .N(1)) u_lpr_n (.ck(ck_n), .d(lpr_root), .q(lpr_n));
    hnx_rp4l_strap u_sr_n (.clk(ck_n), .d({xs_g2, xs_a2, xs_g1, xs_a1}), .q(st_n));
    hnx_rp4l_pinrow u_pr_n (.clk(ck_n), .rst_n(lpr_n), .d(rin_n), .q(rl_n));
    hnx_rp4l_pinbeat u_pb (.clk(ck_n), .rst_n(lpr_n), .d(bin), .q(bin_l));
    ot_smh_tr_group_row_w u_row0 (.clk(ck_n), .rst_a(lpr_n), .d(rl_n), .first(rl1_n), .last(rpm_n));
    ot_smh_tr_group_beat_e u_beat_t (.clk(ck_n), .rst_a(lpr_n), .d(bin_l), .last(bm));
    ot_smh_tr_group_land u_land_n (.clk(ck_n), .rst_a(lpr_n), .d(bin_l), .q(bk1_n));
    ot_smh_tr_group_row_e u_rowe0 (.clk(ck_n), .rst_a(lpr_n), .d(rpm_n), .last(rout_n));
    ot_smh_tr_group_beat_e u_beate (.clk(ck_n), .rst_a(lpr_n), .d(bm), .last(bout));
    assign rst_lf = lpr_n; assign lf_st = st_n; assign lf_rl1 = rl1_n; assign lf_bk1 = bk1_n;
    wire [2:0] act_d;
    hnx_rp3h_actd #(.D((MUT == 3) ? 2 : 3)) u_actd (.clk(ck_n), .rst_n(lpr_n), .d(lf_act), .q(act_d));
    hnx_rp4lp4_pub #(.P(3), .LSKEW(8)) u_pub (.clk(ck_n), .rst_n(lpr_n), .g_p(lf_g), .act(act_d), .g(g0));
    hnx_rp4l_gn #(.NREL(2)) u_gn (.clk(ck_n), .rst_n(lpr_n), .g0(g0), .gin(gin), .g0m(g0m), .gpm(gpm));
    ot_pl_land_w #(.W(150), .D(4)) u_sb_w (.ck(ck_n), .rsi(lpr_n), .i({gpm, g0m}), .bank(sb_bank), .epo(epo_w), .vld(sb_vld));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// hnx_rp3h_gs: hnx_rp3lp3h_s__fcore without u_lf1 (verbatim, SYNTHESIS form: slot epochs are assertion-only) + publish
module hnx_rp3h_gs #(parameter integer MUT = 0) (
    input wire ck_s, input wire rst_n,
    input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
    input wire [817:0] rin_s, input wire [2068:0] bin,
    input wire [599:0] sb_bank, input wire [3:0] sb_vld,
    output wire [817:0] rout_s, output wire [199:0] gout,
    output wire rst_lf, output wire [25:0] lf_st, output wire [817:0] lf_rl1, output wire [2068:0] lf_bk1,
    input wire [2:0] lf_act, input wire [149:0] lf_g
);
    wire [25:0] st_s;
    wire [817:0] rl_s, rl1_s, rpm_s;
    wire [2068:0] bin_c, bk1_s;
    wire [49:0] g1, g1p;
    wire [149:0] sb_o;
    wire [11:0] epo_r = 12'd0;
    wire lpr_root; ot_pl_pad #(.W(1), .N(1)) u_lpr_root (.ck(ck_s), .d(rst_n), .q(lpr_root));
    wire lpr_s;    ot_pl_pad #(.W(1), .N(1)) u_lpr_s (.ck(ck_s), .d(lpr_root), .q(lpr_s));
    wire lpr_c_u_gs; ot_pl_pad #(.W(1), .N(3)) u_lprc_u_gs (.ck(ck_s), .d(lpr_s), .q(lpr_c_u_gs));
    hnx_rp4l_strap u_sr_s (.clk(ck_s), .d({xss_g2, xss_a2, xss_g1, xss_a1}), .q(st_s));
    hnx_rp4l_pinrow u_pr_s (.clk(ck_s), .rst_n(lpr_s), .d(rin_s), .q(rl_s));
    hnx_rp4l_pinbeat u_pbs (.clk(ck_s), .rst_n(lpr_s), .d(bin), .q(bin_c));
    ot_smh_tr_group_row_w u_row1 (.clk(ck_s), .rst_a(lpr_s), .d(rl_s), .first(rl1_s), .last(rpm_s));
    ot_smh_tr_group_land u_land_s (.clk(ck_s), .rst_a(lpr_s), .d(bin_c), .q(bk1_s));
    ot_smh_tr_group_row_e u_rowe1 (.clk(ck_s), .rst_a(lpr_s), .d(rpm_s), .last(rout_s));
    assign rst_lf = lpr_s; assign lf_st = st_s; assign lf_rl1 = rl1_s; assign lf_bk1 = bk1_s;
    wire [2:0] act_d;
    hnx_rp3h_actd #(.D((MUT == 3) ? 2 : 3)) u_actd (.clk(ck_s), .rst_n(lpr_s), .d(lf_act), .q(act_d));
    hnx_rp4lp4_pub #(.P(3), .LSKEW(8)) u_pub (.clk(ck_s), .rst_n(lpr_s), .g_p(lf_g), .act(act_d), .g(g1));
    ot_pl_land_r #(.W(150), .D(4), .K(2)) u_sb_r (.ck(ck_s), .rsi(lpr_s), .bank(sb_bank), .epo(epo_r), .vld(sb_vld), .o(sb_o));
    hnx_pl_pad_ring #(.W(50), .N(3)) u_lpp_g1 (.ck(ck_s), .rst_n(lpr_s), .d(g1), .q(g1p));
    hnx_rp4l_gs #(.NREL(2)) u_gs (.clk(ck_s), .rst_n(lpr_c_u_gs), .g1in(g1p), .g0m(sb_o[49:0]), .gpm(sb_o[149:50]), .gout(gout));
endmodule
