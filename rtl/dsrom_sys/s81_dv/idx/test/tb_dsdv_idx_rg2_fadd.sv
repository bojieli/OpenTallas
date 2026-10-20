`timescale 1ns/1ps
// S81-L20RD2 (10-20): exactness of the reader-local FP32 adder dsdv_idx_rg2_fadd (latency 8) against the record
// ot_hdc_fp32_add_lat #(.LAT(7)) (latency 7): every edge a new operand pair, y / err compared bit for bit.
// Operand classes (by cycle): random words, near-equal magnitudes (cancellation), shifted exponents 0..40 apart,
// zeros / subnormals / max-exponent / nonfinite, rounding ties.  +N= vectors (default 4,000,000).  +MUT=1 flips the
// sticky bit of the reference comparison (negative control: must FAIL).  Prints TB_FADD PASS / FAIL.
module tb_dsdv_idx_rg2_fadd;
    reg clk = 0;
    always #1 clk = ~clk;
    integer N = 4000000, MUT = 0;
    initial begin void'($value$plusargs("N=%d", N)); void'($value$plusargs("MUT=%d", MUT)); end
    reg rst_n = 0;
    reg [31:0] a = 0, b = 0;
    wire [31:0] y_r, y_d; wire [1:0] e_r, e_d; wire v_r;
    ot_hdc_fp32_add_lat #(.LAT(7)) u_ref (.clk(clk), .rst_n(rst_n), .valid_in(1'b1), .a(a), .b(b), .y(y_r), .err(e_r), .valid_out(v_r));
    dsdv_idx_rg2_fadd u_dut (.clk(clk), .a(a), .b(b), .y(y_d), .err(e_d));
    reg [31:0] yr1; reg [1:0] er1; reg vr1 = 0;
    always @(posedge clk) begin yr1 <= y_r; er1 <= e_r; vr1 <= v_r; end
    longint seed = 64'h1234_5678_9abc_def1;
    function automatic [63:0] rnd();
        seed = seed ^ (seed << 13); seed = seed ^ (seed >> 7); seed = seed ^ (seed << 17); rnd = seed;
    endfunction
    integer n = 0, bad = 0, cls;
    reg [63:0] r, r2;
    always @(negedge clk) if (rst_n) begin
        r = rnd(); r2 = rnd(); cls = r2[3:0];
        case (cls)
            0, 1, 2: begin a = r[31:0]; b = r[63:32]; end
            3, 4: begin a = r[31:0]; b = {~r[31], r[30:23], r[22:0] ^ (r2[22:0] >> r2[27:23])}; end        // cancellation
            5, 6: begin a = r[31:0]; b = {r[63], 8'(r[30:23] + {2'b00, r2[37:32]} - 8'd20), r[54:32]}; end  // exponents close
            7: begin a = {r[31], 8'd0, r[22:0]}; b = {r[63], r2[40] ? 8'd0 : 8'(r[62:55] & 8'h3f), r[54:32]}; end   // subnormals
            8: begin a = {r[31], 8'hfe, r[22:0]}; b = {r[63], 8'(8'hfe - r2[34:32]), r[54:32]}; end    // overflow edge
            9: begin a = r2[8] ? 32'd0 : {r[31], 8'hff, r[22:0]}; b = r[63:32]; end             // zero / nonfinite
            10: begin a = {r[31], r[30:23], r[22:3], 3'b000}; b = {r[63], 8'(r[30:23] - 8'(r2[41:38])), r[54:32]}; end // ties
            11: begin a = r[31:0]; b = r2[50] ? {r[31], r[30:0]} : {~r[31], r[30:0]}; end      // a + a, a - a
            default: begin a = r[31:0]; b = {r2[60], 8'(r[30:23] + r2[45:42] - 8'd8), r2[22:0]}; end
        endcase
    end
    always @(posedge clk) if (rst_n && vr1) begin
        n = n + 1;
        if ({y_d, e_d} !== ({yr1, er1} ^ ((MUT != 0 && yr1[0] != yr1[1]) ? 34'd4 : 34'd0))) begin
            bad = bad + 1;
            if (bad <= 8) $display("TB_FADD MISMATCH n %0d ref %h/%0d dut %h/%0d", n, yr1, er1, y_d, e_d);
        end
        if (n >= N) begin
            $display("TB_FADD_STATS vectors %0d mismatches %0d mut %0d", n, bad, MUT);
            if (bad != 0) $display("TB_FADD FAIL"); else $display("TB_FADD PASS");
            $finish;
        end
    end
    initial begin repeat (4) @(posedge clk); rst_n = 1; end
endmodule
