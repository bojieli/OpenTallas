`timescale 1ns/1ps
// tb_mtp_hrow (mtp-dsbind 2026-10-10): exact gate of the main-hidden row path to the DSpark primary die:
// 3 x ot_dsrom_mtp_hrow_tx (stage dies of layers 37 / 38 / 39) -> FWD / RET stations -> dsfd_mtp_hrow (row store) <-
// dsfd_mtp_seed_launch (seed client, descriptors from a grant-protocol sender through stations) -> E behavioural seed
// elements (seed_ctl intake protocol) joined at the die.
// Row data = a hash of {user, pos, issue epoch, part, beat}: a squashed row (old epoch) differs from its re-verified
// row, so serving the wrong version is a data mismatch.  Checks: every x beat equals the expected row version's beat,
// rows in order, program starts, final sticky faults (store + seedl) equal the case's expectation, beat count exact.
//   +CASE=pos_steady | pos_late | neg_drop
module tb_mtp_hrow;
    localparam integer NW = 21, UW = 10, SW = UW + 3 * NW + 4, PW = UW + 2 * NW + 4, AW = 24, HW = UW + NW + 6;
    localparam integer FWD = 9, RET = 9, PF = 9, PR = 9, QF = 6, QR = 6, XH = 4, E = 4;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [255:0] cs;
    function [1023:0] rowdata(input integer u, input integer pos, input integer ep, input integer part, input integer b);
        integer k; reg [31:0] h;
        begin
            for (k = 0; k < 32; k = k + 1) begin
                h = ({u[3:0], pos[11:0], ep[3:0], part[1:0], b[6:0], 5'(k)} * 32'h9E3779B1) ^ 32'h85EBCA6B;
                rowdata[32*k +: 32] = h ^ (h >> 13);
            end
        end
    endfunction
    // ---------------- scenario: rows (to the 3 part queues) and descriptors, in program order
    integer evk [0:255], evu [0:255], evp [0:255], eve [0:255], evd [0:255], eva [0:255], evn [0:255], evy [0:255];
    integer nev = 0, exp_sf = 0, exp_lf = 0;
    reg [4+UW+NW-1:0] rq_exp [0:4095]; reg [PW-1:0] eq [0:63];
    integer nr = 0, ne = 0, uep [0:15], ui;
    initial for (ui = 0; ui < 16; ui = ui + 1) uep[ui] = 0;
    task row(input integer u, input integer p, input integer ep, input integer dropmask);
        begin evk[nev] = 0; evu[nev] = u; evp[nev] = p; eve[nev] = ep; evd[nev] = dropmask; nev = nev + 1; end
    endtask
    task rows(input integer u, input integer p0, input integer p1, input integer ep);
        integer q; begin for (q = p0; q <= p1; q = q + 1) row(u, q, ep, 0); end
    endtask
    task desc(input integer u, input integer anc, input integer nrow, input integer y, input integer ep, input integer early,
              input integer good);
        integer q;
        begin
            evk[nev] = early ? 2 : 1; evu[nev] = u; eva[nev] = anc; evn[nev] = nrow; evy[nev] = y; eve[nev] = ep; nev = nev + 1;
            if (good) begin
                eq[ne] = {UW'(u), NW'(anc), NW'(y), 4'(ep)}; ne = ne + 1;
                for (q = anc - nrow + 1; q <= anc; q = q + 1) begin rq_exp[nr] = {4'(uep[u]), UW'(u), NW'(q)}; nr = nr + 1; end
                uep[u] = ep;
            end
        end
    endtask
    integer late_only_rows = 0;
    initial begin
        if (!$value$plusargs("CASE=%s", cs)) cs = "pos_steady";
        if (cs == "pos_steady" || cs == "pos_late") begin
            rows(0, 0, 2, 0); rows(1, 0, 1, 0);
            desc(0, 2, 3, 100, 0, 0, 1); desc(1, 1, 2, 200, 0, 0, 1);
            rows(0, 3, 8, 0);  rows(1, 2, 7, 0);                      // block of 6 issued under epoch 0
            desc(0, 5, 3, 101, 1, 0, 1);                              // user 0: a = 2, rejection -> epoch 1; 6..8 squashed
            desc(1, 7, 6, 201, 0, 0, 1);                              // user 1: all accepted
            if (cs == "pos_late") begin
                desc(0, 11, 6, 102, 1, 1, 1);                         // sent BEFORE the re-verified rows land
                rows(0, 6, 11, 1);                                    // re-issued under epoch 1 (6..8 overwrite)
            end else begin
                rows(0, 6, 11, 1);
                desc(0, 11, 6, 102, 1, 0, 1);
            end
            rows(1, 8, 13, 0); desc(1, 13, 6, 202, 0, 0, 1);
        end else if (cs == "neg_drop") begin
            rows(0, 0, 2, 0); desc(0, 2, 3, 100, 0, 0, 1);
            row(0, 3, 0, 0); row(0, 4, 0, 2);                        // row 4 part 1 LOST on its lane
            rows(0, 5, 8, 0);
            evk[nev] = 1; evu[nev] = 0; eva[nev] = 5; evn[nev] = 3; evy[nev] = 101; eve[nev] = 0; nev = nev + 1;
            eq[ne] = {UW'(0), NW'(5), NW'(101), 4'(0)};                  // (never completes: seed waits at row 4)
            rq_exp[nr] = {4'(0), UW'(0), NW'(3)}; nr = nr + 1;        // row 3 is served, row 4 must NOT be
            rows(0, 9, 20, 0);                                        // the ring wraps: pos 20 lands on row 4's slot
            exp_sf = 1;                                               // store fault[0] overrun
        end
    end
    // ---------------- part senders
    reg [HW-1:0] pq [0:2][0:255]; integer pqw [0:2], pqr [0:2]; integer pk;
    initial for (pk = 0; pk < 3; pk = pk + 1) begin pqw[pk] = 0; pqr[pk] = 0; end
    wire [2:0] hv, hr, bv, br; reg [2:0] sendh; reg [2:0] sendb; integer nbt [0:2];
    wire [514:0] link [0:2]; wire [514:0] link_far [0:2]; wire [2:0] g_far, g_near;
    genvar gp;
    generate for (gp = 0; gp < 3; gp = gp + 1) begin : g_tx
        reg [HW-1:0] cur; reg busy; integer nb;
        wire [HW-1:0] hd = cur;
        assign hv[gp] = busy && nb < 0;
        assign bv[gp] = busy && nb >= 0;
        wire [1023:0] bd = rowdata(cur[6+NW +: UW], cur[6 +: NW], cur[2 +: 4], gp, nb < 0 ? 0 : nb);
        always @(posedge clk) begin
            if (!rst_n) begin busy <= 0; nb <= -1; end
            else begin
                if (!busy && pqr[gp] < pqw[gp]) begin cur <= pq[gp][pqr[gp]]; pqr[gp] = pqr[gp] + 1; busy <= 1; nb <= -1; end
                if (hv[gp] && hr[gp]) nb <= 0;
                if (bv[gp] && br[gp]) begin if (nb == 79) busy <= 0; nb <= nb + 1; end
            end
        end
        wire lv; wire [513:0] ld;
        ot_dsrom_mtp_hrow_tx #(.NW(NW), .USER_W(UW)) u_tx (.clk(clk), .rst_n(rst_n), .h_v(hv[gp]), .h_r(hr[gp]),
            .h_d(hd), .b_v(bv[gp]), .b_r(br[gp]), .b_d(bd), .l_valid(lv), .l_ready(g_near[gp]), .l_data(ld));
        tb_hrow_relay #(.W(515), .HOPS(PF)) u_f (.clk(clk), .rst_n(rst_n), .i({ld, lv}), .o(link_far[gp]));
        tb_hrow_relay #(.W(1), .HOPS(PR)) u_g (.clk(clk), .rst_n(rst_n), .i(g_far[gp]), .o(g_near[gp]));
    end endgenerate
    // ---------------- descriptor sender
    reg [SW-1:0] dq [0:63]; integer dqw = 0, dqr = 0; wire s_r; wire lv_d; wire [SW-1:0] ld_d; wire gd_near;
    always @(posedge clk) if (rst_n && dqr < dqw && s_r) dqr <= dqr + 1;
    ot_dsrom_mtp_ltx #(.W(SW)) u_dtx (.clk(clk), .rst_n(rst_n), .c_valid(dqr < dqw), .c_ready(s_r), .c_data(dq[dqr]),
        .l_valid(lv_d), .l_ready(gd_near), .l_data(ld_d));
    wire [SW:0] f_mrs; wire t_mrs;
    tb_hrow_relay #(.W(SW + 1), .HOPS(FWD)) u_df (.clk(clk), .rst_n(rst_n), .i({ld_d, lv_d}), .o(f_mrs));
    tb_hrow_relay #(.W(1), .HOPS(RET)) u_dg (.clk(clk), .rst_n(rst_n), .i(t_mrs), .o(gd_near));
    // program order: rows go to the part queues at once; a descriptor waits until every earlier row has been sent
    // (it closes after its rows passed layer 39), except an 'early' one (the late re-verified rows case)
    integer ei, k2;
    initial begin
        wait (rst_n);
        repeat (20) @(posedge clk);
        for (ei = 0; ei < nev; ei = ei + 1) begin
            if (evk[ei] == 0) begin
                for (k2 = 0; k2 < 3; k2 = k2 + 1)
                    if (!evd[ei][k2]) begin
                        pq[k2][pqw[k2]] = {UW'(evu[ei]), NW'(evp[ei]), 4'(eve[ei]), 2'(k2)}; pqw[k2] = pqw[k2] + 1;
                    end
            end else begin
                if (evk[ei] == 1) begin
                    while (pqr[0] < pqw[0] || pqr[1] < pqw[1] || pqr[2] < pqw[2] || g_tx[0].busy || g_tx[1].busy || g_tx[2].busy)
                        @(posedge clk);
                    repeat (300) @(posedge clk);
                end
                if (evk[ei] == 2) while (starts != dqw) @(posedge clk);  // seedl idle: it reads the slots at once
                dq[dqw] = {UW'(evu[ei]), NW'(eva[ei]), NW'(evn[ei]), NW'(evy[ei]), 4'(eve[ei])}; dqw = dqw + 1;
                if (evk[ei] == 2) repeat (3000) @(posedge clk);       // the re-verified rows are this late
            end
        end
    end
    // ---------------- row store + seed client
    wire [AW:0] t_vrq, vrq_far; wire vg_far, vg_near; wire [1024:0] t_vrs, vrs_near; wire [2:0] st_flt;
    tb_hrow_relay #(.W(AW + 1), .HOPS(QF)) u_qf (.clk(clk), .rst_n(rst_n), .i(t_vrq), .o(vrq_far));
    tb_hrow_relay #(.W(1), .HOPS(QR)) u_qg (.clk(clk), .rst_n(rst_n), .i(vg_far), .o(vg_near));
    tb_hrow_relay #(.W(1025), .HOPS(QR)) u_qs (.clk(clk), .rst_n(rst_n), .i(t_vrs), .o(vrs_near));
    dsfd_mtp_hrow #(.NW(NW), .USER_W(UW), .AW(AW), .FWD_P(PF), .RET_P(PR), .FWD_Q(QF), .RET_Q(QR)) u_st (
        .ck(clk), .rst(rst_n), .f_hp0(link_far[0]), .f_hp1(link_far[1]), .f_hp2(link_far[2]), .t_hpg(g_far),
        .f_vrq(vrq_far), .t_vrq(vg_far), .t_vrs(t_vrs), .f_clr({UW'(0), 1'b0}), .t_flt(st_flt));
    wire [1024:0] t_x, x_far; wire [1:0] f_x; reg [1:0] x_join; wire [PW:0] t_ps; wire [3:0] l_flt;
    dsfd_mtp_seed_launch #(.NW(NW), .USER_W(UW), .VM_AW(AW), .FWD_C(FWD), .RET_C(RET)) u_sl (
        .ck(clk), .rst(rst_n), .f_mrs(f_mrs), .t_mrs(t_mrs), .f_clr({UW'(0), 1'b0}), .t_vrq(t_vrq), .f_vrq(vg_near),
        .f_vrs(vrs_near), .t_x(t_x), .f_x(f_x), .t_ps(t_ps), .t_flt(l_flt));
    // ---------------- seed elements
    integer errs = 0;
    tb_hrow_relay #(.W(1025), .HOPS(XH)) u_xf (.clk(clk), .rst_n(rst_n), .i(t_x), .o(x_far));
    tb_hrow_relay #(.W(2), .HOPS(XH)) u_xr (.clk(clk), .rst_n(rst_n), .i(x_join), .o(f_x));
    integer nin [0:E-1]; integer tproc [0:E-1]; reg idle [0:E-1]; reg rdy [0:E-1]; integer j, ndone, seed = 3; reg all_rdy;
    always @(posedge clk) begin
        if (!rst_n) begin
            for (j = 0; j < E; j = j + 1) begin nin[j] = 0; tproc[j] = 0; idle[j] = 1; rdy[j] <= 0; end
            ndone = 0; x_join <= 0;
        end else begin
            x_join[1] <= 1'b0;
            for (j = 0; j < E; j = j + 1) begin
                rdy[j] <= idle[j];
                if (x_far[0]) begin
                    if (nin[j] == 240) begin $display("HROW_ERR beat beyond 240"); errs = errs + 1; end
                    nin[j] = nin[j] + 1; idle[j] = 0;
                    if (nin[j] == 240) tproc[j] = 300 + 37 * j + ($random(seed) & 63);
                end else if (nin[j] == 240 && tproc[j] > 0) begin
                    tproc[j] = tproc[j] - 1;
                    if (tproc[j] == 0) begin nin[j] = 0; idle[j] = 1; ndone = ndone + 1; end
                end
            end
            if (ndone == E) begin x_join[1] <= 1'b1; ndone = 0; end
            all_rdy = 1; for (j = 0; j < E; j = j + 1) all_rdy = all_rdy & rdy[j];
            x_join[0] <= all_rdy;
        end
    end
    // ---------------- checker
    integer rws = 0, beat = 0, starts = 0, cyc = 0, beats = 0, t_last = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (rst_n && t_x[0]) begin
            beats = beats + 1; t_last = cyc;
            if (rws >= nr) begin if (errs < 5) $display("HROW_ERR unexpected beat (row %0d)", rws); errs = errs + 1; end
            else if (t_x[1024:1] !== rowdata(rq_exp[rws][UW+NW-1:NW], rq_exp[rws][NW-1:0], rq_exp[rws][4+UW+NW-1:UW+NW],
                                             beat / 80, beat % 80)) begin
                if (errs < 5) $display("HROW_ERR row %0d (u %0d pos %0d ep %0d) beat %0d mismatch", rws, rq_exp[rws][UW+NW-1:NW],
                                       rq_exp[rws][NW-1:0], rq_exp[rws][4+UW+NW-1:UW+NW], beat);
                errs = errs + 1;
            end
            beat = beat + 1;
            if (beat == 240) begin beat = 0; rws = rws + 1; end
        end
        if (rst_n && t_ps[0]) begin
            if (starts >= ne || t_ps[PW:1] !== eq[starts]) begin $display("HROW_ERR program start %0d", starts); errs = errs + 1; end
            starts = starts + 1;
        end
    end
    integer exp_starts;
    initial begin
        repeat (8) @(posedge clk);
        rst_n = 1;
        wait (dqw == dqr && dqw > 0 && ei == nev);
        while (cyc - t_last < 20000 && cyc < 3_000_000) @(posedge clk);
        exp_starts = (cs == "neg_drop") ? 1 : ne;
        if (beats != nr * 240) begin $display("HROW_ERR beats %0d expected %0d", beats, nr * 240); errs = errs + 1; end
        if (starts != exp_starts) begin $display("HROW_ERR starts %0d expected %0d", starts, exp_starts); errs = errs + 1; end
        if (st_flt !== 3'(exp_sf)) begin $display("HROW_ERR store fault %b expected %b", st_flt, 3'(exp_sf)); errs = errs + 1; end
        if (l_flt !== 4'(exp_lf)) begin $display("HROW_ERR seedl fault %b", l_flt); errs = errs + 1; end
        $display("HROW_RESULT case=%0s result=%s rows=%0d beats=%0d starts=%0d store_fault=%b seedl_fault=%b cyc=%0d",
                 cs, errs == 0 ? "PASS" : "FAIL", rws, beats, starts, st_flt, l_flt, cyc);
        $finish;
    end
endmodule

module tb_hrow_relay #(parameter integer W = 1, parameter integer HOPS = 0) (
    input wire clk, rst_n, input wire [W-1:0] i, output wire [W-1:0] o);
    generate if (HOPS == 0) begin : g0 assign o = i; end
    else begin : gp
        reg [W-1:0] p [0:HOPS-1]; integer j;
        always @(posedge clk) begin
            if (!rst_n) for (j = 0; j < HOPS; j = j + 1) p[j] <= '0;
            else begin p[0] <= i; for (j = 1; j < HOPS; j = j + 1) p[j] <= p[j-1]; end
        end
        assign o = p[HOPS-1];
    end endgenerate
endmodule
