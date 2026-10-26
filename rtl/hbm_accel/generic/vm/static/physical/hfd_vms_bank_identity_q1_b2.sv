`timescale 1ns/1ps
`default_nettype none
// Literal physical ABI, valid-select static bank core (H-ELEM-A r2 2026-10-15, successor of hfd_vms_bank_ft_rg4wg1); data calendars unchanged; diagnostic CE +1 edge.
// v15 VM ABI (2026-10-15): IDX read group removed (RG 5->4); IDX reads only the SW slice.
module hfd_vms_bank_identity_q1_b2(
    input wire clk,
    input wire rst_n,
    input wire rslot_v,
    input wire [2:0] rslot,
    input wire wslot_v,
    input wire [2:0] wslot,
    input wire [16:0] rq0,
    output wire [256:0] rr0,
    input wire [16:0] rq1,
    output wire [256:0] rr1,
    input wire [16:0] rq2,
    output wire [256:0] rr2,
    input wire [16:0] rq3,
    output wire [256:0] rr3,
    input wire [280:0] wq0,
    output wire wq_done0,
    input wire [280:0] dq,
    output wire dq_done,
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
    wire [1027:0] rr;
    wire [0:0] wq_done;
    assign rr0=rr[0+:257];
    assign rr1=rr[257+:257];
    assign rr2=rr[514+:257];
    assign rr3=rr[771+:257];
    assign wq_done0=wq_done[0];
    ot_vms_bank_static_identity #(.BANK_ID(2),.SLICE_ID(1),.RG(4),.WG(1)) bank(
        .clk(clk),
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
        .rq({rq3,rq2,rq1,rq0}),.rr(rr),
        .wq({wq0}),.wq_done(wq_done));
endmodule
`default_nettype wire
