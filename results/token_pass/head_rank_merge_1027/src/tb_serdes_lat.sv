`timescale 1ns/1ps
// TOK-ALL-16: ot_pdie_serdes A -> pads (+K channel cycles) -> ot_pdie_serdes B.  Latency of tagged beats coll tx -> rx.
module tb_serdes_lat;
 parameter integer K = 0;
 reg ck = 0; always #0.5 ck = ~ck;
 reg rst = 0;
 reg [511:0] tx; wire [511:0] rxa, rxb; wire [1:0] sta, stb;
 wire [543:0] pa, pb; wire tca, tcb;
 reg [543:0] dl [0:(K>0?K:1)-1]; integer i;
 always @(posedge ck) begin dl[0] <= pa; for (i = 1; i < K; i = i + 1) dl[i] <= dl[i-1]; end
 wire [543:0] pab = (K == 0) ? pa : dl[K-1];
 ot_pdie_serdes A (.clk(ck), .rst(rst), .tx(tx), .rx(rxa), .st(sta), .pma_tx(pa), .pma_tck(tca), .pma_rx(544'd0), .pma_rck(ck));
 ot_pdie_serdes B (.clk(ck), .rst(rst), .tx(512'd2), .rx(rxb), .st(stb), .pma_tx(pb), .pma_tck(tcb), .pma_rx(pab), .pma_rck(ck));
 integer c = 0, sent [0:4095], mn = 99999, mx = 0, n = 0, v;
 always @(negedge ck) begin
  c = c + 1; rst = (c > 4);
  tx = 512'd2;
  if (c >= 200 && c < 1200 && (c % 7) == 0) begin tx = {448'd0, 32'(c), 32'hA5A5_0000}; sent[c % 4096] = c; end
  if (rxb[31:0] == 32'hA5A5_0000) begin v = c - rxb[63:32]; n = n + 1; if (v < mn) mn = v; if (v > mx) mx = v; end
  if (c == 2000) begin $display("SERDES_LAT K%0d beats%0d min%0d max%0d live%0d", K, n, mn, mx, stb[1]); $finish; end
 end
endmodule
