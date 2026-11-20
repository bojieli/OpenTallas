`timescale 1ns/1ps
// KV-PLAN-R2 11-20 (EFAULT-STAGE): equivalence bench of the binder's staged efault form (tools/die_plan/bind_efault_stage.py).
//   staged = per eq bit one reset-less ot_dp_dly_keep #(.W(1), .D(D)) (the bind cell text, bind_pad_tail_split.KEEP_CELL,
//            extracted by run.sh) in front of ot_dp_efault #(.N(N), .AGE(AGE + D)).
//   Claim: staged fault after edge k == the unstaged cell (AGE) fault after edge k - D (0 for k < D), on every edge, and
//   == the cell's own uniform eq pipe ot_dp_efault #(.EQ_PIPE(D)) (same law, different flops).
//   Random stimulus as tb_ot_dp_efault_eqpipe: per run each eq bit rises at a random edge (late = fault), some drop for one
//   edge later (fault), mid-run async resets (the reset-less stations then hold stale values: they must flush before arm).
// MUT 1: stations without the AGE raise; MUT 2: AGE raised by D - 1.  Both must FAIL.
module ot_dp_efault_staged #(parameter integer N = 1, parameter integer AGE = 4, parameter integer D = 1,
                             parameter integer MUT = 0) (
    input wire clk, input wire rst_n, input wire [N-1:0] eq, output wire fault);
    wire [N-1:0] eqs;
    genvar g;
    generate
        for (g = 0; g < N; g = g + 1) begin : g_s
            ot_dp_dly_keep #(.W(1), .D(D)) u_efs (.clk(clk), .d(eq[g]), .q(eqs[g]));
        end
    endgenerate
    localparam integer AGEN = (MUT == 1) ? AGE : (MUT == 2) ? AGE + D - 1 : AGE + D;
    ot_dp_efault #(.N(N), .AGE(AGEN)) u (.clk(clk), .rst_n(rst_n), .eq(eqs), .fault(fault));
endmodule

module stchk #(parameter integer N = 6, parameter integer AGE = 5, parameter integer D = 2, parameter integer MUT = 0) (
    input wire clk, input wire rst_n, input wire [7:0] eq8, output integer errs, output integer nf);
    wire [N-1:0] eq = eq8[N-1:0];
    wire f_st, f_ref, f_pipe;
    ot_dp_efault_staged #(.N(N), .AGE(AGE), .D(D), .MUT(MUT)) s (.clk(clk), .rst_n(rst_n), .eq(eq), .fault(f_st));
    ot_dp_efault #(.N(N), .AGE(AGE)) r (.clk(clk), .rst_n(rst_n), .eq(eq), .fault(f_ref));
    ot_dp_efault #(.N(N), .AGE(AGE), .EQ_PIPE(D)) p (.clk(clk), .rst_n(rst_n), .eq(eq), .fault(f_pipe));
    reg [15:0] dl;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) dl <= 0; else dl <= {dl[14:0], f_ref};
    wire f_exp = dl[D - 1];
    initial begin errs = 0; nf = 0; end
    always @(negedge clk) if (rst_n) begin
        if (f_st !== f_exp) begin errs = errs + 1; if (errs <= 3) $display("MISMATCH N%0d AGE%0d D%0d t%0t staged %b exp %b", N, AGE, D, $time, f_st, f_exp); end
        if (f_st !== f_pipe) begin errs = errs + 1; if (errs <= 3) $display("MISMATCH_PIPE N%0d AGE%0d D%0d t%0t staged %b pipe %b", N, AGE, D, $time, f_st, f_pipe); end
        if (f_st) nf = nf + 1;
    end
endmodule

module tb_ot_dp_efault_stage #(parameter integer MUT = 0);
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg [7:0] eq = 0;
    wire [31:0] e [0:5];
    wire [31:0] nf [0:5];
    stchk #(.N(6), .AGE(5),  .D(2), .MUT(MUT)) c0 (clk, rst_n, eq, e[0], nf[0]);
    stchk #(.N(4), .AGE(0),  .D(1), .MUT(MUT)) c1 (clk, rst_n, eq, e[1], nf[1]);
    stchk #(.N(8), .AGE(3),  .D(4), .MUT(MUT)) c2 (clk, rst_n, eq, e[2], nf[2]);
    stchk #(.N(3), .AGE(7),  .D(3), .MUT(MUT)) c3 (clk, rst_n, eq, e[3], nf[3]);   // the kv3_hub_Wo shape: AGE 7, D 3..4
    stchk #(.N(8), .AGE(7),  .D(4), .MUT(MUT)) c4 (clk, rst_n, eq, e[4], nf[4]);
    stchk #(.N(1), .AGE(13), .D(5), .MUT(MUT)) c5 (clk, rst_n, eq, e[5], nf[5]);
    integer run, k, i, tot;
    integer rise [0:7]; integer drop [0:7];
    initial begin
        tot = 0;
        for (run = 0; run < 600; run = run + 1) begin
            for (i = 0; i < 8; i = i + 1) begin
                rise[i] = $urandom % 20;
                drop[i] = ($urandom % 4 == 0) ? 15 + ($urandom % 30) : -1;
                if ($urandom % 3 != 0) rise[i] = $urandom % 4;
            end
            if ($urandom % 3 == 0) for (i = 0; i < 8; i = i + 1) drop[i] = -1;
            if ($urandom % 4 == 0) for (i = 0; i < 8; i = i + 1) rise[i] = 0;
            // the eq level during reset is random: stale station contents must never reach an armed check
            @(negedge clk); rst_n = 0; eq = $urandom; @(negedge clk); rst_n = 1;
            for (k = 0; k < 50; k = k + 1) begin
                for (i = 0; i < 8; i = i + 1) eq[i] = (k >= rise[i]) && !(drop[i] >= 0 && k == drop[i]);
                @(negedge clk);
            end
        end
        for (i = 0; i < 6; i = i + 1) begin
            tot = tot + e[i];
            if (nf[i] == 0 || nf[i] > 600 * 49 - 100) begin tot = tot + 1; $display("COVERAGE cell %0d fault cycles %0d", i, nf[i]); end
        end
        if (tot == 0) $display("PASS tb_ot_dp_efault_stage MUT %0d (fault cycles %0d %0d %0d %0d %0d %0d)", MUT, nf[0], nf[1], nf[2], nf[3], nf[4], nf[5]);
        else $display("FAIL tb_ot_dp_efault_stage %0d mismatches MUT %0d", tot, MUT);
        $finish;
    end
endmodule
