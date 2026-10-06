`timescale 1ns/1ps
// Lockstep equivalence of rtl/hdc/v41/ot_hdc_fsqrt_c12.sv against rtl/hdc/v41/ot_hdc_fsqrt.sv: one stimulus,
// {vo, y, fault} compared on EVERY cycle after the pipelines fill.  +EX=1: all 2^31 non-negative codes back to
// back (then +N random); +LO=<k> +HI=<k> sweep only codes [k*2^27, (k+1)*2^27) of that range (a shard); default: +N edge-biased random codes (zeros, subnormals, negatives, inf/NaN) with bubbles.
// Prints FSQRTC12 ... mismatches=<m>; exits through $fatal (nonzero) on any mismatch.
module tb_hdc_fsqrt_c12_equiv (input wire clk);
    reg rst_n = 1'b0;
    reg v = 1'b0;
    reg [31:0] a = 0;
    wire rv, rf, dv, df;
    wire [31:0] ry, dy;
    ot_hdc_fsqrt     ref_u (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .y(ry), .vo(rv), .fault(rf));
    ot_hdc_fsqrt_c12 dut_u (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .y(dy), .vo(dv), .fault(df));
    integer n = 1000000, ex = 0, lo = 0, hi = 16;
    reg [63:0] cyc = 0, sent = 0, xsent = 0, checked = 0, bad = 0, refused = 0, quiet = 0, cmp = 0;
    reg [31:0] seed = 32'h2545_F491;
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction
    function automatic [31:0] operand(input [31:0] r1, input [31:0] r2);
        begin
            case (r1[2:0])
                3'd0: operand = r2;
                3'd1: operand = {r1[9], 8'd0, r2[22:0] >> r1[7:3]};
                3'd2: operand = {r2[31], 31'd0};
                3'd3: operand = {r1[9], 8'hFF, r2[22:0] & {23{r1[8]}}};
                3'd4: operand = {1'b0, 8'd1 + {3'd0, r2[27:23]}, r2[22:0]};
                3'd5: operand = {1'b0, 8'd224 + {3'd0, r2[27:23]}, r2[22:0]};
                3'd6: operand = {r1[9], r2[30:23], r2[22:12], 12'd0};
                default: operand = {1'b0, r2[30:0]};
            endcase
        end
    endfunction
    initial begin
        if (!$value$plusargs("N=%d", n)) n = 1000000;
        if (!$value$plusargs("EX=%d", ex)) ex = 0;
        if (!$value$plusargs("LO=%d", lo)) lo = 0;
        if (!$value$plusargs("HI=%d", hi)) hi = 16;
        xsent = 64'h800_0000 * lo;
    end
    wire ex_phase = (ex != 0) && (xsent < 64'h800_0000 * hi);
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        if (rst_n) begin
            if (ex_phase) begin
                v <= 1'b1; a <= xsent[31:0]; xsent <= xsent + 1;
            end else begin
                seed = xs(seed);
                v <= (seed[3:0] != 0) && (sent < n);
                if ((seed[3:0] != 0) && (sent < n)) sent <= sent + 1;
                seed = xs(seed);
                a <= operand(seed, xs(seed ^ 32'h9E3779B9));
            end
            if (cyc > 48) begin
                cmp = cmp + 1;
                if (dv !== rv || dy !== ry || df !== rf) begin
                    if (bad < 10) $display("MISMATCH cyc=%0d ref=%0d/%h/%0d dut=%0d/%h/%0d", cyc, rv, ry, rf, dv, dy, df);
                    bad = bad + 1;
                end
            end
            if (rv) begin checked = checked + 1; if (rf) refused = refused + 1; end
            quiet = (!ex_phase && sent >= n) ? quiet + 1 : 0;
            if (quiet > 40) begin
                $display("FSQRTC12 exhaustive=%0d exhaustive_last=%0h random=%0d results=%0d refused=%0d cycles_compared=%0d mismatches=%0d",
                         ex, xsent - 1, sent, checked, refused, cmp, bad);
                if (bad != 0) $fatal(1, "FSQRTC12 FAIL");
                $finish;
            end
        end
    end
endmodule
