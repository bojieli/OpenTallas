`timescale 1ns/1ps
`default_nettype none
// Wires-only adapter to the actual physical quadrant masters. No memory/compute substitute.
module ot_vms_bank_strap_physical #(
 parameter integer RG=5, WG=1, QUADRANT=0, MUT=0
) (
    input wire clk, rst_n,
    input wire [2:0] bid,               // strap: bank identity (die constant)
    input wire [1:0] sid,               // strap: slice / quadrant identity (die constant)
    input wire rslot_v,
    input wire [((RG+1>1)?$clog2(RG+1):1)-1:0] rslot,
    input wire wslot_v,
    input wire [((WG+5>1)?$clog2(WG+5):1)-1:0] wslot,
    input wire [RG*17-1:0] rq,
    output wire [RG*257-1:0] rr,
    input wire [WG*281-1:0] wq,
    output wire [WG-1:0] wq_done,
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

 initial begin
  if (QUADRANT<0 || QUADRANT>3 || RG!=(QUADRANT==0?5:QUADRANT==1?4:6) || WG!=(QUADRANT<2?1:3)) $fatal(1,"physical strap bank shape mismatch");
  if (MUT!=0 && MUT!=3 && MUT!=4 && MUT!=5) $fatal(1,"unsupported physical strap mutation");
 end
 wire [2:0] die_bid = MUT==3 ? bid^3'd1 : bid;
 wire [1:0] die_sid = MUT==4 ? sid^2'd1 : sid;
 wire die_clk = MUT==5 && bid==7 ? 1'b0 : clk;
 generate
 if(QUADRANT==0) begin:q0
  hfd_vms_bank_strap_q0 u_bank (
   .bid(die_bid),
   .sid(die_sid),
   .clk(die_clk),
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
   .rq0(rq[0*17+:17]),
   .rr0(rr[0*257+:257]),
   .rq1(rq[1*17+:17]),
   .rr1(rr[1*257+:257]),
   .rq2(rq[2*17+:17]),
   .rr2(rr[2*257+:257]),
   .rq3(rq[3*17+:17]),
   .rr3(rr[3*257+:257]),
   .rq4(rq[4*17+:17]),
   .rr4(rr[4*257+:257]),
   .wq0(wq[0*281+:281]),
   .wq_done0(wq_done[0]));
 end
 if(QUADRANT==1) begin:q1
  hfd_vms_bank_strap_q1 u_bank (
   .bid(die_bid),
   .sid(die_sid),
   .clk(die_clk),
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
   .rq0(rq[0*17+:17]),
   .rr0(rr[0*257+:257]),
   .rq1(rq[1*17+:17]),
   .rr1(rr[1*257+:257]),
   .rq2(rq[2*17+:17]),
   .rr2(rr[2*257+:257]),
   .rq3(rq[3*17+:17]),
   .rr3(rr[3*257+:257]),
   .wq0(wq[0*281+:281]),
   .wq_done0(wq_done[0]));
 end
 if(QUADRANT==2) begin:q2
  hfd_vms_bank_strap_q2 u_bank (
   .bid(die_bid),
   .sid(die_sid),
   .clk(die_clk),
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
   .rq0(rq[0*17+:17]),
   .rr0(rr[0*257+:257]),
   .rq1(rq[1*17+:17]),
   .rr1(rr[1*257+:257]),
   .rq2(rq[2*17+:17]),
   .rr2(rr[2*257+:257]),
   .rq3(rq[3*17+:17]),
   .rr3(rr[3*257+:257]),
   .rq4(rq[4*17+:17]),
   .rr4(rr[4*257+:257]),
   .rq5(rq[5*17+:17]),
   .rr5(rr[5*257+:257]),
   .wq0(wq[0*281+:281]),
   .wq_done0(wq_done[0]),
   .wq1(wq[1*281+:281]),
   .wq_done1(wq_done[1]),
   .wq2(wq[2*281+:281]),
   .wq_done2(wq_done[2]));
 end
 if(QUADRANT==3) begin:q3
  hfd_vms_bank_strap_q3 u_bank (
   .bid(die_bid),
   .sid(die_sid),
   .clk(die_clk),
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
   .rq0(rq[0*17+:17]),
   .rr0(rr[0*257+:257]),
   .rq1(rq[1*17+:17]),
   .rr1(rr[1*257+:257]),
   .rq2(rq[2*17+:17]),
   .rr2(rr[2*257+:257]),
   .rq3(rq[3*17+:17]),
   .rr3(rr[3*257+:257]),
   .rq4(rq[4*17+:17]),
   .rr4(rr[4*257+:257]),
   .rq5(rq[5*17+:17]),
   .rr5(rr[5*257+:257]),
   .wq0(wq[0*281+:281]),
   .wq_done0(wq_done[0]),
   .wq1(wq[1*281+:281]),
   .wq_done1(wq_done[1]),
   .wq2(wq[2*281+:281]),
   .wq_done2(wq_done[2]));
 end
 endgenerate
endmodule
`default_nettype wire
