`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_su_norm_lg (s81-suhc-hier-1011, 2026-10-11): one LANE GROUP of the RMSNorm -> RoPE -> FP8 chain
// ot_dsrom_su_norm (HC 0, MEM 0, SXC 0, RXS 0, FREG 0), so an N-lane norm spans T hardened tiles of G = N / T lanes.
// Values are those of ot_dsrom_su_norm: the golden's sum of squares is chunks of 8 summed sequentially, the chunk
// sums by a pairwise tree; a G-lane group's G/8 chunk sums are an ALIGNED subtree of that tree (G a power of two,
// lanes L0 .. L0+G-1, L0 a multiple of G), so each group sums its own subtree and the top level(s) combine the group
// sums left to right in the head group (TI 0) -- the golden's order (T 2: one add, own (left) + partner (right)).
//   every group: square, chunk chains, its subtree -> the group partial (ps_*: a registered pulse with the vector
//                index), the x wait line, the gain ROM slice, the scale y = bf16(w * (x * r)), RoPE (the tail lanes
//                it holds), FP8 act-quant of its 32-blocks
//   head (HEAD 1): the cross-group rung (a held slot a vector for each side; the add fires when both are in), the
//                vector levels, the result wire, ss / D, + eps, rsqrt, the broadcast wire (rb_o_*: to the other
//                groups through registered seams; its own scale takes the same value)
// Non-head groups take the rstd from rb_i_* (the seam's registers, then this group's hold register rh).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_norm_lg #(
    parameter integer N = 512,          // lanes of the whole norm (a power of two)
    parameter integer G = 256,          // lanes of this group (a power of two >= 64, N / T)
    parameter integer L0 = 0,           // first lane of this group
    parameter integer T = 2,            // groups (1 or 2)
    parameter integer HEAD = 1,
    parameter integer D = 512,
    parameter integer RD = 0,
    parameter integer QUANT = 1,
    parameter integer RW = 9,
    parameter integer BW = 9,
    parameter integer LM = 5,
    parameter integer LA = 4
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     go,
    input  wire                     in_v,
    input  wire [G*32-1:0]          in_x,
    input  wire [31:0]              n_f,
    input  wire [31:0]              eps,
    input  wire                     wl_v,
    input  wire [7:0]               wl_i,
    input  wire [G*32-1:0]          wl_d,
    input  wire [(RD ? RD/2 : 1)*32-1:0] cos_t,
    input  wire [(RD ? RD/2 : 1)*32-1:0] sin_t,
    output reg                      ps_v,           // the group partial (non-head)
    output reg  [7:0]               ps_i,
    output reg  [31:0]              ps_d,
    input  wire                     pp_v,           // the partner's partial (head, T 2)
    input  wire [7:0]               pp_i,
    input  wire [31:0]              pp_d,
    output wire                     rb_o_v,         // the broadcast rstd (head)
    output wire [31:0]              rb_o_d,
    input  wire                     rb_i_v,         // the rstd from the head (non-head)
    input  wire [31:0]              rb_i_d,
    output wire                     y_v,
    output wire [7:0]               y_i,
    output wire [G*32-1:0]          y,
    output wire                     q_v,
    output wire [7:0]               q_i,
    output wire [(QUANT ? G/32 : 1)*256-1:0] q_codes,
    output wire [(QUANT ? G/32 : 1)*10-1:0]  q_e,
    output wire [(QUANT ? G/32 : 1)*512-1:0] q_y,
    output wire                     ro_v,
    output wire [G*32-1:0]          ro,
    output wire                     fault
);
    localparam integer NV  = (D + N - 1) / N;
    localparam integer NVP = (NV <= 1) ? 1 : (1 << $clog2(NV));
    localparam integer NC  = G / 8;
    localparam integer LT  = $clog2(NC);
    localparam integer DS  = LM + 7 * LA + LT * LA;         // square + chain + group tree
    localparam integer LB  = D - (NV - 1) * N;
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    function automatic integer tz(input integer x);
        integer t;
        begin
            t = 0;
            while (t < 31 && ((x >> t) & 1) == 0) t = t + 1;
            tz = t;
        end
    endfunction
    localparam integer DK  = tz(D);
    localparam integer DF  = D >> DK;
`ifndef SYNTHESIS
    initial begin
        if (T != 1 && T != 2) $fatal(1, "ot_s81_su_norm_lg: T 1 or 2");
        if (G * T != N || (L0 % G) || (G & (G - 1)) || G < 64) $fatal(1, "ot_s81_su_norm_lg: G = N / T, a power of two >= 64");
        if (NV > 255) $fatal(1, "ot_s81_su_norm_lg: NV < 256 (8-bit vector index)");
    end
`endif
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] s;
        begin
            s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]};
            bf16 = {s[31:16], 16'd0};
        end
    endfunction

    // ---------------------------------------------------------------- input vector index
    reg  [7:0] in_i;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) in_i <= 8'd0;
        else if (go) in_i <= 8'd0;
        else if (in_v) in_i <= in_i + 8'd1;
    reg in_last;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) in_last <= (NV == 1);
        else if (go) in_last <= (NV == 1);
        else if (in_v) in_last <= (in_i + 8'd1 == NV - 1);
    wire       x_v = in_v;
    wire [7:0] xi = in_i;
    wire       x_last = in_last;
    wire [DS:0] vs;
    ot_hdc_vline #(.D(DS)) u_vs (.clk(clk), .rst_n(rst_n), .v(x_v), .vd(vs));
    wire [7:0] si;
    ot_hdc_delay #(.W(8), .D(DS)) u_si (.clk(clk), .rst_n(rst_n), .d(xi), .q(si));

    // scale sequencer (as ot_dsrom_su_norm)
    wire        rb_v;
    reg  [31:0] rh;
    reg         sc_run;
    reg  [7:0]  sc_i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin sc_run <= 1'b0; sc_i <= 8'd0; end
        else if (rb_v) begin sc_run <= (NV > 1); sc_i <= 8'd1; end
        else if (sc_run) begin
            if (sc_i == NV - 1) sc_run <= 1'b0;
            sc_i <= sc_i + 8'd1;
        end
    end
    wire        sc_go = rb_v || sc_run;
    wire [7:0]  sc_x  = rb_v ? 8'd0 : sc_i;
    wire [7:0]  sc_nx = rb_v ? 8'd1 : sc_run ? sc_i + 8'd1 : 8'd0;
    localparam integer DY = 2 * LM + 1;
    wire [DY:0] vy;
    ot_hdc_vline #(.D(DY)) u_vy (.clk(clk), .rst_n(rst_n), .v(sc_go), .vd(vy));
    wire [7:0] yi_m, yi_o;
    ot_hdc_delay #(.W(8), .D(LM)) u_yim (.clk(clk), .rst_n(rst_n), .d(sc_nx), .q(yi_m));
    ot_hdc_delay #(.W(8), .D(DY)) u_yio (.clk(clk), .rst_n(rst_n), .d(sc_x), .q(yi_o));

    wire [G-1:0]    lf;
    wire [G*32-1:0] sq;
    wire [NC*32-1:0] cs;
    wire [NC-1:0]   cf;
    wire [G*32-1:0] yb;
    wire [G*32-1:0] ybr;
    genvar l, c, k, n;
    generate
        for (l = 0; l < G; l = l + 1) begin : g_lane
            wire [31:0] xl = in_x[l * 32 +: 32];
            wire [9:0] f;
            assign f[6:0] = 7'd0;
            wire [31:0] xo;
            reg [31:0] xb [0:NV-1];
            reg [31:0] xo_r;
            always @(posedge clk) if (x_v) xb[xi] <= xl;
            always @(posedge clk) xo_r <= xb[sc_nx];
            assign xo = xo_r;
            wire live = (L0 + l < LB) || !x_last;
            wire [31:0] xs = live ? xl : 32'd0;
            ot_hdc_qmul_lat #(LM) u_sq (clk, rst_n, x_v, xs, xs, sq[l * 32 +: 32], f[7]);
            wire [31:0] wo;
            reg [31:0] wr [0:NV-1];
            reg [31:0] wo_r;
            always @(posedge clk) if (wl_v) wr[wl_i] <= wl_d[l * 32 +: 32];
            always @(posedge clk) wo_r <= wr[yi_m];
            assign wo = wo_r;
            wire [31:0] p, q;
            ot_hdc_qmul_lat #(LM) u_xr (clk, rst_n, sc_go, xo, rh, p, f[8]);
            ot_hdc_qmul_lat #(LM) u_w  (clk, rst_n, vy[LM], wo, p, q, f[9]);
            reg [31:0] yr;
            (* keep *) reg [31:0] yrr;
            always @(posedge clk) begin yr <= bf16(q); yrr <= bf16(q); end
            assign yb[l * 32 +: 32] = yr;
            assign ybr[l * 32 +: 32] = yrr;
            assign lf[l] = |f;
        end
        for (c = 0; c < NC; c = c + 1) begin : g_chunk
            wire [31:0] acc [0:7];
            wire [7:0] f;
            assign acc[0] = sq[(8 * c) * 32 +: 32];
            assign f[0] = 1'b0;
            for (k = 1; k < 8; k = k + 1) begin : g_j
                wire [31:0] sd;
                ot_hdc_delay #(.W(32), .D(LA * (k - 1))) u_sd (.clk(clk), .rst_n(rst_n), .d(sq[(8 * c + k) * 32 +: 32]),
                                                              .q(sd));
                ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, vs[LM + LA * (k - 1)], acc[k - 1], sd, acc[k], f[k]);
            end
            assign cs[c * 32 +: 32] = acc[7];
            assign cf[c] = |f;
        end
    endgenerate

    // group subtree
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
                ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, vs[LM + 7 * LA + LA * (k - 1)], tv[k - 1][2 * c],
                                                           tv[k - 1][2 * c + 1], tv[k][c], f[c]);
            end
            for (c = (NC >> k); c < NC; c = c + 1) begin : g_tz
                assign tv[k][c] = 32'd0;
            end
            assign tf_any[k] = |f;
        end
    endgenerate
    wire        gs_v = vs[DS];
    wire [31:0] gs_d = tv[LT][0];

    // the partial out (registered)
    always @(posedge clk or negedge rst_n) if (!rst_n) ps_v <= 1'b0; else ps_v <= gs_v && !HEAD;
    always @(posedge clk) begin ps_i <= si; ps_d <= gs_d; end

    wire f_head;
    generate if (HEAD) begin : g_head
        // ------------------------------------------------------------ the cross-group rung
        wire        vsum_v;
        wire [31:0] vsum;
        wire [7:0]  vsi;
        wire        f_rung;
        if (T == 1) begin : g_t1
            assign vsum_v = gs_v; assign vsum = gs_d; assign vsi = si; assign f_rung = 1'b0;
        end else begin : g_t2
            reg [31:0] av [0:NV-1];
            reg [31:0] bv [0:NV-1];
            reg [NV-1:0] ah, bh;
            reg [7:0] ptr;
            wire fire = ah[ptr] && bh[ptr] && !go;
            reg [31:0] fa, fb;
            always @(*) begin fa = av[ptr]; fb = bv[ptr]; end
            always @(posedge clk) begin
                if (gs_v) av[si] <= gs_d;
                if (pp_v) bv[pp_i] <= pp_d;
            end
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin ah <= 0; bh <= 0; ptr <= 0; end
                else if (go) begin ah <= 0; bh <= 0; ptr <= 0; end
                else begin
                    if (gs_v) ah[si] <= 1'b1;
                    if (pp_v) bh[pp_i] <= 1'b1;
                    if (fire) begin ah[ptr] <= 1'b0; bh[ptr] <= 1'b0; ptr <= ptr + 8'd1; end
                end
            end
            wire [LA:0] fv;
            ot_hdc_vline #(.D(LA)) u_fv (.clk(clk), .rst_n(rst_n), .v(fire), .vd(fv));
            ot_dsrom_qadd #(.LAT(LA)) u_r (clk, rst_n, fire, fa, fb, vsum, f_rung);
            ot_hdc_delay #(.W(8), .D(LA)) u_fi (.clk(clk), .rst_n(rst_n), .d(ptr), .q(vsi));
            assign vsum_v = fv[LA];
        end

        // ------------------------------------------------------------ vector levels (as ot_dsrom_su_norm)
        wire [31:0] nv [1:2*NVP-1];
        wire        nd [1:2*NVP-1];
        wire        np [1:2*NVP-1];
        wire [NVP:0] nf;
        assign nf[0] = 1'b0;
        assign nf[NVP] = 1'b0;
        for (n = NVP; n < 2 * NVP; n = n + 1) begin : g_leaf
            reg [31:0] val;
            reg        vld;
            wire       hit = vsum_v && vsi == n - NVP;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) vld <= 1'b0;
                else if (go) vld <= 1'b0;
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
                wire [31:0] s;
                wire fire = nd[2 * n] && nd[2 * n + 1] && !st && !go;
                ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rst_n), .v(fire), .vd(av));
                ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rst_n, fire, nv[2 * n], nv[2 * n + 1], s, nf[n]);
                always @(posedge clk or negedge rst_n) begin
                    if (!rst_n) begin st <= 1'b0; vld <= 1'b0; end
                    else if (go) begin st <= 1'b0; vld <= 1'b0; end
                    else begin
                        if (fire) st <= 1'b1;
                        if (av[LAV]) vld <= 1'b1;
                    end
                end
                always @(posedge clk) if (av[LAV]) val <= s;
                assign np[n] = av[LAV];
                assign nd[n] = vld || av[LAV];
                assign nv[n] = vld ? val : s;
            end else begin : g_pass
                assign nv[n] = nv[2 * n];
                assign nd[n] = nd[2 * n];
                assign np[n] = np[2 * n];
                assign nf[n] = 1'b0;
            end
        end
        wire        ss_v = np[1] && !go;
        wire [31:0] ss = nv[1];

        // ------------------------------------------------------------ result wire, scalar tail, broadcast wire
        wire [32:0] ssw;
        ot_hdc_delay #(.W(33), .D(RW), .RESET(1)) u_rw (.clk(clk), .rst_n(rst_n), .d({ss_v, ss}), .q(ssw));
        wire [31:0] mq, me, rr;
        wire        mq_v, me_v, rr_v, f_div, f_eps, f_rsq;
        ot_dsrom_divc #(.F(DF), .K(DK)) u_div (.clk(clk), .rst_n(rst_n), .v(ssw[32]), .x(ssw[31:0]), .y(mq), .vo(mq_v),
                                               .fault(f_div));
        wire [LA:0] ve;
        ot_hdc_vline #(.D(LA)) u_ve (.clk(clk), .rst_n(rst_n), .v(mq_v), .vd(ve));
        ot_dsrom_qadd #(.LAT(LA)) u_eps (clk, rst_n, mq_v, mq, eps, me, f_eps);
        assign me_v = ve[LA];
        ot_dsrom_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(clk), .rst_n(rst_n), .v(me_v), .x(me), .y(rr), .vo(rr_v), .fault(f_rsq));
        wire [32:0] rbw;
        ot_hdc_delay #(.W(33), .D(BW - 1), .RESET(1)) u_bw (.clk(clk), .rst_n(rst_n), .d({rr_v, rr}), .q(rbw));
        assign rb_o_v = rbw[32];
        assign rb_o_d = rbw[31:0];
        assign f_head = f_rung || (|nf) || f_div || f_eps || f_rsq;
    end else begin : g_nohead
        assign rb_o_v = 1'b0;
        assign rb_o_d = 32'd0;
        assign f_head = 1'b0;
    end endgenerate

    // the rstd hold register: from this group's broadcast wire (head) or the seam (others)
    wire        rin_v = HEAD ? rb_o_v : rb_i_v;
    wire [31:0] rin_d = HEAD ? rb_o_d : rb_i_d;
    reg rbv;
    always @(posedge clk or negedge rst_n) if (!rst_n) rbv <= 1'b0; else rbv <= rin_v;
    always @(posedge clk) if (rin_v) rh <= rin_d;
    assign rb_v = rbv;
    assign y_v = vy[DY];
    assign y_i = yi_o;
    assign y = yb;

    // ---------------------------------------------------------------- RoPE tail (the lanes of it this group holds)
    localparam integer LMR = LM + 1, LAR = (LA >= 5) ? LA : LA + 1;
    localparam integer DRO = LMR + LAR + 1;
    wire [DRO:0] vr;
    ot_hdc_vline #(.D(DRO)) u_vr (.clk(clk), .rst_n(rst_n), .v(y_v), .vd(vr));
    wire [7:0] ro_i, ro_im;
    ot_hdc_delay #(.W(8), .D(DRO)) u_roi (.clk(clk), .rst_n(rst_n), .d(yi_o), .q(ro_i));
    ot_hdc_delay #(.W(8), .D(DRO - 1)) u_rom (.clk(clk), .rst_n(rst_n), .d(yi_o), .q(ro_im));
    wire last_rm = (ro_im == NV - 1);
    wire [G-1:0] rf;
    generate
        if (RD > 0) begin : g_rope
            for (l = 0; l < G; l = l + 1) begin : g_rl
                if (L0 + l >= LB - RD && L0 + l < LB) begin : g_rot
                    localparam integer KK = (L0 + l - (LB - RD)) / 2;
                    localparam integer ODD = (L0 + l - (LB - RD)) % 2;
                    wire [31:0] cc = cos_t[KK * 32 +: 32], sn = sin_t[KK * 32 +: 32];
                    wire [31:0] mine = ybr[l * 32 +: 32], pair = ybr[(ODD ? l - 1 : l + 1) * 32 +: 32];
                    wire [31:0] pp, qq, rs, dl;
                    wire f0, f1, f2;
                    ot_hdc_qmul_lat #(LMR) u_p (clk, rst_n, vr[0], mine, cc, pp, f0);
                    ot_hdc_qmul_lat #(LMR) u_q (clk, rst_n, vr[0], pair, ODD ? sn : {~sn[31], sn[30:0]}, qq, f1);
                    ot_dsrom_qadd #(.LAT(LAR)) u_a (clk, rst_n, vr[LMR], pp, qq, rs, f2);
                    ot_hdc_delay #(.W(32), .D(DRO - 1)) u_d (.clk(clk), .rst_n(rst_n), .d(yb[l * 32 +: 32]), .q(dl));
                    reg [31:0] o;
                    always @(posedge clk) o <= last_rm ? bf16(rs) : dl;
                    assign ro[l * 32 +: 32] = o;
                    assign rf[l] = vr[DRO] & (ro_i == NV - 1) & (f0 | f1 | f2);
                end else begin : g_keep
                    ot_hdc_delay #(.W(32), .D(DRO)) u_d (.clk(clk), .rst_n(rst_n), .d(yb[l * 32 +: 32]), .q(ro[l * 32 +: 32]));
                    assign rf[l] = 1'b0;
                end
            end
        end else begin : g_norope
            assign ro = {G * 32{1'b0}};
            assign rf = {G{1'b0}};
        end
    endgenerate
    assign ro_v = (RD > 0) ? vr[DRO] : 1'b0;

    // ---------------------------------------------------------------- FP8 act-quant, one instance a 32-lane block
    wire [G/32:0] qf;
    generate
        if (QUANT) begin : g_q
            wire            qin_v = (RD > 0) ? ro_v : y_v;
            wire [G*32-1:0] qin   = (RD > 0) ? ro : yb;
            wire [7:0]      qin_i = (RD > 0) ? ro_i : yi_o;
            wire [G/32-1:0] vo;
            for (k = 0; k < G / 32; k = k + 1) begin : g_aq
                wire signed [9:0] e;
                ot_dsrom_aq12 u_aq (.clk(clk), .rst_n(rst_n), .v(qin_v), .x(qin[k * 1024 +: 1024]),
                                    .vo(vo[k]), .q(q_codes[k * 256 +: 256]), .e(e), .y(q_y[k * 512 +: 512]),
                                    .fault(qf[k]));
                assign q_e[k * 10 +: 10] = e;
            end
            assign q_v = vo[0];
            ot_hdc_delay #(.W(8), .D(18)) u_qi (.clk(clk), .rst_n(rst_n), .d(qin_i), .q(q_i));
            assign qf[G / 32] = 1'b0;
        end else begin : g_nq
            assign q_v = 1'b0;
            assign q_i = 8'd0;
            assign q_codes = 256'd0;
            assign q_e = 10'd0;
            assign q_y = 512'd0;
            assign qf = {(G / 32 + 1){1'b0}};
        end
    endgenerate

    wire f_any = (|lf) || (|cf) || (|tf_any) || f_head || (|rf) || (|qf);
    reg flt;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) flt <= 1'b0;
        else if (go) flt <= 1'b0;
        else if (f_any) flt <= 1'b1;
    assign fault = flt;
endmodule
