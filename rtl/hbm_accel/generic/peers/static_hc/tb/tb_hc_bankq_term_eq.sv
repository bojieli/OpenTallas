`timescale 1ns/1ps
`default_nettype none
// F-T 2026-10-19: terminal bank ot_hbm_hc_bankq_term_static (generic) vs the die's canonical terminal master
// ot_hbm_hc_bankq_static (scoped hcb.sv, hcb_*7 params CPI=1 CPO=1). Identical random legal stimulus on every input;
// every RETAINED output (sum_out, f_out, wfault) must be equal (4-state ===) on every cycle. Only o_* (the removed
// forward descriptor) is not compared. +define+TMUT=3 builds the f_out mutant of the terminal (must FAIL).
`ifndef TMUT
`define TMUT 0
`endif
module tb_hc_bankq_term_eq;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg d_v, d_ss, f_in, xb_v, wv, xv, j; reg [6:0] d_nv; reg [9:0] d_wa, d_xa, wa; reg [1:0] xb_beat;
    reg [2047:0] sum_in; reg [255:0] xb_d;
    wire [2047:0] s_ref, s_dut; wire f_ref, f_dut, w_ref, w_dut;
    wire o_v, o_ss; wire [6:0] o_nv; wire [9:0] o_wa, o_xa;
    ot_hbm_hc_bankq_static #(.CPI(1), .CPO(1)) ref_i (.clk(clk), .rst_n(rst_n), .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv),
        .d_wa(d_wa), .d_xa(d_xa), .o_v(o_v), .o_ss(o_ss), .o_nv(o_nv), .o_wa(o_wa), .o_xa(o_xa), .sum_in(sum_in),
        .sum_out(s_ref), .f_in(f_in), .f_out(f_ref), .xb_v(xb_v), .xb_beat(xb_beat), .xb_d(xb_d), .wv(wv), .xv(xv),
        .j(j), .wa(wa), .wfault(w_ref));
    ot_hbm_hc_bankq_term_static #(.MUT(`TMUT), .CPI(1), .CPO(1)) dut_i (.clk(clk), .rst_n(rst_n), .d_v(d_v), .d_ss(d_ss),
        .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa), .sum_in(sum_in), .sum_out(s_dut), .f_in(f_in), .f_out(f_dut),
        .xb_v(xb_v), .xb_beat(xb_beat), .xb_d(xb_d), .wv(wv), .xv(xv), .j(j), .wa(wa), .wfault(w_dut));
    integer cyc = 0, errs = 0, checks = 0, nzsum = 0, fones = 0, wfones = 0;
    task automatic drive;
        d_v = $urandom; d_ss = $urandom; d_nv = $urandom; d_wa = $urandom; d_xa = $urandom; f_in = ($urandom % 8) == 0;
        xb_v = $urandom; xb_beat = $urandom; wv = $urandom; xv = ($urandom % 4) == 0; j = $urandom; wa = $urandom;
        for (integer i = 0; i < 64; i = i + 1) sum_in[i*32 +: 32] = $urandom;
        for (integer i = 0; i < 8; i = i + 1) xb_d[i*32 +: 32] = ($urandom % 3 == 0) ? $urandom : ($urandom & 32'hFFFF0000);
    endtask
    initial begin
        drive();
        repeat (6) @(negedge clk);
        rst_n = 1;
        for (cyc = 0; cyc < 4000; cyc = cyc + 1) begin
            @(negedge clk);
            if (s_ref !== s_dut || f_ref !== f_dut || w_ref !== w_dut) begin
                errs = errs + 1;
                if (errs <= 5) $display("MISMATCH cyc=%0d f %b/%b wfault %b/%b sum_eq=%0d", cyc, f_ref, f_dut, w_ref, w_dut, s_ref === s_dut);
            end
            checks = checks + 1; if (|s_ref) nzsum = nzsum + 1; if (f_ref) fones = fones + 1; if (w_ref) wfones = wfones + 1;
            drive();
        end
        $display("TB_HC_BANKQ_TERM TMUT=%0d checks=%0d mismatches=%0d nonzero_sum_cycles=%0d f_out_ones=%0d wfault_ones=%0d",
                 `TMUT, checks, errs, nzsum, fones, wfones);
        if (errs == 0 && nzsum > 0) $display("PASS tb_hc_bankq_term_eq"); else $display("FAIL tb_hc_bankq_term_eq");
        $finish;
    end
endmodule
`default_nettype wire
