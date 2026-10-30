`timescale 1ns/1ps
module ot_sram_1r1w_128x256_m1_r2c2 (input wire clk, input wire r_ce_in, input wire [6:0] r_addr_in, output reg [255:0] rd_out,
 input wire w_ce_in, input wire [6:0] w_addr_in, input wire [255:0] wd_in, input wire [255:0] w_mask_in,
 input wire [1:0] rr_en, input wire [13:0] rr_addr, input wire [1:0] cr_en, input wire [15:0] cr_sel);
 reg [255:0] m [0:127];
 always @(posedge clk) begin if (r_ce_in) rd_out <= m[r_addr_in]; if (w_ce_in) m[w_addr_in] <= (m[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in); end
endmodule
module ot_sram_1r1w_64x128_m1_r2c2 (input wire clk, input wire r_ce_in, input wire [5:0] r_addr_in, output reg [127:0] rd_out,
 input wire w_ce_in, input wire [5:0] w_addr_in, input wire [127:0] wd_in, input wire [127:0] w_mask_in,
 input wire [1:0] rr_en, input wire [13:0] rr_addr, input wire [1:0] cr_en, input wire [15:0] cr_sel);
 reg [127:0] m [0:63];
 always @(posedge clk) begin if (r_ce_in) rd_out <= m[r_addr_in]; if (w_ce_in) m[w_addr_in] <= (m[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in); end
endmodule
module ot_sram_1r1w_256x128_m1_r2c2 (input wire clk, input wire r_ce_in, input wire [7:0] r_addr_in, output reg [127:0] rd_out,
 input wire w_ce_in, input wire [7:0] w_addr_in, input wire [127:0] wd_in, input wire [127:0] w_mask_in,
 input wire [1:0] rr_en, input wire [13:0] rr_addr, input wire [1:0] cr_en, input wire [15:0] cr_sel);
 reg [127:0] m [0:255];
 always @(posedge clk) begin if (r_ce_in) rd_out <= m[r_addr_in]; if (w_ce_in) m[w_addr_in] <= (m[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in); end
endmodule
module ot_sram_1r1w_128x256_m1_r2c2_o (input wire clk, input wire r_ce_in, input wire [6:0] r_addr_in, output reg [255:0] rd_out,
 input wire w_ce_in, input wire [6:0] w_addr_in, input wire [255:0] wd_in, input wire [255:0] w_mask_in,
 input wire [1:0] rr_en, input wire [13:0] rr_addr, input wire [1:0] cr_en, input wire [15:0] cr_sel);
 reg [255:0] m [0:127];
 always @(posedge clk) begin if (r_ce_in) rd_out <= m[r_addr_in]; if (w_ce_in) m[w_addr_in] <= (m[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in); end
endmodule
module ot_sram_1r1w_64x128_m1_r2c2_o (input wire clk, input wire r_ce_in, input wire [5:0] r_addr_in, output reg [127:0] rd_out,
 input wire w_ce_in, input wire [5:0] w_addr_in, input wire [127:0] wd_in, input wire [127:0] w_mask_in,
 input wire [1:0] rr_en, input wire [13:0] rr_addr, input wire [1:0] cr_en, input wire [15:0] cr_sel);
 reg [127:0] m [0:63];
 always @(posedge clk) begin if (r_ce_in) rd_out <= m[r_addr_in]; if (w_ce_in) m[w_addr_in] <= (m[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in); end
endmodule
module ot_sram_1r1w_256x128_m1_r2c2_o (input wire clk, input wire r_ce_in, input wire [7:0] r_addr_in, output reg [127:0] rd_out,
 input wire w_ce_in, input wire [7:0] w_addr_in, input wire [127:0] wd_in, input wire [127:0] w_mask_in,
 input wire [1:0] rr_en, input wire [13:0] rr_addr, input wire [1:0] cr_en, input wire [15:0] cr_sel);
 reg [127:0] m [0:255];
 always @(posedge clk) begin if (r_ce_in) rd_out <= m[r_addr_in]; if (w_ce_in) m[w_addr_in] <= (m[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in); end
endmodule
