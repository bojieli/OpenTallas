// Proof-only SRAM abstraction (identical in gold and gate): a registered read word that depends on every
// control, address and data input, so any port mis-wiring around a macro becomes observable to equiv_*.
module ot_sram_1r1w_128x256_m1_r2c2(input clk,r_ce_in,input [6:0] r_addr_in,output reg [255:0] rd_out,input w_ce_in,
  input [6:0] w_addr_in,input [255:0] wd_in,w_mask_in,input [1:0] rr_en,input [13:0] rr_addr,input [1:0] cr_en,input [15:0] cr_sel);
  wire [63:0] k = {14'd0,r_ce_in,r_addr_in,w_ce_in,w_addr_in,rr_en,rr_addr,cr_en,cr_sel};
  always @(posedge clk) rd_out <= wd_in ^ {w_mask_in[0],w_mask_in[255:1]} ^ {4{k}};
endmodule
module ot_sram_1r1w_64x512_m1_r2c2(input clk,r_ce_in,input [5:0] r_addr_in,output reg [511:0] rd_out,input w_ce_in,
  input [5:0] w_addr_in,input [511:0] wd_in,w_mask_in,input [1:0] rr_en,input [11:0] rr_addr,input [1:0] cr_en,input [17:0] cr_sel);
  wire [63:0] k = {16'd0,r_ce_in,r_addr_in,w_ce_in,w_addr_in,rr_en,rr_addr,cr_en,cr_sel};
  always @(posedge clk) rd_out <= wd_in ^ {w_mask_in[0],w_mask_in[511:1]} ^ {8{k}};
endmodule
