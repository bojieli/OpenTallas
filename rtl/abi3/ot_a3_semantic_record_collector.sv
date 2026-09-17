`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The 128-word semantic record, assembled by watching the descriptor stream.
//
// ot_a3_hc_pre_t1_descriptor_rne and ot_a3_vector_mhc_pre_tile_scheduler consume
// the record as one bundle, and nothing in the device produced it.  The bridge
// holds the operator, the numeric payload and the resolved views but never sees
// the SCHEDULE descriptor, which the microsequencer decodes in its own state, and
// the views arrive later still from the resolver bank.  So no single module had
// all 128 words and the engines could not be connected.
//
// This collects them by TAPPING, not by fetching.  ot_a3_microsequencer already
// exposes desc_id, desc_valid and 192 raw bytes of desc_data as module ports, so a
// collector beside it sees every descriptor the sequencer walks past and adds no
// traffic, no port on the descriptor store and no change to the sequencer.
//
// IT MATCHES BY IDENTITY, NOT BY ARRIVAL ORDER -- AFTER THE OPERATOR.  The
// operator descriptor names every other piece it needs (counter class, numeric
// profile, schedule, four input views, two output views), so once it is latched the
// remaining ten are recognised by their ids in whatever order they arrive.  An
// order-based collector would be a second statement of the sequencer's walk and
// would break the first time that walk changed.
//
// The operator must arrive FIRST, and that is a requirement rather than an
// assumption: nothing can recognise a view by id before reading the descriptor that
// references it.  The microsequencer fetches it first for the same reason -- it
// learns the other ids there too -- so this asks for nothing the sequencer does not
// already do.  A descriptor arriving before the operator is NOT buffered and not
// silently dropped either: ``collected_mask`` simply does not set its bit, so the
// record never completes and the consumer sees no ``record_valid``.  The bench
// drives exactly that case by shuffling the other ten.
//
// The operator is admitted by WHAT IT IS: engine family, sub, and the aux word
// that distinguishes HYPER_CONNECT_PRE from POST.  A descriptor id is a position
// in a table that every earlier removal shifts, and pinning one is what made this
// engine's vectors unbuildable after an unrelated renumbering.
//
// Every field read comes from ot_a3_semantic_record_slices.svh, generated from
// runtime/abi3/descriptors.py's own offset tables by
// tools/generate_a3_semantic_record_collector.py.  The same offsets are read by
// runtime/abi3/semantic_record.py, and tests/abi3/test_semantic_record.py proves
// that reading equal to the decoded assembly on both shipped stores -- so the RTL
// and the Python golden cannot disagree about where a field lives.
// ---------------------------------------------------------------------------
module ot_a3_semantic_record_collector #(
    parameter integer CONFIG_WORDS = 128,
    //: What the collected operator must be.  Defaults are VECTOR.MHC in its PRE
    //: form; POST carries a different aux word and is a different operation.
    parameter [31:0] MATCH_FAMILY = 32'h0000_0030,
    parameter [31:0] MATCH_SUB    = 32'h0000_0009,
    parameter [31:0] MATCH_AUX1   = 32'd20
) (
    input  wire          clk,
    input  wire          rst_n,

    //: One pulse per instruction the collector should try to assemble.  Clears
    //: whatever was half-collected: a record is per-dispatch and a leftover block
    //: from a previous one is the failure this exists to avoid.
    input  wire          begin_valid,
    input  wire [31:0]   cfg_profile,
    input  wire [31:0]   cfg_active_tokens,
    input  wire [31:0]   instruction_pc,
    input  wire [31:0]   instruction_flags,
    input  wire [31:0]   instruction_operator_id,
    input  wire [31:0]   instruction_wait_set_id,
    input  wire [31:0]   instruction_signal_event_id,
    input  wire [31:0]   instruction_control_id,
    input  wire [31:0]   instruction_source_operation_id,

    //: The microsequencer's own descriptor port, observed.
    input  wire          desc_valid,
    input  wire [31:0]   desc_id,
    input  wire [1535:0] desc_data,

    output reg           record_valid,
    output reg  [CONFIG_WORDS*32-1:0] record_words,
    output reg  [7:0]    error_code,
    output reg  [10:0]   collected_mask
);
`include "ot_a3_semantic_record_slices.svh"

    localparam [7:0] ERR_NONE     = 8'd0;
    localparam [7:0] ERR_OPERATOR = 8'd17;

    //: One bit per role, in the order the record lays them out.
    localparam integer R_OPERATOR = 0;
    localparam integer R_COUNTER  = 1;
    localparam integer R_NUMERIC  = 2;
    localparam integer R_SCHEDULE = 3;
    localparam integer R_WAIT     = 4;
    localparam integer R_IN0      = 5;
    localparam integer R_IN1      = 6;
    localparam integer R_IN2      = 7;
    localparam integer R_IN3      = 8;
    localparam integer R_OUT0     = 9;
    localparam integer R_OUT1     = 10;

    reg [31:0] id_counter, id_numeric, id_schedule;
    reg [31:0] id_in0, id_in1, id_in2, id_in3, id_out0, id_out1;

    wire [18*32-1:0] operator_words = a3_record_operator_words(desc_data);
    wire [5*32-1:0]  counter_words  = a3_record_counter_words(desc_data);
    wire [11*32-1:0] numeric_words  = a3_record_numeric_words(desc_data);
    wire [8*32-1:0]  digest_words   = a3_record_digest_words(desc_data);
    wire [12*32-1:0] schedule_words = a3_record_schedule_words(desc_data);
    wire [10*32-1:0] view_words     = a3_record_view_words(desc_data);

    //: The operator's own identity, read before anything is latched from it.
    wire [31:0] cand_family = operator_words[0*32 +: 32];
    wire [31:0] cand_sub    = operator_words[1*32 +: 32];
    wire [31:0] cand_aux1   = operator_words[15*32 +: 32];
    wire operator_matches =
        (cand_family == MATCH_FAMILY) &&
        (cand_sub == MATCH_SUB) &&
        (cand_aux1 == MATCH_AUX1);

    wire have_operator = collected_mask[R_OPERATOR];
    wire is_operator   = desc_valid && !have_operator &&
                         (desc_id == instruction_operator_id);
    wire is_wait       = desc_valid && (desc_id == instruction_wait_set_id);
    wire is_counter    = desc_valid && have_operator && (desc_id == id_counter);
    wire is_numeric    = desc_valid && have_operator && (desc_id == id_numeric);
    wire is_schedule   = desc_valid && have_operator && (desc_id == id_schedule);
    wire is_in0        = desc_valid && have_operator && (desc_id == id_in0);
    wire is_in1        = desc_valid && have_operator && (desc_id == id_in1);
    wire is_in2        = desc_valid && have_operator && (desc_id == id_in2);
    wire is_in3        = desc_valid && have_operator && (desc_id == id_in3);
    wire is_out0       = desc_valid && have_operator && (desc_id == id_out0);
    wire is_out1       = desc_valid && have_operator && (desc_id == id_out1);

    localparam [10:0] ALL_ROLES = 11'b111_1111_1111;

    integer w;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            record_valid <= 1'b0;
            error_code <= ERR_NONE;
            collected_mask <= 11'd0;
            record_words <= {CONFIG_WORDS{32'd0}};
            id_counter <= 32'd0; id_numeric <= 32'd0; id_schedule <= 32'd0;
            id_in0 <= 32'd0; id_in1 <= 32'd0; id_in2 <= 32'd0; id_in3 <= 32'd0;
            id_out0 <= 32'd0; id_out1 <= 32'd0;
        end else if (begin_valid) begin
            //: A record is per-dispatch. The header words that do not come from a
            //: descriptor are written here; word 6 waits for the wait set.
            record_valid <= 1'b0;
            error_code <= ERR_NONE;
            collected_mask <= 11'd0;
            for (w = 0; w < CONFIG_WORDS; w = w + 1)
                record_words[w*32 +: 32] <= 32'd0;
            record_words[0*32 +: 32] <= cfg_profile;
            record_words[1*32 +: 32] <= cfg_active_tokens;
            record_words[2*32 +: 32] <= instruction_pc;
            record_words[3*32 +: 32] <= instruction_flags;
            record_words[4*32 +: 32] <= instruction_operator_id;
            record_words[5*32 +: 32] <= instruction_wait_set_id;
            record_words[7*32 +: 32] <= instruction_signal_event_id;
            record_words[8*32 +: 32] <= instruction_control_id;
            record_words[9*32 +: 32] <= instruction_source_operation_id;
        end else begin
            if (is_operator) begin
                if (!operator_matches) begin
                    //: Fail closed and say which check refused. A collector that
                    //: assembled the record anyway would hand an engine a bundle
                    //: describing an operator it does not implement.
                    error_code <= ERR_OPERATOR;
                end else begin
                    record_words[10*32 +: 18*32] <= operator_words;
                    id_counter  <= operator_words[5*32 +: 32];
                    id_numeric  <= operator_words[6*32 +: 32];
                    id_schedule <= operator_words[7*32 +: 32];
                    id_in0      <= operator_words[8*32 +: 32];
                    id_in1      <= operator_words[9*32 +: 32];
                    id_in2      <= operator_words[10*32 +: 32];
                    id_in3      <= operator_words[11*32 +: 32];
                    id_out0     <= operator_words[12*32 +: 32];
                    id_out1     <= operator_words[13*32 +: 32];
                    collected_mask[R_OPERATOR] <= 1'b1;
                end
            end
            //: Not mutually exclusive with the above by construction: a role's id
            //: is compared independently, so a table that gave two roles one
            //: descriptor would fill both rather than silently pick one.
            if (is_wait) begin
                record_words[6*32 +: 32] <=
                    a3_record_wait_producer_0(desc_data);
                collected_mask[R_WAIT] <= 1'b1;
            end
            if (is_counter) begin
                record_words[28*32 +: 5*32] <= counter_words;
                collected_mask[R_COUNTER] <= 1'b1;
            end
            if (is_numeric) begin
                record_words[33*32 +: 11*32] <= numeric_words;
                record_words[44*32 +: 8*32] <= digest_words;
                collected_mask[R_NUMERIC] <= 1'b1;
            end
            if (is_schedule) begin
                record_words[52*32 +: 12*32] <= schedule_words;
                collected_mask[R_SCHEDULE] <= 1'b1;
            end
            if (is_in0) begin
                record_words[64*32 +: 10*32] <= view_words;
                collected_mask[R_IN0] <= 1'b1;
            end
            if (is_in1) begin
                record_words[74*32 +: 10*32] <= view_words;
                collected_mask[R_IN1] <= 1'b1;
            end
            if (is_in2) begin
                record_words[84*32 +: 10*32] <= view_words;
                collected_mask[R_IN2] <= 1'b1;
            end
            if (is_in3) begin
                record_words[94*32 +: 10*32] <= view_words;
                collected_mask[R_IN3] <= 1'b1;
            end
            if (is_out0) begin
                record_words[104*32 +: 10*32] <= view_words;
                collected_mask[R_OUT0] <= 1'b1;
            end
            if (is_out1) begin
                record_words[114*32 +: 10*32] <= view_words;
                collected_mask[R_OUT1] <= 1'b1;
            end
        end
    end

    //: The record is complete when every role has been seen and nothing refused.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            record_valid <= 1'b0;
        else
            record_valid <= (collected_mask == ALL_ROLES) && (error_code == ERR_NONE);
    end
endmodule
