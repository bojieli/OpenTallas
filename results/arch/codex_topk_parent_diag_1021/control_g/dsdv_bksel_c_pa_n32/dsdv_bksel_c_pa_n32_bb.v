// DIAGNOSTIC stand-in blackbox (tools/qwen_dv/slice_standin.py); never bind
(* blackbox *) module dsdv_bksel_c_pa_n32 (
    input wire ck,
    input wire [412:0] rst_profile,
    input wire [287:0] fs0_0,
    input wire [287:0] fs0_1,
    input wire [288:0] fs0_2,
    input wire [287:0] fs1_0,
    input wire [287:0] fs1_1,
    input wire [288:0] fs1_2,
    input wire [287:0] fs2_0,
    input wire [287:0] fs2_1,
    input wire [288:0] fs2_2,
    input wire [287:0] fs3_0,
    input wire [287:0] fs3_1,
    input wire [288:0] fs3_2,
    input wire [353:0] fo0,
    input wire [353:0] fo1,
    input wire [353:0] fo2,
    input wire [353:0] fo3,
    output wire [131:0] t_c_s,
    output wire [131:0] t_c_n,
    output wire [1:0] t_cr_s,
    output wire [1:0] t_cr_n,
    output wire [513:0] vd
);
endmodule
