`timescale 1ns/1ps
// S81-SVC8 (10-20): lockstep of the successor head group ot_s81svc8_hgrp_s81 against the OLD group
// ot_hdc_v41x_attn_hgrp_s81 (golden, same ports, same cycles: DELTA 0).  Random stationary loads (both modes, w2v,
// all 5 banks, out-of-range groups), issues, NaN/pad/subnormal elements, every cycle.  Reset contract: rst_n low
// for cycles 0..RST-1, no iv/ld_v until cycle WIN.  From WIN on: ov compared EVERY cycle, oy/oflt on every cycle
// the golden ov is 1 (invalid-cycle data differences are counted separately, informational).
// Prints SVC8LOCK cycles=<n> mismatches=<m> ov=<valid outputs compared> invalid_diff=<k>.
module tb_svc8_hgrp;
    parameter integer NCYC = 20000;
    localparam integer TD = 32, NBANK = 5, PWORDS = 2, H = 16, RST = 4, WIN = 12;
    reg clk = 1'b0;
    always #1 clk = ~clk;
    reg rst_n = 1'b0;
    integer cyc = 0, mism = 0, nov = 0, ninv = 0, i, seed = 1, gidv = 1, ivp = 4, ldp = 3;
    reg [7:0] gid;
    reg ld_v = 0, ld_mode = 0, ld_w2v = 0, iv = 0;
    reg [2:0] ld_bank = 0, ibank = 0;
    reg [7:0] ld_grp = 0;
    reg [PWORDS*TD*16-1:0] ld_w = 0;
    reg [4*2*2*16-1:0] ld_wp = 0;
    reg [TD*18-1:0] ib = 0;
    wire ov_o, ov_n;
    wire [127:0] oy_o, oy_n;
    wire [3:0] of_o, of_n;
    ot_hdc_v41x_attn_hgrp_s81 u_old (.clk(clk), .rst_n(rst_n), .gid(gid), .ld_v(ld_v), .ld_mode(ld_mode),
        .ld_bank(ld_bank), .ld_grp(ld_grp), .ld_w(ld_w), .ld_wp(ld_wp), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank),
        .ib(ib), .ov(ov_o), .oy(oy_o), .oflt(of_o));
    ot_s81svc8_hgrp_s81 u_new (.clk(clk), .rst_n(rst_n), .gid(gid), .ld_v(ld_v), .ld_mode(ld_mode),
        .ld_bank(ld_bank), .ld_grp(ld_grp), .ld_w(ld_w), .ld_wp(ld_wp), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank),
        .ib(ib), .ov(ov_n), .oy(oy_n), .oflt(of_n));
    initial begin
        if ($value$plusargs("seed=%d", seed)) ;
        if ($value$plusargs("gid=%d", gidv)) ;
        if ($value$plusargs("ivp=%d", ivp)) ;     // iv = 1 except 1 in ivp cycles (ivp 0: iv every cycle)
        if ($value$plusargs("ldp=%d", ldp)) ;     // ld_v 1 in ldp cycles
        gid = gidv[7:0];
        i = $urandom(seed);
    end
    function automatic [15:0] rbf16(input integer dummy);
        reg [15:0] x;
        begin
            x = $urandom;
            case ($urandom % 8)
                0: x[14:7] = 8'd0;
                1: x[14:7] = 8'hff;
                2: x[14:7] = 8'd120 + ($urandom % 16);
                default: ;
            endcase
            rbf16 = x;
        end
    endfunction
    function automatic [17:0] relem(input integer dummy);
        reg [17:0] e;
        begin
            e = $urandom;
            e[17] = (($urandom % 16) == 0);
            if (($urandom % 4) == 0) e[15:8] = 8'h7f;
            if (($urandom % 4) == 0) e[7:0] = 8'd127 + ($urandom % 8) - 4;
            relem = e;
        end
    endfunction
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == RST) rst_n <= 1'b1;
        ld_v <= (cyc >= WIN) && (($urandom % ldp) == 0);
        ld_mode <= $urandom % 2;
        ld_w2v <= $urandom % 2;
        ld_bank <= $urandom % NBANK;
        ld_grp <= (($urandom % 8) == 0) ? $urandom : ($urandom % H);
        for (i = 0; i < PWORDS * TD; i = i + 1) ld_w[i*16 +: 16] <= rbf16(0);
        for (i = 0; i < 16; i = i + 1) ld_wp[i*16 +: 16] <= rbf16(0);
        iv <= (cyc >= WIN) && ((ivp == 0) || (($urandom % ivp) != 0));
        ibank <= $urandom % NBANK;
        for (i = 0; i < TD; i = i + 1) ib[i*18 +: 18] <= relem(0);
        if (cyc >= WIN) begin
            if (ov_o) nov <= nov + 1;
            if (ov_o !== ov_n || (ov_o && (oy_o !== oy_n || of_o !== of_n))) begin
                mism <= mism + 1;
                if (mism < 5) $display("MISMATCH cyc=%0d ov %b/%b oy %h / %h of %h / %h", cyc, ov_o, ov_n, oy_o, oy_n,
                                       of_o, of_n);
            end else if (!ov_o && (oy_o !== oy_n || of_o !== of_n)) ninv <= ninv + 1;
        end
        if (cyc == NCYC) begin
            $display("SVC8LOCK cycles=%0d mismatches=%0d ov=%0d invalid_diff=%0d seed=%0d gid=%0d", cyc, mism, nov,
                     ninv, seed, gidv);
            if (mism != 0 || nov == 0) $fatal(1, "SVC8LOCK FAIL mismatches=%0d ov=%0d", mism, nov);
            $finish;
        end
    end
endmodule
