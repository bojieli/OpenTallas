`timescale 1ns/1ps
// CORE-S81-SVC (10-23): lockstep of the S81 attention tile as 16 one-head hard cores (ot_s81c_attn_tile_hc) against
// ot_hdc_v41x_attn_tile_s at the S81 engine parameters (default HG 4, PCOLP 0): every output (ov, oy, oflt) every
// cycle from the first cycle after reset.  Random load stream (normal / p-mode, both p-words via ld_w2v, all banks,
// every group index incl. out-of-range) interleaved with a random operand stream (random 18-bit elements: pads,
// formats, codes, scales).  Driven by tb_s81c_hcore.cpp (clock); +seed=<n>, +cycles=<n>.
// Mutants: -DOT_S81C_HCORE_MUT (head g reads head g+1's p-word-1 column) must FAIL.
module tb_s81c_hcore (input wire clk);
    localparam integer H = 16, TD = 32, BW = 3;
    reg rst_n = 1'b0;
    reg ld_v, ld_mode, ld_w2v, iv;
    reg [BW-1:0] ld_bank, ibank;
    reg [7:0] ld_grp;
    reg [1023:0] ld_w;
    reg [575:0] ib;
    wire r_ov, d_ov;
    wire [511:0] r_oy, d_oy;
    wire [15:0] r_of, d_of;
    ot_hdc_v41x_attn_tile_s #(.H(16), .TD(32), .NBANK(5), .BW(3), .PWORDS(2), .FPL(4), .FML(6), .F12(1)) u_ref (
        .clk(clk), .rst_n(rst_n), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp), .ld_w(ld_w),
        .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(r_ov), .oy(r_oy), .oflt(r_of));
    ot_s81c_attn_tile_hc u_dut (
        .clk(clk), .rst_n(rst_n), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp), .ld_w(ld_w),
        .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(d_ov), .oy(d_oy), .oflt(d_of));
    integer cyc = 0, mism = 0, nov = 0, seed = 1, ncyc = 20000, i, nz = 0;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("cycles=%d", ncyc)) ncyc = 20000;
        xs = 32'h9e3779b9 ^ (seed * 32'h85ebca6b);
        ld_v = 0; ld_mode = 0; ld_w2v = 0; iv = 0; ld_bank = 0; ibank = 0; ld_grp = 0; ld_w = 0; ib = 0;
    end
    // xorshift32 stimulus generator (seeded by +seed)
    reg [31:0] xs;
    initial xs = 32'h9e3779b9;
    function [31:0] rnd; input integer dummy; reg [31:0] x; begin
        x = xs; x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5); xs = x; rnd = x; end endfunction
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        // stimulus: phase A (cycles < 400) mostly loads; then mixed
        ld_v <= (cyc < 400) ? (rnd(0) % 8 != 0) : (rnd(0) % 4 == 0);
        ld_mode <= rnd(0) % 3 == 0;
        ld_w2v <= rnd(0) % 2;
        ld_bank <= rnd(0) % 6;                      // 5 = no bank (writes nothing)
        ld_grp <= (rnd(0) % 16 == 0) ? (rnd(0) % 256) : (rnd(0) % 17);
        for (i = 0; i < 32; i = i + 1) ld_w[i*32 +: 32] <= rnd(0);
        iv <= (cyc < 300) ? 1'b0 : (rnd(0) % 4 != 0);
        ibank <= rnd(0) % 5;
        for (i = 0; i < 18; i = i + 1) ib[i*32 +: 32] <= rnd(0);
        if (rst_n && cyc > 4) begin
            if (r_ov !== d_ov || r_oy !== d_oy || r_of !== d_of) begin
                mism = mism + 1;
                if (mism <= 5) $display("MISMATCH cyc=%0d ov %b/%b oy %h / %h oflt %h/%h", cyc, r_ov, d_ov,
                                        r_oy[127:0], d_oy[127:0], r_of, d_of);
            end
            if (r_ov) begin nov = nov + 1; if (r_oy != 0) nz = nz + 1; end
        end
        if (cyc == ncyc) begin
            if (mism == 0 && nov > 1000 && nz > 100)
                $display("S81C_HCORE_BENCH PASS seed=%0d cycles=%0d mismatches=0 ov=%0d ov_nonzero=%0d", seed, ncyc, nov, nz);
            else
                $display("S81C_HCORE_BENCH FAIL seed=%0d cycles=%0d mismatches=%0d ov=%0d ov_nonzero=%0d", seed, ncyc, mism, nov, nz);
            $finish;
        end
    end
endmodule
