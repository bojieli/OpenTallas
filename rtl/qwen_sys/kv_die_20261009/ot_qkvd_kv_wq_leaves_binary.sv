`timescale 1ns/1ps
// Exact full32-PC stack composition of binary ctl and original per-PC leaves.
// Default remains one-hot; FLANE_BINARY=1 connects actual low3 pins without ORs.
module ot_qkvd_kv_wq_leaves_binary #(
    parameter integer HD   = 128,
    parameter integer NPC  = 32,
    parameter integer QD   = 4,
    parameter integer TAGW = 9,
    parameter integer MUT  = 0,
    parameter integer RLY  = 0,
    parameter integer FLANE_BINARY = 0
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  kvw_v,
    input  wire [1:0]            kvw_vg,
    input  wire [13:0]           kvw_t,
    input  wire [5:0]            kvw_layer,
    input  wire [HD*8-1:0]       kvw_d,
    output wire                  kvw_cr,
    output wire [NPC-1:0]        w_v,
    output wire [24*NPC-1:0]     w_sec,
    output wire [256*NPC-1:0]    w_data,
    output wire [TAGW*NPC-1:0]   w_tag,
    input  wire [NPC-1:0]        w_room,
    input  wire [NPC-1:0]        wd_v,
    input  wire [TAGW*NPC-1:0]   wd_tag,
    output wire                  rw_v,
    output wire [21:0]           rw_id,
    output wire                  fault
);
    wire [3:0] fv, rv, rb, fv_d, rv_d, rb_d;
    wire [4*256-1:0] fd, fd_d; wire [4*24-1:0] fs, fs_d; wire [4*8-1:0] fl, fl_d; wire [4*TAGW-1:0] ft, ft_d;
    ot_qkvd_kv_wq_ctl_binary #(.HD(HD), .QD(QD), .TAGW(TAGW), .MUT(MUT), .FLANE_BINARY(FLANE_BINARY)) u_ctl (.clk(clk), .rst_n(rst_n), .kvw_v(kvw_v),
        .kvw_vg(kvw_vg), .kvw_t(kvw_t), .kvw_layer(kvw_layer), .kvw_d(kvw_d), .kvw_cr(kvw_cr), .f_v(fv), .f_d(fd),
        .f_sec(fs), .f_lane(fl), .f_tag(ft), .r_v(rv_d), .r_bad(rb_d), .rw_v(rw_v), .rw_id(rw_id), .fault(fault));
    ot_hdc_delay #(.W(4), .D(RLY), .RESET(1)) u_rf (.clk(clk), .rst_n(rst_n), .d(fv), .q(fv_d));
    ot_hdc_delay #(.W(4*(256+24+8+TAGW)), .D(RLY)) u_rfd (.clk(clk), .rst_n(rst_n), .d({fd, fs, fl, ft}), .q({fd_d, fs_d, fl_d, ft_d}));
    ot_hdc_delay #(.W(8), .D(RLY), .RESET(1)) u_rr (.clk(clk), .rst_n(rst_n), .d({rv, rb}), .q({rv_d, rb_d}));
    genvar g, i;
    generate for (g = 0; g < 4; g = g + 1) begin : g_grp
        // the ctl's one-hot lane -> a 3-bit lane on the chain
        wire [7:0] oh = fl_d[8*g +: 8];
        wire [2:0] ln = (FLANE_BINARY != 0) ? oh[2:0] : {oh[4] | oh[5] | oh[6] | oh[7], oh[2] | oh[3] | oh[6] | oh[7], oh[1] | oh[3] | oh[5] | oh[7]};
        wire [8:0] cv; wire [9*256-1:0] cd; wire [9*24-1:0] cs; wire [9*TAGW-1:0] ct; wire [9*3-1:0] cl;
        wire [8:0] dv, db;
        assign cv[0] = fv_d[g]; assign cd[255:0] = fd_d[256*g +: 256]; assign cs[23:0] = fs_d[24*g +: 24];
        assign ct[TAGW-1:0] = ft_d[TAGW*g +: TAGW]; assign cl[2:0] = ln;
        assign dv[8] = 1'b0; assign db[8] = 1'b0;
        for (i = 0; i < 8; i = i + 1) begin : g_leaf
            ot_qkvd_kv_wq_leaf #(.TAGW(TAGW)) u_l (.clk(clk), .rst_n(rst_n),
                .lane((MUT == 3 && g == 0 && i == 0) ? 3'd7 ^ 3'(i) : 3'(i)),
                .c_v(cv[i]), .c_d(cd[256*i +: 256]), .c_sec(cs[24*i +: 24]), .c_tag(ct[TAGW*i +: TAGW]), .c_lane(cl[3*i +: 3]),
                .n_v(cv[i+1]), .n_d(cd[256*(i+1) +: 256]), .n_sec(cs[24*(i+1) +: 24]), .n_tag(ct[TAGW*(i+1) +: TAGW]),
                .n_lane(cl[3*(i+1) +: 3]), .dn_v(dv[i+1]), .dn_bad(db[i+1]), .dp_v(dv[i]), .dp_bad(db[i]),
                .w_v(w_v[8*g + i]), .w_sec(w_sec[24*(8*g + i) +: 24]), .w_data(w_data[256*(8*g + i) +: 256]),
                .w_tag(w_tag[TAGW*(8*g + i) +: TAGW]), .w_room(w_room[8*g + i]), .wd_v(wd_v[8*g + i]),
                .wd_tag(wd_tag[TAGW*(8*g + i) +: TAGW]));
        end
        assign rv[g] = dv[0]; assign rb[g] = db[0];
    end endgenerate
endmodule
