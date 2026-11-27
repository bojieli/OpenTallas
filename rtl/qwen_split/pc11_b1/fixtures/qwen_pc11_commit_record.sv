`timescale 1ns/1ps
module qkd_pc11_commit_record_tx #(parameter integer TXDP=162) (
    input wire ck, rst_n, enabled, authorized,
    input wire parent_open, input wire [60:0] parent_identity, input wire [1:0] parent_user,
    input wire pcc_commit, input wire [60:0] pcc_identity,
    input wire port1_slot, input wire [3:0] slot_kind, input wire [4:0] slot_beat,
    input wire [1:0] slot_user, input wire port1_capture,
    input wire host_valid, input wire [547:0] host_record,
    output wire tx_valid, output wire [547:0] tx_record,
    output wire commit_capture,
    output reg fault
);
    localparam [3:0] KIND=4'd11;
    reg [TXDP-1:0] commit_slots;
    reg live, pending, sent;
    reg [60:0] owner;
    reg [1:0] user;
    wire commit_slot = enabled && port1_slot && slot_kind==KIND;
    wire valid_slot = live && slot_beat==5'd0 && slot_user==user;
    wire take_commit = commit_slots[TXDP-1];
    wire [5:0] zero_based_stage = owner[44:39]-6'd1;
    assign commit_capture = take_commit && port1_capture && authorized && pending && !fault && !host_valid;
    assign tx_valid = take_commit ? commit_capture : host_valid;
    assign tx_record = take_commit ? {5'd0,KIND,zero_based_stage,owner[60:45],5'd0,451'd0,owner} : host_record;

    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            commit_slots <= 0;
            live <= 0;
            pending <= 0;
            sent <= 0;
            owner <= 0;
            user <= 0;
            fault <= 0;
        end else if (enabled) begin
            commit_slots <= {commit_slots[TXDP-2:0],commit_slot && valid_slot && authorized && !fault};
            if (parent_open) begin
                if (!authorized || (live && !sent) || pcc_commit || take_commit ||
                    parent_identity[44:39]<1 || parent_identity[44:39]>36)
                    fault <= 1;
                else if (!fault) begin
                    live <= 1;
                    pending <= 0;
                    sent <= 0;
                    owner <= parent_identity;
                    user <= parent_user;
                end
            end else if ((!authorized && live) || (commit_slot && !valid_slot) ||
                         (pcc_commit && (!live || pending || sent || pcc_identity!=owner)) ||
                         (take_commit && !commit_capture)) begin
                fault <= 1;
            end else if (!fault) begin
                if (pcc_commit) pending <= 1;
                if (commit_capture) begin
                    pending <= 0;
                    sent <= 1;
                end
            end
        end
    end
endmodule

module qfd_pc11_commit_record_rx (
    input wire ck, rst_n, enabled, authorized,
    input wire awaited_parent_v, input wire [60:0] awaited_identity,
    input wire [1:0] awaited_user,
    input wire port1_slot, port1_event,
    input wire [3:0] slot_kind, input wire [4:0] slot_beat,
    input wire [1:0] slot_user,
    input wire [547:0] rx_record,
    output wire host_event,
    output reg remote_commit,
    output reg [60:0] remote_identity,
    output reg fault
);
    localparam [3:0] KIND=4'd11;
    reg live, accepted;
    reg [60:0] owner;
    reg [1:0] user;
    wire commit_slot = enabled && port1_slot && slot_kind==KIND;
    wire [5:0] zero_based_stage = owner[44:39]-6'd1;
    wire record_ok = live && !accepted && slot_beat==0 && slot_user==user &&
        rx_record=={5'd0,KIND,zero_based_stage,owner[60:45],5'd0,451'd0,owner};
    assign host_event = port1_event && !commit_slot;

    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            remote_commit <= 0;
            remote_identity <= 0;
            live <= 0;
            accepted <= 0;
            owner <= 0;
            user <= 0;
            fault <= 0;
        end else begin
            remote_commit <= 0;
            if (enabled) begin
                if (awaited_parent_v) begin
                    if (!authorized || (live && !accepted) || commit_slot ||
                        awaited_identity[44:39]<1 || awaited_identity[44:39]>36)
                        fault <= 1;
                    else if (!fault) begin
                        live <= 1;
                        accepted <= 0;
                        owner <= awaited_identity;
                        user <= awaited_user;
                    end
                end else if ((!authorized && live) || (commit_slot && (!port1_event || !record_ok))) begin
                    fault <= 1;
                end else if (commit_slot && !fault) begin
                    accepted <= 1;
                    remote_commit <= 1;
                    remote_identity <= owner;
                end
            end
        end
    end
endmodule
