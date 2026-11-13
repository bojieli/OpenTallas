`timescale 1ns/1ps
// tb_dsdv_mu_hwin_la (HARD-S81-SERDES-1 2026-11-13): lock-step of dsdv_mu_hwin LA=LAN (lookahead compares) against LA=0 on the
// same pins, every edge, all outputs (mu_c, mu_rc, t_wf).  Constrained-random epochs: async reset, gap / RL / event
// configuration (mostly legal, some illegal: the fault paths must match too), random starts on and off the calendar,
// repeated users, RX tags that match and that do not, stray configuration words while armed, resets in mid-run.
// PASS needs 0 mismatches AND activity: TX windows, replays, both fault bits seen, retirements.
// LAN 2 / 3 are the RTL mutants (no rec bypass / key one edge late): must FAIL.
module tb_dsdv_mu_hwin_la;
    parameter integer NS = 47, NEV = 8, LAN = 1, EPOCHS = 400, RUN = 3000;
    localparam integer SI = $clog2(NS);
    reg ck = 0; always #5 ck = ~ck;
    reg rst_n = 0; reg [52:0] f_ks = 0; reg [25:0] f_mc = 0, f_mw = 0; reg [63:0] mu_rt = 0;
    wire [135:0] c_a, c_b; wire [43:0] rc_a, rc_b; wire [1:0] wf_a, wf_b;
    dsdv_mu_hwin #(.NSLOT(NS), .NEV(NEV), .NEP(4), .NRT(2), .LA(0))   u_a (.ck(ck), .rst_n(rst_n), .f_ks(f_ks), .f_mc(f_mc), .f_mw(f_mw),
        .mu_c(c_a), .mu_rc(rc_a), .mu_rt(mu_rt), .t_wf(wf_a));
    dsdv_mu_hwin #(.NSLOT(NS), .NEV(NEV), .NEP(4), .NRT(2), .LA(LAN)) u_b (.ck(ck), .rst_n(rst_n), .f_ks(f_ks), .f_mc(f_mc), .f_mw(f_mw),
        .mu_c(c_b), .mu_rc(rc_b), .mu_rt(mu_rt), .t_wf(wf_b));
    integer chk = 0, bad = 0, n_c = 0, n_rc = 0, n_wf0 = 0, n_wf1 = 0, n_ret = 0, n_rec = 0, n_clean = 0;
    reg [1:0] wf_d = 0; integer i4;
    always @(negedge ck) begin
        chk = chk + 1;
        if ({c_a, rc_a, wf_a} !== {c_b, rc_b, wf_b}) begin bad = bad + 1; if (bad < 4) $display("HWIN_LA mismatch at %0t", $time); end
        for (i4 = 0; i4 < 4; i4 = i4 + 1) begin if (c_a[34*i4]) n_c = n_c + 1; if (rc_a[11*i4]) n_rc = n_rc + 1; end
        if (wf_a[0] && !wf_d[0]) n_wf0 = n_wf0 + 1; if (wf_a[1] && !wf_d[1]) n_wf1 = n_wf1 + 1; wf_d = wf_a;
        if (u_a.due) n_ret = n_ret + 1; if (u_a.rec) n_rec = n_rec + 1;
    end
    task mcw(input sel, input [23:0] d); begin @(negedge ck); f_mc = {1'b1, sel, d}; @(negedge ck); f_mc = 0; end endtask
    task mww(input [23:0] d); begin @(negedge ck); f_mw = {1'b1, 1'b0, d}; @(negedge ck); f_mw = 0; end endtask
    integer ep, n, k, g, rl, dd, cyc, pst, nu, legal, clean, e2, s2, gmin, pk;
    reg [9:0] lu; reg [20:0] lp;
    initial begin
        for (ep = 0; ep < EPOCHS; ep = ep + 1) begin
            #3 rst_n = 0; f_ks = 0; f_mc = 0; f_mw = 0; mu_rt = 0; repeat (3) @(negedge ck); #2 rst_n = 1; repeat (4) @(negedge ck);
            legal = (ep % 4) != 3; clean = (ep % 4) == 0;      // clean: distinct (kind, endpoint) per event, RX tags of outstanding starts only
            n = (NS <= 8 && ($urandom % 4) == 0) ? 1 : 2 + $urandom % ((NS > 6) ? 5 : NS - 1);
            gmin = (n == 1) ? NS + 2 : n + 2;
            for (k = 0; k < n; k = k + 1) begin g = legal ? gmin + $urandom % 10 : gmin - 3 + $urandom % 8; mcw(1'b0, g[23:0]); end
            rl = legal ? gmin + 4 + $urandom % 40 : $urandom % 30;
            if (clean || ($urandom % 16) != 0) mcw(1'b1, rl[23:0]);
            for (e2 = 0; e2 < NEV; e2 = e2 + 1) begin
                if (clean) mww({1'b0, 2'd0, 10'd0, 2'(e2), 1'(e2 >> 2), 3'd0, 5'(e2)}); else
                mww({1'b0, 2'd0, 10'd0, 2'($urandom), 1'($urandom), 3'd0, 5'(e2)});
                dd = legal ? gmin + $urandom % (rl - gmin - 1) : $urandom % 40;
                if (clean || ($urandom % 32) != 0) mww({1'b0, 2'd1, 21'(dd)});
                for (s2 = 0; s2 < ((NS < 8) ? NS : 8); s2 = s2 + 1) mww({1'b0, 2'd2, 9'd0, 2'($urandom), 10'(s2)});
            end
            pst = 1 + $urandom % 3; pst = (pst == 1) ? 2 : (pst == 2) ? 9 : 40; nu = 2 + $urandom % 30;
            lu = 0; lp = 0;
            for (cyc = 0; cyc < RUN; cyc = cyc + 1) begin
                @(negedge ck);
                f_ks = 0; f_mc = 0; f_mw = 0; mu_rt = 0;
                if (($urandom % pst) == 0) begin f_ks = {1'b1, 10'($urandom % nu), 21'($urandom), 21'($urandom % 64)}; lu = f_ks[51:42]; lp = f_ks[20:0]; end
                pk = $urandom % NS;
                if (clean) begin if (($urandom % 3) == 0 && u_a.vld[pk]) mu_rt[31:0] = {1'b1, u_a.eu[pk], u_a.ep[pk]}; end
                else begin
                    if (($urandom % 7) == 0) mu_rt[31:0]  = {1'b1, (($urandom % 8) != 0) ? {lu, lp} : 31'($urandom)};
                    if (($urandom % 11) == 0) mu_rt[63:32] = {1'b1, 10'($urandom % nu), 21'($urandom % 64)};
                end
                if (!legal && ($urandom % 700) == 0) f_mc = {1'b1, 1'($urandom), 24'($urandom % 50)};
                if (!legal && ($urandom % 900) == 0) f_mw = {1'b1, 1'b0, 1'b0, 2'($urandom), 21'($urandom % 40)};
                if (!clean && ($urandom % 4000) == 0) begin #2 rst_n = 0; #7 rst_n = 1; end
            end
            if (clean && wf_a == 0) n_clean = n_clean + 1;
        end
        $display("TB_HWIN_LA NS=%0d NEV=%0d LA=%0d checks=%0d bad=%0d tx_windows=%0d replays=%0d wf0=%0d wf1=%0d retire=%0d rec=%0d clean_epochs=%0d",
                 NS, NEV, LAN, chk, bad, n_c, n_rc, n_wf0, n_wf1, n_ret, n_rec, n_clean);
        if (bad == 0 && n_c > 2000 && n_rc > 200 && n_wf0 > 10 && n_wf1 > 10 && n_ret > 2000 && n_clean > 20) $display("TB_HWIN_LA PASS");
        else $display("TB_HWIN_LA FAIL");
        $finish;
    end
endmodule
