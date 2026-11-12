// Equivalence-only SRAM stubs: identical in gold and gate. Each output is a registered function of every input, so
// gold == gate on the macro outputs iff the macros see the same input history (the property under test).
module ot_sram_1r1w_1024x256_m2_r2c2(input clk, r_ce_in, input [9:0] r_addr_in, output reg [255:0] rd_out, input w_ce_in, input [9:0] w_addr_in, input [255:0] wd_in, w_mask_in, input [1:0] rr_en, input [17:0] rr_addr, input [1:0] cr_en, input [15:0] cr_sel);
  always @(posedge clk) rd_out <= rd_out ^ wd_in ^ w_mask_in ^ {r_ce_in, w_ce_in, r_addr_in, w_addr_in, rr_en, rr_addr, cr_en, cr_sel};
endmodule
module ot_sram_1r1w_256x256_m2_r2c2(input clk, r_ce_in, input [7:0] r_addr_in, output reg [255:0] rd_out, input w_ce_in, input [7:0] w_addr_in, input [255:0] wd_in, w_mask_in, input [1:0] rr_en, input [13:0] rr_addr, input [1:0] cr_en, input [15:0] cr_sel);
  always @(posedge clk) rd_out <= rd_out ^ wd_in ^ w_mask_in ^ {r_ce_in, w_ce_in, r_addr_in, w_addr_in, rr_en, rr_addr, cr_en, cr_sel};
endmodule
module ot_sram_1r1w_128x256_m1_r2c2(input clk, r_ce_in, input [6:0] r_addr_in, output reg [255:0] rd_out, input w_ce_in, input [6:0] w_addr_in, input [255:0] wd_in, w_mask_in, input [1:0] rr_en, input [13:0] rr_addr, input [1:0] cr_en, input [15:0] cr_sel);
  always @(posedge clk) rd_out <= rd_out ^ wd_in ^ w_mask_in ^ {r_ce_in, w_ce_in, r_addr_in, w_addr_in, rr_en, rr_addr, cr_en, cr_sel};
endmodule
