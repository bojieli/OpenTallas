`timescale 1ns/1ps
// Logical25-root column; flatten to actual head/store/GW siblings. No columnbbox/view inheritance.
module ot_qfd_xhead_extcap_m #(parameter integer NW = 18, parameter integer AW = 24, parameter integer XCW = 12,
    parameter integer MUT = 0) (   // bench-only head mutant (ot_qfd_xhead MUT); the die instantiates the default
    input  wire          ck,
    input  wire          rst_n,
    input  wire [255:0]  tids,
    input  wire          fault_i,
    output wire          fault,
    input  wire [1+(3*NW+13*AW+13)+(2+AW+2*XCW+4+NW+1)+(2+(AW-6)+6+64+1024)-1:0] h_in,
    output wire [1+(3*NW+13*AW+13)+(2+AW+2*XCW+4+NW+1)+(2+(AW-6)+6+64+1024)-1:0] h_out,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] n_d,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] s_d,
    output wire          cn_wv, cn_wep, cn_cv, cn_cep,
    output wire [5:0]    cn_woff,
    output wire [63:0]   cn_wm,
    output wire [1023:0] cn_wd,
    output wire [71:0]   cn_wctl,
    output wire          cs_wv, cs_wep, cs_cv, cs_cep,
    output wire [5:0]    cs_woff,
    output wire [63:0]   cs_wm,
    output wire [1023:0] cs_wd,
    output wire [71:0]   cs_wctl,
    output wire [3:0]    rn_v, rn_t, rn_ep,
    output wire [111:0]  rn_p,
    input  wire [255:0]  qn,
    input  wire [3:0]    qn_v, qn_bad,
    output wire [3:0]    rs_v, rs_t, rs_ep,
    output wire [111:0]  rs_p,
    input  wire [255:0]  qs,
    input  wire [3:0]    qs_v, qs_bad
);
    wire [1:0] lw_v, lw_ep, lc_v, lc_ep;
    wire [11:0] lw_off;
    wire [127:0] lw_m;
    wire [2047:0] lw_d;
    wire [143:0] lw_ctl;
    ot_qfd_xhead #(.AW(AW), .NW(NW), .XCW(XCW), .NH(8),.NATIVE_AFFINE(1),.LEAF_BANK_PIPE(1),.FILL_LEAD(5),.DX(14),.MUT(MUT)) u_head (.ck(ck), .rst_n(rst_n), .tids(tids), .fault_i(fault_i),
        .a_d(h_in), .a_r(), .b_d(h_out), .b_r(1'b1), .n_d(n_d), .n_r(1'b1), .s_d(s_d), .s_r(1'b1),
        .lw_v(lw_v), .lw_ep(lw_ep), .lw_off(lw_off), .lw_m(lw_m), .lw_d(lw_d), .lw_ctl(lw_ctl),
        .lc_v(lc_v), .lc_ep(lc_ep),
        .lr_v({rs_v, rn_v}), .lr_t({rs_t, rn_t}), .lr_ep({rs_ep, rn_ep}), .lr_p({rs_p, rn_p}),
        .lq({qs, qn}), .lq_v({qs_v, qn_v}), .lq_bad({qs_bad, qn_bad}), .fault(fault));
    assign cn_wv = lw_v[0]; assign cn_wep = lw_ep[0]; assign cn_cv = lc_v[0]; assign cn_cep = lc_ep[0];
    assign cn_woff = lw_off[5:0]; assign cn_wm = lw_m[63:0]; assign cn_wd = lw_d[1023:0]; assign cn_wctl = lw_ctl[71:0];
    assign cs_wv = lw_v[1]; assign cs_wep = lw_ep[1]; assign cs_cv = lc_v[1]; assign cs_cep = lc_ep[1];
    assign cs_woff = lw_off[11:6]; assign cs_wm = lw_m[127:64]; assign cs_wd = lw_d[2047:1024]; assign cs_wctl = lw_ctl[143:72];
endmodule

module qfd_xhead_extcap_e (   // fixed banked/FILL5/DX14 head successor; physical qualification required
    input  wire          ck,
    input  wire          rst_n,
    input  wire [255:0]  tids,
    input  wire          fault_i,
    output wire          fault,
    input  wire [1+379+73+1114-1:0] w_d,
    output wire [1+379+73+1114-1:0] e_d,
    output wire [1+379+128+8-1:0] n_d,
    output wire [1+379+128+8-1:0] s_d,
    output wire          cn_wv, cn_wep, cn_cv, cn_cep,
    output wire [5:0]    cn_woff,
    output wire [63:0]   cn_wm,
    output wire [1023:0] cn_wd,
    output wire [71:0]   cn_wctl,
    output wire          cs_wv, cs_wep, cs_cv, cs_cep,
    output wire [5:0]    cs_woff,
    output wire [63:0]   cs_wm,
    output wire [1023:0] cs_wd,
    output wire [71:0]   cs_wctl,
    output wire [3:0]    rn_v, rn_t, rn_ep,
    output wire [111:0]  rn_p,
    input  wire [255:0]  qn,
    input  wire [3:0]    qn_v, qn_bad,
    output wire [3:0]    rs_v, rs_t, rs_ep,
    output wire [111:0]  rs_p,
    input  wire [255:0]  qs,
    input  wire [3:0]    qs_v, qs_bad
);
    ot_qfd_xhead_extcap_m #(.MUT(0)) u_h (.ck(ck), .rst_n(rst_n), .tids(tids), .fault_i(fault_i), .fault(fault),
        .h_in(w_d), .h_out(e_d), .n_d(n_d), .s_d(s_d),
        .cn_wv(cn_wv), .cn_wep(cn_wep), .cn_cv(cn_cv), .cn_cep(cn_cep), .cn_woff(cn_woff), .cn_wm(cn_wm), .cn_wd(cn_wd),
        .cn_wctl(cn_wctl), .cs_wv(cs_wv), .cs_wep(cs_wep), .cs_cv(cs_cv), .cs_cep(cs_cep), .cs_woff(cs_woff),
        .cs_wm(cs_wm), .cs_wd(cs_wd), .cs_wctl(cs_wctl), .rn_v(rn_v), .rn_t(rn_t), .rn_ep(rn_ep), .rn_p(rn_p),
        .qn(qn), .qn_v(qn_v), .qn_bad(qn_bad), .rs_v(rs_v), .rs_t(rs_t), .rs_ep(rs_ep), .rs_p(rs_p), .qs(qs),
        .qs_v(qs_v), .qs_bad(qs_bad));
endmodule

module qfd_xhead_extcap_w (   // fixed banked/FILL5/DX14 head successor; physical qualification required
    input  wire          ck,
    input  wire          rst_n,
    input  wire [255:0]  tids,
    input  wire          fault_i,
    output wire          fault,
    input  wire [1+379+73+1114-1:0] e_d,
    output wire [1+379+73+1114-1:0] w_d,
    output wire [1+379+128+8-1:0] n_d,
    output wire [1+379+128+8-1:0] s_d,
    output wire          cn_wv, cn_wep, cn_cv, cn_cep,
    output wire [5:0]    cn_woff,
    output wire [63:0]   cn_wm,
    output wire [1023:0] cn_wd,
    output wire [71:0]   cn_wctl,
    output wire          cs_wv, cs_wep, cs_cv, cs_cep,
    output wire [5:0]    cs_woff,
    output wire [63:0]   cs_wm,
    output wire [1023:0] cs_wd,
    output wire [71:0]   cs_wctl,
    output wire [3:0]    rn_v, rn_t, rn_ep,
    output wire [111:0]  rn_p,
    input  wire [255:0]  qn,
    input  wire [3:0]    qn_v, qn_bad,
    output wire [3:0]    rs_v, rs_t, rs_ep,
    output wire [111:0]  rs_p,
    input  wire [255:0]  qs,
    input  wire [3:0]    qs_v, qs_bad
);
    ot_qfd_xhead_extcap_m #(.MUT(0)) u_h (.ck(ck), .rst_n(rst_n), .tids(tids), .fault_i(fault_i), .fault(fault),
        .h_in(e_d), .h_out(w_d), .n_d(n_d), .s_d(s_d),
        .cn_wv(cn_wv), .cn_wep(cn_wep), .cn_cv(cn_cv), .cn_cep(cn_cep), .cn_woff(cn_woff), .cn_wm(cn_wm), .cn_wd(cn_wd),
        .cn_wctl(cn_wctl), .cs_wv(cs_wv), .cs_wep(cs_wep), .cs_cv(cs_cv), .cs_cep(cs_cep), .cs_woff(cs_woff),
        .cs_wm(cs_wm), .cs_wd(cs_wd), .cs_wctl(cs_wctl), .rn_v(rn_v), .rn_t(rn_t), .rn_ep(rn_ep), .rn_p(rn_p),
        .qn(qn), .qn_v(qn_v), .qn_bad(qn_bad), .rs_v(rs_v), .rs_t(rs_t), .rs_ep(rs_ep), .rs_p(rs_p), .qs(qs),
        .qs_v(qs_v), .qs_bad(qs_bad));
endmodule


module ot_qfd_xcol_extcap #(parameter integer EAST = 1) (
    input  wire          ck0, ck1, ck2, ck3, ck4, ck5, ck6, ck7, ck8, ck9, ck10, ck11, ck12, ck13, ck14, ck15, ck16, ck17, ck18, ck19, ck20, ck21, ck22, ck23, ck24,
    input  wire          rst_n,
    input  wire [255:0]  tids,
    input  wire          fault_i,
    output wire          fault,
    input  wire [1+379+73+1114-1:0] h_in,
    output wire [1+379+73+1114-1:0] h_out,
    output wire [1+379+128+8-1:0] n_d,
    output wire [1+379+128+8-1:0] s_d
);
    wire [24:0] ck = {ck24, ck23, ck22, ck21, ck20, ck19, ck18, ck17, ck16, ck15, ck14, ck13, ck12, ck11, ck10, ck9, ck8, ck7, ck6, ck5, ck4, ck3, ck2, ck1, ck0};
    wire [7:0] capture_fault;
    wire       cw_v [0:1][0:4], cw_ep [0:1][0:4], cc_v [0:1][0:4], cc_ep [0:1][0:4];
    wire [5:0] cw_off [0:1][0:4];
    wire [63:0] cw_m [0:1][0:4];
    wire [1023:0] cw_d [0:1][0:4];
    wire [71:0] cw_ctl [0:1][0:4];
    wire [3:0] r_v [0:1], r_t [0:1], r_ep [0:1], q_v [0:1], q_bad [0:1];
    wire [111:0] r_p [0:1];
    wire [255:0] q [0:1];
    // Logical grouping only: physical siblings are head,8extcap cores,16captureGWs.
    // capture_fault OR is actual combinational parentglue requiring placement/timing.
    generate if (EAST) begin : g_he
qfd_xhead_extcap_e u_h (
        .ck(ck0), .rst_n(rst_n), .tids(tids), .fault_i(fault_i|(|capture_fault)), .fault(fault),
        .w_d(h_in), .e_d(h_out), .n_d(n_d), .s_d(s_d),
        .cn_wv(cw_v[0][0]), .cn_wep(cw_ep[0][0]), .cn_cv(cc_v[0][0]), .cn_cep(cc_ep[0][0]), .cn_woff(cw_off[0][0]),
        .cn_wm(cw_m[0][0]), .cn_wd(cw_d[0][0]), .cn_wctl(cw_ctl[0][0]),
        .cs_wv(cw_v[1][0]), .cs_wep(cw_ep[1][0]), .cs_cv(cc_v[1][0]), .cs_cep(cc_ep[1][0]), .cs_woff(cw_off[1][0]),
        .cs_wm(cw_m[1][0]), .cs_wd(cw_d[1][0]), .cs_wctl(cw_ctl[1][0]),
        .rn_v(r_v[0]), .rn_t(r_t[0]), .rn_ep(r_ep[0]), .rn_p(r_p[0]), .qn(q[0]), .qn_v(q_v[0]), .qn_bad(q_bad[0]),
        .rs_v(r_v[1]), .rs_t(r_t[1]), .rs_ep(r_ep[1]), .rs_p(r_p[1]), .qs(q[1]), .qs_v(q_v[1]), .qs_bad(q_bad[1]));
    end else begin : g_hw
qfd_xhead_extcap_w u_h (
        .ck(ck0), .rst_n(rst_n), .tids(tids), .fault_i(fault_i|(|capture_fault)), .fault(fault),
        .e_d(h_in), .w_d(h_out), .n_d(n_d), .s_d(s_d),
        .cn_wv(cw_v[0][0]), .cn_wep(cw_ep[0][0]), .cn_cv(cc_v[0][0]), .cn_cep(cc_ep[0][0]), .cn_woff(cw_off[0][0]),
        .cn_wm(cw_m[0][0]), .cn_wd(cw_d[0][0]), .cn_wctl(cw_ctl[0][0]),
        .cs_wv(cw_v[1][0]), .cs_wep(cw_ep[1][0]), .cs_cv(cc_v[1][0]), .cs_cep(cc_ep[1][0]), .cs_woff(cw_off[1][0]),
        .cs_wm(cw_m[1][0]), .cs_wd(cw_d[1][0]), .cs_wctl(cw_ctl[1][0]),
        .rn_v(r_v[0]), .rn_t(r_t[0]), .rn_ep(r_ep[0]), .rn_p(r_p[0]), .qn(q[0]), .qn_v(q_v[0]), .qn_bad(q_bad[0]),
        .rs_v(r_v[1]), .rs_t(r_t[1]), .rs_ep(r_ep[1]), .rs_p(r_p[1]), .qs(q[1]), .qs_v(q_v[1]), .qs_bad(q_bad[1]));
    end endgenerate
    genvar h, j;
    generate for (h = 0; h < 2; h = h + 1) begin : g_ch
        for (j = 0; j < 4; j = j + 1) begin : g_leaf
qfd_xs_leaf_capture_parent u_leaf (
                .clk(ck[1 + 4*h + j]), .clk_wd0(ck[9+2*(4*h+j)]), .clk_wd1(ck[10+2*(4*h+j)]), .rst_n(rst_n),
                .w_v(cw_v[h][j]), .w_ep(cw_ep[h][j]), .w_off(cw_off[h][j]), .w_m(cw_m[h][j]), .w_d(cw_d[h][j]),
                .w_ctl(cw_ctl[h][j]), .c_v(cc_v[h][j]), .c_ep(cc_ep[h][j]),
                .wo_v(cw_v[h][j+1]), .wo_ep(cw_ep[h][j+1]), .wo_off(cw_off[h][j+1]), .wo_m(cw_m[h][j+1]),
                .wo_d(cw_d[h][j+1]), .wo_ctl(cw_ctl[h][j+1]), .co_v(cc_v[h][j+1]), .co_ep(cc_ep[h][j+1]),
                .r_v(r_v[h][j]), .r_t(r_t[h][j]), .r_ep(r_ep[h][j]), .r_p(r_p[h][28*j +: 28]),
                .q_v(q_v[h][j]), .q(q[h][64*j +: 64]), .q_bad(q_bad[h][j]), .fault(capture_fault[4*h+j]));
        end
    end endgenerate
endmodule

module qfd_xcol_extcap_e  (   // logical grouping, flattened into actual hard children
    input  wire          ck0, ck1, ck2, ck3, ck4, ck5, ck6, ck7, ck8, ck9, ck10, ck11, ck12, ck13, ck14, ck15, ck16, ck17, ck18, ck19, ck20, ck21, ck22, ck23, ck24,
    input  wire          rst_n,
    input  wire [255:0]  tids,
    input  wire          fault_i,
    output wire          fault,
    input  wire [1+379+73+1114-1:0] w_d,
    output wire [1+379+73+1114-1:0] e_d,
    output wire [1+379+128+8-1:0] n_d,
    output wire [1+379+128+8-1:0] s_d,
    output wire          tie_hi,
    output wire          tie_lo
);
    // die strap ties (contract v1.2): the die wires tids[255:0] and a terminus fault_i to these two outputs
    (* keep *) wire tie_hi_w = 1'b1;
    (* keep *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_xcol_extcap #(.EAST(1)) u_c (.ck0(ck0), .ck1(ck1), .ck2(ck2), .ck3(ck3), .ck4(ck4), .ck5(ck5), .ck6(ck6), .ck7(ck7), .ck8(ck8), .ck9(ck9), .ck10(ck10), .ck11(ck11), .ck12(ck12), .ck13(ck13), .ck14(ck14), .ck15(ck15), .ck16(ck16), .ck17(ck17), .ck18(ck18), .ck19(ck19), .ck20(ck20), .ck21(ck21), .ck22(ck22), .ck23(ck23), .ck24(ck24),
        .rst_n(rst_n), .tids(tids), .fault_i(fault_i), .fault(fault), .h_in(w_d), .h_out(e_d),
        .n_d(n_d), .s_d(s_d));
endmodule

module qfd_xcol_extcap_w  (   // logical grouping, flattened into actual hard children
    input  wire          ck0, ck1, ck2, ck3, ck4, ck5, ck6, ck7, ck8, ck9, ck10, ck11, ck12, ck13, ck14, ck15, ck16, ck17, ck18, ck19, ck20, ck21, ck22, ck23, ck24,
    input  wire          rst_n,
    input  wire [255:0]  tids,
    input  wire          fault_i,
    output wire          fault,
    input  wire [1+379+73+1114-1:0] e_d,
    output wire [1+379+73+1114-1:0] w_d,
    output wire [1+379+128+8-1:0] n_d,
    output wire [1+379+128+8-1:0] s_d,
    output wire          tie_hi,
    output wire          tie_lo
);
    // die strap ties (contract v1.2): the die wires tids[255:0] and a terminus fault_i to these two outputs
    (* keep *) wire tie_hi_w = 1'b1;
    (* keep *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_xcol_extcap #(.EAST(0)) u_c (.ck0(ck0), .ck1(ck1), .ck2(ck2), .ck3(ck3), .ck4(ck4), .ck5(ck5), .ck6(ck6), .ck7(ck7), .ck8(ck8), .ck9(ck9), .ck10(ck10), .ck11(ck11), .ck12(ck12), .ck13(ck13), .ck14(ck14), .ck15(ck15), .ck16(ck16), .ck17(ck17), .ck18(ck18), .ck19(ck19), .ck20(ck20), .ck21(ck21), .ck22(ck22), .ck23(ck23), .ck24(ck24),
        .rst_n(rst_n), .tids(tids), .fault_i(fault_i), .fault(fault), .h_in(e_d), .h_out(w_d),
        .n_d(n_d), .s_d(s_d));
endmodule
