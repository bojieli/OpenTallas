`timescale 1ns/1ps
// Physical CN/IK leaf boundaries. These wrappers add no state or arithmetic.
// Each stateful core is contained by exactly one hardened leaf with scalar
// clock/reset pins. CN and IK share the existing KVE bank in dsfd_sp_su_h;
// ot_s81_su_cn_ik is a standalone arithmetic test composition, not another bank.
// Source dependency: ot_s81_su_cn_ik.sv d67d13758 or a verified successor.
module dsfd_su_t_cn8 (
    input wire ck, rst, i_v,
    input wire [1023:0] i_x,
    input wire [13:0] i_ob,
    input wire [3:0] i_block,
    output wire o_v,
    output wire [13:0] o_a,
    output wire [15:0] o_m,
    output wire [511:0] o_d,
    output wire o_fault
);
    ot_s81_su_cn_write #(.E4M3(1)) u_write (
        .clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .i_ob(i_ob), .i_block(i_block),
        .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fault(o_fault));
endmodule

module dsfd_su_t_cn4 (
    input wire ck, rst, i_v,
    input wire [1023:0] i_x,
    input wire [13:0] i_ob,
    input wire [3:0] i_block,
    output wire o_v,
    output wire [13:0] o_a,
    output wire [15:0] o_m,
    output wire [511:0] o_d,
    output wire o_fault
);
    ot_s81_su_cn_write #(.E4M3(0)) u_write (
        .clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .i_ob(i_ob), .i_block(i_block),
        .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fault(o_fault));
endmodule

module dsfd_su_t_cnnw (
    input wire ck, rst, i_v,
    input wire [511:0] i_x,
    input wire [13:0] i_ob,
    input wire [3:0] i_block,
    output wire o_v,
    output wire [13:0] o_a,
    output wire [511:0] o_d
);
    ot_s81_su_cn_norm_write u_write (
        .clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .i_ob(i_ob), .i_block(i_block),
        .o_v(o_v), .o_a(o_a), .o_d(o_d));
endmodule

module dsfd_su_t_ikh (
    input wire ck, rst, i_go,
    input wire [7:0] p_v, p_p,
    input wire [255:0] p_d,
    output wire s_v, s_p,
    output wire [31:0] s_d,
    output wire o_f
);
    ot_s81_su_qnh #(.NE(8), .LA(4)) u_half (
        .clk(ck), .rst_in(rst), .i_go(i_go), .p_v(p_v), .p_p(p_p), .p_d(p_d),
        .s_v(s_v), .s_p(s_p), .s_d(s_d), .o_f(o_f));
endmodule

module dsfd_su_t_ikr (
    input wire ck, rst, i_go,
    input wire [31:0] i_eps,
    input wire [1:0] p_v, p_p, p_f,
    input wire [63:0] p_d,
    output wire r_v,
    output wire [31:0] r_d,
    output wire o_f
);
    ot_s81_su_qnr #(.NE(2), .NV(1), .D(128), .LM(5), .LA(4)) u_reduce (
        .clk(ck), .rst_in(rst), .i_go(i_go), .i_eps(i_eps),
        .p_v(p_v), .p_p(p_p), .p_d(p_d), .p_f(p_f), .r_v(r_v), .r_d(r_d), .o_f(o_f));
endmodule
