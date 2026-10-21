// QKO-HROOT2 10-21: the split ingest_qm (CDC shell qkd_hr_ingest_cdc_shell + engine tile qkd_hr_ingest_eng, behavioural
// engine via QKD_HR_ENG_RTL) behind the qkd_hr_native_qm_cdc port list, for the cycle-exact miter tb_qm_split_equiv.
`timescale 1ns/1ps
module qkd_hr_qm_split_pair #(parameter integer AW=32, HDMAX=128, KVHMAX=2, RMW_EN=0, MUT=0, NATIVE_ROWS=1, QPIPE=2, HFA=4) (
    input wire rst_n, clk_h, h_v, input wire [1:0] h_cls, input wire [511:0] h_d, output wire [HFA:0] h_crn,
    output wire t_v, output wire [63:0] t_d, input wire t_cr, input wire clk_i, input wire [1:0] clk_i_bank, input wire clk_i_out,
    input wire ck, output wire o_v, o_we, output wire [AW-1:0] o_addr, output wire [255:0] o_d, input wire o_cr, i_rv,
    input wire [255:0] i_rd, output wire fault, quiet_h, quiet_i, quiet_c);
    localparam integer KW = 20;
    wire [1:0] e_rst_n; wire e_dv, e_inv_a, e_inv_b, e_wrdy, e_drdy, e_inrdy, e_wv, e_rv, e_done, e_done_a, e_done_b, e_done_c, e_busy;
    wire [255:0] e_ddata, e_wdata; wire [511:0] e_indata; wire [KW-1:0] e_wv_c; wire [31:0] e_waddr, e_raddr, e_nsec; wire [7:0] e_tag;
    qkd_hr_ingest_cdc_shell #(.AW(AW), .HDMAX(HDMAX), .KVHMAX(KVHMAX), .RMW_EN(RMW_EN), .MUT(MUT), .NATIVE_ROWS(NATIVE_ROWS),
        .QPIPE(QPIPE), .KW(KW)) u_qm (
        .rst_n(rst_n), .clk_h(clk_h), .h_v(h_v), .h_cls(h_cls), .h_d(h_d), .h_crn(h_crn), .t_v(t_v), .t_d(t_d), .t_cr(t_cr),
        .clk_i(clk_i), .e_rst_n(e_rst_n), .e_dv(e_dv), .e_ddata(e_ddata), .e_inv_a(e_inv_a), .e_inv_b(e_inv_b), .e_indata(e_indata),
        .e_wrdy_o(e_wrdy), .e_drdy(e_drdy), .e_inrdy(e_inrdy), .e_wv(e_wv), .e_wv_c(e_wv_c), .e_waddr(e_waddr), .e_wdata(e_wdata),
        .e_rv(e_rv), .e_raddr(e_raddr), .e_done(e_done), .e_done_a(e_done_a), .e_done_b(e_done_b), .e_done_c(e_done_c), .e_tag(e_tag), .e_busy(e_busy),
        .e_nsec(e_nsec), .ck(ck), .o_v(o_v), .o_we(o_we), .o_addr(o_addr), .o_d(o_d), .o_cr(o_cr), .i_rv(i_rv), .i_rd(i_rd),
        .fault(fault), .quiet_h(quiet_h), .quiet_i(quiet_i), .quiet_c(quiet_c));
    qkd_hr_ingest_eng #(.KW(KW)) u_eng (.ck_ingest(clk_i), .ck_rl(clk_i), .eng_rst_n(e_rst_n), .eng_dv(e_dv), .eng_ddata(e_ddata),
        .eng_inv_a(e_inv_a), .eng_inv_b(e_inv_b), .eng_indata(e_indata), .eng_wrdy(e_wrdy), .eng_drdy(e_drdy), .eng_inrdy(e_inrdy),
        .eng_wv(e_wv), .eng_wv_c(e_wv_c), .eng_waddr(e_waddr), .eng_wdata(e_wdata), .eng_rv(e_rv), .eng_raddr(e_raddr),
        .eng_done(e_done), .eng_done_a(e_done_a), .eng_done_b(e_done_b), .eng_done_c(e_done_c), .eng_tag(e_tag), .eng_busy(e_busy), .eng_nsec(e_nsec));
endmodule
