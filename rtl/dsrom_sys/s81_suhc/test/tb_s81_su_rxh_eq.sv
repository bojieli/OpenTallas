`timescale 1ns/1ps
// tb_s81_su_rxh_eq (S-ELEM-C 2026-10-15): the hardened RX cluster ot_s81_su_rxh (v2: control + 16 RA front/back lane
// leaves + 4 QR leaves + RB/RW leaf) against the flat tile ot_s81_su_rxt (the production reference of the same units),
// both at S_RD 5 / QW 2, on one random job stream of every RX kind (RA 8, RB 9, QR 10, RW 11): parameter rows several a
// cycle on any slot, RA / RB operand rows behind them in the same cycle (not RW / QR: the flat tile reads the RW
// configuration / QR tables registered BEFORE that cycle, a flat-tile hazard the calendar never schedules; the
// cluster's stage B reads the fresh rows), RB / QR pairs, RW ids + score rows, idle gaps, special
// operands (zeros, subnormals, infinities, NaN).  Every result row (address, mask, data; both write slots) must match
// in order; sticky faults must match.  The per-kind first-result latency difference is printed (the cluster's added
// fixed stages).  XMUT (cluster only): 1 RA returns sp, 2 RB drops the bias, 3 QR inverse rotation, 4 RW skips the
// route scale, 5 RA front leaf without the max(x, 0) clamp,
// 6 control leaf QR row-index stuck at 0 -> the run must FAIL (negative controls).
module tb_s81_su_rxh_eq;
    parameter integer NJOB = 48, SEED = 1, XMUT = 0;
    localparam [3:0] K_RA = 8, K_RB = 9, K_QR = 10, K_RW = 11;
    reg clk = 0, rst = 0;
    always #5 clk = ~clk;
    reg         st; reg [3:0] kind; reg [7:0] jid; reg [4:0] dv; reg [2559:0] dd;
    wire        fv, fv2, ffu, ffo, cv, cv2, cfu, cfo;
    wire [13:0] fa, fa2, ca, ca2; wire [15:0] fm, cm; wire [511:0] fd, fd2, cd, cd2;
    ot_s81_su_rxt #(.S_RD(5), .LM(5), .LA(4), .QW(2)) u_flat (.clk(clk), .rst_in(rst), .dn_st_i(st), .dn_kind_i(kind),
        .dn_jid_i(jid), .dn_v_i(dv), .dn_d_i(dd), .o_v(fv), .o_a(fa), .o_m(fm), .o_d(fd), .o_v2(fv2), .o_a2(fa2), .o_d2(fd2),
        .o_fu(ffu), .o_fo(ffo), .o_alive(), .o_den(), .o_rdy(), .o_rjid());
    ot_s81_su_rxh #(.S_RD(5), .LM(5), .LA(4), .XMUT(XMUT >= 5 ? 0 : XMUT)) u_clu (.clk(clk), .rst_in(rst), .dn_st_i(st), .dn_kind_i(kind),
        .dn_jid_i(jid), .dn_v_i(dv), .dn_d_i(dd), .o_v(cv), .o_a(ca), .o_m(cm), .o_d(cd), .o_v2(cv2), .o_a2(ca2), .o_d2(cd2),
        .o_fu(cfu), .o_fo(cfo), .o_alive(), .o_den(), .o_rdy(), .o_rjid());

    // XMUT 5 (RA FRONT leaf negative control, injected here so the leaf source stays the gated one): lane 3's front leaf
    // loses its max(x, 0) clamp (its NaN guard forced true: negative x pass through to sp = x + l)
    generate if (XMUT == 5) begin : g_m5
        initial force u_clu.g_ra[3].u_f.x_nan = 1'b1;
    end endgenerate
    // XMUT 6 (control leaf negative control): the QR coefficient row-index copies stuck at row 0
    generate if (XMUT == 6) begin : g_m6
        initial force u_clu.u_c.cj = 16'd0;
    end endgenerate
    // ---------------------------------------------------------------- result queues
    reg [541:0] qf [0:65535]; reg [541:0] qc [0:65535];
    reg [525:0] qf2 [0:65535]; reg [525:0] qc2 [0:65535];
    integer nf = 0, nc = 0, nf2 = 0, nc2 = 0, cyc = 0;
    integer job_start = 0, ff_first = -1, cf_first = -1;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (fv)  begin qf[nf] = {1'b1, fa, fm, fd}; nf = nf + 1; if (ff_first < 0) ff_first = cyc; end
        if (cv)  begin qc[nc] = {1'b1, ca, cm, cd}; nc = nc + 1; if (cf_first < 0) cf_first = cyc; end
        if (fv2) begin qf2[nf2] = {1'b0, fa2, fd2}; nf2 = nf2 + 1; end
        if (cv2) begin qc2[nc2] = {1'b0, ca2, cd2}; nc2 = nc2 + 1; end
    end

    // ---------------------------------------------------------------- operands
    reg [31:0] seed;
    function automatic [31:0] rng();                       // xorshift32 (portable across simulators)
        reg [31:0] x;
        begin x = seed; x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5); seed = x; rng = x; end
    endfunction
    function automatic [31:0] rnd_f(input integer lo, input integer hi);
        reg [31:0] r; integer e;
        begin
            r = rng();
            e = lo + (rng() % (hi - lo + 1));
            rnd_f = {r[31], e[7:0], r[22:0]};
        end
    endfunction
    function automatic [31:0] special(input [31:0] x);
        reg [7:0] p;
        begin
            p = rng();
            case (p)
                8'd1: special = 32'h00000000; 8'd2: special = 32'h80000000; 8'd3: special = {x[31], 8'd0, x[22:0]};
                8'd4: special = {x[31], 8'hFF, 23'd0}; 8'd5: special = 32'h7FC00001; 8'd6: special = {x[31], 8'd1, x[22:0]};
                default: special = x;
            endcase
        end
    endfunction
    function automatic [511:0] rrow(input integer lo, input integer hi);
        integer l; reg [511:0] r;
        begin for (l = 0; l < 16; l = l + 1) r[32 * l +: 32] = special(rnd_f(lo, hi)); rrow = r; end
    endfunction

    // ---------------------------------------------------------------- the job stream
    reg [511:0] rows [0:255];                 // the job's rows in order: parameters then operands
    integer nrows, np, k, i, n, s, pairsz, gap, kd [0:3];
    integer lat_f [0:15], lat_c [0:15], seen [0:15];
    task automatic idle(input integer c); integer t; begin
        for (t = 0; t < c; t = t + 1) begin @(negedge clk); st = 0; dv = 0; dd = 0; end
    end endtask
    task automatic run_job(input [3:0] kk);
        integer cnt, ns, kx, off, j, r, slot, per, p0, nop, q;
        reg [511:0] d0, ids;
        begin
            np = (kk == K_QR) ? 5 : 1;
            d0 = rrow(100, 140); d0[13:0] = 14'd512 + (rng() % 4096);
            nrows = 0;
            case (kk)
                K_RA: begin cnt = 1 + (rng() % 12); nop = cnt; end
                K_RB: begin cnt = 1 + (rng() % 10); nop = 2 * cnt; end
                K_QR: begin cnt = 1 + (rng() % 4); nop = 4 * cnt; end
                default: begin ns = 1 + (rng() % 6); nop = ns + 1; end
            endcase
            if (kk == K_RW) begin
                kx = 1 + (rng() % 8); off = rng() % (17 - kx);
                d0[64 +: 16] = nop; d0[96 +: 32] = rnd_f(120, 130); d0[96 + 31] = 1'b0; d0[128 +: 4] = off; d0[160 +: 4] = kx;
                ids = 512'd0;
                // ascending distinct ids inside the score rows
                for (j = 0; j < kx; j = j + 1) ids[32 * j +: 9] = ((16 * ns - kx) * (j + 1) / (kx + 1)) + j;
            end
            rows[nrows] = d0; nrows = nrows + 1;
            if (kk == K_QR) for (j = 0; j < 4; j = j + 1) begin
                rows[nrows] = rrow(110, 126); nrows = nrows + 1;     // cos / sin tables: |c|, |s| < 1
            end
            for (j = 0; j < nop; j = j + 1) begin
                if (kk == K_RW && j == 0) rows[nrows] = ids;
                else if (kk == K_RW) begin rows[nrows] = rrow(115, 130); for (r = 0; r < 16; r = r + 1) rows[nrows][32 * r + 31] = 1'b0; end
                else if (kk == K_RA) rows[nrows] = rrow(110, 134);
                else rows[nrows] = rrow(100, 140);
                nrows = nrows + 1;
            end
            // announce
            @(negedge clk); st = 1; kind = kk; jid = jid + 1; dv = 0; dd = 0;
            if (rng() % 2) idle(1 + (rng() % 3));
            // rows: parameters several a cycle; operands behind them (pairs for RB / QR; one a cycle otherwise)
            r = 0;
            while (r < nrows) begin
                @(negedge clk); st = 0; dv = 0; dd = 0; slot = 0;
                if (r < np) begin
                    per = 1 + (rng() % 5);
                    while (r < np && per > 0 && slot < 5) begin dv[slot] = 1; dd[512 * slot +: 512] = rows[r]; r = r + 1; slot = slot + 1; per = per - 1; end
                end
                if (r >= np && slot < 5 && (slot == 0 || ((kk == K_RA || kk == K_RB) && (rng() % 2)))) begin
                    pairsz = (kk == K_RB || kk == K_QR) ? 2 : 1;
                    if (slot + pairsz <= 5 && r + pairsz <= nrows) begin
                        for (j = 0; j < pairsz; j = j + 1) begin dv[slot] = 1; dd[512 * slot +: 512] = rows[r]; r = r + 1; slot = slot + 1; end
                    end
                end
                if (rng() % 4 == 0) idle(1);
            end
            @(negedge clk); st = 0; dv = 0; dd = 0;
            idle(260);
        end
    endtask

    integer e, errors = 0, jn;
    reg [3:0] kk;
    initial begin
        seed = SEED * 32'h9E3779B1 + 1; if ($value$plusargs("SEED=%d", seed)) $display("RXH_EQ seed %0d", seed); st = 0; kind = 0; jid = 0; dv = 0; dd = 0;
        for (i = 0; i < 16; i = i + 1) begin lat_f[i] = -1; lat_c[i] = -1; seen[i] = 0; end
        repeat (5) @(negedge clk); rst = 1; repeat (5) @(negedge clk);
        for (jn = 0; jn < NJOB; jn = jn + 1) begin
            kk = K_RA + (jn % 4);
            if (jn >= 8) kk = K_RA + (rng() % 4);
            ff_first = -1; cf_first = -1; job_start = cyc;
            run_job(kk);
            if (ff_first >= 0 && cf_first >= 0) begin
                if (lat_f[kk] < 0) begin lat_f[kk] = ff_first - job_start; lat_c[kk] = cf_first - job_start; end
                else if (cf_first - ff_first != lat_c[kk] - lat_f[kk]) begin
                    $display("RXH_EQ latency difference not constant kind %0d: %0d vs %0d", kk, cf_first - ff_first, lat_c[kk] - lat_f[kk]);
                    errors = errors + 1;
                end
            end
            seen[kk] = seen[kk] + 1;
        end
        idle(50);
        if (nf != nc || nf2 != nc2) begin $display("RXH_EQ row counts flat %0d/%0d cluster %0d/%0d", nf, nf2, nc, nc2); errors = errors + 1; end
        for (e = 0; e < nf && e < nc; e = e + 1)
            if (qf[e] !== qc[e]) begin
                if (errors < 12) $display("RXH_EQ row %0d differs: a %0d/%0d m %h/%h d0 %h/%h", e, qf[e][540:527], qc[e][540:527],
                                           qf[e][526:511], qc[e][526:511], qf[e][31:0], qc[e][31:0]);
                errors = errors + 1;
            end
        for (e = 0; e < nf2 && e < nc2; e = e + 1)
            if (qf2[e][524:0] !== qc2[e][524:0]) begin
                if (errors < 12) $display("RXH_EQ row2 %0d differs", e);
                errors = errors + 1;
            end
        if (ffu !== cfu || ffo !== cfo) begin $display("RXH_EQ faults flat fu %b fo %b cluster fu %b fo %b", ffu, ffo, cfu, cfo); errors = errors + 1; end
        for (i = 8; i < 12; i = i + 1)
            $display("RXH_EQ kind %0d jobs %0d first-result latency flat %0d cluster %0d (+%0d)", i, seen[i], lat_f[i], lat_c[i], lat_c[i] - lat_f[i]);
        $display("RXH_EQ rows %0d + %0d (slot 2) faults fu %b fo %b errors %0d XMUT %0d", nf, nf2, ffu, ffo, errors, XMUT);
        if (errors == 0 && nf > 0) $display("RXH_EQ PASS"); else $display("RXH_EQ FAIL");
        $finish;
    end
endmodule
