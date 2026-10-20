`timescale 1ns/1ps
`default_nettype none
// HBM-SMBUDGET 2026-10-19: hardened master of the extension calendar xc_<q><k> for the relative SM service group
// (coordinator decision 0jx) = ot_static_run_target (2,048-row programme window: rows 1024..2047 through window 2; run
// argument ignored here: cmd_ext / kv_desc words are absolute) + ot_hbm_svc_sm_xcal_rel.  Same face, pins and lockstep
// rule as ot_hbm_svc_sm_xcal_t: both collars latch the same global launch_v and issue run_v two edges later.
// MUT: 1/2/3/4 pass to ot_hbm_svc_sm_xcal_rel; 5 = collar ignores the target id.
module ot_hbm_svc_sm_xcal_rel_t #(parameter integer MUT = 0, parameter integer PAW = 11, parameter integer PREL = 1,
    parameter integer DD = 256, parameter integer DAW = (DD > 128) ? 8 : 7) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    tgt,
    input  wire          cfg_v,
    input  wire [7:0]    cfg_target,
    input  wire [11:0]   cfg_addr,
    input  wire [255:0]  cfg_data,
    input  wire          desc_v,
    input  wire [11:0]   desc_base,
    input  wire [12:0]   desc_limit,
    input  wire [15:0]   desc_loops,
    input  wire          launch_v,
    output wire [108:0]  cmd_ext,
    output wire [63:0]   kv_desc,
    output wire          done,
    output wire          configured,
    output wire          fault,
    output wire          active
);
    reg rst_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rst_q <= 1'b0;
        else        rst_q <= 1'b1;
    wire a_we, b_we, run_v, x_active, x_fault;
    wire [PAW-1:0] a_addr; wire [DAW-1:0] b_addr; wire [255:0] a_data, b_data;
    wire [DAW-1:0] run_base; wire [DAW:0] run_count; wire [7:0] run_arg;
    ot_static_run_target #(.TARGET(8'hff), .AWA(PAW), .AWB(DAW), .RBW(DAW), .RCW(DAW + 1), .NA(1), .NF(1),
        .MUT((MUT == 5) ? 2 : 0), .TGT_PIN(1)) u_tgt (
        .clk(clk), .rst_n(rst_q), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops),
        .launch_v(launch_v), .tgt_active(x_active), .tgt_fault(x_fault),
        .a_we(a_we), .a_addr(a_addr), .a_data(a_data), .b_we(b_we), .b_addr(b_addr), .b_data(b_data),
        .run_v(run_v), .run_base(run_base), .run_count(run_count), .run_arg(run_arg),
        .configured(configured), .fault(fault), .active(active));
    ot_hbm_svc_sm_xcal_rel #(.MUT((MUT >= 1 && MUT <= 4) ? MUT : 0), .PAW(PAW), .PREL(PREL), .DD(DD)) u_xcal (
        .clk(clk), .rst_n(rst_q), .cfg_we(a_we), .cfg_addr(a_addr), .cfg_data(a_data),
        .desc_we(b_we), .desc_addr(b_addr), .desc_data(b_data), .run_v(run_v), .run_base(run_base), .run_count(run_count),
        .cmd_ext(cmd_ext), .kv_desc(kv_desc), .active(x_active), .done(done), .fault(x_fault));
    wire unused_arg = &{1'b0, run_arg};
endmodule
`default_nettype wire
