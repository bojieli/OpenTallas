`timescale 1ns/1ps
// safe-hbm S-C1 bench: ot_dsrom_su_hcpost_lane_pr (pin-registered) vs the unchanged ot_dsrom_su_hcpost_lane on the
// same random stimulus (random valid pattern, random FP32 operands incl. specials); the wrapper's outputs must equal
// the core's outputs exactly one cycle later on every cycle after reset.  Prints PASS_HCPOST_LANE_PR / FAIL.
module tb_hcpost_lane_pr #(parameter integer MUTANT = 0, parameter integer CYC = 20000, parameter integer SEED = 7);
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0, v = 0;
    reg [31:0] r0, r1, r2, r3, y, c0, c1, c2, c3, p;
    wire vo_a, fa_a, vo_b, fa_b; wire [31:0] o_a, o_b;
    ot_dsrom_su_hcpost_lane #(.ML(7), .AL(6)) ref_l (.clk(clk), .rst_n(rst_n), .v(v), .r0(r0), .r1(r1), .r2(r2), .r3(r3),
        .y(y), .c0(c0), .c1(c1), .c2(c2), .c3(c3), .p(p), .vo(vo_a), .o(o_a), .fault(fa_a));
    ot_dsrom_su_hcpost_lane_pr #(.ML(7), .AL(6), .MUTANT(MUTANT)) dut (.clk(clk), .rst_n(rst_n), .v(v), .r0(r0), .r1(r1),
        .r2(r2), .r3(r3), .y(y), .c0(c0), .c1(c1), .c2(c2), .c3(c3), .p(p), .vo(vo_b), .o(o_b), .fault(fa_b));
    integer s, cyc, bad, nv;
    reg vo_d, fa_d; reg [31:0] o_d;
    function [31:0] rf(input integer k);
        reg [31:0] x;
        begin
            x = $random(s);
            case (k % 16)
                0: rf = 32'h00000000; 1: rf = 32'h80000000; 2: rf = 32'h7f800000; 3: rf = 32'h00000001;
                4: rf = {x[31], 8'd0, x[22:0]};          // subnormal
                default: rf = {x[31], 8'd100 + x[27:23] , x[22:0]};
            endcase
        end
    endfunction
    initial begin
        s = SEED; bad = 0; nv = 0;
        {r0, r1, r2, r3, y, c0, c1, c2, c3, p} = 0;
        repeat (5) @(negedge clk); rst_n = 1;
        for (cyc = 0; cyc < CYC; cyc = cyc + 1) begin
            @(negedge clk);
            v = ($random(s) & 3) != 0;
            r0 = rf($random(s)); r1 = rf($random(s)); r2 = rf($random(s)); r3 = rf($random(s)); y = rf($random(s));
            c0 = rf($random(s)); c1 = rf($random(s)); c2 = rf($random(s)); c3 = rf($random(s)); p = rf($random(s));
        end
        repeat (40) @(negedge clk);
        if (bad == 0 && nv > CYC / 2) $display("PASS_HCPOST_LANE_PR cycles=%0d outputs=%0d latency=+1", CYC, nv);
        else $display("FAIL_HCPOST_LANE_PR mismatches=%0d outputs=%0d", bad, nv);
        $finish;
    end
    // compare: dut(t) == ref(t-1)
    always @(posedge clk) begin
        vo_d <= vo_a; fa_d <= fa_a; o_d <= o_a;
        if (rst_n && cyc > 2) begin
            if (vo_b !== vo_d || fa_b !== fa_d || (vo_d && o_b !== o_d)) begin
                bad = bad + 1;
                if (bad < 4) $display("MISMATCH cyc=%0d ref(vo=%b o=%h f=%b) dut(vo=%b o=%h f=%b)", cyc, vo_d, o_d, fa_d, vo_b, o_b, fa_b);
            end
            if (vo_d) nv = nv + 1;
        end
    end
endmodule
