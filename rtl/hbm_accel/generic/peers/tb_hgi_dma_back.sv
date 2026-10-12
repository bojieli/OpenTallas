`timescale 1ns/1ps
`default_nettype none
// tb_hgi_dma_back ([tputx-mtp] 2026-10-12): ot_hgi_dma_back against a word-exact reference of every move.
//   VM model: the DMA wide READ group (32 lanes, lane b serves sectors s[4:0] = b, in order, LAT + 0..JIT cycles, the
//   lane credit back at the bank pop = the next edge; c_gnt = c_req one edge later).
//   svc WRITE model: HOPS registered wire stages each way; a beat is written at its sector address on arrival (its lane
//   must belong to the address's stack), its credit goes back HOPS edges later, the stack's written count ALAT edges later.
//   Moves are issued like the DMA record adapter does (POSTED): the next one as soon as the engine is ready (after the
//   previous one's src); at every src the bench overwrites that move's VM source (a posted retire frees it).
//   Tests: P the production swapout (STRIPE4 h 320 x 64 FP32 + linear PRE 8 words, measured mv_v -> done), L a 640-sector
//   linear row (crosses the 256-sector boundaries), S strided multi-row moves (serial windows), R random moves.
//   PASS = every expected HBM word written with the source value, no other HBM word written, done after all.
module tb_hgi_dma_back;
    parameter integer MUT = 0;
    parameter integer LAT = 6;
    parameter integer JIT = 0;
    parameter integer HOPS = 3;
    parameter integer ALAT = 40;
    parameter integer NRAND = 40;
    parameter integer SEED = 1;
    parameter integer NS = 4;          // 1: the HBM B2 per-cluster instance (stack STK only)
    parameter integer STK = 0;
    parameter integer NB = 32;         // VM lanes: 8 = the B2 local slice lane group
    parameter integer VCR = 32;        // VM read credits a lane (B2 slice group: 8)
    localparam integer NL = 8, SBIT = 35;
    reg clk = 0; always #1 clk = ~clk; reg rst_n = 0;
    reg mv_v = 0; reg [226:0] mv = 0; wire mv_rdy, mv_src, mv_done, mv_fault, quiet;
    wire [NB*16:0] vr2q; wire [NB*258:0] vr2r; wire [NS*NL*289-1:0] wd; wire [NS*NL-1:0] wd_cr; wire [NS*4-1:0] wa;
    ot_hgi_dma_back #(.NS(NS), .STK(STK), .NB(NB), .VCR(VCR), .SBIT(SBIT), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv),
        .mv_src(mv_src), .mv_done(mv_done), .mv_fault(mv_fault), .quiet(quiet), .vr2q(vr2q), .vr2r(vr2r),
        .wd(wd), .wd_cr(wd_cr), .wa(wa));
    // ---------------------------------------------------------------- VM model
    reg [31:0] vm [0:262143];
    reg gnt = 0; reg [NB-1:0] vcr = 0; reg [NB*257-1:0] vrr = 0;
    assign vr2r = {gnt, vcr, vrr};
    integer rq_s [0:31][0:255]; longint rq_due [0:31][0:255]; integer rq_h [0:31], rq_t [0:31]; longint ldue [0:31];
    longint cyc = 0;
    initial for (integer b = 0; b < 32; b++) begin rq_h[b] = 0; rq_t[b] = 0; ldue[b] = 0; end
    always @(posedge clk) begin
        cyc <= cyc + 1; gnt <= rst_n && vr2q[NB*16]; vcr <= '0; vrr <= '0;
        if (rst_n) for (integer b = 0; b < NB; b++) begin
            if (vr2q[b*16 + 15]) begin : rd
                integer sec; reg [255:0] d; longint du;
                sec = int'(vr2q[b*16 +: 15]);
                if (sec % NB != b) begin $display("TB FAIL: VM lane %0d got sector %0d", b, sec); $finish; end
                if (!gnt) begin $display("TB FAIL: VM read without the grant"); $finish; end
                du = cyc + LAT + ((JIT > 0) ? $urandom_range(0, JIT) : 0); if (du < ldue[b]) du = ldue[b]; ldue[b] = du;
                rq_s[b][rq_t[b] % 256] = sec; rq_due[b][rq_t[b] % 256] = du; rq_t[b] = rq_t[b] + 1; vcr[b] <= 1'b1;
                if (rq_t[b] - rq_h[b] > 32) begin $display("TB FAIL: VM lane %0d over its 32 credits", b); $finish; end
            end
            // the sector is read when it is answered (a VM bank may serve a queued read late): a source released before
            // its sectors landed is seen
            if (rq_h[b] < rq_t[b] && rq_due[b][rq_h[b] % 256] <= cyc) begin : rs
                reg [255:0] d2; integer sc; sc = rq_s[b][rq_h[b] % 256];
                for (integer w = 0; w < 8; w++) d2[w*32 +: 32] = vm[sc * 8 + w];
                vrr[b*257 +: 257] <= {1'b1, d2}; rq_h[b] = rq_h[b] + 1;
            end
        end
    end
    // ---------------------------------------------------------------- svc WRITE model
    reg [NS*NL*289-1:0] wdh [0:HOPS]; reg [NS*NL-1:0] crh [0:HOPS];
    always @* begin wdh[0] = wd; end
    always @(posedge clk) for (integer k = 1; k <= HOPS; k++) begin wdh[k] <= wdh[k-1]; crh[k] <= crh[k-1]; end
    assign wd_cr = crh[HOPS];
    reg [NS*NL-1:0] cr0 = 0; always @* crh[0] = cr0;
    reg [31:0] hbm [longint]; reg wr [longint];         // HBM words (byte address / 4) written, and the set written
    integer ackq [0:NS-1][0:1023]; longint ackt [0:NS-1][0:1023]; integer aq_h [0:NS-1], aq_t [0:NS-1];
    reg [NS*4-1:0] wa_r = 0; assign wa = wa_r;
    longint nwrit = 0, nack = 0;
    initial for (integer s = 0; s < NS; s++) begin aq_h[s] = 0; aq_t[s] = 0; end
    always @(posedge clk) begin
        cr0 <= '0; wa_r <= '0;
        for (integer s = 0; s < NS; s++) begin : st
            integer c; c = 0;
            for (integer l = 0; l < NL; l++) begin : ln
                reg [288:0] bt; longint a;
                bt = wdh[HOPS][(s*NL + l)*289 +: 289];
                if (bt[288]) begin
                    a = longint'(bt[287:256]) * 32;
                    if (((a >> SBIT) & 3) != ((STK + s) & 3)) begin $display("TB FAIL: stack %0d lane %0d got address %h", s, l, a); $finish; end
                    for (integer w = 0; w < 8; w++) begin hbm[a / 4 + w] = bt[w*32 +: 32]; wr[a / 4 + w] = 1'b1; end
                    cr0[s*NL + l] <= 1'b1; c = c + 1; nwrit = nwrit + 1;
                end
            end
            if (c > 0) begin ackq[s][aq_t[s] % 1024] = c; ackt[s][aq_t[s] % 1024] = cyc + ALAT; aq_t[s] = aq_t[s] + 1; end
            if (aq_h[s] < aq_t[s] && ackt[s][aq_h[s] % 1024] <= cyc) begin
                wa_r[s*4 +: 4] <= 4'(ackq[s][aq_h[s] % 1024]); nack = nack + ackq[s][aq_h[s] % 1024]; aq_h[s] = aq_h[s] + 1;
            end
        end
    end
    // ---------------------------------------------------------------- reference
    reg [31:0] exp_w [longint];
    function automatic longint rowaddr(input longint base, input longint st, input integer code, input integer o);
        longint loc, s0;
        if (code == 1) begin s0 = (base >> SBIT) & 3; loc = (base & ((longint'(1) << SBIT) - 1)) + o * st; rowaddr = (((s0 + o) & 3) << SBIT) | loc; end
        else rowaddr = base + o * st;
    endfunction
    // move word {n 21, m 20, dst istride 16, dst stride 32, dst base 40, dst fmt 3, dst space 2,
    //            src istride 16, src stride 32, src base 40, src fmt 3, src space 2}
    function automatic [226:0] mkmv(input integer vb, input integer vst, input longint db, input integer code, input longint dst,
                                    input integer m, input integer n, input integer fmt);
        mkmv = {21'(n), 20'(m), 16'd1, 32'(dst), {3'(code), 37'(db)}, 3'(fmt), 2'd0, 16'd1, 32'(vst), 40'(vb), 3'(fmt), 2'd1};
    endfunction
    // the posted issue queue: moves in flight; at each src the oldest unreleased move's source is scribbled
    reg [226:0] mq [0:255]; integer mq_n = 0, src_k = 0, iss_k = 0;
    integer errors = 0;
    task automatic expect_mv(input integer vb, input integer vst, input longint db, input integer code, input longint dst,
                             input integer m, input integer n);
        for (integer o = 0; o < m; o++) for (integer i = 0; i < n; i++)
            exp_w[rowaddr(db, dst, code, o) / 4 + i] = vm[vb + o * vst + i];
    endtask
    task automatic add_mv(input integer vb, input integer vst, input longint db, input integer code, input longint dst,
                          input integer m, input integer n, input integer fmt);
        expect_mv(vb, vst, db, code, dst, m, n);
        mq[mq_n] = mkmv(vb, vst, db, code, dst, m, n, fmt); mq_n = mq_n + 1;
    endtask
    always @(posedge clk) if (rst_n && mv_src) begin : scr
        reg [226:0] x; x = mq[src_k];
        for (integer o = 0; o < int'(x[205:186]); o++) for (integer i = 0; i < int'(x[226:206]); i++)
            vm[int'(x[44:5]) + o * int'(x[76:45]) + i] = 32'hDEAD0000 ^ 32'(i);
        src_k = src_k + 1;
    end
    task automatic run_queue(output longint t0, output longint t1);
        integer to; to = 0;
        @(negedge clk); t0 = cyc;
        while (iss_k < mq_n) begin
            mv_v = 1; mv = mq[iss_k];
            if (mv_rdy) iss_k = iss_k + 1;          // accepted at the coming edge
            @(negedge clk);
            to = to + 1; if (to > 200000) begin $display("TB FAIL: issue timeout"); errors++; mv_v = 0; return; end
            if (mv_fault) begin $display("TB FAIL: fault"); errors++; mv_v = 0; return; end
        end
        mv_v = 0;
        while (!(src_k == mq_n && quiet && !dut.dirty)) begin
            @(negedge clk); to = to + 1;
            if (to > 400000) begin $display("TB FAIL: drain timeout (src %0d of %0d)", src_k, mq_n); errors++; return; end
            if (mv_fault) begin $display("TB FAIL: fault"); errors++; return; end
        end
        t1 = cyc;
    endtask
    integer ndone = 0; always @(posedge clk) if (rst_n && mv_done) ndone = ndone + 1;
    task automatic check(input string nm);
        integer bad, extra; bad = 0; extra = 0;
        foreach (exp_w[a]) if (!wr.exists(a) || hbm[a] !== exp_w[a]) begin
            if (bad < 4) $display("  %s: HBM word %h = %h expected %h", nm, a * 4, wr.exists(a) ? hbm[a] : 32'hx, exp_w[a]);
            bad++;
        end
        foreach (wr[a]) if (!exp_w.exists(a)) extra++;
        if (bad || extra) begin $display("TB %s: %0d wrong, %0d stray words", nm, bad, extra); errors++; end
        else $display("TB %s: %0d words exact", nm, exp_w.size());
        exp_w.delete(); wr.delete(); hbm.delete(); mq_n = 0; src_k = 0; iss_k = 0;
    endtask
    // ---------------------------------------------------------------- tests
    longint t0, t1, tp; integer seed = SEED;
    initial begin
        void'($urandom(SEED));
        for (integer i = 0; i < 262144; i++) vm[i] = $urandom;
        repeat (4) @(posedge clk); rst_n = 1; repeat (8) @(posedge clk);
        if (NS == 1) begin : b2
            // HBM B2 per-cluster instance: the cluster's quarter of h (80 rows of 256 B, contiguous in its slice) to its
            // stack (stack-local COLB + STK x 64 + r x 256), cluster 0 also PRE; then a long row and random moves on STK
            longint sb; sb = longint'(STK) << SBIT;
            add_mv(0, 64, sb | (64'h180020000 + 64 * STK), 0, 256, 80, 64, 0);
            if (STK == 0) add_mv(20480, 64, 64'h180020000 + 81920, 0, 0, 1, 8, 0);
            run_queue(t0, t1); tp = t1 - t0;
            $display("TB TPUT B2 cluster %0d swapout quarter (20 KiB%s, store -> quiet): %0d cycles", STK, STK == 0 ? " + PRE" : "", tp);
            check("P1");
            for (integer i = 0; i < 262144; i++) vm[i] = $urandom;
            add_mv(64 * 7, 64, sb | 64'h1000, 0, 0, 1, 20480, 0);
            add_mv(64 * 400, 128, sb | 64'h40000, 0, 4096 + 32, 7, 24, 5);
            add_mv(64 * 1000, 64 * 4, sb | 64'h200000, 0, 512, 9, 40, 0);
            run_queue(t0, t1); check("L1");
            for (integer r = 0; r < NRAND; r++) begin : rnd1
                integer m, n, vb, vst; longint dst;
                for (integer i = 0; i < 262144; i++) vm[i] = $urandom;
                m = $urandom_range(1, 9); n = 8 * $urandom_range(1, 100);
                vst = 64 * ((n + 63) / 64 + $urandom_range(0, 2)); vb = 64 * $urandom_range(0, (262144 - vst * m) / 64 - 1);
                dst = 32 * ((n * 4 + 31) / 32 + $urandom_range(0, 3));
                add_mv(vb, vst, sb | (32 * longint'($urandom_range(0, 1 << 16))), 0, dst, m, n, 0);
                run_queue(t0, t1); check($sformatf("R%0d", r));
                if (errors) break;
            end
        end else begin : b4
        // P: the production swapout (ds_mtp_kernels swap(): h STRIPE4 320 x 64 FP32 at COLB + slot x CSTR, PRE 8 words)
        add_mv(0, 64, (longint'(1) << 37) | 64'h180020000, 1, 64, 320, 64, 0);
        add_mv(20480, 64, 64'h180020000 + 81920, 0, 0, 1, 8, 0);
        run_queue(t0, t1); tp = t1 - t0;
        $display("TB TPUT production swapout (STRIPE4 h 80 KiB + PRE 32 B, store -> quiet): %0d cycles (LAT %0d JIT %0d HOPS %0d ALAT %0d)", tp, LAT, JIT, HOPS, ALAT);
        check("P");
        for (integer i = 0; i < 262144; i++) vm[i] = $urandom;
        // L: one linear 640-sector row (stack 2), then U32 rows
        add_mv(64 * 7, 64, (longint'(2) << SBIT) | 64'h1000, 0, 0, 1, 20480, 0);
        add_mv(64 * 400, 128, 64'h40000, 0, 4096 + 32, 7, 24, 5);
        run_queue(t0, t1); check("L");
        for (integer i = 0; i < 262144; i++) vm[i] = $urandom;
        // S: strided rows whose bank groups collide (serial windows) and a STRIPE4 move with stride 0 offsets
        add_mv(64 * 100, 64 * 4, 64'h200000, 0, 512, 9, 40, 0);
        add_mv(64 * 200, 64 * 2, (longint'(1) << 37) | (longint'(3) << SBIT) | 64'h3000, 1, 1024, 11, 64 * 3, 0);
        run_queue(t0, t1); check("S");
        // R: random moves (non-overlapping VM sources and HBM rows)
        for (integer r = 0; r < NRAND; r++) begin : rnd
            integer m, n, code, vb, vst; longint db, dst;
            for (integer i = 0; i < 262144; i++) vm[i] = $urandom;
            m = $urandom_range(1, 9); n = 8 * $urandom_range(1, 100); code = $urandom_range(0, 1);
            vst = 64 * ((n + 63) / 64 + $urandom_range(0, 2)); vb = 64 * $urandom_range(0, (262144 - vst * m) / 64 - 1);
            dst = 32 * ((n * 4 + 31) / 32 + $urandom_range(0, 3));
            if (code == 1) db = (longint'(1) << 37) | (longint'($urandom_range(0, 3)) << SBIT) | (32 * longint'($urandom_range(0, 1 << 16)));
            else db = (longint'($urandom_range(0, 3)) << SBIT) | (32 * longint'($urandom_range(0, 1 << 16)));
            add_mv(vb, vst, db, code, dst, m, n, 0);
            if ($urandom_range(0, 1)) begin : two
                integer vb2; vb2 = (vb + vst * m + 64 * 8) % (262144 - 64 * 64); vb2 = vb2 - vb2 % 64;
                if (vb2 + 8 * 64 <= vb || vb2 >= vb + vst * m) add_mv(vb2, 64, (longint'(code ^ 1) << SBIT) | 64'h7F0000, 0, 0, 1, 8 * $urandom_range(1, 64), 0);
            end
            run_queue(t0, t1); check($sformatf("R%0d", r));
            if (errors) break;
        end
        end
        if (errors == 0 && !mv_fault) $display("TB_HGI_DMA_BACK PASS (MUT %0d) production %0d cycles", MUT, tp);
        else $display("TB_HGI_DMA_BACK FAIL (MUT %0d) errors %0d", MUT, errors);
        $finish;
    end
    initial begin #4000000; $display("TB_HGI_DMA_BACK FAIL: global timeout"); $finish; end
endmodule
`default_nettype wire
