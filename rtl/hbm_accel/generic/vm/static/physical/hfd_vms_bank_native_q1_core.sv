`timescale 1ns/1ps
`default_nettype none
// H-NETLIST 2230 (d4f, H-DIE): the SE/NE (q1/q3) VM bank for a CORE-ONLY hub (hfd_hgi_vms_static_{SE,NE}_core: no SM
// side in that quadrant).  The exact native q1 master hfd_vms_bank_native_q1 with its SM-side client ports ABSENT:
// HBM fill dq / dq_done, read groups 1 (DMA-back) and 2 (x-load) rq1/rr1/rq2/rr2, write group 1 (SM writer)
// wq1/wq_done1.  Their inputs are module-internal constants (the compiler calendar never schedules those slots; the
// constant cones fold away in synthesis), so the die binds no tied or open port.  Present ports keep the q1 names
// (rq0/rq3 = lg / coll read groups, wq0 = lg write group) so the slice group numbering is unchanged.
module hfd_vms_bank_native_q1_core(
    input wire [16:0] rq0,
    output wire [256:0] rr0,
    input wire [16:0] rq3,
    output wire [256:0] rr3,
    input wire [280:0] wq0,
    output wire wq_done0,
    input wire [2:0] bid,
    input wire [1:0] sid,
    input wire clk,
    input wire rst_n,
    input wire rslot_v,
    input wire [2:0] rslot,
    input wire wslot_v,
    input wire [2:0] wslot,
    input wire [280:0] kq,
    output wire kq_done,
    input wire [275:0] xq,
    output wire xq_done,
    input wire [275:0] xq2,
    output wire xq2_done,
    output wire [275:0] eg,
    input wire [284:0] pq,
    output wire [265:0] pr,
    output wire [17:0] status
);
    wire [256:0] rr1_abs, rr2_abs; wire wq_done1_abs, dq_done_abs;
    hfd_vms_bank_native_q1 u_bank(
        .rq0(rq0), .rr0(rr0), .rq1(17'd0), .rr1(rr1_abs), .rq2(17'd0), .rr2(rr2_abs), .rq3(rq3), .rr3(rr3),
        .wq0(wq0), .wq_done0(wq_done0), .wq1(281'd0), .wq_done1(wq_done1_abs),
        .bid(bid), .sid(sid), .clk(clk), .rst_n(rst_n), .rslot_v(rslot_v), .rslot(rslot), .wslot_v(wslot_v), .wslot(wslot),
        .dq(281'd0), .dq_done(dq_done_abs), .kq(kq), .kq_done(kq_done), .xq(xq), .xq_done(xq_done), .xq2(xq2), .xq2_done(xq2_done),
        .eg(eg), .pq(pq), .pr(pr), .status(status));
endmodule
`default_nettype wire
