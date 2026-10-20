`timescale 1ns/1ps
// S81-VE4 unit equivalence bench: the native-32 ve-local adder / multiplier (ot_s81sl_ve_fadd / _fmul,
// rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv) against the shared f12 units at the ve calendar's cuts
// (ot_hdc_fp32_add_f12 CUTS 6'b101010, ot_hdc_fp32_mul_f12 CUTS 8'b01101010), cycle by cycle: valid_out every edge,
// y / err / y2 on every valid edge.  Operands mix full random words with targeted classes (equal / adjacent exponents =
// cancellation, subnormals, zeros, inf / nan, exponent gaps around 24..30, overflow and underflow edges of the product).
// Every register without reset powers up random (+verilator+rand+reset+2); valid is random; a reset pulse mid-run.
// +n=<cycles> (default 3000000).  MUT (bench only, must FAIL): 1 drops the adder's sticky jam, 2 forces the
// multiplier's subnormal shift one place short (both injected on the DUT's inputs/outputs, see below).
module tb_s81sl_ve_fp #(parameter integer MUT = 0);
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg v;
    reg [31:0] a, b;
    wire [31:0] ya_r, ya_n, ya_n2, ym_r, ym_n, ym_n2;
    wire [1:0]  ea_r, ea_n, em_r, em_n;
    wire        va_r, va_n, vm_r, vm_n;
    ot_hdc_fp32_add_f12 #(.CUTS(6'b101010)) ra (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ya_r), .err(ea_r), .valid_out(va_r));
    ot_s81sl_ve_fadd na (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .a2(a), .b(b), .b2(b), .y(ya_n), .y2(ya_n2), .err(ea_n), .valid_out(va_n));
    ot_hdc_fp32_mul_f12 #(.CUTS(8'b01101010)) rm (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ym_r), .err(em_r), .valid_out(vm_r));
    ot_s81sl_ve_fmul nm (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .a2(a), .b(b), .b2(b), .y(ym_n), .y2(ym_n2), .err(em_n), .valid_out(vm_n));

    function automatic [31:0] gen(input integer cls, input [31:0] r0, input [31:0] r1, input [31:0] base);
        reg [7:0] e;
        begin
            case (cls)
                0, 1, 2: gen = r0;                                                     // full random
                3: gen = {r0[31], base[30:23], r0[22:0]};                              // same exponent
                4: gen = {r0[31], base[30:23] + {7'd0, r0[0]} - {7'd0, r0[1]}, r0[22:0]}; // adjacent exponent
                5: gen = {r0[31], 8'd0, r0[22:0] >> r1[4:0]};                          // subnormal / zero
                6: gen = {r0[31], (r0[2] ? 8'hff : 8'h00), (r0[3] ? 23'd0 : r0[22:0])}; // inf / nan / zero
                7: gen = {r0[31], base[30:23] - (r1[4:0] + 8'd20), r0[22:0]};          // gap 20..51
                8: begin e = 8'd100 + {3'd0, r1[4:0]}; gen = {r0[31], e, r0[22:0]}; end  // product underflow edge
                9: begin e = 8'd190 + {3'd0, r1[5:0]}; gen = {r0[31], e, r0[22:0]}; end  // product overflow edge
                10: gen = {r0[31], base[30:23], base[22:0] ^ (23'd1 << r1[4:0])};      // near-equal magnitude
                11: gen = {r0[31], r1[7:0], 23'h7fffff ^ (r0[22:0] & 23'h7)};            // round carry chains
                default: gen = r0;
            endcase
        end
    endfunction
    integer n, cyc, bad_a, bad_m, nva, nvm;
    reg [31:0] base;
    initial begin
        if (!$value$plusargs("n=%d", n)) n = 3000000;
        bad_a = 0; bad_m = 0; nva = 0; nvm = 0;
        v = 0; a = 0; b = 0;
        repeat (3) @(posedge clk);
        #0.2 rst_n = 1;
        for (cyc = 0; cyc < n; cyc = cyc + 1) begin
            @(negedge clk);
            if (cyc == n / 2) rst_n = 0;               // in-flight reset: valids cleared mid-stream
            if (cyc == n / 2 + 3) rst_n = 1;
            base = $urandom;
            v = ($urandom % 8) != 0;
            a = gen($urandom % 12, $urandom, $urandom, base);
            b = gen($urandom % 12, $urandom, $urandom, base);
            if (($urandom % 16) == 0) b = {~a[31], a[30:0]};                           // exact cancellation
            if (($urandom % 32) == 0) b = a;
        end
        @(negedge clk);
        v = 0;
        repeat (12) @(negedge clk);
        $display("checked add %0d mul %0d valid results", nva, nvm);
        if (MUT != 0) begin
            if (bad_a + bad_m > 0) $display("MUTANT %0d REJECTED mismatches=%0d", MUT, bad_a + bad_m);
            else $display("MUTANT %0d NOT DETECTED", MUT);
        end
        else if (bad_a == 0 && bad_m == 0 && nva > 1000 && nvm > 1000) $display("PASS ve_fp add=%0d mul=%0d", nva, nvm);
        else $display("FAIL ve_fp bad_add=%0d bad_mul=%0d", bad_a, bad_m);
        $finish;
    end
    // MUT 1: the adder result's lowest bit flipped whenever the reference result is inexact-by-sticky would need
    // internal access; the bench mutants instead perturb the DUT outputs the way a broken datapath would:
    //   MUT 1: adder y bit 0 forced to the reference's ~bit 0 when the exponent gap is > 24 (a lost sticky round)
    //   MUT 2: multiplier y shifted right by one for subnormal results (field 0)
    wire [31:0] ya_c = (MUT == 1 && ya_n[30:23] != 0 && ya_n[1:0] == 2'b11) ? (ya_n ^ 32'd1) : ya_n;
    wire [31:0] ym_c = (MUT == 2 && ym_n[30:23] == 0 && ym_n[22:0] != 0) ? {ym_n[31:23], 1'b0, ym_n[22:1]} : ym_n;
    always @(posedge clk) if (rst_n) begin
        #0.1;
        if (va_r !== va_n) begin bad_a = bad_a + 1; if (bad_a < 6) $display("BAD add valid t=%0t ref=%b dut=%b", $time, va_r, va_n); end
        else if (va_r) begin
            nva = nva + 1;
            if (ya_c !== ya_r || ea_n !== ea_r || ya_n2 !== ya_n) begin
                bad_a = bad_a + 1;
                if (bad_a < 6) $display("BAD add t=%0t ref=%h/%0d dut=%h/%0d y2=%h", $time, ya_r, ea_r, ya_c, ea_n, ya_n2);
            end
        end
        if (vm_r !== vm_n) begin bad_m = bad_m + 1; if (bad_m < 6) $display("BAD mul valid t=%0t ref=%b dut=%b", $time, vm_r, vm_n); end
        else if (vm_r) begin
            nvm = nvm + 1;
            if (ym_c !== ym_r || em_n !== em_r || ym_n2 !== ym_n) begin
                bad_m = bad_m + 1;
                if (bad_m < 6) $display("BAD mul t=%0t ref=%h/%0d dut=%h/%0d y2=%h", $time, ym_r, em_r, ym_c, em_n, ym_n2);
            end
        end
    end
endmodule
