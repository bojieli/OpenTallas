`timescale 1ns/1ps
// Runtime weight service: two independently addressed single-port macros.
// Ownership protects resident data; a one-response read port holds valid/data
// under consumer backpressure. Release waits until the bank's response drains.
// Loader and cluster integration are deliberately outside this memory service.
module ot_a3_runtime_weight_banks #(
    parameter integer TAG_BITS = 64
) (
    input wire clk, rst_n,
    input wire reserve_valid, reserve_bank,
    input wire [TAG_BITS-1:0] reserve_tag,
    input wire [9:0] reserve_words,
    output wire reserve_ready,
    input wire fill_valid, fill_bank,
    input wire [TAG_BITS-1:0] fill_tag,
    input wire [127:0] fill_data,
    output wire fill_ready,
    input wire acquire_valid, acquire_bank,
    input wire [TAG_BITS-1:0] acquire_tag,
    output wire acquire_ready,
    output wire [9:0] acquire_words,
    input wire release_valid, release_bank, release_retain,
    input wire [TAG_BITS-1:0] release_tag,
    output wire release_ready,
    input wire cancel_valid, cancel_bank,
    input wire [TAG_BITS-1:0] cancel_tag,
    output wire cancel_ready,
    input wire read_valid, read_bank,
    input wire [TAG_BITS-1:0] read_tag,
    input wire [9:0] read_index,
    output wire read_ready,
    output reg response_valid,
    input wire response_ready,
    output wire [127:0] response_data,
    output reg response_bank,
    output reg [TAG_BITS-1:0] response_tag,
    output wire [1:0] ready_banks, active_banks
);
    wire [9:0] fill_index;
    wire [3:0] bank_states;
    wire read_authorized, owner_release_ready;
    wire response_space = !response_valid || response_ready;
    assign read_ready = read_authorized && response_space;
    wire read_fire = read_valid && read_ready;
    wire fill_fire = fill_valid && fill_ready;
    wire release_safe = !(response_valid && response_bank == release_bank) &&
                        !(read_fire && read_bank == release_bank);
    assign release_ready = owner_release_ready && release_safe;
    ot_a3_operand_bank_owner #(.TAG_BITS(TAG_BITS)) owner (
        .clk(clk), .rst_n(rst_n),
        .reserve_valid(reserve_valid), .reserve_bank(reserve_bank),
        .reserve_tag(reserve_tag), .reserve_words(reserve_words), .reserve_ready(reserve_ready),
        .fill_valid(fill_valid), .fill_bank(fill_bank), .fill_tag(fill_tag),
        .fill_ready(fill_ready), .fill_index(fill_index),
        .acquire_valid(acquire_valid), .acquire_bank(acquire_bank),
        .acquire_tag(acquire_tag), .acquire_ready(acquire_ready),
        .acquire_words(acquire_words),
        .release_valid(release_valid && release_safe), .release_bank(release_bank),
        .release_tag(release_tag), .release_retain(release_retain), .release_ready(owner_release_ready),
        .cancel_valid(cancel_valid), .cancel_bank(cancel_bank),
        .cancel_tag(cancel_tag), .cancel_ready(cancel_ready),
        .query_bank(read_bank), .query_tag(read_tag), .query_index(read_index),
        .read_authorized(read_authorized), .ready_banks(ready_banks),
        .active_banks(active_banks), .bank_states(bank_states)
    );
    wire [127:0] bank_data [0:1];
    genvar b;
    generate for (b=0; b<2; b=b+1) begin : bank
        wire reading = read_fire && read_bank == (b != 0);
        wire writing = fill_fire && fill_bank == (b != 0);
        wire [8:0] address = reading ? read_index[8:0] : fill_index[8:0];
        fakeram_512x128 memory (
            .clk(clk), .addr_in(address), .ce_in(reading || writing),
            .we_in(writing), .wd_in(fill_data), .rd_out(bank_data[b])
        );
    end endgenerate
    assign response_data = bank_data[response_bank];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            response_valid <= 1'b0; response_bank <= 1'b0; response_tag <= 0;
        end else begin
            if (response_space) response_valid <= read_fire;
            if (read_fire) begin
                response_bank <= read_bank;
                response_tag <= read_tag;
            end
        end
    end
endmodule
