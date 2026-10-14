`timescale 1ns/1ps
// el1013-hbm-hc: transaction-exactness bench of the B2 chunk path: 4 x ot_hgi_hc_cat_b2 (the quarters' concentrators)
// -> a link model (LD packet flops, credit pulses held back at random) -> ot_hgi_hc_coll_b2.  Vectors
// tools/hgi_adapters/hc_coll_b2_bench.py: 640 chunk leaves a row and the golden sum (hdc_golden_v41.split_sum, chunk8).
// The bench plays the 32 lanes (lane 8 q + l owns tags 160 q + l + 8 m, m = 0..19).  Rows:
//   0 ORDER   every lane in m order, one chunk a cycle (faster than production: the queues fill)
//   1 OOO     every lane in a random m order with random gaps, the quarters started 0 / 150 / 300 / 450 cycles apart
//   2 BACKP   random order, credit pulses held back at random (up to ~8 cycles): the senders run out of credit
//   3 ABORT   half a row sent, then the row is abandoned (packets still in flight / queued)
//   4 STALE   the next row starts at once: the abandoned row's packets must be dropped, this row exact
//   5 DUP     one lane repeats a tag (other data): flt must rise
//   6 AFTER   a clean row after the fault: exact (clr recovers)
//   7 RANGE   a lane of quarter 1 sends a tag of quarter 2: flt must rise
//   8 AFTER2  clean, exact;  9 BACKP2 as 2 with another seed;  10 OOO2;  11 ORDER2
// Checks every row: ss bit-exact when expected, flt exactly when expected, no credit ever outstanding beyond CD, no
// concentrator overflow, every credit home at the end.  Prints HGI_HC_COLL_B2 PASS / FAIL.
module tb_hgi_hc_coll_b2;
    `include "coll_sizes.svh"
`ifndef CDV
 `define CDV 16
`endif
`ifndef HMUT
 `define HMUT 0
`endif
`ifndef LDV
 `define LDV 6
`endif
    localparam integer CD = `CDV, LD = `LDV, MUT = `HMUT;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg [31:0] chm [0:NROW*640-1]; reg [31:0] ssm [0:NROW-1];
    reg [8*256-1:0] dir; integer seed;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("SEED=%d", seed)) seed = 1013;
        i = $urandom(seed);
        $readmemh({dir, "/coll_chunk.mem"}, chm); $readmemh({dir, "/coll_ss.mem"}, ssm);
    end
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    // DUT
    reg clr = 0; reg [1:0] ep = 0;
    reg [31:0] ch_v = 0; reg [32*42-1:0] ch = 0;
    wire [7:0] ck_v; wire [8*44-1:0] ck; reg [7:0] ck_cr = 0; wire [3:0] c_ovf;
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_q
        ot_hgi_hc_cat_b2 #(.NL(8), .P(2), .QD(32), .CD(CD), .MUT(MUT)) u_cat (.clk(clk), .rst_n(rst_n), .flush(clr), .ep(ep),
            .ch_v(ch_v[gq*8 +: 8]), .ch(ch[gq*336 +: 336]), .ck_v(ck_v[gq*2 +: 2]), .ck(ck[gq*88 +: 88]),
            .ck_cr(ck_cr[gq*2 +: 2]), .ovf(c_ovf[gq]));
    end endgenerate
    // link: LD flops on the packets
    reg [7:0] lv [0:LD]; reg [8*44-1:0] ld [0:LD];
    integer i;
    always @(posedge clk) begin
        lv[0] <= ck_v; ld[0] <= ck;
        for (i = 1; i <= LD; i = i + 1) begin lv[i] <= lv[i-1]; ld[i] <= ld[i-1]; end
    end
    wire [7:0] pk_cr; wire ss_v, flt; wire [31:0] ss; wire [15:0] n_stale;
`ifdef HC_STORELEAF
    localparam integer STOREMODE=1;
`else
    localparam integer STOREMODE=0;
`endif
    ot_hgi_hc_coll_b2 #(.STORELEAF(STOREMODE),.CLOCKED(STOREMODE),.NQ(4), .P(2), .NB(20), .CD(CD), .MUT(MUT)) u_coll (.clk(clk), .rst_n(rst_n), .clr(clr), .ep(ep),
        .clk_store({20{clk}}),.clk_scan({32{clk}}),.clk_block_add({31{clk}}),.clk_heap_add({31{clk}}),
        .pk_v(rst_n ? lv[LD] : 8'd0), .pk(ld[LD]), .pk_cr(pk_cr), .ss_v(ss_v), .ss(ss), .flt(flt), .n_stale(n_stale));
    // credits back: held at random (jit = 0: next cycle), and the protocol monitor at the concentrator pins
    integer jit = 0, errors = 0, pend [0:7], outst [0:7], maxout = 0, starved = 0;
    integer s;
    always @(negedge clk) begin
        for (s = 0; s < 8; s = s + 1) begin
            if (pk_cr[s]) pend[s] = pend[s] + 1;
            ck_cr[s] = 1'b0;
            if (pend[s] > 0 && (jit == 0 || ($urandom % jit) == 0)) begin ck_cr[s] = 1'b1; pend[s] = pend[s] - 1; end
        end
    end
    always @(posedge clk) if (rst_n) begin
        for (s = 0; s < 8; s = s + 1) begin
            if (ck_v[s]) outst[s] = outst[s] + 1;
            if (ck_cr[s]) outst[s] = outst[s] - 1;
            if (outst[s] > maxout) maxout = outst[s];
            if (outst[s] > CD) begin
                if (errors < 8) $display("ERR slot %0d: %0d packets outstanding, %0d credits", s, outst[s], CD);
                errors = errors + 1;
            end
            if (outst[s] == CD) starved = starved + 1;
        end
        if (|c_ovf) begin if (errors < 8) $display("ERR concentrator overflow %b", c_ovf); errors = errors + 1; end
    end
    // lanes
    reg [41:0] lq [0:31][$]; integer gap = 0, start [0:31];
    always @(negedge clk) begin
        ch_v = 0;
        for (s = 0; s < 32; s = s + 1)
            if (lq[s].size() > 0 && cyc >= start[s] && (gap == 0 || ($urandom % gap) == 0)) begin
                ch_v[s] = 1'b1; ch[s*42 +: 42] = lq[s].pop_front();
            end
    end
    reg got = 0; reg [31:0] got_ss; integer t_ss;
    always @(posedge clk) if (ss_v) begin got <= 1'b1; got_ss <= ss; t_ss <= cyc; end
    task automatic fill(input integer r, input integer shuffle, input integer half);
        integer q, l, m, k, j; reg [9:0] tg; integer ord [0:19], x;
        begin
            for (q = 0; q < 4; q = q + 1) for (l = 0; l < 8; l = l + 1) begin
                for (m = 0; m < 20; m = m + 1) ord[m] = m;
                if (shuffle) for (m = 19; m > 0; m = m - 1) begin
                    j = $urandom % (m + 1); x = ord[m]; ord[m] = ord[j]; ord[j] = x;
                end
                for (k = 0; k < (half ? 10 : 20); k = k + 1) begin
                    tg = 10'(160 * q + l + 8 * ord[k]);
                    lq[8*q + l].push_back({tg, chm[640*r + integer'(tg)]});
                end
            end
        end
    endtask
    task automatic newrow();
        begin
            @(negedge clk); clr = 1; ep = ep + 2'd1; got = 0;
            for (s = 0; s < 32; s = s + 1) begin lq[s].delete(); start[s] = 0; end
            @(negedge clk); clr = 0; got = 0;
        end
    endtask
    integer r, t, t0, q2, npass = 0, nflt = 0, stale0;
    reg expf;
    initial begin
        for (s = 0; s < 8; s = s + 1) begin pend[s] = 0; outst[s] = 0; end
        for (s = 0; s < 32; s = s + 1) start[s] = 0;
        for (i = 0; i <= LD; i = i + 1) lv[i] = 0;
        repeat (4) @(posedge clk); rst_n = 1; repeat (4) @(posedge clk);
        for (r = 0; r < NROW && r < 12; r = r + 1) begin
            newrow(); t0 = cyc; expf = 0; jit = 0; gap = 0; stale0 = n_stale;
            case (r)
                0, 11: fill(r, 0, 0);
                1, 10: begin fill(r, 1, 0); gap = 3; for (s = 0; s < 32; s = s + 1) start[s] = cyc + 150 * ((r == 1) ? (s / 8) : (3 - s / 8)); end
                2, 9:  begin fill(r, 1, 0); jit = 8; gap = (r == 9) ? 2 : 0; end
                3:     begin fill(r, 1, 1); gap = 2; end
                4:     begin fill(r, 1, 0); end
                5:     begin fill(r, 0, 0); lq[0].insert(3, {lq[0][0][41:32], ~lq[0][0][31:0]}); expf = 1; end
                6, 8:  fill(r, 1, 0);
                7:     begin fill(r, 0, 0); lq[8][0][41:32] = lq[8][0][41:32] + 10'd160; expf = 1; end
                default: fill(r, 0, 0);
            endcase
            if (r == 3) begin
                repeat (14) @(posedge clk);          // abandon it with packets queued and in flight
                $display("row %0d ABORT after 14 cycles", r);
            end else begin
                t = 0; while (!(got || (expf && flt)) && t < 20000) begin @(posedge clk); t = t + 1; end
                if (expf) begin
                    repeat (200) @(posedge clk);
                    if (flt) begin nflt = nflt + 1; $display("row %0d: fault raised as required", r); end
                    else begin $display("ERR row %0d: a bad tag was accepted silently", r); errors = errors + 1; end
                end else begin
                    if (!got) begin $display("ERR row %0d: no sum after %0d cycles (flt %0d)", r, t, flt); errors = errors + 1; end
                    else if (got_ss !== ssm[r] || flt) begin
                        $display("ERR row %0d: ss %h expected %h flt %0d", r, got_ss, ssm[r], flt); errors = errors + 1;
                    end else begin
                        npass = npass + 1;
                        $display("row %0d: exact ss %h, %0d cycles, stale dropped %0d", r, got_ss, t_ss - t0, n_stale - stale0);
                    end
                    repeat (40) @(posedge clk);
                    if (ss_v) begin $display("ERR row %0d: a second sum", r); errors = errors + 1; end
                end
            end
        end
        // drain: every credit home
        newrow(); repeat (400) @(posedge clk);
        for (s = 0; s < 8; s = s + 1) if (outst[s] != 0 || pend[s] != 0 || u_coll.iw[s] != u_coll.ir[s]) begin
            $display("ERR slot %0d: %0d credits not home", s, outst[s]); errors = errors + 1;
        end
        if (n_stale == 0) begin $display("ERR the stale path was never exercised"); errors = errors + 1; end
        $display("summary: %0d rows exact, %0d faults raised, stale dropped %0d, max outstanding %0d of %0d credits, credit-starved slot-cycles %0d",
                 npass, nflt, n_stale, maxout, CD, starved);
        if (errors == 0 && npass == 9 && nflt == 2) $display("HGI_HC_COLL_B2 PASS"); else $display("HGI_HC_COLL_B2 FAIL errors=%0d", errors);
        $finish;
    end
endmodule
