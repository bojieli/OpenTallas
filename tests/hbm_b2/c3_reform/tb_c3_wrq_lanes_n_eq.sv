`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-61/RTL-C3 11-03: LOCKSTEP new ot_hbm_sm_vm_wr_q_lanes_n (pop/last from flops) vs the origin/main copy
// (renamed *_old).  Cycle-shift map: every output 0 edges.  NL 4, LBPIN 1, NB2 2 (the t_lanes4 config) and NL 8 NB2 1.
// Random SM rows, descriptors (P 0..15 incl. fault cases), bursts, back-to-back descriptors, resets mid-run.
module tb_c3_wrq_lanes_n_eq;
    parameter integer NL = 4, NB2 = 2, LBPIN = 1, NCYC = 40000, SEED = 1;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0; reg [1:0] quad = 1; reg lbase = 1;
    reg [NL-1:0] rv = 0; reg [12*NL-1:0] rrow = 0; reg [256*NL-1:0] rdata = 0;
    reg cmd_v = 0; reg [25+NB2-1:0] cmd = 0; reg [NL-1:0] smf = 0, sms = 0;
    wire [NB2*281*NL-1:0] wq_n, wq_o; wire busy_n, busy_o, fault_n, fault_o;
    ot_hbm_sm_vm_wr_q_lanes_n #(.DEPTH(4), .NL(NL), .LB(0), .LBPIN(LBPIN), .NB2(NB2)) u_new(.clk(clk), .clk_l({NL{clk}}),
        .rst_n(rst_n), .quad(quad), .lbase(lbase), .rv(rv), .rrow(rrow), .rdata(rdata), .cmd_v(cmd_v), .cmd(cmd),
        .sm_fault(smf), .sm_sched_fault(sms), .wq(wq_n), .busy(busy_n), .fault(fault_n));
    ot_hbm_sm_vm_wr_q_lanes_n_old #(.DEPTH(4), .NL(NL), .LB(0), .LBPIN(LBPIN), .NB2(NB2)) u_old(.clk(clk), .clk_l({NL{clk}}),
        .rst_n(rst_n), .quad(quad), .lbase(lbase), .rv(rv), .rrow(rrow), .rdata(rdata), .cmd_v(cmd_v), .cmd(cmd),
        .sm_fault(smf), .sm_sched_fault(sms), .wq(wq_o), .busy(busy_o), .fault(fault_o));
    integer cyc = 0, errs = 0, checks = 0, wqv = 0, seed = SEED, i, k, burst = 0, mode = 0;
    always @(negedge clk) begin
        cyc = cyc + 1;
        if (cyc > 6) begin
            checks = checks + 1;
            if (wq_n !== wq_o || busy_n !== busy_o || fault_n !== fault_o) begin
                errs = errs + 1;
                if (errs < 5) $display("MISMATCH cyc %0d busy %b/%b fault %b/%b", cyc, busy_n, busy_o, fault_n, fault_o);
            end
            for (k = 0; k < NB2*NL; k = k + 1) if (wq_o[k*281+280]) wqv = wqv + 1;
        end
        // stimulus
        rst_n = !((cyc < 4) || (($random(seed) & 4095) == 0));
        if ((cyc % 3000) == 0) mode = $random(seed) & 3;
        cmd_v = 0;
        if (($random(seed) & 255) < ((mode == 0) ? 2 : 6)) begin
            cmd_v = 1;
            cmd = $random(seed);
            cmd[23:20] = (($random(seed) & 7) == 0) ? ($random(seed) & 15) : (1 + (($random(seed) & 7)));
        end
        if (burst == 0 && ($random(seed) & 63) < 8) burst = 1 + ($random(seed) & 15);
        for (k = 0; k < NL; k = k + 1) begin
            rv[k] = (burst != 0) && (($random(seed) & 3) != 0 || mode == 3);
            rrow[12*k +: 12] = $random(seed);
            for (i = 0; i < 8; i = i + 1) rdata[256*k + 32*i +: 32] = $random(seed);
        end
        if (burst != 0) burst = burst - 1;
        smf = (($random(seed) & 8191) == 0) ? ($random(seed) & ((1 << NL) - 1)) : 0;
        sms = 0;
        if (cyc >= NCYC) begin
            $display("C3_WRQ_EQ NL %0d NB2 %0d checks %0d errors %0d wq_valid %0d %s", NL, NB2, checks, errs, wqv,
                     (errs == 0 && wqv > 100) ? "PASS" : "FAIL");
            if (errs != 0 || wqv <= 100) $fatal(1, "FAIL");
            $finish;
        end
    end
endmodule
`default_nettype wire
