module ot_pg_canonical_xor16_1019(input wire clk, rst_n, input wire [15:0] a,b, output reg [15:0] y);
  (* keep=1 *) reg reset_first;
  (* keep=1 *) reg reset_a, reset_b;
  reg [15:0] a_q, b_q;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin reset_first<=0; reset_a<=0; reset_b<=0; end
    else begin reset_first<=1; reset_a<=reset_first; reset_b<=reset_first; end
  always @(posedge clk or negedge reset_a)
    if (!reset_a) begin a_q[15:0]<=0; b_q[7:0]<=0; end
    else begin a_q[15:0]<=a; b_q[7:0]<=b[7:0]; end
  always @(posedge clk or negedge reset_b)
    if (!reset_b) begin b_q[15:8]<=0; y<=0; end
    else begin b_q[15:8]<=b[15:8]; y<=a_q ^ b_q; end
endmodule
