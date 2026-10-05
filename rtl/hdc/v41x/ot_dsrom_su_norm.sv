`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DS-ROM recovery, SU chains (lever su_norm): ONE fused 1.2 GHz pipeline for an RMSNorm chain of the V4.1 decode
// layer, with no vector-memory round trip between its steps:
//
//   HC = 1  hc_pre:  x_j = bf16(((h0_j*p0 + h1_j*p1) + h2_j*p2) + h3_j*p3)   (tools/hdc_golden_v41 Model.hc_pre:
//                    to_bf16(seqsum([mul(pre[k], h[k])])))
//   HC = 0  x_j is the input itself (q latent, kv latent: already BF16 values)
//   then    ss   = csum(x_j * x_j)                (R-ARITH chunk8: chunks of 8 summed sequentially, chunk sums by a
//                                                  pairwise tree padded with +0 to a power of two)
//           r    = rsqrt(ss / D + eps)            (golden div RNE, add, rsqrt = 3 Newton steps from 0x5F3759DF)
//           y_j  = bf16(w_j * (x_j * r))          (rmsnorm_bf16)
//   RD > 0  y's last RD elements rotated as adjacent pairs (rope_tail, forward): re = a*c + (-(b*s)),
//           im = b*c + a*s, BF16
//   QUANT   FP8 act-quant of each 32-element block (ot_hdc_actquant: codes, exponent, dequantised BF16)
//
// The golden's order is kept exactly: the four mix products are independent (one multiply level), the three adds
// are sequential; the square, the 7-add chunk chain and the tree are ot_hdc_v41x_vec_red's contract; the vector
// sums of a D > N row combine by the golden tree's top levels over NV = ceil(D/N) vectors padded to a power of two,
// where a node whose right subtree is all padding PASSES its left value (x + (+0) = x exactly for x >= +0: a sum of
// squares is never -0, every zero result being +0), so a padded level costs nothing.
//
// Layout: lane l of vector v holds element v*N + l (N a power of two >= 8, so every chunk is 8 lanes of one vector
// and a vector's N/8 chunk sums form an aligned subtree of the golden tree).  Lanes past D carry +0.
//
// Timing (1.2 GHz units: ot_hdc_qmul_lat LM 5 / ot_hdc_qadd_lat LA 4 through rtl/hdc/ot_hdc_fastfp_lat_f12.sv):
//   mix LM + 3 LA + 1 (HC), square LM, chain 7 LA, tree log2(N/8) LA, vector levels LA per real add,
//   RW result-wire stages, divide 19 (ot_hdc_v41x_fdiv), + eps LA, rsqrt 1 + 3(3 LM + LA) (ot_hdc_v41x_rsqrt),
//   BW broadcast-wire stages back to the lanes, scale 2 LM + 1, RoPE LM + LA + 1, act-quant 13.
// The x values wait in the lanes (NV words a lane) between the mix and the scale: nothing is written back.
// ---------------------------------------------------------------------------
module ot_dsrom_su_norm #(
    parameter integer N = 1024,         // lanes (a power of two >= 8)
    parameter integer D = 5120,         // row length (a multiple of 8)
    parameter integer HC = 1,           // 1: four-copy hc_pre mix in front; 0: plain input
    parameter integer RD = 0,           // RoPE tail length (0: none; the tail lies in the last vector)
    parameter integer QUANT = 1,        // FP8 act-quant of the output (N a multiple of 32)
    parameter integer RW = 9,           // result wire stages (lane tree -> scalar tail)
    parameter integer BW = 9,           // broadcast wire stages (scalar tail -> lanes)
    parameter integer LM = 5,
    parameter integer LA = 4
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     go,             // a new row starts (clears the vector-level tree)
    input  wire                     in_v,           // one input vector a cycle, v = 0 .. NV-1 in order
    input  wire [(HC ? 4 : 1)*N*32-1:0] in_x,       // HC: copy k of lane l at [(k*N + l)*32 +: 32]
    input  wire [127:0]             pre,            // HC mix weights p0..p3
    input  wire [31:0]              n_f,            // binary32 D (the mean's divisor)
    input  wire [31:0]              eps,
    input  wire                     wl_v,           // gain ROM load: vector wl_i of w
    input  wire [7:0]               wl_i,
    input  wire [N*32-1:0]          wl_d,
    input  wire [(RD ? RD/2 : 1)*32-1:0] cos_t,     // RoPE table (constants of the position)
    input  wire [(RD ? RD/2 : 1)*32-1:0] sin_t,
    output wire                     y_v,            // normalised vector (BF16 values as binary32)
    output wire [7:0]               y_i,
    output wire [N*32-1:0]          y,
    output wire                     r_v,            // the scalar rstd (observability)
    output wire [31:0]              r,
    output wire                     q_v,            // act-quant (QUANT): one vector of blocks a cycle
    output wire [7:0]               q_i,
    output wire [(QUANT ? N/32 : 1)*256-1:0] q_codes,
    output wire [(QUANT ? N/32 : 1)*10-1:0]  q_e,
    output wire [(QUANT ? N/32 : 1)*512-1:0] q_y,
    output wire                     ro_v,           // RoPE output (RD), full vector
    output wire [N*32-1:0]          ro,
    output wire                     fault
);
    localparam integer NV  = (D + N - 1) / N;
    localparam integer NVP = (NV <= 1) ? 1 : (1 << $clog2(NV));
    localparam integer NC  = N / 8;
    localparam integer LT  = $clog2(NC);
    localparam integer DM  = HC ? (LM + 3 * LA + 1) : 0;    // mix depth
    localparam integer DS  = LM + 7 * LA + LT * LA;         // square + chain + tree
    localparam integer DR  = 1 + 3 * (3 * LM + LA);         // ot_hdc_v41x_rsqrt DEPTH
    localparam integer KS  = 1;

    function automatic [31:0] bf16(input [31:0] x);         // RNE to BF16 (tools/hdc_golden.to_bf16)
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

    // ---------------------------------------------------------------- control lines
    localparam integer DY = 2 * LM + 1;                     // scale depth
    wire [(DM > 0 ? DM : 1):0] vm_w;
    ot_hdc_vline #(.D(DM > 0 ? DM : 1)) u_vm (.clk(clk), .rst_n(rst_n), .v(in_v), .vd(vm_w));
    wire [DM:0] vm = vm_w[DM:0];
    wire [7:0] xi;
    ot_hdc_delay #(.W(8), .D(DM)) u_xi (.clk(clk), .rst_n(rst_n), .d(in_i), .q(xi));
    wire x_v = vm[DM];
    wire [DS:0] vs;
    ot_hdc_vline #(.D(DS)) u_vs (.clk(clk), .rst_n(rst_n), .v(x_v), .vd(vs));
    wire [7:0] si;
    ot_hdc_delay #(.W(8), .D(DS)) u_si (.clk(clk), .rst_n(rst_n), .d(xi), .q(si));
    // scale sequencer: vector 0 goes in the cycle the broadcast rstd lands (from the wire), 1 .. NV-1 after it
    wire [32:0] rb;
    reg  [31:0] rl;
    reg         sc_run;
    reg  [7:0]  sc_i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin sc_run <= 1'b0; sc_i <= 8'd0; end
        else if (rb[32]) begin sc_run <= (NV > 1); sc_i <= 8'd1; end
        else if (sc_run) begin
            if (sc_i == NV - 1) sc_run <= 1'b0;
            sc_i <= sc_i + 8'd1;
        end
    end
    always @(posedge clk) if (rb[32]) rl <= rb[31:0];
    wire        sc_go = rb[32] || sc_run;
    wire [7:0]  sc_x  = rb[32] ? 8'd0 : sc_i;
    wire [31:0] sc_r  = rb[32] ? rb[31:0] : rl;
    wire [DY:0] vy;
    ot_hdc_vline #(.D(DY)) u_vy (.clk(clk), .rst_n(rst_n), .v(sc_go), .vd(vy));
    wire [7:0] yi_m, yi_o;
    ot_hdc_delay #(.W(8), .D(LM)) u_yim (.clk(clk), .rst_n(rst_n), .d(sc_x), .q(yi_m));
    ot_hdc_delay #(.W(8), .D(DY)) u_yio (.clk(clk), .rst_n(rst_n), .d(sc_x), .q(yi_o));

    wire [N-1:0]    lf;                 // lane faults
    wire [N*32-1:0] sq;                 // squares (lanes past D: +0)
    wire [NC*32-1:0] cs;                // chunk sums
    wire [NC-1:0]   cf;
    wire [N*32-1:0] yb;

    genvar l, c, k, n;
    generate
        for (l = 0; l < N; l = l + 1) begin : g_lane
            wire [31:0] xl;
            wire [9:0] f;
            if (HC) begin : g_mix
                wire [31:0] m0, m1, m2, m3, m2d, m3d, a1, a2, a3;
                ot_hdc_qmul_lat #(LM) u_m0 (clk, rst_n, in_v, in_x[(0 * N + l) * 32 +: 32], pre[0 +: 32], m0, f[0]);
                ot_hdc_qmul_lat #(LM) u_m1 (clk, rst_n, in_v, in_x[(1 * N + l) * 32 +: 32], pre[32 +: 32], m1, f[1]);
                ot_hdc_qmul_lat #(LM) u_m2 (clk, rst_n, in_v, in_x[(2 * N + l) * 32 +: 32], pre[64 +: 32], m2, f[2]);
                ot_hdc_qmul_lat #(LM) u_m3 (clk, rst_n, in_v, in_x[(3 * N + l) * 32 +: 32], pre[96 +: 32], m3, f[3]);
                ot_hdc_qadd_lat #(.KEEP(KS), .LAT(LA)) u_a1 (clk, rst_n, vm[LM], m0, m1, a1, f[4]);
                ot_hdc_delay #(.W(32), .D(LA)) u_d2 (.clk(clk), .rst_n(rst_n), .d(m2), .q(m2d));
                ot_hdc_qadd_lat #(.KEEP(KS), .LAT(LA)) u_a2 (clk, rst_n, vm[LM + LA], a1, m2d, a2, f[5]);
                ot_hdc_delay #(.W(32), .D(2 * LA)) u_d3 (.clk(clk), .rst_n(rst_n), .d(m3), .q(m3d));
                ot_hdc_qadd_lat #(.KEEP(KS), .LAT(LA)) u_a3 (clk, rst_n, vm[LM + 2 * LA], a2, m3d, a3, f[6]);
                reg [31:0] xr;
                always @(posedge clk) xr <= bf16(a3);
                assign xl = xr;
            end else begin : g_plain
                assign xl = in_x[l * 32 +: 32];
                assign f[6:0] = 7'd0;
            end
            // the x of the row waits here until the rstd comes back
            reg [31:0] xb [0:NV-1];
            always @(posedge clk) if (x_v) xb[xi] <= xl;
            wire live = ({24'd0, xi} * N + l) < D;
            wire [31:0] xs = live ? xl : 32'd0;
            ot_hdc_qmul_lat #(LM) u_sq (clk, rst_n, x_v, xs, xs, sq[l * 32 +: 32], f[7]);
            // gain ROM and the scale y = bf16(w * (x * r))
            reg [31:0] wr [0:NV-1];
            always @(posedge clk) if (wl_v) wr[wl_i] <= wl_d[l * 32 +: 32];
            wire [31:0] p, q;
            ot_hdc_qmul_lat #(LM) u_xr (clk, rst_n, sc_go, xb[sc_x], sc_r, p, f[8]);
            ot_hdc_qmul_lat #(LM) u_w  (clk, rst_n, vy[LM], wr[yi_m], p, q, f[9]);
            reg [31:0] yr;
            always @(posedge clk) yr <= bf16(q);
            assign yb[l * 32 +: 32] = yr;
            assign lf[l] = |f;
        end
        // chunk chains: lane 8c+j joins after j-1 adds
        for (c = 0; c < NC; c = c + 1) begin : g_chunk
            wire [31:0] acc [0:7];
            wire [7:0] f;
            assign acc[0] = sq[(8 * c) * 32 +: 32];
            assign f[0] = 1'b0;
            for (k = 1; k < 8; k = k + 1) begin : g_j
                wire [31:0] sd;
                ot_hdc_delay #(.W(32), .D(LA * (k - 1))) u_sd (.clk(clk), .rst_n(rst_n), .d(sq[(8 * c + k) * 32 +: 32]),
                                                              .q(sd));
                ot_hdc_qadd_lat #(.KEEP(KS), .LAT(LA)) u_a (clk, rst_n, vs[LM + LA * (k - 1)], acc[k - 1], sd, acc[k], f[k]);
            end
            assign cs[c * 32 +: 32] = acc[7];
            assign cf[c] = |f;
        end
    endgenerate

    // in-vector tree: level t has NC >> t nodes
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
                ot_hdc_qadd_lat #(.KEEP(KS), .LAT(LA)) u_a (clk, rst_n, vs[LM + 7 * LA + LA * (k - 1)], tv[k - 1][2 * c],
                                                           tv[k - 1][2 * c + 1], tv[k][c], f[c]);
            end
            for (c = (NC >> k); c < NC; c = c + 1) begin : g_tz
                assign tv[k][c] = 32'd0;
            end
            assign tf_any[k] = |f;
        end
    endgenerate
    wire        vsum_v = vs[DS];
    wire [31:0] vsum = tv[LT][0];

    // vector levels: heap nodes 1 .. 2 NVP - 1 (root 1), leaves NVP + v.  Node n has height
    // h = log2(NVP) - floor(log2 n); its right child's first leaf is ((2n+1) << (h-1)) - NVP.  Every node has a
    // value pulse (the cycle its value first exists: a leaf's arrival, an add's last stage) and a held copy; an add
    // fires in the cycle its second operand pulses, from the pulse value (no latch on the path).
    wire [31:0] nv [1:2*NVP-1];         // the value: the pulse value in the pulse cycle, the held copy after
    wire        nd [1:2*NVP-1];         // available (pulse or held)
    wire        np [1:2*NVP-1];         // pulse
    wire [NVP:0] nf;
    assign nf[0] = 1'b0;
    generate
        for (n = NVP; n < 2 * NVP; n = n + 1) begin : g_leaf
            reg [31:0] val;
            reg        vld;
            wire       hit = vsum_v && si == n - NVP;
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
            if ((((2 * n + 1) << (H - 1)) - NVP) < NV) begin : g_add      // right child real: an add
                reg st, vld;
                reg [31:0] val;
                wire [LA:0] av;
                wire [31:0] s;
                wire fire = nd[2 * n] && nd[2 * n + 1] && !st && !go;
                ot_hdc_vline #(.D(LA)) u_v (.clk(clk), .rst_n(rst_n), .v(fire), .vd(av));
                ot_hdc_qadd_lat #(.KEEP(KS), .LAT(LA)) u_a (clk, rst_n, fire, nv[2 * n], nv[2 * n + 1], s, nf[n]);
                always @(posedge clk or negedge rst_n) begin
                    if (!rst_n) begin st <= 1'b0; vld <= 1'b0; end
                    else if (go) begin st <= 1'b0; vld <= 1'b0; end
                    else begin
                        if (fire) st <= 1'b1;
                        if (av[LA]) vld <= 1'b1;
                    end
                end
                always @(posedge clk) if (av[LA]) val <= s;
                assign np[n] = av[LA];
                assign nd[n] = vld || av[LA];
                assign nv[n] = vld ? val : s;
            end else begin : g_pass                                     // right subtree all padding: x + 0 = x
                assign nv[n] = nv[2 * n];
                assign nd[n] = nd[2 * n];
                assign np[n] = np[2 * n];
                assign nf[n] = 1'b0;
            end
        end
    endgenerate
    // the row's sum: the root's pulse
    wire        ss_v = np[1] && !go;
    wire [31:0] ss = nv[1];

    // ---------------------------------------------------------------- result wire, scalar tail, broadcast wire
    wire [32:0] ssw;
    ot_hdc_delay #(.W(33), .D(RW), .RESET(1)) u_rw (.clk(clk), .rst_n(rst_n), .d({ss_v, ss}), .q(ssw));
    wire [31:0] mq, me, rr;
    wire        mq_v, me_v, rr_v, f_div, f_eps, f_rsq;
    ot_hdc_v41x_fdiv u_div (.clk(clk), .rst_n(rst_n), .v(ssw[32]), .a(ssw[31:0]), .b(n_f), .y(mq), .vo(mq_v), .fault(f_div));
    wire [LA:0] ve;
    ot_hdc_vline #(.D(LA)) u_ve (.clk(clk), .rst_n(rst_n), .v(mq_v), .vd(ve));
    ot_hdc_qadd_lat #(.KEEP(KS), .LAT(LA)) u_eps (clk, rst_n, mq_v, mq, eps, me, f_eps);
    assign me_v = ve[LA];
    ot_hdc_v41x_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(clk), .rst_n(rst_n), .v(me_v), .x(me), .y(rr), .vo(rr_v), .fault(f_rsq));
    assign r_v = rr_v;
    assign r = rr;
    ot_hdc_delay #(.W(33), .D(BW), .RESET(1)) u_bw (.clk(clk), .rst_n(rst_n), .d({rr_v, rr}), .q(rb));
    assign y_v = vy[DY];
    assign y_i = yi_o;
    assign y = yb;

    // ---------------------------------------------------------------- RoPE tail (forward), BF16
    // The tail is the last RD elements of the row: lanes LB-RD .. LB-1 of the last vector (LB = its length); the
    // other vectors (and lanes) pass with the same delay.
    localparam integer DRO = LM + LA + 1;
    localparam integer LB = D - (NV - 1) * N;
    wire [DRO:0] vr;
    ot_hdc_vline #(.D(DRO)) u_vr (.clk(clk), .rst_n(rst_n), .v(y_v), .vd(vr));
    wire [7:0] ro_i;
    ot_hdc_delay #(.W(8), .D(DRO)) u_roi (.clk(clk), .rst_n(rst_n), .d(yi_o), .q(ro_i));
    wire last_ro = (ro_i == NV - 1);
    wire [N-1:0] rf;
    generate
        if (RD > 0) begin : g_rope
            for (l = 0; l < N; l = l + 1) begin : g_rl
                wire [31:0] dl;
                ot_hdc_delay #(.W(32), .D(DRO)) u_d (.clk(clk), .rst_n(rst_n), .d(yb[l * 32 +: 32]), .q(dl));
                if (l >= LB - RD && l < LB) begin : g_rot
                    localparam integer KK = (l - (LB - RD)) / 2;
                    localparam integer ODD = (l - (LB - RD)) % 2;
                    wire [31:0] cc = cos_t[KK * 32 +: 32], sn = sin_t[KK * 32 +: 32];
                    wire [31:0] mine = yb[l * 32 +: 32];
                    wire [31:0] pair = yb[(ODD ? l - 1 : l + 1) * 32 +: 32];
                    wire [31:0] pp, qq, rs;
                    wire f0, f1, f2;
                    ot_hdc_qmul_lat #(LM) u_p (clk, rst_n, y_v, mine, cc, pp, f0);                              // a*c | b*c
                    ot_hdc_qmul_lat #(LM) u_q (clk, rst_n, y_v, pair, ODD ? sn : {~sn[31], sn[30:0]}, qq, f1);  // -(b*s) | a*s
                    ot_hdc_qadd_lat #(.KEEP(KS), .LAT(LA)) u_a (clk, rst_n, vr[LM], pp, qq, rs, f2);
                    reg [31:0] o;
                    always @(posedge clk) o <= bf16(rs);
                    assign ro[l * 32 +: 32] = last_ro ? o : dl;
                    assign rf[l] = last_ro & (f0 | f1 | f2);
                end else begin : g_keep
                    assign ro[l * 32 +: 32] = dl;
                    assign rf[l] = 1'b0;
                end
            end
        end else begin : g_norope
            assign ro = {N * 32{1'b0}};
            assign rf = {N{1'b0}};
        end
    endgenerate
    assign ro_v = (RD > 0) ? vr[DRO] : 1'b0;

    // ---------------------------------------------------------------- FP8 act-quant, one instance a 32-lane block
    wire [N/32:0] qf;
    generate
        if (QUANT) begin : g_q
            wire            qin_v = (RD > 0) ? ro_v : y_v;
            wire [N*32-1:0] qin   = (RD > 0) ? ro : yb;
            wire [7:0]      qin_i = (RD > 0) ? ro_i : yi_o;
            wire [N/32-1:0] vo;
            for (k = 0; k < N / 32; k = k + 1) begin : g_aq
                wire signed [9:0] e;
                ot_hdc_actquant u_aq (.clk(clk), .rst_n(rst_n), .v(qin_v), .fp4(1'b0), .x(qin[k * 1024 +: 1024]),
                                      .vo(vo[k]), .q(q_codes[k * 256 +: 256]), .e(e), .y(q_y[k * 512 +: 512]),
                                      .fault(qf[k]));
                assign q_e[k * 10 +: 10] = e;
            end
            assign q_v = vo[0];
            ot_hdc_delay #(.W(8), .D(13)) u_qi (.clk(clk), .rst_n(rst_n), .d(qin_i), .q(q_i));
            assign qf[N / 32] = 1'b0;
        end else begin : g_nq
            assign q_v = 1'b0;
            assign q_i = 8'd0;
            assign q_codes = 256'd0;
            assign q_e = 10'd0;
            assign q_y = 512'd0;
            assign qf = {(N / 32 + 1){1'b0}};
        end
    endgenerate

    // ---------------------------------------------------------------- faults (sticky)
    reg flt;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) flt <= 1'b0;
        else if (go) flt <= 1'b0;
        else if ((|lf) || (|cf) || (|tf_any) || (|nf) || f_div || f_eps || f_rsq || (|rf) || (|qf)) flt <= 1'b1;
    assign fault = flt;
endmodule
