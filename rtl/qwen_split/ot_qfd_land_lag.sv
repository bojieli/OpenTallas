`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// Q-XPF (2026-10-18): SIMULATION-ONLY lane-timing model of a forwarded-lane landing (never synthesised, never bound by a
// die: tools/qwen_split/land_lag_sim.py swaps it in for ot_qfd_land inside a bench copy of a die slice).
//
// Why: ot_qfd_land reads ring slot (rc - K) mod D.  The die GEN sets K from the lane's TOTAL age E (K = (E + G - R0)
// mod 2D), and with a land plan E = fwd_e_est(n) + E_sta - 2, where E_sta is the landing residual the die STA measured
// (forwarded-clock insertion of the half-cycle stations: dv2f14bg dvw_hr_wi E_sta 7).  A zero-delay simulation writes
// the ring at the zero-delay arrival (E_sta 2), so a lane with E_sta > D - 1 reads a slot that was rewritten D edges
// later: the zero-delay netlist ALIASES the lane age by D (dv2f14br / dv2f14bi hr: E 18 measured as 14, XPF 20 vs 16)
// and the landing's own epoch check raises fault.  The hardware is the netlist WITH its lane timing: this model adds
// the lane's insertion as LAG whole lane-clock periods on the write side (data AND the lane epoch, i.e. exactly a later
// forwarded clock: every word keeps its write slot and epoch, it is written LAG periods later), so the bench measures
// the age the K straps were compiled for, and any landing whose read slot does not hold the expected epoch is reported.
//   LAG = max(0, E_sta - 2) per landing instance (fwd_lanes.json of the GEN), 0 = identical to ot_qfd_land.
// Every fault rise prints   OT_QFD_LAND_FAULT <instance> LAG <n>   (benches fail on ^OT_QFD_LAND_FAULT).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_land_lag #(
    parameter integer W     = 16,
    parameter integer D     = 4,
    parameter integer FIRST = 0,
    parameter integer LAG   = 0,
    parameter integer AW    = (D <= 2) ? 1 : $clog2(D)
) (
    input  wire         ckf,
    input  wire         ea,
    input  wire [W-1:0] i,
    input  wire         ck,
    input  wire         rs,
    input  wire [AW:0]  k,
    output wire [W-1:0] o,
    output wire         fault
);
`ifdef SYNTHESIS
    initial $fatal(1, "ot_qfd_land_lag is a simulation model (Q-XPF): never synthesise it");
`endif
    generate if (LAG == 0) begin : g_nolag
        ot_qfd_land #(.W(W), .D(D), .FIRST(FIRST)) u_land (.ckf(ckf), .ea(ea), .i(i), .ck(ck), .rs(rs), .k(k), .o(o),
                                                           .fault(fault));
    end else begin : g_lag
        wire wck;
        if (FIRST != 0) begin : g_hop0
            ot_qfd_fwd0 u_fwd0 (.ck(ckf), .en(ea), .cko(wck));
        end else begin : g_lane
            assign wck = ckf;
        end
        reg [W-1:0]   dq [0:LAG-1];
        reg [LAG-1:0] de;
        integer j, q;
        always @(posedge wck or negedge ea)
            if (!ea) de <= {LAG{1'b0}};
            else begin
                de[0] <= 1'b1;
                for (j = 1; j < LAG; j = j + 1) de[j] <= de[j-1];
            end
        always @(posedge wck) begin
            dq[0] <= i;
            for (q = 1; q < LAG; q = q + 1) dq[q] <= dq[q-1];
        end
        ot_qfd_land #(.W(W), .D(D), .FIRST(0)) u_land (.ckf(wck), .ea(de[LAG-1]), .i(dq[LAG-1]), .ck(ck), .rs(rs),
                                                       .k(k), .o(o), .fault(fault));
    end endgenerate
    always @(posedge fault) $display("OT_QFD_LAND_FAULT %m LAG %0d at %0t", LAG, $time);
endmodule
`default_nettype wire
