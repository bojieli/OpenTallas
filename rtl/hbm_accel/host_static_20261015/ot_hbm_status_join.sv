`timescale 1ns/1ps
`default_nettype none
// Die status aggregation leaf for the static host ingress (H-NETLIST cp2, 2026-10-15).
// Replaces "an AND/OR in the composition" (glue has no die home) with a real pin-registered tile.
//  * Participation: target i participates in the next launch once the ingress broadcast carries a
//    descriptor for TGTS[i] (desc_v with cfg_target==TGTS[i]); participation clears at launch_v.
//    TGTS[i]==0 marks an always-participating input (a child join in a 2-level tree: its t_ready is
//    already the AND over its own participants).
//  * block_ready = (at least one participant) AND over participants of t_ready, held low for GUARD edges after any cfg/desc/launch
//    frame so a target's stale readiness cannot race its own re-validation.
//  * program_active = OR t_active; program_fault = OR t_fault (targets: refuse config / launch);
//    die_fault = program_fault | OR h_fault (host link, landing, packet, PHY faults) -> host status packet.
//  * irq = programme complete: set when program_active falls after an accepted launch, cleared at launch.
// Every input is a pin flop and every output a flop Q: block_ready/active/fault reach the ingress 2 edges
// after the target status; the ingress pin adds its own edge. Configuration/launch latency only.
module ot_hbm_status_join #(
    parameter integer NT=8,                 // targets (ready/active pairs)
    parameter integer NF=8,                 // target fault inputs
    parameter integer NH=4,                 // host/link fault inputs
    parameter [NT*8-1:0] TGTS={NT{8'd0}},   // F20 target id per input (0 = always participating)
    parameter integer GUARD=8,
    parameter integer MUT=0                 // bench: 1 ignores participation, 2 no guard
)(
    input  wire clk, rst_n,
    input  wire cfg_v, desc_v, launch_v,
    input  wire [7:0] cfg_target,
    input  wire [NT-1:0] t_ready, t_active,
    input  wire [NF-1:0] t_fault,
    input  wire [NH-1:0] h_fault,
    output reg  block_ready, program_active, program_fault, die_fault, irq
);
    reg cv, dv, lv;
    reg [7:0] ct;
    reg [NT-1:0] rdy_q, act_q;
    reg [NF-1:0] tf_q;
    reg [NH-1:0] hf_q;
    always @(posedge clk) ct <= cfg_target;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cv <= 0; dv <= 0; lv <= 0; rdy_q <= 0; act_q <= 0; tf_q <= 0; hf_q <= 0; end
        else begin cv <= cfg_v; dv <= desc_v; lv <= launch_v; rdy_q <= t_ready; act_q <= t_active; tf_q <= t_fault; hf_q <= h_fault; end
    reg [NT-1:0] part;
    reg [7:0] guard;
    reg launched, was_active;
    reg all_ok, any_part;
    integer i;
    always @* begin
        all_ok = 1; any_part = 0;
        for (i = 0; i < NT; i = i + 1) if (part[i] || TGTS[i*8 +: 8] == 8'd0) any_part = 1;
        for (i = 0; i < NT; i = i + 1)
            if ((part[i] || TGTS[i*8 +: 8] == 8'd0 || MUT == 1) && !rdy_q[i]) all_ok = 0;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            part <= 0; guard <= GUARD[7:0]; launched <= 0; was_active <= 0;
            block_ready <= 0; program_active <= 0; program_fault <= 0; die_fault <= 0; irq <= 0;
        end else begin
            if (guard != 0) guard <= guard - 1'b1;
            if ((cv || dv || lv) && MUT != 2) guard <= GUARD[7:0];
            if (dv) for (i = 0; i < NT; i = i + 1) if (TGTS[i*8 +: 8] == ct && ct != 8'd0) part[i] <= 1;
            if (lv) begin part <= 0; launched <= 1; irq <= 0; end
            was_active <= |act_q;
            if (launched && was_active && !(|act_q)) begin launched <= 0; irq <= 1; end
            block_ready <= all_ok && any_part && guard == 0 && !(cv || dv || lv);
            program_active <= |act_q;
            program_fault <= |tf_q;
            die_fault <= (|tf_q) || (|hf_q);
        end
    end
endmodule
`default_nettype wire
