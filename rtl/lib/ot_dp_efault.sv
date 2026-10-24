`timescale 1ns/1ps
// KV-P3-LEAF 10-23: plan landing-check cell.  Replaces the landing-cell epoch faults the plan removes (qkd_landsh*.fault =
// the ot_qfd_land epoch-mismatch fault, rtl/qwen_split/qfd_fwd_lane.sv) with one check per partition over the epoch
// outputs eq of its N in-boundary flops (ot_dp_st .eq, tools/die_plan/gen_rtl.py CELLS).
//   After rst_n releases, a saturating counter counts AGE clk edges (AGE = the plan's counted release age = the longest
//   in-lane latency + sync stages; no wrap).  From then on (every edge after the AGE-th) the fault is sticky:
//   fault <= fault | ~&eq -- an in lane whose epoch has not arrived by its counted age (or drops later) is a calendar slip,
//   the plan analogue of the landing epoch fault.  Timing: eq must be high when sampled at edge AGE + 1 after release.
//   Async clear by rst_n.  Static: no ready / credit; the fault only reports.
module ot_dp_efault #(
    parameter integer N = 1,
    parameter integer AGE = 4
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [N-1:0] eq,
    output reg          fault
);
    localparam integer CW = (AGE < 1) ? 1 : $clog2(AGE + 1);
    localparam [CW-1:0] AGEW = AGE[CW-1:0];
    reg [CW-1:0] cnt;
    wire armed = (cnt == AGEW);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            cnt <= {CW{1'b0}};
            fault <= 1'b0;
        end else begin
            if (!armed) cnt <= cnt + 1'b1;
            fault <= fault | (armed & ~&eq);
        end
endmodule
