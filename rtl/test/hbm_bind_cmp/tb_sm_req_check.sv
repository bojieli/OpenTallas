`timescale 1ns/1ps
`default_nettype none
// HBM-BIND-CMP 2026-10-26: bench of ot_hbm_sm_req_check (the SM request vs scheduled expected_request sticky check).
// Model (cycle-exact to the RTL it stands for): sm_command c(t) leaves the group; the group's S1 copy gives
// expected_request(t) = c(t-1) (ot_smh_static_feed); the SM gives request(t) = c(t - LS - 2) (QSPLIT landing + front
// register), arriving LR edges later through stations WITHOUT reset (garbage after reset).  DUT RQD = LS + LR + 2.
// Phases: P1 matched traffic (incl. invalid words with random address bits) -> clear; P2 one corrupted address bit on a
// valid word -> sticky set and held; P3 host clear -> clear and stays clear; P4 schedule off: both valid bits 0 with
// differing address/tag -> clear; P5 spurious SM valid -> set.  MUT 1/2/3 must make the bench FAIL.
module tb_sm_req_check;
    parameter integer LS = 3, LR = 4, MUT = 0;
    localparam integer RQD = LS + LR + 2;
    localparam integer SMD = LS + 2 + LR;          // c -> sm_req at the check input
    reg clk = 0, rst_n = 0, clr = 0;
    always #1 clk = ~clk;
    reg  [42:0] c, exp_req;
    reg  [42:0] pipe [0:SMD-1];
    reg  [42:0] corrupt;                            // XOR on the SM side (the fault being detected)
    reg         sched_off;                          // P4: SM side differs only in address/tag of invalid words
    wire [42:0] sm_req = pipe[SMD-1] ^ corrupt;
    wire mismatch;
    ot_hbm_sm_req_check #(.RQD(RQD), .MUT(MUT)) dut(.clk(clk), .rst_n(rst_n), .clr(clr), .exp_req(exp_req),
        .sm_req(sm_req), .mismatch(mismatch));
    integer k, errs = 0, seed = 7;
    // stations have no reset: start with garbage
    initial for (k = 0; k < SMD; k = k + 1) pipe[k] = {$random(seed), $random(seed)};
    always @(posedge clk) begin
        exp_req <= c;
        pipe[0] <= c;
        for (k = 1; k < SMD; k = k + 1) pipe[k] <= pipe[k-1];
    end
    task step(input integer n); integer j; begin for (j = 0; j < n; j = j + 1) begin
        c = {$random(seed), $random(seed)};
        c[42] = $random(seed) & 1;
        if (sched_off) c[42] = 1'b0;
        @(posedge clk); #0.1; end end endtask
    task expect_m(input v, input [127:0] what); begin
        if (mismatch !== v) begin errs = errs + 1; $display("ERR %0s: mismatch=%b want %b at %0t", what, mismatch, v, $time); end
    end endtask
    initial begin
        c = 0; exp_req = 0; corrupt = 0; sched_off = 0;
        repeat (3) @(posedge clk); #0.1 rst_n = 1;
        // P1 matched random traffic
        step(200); expect_m(0, "P1 matched");
        // P2 one corrupted address bit on a valid word, for exactly one SM-side edge
        wait_valid_at_sm();
        corrupt = 43'h1 << 17; @(posedge clk); #0.1 corrupt = 0;
        step(RQD + 4); expect_m(1, "P2 mismatch sticky");
        step(100); expect_m(1, "P2 held");
        // P3 host clear
        clr = 1; @(posedge clk); #0.1 clr = 0; step(150); expect_m(0, "P3 cleared + matched");
        // P4 schedule off: no valid words; SM side address/tag bits differ
        sched_off = 1; step(SMD + 2);
        corrupt = 43'h2_0000_0005; step(80); expect_m(0, "P4 schedule off");
        corrupt = 0; step(SMD + 4); sched_off = 0; step(60); expect_m(0, "P4 back to matched");
        // P5 spurious SM valid (scheduled invalid)
        wait_invalid_at_sm();
        corrupt = 43'h400_0000_0000; @(posedge clk); #0.1 corrupt = 0;
        step(RQD + 4); expect_m(1, "P5 spurious valid");
        if (errs == 0) $display("TB_SM_REQ_CHECK MUT=%0d LS=%0d LR=%0d RQD=%0d PASS", MUT, LS, LR, RQD);
        else           $display("TB_SM_REQ_CHECK MUT=%0d LS=%0d LR=%0d RQD=%0d FAIL errs=%0d", MUT, LS, LR, RQD, errs);
        $finish;
    end
    task wait_valid_at_sm; begin while (pipe[SMD-1][42] !== 1'b1) step(1); end endtask
    task wait_invalid_at_sm; begin while (pipe[SMD-1][42] !== 1'b0) step(1); end endtask
endmodule
`default_nettype wire
