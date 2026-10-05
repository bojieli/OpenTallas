`timescale 1ns/1ps
// Tagged HBM wrapper.  Requests reserve a tag before issue; responses may
// interleave across tags but must remain in order within each tag.
module ot_hbm_frontend #(
    parameter integer TAGS = 64,
    parameter integer MAX_OUTSTANDING = 64,
    parameter integer TAG_W = (TAGS <= 2) ? 1 : $clog2(TAGS),
    // The 16-bit minus-one request field represents 1..65,536 beats.  The
    // internal count therefore needs the carry bit; a 16-bit counter would
    // silently turn the architectural maximum into zero.
    parameter integer COUNT_W = 17,
    parameter integer CHECK_CRC = 1
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         req_valid,
    output wire                         req_ready,
    input  wire [63:0]                  req_byte_address,
    input  wire [23:0]                  req_session_id,
    input  wire [11:0]                  req_tag,
    input  wire [15:0]                  req_burst_beats_minus_one,
    input  wire [1:0]                   req_operation,
    input  wire [5:0]                   req_size_log2_bytes,
    input  wire [3:0]                   req_stage_id,
    output reg                          req_accepted,
    input  wire                         rsp_valid,
    output wire                         rsp_ready,
    input  wire [511:0]                 rsp_data,
    input  wire [63:0]                  rsp_byte_valid,
    input  wire [11:0]                  rsp_tag,
    input  wire                         rsp_last,
    input  wire [2:0]                   rsp_error,
    input  wire [15:0]                  rsp_crc,
    output reg                          complete_valid,
    output reg [11:0]                  complete_tag,
    output reg [23:0]                  complete_session_id,
    output reg                          complete_poison,
    output reg [2:0]                   complete_error,
    output reg                          protocol_error,
    output wire [TAG_W:0]               outstanding_count
);
    localparam integer TAG_INDEX_W = (TAGS <= 2) ? 1 : $clog2(TAGS);
    localparam [12:0] TAGS_LIMIT = TAGS[12:0];
    localparam [TAG_W:0] MAX_OUTSTANDING_COUNT =
        MAX_OUTSTANDING[TAG_W:0];
    reg active [0:TAGS-1];
    reg [COUNT_W-1:0] expected_beats [0:TAGS-1];
    reg [COUNT_W-1:0] received_beats [0:TAGS-1];
    reg [23:0] session_mem [0:TAGS-1];
    reg [1:0] operation_mem [0:TAGS-1];
    reg [63:0] address_mem [0:TAGS-1];
    reg poison_mem [0:TAGS-1];
    reg [TAG_W:0] outstanding;
    integer i;
    reg tag_in_range;
    reg response_crc_bad;
    reg response_framing_bad;
    reg [15:0] calculated_crc;
    reg [591:0] response_body;
    wire req_fire = req_valid && req_ready;
    wire rsp_fire = rsp_valid && rsp_ready;
    wire req_tag_in_range = ({1'b0,req_tag} < TAGS_LIMIT);
    wire [TAG_INDEX_W-1:0] req_tag_index = req_tag[TAG_INDEX_W-1:0];
    wire [TAG_INDEX_W-1:0] rsp_tag_index = rsp_tag[TAG_INDEX_W-1:0];
    wire [COUNT_W-1:0] requested_beats =
        {{(COUNT_W-16){1'b0}},req_burst_beats_minus_one} +
        {{(COUNT_W-1){1'b0}},1'b1};
    wire response_completes_active =
        rsp_fire && tag_in_range && active[rsp_tag_index] &&
        (rsp_last ||
         (received_beats[rsp_tag_index] + 1'b1 >=
          expected_beats[rsp_tag_index]));

    assign outstanding_count = outstanding;
    assign req_ready = (outstanding < MAX_OUTSTANDING_COUNT) &&
                       req_tag_in_range && !active[req_tag_index];
    assign rsp_ready = 1'b1; // response buffering is reserved per active tag

    function automatic [15:0] crc16_response;
        input [591:0] d;
        integer by;
        integer bi;
        reg [15:0] c;
        reg fb;
        begin
            c = 16'hffff;
            for (by = 0; by < 74; by = by + 1)
                for (bi = 7; bi >= 0; bi = bi - 1) begin
                    fb = c[15] ^ d[by*8+bi];
                    c = {c[14:0],1'b0};
                    if (fb) c = c ^ 16'h1021;
                end
            crc16_response = c;
        end
    endfunction

    always @* begin
        tag_in_range = ({1'b0,rsp_tag} < TAGS_LIMIT);
        response_body = {rsp_error,rsp_last,rsp_tag,rsp_byte_valid,rsp_data};
        calculated_crc = crc16_response(response_body);
        response_crc_bad = (CHECK_CRC != 0) && (calculated_crc != rsp_crc);
        response_framing_bad = 1'b0;
        if (tag_in_range && active[rsp_tag_index]) begin
            response_framing_bad =
                (received_beats[rsp_tag_index] >= expected_beats[rsp_tag_index]) ||
                (rsp_last &&
                 (received_beats[rsp_tag_index] + 1'b1 != expected_beats[rsp_tag_index])) ||
                (!rsp_last &&
                 (received_beats[rsp_tag_index] + 1'b1 == expected_beats[rsp_tag_index]));
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            outstanding <= 0;
            req_accepted <= 1'b0;
            complete_valid <= 1'b0;
            complete_tag <= 0;
            complete_session_id <= 0;
            complete_poison <= 1'b0;
            complete_error <= 0;
            protocol_error <= 1'b0;
            for (i = 0; i < TAGS; i = i + 1) begin
                active[i] <= 1'b0;
                expected_beats[i] <= 0;
                received_beats[i] <= 0;
                session_mem[i] <= 0;
                operation_mem[i] <= 0;
                address_mem[i] <= 0;
                poison_mem[i] <= 1'b0;
            end
        end else begin
            req_accepted <= req_fire;
            complete_valid <= 1'b0;
            if (req_fire) begin
                active[req_tag_index] <= 1'b1;
                expected_beats[req_tag_index] <= requested_beats;
                received_beats[req_tag_index] <= 0;
                session_mem[req_tag_index] <= req_session_id;
                operation_mem[req_tag_index] <= req_operation;
                address_mem[req_tag_index] <= req_byte_address;
                poison_mem[req_tag_index] <= 1'b0;
            end
            if (rsp_fire) begin
                if (!tag_in_range || !active[rsp_tag_index]) begin
                    protocol_error <= 1'b1;
                    complete_valid <= 1'b1;
                    complete_tag <= rsp_tag;
                    complete_session_id <= 0;
                    complete_poison <= 1'b1;
                    complete_error <= 3'b111;
                end else begin
                    if (response_crc_bad || (rsp_error != 0) || response_framing_bad) begin
                        poison_mem[rsp_tag_index] <= 1'b1;
                        protocol_error <= protocol_error | response_crc_bad;
                    end
                    if (response_framing_bad) begin
                        protocol_error <= 1'b1;
                    end
                    received_beats[rsp_tag_index] <= received_beats[rsp_tag_index] + 1'b1;
                    if (rsp_last ||
                        (received_beats[rsp_tag_index] + 1'b1 >=
                         expected_beats[rsp_tag_index])) begin
                        complete_valid <= 1'b1;
                        complete_tag <= rsp_tag;
                        complete_session_id <= session_mem[rsp_tag_index];
                        complete_poison <= poison_mem[rsp_tag_index] || response_crc_bad ||
                                           (rsp_error != 0) || response_framing_bad;
                        complete_error <= response_crc_bad ? 3'b110 :
                                          (response_framing_bad ? 3'b111 : rsp_error);
                        active[rsp_tag_index] <= 1'b0;
                    end
                end
            end
            // Admission and a different-tag completion may legally coincide.
            // Compose the two reservations instead of allowing textual NBA
            // ordering to lose either the increment or decrement.
            case ({req_fire,response_completes_active})
                2'b10: outstanding <= outstanding + 1'b1;
                2'b01: outstanding <= outstanding - 1'b1;
                default: outstanding <= outstanding;
            endcase
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (TAGS < 2 || TAGS > 4096)
            $error("ot_hbm_frontend TAGS outside architectural limit");
        if (MAX_OUTSTANDING < 1 || MAX_OUTSTANDING > TAGS)
            $error("ot_hbm_frontend MAX_OUTSTANDING outside tag capacity");
        if (COUNT_W < 17)
            $error("ot_hbm_frontend COUNT_W cannot represent 65,536 beats");
    end
`endif
endmodule
