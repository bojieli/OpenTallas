`timescale 1ns/1ps
// DIE-S81-51/RF-D 11-03 (S81-053): lockstep bench dsdv_bksel_c RNF 0 (old form) vs RNF 1 (rst through a negedge flop),
// both SELOH 1 / OLL 2 (the kits_seloh2 form).  Same stimulus (posedge sender: inputs and rst change just after the
// rising edge), outputs compared at every rising edge (pre-edge values), incl. a mid-run reset held 64 edges; the
// reset-assertion edge is excluded (RNF 1 asserts half an edge later by design).  Expected: equal on every other edge.
// +define+OT_RFD_MUT_RNF (rst sampled on the rising edge: release one edge late) must FAIL.  Verdict "BKSELC_RNF".
module tb_dsdv_bksel_c_rnf;
    reg ck = 1'b0, rst = 1'b0;
    always #0.4165 ck = ~ck;
    localparam integer NI = 4*865 + 4*354, NO = 4*66 + 4 + 367;
    reg  [NI-1:0] in = {NI{1'b0}};
    wire [NO-1:0] oa, ob;
    dsdv_bksel_c #(.OLL(2), .SELOH(1), .RNF(0)) ua (.ck(ck), .rst(rst), .f_s_s(in[0 +: 1730]), .f_s_n(in[1730 +: 1730]), .f_o_s(in[3460 +: 708]),
        .f_o_n(in[4168 +: 708]), .t_c_s(oa[0 +: 132]), .t_c_n(oa[132 +: 132]), .t_cr_s(oa[264 +: 2]), .t_cr_n(oa[266 +: 2]), .vd(oa[268 +: 367]));
    dsdv_bksel_c #(.OLL(2), .SELOH(1), .RNF(1)) ub (.ck(ck), .rst(rst), .f_s_s(in[0 +: 1730]), .f_s_n(in[1730 +: 1730]), .f_o_s(in[3460 +: 708]),
        .f_o_n(in[4168 +: 708]), .t_c_s(ob[0 +: 132]), .t_c_n(ob[132 +: 132]), .t_cr_s(ob[264 +: 2]), .t_cr_n(ob[266 +: 2]), .vd(ob[268 +: 367]));
    integer cyc = 0, err = 0, tog = 0, ncmp = 0, ncyc = 2000, seed = 1, j;
    reg [NO-1:0] prev;
    initial begin
        if (!$value$plusargs("ncyc=%d", ncyc)) ncyc = 2000;
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        void'($urandom(seed));
    end
    always @(posedge ck) begin
        if (cyc > 12 && !(cyc >= ncyc / 2 && cyc <= ncyc / 2 + 1)) begin
            ncmp = ncmp + 1;
            if (oa !== ob) begin err = err + 1; if (err < 6) $display("MISMATCH cyc %0d", cyc); end
            if (oa !== prev) tog = tog + 1;
        end
        prev = oa;
        cyc <= cyc + 1;
        #0.05;
        if (cyc == 8) rst = 1'b1;
        if (cyc == ncyc / 2) rst = 1'b0;
        if (cyc == ncyc / 2 + 64) rst = 1'b1;
        for (j = 0; j < NI; j = j + 32) in[j +: 32] = $urandom;
        if (cyc == ncyc) begin
            $display("BKSELC_RNF %0s cycles=%0d compared=%0d toggling_edges=%0d errors=%0d", (err == 0 && tog > 0) ? "PASS" : "FAIL", cyc, ncmp, tog, err);
            $finish;
        end
    end
endmodule
