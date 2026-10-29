`timescale 1ns/1ps
// DIE-HBM-20-EPA: equivalence bench, hfd_ep_static (kit face-shell + fcore) vs hfd_ep_static_pair (tx core + rx core).
// Each DUT's sd_tx is looped back into its own sd_rx (1 register) so the RX gearbox locks on real markers and frames.
// Random COLL controls / tx_v / tx_frame from cycle TXON; sd_st random.  Checks every cycle:
//   all outputs except fault_cause[9] and fault: exact; pair.fault_cause[9](t) == orig.fault_cause[9](t-2);
//   pair.fault(t) == orig.fault(t) whenever the fc9 histories agree (outside the 2-edge window).
module tb;
  reg clk = 0; always #0.5 clk = ~clk;
  reg rst_n = 0;
  reg tx_v; reg [611:0] tx_frame; reg arm_v, arm_b, rel_v, rel_b, slot_v, slot_b; reg [6:0] words; reg [5:0] slot_i;
  reg [1:0] st;
  wire [511:0] tx_a, tx_b; reg [511:0] rx_a, rx_b;
  wire pv_a, pv_b, pu_a, pu_b, f_a, f_b; wire [611:0] pf_a, pf_b; wire [1:0] br_a, br_b; wire [10:0] fc_a, fc_b;
  hfd_ep_static A (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_frame(tx_frame), .rx_arm_v(arm_v), .rx_arm_bank(arm_b),
    .rx_block_words(words), .rx_release_v(rel_v), .rx_release_bank(rel_b), .rx_slot_v(slot_v), .rx_slot_bank(slot_b),
    .rx_slot_index(slot_i), .rx_pin_v(pv_a), .rx_pin_flit(pf_a), .rx_block_ready(br_a), .phy_up(pu_a), .fault(f_a),
    .fault_cause(fc_a), .sd_tx(tx_a), .sd_rx(rx_a), .sd_st(st));
  hfd_ep_static_pair B (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_frame(tx_frame), .rx_arm_v(arm_v), .rx_arm_bank(arm_b),
    .rx_block_words(words), .rx_release_v(rel_v), .rx_release_bank(rel_b), .rx_slot_v(slot_v), .rx_slot_bank(slot_b),
    .rx_slot_index(slot_i), .rx_pin_v(pv_b), .rx_pin_flit(pf_b), .rx_block_ready(br_b), .phy_up(pu_b), .fault(f_b),
    .fault_cause(fc_b), .sd_tx(tx_b), .sd_rx(rx_b), .sd_st(st));
  always @(posedge clk) begin rx_a <= tx_a; rx_b <= tx_b; end
  integer proto, ps, wt, si, nw, nblk, fb_i; reg fb;
  integer cyc, err, i, seed, txon, ncyc, nlock, npv, nfc9, nfault;
  reg [3:0] h9;  // orig fc9 history
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    if (!$value$plusargs("txon=%d", txon)) txon = 3000;
    if (!$value$plusargs("n=%d", ncyc)) ncyc = 20000;
    if (!$value$plusargs("proto=%d", proto)) proto = 0;
    if (!$value$plusargs("words=%d", nw)) nw = 8;
    ps = 0; wt = 0; si = 0; nblk = 0; fb = 0;
    err = 0; nlock = 0; npv = 0; nfc9 = 0; nfault = 0; h9 = 0;
    tx_v = 0; tx_frame = 0; arm_v = 0; arm_b = 0; rel_v = 0; rel_b = 0; slot_v = 0; slot_b = 0; words = 0; slot_i = 0; st = 2'b10;
    rx_a = 0; rx_b = 0;
    repeat (5) @(posedge clk); #0.1 rst_n = 1;
    for (cyc = 0; cyc < ncyc; cyc = cyc + 1) begin
      @(negedge clk);
      tx_v = (cyc >= txon) ? (proto ? (($random(seed) & 15) == 0) : ($random(seed) & 1)) : 0;
      for (i = 0; i < 20; i = i + 1) tx_frame[i*32 +: 32] = $random(seed);
      if (proto) begin
        // legal block protocol driven from the ORIGINAL dut's registered block_ready (same inputs to both DUTs)
        arm_v = 0; rel_v = 0; slot_v = 0;
        case (ps)
          0: begin wt = wt + 1; if (wt > 20) begin arm_v = 1; arm_b = fb; words = nw; ps = 1; end end
          1: if (br_a[fb]) begin ps = 2; wt = 0; end
          2: begin wt = wt + 1; if (wt > 6) begin arm_v = 1; arm_b = !fb; words = nw; ps = 3; end end
          3: begin rel_v = 1; rel_b = fb; ps = 4; si = 0; wt = 0; end
          4: begin wt = wt + 1; if (wt > 4) begin slot_v = 1; slot_b = fb; slot_i = si; si = si + 1; if (si == nw) begin ps = 5; wt = 0; end end end
          5: begin wt = wt + 1; if (wt > 12) begin fb = !fb; ps = 1; nblk = nblk + 1; end end
        endcase
      end else begin
      arm_v = ($random(seed) & 7) == 0; arm_b = $random(seed); words = $random(seed);
      rel_v = ($random(seed) & 7) == 0; rel_b = $random(seed);
      slot_v = ($random(seed) & 3) == 0; slot_b = $random(seed); slot_i = $random(seed);
      end
      st = (cyc > ncyc/2 && ($random(seed) & 255) == 0) ? 2'b11 : 2'b10;
      @(posedge clk); #0.1;
      if ({pv_a, pf_a, br_a, pu_a, fc_a[10], fc_a[8:0], tx_a} !== {pv_b, pf_b, br_b, pu_b, fc_b[10], fc_b[8:0], tx_b}) begin
        err = err + 1; if (err < 10) $display("MISMATCH cyc %0d pv %b/%b pu %b/%b br %b/%b fc %b/%b tx %0d pf %0d", cyc, pv_a, pv_b, pu_a, pu_b, br_a, br_b, fc_a, fc_b, tx_a !== tx_b, pf_a !== pf_b);
      end
      if (fc_b[9] !== h9[1]) begin err = err + 1; if (err < 10) $display("FC9 cyc %0d pair %b orig(t-2) %b", cyc, fc_b[9], h9[1]); end
      if (h9[1:0] == {2{fc_a[9]}} && f_a !== f_b) begin err = err + 1; if (err < 10) $display("FAULT cyc %0d %b/%b", cyc, f_a, f_b); end
      h9 = {h9[2:0], fc_a[9]};
      if (pu_a) nlock = nlock + 1; if (pv_a) npv = npv + 1; if (fc_a[9]) nfc9 = nfc9 + 1; if (f_a) nfault = nfault + 1;
    end
    $display("RESULT proto %0d blocks %0d seed %0d txon %0d cycles %0d errors %0d | coverage phy_up %0d rx_pin_v %0d fc9 %0d fault %0d fc_last %b", proto, nblk, seed, txon, ncyc, err, nlock, npv, nfc9, nfault, fc_a);
    $finish;
  end
endmodule
