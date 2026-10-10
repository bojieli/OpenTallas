`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// dsfd_mtp_seq_rtt: the native-binding successor of dsfd_mtp_seq (Claude mtp-wfc, 2026-10-10).
// dsfd_mtp_seq (pinned, unchanged) receives on three grant links with ot_dsrom_mtp_lrx, whose grant history is
// fixed at three cycles (infl = rdy + r1 + r2, D = 4): it is exact only with no relay stations between the sender
// and the receiver.  On the regenerated head631 floorplan the native buses run through registered relay stations
// (results/rtl/mtp_takeover_20261010/head631_native_binding_verified.json):
//     RESULT        capture -> mtp  5 stations, grant mtp -> capture 6        (u_r, 512 b)
//     rows / draft  vm -> mtp       9 stations, grant mtp -> vm      10       (u_w 10 b, u_q 34 b)
// Every receiver here is ot_dsrom_mtp_lrx_rtt (ENABLE_RTT) sized for its own round trip: grant history
// H = F + R + 3 and FIFO depth D = H + 1 (full rate).  The senders (ot_dsrom_mtp_ltx) are unchanged: their
// receivers sit on the collective / VM side and carry their own RTT sizing.
// Ports, pin names and the sequencer core are identical to dsfd_mtp_seq.  The relays add RF / VF forward cycles
// (wire, priced in the head631 chain model); the seq core's cycle count is unchanged.
// ---------------------------------------------------------------------------
module dsfd_mtp_seq_rtt #(
    parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10,
    parameter integer MAXU = 8, parameter integer G = 5,
    parameter integer SW = USER_W + 3 * NW + 4, parameter integer DW = USER_W + 3 + NW,
    parameter integer RF = 5, parameter integer RR = 6,      // RESULT forward / grant-return relay stations
    parameter integer VF = 9, parameter integer VR = 10,     // rows-ready + draft-result forward / return
    parameter bit OUTPUT_PIPE_R = 0                          // optional elastic output slice on the wide receiver
) (
    input  wire [0:0]        ck,
    input  wire [0:0]        rst,
    input  wire [2*NW-1:0]   f_cfg,
    input  wire [0:0]        f_rv,  input  wire [FLIT-1:0] f_rd,  output wire [0:0] t_rg,   // RESULT in
    output wire [0:0]        t_tv,  output wire [FLIT-1:0] t_td,  input  wire [0:0] f_tg,   // token return out
    output wire [0:0]        t_sv,  output wire [SW-1:0]   t_sd,  input  wire [0:0] f_sg,   // seed out
    input  wire [0:0]        f_wv,  input  wire [USER_W-1:0] f_wd, output wire [0:0] t_wg,  // rows ready in
    output wire [0:0]        t_hv,  output wire [DW-1:0]   t_hd,  input  wire [0:0] f_hg,   // draft-head step out
    input  wire [0:0]        f_qv,  input  wire [DW-1:0]   f_qd,  output wire [0:0] t_qg,   // draft-head result in
    output wire [2*NW+USER_W+4:0] t_acc
);
    localparam integer DR = RF + RR + 4, DV = VF + VR + 4;
    wire clk = ck[0];
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn));
    reg [2*NW-1:0] cfg_q; always @(posedge clk) cfg_q <= f_cfg;
    wire rv, rr; wire [FLIT-1:0] rd;
    ot_dsrom_mtp_lrx_rtt #(.W(FLIT), .D(DR), .ENABLE_RTT(1), .OUTPUT_PIPE(OUTPUT_PIPE_R),
        .FORWARD_HOPS(RF), .RETURN_HOPS(RR)) u_r (.clk(clk), .rst_n(rn),
        .l_valid(f_rv[0]), .l_ready(t_rg[0]), .l_data(f_rd), .c_valid(rv), .c_ready(rr), .c_data(rd));
    wire tv, tr; wire [FLIT-1:0] td;
    ot_dsrom_mtp_ltx #(.W(FLIT)) u_t (.clk(clk), .rst_n(rn), .c_valid(tv), .c_ready(tr), .c_data(td),
        .l_valid(t_tv[0]), .l_ready(f_tg[0]), .l_data(t_td));
    wire sv, sr; wire [SW-1:0] sd;
    ot_dsrom_mtp_ltx #(.W(SW)) u_s (.clk(clk), .rst_n(rn), .c_valid(sv), .c_ready(sr), .c_data(sd),
        .l_valid(t_sv[0]), .l_ready(f_sg[0]), .l_data(t_sd));
    wire wv, wr; wire [USER_W-1:0] wd;
    ot_dsrom_mtp_lrx_rtt #(.W(USER_W), .D(DV), .ENABLE_RTT(1), .FORWARD_HOPS(VF), .RETURN_HOPS(VR)) u_w (
        .clk(clk), .rst_n(rn), .l_valid(f_wv[0]), .l_ready(t_wg[0]), .l_data(f_wd),
        .c_valid(wv), .c_ready(wr), .c_data(wd));
    wire hv, hr; wire [DW-1:0] hd;
    ot_dsrom_mtp_ltx #(.W(DW)) u_h (.clk(clk), .rst_n(rn), .c_valid(hv), .c_ready(hr), .c_data(hd),
        .l_valid(t_hv[0]), .l_ready(f_hg[0]), .l_data(t_hd));
    wire qv, qr; wire [DW-1:0] qd;
    ot_dsrom_mtp_lrx_rtt #(.W(DW), .D(DV), .ENABLE_RTT(1), .FORWARD_HOPS(VF), .RETURN_HOPS(VR)) u_q (
        .clk(clk), .rst_n(rn), .l_valid(f_qv[0]), .l_ready(t_qg[0]), .l_data(f_qd),
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
