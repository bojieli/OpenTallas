`timescale 1ns/1ps
// Cycle equivalence of the low-latency binary32 units (rtl/hdc/ot_hdc_fastfp.sv)
// against the qualified five-stage pipes: the same edge-biased operand stream
// enters both, and the fast unit's y / err / valid, delayed by the latency
// difference, must equal the qualified pipe's on every cycle.
module tb_hdc_fastfp_equiv (input wire clk);
    localparam integer DL = 2;              // 5 - 3
    reg rst_n = 1'b0;
    reg v = 1'b0;
    reg [31:0] a = 0, b = 0;
    wire [31:0] ya0, ya1, ym0, ym1;
    wire [1:0]  ea0, ea1, em0, em1;
    wire        va0, va1, vm0, vm1;
    ot_fp32_add_rne_pipe  ra (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ya0), .err(ea0), .valid_out(va0));
    ot_hdc_fp32_add_fast  da (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ya1), .err(ea1), .valid_out(va1));
    ot_hdc_fp32_mul_pipe  rm (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ym0), .err(em0), .valid_out(vm0));
    ot_hdc_fp32_mul_fast  dm (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ym1), .err(em1), .valid_out(vm1));
    reg [34:0] qa1, qa2, qm1, qm2;
    always @(posedge clk) begin
        qa1 <= {va1, ea1, ya1}; qa2 <= qa1;
        qm1 <= {vm1, em1, ym1}; qm2 <= qm1;
    end

    integer n = 1000000, cyc = 0, sent = 0, checked = 0, bada = 0, badm = 0, quiet = 0;
    reg [31:0] seed;
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction
    function automatic [31:0] operand(input [31:0] r1, input [31:0] r2);
        begin
            case (r1[3:0])
                4'd0: operand = r2;
                4'd1: operand = {r2[31], 8'd107 + {3'd0, r2[4:0]} + {3'd0, r2[9:5]}, r2[22:0]};
                4'd2: operand = {r2[31], 8'd0, r2[22:0] >> r1[8:4]};
                4'd3: operand = {r2[31], 31'd0};
                4'd4: operand = {r2[31], 8'd1 + {3'd0, r2[27:23]}, r2[22:0]};
                4'd5: operand = {r2[31], 8'd200 + {2'd0, r2[28:23]}, r2[22:0]};
                4'd6: operand = {r2[31:16], 16'd0};
                4'd7: operand = {r2[31], 8'd127 + {{4{r2[27]}}, r2[26:23]}, r2[22:0]};
                4'd8: operand = {r2[31], 8'd254 - {5'd0, r2[25:23]}, r2[22:0]};
                4'd9: operand = {r2[31], 8'hff, r2[22:0] & {23{r1[9]}}};
                4'd10: operand = {r2[31], r2[30:23], 23'h7fffff ^ (23'd1 << r1[8:4])};
                4'd11: operand = {r2[31], r2[30:23], 23'd0 | (23'd1 << r1[8:4])};
                default: operand = r2;
            endcase
        end
    endfunction
    reg [31:0] pa, pb;
    initial begin
        if (!$value$plusargs("N=%d", n)) n = 1000000;
        if (!$value$plusargs("SEED=%d", seed)) seed = 32'h1234_5678;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        if (rst_n) begin
            seed = xs(seed);
            v <= (seed[3:0] != 0) && (sent < n);
            if ((seed[3:0] != 0) && (sent < n)) sent <= sent + 1;
            seed = xs(seed);
            pa = operand(seed, xs(seed ^ 32'h9E3779B9));
            seed = xs(seed);
            pb = operand(seed, xs(seed ^ 32'h7F4A7C15));
            // near cancellations and close exponents, the adder's hard cases
            case (seed[31:29])
                3'd0: pb = {~pa[31], pa[30:0]} ^ {9'd0, 23'd1 << seed[28:24]};
                3'd1: pb = {seed[23], pa[30:23] - {6'd0, seed[25:24]}, pb[22:0]};
                3'd2: pb = {~pa[31], pa[30:0] - {27'd0, seed[27:24]}};
                default: ;
            endcase
            a <= pa; b <= pb;
            if (va0 !== qa2[34] || (va0 && (ya0 !== qa2[31:0] || ea0 !== qa2[33:32]))) begin
                if (bada < 10) $display("ADD MISMATCH cyc=%0d ref=%h/%0d dut=%h/%0d", cyc, ya0, ea0, qa2[31:0], qa2[33:32]);
                bada = bada + 1;
            end
            if (vm0 !== qm2[34] || (vm0 && (ym0 !== qm2[31:0] || em0 !== qm2[33:32]))) begin
                if (badm < 10) $display("MUL MISMATCH cyc=%0d ref=%h/%0d dut=%h/%0d", cyc, ym0, em0, qm2[31:0], qm2[33:32]);
                badm = badm + 1;
            end
            if (va0) checked = checked + 1;
            quiet = (sent >= n) ? quiet + 1 : 0;
            if (quiet > 20) begin
                $display("FASTFP checked=%0d add_mismatches=%0d mul_mismatches=%0d", checked, bada, badm);
                if (bada == 0 && badm == 0 && checked == n) $display("PASS"); else $display("FAIL");
                $finish;
            end
        end
    end
endmodule
