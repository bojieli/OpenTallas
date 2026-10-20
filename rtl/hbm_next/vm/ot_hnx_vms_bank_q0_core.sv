`timescale 1ns/1ps
`default_nettype none
// HBM-NEXT (hnx, 2026-10-19): fork of rtl/hbm_accel/generic/vm/static/faces_q0/ot_vms_bank_q0_faces_core.sv for the 2^19-word
// VM (A0 + A1 data macros, 17-bit sector).  Port widths +1 on every record (rq 18, wq/dq/kq 282, xq/xq2/eg 277, pq 286);
// safe3 (10-20): SRAM clock pins on the core clk root with their launch/capture registers.  RG 5 / WG 2 / EG_WIDE 1 as the d4g SE/NE master.
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
    input wire clk, clk_n, clk_s, clk_e, clk_w,
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
    output wire [17:0] status,
    // safe3 census: replicated valid pin registers (10 kept copies each, from the faces wrapper)
    input wire [9:0] dq_vr, kq_vr, xq_vr, x2_vr, wq0_vr, wq1_vr, pq_vr, pq_wr
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
 .wq({wq1,wq0}),.wq_done(wq_done),
 .dq_vr(dq_vr),.kq_vr(kq_vr),.xq_vr(xq_vr),.x2_vr(x2_vr),.wq_vr({wq1_vr,wq0_vr}),.pq_vr(pq_vr),.pq_wr(pq_wr));
endmodule
`default_nettype wire
