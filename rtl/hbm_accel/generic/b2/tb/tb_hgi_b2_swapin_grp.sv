`timescale 1ns/1ps
`default_nettype none
// tb_hgi_b2_swapin_grp ([mtp-rtl] 2026-10-13): the native B2 MTP swap-IN group (ot_hgi_b2_swap_disp + relays + stations +
// four REAL ot_hgi_dma_front B2 1 / QID q) against an INDEPENDENT oracle of the NATIVE slot image
// (tools/hgi_b2/mtp_swap.py NATIVE LAYOUT, 2026-10-13: cluster q moves ITS quarter of h, logical rows 80q .. 80q + 79, where the B2
// allocator holds it, to stack q's slot rows q + 4j; the STRIPE4 footprint with rows permuted by owner).
//   HBM = the LOGICAL native image only: h row 80q + j on stack q at stack-local COLB + slot x CSTR + 64 q + 256 j; PRE on stack
//   0 at COLB + slot x CSTR + 81920 (every other byte a hash of its address).
//   Stimulus = the four linear own-stack h LOAD records as ONE group (cluster q: 80 rows x 64 words, HBM base (q << 35) |
//   COLB + slot x CSTR + 64 q, row stride 256 B -> the cluster's VM allocation, compact LOCAL or MIRROR), then PRE.
//   Expected VM = each cluster's initial slice with its quarter of h (rows 80q + j) at its descriptor (cluster 0: + PRE); the WHOLE slice
//   is compared (a stray write fails).
//   Cluster models: svc READ per stack (request lane, NL data lanes, credit LD a lane, HOPS wire stages each way, first
//   beat of a request RLAT edges after it; as tb_hgi_dma_front at full rate); VM wide WRITE NB lanes, done 2 edges later.
//   PASS = every slice exact, no fault, fence_quiet / done never before the last VM sector landed, and dispatch -> done
//   <= LIMIT in every run.  PRICE ROW (results/rtl/tput_map_1011/mtp_verify/record.json native_b2_swap_in): 336 cycles
//   = the simulator's S2 price of the swapin body (335.9: DMA.LOAD h 81,920 B + DMA.LOAD PRE 32 B + END; DMA.LOAD =
//   HBM first access 104 + bytes / bw, issue interval 4), the swap-in term of the 63,800 MTP.VERIFY price (5 columns x
//   (swapin 335.9 + embed 326.0 + L0 body 11,861.9 + swapout 241.0)); LIMIT = 1.10 x = 369.
//   MUT (S): 1 clusters 1 / 2 swapped, 2 cluster 2's destination base + 256, 3 the join ignores the outstanding count,
//   4 SERIALIZED group (exact, but must fail the throughput check).
module tb_hgi_b2_swapin_grp;
    parameter integer MUT = 0;
    parameter integer DHOPS = 10;
    parameter integer HOPS = 3;
    parameter integer RLAT = 40;
    parameter integer LD = 16;
    parameter integer SEED = 1;
    parameter integer LIMIT = 369;       // 1.10 x 335.9 (the swap-in price row)
    localparam integer NB = 8, NL = 8, SBIT = 35;
    localparam longint COLB = 64'h510000000, CSTR = 64'd131072;
    localparam integer VMW = 98304;
    reg clk = 0; always #1 clk = ~clk; reg rst_n = 0;
    reg g_v = 0, g_last = 0; reg [1:0] g_q = 0; reg [226:0] g_mv = 0;
    wire g_rdy, fence_quiet, done, fault; wire [3:0] e_acc;
    wire [4*51-1:0] dq; reg [3:0] dq_rdy = 0; reg [4*NL*270-1:0] dd_m = 0; wire [4*NL*270-1:0] dd; wire [4*NL-1:0] dd_cr;
    wire [4*NB*280-1:0] wl; reg [4*NB-1:0] wl_d1 = 0, wl_done = 0;
    ot_hgi_b2_swapin_grp #(.DHOPS(DHOPS), .NL(NL), .NB(NB), .LD(LD), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .g_v(g_v), .g_rdy(g_rdy),
        .g_last(g_last), .g_q(g_q), .g_mv(g_mv), .fence_quiet(fence_quiet), .done(done), .fault(fault), .e_acc(e_acc),
        .dq(dq), .dq_rdy(dq_rdy), .dd(dd), .dd_cr(dd_cr), .wl(wl), .wl_done(wl_done));
    longint cyc = 0; integer errors = 0;
    // ---------------------------------------------------------------- HBM (the legacy image) and the svc READ models
    reg [31:0] hw [longint];
    function automatic [31:0] hword(input longint a);        // a = byte address / 4
        longint x;
        begin
            if (hw.exists(a)) hword = hw[a];
            else begin x = a ^ (a >> 31); x = x * 64'h9E3779B97F4A7C15; x = x ^ (x >> 29); hword = 32'(x >> 16); end
        end
    endfunction
    integer rq_n [0:3], rq_h [0:3], nxt [0:3]; reg [49:0] rq [0:3][0:63]; longint rq_t [0:3][0:63];
    integer cr [0:4*NL-1]; reg [269:0] lb [0:4*NL-1][0:1023]; integer lh [0:4*NL-1], lt [0:4*NL-1];
    reg [4*NL*270-1:0] dpipe [0:7]; reg [4*NL-1:0] cpipe [0:7]; wire [4*NL-1:0] cr_in;
    always @(posedge clk) begin dpipe[0] <= dd_m; cpipe[0] <= dd_cr; for (integer k = 1; k < 8; k++) begin dpipe[k] <= dpipe[k-1]; cpipe[k] <= cpipe[k-1]; end end
    assign dd = (HOPS == 0) ? dd_m : dpipe[HOPS-1];
    assign cr_in = (HOPS == 0) ? dd_cr : cpipe[HOPS-1];
    initial begin
        for (integer i = 0; i < 4*NL; i++) begin cr[i] = LD; lh[i] = 0; lt[i] = 0; end
        for (integer s = 0; s < 4; s++) begin rq_n[s] = 0; rq_h[s] = 0; nxt[s] = 0; end
    end
    longint nreq = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (rst_n) begin
            dd_m <= '0;
            for (integer s = 0; s < 4; s++) begin
                dq_rdy[s] <= 1'b1;
                if (dq[s*51 + 50] && dq_rdy[s]) begin
                    rq[s][(rq_h[s] + rq_n[s]) % 64] = dq[s*51 +: 50]; rq_t[s][(rq_h[s] + rq_n[s]) % 64] = cyc + RLAT; rq_n[s] = rq_n[s] + 1; nreq = nreq + 1;
                    if (((dq[s*51 +: 37] >> SBIT) & 3) != s) begin $display("TB FAIL: stack %0d request lane got address %h", s, dq[s*51 +: 37]); errors++; end
                end
                for (integer k = 0; k < NL && rq_n[s] > 0 && rq_t[s][rq_h[s] % 64] <= cyc && lt[s*NL + (nxt[s] % NL)] - lh[s*NL + (nxt[s] % NL)] < 512; k++) begin : sch
                    reg [49:0] r; reg [255:0] sd; longint a; integer l;
                    r = rq[s][rq_h[s] % 64];
                    a = longint'(r[36:0]) + 32 * nxt[s];
                    for (integer w = 0; w < 8; w++) sd[32*w +: 32] = hword(a / 4 + w);
                    l = s * NL + (nxt[s] % NL);
                    lb[l][lt[l] % 1024] = {1'b1, 1'b0, r[49:46], 8'(nxt[s]), sd}; lt[l] = lt[l] + 1;
                    nxt[s] = nxt[s] + 1;
                    if (nxt[s] == int'(r[45:37])) begin nxt[s] = 0; rq_h[s] = rq_h[s] + 1; rq_n[s] = rq_n[s] - 1; end
                end
            end
            for (integer i = 0; i < 4*NL; i++) begin
                if (cr_in[i]) cr[i] = cr[i] + 1;
                if (lt[i] > lh[i] && cr[i] > 0) begin dd_m[i*270 +: 270] <= lb[i][lh[i] % 1024]; lh[i] = lh[i] + 1; cr[i] = cr[i] - 1; end
            end
        end
    end
    // ---------------------------------------------------------------- VM wide WRITE models (one a cluster)
    reg [31:0] vm [0:3][0:VMW-1]; reg [31:0] ev [0:3][0:VMW-1];
    longint nland = 0, t_lastl = 0;
    always @(posedge clk) begin
        wl_d1 <= '0; wl_done <= wl_d1;
        for (integer c = 0; c < 4; c++) for (integer p = 0; p < NB; p++) begin : ln
            reg [279:0] b; integer s;
            b = wl[(c*NB + p)*280 +: 280];
            if (rst_n && b[279]) begin
                s = int'(b[278:264]);
                if ((s % NB) != p) begin $display("TB FAIL: cluster %0d wide lane %0d carries sector %0d", c, p, s); errors++; end
                if (s * 8 + 7 >= VMW) begin $display("TB FAIL: cluster %0d VM sector %0d outside the slice", c, s); errors++; end
                else for (integer w = 0; w < 8; w++) if (b[w]) vm[c][s * 8 + w] = b[8 + 32*w +: 32];
                wl_d1[c*NB + p] <= 1'b1; nland = nland + 1; t_lastl = cyc;
            end
        end
    end
    // ---------------------------------------------------------------- stimulus / oracle
    function automatic [226:0] mkld(input longint hb, input longint hst, input integer vb, input integer vst, input integer m, input integer n);
        mkld = {21'(n), 20'(m), 16'd1, 32'(vst), 40'(vb), 3'd0, 2'd1, 16'd1, 32'(hst), {3'd0, 37'(hb)}, 3'd0, 2'd0};
    endfunction
    integer exp_sec = 0; reg armed = 0; longint t_first = 0, t_acc = 0, t_done = 0;
    always @(posedge clk) if (rst_n && armed) begin
        if ((fence_quiet || done) && cyc > t_first + 4 && nland < exp_sec && errors < 8) begin
            $display("TB FAIL: fence_quiet %0d done %0d at cycle %0d with %0d of %0d VM sectors landed", fence_quiet, done, cyc - t_first, nland, exp_sec);
            errors++;
        end
        if (|e_acc && t_acc == 0) t_acc = cyc;
    end
    task automatic beat(input integer q, input bit last, input [226:0] m);
        g_v = 1; g_q = 2'(q); g_last = last; g_mv = m;
        begin : hs
            bit r; integer w;
            r = 0; w = 0;
            while (!r && w < 4000) begin r = g_rdy; @(negedge clk); w++; end
            if (!r) begin $display("TB FAIL: beat for cluster %0d never accepted", q); errors++; end
        end
    endtask
    longint tp, tp_max = 0;
    task automatic run(input integer slot, input bit mirror);
        integer to, vb [0:3], vs, pb; longint loc;
        to = 0; loc = COLB + slot * CSTR;
        hw.delete(); nland = 0; t_acc = 0; t_lastl = 0;
        // the NATIVE slot image (logical row 80q + j on stack q at slot row q + 4j; from the logical h / PRE only) and the expected slices
        for (integer c = 0; c < 4; c++) for (integer i = 0; i < VMW; i++) begin vm[c][i] = $urandom; ev[c][i] = vm[c][i]; end
        vs = 64; pb = mirror ? 65536 + 20480 : 8192;
        for (integer c = 0; c < 4; c++) vb[c] = mirror ? 65536 + 5120 * c : 128 + 1024 * c;
        for (integer o = 0; o < 320; o++) for (integer i = 0; i < 64; i++) begin : hh
            reg [31:0] v; v = $urandom;
            hw[((longint'(o / 80) << SBIT) | (loc + 64 * (o / 80) + 256 * (o % 80))) / 4 + i] = v;
            ev[o / 80][vb[o / 80] + (o % 80) * vs + i] = v;
        end
        for (integer i = 0; i < 8; i++) begin : pp reg [31:0] v; v = $urandom; hw[(loc + 81920) / 4 + i] = v; ev[0][pb + i] = v; end
        exp_sec = 4 * 640 + 1;
        repeat (6) @(negedge clk);
        if (!fence_quiet) begin $display("TB FAIL: not quiet before the group"); errors++; end
        t_first = cyc; armed = 1;
        for (integer c = 0; c < 4; c++)
            beat(c, c == 3, mkld((longint'(c) << SBIT) | (loc + 64 * c), 256, vb[c], vs, 80, 64));
        beat(0, 1, mkld(loc + 81920, 0, pb, 64, 1, 8));
        g_v = 0;
        while (!done && !fault && to < 20000) begin @(negedge clk); to++; end
        t_done = cyc; tp = t_done - t_first; armed = 0;
        if (done && nland < exp_sec) begin $display("TB FAIL: EARLY DONE at +%0d with %0d of %0d VM sectors landed", tp, nland, exp_sec); errors++; end
        if (fault) begin $display("TB FAIL: fault (slot %0d mirror %0d)", slot, mirror); errors++; end
        if (to >= 20000) begin $display("TB FAIL: timeout (slot %0d mirror %0d): %0d sectors landed, %0d requests", slot, mirror, nland, nreq); errors++; end
        repeat (60) @(negedge clk);
        begin : chk
            integer bad; bad = 0;
            for (integer c = 0; c < 4; c++) for (integer i = 0; i < VMW; i++) if (vm[c][i] !== ev[c][i]) begin
                if (bad < 3) $display("  cluster %0d VM word %0d = %h expected %h", c, i, vm[c][i], ev[c][i]);
                bad++;
            end
            if (bad) begin $display("TB slot %0d %s: %0d wrong VM words", slot, mirror ? "MIRROR" : "LOCAL", bad); errors++; end
            else $display("TB slot %0d %s: 4 slices exact (%0d sectors landed); dispatch -> done %0d cycles (first accept +%0d, last landed +%0d)",
                          slot, mirror ? "MIRROR" : "LOCAL", nland, tp, t_acc - t_first, t_lastl - t_first);
        end
        if (tp > tp_max) tp_max = tp;
    endtask
    initial begin
        void'($urandom(SEED));
        repeat (4) @(posedge clk); rst_n = 1; repeat (40 + 2 * DHOPS) @(posedge clk);
        begin : runs
            integer sl [0:5]; bit mi [0:5];
            sl = '{0, 0, 5, 12, 12, 7}; mi = '{0, 1, 0, 0, 1, 1};
            for (integer k = 0; k < 6 && errors == 0; k++) run(sl[k], mi[k]);
        end
        if (errors == 0 && !fault && tp_max > LIMIT) $display("TB THROUGHPUT FAIL: %0d cycles > limit %0d (price 336)", tp_max, LIMIT);
        if (errors == 0 && !fault && tp_max <= LIMIT)
            $display("TB_HGI_B2_SWAPIN_GRP PASS (MUT %0d DHOPS %0d HOPS %0d RLAT %0d LD %0d) exact, worst dispatch -> done %0d cycles (price 336, limit %0d, ratio %0.3f)",
                     MUT, DHOPS, HOPS, RLAT, LD, tp_max, LIMIT, real'(tp_max) / 336.0);
        else $display("TB_HGI_B2_SWAPIN_GRP FAIL (MUT %0d) errors %0d worst %0d cycles", MUT, errors, tp_max);
        $finish;
    end
    initial begin #4000000; $display("TB_HGI_B2_SWAPIN_GRP FAIL: global timeout"); $finish; end
endmodule
`default_nettype wire
