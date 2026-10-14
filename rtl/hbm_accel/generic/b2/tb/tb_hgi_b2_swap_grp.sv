`timescale 1ns/1ps
`default_nettype none
// tb_hgi_b2_swap_grp ([mtp-dispatch] 2026-10-13): the native B2 MTP swap-out group (ot_hgi_b2_swap_disp + four REAL
// ot_hgi_dma_back NS 1 / NB 8 engines) against an INDEPENDENT oracle of the NATIVE slot image
// (tools/hgi_b2/mtp_swap.py NATIVE LAYOUT, 2026-10-13: cluster q moves ITS quarter of h, logical rows 80q .. 80q + 79, where the B2
// allocator holds it, to stack q's slot rows q + 4j; the STRIPE4 footprint with rows permuted by owner).
//   Stimulus = what tools/hgi_b2/mtp_swap.py emits: four linear own-stack h records (cluster q: 80 rows x 64 words, HBM
//   base (q << 35) | COLB + slot x CSTR + 64 q, row stride 256 B; VM descriptor = the cluster's allocation, compact LOCAL
//   base / stride 64 or MIRROR base 65536 + 5120 q / stride 64) as ONE group, then PRE (8 words, cluster 0).
//   Oracle = the LOGICAL native rule only: h row 80q + j on stack q at stack-local COLB + slot x CSTR + 64 q + 256 j; PRE on
//   stack 0 at COLB + slot x CSTR + 81920.  It never sees the native descriptors.
//   Cluster models (as tb_hgi_dma_back, production settings): VM slice wide READ group 8 lanes, LAT + 0..JIT, credits
//   VCR; svc WRITE HOPS stages each way, written counts back ALAT edges later.  At every engine src the bench overwrites
//   that record's VM source (a posted retire frees it).
//   PASS = every expected HBM word written with the source value, no other word written, no fault, fence_quiet / done
//   never before the last acknowledged sector, and dispatch (first beat valid) -> done <= LIMIT cycles in every run.
module tb_hgi_b2_swap_grp;
    parameter integer MUT = 0;
    parameter integer DHOPS = 10;
    parameter integer LAT = 6;
    parameter integer JIT = 5;
    parameter integer HOPS = 3;
    parameter integer ALAT = 40;
    parameter integer VCR = 8;
    parameter integer LIMIT = 272;       // 1.10 x 248 (immutable price)
    parameter integer SEED = 1;
    localparam integer NB = 8, NL = 8, SBIT = 35;
    localparam longint COLB = 64'h510000000, CSTR = 64'd131072;
    localparam integer VMW = 98304;
    reg clk = 0; always #1 clk = ~clk; reg rst_n = 0;
    reg g_v = 0, g_last = 0; reg [1:0] g_q = 0; reg [226:0] g_mv = 0;
    wire g_rdy, fence_quiet, done, fault; wire [3:0] e_src, e_acc;
    wire [4*129-1:0] vr2q; reg [4*2065-1:0] vr2r = 0; wire [4*2312-1:0] wd; wire [31:0] wd_cr; reg [15:0] wa = 0;
    ot_hgi_b2_swap_grp #(.DHOPS(DHOPS), .VCR(VCR), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .g_v(g_v), .g_rdy(g_rdy),
        .g_last(g_last), .g_q(g_q), .g_mv(g_mv), .fence_quiet(fence_quiet), .done(done), .fault(fault), .e_src(e_src),
        .e_acc(e_acc), .vr2q(vr2q), .vr2r(vr2r), .wd(wd), .wd_cr(wd_cr), .wa(wa));
    longint cyc = 0;
    // ---------------------------------------------------------------- VM slice models (one a cluster)
    reg [31:0] vm [0:3][0:VMW-1];
    integer rq_s [0:3][0:7][0:255]; longint rq_due [0:3][0:7][0:255]; integer rq_h [0:3][0:7], rq_t [0:3][0:7]; longint ldue [0:3][0:7];
    reg [3:0] gnt = 0;
    integer errors = 0;
    initial for (integer c = 0; c < 4; c++) for (integer b = 0; b < 8; b++) begin rq_h[c][b] = 0; rq_t[c][b] = 0; ldue[c][b] = 0; end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        for (integer c = 0; c < 4; c++) begin : vc
            reg [128:0] rq; reg [2064:0] rr;
            rq = vr2q[c*129 +: 129]; rr = '0;
            rr[2064] = gnt[c]; gnt[c] <= rst_n && rq[128];
            if (rst_n) for (integer b = 0; b < NB; b++) begin
                if (rq[b*16 + 15]) begin : rd
                    integer sec; longint du;
                    sec = int'(rq[b*16 +: 15]);
                    if (sec % NB != b) begin $display("TB FAIL: cluster %0d VM lane %0d got sector %0d", c, b, sec); errors++; end
                    if (!gnt[c]) begin $display("TB FAIL: cluster %0d VM read without the grant", c); errors++; end
                    du = cyc + LAT + ((JIT > 0) ? $urandom_range(0, JIT) : 0); if (du < ldue[c][b]) du = ldue[c][b]; ldue[c][b] = du;
                    rq_s[c][b][rq_t[c][b] % 256] = sec; rq_due[c][b][rq_t[c][b] % 256] = du; rq_t[c][b] = rq_t[c][b] + 1;
                    rr[NB*257 + b] = 1'b1;
                    // (as tb_hgi_dma_back: the credit is back at the bank pop = the next edge; the response pipeline holds <= 32)
                    if (rq_t[c][b] - rq_h[c][b] > 32) begin $display("TB FAIL: cluster %0d VM lane %0d over 32 in flight", c, b); errors++; end
                end
                if (rq_h[c][b] < rq_t[c][b] && rq_due[c][b][rq_h[c][b] % 256] <= cyc) begin : rs
                    integer sc; sc = rq_s[c][b][rq_h[c][b] % 256];
                    for (integer w = 0; w < 8; w++) rr[b*257 + w*32 +: 32] = vm[c][(sc * 8 + w) % VMW];
                    rr[b*257 + 256] = 1'b1; rq_h[c][b] = rq_h[c][b] + 1;
                end
            end
            vr2r[c*2065 +: 2065] <= rr;
        end
    end
    // ---------------------------------------------------------------- svc WRITE models (one a stack)
    reg [4*2312-1:0] wdh [0:HOPS]; reg [31:0] crh [0:HOPS]; reg [31:0] cr0 = 0;
    always @* begin wdh[0] = wd; crh[0] = cr0; end
    always @(posedge clk) for (integer k = 1; k <= HOPS; k++) begin wdh[k] <= wdh[k-1]; crh[k] <= crh[k-1]; end
    assign wd_cr = crh[HOPS];
    reg [31:0] hbm [longint]; reg wr [longint];
    integer ackq [0:3][0:1023]; longint ackt [0:3][0:1023]; integer aq_h [0:3], aq_t [0:3];
    longint nwrit = 0, nack = 0, t_lastw = 0, t_lastack = 0;
    initial for (integer s = 0; s < 4; s++) begin aq_h[s] = 0; aq_t[s] = 0; end
    always @(posedge clk) begin
        cr0 <= '0; wa <= '0;
        for (integer s = 0; s < 4; s++) begin : st
            integer c; c = 0;
            for (integer l = 0; l < NL; l++) begin : ln
                reg [288:0] bt; longint a;
                bt = wdh[HOPS][(s*NL + l)*289 +: 289];
                if (bt[288]) begin
                    a = longint'(bt[287:256]) * 32;
                    if (((a >> SBIT) & 3) != s) begin $display("TB FAIL: stack %0d lane %0d got address %h", s, l, a); errors++; end
                    for (integer w = 0; w < 8; w++) begin
                        if (wr.exists(a / 4 + w)) begin $display("TB FAIL: HBM word %h written twice", a + w * 4); errors++; end
                        hbm[a / 4 + w] = bt[w*32 +: 32]; wr[a / 4 + w] = 1'b1;
                    end
                    cr0[s*NL + l] <= 1'b1; c = c + 1; nwrit = nwrit + 1; t_lastw = cyc;
                end
            end
            if (c > 0) begin ackq[s][aq_t[s] % 1024] = c; ackt[s][aq_t[s] % 1024] = cyc + ALAT; aq_t[s] = aq_t[s] + 1; end
            if (aq_h[s] < aq_t[s] && ackt[s][aq_h[s] % 1024] <= cyc) begin
                wa[s*4 +: 4] <= 4'(ackq[s][aq_h[s] % 1024]); nack = nack + ackq[s][aq_h[s] % 1024]; aq_h[s] = aq_h[s] + 1;
                t_lastack = cyc;
            end
        end
    end
    // ---------------------------------------------------------------- stimulus / oracle
    function automatic [226:0] mkmv(input integer vb, input integer vst, input longint db, input longint dst, input integer m, input integer n);
        mkmv = {21'(n), 20'(m), 16'd1, 32'(dst), {3'd0, 37'(db)}, 3'd0, 2'd0, 16'd1, 32'(vst), 40'(vb), 3'd0, 2'd1};
    endfunction
    reg [31:0] h [0:319][0:63]; reg [31:0] pre [0:7];
    reg [31:0] exp_w [longint];
    // the VM source of each record a cluster receives (issue order), scribbled at its src
    integer sv_b [0:3][0:1], sv_s [0:3][0:1], sv_m [0:3][0:1], sv_n [0:3][0:1]; integer sv_k [0:3], sv_t [0:3];
    always @(posedge clk) if (rst_n) for (integer c = 0; c < 4; c++) if (e_src[c]) begin
        if (sv_k[c] < sv_t[c])
            for (integer o = 0; o < sv_m[c][sv_k[c]]; o++) for (integer i = 0; i < sv_n[c][sv_k[c]]; i++)
                vm[c][sv_b[c][sv_k[c]] + o * sv_s[c][sv_k[c]] + i] = 32'hDEAD0000 ^ 32'(i);
        sv_k[c] = sv_k[c] + 1;
    end
    // fence monitor: after the release, fence_quiet / done only once every expected sector is acknowledged
    integer exp_sec = 0; reg armed = 0; longint t_first = 0, t_rel = 0, t_acc = 0, t_src = 0, t_done = 0;
    always @(posedge clk) if (rst_n && armed) begin
        if ((fence_quiet || done) && cyc > t_first + 4 && nack < exp_sec && errors < 8) begin
            $display("TB FAIL: fence_quiet %0d done %0d at cycle %0d with %0d of %0d sectors acknowledged", fence_quiet, done, cyc - t_first, nack, exp_sec);
            errors++;
        end
        if (t_rel == 0 && (dut.dn[0] | dut.dn[228] | dut.dn[456] | dut.dn[684])) t_rel = cyc;
        if (|e_acc && t_acc == 0) t_acc = cyc;
        if (|e_src) t_src = cyc;
    end
    task automatic beat(input integer q, input bit last, input [226:0] m);
        g_v = 1; g_q = 2'(q); g_last = last; g_mv = m;
        begin : hs
            bit r; integer w;
            r = 0; w = 0;
            while (!r && w < 4000) begin r = g_rdy; @(negedge clk); w++; end   // g_rdy high before the edge: accepted at that edge
            if (!r) begin $display("TB FAIL: beat for cluster %0d never accepted", q); errors++; end
        end
    endtask
    longint tp, tp_max = 0;
    task automatic run(input integer slot, input bit mirror);
        integer to; longint loc;
        to = 0; loc = COLB + slot * CSTR;
        exp_w.delete(); wr.delete(); hbm.delete(); nwrit = 0; nack = 0; t_rel = 0; t_acc = 0; t_src = 0; t_lastw = 0; t_lastack = 0;
        for (integer c = 0; c < 4; c++) begin sv_k[c] = 0; sv_t[c] = 0; for (integer i = 0; i < VMW; i++) vm[c][i] = $urandom; end
        for (integer o = 0; o < 320; o++) for (integer i = 0; i < 64; i++) h[o][i] = $urandom;
        for (integer i = 0; i < 8; i++) pre[i] = $urandom;
        // ORACLE: the NATIVE slot image (logical row 80q + j on stack q at slot row q + 4j), from the logical h / PRE only
        for (integer o = 0; o < 320; o++) for (integer i = 0; i < 64; i++)
            exp_w[((longint'(o / 80) << SBIT) | (loc + 64 * (o / 80) + 256 * (o % 80))) / 4 + i] = h[o][i];
        for (integer i = 0; i < 8; i++) exp_w[(loc + 81920) / 4 + i] = pre[i];
        exp_sec = 4 * 640 + 1;
        // the clusters' allocations: compact LOCAL (the cluster's quarter, rows 80q + j, packed at 128 + 64 j) or MIRROR (the whole h at 65536: quarter q at 65536 + 5120 q)
        for (integer c = 0; c < 4; c++) begin
            sv_b[c][0] = mirror ? 65536 + 5120 * c : 128 + 1024 * c; sv_s[c][0] = 64; sv_m[c][0] = 80; sv_n[c][0] = 64; sv_t[c] = 1;
            if (mirror) begin for (integer o = 0; o < 320; o++) for (integer i = 0; i < 64; i++) vm[c][65536 + 64 * o + i] = h[o][i]; end
            else for (integer j = 0; j < 80; j++) for (integer i = 0; i < 64; i++) vm[c][sv_b[c][0] + 64 * j + i] = h[80 * c + j][i];
        end
        sv_b[0][1] = mirror ? 65536 + 20480 : 8192; sv_s[0][1] = 64; sv_m[0][1] = 1; sv_n[0][1] = 8; sv_t[0] = 2;
        for (integer i = 0; i < 8; i++) vm[0][sv_b[0][1] + i] = pre[i];
        repeat (6) @(negedge clk);
        if (!fence_quiet) begin $display("TB FAIL: not quiet before the group"); errors++; end
        t_first = cyc; armed = 1;
        for (integer c = 0; c < 4; c++)
            beat(c, c == 3, mkmv(sv_b[c][0], sv_s[c][0], (longint'(c) << SBIT) | (loc + 64 * c), 256, 80, 64));
        beat(0, 1, mkmv(sv_b[0][1], 64, loc + 81920, 0, 1, 8));
        g_v = 0;
        while (!done && !fault && to < 20000) begin @(negedge clk); to++; end
        t_done = cyc; tp = t_done - t_first; armed = 0;
        if (done && nack < exp_sec) begin          // the fence answer before the last acknowledged sector
            $display("TB FAIL: EARLY FENCE: done at +%0d with %0d of %0d sectors acknowledged (%0d written)", tp, nack, exp_sec, nwrit); errors++;
        end
        if (fault) begin $display("TB FAIL: fault (slot %0d mirror %0d)", slot, mirror); errors++; end
        if (to >= 20000) begin $display("TB FAIL: timeout (slot %0d mirror %0d)", slot, mirror); errors++; end
        repeat (ALAT + 2 * HOPS + 30) @(negedge clk);       // late / stray writes after the fence
        begin : chk
            integer bad, extra; bad = 0; extra = 0;
            foreach (exp_w[a]) if (!wr.exists(a) || hbm[a] !== exp_w[a]) begin
                if (bad < 3) $display("  HBM word %h = %h expected %h", a * 4, wr.exists(a) ? hbm[a] : 32'hx, exp_w[a]);
                bad++;
            end
            foreach (wr[a]) if (!exp_w.exists(a)) extra++;
            if (bad || extra) begin $display("TB slot %0d %s: %0d wrong, %0d stray words", slot, mirror ? "MIRROR" : "LOCAL", bad, extra); errors++; end
            else $display("TB slot %0d %s: %0d words exact, 0 stray; dispatch -> done %0d cycles (release +%0d, first accept +%0d, last src +%0d, last write +%0d, last ack +%0d)",
                          slot, mirror ? "MIRROR" : "LOCAL", exp_w.size(), tp, t_rel - t_first, t_acc - t_first, t_src - t_first, t_lastw - t_first, t_lastack - t_first);
        end
        if (tp > tp_max) tp_max = tp;
    endtask
    initial begin
        void'($urandom(SEED));
        repeat (4) @(posedge clk); rst_n = 1; repeat (40 + 2 * DHOPS) @(posedge clk);
        begin : runs                           // a failed run leaves writes in flight: stop at the first one
            integer sl [0:5]; bit mi [0:5];
            sl = '{0, 0, 5, 12, 12, 7}; mi = '{0, 1, 0, 0, 1, 1};
            for (integer k = 0; k < 6 && errors == 0; k++) run(sl[k], mi[k]);
        end
        if (errors == 0 && tp_max > LIMIT) $display("TB THROUGHPUT FAIL: %0d cycles > limit %0d (price 248)", tp_max, LIMIT);
        if (errors == 0 && !fault && tp_max <= LIMIT)
            $display("TB_HGI_B2_SWAP_GRP PASS (MUT %0d DHOPS %0d LAT %0d JIT %0d HOPS %0d ALAT %0d) exact, worst dispatch -> fence %0d cycles (price 248, limit %0d, ratio %0.3f)",
                     MUT, DHOPS, LAT, JIT, HOPS, ALAT, tp_max, LIMIT, real'(tp_max) / 248.0);
        else $display("TB_HGI_B2_SWAP_GRP FAIL (MUT %0d) errors %0d worst %0d cycles", MUT, errors, tp_max);
        $finish;
    end
`ifdef SWAP_DBG
    always @(posedge clk) if ((cyc < 600 && cyc % 20 == 0) || (cyc > 0 && cyc % 100000 == 0))
        $display("c %0d rst %b grdy %b gv %b fq %b cnt %0d hv %b cred %0d%0d%0d%0d uq %b dv %b nwrit %0d nack %0d fault %b", cyc, rst_n, g_rdy, g_v, fence_quiet,
            dut.u_s.cnt, dut.u_s.hv, dut.u_s.cred[0], dut.u_s.cred[1], dut.u_s.cred[2], dut.u_s.cred[3], dut.u_s.u_quiet, dut.u_s.dv, nwrit, nack, fault);
`endif
    initial begin #2000000; $display("TB_HGI_B2_SWAP_GRP FAIL: global timeout"); $finish; end
endmodule
`default_nettype wire
