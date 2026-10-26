`timescale 1ns/1ps
// CODEX-S81-KVQ 10-21: production D512 KV bank wiring extracted verbatim from
// dsfd_sp_su_static (KV off-spine section and TK8 taps), not new arithmetic.
// CN/IK-only branches omitted; the dispatcher accepts KV1/GK7 exclusively.
// Four tap quarters,64 KVE (last8 RoPE),4x16 half reduction,NE4/NV1/D512
// final reduction and16 quant exits. LM5/LA4 and ERL3 match current master.
// Source-only integration: native/physical qualification and calendar pending.
// RTLGAP-SUKV 10-21 (opt-in CNIK=1, default 0 = the KV1/GK7-only bank above, unchanged): the CN (kind 12, compressor
// row D512: RMSNorm -> RoPE64 -> FP4 E2M1/E4M3-16 QDQ, plus the pre-RoPE BF16 norm rows for the cmp.wk frames) and IK
// (kind 13, index key D128 zero-prefixed onto KVE48..63: RMSNorm -> RoPE64 -> FP4 E2M1/UE8M0-32 QDQ) branches of the
// hub master dsfd_sp_su_h (667449857 / eabb53e66), ported verbatim onto this bank: the SAME 64 KVE + KVT + QNH/QNR,
// ot_s81_su_ik_reduce (IK's 16-engine tree, divisor 128), ot_s81_su_cn_norm_write x16, ot_s81_su_cn_write E4M3 x16 and
// E8M0 x4.  Changes vs the hub (structural only, values identical): the rstd select is ONE registered-free mux at the
// reducer outputs (not 64 per-engine muxes on kt_mode), the mode reaches each block through a kept per-block copy
// (fanout), every CN/IK exit rides the same ERL relay as the KVQ exits, and a slot's three sources are AND-OR merged
// with a sticky collision fault (the static calendar never overlaps them; a collision is a fault, never arbitration).
module ot_s81sl_kv_bank #(
    parameter integer MUT=0,
    parameter integer CNIK=0,
    parameter integer HARD_RQ=0, // reuse exact CLOSED D512 LM5/LA4 reduce and quant masters
    parameter integer CNIK_MUT=0      // bench negative controls only (0 in every build): 1 IK applies the D512 QNR rstd
                                      // (wrong tree / divisor); 2 CN norm rows carry the neighbour block's norm
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
    wire                ks_v;                    // the rstd the engines apply: QNR (KV / CN) or, CNIK IK, the IK tree
    wire [31:0]         ks_d;
    wire                ik_f;
    wire [15:0]         cx_f;                    // CNIK: relayed CN / IK write faults (per block)
    wire [15:0]         cnr_v, cwr_v, ikr_vv;    // CNIK: relayed CN norm / CN write / IK write valids (per block)
    wire [16*14-1:0]    cnr_a, cwr_a;
    wire [16*16-1:0]    cwr_m;
    wire [16*512-1:0]   cnr_d, cwr_d;
    wire [4*14-1:0]     ikr_a;                   // IK exits by IK slot 0..3
    wire [4*16-1:0]     ikr_m;
    wire [4*512-1:0]    ikr_d;
    generate if (CNIK == 0) begin : g_cn0
        assign cx_f = 16'd0; assign cnr_v = 16'd0; assign cwr_v = 16'd0; assign ikr_vv = 16'd0;
        assign cnr_a = 0; assign cwr_a = 0; assign cwr_m = 0; assign cnr_d = 0; assign cwr_d = 0;
        assign ikr_a = 0; assign ikr_m = 0; assign ikr_d = 0;
    end endgenerate                              // CNIK != 0: every block of g_kvq drives its bit (IK slots 12..15 only)
    generate if (CNIK != 0) begin : g_iks
        wire ikr_v, ikr_f; wire [31:0] ikr_d;
        // IK's logical chunk order 0..15 maps to physical KVE48..63 (hub dsfd_sp_su_h); the zero prefix is in
        // neither tree nor the divisor.  Partials are the relayed kp (ERL after the engines), as in the hub.
        ot_s81_su_ik_reduce u_ik_reduce(.ck_half({2{sk}}),.rs_half({2{rst[0]}}),
            .ck_reduce(sk),.rs_reduce(rst[0]),.go(kt_go),.eps(kt_eps),
            .p_v(kp_v[NKE-16+:16] & {16{kt_mode==2'd2}}),.p_d(kp_d[32*(NKE-16)+:512]),
            .r_v(ikr_v),.r_d(ikr_d),.fault(ikr_f));
        assign ks_v = (kt_mode == 2'd2 && CNIK_MUT != 1) ? ikr_v : kr_v;
        assign ks_d = (kt_mode == 2'd2 && CNIK_MUT != 1) ? ikr_d : kr_d;
        assign ik_f = ikr_f;
    end else begin : g_nik
        assign ks_v = kr_v; assign ks_d = kr_d; assign ik_f = 1'b0;
    end endgenerate
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
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_rv (.clk(sk), .rst_n(rst[0]), .d(ks_v), .q(rv));
        ot_hdc_delay #(.W(32), .D(ERL)) u_rd (.clk(sk), .rst_n(rst[0]), .d(ks_d), .q(rd));
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
        if(HARD_RQ!=0)begin:g_closed
        dsfd_su_t_kvr u_kvr (
            .ck(sk), .rst(rst[0]), .i_go(go), .i_eps(eps), .p_v(hv), .p_p(hp), .p_d(hd), .p_f(hf), .r_v(kr_v),
            .r_d(kr_d), .o_f(rf));
        end else begin:g_rtl
        ot_s81_su_qnr #(.NE(NKH), .NV(1), .D(KV_N), .LM(LM), .LA(LA)) u_kvr (
            .clk(sk), .rst_in(rst[0]), .i_go(go), .i_eps(eps), .p_v(hv), .p_p(hp), .p_d(hd), .p_f(hf), .r_v(kr_v),
            .r_d(kr_d), .o_f(rf));
        end
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
        wire kv_on;
        if (CNIK != 0) begin : g_cn
            // kept per-block mode copy (one kt_mode load a block); static over a job, set at its dn_st
            wire [1:0] bm;
            ot_s81_su_qn_keep_ff #(.W(2)) u_bm (.clk(sk), .rst_n(rst[0]), .d(kt_mode), .q(bm));
            assign kv_on = (bm == 2'd0);
            wire nv; wire [13:0] na; wire [511:0] nd;
            ot_s81_su_cn_norm_write u_cn_norm_write(.clk(sk),.rst_in(rst[0]),
                .i_v(kn_v[4*kb] && bm==2'd1),.i_x(kn_d[512*((CNIK_MUT == 2) ? (kb ^ 1) : kb)+:512]),
                .i_ob(kt_nb),.i_block(CB),.o_v(nv),.o_a(na),.o_d(nd));
            wire cv, cf; wire [13:0] ca; wire [15:0] cm; wire [511:0] cd;
            ot_s81_su_cn_write #(.E4M3(1)) u_cn_write(.clk(sk),.rst_in(rst[0]),
                .i_v(rv && bm==2'd1),.i_x(ry),.i_ob(rob),.i_block(CB),
                .o_v(cv),.o_a(ca),.o_m(cm),.o_d(cd),.o_fault(cf));
            wire iv, ifl; wire [13:0] ia; wire [15:0] im; wire [511:0] id;
            if (kb >= NKQ - 4) begin : g_ik_write
                // IK block IB = kb - 12 (KVE48..63) writes slot IB: qdq row obase + IB, raw row obase + 4 + IB
                wire [3:0] IBC = kb - (NKQ - 4);
                ot_s81_su_cn_write #(.E4M3(0)) u_ik_write(.clk(sk),.rst_in(rst[0]),
                    .i_v(rv && bm==2'd2),.i_x(ry),.i_ob(rob),.i_block(IBC),
                    .o_v(iv),.o_a(ia),.o_m(im),.o_d(id),.o_fault(ifl));
            end else begin : g_ik0
                assign iv = 1'b0; assign ifl = 1'b0; assign ia = 14'd0; assign im = 16'd0; assign id = 512'd0;
            end
            // equal-depth relays to the stop (as the KVQ exits): CN norm + CN write keep slot kb, IK goes to slot kb - 12
            ot_hdc_delay #(.W(4), .D(ERL), .RESET(1)) u_xv (.clk(sk), .rst_n(rst[0]), .d({nv, cv, iv, cf | ifl}),
                .q({cnr_v[kb], cwr_v[kb], ikr_vv[kb], cx_f[kb]}));
            ot_hdc_delay #(.W(14 + 512), .D(ERL)) u_xn (.clk(sk), .rst_n(rst[0]), .d({na, nd}),
                .q({cnr_a[14 * kb +: 14], cnr_d[512 * kb +: 512]}));
            ot_hdc_delay #(.W(14 + 16 + 512), .D(ERL)) u_xc (.clk(sk), .rst_n(rst[0]), .d({ca, cm, cd}),
                .q({cwr_a[14 * kb +: 14], cwr_m[16 * kb +: 16], cwr_d[512 * kb +: 512]}));
            if (kb >= NKQ - 4) begin : g_ikr
                ot_hdc_delay #(.W(14 + 16 + 512), .D(ERL)) u_xi (.clk(sk), .rst_n(rst[0]), .d({ia, im, id}),
                    .q({ikr_a[14 * (kb - 12) +: 14], ikr_m[16 * (kb - 12) +: 16], ikr_d[512 * (kb - 12) +: 512]}));
            end
        end else begin : g_ncn
            assign kv_on = 1'b1;
        end
        wire ov, ofu, ofo, oal, ode, ord; wire [13:0] oa; wire [15:0] om; wire [511:0] od; wire [7:0] orj;
        if(HARD_RQ!=0)begin:g_closed
        dsfd_su_t_kvq u_kvq (
            .ck(sk), .rst(rst[0]), .cfg_b(CB), .i_v(rv && kv_on), .i_y(ry), .i_ob(rob), .nx_i_v(kqxv[kb ^ 1]),
            .nx_i_q(kqxq[kb ^ 1]), .nx_o_v(kqxv[kb]), .nx_o_q(kqxq[kb]), .e_o_v(kq_ev[kb]), .e_o_e(kq_ee[10 * kb +: 10]),
            .g_i_v(gv), .g_i_e(ge), .o_v(ov), .o_a(oa), .o_m(om), .o_d(od), .o_fu(ofu), .o_fo(ofo), .o_alive(oal),
            .o_den(ode), .o_rdy(ord), .o_rjid(orj));
        end else begin:g_rtl
        ot_s81_su_kvq #(.N(KV_N), .MLAT(LM)) u_kvq (
            .clk(sk), .rst_in(rst[0]), .cfg_b(CB), .i_v(rv && kv_on), .i_y(ry), .i_ob(rob), .nx_i_v(kqxv[kb ^ 1]),
            .nx_i_q(kqxq[kb ^ 1]), .nx_o_v(kqxv[kb]), .nx_o_q(kqxq[kb]), .e_o_v(kq_ev[kb]), .e_o_e(kq_ee[10 * kb +: 10]),
            .g_i_v(gv), .g_i_e(ge), .o_v(ov), .o_a(oa), .o_m(om), .o_d(od), .o_fu(ofu), .o_fo(ofo), .o_alive(oal),
            .o_den(ode), .o_rdy(ord), .o_rjid(orj));
        end
        // to the KV stop: equal-depth relays + (S_WR < NKQ, reduced shapes only) a phase of 8 cycles a slot group so
        // the engines sharing slot kb % S_WR never write in the same cycle (full shape: 0)
        localparam integer PH = ERL + 8 * (kb / S_WR);
        ot_hdc_delay #(.W(5), .D(PH), .RESET(1)) u_ov (.clk(sk), .rst_n(rst[0]), .d({ov, ofu, ofo, oal, ode}),
            .q({kq_v[kb], kq_fu[kb], kq_fo[kb], kq_al[kb], kq_de[kb]}));
        ot_hdc_delay #(.W(14 + 16 + 512), .D(PH)) u_od (.clk(sk), .rst_n(rst[0]), .d({oa, om, od}),
            .q({kq_a[14 * kb +: 14], kq_m[16 * kb +: 16], kq_d[512 * kb +: 512]}));
    end endgenerate

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
    generate if (CNIK != 0) begin : g_mrg
        // per slot: KVQ | CN norm | CN write | IK write (slot b < 4), AND-OR (one-hot by the static calendar)
        reg col;
        integer b;
        reg [15:0] mv; reg [16*14-1:0] ma; reg [16*16-1:0] mm; reg [16*512-1:0] md; reg [15:0] mc;
        always @(*) begin
            for (b = 0; b < 16; b = b + 1) begin
                mv[b] = kq_v[b] | cnr_v[b] | cwr_v[b] | ((b < 4) ? ikr_vv[12 + b] : 1'b0);
                mc[b] = (kq_v[b] + cnr_v[b] + cwr_v[b] + ((b < 4) ? ikr_vv[12 + b] : 1'b0)) > 1;
                ma[14*b+:14] = ({14{kq_v[b]}} & kq_a[14*b+:14]) | ({14{cnr_v[b]}} & cnr_a[14*b+:14]) |
                               ({14{cwr_v[b]}} & cwr_a[14*b+:14]) | ((b < 4 && ikr_vv[12 + b]) ? ikr_a[14*b+:14] : 14'd0); // selrange-ok: ikr_vv[12+b] and ikr_a[14*b+:14] used only for constant-unrolled b<4; b>=4 selects zero; RTL-SELRANGE triage ~/coord/lanes/RTL-SELRANGE.md section3, probe p1
                mm[16*b+:16] = ({16{kq_v[b]}} & kq_m[16*b+:16]) | {16{cnr_v[b]}} |
                               ({16{cwr_v[b]}} & cwr_m[16*b+:16]) | ((b < 4 && ikr_vv[12 + b]) ? ikr_m[16*b+:16] : 16'd0); // selrange-ok: ikr_vv[12+b] and ikr_m[16*b+:16] used only for constant-unrolled b<4; b>=4 selects zero; RTL-SELRANGE triage ~/coord/lanes/RTL-SELRANGE.md section3, probe p1
                md[512*b+:512] = ({512{kq_v[b]}} & kq_d[512*b+:512]) | ({512{cnr_v[b]}} & cnr_d[512*b+:512]) |
                                 ({512{cwr_v[b]}} & cwr_d[512*b+:512]) | ((b < 4 && ikr_vv[12 + b]) ? ikr_d[512*b+:512] : 512'd0); // selrange-ok: ikr_vv[12+b] and ikr_d[512*b+:512] used only for constant-unrolled b<4; b>=4 selects zero; RTL-SELRANGE triage ~/coord/lanes/RTL-SELRANGE.md section3, probe p1
            end
        end
        always @(posedge sk or negedge rst[0]) if (!rst[0]) col <= 1'b0; else col <= col | (|mc) | (|cx_f) | ik_f;
        assign wq_v = mv; assign wq_row = ma; assign wq_mask = mm; assign wq_d = md;
        assign fault = tfu|tfo|(|kq_fu)|(|kq_fo)|col;
    end else begin : g_nmrg
        assign wq_v=kq_v;
        assign wq_row=kq_a;
        assign wq_mask=kq_m;
        assign wq_d=kq_d;
        assign fault=tfu|tfo|(|kq_fu)|(|kq_fo);
    end endgenerate
    assign online=tal & (&kq_al);
    assign input_done=trd;
endmodule
