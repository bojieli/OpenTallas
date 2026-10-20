`timescale 1ns/1ps
// HBM-XLP10 10-20: PIPELINED x-load bench (ot_hgi_sm_xload_static_xqlp = XP ctlx, vs the CLOSED-function cl2 xql).
//   ref : ot_hgi_sm_xload_static_xql (cl2 ctlx), every command run ALONE (its own calendar, launch, wait for x_done):
//         per load i the beat list (edge after launch, xw_addr, xw_grp, 2048-b xw_data) and its FIRST / LAST beat edge.
//   dut : ot_hgi_sm_xload_static_xqlp, ALL commands in ONE calendar at the compiler's pipelined slots
//           at(0) = A0,  at(i+1) = at(i) + max(ISS(i), LAST(i) + 1 - FIRST(i+1))
//         ISS = BF 8 nb gn, BD wb gtp (the issue span; the XP issue engine is free on its last edge).
// PASS: the dut beat stream is exactly the concatenation of the ref loads' beats, each shifted by at(i) (every beat
// edge, addr, grp and all 2048 data bits), N x_done, no fault, no lane fault, and loads overlap (sum ISS < serial).
// Both run on the same VM model (bank content), RD_LAT = the die BUDGET vector on GEN2c NE lanes + die rq pads.
// Commands: 12 DeepSeek SM production shapes (P 1, K 512..7168, fmt BF16 / FP8 / FP4 transitions) + 12 random (P 1..8).
// -DEARLY 1 (compiler mutant: every slot one edge before the law) must FAIL; -DDMUT 8 (RTL: egress xb does not ride
// the pipe) must FAIL; -DDMUT 0 -DEARLY 0 must PASS.  -DNCMD n limits the command count (smoke).
`ifndef EARLY
`define EARLY 0
`endif
`ifndef DMUT
`define DMUT 0
`endif
`ifndef NCMD
`define NCMD 24
`endif
module tb_xp_vm #(
    parameter [63:0] LQ = 64'd0,
    parameter [63:0] LR = 64'd0,
    parameter integer BK = 7
) (
    input  wire               clk,
    input  wire [8*17-1:0]    rq,
    output wire [8*257-1:0]   rr,
    output wire integer       lanefault
);
    reg [31:0] mem [0:32767];
    function automatic [31:0] val(input integer k, input integer h, input integer row, input integer w);
        reg [31:0] r;
        begin
            r = 32'h9E3779B9 * (k * 131 + h * 17 + 1) ^ (row * 32'h85EBCA6B) ^ (w * 32'hC2B2AE35);
            r = r ^ (r >> 15); r = r * 32'h2C1B3C6D; r = r ^ (r >> 12);
            r[30:23] = 8'd100 + 8'(r[7:0] % 50);
            if (r[13:8] == 6'd0) r = 32'h0;
            val = r;
        end
    endfunction
    initial begin
        for (integer k = 0; k < 4; k = k + 1) for (integer h = 0; h < 2; h = h + 1)
            for (integer row = 0; row < 4096; row = row + 1) for (integer w = 0; w < 8; w = w + 1)
                mem[(row * 8 + (k + 4 * h)) * 8 + w] = val(k, h, row, w);
    end
    reg [7:0] lfv = 8'd0;
    assign lanefault = (lfv != 8'd0) ? 1 : 0;
    function automatic [256:0] look(input [16:0] q);
        reg [14:0] s;
        begin
            look = '0; s = q[14:0];
            if (q[16]) begin
                look[256] = 1'b1;
                for (integer w = 0; w < 8; w = w + 1) look[32*w +: 32] = mem[{s[11:0], 3'(w)}];
            end
        end
    endfunction
    genvar gb;
    generate for (gb = 0; gb < 8; gb = gb + 1) begin : g_b
        localparam integer NQ = (LQ >> (8 * gb)) & 64'hFF, NRR = (LR >> (8 * gb)) & 64'hFF;
        wire [16:0] at;
        if (NQ == 0) begin : g_q0
            assign at = rq[gb*17 +: 17];
        end else begin : g_q
            reg [16:0] ql [1:NQ];
            always @(posedge clk) begin ql[1] <= rq[gb*17 +: 17]; for (integer d = 2; d <= NQ; d = d + 1) ql[d] <= ql[d-1]; end
            assign at = ql[NQ];
        end
        reg [256:0] bp [1:BK];
        always @(posedge clk) begin
            if (at[16] && (at[2:0] != 3'(gb) || at[15])) lfv[gb] <= 1'b1;
            bp[1] <= look(at);
            for (integer d = 2; d <= BK; d = d + 1) bp[d] <= bp[d-1];
        end
        if (NRR == 0) begin : g_r0
            assign rr[gb*257 +: 257] = bp[BK];
        end else begin : g_r
            reg [256:0] rl [1:NRR];
            always @(posedge clk) begin rl[1] <= bp[BK]; for (integer d = 2; d <= NRR; d = d + 1) rl[d] <= rl[d-1]; end
            assign rr[gb*257 +: 257] = rl[NRR];
        end
    end endgenerate
endmodule

module tb_xload_xpipe;
    localparam integer T = 2, N = `NCMD, EARLY = `EARLY, DM = `DMUT, A0 = 16, MAXB = 1200;
    function automatic [63:0] pk(input integer a0, a1, a2, a3, a4, a5, a6, a7);
        pk = {8'(a7), 8'(a6), 8'(a5), 8'(a4), 8'(a3), 8'(a2), 8'(a1), 8'(a0)};
    endfunction
    function automatic integer el(input [63:0] v, input integer b);
        reg [63:0] x; begin x = v >> (8 * b); el = x[7:0]; end
    endfunction
    // GEN2c NE lanes + die rq pads to the BUDGET vector (= tb_hgi_xload_banklat CFG 2; kit hgi_sm_xl2_ctlx_bl RD_LAT)
    localparam [63:0] NE_LQ = pk(2, 3, 8, 9, 10, 11, 16, 17),  NE_LR = pk(1, 3, 8, 9, 9, 11, 16, 17);
    localparam [63:0] NE_RT = pk(10, 13, 23, 25, 26, 29, 39, 41);
    localparam [63:0] BUD = pk(37, 39, 27, 29, 53, 55, 43, 45);
    function automatic [63:0] padq(input [63:0] lq, input [63:0] rt, input [63:0] bud);
        padq = 0;
        for (integer b = 0; b < 8; b = b + 1) padq = padq | (64'(el(lq, b) + el(bud, b) - el(rt, b)) << (8 * b));
    endfunction
    localparam [63:0] LQ = padq(NE_LQ, NE_RT, BUD), LR = NE_LR;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0; integer seed = 11, errors = 0, cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    // ---- F20 drive (the host ingress broadcast), one set per unit
    reg [1:0] cfg_v = 0, desc_v = 0, launch_v = 0; reg [11:0] cfg_addr = 0; reg [255:0] cfg_data = 0;
    reg [11:0] desc_base = 0; reg [12:0] desc_limit = 0; reg [15:0] desc_loops = 0;
    wire [8*17-1:0] rq_r, rq_d; wire [8*257-1:0] rr_r, rr_d;
    integer lf_r, lf_d;
    wire [1:0] cf, ft, ac;
    wire d_r, e_r, l_r, d_d, e_d, l_d; wire [6:0] a_r, g_r, a_d, g_d; wire [2047:0] x_r, x_d;
`define XP_PORTS(U, RQ, RR, D, E, L, A, G, X) \
        .clk(clk), .clk_cal(clk), .clk_qlo(clk), .clk_qhi(clk), .clk_bf({4{clk}}), .clk_bd(clk), .clk_eg(clk), \
        .rst_n(rst_n), .tgt(8'd100), .cfg_v(cfg_v[U]), .cfg_target(8'd100), .cfg_addr(cfg_addr), .cfg_data(cfg_data), \
        .desc_v(desc_v[U]), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v[U]), \
        .configured(cf[U]), .fault(ft[U]), .active(ac[U]), .x_done(D), .xw_en(E), .xw_last(L), .xw_addr(A), .xw_grp(G), \
        .xw_data(X), .rq(RQ), .rr(RR)
    ot_hgi_sm_xload_static_xql  #(.RD_LAT(BUD), .MUT(0), .NP(1), .T(T), .XQL_MUT(0)) u_ref (`XP_PORTS(0, rq_r, rr_r, d_r, e_r, l_r, a_r, g_r, x_r));
    ot_hgi_sm_xload_static_xqlp #(.RD_LAT(BUD), .MUT(DM), .NP(1), .T(T), .XQL_MUT(0)) u_dut (`XP_PORTS(1, rq_d, rr_d, d_d, e_d, l_d, a_d, g_d, x_d));
    tb_xp_vm #(.LQ(LQ), .LR(LR), .BK(7)) vm_r (.clk(clk), .rq(rq_r), .rr(rr_r), .lanefault(lf_r));
    tb_xp_vm #(.LQ(LQ), .LR(LR), .BK(7)) vm_d (.clk(clk), .rq(rq_d), .rr(rr_d), .lanefault(lf_d));
    // ---- beat capture (edge relative to the unit's launch edge)
    integer tl_r = 0, tl_d = 0, cur = 0, nd_r = 0, nd_d = 0;
    integer rb_n [0:N-1]; integer rb_t [0:N-1][0:MAXB-1]; reg [13:0] rb_ag [0:N-1][0:MAXB-1]; reg [2047:0] rb_x [0:N-1][0:MAXB-1];
    integer db_n = 0; integer db_t [0:N*MAXB-1]; reg [13:0] db_ag [0:N*MAXB-1]; reg [2047:0] db_x [0:N*MAXB-1];
    always @(posedge clk) if (rst_n) begin
        if (e_r) begin
            if (rb_n[cur] < MAXB) begin rb_t[cur][rb_n[cur]] = cyc - tl_r; rb_ag[cur][rb_n[cur]] = {a_r, g_r}; rb_x[cur][rb_n[cur]] = x_r; end
            rb_n[cur] = rb_n[cur] + 1;
        end
        if (e_d) begin
            if (db_n < N * MAXB) begin db_t[db_n] = cyc - tl_d; db_ag[db_n] = {a_d, g_d}; db_x[db_n] = x_d; end
            db_n = db_n + 1;
        end
        if (d_r) nd_r = nd_r + 1;
        if (d_d) nd_d = nd_d + 1;
    end
    // ---- commands
    reg [107:0] pl [0:N-1]; integer iss [0:N-1], at [0:N-1];
    function automatic integer nb_of(input integer p); nb_of = (p * 3152 + 2047) / 2048; endfunction
    function automatic integer iss_of(input [107:0] c);
        integer p, k, f, nb, la, pla, wb, gnb;
        begin
            k = c[60:40]; p = c[64:61]; f = c[100:99]; nb = nb_of(p);
            if (f == 0) iss_of = 8 * nb * ((k - 1) / 512 + 1);
            else begin
                la = (f == 2) ? 8 : 4; pla = p * la; wb = ((pla > 2 * nb) ? pla : 2 * nb) + 4;
                gnb = (f == 2) ? (k - 1) / 2048 + 1 : (k - 1) / 1024 + 1;
                iss_of = wb * gnb * 4;
            end
        end
    endfunction
    task automatic mk(input integer c, output [107:0] o);
        reg [20:0] n; reg [3:0] p; reg [39:0] base; reg [31:0] st; reg [6:0] xb; reg [1:0] fmt;
        integer pk_k [0:11]; integer pk_f [0:11];
        begin
            // production (P 1): DS SM x-loads -- dense FP8 / BF16, routed FP4, short indexer / compressor x, transitions
            pk_k[0] = 7168; pk_f[0] = 1; pk_k[1] = 7168; pk_f[1] = 1; pk_k[2] = 7168; pk_f[2] = 2; pk_k[3] = 2048; pk_f[3] = 2;
            pk_k[4] = 512;  pk_f[4] = 0; pk_k[5] = 1536; pk_f[5] = 1; pk_k[6] = 7168; pk_f[6] = 0; pk_k[7] = 1024; pk_f[7] = 1;
            pk_k[8] = 4096; pk_f[8] = 2; pk_k[9] = 512;  pk_f[9] = 1; pk_k[10] = 7168; pk_f[10] = 2; pk_k[11] = 2048; pk_f[11] = 0;
            xb = $unsigned($random(seed)) % 128; base = 8 * ($unsigned($random(seed)) % 20);
            if (c < 12) begin p = 1; n = pk_k[c]; fmt = pk_f[c]; st = 8 * ((n + 7) / 8); end
            else begin
                p = 1 + ($unsigned($random(seed)) % 8); fmt = $unsigned($random(seed)) % 3;
                n = (fmt == 0) ? 1 + ($unsigned($random(seed)) % 1500) : 32 * (1 + ($unsigned($random(seed)) % 90));
                st = 8 * (((n + 7) / 8) + ($unsigned($random(seed)) % 3));
            end
            o = {xb, fmt, 2'd1, st, p, n, base};
        end
    endtask
    task automatic cfgw(input integer u, input [11:0] a, input [255:0] d);
        begin
            @(negedge clk); cfg_v[u] = 1; cfg_addr = a; cfg_data = d; @(negedge clk); cfg_v[u] = 0; repeat (3) @(negedge clk);
        end
    endtask
    task automatic descw(input integer u, input integer lim);
        begin
            @(negedge clk); desc_v[u] = 1; desc_base = 0; desc_limit = 13'(lim); desc_loops = 1; @(negedge clk); desc_v[u] = 0;
            repeat (3) @(negedge clk);
        end
    endtask
    task automatic launch(input integer u, output integer tl);
        begin
            @(negedge clk); launch_v[u] = 1; @(posedge clk); tl = cyc; @(negedge clk); launch_v[u] = 0;
        end
    endtask
    integer c, t, d0, mism, tr, ser, ov, fst [0:N-1], lst [0:N-1];
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 11;
        $display("XPIPE SEED=%0d N=%0d EARLY=%0d DMUT=%0d RD_LAT=%h", seed, N, EARLY, DM, BUD);
        for (c = 0; c < N; c = c + 1) begin rb_n[c] = 0; mk(c, pl[c]); iss[c] = iss_of(pl[c]); end
        repeat (3) @(posedge clk); rst_n = 1; repeat (40) @(posedge clk);
        // ---- reference: one command at a time
        for (c = 0; c < N; c = c + 1) begin
            cur = c;
            cfgw(0, 12'h800, {116'd0, pl[c], 32'd0});
            descw(0, 1);
            d0 = nd_r; launch(0, tl_r);
            t = 0; while ((nd_r == d0 || ac[0]) && t < 200000) begin @(posedge clk); t = t + 1; end
            repeat (12) @(posedge clk);
            if (t >= 200000 || rb_n[c] == 0 || rb_n[c] > MAXB) begin $display("ERR ref load %0d did not finish / no beats (%0d)", c, rb_n[c]); errors = errors + 1; end
            fst[c] = rb_t[c][0]; lst[c] = rb_t[c][rb_n[c] - 1];
            $display("ref %0d {fmt %0d P %0d K %0d xb %0d}: ISS %0d beats %0d FIRST %0d LAST %0d", c, pl[c][100:99], pl[c][64:61],
                     pl[c][60:40], pl[c][107:101], iss[c], rb_n[c], fst[c], lst[c]);
        end
        // ---- the compiler law (pipelined slots)
        at[0] = A0; ser = 0; ov = 0;
        for (c = 0; c + 1 < N; c = c + 1) begin
            t = iss[c];
            if (lst[c] + 1 - fst[c+1] > t) t = lst[c] + 1 - fst[c+1];
            at[c+1] = at[c] + t - EARLY;
            if (lst[c] > t) ov = ov + 1;                // load c+1 fires while load c still emits
            ser = ser + lst[c] + 2;                     // cl2 serial: the next command after x_done
        end
        // ---- dut: one calendar, all commands
        for (c = 0; c < N; c = c + 1) cfgw(1, 12'h800 + 12'(c), {116'd0, pl[c], 32'(at[c])});
        descw(1, N);
        d0 = nd_d; launch(1, tl_d);
        t = 0; while ((nd_d - d0 < N || ac[1]) && t < 400000 && !ft[1]) begin @(posedge clk); t = t + 1; end
        repeat (40) @(posedge clk);
        // ---- compare: dut stream == concat over i of ref(i) shifted by at(i)
        mism = 0; tr = 0;
        for (c = 0; c < N; c = c + 1) for (integer b = 0; b < rb_n[c] && b < MAXB; b = b + 1) begin
            if (tr >= db_n) begin if (mism < 6) $display("ERR missing dut beat: load %0d beat %0d (exp edge %0d)", c, b, at[c] + rb_t[c][b]); mism = mism + 1; end
            else if (db_t[tr] != at[c] + rb_t[c][b] || db_ag[tr] !== rb_ag[c][b] || db_x[tr] !== rb_x[c][b]) begin
                if (mism < 6) $display("ERR load %0d beat %0d: dut edge %0d ag %h vs exp edge %0d ag %h data %s", c, b, db_t[tr], db_ag[tr],
                                       at[c] + rb_t[c][b], rb_ag[c][b], (db_x[tr] === rb_x[c][b]) ? "eq" : "DIFF");
                mism = mism + 1;
            end
            tr = tr + 1;
        end
        if (db_n != tr) begin $display("ERR dut beats %0d, expected %0d", db_n, tr); errors = errors + 1; end
        $display("XPIPE dut span %0d edges (last slot %0d) for %0d loads (cl2 serial slots would span %0d); %0d of %0d slots overlap the previous load's emission; beats %0d / %0d, mismatches %0d; x_done ref %0d dut %0d; fault ref %b dut %b; lanefault %0d/%0d",
                 t, at[N-1], N, ser, ov, N - 1, db_n, tr, mism, nd_r, nd_d - d0, ft[0], ft[1], lf_r, lf_d);
        if (mism || nd_d - d0 != N || nd_r != N || |ft || lf_r || lf_d || ov == 0) errors = errors + 1;
        if (errors == 0) $display("XLOAD_XPIPE PASS N=%0d", N); else $display("XLOAD_XPIPE FAIL EARLY=%0d DMUT=%0d errors=%0d", EARLY, DM, errors);
        $finish;
    end
endmodule
