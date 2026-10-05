`timescale 1ns/1ps
// Original and GENERATED helper-substituted FP pipelines, same clock/input.
// No source-list substitution is performed by this bench.
module tb_w11_fastfp_prefix_sequential_gate (
    input wire clk, rst_n, valid_in,
    input wire [31:0] a, b,
    output wire [31:0] ref_add_y, sim_add_y, ref_mul_y, sim_mul_y,
    output wire [1:0] ref_add_err, sim_add_err, ref_mul_err, sim_mul_err,
    output wire ref_add_v, sim_add_v, ref_mul_v, sim_mul_v,
    output wire [31:0] ref_qadd_y, sim_qadd_y, ref_qmul_y, sim_qmul_y,
    output wire ref_qadd_fault, sim_qadd_fault, ref_qmul_fault, sim_qmul_fault
);
    gate_ref_ot_hdc_fp32_add_fast ra (clk, rst_n, valid_in, a, b, ref_add_y, ref_add_err, ref_add_v);
    gate_sim_ot_hdc_fp32_add_fast sa (clk, rst_n, valid_in, a, b, sim_add_y, sim_add_err, sim_add_v);
    gate_ref_ot_hdc_fp32_mul_fast rm (clk, rst_n, valid_in, a, b, ref_mul_y, ref_mul_err, ref_mul_v);
    gate_sim_ot_hdc_fp32_mul_fast sm (clk, rst_n, valid_in, a, b, sim_mul_y, sim_mul_err, sim_mul_v);
    gate_ref_ot_hdc_qadd rqa (clk, rst_n, valid_in, a, b, ref_qadd_y, ref_qadd_fault);
    gate_sim_ot_hdc_qadd sqa (clk, rst_n, valid_in, a, b, sim_qadd_y, sim_qadd_fault);
    gate_ref_ot_hdc_qmul rqm (clk, rst_n, valid_in, a, b, ref_qmul_y, ref_qmul_fault);
    gate_sim_ot_hdc_qmul sqm (clk, rst_n, valid_in, a, b, sim_qmul_y, sim_qmul_fault);
endmodule
