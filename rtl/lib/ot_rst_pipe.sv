`timescale 1ns/1ps
// Pipelined reset distribution for a block too large for one reset net per cycle (q13-kvh 2026-10-13).
//
// ot_rst_relay clears every regional relay flop ASYNCHRONOUSLY from the block's rst_n port, so that one net spans the
// block inside the port's IO budget.  On the 1,175 x 760 um attention-hub cluster this was the worst path
// (qkd_ahub_ref-q13: rst_n port -> u_rr.rst_n[7] recovery -611 ps, port -> hard-child rst_n pins -722 ps).
//
// Here the port drives ONLY a 2-flop synchroniser placed at the pin (asynchronous assert, synchronous release).  From it
// every region k has its own chain of STAGES plain D flops (no asynchronous clear): rst_n[k] = the last one, placed by
// its loads; the earlier ones sit on the way, so no stage spans more than ~1 / STAGES of the distance.  Each rst_n[k]
// is a flop output that resets only its region (or drives one hard child's rst_n pin).
//
// Assert reaches region k STAGES cycles after the port (the clock must run during reset); release takes 2 + STAGES
// rising edges.  Consumers must not count cycles from the port (same rule as ot_rst_relay).
module ot_rst_pipe #(
    parameter integer REGIONS = 4,
    parameter integer STAGES  = 2
) (
    input  wire               clk,
    input  wire               rst_n_in,
    output wire [REGIONS-1:0] rst_n
);
    (* keep = "true", dont_touch = "true" *) reg s0, s1;
    always @(posedge clk or negedge rst_n_in)
        if (!rst_n_in) begin s0 <= 1'b0; s1 <= 1'b0; end
        else begin s0 <= 1'b1; s1 <= s0; end
    genvar t;
    generate for (t = 0; t < STAGES; t = t + 1) begin : g_p
        (* keep = "true", dont_touch = "true" *) reg [REGIONS-1:0] q;
        if (t == 0) begin : g_first
            always @(posedge clk) q <= {REGIONS{s1}};
        end else begin : g_next
            always @(posedge clk) q <= g_p[t-1].q;
        end
    end endgenerate
    assign rst_n = g_p[STAGES-1].q;
`ifndef SYNTHESIS
    initial if (STAGES < 1 || REGIONS < 1) $error("ot_rst_pipe: STAGES and REGIONS must be >= 1");
`endif
endmodule
