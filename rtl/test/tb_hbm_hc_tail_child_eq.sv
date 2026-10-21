`timescale 1ns/1ps
// HBM-HCROOT6 10-20: lockstep equivalence of the hardened HC tail child ot_hbm_hc_tail_child_static against the released
// tail unit ot_hbm_hc_tail_unit_static (ot_hgi_hc_tail_static inside): the same random launches (+N cases, +SEED) into
// both; the child's result_v must come exactly 2 edges after the unit's, with an identical 768-bit result, and the
// sticky faults must agree.  Launch spacing is random (every divider phase).  Inputs: pre-sigmoid mixes / bases in
// [-8, 8] (some wide-range words), scales in [0.5, 2).  Prints TAILC PASS cases=<n> / TAILC FAIL <errors>.
// -DMUT=1 builds the child's p3 row-max mutant (must FAIL).  Cycle-driven by --binary --timing.
`ifndef MUT
`define MUT 0
`endif
module tb_hbm_hc_tail_child_eq;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0, launch = 0;
    reg [767:0] mixes = 0, bases = 0; reg [95:0] scales = 0;
    wire rv_r, rv_c, f_r, f_c; wire [767:0] y_r, y_c;
    ot_hbm_hc_tail_unit_static u_ref (.clk(clk), .rst_n(rst_n), .launch(launch), .mixes(mixes), .bases(bases),
        .scales(scales), .result_v(rv_r), .result(y_r), .fault(f_r));
`ifdef NATIVE_DUT   // gate-level cloned netlist (no parameters; mutants are RTL-only)
    ot_hbm_hc_tail_child_static u_dut (
`else
    ot_hbm_hc_tail_child_static #(.MUT(`MUT)) u_dut (
`endif
                                       .clk(clk), .rst_n(rst_n), .launch(launch), .mixes(mixes),
        .bases(bases), .scales(scales), .result_v(rv_c), .result(y_c), .fault(f_c));
    integer N, seed, cyc = 0, errs = 0, done_r = 0, done_c = 0, nf = 0;
    reg [31:0] lf;
    integer t_r [0:4095];
    reg [767:0] yr [0:4095];
    function [31:0] nx(input [31:0] x); reg [31:0] v; begin v = x ^ (x << 13); v = v ^ (v >> 17); nx = v ^ (v << 5); end endfunction
    task automatic rnd(input integer kind, output [31:0] w);
        reg [31:0] a;
        begin
            lf = nx(lf); a = lf;
            case (kind)
                0: w = {a[31], 8'(118 + a[27:24] % 12), a[22:0]};             // |x| in [2^-9, 8)
                1: w = {a[31], 8'(100 + a[29:24] % 40), a[22:0]};             // wide range
                default: w = {1'b0, 8'(126 + a[24]), a[22:0]};                 // [0.5, 2)
            endcase
        end
    endtask
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 48;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        lf = 32'h9e3779b9 ^ seed; if (lf == 0) lf = 1;
        repeat (5) @(negedge clk); rst_n = 1; repeat (8) @(negedge clk);
        for (integer c = 0; c < N; c = c + 1) begin
            reg [31:0] w; integer kind, gap;
            lf = nx(lf); kind = (lf[3:0] == 0) ? 1 : 0;
            for (integer j = 0; j < 24; j = j + 1) begin rnd(kind, w); mixes[j*32 +: 32] = w; rnd(0, w); bases[j*32 +: 32] = w; end
            for (integer j = 0; j < 3; j = j + 1) begin rnd(2, w); scales[j*32 +: 32] = w; end
            launch = 1; @(negedge clk); launch = 0;
            // scramble the inputs after the launch edge: both must have captured
            lf = nx(lf); mixes = {24{lf}}; bases = {24{~lf}}; scales = {3{lf ^ 32'h5a5a5a5a}};
            lf = nx(lf); gap = 500 + lf % 23;
            repeat (gap) @(negedge clk);
        end
        repeat (40) @(negedge clk);
        if (done_r != N || done_c != N) begin errs = errs + 1; $display("TAILC ERR results ref %0d child %0d of %0d", done_r, done_c, N); end
        if (f_r !== f_c) begin errs = errs + 1; $display("TAILC ERR final fault ref %0d child %0d", f_r, f_c); end
        if (errs == 0) $display("TAILC PASS cases=%0d seed=%0d child result = unit result + 2 edges, faults agree (fault %0d)", N, seed, f_r);
        else $display("TAILC FAIL %0d errors in %0d cases", errs, N);
        $finish;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        // HBM-HCROOT8 10-20: results count only while rst_n is high.  The parent (ot_hbm_hc_root_static) holds its tail
        // consumers (tready, tail_fault) in rst_tail = this rst_n, so child pins during reset are don't-care there; a 2-state
        // gate-level model whose async-reset flops see no negedge at time 0 shows one power-up result_v at cycle 0 (the
        // 10-20 native FAIL50 = 49 vs 48 results, every later result offset by one count).
        if (rst_n && rv_r) begin t_r[done_r] = cyc; yr[done_r] = y_r; done_r = done_r + 1; end
        if (rst_n && rv_c) begin
            if (done_c >= done_r) begin errs = errs + 1; $display("TAILC ERR child result %0d before the unit's", done_c); end
            else begin
                if (cyc - t_r[done_c] != 2) begin errs = errs + 1; $display("TAILC ERR case %0d child result %0d edges after the unit's (want 2)", done_c, cyc - t_r[done_c]); end
                if (y_c !== yr[done_c]) begin
                    errs = errs + 1;
                    if (errs < 8) for (integer j = 0; j < 24; j = j + 1) if (y_c[j*32 +: 32] !== yr[done_c][j*32 +: 32])
                        $display("TAILC ERR case %0d word %0d child %08x unit %08x", done_c, j, y_c[j*32 +: 32], yr[done_c][j*32 +: 32]);
                end
            end
            done_c = done_c + 1;
        end
        if (cyc > 200000) begin $display("TAILC FAIL watchdog"); $finish; end
    end
endmodule
