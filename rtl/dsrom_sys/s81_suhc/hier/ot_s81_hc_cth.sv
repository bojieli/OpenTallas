`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_cth (el1011-s81hc-ctile, 2026-10-12): the HALF = 1 column sub-tile of the HC slab (dsfd_sp_hc HIER=2),
// split into hard tiles of <= ~15k clock sinks each.  Cycle-for-cycle the same pins and bus timing as
// ot_s81_hc_ctile #(.HALF(1)) (that module's header holds the protocol); this file only moves the logic:
//   ctf   forward bus: reset relay, fv / fd pin flops, y-shift register, RLY relay, out flops (the 4 forward hops);
//         exports its pin flops (fv, fd control + slot data) to the other tiles (registered seam).
//   ctnl  x16, one per norm lane (bank j = h row % 4, group l): the lane's slice of the bank's resident h rows
//         (group l, 2 slots x NV), its gain words, hc_pre mix -> square, x wait line, scale, y, and chain adder l of the
//         bank's chunk chain (+ the HALF carry at lane 0); registered zero-gated read ports for hc_post (hpr) and the
//         return's h rows (hrq, read one stage ahead).  bank / lane / tid / last are strap PINS captured in flops: one
//         hardened master serves all 16 lanes of every sub-tile; no strap fans out.
//   ctpl  x8, hc_post group g output lanes {2h, 2h+1} (ot_dsrom_su_hcpost sliced) + its coefficient words and the
//         write-back counters; in_r = OR of the 4 banks' zero-gated group-g reads.
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
    wire [16*S_RT-1:0]  rq_q;
    wire                hs_run;
    wire [15:0]         hs_c;
    wire [16*64-1:0]    hpr;                       // lane tile n = 4 bank + group
    wire [16*64*S_RT-1:0] hrq;
    wire [16*16-1:0]    yb;
    wire [16*32-1:0]    sq, acc, cyo;
    wire [15:0]         nflt;
    wire [7:0]          hov, pwb, phs, hnz_d, pflt_d, hov_d;
    wire [8*16-1:0]     pob;
    wire [8*32-1:0]     hpo;                       // lane-pair tile m = 2 group + half
    genvar j, l, m;
    generate for (j = 0; j < 4; j = j + 1) begin : g_b
        for (l = 0; l < 4; l = l + 1) begin : g_l
            localparam integer n = 4 * j + l;
            ot_s81_hc_ctnl #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY)) u_n (
                .clk(clk), .rst_in(rst_in), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fdx),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_q), .hs_run(hs_run), .hs_c(hs_c),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
        end
        assign cy_out[32 * j +: 32] = cyo[32 * (4 * j + 2) +: 32];
    end endgenerate
    generate for (m = 0; m < 8; m = m + 1) begin : g_p
        ot_s81_hc_ctpl #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL)) u_p (
            .clk(clk), .rst_in(rst_in), .grp(m[2:1]), .half(m[0]), .fv(fv), .fdx(fdx),
            .hpr({hpr[64 * (12 + m / 2) +: 64], hpr[64 * (8 + m / 2) +: 64], hpr[64 * (4 + m / 2) +: 64], hpr[64 * (m / 2) +: 64]}),
            .hov(hov[m]), .pwb(pwb[m]), .phs(phs[m]), .pob(pob[16 * m +: 16]), .hpo(hpo[32 * m +: 32]),
            .hov_d(hov_d[m]), .hnz_d(hnz_d[m]), .pflt_d(pflt_d[m]));
    end endgenerate
    wire [4*32-1:0] cs = {acc[32 * 15 +: 32], acc[32 * 11 +: 32], acc[32 * 7 +: 32], acc[32 * 3 +: 32]};
    ot_s81_hc_ctr #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY)) u_r (
        .clk(clk), .rst_in(rst_in), .tid(tid), .last(last), .fv(fv), .fdx(fdx), .rv_in(rv_in), .rd_in(rd_in),
        .rv_out(rv_out), .rd_out(rd_out), .rq_q(rq_q), .hs_run(hs_run), .hs_c(hs_c), .hrq(hrq), .yb(yb), .cs(cs),
        .nflt(nflt), .hov_d(hov_d[0]), .hnz_d(|hnz_d), .pflt_d(|pflt_d));
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
    output wire [ML+7*AL:0] vs,
    output wire [7:0]      si,
    output reg  [31:0]     rh,
    output reg  [7:0]      sc_i,
    output reg             b_v,
    output wire [2*ML+1:0] vy,
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

// ------------------------------------------------------------------------------------------------ norm lane tile
// One norm lane (bank bq, lane lq of the half-octet: slab lane bq * 4 + lq) = adder position lq of the bank's chunk
// chain.  Holds the lane's slice of the bank's resident h rows (group lq: 4 copies BF16 x 2 slots x NV), its gain
// words, mix -> square, x wait line, scale, y.  Chain (ot_s81_hc_ctile g_half): adder kk = lq; near half: operand
// = next lane's square (sqn_in, delayed LA kk), fires vs[LM + LA kk] (lane 3 idle); far half: operand = own square
// delayed LA (kk + 3), fires vs[LM + LA (kk + 3)]; acc[0] = (far ? carry : own square) at lane 0, else acc_in.
// Straps bank / lane / tid / last are pins captured in flops: one master for all 16 lanes of every sub-tile.
module ot_s81_hc_ctnl #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, RLY = 2
) (
    input  wire                  clk,
    input  wire                  rst_in,
    input  wire [7:0]            tid,
    input  wire [1:0]            bank,
    input  wire [1:0]            lane,
    input  wire                  last,
    input  wire [S_RD+4:0]       fv,
    input  wire [FXW-1:0]        fdx,
    input  wire                  wb_v, wb_en, wb_hs,  // hc_post write back (ctpl flops)
    input  wire [15:0]           wb_ob,
    input  wire [63:0]           wb_d,                // group lq's 4 hc_post outputs, BF16
    input  wire [16*S_RT-1:0]    rq_q,                // return pin flops (ctr): row field
    input  wire                  hs_run,
    input  wire [15:0]           hs_c,
    output reg  [63:0]           hpr,                 // hc_post row read, group lq (zero unless this bank)
    output reg  [64*S_RT-1:0]    hrq,                 // return h row reads, group lq (zero unless this bank)
    input  wire [31:0]           cy_in,               // octet carry (lane 0)
    input  wire [31:0]           acc_in,              // chain: previous lane's adder output
    input  wire [31:0]           sqn_in,              // chain: next lane's square
    output wire [31:0]           sq_out,
    output wire [31:0]           acc_out,
    output reg  [31:0]           cy_out,              // registered acc_out (the octet carry at lane 2)
    output wire [15:0]           yb,
    output reg                   flt
);
    localparam integer O_RK = 0, O_RS = 2, O_RG = 3, O_RC = 5, O_PB = O_RC + S_RD * 16, O_NG = O_PB + 20,
                       O_NV = O_NG + 6, O_R = O_NV + 8, O_HS = O_R + 32, O_D = O_HS + 1, FXW = O_D + S_RD * 512;
    localparam integer GT = GS / 2, N = 4 * NG, NV = D / N, PPR = NG / 8, LM = ML, LA = AL;
    localparam integer DS = LM + 7 * LA, DY = 2 * LM + 1;
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] s;
        begin s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]}; bf16 = {s[31:16], 16'd0}; end
    endfunction
    reg [1:0] rr;
    always @(posedge clk) rr <= {rr[0], rst_in};
    wire rst_n = rr[1];
    reg [7:0] tq;
    reg [1:0] bq, lq;
    reg       laq, hs_sl, farq, l0q, l3q;
    always @(posedge clk) begin
        tq <= tid; bq <= bank; lq <= lane; laq <= last; farq <= tid[0]; l0q <= (lane == 2'd0); l3q <= (lane == 2'd3);
    end
    wire [S_RD-1:0] rd_v = fv[S_RD-1:0];
    wire pb_v = fv[S_RD], nv_v = fv[S_RD+2], hs_v = fv[S_RD+4];
    wire [1:0] rd_k = fdx[O_RK +: 2];
    wire       rd_s = fdx[O_RS];
    wire [1:0] rd_g = fdx[O_RG +: 2];
    wire       pb_hs = fdx[O_PB + 2];
    wire [15:0] pb_b = fdx[O_PB + 4 +: 16];
    wire [7:0]  nv_i = fdx[O_NV +: 8];
    always @(posedge clk) if (hs_v) hs_sl <= fdx[O_HS];

    reg [63:0]  hb [0:2*NV-1];                           // group lq of bank bq's h rows
    reg [31:0]  gt [0:4*NV-1];                           // lane gain words
    reg [127:0] cf_pre [0:1];
    integer s, k;
    always @(posedge clk) begin
        for (s = 0; s < S_RD; s = s + 1)
            if (rd_v[s]) begin : one
                reg [15:0] c, g0, l0, rb, g;
                c = fdx[O_RC + 16 * s +: 16];
                if (rd_k == 2'd0) begin
                    rb = c / PPR; g0 = c % PPR;
                    for (k = 0; k < 8; k = k + 1)
                        if (g0 * (8 / GT) + k / GT == tq && rb % 4 == bq && k % GT == lq)
                            hb[rd_s * NV + rb / 4] <= fdx[O_D + 512 * s + 64 * k +: 64];
                end else if (rd_k == 2'd1) begin
                    l0 = (16 * c) % N;
                    g = (l0 % NG) / GT;
                    for (k = 0; k < 16; k = k + 1)
                        if (g + k / GT == tq && l0 / NG == bq && k % GT == lq)
                            gt[rd_g * NV + (16 * c) / N] <= fdx[O_D + 512 * s + 32 * k +: 32];
                end else if (rd_k == 2'd2) begin
                    if (c != 0) cf_pre[rd_s] <= fdx[O_D + 512 * s +: 128];
                end
            end
        if (wb_v && wb_en && wb_ob % 4 == bq) hb[wb_hs * NV + wb_ob / 4] <= wb_d;
    end
    always @(posedge clk) if (pb_v) hpr <= (pb_b % 4 == bq) ? hb[pb_hs * NV + pb_b / 4] : 64'd0;
    always @(posedge clk) begin : rdh
        reg [15:0] qx, b;
        for (s = 0; s < S_RT; s = s + 1) begin
            qx = laq ? hs_c + s : rq_q[16 * s +: 16];
            b = (8 * qx) / NG;
            hrq[64 * s +: 64] <= (b % 4 == bq) ? hb[hs_sl * NV + b / 4] : 64'd0;
        end
    end

    wire n_hs, n_cs, mx_v, x_v, b_v;
    wire [1:0] n_gs;
    wire [7:0] xi, si, sc_i, wi, yi;
    wire [DS:0] vs;
    wire [DY:0] vy;
    wire [31:0] rh;
    ot_s81_hc_ctq #(.NG(NG), .D(D), .S_RD(S_RD), .ML(ML), .AL(AL)) u_q (.clk(clk), .rst_n(rst_n), .fv(fv), .fdx(fdx),
        .n_hs(n_hs), .n_cs(n_cs), .n_gs(n_gs), .mx_v(mx_v), .x_v(x_v), .xi(xi), .vs(vs), .si(si), .rh(rh), .sc_i(sc_i),
        .b_v(b_v), .vy(vy), .wi(wi), .yi(yi));
    reg [63:0] mx_h;
    always @(posedge clk) if (nv_v) mx_h <= hb[n_hs * NV + nv_i];
    wire [31:0] xl, p, qq, sq;
    wire [4:0]  f;
    ot_dsrom_su_norm_mix #(.LM(LM), .LA(LA)) u_mix (.clk(clk), .rst_n(rst_n), .v(mx_v),
        .h0({mx_h[0 +: 16], 16'h0000}), .h1({mx_h[16 +: 16], 16'h0000}), .h2({mx_h[32 +: 16], 16'h0000}),
        .h3({mx_h[48 +: 16], 16'h0000}), .pre(cf_pre[n_cs]), .x(xl), .fault(f[0]));
    reg [31:0] xb [0:NV-1];
    reg [31:0] xo_r, wo_r, yr;
    always @(posedge clk) if (x_v) xb[xi] <= xl;
    always @(posedge clk) xo_r <= xb[sc_i];
    always @(posedge clk) wo_r <= gt[n_gs * NV + wi];
    ot_hdc_qmul_lat #(LM) u_sq (clk, rst_n, x_v, xl, xl, sq, f[1]);
    ot_hdc_qmul_lat #(LM) u_xr (clk, rst_n, b_v, xo_r, rh, p, f[2]);
    ot_hdc_qmul_lat #(LM) u_w  (clk, rst_n, vy[LM], wo_r, p, qq, f[3]);
    always @(posedge clk) yr <= bf16(qq);
    assign yb = yr[31:16];
    assign sq_out = sq;
    // chain adder kk = lq: tapped delay lines (taps LA lq near, LA (lq + 3) far)
    reg  [31:0] dnl [1:2*LA];
    reg  [31:0] dfl [1:6*LA];
    integer t;
    always @(posedge clk) begin
        dnl[1] <= sqn_in; for (t = 2; t <= 2 * LA; t = t + 1) dnl[t] <= dnl[t - 1];
        dfl[1] <= sq;     for (t = 2; t <= 6 * LA; t = t + 1) dfl[t] <= dfl[t - 1];
    end
    reg [31:0] dn, df;
    reg        fire;
    always @(*) begin
        case (lq) 2'd0: dn = sqn_in; 2'd1: dn = dnl[LA]; 2'd2: dn = dnl[2 * LA]; default: dn = 32'd0; endcase
        case (lq) 2'd0: df = dfl[3 * LA]; 2'd1: df = dfl[4 * LA]; 2'd2: df = dfl[5 * LA]; default: df = dfl[6 * LA]; endcase
        case (lq) 2'd0: fire = farq ? vs[LM + 3 * LA] : vs[LM];
                  2'd1: fire = farq ? vs[LM + 4 * LA] : vs[LM + LA];
                  2'd2: fire = farq ? vs[LM + 5 * LA] : vs[LM + 2 * LA];
                  default: fire = farq ? vs[LM + 6 * LA] : 1'b0; endcase
    end
    wire [31:0] cyd;
    reg  [31:0] cyq;
    always @(posedge clk) cyq <= cy_in;
    ot_hdc_delay #(.W(32), .D(RLY)) u_cy (.clk(clk), .rst_n(rst_n), .d(cyq), .q(cyd));
    wire [31:0] acc_a = l0q ? (farq ? cyd : sq) : acc_in;
    ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, fire, acc_a, farq ? df : dn, acc_out, f[4]);
    always @(posedge clk) cy_out <= acc_out;
    always @(posedge clk or negedge rst_n) if (!rst_n) flt <= 1'b0; else flt <= |f;
endmodule

// ------------------------------------------------------------------------------------------------ hc_post lane-pair tile
// Element group gq (of the half-octet's 4), output lanes k = 2 hq, 2 hq + 1: ot_dsrom_su_hcpost sliced (the op words'
// WIN traverse + latch, the group's WIN in-wire + x register, 2 ot_dsrom_su_hcpost_lane, the WOUT out-wire), with its
// slice of the coefficient words and the write-back counters.  r: OR of the 4 banks' zero-gated group-gq reads.
module ot_s81_hc_ctpl #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, WIN = 2, WOUT = 2, ML = 5, AL = 4
) (
    input  wire                clk,
    input  wire                rst_in,
    input  wire [1:0]          grp,
    input  wire                half,
    input  wire [S_RD+4:0]     fv,
    input  wire [FXW-1:0]      fdx,
    input  wire [4*64-1:0]     hpr,                  // banks 0..3, group gq
    output wire                hov,
    output reg                 pwb, phs,
    output reg  [15:0]         pob,
    output wire [31:0]         hpo,                  // its 2 outputs, BF16
    output reg                 hov_d, hnz_d, pflt_d
);
    localparam integer O_RK = 0, O_RS = 2, O_RC = 5, O_PB = O_RC + S_RD * 16, O_D = O_PB + 20 + 6 + 8 + 32 + 1;
    localparam integer FXW = O_D + S_RD * 512;
    reg [1:0] rr;
    always @(posedge clk) rr <= {rr[0], rst_in};
    wire rst_n = rr[1];
    reg [1:0] gq;
    reg       hq;
    always @(posedge clk) begin gq <= grp; hq <= half; end
    wire [S_RD-1:0] rd_v = fv[S_RD-1:0];
    wire pb_v = fv[S_RD];
    wire [1:0] rd_k = fdx[O_RK +: 2];
    wire       rd_s = fdx[O_RS];
    wire pb_go = fdx[O_PB], pb_wb = fdx[O_PB + 1], pb_hs = fdx[O_PB + 2], pb_cs = fdx[O_PB + 3];
    // coefficient words of lanes k0 = 2 hq, k0 + 1: comb c[j][k] = word 4 j + k, post[k]
    reg [8*32-1:0] cf_comb [0:1];
    reg [2*32-1:0] cf_post [0:1];
    integer s, j, e;
    always @(posedge clk)
        for (s = 0; s < S_RD; s = s + 1)
            if (rd_v[s] && rd_k == 2'd2) begin
                if (fdx[O_RC + 16 * s +: 16] == 16'd0) begin
                    for (j = 0; j < 4; j = j + 1)
                        for (e = 0; e < 2; e = e + 1)
                            cf_comb[rd_s][32 * (2 * j + e) +: 32] <= hq ? fdx[O_D + 512 * s + 32 * (4 * j + 2 + e) +: 32]
                                                                         : fdx[O_D + 512 * s + 32 * (4 * j + e) +: 32];
                end else
                    cf_post[rd_s] <= hq ? fdx[O_D + 512 * s + 128 + 64 +: 64] : fdx[O_D + 512 * s + 128 +: 64];
            end
    reg            hp_go, hp_in_v;
    reg [31:0]     hp_y;
    reg [8*32-1:0] hp_comb;
    reg [2*32-1:0] hp_post;
    always @(posedge clk or negedge rst_n) if (!rst_n) hp_in_v <= 1'b0; else hp_in_v <= pb_v;
    always @(posedge clk) begin
        hp_go <= pb_v && pb_go;
        if (pb_v) begin
            case (gq) 2'd0: hp_y <= fdx[O_D +: 32]; 2'd1: hp_y <= fdx[O_D + 32 +: 32];
                      2'd2: hp_y <= fdx[O_D + 64 +: 32]; default: hp_y <= fdx[O_D + 96 +: 32]; endcase
            hp_comb <= cf_comb[pb_cs]; hp_post <= cf_post[pb_cs];
            if (pb_go) begin pwb <= pb_wb; phs <= pb_hs; pob <= 16'd0; end
        end
        if (hov) pob <= pob + 16'd1;
    end
    // op words: WIN traverse with go, latched (ot_dsrom_su_hcpost u_wop / c_r / p_r)
    wire           w_v;
    wire [10*32-1:0] w_d;
    ot_dsrom_su_hcpost_wire #(.W(10*32), .D(WIN)) u_wop (.clk(clk), .rst_n(rst_n), .v(hp_go), .d({hp_post, hp_comb}),
                                                         .vq(w_v), .q(w_d));
    reg [8*32-1:0] c_r;
    reg [2*32-1:0] p_r;
    always @(posedge clk) if (w_v) begin c_r <= w_d[8*32-1:0]; p_r <= w_d[10*32-1:8*32]; end
    // the group (ot_dsrom_su_hcpost_group, lanes k0, k0 + 1)
    wire [63:0]  hr = hpr[0 +: 64] | hpr[64 +: 64] | hpr[128 +: 64] | hpr[192 +: 64];
    wire [127:0] r  = {hr[48 +: 16], 16'h0000, hr[32 +: 16], 16'h0000, hr[16 +: 16], 16'h0000, hr[0 +: 16], 16'h0000};
    wire         b_v;
    wire [159:0] b_d;
    ot_dsrom_su_hcpost_wire #(.W(160), .D(WIN)) u_win (.clk(clk), .rst_n(rst_n), .v(hp_in_v), .d({hp_y, r}), .vq(b_v), .q(b_d));
    reg          x_v;
    reg  [159:0] x_d;
    always @(posedge clk or negedge rst_n) if (!rst_n) x_v <= 1'b0; else x_v <= b_v;
    always @(posedge clk) x_d <= b_d;
    wire [63:0] l_o;
    wire [1:0]  l_v, l_f;
    genvar k;
    generate for (k = 0; k < 2; k = k + 1) begin : g_k
        ot_dsrom_su_hcpost_lane #(.ML(ML), .AL(AL)) u (
            .clk(clk), .rst_n(rst_n), .v(x_v),
            .r0(x_d[0 +: 32]), .r1(x_d[32 +: 32]), .r2(x_d[64 +: 32]), .r3(x_d[96 +: 32]), .y(x_d[128 +: 32]),
            .c0(c_r[32*(0+k) +: 32]), .c1(c_r[32*(2+k) +: 32]), .c2(c_r[32*(4+k) +: 32]), .c3(c_r[32*(6+k) +: 32]),
            .p(p_r[32*k +: 32]), .vo(l_v[k]), .o(l_o[32*k +: 32]), .fault(l_f[k]));
    end endgenerate
    wire [63:0] o;
    ot_dsrom_su_hcpost_wire #(.W(64), .D(WOUT)) u_wout (.clk(clk), .rst_n(rst_n), .v(l_v[0]), .d(l_o), .vq(hov), .q(o));
    assign hpo = {o[48 +: 16], o[16 +: 16]};
    wire nz = (|o[0 +: 16]) | (|o[32 +: 16]);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin hov_d <= 1'b0; hnz_d <= 1'b0; pflt_d <= 1'b0; end
        else begin hov_d <= hov; hnz_d <= hov & nz; pflt_d <= |l_f; end
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
    input  wire [16*64*S_RT-1:0]  hrq,                // lane tile n = 4 bank + group
    input  wire [16*16-1:0]       yb,
    input  wire [4*32-1:0]        cs,
    input  wire [15:0]            nflt,
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
    reg [256*S_RT-1:0] hrd;                                          // slot s, group l: OR of the 4 banks
    integer ss, ll;
    always @(*)
        for (ss = 0; ss < S_RT; ss = ss + 1)
            for (ll = 0; ll < 4; ll = ll + 1)
                hrd[256 * ss + 64 * ll +: 64] = hrq[64 * S_RT * ll + 64 * ss +: 64] | hrq[64 * S_RT * (4 + ll) + 64 * ss +: 64] |
                                                hrq[64 * S_RT * (8 + ll) + 64 * ss +: 64] | hrq[64 * S_RT * (12 + ll) + 64 * ss +: 64];
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
