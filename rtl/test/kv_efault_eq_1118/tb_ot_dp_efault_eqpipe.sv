`timescale 1ns/1ps
// KV-EFAULT-EQ 11-18: equivalence bench of the eq input pipe of ot_dp_efault (EQ_PIPE, EQ_PIPE_V).
//   ref0   = a verbatim copy of the cell as it was before the pipe (ot_dp_efault_ref0, HEAD 33541dd09f1).
//   EQ_PIPE = 0, EQ_PIPE_V = 0 : cycle-exact equal to ref0 (same N, AGE) on every edge.
//   bit i with depth D_i = EQ_PIPE + EQ_PIPE_V[4i+:4]: fault = OR_i ( ref0 over bit i alone, AGE, delayed by D_i edges );
//   uniform depth P (V = 0): fault = ref0 (all N bits, AGE) delayed by P edges.
//   Random stimulus: per run every eq bit rises at a random edge 0..AGE+5 (some after the age: faults), some bits drop for
//   one edge later (faults), random mid-run async resets.  Both fault and no-fault outcomes must occur (coverage check).
// MUT 1: expected delay D_i + 1 (a check one edge off); MUT 2: the pipe without the AGE raise (ot_dp_efault_noage). Both must FAIL.
module ot_dp_efault_ref0 #(parameter integer N = 1, parameter integer AGE = 4) (
    input wire clk, input wire rst_n, input wire [N-1:0] eq, output reg fault);
    localparam integer CW = (AGE < 1) ? 1 : $clog2(AGE + 1);
    localparam [CW-1:0] AGEW = AGE[CW-1:0];
    reg [CW-1:0] cnt;
    wire armed = (cnt == AGEW);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cnt <= {CW{1'b0}}; fault <= 1'b0; end
        else begin if (!armed) cnt <= cnt + 1'b1; fault <= fault | (armed & ~&eq); end
endmodule

// mutant: the pipe flops, AGE not raised
module ot_dp_efault_noage #(parameter integer N = 1, parameter integer AGE = 4, parameter integer EQ_PIPE = 0,
                            parameter [4*N-1:0] EQ_PIPE_V = {4*N{1'b0}}) (
    input wire clk, input wire rst_n, input wire [N-1:0] eq, output wire fault);
    reg [N-1:0] q [0:15];
    integer i, k;
    reg [N-1:0] e;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) for (k = 0; k < 16; k = k + 1) q[k] <= 0;
        else begin q[0] <= eq; for (k = 1; k < 16; k = k + 1) q[k] <= q[k-1]; end
    always @* for (i = 0; i < N; i = i + 1) e[i] = (EQ_PIPE + EQ_PIPE_V[4*i +: 4] == 0) ? eq[i] : q[EQ_PIPE + EQ_PIPE_V[4*i +: 4] - 1][i];
    ot_dp_efault_ref0 #(.N(N), .AGE(AGE)) u (.clk(clk), .rst_n(rst_n), .eq(e), .fault(fault));
endmodule

module eqchk #(parameter integer N = 6, parameter integer AGE = 5, parameter integer P = 0,
               parameter [4*N-1:0] V = {4*N{1'b0}}, parameter integer MUT = 0) (
    input wire clk, input wire rst_n, input wire [7:0] eq8, output integer errs, output integer nf);
    wire [N-1:0] eq = eq8[N-1:0];
    wire f_dut, f_ref0;
    generate
        if (MUT == 2) begin : g_m
            ot_dp_efault_noage #(.N(N), .AGE(AGE), .EQ_PIPE(P), .EQ_PIPE_V(V)) d (.clk(clk), .rst_n(rst_n), .eq(eq), .fault(f_dut));
        end else begin : g_d
            ot_dp_efault #(.N(N), .AGE(AGE), .EQ_PIPE(P), .EQ_PIPE_V(V)) d (.clk(clk), .rst_n(rst_n), .eq(eq), .fault(f_dut));
        end
    endgenerate
    ot_dp_efault_ref0 #(.N(N), .AGE(AGE)) r (.clk(clk), .rst_n(rst_n), .eq(eq), .fault(f_ref0));
    // per bit reference, delayed D_i (+1 for MUT 1)
    wire [N-1:0] fb;
    reg  [N-1:0] fexp_bits;
    genvar g;
    generate
        for (g = 0; g < N; g = g + 1) begin : g_b
            localparam integer D = P + V[4*g +: 4] + ((MUT == 1) ? 1 : 0);
            ot_dp_efault_ref0 #(.N(1), .AGE(AGE)) rb (.clk(clk), .rst_n(rst_n), .eq(eq[g]), .fault(fb[g]));
            reg [15:0] dl;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) dl <= 0; else dl <= {dl[14:0], fb[g]};
            always @* fexp_bits[g] = (D == 0) ? fb[g] : dl[(D == 0) ? 0 : D - 1];
        end
    endgenerate
    localparam UNI = (V == 0);
    reg [15:0] dlu;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) dlu <= 0; else dlu <= {dlu[14:0], f_ref0};
    wire f_uni = (P == 0) ? f_ref0 : dlu[(P == 0) ? 0 : P - 1];
    initial begin errs = 0; nf = 0; end
    always @(negedge clk) if (rst_n) begin
        if (f_dut !== (|fexp_bits)) begin errs = errs + 1; if (errs <= 3) $display("MISMATCH N%0d AGE%0d P%0d V%h t%0t dut %b exp %b", N, AGE, P, V, $time, f_dut, |fexp_bits); end
        if (UNI && !(MUT == 1) && f_dut !== f_uni) begin errs = errs + 1; if (errs <= 3) $display("MISMATCH_UNI N%0d AGE%0d P%0d t%0t", N, AGE, P, $time); end
        if (P == 0 && UNI && f_dut !== f_ref0) begin errs = errs + 1; $display("MISMATCH_REF0 t%0t", $time); end
        if (f_dut) nf = nf + 1;
    end
endmodule

module tb_ot_dp_efault_eqpipe #(parameter integer MUT = 0);
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg [7:0] eq = 0;
    wire [31:0] e [0:7];
    wire [31:0] nf [0:7];
    eqchk #(.N(6), .AGE(5), .P(0), .MUT(MUT))                       c0 (clk, rst_n, eq, e[0], nf[0]);
    eqchk #(.N(6), .AGE(5), .P(2), .MUT(MUT))                       c1 (clk, rst_n, eq, e[1], nf[1]);
    eqchk #(.N(6), .AGE(5), .P(0), .V(24'h002111), .MUT(MUT))       c2 (clk, rst_n, eq, e[2], nf[2]);
    eqchk #(.N(4), .AGE(0), .P(1), .V(16'h0010), .MUT(MUT))         c3 (clk, rst_n, eq, e[3], nf[3]);
    eqchk #(.N(8), .AGE(3), .P(1), .V(32'h01100021), .MUT(MUT))     c4 (clk, rst_n, eq, e[4], nf[4]);
    eqchk #(.N(1), .AGE(0), .P(0), .MUT(MUT))                       c5 (clk, rst_n, eq, e[5], nf[5]);
    eqchk #(.N(5), .AGE(13), .P(0), .V(20'h00221), .MUT(MUT))       c6 (clk, rst_n, eq, e[6], nf[6]);   // the plan shape: depths 1,2,2 on 3 buses
    eqchk #(.N(3), .AGE(6), .P(3), .MUT(MUT))                       c7 (clk, rst_n, eq, e[7], nf[7]);
    integer run, k, i, tot, nfs, nok;
    integer rise [0:7]; integer drop [0:7]; integer rstat;
    initial begin
        tot = 0; nfs = 0; nok = 0;
        for (run = 0; run < 600; run = run + 1) begin
            for (i = 0; i < 8; i = i + 1) begin
                rise[i] = $urandom % 20;                 // rise edge (AGE up to 13: the late ones fault)
                drop[i] = ($urandom % 4 == 0) ? 15 + ($urandom % 30) : -1;
                if ($urandom % 3 != 0) rise[i] = $urandom % 4;   // mostly early: a fair share of runs stays clean
            end
            if ($urandom % 3 == 0) for (i = 0; i < 8; i = i + 1) drop[i] = -1;
            if ($urandom % 4 == 0) for (i = 0; i < 8; i = i + 1) rise[i] = 0;   // a clean-from-release run (AGE 0 cells stay fault-free)
            @(negedge clk); rst_n = 0; eq = 0; @(negedge clk); rst_n = 1;
            for (k = 0; k < 50; k = k + 1) begin
                for (i = 0; i < 8; i = i + 1) eq[i] = (k >= rise[i]) && !(drop[i] >= 0 && k == drop[i]);
                @(negedge clk);
            end
            for (i = 0; i < 8; i = i + 1) begin tot = tot + e[i]; end
        end
        for (i = 0; i < 8; i = i + 1) begin if (nf[i] == 0 || nf[i] > 600 * 49 - 100) begin tot = tot + 1; $display("COVERAGE cell %0d fault cycles %0d", i, nf[i]); end end
        if (tot == 0) $display("PASS tb_ot_dp_efault_eqpipe MUT %0d (fault cycles %0d %0d %0d %0d %0d %0d %0d %0d)", MUT, nf[0], nf[1], nf[2], nf[3], nf[4], nf[5], nf[6], nf[7]);
        else $display("FAIL tb_ot_dp_efault_eqpipe %0d mismatches MUT %0d", tot, MUT);
        $finish;
    end
endmodule
