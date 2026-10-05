`timescale 1ns/1ps
// Unit bench of rtl/hdc/ot_hdc_mtp_accept_caller.sv (the protected DS MTP accept leaf behind the core's
// ot_hdc_accept ABI) against ot_hdc_accept, cycle-driven the way ot_hdc_core_v41x drives it: STEP runs
// (iter = 0) between speculative steps, gamma = 5 TOKX pulses (slots 1..5) and 6 AMAX pulses (slots 0..5)
// >= 5 cycles apart, ACCEPT, the next start >= 8 cycles after acc_done.  Per step the drafts are chosen so
// that accepted lengths 0..5 all occur; checked every step: acc_a, n_emit, bonus, ttok[0..5], stok[0..5]
// at the DYN point (before ACCEPT), acc_any, and no caller fault.  +MUTATE drops one TOKX (the leaf must
// refuse: fault), proving the check can fail.
module tb_hdc_mtp_accept_caller;
    localparam integer NW = 16, NSLOT = 8, G = 5;
    reg clk = 0, rst_n = 0;
    always #5 clk = ~clk;
    reg start_v = 0, iter = 0, tokx_v = 0, amax_v = 0, acc_v = 0;
    reg [NW-1:0] pos = 0, tok = 0, xtok = 0, mtok = 0;
    reg [2:0] slot = 0;
    wire [NSLOT*NW-1:0] s_c, t_c, s_g, t_g;
    wire d_c, d_g, any_c, any_g, hold, fault;
    wire [2:0] a_c, a_g; wire [3:0] n_c, n_g; wire [NW-1:0] b_c, b_g;
    ot_hdc_mtp_accept_caller #(.NSLOT(NSLOT), .NW(NW), .SLW(3)) dut (.clk(clk), .rst_n(rst_n), .start_v(start_v),
        .iter(iter), .start_pos(pos), .start_tok(tok), .gamma(3'd5), .tokx_v(tokx_v), .tokx_slot(slot),
        .tokx_tok(xtok), .amax_v(amax_v), .amax_slot(slot), .amax_tok(mtok), .acc_v(acc_v), .acc_g(slot),
        .stok(s_c), .ttok(t_c), .acc_done(d_c), .acc_any(any_c), .acc_a(a_c), .n_emit(n_c), .bonus(b_c),
        .hold(hold), .fault(fault));
    ot_hdc_accept #(.NSLOT(NSLOT), .NW(NW)) ref_u (.clk(clk), .rst_n(rst_n), .start_v(start_v), .start_tok(tok),
        .tokx_v(tokx_v), .tokx_slot(slot), .tokx_tok(xtok), .amax_v(amax_v), .amax_slot(slot), .amax_tok(mtok),
        .acc_v(acc_v), .acc_g(slot), .stok(s_g), .ttok(t_g), .acc_done(d_g), .acc_any(any_g), .acc_a(a_g),
        .n_emit(n_g), .bonus(b_g));
    integer step, i, bad = 0, seen [0:5], mutate = 0, w;
    reg [NW-1:0] tg [0:5];
    task tick(input integer n); integer q; begin for (q = 0; q < n; q = q + 1) @(posedge clk); #1; end endtask
    task pulse_start(input it, input [NW-1:0] t);
        begin start_v = 1; iter = it; tok = t; tick(1); start_v = 0; tick(2); end
    endtask
    initial begin
        if ($test$plusargs("MUTATE")) mutate = 1;
        for (i = 0; i < 6; i = i + 1) seen[i] = 0;
        tick(3); rst_n = 1; tick(2);
        for (step = 0; step < 48; step = step + 1) begin
            // a STEP run (prefill position): slot 0 = token, no cohort
            pulse_start(0, 16'(100 + step));
            if (s_c[0 +: NW] !== s_g[0 +: NW] || any_c) begin bad = bad + 1; $display("STEP slot0 differs"); end
            tick(5);
            // the ITER run
            pos = 16'(10 + 7 * step);
            pulse_start(1, 16'(200 + step));
            for (i = 0; i <= G; i = i + 1) tg[i] = 16'((step * 37 + i * 11) % 4040);
            for (i = 1; i <= G; i = i + 1) begin            // drafts: match targets up to step % 6
                slot = 3'(i); xtok = (i - 1 < step % 6) ? tg[i - 1] : 16'(tg[i - 1] + 1);
                tokx_v = !(mutate && step == 3 && i == 2); tick(1); tokx_v = 0; tick(5 + (step % 3));
            end
            for (i = 0; i <= G; i = i + 1) begin
                slot = 3'(i); mtok = tg[i]; amax_v = 1; tick(1); amax_v = 0; tick(5);
            end
            w = 0; while (hold && w < 50) begin tick(1); w = w + 1; end
            for (i = 0; i <= G; i = i + 1)
                if (s_c[i*NW +: NW] !== s_g[i*NW +: NW]) begin bad = bad + 1; $display("step %0d stok %0d", step, i); end
            slot = 3'(G); acc_v = 1; tick(1); acc_v = 0;
            w = 0; while (!d_c && w < 50) begin tick(1); w = w + 1; end
            if (w >= 50) begin bad = bad + 1; $display("step %0d: no acc_done", step); end
            tick(1);
            if (a_c !== a_g || n_c !== n_g || b_c !== b_g || !any_c || any_g !== any_c) begin
                bad = bad + 1; $display("step %0d a %0d/%0d n %0d/%0d bonus %0d/%0d", step, a_c, a_g, n_c, n_g, b_c, b_g);
            end
            for (i = 0; i <= G; i = i + 1)
                if (t_c[i*NW +: NW] !== t_g[i*NW +: NW]) begin bad = bad + 1; $display("step %0d ttok %0d", step, i); end
            seen[a_c] = seen[a_c] + 1;
            tick(8);
            if (fault) begin bad = bad + 1; $display("step %0d: caller fault", step); step = 99; end
        end
        $display("CALLER steps=%0d mismatches=%0d fault=%0d accepted_hist=%0d,%0d,%0d,%0d,%0d,%0d", step, bad, fault,
                 seen[0], seen[1], seen[2], seen[3], seen[4], seen[5]);
        if (bad == 0 && !fault && seen[0] > 0 && seen[5] > 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
