(* blackbox *) module ot_sram_1r1w_128x256_m1_r2c2 (
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

(* blackbox *) module ot_sram_1r1w_64x512_m1_r2c2 (
    input  wire clk,
    input  wire r_ce_in,
    input  wire [5:0] r_addr_in,
    output reg  [511:0] rd_out,
    input  wire w_ce_in,
    input  wire [5:0] w_addr_in,
    input  wire [511:0] wd_in,
    input  wire [511:0] w_mask_in,
    input  wire [1:0] rr_en,
    input  wire [11:0] rr_addr,
    input  wire [1:0] cr_en,
    input  wire [17:0] cr_sel
);
endmodule



(* blackbox *) module ot_rom_4096x72_m8 #(parameter VIAMAP = "", parameter INSTANCE = "") (
    input  wire clk,
    input  wire ce_in,
    input  wire [11:0] addr_in,
    output reg  [71:0] rd_out
);
endmodule

(* blackbox *) module ot_rom_4096x266_m8 #(parameter VIAMAP = "", parameter INSTANCE = "") (
    input  wire clk,
    input  wire ce_in,
    input  wire [11:0] addr_in,
    output reg  [265:0] rd_out
);
endmodule

// QW-CALR 10-20: closed hard child qfd_tt_ctlm_dv_wtn (view physical/ref_tile/qfd_tt_ctlm_dv_wtn, record
// codex/closure-record-qfd_tt_ctlm_dv_wtn-wtn1-9fa6fd27d), header of rtl/qwen_dv/qfd_tt_ctlm_dv_wtn.sv
(* blackbox *) module qfd_tt_ctlm_dv_wtn #(parameter integer MUT = 0) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [74:0]  pw,
    input  wire [82:0]  auth,
    input  wire [24:0]  start,
    input  wire [3:0]   retire,
    input  wire [37:0]  obs,
    output wire [16:0]  st
);
endmodule
