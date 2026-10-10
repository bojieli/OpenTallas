`timescale 1ns/1ps
// hgi-takeover 2026-10-10: ot_hgi_dma_front against an svc-stream MODEL per the hgi-takeover.log interface spec (per
// stack: requests {tag, nsec, addr}; 8 lanes, lane l = idx % 8 in order, credit 4 a lane, random lane latencies and
// gaps) and a VM wide-port model.  Every LOAD's VM destination words are compared with an independent decode of the
// HBM model (BF16 << 16, E4M3 exact / NaN -> 0x7FC00000, INT8 exact, FP32 / U32 the word); no other VM word may change.
// Reports cycles and destination bytes a cycle.  +MUT via parameter MUT (1 BF16 lane mirror, 2 early tag free): FAIL.
module tb_hgi_dma_front;
    parameter integer MUT = 0;
    localparam integer NS = 4, NL = 8, NIN = 32;
    localparam integer SBIT = 20; localparam longint SB = 1048576;   // 1 MiB stacks in the bench
    reg clk = 0; always #1 clk = ~clk; reg rst_n = 0;
    reg mv_v = 0; reg [226:0] mv = 0; wire mv_rdy, mv_done, mv_fault;
    wire [NS*51-1:0] dq; reg [NS-1:0] dq_rdy = 0; reg [NIN*270-1:0] dd = 0; wire [NIN-1:0] dd_cr;
    wire [32*280-1:0] wl; reg [31:0] wl_done = 0;
    ot_hgi_dma_front #(.NS(NS), .NL(NL), .SBIT(SBIT), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .mv_v(mv_v),
        .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done), .mv_fault(mv_fault), .dq(dq), .dq_rdy(dq_rdy), .dd(dd), .dd_cr(dd_cr),
        .wl(wl), .wl_done(wl_done));
    // ---- memories
    function automatic [7:0] hb(input longint a); hb = 8'((a * 2654435761 + (a >> 7) * 40503) >> 3); endfunction
    reg [31:0] vm [0:262143];
    reg [31:0] wl_d1 = 0;
    always @(posedge clk) begin
        wl_d1 <= 0; wl_done <= wl_d1;
        for (integer p = 0; p < 32; p = p + 1) if (wl[p*280 + 279]) begin
            if (wl[p*280 + 264 +: 5] != 5'(p)) $fatal(1, "wide lane %0d carries bank %0d", p, wl[p*280 + 264 +: 5]);
            for (integer w = 0; w < 8; w = w + 1) if (wl[p*280 + w]) vm[{wl[p*280 + 264 +: 15], 3'(w)}] = wl[p*280 + 8 + 32*w +: 32];
            wl_d1[p] <= 1'b1;
        end
    end
    // ---- svc model: per stack a request queue; per lane a beat queue in idx order; credit 4 a lane
    integer rq_n [0:NS-1]; reg [49:0] rq [0:NS-1][0:63]; integer rq_h [0:NS-1];
    integer cr [0:NIN-1]; integer nxt [0:NS-1];               // next idx of the head request to schedule
    reg [269:0] lb [0:NIN-1][0:1023]; integer lh [0:NIN-1]; integer lt [0:NIN-1];
    initial for (integer i = 0; i < NIN; i = i + 1) begin cr[i] = 4; lh[i] = 0; lt[i] = 0; end
    initial for (integer s = 0; s < NS; s = s + 1) begin rq_n[s] = 0; rq_h[s] = 0; nxt[s] = 0; end
    always @(posedge clk) if (rst_n) begin
        dd <= 0;
        for (integer s = 0; s < NS; s = s + 1) begin
            dq_rdy[s] <= full || ($urandom % 4) != 0;
            if (dq[s*51 + 50] && dq_rdy[s]) begin rq[s][(rq_h[s] + rq_n[s]) % 64] = dq[s*51 +: 50]; rq_n[s] = rq_n[s] + 1; end
            // schedule up to 8 sectors of the head request into the lane queues (the svc reading its PCs)
            for (integer k = 0; k < 8 && rq_n[s] > 0; k = k + 1) begin : sch
                reg [49:0] r; reg [255:0] sd; longint a; integer l;
                r = rq[s][rq_h[s] % 64];
                a = longint'(r[36:0]) + 32 * nxt[s];
                for (integer b = 0; b < 32; b = b + 1) sd[8*b +: 8] = hb(a + b);
                l = s * NL + (nxt[s] % 8);
                lb[l][lt[l] % 1024] = {1'b1, 1'b0, r[49:46], 8'(nxt[s]), sd}; lt[l] = lt[l] + 1;
                nxt[s] = nxt[s] + 1;
                if (nxt[s] == int'(r[45:37])) begin nxt[s] = 0; rq_h[s] = rq_h[s] + 1; rq_n[s] = rq_n[s] - 1; end
            end
        end
        for (integer i = 0; i < NIN; i = i + 1) begin
            if (dd_cr[i]) cr[i] = cr[i] + 1;
            if (lt[i] > lh[i] && cr[i] > 0 && (full || ($urandom % 5) != 0)) begin dd[i*270 +: 270] <= lb[i][lh[i] % 1024]; lh[i] = lh[i] + 1; cr[i] = cr[i] - 1; end
        end
    end
    // ---- reference decode
    // binary32 bits of an exactly representable normal / zero double (Verilator's $shortrealtobits is not reliable)
    function automatic [31:0] f32(input real v);
        reg [63:0] d;
        begin
            d = $realtobits(v);
            f32 = (d[62:0] == 63'd0) ? {d[63], 31'd0} : {d[63], 8'(d[62:52] - 11'd1023 + 11'd127), d[51:29]};
        end
    endfunction
    function automatic [31:0] e4(input [7:0] c);
        real v; integer e, m; reg [31:0] r;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 15 && m == 7) e4 = 32'h7FC00000;
            else begin
                v = (e == 0) ? (m / 8.0) * (2.0 ** -6) : (1.0 + m / 8.0) * (2.0 ** (e - 7));
                r = f32(v); r[31] = c[7];
                if (v == 0.0) r = {c[7], 31'd0};
                e4 = r;
            end
        end
    endfunction
    function automatic [31:0] i8(input [7:0] c); i8 = f32(real'($signed(c))); if (c == 0) i8 = 0; endfunction
    integer full = 0; initial full = $test$plusargs("FULL");     // +FULL: the svc model at its full rate (no gaps)
    integer errs = 0, cyc = 0, tbytes = 0, tcyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    task automatic load(input [2:0] f, input longint sbase, input longint sstr, input integer dbase, input integer dstr,
                        input integer m, input integer n);
        integer es, t0, o, i, e0; longint a; reg [31:0] want;
        begin
            es = (f == 0 || f == 5) ? 4 : (f == 1) ? 2 : 1; e0 = errs;
            for (i = 0; i < 262144; i = i + 1) vm[i] = 32'hA5A5_0000 + i;
            mv = 0; mv[1:0] = 0; mv[4:2] = f; mv[44:5] = 40'(sbase); mv[76:45] = 32'(sstr); mv[92:77] = 1;
            mv[94:93] = 1; mv[97:95] = 0; mv[137:98] = 40'(dbase); mv[169:138] = 32'(dstr); mv[185:170] = 1;
            mv[205:186] = 20'(m); mv[226:206] = 21'(n);
            @(negedge clk); mv_v = 1; while (!mv_rdy) @(negedge clk); @(negedge clk); mv_v = 0; t0 = cyc;
            while (!mv_done && !mv_fault && cyc - t0 < 200000) @(negedge clk);
            if (!mv_done) begin $display("FAIL load f %0d m %0d n %0d: done %0d fault %0d", f, m, n, mv_done, mv_fault); errs = errs + 1; end
            else begin
                tcyc = tcyc + (cyc - t0); tbytes = tbytes + m * n * 4;
                for (o = 0; o < m; o = o + 1) for (i = 0; i < n; i = i + 1) begin
                    a = sbase + o * sstr + i * es;
                    case (f)
                        1: want = {hb(a + 1), hb(a), 16'd0};
                        2: want = e4(hb(a));
                        4: want = i8(hb(a));
                        default: want = {hb(a + 3), hb(a + 2), hb(a + 1), hb(a)};
                    endcase
                    if (vm[dbase + o * dstr + i] !== want) begin
                        if (errs < 8) $display("FAIL f %0d row %0d elem %0d: vm %h want %h", f, o, i, vm[dbase + o * dstr + i], want);
                        errs = errs + 1;
                    end
                end
                begin : untouched
                    integer w, o2, hit, bad; bad = 0;
                    for (w = 0; w < 262144; w = w + 1) begin
                        hit = 0;
                        for (o2 = 0; o2 < m; o2 = o2 + 1) if (w >= dbase + o2 * dstr && w < dbase + o2 * dstr + n) hit = 1;
                        if (!hit && vm[w] !== 32'hA5A5_0000 + w) bad = bad + 1;
                    end
                    if (bad != 0) begin $display("FAIL f %0d: %0d words outside the destination changed", f, bad); errs = errs + 1; end
                end
                if (errs != e0) $display("  load f %0d: %0d errors", f, errs - e0);
                $display("LOAD f %0d m %0d n %0d: %0d cycles, %0.1f destination B / cycle", f, m, n, cyc - t0, (m * n * 4.0) / (cyc - t0));
            end
        end
    endtask
    initial begin
        repeat (4) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
        load(0, 64'h0000, 2048, 1024, 512, 4, 512);                      // FP32 rows, one stack
        load(1, 64'h1000, 8192, 8192, 4096, 3, 4096);                    // BF16
        load(2, 64'h4000, 4096, 40000, 4096, 2, 4096);                   // FP8
        load(4, 64'h8000, 1024, 100000, 1024, 5, 1024);                  // INT8
        load(0, 64'h0, 64'(SB), 150000, 2048, 4, 2048);                  // FP32 rows striped over the 4 stacks
        load(2, 64'h100, 64'(SB), 200000, 8192, 4, 8192);                // FP8 striped (4 x 32 KB raw -> 128 KB VM)
        load(0, 64'h2000, 32, 250000, 8, 64, 8);                         // 64 one-sector rows
        load(0, 64'h0, 64'(SB), 0, 16384, 4, 16384);                    // FP32 striped, 4 x 64 KB (steady state)
        load(1, 64'h0, 64'(SB), 100000, 32768, 4, 32768);               // BF16 striped, 4 x 64 KB raw -> 512 KB VM
        if (errs == 0) $display("PASS HGI_DMA_FRONT %0d B in %0d cycles (%0.1f B / cycle overall)", tbytes, tcyc, (1.0 * tbytes) / tcyc);
        else $display("FATAL HGI_DMA_FRONT errors=%0d", errs);
        $finish;
    end
endmodule
