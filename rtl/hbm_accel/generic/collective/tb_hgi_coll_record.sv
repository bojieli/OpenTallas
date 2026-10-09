`timescale 1ns/1ps
// ot_hgi_coll_record bench (hgi-takeover): normative records -> endpoint / formatter control and retirement.
module tb_hgi_coll_record;
    parameter integer MUT_PF = 0, MUT_DONE = 0;
    reg clk = 0; always #0.4166665 clk = ~clk;
    reg rst_n = 0;
    reg [7:0] g, die;
    reg rec_v = 0; wire rec_rdy;
    reg [127:0] hdr; reg [255:0] a, o, i; reg [20:0] na, no, ni;
    wire rec_done, rec_fault;
    wire [7:0] ep_rank, ep_mg; wire ep_mall, ep_byp; wire [3:0] ep_gsz; wire [15:0] ep_pf; wire ep_go; wire ep_done_ready;
    wire [39:0] ep_ab, ep_ob;
    reg ep_ready = 1, ep_done = 0, ep_fault = 0;
    wire rf_sv; reg rf_sr = 1; wire [7:0] rf_g, rf_b, rf_d; wire [20:0] rf_rows; wire [15:0] rf_words; wire [31:0] rf_ctx;
    reg rf_dv = 0, rf_f = 0; wire rf_dr;
    ot_hgi_coll_record #(.MUT_PF(MUT_PF), .MUT_DONE(MUT_DONE)) dut (
        .clk(clk), .rst_n(rst_n), .cfg_coll_group_size(g), .cfg_die_id(die),
        .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(hdr), .rec_a(a), .rec_o(o), .rec_i(i),
        .rec_n_a(na), .rec_n_o(no), .rec_n_i(ni), .rec_done(rec_done), .rec_fault(rec_fault),
        .ep_rank(ep_rank), .ep_mcast_group_size(ep_mg), .ep_mcast_all(ep_mall), .ep_gsz(ep_gsz), .ep_byp(ep_byp), .ep_pf(ep_pf),
        .ep_go(ep_go), .ep_start_ready(ep_ready), .ep_done_valid(ep_done), .ep_done_ready(ep_done_ready),
        .ep_fault(ep_fault), .ep_a_base(ep_ab), .ep_o_base(ep_ob),
        .rf_start_v(rf_sv), .rf_start_r(rf_sr), .rf_group_size(rf_g), .rf_owner_block(rf_b), .rf_destinations(rf_d),
        .rf_row_count(rf_rows), .rf_row_words(rf_words), .rf_context_rows(rf_ctx), .rf_done_v(rf_dv),
        .rf_done_r(rf_dr), .rf_fault(rf_f));
    integer cases = 0, gos = 0, rfstarts = 0, t, lat;
    always @(posedge clk) if (ep_go) gos <= gos + 1;
    // descriptor: space VM(1), fmt, base, n, m
    function [255:0] md(input [2:0] fmt, input [39:0] base, input [19:0] n, input [19:0] m, input [5:0] nsel);
        begin md = 256'd0; md[1:0] = 2'd1; md[4:2] = fmt; md[47:8] = base; md[67:48] = n; md[87:68] = m; md[206:201] = nsel; end
    endfunction
    task reset; begin rst_n = 0; repeat (3) @(negedge clk); rst_n = 1; repeat (2) @(negedge clk); end endtask
    task send(input [5:0] op, input [24:0] param, input [31:0] imm_a, input [31:0] imm_b, input [6:0] opnd);
        begin
            hdr = 0; hdr[127:124] = 4'd6; hdr[123:118] = op; hdr[99:93] = opnd; hdr[88:64] = param;
            hdr[63:32] = imm_a; hdr[31:0] = imm_b;
            @(negedge clk); while (!rec_rdy) @(negedge clk);
            rec_v = 1; @(negedge clk); rec_v = 0; hdr = ~hdr; a = ~a;   // station must have captured
        end
    endtask
    task expect_fault; begin
        t = 0; while (!rec_fault && !rec_done && t < 200) begin @(negedge clk); t = t + 1; end
        if (!rec_fault) $fatal(1, "FATAL: expected fault");
        reset; cases = cases + 1;
    end endtask
    // endpoint collective with completion latency `lat`
    task ep_case(input [7:0] gs, input [7:0] d, input [5:0] op, input [7:0] s, input [19:0] n);
        integer g0;
        begin
            g = gs; die = d; a = md(3'd0, 40'h12345, n, 20'd1, 6'd0); o = md(3'd0, 40'h6789A, n, 20'd1, 6'd0);
            i = 0; na = n; no = n; ni = 0; reset; g0 = gos;
            send(op, s, 0, 0, 7'b0010001);
            t = 0; while (gos == g0 && t < 100) begin @(negedge clk); t = t + 1; end
            if (gos != g0 + 1) $fatal(1, "FATAL: no go op=%0d g=%0d", op, gs);
            // endpoint rank = die mod 96 (TU fabric position); GROUP_REDUCE_MCAST: gsz = log2 s, outer group G;
            // ALL_GATHER: bypass, gsz = log2 G (G = 96: the outer group, mcast_all); pf = A row bits / 512
            if (ep_rank != d % 96 || ep_mg != gs || ep_mall != (op == 4 || (op == 1 && gs == 96)) || ep_byp != (op == 1) ||
                ep_gsz != ((op == 4) ? ((s == 2) ? 4'd1 : (s == 4) ? 4'd2 : 4'd3) :
                           (gs == 96) ? ((op == 1) ? 4'd3 : 4'hF) : (gs == 8) ? 4'd3 : (gs == 4) ? 4'd2 : (gs == 2) ? 4'd1 : 4'd0) ||
                ep_pf != n / 16 || ep_ab != 40'h12345 || ep_ob != 40'h6789A)
                $fatal(1, "FATAL: endpoint control mismatch op=%0d g=%0d die=%0d pf=%0d", op, gs, d, ep_pf);
            repeat (lat) begin @(negedge clk); if (rec_done) $fatal(1, "FATAL: retired before endpoint completion"); end
            ep_done = 1; t = 0; while (!ep_done_ready && t < 20) begin @(negedge clk); t = t + 1; end
            if (!rec_done || rec_fault) $fatal(1, "FATAL: legal collective did not retire with the endpoint completion");
            @(negedge clk); ep_done = 0;
            cases = cases + 1;
        end
    endtask
    integer gi, di, k;
    reg [7:0] gl [0:4];
    initial begin
        gl[0] = 1; gl[1] = 2; gl[2] = 4; gl[3] = 8; gl[4] = 96;
        g = 96; die = 0; hdr = 0; a = 0; o = 0; i = 0; na = 0; no = 0; ni = 0; lat = 5;
        reset;
        // ALL_REDUCE_SUM 256 words, groups 1/2/4/8 at every rank of the first two groups
        for (gi = 0; gi < 4; gi = gi + 1) for (di = 0; di < 16; di = di + 1) ep_case(gl[gi], di, 6'd0, 0, 20'd256);
        // GROUP_REDUCE_MCAST s = 8 at G = 96 (the DS order) and s = 2/4/8 at G = 8, DS hidden 4096 and 7168
        for (di = 0; di < 96; di = di + 7) ep_case(8'd96, di, 6'd4, 8'd8, 20'd4096);
        for (k = 2; k <= 8; k = k * 2) for (di = 0; di < 8; di = di + 1) ep_case(8'd8, di, 6'd4, k, 20'd7168);
        // GX11: ALL_REDUCE_SUM at 96 faults; never reaches the endpoint
        g = 96; die = 5; a = md(0, 0, 256, 1, 0); na = 256; reset; k = gos;
        send(6'd0, 0, 0, 0, 7'b0010001); expect_fault; if (gos != k) $fatal(1, "FATAL: G96 AR started the endpoint");
        // ALL_GATHER (op 1, exact bypass): groups 1 / 2 / 4 / 8 / 96, dies past 96 (rank = die mod 96)
        for (gi = 0; gi < 5; gi = gi + 1) for (di = 0; di < 200; di = di + 37) ep_case(gl[gi], di, 6'd1, 0, 20'd512);
        // ALL_GATHER with a row that is not whole flits faults (FP32 n = 250 -> 8,000 bits)
        g = 8; die = 3; a = md(0, 0, 250, 1, 0); na = 250; reset; send(6'd1, 0, 0, 0, 7'b0010001); expect_fault;
        // ops 2-3 (merge stage not installed) fault
        for (k = 2; k <= 3; k = k + 1) begin g = 4; die = 1; a = md(0, 0, 256, 1, 0); na = 256; reset; send(k, 0, 0, 0, 7'b0010001); expect_fault; end
        // A.n not a whole number of flits faults
        g = 4; die = 2; a = md(0, 0, 250, 1, 0); na = 250; reset; send(6'd0, 0, 0, 0, 7'b0010001); expect_fault;
        // endpoint fault during the run faults (sticky)
        g = 4; die = 2; a = md(0, 0, 256, 1, 0); na = 256; reset; send(6'd0, 0, 0, 0, 7'b0010001);
        repeat (12) @(negedge clk); ep_fault = 1; expect_fault; ep_fault = 0;
        // ROW_GATHER: I count from the table (n_sel 63) and from imm_a; BF16 rows of 512 (16 words), FP8 rows of 576 (9)
        for (k = 0; k < 4; k = k + 1) begin
            g = 96; die = 3 + k; reset;
            a = md((k < 2) ? 3'd1 : 3'd2, 40'h1000, (k < 2) ? 20'd512 : 20'd576, 20'd131072, 0);
            na = (k < 2) ? 512 : 576; o = md(1, 40'h2000, 512, 1, 0);
            i = md(5, 40'h3000, 2048, 2, (k % 2) ? 6'd63 : 6'd0); ni = (k % 2) ? 21'd513 : 21'd2048;
            send(6'd5, 25'd8, (k % 2) ? 32'd999 : 32'd7, 32'd64, 7'b1010001);
            t = 0; while (!rf_sv && t < 50) begin @(negedge clk); t = t + 1; end
            if (!rf_sv || rf_g != 96 || rf_b != 8 || rf_d != 64 || rf_rows != ((k % 2) ? 513 : 7) ||
                rf_words != ((k < 2) ? 16 : 9) || rf_ctx != 131072)
                $fatal(1, "FATAL: formatter start mismatch k=%0d rows=%0d words=%0d ctx=%0d", k, rf_rows, rf_words, rf_ctx);
            repeat (6) @(negedge clk); if (rec_done) $fatal(1, "FATAL: ROW_GATHER retired early");
            rf_dv = 1; rf_f = (k == 3); t = 0; while (!rf_dr && t < 20) begin @(negedge clk); t = t + 1; end
            if ((k == 3) ? (!rec_fault || rec_done) : (!rec_done || rec_fault)) $fatal(1, "FATAL: ROW_GATHER retirement k=%0d", k);
            @(negedge clk); rf_dv = 0; rf_f = 0;
            cases = cases + 1;
        end
        // endpoint backpressure: start_ready low holds go
        g = 8; die = 9; a = md(0, 0, 256, 1, 0); o = md(0, 0, 256, 1, 0); na = 256; reset; ep_ready = 0; k = gos;
        send(6'd0, 0, 0, 0, 7'b0010001); repeat (30) @(negedge clk);
        if (gos != k) $fatal(1, "FATAL: go without start_ready");
        ep_ready = 1; repeat (8) @(negedge clk); if (gos != k + 1) $fatal(1, "FATAL: go lost after start_ready");
        ep_done = 1; repeat (6) @(negedge clk); ep_done = 0; cases = cases + 1;
        $display("PASS HGI-COLL record cases=%0d gos=%0d", cases, gos);
        $finish;
    end
endmodule
