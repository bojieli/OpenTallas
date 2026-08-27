`timescale 1ns/1ps
// Packetizing sender with one in-flight retry window.  The complete packet is
// retained until a positive acknowledgement, so replay cannot duplicate a
// state commit at the receiver.
module ot_stage_link_tx #(
    parameter integer FLIT_W = 256,
    parameter integer MAX_FLITS = 256,
    parameter integer SEQ_W = 8,
    parameter integer RETRY_MAX = 2,
    parameter integer ACK_TIMEOUT = 1024
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         in_valid,
    output wire                         in_ready,
    input  wire [FLIT_W-1:0]             in_flit,
    input  wire                         in_last,
    input  wire [SEQ_W-1:0]             in_packet_seq,
    input  wire                         remote_credit,
    output reg                          credit_consumed,
    output wire                         link_valid,
    input  wire                         link_ready,
    output wire [FLIT_W-1:0]             link_flit,
    output wire [31:0]                  link_flit_crc,
    output wire [31:0]                  link_packet_crc,
    output wire                         link_last,
    output wire [SEQ_W-1:0]             link_packet_seq,
    input  wire                         ack_valid,
    input  wire [SEQ_W-1:0]             ack_seq,
    input  wire                         ack_ok,
    input  wire                         abort,
    output reg                          busy,
    output reg [1:0]                    retry_count,
    output reg                          timeout,
    output reg                          error
);
    localparam integer IDX_W = (MAX_FLITS <= 2) ? 1 : $clog2(MAX_FLITS);
    localparam integer CNT_W = $clog2(MAX_FLITS+1);
    localparam [CNT_W-1:0] MAX_FLITS_COUNT = MAX_FLITS[CNT_W-1:0];
    localparam [1:0] RETRY_MAX_COUNT = RETRY_MAX[1:0];
    localparam [2:0] ST_IDLE=3'd0, ST_COLLECT=3'd1, ST_SEND=3'd2,
                     ST_WAIT_ACK=3'd3, ST_ABORT=3'd4;
    reg [2:0] state;
    reg [FLIT_W-1:0] packet_mem [0:MAX_FLITS-1];
    reg [CNT_W-1:0] packet_count;
    reg [IDX_W-1:0] send_index;
    reg [SEQ_W-1:0] packet_seq;
    reg [31:0] packet_crc;
    reg [31:0] ack_timer;
    integer i;
    wire in_fire = in_valid && in_ready;
    wire link_fire = link_valid && link_ready;
    wire packet_full = (packet_count >= MAX_FLITS_COUNT);
    wire [IDX_W-1:0] packet_write_index = packet_count[IDX_W-1:0];
    wire [IDX_W-1:0] last_packet_index =
        packet_count[IDX_W-1:0] - 1'b1;

    function automatic [31:0] crc32c_flit;
        input [FLIT_W-1:0] d;
        integer by;
        integer bi;
        reg [31:0] c;
        reg fb;
        begin
            c = 32'hffffffff;
            for (by = 0; by < FLIT_W/8; by = by + 1)
                for (bi = 0; bi < 8; bi = bi + 1) begin
                    fb = c[0] ^ d[by*8+bi];
                    c = c >> 1;
                    if (fb) c = c ^ 32'h82f63b78;
                end
            crc32c_flit = c ^ 32'hffffffff;
        end
    endfunction

    function automatic [31:0] crc32c_extend;
        input [31:0] state_in;
        input [FLIT_W-1:0] d;
        integer by;
        integer bi;
        reg [31:0] c;
        reg fb;
        begin
            c = state_in;
            for (by = 0; by < FLIT_W/8; by = by + 1)
                for (bi = 0; bi < 8; bi = bi + 1) begin
                    fb = c[0] ^ d[by*8+bi];
                    c = c >> 1;
                    if (fb) c = c ^ 32'h82f63b78;
                end
            crc32c_extend = c;
        end
    endfunction

    assign in_ready = (state == ST_IDLE && remote_credit) ||
                      (state == ST_COLLECT && !packet_full);
    assign link_valid = (state == ST_SEND);
    assign link_flit = (state == ST_SEND) ? packet_mem[send_index] : {FLIT_W{1'b0}};
    assign link_flit_crc = (state == ST_SEND) ? crc32c_flit(packet_mem[send_index]) : 32'b0;
    assign link_packet_crc = packet_crc;
    assign link_last = (state == ST_SEND) && (send_index == last_packet_index);
    assign link_packet_seq = packet_seq;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= ST_IDLE;
            packet_count <= 0;
            send_index <= 0;
            packet_seq <= 0;
            packet_crc <= 32'hffffffff;
            ack_timer <= 0;
            credit_consumed <= 1'b0;
            busy <= 1'b0;
            retry_count <= 0;
            timeout <= 1'b0;
            error <= 1'b0;
        end else begin
            credit_consumed <= 1'b0;
            timeout <= 1'b0;
            case (state)
                ST_IDLE: begin
                    busy <= 1'b0;
                    if (in_fire) begin
                        retry_count <= 0;
                        packet_mem[0] <= in_flit;
                        packet_count <= 1;
                        packet_seq <= in_packet_seq;
                        packet_crc <= in_last ?
                                      (crc32c_extend(32'hffffffff, in_flit) ^ 32'hffffffff) :
                                      crc32c_extend(32'hffffffff, in_flit);
                        credit_consumed <= 1'b1;
                        busy <= 1'b1;
                        if (in_last) begin
                            send_index <= 0;
                            state <= ST_SEND;
                        end else begin
                            state <= ST_COLLECT;
                        end
                    end
                end
                ST_COLLECT: begin
                    busy <= 1'b1;
                    if (abort || packet_full) begin
                        error <= 1'b1;
                        state <= ST_ABORT;
                    end else if (in_fire) begin
                        packet_mem[packet_write_index] <= in_flit;
                        packet_count <= packet_count + 1'b1;
                        packet_crc <= in_last ?
                                      (crc32c_extend(packet_crc, in_flit) ^ 32'hffffffff) :
                                      crc32c_extend(packet_crc, in_flit);
                        if (in_packet_seq != packet_seq) begin
                            error <= 1'b1;
                            state <= ST_ABORT;
                        end else if (in_last) begin
                            send_index <= 0;
                            state <= ST_SEND;
                        end
                    end
                end
                ST_SEND: begin
                    busy <= 1'b1;
                    if (abort) begin
                        error <= 1'b1;
                        state <= ST_ABORT;
                    end else if (link_fire) begin
                        if (send_index == last_packet_index) begin
                            ack_timer <= 0;
                            state <= ST_WAIT_ACK;
                        end else begin
                            send_index <= send_index + 1'b1;
                        end
                    end
                end
                ST_WAIT_ACK: begin
                    busy <= 1'b1;
                    if (abort) begin
                        error <= 1'b1;
                        state <= ST_ABORT;
                    end else if (ack_valid && (ack_seq == packet_seq)) begin
                        if (ack_ok) begin
                            state <= ST_IDLE;
                            busy <= 1'b0;
                        end else if (retry_count < RETRY_MAX_COUNT) begin
                            retry_count <= retry_count + 1'b1;
                            send_index <= 0;
                            state <= ST_SEND;
                        end else begin
                            error <= 1'b1;
                            state <= ST_ABORT;
                        end
                    end else if (ACK_TIMEOUT != 0 && ack_timer >= ACK_TIMEOUT) begin
                        timeout <= 1'b1;
                        if (retry_count < RETRY_MAX_COUNT) begin
                            retry_count <= retry_count + 1'b1;
                            send_index <= 0;
                            state <= ST_SEND;
                        end else begin
                            error <= 1'b1;
                            state <= ST_ABORT;
                        end
                    end else begin
                        ack_timer <= ack_timer + 1'b1;
                    end
                end
                ST_ABORT: begin
                    busy <= 1'b0;
                    // Abort is a terminal packet outcome; a new packet may be
                    // accepted only after the caller observes error and drops
                    // the poisoned transaction.
                    if (!abort)
                        state <= ST_IDLE;
                end
                default: state <= ST_ABORT;
            endcase
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (MAX_FLITS < 1 || MAX_FLITS > 256 || RETRY_MAX > 2)
            $error("ot_stage_link_tx parameter outside ICD limit");
    end
`endif
endmodule
