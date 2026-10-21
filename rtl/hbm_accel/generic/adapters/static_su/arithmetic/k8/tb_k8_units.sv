`timescale 1ns/1ps
// HBM-KIND8: lockstep of the k8 native-32 units against the released ones (same inputs every edge, compare every edge).
//   ot_hdc_fp32_mul_lat4i_k8 vs ot_hdc_fp32_mul_lat4i  (random + subnormal-result biased operands)
//   ot_hdc_v41x_exp_k8      vs ot_hdc_v41x_exp #(4,3)  (random x in the clamp range and beyond)
// +MUT_MUL / +MUT_EXP flip one output bit of the k8 unit (negative controls: the bench must FAIL).
module tb_k8_units;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg v = 0; reg [31:0] a = 0, b = 0, x = 0;
    wire [31:0] y0, y1, e0, e1; wire [1:0] r0, r1; wire o0, o1, eo0, eo1, ef0, ef1;
    ot_hdc_fp32_mul_lat4i    u_ref (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y0), .err(r0), .valid_out(o0));
    ot_hdc_fp32_mul_lat4i_k8 u_k8  (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y1), .err(r1), .valid_out(o1));
    ot_hdc_v41x_exp    #(.LM(4), .LA(3)) x_ref (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .y(e0), .vo(eo0), .fault(ef0));
    ot_hdc_v41x_exp_k8 #(.LM(4), .LA(3)) x_k8  (.clk(clk), .rst_n(rst_n), .rst_m(rst_n), .rst_a(rst_n), .v(v), .x(x), .y(e1), .vo(eo1), .fault(ef1));
    integer n = 0, err = 0, mchk = 0, echk = 0, subs = 0, N = 400000;
    bit mm, me;
    function automatic [31:0] rnd_fp(input integer mode);
        reg [31:0] r;
        begin
            r = $urandom;
            case (mode)
                0: rnd_fp = r;
                1: rnd_fp = {r[31], 8'(1 + r[9:4] % 40), r[22:0]};         // tiny normals: products go subnormal
                2: rnd_fp = {r[31], 8'd0, r[22:0]};                          // subnormals
                default: rnd_fp = {r[31], 8'(100 + r[5:0] % 40), r[22:0]};
            endcase
        end
    endfunction
    initial begin
        mm = $test$plusargs("MUT_MUL"); me = $test$plusargs("MUT_EXP");
        if (!$value$plusargs("N=%d", N)) N = 400000;
        repeat (3) @(negedge clk); rst_n = 1;
        for (n = 0; n < N; n = n + 1) begin
            @(negedge clk);
            v = ($urandom % 8) != 0;
            a = rnd_fp($urandom % 4); b = rnd_fp($urandom % 4);
            x = (($urandom % 4) == 0) ? $urandom : {$urandom % 2 == 0, 8'(110 + $urandom % 25), 23'($urandom)};
        end
        repeat (80) @(negedge clk);
        $display("K8_UNITS %s mul_checks=%0d exp_checks=%0d sub_results=%0d errors=%0d", err ? "FAIL" : "PASS", mchk, echk, subs, err);
        if (err) $fatal(1, "K8_UNITS FAIL");
        $finish;
    end
    always @(posedge clk) if (rst_n) begin
        if (o0 !== o1) begin err = err + 1; if (err < 8) $display("K8 mul valid mismatch"); end
        if (o0) begin
            mchk = mchk + 1; if (y0[30:23] == 0 && y0[22:0] != 0) subs = subs + 1;
            if ({y0, r0} !== {y1 ^ (mm ? 32'h1 : 32'h0), r1}) begin err = err + 1; if (err < 8) $display("K8 mul y %h/%h err %0d/%0d", y0, y1, r0, r1); end
        end
        if (eo0 !== eo1) begin err = err + 1; if (err < 8) $display("K8 exp valid mismatch"); end
        if (eo0) begin
            echk = echk + 1;
            if ({e0, ef0} !== {e1 ^ (me ? 32'h100 : 32'h0), ef1}) begin err = err + 1; if (err < 8) $display("K8 exp y %h/%h", e0, e1); end
        end
    end
endmodule
