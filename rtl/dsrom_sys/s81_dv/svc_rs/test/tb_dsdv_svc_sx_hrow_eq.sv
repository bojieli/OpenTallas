`timescale 1ns/1ps
// S81-KITS-HROW 2026-10-24: cycle-exact equivalence bench of dsdv_svc_sx_hrow (registered decoded selects) against the
// reference form (role register decoded at every mux; the same file before the change, module renamed
// dsdv_svc_sx_hrow_ref by tools/s81_dv/svc_rs/hrow_eq_bench.sh).  All 16 sid straps x both halves hb side by side, every
// input port random on every cycle (valids at ~50% density so every mux source, the stray / misalignment checks and the
// sticky fault all toggle), the die reset asserted at cycle 0 and again mid-run (async, off the clock edge).  Every output
// port of every pair is compared on every cycle from time 0 (reset included); X-free start (--x-initial 0 both sides).
module tb_dsdv_svc_sx_hrow_eq;
`ifndef MUT
`define MUT 0
`endif
`ifndef NCYC
`define NCYC 20000
`endif
    reg ck = 0; reg rst = 0;
    always #0.5 ck = ~ck;
    integer seed = 1, cyc = 0, err = 0;
    genvar p;
    generate for (p = 0; p < 32; p = p + 1) begin : g_p
        reg [269:0] l_i, gi_n, gi_e, gi_s, gi_w; reg [137:0] si_n, si_e, si_s, si_w;
        wire [269:0] go_n0, go_e0, go_s0, go_w0, rt0, go_n1, go_e1, go_s1, go_w1, rt1;
        wire [137:0] so_n0, so_e0, so_s0, so_w0, so_n1, so_e1, so_s1, so_w1; wire [38:0] t0, t1; wire f0, f1;
        dsdv_svc_sx_hrow_ref #(.MUT(`MUT)) u_ref (.ck(ck), .rst(rst), .sid(4'(p / 2)), .hb(1'(p % 2)), .l_i(l_i),
            .gi_n(gi_n), .gi_e(gi_e), .gi_s(gi_s), .gi_w(gi_w), .go_n(go_n0), .go_e(go_e0), .go_s(go_s0), .go_w(go_w0),
            .si_n(si_n), .si_e(si_e), .si_s(si_s), .si_w(si_w), .so_n(so_n0), .so_e(so_e0), .so_s(so_s0), .so_w(so_w0),
            .rt_o(rt0), .t_o(t0), .fault(f0));
        dsdv_svc_sx_hrow #(.MUT(`MUT)) u_new (.ck(ck), .rst(rst), .sid(4'(p / 2)), .hb(1'(p % 2)), .l_i(l_i),
            .gi_n(gi_n), .gi_e(gi_e), .gi_s(gi_s), .gi_w(gi_w), .go_n(go_n1), .go_e(go_e1), .go_s(go_s1), .go_w(go_w1),
            .si_n(si_n), .si_e(si_e), .si_s(si_s), .si_w(si_w), .so_n(so_n1), .so_e(so_e1), .so_s(so_s1), .so_w(so_w1),
            .rt_o(rt1), .t_o(t1), .fault(f1));
        // every output port: 5 x 270 + 4 x 138 + 39 + 1 = 1942 b
        wire [1941:0] a = {go_n0, go_e0, go_s0, go_w0, rt0, so_n0, so_e0, so_s0, so_w0, t0, f0};
        wire [1941:0] b = {go_n1, go_e1, go_s1, go_w1, rt1, so_n1, so_e1, so_s1, so_w1, t1, f1};
        function automatic [269:0] r270(input integer dummy);
            for (int i = 0; i < 270; i += 32) r270[i +: 32] = $urandom;
            r270[269] = $urandom % 2;
        endfunction
        function automatic [137:0] r138(input integer dummy);
            for (int i = 0; i < 138; i += 32) r138[i +: 32] = $urandom;
            r138[137] = $urandom % 2;
        endfunction
        always @(negedge ck) begin
            l_i <= r270(0); gi_n <= r270(0); gi_e <= r270(0); gi_s <= r270(0); gi_w <= r270(0);
            si_n <= r138(0); si_e <= r138(0); si_s <= r138(0); si_w <= r138(0);
        end
        integer pe = 0;
        always @(posedge ck) begin
            #0.1;
            if (a !== b) begin
                pe = pe + 1; err = err + 1;
                if (pe <= 3) $display("MISMATCH pair %0d (sid %0d hb %0d) cycle %0d: diff bits %0d", p, p / 2, p % 2, cyc,
                                      $countones(a ^ b));
            end
        end
    end endgenerate
    always @(posedge ck) cyc <= cyc + 1;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        void'($urandom(seed));
        rst = 0; repeat (3) @(posedge ck); #0.3 rst = 1;
        repeat (`NCYC / 2) @(posedge ck); #0.2 rst = 0;      // mid-run async reset
        repeat (4) @(posedge ck); #0.4 rst = 1;
        repeat (`NCYC / 2) @(posedge ck); #0.2;
        $display("HROW_EQ cycles %0d pairs 32 MUT %0d mismatches %0d", cyc, `MUT, err);
        if (err == 0) $display("HROW_EQ PASS"); else $display("HROW_EQ FAIL");
        $finish;
    end
endmodule
