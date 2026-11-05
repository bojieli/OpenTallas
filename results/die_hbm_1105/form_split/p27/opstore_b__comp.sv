// HBM-FORM-SPLIT d44v part 27: plan form of the opstore_b composition, same ports as ot_hgi_sfu_split3_opstore_b_core.
`default_nettype none
module ot_hgi_sfu_opsb__comp #(parameter integer MUT = 0) (
    input wire group0_clk, input wire group0_rst_n, input wire [15:0] group0_rq, input wire [383:0] group0_ra,
    input wire [7:0] group0_sw_v, input wire [119:0] group0_sw_addr, input wire [63:0] group0_sw_mask, input wire [2047:0] group0_sw_d,
    input wire [15:0] group1_rq, input wire [383:0] group1_ra, input wire [7:0] group1_sw_v,
    input wire [1:0] output_sr_v, input wire [29:0] output_sr_addr, input wire [15:0] output_lw, input wire [383:0] output_lwa, input wire [511:0] output_lwd,
    output wire [511:0] group0_rd, output wire group0_flt, output wire [511:0] group1_rd, output wire group1_flt,
    output wire [511:0] output_sr_d, output wire [1:0] output_sr_rv, output wire output_flt);
    ot_hgi_sfu_opsb_group__fs u_g0 (.clk(group0_clk), .rst_n(group0_rst_n), .rq(group0_rq), .ra(group0_ra), .rd(group0_rd),
        .sw_v(group0_sw_v), .sw_addr(group0_sw_addr), .sw_mask(group0_sw_mask), .sw_d(group0_sw_d), .flt(group0_flt));
    ot_hgi_sfu_opsb_group__fs u_g1 (.clk(group0_clk), .rst_n(group0_rst_n), .rq(MUT == 1 ? group0_rq : group1_rq), .ra(group1_ra), .rd(group1_rd),
        .sw_v(MUT == 2 ? group0_sw_v : group1_sw_v), .sw_addr(group0_sw_addr), .sw_mask(group0_sw_mask), .sw_d(group0_sw_d), .flt(group1_flt));
    wire [29:0] oa = MUT == 3 ? {output_sr_addr[14:0], output_sr_addr[29:15]} : output_sr_addr;
    ot_hgi_sfu_opsb_output__fs u_o (.clk(group0_clk), .rst_n(group0_rst_n), .sr_v(output_sr_v), .sr_addr(oa), .sr_d(output_sr_d), .sr_rv(output_sr_rv),
        .lw(output_lw), .lwa(output_lwa), .lwd(output_lwd), .flt(output_flt));
endmodule
`default_nettype wire
