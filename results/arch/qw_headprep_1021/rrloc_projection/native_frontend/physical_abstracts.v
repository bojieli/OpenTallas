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

(* blackbox *) module ot_qfd_tt_ctlm_static_hr_safe32_native32_1r #(parameter integer STAGE_ME=1, SEGCAL=1) (
    input wire [94:0] rom_ret_i,
    input wire cp_active,
    output wire [55:0] cp,
    output wire me_image_ready,
    output wire [75:0] program_obs,
    output wire layer_context_v,
    output wire [17:0] native_tok,
    output wire [17:0] native_pos,
    output wire [379:0] rom_cmd,
    output wire [5:0] command_stage,
    output wire [379:0] native_cmd,
    output wire [15:0] me_observe,
    input wire [94:0] native_ret,
    input wire ck_head,
    input wire rst_n,
    input wire h_start,
    input wire stage_start,
    input wire [5:0] stage,
    input wire [17:0] token,
    input wire [17:0] pos,
    input wire [11:0] prog_base,
    input wire pw_v,
    input wire [9:0] pw_addr,
    input wire [63:0] pw_data,
    input wire [23:0] x_oacc,
    input wire x_oidle,
    input wire [15:0] x_oprog,
    input wire [15:0] x_orows,
    input wire kv_ok,
    input wire kv_write_drained,
    input wire me_mem_ok,
    output wire m_fin_o,
    output wire [17:0] m_fidx_o,
    output wire [31:0] m_fval_o,
    output wire kvd_v,
    output wire [23:0] kvd_wbase,
    output wire [23:0] kvd_ts,
    output wire [23:0] kvd_ks,
    output wire [23:0] kvd_js,
    output wire [23:0] kvd_wcs,
    output wire [3:0] kvd_split,
    output wire [2:0] kvd_jsh,
    output wire [17:0] kvd_tiles,
    output wire [17:0] kvd_k,
    output wire [17:0] kvd_nout,
    output wire kvd_kindk,
    output wire [17:0] kvd_pos,
    output wire me_clk_en,
    output wire c_fault
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
