`timescale 1ns/1ps
// Lockstep bench: ot_dshbm_dspark_ctl FAST = 0 (as built) vs FAST = 1 driven by one random engine / argmax / host
// environment (random cmd_ready and engine latency, argmax tokens from a small alphabet so every accept length
// occurs, forced and drafted runs, MAXPOS-limited gamma).  Every output of the two is compared every cycle.
module tb_ctl_lockstep;
    parameter integer NRUN = 200, SEED = 1, MAXPOS = 64, NL = 3;
    localparam integer TW = 17, PMAX = 8;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg start = 0, cfg_force = 0; reg [3:0] cfg_gamma = 0; reg [15:0] cfg_ngen = 0, cfg_plen = 0;
    reg cmd_ready = 0, eng_done = 0, am_v = 0; reg [TW-1:0] am_idx = 0;
    reg [TW-1:0] p_tok = 0, f_tok = 0;
    reg [31:0] n = 0;
    wire [15:0] pa0, pa1, fa0, fa1, ei0, ei1, st0, st1;
    wire ev0, ev1, dn0, dn1, cv0, cv1, ns0, ns1, tv0, tv1, sv0, sv1;
    wire [TW-1:0] et0, et1, ct0, ct1, tt0, tt1;
    wire [3:0] co0, co1, cn0, cn1, sg0, sg1; wire [7:0] cx0, cx1; wire [31:0] cp0, cp1, nv0, nv1, tp0, tp1;
    wire [PMAX*TW-1:0] cs0, cs1; wire [2:0] sa0, sa1; wire [31:0] y00, y01, y10, y11, y20, y21;
`define CTL(I, F) \
    ot_dshbm_dspark_ctl #(.TW(TW), .PMAX(PMAX), .NL(NL), .MAXPOS(MAXPOS), .FAST(F)) u``I (.clk(clk), .rst_n(rst_n), \
        .start(start), .cfg_gamma(cfg_gamma), .cfg_force(cfg_force), .cfg_ngen(cfg_ngen), .cfg_plen(cfg_plen), \
        .p_addr(pa``I), .p_tok(p_tok), .f_addr(fa``I), .f_tok(f_tok), .e_v(ev``I), .e_tok(et``I), .e_idx(ei``I), .done(dn``I), \
        .cmd_v(cv``I), .cmd_ready(cmd_ready), .cmd_op(co``I), .cmd_idx(cx``I), .cmd_ncol(cn``I), .cmd_pos(cp``I), \
        .cmd_tok1(ct``I), .cmd_toks(cs``I), .eng_done(eng_done), .am_v(am_v), .am_idx(am_idx), .n(n), .n_set(ns``I), \
        .n_val(nv``I), .tw_v(tv``I), .tw_pos(tp``I), .tw_tok(tt``I), .step_v(sv``I), .step_a(sa``I), .step_g(sg``I), \
        .steps(st``I), .cyc_total(y0``I), .cyc_engine(y1``I), .cyc_markov(y2``I));
    `CTL(0, 0)
    `CTL(1, 1)
    wire [1023:0] o0 = {pa0, fa0, ev0, et0, ei0, dn0, cv0, co0, cx0, cn0, cp0, ct0, cs0, ns0, nv0, tv0, tp0, tt0, sv0, sa0, sg0, st0, y00, y10, y20};
    wire [1023:0] o1 = {pa1, fa1, ev1, et1, ei1, dn1, cv1, co1, cx1, cn1, cp1, ct1, cs1, ns1, nv1, tv1, tp1, tt1, sv1, sa1, sg1, st1, y01, y11, y21};
    integer seed, bad = 0, cyc = 0, r, steps_tot = 0, emits = 0, pend = 0, delay = 0, amq = 0;
    reg busy = 0, acc = 0; reg [3:0] acc_op = 0, acc_nc = 0;
    // command acceptance as the DUT sees it (sampled at the edge, before cmd_v drops)
    always @(posedge clk) begin acc <= cv0 && cmd_ready; acc_op <= co0; acc_nc <= cn0; end
    always @(posedge clk) if (rst_n) begin
        cyc = cyc + 1;
        if (o0 !== o1) begin bad = bad + 1; if (bad < 8) $display("MISMATCH cyc %0d %h", cyc, o0 ^ o1); end
        if (ns0) n <= nv0;
        if (sv0) steps_tot = steps_tot + 1;
        if (ev0) emits = emits + 1;
    end
    // engine: accept a command, answer its argmaxes and done after a random delay
    always @(negedge clk) begin
        cmd_ready <= $random(seed);
        eng_done <= 0; am_v <= 0;
        if (acc) begin busy = 1; delay = 1 + ($unsigned($random(seed)) % 6);
            amq = (acc_op == 1) ? acc_nc : (acc_op == 5) ? 1 : 0; end
        else if (busy) begin
            if (amq > 0 && ($random(seed) & 1)) begin am_v <= 1; am_idx <= $unsigned($random(seed)) % 3; amq = amq - 1; end
            else if (amq == 0) begin if (delay == 0) begin eng_done <= 1; busy = 0; end else delay = delay - 1; end
        end
        p_tok <= $unsigned($random(seed)) % 5; f_tok <= $unsigned($random(seed)) % 3;
    end
    initial begin
        seed = SEED;
        for (r = 0; r < NRUN; r = r + 1) begin
            rst_n = 0; n = 0; busy = 0; repeat (2) @(posedge clk); rst_n = 1;
            @(negedge clk);
            cfg_gamma = $unsigned($random(seed)) % 8; cfg_force = $random(seed); cfg_ngen = 1 + $unsigned($random(seed)) % 30;
            cfg_plen = 1 + $unsigned($random(seed)) % 4;
            start = 1; @(negedge clk); start = 0;
            while (!dn0) @(negedge clk);
            repeat (3) @(negedge clk);
        end
        $display("LOCKSTEP ctl runs=%0d cycles=%0d steps=%0d emits=%0d mismatches=%0d", NRUN, cyc, steps_tot, emits, bad);
        if (bad != 0) $fatal(1, "LOCKSTEP_TERMINAL_FAIL");
        $finish;
    end
    initial begin #500000000; $display("TIMEOUT run %0d s=%0d busy=%0d amq=%0d delay=%0d", r, u0.s, busy, amq, delay); $fatal(1, "LOCKSTEP_TERMINAL_TIMEOUT"); end
endmodule
