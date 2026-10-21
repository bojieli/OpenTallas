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
// XB (kit default 1): the n half's bin -> S-face crossing runs from the W-face bin pins at the TOP of n (beside the x
// store's bk1 face) to the S face, ~1.4 mm: XB more kept relays (u_xb3) after u_xb2 keep it <= ~360 um a hop.  The s half
// is then 3 + XB edges behind n (lp: 3): its leaf-1 alignment pads (rl1, straps) and reset pads grow by XB and the leaf-1
// gather lane takes GN + GS - XB pads, so gout stays +(GN + GS) uniform.
// GN / GS (kit defaults 2 / 1): the attention leaf stack makes the halves 1,425.6 (n) / 1,123.2 (s) um tall (rp4h:
// 864-907 / 691-734), so the N->S gather lanes that cross a whole half would run 475-710 um a cycle (> 405 reach).  The n
// half adds GN kept relays on the leaf-0 and pass lanes (u_xgr / u_xpr, before the S-face out registers), the s half GS
// relays on the leaf-0 and pass lanes (u_xg3 / u_xp3, after u_xg2 / u_xp2) and GN + GS pads on the leaf-1 lane (u_g1p),
// so EVERY gout lane is +(GN + GS) edges vs the rp4h / lp record (kits: gout +6 instead of +3, all 4 lanes uniform, all
// other ports unchanged).  PRICED SCHEDULE CHANGE (checklist item 8): the front's per-hop result deskew grows by GN + GS
// per tile hop -> compiler / die schedule owner.  GN = GS = 0 = the rp4h latencies (bench comparison only).
// MUT (bench only, 0 in every kit): 1/2/3 as ot_hbm_smh_rp4h (bin crossing short / gpm crossing short / leaf-1 rl1 pad
// short); 5 = n-half attn strap one row off (leaf 0 publishes as row 1: a wrong static strap must be visible).
`timescale 1ns/1ps

// static attention strap: two kept face stages (no reset: static configuration, compared after warm-up)
module ot_rp4a_astrap (input wire clk, input wire [4:0] d, output wire [4:0] q);
    (* keep *) reg [4:0] s0, s1;
    always @(posedge clk) begin s0 <= d; s1 <= s0; end
    assign q = s1;
endmodule

// N kept relay stages (valid bits in VMASK sync-cleared); stage k = g_s[k].u_r (FIRM station groups match on it)
module ot_rp4a_relay #(parameter integer W = 50, parameter integer N = 1, parameter [W-1:0] VMASK = 0) (
    input wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
    wire [W-1:0] c [0:N];
    assign c[0] = d;
    genvar k;
    generate for (k = 0; k < N; k = k + 1) begin : g_s
        ot_rp4h_xreg #(.W(W), .VMASK(VMASK)) u_r (.clk(clk), .rst_n(rst_n), .d(c[k]), .q(c[k+1]));
    end endgenerate
    assign q = c[N];
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
// HBM-SMATT10 (10-20, H.STA.BLK.9.1 frame re-plan on the CLOSED XS bay 475.2 x 388.8): LR kept leaf-input relay stages.
// Every leaf input (rl1, bk1, st, at) and the leaf reset are delayed by the SAME LR edges, so ot_rp4a_leaf #(LR) equals
// ot_rp4a_leaf #(0) delayed by exactly LR edges (g +LR).  Why: rl1 runs from the row_w 'first' face (row band, y ~480)
// to the x store's W-face rl1 pins (~780..1080 in the MX x store): one cycle was 300-560 um (stand-in gate macro->macro
// -187 ps).  LR = 2 FIRM stations in the W channel keep every rl1 hop <= ~330 um.  ohl1 gets its OWN kept 13-bit copy
// (u_oh) so it can be stationed at the x-store W face apart from the 2,069-bit bk1 stages (stand-in reg->macro -360 ps).
// MUT 6 (bench only): rl1 one relay short -> must FAIL.  The halves pad gin by LR so every gout lane is +LR uniform.
module ot_rp4a_leaf #(parameter integer LR = 0, parameter integer MUT = 0, parameter integer OS = 0) (input wire clk, input wire rst_n,
    input wire [25:0] st, input wire [4:0] at, input wire [817:0] rl1, input wire [2068:0] bk1, output wire [49:0] g);
    generate if (LR == 0) begin : g_nolr
        ot_rp4a_leaf_core #(.OS(OS)) u_c (.clk(clk), .rst_n(rst_n), .st(st), .at(at), .rl1(rl1), .bk1(bk1), .ohl(bk1[2060:2048]), .g(g));
    end else begin : g_lr
        (* keep *) reg [LR-1:0] rd;
        always @(posedge clk) rd <= {rd, rst_n};
        wire [817:0] rl1_r; wire [2068:0] bk1_r; wire [12:0] ohl_r; wire [25:0] st_r; wire [4:0] at_r;
        ot_rp4a_relay #(.W(818), .N((MUT == 6) ? LR - 1 : LR)) u_rl (.clk(clk), .rst_n(1'b1), .d(rl1), .q(rl1_r));
        ot_rp4a_relay #(.W(2069), .N(LR)) u_bk (.clk(clk), .rst_n(1'b1), .d(bk1), .q(bk1_r));
        ot_rp4a_relay #(.W(13), .N(LR)) u_oh (.clk(clk), .rst_n(1'b1), .d(bk1[2060:2048]), .q(ohl_r));
        ot_rp4a_relay #(.W(26), .N(LR)) u_st (.clk(clk), .rst_n(1'b1), .d(st), .q(st_r));
        ot_rp4a_relay #(.W(5), .N(LR)) u_at (.clk(clk), .rst_n(1'b1), .d(at), .q(at_r));
        ot_rp4a_leaf_core #(.OS(OS)) u_c (.clk(clk), .rst_n(rd[LR-1]), .st(st_r), .at(at_r), .rl1(rl1_r), .bk1(bk1_r), .ohl(ohl_r), .g(g));
    end endgenerate
endmodule

// OS (HBM-SMATT10, native census of the r1 gate: input_pv 257 loads, attn_column 130/65/49, r_x 253, bdc ov 98,
// merge pub_v 89): OS = 1 adds two uniform stages inside the core, g +2: (XO) every x-store output registered, the PV
// select input_pv rebuilt per 32-bit fx slice from 8 KEPT copies of its three inputs and the PV broadcast word from 16
// KEPT one-hot attn_column copies; (GO) the bdc / tct / merge outputs registered before the g select with 3 KEPT copies
// of each valid; the publication delay line reset from 16 KEPT copies.  OS = 0 = the original core (bench reference).
module ot_rp4a_leaf_core #(parameter integer OS = 0) (input wire clk, input wire rst_n, input wire [25:0] st, input wire [4:0] at,
    input wire [817:0] rl1, input wire [2068:0] bk1, input wire [12:0] ohl, output wire [49:0] g);
    localparam integer LBS = 2, LSB = 16, IL = 8, TAGW = 16, NBEAT = 13;
    wire [2:0] attn_column = at[2:0];
    wire [1:0] attn_row = at[4:3];
    (* keep *) reg [4:0] rq;
    always @(posedge clk) rq <= {5{rst_n}};
    wire r_xs = rq[0], r_bdc = rq[1], r_tcc = rq[2], r_g = rq[3], r_x = rq[4];
    (* keep *) reg [15:0] rpp;
    always @(posedge clk) rpp <= {16{rst_n}};
    wire x_iv_b, x_iv_f, x_ifirst, x_ilast, x_ifp4, x_ifirst_e, x_ilast_e;
    wire [TAGW-1:0] x_itag, x_itag_e;
    wire [LBS*266+LSB*16-1:0] x_iw, x_ix;
    wire iv_b, iv_f, ifirst, ilast, ifp4, ifirst_e, ilast_e;
    wire [TAGW-1:0] itag, itag_e;
    wire [LBS*266+LSB*16-1:0] iw, ix;
    wire [255:0] pvx;          // fx when input_pv (the broadcast x word)
    wire [7:0] ipv;            // input_pv per 32-bit fx slice
    generate if (OS != 0) begin : g_xo
        reg q_iv_b, q_iv_f, q_ifirst, q_ilast, q_ifp4, q_ifirst_e, q_ilast_e;
        reg [TAGW-1:0] q_itag, q_itag_e;
        reg [LBS*266+LSB*16-1:0] q_iw, q_ix;
        (* keep *) reg [7:0] k_ivf, k_fp4, k_w129;
        reg [7:0] oh;
        (* keep *) reg [7:0] k_oh [0:15];
        integer i;
        always @(posedge clk) begin
            q_iv_b <= x_iv_b; q_iv_f <= x_iv_f; q_ifirst <= x_ifirst; q_ilast <= x_ilast; q_ifp4 <= x_ifp4;
            q_ifirst_e <= x_ifirst_e; q_ilast_e <= x_ilast_e; q_itag <= x_itag; q_itag_e <= x_itag_e; q_iw <= x_iw; q_ix <= x_ix;
            k_ivf <= {8{x_iv_f}}; k_fp4 <= {8{x_ifp4}}; k_w129 <= {8{x_iw[129]}};
            for (i = 0; i < 8; i = i + 1) oh[i] <= (attn_column == i[2:0]);
            for (i = 0; i < 16; i = i + 1) k_oh[i] <= oh;
        end
        assign {iv_b, iv_f, ifirst, ilast, ifp4, ifirst_e, ilast_e} = {q_iv_b, q_iv_f, q_ifirst, q_ilast, q_ifp4, q_ifirst_e, q_ilast_e};
        assign itag = q_itag; assign itag_e = q_itag_e; assign iw = q_iw; assign ix = q_ix;
        genvar s, b, c;
        for (s = 0; s < 8; s = s + 1) begin : g_ipv
            assign ipv[s] = k_ivf[s] && k_fp4[s] && k_w129[s];
        end
        for (s = 0; s < 16; s = s + 1) begin : g_bw
            for (b = 0; b < 16; b = b + 1) begin : g_b
                wire [7:0] t;
                for (c = 0; c < 8; c = c + 1) begin : g_c
                    assign t[c] = k_oh[s][c] & q_iw[16*c + b];
                end
                assign pvx[16*s + b] = |t;
            end
        end
    end else begin : g_noxo
        assign {iv_b, iv_f, ifirst, ilast, ifp4, ifirst_e, ilast_e} = {x_iv_b, x_iv_f, x_ifirst, x_ilast, x_ifp4, x_ifirst_e, x_ilast_e};
        assign itag = x_itag; assign itag_e = x_itag_e; assign iw = x_iw; assign ix = x_ix;
        assign pvx = {16{x_iw[16*attn_column +: 16]}};
        assign ipv = {8{x_iv_f && x_ifp4 && x_iw[129]}};
    end endgenerate
    ot_hbm_accel_smh_xs
`ifndef OT_RP4A_HARD
        #(.TAGW(TAGW), .NBEAT(NBEAT))
`endif
        u_xs (.clk(clk), .rst_a(r_xs), .xs_a1(st[8:0]), .xs_g1(st[13:9]),
        .xs_a2(st[20:14]), .xs_g2(st[25:21]), .rl1(rl1), .bk1(bk1), .ohl1(ohl), .o_iv_b(x_iv_b), .o_iv_f(x_iv_f),
        .o_ifirst(x_ifirst), .o_ilast(x_ilast), .o_ifp4(x_ifp4), .o_itag(x_itag), .o_iw(x_iw), .o_ix(x_ix), .o_ifirst_e(x_ifirst_e),
        .o_ilast_e(x_ilast_e), .o_itag_e(x_itag_e));
    wire marker = iv_f && ifp4;
    wire input_pv = marker && iw[129];
    wire input_arithmetic = iv_f && (!marker || iw[137]);
    reg bv, bfirst, blast, bfp4, fv, ffirst, fqlast, fplast, frfirst, frlast;
    reg [TAGW-1:0] btag, ftag;
    reg [LBS*266-1:0] bw, bx;
    reg [255:0] fw, fx;
    reg [4:0] publish0;
    reg fold0; reg [2:0] fold0_a, fold0_b;
    integer fs;
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
        for (fs = 0; fs < 8; fs = fs + 1) fx[32*fs +: 32] <= ipv[fs] ? pvx[32*fs +: 32] : ix[LBS*266 + 32*fs +: 32];
    end
    wire bov, bfault, fov, qf, mf, ps_v;
    wire [31:0] by, fy, ps_data;
    wire [TAGW-1:0] bt, ft, ps_tag;
    wire [3:0] ps_word;
    wire [2:0] ps_slot;
    ot_hbm_accel_smh_bdc
`ifndef OT_RP4A_HARD
        #(.LBS(LBS), .IL(IL), .TAGW(TAGW))
`endif
        u_bdc (.clk(clk), .rst_a(r_bdc), .i_v(bv), .i_first(bfirst),
        .i_last(blast), .i_fp4(bfp4), .i_tag(btag), .i_w(bw), .i_x(bx), .ov(bov), .y(by), .otag(bt), .fault(bfault));
    // publication delay line: static tap {attn_row, 4'b0} (0 / 16 / 32 / 48)
    reg [4:0] pub_pipe [0:48];
    integer d;
    always @(posedge clk)
        for (d = 0; d < 49; d = d + 1)
            if (!((OS != 0) ? rpp[d % 16] : r_x)) pub_pipe[d] <= 0;
            else pub_pipe[d] <= (d == 0) ? publish0 : pub_pipe[(d == 0) ? 0 : d - 1];
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
    ot_hbm_accel_smh_tct
`ifndef OT_RP4A_HARD
        #(.TAGW(TAGW))
`endif
        u_qk (.clk(clk), .rst_a(r_tcc), .i_v(fv), .i_last(fqlast), .i_tag(ftag),
        .sum_i({s1, s0}), .lf_a(lf0), .lf_b(lf1), .ov(fov), .y(fy), .otag(ft), .fault(qf));
    wire event_v;
    wire [511:0] event_sum;
    wire [TAGW-1:0] event_tag;
    ot_rp4a_cap #(.TAGW(TAGW)) u_cap (.clk(clk), .rst_n(r_tcc), .i_v(fv), .i_last(fplast), .i_run_first(frfirst),
        .i_run_last(frlast), .i_tag(ftag), .sum_i({s1, s0}), .event_v(event_v), .event_sum(event_sum), .event_tag(event_tag));
    wire pv_v;
    wire [511:0] pv_y;
    wire [TAGW-1:0] pv_tag;
    // hard view = the closed config (TAGW 16, LV 4, PUBLISH 1, TURNREG 1, SAFE 2): no overrides under OT_RP4A_HARD
    ot_hbm_sm_pv_merge_s3
`ifndef OT_RP4A_HARD
        #(.TAGW(TAGW), .LV(4), .PUBLISH(1), .TURNREG(1), .SAFE(2))
`endif
        u_merge (.clk(clk), .rst_n(r_tcc),
        .ev(event_v), .sum(event_sum), .tag_d(event_tag), .pv_v(pv_v), .pv_y(pv_y), .pv_tag(pv_tag), .fault(mf),
        .pub_start(pc[3]), .pub_slot(selected_slot), .pub_v(ps_v), .pub_data(ps_data), .pub_word(ps_word),
        .pub_out_slot(ps_slot), .pub_tag(ps_tag), .fold_start(fold0), .fold_a(fold0_a), .fold_b(fold0_b));
    wire ffault = qf | mf;
    wire [11:0] scalar_row = published_h128 ? {4'd0, ps_slot[1:0], attn_row, ps_word} : {6'd0, attn_row, ps_word};
    reg gv_q, gf_q;
    reg [31:0] gy_q;
    reg [TAGW-1:0] gt_q;
    wire [2:0] kb, kf, kp;
    wire [31:0] gby, gfy, gpd;
    wire [TAGW-1:0] gbt, gft;
    wire [11:0] gsr;
    wire gbf, gff;
    generate if (OS != 0) begin : g_go
        (* keep *) reg [2:0] k_b, k_f, k_p;
        reg [31:0] q_by, q_fy, q_pd;
        reg [TAGW-1:0] q_bt, q_ft;
        reg [11:0] q_sr;
        reg q_bf, q_ff;
        always @(posedge clk) begin
            k_b <= {3{bov}}; k_f <= {3{fov}}; k_p <= {3{ps_v}};
            q_by <= by; q_fy <= fy; q_pd <= ps_data; q_bt <= bt; q_ft <= ft; q_sr <= scalar_row; q_bf <= bfault; q_ff <= ffault;
        end
        assign kb = k_b; assign kf = k_f; assign kp = k_p; assign gby = q_by; assign gfy = q_fy; assign gpd = q_pd;
        assign gbt = q_bt; assign gft = q_ft; assign gsr = q_sr; assign gbf = q_bf; assign gff = q_ff;
    end else begin : g_nogo
        assign kb = {3{bov}}; assign kf = {3{fov}}; assign kp = {3{ps_v}}; assign gby = by; assign gfy = fy; assign gpd = ps_data;
        assign gbt = bt; assign gft = ft; assign gsr = scalar_row; assign gbf = bfault; assign gff = ffault;
    end endgenerate
    always @(posedge clk)
        if (!r_g) begin gv_q <= 0; gf_q <= 0; end
        else begin gv_q <= kb[0] | kf[0] | kp[0]; gf_q <= gbf | gff | (kb[0] && kf[0]) | (kp[0] && (kb[0] || kf[0])); end
    always @(posedge clk) begin
        gy_q <= kp[1] ? gpd : kb[1] ? gby : gfy;
        gt_q <= kp[2] ? {gsr, 1'b1, 3'd0} : kb[2] ? gbt : gft;
    end
    assign g = {gv_q, gf_q, gy_q, gt_q};
endmodule

// n half: ot_hbm_smh_rp4h_n with the attention leaf; attn = {attn_rowbase[1:0], attn_column[2:0]} (static strap)
module ot_hbm_smh_rp4ah_n #(parameter integer MUT = 0, parameter integer SOFTBEAT = 1, parameter integer GN = 2, parameter integer XB = 1, parameter integer LR = 0, parameter integer OS = 0) (
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
    ot_rp4a_leaf #(.LR(LR), .MUT(MUT), .OS(OS)) u_lf0 (.clk(clk), .rst_n(r[7]), .st(st_n), .at(at_n), .rl1(rl1_n), .bk1(bk1_n), .g(g0));
    wire [99:0] gin_r;
    ot_rp4a_relay #(.W(100), .N(LR + 2 * OS), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_gip (.clk(clk), .rst_n(r[8]), .d(gin), .q(gin_r));
    ot_rp4l_gn u_gn (.clk(clk), .rst_n(r[8]), .g0(g0), .gin(gin_r), .g0m(g0m), .gpm(gpm));
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_xb1 (.clk(clk), .rst_n(r[9]), .d(bin_l), .q(xb1));
    generate if (MUT == 1) begin : g_m1
        assign xb2 = xb1;
    end else begin : g_xb2
        ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_xb2 (.clk(clk), .rst_n(r[9]), .d(xb1), .q(xb2));
    end endgenerate
    wire [2068:0] xb3;
    generate if (XB != 0) begin : g_xb3
        ot_rp4a_relay #(.W(2069), .N(XB), .VMASK({1'b1, 2068'b0})) u_xb3 (.clk(clk), .rst_n(r[9]), .d(xb2), .q(xb3));
    end else begin : g_noxb3
        assign xb3 = xb2;
    end endgenerate
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_xbo (.clk(clk), .rst_n(r[9]), .d(xb3), .q(xo_b));
    wire [49:0] g0r;
    wire [99:0] gpr;
    generate if (GN != 0) begin : g_grel
        ot_rp4a_relay #(.W(50), .N(GN), .VMASK({2'b11, 48'b0})) u_xgr (.clk(clk), .rst_n(r[10]), .d(g0m), .q(g0r));
        ot_rp4a_relay #(.W(100), .N(GN), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_xpr (.clk(clk), .rst_n(r[10]), .d(gpm), .q(gpr));
    end else begin : g_nogrel
        assign g0r = g0m; assign gpr = gpm;
    end endgenerate
    ot_rp4h_xreg #(.W(50), .VMASK({2'b11, 48'b0})) u_xgo (.clk(clk), .rst_n(r[10]), .d(g0r), .q(xo_g0));
    ot_rp4h_xreg #(.W(100), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_xpo (.clk(clk), .rst_n(r[10]), .d(gpr), .q(xo_gp));
endmodule

// s half: ot_hbm_smh_rp4h_s with the attention leaf (leaf 1 = attn_rowbase + 1)
module ot_hbm_smh_rp4ah_s #(parameter integer MUT = 0, parameter integer GN = 2, parameter integer GS = 1, parameter integer XB = 1, parameter integer LR = 0, parameter integer OS = 0) (
    input wire clk, input wire rst_n,
    input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2, input wire [4:0] attn,
    input wire [817:0] rin_s, output wire [817:0] rout_s,
    input wire [2068:0] xi_b, input wire [49:0] xi_g0, input wire [99:0] xi_gp,
    output wire [199:0] gout
);
    wire [7:0] r;
    ot_rp4h_rst #(.NC(8)) u_rst (.clk(clk), .rst_n(rst_n), .r(r));
    wire r_land, r_lf1, r_gs;
    ot_rp4h_rpad #(.N(3 + XB)) u_rp_land (.clk(clk), .d(r[3]), .q(r_land));
    ot_rp4h_rpad #(.N(3 + XB)) u_rp_lf1 (.clk(clk), .d(r[4]), .q(r_lf1));
    ot_rp4h_rpad #(.N(3 + XB)) u_rp_gs (.clk(clk), .d(r[5]), .q(r_gs));
    wire [25:0] st_s, st_s_p;
    wire [4:0] at_s;
    wire [817:0] rl_s, rl1_s, rl1_s_p, rpm_s;
    wire [2068:0] bk1_s;
    wire [49:0] g1, xg, g0m;
    wire [99:0] xp, gpm;
`ifndef SYNTHESIS
    initial if (GN + GS < XB) $fatal(1, "ot_hbm_smh_rp4ah_s: GN + GS must be >= XB (leaf-1 lane pads)");
`endif
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_lands (.clk(clk), .rst_n(r_land), .d(xi_b), .q(bk1_s));
    ot_rp4h_xreg #(.W(50), .VMASK({2'b11, 48'b0})) u_xgi (.clk(clk), .rst_n(r[6]), .d(xi_g0), .q(xg));
    wire [49:0] xg2o;
    ot_rp4h_xreg #(.W(50), .VMASK({2'b11, 48'b0})) u_xg2 (.clk(clk), .rst_n(r[6]), .d(xg), .q(xg2o));
    ot_rp4h_xreg #(.W(100), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_xpi (.clk(clk), .rst_n(r[7]), .d(xi_gp), .q(xp));
    wire [99:0] xp2;
    ot_rp4h_xreg #(.W(100), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_xp2 (.clk(clk), .rst_n(r[7]), .d(xp), .q(xp2));
    wire [99:0] gpm0 = (MUT == 2) ? xp : xp2;
    wire [49:0] g1p;
    generate if (GS != 0) begin : g_grel
        ot_rp4a_relay #(.W(50), .N(GS), .VMASK({2'b11, 48'b0})) u_xg3 (.clk(clk), .rst_n(r[6]), .d(xg2o), .q(g0m));
        ot_rp4a_relay #(.W(100), .N(GS), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_xp3 (.clk(clk), .rst_n(r[7]), .d(gpm0), .q(gpm));
    end else begin : g_nogrel
        assign g0m = xg2o; assign gpm = gpm0;
    end endgenerate
    generate if (GN + GS - XB > 0) begin : g_g1pad
        ot_rp4a_relay #(.W(50), .N(GN + GS - XB), .VMASK({2'b11, 48'b0})) u_g1p (.clk(clk), .rst_n(r_gs), .d(g1), .q(g1p));
    end else begin : g_nog1pad
        assign g1p = g1;
    end endgenerate
    ot_rp4l_strap u_sr_s (.clk(clk), .d({xss_g2, xss_a2, xss_g1, xss_a1}), .q(st_s));
    ot_rp4a_astrap u_as_s (.clk(clk), .d({attn[4:3] + 2'd1, attn[2:0]}), .q(at_s));
    ot_rp4l_pinrow u_pr_s (.clk(clk), .rst_n(r[0]), .d(rin_s), .q(rl_s));
    ot_smh_tr_group_row_w u_row1 (.clk(clk), .rst_a(r[1]), .d(rl_s), .first(rl1_s), .last(rpm_s));
    ot_smh_tr_group_row_e u_rowe1 (.clk(clk), .rst_a(r[2]), .d(rpm_s), .last(rout_s));
    ot_pl_pad #(.W(818), .N(((MUT == 3) ? 2 : 3) + XB)) u_pp_rl1 (.ck(clk), .d(rl1_s), .q(rl1_s_p));
    ot_pl_pad #(.W(26), .N(3 + XB)) u_pp_st (.ck(clk), .d(st_s), .q(st_s_p));
    ot_rp4a_leaf #(.LR(LR), .MUT(MUT), .OS(OS)) u_lf1 (.clk(clk), .rst_n(r_lf1), .st(st_s_p), .at(at_s), .rl1(rl1_s_p), .bk1(bk1_s), .g(g1));
    ot_rp4l_gs u_gs (.clk(clk), .rst_n(r_gs), .g1in(g1p), .g0m(g0m), .gpm(gpm), .gout(gout));
endmodule

// the SM frame slot: both halves abutted (die binder form; also the bench DUT)
module ot_hbm_smh_rp4ah2 #(parameter integer MUT = 0, parameter integer SOFTBEAT = 1, parameter integer GN = 2, parameter integer GS = 1, parameter integer XB = 1, parameter integer LR = 0, parameter integer OS = 0) (
    input wire rst_n, input wire [4:0] attn,
    input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
    input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
    input wire [817:0] rin_n, input wire [817:0] rin_s, input wire [2068:0] bin,
    output wire [817:0] rout_n, output wire [817:0] rout_s, output wire [2068:0] bout,
    input wire [99:0] gin, output wire [199:0] gout,
    input wire ck_n, input wire ck_s
);
    wire [2068:0] x_b; wire [49:0] x_g0; wire [99:0] x_gp;
    ot_hbm_smh_rp4ah_n #(.MUT(MUT), .SOFTBEAT(SOFTBEAT), .GN(GN), .XB(XB), .LR(LR), .OS(OS)) u_n (.clk(ck_n), .rst_n(rst_n), .xs_a1(xs_a1), .xs_g1(xs_g1),
        .xs_a2(xs_a2), .xs_g2(xs_g2), .attn(attn), .rin_n(rin_n), .bin(bin), .gin(gin), .rout_n(rout_n), .bout(bout),
        .xo_b(x_b), .xo_g0(x_g0), .xo_gp(x_gp));
    ot_hbm_smh_rp4ah_s #(.MUT(MUT), .GN(GN), .GS(GS), .XB(XB), .LR(LR), .OS(OS)) u_s (.clk(ck_s), .rst_n(rst_n), .xss_a1(xss_a1), .xss_g1(xss_g1), .xss_a2(xss_a2),
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
