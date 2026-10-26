`timescale 1ns/1ps
// conservative-1011 2026-10-11 OWNER textbook rebuild of the split norm engine (g8p), see conservative-1011.log audit:
//  * ot_hbm_norm_gtile8: the hardened group tile = ot_hbm_norm_grp (G=8, pin-flop boundary, own reset sync) + XI
//    alignment stages on its OUTER-face data inputs (in_x, wl_d) + YO stages on its outer-face y; band-face y copy
//    (y_b) for the act-quant; planned pin plan (outer face: in_x / wl_d / y_o; band face: everything else).
//  * ot_hbm_norm_split_core_p: no top x / wl_d / y data flops; distance-matched (* keep *) relay chains on the control
//    broadcast (BD), rstd broadcast (RBD), results (OD), reset (RR); go_t aligned with the groups' pin-flop go.
//    Valid-driven protocol (the group scale sequencer starts on rb_v), so the relays change latency only.
module ot_hbm_norm_gtile8 #(
    parameter integer XI = 4,
    parameter integer YO = 4
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go,
    input  wire          in_v,
    input  wire [1023:0] in_x,
    input  wire [127:0]  pre,
    input  wire          wl_v,
    input  wire [7:0]    wl_i,
    input  wire [255:0]  wl_d,
    input  wire          rb_v,
    input  wire [31:0]   rb_d,
    output wire          s_v,
    output wire [7:0]    s_i,
    output wire [31:0]   s,
    output wire          y_v,
    output wire [7:0]    y_i,
    output wire [255:0]  y_b,
    output wire [255:0]  y_o,
    output wire          gf
);
    (* keep *) reg [1024*XI-1:0] xs; (* keep *) reg [256*XI-1:0] ws; (* keep *) reg [256*YO-1:0] ys;
    wire [255:0] y;
    integer t;
    always @(posedge clk) begin
        xs[1023:0] <= in_x; ws[255:0] <= wl_d; ys[255:0] <= y;
        for (t = 1; t < XI; t = t + 1) begin xs[1024 * t +: 1024] <= xs[1024 * (t - 1) +: 1024]; ws[256 * t +: 256] <= ws[256 * (t - 1) +: 256]; end
        for (t = 1; t < YO; t = t + 1) ys[256 * t +: 256] <= ys[256 * (t - 1) +: 256];
    end
    ot_hbm_norm_grp #(.G(8)) u (.clk(clk), .rst_n(rst_n), .go(go), .in_v(in_v), .in_x(xs[1024 * (XI - 1) +: 1024]),
        .pre(pre), .wl_v(wl_v), .wl_i(wl_i), .wl_d(ws[256 * (XI - 1) +: 256]), .rb_v(rb_v), .rb_d(rb_d), .s_v(s_v),
        .s_i(s_i), .s(s), .y_v(y_v), .y_i(y_i), .y(y), .gf(gf));
    assign y_b = y;
    assign y_o = ys[256 * (YO - 1) +: 256];
endmodule

module ot_hbm_norm_split_core_p #(
    parameter integer G = 8,
    parameter integer N = 64,
    parameter integer D = 5120,
    parameter integer LM = 5,
    parameter integer LA = 6,
    parameter integer RW = 9,
    parameter integer BW = 9,
    // safe-hbm 2026-10-08 (REVIEW_20261008 C7, S-C7): REP=1 replicates the top's broadcast flops per group: the rstd
    // broadcast output flops (rbv_o / rbd_o) and the capture flops that every group reads (go, in_v, wl_v, wl_i, pre).
    // Each replica is loaded from the same source on the same edge as the shared flop, so the groups see identical
    // values on identical cycles (0 cycles).  REP=0 (default) is the original netlist.
    parameter integer REP = 1,          // (g8p: always per-group broadcast chains)
    // conservative-1011 textbook rebuild (g8p): distance-matched seam relays.  BD: die pin -> group-tile pin stages of
    // the control broadcast (the tile adds XI = BD stages on its outer-face x / wl_d, so they stay aligned); RBD: rstd
    // broadcast relay stages; OD: result relay stages to the E-edge pins (the tile adds YO = OD + 1 on y); RR: per-group
    // reset relay stages.  Every chain is (* keep *) so a stage lands every <= ~470 um.
    parameter integer BD = 4,
    parameter integer RBD = 3,
    parameter integer OD = 3,
    parameter integer RR = 3
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
    // die-pin flops of the control broadcast (stage 1 of BD); x / wl_d slices enter their group tile directly
    (* keep *) reg go_c, in_v_c, wl_v_c; (* keep *) reg [7:0] wl_i_c; (* keep *) reg [127:0] pre_c;
    reg [31:0] nf_i, eps_i, nf_c, eps_c;
    always @(posedge clk) begin
        go_c <= go; in_v_c <= in_v; wl_v_c <= wl_v; wl_i_c <= wl_i; pre_c <= pre;
        nf_i <= n_f; eps_i <= eps; nf_c <= nf_i; eps_c <= eps_i;
    end
    // the top core's go: aligned with the groups' pin-flop copy (BD broadcast stages + the group's pin flop)
    wire [BD:0] go_tl;
    ot_hdc_delay #(.W(1), .D(BD), .RESET(1)) u_got (.clk(clk), .rst_n(rstn), .d(go_c), .q(go_tl[0]));
    wire go_t = go_tl[0];

    // ---------------------------------------------------------------- groups
    wire [NG-1:0]      g_sv, g_yv, g_f;
    wire [NG*8-1:0]    g_si, g_yi;
    wire [NG*32-1:0]   g_s;
    wire [N*32-1:0]    g_y;
    wire [N*32-1:0]    y_pin;           // the tiles' outer-face y (YO stages): the y die pins
    wire [32:0]        rbw;             // broadcast wire output (declared here: the REP replicas read it)
    wire               rb_v_o;          // broadcast output flops
    wire [31:0]        rb_d_o;
    genvar g, c, k, n;
    generate
        for (g = 0; g < NG; g = g + 1) begin : g_grp
            // control broadcast chain: stage 1 = the shared die-pin flops, stages 2..BD per group (* keep *)
            (* keep *) reg [BD-1:1] c_go, c_inv, c_wlv; (* keep *) reg [8*BD-1:8] c_wli; (* keep *) reg [128*BD-1:128] c_pre;
            (* keep *) reg [RBD-1:0] c_rbv; (* keep *) reg [32*RBD-1:0] c_rbd;
            (* keep *) reg [RR-1:0] c_rst;
            integer t;
            always @(posedge clk) begin
                c_go[1] <= go_c; c_inv[1] <= in_v_c; c_wlv[1] <= wl_v_c; c_wli[15:8] <= wl_i_c; c_pre[255:128] <= pre_c;
                for (t = 2; t < BD; t = t + 1) begin
                    c_go[t] <= c_go[t - 1]; c_inv[t] <= c_inv[t - 1]; c_wlv[t] <= c_wlv[t - 1];
                    c_wli[8 * t +: 8] <= c_wli[8 * (t - 1) +: 8]; c_pre[128 * t +: 128] <= c_pre[128 * (t - 1) +: 128];
                end
                c_rbd[31:0] <= rbw[31:0];
                for (t = 1; t < RBD; t = t + 1) c_rbd[32 * t +: 32] <= c_rbd[32 * (t - 1) +: 32];
                c_rst[0] <= rstn;
                for (t = 1; t < RR; t = t + 1) c_rst[t] <= c_rst[t - 1];
            end
            always @(posedge clk or negedge rstn)
                if (!rstn) c_rbv <= {RBD{1'b0}};
                else begin c_rbv[0] <= rbw[32]; for (t = 1; t < RBD; t = t + 1) c_rbv[t] <= c_rbv[t - 1]; end
`ifdef OT_NSPLIT_P_MUT
            // NEGATIVE CONTROL: group 1's in_v broadcast one stage short (in_v ahead of its x slice)
            wire b_inv = (g == 1) ? c_inv[BD - 2] : c_inv[BD - 1];
`else
            wire b_inv = c_inv[BD - 1];
`endif
            wire [4*G*32-1:0] gx;
            for (k = 0; k < 4; k = k + 1) begin : g_cp
                assign gx[k * G * 32 +: G * 32] = in_x[(k * N + g * G) * 32 +: G * 32];
            end
            ot_hbm_norm_gtile8 #(.XI(BD), .YO(OD + 1)) u_g (.clk(clk), .rst_n(c_rst[RR - 1]), .go(c_go[BD - 1]),
                .in_v(b_inv), .in_x(gx), .pre(c_pre[128 * (BD - 1) +: 128]), .wl_v(c_wlv[BD - 1]),
                .wl_i(c_wli[8 * (BD - 1) +: 8]), .wl_d(wl_d[g * G * 32 +: G * 32]), .rb_v(c_rbv[RBD - 1]),
                .rb_d(c_rbd[32 * (RBD - 1) +: 32]), .s_v(g_sv[g]), .s_i(g_si[g * 8 +: 8]), .s(g_s[g * 32 +: 32]),
                .y_v(g_yv[g]), .y_i(g_yi[g * 8 +: 8]), .y_b(g_y[g * G * 32 +: G * 32]), .y_o(y_pin[g * G * 32 +: G * 32]),
                .gf(g_f[g]));
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
    // OD result relay stages to the E-edge pins (valids reset, data unreset)
    localparam integer WR = 8 + 32 + 8 + (N/32)*256 + (N/32)*10 + (N/32)*512;
    (* keep *) reg [WR*OD-1:0] od_d; (* keep *) reg [3*OD-1:0] od_v;
    integer u;
    always @(posedge clk) begin
        od_d[WR-1:0] <= {y_i_o, r_o, q_i_o, qc_o, qe_o, qy_o};
        for (u = 1; u < OD; u = u + 1) od_d[WR * u +: WR] <= od_d[WR * (u - 1) +: WR];
    end
    always @(posedge clk or negedge rstn)
        if (!rstn) od_v <= {3*OD{1'b0}};
        else begin od_v[2:0] <= {y_v_o, r_v_o, q_v_o}; for (u = 1; u < OD; u = u + 1) od_v[3 * u +: 3] <= od_v[3 * (u - 1) +: 3]; end
    assign {y_i, r, q_i, q_codes, q_e, q_y} = od_d[WR * (OD - 1) +: WR];
    assign {y_v, r_v, q_v} = od_v[3 * (OD - 1) +: 3];
    assign y = y_pin;
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
    (* keep *) reg [OD:0] flt_o;
    always @(posedge clk or negedge rstn) if (!rstn) flt_o <= {OD+1{1'b0}}; else flt_o <= {flt_o[OD-1:0], flt};
    assign fault = flt_o[OD];
endmodule

// g8p route top (same ports as ot_hbm_norm_engine_view)
module ot_hbm_norm_split_view_g8p (
    input wire clk, input wire rst_n, input wire go, input wire in_v, input wire [4*64*32-1:0] in_x,
    input wire [127:0] pre, input wire [31:0] n_f, input wire [31:0] eps, input wire wl_v, input wire [7:0] wl_i,
    input wire [64*32-1:0] wl_d, input wire [31:0] cos_t, input wire [31:0] sin_t,
    output wire y_v, output wire [7:0] y_i, output wire [64*32-1:0] y, output wire r_v, output wire [31:0] r,
    output wire q_v, output wire [7:0] q_i, output wire [2*256-1:0] q_codes, output wire [2*10-1:0] q_e,
    output wire [2*512-1:0] q_y, output wire ro_v, output wire [64*32-1:0] ro, output wire fault
);
    ot_hbm_norm_split_core_p #(.G(8)) u (.clk(clk), .rst_n(rst_n), .go(go), .in_v(in_v), .in_x(in_x), .pre(pre),
        .n_f(n_f), .eps(eps), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .cos_t(cos_t), .sin_t(sin_t), .y_v(y_v),
        .y_i(y_i), .y(y), .r_v(r_v), .r(r), .q_v(q_v), .q_i(q_i), .q_codes(q_codes), .q_e(q_e), .q_y(q_y),
        .ro_v(ro_v), .ro(ro), .fault(fault));
endmodule
