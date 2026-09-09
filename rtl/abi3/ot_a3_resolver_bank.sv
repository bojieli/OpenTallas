`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 resolver bank: six view-resolver lanes, one per operand slot
// (docs/CHIP_ARCHITECTURE_DESIGN.md section 3.5; CP-RES-A/B/C of section 11.1
// as one bank).
//
// Given an OPERATOR payload the bank fetches the TENSOR_VIEW record of every
// operand slot the operator names (input_view_0..3 at payload byte 24,
// output_view_0..1 at byte 40, NO_ID skipped) and starts that slot's lane as
// soon as the record arrives; the lanes then resolve concurrently and the
// bank is done when the last started lane is.  The descriptor port is the
// sequencer's one 256-byte port (section 11.2: the vehicle serialises the
// store to one port), owned by the bank between start and done, so the six
// fetches are serial (one read, one registered cycle each) and only the
// resolution is parallel -- the "fetch 2 || terms 1 each" of section 3.3's R
// row is not claimed here.
//
// Faults keep the serial order of the one-lane front end they replace: a
// descriptor that is not a well-formed TENSOR_VIEW (trap 3) or a lane that
// fails closed (its own class, 7) is recorded per slot, and the bank reports
// the fault of the lowest faulting slot, which is exactly the first fault a
// slot-by-slot walk would have raised.  No view is published for a faulting
// instruction: the sequencer publishes the six results together, after the
// bank is done and the dependence check has passed (section 3.3's I stage).
//
// Each lane holds its own copy of the 128-byte view payload for the duration
// of the resolution, because the one-port store cannot serve six readers;
// that is 6 x 1,024 bits of flops and is the cost of six lanes on one port.
//
// FAST_SCAN (measured, not asserted).  The slot walk this block shipped with
// visited all six slots one cycle each and then took a seventh cycle to notice
// it was done, whether or not a slot named anything: a per-state census of the
// Qwen ROM deployment (Icarus, case 0, 691 OPERATOR instructions, 2,143 views)
// charged 4,837 cycles to the scan state -- exactly 7.00 per operator -- of
// which 2,003 were spent stepping over the empty slots of instructions that
// name 3.10 operands on average, and 691 were the terminal cycle.  With
// FAST_SCAN the six slot IDs are compared with NO_ID in parallel at ``start``,
// a priority encoder names the lowest slot still owed a descriptor, and the
// request for it is issued from ``start`` itself and thereafter from the cycle
// that consumes the previous record: the scan state is gone and a descriptor
// read costs the two cycles the port takes and nothing else.
//
// Exactly one read is in flight at any time, which is the descriptor port's
// standing contract (ot_a3_g2_descriptor_store: "each master has at most one
// read in flight by construction").  Issuing the next request in the cycle the
// previous ``desc_valid`` is observed does not break it: that store clears its
// pending register when a read starts, so the pulse is captured cleanly and
// nothing is dropped.  This block still never has two reads outstanding.
//
// The order of the walk is unchanged -- the priority encoder picks the lowest
// slot, which is the order the counter visited them in -- so the fault that a
// faulting instruction reports and the descriptor IDs recorded per slot are
// what they always were.
//
// The package is referenced by scope, never wildcard-imported [OI-43].
// ---------------------------------------------------------------------------
module ot_a3_resolver_bank #(
    // 1: the scan state is elided and empty slots are skipped by a priority
    // encoder.  0: the six-slot serial counter walk this block shipped with,
    // which is the default, so a build that does not name the parameter is the
    // block as it shipped.  Both builds are driven from one stimulus by
    // rtl/test/tb_a3_resolver_bank_equiv.sv, and the 0 build is driven against
    // a verbatim copy of the shipped source by
    // rtl/test/tb_a3_resolver_bank_inert.sv.
    parameter integer FAST_SCAN = 0,
    // Forwarded to every lane; see ot_a3_view_resolver.  Defaults off for the
    // same reason: two optimisations, two knobs, neither on by default.
    //
    // This is the parameter that decides the lanes' walk.  It is passed down
    // explicitly below, so it OVERRIDES ot_a3_view_resolver's own default;
    // turning the lane walk off means setting it here (or from the top through
    // ot_a3_microsequencer), never by editing the lane's default.
    parameter integer FAST_WALK = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            clear,

    input  wire            start,
    input  wire [511:0]    op_payload,        // OPERATOR payload, held by the caller

    // descriptor store (owned between start and done)
    output reg             desc_req,
    output reg  [31:0]     desc_id,
    input  wire            desc_valid,
    input  wire            desc_fault,
    input  wire [1535:0]   desc_data,

    // loop stack query ports (six, flat; combinational)
    output wire [6*32-1:0] loop_query_id,
    input  wire [5:0]      loop_query_active,
    input  wire [6*32-1:0] loop_query_value,
    input  wire [5:0]      loop_query_symbol_bounded,
    input  wire [6*32-1:0] loop_query_divisor,
    input  wire [6*32-1:0] loop_query_bound_value,

    // symbol file (flat)
    input  wire [ot_a3_pkg::A3_SYMBOL_COUNT*64-1:0] sym_values,
    input  wire [ot_a3_pkg::A3_SYMBOL_COUNT-1:0]    sym_bound,

    // shared divider, requesters 1..6 (flat)
    output wire [5:0]      div_req,
    output wire [6*64-1:0] div_num,
    output wire [6*32-1:0] div_den,
    input  wire [5:0]      div_done,
    input  wire [63:0]     div_quot,
    input  wire [63:0]     div_rem,

    output reg             busy,
    output reg             done,
    output reg             fault,
    output reg  [15:0]     trap_class,

    // per-slot results, valid with done and held until the next start
    output reg  [5:0]      slot_valid,
    output reg  [6*32-1:0] slot_descriptor_id,
    output wire [6*32-1:0] slot_extent,
    output wire [6*8-1:0]  slot_axis,
    output wire [6*64-1:0] slot_offset,
    output wire [6*8-1:0]  slot_rank,
    output wire [6*16-1:0] slot_object,
    output wire [6*40-1:0] slot_lo,
    output wire [6*40-1:0] slot_hi,
    output wire [5:0]      slot_write,
    output wire [6*32-1:0] slot_scale_object,
    output wire [5:0]      slot_scale_valid
);
    // -- descriptor header view -----------------------------------------
    wire [31:0]   desc_magic          = desc_data[31:0];
    wire [15:0]   desc_type           = desc_data[47:32];
    wire [7:0]    desc_type_major     = desc_data[55:48];
    wire [31:0]   desc_primary_object = desc_data[159:128];
    wire [31:0]   desc_permissions    = desc_data[287:256];
    wire [31:0]   desc_payload_offset = desc_data[351:320];
    wire [1023:0] desc_payload_wide   = desc_data[1535:512];
    wire          desc_header_ok = !desc_fault &&
                                   (desc_magic == ot_a3_pkg::A3_DESCRIPTOR_MAGIC) &&
                                   (desc_type_major == ot_a3_pkg::A3_TYPE_MAJOR) &&
                                   (desc_payload_offset == 32'd64) &&
                                   (desc_type == ot_a3_pkg::A3_DESC_TENSOR_VIEW);

    // Any non-zero parameter selects the fast build, so an instantiation that
    // passes 2 does not silently get the slow one.
    localparam FAST_SCAN_ON = (FAST_SCAN != 0);

    // -- slot walk -----------------------------------------------------------
    localparam [1:0] S_IDLE  = 2'd0;
    localparam [1:0] S_SCAN  = 2'd1;
    localparam [1:0] S_WAIT  = 2'd2;
    localparam [1:0] S_RUN   = 2'd3;

    reg [1:0]   state;
    reg [2:0]   slot;
    reg [5:0]   lane_started;
    reg [5:0]   lane_finished;
    reg [5:0]   lane_faulted;
    reg [15:0]  lane_trap [0:5];
    reg [5:0]   desc_faulted;

    // The operand view IDs of the OPERATOR payload (input_view_0..3 at byte
    // 24, output_view_0..1 at byte 40); nothing above byte 47 is read.  The
    // sequencer holds op_payload stable from start to done, so it is read
    // in place rather than copied.
    function [31:0] slot_id_of;
        input [2:0] which;
        begin
            case (which)
                3'd0:    slot_id_of = op_payload[223:192];
                3'd1:    slot_id_of = op_payload[255:224];
                3'd2:    slot_id_of = op_payload[287:256];
                3'd3:    slot_id_of = op_payload[319:288];
                3'd4:    slot_id_of = op_payload[351:320];
                3'd5:    slot_id_of = op_payload[383:352];
                default: slot_id_of = ot_a3_pkg::A3_NO_ID;
            endcase
        end
    endfunction

    // Explicit sensitivity, not @*: the payload is read inside the function
    // rather than named in the statement, and a continuous assignment would
    // not be re-evaluated when it changes.
    reg [31:0] slot_id;
    always @(slot or op_payload) slot_id = slot_id_of(slot);

    // FAST_SCAN.  The six comparisons the counter walk made one per cycle,
    // made at once: bit k is set exactly when slot k names a descriptor.  The
    // comparison is the same one, against the same field, in the same order.
    wire [5:0] slot_present = {
        (op_payload[383:352] != ot_a3_pkg::A3_NO_ID),
        (op_payload[351:320] != ot_a3_pkg::A3_NO_ID),
        (op_payload[319:288] != ot_a3_pkg::A3_NO_ID),
        (op_payload[287:256] != ot_a3_pkg::A3_NO_ID),
        (op_payload[255:224] != ot_a3_pkg::A3_NO_ID),
        (op_payload[223:192] != ot_a3_pkg::A3_NO_ID)
    };

    // Slots that still owe a descriptor read.  ``pick`` is the lowest of them,
    // which is the slot the counter walk would have reached next, so the read
    // order -- and therefore the fault order and the port's request order --
    // is unchanged.
    reg  [5:0] pending;
    wire [5:0] pick_mask = FAST_SCAN_ON ? pending : 6'd0;
    reg  [2:0] pick;
    always @* begin
        casez (pick_mask)
            6'b?????1: pick = 3'd0;
            6'b????10: pick = 3'd1;
            6'b???100: pick = 3'd2;
            6'b??1000: pick = 3'd3;
            6'b?10000: pick = 3'd4;
            6'b100000: pick = 3'd5;
            default:   pick = 3'd0;
        endcase
    end
    // The same encoder applied to the mask ``start`` computes, for the first
    // read of a transaction; the register is not yet loaded that cycle.
    reg [2:0] pick_first;
    always @* begin
        casez (slot_present)
            6'b?????1: pick_first = 3'd0;
            6'b????10: pick_first = 3'd1;
            6'b???100: pick_first = 3'd2;
            6'b??1000: pick_first = 3'd3;
            6'b?10000: pick_first = 3'd4;
            6'b100000: pick_first = 3'd5;
            default:   pick_first = 3'd0;
        endcase
    end

    // -- lanes -----------------------------------------------------------------
    reg  [5:0]    lane_start;
    reg  [1023:0] lane_payload [0:5];
    reg  [31:0]   lane_object  [0:5];
    reg  [31:0]   lane_perm    [0:5];
    wire [5:0]    lane_done;
    wire [5:0]    lane_fault;
    wire [15:0]   lane_trap_class [0:5];

    genvar g;
    generate
        for (g = 0; g < 6; g = g + 1) begin : g_lane
            wire [3:0]  lane_sym_index;
            wire [63:0] lane_sym_value = sym_values[lane_sym_index*64 +: 64];
            wire        lane_sym_bound = sym_bound[lane_sym_index];
            ot_a3_view_resolver #(.FAST_WALK(FAST_WALK)) lane (
                .clk(clk),
                .rst_n(rst_n),
                .clear(clear),
                .start(lane_start[g]),
                .payload(lane_payload[g]),
                .object_id(lane_object[g]),
                .permissions(lane_perm[g]),
                .busy(),
                .done(lane_done[g]),
                .fault(lane_fault[g]),
                .trap_class(lane_trap_class[g]),
                .out_element_offset(slot_offset[g*64 +: 64]),
                .out_extent(slot_extent[g*32 +: 32]),
                .out_extent_axis(slot_axis[g*8 +: 8]),
                .out_rank(slot_rank[g*8 +: 8]),
                .out_dtype(),
                .out_term_count(),
                .out_object(slot_object[g*16 +: 16]),
                .out_write(slot_write[g]),
                .out_lo(slot_lo[g*40 +: 40]),
                .out_hi(slot_hi[g*40 +: 40]),
                .out_scale_object(slot_scale_object[g*32 +: 32]),
                .out_scale_valid(slot_scale_valid[g]),
                .loop_query_id(loop_query_id[g*32 +: 32]),
                .loop_query_active(loop_query_active[g]),
                .loop_query_value(loop_query_value[g*32 +: 32]),
                .loop_query_symbol_bounded(loop_query_symbol_bounded[g]),
                .loop_query_divisor(loop_query_divisor[g*32 +: 32]),
                .loop_query_bound_value(loop_query_bound_value[g*32 +: 32]),
                .sym_index(lane_sym_index),
                .sym_value(lane_sym_value),
                .sym_bound(lane_sym_bound),
                .div_req(div_req[g]),
                .div_num(div_num[g*64 +: 64]),
                .div_den(div_den[g*32 +: 32]),
                .div_done(div_done[g]),
                .div_quot(div_quot),
                .div_rem(div_rem)
            );
        end
    endgenerate

    // lowest faulting slot, descriptor or lane
    reg        any_fault;
    reg [15:0] first_trap;
    integer k;
    always @* begin
        any_fault = 1'b0;
        first_trap = ot_a3_pkg::A3_TRAP_NONE;
        for (k = 5; k >= 0; k = k - 1) begin
            if (desc_faulted[k]) begin
                any_fault = 1'b1;
                first_trap = ot_a3_pkg::A3_TRAP_DESCRIPTOR;
            end else if (lane_faulted[k]) begin
                any_fault = 1'b1;
                first_trap = lane_trap[k];
            end
        end
    end

    reg [31:0] pick_id;
    always @(pick or op_payload)       pick_id       = slot_id_of(pick);
    reg [31:0] pick_first_id;
    always @(pick_first or op_payload) pick_first_id = slot_id_of(pick_first);

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            slot <= 3'd0;
            lane_started <= 6'd0;
            lane_finished <= 6'd0;
            lane_faulted <= 6'd0;
            desc_faulted <= 6'd0;
            lane_start <= 6'd0;
            for (i = 0; i < 6; i = i + 1) begin
                lane_payload[i] <= 1024'd0;
                lane_object[i] <= 32'd0;
                lane_perm[i] <= 32'd0;
                lane_trap[i] <= ot_a3_pkg::A3_TRAP_NONE;
            end
            desc_req <= 1'b0;
            desc_id <= ot_a3_pkg::A3_NO_ID;
            pending <= 6'd0;
            busy <= 1'b0;
            done <= 1'b0;
            fault <= 1'b0;
            trap_class <= ot_a3_pkg::A3_TRAP_NONE;
            slot_valid <= 6'd0;
            slot_descriptor_id <= {6{ot_a3_pkg::A3_NO_ID}};
        end else begin
            done <= 1'b0;
            desc_req <= 1'b0;
            lane_start <= 6'd0;
            // lane completions, in any order
            for (i = 0; i < 6; i = i + 1) begin
                if (lane_done[i]) begin
                    lane_finished[i] <= 1'b1;
                    lane_faulted[i] <= lane_fault[i];
                    lane_trap[i] <= lane_trap_class[i];
                end
            end
            if (clear) begin
                state <= S_IDLE;
                busy <= 1'b0;
                lane_started <= 6'd0;
                lane_finished <= 6'd0;
                lane_faulted <= 6'd0;
                desc_faulted <= 6'd0;
                pending <= 6'd0;
            end else begin
                case (state)
                    S_IDLE: begin
                        if (start) begin
                            busy <= 1'b1;
                            fault <= 1'b0;
                            trap_class <= ot_a3_pkg::A3_TRAP_NONE;
                            slot <= 3'd0;
                            lane_started <= 6'd0;
                            lane_finished <= 6'd0;
                            lane_faulted <= 6'd0;
                            desc_faulted <= 6'd0;
                            slot_valid <= 6'd0;
                            if (FAST_SCAN_ON) begin
                                // The first read leaves with ``start``: the
                                // caller holds op_payload from here to done,
                                // so the six IDs are settled this cycle.
                                if (slot_present != 6'd0) begin
                                    desc_req <= 1'b1;
                                    desc_id <= pick_first_id;
                                    slot <= pick_first;
                                    pending <= slot_present &
                                               ~(6'd1 << pick_first);
                                    state <= S_WAIT;
                                end else begin
                                    pending <= 6'd0;
                                    state <= S_RUN;
                                end
                            end else begin
                                state <= S_SCAN;
                            end
                        end
                    end
                    S_SCAN: begin
                        if (slot >= 3'd6) begin
                            state <= S_RUN;
                        end else if (slot_id == ot_a3_pkg::A3_NO_ID) begin
                            slot <= slot + 3'd1;
                        end else begin
                            desc_req <= 1'b1;
                            desc_id <= slot_id;
                            state <= S_WAIT;
                        end
                    end
                    S_WAIT: begin
                        if (desc_valid) begin
                            slot_descriptor_id[slot*32 +: 32] <= desc_id;
                            if (!desc_header_ok) begin
                                desc_faulted[slot] <= 1'b1;
                            end else begin
                                lane_payload[slot] <= desc_payload_wide;
                                lane_object[slot] <= desc_primary_object;
                                lane_perm[slot] <= desc_permissions;
                                lane_start[slot] <= 1'b1;
                                lane_started[slot] <= 1'b1;
                                slot_valid[slot] <= 1'b1;
                            end
                            if (FAST_SCAN_ON) begin
                                // The next request leaves in the cycle that
                                // consumed this record.  One read is in
                                // flight at a time either way; what is gone
                                // is the dead cycle between them.
                                if (pending != 6'd0) begin
                                    desc_req <= 1'b1;
                                    desc_id <= pick_id;
                                    slot <= pick;
                                    pending <= pending & ~(6'd1 << pick);
                                    state <= S_WAIT;
                                end else begin
                                    state <= S_RUN;
                                end
                            end else begin
                                slot <= slot + 3'd1;
                                state <= S_SCAN;
                            end
                        end
                    end
                    S_RUN: begin
                        if ((lane_started & ~lane_finished) == 6'd0) begin
                            busy <= 1'b0;
                            done <= 1'b1;
                            fault <= any_fault;
                            trap_class <= first_trap;
                            state <= S_IDLE;
                        end
                    end
                    default: state <= S_IDLE;
                endcase
            end
        end
    end
endmodule
