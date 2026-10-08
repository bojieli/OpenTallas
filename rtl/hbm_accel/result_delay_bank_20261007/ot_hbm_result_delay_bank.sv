// Fixed bit-opaque balancing delay. Full packet protection belongs to endpoints.
// Candidate only: fixed pin views, async-reset mapping and context timing are open.
module ot_hbm_result_delay_bank #(
  parameter integer W = 64,
  parameter integer STAGES = 8,
  parameter integer ENABLE = 0
) (
  input wire clk,
  input wire rst_n,
  input wire [W-1:0] d,
  output wire [W-1:0] q
);
  generate if (ENABLE != 0) begin : g_on
    reg [W-1:0] pipe [0:STAGES-1];
    integer stage;
    always @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
        for (stage=0; stage<STAGES; stage=stage+1) pipe[stage] <= {W{1'b0}};
      end else begin
        pipe[0] <= d;
        for (stage=1; stage<STAGES; stage=stage+1) pipe[stage] <= pipe[stage-1];
      end
    end
    assign q = pipe[STAGES-1];
  end else begin : g_off
    assign q = {W{1'b0}};
  end endgenerate
endmodule
