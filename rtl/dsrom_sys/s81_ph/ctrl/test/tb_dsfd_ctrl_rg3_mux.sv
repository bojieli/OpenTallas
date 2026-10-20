`timescale 1ps/1ps
// S81-IDX3R (10-20, MU.BAL.SX.3): slot-mux / tag-demux gate of dsfd_ctrl_rg3 against the record dsfd_ctrl_rg2.
// Three controllers run the SAME svc_rs stimulus (a fixed per-cycle schedule of reads and writes on both PCs, tags in
// the svc ranges 00 / 01 / 10) against identical per-PC PHY models (k_rdy pattern = f(ckh cycle, PC); in-order
// responses after a fixed latency; write-done after the same latency):
//   A = dsfd_ctrl_rg2 (record),  B = dsfd_ctrl_rg3 with idle reader lanes,  C = dsfd_ctrl_rg3 with a reader window.
// Phases (cks cycles): 1 svc (random, both PCs) | gap | 2 reader window on C (sl = 1 on both lanes; the bench reader
// issues random reads within its RFD budget, counting pops; PHY slow phase) | gap | 3 svc again.
// Checks:
//   (1) A == B: rd[561:0] and the whole PHY face bit-identical EVERY cycle (reader logic transparent when idle);
//   (2) A vs C: every svc-visible rd bit identical every cycle: {fault, live}, and per PC {wd, rk, rv} and, when rv,
//       {beat, tag, data} (reader responses never leak into rd; reader rk is filtered by the owner FIFO);
//   (3) C reader lanes: every reader request returns exactly its len beats in order per PC with the PHY data, tag10 and
//       beat; pops == requests; no lane word outside the window; C status fault 0.
//   +SLOTHIT=1: one svc read inside C's reader window (schedule violation, applied to A and B too): C must raise its
//       status fault (fail-closed) and its reader traffic stays complete -> PASS; (2) is skipped for this case.
// MUT = dsfd_ctrl_rg3 MUT (1 demux on tag[16], 2 rk unfiltered, 3 reader moves ignore the PC budget, 4 slice priority
// without fault): each must print TB_CTRL3 FAIL.  Prints TB_CTRL3 PASS / FAIL and a TB_CTRL3_STATS line.
module tb_dsfd_ctrl_rg3_mux;
    parameter integer MUT = 0;
    parameter integer CKH_PS = 900;
    parameter integer RFD = 24;
    integer SEED = 1, SLOTHIT = 0, NSV = 400, NRQ = 600, LAT = 24;
    initial begin
        void'($value$plusargs("SEED=%d", SEED)); void'($value$plusargs("SLOTHIT=%d", SLOTHIT));
        void'($value$plusargs("NSV=%d", NSV)); void'($value$plusargs("NRQ=%d", NRQ)); void'($value$plusargs("LAT=%d", LAT));
    end
    reg ck = 0, ckh = 0, rst = 0;
    always begin #417 ck = 1; #416 ck = 0; end
    always #(CKH_PS / 2) ckh = ~ckh;
    longint cyc = 0, hcyc = 0;
    always @(posedge ck) cyc <= cyc + 1;
    always @(posedge ckh) hcyc <= hcyc + 1;
    function automatic [31:0] mix(input longint a);
        longint z; z = a * 64'h9E3779B97F4A7C15 + 64'(SEED) * 64'hBF58476D1CE4E5B9;
        z = (z ^ (z >> 30)) * 64'hBF58476D1CE4E5B9; z = (z ^ (z >> 27)) * 64'h94D049BB133111EB; z = z ^ (z >> 31);
        mix = z[31:0];
    endfunction
    // phases (cks cycles from reset release)
    localparam longint P1A = 100, P1B = 2600, P2A = 3400, P2B = 9400, P3A = 10200, P3B = 12700, PEND = 14500;
    longint t0 = 0;
    reg slow = 0;                                  // PHY slow phase (reader window): k_rdy 1 in 8
    // ------------------------------------------------------------------ DUTs
    reg  [681:0] rq = 0;                           // svc stimulus (A, B, C)
    reg  [91:0]  rrq_c = 0;                        // reader lanes into C
    wire [561:0] rd_a, rd_b, rd_c;
    wire [543:0] rrd_b, rrd_c;
    wire [1:0] kv [0:2], krdy [0:2], kwe [0:2], kwd [0:2], krv [0:2], krrdy [0:2];
    wire [59:0] kad [0:2]; wire [7:0] kln [0:2], krb [0:2]; wire [33:0] ktg [0:2], krt [0:2];
    wire [511:0] kwdat [0:2], krd [0:2]; wire [63:0] kws [0:2];
    dsfd_ctrl_rg2 #(.DQ(8)) u_a (.clk(ck), .ckh(ckh), .rst_n(rst), .rq(rq), .rd(rd_a), .ck_o(),
        .k_v(kv[0]), .k_rdy(krdy[0]), .k_addr(kad[0]), .k_len(kln[0]), .k_tag(ktg[0]), .k_we(kwe[0]), .k_wdata(kwdat[0]),
        .k_wstrb(kws[0]), .k_wr_done(kwd[0]), .kr_v(krv[0]), .kr_rdy(krrdy[0]), .kr_tag(krt[0]), .kr_beat(krb[0]), .kr_data(krd[0]));
    dsfd_ctrl_rg3 #(.DQ(8), .RFD(RFD), .MUT(MUT)) u_b (.clk(ck), .ckh(ckh), .rst_n(rst), .rq(rq), .rd(rd_b), .ck_o(),
        .rrq(92'd0), .rrd(rrd_b),
        .k_v(kv[1]), .k_rdy(krdy[1]), .k_addr(kad[1]), .k_len(kln[1]), .k_tag(ktg[1]), .k_we(kwe[1]), .k_wdata(kwdat[1]),
        .k_wstrb(kws[1]), .k_wr_done(kwd[1]), .kr_v(krv[1]), .kr_rdy(krrdy[1]), .kr_tag(krt[1]), .kr_beat(krb[1]), .kr_data(krd[1]));
    dsfd_ctrl_rg3 #(.DQ(8), .RFD(RFD), .MUT(MUT)) u_c (.clk(ck), .ckh(ckh), .rst_n(rst), .rq(rq), .rd(rd_c), .ck_o(),
        .rrq(rrq_c), .rrd(rrd_c),
        .k_v(kv[2]), .k_rdy(krdy[2]), .k_addr(kad[2]), .k_len(kln[2]), .k_tag(ktg[2]), .k_we(kwe[2]), .k_wdata(kwdat[2]),
        .k_wstrb(kws[2]), .k_wr_done(kwd[2]), .kr_v(krv[2]), .kr_rdy(krrdy[2]), .kr_tag(krt[2]), .kr_beat(krb[2]), .kr_data(krd[2]));
    function automatic [255:0] pdat(input [29:0] a, input integer pc);
        pdat = {8{mix(64'h5100_0000 + 64'(a) * 4 + pc)}};
    endfunction
    typedef struct packed { longint rdy_t; logic [29:0] a; logic [3:0] ln; logic [16:0] tg; logic we; } ent_t;
    genvar gi, gp;
    generate for (gi = 0; gi < 3; gi = gi + 1) begin : g_phy
        for (gp = 0; gp < 2; gp = gp + 1) begin : g_pc
            ent_t q[$];
            reg [3:0] bt = 0; reg rv = 0; reg [16:0] rtg = 0; reg [3:0] rbt = 0; reg [255:0] rdat = 0; reg wdn = 0;
            assign krdy[gi][gp] = rst && (slow ? (mix(64'h5200_0000 + hcyc * 2 + gp) % 8 == 0) : (mix(64'h5200_0000 + hcyc * 2 + gp) % 4 != 0));
            assign krv[gi][gp] = rv; assign krt[gi][17 * gp +: 17] = rtg; assign krb[gi][4 * gp +: 4] = rbt;
            assign krd[gi][256 * gp +: 256] = rdat; assign kwd[gi][gp] = wdn;
            always @(posedge ckh) begin
                wdn <= 1'b0;
                if (kv[gi][gp] && krdy[gi][gp])
                    q.push_back('{hcyc + LAT, kad[gi][30 * gp +: 30], kln[gi][4 * gp +: 4], ktg[gi][17 * gp +: 17], kwe[gi][gp]});
                if (rv && krrdy[gi][gp]) rv <= 1'b0;
                if ((!rv || krrdy[gi][gp]) && q.size() > 0 && q[0].rdy_t <= hcyc) begin
                    if (q[0].we) begin wdn <= 1'b1; void'(q.pop_front()); bt <= 0; end
                    else begin
                        rv <= 1'b1; rtg <= q[0].tg; rbt <= bt; rdat <= pdat(q[0].a + 30'(bt), gp);
                        if (bt + 4'd1 == q[0].ln) begin bt <= 0; void'(q.pop_front()); end else bt <= bt + 4'd1;
                    end
                end
            end
        end
    end endgenerate
    // ------------------------------------------------------------------ checks
    integer errs = 0, e_ab = 0, e_ac = 0, e_rd = 0, n_rq = 0, n_beats = 0, n_pop = 0, n_svrq = 0, own [0:1];
    initial begin own[0] = 0; own[1] = 0; end
    typedef struct packed { logic [29:0] a; logic [3:0] ln; logic [9:0] t; } rq_t;
    rq_t rqq [0:1][$];
    reg [3:0] rbeat [0:1];
    initial begin rbeat[0] = 0; rbeat[1] = 0; end
    always @(posedge ck) if (rst) begin : g_chk
        integer p; reg [279:0] wa, wc; reg [271:0] l;
        // (1) A == B, whole face
        if (rd_a !== rd_b || kv[0] !== kv[1] || kad[0] !== kad[1] || kln[0] !== kln[1] || ktg[0] !== ktg[1] || kwe[0] !== kwe[1] ||
            kwdat[0] !== kwdat[1] || kws[0] !== kws[1] || krrdy[0] !== krrdy[1] || rrd_b !== 544'd0) begin
            e_ab = e_ab + 1; if (e_ab <= 4) $display("TB_CTRL3 A!=B cyc %0d", cyc - t0);
        end
        // (2) A vs C, svc-visible
        if (SLOTHIT == 0) begin
            if (rd_a[561:560] !== rd_c[561:560]) begin e_ac = e_ac + 1; if (e_ac <= 4) $display("TB_CTRL3 A!=C status cyc %0d %b %b", cyc - t0, rd_a[561:560], rd_c[561:560]); end
            for (p = 0; p < 2; p = p + 1) begin
                wa = rd_a[280 * p +: 280]; wc = rd_c[280 * p +: 280];
                if (wa[279:277] !== wc[279:277] || (wa[277] && wa[276:0] !== wc[276:0])) begin
                    e_ac = e_ac + 1; if (e_ac <= 4) $display("TB_CTRL3 A!=C pc %0d cyc %0d {wd,rk,rv} %b %b tag %h %h", p, cyc - t0, wa[279:277], wc[279:277], wa[272:256], wc[272:256]);
                end
            end
        end
        // (3) C reader lanes
        for (p = 0; p < 2; p = p + 1) begin
            l = rrd_c[272 * p +: 272];
            if (l[1]) begin n_pop = n_pop + 1; own[p] = own[p] - 1; end
            if (l[0]) begin
                n_beats = n_beats + 1;
                if (rqq[p].size() == 0) begin e_rd = e_rd + 1; if (e_rd <= 4) $display("TB_CTRL3 reader beat with no request pc %0d", p); end
                else begin
                    if (l[15:6] !== rqq[p][0].t || l[5:2] !== rbeat[p] || l[271:16] !== pdat(rqq[p][0].a + 30'(rbeat[p]), p)) begin
                        e_rd = e_rd + 1; if (e_rd <= 4) $display("TB_CTRL3 reader beat mismatch pc %0d tag %h/%h beat %0d/%0d", p, l[15:6], rqq[p][0].t, l[5:2], rbeat[p]);
                    end
                    if (rbeat[p] + 4'd1 == rqq[p][0].ln) begin rbeat[p] = 0; void'(rqq[p].pop_front()); end else rbeat[p] = rbeat[p] + 4'd1;
                end
            end
        end
    end
    // ------------------------------------------------------------------ stimulus
    function automatic [340:0] svc_word(input integer k, input integer p);
        reg [31:0] m; reg [1:0] tr; reg we; reg [3:0] ln;
        m = mix(64'h5300_0000 + k * 2 + p); tr = m[1:0] == 2'b11 ? 2'b10 : m[1:0];
        we = m[4:2] == 3'd0; ln = we ? 4'd1 : 4'(1 + m[6:5]);
        svc_word = {we ? {8{mix(64'h5400_0000 + k * 2 + p)}} : 256'd0, we ? 32'hFFFF_FFFF : 32'd0,
                    {tr, 15'(k)}, ln, 30'(1000 + 8 * k + p), we, 1'b1};
    endfunction
    initial begin : g_run
        integer k, p, gap; longint t; reg [31:0] m;
        repeat (20) @(posedge ck); rst = 1; t0 = cyc;
        // phase 1: svc
        while (cyc - t0 < P1A) @(negedge ck);
        k = 0;
        while (cyc - t0 < P1B && k < NSV) begin
            @(negedge ck); rq = 0;
            for (p = 0; p < 2; p = p + 1) if (mix(64'h5500_0000 + (cyc - t0) * 2 + p) % 6 == 0) begin
                rq[341 * p +: 341] = svc_word(k, p); n_svrq = n_svrq + 1; k = k + 1; end
        end
        @(negedge ck); rq = 0;
        // phase 2: reader window on C
        while (cyc - t0 < P2A) @(negedge ck);
        slow = 1;
        rrq_c[1] = 1; rrq_c[47] = 1;
        k = 0;
        while (cyc - t0 < P2B - 600) begin
            @(negedge ck);
            rrq_c[0] = 0; rrq_c[46] = 0;
            if (SLOTHIT != 0 && cyc - t0 == P2A + 300) begin rq[340:0] = svc_word(9999, 0); n_svrq = n_svrq + 1; end
            else rq = 0;
            for (p = 0; p < 2; p = p + 1) if (k < NRQ && own[p] < RFD && mix(64'h5600_0000 + (cyc - t0) * 2 + p) % 3 == 0) begin : g_i
                rq_t w;
                m = mix(64'h5700_0000 + k);
                w.a = 30'(50000 + 16 * k + p); w.ln = 4'(1 + m[1:0]); w.t = 10'(k);
                rrq_c[46 * p +: 46] = {w.t, w.ln, w.a, 1'b1, 1'b1};
                rqq[p].push_back(w); own[p] = own[p] + 1; n_rq = n_rq + 1; k = k + 1;
            end
        end
        @(negedge ck); rrq_c[0] = 0; rrq_c[46] = 0; rq = 0;
        while (cyc - t0 < P2B) @(negedge ck);
        rrq_c = 0; slow = 0;
        // phase 3: svc again
        while (cyc - t0 < P3A) @(negedge ck);
        k = 10000;
        while (cyc - t0 < P3B && k < 10000 + NSV) begin
            @(negedge ck); rq = 0;
            for (p = 0; p < 2; p = p + 1) if (mix(64'h5800_0000 + (cyc - t0) * 2 + p) % 6 == 0) begin
                rq[341 * p +: 341] = svc_word(k, p); n_svrq = n_svrq + 1; k = k + 1; end
        end
        @(negedge ck); rq = 0;
        while (cyc - t0 < PEND) @(negedge ck);
        if (rqq[0].size() != 0 || rqq[1].size() != 0) begin e_rd = e_rd + 1; $display("TB_CTRL3 reader requests unanswered %0d %0d", rqq[0].size(), rqq[1].size()); end
        if (n_pop != n_rq) begin e_rd = e_rd + 1; $display("TB_CTRL3 pops %0d != requests %0d", n_pop, n_rq); end
        if (SLOTHIT != 0) begin
            if (rd_c[561] !== 1'b1) begin e_rd = e_rd + 1; $display("TB_CTRL3 slot hit NOT flagged (fail-open)"); end
        end else if (rd_c[561] !== 1'b0 || rd_a[561] !== 1'b0) begin e_rd = e_rd + 1; $display("TB_CTRL3 status fault a %b c %b", rd_a[561], rd_c[561]); end
        errs = e_ab + e_ac + e_rd;
        $display("TB_CTRL3_STATS mut %0d seed %0d slothit %0d svc_rq %0d rd_rq %0d rd_beats %0d pops %0d e_ab %0d e_ac %0d e_rd %0d",
                 MUT, SEED, SLOTHIT, n_svrq, n_rq, n_beats, n_pop, e_ab, e_ac, e_rd);
        if (errs != 0 || n_rq == 0 || n_svrq == 0) $display("TB_CTRL3 FAIL"); else $display("TB_CTRL3 PASS");
        $finish;
    end
endmodule
