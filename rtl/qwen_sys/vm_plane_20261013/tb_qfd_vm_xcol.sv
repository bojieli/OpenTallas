`timescale 1ns/1ps
// Leaf miter of ot_qfd_vm_xcol_t (claude/qwen-tp8-vm PLAN 2026-10-13): the merged plane + line leaf against its two
// parts wired as the parent wired them before the merge (ot_qfd_vm_xplane_t q -> ot_qfd_vm_xline_t d).  The parts
// carry their own miters against the parent's expressions (tb_qfd_vm_xplane.sv, tb_qfd_vm_xtree.sv); this bench binds
// the HARDENED module: q compared on every clock under xorshift64 stimulus (random data, plane / line control, me
// stalls 1 in 4).  Non-vacuity refusal: stalls, engine edges, q changes, line writes and replications below their
// floors print FAIL.  PMUT 1..3 (plane) and LMUT 1..3 (line) inside the candidate must FAIL.
module tb_qfd_vm_xcol;
    parameter integer NRB = 16, SMIN = 7, SMAX = 9, BMAX = 8, ND = 14, CYCLES = 4000, SEED = 1, PMUT = 0, LMUT = 0;
    localparam integer LNRB = $clog2(NRB), BEAT = (NRB - 1) * 16, NVW = $clog2(BEAT + 1), LB = $clog2(BMAX) + 1, NX = 1 << SMAX;
    reg clk = 0; always #5 clk = ~clk;
    reg me_e = 0;
    reg [NRB*16-1:0] d = 0;
    reg [LNRB+3:0] c_a = 0; reg [NVW-1:0] c_nv = 0;
    reg c_v = 0, o_v = 0; reg [ND-1:0] c_d = 0; reg [LB-1:0] c_j = 0; reg [3:0] c_sp = 0, o_sp = 0;
    wire [NX-1:0] q, r_q; wire [BEAT-1:0] r_bv;
    ot_qfd_vm_xcol_t #(.NRB(NRB), .SMIN(SMIN), .SMAX(SMAX), .BMAX(BMAX), .ND(ND), .PMUT(PMUT), .LMUT(LMUT)) candidate (
        .clk(clk), .me_e(me_e), .d_lo(d[NRB*8-1:0]), .d_hi(d[NRB*16-1:NRB*8]), .c_a(c_a), .c_nv(c_nv), .c_v(c_v), .c_d(c_d), .c_j(c_j), .c_sp(c_sp),
        .o_v(o_v), .o_sp(o_sp), .q_lo(q[NX/2-1:0]), .q_hi(q[NX-1:NX/2]));
    ot_qfd_vm_xplane_t #(.NRB(NRB)) ref_p (.clk(clk), .me_e(me_e), .d(d), .c_a(c_a), .c_nv(c_nv), .q(r_bv));
    ot_qfd_vm_xline_t #(.NRB(NRB), .SMIN(SMIN), .SMAX(SMAX), .BMAX(BMAX), .ND(ND)) ref_l (.clk(clk), .me_e(me_e), .d(r_bv),
        .c_v(c_v), .c_d(c_d), .c_j(c_j), .c_sp(c_sp), .o_v(o_v), .o_sp(o_sp), .q(r_q));
    reg [63:0] rng;
    function automatic [31:0] rnd(input integer dummy);
        begin rng = rng ^ (rng << 13); rng = rng ^ (rng >> 7); rng = rng ^ (rng << 17); rnd = rng[47:16]; end
    endfunction
    integer cyc, w, errors = 0, checks = 0, stalls = 0, moves = 0, qchg = 0, writes = 0, reps = 0, ones = 0;
    reg [NX-1:0] lq = 0;
    initial begin
        rng = 64'h9E3779B97F4A7C15 ^ {32'd0, SEED[31:0]} ^ ({32'd0, SEED[31:0]} << 32);
        for (cyc = 0; cyc < CYCLES; cyc = cyc + 1) begin
            @(negedge clk);
            me_e = ((rnd(0) % 4) != 0); if (me_e) moves = moves + 1; else stalls = stalls + 1;
            for (w = 0; w < NRB / 2; w = w + 1) d[w*32 +: 32] = rnd(0);
            c_a = rnd(0); c_nv = ((rnd(0) % 4) == 0) ? (rnd(0) % (BEAT + 1)) : BEAT;
            c_v = ((rnd(0) % 2) == 0); c_d = (rnd(0) % 3 == 0) ? rnd(0) : (1 << (rnd(0) % ND)); c_j = rnd(0) % (BMAX + 1);
            c_sp = SMIN + (rnd(0) % (SMAX - SMIN + 1)); o_v = ((rnd(0) % 3) == 0); o_sp = SMIN + (rnd(0) % (SMAX - SMIN + 1));
            if (c_v && me_e) writes = writes + 1;
            if (o_v && me_e) reps = reps + 1;
            @(posedge clk); #1;
            if (cyc > 16) begin
                checks = checks + 1;
                if (q !== r_q) begin errors = errors + 1; if (errors < 4) $display("xcol mismatch cyc %0d", cyc); end
                if (r_q !== lq) qchg = qchg + 1;
                if (^r_q === 1'b1) ones = ones + 1;
                lq = r_q;
            end
        end
        if (stalls < CYCLES / 8 || moves < CYCLES / 2 || qchg < CYCLES / 8 || writes < CYCLES / 8 || reps < CYCLES / 8 || ones < CYCLES / 16) begin
            $display("FAIL qfd_vm_xcol VACUOUS stalls=%0d moves=%0d q_changes=%0d line_writes=%0d replications=%0d odd_parity=%0d",
                     stalls, moves, qchg, writes, reps, ones);
            $fatal(1, "FAIL");
        end
        if (errors != 0) begin $display("FAIL qfd_vm_xcol PMUT=%0d LMUT=%0d errors=%0d of %0d", PMUT, LMUT, errors, checks); $fatal(1, "FAIL"); end
        $display("PASS qfd_vm_xcol NRB=%0d SMAX=%0d SEED=%0d exact %0d checks: stalls=%0d q_changes=%0d line_writes=%0d replications=%0d odd_parity=%0d",
                 NRB, SMAX, SEED, checks, stalls, qchg, writes, reps, ones);
        $finish;
    end
endmodule
