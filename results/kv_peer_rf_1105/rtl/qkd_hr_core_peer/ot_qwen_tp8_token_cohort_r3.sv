`timescale 1ns/1ps
// DIE-KV-70 11-04 RE-FORM of ot_qwen_tp8_token_cohort_mu (same rules, begin_identity_ok replaces the tag compare).
//  Participant join +1 edge: req_v_q / req_bad_q hold the pulse and its registered check; active covers req_v_q.
//  terminal_matches registered from the head (terminal_check) one edge before presentation; see lifecycle_r3.
//  Face payload cohort_tag / generation / accepted_ranks / dispatched is registered.  dispatch_valid is same-edge combinational as
//  the source and asserts only when the registered payload shows the head cohort (us_q == ud), so a handshake always carries
//  the head's identity; first assertion +1 edge, dispatched +1 edge.  dispatch valid/ready is not staged.
module ot_qwen_tp8_token_cohort_r3 #(parameter integer MU = 1) (
    input wire clk, input wire por_n, input wire warm_ready,
    input wire begin_valid, output wire begin_ready, input wire begin_identity_ok,
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
    function automatic sel4(input[3:0]x,input[1:0]i);sel4=i[1]?(i[0]?x[3]:x[2]):(i[0]?x[1]:x[0]);endfunction
    reg [3:0] act, disp;
    reg [7:0] acc [0:3];
    reg [58:0] ctag [0:3];
    reg [1:0] cgen [0:3];
    reg [1:0] dq [0:3];
    reg [1:0] dw, dr; reg [2:0] dn;
    reg [1:0] shown, us_q;
    reg idf, tacc, terminal_consumed, matches_q, disp_r; reg [7:0] credit, acc_r, req_v_q, req_bad_q;
    reg [58:0] ctag_r; reg [1:0] cgen_r;
    integer r, k;
    wire [1:0] ub = begin_tag[44:43];
    wire [1:0] ut = terminal_tag[44:43];
    wire [1:0] ud = dq[dr];
    wire [1:0] us = (dn != 0) ? ud : shown;
    wire [58:0] expected_terminal = {ctag[ut][58:43], 6'd37, ctag[ut][36:0]};
    wire terminal_matches = sel4(act, ut) && terminal_tag == expected_terminal && terminal_generation == cgen[ut] &&
        (terminal_done || terminal_fault) && (terminal_fault || sel4(disp, ut));
    wire invalid_terminal = terminal_valid && !terminal_consumed && !matches_q;
    wire invalid_begin = begin_valid && !begin_identity_ok;
    wire act_d = sel4(act, ud);
    wire pop_dead = dn != 0 && !act_d;
    assign begin_ready = por_n && warm_ready && !sel4(act, ub) && !idf && begin_identity_ok &&
        !(terminal_valid && ut == ub) && dn != 3'd4;
    wire participant_fault = |(req_v_q & req_bad_q);
    wire [7:0] req_bad;
    for (genvar q = 0; q < 8; q = q + 1) begin : g_req
     wire [1:0] u = request_tag[59*q+43 +: 2];
     assign req_bad[q] = !warm_ready || !sel4(act, u) || acc[u][q] || request_tag[59*q +: 59] != ctag[u] ||
                         request_generation[2*q +: 2] != cgen[u];
    end
    assign dispatch_valid = dn != 0 && us_q == ud && act_d && (&acc_r) && !disp_r &&
        warm_ready && !idf;  // DIE-KV-73 r4: participant, terminal and begin faults stop dispatch through idf, +1 edge
    assign cohort_tag = ctag_r; assign cohort_generation = cgen_r; assign accepted_ranks = acc_r;
    assign dispatched = disp_r; assign active = (|act) || (|req_v_q); assign identity_fault = idf;
    assign terminal_accepted = tacc; assign request_credit = credit;
    always @(posedge clk) begin ctag_r <= ctag[us]; cgen_r <= cgen[us]; end
    always @(posedge clk or negedge por_n) begin
        if (!por_n) begin
            act <= 0; disp <= 0; idf <= 0; tacc <= 0; terminal_consumed <= 0; credit <= 0; matches_q <= 0;
            dw <= 0; dr <= 0; dn <= 0; shown <= 0; us_q <= 0; acc_r <= 0; disp_r <= 0; req_v_q <= 0; req_bad_q <= 0;
            for (k = 0; k < 4; k = k + 1) begin acc[k] <= 0; ctag[k] <= 0; cgen[k] <= 0; dq[k] <= 0; end
        end else begin
            credit <= 0; tacc <= 0;
            us_q <= us; acc_r <= acc[us]; disp_r <= sel4(disp, us);
            matches_q <= terminal_matches;
            req_v_q <= request_valid; req_bad_q <= req_bad;
            if (!terminal_valid) terminal_consumed <= 0;
            if (invalid_begin) idf <= 1;
            if (begin_valid && begin_ready) begin
                act[ub] <= 1; disp[ub] <= 0; acc[ub] <= 0; ctag[ub] <= begin_tag; cgen[ub] <= begin_generation;
                dq[dw] <= ub; dw <= dw + 1'b1;
            end
            if (participant_fault || invalid_terminal) idf <= 1;
            if (warm_ready && !idf && !participant_fault && !invalid_terminal)
                for (r = 0; r < 8; r = r + 1)
                    if (req_v_q[r]) begin
                        acc[request_tag[59*r+43 +: 2]][r] <= 1;
                        credit[r] <= 1;
                    end
            if (dispatch_valid && dispatch_ready) begin disp[ud] <= 1; shown <= ud; end
            if ((dispatch_valid && dispatch_ready) || pop_dead) dr <= dr + 1'b1;
            dn <= dn + 3'(begin_valid && begin_ready) - 3'((dispatch_valid && dispatch_ready) || pop_dead);
            if (terminal_valid && !terminal_consumed && matches_q) begin
                act[ut] <= 0; acc[ut] <= 0; disp[ut] <= 0; tacc <= 1; terminal_consumed <= 1;
            end
            if (recovery_valid) begin
                if (act == 0 && !begin_valid && !terminal_valid && !terminal_consumed && !(|request_valid) && !(|req_v_q) &&
                    kv_drained && vm_drained && collective_drained && host_drained && links_drained &&
                    link_reset_seen && retraining_done)
                    idf <= 0;
                else idf <= 1;
            end
        end
    end
endmodule
