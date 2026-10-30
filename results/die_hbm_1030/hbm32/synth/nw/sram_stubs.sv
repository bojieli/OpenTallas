// GENERATED DIE-HBM-32: port-only blackbox stubs of the 4 SRAM macro models (hub synth count; macros are hard macros)
(* blackbox *)
module ot_sram_1r1w_128x256_m1_r2c2 (
    input  wire clk,
    input  wire r_ce_in,
    input  wire [6:0] r_addr_in,
    output reg  [255:0] rd_out,
    input  wire w_ce_in,
    input  wire [6:0] w_addr_in,
    input  wire [255:0] wd_in,
    input  wire [255:0] w_mask_in,
    input  wire [1:0] rr_en,
    input  wire [13:0] rr_addr,
    input  wire [1:0] cr_en,
    input  wire [15:0] cr_sel
);
endmodule

(* blackbox *)
module ot_sram_1r1w_64x16_m1 (
    input  wire clk,
    input  wire r_ce_in,
    input  wire [5:0] r_addr_in,
    output reg  [15:0] rd_out,
    input  wire w_ce_in,
    input  wire [5:0] w_addr_in,
    input  wire [15:0] wd_in,
    input  wire [15:0] w_mask_in
);
endmodule

(* blackbox *)
module ot_sram_1r1w_128x64_m1_p192 (
    input  wire clk,
    input  wire r_ce_in,
    input  wire [6:0] r_addr_in,
    output reg  [63:0] rd_out,
    input  wire w_ce_in,
    input  wire [6:0] w_addr_in,
    input  wire [63:0] wd_in,
    input  wire [63:0] w_mask_in
);
endmodule

(* blackbox *)
module ot_sram_1r1w_1024x256_m2_r2c2 (
    input  wire clk,
    input  wire r_ce_in,
    input  wire [9:0] r_addr_in,
    output reg  [255:0] rd_out,
    input  wire w_ce_in,
    input  wire [9:0] w_addr_in,
    input  wire [255:0] wd_in,
    input  wire [255:0] w_mask_in,
    input  wire [1:0] rr_en,
    input  wire [17:0] rr_addr,
    input  wire [1:0] cr_en,
    input  wire [15:0] cr_sel
);
endmodule
