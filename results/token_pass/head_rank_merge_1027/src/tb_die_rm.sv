`timescale 1ns/1ps
// TOK-ALL-16: HEAD die spine/chain path + RANK MERGE on the GENERATED die top (tools/die_plan/gen.py rtl of main
// die_plan s81_head; TOK-15 vehicle).  New vs TOK-15: the REAL ot_s81hd_mesh_ep_core (mesh0S / mesh7S / mesh7N) and the
// REAL ot_s81hd_serdes_link (ot_pdie_serdes) replace their stubs; the ctl driver issues the BEST records and runs the REAL
// rank merge.  One die is simulated; the pads of the TP4 mesh SerDes are looped back so that one die stands for its
// ring neighbours (all head dies are the same generated top, same compiled dates):
//   lk_ES0/ES1 tx -> lk_WS0/WS1 rx  (my east transmission == west peer's east transmission arriving at my west)
//   lk_WS0/WS1 tx -> lk_ES0/ES1 rx  (east peer)
//   lk_EN0/EN1 tx -> lk_EN0/EN1 rx  (diagonal peer, EN<->EN)
// Channel: K extra cycles on the PMA word (behavioural analog PMA + cable).  Standalone ot_pdie_serdes measured
// serdes coll tx -> far coll rx = 79 cycles at K 0 (tb_serdes_lat.sv); K = 172 makes the leaf-to-leaf hop D = 251,
// the model's tp_mesh hop (rack OPTION D full-KP4 cable hop, s81_head_die_model.py HOP_D).
module tb;
 parameter integer K = 172;
 reg ck = 0; always #0.4165 ck = ~ck;
 reg rst_n = 0, start = 0;
 wire [543:0] es0, es1, ws0, ws1, en0, en1;
 reg  [543:0] d_es0 [0:K-1], d_es1 [0:K-1], d_ws0 [0:K-1], d_ws1 [0:K-1], d_en0 [0:K-1], d_en1 [0:K-1];
 integer i;
 always @(posedge ck) begin
  d_es0[0] <= es0; d_es1[0] <= es1; d_ws0[0] <= ws0; d_ws1[0] <= ws1; d_en0[0] <= en0; d_en1[0] <= en1;
  for (i = 1; i < K; i = i + 1) begin
   d_es0[i] <= d_es0[i-1]; d_es1[i] <= d_es1[i-1]; d_ws0[i] <= d_ws0[i-1]; d_ws1[i] <= d_ws1[i-1]; d_en0[i] <= d_en0[i-1]; d_en1[i] <= d_en1[i-1];
  end
 end
 s81_head_top dut (.clk(ck), .rst_n(rst_n), .start(start),
  .lk_ES0_pma_tx(es0), .lk_ES1_pma_tx(es1), .lk_WS0_pma_tx(ws0), .lk_WS1_pma_tx(ws1), .lk_EN0_pma_tx(en0), .lk_EN1_pma_tx(en1),
  .lk_WS0_pma_rx(d_es0[K-1]), .lk_WS1_pma_rx(d_es1[K-1]), .lk_ES0_pma_rx(d_ws0[K-1]), .lk_ES1_pma_rx(d_ws1[K-1]),
  .lk_EN0_pma_rx(d_en0[K-1]), .lk_EN1_pma_rx(d_en1[K-1]),
  .lk_WS0_pma_rck(ck), .lk_WS1_pma_rck(ck), .lk_ES0_pma_rck(ck), .lk_ES1_pma_rck(ck), .lk_EN0_pma_rck(ck), .lk_EN1_pma_rck(ck));
 integer maxc;
 initial begin
  if (!$value$plusargs("MAXC=%d", maxc)) maxc = 12000;
  repeat (8) @(negedge ck); rst_n = 1; repeat (4) @(negedge ck); start = 1;
  repeat (maxc) @(negedge ck);
  $finish;
 end
endmodule
