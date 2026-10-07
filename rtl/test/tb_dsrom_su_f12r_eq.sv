`timescale 1ns/1ps
// Equivalence of the re-cut f12 units (ot_hdc_fp32_{mul,add}_f12r) with the all-cut originals (ot_hdc_fp32_{mul,add}_f12,
// CUTS all ones): {y, err} of every valid pair equal, the re-cut unit 2 cycles later.  +N=<pairs> +SEED=<s>.
module tb_dsrom_su_f12r_eq;
    reg clk = 1'b0, rst_n = 1'b0;
    always #1 clk = ~clk;
    reg v; reg [31:0] a, b;
    wire [31:0] ym0, ym1, ya0, ya1; wire [1:0] em0, em1, ea0, ea1; wire vm0, vm1, va0, va1;
    ot_hdc_fp32_mul_f12  #(.CUTS(8'b11111111)) m0 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ym0), .err(em0), .valid_out(vm0));
    ot_hdc_fp32_mul_f12r                       m1 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ym1), .err(em1), .valid_out(vm1));
    ot_hdc_fp32_add_f12  #(.CUTS(7'b1111111)) a0 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ya0), .err(ea0), .valid_out(va0));
    ot_hdc_fp32_add_f12r                       a1 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ya1), .err(ea1), .valid_out(va1));
    reg [33:0] qm [0:31], qa [0:31];
    integer wm, rm, wa, ra, n, N, seed, mism;
    function automatic [31:0] pick(input integer s);
        reg [31:0] r; integer c;
        begin
            r = $urandom; c = $urandom % 12;
            case (c)
                0: pick = {r[31], 8'd0, r[22:0]};
                1: pick = {r[31], 8'd0, 22'd0, r[0]};
                2: pick = {r[31], 8'hFF, (r[1] ? r[22:0] : 23'd0)};
                3: pick = {r[31], 31'd0};
                4: pick = {r[31], 8'd254 - r[2:0], r[22:0]};
                5: pick = {r[31], 8'd1 + r[2:0], r[22:0]};
                6: pick = {r[31], 8'd127 + r[1:0] - 8'd1, r[22:0]};
                7: pick = {r[31], 8'd64 + r[5:0], r[22:0]};
                default: pick = r;
            endcase
        end
    endfunction
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 1000000;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        void'($urandom(seed));
        v = 0; a = 0; b = 0; mism = 0; wm = 0; rm = 0; wa = 0; ra = 0;
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        for (n = 0; n < N + 40; n = n + 1) begin
            @(posedge clk);
            if (n < N) begin
                v <= 1'b1; a <= pick(0);
                case ($urandom % 4)
                    0: b <= pick(1);
                    1: b <= {a[31] ^ ($urandom % 2 == 0), a[30:23], a[22:0] ^ ($urandom % 8)};     // near cancellation
                    2: b <= {~a[31], a[30:23] + 8'd1, a[22:0]};
                    default: b <= pick(1);
                endcase
            end else v <= 1'b0;
        end
        $display("F12REQ n=%0d mismatches=%0d", N, mism);
        $finish;
    end
    always @(posedge clk) begin
        if (vm0) begin qm[wm % 32] <= {em0, ym0}; wm <= wm + 1; end
        if (vm1) begin
            if (qm[rm % 32] !== {em1, ym1}) begin if (mism < 10) $display("MUL MISMATCH %h %h", qm[rm % 32], {em1, ym1}); mism = mism + 1; end
            rm <= rm + 1;
        end
        if (va0) begin qa[wa % 32] <= {ea0, ya0}; wa <= wa + 1; end
        if (va1) begin
            if (qa[ra % 32] !== {ea1, ya1}) begin if (mism < 10) $display("ADD MISMATCH %h %h", qa[ra % 32], {ea1, ya1}); mism = mism + 1; end
            ra <= ra + 1;
        end
    end
endmodule
