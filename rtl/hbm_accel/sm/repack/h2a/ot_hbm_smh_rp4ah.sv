// L2H-SMATT/RP4A (LEAD3-HBM, 10-19; RELEASE_TREE H.STA.BLK.14.6): the HBM SM ATTENTION tile rp4a (the die binds smh_attn
// x16) as TWO HARDENED HALVES, built from the rp4 halves (rtl/hbm_accel/sm/repack/h2/ot_hbm_smh_rp4h.sv, L2H-SM9).
//
// Same split, crossing, reset depths and lp latencies as ot_hbm_smh_rp4h_n / _s; only the LEAF changes: ot_rp4a_leaf is
// the attention leaf of ot_hbm_sm_attn_leafh (H-SM-ATT r2, owner option B) with its native column inlined so every hard
// child is a direct instance of the leaf:
//   u_xs    ot_hbm_accel_smh_xs      x store (final: smh_xs_ring_p192c_1019, 475.2 x 302.4; NOT CLOSED -> kit stand-in)
//   u_bdc   ot_hbm_accel_smh_bdc     block-dot column (closed smh_bdc_ref_p50)
//   u_h0/1  ot_hbm_accel_smh_tcl_gu  BF16 column halves (closed smh_tcl_gu_ref)
//   u_qk    ot_hbm_accel_smh_tct     QK reduction tree (closed smh_tct_ref_p45)
//   u_merge ot_hbm_sm_pv_merge_s3    PV merge, SAFE 2 / TURNREG 1 / PUBLISH 1 (closed smh_pvm_ref_s4a, record cf9c5a54b)
// soft: the xs -> column operand registers, the PV-x broadcast select (static attn_column strap), the publication delay
// line (static attn_row tap), the PV sum capture (closed-tct LL = 16 alignment) and the G1 gather select.
// Differences from ot_hbm_sm_attn_leafh (all cycle-neutral on a compiled schedule):
//   * every glue reset is SYNCHRONOUS from a kept per-consumer copy (rp4 OT_SMH_RP4_SRST lesson: no async RESETN removal
//     check across clock roots); the copies are the kept rq registers of the rp4 leaf;
//   * the PV merge is the closed SAFE 2 successor ot_hbm_sm_pv_merge_s3 (fold write-back +1 cycle, already in the Qwen
//     h128 calendar, HBM-PVM-SAFE 10-19), not the original ot_hbm_sm_pv_merge;
//   * attn_column / attn_row are STATIC straps registered at the face (u_as*, 2 kept stages) like the x-store straps.
// INT8 (ENABLE_INT8, smh_int8_s2 CLOSED) lives in the SM front (ot_hbm_accel_smh_attn g_int8), NOT in this tile.
// MUT (bench only, 0 in every kit): 1/2/3 as ot_hbm_smh_rp4h (bin crossing short / gpm crossing short / leaf-1 rl1 pad
// short); 5 = n-half attn strap one row off (leaf 0 publishes as row 1: a wrong static strap must be visible).
`timescale 1ns/1ps

// static attention strap: two kept face stages (no reset: static configuration, compared after warm-up)
module ot_rp4a_astrap (input wire clk, input wire [4:0] d, output wire [4:0] q);
    (* keep *) reg [4:0] s0, s1;
    always @(posedge clk) begin s0 <= d; s1 <= s0; end
    assign q = s1;
endmodule

// PV sum capture (as ot_hbm_sm_attn_sum_capture, synchronous reset): event at the closed tct's LL = 16 boundary
module ot_rp4a_cap #(parameter integer TAGW = 16) (
    input wire clk, input wire rst_n, input wire i_v, input wire i_last, input wire i_run_first, input wire i_run_last,
    input wire [TAGW-1:0] i_tag, input wire [511:0] sum_i,
    output wire event_v, output wire [511:0] event_sum, output wire [TAGW-1:0] event_tag);
    localparam integer LL = 16;
    reg jv, jlast, v_q, last_q, last_q2;
    reg [TAGW-1:0] jtag, tag_q, tag_q2;
    always @(posedge clk)
        if (!rst_n) begin jv <= 0; v_q <= 0; last_q <= 0; last_q2 <= 0; end
        else begin jv <= i_v; v_q <= jv; last_q <= jv && jlast; last_q2 <= last_q; end
    always @(posedge clk) begin
        jlast <= i_last;
        jtag <= {1'b1, i_run_first, i_run_last, i_tag[TAGW-4:0]};
        tag_q <= jtag; tag_q2 <= tag_q;
    end
    reg [LL-1:0] vl;
    reg [TAGW-1:0] tl [0:LL-1];
    integer k;
    always @(posedge clk) begin
        if (!rst_n) vl <= {LL{1'b0}}; else vl <= {vl[LL-2:0], last_q2};
        tl[0] <= tag_q2;
        for (k = 1; k < LL; k = k + 1) tl[k] <= tl[k-1];
    end
    reg [511:0] sum_q2;
    always @(posedge clk) sum_q2 <= sum_i;
    assign event_sum = sum_q2;
    assign event_v = vl[LL-1];
    assign event_tag = tl[LL-1];
endmodule

// one attention leaf on one clock; st = x-store straps {g2, a2, g1, a1}, at = {attn_row[1:0], attn_column[2:0]},
// g = {gv, gf, gy, gt}
module ot_rp4a_leaf (input wire clk, input wire rst_n, input wire [25:0] st, input wire [4:0] at,
    input wire [817:0] rl1, input wire [2068:0] bk1, output wire [49:0] g);
    localparam integer LBS = 2, LSB = 16, IL = 8, TAGW = 16, NBEAT = 13;
    wire [2:0] attn_column = at[2:0];
    wire [1:0] attn_row = at[4:3];
    (* keep *) reg [4:0] rq;
    always @(posedge clk) rq <= {5{rst_n}};
    wire r_xs = rq[0], r_bdc = rq[1], r_tcc = rq[2], r_g = rq[3], r_x = rq[4];
    wire iv_b, iv_f, ifirst, ilast, ifp4, ifirst_e, ilast_e;
    wire [TAGW-1:0] itag, itag_e;
    wire [LBS*266+LSB*16-1:0] iw, ix;
    ot_hbm_accel_smh_xs #(.TAGW(TAGW), .NBEAT(NBEAT)) u_xs (.clk(clk), .rst_a(r_xs), .xs_a1(st[8:0]), .xs_g1(st[13:9]),
        .xs_a2(st[20:14]), .xs_g2(st[25:21]), .rl1(rl1), .bk1(bk1), .ohl1(bk1[2060:2048]), .o_iv_b(iv_b), .o_iv_f(iv_f),
        .o_ifirst(ifirst), .o_ilast(ilast), .o_ifp4(ifp4), .o_itag(itag), .o_iw(iw), .o_ix(ix), .o_ifirst_e(ifirst_e),
        .o_ilast_e(ilast_e), .o_itag_e(itag_e));
    wire marker = iv_f && ifp4;
    wire input_pv = marker && iw[129];
    wire input_arithmetic = iv_f && (!marker || iw[137]);
    reg bv, bfirst, blast, bfp4, fv, ffirst, fqlast, fplast, frfirst, frlast;
    reg [TAGW-1:0] btag, ftag;
    reg [LBS*266-1:0] bw, bx;
    reg [255:0] fw, fx;
    reg [4:0] publish0;
    reg fold0; reg [2:0] fold0_a, fold0_b;
    always @(posedge clk)
        if (!r_x) begin bv <= 0; fv <= 0; publish0 <= 0; fold0 <= 0; end
        else begin
            bv <= iv_b; fv <= input_arithmetic;
            publish0 <= {iw[145], marker && iw[134], iw[131], iw[136:135]};
            fold0 <= marker && iw[138];
        end
    always @(posedge clk) begin
        bfirst <= ifirst; blast <= ilast; bfp4 <= ifp4; btag <= itag;
        bw <= iw[0 +: LBS*266]; bx <= ix[0 +: LBS*266];
        fold0_a <= iw[141:139]; fold0_b <= iw[144:142];
        ffirst <= ifirst_e; fqlast <= ilast_e && !input_pv; fplast <= ilast_e && input_pv;
        frfirst <= iw[132]; frlast <= iw[133]; ftag <= itag_e;
        fw <= iw[LBS*266 +: 256];
        fx <= input_pv ? {16{iw[16*attn_column +: 16]}} : ix[LBS*266 +: 256];
    end
    wire bov, bfault, fov, qf, mf, ps_v;
    wire [31:0] by, fy, ps_data;
    wire [TAGW-1:0] bt, ft, ps_tag;
    wire [3:0] ps_word;
    wire [2:0] ps_slot;
    ot_hbm_accel_smh_bdc #(.LBS(LBS), .IL(IL), .TAGW(TAGW)) u_bdc (.clk(clk), .rst_a(r_bdc), .i_v(bv), .i_first(bfirst),
        .i_last(blast), .i_fp4(bfp4), .i_tag(btag), .i_w(bw), .i_x(bx), .ov(bov), .y(by), .otag(bt), .fault(bfault));
    // publication delay line: static tap {attn_row, 4'b0} (0 / 16 / 32 / 48)
    reg [4:0] pub_pipe [0:48];
    integer d;
    always @(posedge clk)
        if (!r_x) for (d = 0; d < 49; d = d + 1) pub_pipe[d] <= 0;
        else begin
            pub_pipe[0] <= publish0;
            for (d = 1; d < 49; d = d + 1) pub_pipe[d] <= pub_pipe[d-1];
        end
    wire [4:0] pc = pub_pipe[{attn_row, 4'b0000}];
    wire [2:0] selected_slot = pc[2] ? (pc[4] ? {2'b00, attn_column[0]} : {attn_column[0], pc[1:0]}) : attn_column;
    reg published_h128;
    always @(posedge clk) if (pc[3]) published_h128 <= pc[2];
    // native column (ot_hbm_sm_attn_native_col, inlined): closed tcl_gu halves, closed tct (QK), sum capture, PV merge
    wire [255:0] s0, s1;
    wire lf0, lf1;
    ot_hbm_accel_smh_tcl_gu u_h0 (.clk(clk), .rst_a(r_tcc), .i_v(fv), .i_first(ffirst), .i_w(fw[127:0]), .i_x(fx[127:0]),
        .sum_o(s0), .lfault(lf0));
    ot_hbm_accel_smh_tcl_gu u_h1 (.clk(clk), .rst_a(r_tcc), .i_v(fv), .i_first(ffirst), .i_w(fw[255:128]),
        .i_x(fx[255:128]), .sum_o(s1), .lfault(lf1));
    ot_hbm_accel_smh_tct #(.TAGW(TAGW)) u_qk (.clk(clk), .rst_a(r_tcc), .i_v(fv), .i_last(fqlast), .i_tag(ftag),
        .sum_i({s1, s0}), .lf_a(lf0), .lf_b(lf1), .ov(fov), .y(fy), .otag(ft), .fault(qf));
    wire event_v;
    wire [511:0] event_sum;
    wire [TAGW-1:0] event_tag;
    ot_rp4a_cap #(.TAGW(TAGW)) u_cap (.clk(clk), .rst_n(r_tcc), .i_v(fv), .i_last(fplast), .i_run_first(frfirst),
        .i_run_last(frlast), .i_tag(ftag), .sum_i({s1, s0}), .event_v(event_v), .event_sum(event_sum), .event_tag(event_tag));
    wire pv_v;
    wire [511:0] pv_y;
    wire [TAGW-1:0] pv_tag;
    ot_hbm_sm_pv_merge_s3 #(.TAGW(TAGW), .LV(4), .PUBLISH(1), .TURNREG(1), .SAFE(2)) u_merge (.clk(clk), .rst_n(r_tcc),
        .ev(event_v), .sum(event_sum), .tag_d(event_tag), .pv_v(pv_v), .pv_y(pv_y), .pv_tag(pv_tag), .fault(mf),
        .pub_start(pc[3]), .pub_slot(selected_slot), .pub_v(ps_v), .pub_data(ps_data), .pub_word(ps_word),
        .pub_out_slot(ps_slot), .pub_tag(ps_tag), .fold_start(fold0), .fold_a(fold0_a), .fold_b(fold0_b));
    wire ffault = qf | mf;
    wire [11:0] scalar_row = published_h128 ? {4'd0, ps_slot[1:0], attn_row, ps_word} : {6'd0, attn_row, ps_word};
    reg gv_q, gf_q;
    reg [31:0] gy_q;
    reg [TAGW-1:0] gt_q;
    always @(posedge clk)
        if (!r_g) begin gv_q <= 0; gf_q <= 0; end
        else begin gv_q <= bov | fov | ps_v; gf_q <= bfault | ffault | (bov && fov) | (ps_v && (bov || fov)); end
    always @(posedge clk) begin
        gy_q <= ps_v ? ps_data : bov ? by : fy;
        gt_q <= ps_v ? {scalar_row, 1'b1, 3'd0} : bov ? bt : ft;
    end
    assign g = {gv_q, gf_q, gy_q, gt_q};
endmodule

// n half: ot_hbm_smh_rp4h_n with the attention leaf; attn = {attn_rowbase[1:0], attn_column[2:0]} (static strap)
module ot_hbm_smh_rp4ah_n #(parameter integer MUT = 0, parameter integer SOFTBEAT = 1) (
    input wire clk, input wire rst_n,
    input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2, input wire [4:0] attn,
    input wire [817:0] rin_n, input wire [2068:0] bin, input wire [99:0] gin,
    output wire [817:0] rout_n, output wire [2068:0] bout,
    output wire [2068:0] xo_b, output wire [49:0] xo_g0, output wire [99:0] xo_gp
);
    wire [10:0] r;
    ot_rp4h_rst #(.NC(11)) u_rst (.clk(clk), .rst_n(rst_n), .r(r));
    wire [25:0] st_n;
    wire [4:0] at_n;
    wire [817:0] rl_n, rl1_n, rpm_n;
    wire [2068:0] bin_l, bm, bk1_n, xb1, xb2;
    wire [49:0] g0, g0m;
    wire [99:0] gpm;
    ot_rp4l_strap u_sr_n (.clk(clk), .d({xs_g2, xs_a2, xs_g1, xs_a1}), .q(st_n));
    ot_rp4a_astrap u_as_n (.clk(clk), .d((MUT == 5) ? {attn[4:3] + 2'd1, attn[2:0]} : attn), .q(at_n));
    ot_rp4l_pinrow u_pr_n (.clk(clk), .rst_n(r[0]), .d(rin_n), .q(rl_n));
    ot_rp4l_pinbeat u_pb (.clk(clk), .rst_n(r[1]), .d(bin), .q(bin_l));
    ot_smh_tr_group_row_w u_row0 (.clk(clk), .rst_a(r[2]), .d(rl_n), .first(rl1_n), .last(rpm_n));
    wire [2068:0] bt1, be1;
    generate if (SOFTBEAT != 0) begin : g_sbeat
        ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_bt1 (.clk(clk), .rst_n(r[3]), .d(bin_l), .q(bt1));
        ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_bt2 (.clk(clk), .rst_n(r[3]), .d(bt1), .q(bm));
        ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_be1 (.clk(clk), .rst_n(r[6]), .d(bm), .q(be1));
        ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_be2 (.clk(clk), .rst_n(r[6]), .d(be1), .q(bout));
    end else begin : g_hbeat
        ot_smh_tr_group_beat_e u_beat_t (.clk(clk), .rst_a(r[3]), .d(bin_l), .last(bm));
        ot_smh_tr_group_beat_e u_beate (.clk(clk), .rst_a(r[6]), .d(bm), .last(bout));
    end endgenerate
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_landn (.clk(clk), .rst_n(r[4]), .d(bin_l), .q(bk1_n));
    ot_smh_tr_group_row_e u_rowe0 (.clk(clk), .rst_a(r[5]), .d(rpm_n), .last(rout_n));
    ot_rp4a_leaf u_lf0 (.clk(clk), .rst_n(r[7]), .st(st_n), .at(at_n), .rl1(rl1_n), .bk1(bk1_n), .g(g0));
    ot_rp4l_gn u_gn (.clk(clk), .rst_n(r[8]), .g0(g0), .gin(gin), .g0m(g0m), .gpm(gpm));
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_xb1 (.clk(clk), .rst_n(r[9]), .d(bin_l), .q(xb1));
    generate if (MUT == 1) begin : g_m1
        assign xb2 = xb1;
    end else begin : g_xb2
        ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_xb2 (.clk(clk), .rst_n(r[9]), .d(xb1), .q(xb2));
    end endgenerate
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_xbo (.clk(clk), .rst_n(r[9]), .d(xb2), .q(xo_b));
    ot_rp4h_xreg #(.W(50), .VMASK({2'b11, 48'b0})) u_xgo (.clk(clk), .rst_n(r[10]), .d(g0m), .q(xo_g0));
    ot_rp4h_xreg #(.W(100), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_xpo (.clk(clk), .rst_n(r[10]), .d(gpm), .q(xo_gp));
endmodule

// s half: ot_hbm_smh_rp4h_s with the attention leaf (leaf 1 = attn_rowbase + 1)
module ot_hbm_smh_rp4ah_s #(parameter integer MUT = 0) (
    input wire clk, input wire rst_n,
    input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2, input wire [4:0] attn,
    input wire [817:0] rin_s, output wire [817:0] rout_s,
    input wire [2068:0] xi_b, input wire [49:0] xi_g0, input wire [99:0] xi_gp,
    output wire [199:0] gout
);
    wire [7:0] r;
    ot_rp4h_rst #(.NC(8)) u_rst (.clk(clk), .rst_n(rst_n), .r(r));
    wire r_land, r_lf1, r_gs;
    ot_rp4h_rpad #(.N(3)) u_rp_land (.clk(clk), .d(r[3]), .q(r_land));
    ot_rp4h_rpad #(.N(3)) u_rp_lf1 (.clk(clk), .d(r[4]), .q(r_lf1));
    ot_rp4h_rpad #(.N(3)) u_rp_gs (.clk(clk), .d(r[5]), .q(r_gs));
    wire [25:0] st_s, st_s_p;
    wire [4:0] at_s;
    wire [817:0] rl_s, rl1_s, rl1_s_p, rpm_s;
    wire [2068:0] bk1_s;
    wire [49:0] g1, xg, g0m;
    wire [99:0] xp, gpm;
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_lands (.clk(clk), .rst_n(r_land), .d(xi_b), .q(bk1_s));
    ot_rp4h_xreg #(.W(50), .VMASK({2'b11, 48'b0})) u_xgi (.clk(clk), .rst_n(r[6]), .d(xi_g0), .q(xg));
    ot_rp4h_xreg #(.W(50), .VMASK({2'b11, 48'b0})) u_xg2 (.clk(clk), .rst_n(r[6]), .d(xg), .q(g0m));
    ot_rp4h_xreg #(.W(100), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_xpi (.clk(clk), .rst_n(r[7]), .d(xi_gp), .q(xp));
    wire [99:0] xp2;
    ot_rp4h_xreg #(.W(100), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_xp2 (.clk(clk), .rst_n(r[7]), .d(xp), .q(xp2));
    assign gpm = (MUT == 2) ? xp : xp2;
    ot_rp4l_strap u_sr_s (.clk(clk), .d({xss_g2, xss_a2, xss_g1, xss_a1}), .q(st_s));
    ot_rp4a_astrap u_as_s (.clk(clk), .d({attn[4:3] + 2'd1, attn[2:0]}), .q(at_s));
    ot_rp4l_pinrow u_pr_s (.clk(clk), .rst_n(r[0]), .d(rin_s), .q(rl_s));
    ot_smh_tr_group_row_w u_row1 (.clk(clk), .rst_a(r[1]), .d(rl_s), .first(rl1_s), .last(rpm_s));
    ot_smh_tr_group_row_e u_rowe1 (.clk(clk), .rst_a(r[2]), .d(rpm_s), .last(rout_s));
    ot_pl_pad #(.W(818), .N((MUT == 3) ? 2 : 3)) u_pp_rl1 (.ck(clk), .d(rl1_s), .q(rl1_s_p));
    ot_pl_pad #(.W(26), .N(3)) u_pp_st (.ck(clk), .d(st_s), .q(st_s_p));
    ot_rp4a_leaf u_lf1 (.clk(clk), .rst_n(r_lf1), .st(st_s_p), .at(at_s), .rl1(rl1_s_p), .bk1(bk1_s), .g(g1));
    ot_rp4l_gs u_gs (.clk(clk), .rst_n(r_gs), .g1in(g1), .g0m(g0m), .gpm(gpm), .gout(gout));
endmodule

// the SM frame slot: both halves abutted (die binder form; also the bench DUT)
module ot_hbm_smh_rp4ah2 #(parameter integer MUT = 0, parameter integer SOFTBEAT = 1) (
    input wire rst_n, input wire [4:0] attn,
    input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
    input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
    input wire [817:0] rin_n, input wire [817:0] rin_s, input wire [2068:0] bin,
    output wire [817:0] rout_n, output wire [817:0] rout_s, output wire [2068:0] bout,
    input wire [99:0] gin, output wire [199:0] gout,
    input wire ck_n, input wire ck_s
);
    wire [2068:0] x_b; wire [49:0] x_g0; wire [99:0] x_gp;
    ot_hbm_smh_rp4ah_n #(.MUT(MUT), .SOFTBEAT(SOFTBEAT)) u_n (.clk(ck_n), .rst_n(rst_n), .xs_a1(xs_a1), .xs_g1(xs_g1),
        .xs_a2(xs_a2), .xs_g2(xs_g2), .attn(attn), .rin_n(rin_n), .bin(bin), .gin(gin), .rout_n(rout_n), .bout(bout),
        .xo_b(x_b), .xo_g0(x_g0), .xo_gp(x_gp));
    ot_hbm_smh_rp4ah_s #(.MUT(MUT)) u_s (.clk(ck_s), .rst_n(rst_n), .xss_a1(xss_a1), .xss_g1(xss_g1), .xss_a2(xss_a2),
        .xss_g2(xss_g2), .attn(attn), .rin_s(rin_s), .rout_s(rout_s), .xi_b(x_b), .xi_g0(x_g0), .xi_gp(x_gp), .gout(gout));
endmodule

// BENCH REFERENCE: the rp4 flat parent (ot_hbm_smh_rp4_flat: one clock, no split, hard land children) with the attention
// leaf; the halves must equal it cycle for cycle with the lp offsets (reset delayed 3, gout +3)
module ot_hbm_smh_rp4a_flat (input wire clk, input wire rst_n, input wire [4:0] attn,
    input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
    input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
    input wire [817:0] rin_n, input wire [817:0] rin_s, input wire [2068:0] bin,
    output wire [817:0] rout_n, output wire [817:0] rout_s, output wire [2068:0] bout,
    input wire [99:0] gin, output wire [199:0] gout);
    wire [25:0] st_n, st_s;
    wire [4:0] at_n, at_s;
    wire [817:0] rl_n, rl_s, rl1_n, rl1_s, rpm_n, rpm_s;
    wire [2068:0] bin_l, bm, bk1_n, bk1_s;
    wire [49:0] g0, g1, g0m;
    wire [99:0] gpm;
    ot_rp4l_strap u_sr_n (.clk(clk), .d({xs_g2, xs_a2, xs_g1, xs_a1}), .q(st_n));
    ot_rp4l_strap u_sr_s (.clk(clk), .d({xss_g2, xss_a2, xss_g1, xss_a1}), .q(st_s));
    ot_rp4a_astrap u_as_n (.clk(clk), .d(attn), .q(at_n));
    ot_rp4a_astrap u_as_s (.clk(clk), .d({attn[4:3] + 2'd1, attn[2:0]}), .q(at_s));
    ot_rp4l_pinrow u_pr_n (.clk(clk), .rst_n(rst_n), .d(rin_n), .q(rl_n));
    ot_rp4l_pinrow u_pr_s (.clk(clk), .rst_n(rst_n), .d(rin_s), .q(rl_s));
    ot_rp4l_pinbeat u_pb (.clk(clk), .rst_n(rst_n), .d(bin), .q(bin_l));
    ot_smh_tr_group_row_w u_row0 (.clk(clk), .rst_a(rst_n), .d(rl_n), .first(rl1_n), .last(rpm_n));
    ot_smh_tr_group_row_w u_row1 (.clk(clk), .rst_a(rst_n), .d(rl_s), .first(rl1_s), .last(rpm_s));
    ot_smh_tr_group_beat_e u_beat_t (.clk(clk), .rst_a(rst_n), .d(bin_l), .last(bm));
    ot_smh_tr_group_land u_land_n (.clk(clk), .rst_a(rst_n), .d(bin_l), .q(bk1_n));
    ot_smh_tr_group_land u_land_s (.clk(clk), .rst_a(rst_n), .d(bin_l), .q(bk1_s));
    ot_smh_tr_group_row_e u_rowe0 (.clk(clk), .rst_a(rst_n), .d(rpm_n), .last(rout_n));
    ot_smh_tr_group_row_e u_rowe1 (.clk(clk), .rst_a(rst_n), .d(rpm_s), .last(rout_s));
    ot_smh_tr_group_beat_e u_beate (.clk(clk), .rst_a(rst_n), .d(bm), .last(bout));
    ot_rp4a_leaf u_lf0 (.clk(clk), .rst_n(rst_n), .st(st_n), .at(at_n), .rl1(rl1_n), .bk1(bk1_n), .g(g0));
    ot_rp4a_leaf u_lf1 (.clk(clk), .rst_n(rst_n), .st(st_s), .at(at_s), .rl1(rl1_s), .bk1(bk1_s), .g(g1));
    ot_rp4l_gn u_gn (.clk(clk), .rst_n(rst_n), .g0(g0), .gin(gin), .g0m(g0m), .gpm(gpm));
    ot_rp4l_gs u_gs (.clk(clk), .rst_n(rst_n), .g1in(g1), .g0m(g0m), .gpm(gpm), .gout(gout));
endmodule
