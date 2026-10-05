`timescale 1ns/1ps
// Blackbox view of the hardened Qwen SU lane macro (rtl/hbm_accel/qwen/fmax/ot_hdc_vstream_lane_f12_m.sv) for the
// hierarchical route of ot_hdc_vstream_rt_f12_hw; its LEF and SS/FF ETMs come from the routed lane (vs/jobs/export_abstract.sh).
(* blackbox *)
module ot_hdc_vstream_lane_f12_m (
    input  wire              clk,
    input  wire              rst_n,
    // controller state (lane 0's view) and this lane's element
    input  wire              emit0,
    input  wire              live,
    input  wire [17:0]     i,
    input  wire [18:0]       fin_th,
    input  wire              i_last_r,
    input  wire [23:0]     cura0, curb0, curc0, curd0, rrow,
    input  wire [23:0]     asi, bsi, csi, dsi,
    input  wire              asrc, bsrc, csrc, mc, md, redsq,
    input  wire [1:0]        ma, mb, dst, red,
    input  wire [2:0]        ad,
    input  wire [31:0]       imm1, imm2,
    input  wire [2:0]        cls,
    input  wire              accept,
    input  wire [2:0]        i_sfu,
    // memories
    output wire              va_re,
    output wire [23:0]     va_addr,
    input  wire [31:0]       va_q,
    output wire              vb_re,
    output wire [23:0]     vb_addr,
    input  wire [31:0]       vb_q,
    output wire              vc_re,
    output wire [23:0]     vc_addr,
    input  wire [31:0]       vc_q,
    output wire              wrom_re,
    output wire [23:0]     wrom_addr,
    input  wire [256-1:0]  wrom_q,
    output wire              crom_re,
    output wire [23:0]     crom_addr,
    input  wire [63:0]       crom_q,
    output wire              vm_we,
    output wire [23:0]     vm_waddr,
    output wire [31:0]       vm_wdata,
    output wire              kv_we,
    output wire [23:0]     kv_waddr,
    output wire [31:0]       kv_wdata,
    // to the vector reducer
    output wire              l_ov,
    output wire [31:0]       l_out,
    output wire [1:0]        l_red,
    output wire              l_redsq,
    output wire [23:0]     l_raddr,
    output wire              l_last,
    output wire              retire,
    output wire              l_fault

);
endmodule
