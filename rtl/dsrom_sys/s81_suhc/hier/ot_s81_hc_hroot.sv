`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_hroot (s81-suhc-hier-1011, 2026-10-11): the root of the hierarchical S81 HC slab (ot_s81_hc_hier).  It
// keeps ot_s81_hc_core's engine-side contract (job intake, done / tag, VM read and write slots, y valid/ready) and
// the job sequencing; the per-element work runs in the KT row-group tiles (ot_s81_hc_tile).  It also holds the
// scalar tail of the norm: the cross-tile sum-of-squares tree (leaves ordered bank-major, tile-minor = the golden
// pairwise tree's top levels above the tiles' aligned subtrees), the vector levels (the golden tree's top levels over
// NV vectors padded to a power of two, a right subtree of padding passes its left value), / D (ot_dsrom_divc), + eps,
// rsqrt (ot_dsrom_rsqrt), and broadcasts r back on the forward bus.
// Forward bus out (fv / fd, registered), y beat out (aligned with fv / fd), return packet in (rv / rd, pin flopped).
// MUT (bench negative controls, 0 in silicon) as ot_s81_hc_core: 1 POST does not write h back; 2 POST / NORM use the
// other slot's h; 3 NORM skipped; 4 done one write early; 5 done tag op bit flipped.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_hroot #(
    parameter integer NG = 256, D = 5120, KT = 8, S_RD = 2, S_WR = 8, ML = 5, AL = 4, RW = 2, MUT = 0
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   e_cmd_v,
    input  wire [83:0]            e_cmd_d,
    output wire                   e_cmd_ready,
    output reg                    e_done_v,
    output reg  [7:0]             e_done_tag,
    input  wire                   y_v,
    output wire                   y_rdy,
    input  wire [NG*32-1:0]       y_d,
    output reg  [S_RD-1:0]        rq_v,
    output reg  [S_RD*14-1:0]     rq_row,
    input  wire [S_RD-1:0]        rs_v,
    input  wire [S_RD*512-1:0]    rs_d,
    output reg  [S_WR-1:0]        wq_v,
    output reg  [S_WR*14-1:0]     wq_row,
    output reg  [S_WR*16-1:0]     wq_mask,
    output reg  [S_WR*512-1:0]    wq_d,
    output wire                   busy,
    output reg                    fault,
    output reg  [3:0]             fault_code,
    output reg  [31:0]            st_jobs,
    // tile buses
    output reg  [S_RD+4:0]        fv,
    output reg  [FDW-1:0]         fd,
    output reg  [NG*32-1:0]       yo,
    input  wire [S_WR+3:0]        rv_in,
    input  wire [RDW-1:0]         rd_in
);
    localparam integer N    = 4 * NG;
    localparam integer NR   = D / NG;
    localparam integer NV   = D / N;
    localparam integer HROWS = NR * NG / 8;
    localparam integer CROWS = N / 64;
    localparam integer EROWS = (N + 1023) / 1024;
    localparam integer YROWS = N / 32;
    localparam integer GROWS = D / 16;
    localparam integer LA = AL, LM = ML;
    localparam integer O_RK = 0, O_RS = 2, O_RG = 3, O_RC = 5, O_RD = O_RC + S_RD * 16, O_PB = O_RD + S_RD * 512,
                       O_NG = O_PB + 12, O_NV = O_NG + 6, O_R = O_NV + 8, O_HS = O_R + 32, FDW = O_HS + 1;
    localparam integer P_T = 0, P_I = 2 * S_WR, P_Q = P_I + 8 * S_WR, P_D = P_Q + 16 * S_WR, P_PI = P_D + 512 * S_WR,
                       P_PD = P_PI + 8, RDW = P_PD + KT * 128;
    localparam [2:0] K_HLOAD = 0, K_HSTORE = 1, K_COEF = 2, K_POST = 3, K_NORM = 4, K_GAIN = 5;

    reg         run;
    reg  [2:0]  kind;
    reg         jslot;
    reg  [7:0]  jtag;
    reg  [13:0] base;
    reg  [1:0]  gsel;
    reg         f_q, f_y, st0;
    reg  [15:0] ci, cr, cw, nw, post_ob;
    reg  [31:0] cf_eps [0:1];
    assign e_cmd_ready = !run && !fault;
    assign busy = run;
    wire take = e_cmd_v && e_cmd_ready;
    wire [23:0] c_arg = e_cmd_d[30:7];
    wire hs = (MUT == 2 && (kind == K_POST || kind == K_NORM)) ? ~jslot : jslot;
    assign y_rdy = run && (kind == K_POST) && (ci < NR) && !fault;
    wire y_take = y_v && y_rdy;

    // return packet pin flops
    reg [S_WR+3:0] rv;
    reg [RDW-1:0]  rd;
    always @(posedge clk or negedge rst_n) if (!rst_n) rv <= 0; else rv <= rv_in;
    always @(posedge clk) rd <= rd_in;

    // ---------------------------------------------------------------- norm scalar tail
    reg ngo;                                             // the norm job's go (clears the vector levels)
    localparam integer NL = 4 * KT;
    localparam integer LT = $clog2(NL);
    wire [LT*LA:0] tvv;
    ot_hdc_vline #(.D(LT * LA > 0 ? LT * LA : 1)) u_tv (.clk(clk), .rst_n(rst_n), .v(rv[S_WR]), .vd(tvv));
    wire [7:0] tvi;
    ot_hdc_delay #(.W(8), .D(LT * LA)) u_tvi (.clk(clk), .rst_n(rst_n), .d(rd[P_PI +: 8]), .q(tvi));
    wire [31:0] tn [0:LT][0:NL-1];
    wire [LT:0] tf;
    genvar c, k, n;
    generate
        for (c = 0; c < NL; c = c + 1) begin : g_l0                // leaf c = bank c / KT, tile c % KT
            assign tn[0][c] = rd[P_PD + 128 * (c % KT) + 32 * (c / KT) +: 32];
        end
        assign tf[0] = 1'b0;
        for (k = 1; k <= LT; k = k + 1) begin : g_tl
            wire [(NL >> k)-1:0] f;
            for (c = 0; c < (NL >> k); c = c + 1) begin : g_tn
                ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, tvv[LA * (k - 1)], tn[k - 1][2 * c], tn[k - 1][2 * c + 1], tn[k][c], f[c]);
            end
            for (c = (NL >> k); c < NL; c = c + 1) begin : g_tz
                assign tn[k][c] = 32'd0;
            end
            assign tf[k] = |f;
        end
    endgenerate
    wire        vsum_v = tvv[LT * LA];
    wire [31:0] vsum = tn[LT][0];
    localparam integer NVP = (NV <= 1) ? 1 : (1 << $clog2(NV));
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    wire [31:0] nv_ [1:2*NVP-1];
    wire        nd [1:2*NVP-1];
    wire        np [1:2*NVP-1];
    wire [NVP:0] nf;
    assign nf[0] = 1'b0;
    assign nf[NVP] = 1'b0;
    generate
        for (n = NVP; n < 2 * NVP; n = n + 1) begin : g_leaf
            reg [31:0] val;
            reg        vld;
            wire       hit = vsum_v && tvi == n - NVP;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) vld <= 1'b0;
                else if (ngo) vld <= 1'b0;
                else if (hit) vld <= 1'b1;
            always @(posedge clk) if (hit) val <= vsum;
            assign np[n] = hit;
            assign nd[n] = vld || hit;
            assign nv_[n] = vld ? val : vsum;
        end
        for (n = 1; n < NVP; n = n + 1) begin : g_vn
            localparam integer H = $clog2(NVP) - ($clog2(n + 1) - 1);
            if ((((2 * n + 1) << (H - 1)) - NVP) < NV) begin : g_add
                reg st, vld;
                reg [31:0] val;
                wire [LAV:0] av;
                wire [31:0] s;
                wire fire = nd[2 * n] && nd[2 * n + 1] && !st && !ngo;
                ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rst_n), .v(fire), .vd(av));
                ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rst_n, fire, nv_[2 * n], nv_[2 * n + 1], s, nf[n]);
                always @(posedge clk or negedge rst_n) begin
                    if (!rst_n) begin st <= 1'b0; vld <= 1'b0; end
                    else if (ngo) begin st <= 1'b0; vld <= 1'b0; end
                    else begin
                        if (fire) st <= 1'b1;
                        if (av[LAV]) vld <= 1'b1;
                    end
                end
                always @(posedge clk) if (av[LAV]) val <= s;
                assign np[n] = av[LAV];
                assign nd[n] = vld || av[LAV];
                assign nv_[n] = vld ? val : s;
            end else begin : g_pass
                assign nv_[n] = nv_[2 * n];
                assign nd[n] = nd[2 * n];
                assign np[n] = np[2 * n];
                assign nf[n] = 1'b0;
            end
        end
    endgenerate
    wire        ss_v = np[1] && !ngo;
    wire [31:0] ss = nv_[1];
    wire [32:0] ssw;
    ot_hdc_delay #(.W(33), .D(RW), .RESET(1)) u_rw (.clk(clk), .rst_n(rst_n), .d({ss_v, ss}), .q(ssw));
    function automatic integer tz(input integer x);
        integer t;
        begin t = 0; while (t < 31 && ((x >> t) & 1) == 0) t = t + 1; tz = t; end
    endfunction
    localparam integer DK = tz(D);
    localparam integer DF = D >> DK;
    wire [31:0] mq, me, rr_;
    wire        mq_v, rr_v, f_div, f_eps, f_rsq;
    reg  [31:0] n_eps;
    ot_dsrom_divc #(.F(DF), .K(DK)) u_div (.clk(clk), .rst_n(rst_n), .v(ssw[32]), .x(ssw[31:0]), .y(mq), .vo(mq_v), .fault(f_div));
    wire [LA:0] ve;
    ot_hdc_vline #(.D(LA)) u_ve (.clk(clk), .rst_n(rst_n), .v(mq_v), .vd(ve));
    ot_dsrom_qadd #(.LAT(LA)) u_eps (clk, rst_n, mq_v, mq, n_eps, me, f_eps);
    ot_dsrom_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(clk), .rst_n(rst_n), .v(ve[LA]), .x(me), .y(rr_), .vo(rr_v), .fault(f_rsq));
    wire tail_f = (|tf) || (|nf) || f_div || f_eps || f_rsq;

    // ---------------------------------------------------------------- sequencer
    integer s;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 1'b0; kind <= 0; jslot <= 0; jtag <= 0; base <= 0; gsel <= 0; f_q <= 0; f_y <= 0; st0 <= 0;
            e_done_v <= 1'b0; e_done_tag <= 0; fault <= 1'b0; fault_code <= 0; st_jobs <= 0;
            ci <= 0; cr <= 0; cw <= 0; nw <= 0; post_ob <= 0; rq_v <= 0; wq_v <= 0; fv <= 0; ngo <= 1'b0;
        end else begin
            e_done_v <= 1'b0; rq_v <= 0; wq_v <= 0; fv <= 0; ngo <= 1'b0;
            if (tail_f || rv[S_WR+2]) begin fault <= 1'b1; if (!fault) fault_code <= 4'd1; end
            if (rv[S_WR+3]) begin fault <= 1'b1; if (!fault) fault_code <= 4'd4; end
            if (rs_v != 0 && !(run && (kind == K_HLOAD || kind == K_COEF || kind == K_GAIN))) begin
                fault <= 1'b1; if (!fault) fault_code <= 4'd2;
            end
            if (take) begin
                run <= 1'b1; kind <= c_arg[22:20]; jslot <= e_cmd_d[83]; jtag <= {e_cmd_d[83], e_cmd_d[6:0]};
                base <= c_arg[13:0]; gsel <= c_arg[19:18]; f_q <= c_arg[14]; f_y <= c_arg[15]; st0 <= 1'b0;
                ci <= 0; cr <= 0; cw <= 0; post_ob <= 0;
                if (c_arg[23] || c_arg[22:20] > 3'd5 || (c_arg[22:20] == K_NORM && !c_arg[14] && !c_arg[15])) begin
                    fault <= 1'b1; fault_code <= 4'd3;
                end
                nw <= (c_arg[22:20] == K_HSTORE) ? HROWS :
                      (c_arg[22:20] == K_NORM) ? (c_arg[14] ? NV * (CROWS + EROWS) : 0) + (c_arg[15] ? NV * YROWS : 0) : 0;
            end
            // ---------------------------------------------------------- returned VM rows (h store / norm outputs)
            begin : wr
                reg [15:0] n_w;
                n_w = 0;
                for (s = 0; s < S_WR; s = s + 1)
                    if (rv[s] && run) begin : one
                        reg [1:0] t; reg [7:0] v; reg [15:0] q; reg [13:0] a;
                        t = rd[P_T + 2 * s +: 2]; v = rd[P_I + 8 * s +: 8]; q = rd[P_Q + 16 * s +: 16];
                        case (t)
                            2'd0: a = base + v * CROWS + q;
                            2'd1: a = base + NV * CROWS + v * EROWS + q;
                            2'd2: a = base + (f_q ? NV * (CROWS + EROWS) : 0) + v * YROWS + q;
                            default: a = base + q;
                        endcase
                        wq_v[s] <= 1'b1; wq_row[14 * s +: 14] <= a; wq_mask[16 * s +: 16] <= 16'hFFFF;
                        wq_d[512 * s +: 512] <= rd[P_D + 512 * s +: 512];
                        n_w = n_w + 1;
                    end
                if (run && (kind == K_HSTORE || kind == K_NORM) && !fault && !(kind == K_NORM && MUT == 3)) begin
                    cw <= cw + n_w;
                    if (n_w != 0 && cw + n_w >= nw - ((MUT == 4) ? S_WR : 0) && (kind == K_HSTORE || ci == NV + 1)) begin
                        run <= 1'b0; e_done_v <= 1'b1; e_done_tag <= (MUT == 5) ? (jtag ^ 8'h01) : jtag;
                        st_jobs <= st_jobs + 1;
                    end
                end
            end
            if (rr_v) begin fv[S_RD + 3] <= 1'b1; fd[O_R +: 32] <= rr_; end
            if (run && !fault) begin
                case (kind)
                K_HLOAD, K_COEF, K_GAIN: begin
                    for (s = 0; s < S_RD; s = s + 1)
                        if (ci + s < ((kind == K_HLOAD) ? HROWS : (kind == K_COEF) ? 2 : GROWS)) begin
                            rq_v[s] <= 1'b1; rq_row[14 * s +: 14] <= base + ci + s;
                        end
                    ci <= ci + S_RD;
                    begin : rsp
                        reg [15:0] cc;
                        cc = cr;
                        fd[O_RK +: 2] <= (kind == K_HLOAD) ? 2'd0 : (kind == K_GAIN) ? 2'd1 : 2'd2;
                        fd[O_RS] <= (kind == K_HLOAD) ? hs : jslot;
                        fd[O_RG +: 2] <= gsel;
                        for (s = 0; s < S_RD; s = s + 1)
                            if (rs_v[s]) begin
                                fv[s] <= 1'b1; fd[O_RC + 16 * s +: 16] <= cc; fd[O_RD + 512 * s +: 512] <= rs_d[512 * s +: 512];
                                if (kind == K_COEF && cc == 1) cf_eps[jslot] <= rs_d[512 * s + 256 +: 32];
                                cc = cc + 1;
                            end
                        cr <= cc;
                        if (cc == ((kind == K_HLOAD) ? HROWS : (kind == K_COEF) ? 2 : GROWS)) begin
                            run <= 1'b0; e_done_v <= 1'b1; e_done_tag <= (MUT == 5) ? (jtag ^ 8'h01) : jtag;
                            st_jobs <= st_jobs + 1;
                        end
                    end
                end
                K_HSTORE: if (!st0) begin fv[S_RD + 4] <= 1'b1; fd[O_HS] <= hs; st0 <= 1'b1; end
                K_POST: begin
                    if (y_take) begin
                        fv[S_RD] <= 1'b1;
                        fd[O_PB] <= (ci == 0); fd[O_PB + 1] <= (MUT != 1); fd[O_PB + 2] <= hs; fd[O_PB + 3] <= jslot;
                        fd[O_PB + 4 +: 8] <= ci[7:0];
                        ci <= ci + 1;
                    end
                    if (rv[S_WR + 1]) begin
                        post_ob <= post_ob + 1;
                        if (post_ob + 1 == NR - ((MUT == 4) ? 1 : 0)) begin
                            run <= 1'b0; e_done_v <= 1'b1; e_done_tag <= (MUT == 5) ? (jtag ^ 8'h01) : jtag;
                            st_jobs <= st_jobs + 1;
                        end
                    end
                end
                K_NORM: begin
                    if (MUT == 3) begin
                        run <= 1'b0; e_done_v <= 1'b1; e_done_tag <= jtag; st_jobs <= st_jobs + 1;
                    end else if (ci == 0) begin
                        fv[S_RD + 1] <= 1'b1; ngo <= 1'b1; n_eps <= cf_eps[jslot];
                        fd[O_NG] <= hs; fd[O_NG + 1] <= jslot; fd[O_NG + 2 +: 2] <= gsel; fd[O_NG + 4] <= f_q; fd[O_NG + 5] <= f_y;
                        ci <= 1;
                    end else if (ci < NV + 1) begin
                        fv[S_RD + 2] <= 1'b1; fd[O_NV +: 8] <= ci[7:0] - 8'd1;
                        ci <= ci + 1;
                    end
                end
                default: ;
                endcase
            end
        end
    end
    always @(posedge clk) yo <= y_d;
endmodule
