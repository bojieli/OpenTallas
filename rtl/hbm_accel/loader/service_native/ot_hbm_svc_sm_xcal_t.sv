`timescale 1ns/1ps
`default_nettype none
// H-SM svc helper 2026-10-16: the HARDENED master of the attention SM extension calendar xc_<q><k> (option A, H-NETLIST /
// H-DIE decision 06:5x: every ot_static_cmd_target is folded into its consumer as pin-registered soft logic).
//   = ot_static_cmd_target (MODE 0 RUN, AWA 10 programme window, AWB 7 descriptor window, RBW 7 / RCW 8, TGT_PIN 1)
//   + ot_hbm_svc_sm_xcal.
// The face takes the raw ot_hbm_host_static_ingress F20 broadcast plus the identity strap tgt[7:0] (die constant).  The
// extension calendar now owns its descriptor-table copy through its OWN window B (the host writes the same descriptor rows
// to the svg target and to this target) instead of the die fan-out of cp_svg b_* / run_*: both collars latch the same
// global launch_v and issue run_v two edges later on the same edge, so the svg issuer and this calendar start on the same
// edge exactly as before (bench tb_hbm_svc_sm_xcal_t: both collars behind one real ingress).
// Reset: rst_n lands on ONE local reset-release flop at the pin (r1 native capture 254.0 ps > 190 at rst_n); the collar
// and the calendar clear from rst_q.  Pins: every input lands in a pin flop (collar pin rung), every output is a flop.
// MUT: 1/2/3 pass to ot_hbm_svc_sm_xcal (late calendar / wrong field / reset never released); 4 = collar ignores the
// target id (takes the svg target's writes).
module ot_hbm_svc_sm_xcal_t #(parameter integer MUT = 0) (
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
    wire [9:0] a_addr; wire [6:0] b_addr; wire [255:0] a_data, b_data;
    wire [6:0] run_base; wire [7:0] run_count;
    ot_static_cmd_target #(.TARGET(8'hff), .MODE(0), .AWA(10), .AWB(7), .RBW(7), .RCW(8), .NA(1), .NF(1),
        .MUT((MUT == 4) ? 2 : 0), .TGT_PIN(1)) u_tgt (
        .clk(clk), .rst_n(rst_q), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops),
        .launch_v(launch_v), .tgt_active(x_active), .tgt_fault(x_fault),
        .a_we(a_we), .a_addr(a_addr), .a_data(a_data), .b_we(b_we), .b_addr(b_addr), .b_data(b_data),
        .run_v(run_v), .run_base(run_base), .run_count(run_count), .cmd_v(), .cmd(), .cycle(),
        .configured(configured), .fault(fault), .active(active));
    ot_hbm_svc_sm_xcal #(.MUT((MUT >= 1 && MUT <= 3) ? MUT : 0)) u_xcal (
        .clk(clk), .rst_n(rst_q), .cfg_we(a_we), .cfg_addr(a_addr), .cfg_data(a_data),
        .desc_we(b_we), .desc_addr(b_addr), .desc_data(b_data), .run_v(run_v), .run_base(run_base), .run_count(run_count),
        .cmd_ext(cmd_ext), .kv_desc(kv_desc), .active(x_active), .done(done), .fault(x_fault));
endmodule
`default_nettype wire
