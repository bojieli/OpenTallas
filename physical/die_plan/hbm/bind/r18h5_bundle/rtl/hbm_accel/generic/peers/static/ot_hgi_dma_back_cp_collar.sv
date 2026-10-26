`timescale 1ns/1ps
`default_nettype none
// HCDMA-DBK 2026-10-17: the DMA dispatcher collar of hb_dbk (ot_hgi_dma_back_static_vp4_banks_cp) as ONE hard leaf:
// ot_static_cmd_target_core MODE 1 (SEQ), CW 308, RELF 2, TGT_PIN 1 + its two 128x256 command-table SRAMs, all on the
// leaf clock clk (compact CTS root inside the leaf; the table SRAMs are leaf macros on that tree).  Pin rule: every input
// lands in a core pin flop (cfg/desc/launch/tgt/tgt_active/tgt_fault), every output is a core register (cmd_v, cmd,
// cycle, configured, fault, active), rst_n loads exactly one pin flop.  Function = the core exactly as folded before
// (same instance of ot_static_cmd_target_core, same table wiring); the reset release is one edge after the pin.
module ot_hgi_dma_back_cp_collar (
    input wire clk,rst_n,
    input wire [7:0] tgt,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    input wire tgt_active,tgt_fault,
    output wire cmd_v,
    output wire [307:0] cmd,
    output wire [31:0] cycle,
    output wire configured,fault,active
);
    // rst_n pin flop: asynchronous assert, release on the next clk edge (the pin is driven by a parent relay flop, so
    // it is already synchronous); the pin net loads exactly this flop.
    (* keep = "true" *) reg rst_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rst_q <= 1'b0; else rst_q <= 1'b1;
    wire t_rce; wire [6:0] t_raddr,t_waddr; wire [1:0] t_wce; wire [255:0] t_wdata; wire [511:0] t_rd;
    ot_static_cmd_target_core #(.MODE(1),.CW(308),.RELF(2),.NA(1),.NF(1),.TGT_PIN(1)) u_core(
        .clk(clk),.rst_n(rst_q),.tgt(tgt),
        .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .tgt_active(tgt_active),.tgt_fault(tgt_fault),
        .a_we(),.a_addr(),.a_data(),.b_we(),.b_addr(),.b_data(),.run_v(),.run_base(),.run_count(),   // MODE 1: no windows/run
        .cmd_v(cmd_v),.cmd(cmd),.cycle(cycle),.configured(configured),.fault(fault),.active(active),
        .tab_r_ce(t_rce),.tab_r_addr(t_raddr),.tab_rd_word(t_rd),.tab_w_ce(t_wce),.tab_w_addr(t_waddr),.tab_w_data(t_wdata));
    for (genvar w = 0; w < 2; w = w + 1) begin : g_tab
        ot_sram_1r1w_128x256_m1_r2c2 u_tab(.clk(clk),.r_ce_in(t_rce),.r_addr_in(t_raddr),.rd_out(t_rd[w*256+:256]),
            .w_ce_in(t_wce[w]),.w_addr_in(t_waddr),.wd_in(t_wdata),.w_mask_in({256{1'b1}}),
            .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(16'b0));
    end
endmodule
`default_nettype wire
