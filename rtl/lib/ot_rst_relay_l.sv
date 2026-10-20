`timescale 1ns/1ps
// LANDED reset relay (L2H-IDXSCORE 2026-10-19; ROOT-RST reset_landing standard): same ports, same assert / release timing
// as ot_rst_relay, but the rst_n_in PORT net reaches ONLY the SYNC_STAGES synchroniser flops (the "2 registered stages at
// the face"; textbook_lint rst_land_max = 2).  The relay copies are cleared asynchronously by the LAST synchroniser stage
// instead of the port: assert still propagates asynchronously (port low -> sync_q clear -> relay clear, no clock needed),
// release still takes SYNC_STAGES + TREE_STAGES rising edges (relay_q samples sync_q[last] = 1 on edge SYNC_STAGES + 1,
// exactly as before), so every consumer sees the identical reset waveform.  ot_rst_relay drove SYNC_STAGES + REGIONS *
// TREE_STAGES clears from the port (idx_score qw 4, qe 3 sinks; reset_landing FAIL).
module ot_rst_relay_l #(
    parameter integer REGIONS     = 4,
    parameter integer SYNC_STAGES = 2,
    parameter integer TREE_STAGES = 1
) (
    input  wire               clk,
    input  wire               rst_n_in,
    output wire [REGIONS-1:0] rst_n
);
    (* async_reg = "true", keep = "true", dont_touch = "true" *) reg [SYNC_STAGES-1:0] sync_q;
    always @(posedge clk or negedge rst_n_in) begin
        if (!rst_n_in)
            sync_q <= {SYNC_STAGES{1'b0}};
        else
            sync_q <= {sync_q[SYNC_STAGES-2:0], 1'b1};
    end
    wire land_n = sync_q[SYNC_STAGES-1];
    (* keep = "true", dont_touch = "true" *) reg [REGIONS-1:0] relay_q [0:TREE_STAGES-1];
    genvar t;
    generate
        for (t = 0; t < TREE_STAGES; t = t + 1) begin : g_stage
            always @(posedge clk or negedge land_n) begin
                if (!land_n)
                    relay_q[t] <= {REGIONS{1'b0}};
                else if (t == 0)
                    relay_q[t] <= {REGIONS{land_n}};
                else
                    relay_q[t] <= relay_q[(t == 0) ? 0 : t-1];
            end
        end
    endgenerate
    assign rst_n = relay_q[TREE_STAGES-1];
`ifndef SYNTHESIS
    initial begin
        if (SYNC_STAGES < 2) $error("ot_rst_relay_l: SYNC_STAGES must be >= 2");
        if (TREE_STAGES < 1) $error("ot_rst_relay_l: TREE_STAGES must be >= 1");
        if (REGIONS < 1)     $error("ot_rst_relay_l: REGIONS must be >= 1");
    end
`endif
endmodule
