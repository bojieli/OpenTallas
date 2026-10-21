`timescale 1ns/1ps
// CODEX-S81-KVQ 10-21: production D512 KV bank wiring extracted verbatim from
// dsfd_sp_su_static (KV off-spine section and TK8 taps), not new arithmetic.
// CN/IK-only branches omitted; the dispatcher accepts KV1/GK7 exclusively.
// Four tap quarters,64 KVE (last8 RoPE),4x16 half reduction,NE4/NV1/D512
// final reduction and16 quant exits. LM5/LA4 and ERL3 match current master.
// Source-only integration: native/physical qualification and calendar pending.
module ot_s81sl_kv_bank #(
    parameter integer MUT=0
)(
    input wire sk, rst_n,
    input wire dn_st, input wire [3:0] dn_kind,
    input wire [1:0] dn_gsel, input wire [7:0] dn_jid,
    input wire [15:0] dn_v, input wire [8191:0] dn_d,
    output wire [15:0] wq_v, output wire [223:0] wq_row,
    output wire [255:0] wq_mask, output wire [8191:0] wq_d,
    output wire fault, online, input_done
);
    localparam integer KV_N=512,S_RD=16,S_WR=16,LM=5,LA=4,NKE=64,NKQ=16,ERL=3;
    wire [0:0] rst={rst_n};
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
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_rv (.clk(sk), .rst_n(rst[0]), .d(kr_v), .q(rv));
        ot_hdc_delay #(.W(32), .D(ERL)) u_rd (.clk(sk), .rst_n(rst[0]), .d(kr_d), .q(rd));
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
        ot_s81_su_kvq #(.N(KV_N), .MLAT(LM)) u_kvq (
            .clk(sk), .rst_in(rst[0]), .cfg_b(CB), .i_v(rv), .i_y(ry), .i_ob(rob), .nx_i_v(kqxv[kb ^ 1]),
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

    wire tfu,tfo,tal,tde,trd; wire [7:0] trj;
            // four data quarters, identical control; quarter 0 carries the job fields, the status and the faults
            wire tfu, tfo, tal, tde, trd; wire [7:0] trj;
            genvar u;
            for (u = 0; u < 4; u = u + 1) begin : g_u
                wire [S_RD*128-1:0] dq;
                genvar s2;
                for (s2 = 0; s2 < S_RD; s2 = s2 + 1) begin : g_s
                    assign dq[128 * s2 +: 128] = dn_d[512 * s2 + 128 * u +: 128];
                end
                wire ugk, ugo, ufu, ufo, ual, ude, urd; wire [1:0] ugr, ugw, umode; wire [13:0] uob, unb; wire [31:0] uep; wire [7:0] urj;
                ot_s81_su_kvt #(.N(KV_N), .S_RD(S_RD), .NFI(NKE + 1), .MUT(MUT)) u_kvt (
                    .clk(sk), .rst_in(rst[0]),
                    .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_gsel_i(dn_gsel), .dn_jid_i(dn_jid), .dn_v_i(dn_v), .dn_d_i(dq),
                    .i_f(u == 0 ? kv_f : {(NKE + 1){1'b0}}), .e_v(kt_v[u]), .e_d(kt_d[u]), .e_gk(ugk), .e_gr(ugr),
                    .e_gw(ugw), .e_go(ugo), .e_mode(umode), .e_ob(uob), .e_nb(unb), .e_eps(uep), .e_cs(kt_cs[u]), .o_fu(ufu), .o_fo(ufo),
                    .o_alive(ual), .o_den(ude), .o_rdy(urd), .o_rjid(urj));
                if (u == 0) begin : g_u0
                    assign kt_gk = ugk; assign kt_gr = ugr; assign kt_gw = ugw; assign kt_go = ugo; assign kt_ob = uob;
                    assign kt_eps = uep; assign kt_mode=umode; assign kt_nb=unb;
                    assign tfu = ufu; assign tfo = ufo; assign tal = ual; assign tde = ude; assign trd = urd; assign trj = urj;
                end
            end

    // The per-engine source output streams remain separate: never OR simultaneous
    // masked exponent fragments or introduce a ready/credit handshake here.
    assign wq_v=kq_v;
    assign wq_row=kq_a;
    assign wq_mask=kq_m;
    assign wq_d=kq_d;
    assign fault=tfu|tfo|(|kq_fu)|(|kq_fo);
    assign online=tal & (&kq_al);
    assign input_done=trd;
endmodule
