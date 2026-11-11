// CPL-HBM-B1 (DO_NOT_COUNT) DEC12 multi-beat lane endpoint: 1:N deserialiser (leaf station).
// Captures beat k into slice k; on the last beat (k = N-1) the whole word is registered out the next cycle.
// Holding flops: (N-1)*ceil(W/N) slices + W output register.
module ot_lane_deser #(parameter int W = 2745, parameter int N = 4,
                       localparam int S = (W + N - 1) / N, localparam int B = (N > 1) ? $clog2(N) : 1) (
  input  logic         clk, rst_n,
  input  logic         lane_valid,
  input  logic [B-1:0] lane_beat,
  input  logic [S-1:0] lane_data,
  output logic         out_valid,
  output logic [W-1:0] out_word
);
  logic [S*N-1:0] acc;
  logic [S*N-1:0] full;
  always_comb begin
    full = acc;
`ifdef NEG_SWAP
    full[(N-1-lane_beat)*S +: S] = lane_data;   // negative control: reversed beat order
`else
    full[lane_beat*S +: S] = lane_data;
`endif
  end
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin acc <= '0; out_valid <= 1'b0; out_word <= '0; end
    else begin
      out_valid <= 1'b0;
      if (lane_valid) begin
        acc <= full;
        if (lane_beat == B'(N - 1)) begin out_valid <= 1'b1; out_word <= full[W-1:0]; end
      end
    end
  end
endmodule
