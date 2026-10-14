`timescale 1ns/1ps
// Leaf miter of ot_qfd_vm_xtree.sv (claude/qwen-tp8-vm-rtl, 2026-10-13) against the FLAT reference:
//   xline   32 x ot_qfd_vm_xline_t  vs the parent's line / x_q expressions (ot_qfd_sp_vector_memory_bv g_ent / x_q,
//           copied verbatim, 32-b elements): DUT q == flat x_q delayed by exactly ONE engine edge.
//   xqface  XQR x ot_qfd_vm_xrelay_t + ot_qfd_vm_xqface_t == its input delayed XQR + 1 engine edges.
//   fan     me tree: K free-running stages fed me (K + 1) edges early == me one edge early at the leaf;
//           control tree: K engine-enabled stages fed a word tapped K engine edges early == the word on its edge.
// Stimulus xorshift64 ($urandom(seed) re-seeds per call under Verilator).  A run with too little coverage FAILS.
// XMUT: 1 / 2 / 3 = xline MUT on plane 3; 4 = face free-runs; 5 = me-tree stage transparent; 6 = control-tree stage
// transparent; 7 = one x_q relay free-runs.  All must FAIL.
module tb_qfd_vm_xtree #(
    parameter integer NRB = 16,
    parameter integer SMIN = 5,
    parameter integer SMAX = 8,
    parameter integer BMAX = 8,
    parameter integer ND = 14,
    parameter [ND*8-1:0] DSET = {8'd96, 8'd64, 8'd48, 8'd32, 8'd24, 8'd16, 8'd12, 8'd8, 8'd6, 8'd4, 8'd3, 8'd2, 8'd1, 8'd0},
    parameter integer K = 3,
    parameter integer XQR = 2,
    parameter integer MEREG = 1,
    parameter integer CYCLES = 4000,
    parameter integer SEED = 1,
    parameter integer XMUT = 0
);
    localparam integer BEAT = (NRB - 1) * 16;
    localparam integer NX = 1 << SMAX;
    localparam integer LB = $clog2(BMAX) + 1;
    localparam integer CW = 1 + ND + LB + 4 + 1 + 4;
    localparam integer QE = K + 2;                     // reference control queue depth (entries 0 .. QE-1)
    reg clk = 1'b0;
    always #1 clk = ~clk;
    reg [63:0] xs = 64'h9E3779B97F4A7C15 ^ {32'd0, SEED[31:0]} ^ 64'h1;
    function automatic [31:0] rnd(input integer dummy);
        begin xs = xs ^ (xs << 13); xs = xs ^ (xs >> 7); xs = xs ^ (xs << 17); rnd = xs[47:16]; end
    endfunction
    // ---- me: mh[0] is the tree input (K + 1 edges early), mh[K] = me_e, mh[K+1] = me ----
    reg [K+1:0] mh = 0;
    wire me_t = mh[0], me_e_ref = mh[K], me = mh[K+1];
    // ---- stimulus (changes every clock; only engine edges are sampled) ----
    reg [BEAT*32-1:0] bvs;
    reg               s6_bv, co_v;
    reg [ND-1:0]      s6_d;
    reg [LB-1:0]      s6_j;
    reg [3:0]         s6_sp, co_sp;
    integer i, di, t;
    reg [31:0] r;
    always @(posedge clk) begin
        mh <= {mh[K:0], (rnd(0) % 4) != 0};
        for (i = 0; i < BEAT; i = i + 1) bvs[i*32 +: 32] <= rnd(0);
        r = rnd(0);
        s6_bv <= r[0];
        s6_d <= (r[3:1] == 3'd0) ? r[4 +: ND] & r[18 +: ND] : (r[3:1] == 3'd1) ? {ND{1'b0}} : ({{(ND-1){1'b0}}, 1'b1} << (r[8:4] % ND));
        s6_j <= r[20 +: 5] % (BMAX + 2);
        r = rnd(0);
        s6_sp <= (r[3:0] == 4'd0) ? r[7:4] : SMIN + (r[11:8] % (SMAX - SMIN + 1));
        co_v <= (r[13:12] == 2'd0);
        co_sp <= (r[17:14] == 4'd0) ? r[21:18] : SMIN + (r[25:22] % (SMAX - SMIN + 1));
    end
    // ---- FLAT reference: line / x_q, verbatim from the parent (me_x -> me) ----
    reg [NX*32-1:0] line, x_q, xq_d1;
    genvar c, dd, pl, pb;
    generate for (c = 0; c < NX; c = c + 1) begin : g_ent
        wire [ND-1:0] hit;
        wire [ND*32-1:0] src;
        for (dd = 0; dd < ND; dd = dd + 1) begin : g_d
            localparam integer DV = DSET[dd*8 +: 8];
            localparam integer JJ = (c * DV) / BEAT;
            localparam integer MM = (c * DV) % BEAT;
            if (JJ < BMAX) begin : g_ok
                assign hit[dd] = s6_d[dd] && (s6_j == JJ);
                assign src[dd*32 +: 32] = bvs[MM*32 +: 32];
            end else begin : g_no
                assign hit[dd] = 1'b0;
                assign src[dd*32 +: 32] = 32'd0;
            end
        end
        reg [31:0] pick;
        integer kk;
        always @(*) begin
            pick = 32'd0;
            for (kk = 0; kk < ND; kk = kk + 1) if (hit[kk]) pick = src[kk*32 +: 32];
        end
        always @(posedge clk) if (me && s6_bv && (|hit) && c < (1 << s6_sp)) line[c*32 +: 32] <= pick;
    end endgenerate
    integer xi;
    always @(posedge clk) if (co_v) begin
        for (xi = 0; xi < NX; xi = xi + 1) if (me) x_q[xi*32 +: 32] <= line[(xi & ((1 << co_sp) - 1))*32 +: 32];
    end
    always @(posedge clk) if (me) xq_d1 <= x_q;
    // ---- me tree (chain of K free-running stages; node K-1 output = me_e) ----
    wire [K:0] mt;
    assign mt[0] = me_t;
    generate for (c = 0; c < K; c = c + 1) begin : g_mt
        ot_qfd_vm_fan_t #(.W(1), .EN(0), .MUT((XMUT == 5 && c == K - 1) ? 1 : 0)) u_f (.clk(clk), .me_e(1'b0),
            .d(mt[c]), .q(mt[c+1]));
    end endgenerate
    wire me_e = mt[K];
    // ---- control tree: reference engine-enabled queue, tapped K entries early, K engine-enabled stages ----
    wire [CW-1:0] cw_in = {s6_bv, s6_d, s6_j, s6_sp, co_v, co_sp};
    reg  [QE*CW-1:0] cq;
    always @(posedge clk) if (me) cq <= {cq[(QE-1)*CW-1:0], cw_in};
    wire [(K+1)*CW-1:0] ct;
    assign ct[0 +: CW] = cq[0 +: CW];                  // entry 0: K engine edges before entry K
    generate for (c = 0; c < K; c = c + 1) begin : g_ct
        ot_qfd_vm_fan_t #(.W(CW), .EN(1), .MEREG(MEREG), .MUT((XMUT == 6 && c == 0) ? 1 : 0)) u_f (.clk(clk),
            .me_e((MEREG != 0) ? me_e : me), .d(ct[c*CW +: CW]), .q(ct[(c+1)*CW +: CW]));
    end endgenerate
    wire [CW-1:0] ct_o = ct[K*CW +: CW];
    wire [CW-1:0] ct_ref = cq[K*CW +: CW];
    // ---- DUT: 32 line planes ----
    wire [NX*32-1:0] dq;
    generate for (pl = 0; pl < 32; pl = pl + 1) begin : g_p
        wire [BEAT-1:0] pd;
        wire [NX-1:0]   pq;
        for (pb = 0; pb < BEAT; pb = pb + 1) begin : g_i
            assign pd[pb] = bvs[pb*32 + pl];
        end
        ot_qfd_vm_xline_t #(.NRB(NRB), .SMIN(SMIN), .SMAX(SMAX), .BMAX(BMAX), .ND(ND), .DSET(DSET), .MEREG(MEREG),
            .MUT((pl == 3 && XMUT >= 1 && XMUT <= 3) ? XMUT : 0)) u_l (.clk(clk), .me_e((MEREG != 0) ? me_e : me),
            .d(pd), .c_v(s6_bv), .c_d(s6_d), .c_j(s6_j), .c_sp(s6_sp), .o_v(co_v), .o_sp(co_sp), .q(pq));
        for (pb = 0; pb < NX; pb = pb + 1) begin : g_o
            assign dq[pb*32 + pl] = pq[pb];
        end
    end endgenerate
    // ---- DUT: x_q relays + face, on the reference x_q (so a line fault does not hide a face fault) ----
    localparam integer FW = (NX*32 >= 1024) ? 1024 : NX*32;
    wire [(XQR+1)*FW-1:0] xr;
    assign xr[0 +: FW] = x_q[0 +: FW];
    generate for (c = 0; c < XQR; c = c + 1) begin : g_xr
        ot_qfd_vm_xrelay_t #(.W(FW), .MEREG(MEREG), .MUT((XMUT == 7 && c == 0) ? 1 : 0)) u_r (.clk(clk),
            .me_e((MEREG != 0) ? me_e : me), .d(xr[c*FW +: FW]), .q(xr[(c+1)*FW +: FW]));
    end endgenerate
    wire [FW-1:0] fq;
    ot_qfd_vm_xqface_t #(.W(FW), .MEREG(MEREG), .MUT((XMUT == 4) ? 1 : 0)) u_face (.clk(clk),
        .me_e((MEREG != 0) ? me_e : me), .d(xr[XQR*FW +: FW]), .q(fq));
    reg [(XQR+1)*FW-1:0] fr;                           // reference: XQR + 1 engine-edge delays
    always @(posedge clk) if (me) fr <= {fr[XQR*FW-1 + ((XQR == 0) ? FW : 0) : 0], x_q[0 +: FW]} ;
    wire [FW-1:0] f_ref = fr[XQR*FW +: FW];
    // ---- checks + coverage ----
    integer n_chk = 0, n_stall = 0, n_upd = 0, n_now = 0, n_ctchg = 0, n_fchg = 0, bad = 0, first = -1;
    integer n_d [0:ND-1];
    integer n_j [0:BMAX-1];
    integer n_ws [0:15];
    integer n_rs [0:15];
    reg [NX*32-1:0] xq_prev;
    reg [FW-1:0]    f_prev;
    reg [CW-1:0]    ct_prev;
    initial begin
        for (i = 0; i < ND; i = i + 1) n_d[i] = 0;
        for (i = 0; i < BMAX; i = i + 1) n_j[i] = 0;
        for (i = 0; i < 16; i = i + 1) begin n_ws[i] = 0; n_rs[i] = 0; end
        line = 0; x_q = 0; xq_d1 = 0; cq = 0; fr = 0;
    end
    integer cyc = 0;
    localparam integer WARM = 4 * (K + XQR + 6);
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc > WARM) begin
            n_chk = n_chk + 1;
            if (!me) n_stall = n_stall + 1;
            if (dq !== xq_d1 || me_e !== me_e_ref || ct_o !== ct_ref || fq !== f_ref) begin
                bad = bad + 1;
                if (first < 0) begin
                    first = cyc;
                    $display("MISMATCH cyc=%0d xline=%0d me_e=%0d ctl=%0d face=%0d", cyc, dq !== xq_d1, me_e !== me_e_ref,
                             ct_o !== ct_ref, fq !== f_ref);
                end
            end
            if (me) begin
                xq_prev <= x_q; f_prev <= f_ref; ct_prev <= ct_ref;
                if (x_q !== xq_prev) n_upd = n_upd + 1;
                if (f_ref !== f_prev) n_fchg = n_fchg + 1;
                if (ct_ref !== ct_prev) n_ctchg = n_ctchg + 1;
                if (s6_bv) begin
                    for (di = 0; di < ND; di = di + 1) if (s6_d == ({{(ND-1){1'b0}}, 1'b1} << di) && s6_j < BMAX) n_d[di] = n_d[di] + 1;
                    if (|s6_d && s6_j < BMAX) n_j[s6_j] = n_j[s6_j] + 1;
                    if (|s6_d) n_ws[s6_sp] = n_ws[s6_sp] + 1;
                    if (|s6_d && s6_sp < SMAX) n_now = n_now + 1;
                end
                if (co_v) n_rs[co_sp] = n_rs[co_sp] + 1;
            end
        end
        if (cyc == CYCLES) begin : fin
            integer lo_d, lo_j, lo_ws, lo_rs;
            lo_d = 1 << 30; lo_j = 1 << 30; lo_ws = 1 << 30; lo_rs = 1 << 30;
            for (i = 0; i < ND; i = i + 1) if (n_d[i] < lo_d) lo_d = n_d[i];
            for (i = 0; i < BMAX; i = i + 1) if (n_j[i] < lo_j) lo_j = n_j[i];
            for (i = SMIN; i <= SMAX; i = i + 1) begin
                if (n_ws[i] < lo_ws) lo_ws = n_ws[i];
                if (n_rs[i] < lo_rs) lo_rs = n_rs[i];
            end
            if (bad != 0)
                $display("FAIL qfd_vm_xtree first=%0d bad=%0d of %0d XMUT=%0d", first, bad, n_chk, XMUT);
            else if (n_chk < CYCLES / 2 || n_stall < CYCLES / 8 || n_upd < CYCLES / 16 || n_now < CYCLES / 16 || lo_d < 8 ||
                     lo_j < 8 || lo_ws < 8 || lo_rs < 8 || n_ctchg < CYCLES / 4 || n_fchg < 64 || n_fchg * 4 < n_upd)
                $display("FAIL qfd_vm_xtree VACUOUS checks=%0d stalls=%0d xq_updates=%0d bounded_writes=%0d min_d=%0d min_j=%0d min_wsp=%0d min_rsp=%0d ctl_changes=%0d face_changes=%0d",
                         n_chk, n_stall, n_upd, n_now, lo_d, lo_j, lo_ws, lo_rs, n_ctchg, n_fchg);
            else
                $display("PASS qfd_vm_xtree NRB=%0d SMAX=%0d K=%0d XQR=%0d MEREG=%0d checks=%0d stalls=%0d xq_updates=%0d bounded_writes=%0d min_d=%0d min_j=%0d min_wsp=%0d min_rsp=%0d ctl_changes=%0d face_changes=%0d",
                         NRB, SMAX, K, XQR, MEREG, n_chk, n_stall, n_upd, n_now, lo_d, lo_j, lo_ws, lo_rs, n_ctchg, n_fchg);
            $finish;
        end
    end
endmodule
