`timescale 1ns/1ps
// PIN-FLOP VARIANT (redesign-hbm 2026-10-08): every data input (rb_pop, send, issue, cdc_wr, phy_pop) lands in a
// pin flop with no logic before it (PIN=1 in the three cores), so the consistent die-link budget's input window
// (T-60-R, R = 254 ps) sees only pin -> flop.  Outputs were already flop-driven.  Cost: 0 cycles on the token path;
// credit return +1 core edge (rb_pop), partner reserve 1 credit (send), TX full-rate bound D_tx >= 29 (was 27).
// Physical screen wrapper of the native credit contract: one RX producer (core) + its PHY-side
// synchronisers + one partner consumer + one TX flight gate.  For the single-clock screen the PHY and
// partner domains are tied to clk, so every synchroniser path is timed as a full single-cycle path
// (stricter than the asynchronous false path the real crossing gets).
// Both reset inputs enter through local async-assert / 2-edge-release synchronisers (as
// ot_hbm_collective_reset_entry does on the die); the raw reset ports are false paths in the screen SDC.
module hfd_coll_credit_prod(
 input wire clk,rst_in_n,phy_rst_in_n,rb_pop,send,issue,cdc_wr,phy_pop,
 input wire [8:0] k_gray_link,input wire ready_link,
 output wire [8:0] k_gray_ph,output wire ready_ph,
 output wire can_send,allow,output wire [8:0] avail);
 wire [8:0] k_gray,k_seen;wire ready,ready_seen;wire [7:0] infl;
 (* ASYNC_REG="TRUE" *) reg [1:0] rst_s,prst_s;
 always @(posedge clk or negedge rst_in_n)if(!rst_in_n)rst_s<=2'b00;else rst_s<={rst_s[0],1'b1};
 always @(posedge clk or negedge phy_rst_in_n)if(!phy_rst_in_n)prst_s<=2'b00;else prst_s<={prst_s[0],1'b1};
 wire rst_n=rst_s[1],phy_rst_n=prst_s[1];
 ot_hbm_coll_credit_producer #(.C(256),.CW(9),.SYNC(2),.PIN(1)) u_p(.clk(clk),.rst_n(rst_n),.phy_rst_n(phy_rst_n),
  .rb_pop(rb_pop),.k_gray(k_gray),.ready(ready));
 ot_hbm_coll_credit_phy_tx #(.CW(9),.SYNC(2)) u_t(.pclk(clk),.prst_n(phy_rst_n),.k_gray_core(k_gray),
  .ready_core(ready),.k_gray_ph(k_gray_ph),.ready_ph(ready_ph));
 ot_hbm_coll_credit_consumer #(.C(256),.CW(9),.SYNC(2),.PIN(1)) u_c(.clk(clk),.rst_n(rst_n),.k_gray_link(k_gray_link),
  .ready_link(ready_link),.send(send),.can_send(can_send),.avail_o(avail),.k_seen_o(k_seen),.ready_seen_o(ready_seen));
 ot_hbm_coll_tx_flight_gate #(.DTX(64),.DW(8),.WSTG(14),.SYNC(2),.H(2),.PIN(1)) u_g(.clk(clk),.rst_n(rst_n),.pclk(clk),
  .prst_n(phy_rst_n),.issue(issue),.cdc_wr(cdc_wr),.phy_pop(phy_pop),.allow(allow),.inflight_o(infl));
endmodule
