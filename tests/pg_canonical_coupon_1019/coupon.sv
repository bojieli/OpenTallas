module ot_pg_canonical_xor16_1019(input wire clk, rst_n, input wire [15:0] a,b, output reg [15:0] y);
  (* keep=1 *) reg reset_first;
  wire reset_a, reset_b;
  (* keep=1, keep_hierarchy=1 *) ot_pg_reset_copy_1019 #(.COPY_ID(0)) u_reset_a(clk,rst_n,reset_first,reset_a);
  (* keep=1, keep_hierarchy=1 *) ot_pg_reset_copy_1019 #(.COPY_ID(1)) u_reset_b(clk,rst_n,reset_first,reset_b);
  reg [15:0] a_q, b_q;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin reset_first<=0; end
    else begin reset_first<=1; end
  always @(posedge clk or negedge reset_a)
    if (!reset_a) begin a_q[15:0]<=0; b_q[7:0]<=0; end
    else begin a_q[15:0]<=a; b_q[7:0]<=b[7:0]; end
  always @(posedge clk or negedge reset_b)
    if (!reset_b) begin b_q[15:8]<=0; y<=0; end
    else begin b_q[15:8]<=b[15:8]; y<=a_q ^ b_q; end
endmodule

(* keep_hierarchy=1 *) module ot_pg_reset_copy_1019 #(parameter COPY_ID=0)(input wire clk,rst_n,d,output reg q);
 always @(posedge clk or negedge rst_n) if(!rst_n) q<=0; else q<=d;
endmodule
