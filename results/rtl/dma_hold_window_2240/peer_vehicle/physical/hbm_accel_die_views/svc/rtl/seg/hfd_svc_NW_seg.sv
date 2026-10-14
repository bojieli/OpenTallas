`default_nettype none
// GENERATED (gen_svc_seg.py): the SW segments joined with the ports of hfd_svc_NW (bench vehicle)
module hfd_svc_NW_seg (
    input wire [0:0] ck,
    input wire [128:0] e,
    output wire [1025:0] ik,
    output wire [1040:0] kv,
    output wire [1098:0] lsm16,
    output wire [1098:0] lsm17,
    output wire [1098:0] lsm18,
    output wire [1098:0] lsm19,
    output wire [1101:0] lsm20,
    output wire [1101:0] lsm21,
    output wire [1101:0] lsm22,
    output wire [1101:0] lsm23,
    inout wire [22237:0] phy,
    inout wire [43:0] qsm16,
    inout wire [43:0] qsm17,
    inout wire [43:0] qsm18,
    inout wire [43:0] qsm19,
    input wire [44:0] qsm20,
    input wire [44:0] qsm21,
    input wire [44:0] qsm22,
    input wire [44:0] qsm23,
    input wire [0:0] rst
);
  wire [596:0] xr0;
  wire [1174:0] xl0;
  wire [1416:0] xr1;
  wire [979:0] xl1;
  wire [1144:0] xr2;
  wire [1018:0] xl2;
  wire [866:0] xr3;
  wire [893:0] xl3;
  wire [815:0] xr4;
  wire [5:0] xl4;
  wire [543:0] xr5;
  wire [3:0] xl5;
  wire [271:0] xr6;
  wire [1:0] xl6;
  hfd_svc_SW_s0 u_s0 (.l0(lsm20), .q0(qsm20), .l1(lsm16), .q1(qsm16), .phy(phy[3625:0]), .ck(ck), .rst(rst), .eo(xr0), .ei(xl0));
  hfd_svc_SW_s1 u_s1 (.kv(kv), .l2(lsm21), .q2(qsm21), .ik(ik), .phy(phy[7831:3626]), .ck(ck), .rst(rst), .wi(xr0), .wo(xl0), .eo(xr1), .ei(xl1));
  hfd_svc_SW_s2 u_s2 (.l3(lsm17), .q3(qsm17), .phy(phy[10319:7832]), .ck(ck), .rst(rst), .wi(xr1), .wo(xl1), .eo(xr2), .ei(xl2));
  hfd_svc_SW_s3 u_s3 (.l4(lsm22), .q4(qsm22), .e(e), .phy(phy[12907:10320]), .ck(ck), .rst(rst), .wi(xr2), .wo(xl2), .eo(xr3), .ei(xl3));
  hfd_svc_SW_s4 u_s4 (.phy(phy[14773:12908]), .ck(ck), .rst(rst), .wi(xr3), .wo(xl3), .eo(xr4), .ei(xl4));
  hfd_svc_SW_s5 u_s5 (.l5(lsm18), .q5(qsm18), .phy(phy[17261:14774]), .ck(ck), .rst(rst), .wi(xr4), .wo(xl4), .eo(xr5), .ei(xl5));
  hfd_svc_SW_s6 u_s6 (.l6(lsm23), .q6(qsm23), .phy(phy[19749:17262]), .ck(ck), .rst(rst), .wi(xr5), .wo(xl5), .eo(xr6), .ei(xl6));
  hfd_svc_SW_s7 u_s7 (.l7(lsm19), .q7(qsm19), .ck(ck), .rst(rst), .phy(phy[22237:19750]), .wi(xr6), .wo(xl6));
endmodule
`default_nettype wire
