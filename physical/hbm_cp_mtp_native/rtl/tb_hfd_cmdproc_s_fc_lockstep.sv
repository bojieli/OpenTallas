`timescale 1ns/1ps
// mtp-lead 2026-10-10: lockstep bench of the face-clock AR band hfd_cmdproc_s_fc (gen_ar_fc.py) against the adopted
// hfd_cmdproc_s: all four taps on the die clock (as the die tree delivers them), random stimulus on every input and on
// the inout buses (weak drive: each band's own strong drivers win on its output bits), every output bit compared every
// cycle after reset.  Prints LOCKSTEP PASS / FAIL.  Mutant (tools/hbm_mx1_regb_gate.py): the derived band's f_loader
// lockup on the rising edge (one added cycle on f_loader -> xl) must FAIL.
module tb_hfd_cmdproc_s_fc_lockstep #(parameter integer CYC = 3000);
    reg clk = 0; always #5 clk = ~clk;
    reg rst = 1;
    reg [340:0] f_loader = 0; reg [63:0] f_router = 0; reg [15:0] xb = 0;
    reg [826:0] rse = 0, rsw = 0;
    wire [826:0] cSE_a, cSW_a, cSE_b, cSW_b;
    assign (weak0, weak1) cSE_a = rse; assign (weak0, weak1) cSW_a = rsw;
    assign (weak0, weak1) cSE_b = rse; assign (weak0, weak1) cSW_b = rsw;
    wire [63:0] su_e_a, su_w_a, su_e_b, su_w_b; wire [146:0] xl_a, xl_b; wire [15:0] xt_a, xt_b;
    hfd_cmdproc_s a (.cSE(cSE_a), .cSW(cSW_a), .ck(clk), .rst(rst), .f_loader(f_loader), .f_router(f_router),
        .t_su_SE(su_e_a), .t_su_SW(su_w_a), .xb(xb), .xl(xl_a), .xt(xt_a));
    hfd_cmdproc_s_fc b (.cks(clk), .ckn(clk), .cke(clk), .ckw(clk), .cSE(cSE_b), .cSW(cSW_b), .ck(clk), .rst(rst),
        .f_loader(f_loader), .f_router(f_router), .t_su_SE(su_e_b), .t_su_SW(su_w_b), .xb(xb), .xl(xl_b), .xt(xt_b));
    integer i, k, errs = 0, ncmp = 0;
    // random fills through a 32-bit-multiple temporary (a part-select past the return vector's top aborts some vvp builds)
    function [826:0] r827; input integer dummy; integer j; reg [831:0] t; begin for (j = 0; j < 832; j = j + 32) t[j +: 32] = $random; r827 = t[826:0]; end endfunction
    function [340:0] r341; input integer dummy; integer j; reg [351:0] t; begin for (j = 0; j < 352; j = j + 32) t[j +: 32] = $random; r341 = t[340:0]; end endfunction
    initial begin
        repeat (6) @(negedge clk); rst = 0;
        for (i = 0; i < CYC; i = i + 1) begin
            @(negedge clk);
            f_loader = r341(0); f_router = {$random, $random}; xb = $random;
            rse = r827(0); rsw = r827(0);
            @(posedge clk); #1;
            if (i > 8) begin
                ncmp = ncmp + 1;
                if (cSE_a !== cSE_b || cSW_a !== cSW_b || su_e_a !== su_e_b || su_w_a !== su_w_b || xl_a !== xl_b || xt_a !== xt_b) begin
                    errs = errs + 1;
                    if (errs < 4) $display("MISMATCH cyc %0d cSE %0d cSW %0d su %0d/%0d xl %0d xt %0d", i, cSE_a !== cSE_b,
                                           cSW_a !== cSW_b, su_e_a !== su_e_b, su_w_a !== su_w_b, xl_a !== xl_b, xt_a !== xt_b);
                end
            end
        end
        if (errs == 0) $display("LOCKSTEP PASS %0d cycles compared (cSE/cSW 827+827, t_su 64+64, xl 147, xt 16)", ncmp);
        else $display("LOCKSTEP FAIL %0d mismatching cycles", errs);
        $finish;
    end
endmodule
