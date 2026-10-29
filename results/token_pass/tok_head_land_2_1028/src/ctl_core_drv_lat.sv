`timescale 1ns/1ps
`default_nettype none
// TOK-ALL-15 bench driver in place of the ctl LEAF ot_s81hd_ctl_core (same ports as main). The generated ctl
// partition wrapper (boundary flops, ONE reset/START root, wavefront) stays unchanged around it.  x_o is driven
// from a register exactly in the ot_s81hd_ctl_hsf0_static sno_q format: one go beat {flt0, null best: bits
// FF800000, row 1FFFF, rv=go, xv, go}, then x slice m at go+5+m (SK 11: m < 8192+7*11+8), xa K0..4095 / xb
// K4096..5119 from +DIR.  b_i (the wrapper's in-flop q of spine sp0.b_o) is monitored: first rv per position.
// Measured: core x_o go edge -> core b_i result edge (the ctl-internal hsf0 issue/final compare stay in the
// composed rows).  Plusargs: +DIR +GO_AT (cycles after start) +NPOS +GAP +EXP_ROW +EXP_BITS +XSHIFT (control).
module ot_s81hd_ctl_core #(parameter integer SK=11,parameter integer MUT_DRAFT_EARLY=0)(
 input wire ck,rst_n,start_i,lep_fault_i, input wire[10:0]lw_i,
 input wire[1103:0]lepk_i0, output wire[1103:0]lepk_o0,
 output wire lepf_o0, output wire[44:0]unit_o0,input wire[31:0]ctrl_i0,
 output wire[564:0]x_o,input wire[564:0]b_i,
 output wire[276:0]h_tx_o,input wire[275:0]h_rx_i,
 output wire[63:0]a_tx_o,b7_tx_o,n_tx_o,input wire[63:0]a_rx_i,b7_rx_i,n_rx_i
);
 assign lepk_o0='0; assign lepf_o0=1'b0; assign unit_o0='0; assign h_tx_o='0;
 assign a_tx_o='0; assign b7_tx_o='0; assign n_tx_o='0;
 localparam integer NX = 8192 + 7*SK + 8;
 reg [255:0] xa [0:255]; reg [255:0] xb [0:63];
 reg [564:0] xq; assign x_o = xq;
 string dir; integer go_at, npos, gap, exp_row, xshift; reg [31:0] exp_bits;
 // TOK-HEAD-LAND-2 (COORD 10-28 22:37 ASK 4): exact GO->result latency of record, FAIL on any other value
 // (the only catch for an in-window K+1).  +EXP_LAT=-1 disables (diagnostic only).
 integer exp_lat;
 integer cyc = 0, t = -1, pos = 0, nres = 0, bad = 0, go_cyc [0:15];
 initial begin
  if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR");
  if (!$value$plusargs("GO_AT=%d", go_at)) go_at = 400;
  if (!$value$plusargs("NPOS=%d", npos)) npos = 1;
  if (!$value$plusargs("GAP=%d", gap)) gap = 10357;
  if (!$value$plusargs("EXP_ROW=%d", exp_row)) exp_row = 21946;
  if (!$value$plusargs("EXP_BITS=%h", exp_bits)) exp_bits = 32'h4173a558;
  if (!$value$plusargs("XSHIFT=%d", xshift)) xshift = 0;
  if (!$value$plusargs("EXP_LAT=%d", exp_lat)) exp_lat = 8780;
  $readmemh({dir, "/xa.hex"}, xa); $readmemh({dir, "/xb.hex"}, xb);
 end
 reg run = 1'b0;
 always @(posedge ck or negedge rst_n)
  if (!rst_n) begin run <= 1'b0; cyc <= 0; t <= -1; pos <= 0; xq <= '0; end
  else begin
   if (start_i) run <= 1'b1;
   if (run) cyc <= cyc + 1;
   xq <= '0;
   if (run && pos < npos && cyc == go_at + pos * gap) begin
    t <= 1; go_cyc[pos] = cyc + 1;
    xq[512] <= 1'b1; xq[513] <= 1'b1; xq[514] <= 1'b1; xq[531:515] <= 17'h1FFFF; xq[563:532] <= 32'hFF800000; xq[564] <= 1'b0;
   end else if (t >= 1) begin
    t <= (t - 5 + 1 >= NX) ? -1 : t + 1;
    xq[513] <= 1'b1;
    if (t >= 5) begin xq[255:0] <= xa[(t - 5 + xshift) % 256]; xq[511:256] <= xb[(t - 5) % 64]; end
    if (t - 5 + 1 >= NX) pos <= pos + 1;
   end
  end
 // result monitor: b_i rv (one result per position from the spine root spr)
 always @(posedge ck) if (rst_n && run && b_i[514]) begin
  $display("DIE_SPINE_RESULT pos%0d row%0d bits%08h flt%0d go_to_result%0d", nres, b_i[531:515], b_i[563:532], b_i[564], cyc - go_cyc[nres]);
  if (b_i[531:515] !== exp_row[16:0] || b_i[563:532] !== exp_bits || b_i[564]) begin bad++; $display("DIE_SPINE_MISMATCH pos%0d", nres); end
  if (exp_lat >= 0 && cyc - go_cyc[nres] != exp_lat) begin bad++; $display("DIE_SPINE_LATENCY_MISMATCH pos%0d go_to_result%0d exp%0d", nres, cyc - go_cyc[nres], exp_lat); end
  nres++;
 end
 final begin
  if (nres == npos && bad == 0) $display("DIE_SPINE PASS positions%0d exp_lat%0d", npos, exp_lat);
  else $display("DIE_SPINE FAIL results%0d of%0d bad%0d", nres, npos, bad);
 end
endmodule
`default_nettype wire
