`timescale 1ns/1ps
`default_nettype none
// H-WRQ 2026-10-17: the HARDENED writer master smw_<q> with ONE CLOCK ROOT PER SM LANE (results/rtl/hsm_wrq_1017/DESIGN_NOTE.md).
//   = ot_static_cmd_target_core (MODE 1 SEQ command calendar CW 26, TGT_PIN strap; its pin flops / sequencer on the shared
//     core root clk) + its 128x256 table SRAM (raw entry clk_cal) + ot_hbm_sm_vm_wr_q_lanes (SM lane k on clk_l<k>).
// Logically identical to ot_hbm_sm_vm_wr_q_t / _t_faces4 (same timing: calendar fire edge C_launch + 2 + LEAD + at; rv(t) ->
// wq slot 0 at t+3).  Per-SM ports (SM k): rv_s<k> = rv[k], rrow_s<k> = rrow[12k+:12], rdata_s<k> = rdata[256k+:256],
// smf_s<k> = sm_fault[k], sms_s<k> = sm_sched_fault[k], wq_s<k> = wq[281k+:281] (bank k write group).  clk, clk_cal and
// clk_l0..7 are the same PLL output at phase 0 (die: pll_stream); benches tie them together.
// MUT: 1/2/3 pass to the writer (wrong row / late phase / quad strap ignored); 4 = calendar fires one edge late.
module ot_hbm_sm_vm_wr_q_t_lanes #(parameter integer DEPTH = 4, parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          clk_cal,
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
    input  wire          clk_l0, rv_s0, smf_s0, sms_s0,
    input  wire [11:0]   rrow_s0,
    input  wire [255:0]  rdata_s0,
    output wire [280:0]  wq_s0,
    input  wire          clk_l1, rv_s1, smf_s1, sms_s1,
    input  wire [11:0]   rrow_s1,
    input  wire [255:0]  rdata_s1,
    output wire [280:0]  wq_s1,
    input  wire          clk_l2, rv_s2, smf_s2, sms_s2,
    input  wire [11:0]   rrow_s2,
    input  wire [255:0]  rdata_s2,
    output wire [280:0]  wq_s2,
    input  wire          clk_l3, rv_s3, smf_s3, sms_s3,
    input  wire [11:0]   rrow_s3,
    input  wire [255:0]  rdata_s3,
    output wire [280:0]  wq_s3,
    input  wire          clk_l4, rv_s4, smf_s4, sms_s4,
    input  wire [11:0]   rrow_s4,
    input  wire [255:0]  rdata_s4,
    output wire [280:0]  wq_s4,
    input  wire          clk_l5, rv_s5, smf_s5, sms_s5,
    input  wire [11:0]   rrow_s5,
    input  wire [255:0]  rdata_s5,
    output wire [280:0]  wq_s5,
    input  wire          clk_l6, rv_s6, smf_s6, sms_s6,
    input  wire [11:0]   rrow_s6,
    input  wire [255:0]  rdata_s6,
    output wire [280:0]  wq_s6,
    input  wire          clk_l7, rv_s7, smf_s7, sms_s7,
    input  wire [11:0]   rrow_s7,
    input  wire [255:0]  rdata_s7,
    output wire [280:0]  wq_s7,
    output wire          configured,
    output wire          fault,
    output wire          active
);
    // reset release (as _t_faces4): rst_n lands on ONE local flop (root clk); collar and writer clear from rst_q
    reg rst_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rst_q <= 1'b0;
        else        rst_q <= 1'b1;
    wire cmd_v, w_busy, w_fault;
    wire [25:0] cmd;
    wire t_rce; wire [6:0] t_ra, t_wa; wire [0:0] t_wce; wire [255:0] t_wd, t_rd;
    ot_static_cmd_target_core #(.TARGET(8'hff), .MODE(1), .CW(26), .RELF(0), .NA(1), .NF(1),
        .MUT((MUT == 4) ? 1 : 0), .TGT_PIN(1)) u_tgt (
        .clk(clk), .rst_n(rst_q), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops),
        .launch_v(launch_v), .tgt_active(w_busy), .tgt_fault(w_fault),
        .a_we(), .a_addr(), .a_data(), .b_we(), .b_addr(), .b_data(), .run_v(), .run_base(), .run_count(),
        .cmd_v(cmd_v), .cmd(cmd), .cycle(), .configured(configured), .fault(fault), .active(active),
        .tab_r_ce(t_rce), .tab_r_addr(t_ra), .tab_rd_word(t_rd), .tab_w_ce(t_wce), .tab_w_addr(t_wa), .tab_w_data(t_wd));
    ot_sram_1r1w_128x256_m1_r2c2 u_tab(.clk(clk_cal), .r_ce_in(t_rce), .r_addr_in(t_ra), .rd_out(t_rd),
        .w_ce_in(t_wce[0]), .w_addr_in(t_wa), .wd_in(t_wd), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    ot_hbm_sm_vm_wr_q_lanes #(.DEPTH(DEPTH), .MUT((MUT >= 1 && MUT <= 3) ? MUT : 0)) u_wrq (
        .clk(clk), .clk_l({clk_l7,clk_l6,clk_l5,clk_l4,clk_l3,clk_l2,clk_l1,clk_l0}), .rst_n(rst_q), .quad(quad),
        .rv({rv_s7,rv_s6,rv_s5,rv_s4,rv_s3,rv_s2,rv_s1,rv_s0}), .rrow({rrow_s7,rrow_s6,rrow_s5,rrow_s4,rrow_s3,rrow_s2,rrow_s1,rrow_s0}),
        .rdata({rdata_s7,rdata_s6,rdata_s5,rdata_s4,rdata_s3,rdata_s2,rdata_s1,rdata_s0}),
        .cmd_v(cmd_v), .cmd(cmd), .sm_fault({smf_s7,smf_s6,smf_s5,smf_s4,smf_s3,smf_s2,smf_s1,smf_s0}), .sm_sched_fault({sms_s7,sms_s6,sms_s5,sms_s4,sms_s3,sms_s2,sms_s1,sms_s0}),
        .wq({wq_s7,wq_s6,wq_s5,wq_s4,wq_s3,wq_s2,wq_s1,wq_s0}), .busy(w_busy), .fault(w_fault));
endmodule
`default_nettype wire
