`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Cluster dispatcher: one descriptor, expanded in hardware across UNITS compute
// units and PASSES weight-SRAM passes each.
//
// WHY. tools/audit_control_path_throughput.py measures both sides of the control
// question against place-and-routed clocks and an RTL-measured instruction cost:
//
//     control plane  ot_a3_microsequencer at 265 MHz, 116.4 cycles per engine
//                    command (G1e, checked against a Python golden model)
//                    -> one descriptor every 439 ns = 567 datapath cycles
//     datapath       ot_compute_unit at 1,290 MHz, one K=256 pass = 270 cycles
//                    -> wants a descriptor every 209 ns
//
// So the control plane is 2.1x too slow for ONE compute unit, and 34x to 1,075x
// too slow for the arrays this project actually proposes. Wiring a sequencer to
// an array of units gets about 48 % utilisation on one unit and a few percent on
// an array, whatever the datapath's clock is.
//
// Neither half of the fix works alone:
//
//   FAN-OUT alone      removes the factor of UNITS but not the 2.1x per-unit
//                      deficit. The audit reports 47.6 % utilisation with
//                      perfect fan-out and one K-pass per descriptor.
//   COARSENING alone   a descriptor covering 3 passes keeps ONE unit busy, and
//                      leaves the array starved by the factor of UNITS.
//
// Together they do: one descriptor covers PASSES * K cycles of work on each of
// UNITS units, so the sequencer's rate is divided by UNITS and multiplied by
// PASSES. This is the GigaThread-engine-to-SM hierarchy in a GPU, the descriptor
// ring in a DPU, and the single instruction stream driving a whole MXU in a TPU:
// in none of them does the sequencer issue one command per arithmetic unit.
//
// WHAT THIS IS NOT. There is no work SPLITTING here: every unit runs the same K
// and scale, which is the output-stationary case where units differ only by which
// output tile they hold. A descriptor that had to be divided unequally across
// units would need a splitter, and this module would refuse it rather than
// silently give every unit the whole extent.
// ---------------------------------------------------------------------------
module ot_cluster_dispatcher #(
    parameter integer UNITS      = 16,
    parameter integer QUEUE_LOG2 = 3,
    parameter integer PASS_W     = 6      // up to 63 passes per descriptor
) (
    input  wire                   clk,
    input  wire                   rst_n,

    // ---- descriptor write port, from the control plane ----
    input  wire                   desc_valid,
    output wire                   desc_ready,
    input  wire [8:0]             desc_k,
    input  wire [7:0]             desc_scale,
    input  wire [PASS_W-1:0]      desc_passes,     // K-passes this descriptor covers

    // ---- broadcast to the cluster's compute units ----
    output reg                    cu_start,        // one pulse, every unit
    output reg  [8:0]             cu_cfg_k,
    output reg  [7:0]             cu_cfg_scale,
    input  wire [UNITS-1:0]       cu_busy,
    input  wire [UNITS-1:0]       cu_done,

    // ---- observation ----
    output reg  [31:0]            descriptors_retired,
    output reg  [31:0]            passes_launched,
    output reg  [63:0]            unit_busy_cycles,   // summed over all units
    output reg  [31:0]            cluster_cycles,
    output reg  [31:0]            starved_cycles      // cluster idle, queue empty
);
    localparam integer DEPTH = 1 << QUEUE_LOG2;

    // ---- descriptor queue -------------------------------------------------
    reg [8:0]        q_k      [0:DEPTH-1];
    reg [7:0]        q_scale  [0:DEPTH-1];
    reg [PASS_W-1:0] q_passes [0:DEPTH-1];
    reg [QUEUE_LOG2:0] wptr, rptr;

    wire q_empty = (wptr == rptr);
    wire q_full  = (wptr[QUEUE_LOG2-1:0] == rptr[QUEUE_LOG2-1:0]) &&
                   (wptr[QUEUE_LOG2] != rptr[QUEUE_LOG2]);
    assign desc_ready = !q_full;
    wire push = desc_valid && desc_ready;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) wptr <= {(QUEUE_LOG2+1){1'b0}};
        else if (push) begin
            q_k     [wptr[QUEUE_LOG2-1:0]] <= desc_k;
            q_scale [wptr[QUEUE_LOG2-1:0]] <= desc_scale;
            q_passes[wptr[QUEUE_LOG2-1:0]] <= (desc_passes == {PASS_W{1'b0}})
                                              ? {{(PASS_W-1){1'b0}}, 1'b1}
                                              : desc_passes;
            wptr <= wptr + 1'b1;
        end

    // ---- completion scoreboard --------------------------------------------
    //: A pass is complete when EVERY unit has reported done for it.  Tracking a
    //: mask rather than watching one unit is what makes this correct when units
    //: finish at different times -- which they do as soon as their memory paths
    //: are not identical, even though they are given identical work here.
    reg [UNITS-1:0]    done_mask;
    reg [PASS_W-1:0]   pass_left;
    reg                running;

    wire all_done = running && ((done_mask | cu_done) == {UNITS{1'b1}});
    wire cluster_idle = !running && !cu_start;
    wire launch = cluster_idle && !q_empty;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            rptr <= {(QUEUE_LOG2+1){1'b0}};
            cu_start <= 1'b0; cu_cfg_k <= 9'b0; cu_cfg_scale <= 8'b0;
            done_mask <= {UNITS{1'b0}}; pass_left <= {PASS_W{1'b0}};
            running <= 1'b0;
        end else begin
            cu_start <= 1'b0;

            if (launch) begin
                //: First pass of a new descriptor: latch its configuration and
                //: its pass count, and pop it.  The remaining passes reuse the
                //: latched configuration, so a multi-pass descriptor costs the
                //: queue one entry and the control plane one command.
                cu_cfg_k     <= q_k     [rptr[QUEUE_LOG2-1:0]];
                cu_cfg_scale <= q_scale [rptr[QUEUE_LOG2-1:0]];
                pass_left    <= q_passes[rptr[QUEUE_LOG2-1:0]] - 1'b1;
                cu_start     <= 1'b1;
                running      <= 1'b1;
                done_mask    <= {UNITS{1'b0}};
                rptr         <= rptr + 1'b1;
            end else if (all_done) begin
                done_mask <= {UNITS{1'b0}};
                if (pass_left != {PASS_W{1'b0}}) begin
                    //: Another pass of the SAME descriptor, launched on the cycle
                    //: after the last one retired.  No control-plane involvement,
                    //: which is the entire point.
                    pass_left <= pass_left - 1'b1;
                    cu_start  <= 1'b1;
                end else
                    running <= 1'b0;
            end else if (running)
                done_mask <= done_mask | cu_done;
        end

    // ---- observation ------------------------------------------------------
    integer u;
    reg [31:0] busy_now;
    always @* begin
        busy_now = 32'b0;
        for (u = 0; u < UNITS; u = u + 1)
            busy_now = busy_now + {31'b0, cu_busy[u]};
    end

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            descriptors_retired <= 32'b0; passes_launched <= 32'b0;
            unit_busy_cycles <= 64'b0; cluster_cycles <= 32'b0;
            starved_cycles <= 32'b0;
        end else begin
            cluster_cycles   <= cluster_cycles + 32'd1;
            unit_busy_cycles <= unit_busy_cycles + {32'b0, busy_now};
            if (cu_start) passes_launched <= passes_launched + 32'd1;
            if (all_done && (pass_left == {PASS_W{1'b0}}))
                descriptors_retired <= descriptors_retired + 32'd1;
            if (cluster_idle && q_empty) starved_cycles <= starved_cycles + 32'd1;
        end
endmodule
