`timescale 1ns/1ps
// Qwen TP8 compute die, distributed x slices (el1014-qwen-dvm-build.log): the slot-shaped die masters, each hardened
// ONCE under its die name.  STATIC SCHEDULE (owner 2026-10-14 18:59): the die masters carry NO ready / back-pressure
// port: a bundle is its data word x_d only; the compiler reserves every slot, faults travel on the fault chain.  The
// core ot_qfd_* modules keep their (constant-1) readiness inputs for the array benches; the wrappers tie them inside.
// Strap masters (xcst sidx, xcol tids / fault_i terminus) expose tie_hi / tie_lo outputs (contract v1.2) so the die
// never writes a literal.
//
// r3 (16:15 PT 10-14), the compute die lead's four requests (11:51) + the column slot fit:
//   * tile ids: strap tids[255:0] = 16 x 16-b reference ids (N stations 0..7 outward, then S 8..15 outward);
//   * head roots: the tap takes gi = {ib, go} and drives two registered head words hw_d / he_d = {fill, ib, go};
//   * clocks: one scalar clock port per hardened child (qfd_xcol_*: ck0 = head, ck1..ck8 = leaves N0..N3, S0..S3);
//   * fault: fault_i (outer neighbour's fault) chained inward along the head row; the tap ORs both roots' chains;
//   * the station has no tap ready (the tile never back-pressures: no tied port);
//   * slot: the column is a die-placed N-S STACK of nine tiles in the 64.8-um corridor slot (a hardened cluster cannot
//     hold 20-um child channels / edges in 64.8 um): qfd_xs_leaf x 4 (N chain, R0) / qfd_xhead_e|w / qfd_xs_leaf x 4
//     (S chain, MX); the write chains cross abutted N / S faces (pin to pin), the read buses (31 b out, 66 b in per
//     leaf) and the corridor words leave the head's W / E faces.  qfd_xcol_e/w below is the same composition as ONE
//     RTL module for a die that binds the column as one instance.
//
//   qfd_xcst_s   corridor station with x hold, south half   in a (N)  out b (S), tap (W)          384
//   qfd_xcst_n   corridor station with x hold, north half   in b (S)  out a (N), tap (W)          384
//   qfd_xhead_e  column head, head row in w (W) out e (E); chains cn_* (N face) / cs_* (S face)   24
//   qfd_xhead_w  the same, head row in e (E) out w (W)                                              24
//   qfd_xs_leaf  = ot_qfd_xs_leaf (NCH 4)                                                          384
//   qfd_xs_tap   x tap at the VM N face: sw / aw / xpf / gi in, hw_d / he_d out, hw_f / he_f fault chains in    1
// Straps: sidx (station index in its corridor half), tids (the column's 16 reference tile ids) are constant ties of
// strap ports at the die (as tile_id), not logic.

module qfd_xcst_s #(parameter integer NW = 18, parameter integer AW = 24, parameter integer XOFF = 3) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [2:0]    sidx,
    input  wire [1+(3*NW+13*AW+13)+128+8-1:0] a_d,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] b_d,
    output wire [1+(3*NW+13*AW+13)+128-1:0] tap_d,
    output wire          tie_hi,
    output wire          tie_lo
);
    // die strap ties (contract v1.2): the die wires every strap / terminus bit of this instance to these two outputs
    (* keep *) wire tie_hi_w = 1'b1;
    (* keep *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_xcst #(.AW(AW), .NW(NW), .XOFF(XOFF)) u_st (.ck(ck), .rst_n(rst_n), .sidx(sidx), .a_d(a_d), .a_r(),
        .b_d(b_d), .b_r(1'b1), .tap_d(tap_d));
endmodule

module qfd_xcst_n #(parameter integer NW = 18, parameter integer AW = 24, parameter integer XOFF = 3) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [2:0]    sidx,
    input  wire [1+(3*NW+13*AW+13)+128+8-1:0] b_d,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] a_d,
    output wire [1+(3*NW+13*AW+13)+128-1:0] tap_d,
    output wire          tie_hi,
    output wire          tie_lo
);
    // die strap ties (contract v1.2): the die wires every strap / terminus bit of this instance to these two outputs
    (* keep *) wire tie_hi_w = 1'b1;
    (* keep *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_xcst #(.AW(AW), .NW(NW), .XOFF(XOFF)) u_st (.ck(ck), .rst_n(rst_n), .sidx(sidx), .a_d(b_d), .a_r(),
        .b_d(a_d), .b_r(1'b1), .tap_d(tap_d));
endmodule

// x tap die master.  Bundles (LSB first): sw = {sw_d 2048, sw_m 64, sw_a 24, sw_v} (2,137 b), aw = {aw_d 512, aw_m 16,
// aw_a 24, aw_v} (553 b), xpf = {round, k NW, split 4, xks 12, xcs 12, xbase 24, v} (72 b at NW 18), gi = {ib, go}.
module qfd_xs_tap #(parameter integer NW = 18, parameter integer AW = 24, parameter integer XCW = 12,
    parameter integer MUT = 0) (   // bench-only mutant (1: no rounding); the die instantiates the default
    input  wire          ck,
    input  wire          rst_n,
    input  wire [1+AW+64+2048-1:0] sw,
    input  wire [1+AW+16+512-1:0]  aw,
    input  wire [1+AW+2*XCW+4+NW+1-1:0] xpf,
    input  wire [3*NW+13*AW+13:0]  gi,
    output wire [1+(3*NW+13*AW+13)+(2+AW+2*XCW+4+NW+1)+(2+(AW-6)+6+64+1024)-1:0] hw_d,
    output wire [1+(3*NW+13*AW+13)+(2+AW+2*XCW+4+NW+1)+(2+(AW-6)+6+64+1024)-1:0] he_d,
    input  wire          hw_f,
    input  wire          he_f,
    output wire          fault
);
    // the head row is a lockstep broadcast on compiler-reserved slots: no ready port (static schedule); a root's
    // faults arrive on hw_f / he_f
    wire tf;
    // One physical reset-capture edge at the tap boundary. The compiler boot
    // contract must release this local reset before any scheduled input.
    (* keep *) reg local_rst_n;
    always @(posedge ck) local_rst_n <= rst_n;
    ot_qfd_xs_tap #(.AW(AW), .NW(NW), .XCW(XCW),.STATIC_SCHEDULE(1),.NATIVE_AFFINE(1),.MUT(MUT)) u_tap (.clk(ck), .rst_n(local_rst_n),
        .xpf_v(xpf[0]), .xpf_xbase(xpf[1 +: AW]), .xpf_xcs(xpf[1+AW +: XCW]), .xpf_xks(xpf[1+AW+XCW +: XCW]),
        .xpf_split(xpf[1+AW+2*XCW +: 4]), .xpf_k(xpf[1+AW+2*XCW+4 +: NW]), .xpf_round(xpf[1+AW+2*XCW+4+NW]),
        .sw_v(sw[0]), .sw_a(sw[1 +: AW]), .sw_m(sw[1+AW +: 64]), .sw_d(sw[1+AW+64 +: 2048]),
        .aw_v(aw[0]), .aw_a(aw[1 +: AW]), .aw_m(aw[1+AW +: 16]), .aw_d(aw[1+AW+16 +: 512]),
        .gi(gi), .hw(hw_d), .he(he_d), .fw_i(hw_f), .fe_i(he_f), .fault(tf));
    assign fault = tf;
endmodule

// column head die masters (stack plan).  Chains: c{n,s}_* = the write word to leaf N0 / S0 (N / S face), reads
// r{n,s}_* / q{n,s}* = the four read buses of that chain's leaves (W / E faces with the corridors and the head row).
module ot_qfd_xhead_m #(parameter integer NW = 18, parameter integer AW = 24, parameter integer XCW = 12,
    parameter integer MUT = 0, parameter integer REQ_PIPE = 0) (   // REQ_PIPE: read-request relay stages (ot_qfd_xhead)   // bench-only head mutant (ot_qfd_xhead MUT); the die instantiates the default
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
    ot_qfd_xhead #(.AW(AW), .NW(NW), .XCW(XCW), .NH(8),.NATIVE_AFFINE(1),.REQ_PIPE(REQ_PIPE),.MUT(MUT)) u_head (.ck(ck), .rst_n(rst_n), .tids(tids), .fault_i(fault_i),
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

module qfd_xhead_e #(parameter integer MUT = 0, parameter integer REQ_PIPE = 0) (   // bench-only head mutant; the die / cluster use the default
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
    ot_qfd_xhead_m #(.MUT(MUT), .REQ_PIPE(REQ_PIPE)) u_h (.ck(ck), .rst_n(rst_n), .tids(tids), .fault_i(fault_i), .fault(fault),
        .h_in(w_d), .h_out(e_d), .n_d(n_d), .s_d(s_d),
        .cn_wv(cn_wv), .cn_wep(cn_wep), .cn_cv(cn_cv), .cn_cep(cn_cep), .cn_woff(cn_woff), .cn_wm(cn_wm), .cn_wd(cn_wd),
        .cn_wctl(cn_wctl), .cs_wv(cs_wv), .cs_wep(cs_wep), .cs_cv(cs_cv), .cs_cep(cs_cep), .cs_woff(cs_woff),
        .cs_wm(cs_wm), .cs_wd(cs_wd), .cs_wctl(cs_wctl), .rn_v(rn_v), .rn_t(rn_t), .rn_ep(rn_ep), .rn_p(rn_p),
        .qn(qn), .qn_v(qn_v), .qn_bad(qn_bad), .rs_v(rs_v), .rs_t(rs_t), .rs_ep(rs_ep), .rs_p(rs_p), .qs(qs),
        .qs_v(qs_v), .qs_bad(qs_bad));
endmodule

module qfd_xhead_w #(parameter integer MUT = 0, parameter integer REQ_PIPE = 0) (   // bench-only head mutant; the die / cluster use the default
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
    ot_qfd_xhead_m #(.MUT(MUT), .REQ_PIPE(REQ_PIPE)) u_h (.ck(ck), .rst_n(rst_n), .tids(tids), .fault_i(fault_i), .fault(fault),
        .h_in(e_d), .h_out(w_d), .n_d(n_d), .s_d(s_d),
        .cn_wv(cn_wv), .cn_wep(cn_wep), .cn_cv(cn_cv), .cn_cep(cn_cep), .cn_woff(cn_woff), .cn_wm(cn_wm), .cn_wd(cn_wd),
        .cn_wctl(cn_wctl), .cs_wv(cs_wv), .cs_wep(cs_wep), .cs_cv(cs_cv), .cs_cep(cs_cep), .cs_woff(cs_woff),
        .cs_wm(cs_wm), .cs_wd(cs_wd), .cs_wctl(cs_wctl), .rn_v(rn_v), .rn_t(rn_t), .rn_ep(rn_ep), .rn_p(rn_p),
        .qn(qn), .qn_v(qn_v), .qn_bad(qn_bad), .rs_v(rs_v), .rs_t(rs_t), .rs_ep(rs_ep), .rs_p(rs_p), .qs(qs),
        .qs_v(qs_v), .qs_bad(qs_bad));
endmodule

// one column as ONE RTL module: xhead + 8 x qfd_xs_leaf (two write chains), one clock port per hardened child
module ot_qfd_xcol #(parameter integer HEAD_MUT = 0, parameter integer EAST = 1, parameter integer REQ_PIPE = 0) (
    input  wire          ck0, ck1, ck2, ck3, ck4, ck5, ck6, ck7, ck8,
    input  wire          rst_n,
    input  wire [255:0]  tids,
    input  wire          fault_i,
    output wire          fault,
    input  wire [1+379+73+1114-1:0] h_in,
    output wire [1+379+73+1114-1:0] h_out,
    output wire [1+379+128+8-1:0] n_d,
    output wire [1+379+128+8-1:0] s_d
);
    wire [8:0] ck = {ck8, ck7, ck6, ck5, ck4, ck3, ck2, ck1, ck0};
    wire       cw_v [0:1][0:4], cw_ep [0:1][0:4], cc_v [0:1][0:4], cc_ep [0:1][0:4];
    wire [5:0] cw_off [0:1][0:4];
    wire [63:0] cw_m [0:1][0:4];
    wire [1023:0] cw_d [0:1][0:4];
    wire [71:0] cw_ctl [0:1][0:4];
    wire [3:0] r_v [0:1], r_t [0:1], r_ep [0:1], q_v [0:1], q_bad [0:1];
    wire [111:0] r_p [0:1];
    wire [255:0] q [0:1];
    // the column's hard children by their die names: head qfd_xhead_e (EAST) / qfd_xhead_w, leaves qfd_xs_leaf
    generate if (EAST) begin : g_he
`ifndef OT_QFD_XS_HARD
    qfd_xhead_e #(.MUT(HEAD_MUT), .REQ_PIPE(REQ_PIPE)) u_h (
`else
    qfd_xhead_e u_h (
`endif
        .ck(ck0), .rst_n(rst_n), .tids(tids), .fault_i(fault_i), .fault(fault),
        .w_d(h_in), .e_d(h_out), .n_d(n_d), .s_d(s_d),
        .cn_wv(cw_v[0][0]), .cn_wep(cw_ep[0][0]), .cn_cv(cc_v[0][0]), .cn_cep(cc_ep[0][0]), .cn_woff(cw_off[0][0]),
        .cn_wm(cw_m[0][0]), .cn_wd(cw_d[0][0]), .cn_wctl(cw_ctl[0][0]),
        .cs_wv(cw_v[1][0]), .cs_wep(cw_ep[1][0]), .cs_cv(cc_v[1][0]), .cs_cep(cc_ep[1][0]), .cs_woff(cw_off[1][0]),
        .cs_wm(cw_m[1][0]), .cs_wd(cw_d[1][0]), .cs_wctl(cw_ctl[1][0]),
        .rn_v(r_v[0]), .rn_t(r_t[0]), .rn_ep(r_ep[0]), .rn_p(r_p[0]), .qn(q[0]), .qn_v(q_v[0]), .qn_bad(q_bad[0]),
        .rs_v(r_v[1]), .rs_t(r_t[1]), .rs_ep(r_ep[1]), .rs_p(r_p[1]), .qs(q[1]), .qs_v(q_v[1]), .qs_bad(q_bad[1]));
    end else begin : g_hw
`ifndef OT_QFD_XS_HARD
    qfd_xhead_w #(.MUT(HEAD_MUT), .REQ_PIPE(REQ_PIPE)) u_h (
`else
    qfd_xhead_w u_h (
`endif
        .ck(ck0), .rst_n(rst_n), .tids(tids), .fault_i(fault_i), .fault(fault),
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
`ifndef OT_QFD_XS_HARD
            ot_qfd_xs_leaf #(.NCH(4)) u_leaf (
`else
            ot_qfd_xs_leaf u_leaf (
`endif
                .clk(ck[1 + 4*h + j]), .rst_n(rst_n),
                .w_v(cw_v[h][j]), .w_ep(cw_ep[h][j]), .w_off(cw_off[h][j]), .w_m(cw_m[h][j]), .w_d(cw_d[h][j]),
                .w_ctl(cw_ctl[h][j]), .c_v(cc_v[h][j]), .c_ep(cc_ep[h][j]),
                .wo_v(cw_v[h][j+1]), .wo_ep(cw_ep[h][j+1]), .wo_off(cw_off[h][j+1]), .wo_m(cw_m[h][j+1]),
                .wo_d(cw_d[h][j+1]), .wo_ctl(cw_ctl[h][j+1]), .co_v(cc_v[h][j+1]), .co_ep(cc_ep[h][j+1]),
                .r_v(r_v[h][j]), .r_t(r_t[h][j]), .r_ep(r_ep[h][j]), .r_p(r_p[h][28*j +: 28]),
                .q_v(q_v[h][j]), .q(q[h][64*j +: 64]), .q_bad(q_bad[h][j]));
        end
    end endgenerate
endmodule

module qfd_xcol_e #(parameter integer HEAD_MUT = 0,   // bench-only; the die instantiates the default
    parameter integer REQ_PIPE = 0) (   // read-request relay stages head -> leaves (candidate 1: +1 x-read edge, DX 11)
    input  wire          ck0, ck1, ck2, ck3, ck4, ck5, ck6, ck7, ck8,
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
    ot_qfd_xcol #(.HEAD_MUT(HEAD_MUT), .EAST(1), .REQ_PIPE(REQ_PIPE)) u_c (.ck0(ck0), .ck1(ck1), .ck2(ck2), .ck3(ck3), .ck4(ck4), .ck5(ck5), .ck6(ck6), .ck7(ck7), .ck8(ck8),
        .rst_n(rst_n), .tids(tids), .fault_i(fault_i), .fault(fault), .h_in(w_d), .h_out(e_d),
        .n_d(n_d), .s_d(s_d));
endmodule

module qfd_xcol_w #(parameter integer HEAD_MUT = 0,   // bench-only; the die instantiates the default
    parameter integer REQ_PIPE = 0) (   // read-request relay stages head -> leaves (candidate 1: +1 x-read edge, DX 11)
    input  wire          ck0, ck1, ck2, ck3, ck4, ck5, ck6, ck7, ck8,
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
    ot_qfd_xcol #(.HEAD_MUT(HEAD_MUT), .EAST(0), .REQ_PIPE(REQ_PIPE)) u_c (.ck0(ck0), .ck1(ck1), .ck2(ck2), .ck3(ck3), .ck4(ck4), .ck5(ck5), .ck6(ck6), .ck7(ck7), .ck8(ck8),
        .rst_n(rst_n), .tids(tids), .fault_i(fault_i), .fault(fault), .h_in(e_d), .h_out(w_d),
        .n_d(n_d), .s_d(s_d));
endmodule
