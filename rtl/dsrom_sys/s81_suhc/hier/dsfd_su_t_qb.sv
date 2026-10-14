`timescale 1ns/1ps
// QB (el1011-s81su, spec v3): the tap at the down-spine stop + 8 position-independent engines (one act-quant block
// each, SRAM wait line), hardened once and stepped; cfg_b = the engine's block index (a constant at the parent).
// The tap is split in two half-taps (el1013-s81su, 10-13): dsfd_su_t_qbtl = slots 0..7 + the control; slots 8..15 are
// the data-only half-tap dsfd_su_t_swth (rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_sw.sv, hardened once for SW and QB).
module dsfd_su_t_qbtl (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [1:0] dn_gsel, input wire dn_fp4,
    input  wire [7:0]    dn_jid, input wire [15:0] dn_v,
    input  wire [4095:0] dn_dl,
    output wire [15:0]   e_v, output wire [4095:0] e_dl, output wire [191:0] e_t, output wire [13:0] e_ob, output wire e_f4,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_qbtl #(.QB_NB(32), .S_RD(16), .NPB(8)) u_t (
        .clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_gsel_i(dn_gsel), .dn_fp4_i(dn_fp4),
        .dn_jid_i(dn_jid), .dn_v_i(dn_v), .dn_d_i(dn_dl), .e_v(e_v), .e_d(e_dl), .e_t(e_t), .e_ob(e_ob),
        .e_f4(e_f4), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
endmodule
module dsfd_su_t_qbe (
    input  wire          ck, rst,
    input  wire [3:0]    cfg_b,
    input  wire          i_vlo, i_vhi, input wire [511:0] i_lo, input wire [511:0] i_hi,
    input  wire [11:0]   i_tlo, input wire [11:0] i_thi, input wire [13:0] i_ob, input wire i_f4,
    input  wire          nx_i_v, input wire [255:0] nx_i_q, input wire [9:0] nx_i_e,
    output wire          nx_o_v, output wire [255:0] nx_o_q, output wire [9:0] nx_o_e,
    output wire [1:0]    o_v, output wire [27:0] o_a, output wire [31:0] o_m, output wire [1023:0] o_d,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_qbe #(.QB_NB(32), .NPB(8)) u_e (
        .clk(ck), .rst_in(rst), .cfg_b(cfg_b), .i_vlo(i_vlo), .i_vhi(i_vhi), .i_lo(i_lo), .i_hi(i_hi), .i_tlo(i_tlo),
        .i_thi(i_thi), .i_ob(i_ob), .i_f4(i_f4), .nx_i_v(nx_i_v), .nx_i_q(nx_i_q), .nx_i_e(nx_i_e), .nx_o_v(nx_o_v),
        .nx_o_q(nx_o_q), .nx_o_e(nx_o_e), .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo),
        .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
endmodule
