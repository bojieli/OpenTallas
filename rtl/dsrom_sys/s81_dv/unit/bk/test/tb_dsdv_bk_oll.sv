`timescale 1ns/1ps
// DIE-S81-51/RF-C/bk 11-03: OLL bench.  Old form (OLL 0) vs re-formed (OLL 1) of one bk core, same random stimulus.
// Checks per cycle, on every output bit:
//   (a) at the capture edge (rising edge - 1 ps) the re-formed port == the old port  (0 cycles, bit-exact);
//   (b) through the whole HIGH phase (rising + 1 ps and falling - 1 ps) the re-formed port still holds the value
//       the old port had before the rising edge (the hold-safe property: it moves only after the falling edge).
// +define+OT_BK_OLL_MUT (positive-level latch) must FAIL.  Verdict: "DSDV_BK_OLL <top> PASS|FAIL".
module tb_dsdv_bk_oll;
    reg ck = 1'b0, rst = 1'b0;
    always #0.4165 ck = ~ck;
`ifdef TB_Q
    localparam integer NI = 515 + 66 + 1, NO = 865 + 354;
    reg  [NI-1:0] in;
    wire [NO-1:0] oa, ob;
    dsdv_bksel_q #(.OLL(0)) ua (.ck(ck), .rst(rst), .lane(in[514:0]), .f_c(in[580:515]), .f_cr(in[581]), .t_s(oa[NO-1 -: 865]), .t_o(oa[353:0]));
    dsdv_bksel_q #(.OLL(1)) ub (.ck(ck), .rst(rst), .lane(in[514:0]), .f_c(in[580:515]), .f_cr(in[581]), .t_s(ob[NO-1 -: 865]), .t_o(ob[353:0]));
    localparam [8*8-1:0] TOP = "bksel_q";
`else
    localparam integer NI = 4*865 + 4*354, NO = 4*66 + 4 + 367;
    reg  [NI-1:0] in;
    wire [NO-1:0] oa, ob;
    dsdv_bksel_c #(.OLL(0)) ua (.ck(ck), .rst(rst), .f_s_s(in[0 +: 1730]), .f_s_n(in[1730 +: 1730]), .f_o_s(in[3460 +: 708]),
        .f_o_n(in[4168 +: 708]), .t_c_s(oa[0 +: 132]), .t_c_n(oa[132 +: 132]), .t_cr_s(oa[264 +: 2]), .t_cr_n(oa[266 +: 2]), .vd(oa[268 +: 367]));
    dsdv_bksel_c #(.OLL(1)) ub (.ck(ck), .rst(rst), .f_s_s(in[0 +: 1730]), .f_s_n(in[1730 +: 1730]), .f_o_s(in[3460 +: 708]),
        .f_o_n(in[4168 +: 708]), .t_c_s(ob[0 +: 132]), .t_c_n(ob[132 +: 132]), .t_cr_s(ob[264 +: 2]), .t_cr_n(ob[266 +: 2]), .vd(ob[268 +: 367]));
    localparam [8*8-1:0] TOP = "bksel_c";
`endif
    integer cyc, err, tog, k, ncyc;
    reg [NO-1:0] pa, pb, prev_a;
    task automatic rnd; integer j; begin for (j = 0; j < NI; j = j + 32) in[j +: 32] = $random; end endtask
    initial begin
        if (!$value$plusargs("ncyc=%d", ncyc)) ncyc = 400;
        err = 0; tog = 0; in = {NI{1'b0}};
        repeat (4) @(posedge ck); #0.1 rst = 1'b1;
        prev_a = oa;
        for (cyc = 0; cyc < ncyc; cyc = cyc + 1) begin
            @(negedge ck); #0.2 rnd;                       // drive inputs in the low phase (any time is legal)
            @(posedge ck);
        end
        $display("DSDV_BK_OLL %0s %0s cycles %0d toggled_bits %0d errors %0d", TOP, (err == 0 && tog > 0) ? "PASS" : "FAIL", ncyc, tog, err);
        $finish;
    end
    // (a) capture edge
    always @(posedge ck) if (rst) begin
        pa = oa; pb = ob;                                   // values just before the edge (blocking sample at the edge,
                                                            // before NBA updates of the flops)
        for (k = 0; k < NO; k = k + 1) begin
            if (pb[k] !== pa[k]) begin err = err + 1; if (err < 6) $display("ERR capture bit %0d old %b new %b t=%0t", k, pa[k], pb[k], $time); end
            if (pa[k] !== prev_a[k]) tog = tog + 1;
        end
        prev_a = pa;
        #0.001 for (k = 0; k < NO; k = k + 1) if (ob[k] !== pa[k]) begin err = err + 1; if (err < 6) $display("ERR high+1ps bit %0d t=%0t", k, $time); end
        #0.414 for (k = 0; k < NO; k = k + 1) if (ob[k] !== pa[k]) begin err = err + 1; if (err < 6) $display("ERR high-end bit %0d t=%0t", k, $time); end
    end
endmodule
