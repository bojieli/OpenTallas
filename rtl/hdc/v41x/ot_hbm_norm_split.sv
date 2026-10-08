`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HBM norm engine, PARTITIONED (stream hbm-norm-split 2026-10-08).  The flat N64 / D5120 / HC1 / QUANT1 engine view
// (ot_hbm_norm_engine_view = ot_dsrom_su_norm MEM=1 behind pin flops) synthesises to ~3.75-4.5M cells and places in
// 8-12 h.  Following "replicate hardened elements sized to the goal", it is split into
//   ot_hbm_norm_grp   : a G-lane group (G = 8 or 16), the hardened, replicated element: per lane the hc_pre mix,
//                       the square, the scale (x*r, w*(x*r)) and the BF16 output register; per 8 lanes the chunk
//                       chain and one x / one gain SRAM macro; the in-group part of the chunk-sum tree.  Every input
//                       pin lands in a flop, every output pin leaves a flop.
//   ot_hbm_norm_split_view : the thin top: input capture flops, N/G groups, the remaining log2(N/G) chunk-tree levels,
//                       the vector-level tree, the scalar tail (divide by D, + eps, rsqrt), the rstd broadcast, the
//                       FP8 act-quant (32-lane blocks span groups), output flops, the sticky fault.
// Arithmetic and association order are exactly ot_dsrom_su_norm's (the golden's): the group tree is an aligned
// subtree of the in-vector pairwise tree, the top finishes the same tree.  Pipeline: the two pin flops on the result
// path (group output, top input) are taken out of the RW result-wire stages and the two on the broadcast path (top
// output, group input) out of the BW broadcast-wire stages, so the reduction / broadcast loop is cycle-identical to
// the flat engine.  Added latency vs the flat view: +1 on every output (the top's input capture flops in front of the
// group pin flops) and +1 more on the act-quant outputs (q is fed from the top's y output flops): r/y +1, q +2;
// throughput unchanged (one vector a cycle).
// Constraints: HC = 1, RD = 0, MEM = 1, FREG = 1 (the HBM view's selection), D a multiple of N, NV <= 128.
// ---------------------------------------------------------------------------
module ot_hbm_norm_grp #(
    parameter integer G = 8,            // lanes in the group (multiple of 8)
    parameter integer D = 5120,
    parameter integer N = 64,           // lanes of the whole engine (sets NV)
    parameter integer LM = 5,
    parameter integer LA = 6,
    parameter integer SXC = 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 go,
    input  wire                 in_v,
    input  wire [4*G*32-1:0]    in_x,       // copy k of local lane l at [(k*G + l)*32 +: 32]
    input  wire [127:0]         pre,
    input  wire                 wl_v,
    input  wire [7:0]           wl_i,
    input  wire [G*32-1:0]      wl_d,
    input  wire                 rb_v,       // rstd broadcast (the flat engine's rbw[32], one stage before rh)
    input  wire [31:0]          rb_d,
    output wire                 s_v,        // group partial of the in-vector chunk-sum tree, one per vector
    output wire [7:0]           s_i,
    output wire [31:0]          s,
    output wire                 y_v,
    output wire [7:0]           y_i,
    output wire [G*32-1:0]      y,
    output wire                 gf          // any fault this cycle (lanes, chains, group tree)
);
    localparam integer NV  = D / N;
    localparam integer NC  = G / 8;
    localparam integer LT  = $clog2(NC);
    localparam integer DM  = LM + 3 * LA + 1;
    localparam integer DS  = LM + 7 * LA + LT * LA;
    localparam integer LMS = LM + SXC;
    localparam integer DY  = 2 * LMS + 1;
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] t;
        begin
            t = {1'b0, x} + 33'h7FFF + {32'd0, x[16]};
            bf16 = {t[31:16], 16'd0};
        end
    endfunction
    // reset: asynchronous assert, synchronous release (two flops)
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rstn = rs[1];
    // input pin flops
    reg go_c, in_v_c, wl_v_c, rb_v_c; reg [7:0] wl_i_c; reg [4*G*32-1:0] x_c; reg [127:0] pre_c;
    reg [G*32-1:0] wl_d_c; reg [31:0] rb_d_c;
    always @(posedge clk or negedge rstn)
        if (!rstn) begin go_c <= 1'b0; in_v_c <= 1'b0; wl_v_c <= 1'b0; rb_v_c <= 1'b0; end
        else begin go_c <= go; in_v_c <= in_v; wl_v_c <= wl_v; rb_v_c <= rb_v; end
    always @(posedge clk) begin
        wl_i_c <= wl_i; x_c <= in_x; pre_c <= pre; wl_d_c <= wl_d; rb_d_c <= rb_d;
    end

    // ---------------------------------------------------------------- control (ot_dsrom_su_norm, replicated per group)
    reg [7:0] in_i;
    always @(posedge clk or negedge rstn)
        if (!rstn) in_i <= 8'd0;
        else if (go_c) in_i <= 8'd0;
        else if (in_v_c) in_i <= in_i + 8'd1;
    wire [DM:0] vm;
    ot_hdc_vline #(.D(DM)) u_vm (.clk(clk), .rst_n(rstn), .v(in_v_c), .vd(vm));
    wire [7:0] xi;
    ot_hdc_delay #(.W(8), .D(DM)) u_xi (.clk(clk), .rst_n(rstn), .d(in_i), .q(xi));
    wire x_v = vm[DM];
    wire [DS:0] vs;
    ot_hdc_vline #(.D(DS)) u_vs (.clk(clk), .rst_n(rstn), .v(x_v), .vd(vs));
    wire [7:0] si;
    ot_hdc_delay #(.W(8), .D(DS)) u_si (.clk(clk), .rst_n(rstn), .d(xi), .q(si));
    // scale sequencer: rb_v_c is the flat engine's rbw[32]; rbv / rh its hold stage
    reg         rbv;
    reg  [31:0] rh;
    always @(posedge clk or negedge rstn) if (!rstn) rbv <= 1'b0; else rbv <= rb_v_c;
    always @(posedge clk) if (rb_v_c) rh <= rb_d_c;
    reg         sc_run;
    reg  [7:0]  sc_i;
    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin sc_run <= 1'b0; sc_i <= 8'd0; end
        else if (rbv) begin sc_run <= (NV > 1); sc_i <= 8'd1; end
        else if (sc_run) begin
            if (sc_i == NV - 1) sc_run <= 1'b0;
            sc_i <= sc_i + 8'd1;
        end
    end
    wire        sc_go = rbv || sc_run;
    wire [7:0]  sc_x  = rbv ? 8'd0 : sc_i;
    wire [7:0]  sc_nx = rbv ? 8'd1 : sc_run ? sc_i + 8'd1 : 8'd0;
    wire        sc_run_n = rbv ? (NV > 1) : (sc_run && sc_i != NV - 1);
    wire [7:0]  sc_i_n   = rbv ? 8'd1 : sc_run ? sc_i + 8'd1 : sc_i;
    wire [7:0]  sc_nn    = rb_v_c ? 8'd1 : sc_run_n ? sc_i_n + 8'd1 : 8'd0;
    wire [DY:0] vy;
    ot_hdc_vline #(.D(DY)) u_vy (.clk(clk), .rst_n(rstn), .v(sc_go), .vd(vy));
    wire [7:0] yi_mm, yi_o;
    ot_hdc_delay #(.W(8), .D(LMS > 1 ? LMS - 1 : 1)) u_yimm (.clk(clk), .rst_n(rstn), .d(sc_nx), .q(yi_mm));
    ot_hdc_delay #(.W(8), .D(DY)) u_yio (.clk(clk), .rst_n(rstn), .d(sc_x), .q(yi_o));

    // ---------------------------------------------------------------- lanes
    wire [G-1:0]    lf;
    wire [G*32-1:0] sq;
    wire [NC*32-1:0] cs;
    wire [NC-1:0]   cf;
    wire [G*32-1:0] xl_all, xmq, wmq;
    genvar l, c, k;
    generate
        for (c = 0; c < NC; c = c + 1) begin : g_m
            ot_sram_1r1w_128x256_m1_r2c2 u_x (.clk(clk), .r_ce_in(1'b1), .r_addr_in(sc_nn[6:0]),
                .rd_out(xmq[c * 256 +: 256]), .w_ce_in(x_v), .w_addr_in(xi[6:0]), .wd_in(xl_all[c * 256 +: 256]),
                .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
            ot_sram_1r1w_128x256_m1_r2c2 u_w (.clk(clk), .r_ce_in(1'b1), .r_addr_in(yi_mm[6:0]),
                .rd_out(wmq[c * 256 +: 256]), .w_ce_in(wl_v_c), .w_addr_in(wl_i_c[6:0]), .wd_in(wl_d_c[c * 256 +: 256]),
                .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
        for (l = 0; l < G; l = l + 1) begin : g_lane
            wire [31:0] xl;
            wire [9:0] f;
            ot_dsrom_su_norm_mix #(.LM(LM), .LA(LA)) u_mix (.clk(clk), .rst_n(rstn), .v(in_v_c),
                .h0(x_c[(0 * G + l) * 32 +: 32]), .h1(x_c[(1 * G + l) * 32 +: 32]),
                .h2(x_c[(2 * G + l) * 32 +: 32]), .h3(x_c[(3 * G + l) * 32 +: 32]), .pre(pre_c), .x(xl),
                .fault(f[0]));
            assign f[6:1] = 6'd0;
            assign xl_all[l * 32 +: 32] = xl;
            reg [31:0] xo, wo;                   // macro output registers
            always @(posedge clk) begin xo <= xmq[l * 32 +: 32]; wo <= wmq[l * 32 +: 32]; end
            ot_hdc_qmul_lat #(LM) u_sq (clk, rstn, x_v, xl, xl, sq[l * 32 +: 32], f[7]);
            wire [31:0] p, q;
            ot_hdc_qmul_lat #(LMS) u_xr (clk, rstn, sc_go, xo, rh, p, f[8]);
            ot_hdc_qmul_lat #(LMS) u_w  (clk, rstn, vy[LMS], wo, p, q, f[9]);
            reg [31:0] yr;
            always @(posedge clk) yr <= bf16(q);
            assign y[l * 32 +: 32] = yr;
            assign lf[l] = |f;
        end
        for (c = 0; c < NC; c = c + 1) begin : g_chunk
            wire [31:0] acc [0:7];
            wire [7:0] f;
            assign acc[0] = sq[(8 * c) * 32 +: 32];
            assign f[0] = 1'b0;
            for (k = 1; k < 8; k = k + 1) begin : g_j
                wire [31:0] sd;
                ot_hdc_delay #(.W(32), .D(LA * (k - 1))) u_sd (.clk(clk), .rst_n(rstn), .d(sq[(8 * c + k) * 32 +: 32]),
                                                              .q(sd));
                ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rstn, vs[LM + LA * (k - 1)], acc[k - 1], sd, acc[k], f[k]);
            end
            assign cs[c * 32 +: 32] = acc[7];
            assign cf[c] = |f;
        end
    endgenerate
    // in-group levels of the chunk-sum tree
    wire [31:0] tv [0:LT][0:NC-1];
    wire [LT:0] tf_any;
    generate
        for (c = 0; c < NC; c = c + 1) begin : g_t0
            assign tv[0][c] = cs[c * 32 +: 32];
        end
        assign tf_any[0] = 1'b0;
        for (k = 1; k <= LT; k = k + 1) begin : g_tl
            wire [(NC >> k)-1:0] f;
            for (c = 0; c < (NC >> k); c = c + 1) begin : g_tn
                ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rstn, vs[LM + 7 * LA + LA * (k - 1)], tv[k - 1][2 * c],
                                               tv[k - 1][2 * c + 1], tv[k][c], f[c]);
            end
            for (c = (NC >> k); c < NC; c = c + 1) begin : g_tz
                assign tv[k][c] = 32'd0;
            end
            assign tf_any[k] = |f;
        end
    endgenerate
    // ---------------------------------------------------------------- output pin flops
    reg s_v_o; reg [7:0] s_i_o; reg [31:0] s_o;
    reg [G-1:0] lf_r; reg gf_o;
    always @(posedge clk or negedge rstn)
        if (!rstn) begin s_v_o <= 1'b0; lf_r <= {G{1'b0}}; gf_o <= 1'b0; end
        else begin
            s_v_o <= vs[DS];
            lf_r <= go_c ? {G{1'b0}} : lf;
            gf_o <= go_c ? 1'b0 : ((|lf_r) || (|cf) || (|tf_any));
        end
    always @(posedge clk) begin s_i_o <= si; s_o <= tv[LT][0]; end
    assign s_v = s_v_o; assign s_i = s_i_o; assign s = s_o; assign gf = gf_o;
    assign y_v = vy[DY];
    assign y_i = yi_o;
endmodule

// The hardened group masters (fixed parameters: the module name is the macro name in the top's route).
module ot_hbm_norm_grp8 (
    input wire clk, input wire rst_n, input wire go, input wire in_v, input wire [4*8*32-1:0] in_x,
    input wire [127:0] pre, input wire wl_v, input wire [7:0] wl_i, input wire [8*32-1:0] wl_d,
    input wire rb_v, input wire [31:0] rb_d,
    output wire s_v, output wire [7:0] s_i, output wire [31:0] s, output wire y_v, output wire [7:0] y_i,
    output wire [8*32-1:0] y, output wire gf
);
    ot_hbm_norm_grp #(.G(8)) u (.clk(clk), .rst_n(rst_n), .go(go), .in_v(in_v), .in_x(in_x), .pre(pre), .wl_v(wl_v),
        .wl_i(wl_i), .wl_d(wl_d), .rb_v(rb_v), .rb_d(rb_d), .s_v(s_v), .s_i(s_i), .s(s), .y_v(y_v), .y_i(y_i), .y(y),
        .gf(gf));
endmodule

module ot_hbm_norm_grp16 (
    input wire clk, input wire rst_n, input wire go, input wire in_v, input wire [4*16*32-1:0] in_x,
    input wire [127:0] pre, input wire wl_v, input wire [7:0] wl_i, input wire [16*32-1:0] wl_d,
    input wire rb_v, input wire [31:0] rb_d,
    output wire s_v, output wire [7:0] s_i, output wire [31:0] s, output wire y_v, output wire [7:0] y_i,
    output wire [16*32-1:0] y, output wire gf
);
    ot_hbm_norm_grp #(.G(16)) u (.clk(clk), .rst_n(rst_n), .go(go), .in_v(in_v), .in_x(in_x), .pre(pre), .wl_v(wl_v),
        .wl_i(wl_i), .wl_d(wl_d), .rb_v(rb_v), .rb_d(rb_d), .s_v(s_v), .s_i(s_i), .s(s), .y_v(y_v), .y_i(y_i), .y(y),
        .gf(gf));
endmodule

// ---------------------------------------------------------------------------
// The partitioned engine view: same ports as ot_hbm_norm_engine_view.
// ---------------------------------------------------------------------------
module ot_hbm_norm_split_core #(
    parameter integer G = 8,
    parameter integer N = 64,
    parameter integer D = 5120,
    parameter integer LM = 5,
    parameter integer LA = 6,
    parameter integer RW = 9,
    parameter integer BW = 9
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 go,
    input  wire                 in_v,
    input  wire [4*N*32-1:0]    in_x,
    input  wire [127:0]         pre,
    input  wire [31:0]          n_f,
    input  wire [31:0]          eps,
    input  wire                 wl_v,
    input  wire [7:0]           wl_i,
    input  wire [N*32-1:0]      wl_d,
    input  wire [31:0]          cos_t,
    input  wire [31:0]          sin_t,
    output wire                 y_v,
    output wire [7:0]           y_i,
    output wire [N*32-1:0]      y,
    output wire                 r_v,
    output wire [31:0]          r,
    output wire                 q_v,
    output wire [7:0]           q_i,
    output wire [(N/32)*256-1:0] q_codes,
    output wire [(N/32)*10-1:0]  q_e,
    output wire [(N/32)*512-1:0] q_y,
    output wire                 ro_v,
    output wire [N*32-1:0]      ro,
    output wire                 fault
);
    localparam integer NG  = N / G;
    localparam integer NV  = D / N;
    localparam integer NVP = (NV <= 1) ? 1 : (1 << $clog2(NV));
    localparam integer LTT = $clog2(NG);                   // chunk-tree levels finished in the top
    localparam integer DT  = LTT * LA;
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    function automatic integer tz(input integer x);
        integer t;
        begin
            t = 0;
            while (t < 31 && ((x >> t) & 1) == 0) t = t + 1;
            tz = t;
        end
    endfunction
    localparam integer DK = tz(D);
    localparam integer DF = D >> DK;
    generate if (NV * N != D || NV > 128 || G % 8 != 0 || N % G != 0 || RW < 3 || BW < 4) begin : g_bad
        initial $fatal(1, "ot_hbm_norm_split: unsupported parameters");
    end endgenerate

    // reset: asynchronous assert, synchronous release
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rstn = rs[1];
    // input capture (no logic ahead of the flops); the groups re-register them at their pins
    reg go_c, in_v_c, wl_v_c; reg [7:0] wl_i_c;
    reg [4*N*32-1:0] x_c; reg [127:0] pre_c; reg [31:0] nf_c, eps_c; reg [N*32-1:0] wl_d_c;
    always @(posedge clk) begin
        go_c <= go; in_v_c <= in_v; wl_v_c <= wl_v; wl_i_c <= wl_i;
        x_c <= in_x; pre_c <= pre; nf_c <= n_f; eps_c <= eps; wl_d_c <= wl_d;
    end
    reg go_t;                           // the top core's go: aligned with the groups' pin-flop copy
    always @(posedge clk or negedge rstn) if (!rstn) go_t <= 1'b0; else go_t <= go_c;

    // ---------------------------------------------------------------- groups
    wire [NG-1:0]      g_sv, g_yv, g_f;
    wire [NG*8-1:0]    g_si, g_yi;
    wire [NG*32-1:0]   g_s;
    wire [N*32-1:0]    g_y;
    wire               rb_v_o;          // broadcast output flops
    wire [31:0]        rb_d_o;
    genvar g, c, k, n;
    generate
        for (g = 0; g < NG; g = g + 1) begin : g_grp
            wire [4*G*32-1:0] gx;
            for (k = 0; k < 4; k = k + 1) begin : g_cp
                assign gx[k * G * 32 +: G * 32] = x_c[(k * N + g * G) * 32 +: G * 32];
            end
            if (G == 8) begin : g8
                ot_hbm_norm_grp8 u_g (.clk(clk), .rst_n(rstn), .go(go_c), .in_v(in_v_c), .in_x(gx), .pre(pre_c),
                    .wl_v(wl_v_c), .wl_i(wl_i_c), .wl_d(wl_d_c[g * G * 32 +: G * 32]), .rb_v(rb_v_o), .rb_d(rb_d_o),
                    .s_v(g_sv[g]), .s_i(g_si[g * 8 +: 8]), .s(g_s[g * 32 +: 32]), .y_v(g_yv[g]), .y_i(g_yi[g * 8 +: 8]),
                    .y(g_y[g * G * 32 +: G * 32]), .gf(g_f[g]));
            end else if (G == 16) begin : g16
                ot_hbm_norm_grp16 u_g (.clk(clk), .rst_n(rstn), .go(go_c), .in_v(in_v_c), .in_x(gx), .pre(pre_c),
                    .wl_v(wl_v_c), .wl_i(wl_i_c), .wl_d(wl_d_c[g * G * 32 +: G * 32]), .rb_v(rb_v_o), .rb_d(rb_d_o),
                    .s_v(g_sv[g]), .s_i(g_si[g * 8 +: 8]), .s(g_s[g * 32 +: 32]), .y_v(g_yv[g]), .y_i(g_yi[g * 8 +: 8]),
                    .y(g_y[g * G * 32 +: G * 32]), .gf(g_f[g]));
            end else begin : gp
                ot_hbm_norm_grp #(.G(G), .D(D), .N(N), .LM(LM), .LA(LA)) u_g (.clk(clk), .rst_n(rstn), .go(go_c),
                    .in_v(in_v_c), .in_x(gx), .pre(pre_c), .wl_v(wl_v_c), .wl_i(wl_i_c),
                    .wl_d(wl_d_c[g * G * 32 +: G * 32]), .rb_v(rb_v_o), .rb_d(rb_d_o),
                    .s_v(g_sv[g]), .s_i(g_si[g * 8 +: 8]), .s(g_s[g * 32 +: 32]), .y_v(g_yv[g]), .y_i(g_yi[g * 8 +: 8]),
                    .y(g_y[g * G * 32 +: G * 32]), .gf(g_f[g]));
            end
        end
    endgenerate

    // ---------------------------------------------------------------- group partials: input flops, top tree levels
    reg            p_v; reg [7:0] p_i; reg [NG*32-1:0] p_s; reg [NG-1:0] p_f;
    always @(posedge clk or negedge rstn)
        if (!rstn) begin p_v <= 1'b0; p_f <= {NG{1'b0}}; end
        else begin p_v <= g_sv[0]; p_f <= go_t ? {NG{1'b0}} : g_f; end
    always @(posedge clk) begin p_i <= g_si[7:0]; p_s <= g_s; end
    wire [DT:0] vt;
    generate if (DT > 0) begin : g_vt
        ot_hdc_vline #(.D(DT)) u_vt (.clk(clk), .rst_n(rstn), .v(p_v), .vd(vt));
    end else begin : g_vt0
        assign vt = p_v;
    end endgenerate
    wire [7:0] si;
    ot_hdc_delay #(.W(8), .D(DT)) u_si (.clk(clk), .rst_n(rstn), .d(p_i), .q(si));
    wire [31:0] tv [0:LTT][0:NG-1];
    wire [LTT:0] tf_any;
    generate
        for (c = 0; c < NG; c = c + 1) begin : g_t0
`ifdef OT_NSPLIT_MUT
            // NEGATIVE CONTROL: group 1's partial replaced by group 0's (a top wiring error)
            assign tv[0][c] = (c == 1) ? p_s[0 +: 32] : p_s[c * 32 +: 32];
`else
            assign tv[0][c] = p_s[c * 32 +: 32];
`endif
        end
        assign tf_any[0] = 1'b0;
        for (k = 1; k <= LTT; k = k + 1) begin : g_tl
            wire [(NG >> k)-1:0] f;
            for (c = 0; c < (NG >> k); c = c + 1) begin : g_tn
                ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rstn, vt[LA * (k - 1)], tv[k - 1][2 * c], tv[k - 1][2 * c + 1],
                                               tv[k][c], f[c]);
            end
            for (c = (NG >> k); c < NG; c = c + 1) begin : g_tz
                assign tv[k][c] = 32'd0;
            end
            assign tf_any[k] = |f;
        end
    endgenerate
    wire        vsum_v = vt[DT];
    wire [31:0] vsum = tv[LTT][0];

    // ---------------------------------------------------------------- vector levels (ot_dsrom_su_norm, verbatim)
    wire [31:0] nv [1:2*NVP-1];
    wire        nd [1:2*NVP-1];
    wire        np [1:2*NVP-1];
    wire [NVP:0] nf;
    assign nf[0] = 1'b0;
    assign nf[NVP] = 1'b0;
    generate
        for (n = NVP; n < 2 * NVP; n = n + 1) begin : g_leaf
            reg [31:0] val;
            reg        vld;
            wire       hit = vsum_v && si == n - NVP;
            always @(posedge clk or negedge rstn)
                if (!rstn) vld <= 1'b0;
                else if (go_t) vld <= 1'b0;
                else if (hit) vld <= 1'b1;
            always @(posedge clk) if (hit) val <= vsum;
            assign np[n] = hit;
            assign nd[n] = vld || hit;
            assign nv[n] = vld ? val : vsum;
        end
        for (n = 1; n < NVP; n = n + 1) begin : g_vn
            localparam integer H = $clog2(NVP) - ($clog2(n + 1) - 1);
            if ((((2 * n + 1) << (H - 1)) - NVP) < NV) begin : g_add
                reg st, vld;
                reg [31:0] val;
                wire [LAV:0] av;
                wire [31:0] sm;
                wire fire = nd[2 * n] && nd[2 * n + 1] && !st && !go_t;
                ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rstn), .v(fire), .vd(av));
                ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rstn, fire, nv[2 * n], nv[2 * n + 1], sm, nf[n]);
                always @(posedge clk or negedge rstn) begin
                    if (!rstn) begin st <= 1'b0; vld <= 1'b0; end
                    else if (go_t) begin st <= 1'b0; vld <= 1'b0; end
                    else begin
                        if (fire) st <= 1'b1;
                        if (av[LAV]) vld <= 1'b1;
                    end
                end
                always @(posedge clk) if (av[LAV]) val <= sm;
                assign np[n] = av[LAV];
                assign nd[n] = vld || av[LAV];
                assign nv[n] = vld ? val : sm;
            end else begin : g_pass
                assign nv[n] = nv[2 * n];
                assign nd[n] = nd[2 * n];
                assign np[n] = np[2 * n];
                assign nf[n] = 1'b0;
            end
        end
    endgenerate
    wire        ss_v = np[1] && !go_t;
    wire [31:0] ss = nv[1];

    // ---------------------------------------------------------------- result wire (RW - 2: the two pin flops), tail
    wire [32:0] ssw;
    ot_hdc_delay #(.W(33), .D(RW - 2), .RESET(1)) u_rw (.clk(clk), .rst_n(rstn), .d({ss_v, ss}), .q(ssw));
    wire [31:0] mq, me, rr;
    wire        mq_v, me_v, rr_v, f_div, f_eps, f_rsq;
    ot_dsrom_divc #(.F(DF), .K(DK)) u_div (.clk(clk), .rst_n(rstn), .v(ssw[32]), .x(ssw[31:0]), .y(mq), .vo(mq_v),
                                           .fault(f_div));
    wire [LA:0] ve;
    ot_hdc_vline #(.D(LA)) u_ve (.clk(clk), .rst_n(rstn), .v(mq_v), .vd(ve));
    ot_dsrom_qadd #(.LAT(LA)) u_eps (clk, rstn, mq_v, mq, eps_c, me, f_eps);
    assign me_v = ve[LA];
    ot_dsrom_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(clk), .rst_n(rstn), .v(me_v), .x(me), .y(rr), .vo(rr_v), .fault(f_rsq));
    // broadcast wire: BW - 3 stages here, then the output flop (here) and the group's pin flop = the flat engine's
    // BW - 1 stages; the group's rh is the BW-th
    wire [32:0] rbw;
    ot_hdc_delay #(.W(33), .D(BW - 3), .RESET(1)) u_bw (.clk(clk), .rst_n(rstn), .d({rr_v, rr}), .q(rbw));
    reg rbv_o; reg [31:0] rbd_o;
    always @(posedge clk or negedge rstn) if (!rstn) rbv_o <= 1'b0; else rbv_o <= rbw[32];
    always @(posedge clk) rbd_o <= rbw[31:0];
    assign rb_v_o = rbv_o;
    assign rb_d_o = rbd_o;

    // ---------------------------------------------------------------- outputs: y flops, act-quant from them
    reg y_v_o, r_v_o, q_v_o; reg [7:0] y_i_o, q_i_o; reg [N*32-1:0] y_o; reg [31:0] r_o;
    reg [(N/32)*256-1:0] qc_o; reg [(N/32)*10-1:0] qe_o; reg [(N/32)*512-1:0] qy_o;
    wire [N/32-1:0] aq_v, aq_f;
    wire [(N/32)*256-1:0] aq_c; wire [(N/32)*10-1:0] aq_e; wire [(N/32)*512-1:0] aq_y;
    generate
        for (k = 0; k < N / 32; k = k + 1) begin : g_aq
            wire signed [9:0] e;
            ot_dsrom_aq12 u_aq (.clk(clk), .rst_n(rstn), .v(y_v_o), .x(y_o[k * 1024 +: 1024]), .vo(aq_v[k]),
                                .q(aq_c[k * 256 +: 256]), .e(e), .y(aq_y[k * 512 +: 512]), .fault(aq_f[k]));
            assign aq_e[k * 10 +: 10] = e;
        end
    endgenerate
    wire [7:0] aq_i;
    ot_hdc_delay #(.W(8), .D(18)) u_qi (.clk(clk), .rst_n(rstn), .d(y_i_o), .q(aq_i));
    always @(posedge clk or negedge rstn)
        if (!rstn) begin y_v_o <= 1'b0; r_v_o <= 1'b0; q_v_o <= 1'b0; end
        else begin y_v_o <= g_yv[0]; r_v_o <= rr_v; q_v_o <= aq_v[0]; end
    always @(posedge clk) begin
        y_i_o <= g_yi[7:0]; y_o <= g_y; r_o <= rr; q_i_o <= aq_i; qc_o <= aq_c; qe_o <= aq_e; qy_o <= aq_y;
    end
    assign y_v = y_v_o; assign y_i = y_i_o; assign y = y_o; assign r_v = r_v_o; assign r = r_o;
    assign q_v = q_v_o; assign q_i = q_i_o; assign q_codes = qc_o; assign q_e = qe_o; assign q_y = qy_o;
    assign ro_v = 1'b0;                 // RD = 0: no RoPE tail (the flat view's ro flops hold constant 0)
    assign ro = {N * 32{1'b0}};

    // ---------------------------------------------------------------- faults (sticky, registered reduction)
    reg [7:0] fg; reg flt;
    always @(posedge clk or negedge rstn)
        if (!rstn) begin fg <= 8'd0; flt <= 1'b0; end
        else if (go_t) begin fg <= 8'd0; flt <= 1'b0; end
        else begin
            fg  <= {|p_f, |tf_any, |nf, f_div, f_eps, f_rsq, |aq_f, 1'b0};
            if (|fg) flt <= 1'b1;
        end
    reg flt_o;
    always @(posedge clk or negedge rstn) if (!rstn) flt_o <= 1'b0; else flt_o <= flt;
    assign fault = flt_o;
endmodule

// Fixed-parameter top masters (the route tops; same ports as ot_hbm_norm_engine_view).
module ot_hbm_norm_split_view_g8 (
    input wire clk, input wire rst_n, input wire go, input wire in_v, input wire [4*64*32-1:0] in_x,
    input wire [127:0] pre, input wire [31:0] n_f, input wire [31:0] eps, input wire wl_v, input wire [7:0] wl_i,
    input wire [64*32-1:0] wl_d, input wire [31:0] cos_t, input wire [31:0] sin_t,
    output wire y_v, output wire [7:0] y_i, output wire [64*32-1:0] y, output wire r_v, output wire [31:0] r,
    output wire q_v, output wire [7:0] q_i, output wire [2*256-1:0] q_codes, output wire [2*10-1:0] q_e,
    output wire [2*512-1:0] q_y, output wire ro_v, output wire [64*32-1:0] ro, output wire fault
);
    ot_hbm_norm_split_core #(.G(8)) u (.clk(clk), .rst_n(rst_n), .go(go), .in_v(in_v), .in_x(in_x), .pre(pre),
        .n_f(n_f), .eps(eps), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .cos_t(cos_t), .sin_t(sin_t), .y_v(y_v),
        .y_i(y_i), .y(y), .r_v(r_v), .r(r), .q_v(q_v), .q_i(q_i), .q_codes(q_codes), .q_e(q_e), .q_y(q_y),
        .ro_v(ro_v), .ro(ro), .fault(fault));
endmodule

module ot_hbm_norm_split_view_g16 (
    input wire clk, input wire rst_n, input wire go, input wire in_v, input wire [4*64*32-1:0] in_x,
    input wire [127:0] pre, input wire [31:0] n_f, input wire [31:0] eps, input wire wl_v, input wire [7:0] wl_i,
    input wire [64*32-1:0] wl_d, input wire [31:0] cos_t, input wire [31:0] sin_t,
    output wire y_v, output wire [7:0] y_i, output wire [64*32-1:0] y, output wire r_v, output wire [31:0] r,
    output wire q_v, output wire [7:0] q_i, output wire [2*256-1:0] q_codes, output wire [2*10-1:0] q_e,
    output wire [2*512-1:0] q_y, output wire ro_v, output wire [64*32-1:0] ro, output wire fault
);
    ot_hbm_norm_split_core #(.G(16)) u (.clk(clk), .rst_n(rst_n), .go(go), .in_v(in_v), .in_x(in_x), .pre(pre),
        .n_f(n_f), .eps(eps), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .cos_t(cos_t), .sin_t(sin_t), .y_v(y_v),
        .y_i(y_i), .y(y), .r_v(r_v), .r(r), .q_v(q_v), .q_i(q_i), .q_codes(q_codes), .q_e(q_e), .q_y(q_y),
        .ro_v(ro_v), .ro(ro), .fault(fault));
endmodule
