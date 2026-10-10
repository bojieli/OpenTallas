`timescale 1ns/1ps
// redesign-qwen 2026-10-09: composition of the KV-die write-queue tiles (ot_qkvd_kv_wq_tiles.sv) with the base's ports.
// The tiles composed with the base's ports (bench / die composition); RLY registered relay stages each way.
module ot_qkvd_kv_wq_tiles #(
    parameter integer HD   = 128,
    parameter integer NPC  = 32,
    parameter integer QD   = 4,
    parameter integer TAGW = 9,
    parameter integer MUT  = 0,
    parameter integer RLY  = 0
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
    localparam integer FW = 1 + 256 + 24 + 8 + TAGW;
    wire [3:0] fv, rv, rb, fv_d, rv_d, rb_d;
    wire [4*256-1:0] fd, fd_d; wire [4*24-1:0] fs, fs_d; wire [4*8-1:0] fl, fl_d; wire [4*TAGW-1:0] ft, ft_d;
    ot_qkvd_kv_wq_ctl #(.HD(HD), .QD(QD), .TAGW(TAGW), .MUT(MUT)) u_ctl (.clk(clk), .rst_n(rst_n), .kvw_v(kvw_v),
        .kvw_vg(kvw_vg), .kvw_t(kvw_t), .kvw_layer(kvw_layer), .kvw_d(kvw_d), .kvw_cr(kvw_cr), .f_v(fv), .f_d(fd),
        .f_sec(fs), .f_lane(fl), .f_tag(ft), .r_v(rv_d), .r_bad(rb_d), .rw_v(rw_v), .rw_id(rw_id), .fault(fault));
    ot_hdc_delay #(.W(4), .D(RLY), .RESET(1)) u_rf (.clk(clk), .rst_n(rst_n), .d(fv), .q(fv_d));
    ot_hdc_delay #(.W(4*(256+24+8+TAGW)), .D(RLY)) u_rfd (.clk(clk), .rst_n(rst_n), .d({fd, fs, fl, ft}), .q({fd_d, fs_d, fl_d, ft_d}));
    ot_hdc_delay #(.W(8), .D(RLY), .RESET(1)) u_rr (.clk(clk), .rst_n(rst_n), .d({rv, rb}), .q({rv_d, rb_d}));
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_grp
        ot_qkvd_kv_wq_grp #(.GP(8), .TAGW(TAGW), .NOPUSH((MUT == 3 && g == 0) ? 1 : 0)) u_g (.clk(clk), .rst_n(rst_n),
            .f_v(fv_d[g]), .f_d(fd_d[256*g +: 256]), .f_sec(fs_d[24*g +: 24]), .f_lane(fl_d[8*g +: 8]),
            .f_tag(ft_d[TAGW*g +: TAGW]),
            .w_v(w_v[8*g +: 8]), .w_sec(w_sec[24*8*g +: 24*8]), .w_data(w_data[256*8*g +: 256*8]),
            .w_tag(w_tag[TAGW*8*g +: TAGW*8]), .w_room(w_room[8*g +: 8]), .wd_v(wd_v[8*g +: 8]),
            .wd_tag(wd_tag[TAGW*8*g +: TAGW*8]), .r_v(rv[g]), .r_bad(rb[g]));
    end endgenerate
endmodule


// redesign-qwen 2026-10-10: the ctl tile + 4 groups x 8 per-PC leaves (feed chain down, done chain up), RLY relays between
// the ctl tile and each group's first leaf (both directions).  MUT 3: the leaf of sector 0's group never pushes (NOPUSH).
module ot_qkvd_kv_wq_leaves #(
    parameter integer HD   = 128,
    parameter integer NPC  = 32,
    parameter integer QD   = 4,
    parameter integer TAGW = 9,
    parameter integer MUT  = 0,
    parameter integer RLY  = 0
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
    ot_qkvd_kv_wq_ctl #(.HD(HD), .QD(QD), .TAGW(TAGW), .MUT(MUT)) u_ctl (.clk(clk), .rst_n(rst_n), .kvw_v(kvw_v),
        .kvw_vg(kvw_vg), .kvw_t(kvw_t), .kvw_layer(kvw_layer), .kvw_d(kvw_d), .kvw_cr(kvw_cr), .f_v(fv), .f_d(fd),
        .f_sec(fs), .f_lane(fl), .f_tag(ft), .r_v(rv_d), .r_bad(rb_d), .rw_v(rw_v), .rw_id(rw_id), .fault(fault));
    ot_hdc_delay #(.W(4), .D(RLY), .RESET(1)) u_rf (.clk(clk), .rst_n(rst_n), .d(fv), .q(fv_d));
    ot_hdc_delay #(.W(4*(256+24+8+TAGW)), .D(RLY)) u_rfd (.clk(clk), .rst_n(rst_n), .d({fd, fs, fl, ft}), .q({fd_d, fs_d, fl_d, ft_d}));
    ot_hdc_delay #(.W(8), .D(RLY), .RESET(1)) u_rr (.clk(clk), .rst_n(rst_n), .d({rv, rb}), .q({rv_d, rb_d}));
    genvar g, i;
    generate for (g = 0; g < 4; g = g + 1) begin : g_grp
        // the ctl's one-hot lane -> a 3-bit lane on the chain
        wire [7:0] oh = fl_d[8*g +: 8];
        wire [2:0] ln = {oh[4] | oh[5] | oh[6] | oh[7], oh[2] | oh[3] | oh[6] | oh[7], oh[1] | oh[3] | oh[5] | oh[7]};
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
