// GENERATED: exact selected s8 column0 NCH4 READ1/FILL1 chains, real leaf returns. No whole-parent age claim.
`timescale 1ns/1ps
// tb_xhead3: lockstep of the structural successor qfd_dv_s5_xhead3 against the current leaf qfd_dv_s5_xhead
// (rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv + ot_qfd_xhead).  Both see the same a_d / cid / rst_n; the leaf answers lq / lq_v /
// lq_bad and fault_i reach the successor one edge later (its read requests leave one edge later).  Every output is
// compared every edge: new(t + 1) == old(t).  Stimulus: legal x-slice operations (descriptor, data beats aimed at the
// tile windows, go with the matching instruction, back-to-back / overlapped epochs, pooled k 24 / 32 at split 7),
// interleaved with illegal / random words (faults), random leaf answers, quiesced mid-run resets.
// +seed=N +cycles=N +cid=N.  Prints S5_XH3_EQ PASS <compares> ... or S5_XH3_EQ FAIL <first mismatch>.
module tb_s8_column;
    localparam integer AW = 24, NW = 18, XCW = 12, NH = 8, NR = 16, IBW = 379, FW = 1187, HW = 1567, DESC = 73;
    reg ck = 1'b0;
    reg rst_n = 1'b0;
    reg [5:0] cid = 6'd0;
    reg fault_i = 1'b0, fault_i_d = 1'b0;
    reg [HW-1:0] a_d = {HW{1'b0}};
    wire [511:0] lq,lq_d;
    wire[7:0]lq_v,lq_v_d,lq_bad,lq_bad_d;
    wire [515:0] o_n, o_s, n_n, n_s;
    wire [1:0] o_lwv, o_lwep, o_lcv, o_lcep, n_lwv, n_lwep, n_lcv, n_lcep;
    wire [11:0] o_lwoff, n_lwoff;
    wire [127:0] o_lwm, n_lwm;
    wire [2047:0] o_lwd, n_lwd;
    wire [143:0] o_lwctl, n_lwctl;
    wire [7:0] o_lrv, o_lrt, o_lrep, n_lrv, n_lrt, n_lrep;
    wire [223:0] o_lrp, n_lrp;
    wire o_lrst, n_lrst, o_flt, n_flt;
    qfd_dv_s5_xhead u_old (.ck(ck), .rst_n(rst_n), .cid(cid), .fault_i(fault_i), .a_d(a_d), .n_d(o_n), .s_d(o_s),
        .lw_v(o_lwv), .lw_ep(o_lwep), .lc_v(o_lcv), .lc_ep(o_lcep), .lw_off(o_lwoff), .lw_m(o_lwm), .lw_d(o_lwd),
        .lw_ctl(o_lwctl), .lr_v(o_lrv), .lr_t(o_lrt), .lr_ep(o_lrep), .lr_p(o_lrp), .lq(lq), .lq_v(lq_v),
        .lq_bad(lq_bad), .l_rst_n(o_lrst), .fault(o_flt));
    qfd_dv_s5_xhead3 u_new (.ck(ck), .rst_n(rst_n), .cid(cid), .fault_i(fault_i_d), .a_d(a_d), .n_d(n_n), .s_d(n_s),
        .lw_v(n_lwv), .lw_ep(n_lwep), .lc_v(n_lcv), .lc_ep(n_lcep), .lw_off(n_lwoff), .lw_m(n_lwm), .lw_d(n_lwd),
        .lw_ctl(n_lwctl), .lr_v(n_lrv), .lr_t(n_lrt), .lr_ep(n_lrep), .lr_p(n_lrp), .lq(lq_d), .lq_v(lq_v_d),
        .lq_bad(lq_bad_d), .l_rst_n(n_lrst), .fault(n_flt));
`ifdef OT_S8_COL_MUT_READ0
 localparam NEW_READ=0;
`else
 localparam NEW_READ=1;
`endif
generate begin : o_real_leaves
    wire x00cv0, x00cep0, x00wv0, x00wep0; wire [5:0] x00woff0; wire [63:0] x00wm0; wire [1023:0] x00wd0; wire [71:0] x00wc0;
    wire x00cv1, x00cep1, x00wv1, x00wep1; wire [5:0] x00woff1; wire [63:0] x00wm1; wire [1023:0] x00wd1; wire [71:0] x00wc1;
    wire x00cv2, x00cep2, x00wv2, x00wep2; wire [5:0] x00woff2; wire [63:0] x00wm2; wire [1023:0] x00wd2; wire [71:0] x00wc2;
    wire x00cv3, x00cep3, x00wv3, x00wep3; wire [5:0] x00woff3; wire [63:0] x00wm3; wire [1023:0] x00wd3; wire [71:0] x00wc3;
    wire x00cv4, x00cep4, x00wv4, x00wep4; wire [5:0] x00woff4; wire [63:0] x00wm4; wire [1023:0] x00wd4; wire [71:0] x00wc4;
    assign x00cv0 = o_lcv[0]; assign x00cep0 = o_lcep[0]; assign x00wv0 = o_lwv[0]; assign x00wep0 = o_lwep[0];
    assign x00woff0 = o_lwoff[5:0]; assign x00wm0 = o_lwm[63:0]; assign x00wd0 = o_lwd[1023:0]; assign x00wc0 = o_lwctl[71:0];
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`endif
`endif
        u_xl0_0 (.clk(ck), .rst_n(rst_n),
        .w_v(x00wv0), .w_ep(x00wep0), .w_off(x00woff0), .w_m(x00wm0), .w_d(x00wd0), .w_ctl(x00wc0),
        .c_v(x00cv0), .c_ep(x00cep0), .wo_v(x00wv1), .wo_ep(x00wep1), .wo_off(x00woff1),
        .wo_m(x00wm1), .wo_d(x00wd1), .wo_ctl(x00wc1), .co_v(x00cv1), .co_ep(x00cep1),
        .r_v(o_lrv[0]), .r_t(o_lrt[0]), .r_ep(o_lrep[0]), .r_p(o_lrp[27:0]),
        .q_v(lq_v[0]), .q(lq[63:0]), .q_bad(lq_bad[0]));
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`endif
`endif
        u_xl0_1 (.clk(ck), .rst_n(rst_n),
        .w_v(x00wv1), .w_ep(x00wep1), .w_off(x00woff1), .w_m(x00wm1), .w_d(x00wd1), .w_ctl(x00wc1),
        .c_v(x00cv1), .c_ep(x00cep1), .wo_v(x00wv2), .wo_ep(x00wep2), .wo_off(x00woff2),
        .wo_m(x00wm2), .wo_d(x00wd2), .wo_ctl(x00wc2), .co_v(x00cv2), .co_ep(x00cep2),
        .r_v(o_lrv[1]), .r_t(o_lrt[1]), .r_ep(o_lrep[1]), .r_p(o_lrp[55:28]),
        .q_v(lq_v[1]), .q(lq[127:64]), .q_bad(lq_bad[1]));
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`endif
`endif
        u_xl0_2 (.clk(ck), .rst_n(rst_n),
        .w_v(x00wv2), .w_ep(x00wep2), .w_off(x00woff2), .w_m(x00wm2), .w_d(x00wd2), .w_ctl(x00wc2),
        .c_v(x00cv2), .c_ep(x00cep2), .wo_v(x00wv3), .wo_ep(x00wep3), .wo_off(x00woff3),
        .wo_m(x00wm3), .wo_d(x00wd3), .wo_ctl(x00wc3), .co_v(x00cv3), .co_ep(x00cep3),
        .r_v(o_lrv[2]), .r_t(o_lrt[2]), .r_ep(o_lrep[2]), .r_p(o_lrp[83:56]),
        .q_v(lq_v[2]), .q(lq[191:128]), .q_bad(lq_bad[2]));
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`endif
`endif
        u_xl0_3 (.clk(ck), .rst_n(rst_n),
        .w_v(x00wv3), .w_ep(x00wep3), .w_off(x00woff3), .w_m(x00wm3), .w_d(x00wd3), .w_ctl(x00wc3),
        .c_v(x00cv3), .c_ep(x00cep3), .wo_v(x00wv4), .wo_ep(x00wep4), .wo_off(x00woff4),
        .wo_m(x00wm4), .wo_d(x00wd4), .wo_ctl(x00wc4), .co_v(x00cv4), .co_ep(x00cep4),
        .r_v(o_lrv[3]), .r_t(o_lrt[3]), .r_ep(o_lrep[3]), .r_p(o_lrp[111:84]),
        .q_v(lq_v[3]), .q(lq[255:192]), .q_bad(lq_bad[3]));
    wire x01cv0, x01cep0, x01wv0, x01wep0; wire [5:0] x01woff0; wire [63:0] x01wm0; wire [1023:0] x01wd0; wire [71:0] x01wc0;
    wire x01cv1, x01cep1, x01wv1, x01wep1; wire [5:0] x01woff1; wire [63:0] x01wm1; wire [1023:0] x01wd1; wire [71:0] x01wc1;
    wire x01cv2, x01cep2, x01wv2, x01wep2; wire [5:0] x01woff2; wire [63:0] x01wm2; wire [1023:0] x01wd2; wire [71:0] x01wc2;
    wire x01cv3, x01cep3, x01wv3, x01wep3; wire [5:0] x01woff3; wire [63:0] x01wm3; wire [1023:0] x01wd3; wire [71:0] x01wc3;
    wire x01cv4, x01cep4, x01wv4, x01wep4; wire [5:0] x01woff4; wire [63:0] x01wm4; wire [1023:0] x01wd4; wire [71:0] x01wc4;
    assign x01cv0 = o_lcv[1]; assign x01cep0 = o_lcep[1]; assign x01wv0 = o_lwv[1]; assign x01wep0 = o_lwep[1];
    assign x01woff0 = o_lwoff[11:6]; assign x01wm0 = o_lwm[127:64]; assign x01wd0 = o_lwd[2047:1024]; assign x01wc0 = o_lwctl[143:72];
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`endif
`endif
        u_xl0_4 (.clk(ck), .rst_n(rst_n),
        .w_v(x01wv0), .w_ep(x01wep0), .w_off(x01woff0), .w_m(x01wm0), .w_d(x01wd0), .w_ctl(x01wc0),
        .c_v(x01cv0), .c_ep(x01cep0), .wo_v(x01wv1), .wo_ep(x01wep1), .wo_off(x01woff1),
        .wo_m(x01wm1), .wo_d(x01wd1), .wo_ctl(x01wc1), .co_v(x01cv1), .co_ep(x01cep1),
        .r_v(o_lrv[4]), .r_t(o_lrt[4]), .r_ep(o_lrep[4]), .r_p(o_lrp[139:112]),
        .q_v(lq_v[4]), .q(lq[319:256]), .q_bad(lq_bad[4]));
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`endif
`endif
        u_xl0_5 (.clk(ck), .rst_n(rst_n),
        .w_v(x01wv1), .w_ep(x01wep1), .w_off(x01woff1), .w_m(x01wm1), .w_d(x01wd1), .w_ctl(x01wc1),
        .c_v(x01cv1), .c_ep(x01cep1), .wo_v(x01wv2), .wo_ep(x01wep2), .wo_off(x01woff2),
        .wo_m(x01wm2), .wo_d(x01wd2), .wo_ctl(x01wc2), .co_v(x01cv2), .co_ep(x01cep2),
        .r_v(o_lrv[5]), .r_t(o_lrt[5]), .r_ep(o_lrep[5]), .r_p(o_lrp[167:140]),
        .q_v(lq_v[5]), .q(lq[383:320]), .q_bad(lq_bad[5]));
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`endif
`endif
        u_xl0_6 (.clk(ck), .rst_n(rst_n),
        .w_v(x01wv2), .w_ep(x01wep2), .w_off(x01woff2), .w_m(x01wm2), .w_d(x01wd2), .w_ctl(x01wc2),
        .c_v(x01cv2), .c_ep(x01cep2), .wo_v(x01wv3), .wo_ep(x01wep3), .wo_off(x01woff3),
        .wo_m(x01wm3), .wo_d(x01wd3), .wo_ctl(x01wc3), .co_v(x01cv3), .co_ep(x01cep3),
        .r_v(o_lrv[6]), .r_t(o_lrt[6]), .r_ep(o_lrep[6]), .r_p(o_lrp[195:168]),
        .q_v(lq_v[6]), .q(lq[447:384]), .q_bad(lq_bad[6]));
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
`endif
`endif
        u_xl0_7 (.clk(ck), .rst_n(rst_n),
        .w_v(x01wv3), .w_ep(x01wep3), .w_off(x01woff3), .w_m(x01wm3), .w_d(x01wd3), .w_ctl(x01wc3),
        .c_v(x01cv3), .c_ep(x01cep3), .wo_v(x01wv4), .wo_ep(x01wep4), .wo_off(x01woff4),
        .wo_m(x01wm4), .wo_d(x01wd4), .wo_ctl(x01wc4), .co_v(x01cv4), .co_ep(x01cep4),
        .r_v(o_lrv[7]), .r_t(o_lrt[7]), .r_ep(o_lrep[7]), .r_p(o_lrp[223:196]),
        .q_v(lq_v[7]), .q(lq[511:448]), .q_bad(lq_bad[7]));

end endgenerate
generate begin : n_real_leaves
    wire x00cv0, x00cep0, x00wv0, x00wep0; wire [5:0] x00woff0; wire [63:0] x00wm0; wire [1023:0] x00wd0; wire [71:0] x00wc0;
    wire x00cv1, x00cep1, x00wv1, x00wep1; wire [5:0] x00woff1; wire [63:0] x00wm1; wire [1023:0] x00wd1; wire [71:0] x00wc1;
    wire x00cv2, x00cep2, x00wv2, x00wep2; wire [5:0] x00woff2; wire [63:0] x00wm2; wire [1023:0] x00wd2; wire [71:0] x00wc2;
    wire x00cv3, x00cep3, x00wv3, x00wep3; wire [5:0] x00woff3; wire [63:0] x00wm3; wire [1023:0] x00wd3; wire [71:0] x00wc3;
    wire x00cv4, x00cep4, x00wv4, x00wep4; wire [5:0] x00woff4; wire [63:0] x00wm4; wire [1023:0] x00wd4; wire [71:0] x00wc4;
    assign x00cv0 = n_lcv[0]; assign x00cep0 = n_lcep[0]; assign x00wv0 = n_lwv[0]; assign x00wep0 = n_lwep[0];
    assign x00woff0 = n_lwoff[5:0]; assign x00wm0 = n_lwm[63:0]; assign x00wd0 = n_lwd[1023:0]; assign x00wc0 = n_lwctl[71:0];
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`endif
`endif
        u_xl0_0 (.clk(ck), .rst_n(rst_n),
        .w_v(x00wv0), .w_ep(x00wep0), .w_off(x00woff0), .w_m(x00wm0), .w_d(x00wd0), .w_ctl(x00wc0),
        .c_v(x00cv0), .c_ep(x00cep0), .wo_v(x00wv1), .wo_ep(x00wep1), .wo_off(x00woff1),
        .wo_m(x00wm1), .wo_d(x00wd1), .wo_ctl(x00wc1), .co_v(x00cv1), .co_ep(x00cep1),
        .r_v(n_lrv[0]), .r_t(n_lrt[0]), .r_ep(n_lrep[0]), .r_p(n_lrp[27:0]),
        .q_v(lq_v_d[0]), .q(lq_d[63:0]), .q_bad(lq_bad_d[0]));
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`endif
`endif
        u_xl0_1 (.clk(ck), .rst_n(rst_n),
        .w_v(x00wv1), .w_ep(x00wep1), .w_off(x00woff1), .w_m(x00wm1), .w_d(x00wd1), .w_ctl(x00wc1),
        .c_v(x00cv1), .c_ep(x00cep1), .wo_v(x00wv2), .wo_ep(x00wep2), .wo_off(x00woff2),
        .wo_m(x00wm2), .wo_d(x00wd2), .wo_ctl(x00wc2), .co_v(x00cv2), .co_ep(x00cep2),
        .r_v(n_lrv[1]), .r_t(n_lrt[1]), .r_ep(n_lrep[1]), .r_p(n_lrp[55:28]),
        .q_v(lq_v_d[1]), .q(lq_d[127:64]), .q_bad(lq_bad_d[1]));
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`endif
`endif
        u_xl0_2 (.clk(ck), .rst_n(rst_n),
        .w_v(x00wv2), .w_ep(x00wep2), .w_off(x00woff2), .w_m(x00wm2), .w_d(x00wd2), .w_ctl(x00wc2),
        .c_v(x00cv2), .c_ep(x00cep2), .wo_v(x00wv3), .wo_ep(x00wep3), .wo_off(x00woff3),
        .wo_m(x00wm3), .wo_d(x00wd3), .wo_ctl(x00wc3), .co_v(x00cv3), .co_ep(x00cep3),
        .r_v(n_lrv[2]), .r_t(n_lrt[2]), .r_ep(n_lrep[2]), .r_p(n_lrp[83:56]),
        .q_v(lq_v_d[2]), .q(lq_d[191:128]), .q_bad(lq_bad_d[2]));
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`endif
`endif
        u_xl0_3 (.clk(ck), .rst_n(rst_n),
        .w_v(x00wv3), .w_ep(x00wep3), .w_off(x00woff3), .w_m(x00wm3), .w_d(x00wd3), .w_ctl(x00wc3),
        .c_v(x00cv3), .c_ep(x00cep3), .wo_v(x00wv4), .wo_ep(x00wep4), .wo_off(x00woff4),
        .wo_m(x00wm4), .wo_d(x00wd4), .wo_ctl(x00wc4), .co_v(x00cv4), .co_ep(x00cep4),
        .r_v(n_lrv[3]), .r_t(n_lrt[3]), .r_ep(n_lrep[3]), .r_p(n_lrp[111:84]),
        .q_v(lq_v_d[3]), .q(lq_d[255:192]), .q_bad(lq_bad_d[3]));
    wire x01cv0, x01cep0, x01wv0, x01wep0; wire [5:0] x01woff0; wire [63:0] x01wm0; wire [1023:0] x01wd0; wire [71:0] x01wc0;
    wire x01cv1, x01cep1, x01wv1, x01wep1; wire [5:0] x01woff1; wire [63:0] x01wm1; wire [1023:0] x01wd1; wire [71:0] x01wc1;
    wire x01cv2, x01cep2, x01wv2, x01wep2; wire [5:0] x01woff2; wire [63:0] x01wm2; wire [1023:0] x01wd2; wire [71:0] x01wc2;
    wire x01cv3, x01cep3, x01wv3, x01wep3; wire [5:0] x01woff3; wire [63:0] x01wm3; wire [1023:0] x01wd3; wire [71:0] x01wc3;
    wire x01cv4, x01cep4, x01wv4, x01wep4; wire [5:0] x01woff4; wire [63:0] x01wm4; wire [1023:0] x01wd4; wire [71:0] x01wc4;
    assign x01cv0 = n_lcv[1]; assign x01cep0 = n_lcep[1]; assign x01wv0 = n_lwv[1]; assign x01wep0 = n_lwep[1];
    assign x01woff0 = n_lwoff[11:6]; assign x01wm0 = n_lwm[127:64]; assign x01wd0 = n_lwd[2047:1024]; assign x01wc0 = n_lwctl[143:72];
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`endif
`endif
        u_xl0_4 (.clk(ck), .rst_n(rst_n),
        .w_v(x01wv0), .w_ep(x01wep0), .w_off(x01woff0), .w_m(x01wm0), .w_d(x01wd0), .w_ctl(x01wc0),
        .c_v(x01cv0), .c_ep(x01cep0), .wo_v(x01wv1), .wo_ep(x01wep1), .wo_off(x01woff1),
        .wo_m(x01wm1), .wo_d(x01wd1), .wo_ctl(x01wc1), .co_v(x01cv1), .co_ep(x01cep1),
        .r_v(n_lrv[4]), .r_t(n_lrt[4]), .r_ep(n_lrep[4]), .r_p(n_lrp[139:112]),
        .q_v(lq_v_d[4]), .q(lq_d[319:256]), .q_bad(lq_bad_d[4]));
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`endif
`endif
        u_xl0_5 (.clk(ck), .rst_n(rst_n),
        .w_v(x01wv1), .w_ep(x01wep1), .w_off(x01woff1), .w_m(x01wm1), .w_d(x01wd1), .w_ctl(x01wc1),
        .c_v(x01cv1), .c_ep(x01cep1), .wo_v(x01wv2), .wo_ep(x01wep2), .wo_off(x01woff2),
        .wo_m(x01wm2), .wo_d(x01wd2), .wo_ctl(x01wc2), .co_v(x01cv2), .co_ep(x01cep2),
        .r_v(n_lrv[5]), .r_t(n_lrt[5]), .r_ep(n_lrep[5]), .r_p(n_lrp[167:140]),
        .q_v(lq_v_d[5]), .q(lq_d[383:320]), .q_bad(lq_bad_d[5]));
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`endif
`endif
        u_xl0_6 (.clk(ck), .rst_n(rst_n),
        .w_v(x01wv2), .w_ep(x01wep2), .w_off(x01woff2), .w_m(x01wm2), .w_d(x01wd2), .w_ctl(x01wc2),
        .c_v(x01cv2), .c_ep(x01cep2), .wo_v(x01wv3), .wo_ep(x01wep3), .wo_off(x01woff3),
        .wo_m(x01wm3), .wo_d(x01wd3), .wo_ctl(x01wc3), .co_v(x01cv3), .co_ep(x01cep3),
        .r_v(n_lrv[6]), .r_t(n_lrt[6]), .r_ep(n_lrep[6]), .r_p(n_lrp[195:168]),
        .q_v(lq_v_d[6]), .q(lq_d[447:384]), .q_bad(lq_bad_d[6]));
    ot_qfd_xs_leaf
`ifdef OT_S8_SIM
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`else
`ifndef OT_S5_HARD
        #(.NCH(4), .READ_PIN_PIPE(NEW_READ), .FILL_PIPE(1))
`endif
`endif
        u_xl0_7 (.clk(ck), .rst_n(rst_n),
        .w_v(x01wv3), .w_ep(x01wep3), .w_off(x01woff3), .w_m(x01wm3), .w_d(x01wd3), .w_ctl(x01wc3),
        .c_v(x01cv3), .c_ep(x01cep3), .wo_v(x01wv4), .wo_ep(x01wep4), .wo_off(x01woff4),
        .wo_m(x01wm4), .wo_d(x01wd4), .wo_ctl(x01wc4), .co_v(x01cv4), .co_ep(x01cep4),
        .r_v(n_lrv[7]), .r_t(n_lrt[7]), .r_ep(n_lrep[7]), .r_p(n_lrp[223:196]),
        .q_v(lq_v_d[7]), .q(lq_d[511:448]), .q_bad(lq_bad_d[7]));

end endgenerate
    localparam integer OW = 516 * 2 + 8 + 12 + 128 + 2048 + 144 + 24 + 224 + 2;
    wire [OW-1:0] o_all = {o_n, o_s, o_lwv, o_lwep, o_lcv, o_lcep, o_lwoff, o_lwm, o_lwd, o_lwctl, o_lrv, o_lrt, o_lrep,
                           o_lrp, o_lrst, o_flt};
    wire [OW-1:0] n_all = {n_n, n_s, n_lwv, n_lwep, n_lcv, n_lcep, n_lwoff, n_lwm, n_lwd, n_lwctl, n_lrv, n_lrt, n_lrep,
                           n_lrp, n_lrst, n_flt};
    reg [OW-1:0] o_prev;

    // ---- the column's tile ids (copy of the strap function) ----
    function automatic integer tid(input integer c, input integer r);
        integer dr, bc, br, lbc, lbr, blk, z, p, i;
        begin
            dr = (r < NH) ? NH + r : NH - 1 - (r - NH);
            bc = 4; br = 4; lbc = 2; lbr = 2;
            blk = (c / bc) * (2 * NH / br) + dr / br;
            z = 0; p = 0;
            for (i = 0; i < 2; i = i + 1) begin
                if (i < lbc) begin z = z | (((c % bc) >> i) & 1) << p; p = p + 1; end
                if (i < lbr) begin z = z | (((dr % br) >> i) & 1) << p; p = p + 1; end
            end
            tid = bc * br * blk + z;
        end
    endfunction

integer first_or=-1,first_oq=-1,first_nr=-1,first_nq=-1,edge_count=0;
 always @(posedge ck)begin
  #1;edge_count=edge_count+1;
  if(o_lrv[0] && first_or<0)first_or=edge_count;
  if(n_lrv[0] && first_nr<0)first_nr=edge_count;
  if(lq_v[0] && first_oq<0)first_oq=edge_count;
  if(lq_v_d[0] && first_nq<0)first_nq=edge_count;
 end
    integer seed, cycles, cyc, compares, mism, pass_start;
    integer n_lw, n_en, n_lr, n_go, n_vd, n_pool, c_flt, n_ops, n_rst, n_bits_nz;
    // generator state
    integer ph_state, gap, beats, k_cur, sp_cur, tiles_cur, ep_cur, go_due, next_go_min, q, noise, quiet;
    integer w_rows [0:NR-1];
    reg [AW-1:0] xb_cur;
    reg rnd_cur;
    reg [5:0] ksel;
    integer ex_ep, pend_go;           // the epoch whose data is loaded and waiting for its go
    integer i, r, bad;
    function automatic integer urand(input integer n);
        urand = (n <= 1) ? 0 : ($urandom % n);
    endfunction
    function automatic integer pick_k(input integer pooled);
        integer x;
        begin
            x = urand(3);
            if (pooled != 0) pick_k = (urand(2) == 0) ? 24 : 32;
            else pick_k = (x == 0) ? 2 : (x == 1) ? 6 : 8;
        end
    endfunction
    reg [HW-1:0] w;
    task automatic make_desc(input integer ep);
        integer pooled, rr2, pr, emin, fm;
        begin
            pooled = (urand(4) == 0);
            k_cur = pick_k(pooled);
            sp_cur = pooled ? 7 : 7 + urand(5);
            xb_cur = pooled ? (AW'(urand(1 << 12)) << 6) : AW'(urand(1 << 16));
            if (urand(16) == 0) xb_cur = AW'($urandom);          // anywhere (beat wrap)
            rnd_cur = urand(2);
            tiles_cur = 1 + urand(3);
            fm = 4 * k_cur - 1;
            for (rr2 = 0; rr2 < NR; rr2 = rr2 + 1) begin
                q = tid(cid, rr2) & ((1 << (sp_cur - 2)) - 1);
                pr = 4 * k_cur * q;
                emin = xb_cur + pr;
                w_rows[rr2] = ((emin >> 6) + ((fm >= 64 && rr2 >= NH) ? 1 : 0)) & ((1 << 18) - 1);
            end
            w = {HW{1'b0}};
            w[1 + IBW + 0] = 1'b1;                                  // d_v
            w[1 + IBW + 1] = ep[0];
            w[1 + IBW + 2 +: AW] = xb_cur;
            w[1 + IBW + 26 +: XCW] = XCW'(k_cur);                   // x_cs = k
            w[1 + IBW + 38 +: XCW] = 12'd1;                         // x_ks = 1
            w[1 + IBW + 50 +: 4] = 4'(sp_cur);
            w[1 + IBW + 54 +: NW] = NW'(k_cur);
            w[1 + IBW + 72] = rnd_cur;
            if (urand(64) == 0) w[1 + IBW + 26 +: XCW] = XCW'(urand(40));   // occasional illegal descriptor
            if (urand(64) == 0) w[1 + IBW + 50 +: 4] = 4'(urand(16));
        end
    endtask
    task automatic make_beat(input integer ep);
        integer fb;
        begin
            w = {HW{1'b0}};
            for (i = 0; i < HW / 32 + 1; i = i + 1) w[32 * i +: 32] = $urandom;
            w[0] = 1'b0;
            w[1 + IBW + 0] = 1'b0;                                  // no descriptor
            w[1 + IBW + DESC] = 1'b1;                               // fv
            w[1 + IBW + DESC + 1] = ep[0];
            fb = w_rows[urand(NR)] + urand(3) - 1;
            if (urand(8) == 0) fb = $urandom;
            w[1 + IBW + DESC + 2 +: 18] = 18'(fb);
            if (urand(32) == 0) w[1 + IBW + DESC + 1] = ~ep[0];
        end
    endtask
    task automatic make_go(input integer ep);
        begin
            w = {HW{1'b0}};
            for (i = 0; i < IBW / 32 + 1; i = i + 1) w[1 + 32 * i +: 32] = $urandom;
            w[0] = 1'b1;
            w[1 + IBW - 2*NW +: NW] = NW'(tiles_cur);               // tiles
            w[1 + IBW - 3*NW +: NW] = NW'(k_cur);                   // k
            w[1 + 13*AW + 12] = 1'b0;                               // wsrc
            w[1 + 8*AW + 12 +: AW] = xb_cur;
            w[1 + 7*AW + 12 +: AW] = 24'd1;                         // x_ks
            w[1 + 6*AW + 12 +: AW] = 24'd0;                         // x_js
            w[1 + 5*AW + 12 +: AW] = AW'(k_cur);                    // x_cs
            w[1 + 5*AW + 5 +: 4] = 4'(sp_cur);
            w[1 + 4*AW + 4] = rnd_cur;
            w[1 + IBW +: FW] = {FW{1'b0}};
            for (i = 0; i < FW / 32; i = i + 1) w[1 + IBW + 99 + 32 * i +: 32] = (urand(2) == 0) ? $urandom : 0;
            w[1 + IBW + 0] = 1'b0; w[1 + IBW + DESC] = 1'b0;
            if (urand(48) == 0) w[1 + 8*AW + 12 +: AW] = AW'($urandom);   // occasional mismatching go
        end
    endtask

    always #5 ck = ~ck;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("cycles=%d", cycles)) cycles = 200000;
        if (!$value$plusargs("cid=%d", cid)) cid = 6'd0;
        void'($urandom(seed));
        compares = 0; mism = 0; n_lw = 0; n_en = 0; n_lr = 0; n_go = 0; n_vd = 0; n_pool = 0; c_flt = 0; n_ops = 0;
        n_rst = 0; n_bits_nz = 0;
        ph_state = 0; gap = 4; beats = 0; ep_cur = 0; go_due = 0; next_go_min = 0; noise = 0; quiet = 0; pend_go = 0;
        pass_start = 40;
        o_prev = {OW{1'b0}};
        rst_n = 1'b0;
        repeat (4) @(negedge ck);
        rst_n = 1'b1;
        for (cyc = 0; cyc < cycles; cyc = cyc + 1) begin
            @(negedge ck);
            // ---- compare: new(now) against old(previous edge) ----
            if (cyc >= pass_start) begin
                compares = compares + 1;
                if (n_all !== o_prev) begin
                    mism = mism + 1;
                    if (mism <= 4) begin
                        $display("S5_XH3_EQ MISMATCH cyc %0d", cyc);
                        for (i = 0; i < OW; i = i + 1)
                            if (n_all[i] !== o_prev[i]) begin bad = i; end
                        $display("  highest differing output bit %0d (o_all index; n_d at top)", bad);
                        if (n_n !== o_prev[OW-1 -: 516]) $display("  n_d differs");
                        if (n_s !== o_prev[OW-517 -: 516]) $display("  s_d differs");
                        if (n_lwd !== o_prev[OW-1032-8-12-128-1 -: 2048]) $display("  lw_d differs");
                        if (n_lwctl !== o_prev[OW-1032-8-12-128-2048-1 -: 144]) $display("  lw_ctl differs");
                        if (n_lrp !== o_prev[2 +: 224]) $display("  lr_p differs");
                        if (n_flt !== o_prev[0]) $display("  fault differs");
                    end
                end
            end
            o_prev = o_all;
            // coverage
            if (|o_lwv) n_lw = n_lw + 1;
            for (i = 0; i < 16; i = i + 1) if (o_lwctl[9*i + 8]) n_en = n_en + 1;
            if (|o_lrv) n_lr = n_lr + 1;
            if (o_n[0]) n_go = n_go + 1;
            if (o_n[515]) n_vd = n_vd + 1;
            if (o_flt) c_flt = c_flt + 1;
            if (|o_n[380 +: 128]) n_bits_nz = n_bits_nz + 1;
            // ---- next inputs ----
            fault_i_d = fault_i;
            fault_i = (urand(30000) == 0) ? 1'b1 : (urand(50) == 0 ? 1'b0 : fault_i);
            w = {HW{1'b0}};
            if (quiet > 0) begin
                // quiesced reset window
                quiet = quiet - 1;
                if (quiet == 30) rst_n = 1'b0;
                if (quiet == 26) begin rst_n = 1'b1; n_rst = n_rst + 1; end
                if (quiet == 0) begin ph_state = 0; gap = 2; pend_go = 0; next_go_min = cyc; ep_cur = 0; end
                if (quiet == 31) pass_start = cyc + 40;          // stop comparing from the reset edge on
            end else if (noise > 0) begin
                noise = noise - 1;
                if (urand(3) == 0) for (i = 0; i < HW / 32 + 1; i = i + 1) w[32 * i +: 32] = $urandom;
                if (urand(2) == 0) w[0] = 1'b0;
                if (noise == 0) begin quiet = 140; end
            end else begin
                // legal stream: desc(e) .. beats(e) .. go(e) at >= next_go_min; next desc(e') right after the go
                case (ph_state)
                    0: begin                                     // gap, then descriptor
                        if (gap > 0) gap = gap - 1;
                        else begin make_desc(ep_cur); beats = 2 + urand(12); gap = 2 + urand(3); ph_state = 1; end
                    end
                    1: begin                                     // data beats (>= 3 edges behind the descriptor)
                        if (gap > 0) begin gap = gap - 1; if (urand(3) == 0) make_beat(ep_cur ^ 1); end
                        else if (beats > 0) begin make_beat(ep_cur); beats = beats - 1; end
                        else begin ph_state = 2; gap = urand(4); end
                    end
                    2: begin                                     // go when the previous op ends (back-to-back allowed)
                        if (gap > 0) gap = gap - 1;
                        else if (cyc >= next_go_min) begin
                            make_go(ep_cur);
                            n_ops = n_ops + 1;
                            next_go_min = cyc + 8 * k_cur * tiles_cur - 1 + ((urand(3) == 0) ? 0 : urand(4));
                            // the next descriptor claims the other epoch: it must reach the head after this go's
                            // g_q (5 edges), the previous op's last edge on that epoch
                            ep_cur = ep_cur ^ 1; ph_state = 0; gap = 6 + urand(3);
                            if (urand(150) == 0) noise = 50 + urand(200);
                            else if (urand(60) == 0) quiet = 140;
                        end
                    end
                endcase
            end
            a_d = w;
        end
        $display("S5_XH3_COVER ops %0d lw_v %0d en %0d lr_v %0d go %0d xvalid %0d xnz %0d fault %0d resets %0d",
                 n_ops, n_lw, n_en, n_lr, n_go, n_vd, n_bits_nz, c_flt, n_rst);
        if (mism == 0 && compares > 0 && n_en > 0 && n_vd > 0) begin
            if(first_or<0 || first_nr<0 || first_oq<0 || first_nq<0)$fatal(1,"S8_COLUMN no real read coverage");
            $display("S8_COLUMN_AGES first_req old=%0d new=%0d first_q old=%0d new=%0d; local leaf read=%0d/%0d",first_or,first_nr,first_oq,first_nq,first_oq-first_or,first_nq-first_nr);
            $display("S5_XH3_EQ PASS %0d compares seed %0d cid %0d", compares, seed, cid);
        end else begin
            $display("S5_XH3_EQ FAIL %0d mismatches of %0d compares seed %0d cid %0d", mism, compares, seed, cid);
            $fatal(1, "S5_XH3_EQ FAIL");
        end
        $finish;
    end
endmodule
