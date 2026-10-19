`timescale 1ns/1ps
`default_nettype none
// HBM-FAULT 2026-10-17: host status join + fault-aggregation tree root (coordinator 0da+ (b)).
// ot_hbm_status_join unchanged inside; NA region roots of the ot_hbm_fault_leaf tree join here.
//  * a_fault[i] (region root i, pulse or level) -> pin flop -> cause[i] (sticky, region cause vector).
//  * Any cause holds block_ready low (the ingress refuses the next launch) and raises die_fault (the host packet
//    sends its {fault, irq} status flit at once). program_fault is NOT raised, so configuration writes stay open
//    and the host can clear after logging the fault.
//  * Sticky here only: the leaves are registered ORs, so a pulse reaches a_fault exactly once and a level source
//    keeps a_fault high. Clear: an F20 configuration row to target FCLR (cfg_v with cfg_target == FCLR; the ingress
//    TARGET_MASK admits it, no target consumes it) clears cause; a source still faulting (level) re-sets it on the
//    next edge, a pulse still in flight in the tree at the clear sets it when it lands (both are real faults).
//    The join's own GUARD (8 edges after any cfg row) keeps block_ready low across the clear.
//  * Latency: a_fault -> cause 2 edges -> die_fault / block_ready 3 edges. block_ready and die_fault carry one
//    more register than in ot_hbm_status_join (configuration latency only); program_active/program_fault/irq are
//    the join's flops unchanged. a_cause = the sticky region cause (host read map: ingress follow-up).
// FMUT (bench only): 1 not sticky, 2 clear ignored, 3 block_ready not gated.
// HBM-TILES-A2 2026-10-17 (hardened master, successor of hdie_host_status_r2 which hardens the bare join): parameter
// defaults = the d4f host_status instance (NT67/NF105/NH6 + its target list, as ot_hbm_status_join), so the master
// needs no parameter override. RRELAY (default 0 = unchanged) is passed to the join and, when 1, the wrapper's own
// flops (a_q/cv_q/a_cause/block_ready/die_fault; ct_q has no reset) reset from a 1-region ot_rst_relay with the same
// 2+1 stages, so rst_n drives only the two relays and every region releases on the same edge (cycle-exact with
// RRELAY=0 driven by a relayed reset: tb_hbm_status_join_fa_relay).
module ot_hbm_status_join_fa #(
    parameter integer NT=67,
    parameter integer NF=105,
    parameter integer NH=6,
    parameter [NT*8-1:0] TGTS=536'hd7d6d5d4d3d2d1d0c7c6c5c4c3c2c1c0a5a4a2a0878685846f6e6d6c6a68666463626160575655545352515047464544434241403b3a39387877767574703736353430,
    parameter integer GUARD=8,
    parameter integer MUT=0,
    parameter integer NA=4,                 // fault-tree region roots
    parameter [7:0] FCLR=8'd125,            // F20 target id of the fault clear
    parameter integer FMUT=0,
    parameter integer RRELAY=0
)(
    input  wire clk, rst_n,
    input  wire cfg_v, desc_v, launch_v,
    input  wire [7:0] cfg_target,
    input  wire [NT-1:0] t_ready, t_active,
    input  wire [NF-1:0] t_fault,
    input  wire [NH-1:0] h_fault,
    input  wire [NA-1:0] a_fault,
    output reg  block_ready,
    output wire program_active, program_fault, irq,
    output reg  die_fault,
    output reg  [NA-1:0] a_cause
);
    wire jb, jd;
    ot_hbm_status_join #(.NT(NT), .NF(NF), .NH(NH), .TGTS(TGTS), .GUARD(GUARD), .MUT(MUT), .RRELAY(RRELAY)) join_core (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .desc_v(desc_v), .launch_v(launch_v), .cfg_target(cfg_target),
        .t_ready(t_ready), .t_active(t_active), .t_fault(t_fault), .h_fault(h_fault),
        .block_ready(jb), .program_active(program_active), .program_fault(program_fault), .die_fault(jd), .irq(irq));
    reg [NA-1:0] a_q;
    reg cv_q;
    reg [7:0] ct_q;
    wire fclr = cv_q && ct_q == FCLR && FMUT != 2;
    always @(posedge clk) ct_q <= cfg_target;
    wire fa_rst_n;
    generate if (RRELAY != 0) begin : g_frr
        wire [0:0] frr;
        ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_frr (.clk(clk), .rst_n_in(rst_n), .rst_n(frr));
        assign fa_rst_n = frr[0];
    end else begin : g_frr0
        assign fa_rst_n = rst_n;
    end endgenerate
    always @(posedge clk or negedge fa_rst_n)
        if (!fa_rst_n) begin
            a_q <= {NA{1'b0}}; cv_q <= 1'b0; a_cause <= {NA{1'b0}};
            block_ready <= 1'b0; die_fault <= 1'b0;
        end else begin
            a_q <= a_fault; cv_q <= cfg_v;
            a_cause <= fclr ? {NA{1'b0}} : (FMUT == 1) ? a_q : (a_cause | a_q);
            block_ready <= jb && (FMUT == 3 || (a_cause == {NA{1'b0}} && !fclr));
            die_fault <= jd || (|a_cause);
        end
endmodule
`default_nettype wire
