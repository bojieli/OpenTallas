import sys, re, pathlib
fit = pathlib.Path(sys.argv[1]).read_text(); out = pathlib.Path(sys.argv[2])
a = fit.index("    // S81-CORES-R 11-16 (COORD): ring depth MQ_D")
b = fit.index(".wd({{(256-MW-1){1'b0}}, k_v, k_it[24:3]}));", a); b = fit.index("\n", b) + 1
c = fit.index("    // S81-CORES-R 11-16: u_mq ring output"); d = fit.index("end endgenerate", c) + len("end endgenerate\n")
ring, tail = fit[a:b], fit[c:d]
dut = f"""`timescale 1ns/1ps
// bench DUT: the u_mq ring + tail text cut verbatim from the generated dsdv_idx_rg3_nq_native_fit.sv
module mq_new #(parameter integer EL = 140, parameter integer KR = 0, parameter bit SRAM_MACRO = 1) (
    input wire ck, input wire [9:0] mw, input wire k_v, input wire [24:0] k_it, output wire [255:0] mq_q);
    localparam integer MW = 22;
    wire [255:0] mq_q_unused;
{ring}{tail}endmodule
// reference: the pre-fit 1024-deep form (read EL + KR - 1 behind, no tail)
module mq_ref #(parameter integer EL = 140, parameter integer KR = 0) (
    input wire ck, input wire [9:0] mw, input wire k_v, input wire [24:0] k_it, output wire [255:0] mq_q);
    localparam integer MW = 22;
    dsdv_idx_fit_mem #(.SRAM_MACRO(0), .WORDS(1024), .BITS(MW + 1)) u_mq (
        .ck(ck), .re(1'b1), .ra(mw - 10'(EL + KR - 1)), .rd(mq_q), .we(1'b1), .wa(mw),
        .wd({{{{(256-MW-1){{1'b0}}}}, k_v, k_it[24:3]}}));
endmodule
module tb;
    reg ck = 0; always #1 ck = ~ck;
    reg [9:0] mw = 0; reg k_v = 0; reg [24:0] k_it = 0;
    wire [255:0] qn140, qr140, qn124, qr124, qn124m;
    mq_new #(.EL(140)) n140 (.ck(ck), .mw(mw), .k_v(k_v), .k_it(k_it), .mq_q(qn140));
    mq_ref #(.EL(140)) r140 (.ck(ck), .mw(mw), .k_v(k_v), .k_it(k_it), .mq_q(qr140));
    mq_new #(.EL(124)) n124 (.ck(ck), .mw(mw), .k_v(k_v), .k_it(k_it), .mq_q(qn124));
    mq_ref #(.EL(124)) r124 (.ck(ck), .mw(mw), .k_v(k_v), .k_it(k_it), .mq_q(qr124));
    reg [22:0] hist [0:4095]; integer t, err140 = 0, err124 = 0, errd = 0, n = 0, dly = -1, j;
    always @(posedge ck) begin
        hist[t % 4096] <= {{k_v, k_it[24:3]}};
        mw <= mw + 10'd1; k_v <= $random; k_it <= $random; t <= t + 1;
    end
    initial t = 0;
    always @(negedge ck) if (t > 200) begin
        n = n + 1;
        if (qn140 !== qr140) err140 = err140 + 1;
        if (qn124 !== qr124) err124 = err124 + 1;
        // absolute depth: qn140 must equal the word written 139 writes before the newest completed one, +1 read reg
        if (qn140[22:0] !== hist[(t - 1 - 139) % 4096]) errd = errd + 1;
        if (qn140[255:23] !== 0) errd = errd + 1;
    end
    initial begin
        #12000;
        // find delay by search on the last sample
        for (j = 100; j < 200; j = j + 1) if (dly < 0 && qr140[22:0] === hist[(t - 1 - j) % 4096] && qn140[22:0] === hist[(t - 1 - j) % 4096]) dly = j;
        $display("MQBENCH samples=%0d EL140_vs_ref_mismatch=%0d EL124_vs_ref_mismatch=%0d EL140_depth139_mismatch=%0d first_match_lag=%0d tail_stages=%0d",
                 n, err140, err124, errd, dly, n140.MQ_T);
        $finish;
    end
endmodule
"""
out.write_text(dut)
