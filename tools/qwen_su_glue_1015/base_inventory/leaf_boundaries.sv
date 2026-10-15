(* blackbox *) module ot_hdc_vstream_lane_clock_entries_candidate #(
    parameter integer WR   = 64,
    parameter integer AW   = 24,
    parameter integer NW   = 16,
    parameter integer KV_FP8 = 1,
    parameter integer ML   = 0,          // the memory latency at the vstream ports (answer at 1 + ML edges)
    parameter integer RD   = 1,          // parent relay stages each way between the vstream ports and this tile
    // el1011-q-sp 2026-10-11: the hardened tile's fp32 latencies (lane QLA / QLM).  Defaults = the hardened
    // configuration (a parent instantiates the hard tile with no overrides): mul 5 (CSA tree | prefix add | round),
    // add 4 (prefix adds split from the alignment).  The tile's results are tagged; only the lane latency grows.
    parameter integer QLA  = 4,
    parameter integer QLM  = 5
) (
    input wire ck_head,ck_exp,ck_rcp,ck_rsq,
    input  wire              rst_n,
    input  wire              emit0,
    input  wire              live,
    input  wire [NW-1:0]     i,
    input  wire [NW:0]       fin_th,
    input  wire              i_last_r,
    input  wire [AW-1:0]     cura0, curb0, curc0, curd0, rrow,
    input  wire [AW-1:0]     asi, bsi, csi, dsi,
    input  wire              asrc, bsrc, csrc, mc, md, redsq,
    input  wire [1:0]        ma, mb, dst, red,
    input  wire [2:0]        ad,
    input  wire [31:0]       imm1, imm2,
    input  wire [2:0]        cls,
    input  wire              accept,
    input  wire [2:0]        i_sfu,
    output wire              va_re,
    output wire [AW-1:0]     va_addr,
    input  wire [31:0]       va_q,
    output wire              vb_re,
    output wire [AW-1:0]     vb_addr,
    input  wire [31:0]       vb_q,
    output wire              vc_re,
    output wire [AW-1:0]     vc_addr,
    input  wire [31:0]       vc_q,
    output wire              wrom_re,
    output wire [AW-1:0]     wrom_addr,
    input  wire [WR*16-1:0]  wrom_q,
    output wire              crom_re,
    output wire [AW-1:0]     crom_addr,
    input  wire [63:0]       crom_q,
    output wire              vm_we,
    output wire [AW-1:0]     vm_waddr,
    output wire [31:0]       vm_wdata,
    output wire              kv_we,
    output wire [AW-1:0]     kv_waddr,
    output wire [31:0]       kv_wdata,
    output wire              l_ov,
    output wire [31:0]       l_out,
    output wire [1:0]        l_red,
    output wire              l_redsq,
    output wire [AW-1:0]     l_raddr,
    output wire              l_last,
    output wire              retire,
    output wire              l_fault
);
endmodule

(* blackbox *) module ot_qfd_su_align_group4 #(
    parameter integer ML=15, VL=7, MC=4
) (
    input wire clk, rst_n,
    input wire [383:0] vm_q,
    input wire [255:0] crom_q,
    input wire [127:0] emb_q,
    input wire [3:0] emb_sel,
    input wire [11:0] vm_mask,
    output wire [383:0] vm_eff,
    output wire [255:0] crom_m,
    output wire [127:0] emb_m,
    output wire [3:0] emb_sel_m
);
endmodule

(* blackbox *) module qfd_su_vred_entries64 #(parameter integer QLA=4,QLM=5)(
 input wire ck_region0,ck_region1,ck_region2,ck_region3,ck_region4,ck_region5,ck_region6,ck_region7,ck_tail,rst_n,
 input wire v_in,mx_in,sq_in,last_in,input wire [23:0]addr_in,input wire [2047:0]x_in,
 output wire o_we,output wire [23:0]o_addr,output wire [31:0]o_data,output wire busy,fault);
endmodule

(* blackbox *) module ot_qfd_su_lane_relay #(
    parameter integer AW=24, NW=18, WR=16, RD=2,
    parameter integer RTREE=0,
    parameter integer GBW=NW+(NW+1)+5*AW+6+8+9+64+WR*16,
    parameter integer PDW=4*AW+3*32+64,
    parameter integer OVW=11,
    parameter integer ODW=7*AW+2*32+32+2+1+AW
)(
    input wire clk, rst_n,
    input wire [GBW-1:0] b_d,
    input wire [2:0] b_v,
    input wire live,
    input wire [AW-1:0] cura,curb,curc,curd,
    input wire [159:0] mem_q,
    input wire [OVW-1:0] o_v,
    input wire [ODW-1:0] o_d,
    output wire rst_l,
    output wire [GBW-1:0] b_q,
    output wire [2:0] bv_q,
    output wire lv_q,
    output wire [PDW-1:0] p_q,
    output wire [OVW-1:0] o_vq,
    output wire [ODW-1:0] o_dq
);
endmodule
