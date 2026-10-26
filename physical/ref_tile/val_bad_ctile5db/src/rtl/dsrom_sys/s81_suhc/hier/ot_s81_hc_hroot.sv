`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_hroot (s81-suhc-hier-1011, 2026-10-11): the root of the hierarchical S81 HC slab (dsfd_sp_hc HIER=1),
// placed in the combine tile ot_s81_hc_comb.  It keeps ot_s81_hc_core's engine-side contract (job intake, done / tag,
// VM read and write slots, y valid/ready) and the job sequencing; the per-element work runs in the column sub-tiles
// (ot_s81_hc_ctile, NCOL chains).  It holds the norm's scalar tail -- the final rungs of the sum-of-squares tree
// (ot_s81_hc_stree OWN 3: the nodes no single chain owns, from the chain roots' exported subtrees), the vector levels,
// / D, + eps, rsqrt, r broadcast -- and the FP8 act-quant of the y rows (one y
// row = one 32-element block; S_RT ot_dsrom_aq12 units on the returned rows: codes rows pair blocks 2r, 2r+1, the
// exponent row collects the vector's blocks).  Write slots: y rows / h rows 0 .. S_RT-1, codes S_RT, S_RT+1, exps S_RT+2.
// MUT (bench negative controls, 0 in silicon) as ot_s81_hc_core: 1 POST does not write h back; 2 POST / NORM use the
// other slot's h; 3 NORM skipped; 4 done one write early; 5 done tag op bit flipped.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_hroot #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_WR = 8, S_RT = 4, ML = 5, AL = 4, RW = 2,
    parameter integer MUT = 0,
    parameter integer NIM = 1                       // imported tree nodes (ot_s81_hc_stree_fn.vh necnt 0 + 1 + 2)
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   e_cmd_v,
    input  wire [83:0]            e_cmd_d,
    output wire                   e_cmd_ready,
    output reg                    e_done_v,
    output reg  [7:0]             e_done_tag,
    input  wire                   y_v,            // a y beat is buffered in the chain roots (data never comes here)
    output wire                   y_rdy,          // taken: its POST forward beat issues next cycle
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
    // forward bus to the chains (the data field carries the VM rows; the chain roots insert the y slices), the
    // merged return bus (the chains' aligned returns ORed), the imported chain subtrees (aligned with the return bus)
    output reg  [S_RD+4:0]        fv,
    output reg  [FSW-1:0]         fd,
    input  wire [S_RT+3:0]        rv_in,
    input  wire [RDW-1:0]         rd_in,
    input  wire [NIM*32-1:0]      im
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
    localparam integer NS   = NG / GS;
    localparam integer NP   = (NS + NCOL - 1) / NCOL;
    localparam integer YW   = NP * GS * 32;
    localparam integer FDD  = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_RK = 0, O_RS = 2, O_RG = 3, O_RC = 5, O_PB = O_RC + S_RD * 16, O_NG = O_PB + 20, O_NV = O_NG + 6,
                       O_R = O_NV + 8, O_HS = O_R + 32, O_D = O_HS + 1, FSW = O_D + S_RD * 512;
    localparam integer P_T = 0, P_I = S_RT, P_Q = P_I + 8 * S_RT, P_PI = P_Q + 16 * S_RT, P_D = P_PI + 8,
                       RDW = P_D + 512 * S_RT;
    localparam integer RVW = S_RT + 4;
`ifndef SYNTHESIS
    initial if (S_WR < S_RT + 3) $fatal(1, "ot_s81_hc_hroot: S_WR >= S_RT + 3 (rows, two codes rows, the exps row)");
`endif
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

    // merged return bus pin flops
    reg [RVW-1:0] rv;
    reg [RDW-1:0] rd;
    reg [NIM*32-1:0] imq;
    always @(posedge clk or negedge rst_n) if (!rst_n) rv <= 0; else rv <= rv_in;
    always @(posedge clk) begin rd <= rd_in; imq <= im; end

    // ---------------------------------------------------------------- norm scalar tail
    reg ngo;                                             // the norm job's go (clears the vector levels)
    localparam integer NL = 4 * NS;
    localparam integer LT = $clog2(NL);
    wire [7:0] tvi;
    ot_hdc_delay #(.W(8), .D(LT * LA)) u_tvi (.clk(clk), .rst_n(rst_n), .d(rd[P_PI +: 8]), .q(tvi));
    wire        vsum_v, tf;
    wire [31:0] vsum;
    ot_s81_hc_stree #(.NS(NS), .NP(NP), .LA(LA), .OWN(3)) u_tree (.clk(clk), .rst_n(rst_n), .v(rv[S_RT]),
        .pk({NP*128{1'b0}}), .im(imq), .ex(), .r_v(vsum_v), .r(vsum), .fault(tf));
    genvar k, n;
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
    // ---------------------------------------------------------------- FP8 act-quant of the returned y rows
    localparam integer N_ = 4 * NG;
    localparam integer CR = (N_ / 64) > 0 ? N_ / 64 : 1, ER = (N_ + 1023) / 1024, YR = N_ / 32;
    wire [S_RT-1:0]    aq_vo, aq_f;
    wire [S_RT*256-1:0] aq_q;
    wire [S_RT*10-1:0] aq_e;
    wire [S_RT*24-1:0] aq_iq;                            // {vector, row} of each unit's block, delayed with it
    genvar u;
    generate for (u = 0; u < S_RT; u = u + 1) begin : g_aq
        reg [1023:0] x;
        integer e_;
        always @(*) for (e_ = 0; e_ < 32; e_ = e_ + 1) x[32 * e_ +: 32] = {rd[P_D + 512 * u + 16 * e_ +: 16], 16'h0000};
        wire [511:0] unused_y;
        wire signed [9:0] e;
        ot_dsrom_aq12 u_aq (.clk(clk), .rst_n(rst_n), .v(rv[u] && !rd[P_T + u] && run && kind == K_NORM), .x(x),
                            .vo(aq_vo[u]), .q(aq_q[256 * u +: 256]), .e(e), .y(unused_y), .fault(aq_f[u]));
        assign aq_e[10 * u +: 10] = e;
        ot_hdc_delay #(.W(24), .D(18)) u_iq (.clk(clk), .rst_n(rst_n), .d({rd[P_I + 8 * u +: 8], rd[P_Q + 16 * u +: 16]}),
                                             .q(aq_iq[24 * u +: 24]));
    end endgenerate
    reg [511:0] er;                                      // the vector's exponent row being collected
    wire tail_f = tf || (|nf) || f_div || f_eps || f_rsq || (|aq_f);

    // ---------------------------------------------------------------- sequencer
    integer s;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 1'b0; kind <= 0; jslot <= 0; jtag <= 0; base <= 0; gsel <= 0; f_q <= 0; f_y <= 0; st0 <= 0;
            e_done_v <= 1'b0; e_done_tag <= 0; fault <= 1'b0; fault_code <= 0; st_jobs <= 0;
            ci <= 0; cr <= 0; cw <= 0; nw <= 0; post_ob <= 0; rq_v <= 0; wq_v <= 0; fv <= 0; ngo <= 1'b0;
        end else begin
            e_done_v <= 1'b0; rq_v <= 0; wq_v <= 0; fv <= 0; ngo <= 1'b0;
            if (tail_f || rv[S_RT+2]) begin fault <= 1'b1; if (!fault) fault_code <= 4'd1; end
            if (rv[S_RT+3]) begin fault <= 1'b1; if (!fault) fault_code <= 4'd4; end
            if (rs_v != 0 && !(run && (kind == K_HLOAD || kind == K_COEF || kind == K_GAIN))) begin
                fault <= 1'b1; if (!fault) fault_code <= 4'd2;
            end
            if (take) begin
                er <= 512'd0;
                run <= 1'b1; kind <= c_arg[22:20]; jslot <= e_cmd_d[83]; jtag <= {e_cmd_d[83], e_cmd_d[6:0]};
                base <= c_arg[13:0]; gsel <= c_arg[19:18]; f_q <= c_arg[14]; f_y <= c_arg[15]; st0 <= 1'b0;
                ci <= 0; cr <= 0; cw <= 0; post_ob <= 0;
                if (c_arg[23] || c_arg[22:20] > 3'd5 || (c_arg[22:20] == K_NORM && !c_arg[14] && !c_arg[15])) begin
                    fault <= 1'b1; fault_code <= 4'd3;
                end
                nw <= (c_arg[22:20] == K_HSTORE) ? HROWS :
                      (c_arg[22:20] == K_NORM) ? (c_arg[14] ? NV * (CROWS + EROWS) : 0) + (c_arg[15] ? NV * YROWS : 0) : 0;
            end
            // ---------------------------------------------------------- returned rows (h store / y), quant outputs
            begin : wr
                reg [15:0] n_w;
                reg [511:0] ern;
                n_w = 0;
                ern = er;
                for (s = 0; s < S_RT; s = s + 1)
                    if (rv[s] && run && (rd[P_T + s] || f_y)) begin : one
                        reg [7:0] v; reg [15:0] q;
                        v = rd[P_I + 8 * s +: 8]; q = rd[P_Q + 16 * s +: 16];
                        wq_v[s] <= 1'b1; wq_mask[16 * s +: 16] <= 16'hFFFF; wq_d[512 * s +: 512] <= rd[P_D + 512 * s +: 512];
                        wq_row[14 * s +: 14] <= rd[P_T + s] ? base + q : base + (f_q ? NV * (CR + ER) : 0) + v * YR + q;
                        n_w = n_w + 1;
                    end
                if (f_q && run && kind == K_NORM)
                    for (s = 0; s < S_RT; s = s + 2) begin : cd             // codes row: blocks 2r (slot s), 2r+1 (s+1)
                        reg [7:0] v; reg [15:0] q;
                        v = aq_iq[24 * s + 16 +: 8]; q = aq_iq[24 * s +: 16];
                        if (aq_vo[s]) begin
                            wq_v[S_RT + s / 2] <= 1'b1; wq_mask[16 * (S_RT + s / 2) +: 16] <= 16'hFFFF;
                            wq_row[14 * (S_RT + s / 2) +: 14] <= base + v * CR + q / 2;
                            wq_d[512 * (S_RT + s / 2) +: 512] <= {aq_vo[s + 1] ? aq_q[256 * (s + 1) +: 256] : 256'd0, aq_q[256 * s +: 256]};
                            n_w = n_w + 1;
                        end
                    end
                if (f_q && run && kind == K_NORM)
                    for (s = 0; s < S_RT; s = s + 1)
                        if (aq_vo[s]) begin : ex
                            reg [7:0] v; reg [15:0] q;
                            v = aq_iq[24 * s + 16 +: 8]; q = aq_iq[24 * s +: 16];
                            ern[16 * (q % 32) +: 16] = {6'd0, aq_e[10 * s +: 10]};
                            if (q == YR - 1) begin
                                wq_v[S_RT + 2] <= 1'b1; wq_mask[16 * (S_RT + 2) +: 16] <= 16'hFFFF;
                                wq_row[14 * (S_RT + 2) +: 14] <= base + NV * CR + v * ER;
                                wq_d[512 * (S_RT + 2) +: 512] <= ern;
                                ern = 512'd0;
                                n_w = n_w + 1;
                            end
                        end
                er <= ern;
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
                                fv[s] <= 1'b1; fd[O_RC + 16 * s +: 16] <= cc; fd[O_D + 512 * s +: 512] <= rs_d[512 * s +: 512];
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
                        fd[O_PB + 4 +: 16] <= ci;
                        ci <= ci + 1;
                    end
                    if (rv[S_RT + 1]) begin
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
endmodule
