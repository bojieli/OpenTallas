`timescale 1ns/1ps
// SW (el1011-s81su-sw, PHYSICAL SPEC SW v3): the tap at the down-spine stop (two half-taps) + 128 position-independent lane engines (one
// SwiGLU lane pipeline over 8 lanes each, SRAM wait lines), hardened once and stepped; the act-quant engines are the QB
// master dsfd_su_t_qbe (unchanged).  Production params: SW_W 1024, S_RD 16, 8 quant engines, 4 passes, LPE 8.
// The tap is split in two half-taps (el1013-s81su-qual): dsfd_su_t_swtl = slots 0..7 + the control, dsfd_su_t_swth =
// slots 8..15 (data only); each a 36.72 x 453.6 column, pins registered on both faces.
module dsfd_su_t_swtl (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [1:0] dn_gsel, input wire dn_fp4,
    input  wire [7:0]    dn_jid, input wire [15:0] dn_v,
    input  wire [4095:0] dn_dl,
    input  wire [31:0]   i_f,
    output wire [4095:0] e_dl, output wire [3:0] e_gv, output wire [3:0] e_uv,
    output wire [11:0]   e_t, output wire [31:0] e_w, output wire [31:0] e_lim, output wire [13:0] e_ob,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_swtl #(.SW_W(1024), .S_RD(16), .NSQ(8), .NCH(32)) u_t (
        .clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_gsel_i(dn_gsel), .dn_fp4_i(dn_fp4),
        .dn_jid_i(dn_jid), .dn_v_i(dn_v), .dn_d_i(dn_dl), .i_f(i_f), .e_d(e_dl), .e_gv(e_gv), .e_uv(e_uv),
        .e_t(e_t), .e_w(e_w), .e_lim(e_lim), .e_ob(e_ob), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
        .o_rdy(o_rdy), .o_rjid(o_rjid));
endmodule
module dsfd_su_t_swth (
    input  wire          ck,
    input  wire [4095:0] dn_dh,
    output wire [4095:0] e_dh
);
    ot_s81_su_swth #(.S_RD(16)) u_t (.clk(ck), .dn_d_i(dn_dh), .e_d(e_dh));
endmodule
module dsfd_su_t_swe (
    input  wire          ck, rst,
    input  wire          i_gv, i_uv, input wire [255:0] i_d, input wire [11:0] i_t, input wire [31:0] i_w, input wire [31:0] i_lim,
    input  wire          c_iv, input wire [127:0] c_id, input wire [11:0] c_it, input wire c_if,
    output wire          c_ov, output wire [127:0] c_od, output wire [11:0] c_ot, output wire c_of
);
    ot_s81_su_swe #(.LPE(8), .LM(5), .LA(4)) u_e (
        .clk(ck), .rst_in(rst), .i_gv(i_gv), .i_uv(i_uv), .i_d(i_d), .i_t(i_t), .i_w(i_w), .i_lim(i_lim), .c_iv(c_iv),
        .c_id(c_id), .c_it(c_it), .c_if(c_if), .c_ov(c_ov), .c_od(c_od), .c_ot(c_ot), .c_of(c_of));
endmodule
