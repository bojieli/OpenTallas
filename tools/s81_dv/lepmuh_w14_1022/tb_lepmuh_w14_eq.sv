`timescale 1ns/1ps
// STW-S81c-COLLA3-LEP w14 (2026-10-22): LOCKSTEP equivalence of ot_s81sl_lep_mu_h with the w14 opt-ins (WRLY +1 booked
// landing edge, VQREP, SELST, PUSHREP, FHLA) against the SAME source without them (rf_* = renamed copy made by
// run_eq.sh), CRED 12 / DR 12 / RX_SRAM / IN_PIPE / NATIVE32 1, identical inputs every cycle.  Every output must be equal
// on every cycle, except ml_wv / ml_wd, which must equal the reference ONE cycle earlier (the booked +1 edge).
// Stimulus: phase 1 credit-respecting link traffic (li_v only with a credit in hand, li_r returns credits), random
// ring / HOST / KS frame kinds and tags, ro beats, t_host / t_kd events, mu_c windows, ml_rv replays, lo_r credits;
// phase 2 unconstrained (overflow / protocol faults); a reset in the middle.  Verdict "EQ_PASS ..." / "EQ_FAIL ...".
module tb_lepmuh_w14_eq;
    parameter integer SEED = 1;
    parameter integer NCYC = 40000;
    localparam integer CR = 12;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    reg [1103:0] ro = 0; reg lo0_r = 0, lo1_r = 0; reg li0_v = 0, li1_v = 0; reg [552:0] li0_d = 0, li1_d = 0;
    reg sl_f = 0; reg [2:0] l0_f = 0, l1_f = 0; reg [1:0] l0_st = 0, l1_st = 0; reg [76:0] t_host = 0; reg [53:0] t_kd = 0;
    reg [33:0] mu_c = 0; reg ml_rv = 0; reg [1103:0] ml_rd = 0; reg ml_f = 0;
    wire [1103:0] ri_d, ri_r; wire lo0_v_d, lo0_v_r, lo1_v_d, lo1_v_r; wire [552:0] lo0_d_d, lo0_d_r, lo1_d_d, lo1_d_r;
    wire li0_r_d, li0_r_r, li1_r_d, li1_r_r; wire [1:0] rxv_d, rxv_r; wire [514:0] fh_d, fh_r; wire [3:0] lf_d, lf_r;
    wire [52:0] ks_d, ks_r; wire [31:0] rt_d, rt_r; wire mwv_d, mwv_r; wire [1103:0] mwd_d, mwd_r; wire f_d, f_r;
    ot_s81sl_lep_mu_h #(.CRED(12), .DR(12), .RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) dut (.clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri_d),
        .lo0_v(lo0_v_d), .lo0_r(lo0_r), .lo0_d(lo0_d_d), .lo1_v(lo1_v_d), .lo1_r(lo1_r), .lo1_d(lo1_d_d),
        .li0_v(li0_v), .li0_r(li0_r_d), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r_d), .li1_d(li1_d), .rxv(rxv_d),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(l0_st), .l1_st(l1_st), .t_host(t_host), .t_kd(t_kd),
        .f_host(fh_d), .f_lf(lf_d), .f_ks(ks_d), .mu_c(mu_c), .mu_rt(rt_d), .ml_wv(mwv_d), .ml_wd(mwd_d),
        .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f), .fault(f_d));
    rf_s81sl_lep_mu_h #(.CRED(12), .DR(12), .RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) ref0 (.clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri_r),
        .lo0_v(lo0_v_r), .lo0_r(lo0_r), .lo0_d(lo0_d_r), .lo1_v(lo1_v_r), .lo1_r(lo1_r), .lo1_d(lo1_d_r),
        .li0_v(li0_v), .li0_r(li0_r_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r_r), .li1_d(li1_d), .rxv(rxv_r),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(l0_st), .l1_st(l1_st), .t_host(t_host), .t_kd(t_kd),
        .f_host(fh_r), .f_lf(lf_r), .f_ks(ks_r), .mu_c(mu_c), .mu_rt(rt_r), .ml_wv(mwv_r), .ml_wd(mwd_r),
        .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f), .fault(f_r));
`ifdef OT_S81SL_LEP_WRLY
    localparam integer LL = 1;
`else
    localparam integer LL = 0;
`endif
    reg mwv_q; reg [1103:0] mwd_q;
    always @(posedge clk) begin mwv_q <= mwv_r; mwd_q <= mwd_r; end
    integer cyc = 0, bad = 0, nmw = 0, nri = 0, nfh = 0, nks = 0, nlo = 0, nrt = 0, cr0 = CR, cr1 = CR, k;
    reg [31:0] seq; reg par;
    function automatic [552:0] rword(input integer lane, input integer kind, input bit p);
        reg [552:0] w; integer b;
        begin
            for (b = 0; b < 553; b = b + 32) w[b +: 32] = $urandom;
            if (lane == 0) begin
                case (kind)
                    0: begin w[0] = 1'b1; w[3:1] = ($urandom % 2) ? 3'd2 : 3'd1; end   // XB / XQ ring beat
                    1: begin w[0] = 1'b0; w[3:1] = 3'd1; end                             // HOST
                    2: begin w[0] = 1'b0; w[3:1] = 3'd2; end                             // KS
                    default: ;
                endcase
            end else begin
                if (kind == 0) begin w[1045-552] = $urandom % 2; w[1046-552] = $urandom % 2; end  // tag / land bits
            end
            w[552] = p;
            rword = w;
        end
    endfunction
    integer kind; bit ph2;
    initial begin
        if (!$value$plusargs("seed=%d", k)) k = SEED;
        void'($urandom(k));
        par = 0;
        repeat (10) @(negedge clk);
        rst_n = 1;
        for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
            @(negedge clk);
            ph2 = cyc > (NCYC * 7) / 10;
            if (cyc == NCYC / 2) begin rst_n = 0; repeat (6) @(negedge clk); rst_n = 1; cr0 = CR; cr1 = CR; end
            // link receive: a frame = one beat on each lane in the same cycle (same parity), credit-respecting in phase 1
            li0_v = 0; li1_v = 0;
            if (($urandom % 100) < 45 && (ph2 || (cr0 > 0 && cr1 > 0))) begin
                kind = $urandom % 4; par = ($urandom % 50 == 0) ? par : ~par;
                li0_v = 1; li1_v = 1; li0_d = rword(0, kind, par); li1_d = rword(1, kind, par);
                if (!ph2) begin cr0 = cr0 - 1; cr1 = cr1 - 1; end
            end else begin li0_d = rword(0, 3, par); li1_d = rword(1, 3, par); end
            if (ph2 && ($urandom % 100) < 5) li0_v = 1;                               // unpaired beat (fault path)
            lo0_r = ($urandom % 100) < 40; lo1_r = ($urandom % 100) < 40;
            for (k = 0; k < 1104; k = k + 32) ro[k +: 32] = $urandom;
            ro[0] = ($urandom % 100) < 35; ro[3:1] = ($urandom % 3 == 0) ? 3'd1 : 3'd2;
            t_host = {$urandom, $urandom, $urandom}; t_host[64] = ($urandom % 100) < 4; t_host[76:65] = ($urandom % 100 < 3) ? 12'($urandom) : t_host[76:65];
            t_kd = {$urandom, $urandom}; t_kd[53] = ($urandom % 100) < 3;
            mu_c = {$urandom, $urandom}; mu_c[0] = ($urandom % 100) < 2; mu_c[1] = 1'b0;
            ml_rv = ($urandom % 100) < 10; for (k = 0; k < 1104; k = k + 32) ml_rd[k +: 32] = $urandom;
            ml_rd[0] = ($urandom % 2); ml_rd[3:1] = ($urandom % 2) ? 3'd2 : 3'd1; ml_rd[1045] = $urandom % 2;
            sl_f = ph2 && ($urandom % 1000 == 0); l0_f = 0; l1_f = 0; l0_st = 2'($urandom); l1_st = 2'($urandom); ml_f = 0;
        end
        $display("LEPMUH_W14_EQ cycles %0d bad %0d | ml_wv %0d ri %0d f_host %0d f_ks %0d lo %0d mu_rt %0d (activity counts)",
                 NCYC, bad, nmw, nri, nfh, nks, nlo, nrt);
        if (bad == 0 && nmw > 100 && nri > 100 && nfh > 5 && nlo > 100) $display("EQ_PASS lepmuh w14 lockstep seed %0d", k);
        else $display("EQ_FAIL lepmuh w14 lockstep bad %0d", bad);
        $finish;
    end
    // credits returned by li_r (identical on both, checked below)
    always @(posedge clk) if (rst_n) begin cr0 = cr0 + li0_r_r; cr1 = cr1 + li1_r_r; if (cr0 > CR) cr0 = CR; if (cr1 > CR) cr1 = CR; end
    always @(posedge clk) if (rst_n) begin
        if (mwv_q) nmw = nmw + 1; if (ri_r[0]) nri = nri + 1; if (fh_r[0]) nfh = nfh + 1; if (ks_r[52]) nks = nks + 1;
        if (lo0_v_r) nlo = nlo + 1; if (rt_r[31]) nrt = nrt + 1;
        if ({ri_d, lo0_v_d, lo0_d_d, lo1_v_d, lo1_d_d, li0_r_d, li1_r_d, rxv_d, fh_d, lf_d, ks_d, rt_d, f_d} !==
            {ri_r, lo0_v_r, lo0_d_r, lo1_v_r, lo1_d_r, li0_r_r, li1_r_r, rxv_r, fh_r, lf_r, ks_r, rt_r, f_r}) begin
            bad = bad + 1; if (bad < 10) $display("MISMATCH cyc %0d ri %0d lo %0d%0d f_host %0d f_ks %0d mu_rt %0d fault %0d li_r %0d%0d", cyc,
                ri_d !== ri_r, lo0_d_d !== lo0_d_r, lo1_d_d !== lo1_d_r, fh_d !== fh_r, ks_d !== ks_r, rt_d !== rt_r, f_d !== f_r, li0_r_d !== li0_r_r, li1_r_d !== li1_r_r);
        end
        if (LL == 1 ? ({mwv_d, mwd_d} !== {mwv_q, mwd_q}) : ({mwv_d, mwd_d} !== {mwv_r, mwd_r})) begin
            bad = bad + 1; if (bad < 10) $display("MISMATCH cyc %0d ml_wv/ml_wd (LL %0d)", cyc, LL);
        end
    end
endmodule
