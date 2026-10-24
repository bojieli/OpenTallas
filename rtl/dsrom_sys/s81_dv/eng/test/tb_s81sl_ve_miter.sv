`timescale 1ns/1ps
// S81-VE4 miter bench: ot_s81sl_ve r4 (native-32 source, DUT) against the r3 RTL (6ad9506a1, renamed r3ref_*, test/ref_r3)
// and against tools/hdc_golden_v41 (tools/s81_dv/ve_golden.py fixtures, +dir=).  Build with -DSYNTHESIS (no simulation
// initial values: the ring pointers power up random too) and run with +verilator+rand+reset+2: EVERY unreset register
// of both designs powers up independently random.  Checks, from the first released reset edge (no warm-up mask):
//   control {p_v, o_v, fault} equal every edge; payload {p_c, p_hh, p_kk, p_dd} / {o_c, o_y} equal on every valid edge;
//   phase 1: one beat (4 copies x 64 elements reduce, 32 add sub-beats) bit exact against the golden;
//   phase 2: eight in-flight resets (asserted at distinct stream ages, 1..3 cycles long) then legal streams again.
// Outputs during reset assertion are the parent's don't-care.  MUT (DUT only; the reference stays MUT 0): any mismatch
// prints "MUTANT n REJECTED mismatches=k".
module tb_s81sl_ve_miter #(parameter integer MUT = 0, GAP = 0, LM = 5, LA = 4);
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg r_v = 0; reg [1:0] r_c = 0; reg [127:0] r_h = 0, r_k = 0, r_w = 0;
    reg a_v = 0; reg [1:0] a_c = 0; reg [255:0] a_h = 0, a_val = 0; reg [31:0] a_g = 0;
    wire p_v, o_v, fault; wire [1:0] p_c, o_c; wire [31:0] p_hh, p_kk, p_dd; wire [255:0] o_y;
    ot_s81sl_ve #(.LM(LM), .LA(LA), .MUT(MUT)) dut (clk, rst_n, r_v, r_c, r_h, r_k, r_w, p_v, p_c, p_hh, p_kk, p_dd,
                                               a_v, a_c, a_h, a_val, a_g, o_v, o_c, o_y, fault);
    wire n_pv, n_ov, n_fault; wire [1:0] n_pc, n_oc; wire [31:0] n_hh, n_kk, n_dd; wire [255:0] n_y;
    r3ref_ot_s81sl_ve #(.LM(LM), .LA(LA), .MUT(0)) ref_r3 (clk, rst_n, r_v, r_c, r_h, r_k, r_w, n_pv, n_pc, n_hh, n_kk, n_dd,
                                               a_v, a_c, a_h, a_val, a_g, n_ov, n_oc, n_y, n_fault);
    integer compared = 0, diffs = 0, nvp = 0, nvo = 0;
    reg [31:0] hm [0:255], km [0:255], wm [0:255], vm [0:63], gm [0:3], pm [0:11], ym [0:255];
    string dir; reg stress = 0; integer ep, j;
    integer i, c, e, cyc = 0, bad = 0, np = 0, no = 0, t_r0 = -1, t_p_last = -1, t_a0 = -1, t_o_last = -1;
    always @(posedge clk) cyc <= cyc + 1;
    always @(posedge clk) begin
        #0.01;
        if (rst_n) begin
            compared = compared + 1;
            if ({p_v, o_v, fault} !== {n_pv, n_ov, n_fault}) begin
                diffs = diffs + 1;
                if (diffs < 6) $display("MITER CONTROL DIFF cyc=%0d r4=%b r3=%b", cyc, {p_v, o_v, fault}, {n_pv, n_ov, n_fault});
            end
            if (p_v) begin
                nvp = nvp + 1;
                if ({p_c, p_hh, p_kk, p_dd} !== {n_pc, n_hh, n_kk, n_dd}) begin
                    diffs = diffs + 1; if (diffs < 6) $display("MITER PARTIAL DIFF cyc=%0d", cyc);
                end
            end
            if (o_v) begin
                nvo = nvo + 1;
                if ({o_c, o_y} !== {n_oc, n_y}) begin
                    diffs = diffs + 1; if (diffs < 6) $display("MITER OUTPUT DIFF cyc=%0d", cyc);
                end
            end
        end
    end
    always @(posedge clk) if (rst_n && !stress) begin
        if (p_v) begin
            if (p_c != np[1:0]) begin bad = bad + 1; $display("BAD partial copy %0d expected %0d", p_c, np); end
            if (p_hh !== pm[3*np] || p_kk !== pm[3*np+1] || p_dd !== pm[3*np+2]) begin
                bad = bad + 1;
                $display("BAD partial copy %0d: hh %h/%h kk %h/%h dd %h/%h", np, p_hh, pm[3*np], p_kk, pm[3*np+1], p_dd, pm[3*np+2]);
            end
            np = np + 1; t_p_last = cyc;
        end
        if (o_v) begin
            for (e = 0; e < 8; e = e + 1)
                if (o_y[32*e +: 32] !== ym[8*no + e]) begin
                    bad = bad + 1;
                    if (bad < 8) $display("BAD y sub-beat %0d lane %0d: %h vs %h", no, e, o_y[32*e +: 32], ym[8*no + e]);
                end
            if (o_c != no[4:3]) begin bad = bad + 1; $display("BAD y copy"); end
            no = no + 1; t_o_last = cyc;
        end
        if (fault && MUT == 0) begin bad = bad + 1; $display("fault at cycle %0d", cyc); end
    end
    always @(posedge clk) if (cyc > 6000) $fatal(1, "timeout");
    initial begin
        if (!$value$plusargs("dir=%s", dir)) $fatal(1, "dir required");
        $readmemh({dir, "/h.mem"}, hm); $readmemh({dir, "/k.mem"}, km); $readmemh({dir, "/w.mem"}, wm);
        $readmemh({dir, "/v.mem"}, vm); $readmemh({dir, "/g.mem"}, gm); $readmemh({dir, "/p.mem"}, pm);
        $readmemh({dir, "/y.mem"}, ym);
        repeat (4) @(negedge clk); rst_n = 1; repeat (6) @(negedge clk);
        t_r0 = cyc;
        for (i = 0; i < 64; i = i + 1) begin
            r_v = 1; r_c = i / 16;
            for (e = 0; e < 4; e = e + 1) begin
                r_h[32*e +: 32] = hm[4*i + e]; r_k[32*e +: 32] = km[4*i + e]; r_w[32*e +: 32] = wm[4*i + e];
            end
            @(negedge clk); r_v = 0;
            repeat (GAP) @(negedge clk);
        end
        wait (np == 4); repeat (3) @(negedge clk);
        t_a0 = cyc;
        for (i = 0; i < 32; i = i + 1) begin
            a_v = 1; a_c = i / 8; a_g = gm[i / 8];
            for (e = 0; e < 8; e = e + 1) begin a_h[32*e +: 32] = hm[8*i + e]; a_val[32*e +: 32] = vm[8*(i % 8) + e]; end
            @(negedge clk);
        end
        a_v = 0;
        wait (no == 32); repeat (20) @(negedge clk);
        if (MUT == 0 && (bad || np != 4 || no != 32)) $fatal(1, "FAIL golden %0d mismatches np=%0d no=%0d", bad, np, no);
        if (MUT == 0)
            $display("PASS golden beat 4 copies x 64: 12 partials + 256 outputs bit exact; reduce %0d cyc (GAP %0d), add %0d cyc",
                     t_p_last - t_r0, GAP, t_o_last - t_a0);
        stress = 1;
        for (ep = 0; ep < 8; ep = ep + 1) begin
            rst_n = 0; r_v = 0; a_v = 0; repeat (4) @(negedge clk); rst_n = 1; repeat (6) @(negedge clk);
            // legal copy-major stream, interrupted by a reset at distinct arithmetic / queue ages
            for (j = 0; j < 64; j = j + 1) begin
                r_v = 1; r_c = j / 16;
                for (e = 0; e < 4; e = e + 1) begin r_h[32*e+:32] = hm[4*j+e]; r_k[32*e+:32] = km[4*j+e]; r_w[32*e+:32] = wm[4*j+e]; end
                a_v = (j < 32); a_c = j / 8; a_g = gm[(j / 8) % 4];
                for (e = 0; e < 8; e = e + 1) begin a_h[32*e+:32] = hm[(8*j+e)%256]; a_val[32*e+:32] = vm[(8*j+e)%64]; end
                @(negedge clk);
                if (j == ep * 7 + 2) begin rst_n = 0; r_v = 0; a_v = 0; repeat ((ep % 3) + 1) @(negedge clk); j = 64; end
            end
            r_v = 0; a_v = 0;
            repeat (4) @(negedge clk); rst_n = 1; repeat (170) @(negedge clk);
        end
        if (MUT != 0) begin
            if (diffs + bad == 0) $display("MUTANT %0d NOT DETECTED", MUT);
            else $display("MUTANT %0d REJECTED mismatches=%0d", MUT, diffs + bad);
        end else if (diffs == 0)
            $display("PASS MITER r4 vs r3 independent random init + 8 in-flight resets: %0d released edges, %0d partial / %0d output valid edges equal",
                     compared, nvp, nvo);
        else $display("FAIL MITER diffs=%0d", diffs);
        $finish;
    end
endmodule
