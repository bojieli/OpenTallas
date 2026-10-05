`timescale 1ns/1ps
// Existing native-cut port/observer surface, additive static-provider selection.
// Reused from wrapper62c249 at6d1f532; no field array under RT_CUT.
// STATIC_CONTROLS is off by default; hierarchy dut.u_sp and dut.vm is retained.
module dsrom_source_cut #(
    parameter integer FAST = 0,
    parameter integer PP = 0,
    parameter integer BP = 0,
    parameter integer NP = 8,
    parameter integer R = 2,
    parameter integer NBF = 2,
    parameter integer PHW = 6,
    parameter integer STATIC_CONTROLS = 0,
    parameter integer CONTROL_STAGE = 37,
    parameter integer SAW = 14,
    parameter integer VAW = 14,
    parameter integer VRD = 64,
    parameter integer KMAX = 6144,
    parameter integer BST = 2,
    parameter integer RST = 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire [PHW-1:0]    i_ph,
    input  wire [2:0]        i_np,
    input  wire [VAW-1:0]    i_xbase,
    input  wire [VAW-1:0]    i_xps,
    input  wire [VAW-1:0]    i_obase,
    input  wire [VAW-1:0]    i_ops,
    output wire              ready,
    output wire              idle,
    output wire [R-1:0]      o_we,
    output wire [R*VAW-1:0]  o_addr,
    output wire [R*32-1:0]   o_data,
    output wire              fault,
    output wire [31:0]       phase_cycles
`ifdef RT_CUT
    ,
    output wire              fb_cfg_go,
    output wire [PHW-1:0]    fb_cfg_ph,
    output wire [2:0]        fb_cfg_np,
    output wire              fb_go,
    output wire              fb_go_bf,
    output wire              fb_xs_v,
    output wire [7:0]        fb_xs_p,
    output wire [2:0]        fb_xs_b,
    output wire [1:0]        fb_xs_sv,
    output wire [255:0]      fb_xs_q0,
    output wire [9:0]        fb_xs_e0,
    output wire [255:0]      fb_xs_q1,
    output wire [9:0]        fb_xs_e1,
    output wire [2:0]        fb_xs_pos,
    output wire [2:0]        fb_xb_pos,
    output wire              fb_xb_v,
    output wire [2:0]        fb_xb_b,
    output wire [3:0]        fb_xb_sv,
    output wire [31:0]       fb_xb_u,
    output wire [1023:0]     fb_xb_d,
    input  wire [R-1:0]      fr_v,
    input  wire [16*R-1:0]   fr_row,
    input  wire [3*R-1:0]    fr_pos,
    input  wire [32*R-1:0]   fr_fp32,
    input  wire [16*R-1:0]   fr_bf16,
    input  wire [R-1:0]      fr_e,
    input  wire              fr_fault
`endif
,
    output wire obs_VM_re,
    output wire [VAW-1:0] obs_VM_addr,
    output wire obs_AQ_in,
    output wire [13:0] obs_AQ_k,
    output wire [1:0] obs_AQ_out,
    output wire [14:0] obs_have,
    output wire obs_sm_adv,
    output wire [15:0] obs_sm_i,
    output wire [47:0] obs_sm_word,
    output wire [14:0] obs_sm_have,
    output wire [14:0] obs_sm_need,
    output wire obs_sm_wait,
    output wire [18:0] obs_rows_left,
    output wire obs_ld_run,
    output wire obs_sm_run
);
ot_v41_fieldtop_static_w17w10 #( .FAST(FAST), .PP(PP), .BP(BP), .NP(NP), .R(R), .NBF(NBF), .PHW(PHW), .SAW(SAW), .STATIC_CONTROLS(STATIC_CONTROLS), .CONTROL_STAGE(CONTROL_STAGE), .VAW(VAW), .VRD(VRD), .KMAX(KMAX), .BST(BST), .RST(RST) ) dut (.*);
assign obs_VM_re = dut.x_re;
assign obs_VM_addr = dut.x_addr;
assign obs_AQ_in = dut.u_sp.rq_v;
assign obs_AQ_k = dut.u_sp.rq_k;
assign obs_AQ_out = dut.u_sp.aq_vo;
assign obs_have = dut.u_sp.have[0];
assign obs_sm_adv = dut.u_sp.s_adv;
assign obs_sm_i = dut.u_sp.sm_i;
assign obs_sm_word = dut.u_sp.sw;
assign obs_sm_have = dut.u_sp.have[0];
assign obs_sm_need = dut.u_sp.need_q;
assign obs_sm_wait = dut.u_sp.sm_run && dut.u_sp.sw_v && !dut.u_sp.s_ok;
assign obs_rows_left = dut.u_sp.rows_left;
assign obs_ld_run = dut.u_sp.ld_run;
assign obs_sm_run = dut.u_sp.sm_run;
endmodule
