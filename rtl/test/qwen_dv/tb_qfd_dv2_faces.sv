`timescale 1ns/1ps
// Q-SLICE 10-17: face-variant chain bench. Die order W1 | W0 || E0 | E1 (W5 end = W1), wired face to face as the die
// writer does: W variants R0 (dn = master W), E variants MY (dn = master E faces the die W side).
//   cmd: W1.cmd_wi <- TB; W1.cmd_eo -> W0.cmd_wi; W0.cmd_eo -> E0.cmd_ei; E0.cmd_wo -> E1.cmd_ei
//   AR return: W1.r*_wi <- TB; W1.r*_eo -> W0.r*_wi; W0.r*_eo -> E0.r*_ei; E0.r*_wo -> E1.r*_ei
//   outbound / ag: E1.*_eo -> E0.*_wi; E0.*_eo -> W0.*_ei; W0.*_wo -> W1.*_ei; W1.*_wo = the W column (checked)
// Checks: SETID x4 -> ids 0..3 in ss; XC COLL to id 0 on W1.cc*_wo exactly; GATHER of 8 rank words -> every slice's
// ss token = rank 2's index (tie with rank 5 keeps the earlier rank); ag at the W column = 0 (no fault anywhere).
// MUT passes to every core (11: XC mode from bit 7 -> FAIL; 12: tie to the later rank -> FAIL).
module tb_qfd_dv2_faces;
    parameter integer MUT = 0;
    parameter integer MU_NU = 1;      // MU-ADOPT-SLICE: the faces' MU_NU (4: the 4-user LM-head argmax, user fields 0 here)
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    reg [115:0] cmd0 = 0;
    reg rv0 = 0, re0 = 0, rl0 = 0; reg [2:0] rr0 = 0; reg [511:0] rd0 = 0;
    wire [115:0] c1, c2, c3;
    wire r1v, r1e, r1l, r2v, r2e, r2l, r3v, r3e, r3l; wire [2:0] r1r, r2r, r3r; wire [511:0] r1d, r2d, r3d;
    wire [519:0] d1, d2, d3;
    wire [9:0] a1, a2, a3, aw;
    wire [106:0] s0, s1, s2, s3;
    wire ccv; wire ccm; wire [15:0] ccw; wire [31:0] cct;
    // outbound chain between slices (AR + DD); the W column end is open
    wire o3v, o3m, o3l, o2v, o2m, o2l, o1v, o1m, o1l; wire [31:0] o3t, o2t, o1t; wire [511:0] o3d, o2d, o1d;
    wire [547:0] q3, q2, q1;
    wire [1087:0] x0, x1, x2, x3, y0, y1, y2, y3; wire [47:0] u0, u1, u2, u3, v0, v1, v2, v3;
    qfd_dv_slice2_w #(.MUT(MUT), .MU_NU(MU_NU)) W1 (.ck(ck), .rst_n(rst_n), .cmd_wi(cmd0), .cmd_eo(c1), .hr_wi(453'd0), .hr_eo(),
        .st_wo(), .st_wi(1088'd0), .st_eo(x0), .st_ei(y0), .sc_wo(), .sc_wi(48'd0), .sc_eo(u0), .sc_ei(v0),
        .arv_wo(), .art_wo(), .arm_wo(), .arl_wo(), .ard_wo(), .dd_wo(),
        .arv_ei(o1v), .art_ei(o1t), .arm_ei(o1m), .arl_ei(o1l), .ard_ei(o1d), .dd_ei(q1),
        .rv_wi(rv0), .re_wi(re0), .rr_wi(rr0), .rl_wi(rl0), .rd_wi(rd0), .dr_wi(520'd0),
        .rv_eo(r1v), .re_eo(r1e), .rr_eo(r1r), .rl_eo(r1l), .rd_eo(r1d), .dr_eo(d1),
        .ag_wo(aw), .ag_ei(a1), .ss_wo(s0), .ccv_wo(ccv), .ccm_wo(ccm), .ccw_wo(ccw), .cct_wo(cct),
        .l9_wi(514'd0), .l9_eo(), .rs_n0(514'd0), .rs_n1(514'd0), .rs_s0(514'd0), .rs_s1(514'd0),
        .cw_n0(), .cw_n1(), .cw_n2(), .cw_n3(), .cw_s0(), .cw_s1(), .cw_s2(), .cw_s3());
    qfd_dv_slice2_w #(.MUT(MUT), .MU_NU(MU_NU)) W0 (.ck(ck), .rst_n(rst_n), .cmd_wi(c1), .cmd_eo(c2), .hr_wi(453'd0), .hr_eo(),
        .st_wo(y0), .st_wi(x0), .st_eo(x1), .st_ei(y1), .sc_wo(v0), .sc_wi(u0), .sc_eo(u1), .sc_ei(v1),
        .arv_wo(o1v), .art_wo(o1t), .arm_wo(o1m), .arl_wo(o1l), .ard_wo(o1d), .dd_wo(q1),
        .arv_ei(o2v), .art_ei(o2t), .arm_ei(o2m), .arl_ei(o2l), .ard_ei(o2d), .dd_ei(q2),
        .rv_wi(r1v), .re_wi(r1e), .rr_wi(r1r), .rl_wi(r1l), .rd_wi(r1d), .dr_wi(d1),
        .rv_eo(r2v), .re_eo(r2e), .rr_eo(r2r), .rl_eo(r2l), .rd_eo(r2d), .dr_eo(d2),
        .ag_wo(a1), .ag_ei(a2), .ss_wo(s1), .ccv_wo(), .ccm_wo(), .ccw_wo(), .cct_wo(),
        .l9_wi(514'd0), .l9_eo(), .rs_n0(514'd0), .rs_n1(514'd0), .rs_s0(514'd0), .rs_s1(514'd0),
        .cw_n0(), .cw_n1(), .cw_n2(), .cw_n3(), .cw_s0(), .cw_s1(), .cw_s2(), .cw_s3());
    qfd_dv_slice2_e #(.MUT(MUT), .MU_NU(MU_NU)) E0 (.ck(ck), .rst_n(rst_n), .cmd_ei(c2), .cmd_wo(c3), .hr_ei(453'd0), .hr_wo(),
        .st_eo(y1), .st_ei(x1), .st_wo(x2), .st_wi(y2), .sc_eo(v1), .sc_ei(u1), .sc_wo(u2), .sc_wi(v2),
        .arv_eo(o2v), .art_eo(o2t), .arm_eo(o2m), .arl_eo(o2l), .ard_eo(o2d), .dd_eo(q2),
        .arv_wi(o3v), .art_wi(o3t), .arm_wi(o3m), .arl_wi(o3l), .ard_wi(o3d), .dd_wi(q3),
        .rv_ei(r2v), .re_ei(r2e), .rr_ei(r2r), .rl_ei(r2l), .rd_ei(r2d), .dr_ei(d2),
        .rv_wo(r3v), .re_wo(r3e), .rr_wo(r3r), .rl_wo(r3l), .rd_wo(r3d), .dr_wo(d3),
        .ag_eo(a2), .ag_wi(a3), .ss_eo(s2), .ccv_eo(), .ccm_eo(), .ccw_eo(), .cct_eo(),
        .l9_wi(514'd0), .l9_eo(), .rs_n0(514'd0), .rs_n1(514'd0), .rs_s0(514'd0), .rs_s1(514'd0),
        .cw_n0(), .cw_n1(), .cw_n2(), .cw_n3(), .cw_s0(), .cw_s1(), .cw_s2(), .cw_s3());
    qfd_dv_slice2_e #(.MUT(MUT), .MU_NU(MU_NU)) E1 (.ck(ck), .rst_n(rst_n), .cmd_ei(c3), .cmd_wo(), .hr_ei(453'd0), .hr_wo(),
        .st_eo(y2), .st_ei(x2), .st_wo(), .st_wi(1088'd0), .sc_eo(v2), .sc_ei(u2), .sc_wo(), .sc_wi(48'd0),
        .arv_eo(o3v), .art_eo(o3t), .arm_eo(o3m), .arl_eo(o3l), .ard_eo(o3d), .dd_eo(q3),
        .arv_wi(1'b0), .art_wi(32'd0), .arm_wi(1'b0), .arl_wi(1'b0), .ard_wi(512'd0), .dd_wi(548'd0),
        .rv_ei(r3v), .re_ei(r3e), .rr_ei(r3r), .rl_ei(r3l), .rd_ei(r3d), .dr_ei(d3),
        .rv_wo(), .re_wo(), .rr_wo(), .rl_wo(), .rd_wo(), .dr_wo(),
        .ag_eo(a3), .ag_wi(10'd0), .ss_eo(s3), .ccv_eo(), .ccm_eo(), .ccw_eo(), .cct_eo(),
        .l9_wi(514'd0), .l9_eo(), .rs_n0(514'd0), .rs_n1(514'd0), .rs_s0(514'd0), .rs_s1(514'd0),
        .cw_n0(), .cw_n1(), .cw_n2(), .cw_n3(), .cw_s0(), .cw_s1(), .cw_s2(), .cw_s3());
    integer errs = 0, r, ncc = 0;
    reg [49:0] cc_got;
    reg [31:0] vals [0:7];
    function [115:0] cmd(input [3:0] dst, input [2:0] kind, input [107:0] f);
        cmd = {dst, f, kind, 1'b1};
    endfunction
    always @(posedge ck) if (ccv) begin ncc = ncc + 1; cc_got = {ccv, ccm, ccw, cct}; end
    initial begin
        vals[0] = 32'h3f800000; vals[1] = 32'hc0000000; vals[2] = 32'h42480000; vals[3] = 32'h40400000;
        vals[4] = 32'hbf800000; vals[5] = 32'h42480000; vals[6] = 32'hc2700000; vals[7] = 32'h41200000;
        repeat (4) @(negedge ck); rst_n = 1; repeat (4) @(negedge ck);
        cmd0 = {4'hF, 104'd0, 4'd0, 3'd7, 1'b1}; @(negedge ck); cmd0 = 0;          // SETID id 0
        repeat (20) @(negedge ck);
        cmd0 = cmd(4'd0, 3'd0, {53'd0, 32'hCAFEF00D, 16'hBEEE, 1'b1, 2'd0, 4'd0} >> 4); @(negedge ck); cmd0 = 0;
        repeat (10) @(negedge ck);
        cmd0 = cmd(4'hF, 3'd6, {100'd0, 1'b1, 3'd0, 4'd0} >> 4); @(negedge ck); cmd0 = 0;   // AMAX GATHER, all
        repeat (12) @(negedge ck);
        for (r = 0; r < 8; r = r + 1) begin
            rv0 = 1; rr0 = r[2:0]; rl0 = (r == 7); rd0 = {456'd0, 24'(1000 * r + 7), vals[r]};
            @(negedge ck);
        end
        rv0 = 0; rl0 = 0; rd0 = 0; rr0 = 0;
        repeat (20) @(negedge ck);
        if (s0[73:70] != 0 || s1[73:70] != 1 || s2[73:70] != 2 || s3[73:70] != 3) begin
            errs = errs + 1; $display("SETID ids %0d %0d %0d %0d", s0[73:70], s1[73:70], s2[73:70], s3[73:70]); end
        if (ncc != 1 || cc_got != {1'b1, 1'b1, 16'hBEEE, 32'hCAFEF00D}) begin
            errs = errs + 1; $display("XC cc count %0d word %h", ncc, cc_got); end
        if (s0[23:0] != 2007 || s1[23:0] != 2007 || s2[23:0] != 2007 || s3[23:0] != 2007) begin
            errs = errs + 1; $display("GATHER tokens %0d %0d %0d %0d (want 2007)", s0[23:0], s1[23:0], s2[23:0], s3[23:0]); end
        if (s0[105:74] != 32'h42480000 || s3[105:74] != 32'h42480000) begin
            errs = errs + 1; $display("GATHER values %h %h", s0[105:74], s3[105:74]); end
        if (aw != 10'd0 || s0[69] || s1[69] || s2[69] || s3[69]) begin
            errs = errs + 1; $display("faults: ag %b any %b%b%b%b", aw, s0[69], s1[69], s2[69], s3[69]); end
        $display("FACES MU_NU=%0d", MU_NU);
        if (errs == 0) $display("FACES MUT=%0d: PASS", MUT); else $display("FACES MUT=%0d: FAIL %0d", MUT, errs);
        $finish;
    end
endmodule
