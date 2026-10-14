// tb_vm_ring.sv: [vm8cp] shared ring-transport bench of the VM8 ring / relay tiles (vm_cp_rt, rt2, rb, rb2, rwa, rwb).
// The DUT is the EXACT routed tile module (no parameters), bound by ring_dut (generated per tile by run_vm_ring.sh from the
// lane table there, which is independent of the tile RTL).  Lanes: A = W->E (a_i -> a_o, WA bits), B = E->W (b_i -> b_o,
// WB bits, 0 = none), fork F = low WF bits of lane B dropped at a station face (rb2 rd, rt2 cfg; 0 = none).
// Checks (always on, both phases):
//   exact     every output bit == its lane input bit exactly ONE clock earlier (random, walking-one, then link traffic)
// Phase 2, one credit link per lane through the DUT (frame = valid, 8-bit station address, per-station sequence, global
// sequence, hashed payload on EVERY remaining bit; credits of lane A return on the top two bits of lane B through the
// same DUT and vice versa; a one-way tile takes its credit return on a one-flop bench wire):
//   order     per-station and global sequence numbers arrive consecutive (no loss, no duplicate, no reorder)
//   data      the whole received frame equals the frame regenerated from its header
//   addr      a valid beat carries one of the two station addresses; MAIN is taken at the lane output, STN at the fork
//             face when the tile has a fork of >= 57 bits (station drop), else at the lane output
//   credit    conservation under receiver back-pressure (stalled / slow / fast drain windows, per station): credits
//             held never exceed D, beats in flight and credits in flight stay within the measured two-edge latency,
//             receiver FIFOs never overflow, and after the drain every credit is home (no leak)
// Coverage refusal (a vacuous run FAILS): every output bit seen 0 and 1, the beat target reached on every link and
// station, sender starved of credit, FIFO full and credit 0 observed on every station of every link.
`timescale 1ns/1ps
`ifndef WA
 `define WA 2048
`endif
`ifndef WB
 `define WB 0
`endif
`ifndef WF
 `define WF 0
`endif

package ring_pkg;
  function automatic logic [2047:0] mkframe(input logic [7:0] dst, input logic [23:0] ds, input logic [23:0] gs, input int lane);
    logic [2047:0] f; logic [31:0] x;
    x = {gs, dst} ^ (32'h9E3779B9 * ({8'd0, ds} + 32'd1)) ^ (32'h85EBCA6B * (lane + 1));
    if (x == 0) x = 32'h1;
    for (int w = 0; w < 64; w++) begin x ^= x << 13; x ^= x >> 17; x ^= x << 5; f[w*32 +: 32] = x; end
    f[0] = 1'b1; f[8:1] = dst; f[32:9] = ds; f[56:33] = gs;
    return f;
  endfunction
  function automatic logic [2047:0] rnd();
    logic [2047:0] f;
    for (int w = 0; w < 64; w++) f[w*32 +: 32] = $urandom;
    return f;
  endfunction
endpackage

module ring_link #(parameter int F = 2046, parameter int FS = 2046, parameter int LANE = 0, parameter int D = 8) (
    input  logic ck, input logic run, input int unsigned beats,
    output logic [F-1:0] tx, input logic [F-1:0] rx, input logic [FS-1:0] srx,
    output logic [1:0] cr_tx, input logic [1:0] cr_rx,
    output int unsigned e_order, output int unsigned e_data, output int unsigned e_addr, output int unsigned e_credit,
    output int unsigned recv0, output int unsigned recv1, output int unsigned stall0, output int unsigned stall1,
    output int unsigned full0, output int unsigned full1, output int unsigned zero0, output int unsigned zero1,
    output int unsigned gsent, output logic done);
  import ring_pkg::*;
  localparam logic [7:0] A0 = 8'hA5, A1 = 8'h5A;
  int unsigned sent[2], recv[2], popd[2], crx[2], stall[2], fulls[2], zeros[2];
  int cred[2]; int fifo[2];
  int unsigned grecv, cyc, quiet;
  initial begin
    for (int r = 0; r < 2; r++) begin sent[r]=0; recv[r]=0; popd[r]=0; crx[r]=0; stall[r]=0; fulls[r]=0; zeros[r]=0; cred[r]=D; fifo[r]=0; end
    grecv=0; gsent=0; cyc=0; quiet=0; e_order=0; e_data=0; e_addr=0; e_credit=0; tx='0; cr_tx='0; done=0;
  end
  assign recv0=recv[0]; assign recv1=recv[1]; assign stall0=stall[0]; assign stall1=stall[1];
  assign full0=fulls[0]; assign full1=fulls[1]; assign zero0=zeros[0]; assign zero1=zeros[1];
  logic [2047:0] t, g; logic [7:0] dst; int d; int unsigned ph; int pr; logic mainhit, stnhit;
  always @(posedge ck) begin
    cyc <= cyc + 1;
    // ---- credits home (before the send decision, as a registered sender would see them next edge) ----
    for (int r = 0; r < 2; r++) if (run && cr_rx[r]) begin
      crx[r] = crx[r] + 1;
      if (cred[r] >= D) e_credit <= e_credit + 1; else cred[r] = cred[r] + 1;     // more credits than the receiver owns
    end
    // ---- sender ----
    t = rnd(); t[0] = 1'b0;                                                          // idle: garbage, not valid
    if (run && gsent < beats && ($urandom % 100) < 85) begin
      d = int'($urandom & 1);
      if (cred[d] > 0) begin
        t = mkframe(d == 0 ? A0 : A1, sent[d][23:0], gsent[23:0], LANE);
        cred[d] = cred[d] - 1; sent[d] = sent[d] + 1; gsent = gsent + 1;
        if (cred[d] == 0) zeros[d] = zeros[d] + 1;
      end else stall[d] = stall[d] + 1;                                              // back-pressure reached the sender
    end
    tx <= t[F-1:0];
    // ---- receivers: MAIN at the lane output, STN at the station face ----
    mainhit = run && rx[0] && rx[8:1] == A0;
    stnhit  = run && srx[0] && srx[8:1] == A1;
    if (run && rx[0] && rx[8:1] != A0 && rx[8:1] != A1) e_addr <= e_addr + 1;        // beat for no station
    if (run && srx[0] && srx[8:1] != A0 && srx[8:1] != A1) e_addr <= e_addr + 1;
    if (mainhit && stnhit) e_addr <= e_addr + 1;                                     // one beat, two owners
    if (mainhit) begin
      g = mkframe(rx[8:1], rx[32:9], rx[56:33], LANE);
      if (rx !== g[F-1:0]) e_data <= e_data + 1;
      if (rx[32:9] !== recv[0][23:0] || rx[56:33] !== grecv[23:0]) e_order <= e_order + 1;
      recv[0] = recv[0] + 1; grecv = grecv + 1;
      if (fifo[0] >= D) e_credit <= e_credit + 1; else fifo[0] = fifo[0] + 1;       // overflow: sent without a credit
      if (fifo[0] == D) fulls[0] = fulls[0] + 1;
    end
    if (stnhit) begin
      g = mkframe(srx[8:1], srx[32:9], srx[56:33], LANE);
      if (srx !== g[FS-1:0]) e_data <= e_data + 1;
      if (srx[32:9] !== recv[1][23:0] || srx[56:33] !== grecv[23:0]) e_order <= e_order + 1;
      recv[1] = recv[1] + 1; grecv = grecv + 1;
      if (fifo[1] >= D) e_credit <= e_credit + 1; else fifo[1] = fifo[1] + 1;
      if (fifo[1] == D) fulls[1] = fulls[1] + 1;
    end
    // ---- drain under back-pressure: per-station windows of 512 edges: fast / slow / stalled / half ----
    for (int r = 0; r < 2; r++) begin
      ph = ((cyc >> 9) + (r == 1 ? 32'd2 : 32'd0) + (LANE == 1 ? 32'd1 : 32'd0)) % 4;
      pr = (gsent >= beats) ? 100 : (ph == 0 ? 90 : ph == 1 ? 8 : ph == 2 ? 0 : 50);
      if (run && fifo[r] > 0 && int'($urandom % 100) < pr) begin fifo[r] = fifo[r] - 1; popd[r] = popd[r] + 1; cr_tx[r] <= 1'b1; end
      else cr_tx[r] <= 1'b0;
    end
    // ---- conservation: D = credits held + beats in flight + FIFO + credits in flight, the flights bounded by latency ----
    for (int r = 0; r < 2; r++) if (run) begin
      if (cred[r] < 0 || cred[r] > D) e_credit <= e_credit + 1;
      if (sent[r] < recv[r] || sent[r] - recv[r] > 2) e_credit <= e_credit + 1;      // beat lost or invented
      if (popd[r] < crx[r] || popd[r] - crx[r] > 2) e_credit <= e_credit + 1;        // credit lost, stale or invented
      if (cred[r] + int'(sent[r] - recv[r]) + fifo[r] + int'(popd[r] - crx[r]) != D) e_credit <= e_credit + 1;
    end
    if (run && gsent >= beats && cred[0] == D && cred[1] == D && fifo[0] == 0 && fifo[1] == 0 && sent[0] == recv[0]
        && sent[1] == recv[1] && popd[0] == crx[0] && popd[1] == crx[1]) quiet <= quiet + 1; else quiet <= 0;
    done <= (quiet >= 8);
  end
endmodule

module tb_vm_ring;
  import ring_pkg::*;
  localparam int WA = `WA, WB = `WB, WF = `WF;
  localparam int WBX = WB > 0 ? WB : 1, WFX = WF > 0 ? WF : 1;
  localparam int FA = WB > 0 ? WA - 2 : WA;              // lane A frame (top two bits = lane B's credit return)
  localparam int FB = WB > 0 ? WB - 2 : 64;              // lane B frame (top two bits = lane A's credit return)
  localparam int FSB = WF >= 57 ? WF : FB;               // station face of lane B: the fork when it carries the header
  localparam int D = 8, N1 = 4096;
  logic ck = 0; always #1 ck = ~ck;
  logic [WA-1:0] a_i = '0, a_o, a_d1 = '0, p1a = '0; logic [WBX-1:0] b_i = '0, b_o, b_d1 = '0, p1b = '0; logic [WFX-1:0] f_o;
  ring_dut dut (.ck(ck), .a_i(a_i), .a_o(a_o), .b_i(b_i), .b_o(b_o), .f_o(f_o));

  int unsigned beats = 20000, cyc = 0, e_exact = 0, cfg_ones = 0, idle = 0; logic run = 0; string tile = "?";
  logic [WA-1:0] a0 = '0, a1 = '0; logic [WBX-1:0] b0 = '0, b1 = '0; logic [WFX-1:0] f0 = '0, f1 = '0;
  logic [FA-1:0] txa; logic [1:0] cra_tx, cra_rx, crb_tx, crb_rx;
  int unsigned ao, ad, aa, ac, ar0, ar1, as0, as1, af0, af1, az0, az1, ags; logic adone;
  int unsigned bo = 0, bd = 0, ba = 0, bc = 0, br0 = 0, br1 = 0, bs0 = 0, bs1 = 0, bf0 = 0, bf1 = 0, bz0 = 0, bz1 = 0, bgs = 0; logic bdone = 1;
  ring_link #(.F(FA), .FS(FA), .LANE(0), .D(D)) la (.ck, .run, .beats, .tx(txa), .rx(a_o[FA-1:0]), .srx(a_o[FA-1:0]),
      .cr_tx(cra_tx), .cr_rx(cra_rx), .e_order(ao), .e_data(ad), .e_addr(aa), .e_credit(ac), .recv0(ar0), .recv1(ar1),
      .stall0(as0), .stall1(as1), .full0(af0), .full1(af1), .zero0(az0), .zero1(az1), .gsent(ags), .done(adone));
  generate if (WB > 0) begin : g_b
    logic [FB-1:0] txb; logic [FSB-1:0] srxb;
    if (WF >= 57) begin : g_fork assign srxb = f_o[FSB-1:0]; end else begin : g_nofork assign srxb = b_o[FSB-1:0]; end
    ring_link #(.F(FB), .FS(FSB), .LANE(1), .D(D)) lb (.ck, .run, .beats, .tx(txb), .rx(b_o[FB-1:0]), .srx(srxb),
      .cr_tx(crb_tx), .cr_rx(crb_rx), .e_order(bo), .e_data(bd), .e_addr(ba), .e_credit(bc), .recv0(br0), .recv1(br1),
      .stall0(bs0), .stall1(bs1), .full0(bf0), .full1(bf1), .zero0(bz0), .zero1(bz1), .gsent(bgs), .done(bdone));
    always_comb begin
      a_i = run ? {crb_tx, txa} : p1a;                      // lane B's credits ride lane A through the DUT
      b_i = run ? {cra_tx, txb} : p1b;                      // lane A's credits ride lane B through the DUT
    end
    assign cra_rx = run ? b_o[WB-1:WB-2] : 2'b0;
    assign crb_rx = run ? a_o[WA-1:WA-2] : 2'b0;
  end else begin : g_oneway
    logic [1:0] crw = '0; always @(posedge ck) crw <= cra_tx;   // one-way tile: credit return on a one-flop bench wire
    always_comb begin a_i = run ? txa : p1a; b_i = '0; end
    assign cra_rx = run ? crw : 2'b0; assign crb_tx = '0; assign crb_rx = '0;
  end endgenerate

  int unsigned p1len;
  logic [2047:0] ra, rb;
  initial begin
    void'($value$plusargs("beats=%d", beats)); void'($value$plusargs("tile=%s", tile));
    p1len = N1 + WA + WB + 8;
  end
  int ntog; string why;
  always @(posedge ck) begin
    cyc <= cyc + 1;
    // phase 1 stimulus: random, then walking one on lane A (B zero), then walking one on lane B (A zero)
    ra = rnd(); rb = rnd();
    if (cyc < N1) begin p1a <= ra[WA-1:0]; p1b <= rb[WBX-1:0]; end
    else if (cyc < N1 + WA) begin p1a <= WA'(1) << (cyc - N1); p1b <= '0; end
    else if (cyc < N1 + WA + WB) begin p1a <= '0; p1b <= WBX'(1) << (cyc - N1 - WA); end
    else begin p1a <= '0; p1b <= '0; end
    if (cyc == p1len) run <= 1;
    // exactness, always on: output == input one clock earlier (first compare once the pipeline holds driven data)
    a_d1 <= a_i; b_d1 <= b_i;
    if (cyc >= 3) begin
      if (a_o !== a_d1) e_exact <= e_exact + 1;
      if (WB > 0 && b_o !== b_d1) e_exact <= e_exact + 1;
      if (WF > 0 && f_o !== b_d1[WFX-1:0]) e_exact <= e_exact + 1;
      a0 <= a0 | ~a_o; a1 <= a1 | a_o;
      if (WB > 0) begin b0 <= b0 | ~b_o; b1 <= b1 | b_o; end
      if (WF > 0) begin f0 <= f0 | ~f_o; f1 <= f1 | f_o; end
    end
    if (run && WF > 0 && WF < 57 && f_o[0]) cfg_ones <= cfg_ones + 1;   // narrow fork (cfg): one pulse per lane-B beat
    if (run) idle <= idle + 1;
    if ((run && adone && bdone) || (run && idle > 40 * beats + 400000)) begin
      ntog = $countones(a0 & a1) + (WB > 0 ? $countones(b0 & b1) : 0) + (WF > 0 ? $countones(f0 & f1) : 0);
      why = "";
      if (e_exact != 0) why = {why, " exact"};
      if (ao + bo != 0) why = {why, " order"};
      if (ad + bd != 0) why = {why, " data"};
      if (aa + ba != 0) why = {why, " addr"};
      if (ac + bc != 0) why = {why, " credit"};
      if (!(adone && bdone)) why = {why, " leak_or_deadlock"};
      if (WF > 0 && WF < 57 && cfg_ones != bgs) why = {why, " fork"};
      // coverage refusal: a run that did not exercise the transport is not a pass
      if (ntog != WA + WB + WF) why = {why, " cov_toggle"};
      if (beats < 20000 || ags != beats || ar0 < beats / 4 || ar1 < beats / 4) why = {why, " cov_beats_A"};
      if (as0 < 100 || as1 < 100 || af0 == 0 || af1 == 0 || az0 == 0 || az1 == 0) why = {why, " cov_backpressure_A"};
      if (WB > 0) begin
        if (bgs != beats || br0 < beats / 4 || br1 < beats / 4) why = {why, " cov_beats_B"};
        if (bs0 < 100 || bs1 < 100 || bf0 == 0 || bf1 == 0 || bz0 == 0 || bz1 == 0) why = {why, " cov_backpressure_B"};
      end
      $display("VM_RING tile=%s WA=%0d WB=%0d WF=%0d cycles=%0d beatsA=%0d(main %0d stn %0d) beatsB=%0d(main %0d stn %0d) exact_err=%0d order_err=%0d data_err=%0d addr_err=%0d credit_err=%0d toggled=%0d/%0d stallA=%0d/%0d fullA=%0d/%0d zeroA=%0d/%0d stallB=%0d/%0d fullB=%0d/%0d zeroB=%0d/%0d cfg=%0d",
               tile, WA, WB, WF, cyc, ags, ar0, ar1, bgs, br0, br1, e_exact, ao + bo, ad + bd, aa + ba, ac + bc, ntog, WA + WB + WF,
               as0, as1, af0, af1, az0, az1, bs0, bs1, bf0, bf1, bz0, bz1, cfg_ones);
      if (why == "") $display("VM_RING_RUN PASS tile=%s beats=%0d", tile, ar0 + ar1 + br0 + br1);
      else $display("VM_RING_RUN FAIL tile=%s:%s", tile, why);
      $finish;
    end
  end
endmodule
