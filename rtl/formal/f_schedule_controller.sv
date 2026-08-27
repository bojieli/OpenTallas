`timescale 1ns/1ps
module f_schedule_controller;
    (* gclk *) reg clk;
    reg rst_n = 1'b0;
    reg f_past_valid = 1'b0;
    (* anyseq *) reg shadow_wr_valid;
    (* anyseq *) reg [1:0] shadow_wr_slot;
    (* anyseq *) reg [3:0] shadow_wr_data;
    (* anyseq *) reg commit_req, quiescent, epoch_boundary, manifest_crc_ok;
    (* anyseq *) reg [7:0] commit_schedule_id;
    (* anyseq *) reg [1:0] active_slot;
    wire shadow_wr_ready, commit_ack, commit_error, schedule_valid;
    wire [7:0] epoch_id;
    wire [7:0] active_schedule_id;
    wire active_slot_valid, active_expect_valid, active_idle, commit_pending;
    wire [1:0] active_source_port;
    wire [31:0] active_schedule_crc;
    wire formal_active_bank, formal_pending, formal_shadow_complete;
    wire [7:0] formal_pending_schedule_id;

    ot_schedule_controller #(
        .PORTS(3), .SLOTS(3), .PORT_ID_W(2), .SLOT_W(2), .ENTRY_W(4)
    ) dut (
        .clk(clk), .rst_n(rst_n), .shadow_wr_valid(shadow_wr_valid),
        .shadow_wr_ready(shadow_wr_ready), .shadow_wr_slot(shadow_wr_slot),
        .shadow_wr_data(shadow_wr_data), .commit_req(commit_req),
        .quiescent(quiescent), .epoch_boundary(epoch_boundary),
        .manifest_crc_ok(manifest_crc_ok), .commit_schedule_id(commit_schedule_id),
        .commit_ack(commit_ack),
        .commit_error(commit_error), .schedule_valid(schedule_valid),
        .epoch_id(epoch_id), .active_schedule_id(active_schedule_id),
        .active_slot(active_slot),
        .active_slot_valid(active_slot_valid), .active_source_port(active_source_port),
        .active_expect_valid(active_expect_valid), .active_idle(active_idle),
        .active_schedule_crc(active_schedule_crc), .commit_pending(commit_pending),
        .formal_active_bank(formal_active_bank), .formal_pending(formal_pending),
        .formal_shadow_complete(formal_shadow_complete),
        .formal_pending_schedule_id(formal_pending_schedule_id)
    );

    always @(posedge clk) begin
        f_past_valid <= 1'b1;
        rst_n <= 1'b1;
        if (rst_n) begin
            assert(commit_pending == formal_pending);
            assert(shadow_wr_ready == !commit_pending);
            if (active_slot_valid) begin
                assert(schedule_valid);
                assert(active_slot < 3);
                assert(active_source_port < 3);
                assert(!active_idle);
            end
            if (f_past_valid && $past(rst_n)) begin
                if ($past(formal_pending && quiescent && epoch_boundary)) begin
                    assert(commit_ack);
                    assert(formal_active_bank != $past(formal_active_bank));
                    assert(epoch_id == $past(epoch_id) + 1'b1);
                    assert(active_schedule_id == $past(formal_pending_schedule_id));
                    assert(schedule_valid);
                end else begin
                    assert(!commit_ack);
                    assert(formal_active_bank == $past(formal_active_bank));
                    assert(epoch_id == $past(epoch_id));
                end
                if ($past(commit_req && !commit_pending &&
                          (!formal_shadow_complete || !manifest_crc_ok)))
                    assert(!commit_pending);
                if ($past((shadow_wr_valid && shadow_wr_ready &&
                           ((shadow_wr_slot >= 3) ||
                            (!shadow_wr_data[3] && (shadow_wr_data[1:0] >= 3)))) ||
                          (commit_req && !commit_pending &&
                           (!formal_shadow_complete || !manifest_crc_ok)))) begin
                    assert(commit_error);
                end else begin
                    assert(!commit_error);
                end
            end
            cover(commit_ack && schedule_valid);
            cover(commit_error);
            cover(active_slot_valid && active_expect_valid);
        end
    end
endmodule
