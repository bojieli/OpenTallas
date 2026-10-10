`timescale 1ns/1ps
// dsfd_mtp_seq_rtt (mtp-head-1010, 2026-10-10): dsfd_mtp_seq (rtl/dsrom_sys/mtp/dsfd_mtp_tops.sv, CLOSED c67a71fe5,
// unchanged) with its three grant RECEIVERS (RESULT u_r, rows-ready u_w, draft-head result u_q) replaced by the
// RTT-aware receiver ot_dsrom_mtp_lrx_rtt sized to the head die's actual registered relay chains. The legacy
// receiver reserves a 3-cycle grant history; on the 5+6 / 9+10 station chains it grants flits that arrive after the
// history expired and overflows (Codex physical/mtp_link_rtt/native_legacy_failure). Same function, same ports,
// same transmitters; only receive depth / grant accounting change (0 added cycles at the pin, full rate).
module dsfd_mtp_seq_rtt #(
    parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10,
    parameter integer MAXU = 8, parameter integer G = 5,
    parameter integer SW = USER_W + 3 * NW + 4, parameter integer DW = USER_W + 3 + NW,
    // actual registered relay stations of the head-die chains (head631 / headp2 regenerated, ef227c660):
    //   capture -> mtp 5 (data) / mtp -> capture 6 (grant); vm -> mtp 9 (data) / mtp -> vm 10 (grant)
    parameter integer FWD_R = 5, parameter integer RET_R = 6, parameter integer FWD_V = 9, parameter integer RET_V = 10,
    // full-rate depth: one slot per grant of the round trip (history F + R + 3) plus one
    parameter integer D_R = FWD_R + RET_R + 4, parameter integer D_V = FWD_V + RET_V + 4
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
    wire clk = ck[0];
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn));
    reg [2*NW-1:0] cfg_q; always @(posedge clk) cfg_q <= f_cfg;
    wire rv, rr; wire [FLIT-1:0] rd;
    ot_dsrom_mtp_lrx_rtt #(.W(FLIT), .D(D_R), .ENABLE_RTT(1), .FORWARD_HOPS(FWD_R), .RETURN_HOPS(RET_R)) u_r (.clk(clk), .rst_n(rn), .l_valid(f_rv[0]), .l_ready(t_rg[0]), .l_data(f_rd),
        .c_valid(rv), .c_ready(rr), .c_data(rd));
    wire tv, tr; wire [FLIT-1:0] td;
    ot_dsrom_mtp_ltx #(.W(FLIT)) u_t (.clk(clk), .rst_n(rn), .c_valid(tv), .c_ready(tr), .c_data(td),
        .l_valid(t_tv[0]), .l_ready(f_tg[0]), .l_data(t_td));
    wire sv, sr; wire [SW-1:0] sd;
    ot_dsrom_mtp_ltx #(.W(SW)) u_s (.clk(clk), .rst_n(rn), .c_valid(sv), .c_ready(sr), .c_data(sd),
        .l_valid(t_sv[0]), .l_ready(f_sg[0]), .l_data(t_sd));
    wire wv, wr; wire [USER_W-1:0] wd;
    ot_dsrom_mtp_lrx_rtt #(.W(USER_W), .D(D_V), .ENABLE_RTT(1), .FORWARD_HOPS(FWD_V), .RETURN_HOPS(RET_V)) u_w (.clk(clk), .rst_n(rn), .l_valid(f_wv[0]), .l_ready(t_wg[0]), .l_data(f_wd),
        .c_valid(wv), .c_ready(wr), .c_data(wd));
    wire hv, hr; wire [DW-1:0] hd;
    ot_dsrom_mtp_ltx #(.W(DW)) u_h (.clk(clk), .rst_n(rn), .c_valid(hv), .c_ready(hr), .c_data(hd),
        .l_valid(t_hv[0]), .l_ready(f_hg[0]), .l_data(t_hd));
    wire qv, qr; wire [DW-1:0] qd;
    ot_dsrom_mtp_lrx_rtt #(.W(DW), .D(D_V), .ENABLE_RTT(1), .FORWARD_HOPS(FWD_V), .RETURN_HOPS(RET_V)) u_q (.clk(clk), .rst_n(rn), .l_valid(f_qv[0]), .l_ready(t_qg[0]), .l_data(f_qd),
        .c_valid(qv), .c_ready(qr), .c_data(qd));
    wire av, fl; wire [USER_W-1:0] au; wire [2:0] aa; wire [NW-1:0] ac, ay;
    ot_dsrom_mtp_seq #(.FLIT(FLIT), .NW(NW), .USER_W(USER_W), .MAXU(MAXU), .G(G)) u_seq (
        .clk(clk), .rst_n(rn), .cfg_plen(cfg_q[NW-1:0]), .cfg_glen(cfg_q[2*NW-1:NW]),
        .r_valid(rv), .r_ready(rr), .r_data(rd), .t_valid(tv), .t_ready(tr), .t_data(td),
        .s_valid(sv), .s_ready(sr), .s_data(sd), .w_valid(wv), .w_ready(wr), .w_user(wd),
        .h_valid(hv), .h_ready(hr), .h_data(hd), .q_valid(qv), .q_ready(qr), .q_data(qd),
        .acc_v(av), .acc_u(au), .acc_a(aa), .acc_c(ac), .acc_y(ay), .fault(fl));
    reg [2*NW+USER_W+4:0] acc_q; always @(posedge clk) acc_q <= {fl, av, au, aa, ac, ay};
    assign t_acc = acc_q;
endmodule
