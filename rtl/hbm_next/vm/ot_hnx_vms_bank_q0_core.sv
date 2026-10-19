`timescale 1ns/1ps
`default_nettype none
// HBM-NEXT (hnx, 2026-10-19): fork of rtl/hbm_accel/generic/vm/static/faces_q0/ot_vms_bank_q0_faces_core.sv for the 2^19-word
// VM (A0 + A1 data macros, 17-bit sector).  Port widths +1 on every record (rq 18, wq/dq/kq 282, xq/xq2/eg 277, pq 286);
// clk_macro3 = the A1 macro's direct clock entry.  RG 5 / WG 2 / EG_WIDE 1 as the d4g SE/NE master.
module ot_hnx_vms_bank_q0_core #(parameter integer MUT = 0) (
    input wire [17:0] rq0,
    output wire [256:0] rr0,
    input wire [17:0] rq1,
    output wire [256:0] rr1,
    input wire [17:0] rq2,
    output wire [256:0] rr2,
    input wire [17:0] rq3,
    output wire [256:0] rr3,
    input wire [17:0] rq4,
    output wire [256:0] rr4,
    input wire [281:0] wq0,
    output wire wq_done0,
    input wire [281:0] wq1,
    output wire wq_done1,
    input wire [2:0] bid,
    input wire [1:0] sid,
    input wire clk, clk_n, clk_s, clk_e, clk_w, clk_macro0, clk_macro1, clk_macro2, clk_macro3,
    input wire rst_n,
    input wire rslot_v,
    input wire [2:0] rslot,
    input wire wslot_v,
    input wire [2:0] wslot,
    input wire [281:0] dq,
    output wire dq_done,
    input wire [281:0] kq,
    output wire kq_done,
    input wire [276:0] xq,
    output wire xq_done,
    input wire [276:0] xq2,
    output wire xq2_done,
    output wire [276:0] eg,
    input wire [285:0] pq,
    output wire [265:0] pr,
    output wire [17:0] status
);
 wire [1284:0] rr;wire [1:0] wq_done;
 assign rr0=rr[0+:257];
 assign rr1=rr[257+:257];
 assign rr2=rr[514+:257];
 assign rr3=rr[771+:257];
 assign rr4=rr[1028+:257];
 assign wq_done0=wq_done[0];
 assign wq_done1=wq_done[1];
 ot_hnx_vms_bank_q0_body #(.RG(5),.WG(2),.EG_WIDE(1),.MUT(MUT)) bank(
 .bid(bid),
 .sid(sid),
 .clk(clk), .clk_n(clk_n), .clk_s(clk_s), .clk_e(clk_e), .clk_w(clk_w),
 .clk_macro0(clk_macro0), .clk_macro1(clk_macro1), .clk_macro2(clk_macro2), .clk_macro3(clk_macro3),
 .rst_n(rst_n),
 .rslot_v(rslot_v),
 .rslot(rslot),
 .wslot_v(wslot_v),
 .wslot(wslot),
 .dq(dq),
 .dq_done(dq_done),
 .kq(kq),
 .kq_done(kq_done),
 .xq(xq),
 .xq_done(xq_done),
 .xq2(xq2),
 .xq2_done(xq2_done),
 .eg(eg),
 .pq(pq),
 .pr(pr),
 .status(status),
 .rq({rq4,rq3,rq2,rq1,rq0}),.rr(rr),
 .wq({wq1,wq0}),.wq_done(wq_done));
endmodule
`default_nettype wire
