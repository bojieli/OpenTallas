// EQ bench: ser -> P-stage lane pipe -> deser  ==  parallel pipe of (1 + P + 1) + (N-1) stages, cycle-exact.
// Random words, random gaps >= N (static schedule). Negative controls: -DNEG_SWAP (beat order) and -DNEG_LAT (reference N-2).
module tb;
  parameter int W = 2745, N = 4, P = 3, WORDS = 3000;
  localparam int S = (W + N - 1) / N, B = (N > 1) ? $clog2(N) : 1;
`ifdef NEG_LAT
  localparam int D = 1 + P + 1 + (N - 2);
`else
  localparam int D = 1 + P + 1 + (N - 1);
`endif
  logic clk = 0, rst_n = 0; always #1 clk = ~clk;
  logic in_valid; logic [W-1:0] in_word;
  logic lv; logic [B-1:0] lb; logic [S-1:0] ld; logic ovr;
  logic pv [1:P]; logic [B-1:0] pb [1:P]; logic [S-1:0] pd [1:P];
  logic ov; logic [W-1:0] ow;
  logic rv [1:D]; logic [W-1:0] rw [1:D];
  ot_lane_ser   #(.W(W), .N(N)) u_s (.clk, .rst_n, .in_valid, .in_word, .lane_valid(lv), .lane_beat(lb), .lane_data(ld), .overrun(ovr));
  always @(posedge clk) begin
    for (int i = P; i > 1; i--) begin pv[i] <= rst_n ? pv[i-1] : 1'b0; pb[i] <= pb[i-1]; pd[i] <= pd[i-1]; end
    pv[1] <= rst_n ? lv : 1'b0; pb[1] <= lb; pd[1] <= ld;
  end
  ot_lane_deser #(.W(W), .N(N)) u_d (.clk, .rst_n, .lane_valid(pv[P]), .lane_beat(pb[P]), .lane_data(pd[P]), .out_valid(ov), .out_word(ow));
  always @(posedge clk) begin
    for (int i = D; i > 1; i--) begin rv[i] <= rst_n ? rv[i-1] : 1'b0; rw[i] <= rw[i-1]; end
    rv[1] <= rst_n ? in_valid : 1'b0; rw[1] <= in_word;
  end
  int err = 0, nout = 0, gap = 0, sent = 0;
  function automatic logic [W-1:0] rnd(); logic [W-1:0] x; for (int k = 0; k < W; k += 32) x[k +: 32] = $urandom; return x; endfunction
  initial begin
    in_valid = 0; in_word = '0;
    repeat (4) @(posedge clk); rst_n = 1;
    while (sent < WORDS) begin
      @(negedge clk);
      if (gap == 0) begin in_valid = 1; in_word = rnd(); sent++; gap = N - 1 + ($urandom % 3); end
      else begin in_valid = 0; in_word = rnd(); gap--; end   // data toggles while invalid (must be ignored)
    end
    @(negedge clk) in_valid = 0;
    repeat (D + N + 4) @(posedge clk);
    if (ovr) begin $display("FAIL overrun"); err++; end
    if (nout != WORDS) begin $display("FAIL count %0d != %0d", nout, WORDS); err++; end
    $display("%s W=%0d N=%0d P=%0d words=%0d out=%0d errors=%0d", err ? "FAIL" : "PASS", W, N, P, WORDS, nout, err);
    $finish;
  end
  always @(posedge clk) if (rst_n) begin
    #0.1;
    if (ov !== rv[D] || (ov && ow !== rw[D])) begin if (err < 5) $display("MISMATCH t=%0t ov=%b ref=%b", $time, ov, rv[D]); err++; end
    if (ov) nout++;
  end
endmodule
