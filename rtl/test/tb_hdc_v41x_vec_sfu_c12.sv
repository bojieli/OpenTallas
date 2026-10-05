`timescale 1ns/1ps
// HBM SU c12 (claude hbm-su-attn, 2026-10-05): FILE SWAP of rtl/test/tb_hdc_v41x_vec_sfu.sv for the c12 build
// (rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv + rtl/hdc/ot_hdc_fastfp_lat_c12.sv): the same equivalence of the vector unit's
// special-function pipes against the repository's qualified five-stage pipes, one operand per cycle, with every
// pair aligned by whichever is shallower (at MLAT 6 / ALAT 6 the fast pipes are deeper than some references):
//   divider (DDIV: ot_dsrom_fdiv_f12 at 21, else ot_hdc_v41x_fdiv)  vs ot_hdc_fdiv (31)   code and fault
//   ot_hdc_v41x_exp                                                 vs ot_hdc_exp (92)    code and fault
//   ot_hdc_v41x_rsqrt                                               vs ot_hdc_rsqrt (61)  code where neither faults
//   ot_hdc_v41x_softplus #(DDIV, FSQ)                               vs ot_hdc_softplus (259) both results and fault
//   square root (FSQ: ot_hdc_fsqrt_c12, else ot_hdc_fsqrt)          vs ot_hdc_fsqrt (31)  code and fault
// Prints: V41XSFU n=.. div=.. div_err=.. exp=.. exp_err=.. rsq=.. rsq_err=.. rsq_fault_timing=.. sp=.. sp_err=..
//         sq=.. sq_err=..   and stops with $fatal (nonzero exit) on any error.
module tb_hdc_v41x_vec_sfu #(parameter integer MLAT = 6, parameter integer ALAT = 6, parameter integer DDIV = 21,
                             parameter integer FSQ = 1) (input wire clk);
    reg rst_n = 1'b0;
    integer cyc = 0, n = 200000, fed = 0;
    reg  [31:0] a, b;
    reg         v = 1'b0;
    function automatic [31:0] rnd_word(input [31:0] r0, input [31:0] r1);
        reg [7:0] e;
        begin
            case (r1[2:0])
                3'd0: e = 8'd0;
                3'd1: e = 8'd1 + r1[5:3];
                3'd2: e = 8'd254 - r1[5:3];
                3'd3: e = 8'd127 + {{5{r1[6]}}, r1[5:3]};
                3'd4: e = 8'd100 + r1[9:3] % 8'd60;
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
    localparam integer DQ_DIV = DDIV, DR_DIV = 31;
    localparam integer DQ_EXP = 7 * MLAT + 8 * ALAT + 4, DR_EXP = 92;
    localparam integer DQ_RSQ = 1 + 9 * MLAT + 3 * ALAT, DR_RSQ = 61;
    localparam integer DQ_SP = DQ_EXP + 11 * MLAT + 10 * ALAT + 31 + DDIV, DR_SP = 259;
    localparam integer DQ_SQ = 31, DR_SQ = 31;
    // align: the shallower of the pair is delayed to the deeper one
    `define OT_ALIGN(NM, W, DQ, DR, QIN, RIN, QOUT, ROUT) \
        generate if ((DQ) <= (DR)) begin : NM``_q \
            ot_hdc_delay #(.W(W), .D((DR) - (DQ)), .RESET(1)) u (clk, rst_n, QIN, QOUT); assign ROUT = RIN; \
        end else begin : NM``_r \
            ot_hdc_delay #(.W(W), .D((DQ) - (DR)), .RESET(1)) u (clk, rst_n, RIN, ROUT); assign QOUT = QIN; \
        end endgenerate
    // division
    wire [31:0] dq, dr; wire dvq, dvr, dfq, dfr;
    generate if (DDIV == 21) begin : g_d21
        ot_dsrom_fdiv_f12 u_nd (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(dq), .vo(dvq), .fault(dfq));
    end else begin : g_d19
        ot_hdc_v41x_fdiv u_nd (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(dq), .vo(dvq), .fault(dfq));
    end endgenerate
    ot_hdc_fdiv u_rd (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(dr), .vo(dvr), .fault(dfr));
    wire [33:0] dq_c, dr_c;
    `OT_ALIGN(g_ad, 34, DQ_DIV, DR_DIV, ({dvq, dfq, dq}), ({dvr, dfr, dr}), dq_c, dr_c)
    // exp
    wire [31:0] eq, er; wire evq, evr, efq, efr;
    ot_hdc_v41x_exp #(.LM(MLAT), .LA(ALAT)) u_ne (.clk(clk), .rst_n(rst_n), .v(v), .x(a), .y(eq), .vo(evq), .fault(efq));
    ot_hdc_exp u_re (.clk(clk), .rst_n(rst_n), .v(v), .x(a), .y(er), .vo(evr), .fault(efr));
    wire [33:0] eq_c, er_c;
    `OT_ALIGN(g_ae, 34, DQ_EXP, DR_EXP, ({evq, efq, eq}), ({evr, efr, er}), eq_c, er_c)
    // rsqrt (argument |a|)
    wire [31:0] rq, rr; wire rvq, rvr, rfq, rfr;
    ot_hdc_v41x_rsqrt #(.LM(MLAT), .LA(ALAT)) u_nr (.clk(clk), .rst_n(rst_n), .v(v), .x({1'b0, a[30:0]}), .y(rq), .vo(rvq), .fault(rfq));
    ot_hdc_rsqrt u_rr (.clk(clk), .rst_n(rst_n), .v(v), .x({1'b0, a[30:0]}), .y(rr), .vo(rvr), .fault(rfr));
    wire [33:0] rq_c, rr_c;
    `OT_ALIGN(g_ar, 34, DQ_RSQ, DR_RSQ, ({rvq, rfq, rq}), ({rvr, rfr, rr}), rq_c, rr_c)
    // softplus
    wire [31:0] sq, sr, tq, tr; wire svq, svr, sfq, sfr;
    ot_hdc_v41x_softplus #(.LM(MLAT), .LA(ALAT), .DDIV(DDIV), .FSQ(FSQ)) u_ns (.clk(clk), .rst_n(rst_n), .v(v), .x(a), .sp(sq), .r(tq), .vo(svq), .fault(sfq));
    ot_hdc_softplus u_rs (.clk(clk), .rst_n(rst_n), .v(v), .x(a), .sp(sr), .r(tr), .vo(svr), .fault(sfr));
    wire [65:0] sq_c, sr_c;
    `OT_ALIGN(g_as, 66, DQ_SP, DR_SP, ({svq, sfq, sq, tq}), ({svr, sfr, sr, tr}), sq_c, sr_c)
    // square root (argument |a|, and a itself: negatives fault)
    wire [31:0] qq, qr; wire qvq, qvr, qfq, qfr;
    generate if (FSQ != 0) begin : g_sq12
        ot_hdc_fsqrt_c12 u_nq (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .y(qq), .vo(qvq), .fault(qfq));
    end else begin : g_sq
        ot_hdc_fsqrt u_nq (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .y(qq), .vo(qvq), .fault(qfq));
    end endgenerate
    ot_hdc_fsqrt u_rq (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .y(qr), .vo(qvr), .fault(qfr));
    `undef OT_ALIGN

    integer rsq_fm = 0;
    integer de = 0, ee = 0, re = 0, se = 0, qe = 0, dn = 0, en = 0, rn = 0, sn = 0, qn = 0;
    always @(posedge clk) if (rst_n) begin
        if (dr_c[33]) begin dn = dn + 1; if (!dq_c[33] || dq_c[32] != dr_c[32] || (!dr_c[32] && dq_c[31:0] != dr_c[31:0])) de = de + 1; end
        if (er_c[33]) begin en = en + 1; if (!eq_c[33] || eq_c[32] != er_c[32] || (!er_c[32] && eq_c[31:0] != er_c[31:0])) ee = ee + 1; end
        if (rr_c[33]) begin rn = rn + 1; if (!rq_c[33] || (!rr_c[32] && !rq_c[32] && rq_c[31:0] != rr_c[31:0])) re = re + 1;
            if (rr_c[32] != rq_c[32]) rsq_fm = rsq_fm + 1; end
        if (sr_c[65]) begin sn = sn + 1;
            if (!sq_c[65] || sq_c[64] != sr_c[64] || (!sr_c[64] && sq_c[63:0] != sr_c[63:0])) se = se + 1; end
        if (qvr) begin qn = qn + 1; if (!qvq || qfq != qfr || qq != qr) qe = qe + 1; end
        if (fed == n && cyc > n + 600) begin
            $display("V41XSFU n=%0d div=%0d div_err=%0d exp=%0d exp_err=%0d rsq=%0d rsq_err=%0d rsq_fault_timing=%0d sp=%0d sp_err=%0d sq=%0d sq_err=%0d",
                     n, dn, de, en, ee, rn, re, rsq_fm, sn, se, qn, qe);
            if (de || ee || re || se || qe || dn == 0 || en == 0 || rn == 0 || sn == 0 || qn == 0) $fatal(1, "V41XSFU MISMATCH");
            $finish;
        end
    end
    initial begin
        if (!$value$plusargs("N=%d", n)) n = 200000;
    end
endmodule
