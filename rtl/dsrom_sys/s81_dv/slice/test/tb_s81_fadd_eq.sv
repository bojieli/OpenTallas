`timescale 1ns/1ps
// S81U-CAP5: ot_s81_fadd_pipe == ot_fp32_add_rne_pipe, cycle for cycle (y / err / valid_out every edge after reset),
// on random operands biased to the hard cases: equal / near-equal magnitudes (cancellation), equal exponents, carries,
// subnormals, zeros of both signs, nonfinite, near-overflow.  +N=<vectors> (default 2,000,000).
module tb_s81_fadd_eq;
    reg clk = 0, rst_n = 0, v = 0;
    reg [31:0] a = 0, b = 0;
    wire [31:0] y0, y1; wire [1:0] e0, e1; wire v0, v1;
    ot_fp32_add_rne_pipe ref_add (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y0), .err(e0), .valid_out(v0));
    ot_s81_fadd_pipe     dut     (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y1), .err(e1), .valid_out(v1));
    always #1 clk = ~clk;
    integer n, N, bad = 0, cnt = 0, r;
    function automatic [31:0] pick(input [31:0] other);
        reg [31:0] x; integer s;
        begin
            x = $urandom; s = $urandom % 16;
            case (s)
                0: x[30:23] = 8'd0;                                   // subnormal / zero
                1: x[30:0] = 31'd0;                                   // +-0
                2: x[30:23] = 8'hff;                                  // nonfinite
                3: x[30:23] = 8'hfe;                                  // near overflow
                4: x = {~other[31], other[30:0]};                     // exact cancellation
                5: x = {~other[31], other[30:0]} ^ (32'd1 << ($urandom % 4));   // near cancellation
                6: x[30:23] = other[30:23];                           // equal exponents
                7: x[30:23] = other[30:23] + ($urandom % 3);          // close exponents
                8: x = {~other[31], other[30:23], $urandom} ;         // equal exp, opposite sign
                9: x[30:23] = 8'd1;
                default: ;
            endcase
            pick = x;
        end
    endfunction
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 2000000;
        repeat (3) @(posedge clk);
        rst_n = 1;
        for (n = 0; n < N; n = n + 1) begin
            @(negedge clk);
            v = ($urandom % 8) != 0;
            a = pick($urandom);
            b = pick(a);
            if ($urandom % 2) begin a = a ^ b; b = a ^ b; a = a ^ b; end
        end
        @(negedge clk) v = 0;
        repeat (8) @(posedge clk);
        if (bad == 0) $display("PASS fadd_eq %0d vectors, %0d valid results compared", N, cnt);
        else $display("FAIL fadd_eq %0d mismatches", bad);
        $finish;
    end
    always @(posedge clk) if (rst_n) begin
        if (v0 !== v1) begin bad = bad + 1; if (bad < 8) $display("MISMATCH valid %b %b", v0, v1); end
        else if (v0) begin
            cnt = cnt + 1;
            if (y0 !== y1 || e0 !== e1) begin
                bad = bad + 1;
                if (bad < 8) $display("MISMATCH y %h/%h err %0d/%0d", y0, y1, e0, e1);
            end
        end
    end
endmodule
