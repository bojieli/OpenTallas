`timescale 1ns/1ps
module dsfd_m2l_vr_68x11__hr_E3 (
    input wire [0:0] ck,
    output wire [760:0] o,
    input wire [0:0] rs,
    input wire [69:0] di0,
    input wire [0:0] fi0,
    input wire [69:0] di1,
    input wire [0:0] fi1,
    input wire [69:0] di2,
    input wire [0:0] fi2,
    input wire [69:0] di3,
    input wire [0:0] fi3,
    input wire [69:0] di4,
    input wire [0:0] fi4,
    input wire [69:0] di5,
    input wire [0:0] fi5,
    input wire [69:0] di6,
    input wire [0:0] fi6,
    input wire [69:0] di7,
    input wire [0:0] fi7,
    input wire [69:0] di8,
    input wire [0:0] fi8,
    input wire [69:0] di9,
    input wire [0:0] fi9,
    input wire [69:0] di10,
    input wire [0:0] fi10
);
    reg [1:0] rsl_q; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rsl_q <= 2'b00; else rsl_q <= {rsl_q[0], 1'b1};
    wire rsl = rsl_q[1];
    wire [760:0] o_d;
    reg [69:0] dq0; always @(negedge fi0[0]) dq0 <= di0;   // pin register, falling forwarded edge
    wire [69:0] rc0 = dq0;
    wire [68:0] rq0; wire lv0, fl0;
    ot_s81_static_lane_end #(.W(69)) u_0 (.f_ck(fi0[0]), .i(rc0), .ck(ck[0]), .rst_n(rsl), .o(rq0), .live(lv0), .fault(fl0));
    assign o_d[68:0] = {rq0[68:1], rq0[0] & lv0};
    reg [69:0] dq1; always @(negedge fi1[0]) dq1 <= di1;   // pin register, falling forwarded edge
    wire [69:0] rc1 = dq1;
    wire [68:0] rq1; wire lv1, fl1;
    ot_s81_static_lane_end #(.W(69)) u_1 (.f_ck(fi1[0]), .i(rc1), .ck(ck[0]), .rst_n(rsl), .o(rq1), .live(lv1), .fault(fl1));
    assign o_d[137:69] = {rq1[68:1], rq1[0] & lv1};
    reg [69:0] dq2; always @(negedge fi2[0]) dq2 <= di2;   // pin register, falling forwarded edge
    wire [69:0] rc2 = dq2;
    wire [68:0] rq2; wire lv2, fl2;
    ot_s81_static_lane_end #(.W(69)) u_2 (.f_ck(fi2[0]), .i(rc2), .ck(ck[0]), .rst_n(rsl), .o(rq2), .live(lv2), .fault(fl2));
    assign o_d[206:138] = {rq2[68:1], rq2[0] & lv2};
    reg [69:0] dq3; always @(negedge fi3[0]) dq3 <= di3;   // pin register, falling forwarded edge
    wire [69:0] rc3 = dq3;
    wire [68:0] rq3; wire lv3, fl3;
    ot_s81_static_lane_end #(.W(69)) u_3 (.f_ck(fi3[0]), .i(rc3), .ck(ck[0]), .rst_n(rsl), .o(rq3), .live(lv3), .fault(fl3));
    assign o_d[275:207] = {rq3[68:1], rq3[0] & lv3};
    reg [69:0] dq4; always @(negedge fi4[0]) dq4 <= di4;   // pin register, falling forwarded edge
    wire [69:0] rc4 = dq4;
    wire [68:0] rq4; wire lv4, fl4;
    ot_s81_static_lane_end #(.W(69)) u_4 (.f_ck(fi4[0]), .i(rc4), .ck(ck[0]), .rst_n(rsl), .o(rq4), .live(lv4), .fault(fl4));
    assign o_d[344:276] = {rq4[68:1], rq4[0] & lv4};
    reg [69:0] dq5; always @(negedge fi5[0]) dq5 <= di5;   // pin register, falling forwarded edge
    wire [69:0] rc5 = dq5;
    wire [68:0] rq5; wire lv5, fl5;
    ot_s81_static_lane_end #(.W(69)) u_5 (.f_ck(fi5[0]), .i(rc5), .ck(ck[0]), .rst_n(rsl), .o(rq5), .live(lv5), .fault(fl5));
    assign o_d[413:345] = {rq5[68:1], rq5[0] & lv5};
    reg [69:0] dq6; always @(negedge fi6[0]) dq6 <= di6;   // pin register, falling forwarded edge
    wire [69:0] rc6 = dq6;
    wire [68:0] rq6; wire lv6, fl6;
    ot_s81_static_lane_end #(.W(69)) u_6 (.f_ck(fi6[0]), .i(rc6), .ck(ck[0]), .rst_n(rsl), .o(rq6), .live(lv6), .fault(fl6));
    assign o_d[482:414] = {rq6[68:1], rq6[0] & lv6};
    reg [69:0] dq7; always @(negedge fi7[0]) dq7 <= di7;   // pin register, falling forwarded edge
    wire [69:0] rc7 = dq7;
    wire [68:0] rq7; wire lv7, fl7;
    ot_s81_static_lane_end #(.W(69)) u_7 (.f_ck(fi7[0]), .i(rc7), .ck(ck[0]), .rst_n(rsl), .o(rq7), .live(lv7), .fault(fl7));
    assign o_d[551:483] = {rq7[68:1], rq7[0] & lv7};
    reg [69:0] dq8; always @(negedge fi8[0]) dq8 <= di8;   // pin register, falling forwarded edge
    wire [69:0] rc8 = dq8;
    wire [68:0] rq8; wire lv8, fl8;
    ot_s81_static_lane_end #(.W(69)) u_8 (.f_ck(fi8[0]), .i(rc8), .ck(ck[0]), .rst_n(rsl), .o(rq8), .live(lv8), .fault(fl8));
    assign o_d[620:552] = {rq8[68:1], rq8[0] & lv8};
    reg [69:0] dq9; always @(negedge fi9[0]) dq9 <= di9;   // pin register, falling forwarded edge
    wire [69:0] rc9 = dq9;
    wire [68:0] rq9; wire lv9, fl9;
    ot_s81_static_lane_end #(.W(69)) u_9 (.f_ck(fi9[0]), .i(rc9), .ck(ck[0]), .rst_n(rsl), .o(rq9), .live(lv9), .fault(fl9));
    assign o_d[689:621] = {rq9[68:1], rq9[0] & lv9};
    reg [69:0] dq10; always @(negedge fi10[0]) dq10 <= di10;   // pin register, falling forwarded edge
    wire [69:0] rc10 = dq10;
    wire [68:0] rq10; wire lv10, fl10;
    ot_s81_static_lane_end #(.W(69)) u_10 (.f_ck(fi10[0]), .i(rc10), .ck(ck[0]), .rst_n(rsl), .o(rq10), .live(lv10), .fault(fl10));
    assign o_d[758:690] = {rq10[68:1], rq10[0] & lv10};
    assign o_d[760:759] = {fl0 | fl1 | fl2 | fl3 | fl4 | fl5 | fl6 | fl7 | fl8 | fl9 | fl10, lv0 & lv1 & lv2 & lv3 & lv4 & lv5 & lv6 & lv7 & lv8 & lv9 & lv10};   // {fault, live}
    reg [760:0] o_q; always @(posedge ck[0]) o_q <= o_d;   // output pin flop
    assign o = o_q;
endmodule
