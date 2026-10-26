`timescale 1ns/1ps
// MU-KV-PEER 10-19 (Qwen ROM 4 users): drop-in successor of ot_qwen_tp8_token_cohort (same ports).
//   MU 0: instantiates the unchanged original (behaviour-identical by construction; original file untouched).
//   MU 1: four cohorts, one per user.  The user is TAG epoch[1:0] (TAG59 bits [44:43]; allocator convention
//         epoch = {seq14[user], user2}).  A begin opens the cohort of its tag's user (a second begin for a user whose
//         cohort is still open is not ready -> the lifecycle's begin fault, as the original).  A participant request
//         joins the cohort of its tag's user; duplicate rank, wrong TAG59/generation or a closed cohort is a sticky
//         identity_fault (fail closed, as the original).  Cohorts dispatch in begin order (the oldest open,
//         not-yet-dispatched cohort, once all 8 ranks joined).  cohort_tag / cohort_generation / accepted_ranks /
//         dispatched show that cohort while one waits, else the last dispatched one.  active = any cohort open.
//   Terminal: matched to the cohort of the terminal tag's user (full TAG59 + generation + done/fault, dispatched
//         unless fault).  The caller (qkd_host_lifecycle_collected_mu) presents a terminal only when the allocator
//         accepts it on the same edge (all drains, or other users in flight), so MU 1 consumes a matching terminal
//         without its own drain check; both pulses therefore coincide.  Recovery as the original (all cohorts closed).
//   No ready/credit/stall added: request_credit is the original's per-rank acceptance pulse.
module ot_qwen_tp8_token_cohort_mu #(parameter integer MU = 1) (
    input wire clk, input wire por_n, input wire warm_ready,
    input wire begin_valid, output wire begin_ready,
    input wire [58:0] begin_tag, input wire [1:0] begin_generation,
    input wire [7:0] request_valid,
    input wire [471:0] request_tag, input wire [15:0] request_generation,
    output wire [7:0] request_credit,
    output wire dispatch_valid, input wire dispatch_ready,
    output wire [58:0] cohort_tag, output wire [1:0] cohort_generation,
    output wire [7:0] accepted_ranks, output wire active,
    output wire dispatched, output wire identity_fault,
    input wire terminal_valid, input wire [58:0] terminal_tag,
    input wire [1:0] terminal_generation, input wire terminal_done,
    input wire terminal_fault, input wire kv_drained, input wire vm_drained,
    input wire collective_drained, input wire host_drained,
    output wire terminal_accepted,
    input wire recovery_valid, input wire links_drained,
    input wire link_reset_seen, input wire retraining_done
);
generate if (MU == 0) begin : g_plain
    ot_qwen_tp8_token_cohort u_plain (
        .clk(clk), .por_n(por_n), .warm_ready(warm_ready), .begin_valid(begin_valid), .begin_ready(begin_ready),
        .begin_tag(begin_tag), .begin_generation(begin_generation), .request_valid(request_valid),
        .request_tag(request_tag), .request_generation(request_generation), .request_credit(request_credit),
        .dispatch_valid(dispatch_valid), .dispatch_ready(dispatch_ready), .cohort_tag(cohort_tag),
        .cohort_generation(cohort_generation), .accepted_ranks(accepted_ranks), .active(active),
        .dispatched(dispatched), .identity_fault(identity_fault), .terminal_valid(terminal_valid),
        .terminal_tag(terminal_tag), .terminal_generation(terminal_generation), .terminal_done(terminal_done),
        .terminal_fault(terminal_fault), .kv_drained(kv_drained), .vm_drained(vm_drained),
        .collective_drained(collective_drained), .host_drained(host_drained), .terminal_accepted(terminal_accepted),
        .recovery_valid(recovery_valid), .links_drained(links_drained), .link_reset_seen(link_reset_seen),
        .retraining_done(retraining_done));
end else begin : g_mu
    reg [3:0] act, disp;
    reg [7:0] acc [0:3];
    reg [58:0] ctag [0:3];
    reg [1:0] cgen [0:3];
    reg [1:0] dq [0:3];               // begin-order queue of users awaiting dispatch
    reg [1:0] dw, dr; reg [2:0] dn;
    reg [1:0] shown;                  // last dispatched user (shown when no cohort waits)
    reg idf, tacc, terminal_consumed; reg [7:0] credit;
    integer r, k;
    wire [1:0] ub = begin_tag[44:43];
    wire [1:0] ut = terminal_tag[44:43];
    wire [1:0] ud = dq[dr];
    wire [1:0] us = (dn != 0) ? ud : shown;
    wire begin_identity_ok = begin_tag[42:37] == 6'd0 && begin_tag[5:0] == 6'd0 && begin_tag[36:19] < 18'd151936;
    wire [58:0] expected_terminal = {ctag[ut][58:43], 6'd37, ctag[ut][36:0]};
    wire terminal_matches = act[ut] && terminal_tag == expected_terminal && terminal_generation == cgen[ut] &&
        (terminal_done || terminal_fault) && (terminal_fault || disp[ut]);
    wire invalid_terminal = terminal_valid && !terminal_consumed && !terminal_matches;
    wire invalid_begin = begin_valid && !begin_identity_ok;
    // a faulted (cancelled) cohort that never dispatched leaves the dispatch queue when it reaches the head
    wire pop_dead = dn != 0 && !act[ud];
    assign begin_ready = por_n && warm_ready && !act[ub] && !idf && begin_identity_ok &&
        !(terminal_valid && ut == ub) && dn != 3'd4;
    reg participant_fault;
    always @* begin
        participant_fault = 0;
        for (integer q = 0; q < 8; q = q + 1)
            if (request_valid[q] && (!warm_ready || !act[request_tag[59*q+43 +: 2]] ||
                acc[request_tag[59*q+43 +: 2]][q] ||
                request_tag[59*q +: 59] != ctag[request_tag[59*q+43 +: 2]] ||
                request_generation[2*q +: 2] != cgen[request_tag[59*q+43 +: 2]]))
                participant_fault = 1;
    end
    assign dispatch_valid = dn != 0 && act[ud] && (&acc[ud]) && !disp[ud] &&
        warm_ready && !idf && !participant_fault && !invalid_terminal && !invalid_begin;
    assign cohort_tag = ctag[us]; assign cohort_generation = cgen[us]; assign accepted_ranks = acc[us];
    assign dispatched = disp[us]; assign active = |act; assign identity_fault = idf;
    assign terminal_accepted = tacc; assign request_credit = credit;
    always @(posedge clk or negedge por_n) begin
        if (!por_n) begin
            act <= 0; disp <= 0; idf <= 0; tacc <= 0; terminal_consumed <= 0; credit <= 0;
            dw <= 0; dr <= 0; dn <= 0; shown <= 0;
            for (k = 0; k < 4; k = k + 1) begin acc[k] <= 0; ctag[k] <= 0; cgen[k] <= 0; dq[k] <= 0; end
        end else begin
            credit <= 0; tacc <= 0;
            if (!terminal_valid) terminal_consumed <= 0;
            if (invalid_begin) idf <= 1;
            if (begin_valid && begin_ready) begin
                act[ub] <= 1; disp[ub] <= 0; acc[ub] <= 0; ctag[ub] <= begin_tag; cgen[ub] <= begin_generation;
                dq[dw] <= ub; dw <= dw + 1'b1;
            end
            if (participant_fault || invalid_terminal) idf <= 1;
            if (warm_ready && !idf && !participant_fault && !invalid_terminal)
                for (r = 0; r < 8; r = r + 1)
                    if (request_valid[r]) begin
                        acc[request_tag[59*r+43 +: 2]][r] <= 1;
                        credit[r] <= 1;
                    end
            if (dispatch_valid && dispatch_ready) begin disp[ud] <= 1; shown <= ud; end
            if ((dispatch_valid && dispatch_ready) || pop_dead) dr <= dr + 1'b1;
            dn <= dn + 3'(begin_valid && begin_ready) - 3'((dispatch_valid && dispatch_ready) || pop_dead);
            if (terminal_valid && !terminal_consumed && terminal_matches) begin
                act[ut] <= 0; acc[ut] <= 0; disp[ut] <= 0; tacc <= 1; terminal_consumed <= 1;
            end
            if (recovery_valid) begin
                if (act == 0 && !begin_valid && !terminal_valid && !terminal_consumed && !(|request_valid) &&
                    kv_drained && vm_drained && collective_drained && host_drained && links_drained &&
                    link_reset_seen && retraining_done)
                    idf <= 0;
                else idf <= 1;
            end
        end
    end
end endgenerate
endmodule
