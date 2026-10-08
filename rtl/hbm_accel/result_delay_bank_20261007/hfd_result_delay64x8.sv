// Full-shape physical vehicles; the reusable core stays default-off.
module hfd_result_delay64x8_ew(input wire clk, rst_n,
  input wire [63:0] d, output wire [63:0] q);
  ot_hbm_result_delay_bank #(.W(64),.STAGES(8),.ENABLE(1)) bank(clk,rst_n,d,q);
endmodule
module hfd_result_delay64x8_ns(input wire clk, rst_n,
  input wire [63:0] d, output wire [63:0] q);
  ot_hbm_result_delay_bank #(.W(64),.STAGES(8),.ENABLE(1)) bank(clk,rst_n,d,q);
endmodule
