`timescale 1ps/1fs
`default_nettype none
// Chain bench of hfd_att_su_relay: N relays in series (the longest R25GQ bus) against a cycle-exact N-deep reference.
// Random valid / payload, back-to-back bursts and gaps, a mid-run reset (valid must flush, the chain must restart).
// DENSE (tput-map-1011 F3): valid every cycle outside the reset window (production-shape dense stream); MUT=1 drops
// the relay register (wire through) so the latency/reference check must FAIL.
// PASS: every output cycle equals the reference (valid always; payload when valid), N cycles latency, no lost beat.
module tb_hfd_att_su_relay_dense;
  parameter integer N = 8;
  parameter integer CYC = 20000;
  parameter integer DENSE = 1;
  reg ck = 1'b0;
  always #416 ck = ~ck;
  reg rst = 1'b0;
  reg [528:0] in = 529'd0;
  wire [528:0] ch [0:N];
  assign ch[0] = in;
  genvar g;
  generate for (g = 0; g < N; g = g + 1) begin : gr
`ifdef MUT
    if (g == N - 1) begin : wire_through assign ch[g+1] = ch[g]; end else
`endif
    hfd_att_su_relay u (.ck(ck), .rst(rst), .i(ch[g]), .o(ch[g+1]));
  end endgenerate
  reg [528:0] ref_q [0:N-1];
  integer act = 0;
  integer k, cyc = 0, nin = 0, nout = 0, bad = 0, sync = 0;
  reg [31:0] lfsr = 32'hace1;
  function automatic [31:0] nx(input [31:0] x); nx = {x[30:0], x[31] ^ x[21] ^ x[1] ^ x[0]}; endfunction
  always @(posedge ck) begin
    // reference: N-deep pipe, valid cleared while the relays' synchronised reset is low (2 cycles after release)
    for (k = N - 1; k > 0; k = k - 1) ref_q[k] <= ref_q[k-1];
    ref_q[0] <= in;
    if (!rst || sync < 2) for (k = 0; k < N; k = k + 1) ref_q[k][0] <= 1'b0;
  end
  always @(posedge ck) sync <= rst ? (sync < 2 ? sync + 1 : sync) : 0;
  always @(negedge ck) begin
    cyc = cyc + 1;
    if (rst && sync >= 2) begin
      if (ch[N][0] !== ref_q[N-1][0] || (ch[N][0] && ch[N][528:1] !== ref_q[N-1][528:1])) begin
        bad = bad + 1;
        if (bad < 4) $display("MISMATCH cyc=%0d v %b/%b d0 %h/%h", cyc, ch[N][0], ref_q[N-1][0], ch[N][32:1], ref_q[N-1][32:1]);
      end
      if (ch[N][0]) nout = nout + 1;
      act = act + 1;
    end
    lfsr = nx(lfsr);
    in[0] = rst && (DENSE ? 1'b1 : (cyc % 997 < 300 ? 1'b1 : lfsr[3:0] < 4'd9));
    for (k = 0; k < 17; k = k + 1) begin lfsr = nx(lfsr); in[1 + 32*k +: 32] = lfsr; end
    if (in[0]) nin = nin + 1;
    if (cyc == 10) rst = 1'b1;
    if (cyc == CYC / 2) rst = 1'b0;          // mid-run reset: in-flight beats are dropped by both
    if (cyc == CYC / 2 + 5) rst = 1'b1;
    if (cyc == CYC) begin
      $display("RELAYCHAIN_DENSE N=%0d active_cycles=%0d in=%0d out=%0d II_x1000=%0d", N, act, nin, nout, act*1000/(nout>0?nout:1));
      $display("RELAYCHAIN N=%0d cycles=%0d in=%0d out=%0d mismatches=%0d latency=%0d %s", N, CYC, nin, nout, bad, N,
               (bad == 0 && nout > CYC / 3) ? "RELAY_PASS" : "RELAY_FAIL");
      $finish;
    end
  end
endmodule
`default_nettype wire
