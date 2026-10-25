`timescale 1ns/1ps
// S81-HEAD HD-TILE (10-21): mini array bench of the head die tile chain on real released head.weight ROM images.
//   ctl (this bench) -> ot_s81hd_spo -> ow: tile t0 -> tile t1 -> ot_s81hd_spr.iw ;  spo.oe -> spr.ie ; spo.o -> spr.i
// The bench drives bus B like ot_s81hd_ctl: go + null best (rv 1, bits -inf, row 1FFFF, flt FLT_IN) in one beat, then
// x slice m at go + 5 + m (xa: K 0..4095, xb: K 4096..5119).  Tile ROM instances t0* / t1* are read from +OT_ROM_DIR
// (the bench script links them to the h* (rows 21888..) / g* (rows 22016..) images per scenario).
// Plusargs: +DIR (xa.hex / xb.hex) +ROW0_0 +ROW0_1 +TEN0 +TEN1 +FLT_IN +XINF_M (slice index whose xa lane 0 is BF16 +Inf;
// -1 none) +NPOS (positions) +GAP (cycles between gos) +EXP_ROW +EXP_BITS (hex) +EXP_FLT +EXP_CYC (-1: no cycle check).
// Prints "POS <n> RES <row> <bits> <flt> <cyc>" per position and "TB_PASS" / "TB_FAIL <why>".
// 10-24: CUT / SPLIT9 select the element adder pipeline (default 0x1ff / 1 = SK 11 = the closed element views, ROM
// images re-skewed by tools/s81_head/hd_reskew_images.py; 0x17b / 0 = SK 8 = the 10-21 images as committed).
module tb_s81hd_mini #(parameter [8:0] CUT = 9'b1_1111_1111, parameter integer SPLIT9 = 1, parameter integer CV = 0,
                       parameter integer AIS = 0, parameter integer MH = 0, parameter integer CS = 0,
                       parameter integer SK = 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8] + SPLIT9);
    reg ck = 1'b0, rst_n = 1'b0;
    always #0.5 ck = ~ck;
    reg  [564:0] bi = '0;
    wire [564:0] so, sw, se, t0o, t1o, ro;
    integer row0_0, row0_1, ten0, ten1, flt_in, xinf_m, npos, gap, exp_row, exp_flt, exp_cyc;
    reg [31:0] exp_bits;
    reg [16:0] r0_0, r0_1;
    reg t0en, t1en;
    ot_s81hd_spo u_spo (.ck(ck), .rst_n(rst_n), .i(bi), .o(so), .ow(sw), .oe(se));
    ot_s81hd_tile #(.INSTANCE("t0"), .CUT(CUT), .SPLIT9(SPLIT9), .CV(CV), .A_INPUT_STAGES(AIS), .MERGE_HOP(MH), .CMP_STAGES(CS)) u_t0 (.ck(ck), .rst_n(rst_n), .i(sw), .o(t0o), .row0(r0_0), .ten(t0en));
    ot_s81hd_tile #(.INSTANCE("t1"), .CUT(CUT), .SPLIT9(SPLIT9), .CV(CV), .A_INPUT_STAGES(AIS), .MERGE_HOP(MH), .CMP_STAGES(CS)) u_t1 (.ck(ck), .rst_n(rst_n), .i(t0o), .o(t1o), .row0(r0_1), .ten(t1en));
    ot_s81hd_spr u_spr (.ck(ck), .rst_n(rst_n), .i(so), .iw(t1o), .ie(se), .o(ro));
    reg [255:0] ma [0:255];
    reg [255:0] mb [0:63];
    reg [8*1024-1:0] dir;
    integer cyc = 0, g0 = 0, m, pos, nres = 0, bad = 0;
    always @(posedge ck) cyc <= cyc + 1;
    // output monitor: one result per position, fire-once
    always @(negedge ck) if (rst_n && ro[514]) begin
        $display("POS %0d RES %0d %08h %0d %0d", nres, ro[531:515], ro[563:532], ro[564], cyc - g0);
        if (ro[531:515] !== exp_row[16:0] && exp_row >= 0) begin $display("TB_FAIL row %0d != %0d", ro[531:515], exp_row); bad = bad + 1; end
        if (ro[563:532] !== exp_bits && exp_row >= 0) begin $display("TB_FAIL bits %08h != %08h", ro[563:532], exp_bits); bad = bad + 1; end
        if (ro[564] !== exp_flt[0]) begin $display("TB_FAIL flt %0d != %0d", ro[564], exp_flt); bad = bad + 1; end
        if (exp_cyc >= 0 && cyc - g0 != exp_cyc) begin $display("TB_FAIL cycles %0d != %0d", cyc - g0, exp_cyc); bad = bad + 1; end
        nres = nres + 1;
    end
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR");
        if (!$value$plusargs("ROW0_0=%d", row0_0)) row0_0 = 21888;
        if (!$value$plusargs("ROW0_1=%d", row0_1)) row0_1 = 22016;
        if (!$value$plusargs("TEN0=%d", ten0)) ten0 = 1;
        if (!$value$plusargs("TEN1=%d", ten1)) ten1 = 1;
        if (!$value$plusargs("FLT_IN=%d", flt_in)) flt_in = 0;
        if (!$value$plusargs("XINF_M=%d", xinf_m)) xinf_m = -1;
        if (!$value$plusargs("NPOS=%d", npos)) npos = 1;
        if (!$value$plusargs("GAP=%d", gap)) gap = 9000;
        if (!$value$plusargs("EXP_ROW=%d", exp_row)) exp_row = -1;
        if (!$value$plusargs("EXP_BITS=%h", exp_bits)) exp_bits = 32'h0;
        if (!$value$plusargs("EXP_FLT=%d", exp_flt)) exp_flt = 0;
        if (!$value$plusargs("EXP_CYC=%d", exp_cyc)) exp_cyc = -1;
        r0_0 = row0_0[16:0]; r0_1 = row0_1[16:0]; t0en = ten0[0]; t1en = ten1[0];
        $readmemh({dir, "/xa.hex"}, ma);
        $readmemh({dir, "/xb.hex"}, mb);
        repeat (4) @(negedge ck);
        rst_n = 1'b1;
        repeat (8) @(negedge ck);
        for (pos = 0; pos < npos; pos = pos + 1) begin
            // go + null best, then the x slices
            g0 = cyc;
            bi = '0;
            bi[512] = 1'b1; bi[513] = 1'b1; bi[514] = 1'b1; bi[531:515] = 17'h1FFFF; bi[563:532] = 32'hFF800000; bi[564] = flt_in[0];
            @(negedge ck);
            bi[514] = 1'b0; bi[512] = 1'b0;
            for (m = 0; m < 8192 + 7 * SK + 8; m = m + 1) begin
                while (cyc - g0 != 5 + m) @(negedge ck);
                bi[255:0] = ma[m % 256]; bi[511:256] = mb[m % 64];
                if (m == xinf_m) bi[15:0] = 16'h7F80;
            end
            bi[513] = 1'b0;
            while (nres < pos + 1 && cyc - g0 < gap) @(negedge ck);
            while (cyc - g0 < gap) @(negedge ck);
        end
        repeat (200) @(negedge ck);
        if (nres != npos) begin $display("TB_FAIL results %0d != positions %0d", nres, npos); bad = bad + 1; end
        if (bad == 0) $display("TB_PASS positions %0d", npos); else $display("TB_FAIL %0d mismatches", bad);
        $finish;
    end
    initial begin #400000; $display("TB_FAIL TIMEOUT"); $finish; end
endmodule
