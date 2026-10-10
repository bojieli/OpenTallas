`timescale 1ns/1ps
// Die master dsfd_mtp_seq, RTT successor (mtp-head-1010): the S81 view flow routes a block under its die master name
// (physical/s81_ph_views/ports/contract/dsfd_mtp_seq). This file replaces dsfd_mtp_tops.sv for that route only;
// the function is dsfd_mtp_seq_rtt (rtl/dsrom_sys/mtp/dsfd_mtp_seq_rtt.sv), same pins.
// reset synchroniser, identical to dsfd_mtp_tops.sv (that file is not in this route)
module ot_dsrom_mtp_rstsync (input wire clk, input wire rst_n_async, output wire rst_n);
    reg [1:0] s;
    always @(posedge clk or negedge rst_n_async) if (!rst_n_async) s <= 2'b00; else s <= {s[0], 1'b1};
    assign rst_n = s[1];
endmodule

module dsfd_mtp_seq #(
    parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10,
    parameter integer MAXU = 8, parameter integer G = 5,
    parameter integer SW = USER_W + 3 * NW + 4, parameter integer DW = USER_W + 3 + NW
) (
    input  wire [0:0]        ck,
    input  wire [0:0]        rst,
    input  wire [2*NW-1:0]   f_cfg,          // {glen, plen} (static)
    input  wire [0:0]        f_rv,  input  wire [FLIT-1:0] f_rd,  output wire [0:0] t_rg,   // RESULT in
    output wire [0:0]        t_tv,  output wire [FLIT-1:0] t_td,  input  wire [0:0] f_tg,   // token return out
    output wire [0:0]        t_sv,  output wire [SW-1:0]   t_sd,  input  wire [0:0] f_sg,   // seed out
    input  wire [0:0]        f_wv,  input  wire [USER_W-1:0] f_wd, output wire [0:0] t_wg,  // rows ready in
    output wire [0:0]        t_hv,  output wire [DW-1:0]   t_hd,  input  wire [0:0] f_hg,   // draft-head step out
    input  wire [0:0]        f_qv,  input  wire [DW-1:0]   f_qd,  output wire [0:0] t_qg,   // draft-head result in
    output wire [2*NW+USER_W+4:0] t_acc      // {fault, acc_v, acc_u, acc_a, acc_c, acc_y} (from flops)
);
    dsfd_mtp_seq_rtt #(.FLIT(FLIT), .NW(NW), .USER_W(USER_W), .MAXU(MAXU), .G(G)) u (.ck(ck), .rst(rst), .f_cfg(f_cfg), .f_rv(f_rv), .f_rd(f_rd), .t_rg(t_rg), .t_tv(t_tv), .t_td(t_td), .f_tg(f_tg), .t_sv(t_sv), .t_sd(t_sd), .f_sg(f_sg), .f_wv(f_wv), .f_wd(f_wd), .t_wg(t_wg), .t_hv(t_hv), .t_hd(t_hd), .f_hg(f_hg), .f_qv(f_qv), .f_qd(f_qd), .t_qg(t_qg), .t_acc(t_acc));
endmodule
