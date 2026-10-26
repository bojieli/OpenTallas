// QC-SU-F4-2 LEC abstraction (NOT a model): one registered observation function shared by BOTH SRAM masters, so the
// equivalence compares every SRAM input connection (control fields at distinct bit positions, data/mask folded).
module ot_sram_1r1w_1024x256_m2_r2c2 (input wire clk, input wire r_ce_in, input wire [9:0] r_addr_in, output reg [255:0] rd_out, input wire w_ce_in,
    input wire [9:0] w_addr_in, input wire [255:0] wd_in, input wire [255:0] w_mask_in, input wire [1:0] rr_en,
    input wire [17:0] rr_addr, input wire [1:0] cr_en, input wire [15:0] cr_sel);
  wire [19:0] rra = {2'b00, rr_addr};
  always @(posedge clk) rd_out <= (wd_in ^ {w_mask_in[127:0], w_mask_in[255:128]}) ^ {194'd0, r_ce_in, r_addr_in, w_ce_in, w_addr_in, rr_en, rra, cr_en, cr_sel};
endmodule
