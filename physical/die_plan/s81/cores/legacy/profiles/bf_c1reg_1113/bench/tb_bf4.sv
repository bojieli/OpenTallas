`timescale 1ns/1ps
// GUNIT-CORE-1 11-13 lock-step bench: bf gf4 (OT_GUNIT_BF_M1REG + OT_GUNIT_BF_C1REG) outputs == gf3 outputs delayed NDLY
// edges (expected NDLY 1; NDLY 0 / 2 and the C1REG_MUT mutant must FAIL), random stimulus, warm reset pulse every 400
// cycles (copy of profiles/bf_m1reg_1108/bench/tb_bf.sv)
module tb_bf4;
    reg clk = 0, rst_n = 0;
    reg [5:0] sa_r, sb_r; reg [223:0] sa_d, sb_d; reg [13:0] we; reg c_go, c_fw, c_l; reg [2:0] c_bn; reg [4:0] c_lvn;
    reg g_go; reg [5:0] g_hit; reg [41:0] g_a; reg [327:0] s0a, s0b, s1a, s1b; reg [2:0] sf0; reg [23:0] vf_lo, vf_hi;
    wire [255:0] gsl, gsh, nsl, nsh; wire [13:0] gcl, gch, ncl, nch;
    wire gv, gf, gl, gg, gflt, nv, nf, nl, ng, nflt; wire [244:0] gd, nd;
    gold_bf3 u_gold (.clk(clk), .rst_n(rst_n), .sa_r(sa_r), .sa_d(sa_d), .sb_r(sb_r), .sb_d(sb_d), .we(we), .c_go(c_go), .c_fw(c_fw),
        .c_l(c_l), .c_bn(c_bn), .c_lvn(c_lvn), .g_go(g_go), .g_hit(g_hit), .g_a(g_a), .sv_lo(gsl), .sv_hi(gsh), .ctl_lo(gcl),
        .ctl_hi(gch), .s0a(s0a), .s0b(s0b), .sf0(sf0), .vf_lo(vf_lo), .s1a(s1a), .s1b(s1b), .vf_hi(vf_hi), .o_v(gv), .o_f(gf),
        .o_l(gl), .o_g(gg), .o_d(gd), .o_flt(gflt));
    dsdv_gunit_l1f_bf u_new (.clk(clk), .rst_n(rst_n), .sa_r(sa_r), .sa_d(sa_d), .sb_r(sb_r), .sb_d(sb_d), .we(we), .c_go(c_go), .c_fw(c_fw),
        .c_l(c_l), .c_bn(c_bn), .c_lvn(c_lvn), .g_go(g_go), .g_hit(g_hit), .g_a(g_a), .sv_lo(nsl), .sv_hi(nsh), .ctl_lo(ncl),
        .ctl_hi(nch), .s0a(s0a), .s0b(s0b), .sf0(sf0), .vf_lo(vf_lo), .s1a(s1a), .s1b(s1b), .vf_hi(vf_hi), .o_v(nv), .o_f(nf),
        .o_l(nl), .o_g(ng), .o_d(nd), .o_flt(nflt));
`ifndef NDLY
`define NDLY 1
`endif
    reg [249:0] gq; reg [249:0] gq1;   // gold outputs NDLY edges later
    generate if (`NDLY == 0) begin : g_d0 always @(*) gq = {gv, gf, gl, gg, gflt, gd}; end
    else if (`NDLY == 1) begin : g_d1 always @(posedge clk) gq <= {gv, gf, gl, gg, gflt, gd}; end
    else begin : g_d2 always @(posedge clk) begin gq1 <= {gv, gf, gl, gg, gflt, gd}; gq <= gq1; end end endgenerate
    integer cyc = 0, bad = 0, cmp = 0, dcmp = 0, nflt1 = 0, ngath = 0, nval = 0;
    function [31:0] r32; input x; r32 = $random; endfunction
    task rnd; integer q; begin
        sa_r = $random; sb_r = $random; we = ($random % 4 == 0) ? $random : 0; c_go = ($random % 3 == 0); c_fw = $random; c_l = $random;
        c_bn = $random; c_lvn = $random; g_go = ($random % 5 == 0); g_hit = $random; g_a = {$random, $random};
        for (q = 0; q < 7; q = q + 1) begin sa_d[32*q +: 32] = $random; sb_d[32*q +: 32] = $random; end
        for (q = 0; q < 11; q = q + 1) begin s0a[32*q +: 32] = $random; s0b[32*q +: 32] = $random; s1a[32*q +: 32] = $random; s1b[32*q +: 32] = $random; end
        sf0 = $random; vf_lo = ($random % 50 == 0) ? $random : 0; vf_hi = ($random % 50 == 0) ? $random : 0;
    end endtask
    always #5 clk = ~clk;
    initial begin
        rnd;
        repeat (6) @(negedge clk) rnd;
        rst_n = 1;
        repeat (`NCYC) begin
            @(negedge clk);
            cyc = cyc + 1;
            // a reset pulse every 400 cycles (o_flt is sticky); no compare for 4 edges around each pulse
            if (cyc % 400 == 0) rst_n = 0; else if (cyc % 400 == 2) rst_n = 1;
            if ((cyc % 400) > 7) begin
                // control outputs are reset flops: compare exactly; o_d only where the gold bit is known
                cmp = cmp + 1;
                if ({nv, nf, nl, ng, nflt} !== gq[249:245]) begin bad = bad + 1; if (bad < 5) $display("CTL MISMATCH cyc %0d new %b gold %b", cyc, {nv,nf,nl,ng,nflt}, gq[249:245]); end
                if (^gq[244:0] !== 1'bx) begin dcmp = dcmp + 1; if (nd !== gq[244:0]) begin bad = bad + 1; if (bad < 5) $display("DATA MISMATCH cyc %0d", cyc); end end
                if ({nsl, nsh, ncl, nch} !== {gsl, gsh, gcl, gch}) begin bad = bad + 1; if (bad < 5) $display("SV MISMATCH cyc %0d", cyc); end
                nflt1 = nflt1 + gq[245]; ngath = ngath + gq[246]; nval = nval + gq[249];
            end
            rnd;
        end
        $display("BENCH cycles %0d compares %0d data_compares %0d valid %0d gather %0d flt %0d mismatches %0d -> %s", cyc, cmp, dcmp, nval, ngath, nflt1, bad, bad == 0 ? "PASS" : "FAIL");
        $finish;
    end
endmodule
