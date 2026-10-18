`timescale 1ns/1ps
`default_nettype none
// HBM-B-RTL1 2026-10-17 (plan (b) d4g): the QUADRANT SM result -> VM writer smw_<Q> = ot_hbm_sm_vm_wr_q_t_lanes with the
// writer core ot_hbm_sm_vm_wr_q_lanes_n #(NL 4, LBPIN 1, NB2 2): the quadrant's 4 SMs (ports s0..s3 = SM LB+0..LB+3 of the stack;
// d4f stack index) write banks LB+k (half 0, wq_s<k> -> vmb_<Q>{LB+k}.wq1) or (LB+k+4)%8 (half 1, wq_t<k>), LB = 4*lbase (strap pin: ONE
// master for all four quadrant writers), of the
// quadrant's own VM slice, per descriptor bit cmd[26] (calendar entry {cmd27, at32}; d4f entries are {cmd26, at32}).  W quadrants
// LB 0, E quadrants LB 4 (the same bank index as the d4f stack writer; only the quad strap changes to the SM's quadrant).
// Calendar target, descriptor ABI, table SRAM, timing (calendar fire edge C_launch + 2 + LEAD + at; rv(t) -> wq slot 0 at
// t+3), faults and MUT 1/2/3/4 are those of ot_hbm_sm_vm_wr_q_t_lanes; MUT 6 = bank base ignored.  Pin rule: every data
// input lands on a lane-root pin flop, rst_n on ONE root flop then the hub 2-flop sync + one relay per lane (as t_lanes).
// Bench: rtl/hbm_accel/generic/vm/static/run_sm_vm_wr_q_t_lanes4.sh (lockstep against the d4f 8-SM writer).
// Original header:
// H-WRQ 2026-10-17: the HARDENED writer master smw_<q> with ONE CLOCK ROOT PER SM LANE (results/rtl/hsm_wrq_1017/DESIGN_NOTE.md).
//   = ot_static_cmd_target_core (MODE 1 SEQ command calendar CW 26, TGT_PIN strap; its pin flops / sequencer on the shared
//     core root clk) + its 128x256 table SRAM (raw entry clk_cal) + ot_hbm_sm_vm_wr_q_lanes (SM lane k on clk_l<k>).
// Logically identical to ot_hbm_sm_vm_wr_q_t / _t_faces4 (same timing: calendar fire edge C_launch + 2 + LEAD + at; rv(t) ->
// wq slot 0 at t+3).  Per-SM ports (SM k): rv_s<k> = rv[k], rrow_s<k> = rrow[12k+:12], rdata_s<k> = rdata[256k+:256],
// smf_s<k> = sm_fault[k], sms_s<k> = sm_sched_fault[k], wq_s<k> = wq[281k+:281] (bank k write group).  clk, clk_cal and
// clk_l0..7 are the same PLL output at phase 0 (die: pll_stream); benches tie them together.
// MUT: 1/2/3 pass to the writer (wrong row / late phase / quad strap ignored); 4 = calendar fires one edge late.
module ot_hbm_sm_vm_wr_q_t_lanes4 #(parameter integer DEPTH = 4, parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          clk_cal,
    input  wire          rst_n,
    input  wire [7:0]    tgt,
    input  wire [1:0]    quad,
    input  wire          lbase,     // bank-base strap: 0 = W quadrant (half 0 = banks 0-3), 1 = E (half 0 = banks 4-7)
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
    output wire [280:0]  wq_t0,       // half 1: bank (LB+0+4)%8
    input  wire          clk_l1, rv_s1, smf_s1, sms_s1,
    input  wire [11:0]   rrow_s1,
    input  wire [255:0]  rdata_s1,
    output wire [280:0]  wq_s1,
    output wire [280:0]  wq_t1,       // half 1: bank (LB+1+4)%8
    input  wire          clk_l2, rv_s2, smf_s2, sms_s2,
    input  wire [11:0]   rrow_s2,
    input  wire [255:0]  rdata_s2,
    output wire [280:0]  wq_s2,
    output wire [280:0]  wq_t2,       // half 1: bank (LB+2+4)%8
    input  wire          clk_l3, rv_s3, smf_s3, sms_s3,
    input  wire [11:0]   rrow_s3,
    input  wire [255:0]  rdata_s3,
    output wire [280:0]  wq_s3,
    output wire [280:0]  wq_t3,       // half 1: bank (LB+3+4)%8
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
    wire [26:0] cmd;
    wire t_rce; wire [6:0] t_ra, t_wa; wire [0:0] t_wce; wire [255:0] t_wd, t_rd;
    ot_static_cmd_target_core #(.TARGET(8'hff), .MODE(1), .CW(27), .RELF(0), .NA(1), .NF(1),
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
    ot_hbm_sm_vm_wr_q_lanes_n #(.DEPTH(DEPTH), .NL(4), .LB(0), .LBPIN(1), .NB2(2), .MUT(((MUT >= 1 && MUT <= 3) || MUT == 6) ? MUT : 0)) u_wrq (
        .clk(clk), .clk_l({clk_l3,clk_l2,clk_l1,clk_l0}), .rst_n(rst_q), .quad(quad), .lbase(lbase),
        .rv({rv_s3,rv_s2,rv_s1,rv_s0}), .rrow({rrow_s3,rrow_s2,rrow_s1,rrow_s0}),
        .rdata({rdata_s3,rdata_s2,rdata_s1,rdata_s0}),
        .cmd_v(cmd_v), .cmd(cmd), .sm_fault({smf_s3,smf_s2,smf_s1,smf_s0}), .sm_sched_fault({sms_s3,sms_s2,sms_s1,sms_s0}),
        .wq({wq_t3,wq_t2,wq_t1,wq_t0,wq_s3,wq_s2,wq_s1,wq_s0}), .busy(w_busy), .fault(w_fault));
endmodule
`default_nettype wire
