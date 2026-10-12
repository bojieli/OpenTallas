`timescale 1ns/1ps
// tb_s81lv_bgq_tlm_eq (el1011-s81lv/B, 2026-10-12): lockstep equivalence of the bank-group TLM s81lv_vm_bgq_tlm against
// the real tile dsfd_vm_bgq #(NP 28, NPR 10, NSTG 2, EP 2, MACRO 1) (= dsfd_vm_bgq28) at the same group strap: phase 1
// writes every row of the group (full mask), phase 2 runs NCYC cycles of seeded random masked writes / reads on all
// ports (reads on 0 .. NPR-1, at most one op per bank a cycle so the closed tile's queue contract holds) plus random
// upstream r_* traffic.  Every cycle after reset: f_*, o_v, o_d, o_f, o_o of the two must be identical.
// Prints RESULT ... and PASS / FAIL.  +define+S81LV_MUT_BGADDR (TLM group decode on row[5:4]) must FAIL.
module tb_s81lv_bgq_tlm_eq;
    parameter integer SEED = 1, NCYC = 20000, GRP = 1;
    localparam integer NP = 28, NPR = 10, DW = 128;
    reg clk = 0; always #1 clk = ~clk;
    reg rs = 0;
    reg [NP-1:0] i_v = 0, i_we = 0; reg [NP*14-1:0] i_row = 0; reg [NP*4-1:0] i_m = 0; reg [NP*DW-1:0] i_d = 0;
    reg [NPR-1:0] r_v = 0; reg [NPR*DW-1:0] r_d = 0; reg [3:0] r_f = 0; reg [2:0] r_o = 0;
    wire [NP-1:0] fv_a, fwe_a, fv_b, fwe_b; wire [NP*14-1:0] fr_a, fr_b; wire [NP*4-1:0] fm_a, fm_b;
    wire [NP*DW-1:0] fd_a, fd_b; wire [NPR-1:0] ov_a, ov_b; wire [NPR*DW-1:0] od_a, od_b; wire [3:0] of_a, of_b;
    wire [2:0] oo_a, oo_b;
    wire [1:0] g = GRP;
    dsfd_vm_bgq #(.NP(NP), .NPR(NPR), .NB(32), .NBL(8), .QD(4), .RQ(8), .MACRO(1), .DW(DW), .NSTG(2), .EP(2)) u_real (
        .ck(clk), .rs(rs), .grp(g), .i_v(i_v), .i_we(i_we), .i_row(i_row), .i_mask(i_m), .i_d(i_d),
        .f_v(fv_a), .f_we(fwe_a), .f_row(fr_a), .f_mask(fm_a), .f_d(fd_a), .r_v(r_v), .r_d(r_d), .r_f(r_f), .r_o(r_o),
        .o_v(ov_a), .o_d(od_a), .o_f(of_a), .o_o(oo_a));
    s81lv_vm_bgq_tlm u_tlm (
        .ck(clk), .rs(rs), .grp(g), .i_v(i_v), .i_we(i_we), .i_row(i_row), .i_mask(i_m), .i_d(i_d),
        .f_v(fv_b), .f_we(fwe_b), .f_row(fr_b), .f_mask(fm_b), .f_d(fd_b), .r_v(r_v), .r_d(r_d), .r_f(r_f), .r_o(r_o),
        .o_v(ov_b), .o_d(od_b), .o_f(of_b), .o_o(oo_b));
    integer cyc = 0, nbad = 0, nrd = 0, nwr = 0, nown = 0, p, b, k;
    reg [31:0] busy;
    reg live = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (live) begin
            if (fv_a !== fv_b || fwe_a !== fwe_b || ((fr_a ^ fr_b) & {NP{14'h3fff}}) != 0 || fd_a !== fd_b || fm_a !== fm_b) begin
                nbad = nbad + 1; if (nbad < 6) $display("MISMATCH f_* cyc %0d", cyc); end
            if (ov_a !== ov_b || of_a !== of_b) begin
                nbad = nbad + 1; if (nbad < 6) $display("MISMATCH o_v/o_f cyc %0d: real %b/%b tlm %b/%b", cyc, ov_a, of_a, ov_b, of_b); end
            for (p = 0; p < NPR; p = p + 1) if (ov_a[p] && od_a[DW*p +: DW] !== od_b[DW*p +: DW]) begin
                nbad = nbad + 1; if (nbad < 6) $display("MISMATCH o_d port %0d cyc %0d: real %h tlm %h", p, cyc, od_a[DW*p +: 32], od_b[DW*p +: 32]); end
        end
    end
    task automatic op(input integer pp, input integer row, input integer we, input [3:0] m);
        begin
            i_v[pp] = 1; i_we[pp] = we[0]; i_row[14*pp +: 14] = row[13:0]; i_m[4*pp +: 4] = m;
            for (k = 0; k < 4; k = k + 1) i_d[DW*pp + 32*k +: 32] = $urandom;
            if (we) nwr = nwr + 1; else nrd = nrd + 1;
            if (row[4:3] == GRP) nown = nown + 1;
        end
    endtask
    integer r, bank, pp, n;
    initial begin
        void'($urandom(SEED));
        repeat (5) @(negedge clk); rs = 1; repeat (6) @(negedge clk); live = 1;
        // phase 1: write every row of the group (8 ops a cycle, one per bank)
        for (r = 0; r < 512; r = r + 1) begin
            @(negedge clk); i_v = 0;
            for (b = 0; b < 8; b = b + 1) op(b, {r[8:0], GRP[1:0], b[2:0]}, 1, 4'hf);
        end
        @(negedge clk); i_v = 0;
        // phase 2: random traffic, at most one op per bank a cycle
        for (n = 0; n < NCYC; n = n + 1) begin
            @(negedge clk); i_v = 0; busy = 0; r_v = 0;
            for (pp = 0; pp < NP; pp = pp + 1) if ($urandom % 6 == 0) begin
                bank = (($urandom % 3) == 0) ? $urandom % 32 : GRP * 8 + $urandom % 8;
                if (!busy[bank]) begin
                    busy[bank] = 1'b1;
                    if (pp < NPR && $urandom % 2) op(pp, {$urandom % 512, bank[4:0]} , 0, 4'h0);
                    else op(pp, {$urandom % 512, bank[4:0]}, 1, $urandom % 16);
                end
            end
            for (pp = 0; pp < NPR; pp = pp + 1) if ($urandom % 9 == 0) begin r_v[pp] = 1; r_d[DW*pp +: 32] = $urandom; end
        end
        @(negedge clk); i_v = 0; r_v = 0;
        repeat (40) @(negedge clk);
        $display("RESULT cyc %0d ops wr %0d rd %0d own %0d mismatches %0d real_flt %b tlm_flt %b uninit %0d", cyc, nwr, nrd,
                 nown, nbad, of_a, of_b, u_tlm.n_uninit);
        if (nbad == 0 && of_a == 0 && of_b == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
