`timescale 1ns/1ps
// CLAUDE S81-PH: die view top of the scan-service IO hub (sub-block of dsfd_svc at its N-E pin group; contract pin plan
// physical/s81_ph_views/ports/contract/dsfd_svc_io).  N face = the svc's die pins (q / od+of / xd+xf / ad+af / ck / rst);
// S face = the quadrant-side valid/ready ports.  Function: ot_s81ph_svc_io.sv.  Forwarded clocks = ck through kept
// inverters (the first station captures on negedge = posedge ck), as every r8/r9 glue block.
module dsfd_svc_io (
    input  wire [0:0]    ck,
    input  wire [0:0]    rst,
    input  wire [514:0]  q,
    output wire [513:0]  od,
    output wire [0:0]    of,
    output wire [513:0]  xd,
    output wire [0:0]    xf,
    output wire [1025:0] ad,
    output wire [0:0]    af,
    output wire [0:0]    fault,
    output wire [2059:0] q_q,
    input  wire [3:0]    od_v,
    input  wire [2047:0] od_d,
    output wire [3:0]    od_r,
    input  wire [3:0]    a0_v,
    input  wire [2047:0] a0_d,
    output wire [3:0]    a0_r,
    input  wire [0:0]    a1_v,
    input  wire [511:0]  a1_d,
    output wire [0:0]    a1_r,
    input  wire [0:0]    x_v,
    input  wire [511:0]  x_d,
    output wire [0:0]    x_r
);
    reg [1:0] rst_s;                         // rst_s[1]: the margin SDC's rst_mcp2 cell name
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire [513:0] od_i, xd_i; wire [1025:0] ad_i; wire [2059:0] qq_i; wire f_i;
    ot_s81ph_svc_io #(.NQ(4), .SYNC(0)) u_io (.ck(ck[0]), .rst(rst_s[1]), .q(q), .od(od_i), .xd(xd_i), .ad(ad_i), .fault(f_i), .q_q(qq_i),
        .od_v(od_v), .od_d(od_d), .od_r(od_r), .a0_v(a0_v), .a0_d(a0_d), .a0_r(a0_r), .a1_v(a1_v[0]), .a1_d(a1_d), .a1_r(a1_r[0]),
        .x_v(x_v[0]), .x_d(x_d), .x_r(x_r[0]));
    assign od = od_i; assign xd = xd_i; assign ad = ad_i; assign q_q = qq_i; assign fault = f_i;
    ot_fwd_clk_inv u_of (.a(ck[0]), .y(of[0]));
    ot_fwd_clk_inv u_xf (.a(ck[0]), .y(xf[0]));
    ot_fwd_clk_inv u_af (.a(ck[0]), .y(af[0]));
endmodule
