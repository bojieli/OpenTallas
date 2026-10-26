`timescale 1ns/1ps
`default_nettype none
// Literal physical ABI, exact unchanged static bank core; no added pipeline.
module hfd_vms_bank_ft_rg5wg1(
    input wire clk,
    input wire rst_n,
    input wire [2:0] bid,
    input wire [1:0] sid,
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
    input wire [16:0] rq4,
    output wire [256:0] rr4,
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
    wire [1284:0] rr;
    wire [0:0] wq_done;
    assign rr0=rr[0+:257];
    assign rr1=rr[257+:257];
    assign rr2=rr[514+:257];
    assign rr3=rr[771+:257];
    assign rr4=rr[1028+:257];
    assign wq_done0=wq_done[0];
    ot_vms_bank_static_wdecode_ft #(.RG(5),.WG(1)) bank(
        .clk(clk),
        .rst_n(rst_n),
        .bid(bid),
        .sid(sid),
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
        .wq({wq0}),.wq_done(wq_done));
endmodule
`default_nettype wire
