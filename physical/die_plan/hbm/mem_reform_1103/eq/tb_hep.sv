`timescale 1ns/1ps
// DIE-HBM-61/MEM lockstep bench: ot_hep_rx_block (the two ot_hep_rx_leaf SRAM leaves + fill/seal/drain contract) and a
// bare ot_hep_rx_leaf, random stimulus biased to exercise arm -> fill -> ready -> slot drain -> release.  Every
// output is printed every cycle; the r2c2 and right-width builds must print identical traces.
module tb;
  reg clk = 0, rst_n = 0;
  always #1 clk = ~clk;
  reg arm_v, phy_v, release_v, slot_v; reg [6:0] block_words; reg [611:0] phy_flit; reg [5:0] slot_index;
  wire phy_ready, block_ready, pin_v, fault; wire [9:0] pin_vr; wire [611:0] pin_flit; wire [4:0] fault_cause;
  ot_hep_rx_block #(.MUT(`TB_MUT)) dut (.clk(clk), .rst_n(rst_n), .arm_v(arm_v), .block_words(block_words), .phy_v(phy_v),
    .phy_flit(phy_flit), .phy_ready(phy_ready), .block_ready(block_ready), .release_v(release_v), .slot_v(slot_v),
    .slot_index(slot_index), .pin_v(pin_v), .pin_vr(pin_vr), .pin_flit(pin_flit), .fault(fault), .fault_cause(fault_cause));
  reg we; reg [5:0] wa, ra; reg [305:0] din; wire [305:0] dout;
  ot_hep_rx_leaf #(.W(306), .MUT(0)) leaf (.ck(clk), .we(we), .wa(wa), .ra(ra), .din(din), .dout(dout));
  integer cyc, seed, wr, nzr, rdy, pv;
  integer k, ph, idle, nw, ns; reg [639:0] r640;
  initial begin
    seed = `TB_SEED; ph = 0; idle = 2; wr = 0; nzr = 0; rdy = 0; pv = 0;
    arm_v = 0; phy_v = 0; release_v = 0; slot_v = 0; block_words = 0; phy_flit = 0; slot_index = 0; we = 0; wa = 0; ra = 0; din = 0;
    repeat (4) @(posedge clk); rst_n = 1;
    for (cyc = 0; cyc < `TB_CYC; cyc = cyc + 1) begin
      @(negedge clk);
      // protocol driver: EMPTY -> arm -> FILL (random phy_v gaps) -> READY -> release -> DRAIN slots in order -> FLUSH
      arm_v = 0; release_v = 0; slot_v = 0; phy_v = 0; slot_index = 0;
      case (ph)
        0: begin if (idle == 0) begin arm_v = 1; block_words = 7'd1 + ($random(seed) & 63); nw = block_words; ph = 1; end else idle = idle - 1; end
        1: begin phy_v = ($random(seed) & 3) != 0; if (block_ready) ph = 2; end
        2: begin if (($random(seed) & 3) == 0) begin release_v = 1; ph = 3; ns = 0; end end
        3: begin if (($random(seed) & 1) && ns < nw) begin slot_v = 1; slot_index = ns; ns = ns + 1; end
                 if (ns == nw) begin ph = 0; idle = 8; end end
      endcase
      for (k = 0; k < 20; k = k + 1) r640[k*32 +: 32] = $random(seed); phy_flit = r640[611:0];
      we = $random(seed); wa = $random(seed); ra = $random(seed); for (k = 0; k < 10; k = k + 1) r640[k*32 +: 32] = $random(seed); din = r640[305:0];
      @(posedge clk); #0.1;
      if (we) wr = wr + 1; if (dout != 0) nzr = nzr + 1; if (block_ready) rdy = rdy + 1; if (pin_v) pv = pv + 1;
      $display("%0d %b%b%b%b %h %h %h %h", cyc, phy_ready, block_ready, pin_v, fault, pin_vr, fault_cause, pin_flit, dout);
    end
    $display("COVER leaf_writes=%0d leaf_nonzero_reads=%0d block_ready_cycles=%0d pin_v_cycles=%0d fault=%0d", wr, nzr, rdy, pv, fault);
    $finish;
  end
endmodule
