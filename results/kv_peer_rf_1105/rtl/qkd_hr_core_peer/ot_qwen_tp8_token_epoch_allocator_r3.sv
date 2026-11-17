`timescale 1ns/1ps
// DIE-KV-70 11-04 RE-FORM of ot_qwen_tp8_token_epoch_allocator_mu (same rules).  terminal_identity_ok registered from the
// head one edge before presentation (see lifecycle_r3); invalid_terminal is then shallow.  g_id_ok: the granted token's range
// check, registered with the grant, replaces the compare on grant_tag in the cohort.
// Request acceptance reads req_ok_q: the checks on the waiting request (user busy, POST pending through request_valid, range) register one edge
// ahead (+1 edge).  The request is held stable by the coordinator stage; ubusy rises only on this request's own acceptance and pp rises only
// while terminal_consumed masks it, so a registered PASS still holds.
// Terminal acceptance needs only terminal_valid: lifecycle present_q holds the drain rule.
module ot_qwen_tp8_token_epoch_allocator_r3 #(
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
    output wire allocated_valid, output wire allocated_delivered, output reg g_id_ok, input wire grant_hold,
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
    function automatic sel4(input[3:0]x,input[1:0]i);sel4=i[1]?(i[0]?x[3]:x[2]):(i[0]?x[1]:x[0]);endfunction
    reg [13:0] seq [0:3];
    reg [3:0]  ubusy, udeliv;
    reg [15:0] a_epoch [0:3];
    reg [17:0] a_token [0:3];
    reg [12:0] a_pos   [0:3];
    reg [1:0]  a_gen   [0:3];
    reg [15:0] g_epoch; reg [17:0] g_token, g_position; reg [1:0] g_generation; reg [1:0] g_user;
    reg grant_pending, terminal_consumed, wl, idf, tacc, identity_ok_q, req_ok_q;
    wire [1:0] ureq = request_position[17:16];
    wire [1:0] ut   = terminal_tag[44:43];
    wire [58:0] expected_terminal = {a_epoch[ut], 6'd37, a_token[ut], a_pos[ut], 6'd0};
    assign grant_epoch = g_epoch; assign grant_token = g_token; assign grant_position = g_position;
    assign grant_generation = g_generation;
    assign grant_tag = {g_epoch, 6'd0, g_token, g_position[12:0], 6'd0};
    assign busy = |ubusy;
    assign wrap_locked = wl; assign identity_fault = idf; assign terminal_accepted = tacc;
    assign allocated_valid = (|ubusy) || grant_pending;
    assign allocated_delivered = sel4(ubusy, g_user) && sel4(udeliv, g_user);
    wire terminal_identity_ok = sel4(ubusy, ut) && (sel4(udeliv, ut) || terminal_fault) &&
         terminal_tag == expected_terminal && terminal_generation == a_gen[ut] && (terminal_done || terminal_fault);
    wire invalid_terminal = terminal_valid && !terminal_consumed && !identity_ok_q;
    wire pos_ok = request_position[15:0] < 16'd8192;
    wire token_ok = request_token < 18'd151936;
    wire invalid_request = request_valid && (!pos_ok || !token_ok);
    assign grant_valid = grant_pending && !grant_hold && !idf && warm_ready;  // DIE-KV-73 r4: invalid terminal stops grant through idf, +1 edge
    assign request_ready = req_ok_q && warm_ready && !idf && !terminal_valid && !terminal_consumed && !grant_pending && !wl;
    wire drains = terminal_kv_drained && terminal_vm_drained && terminal_collective_drained && terminal_host_drained;
    integer k;
    always @(posedge clk or negedge por_n) begin
        if (!por_n) begin
            for (k = 0; k < 4; k = k + 1) begin
                seq[k] <= INITIAL_EPOCH[15:2]; a_epoch[k] <= 0; a_token[k] <= 0; a_pos[k] <= 0; a_gen[k] <= 0;
            end
            ubusy <= 0; udeliv <= 0; g_epoch <= 0; g_token <= 0; g_position <= 0; g_generation <= 0; g_user <= 0;
            grant_pending <= 0; terminal_consumed <= 0; wl <= 0; idf <= 0; tacc <= 0; identity_ok_q <= 0; req_ok_q <= 0; g_id_ok <= 1;
        end else begin
            tacc <= 0; identity_ok_q <= terminal_identity_ok;
            req_ok_q <= request_valid && !request_ready && !sel4(ubusy, ureq) && pos_ok && token_ok;
            if (!terminal_valid) terminal_consumed <= 0;
            if (invalid_request) idf <= 1;
            if (request_valid && request_ready) begin
                g_epoch <= {seq[ureq], ureq}; g_token <= request_token; g_position <= request_position;
                g_generation <= request_generation; g_user <= ureq; grant_pending <= 1; g_id_ok <= token_ok;
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
                if (!identity_ok_q) idf <= 1;
                else begin
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
endmodule
