`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Testbench-side adapter: the sequencer's two-phase engine port to a
// run-to-completion engine.
//
// rtl/abi3/ot_a3_device_top.sv issues an operation with a queue-acceptance
// handshake and learns of its completion later, by slot, on a separate port
// (docs/CHIP_ARCHITECTURE_DESIGN.md section 3.2 item 2).  The shipped-prefix
// engine bridge (rtl/abi3/ot_a3_engine_issue_bridge.sv) and the exact
// multicast witness still speak the older protocol, in which ``issue_ready``
// *is* the completion and the views of the operation are the pulses that
// preceded its issue.  This adapter sits between the two:
//
//   * it captures every resolved view the sequencer publishes, tagged with
//     the issue-record slot the view belongs to -- the testbench's stand-in
//     for the engine controller reading the operation's views out of the
//     issue record store;
//   * it accepts one issue at a time (depth 1: the next acceptance waits
//     for the previous completion), replays that operation's views to the
//     engine as the pulses the bridge expects, then presents the issue to
//     the engine and holds it until the engine's ready, which is the
//     completion;
//   * it reports that completion to the sequencer one cycle later, with the
//     engine's fault bit and class, and leaves one cycle between the
//     completion and the next acceptance so a fault is recorded before any
//     later operation could be accepted.
//
// The response the shipped-prefix checkers observe (``response_valid`` =
// the engine handshake, with the operation's family, subopcode, descriptor
// and pc) therefore keeps its meaning and its order exactly.  The adapter is
// verification scaffolding: it is not part of the design and is never
// synthesised.
// ---------------------------------------------------------------------------
module a3_engine_completion_adapter (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        clear,

    // -- sequencer side: two-phase port --------------------------------
    input  wire        issue_valid,
    output wire        issue_ready,
    input  wire [7:0]  issue_family,
    input  wire [7:0]  issue_sub,
    input  wire [31:0] issue_descriptor_id,
    input  wire [31:0] issue_index,
    input  wire [4:0]  issue_slot,

    input  wire        view_valid,
    input  wire [31:0] view_descriptor_id,
    input  wire [2:0]  view_slot,
    input  wire [31:0] view_extent,
    input  wire [7:0]  view_extent_axis,
    input  wire [63:0] view_element_offset,
    input  wire [7:0]  view_rank,
    input  wire [4:0]  view_irs_slot,

    output reg         complete_valid,
    output reg  [4:0]  complete_slot,
    output reg         complete_fault,
    output reg  [15:0] complete_trap_class,

    // -- engine side: run-to-completion port ---------------------------
    output reg         eng_issue_valid,
    input  wire        eng_issue_ready,
    input  wire        eng_issue_fault,
    input  wire [15:0] eng_issue_trap_class,
    output reg  [7:0]  eng_issue_family,
    output reg  [7:0]  eng_issue_sub,
    output reg  [31:0] eng_issue_descriptor_id,
    output reg  [31:0] eng_issue_index,
    output reg  [31:0] eng_issue_view_count,   // views replayed for this issue

    output reg         eng_view_valid,
    output reg  [31:0] eng_view_descriptor_id,
    output reg  [2:0]  eng_view_slot,
    output reg  [31:0] eng_view_extent,
    output reg  [7:0]  eng_view_extent_axis,
    output reg  [63:0] eng_view_element_offset,
    output reg  [7:0]  eng_view_rank
);
    localparam integer SLOTS = 32;

    // The captured views, by issue-record slot and operand slot.
    reg         cap_valid  [0:SLOTS*6-1];
    reg [31:0]  cap_desc   [0:SLOTS*6-1];
    reg [31:0]  cap_extent [0:SLOTS*6-1];
    reg [7:0]   cap_axis   [0:SLOTS*6-1];
    reg [63:0]  cap_offset [0:SLOTS*6-1];
    reg [7:0]   cap_rank   [0:SLOTS*6-1];

    localparam [1:0] S_IDLE   = 2'd0;
    localparam [1:0] S_REPLAY = 2'd1;
    localparam [1:0] S_RUN    = 2'd2;
    localparam [1:0] S_GAP    = 2'd3;

    reg [1:0] state;
    reg [4:0] held_slot;
    reg [2:0] replay_index;
    wire [7:0] replay_at = {held_slot, replay_index};

    assign issue_ready = (state == S_IDLE) && !clear;

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            held_slot <= 5'd0;
            replay_index <= 3'd0;
            complete_valid <= 1'b0;
            complete_slot <= 5'd0;
            complete_fault <= 1'b0;
            complete_trap_class <= 16'd0;
            eng_issue_valid <= 1'b0;
            eng_issue_family <= 8'd0;
            eng_issue_sub <= 8'd0;
            eng_issue_descriptor_id <= 32'hffff_ffff;
            eng_issue_index <= 32'hffff_ffff;
            eng_issue_view_count <= 32'd0;
            eng_view_valid <= 1'b0;
            eng_view_descriptor_id <= 32'hffff_ffff;
            eng_view_slot <= 3'd0;
            eng_view_extent <= 32'd0;
            eng_view_extent_axis <= 8'd0;
            eng_view_element_offset <= 64'd0;
            eng_view_rank <= 8'd0;
            for (i = 0; i < SLOTS*6; i = i + 1) begin
                cap_valid[i] <= 1'b0;
                cap_desc[i] <= 32'hffff_ffff;
                cap_extent[i] <= 32'd0;
                cap_axis[i] <= 8'd0;
                cap_offset[i] <= 64'd0;
                cap_rank[i] <= 8'd0;
            end
        end else begin
            complete_valid <= 1'b0;
            eng_view_valid <= 1'b0;
            if (clear) begin
                state <= S_IDLE;
                eng_issue_valid <= 1'b0;
                for (i = 0; i < SLOTS*6; i = i + 1)
                    cap_valid[i] <= 1'b0;
            end else begin
                // capture every published view under its slot
                if (view_valid && (view_slot < 3'd6)) begin
                    cap_valid[{view_irs_slot, view_slot}] <= 1'b1;
                    cap_desc[{view_irs_slot, view_slot}] <= view_descriptor_id;
                    cap_extent[{view_irs_slot, view_slot}] <= view_extent;
                    cap_axis[{view_irs_slot, view_slot}] <= view_extent_axis;
                    cap_offset[{view_irs_slot, view_slot}] <= view_element_offset;
                    cap_rank[{view_irs_slot, view_slot}] <= view_rank;
                end
                case (state)
                    S_IDLE: begin
                        if (issue_valid) begin
                            held_slot <= issue_slot;
                            eng_issue_family <= issue_family;
                            eng_issue_sub <= issue_sub;
                            eng_issue_descriptor_id <= issue_descriptor_id;
                            eng_issue_index <= issue_index;
                            eng_issue_view_count <= 32'd0;
                            replay_index <= 3'd0;
                            state <= S_REPLAY;
                        end
                    end
                    S_REPLAY: begin
                        // one operand slot per cycle, in order; a slot that
                        // holds no view is skipped in its cycle
                        if (cap_valid[replay_at]) begin
                            eng_view_valid <= 1'b1;
                            eng_view_descriptor_id <= cap_desc[replay_at];
                            eng_view_slot <= replay_index;
                            eng_view_extent <= cap_extent[replay_at];
                            eng_view_extent_axis <= cap_axis[replay_at];
                            eng_view_element_offset <= cap_offset[replay_at];
                            eng_view_rank <= cap_rank[replay_at];
                            eng_issue_view_count <= eng_issue_view_count + 32'd1;
                            cap_valid[replay_at] <= 1'b0;
                        end
                        if (replay_index == 3'd5) begin
                            eng_issue_valid <= 1'b1;
                            state <= S_RUN;
                        end else begin
                            replay_index <= replay_index + 3'd1;
                        end
                    end
                    S_RUN: begin
                        if (eng_issue_ready) begin
                            eng_issue_valid <= 1'b0;
                            complete_valid <= 1'b1;
                            complete_slot <= held_slot;
                            complete_fault <= eng_issue_fault;
                            complete_trap_class <= eng_issue_trap_class;
                            state <= S_GAP;
                        end
                    end
                    S_GAP: begin
                        // the completion is being reported this cycle; the
                        // next acceptance waits one more
                        state <= S_IDLE;
                    end
                    default: state <= S_IDLE;
                endcase
            end
        end
    end
endmodule
