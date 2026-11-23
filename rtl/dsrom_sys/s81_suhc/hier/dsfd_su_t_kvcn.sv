`timescale 1ns/1ps
// S81-KVLEAF-T2-ARCH 11-23: masters of the slice-leaf KV bank (ot_s81sl_kv_bank, HARD_RQ >= 2) that the closed KV v3
// masters of dsfd_su_t_kv.sv do not cover: the CN / IK form of the tap and of the norm engines (the SAME bodies
// ot_s81_su_kvt / ot_s81_su_kve with the CN outputs e_mode / e_nb / norm_v / norm_y brought out), the CN and IK
// writers and the IK reduce.  Wrappers only: fixed parameters, renamed clock / reset, no logic.  Each is hardened once
// and placed as a hard core of the leaf partition (x4 tap, x56 engine, x8 RoPE engine, x16 CN writer, x4 IK writer,
// x1 IK reduce); the bank then keeps only its relays and the slot merge as soft logic.
module dsfd_su_t_kvtc (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [1:0] dn_gsel, input wire [7:0] dn_jid,
    input  wire [15:0]   dn_v, input wire [2047:0] dn_d, input wire [64:0] i_f,
    output wire [31:0]   e_v, output wire [4095:0] e_d, output wire e_gk, output wire [1:0] e_gr, output wire [1:0] e_gw,
    output wire          e_go, output wire [1:0] e_mode, output wire [13:0] e_ob, output wire [13:0] e_nb,
    output wire [31:0]   e_eps, output wire [511:0] e_cs,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_kvt #(.N(512), .S_RD(16), .NFI(65), .MUT(0)) u_t (
        .clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_gsel_i(dn_gsel), .dn_jid_i(dn_jid),
        .dn_v_i(dn_v), .dn_d_i(dn_d), .i_f(i_f), .e_v(e_v), .e_d(e_d), .e_gk(e_gk), .e_gr(e_gr), .e_gw(e_gw),
        .e_go(e_go), .e_mode(e_mode), .e_ob(e_ob), .e_nb(e_nb), .e_eps(e_eps), .e_cs(e_cs), .o_fu(o_fu), .o_fo(o_fo),
        .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
endmodule
module dsfd_su_t_kvec (
    input  wire          ck, rst,
    input  wire          i_v, input wire [255:0] i_x, input wire i_gk, input wire [1:0] i_gr, input wire [1:0] i_gw,
    input  wire          r_v, input wire [31:0] r_d,
    output wire          p_v, output wire [31:0] p_d, output wire norm_v, output wire [127:0] norm_y,
    output wire          y_v, output wire [255:0] y, output wire o_f
);
    ot_s81_su_kve #(.RP(0), .LM(5), .LA(4)) u_e (
        .clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .i_gk(i_gk), .i_gr(i_gr), .i_gw(i_gw), .i_cos(128'd0),
        .i_sin(128'd0), .r_v(r_v), .r_d(r_d), .p_v(p_v), .p_d(p_d), .norm_v(norm_v), .norm_y(norm_y), .y_v(y_v), .y(y),
        .o_f(o_f));
endmodule
module dsfd_su_t_kvpc (
    input  wire          ck, rst,
    input  wire          i_v, input wire [255:0] i_x, input wire i_gk, input wire [1:0] i_gr, input wire [1:0] i_gw,
    input  wire [127:0]  i_cos, input wire [127:0] i_sin, input wire r_v, input wire [31:0] r_d,
    output wire          p_v, output wire [31:0] p_d, output wire norm_v, output wire [127:0] norm_y,
    output wire          y_v, output wire [255:0] y, output wire o_f
);
    ot_s81_su_kve #(.RP(1), .LM(5), .LA(4)) u_e (
        .clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .i_gk(i_gk), .i_gr(i_gr), .i_gw(i_gw), .i_cos(i_cos),
        .i_sin(i_sin), .r_v(r_v), .r_d(r_d), .p_v(p_v), .p_d(p_d), .norm_v(norm_v), .norm_y(norm_y), .y_v(y_v), .y(y),
        .o_f(o_f));
endmodule
module dsfd_su_t_cnw (
    input  wire          ck, rst,
    input  wire          i_v, input wire [1023:0] i_x, input wire [13:0] i_ob, input wire [3:0] i_block,
    output wire          o_v, output wire [13:0] o_a, output wire [15:0] o_m, output wire [511:0] o_d, output wire o_fault
);
    ot_s81_su_cn_write #(.E4M3(1)) u_w (
        .clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .i_ob(i_ob), .i_block(i_block),
        .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fault(o_fault));
endmodule
module dsfd_su_t_ikw (
    input  wire          ck, rst,
    input  wire          i_v, input wire [1023:0] i_x, input wire [13:0] i_ob, input wire [3:0] i_block,
    output wire          o_v, output wire [13:0] o_a, output wire [15:0] o_m, output wire [511:0] o_d, output wire o_fault
);
    ot_s81_su_cn_write #(.E4M3(0)) u_w (
        .clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .i_ob(i_ob), .i_block(i_block),
        .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fault(o_fault));
endmodule
module dsfd_su_t_ikr (
    input  wire          ck, rst,
    input  wire          go, input wire [31:0] eps, input wire [15:0] p_v, input wire [511:0] p_d,
    output wire          r_v, output wire [31:0] r_d, output wire fault
);
    ot_s81_su_ik_reduce u_r (
        .ck_half({2{ck}}), .rs_half({2{rst}}), .ck_reduce(ck), .rs_reduce(rst), .go(go), .eps(eps),
        .p_v(p_v), .p_d(p_d), .r_v(r_v), .r_d(r_d), .fault(fault));
endmodule


// One implemented bank-to-engine relay. A separate master per stage lets the
// parent keep three physical reaches without exposing a new timing calendar.
module dsfd_su_t_kvi (
    input wire ck, rst,
    input wire i_v, input wire [255:0] i_d,
    output wire o_v, output wire [255:0] o_d
);
    ot_hdc_delay #(.W(1), .D(1), .RESET(1)) u_iv (.clk(ck), .rst_n(rst), .d(i_v), .q(o_v));
    ot_hdc_delay #(.W(256), .D(1)) u_id (.clk(ck), .rst_n(rst), .d(i_d), .q(o_d));
endmodule
