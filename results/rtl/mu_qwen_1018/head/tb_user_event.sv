`timescale 1ns/1ps
// MU-QWEN-HEAD (R3) behavioural bench for qfd_sys_face_mu_user.  Verilator 5.050 --binary --timing.
// A random T calendar event stream (classes 0 STAGE, 1 LEVEL, 5 MARK, 7 USER and the illegal-on-T classes 2/3/4/6,
// random args, USER followed by STAGE on the very next edge included) drives
//   n1 = qfd_sys_face_mu_user #(.NU(1)): the face's class check WITH the adoption patch applied must equal
//        today's t_bad (qfd_sys_face.sv lines 383-384, copied verbatim below) on every edge -- default identity;
//   n4 = qfd_sys_face_mu_user #(.NU(4)): a USER event (class 7, arg[8:2] = 0) is legal and latches the user; one
//        with a reserved bit set faults; every other class faults exactly as today; every STAGE / MARK / LEVEL event
//        carries the user of the latest earlier USER event.
module tb_user_event;
    parameter integer MUT = 0;
    integer N = 200000, seed = 1;
    reg ck = 1'b0;
    always #1 ck = ~ck;
    reg rst_n = 1'b0;
    reg te = 0; reg [2:0] tp = 0; reg [8:0] ta = 0;
    wire e1, b1, e4, b4; wire [1:0] u1, u4;
    qfd_sys_face_mu_user #(.NU(1), .MUT((MUT == 3) ? 3 : 0)) n1 (.ck(ck), .rst_n(rst_n), .te(te), .tp(tp), .ta(ta),
        .t_user_ev(e1), .t_user_bad(b1), .ev_user(u1));
    qfd_sys_face_mu_user #(.NU(4), .MUT((MUT == 1 || MUT == 2) ? MUT : 0)) n4 (.ck(ck), .rst_n(rst_n), .te(te), .tp(tp), .ta(ta),
        .t_user_ev(e4), .t_user_bad(b4), .ev_user(u4));
    // today's class check (qfd_sys_face.sv 383-384, verbatim)
    wire t_bad = te && ((tp >= 3'd2 && tp != 3'd5) || ((tp == 3'd0 || tp == 3'd5) && ta[6] && ta[7]) ||
                        (tp == 3'd1 && ta[8:3] != 0) || (tp == 3'd5 && (ta[8] || ta[5:0] != 0 || !(ta[6] || ta[7]))));
    // the same check with the adoption patch (adopt_sys_face.patch) applied
    function automatic pbad(input ue, input ub);
        pbad = (te && ((tp >= 3'd2 && tp != 3'd5 && !ue) || ((tp == 3'd0 || tp == 3'd5) && ta[6] && ta[7]) ||
                       (tp == 3'd1 && ta[8:3] != 0) || (tp == 3'd5 && (ta[8] || ta[5:0] != 0 || !(ta[6] || ta[7]))))) || ub;
    endfunction
    integer i, err1 = 0, err4 = 0, users = 0, stages = 0, adj = 0, rsv = 0, c;
    reg [1:0] model; reg prev_user;
    initial begin
        if ($value$plusargs("seed=%d", seed)) ;
        void'($urandom(seed));
        model = 0; prev_user = 0;
        repeat (3) @(negedge ck); rst_n = 1;
        for (i = 0; i < N; i = i + 1) begin
            te = ($urandom % 10) < 7;
            c = $urandom % 10;
            tp = (c < 3) ? 3'd0 : (c == 3) ? 3'd1 : (c == 4) ? 3'd5 : (c < 8) ? 3'd7 : 3'($urandom % 4 + 2);
            ta = 9'($urandom);
            if (tp == 3'd7 && ($urandom % 5) != 0) ta[8:2] = 7'd0;
            if (prev_user && ($urandom % 2)) begin te = 1; tp = 3'd0; end        // STAGE right behind a USER event
            #0.5;
            // ---- default identity: patched check == today's check, no user state
            if (pbad(e1, b1) !== t_bad || u1 !== 2'd0) begin
                err1 = err1 + 1;
                if (err1 <= 5) $display("NU1 MISMATCH edge %0d te %b tp %0d ta %h: today t_bad %b, patched %b (ue %b ub %b) user %0d", i, te, tp, ta, t_bad, pbad(e1, b1), e1, b1, u1);
            end
            // ---- NU = 4
            if (te && tp == 3'd7) begin
                users = users + 1;
                if (ta[8:2] != 0) rsv = rsv + 1;
                if (!(e4 === 1'b1 && b4 === (ta[8:2] != 0) && pbad(e4, b4) === (ta[8:2] != 0))) begin
                    err4 = err4 + 1;
                    if (err4 <= 5) $display("NU4 USER-EVENT MISMATCH edge %0d ta %h: ev %b bad %b", i, ta, e4, b4);
                end
            end else begin
                if (e4 !== 1'b0 || b4 !== 1'b0 || pbad(e4, b4) !== t_bad) begin
                    err4 = err4 + 1;
                    if (err4 <= 5) $display("NU4 CLASS MISMATCH edge %0d te %b tp %0d ta %h", i, te, tp, ta);
                end
                if (te && (tp == 3'd0 || tp == 3'd1 || tp == 3'd5)) begin
                    stages = stages + 1;
                    if (prev_user) adj = adj + 1;
                    if (u4 !== model) begin
                        err4 = err4 + 1;
                        if (err4 <= 5) $display("NU4 USER MISMATCH edge %0d class %0d: event user %0d, latest USER event %0d", i, tp, u4, model);
                    end
                end
            end
            prev_user = te && tp == 3'd7;
            if (te && tp == 3'd7) model = ta[1:0];
            @(negedge ck);
        end
        $display("edges %0d: USER events %0d (reserved-bit %0d), user-carrying events %0d (%0d right behind a USER event)", N, users, rsv, stages, adj);
        $display("NU1 identity mismatches %0d, NU4 mismatches %0d", err1, err4);
        if (err1 == 0 && err4 == 0 && users > 0 && adj > 0 && rsv > 0) $display("TB_USER_EVENT PASS MUT=%0d seed=%0d", MUT, seed);
        else $display("TB_USER_EVENT FAIL MUT=%0d seed=%0d", MUT, seed);
        $finish;
    end
endmodule
