`timescale 1ns/1ps
// TOKEN-R2 fork C: default-off kind11 commit-record path carrying the 91-bit {valid,identity61,address29} PCC bundle.
// K/HOST side: qkd_pc11_b1_kind11_tx. C safe7 side: qfd_pc11_b1_kind11_rx. enabled=0 is exactly pass-through of the host record
// path (tx_valid/tx_record = host, host_event = port1_event, no receipt, no fault). Single context only: mctx or a second
// parent_open while one is live and not yet accepted/sent faults. Record layout = stock kind11 record with the 29-bit
// commit address in the stock zero field bits [89:61]; the other 422 bits and the 5+5 lead/pad stay zero.
module qkd_pc11_b1_kind11_tx #(parameter integer TXDP=162) (
    input wire ck, rst_n, enabled, authorized, mctx,
    input wire parent_open, input wire [60:0] parent_identity, input wire [28:0] parent_address, input wire [1:0] parent_user,
    input wire pcc_commit, input wire [60:0] pcc_identity, input wire [28:0] pcc_address,
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
    reg [60:0] owner; reg [28:0] addr; reg [1:0] user;
    wire commit_slot = enabled && port1_slot && slot_kind==KIND;
    wire valid_slot = live && slot_beat==5'd0 && slot_user==user;
    wire take_commit = commit_slots[TXDP-1];
    wire [5:0] zb = owner[44:39]-6'd1;
    wire [547:0] rec = {5'd0,KIND,zb,owner[60:45],5'd0,{(451-89){1'b0}},addr,owner};
    assign commit_capture = take_commit && port1_capture && authorized && pending && !fault && !host_valid;
    assign tx_valid = take_commit ? commit_capture : host_valid;
    assign tx_record = take_commit ? rec : host_record;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin commit_slots<=0; live<=0; pending<=0; sent<=0; owner<=0; addr<=0; user<=0; fault<=0; end
        else if (enabled) begin
            commit_slots <= {commit_slots[TXDP-2:0],commit_slot && valid_slot && authorized && !fault};
            if (mctx) fault <= 1;
            if (parent_open) begin
                if (!authorized || (live && !sent) || pcc_commit || take_commit || parent_identity[44:39]<1 || parent_identity[44:39]>36) fault <= 1;
                else if (!fault) begin live<=1; pending<=0; sent<=0; owner<=parent_identity; addr<=parent_address; user<=parent_user; end
            end else if ((!authorized && live) || (commit_slot && !valid_slot) ||
                         (pcc_commit && (!live || pending || sent || pcc_identity!=owner || pcc_address!=addr)) ||
                         (take_commit && !commit_capture)) fault <= 1;
            else if (!fault) begin
                if (pcc_commit) pending <= 1;
                if (commit_capture) begin pending <= 0; sent <= 1; end
            end
        end
    end
endmodule

module qfd_pc11_b1_kind11_rx (
    input wire ck, rst_n, enabled, authorized, mctx,
    input wire awaited_parent_v, input wire [60:0] awaited_identity, input wire [28:0] awaited_address, input wire [1:0] awaited_user,
    input wire port1_slot, port1_event, input wire any_event, input wire [3:0] any_event_kind,
    input wire [3:0] slot_kind, input wire [4:0] slot_beat, input wire [1:0] slot_user,
    input wire [547:0] rx_record,
    output wire host_event,
    output reg b1_ready,            // level: held from the accepted receipt until the next awaited parent (service pcc_b1_ready)
    output reg [60:0] b1_identity,  // service pcc_b1_identity
    output reg [28:0] b1_address,
    output reg fault                // service pcc_b1_fault
);
    localparam [3:0] KIND=4'd11;
    reg live, accepted; reg [60:0] owner; reg [28:0] addr; reg [1:0] user;
    wire commit_slot = enabled && port1_slot && slot_kind==KIND;
    wire stray_kind = enabled && any_event && any_event_kind==KIND && !(port1_slot && port1_event);
    wire [5:0] zb = owner[44:39]-6'd1;
    wire record_ok = live && !accepted && slot_beat==0 && slot_user==user &&
        rx_record=={5'd0,KIND,zb,owner[60:45],5'd0,{(451-89){1'b0}},addr,owner};
    assign host_event = port1_event && !commit_slot;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin b1_ready<=0; b1_identity<=0; b1_address<=0; live<=0; accepted<=0; owner<=0; addr<=0; user<=0; fault<=0; end
        else if (enabled) begin
            if (mctx || stray_kind) fault <= 1;
            if (awaited_parent_v) begin
                if (!authorized || (live && !accepted) || commit_slot || awaited_identity[44:39]<1 || awaited_identity[44:39]>36) fault <= 1;
                else if (!fault) begin live<=1; accepted<=0; b1_ready<=0; owner<=awaited_identity; addr<=awaited_address; user<=awaited_user; end
            end else if ((!authorized && live) || (commit_slot && (!port1_event || !record_ok))) fault <= 1;
            else if (commit_slot && !fault) begin accepted<=1; b1_ready<=1; b1_identity<=owner; b1_address<=addr; end
        end
    end
endmodule
