// eq_rreg.sh stub (equivalence only): the same deterministic sequential function in gold and gate, every input observed.
module ot_sram_1r1w_256x256_m2_r2c2 (input wire clk, input wire r_ce_in, input wire [7:0] r_addr_in, output reg [255:0] rd_out,
    input wire w_ce_in, input wire [7:0] w_addr_in, input wire [255:0] wd_in, input wire [255:0] w_mask_in,
    input wire [1:0] rr_en, input wire [13:0] rr_addr, input wire [1:0] cr_en, input wire [15:0] cr_sel);
  always @(posedge clk) if (r_ce_in) rd_out <= wd_in ^ w_mask_in ^ {32{r_addr_in}} ^ {32{w_addr_in}} ^ {128{rr_en}} ^ {64{w_ce_in, cr_en, ^rr_addr, ^cr_sel}};
endmodule
module ot_sram_1r1w_2048x32_m8_r0c0_g32 (input wire clk, input wire r_ce_in, input wire [10:0] r_addr_in, output reg [31:0] rd_out,
    input wire w_ce_in, input wire [10:0] w_addr_in, input wire [31:0] wd_in, input wire w_mask_in);
  always @(posedge clk) if (r_ce_in) rd_out <= wd_in ^ {r_addr_in, w_addr_in, r_addr_in[9:0]} ^ {32{w_ce_in ^ w_mask_in}};
endmodule
