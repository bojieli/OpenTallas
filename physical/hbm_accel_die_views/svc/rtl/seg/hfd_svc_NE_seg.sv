`default_nettype none
// GENERATED (gen_svc_seg.py): the SE segments joined with the ports of hfd_svc_NE (bench vehicle)
module hfd_svc_NE_seg (
    input wire [0:0] ck,
    input wire [128:0] e,
    output wire [1025:0] ik,
    output wire [1040:0] kv,
    output wire [1098:0] lsm24,
    output wire [1098:0] lsm25,
    output wire [1098:0] lsm26,
    output wire [1098:0] lsm27,
    output wire [1101:0] lsm28,
    output wire [1101:0] lsm29,
    output wire [1101:0] lsm30,
    output wire [1101:0] lsm31,
    inout wire [22237:0] phy,
    inout wire [43:0] qsm24,
    inout wire [43:0] qsm25,
    inout wire [43:0] qsm26,
    inout wire [43:0] qsm27,
    input wire [44:0] qsm28,
    input wire [44:0] qsm29,
    input wire [44:0] qsm30,
    input wire [44:0] qsm31,
    input wire [0:0] rst
);
  wire [596:0] xr0;
  wire [1174:0] xl0;
  wire [1412:0] xr1;
  wire [938:0] xl1;
  wire [1140:0] xr2;
  wire [936:0] xl2;
  wire [919:0] xr3;
  wire [561:0] xl3;
  wire [647:0] xr4;
  wire [559:0] xl4;
  wire [375:0] xr5;
  wire [557:0] xl5;
  wire [549:0] xr6;
  wire [53:0] xl6;
  hfd_svc_SE_s0 u_s0 (.ck(ck), .rst(rst), .l0(lsm28), .q0(qsm28), .l1(lsm24), .q1(qsm24), .phy(phy[3625:0]), .eo(xr0), .ei(xl0));
  hfd_svc_SE_s1 u_s1 (.l2(lsm29), .q2(qsm29), .phy(phy[7831:3626]), .ck(ck), .rst(rst), .wi(xr0), .wo(xl0), .eo(xr1), .ei(xl1));
  hfd_svc_SE_s2 u_s2 (.l3(lsm25), .q3(qsm25), .phy(phy[10319:7832]), .ck(ck), .rst(rst), .wi(xr1), .wo(xl1), .eo(xr2), .ei(xl2));
  hfd_svc_SE_s3 u_s3 (.kv(kv), .l4(lsm30), .q4(qsm30), .ik(ik), .e(e), .phy(phy[13529:10320]), .ck(ck), .rst(rst), .wi(xr2), .wo(xl2), .eo(xr3), .ei(xl3));
  hfd_svc_SE_s4 u_s4 (.l5(lsm26), .q5(qsm26), .phy(phy[16017:13530]), .ck(ck), .rst(rst), .wi(xr3), .wo(xl3), .eo(xr4), .ei(xl4));
  hfd_svc_SE_s5 u_s5 (.l6(lsm31), .q6(qsm31), .phy(phy[18505:16018]), .ck(ck), .rst(rst), .wi(xr4), .wo(xl4), .eo(xr5), .ei(xl5));
  hfd_svc_SE_s6 u_s6 (.phy(phy[20371:18506]), .ck(ck), .rst(rst), .wi(xr5), .wo(xl5), .eo(xr6), .ei(xl6));
  hfd_svc_SE_s7 u_s7 (.l7(lsm27), .q7(qsm27), .phy(phy[22237:20372]), .ck(ck), .rst(rst), .wi(xr6), .wo(xl6));
endmodule
`default_nettype wire
