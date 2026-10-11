`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_tile (s81-suhc-hier-1011, 2026-10-11): ONE replicated hardened row-group tile of the hierarchical S81 HC
// slab (ot_s81_hc_hier).  The slab is KT identical tiles in a column; tile t owns element groups g = t*G .. t*G+G-1
// (G = NG / KT) of every resident row, i.e. lanes l = j*NG + t*G + gl (bank j = 0..3, gl < G) of every norm vector:
//   - the resident h of its groups (2 job slots x NR rows x G groups x 4 copies BF16; no reset),
//   - its hc_post groups (ot_dsrom_su_hcpost, NG = G) writing back in place,
//   - its 4G norm lanes: hc_pre mix -> square -> 8-element chunk chains -> the per-bank subtree over its G/8 chunks
//     (an aligned subtree of the golden pairwise tree: G a power of two, chunks never straddle tiles), the x wait
//     line, the gain slice, the scale y = bf16(w * (x * r)) and the FP8 act-quant of its 32-lane blocks (G % 32 == 0:
//     every quant block is tile-local),
//   - the coefficient words of both slots (broadcast copy).
// The tile is driven by ONE forward bus (fv valid bits / fd data, the root's commands and VM response rows), relayed
// tile to tile (fwd_out = this tile's pin flop: a registered feed-through), and contributes to ONE return packet bus
// relayed from the far tile (KT-1) toward the root (ret_out = the registered merge).  The far tile ORIGINATES the
// return slots (partial-sum packets per norm vector; VM row slots of norm outputs / h stores); every tile ORs its own
// pieces into the slots that pass it.  The far tile is the latest tile (commands reach it last), so every nearer tile
// has its pieces buffered when a slot passes.  Strap tid = tile index (tied off by the slab; tiles are identical).
// Reset: rst_in is relayed (two flops, no reset) to this tile's logic and to rst_out; datapath registers have no reset.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_tile #(
    parameter integer NG = 256, D = 5120, KT = 8, S_RD = 2, S_WR = 8, WIN = 2, WOUT = 2, ML = 5, AL = 4
) (
    input  wire                       clk,
    input  wire                       rst_in,
    output wire                       rst_out,
    input  wire [7:0]                 tid,
    input  wire [S_RD+4:0]            fv_in,
    input  wire [FDW-1:0]             fd_in,
    output wire [S_RD+4:0]            fv_out,
    output wire [FDW-1:0]             fd_out,
    input  wire [G*32-1:0]            y_in,       // this tile's y slice (aligned with fd_in)
    input  wire [S_WR+3:0]            rv_in,
    input  wire [RDW-1:0]             rd_in,
    output reg  [S_WR+3:0]            rv_out,
    output reg  [RDW-1:0]             rd_out
);
    localparam integer G    = NG / KT;
    localparam integer N    = 4 * NG;
    localparam integer NT   = 4 * G;                 // norm lanes of the tile
    localparam integer NR   = D / NG;
    localparam integer NV   = D / N;
    localparam integer PPR  = NG / 8;
    localparam integer RWT  = G * 64;               // tile resident row bits
    localparam integer NBT  = NT / 32;              // quant blocks of the tile
    localparam integer BPB  = NG / 32;              // quant blocks of a bank (global)
    localparam integer GB   = G / 32;               // quant blocks of a bank in the tile
    localparam integer LTB  = $clog2(G / 8);        // per-bank subtree levels
    localparam integer CROWS = N / 64;
    localparam integer EROWS = (N + 1023) / 1024;
    localparam integer YROWS = N / 32;
    localparam integer HROWS = NR * NG / 8;
    localparam integer LM = ML, LA = AL;
    localparam integer DM = LM + 3 * LA + 1;        // mix
    localparam integer DS = LM + 7 * LA + LTB * LA; // square + chain + subtree
    // ---- forward bus layout (ot_s81_hc_hier / ot_s81_hc_hroot use the same)
    localparam integer O_RK = 0, O_RS = 2, O_RG = 3, O_RC = 5, O_RD = O_RC + S_RD * 16, O_PB = O_RD + S_RD * 512,
                       O_NG = O_PB + 12, O_NV = O_NG + 6, O_R = O_NV + 8, O_HS = O_R + 32, FDW = O_HS + 1;
    // ---- return bus layout
    localparam integer P_T = 0, P_I = 2 * S_WR, P_Q = P_I + 8 * S_WR, P_D = P_Q + 16 * S_WR, P_PI = P_D + 512 * S_WR,
                       P_PD = P_PI + 8, RDW = P_PD + KT * 128;
`ifndef SYNTHESIS
    initial begin
        if (G % 32 != 0 || (G & (G - 1)) != 0 || (KT & (KT - 1)) != 0) $fatal(1, "ot_s81_hc_tile: G a power of two >= 32, KT a power of two");
        if (D % N != 0) $fatal(1, "ot_s81_hc_tile: D a multiple of 4 NG");
    end
`endif
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] s;
        begin s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]}; bf16 = {s[31:16], 16'd0}; end
    endfunction

    // ------------------------------------------------------------------ reset relay, pin flops
    reg [1:0] rr;
    always @(posedge clk) rr <= {rr[0], rst_in};
    wire rst_n = rr[1];
    assign rst_out = rr[1];
    reg [S_RD+4:0] fv;
    reg [FDW-1:0]  fd;
    reg [G*32-1:0] yq;
    always @(posedge clk or negedge rst_n) if (!rst_n) fv <= 0; else fv <= fv_in;
    always @(posedge clk) begin fd <= fd_in; yq <= y_in; end
    assign fv_out = fv;
    assign fd_out = fd;
    reg [S_WR+3:0] rvq;
    reg [RDW-1:0]  rdq;
    always @(posedge clk or negedge rst_n) if (!rst_n) rvq <= 0; else rvq <= rv_in;
    always @(posedge clk) rdq <= rd_in;
    wire last = (tid == KT - 1);

    wire [S_RD-1:0] rd_v = fv[S_RD-1:0];
    wire pb_v = fv[S_RD], ng_v = fv[S_RD+1], nv_v = fv[S_RD+2], r_v = fv[S_RD+3], hs_v = fv[S_RD+4];
    wire [1:0] rd_k = fd[O_RK +: 2];
    wire       rd_s = fd[O_RS];
    wire [1:0] rd_g = fd[O_RG +: 2];
    wire pb_go = fd[O_PB], pb_wb = fd[O_PB + 1], pb_hs = fd[O_PB + 2], pb_cs = fd[O_PB + 3];
    wire [7:0] pb_b = fd[O_PB + 4 +: 8];
    wire [7:0] nv_i = fd[O_NV +: 8];
    wire [31:0] r_d = fd[O_R +: 32];

    // ------------------------------------------------------------------ resident state (no reset)
    reg [RWT-1:0]   hb [0:8*NV-1];                     // bank j, index i at j*2NV + i
    reg [16*32-1:0] cf_comb [0:1];
    reg [4*32-1:0]  cf_pre  [0:1];
    reg [4*32-1:0]  cf_post [0:1];
    reg [31:0]      cf_eps  [0:1];
    reg [NT*32-1:0] gtab [0:4*NV-1];

    // ------------------------------------------------------------------ VM response rows (H_LOAD 0 / GAIN 1 / COEF 2)
    integer s, k, q, b_, j_, gg;
    always @(posedge clk) begin
        for (s = 0; s < S_RD; s = s + 1)
            if (rd_v[s]) begin : one
                reg [15:0] c;
                reg [15:0] g0, l0, rb;
                c = fd[O_RC + 16 * s +: 16];
                if (rd_k == 2'd0) begin
                    rb = c / PPR; g0 = 8 * (c % PPR);
                    if (g0 / G == tid)
                        hb[(rb % 4) * 2 * NV + rd_s * NV + rb / 4][64 * (g0 % G) +: 512] <= fd[O_RD + 512 * s +: 512];
                end else if (rd_k == 2'd1) begin
                    l0 = (16 * c) % N; g0 = l0 % NG;
                    if (g0 / G == tid)
                        gtab[rd_g * NV + (16 * c) / N][32 * ((l0 / NG) * G + g0 % G) +: 512] <= fd[O_RD + 512 * s +: 512];
                end else if (rd_k == 2'd2) begin
                    if (c == 0) cf_comb[rd_s] <= fd[O_RD + 512 * s +: 512];
                    else begin
                        cf_pre[rd_s]  <= fd[O_RD + 512 * s +: 128];
                        cf_post[rd_s] <= fd[O_RD + 512 * s + 128 +: 128];
                        cf_eps[rd_s]  <= fd[O_RD + 512 * s + 256 +: 32];
                    end
                end
            end
    end

    // ------------------------------------------------------------------ hc_post (G groups), write back in place
    reg              hp_go, hp_in_v;
    reg [G*4*32-1:0] hp_r;
    reg [G*32-1:0]   hp_y;
    reg [16*32-1:0]  hp_comb;
    reg [4*32-1:0]   hp_post;
    wire             hp_out_v, hp_fault;
    wire [G*4*32-1:0] hp_out;
    ot_dsrom_su_hcpost #(.NG(G), .WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL)) u_post (
        .clk(clk), .rst_n(rst_n), .go(hp_go), .comb(hp_comb), .post(hp_post), .in_v(hp_in_v), .in_r(hp_r), .in_y(hp_y),
        .out_v(hp_out_v), .out_d(hp_out), .fault(hp_fault));
    reg        p_wb, p_hs;
    reg [7:0]  p_ob;
    always @(posedge clk or negedge rst_n) if (!rst_n) hp_in_v <= 1'b0; else hp_in_v <= pb_v;
    always @(posedge clk) begin
        hp_go <= pb_v && pb_go;
        if (pb_v) begin
            for (q = 0; q < 4 * G; q = q + 1) hp_r[32 * q +: 32] <= {hb[(pb_b % 4) * 2 * NV + pb_hs * NV + pb_b / 4][16 * q +: 16], 16'h0000};
            hp_y <= yq; hp_comb <= cf_comb[pb_cs]; hp_post <= cf_post[pb_cs];
            if (pb_go) begin p_wb <= pb_wb; p_hs <= pb_hs; p_ob <= 8'd0; end
        end
        if (hp_out_v) begin
            if (p_wb)
                for (q = 0; q < 4 * G; q = q + 1) hb[(p_ob % 4) * 2 * NV + p_hs * NV + p_ob / 4][16 * q +: 16] <= hp_out[32 * q + 16 +: 16];
            p_ob <= p_ob + 8'd1;
        end
    end
    reg nz;                                              // hc_post output not BF16 (lower half nonzero)
    always @(*) begin nz = 1'b0; for (q = 0; q < 4 * G; q = q + 1) nz = nz | (|hp_out[32 * q +: 16]); end

    // ------------------------------------------------------------------ norm: job state
    reg       n_hs, n_cs, n_fq, n_fy;
    reg [1:0] n_gs;
    always @(posedge clk) if (ng_v) begin
        n_hs <= fd[O_NG]; n_cs <= fd[O_NG + 1]; n_gs <= fd[O_NG + 2 +: 2]; n_fq <= fd[O_NG + 4]; n_fy <= fd[O_NG + 5];
    end
    // operand read: the four banks' rows at index v (lane lj = j*G + gl, copy k)
    reg            mx_v;
    reg [7:0]      mx_i;
    reg [4*NT*32-1:0] mx_x;
    always @(posedge clk or negedge rst_n) if (!rst_n) mx_v <= 1'b0; else mx_v <= nv_v;
    always @(posedge clk) if (nv_v) begin
        mx_i <= nv_i;
        for (j_ = 0; j_ < 4; j_ = j_ + 1)
            for (gg = 0; gg < G; gg = gg + 1)
                for (k = 0; k < 4; k = k + 1)
                    mx_x[(k * NT + j_ * G + gg) * 32 +: 32] <= {hb[j_ * 2 * NV + n_hs * NV + nv_i][16 * (4 * gg + k) +: 16], 16'h0000};
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
    // stage A (sc_run, sc_i): x read; stage B (a cycle later): x * r; w read LM cycles after A
    reg        b_v;
    always @(posedge clk or negedge rst_n) if (!rst_n) b_v <= 1'b0; else b_v <= sc_run;
    localparam integer DY = 2 * LM + 1;             // B -> y register
    wire [DY:0] vy;
    ot_hdc_vline #(.D(DY)) u_vy (.clk(clk), .rst_n(rst_n), .v(b_v), .vd(vy));
    wire [7:0] wi, yi;
    ot_hdc_delay #(.W(8), .D(LM)) u_wi (.clk(clk), .rst_n(rst_n), .d(sc_i), .q(wi));
    reg  [7:0] bi;
    always @(posedge clk) bi <= sc_i;
    ot_hdc_delay #(.W(8), .D(DY)) u_yi (.clk(clk), .rst_n(rst_n), .d(bi), .q(yi));

    wire [NT-1:0]    lf;
    wire [NT*32-1:0] sq, yb;
    wire [NT/8*32-1:0] cs;
    wire [NT/8-1:0]  cf;
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
    endgenerate
    // per-bank subtree over the tile's G/8 chunks of the bank (chunks of bank j: j*G/8 .. j*G/8 + G/8 - 1)
    localparam integer NC = NT / 8;
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
    // the 4 bank partials of vector si (valid vs[DS]) -> partial buffer
    reg [127:0] psb [0:NV-1];
    always @(posedge clk) if (vs[DS]) psb[si] <= {tv[LTB][3], tv[LTB][2], tv[LTB][1], tv[LTB][0]};

    // FP8 act-quant of the tile's 32-lane blocks (local block lb = j*GB + gl/32)
    wire [NBT*256-1:0] qc;
    wire [NBT*10-1:0]  qe;
    wire [NBT-1:0]     qvo, qf;
    wire [7:0]         qi;
    generate for (kk = 0; kk < NBT; kk = kk + 1) begin : g_aq
        wire signed [9:0] e;
        wire [511:0] unused_y;
        ot_dsrom_aq12 u_aq (.clk(clk), .rst_n(rst_n), .v(vy[DY]), .x(yb[kk * 1024 +: 1024]), .vo(qvo[kk]),
                            .q(qc[kk * 256 +: 256]), .e(e), .y(unused_y), .fault(qf[kk]));
        assign qe[kk * 10 +: 10] = e;
    end endgenerate
    ot_hdc_delay #(.W(8), .D(18)) u_qi (.clk(clk), .rst_n(rst_n), .d(yi), .q(qi));
    // output buffers by vector: y BF16, codes, exps
    reg [NT*16-1:0]  ybuf [0:NV-1];
    reg [NBT*256-1:0] cbuf [0:NV-1];
    reg [NBT*10-1:0] ebuf [0:NV-1];
    always @(posedge clk) begin
        if (vy[DY]) for (q = 0; q < NT; q = q + 1) ybuf[yi][16 * q +: 16] <= yb[32 * q + 16 +: 16];
        if (qvo[0]) begin cbuf[qi] <= qc; ebuf[qi] <= qe; end
    end

    // ------------------------------------------------------------------ far tile: return slot origination
    // partial packets: a cycle after its partial of v is buffered; row slots: norm rows of v a cycle after its quant
    // of v is buffered (codes CROWS + exps EROWS when QUANT, y YROWS when YOUT), h store rows on hs_v.
    reg        po_v;  reg [7:0] po_i;
    always @(posedge clk or negedge rst_n) if (!rst_n) po_v <= 1'b0; else po_v <= vs[DS] && last;
    always @(posedge clk) po_i <= si;
    reg [7:0]  oq_rdy;                                   // norm vectors with outputs buffered (far tile)
    reg [7:0]  o_v;                                      // vector being emitted
    reg [15:0] o_r;                                      // row within the vector's emission
    reg        hs_run;
    reg [15:0] hs_c;
    reg        hs_sl;
    localparam integer RPV_MAX = CROWS + EROWS + YROWS;
    wire [15:0] rpv = (n_fq ? CROWS + EROWS : 0) + (n_fy ? YROWS : 0);
    reg  [S_WR-1:0]    g_v;
    reg  [2*S_WR-1:0]  g_t;
    reg  [8*S_WR-1:0]  g_i;
    reg  [16*S_WR-1:0] g_q;
    always @(*) begin
        g_v = 0; g_t = 0; g_i = 0; g_q = 0;
        if (last) begin
            if (hs_run) begin
                for (s = 0; s < S_WR; s = s + 1)
                    if (hs_c + s < HROWS) begin g_v[s] = 1'b1; g_t[2 * s +: 2] = 2'd3; g_q[16 * s +: 16] = hs_c + s; end
            end else if (o_v < oq_rdy) begin
                for (s = 0; s < S_WR; s = s + 1) begin : em
                    reg [15:0] r;
                    r = o_r + s;
                    if (r < rpv) begin
                        g_v[s] = 1'b1; g_i[8 * s +: 8] = o_v;
                        if (n_fq && r < CROWS) begin g_t[2 * s +: 2] = 2'd0; g_q[16 * s +: 16] = r; end
                        else if (n_fq && r < CROWS + EROWS) begin g_t[2 * s +: 2] = 2'd1; g_q[16 * s +: 16] = r - CROWS; end
                        else begin g_t[2 * s +: 2] = 2'd2; g_q[16 * s +: 16] = r - (n_fq ? CROWS + EROWS : 0); end
                    end
                end
            end
        end
    end
    reg q_last;
    always @(posedge clk or negedge rst_n) if (!rst_n) q_last <= 1'b0; else q_last <= qvo[0];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin oq_rdy <= 0; o_v <= 0; o_r <= 0; hs_run <= 1'b0; hs_c <= 0; end
        else begin
            if (ng_v) begin oq_rdy <= 0; o_v <= 0; o_r <= 0; end
            else begin
                if (q_last) oq_rdy <= oq_rdy + 8'd1;
                if (!hs_run && o_v < oq_rdy) begin
                    if (o_r + S_WR >= rpv) begin o_r <= 0; o_v <= o_v + 8'd1; end
                    else o_r <= o_r + S_WR;
                end
            end
            if (hs_v) begin hs_run <= 1'b1; hs_c <= 0; end
            else if (hs_run) begin hs_c <= hs_c + S_WR; if (hs_c + S_WR >= HROWS) hs_run <= 1'b0; end
        end
    end
    always @(posedge clk) if (hs_v) hs_sl <= fd[O_HS];

    // ------------------------------------------------------------------ merge: base slots (originated or passing) | mine
    // global quant block B (row-local position) -> mine? and the local block index
    function automatic is_mine(input [15:0] B);
        is_mine = ((B % BPB) / GB) == tid;
    endfunction
    function automatic [7:0] lblk(input [15:0] B);
        lblk = (B / BPB) * GB + (B % GB);
    endfunction
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rv_out <= 0;
        else begin
            rv_out[S_WR-1:0] <= last ? g_v : rvq[S_WR-1:0];
            rv_out[S_WR]     <= last ? po_v : rvq[S_WR];
            rv_out[S_WR+1]   <= (last && hp_out_v) | (!last && rvq[S_WR+1]);
            rv_out[S_WR+2]   <= rvq[S_WR+2] | hp_fault | (|lf) | (|cf) | (|tf) | (|qf);
            rv_out[S_WR+3]   <= rvq[S_WR+3] | (hp_out_v & nz);
        end
    end
    always @(posedge clk) begin : mrg
        reg [RDW-1:0] o;
        reg [S_WR-1:0] vv;
        reg [7:0] pi;
        o = last ? {RDW{1'b0}} : rdq;
        vv = last ? g_v : rvq[S_WR-1:0];
        if (last) begin
            o[P_T +: 2 * S_WR] = g_t; o[P_I +: 8 * S_WR] = g_i; o[P_Q +: 16 * S_WR] = g_q; o[P_PI +: 8] = po_i;
        end
        // partial packet: my slot
        pi = o[P_PI +: 8];
        if (last ? po_v : rvq[S_WR]) o[P_PD + 128 * tid +: 128] = psb[pi];
        // row slots
        for (s = 0; s < S_WR; s = s + 1)
            if (vv[s]) begin : sl
                reg [1:0] t;
                reg [7:0] vi;
                reg [15:0] qx, B, g0;
                reg [511:0] dd;
                t = o[P_T + 2 * s +: 2]; vi = o[P_I + 8 * s +: 8]; qx = o[P_Q + 16 * s +: 16];
                dd = o[P_D + 512 * s +: 512];
                case (t)
                    2'd0: for (k = 0; k < 2; k = k + 1) begin
                              B = 2 * qx + k;
                              if (is_mine(B)) dd[256 * k +: 256] = cbuf[vi][256 * lblk(B) +: 256];
                          end
                    2'd1: for (k = 0; k < 32; k = k + 1) begin
                              B = 32 * qx + k;
                              if (B < N / 32 && is_mine(B)) dd[16 * k +: 16] = {6'd0, ebuf[vi][10 * lblk(B) +: 10]};
                          end
                    2'd2: begin
                              B = qx;
                              if (is_mine(B)) dd = ybuf[vi][512 * lblk(B) +: 512];
                          end
                    default: begin
                              g0 = (8 * qx) % NG;
                              if (g0 / G == tid)
                                  dd = hb[(((8 * qx) / NG) % 4) * 2 * NV + hs_sl * NV + ((8 * qx) / NG) / 4][64 * (g0 % G) +: 512];
                          end
                endcase
                o[P_D + 512 * s +: 512] = dd;
            end
        rd_out <= o;
    end
endmodule
