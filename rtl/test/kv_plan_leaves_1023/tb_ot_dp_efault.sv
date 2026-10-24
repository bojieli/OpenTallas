`timescale 1ns/1ps
// KV-P3-LEAF 10-23: bench of ot_dp_efault (N 3, AGE 6).  Edge k = the k-th clk edge after rst_n release.
//   S0 every eq rises by its counted age (lanes at edges 2, 4, 6; sampled from edge 7): fault stays 0 for 60 edges;
//   S1 lane 1 rises late (edge 8): fault rises at edge 7 and stays (sticky) after the lane arrives;
//   S2 all on time, lane 2 drops for one edge at edge 30: fault rises at edge 31 and stays;
//   S3 reset in the middle of a fault clears it; S0 again after it passes;
//   S4 AGE 0 (armed at once), lanes high from release: no fault.
// Mutants (bench power): MUT 1 = a non-sticky cell copy (fault <= armed & ~&eq), MUT 2 = wrong age (AGE + 3): FAIL.
module ot_dp_efault_nosticky #(parameter integer N = 1, parameter integer AGE = 4) (
    input wire clk, input wire rst_n, input wire [N-1:0] eq, output reg fault);
    reg [7:0] cnt;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cnt <= 0; fault <= 0; end
        else begin if (cnt != AGE) cnt <= cnt + 1; fault <= (cnt == AGE) & ~&eq; end
endmodule

module tb_ot_dp_efault #(parameter integer MUT = 0);
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg [2:0] eq = 0;
    reg [1:0] eq0 = 0;
    wire fault, fault0;
    generate
        if (MUT == 1) begin : g_m1
            ot_dp_efault_nosticky #(.N(3), .AGE(6)) u (.clk(clk), .rst_n(rst_n), .eq(eq), .fault(fault));
        end else begin : g_ok
            ot_dp_efault #(.N(3), .AGE((MUT == 2) ? 9 : 6)) u (.clk(clk), .rst_n(rst_n), .eq(eq), .fault(fault));
        end
    endgenerate
    ot_dp_efault #(.N(2), .AGE(0)) u0 (.clk(clk), .rst_n(rst_n), .eq(eq0), .fault(fault0));
    integer k, errs = 0, sc;
    // eq after edge k of scenario sc (applied at the negedge before edge k + 1)
    function automatic [2:0] lanes(input integer s, input integer k);
        lanes[0] = k >= 2;
        lanes[1] = (s == 1) ? (k >= 8) : (k >= 4);
        lanes[2] = (k >= 6) && !(s == 2 && k == 30);
    endfunction
    function automatic expect_fault(input integer s, input integer k);   // fault after edge k
        expect_fault = (s == 1) ? (k >= 7) : (s == 2) ? (k >= 31) : 1'b0;
    endfunction
    task automatic run(input integer s, input integer n);
        begin
            @(negedge clk); rst_n = 0; eq = 0; eq0 = 0; @(negedge clk); rst_n = 1;   // release; next posedge = edge 1
            eq = lanes(s, 0); eq0 = 2'b11;
            for (k = 1; k <= n; k = k + 1) begin
                @(negedge clk);   // edge k done
                if (fault !== expect_fault(s, k)) begin
                    errs = errs + 1;
                    if (errs <= 6) $display("MISMATCH S%0d edge %0d fault %b", s, k, fault);
                end
                if (fault0 !== 1'b0) begin errs = errs + 1; $display("MISMATCH AGE0 edge %0d", k); end
                eq = lanes(s, k);
            end
        end
    endtask
    initial begin
        run(0, 60);
        run(1, 60);
        run(2, 60);
        run(1, 20);          // S3: fault, then the reset of the next run clears it
        if (fault !== 1'b1) begin errs = errs + 1; $display("MISMATCH S3 no fault before reset"); end
        @(negedge clk); rst_n = 0; #1;
        if (fault !== 1'b0) begin errs = errs + 1; $display("MISMATCH S3 async clear"); end
        run(0, 60);
        if (errs == 0) $display("PASS tb_ot_dp_efault MUT %0d", MUT);
        else $display("FAIL tb_ot_dp_efault %0d mismatches MUT %0d", errs, MUT);
        $finish;
    end
endmodule
