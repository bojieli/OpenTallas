`timescale 1ns/1ps
// Registered, replicated local reset relay (synchronous-release reset tree).
//
// Design standard (coordinator 2026-10-10, drive-1010): a block's rst_n INPUT PORT drives only this relay.  The port net
// fans out to SYNC_STAGES synchronizer flops plus the asynchronous clear of the REGIONS*TREE_STAGES relay flops (assert
// stays asynchronous and immediate); release is synchronous and takes SYNC_STAGES + TREE_STAGES rising clk edges.
// Each region k then resets its own flops from rst_n[k], a flop output that placement can put next to that region, so no
// net from the port (or from one relay flop) spans the block.  On ~7 blocks the port -> thousands of reset flops net was
// the worst setup / hold path (hgi su_unit / su_ctl, idx-topk, qwen tile_e, ds qelem x1b).
//
// The region copies are logically identical, so synthesis would merge them: they are (* keep *) registers, which the
// ORFS flow's SYNTH_CANONICALIZE_TCL hook (physical/common_flow/ot_keep_regs.tcl, 0d3958d56) turns into kept flop cells.
//
// Consumers: release is delayed by RELEASE_CYCLES = SYNC_STAGES + TREE_STAGES cycles (exactness is transaction-level; any
// logic that counts cycles from reset release must count from rst_n[k], never from the port).
module ot_rst_relay #(
    parameter integer REGIONS     = 4,
    parameter integer SYNC_STAGES = 2,
    parameter integer TREE_STAGES = 1
) (
    input  wire               clk,
    input  wire               rst_n_in,
    output wire [REGIONS-1:0] rst_n
);
    localparam integer RELEASE_CYCLES = SYNC_STAGES + TREE_STAGES;

    (* async_reg = "true" *) reg [SYNC_STAGES-1:0] sync_q;
    always @(posedge clk or negedge rst_n_in) begin
        if (!rst_n_in)
            sync_q <= {SYNC_STAGES{1'b0}};
        else
            sync_q <= {sync_q[SYNC_STAGES-2:0], 1'b1};
    end

    // relay tree: stage t, region r.  Every stage is replicated per region so each copy drives only its own region.
    (* keep = "true", dont_touch = "true" *) reg [REGIONS-1:0] relay_q [0:TREE_STAGES-1];
    genvar t;
    generate
        for (t = 0; t < TREE_STAGES; t = t + 1) begin : g_stage
            always @(posedge clk or negedge rst_n_in) begin
                if (!rst_n_in)
                    relay_q[t] <= {REGIONS{1'b0}};
                else if (t == 0)
                    relay_q[t] <= {REGIONS{sync_q[SYNC_STAGES-1]}};
                else
                    relay_q[t] <= relay_q[(t == 0) ? 0 : t-1];
            end
        end
    endgenerate

    assign rst_n = relay_q[TREE_STAGES-1];

`ifndef SYNTHESIS
    initial begin
        if (SYNC_STAGES < 2) $error("ot_rst_relay: SYNC_STAGES must be >= 2 (release crosses from the async port)");
        if (TREE_STAGES < 1) $error("ot_rst_relay: TREE_STAGES must be >= 1");
        if (REGIONS < 1)     $error("ot_rst_relay: REGIONS must be >= 1");
    end
`endif
endmodule
