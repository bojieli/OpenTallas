`timescale 1ns/1ps
// CLAUDE S81-PH su BENCH SHIM (bench source lists only, never with rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv): a module of the
// native name that runs the unit through the S81 die crossing (ot_s81ph_su_xing), DF / DR from +define+S81PH_DF/_DR,
// so the unchanged core and decode campaign exercise the split unit.
`ifndef S81PH_DF
`define S81PH_DF 0
`endif
`ifndef S81PH_NEG
`define S81PH_NEG 0
`endif
`ifndef S81PH_DR
`define S81PH_DR 0
`endif
module ot_hdc_v41x_su_adapt #(

    parameter integer N  = 16,          // vector-unit light lanes
    parameter integer M  = 8,           // SFU lanes
    parameter integer LV = 7,           // reducer time levels (a reduced segment spans <= 2^LV vectors), 1..7
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer CLS_DRAIN = 0,
    parameter integer KVT_SH = 9,
    parameter integer BCAST_STAGES = 0, // ot_hdc_v41x_vec: controller -> lane broadcast tree stages
    parameter integer RET_STAGES = 0,   // ot_hdc_v41x_vec: lane / reducer -> vector-memory write stages
    parameter integer MLAT = 3,         // ot_hdc_v41x_vec: multiplier latency (3, 4 or 5: W11 serial domain)
    parameter integer ALAT = 3          // ot_hdc_v41x_vec: FP add latency (3, or 4)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output wire              idle,
    input  wire [NW-1:0]     i_nout, i_nin, i_chase,
    input  wire [1:0]        i_asrc, i_bsrc, i_csrc, i_dsrc,
    input  wire [AW-1:0]     i_abase, i_aso, i_asi, i_aibase,
    input  wire [1:0]        i_aind,
    input  wire [AW-1:0]     i_bbase, i_bso, i_bsi,
    input  wire              i_bhalf,
    input  wire [AW-1:0]     i_cbase, i_cso, i_csi,
    input  wire              i_cpair,
    input  wire [AW-1:0]     i_dbase, i_dso, i_dsi,
    input  wire              i_arnd, i_arelu, i_amin, i_cclip,
    input  wire [2:0]        i_m1,
    input  wire [1:0]        i_m2,
    input  wire [2:0]        i_qm, i_ad, i_sfu, i_e1,
    input  wire [1:0]        i_e2,
    input  wire              i_rnd,
    input  wire [1:0]        i_dst,
    input  wire [AW-1:0]     i_obase, i_oso, i_osi, i_orow,
    input  wire [1:0]        i_red,
    input  wire              i_redsq, i_redwhole, i_redtree, i_redrnd,
    input  wire [AW-1:0]     i_rbase, i_rso,
    input  wire [31:0]       i_imm1, i_imm2, i_imm3,
    input  wire [2:0]        i_m,
    input  wire [AW-1:0]     i_xps, i_ops,
    // the vector unit's memory ports
    output wire [N-1:0]      vi_re,
    output wire [N*AW-1:0]   vi_addr,
    input  wire [N*32-1:0]   vi_q,
    output wire [4*N*AW-1:0] rd_addr,
    output wire [4*N-1:0]    rd_re,
    output wire [8*N-1:0]    rd_src,
    input  wire [4*N*32-1:0] rd_q,
    output wire [N-1:0]      vm_we,
    output wire [N*AW-1:0]   vm_waddr,
    output wire [N*32-1:0]   vm_wdata,
    output wire [N-1:0]      kv_we,
    output wire [N*AW-1:0]   kv_waddr,
    output wire [N*32-1:0]   kv_wdata,
    output wire [N/8-1:0]    res_we,
    output wire [N/8*AW-1:0] res_addr,
    output wire [N/8*32-1:0] res_data,
    output wire              fault,
    output wire [31:0]       dbg_ops, dbg_elems
);
    ot_s81ph_su_xing #(.DF(`S81PH_DF), .DR(`S81PH_DR), .NEG(`S81PH_NEG), .N(N), .M(M), .LV(LV), .AW(AW), .NW(NW), .CLS_DRAIN(CLS_DRAIN), .KVT_SH(KVT_SH), .BCAST_STAGES(BCAST_STAGES), .RET_STAGES(RET_STAGES), .MLAT(MLAT), .ALAT(ALAT)) u_x (.*);
endmodule
