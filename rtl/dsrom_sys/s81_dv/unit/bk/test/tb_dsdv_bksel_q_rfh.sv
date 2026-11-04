`timescale 1ns/1ps
// DIE-S81-51/RF-H 11-03 (S81-054 conservative form): lockstep bench dsdv_bksel_q RFH 0 (RF-C form) vs RFH 1 (negedge
// face flops on every input incl. rst + registered type-8 selects + per-group reset copies), both OLL 2, HQ quarter.
// Stimulus: posedge sender (inputs change just after the rising edge); lanes are biased to legal words (types 1/2/6/8
// with random payload, 1 in 8 fully random), commands / credits random.  The RFH 0 instance sees rst through one TB
// posedge register (RFH 1 asserts and releases the reset one edge later by design); every other input is the same
// signal.  Outputs (t_s, t_o) compared at every rising edge (pre-edge values) incl. a mid-run reset held 64 edges.
// Expected: equal on every edge.  Mutants: +define+OT_RFH_MUT_FACE (posedge face flops) and +define+OT_RFH_MUT_SEL
// (one select copy inverted) must FAIL.  Verdict line "BKSELQ_RFH".
module tb_dsdv_bksel_q_rfh;
    reg ck = 1'b0, rst = 1'b0, rst_d = 1'b0;
    always #0.4165 ck = ~ck;
    reg  [514:0] lane = 515'd0;
    reg  [65:0]  f_c = 66'd0;
    reg          f_cr = 1'b0;
    wire [864:0] tsa, tsb; wire [353:0] toa, tob;
    always @(posedge ck) rst_d <= rst;
    dsdv_bksel_q #(.OLL(2), .RFH(0)) ua (.ck(ck), .rst(rst_d), .lane(lane), .f_c(f_c), .f_cr(f_cr), .t_s(tsa), .t_o(toa));
    dsdv_bksel_q #(.OLL(2), .RFH(1)) ub (.ck(ck), .rst(rst),   .lane(lane), .f_c(f_c), .f_cr(f_cr), .t_s(tsb), .t_o(tob));
    integer cyc = 0, err = 0, tog = 0, ncmp = 0, ncyc = 4000, seed = 1, j, nbeat = 0;
    reg [1218:0] prev;
    reg [3:0] ty;
    initial begin
        if (!$value$plusargs("ncyc=%d", ncyc)) ncyc = 4000;
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        void'($urandom(seed));
    end
    always @(posedge ck) begin
        if (cyc > 12) begin
            ncmp = ncmp + 1;
            if ({tsa, toa} !== {tsb, tob}) begin err = err + 1; if (err < 6) $display("MISMATCH cyc %0d", cyc); end
            if ({tsa, toa} !== prev) tog = tog + 1;
            if (toa[0]) nbeat = nbeat + 1;
        end
        prev = {tsa, toa};
        cyc <= cyc + 1;
        #0.05;
        if (cyc == 8) rst = 1'b1;
        if (cyc == ncyc / 2) rst = 1'b0;
        if (cyc == ncyc / 2 + 64) rst = 1'b1;
        for (j = 0; j < 515; j = j + 32) lane[j +: 32] = $urandom;
        if ($urandom % 8 != 0) begin
            case ($urandom % 8)
                0: ty = 4'd1; 1: ty = 4'd6; 2, 3, 4: ty = 4'd8; default: ty = 4'd2;
            endcase
            lane[512:509] = ty; lane[0] = ($urandom % 4) != 0; lane[514] = 1'b0; lane[513] = 1'b1;
        end
        f_c = {$urandom, $urandom, $urandom};
        f_cr = ($urandom % 3) == 0;
        if (cyc == ncyc) begin
            $display("BKSELQ_RFH %0s cycles=%0d compared=%0d toggling_edges=%0d beats=%0d errors=%0d",
                     (err == 0 && tog > 0) ? "PASS" : "FAIL", cyc, ncmp, tog, nbeat, err);
            $finish;
        end
    end
endmodule
