`timescale 1ns/1ps
// S81-ARCH-RTL-2 11-12: HLAT bench of dsdv_bksel_q (bksplit_1108 profile, kit params OLL 2 RFH 2).  HLAT 0 vs HLAT 1, same
// random stimulus.  (a) every output bit, every capture edge: HLAT 1 == HLAT 0 (0 cycles, bit-exact).  (b) every lockup
// latch u_fl_{i0,c1,pend,o0m}: through the whole HIGH phase (rising + 1 ps .. falling - 1 ps) its q holds the value it had
// before the rising edge (the hold-safe property: the hop moves only after the falling edge).  Random stimulus reaches
// u_fl_i0 every cycle (the PASS needs it to toggle); full latch coverage is the layer bench HLK_COV (run_hlat_gates.sh).  +define+OT_S81PH_HLK_MUT (positive-level latch) must FAIL (b).  Verdict "DSDV_BKSEL_HLAT PASS|FAIL".
module tb_dsdv_bksel_hlat;
    reg ck = 1'b0, rst = 1'b0;
    always #0.4165 ck = ~ck;
    localparam integer NI = 515 + 66 + 1, NO = 865 + 354;
    reg  [NI-1:0] in;
    wire [NO-1:0] oa, ob;
    dsdv_bksel_q #(.OLL(2), .RFH(2), .HLAT(0)) ua (.ck(ck), .rst(rst), .lane(in[514:0]), .f_c(in[580:515]), .f_cr(in[581]), .t_s(oa[NO-1 -: 865]), .t_o(oa[353:0]));
    dsdv_bksel_q #(.OLL(2), .RFH(2), .HLAT(1)) ub (.ck(ck), .rst(rst), .lane(in[514:0]), .f_c(in[580:515]), .f_cr(in[581]), .t_s(ob[NO-1 -: 865]), .t_o(ob[353:0]));
    wire [1+16+256+320-1:0] l0 = ub.u_q.u_s.u_fl_i0.q;
    wire [2*16+16*37-1:0]   l1 = ub.u_q.u_s.u_fl_c1.q;
    wire [$bits(ub.u_q.u_s.u_fl_pend.q)-1:0] l2 = ub.u_q.u_s.u_fl_pend.q;
    wire [$bits(ub.u_q.u_s.u_fl_o0m.q)-1:0]  l3 = ub.u_q.u_s.u_fl_o0m.q;
    integer cyc, err, herr, tog, k, ncyc;
    integer lt [0:3];
    reg [NO-1:0] pa, pb, prev_a;
    reg [$bits(l0)-1:0] s0, q0; reg [$bits(l1)-1:0] s1, q1; reg [$bits(l2)-1:0] s2, q2; reg [$bits(l3)-1:0] s3, q3;
    task automatic rnd; integer j; begin for (j = 0; j < NI; j = j + 32) in[j +: 32] = $random; end endtask
    initial begin
        if (!$value$plusargs("ncyc=%d", ncyc)) ncyc = 400;
        err = 0; herr = 0; tog = 0; for (k = 0; k < 4; k = k + 1) lt[k] = 0; in = {NI{1'b0}};
        repeat (4) @(posedge ck); #0.1 rst = 1'b1;
        prev_a = oa; q0 = l0; q1 = l1; q2 = l2; q3 = l3;
        for (cyc = 0; cyc < ncyc; cyc = cyc + 1) begin
            @(negedge ck); #0.2 rnd;
            @(posedge ck);
        end
        $display("DSDV_BKSEL_HLAT %0s cycles %0d out_toggles %0d latch_toggles i0 %0d c1 %0d pend %0d o0m %0d out_errors %0d high_phase_errors %0d",
                 (err == 0 && herr == 0 && tog > 0 && lt[0] > 0) ? "PASS" : "FAIL",
                 ncyc, tog, lt[0], lt[1], lt[2], lt[3], err, herr);
        $finish;
    end
    always @(posedge ck) if (rst) begin
        pa = oa; pb = ob; s0 = l0; s1 = l1; s2 = l2; s3 = l3;
        for (k = 0; k < NO; k = k + 1) begin
            if (pb[k] !== pa[k]) begin err = err + 1; if (err < 6) $display("ERR out bit %0d hlat0 %b hlat1 %b t=%0t", k, pa[k], pb[k], $time); end
            if (pa[k] !== prev_a[k]) tog = tog + 1;
        end
        prev_a = pa;
        if (s0 !== q0) lt[0] = lt[0] + 1; if (s1 !== q1) lt[1] = lt[1] + 1; if (s2 !== q2) lt[2] = lt[2] + 1; if (s3 !== q3) lt[3] = lt[3] + 1;
        q0 = s0; q1 = s1; q2 = s2; q3 = s3;
        #0.001 if (l0 !== s0 || l1 !== s1 || l2 !== s2 || l3 !== s3) begin herr = herr + 1; if (herr < 6) $display("ERR latch moved at rise+1ps t=%0t", $time); end
        #0.414 if (l0 !== s0 || l1 !== s1 || l2 !== s2 || l3 !== s3) begin herr = herr + 1; if (herr < 6) $display("ERR latch moved in high phase t=%0t", $time); end
    end
endmodule
