`timescale 1ns/1ps
// Qwen TP8 compute die, distributed x slices (el1014-qwen-dvm-build.log): the slot-shaped die masters, each hardened
// ONCE under its die name (same convention as ot_qwen_die_station_slots.sv: a bundle x is the pair x_d (data, flow
// direction) + x_r (ready, against the flow) on the bundle's face).
//
//   qfd_xcst_s   corridor station with x hold, south half   in a (N)  out b (S), tap (W)          384
//   qfd_xcst_n   corridor station with x hold, north half   in b (S)  out a (N), tap (W)          384
//   qfd_xcol_e   column x slice cluster, east chain: ot_qfd_xhead + 8 x ot_qfd_xs_leaf (two write chains)
//                head row in w (W) out e (E), corridors n (N) / s (S)                             24
//   qfd_xcol_w   the same, west chain: head row in e (E) out w (W)                                  24
//   ot_qfd_xs_leaf (qfd_xs_leaf) and ot_qfd_xs_tap (qfd_xs_tap) are their own die / cluster masters.
// Straps: sidx (station index in its corridor half), tid0 (tile id of the column's row 0) come from the die netlist
// as constant ties of a strap port (as tile_id), not logic.
module qfd_xcst_s #(parameter integer NW = 18, parameter integer AW = 24, parameter integer XOFF = 3) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [2:0]    sidx,
    input  wire [1+(3*NW+13*AW+13)+128+8-1:0] a_d,
    output wire          a_r,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] b_d,
    input  wire          b_r,
    output wire [1+(3*NW+13*AW+13)+128-1:0] tap_d,
    input  wire          tap_r
);
    ot_qfd_xcst #(.AW(AW), .NW(NW), .XOFF(XOFF)) u_st (.ck(ck), .rst_n(rst_n), .sidx(sidx), .a_d(a_d), .a_r(a_r),
        .b_d(b_d), .b_r(b_r), .tap_d(tap_d), .tap_r(tap_r));
endmodule

module qfd_xcst_n #(parameter integer NW = 18, parameter integer AW = 24, parameter integer XOFF = 3) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [2:0]    sidx,
    input  wire [1+(3*NW+13*AW+13)+128+8-1:0] b_d,
    output wire          b_r,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] a_d,
    input  wire          a_r,
    output wire [1+(3*NW+13*AW+13)+128-1:0] tap_d,
    input  wire          tap_r
);
    ot_qfd_xcst #(.AW(AW), .NW(NW), .XOFF(XOFF)) u_st (.ck(ck), .rst_n(rst_n), .sidx(sidx), .a_d(b_d), .a_r(b_r),
        .b_d(a_d), .b_r(a_r), .tap_d(tap_d), .tap_r(tap_r));
endmodule

// column cluster body: xhead + two write chains of NH/2 leaves (N chain = rows 0 .. NH-1, S chain = NH .. 2NH-1)
module ot_qfd_xcol #(
    parameter integer AW = 24, parameter integer NW = 18, parameter integer XCW = 12, parameter integer TG = 4,
    parameter integer NH = 8, parameter integer SMIN = 7, parameter integer SMAX = 11, parameter integer DX = 4
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [15:0]   tid0,
    input  wire [1+(3*NW+13*AW+13)+(2+AW+2*XCW+4+NW+1)+(2+(AW-6)+6+64+1024)-1:0] h_in,
    output wire          h_in_r,
    output wire [1+(3*NW+13*AW+13)+(2+AW+2*XCW+4+NW+1)+(2+(AW-6)+6+64+1024)-1:0] h_out,
    input  wire          h_out_r,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] n_d,
    input  wire          n_r,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] s_d,
    input  wire          s_r,
    output wire          fault
);
    localparam integer NCH = NH / 2;
    wire [1:0]    lw_v, lc_v;
    wire          lw_ep, lc_ep;
    wire [5:0]    lw_off;
    wire [63:0]   lw_m;
    wire [1023:0] lw_d;
    wire [NH*8-1:0] lw_ctl;
    wire [NH-1:0] lr_v, lr_t, lr_ep, lq_v, lq_bad;
    wire [NH*28-1:0] lr_p;
    wire [NH*64-1:0] lq;
    ot_qfd_xhead #(.AW(AW), .NW(NW), .XCW(XCW), .TG(TG), .NH(NH), .SMIN(SMIN), .SMAX(SMAX), .DX(DX)) u_head (
        .ck(ck), .rst_n(rst_n), .tid0(tid0), .a_d(h_in), .a_r(h_in_r), .b_d(h_out), .b_r(h_out_r),
        .n_d(n_d), .n_r(n_r), .s_d(s_d), .s_r(s_r),
        .lw_v(lw_v), .lw_ep(lw_ep), .lw_off(lw_off), .lw_m(lw_m), .lw_d(lw_d), .lw_ctl(lw_ctl),
        .lc_v(lc_v), .lc_ep(lc_ep), .lr_v(lr_v), .lr_t(lr_t), .lr_ep(lr_ep), .lr_p(lr_p),
        .lq(lq), .lq_v(lq_v), .lq_bad(lq_bad), .fault(fault));
    genvar h, j;
    generate for (h = 0; h < 2; h = h + 1) begin : g_ch
        wire          cv [0:NCH];
        wire          cep [0:NCH];
        wire          wv [0:NCH];
        wire          wep [0:NCH];
        wire [5:0]    woff [0:NCH];
        wire [63:0]   wm [0:NCH];
        wire [1023:0] wd [0:NCH];
        wire [NCH*8-1:0] wc [0:NCH];
        assign cv[0] = lc_v[h]; assign cep[0] = lc_ep; assign wv[0] = lw_v[h]; assign wep[0] = lw_ep;
        assign woff[0] = lw_off; assign wm[0] = lw_m; assign wd[0] = lw_d; assign wc[0] = lw_ctl[h*NCH*8 +: NCH*8];
        for (j = 0; j < NCH; j = j + 1) begin : g_leaf
            localparam integer LF = h * NCH + j;
`ifndef OT_QFD_XS_HARD
            ot_qfd_xs_leaf #(.NCH(NCH)) u_leaf (
`else
            ot_qfd_xs_leaf u_leaf (
`endif
                .clk(ck), .rst_n(rst_n),
                .w_v(wv[j]), .w_ep(wep[j]), .w_off(woff[j]), .w_m(wm[j]), .w_d(wd[j]), .w_ctl(wc[j]),
                .c_v(cv[j]), .c_ep(cep[j]),
                .wo_v(wv[j+1]), .wo_ep(wep[j+1]), .wo_off(woff[j+1]), .wo_m(wm[j+1]), .wo_d(wd[j+1]), .wo_ctl(wc[j+1]),
                .co_v(cv[j+1]), .co_ep(cep[j+1]),
                .r_v(lr_v[LF]), .r_t(lr_t[LF]), .r_ep(lr_ep[LF]), .r_p(lr_p[28*LF +: 28]),
                .q_v(lq_v[LF]), .q(lq[64*LF +: 64]), .q_bad(lq_bad[LF]));
        end
    end endgenerate
endmodule

module qfd_xcol_e (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [15:0]   tid0,
    input  wire [1+379+73+1114-1:0] w_d,
    output wire          w_r,
    output wire [1+379+73+1114-1:0] e_d,
    input  wire          e_r,
    output wire [1+379+128+8-1:0] n_d,
    input  wire          n_r,
    output wire [1+379+128+8-1:0] s_d,
    input  wire          s_r,
    output wire          fault
);
    ot_qfd_xcol u_c (.ck(ck), .rst_n(rst_n), .tid0(tid0), .h_in(w_d), .h_in_r(w_r), .h_out(e_d), .h_out_r(e_r),
        .n_d(n_d), .n_r(n_r), .s_d(s_d), .s_r(s_r), .fault(fault));
endmodule

module qfd_xcol_w (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [15:0]   tid0,
    input  wire [1+379+73+1114-1:0] e_d,
    output wire          e_r,
    output wire [1+379+73+1114-1:0] w_d,
    input  wire          w_r,
    output wire [1+379+128+8-1:0] n_d,
    input  wire          n_r,
    output wire [1+379+128+8-1:0] s_d,
    input  wire          s_r,
    output wire          fault
);
    ot_qfd_xcol u_c (.ck(ck), .rst_n(rst_n), .tid0(tid0), .h_in(e_d), .h_in_r(e_r), .h_out(w_d), .h_out_r(w_r),
        .n_d(n_d), .n_r(n_r), .s_d(s_d), .s_r(s_r), .fault(fault));
endmodule
