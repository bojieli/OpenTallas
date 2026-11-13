module ot_sram_1r1w_128x256_m1_r0c0_g256(input wire clk, input wire r_ce_in, input wire [6:0] r_addr_in, output wire [255:0] rd_out, input wire w_ce_in, input wire [6:0] w_addr_in, input wire [255:0] wd_in, input wire w_mask_in);
  reg [255:0] q;
  always @(posedge clk) q <= (wd_in ^ {37{r_addr_in,w_addr_in,r_ce_in,w_ce_in}}) ^ {q[254:0],q[255]};
  assign rd_out = q;
endmodule
