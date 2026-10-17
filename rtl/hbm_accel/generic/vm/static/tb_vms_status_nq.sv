`timescale 1ns/1ps
// H-NETLIST 1930 (A2P): ot_vms_status4_static NQ=2/4.  NQ=4: lockstep against the unchanged original (ot_vms_status4_ref,
// extracted by the runner from git); NQ=2: against the 2-quadrant reference model (same 3-rung latency).  Random
// statuses incl. saturation and flags.  Prints VMS_STATUS_NQ<n> PASS|FAIL checks.
module tb_vms_status_nq;
    parameter integer NQ = 2;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg [NQ*19-1:0] qs = 0; wire [18:0] vs;
    ot_vms_status4_static #(.NQ(NQ)) dut (.clk(clk), .rst_n(rst_n), .quadrant_status(qs), .vmstat(vs));
    reg [18:0] exp_q [0:3]; integer i, k, errs = 0, checks = 0; reg [17:0] t; reg [2:0] f;
    generate if (NQ == 4) begin : g4
        wire [18:0] rv; ot_vms_status4_ref r (.clk(clk), .rst_n(rst_n), .quadrant_status(qs), .vmstat(rv));
        always @(negedge clk) if (rst_n) begin checks = checks + 1; if (rv !== vs) errs = errs + 1; end
    end else begin : g2
        // reference: vmstat(t) = f(status(t-3)) once valid; status sampled at posedge
        reg [NQ*19-1:0] h1, h2, h3; reg [1:0] vq;
        always @(posedge clk) begin h1 <= qs; h2 <= h1; h3 <= h2; end
        always @(posedge clk or negedge rst_n) if (!rst_n) vq <= 0; else vq <= {vq[0], 1'b1};
        always @(negedge clk) if (rst_n && vq == 2'b11) begin
            t = 0; f = 0; for (k = 0; k < NQ; k = k + 1) begin t = t + h3[19*k +: 16]; f = f | h3[19*k + 16 +: 3]; end
            checks = checks + 1;
            if (vs !== {f, (|t[17:16]) ? 16'hffff : t[15:0]}) errs = errs + 1;
        end
    end endgenerate
    initial begin
        repeat (3) @(posedge clk); rst_n = 1;
        for (i = 0; i < 20000; i = i + 1) begin
            @(posedge clk); #0.1;
            for (k = 0; k < NQ; k = k + 1) qs[19*k +: 19] = (i % 7 == 0) ? {$random} | 19'h0ffff : {$random} & ((i % 3 == 0) ? 19'h7ffff : 19'h0ffff);
        end
        $display("VMS_STATUS_NQ%0d %s checks=%0d errors=%0d", NQ, (errs == 0 && checks > 1000) ? "PASS" : "FAIL", checks, errs);
        $finish;
    end
endmodule
