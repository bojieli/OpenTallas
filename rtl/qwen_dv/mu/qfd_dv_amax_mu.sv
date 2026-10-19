`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_amax_mu -- the Q-DV slice's LM-head running argmax (qfd_dv_slice2 lines "LM-head running argmax"), cut out
// as one block with an OPT-IN per-user mode for the Qwen ROM 4-user static calendar (MU-QWEN item R4, 2026-10-19).
//
// NU = 1 (default): today's logic, statement for statement (same tree, same running best, same clear / emit, same
//   emit-empty fault term).  tb_amax_mu.sv proves it cycle-equal to a verbatim copy of the qfd_dv_slice2 block.
// NU = 2..4: the static calendar runs a filler user's 3,048-cycle LM head as row chunks interleaved with the other
//   users' ops (the latency user's tile-field gaps are all shorter than the head).  Every chunk is an STN op armed
//   with amax; its station results carry the op's user down the 4-level compare tree (au0..au4, one user per edge,
//   all 16 leaves of an edge are one op), and merge into THAT user's running best run[u].  The merge is today's
//   amb rule: larger okey wins, equal keys -> the lower index.  Because the index is part of the rule, the running
//   best over any chunk sequence equals the single-shot argmax over the union (ties -> the lowest index, as today);
//   in row order this is exactly "strictly greater wins, earlier chunk keeps a tie".
//   AMAX (kind 6) [4] clear / [5] emit act on the user in the AMAX command's user field; emit presents run[user].
//   Static schedule: no credits, no stall.  Schedule violations are STICKY faults (the compiler must make them
//   impossible): a clear for a user whose head is open, an amax result for a user whose head is not open, an emit
//   for a user whose head is not open, a clear on the edge a result of the same user merges (it would be dropped).
// Command fields (opt-in, NU > 1; spare bits today): STN (kind 2) user = cmd[52:51]; AMAX (kind 6) user = cmd[9:8].
// MUT (bench only, NU > 1 only): 1 the run merge takes a tie for the LATER chunk (okey >=, no index rule);
//   2 results merge into the user of the CURRENT STN register instead of the user carried down the tree;
//   3 an AMAX clear clears every user;  4 emit selects the current STN user instead of the AMAX command's user;
//   5 the STN-overlap fault (below) is dropped.
// am_u (MU-QW-AMIX 10-19): the user of the emitted candidate (the AMAX emit's cmd[9:8]); qfd_dv_scalar2 carries it to
//   the root in the AMI / AMV tag and faults a merge that holds two users' candidates.  NU = 1: constant 0.
// STN overlap (MU-ADOPT-SLICE 10-19, F-TOK-1 / blocker B2 of MU-ADOPT-TOK): results are gated and attributed by the
//   CURRENT STN register (amax bit, user), as in today's slice; an STN of ANY user issued while the previous op's
//   station results are still pending (stn_pend) would silently drop or misattribute them (and the slice's r_addr
//   base moves with it).  NU > 1: such an STN is a sticky mu_fault when either op is amax-armed (static schedule:
//   fault, never stall; the compiler reserves the station from an amax STN's issue to its last result).
// =====================================================================================================================
module qfd_dv_amax_mu #(
    parameter integer NU  = 1,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst,           // the slice's synchronised reset (active low)
    input  wire          c_stn,         // STN command on its issue edge
    input  wire          stn_amax_bit,  // cmd[50]
    input  wire [1:0]    stn_user,      // cmd[52:51] (NU > 1)
    input  wire          stn_pend,      // station results of the previous STN still pending on this edge (slice stn_left)
    input  wire          r_v,           // station result word
    input  wire [23:0]   r_addr,
    input  wire [511:0]  r_d,
    input  wire          c_am,          // AMAX command on its issue edge
    input  wire          am_clr,        // cmd[4]
    input  wire          am_emit_cmd,   // cmd[5]
    input  wire [1:0]    am_user,       // cmd[9:8] (NU > 1)
    output wire          am_v,
    output wire [23:0]   am_idx,
    output wire [31:0]   am_val,
    output wire [1:0]    am_u,          // user of the emitted candidate (MU-QW-AMIX: carried to the root; 0 for NU = 1)
    output wire          emit_empty,    // today's port_fault term (am_emit && !am_run[56])
    output wire          mu_fault       // sticky schedule fault (NU > 1); 0 for NU = 1
);
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    function automatic [56:0] amb(input [56:0] a, input [56:0] b);   // {valid, idx 24, value 32}
        amb = (a[56] && (!b[56] || okey(a[31:0]) > okey(b[31:0]) ||
               (okey(a[31:0]) == okey(b[31:0]) && a[55:32] < b[55:32]))) ? a : b;
    endfunction
    reg stn_amax;
    always @(posedge ck or negedge rst) if (!rst) stn_amax <= 1'b0; else if (c_stn) stn_amax <= stn_amax_bit;
    reg [16*57-1:0] al0;
    reg [8*57-1:0]  al1;
    reg [4*57-1:0]  al2;
    reg [2*57-1:0]  al3;
    reg [56:0]      al4;
    integer q;
    always @(posedge ck or negedge rst)
        if (!rst) begin al0 <= 0; al1 <= 0; al2 <= 0; al3 <= 0; al4 <= 0; end
        else begin
            for (q = 0; q < 16; q = q + 1)
                al0[57*q +: 57] <= {r_v && stn_amax, r_addr + 24'(q), r_d[32*q +: 32]};
            for (q = 0; q < 8; q = q + 1) al1[57*q +: 57] <= amb(al0[57*(2*q) +: 57], al0[57*(2*q+1) +: 57]);
            for (q = 0; q < 4; q = q + 1) al2[57*q +: 57] <= amb(al1[57*(2*q) +: 57], al1[57*(2*q+1) +: 57]);
            for (q = 0; q < 2; q = q + 1) al3[57*q +: 57] <= amb(al2[57*(2*q) +: 57], al2[57*(2*q+1) +: 57]);
            al4 <= amb(al3[56:0], al3[113:57]);
        end
    reg am_emit;
    always @(posedge ck or negedge rst) if (!rst) am_emit <= 1'b0; else am_emit <= c_am && am_emit_cmd;

    generate if (NU == 1) begin : g_one
        // ---------------------------------------------------------------- today (qfd_dv_slice2), unchanged
        reg [56:0] am_run;
        always @(posedge ck or negedge rst)
            if (!rst) am_run <= 0;
            else if (c_am && am_clr) am_run <= 57'd0;
            else am_run <= amb(am_run, al4);
        assign am_v = am_emit && am_run[56];
        assign am_idx = am_run[55:32];
        assign am_val = am_run[31:0];
        assign emit_empty = am_emit && !am_run[56];
        assign mu_fault = 1'b0;
        assign am_u = 2'd0;
    end else begin : g_mu
        // ---------------------------------------------------------------- per-user running best (opt-in)
        reg [1:0] stn_u, au0, au1, au2, au3, au4, am_eu;
        reg [56:0] run [0:NU-1];
        reg [NU-1:0] open;
        reg fault_q;
        integer u;
        always @(posedge ck or negedge rst)
            if (!rst) begin stn_u <= 2'd0; au0 <= 2'd0; au1 <= 2'd0; au2 <= 2'd0; au3 <= 2'd0; au4 <= 2'd0; end
            else begin
                if (c_stn) stn_u <= stn_user;
                au0 <= stn_u; au1 <= au0; au2 <= au1; au3 <= au2; au4 <= au3;
            end
        wire [1:0] mu = (MUT == 2) ? stn_u : au4;                       // the merging result's user
        wire       clr = c_am && am_clr;
        always @(posedge ck or negedge rst)
            if (!rst) begin
                for (u = 0; u < NU; u = u + 1) run[u] <= 57'd0;
                open <= {NU{1'b0}}; am_eu <= 2'd0; fault_q <= 1'b0;
            end else begin
                if (c_am && am_emit_cmd) am_eu <= (MUT == 4) ? stn_u : am_user;
                for (u = 0; u < NU; u = u + 1) begin
                    if (clr && (am_user == u[1:0] || MUT == 3)) run[u] <= 57'd0;
                    else if (al4[56] && mu == u[1:0])
                        run[u] <= (MUT == 1) ? ((!run[u][56] || okey(al4[31:0]) >= okey(run[u][31:0])) ? al4 : run[u])
                                             : amb(run[u], al4);
                end
                if (clr) open[am_user] <= 1'b1;
                if (am_emit) open[am_eu] <= 1'b0;
                if ((clr && (am_user >= NU || open[am_user])) ||
                    (al4[56] && (au4 >= NU || !open[au4])) ||
                    (c_am && am_emit_cmd && (am_user >= NU || !open[am_user])) ||
                    (clr && al4[56] && au4 == am_user) ||
                    (c_stn && stn_amax_bit && stn_user >= NU) ||
                    (MUT != 5 && c_stn && stn_pend && (stn_amax || stn_amax_bit)))
                    fault_q <= 1'b1;
            end
        wire [56:0] sel = run[am_eu];
        assign am_v = am_emit && sel[56];
        assign am_idx = sel[55:32];
        assign am_val = sel[31:0];
        assign emit_empty = am_emit && !sel[56];
        assign mu_fault = fault_q;
        assign am_u = am_eu;
    end endgenerate
    initial if (NU < 1 || NU > 4) $fatal(1, "qfd_dv_amax_mu: NU %0d outside 1..4", NU);
    initial if (MUT < 0 || MUT > 5) $fatal(1, "qfd_dv_amax_mu: MUT %0d undefined", MUT);
endmodule
