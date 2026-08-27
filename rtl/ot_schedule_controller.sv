`timescale 1ns/1ps
// Active/shadow static schedule store.  Shadow writes are isolated from the
// running bank and become visible only at a quiescent epoch boundary.
module ot_schedule_controller #(
    parameter integer PORTS = 8,
    parameter integer SLOTS = 16,
    parameter integer PORT_ID_W = (PORTS <= 2) ? 1 : $clog2(PORTS),
    parameter integer SLOT_W = (SLOTS <= 2) ? 1 : $clog2(SLOTS),
    parameter integer ENTRY_W = PORT_ID_W + 2
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         shadow_wr_valid,
    output wire                         shadow_wr_ready,
    input  wire [SLOT_W-1:0]             shadow_wr_slot,
    input  wire [ENTRY_W-1:0]            shadow_wr_data,
    input  wire                         commit_req,
    input  wire                         quiescent,
    input  wire                         epoch_boundary,
    input  wire                         manifest_crc_ok,
    output reg                          commit_ack,
    output reg                          commit_error,
    output reg                          schedule_valid,
    output reg [7:0]                    epoch_id,
    input  wire [SLOT_W-1:0]             active_slot,
    output wire                          active_slot_valid,
    output wire [PORT_ID_W-1:0]          active_source_port,
    output wire                          active_expect_valid,
    output wire                          active_idle,
    output wire [31:0]                   active_schedule_crc,
    output wire                          commit_pending
);
    reg [ENTRY_W-1:0] schedule_mem [0:1][0:SLOTS-1];
    reg active_bank;
    reg pending;
    reg shadow_invalid;
    reg [31:0] shadow_crc;
    reg [31:0] active_crc [0:1];
    integer i;
    integer source_int;
    reg [PORT_ID_W-1:0] source_field;
    reg idle_field;
    reg expect_field;
    reg [31:0] crc_work;
    integer b;
    integer bit_i;

    assign shadow_wr_ready = !pending && !schedule_valid ? 1'b1 : !pending;
    assign commit_pending = pending;
    assign active_slot_valid = schedule_valid && (active_slot < SLOTS) &&
                               !schedule_mem[active_bank][active_slot][ENTRY_W-1];
    assign active_source_port = schedule_mem[active_bank][active_slot][PORT_ID_W-1:0];
    assign active_expect_valid = schedule_mem[active_bank][active_slot][PORT_ID_W];
    assign active_idle = schedule_mem[active_bank][active_slot][ENTRY_W-1];
    assign active_schedule_crc = active_crc[active_bank];

    // Deterministic CRC over the exact entry bytes (low-order byte first).
    function automatic [31:0] crc32_entries;
        input integer bank;
        integer slot_i;
        integer byte_i;
        integer bit_j;
        reg [31:0] c;
        reg fb;
        reg [ENTRY_W-1:0] entry;
        begin
            c = 32'hffffffff;
            for (slot_i = 0; slot_i < SLOTS; slot_i = slot_i + 1) begin
                entry = schedule_mem[bank][slot_i];
                for (byte_i = 0; byte_i < (ENTRY_W+7)/8; byte_i = byte_i + 1) begin
                    for (bit_j = 0; bit_j < 8; bit_j = bit_j + 1) begin
                        if (byte_i*8+bit_j < ENTRY_W) begin
                            fb = c[0] ^ entry[byte_i*8+bit_j];
                            c = c >> 1;
                            if (fb) c = c ^ 32'h82f63b78;
                        end
                    end
                end
            end
            crc32_entries = c ^ 32'hffffffff;
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active_bank <= 1'b0;
            pending <= 1'b0;
            schedule_valid <= 1'b0;
            epoch_id <= 8'h00;
            commit_ack <= 1'b0;
            commit_error <= 1'b0;
            shadow_invalid <= 1'b0;
            shadow_crc <= 32'h0;
            active_crc[0] <= 32'h0;
            active_crc[1] <= 32'h0;
            for (i = 0; i < SLOTS; i = i + 1) begin
                schedule_mem[0][i] = {ENTRY_W{1'b1}}; // idle after reset
                schedule_mem[1][i] = {ENTRY_W{1'b1}};
            end
        end else begin
            commit_ack <= 1'b0;
            if (shadow_wr_valid && shadow_wr_ready) begin
                source_field = shadow_wr_data[PORT_ID_W-1:0];
                expect_field = shadow_wr_data[PORT_ID_W];
                idle_field = shadow_wr_data[ENTRY_W-1];
                source_int = source_field;
                if (shadow_wr_slot >= SLOTS ||
                    (!idle_field && source_int >= PORTS)) begin
                    shadow_invalid <= 1'b1;
                    commit_error <= 1'b1;
                end else begin
                    schedule_mem[~active_bank][shadow_wr_slot] <= shadow_wr_data;
                end
            end
            if (commit_req && !pending) begin
                if (shadow_invalid || !manifest_crc_ok) begin
                    commit_error <= 1'b1;
                end else begin
                    pending <= 1'b1;
                end
            end
            if (pending && quiescent && epoch_boundary) begin
                // Capture CRC before changing the bank; software can compare
                // this value with its certificate on the acknowledgement.
                shadow_crc <= crc32_entries(~active_bank);
                active_crc[~active_bank] <= crc32_entries(~active_bank);
                active_bank <= ~active_bank;
                schedule_valid <= 1'b1;
                epoch_id <= epoch_id + 1'b1;
                pending <= 1'b0;
                commit_ack <= 1'b1;
                shadow_invalid <= 1'b0;
            end
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (PORTS < 1 || PORTS > 4096 || SLOTS < 1 || SLOTS > 256)
            $error("ot_schedule_controller parameter outside architectural limit");
    end
`endif
endmodule
