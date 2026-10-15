`timescale 1ns/1ps
`default_nettype none
module hfd_vms_bank_stage6_NW (
    input wire clk_pin,
    input wire clk_s1,
    input wire clk_mem,
    input wire clk_capture,
    input wire clk_return,
    input wire clk_status,
    input wire rst_n,
    input wire [2:0] bid,
    input wire [1:0] sid,
    input wire rslot_v,
    input wire [2:0] rslot,
    input wire wslot_v,
    input wire [2:0] wslot,
    input wire [16:0] rq0,
    input wire [16:0] rq1,
    input wire [16:0] rq2,
    input wire [16:0] rq3,
    input wire [16:0] rq4,
    input wire [16:0] rq5,
    output wire [256:0] rr0,
    output wire [256:0] rr1,
    output wire [256:0] rr2,
    output wire [256:0] rr3,
    output wire [256:0] rr4,
    output wire [256:0] rr5,
    input wire [280:0] wq0,
    input wire [280:0] wq1,
    input wire [280:0] wq2,
    output wire wq_done0,
    output wire wq_done1,
    output wire wq_done2,
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
    wire [1541:0] rr;
    wire [2:0] wq_done;
    assign rr0=rr[0+:257];
    assign rr1=rr[257+:257];
    assign rr2=rr[514+:257];
    assign rr3=rr[771+:257];
    assign rr4=rr[1028+:257];
    assign rr5=rr[1285+:257];
    assign wq_done0=wq_done[0+:1];
    assign wq_done1=wq_done[1+:1];
    assign wq_done2=wq_done[2+:1];
    ot_vms_bank_static_wdecode_ft_stageclocks #(.RG(6),.WG(3)) bank (
        .clk_pin(clk_pin),
        .clk_s1(clk_s1),
        .clk_mem(clk_mem),
        .clk_capture(clk_capture),
        .clk_return(clk_return),
        .clk_status(clk_status),
        .rst_n(rst_n),
        .bid(bid),
        .sid(sid),
        .rslot_v(rslot_v),
        .rslot(rslot),
        .wslot_v(wslot_v),
        .wslot(wslot),
        .rq({rq5,rq4,rq3,rq2,rq1,rq0}),
        .rr(rr),
        .wq({wq2,wq1,wq0}),
        .wq_done(wq_done),
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
        .status(status)
    );
endmodule
`default_nettype wire
