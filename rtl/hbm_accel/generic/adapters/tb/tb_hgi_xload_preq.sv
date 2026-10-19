`timescale 1ns/1ps
// HBM-COLLQ/X (10-18): x-load PRE-QUANTISED mode (fmt 3, ot_hgi_sm_xload_static_cl2p) vs the FP8 block-dot fmt 1 of the
// unchanged cl2 cluster on the same vectors.  A = cl2 on the FP32 image (its quantiser tiles ot_hbm_xp_aq_tree13 quantise),
// B = cl2p on the PRE-QUANTISED VM FORMAT v1 image made by hdc_golden_v41.quant_fp8 (tools/hgi_sim/xload_preq_vectors_1018.py).
// Both get their command on the same edge; every xw beat of B (en, last, addr, grp, 2048-b data) and its x_done must equal
// A's exactly D = P S Es + 3 edges later; no x_fault, no lane fault.  +DIR=<vector dir>.
// +SAME=1: regression, B runs fmt 1 on the FP32 image (D = 0: cl2p fmt 1 cycle-identical to cl2).
// MUT 7 (exponent byte of the next pair) and 8 (bypass bias 126) must FAIL.
module tb_hgi_xload_preq;
    parameter integer MUT = 0;
    localparam integer RD_LAT = 6;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0; integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    integer same = 0; reg [1:0] fb_fmt;
    reg xv = 0; reg [39:0] xba, xbb; reg [20:0] xn; reg [3:0] xp; reg [31:0] xsa, xsb; reg [6:0] xxb;
    wire bsa, dna, fa, ena, lsa, bsb, dnb, fb, enb, lsb; wire [6:0] ada, gra, adb, grb; wire [2047:0] da, db;
    wire [8*17-1:0] rqa, rqb; reg [8*257-1:0] rra, rrb;
    ot_hgi_sm_xload_static_cl2 #(.RD_LAT(RD_LAT)) ua (.clk(clk), .clk_eg(clk), .clk_bf({4{clk}}), .clk_qlo(clk), .clk_qhi(clk), .clk_bd(clk),
        .rst_n(rst_n), .x_v(xv), .x_base(xba), .x_n(xn), .x_p(xp), .x_stride(xsa), .x_space(2'd1), .x_fmt(2'd1), .x_xb(xxb),
        .x_busy(bsa), .x_done(dna), .x_fault(fa), .xw_en(ena), .xw_last(lsa), .xw_addr(ada), .xw_grp(gra), .xw_data(da), .rq(rqa), .rr(rra));
    ot_hgi_sm_xload_static_cl2p #(.RD_LAT(RD_LAT), .MUT(MUT)) ub (.clk(clk), .clk_eg(clk), .clk_bf({4{clk}}), .clk_qlo(clk), .clk_qhi(clk),
        .clk_plo(clk), .clk_phi(clk), .clk_bd(clk),
        .rst_n(rst_n), .x_v(xv), .x_base(xbb), .x_n(xn), .x_p(xp), .x_stride(xsb), .x_space(2'd1), .x_fmt(fb_fmt), .x_xb(xxb),
        .x_busy(bsb), .x_done(dnb), .x_fault(fb), .xw_en(enb), .xw_last(lsb), .xw_addr(adb), .xw_grp(grb), .xw_data(db), .rq(rqb), .rr(rrb));
    // fixed-latency static bank model (sector S on lane S[2:0], response RD_LAT edges later), one per DUT
    reg [31:0] mem [0:65535];
    reg [8*257-1:0] pa [0:RD_LAT-1]; reg [8*257-1:0] pb [0:RD_LAT-1];
    integer lanefault = 0, rd_a = 0, rd_b = 0;
    always @(posedge clk) begin : vm
        reg [8*257-1:0] na, nb; reg [14:0] s;
        na = '0; nb = '0;
        for (integer b = 0; b < 8; b = b + 1) begin
            if (rqa[b*17 + 16]) begin s = rqa[b*17 +: 15]; if (s[2:0] != b[2:0] || rqa[b*17 + 15]) lanefault = lanefault + 1;
                na[b*257 + 256] = 1'b1; rd_a = rd_a + 1; for (integer w = 0; w < 8; w = w + 1) na[b*257 + 32*w +: 32] = mem[{1'b0, s[11:0], 3'(w)}]; end
            if (rqb[b*17 + 16]) begin s = rqb[b*17 +: 15]; if (s[2:0] != b[2:0] || rqb[b*17 + 15]) lanefault = lanefault + 1;
                nb[b*257 + 256] = 1'b1; rd_b = rd_b + 1; for (integer w = 0; w < 8; w = w + 1) nb[b*257 + 32*w +: 32] = mem[{(same == 0), s[11:0], 3'(w)}]; end
        end
        pa[0] <= na; pb[0] <= nb;
        for (integer d = 1; d < RD_LAT; d = d + 1) begin pa[d] <= pa[d-1]; pb[d] <= pb[d-1]; end
    end
    always @* begin rra = pa[RD_LAT-1]; rrb = pb[RD_LAT-1]; end
    // beat logs
    integer na_b, nb_b, done_a, done_b; integer ca [0:8191]; integer cb [0:8191];
    reg [2047:0] dla [0:8191]; reg [2047:0] dlb [0:8191]; reg [15:0] ma [0:8191]; reg [15:0] mb2 [0:8191];
    always @(posedge clk) begin
        if (ena) begin if (na_b < 8192) begin ca[na_b] = cyc; dla[na_b] = da; ma[na_b] = {lsa, ada, gra[6:0]} ; end na_b = na_b + 1; end
        if (enb) begin if (nb_b < 8192) begin cb[nb_b] = cyc; dlb[nb_b] = db; mb2[nb_b] = {lsb, adb, grb[6:0]}; end nb_b = nb_b + 1; end
        if (dna) done_a = cyc; if (dnb) done_b = cyc;
    end
    string dir, fn; integer fd, ncase, K, P, Bs, ss, bA, sA, bB, sB, xb, kind, errors = 0, S, Es, D, bad, t;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if ($value$plusargs("SAME=%d", same)) begin end
        fb_fmt = same ? 2'd1 : 2'd3;
        fd = $fopen({dir, "/cases.txt"}, "r"); if (fd == 0) $fatal(1, "no cases.txt");
        void'($fscanf(fd, "%d", ncase));
        repeat (3) @(posedge clk); rst_n = 1; repeat (8) @(posedge clk);
        for (integer c = 0; c < ncase; c = c + 1) begin
            void'($fscanf(fd, "%d %d %d %d %d %d %d %d %d %d", K, P, Bs, ss, bA, sA, bB, sB, xb, kind));
            fn = $sformatf("%s/case%0d.memh", dir, c); $readmemh(fn, mem);
            S = ((K / 32) + Bs - 1) / Bs; Es = (Bs + 31) / 32; D = same ? 0 : P * S * Es + 3;
            na_b = 0; nb_b = 0; done_a = -1; done_b = -1;
            @(negedge clk); xv = 1; xn = 21'(K); xp = 4'(P); xxb = 7'(xb);
            xba = 40'(bA); xsa = 32'(sA); xbb = same ? 40'(bA) : {12'(ss), 10'(Bs), 18'(bB)}; xsb = same ? 32'(sA) : 32'(sB);
            @(negedge clk); xv = 0;
            t = 0; while ((done_a < 0 || done_b < 0) && t < 200000) begin @(posedge clk); t = t + 1; end
            repeat (4) @(posedge clk);
            bad = 0;
            if (done_a < 0 || done_b < 0 || na_b == 0 || na_b != nb_b || done_b - done_a != D) bad = bad + 1;
            for (integer i = 0; i < na_b && i < nb_b && i < 8192; i = i + 1)
                if (cb[i] - ca[i] != D || mb2[i] !== ma[i] || dlb[i] !== dla[i]) begin
                    if (bad < 4) $display("XLOAD_PREQ case %0d beat %0d: A edge %0d B edge %0d (D %0d) meta %h/%h data %s", c, i, ca[i], cb[i], D,
                                          ma[i], mb2[i], (dlb[i] === dla[i]) ? "eq" : "DIFF");
                    bad = bad + 1;
                end
            $display("XLOAD_PREQ case %0d K %0d P %0d Bs %0d S %0d Es %0d kind %0d: beats %0d/%0d done +%0d (D %0d) mismatches %0d",
                     c, K, P, Bs, S, Es, kind, na_b, nb_b, done_b - done_a, D, bad);
            if (bad) errors = errors + 1;
            $fflush;
        end
        if (fa || fb || lanefault) begin $display("XLOAD_PREQ fault A %b B %b lanefault %0d", fa, fb, lanefault); errors = errors + 1; end
        $display("XLOAD_PREQ reads A %0d B %0d (bank-lane reads)", rd_a, rd_b);
        if (errors == 0) $display("XLOAD_PREQ PASS cases=%0d", ncase); else $display("XLOAD_PREQ FAIL %0d", errors);
        $finish;
    end
endmodule
