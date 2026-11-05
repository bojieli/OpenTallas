// DIE-HBM-61/SPLIT d44v part 6 (u_core -> ot_hgi_sfu_opsb__comp); from gen_core_kit_hbm.py (ELEM-HBM): pass-through wrapper, plan pins -> RTL top; wires only.
`default_nettype none
module ot_hgi_sfu_core_split3__opstore_b__fcore (
    input wire clk,
    output wire g_operand_2_u_group_flt,
    input wire [383:0] g_operand_2_u_group_ra,
    output wire [511:0] g_operand_2_u_group_rd,
    input wire [15:0] g_operand_2_u_group_rq,
    input wire g_operand_2_u_group_rst_n,
    input wire [119:0] g_operand_2_u_group_sw_addr,
    input wire [2047:0] g_operand_2_u_group_sw_d,
    input wire [63:0] g_operand_2_u_group_sw_mask,
    input wire [7:0] g_operand_2_u_group_sw_v,
    output wire g_operand_3_u_group_flt,
    input wire [383:0] g_operand_3_u_group_ra,
    output wire [511:0] g_operand_3_u_group_rd,
    input wire [15:0] g_operand_3_u_group_rq,
    input wire [7:0] g_operand_3_u_group_sw_v,
    output wire u_output_flt,
    input wire [15:0] u_output_lw,
    input wire [383:0] u_output_lwa,
    input wire [511:0] u_output_lwd,
    input wire [29:0] u_output_sr_addr,
    output wire [511:0] u_output_sr_d,
    output wire [1:0] u_output_sr_rv,
    input wire [1:0] u_output_sr_v
);
    ot_hgi_sfu_opsb__comp u_core (
        .group0_clk(clk),
        .group0_flt(g_operand_2_u_group_flt),
        .group0_ra(g_operand_2_u_group_ra),
        .group0_rd(g_operand_2_u_group_rd),
        .group0_rq(g_operand_2_u_group_rq),
        .group0_rst_n(g_operand_2_u_group_rst_n),
        .group0_sw_addr(g_operand_2_u_group_sw_addr),
        .group0_sw_d(g_operand_2_u_group_sw_d),
        .group0_sw_mask(g_operand_2_u_group_sw_mask),
        .group0_sw_v(g_operand_2_u_group_sw_v),
        .group1_flt(g_operand_3_u_group_flt),
        .group1_ra(g_operand_3_u_group_ra),
        .group1_rd(g_operand_3_u_group_rd),
        .group1_rq(g_operand_3_u_group_rq),
        .group1_sw_v(g_operand_3_u_group_sw_v),
        .output_flt(u_output_flt),
        .output_lw(u_output_lw),
        .output_lwa(u_output_lwa),
        .output_lwd(u_output_lwd),
        .output_sr_addr(u_output_sr_addr),
        .output_sr_d(u_output_sr_d),
        .output_sr_rv(u_output_sr_rv),
        .output_sr_v(u_output_sr_v));
endmodule
`default_nettype wire

// DIE-HBM-61/SPLIT d44v part 6: plan module ot_hgi_sfu_core_split3__opstore_b = thin parent glue of the split hard core (wires only; the
// sub-cores of ot_hgi_sfu_opsb__comp are the hard cores, each with its own kit face shell).  Ports open in the composition: none.
`default_nettype none
module ot_hgi_sfu_core_split3__opstore_b (
    input wire clk,
    output wire g_operand_2_u_group_flt,
    input wire [383:0] g_operand_2_u_group_ra,
    output wire [511:0] g_operand_2_u_group_rd,
    input wire [15:0] g_operand_2_u_group_rq,
    input wire g_operand_2_u_group_rst_n,
    input wire [119:0] g_operand_2_u_group_sw_addr,
    input wire [2047:0] g_operand_2_u_group_sw_d,
    input wire [63:0] g_operand_2_u_group_sw_mask,
    input wire [7:0] g_operand_2_u_group_sw_v,
    output wire g_operand_3_u_group_flt,
    input wire [383:0] g_operand_3_u_group_ra,
    output wire [511:0] g_operand_3_u_group_rd,
    input wire [15:0] g_operand_3_u_group_rq,
    input wire [7:0] g_operand_3_u_group_sw_v,
    output wire u_output_flt,
    input wire [15:0] u_output_lw,
    input wire [383:0] u_output_lwa,
    input wire [511:0] u_output_lwd,
    input wire [29:0] u_output_sr_addr,
    output wire [511:0] u_output_sr_d,
    output wire [1:0] u_output_sr_rv,
    input wire [1:0] u_output_sr_v
);
    ot_hgi_sfu_core_split3__opstore_b__fcore u_fcore (.clk(clk), .g_operand_2_u_group_flt(g_operand_2_u_group_flt), .g_operand_2_u_group_ra(g_operand_2_u_group_ra), .g_operand_2_u_group_rd(g_operand_2_u_group_rd), .g_operand_2_u_group_rq(g_operand_2_u_group_rq), .g_operand_2_u_group_rst_n(g_operand_2_u_group_rst_n), .g_operand_2_u_group_sw_addr(g_operand_2_u_group_sw_addr), .g_operand_2_u_group_sw_d(g_operand_2_u_group_sw_d), .g_operand_2_u_group_sw_mask(g_operand_2_u_group_sw_mask), .g_operand_2_u_group_sw_v(g_operand_2_u_group_sw_v), .g_operand_3_u_group_flt(g_operand_3_u_group_flt), .g_operand_3_u_group_ra(g_operand_3_u_group_ra), .g_operand_3_u_group_rd(g_operand_3_u_group_rd), .g_operand_3_u_group_rq(g_operand_3_u_group_rq), .g_operand_3_u_group_sw_v(g_operand_3_u_group_sw_v), .u_output_flt(u_output_flt), .u_output_lw(u_output_lw), .u_output_lwa(u_output_lwa), .u_output_lwd(u_output_lwd), .u_output_sr_addr(u_output_sr_addr), .u_output_sr_d(u_output_sr_d), .u_output_sr_rv(u_output_sr_rv), .u_output_sr_v(u_output_sr_v));
endmodule
`default_nettype wire
