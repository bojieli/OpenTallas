
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
