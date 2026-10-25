`timescale 1ns/1ps
// HBM-W128 2026-10-25: valid-masked 4-state check of the HC multiplier reset fix.
//  (1) ot_hdc_fp32_mul_lat LAT 8: gold DRST 1 vs gate DRST 0: valid_out identical (!==) every cycle; y/err identical
//      whenever valid_out (gate data FFs start X: any X reaching a valid output fails).
//  (2) HC lane leaf ot_hdc_v41x_hcp_lanes G 8: gold = pre-fix source (multiplier DRST 1) vs gate = fixed source
//      (.DRST(ADRST) = 0): lf identical every cycle, y identical whenever the leaf's sum is valid (u_add valid + SOR).
// Random operands incl. zero/subnormal/inf/NaN classes, random valid, a mid-run reset pulse.  MUT_* defines inject the
// mutants that must be caught (MUT_NORST: no reset delivered to the gate multiplier; MUT_DATA: output data bit
// flipped).  MUT_VALID (one mid-pipeline valid bit unreset) is EXPECTED benign: reset is held >= 2 cycles with the clock
// running (decision 2), so its reset neighbours flush it; it is reported, not counted as a required catch.
module tb;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg v; reg [31:0] a, b;
    wire [31:0] yg, yt; wire [1:0] eg, et; wire vg, vt;
    ot_hdc_fp32_mul_lat #(.LAT(8), .DRST(1)) u_g (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(yg), .err(eg), .valid_out(vg));
`ifdef MUT_VALID
    ot_hdc_fp32_mul_lat_mv
`elsif MUT_DATA
    ot_hdc_fp32_mul_lat_md
`else
    ot_hdc_fp32_mul_lat
`endif
        #(.LAT(8), .DRST(0)) u_t (.clk(clk),
`ifdef MUT_NORST
        .rst_n(1'b1),      // mutant: reset never delivered to the gate multiplier (valid bits included)
`else
        .rst_n(rst_n),
`endif .valid_in(v), .a(a), .b(b), .y(yt), .err(et), .valid_out(vt));
    // leaf
    reg fst, gov; reg [7:0] lv, ss; reg [255:0] w, s; reg [127:0] x;
    wire [255:0] lyg, lyt; wire lfg, lft;
    gold_hcp_lanes u_lg (.clk(clk), .rst_n(rst_n), .fst(fst), .gov_i(gov), .lv_i(lv), .ss_i(ss), .w_i(w), .x_i(x), .s_i(s), .y(lyg), .lf(lfg));
    ot_hdc_v41x_hcp_lanes u_lt (.clk(clk), .rst_n(rst_n), .fst(fst), .gov_i(gov), .lv_i(lv), .ss_i(ss), .w_i(w), .x_i(x), .s_i(s), .y(lyt), .lf(lft));
    reg lvld; always @(posedge clk) lvld <= u_lg.g_lane[0].v1;   // SOR: y = so_q one edge after the adder output
    function [31:0] rop; input integer r; begin
        case (r % 8) 0: rop = 32'd0; 1: rop = {$random} & 32'h807fffff; 2: rop = {$random} | 32'h7f800000;
        3: rop = 32'h7f800000 ^ ({$random} & 32'h80000000); default: rop = $random; endcase end endfunction
    integer cyc = 0, nmul = 0, nleaf = 0, fails = 0;
    initial begin
        v = 0; a = 0; b = 0; fst = 0; gov = 0; lv = 0; ss = 0; w = 0; s = 0; x = 0;
        repeat (3) @(negedge clk); rst_n = 1;
        repeat (3000) begin
            @(negedge clk); cyc = cyc + 1;
            if (cyc == 1500) rst_n = 0; if (cyc == 1503) rst_n = 1;
            v = ($random % 3) != 0; a = rop($random); b = rop($random);
            fst = $random; gov = ($random % 3) != 0; lv = $random; ss = $random;
            w = {8{rop($random)}} ^ {$random, $random, $random, $random, $random, $random, $random, $random};
            x = {$random, $random, $random, $random}; s = {$random, $random, $random, $random, $random, $random, $random, $random};
        end
        $display("DRST_CHECK cycles=%0d mul_valid_compares=%0d leaf_valid_compares=%0d fails=%0d %s", cyc, nmul, nleaf, fails,
                 fails ? "FAIL" : "PASS");
        $finish;
    end
    always @(posedge clk) #0.5 if (rst_n) begin
        if (vg !== vt || (vg === 1'b1 && (yg !== yt || eg !== et))) begin
            fails = fails + 1; if (fails < 5) $display("MUL MISMATCH cyc %0d vg %b vt %b yg %h yt %h", cyc, vg, vt, yg, yt); end
        if (vg === 1'b1) nmul = nmul + 1;
        if (lfg !== lft || (lvld === 1'b1 && lyg !== lyt)) begin
            fails = fails + 1; if (fails < 5) $display("LEAF MISMATCH cyc %0d lf %b/%b", cyc, lfg, lft); end
        if (lvld === 1'b1) nleaf = nleaf + 1;
    end
endmodule
