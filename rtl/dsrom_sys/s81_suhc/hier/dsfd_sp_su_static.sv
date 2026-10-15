`timescale 1ns/1ps
// Connected fixed-calendar successor, preserving the actual granular arithmetic
// and registered datapath of dsfd_sp_su_h. No legacy hctl/engine_adapter is instantiated.
// Full production programs, mapped calendar storage and physical binding are
// separate integration gates; this source alone does not qualify the full layer.
module dsfd_sp_su_static #(
    parameter integer QN_N = 256, KV_N = 512, QB_NB = 32, SW_W = 1024, SM_H = 16, SM_LPH = 16, SM_NVMAX = 40,
    parameter integer S_RD = 16, S_WR = 16, LM = 5, LA = 4, OQ = 1024, MUT = 0, AMUT = 0, XMUT = 0,
    // lane-group tiles (production: QN 2 x 128 lanes, KV 2 x 256 lanes, QB 4 x 8 blocks, SW 8 x 128 lanes, SM 8 x 2
    // heads; pin owners 4 x (4 read + 4 write slots); every tile <= ~600 x 600 um)
    // QN (el1011-s81su-qn, spec v3): a tap (2 data halves) + NQE = QN_N / 8 norm engines + a reduce + NQQ = QN_N / 32
    // act-quant engines; spine stops: the tap, then the quant engines (the norm engines and the reduce hang off the tap)
    parameter integer NQE = QN_N / 8,
    parameter integer NQQ = QN_N / 32,
    // KV (el1011-s81su-kv, spec v3): a tap (4 data quarters) + NKE = KV_N / 8 norm engines (the last 8: RoPE) + 4 half
    // trees + a reduce + NKQ = KV_N / 32 act-quant engines; ONE spine stop (the tap's; the engines' slots merge there).
    // NKV = the exps-row writes of a KV vector (one a group of 8 blocks; the control tile's rows_out)
    parameter integer NKV = KV_N / 256,
    parameter integer NKE = KV_N / 8,
    parameter integer NKQ = KV_N / 32,
    // QB (el1011-s81su, spec v3): one tap + NPB engines (rate-matched to the down spine: NPB = S_RD / 2 blocks a pass)
    parameter integer NPB = (S_RD / 2 > 2) ? S_RD / 2 : 2,
    parameter integer ERL = (S_RD >= 16) ? 3 : 1,      // tap -> engine relays, equal depth on every engine (lockstep)
    parameter integer NSW = (SW_W >= 128) ? SW_W / 128 : 1,
    // SW (el1011-s81su-sw, spec v3): one tap + NSWQ act-quant engines (the QB master) on the spine, NSWQ * 2 * 16 / SLPE
    // ... lane engines off the tap (SLPE lanes each, rate-matched: a beat takes >= SLPE spine cycles); ERS equal-depth
    // relay stations tap -> lane engine (and lane faults back), <= 500 um a station over the ~3.2 x 2 mm SW region
    parameter integer NSWQ = (S_RD / 2 > 2) ? S_RD / 2 : 2,
    parameter integer ERS = (S_RD >= 16) ? 5 : 1,
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
    parameter integer NRC = (S_RD >= 16) ? 5 : 1,
    // RXH 1 (s81-romB2 2026-10-14): the RA / RB / QR tile ot_s81_su_rxt sits at the SPINE HEAD beside the pin owners:
    // it taps the stop-0 down register and its write slot (slot 0) merges at stop 0's up relay, instead of the far end
    // of the ~2 x SRD x NTL cycle spines (measured hier RB 277 / QR 298 / RA 353 vs flat 69 / 115 / 168). 0 = far end.
    parameter integer RXH = 1
) (
    input wire sk, srs,
    // Calendar words are supplied on every edge, including idle edges. They must
    // come from compiled configuration storage; they are never computed from status.
    input wire arm,
    input wire calendar_valid,
    input wire [31:0] calendar_cycle,
    input wire [1023:0] calendar_word,
    output wire [31:0] cycle,
    output wire done,
    output wire [7:0] done_tag,
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
    localparam integer NSWS = 1 + NSWQ;                // SW stops: the tap, then the quant engines
    localparam integer NTL = NQN + 1 + NQB + NSWS + NSM + 1;   // + the RA / RB / QR stop (die item F1)
    localparam integer SLPE = (SW_W / (8 * S_RD) > 16) ? 16 : (SW_W / (8 * S_RD) < 1) ? 1 : SW_W / (8 * S_RD);
    localparam integer SL = 2 * NSWQ, SNPS = (SW_W / 16) / SL, SEPR = 16 / SLPE, SNCH = SL * SEPR, SNE = SNCH * SNPS;
    // SW tap -> lane engines, lane chains -> quant engines
    wire [SL*512-1:0]    sw_d;
    wire [SNPS-1:0]      sw_gv, sw_uv;
    wire [11:0]          sw_t;
    wire [31:0]          sw_w, sw_lim;
    wire [13:0]          sw_ob;
    wire [SNCH-1:0]      sw_f;                         // chain-head lane faults, relayed into the tap
    wire [SNE-1:0]       sc_v, sc_f;                   // engine e = ch * SNPS + P: its chain output
    wire [SNE*16*SLPE-1:0] sc_d;
    wire [SNE*12-1:0]    sc_t;
    wire                 snxv [0:NSWQ-1];
    wire [255:0]         snxq [0:NSWQ-1];
    wire [9:0]           snxe [0:NSWQ-1];
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

    // Fixed-cycle control. There is no command FIFO, asynchronous issue adapter,
    // ready path, descriptor-dependent issue, or completion-driven rescheduling.
    wire [S_RD-1:0] c_rq_v;
    wire [S_RD*14-1:0] c_rq_row;
    wire [S_RD-1:0] p_rv;
    wire [S_RD*30-1:0] p_rf;
    wire [S_WR-1:0] p_uv;
    wire rst_c = srs;
    wire moe_iv,moe_ov,moe_fault;
    wire [13:0]moe_ir,moe_or;
    wire [511:0]moe_od;
    reg moe_availability_fault;
    // Explicit compiler operand pulse; missing operands latch a fault and never
    // defer, cancel, or replay the arithmetic. Slots 0..6 are E0 through E6.
    ot_s81_su_moe_sum_static u_moe(.ck({6{sk}}),.rst_n(rst_c),.i_v(moe_iv),
        .i_e(dd[0][3583:0]),.i_present(dv[0][6:0]),.i_row(moe_ir),.o_v(moe_ov),.o_d(moe_od),
        .o_row(moe_or),.fault(moe_fault));
    always @(posedge sk or negedge rst_c)
        if(!rst_c)moe_availability_fault<=0;
        else if(moe_iv && dv[0][6:0]!=7'h7f)moe_availability_fault<=1;
    ot_s81_su_calendar_ctl u_calendar (
        .clk(sk), .rst_n(srs), .arm(arm), .calendar_valid(calendar_valid),
        .calendar_cycle(calendar_cycle), .calendar_word(calendar_word), .cycle(cycle),
        .rq_v(c_rq_v), .rq_row(c_rq_row), .rs_v(rs_v),
        .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask),
        .dn_st(dst[0]), .dn_kind(dkd[0]), .dn_gsel(dgs[0]),
        .dn_fp4(df4[0]), .dn_jid(dji[0]), .moe_v(moe_iv), .moe_row(moe_ir), .done(done), .done_tag(done_tag),
        .up_fu(ufu[0]|moe_fault|moe_availability_fault), .up_fo(ufo[0]), .up_alive(ual[0]),
        .up_den(ude[0]), .up_rdy(urd[0]), .up_rjid(urj[0]),
        .fault(flt), .fault_code(fcode), .running(online));
    initial begin
        if (S_RD != 16 || S_WR != 16) $fatal(1, "native calendar ABI is 16 SU slots each way");
    end
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


    // ------------------------------------------------------------------ KV: norm engines + reduce + quant (off the spine)
    localparam integer KL = KV_N / 16;                 // KV tap positions (rows a vector)
    localparam integer NRP = 64 / 8;                   // RoPE engines (RD 64)
    wire [KL-1:0]       kt_v  [0:3];
    wire [KL*128-1:0]   kt_d  [0:3];
    wire [511:0]        kt_cs [0:3];
    wire                kt_gk, kt_go;
    wire [1:0]          kt_gr, kt_gw, kt_mode;
    wire [13:0]         kt_ob, kt_nb;
    wire [31:0]         kt_eps;
    wire [NKE:0]        kv_f;
    wire [NKE-1:0]      ky_v, kp_v;
    wire [NKE*256-1:0]  ky_d;
    wire [NKE*32-1:0]   kp_d;
    wire                kr_v;
    wire [31:0]         kr_d;
    wire [NKE-1:0] kn_v;wire [NKE*128-1:0] kn_d;
    wire [15:0] cnn_v;wire [16*14-1:0] cnn_a;wire [16*512-1:0] cnn_d;
    wire ikr_v, ikr_fault;wire [31:0] ikr_d;
    wire [19:0] cn_v, cn_fault;
    wire [20*14-1:0] cn_a;wire [20*16-1:0] cn_m;wire [20*512-1:0] cn_d;
    // IK's logical chunk order 0..15 maps to physical KVE48..63. The
    // zero prefix is not included in either tree or the divisor.
    ot_s81_su_ik_reduce u_ik_reduce(.ck_half({2{sk}}),.rs_half({2{rst[0]}}),
        .ck_reduce(sk),.rs_reduce(rst[0]),.go(kt_go),.eps(kt_eps),
        .p_v(kp_v[NKE-16+:16] & {16{kt_mode==2}}),.p_d(kp_d[32*(NKE-16)+:512]),
        .r_v(ikr_v),.r_d(ikr_d),.fault(ikr_fault));
    wire [NKQ-1:0]      kq_v, kq_fu, kq_fo, kq_al, kq_de, kq_ev;
    wire [NKQ*14-1:0]   kq_a;
    wire [NKQ*16-1:0]   kq_m;
    wire [NKQ*512-1:0]  kq_d;
    wire [NKQ*10-1:0]   kq_ee;
    wire                kqxv [0:NKQ-1];
    wire [255:0]        kqxq [0:NKQ-1];
    genvar ke;
    generate for (ke = 0; ke < NKE; ke = ke + 1) begin : g_kve
        // engine ke = position ke / 2, data half ke % 2 = quarters 2 (ke % 2), 2 (ke % 2) + 1; equal-depth relays
        localparam integer KP = ke / 2, KH = ke % 2;
        wire iv, igk, ef, pv, yv; wire [255:0] ix, yd; wire [1:0] igr, igw; wire [31:0] pd; wire rv; wire [31:0] rd;
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_iv (.clk(sk), .rst_n(rst[0]), .d(kt_v[2 * KH][KP]), .q(iv));
        ot_hdc_delay #(.W(256 + 5), .D(ERL)) u_id (.clk(sk), .rst_n(rst[0]),
            .d({kt_d[2 * KH + 1][128 * KP +: 128], kt_d[2 * KH][128 * KP +: 128], kt_gk, kt_gr, kt_gw}),
            .q({ix, igk, igr, igw}));
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_rv (.clk(sk), .rst_n(rst[0]), .d(kt_mode==2?ikr_v:kr_v), .q(rv));
        ot_hdc_delay #(.W(32), .D(ERL)) u_rd (.clk(sk), .rst_n(rst[0]), .d(kt_mode==2?ikr_d:kr_d), .q(rd));
        if (ke >= NKE - NRP) begin : g_rp
            // RoPE engine k: cos / sin of lane pairs 4 k .. 4 k + 3 = quarter k % 4 of param rows 1 / 2 (cos), 3 / 4 (sin)
            localparam integer K = ke - (NKE - NRP);
            wire [127:0] cc, sn;
            ot_hdc_delay #(.W(256), .D(ERL)) u_cs (.clk(sk), .rst_n(rst[0]),
                .d({kt_cs[K % 4][(K < 4 ? 256 : 384) +: 128], kt_cs[K % 4][(K < 4 ? 0 : 128) +: 128]}), .q({sn, cc}));
            ot_s81_su_kve #(.RP(1), .LM(LM), .LA(LA)) u_kve (
                .clk(sk), .rst_in(rst[0]), .i_v(iv), .i_x(ix), .i_gk(igk), .i_gr(igr), .i_gw(igw), .i_cos(cc), .i_sin(sn),
                .r_v(rv), .r_d(rd), .p_v(pv), .p_d(pd), .norm_v(kn_v[ke]),.norm_y(kn_d[128*ke+:128]),.y_v(yv), .y(yd), .o_f(ef));
        end else begin : g_np
            ot_s81_su_kve #(.RP(0), .LM(LM), .LA(LA)) u_kve (
                .clk(sk), .rst_in(rst[0]), .i_v(iv), .i_x(ix), .i_gk(igk), .i_gr(igr), .i_gw(igw), .i_cos(128'd0),
                .i_sin(128'd0), .r_v(rv), .r_d(rd), .p_v(pv), .p_d(pd), .norm_v(kn_v[ke]),.norm_y(kn_d[128*ke+:128]),.y_v(yv), .y(yd), .o_f(ef));
        end
        assign ky_v[ke] = yv; assign ky_d[256 * ke +: 256] = yd;
        ot_hdc_delay #(.W(2), .D(ERL), .RESET(1)) u_pv (.clk(sk), .rst_n(rst[0]), .d({pv, ef}), .q({kp_v[ke], kv_f[ke]}));
        ot_hdc_delay #(.W(32), .D(ERL)) u_pd (.clk(sk), .rst_n(rst[0]), .d(pd), .q(kp_d[32 * ke +: 32]));
    end endgenerate
    generate if (1) begin : g_kvr
        localparam integer NKH = NKE / 16;
        wire go, rf; wire [31:0] eps;
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_gv (.clk(sk), .rst_n(rst[0]), .d(kt_go), .q(go));
        ot_hdc_delay #(.W(32), .D(ERL)) u_gd (.clk(sk), .rst_n(rst[0]), .d(kt_eps), .q(eps));
        // NKH half trees of 16 engines (the QN master qnh) -> the reduce (NE NKH: the golden tree's top levels)
        wire [NKH-1:0] hv, hp, hf; wire [NKH*32-1:0] hd;
        genvar hh;
        for (hh = 0; hh < NKH; hh = hh + 1) begin : g_kvh
            ot_s81_su_qnh #(.NE(16), .LA(LA)) u_qnh (
                .clk(sk), .rst_in(rst[0]), .i_go(go), .p_v(kp_v[16 * hh +: 16]), .p_p(16'd0),
                .p_d(kp_d[512 * hh +: 512]), .s_v(hv[hh]), .s_p(hp[hh]), .s_d(hd[32 * hh +: 32]), .o_f(hf[hh]));
        end
        ot_s81_su_qnr #(.NE(NKH), .NV(1), .D(KV_N), .LM(LM), .LA(LA)) u_kvr (
            .clk(sk), .rst_in(rst[0]), .i_go(go), .i_eps(eps), .p_v(hv), .p_p(hp), .p_d(hd), .p_f(hf), .r_v(kr_v),
            .r_d(kr_d), .o_f(rf));
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_rf (.clk(sk), .rst_n(rst[0]), .d(rf), .q(kv_f[NKE]));
    end endgenerate
    genvar kb;
    generate for (kb = 0; kb < NKQ; kb = kb + 1) begin : g_kvq
        // block kb = norm engines 4 kb .. 4 kb + 3; e gather of blocks 8 (kb / 8) .. into engine kb % 8 == 7
        wire rv; wire [1023:0] ry; wire [13:0] rob; wire [7:0] gv; wire [79:0] ge;
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_rv (.clk(sk), .rst_n(rst[0]), .d(ky_v[4 * kb]), .q(rv));
        ot_hdc_delay #(.W(1024 + 14), .D(ERL)) u_rd (.clk(sk), .rst_n(rst[0]), .d({ky_d[1024 * kb +: 1024], kt_ob}),
                                                    .q({ry, rob}));
        if (kb % 8 == 7) begin : g_gl
            ot_hdc_delay #(.W(8), .D(ERL), .RESET(1)) u_gv (.clk(sk), .rst_n(rst[0]), .d(kq_ev[kb - 7 +: 8]), .q(gv));
            ot_hdc_delay #(.W(80), .D(ERL)) u_ge (.clk(sk), .rst_n(rst[0]), .d(kq_ee[10 * (kb - 7) +: 80]), .q(ge));
        end else begin : g_g0
            assign gv = 8'd0; assign ge = 80'd0;
        end
        wire [3:0] CB = kb;
        ot_s81_su_cn_norm_write u_cn_norm_write(.clk(sk),.rst_in(rst[0]),
            .i_v(kn_v[4*kb] && kt_mode==1),.i_x(kn_d[512*kb+:512]),
            .i_ob(kt_nb),.i_block(CB),.o_v(cnn_v[kb]),.o_a(cnn_a[14*kb+:14]),.o_d(cnn_d[512*kb+:512]));
        ot_s81_su_cn_write #(.E4M3(1)) u_cn_write(.clk(sk),.rst_in(rst[0]),
            .i_v(rv && kt_mode==1),.i_x(ry),.i_ob(rob),.i_block(CB),
            .o_v(cn_v[kb]),.o_a(cn_a[14*kb+:14]),.o_m(cn_m[16*kb+:16]),
            .o_d(cn_d[512*kb+:512]),.o_fault(cn_fault[kb]));
        if(kb>=NKQ-4) begin:g_ik_write
            localparam integer IB=kb-(NKQ-4), IS=16+IB;
            wire [3:0] IBC=IB;
            ot_s81_su_cn_write #(.E4M3(0)) u_ik_write(.clk(sk),.rst_in(rst[0]),
                .i_v(rv && kt_mode==2),.i_x(ry),.i_ob(rob),.i_block(IBC),
                .o_v(cn_v[IS]),.o_a(cn_a[14*IS+:14]),.o_m(cn_m[16*IS+:16]),
                .o_d(cn_d[512*IS+:512]),.o_fault(cn_fault[IS]));
        end
        wire ov, ofu, ofo, oal, ode, ord; wire [13:0] oa; wire [15:0] om; wire [511:0] od; wire [7:0] orj;
        ot_s81_su_kvq #(.N(KV_N), .MLAT(LM)) u_kvq (
            .clk(sk), .rst_in(rst[0]), .cfg_b(CB), .i_v(rv && kt_mode==0), .i_y(ry), .i_ob(rob), .nx_i_v(kqxv[kb ^ 1]),
            .nx_i_q(kqxq[kb ^ 1]), .nx_o_v(kqxv[kb]), .nx_o_q(kqxq[kb]), .e_o_v(kq_ev[kb]), .e_o_e(kq_ee[10 * kb +: 10]),
            .g_i_v(gv), .g_i_e(ge), .o_v(ov), .o_a(oa), .o_m(om), .o_d(od), .o_fu(ofu), .o_fo(ofo), .o_alive(oal),
            .o_den(ode), .o_rdy(ord), .o_rjid(orj));
        // to the KV stop: equal-depth relays + (S_WR < NKQ, reduced shapes only) a phase of 8 cycles a slot group so
        // the engines sharing slot kb % S_WR never write in the same cycle (full shape: 0)
        localparam integer PH = ERL + 8 * (kb / S_WR);
        ot_hdc_delay #(.W(5), .D(PH), .RESET(1)) u_ov (.clk(sk), .rst_n(rst[0]), .d({ov, ofu, ofo, oal, ode}),
            .q({kq_v[kb], kq_fu[kb], kq_fo[kb], kq_al[kb], kq_de[kb]}));
        ot_hdc_delay #(.W(14 + 16 + 512), .D(PH)) u_od (.clk(sk), .rst_n(rst[0]), .d({oa, om, od}),
            .q({kq_a[14 * kb +: 14], kq_m[16 * kb +: 16], kq_d[512 * kb +: 512]}));
    end endgenerate

    // ------------------------------------------------------------------ SW: lane engines (off the spine, chains)
    genvar sch, sp;
    generate for (sch = 0; sch < SNCH; sch = sch + 1) begin : g_swc
        // chain sch = pass row sch / SEPR, chunk sch % SEPR; engine P of the chain owns that chunk of pass P
        for (sp = 0; sp < SNPS; sp = sp + 1) begin : g_swe
            localparam integer E = sch * SNPS + sp;
            wire gv, uv; wire [32*SLPE-1:0] d; wire [11:0] et; wire [31:0] ew, el;
            ot_hdc_delay #(.W(2), .D(ERS), .RESET(1)) u_iv (.clk(sk), .rst_n(rst[0]), .d({sw_gv[sp], sw_uv[sp]}), .q({gv, uv}));
            ot_hdc_delay #(.W(32 * SLPE + 12 + 64), .D(ERS)) u_id (.clk(sk), .rst_n(rst[0]),
                .d({sw_d[512 * (sch / SEPR) + 32 * SLPE * (sch % SEPR) +: 32 * SLPE], sw_t, sw_w, sw_lim}), .q({d, et, ew, el}));
            wire civ, cif; wire [16*SLPE-1:0] cid; wire [11:0] cit;
            if (sp == SNPS - 1) begin : g_tail
                assign civ = 1'b0; assign cif = 1'b0; assign cid = 0; assign cit = 12'd0;
            end else begin : g_link
                assign civ = sc_v[E + 1]; assign cif = sc_f[E + 1]; assign cid = sc_d[16 * SLPE * (E + 1) +: 16 * SLPE];
                assign cit = sc_t[12 * (E + 1) +: 12];
            end
            ot_s81_su_swe #(.LPE(SLPE), .LM(LM), .LA(LA)) u_swe (
                .clk(sk), .rst_in(rst[0]), .i_gv(gv), .i_uv(uv), .i_d(d), .i_t(et), .i_w(ew), .i_lim(el),
                .c_iv(civ), .c_id(cid), .c_it(cit), .c_if(cif), .c_ov(sc_v[E]), .c_od(sc_d[16 * SLPE * E +: 16 * SLPE]),
                .c_ot(sc_t[12 * E +: 12]), .c_of(sc_f[E]));
        end
        ot_hdc_delay #(.W(1), .D(ERS), .RESET(1)) u_fr (.clk(sk), .rst_n(rst[0]), .d(sc_f[sch * SNPS]), .q(sw_f[sch]));
    end endgenerate

    // ------------------------------------------------------------------ engine tiles
    // norm rungs: the group partial of tile t (TI 1) to its head (t - 1), the head's rstd back (registered relays)
    wire        xpv [0:NTL]; wire [7:0] xpi [0:NTL]; wire [31:0] xpd [0:NTL];   // tile t's outputs
    wire        xrv [0:NTL]; wire [31:0] xrd [0:NTL];
    // RXH: the head-placed rxt's outputs, merged at stop 0
    wire        rx_v, rx_fu, rx_fo, rx_alive; wire [13:0] rx_a; wire [15:0] rx_m; wire [511:0] rx_d;
    wire        rx_v2; wire [13:0] rx_a2; wire [511:0] rx_d2;     // QR pair: the second result row (write slot 1)
    genvar t;
    generate for (t = 0; t < NTL; t = t + 1) begin : g_t
        localparam integer B1 = NQN, B2 = NQN + 1, B3 = B2 + NQB, B4 = B3 + NSWS, B5 = B4 + NSM;
        // TK 2: the QB tap (no write slots), TK 5: QB engine TI (slots 2 TI, 2 TI + 1)
        // TK 6: the QN tap (no write slots), TK 7: QN quant engine TI (slot TI), TK 8: the KV stop (tap + all S_WR slots)
        // TK 12: the SW tap (no write slots), TK 13: SW quant engine TI (the QB master; slots 2 TI, 2 TI + 1)
        // TK 14: the RA / RB / QR tile ot_s81_su_rxt (the last stop; one write slot, slot 0)
        localparam integer TK = (t == 0) ? 6 : (t < B1) ? 7 : (t < B2) ? 8 : (t == B2) ? 2 : (t < B3) ? 5 : (t == B3) ? 12 : (t < B4) ? 13 : (t < B5) ? 4 : 14;
        localparam integer TI = (t < B1) ? (t == 0 ? 0 : t - 1) : (t < B2) ? t - B1 : (t < B3) ? (t == B2 ? 0 : t - B2 - 1) : (t < B4) ? (t == B3 ? 0 : t - B3 - 1) : (t < B5) ? t - B4 : 0;
        localparam integer NT = (t < B1) ? NQQ : (t < B2) ? 1 : (t < B3) ? NPB : (t < B4) ? NSWQ : (t < B5) ? NSM : 1;
        localparam integer WS = (TK == 2 || TK == 6 || TK == 12) ? 0 : (TK == 7 || TK == 14) ? 1 : (TK == 8) ? S_WR : S_WR / NT, W0 = TI * WS;
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
        end else if (TK == 8) begin : g_kv
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
            // four data quarters, identical control; quarter 0 carries the job fields, the status and the faults
            wire tfu, tfo, tal, tde, trd; wire [7:0] trj;
            genvar u;
            for (u = 0; u < 4; u = u + 1) begin : g_u
                wire [S_RD*128-1:0] dq;
                genvar s2;
                for (s2 = 0; s2 < S_RD; s2 = s2 + 1) begin : g_s
                    assign dq[128 * s2 +: 128] = dd[t][512 * s2 + 128 * u +: 128];
                end
                wire ugk, ugo, ufu, ufo, ual, ude, urd; wire [1:0] ugr, ugw, umode; wire [13:0] uob, unb; wire [31:0] uep; wire [7:0] urj;
                ot_s81_su_kvt #(.N(KV_N), .S_RD(S_RD), .NFI(NKE + 1), .MUT(MUT)) u_kvt (
                    .clk(sk), .rst_in(rst[t]),
                    .dn_st_i(dst[t]), .dn_kind_i(dkd[t]), .dn_gsel_i(dgs[t]), .dn_jid_i(dji[t]), .dn_v_i(dv[t]), .dn_d_i(dq),
                    .i_f(u == 0 ? kv_f : {(NKE + 1){1'b0}}), .e_v(kt_v[u]), .e_d(kt_d[u]), .e_gk(ugk), .e_gr(ugr),
                    .e_gw(ugw), .e_go(ugo), .e_mode(umode), .e_ob(uob), .e_nb(unb), .e_eps(uep), .e_cs(kt_cs[u]), .o_fu(ufu), .o_fo(ufo),
                    .o_alive(ual), .o_den(ude), .o_rdy(urd), .o_rjid(urj));
                if (u == 0) begin : g_u0
                    assign kt_gk = ugk; assign kt_gr = ugr; assign kt_gw = ugw; assign kt_go = ugo; assign kt_ob = uob;
                    assign kt_eps = uep; assign kt_mode=umode; assign kt_nb=unb;
                    assign tfu = ufu; assign tfo = ufo; assign tal = ual; assign tde = ude; assign trd = urd; assign trj = urj;
                end
            end
            // the quant engines' slots: engine b on slot b % S_WR (phased apart when shared)
            reg [S_WR-1:0] mv; reg [S_WR*14-1:0] ma; reg [S_WR*16-1:0] mm; reg [S_WR*512-1:0] md;
            always @(*) begin : mrg
                integer b;
                mv = 0; ma = 0; mm = 0; md = 0;
                for (b = 0; b < NKQ; b = b + 1) if (kq_v[b]) begin
                    mv[b % S_WR] = 1'b1;
                    ma[14 * (b % S_WR) +: 14] = ma[14 * (b % S_WR) +: 14] | kq_a[14 * b +: 14];
                    mm[16 * (b % S_WR) +: 16] = mm[16 * (b % S_WR) +: 16] | kq_m[16 * b +: 16];
                    md[512 * (b % S_WR) +: 512] = md[512 * (b % S_WR) +: 512] | kq_d[512 * b +: 512];
                end
                for(b=0;b<16;b=b+1)if(cnn_v[b])begin
                    mv[b%S_WR]=1'b1;
                    ma[14*(b%S_WR)+:14]=cnn_a[14*b+:14];mm[16*(b%S_WR)+:16]=16'hffff;
                    md[512*(b%S_WR)+:512]=cnn_d[512*b+:512];
                end
                for(b=0;b<20;b=b+1)if(cn_v[b])begin
                    mv[(b<16?b:b-16)%S_WR]=1'b1;
                    ma[14*((b<16?b:b-16)%S_WR)+:14]=cn_a[14*b+:14];
                    mm[16*((b<16?b:b-16)%S_WR)+:16]=cn_m[16*b+:16];
                    md[512*((b<16?b:b-16)%S_WR)+:512]=cn_d[512*b+:512];
                end
            end
            assign o_v = mv; assign o_a = ma; assign o_m = mm; assign o_d = md;
            assign o_fu = tfu | (|kq_fu) | (|cn_fault) | ikr_fault; assign o_fo = tfo | (|kq_fo); assign o_alive = tal & (&kq_al);
            assign o_den = tde & (&kq_de); assign o_rdy = trd; assign o_rjid = trj;
`ifndef SYNTHESIS
            always @(posedge sk) if (rst[t]) begin : sc
                integer b, c;
                for (b = 0; b < NKQ; b = b + 1) for (c = b + 1; c < NKQ; c = c + 1)
                    if (kq_v[b] && kq_v[c] && (b % S_WR) == (c % S_WR))
                        $fatal(1, "dsfd_sp_su_h: KV quant engines %0d and %0d write slot %0d in one cycle", b, c, b % S_WR);
            end
`endif
        end else if (TK == 2) begin : g_qbt
            assign o_v = 1'b0; assign o_a = 0; assign o_m = 0; assign o_d = 0;
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
            // full configuration (rate-aligned, S_RD == 2 NPB): two half-taps (the high one is the SW data half-tap, hardened
            // once), cycle for cycle the single tap; reduced shapes: the assembling tap
            if (S_RD == 2 * NPB) begin : g_sp
                ot_s81_su_qbtl #(.QB_NB(QB_NB), .S_RD(S_RD), .NPB(NPB)) u_qbtl (
                    .clk(sk), .rst_in(rst[t]),
                    .dn_st_i(dst[t]), .dn_kind_i(dkd[t]), .dn_gsel_i(dgs[t]), .dn_fp4_i(df4[t]), .dn_jid_i(dji[t]),
                    .dn_v_i(dv[t]), .dn_d_i(dd[t][S_RD*256-1:0]), .e_v(qe_v), .e_d(qe_d[NPB*512-1:0]), .e_t(qe_t), .e_ob(qe_ob),
                    .e_f4(qe_f4), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
                ot_s81_su_swth #(.S_RD(S_RD)) u_qbth (
                    .clk(sk), .dn_d_i(dd[t][S_RD*512-1:S_RD*256]), .e_d(qe_d[2*NPB*512-1:NPB*512]));
            end else begin : g_as
                ot_s81_su_qbt #(.QB_NB(QB_NB), .S_RD(S_RD), .NPB(NPB)) u_qbt (
                    .clk(sk), .rst_in(rst[t]),
                    .dn_st_i(dst[t]), .dn_kind_i(dkd[t]), .dn_gsel_i(dgs[t]), .dn_fp4_i(df4[t]), .dn_jid_i(dji[t]),
                    .dn_v_i(dv[t]), .dn_d_i(dd[t]), .e_v(qe_v), .e_d(qe_d), .e_t(qe_t), .e_ob(qe_ob), .e_f4(qe_f4),
                    .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
            end
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
            wire s_v, p_v, c_v, cs_v, e_v, o_vv, den_v, f_any; wire [1023:0] e_d; wire [511:0] o_dd;
            wire [6:0] c_nv; wire [2:0] c_lt; wire [31:0] c_scale; wire [63:0] c_sink; wire [4:0] cs_i; wire [63:0] cs_d;
            wire [1:0] hden_v; wire [15:0] hf;
            wire [3:0] CTI = TI;
            ot_s81_su_smt #(.SM_H(SM_H), .SM_LPH(SM_LPH), .S_RD(S_RD), .WS(WS), .MUT(MUT)) u_smt (
                .clk(sk), .rst_in(rst[t]), .cfg_ti(CTI), .dn_st_i(dst[t]), .dn_kind_i(dkd[t]), .dn_jid_i(dji[t]),
                .dn_v_i(dv[t]), .dn_p_i(dd[t][0 +: NPS * 512]),
                .s_v(s_v), .p_v(p_v), .c_v(c_v), .c_nv(c_nv), .c_lt(c_lt), .c_scale(c_scale), .c_sink(c_sink),
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
            ot_hdc_delay #(.W(7 + 3 + 32 + 64 + 5 + 64), .D(SRL)) u_td (.clk(sk), .rst_n(rst[t]),
                .d({c_nv, c_lt, c_scale, c_sink, cs_i, cs_d}), .q({rc_nv, rc_lt, rc_scale, rc_sink, rcs_i, rcs_d}));
            // the stop's operand rows (spine slots 2 TI, 2 TI + 1) straight to the engines: SRL + 2 stations (the tap's
            // pin + valid registers), so they meet their valids at the engines' pin flops
            ot_hdc_delay #(.W(1024), .D(SRL + 2)) u_tdd (.clk(sk), .rst_n(rst[t]), .d(dd[t][1024 * TI +: 1024]), .q(rd_d));
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
        end else if (TK == 12) begin : g_swt
            assign o_v = 1'b0; assign o_a = 0; assign o_m = 0; assign o_d = 0;
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
            // full configuration (rate-aligned, S_RD == 2 NSWQ): two half-taps, pins registered (one cycle deeper than the
            // single tap); reduced shapes: the assembling tap
            if (S_RD == 2 * NSWQ) begin : g_sp
                ot_s81_su_swtl #(.SW_W(SW_W), .S_RD(S_RD), .NSQ(NSWQ), .NCH(SNCH)) u_swtl (
                    .clk(sk), .rst_in(rst[t]),
                    .dn_st_i(dst[t]), .dn_kind_i(dkd[t]), .dn_gsel_i(dgs[t]), .dn_fp4_i(df4[t]), .dn_jid_i(dji[t]),
                    .dn_v_i(dv[t]), .dn_d_i(dd[t][S_RD*256-1:0]), .i_f(sw_f), .e_d(sw_d[SL*256-1:0]), .e_gv(sw_gv), .e_uv(sw_uv),
                    .e_t(sw_t), .e_w(sw_w), .e_lim(sw_lim), .e_ob(sw_ob), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive),
                    .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
                ot_s81_su_swth #(.S_RD(S_RD)) u_swth (
                    .clk(sk), .dn_d_i(dd[t][S_RD*512-1:S_RD*256]), .e_d(sw_d[SL*512-1:SL*256]));
            end else begin : g_as
                ot_s81_su_swt #(.SW_W(SW_W), .S_RD(S_RD), .NSQ(NSWQ), .NCH(SNCH)) u_swt (
                    .clk(sk), .rst_in(rst[t]),
                    .dn_st_i(dst[t]), .dn_kind_i(dkd[t]), .dn_gsel_i(dgs[t]), .dn_fp4_i(df4[t]), .dn_jid_i(dji[t]),
                    .dn_v_i(dv[t]), .dn_d_i(dd[t]), .i_f(sw_f), .e_d(sw_d), .e_gv(sw_gv), .e_uv(sw_uv), .e_t(sw_t), .e_w(sw_w),
                    .e_lim(sw_lim), .e_ob(sw_ob), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy),
                    .o_rjid(o_rjid));
            end
        end else if (TK == 13) begin : g_swq
            // quant engine TI: lo = the chain heads of pass row 2 TI, hi = row 2 TI + 1 (words {bf16, 16'h0})
            wire [1023:0] x; wire [13:0] rob;
            genvar hc, hj;
            for (hc = 0; hc < 2 * SEPR; hc = hc + 1) begin : g_c
                for (hj = 0; hj < SLPE; hj = hj + 1) begin : g_j
                    assign x[32 * (SLPE * hc + hj) +: 32] =
                        {sc_d[((2 * TI * SEPR + hc) * SNPS) * 16 * SLPE + 16 * hj +: 16], 16'h0000};
                end
            end
            ot_hdc_delay #(.W(14), .D(ERS)) u_ob (.clk(sk), .rst_n(rst[t]), .d(sw_ob), .q(rob));
            localparam integer PN = TI ^ 1;
            localparam integer HL = (2 * TI * SEPR) * SNPS, HH = ((2 * TI + 1) * SEPR) * SNPS;
            wire [3:0] CB = TI;
            ot_s81_su_qbe #(.QB_NB(SW_W / 32), .NPB(NSWQ)) u_qbe (
                .clk(sk), .rst_in(rst[t]), .cfg_b(CB),
                .i_vlo(sc_v[HL]), .i_vhi(sc_v[HH]), .i_lo(x[511:0]), .i_hi(x[1023:512]), .i_tlo(sc_t[12 * HL +: 12]),
                .i_thi(sc_t[12 * HH +: 12]), .i_ob(rob), .i_f4(1'b0), .nx_i_v(snxv[PN]), .nx_i_q(snxq[PN]), .nx_i_e(snxe[PN]),
                .nx_o_v(snxv[TI]), .nx_o_q(snxq[TI]), .nx_o_e(snxe[TI]),
                .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
                .o_rdy(o_rdy), .o_rjid(o_rjid));
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
        end else if (TK == 14) begin : g_rx
            if (RXH != 0) begin : g_head
                // spine-head tile: tap = stop 0's down register, write slot merged at stop 0 (rx_*); its own stop
                // here relays the spines only
                ot_s81_su_rxt #(.S_RD(S_RD), .LM(LM), .LA(LA), .XMUT(XMUT), .QW(2)) u_rxt (
                    .clk(sk), .rst_in(rst[0]), .dn_st_i(dst[0]), .dn_kind_i(dkd[0]), .dn_jid_i(dji[0]), .dn_v_i(dv[0]),
                    .dn_d_i(dd[0]), .o_v(rx_v), .o_a(rx_a), .o_m(rx_m), .o_d(rx_d), .o_v2(rx_v2), .o_a2(rx_a2), .o_d2(rx_d2),
                    .o_fu(rx_fu), .o_fo(rx_fo),
                    .o_alive(rx_alive), .o_den(), .o_rdy(), .o_rjid());
                assign o_v = 1'b0; assign o_a = 0; assign o_m = 0; assign o_d = 0;
                assign o_fu = 1'b0; assign o_fo = 1'b0; assign o_alive = 1'b1; assign o_den = 1'b1; assign o_rdy = 1'b0;
                assign o_rjid = 8'd0;
            end else begin : g_tail
                ot_s81_su_rxt #(.S_RD(S_RD), .LM(LM), .LA(LA), .XMUT(XMUT)) u_rxt (
                    .clk(sk), .rst_in(rst[t]), .dn_st_i(dst[t]), .dn_kind_i(dkd[t]), .dn_jid_i(dji[t]), .dn_v_i(dv[t]),
                    .dn_d_i(dd[t]), .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_v2(), .o_a2(), .o_d2(), .o_fu(o_fu), .o_fo(o_fo),
                    .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
                assign rx_v2 = 1'b0; assign rx_a2 = 0; assign rx_d2 = 0;
                assign rx_v = 1'b0; assign rx_a = 0; assign rx_m = 0; assign rx_d = 0;
                assign rx_fu = 1'b0; assign rx_fo = 1'b0; assign rx_alive = 1'b1;
            end
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
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
                end else if (t == 0 && s == 0 && moe_ov) begin
                    ua_q[13:0] <= moe_or; um_q[15:0] <= 16'hffff; ud_q[511:0] <= moe_od;
                end else if (t == 0 && s == 0 && rx_v) begin
                    ua_q[13:0] <= rx_a; um_q[15:0] <= rx_m; ud_q[511:0] <= rx_d;
                end else if (t == 0 && s == 1 && rx_v2) begin
                    ua_q[27:14] <= rx_a2; um_q[31:16] <= 16'hFFFF; ud_q[1023:512] <= rx_d2;
                end else begin
                    ua_q[14 * s +: 14] <= ua[t + 1][14 * s +: 14]; um_q[16 * s +: 16] <= um[t + 1][16 * s +: 16];
                    ud_q[512 * s +: 512] <= ud[t + 1][512 * s +: 512];
                end
        end
        always @(posedge sk or negedge rst[t]) begin
            if (!rst[t]) begin uv_q <= 0; ufu_q <= 0; ufo_q <= 0; ual_q <= 0; ude_q <= 0; urd_q <= 0; urj_q <= 0; end
            else begin
                for (s = 0; s < S_WR; s = s + 1) uv_q[s] <= uv[t + 1][s] || (s >= W0 && s < W0 + WS && o_v[s - W0]) || (t == 0 && s == 0 && (rx_v || moe_ov)) || (t == 0 && s == 1 && rx_v2);
                ufu_q <= ufu[t + 1] || o_fu || (t == 0 && rx_fu); ufo_q <= ufo[t + 1] || o_fo || (t == 0 && rx_fo);
                ual_q <= ual[t + 1] && o_alive && (t != 0 || rx_alive);
                ude_q <= ude[t + 1] && o_den; urd_q <= urd[t + 1] || o_rdy; urj_q <= o_rdy ? o_rjid : urj[t + 1];
            end
        end
    end endgenerate
    assign xpv[NTL] = 1'b0; assign xpi[NTL] = 8'd0; assign xpd[NTL] = 32'd0;
endmodule
