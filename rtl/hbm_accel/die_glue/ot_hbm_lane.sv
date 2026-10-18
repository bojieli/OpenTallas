`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HBM-LANDING (2026-10-18; CLOCK-AUDIT HBM row, LANDING-CONTRACT sections 2, 3, 7): forwarded-clock HALF-CYCLE lane
// stations for the HBM d4g die.  The single-branch half-cycle station and the landing are the Qwen cores unchanged
// (rtl/qwen_split/qfd_fwd_lane.sv: ot_qfd_lane_st FIRST 0, ot_qfd_land, ot_qfd_ckinv); this file adds the fork and the
// HBM hop 0:
//   ot_hbm_lane_stf #(W, N, FIRST): ONE register stage of the W data bits + the lane epoch bit, captured on cap
//     FIRST = 1: cap = ICG(ck = source root, en), NON-inverting (ot_hdc_cg): hop 0 is an ordinary register on the source
//                regional root, one cycle after the source launch (source -> hop 0 hold = the source region tree's), and
//                the half-cycle forward starts at its ck_o.  The Qwen hop 0 (ot_qfd_fwd0, inverting) captures on the
//                FALLING root edge: the ref_tile flow's link budget (report_clock_latency rise -> rise) finds no sinks on
//                the root port and refuses the kit (gate hbfd_lh0_136_* 10-18 'OT_LINK_BUDGET: no measured clock'), and
//                it saves only T/2 per lane.  Epoch in = en (the source's released reset gates the clock: L3).
//     FIRST = 0: cap = ckf (the previous station's ck_o; epoch in = ea)
//   and N branches k: ck_o[k] = ~cap through ONE kept inverter per branch (each branch drives one downstream station or
//   landing), b[k*W +: W] / eb[k] = the stage (the same flops; the physical flow buffers each branch at its face).
// Epoch: asynchronous clear by en / ea, release on cap (a reset repeater walking one station per forwarded edge), as
// ot_qfd_lane_st.  Data: no reset (flushed by the producer; the landing reads unwritten slots as 0 bubbles).
// Bench hooks: OT_QFD_LANE_MUT_FULL (every branch non-inverting, as the Qwen station), OT_HBM_LANE_MUT_HOP0INV (hop 0
// = the Qwen inverting gate), OT_HBM_LANE_MUT_FORKCK (branch 1 only non-inverting).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_lane_stf #(parameter integer W = 136, parameter integer N = 2, parameter integer FIRST = 0) (
    input  wire           ck,        // FIRST: source block root;  else: the lane's forwarded clock (ckf)
    input  wire           en,        // FIRST: source released reset (gate enable + epoch);  else: lane epoch in (ea)
    input  wire [W-1:0]   a,
    output wire [N*W-1:0] b,
    output wire [N-1:0]   eb,
    output wire [N-1:0]   ck_o
);
    wire cap;
    generate if (FIRST != 0) begin : g_hop0
`ifdef OT_HBM_LANE_MUT_HOP0INV
        ot_qfd_fwd0 u_fwd0 (.ck(ck), .en(en), .cko(cap));        // bench mutant: the Qwen inverting hop 0 (T/2 early)
`else
        ot_hdc_cg u_cg (.clk(ck), .en(en), .gclk(cap));
`endif
    end else begin : g_st
        assign cap = ck;
    end endgenerate
    reg [W-1:0] r;
    reg         e;
    always @(posedge cap) r <= a;
    always @(posedge cap or negedge en)
        if (!en) e <= 1'b0; else e <= 1'b1;
    genvar k;
    generate for (k = 0; k < N; k = k + 1) begin : g_br
        assign b[k * W +: W] = r;
        assign eb[k] = e;
`ifdef OT_QFD_LANE_MUT_FULL
        wire ckn;
        ot_qfd_ckinv u_ck0 (.a(cap), .y(ckn));
        ot_qfd_ckinv u_ck1 (.a(ckn), .y(ck_o[k]));
`else
`ifdef OT_HBM_LANE_MUT_FORKCK
        if (k == 1) begin : g_mut
            wire ckn;
            ot_qfd_ckinv u_ck0 (.a(cap), .y(ckn));
            ot_qfd_ckinv u_ck1 (.a(ckn), .y(ck_o[k]));
        end else begin : g_ok
            ot_qfd_ckinv u_ck0 (.a(cap), .y(ck_o[k]));
        end
`else
        ot_qfd_ckinv u_ck0 (.a(cap), .y(ck_o[k]));
`endif
`endif
    end endgenerate
endmodule
`default_nettype wire
