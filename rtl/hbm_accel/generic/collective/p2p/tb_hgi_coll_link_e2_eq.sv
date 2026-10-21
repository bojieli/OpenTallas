`timescale 1ns/1ps
// HBM-COLLQ6-LINK 10-20: link-level lockstep miter for the SAFE rail leaf body.
//   u_ref = ot_hgi_coll_link_e  (original: 5 entry clocks, 4 x 141-b retry banks, ot_qkvd_llr_replay_sram_leaf)
//   u_dut = ot_hgi_coll_link_e1 (hard leaf wrapper; body ot_hgi_coll_link_e2: 2 x 282-b banks, kept fan-out copies)
// Same inputs; EVERY output compared EVERY cycle.  Stimulus = epochs of a legal compiled link calendar (sequential
// write / read / rx-expect identities, write-before-read, slot reuse only after its read, PHY loopback of the reference's
// TX frames into RX after LOOP edges with the matching rx expectation) plus, per epoch, an optional random fault
// injection (sequence slip, epoch mismatch, PHY down, CRC bit flip on the loopback, unexpected / missing RX, slot
// collision, observed-write drop).  The parent lockstep (tb_hfd_coll_<v>_lpf_ars_eq) has tx_v_cycles=0, so this miter is
// the bench that exercises the retry store, the TX/RX codec and the fault paths.
module tb_hgi_coll_link_e2_eq;
 localparam integer NCYC=60000, LOOP=3;
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0;
 reg epoch_begin=0; reg [7:0] epoch_new=0, held_epoch=0;
 reg wr_v=0, wr_observed_v=0; reg [15:0] wr_seq=0; reg [544:0] wr_flit=0;
 reg rd_v=0; reg [15:0] rd_seq=0; reg rx_expect_v=0; reg [15:0] rx_expect_seq=0;
 reg phy_up=1; reg rx_pin_v=0; reg [611:0] rx_pin_flit=0;
 wire r_tx_v,d_tx_v,r_rx_v,d_rx_v,r_ab,d_ab,r_rr,d_rr;
 wire [611:0] r_tx,d_tx; wire [544:0] r_rx,d_rx; wire [10:0] r_fc,d_fc;
 ot_hgi_coll_link_e u_ref(.ck({5{clk}}),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch_new(epoch_new),.held_epoch(held_epoch),
  .wr_v(wr_v),.wr_observed_v(wr_observed_v),.wr_seq(wr_seq),.wr_flit(wr_flit),.rd_v(rd_v),.rd_seq(rd_seq),
  .rx_expect_v(rx_expect_v),.rx_expect_seq(rx_expect_seq),.phy_up(phy_up),.tx_pin_v(r_tx_v),.tx_pin_flit(r_tx),
  .rx_pin_v(rx_pin_v),.rx_pin_flit(rx_pin_flit),.rx_v(r_rx_v),.rx_flit(r_rx),.epoch_abort(r_ab),
  .retry_requested(r_rr),.fault_cause(r_fc));
 ot_hgi_coll_link_e1 u_dut(.clk(clk),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch_new(epoch_new),.held_epoch(held_epoch),
  .wr_v(wr_v),.wr_observed_v(wr_observed_v),.wr_seq(wr_seq),.wr_flit(wr_flit),.rd_v(rd_v),.rd_seq(rd_seq),
  .rx_expect_v(rx_expect_v),.rx_expect_seq(rx_expect_seq),.phy_up(phy_up),.tx_pin_v(d_tx_v),.tx_pin_flit(d_tx),
  .rx_pin_v(rx_pin_v),.rx_pin_flit(rx_pin_flit),.rx_v(d_rx_v),.rx_flit(d_rx),.epoch_abort(d_ab),
  .retry_requested(d_rr),.fault_cause(d_fc));

 // ---- calendar state (testbench side)
 integer cyc=0, bad=0, nc=0, n_tx=0, n_rx=0, n_ab=0, n_ep=0, n_wr=0, n_rd=0, n_fi=0;
 integer wcnt, rcnt, xcnt;            // identities issued this epoch
 integer ep_len, ep_age, fi_kind, fi_at;
 reg [63:0] pend;                      // slot written, not yet read (TB view)
 integer wr_age[0:63];                 // cycle the slot's write was issued
 integer rd_age[0:63];                 // cycle the slot's read was issued (reuse >= 5 edges later: no s2..s4 collision)
 reg [LOOP-1:0] lv; reg [611:0] lf[0:LOOP-1];
 reg [31:0] seed;
 function [31:0] rnd; input integer dummy; begin seed = seed*32'd1664525 + 32'd1013904223; rnd = seed; end endfunction
 integer i;
 task new_epoch; begin
  epoch_begin <= 1; epoch_new <= rnd(0); wcnt = 0; rcnt = 0; xcnt = 0; pend = 0; ep_age = 0;
  ep_len = 300 + (rnd(0) % 900); n_ep = n_ep + 1;
  for (i = 0; i < 64; i = i + 1) rd_age[i] = -100;
  lv <= 0; rx_pin_v <= 0; rx_expect_v <= 0;   // no frame of the old epoch reaches the new one
  fi_kind = (rnd(0) % 3 == 0) ? 0 : 1 + (rnd(0) % 9);   // 1/3 of epochs fault-free to the end
  fi_at = 40 + (rnd(0) % (ep_len - 60));
 end endtask

 always @(posedge clk) begin
  cyc <= cyc + 1;
  // ---------- compare (outputs of the previous edge)
  if (rst_n) begin
   nc = nc + 1;
   if ({r_tx_v,r_tx,r_rx_v,r_rx,r_ab,r_rr,r_fc} !== {d_tx_v,d_tx,d_rx_v,d_rx,d_ab,d_rr,d_fc}) begin
    bad = bad + 1;
    if (bad <= 8) $display("LINK_EQ_MISMATCH cyc=%0d tx_v %b/%b rx_v %b/%b abort %b/%b fc %h/%h tx_eq %0d rx_eq %0d",
      cyc, r_tx_v, d_tx_v, r_rx_v, d_rx_v, r_ab, d_ab, r_fc, d_fc, r_tx===d_tx, r_rx===d_rx);
   end
   if (r_tx_v) n_tx = n_tx + 1;
   if (r_rx_v) n_rx = n_rx + 1;
  end
  // ---------- PHY loopback of the REFERENCE's TX (both DUTs see the same RX)
  lv <= {lv[LOOP-2:0], r_tx_v}; lf[0] <= r_tx; for (i = 1; i < LOOP; i = i + 1) lf[i] <= lf[i-1];
  rx_pin_v <= lv[LOOP-1]; rx_pin_flit <= lf[LOOP-1];
  rx_expect_v <= lv[LOOP-1]; rx_expect_seq <= xcnt[15:0];
  if (lv[LOOP-1]) xcnt = xcnt + 1;
  // ---------- defaults
  epoch_begin <= 0; wr_v <= 0; wr_observed_v <= 0; rd_v <= 0; phy_up <= 1;
  wr_flit <= {rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0)};
  if (!rst_n) begin
   if (cyc == 6) rst_n <= 1;
  end else if (cyc == 10 || ep_age >= ep_len) begin
   if (r_ab) n_ab = n_ab + 1;
   new_epoch;
  end else begin
   ep_age = ep_age + 1;
   held_epoch <= epoch_new;
   // legal calendar: write when the next slot is free; read slots written >= 2 edges ago, in order
   if ((rnd(0) % 4) != 0 && !pend[wcnt % 64] && ep_age - rd_age[wcnt % 64] >= 5) begin
    wr_v <= 1; wr_observed_v <= 1; wr_seq <= wcnt[15:0]; pend[wcnt % 64] = 1; wr_age[wcnt % 64] = ep_age;
    wcnt = wcnt + 1; n_wr = n_wr + 1;
   end
   if (rcnt < wcnt && pend[rcnt % 64] && ep_age - wr_age[rcnt % 64] >= 3 && (rnd(0) % 3) != 0) begin
    rd_v <= 1; rd_seq <= rcnt[15:0]; pend[rcnt % 64] = 0; rd_age[rcnt % 64] = ep_age; rcnt = rcnt + 1; n_rd = n_rd + 1;
   end
   // one fault injection per faulty epoch
   if (fi_kind != 0 && ep_age == fi_at) begin
    n_fi = n_fi + 1;
    case (fi_kind)
     1: begin wr_v <= 1; wr_observed_v <= 1; wr_seq <= wcnt[15:0] + 16'd5; end   // write sequence slip
     2: held_epoch <= epoch_new ^ 8'h21;                                        // epoch mismatch
     3: phy_up <= 0;                                                            // PHY down (fault only on a TX edge)
     4: rx_pin_flit <= lf[LOOP-1] ^ (612'd1 << (rnd(0) % 580));                 // CRC / payload bit flip
     5: begin rx_pin_v <= 1; rx_expect_v <= 0; end                              // unexpected RX
     6: begin rx_pin_v <= 0; rx_expect_v <= 1; end                              // missing RX
     7: begin rd_v <= 1; rd_seq <= rcnt[15:0]; rcnt = rcnt + 1; end             // read of an unwritten slot
     8: begin wr_v <= 1; wr_observed_v <= 0; wr_seq <= wcnt[15:0]; wcnt = wcnt + 1; end   // observed-write dropped
     default: rx_expect_seq <= xcnt[15:0] + 16'd3;                              // rx identity slip
    endcase
    if (fi_kind == 3) phy_up <= 0;
   end
  end
  if (cyc == NCYC) begin
   $display("LINK_ACTIVITY epochs=%0d writes=%0d reads=%0d tx_frames=%0d rx_frames=%0d aborted_epochs=%0d injected=%0d",
            n_ep, n_wr, n_rd, n_tx, n_rx, n_ab, n_fi);
   if (bad == 0 && nc > 0 && n_tx > 1000 && n_rx > 1000 && n_ab > 10)
    $display("LINK_EQ PASS compared=%0d cycles=%0d", nc, cyc);
   else
    $display("LINK_EQ FAIL mismatches=%0d of %0d (tx %0d rx %0d aborted %0d)", bad, nc, n_tx, n_rx, n_ab);
   $finish;
  end
 end
 initial begin seed = 32'h0c011e2; lv = 0; for (i = 0; i < LOOP; i = i + 1) lf[i] = 0; for (i = 0; i < 64; i = i + 1) begin wr_age[i] = 0; rd_age[i] = -100; end
  wcnt = 0; rcnt = 0; xcnt = 0; pend = 0; ep_len = 1000; ep_age = 0; fi_kind = 0; fi_at = 0; end
endmodule
