`timescale 1ns/1ps
// lockstep: old (pre-fix, renamed old_*) vs new ot_s81_cfg7_seq_bfp (kit params LAYOUT 1 PINREG 1) and
// ot_s81_cfg7_seq_local at PQ 1 (LAYOUT 1 PINREG 1, LAYOUT 0 PINREG 0) and PQ 0 (LAYOUT 1 PINREG 1); every output every cycle
module tb;
    localparam integer PHW = 10;
    reg clk = 0;
    reg rst_n = 0;
    reg [PHW+4:0] lc = 0;
    reg [71:0] q [0:6];
    reg [1:0] ef = 0;
    integer cyc, errs, n_pend, n_cgo;
    always #5 clk = ~clk;
    // ---- bfp ----
    wire [11:0] a_o, a_n; wire [6:0] ce_o, ce_n; wire [53:0] cfg_o, cfg_n; wire ge_o, ge_n; wire [1:0] st_o, st_n; wire [37:0] fp_o, fp_n;
    old_ot_s81_cfg7_seq_bfp #(.LAYOUT(1), .PINREG(1)) uo (.clk(clk), .rst_n(rst_n), .lc(lc), .a(a_o),
        .ce0(ce_o[0]), .ce1(ce_o[1]), .ce2(ce_o[2]), .ce3(ce_o[3]), .ce4(ce_o[4]), .ce5(ce_o[5]), .ce6(ce_o[6]),
        .q0(q[0]), .q1(q[1]), .q2(q[2]), .q3(q[3]), .q4(q[4]), .q5(q[5]), .q6(q[6]), .cfg(cfg_o), .go_e(ge_o), .st(st_o), .f_prog(fp_o));
    ot_s81_cfg7_seq_bfp #(.LAYOUT(1), .PINREG(1)) un (.clk(clk), .rst_n(rst_n), .lc(lc), .a(a_n),
        .ce0(ce_n[0]), .ce1(ce_n[1]), .ce2(ce_n[2]), .ce3(ce_n[3]), .ce4(ce_n[4]), .ce5(ce_n[5]), .ce6(ce_n[6]),
        .q0(q[0]), .q1(q[1]), .q2(q[2]), .q3(q[3]), .q4(q[4]), .q5(q[5]), .q6(q[6]), .cfg(cfg_n), .go_e(ge_n), .st(st_n), .f_prog(fp_n));
    wire [37+54+12+7+1+2:0] vb_o = {fp_o, cfg_o, a_o, ce_o, ge_o, st_o};
    wire [37+54+12+7+1+2:0] vb_n = {fp_n, cfg_n, a_n, ce_n, ge_n, st_n};
    // ---- local, 3 parameter sets ----
    localparam integer LW = 12 + 7 + 54 + 1 + 2 + 2 + 7 + 6 + 1;
    wire [LW-1:0] vl_o [0:2];
    wire [LW-1:0] vl_n [0:2];
    genvar g;
    generate for (g = 0; g < 3; g = g + 1) begin : g_loc
        localparam integer PQ_ = (g == 2) ? 0 : 1;
        localparam integer LY_ = (g == 1) ? 0 : 1;
        localparam integer PR_ = (g == 1) ? 0 : 1;
        wire [11:0] ao, an; wire [6:0] co, cn; wire [53:0] fo, fn; wire go_o, go_n; wire [1:0] so, sn, to, tn;
        wire [6:0] clo, cln; wire [5:0] flo, fln; wire glo, gln;
        old_ot_s81_cfg7_seq_local #(.PQ(PQ_), .LAYOUT(LY_), .LOCAL_COPY(PR_), .PINREG(PR_)) lo (.clk(clk), .rst_n(rst_n), .lc(lc), .a(ao),
            .ce0(co[0]), .ce1(co[1]), .ce2(co[2]), .ce3(co[3]), .ce4(co[4]), .ce5(co[5]), .ce6(co[6]),
            .q0(q[0][47:0]), .q1(q[1][47:0]), .q2(q[2][47:0]), .q3(q[3][47:0]), .q4(q[4][47:0]), .q5(q[5][47:0]), .q6(q[6][47:0]),
            .cfg(fo), .go_e(go_o), .st(so), .ef(ef), .go_tag(to), .ce_local(clo), .cfg_local(flo), .go_local(glo));
        ot_s81_cfg7_seq_local #(.PQ(PQ_), .LAYOUT(LY_), .LOCAL_COPY(PR_), .PINREG(PR_)) ln (.clk(clk), .rst_n(rst_n), .lc(lc), .a(an),
            .ce0(cn[0]), .ce1(cn[1]), .ce2(cn[2]), .ce3(cn[3]), .ce4(cn[4]), .ce5(cn[5]), .ce6(cn[6]),
            .q0(q[0][47:0]), .q1(q[1][47:0]), .q2(q[2][47:0]), .q3(q[3][47:0]), .q4(q[4][47:0]), .q5(q[5][47:0]), .q6(q[6][47:0]),
            .cfg(fn), .go_e(go_n), .st(sn), .ef(ef), .go_tag(tn), .ce_local(cln), .cfg_local(fln), .go_local(gln));
        assign vl_o[g] = {ao, co, fo, go_o, so, to, clo, flo, glo};
        assign vl_n[g] = {an, cn, fn, go_n, sn, tn, cln, fln, gln};
    end endgenerate
    integer k, NCYC;
    initial begin
        if (!$value$plusargs("ncyc=%d", NCYC)) NCYC = 200000;
        errs = 0; n_pend = 0; n_cgo = 0;
        for (k = 0; k < 7; k = k + 1) q[k] = {$urandom, $urandom, $urandom};
        for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
            @(negedge clk);
            if (vb_o !== vb_n) begin errs = errs + 1; if (errs <= 5) $display("MISMATCH bfp cyc %0d old %h new %h", cyc, vb_o, vb_n); end
            for (k = 0; k < 3; k = k + 1)
                if (vl_o[k] !== vl_n[k]) begin errs = errs + 1; if (errs <= 5) $display("MISMATCH local%0d cyc %0d old %h new %h", k, cyc, vl_o[k], vl_n[k]); end
            // stimulus: reset first 8 cycles and rarely later; sparse cfg_go / go (lc[1] / lc[0]), random phase / np, random ef
            rst_n = !(cyc < 8 || ($urandom % 20000) == 0);
            lc = $urandom;
            lc[1] = (($urandom % 23) == 0);
            lc[0] = (($urandom % 29) == 0);
            ef = (($urandom % 3) == 0) ? 2'b11 : 2'($urandom);
            if (lc[1] && ef != 2'b11) n_pend = n_pend + 1;
            if (lc[1]) n_cgo = n_cgo + 1;
            for (k = 0; k < 7; k = k + 1) q[k] = {$urandom, $urandom, $urandom};
        end
        $display("CFG7_LOCKSTEP cycles %0d cfg_go %0d busy_broadcasts %0d mismatches %0d %s", NCYC, n_cgo, n_pend, errs, errs == 0 ? "PASS" : "FAIL");
        $finish;
    end
endmodule
