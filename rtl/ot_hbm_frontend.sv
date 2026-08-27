`timescale 1ns/1ps
// Tagged HBM wrapper.  Requests reserve a tag before issue; responses may
// interleave across tags but must remain in order within each tag.
module ot_hbm_frontend #(
    parameter integer TAGS = 64,
    parameter integer MAX_OUTSTANDING = 64,
    parameter integer TAG_W = (TAGS <= 2) ? 1 : $clog2(TAGS),
    parameter integer COUNT_W = 16,
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
    reg active [0:TAGS-1];
    reg [COUNT_W-1:0] expected_beats [0:TAGS-1];
    reg [COUNT_W-1:0] received_beats [0:TAGS-1];
    reg [23:0] session_mem [0:TAGS-1];
    reg [1:0] operation_mem [0:TAGS-1];
    reg [63:0] address_mem [0:TAGS-1];
    reg poison_mem [0:TAGS-1];
    reg [TAG_W:0] outstanding;
    integer i;
    integer tag_index;
    reg tag_in_range;
    reg response_crc_bad;
    reg [15:0] calculated_crc;
    reg [591:0] response_body;
    wire req_fire = req_valid && req_ready;
    wire rsp_fire = rsp_valid && rsp_ready;

    assign outstanding_count = outstanding;
    assign req_ready = (outstanding < MAX_OUTSTANDING) &&
                       (req_tag < TAGS) && !active[req_tag];
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
        tag_index = rsp_tag;
        tag_in_range = (rsp_tag < TAGS);
        response_body = {rsp_error,rsp_last,rsp_tag,rsp_byte_valid,rsp_data};
        calculated_crc = crc16_response(response_body);
        response_crc_bad = CHECK_CRC && (calculated_crc != rsp_crc);
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
                active[i] = 1'b0;
                expected_beats[i] = 0;
                received_beats[i] = 0;
                session_mem[i] = 0;
                operation_mem[i] = 0;
                address_mem[i] = 0;
                poison_mem[i] = 1'b0;
            end
        end else begin
            req_accepted <= req_fire;
            complete_valid <= 1'b0;
            if (req_fire) begin
                active[req_tag] <= 1'b1;
                expected_beats[req_tag] <= req_burst_beats_minus_one + 1'b1;
                received_beats[req_tag] <= 0;
                session_mem[req_tag] <= req_session_id;
                operation_mem[req_tag] <= req_operation;
                address_mem[req_tag] <= req_byte_address;
                poison_mem[req_tag] <= 1'b0;
                outstanding <= outstanding + 1'b1;
            end
            if (rsp_fire) begin
                if (!tag_in_range || !active[tag_index]) begin
                    protocol_error <= 1'b1;
                    complete_valid <= 1'b1;
                    complete_tag <= rsp_tag;
                    complete_session_id <= 0;
                    complete_poison <= 1'b1;
                    complete_error <= 3'b111;
                end else begin
                    if (response_crc_bad || (rsp_error != 0)) begin
                        poison_mem[tag_index] <= 1'b1;
                        protocol_error <= protocol_error | response_crc_bad;
                    end
                    if (received_beats[tag_index] >= expected_beats[tag_index] ||
                        (rsp_last && (received_beats[tag_index] + 1'b1 != expected_beats[tag_index])) ||
                        (!rsp_last && (received_beats[tag_index] + 1'b1 == expected_beats[tag_index]))) begin
                        protocol_error <= 1'b1;
                        poison_mem[tag_index] <= 1'b1;
                    end
                    received_beats[tag_index] <= received_beats[tag_index] + 1'b1;
                    if (rsp_last || (received_beats[tag_index] + 1'b1 >= expected_beats[tag_index])) begin
                        complete_valid <= 1'b1;
                        complete_tag <= rsp_tag;
                        complete_session_id <= session_mem[tag_index];
                        complete_poison <= poison_mem[tag_index] || response_crc_bad ||
                                           (rsp_error != 0) || protocol_error;
                        complete_error <= response_crc_bad ? 3'b110 : rsp_error;
                        active[tag_index] <= 1'b0;
                        outstanding <= outstanding - 1'b1;
                    end
                end
            end
            if (req_fire && rsp_fire && tag_in_range && active[tag_index] &&
                (req_tag == rsp_tag))
                outstanding <= outstanding; // same-cycle recycle is forbidden by req_ready
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (TAGS < 2 || TAGS > 4096)
            $error("ot_hbm_frontend TAGS outside architectural limit");
    end
`endif
endmodule
