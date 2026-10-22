`timescale 1ns/1ps
// RTLGAP2-HEADTB (10-21) CUT-A of the per-tile hierarchical head-die token TB (G-HEAD-DIE-TB).
// ONE ot_s81hd_tile of the bound head die, full RTL (pin registers, ot_s81hd_bundle = 5 elements + 10 x
// ot_rom_4096x274_m8 with the released DeepSeek-V4.1 head.weight rank-0 image of that die instance, chain-best merge),
// with the die's exact tile parameters (#(.IOREG(1), .INSTANCE)) and the die strap row0 / ten 1.  Bus B is driven as
// ot_s81hd_ctl / ot_s81hd_spo deliver it: go + null chain best (rv 1, row 1FFFF, bits -inf) at G, xv 1, x slice m at
// G + 5 + m (xa K 0..4095 = xa.hex[m % 256], xb K 4096..5119 = xb.hex[m % 64]) for m < NSLICE.
// Checks (bit-exact): every formed logit (element l_v / l_d, 128) = golden logit of that row (+LG, local row order);
// the tile output best (row / bits / flt) = golden argmax of the tile's 128 rows (lowest id on ties).
// Records the ot_s81hd_bundle OUTPUT face for CUT-B (die): "REC <lat go->res_v> <res_row> <res_bits> <fault>".
// Plusargs: +DIR (xa.hex / xb.hex) +LG (128 x 32 b hex) +ROW0 +EXP_ROW +EXP_BITS +OT_ROM_DIR (t*.viamap.hex).
module tb_s81hd_tilecut #(parameter integer NSLICE = 8248);
    reg ck = 1'b0, rst_n = 1'b0;
    always #0.5 ck = ~ck;
    reg  [564:0] bi = '0;
    wire [564:0] to;
    reg  [16:0]  r0 = 17'd0;
    ot_s81hd_tile #(.IOREG(1), .INSTANCE("t")) u_t (.ck(ck), .rst_n(rst_n), .i(bi), .o(to), .row0(r0), .ten(1'b1));

    reg [31:0] lg [0:127];
    integer lgn [0:3];
    integer lok = 0, lnum = 0;
    initial begin : z integer q; for (q = 0; q < 4; q = q + 1) lgn[q] = 0; end
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_lchk
        always @(negedge ck) if (rst_n && u_t.u_b.g_a[gq].lv) begin
            lnum = lnum + 1;
            if (u_t.u_b.g_a[gq].ld === lg[32 * gq + (lgn[gq] % 32)]) lok = lok + 1;
            else if (lnum - lok < 8) $display("LOGIT_MISMATCH row %0d %08h != %08h", 32 * gq + (lgn[gq] % 32),
                                              u_t.u_b.g_a[gq].ld, lg[32 * gq + (lgn[gq] % 32)]);
            lgn[gq] = lgn[gq] + 1;
        end
    end endgenerate

    reg [255:0] ma [0:255];
    reg [255:0] mb [0:63];
    reg [8*1024-1:0] dir, lgf;
    integer row0, exp_row, cyc = 0, g0 = 0, gb = -1, m, bad = 0, nres = 0, nrec = 0;
    reg [31:0] exp_bits;
    reg rv_d = 1'b0;
    always @(posedge ck) cyc <= cyc + 1;
    // bundle face: go edge and the first res_v edge after it (recorded for the die cut's replay shim)
    always @(negedge ck) if (rst_n) begin
        if (u_t.u_b.go && gb < 0) gb = cyc;
        rv_d <= u_t.u_b.res_v;
        if (u_t.u_b.res_v && !rv_d && gb >= 0) begin
            $display("REC %0d %0d %08h %0d", cyc - gb, u_t.u_b.res_row, u_t.u_b.res_bits, u_t.u_b.fault);
            nrec = nrec + 1;
        end
        if (to[514]) begin
            $display("TILE_OUT row %0d bits %08h flt %0d at %0d", to[531:515], to[563:532], to[564], cyc - g0);
            if (to[531:515] !== exp_row[16:0]) begin $display("FAIL tilecut row %0d != %0d", to[531:515], exp_row); bad = bad + 1; end
            if (to[563:532] !== exp_bits) begin $display("FAIL tilecut bits %08h != %08h", to[563:532], exp_bits); bad = bad + 1; end
            if (to[564] !== 1'b0) begin $display("FAIL tilecut flt"); bad = bad + 1; end
            nres = nres + 1;
        end
    end
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR");
        if (!$value$plusargs("LG=%s", lgf)) $fatal(1, "+LG");
        if (!$value$plusargs("ROW0=%d", row0)) $fatal(1, "+ROW0");
        if (!$value$plusargs("EXP_ROW=%d", exp_row)) $fatal(1, "+EXP_ROW");
        if (!$value$plusargs("EXP_BITS=%h", exp_bits)) $fatal(1, "+EXP_BITS");
        r0 = row0[16:0];
        $readmemh({dir, "/xa.hex"}, ma);
        $readmemh({dir, "/xb.hex"}, mb);
        $readmemh(lgf, lg);
        repeat (4) @(negedge ck);
        rst_n = 1'b1;
        repeat (8) @(negedge ck);
        g0 = cyc;
        bi = '0;
        bi[512] = 1'b1; bi[513] = 1'b1; bi[514] = 1'b1; bi[531:515] = 17'h1FFFF; bi[563:532] = 32'hFF800000;
        @(negedge ck);
        bi[514] = 1'b0; bi[512] = 1'b0;
        for (m = 0; m < NSLICE; m = m + 1) begin
            while (cyc - g0 != 5 + m) @(negedge ck);
            bi[255:0] = ma[m % 256]; bi[511:256] = mb[m % 64];
        end
        @(negedge ck);
        bi[513] = 1'b0;
        while (nres == 0 && cyc - g0 < 12000) @(negedge ck);
        repeat (50) @(negedge ck);
        $display("LOGITS %0d/%0d", lok, lnum);
        if (lok != lnum || lnum != 128) begin $display("FAIL tilecut logits %0d/%0d (expect 128/128)", lok, lnum); bad = bad + 1; end
        if (nres != 1) begin $display("FAIL tilecut tile outputs %0d != 1", nres); bad = bad + 1; end
        if (nrec != 1) begin $display("FAIL tilecut bundle results %0d != 1", nrec); bad = bad + 1; end
        if (bad == 0) $display("PASS tilecut row0 %0d best %0d %08h", row0, exp_row, exp_bits);
        else $display("FAIL tilecut errors %0d", bad);
        $finish;
    end
    initial begin #40000; $display("FAIL tilecut timeout"); $finish; end
endmodule
