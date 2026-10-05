`timescale 1ns/1ps
// Lockstep: ot_qwen_hbmacc_gate_f12 OPT=0 (the die top's gating, expression for expression) against OPT=1 (the
// 1.2 GHz form) on random segment tables, spine reads and window arrivals.  Every cycle me_ok, kv_ok, w_c_gray and
// hbm_fault must match.  The host rewrites the table only between stages: the bench holds the spine's read low for
// the cycle of the write and the next three (the registered copy's settle) and does not compare those cycles.  +seed=<n> +cycles=<n>
module tb_qwen_hbmacc_gate_lockstep;
    // DUT = 1: zero-cycle form, compared cycle for cycle.  DUT = 2: registered window count = the reference with its
    // window input one cycle later (AGD = 1).  DUT = 3: also its consumed count one cycle later (WCL = 1).  DUT 3 assumes
    // non-wrapping stream indexes, so the bench keeps sidx < 2^31.
    parameter integer DUT = 1;
    localparam integer AGD = (DUT >= 2) ? 1 : 0, WCL = (DUT >= 3) ? 1 : 0;
    localparam integer NSEG = 8, CW = 32, AW = 24;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg              re, cen;
    reg  [AW-1:0]    addr;
    reg  [NSEG*24-1:0] base, len;
    reg  [NSEG*CW-1:0] sidx;
    reg  [NSEG*2-1:0]  kind;
    reg  [CW-1:0]    a_bin, a_gray;
    wire mo0, mo1, ko0, ko1, f0, f1;
    wire [CW-1:0] cg0, cg1;
    ot_qwen_hbmacc_gate_f12 #(.OPT(0)) u0 (.clk(clk), .rst_n(rst_n), .int8_wrom_re(re), .int8_wrom_addr(addr), .me_clk_en(cen),
        .seg_base(base), .seg_len(len), .seg_sidx(sidx), .seg_kind(kind), .w_a_gray(AGD ? a_gray_d : a_gray),
        .me_ok(mo0), .kv_ok(ko0), .w_c_gray(cg0), .hbm_fault(f0));
    ot_qwen_hbmacc_gate_f12 #(.OPT(DUT)) u1 (.clk(clk), .rst_n(rst_n), .int8_wrom_re(re), .int8_wrom_addr(addr), .me_clk_en(cen),
        .seg_base(base), .seg_len(len), .seg_sidx(sidx), .seg_kind(kind), .w_a_gray(a_gray),
        .me_ok(mo1), .kv_ok(ko1), .w_c_gray(cg1), .hbm_fault(f1));
    reg  [CW-1:0] a_gray_d, cg0_d;
    always @(posedge clk) begin a_gray_d <= a_gray; cg0_d <= cg0; end
    wire [CW-1:0] cg0x = WCL ? cg0_d : cg0;
    integer seed, seed0, cycles, c, k, settle, errs, n_ok0, n_hit, n_stall, tables;
    reg [CW-1:0] r;
    task new_table;
        integer s; reg [23:0] b;
        begin
            b = rnd(0) & 24'h3fff;
            for (s = 0; s < NSEG; s = s + 1) begin
                // mostly contiguous segments in consumption order, sometimes overlapping or wrapping (priority check)
                base[s*24 +: 24] = (rnd(0) % 8 == 0) ? rnd(0) : b;
                len[s*24 +: 24]  = (rnd(0) % 16 == 0) ? rnd(0) : (rnd(0) & 24'h1ff);
                b = base[s*24 +: 24] + len[s*24 +: 24];
                sidx[s*CW +: CW] = (rnd(0) % 8 == 0) ? (rnd(0) & 32'h7fffffff) : (rnd(0) & 32'hffff);
                kind[s*2 +: 2]   = rnd(0);
            end
            tables = tables + 1;
        end
    endtask
    // xorshift32 (simulator-independent; Verilator's $random(seed) ignores the seed variable)
    reg [31:0] rs;
    function automatic integer rnd(input integer dummy);
        begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 17); rs = rs ^ (rs << 5); rnd = rs; end
    endfunction
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        seed0 = seed;
        rs = 32'h9e3779b9 ^ seed; if (rs == 0) rs = 1;
        if (!$value$plusargs("cycles=%d", cycles)) cycles = 200000;
        errs = 0; n_ok0 = 0; n_hit = 0; n_stall = 0; tables = 0;
        re = 0; cen = 0; addr = 0; a_bin = 0; a_gray = 0; settle = 2;
        new_table;
        repeat (3) @(posedge clk);
        #0.1 rst_n = 1;
        for (c = 0; c < cycles; c = c + 1) begin
            @(negedge clk);
            if (settle == 0 && (mo0 !== mo1 || ko0 !== ko1 || cg0x !== cg1 || f0 !== f1)) begin
                errs = errs + 1;
                if (errs < 10) $display("MISMATCH c=%0d me_ok %b/%b kv_ok %b/%b wc %h/%h fault %b/%b", c, mo0, mo1, ko0, ko1, cg0x, cg1, f0, f1);
            end
            if (settle == 0) begin n_ok0 = n_ok0 + mo0; n_stall = n_stall + !mo0; end
            if (settle > 0) settle = settle - 1;
            // drive the next cycle
            if (rnd(0) % 4000 == 0) begin new_table; settle = 4; end
            re = (settle == 0) && ((rnd(0) % 4) != 0);
            cen = (rnd(0) % 3) != 0;
            k = rnd(0) % NSEG; if (k < 0) k = -k;
            r = rnd(0);
            addr = (r[3:0] == 0) ? r[31:8] : base[k*24 +: 24] + (r[20:8] % (len[k*24 +: 24] + 2));
            if (r[30:28] == 0) a_bin = a_bin + (rnd(0) & 32'h7);
            if (rnd(0) % 5000 == 0) a_bin = rnd(0);        // wrap / jump cases
            a_gray = a_bin ^ (a_bin >> 1);
        end
        $display("RESULT gate_lockstep DUT=%0d seed=%0d cycles=%0d tables=%0d me_ok=%0d stall=%0d mismatches=%0d", DUT, seed0, cycles, tables, n_ok0, n_stall, errs);
        $finish;
    end
endmodule
