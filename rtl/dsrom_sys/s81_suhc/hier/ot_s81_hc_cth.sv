`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_cth (el1011-s81hc-ctile, 2026-10-12): the HALF = 1 column sub-tile of the HC slab (dsfd_sp_hc HIER=2),
// split into hard tiles of <= ~15k clock sinks each.  Cycle-for-cycle the same pins and bus timing as
// ot_s81_hc_ctile #(.HALF(1)) (that module's header holds the protocol); this file only moves the logic:
//   ctf   forward bus: reset relay, fv / fd pin flops, y-shift register, RLY relay, out flops (the 4 forward hops);
//         exports its pin flops (fv, fd control + slot data) to the other tiles (registered seam).
//   ctn   x4, one per norm bank j (an h row's bank is row % 4): the bank's resident h rows (2 slots x NV), its 4 lanes'
//         gain slices, hc_pre mix -> square -> chunk chain (+ the HALF carry), x wait line, scale, y; registered read
//         ports for hc_post (hpr) and the return's h rows (hrq, read one stage ahead).  bank / tid are strap PINS
//         captured in flops (one hardened master serves all 4 banks of every sub-tile; no strap fans out).
//   ctp   hc_post (4 groups) + coefficient words; picks the bank read (OR of the 4 zero-gated hpr) into in_r.
//   ctr   return bus: rv / rd pin flops, a stage for the far tile's originated slots, the merge stage (y rows from
//         ybuf, partial packet from psb, h rows from the banks' hrq), out flops.  The merge sits one stage later than
//         in ot_s81_hc_ctile and the relay one stage earlier (needs RLY >= 2): same 2 + RLY registers a hop, and every
//         merged source is one register later (faults / hc_post flags registered at their tile), so rv / rd are
//         cycle-identical.
// Every signal crossing between these tiles leaves a flop.  ctq: the norm/scale timing sequencer, replicated in ctn
// and ctr (a few hundred flops each) instead of a cross-tile strobe tree.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_cth #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, WIN = 2, WOUT = 2, ML = 5, AL = 4,
    parameter integer RLY = 2
) (
    input  wire                       clk,
    input  wire                       rst_in,
    output wire                       rst_out,
    input  wire [7:0]                 tid,
    input  wire                       last,
    input  wire [S_RD+4:0]            fv_in,
    input  wire [FDW-1:0]             fd_in,
    output wire [S_RD+4:0]            fv_out,
    output wire [FDW-1:0]             fd_out,
    input  wire [S_RT+3:0]            rv_in,
    input  wire [RDW-1:0]             rd_in,
    output wire [S_RT+3:0]            rv_out,
    output wire [RDW-1:0]             rd_out,
    output wire [127:0]               cy_out,
    input  wire [127:0]               cy_in
);
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, YW = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FDW = O_D + FDD, FXW = O_D + S_RD * 512;
    localparam integer RDW = S_RT + 8 * S_RT + 16 * S_RT + 8 + 512 * S_RT;
`ifndef SYNTHESIS
    initial if (RLY < 2 || GS != 8) $fatal(1, "ot_s81_hc_cth: RLY >= 2 (the return merge takes a relay stage), GS 8");
`endif
    wire [S_RD+4:0] fv;
    wire [FXW-1:0]  fdx;
    ot_s81_hc_ctf #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .RLY(RLY)) u_f (
        .clk(clk), .rst_in(rst_in), .rst_out(rst_out), .fv_in(fv_in), .fd_in(fd_in), .fv_out(fv_out), .fd_out(fd_out),
        .fv(fv), .fdx(fdx));
    wire [S_RT-1:0]     rq_v, rq_t;
    wire [16*S_RT-1:0]  rq_q;
    wire                hs_run;
    wire [15:0]         hs_c;
    wire [4*256-1:0]    hpr;
    wire [4*256*S_RT-1:0] hrq;
    wire [4*64-1:0]     yb;
    wire [4*32-1:0]     cs;
    wire [3:0]          nflt;
    wire                hov, pwb, phs;
    wire [15:0]         pob;
    wire [255:0]        hpo;
    wire                hov_d, hnz_d, pflt_d;
    genvar j;
    generate for (j = 0; j < 4; j = j + 1) begin : g_n
        ot_s81_hc_ctn #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY)) u_n (
            .clk(clk), .rst_in(rst_in), .tid(tid), .bank(j[1:0]), .last(last), .fv(fv), .fdx(fdx),
            .wb_v(hov), .wb_en(pwb), .wb_hs(phs), .wb_ob(pob), .wb_d(hpo),
            .rq_q(rq_q), .hs_run(hs_run), .hs_c(hs_c),
            .hpr(hpr[256 * j +: 256]), .hrq(hrq[256 * S_RT * j +: 256 * S_RT]),
            .cy_in(cy_in[32 * j +: 32]), .cy_out(cy_out[32 * j +: 32]), .yb(yb[64 * j +: 64]), .cs(cs[32 * j +: 32]),
            .flt(nflt[j]));
    end endgenerate
    ot_s81_hc_ctp #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL)) u_p (
        .clk(clk), .rst_in(rst_in), .fv(fv), .fdx(fdx), .hpr(hpr), .hov(hov), .pwb(pwb), .phs(phs), .pob(pob), .hpo(hpo),
        .hov_d(hov_d), .hnz_d(hnz_d), .pflt_d(pflt_d));
    ot_s81_hc_ctr #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY)) u_r (
        .clk(clk), .rst_in(rst_in), .tid(tid), .last(last), .fv(fv), .fdx(fdx), .rv_in(rv_in), .rd_in(rd_in),
        .rv_out(rv_out), .rd_out(rd_out), .rq_q(rq_q), .hs_run(hs_run), .hs_c(hs_c), .hrq(hrq), .yb(yb), .cs(cs),
        .nflt(nflt), .hov_d(hov_d), .hnz_d(hnz_d), .pflt_d(pflt_d));
endmodule

// ------------------------------------------------------------------------------------------------ forward bus tile
module ot_s81_hc_ctf #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, RLY = 2
) (
    input  wire               clk,
    input  wire               rst_in,
    output wire               rst_out,
    input  wire [S_RD+4:0]    fv_in,
    input  wire [FDW-1:0]     fd_in,
    output reg  [S_RD+4:0]    fv_out,
    output reg  [FDW-1:0]     fd_out,
    output reg  [S_RD+4:0]    fv,                    // pin flops, exported
    output wire [FXW-1:0]     fdx
);
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, YW = NP * GS * 32, GT = GS / 2;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FDW = O_D + FDD, FXW = O_D + S_RD * 512;
    reg [1:0] rr;
    always @(posedge clk) rr <= {rr[0], rst_in};
    wire rst_n = rr[1];
    assign rst_out = rr[1];
    reg [S_RD+4:0] fvm;
    reg [FDW-1:0]  fd, fdm;
    wire [S_RD+4:0] fvm_d;
    wire [FDW-1:0]  fdm_d;
    assign fdx = fd[FXW-1:0];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fv <= 0; fvm <= 0; fv_out <= 0; end
        else begin fv <= fv_in; fvm <= fv; fv_out <= fvm_d; end
    always @(posedge clk) begin
        fd <= fd_in;
        fdm <= fd;
        if (fv[S_RD]) fdm[O_D +: YW] <= fd[O_D +: YW] >> (GT * 32);           // y beat: next tile's slice to 0
        fd_out <= fdm_d;
    end
    ot_hdc_delay #(.W(S_RD + 5), .D(RLY - 1), .RESET(1)) u_fvr (.clk(clk), .rst_n(rst_n), .d(fvm), .q(fvm_d));
    ot_hdc_delay #(.W(FDW), .D(RLY - 1)) u_fdr (.clk(clk), .rst_n(rst_n), .d(fdm), .q(fdm_d));
endmodule

// ------------------------------------------------------------------------------------------------ norm/scale sequencer
module ot_s81_hc_ctq #(
    parameter integer NG = 256, D = 5120, S_RD = 2, ML = 5, AL = 4
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [S_RD+4:0] fv,
    input  wire [FXW-1:0]  fdx,
    output reg             n_hs, n_cs,
    output reg  [1:0]      n_gs,
    output reg             mx_v,
    output wire            x_v,
    output wire [7:0]      xi,
    output wire [DS:0]     vs,
    output wire [7:0]      si,
    output reg  [31:0]     rh,
    output reg  [7:0]      sc_i,
    output reg             b_v,
    output wire [DY:0]     vy,
    output wire [7:0]      wi,
    output wire [7:0]      yi
);
    localparam integer O_NG = 5 + S_RD * 16 + 20, O_NV = O_NG + 6, O_R = O_NV + 8, O_D = O_R + 32 + 1;
    localparam integer FXW = O_D + S_RD * 512;
    localparam integer N = 4 * NG, NV = D / N, LM = ML, LA = AL;
    localparam integer DM = LM + 3 * LA + 1, DS = LM + 7 * LA, DY = 2 * LM + 1;
    wire ng_v = fv[S_RD+1], nv_v = fv[S_RD+2], r_v = fv[S_RD+3];
    always @(posedge clk) if (ng_v) begin n_hs <= fdx[O_NG]; n_cs <= fdx[O_NG + 1]; n_gs <= fdx[O_NG + 2 +: 2]; end
    reg [7:0] mx_i;
    always @(posedge clk or negedge rst_n) if (!rst_n) mx_v <= 1'b0; else mx_v <= nv_v;
    always @(posedge clk) if (nv_v) mx_i <= fdx[O_NV +: 8];
    wire [DM:0] vm;
    ot_hdc_vline #(.D(DM)) u_vm (.clk(clk), .rst_n(rst_n), .v(mx_v), .vd(vm));
    ot_hdc_delay #(.W(8), .D(DM)) u_xi (.clk(clk), .rst_n(rst_n), .d(mx_i), .q(xi));
    assign x_v = vm[DM];
    ot_hdc_vline #(.D(DS)) u_vs (.clk(clk), .rst_n(rst_n), .v(x_v), .vd(vs));
    ot_hdc_delay #(.W(8), .D(DS)) u_si (.clk(clk), .rst_n(rst_n), .d(xi), .q(si));
    reg sc_run;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin sc_run <= 1'b0; sc_i <= 8'd0; end
        else if (r_v) begin sc_run <= 1'b1; sc_i <= 8'd0; end
        else if (sc_run) begin if (sc_i == NV - 1) sc_run <= 1'b0; sc_i <= sc_i + 8'd1; end
    always @(posedge clk) if (r_v) rh <= fdx[O_R +: 32];
    always @(posedge clk or negedge rst_n) if (!rst_n) b_v <= 1'b0; else b_v <= sc_run;
    ot_hdc_vline #(.D(DY)) u_vy (.clk(clk), .rst_n(rst_n), .v(b_v), .vd(vy));
    ot_hdc_delay #(.W(8), .D(LM)) u_wi (.clk(clk), .rst_n(rst_n), .d(sc_i), .q(wi));
    reg [7:0] bi;
    always @(posedge clk) bi <= sc_i;
    ot_hdc_delay #(.W(8), .D(DY)) u_yi (.clk(clk), .rst_n(rst_n), .d(bi), .q(yi));
endmodule

// ------------------------------------------------------------------------------------------------ norm bank tile
module ot_s81_hc_ctn #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, RLY = 2
) (
    input  wire                  clk,
    input  wire                  rst_in,
    input  wire [7:0]            tid,                 // strap pins, captured in flops
    input  wire [1:0]            bank,
    input  wire                  last,
    input  wire [S_RD+4:0]       fv,
    input  wire [FXW-1:0]        fdx,
    input  wire                  wb_v, wb_en, wb_hs,  // hc_post write back (ctp flops)
    input  wire [15:0]           wb_ob,
    input  wire [255:0]          wb_d,                // hc_post outputs, BF16 halves (16 x 16 b)
    input  wire [16*S_RT-1:0]    rq_q,                // return pin flops (ctr): row field
    input  wire                  hs_run,
    input  wire [15:0]           hs_c,
    output reg  [255:0]          hpr,                 // hc_post row read (zero unless this bank)
    output reg  [256*S_RT-1:0]   hrq,                 // return h row reads (zero unless this bank)
    input  wire [31:0]           cy_in,
    output reg  [31:0]           cy_out,
    output wire [63:0]           yb,                  // 4 lanes' y (BF16)
    output wire [31:0]           cs,                  // this bank's chunk sum
    output reg                   flt
);
    localparam integer O_RK = 0, O_RS = 2, O_RG = 3, O_RC = 5, O_PB = O_RC + S_RD * 16, O_NG = O_PB + 20,
                       O_NV = O_NG + 6, O_R = O_NV + 8, O_HS = O_R + 32, O_D = O_HS + 1, FXW = O_D + S_RD * 512;
    localparam integer GT = GS / 2, N = 4 * NG, NR = D / NG, NV = D / N, PPR = NG / 8, LM = ML, LA = AL;
    localparam integer DS = LM + 7 * LA, DY = 2 * LM + 1;
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] s;
        begin s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]}; bf16 = {s[31:16], 16'd0}; end
    endfunction
    reg [1:0] rr;
    always @(posedge clk) rr <= {rr[0], rst_in};
    wire rst_n = rr[1];
    reg [7:0] tq;
    reg [1:0] bq;
    reg       lq, hs_sl;
    reg [3:0] farq;                                      // one 'far half' flop per chunk adder (no strap fanout)
    always @(posedge clk) begin tq <= tid; bq <= bank; lq <= last; farq <= {4{tid[0]}}; end

    wire [S_RD-1:0] rd_v = fv[S_RD-1:0];
    wire pb_v = fv[S_RD], hs_v = fv[S_RD+4];
    wire [1:0] rd_k = fdx[O_RK +: 2];
    wire       rd_s = fdx[O_RS];
    wire [1:0] rd_g = fdx[O_RG +: 2];
    wire       pb_hs = fdx[O_PB + 2];
    wire [15:0] pb_b = fdx[O_PB + 4 +: 16];
    always @(posedge clk) if (hs_v) hs_sl <= fdx[O_HS];

    // resident state of bank bq: h rows (slot x NV, 4 groups x 4 copies BF16), the 4 lanes' gain words, pre coefs
    reg [255:0]     hb [0:2*NV-1];
    reg [127:0]     gt [0:4*NV-1];
    reg [127:0]     cf_pre [0:1];
    integer s, k;
    always @(posedge clk) begin
        for (s = 0; s < S_RD; s = s + 1)
            if (rd_v[s]) begin : one
                reg [15:0] c, g0, l0, rb, g;
                c = fdx[O_RC + 16 * s +: 16];
                if (rd_k == 2'd0) begin
                    rb = c / PPR; g0 = c % PPR;
                    for (k = 0; k < 8; k = k + 1)
                        if (g0 * (8 / GT) + k / GT == tq && rb % 4 == bq)
                            hb[rd_s * NV + rb / 4][64 * (k % GT) +: 64] <= fdx[O_D + 512 * s + 64 * k +: 64];
                end else if (rd_k == 2'd1) begin
                    l0 = (16 * c) % N;
                    g = (l0 % NG) / GT;
                    for (k = 0; k < 16; k = k + 1)
                        if (g + k / GT == tq && l0 / NG == bq)
                            gt[rd_g * NV + (16 * c) / N][32 * (k % GT) +: 32] <= fdx[O_D + 512 * s + 32 * k +: 32];
                end else if (rd_k == 2'd2) begin
                    if (c != 0) cf_pre[rd_s] <= fdx[O_D + 512 * s +: 128];
                end
            end
        if (wb_v && wb_en && wb_ob % 4 == bq) hb[wb_hs * NV + wb_ob / 4] <= wb_d;
    end
    // registered read ports: hc_post row (on pb_v) and the return's h rows (one stage ahead of the merge)
    always @(posedge clk) if (pb_v) hpr <= (pb_b % 4 == bq) ? hb[pb_hs * NV + pb_b / 4] : 256'd0;
    always @(posedge clk) begin : rdh
        reg [15:0] qx, b;
        for (s = 0; s < S_RT; s = s + 1) begin
            qx = lq ? hs_c + s : rq_q[16 * s +: 16];
            b = (8 * qx) / NG;
            hrq[256 * s +: 256] <= (b % 4 == bq) ? hb[hs_sl * NV + b / 4] : 256'd0;
        end
    end

    // norm lanes gg = 0..3 (slab lane bq * GT + gg)
    wire n_hs, n_cs, mx_v, x_v, b_v;
    wire [1:0] n_gs;
    wire [7:0] xi, si, sc_i, wi, yi;
    wire [DS:0] vs;
    wire [DY:0] vy;
    wire [31:0] rh;
    ot_s81_hc_ctq #(.NG(NG), .D(D), .S_RD(S_RD), .ML(ML), .AL(AL)) u_q (.clk(clk), .rst_n(rst_n), .fv(fv), .fdx(fdx),
        .n_hs(n_hs), .n_cs(n_cs), .n_gs(n_gs), .mx_v(mx_v), .x_v(x_v), .xi(xi), .vs(vs), .si(si), .rh(rh), .sc_i(sc_i),
        .b_v(b_v), .vy(vy), .wi(wi), .yi(yi));
    wire nv_v = fv[S_RD+2];
    wire [7:0] nv_i = fdx[O_NV +: 8];
    reg [255:0] mx_h;                                    // the bank's row of the vector (groups x copies)
    always @(posedge clk) if (nv_v) mx_h <= hb[n_hs * NV + nv_i];
    wire [3:0]     lf;
    wire [4*32-1:0] sq;
    genvar l, kk;
    generate
        for (l = 0; l < GT; l = l + 1) begin : g_lane
            wire [31:0] xl, p, qq;
            wire [3:0] f;
            ot_dsrom_su_norm_mix #(.LM(LM), .LA(LA)) u_mix (.clk(clk), .rst_n(rst_n), .v(mx_v),
                .h0({mx_h[16 * (4 * l + 0) +: 16], 16'h0000}), .h1({mx_h[16 * (4 * l + 1) +: 16], 16'h0000}),
                .h2({mx_h[16 * (4 * l + 2) +: 16], 16'h0000}), .h3({mx_h[16 * (4 * l + 3) +: 16], 16'h0000}),
                .pre(cf_pre[n_cs]), .x(xl), .fault(f[0]));
            reg [31:0] xb [0:NV-1];
            reg [31:0] xo_r, wo_r, yr;
            always @(posedge clk) if (x_v) xb[xi] <= xl;
            always @(posedge clk) xo_r <= xb[sc_i];
            always @(posedge clk) wo_r <= gt[n_gs * NV + wi][32 * l +: 32];
            ot_hdc_qmul_lat #(LM) u_sq (clk, rst_n, x_v, xl, xl, sq[l * 32 +: 32], f[1]);
            ot_hdc_qmul_lat #(LM) u_xr (clk, rst_n, b_v, xo_r, rh, p, f[2]);
            ot_hdc_qmul_lat #(LM) u_w  (clk, rst_n, vy[LM], wo_r, p, qq, f[3]);
            always @(posedge clk) yr <= bf16(qq);
            assign yb[16 * l +: 16] = yr[31:16];
            assign lf[l] = |f;
        end
        // the octet chunk chain across the HALF seam (ot_s81_hc_ctile g_half, bank bq's chunk)
        wire [31:0]  cyd_b;
        reg  [31:0]  cyq;
        always @(posedge clk) cyq <= cy_in;
        ot_hdc_delay #(.W(32), .D(RLY)) u_cy (.clk(clk), .rst_n(rst_n), .d(cyq), .q(cyd_b));
        wire [31:0] acc [0:4];
        wire [4:0]  cf;
        assign cf[0] = 1'b0;
        assign acc[0] = farq[0] ? cyd_b : sq[0 +: 32];
        for (kk = 0; kk < 4; kk = kk + 1) begin : g_j
            wire [31:0] dn, df;
            if (kk < 3) begin : g_n
                ot_hdc_delay #(.W(32), .D(LA * kk)) u_dn (.clk(clk), .rst_n(rst_n), .d(sq[(kk + 1) * 32 +: 32]), .q(dn));
            end else begin : g_nn
                assign dn = 32'd0;
            end
            ot_hdc_delay #(.W(32), .D(LA * (kk + 3))) u_df (.clk(clk), .rst_n(rst_n), .d(sq[kk * 32 +: 32]), .q(df));
            wire fire = farq[kk] ? vs[LM + LA * (kk + 3)] : (kk < 3 ? vs[LM + LA * kk] : 1'b0);
            ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, fire, acc[kk], farq[kk] ? df : dn, acc[kk + 1], cf[kk + 1]);
        end
        assign cs = acc[4];
        always @(posedge clk) cy_out <= acc[3];
    endgenerate
    always @(posedge clk or negedge rst_n) if (!rst_n) flt <= 1'b0; else flt <= (|lf) | (|cf);
endmodule

// ------------------------------------------------------------------------------------------------ hc_post tile
module ot_s81_hc_ctp #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, WIN = 2, WOUT = 2, ML = 5, AL = 4
) (
    input  wire                clk,
    input  wire                rst_in,
    input  wire [S_RD+4:0]     fv,
    input  wire [FXW-1:0]      fdx,
    input  wire [4*256-1:0]    hpr,                  // the 4 banks' zero-gated row reads
    output wire                hov,                  // hc_post out valid (hcpost output flop)
    output reg                 pwb, phs,
    output reg  [15:0]         pob,
    output wire [255:0]        hpo,
    output reg                 hov_d, hnz_d, pflt_d  // return-bus flags, one register later (ctr merges a stage later)
);
    localparam integer O_RK = 0, O_RS = 2, O_RC = 5, O_PB = O_RC + S_RD * 16, O_D = O_PB + 20 + 6 + 8 + 32 + 1;
    localparam integer FXW = O_D + S_RD * 512, GT = GS / 2;
    reg [1:0] rr;
    always @(posedge clk) rr <= {rr[0], rst_in};
    wire rst_n = rr[1];
    wire [S_RD-1:0] rd_v = fv[S_RD-1:0];
    wire pb_v = fv[S_RD];
    wire [1:0] rd_k = fdx[O_RK +: 2];
    wire       rd_s = fdx[O_RS];
    wire pb_go = fdx[O_PB], pb_wb = fdx[O_PB + 1], pb_hs = fdx[O_PB + 2], pb_cs = fdx[O_PB + 3];
    reg [16*32-1:0] cf_comb [0:1];
    reg [4*32-1:0]  cf_post [0:1];
    integer s, q;
    always @(posedge clk)
        for (s = 0; s < S_RD; s = s + 1)
            if (rd_v[s] && rd_k == 2'd2) begin
                if (fdx[O_RC + 16 * s +: 16] == 16'd0) cf_comb[rd_s] <= fdx[O_D + 512 * s +: 512];
                else cf_post[rd_s] <= fdx[O_D + 512 * s + 128 +: 128];
            end
    reg               hp_go, hp_in_v;
    reg [GT*32-1:0]   hp_y;
    reg [16*32-1:0]   hp_comb;
    reg [4*32-1:0]    hp_post;
    wire [255:0]      hr = hpr[0 +: 256] | hpr[256 +: 256] | hpr[512 +: 256] | hpr[768 +: 256];
    reg  [GT*4*32-1:0] hp_r;
    always @(*) for (q = 0; q < 4 * GT; q = q + 1) hp_r[32 * q +: 32] = {hr[16 * q +: 16], 16'h0000};
    wire              hp_fault;
    wire [GT*4*32-1:0] hp_out;
    ot_dsrom_su_hcpost #(.NG(GT), .WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL)) u_post (
        .clk(clk), .rst_n(rst_n), .go(hp_go), .comb(hp_comb), .post(hp_post), .in_v(hp_in_v), .in_r(hp_r), .in_y(hp_y),
        .out_v(hov), .out_d(hp_out), .fault(hp_fault));
    always @(posedge clk or negedge rst_n) if (!rst_n) hp_in_v <= 1'b0; else hp_in_v <= pb_v;
    always @(posedge clk) begin
        hp_go <= pb_v && pb_go;
        if (pb_v) begin
            hp_y <= fdx[O_D +: GT * 32]; hp_comb <= cf_comb[pb_cs]; hp_post <= cf_post[pb_cs];
            if (pb_go) begin pwb <= pb_wb; phs <= pb_hs; pob <= 16'd0; end
        end
        if (hov) pob <= pob + 16'd1;
    end
    genvar g;
    generate for (g = 0; g < 4 * GT; g = g + 1) begin : g_o
        assign hpo[16 * g +: 16] = hp_out[32 * g + 16 +: 16];
    end endgenerate
    reg nz;
    always @(*) begin nz = 1'b0; for (q = 0; q < 4 * GT; q = q + 1) nz = nz | (|hp_out[32 * q +: 16]); end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin hov_d <= 1'b0; hnz_d <= 1'b0; pflt_d <= 1'b0; end
        else begin hov_d <= hov; hnz_d <= hov & nz; pflt_d <= hp_fault; end
endmodule

// ------------------------------------------------------------------------------------------------ return bus tile
module ot_s81_hc_ctr #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, RLY = 2
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire [7:0]             tid,
    input  wire                   last,
    input  wire [S_RD+4:0]        fv,
    input  wire [FXW-1:0]         fdx,
    input  wire [S_RT+3:0]        rv_in,
    input  wire [RDW-1:0]         rd_in,
    output wire [S_RT+3:0]        rv_out,
    output wire [RDW-1:0]         rd_out,
    output wire [16*S_RT-1:0]     rq_q,               // pin-flop row fields for the banks' h reads
    output reg                    hs_run,
    output reg  [15:0]            hs_c,
    input  wire [4*256*S_RT-1:0]  hrq,
    input  wire [4*64-1:0]        yb,
    input  wire [4*32-1:0]        cs,
    input  wire [3:0]             nflt,
    input  wire                   hov_d, hnz_d, pflt_d
);
    localparam integer O_HS = 5 + S_RD * 16 + 20 + 6 + 8 + 32, O_D = O_HS + 1, FXW = O_D + S_RD * 512;
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, GT = GS / 2, N = 4 * NG, NV = D / N, NT = 4 * GT;
    localparam integer NR = D / NG, HROWS = NR * NG / 8, YROWS = N / 32, LM = ML, LA = AL;
    localparam integer DS = LM + 7 * LA, DY = 2 * LM + 1;
    localparam integer P_T = 0, P_I = S_RT, P_Q = P_I + 8 * S_RT, P_PI = P_Q + 16 * S_RT, P_D = P_PI + 8,
                       RDW = P_D + 512 * S_RT;
    reg [1:0] rr;
    always @(posedge clk) rr <= {rr[0], rst_in};
    wire rst_n = rr[1];
    reg [7:0] tq;
    reg       lq, farq;
    always @(posedge clk) begin tq <= tid; lq <= last; farq <= tid[0]; end
    wire ng_v = fv[S_RD+1], hs_v = fv[S_RD+4];

    wire n_hs, n_cs, mx_v, x_v, b_v;
    wire [1:0] n_gs;
    wire [7:0] xi, si, sc_i, wi, yi;
    wire [DS:0] vs;
    wire [DY:0] vy;
    wire [31:0] rh;
    ot_s81_hc_ctq #(.NG(NG), .D(D), .S_RD(S_RD), .ML(ML), .AL(AL)) u_q (.clk(clk), .rst_n(rst_n), .fv(fv), .fdx(fdx),
        .n_hs(n_hs), .n_cs(n_cs), .n_gs(n_gs), .mx_v(mx_v), .x_v(x_v), .xi(xi), .vs(vs), .si(si), .rh(rh), .sc_i(sc_i),
        .b_v(b_v), .vy(vy), .wi(wi), .yi(yi));
    integer s, k, qd, q;
    reg [127:0] psb [0:NV-1];
    always @(posedge clk) if (vs[DS]) psb[si] <= cs;
    reg [NT*16-1:0] ybuf [0:NV-1];
    always @(posedge clk) if (vy[DY]) ybuf[yi] <= yb;

    // far tile: return slot origination (ot_s81_hc_ctile)
    reg        po_v;  reg [7:0] po_i;
    always @(posedge clk or negedge rst_n) if (!rst_n) po_v <= 1'b0; else po_v <= vs[DS] && lq;
    always @(posedge clk) po_i <= si;
    reg  y_d1;
    always @(posedge clk or negedge rst_n) if (!rst_n) y_d1 <= 1'b0; else y_d1 <= vy[DY];
    reg [7:0]  oq_rdy, o_v;
    reg [15:0] o_r;
    reg  [S_RT-1:0]    g_v, g_t;
    reg  [8*S_RT-1:0]  g_i;
    reg  [16*S_RT-1:0] g_q;
    always @(*) begin
        g_v = 0; g_t = 0; g_i = 0; g_q = 0;
        if (lq) begin
            if (hs_run) begin
                for (s = 0; s < S_RT; s = s + 1)
                    if (hs_c + s < HROWS) begin g_v[s] = 1'b1; g_t[s] = 1'b1; g_q[16 * s +: 16] = hs_c + s; end
            end else if (o_v < oq_rdy) begin
                for (s = 0; s < S_RT; s = s + 1)
                    if (o_r + s < YROWS) begin g_v[s] = 1'b1; g_i[8 * s +: 8] = o_v; g_q[16 * s +: 16] = o_r + s; end
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin oq_rdy <= 0; o_v <= 0; o_r <= 0; hs_run <= 1'b0; hs_c <= 0; end
        else begin
            if (ng_v) begin oq_rdy <= 0; o_v <= 0; o_r <= 0; end
            else begin
                if (y_d1) oq_rdy <= oq_rdy + 8'd1;
                if (!hs_run && o_v < oq_rdy) begin
                    if (o_r + S_RT >= YROWS) begin o_r <= 0; o_v <= o_v + 8'd1; end
                    else o_r <= o_r + S_RT;
                end
            end
            if (hs_v) begin hs_run <= 1'b1; hs_c <= 0; end
            else if (hs_run) begin hs_c <= hs_c + S_RT; if (hs_c + S_RT >= HROWS) hs_run <= 1'b0; end
        end
    end

    // stage 1: pin flops; stage 2: the far tile's originated slots; stage 3: merge; then 2 + RLY - 3 relays + out
    reg [S_RT+3:0] rvq, rv2, rvm;
    reg [RDW-1:0]  rdq, rd2, rdm;
    assign rq_q = rdq[P_Q +: 16 * S_RT];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rvq <= 0; rv2 <= 0; rvm <= 0; end
        else begin
            rvq <= rv_in;
            rv2[S_RT-1:0] <= lq ? g_v : rvq[S_RT-1:0];
            rv2[S_RT]     <= lq ? po_v : rvq[S_RT];
            rv2[S_RT+1]   <= !lq && rvq[S_RT+1];
            rv2[S_RT+2]   <= rvq[S_RT+2];
            rv2[S_RT+3]   <= rvq[S_RT+3];
            rvm[S_RT:0]   <= rv2[S_RT:0];
            rvm[S_RT+1]   <= rv2[S_RT+1] | (lq && hov_d);
            rvm[S_RT+2]   <= rv2[S_RT+2] | pflt_d | (|nflt);
            rvm[S_RT+3]   <= rv2[S_RT+3] | hnz_d;
        end
    always @(posedge clk) begin : orig
        reg [RDW-1:0] o;
        o = lq ? {RDW{1'b0}} : rdq;
        if (lq) begin o[P_T +: S_RT] = g_t; o[P_I +: 8 * S_RT] = g_i; o[P_Q +: 16 * S_RT] = g_q; o[P_PI +: 8] = po_i; end
        rdq <= rd_in;
        rd2 <= o;
    end
    wire [256*S_RT-1:0] hrd = hrq[0 +: 256 * S_RT] | hrq[256 * S_RT +: 256 * S_RT] | hrq[512 * S_RT +: 256 * S_RT] |
                              hrq[768 * S_RT +: 256 * S_RT];
    always @(posedge clk) begin : mrg
        reg [RDW-1:0] o;
        o = rd2;
        if (rv2[S_RT] && farq) begin                                     // the far half owns the octet's slot
            if (NP > 1) o[P_D + 128 +: (NP > 1 ? NP - 1 : 1) * 128] = o[P_D +: (NP > 1 ? NP - 1 : 1) * 128];
            o[P_D +: 128] = psb[o[P_PI +: 8]];
        end
        for (s = 0; s < S_RT; s = s + 1)
            if (rv2[s]) begin : sl
                reg [7:0] vi;
                reg [15:0] qx, g, g0, b;
                reg [NT*16-1:0] yr;
                reg [255:0] hr;
                vi = o[P_I + 8 * s +: 8]; qx = o[P_Q + 16 * s +: 16];
                if (!o[P_T + s]) begin
                    yr = ybuf[vi];
                    g = ((32 * qx) % NG) / GT; b = (32 * qx) / NG;
                    for (k = 0; k < 32; k = k + 1)
                        for (qd = 0; qd < N / NG; qd = qd + 1)
                            if ((NG >= 32 ? g + k / GT : (k % NG) / GT) == tq && (NG >= 32 ? b : b + k / NG) == qd)
                                o[P_D + 512 * s + 16 * k +: 16] = yr[16 * (qd * GT + k % GT) +: 16];
                end else begin
                    g0 = ((8 * qx) % NG) / 8;
                    hr = hrd[256 * s +: 256];
                    for (k = 0; k < 8; k = k + 1)
                        if (g0 * (8 / GT) + k / GT == tq)
                            o[P_D + 512 * s + 64 * k +: 64] = hr[64 * (k % GT) +: 64];
                end
            end
        rdm <= o;
    end
    wire [S_RT+3:0] rv_out_d;
    wire [RDW-1:0]  rd_out_d;
    ot_hdc_delay #(.W(S_RT + 4), .D(RLY - 2), .RESET(1)) u_rvr (.clk(clk), .rst_n(rst_n), .d(rvm), .q(rv_out_d));
    ot_hdc_delay #(.W(RDW), .D(RLY - 2)) u_rdr (.clk(clk), .rst_n(rst_n), .d(rdm), .q(rd_out_d));
    reg  [S_RT+3:0] rvo;
    reg  [RDW-1:0]  rdo;
    always @(posedge clk or negedge rst_n) if (!rst_n) rvo <= 0; else rvo <= rv_out_d;
    always @(posedge clk) rdo <= rd_out_d;
    assign rv_out = rvo;
    assign rd_out = rdo;
endmodule
