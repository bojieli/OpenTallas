`timescale 1ns/1ps
// KV-P3-LEAF 10-23: plan landing-check cell.  Replaces the landing-cell epoch faults the plan removes (qkd_landsh*.fault =
// the ot_qfd_land epoch-mismatch fault, rtl/qwen_split/qfd_fwd_lane.sv) with one check per partition over the epoch
// outputs eq of its N in-boundary flops (ot_dp_st .eq, tools/die_plan/gen_rtl.py CELLS).
//   After rst_n releases, a saturating counter counts AGE clk edges (AGE = the plan's counted release age = the longest
//   in-lane latency + sync stages; no wrap).  From then on (every edge after the AGE-th) the fault is sticky:
//   fault <= fault | ~&eq -- an in lane whose epoch has not arrived by its counted age (or drops later) is a calendar slip,
//   the plan analogue of the landing epoch fault.  Timing: eq must be high when sampled at edge AGE + 1 after release.
//   Async clear by rst_n.  Static: no ready / credit; the fault only reports.
//   EQ_PIPE / EQ_PIPE_V (KV-EFAULT-EQ 11-18, default 0 = the cell above, byte-identical behaviour and netlist): an eq input
//   pipe so the plan can place stations on the long eq -> efault paths.  Bit i gets D_i = EQ_PIPE + EQ_PIPE_V[4i +: 4] reset-0
//   flops; bit i is masked until counter >= AGE + D_i (its delayed epoch is then the epoch of edge AGE + 1 onward), so each
//   bit's check is exactly the D_i = 0 check delayed by D_i edges (fault itself rises D_i edges later for that bit; sticky,
//   never earlier, never a different bit set).  Uniform EQ_PIPE = P gives fault_P(k) = fault_0(k - P).  The AGE of a plan cell
//   stays the counted release age: the cell adds D_i internally, so the plan does not re-derive AGE.
module ot_dp_efault #(
    parameter integer N = 1,
    parameter integer AGE = 4,
    parameter integer EQ_PIPE = 0,
    parameter [4*N-1:0] EQ_PIPE_V = {4*N{1'b0}}
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [N-1:0] eq,
    output reg          fault
);
    function automatic integer depth(input integer i);
        depth = EQ_PIPE + {28'b0, EQ_PIPE_V[4*i +: 4]};
    endfunction
    function automatic integer dmax(input integer n);
        integer i;
        begin
            dmax = 0;
            for (i = 0; i < n; i = i + 1) if (depth(i) > dmax) dmax = depth(i);
        end
    endfunction
    localparam integer DM = dmax(N);
    localparam integer AGEM = AGE + DM;
    localparam integer CW = (AGEM < 1) ? 1 : $clog2(AGEM + 1);
    localparam [CW-1:0] AGEW = AGEM[CW-1:0];
    reg [CW-1:0] cnt;
    wire armed_all = (cnt == AGEW);
    wire [N-1:0] bad;     // per bit: armed (its own age + depth reached) and its (delayed) epoch low
    genvar g;
    generate
        for (g = 0; g < N; g = g + 1) begin : g_b
            localparam integer D = EQ_PIPE + {28'b0, EQ_PIPE_V[4*g +: 4]};
            localparam integer ARM = AGE + D;
            wire eqd;
            if (D == 0) begin : g_d0
                assign eqd = eq[g];
            end else begin : g_dp
                reg [D-1:0] pipe;
                if (D == 1) begin : g_p1
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) pipe <= 1'b0;
                        else        pipe <= eq[g];
                end else begin : g_pn
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) pipe <= {D{1'b0}};
                        else        pipe <= {pipe[D-2:0], eq[g]};
                end
                assign eqd = pipe[D-1];
            end
            if (DM == 0) begin : g_a0
                assign bad[g] = armed_all & ~eqd;
            end else begin : g_a1
                assign bad[g] = (cnt >= ARM[CW-1:0]) & ~eqd;
            end
        end
    endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            cnt <= {CW{1'b0}};
            fault <= 1'b0;
        end else begin
            if (!armed_all) cnt <= cnt + 1'b1;
            fault <= fault | (|bad);
        end
endmodule
