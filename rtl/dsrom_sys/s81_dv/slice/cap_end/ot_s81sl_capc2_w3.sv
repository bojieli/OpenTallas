`timescale 1ns/1ps
`default_nettype none
// S81/PORTFIX-DEAD D-CAPEND (2026-10-25): ot_s81sl_capc2_w3 = ot_s81sl_capc2 (cap_p1 PINPIPE 1 around ot_s81sl_cap #(24, 16))
// for the 3-frame row-end slices on ot_s81sl_slice (die s_3N sukv_raw512, s_3S slice_iq): rt_w 210 b (lanes 0..2), no rt_e
// (the as-built die tied lanes 3..7 = 0).  Core = ot_s81sl_cap_w3 (tools/s81_slice/cap_end/cap_end_eq.sh: every edge equal to
// ot_s81sl_cap with those lanes 0); the boundary pipeline is ot_s81sl_cap_p1's PINPIPE 1 verbatim minus the E pin register.
// Parameter-free release top (hard view: kit s81sl_capc2_w3, children s81sl_cap_tr3 + s81sl_cap_rt_w).
module ot_s81sl_capc2_w3 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [209:0]  rt_w,
    input  wire          cfg_v,
    input  wire [159:0]  cfg_d,
    output wire [5:0]    cw_s_v,
    output wire [71:0]   cw_s_a,
    output wire [191:0]  cw_s_d,
    output wire [3:0]    cw_n_v,
    output wire [47:0]   cw_n_a,
    output wire [127:0]  cw_n_d,
    output wire          fault
);
    wire [5:0] sv; wire [71:0] sa; wire [191:0] sd;
    wire [3:0] nv; wire [47:0] na; wire [127:0] nd; wire fl;
    (* async_reg="true", keep="true", dont_touch="true" *) reg rst_l0, rst_l1;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rst_l0 <= 0; rst_l1 <= 0; end
        else begin rst_l0 <= 1; rst_l1 <= rst_l0; end
    (* keep="true" *) reg [209:0] wq;
    (* keep="true" *) reg cvq; (* keep="true" *) reg [159:0] cdq;
    always @(posedge clk) begin wq <= rt_w; cvq <= cfg_v; cdq <= cfg_d; end
    (* keep="true" *) reg [5:0] svq; (* keep="true" *) reg [3:0] nvq; (* keep="true" *) reg fq;
    (* keep="true" *) reg [71:0] saq; (* keep="true" *) reg [191:0] sdq;
    (* keep="true" *) reg [47:0] naq; (* keep="true" *) reg [127:0] ndq;
    always @(posedge clk) begin saq <= sa; sdq <= sd; naq <= na; ndq <= nd; end
    always @(posedge clk or negedge rst_l1)
        if (!rst_l1) begin svq <= 0; nvq <= 0; fq <= 0; end
        else begin svq <= sv; nvq <= nv; fq <= fl; end
    assign cw_s_v = svq; assign cw_n_v = nvq;
    assign cw_s_a = saq; assign cw_s_d = sdq; assign cw_n_a = naq; assign cw_n_d = ndq; assign fault = fq;
    ot_s81sl_cap_w3 u_core (.clk(clk), .rst_n(rst_l1), .rt_w(wq), .cfg_v(cvq), .cfg_d(cdq),
        .cw_s_v(sv), .cw_s_a(sa), .cw_s_d(sd), .cw_n_v(nv), .cw_n_a(na), .cw_n_d(nd), .fault(fl));
endmodule
`default_nettype wire
