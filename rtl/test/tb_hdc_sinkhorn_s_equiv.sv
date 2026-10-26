`timescale 1ns/1ps
// HBM-P4-SPLIT (2026-10-23): lock-step of the core-split twin ot_hdc_sinkhorn_s (step0 / steady hard cores) against the
// pinned ot_hdc_sinkhorn on the same accepted inputs.  Per case: y and fault must be bit-identical and the twin's
// out_valid must come exactly 1 edge after the pinned one (cost +1 edge, 2 ITERS + 2).  Inputs (seeded xorshift): normal
// positives over a wide exponent range, subnormals, zeros, all-zero rows (0/0), negatives / Inf / NaN (fault cases).
// +N=<cases> +SEED=<n>.  -DMUT=1: B output register one edge early -> must FAIL.  PASS: "SINKHORN_S_EQUIV PASS".
module tb_hdc_sinkhorn_s_equiv;
    reg clk = 1'b0; always #0.5 clk = !clk;
`ifndef MUT
`define MUT 0
`endif
    parameter integer ITERS = 20;
    reg rst_n = 1'b0, in_valid = 1'b0; reg [511:0] in_e = 0;
    wire a_rdy, a_ov, a_f, a_busy, b_rdy, b_ov, b_f, b_busy; wire [511:0] a_y, b_y;
    ot_hdc_sinkhorn   #(.ITERS(ITERS)) ref_u (.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(a_rdy), .in_e(in_e),
        .out_valid(a_ov), .y(a_y), .fault(a_f), .busy(a_busy));
    ot_hdc_sinkhorn_s #(.ITERS(ITERS), .MUT(`MUT)) dut (.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(b_rdy), .in_e(in_e),
        .out_valid(b_ov), .y(b_y), .fault(b_f), .busy(b_busy));
    reg [31:0] s = 32'h2026_1023;
    function automatic [31:0] xs(input [31:0] v); reg [31:0] t; begin t = v ^ (v << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end endfunction
    function automatic [31:0] word(input [31:0] r1, input [31:0] r2);
        reg [7:0] e; integer k;
        begin
            k = r1 % 100;
            if (k < 80) begin e = 8'(100 + (r2 % 40)); word = {1'b0, e, r1[22:0] ^ r2[31:9]}; end      // normal positive
            else if (k < 88) word = {1'b0, 8'd0, r2[22:0]};                                            // subnormal
            else if (k < 95) word = 32'd0;                                                              // zero
            else if (k < 97) word = {1'b0, 8'(1 + (r2 % 20)), r1[22:0]};                                // tiny normal
            else if (k < 98) word = {1'b1, 8'(120), r2[22:0]};                                          // negative (fault)
            else if (k < 99) word = 32'h7F80_0000;                                                      // +Inf (fault)
            else word = 32'h3F80_0000;
        end
    endfunction
    integer n = 300, c, k, cyc = 0, ta, tb_, errs = 0, faults = 0, zrow;
    reg [511:0] ya; reg fa;
    always @(posedge clk) cyc <= cyc + 1;
    initial begin
        if ($value$plusargs("N=%d", n)) begin end
        if ($value$plusargs("SEED=%d", s)) begin end
        repeat (4) @(negedge clk); rst_n = 1'b1; repeat (2) @(negedge clk);
        for (c = 0; c < n; c = c + 1) begin
            while (!(a_rdy && b_rdy)) @(negedge clk);
            for (k = 0; k < 16; k = k + 1) begin s = xs(s); ta = s; s = xs(s); in_e[32*k +: 32] = word(ta, s); end
            s = xs(s); zrow = s % 16;                                  // occasionally an all-zero row (0/0 fault)
            if (zrow == 3) for (k = 0; k < 4; k = k + 1) in_e[32*(4*(c%4) + k) +: 32] = 32'd0;
            in_valid = 1'b1; @(negedge clk); in_valid = 1'b0;
            while (!a_ov) @(negedge clk);
            ta = cyc; ya = a_y; fa = a_f;
            while (!b_ov) @(negedge clk);
            tb_ = cyc;
            if (b_y !== ya || b_f !== fa || tb_ != ta + 1) begin
                errs = errs + 1;
                if (errs < 6) $display("MISMATCH case %0d fault %0d/%0d dt %0d y_equal %0d", c, fa, b_f, tb_ - ta, b_y === ya);
            end
            if (fa) faults = faults + 1;
        end
        $display("SINKHORN_S_EQUIV cases %0d faults %0d errors %0d mut %0d", n, faults, errs, `MUT);
        if (errs == 0 && faults > 0 && faults < n) $display("SINKHORN_S_EQUIV PASS cases %0d", n);
        else $fatal(1, "SINKHORN_S_EQUIV FAIL");
        $finish;
    end
endmodule
