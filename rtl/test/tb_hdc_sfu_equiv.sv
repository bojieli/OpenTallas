`timescale 1ns/1ps
// Input-sweep equivalence of the decode core's special-function pipelines
// against a reference build of the previous ones (the five-stage-pipe SFUs,
// module names suffixed _ref, the sources at the commit that preceded the
// low-latency units): every input word in [+LO, +HI) enters both, one per
// cycle (every STRIDE-th word, default 1: all of them), and the k-th result of
// each function must match bit for bit.
//
// FUNC 0 exp, 1 reciprocal, 2 rsqrt, 3 sigmoid denominator path as the stream
// unit composes it: reciprocal(exp(x) + 1).
//
// Faults are compared per block of BLK inputs, each followed by a drain longer
// than the deepest pipeline: the block faults in one design exactly when it
// faults in the other.
module tb_hdc_sfu_equiv (input wire clk);
    localparam integer BLK = 4096, GAP = 160;
    reg rst_n = 1'b0;
    reg v = 1'b0;
    reg [31:0] x = 0;
    integer func = 0;
    reg [63:0] lo = 0, hi = 64'h1_0000_0000, cur, stride = 1, expect_n;

    // reference
    wire [31:0] re_y, rr_y, rs_y, re1;
    wire re_vo, rr_vo, rs_vo, re_f, rr_f, rs_f, re1_f;
    wire [5:0] rve1;
    ot_hdc_exp_ref   r_exp (.clk(clk), .rst_n(rst_n), .v(v && (func == 0 || func == 3)), .x(x), .y(re_y), .vo(re_vo), .fault(re_f));
    ot_hdc_fadd      r_e1  (clk, rst_n, re_vo && func == 3, re_y, 32'h3F800000, re1, re1_f);
    ot_hdc_vline_ref #(.D(5)) r_ve1 (.clk(clk), .rst_n(rst_n), .v(re_vo && func == 3), .vd(rve1));
    ot_hdc_recip_ref r_rcp (.clk(clk), .rst_n(rst_n), .v(func == 3 ? rve1[5] : (v && func == 1)), .x(func == 3 ? re1 : x),
                            .y(rr_y), .vo(rr_vo), .fault(rr_f));
    ot_hdc_rsqrt_ref r_rsq (.clk(clk), .rst_n(rst_n), .v(v && func == 2), .x(x), .y(rs_y), .vo(rs_vo), .fault(rs_f));
    // new
    wire [31:0] ne_y, nr_y, ns_y, ne1;
    wire ne_vo, nr_vo, ns_vo, ne_f, nr_f, ns_f, ne1_f;
    wire [3:0] nve1;
    ot_hdc_exp_q n_exp (.clk(clk), .rst_n(rst_n), .v(v && (func == 0 || func == 3)), .x(x), .y(ne_y), .vo(ne_vo), .fault(ne_f));
    ot_hdc_qadd  n_e1  (clk, rst_n, ne_vo && func == 3, ne_y, 32'h3F800000, ne1, ne1_f);
    ot_hdc_vline #(.D(3)) n_ve1 (.clk(clk), .rst_n(rst_n), .v(ne_vo && func == 3), .vd(nve1));
    ot_hdc_recip_q n_rcp (.clk(clk), .rst_n(rst_n), .v(func == 3 ? nve1[3] : (v && func == 1)), .x(func == 3 ? ne1 : x),
                        .y(nr_y), .vo(nr_vo), .fault(nr_f));
    ot_hdc_rsqrt_q n_rsq (.clk(clk), .rst_n(rst_n), .v(v && func == 2), .x(x), .y(ns_y), .vo(ns_vo), .fault(ns_f));

    wire        r_vo = func == 0 ? re_vo : func == 2 ? rs_vo : rr_vo;
    wire [31:0] r_y  = func == 0 ? re_y  : func == 2 ? rs_y  : rr_y;
    wire        n_vo = func == 0 ? ne_vo : func == 2 ? ns_vo : nr_vo;
    wire [31:0] n_y  = func == 0 ? ne_y  : func == 2 ? ns_y  : nr_y;
    wire r_f = re_f | re1_f | rr_f | rs_f;
    wire n_f = ne_f | ne1_f | nr_f | ns_f;

    // the new results arrive first; hold them until the reference catches up
    localparam integer QN = 256;
    reg [31:0] q [0:QN-1];
    reg [31:0] xin [0:QN-1];
    integer qw = 0, qr = 0, xw = 0;
    reg [63:0] checked = 0, bad = 0, blocks = 0, fbad = 0, fblocks = 0;
    reg rfb = 0, nfb = 0;
    integer phase_cnt = 0;
    reg in_gap = 0, done = 0;
    initial begin
        if (!$value$plusargs("FUNC=%d", func)) func = 0;
        if (!$value$plusargs("LO=%h", lo)) lo = 0;
        if (!$value$plusargs("HI=%h", hi)) hi = 64'h1_0000_0000;
        if (!$value$plusargs("STRIDE=%d", stride)) stride = 1;
        cur = lo;
        expect_n = (hi - lo + stride - 1) / stride;
    end
    integer cyc = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        if (rst_n) begin
            // stimulus: BLK inputs, then GAP idle cycles
            if (!in_gap && cur < hi) begin
                v <= 1'b1; x <= cur[31:0];
                xin[xw % QN] = cur[31:0]; xw = xw + 1;
                cur = cur + stride;
                phase_cnt = phase_cnt + 1;
                if (phase_cnt == BLK || cur >= hi) begin in_gap = 1; phase_cnt = 0; end
            end else begin
                v <= 1'b0;
                if (in_gap) begin
                    phase_cnt = phase_cnt + 1;
                    if (phase_cnt == GAP) begin
                        in_gap = 0; phase_cnt = 0;
                        blocks = blocks + 1;
                        if (rfb !== nfb) begin
                            if (fbad < 10) $display("FAULT MISMATCH block ending %h ref=%0d new=%0d", cur[31:0], rfb, nfb);
                            fbad = fbad + 1;
                        end
                        if (rfb) fblocks = fblocks + 1;
                        rfb = 0; nfb = 0;
                        if (cur >= hi) done = 1;
                    end
                end
            end
            if (r_f) rfb = 1;
            if (n_f) nfb = 1;
            if (n_vo) begin q[qw % QN] = n_y; qw = qw + 1; end
            if (r_vo) begin
                if (qr >= qw) begin
                    if (bad < 10) $display("ORDER: reference result with no new result");
                    bad = bad + 1;
                end else if (q[qr % QN] !== r_y) begin
                    if (bad < 10) $display("MISMATCH func=%0d x=%h ref=%h new=%h", func, xin[qr % QN], r_y, q[qr % QN]);
                    bad = bad + 1;
                end
                qr = qr + 1;
                checked = checked + 1;
            end
            if (done) begin
                $display("SFUEQ func=%0d lo=%h hi=%h checked=%0d mismatches=%0d blocks=%0d fault_blocks=%0d fault_mismatches=%0d",
                         func, lo, hi, checked, bad, blocks, fblocks, fbad);
                if (bad == 0 && fbad == 0 && checked == expect_n && qw == qr) $display("PASS"); else $display("FAIL");
                if (!(bad == 0 && fbad == 0 && checked == expect_n && qw == qr)) $fatal(1, "EQUIVALENCE_TERMINAL_FAIL");
        $finish;
            end
        end
    end
endmodule
