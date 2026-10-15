`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_ctile (s81-suhc-hier-1011, 2026-10-11): ONE column sub-tile of the hierarchical S81 HC slab
// (dsfd_sp_hc HIER=1).  The slab (1,727.976 um wide) is NCOL = 3 independent column chains of 575.992 um; chain c
// holds the sub-tiles s = B_c .. B_c + L_c - 1 (NS = NG / GS sub-tiles, NP = ceil(NS / NCOL); L = NP, NS - 2 NP, NP:
// the short chain in the centre, under the combine tile; B = 0, NP, NP + L_1), sub-tile s
// owning the GS element groups s*GS .. s*GS + GS - 1 (an octet at GS 8) of every resident row:
//   - the resident h of its groups (2 job slots x NR rows x GS groups x 4 copies BF16; no reset),
//   - its hc_post groups (ot_dsrom_su_hcpost, NG = GS) writing back in place,
//   - its 4 GS norm lanes (lane j*GS + gl = bank j, group s*GS + gl): hc_pre mix -> square -> 8-element chunk chains
//     -> the per-bank subtree over its GS/8 chunks (an aligned subtree of the golden pairwise tree), the x wait line,
//     the gain slice and the scale y = bf16(w * (x * r)); the FP8 act-quant runs at the root on the y rows,
//   - the coefficient words of both slots (broadcast copy).
// Buses (all fixed-latency pulse buses: no handshake crosses a tile boundary): the forward bus fv / fd (root commands,
// VM response rows or the chain's y beat in the shared data field: no job carries both) enters the N face, is captured
// in pin flops, relayed by a mid-tile register and leaves the S face at identical x (3 registers a hop; the y field is
// shifted down one slice so every tile takes slice 0).  The return bus rv / rd enters the S face (pin flops), takes this
// tile's pieces in the merge register and leaves the N face through a relay register (3 registers a hop).  The far tile
// of the chain (strap `last`) ORIGINATES the return slots: per norm vector a partial packet (each tile shifts it up one
// 128-b slot and inserts its 4 bank partials) and the y rows (S_RT a cycle), and the h rows of an H_STORE.
// HALF = 1 (structural variant): every octet is two half-octet sub-tiles (GT = GS / 2 = 4 groups: 16 hc_post + 16
// norm lanes each), N-S neighbours in the chain (tid = 2 x octet + h).  An octet's 8-lane chunk chain runs across the
// seam in the golden order: the near half (h 0) sums lanes 0..3 sequentially and sends the running sum south (send +
// capture + RLY registers = exactly one forward hop, so it meets the far half's lane-4 add); the far half (h 1)
// continues with lanes 4..7 and owns the octet's slot in the partial packet (the near half passes it through).
// RLY: mid-tile relay registers on each bus (a hop is 2 + RLY registers each way).
// Reset: rst_in is relayed (two flops, no reset) to this tile's logic and to rst_out; datapath registers have no reset.
// Straps: tid = s, last = (s is the chain's far tile).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_ctile #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, WIN = 2, WOUT = 2, ML = 5, AL = 4,
    parameter integer HALF = 0, RLY = 1
) (
    input  wire                       clk,
    input  wire                       rst_in,
    output wire                       rst_out,
    input  wire [7:0]                 tid,
    input  wire                       last,
    input  wire [S_RD+4:0]            fv_in,
    input  wire [FDW-1:0]             fd_in,
    output reg  [S_RD+4:0]            fv_out,
    output reg  [FDW-1:0]             fd_out,
    input  wire [S_RT+3:0]            rv_in,
    input  wire [RDW-1:0]             rd_in,
    output reg  [S_RT+3:0]            rv_out,
    output reg  [RDW-1:0]             rd_out,
    // HALF: an octet's chunk chain carry, near half -> far half (4 banks x 32 b)
    output reg  [127:0]               cy_out,
    input  wire [127:0]               cy_in
);
    localparam integer NS   = NG / GS;                // octets
    localparam integer NP   = (NS + NCOL - 1) / NCOL; // octet slots a chain (the partial packet)
    localparam integer YW   = NP * GS * 32;
    localparam integer GT   = HALF ? GS / 2 : GS;     // groups of this sub-tile
    localparam integer FDD  = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer N    = 4 * NG;
    localparam integer NR   = D / NG;
    localparam integer NV   = D / N;
    localparam integer PPR  = NG / 8;
    localparam integer RWT  = GT * 64;
    localparam integer NT   = 4 * GT;
    localparam integer LTB  = HALF ? 0 : $clog2(GS / 8);
    localparam integer HROWS = NR * NG / 8;
    localparam integer YROWS = N / 32;
    localparam integer LM = ML, LA = AL;
    localparam integer DM = LM + 3 * LA + 1;
    localparam integer DS = LM + 7 * LA + LTB * LA;
    // forward bus layout (ot_s81_hc_hroot uses the same)
    localparam integer O_RK = 0, O_RS = 2, O_RG = 3, O_RC = 5, O_PB = O_RC + S_RD * 16, O_NG = O_PB + 20, O_NV = O_NG + 6,
                       O_R = O_NV + 8, O_HS = O_R + 32, O_D = O_HS + 1, FDW = O_D + FDD;
    // return bus layout
    localparam integer P_T = 0, P_I = S_RT, P_Q = P_I + 8 * S_RT, P_PI = P_Q + 16 * S_RT, P_D = P_PI + 8,
                       RDW = P_D + 512 * S_RT;
`ifndef SYNTHESIS
    initial begin
        if (GS < 8 || (GS & (GS - 1)) != 0 || NG % GS != 0) $fatal(1, "ot_s81_hc_ctile: GS a power of two >= 8 dividing NG");
        if (GS != 8) $fatal(1, "ot_s81_hc_ctile: decoded row writes assume octet groups (GS 8)");
        if (NG % 32 != 0 && 32 % NG != 0) $fatal(1, "ot_s81_hc_ctile: NG a multiple or a divisor of 32 (y row decode)");
        if (HALF && GS != 8) $fatal(1, "ot_s81_hc_ctile: HALF splits an octet (GS 8)");
        if (NP * 128 > S_RT * 512) $fatal(1, "ot_s81_hc_ctile: the partial packet must fit the return data field");
        if (D % N != 0) $fatal(1, "ot_s81_hc_ctile: D a multiple of 4 NG");
    end
`endif
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] s;
        begin s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]}; bf16 = {s[31:16], 16'd0}; end
    endfunction

    // ------------------------------------------------------------------ reset relay, forward pin flops and relay
    reg [1:0] rr;
    always @(posedge clk) rr <= {rr[0], rst_in};
    wire rst_n = rr[1];
    assign rst_out = rr[1];
    reg [S_RD+4:0] fv, fvm;
    reg [FDW-1:0]  fd, fdm;
    wire [S_RD+4:0] fvm_d;
    wire [FDW-1:0]  fdm_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fv <= 0; fvm <= 0; fv_out <= 0; end
        else begin fv <= fv_in; fvm <= fv; fv_out <= fvm_d; end
    always @(posedge clk) begin
        fd <= fd_in;
        fdm <= fd;
        if (fv[S_RD] && (NP > 1 || HALF)) fdm[O_D +: YW] <= fd[O_D +: YW] >> (GT * 32);   // y beat: next tile's slice to 0
        fd_out <= fdm_d;
    end
    ot_hdc_delay #(.W(S_RD + 5), .D(RLY - 1), .RESET(1)) u_fvr (.clk(clk), .rst_n(rst_n), .d(fvm), .q(fvm_d));
    ot_hdc_delay #(.W(FDW), .D(RLY - 1)) u_fdr (.clk(clk), .rst_n(rst_n), .d(fdm), .q(fdm_d));

    wire [S_RD-1:0] rd_v = fv[S_RD-1:0];
    wire pb_v = fv[S_RD], ng_v = fv[S_RD+1], nv_v = fv[S_RD+2], r_v = fv[S_RD+3], hs_v = fv[S_RD+4];
    wire [1:0] rd_k = fd[O_RK +: 2];
    wire       rd_s = fd[O_RS];
    wire [1:0] rd_g = fd[O_RG +: 2];
    wire pb_go = fd[O_PB], pb_wb = fd[O_PB + 1], pb_hs = fd[O_PB + 2], pb_cs = fd[O_PB + 3];
    wire [15:0] pb_b = fd[O_PB + 4 +: 16];
    wire [7:0] nv_i = fd[O_NV +: 8];
    wire [31:0] r_d = fd[O_R +: 32];

    // ------------------------------------------------------------------ resident state (no reset)
    reg [RWT-1:0]   hb [0:8*NV-1];                       // bank j, index i at j*2NV + i
    reg [16*32-1:0] cf_comb [0:1];
    reg [4*32-1:0]  cf_pre  [0:1];
    reg [4*32-1:0]  cf_post [0:1];
    reg [NT*32-1:0] gtab [0:4*NV-1];

    // ------------------------------------------------------------------ VM response rows (H_LOAD 0 / GAIN 1 / COEF 2)
    integer s, k, q, j_, gg, qd;
    always @(posedge clk) begin
        for (s = 0; s < S_RD; s = s + 1)
            if (rd_v[s]) begin : one
                reg [15:0] c, g0, l0, rb, g;
                c = fd[O_RC + 16 * s +: 16];
                // decoded writes: every lane slice is a constant part-select; the row's tile and quadrant are
                // compares (GS 8: an h row's 8 groups start at a multiple of 8, a gain row's 16 lanes at a multiple
                // of 16, so the in-tile slice is k % GT and only the owner / quadrant are runtime values)
                if (rd_k == 2'd0) begin
                    rb = c / PPR; g0 = c % PPR;                           // group octet of the row
                    for (k = 0; k < 8; k = k + 1)                         // the row's 8 groups
                        if (g0 * (8 / GT) + k / GT == tid)
                            hb[(rb % 4) * 2 * NV + rd_s * NV + rb / 4][64 * (k % GT) +: 64] <= fd[O_D + 512 * s + 64 * k +: 64];
                end else if (rd_k == 2'd1) begin
                    l0 = (16 * c) % N;
                    g = (l0 % NG) / GT;                                   // first tile-group of the row's 16 lanes
                    for (k = 0; k < 16; k = k + 1)
                        for (qd = 0; qd < N / NG; qd = qd + 1)
                            if (g + k / GT == tid && l0 / NG == qd)
                                gtab[rd_g * NV + (16 * c) / N][32 * (qd * GT + k % GT) +: 32] <= fd[O_D + 512 * s + 32 * k +: 32];
                end else if (rd_k == 2'd2) begin
                    if (c == 0) cf_comb[rd_s] <= fd[O_D + 512 * s +: 512];
                    else begin
                        cf_pre[rd_s]  <= fd[O_D + 512 * s +: 128];
                        cf_post[rd_s] <= fd[O_D + 512 * s + 128 +: 128];
                    end
                end
            end
    end

    // ------------------------------------------------------------------ hc_post (GT groups), write back in place
    reg               hp_go, hp_in_v;
    reg [GT*4*32-1:0] hp_r;
    reg [GT*32-1:0]   hp_y;
    reg [16*32-1:0]   hp_comb;
    reg [4*32-1:0]    hp_post;
    wire              hp_out_v, hp_fault;
    wire [GT*4*32-1:0] hp_out;
    ot_dsrom_su_hcpost #(.NG(GT), .WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL)) u_post (
        .clk(clk), .rst_n(rst_n), .go(hp_go), .comb(hp_comb), .post(hp_post), .in_v(hp_in_v), .in_r(hp_r), .in_y(hp_y),
        .out_v(hp_out_v), .out_d(hp_out), .fault(hp_fault));
    reg        p_wb, p_hs;
    reg [15:0] p_ob;
    always @(posedge clk or negedge rst_n) if (!rst_n) hp_in_v <= 1'b0; else hp_in_v <= pb_v;
    always @(posedge clk) begin
        hp_go <= pb_v && pb_go;
        if (pb_v) begin
            for (q = 0; q < 4 * GT; q = q + 1) hp_r[32 * q +: 32] <= {hb[(pb_b % 4) * 2 * NV + pb_hs * NV + pb_b / 4][16 * q +: 16], 16'h0000};
            hp_y <= fd[O_D +: GT * 32]; hp_comb <= cf_comb[pb_cs]; hp_post <= cf_post[pb_cs];
            if (pb_go) begin p_wb <= pb_wb; p_hs <= pb_hs; p_ob <= 16'd0; end
        end
        if (hp_out_v) begin
            if (p_wb)
                for (q = 0; q < 4 * GT; q = q + 1) hb[(p_ob % 4) * 2 * NV + p_hs * NV + p_ob / 4][16 * q +: 16] <= hp_out[32 * q + 16 +: 16];
            p_ob <= p_ob + 16'd1;
        end
    end
    reg nz;                                              // hc_post output not BF16 (lower half nonzero)
    always @(*) begin nz = 1'b0; for (q = 0; q < 4 * GT; q = q + 1) nz = nz | (|hp_out[32 * q +: 16]); end

    // ------------------------------------------------------------------ norm
    reg       n_hs, n_cs;
    reg [1:0] n_gs;
    always @(posedge clk) if (ng_v) begin n_hs <= fd[O_NG]; n_cs <= fd[O_NG + 1]; n_gs <= fd[O_NG + 2 +: 2]; end
    reg               mx_v;
    reg [7:0]         mx_i;
    reg [4*NT*32-1:0] mx_x;
    always @(posedge clk or negedge rst_n) if (!rst_n) mx_v <= 1'b0; else mx_v <= nv_v;
    always @(posedge clk) if (nv_v) begin
        mx_i <= nv_i;
        for (j_ = 0; j_ < 4; j_ = j_ + 1)
            for (gg = 0; gg < GT; gg = gg + 1)
                for (k = 0; k < 4; k = k + 1)
                    mx_x[(k * NT + j_ * GT + gg) * 32 +: 32] <= {hb[j_ * 2 * NV + n_hs * NV + nv_i][16 * (4 * gg + k) +: 16], 16'h0000};
    end
    wire [DM:0] vm;
    ot_hdc_vline #(.D(DM)) u_vm (.clk(clk), .rst_n(rst_n), .v(mx_v), .vd(vm));
    wire [7:0] xi;
    ot_hdc_delay #(.W(8), .D(DM)) u_xi (.clk(clk), .rst_n(rst_n), .d(mx_i), .q(xi));
    wire x_v = vm[DM];
    wire [DS:0] vs;
    ot_hdc_vline #(.D(DS)) u_vs (.clk(clk), .rst_n(rst_n), .v(x_v), .vd(vs));
    wire [7:0] si;
    ot_hdc_delay #(.W(8), .D(DS)) u_si (.clk(clk), .rst_n(rst_n), .d(xi), .q(si));
    // scale sequencer: r lands -> vectors 0 .. NV-1, one a cycle
    reg [31:0] rh;
    reg        sc_run;
    reg [7:0]  sc_i;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin sc_run <= 1'b0; sc_i <= 8'd0; end
        else if (r_v) begin sc_run <= 1'b1; sc_i <= 8'd0; end
        else if (sc_run) begin if (sc_i == NV - 1) sc_run <= 1'b0; sc_i <= sc_i + 8'd1; end
    always @(posedge clk) if (r_v) rh <= r_d;
    reg b_v;
    always @(posedge clk or negedge rst_n) if (!rst_n) b_v <= 1'b0; else b_v <= sc_run;
    localparam integer DY = 2 * LM + 1;
    wire [DY:0] vy;
    ot_hdc_vline #(.D(DY)) u_vy (.clk(clk), .rst_n(rst_n), .v(b_v), .vd(vy));
    wire [7:0] wi, yi;
    ot_hdc_delay #(.W(8), .D(LM)) u_wi (.clk(clk), .rst_n(rst_n), .d(sc_i), .q(wi));
    reg  [7:0] bi;
    always @(posedge clk) bi <= sc_i;
    ot_hdc_delay #(.W(8), .D(DY)) u_yi (.clk(clk), .rst_n(rst_n), .d(bi), .q(yi));

    wire [NT-1:0]      lf;
    wire [NT*32-1:0]   sq, yb;
    localparam integer NC = HALF ? 4 : NT / 8;        // chunk sums of the tile (HALF: one a bank, the far half's real)
    wire [NC*32-1:0]   cs;
    wire [NC-1:0]      cf;
    genvar l, c, kk;
    generate
        for (l = 0; l < NT; l = l + 1) begin : g_lane
            wire [31:0] xl, xo, wo, p, qq;
            wire [3:0] f;
            ot_dsrom_su_norm_mix #(.LM(LM), .LA(LA)) u_mix (.clk(clk), .rst_n(rst_n), .v(mx_v),
                .h0(mx_x[(0 * NT + l) * 32 +: 32]), .h1(mx_x[(1 * NT + l) * 32 +: 32]),
                .h2(mx_x[(2 * NT + l) * 32 +: 32]), .h3(mx_x[(3 * NT + l) * 32 +: 32]), .pre(cf_pre[n_cs]), .x(xl),
                .fault(f[0]));
            reg [31:0] xb [0:NV-1];
            reg [31:0] xo_r, wo_r, yr;
            always @(posedge clk) if (x_v) xb[xi] <= xl;
            always @(posedge clk) xo_r <= xb[sc_i];
            always @(posedge clk) wo_r <= gtab[n_gs * NV + wi][32 * l +: 32];
            assign xo = xo_r;
            assign wo = wo_r;
            ot_hdc_qmul_lat #(LM) u_sq (clk, rst_n, x_v, xl, xl, sq[l * 32 +: 32], f[1]);
            ot_hdc_qmul_lat #(LM) u_xr (clk, rst_n, b_v, xo, rh, p, f[2]);
            ot_hdc_qmul_lat #(LM) u_w  (clk, rst_n, vy[LM], wo, p, qq, f[3]);
            always @(posedge clk) yr <= bf16(qq);
            assign yb[l * 32 +: 32] = yr;
            assign lf[l] = |f;
        end
        if (!HALF) begin : g_full
        for (c = 0; c < NT / 8; c = c + 1) begin : g_chunk
            wire [31:0] acc [0:7];
            wire [7:0] f;
            assign acc[0] = sq[(8 * c) * 32 +: 32];
            assign f[0] = 1'b0;
            for (kk = 1; kk < 8; kk = kk + 1) begin : g_j
                wire [31:0] sd;
                ot_hdc_delay #(.W(32), .D(LA * (kk - 1))) u_sd (.clk(clk), .rst_n(rst_n), .d(sq[(8 * c + kk) * 32 +: 32]), .q(sd));
                ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, vs[LM + LA * (kk - 1)], acc[kk - 1], sd, acc[kk], f[kk]);
            end
            assign cs[c * 32 +: 32] = acc[7];
            assign cf[c] = |f;
        end
        always @(posedge clk) cy_out <= 128'd0;
        end else begin : g_half
        // one master for both halves (the half is the strap tid[0]): 4 adders a bank, run as chain positions 1..3 (near
        // half: acc = lane 0, + lanes 1, 2, 3; the running sum leaves south as cy_out) or 4..7 (far half: the near
        // half's running sum, one forward hop late = exactly this tile's lane-4 time, + lanes 0..3 = chunk lanes 4..7)
        wire         far = tid[0];
        wire [127:0] cyd;
        reg  [127:0] cyq;
        always @(posedge clk) cyq <= cy_in;
        ot_hdc_delay #(.W(128), .D(RLY)) u_cy (.clk(clk), .rst_n(rst_n), .d(cyq), .q(cyd));
        for (c = 0; c < 4; c = c + 1) begin : g_chunk
            wire [31:0] acc [0:4];
            wire [4:0]  f;
            assign f[0] = 1'b0;
            assign acc[0] = far ? cyd[32 * c +: 32] : sq[(4 * c) * 32 +: 32];
            for (kk = 0; kk < 4; kk = kk + 1) begin : g_j
                // near: adder kk = position kk + 1, operand lane kk + 1, fires at LM + LA kk
                // far:  adder kk = position kk + 4, operand lane kk,     fires at LM + LA (kk + 3)
                wire [31:0] dn, df;
                if (kk < 3) begin : g_n
                    ot_hdc_delay #(.W(32), .D(LA * kk)) u_dn (.clk(clk), .rst_n(rst_n), .d(sq[(4 * c + kk + 1) * 32 +: 32]), .q(dn));
                end else begin : g_nn
                    assign dn = 32'd0;
                end
                ot_hdc_delay #(.W(32), .D(LA * (kk + 3))) u_df (.clk(clk), .rst_n(rst_n), .d(sq[(4 * c + kk) * 32 +: 32]), .q(df));
                wire fire = far ? vs[LM + LA * (kk + 3)] : (kk < 3 ? vs[LM + LA * kk] : 1'b0);
                ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, fire, acc[kk], far ? df : dn, acc[kk + 1], f[kk + 1]);
            end
            assign cs[c * 32 +: 32] = acc[4];
            assign cf[c] = |f;
            always @(posedge clk) cy_out[32 * c +: 32] <= acc[3];
        end
        end
    endgenerate
    // per-bank subtree over the tile's GS/8 chunks of the bank (chunks of bank j: j*GS/8 .. j*GS/8 + GS/8 - 1)
    wire [31:0] tv [0:LTB][0:NC-1];
    wire [LTB:0] tf;
    generate
        for (c = 0; c < NC; c = c + 1) begin : g_t0
            assign tv[0][c] = cs[c * 32 +: 32];
        end
        assign tf[0] = 1'b0;
        for (kk = 1; kk <= LTB; kk = kk + 1) begin : g_tl
            wire [(NC >> kk)-1:0] f;
            for (c = 0; c < (NC >> kk); c = c + 1) begin : g_tn
                ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, vs[LM + 7 * LA + LA * (kk - 1)], tv[kk - 1][2 * c],
                                               tv[kk - 1][2 * c + 1], tv[kk][c], f[c]);
            end
            for (c = (NC >> kk); c < NC; c = c + 1) begin : g_tz
                assign tv[kk][c] = 32'd0;
            end
            assign tf[kk] = |f;
        end
    endgenerate
    reg [127:0] psb [0:NV-1];
    always @(posedge clk) if (vs[DS]) psb[si] <= {tv[LTB][3], tv[LTB][2], tv[LTB][1], tv[LTB][0]};
    reg [NT*16-1:0] ybuf [0:NV-1];
    always @(posedge clk) if (vy[DY]) for (q = 0; q < NT; q = q + 1) ybuf[yi][16 * q +: 16] <= yb[32 * q + 16 +: 16];

    // ------------------------------------------------------------------ far tile: return slot origination
    reg        po_v;  reg [7:0] po_i;
    always @(posedge clk or negedge rst_n) if (!rst_n) po_v <= 1'b0; else po_v <= vs[DS] && last;
    always @(posedge clk) po_i <= si;
    reg  y_d1;
    always @(posedge clk or negedge rst_n) if (!rst_n) y_d1 <= 1'b0; else y_d1 <= vy[DY];
    reg [7:0]  oq_rdy, o_v;
    reg [15:0] o_r, hs_c;
    reg        hs_run, hs_sl;
    reg  [S_RT-1:0]    g_v, g_t;
    reg  [8*S_RT-1:0]  g_i;
    reg  [16*S_RT-1:0] g_q;
    always @(*) begin
        g_v = 0; g_t = 0; g_i = 0; g_q = 0;
        if (last) begin
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
    always @(posedge clk) if (hs_v) hs_sl <= fd[O_HS];

    // ------------------------------------------------------------------ return: pin flops, merge, relay
    reg [S_RT+3:0] rvq, rvm;
    reg [RDW-1:0]  rdq, rdm;
    wire [S_RT+3:0] rvm_d;
    wire [RDW-1:0]  rdm_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rvq <= 0; rvm <= 0; rv_out <= 0; end
        else begin
            rvq <= rv_in;
            rvm[S_RT-1:0] <= last ? g_v : rvq[S_RT-1:0];
            rvm[S_RT]     <= last ? po_v : rvq[S_RT];
            rvm[S_RT+1]   <= (last && hp_out_v) | (!last && rvq[S_RT+1]);
            rvm[S_RT+2]   <= rvq[S_RT+2] | hp_fault | (|lf) | (|cf) | (|tf);
            rvm[S_RT+3]   <= rvq[S_RT+3] | (hp_out_v & nz);
            rv_out <= rvm_d;
        end
    always @(posedge clk) begin : mrg
        reg [RDW-1:0] o;
        reg [S_RT-1:0] vv;
        o = last ? {RDW{1'b0}} : rdq;
        vv = last ? g_v : rvq[S_RT-1:0];
        if (last) begin o[P_T +: S_RT] = g_t; o[P_I +: 8 * S_RT] = g_i; o[P_Q +: 16 * S_RT] = g_q; o[P_PI +: 8] = po_i; end
        // partial packet: shift up one slot, insert mine at slot 0 (tile p of the chain ends at slot p)
        if ((last ? po_v : rvq[S_RT]) && (!HALF || tid[0])) begin                       // HALF: the far half owns the slot
            if (NP > 1) o[P_D + 128 +: (NP > 1 ? NP - 1 : 1) * 128] = o[P_D +: (NP > 1 ? NP - 1 : 1) * 128];
            o[P_D +: 128] = psb[o[P_PI +: 8]];
        end
        for (s = 0; s < S_RT; s = s + 1)
            if (vv[s]) begin : sl
                reg [7:0] vi;
                reg [15:0] qx, g, g0, b;
                reg [NT*16-1:0] yr;
                reg [RWT-1:0] hr;
                vi = o[P_I + 8 * s +: 8]; qx = o[P_Q + 16 * s +: 16];
                if (!o[P_T + s]) begin                                       // y row qx: lanes 32 qx .. 32 qx + 31
                    yr = ybuf[vi];                                           // one row read a slot
                    g = ((32 * qx) % NG) / GT; b = (32 * qx) / NG;            // first tile-group, lane quadrant
                    for (k = 0; k < 32; k = k + 1)
                        for (qd = 0; qd < N / NG; qd = qd + 1)
                            // NG >= 32: the row sits in one quadrant; NG < 32 (32 % NG == 0): lane k is group k % NG
                            // of quadrant 32 qx / NG + k / NG
                            if ((NG >= 32 ? g + k / GT : (k % NG) / GT) == tid && (NG >= 32 ? b : b + k / NG) == qd)
                                o[P_D + 512 * s + 16 * k +: 16] = yr[16 * (qd * GT + k % GT) +: 16];
                end else begin                                               // h row qx: 8 groups of resident row b
                    g0 = ((8 * qx) % NG) / 8; b = (8 * qx) / NG;
                    hr = hb[(b % 4) * 2 * NV + hs_sl * NV + b / 4];          // one row read a slot
                    for (k = 0; k < 8; k = k + 1)
                        if (g0 * (8 / GT) + k / GT == tid)
                            o[P_D + 512 * s + 64 * k +: 64] = hr[64 * (k % GT) +: 64];
                end
            end
        rdq <= rd_in;
        rdm <= o;
        rd_out <= rdm_d;
    end
    ot_hdc_delay #(.W(S_RT + 4), .D(RLY - 1), .RESET(1)) u_rvr (.clk(clk), .rst_n(rst_n), .d(rvm), .q(rvm_d));
    ot_hdc_delay #(.W(RDW), .D(RLY - 1)) u_rdr (.clk(clk), .rst_n(rst_n), .d(rdm), .q(rdm_d));
endmodule
