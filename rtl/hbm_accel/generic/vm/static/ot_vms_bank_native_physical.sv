`timescale 1ns/1ps
`default_nettype none
// Wires-only adapter to the actual physical quadrant masters. No memory/compute substitute.
module ot_vms_bank_native_physical #(
 parameter integer RG=5, WG=2, QUADRANT=0, MUT=0,
 // Q2_MERGE (H-SM 1016 aef736948, H-NETLIST d4f): the q2 (NW) bank = the exact q0 master + hfd_vms_wq2_merge, which
 // ORs the valid-masked wq1 (SM writer) / wq2 (quantiser) onto the q0 bank's wq1 port (+2 edges, compiler issues them
 // 2 edges earlier; owner codes 2->1, k>=3 -> k-1) and steers wq_done1 back through a fixed 5-edge shift; its sticky
 // flt (same-edge collision = compiler schedule error) joins the bank fault status bit 17.  0 = hfd_vms_bank_native_q2.
 parameter integer Q2_MERGE=0,
 // PIN_IN (H-SM 2026-10-17, H-NETLIST source binding): 1 = every bank data / slot / strap input passes one pin flop at
 // the BANK port -- exactly the literal input pin registers of the bound masters hfd_vms_bank_native_q0_faces (SW, and
 // NW behind the merge leaf: the leaf output wq_m is registered at the bank, the leaf inputs are not) and
 // hfd_vms_bank_native_q1_core_pr (SE/NE).  Outputs unchanged (already bank registers).  The slice moves its ring-stop
 // COMMIT_DELAY to 5 + PIN_IN; every other consequence is a compiler calendar shift (tb_vms_static_ring4_memory PIN_IN).
 parameter integer PIN_IN=0
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
 if(QUADRANT<0||QUADRANT>3||RG!=((QUADRANT==1||QUADRANT==3)?4:5)||WG!=(QUADRANT==2?3:2))$fatal(1,"native bank shape mismatch");
 if(MUT!=0&&MUT!=3&&MUT!=4&&MUT!=5)$fatal(1,"unsupported native mutation");
 end
 wire[2:0] die_bid=MUT==3?bid^3'd1:bid;wire[1:0]die_sid=MUT==4?sid^2'd1:sid;wire die_clk=MUT==5&&bid==7?1'b0:clk;
 localparam integer RBW=((RG+1>1)?$clog2(RG+1):1), WBW=((WG+5>1)?$clog2(WG+5):1);
 wire[2:0] p_bid; wire[1:0] p_sid; wire p_rslot_v, p_wslot_v; wire[RBW-1:0] p_rslot; wire[WBW-1:0] p_wslot;
 wire[RG*17-1:0] p_rq; wire[WG*281-1:0] p_wq; wire[280:0] p_dq, p_kq; wire[275:0] p_xq, p_xq2; wire[284:0] p_pq;
 generate if(PIN_IN!=0)begin:pin_in
  reg[2:0] q_bid; reg[1:0] q_sid; reg q_rv, q_wv; reg[RBW-1:0] q_rs; reg[WBW-1:0] q_ws; reg[RG*17-1:0] q_rq;
  reg[WG*281-1:0] q_wq; reg[280:0] q_dq, q_kq; reg[275:0] q_xq, q_xq2; reg[284:0] q_pq;
  always @(posedge die_clk) begin q_bid<=die_bid; q_sid<=die_sid; q_rv<=rslot_v; q_wv<=wslot_v; q_rs<=rslot; q_ws<=wslot;
   q_rq<=rq; q_wq<=wq; q_dq<=dq; q_kq<=kq; q_xq<=xq; q_xq2<=xq2; q_pq<=pq; end
  assign p_bid=q_bid; assign p_sid=q_sid; assign p_rslot_v=q_rv; assign p_wslot_v=q_wv; assign p_rslot=q_rs; assign p_wslot=q_ws;
  assign p_rq=q_rq; assign p_wq=q_wq; assign p_dq=q_dq; assign p_kq=q_kq; assign p_xq=q_xq; assign p_xq2=q_xq2; assign p_pq=q_pq;
 end else begin:no_pin_in
  assign p_bid=die_bid; assign p_sid=die_sid; assign p_rslot_v=rslot_v; assign p_wslot_v=wslot_v; assign p_rslot=rslot; assign p_wslot=wslot;
  assign p_rq=rq; assign p_wq=wq; assign p_dq=dq; assign p_kq=kq; assign p_xq=xq; assign p_xq2=xq2; assign p_pq=pq;
 end endgenerate
 generate
 if(QUADRANT==0)begin:q0
 hfd_vms_bank_native_q0 u_bank(
.bid(p_bid),
   .sid(p_sid),
   .clk(die_clk),
   .rst_n(rst_n),
   .rslot_v(p_rslot_v),
   .rslot(p_rslot),
   .wslot_v(p_wslot_v),
   .wslot(p_wslot),
   .dq(p_dq),
   .dq_done(dq_done),
   .kq(p_kq),
   .kq_done(kq_done),
   .xq(p_xq),
   .xq_done(xq_done),
   .xq2(p_xq2),
   .xq2_done(xq2_done),
   .eg(eg),
   .pq(p_pq),
   .pr(pr),
   .status(status),
.rq0(p_rq[0*17+:17]),.rr0(rr[0*257+:257]),
.rq1(p_rq[1*17+:17]),.rr1(rr[1*257+:257]),
.rq2(p_rq[2*17+:17]),.rr2(rr[2*257+:257]),
.rq3(p_rq[3*17+:17]),.rr3(rr[3*257+:257]),
.rq4(p_rq[4*17+:17]),.rr4(rr[4*257+:257]),
.wq0(p_wq[0*281+:281]),.wq_done0(wq_done[0]),
.wq1(p_wq[1*281+:281]),.wq_done1(wq_done[1]));
 end
 if(QUADRANT==1)begin:q1
 hfd_vms_bank_native_q1 u_bank(
.bid(p_bid),
   .sid(p_sid),
   .clk(die_clk),
   .rst_n(rst_n),
   .rslot_v(p_rslot_v),
   .rslot(p_rslot),
   .wslot_v(p_wslot_v),
   .wslot(p_wslot),
   .dq(p_dq),
   .dq_done(dq_done),
   .kq(p_kq),
   .kq_done(kq_done),
   .xq(p_xq),
   .xq_done(xq_done),
   .xq2(p_xq2),
   .xq2_done(xq2_done),
   .eg(eg),
   .pq(p_pq),
   .pr(pr),
   .status(status),
.rq0(p_rq[0*17+:17]),.rr0(rr[0*257+:257]),
.rq1(p_rq[1*17+:17]),.rr1(rr[1*257+:257]),
.rq2(p_rq[2*17+:17]),.rr2(rr[2*257+:257]),
.rq3(p_rq[3*17+:17]),.rr3(rr[3*257+:257]),
.wq0(p_wq[0*281+:281]),.wq_done0(wq_done[0]),
.wq1(p_wq[1*281+:281]),.wq_done1(wq_done[1]));
 end
 if(QUADRANT==2&&Q2_MERGE!=0)begin:q2m
 wire[280:0] m_wq; wire m_done, m_flt; wire[17:0] b_status; wire[280:0] p_mwq;
 if(PIN_IN!=0)begin:mpin reg[280:0] q_mwq; always @(posedge die_clk) q_mwq<=m_wq; assign p_mwq=q_mwq; end
 else begin:mnopin assign p_mwq=m_wq; end
 // DONE_LAT = bank wq1 -> wq_done1 seen from the leaf output: 4 at the bare q0 body, 5 with the bank's input pin flop
 hfd_vms_wq2_merge #(.DONE_LAT(4+(PIN_IN!=0?1:0))) u_merge(.clk(die_clk),.rst_n(rst_n),.wq1(wq[1*281+:281]),.wq2(wq[2*281+:281]),.wq_m(m_wq),
   .done_m(m_done),.wq_done1(wq_done[1]),.wq_done2(wq_done[2]),.flt(m_flt));
 assign status={b_status[17]|m_flt,b_status[16:0]};
 hfd_vms_bank_native_q0 u_bank(
.bid(p_bid),
   .sid(p_sid),
   .clk(die_clk),
   .rst_n(rst_n),
   .rslot_v(p_rslot_v),
   .rslot(p_rslot),
   .wslot_v(p_wslot_v),
   .wslot(p_wslot),
   .dq(p_dq),
   .dq_done(dq_done),
   .kq(p_kq),
   .kq_done(kq_done),
   .xq(p_xq),
   .xq_done(xq_done),
   .xq2(p_xq2),
   .xq2_done(xq2_done),
   .eg(eg),
   .pq(p_pq),
   .pr(pr),
   .status(b_status),
.rq0(p_rq[0*17+:17]),.rr0(rr[0*257+:257]),
.rq1(p_rq[1*17+:17]),.rr1(rr[1*257+:257]),
.rq2(p_rq[2*17+:17]),.rr2(rr[2*257+:257]),
.rq3(p_rq[3*17+:17]),.rr3(rr[3*257+:257]),
.rq4(p_rq[4*17+:17]),.rr4(rr[4*257+:257]),
.wq0(p_wq[0*281+:281]),.wq_done0(wq_done[0]),
.wq1(p_mwq),.wq_done1(m_done));
 end
 if(QUADRANT==2&&Q2_MERGE==0)begin:q2
 hfd_vms_bank_native_q2 u_bank(
.bid(p_bid),
   .sid(p_sid),
   .clk(die_clk),
   .rst_n(rst_n),
   .rslot_v(p_rslot_v),
   .rslot(p_rslot),
   .wslot_v(p_wslot_v),
   .wslot(p_wslot),
   .dq(p_dq),
   .dq_done(dq_done),
   .kq(p_kq),
   .kq_done(kq_done),
   .xq(p_xq),
   .xq_done(xq_done),
   .xq2(p_xq2),
   .xq2_done(xq2_done),
   .eg(eg),
   .pq(p_pq),
   .pr(pr),
   .status(status),
.rq0(p_rq[0*17+:17]),.rr0(rr[0*257+:257]),
.rq1(p_rq[1*17+:17]),.rr1(rr[1*257+:257]),
.rq2(p_rq[2*17+:17]),.rr2(rr[2*257+:257]),
.rq3(p_rq[3*17+:17]),.rr3(rr[3*257+:257]),
.rq4(p_rq[4*17+:17]),.rr4(rr[4*257+:257]),
.wq0(p_wq[0*281+:281]),.wq_done0(wq_done[0]),
.wq1(p_wq[1*281+:281]),.wq_done1(wq_done[1]),
.wq2(p_wq[2*281+:281]),.wq_done2(wq_done[2]));
 end
 if(QUADRANT==3)begin:q3
 // NE shares the SE bank master (RG4/WG2); sid is a port (H-NETLIST 0600)
 hfd_vms_bank_native_q1 u_bank(
.bid(p_bid),
   .sid(p_sid),
   .clk(die_clk),
   .rst_n(rst_n),
   .rslot_v(p_rslot_v),
   .rslot(p_rslot),
   .wslot_v(p_wslot_v),
   .wslot(p_wslot),
   .dq(p_dq),
   .dq_done(dq_done),
   .kq(p_kq),
   .kq_done(kq_done),
   .xq(p_xq),
   .xq_done(xq_done),
   .xq2(p_xq2),
   .xq2_done(xq2_done),
   .eg(eg),
   .pq(p_pq),
   .pr(pr),
   .status(status),
.rq0(p_rq[0*17+:17]),.rr0(rr[0*257+:257]),
.rq1(p_rq[1*17+:17]),.rr1(rr[1*257+:257]),
.rq2(p_rq[2*17+:17]),.rr2(rr[2*257+:257]),
.rq3(p_rq[3*17+:17]),.rr3(rr[3*257+:257]),
.wq0(p_wq[0*281+:281]),.wq_done0(wq_done[0]),
.wq1(p_wq[1*281+:281]),.wq_done1(wq_done[1]));
 end
 endgenerate
endmodule
`default_nettype wire
