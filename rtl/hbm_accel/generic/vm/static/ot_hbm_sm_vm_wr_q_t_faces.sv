`timescale 1ns/1ps
`default_nettype none
// H-SM svc helper 2026-10-16: the HARDENED master of the quadrant SM-result -> VM writer smw_<q> (option A, H-NETLIST /
// H-DIE decision 06:5x: every ot_static_cmd_target is folded into its consumer as pin-registered soft logic).
//   = ot_static_cmd_target (MODE 1 SEQ: the compiler command calendar, CW 26 = the writer descriptor, one 128x256 SRAM
//     table, TGT_PIN 1) + ot_hbm_sm_vm_wr_q (quad strap).
// One master for the 4 instances: identity strap tgt[7:0] and quadrant strap quad[1:0] are die constants captured in pin
// flops.  The face takes the raw ot_hbm_host_static_ingress F20 broadcast; the writer's descriptor cmd_v/cmd, busy and
// fault become internal (busy -> collar tgt_active, fault -> collar tgt_fault); status leaves as configured/fault/active.
// Timing: a calendar entry {cmd26, at32} fires cmd_v on the edge where the collar cycle == C_launch + 2 + LEAD + at (the
// same edge the die-level collar fired before the fold); the writer keeps rv(t) -> wq slot 0 at t+3.
// Reset: rst_n lands on ONE local reset-release flop; collar and writer clear from rst_q.
// MUT: 1/2/3 pass to ot_hbm_sm_vm_wr_q (wrong row / late phase / quad strap ignored); 4 = calendar fires one edge late.
module ot_hbm_sm_vm_wr_q_t_faces #(parameter integer DEPTH = 4, parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          clk_in,            // W-face input flop root (see ot_hbm_sm_vm_wr_q)
    input  wire          clk_out,           // E-face wq output flop root
    input  wire          rst_n,
    input  wire [7:0]    tgt,
    input  wire [1:0]    quad,
    input  wire          cfg_v,
    input  wire [7:0]    cfg_target,
    input  wire [11:0]   cfg_addr,
    input  wire [255:0]  cfg_data,
    input  wire          desc_v,
    input  wire [11:0]   desc_base,
    input  wire [12:0]   desc_limit,
    input  wire [15:0]   desc_loops,
    input  wire          launch_v,
    input  wire [7:0]    rv,
    input  wire [95:0]   rrow,
    input  wire [1023:0] rdata_lo,          // SM 0..3 result columns (= rdata[1023:0] of ot_hbm_sm_vm_wr_q); split so the
    input  wire [1023:0] rdata_hi,          // W-face clock entry clk_in sits at the face centre between the halves
    input  wire [7:0]    sm_fault,
    input  wire [7:0]    sm_sched_fault,
    output wire [1123:0] wq_lo,             // banks 0..3 write groups (= wq[1123:0]); split for the E-face clock entry
    output wire [1123:0] wq_hi,             // banks 4..7 (= wq[2247:1124])
    output wire          configured,
    output wire          fault,
    output wire          active
);
    reg rst_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rst_q <= 1'b0;
        else        rst_q <= 1'b1;
    wire cmd_v, w_busy, w_fault;
    wire [25:0] cmd;
    ot_static_cmd_target #(.TARGET(8'hff), .MODE(1), .CW(26), .RELF(0), .NA(1), .NF(1),
        .MUT((MUT == 4) ? 1 : 0), .TGT_PIN(1)) u_tgt (
        .clk(clk), .rst_n(rst_q), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops),
        .launch_v(launch_v), .tgt_active(w_busy), .tgt_fault(w_fault),
        .a_we(), .a_addr(), .a_data(), .b_we(), .b_addr(), .b_data(), .run_v(), .run_base(), .run_count(),
        .cmd_v(cmd_v), .cmd(cmd), .cycle(), .configured(configured), .fault(fault), .active(active));
    ot_hbm_sm_vm_wr_q_faces #(.DEPTH(DEPTH), .MUT((MUT >= 1 && MUT <= 3) ? MUT : 0)) u_wrq (
        .clk(clk), .clk_in(clk_in), .clk_out(clk_out), .rst_n(rst_q), .quad(quad), .rv(rv), .rrow(rrow), .rdata({rdata_hi, rdata_lo}), .cmd_v(cmd_v), .cmd(cmd),
        .sm_fault(sm_fault), .sm_sched_fault(sm_sched_fault), .wq({wq_hi, wq_lo}), .busy(w_busy), .fault(w_fault));
endmodule
`default_nettype wire
