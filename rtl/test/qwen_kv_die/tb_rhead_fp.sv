`timescale 1ns/1ps
// tb_rhead_fp (fe-push-qwen-1010, 2026-10-10): the KV-die head tile ot_qwen_nearhbm_head_h with FP = 1 (ANR adders, quad
// reset leaves, per-group node-slice select) in LOCKSTEP with FP = 0, both with the REAL FP32 units (no DPI stand-ins),
// HD = 32 (two 16-lane groups, so the per-group select differs structurally from group 0's).  The same random stimulus
// on every input pin (control word, KV rows, e, decision word, q beats incl. the hid-strapped beats); after a warm-up
// every output (sc_d, sc_f, g_f, nb_d) must match on EVERY cycle (4-state !==).  FPMUT = 1 (the ANR adders' HSPLIT copy
// one edge stale) must FAIL.
module tb_rhead_fp;
    parameter integer HD = 32, N = 1200, WARM = 64, SEED = 1, FPMUT = 0;
    parameter [1:0] HID = 2'd1;
    reg clk = 0, rst_n = 0;
    reg [3:0] c_in = 0; reg [HD*8-1:0] row_in = 0; reg [15:0] e_in = 0; reg [11:0] lt_in = 0;
    reg qv = 0; reg [5:0] qb = 0; reg [511:0] qd = 0;
    wire [31:0] sd0, sd1; wire sf0, sf1, gf0, gf1; wire [HD*8-1:0] nb0, nb1;
    ot_qwen_nearhbm_head_h #(.HD(HD), .FP(0)) u_ref (.clk(clk), .rst_n(rst_n), .c_in(c_in), .row_in(row_in), .e_in(e_in),
        .lt_in(lt_in), .hid(HID), .q_valid_in(qv), .q_beat_in(qb), .q_data_in(qd), .sc_d(sd0), .sc_f(sf0), .g_f(gf0), .nb_d(nb0));
    ot_qwen_nearhbm_head_h #(.HD(HD), .FP(1), .FPMUT(FPMUT)) u_dut (.clk(clk), .rst_n(rst_n), .c_in(c_in), .row_in(row_in),
        .e_in(e_in), .lt_in(lt_in), .hid(HID), .q_valid_in(qv), .q_beat_in(qb), .q_data_in(qd), .sc_d(sd1), .sc_f(sf1),
        .g_f(gf1), .nb_d(nb1));
    always #0.5 clk = ~clk;
    integer i, j, bad = 0, cmp = 0, nbw = 0, scv = 0, seed = SEED;
    reg [31:0] r;
    function [7:0] fp8(input integer x); fp8 = (x[6:3] == 4'hF) ? {x[7], 4'hE, x[2:0]} : x[7:0]; endfunction
    function [15:0] bf(input integer x); bf = {x[15], 3'b011, x[11:0]}; endfunction   // finite, mid exponents
    initial begin
        repeat (6) @(posedge clk);
        rst_n <= 1;
        for (i = 0; i < N; i = i + 1) begin
            @(negedge clk);
            r = $random(seed); c_in = r[3:0];
            for (j = 0; j < HD; j = j + 1) begin r = $random(seed); row_in[8*j +: 8] = fp8(r); end
            r = $random(seed); e_in = bf(r);
            r = $random(seed); lt_in = r[11:0];
            r = $random(seed); qv = r[0]; qb = (r[3:1] == 0) ? 6'(HID) : ((r[3:1] == 1) ? 6'(4 + HID) : r[9:4]);
            for (j = 0; j < 32; j = j + 1) begin r = $random(seed); qd[16*j +: 16] = bf(r); end
        end
        repeat (40) @(posedge clk);
        if (bad == 0 && cmp > N / 2 && nbw > 100) $display("PASS rhead_fp HD=%0d cycles=%0d nb_writes=%0d", HD, cmp, nbw);
        else $display("FAIL rhead_fp HD=%0d mismatches=%0d cycles=%0d nb_writes=%0d", HD, bad, cmp, nbw);
        $finish;
    end
    reg [HD*8-1:0] nbp;
    integer t = 0;
    always @(negedge clk) begin
        t = t + 1;
        if (t % 200 == 0) $display("progress t=%0d mismatches=%0d", t, bad);
        if (t > WARM + 10) begin
            cmp = cmp + 1;
            if (nb0 !== nbp) nbw = nbw + 1;
            if ({sd0, sf0, gf0, nb0} !== {sd1, sf1, gf1, nb1}) begin
                bad = bad + 1;
                if (bad <= 5) $display("MISMATCH t=%0d sc %h/%h sf %b/%b gf %b/%b nbdiff=%0d", t, sd0, sd1, sf0, sf1, gf0, gf1, nb0 !== nb1);
            end
        end
        nbp = nb0;
    end
endmodule
