`timescale 1ns/1ps
// Successor-only primitive. Calendar owns put_slot/get_slot/address/identity.
// No ready/credit ports: fault observations never alter a reserved transfer.
// Existing routed ATTQ/home/comb masters are unchanged and remain historical.
module ot_s81_svc_static_store #(
    parameter integer WIDTH = 2132,
    parameter integer DEPTH = 8,
    parameter integer ID_W = 32,
    parameter integer AW = (DEPTH <= 1) ? 1 : $clog2(DEPTH)
) (
    input wire clk, rst_n,
    input wire put_slot,
    input wire [AW-1:0] put_addr,
    input wire [ID_W-1:0] put_id,
    input wire producer_v,
    input wire [ID_W-1:0] producer_id,
    input wire [WIDTH-1:0] producer_data,
    input wire get_slot,
    input wire [AW-1:0] get_addr,
    input wire [ID_W-1:0] get_id,
    input wire consumer_available,
    output reg result_v,
    output reg [ID_W-1:0] result_id,
    output reg [WIDTH-1:0] result_data,
    output reg [6:0] fault_code
);
    reg [WIDTH-1:0] payload [0:DEPTH-1];
    reg [ID_W-1:0] identity [0:DEPTH-1];
    reg [DEPTH-1:0] occupied, valid;
    // Read-before-write: a same-address exchange returns the preceding word.
    // Missing/stale data is marked invalid; the calendar still advances.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            occupied <= '0; valid <= '0; result_v <= 0;
            result_id <= 0; result_data <= 0; fault_code <= 0;
        end else begin
            result_v <= get_slot;
            if (producer_v && !put_slot) fault_code[0] <= 1;
            if (put_slot && !producer_v) fault_code[1] <= 1;
            if (put_slot && producer_id != put_id) fault_code[2] <= 1;
            if (get_slot && !consumer_available) fault_code[3] <= 1;
            if (get_slot) begin
                result_id <= get_id;
                if (32'(get_addr) >= DEPTH) begin
                    fault_code[6] <= 1;
                    result_data <= '0;
                end else begin
                    result_data <= payload[get_addr];
                    if (!occupied[get_addr] || !valid[get_addr]) fault_code[4] <= 1;
                    if (identity[get_addr] != get_id) fault_code[2] <= 1;
                    occupied[get_addr] <= 0;
                    valid[get_addr] <= 0;
                end
            end
            if (put_slot) begin
                if (32'(put_addr) >= DEPTH) fault_code[6] <= 1;
                else begin
                    if (occupied[put_addr] && !(get_slot && get_addr == put_addr))
                        fault_code[5] <= 1;
                    payload[put_addr] <= producer_data;
                    identity[put_addr] <= put_id;
                    occupied[put_addr] <= 1;
                    valid[put_addr] <= producer_v && producer_id == put_id;
                end
            end
        end
    end
endmodule
