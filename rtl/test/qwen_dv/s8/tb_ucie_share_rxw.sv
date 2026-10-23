`timescale 1ns/1ps
// QC-P4 10-23: qfd_ucie_static_share #(RXW 597) (no phy_rx[1042:597] port) vs the as-built module with those 446 bits
// tied 0 (the SIX_FIVE gearbox path).  Random slots/valid/frames every edge, rx_frames/rx_valid/phy_tx/fault compared.
// MUT 1: the reference sees random upper bits (must FAIL: the fault check observes them).  Reference = git HEAD copy
// renamed qfd_ucie_static_share_ref (bench argument).
module tb_ucie_share_rxw;
  parameter integer MUT = 0;
  reg clk = 0; always #0.5 clk = ~clk;
  reg rst_n = 0; reg [1:0] tx_slot, tx_valid, rx_slot; reg rxv; reg [596:0] pf; reg [564:0] rf; reg [1042:0] rx;
  wire [1042:0] rx_ref = (MUT == 1) ? rx : {446'b0, rx[596:0]};
  wire a_ptv, b_ptv; wire [1042:0] a_pt, b_pt; wire [1:0] a_rv, b_rv; wire [1161:0] a_rf, b_rf; wire a_f, b_f;
  qfd_ucie_static_share_ref u_a(.clk(clk),.rst_n(rst_n),.tx_slot(tx_slot),.tx_valid(tx_valid),.p_frame(pf),.r_frame(rf),
    .rx_slot(rx_slot),.phy_rx_valid(rxv),.phy_rx(rx_ref),.phy_tx_valid(a_ptv),.phy_tx(a_pt),.rx_valid(a_rv),.rx_frames(a_rf),.fault(a_f));
  qfd_ucie_static_share #(.RXW(597)) u_b(.clk(clk),.rst_n(rst_n),.tx_slot(tx_slot),.tx_valid(tx_valid),.p_frame(pf),.r_frame(rf),
    .rx_slot(rx_slot),.phy_rx_valid(rxv),.phy_rx(rx[596:0]),.phy_tx_valid(b_ptv),.phy_tx(b_pt),.rx_valid(b_rv),.rx_frames(b_rf),.fault(b_f));
  integer c, bad, nf, i;
  initial begin
    bad = 0; nf = 0;
    for (c = 0; c < 200000; c = c + 1) begin
      @(negedge clk);
      if (c % 256 == 0) rst_n = 0; else rst_n = 1;          // re-arm the sticky fault often
      // mostly legal one-hot slots with matching valid, sometimes illegal; frames random with the high part often 0
      rx_slot = ($urandom % 512 == 0) ? $urandom : (($urandom & 1) ? 2'b01 : 2'b10); rxv = ($urandom % 512 == 0) ? $urandom : |rx_slot;
      tx_slot = ($urandom & 1) ? 2'b01 : 2'b10; tx_valid = ($urandom % 512 == 0) ? $urandom : tx_slot;
      for (i = 0; i < 1043; i = i + 32) rx[i +: 32] = $urandom;
      for (i = 0; i < 597; i = i + 32) pf[i +: 32] = $urandom; for (i = 0; i < 565; i = i + 32) rf[i +: 32] = $urandom;
      if ($urandom % 128 != 0) rx[1042:565] = 0; else if ($urandom & 1) rx[1042:597] = 0;               // legal R565 frames
      #0.2;
      if (a_f) nf = nf + 1;
      if ({a_ptv, a_pt, a_rv, a_rf, a_f} !== {b_ptv, b_pt, b_rv, b_rf, b_f}) begin bad = bad + 1; if (bad <= 4) $display("SHARE_MISMATCH c=%0d fault %b/%b", c, a_f, b_f); end
    end
    if (bad == 0) $display("SHARE_RXW PASS MUT=%0d cycles=200000 fault_cycles=%0d", MUT, nf);
    else $display("SHARE_RXW FAIL MUT=%0d mismatches=%0d", MUT, bad);
    $finish;
  end
endmodule
