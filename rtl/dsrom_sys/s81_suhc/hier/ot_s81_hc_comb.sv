`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_comb (s81-suhc-hier-1011, comb v2 2026-10-11): the CENTRE combine region of the hierarchical S81 HC slab
// (dsfd_sp_hc HIER=1), now a WIRES-ONLY wrapper of hard tiles (the flat comb was 124k flops on one clock root;
// PHYSICAL SPEC comb v2 in el1011-s81-suhc-hier-1011.log).  Same port list and parameters as the flat comb, so the
// slab composition and the hc_gate bench are unchanged; the die places the tiles (no comb parent route).
//   ot_s81_hc_cseq    adapter + sequencer + y credit view + norm scalar tail; forward bus output flops (top row)
//   ot_s81_hc_crx     return merge + VM writer; w_w / e_w output flops (top row)
//   ot_s81_hc_cntree  the norm sum tree's final rungs + vector levels (middle row)
//   ot_s81_hc_caq x S_RT  FP8 act-quant units, hardened once and stepped (middle row)
//   ot_s81_hc_ccr     centre chain return root: capture, subtree OWN 1, valid / export pad (bottom row)
//   ot_s81_hc_cpad    centre chain pad registers: return rows, forward bus (bottom row)
//   ot_s81_hc_ccf     centre chain forward root: y slice FIFO (SRAM macros), ch_fv / ch_fd, ch_rst (bottom row)
// Every tile: own clock root sk, tile-local 2-flop reset relay, registered inputs and outputs.  The lockstep paths
// keep the flat comb's exact register counts (centre return rows / valids / exports = RP, forward pad = FP; pad
// stages moved across seams, seam flops counted); the act-quant outputs, ss -> r, ngo, faults and the done events
// gain cycles (count-based / event-based, the done still leaves after the writes).
// Under `define OT_S81_HC_COMB_HARD the tiles are instantiated with NO parameter overrides (hard views: their
// defaults are the hardened NG 256 HIER=1 configuration = this module's defaults; elaboration check below).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_comb #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_WR = 8, S_RT = 4, ML = 5, AL = 4,
    parameter integer WIN = 2, WOUT = 2, MUT = 0, AMUT = 0, RF = 1, RT = 1, RW = 2, YD = 16,
    parameter integer HALF = 0, RLY = 1,            // the chains' sub-tiles: half octets (2 a slot), RLY relays a hop
    parameter integer DW = 3 + RW, RET_EXTRA = 0,   // the write path to the pins (send + capture + relays + pin flop)
    parameter integer PIPE = 1, PIPE_PD = 40,       // ot_s81_hc_cseq: POST issue-order done (0 = return-event done)
    // CCF_BP (HC-COMB 2026-10-16, opt-in, default 0 = unchanged): 1 = CCF successor ot_s81_hc_ccf_bankpipe (7 leaf roots,
    // +2 public edges) with the forward pad trimmed by 2 (ot_s81_hc_cpad_split FWD_TRIM 2): same centre-chain cycle.
    // 2 = bankpipe WITHOUT the trim: negative control, the HC composition must FAIL (centre chain 2 edges late).
    // 3 = bankpipe PINREG 1 (every leaf pin registered, uniform +3) with the forward pad trimmed by 3 (production
    // candidate); 4 = PINREG 1 without the trim (negative control).
    parameter integer CCF_BP = 0
) (
    input  wire                 cck, crs, sk, srs,
    // centre pin tile seam
    input  wire                 n_cmd_v,
    input  wire [83:0]          n_cmd_d,
    output wire                 n_done_v,
    output wire [7:0]           n_done_tag,
    input  wire                 n_inp,
    output wire [S_RD-1:0]      n_rq_v,
    output wire [S_RD*14-1:0]   n_rq_row,
    input  wire [S_RD-1:0]      n_rs_v,
    input  wire [S_RD*512-1:0]  n_rs_d,
    output wire                 n_flt,
    output wire                 n_online,
    output wire [3:0]           n_fcode,
    input  wire                 n_yacc,
    input  wire [YS1-1:0]       n_y,
    output wire                 n_ypop,
    // west / east column root seams
    output wire [FVW-1:0]       w_fv,
    output wire [FSW-1:0]       w_fd,
    output wire [4*WSL-1:0]     w_w,
    input  wire [RVW-1:0]       w_rv,
    input  wire [RDW-1:0]       w_rd,
    input  wire [NE0*32-1:0]    w_ex,
    input  wire                 w_flt,
    output wire [FVW-1:0]       e_fv,
    output wire [FSW-1:0]       e_fd,
    output wire [4*WSL-1:0]     e_w,
    input  wire [RVW-1:0]       e_rv,
    input  wire [RDW-1:0]       e_rd,
    input  wire [NE2*32-1:0]    e_ex,
    input  wire                 e_flt,
    // centre column chain
    output wire                 ch_rst,
    output wire [FVW-1:0]       ch_fv,
    output wire [FDW-1:0]       ch_fd,
    input  wire [RVW-1:0]       ch_rv,
    input  wire [RDW-1:0]       ch_rd
);
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0;
    localparam integer FVW = S_RD + 5, RVW = S_RT + 4;
    localparam integer YW  = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FSW = O_D + S_RD * 512, FDW = O_D + FDD;
    localparam integer P_T = 0, P_I = S_RT, P_Q = P_I + 8 * S_RT, P_PI = P_Q + 16 * S_RT, P_D = P_PI + 8,
                       RDW = P_D + 512 * S_RT;
    localparam integer WSL = 1 + 14 + 16 + 512;
    localparam integer YS1 = (L1 > 0) ? L1 * GS * 32 : 1;
    localparam integer NL = 4 * NS;
    localparam integer LT = $clog2(NL);
    localparam integer L0 = NP, L2 = NP;
    localparam integer B0 = 0, B1 = NP, B2 = NP + L1;
    function automatic integer lev(input integer n);
        integer t;
        begin t = 0; while ((n >> (t + 1)) > 0) t = t + 1; lev = LT - t; end
    endfunction
    function automatic integer owner(input integer n);
        integer k, sz, s0;
        begin
            k = lev(n); sz = 1 << k; s0 = ((n << k) - NL) % NS;
            owner = 3;
            if (sz <= NS) begin
                if (L0 > 0 && s0 >= B0 && s0 + sz <= B0 + L0) owner = 0;
                else if (L1 > 0 && s0 >= B1 && s0 + sz <= B1 + L1) owner = 1;
                else if (L2 > 0 && s0 >= B2 && s0 + sz <= B2 + L2) owner = 2;
            end
        end
    endfunction
    function automatic integer expd(input integer n, input integer c);
        expd = (owner(n) == c) && (c != 3) && (n == 1 || owner(n / 2) != c);
    endfunction
    function automatic integer exidx(input integer n, input integer c);
        integer m, t;
        begin t = 0; for (m = 1; m < n; m = m + 1) t = t + expd(m, c); exidx = t; end
    endfunction
    function automatic integer necnt(input integer c);
        necnt = exidx(2 * NL, c);
    endfunction
    localparam integer NE0_ = necnt(0), NE1_ = necnt(1), NE2_ = necnt(2);
    localparam integer NE0 = (NE0_ > 0) ? NE0_ : 1, NE1 = (NE1_ > 0) ? NE1_ : 1, NE2 = (NE2_ > 0) ? NE2_ : 1;
    localparam integer NIM_ = NE0_ + NE1_ + NE2_, NIM = (NIM_ > 0) ? NIM_ : 1;
`ifdef OT_S81_HC_COMB_HARD
 `define OT_HCC_P
 `define OT_HCC_F
 `define OT_HCC_R
`ifndef SYNTHESIS
    initial if (NG != 256 || D != 5120 || NCOL != 3 || GS != 8 || S_RD != 2 || S_WR != 8 || S_RT != 4 || ML != 5 ||
                AL != 4 || MUT != 0 || AMUT != 0 || RF != 1 || RT != 1 || RW != 2 || YD != 16 || HALF != 0 ||
                RLY != 1 || DW != 3 + RW || RET_EXTRA != 0)
        $fatal(1, "ot_s81_hc_comb: OT_S81_HC_COMB_HARD needs the hardened configuration (the tiles' defaults)");
`endif
`else
 `define OT_HCC_P #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_WR(S_WR), .S_RT(S_RT), .ML(ML), .AL(AL), \
     .MUT(MUT), .AMUT(AMUT), .RF(RF), .RT(RT), .RW(RW), .YD(YD), .HALF(HALF), .RLY(RLY), .DW(DW))
 `define OT_HCC_R #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_WR(S_WR), .S_RT(S_RT), .ML(ML), .AL(AL), \
     .MUT(MUT), .AMUT(AMUT), .RF(RF), .RT(RT), .RW(RW), .YD(YD), .HALF(HALF), .RLY(RLY), .DW(DW), .RET_EXTRA(RET_EXTRA))
 `define OT_HCC_F #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_WR(S_WR), .S_RT(S_RT), .ML(ML), .AL(AL), \
     .MUT(MUT), .AMUT(AMUT), .RF(RF), .RT(RT), .RW(RW), .YD(YD), .HALF(HALF), .RLY(RLY), .DW(DW), \
     .FIFO_SLICE(512), .KEEP_POP(1), .Y_RELAY(1))
`endif
    // ---------------------------------------------------------------- seam nets (tile to tile)
    wire              ngo, t_ssv, t_flt, j_v, j_fq, j_fy, j_end, j_flt, j_civ, x_wdone, x_pob, x_f1, x_f4, c_yfl;
    wire [31:0]       t_ss;
    wire [2:0]        j_kind;
    wire [13:0]       j_base;
    wire [FVW-1:0]    c_fv, p_fv;
    wire [FSW-1:0]    c_fd, p_fd;
    wire [RDW-1:0]    r_crd, p_crd;
    wire [P_D-1:0]    o_rd;
    wire [4*(WSL-512)-1:0] w_h;
    wire [S_RT*512-1:0]    a_wd;
    wire [4*(WSL-512)-1:0] e_h;
    wire [1023:0]          e_x;
    wire [S_RT*256-1:0]    a_cq;
    wire [RVW-1:0]    r_crv;
    wire [7:0]        r_cpi;
    wire [NE1*32-1:0] r_ex1;
    wire [S_RT-1:0]   o_rv, a_vo, a_f;
    wire              o_run;
    wire [2:0]        o_kind;
    wire [S_RT*10-1:0]  a_e;
    wire [S_RT*24-1:0]  a_iq;

`ifdef OT_S81_HC_COMB_HARD
    ot_s81_hc_cseq #(.PIPE(PIPE), .PD(PIPE_PD)) u_seq (
`else
    ot_s81_hc_cseq #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_WR(S_WR), .S_RT(S_RT), .ML(ML), .AL(AL),
        .MUT(MUT), .AMUT(AMUT), .RF(RF), .RT(RT), .RW(RW), .YD(YD), .HALF(HALF), .RLY(RLY), .DW(DW),
        .PIPE(PIPE), .PD(PIPE_PD)) u_seq (
`endif
        .cck(cck), .crs(crs), .sk(sk), .srs(srs), .n_cmd_v(n_cmd_v), .n_cmd_d(n_cmd_d), .n_done_v(n_done_v),
        .n_done_tag(n_done_tag), .n_inp(n_inp), .n_rq_v(n_rq_v), .n_rq_row(n_rq_row), .n_rs_v(n_rs_v), .n_rs_d(n_rs_d),
        .n_flt(n_flt), .n_online(n_online), .n_fcode(n_fcode), .n_yacc(n_yacc), .n_ypop(n_ypop),
        .w_flt(w_flt), .e_flt(e_flt), .w_fv(w_fv), .e_fv(e_fv), .c_fv(c_fv), .w_fd(w_fd), .e_fd(e_fd), .c_fd(c_fd),
        .ngo(ngo), .t_ssv(t_ssv), .t_ss(t_ss), .t_flt(t_flt),
        .j_v(j_v), .kind(j_kind), .base(j_base), .f_q(j_fq), .f_y(j_fy), .j_end(j_end), .fault(j_flt), .j_civ(j_civ),
        .x_wdone(x_wdone), .x_pob(x_pob), .x_f1(x_f1), .x_f4(x_f4), .c_yfl(c_yfl));

    ot_s81_hc_crx `OT_HCC_P u_rx (
        .sk(sk), .srs(srs), .w_rv(w_rv), .e_rv(e_rv), .w_rd(w_rd[P_D-1:0]), .e_rd(e_rd[P_D-1:0]), .c_rv(r_crv),
        .c_rd(p_crd[P_D-1:0]),
        .j_v(j_v), .j_kind(j_kind), .j_base(j_base), .j_fq(j_fq), .j_fy(j_fy), .j_end(j_end), .j_flt(j_flt),
        .j_civ(j_civ), .a_vo(a_vo), .a_f(a_f), .a_e(a_e), .a_iq(a_iq),
        .o_rv(o_rv), .o_rd(o_rd), .o_run(o_run), .o_kind(o_kind), .w_h(w_h), .e_h(e_h), .e_x(e_x),
        .x_wdone(x_wdone), .x_pob(x_pob), .x_f1(x_f1), .x_f4(x_f4));

    genvar u;
    generate for (u = 0; u < S_RT; u = u + 1) begin : g_aq
        ot_s81_hc_caq u_caq (.sk(sk), .srs(srs), .run(o_run), .kind(o_kind), .rv_u(o_rv[u]), .t_u(o_rd[P_T + u]),
            .w_d(w_rd[P_D + 512 * u +: 512]), .e_d(e_rd[P_D + 512 * u +: 512]),
            .c_d((L1 > 0) ? p_crd[P_D + 512 * u +: 512] : 512'd0), .wd(a_wd[512 * u +: 512]), .odd(u % 2 == 1),
            .cq(a_cq[256 * u +: 256]),
            .iq({o_rd[P_I + 8 * u +: 8], o_rd[P_Q + 16 * u +: 16]}),
            .vo(a_vo[u]), .e(a_e[10 * u +: 10]), .f(a_f[u]), .iqo(a_iq[24 * u +: 24]));
        assign w_w[WSL * u +: WSL] = {a_wd[512 * u +: 512], w_h[(WSL - 512) * u +: WSL - 512]};
    end endgenerate
    assign e_w = {e_x[512 +: 512], e_h[3 * (WSL - 512) +: WSL - 512], e_x[0 +: 512], e_h[2 * (WSL - 512) +: WSL - 512],
                  a_cq[768 +: 256], a_cq[512 +: 256], e_h[(WSL - 512) +: WSL - 512],
                  a_cq[256 +: 256], a_cq[0 +: 256], e_h[0 +: WSL - 512]};

    ot_s81_hc_cntree `OT_HCC_P u_nt (
        .sk(sk), .srs(srs), .w_rvt(w_rv[S_RT]), .e_rvt(e_rv[S_RT]), .w_pi(w_rd[P_PI +: 8]), .e_pi(e_rd[P_PI +: 8]),
        .w_ex(w_ex), .e_ex(e_ex), .c_rvt(r_crv[S_RT]), .c_pi(r_cpi), .c_ex(r_ex1), .ngo_i(ngo),
        .ss_v(t_ssv), .ss(t_ss), .tflt(t_flt));

    ot_s81_hc_ccr_align `OT_HCC_R u_cr (
        .sk(sk), .srs(srs), .ch_rv(ch_rv), .ch_rd(ch_rd), .crd_o(r_crd), .crv_o(r_crv), .cpi_o(r_cpi), .ex1_o(r_ex1));

    generate if (CCF_BP == 0) begin : g_cf_old
    ot_s81_hc_cpad_split `OT_HCC_R u_pd (
        .sk(sk), .srs(srs), .crd_i(r_crd), .crd_o(p_crd), .fv_i(c_fv), .fd_i(c_fd), .fv_o(p_fv), .fd_o(p_fd));

    ot_s81_hc_ccf `OT_HCC_F u_cf (
        .sk(sk), .srs(srs), .fv_i(p_fv), .fd_i(p_fd), .n_yacc(n_yacc), .n_y(n_y), .ch_rst(ch_rst), .ch_fv(ch_fv),
        .ch_fd(ch_fd), .yfl(c_yfl));
    end else begin : g_cf_bp
    ot_s81_hc_cpad_split #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_WR(S_WR), .S_RT(S_RT), .ML(ML), .AL(AL),
        .MUT(MUT), .AMUT(AMUT), .RF(RF), .RT(RT), .RW(RW), .YD(YD), .HALF(HALF), .RLY(RLY), .DW(DW), .RET_EXTRA(RET_EXTRA),
        .FWD_TRIM(CCF_BP == 1 ? 2 : CCF_BP == 3 ? 3 : 0)) u_pd (
        .sk(sk), .srs(srs), .crd_i(r_crd), .crd_o(p_crd), .fv_i(c_fv), .fd_i(c_fd), .fv_o(p_fv), .fd_o(p_fd));

    ot_s81_hc_ccf_bankpipe #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_WR(S_WR), .S_RT(S_RT), .ML(ML), .AL(AL),
        .MUT(MUT), .AMUT(AMUT), .RF(RF), .RT(RT), .RW(RW), .YD(YD), .HALF(HALF), .RLY(RLY), .DW(DW),
        .FIFO_SLICE(512), .KEEP_POP(1), .Y_RELAY(1), .PINREG(CCF_BP >= 3)) u_cf (
        .sk_n(sk), .sk_s(sk), .bank_ck({5{sk}}), .srs(srs), .fv_i(p_fv), .fd_i(p_fd), .n_yacc(n_yacc), .n_y(n_y),
        .ch_rst(ch_rst), .ch_fv(ch_fv), .ch_fd(ch_fd), .yfl(c_yfl));
    end endgenerate
`ifndef SYNTHESIS
    // bench observability (dsfd_sp_hc reads u_cb.e_v / e_r / e_d: tb job start cycles)
    wire        e_v = u_seq.e_v, e_r = u_seq.e_r;
    wire [83:0] e_d = u_seq.e_d;
`endif
`undef OT_HCC_P
`undef OT_HCC_F
endmodule
