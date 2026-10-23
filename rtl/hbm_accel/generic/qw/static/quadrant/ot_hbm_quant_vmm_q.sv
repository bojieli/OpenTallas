`timescale 1ns/1ps
`default_nettype none
// HBM-P4-QUANT 2026-10-23 (COORD R6(3), HBM-QLOCAL Step C item 3): one quadrant's QUANT + VM write-merge group of the
// d4g die, REPLICATED in all four quadrants (NW, NE, SW, SE) instead of the as-built NW-only hb_quant_NW / vmm_NW0..7 /
// hb_idx__nwsh.  Pure composition of hardened masters (soft glue, no logic, no flops added here -> 0 added cycles):
//   hb_quant_Q    ot_hgi_qdq_host_split_q #(Q)      programme leaf target id 8'h30+Q; children as hb_quant_NW
//   idx_share_Q   ot_hbm_idx_vm_share2_static_r     read group r3 of the 8 local banks shared by the local IDX operand
//                                                   reader (a: hb_idx__op_Q) and the local quantiser (b)
//   vmm_Q0..7     hfd_vms_wq2_merge                 bank k write port wq1 = local SM writer (smw_Q, wq1) OR quantiser
//                                                   bank k (wq2), the bank's wq_done1 steered back to wq_done1/wq_done2
// Every port lands on a quadrant-local role (hleaf_Q, hb_idx__op_Q, vmb_Q0..7, smw_Q, hb_vms_Q, obs_Q): there is no
// cross-quadrant lane.  The as-built NW engine never served another quadrant (its wq reached vmb_NW0..7 only), so the
// replicas add local engines; nothing moves out of NW.  Bank k ports are bank-indexed here; which smw_Q port feeds bank
// k (the NE/SE mirror) is die wiring, as in r18h5.
// Static schedule (rule 10-14): no credits, no ready, no arbitration; the compiler books each bank/edge for at most one
// read owner (IDX or QUANT) and one write source (SM or QUANT); double bookings raise the sticky faults.
// Timing law (benched by tb_hbm_quant_vmm_q_lockstep at RL 54 / BANK_RT 51): vm_rq = split rq +1 (share flop); bank face
// answers BANK_RT+1 edges after vm_rq; split RL = BANK_RT+3 (only BANK_RT 51 passes at RL 54: 48..54 swept);
// wq_m = split wq +2 (merge pin + merge flop); wq_done1/2 = bank done +1.
// Opt-in: nothing in the pinned die instantiates this module; the die generator binds it only under its quant_rep key
// (default off), so the pinned r18h5 composition is byte-identical.
module ot_hbm_quant_vmm_q #(
    parameter integer Q=0,              // 0 NW, 1 NE, 2 SW, 3 SE (gen_plan_v2 QS order)
    parameter integer RL=54,WC=4,XR=0,BANK_RT=51,DONE_LAT=5,  // RL = BANK_RT+3 (die value at hb_quant: RL 54)
    parameter integer MUT=0             // bench: 1 strap of quadrant Q^1; 2 vmm bank-pair 0/1 crossed; 3 vmm done steered late
)(
    input  wire        clk_program,clk_transport,clk_dec,rst_n,
    input  wire [3:0]  clk_lg,
    input  wire [3:0]  clk_share,
    input  wire [7:0]  clk_vmm,
    // configuration from hleaf_Q
    input  wire        cfg_v,
    input  wire [7:0]  cfg_target,
    input  wire [11:0] cfg_addr,
    input  wire [255:0] cfg_data,
    input  wire        desc_v,
    input  wire [11:0] desc_base,
    input  wire [12:0] desc_limit,
    input  wire [15:0] desc_loops,
    input  wire        launch_v,
    output wire        program_active,program_done,configured,
    // local IDX operand reader (hb_idx__op_Q) on the shared read group r3
    input  wire [135:0]  idx_rq,
    output wire [2055:0] idx_rr,
    // local VM banks vmb_Q0..7: read group r3, write port wq1, wq_done1
    output wire [135:0]  vm_rq,
    input  wire [2055:0] vm_rr,
    input  wire [8*281-1:0] wq_sm,     // smw_Q write leaf of bank k
    output wire [8*281-1:0] wq_m,      // to bank k wq1
    input  wire [7:0]  done_m,         // bank k wq_done1
    output wire [7:0]  wq_done1,wq_done2,vmm_flt,
    output wire        beat_done,record_done,fault,share_fault
);
    wire [135:0] q_rq; wire [2055:0] q_rr; wire [8*281-1:0] q_wq;
    ot_hgi_qdq_host_split_q #(.Q(Q),.RL(RL),.WC(WC),.XR(XR),.COMPACT(1),.QMUT(MUT==1?1:0)) hb_quant_Q(
        .clk_program(clk_program),.clk_transport(clk_transport),.clk_dec(clk_dec),.clk_lg(clk_lg),.rst_n(rst_n),
        .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .program_active(program_active),.program_done(program_done),.configured(configured),
        .rq(q_rq),.rr(q_rr),.wq(q_wq),.beat_done(beat_done),.record_done(record_done),.fault(fault));
    ot_hbm_idx_vm_share2_static_r #(.BANK_RT(BANK_RT)) idx_share_Q(
        .clk_pair(clk_share),.rst_n(rst_n),.a_rq(idx_rq),.b_rq(q_rq),.vm_rq(vm_rq),.vm_rr(vm_rr),
        .a_rr(idx_rr),.b_rr(q_rr),.fault(share_fault));
    for(genvar k=0;k<8;k=k+1) begin: vmm
        localparam integer KQ=(MUT==2&&k<2)?(k^1):k;
        hfd_vms_wq2_merge #(.DONE_LAT(DONE_LAT),.MUT(MUT==3?1:0)) vmm_Q(
            .clk(clk_vmm[k]),.rst_n(rst_n),.wq1(wq_sm[k*281+:281]),.wq2(q_wq[KQ*281+:281]),.wq_m(wq_m[k*281+:281]),
            .done_m(done_m[k]),.wq_done1(wq_done1[k]),.wq_done2(wq_done2[k]),.flt(vmm_flt[k]));
    end
endmodule
`default_nettype wire
