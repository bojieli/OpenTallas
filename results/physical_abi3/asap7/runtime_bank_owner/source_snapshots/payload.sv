`timescale 1ns/1ps
// Two-bank ownership for the runtime operand service. Memory writes must occur
// on fill_valid && fill_ready; the last accepted write publishes the bank for
// acquisition on the NEXT edge. Tags include an operation generation assigned
// by the scheduler; tags must not be reused while old responses can still arrive.
// The scheduler releases only after the last read response has drained. This
// controller grants ownership; it does not implement memory or drain detection.
module ot_a3_operand_bank_owner #(
    parameter integer TAG_BITS = 64,
    parameter integer BANK_WORDS = 512,
    parameter integer CW = $clog2(BANK_WORDS + 1)
) (
    input wire clk, rst_n,
    input wire reserve_valid, reserve_bank,
    input wire [TAG_BITS-1:0] reserve_tag,
    input wire [CW-1:0] reserve_words,
    output wire reserve_ready,
    input wire fill_valid, fill_bank,
    input wire [TAG_BITS-1:0] fill_tag,
    output wire fill_ready,
    output wire [CW-1:0] fill_index,
    input wire acquire_valid, acquire_bank,
    input wire [TAG_BITS-1:0] acquire_tag,
    output wire acquire_ready,
    output wire [CW-1:0] acquire_words,
    input wire release_valid, release_bank, release_retain,
    input wire [TAG_BITS-1:0] release_tag,
    output wire release_ready,
    input wire cancel_valid, cancel_bank,
    input wire [TAG_BITS-1:0] cancel_tag,
    output wire cancel_ready,
    input wire query_bank,
    input wire [TAG_BITS-1:0] query_tag,
    input wire [CW-1:0] query_index,
    output wire read_authorized,
    output wire [1:0] ready_banks, active_banks,
    output wire [3:0] bank_states
);
    localparam [1:0] FREE=0, FILLING=1, READY=2, ACTIVE=3;
    localparam [CW-1:0] MAX_WORDS = CW'(BANK_WORDS);
    reg [1:0] state [0:1];
    reg [TAG_BITS-1:0] tag [0:1];
    reg [CW-1:0] count [0:1], extent [0:1];
    // Cancellation wins over fill/acquire on its own bank. It may never free
    // an ACTIVE bank; the consumer must drain and release that bank first.
    assign cancel_ready = rst_n && (state[cancel_bank] == FILLING || state[cancel_bank] == READY)
                          && tag[cancel_bank] == cancel_tag;
    wire cancelling_fill = cancel_valid && cancel_ready && cancel_bank == fill_bank;
    wire cancelling_acquire = cancel_valid && cancel_ready && cancel_bank == acquire_bank;
    assign reserve_ready = rst_n && state[reserve_bank] == FREE && reserve_words != 0
                           && reserve_words <= MAX_WORDS;
    assign fill_ready = rst_n && state[fill_bank] == FILLING && tag[fill_bank] == fill_tag
                        && !cancelling_fill;
    assign fill_index = count[fill_bank];
    assign acquire_ready = rst_n && state[acquire_bank] == READY && tag[acquire_bank] == acquire_tag
                           && !cancelling_acquire;
    assign acquire_words = extent[acquire_bank];
    assign release_ready = rst_n && state[release_bank] == ACTIVE && tag[release_bank] == release_tag;
    assign ready_banks = {state[1] == READY, state[0] == READY};
    assign active_banks = {state[1] == ACTIVE, state[0] == ACTIVE};
    assign bank_states = {state[1],state[0]};
    assign read_authorized = rst_n && state[query_bank] == ACTIVE &&
                             tag[query_bank] == query_tag && query_index < extent[query_bank];
    integer b;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (b=0; b<2; b=b+1) begin
                state[b] <= FREE;
            end
        end else begin
            for (b=0; b<2; b=b+1) begin
                if (cancel_valid && cancel_ready && cancel_bank == b[0]) begin
                    state[b] <= FREE;
                end else case (state[b])
                    FREE: if (reserve_valid && reserve_ready && reserve_bank == b[0]) begin
                        state[b] <= FILLING;
                    end
                    FILLING: if (fill_valid && fill_ready && fill_bank == b[0]) begin
                        if (count[b] == extent[b] - 1'b1) state[b] <= READY;
                    end
                    READY: if (acquire_valid && acquire_ready && acquire_bank == b[0])
                        state[b] <= ACTIVE;
                    ACTIVE: if (release_valid && release_ready && release_bank == b[0])
                        state[b] <= release_retain ? READY : FREE;
                endcase
            end
        end
    end
    // State is the validity boundary. Every reservation initializes payload
    // before FILLING becomes observable; stale tags in FREE cannot authorize
    // fill, acquire, release, cancellation or reads.
    genvar bank;
    generate for(bank=0;bank<2;bank=bank+1)begin: bank_payload
        always @(posedge clk)begin
            if(reserve_valid && reserve_ready && reserve_bank==1'(bank))begin
                tag[bank]<=reserve_tag;extent[bank]<=reserve_words;count[bank]<=0;
            end else if(fill_valid && fill_ready && fill_bank==1'(bank))
                count[bank]<=count[bank]+1'b1;
        end
    end endgenerate
endmodule
