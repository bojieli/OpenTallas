`default_nettype none
// GENERATED (gen_svc_seg.py): the SE segments joined with the ports of hfd_svc_SE (bench vehicle)
module hfd_svc_SE_seg (
    input wire [0:0] ck,
    input wire [128:0] e,
    output wire [1025:0] ik,
    input wire [1:0] kc0,
    input wire [1:0] kc1,
    input wire [1:0] kc2,
    input wire [1:0] kc3,
    input wire [1:0] kc4,
    input wire [1:0] kc5,
    input wire [1:0] kc6,
    input wire [1:0] kc7,
    output wire [1:0] kd,
    input wire [1:0] kq0,
    input wire [1:0] kq1,
    input wire [1:0] kq2,
    input wire [1:0] kq3,
    input wire [1:0] kq4,
    input wire [1:0] kq5,
    input wire [1:0] kq6,
    input wire [1:0] kq7,
    output wire [1101:0] ks0,
    output wire [1101:0] ks1,
    output wire [1101:0] ks2,
    output wire [1101:0] ks3,
    output wire [1101:0] ks4,
    output wire [1101:0] ks5,
    output wire [1101:0] ks6,
    output wire [1101:0] ks7,
    output wire [1040:0] kv,
    input wire [350:0] lq,
    output wire [293:0] lr,
    output wire [1098:0] lsm10,
    output wire [1098:0] lsm11,
    output wire [1101:0] lsm12,
    output wire [1101:0] lsm13,
    output wire [1101:0] lsm14,
    output wire [1101:0] lsm15,
    output wire [1098:0] lsm8,
    output wire [1098:0] lsm9,
    inout wire [22237:0] phy,
    inout wire [43:0] qsm10,
    inout wire [43:0] qsm11,
    input wire [44:0] qsm12,
    input wire [44:0] qsm13,
    input wire [44:0] qsm14,
    input wire [44:0] qsm15,
    inout wire [43:0] qsm8,
    inout wire [43:0] qsm9,
    input wire [0:0] rst
);
  wire [751:0] xr0;
  wire [1442:0] xl0;
  wire [1565:0] xr1;
  wire [1220:0] xl1;
  wire [1293:0] xr2;
  wire [1232:0] xl2;
  wire [1205:0] xr3;
  wire [708:0] xl3;
  wire [919:0] xr4;
  wire [706:0] xl4;
  wire [633:0] xr5;
  wire [704:0] xl5;
  wire [803:0] xr6;
  wire [202:0] xl6;
  wire [293:0] xr7;
  wire [424:0] xl7;
  hfd_svc_SE_s0 u_s0 (.l0(lsm12), .q0(qsm12), .l1(lsm8), .q1(qsm8), .ks0(ks0), .ks1(ks1), .kq0(kq0), .kq1(kq1), .kc0(kc0), .kc1(kc1), .phy(phy[3625:0]), .ck(ck), .rst(rst), .eo(xr0), .ei(xl0));
  hfd_svc_SE_s1 u_s1 (.l2(lsm13), .q2(qsm13), .ks2(ks2), .kq2(kq2), .kc2(kc2), .phy(phy[7831:3626]), .ck(ck), .rst(rst), .wi(xr0), .wo(xl0), .eo(xr1), .ei(xl1));
  hfd_svc_SE_s2 u_s2 (.l3(lsm9), .q3(qsm9), .ks3(ks3), .kq3(kq3), .kc3(kc3), .phy(phy[10319:7832]), .ck(ck), .rst(rst), .wi(xr1), .wo(xl1), .eo(xr2), .ei(xl2));
  hfd_svc_SE_s3 u_s3 (.kv(kv), .l4(lsm14), .q4(qsm14), .ik(ik), .e(e), .ks4(ks4), .kq4(kq4), .kd(kd), .kc4(kc4), .lq(lq), .lr(lr), .phy(phy[13529:10320]), .ck(ck), .rst(rst), .wi(xr2), .wo(xl2), .eo(xr3), .ei(xl3));
  hfd_svc_SE_s4 u_s4 (.l5(lsm10), .q5(qsm10), .ks5(ks5), .kq5(kq5), .kc5(kc5), .phy(phy[16017:13530]), .ck(ck), .rst(rst), .wi(xr3), .wo(xl3), .eo(xr4), .ei(xl4));
  hfd_svc_SE_s5 u_s5 (.l6(lsm15), .q6(qsm15), .ks6(ks6), .kq6(kq6), .kc6(kc6), .phy(phy[18505:16018]), .ck(ck), .rst(rst), .wi(xr4), .wo(xl4), .eo(xr5), .ei(xl5));
  hfd_svc_SE_s6 u_s6 (.phy(phy[20371:18506]), .ck(ck), .rst(rst), .wi(xr5), .wo(xl5), .eo(xr6), .ei(xl6));
  hfd_svc_SE_s7 u_s7 (.l7(lsm11), .q7(qsm11), .ks7(ks7), .kq7(kq7), .kc7(kc7), .phy(phy[21615:20372]), .ck(ck), .rst(rst), .wi(xr6), .wo(xl6), .eo(xr7), .ei(xl7));
  hfd_svc_SE_s8 u_s8 (.phy(phy[22237:21616]), .ck(ck), .rst(rst), .wi(xr7), .wo(xl7));
endmodule
`default_nettype wire
