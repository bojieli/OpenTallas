`timescale 1ns/1ps
// Cycle-by-cycle equivalence against the qualified rtl/proto/ot_fp32_mul_rne_pipe.sv:
// * rtl/hdc/ot_hdc_fp32_mul_pipe.sv (rebalanced): y, err and valid_out agree on
//   every cycle of +N operand pairs biased toward every multiplier edge;
// * ot_hdc_bmul (exact BF16 x BF16) on the same stream with the low 16 bits of
//   each operand cleared: wherever it does not fault, y agrees; it may fault
//   only where the qualified pipe refuses or the product is not exact.
module tb_hdc_mul_equiv (input wire clk);
    reg rst_n = 1'b0;
    reg v = 1'b0;
    reg [31:0] a = 0, b = 0;
    wire [31:0] y0, y1;
    wire [1:0] e0, e1;
    wire v0, v1;
    ot_fp32_mul_rne_pipe ref_u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y0), .err(e0), .valid_out(v0));
    ot_hdc_fp32_mul_pipe dut_u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y1), .err(e1), .valid_out(v1));
    wire [31:0] ab = {a[31:16], 16'd0}, bb = {b[31:16], 16'd0};
    wire [31:0] yb0, yb1;
    wire [1:0] eb0;
    wire vb0, fb1;
    ot_fp32_mul_rne_pipe refb_u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(ab), .b(bb), .y(yb0), .err(eb0), .valid_out(vb0));
    ot_hdc_bmul bmul_u (.clk(clk), .rst_n(rst_n), .v(v), .a(ab), .b(bb), .y(yb1), .fault(fb1));
    integer bchecked = 0, bfault = 0, bbad = 0;
    // exact product magnitude floor: a result below 2^-132 (biased < -6) is not exact
    always @(posedge clk) if (rst_n && vb0) begin
        if (fb1) begin
            bfault = bfault + 1;
            //: a refusal is legitimate only where the pipe refuses, or rounds a
            //: product that is not a normal number
            if (eb0 == 2'd0 && yb0[30:23] != 8'd0) begin
                if (bbad < 10) $display("BMUL SPURIOUS FAULT ref=%h", yb0);
                bbad = bbad + 1;
            end
        end
        else begin
            bchecked = bchecked + 1;
            if (yb1 !== yb0 || eb0 != 2'd0) begin
                if (bbad < 10) $display("BMUL MISMATCH ref=%h/%0d bmul=%h", yb0, eb0, yb1);
                bbad = bbad + 1;
            end
        end
    end

    integer n = 1000000, cyc = 0, sent = 0, checked = 0, bad = 0, quiet = 0;
    reg [31:0] seed = 32'h1234_5678;
    function automatic [31:0] xs(input [31:0] s);   // xorshift32
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction
    function automatic [31:0] operand(input [31:0] r1, input [31:0] r2);
        reg [7:0] e;
        begin
            case (r1[2:0])
                3'd0: operand = r2;
                3'd1: operand = {r2[31], 8'd107 + {3'd0, r2[4:0]} + {3'd0, r2[9:5]}, r2[22:0]};
                3'd2: operand = {r2[31], 8'd0, r2[22:0] >> r1[7:3]};
                3'd3: operand = {r2[31], 31'd0};
                3'd4: operand = {r2[31], 8'd1 + {3'd0, r2[27:23]}, r2[22:0]};
                3'd5: operand = {r2[31], 8'd200 + {2'd0, r2[28:23]}, r2[22:0]};
                3'd6: operand = {r2[31:16], 16'd0};
                default: begin e = r2[30:23]; operand = {r2[31], e, r2[22:0]}; end
            endcase
        end
    endfunction
    initial if (!$value$plusargs("N=%d", n)) n = 1000000;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        if (rst_n) begin
            seed = xs(seed);
            v <= (seed[3:0] != 0) && (sent < n);
            if ((seed[3:0] != 0) && (sent < n)) sent <= sent + 1;
            seed = xs(seed);
            a <= operand(seed, xs(seed ^ 32'h9E3779B9));
            seed = xs(seed);
            b <= operand(seed, xs(seed ^ 32'h7F4A7C15));
            if (v0 !== v1 || (v0 && (y0 !== y1 || e0 !== e1))) begin
                if (bad < 10) $display("MISMATCH cyc=%0d ref=%h/%0d dut=%h/%0d", cyc, y0, e0, y1, e1);
                bad = bad + 1;
            end
            if (v0) checked = checked + 1;
            quiet = (sent >= n) ? quiet + 1 : 0;
            if (quiet > 20) begin
                $display("MULEQ checked=%0d mismatches=%0d", checked, bad);
                $display("BMULEQ checked=%0d faulted=%0d mismatches=%0d", bchecked, bfault, bbad);
                if (bad == 0 && checked == n && bbad == 0) $display("PASS"); else $display("FAIL");
                $finish;
            end
        end
    end
endmodule
