`timescale 1ns/1ps
// FABLE-FIX-S81-SEQHOST (2026-11-19): lockstep bench, dsdv_mu_hwin (restructured, 0 cycles) against the 11-18 source
// kept as test/ref/dsdv_mu_hwin_ref_1119.sv.  Both see the same pins; mu_c / mu_rc / t_wf must be equal on EVERY edge.
// Random episodes: reset, idle (pointers free-run), boot words (1 or n slot gaps, RL, event rows, slot attributes; legal
// and illegal values, words on consecutive edges, a D / RL word on the edge of the first start), then starts on and off
// the slot calendar with fresh and duplicate users, RX tags of outstanding and of unknown starts, words while armed,
// and resets in mid run.  State is NOT cleared between episodes, so stale entry payload / ages are exercised.
// DMUT: the dut's MUT parameter (3 / 4 / 5 must be caught).  PASS line: "HWIN_EQ PASS".
module tb_mu_hwin_eq;
`ifndef NSLOT
 `define NSLOT 47
`endif
`ifndef NEV
 `define NEV 8
`endif
`ifndef DMUT
 `define DMUT 0
`endif
    localparam integer NSLOT = `NSLOT, NEV = `NEV, NEP = 4, NRT = 2;
    reg ck = 0, rst_n = 0;
    always #0.5 ck = ~ck;
    reg [52:0] f_ks = 0; reg [25:0] f_mc = 0, f_mw = 0; reg [NRT*32-1:0] mu_rt = 0;
    wire [NEP*34-1:0] c_r, c_d; wire [NEP*11-1:0] rc_r, rc_d; wire [1:0] wf_r, wf_d;
    dsdv_mu_hwin_ref_1119 #(.NSLOT(NSLOT), .NEV(NEV), .NEP(NEP), .NRT(NRT), .MUT(0)) gold (.ck(ck), .rst_n(rst_n),
        .f_ks(f_ks), .f_mc(f_mc), .f_mw(f_mw), .mu_c(c_r), .mu_rc(rc_r), .mu_rt(mu_rt), .t_wf(wf_r));
    dsdv_mu_hwin #(.NSLOT(NSLOT), .NEV(NEV), .NEP(NEP), .NRT(NRT), .MUT(`DMUT)) dut (.ck(ck), .rst_n(rst_n),
        .f_ks(f_ks), .f_mc(f_mc), .f_mw(f_mw), .mu_c(c_d), .mu_rc(rc_d), .mu_rt(mu_rt), .t_wf(wf_d));
    integer errs = 0; longint cyc = 0;
    longint n_c = 0, n_rc = 0, n_rec = 0, n_due = 0, n_wf0 = 0, n_wf1 = 0, n_colw = 0, n_lt = 0, n_udup = 0, n_col = 0,
            n_oob = 0, n_offcal = 0, n_rtbad = 0, n_cwd_rec = 0, n_cwr_rec = 0, n_arm = 0, n_wr_norec = 0;
    reg [1:0] wf_p = 0; integer k;
    always @(negedge ck) begin
        cyc = cyc + 1;
        if (c_r !== c_d || rc_r !== rc_d || wf_r !== wf_d) begin
            errs = errs + 1;
            if (errs <= 20) $display("MISMATCH c%0d mu_c %h / %h  mu_rc %h / %h  t_wf %b / %b", cyc, c_r, c_d, rc_r, rc_d, wf_r, wf_d);
        end
        for (k = 0; k < NEP; k = k + 1) begin if (c_r[34*k]) n_c = n_c + 1; if (rc_r[11*k]) n_rc = n_rc + 1; end
        if (gold.rec) n_rec = n_rec + 1;
        if (gold.due) n_due = n_due + 1;
        if (wf_r[0] && !wf_p[0]) n_wf0 = n_wf0 + 1;
        if (wf_r[1] && !wf_p[1]) n_wf1 = n_wf1 + 1;
        wf_p = wf_r;
        if (gold.col_w) n_colw = n_colw + 1;
        if (|gold.lt) n_lt = n_lt + 1;
        if (gold.st && gold.udup) n_udup = n_udup + 1;
        if (gold.st && gold.col) n_col = n_col + 1;
        if (gold.st && !gold.on_cal) n_offcal = n_offcal + 1;
        if (gold.rtbad) n_rtbad = n_rtbad + 1;
        if (32'(gold.rp) >= NSLOT || 32'(gold.pe[0]) >= NSLOT) n_oob = n_oob + 1;
        if (dut.cwd && dut.rec) n_cwd_rec = n_cwd_rec + 1;
        if (dut.cwr && dut.rec) n_cwr_rec = n_cwr_rec + 1;
        if (gold.st && !gold.armed && !gold.hcfg_bad) n_arm = n_arm + 1;
        if ((|dut.wr) && !dut.rec) n_wr_norec = n_wr_norec + 1;
    end
    function automatic integer rnd(input integer lo, input integer hi);    // uniform lo..hi
        if (hi <= lo) rnd = lo; else rnd = lo + integer'($urandom % (hi - lo + 1));
    endfunction
    function automatic bit pct(input integer p); pct = (integer'($urandom % 1000) < p); endfunction   // p in 1/1000
    task automatic tick; begin @(posedge ck); #0.1; f_ks = 0; f_mc = 0; f_mw = 0; mu_rt = 0; end endtask
    integer ep_n, n, nw, g0, P, RL, x, j, s, q, runlen, pool, unext, eps, seed, idlen;
    integer gap [0:1023]; integer Dv [0:31];
    reg sim_d, sim_rl, do_rt, do_badrt, do_cfgrun, do_midrst, early_start; integer simev;
    reg [25:0] wq [0:8191]; reg wk [0:8191]; integer nwq, wi, wj, nmc, half;      // boot word queue: wk 0 = f_mc, 1 = f_mw
    task automatic push(input bit kind, input [25:0] w); begin wq[nwq] = w; wk[nwq] = kind; nwq = nwq + 1; end endtask
    initial begin
        if (!$value$plusargs("EPS=%d", eps)) eps = 200;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        x = $urandom(seed);
        for (ep_n = 0; ep_n < eps; ep_n = ep_n + 1) begin
            // ---- reset + idle
            rst_n = 0; repeat (rnd(1, 4)) tick; rst_n = 1;
            idlen = pct(300) ? rnd(0, 6) : rnd(0, 3 * NSLOT + 40);
            repeat (idlen) tick;
            // ---- episode shape
            n = pct(200) ? 1 : (pct(550) ? rnd(2, (NSLOT < 6) ? NSLOT : 6) : rnd(2, NSLOT));
            nw = (n == 1) ? NSLOT : n;
            g0 = pct(30) ? rnd(1, nw) : rnd(nw, nw + 30);
            P = 0;
            for (j = 0; j < n; j = j + 1) begin gap[j] = g0 + rnd(0, 3); P = P + ((n == 1) ? NSLOT * gap[j] : gap[j]); end
            x = rnd(0, 99);
            if (x < 70) RL = rnd(nw + 3, P - 1); else if (x < 85) RL = rnd(P, 2 * P); else if (x < 90) RL = rnd(0, nw); else RL = rnd(3, nw + 3);
            for (j = 0; j < NEV; j = j + 1) begin
                x = rnd(0, 99);
                if (x < 75 && RL - 2 >= nw + 2) Dv[j] = rnd(nw + 2, RL - 2);
                else if (x < 82) Dv[j] = rnd(0, 3);
                else if (x < 92 && j > 0) Dv[j] = Dv[j-1];
                else Dv[j] = rnd(0, RL + 3);
            end
            sim_d = pct(60); sim_rl = pct(40); simev = rnd(0, NEV - 1);
            do_rt = pct(500); do_badrt = pct(150); do_cfgrun = pct(150); do_midrst = pct(60); early_start = pct(40);
            // ---- boot words
            nwq = 0;
            for (j = 0; j < n; j = j + 1) push(0, {1'b1, 1'b0, 24'(gap[j])});
            if (pct(30)) push(0, {1'b1, 1'b0, 24'(g0)});                 // one more gap than planned
            push(0, {1'b1, 1'b1, 24'(RL)});
            for (j = 0; j < NEV; j = j + 1) begin
                push(1, {1'b1, 2'b00, 2'd0, 21'((rnd(0, 3) << 9) | (rnd(0, 1) << 8) | j)});
                if (pct(100)) push(1, {1'b1, 2'b00, 2'd1, 21'(rnd(0, 50))});     // overwritten below
                push(1, {1'b1, 2'b00, 2'd1, 21'(Dv[j])});
                for (s = 0; s < nw; s = s + 1) if (pct(900)) push(1, {1'b1, 2'b00, 2'd2, 21'((rnd(0, 3) << 10) | s)});
                if (pct(100)) push(1, {1'b1, 2'b00, 2'd2, 21'((rnd(0, 3) << 10) | rnd(NSLOT, 1023))});   // slot index past the table
            end
            if (pct(20)) push(1, {1'b1, 2'b00, 2'd3, 21'd0});              // sel 3: config fault
            // f_mc words in order and f_mw words in order; the two streams share edges at random
            wi = 0; wj = 0; while (wi < nwq && wk[wi] == 0) wi = wi + 1;     // wi: next f_mw word, wj: next f_mc word
            nmc = wi; half = (nwq - nmc) / 2 + nmc;
            while (wj < nmc || wi < nwq) begin
                if (wj < nmc && pct(600)) begin f_mc = wq[wj]; wj = wj + 1; end
                if (wi < nwq && pct(800)) begin f_mw = wq[wi]; wi = wi + 1;
                    if (early_start && wi == half) f_ks = {1'b1, 10'(rnd(0, 7)), 21'd0, 21'($urandom)}; end
                @(posedge ck); #0.1; f_ks = 0; f_mc = 0; f_mw = 0;
                if (pct(100)) repeat (rnd(1, 3)) tick;
            end
            repeat (rnd(0, 5)) tick;
            // ---- run
            runlen = pct(100) ? rnd(10, 200) : rnd(P, 5 * P + 200);
            if (runlen > 40000) runlen = 40000;
            pool = pct(700) ? nw : rnd(1, nw + 4); unext = rnd(0, 1023);
            for (q = 0; q < runlen; q = q + 1) begin
                // starts: st lands one edge after f_ks; on_cal then iff (armed && ph == cg) now
                if (!gold.armed ? pct(60) : ((gold.ph == gold.cg) ? pct(850) : pct(8))) begin
                    if (pct(950)) begin x = unext; unext = (unext + 1) % 1024; end
                    else x = rnd(0, 1023);
                    f_ks = {1'b1, 10'((pool > 0) ? (x % pool) + ((pct(980)) ? 0 : 1) : x), 21'($urandom), 21'($urandom)};
                    if (!gold.armed && sim_d)  begin f_mw = {1'b1, 2'b00, 2'd1, 21'(rnd(0, 2))}; sim_d = 0; end
                    if (!gold.armed && sim_rl) begin f_mc = {1'b1, 1'b1, 24'(rnd(0, 4))}; sim_rl = 0; end
                end
                if (do_rt) for (j = 0; j < NRT; j = j + 1) begin
                    x = rnd(0, NSLOT - 1);
                    if (pct(300) && gold.vld[x]) mu_rt[32*j +: 32] = {1'b1, gold.eu[x], gold.ep[x]};
                    else if (do_badrt && pct(2)) mu_rt[32*j +: 32] = {1'b1, 10'($urandom), 21'($urandom)};
                    else mu_rt[32*j +: 32] = {1'b0, 31'($urandom)};
                end
                if (do_cfgrun && pct(2)) begin if (pct(500)) f_mc = 26'($urandom) | 26'h2000000; else f_mw = 26'($urandom) | 26'h2000000; end
                if (do_midrst && pct(1)) q = runlen;
                @(posedge ck); #0.1; f_ks = 0; f_mc = 0; f_mw = 0; mu_rt = 0;
            end
        end
        repeat (4) tick;
        $display("HWIN_EQ stats NSLOT %0d NEV %0d DMUT %0d seed %0d episodes %0d cycles %0d: mu_c %0d mu_rc %0d rec %0d due %0d arm %0d t_wf0 %0d t_wf1 %0d col_w %0d late %0d dup-user %0d slot-busy %0d off-cal %0d rtbad %0d oob-ptr-cycles %0d Dword+rec %0d RLword+rec %0d wr-without-rec %0d",
                 NSLOT, NEV, `DMUT, seed, eps, cyc, n_c, n_rc, n_rec, n_due, n_arm, n_wf0, n_wf1, n_colw, n_lt, n_udup, n_col, n_offcal, n_rtbad, n_oob, n_cwd_rec, n_cwr_rec, n_wr_norec);
        if (errs == 0 && n_c > 0 && n_rc > 0 && n_due > 0) $display("HWIN_EQ PASS"); else $display("HWIN_EQ FAIL errs %0d", errs);
        $finish;
    end
endmodule
