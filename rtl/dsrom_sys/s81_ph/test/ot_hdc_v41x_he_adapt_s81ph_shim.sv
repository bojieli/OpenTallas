`timescale 1ns/1ps
// CLAUDE S81-PH hc BENCH SHIM (bench source lists only, never with rtl/hdc/v41x/ot_hdc_v41x_he_adapt.sv): the native
// module name running the unit through ot_s81ph_he_xing, DF / DR / NEG from +define+S81PH_DF / _DR / _NEG.
`ifndef S81PH_DF
`define S81PH_DF 0
`endif
`ifndef S81PH_DR
`define S81PH_DR 0
`endif
`ifndef S81PH_NEG
`define S81PH_NEG 0
`endif
module ot_hdc_v41x_he_adapt #(

    parameter integer HW   = 8,            // engine lanes per group (8 * HW FP32 MAC lanes)
    parameter integer TL   = 9,            // engine tail levels
    parameter integer KCMAX = 128,         // largest he_k (chunks per row)
    parameter integer PMAX = 8,            // positions per op (power of two >= MP)
    parameter integer BAW  = 16,           // weight bank word address width
    parameter integer AW   = 24,
    parameter integer NW   = 16,
    parameter integer S    = 8,            // x read ports (the as-built HC_SPLIT)
    parameter integer MP   = 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output wire              idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_k,
    input  wire [AW-1:0]     i_wbase,
    input  wire [AW-1:0]     i_xbase,
    input  wire [AW-1:0]     i_obase,
    input  wire [2:0]        i_m,
    input  wire [AW-1:0]     i_xps,
    input  wire [AW-1:0]     i_ops,
    // weight banks (binary32), bank k at [k*...]
    output wire [7:0]        w_re,
    output wire [8*BAW-1:0]  w_addr,
    input  wire [8*HW*32-1:0] w_data,
    // vector memory: x reads (the as-built HE's per-chunk ports) and the masked write
    output wire [MP*S-1:0]   x_re,
    output wire [MP*S*AW-1:0] x_addr,
    input  wire [MP*S*32-1:0] x_q,
    output wire [MP-1:0]     o_we,
    output wire [MP*AW-1:0]  o_addr,
    output wire [MP*32-1:0]  o_mask,
    output wire [MP*1024-1:0] o_data,
    output wire              fault
);
    // the bench (tb_hdc_core_v41x) reads the adapter's debug counters by hierarchy
    wire [31:0] dbg_ops = u_x.u_he.dbg_ops, dbg_elems = u_x.u_he.dbg_elems;
    ot_s81ph_he_xing #(.DF(`S81PH_DF), .DR(`S81PH_DR), .NEG(`S81PH_NEG), .HW(HW), .TL(TL), .KCMAX(KCMAX), .PMAX(PMAX), .BAW(BAW), .AW(AW), .NW(NW), .S(S), .MP(MP)) u_x (.*);
endmodule
