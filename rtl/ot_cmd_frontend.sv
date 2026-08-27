`timescale 1ns/1ps
// Host-command parser, legality checker, and ordered response queue.  State is
// allocated only after CRC/version/field checks pass; a legal command is held
// until the stage controller accepts the complete parsed payload.
module ot_cmd_frontend #(
    parameter integer RSP_DEPTH = 8,
    parameter integer MAX_LAYERS = 128,
    parameter integer MAX_CONTEXT = 1048576,
    parameter integer MAX_BATCH = 65536,
    parameter integer EXPECTED_ABI_MAJOR = 1,
    parameter integer EXPECTED_ABI_MINOR = 0
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         cmd_valid,
    output wire                         cmd_ready,
    input  wire [255:0]                 cmd_record,
    output wire                         dispatch_valid,
    input  wire                         dispatch_ready,
    output wire [7:0]                   dispatch_opcode,
    output wire [7:0]                   dispatch_flags,
    output wire [7:0]                   dispatch_epoch,
    output wire [7:0]                   dispatch_schedule,
    output wire [23:0]                  dispatch_session,
    output wire [19:0]                  dispatch_position,
    output wire [19:0]                  dispatch_context_minus_one,
    output wire [15:0]                  dispatch_batch_minus_one,
    output wire [6:0]                   dispatch_first_layer,
    output wire [6:0]                   dispatch_last_layer,
    output wire [3:0]                   dispatch_draft_tokens,
    output wire [7:0]                   dispatch_image_slot,
    output wire [47:0]                  dispatch_activation_address,
    output wire [31:0]                  dispatch_cookie,
    output wire [15:0]                  dispatch_transaction_id,
    input  wire                         completion_valid,
    input  wire [7:0]                   completion_status,
    input  wire [7:0]                   completion_error_source,
    input  wire [3:0]                   completion_syndrome,
    input  wire [7:0]                   active_epoch,
    input  wire [7:0]                   active_schedule,
    input  wire [255:0]                 image_slot_valid,
    input  wire                         service_enable,
    input  wire                         quiesce,
    output wire                         rsp_valid,
    input  wire                         rsp_ready,
    output wire [127:0]                 rsp_record,
    output reg [31:0]                   bad_crc_count,
    output reg [31:0]                   bad_field_count,
    output reg [31:0]                   accepted_count,
    output reg [31:0]                   transaction_counter
);
    localparam [7:0] ST_SUCCESS = 8'h00;
    localparam [7:0] ST_BAD_OPCODE = 8'h01;
    localparam [7:0] ST_BAD_VERSION = 8'h02;
    localparam [7:0] ST_BAD_FIELD = 8'h03;
    localparam [7:0] ST_BAD_CRC = 8'h04;
    localparam [7:0] ST_BUSY = 8'h05;
    localparam [7:0] ST_IMAGE = 8'h08;
    localparam [7:0] ST_THERMAL = 8'h0c;
    localparam [7:0] ST_INTERNAL = 8'h0f;
    localparam integer RSP_PTR_W = $clog2(RSP_DEPTH);
    localparam integer RSP_CNT_W = $clog2(RSP_DEPTH+1);
    localparam integer RSP_LAST_INT = RSP_DEPTH-1;
    localparam [RSP_PTR_W-1:0] RSP_LAST = RSP_LAST_INT[RSP_PTR_W-1:0];
    localparam [RSP_CNT_W-1:0] RSP_ADMISSION_LIMIT = RSP_LAST_INT[RSP_CNT_W-1:0];
    localparam [7:0] ABI_MAJOR_VALUE = EXPECTED_ABI_MAJOR[7:0];
    localparam [7:0] ABI_MINOR_VALUE = EXPECTED_ABI_MINOR[7:0];
    reg hold_valid;
    reg inflight;
    reg [7:0] hold_opcode;
    reg [7:0] hold_flags;
    reg [7:0] hold_epoch;
    reg [7:0] hold_schedule;
    reg [23:0] hold_session;
    reg [19:0] hold_position;
    reg [19:0] hold_context_m1;
    reg [15:0] hold_batch_m1;
    reg [6:0] hold_first_layer;
    reg [6:0] hold_last_layer;
    reg [3:0] hold_draft_tokens;
    reg [7:0] hold_image_slot;
    reg [47:0] hold_activation_address;
    reg [31:0] hold_cookie;
    reg [15:0] hold_txn;
    reg [127:0] rsp_mem [0:RSP_DEPTH-1];
    reg [RSP_PTR_W-1:0] rsp_wr_ptr;
    reg [RSP_PTR_W-1:0] rsp_rd_ptr;
    reg [RSP_CNT_W-1:0] rsp_count;
    reg [7:0] check_status;
    reg crc_bad;
    reg version_bad;
    reg opcode_bad;
    reg field_bad;
    reg image_bad;
    reg state_bad;
    reg [7:0] opcode;
    reg [7:0] abi_major;
    reg [7:0] abi_minor;
    reg [7:0] epoch;
    reg [7:0] schedule_id;
    reg [23:0] session;
    reg [19:0] position;
    reg [19:0] context_m1;
    reg [6:0] first_layer;
    reg [6:0] last_layer;
    reg [3:0] draft_tokens;
    reg [7:0] image_slot;
    reg [15:0] supplied_crc;
    reg [15:0] calculated_crc;
    reg [31:0] cookie;
    wire cmd_fire = cmd_valid && cmd_ready;
    wire dispatch_fire = dispatch_valid && dispatch_ready;
    wire rsp_pop = rsp_valid && rsp_ready;
    wire rsp_push = (cmd_fire && (check_status != ST_SUCCESS)) || completion_valid;
    wire context_limit_bad;
    wire batch_limit_bad;
    wire layer_limit_bad;
    generate
        if (MAX_CONTEXT >= 1048576) begin : GEN_FULL_CONTEXT_FIELD
            assign context_limit_bad = 1'b0;
        end else begin : GEN_LIMITED_CONTEXT_FIELD
            localparam [19:0] MAX_CONTEXT_VALUE = MAX_CONTEXT;
            assign context_limit_bad = (context_m1 >= MAX_CONTEXT_VALUE);
        end
        if (MAX_BATCH >= 65536) begin : GEN_FULL_BATCH_FIELD
            assign batch_limit_bad = 1'b0;
        end else begin : GEN_LIMITED_BATCH_FIELD
            localparam [15:0] MAX_BATCH_VALUE = MAX_BATCH;
            assign batch_limit_bad = (cmd_record[127:112] >= MAX_BATCH_VALUE);
        end
        if (MAX_LAYERS >= 128) begin : GEN_FULL_LAYER_FIELD
            assign layer_limit_bad = 1'b0;
        end else begin : GEN_LIMITED_LAYER_FIELD
            localparam [6:0] MAX_LAYERS_VALUE = MAX_LAYERS;
            assign layer_limit_bad = (last_layer >= MAX_LAYERS_VALUE);
        end
    endgenerate

    function automatic [15:0] crc16_command;
        input [239:0] d;
        integer byte_i;
        integer bit_i;
        reg [15:0] c;
        reg fb;
        begin
            c = 16'hffff;
            for (byte_i = 0; byte_i < 30; byte_i = byte_i + 1) begin
                for (bit_i = 7; bit_i >= 0; bit_i = bit_i - 1) begin
                    fb = c[15] ^ d[byte_i*8+bit_i];
                    c = {c[14:0],1'b0};
                    if (fb) c = c ^ 16'h1021;
                end
            end
            crc16_command = c;
        end
    endfunction

    function automatic [127:0] make_response;
        input [7:0] st;
        input [7:0] op;
        input [7:0] ep;
        input [7:0] src;
        input [23:0] sid;
        input [19:0] pos;
        input [31:0] ck;
        input [3:0] syn;
        reg [111:0] body;
        reg [15:0] c;
        begin
            body = 112'b0;
            body[7:0] = st;
            body[15:8] = op;
            body[23:16] = ep;
            body[31:24] = src;
            body[55:32] = sid;
            body[75:56] = pos;
            body[107:76] = ck;
            body[111:108] = syn;
            c = crc16_response(body);
            make_response = {c,body};
        end
    endfunction

    function automatic [15:0] crc16_response;
        input [111:0] d;
        integer byte_i;
        integer bit_i;
        reg [15:0] c;
        reg fb;
        begin
            c = 16'hffff;
            for (byte_i = 0; byte_i < 14; byte_i = byte_i + 1) begin
                for (bit_i = 7; bit_i >= 0; bit_i = bit_i - 1) begin
                    fb = c[15] ^ d[byte_i*8+bit_i];
                    c = {c[14:0],1'b0};
                    if (fb) c = c ^ 16'h1021;
                end
            end
            crc16_response = c;
        end
    endfunction

    always @* begin
        opcode = cmd_record[7:0];
        abi_major = cmd_record[23:16];
        abi_minor = cmd_record[31:24];
        epoch = cmd_record[39:32];
        schedule_id = cmd_record[47:40];
        session = cmd_record[71:48];
        position = cmd_record[91:72];
        context_m1 = cmd_record[111:92];
        first_layer = cmd_record[134:128];
        last_layer = cmd_record[141:135];
        draft_tokens = cmd_record[145:142];
        image_slot = cmd_record[153:146];
        cookie = cmd_record[233:202];
        supplied_crc = cmd_record[255:240];
        calculated_crc = crc16_command(cmd_record[239:0]);
        crc_bad = (supplied_crc != calculated_crc);
        version_bad = (abi_major != ABI_MAJOR_VALUE) || (abi_minor > ABI_MINOR_VALUE);
        opcode_bad = !((opcode == 8'h00) || (opcode == 8'h01) || (opcode == 8'h02) ||
                        (opcode == 8'h10) || (opcode == 8'h11) || (opcode == 8'h20) ||
                        (opcode == 8'h21) || (opcode == 8'h22) || (opcode == 8'h30) ||
                        (opcode == 8'h31) || (opcode == 8'h40) || (opcode == 8'h41) ||
                        (opcode == 8'h7f));
        field_bad = (cmd_record[239:234] != 0) || (cmd_record[15:14] != 0) ||
                    context_limit_bad || batch_limit_bad ||
                    (first_layer > last_layer) || layer_limit_bad ||
                    (position > context_m1) ||
                    ((opcode == 8'h11) ? (draft_tokens == 0) :
                                         (draft_tokens != 0)) ||
                    ((opcode == 8'h7f) ? !cmd_record[13] : cmd_record[13]) ||
                    ((opcode != 8'h00) && !cmd_record[10]);
        image_bad = !image_slot_valid[image_slot];
        state_bad = ((opcode == 8'h10 || opcode == 8'h11) && (!service_enable || quiesce));
        if (crc_bad) check_status = ST_BAD_CRC;
        else if (version_bad) check_status = ST_BAD_VERSION;
        else if (opcode_bad) check_status = ST_BAD_OPCODE;
        else if (field_bad) check_status = ST_BAD_FIELD;
        else if (image_bad) check_status = ST_IMAGE;
        else if (epoch != active_epoch && opcode != 8'h00) check_status = 8'h07;
        else if (schedule_id != active_schedule && opcode != 8'h00) check_status = 8'h07;
        else if (state_bad) check_status = ST_THERMAL;
        else check_status = ST_SUCCESS;
    end

    assign cmd_ready = !hold_valid && !inflight && (rsp_count < RSP_ADMISSION_LIMIT);
    assign dispatch_valid = hold_valid;
    assign dispatch_opcode = hold_opcode;
    assign dispatch_flags = hold_flags;
    assign dispatch_epoch = hold_epoch;
    assign dispatch_schedule = hold_schedule;
    assign dispatch_session = hold_session;
    assign dispatch_position = hold_position;
    assign dispatch_context_minus_one = hold_context_m1;
    assign dispatch_batch_minus_one = hold_batch_m1;
    assign dispatch_first_layer = hold_first_layer;
    assign dispatch_last_layer = hold_last_layer;
    assign dispatch_draft_tokens = hold_draft_tokens;
    assign dispatch_image_slot = hold_image_slot;
    assign dispatch_activation_address = hold_activation_address;
    assign dispatch_cookie = hold_cookie;
    assign dispatch_transaction_id = hold_txn;
    assign rsp_valid = (rsp_count != 0);
    assign rsp_record = rsp_mem[rsp_rd_ptr];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            hold_valid <= 1'b0;
            inflight <= 1'b0;
            hold_opcode <= 8'b0;
            hold_flags <= 8'b0;
            hold_epoch <= 8'b0;
            hold_schedule <= 8'b0;
            hold_session <= 24'b0;
            hold_position <= 20'b0;
            hold_context_m1 <= 20'b0;
            hold_batch_m1 <= 16'b0;
            hold_first_layer <= 7'b0;
            hold_last_layer <= 7'b0;
            hold_draft_tokens <= 4'b0;
            hold_image_slot <= 8'b0;
            hold_activation_address <= 48'b0;
            hold_cookie <= 32'b0;
            hold_txn <= 16'b0;
            rsp_wr_ptr <= 0;
            rsp_rd_ptr <= 0;
            rsp_count <= 0;
            bad_crc_count <= 0;
            bad_field_count <= 0;
            accepted_count <= 0;
            transaction_counter <= 0;
        end else begin
            if (cmd_fire) begin
                hold_opcode <= opcode;
                hold_flags <= cmd_record[15:8];
                hold_epoch <= epoch;
                hold_schedule <= schedule_id;
                hold_session <= session;
                hold_position <= position;
                hold_context_m1 <= context_m1;
                hold_batch_m1 <= cmd_record[127:112];
                hold_first_layer <= first_layer;
                hold_last_layer <= last_layer;
                hold_draft_tokens <= draft_tokens;
                hold_image_slot <= image_slot;
                hold_activation_address <= cmd_record[201:154];
                hold_cookie <= cookie;
                hold_txn <= transaction_counter[15:0];
                transaction_counter <= transaction_counter + 1'b1;
                if (crc_bad) bad_crc_count <= bad_crc_count + 1'b1;
                if (field_bad || version_bad || opcode_bad) bad_field_count <= bad_field_count + 1'b1;
                if (check_status == ST_SUCCESS)
                    hold_valid <= 1'b1;
                else begin
                    rsp_mem[rsp_wr_ptr] <= make_response(check_status, opcode, epoch, 8'h01,
                                                         session, position, cookie, 4'b0);
                    if (rsp_wr_ptr == RSP_LAST) rsp_wr_ptr <= 0;
                    else rsp_wr_ptr <= rsp_wr_ptr + 1'b1;
                end
            end
            if (dispatch_fire) begin
                hold_valid <= 1'b0;
                inflight <= 1'b1;
                accepted_count <= accepted_count + 1'b1;
            end
            if (completion_valid) begin
                rsp_mem[rsp_wr_ptr] <= make_response(completion_status,
                                                     hold_opcode, hold_epoch,
                                                     completion_error_source,
                                                     hold_session, hold_position,
                                                     hold_cookie, completion_syndrome);
                if (rsp_wr_ptr == RSP_LAST) rsp_wr_ptr <= 0;
                else rsp_wr_ptr <= rsp_wr_ptr + 1'b1;
                inflight <= 1'b0;
            end
            if (rsp_pop) begin
                if (rsp_rd_ptr == RSP_LAST) rsp_rd_ptr <= 0;
                else rsp_rd_ptr <= rsp_rd_ptr + 1'b1;
            end
            case ({rsp_push,rsp_pop})
                2'b10: rsp_count <= rsp_count + 1'b1;
                2'b01: rsp_count <= rsp_count - 1'b1;
                default: rsp_count <= rsp_count;
            endcase
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (RSP_DEPTH < 2 || (RSP_DEPTH & (RSP_DEPTH-1)) != 0)
            $error("ot_cmd_frontend RSP_DEPTH must be a power of two >= 2");
    end
`endif
endmodule
