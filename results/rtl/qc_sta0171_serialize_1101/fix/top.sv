module top (input wire ck, input wire rst_n, input wire [7:0] re, input wire [191:0] addr,
    input wire [7:0] vm_we, input wire [191:0] vm_waddr, input wire [255:0] vm_wdata,
    input wire w16_we, input wire [23:0] w16_addr, input wire [511:0] w16_data,
    input wire w1_we, input wire [23:0] w1_addr, input wire [31:0] w1_data,
    input wire tw_we, input wire [1:0] tw_kind, input wire [23:0] tw_addr, input wire [511:0] tw_d,
    output wire [255:0] q_v, output wire [255:0] q_c0, output wire [255:0] q_c1, output wire [2:0] fault);
  // parent form of qfd_dv_s8_vm8q_rp1: .MIF(MIF) / .MUT(MUT) elaborate to numeric overrides on the signed masters
  qfd_dv_s8x_vmr #(.MUT(0), .MIF(0)) u_va (.ck(ck), .rst_n(rst_n), .re(re), .addr(addr), .q(q_v), .vm_we(vm_we),
    .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data),
    .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(fault[0]), .ft_ck_i(ck), .ft_ck_o(), .ft_rst_i(rst_n), .ft_rst_o());
  qfd_dv_s8_crh_rp1 #(.MIF(0)) u_cl (.ck(ck), .rst_n(rst_n), .cr_re(re), .cr_addr(addr), .q(q_c0), .tw_we(tw_we),
    .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_d(tw_d), .fault(fault[1]), .ft_ck_i(ck), .ft_ck_o(), .ft_rst_i(rst_n), .ft_rst_o());
  qfd_dv_s8_crh_rp1 u_ch (.ck(ck), .rst_n(rst_n), .cr_re(re), .cr_addr(addr), .q(q_c1), .tw_we(tw_we),
    .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_d(tw_d), .fault(fault[2]), .ft_ck_i(ck), .ft_ck_o(), .ft_rst_i(rst_n), .ft_rst_o());
endmodule
