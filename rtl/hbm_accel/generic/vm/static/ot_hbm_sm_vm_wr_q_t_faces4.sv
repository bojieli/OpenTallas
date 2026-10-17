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
module ot_hbm_sm_vm_wr_q_t_faces4 #(parameter integer DEPTH = 4, parameter integer MUT = 0) (
    input  wire          clk,
    input wire clk_in_lo,clk_in_hi,            // W-face input flop root (see ot_hbm_sm_vm_wr_q)
    input  wire          clk_cal,           // raw hard calendar SRAM clock entry
    input  wire          clk_hcfg,          // N-face host pin-flop clock entry (cfg/desc/launch/tgt pin flops; H-SM 1815)
    input wire clk_out_lo,clk_out_hi,           // E-face wq output flop root
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
    input wire [3:0]rv_lo,rv_hi,
    input wire [47:0]rrow_lo,rrow_hi,
    input  wire [1023:0] rdata_lo,          // SM 0..3 result columns (= rdata[1023:0] of ot_hbm_sm_vm_wr_q); split so the
    input  wire [1023:0] rdata_hi,          // W-face clock entry clk_in sits at the face centre between the halves
    input wire [3:0]sm_fault_lo,sm_fault_hi,
    input wire [3:0]sm_sched_fault_lo,sm_sched_fault_hi,
    output wire [1123:0] wq_lo,             // banks 0..3 write groups (= wq[1123:0]); split for the E-face clock entry
    output wire [1123:0] wq_hi,             // banks 4..7 (= wq[2247:1124])
    output wire          configured,
    output wire          fault,
    output wire          active
);
    wire[7:0]rv={rv_hi,rv_lo},sm_fault={sm_fault_hi,sm_fault_lo},sm_sched_fault={sm_sched_fault_hi,sm_sched_fault_lo};
    wire[95:0]rrow={rrow_hi,rrow_lo};
    reg rst_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rst_q <= 1'b0;
        else        rst_q <= 1'b1;
    wire cmd_v, w_busy, w_fault;
    wire [25:0] cmd;
    wire t_rce;wire[6:0]t_ra,t_wa;wire[0:0]t_wce;wire[255:0]t_wd,t_rd;
    ot_static_cmd_target_core_pc #(.TARGET(8'hff), .MODE(1), .CW(26), .RELF(0), .NA(1), .NF(1),
        .MUT((MUT == 4) ? 1 : 0), .TGT_PIN(1)) u_tgt (
        .clk(clk), .clk_pin(clk_hcfg), .rst_n(rst_q), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops),
        .launch_v(launch_v), .tgt_active(w_busy), .tgt_fault(w_fault),
        .a_we(), .a_addr(), .a_data(), .b_we(), .b_addr(), .b_data(), .run_v(), .run_base(), .run_count(),
        .cmd_v(cmd_v), .cmd(cmd), .cycle(), .configured(configured), .fault(fault), .active(active),
        .tab_r_ce(t_rce),.tab_r_addr(t_ra),.tab_rd_word(t_rd),.tab_w_ce(t_wce),.tab_w_addr(t_wa),.tab_w_data(t_wd));
    ot_sram_1r1w_128x256_m1_r2c2 u_tab(.clk(clk_cal),.r_ce_in(t_rce),.r_addr_in(t_ra),.rd_out(t_rd),
        .w_ce_in(t_wce[0]),.w_addr_in(t_wa),.wd_in(t_wd),.w_mask_in({256{1'b1}}),
        .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
    ot_hbm_sm_vm_wr_q_faces4 #(.DEPTH(DEPTH), .MUT((MUT >= 1 && MUT <= 3) ? MUT : 0)) u_wrq (
        .clk(clk), .clk_in_lo(clk_in_lo),.clk_in_hi(clk_in_hi),.clk_out_lo(clk_out_lo),.clk_out_hi(clk_out_hi), .rst_n(rst_q), .quad(quad), .rv(rv), .rrow(rrow), .rdata({rdata_hi, rdata_lo}), .cmd_v(cmd_v), .cmd(cmd),
        .sm_fault(sm_fault), .sm_sched_fault(sm_sched_fault), .wq({wq_hi, wq_lo}), .busy(w_busy), .fault(w_fault));
endmodule
`default_nettype wire
