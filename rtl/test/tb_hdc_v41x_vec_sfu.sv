`timescale 1ns/1ps
// Equivalence of the V4.1 vector unit's special-function pipes (rtl/hdc/v41x/ot_hdc_v41x_sfu.sv)
// against the repository's qualified five-stage pipes, one operand per cycle:
//   ot_hdc_v41x_fdiv (19)     vs ot_hdc_fdiv (31)       code and fault
//   ot_hdc_v41x_exp (49)      vs ot_hdc_exp (92)        code and fault
//   ot_hdc_v41x_rsqrt (37)    vs ot_hdc_rsqrt (61)      code where neither faults (both
//                             report a unit's refusal at that unit's own cycle, not
//                             aligned with vo, so fault timing is counted, not graded)
//   ot_hdc_v41x_softplus (162) vs ot_hdc_softplus (259) both results and fault
// Operands: random words with the exponent field biased toward the edges
// (subnormal, near-overflow, near 1).  +N=<count> sets the number of operands.
// Prints: V41XSFU n=<n> div_err=<e> exp_err=<e> rsq_err=<e> sp_err=<e>
module tb_hdc_v41x_vec_sfu (input wire clk);
    reg rst_n = 1'b0;
    integer cyc = 0, n = 200000, fed = 0;
    reg  [31:0] a, b;
    reg         v = 1'b0;
    reg  [31:0] seed = 32'h1234_5678;
    function automatic [31:0] rnd_word(input [31:0] r0, input [31:0] r1);
        reg [7:0] e;
        begin
            case (r1[2:0])
                3'd0: e = 8'd0;                          // subnormal / zero
                3'd1: e = 8'd1 + r1[5:3];                // bottom of the normals
                3'd2: e = 8'd254 - r1[5:3];              // near overflow
                3'd3: e = 8'd127 + {{5{r1[6]}}, r1[5:3]}; // near 1
                3'd4: e = 8'd100 + r1[9:3] % 8'd60;      // exp's live range
                default: e = r0[30:23];
            endcase
            rnd_word = {r0[31], e, r0[22:0]};
        end
    endfunction
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (rst_n && fed < n) begin
            a <= rnd_word($random, $random);
            b <= rnd_word($random, $random);
            v <= 1'b1;
            fed <= fed + 1;
        end else v <= 1'b0;
    end

    // division
    wire [31:0] dq, dr, dq_d;
    wire dvq, dvr, dfq, dfr, dfq_d, dvq_d;
    ot_hdc_v41x_fdiv u_nd (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(dq), .vo(dvq), .fault(dfq));
    ot_hdc_fdiv      u_rd (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(dr), .vo(dvr), .fault(dfr));
    ot_hdc_delay #(.W(34), .D(31 - 19), .RESET(1)) d_d (clk, rst_n, {dvq, dfq, dq}, {dvq_d, dfq_d, dq_d});
    // exp
    wire [31:0] eq, er, eq_d;
    wire evq, evr, efq, efr, evq_d, efq_d;
    ot_hdc_v41x_exp u_ne (.clk(clk), .rst_n(rst_n), .v(v), .x(a), .y(eq), .vo(evq), .fault(efq));
    ot_hdc_exp      u_re (.clk(clk), .rst_n(rst_n), .v(v), .x(a), .y(er), .vo(evr), .fault(efr));
    ot_hdc_delay #(.W(34), .D(92 - 49), .RESET(1)) d_e (clk, rst_n, {evq, efq, eq}, {evq_d, efq_d, eq_d});
    // rsqrt (argument |a|)
    wire [31:0] rq, rr, rq_d;
    wire rvq, rvr, rfq, rfr, rvq_d, rfq_d;
    ot_hdc_v41x_rsqrt u_nr (.clk(clk), .rst_n(rst_n), .v(v), .x({1'b0, a[30:0]}), .y(rq), .vo(rvq), .fault(rfq));
    ot_hdc_rsqrt      u_rr (.clk(clk), .rst_n(rst_n), .v(v), .x({1'b0, a[30:0]}), .y(rr), .vo(rvr), .fault(rfr));
    ot_hdc_delay #(.W(34), .D(61 - 37), .RESET(1)) d_r (clk, rst_n, {rvq, rfq, rq}, {rvq_d, rfq_d, rq_d});
    // softplus
    wire [31:0] sq, sr, tq, tr, sq_d, tq_d;
    wire svq, svr, sfq, sfr, svq_d, sfq_d;
    ot_hdc_v41x_softplus u_ns (.clk(clk), .rst_n(rst_n), .v(v), .x(a), .sp(sq), .r(tq), .vo(svq), .fault(sfq));
    ot_hdc_softplus      u_rs (.clk(clk), .rst_n(rst_n), .v(v), .x(a), .sp(sr), .r(tr), .vo(svr), .fault(sfr));
    ot_hdc_delay #(.W(66), .D(259 - 162), .RESET(1)) d_s (clk, rst_n, {svq, sfq, sq, tq}, {svq_d, sfq_d, sq_d, tq_d});

    integer rsq_fm = 0;
    integer de = 0, ee = 0, re = 0, se = 0, dn = 0, en = 0, rn = 0, sn = 0;
    always @(posedge clk) if (rst_n) begin
        if (dvr) begin dn = dn + 1; if (!dvq_d || dfq_d != dfr || (!dfr && dq_d != dr)) de = de + 1; end
        if (evr) begin en = en + 1; if (!evq_d || efq_d != efr || (!efr && eq_d != er)) ee = ee + 1; end
        if (rvr) begin rn = rn + 1; if (!rvq_d || (!rfr && !rfq_d && rq_d != rr)) re = re + 1;
            if (rfr != rfq_d) rsq_fm = rsq_fm + 1; end
        if (svr) begin sn = sn + 1;
            if (!svq_d || sfq_d != sfr || (!sfr && (sq_d != sr || tq_d != tr))) se = se + 1; end
        if (fed == n && cyc > n + 400) begin
            $display("V41XSFU n=%0d div=%0d div_err=%0d exp=%0d exp_err=%0d rsq=%0d rsq_err=%0d rsq_fault_timing=%0d sp=%0d sp_err=%0d",
                     n, dn, de, en, ee, rn, re, rsq_fm, sn, se);
            $finish;
        end
    end
    initial begin
        if (!$value$plusargs("N=%d", n)) n = 200000;
    end
endmodule
