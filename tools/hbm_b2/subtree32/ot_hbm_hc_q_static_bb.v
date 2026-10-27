// Port list of the qhub client ot_hbm_hc_q_static (rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_q_static.sv), black-boxed
// while hc128_subtree32_gen.sh elaborates ot_hbm_hc_qhub_static: the subtree32 cut reads none of it.
(* blackbox *) module ot_hbm_hc_q_static #(
    parameter integer RD_CAPTURE=23,
    parameter integer GATHER_PHASE=23,
    parameter integer DONE_LAT=19,
    parameter integer XW_BEATS=4,
    parameter integer MUT=0 // 1 residual wave word mutant, 2 result store one sector late, 3 capture edge early,
                            // 4 x_wave beats 1/2 sent swapped, 5 x_wave beat 3 one edge late
)(
    input wire clk,rst_n,
    input wire [7:0] tgt,              // identity strap: F20 target id (108+q)
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    output wire configured,
    output reg [135:0] lg_rq,
    output wire [2247:0] lg_wq,
    input wire [2055:0] lg_rr,
    input wire [7:0] lg_w_done,
    output wire x_wave_v,
    output wire [9:0] x_wave_word,
    output wire [8192/XW_BEATS-1:0] x_wave,
    output wire [1:0] x_wave_beat,
    output wire residual_done,
    output wire gathered_mix_v,
    output wire [4:0] gathered_mix_row,
    output wire [2:0] gathered_mix_pos,
    output wire [31:0] gathered_mix_data,
    output wire gather_done,
    input wire result_v,
    input wire [2:0] result_position,
    input wire [767:0] result,
    output wire program_active,program_done,
    output reg fault
);
endmodule
