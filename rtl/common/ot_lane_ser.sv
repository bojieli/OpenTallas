// CPL-HBM-B1 (DO_NOT_COUNT) DEC12 multi-beat lane endpoint: N:1 serialiser.
// A word accepted at cycle t (in_valid) leaves as beats 0..N-1 on cycles t+1..t+N (LSB slice first).
// Lane wire = {beat_idx, slice}: ceil(W/N) data bits + ceil(log2 N) beat-index bits (DEC12 port width rule).
// Static schedule contract: in_valid at most once every N cycles; a violation raises overrun (sticky).
module ot_lane_ser #(parameter int W = 2745, parameter int N = 4,
                     localparam int S = (W + N - 1) / N, localparam int B = (N > 1) ? $clog2(N) : 1) (
  input  logic         clk, rst_n,
  input  logic         in_valid,
  input  logic [W-1:0] in_word,
  output logic         lane_valid,
  output logic [B-1:0] lane_beat,
  output logic [S-1:0] lane_data,
  output logic         overrun
);
  logic [S*N-1:0] sh;          // padded word, shifted one slice per beat
  logic [B-1:0]   cnt;
  logic           busy;
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      sh <= '0; cnt <= '0; busy <= 1'b0; lane_valid <= 1'b0; lane_beat <= '0; lane_data <= '0; overrun <= 1'b0;
    end else begin
      if (in_valid) begin
        if (busy && cnt != B'(N - 1)) overrun <= 1'b1;
        lane_valid <= 1'b1; lane_beat <= '0; lane_data <= in_word[S-1:0];
        sh <= {{(S*N-W){1'b0}}, in_word} >> S;
        cnt <= '0; busy <= (N > 1);
      end else if (busy) begin
        lane_valid <= 1'b1; lane_beat <= cnt + 1'b1; lane_data <= sh[S-1:0];
        sh <= sh >> S;
        cnt <= cnt + 1'b1; busy <= (cnt + 1'b1 != B'(N - 1));
      end else begin
        lane_valid <= 1'b0;
      end
    end
  end
endmodule
