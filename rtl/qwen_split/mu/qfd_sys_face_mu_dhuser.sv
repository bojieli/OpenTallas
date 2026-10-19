`timescale 1ns/1ps
// =====================================================================================================================
// qfd_sys_face_mu_dhuser -- the user of every stage start on the compute die, WITHOUT touching the closed system face
// (MU-QWEN item R3, MU-ADOPT-SLICE 2026-10-19).  Supersedes, for adoption, the class-7 USER prefix event
// (qfd_sys_face_mu_user + adopt_sys_face.patch): that encoding has to change the closed qfd_sys_face (its T calendar
// and the class check t_bad live inside the face, so a class-7 T event faults there today).
//
// What it does: the face's T calendar is a static, periodic image, so the k-th stage start (seq_dh h_start) of every
// calendar period always belongs to the same user.  This leaf holds that compiled per-period list and names the user
// of each h_start on the same edge the h_start leaves the face:
//   dh_user = USER_SEQ[k] in the cycle seq_dh[42] (h_start) is high; it holds the last user between h_starts.
//   k counts the h_starts of the period, 0 .. NS-1, and wraps to 0 after NS-1 (NS = h_starts per period).
// The compiled list carries each entry's stage number too (STG_SEQ[k]); an h_start whose stage (seq_dh[41:36])
// differs from STG_SEQ[k] raises the sticky mu_fault: the two compiler images (the face's T calendar and this list)
// cannot drift apart unnoticed (the same rule as the face's own T-vs-D2D-sequencer check).  RES_SEQ[k] marks the
// h_start that carries the RESULT capture (STAGE arg[8]); res_user = that h_start's user, held.
// Static schedule: no handshake, no stall; it only observes seq_dh.  Zero added edges: dh_user is valid with the
// h_start it names (k is a register; the lookup is combinational from it).
// Placement: next to the consumer of seq_dh -- inside the qfd_tt_ctlm_dv cluster at its dh input (MU-ADOPT-CTLM, R1/R2),
// or at the die top beside qfd_sys_face; either way the closed qfd_sys_face view is untouched.
// seq_dh field map (qfd_sys_face.sv: seq_dh = {dh_prog, dh_run}; dh_run = {kv_write_drained, h_start, stage6,
// tp_token18, tp_pos18}): h_start = seq_dh[42], stage = seq_dh[41:36].
// NU = 1 (default): dh_user = res_user = 0, mu_fault = 0 (constants: today).
// MUT (bench only): 1 user of entry k+1 (off by one); 2 stage check dropped; 3 dh_user one edge late.
// =====================================================================================================================
module qfd_sys_face_mu_dhuser #(
    parameter integer NU = 1,
    parameter integer NS = 1,                      // h_starts per T calendar period (1..64)
    parameter [64*2-1:0] USER_SEQ = '0,            // entry k = bits [2k+1:2k]: user of the k-th h_start of the period
    parameter [64*6-1:0] STG_SEQ = '0,             // entry k = bits [6k+5:6k]: its stage number (alignment check)
    parameter [63:0]     RES_SEQ = '0,             // bit k: the k-th h_start carries the RESULT capture
    parameter integer MUT = 0
) (
    input  wire        ck,
    input  wire        rst_n,
    input  wire [43:0] dh_run,                     // seq_dh[43:0] (the face's dh_run)
    output wire [1:0]  dh_user,                    // user of the h_start on this edge (holds between h_starts)
    output wire [1:0]  res_user,                   // user of the latest RESULT h_start (holds)
    output wire        mu_fault                    // sticky: stage mismatch against the compiled list
);
    generate if (NU == 1) begin : g_one
        assign dh_user = 2'd0;
        assign res_user = 2'd0;
        assign mu_fault = 1'b0;
    end else begin : g_mu
        wire       hs = dh_run[42];
        wire [5:0] stg = dh_run[41:36];
        reg  [5:0] k;
        reg  [1:0] hold_u, res_q, late_u;
        reg        fault_q;
        wire [5:0] kk = (MUT == 1) ? ((k == 6'(NS - 1)) ? 6'd0 : k + 6'd1) : k;
        wire [1:0] u_k = USER_SEQ[2*kk +: 2];
        wire [5:0] s_k = STG_SEQ[6*k +: 6];
        always @(posedge ck or negedge rst_n)
            if (!rst_n) begin k <= 6'd0; hold_u <= 2'd0; res_q <= 2'd0; late_u <= 2'd0; fault_q <= 1'b0; end
            else begin
                late_u <= hs ? u_k : hold_u;
                if (hs) begin
                    k <= (k == 6'(NS - 1)) ? 6'd0 : k + 6'd1;
                    hold_u <= u_k;
                    if (RES_SEQ[k]) res_q <= u_k;
                    if (stg != s_k && MUT != 2) fault_q <= 1'b1;
                end
            end
        assign dh_user = (MUT == 3) ? late_u : hs ? u_k : hold_u;
        assign res_user = res_q;
        assign mu_fault = fault_q;
    end endgenerate
    integer q;
    initial begin
        if (NU < 1 || NU > 4) $fatal(1, "qfd_sys_face_mu_dhuser: NU %0d outside 1..4", NU);
        if (NS < 1 || NS > 64) $fatal(1, "qfd_sys_face_mu_dhuser: NS %0d outside 1..64", NS);
        if (MUT < 0 || MUT > 3) $fatal(1, "qfd_sys_face_mu_dhuser: MUT %0d undefined", MUT);
        for (q = 0; q < NS; q = q + 1)
            if (NU > 1 && USER_SEQ[2*q +: 2] >= NU) $fatal(1, "qfd_sys_face_mu_dhuser: entry %0d user >= NU", q);
    end
endmodule
