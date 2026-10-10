`timescale 1ns/1ps
// hardcore-1010 group B (2026-10-10): transaction-level exactness bench of the ot_hcoll_port FALLBACK (FB 1, PAYLOAD_ECC 0,
// FACE_CK 0) against a golden transaction model, with the unmodified port (FB 0) run on the same stimulus as the rate
// reference.  Checks, every cycle:
//   TX: every ph_tx flit is the oldest outstanding word of the partial OR the result queue (per-queue order, no loss,
//       no duplicate, no invention); cumulative TX <= SWCRED + cumulative switch credit returns (never over-issue);
//   RX: rb_d is exactly the ph_rx stream in order; cumulative rb_v <= K + cumulative rb_cr (consumer credit);
//   end: every pushed / received word delivered by both ports, fault 0, FB delivered within ref + 8 cycles per phase
//        (rate unchanged) and the burst phase streams at one flit per cycle.
// Phases: random mixed traffic; a long credit drought (switch credit exhausted, returns resumed); a full-rate burst;
// > 2 x 128 RX words (both receive-buffer banks).  Mutants: OT_HCOLL_FB_MUT_SLICE / _CREDIT / _BS must FAIL.
module tb_port_fb;
  localparam integer W = 545, SWCRED = 256, K = 8;
  reg clk = 0; always #0.416666667 clk = ~clk;
  reg rst_n = 0;
  reg qp = 0, qr = 0, cr = 0, rx = 0, rbc = 0;
  reg [W-1:0] qpd = '0, qrd = '0, rxd = '0;
  wire txv, rbv, fault, stall, ce; wire [1:0] drops; wire [W-1:0] txd, rbd;
  wire txv0, rbv0, fault0, stall0, ce0; wire [1:0] drops0; wire [W-1:0] txd0, rbd0;
  ot_hcoll_port #(.FB(1)) dut (.clk(clk),.ckf(clk),.ckt(clk),.rst_n(rst_n),.qp_push(qp),.qp_din(qpd),.qr_push(qr),.qr_din(qrd),
    .sw_cr_ret(cr),.ph_tx_v(txv),.ph_tx_flit(txd),.ph_rx_v(rx),.ph_rx_flit(rxd),.rb_v(rbv),.rb_d(rbd),.rb_cr(rbc),
    .stall(stall),.ecc_ce(ce),.rx_ecc_drop(drops),.fault(fault));
  ot_hcoll_port #(.FB(0)) ref0 (.clk(clk),.ckf(clk),.ckt(clk),.rst_n(rst_n),.qp_push(qp),.qp_din(qpd),.qr_push(qr),.qr_din(qrd),
    .sw_cr_ret(cr),.ph_tx_v(txv0),.ph_tx_flit(txd0),.ph_rx_v(rx),.ph_rx_flit(rxd),.rb_v(rbv0),.rb_d(rbd0),.rb_cr(rbc),
    .stall(stall0),.ecc_ce(ce0),.rx_ecc_drop(drops0),.fault(fault0));

  // golden transaction model
  reg [W-1:0] qpe [$]; reg [W-1:0] qre [$]; reg [W-1:0] rxe [$];
  reg [W-1:0] qpe0 [$]; reg [W-1:0] qre0 [$]; reg [W-1:0] rxe0 [$];
  integer ntx = 0, ncr = 0, nrb = 0, nrbc = 0, ntx0 = 0, nrb0 = 0, nrbc0 = 0, checks = 0, seq = 0;
  integer burst_first = -1, burst_last = -1, cyc = 0;
  reg burst_mon = 0;
  reg [W-1:0] dmy;
  integer burst_cnt = 0;

  function automatic [W-1:0] word(input integer q, input integer n);
    reg [W-1:0] r; integer i;
    begin
      r = '0;
      for (i = 0; i < W; i = i + 32) r = r ^ ({{(W-32){1'b0}}, $urandom} << i);
      r[W-1 -: 2] = q[1:0]; r[31:0] = n;
      word = r;
    end
  endfunction

  always @(posedge clk) if (rst_n) begin
    cyc <= cyc + 1;
    // ---- FB port ----
    if (txv) begin
      if (qpe.size() && txd === qpe[0]) dmy = qpe.pop_front();
      else if (qre.size() && txd === qre[0]) dmy = qre.pop_front();
      else $fatal(1, "FB TX flit %0d is not the oldest word of either queue (seq %0h)", ntx, txd[31:0]);
      ntx = ntx + 1; checks = checks + 1;
      if (burst_mon) burst_cnt = burst_cnt + 1;
    end
    if (cr) ncr = ncr + 1;
    if (ntx > SWCRED + ncr) $fatal(1, "FB over-issue: %0d TX flits against %0d switch credits", ntx, SWCRED + ncr);
    if (rbv) begin
      if (!rxe.size() || rbd !== rxe[0]) $fatal(1, "FB RX word %0d mismatch / invented", nrb);
      dmy = rxe.pop_front(); nrb = nrb + 1; checks = checks + 1;
    end
    if (rbc) nrbc = nrbc + 1;
    if (nrb > K + nrbc) $fatal(1, "FB consumer over-publication %0d > %0d", nrb, K + nrbc);
    if (fault) $fatal(1, "FB fault");
    // ---- reference port (FB 0) ----
    if (txv0) begin
      if (qpe0.size() && txd0 === qpe0[0]) dmy = qpe0.pop_front();
      else if (qre0.size() && txd0 === qre0[0]) dmy = qre0.pop_front();
      else $fatal(1, "REF TX mismatch");
      ntx0 = ntx0 + 1;
    end
    if (rbv0) begin
      if (!rxe0.size() || rbd0 !== rxe0[0]) $fatal(1, "REF RX mismatch");
      dmy = rxe0.pop_front(); nrb0 = nrb0 + 1;
    end
    if (fault0) $fatal(1, "REF fault");
  end

  // stimulus helpers (drive on negedge; record expectations at the same time)
  integer outstanding_q;
  task automatic step(input integer pq, input integer pr, input integer pc, input integer px, input integer pk);
    begin
      @(negedge clk);
      outstanding_q = qpe.size() + qre.size();
      qp = ($urandom % 100) < pq && qpe.size() < 100 && qpe0.size() < 100;
      qr = ($urandom % 100) < pr && qre.size() < 100 && qre0.size() < 100;
      // the switch returns a credit only for a flit it holds (both ports' TX counts bound it)
      cr = ($urandom % 100) < pc && ncr < ntx && ncr < ntx0;
      // the switch sends only into a free receive-buffer slot of both ports (pool 2^RXAW = 256, margin 16)
      rx = ($urandom % 100) < px && (rxe.size() < 240) && (rxe0.size() < 240);
      rbc = ($urandom % 100) < pk && nrbc < nrb && nrbc0 < nrb0;
      if (rbc) nrbc0 = nrbc0 + 1;
      if (qp) begin qpd = word(0, seq); seq = seq + 1; qpe.push_back(qpd); qpe0.push_back(qpd); end
      if (qr) begin qrd = word(1, seq); seq = seq + 1; qre.push_back(qrd); qre0.push_back(qrd); end
      if (rx) begin rxd = word(2, seq); seq = seq + 1; rxe.push_back(rxd); rxe0.push_back(rxd); end
    end
  endtask
  task automatic drain(input string what);
    integer n, t_fb, t_ref;
    begin
      n = 0; t_fb = -1; t_ref = -1;
      while ((qpe.size() || qre.size() || rxe.size() || qpe0.size() || qre0.size() || rxe0.size()) && n < 4000) begin
        step(0, 0, 60, 0, 60);
        if (t_fb < 0 && !(qpe.size() || qre.size() || rxe.size())) t_fb = n;
        if (t_ref < 0 && !(qpe0.size() || qre0.size() || rxe0.size())) t_ref = n;
        n = n + 1;
      end
      if (t_fb < 0) t_fb = n; if (t_ref < 0) t_ref = n;
      if (qpe.size() || qre.size() || rxe.size()) $fatal(1, "%s: FB lost words (qp %0d qr %0d rx %0d)", what, qpe.size(), qre.size(), rxe.size());
      if (qpe0.size() || qre0.size() || rxe0.size()) $fatal(1, "%s: REF lost words", what);
      if (t_fb > t_ref + 8) $fatal(1, "%s: FB drained %0d cycles after the reference (rate loss)", what, t_fb - t_ref);
      $display("%s drained: FB %0d / REF %0d cycles", what, t_fb, t_ref);
    end
  endtask

  initial begin
    repeat (4) @(negedge clk); rst_n = 1;
    // phase 1: random mixed traffic
    repeat (3000) step(35, 25, 50, 45, 55);
    drain("mixed");
    // phase 2: credit drought (no switch credit returns until both ports exhaust the 256 credits), then resume
    repeat (900) step(45, 30, 0, 20, 70);
    if (ntx != SWCRED + ncr) $fatal(1, "drought: FB issued %0d, expected the credit limit %0d", ntx, SWCRED + ncr);
    drain("drought");
    // phase 3: full-rate burst on the partial queue (plenty of credit): one flit per cycle in steady state
    repeat (60) step(100, 0, 100, 0, 100);
    burst_mon = 1; burst_cnt = 0;
    repeat (40) step(100, 0, 100, 0, 100);
    burst_mon = 0;
    if (burst_cnt < 39) $fatal(1, "burst: FB streamed %0d flits in 40 cycles (< 1 per cycle)", burst_cnt);
    drain("burst");
    // phase 4: RX-heavy (crosses both 128-entry receive-buffer banks several times) with a slow consumer
    repeat (2500) step(10, 10, 80, 90, 35);
    drain("rx");
    if (nrb < 600) $fatal(1, "rx phase too short: %0d", nrb);
    $display("HCOLL_PORT_FB PASS tx=%0d rx=%0d credits=%0d checks=%0d", ntx, nrb, ncr, checks);
    $finish;
  end
endmodule
