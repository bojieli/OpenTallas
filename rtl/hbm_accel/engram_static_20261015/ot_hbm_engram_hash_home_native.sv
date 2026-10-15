`timescale 1ns/1ps
// Actual released 12-stage hash plus both eight-home dispatch streams.
// The compressed-token input is an explicit boundary; raw-token mapping/history
// context and external HBM return/collective integration remain separate work.
module ot_hbm_engram_hash_home_native #(
    parameter integer MUTANT_RANK = 0
)(
    input wire clk, rst_n, in_valid, in_first,
    input wire [16:0] in_cid,
    output wire [1:0] request_valid,
    output wire [13:0] request_rank,
    output wire [73:0] request_address,
    output wire [51:0] request_local_row,
    output wire [9:0] request_staging_slot,
    output wire [39:0] gather_slot_id,
    output wire [9:0] request_list_index,
    output wire done,
    output wire fault
);
    wire hv;
    wire [1391:0] hashes;
    reg [1391:0] held;
    reg serial_active, busy, local_fault;
    reg [4:0] serial_index;
    wire [1:0] finished, child_fault;
    ot_hdc_engram_hash_shipped hash (
        .clk(clk),.rst_n(rst_n),.in_valid(in_valid && !busy),
        .in_first(in_first),.in_cid(in_cid),.out_valid(hv),.out_row(hashes));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            held <= 0; serial_active <= 0; serial_index <= 0;
            busy <= 0; local_fault <= 0;
        end else begin
            if (in_valid) begin
                if (busy) local_fault <= 1;
                else busy <= 1;
            end
            if (hv) begin
                if (serial_active) local_fault <= 1;
                held <= hashes; serial_active <= 1; serial_index <= 0;
            end else if (serial_active) begin
                if (serial_index == 23) serial_active <= 0;
                else serial_index <= serial_index + 1'b1;
            end
            if (&finished) busy <= 0;
        end
    end
    assign done = &finished;
    assign fault = local_fault | (|child_fault);
    for (genvar l = 0; l < 2; l=l+1) begin : g_layer
        wire [28:0] row = held[(l*24 + serial_index)*29 +:29];
        ot_hbm_engram_home_dispatch #(.MUTANT_RANK(MUTANT_RANK)) home (
            .clk(clk),.rst_n(rst_n),.start(hv),.layer_index(1'(l)),
            .row_valid(serial_active),.row_id(row),
            .request_valid(request_valid[l]),.request_rank(request_rank[l*7+:7]),
            .request_address(request_address[l*37+:37]),
            .request_local_row(request_local_row[l*26+:26]),
            .request_staging_slot(request_staging_slot[l*5+:5]),
            .gather_slot_id(gather_slot_id[l*20+:20]),
            .request_list_index(request_list_index[l*5+:5]),
            .done(finished[l]),.fault(child_fault[l]));
    end
endmodule
