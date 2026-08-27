`timescale 1ns/1ps
// Packet receiver that buffers a complete packet before exposing any flit to
// the service plane.  CRC/sequence failures therefore cannot leak partial
// architectural state; duplicate packets are acknowledged idempotently.
module ot_stage_link_rx #(
    parameter integer FLIT_W = 256,
    parameter integer MAX_FLITS = 256,
    parameter integer SEQ_W = 8
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         link_valid,
    output wire                         link_ready,
    input  wire [FLIT_W-1:0]             link_flit,
    input  wire [31:0]                  link_flit_crc,
    input  wire [31:0]                  link_packet_crc,
    input  wire                         link_last,
    input  wire [SEQ_W-1:0]             link_packet_seq,
    output wire                         out_valid,
    input  wire                         out_ready,
    output wire [FLIT_W-1:0]             out_flit,
    output wire                         out_last,
    output wire [SEQ_W-1:0]             out_packet_seq,
    output wire                         out_poison,
    output reg                          ack_valid,
    output reg [SEQ_W-1:0]              ack_seq,
    output reg                          ack_ok,
    output reg                          protocol_error,
    output reg                          duplicate_packet
);
    localparam integer IDX_W = (MAX_FLITS <= 2) ? 1 : $clog2(MAX_FLITS);
    localparam integer CNT_W = $clog2(MAX_FLITS+1);
    localparam [1:0] ST_IDLE=2'd0, ST_COLLECT=2'd1, ST_DELIVER=2'd2;
    reg [1:0] state;
    reg [FLIT_W-1:0] packet_mem [0:MAX_FLITS-1];
    reg [CNT_W-1:0] packet_count;
    reg [CNT_W-1:0] deliver_index;
    reg [SEQ_W-1:0] packet_seq;
    reg [SEQ_W-1:0] expected_seq;
    reg have_sequence;
    reg packet_bad;
    reg [31:0] packet_crc_state;
    reg [31:0] next_packet_crc;
    reg [31:0] calculated_flit_crc;
    reg flit_bad;
    wire link_fire = link_valid && link_ready;
    wire out_fire = out_valid && out_ready;

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

    always @* begin
        calculated_flit_crc = crc32c_flit(link_flit);
        flit_bad = (calculated_flit_crc != link_flit_crc);
        next_packet_crc = crc32c_extend(packet_crc_state, link_flit);
    end

    assign link_ready = (state == ST_IDLE) || (state == ST_COLLECT && packet_count < MAX_FLITS);
    assign out_valid = (state == ST_DELIVER);
    assign out_flit = (state == ST_DELIVER) ? packet_mem[deliver_index] : {FLIT_W{1'b0}};
    assign out_last = (state == ST_DELIVER) && (deliver_index == packet_count-1'b1);
    assign out_packet_seq = packet_seq;
    assign out_poison = 1'b0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= ST_IDLE;
            packet_count <= 0;
            deliver_index <= 0;
            packet_seq <= 0;
            expected_seq <= 0;
            have_sequence <= 1'b0;
            packet_bad <= 1'b0;
            packet_crc_state <= 32'hffffffff;
            ack_valid <= 1'b0;
            ack_seq <= 0;
            ack_ok <= 1'b0;
            protocol_error <= 1'b0;
            duplicate_packet <= 1'b0;
        end else begin
            ack_valid <= 1'b0;
            if (link_fire) begin
                if (state == ST_IDLE) begin
                    packet_count <= 1;
                    deliver_index <= 0;
                    packet_seq <= link_packet_seq;
                    packet_crc_state <= next_packet_crc;
                    packet_bad <= flit_bad;
                    if (have_sequence && (link_packet_seq != expected_seq) &&
                        (link_packet_seq != expected_seq - 1'b1)) begin
                        packet_bad <= 1'b1;
                        protocol_error <= 1'b1;
                    end
                    if (have_sequence && (link_packet_seq == expected_seq - 1'b1)) begin
                        // Idempotent replay of an already accepted packet.
                        duplicate_packet <= 1'b1;
                        ack_valid <= 1'b1;
                        ack_seq <= link_packet_seq;
                        ack_ok <= 1'b1;
                        packet_count <= 0;
                        packet_bad <= 1'b0;
                    end else begin
                        packet_mem[0] <= link_flit;
                        if (link_last) begin
                            if (flit_bad || ((next_packet_crc ^ 32'hffffffff) != link_packet_crc)) begin
                                ack_valid <= 1'b1;
                                ack_seq <= link_packet_seq;
                                ack_ok <= 1'b0;
                                protocol_error <= 1'b1;
                                state <= ST_IDLE;
                            end else begin
                                state <= ST_DELIVER;
                            end
                        end else begin
                            state <= ST_COLLECT;
                        end
                    end
                end else begin // ST_COLLECT
                    packet_mem[packet_count] <= link_flit;
                    packet_count <= packet_count + 1'b1;
                    packet_crc_state <= next_packet_crc;
                    if (flit_bad)
                        packet_bad <= 1'b1;
                    if (link_packet_seq != packet_seq) begin
                        packet_bad <= 1'b1;
                        protocol_error <= 1'b1;
                    end
                    if (link_last) begin
                        if (packet_bad || flit_bad || ((next_packet_crc ^ 32'hffffffff) != link_packet_crc)) begin
                            ack_valid <= 1'b1;
                            ack_seq <= packet_seq;
                            ack_ok <= 1'b0;
                            protocol_error <= 1'b1;
                            state <= ST_IDLE;
                            packet_count <= 0;
                        end else begin
                            deliver_index <= 0;
                            state <= ST_DELIVER;
                        end
                    end
                end
            end
            if (out_fire && out_last) begin
                ack_valid <= 1'b1;
                ack_seq <= packet_seq;
                ack_ok <= 1'b1;
                expected_seq <= packet_seq + 1'b1;
                have_sequence <= 1'b1;
                state <= ST_IDLE;
                packet_count <= 0;
            end else if (out_fire) begin
                deliver_index <= deliver_index + 1'b1;
            end
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (MAX_FLITS < 1 || MAX_FLITS > 256)
            $error("ot_stage_link_rx MAX_FLITS outside ICD limit");
    end
`endif
endmodule
