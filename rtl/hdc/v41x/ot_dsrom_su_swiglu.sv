`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DS-ROM recovery (SU chains, lever su_swiglu, 2026-10-04): FUSED 1.2 GHz pipelines for the serial stream-unit
// chains ffn.swiglu -> ffn.route_w -> ffn.quant2 and for the stream-bound quantiser nodes attn.z_quant and
// attn.idx.q.  New files only, default-off: nothing existing is swapped or edited; a source list opts in.  Built
// for the 1.2 GHz domain with rtl/hdc/ot_hdc_fastfp_lat_f12.sv (+ ot_hdc_fp32_f12.sv): ot_hdc_qmul_lat LAT 5 ->
// ot_hdc_fp32_mul_f12_l5, ot_hdc_qadd_lat KEEP 1 LAT 4 -> ot_hdc_fp32_add_f12_l4.
//
// ot_dsrom_su_swiglu_lane: one element of the golden's expert activation (tools/dsrom_1m_su.py _replay.expert,
// the SU lowering chain_swiglu), the same IEEE operations in the same order:
//     g' = min(g, limit)  u' = clip(u, -limit, limit)              PRE (the lane's pre_a / clip, okey compares)
//     s  = g' / (exp(-g') + 1)                                      ot_dsrom_exp_f12, ot_hdc_qadd_lat, ot_dsrom_fdiv_f12
//     t  = s * u'                                                   ot_hdc_qmul_lat
//     a  = t * w            (ROUTED: the routing weight)            ot_hdc_qmul_lat
// and the unrounded a leaves the lane; the BF16 rounding (round to nearest even on the encoding, the lane's OUT
// rnd) is the combinational front of the quantiser's input register.  Depth (PRE register -> a):
//     1 + D_EXP + LA + D_DIV + LM (+ LM routed) = 1 + 76 + 4 + 21 + 5 + 5 = 112 at LM 5 / LA 4 (the 1.2 GHz
//     copies of the SU's exp and divider, rtl/hdc/v41x/ot_dsrom_su_f12.sv: five and two extra stages).
//
// ot_dsrom_su_swiglu: W lanes (W/32 quantiser blocks a vector, W a multiple of 32).  The operands arrive through
// NIN register stages (the hub traverse in: 22 slow stages x 748/504 = 33 at 1.2 GHz; the last one is the lanes'
// input register), the codes / exponents / dequantised BF16 leave through NOUT stages (15 x 748/504 = 23).  The
// quantiser is ot_dsrom_actquant_f12 (rtl/hdc/v41x/ot_dsrom_su_f12.sv: ot_hdc_actquant's function, FP8 E4M3, block 32,
// scale 2^e, staged for 1.2 GHz), one instance per 32 lanes, fixed latency 18.
//
// ot_dsrom_su_qbank: NB ot_dsrom_actquant_f12 instances (NB blocks a beat) for the quantiser-only nodes, with the same
// NIN / NOUT traverse; ROPE = 1 adds the index-q RoPE front, its re/im adds on the 6-cut f12 adder (ot_dsrom_add_f12_l6:
// routed, the LAT-4/LAT-5 adders' compare->align stage missed 0.833 ns by 35-75 ps in all four rope route variants)
// NIN / NOUT traverse; ROPE = 1 adds the index-q RoPE front: each beat is NB/4 rows of 128 (head dim), the last
// 64 elements of a row rotated as adjacent pairs (golden rope_tail: re = a*c - b*s, im = a*s + b*c, BF16), the
// first 64 delayed to match; then FP4 (E2M1, E8M0 scale) QDQ of all four blocks of the row.
// ---------------------------------------------------------------------------
module ot_dsrom_su_swiglu_lane #(
    parameter integer LM = 5,
    parameter integer LA = 4,
    parameter integer ROUTED = 1
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] g,
    input  wire [31:0] u,
    input  wire [31:0] w,
    input  wire [31:0] lim,
    output wire [31:0] a,
    output wire        vo,
    output wire        fault
);
    localparam integer D_EXP = 7 * LM + 6 * LA + 12 + 5;   // ot_dsrom_exp_f12 (two adds on the 6-stage adder)
    localparam integer D_DIV = 21;                    // ot_dsrom_fdiv_f12
    localparam integer KS = 1;
    localparam integer DEPTH = 1 + D_EXP + LA + D_DIV + LM + (ROUTED != 0 ? LM : 0);

    function automatic [31:0] okey(input [31:0] x);
        okey = x[31] ? ~x : {1'b1, x[30:0]};
    endfunction
    // ---- PRE: g' = min(g, lim), u' = clip(u, -lim, lim) (the SU lane's pre_a with amin, and its cclip)
    wire [31:0] k_lim = okey(lim);
    wire [31:0] c_lo = {1'b1, lim[30:0]};
    wire le_g, c_ge_lo, c_le_hi, c_lohi;
    ot_hdc_kge #(.W(32), .K(KS)) u_leg (.a(k_lim), .b(okey(g)), .ge(le_g));
    ot_hdc_kge #(.W(32), .K(KS)) u_cgl (.a(okey(u)), .b(okey(c_lo)), .ge(c_ge_lo));
    ot_hdc_kge #(.W(32), .K(KS)) u_clh (.a(k_lim), .b(okey(u)), .ge(c_le_hi));
    ot_hdc_kge #(.W(32), .K(KS)) u_clo (.a(k_lim), .b(okey(c_lo)), .ge(c_lohi));
    reg [31:0] p_g, p_u, p_w;
    reg        p_v;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p_v <= 1'b0; else p_v <= v;
    end
    always @(posedge clk) begin
        p_g <= le_g ? g : lim;
        p_u <= c_ge_lo ? (c_le_hi ? u : lim) : (c_lohi ? c_lo : lim);
        p_w <= w;
    end
    // ---- s = g' / (exp(-g') + 1)
    wire [31:0] y_exp, den, y_div, g_d, u_d, w_d;
    wire f_e, f_den, f_div, f_m1, f_m2;
    wire [D_EXP:0] ve;
    ot_hdc_vline #(.D(D_EXP)) u_ve (.clk(clk), .rst_n(rst_n), .v(p_v), .vd(ve));
    ot_dsrom_exp_f12 #(.LM(LM), .LA(LA)) u_exp (.clk(clk), .rst_n(rst_n), .v(p_v), .x({~p_g[31], p_g[30:0]}),
                                                .y(y_exp), .vo(), .fault(f_e));
    ot_hdc_qadd_lat #(.KEEP(KS), .LAT(LA)) u_den (clk, rst_n, ve[D_EXP], y_exp, 32'h3F800000, den, f_den);
    ot_hdc_delay #(.W(32), .D(D_EXP + LA)) u_gd (.clk(clk), .rst_n(rst_n), .d(p_g), .q(g_d));
    wire [LA:0] vdn;
    ot_hdc_vline #(.D(LA)) u_vdn (.clk(clk), .rst_n(rst_n), .v(ve[D_EXP]), .vd(vdn));
    wire v_div;
    ot_dsrom_fdiv_f12 u_div (.clk(clk), .rst_n(rst_n), .v(vdn[LA]), .a(g_d), .b(den), .y(y_div), .vo(v_div),
                            .fault(f_div));
    // ---- t = s * u'
    ot_hdc_delay #(.W(32), .D(D_EXP + LA + D_DIV)) u_ud (.clk(clk), .rst_n(rst_n), .d(p_u), .q(u_d));
    wire [31:0] t;
    ot_hdc_qmul_lat #(LM) u_m1 (clk, rst_n, v_div, y_div, u_d, t, f_m1);
    wire [LM:0] vm1;
    ot_hdc_vline #(.D(LM)) u_vm1 (.clk(clk), .rst_n(rst_n), .v(v_div), .vd(vm1));
    generate if (ROUTED != 0) begin : g_w
        // ---- a = t * w (golden mul(weight, a): binary32 multiply commutes bit for bit)
        ot_hdc_delay #(.W(32), .D(D_EXP + LA + D_DIV + LM)) u_wd (.clk(clk), .rst_n(rst_n), .d(p_w), .q(w_d));
        ot_hdc_qmul_lat #(LM) u_m2 (clk, rst_n, vm1[LM], t, w_d, a, f_m2);
        wire [LM:0] vm2;
        ot_hdc_vline #(.D(LM)) u_vm2 (.clk(clk), .rst_n(rst_n), .v(vm1[LM]), .vd(vm2));
        assign vo = vm2[LM];
    end else begin : g_nw
        assign a = t; assign vo = vm1[LM]; assign f_m2 = 1'b0; assign w_d = 32'd0;
    end endgenerate
    // a fault is reported with its element (the units flag nonfinite operands / overflow)
    reg [DEPTH:0] fl;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fl <= 0;
        else fl <= {fl[DEPTH-1:0], 1'b0} | {{(DEPTH){1'b0}}, f_e | f_den | f_div | f_m1 | f_m2};
    end
    assign fault = |fl;
endmodule

// BF16 round-to-nearest-even of a binary32 word (the SU lane's OUT rnd), as a binary32 word
module ot_dsrom_su_bf16rnd (input wire [31:0] x, output wire [31:0] y);
    wire [15:0] hi;
    ot_hdc_kinc #(.W(16), .K(1)) u (.a(x[31:16]), .inc(x[15] & (x[16] | (|x[14:0]))), .y(hi));
    assign y = {hi, 16'd0};
endmodule

module ot_dsrom_su_swiglu #(
    parameter integer QLAT = 5,         // the quantisers' scale multiply latency (5 | 6)
    parameter integer W = 1024,
    parameter integer NIN = 33,
    parameter integer NOUT = 23,
    parameter integer ROUTED = 1,
    parameter integer LM = 5,
    parameter integer LA = 4
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              v,
    input  wire [32*W-1:0]   g,
    input  wire [32*W-1:0]   u,
    input  wire [32*W-1:0]   w,          // the lane's routing weight (its expert's), unused when ROUTED = 0
    input  wire [31:0]       lim,
    output wire              vo,
    output wire [8*W-1:0]    q,          // FP8 E4M3 codes
    output wire [10*W/32-1:0] e,         // per block: scale exponent (signed)
    output wire [16*W-1:0]   y,          // dequantised BF16 (qdq_fp8)
    output wire              fault
);
    localparam integer NB = W / 32;
    // ---- hub traverse in (the last stage is the lanes' input register); the valid has its own reset line
    wire [96*W-1:0] dq;
    ot_hdc_delay #(.W(96*W), .D(NIN)) u_in (.clk(clk), .rst_n(rst_n), .d({w, u, g}), .q(dq));
    wire [32*W-1:0] gi = dq[32*W-1:0], ui = dq[64*W-1:32*W], wi = dq[96*W-1:64*W];
    wire [NIN:0] vin;
    ot_hdc_vline #(.D(NIN)) u_vin (.clk(clk), .rst_n(rst_n), .v(v), .vd(vin));
    wire [32*W-1:0] a;
    wire [W-1:0] av, af;
    genvar l, b;
    generate for (l = 0; l < W; l = l + 1) begin : g_l
        ot_dsrom_su_swiglu_lane #(.LM(LM), .LA(LA), .ROUTED(ROUTED)) u (.clk(clk), .rst_n(rst_n), .v(vin[NIN]),
            .g(gi[32*l +: 32]), .u(ui[32*l +: 32]), .w(wi[32*l +: 32]), .lim(lim), .a(a[32*l +: 32]), .vo(av[l]),
            .fault(af[l]));
    end endgenerate
    // ---- BF16 rounding (combinational) into the quantisers' input register
    wire [32*W-1:0] ab;
    wire [NB-1:0] qv, qf;
    wire [8*W-1:0] qq;
    wire [10*NB-1:0] qe;
    wire [16*W-1:0] qy;
    generate for (l = 0; l < W; l = l + 1) begin : g_r
        ot_dsrom_su_bf16rnd u (.x(a[32*l +: 32]), .y(ab[32*l +: 32]));
    end endgenerate
    generate for (b = 0; b < NB; b = b + 1) begin : g_q
        ot_dsrom_actquant_f12 #(.MLAT(QLAT)) u (.clk(clk), .rst_n(rst_n), .v(av[0]), .fp4(1'b0), .x(ab[1024*b +: 1024]), .vo(qv[b]),
                           .q(qq[256*b +: 256]), .e(qe[10*b +: 10]), .y(qy[512*b +: 512]), .fault(qf[b]));
    end endgenerate
    // ---- hub traverse out
    localparam integer OW = 1 + 8 * W + 10 * NB + 16 * W;
    wire [OW-1:0] oq;
    ot_hdc_delay #(.W(OW), .D(NOUT)) u_out (.clk(clk), .rst_n(rst_n), .d({(|qf) | (|af), qq, qe, qy}), .q(oq));
    wire [NOUT:0] vout;
    ot_hdc_vline #(.D(NOUT)) u_vout (.clk(clk), .rst_n(rst_n), .v(qv[0]), .vd(vout));
    assign vo = vout[NOUT];
    assign {fault, q, e, y} = oq;
endmodule

// NB quantiser instances (NB blocks a beat), FP8 or FP4 (E8M0) per beat; ROPE = 1: index-q RoPE front
module ot_dsrom_su_qbank #(
    parameter integer QLAT = 5,         // the quantisers' scale multiply latency (5 | 6)
    parameter integer NB = 32,
    parameter integer NIN = 33,
    parameter integer NOUT = 23,
    parameter integer ROPE = 0,
    parameter integer LM = 5,
    parameter integer LA = 4
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               v,
    input  wire               fp4,
    input  wire [1024*NB-1:0] x,
    input  wire [2047:0]      cs,        // ROPE: {sin[31:0], cos[31:0]} binary32 words (32 pairs), the row tail's table
    output wire               vo,
    output wire [256*NB-1:0]  q,
    output wire [10*NB-1:0]   e,
    output wire [512*NB-1:0]  y,
    output wire               fault
);
    localparam integer N = 32 * NB;
    wire [1024*NB:0] dq;
    ot_hdc_delay #(.W(1024*NB + 1), .D(NIN)) u_in (.clk(clk), .rst_n(rst_n), .d({fp4, x}), .q(dq));
    wire [NIN:0] vin;
    ot_hdc_vline #(.D(NIN)) u_vin (.clk(clk), .rst_n(rst_n), .v(v), .vd(vin));
    wire [1024*NB-1:0] xi = dq[1024*NB-1:0];
    wire fp4i = dq[1024*NB];
    wire [1024*NB-1:0] xr;           // the quantisers' (unrounded) input words
    wire               vq, fp4q;
    wire               frope;
    genvar k, b;
    generate if (ROPE != 0) begin : g_rope
        localparam integer DR = LM + 6;    // a*c (|| b*s) then the add on the 6-cut f12 adder
        wire [N-1:0] fm, fa;
        for (k = 0; k < N; k = k + 1) begin : g_e
            localparam integer col = k % 128;
            if (col < 64) begin : g_pass
                ot_hdc_delay #(.W(32), .D(DR)) u_d (.clk(clk), .rst_n(rst_n), .d(xi[32*k +: 32]), .q(xr[32*k +: 32]));
                assign fm[k] = 1'b0; assign fa[k] = 1'b0;
            end else begin : g_rot
                localparam integer pr = (col - 64) / 2;
                localparam integer odd = (col - 64) % 2;
                // even (re): a*c + b*(-s);  odd (im): b*c + a*s   (the SU lane's QM_ALT_NP; golden rope_tail)
                wire [31:0] self = xi[32*k +: 32];
                wire [31:0] mate = xi[32*(odd ? k - 1 : k + 1) +: 32];
                wire [31:0] c = cs[32*pr +: 32], s = cs[1024 + 32*pr +: 32];
                // one rotation element (ot_dsrom_su_rope_el), the routed minimum component of the RoPE front
                ot_dsrom_su_rope_el #(.LM(LM), .ODD(odd)) u_el (.clk(clk), .rst_n(rst_n), .v(vin[NIN]), .self(self),
                    .mate(mate), .c(c), .s(s), .y(xr[32*k +: 32]), .fault(fa[k]));
                assign fm[k] = 1'b0;
            end
        end
        wire [DR:0] vr;
        ot_hdc_vline #(.D(DR)) u_vr (.clk(clk), .rst_n(rst_n), .v(vin[NIN]), .vd(vr));
        ot_hdc_delay #(.W(1), .D(DR)) u_f4 (.clk(clk), .rst_n(rst_n), .d(fp4i), .q(fp4q));
        assign vq = vr[DR];
        reg [DR+1:0] fl;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) fl <= 0; else fl <= {fl[DR:0], (|fm) | (|fa)};
        end
        assign frope = |fl;
    end else begin : g_norope
        assign xr = xi; assign vq = vin[NIN]; assign fp4q = fp4i; assign frope = 1'b0;
    end endgenerate
    wire [NB-1:0] qv, qf;
    wire [256*NB-1:0] qq;
    wire [10*NB-1:0] qe;
    wire [512*NB-1:0] qy;
    generate for (b = 0; b < NB; b = b + 1) begin : g_q
        wire [1023:0] xb;
        for (k = 0; k < 32; k = k + 1) begin : g_r
            if (ROPE != 0) begin : g_rr
                ot_dsrom_su_bf16rnd u (.x(xr[1024*b + 32*k +: 32]), .y(xb[32*k +: 32]));
            end else begin : g_nr
                assign xb[32*k +: 32] = xr[1024*b + 32*k +: 32];
            end
        end
        ot_dsrom_actquant_f12 #(.MLAT(QLAT)) u (.clk(clk), .rst_n(rst_n), .v(vq), .fp4(fp4q), .x(xb), .vo(qv[b]),
                           .q(qq[256*b +: 256]), .e(qe[10*b +: 10]), .y(qy[512*b +: 512]), .fault(qf[b]));
    end endgenerate
    wire [778*NB:0] oq;
    ot_hdc_delay #(.W(778*NB + 1), .D(NOUT)) u_out (.clk(clk), .rst_n(rst_n), .d({(|qf) | frope, qq, qe, qy}),
                                                    .q(oq));
    wire [NOUT:0] vout;
    ot_hdc_vline #(.D(NOUT)) u_vout (.clk(clk), .rst_n(rst_n), .v(qv[0]), .vd(vout));
    assign vo = vout[NOUT];
    assign {fault, q, e, y} = oq;
endmodule

// ---------------------------------------------------------------------------
// ot_dsrom_su_rope_el: one index-q RoPE element (golden rope_tail; the SU lane's QM_ALT_NP): even (re) a*c + b*(-s),
// odd (im) b*c + a*s, the two products on the f12 multiplier (LM) and the add on the six-cut f12 adder
// (ot_dsrom_add_f12_l6).  Latency LM + 6.  The qbank's RoPE front is 2 x 32 of these a 128-element row.
// ---------------------------------------------------------------------------
module ot_dsrom_su_rope_el #(
    parameter integer LM = 5,
    parameter integer ODD = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] self,
    input  wire [31:0] mate,
    input  wire [31:0] c,
    input  wire [31:0] s,
    output wire [31:0] y,
    output wire        fault
);
    wire [31:0] p1, p2;
    wire f1, f2, fa;
    ot_hdc_qmul_lat #(LM) u_m1 (clk, rst_n, v, self, c, p1, f1);
    ot_hdc_qmul_lat #(LM) u_m2 (clk, rst_n, v, mate, {s[31] ^ (ODD == 0), s[30:0]}, p2, f2);
    wire [LM:0] vm;
    ot_hdc_vline #(.D(LM)) u_vm (.clk(clk), .rst_n(rst_n), .v(v), .vd(vm));
    ot_dsrom_add_f12_l6 u_a (clk, rst_n, vm[LM], p1, p2, y, fa);
    assign fault = f1 | f2 | fa;
endmodule

// ---------------------------------------------------------------------------
// ot_dsrom_su_rope_slice: the routable hardened element of the qbank RoPE front (owner closure procedure: a block
// whose route exceeds ~3 h is split into replicated pieces with registered boundaries).  P rotation pairs (2P
// ot_dsrom_su_rope_el) between the qbank's registered operands (the input traverse's last stage, and the position's
// cos/sin table words, registered here) and the quantiser's input register (ot_dsrom_actquant_f12 S0): the BF16
// rounding of the result and that register are inside, so every path of the front is register to register.
// ---------------------------------------------------------------------------
module ot_dsrom_su_rope_slice #(
    parameter integer P = 4,
    parameter integer LM = 5
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              v,
    input  wire [64*P-1:0]   x,
    input  wire [64*P-1:0]   cs,        // {sin[P], cos[P]}
    output wire              vo,
    output reg  [64*P-1:0]   y,
    output reg               fault
);
    reg [64*P-1:0] xq, csq;
    reg            vq;
    always @(posedge clk or negedge rst_n) if (!rst_n) vq <= 1'b0; else vq <= v;
    always @(posedge clk) begin xq <= x; csq <= cs; end
    wire [64*P-1:0] yr, yb;
    wire [2*P-1:0]  f;
    genvar k;
    generate for (k = 0; k < 2 * P; k = k + 1) begin : g_e
        ot_dsrom_su_rope_el #(.LM(LM), .ODD(k % 2)) u_el (.clk(clk), .rst_n(rst_n), .v(vq), .self(xq[32*k +: 32]),
            .mate(xq[32*(k ^ 1) +: 32]), .c(csq[32*(k/2) +: 32]), .s(csq[32*P + 32*(k/2) +: 32]), .y(yr[32*k +: 32]),
            .fault(f[k]));
        ot_dsrom_su_bf16rnd u_r (.x(yr[32*k +: 32]), .y(yb[32*k +: 32]));
    end endgenerate
    wire [LM+6:0] vd;
    ot_hdc_vline #(.D(LM + 6)) u_v (.clk(clk), .rst_n(rst_n), .v(vq), .vd(vd));
    reg vr;
    always @(posedge clk or negedge rst_n) if (!rst_n) vr <= 1'b0; else vr <= vd[LM + 6];
    always @(posedge clk) y <= yb;
    always @(posedge clk or negedge rst_n) if (!rst_n) fault <= 1'b0; else fault <= |f;
    assign vo = vr;
endmodule
