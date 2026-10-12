`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// dsfd_sp_su_h (s81-suhc-hier-1011, 2026-10-11): the S81 SU slab master rebuilt as a hierarchical slab.  Same pins
// and adapter as dsfd_sp_su (contract su_hc v2: c_cmd / c_done / inp / VM rd S_RD rows / VM wr S_WR rows / flt /
// online / fcode); inside, one control tile and NT hardened engine tiles on two registered chains:
//
//   pins -> NPO pin owners ot_s81_su_pin (stacked along the VM pin edge, each its slots' pin flops / registers) and the
//           control tile ot_s81_su_ctl (adapter, ot_s81_su_hctl job control / VM read issue / completion)
//       down spine (VM response rows + job announce, S_RD x 512 b): relay stations at the stops QN, KV, QB 0..NQB-1,
//         SW 0..NSW-1, SM 0..NSM-1 (one register a stop); each tile taps its stop
//       up spine (S_WR write row slots): a relay station a stop merges that tile's registered slots into its window
//   regional reset: pin -> relay -> ctl; a reset spine station a stop -> the tile's own two-flop relay
// Tiles carry one copy of each bus (no pass-through): pins = the down tap + its own write slots + status.
//
// Tile decomposition (production params): QN norm x 2 (128 lanes, D 1,280, its q gain set slice), KV norm x 2 (256
// lanes, the RoPE tail in the second, its kv gain set slice), QB x 4 (8 blocks each), SW x 8 (128 lanes each), SM x 8
// (2 heads x 16 lanes each); a norm's group sums of squares meet in its head tile over a registered rung (the golden's
// top tree level, left + right), the rstd returns the same way.
// The values are those of dsfd_sp_su (bit-exact gate tools/s81_suhc/su_gate.py --hier); added latency: the chain
// hops (a cycle a tile each way) and the norm tiles' ready round trip.
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_sp_su_h #(
    parameter integer QN_N = 256, KV_N = 512, QB_NB = 32, SW_W = 1024, SM_H = 16, SM_LPH = 16, SM_NVMAX = 40,
    parameter integer S_RD = 16, S_WR = 16, LM = 5, LA = 4, OQ = 1024, MUT = 0, AMUT = 0,
    // lane-group tiles (production: QN 2 x 128 lanes, KV 2 x 256 lanes, QB 4 x 8 blocks, SW 8 x 128 lanes, SM 8 x 2
    // heads; pin owners 4 x (4 read + 4 write slots); every tile <= ~600 x 600 um)
    // QN (el1011-s81su-qn, spec v3): a tap (2 data halves) + NQE = QN_N / 8 norm engines + a reduce + NQQ = QN_N / 32
    // act-quant engines; spine stops: the tap, then the quant engines (the norm engines and the reduce hang off the tap)
    parameter integer NQE = QN_N / 8,
    parameter integer NQQ = QN_N / 32,
    parameter integer NKV = (KV_N >= 128) ? 2 : 1,
    // QB (el1011-s81su, spec v3): one tap + NPB engines (rate-matched to the down spine: NPB = S_RD / 2 blocks a pass)
    parameter integer NPB = (S_RD / 2 > 2) ? S_RD / 2 : 2,
    parameter integer ERL = (S_RD >= 16) ? 3 : 1,      // tap -> engine relays, equal depth on every engine (lockstep)
    parameter integer NSW = (SW_W >= 128) ? SW_W / 128 : 1,
    parameter integer NSM = (SM_H >= 2) ? SM_H / 2 : 1,
    parameter integer NPO = (S_RD >= 16 && S_WR >= 16) ? 4 : 1,
    // relay stations on every pin owner link (spine slices and control seams), the same depth on every link so the
    // slots of a cycle stay aligned: the pin owners stack ~1.9 mm along the VM pin edge (<= 500 um a station)
    parameter integer NRL = (S_RD >= 16) ? 4 : 1,
    // relay stations a spine stop / norm rung hop (adjacent tiles' centres ~620 um apart: 2 for <= 500 um a station)
    // and on the controller pulse nets c_cmd / c_done between the slab's N-face pins and the control tile (cck domain;
    // ~2.25 mm in the su_s composition: 5 stations for <= 500 um)
    parameter integer SRD = (S_RD >= 16) ? 2 : 1,
    // SM stop (spec v3): relay stations on every link between its masters (a stop ~1.3 x 1.0 mm: 2 for <= 500 um)
    parameter integer SRL = (S_RD >= 16) ? 2 : 1,
    parameter integer NRC = (S_RD >= 16) ? 5 : 1
) (
    input  wire                cck, crs,
    input  wire                sk, srs,
    input  wire                c_cmd_v,
    input  wire [83:0]         c_cmd_d,
    output wire                c_done_v,
    output wire [7:0]          c_done_tag,
    input  wire                inp,
    output wire [S_RD-1:0]     rq_v,
    output wire [S_RD*14-1:0]  rq_row,
    input  wire [S_RD-1:0]     rs_v,
    input  wire [S_RD*512-1:0] rs_d,
    output wire [S_WR-1:0]     wq_v,
    output wire [S_WR*14-1:0]  wq_row,
    output wire [S_WR*16-1:0]  wq_mask,
    output wire [S_WR*512-1:0] wq_d,
    output wire                flt,
    output wire                online,
    output wire [3:0]          fcode
);
    localparam integer NQB = 1 + NPB;                  // QB stops: the tap, then the engines
    localparam integer NQN = 1 + NQQ;                  // QN stops: the tap, then the quant engines
    localparam integer NTL = NQN + NKV + NQB + NSW + NSM;
    localparam integer QL = QN_N / 16;                 // QN tap positions (rows a vector)
    localparam integer DQ_ = 1280;                     // q width (the golden's DQ)
    // QB tap -> engines (positions 2b / 2b + 1 to engine b) and the engines' pair exchange
    wire [2*NPB-1:0]     qe_v;
    wire [2*NPB*512-1:0] qe_d;
    wire [2*NPB*12-1:0]  qe_t;
    wire [13:0]          qe_ob;
    wire                 qe_f4;
    wire                 nxv [0:NPB-1];
    wire [255:0]         nxq [0:NPB-1];
    wire [9:0]           nxe [0:NPB-1];
    localparam integer KR = S_RD / NPO, KW = S_WR / NPO;
    // spines: stop t = tile t.  Down: dn[t] is the relay register at stop t (dn[0]: the pin owners' row registers +
    // the control tile's job announce); the tile taps it and the next stop re-registers it.  Up: up[t] is the relay
    // register at stop t, = up[t + 1] with tile t's registered write slots merged into its window; up[0]: the wide
    // part to the pin owners (each its slice), the status to the control tile.
    wire                  dst [0:NTL];
    wire [3:0]            dkd [0:NTL];
    wire [1:0]            dgs [0:NTL];
    wire                  df4 [0:NTL];
    wire [7:0]            dji [0:NTL];
    wire [S_RD-1:0]       dv  [0:NTL];
    wire [S_RD*512-1:0]   dd  [0:NTL];
    wire [S_WR-1:0]       uv  [0:NTL];
    wire [S_WR*14-1:0]    ua  [0:NTL];
    wire [S_WR*16-1:0]    um  [0:NTL];
    wire [S_WR*512-1:0]   ud  [0:NTL];
    wire                  ufu [0:NTL], ufo [0:NTL], ual [0:NTL], ude [0:NTL], urd [0:NTL];
    wire [7:0]            urj [0:NTL];
    wire                  rst [0:NTL];
    assign uv[NTL] = 0; assign ua[NTL] = 0; assign um[NTL] = 0; assign ud[NTL] = 0;
    assign ufu[NTL] = 1'b0; assign ufo[NTL] = 1'b0; assign ual[NTL] = 1'b1; assign ude[NTL] = 1'b1;
    assign urd[NTL] = 1'b0; assign urj[NTL] = 8'd0;

    // ------------------------------------------------------------------ controller pulse nets: NRC relay stations (cck)
    wire        cc_v, cd_v;
    wire [83:0] cc_d;
    wire [7:0]  cd_t;
    ot_hdc_delay #(.W(2), .D(NRC), .RESET(1)) u_rcv (.clk(cck), .rst_n(crs), .d({c_cmd_v, cd_v}), .q({cc_v, c_done_v}));
    ot_hdc_delay #(.W(92), .D(NRC)) u_rcd (.clk(cck), .rst_n(crs), .d({c_cmd_d, cd_t}), .q({cc_d, c_done_tag}));

    // ------------------------------------------------------------------ control tile
    wire [S_RD-1:0]    c_rq_v;
    wire [S_RD*14-1:0] c_rq_row;
    wire [S_RD-1:0]    p_rv;
    wire [S_RD*30-1:0] p_rf;
    wire [S_WR-1:0]    p_uv;
    wire               rst_c;
    ot_s81_su_ctl #(.QN_N(QN_N), .KV_N(KV_N), .QB_NB(QB_NB), .SW_W(SW_W), .SM_H(SM_H), .SM_LPH(SM_LPH),
                    .S_RD(S_RD), .S_WR(S_WR), .NSW(NSW), .NQB(QB_NB / 2), .NQN(QN_N / 64), .NKV(NKV), .MUT(MUT), .AMUT(AMUT)) u_ctl (
        .cck(cck), .crs(crs), .sk(sk), .srs(srs), .c_cmd_v(cc_v), .c_cmd_d(cc_d), .c_done_v(cd_v),
        .c_done_tag(cd_t), .inp(inp), .flt(flt), .online(online), .fcode(fcode), .rst_o(rst_c),
        .p_rq_v(c_rq_v), .p_rq_row(c_rq_row), .p_rv(p_rv), .p_rf(p_rf), .p_uv(p_uv),
        .dn_st(dst[0]), .dn_kind(dkd[0]), .dn_gsel(dgs[0]), .dn_fp4(df4[0]), .dn_jid(dji[0]),
        .up_fu(ufu[0]), .up_fo(ufo[0]), .up_alive(ual[0]), .up_den(ude[0]), .up_rdy(urd[0]), .up_rjid(urj[0]));
    // reset spine head
    reg rs0;
    always @(posedge sk or negedge rst_c) if (!rst_c) rs0 <= 1'b0; else rs0 <= 1'b1;
    assign rst[0] = rs0;

    // ------------------------------------------------------------------ pin owners (+ NRL relay stations every link)
    genvar o;
    generate for (o = 0; o < NPO; o = o + 1) begin : g_po
        wire [KR-1:0]    rv, dnv;  wire [KR*30-1:0] rf;   wire [KW-1:0] uvo;
        wire [KR*512-1:0] dnd;
        wire [KR-1:0]    rq_v_r;  wire [KR*14-1:0] rq_row_r;
        wire [KW-1:0]    upv;     wire [KW*14-1:0] upa;   wire [KW*16-1:0] upm;  wire [KW*512-1:0] upd;
        // control-signal relays (reset), data relays (no reset)
        ot_hdc_delay #(.W(KR + KR + KW + KR + KW), .D(NRL), .RESET(1)) u_rlc (.clk(sk), .rst_n(rs0),
            .d({c_rq_v[KR * o +: KR], rv, uvo, dnv, uv[0][KW * o +: KW]}),
            .q({rq_v_r, p_rv[KR * o +: KR], p_uv[KW * o +: KW], dv[0][KR * o +: KR], upv}));
        ot_hdc_delay #(.W(KR * 14 + KR * 30 + KR * 512 + KW * (14 + 16 + 512)), .D(NRL)) u_rld (.clk(sk), .rst_n(rs0),
            .d({c_rq_row[KR * 14 * o +: KR * 14], rf, dnd, ua[0][KW * 14 * o +: KW * 14], um[0][KW * 16 * o +: KW * 16],
                ud[0][KW * 512 * o +: KW * 512]}),
            .q({rq_row_r, p_rf[KR * 30 * o +: KR * 30], dd[0][KR * 512 * o +: KR * 512], upa, upm, upd}));
        ot_s81_su_pin #(.KR(KR), .KW(KW)) u_po (
            .clk(sk), .rst_in(rs0),
            .rq_v(rq_v[KR * o +: KR]), .rq_row(rq_row[KR * 14 * o +: KR * 14]), .rs_v(rs_v[KR * o +: KR]),
            .rs_d(rs_d[KR * 512 * o +: KR * 512]), .wq_v(wq_v[KW * o +: KW]), .wq_row(wq_row[KW * 14 * o +: KW * 14]),
            .wq_mask(wq_mask[KW * 16 * o +: KW * 16]), .wq_d(wq_d[KW * 512 * o +: KW * 512]),
            .dn_v(dnv), .dn_d(dnd), .up_v(upv), .up_a(upa), .up_m(upm), .up_d(upd),
            .c_rq_v(rq_v_r), .c_rq_row(rq_row_r), .c_rv(rv), .c_rf(rf), .c_uv(uvo));
    end endgenerate

    // ------------------------------------------------------------------ QN: norm engines + reduce (off the spine)
    wire [QL-1:0]       qt_v [0:1];
    wire [QL*256-1:0]   qt_d [0:1];
    wire [QL*8-1:0]     qt_t [0:1];
    wire                qt_gq, qt_go;
    wire [1:0]          qt_gr, qt_gw;
    wire [13:0]         qt_ob;
    wire [31:0]         qt_eps;
    wire [NQE:0]        qn_f;                          // engine faults + the reduce's (relayed into the tap)
    wire [NQE-1:0]      qy_v;
    wire [NQE*8-1:0]    qy_i;
    wire [NQE*256-1:0]  qy_d;
    wire [NQE-1:0]      qp_v, qp_p;
    wire [NQE*32-1:0]   qp_d;
    wire                qr_v;
    wire [31:0]         qr_d;
    wire                qnxv [0:NQQ-1];
    wire [255:0]        qnxq [0:NQQ-1];
    wire [9:0]          qnxe [0:NQQ-1];
    genvar qe;
    generate for (qe = 0; qe < NQE; qe = qe + 1) begin : g_qne
        // engine qe = position qe / 2, data half qe % 2; equal-depth relays tap -> engine, engine -> reduce, rstd back
        wire iv, igq, ef, pv, pvr; wire [255:0] ix; wire [7:0] it, pi; wire [1:0] igr, igw; wire [31:0] pd, pdr;
        wire rv; wire [31:0] rd;
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_iv (.clk(sk), .rst_n(rst[0]), .d(qt_v[qe % 2][qe / 2]), .q(iv));
        ot_hdc_delay #(.W(256 + 8 + 5), .D(ERL)) u_id (.clk(sk), .rst_n(rst[0]),
            .d({qt_d[qe % 2][256 * (qe / 2) +: 256], qt_t[qe % 2][8 * (qe / 2) +: 8], qt_gq, qt_gr, qt_gw}),
            .q({ix, it, igq, igr, igw}));
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_rv (.clk(sk), .rst_n(rst[0]), .d(qr_v), .q(rv));
        ot_hdc_delay #(.W(32), .D(ERL)) u_rd (.clk(sk), .rst_n(rst[0]), .d(qr_d), .q(rd));
        ot_s81_su_qne #(.NV(DQ_ / QN_N), .LM(LM), .LA(LA)) u_qne (
            .clk(sk), .rst_in(rst[0]), .i_v(iv), .i_x(ix), .i_t(it), .i_gq(igq), .i_gr(igr), .i_gw(igw), .r_v(rv), .r_d(rd),
            .p_v(pv), .p_i(pi), .p_d(pd), .y_v(qy_v[qe]), .y_i(qy_i[8 * qe +: 8]), .y(qy_d[256 * qe +: 256]), .o_f(ef));
        ot_hdc_delay #(.W(2), .D(ERL), .RESET(1)) u_pv (.clk(sk), .rst_n(rst[0]), .d({pv, ef}), .q({qp_v[qe], qn_f[qe]}));
        ot_hdc_delay #(.W(33), .D(ERL)) u_pd (.clk(sk), .rst_n(rst[0]), .d({pi[0], pd}), .q({qp_p[qe], qp_d[32 * qe +: 32]}));
    end endgenerate
    generate if (1) begin : g_qnr
        wire go, rf; wire [31:0] eps;
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_gv (.clk(sk), .rst_n(rst[0]), .d(qt_go), .q(go));
        ot_hdc_delay #(.W(32), .D(ERL)) u_gd (.clk(sk), .rst_n(rst[0]), .d(qt_eps), .q(eps));
        // two half trees (engines 0..NQE/2-1, NQE/2..NQE-1) -> the reduce (NE 2: the golden tree's top add, vector
        // levels, / D, + eps, rsqrt); each half is its own hardened tile (<= 15k sinks)
        wire [1:0] hv, hp, hf; wire [63:0] hd;
        genvar hh;
        for (hh = 0; hh < 2; hh = hh + 1) begin : g_qnh
            ot_s81_su_qnh #(.NE(NQE / 2), .LA(LA)) u_qnh (
                .clk(sk), .rst_in(rst[0]), .i_go(go), .p_v(qp_v[hh * (NQE / 2) +: NQE / 2]),
                .p_p(qp_p[hh * (NQE / 2) +: NQE / 2]), .p_d(qp_d[hh * 16 * NQE +: 16 * NQE]), .s_v(hv[hh]), .s_p(hp[hh]),
                .s_d(hd[32 * hh +: 32]), .o_f(hf[hh]));
        end
        ot_s81_su_qnr #(.NE(2), .NV(DQ_ / QN_N), .D(DQ_), .LM(LM), .LA(LA)) u_qnr (
            .clk(sk), .rst_in(rst[0]), .i_go(go), .i_eps(eps), .p_v(hv), .p_p(hp), .p_d(hd), .p_f(hf), .r_v(qr_v),
            .r_d(qr_d), .o_f(rf));
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_rf (.clk(sk), .rst_n(rst[0]), .d(rf), .q(qn_f[NQE]));
    end endgenerate

    // ------------------------------------------------------------------ engine tiles
    // norm rungs: the group partial of tile t (TI 1) to its head (t - 1), the head's rstd back (registered relays)
    wire        xpv [0:NTL]; wire [7:0] xpi [0:NTL]; wire [31:0] xpd [0:NTL];   // tile t's outputs
    wire        xrv [0:NTL]; wire [31:0] xrd [0:NTL];
    genvar t;
    generate for (t = 0; t < NTL; t = t + 1) begin : g_t
        localparam integer B1 = NQN, B2 = NQN + NKV, B3 = B2 + NQB, B4 = B3 + NSW;
        // TK 2: the QB tap (no write slots), TK 5: QB engine TI (slots 2 TI, 2 TI + 1)
        // TK 6: the QN tap (no write slots), TK 7: QN quant engine TI (slot TI)
        localparam integer TK = (t == 0) ? 6 : (t < B1) ? 7 : (t < B2) ? 1 : (t == B2) ? 2 : (t < B3) ? 5 : (t < B4) ? 3 : 4;
        localparam integer TI = (t < B1) ? (t == 0 ? 0 : t - 1) : (t < B2) ? t - B1 : (t < B3) ? (t == B2 ? 0 : t - B2 - 1) : (t < B4) ? t - B3 : t - B4;
        localparam integer NT = (t < B1) ? NQQ : (t < B2) ? NKV : (t < B3) ? NPB : (t < B4) ? NSW : NSM;
        localparam integer WS = (TK == 2 || TK == 6) ? 0 : (TK == 7) ? 1 : S_WR / NT, W0 = TI * WS;
        localparam integer WSX = (WS > 0) ? WS : 1;
        wire [WSX-1:0] o_v; wire [WSX*14-1:0] o_a; wire [WSX*16-1:0] o_m; wire [WSX*512-1:0] o_d;
        wire o_fu, o_fo, o_alive, o_den, o_rdy; wire [7:0] o_rjid;
        // rung relays: into a head (TK <= 1, TI 0) from t + 1; into a member (TI 1) from t - 1
        reg ipv, irv; reg [7:0] ipi; reg [31:0] ipd, ird;
        if (TK <= 1 && TI == 0 && NT == 2) begin : g_rh
            wire v; wire [39:0] d;
            ot_hdc_delay #(.W(1), .D(SRD), .RESET(1)) u_v (.clk(sk), .rst_n(rst[t]), .d(xpv[t + 1]), .q(v));
            ot_hdc_delay #(.W(40), .D(SRD)) u_d (.clk(sk), .rst_n(rst[t]), .d({xpi[t + 1], xpd[t + 1]}), .q(d));
            always @(*) begin ipv = v; {ipi, ipd} = d; end
        end else begin : g_rh0
            always @(*) begin ipv = 1'b0; ipi = 8'd0; ipd = 32'd0; end
        end
        if (TK <= 1 && TI == 1) begin : g_rm
            wire v; wire [31:0] d;
            ot_hdc_delay #(.W(1), .D(SRD), .RESET(1)) u_v (.clk(sk), .rst_n(rst[t]), .d(xrv[t - 1]), .q(v));
            ot_hdc_delay #(.W(32), .D(SRD)) u_d (.clk(sk), .rst_n(rst[t]), .d(xrd[t - 1]), .q(d));
            always @(*) begin irv = v; ird = d; end
        end else begin : g_rm0
            always @(*) begin irv = 1'b0; ird = 32'd0; end
        end
        if (TK == 6) begin : g_qnt
            assign o_v = 1'b0; assign o_a = 0; assign o_m = 0; assign o_d = 0;
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
            // two data halves, identical control; half 0 carries the job fields, the status and the faults
            genvar h;
            for (h = 0; h < 2; h = h + 1) begin : g_h
                wire [S_RD*256-1:0] dh;
                genvar s2;
                for (s2 = 0; s2 < S_RD; s2 = s2 + 1) begin : g_s
                    assign dh[256 * s2 +: 256] = dd[t][512 * s2 + 256 * h +: 256];
                end
                wire hgq, hgo, hfu, hfo, hal, hde, hrd; wire [1:0] hgr, hgw; wire [13:0] hob; wire [31:0] hep; wire [7:0] hrj;
                ot_s81_su_qnt #(.N(QN_N), .S_RD(S_RD), .NFI(NQE + 1), .MUT(MUT)) u_qnt (
                    .clk(sk), .rst_in(rst[t]),
                    .dn_st_i(dst[t]), .dn_kind_i(dkd[t]), .dn_gsel_i(dgs[t]), .dn_jid_i(dji[t]), .dn_v_i(dv[t]), .dn_d_i(dh),
                    .i_f(h == 0 ? qn_f : {(NQE + 1){1'b0}}), .e_v(qt_v[h]), .e_d(qt_d[h]), .e_t(qt_t[h]), .e_gq(hgq),
                    .e_gr(hgr), .e_gw(hgw), .e_go(hgo), .e_ob(hob), .e_eps(hep), .o_fu(hfu), .o_fo(hfo), .o_alive(hal),
                    .o_den(hde), .o_rdy(hrd), .o_rjid(hrj));
                if (h == 0) begin : g_h0
                    assign qt_gq = hgq; assign qt_gr = hgr; assign qt_gw = hgw; assign qt_go = hgo; assign qt_ob = hob;
                    assign qt_eps = hep;
                    assign o_fu = hfu; assign o_fo = hfo; assign o_alive = hal; assign o_den = hde; assign o_rdy = hrd;
                    assign o_rjid = hrj;
                end
            end
        end else if (TK == 7) begin : g_qnq
            // the y of norm engines 4 TI .. 4 TI + 3 (equal-depth relays) and the obase
            wire rv; wire [7:0] rt; wire [1023:0] ry; wire [13:0] rob;
            ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_rv (.clk(sk), .rst_n(rst[t]), .d(qy_v[4 * TI]), .q(rv));
            ot_hdc_delay #(.W(8 + 1024 + 14), .D(ERL)) u_rd (.clk(sk), .rst_n(rst[t]),
                .d({qy_i[8 * 4 * TI +: 8], qy_d[1024 * TI +: 1024], qt_ob}), .q({rt, ry, rob}));
            localparam integer PN = TI ^ 1;
            wire [3:0] CB = TI;
            ot_s81_su_qnq #(.N(QN_N), .MLAT(LM)) u_qnq (
                .clk(sk), .rst_in(rst[t]), .cfg_b(CB), .i_v(rv), .i_t(rt), .i_y(ry), .i_ob(rob),
                .nx_i_v(qnxv[PN]), .nx_i_q(qnxq[PN]), .nx_i_e(qnxe[PN]), .nx_o_v(qnxv[TI]), .nx_o_q(qnxq[TI]), .nx_o_e(qnxe[TI]),
                .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
                .o_rdy(o_rdy), .o_rjid(o_rjid));
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
        end else if (TK == 2) begin : g_qbt
            assign o_v = 1'b0; assign o_a = 0; assign o_m = 0; assign o_d = 0;
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
            ot_s81_su_qbt #(.QB_NB(QB_NB), .S_RD(S_RD), .NPB(NPB)) u_qbt (
                .clk(sk), .rst_in(rst[t]),
                .dn_st_i(dst[t]), .dn_kind_i(dkd[t]), .dn_gsel_i(dgs[t]), .dn_fp4_i(df4[t]), .dn_jid_i(dji[t]),
                .dn_v_i(dv[t]), .dn_d_i(dd[t]), .e_v(qe_v), .e_d(qe_d), .e_t(qe_t), .e_ob(qe_ob), .e_f4(qe_f4),
                .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
        end else if (TK == 5) begin : g_qbe
            // equal-depth relays from the tap (every engine ERL stations: lockstep), positions 2 TI / 2 TI + 1
            wire [1:0] rv; wire [1023:0] rd; wire [23:0] rt; wire [13:0] rob; wire rf4;
            ot_hdc_delay #(.W(2), .D(ERL), .RESET(1)) u_rv (.clk(sk), .rst_n(rst[t]), .d(qe_v[2 * TI +: 2]), .q(rv));
            ot_hdc_delay #(.W(1024 + 24 + 15), .D(ERL)) u_rd (.clk(sk), .rst_n(rst[t]),
                .d({qe_d[1024 * TI +: 1024], qe_t[24 * TI +: 24], qe_ob, qe_f4}), .q({rd, rt, rob, rf4}));
            localparam integer PN = TI ^ 1;              // the pair neighbour
            wire [3:0] CB = TI;
            ot_s81_su_qbe #(.QB_NB(QB_NB), .NPB(NPB)) u_qbe (
                .clk(sk), .rst_in(rst[t]), .cfg_b(CB),
                .i_vlo(rv[0]), .i_vhi(rv[1]), .i_lo(rd[511:0]), .i_hi(rd[1023:512]), .i_tlo(rt[11:0]), .i_thi(rt[23:12]),
                .i_ob(rob), .i_f4(rf4), .nx_i_v(nxv[PN]), .nx_i_q(nxq[PN]), .nx_i_e(nxe[PN]),
                .nx_o_v(nxv[TI]), .nx_o_q(nxq[TI]), .nx_o_e(nxe[TI]),
                .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
                .o_rdy(o_rdy), .o_rjid(o_rjid));
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
        end else if (TK == 4) begin : g_sm
            // SM (el1011-s81su-sm, spec v3): tap/out smt + per head 16 lanes sml, sum smc, root smr, 8 divide smd;
            // every intra-stop link through SRL equal-depth relays (lanes in lockstep)
            localparam integer NPS = (S_RD < 5) ? S_RD : 5;
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
            wire s_v, p_v, c_v, cs_v, e_v, o_vv, den_v, f_any; wire [1023:0] d_d, e_d; wire [511:0] o_dd;
            wire [6:0] c_nv; wire [2:0] c_lt; wire [31:0] c_scale; wire [63:0] c_sink; wire [4:0] cs_i; wire [63:0] cs_d;
            wire [1:0] hden_v; wire [15:0] hf;
            wire [3:0] CTI = TI;
            ot_s81_su_smt #(.SM_H(SM_H), .SM_LPH(SM_LPH), .S_RD(S_RD), .WS(WS), .MUT(MUT)) u_smt (
                .clk(sk), .rst_in(rst[t]), .cfg_ti(CTI), .dn_st_i(dst[t]), .dn_kind_i(dkd[t]), .dn_jid_i(dji[t]),
                .dn_v_i(dv[t]), .dn_p_i(dd[t][0 +: NPS * 512]), .dn_d_i(dd[t][1024 * TI +: 1024]),
                .s_v(s_v), .p_v(p_v), .d_d(d_d), .c_v(c_v), .c_nv(c_nv), .c_lt(c_lt), .c_scale(c_scale), .c_sink(c_sink),
                .cs_v(cs_v), .cs_i(cs_i), .cs_d(cs_d), .e_v_i(e_v), .e_d_i(e_d), .o_v_i(o_vv), .o_d_i(o_dd),
                .den_v_i(hden_v[0]), .f_i(f_any),
                .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
                .o_rdy(o_rdy), .o_rjid(o_rjid));
            assign f_any = |hf;
            // relayed copies (SRL stations) of the tap's outputs: one copy per destination group
            wire rs_v, rp_v, rc_v, rcs_v; wire [1023:0] rd_d; wire [6:0] rc_nv; wire [2:0] rc_lt; wire [31:0] rc_scale;
            wire [63:0] rc_sink; wire [4:0] rcs_i; wire [63:0] rcs_d;
            ot_hdc_delay #(.W(4), .D(SRL), .RESET(1)) u_tv (.clk(sk), .rst_n(rst[t]), .d({s_v, p_v, c_v, cs_v}),
                .q({rs_v, rp_v, rc_v, rcs_v}));
            ot_hdc_delay #(.W(1024 + 7 + 3 + 32 + 64 + 5 + 64), .D(SRL)) u_td (.clk(sk), .rst_n(rst[t]),
                .d({d_d, c_nv, c_lt, c_scale, c_sink, cs_i, cs_d}), .q({rd_d, rc_nv, rc_lt, rc_scale, rc_sink, rcs_i, rcs_d}));
            wire [1:0] he_v; wire [1:0] ho_v;
            genvar h, ln, pp;
            for (h = 0; h < 2; h = h + 1) begin : g_h
                wire [15:0] l_mxv, l_ev, l_es, l_el; wire [511:0] l_mx, l_e;
                wire mv, dv0; wire [31:0] nmb, den;
                wire rmv, rdv; wire [31:0] rnmb, rden;
                ot_hdc_delay #(.W(2), .D(SRL), .RESET(1)) u_rv (.clk(sk), .rst_n(rst[t]), .d({mv, dv0}), .q({rmv, rdv}));
                ot_hdc_delay #(.W(64), .D(SRL)) u_rd (.clk(sk), .rst_n(rst[t]), .d({nmb, den}), .q({rnmb, rden}));
                for (ln = 0; ln < 16; ln = ln + 1) begin : g_l
                    wire sken = (ln == 0);
                    ot_s81_su_sml #(.NVMAX(SM_NVMAX), .LM(LM), .LA(LA)) u_sml (
                        .clk(sk), .rst_in(rst[t]), .sk_en(sken), .i_cv(rc_v), .i_nv(rc_nv), .i_scale(rc_scale),
                        .i_sink(rc_sink[32 * h +: 32]), .i_sv(rs_v), .i_s(rd_d[512 * h + 32 * ln +: 32]),
                        .i_mv(rmv), .i_nmb(rnmb), .o_mxv(l_mxv[ln]), .o_mx(l_mx[32 * ln +: 32]),
                        .o_ev(l_ev[ln]), .o_es(l_es[ln]), .o_el(l_el[ln]), .o_e(l_e[32 * ln +: 32]));
                end
                // lane outputs relayed to the sum / root / tap
                wire rl_mxv, rl_ev, rl_el, rl_skv; wire [511:0] rl_mx, rl_e; wire [31:0] rl_sk;
                ot_hdc_delay #(.W(4), .D(SRL), .RESET(1)) u_lv (.clk(sk), .rst_n(rst[t]),
                    .d({l_mxv[1], l_ev[1], l_el[1], l_ev[0] && l_es[0]}), .q({rl_mxv, rl_ev, rl_el, rl_skv}));
                ot_hdc_delay #(.W(512 + 512 + 32), .D(SRL)) u_ld (.clk(sk), .rst_n(rst[t]), .d({l_mx, l_e, l_e[31:0]}),
                    .q({rl_mx, rl_e, rl_sk}));
                wire c_ov, c_ol; wire [31:0] c_os; wire rc_ov, rc_ol; wire [31:0] rc_os;
                ot_s81_su_smc #(.LPH(16), .LA(LA)) u_smc (.clk(sk), .rst_in(rst[t]), .i_v(rl_ev), .i_l(rl_el), .i_e(rl_e),
                    .o_v(c_ov), .o_l(c_ol), .o_s(c_os));
                ot_hdc_delay #(.W(2), .D(SRL), .RESET(1)) u_cv (.clk(sk), .rst_n(rst[t]), .d({c_ov, c_ol}), .q({rc_ov, rc_ol}));
                ot_hdc_delay #(.W(32), .D(SRL)) u_cd (.clk(sk), .rst_n(rst[t]), .d(c_os), .q(rc_os));
                ot_s81_su_smr #(.LPH(16), .LA(LA)) u_smr (.clk(sk), .rst_in(rst[t]), .i_cv(rc_v), .i_lt(rc_lt),
                    .i_mxv(rl_mxv), .i_mx(rl_mx), .i_skv(rl_skv), .i_sk(rl_sk), .i_vv(rc_ov), .i_vl(rc_ol), .i_vs(rc_os),
                    .o_mv(mv), .o_nmb(nmb), .o_dv(dv0), .o_den(den));
                assign hden_v[h] = rdv;
                // divide engines (one RoPE pair each)
                wire [7:0] d_ov, d_f; wire [255:0] d_o;
                for (pp = 0; pp < 8; pp = pp + 1) begin : g_p
                    wire [2:0] CP = pp;
                    ot_s81_su_smd #(.LPH(16), .LM(LM), .LA(LA), .STALEDEN(MUT == 5)) u_smd (
                        .clk(sk), .rst_in(rst[t]), .cfg_p(CP), .i_pv(rp_v), .i_pa(rd_d[512 * h + 64 * pp +: 64]),
                        .i_dv(rdv), .i_den(rden), .i_csv(rcs_v), .i_csi(rcs_i), .i_csd(rcs_d),
                        .o_ov(d_ov[pp]), .o_o(d_o[32 * pp +: 32]), .o_f(d_f[pp]));
                end
                assign hf[8 * h +: 8] = d_f;
                // e / o rows to the tap
                wire [255:0] rd_o; wire rd_ov;
                ot_hdc_delay #(.W(1), .D(SRL), .RESET(1)) u_ov (.clk(sk), .rst_n(rst[t]), .d(d_ov[0]), .q(rd_ov));
                ot_hdc_delay #(.W(256), .D(SRL)) u_od (.clk(sk), .rst_n(rst[t]), .d(d_o), .q(rd_o));
                assign e_d[512 * h +: 512] = rl_e;
                assign o_dd[256 * h +: 256] = rd_o;
                assign he_v[h] = rl_ev;
                assign ho_v[h] = rd_ov;
            end
            assign e_v = he_v[0];
            assign o_vv = ho_v[0];
            assign den_v = hden_v[0];
        end else begin : g_tl
            ot_s81_su_tile #(.TK(TK), .TI(TI), .NT(NT), .QN_N(QN_N), .KV_N(KV_N), .QB_NB(QB_NB), .SW_W(SW_W), .SM_H(SM_H),
                             .SM_LPH(SM_LPH), .SM_NVMAX(SM_NVMAX), .S_RD(S_RD), .S_WR(S_WR), .LM(LM), .LA(LA), .MUT(MUT)) u_tile (
                .clk(sk), .rst_in(rst[t]),
                .dn_st_i(dst[t]), .dn_kind_i(dkd[t]), .dn_gsel_i(dgs[t]), .dn_fp4_i(df4[t]), .dn_jid_i(dji[t]),
                .dn_v_i(dv[t]), .dn_d_i(dd[t]),
                .x_pp_v_i(ipv), .x_pp_i_i(ipi), .x_pp_d_i(ipd), .x_rb_v_i(irv), .x_rb_d_i(ird),
                .x_pp_v_o(xpv[t]), .x_pp_i_o(xpi[t]), .x_pp_d_o(xpd[t]), .x_rb_v_o(xrv[t]), .x_rb_d_o(xrd[t]),
                .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
                .o_rdy(o_rdy), .o_rjid(o_rjid));
        end
        // reset spine station
        reg rs_q;
        always @(posedge sk or negedge rst[t]) if (!rst[t]) rs_q <= 1'b0; else rs_q <= 1'b1;
        assign rst[t + 1] = rs_q;
        // down spine relay station
        ot_hdc_delay #(.W(1 + S_RD), .D(SRD), .RESET(1)) u_dsc (.clk(sk), .rst_n(rst[t]), .d({dst[t], dv[t]}),
                                                               .q({dst[t + 1], dv[t + 1]}));
        ot_hdc_delay #(.W(15 + S_RD * 512), .D(SRD)) u_dsd (.clk(sk), .rst_n(rst[t]),
            .d({dkd[t], dgs[t], df4[t], dji[t], dd[t]}), .q({dkd[t + 1], dgs[t + 1], df4[t + 1], dji[t + 1], dd[t + 1]}));
        // up spine relay station: the tile's window merged in
        integer s;
        reg [S_WR-1:0] uv_q; reg [S_WR*14-1:0] ua_q; reg [S_WR*16-1:0] um_q; reg [S_WR*512-1:0] ud_q;
        reg ufu_q, ufo_q, ual_q, ude_q, urd_q; reg [7:0] urj_q;
        ot_hdc_delay #(.W(S_WR + 13), .D(SRD - 1), .RESET(1)) u_usc (.clk(sk), .rst_n(rst[t]),
            .d({uv_q, ufu_q, ufo_q, ual_q, ude_q, urd_q, urj_q}), .q({uv[t], ufu[t], ufo[t], ual[t], ude[t], urd[t], urj[t]}));
        ot_hdc_delay #(.W(S_WR * 542), .D(SRD - 1)) u_usd (.clk(sk), .rst_n(rst[t]), .d({ua_q, um_q, ud_q}),
                                                          .q({ua[t], um[t], ud[t]}));
        always @(posedge sk) begin
            for (s = 0; s < S_WR; s = s + 1)
                if (s >= W0 && s < W0 + WS && o_v[s - W0]) begin
                    ua_q[14 * s +: 14] <= o_a[14 * (s - W0) +: 14]; um_q[16 * s +: 16] <= o_m[16 * (s - W0) +: 16];
                    ud_q[512 * s +: 512] <= o_d[512 * (s - W0) +: 512];
                end else begin
                    ua_q[14 * s +: 14] <= ua[t + 1][14 * s +: 14]; um_q[16 * s +: 16] <= um[t + 1][16 * s +: 16];
                    ud_q[512 * s +: 512] <= ud[t + 1][512 * s +: 512];
                end
        end
        always @(posedge sk or negedge rst[t]) begin
            if (!rst[t]) begin uv_q <= 0; ufu_q <= 0; ufo_q <= 0; ual_q <= 0; ude_q <= 0; urd_q <= 0; urj_q <= 0; end
            else begin
                for (s = 0; s < S_WR; s = s + 1) uv_q[s] <= uv[t + 1][s] || (s >= W0 && s < W0 + WS && o_v[s - W0]);
                ufu_q <= ufu[t + 1] || o_fu; ufo_q <= ufo[t + 1] || o_fo; ual_q <= ual[t + 1] && o_alive;
                ude_q <= ude[t + 1] && o_den; urd_q <= urd[t + 1] || o_rdy; urj_q <= o_rdy ? o_rjid : urj[t + 1];
            end
        end
    end endgenerate
    assign xpv[NTL] = 1'b0; assign xpi[NTL] = 8'd0; assign xpd[NTL] = 32'd0;
endmodule
