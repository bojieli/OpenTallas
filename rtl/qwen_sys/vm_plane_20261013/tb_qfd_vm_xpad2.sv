`timescale 1ns/1ps
// Leaf bench of ot_qfd_vm_xpad2_t (claude/qwen-tp8-vm PLAN 2026-10-13): the 2-stage pad leaf against a behavioural
// 2-deep me-enabled shift register (reference written here, not from the leaf's parts), q compared on every clock
// under xorshift64 stimulus, me stalls 1 in 4 (MEREG = 1: me_e is me one edge early).  Non-vacuity refusal: stalls,
// engine edges and q changes below their floors print FAIL.  MUT 1 (stage 0 free-runs) and MUT 2 (one stage short) must FAIL.
module tb_qfd_vm_xpad2;
    parameter integer W = 512, CYCLES = 4000, SEED = 1, MUT = 0;
    reg clk = 0; always #5 clk = ~clk;
    reg me_e = 0, me = 0;
    reg [W-1:0] d = 0, r0 = 0, r1 = 0, lq = 0;
    wire [W-1:0] q;
    ot_qfd_vm_xpad2_t #(.W(W), .MEREG(1), .MUT(MUT)) dut (.clk(clk), .me_e(me_e), .d(d), .q(q));
    always @(posedge clk) begin me <= me_e; if (me) begin r0 <= d; r1 <= r0; end end
    reg [63:0] rng;
    function automatic [31:0] rnd(input integer dummy);
        begin rng = rng ^ (rng << 13); rng = rng ^ (rng >> 7); rng = rng ^ (rng << 17); rnd = rng[47:16]; end
    endfunction
    integer cyc, w, errors = 0, checks = 0, stalls = 0, moves = 0, qchg = 0;
    initial begin
        rng = 64'h9E3779B97F4A7C15 ^ {32'd0, SEED[31:0]} ^ ({32'd0, SEED[31:0]} << 32);
        for (cyc = 0; cyc < CYCLES; cyc = cyc + 1) begin
            @(negedge clk);
            me_e = ((rnd(0) % 4) != 0); if (me_e) moves = moves + 1; else stalls = stalls + 1;
            for (w = 0; w < W / 32; w = w + 1) d[w*32 +: 32] = rnd(0);
            @(posedge clk); #1;
            if (cyc > 8) begin
                checks = checks + 1;
                if (q !== r1) begin errors = errors + 1; if (errors < 4) $display("xpad2 mismatch cyc %0d", cyc); end
                if (r1 !== lq) qchg = qchg + 1;
                lq = r1;
            end
        end
        if (stalls < CYCLES / 8 || moves < CYCLES / 2 || qchg < CYCLES / 2) begin
            $display("FAIL qfd_vm_xpad2 VACUOUS stalls=%0d moves=%0d q_changes=%0d", stalls, moves, qchg); $fatal(1, "FAIL");
        end
        if (errors != 0) begin $display("FAIL qfd_vm_xpad2 MUT=%0d errors=%0d of %0d", MUT, errors, checks); $fatal(1, "FAIL"); end
        $display("PASS qfd_vm_xpad2 W=%0d SEED=%0d exact %0d checks: stalls=%0d q_changes=%0d", W, SEED, checks, stalls, qchg);
        $finish;
    end
endmodule
