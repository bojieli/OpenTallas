`timescale 1ns/1ps
// =====================================================================================================================
// qfd_sys_face_mu_user -- OPT-IN user index for the compute-die system face's token calendar (MU-QWEN item R3,
// 2026-10-19).  Qwen ROM 4-user static calendar: every stage start (dh h_start / stage), MARK and RESULT capture must
// name its user, i.e. +2 bits on the T calendar event.  The event is {port3 = class, kind4|beat5 = arg9} and all 9
// arg bits are in use by class 0 STAGE (stage 6, L start, token run, RESULT), so the user cannot ride in the STAGE arg.
//
// Chosen encoding: a USER prefix event, class 7 on the T calendar (class 7 = FILL is an E-calendar class; on T every
// class >= 2 except 5 faults today, so class 7 on T is free).  arg[1:0] = user, arg[8:2] must be 0.  It latches
// cur_user on its edge; every later T event (STAGE / MARK / RESULT / LEVEL / END) belongs to cur_user until the next
// USER event.  The compiler emits USER only where the user changes, so a period with u user switches costs u T entries.
// Why not elsewhere:
//   * widening the calendar entry (ot_qwen_d2d_cal, the Q-LINK calendar RTL) changes the engine shared with the
//     static D2D ends (qfd_d2d_static / qkd_d2d_static, closed link tiles) -- a wider ROM/cfg word for 2 bits;
//   * splitting STAGE's arg (stage 6 bits has 37 stages + LAST_STAGE in use) leaves no 2 spare bits;
//   * deriving the user from the token number needs the per-user token bank (R2) BEFORE the stage starts it selects.
// NU = 1 (default): t_user_ev = t_user_bad = 0 and cur_user = 0 constant, so the face's decode is today's exactly.
// MUT (bench only): 1 cur_user takes effect one edge late; 2 the reserved-bit / range check is dropped;
//                   3 class 7 is accepted as USER even when NU = 1 (breaks the default identity).
// =====================================================================================================================
module qfd_sys_face_mu_user #(
    parameter integer NU  = 1,
    parameter integer MUT = 0
) (
    input  wire       ck,
    input  wire       rst_n,
    input  wire       te,          // the face's T event (after its own MUT-1 select): te / tp / ta
    input  wire [2:0] tp,
    input  wire [8:0] ta,
    output wire       t_user_ev,   // a USER event on this edge: exempt it from t_bad's class check
    output wire       t_user_bad,  // a USER event with a reserved bit set or a user >= NU: OR into t_bad
    output wire [1:0] ev_user      // the user every non-USER T event of this edge belongs to
);
    wire on = (NU > 1) || (MUT == 3);
    assign t_user_ev  = on && te && tp == 3'd7;
    assign t_user_bad = t_user_ev && (MUT != 2) && (ta[8:2] != 7'd0 || {1'b0, ta[1:0]} >= 3'(NU));
    reg [1:0] cur, cur_d;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin cur <= 2'd0; cur_d <= 2'd0; end
        else begin
            if (t_user_ev && NU > 1) cur <= ta[1:0];
            cur_d <= cur;
        end
    assign ev_user = (NU == 1) ? 2'd0 : (MUT == 1) ? cur_d : cur;
    initial if (NU < 1 || NU > 4) $fatal(1, "qfd_sys_face_mu_user: NU %0d outside 1..4", NU);
    initial if (MUT < 0 || MUT > 3) $fatal(1, "qfd_sys_face_mu_user: MUT %0d undefined", MUT);
endmodule
