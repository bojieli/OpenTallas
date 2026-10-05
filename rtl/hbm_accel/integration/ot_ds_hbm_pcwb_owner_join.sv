`timescale 1ps/1fs
// Proposed thin held-source join (Claude design, 2026-10-05) between the ACTUAL DS HA issuer, one die's
// ot_ds_hbm_cmdproc20 (doorbell accepted edge db_v && db_rdy, clk_sm), and the PCWB service parent's owner
// frame (service_clk).  It invents no identity: the held fields are the issuer's existing registers
// (job_q -> cpl_job[31:0], generation_q -> cpl_generation[3:0], launch_pos -> cpl_position[19:0]), the
// physical rank is the cluster's die index (g_die[d], die_id[7:0] of the die's SMs, ND <= 128) and the stack
// is the PCWB instance's STACK parameter (compare only).  ENABLE = 0: pass-through, no gating.
//  * accept:  acc = db_v && db_rdy_eff (clk_sm).  The issuer latches job/generation on this edge; launch_pos
//             on the same edge (S_IDLE, legal position).  The fields are stable from acc+1 until the next acc.
//  * hold:    db_rdy_eff = db_rdy && !pend: a new step is NOT accepted until the parent has bound AND released
//             (fenced: all queued + issued + PHY-accepted + visibility-returned debt drained) the previous frame.
//  * cross:   a request toggle (clk_sm -> service_clk, 2-flop) while the fields are stable; the parent's
//             owner_v is the synchronised toggle edge; the ack toggle returns at frame release (bound && fenced).
//  * rows:    row_v && row_r and desc_v && desc_r are admitted only while the frame is held (the parent's
//             `active`); each accepted row must carry pos == held position and die == held rank, otherwise
//             assoc_fault (fail closed).  Descriptors are bound by window (held frame, before the next accept).
// Caller must gate CP db_v with the ALL-stack permission, not only host db_rdy.
// Actual CP cpl_v latches issuer_done; release also requires parent ALL-debt-drained owner_released.
// acc_q closes the accept-to-toggle edge; assoc_fault stops further admission.
module ot_ds_hbm_pcwb_owner_join #(
    parameter integer ENABLE = 0, parameter integer DIE = 0, parameter integer STACK = 0
) (
    input  wire        clk_sm, rst_sm_n, service_clk, por_n,
    // issuer side (one die's u_cp)
    input  wire        db_v, db_rdy, issuer_done,
    output wire        db_rdy_eff,             // drive the cluster's db_rdy[d] / u_cp gating with this
    input  wire [31:0] cpl_job,
    input  wire [3:0]  cpl_generation,
    input  wire [19:0] cpl_position,
    // parent owner side (service_clk)
    output wire        owner_v,
    input  wire        owner_r,
    input  wire        owner_held, owner_fenced,    // parent frame_q[2] / frame_q[1]
    output reg  [31:0] o_job, output reg [3:0] o_gen, output reg [19:0] o_pos,
    output wire [6:0]  o_rank, output wire [1:0] o_stack,
    // row association check (service_clk), on the parent's row/descriptor ports
    input  wire        row_acc,                 // row_v && row_r at the parent
    input  wire [6:0]  row_die, input wire [19:0] row_pos,
    output reg         assoc_fault,
    output wire        source_window_owned
);
    assign o_rank = 7'(DIE); assign o_stack = 2'(STACK);
    generate if (!ENABLE) begin : off
        assign db_rdy_eff = db_rdy; assign owner_v = 1'b0; assign source_window_owned = 1'b0;
        always @* begin o_job = 0; o_gen = 0; o_pos = 0; assoc_fault = 1'b0; end
    end else begin : on
        reg step_done, acc_q, req_t, ack_s1, ack_s2;              // clk_sm
        reg done_s1, done_s2, req_s1, req_s2, req_s3, ack_t, want, bound; // service_clk
        // the ack toggle returns only when the parent has RELEASED the frame (bound and fenced = all debt
        // drained), so "pend" spans the whole hold and no level synchroniser can race it
        wire pend = (req_t != ack_s2);
        assign db_rdy_eff = db_rdy && !pend && !acc_q && !assoc_fault;
        always @(posedge clk_sm or negedge rst_sm_n)
            if (!rst_sm_n) begin step_done <= 0; acc_q <= 0; req_t <= 0; ack_s1 <= 0; ack_s2 <= 0; end
            else begin
                if (db_v && db_rdy_eff) step_done <= 0;
                else if (issuer_done) step_done <= 1;
                acc_q <= db_v && db_rdy_eff;            // fields (job_q, generation_q, launch_pos) stable from here
                if (acc_q) req_t <= ~req_t;
                ack_s1 <= ack_t; ack_s2 <= ack_s1;
            end
        always @(posedge service_clk or negedge por_n)
            if (!por_n) begin done_s1 <= 0; done_s2 <= 0; req_s1 <= 0; req_s2 <= 0; req_s3 <= 0; ack_t <= 0; want <= 0; bound <= 0;
                              o_job <= 0; o_gen <= 0; o_pos <= 0; assoc_fault <= 0; end
            else begin
                done_s1 <= step_done; done_s2 <= done_s1;
                req_s1 <= req_t; req_s2 <= req_s1; req_s3 <= req_s2;
                if (req_s2 != req_s3) begin want <= 1'b1; o_job <= cpl_job; o_gen <= cpl_generation; o_pos <= cpl_position; end
                else if (want && owner_r) begin want <= 1'b0; bound <= 1'b1; end
                else if (bound && done_s2 && owner_held && owner_fenced && !assoc_fault) begin bound <= 1'b0; ack_t <= ~ack_t; end
                if (row_acc && (row_pos != o_pos || row_die != 7'(DIE))) assoc_fault <= 1'b1;   // sticky
            end
        assign owner_v = want && !assoc_fault;
        // Admission window closes at release; stale parent-held context cannot admit the next frame.
        assign source_window_owned = bound && !assoc_fault;
    end endgenerate
endmodule
