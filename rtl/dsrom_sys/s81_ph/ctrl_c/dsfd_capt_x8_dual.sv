`timescale 1ns/1ps
// Structural half-column of capture CDC: independent core and serial clock roots.
// NR=8 preserves every root transaction and cycle; two leaves replace one NR=16
// without any data pipeline stage. Duplicate status crossing retains the original
// status latency in both halves; the parent observes the first half only.
module dsfd_capt_x8_dual (
    input wire [0:0] ck, rst, ckv, rsv,
    input wire [415:0] f_w,
    output wire [831:0] t_vm,
    output wire [0:0] t_ho,
    input wire [63:0] f_sn,
    output wire [63:0] t_st
);
    dsfd_capt_x #(.NR(8), .LD(4), .LOCAL_CTRL(1)) u_half
        (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_w(f_w),
         .t_vm(t_vm), .t_ho(t_ho), .f_sn(f_sn), .t_st(t_st));
endmodule
