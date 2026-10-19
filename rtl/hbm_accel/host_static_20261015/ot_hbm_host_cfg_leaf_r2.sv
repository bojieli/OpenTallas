`timescale 1ns/1ps
`default_nettype none
// HBM-RTL5 2026-10-18 (coordinator 0fi): d4g SE / NE host config/status leaves re-hardened at the widths that carry the
// six new E-quadrant targets of the d4g L1 layer (x-load ctlx 101/103, DMA/write-back hb_dbk 105/107, refresh refcfg
// 128/129) and the wbk_<E> fault through the leaf instead of straight into host_status:
//   SE  NT 18 -> 21 (+ xl_SE_ctl, hb_dbk_SE, refcfg_SE), NF 26 -> 30 (+ their faults + wbk_SE.fault)
//   NE  NT 14 -> 17 (+ xl_NE_ctl, hb_dbk_NE, refcfg_NE), NF 23 -> 27 (+ their faults + wbk_NE.fault)
// Same datapath as ot_hbm_host_cfg_leaf2 (CFG_LAT 2, ST_LAT 2, synced rst_n), exact widths (every status input is driven
// by a real target / source pin, every output is sunk; no tie).  The new bits are appended at the top of each status
// vector (s_ready[18..20] SE / [14..16] NE, s_fault[26..29] / [23..26]); bits below keep the r1 order.
// MUT (bench only): 1..4 as ot_hbm_host_cfg_leaf (passed down); 5 s_ready[NT-1] inverted (new slot); 6 s_fault[NF-1]
// inverted (new slot); 7 s_fault[NT-1] forced 0 (new target's fault[0] in the bench map).
module ot_hbm_host_cfg_leaf_se2 #(parameter integer MUT = 0) (
    input  wire clk, rst_n,
    input  wire cfg_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr, input wire [255:0] cfg_data,
    input  wire desc_v, input wire [11:0] desc_base, input wire [12:0] desc_limit, input wire [15:0] desc_loops,
    input  wire launch_v,
    output wire a_cfg_v, output wire [7:0] a_cfg_target, output wire [11:0] a_cfg_addr, output wire [255:0] a_cfg_data,
    output wire a_desc_v, output wire [11:0] a_desc_base, output wire [12:0] a_desc_limit, output wire [15:0] a_desc_loops,
    output wire a_launch_v,
    output wire b_cfg_v, output wire [7:0] b_cfg_target, output wire [11:0] b_cfg_addr, output wire [255:0] b_cfg_data,
    output wire b_desc_v, output wire [11:0] b_desc_base, output wire [12:0] b_desc_limit, output wire [15:0] b_desc_loops,
    output wire b_launch_v,
    input  wire [20:0] t_ready, t_active, input wire [29:0] t_fault,
    output wire [20:0] s_ready, s_active, output wire [29:0] s_fault
);
    localparam integer NT = 21, NF = 30;
    wire [NT-1:0] u_rdy; wire [NF-1:0] u_flt;
    ot_hbm_host_cfg_leaf2 #(.NT(NT), .NF(NF), .MUT(MUT < 5 ? MUT : 0)) u (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .a_cfg_v(a_cfg_v), .a_cfg_target(a_cfg_target), .a_cfg_addr(a_cfg_addr), .a_cfg_data(a_cfg_data),
        .a_desc_v(a_desc_v), .a_desc_base(a_desc_base), .a_desc_limit(a_desc_limit), .a_desc_loops(a_desc_loops),
        .a_launch_v(a_launch_v), .b_cfg_v(b_cfg_v), .b_cfg_target(b_cfg_target), .b_cfg_addr(b_cfg_addr),
        .b_cfg_data(b_cfg_data), .b_desc_v(b_desc_v), .b_desc_base(b_desc_base), .b_desc_limit(b_desc_limit),
        .b_desc_loops(b_desc_loops), .b_launch_v(b_launch_v), .t_ready(t_ready), .t_active(t_active),
        .t_fault(t_fault), .s_ready(u_rdy), .s_active(s_active), .s_fault(u_flt));
    assign s_ready = (MUT == 5) ? (u_rdy ^ ({{(NT-1){1'b0}}, 1'b1} << (NT - 1))) : u_rdy;
    assign s_fault = (MUT == 6) ? (u_flt ^ ({{(NF-1){1'b0}}, 1'b1} << (NF - 1)))
                   : (MUT == 7) ? (u_flt & ~({{(NF-1){1'b0}}, 1'b1} << (NT - 1))) : u_flt;
endmodule
module ot_hbm_host_cfg_leaf_ne2 #(parameter integer MUT = 0) (
    input  wire clk, rst_n,
    input  wire cfg_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr, input wire [255:0] cfg_data,
    input  wire desc_v, input wire [11:0] desc_base, input wire [12:0] desc_limit, input wire [15:0] desc_loops,
    input  wire launch_v,
    output wire a_cfg_v, output wire [7:0] a_cfg_target, output wire [11:0] a_cfg_addr, output wire [255:0] a_cfg_data,
    output wire a_desc_v, output wire [11:0] a_desc_base, output wire [12:0] a_desc_limit, output wire [15:0] a_desc_loops,
    output wire a_launch_v,
    output wire b_cfg_v, output wire [7:0] b_cfg_target, output wire [11:0] b_cfg_addr, output wire [255:0] b_cfg_data,
    output wire b_desc_v, output wire [11:0] b_desc_base, output wire [12:0] b_desc_limit, output wire [15:0] b_desc_loops,
    output wire b_launch_v,
    input  wire [16:0] t_ready, t_active, input wire [26:0] t_fault,
    output wire [16:0] s_ready, s_active, output wire [26:0] s_fault
);
    localparam integer NT = 17, NF = 27;
    wire [NT-1:0] u_rdy; wire [NF-1:0] u_flt;
    ot_hbm_host_cfg_leaf2 #(.NT(NT), .NF(NF), .MUT(MUT < 5 ? MUT : 0)) u (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .a_cfg_v(a_cfg_v), .a_cfg_target(a_cfg_target), .a_cfg_addr(a_cfg_addr), .a_cfg_data(a_cfg_data),
        .a_desc_v(a_desc_v), .a_desc_base(a_desc_base), .a_desc_limit(a_desc_limit), .a_desc_loops(a_desc_loops),
        .a_launch_v(a_launch_v), .b_cfg_v(b_cfg_v), .b_cfg_target(b_cfg_target), .b_cfg_addr(b_cfg_addr),
        .b_cfg_data(b_cfg_data), .b_desc_v(b_desc_v), .b_desc_base(b_desc_base), .b_desc_limit(b_desc_limit),
        .b_desc_loops(b_desc_loops), .b_launch_v(b_launch_v), .t_ready(t_ready), .t_active(t_active),
        .t_fault(t_fault), .s_ready(u_rdy), .s_active(s_active), .s_fault(u_flt));
    assign s_ready = (MUT == 5) ? (u_rdy ^ ({{(NT-1){1'b0}}, 1'b1} << (NT - 1))) : u_rdy;
    assign s_fault = (MUT == 6) ? (u_flt ^ ({{(NF-1){1'b0}}, 1'b1} << (NF - 1)))
                   : (MUT == 7) ? (u_flt & ~({{(NF-1){1'b0}}, 1'b1} << (NT - 1))) : u_flt;
endmodule
`default_nettype wire
