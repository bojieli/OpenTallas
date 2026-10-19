`timescale 1ns/1ps
// MU-ADOPT-HROOT 10-19 (Qwen ROM 4 users): drop-in successor of ot_qwen_tp8_token_epoch_allocator (same ports).
//   MU 0: instantiates the unchanged original (behaviour-identical by construction; original file untouched).
//   MU 1: one outstanding allocation PER USER (4 in flight).  The user is the request position's [17:16] (the host step
//         carries it on hc pos[17:16], qkd_host_ctl MU); the range check is on the per-user position [15:0] < 8192.
//         Epoch = {seq14[user], user2} (MU-ADOPT-KV convention: the KV die reads the stage user from TAG epoch[1:0]);
//         each user has its own 14-bit sequence, so a user's epochs wrap after 16,384 steps (wrap_locked, then the
//         existing physical wrap fence clears every sequence, as the original's).  grant_* / grant_tag show the latest
//         grant (one grant handshake at a time, as the original).  A terminal is matched to the allocation of the user
//         in its TAG's epoch[1:0] with the full TAG59 + generation; a request for a user that still owns an allocation is
//         not ready (request_ready low, the host-boundary admission handshake of the original).  Faults stay sticky.
//   Drains: with one allocation outstanding a terminal waits for the four drains exactly as the original; with other
//         users in flight the die is never globally drained, so a matching terminal retires its own allocation (the
//         static calendar emits it after that step's last scheduled work; audit point, lanes/MU-QWEN-ADOPT.md ## HROOT).
module ot_qwen_tp8_token_epoch_allocator_mu #(
    parameter [15:0] INITIAL_EPOCH = 16'd0,
    parameter integer MU = 1
) (
    input wire clk, input wire por_n, input wire warm_ready,
    input wire request_valid, output wire request_ready,
    input wire [17:0] request_token, input wire [17:0] request_position,
    input wire [1:0] request_generation,
    output wire grant_valid, input wire grant_ready,
    output wire [15:0] grant_epoch, output wire [17:0] grant_token,
    output wire [17:0] grant_position, output wire [1:0] grant_generation,
    output wire [58:0] grant_tag,
    output wire allocated_valid, output wire allocated_delivered,
    input wire terminal_valid, input wire [58:0] terminal_tag,
    input wire [1:0] terminal_generation,
    input wire terminal_done, input wire terminal_fault, input wire terminal_kv_drained,
    input wire terminal_vm_drained, input wire terminal_collective_drained,
    input wire terminal_host_drained,
    input wire wrap_fence_valid, input wire wrap_links_drained,
    input wire wrap_link_reset_seen, input wire wrap_retraining_done,
    output wire busy, output wire wrap_locked, output wire identity_fault,
    output wire terminal_accepted
);
generate if (MU == 0) begin : g_plain
    ot_qwen_tp8_token_epoch_allocator #(.INITIAL_EPOCH(INITIAL_EPOCH)) u_plain (
        .clk(clk), .por_n(por_n), .warm_ready(warm_ready), .request_valid(request_valid), .request_ready(request_ready),
        .request_token(request_token), .request_position(request_position), .request_generation(request_generation),
        .grant_valid(grant_valid), .grant_ready(grant_ready), .grant_epoch(grant_epoch), .grant_token(grant_token),
        .grant_position(grant_position), .grant_generation(grant_generation), .grant_tag(grant_tag),
        .allocated_valid(allocated_valid), .allocated_delivered(allocated_delivered),
        .terminal_valid(terminal_valid), .terminal_tag(terminal_tag), .terminal_generation(terminal_generation),
        .terminal_done(terminal_done), .terminal_fault(terminal_fault), .terminal_kv_drained(terminal_kv_drained),
        .terminal_vm_drained(terminal_vm_drained), .terminal_collective_drained(terminal_collective_drained),
        .terminal_host_drained(terminal_host_drained), .wrap_fence_valid(wrap_fence_valid),
        .wrap_links_drained(wrap_links_drained), .wrap_link_reset_seen(wrap_link_reset_seen),
        .wrap_retraining_done(wrap_retraining_done), .busy(busy), .wrap_locked(wrap_locked),
        .identity_fault(identity_fault), .terminal_accepted(terminal_accepted));
end else begin : g_mu
    reg [13:0] seq [0:3];
    reg [3:0]  ubusy, udeliv;
    reg [15:0] a_epoch [0:3];
    reg [17:0] a_token [0:3];
    reg [12:0] a_pos   [0:3];
    reg [1:0]  a_gen   [0:3];
    reg [15:0] g_epoch; reg [17:0] g_token, g_position; reg [1:0] g_generation; reg [1:0] g_user;
    reg grant_pending, terminal_consumed, wl, idf, tacc;
    wire [1:0] ureq = request_position[17:16];
    wire [1:0] ut   = terminal_tag[44:43];
    wire [58:0] expected_terminal = {a_epoch[ut], 6'd37, a_token[ut], a_pos[ut], 6'd0};
    assign grant_epoch = g_epoch; assign grant_token = g_token; assign grant_position = g_position;
    assign grant_generation = g_generation;
    assign grant_tag = {g_epoch, 6'd0, g_token, g_position[12:0], 6'd0};
    assign busy = |ubusy;
    assign wrap_locked = wl; assign identity_fault = idf; assign terminal_accepted = tacc;
    assign allocated_valid = (|ubusy) || grant_pending;
    assign allocated_delivered = ubusy[g_user] && udeliv[g_user];
    wire terminal_identity_ok = ubusy[ut] && (udeliv[ut] || terminal_fault) &&
         terminal_tag == expected_terminal && terminal_generation == a_gen[ut] && (terminal_done || terminal_fault);
    wire invalid_terminal = terminal_valid && !terminal_consumed && !terminal_identity_ok;
    wire pos_ok = request_position[15:0] < 16'd8192;
    wire invalid_request = request_valid && (!pos_ok || request_token >= 18'd151936);
    assign grant_valid = grant_pending && !idf && !invalid_terminal && warm_ready;
    assign request_ready = por_n && warm_ready && !idf && !terminal_valid && !terminal_consumed &&
                           !ubusy[ureq] && !grant_pending && !wl && pos_ok && request_token < 18'd151936;
    wire drains = terminal_kv_drained && terminal_vm_drained && terminal_collective_drained && terminal_host_drained;
    wire alone = (ubusy & ~(4'd1 << ut)) == 4'd0;
    integer k;
    always @(posedge clk or negedge por_n) begin
        if (!por_n) begin
            for (k = 0; k < 4; k = k + 1) begin
                seq[k] <= INITIAL_EPOCH[15:2]; a_epoch[k] <= 0; a_token[k] <= 0; a_pos[k] <= 0; a_gen[k] <= 0;
            end
            ubusy <= 0; udeliv <= 0; g_epoch <= 0; g_token <= 0; g_position <= 0; g_generation <= 0; g_user <= 0;
            grant_pending <= 0; terminal_consumed <= 0; wl <= 0; idf <= 0; tacc <= 0;
        end else begin
            tacc <= 0;
            if (!terminal_valid) terminal_consumed <= 0;
            if (invalid_request) idf <= 1;
            if (request_valid && request_ready) begin
                g_epoch <= {seq[ureq], ureq}; g_token <= request_token; g_position <= request_position;
                g_generation <= request_generation; g_user <= ureq; grant_pending <= 1;
                ubusy[ureq] <= 1; udeliv[ureq] <= 0;
                a_epoch[ureq] <= {seq[ureq], ureq}; a_token[ureq] <= request_token;
                a_pos[ureq] <= request_position[12:0]; a_gen[ureq] <= request_generation;
                if (seq[ureq] == 14'h3fff) wl <= 1;
                else seq[ureq] <= seq[ureq] + 1'b1;
            end
            if (grant_valid && grant_ready && warm_ready) begin
                grant_pending <= 0; udeliv[g_user] <= 1;
            end
            if (terminal_valid && !terminal_consumed) begin
                if (!terminal_identity_ok) idf <= 1;
                else if (drains || !alone) begin
                    ubusy[ut] <= 0; terminal_consumed <= 1; tacc <= 1;
                    if (ut == g_user) grant_pending <= 0;
                end
            end
            if (wrap_fence_valid) begin
                if (!terminal_valid && !terminal_consumed && !invalid_request &&
                    !(|ubusy) && !grant_pending && (wl || idf) && drains && wrap_links_drained &&
                    wrap_link_reset_seen && wrap_retraining_done) begin
                    if (wl) begin for (k = 0; k < 4; k = k + 1) seq[k] <= 0; wl <= 0; end
                    idf <= 0;
                end else idf <= 1;
            end
        end
    end
end endgenerate
endmodule
